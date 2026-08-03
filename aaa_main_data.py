import time
import pandas as pd
from binance.um_futures import UMFutures
from ta.momentum import RSIIndicator
from ta.trend import MACD

client = UMFutures()

# --- ШИНЭ: MACD-ийн төлөвийг хадгалах state (macd.py-аас) ---
macd_state = {}

def _build_initial_macd_state(klines, macd_line, macd_signal):
    """
    MACD-ийн түүхэн мэдээлэлд үндэслэн анхны state-г үүсгэнэ.
    Хамгийн сүүлийн UP, DOWN огтлолцлыг олж, limit болон trend-г тохируулна.
    """
    initial_st = {
        "uplimit": None, "downlimit": None,
        "uplimit_cross_line": None, "downlimit_cross_line": None,
        "trend": "None"
    }
    last_cross_up_idx = -1
    last_cross_down_idx = -1

    # Хамгийн сүүлийн үеэс эхлэн ухарч шалгах
    for i in range(len(macd_line) - 2, 2, -1):
        # UP огтлолцол
        if macd_line.iloc[i] > macd_signal.iloc[i] and macd_line.iloc[i-1] < macd_signal.iloc[i-1]:
            if initial_st["uplimit"] is None: # Хамгийн сүүлийнхийг олох
                last_cross_up_idx = i
                window_klines = macd_line.iloc[i-3:i+1]
                initial_st["uplimit"] = min(window_klines)
                initial_st["uplimit_cross_line"] = macd_line.iloc[i]

        # DOWN огтлолцол
        if macd_line.iloc[i] < macd_signal.iloc[i] and macd_line.iloc[i-1] > macd_signal.iloc[i-1]:
            if initial_st["downlimit"] is None: # Хамгийн сүүлийнхийг олох
                last_cross_down_idx = i
                window_klines = macd_line.iloc[i-3:i+1]
                initial_st["downlimit"] = max(window_klines)
                initial_st["downlimit_cross_line"] = macd_line.iloc[i]

        # Хоёулаа олдсон бол зогсох
        if initial_st["uplimit"] is not None and initial_st["downlimit"] is not None:
            break

    # Хамгийн сүүлд аль огтлолцол болсныг тодорхойлох
    if last_cross_up_idx > last_cross_down_idx:
        initial_st["trend"] = "UP"
    elif last_cross_down_idx > last_cross_up_idx:
        initial_st["trend"] = "DOWN"

    return initial_st

def get_all_data(symbol):
    """
    Нэг зоосны бүх индикатор болон шаардлагатай мэдээллийг тооцоолж,
    нэгдсэн dictionary хэлбэрээр буцаана.
    """
    global macd_state # Глобал state-г ашиглах

    # --- ШИНЭ: API дуудлагыг алдаанаас хамгаалах ---
    try:
        # Бүх тооцоололд хангалттай дата хэрэгтэй тул limit-г 200 болгоно
        klines = client.klines(symbol=symbol, interval="1m", limit=200)
    except Exception as e:
        # Сүлжээний алдаа, timeout зэрэг гарвал энд барьж авна.
        print(f"🔥 API Error in get_all_data for {symbol}: {e}")
        return None # Алдаа гарвал None буцааж, main_loop-г зогсоохгүй.
    # --- /ШИНЭ ---

    try:
        if not klines or len(klines) < 50:
            return None

        closes = [float(x[4]) for x in klines]
        closes_series = pd.Series(closes)
        
        # --- RSI Тооцоолол (rsi.py, rsi_cross.py, rsi_status.py-ийн логик) ---
        rsi_series = RSIIndicator(close=closes_series, window=7).rsi().dropna()
        if len(rsi_series) < 4: return None

        rsi0, rsi1, rsi2 = rsi_series.iloc[-1], rsi_series.iloc[-2], rsi_series.iloc[-3]

        # --- OHLC Тооцоолол (ohlc.py-ийн логик) ---
        last_4_klines = klines[-4:]
        opens = [float(k[1]) for k in last_4_klines]
        highs = [float(k[2]) for k in last_4_klines]
        lows = [float(k[3]) for k in last_4_klines]
        closes_4 = [float(k[4]) for k in last_4_klines]

        # --- RSI Status & History Тооцоолол (rsi_status.py, rsi_last_status.py-ийн логик) ---
        offset = len(klines) - len(rsi_series)
        status_history = {"rsi_30_up": [], "rsi_30_down": [], "rsi_70_up": [], "rsi_70_down": []}
        last_status = "None"

        # 1. Last status-г олох
        for i in range(len(rsi_series) - 1, 0, -1):
            prev_rsi, curr_rsi = rsi_series.iloc[i - 1], rsi_series.iloc[i]
            if prev_rsi <= 30 and curr_rsi > 30: last_status = "30U"; break
            if prev_rsi >= 30 and curr_rsi < 30: last_status = "30D"; break
            if prev_rsi <= 70 and curr_rsi > 70: last_status = "70U"; break
            if prev_rsi >= 70 and curr_rsi < 70: last_status = "70D"; break
        
        # 2. Түүхэн үнийг олох
        for i in range(len(rsi_series) - 2, 2, -1):
            prev_rsi, cur_rsi = rsi_series.iloc[i - 1], rsi_series.iloc[i]
            window_klines = klines[i + offset - 3 : i + offset + 1]
            w_opens = [float(k[1]) for k in window_klines]
            if prev_rsi <= 30 and cur_rsi > 30: status_history["rsi_30_up"].append(min(w_opens))
            if prev_rsi >= 30 and cur_rsi < 30: status_history["rsi_30_down"].append(max(w_opens))
            if prev_rsi <= 70 and cur_rsi > 70: status_history["rsi_70_up"].append(min(w_opens))
            if prev_rsi >= 70 and cur_rsi < 70: status_history["rsi_70_down"].append(max(w_opens))

        # --- Average Status, MAXU, MIND (rsi_avg_status.py-ийн логик) ---
        s30u_val = status_history["rsi_30_up"][0] if status_history["rsi_30_up"] else None
        s70d_val = status_history["rsi_70_down"][0] if status_history["rsi_70_down"] else None
        s70u_val = status_history["rsi_70_up"][0] if status_history["rsi_70_up"] else None
        s30d_val = status_history["rsi_30_down"][0] if status_history["rsi_30_down"] else None

        average_status = (s30u_val + s70d_val) / 2.0 if s30u_val and s70d_val else None
        valid_up = [v for v in [s30u_val, s70u_val] if v is not None]
        valid_down = [v for v in [s30d_val, s70d_val] if v is not None]
        max_u = max(valid_up) if valid_up else None
        min_d = min(valid_down) if valid_down else None

        # --- MACD Тооцоолол (macd.py-ийн логикийг нэгтгэв) ---
        macd_indicator = MACD(close=closes_series, window_slow=26, window_fast=12, window_sign=9)
        macd_line = macd_indicator.macd()
        macd_signal = macd_indicator.macd_signal()
        macd_hist = macd_indicator.macd_diff()

        macd_data = {} # Алдаа гарвал хоосон байх
        if len(macd_line.dropna()) >= 4:
            # MACD state-г анхлуулах
            if symbol not in macd_state:
                macd_state[symbol] = _build_initial_macd_state(klines, macd_line, macd_signal)

            # --- ХҮСЭЛТИЙН ДАГУУ ЗАСВАР: Огтлолцлын логикийг сэргээж, төлвийг хадгалах ---
            # 1. Огтлолцол болсон эсэхийг шалгах (Хэрэглэгчийн анхны логик)
            is_cross_up = macd_line.iloc[-2] > macd_signal.iloc[-2] and macd_line.iloc[-3] < macd_signal.iloc[-3]
            is_cross_down = macd_line.iloc[-2] < macd_signal.iloc[-2] and macd_line.iloc[-3] > macd_signal.iloc[-3]

            # Сүүлийн 4 line-ийн min/max
            last_4_lines = macd_line.tail(4).tolist()
            macd_min = min(last_4_lines)
            macd_max = max(last_4_lines)

            # 2. Огтлолцол болсон бол "trend" болон limit утгуудыг шинэчлэх
            if is_cross_up:
                macd_state[symbol]["trend"] = "UP"
                macd_state[symbol]["uplimit"] = macd_min
                macd_state[symbol]["uplimit_cross_line"] = macd_line.iloc[-2]
            if is_cross_down:
                macd_state[symbol]["trend"] = "DOWN"
                macd_state[symbol]["downlimit"] = macd_max
                macd_state[symbol]["downlimit_cross_line"] = macd_line.iloc[-2]

            macd_data = {
                "line": { "0": macd_line.iloc[-1], "-1": macd_line.iloc[-2], "-2": macd_line.iloc[-3], "-3": macd_line.iloc[-4] },
                "signal": { "0": macd_signal.iloc[-1], "-1": macd_signal.iloc[-2], "-2": macd_signal.iloc[-3], "-3": macd_signal.iloc[-4] },
                "hist": { "0": macd_hist.iloc[-1], "-1": macd_hist.iloc[-2], "-2": macd_hist.iloc[-3], "-3": macd_hist.iloc[-4] },
                "macd_up": macd_state[symbol].get("trend") == "UP",      # 3. Хадгалсан төлвийг ашиглах
                "macd_down": macd_state[symbol].get("trend") == "DOWN",  # 3. Хадгалсан төлвийг ашиглах
                "macd_min": macd_min,
                "macd_max": macd_max,
                "macd_uplimit": macd_state[symbol]["uplimit"],
                "macd_downlimit": macd_state[symbol]["downlimit"],
                "uplimit_cross_line": macd_state[symbol]["uplimit_cross_line"],
                "downlimit_cross_line": macd_state[symbol]["downlimit_cross_line"]
            }

        # --- Бүх мэдээллийг нэгтгэн буцаах ---
        return {
            "symbol": symbol,
            "price": closes_series.iloc[-1],
            "last_status": last_status,
            "average_status": average_status,
            "MAXU": max_u,
            "MIND": min_d,
            "status": {
                "rsi_30_up": s30u_val,
                "rsi_30_up_prev": status_history["rsi_30_up"][1] if len(status_history["rsi_30_up"]) > 1 else None,
                "rsi_30_down": s30d_val,
                "rsi_30_down_prev": status_history["rsi_30_down"][1] if len(status_history["rsi_30_down"]) > 1 else None,
                "rsi_70_up": s70u_val,
                "rsi_70_up_prev": status_history["rsi_70_up"][1] if len(status_history["rsi_70_up"]) > 1 else None,
                "rsi_70_down": s70d_val,
                "rsi_70_down_prev": status_history["rsi_70_down"][1] if len(status_history["rsi_70_down"]) > 1 else None,
            },
            "cross": {
                "30_up": "UP" if (rsi2 <= 30 and rsi1 > 30) else "--",
                "70_up": "UP" if (rsi2 <= 70 and rsi1 > 70) else "--",
                "30_down": "DOWN" if (rsi2 >= 30 and rsi1 < 30) else "--",
                "70_down": "DOWN" if (rsi2 >= 70 and rsi1 < 70) else "--"
            },
            "rsi": { "0": rsi0, "-1": rsi1, "-2": rsi2, "-3": rsi_series.iloc[-4] },
            "ohlc": {
                "open": { "0": opens[-1], "-1": opens[-2], "-2": opens[-3], "-3": opens[-4] },
                "high": { "0": highs[-1], "-1": highs[-2], "-2": highs[-3], "-3": highs[-4] },
                "low": { "0": lows[-1], "-1": lows[-2], "-2": lows[-3], "-3": lows[-4] },
                "close": { "0": closes_4[-1], "-1": closes_4[-2], "-2": closes_4[-3], "-3": closes_4[-4] },
                "min_open": min(opens), "max_open": max(opens),
                "min_high": min(highs), "max_high": max(highs),
                "min_low": min(lows), "max_low": max(lows),
                "min_close": min(closes_4), "max_close": max(closes_4),
            },
            "macd": macd_data
        }
    except Exception as e:
        print(f"🔥 Calculation Error in get_all_data for {symbol}: {e}")
        return None
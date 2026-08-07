import pandas as pd
from binance.um_futures import UMFutures
from ta.momentum import RSIIndicator
from collections import deque

def _get_standalone_client():
    """
    Зөвхөн RSI тооцоолоход зориулсан, нийтийн API ашигладаг,
    дангаараа ажиллах Binance client үүсгэнэ.
    """
    client = UMFutures()
    # Сүлжээнээс болж гацахаас сэргийлж timeout тохируулах
    client.session.requests_params = {"timeout": 10}
    return client

def get_rsi_data(symbol): # --- ЗАСВАР: client параметрийг хасаж, дангаар нь ажилладаг болгох ---
    """
    Нэг зоосны RSI-тай холбоотой бүх мэдээллийг тооцоолж,
    нэгдсэн dictionary хэлбэрээр буцаана.
    """
    try:
        client = _get_standalone_client() # --- ШИНЭ: Client-г дотроо үүсгэнэ ---
        # Бүх тооцоололд хангалттай дата хэрэгтэй тул limit-г 200 болгоно
        klines = client.klines(symbol=symbol, interval="1m", limit=200)
        if not klines or len(klines) < 50:
            print(f"Warning: Not enough kline data for {symbol} to calculate RSI.")
            return None

        closes = [float(x[4]) for x in klines]
        closes_series = pd.Series(closes)
        
        # --- RSI Тооцоолол ---
        rsi_series = RSIIndicator(close=closes_series, window=7).rsi().dropna()
        if len(rsi_series) < 4: return None

        rsi0, rsi1, rsi2, rsi3 = rsi_series.iloc[-1], rsi_series.iloc[-2], rsi_series.iloc[-3], rsi_series.iloc[-4]

        # --- RSI Status & History Тооцоолол ---
        offset = len(klines) - len(rsi_series)
        price_history = {"rsi_30_up": [], "rsi_30_down": [], "rsi_70_up": [], "rsi_70_down": []}
        
        # --- ЗАСВАР: last_status-ийн логикийг хуучин, зөв хэлбэрт нь буцаах ---
        last_status = "None"
        for i in range(len(rsi_series) - 1, 0, -1):
            prev_rsi, curr_rsi = rsi_series.iloc[i - 1], rsi_series.iloc[i]
            if prev_rsi <= 30 and curr_rsi > 30: last_status = "30U"; break
            if prev_rsi >= 30 and curr_rsi < 30: last_status = "30D"; break
            if prev_rsi <= 70 and curr_rsi > 70: last_status = "70U"; break
            if prev_rsi >= 70 and curr_rsi < 70: last_status = "70D"; break
        # --- /ЗАСВАР ---

        # --- Trend-ийн логикийг тусад нь тооцоолох ---
        trend_status_history = deque(maxlen=10)
        for i in range(len(rsi_series) - 1, 0, -1):
            prev_rsi, curr_rsi = rsi_series.iloc[i - 1], rsi_series.iloc[i]
            new_status = None
            if prev_rsi <= 30 and curr_rsi > 30: new_status = "30U"
            elif prev_rsi >= 30 and curr_rsi < 30: new_status = "30D"
            elif prev_rsi <= 50 and curr_rsi > 50: new_status = "50U"
            elif prev_rsi >= 50 and curr_rsi < 50: new_status = "50D"
            elif prev_rsi <= 70 and curr_rsi > 70: new_status = "70U"
            elif prev_rsi >= 70 and curr_rsi < 70: new_status = "70D"
            if new_status:
                if not trend_status_history or trend_status_history[0] != new_status:
                    trend_status_history.appendleft(new_status)

        trend = "None"
        if len(trend_status_history) >= 2:
            for i in range(len(trend_status_history) - 1, 0, -1):
                curr, prev = trend_status_history[i], trend_status_history[i-1]
                if prev == "30U" and curr == "50U": trend = "uptrand1"; break
                elif prev == "50U" and curr == "70U": trend = "uptrand2"; break
                elif prev == "70D" and curr == "50D": trend = "downtrand1"; break
                elif prev == "50D" and curr == "30D": trend = "downtrand2"; break
        # --- /Trend-ийн логик ---
        
        # 2. Түүхэн огтлолцлын үнийг олох
        for i in range(len(rsi_series) - 2, 2, -1):
            prev_rsi, cur_rsi = rsi_series.iloc[i - 1], rsi_series.iloc[i]
            # Тухайн огтлолцол болсон лааны орчны нээлтийн үнийг авна
            window_klines = klines[i + offset - 3 : i + offset + 1]
            w_opens = [float(k[1]) for k in window_klines]
            if prev_rsi <= 30 and cur_rsi > 30: price_history["rsi_30_up"].append(min(w_opens))
            if prev_rsi >= 30 and cur_rsi < 30: price_history["rsi_30_down"].append(max(w_opens))
            if prev_rsi <= 70 and cur_rsi > 70: price_history["rsi_70_up"].append(min(w_opens))
            if prev_rsi >= 70 and cur_rsi < 70: price_history["rsi_70_down"].append(max(w_opens))

        # --- Average Status, MAXU, MIND Тооцоолол ---
        s30u_val = price_history["rsi_30_up"][0] if price_history["rsi_30_up"] else None
        s70d_val = price_history["rsi_70_down"][0] if price_history["rsi_70_down"] else None
        s70u_val = price_history["rsi_70_up"][0] if price_history["rsi_70_up"] else None
        s30d_val = price_history["rsi_30_down"][0] if price_history["rsi_30_down"] else None

        average_status = (s30u_val + s70d_val) / 2.0 if s30u_val and s70d_val else None
        valid_up = [v for v in [s30u_val, s70u_val] if v is not None]
        valid_down = [v for v in [s30d_val, s70d_val] if v is not None]
        max_u = max(valid_up) if valid_up else None
        min_d = min(valid_down) if valid_down else None

        # --- Бүх мэдээллийг нэгтгэн буцаах ---
        return {
            "values": { "0": rsi0, "-1": rsi1, "-2": rsi2, "-3": rsi3 },
            "last_status": last_status,
            "trend": trend, # --- ШИНЭ: Тренд нэмэгдсэн ---
            "average_status": average_status,
            "MAXU": max_u,
            "MIND": min_d,
            "cross_history": {
                "s30u": s30u_val,
                "s30u_prev": price_history["rsi_30_up"][1] if len(price_history["rsi_30_up"]) > 1 else None,
                "s30d": s30d_val,
                "s30d_prev": price_history["rsi_30_down"][1] if len(price_history["rsi_30_down"]) > 1 else None,
                "s70u": s70u_val,
                "s70u_prev": price_history["rsi_70_up"][1] if len(price_history["rsi_70_up"]) > 1 else None,
                "s70d": s70d_val,
                "s70d_prev": price_history["rsi_70_down"][1] if len(price_history["rsi_70_down"]) > 1 else None,
            },
            "cross_now": {
                "30_up": "UP" if (rsi2 <= 30 and rsi1 > 30) else "--",
                "70_up": "UP" if (rsi2 <= 70 and rsi1 > 70) else "--",
                "30_down": "DOWN" if (rsi2 >= 30 and rsi1 < 30) else "--",
                "70_down": "DOWN" if (rsi2 >= 70 and rsi1 < 70) else "--"
            }
        }
    except Exception as e:
        print(f"🔥 Calculation Error in get_rsi_data for {symbol}: {e}")
        return None
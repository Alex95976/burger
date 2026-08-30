import time
import pandas as pd
from binance.um_futures import UMFutures

macd_state = {}

def get_initial_price(symbol):
    """
    Зөвхөн тухайн зоосны MACD state эсвэл 0-ийн огтлолцлын эхлэх үнийг 
    ямар ч print-гүйгээр хурдан олж буцаах туслах функц.
    """
    try:
        client = _get_standalone_client()
        klines = client.klines(symbol=symbol, interval="1m", limit=200)
        if not klines or len(klines) < 50:
            return None
        
        closes = [float(x[4]) for x in klines]
        closes_series = pd.Series(closes)
        ema12 = closes_series.ewm(span=12, adjust=False).mean()
        ema26 = closes_series.ewm(span=26, adjust=False).mean()
        macd_line = ema12 - ema26
        
        if len(macd_line.dropna()) < 4:
            return float(klines[-1][1])

        # 0-ийн огтлолцлыг ухрааж хайх
        for i in range(len(macd_line) - 1, 0, -1):
            curr_line = macd_line.iloc[i]
            prev_line = macd_line.iloc[i-1]
            if (prev_line > 0 and curr_line < 0) or (prev_line < 0 and curr_line > 0):
                kline_idx = i + (len(klines) - len(macd_line))
                if 0 <= kline_idx < len(klines):
                    return float(klines[kline_idx][1])
                    
        return float(klines[-1][1])
    except Exception:
        return None

def _get_standalone_client():
    client = UMFutures()
    client.session.requests_params = {"timeout": 10}
    return client

def _build_initial_macd_state(klines, macd_line, macd_signal):
    initial_st = {
        "uplimit": None, "downlimit": None,
        "uplimit_cross_line": None, "downlimit_cross_line": None,
        "trend": "None",
        "macd_initial_price": None
    }
    last_cross_up_idx = -1
    last_cross_down_idx = -1

    for i in range(len(macd_line) - 2, 2, -1):
        if macd_line.iloc[i] > macd_signal.iloc[i] and macd_line.iloc[i-1] < macd_signal.iloc[i-1]:
            if initial_st["uplimit"] is None:
                last_cross_up_idx = i
                window_klines = macd_line.iloc[i-3:i+1]
                initial_st["uplimit"] = min(window_klines)
                initial_st["uplimit_cross_line"] = macd_line.iloc[i]

        if macd_line.iloc[i] < macd_signal.iloc[i] and macd_line.iloc[i-1] > macd_signal.iloc[i-1]:
            if initial_st["downlimit"] is None:
                last_cross_down_idx = i
                window_klines = macd_line.iloc[i-3:i+1]
                initial_st["downlimit"] = max(window_klines)
                initial_st["downlimit_cross_line"] = macd_line.iloc[i]

        if initial_st["uplimit"] is not None and initial_st["downlimit"] is not None:
            break

    if last_cross_up_idx > last_cross_down_idx:
        initial_st["trend"] = "UP"
    elif last_cross_down_idx > last_cross_up_idx:
        initial_st["trend"] = "DOWN"

    # --- АНХНЫ ТӨЛӨВ ҮҮСГЭХ ҮЕД 0 КАБЕЛЬ ОГТЛОЛЦОЛ БАЙГАА ЭСЫГ ШАЛГАХ ЛОГИК ---
    found_zero_cross = False
    for i in range(len(macd_line) - 1, 0, -1):
        curr_line = macd_line.iloc[i]     # macd_line1
        prev_line = macd_line.iloc[i-1]   # өмнөх лааны line
        
        # 0-ээс дээш байж байгаад доош орсон эсвэл 0-ээс доош байж байгаад дээш гарсан нөхцөл
        if (prev_line > 0 and curr_line < 0) or (prev_line < 0 and curr_line > 0):
            # Тухайн индексийн klines дээрх open үнийг олж авна
            # offset тооцож klines-аас тохирох лааны open-ийг авна
            kline_idx = i + (len(klines) - len(macd_line))
            if 0 <= kline_idx < len(klines):
                initial_st["macd_initial_price"] = float(klines[kline_idx][1])
                found_zero_cross = True
                break

    # Хэрэв түүхээс 0-ийн огтлолцол олдохгүй бол хамгийн сүүлийн лааны open-ийг авна
    if not found_zero_cross and klines:
        initial_st["macd_initial_price"] = float(klines[-1][1])

    return initial_st

def get_macd(symbol):
    global macd_state
    try:
        print(f"[CHECK] Fetching data for {symbol}...")
        client = _get_standalone_client()
        klines = client.klines(symbol=symbol, interval="1m", limit=200)
        if not klines or len(klines) < 50:
            print(f"Warning: Not enough kline data for {symbol} to calculate MACD.")
            return None

        closes = [float(x[4]) for x in klines]
        closes_series = pd.Series(closes)

        ema12 = closes_series.ewm(span=12, adjust=False).mean()
        ema26 = closes_series.ewm(span=26, adjust=False).mean()
        macd_line = ema12 - ema26
        macd_signal = macd_line.ewm(span=9, adjust=False).mean()
        macd_hist = macd_line - macd_signal

        if len(macd_line.dropna()) < 4:
            return None

        if symbol not in macd_state:
            macd_state[symbol] = _build_initial_macd_state(klines, macd_line, macd_signal)
            macd_state[symbol]["line_direction"] = "None"
            macd_state[symbol]["macd_lineup_limit"] = None
            macd_state[symbol]["macd_linedown_limit"] = None
            print(f"[INITIAL STATE] {symbol}: {macd_state[symbol]}")

        macd_up = macd_line.iloc[-2] > macd_signal.iloc[-2] and macd_line.iloc[-3] < macd_signal.iloc[-3]
        macd_down = macd_line.iloc[-2] < macd_signal.iloc[-2] and macd_line.iloc[-3] > macd_signal.iloc[-3]

        line_minus_1 = macd_line.iloc[-2]
        line_minus_2 = macd_line.iloc[-3]

        current_line_direction = "UP" if line_minus_1 > line_minus_2 else "DOWN"
        previous_line_direction = macd_state[symbol].get("line_direction", "None")

        if current_line_direction != previous_line_direction:
            if current_line_direction == "DOWN":
                macd_state[symbol]["macd_lineup_limit"] = line_minus_2
            elif current_line_direction == "UP":
                macd_state[symbol]["macd_linedown_limit"] = line_minus_2
        
        macd_state[symbol]["line_direction"] = current_line_direction

        last_4_lines = [macd_line.iloc[-1], macd_line.iloc[-2], macd_line.iloc[-3], macd_line.iloc[-4]]
        macd_min = min(last_4_lines)
        macd_max = max(last_4_lines)

        if macd_up:
            macd_state[symbol]["trend"] = "UP"
            macd_state[symbol]["uplimit"] = macd_min
            macd_state[symbol]["uplimit_cross_line"] = macd_line.iloc[-2]
        if macd_down:
            macd_state[symbol]["trend"] = "DOWN"
            macd_state[symbol]["downlimit"] = macd_max
            macd_state[symbol]["downlimit_cross_line"] = macd_line.iloc[-2]

        current_trend = macd_state[symbol].get("trend", "None")

        # --- ҮРГЭЛЖЛЭХ ЯВЦАД MACD_LINE 0-ИЙГ ГАТЛАХЫГ ХЯНАХ ЛОГИК ---
        try:
            curr_line1 = macd_line.iloc[-2]
            prev_line1 = macd_line.iloc[-3]
            
            # macd_line1 0-ээс дээш байж байгаад доош орох эсвэл доороос дээш гарах моментууд
            cross_zero_line_up = (prev_line1 < 0 and curr_line1 > 0)
            cross_zero_line_down = (prev_line1 > 0 and curr_line1 < 0)

            if cross_zero_line_up or cross_zero_line_down:
                open1 = float(klines[-2][1]) # тухайн лааны open ханш
                macd_state[symbol]["macd_initial_price"] = open1
                print(f"[MACD LINE ZERO CROSS] {symbol} | up={cross_zero_line_up} | down={cross_zero_line_down} | open={open1}")
        except IndexError:
            pass

        try:
            cross_above_zero = (macd_signal.iloc[-2] > 0 and macd_signal.iloc[-3] < 0 and macd_signal.iloc[-4] < 0)
            cross_below_zero = (macd_signal.iloc[-2] < 0 and macd_signal.iloc[-3] > 0 and macd_signal.iloc[-4] > 0)

            if cross_above_zero or cross_below_zero:
                open0 = float(klines[-1][1])
                print(f"[ZERO CROSS SIGNAL] {symbol} | above_zero={cross_above_zero} | below_zero={cross_below_zero} | signal[-2]={macd_signal.iloc[-2]:.8f}")
        except IndexError:
            pass

        # --- ТООНУУДЫГ ЦЭВЭРХЭН БУТАРХАЙГААР ФОРМАТЛАХ ХЭСЭГ ---
        line_4 = [f"{x:.8f}" for x in macd_line.iloc[-4:].tolist()]
        sig_4 = [f"{x:.8f}" for x in macd_signal.iloc[-4:].tolist()]
        hist_4 = [f"{x:.8f}" for x in macd_hist.iloc[-4:].tolist()]

        up_lim = f"{macd_state[symbol]['uplimit']:.8f}" if macd_state[symbol]['uplimit'] is not None else "None"
        down_lim = f"{macd_state[symbol]['downlimit']:.8f}" if macd_state[symbol]['downlimit'] is not None else "None"
        
        line_up_lim = f"{macd_state[symbol].get('macd_lineup_limit'):.8f}" if macd_state[symbol].get('macd_lineup_limit') is not None else "None"
        line_down_lim = f"{macd_state[symbol].get('macd_linedown_limit'):.8f}" if macd_state[symbol].get('macd_linedown_limit') is not None else "None"
        
        up_cross = f"{macd_state[symbol]['uplimit_cross_line']:.8f}" if macd_state[symbol]['uplimit_cross_line'] is not None else "None"
        down_cross = f"{macd_state[symbol]['downlimit_cross_line']:.8f}" if macd_state[symbol]['downlimit_cross_line'] is not None else "None"
        
        init_price = f"{macd_state[symbol].get('macd_initial_price'):.8f}" if macd_state[symbol].get('macd_initial_price') is not None else "None"

        print(f"\n========== MACD DEBUG: {symbol} ==========")
        print(f"MACD line   : {line_4}")
        print(f"Signal      : {sig_4}")
        print(f"Hist        : {hist_4}")
        print(f"MACD UP     : {macd_up}")
        print(f"MACD DOWN   : {macd_down}")
        print(f"Current trend: {current_trend}")
        print(f"MACD min    : {macd_min:.8f}")
        print(f"MACD max    : {macd_max:.8f}")
        print(f"UP limit    : {up_lim}")
        print(f"DOWN limit  : {down_lim}")
        print(f"Line UP limit   : {line_up_lim}")
        print(f"Line DOWN limit : {line_down_lim}")
        print(f"UP cross line   : {up_cross}")
        print(f"DOWN cross line : {down_cross}")
        print(f"Initial price   : {init_price}")
        print("==========================================")

        return {
            "line": {"0": macd_line.iloc[-1], "-1": macd_line.iloc[-2], "-2": macd_line.iloc[-3], "-3": macd_line.iloc[-4]},
            "signal": {"0": macd_signal.iloc[-1], "-1": macd_signal.iloc[-2], "-2": macd_signal.iloc[-3], "-3": macd_signal.iloc[-4]},
            "hist": {"0": macd_hist.iloc[-1], "-1": macd_hist.iloc[-2], "-2": macd_hist.iloc[-3], "-3": macd_hist.iloc[-4]},
            "macd_up": current_trend == "UP",
            "macd_down": current_trend == "DOWN",
            "macd_min": macd_min,
            "macd_max": macd_max,
            "macd_uplimit": macd_state[symbol]["uplimit"],
            "macd_downlimit": macd_state[symbol]["downlimit"],
            "macd_lineup_limit": macd_state[symbol].get("macd_lineup_limit"),
            "macd_linedown_limit": macd_state[symbol].get("macd_linedown_limit"),
            "uplimit_cross_line": macd_state[symbol]["uplimit_cross_line"],
            "downlimit_cross_line": macd_state[symbol]["downlimit_cross_line"],
            "macd_initial_price": macd_state[symbol].get("macd_initial_price")
        }

    except Exception as e:
        print(f"Error calculating MACD for {symbol}: {e}")
        return None

if __name__ == "__main__":
    target_symbol = "MAGMAUSDT"
    print(f"Starting MACD monitor loop for {target_symbol} every 1 second...")
    while True:
        get_macd(target_symbol)
        time.sleep(1)

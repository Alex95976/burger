import time
import pandas as pd
from ta.trend import MACD
from binance.um_futures import UMFutures

# --- ШИНЭ: Огтлолцлын үеийн хязгаарын утгыг хадгалах state ---
macd_state = {}

def _get_standalone_client():
    """
    Зөвхөн MACD тооцоолоход зориулсан, нийтийн API ашигладаг,
    дангаараа ажиллах Binance client үүсгэнэ.
    """
    client = UMFutures()
    client.session.requests_params = {"timeout": 10}
    return client

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

def get_macd(symbol): # --- ЗАСВАР: client параметрийг хасаж, бие даасан болгох ---
    """
    Тухайн зоосны MACD-г тооцоолж, сүүлийн 4 үеийн утгуудыг буцаана.
    """
    global macd_state # Глобал state-г ашиглах

    try:
        client = _get_standalone_client() # --- ШИНЭ: Client-г дотроо үүсгэнэ ---
        # MACD тооцоолоход хангалттай дата хэрэгтэй тул limit-г 200 болгоно
        klines = client.klines(symbol=symbol, interval="1m", limit=200)
        if not klines or len(klines) < 50: # Хангалттай дата байхгүй бол алгасах
            print(f"Warning: Not enough kline data for {symbol} to calculate MACD.")
            return None

        closes = [float(x[4]) for x in klines]
        closes_series = pd.Series(closes)

        # MACD тооцоолох (Binance-ийн стандарт тохиргоо: 12, 26, 9)
        macd_indicator = MACD(close=closes_series, window_slow=26, window_fast=12, window_sign=9)
        macd_line = macd_indicator.macd()
        macd_signal = macd_indicator.macd_signal()
        macd_hist = macd_indicator.macd_diff()

        # Сүүлийн 4 утгыг авахад хангалттай урттай эсэхийг шалгах
        if len(macd_line.dropna()) < 4:
            return None

        # Хэрэв тухайн зоосны state байхгүй бол анхны утгыг оноох
        if symbol not in macd_state:
            # --- ШИНЭ: Анхны state-г түүхээс бодож олох ---
            macd_state[symbol] = _build_initial_macd_state(klines, macd_line, macd_signal)

        # MACD огтлолцлыг тооцоолох
        macd_up = macd_line.iloc[-2] > macd_signal.iloc[-2] and macd_line.iloc[-3] < macd_signal.iloc[-3]
        macd_down = macd_line.iloc[-2] < macd_signal.iloc[-2] and macd_line.iloc[-3] > macd_signal.iloc[-3]

        # Сүүлийн 4 MACD line-ийн min/max-г олох
        last_4_lines = [macd_line.iloc[-1], macd_line.iloc[-2], macd_line.iloc[-3], macd_line.iloc[-4]]
        macd_min = min(last_4_lines)
        macd_max = max(last_4_lines)

        # Огтлолцол болсон үед limit утгуудыг шинэчлэх
        # --- ШИНЭ: Огтлолцол болсон бол trend-г шинэчлэх ---
        if macd_up:
            macd_state[symbol]["trend"] = "UP"
            macd_state[symbol]["uplimit"] = macd_min
            macd_state[symbol]["uplimit_cross_line"] = macd_line.iloc[-2] # ШИНЭ: Огтлолцол үеийн MACD line-г хадгалах
        if macd_down:
            macd_state[symbol]["trend"] = "DOWN"
            macd_state[symbol]["downlimit"] = macd_max
            macd_state[symbol]["downlimit_cross_line"] = macd_line.iloc[-2] # ШИНЭ: Огтлолцол үеийн MACD line-г хадгалах

        # --- ШИНЭ: Буцаах утгыг хадгалсан trend-ээс авах ---
        current_trend = macd_state[symbol].get("trend", "None")

        # --- ЗАСВАР: macd_initial_price-г state-д хадгалж, шинэчилдэг болгох ---
        # 1. Хэрэв state-д анх удаа орж ирж байвал одоогийн үнийг оноох (тестлэхэд хялбар)
        if "macd_initial_price" not in macd_state[symbol]:
            macd_state[symbol]["macd_initial_price"] = float(klines[-1][1]) # Хамгийн сүүлийн нээлтийн үнэ (open0)

        # 2. Хэрэглэгчийн хүссэн онцгой нөхцөлийг шалгах
        try:
            # Нөхцөл 1: Signal шугам 0-г доороос дээш сэтлэх
            cross_above_zero = (macd_signal.iloc[-2] > 0 and 
                                macd_signal.iloc[-3] < 0 and 
                                macd_signal.iloc[-4] < 0)
            
            # Нөхцөл 2: Signal шугам 0-г дээрээс доош сэтлэх (ЭСРЭГ НӨХЦӨЛ)
            cross_below_zero = (macd_signal.iloc[-2] < 0 and 
                                macd_signal.iloc[-3] > 0 and 
                                macd_signal.iloc[-4] > 0)

            # Аль нэг нөхцөл биелбэл initial price-г шинэчлэх
            if cross_above_zero or cross_below_zero:
                # Нөхцөл биелбэл state доторх утгыг шинэчилнэ
                open0 = float(klines[-1][1])
                macd_state[symbol]["macd_initial_price"] = open0

        except IndexError:
            # Хангалттай дата байхгүй үед алдаа заахаас сэргийлнэ
            pass

        # 3. Буцаахдаа state-д хадгалагдсан утгыг ашиглах
        return {
            "line": {
                "0": macd_line.iloc[-1], "-1": macd_line.iloc[-2], "-2": macd_line.iloc[-3], "-3": macd_line.iloc[-4]
            },
            "signal": {
                "0": macd_signal.iloc[-1], "-1": macd_signal.iloc[-2], "-2": macd_signal.iloc[-3], "-3": macd_signal.iloc[-4]
            },
            "hist": {
                "0": macd_hist.iloc[-1], "-1": macd_hist.iloc[-2], "-2": macd_hist.iloc[-3], "-3": macd_hist.iloc[-4]
            },
            "macd_up": current_trend == "UP",
            "macd_down": current_trend == "DOWN",
            "macd_min": macd_min,
            "macd_max": macd_max,
            "macd_uplimit": macd_state[symbol]["uplimit"],
            "macd_downlimit": macd_state[symbol]["downlimit"],
            "uplimit_cross_line": macd_state[symbol]["uplimit_cross_line"], # ШИНЭ: Буцаах утганд нэмэх
            "downlimit_cross_line": macd_state[symbol]["downlimit_cross_line"], # ШИНЭ: Буцаах утганд нэмэх
            "macd_initial_price": macd_state[symbol].get("macd_initial_price") # --- ЗАСВАР: State-ээс утгыг авах ---
        }

    except Exception as e:
        print(f"Error calculating MACD for {symbol}: {e}")
        return None

# --- ЗАСВАР: Локал тестлэх хэсгийг устгах эсвэл коммент болгох ---
# if __name__ == "__main__":
#     # Энэ хэсэг нь зөвхөн локал дээр тестлэхэд зориулагдсан тул
#     # Railway дээр байршуулахад шаардлагагүй.
#     # Мөн `aaa_precision` файлаас хамааралтай тул алдаа заана.
#     main()

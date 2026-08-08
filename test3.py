import pandas as pd
from binance.um_futures import UMFutures

def _get_standalone_client():
    """
    Зөвхөн OHLC мэдээлэл татахад зориулсан, нийтийн API ашигладаг,
    дангаараа ажиллах Binance client үүсгэнэ.
    """
    client = UMFutures()
    client.session.requests_params = {"timeout": 10}
    return client

def get_last_4_ohlc(symbol):
    """
    Тухайн зоосны сүүлийн 4 лааны OHLC мэдээллийг татаж,
    -3, -2, -1, 0 гэсэн индекс бүхий dictionary хэлбэрээр буцаана.
    """
    try:
        client = _get_standalone_client()
        # Binance-аас сүүлийн 4 лааны мэдээллийг татах
        # (klines[0] = хамгийн хуучин, klines[3] = хамгийн шинэ/одоогийн)
        klines = client.klines(symbol=symbol, interval="1m", limit=4)
        if not klines or len(klines) < 4:
            print(f"Warning: {symbol}-н хувьд хангалттай лааны мэдээлэл олдсонгүй.")
            return None

        # --- ЗАСВАР: Логик дараалалтай, ойлгомжтой түлхүүр ашиглах ---
        index_keys = ["-3", "-2", "-1", "0"]
        ohlc_dict = {}
        ohlc_list_for_df = []

        for i in range(4):
            kline = klines[i]
            idx_key = index_keys[i]
            
            candle_data = {
                "open": float(kline[1]),
                "high": float(kline[2]),
                "low": float(kline[3]),
                "close": float(kline[4])
            }
            
            # Дикшнри болон жагсаалтад зэрэг нэмэх
            ohlc_dict[idx_key] = candle_data
            ohlc_list_for_df.append(candle_data)

        # Min/Max утгуудыг тооцоолох DataFrame
        df = pd.DataFrame(ohlc_list_for_df)
        
        return {
            "candles": ohlc_dict,         # "-3", "-2", "-1", "0" гэсэн түлхүүрүүдтэй
            "ohlc_list": ohlc_list_for_df,  # Эрэмбэлэгдсэн жагсаалт
            "min_open": df['open'].min(),
            "max_open": df['open'].max(),
            "min_close": df['close'].min(),
            "max_close": df['close'].max(),
            "max_high": df['high'].max(),
            "min_low": df['low'].min()
        }

    except Exception as e:
        print(f"Error fetching OHLC for {symbol}: {e}")
        return None

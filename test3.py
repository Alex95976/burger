import pandas as pd
from binance.um_futures import UMFutures

def _get_standalone_client():
    """
    Зөвхөн OHLC мэдээлэл татахад зориулсан, нийтийн API ашигладаг,
    дангаараа ажиллах Binance client үүсгэнэ.
    """
    client = UMFutures()
    # Сүлжээнээс болж гацахаас сэргийлж timeout тохируулах
    client.session.requests_params = {"timeout": 10}
    return client

def get_last_4_ohlc(symbol): # --- ЗАСВАР: client параметрийг хасаж, бие даасан болгох ---
    """
    Тухайн зоосны сүүлийн 4 лааны OHLC мэдээллийг татаж,
    нэгтгэсэн dictionary хэлбэрээр буцаана.
    """
    try:
        client = _get_standalone_client() # --- ШИНЭ: Client-г дотроо үүсгэнэ ---
        # Сүүлийн 4 лааны мэдээллийг авах
        klines = client.klines(symbol=symbol, interval="1m", limit=4)
        if not klines or len(klines) < 4:
            print(f"Warning: {symbol}-н хувьд хангалттай лааны мэдээлэл олдсонгүй.")
            return None

        ohlc_data = []
        for kline in reversed(klines): # Сүүлийн лаанаас эхлэх
            ohlc_data.append({
                "open": float(kline[1]),
                "high": float(kline[2]),
                "low": float(kline[3]),
                "close": float(kline[4])
            })

        # Min/Max утгуудыг тооцоолох
        df = pd.DataFrame(ohlc_data)
        return {
            "ohlc_list": ohlc_data,
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

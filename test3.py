import pandas as pd
from binance.um_futures import UMFutures


def _get_standalone_client():
  """Зөвхөн OHLC мэдээлэл татахад зориулсан, нийтийн API ашигладаг,

  дангаараа ажиллах Binance client үүсгэнэ.
  """
  client = UMFutures()
  # Сүлжээнээс болж гацахаас сэргийлж timeout тохируулах
  client.session.requests_params = {"timeout": 10}
  return client


def get_last_4_ohlc(
    symbol,
):  # --- ЗАСВАР: client параметрийг хасаж, бие даасан болгох ---
  """Тухайн зоосны сүүлийн 4 лааны OHLC мэдээллийг татаж,

  нэгтгэсэн dictionary хэлбэрээр буцаана.
  """
  try:
    client = _get_standalone_client()  # --- ШИНЭ: Client-г дотроо үүсгэнэ ---
    # Сүүлийн 4 лааны мэдээллийг авах
    klines = client.klines(symbol=symbol, interval="1m", limit=4)
    if not klines or len(klines) < 4:
      print(f"Warning: {symbol}-н хувьд хангалттай лааны мэдээлэл олдсонгүй.")
      return None

    # RSI, MACD шиг -3, -2, -1, 0 гэсэн түлхүүртэй dict болгох
    ohlc_dict = {}
    ohlc_list_for_df = []  # Min/max олох зорилгоор DataFrame-д ашиглах жагсаалт

    # reversed(klines) хийхэд хамгийн эхний элемент нь 3 минутын өмнөх (-3) лаа байна
    indexes = ["-3", "-2", "-1", "0"]

    for i, kline in enumerate(reversed(klines)):
      idx_key = indexes[i]
      candle_data = {
          "open": float(kline[1]),
          "high": float(kline[2]),
          "low": float(kline[3]),
          "close": float(kline[4]),
      }
      # Динамик байдлаар тус бүрээр нь хадгалах
      ohlc_dict[idx_key] = candle_data
      ohlc_list_for_df.append(candle_data)

    # Min/Max утгуудыг тооцоолох
    df = pd.DataFrame(ohlc_list_for_df)
    return {
        # Жагсаалт хэлбэрээр хэрэгтэй бол
        "ohlc_list": ohlc_list_for_df,
        # MACD, RSI шиг түлхүүр-утга хэлбэрээр хэрэгтэй бол
        "candles": ohlc_dict,
        "min_open": df["open"].min(),
        "max_open": df["open"].max(),
        "min_close": df["close"].min(),
        "max_close": df["close"].max(),
        "max_high": df["high"].max(),
        "min_low": df["low"].min(),
    }

  except Exception as e:
    print(f"Error fetching OHLC for {symbol}: {e}")
    return None

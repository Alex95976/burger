import pandas as pd
import time
from binance.um_futures import UMFutures


def _get_standalone_client():
    client = UMFutures()
    client.session.requests_params = {"timeout": 10}
    return client


def create_ohlc_tracker():
    """
    Лимит утгуудыг зөвхөн чиглэл шинээр өөрчлөгдөх мөчид түгжих Stateful функц.
    """
    last_openup_limit = None
    last_opendown_limit = None
    
    # Өмнөх төлөвийг хадгалах хувьсагчид
    prev_openup = False
    prev_opendown = False

    def get_last_4_ohlc(symbol):
        nonlocal last_openup_limit, last_opendown_limit, prev_openup, prev_opendown
        try:
            client = _get_standalone_client()
            klines = client.klines(symbol=symbol, interval="1m", limit=4)

            if not klines or len(klines) < 4:
                print(f"⚠️ {symbol}: хангалттай candle олдсонгүй.")
                return None

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
                ohlc_dict[idx_key] = candle_data
                ohlc_list_for_df.append(candle_data)

            df = pd.DataFrame(ohlc_list_for_df)

            min_open = df["open"].min()
            max_open = df["open"].max()
            min_close = df["close"].min()
            max_close = df["close"].max()
            max_high = df["high"].max()
            min_low = df["low"].min()

            open0 = ohlc_list_for_df[-1]["open"]
            open1 = ohlc_list_for_df[-2]["open"]

            openup = open0 > open1
            opendown = open0 < open1

            # 💡 ЗӨВХӨН ШИНЭЭР TRUE БОЛОХ МӨЧИД (False -> True) ЛИМИТИЙГ ТҮГЖИХ
            if openup and not prev_openup:
                last_openup_limit = min_open

            if opendown and not prev_opendown:
                last_opendown_limit = max_open

            # Өмнөх төлөвийг шинэчлэх
            prev_openup = openup
            prev_opendown = opendown

            return {
                "candles": ohlc_dict,
                "ohlc_list": ohlc_list_for_df,
                "min_open": min_open,
                "max_open": max_open,
                "min_close": min_close,
                "max_close": max_close,
                "max_high": max_high,
                "min_low": min_low,
                "openup": openup,
                "opendown": opendown,
                "openup_limit": last_openup_limit,     
                "opendown_limit": last_opendown_limit  
            }

        except Exception as e:
            print(f"❌ Error fetching OHLC for {symbol}: {e}")
            return None

    return get_last_4_ohlc

# Функцээ үүсгэх
get_last_4_ohlc = create_ohlc_tracker()

if __name__ == "__main__":
    symbol = "4USDT"

    print(f"🚀 {symbol} OHLC monitor STARTED")
    print("⏱️ 1 секунд тутамд шинэчилнэ.")
    print("🛑 Зогсоох: CTRL + C")

    while True:
        data = get_last_4_ohlc(symbol)

        if data:
            import os
            os.system("cls")

            print("=" * 70)
            print(f"📊 {symbol} | 1m OHLC (Sticky Limits)")
            print("=" * 70)

            print(f"\n🚀 Trend Limits Check:")
            print(f"   openup   = {data['openup']}   --> openup_limit = {data['openup_limit']}")
            print(f"   opendown = {data['opendown']} --> opendown_limit = {data['opendown_limit']}")
            print("-" * 70)

            print("\n🕯️ CANDLES")
            print("-" * 70)

            for idx, candle in data["candles"].items():
                print(
                    f"[{idx}] "
                    f"Open: {candle['open']:g} | "
                    f"High: {candle['high']:g} | "
                    f"Low: {candle['low']:g} | "
                    f"Close: {candle['close']:g}"
                )

            print("\n📈 MIN / MAX")
            print("-" * 70)

            print(f"Min Open  : {data['min_open']:g}")
            print(f"Max Open  : {data['max_open']:g}")
            print(f"Min Close : {data['min_close']:g}")
            print(f"Max Close : {data['max_close']:g}")
            print(f"Max High  : {data['max_high']:g}")
            print(f"Min Low   : {data['min_low']:g}")

            print("\n" + "=" * 70)
            print("🔄 Updating...")

        time.sleep(1)

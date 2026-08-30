# data_percent2.py

import json
import time
from client import get_client
from data_macd import get_initial_price

BASELINE_FILE = "baseline.json"

def read_baseline_json():
    """baseline.json файлаас шинэчлэгдсэн baseline-ийг унших."""
    try:
        with open(BASELINE_FILE, "r", encoding="utf-8") as f:
            content = f.read().strip()
            if not content:
                return {}
            return json.loads(content)
    except (FileNotFoundError, json.JSONDecodeError, UnicodeDecodeError):
        return {}

def initialize_baseline(client):
    """
    Зөвхөн MACD 0-ийн огтлолцлоос олдох initial price-ийг авна. 
    Олдохгүй бол шууд алгасна.
    """
    baseline = {}
    exchange_info = client.exchange_info()

    valid_symbols = [
        s["symbol"]
        for s in exchange_info["symbols"]
        if (
            s["quoteAsset"] == "USDT"
            and s["status"] == "TRADING"
            and s["contractType"] == "PERPETUAL"
        )
    ]

    total_coins = len(valid_symbols)
    print(f"🔄 Нийт {total_coins} зоосны MACD Initial Price baseline-ийг үүсгэж байна...\n")

    for i, symbol in enumerate(valid_symbols, 1):
        print(f"[{i}/{total_coins}] Шалгаж байна: {symbol:<12}", end="\r")
        
        init_price = get_initial_price(symbol)
        
        if init_price is not None and init_price > 0:
            baseline[symbol] = init_price
        
        time.sleep(0.05)

    print("\n")

    try:
        with open(BASELINE_FILE, "w", encoding="utf-8") as f:
            json.dump(baseline, f, indent=2, ensure_ascii=False)
    except Exception:
        pass

    print(f"✅ Baseline initialized with MACD Initial Prices: {len(baseline)} / {total_coins} coins")
    return baseline

def get_percent_change(client, baseline):
    """
    Зөвхөн MACD Initial Price-д суурилсан baseline-ээс хувь өөрчлөлт тооцох
    """
    result = {}
    tickers = client.ticker_price()
    saved_baselines = read_baseline_json()

    # Хэрэв baseline.json хоосон байвал санах ойн baseline-ийг ашиглана
    active_baseline = saved_baselines if saved_baselines else baseline

    for ticker in tickers:
        symbol = ticker["symbol"]

        if symbol not in active_baseline:
            continue

        try:
            start_price = active_baseline[symbol]
            current_price = float(ticker["price"])

            if start_price is None or start_price <= 0:
                continue

            percent = ((current_price - start_price) / start_price) * 100

            result[symbol] = {
                "start_price": start_price,
                "current_price": current_price,
                "percent": percent
            }

        except (ValueError, TypeError, KeyError):
            continue

    return result

def get_top_gainers_n(client, baseline, n=10):
    percent_data = get_percent_change(client, baseline)

    sorted_data = sorted(
        percent_data.items(),
        key=lambda x: x[1]["percent"],
        reverse=True
    )

    top_n = [
        (symbol, data)
        for symbol, data in sorted_data[:n]
        if data["percent"] > 0
    ]

    return top_n

def get_top_losers_n(client, baseline, n=10):
    percent_data = get_percent_change(client, baseline)

    sorted_data = sorted(
        percent_data.items(),
        key=lambda x: x[1]["percent"],
        reverse=False
    )

    top_losers = [
        (symbol, data)
        for symbol, data in sorted_data[:n]
        if data["percent"] < 0
    ]

    return top_losers

def run_scanner(client):
    print("\n==============================")
    print("🚀 BASELINE ҮҮСГЭЖ БАЙНА...")
    print("==============================")

    baseline = initialize_baseline(client)

    print("\n==============================")
    print("📈 USDT-M PERPETUAL SCANNER (.JSON LOG)")
    print("==============================")
    print("🔄 Update: 1 sec | Өөрчлөлт орсон датаг JSON файл руу бичиж байна...\n")

    while True:
        loop_start = time.perf_counter()

        percent_data = get_percent_change(client, baseline)

        sorted_percent_data = sorted(percent_data.items(), key=lambda x: x[0])
        ordered_changed_coins = {symbol: data for symbol, data in sorted_percent_data}

        try:
            with open("market_changes.json", "w", encoding="utf-8") as f:
                json.dump(ordered_changed_coins, f, ensure_ascii=False, indent=4)
        except Exception as e:
            print(f"JSON бичихэд алдаа гарлаа: {e}")

        # Функцүүдийг ашиглаж TOP Gainers болон Losers-ийг авна
        top_gainers = get_top_gainers_n(client, baseline, n=10)
        top_losers = get_top_losers_n(client, baseline, n=10)
        
        changed_coins = [
            symbol
            for symbol, data in percent_data.items()
            if data["percent"] != 0
        ]

        print("\033[H\033[J", end="")
        print("==========================================")
        print("📈 REAL-TIME SCANNER (JSON LOGGED)")
        print("==========================================")
        print(f"🪙 Нийт хөдөлгөөн орсон coin: {len(changed_coins)} / {len(percent_data)}")
        print("💾 Файл руу хадгалагдлаа: market_changes.json\n")

        print("🚀 TOP 10 GAINERS:")
        for symbol, data in top_gainers:
            print(f"  {symbol:<18} {data['current_price']:<14} \033[92m+{data['percent']:.2f}%\033[0m")

        print("\n📉 TOP 10 LOSERS:")
        for symbol, data in top_losers:
            print(f"  {symbol:<18} {data['current_price']:<14} \033[91m{data['percent']:.2f}%\033[0m")

        elapsed = time.perf_counter() - loop_start
        sleep_time = max(0, 1.0 - elapsed)
        time.sleep(sleep_time)

if __name__ == "__main__":
    client = get_client()

    if not client:
        print("❌ Binance client үүссэнгүй")
        exit()

    try:
        run_scanner(client)
    except KeyboardInterrupt:
        print("\n\n🛑 Scanner stopped.")
    except Exception as e:
        print(f"\n🔥 Scanner error: {e}")

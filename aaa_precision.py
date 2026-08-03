from binance.um_futures import UMFutures
import os
import json

client = UMFutures()
_cache = {}

def get_active_coins():
    if not os.path.exists("active.json"):
        return ["BTCUSDT"]

    with open("active.json", "r", encoding="utf-8") as f:
        data = json.load(f)

    coins = data.get("active", [])

    return coins if coins else ["BTCUSDT"]

def get_precision(symbol):
    if symbol in _cache:
        return _cache[symbol]

    info = client.exchange_info()

    for s in info["symbols"]:
        if s["symbol"] == symbol:
            _cache[symbol] = s["pricePrecision"]
            return _cache[symbol]

    return 8

def format_price(price, symbol):
    precision = get_precision(symbol)
    return f"{price:.{precision}f}".rstrip("0").rstrip(".")
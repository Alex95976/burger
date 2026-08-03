import asyncio
import aiohttp
import traceback
import os
import time
import hmac
import hashlib
from aaa_precision import get_active_coins

def process_leverage_brackets(leverage_brackets_data):
    """
    Өгөгдсөн leverage bracket датаг боловсруулж, символ тус бүрийн
    хамгийн их хөшүүргийг буцаана.
    :param leverage_brackets_data: /fapi/v1/leverageBracket-аас ирсэн түүхий дата (list of dicts).
    :return: {'SYMBOL': max_leverage} гэсэн dict.
    """
    leverage_data = {}
    if not leverage_brackets_data:
        return leverage_data
        
    for item in leverage_brackets_data:
        symbol = item.get('symbol')
        if symbol and symbol.endswith('USDT') and item.get('brackets'):
            leverage_data[symbol] = max(b['initialLeverage'] for b in item['brackets'])
    return leverage_data

async def get_max_leverage(session, api_key, api_secret, symbol=None):
    """
    Нэг эсвэл бүх зоосны хамгийн их хөшүүргийг татна.
    :param symbol: Хэрэв None бол бүх зоосны мэдээллийг татна.
    """
    lvr_url = "https://fapi.binance.com/fapi/v1/leverageBracket"
    ts = int(time.time() * 1000)
    
    params = {"timestamp": ts}
    if symbol:
        params['symbol'] = symbol

    query = '&'.join([f"{k}={v}" for k, v in params.items()])
    
    signature = hmac.new(
        api_secret.encode('utf-8'),
        query.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()

    headers = {"X-MBX-APIKEY": api_key}
    full_url = f"{lvr_url}?{query}&signature={signature}"
    
    async with session.get(full_url, headers=headers) as response:
        if response.status == 200:
            data = await response.json()
            # Нэг зоосны мэдээлэл [dict] хэлбэрээр, олон бол list of dicts хэлбэрээр ирдэг.
            return process_leverage_brackets(data if isinstance(data, list) else [data])
        else:
            print(f"Error fetching leverage data: HTTP {response.status}, Response: {await response.text()}")
            return {}

async def main():
    """
    Binance Futures дээрх бүх USDT хослолтой койны зөвшөөрөгдсөн
    хамгийн их хөшүүргийг (max leverage) татаж харуулна.
    """
    api_key = os.getenv("BINANCE_API_KEY")
    api_secret = os.getenv("BINANCE_API_SECRET")

    if not api_key or not api_secret:
        print("🔥 CRITICAL ERROR: Binance API key эсвэл secret олдсонгүй.")
        print("   Системийн environment variables-д BINANCE_API_KEY, BINANCE_API_SECRET утгуудаа тохируулна уу.")
        return

    # active.json-оос идэвхтэй зооснуудыг авах
    active_coins = get_active_coins()

    try:
        print("Fetching leverage brackets for all symbols...")
        
        async with aiohttp.ClientSession() as session:
            leverage_data = await get_max_leverage(session, api_key, api_secret)

        # Зөвхөн active.json-д байгаа зооснуудыг шүүж авах
        filtered_leverage_data = {
            symbol: leverage for symbol, leverage in leverage_data.items() if symbol in active_coins
        }

        print("-" * 40)
        print(f"Found max leverage for {len(filtered_leverage_data)} active USDT symbols:")
        print(f"{'#': >4}  {'Symbol': <15} {'Max Leverage'}")
        print("-" * 40)

        for i, symbol in enumerate(sorted(filtered_leverage_data.keys())):
            leverage = filtered_leverage_data[symbol]
            print(f"{i+1: >4}: {symbol: <15} {leverage}x")

    except Exception as e:
        print(f"An error occurred: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
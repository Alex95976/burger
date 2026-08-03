import os
import threading
import traceback
from binance.um_futures import UMFutures
from binance.error import ClientError
import math
import time

# --- ШИНЭ: Бусад файлуудаас функц импортлох ---
from aaa_min import get_trade_rules as get_min_rules
from aaa_lvr import get_max_leverage

def get_client(api_key=None, api_secret=None):
    """
    Binance API client үүсгэх.
    Хэрэв түлхүүрүүд өгөгдөөгүй бол .env файлаас уншихыг оролдоно.
    """
    if not api_key:
        api_key = os.getenv("BINANCE_API_KEY")
    if not api_secret:
        api_secret = os.getenv("BINANCE_API_SECRET")
    
    if not api_key or not api_secret:
        print("🔥 CRITICAL ERROR: Missing Binance API keys")
        return None

    # --- ЗАСВАР: `requests_params` нь constructor-ийн параметр биш ---
    # Client-г үүсгэсний дараа session-д нь тохиргоог хийж өгнө.
    client = UMFutures(key=api_key, secret=api_secret)
    
    # API дуудлага бүрт 10 секундын timeout тохируулах.
    # Програм сүлжээнээс болж гацахаас сэргийлнэ.
    client.session.requests_params = {"timeout": 10}

    return client

# --- ЗАСВАР: Глобал client-ийн оронд функцүүд client-г параметрээр авна ---
# client = get_client()

# --- ШИНЭ: Symbol-ийн дүрмийг хадгалах кэш ---
symbol_rules_cache = {}
cache_lock = threading.Lock()

# Сүүлд ордер хийсэн цагийг хадгалах dictionary
last_order_time = {}

def safe_order(client, symbol, side, positionSide, order_type, qty, cooldown_seconds=5, info=None):
    """Ордерыг алдаанаас хамгаалж, cooldown-тай илгээх нэгдсэн функц."""
    if not client:
        print(f"🔥 ORDER BLOCKED: No API client available for {symbol}")
        return None
    if qty <= 0:
        print(f"🔥 ORDER BLOCKED: Non-positive qty for {symbol}: {qty}")
        return None
    now = time.time()
    if now - last_order_time.get(symbol, 0) < cooldown_seconds:
        print(f"🔁 ORDER COOLDOWN: Skipping order for {symbol} (last {now - last_order_time.get(symbol,0):.1f}s ago)")
        return None # 5 секунд болоогүй бол ордер явуулахгүй

    # ЗАСВАР: info-г функцийн параметрээр шууд авна, get_symbol_info-г дуудахгүй.
    if not info:
        print(f"🔥 ORDER BLOCKED: Symbol info (lvr, step_size) was not provided for {symbol}.")
        return None

    # --- ЗАСВАР: Notional шалгалтыг тоймлосны дараа хийх ---
    # Эхлээд qty-г тоймлоно.
    rounded_qty = round_to_step(qty, info['step_size'])
    if rounded_qty <= 0:
        print(f"🔥 WARNING: Quantity for {symbol} became 0 after rounding. Original: {qty}, step: {info.get('step_size')}")
        return None

    # Дараа нь тоймлосон qty-г ашиглан notional үнийн дүнг тооцоолно.
    current_price = info.get('current_price', 0) # get_symbol_rules-аас үнийг авна
    notional_value = rounded_qty * current_price

    # --- ШИНЭЧИЛСЭН ХӨШҮҮРГИЙН ЛОГИК ---
    # 1. Хөшүүргийг market_buren.py-аас ирсэн мэдээллээс авах
    target_leverage = info.get('lvr')
    if target_leverage is None:
        print(f"🔥 ORDER BLOCKED: Leverage info not found for {symbol} in symbol data.")
        return None
    
    # 2. Хөшүүргийн дүрмийг хэрэгжүүлэх (10-аас багаг блоклох, 20-оос ихийг 20 болгох)
    if target_leverage < 10:
        print(f"🔥 ORDER BLOCKED: Leverage for {symbol} is {target_leverage}x, which is less than 10x.")
        return None
    
    target_leverage = min(target_leverage, 20) # 20-оос их байвал 20 болгох

    try:
        print(f"ORDER: {symbol} | {side} {positionSide} | Qty: {rounded_qty} | Lvr: {target_leverage}x")
        # --- ЗАСВАР: Хөшүүргийг ордер явуулахын өмнө тохируулах ---
        change_leverage(client, symbol, target_leverage)

        result = client.new_order(symbol=symbol, side=side, positionSide=positionSide, type=order_type, quantity=rounded_qty)
        last_order_time[symbol] = now # Цагийг шинэчлэх
        return result
    except ClientError as e:
            # -2022: ReduceOnly Order is rejected. This means the position is already closed.
            if e.error_code == -2022:
                print(f"✅ {symbol}: Position likely already closed. Returning error for state sync.")
                return {"error_code": e.error_code, "error_message": e.error_message}

            # Бусад төрлийн ClientError-г хэвлээд зогсох
            print(f"🔥 ORDER ERROR: {side} {symbol} ({e.status_code}, {e.error_code}, '{e.error_message}')")
            traceback.print_exc()
            return None

    except Exception as e:
        print(f"🔥 UNEXPECTED ERROR on {side} {symbol}: {e}")
        traceback.print_exc()
        return None
def open_long_position(client, symbol, qty, info):
    return safe_order(
        client=client, symbol=symbol,
        side="BUY",
        positionSide="LONG",
        order_type="MARKET",
        qty=qty, # Үржүүлэх логикийг эндээс шууд дамжуулна
        info=info
    )

def open_short_position(client, symbol, qty, info):
    # Үржүүлэх логикийг эндээс шууд дамжуулна
    return safe_order(
        client=client, symbol=symbol,
        side="SELL",
        positionSide="SHORT",
        order_type="MARKET",
        qty=qty,
        info=info
    )

def close_long_position(client, symbol, qty, info):
    # ЗАСВАР: Позиц хаах үед үржүүлэхгүй, зөвхөн одоо байгаа хэмжээгээр хаана.
    # Cooldown хэрэггүй тул 0 болгож дамжуулна.
    return safe_order(
        client=client, symbol=symbol,
        side="SELL",
        positionSide="LONG",
        order_type="MARKET",
        qty=qty,
        cooldown_seconds=0,
        info=info
    )

def close_short_position(client, symbol, qty, info):
    # ЗАСВАР: Позиц хаах үед үржүүлэхгүй.
    return safe_order(
        client=client, symbol=symbol,
        side="BUY",
        positionSide="SHORT",
        order_type="MARKET",
        qty=qty,
        cooldown_seconds=0,
        info=info
    )

def get_open_positions(client):
    if not client:
        return {}

    try:
        positions = client.get_position_risk()
        open_positions = {}

        for p in positions:
            if float(p["positionAmt"]) != 0:
                key = f"{p['symbol']}_{p['positionSide']}"
                open_positions[key] = p
        return open_positions
    except Exception as e:
        print(f"🔥 Error fetching open positions: {e}")
        return {}

def round_to_step(qty, step):
    """Тоог өгөгдсөн step_size-д тааруулж тоймлоно."""
    if step is None or step <= 0:
        return qty
    # step_size-ийн нарийвчлалыг (аравтын орны тоо) олох
    precision = 0
    if "." in str(step):
        precision = len(str(step).split(".")[1].rstrip("0"))
    return round(math.floor(qty / step) * step, precision)

def get_symbol_rules(client, symbol):
    """
    Binance-ээс тухайн зоосны арилжааны дүрмийг (lvr, step_size, min_qty, min_notional)
    татаж, кэшлээд буцаах функц.
    """
    with cache_lock:
        if symbol in symbol_rules_cache:
            return symbol_rules_cache[symbol]

    if not client:
        print(f"🔥 RULES ERROR: No client provided for fetching {symbol} rules.")
        return None

    try:
        # 1. Арилжааны доод хэмжээ, step_size-г aaa_min.py-аас авах
        min_rules = get_min_rules(client, symbol)
        if not min_rules:
            print(f"🔥 RULES ERROR: Could not fetch min trade rules for {symbol}.")
            return None

        # --- ШИНЭ: Үнийг дүрмийн хамт буцаах ---
        current_price = float(client.ticker_price(symbol=symbol)['price'])


        # 2. Хөшүүргийг aaa_lvr.py-аас авах (python-binance-ийн client-г ашиглана)
        brackets = client.leverage_brackets(symbol=symbol)
        lvr = max(b['initialLeverage'] for b in brackets[0]['brackets']) if brackets else 20

        # 3. Бүх дүрмийг нэгтгэх
        all_rules = {
            'lvr': lvr,
            'step_size': min_rules['step_size'],
            'min_coin': min_rules['min_coin'],
            'min_usdt': min_rules['min_usdt'],
            'current_price': current_price # Ордерын notional шалгахад хэрэгтэй
        }

        # Кэш-д хадгалах
        with cache_lock:
            symbol_rules_cache[symbol] = all_rules

        return all_rules

    except Exception as e:
        print(f"🔥 RULES ERROR: Unexpected error fetching rules for {symbol}: {e}")
        traceback.print_exc()
        return None


def get_order_status(client, symbol, order_id):
    if not client:
        return {}

    try:
        return client.query_order(symbol=symbol, orderId=order_id)
    except Exception as e:
        print(f"🔥 Error getting order status for {symbol} (ID: {order_id}): {e}")
        return {}

def change_leverage(client, symbol, leverage):
    """
    Хөшүүргийг өөрчлөх. Хэрэв аль хэдийн зөв байвал юу ч хийхгүй.
    """
    try:
        if client:
            positions = client.get_position_risk(symbol=symbol)
            if positions:
                # Хэрэв нээлттэй позиц байхгүй бол 'leverage' key байхгүй байж болно.
                # Энэ тохиолдолд шууд leverage-г тохируулахыг оролдоно.
                current_leverage_str = positions[0].get('leverage')
                if current_leverage_str and int(current_leverage_str) == leverage:
                    return True # Хөшүүрэг аль хэдийн зөв байвал юу ч хийхгүй.
            client.change_leverage(symbol=symbol, leverage=leverage)
            return True
    except Exception as e:
        print(f"🔥 Failed to change leverage for {symbol}: {e}")
        return False
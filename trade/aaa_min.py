from binance.um_futures import UMFutures
import traceback
import math

from aaa_precision import get_active_coins
def format_value(value, precision=8):
    """
    Тоон утгыг цэгцтэй форматлах функц.
    Илүүдэл тэгүүдийг арилгана.
    """
    try:
        s = f"{float(value):.{precision}f}"
        if '.' in s:
            s = s.rstrip('0').rstrip('.')
        return s
    except (ValueError, TypeError):
        return str(value)

def get_trade_rules(client, symbol):
    """Нэг зоосны арилжааны дүрмийг тооцоолж буцаана."""
    try:
        # API дуудлагыг тоолох
        exchange_info = client.exchange_info()
        # API дуудлагыг тоолох
        current_price = float(client.ticker_price(symbol=symbol)['price'])

        symbol_info = next((s for s in exchange_info['symbols'] if s['symbol'] == symbol), None)

        if not symbol_info:
            return None

        filters = {f['filterType']: f for f in symbol_info.get('filters', [])}
        lot_size_filter = filters.get('LOT_SIZE', {})
        min_notional_val = float(filters.get('MIN_NOTIONAL', {}).get('notional') or \
                                   filters.get('NOTIONAL', {}).get('notional') or 0.0)

        min_coin_qty = float(lot_size_filter.get('minQty', 0))
        step_size = float(lot_size_filter.get('stepSize', 0))

        effective_min_coin = min_coin_qty
        if current_price > 0 and min_notional_val > 0:
            qty_for_notional = min_notional_val / current_price
            if step_size > 0:
                qty_for_notional = math.ceil(qty_for_notional / step_size) * step_size
            effective_min_coin = max(min_coin_qty, qty_for_notional)

        return {
            'min_coin': effective_min_coin,
            'min_usdt': effective_min_coin * current_price,
            'step_size': step_size
        }
    except Exception:
        return None

def main():
    """
    Binance Futures-аас бүх USDT хослолтой койны арилжааны доод
    хэмжээ (Min Coin) болон доод үнийн дүнг (Min USDT) татаж харуулна.
    """
    try:
        client = UMFutures()
        print("Fetching exchange information from Binance Futures...")
        
        # API дуудлагыг тоолох
        exchange_info = client.exchange_info()

        # --- ЗАСВАР: Койнуудын одоогийн ханшийг татах ---
        # API дуудлагыг тоолох
        all_prices = {p['symbol']: float(p['price']) for p in client.ticker_price()}

        # active.json-оос идэвхтэй зооснуудыг авах
        active_coins = get_active_coins()

        trade_rules = {}

        # `main` функц нь одоо get_trade_rules-г ашиглан зоос бүрийн мэдээллийг авна
        for symbol in active_coins:
            rules = get_trade_rules(client, symbol)
            if rules:
                trade_rules[symbol] = rules
            else:
                print(f"Could not fetch rules for {symbol}")

        print("-" * 50)
        print(f"{'#': >4}  {'Symbol': <15} {'Min Coin': >15} {'Min USDT ($)'}")
        print("-" * 50)

        for i, symbol in enumerate(sorted(trade_rules.keys())):
            rules = trade_rules[symbol]
            min_coin_str = format_value(rules['min_coin']).rjust(15)
            print(f"{i+1: >4}: {symbol: <15} {min_coin_str} {rules['min_usdt']: >12.2f}")

    except Exception as e:
        print(f"An error occurred: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    main()
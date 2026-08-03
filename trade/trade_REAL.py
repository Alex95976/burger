import json
import math
import sys
import time
import os
# --- ШИНЭЧЛЭЛТ: Бүх мэдээллийг main_data.py-аас авна ---
from aaa_main_data import get_all_data
from aaa_client import ( # client.py-аас бүх зүйлээ авна
    get_client, get_order_status, get_symbol_rules, round_to_step
)

# --- ШИНЭЧЛЭЛТ: Идэвхтэй зоосыг aaa_precision-оос авна ---
from aaa_precision import get_active_coins

# --- ШИНЭ: Төлөвийг класс ашиглан удирдах ---
from trade_station import PositionState

# --- ШИНЭ: Арилжааны нөхцөлийг тусдаа файлаас импортлох ---
from condition import get_main_trade_conditions

# --- ШИНЭ: Шимтгэлийн хувь ---
FUTURES_TAKER_FEE = 0.0005

# --- ШИНЭ: Төлөв хадгалах файлын нэр ---
TRADE_STATE_FILE = "trade.json"

# --- ШИНЭ: Төлөв хадгалах, сэргээх функц ---
def save_state():
    """Одоогийн арилжааны төлвийг trade.json файлд хадгалах."""
    try:
        with open(TRADE_STATE_FILE, 'w') as f:
            # PositionState object-уудыг dictionary болгож хадгалах
            data_to_save = {symbol: state.__dict__ for symbol, state in open_positions.items()}
            json.dump(data_to_save, f, indent=4)
    except Exception as e:
        print(f"\n🔥 ERROR: Could not save state to {TRADE_STATE_FILE}: {e}")

def load_state():
    """Хэрэв trade.json файл байвал арилжааны төлвийг уншиж сэргээх."""
    global open_positions
    if os.path.exists(TRADE_STATE_FILE):
        try:
            with open(TRADE_STATE_FILE, 'r') as f:
                loaded_data = json.load(f)
                # Dictionary-аас PositionState object-уудыг сэргээх
                for symbol, state_dict in loaded_data.items():
                    state = PositionState()
                    state.__dict__.update(state_dict)
                    open_positions[symbol] = state
                print(f"\n✅ State loaded from {TRADE_STATE_FILE}. Found state for {len(open_positions)} symbol(s).")
        except Exception as e:
            print(f"\n🔥 ERROR: Could not load state from {TRADE_STATE_FILE}, starting fresh. Error: {e}")
            open_positions = {}

open_positions = {}

# --- ШИНЭ: Binance client-г үүсгэх ---
api_key = os.getenv("BINANCE_API_KEY")
api_secret = os.getenv("BINANCE_API_SECRET")
client = get_client(api_key, api_secret)
if not client:
    print("FATAL: Could not initialize Binance client. Exiting.")
    sys.exit(1)

def log_position_state(current_symbol, current_price, data_for_conditions={}):
    """
    Нээлттэй позицуудын мэдээллийг терминал дээр цэвэрлэж, шинээр хэвлэнэ.
    """
    os.system('cls' if os.name == 'nt' else 'clear')
    
    log_output = []
    timestamp = time.strftime('%H:%M:%S')
    
    # Одоо шалгаж буй зоос болон нийт позицын тоог харуулах
    long_count = sum(1 for pos in open_positions.values() if pos.long_opened)
    short_count = sum(1 for pos in open_positions.values() if pos.short_opened)
    log_output.append(f"✅ [{timestamp}] Processing: {current_symbol:<12s} | Price: {current_price:<10} | Open Pos: L({long_count}) S({short_count})")
    log_output.append("-" * 80)

    # Зөвхөн нээлттэй позицтой зооснуудыг шүүж, эрэмбэлэх
    open_symbols = {s: d for s, d in open_positions.items() if d.long_opened or d.short_opened}

    if open_symbols:
        for symbol in sorted(open_symbols.keys()):
            state = open_symbols[symbol]
            # Тухайн зоосны одоогийн үнийг авах (зөвхөн лог хэвлэх үед)
            price_for_pnl = all_prices.get(symbol, 0)

            log_output.append(f"==================== STATE FOR {symbol} =====================")
            total_long_pnl = sum(
                (all_prices.get(s, 0) - pos['entry_price']) * pos['qty']
                for s, st in open_positions.items() for pos in st.long_positions if pos['entry_price'] > 0
            )
            total_short_pnl = sum(
                (pos['entry_price'] - all_prices.get(s, 0)) * pos['qty']
                for s, st in open_positions.items() for pos in st.short_positions if pos['entry_price'] > 0
            )
            total_pnl = total_long_pnl + total_short_pnl
            pnl_str_simple = f"Total PnL: ${total_pnl:+.2f}"
            log_output.append(f"  [INFO] Positions: L({len(state.long_positions)}) S({len(state.short_positions)}) | {pnl_str_simple}") # OK? L/S-г эндээс хассан
            
            # --- ШИНЭ: Олон позицыг тус бүрт нь харуулах ---
            for i, pos in enumerate(state.long_positions):
                pnl = (price_for_pnl - pos['entry_price']) * pos['qty'] if price_for_pnl > 0 and pos['entry_price'] > 0 else 0.0
                pnl_percent = (pnl / (pos['entry_price'] * pos['qty'])) * 100 if pos['entry_price'] * pos['qty'] > 0 else 0.0
                log_output.append(f"  [L-{i+1}] QTY: {pos['qty']:.4f}, Entry: {pos['entry_price']}, PnL: ${pnl:.2f} ({pnl_percent:+.2f}%)")
            
            for i, pos in enumerate(state.short_positions):
                pnl = (pos['entry_price'] - price_for_pnl) * pos['qty'] if price_for_pnl > 0 and pos['entry_price'] > 0 else 0.0
                pnl_percent = (pnl / (pos['entry_price'] * pos['qty'])) * 100 if pos['entry_price'] * pos['qty'] > 0 else 0.0
                log_output.append(f"  [S-{i+1}] QTY: {pos['qty']:.4f}, Entry: {pos['entry_price']}, PnL: ${pnl:.2f} ({pnl_percent:+.2f}%)")

            log_output.append("============================================================")
    
    # --- ХҮСЭЛТИЙН ДАГУУ: Яг одоо шалгаж буй зоосны нөхцөлийн утгуудыг ҮРГЭЛЖ хэвлэх ---
    if data_for_conditions:
        # --- ХҮСЭЛТИЙН ДАГУУ: long_ok, short_ok-г энд нэмж харуулах ---
        current_state = data_for_conditions.get("state")
        if current_state:
            log_output.append(f"  [OK? L/S]           : {current_state.long_ok} / {current_state.short_ok}")
        # --- /ХҮСЭЛТИЙН ДАГУУ ---
        log_output.append(f"========== CONDITION STATES FOR {current_symbol} ==========")
        macd_up = data_for_conditions.get('macd_up')
        macd_down = data_for_conditions.get('macd_down')
        macd_min = data_for_conditions.get('macd_min')
        macd_max = data_for_conditions.get('macd_max')
        macd_uplimit = data_for_conditions.get('macd_uplimit')
        macd_downlimit = data_for_conditions.get('macd_downlimit')
        uplimit_cross = data_for_conditions.get('uplimit_cross_line')
        downlimit_cross = data_for_conditions.get('downlimit_cross_line')
        log_output.append(f"  MACD Up/Down        : {macd_up} / {macd_down}")
        log_output.append(f"  MACD Min/Max        : {macd_min} / {macd_max}")
        log_output.append(f"  MACD UpLimit        : {macd_uplimit}")
        log_output.append(f"  MACD DownLimit      : {macd_downlimit}")
        log_output.append(f"  Uplimit Cross Line  : {uplimit_cross}")
        log_output.append(f"  Downlimit Cross Line: {downlimit_cross}")
        log_output.append("============================================================")

    print("\n".join(log_output))

def run_strategy(symbol, candle_data):
    """candle.py-аас ирсэн мэдээлэлд үндэслэн хедж арилжааны логикийг гүйцэтгэх."""

    # --- АРИЛЖААНЫ ЛОГИК ---
    if symbol not in open_positions:
        open_positions[symbol] = PositionState()

    state = open_positions[symbol]

    # Мэдээлэл задлах
    price = candle_data.get("price")
    last_status = candle_data.get("last_status")
    status = candle_data.get("status", {}) # status object-г авна
    status_30U = status.get("rsi_30_up")
    status_30D = status.get("rsi_30_down")
    status_70U = status.get("rsi_70_up")
    status_70D = status.get("rsi_70_down")
    prev_status_30D = status.get("rsi_30_down_prev") # Өмнөх утгыг авах
    prev_status_30U = status.get("rsi_30_up_prev") # Өмнөх утгыг авах
    max_u = candle_data.get("MAXU")
    min_d = candle_data.get("MIND")
    rsi_data = candle_data.get("rsi", {})
    rsi0 = rsi_data.get("0")
    ohlc_data = candle_data.get("ohlc", {}).get("open", {})
    open0 = ohlc_data.get("0")
    open1 = ohlc_data.get("-1")
    macd_data = candle_data.get("macd", {})
    macd_line = macd_data.get("line", {})
    macd_signal = macd_data.get("signal", {})
    macd_hist = macd_data.get("hist", {})
    macd_up = macd_data.get("macd_up")
    macd_down = macd_data.get("macd_down")
    macd_min = macd_data.get("macd_min")
    macd_max = macd_data.get("macd_max")
    macd_uplimit = macd_data.get("macd_uplimit")
    macd_downlimit = macd_data.get("macd_downlimit")
    uplimit_cross_line = macd_data.get("uplimit_cross_line") # ШИНЭ
    downlimit_cross_line = macd_data.get("downlimit_cross_line") # ШИНЭ

    info = get_symbol_rules(client, symbol)

    if not all([price, last_status, info]):
        return

    min_coin_qty = info.get('min_coin', 0)
    step_size = info.get('step_size', 0)
    
    # --- ЗАСВАР: QTY тооцоолох логикийг энд төвлөрүүлэх ---
    # Арилжааны доод хэмжээнээс 20% илүүгээр ордер нээнэ
    qty = round_to_step(min_coin_qty * 1.2, step_size)
    if qty <= 0:
        return

    # --- ШИНЭ: long_ok, short_ok-г MACD трендээр шинэчлэх ---
    if macd_down and state.long_ok: # Тренд дээшээ бол long нээх боломжтой
        state.long_ok = False
    if macd_up and state.short_ok: # Тренд доошоо бол short нээх боломжтой
        state.short_ok = False

    # --- ШИНЭ: long_ok, short_ok-г MACD трендээр шинэчлэх ---
    if macd_down and state.long_ok2: # Тренд дээшээ бол long нээх боломжтой
        state.long_ok2 = False
    if macd_up and state.short_ok2: # Тренд доошоо бол short нээх боломжтой
        state.short_ok2 = False

    # --- ХҮСЭЛТИЙН ДАГУУ: Нийт long/short позицын тоог тооцоолох ---
    # Энэ нь condition.py-д ашиглагдана
    total_long_positions = sum(len(pos.long_positions) for pos in open_positions.values())
    total_short_positions = sum(len(pos.short_positions) for pos in open_positions.values())

    # --- ХҮСЭЛТИЙН ДАГУУ: PnL-г тооцоолж, condition руу дамжуулах ---
    # --- ШИНЭ: Хамгийн их ашигтай позицыг олох ---
    max_long_pnl = -float('inf')
    max_long_pnl_idx = -1
    for idx, pos in enumerate(state.long_positions):
        pnl = (price - pos['entry_price']) * pos['qty']
        # Шимтгэлийг хасах (нээх, хаах нийт 2 удаа)
        fee = (pos['entry_price'] * pos['qty'] + price * pos['qty']) * FUTURES_TAKER_FEE
        net_pnl = pnl - fee
        if net_pnl > max_long_pnl:
            max_long_pnl = net_pnl
            max_long_pnl_idx = idx

    max_short_pnl = -float('inf')
    max_short_pnl_idx = -1
    for idx, pos in enumerate(state.short_positions):
        pnl = (pos['entry_price'] - price) * pos['qty']
        # Шимтгэлийг хасах (нээх, хаах нийт 2 удаа)
        fee = (pos['entry_price'] * pos['qty'] + price * pos['qty']) * FUTURES_TAKER_FEE
        net_pnl = pnl - fee
        if net_pnl > max_short_pnl:
            max_short_pnl = net_pnl
            max_short_pnl_idx = idx

    # Хэрэв ашигтай позиц байхгүй бол PnL-г 0 гэж үзнэ
    long_pnl_to_check = max_long_pnl if max_long_pnl > -float('inf') else 0.0
    short_pnl_to_check = max_short_pnl if max_short_pnl > -float('inf') else 0.0

    # --- ШИНЭ: Арилжааны нөхцөлийг condition.py-аас авах ---
    # Нөхцөл шалгах функцэд дамжуулах бүх мэдээллийг нэгтгэх
    data_for_conditions = {
        "state": state,
        "last_status": last_status,
        "min_d": min_d,
        "max_u": max_u,
        "macd_up": macd_up,
        "macd_down": macd_down,
        "macd_line": macd_line,
        "macd_min": macd_min,
        "macd_max": macd_max,
        "macd_uplimit": macd_uplimit,
        "macd_downlimit": macd_downlimit,
        "uplimit_cross_line": uplimit_cross_line, # ШИНЭ
        "downlimit_cross_line": downlimit_cross_line, # ШИНЭ
        "long_pnl": long_pnl_to_check,     # Хамгийн их ашигтай Long PnL-г дамжуулах
        "short_pnl": short_pnl_to_check,    # Хамгийн их ашигтай Short PnL-г дамжуулах
        "long_ok": state.long_ok, # ШИНЭ: long_ok-г дамжуулах
        "short_ok": state.short_ok, # ШИНЭ: short_ok-г дамжуулах
        "long_ok2": state.long_ok2, # ШИНЭ: long_ok-г дамжуулах
        "short_ok2": state.short_ok2, # ШИНЭ: short_ok-г дамжуулах
        "total_longs": total_long_positions,   # ЗАСВАР: Тухайн зоосны long-ийн тоог дамжуулах
        "total_shorts": total_short_positions  # ЗАСВАР: Тухайн зоосны short-ийн тоог дамжуулах
    }
    conditions = get_main_trade_conditions(data_for_conditions)
    long_open1 = conditions["long_open1"]
    long_close1 = conditions["long_close1"]
    short_open1 = conditions["short_open1"]
    short_close1 = conditions["short_close1"]
    long_open2 = conditions["long_open2"]
    long_close2 = conditions["long_close2"]
    short_open2 = conditions["short_open2"]
    short_close2 = conditions["short_close2"]

    # --- ЗАСВАР: Эхлээд хаах, дараа нь нээх логикийг шалгах ---
    # --- CLOSE LOGIC ---
    if long_close1 or long_close2:
        print(f"\n[CLOSE LONG] {symbol} at {price} (Status: 30D)")
        if max_long_pnl_idx != -1:
            pos_to_close = state.long_positions[max_long_pnl_idx]
            info['current_price'] = price
            res = (client, symbol, pos_to_close['qty'], info)
            if res:
                state.remove_long(max_long_pnl_idx)
                state.long_ok = False
                save_state()
                print(f"✅ SUCCESS: Closed LONG for {symbol}.")

    if short_close1 or short_close2:
        print(f"\n[CLOSE SHORT] {symbol} at {price} (Status: 70U)")
        if max_short_pnl_idx != -1:
            pos_to_close = state.short_positions[max_short_pnl_idx]
            info['current_price'] = price
            res = (client, symbol, pos_to_close['qty'], info)
            if res:
                state.remove_short(max_short_pnl_idx)
                state.short_ok = False
                save_state()
                print(f"✅ SUCCESS: Closed SHORT for {symbol}.")

    # --- OPEN LOGIC ---
    if long_open1:
        print(f"\n[OPEN LONG] {symbol} at {price} (Status: 30U)")
        info['current_price'] = price
        res = (client, symbol, qty, info)
        if res and "orderId" in res:
            final = get_order_status(client, symbol, res["orderId"])
            if final.get("avgPrice"):
                entry_price = float(final.get("avgPrice", price))
                executed_qty = float(final.get("executedQty", qty))
                state.add_long(entry_price, executed_qty, res["orderId"])
                state.long_ok = True
                print(f"✅ SUCCESS: Added LONG for {symbol} | Qty: {executed_qty} | Entry: {entry_price}")
                save_state()

    if long_open2:
        print(f"\n[OPEN LONG] {symbol} at {price} (Status: 30U)")
        info['current_price'] = price
        res = (client, symbol, qty, info)
        if res and "orderId" in res:
            final = get_order_status(client, symbol, res["orderId"])
            if final.get("avgPrice"):
                entry_price = float(final.get("avgPrice", price))
                executed_qty = float(final.get("executedQty", qty))
                state.add_long(entry_price, executed_qty, res["orderId"])
                state.long_ok2 = True
                print(f"✅ SUCCESS: Added LONG for {symbol} | Qty: {executed_qty} | Entry: {entry_price}")
                save_state()

    if short_open1:
        print(f"\n[OPEN SHORT] {symbol} at {price} (Status: 70D)")
        info['current_price'] = price
        res = (client, symbol, qty, info) # info-г дамжуулна
        if res and "orderId" in res:

            final = get_order_status(client, symbol, res["orderId"])
            if final.get("avgPrice"):
                entry_price = float(final.get("avgPrice", price))
                executed_qty = float(final.get("executedQty", qty))
                state.add_short(entry_price, executed_qty, res["orderId"])
                state.short_ok = True
                print(f"✅ SUCCESS: Added SHORT for {symbol} | Qty: {executed_qty} | Entry: {entry_price}")
                save_state()
    if short_open2:
        print(f"\n[OPEN SHORT] {symbol} at {price} (Status: 70D)")
        info['current_price'] = price
        res = (client, symbol, qty, info)
        if res and "orderId" in res:
            final = get_order_status(client, symbol, res["orderId"])
            if final.get("avgPrice"):
                entry_price = float(final.get("avgPrice", price))
                executed_qty = float(final.get("executedQty", qty))
                state.add_short(entry_price, executed_qty, res["orderId"])
                state.short_ok2 = True
                print(f"✅ SUCCESS: Added SHORT for {symbol} | Qty: {executed_qty} | Entry: {entry_price}")
                save_state()

    # --- ЗАСВАР: Лог хэвлэхдээ нөхцөлийн мэдээллийг хамт дамжуулах ---
    log_position_state(symbol, price, data_for_conditions)

# --- ШИНЭ: Бүх зоосны үнийг хадгалах ---
all_prices = {}

def main_loop():

    print("✅ Starting trading loop (standalone)...")
    
    # --- ШИНЭ: Програм эхлэхэд төлвийг сэргээх ---
    load_state()

    while True:
        try:
            active_coins = get_active_coins()
            if not active_coins:
                time.sleep(5)
                continue
            
            # --- ШИНЭ: Бүх зоосны үнийг нэг удаа татах ---
            all_prices.update({p['symbol']: float(p['price']) for p in client.ticker_price()})
            
            for symbol in active_coins:
                trade_data = get_all_data(symbol)
                if trade_data:
                    run_strategy(symbol, trade_data)
                # --- ЗАСВАР: Хүлээлтийг багасгах ---
                time.sleep(0.2) # Rate limit-д орохгүйн тулд
        except Exception as e:
            print(f"\nError in main loop: {e}")
            time.sleep(5) # Алдаа гарвал 5 секунд хүлээх

if __name__ == "__main__":
    main_loop()
class PositionState:
    def __init__(self):
        # --- ШИНЭ: Олон позиц хадгалах жагсаалт ---
        self.long_positions = []  # [{'entry_price': float, 'qty': float, 'order_id': str}, ...]
        self.short_positions = [] # [{'entry_price': float, 'qty': float, 'order_id': str}, ...]
        self.long_ok = False # ШИНЭ: Long позиц нээхэд бэлэн эсэх
        self.short_ok = False # ШИНЭ: Short позиц нээхэд бэлэн эсэх
        self.long_ok2 = False # ШИНЭ: Long позиц нээхэд бэлэн эсэх
        self.short_ok2 = False # ШИНЭ: Short позиц нээхэд бэлэн эсэх

    @property
    def long_opened(self):
        return len(self.long_positions) > 0

    @property
    def short_opened(self):
        return len(self.short_positions) > 0

    def add_long(self, entry_price, qty, order_id):
        self.long_positions.append({'entry_price': entry_price, 'qty': qty, 'order_id': order_id})

    def add_short(self, entry_price, qty, order_id):
        self.short_positions.append({'entry_price': entry_price, 'qty': qty, 'order_id': order_id})

    def remove_long(self, index=0):
        if 0 <= index < len(self.long_positions):
            del self.long_positions[index]

    def remove_short(self, index=0):
        if 0 <= index < len(self.short_positions):
            del self.short_positions[index]

all_data_store = {}
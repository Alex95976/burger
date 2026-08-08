# --- ШИНЭ: Төлөв хадгалах глобал хувьсагч ---
conditions_state = {}

def get_trade_conditions(symbol, ohlc_data, macd_data, rsi_data):
    """
    OHLC датаг ашиглан 'open_up', 'open_down' болон тэдгээрийн limit утгуудыг тооцоолно.
    Limit утгыг зөвхөн төлөв өөрчлөгдсөн үед нэг удаа шинэчилнэ.
    """
    global conditions_state

    try:
        # 1. Тухайн зоосны төлөвийг анх удаа үүсгэх
        if symbol not in conditions_state:
            conditions_state[symbol] = {
                "open_up": False,
                "open_down": False,
                "open_up_limit": None,
                "open_down_limit": None,
            }

        # 2. Өмнөх төлөвийг авах
        previous_state = conditions_state[symbol]

        # Шаардлагатай хувьсагчдыг задлах
        # --- ЗАСВАР: open0 нь хамгийн шинэ (сүүлийн), open1 нь өмнөх лаа ---
        open0 = ohlc_data["ohlc_list"][-1]["open"] # Хамгийн сүүлийн лаа (list-ийн сүүлийн элемент)
        open1 = ohlc_data["ohlc_list"][-2]["open"] # Өмнөх лаа (сүүлээсээ 2 дахь элемент)

        # 3. Одоогийн төлөвийг тооцоолох
        current_open_up = open0 > open1
        current_open_down = open0 < open1

        # 4. Төлөв өөрчлөгдсөн эсэхийг шалгаж, limit-г шинэчлэх
        # UP төлөв рүү шинээр орсон бол
        if current_open_up and not previous_state["open_up"]:
            previous_state["open_up_limit"] = ohlc_data.get("min_open")

        # DOWN төлөв рүү шинээр орсон бол
        if current_open_down and not previous_state["open_down"]:
            previous_state["open_down_limit"] = ohlc_data.get("max_open")

        # 5. Одоогийн төлөвийг state-д хадгалах
        previous_state["open_up"] = current_open_up
        previous_state["open_down"] = current_open_down

        # 6. Эцсийн үр дүнг буцаах
        result = previous_state.copy()
        result["error"] = None # Алдаагүй бол error-г null болгох
        return result

    except (KeyError, IndexError, TypeError) as e:
        return {"error": f"Data structure error in conditions: {e}"}

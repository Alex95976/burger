def get_trade_conditions(ohlc_data, macd_data, rsi_data):
    """
    OHLC датаг ашиглан 'open_up', 'open_down' хувьсагчдыг тооцоолно.
    `macd_data` параметрийг одоогоор ашиглахгүй.
    """
    # Анхны утгуудыг тодорхойлох
    result = {
        "open_up": False,
        "open_down": False,
        "error": None
    }

    try:
        # Шаардлагатай хувьсагчдыг задлах
        open0 = ohlc_data["ohlc_list"][0]["open"]
        open1 = ohlc_data["ohlc_list"][1]["open"]

        # `open_trend`-г тооцоолох
        if open0 > open1:
            result["open_up"] = True
            result["open_down"] = False
        elif open0 < open1:
            result["open_down"] = True
            result["open_up"] = False
        # Хэрэв open0 == open1 бол хоёулаа False хэвээр үлдэнэ.

    except (KeyError, IndexError, TypeError) as e:
        # Дата дутуу (жишээ нь: ohlc_list байхгүй) үед алдааг барьж авах
        result["error"] = f"Data structure error while processing OHLC: {e}"

    return result
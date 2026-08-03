def get_main_trade_conditions(data):

    state = data.get("state")
    macd_up = data.get("macd_up")
    macd_down = data.get("macd_down")
    macd_line_2 = data.get("macd_line", {}).get("-2")
    macd_uplimit = data.get("macd_uplimit")
    macd_downlimit = data.get("macd_downlimit")
    uplimit_cross_line = data.get("uplimit_cross_line")
    downlimit_cross_line = data.get("downlimit_cross_line") 

    long_pnl = data.get("long_pnl")
    short_pnl = data.get("short_pnl")

    can_compare_cross_lines = uplimit_cross_line is not None and downlimit_cross_line is not None
    state.long_ok = data.get("long_ok", False) 
    state.short_ok = data.get("short_ok", False) 

    total_longs = data.get("total_longs", 0)
    total_shorts = data.get("total_shorts", 0)

    can_open_long = len(state.long_positions) < 10 
    can_open_short = len(state.short_positions) < 10

    long_open1 = can_open_long and macd_up and (total_longs == 0 and total_shorts == 0 or total_longs < total_shorts)

    short_open1 = can_open_short and macd_down and (total_longs == 0 and total_shorts == 0 or total_shorts < total_longs)

    long_open2 = can_open_long and macd_up and macd_line_2 > macd_downlimit and (total_longs == total_shorts)
    
    short_open2 = can_open_short and macd_down and macd_line_2 < macd_uplimit and (total_shorts == total_longs)
    
    long_close1 = state.long_opened and macd_down and long_pnl is not None and (total_longs <= total_shorts) and long_pnl > 0.00

    short_close1 = state.short_opened and macd_up and short_pnl is not None and (total_shorts <= total_longs) and short_pnl > 0.00

    long_close2 = state.long_opened and macd_down and long_pnl is not None and (total_shorts == 0 and total_longs >= total_shorts) and long_pnl > 0.00
    
    short_close2 = state.short_opened and macd_up and short_pnl is not None and (total_longs == 0 and total_shorts >= total_longs) and short_pnl > 0.00

    return {
        "long_open1": long_open1,
        "long_close1": long_close1,
        "short_open1": short_open1,
        "short_close1": short_close1,
        "long_open2": long_open2,
        "long_close2": long_close2,
        "short_open2": short_open2,
        "short_close2": short_close2
    }
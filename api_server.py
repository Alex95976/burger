import os
from flask import Flask, jsonify, request
# from aaa_client import get_client # --- ХАСАХ: Энэ файл одоо хэрэггүй ---
from test import get_rsi_data # test.py нь одоо дангаараа ажиллана
from test2 import get_macd # ШИНЭ: test2.py-аас MACD функцийг импортлох
from test3 import get_last_4_ohlc # ШИНЭ: test3.py-аас OHLC функцийг импортлох
from test4 import get_trade_conditions # ШИНЭ: test4.py-аас нөхцөл шалгах функцийг импортлох

# Flask аппликэйшн үүсгэх
app = Flask(__name__)

@app.route('/rsi-data', methods=['GET'])
def serve_rsi_data():
    """
    /rsi-data?symbol=BTCUSDT гэх мэт хаягаар хандахад RSI мэдээллийг
    JSON хэлбэрээр буцаах endpoint.
    """
    # URL-аас 'symbol' параметрийг авах
    symbol = request.args.get('symbol')
    if not symbol:
        return jsonify({"error": "Please provide a 'symbol' parameter (e.g., ?symbol=BTCUSDT)"}), 400

    # test.py доторх функцээ дуудах (client дамжуулах шаардлагагүй)
    rsi_data = get_rsi_data(symbol.upper())

    if not rsi_data:
        return jsonify({"error": f"Could not calculate RSI data for {symbol}."}), 404

    return jsonify(rsi_data)

@app.route('/macd-data', methods=['GET'])
def serve_macd_data():
    """
    /macd-data?symbol=BTCUSDT гэх мэт хаягаар хандахад MACD мэдээллийг
    JSON хэлбэрээр буцаах endpoint.
    """
    # URL-аас 'symbol' параметрийг авах
    symbol = request.args.get('symbol')
    if not symbol:
        return jsonify({"error": "Please provide a 'symbol' parameter (e.g., ?symbol=BTCUSDT)"}), 400

    # test2.py доторх функцээ дуудах
    macd_data = get_macd(symbol.upper())

    if not macd_data:
        return jsonify({"error": f"Could not calculate MACD data for {symbol}."}), 404

    return jsonify(macd_data)

@app.route('/ohlc-data', methods=['GET'])
def serve_ohlc_data():
    """
    /ohlc-data?symbol=BTCUSDT гэх мэт хаягаар хандахад OHLC мэдээллийг
    JSON хэлбэрээр буцаах endpoint.
    """
    # URL-аас 'symbol' параметрийг авах
    symbol = request.args.get('symbol')
    if not symbol:
        return jsonify({"error": "Please provide a 'symbol' parameter (e.g., ?symbol=BTCUSDT)"}), 400

    # test3.py доторх функцээ дуудах
    ohlc_data = get_last_4_ohlc(symbol.upper())

    if not ohlc_data:
        return jsonify({"error": f"Could not fetch OHLC data for {symbol}."}), 404

    return jsonify(ohlc_data)

@app.route('/trade-conditions', methods=['GET'])
def serve_trade_conditions():
    """
    Бүх индикаторын мэдээллийг нэгтгэж, арилжааны нөхцөлийг тооцоолоод
    JSON хэлбэрээр буцаах endpoint.
    """
    symbol = request.args.get('symbol')
    if not symbol:
        return jsonify({"error": "Please provide a 'symbol' parameter"}), 400

    symbol = symbol.upper()

    # 1. Шаардлагатай бүх датаг бусад endpoint-уудаас татах
    ohlc_data = get_last_4_ohlc(symbol)
    macd_data = get_macd(symbol)
    rsi_data = get_rsi_data(symbol) # rsi_data-г мөн татна

    # Аль нэг нь байхгүй бол алдаа буцаах
    if not all([ohlc_data, macd_data, rsi_data]):
        missing = []
        if not ohlc_data: missing.append("OHLC")
        if not macd_data: missing.append("MACD")
        if not rsi_data: missing.append("RSI")
        return jsonify({"error": f"Could not fetch required data for {symbol}. Missing: {', '.join(missing)}"}), 404

    # 2. test4.py доторх функц рүү датаг дамжуулж, нөхцөл тооцоолох
    conditions = get_trade_conditions(ohlc_data, macd_data, rsi_data)

    return jsonify(conditions)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
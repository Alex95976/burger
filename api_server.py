#api_server.py

import os
from flask import Flask, jsonify, request
from data_rsi import get_rsi_data # test.py нь одоо дангаараа ажиллана
from data_macd import get_macd # ШИНЭ: test2.py-аас MACD функцийг импортлох
from data_ohlc import get_last_4_ohlc # ШИНЭ: test3.py-аас OHLC функцийг импортлох
from data_condition import get_trade_conditions # ШИНЭ: test4.py-аас нөхцөл шалгах функцийг импортлох

# ШИНЭ: data_percent-оос шаардлагатай функц болон клиент авах
from client import get_client
from data_percent import initialize_baseline, get_percent_change, get_top_gainers_n, get_top_losers_n

# Flask аппликэйшн үүсгэх
app = Flask(__name__)

# Сервер асахад Binance client үүсгэж, baseline-ийг автоматаар бэлтгэх
print("🚀 Flask сервер асахын өмнө Baseline үүсгэж байна...")
_client = get_client()
_baseline = {}
if _client:
    try:
        _baseline = initialize_baseline(_client)
        print("✅ Baseline амжилттай үүслээ!")
    except Exception as e:
        print(f"⚠️ Baseline үүсгэхэд алдаа гарлаа: {e}")
else:
    print("❌ Binance client үүссэнгүй!")

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
    # --- ЗАСВАР: Позицын мэдээлэл дамжуулахгүй, зөвхөн индикатор дамжуулна ---
    conditions = get_trade_conditions(symbol, ohlc_data, macd_data, rsi_data)

    return jsonify(conditions)

@app.route('/percent-data', methods=['GET'])
def serve_percent_data():
    """Тухайн зоосны эсвэл бүх зоосны хувь өөрчлөлтийг буцаана."""
    if not _client:
        return jsonify({"error": "Binance client is not initialized."}), 500
    
    symbol = request.args.get('symbol')
    percent_data = get_percent_change(_client, _baseline)

    if symbol:
        symbol = symbol.upper()
        if symbol in percent_data:
            return jsonify({symbol: percent_data[symbol]})
        else:
            return jsonify({"error": f"Symbol {symbol} not found in percent data."}), 404

    return jsonify(percent_data)

@app.route('/top-gainers', methods=['GET'])
def serve_top_gainers():
    """Хамгийн өндөр өсөлттэй N ширхэг зоосыг буцаана."""
    if not _client:
        return jsonify({"error": "Binance client is not initialized."}), 500
    
    n = int(request.args.get('n', 10))
    top_gainers = get_top_gainers_n(_client, _baseline, n=n)
    return jsonify(top_gainers)

@app.route('/top-losers', methods=['GET'])
def serve_top_losers():
    """Хамгийн өндөр уналттай N ширхэг зоосыг буцаана."""
    if not _client:
        return jsonify({"error": "Binance client is not initialized."}), 500
    
    n = int(request.args.get('n', 10))
    top_losers = get_top_losers_n(_client, _baseline, n=n)
    return jsonify(top_losers)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)

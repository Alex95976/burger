import os
from flask import Flask, jsonify, request
from aaa_client import get_client
from test import get_rsi_data # test.py-аас функцээ импортлох

# Flask аппликэйшн үүсгэх
app = Flask(__name__)

# API key-г орчноос авах шаардлагатай тул энд шалгана
# Railway дээр Environment Variables хэсэгт тохируулна
if not os.getenv("BINANCE_API_KEY") or not os.getenv("BINANCE_API_SECRET"):
    raise ValueError("CRITICAL: BINANCE_API_KEY and BINANCE_API_SECRET must be set in the environment.")

# Нэг удаа client үүсгээд дахин ашиглах
client = get_client()

@app.route('/rsi-data', methods=['GET'])
def serve_rsi_data():
    """
    /rsi-data?symbol=BTCUSDT гэх мэт хаягаар хандахад RSI мэдээллийг
    JSON хэлбэрээр буцаах endpoint.
    """
    if not client:
        return jsonify({"error": "Binance client is not available on the server."}), 500

    # URL-аас 'symbol' параметрийг авах
    symbol = request.args.get('symbol')
    if not symbol:
        return jsonify({"error": "Please provide a 'symbol' parameter (e.g., ?symbol=BTCUSDT)"}), 400

    # test.py доторх функцээ дуудах
    rsi_data = get_rsi_data(client, symbol.upper())

    if not rsi_data:
        return jsonify({"error": f"Could not calculate RSI data for {symbol}."}), 404

    return jsonify(rsi_data)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
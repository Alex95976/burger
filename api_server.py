import os
from flask import Flask, jsonify, request
# from aaa_client import get_client # --- ХАСАХ: Энэ файл одоо хэрэггүй ---
from test import get_rsi_data # test.py нь одоо дангаараа ажиллана

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

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
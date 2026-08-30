import os
from binance.um_futures import UMFutures

def get_client(api_key=None, api_secret=None):
    """
    Binance API key шаардахгүйгээр зөвхөн Public Market Data (Public Client) авах зориулалттай үүсгэх.
    """
    # Түлхүүр шаардлагагүй тул хоосон string эсвэл дурын утгаар client үүсгэнэ.
    client = UMFutures(key="", secret="")
    
    # API дуудлага бүрт 10 секундын timeout тохируулах.
    client.session.requests_params = {"timeout": 10}

    return client

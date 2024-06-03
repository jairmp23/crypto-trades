import requests

def fetch_trades_binance(pair):
    url = f'https://api.binance.com/api/v3/trades?symbol={pair.upper()}'
    response = requests.get(url)
    trades = response.json()
    return trades

def fetch_trades_coinbase(pair):
    url = f'https://api.pro.coinbase.com/products/{pair.upper()}/trades'
    response = requests.get(url)
    trades = response.json()
    return trades

def fetch_trades_kraken(pair):
    url = f'https://api.kraken.com/0/public/Trades?pair={pair.upper()}'
    response = requests.get(url)
    trades = response.json()
    return trades
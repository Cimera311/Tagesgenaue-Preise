#!/usr/bin/env python3
"""Test GoMining API calls"""
import json
import urllib.request

def test_coingecko():
    """Test CoinGecko API for GoMining"""
    url = "https://api.coingecko.com/api/v3/simple/price?ids=gomining-token&vs_currencies=eur,usd"
    try:
        req = urllib.request.Request(url, headers={"accept": "application/json", "user-agent": "price-automation/1.1"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            print("✓ CoinGecko Response:")
            print(json.dumps(data, indent=2))
            return True
    except Exception as e:
        print(f"✗ CoinGecko Error: {e}")
        return False

def test_coinpaprika():
    """Test CoinPaprika API for GoMining"""
    url = "https://api.coinpaprika.com/v1/tickers/gmt-gomining-token?quotes=USD,EUR"
    try:
        req = urllib.request.Request(url, headers={"accept": "application/json"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            print("\n✓ CoinPaprika Response:")
            quotes = data.get("quotes", {})
            print(f"  EUR: {quotes.get('EUR', {}).get('price')}")
            print(f"  USD: {quotes.get('USD', {}).get('price')}")
            return True
    except Exception as e:
        print(f"\n✗ CoinPaprika Error: {e}")
        return False

def test_coingecko_search():
    """Search for GoMining on CoinGecko"""
    url = "https://api.coingecko.com/api/v3/search?query=gomining"
    try:
        req = urllib.request.Request(url, headers={"accept": "application/json", "user-agent": "price-automation/1.1"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            print("\n✓ CoinGecko Search for 'gomining':")
            coins = data.get("coins", [])
            for coin in coins[:3]:
                print(f"  - {coin.get('id')}: {coin.get('name')} ({coin.get('symbol')})")
            return True
    except Exception as e:
        print(f"\n✗ CoinGecko Search Error: {e}")
        return False

if __name__ == "__main__":
    print("=== Testing GoMining API Access ===\n")
    test_coingecko()
    test_coinpaprika()
    test_coingecko_search()

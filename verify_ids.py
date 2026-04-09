#!/usr/bin/env python3
"""Verify correct CoinGecko IDs"""
import json
import urllib.request

def test_id(coin_id):
    """Test a specific CoinGecko ID"""
    url = f"https://api.coingecko.com/api/v3/simple/price?ids={coin_id}&vs_currencies=eur,usd"
    try:
        req = urllib.request.Request(url, headers={"accept": "application/json", "user-agent": "price-automation/1.1"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            if data.get(coin_id):
                print(f"✓ '{coin_id}' ist korrekt:")
                print(f"  EUR: {data[coin_id].get('eur')}")
                print(f"  USD: {data[coin_id].get('usd')}")
                return True
            else:
                print(f"✗ '{coin_id}' gibt leere Antwort zurück")
                return False
    except Exception as e:
        print(f"✗ '{coin_id}' Fehler: {e}")
        return False

print("=== Überprüfe CoinGecko IDs ===\n")
print("Bitcoin:")
test_id("bitcoin")

print("\nGoMining - Teste verschiedene IDs:")
test_id("gomining-token")
test_id("gmt-token")
test_id("goMining-token")

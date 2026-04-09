#!/usr/bin/env python3
"""Debug fetch_prices"""
import json
import urllib.request
import time

def coingecko_simple_price(ids):
    """Test with debug output"""
    url = f"https://api.coingecko.com/api/v3/simple/price?ids={','.join(ids)}&vs_currencies=eur,usd"
    print(f"URL: {url}")
    try:
        req = urllib.request.Request(url, headers={"accept": "application/json", "user-agent": "price-automation/1.1"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            print(f"Response: {json.dumps(data, indent=2)}")
            return data
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return None

print("Test with both coins:")
time.sleep(2)  # Wait a bit to avoid rate limit
result = coingecko_simple_price(["bitcoin", "gmt-token"])
print(f"\nResult: {result}")

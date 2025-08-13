# run_test.py (enhanced debug)
import subprocess
import sys
import os
import requests

print("▶ Running fetch_prices.py in local test mode...")

# Ensure data dir exists
os.makedirs("data", exist_ok=True)

# Call the main script
result = subprocess.run(
    [sys.executable, "fetch_prices.py"], 
    capture_output=True, 
    text=True
)

print("---- STDOUT ----")
print(result.stdout)
print("---- STDERR ----")
print(result.stderr)

# Check if CSV files exist
print("\n▶ Checking output files in 'data/'...")
btc_path = "data/bitcoin_eur.csv"
gmt_path = "data/gominingtoken_eur.csv"

print("✅" if os.path.exists(btc_path) else "❌", btc_path, "exists" if os.path.exists(btc_path) else "not found")
print("✅" if os.path.exists(gmt_path) else "❌", gmt_path, "exists" if os.path.exists(gmt_path) else "not found")

if not os.path.exists(gmt_path):
    print("\n🔍 Debugging GoMining Token fetch...\n")
    # CoinGecko
    cg_url = "https://api.coingecko.com/api/v3/simple/price"
    cg_params = {"ids": "gomining-token", "vs_currencies": "eur"}
    try:
        r = requests.get(cg_url, params=cg_params, headers={"accept": "application/json"})
        print(f"CoinGecko URL: {r.url}")
        print(f"Status: {r.status_code}")
        print(f"Response: {r.text[:500]}\n")
    except Exception as e:
        print("CoinGecko fetch failed:", e)

    # CoinPaprika EUR
    paprika_url_eur = "https://api.coinpaprika.com/v1/tickers/gmt-gomining-token?quotes=EUR"
    try:
        r = requests.get(paprika_url_eur, headers={"accept": "application/json"})
        print(f"CoinPaprika EUR URL: {r.url}")
        print(f"Status: {r.status_code}")
        print(f"Response (trunc): {r.text[:500]}\n")
    except Exception as e:
        print("CoinPaprika EUR fetch failed:", e)

    # CoinPaprika USD
    paprika_url_usd = "https://api.coinpaprika.com/v1/tickers/gmt-gomining-token?quotes=USD"
    try:
        r = requests.get(paprika_url_usd, headers={"accept": "application/json"})
        print(f"CoinPaprika USD URL: {r.url}")
        print(f"Status: {r.status_code}")
        print(f"Response (trunc): {r.text[:500]}\n")
    except Exception as e:
        print("CoinPaprika USD fetch failed:", e)

    # FX USD->EUR
    fx_url = "https://api.exchangerate.host/latest?base=USD&symbols=EUR"
    try:
        r = requests.get(fx_url, headers={"accept": "application/json"})
        print(f"FX URL: {r.url}")
        print(f"Status: {r.status_code}")
        print(f"Response (trunc): {r.text[:500]}\n")
    except Exception as e:
        print("FX fetch failed:", e)

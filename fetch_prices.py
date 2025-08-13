#!/usr/bin/env python3
"""
Daily crypto price appender (EUR) aligned to Europe/Berlin local date,
with duplicate-date guard (idempotent).

Primary: CoinGecko simple/price
Fallback: Coinpaprika /tickers/{id}

Coins: BTC, GoMining Token (edit COINS to add more)
"""
import os, sys, csv, json, datetime, urllib.request
from zoneinfo import ZoneInfo

COINS = [
    {"id": "bitcoin", "paprika_id": "btc-bitcoin", "symbol": "BTC"},
    {"id": "gomining-token", "paprika_id": "gmt-gomining-token", "symbol": "GOMINING"},
]

VS_CURRENCY = "eur"
DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
os.makedirs(DATA_DIR, exist_ok=True)

def http_get(url, headers=None):
    req = urllib.request.Request(url, headers=headers or {})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read().decode("utf-8")

def coingecko_simple_price(ids):
    url = f"https://api.coingecko.com/api/v3/simple/price?ids={','.join(ids)}&vs_currencies={VS_CURRENCY}"
    try:
        txt = http_get(url, headers={"accept": "application/json", "user-agent": "price-automation/1.0"})
        return json.loads(txt)
    except Exception:
        return None

def paprika_ticker_last(coin_id):
    url = f"https://api.coinpaprika.com/v1/tickers/{coin_id}"
    try:
        data = json.loads(http_get(url, headers={"accept":"application/json"}))
        q = data.get("quotes", {}).get("EUR")
        if q and "price" in q:
            return float(q["price"])
    except Exception:
        pass
    return None

def append_csv_idempotent(path, row_date_iso, symbol, price):
    # ensure header and skip if date already exists
    rows = []
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                rows.append(line.rstrip("\n"))
        # check last or any line with same date
        for line in rows[1:]:  # skip header
            if not line.strip():
                continue
            d = line.split(",")[0]
            if d == row_date_iso:
                print(f"Skip {symbol}: date {row_date_iso} already in {os.path.basename(path)}")
                return
    exists = os.path.exists(path)
    with open(path, "a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if not exists:
            w.writerow(["date_iso", "symbol", "price_eur"])
        w.writerow([row_date_iso, symbol, f"{price:.8f}"])
    print(f"Appended {symbol} {price:.8f} EUR to {path}")

def main():
    today_berlin = datetime.datetime.now(ZoneInfo("Europe/Berlin")).date().isoformat()
    ids = [c["id"] for c in COINS]
    cg = coingecko_simple_price(ids)

    for c in COINS:
        price = None
        if cg and c["id"] in cg and VS_CURRENCY in cg[c["id"]]:
            try:
                price = float(cg[c["id"]][VS_CURRENCY])
            except Exception:
                price = None
        if price is None:
            price = paprika_ticker_last(c["paprika_id"])
        if price is None:
            print(f"ERROR: Failed to fetch price for {c['id']}", file=sys.stderr)
            continue
        out = os.path.join(DATA_DIR, f"{c['id'].replace('-', '')}_{VS_CURRENCY}.csv")
        append_csv_idempotent(out, today_berlin, c["symbol"], price)

if __name__ == "__main__":
    main()

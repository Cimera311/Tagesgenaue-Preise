#!/usr/bin/env python3
"""
Daily crypto price appender (EUR) aligned to Europe/Berlin local date,
with duplicate-date guard (idempotent).

Primary: CoinGecko simple/price
Fallback 1: CoinPaprika /tickers/{id}?quotes=EUR
Fallback 2: CoinPaprika USD * FX(USD->EUR) via exchangerate.host (free)
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
        data = json.loads(txt)
        # normalize: could be empty {}
        return data if isinstance(data, dict) and data else None
    except Exception:
        return None

def paprika_ticker_eur(coin_id):
    """Try getting EUR directly from CoinPaprika using quotes=EUR."""
    url = f"https://api.coinpaprika.com/v1/tickers/{coin_id}?quotes=EUR"
    try:
        data = json.loads(http_get(url, headers={"accept":"application/json"}))
        q = data.get("quotes", {}).get("EUR")
        if q and "price" in q:
            return float(q["price"])
    except Exception:
        pass
    return None

def paprika_ticker_usd(coin_id):
    url = f"https://api.coinpaprika.com/v1/tickers/{coin_id}?quotes=USD"
    try:
        data = json.loads(http_get(url, headers={"accept":"application/json"}))
        q = data.get("quotes", {}).get("USD")
        if q and "price" in q:
            return float(q["price"])
    except Exception:
        pass
    return None

def usd_to_eur_rate():
    """Free FX rate from exchangerate.host"""
    url = "https://api.exchangerate.host/latest?base=USD&symbols=EUR"
    try:
        data = json.loads(http_get(url, headers={"accept":"application/json"}))
        return float(data["rates"]["EUR"])
    except Exception:
        return None

def paprika_price_eur_with_fallback(coin_id):
    # Try EUR directly
    eur = paprika_ticker_eur(coin_id)
    if eur is not None:
        return eur
    # Then USD * FX
    usd = paprika_ticker_usd(coin_id)
    if usd is not None:
        fx = usd_to_eur_rate()
        if fx is not None:
            return usd * fx
    return None

import csv, os

def append_csv_idempotent(path, row_date_iso, row_time_berlin, symbol, price_eur, price_usd):
    """
    CSV-Format: date_iso;time_berlin;symbol;price_eur;price_usd
    - Delimiter: ';'
    - Idempotent: pro date_iso nur 1 Zeile
    - Auto-Upgrade: wandelt alte 3-Spalten-CSV still in 5 Spalten um (Zeit/ USD leer)
    """
    # --- ggf. altes Format (3 Spalten) einmalig upgraden ---
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8", newline="") as f:
            sample = f.readline()
            if sample and "," in sample and ";" not in sample:
                # altes Komma-CSV -> auf Semikolon und 5 Spalten migrieren
                f.seek(0)
                rows = [r.strip("\n").split(",") for r in f if r.strip()]
        if 'rows' in locals():
            with open(path, "w", encoding="utf-8", newline="") as f2:
                w2 = csv.writer(f2, delimiter=";")
                # neue Header
                w2.writerow(["date_iso", "time_berlin", "symbol", "price_eur", "price_usd"])
                # alte Daten übernehmen (time/usd leer)
                for i, r in enumerate(rows):
                    if i == 0:
                        # Header der alten Datei ignorieren
                        continue
                    date_iso = (r[0] if len(r) > 0 else "").strip()
                    symbol   = (r[1] if len(r) > 1 else "").strip()
                    eur      = (r[2] if len(r) > 2 else "").strip()
                    w2.writerow([date_iso, "", symbol, eur, ""])

    # --- Idempotenz: Datum schon vorhanden? ---
    exists = os.path.exists(path)
    if exists:
        with open(path, "r", encoding="utf-8", newline="") as f:
            rd = csv.reader(f, delimiter=";")
            header = next(rd, None)
            for row in rd:
                if not row:
                    continue
                if row[0].strip() == str(row_date_iso).strip():
                    print(f"Skip {symbol}: date {row_date_iso} already in {os.path.basename(path)}")
                    return

    # --- Schreiben ---
    clean_date  = str(row_date_iso).strip()
    clean_time  = str(row_time_berlin).strip()
    clean_sym   = str(symbol).strip()
    eur_str     = f"{price_eur:.8f}" if price_eur is not None else ""
    usd_str     = f"{price_usd:.8f}" if price_usd is not None else ""

    with open(path, "a", encoding="utf-8", newline="") as f:
        w = csv.writer(f, delimiter=";")
        if not exists:
            w.writerow(["date_iso", "time_berlin", "symbol", "price_eur", "price_usd"])
        w.writerow([clean_date, clean_time, clean_sym, eur_str, usd_str])

    print(f"Appended {clean_sym} EUR={eur_str or '∅'} USD={usd_str or '∅'} to {path}")


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
            price = paprika_price_eur_with_fallback(c["paprika_id"])
        if price is None:
            print(f"ERROR: Failed to fetch price for {c['id']}", file=sys.stderr)
            continue
        out = os.path.join(DATA_DIR, f"{c['id'].replace('-', '')}_{VS_CURRENCY}.csv")
        from zoneinfo import ZoneInfo
        import datetime
        
        now_berlin  = datetime.datetime.now(ZoneInfo("Europe/Berlin"))
        date_berlin = now_berlin.date().isoformat()
        time_berlin = now_berlin.strftime("%H:%M")
        
        # … eur, usd wie gehabt per CoinGecko/Paprika ermitteln …
        
        append_csv_idempotent(out, date_berlin, time_berlin, c["symbol"], eur, usd)
        

if __name__ == "__main__":
    main()

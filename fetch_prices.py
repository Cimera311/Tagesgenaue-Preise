#!/usr/bin/env python3
"""
Daily crypto price appender (EUR + USD) aligned to Europe/Berlin local date/time,
with duplicate-date guard (idempotent).

Primary: CoinGecko /simple/price (no key), asks for eur & usd
Fallback: Coinpaprika /tickers/{id}?quotes=USD,EUR
Extra fallback: if Paprika returns only USD, convert USD->EUR via exchangerate.host

Coins: BTC, GoMining Token (edit COINS to add more)
"""

import os, sys, csv, json, datetime, urllib.request
from zoneinfo import ZoneInfo

COINS = [
    {"id": "bitcoin", "paprika_id": "btc-bitcoin", "symbol": "BTC"},
    {"id": "gomining-token", "paprika_id": "gmt-gomining-token", "symbol": "GOMINING"},
]

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
os.makedirs(DATA_DIR, exist_ok=True)

def http_get(url, headers=None, timeout=30):
    req = urllib.request.Request(url, headers=headers or {})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read().decode("utf-8")

def coingecko_simple_price(ids):
    """
    Returns:
    {
      "bitcoin": {"eur": 99999.0, "usd": 109999.0},
      "gomining-token": {"eur": 0.49, "usd": 0.53}
    }
    """
    url = (
        "https://api.coingecko.com/api/v3/simple/price"
        f"?ids={','.join(ids)}&vs_currencies=eur,usd"
    )
    try:
        txt = http_get(url, headers={"accept": "application/json", "user-agent": "price-automation/1.1"})
        data = json.loads(txt)
        # normalize floats
        for k, v in data.items():
            for cur in ("eur", "usd"):
                if cur in v and v[cur] is not None:
                    try:
                        v[cur] = float(v[cur])
                    except Exception:
                        v[cur] = None
        return data
    except Exception:
        return None

def fetch_fx_usd_eur():
    """USD->EUR FX rate via exchangerate.host (free)."""
    url = "https://api.exchangerate.host/latest?base=USD&symbols=EUR"
    try:
        data = json.loads(http_get(url, headers={"accept":"application/json"}))
        return float(data.get("rates", {}).get("EUR"))
    except Exception:
        return None

def paprika_ticker_quotes(coin_id):
    """
    Returns (eur_price, usd_price) from CoinPaprika.
    Tries ?quotes=USD,EUR; if EUR is missing but USD present, convert USD->EUR.
    """
    url = f"https://api.coinpaprika.com/v1/tickers/{coin_id}?quotes=USD,EUR"
    eur = usd = None
    try:
        data = json.loads(http_get(url, headers={"accept":"application/json"}))
        q = data.get("quotes", {})
        if "EUR" in q and q["EUR"].get("price") is not None:
            eur = float(q["EUR"]["price"])
        if "USD" in q and q["USD"].get("price") is not None:
            usd = float(q["USD"]["price"])
    except Exception:
        pass

    if eur is None and usd is not None:
        fx = fetch_fx_usd_eur()
        if fx is not None:
            eur = usd * fx

    return eur, usd

# ---------- CSV helpers ----------

# ---------- CSV helpers ----------

def append_csv_idempotent(path, row_date_iso, row_time_berlin, symbol, price_eur, price_usd):
    # Duplikate nach Datum verhindern (liest mit Semikolon)
    exists = os.path.exists(path)
    if exists:
        try:
            with open(path, "r", encoding="utf-8") as f:
                rd = csv.reader(f, delimiter=";")
                header = next(rd, None)
                for row in rd:
                    if not row:
                        continue
                    # Spalte 0 ist date_iso
                    if row[0].strip() == row_date_iso:
                        print(f"Skip {symbol}: date {row_date_iso} already in {os.path.basename(path)}")
                        return
        except Exception:
            pass

    # Trim + format
    clean_date = str(row_date_iso).strip()
    clean_time = str(row_time_berlin).strip()
    clean_symbol = str(symbol).strip()
        # ...existing code...
    eur_str = f"{price_eur:.8f}".replace(".", ",").strip() if price_eur is not None else ""
    usd_str = f"{price_usd:.8f}".replace(".", ",").strip() if price_usd is not None else ""
    # ...existing code...
    #eur_str = f"{price_eur:.8f}".strip() if price_eur is not None else ""
    #usd_str = f"{price_usd:.8f}".strip() if price_usd is not None else ""

    with open(path, "a", newline="", encoding="utf-8") as f:
        w = csv.writer(f, delimiter=";")
        if not exists:
            w.writerow(["date_iso", "time_berlin", "symbol", "price_eur", "price_usd"])
        w.writerow([clean_date, clean_time, clean_symbol, eur_str, usd_str])

    print(f"Appended {clean_symbol} EUR={eur_str or '∅'} USD={usd_str or '∅'} to {path}")



# ---------- main ----------

def main():
    now_berlin = datetime.datetime.now(ZoneInfo("Europe/Berlin"))
    date_berlin = now_berlin.date().isoformat()
    time_berlin = now_berlin.strftime("%H:%M")

    ids = [c["id"] for c in COINS]
    cg = coingecko_simple_price(ids)  # kann None sein

    for c in COINS:
        eur = usd = None

        # Primär: CoinGecko (EUR & USD in einem Call)
        if cg and c["id"] in cg:
            eur = cg[c["id"]].get("eur")
            usd = cg[c["id"]].get("usd")

        # Fallback: CoinPaprika (liefert USD/EUR; wenn nur USD -> FX-Konvertierung)
        if eur is None or usd is None:
            eur_f, usd_f = paprika_ticker_quotes(c["paprika_id"])
            if eur is None:
                eur = eur_f
            if usd is None:
                usd = usd_f

        if eur is None and usd is None:
            print(f"ERROR: Failed to fetch EUR/USD for {c['id']}", file=sys.stderr)
            continue

        out = os.path.join(DATA_DIR, f"{c['id'].replace('-', '')}_eur.csv")
        append_csv_idempotent(out, date_berlin, time_berlin, c["symbol"], eur, usd)


if __name__ == "__main__":
    main()

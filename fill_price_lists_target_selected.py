"""
Befüllt data/price_lists/*.csv für ein gegebenes Datum via CoinGecko History API.
Verwendung: python fill_price_lists.py 2026-06-16
"""
import json
import os
import ssl
import sys
import time
import urllib.request
from datetime import datetime, timedelta


_ssl_ctx = ssl.create_default_context()
_ssl_ctx.check_hostname = False
_ssl_ctx.verify_mode = ssl.CERT_NONE

DATA_DIR = os.path.join(os.path.dirname(__file__), "data", "price_lists")
TARGET_START_DATE = "2024-01-01"  # für Tests: Startdatum
TARGET_END_DATE = "2024-02-01"    # für Tests: Enddatum (inklusive)
COINS = [
    ("bitcoin",           "BTC",  "bitcoin_prices.csv"),
    ("gmt-token",         "GMT",  "gomining_prices.csv"),
   ("ethereum",          "ETH",  "ethereum_prices.csv"),
    ("binancecoin",       "BNB",  "bnb_prices.csv"),
    ("solana",            "SOL",  "solana_prices.csv"),
    ("the-open-network",  "TON",  "toncoin_prices.csv"),
    ("tether",            "USDT", "usdt_prices.csv"),
    ("usd-coin",          "USDC", "usdc_prices.csv"),
]

CURRENCIES = [
    "eur","usd","gbp",
    "aed","ars","aud","bdt","bhd","bmd","brl","cad","chf","clp","cny","czk","dkk",
    "gel","hkd","huf","idr","ils","inr","jpy","krw","kwd","lkr","mmk",
    "mxn","myr","ngn","nok","nzd","php","pkr","pln","rub","sar","sek","sgd","thb",
    "try","twd","uah","vnd","xag","xau","zar",
]

HEADER = ["date_iso", "time_berlin", "symbol"] + [f"price_{c}" for c in CURRENCIES]


def fmt(val):
    """Zahl als deutschen Dezimal-String (Komma statt Punkt)."""
    if val is None:
        return ""
    return str(round(float(val), 8)).replace(".", ",")


def date_in_file(filepath, date_iso):
    if not os.path.exists(filepath):
        return False
    with open(filepath, encoding="utf-8") as f:
        for line in f:
            if line.startswith(date_iso + ";"):
                return True
    return False


def fetch_history(coin_id, date_str):
    """date_str = YYYY-MM-DD → wandelt in DD-MM-YYYY um."""
    d = datetime.strptime(date_str, "%Y-%m-%d")
    cg_date = d.strftime("%d-%m-%Y")
    url = f"https://api.coingecko.com/api/v3/coins/{coin_id}/history?date={cg_date}"
    req = urllib.request.Request(url, headers={
        "Accept": "application/json",
        "User-Agent": "Mozilla/5.0",
    })
    with urllib.request.urlopen(req, timeout=15, context=_ssl_ctx) as resp:
        return json.loads(resp.read())


def process_date(date_iso):
    time_berlin = "00:00"

    for coin_id, symbol, filename in COINS:
        filepath = os.path.join(DATA_DIR, filename)

        # Header schreiben falls Datei leer/neu
        if not os.path.exists(filepath) or os.path.getsize(filepath) == 0:
            with open(filepath, "w", encoding="utf-8", newline="") as f:
                f.write(";".join(HEADER) + "\n")

        if date_in_file(filepath, date_iso):
            print(f"  {symbol} {date_iso}: bereits vorhanden, übersprungen.")
            continue

        print(f"  {symbol} ({coin_id}) …", end=" ", flush=True)
        retries = 3
        data = None
        for attempt in range(retries):
            try:
                data = fetch_history(coin_id, date_iso)
                break
            except Exception as e:
                code = getattr(e, "code", None)
                if code == 429:
                    wait = 15 * (attempt + 1)
                    print(f"429 Rate limit, warte {wait}s …", end=" ", flush=True)
                    time.sleep(wait)
                else:
                    print(f"Fehler: {e}")
                    break

        if data is None:
            print("FEHLER – übersprungen.")
            continue

        prices = data.get("market_data", {}).get("current_price", {})
        row = [date_iso, time_berlin, symbol]
        for cur in CURRENCIES:
            row.append(fmt(prices.get(cur)))

        with open(filepath, "a", encoding="utf-8", newline="") as f:
            f.write(";".join(row) + "\n")
        print("OK")

        time.sleep(2)  # Rate-limit-Pause zwischen Coins


def build_date_list(start_iso, end_iso):
    start_date = datetime.strptime(start_iso, "%Y-%m-%d").date()
    end_date = datetime.strptime(end_iso, "%Y-%m-%d").date()
    if start_date > end_date:
        raise ValueError("Startdatum darf nicht nach dem Enddatum liegen.")

    dates = []
    current = start_date
    while current <= end_date:
        dates.append(current.strftime("%Y-%m-%d"))
        current += timedelta(days=1)
    return dates


if __name__ == "__main__":
    if len(sys.argv) == 1:
        # Kein Argument → verwende TARGET_START_DATE bis TARGET_END_DATE.
        start_iso = TARGET_START_DATE
        end_iso = TARGET_END_DATE
        print(
            f"Kein Datum angegeben → verwende TARGET-Bereich: "
            f"{start_iso} bis {end_iso}"
        )
    elif len(sys.argv) == 2:
        start_iso = sys.argv[1]
        end_iso = sys.argv[1]
    elif len(sys.argv) == 3:
        start_iso = sys.argv[1]
        end_iso = sys.argv[2]
    else:
        print("Verwendung: python fill_price_lists_target_Bitcoin.py [YYYY-MM-DD] [YYYY-MM-DD]")
        print("  Ohne Argumente: TARGET_START_DATE bis TARGET_END_DATE")
        print("  Ein Argument: nur dieses Datum")
        print("  Zwei Argumente: von bis (inklusive)")
        sys.exit(1)

    try:
        dates_to_process = build_date_list(start_iso, end_iso)
    except ValueError:
        print("Ungültiges Datum. Format: YYYY-MM-DD")
        sys.exit(1)

    print(
        f"Lade Preise für {len(dates_to_process)} Tag(e): "
        f"{dates_to_process[0]} bis {dates_to_process[-1]} …"
    )
    for date_iso in dates_to_process:
        print(f"\n=== {date_iso} ===")
        process_date(date_iso)
    print("Fertig.")

"""
Befüllt data/price_lists/*.csv mit historischen Tageskursen.

Datenquellen:
- CoinPaprika: täglicher USD-Preis je Kryptowährung
- Frankfurter v2: historische Wechselkurse von USD zu allen Zielwährungen

Verwendung:
    python fill_price_lists_paprika.py
        -> 2025-06-18 bis gestern

    python fill_price_lists_paprika.py 2026-06-16
        -> nur 2026-06-16

    python fill_price_lists_paprika.py 2025-06-18 2026-06-17
        -> kompletter Zeitraum, beide Datumsangaben inklusive

Das Skript übernimmt vorhandene CSV-Zeilen, ergänzt nur fehlende Tage und
sortiert die Dateien anschließend chronologisch.
"""

from __future__ import annotations

import csv
import json
import os
import ssl
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from calendar import monthrange
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from typing import Any

try:
    from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
except ImportError:  # Python < 3.9
    ZoneInfo = None  # type: ignore[assignment]
    ZoneInfoNotFoundError = Exception  # type: ignore[assignment,misc]


DATA_DIR = os.path.join(os.path.dirname(__file__), "data", "price_lists2")
DEFAULT_START_DATE = "2025-06-19"
REQUEST_TIMEOUT = 60
MAX_RETRIES = 4
COIN_REQUEST_PAUSE = 1.5
FX_LOOKBACK_DAYS = 14

COINPAPRIKA_API = "https://api.coinpaprika.com/v1"
FRANKFURTER_API = "https://api.frankfurter.dev/v2"

# CoinPaprika-ID, Symbol in der CSV, Zieldatei
COINS = [
    ("btc-bitcoin",                    "BTC",  "bitcoin_prices.csv"),
    ("gomining-gomining-token",        "GMT",  "gomining_prices.csv"),
    ("eth-ethereum",                   "ETH",  "ethereum_prices.csv"),
    ("bnb-bnb",                        "BNB",  "bnb_prices.csv"),
    ("sol-solana",                     "SOL",  "solana_prices.csv"),
    ("toncoin-the-open-network",       "TON",  "toncoin_prices.csv"),
    ("usdt-tether",                    "USDT", "usdt_prices.csv"),
    ("usdc-usdc",                      "USDC", "usdc_prices.csv"),
]

CURRENCIES = [
    "eur", "usd", "gbp",
    "aed", "ars", "aud", "bdt", "bhd", "bmd", "brl", "cad", "chf",
    "clp", "cny", "czk", "dkk", "gel", "hkd", "huf", "idr", "ils",
    "inr", "jpy", "krw", "kwd", "lkr", "mmk", "mxn", "myr", "ngn",
    "nok", "nzd", "php", "pkr", "pln", "rub", "sar", "sek", "sgd",
    "thb", "try", "twd", "uah", "vnd", "xag", "xau", "zar",
]

HEADER = ["date_iso", "time_berlin", "symbol"] + [
    f"price_{currency}" for currency in CURRENCIES
]

SSL_CONTEXT = ssl.create_default_context()


class ApiError(RuntimeError):
    """Fehler bei einer API-Anfrage oder einer unerwarteten API-Antwort."""


def fmt(value: float | int | None) -> str:
    """Zahl wie bisher mit maximal 8 Nachkommastellen und Dezimalkomma."""
    if value is None:
        return ""
    return str(round(float(value), 8)).replace(".", ",")


def parse_iso_date(value: str) -> date:
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError as exc:
        raise ValueError(f"Ungültiges Datum '{value}'. Format: YYYY-MM-DD") from exc


def yesterday_berlin() -> date:
    """Gestern nach Berliner Zeit; mit sicherem Fallback."""
    if ZoneInfo is not None:
        try:
            return datetime.now(ZoneInfo("Europe/Berlin")).date() - timedelta(days=1)
        except ZoneInfoNotFoundError:
            pass
    return date.today() - timedelta(days=1)


def last_sunday(year: int, month: int) -> date:
    last_day = date(year, month, monthrange(year, month)[1])
    return last_day - timedelta(days=(last_day.weekday() + 1) % 7)


def berlin_time_from_utc(timestamp: str) -> str:
    """Wandelt CoinPaprikas UTC-Zeit korrekt in Berliner Ortszeit um."""
    utc_dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
    if utc_dt.tzinfo is None:
        utc_dt = utc_dt.replace(tzinfo=timezone.utc)
    else:
        utc_dt = utc_dt.astimezone(timezone.utc)

    if ZoneInfo is not None:
        try:
            return utc_dt.astimezone(ZoneInfo("Europe/Berlin")).strftime("%H:%M")
        except ZoneInfoNotFoundError:
            pass

    # Fallback ohne installierte IANA-Zeitzonendaten:
    # EU-Sommerzeit: letzter Sonntag im März 01:00 UTC bis
    # letzter Sonntag im Oktober 01:00 UTC.
    dst_start = datetime.combine(
        last_sunday(utc_dt.year, 3), datetime.min.time(), tzinfo=timezone.utc
    ) + timedelta(hours=1)
    dst_end = datetime.combine(
        last_sunday(utc_dt.year, 10), datetime.min.time(), tzinfo=timezone.utc
    ) + timedelta(hours=1)
    offset = 2 if dst_start <= utc_dt < dst_end else 1
    return (utc_dt + timedelta(hours=offset)).strftime("%H:%M")


def fetch_json(url: str, label: str) -> Any:
    """JSON mit Retries, Backoff und sicherer TLS-Prüfung abrufen."""
    headers = {
        "Accept": "application/json",
        "User-Agent": "HashFarm-PriceImporter/1.0",
    }

    for attempt in range(1, MAX_RETRIES + 1):
        request = urllib.request.Request(url, headers=headers)
        try:
            with urllib.request.urlopen(
                request,
                timeout=REQUEST_TIMEOUT,
                context=SSL_CONTEXT,
            ) as response:
                return json.loads(response.read().decode("utf-8"))

        except urllib.error.HTTPError as exc:
            retryable = exc.code == 429 or 500 <= exc.code <= 599
            if not retryable or attempt == MAX_RETRIES:
                try:
                    body = exc.read().decode("utf-8", errors="replace")
                except Exception:
                    body = ""
                raise ApiError(
                    f"{label}: HTTP {exc.code}. {body[:300]}"
                ) from exc

            retry_after = exc.headers.get("Retry-After")
            try:
                wait = int(retry_after) if retry_after else 5 * attempt
            except ValueError:
                wait = 5 * attempt
            print(f"HTTP {exc.code}, warte {wait}s …", end=" ", flush=True)
            time.sleep(wait)

        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            if attempt == MAX_RETRIES:
                raise ApiError(f"{label}: {exc}") from exc
            wait = 5 * attempt
            print(f"Verbindungsfehler, warte {wait}s …", end=" ", flush=True)
            time.sleep(wait)

    raise ApiError(f"{label}: Anfrage endgültig fehlgeschlagen")


def fetch_coin_history(coin_id: str, start: date, end: date) -> list[dict[str, Any]]:
    """Lädt CoinPaprika-Tageswerte. start/end sind inklusive."""
    # CoinPaprikas end-Grenze verhält sich beim Tagesendpoint exklusiv.
    api_end = end + timedelta(days=1)
    params = urllib.parse.urlencode(
        {
            "start": start.isoformat(),
            "end": api_end.isoformat(),
            "interval": "1d",
            "quote": "usd",
            "limit": 5000,
        }
    )
    url = f"{COINPAPRIKA_API}/tickers/{coin_id}/historical?{params}"
    data = fetch_json(url, f"CoinPaprika {coin_id}")

    if not isinstance(data, list):
        raise ApiError(f"CoinPaprika {coin_id}: unerwartete Antwort: {data!r}")

    result: list[dict[str, Any]] = []
    for item in data:
        timestamp = item.get("timestamp")
        price = item.get("price")
        if not timestamp or price is None:
            continue

        item_date = datetime.fromisoformat(
            str(timestamp).replace("Z", "+00:00")
        ).date()
        if start <= item_date <= end:
            result.append(item)

    return sorted(result, key=lambda item: str(item["timestamp"]))


def fetch_fx_history(start: date, end: date) -> dict[str, dict[str, float]]:
    """
    Lädt USD→Zielwährung und füllt Wochenenden/Feiertage mit dem letzten
    vorhandenen Kurs auf.
    """
    quotes = [currency.upper() for currency in CURRENCIES if currency != "usd"]
    api_start = start - timedelta(days=FX_LOOKBACK_DAYS)

    params = urllib.parse.urlencode(
        {
            "from": api_start.isoformat(),
            "to": end.isoformat(),
            "base": "USD",
            "quotes": ",".join(quotes),
        },
        safe=",",
    )
    url = f"{FRANKFURTER_API}/rates?{params}"
    data = fetch_json(url, "Frankfurter Wechselkurse")

    if not isinstance(data, list):
        raise ApiError(f"Frankfurter: unerwartete Antwort: {data!r}")

    raw: dict[str, dict[str, float]] = defaultdict(dict)
    for item in data:
        item_date = item.get("date")
        quote = str(item.get("quote", "")).lower()
        rate = item.get("rate")
        if item_date and quote and rate is not None:
            raw[str(item_date)][quote] = float(rate)

    # Forward-Fill: Ein Samstag verwendet beispielsweise den Freitagskurs.
    filled: dict[str, dict[str, float]] = {}
    latest: dict[str, float] = {"usd": 1.0}
    current = api_start
    while current <= end:
        latest.update(raw.get(current.isoformat(), {}))
        if current >= start:
            filled[current.isoformat()] = latest.copy()
        current += timedelta(days=1)

    return filled


def load_existing_rows(filepath: str) -> dict[str, list[str]]:
    """Lädt bestehende CSV-Zeilen als date_iso → komplette Zeile."""
    if not os.path.exists(filepath) or os.path.getsize(filepath) == 0:
        return {}

    rows: dict[str, list[str]] = {}
    with open(filepath, "r", encoding="utf-8", newline="") as file:
        reader = csv.reader(file, delimiter=";")
        existing_header = next(reader, None)
        if existing_header and existing_header != HEADER:
            raise RuntimeError(
                f"Header in {filepath} stimmt nicht mit dem erwarteten Header überein."
            )

        for row in reader:
            if row and row[0]:
                rows[row[0]] = row
    return rows


def write_merged_rows(filepath: str, rows_by_date: dict[str, list[str]]) -> None:
    """Schreibt Header und alle Zeilen chronologisch neu."""
    temp_path = filepath + ".tmp"
    with open(temp_path, "w", encoding="utf-8", newline="") as file:
        writer = csv.writer(file, delimiter=";", lineterminator="\n")
        writer.writerow(HEADER)
        for date_iso in sorted(rows_by_date):
            writer.writerow(rows_by_date[date_iso])
    os.replace(temp_path, filepath)


def build_row(
    item: dict[str, Any],
    symbol: str,
    fx_by_date: dict[str, dict[str, float]],
) -> tuple[str, list[str], list[str]]:
    timestamp = str(item["timestamp"])
    date_iso = datetime.fromisoformat(timestamp.replace("Z", "+00:00")).date().isoformat()
    time_berlin = berlin_time_from_utc(timestamp)
    usd_price = float(item["price"])
    daily_fx = fx_by_date.get(date_iso, {"usd": 1.0})

    missing: list[str] = []
    prices: list[str] = []
    for currency in CURRENCIES:
        if currency == "usd":
            value = usd_price
        else:
            rate = daily_fx.get(currency)
            if rate is None:
                value = None
                missing.append(currency.upper())
            else:
                # Frankfurter base=USD bedeutet: 1 USD = rate Zielwährung.
                value = usd_price * rate
        prices.append(fmt(value))

    return date_iso, [date_iso, time_berlin, symbol, *prices], missing


def process_range(start: date, end: date) -> None:
    os.makedirs(DATA_DIR, exist_ok=True)

    print("Lade USD-Wechselkurse über Frankfurter …", end=" ", flush=True)
    fx_by_date = fetch_fx_history(start, end)
    print("OK")

    missing_summary: dict[str, set[str]] = defaultdict(set)

    for index, (coin_id, symbol, filename) in enumerate(COINS, start=1):
        filepath = os.path.join(DATA_DIR, filename)
        print(
            f"[{index}/{len(COINS)}] {symbol} ({coin_id}) …",
            end=" ",
            flush=True,
        )

        try:
            history = fetch_coin_history(coin_id, start, end)
            if not history:
                print("KEINE DATEN")
                continue

            existing_rows = load_existing_rows(filepath)
            added = 0
            skipped = 0

            for item in history:
                date_iso, row, missing = build_row(item, symbol, fx_by_date)
                if date_iso in existing_rows:
                    skipped += 1
                    continue

                existing_rows[date_iso] = row
                added += 1
                for currency in missing:
                    missing_summary[currency].add(date_iso)

            write_merged_rows(filepath, existing_rows)
            print(
                f"OK – {added} ergänzt, {skipped} bereits vorhanden, "
                f"{len(history)} API-Tage"
            )

        except Exception as exc:
            print(f"FEHLER: {exc}")

        if index < len(COINS):
            time.sleep(COIN_REQUEST_PAUSE)

    if missing_summary:
        print("\nWarnung: Für einige Währungen fehlten Wechselkurse:")
        for currency, dates in sorted(missing_summary.items()):
            sample = ", ".join(sorted(dates)[:3])
            suffix = " …" if len(dates) > 3 else ""
            print(f"  {currency}: {len(dates)} Tage ({sample}{suffix})")
    else:
        print("\nAlle angeforderten Währungsspalten konnten befüllt werden.")


def parse_cli() -> tuple[date, date]:
    args = sys.argv[1:]

    if args and args[0] in {"-h", "--help"}:
        print(__doc__)
        raise SystemExit(0)

    if len(args) == 0:
        start = parse_iso_date(DEFAULT_START_DATE)
        end = yesterday_berlin()
        print(
            f"Kein Datum angegeben → verwende {start.isoformat()} "
            f"bis gestern ({end.isoformat()})."
        )
    elif len(args) == 1:
        start = end = parse_iso_date(args[0])
    elif len(args) == 2:
        start = parse_iso_date(args[0])
        end = parse_iso_date(args[1])
    else:
        raise ValueError(
            "Verwendung: python fill_price_lists_paprika.py "
            "[YYYY-MM-DD] oder [START ENDE]"
        )

    if start > end:
        raise ValueError("Das Startdatum darf nicht nach dem Enddatum liegen.")

    if (end - start).days + 1 > 5000:
        raise ValueError(
            "Der Zeitraum überschreitet CoinPaprikas Limit von 5000 Tageswerten."
        )

    return start, end


if __name__ == "__main__":
    try:
        start_date, end_date = parse_cli()
        print(
            f"Lade historische Preise von {start_date.isoformat()} "
            f"bis {end_date.isoformat()} …"
        )
        process_range(start_date, end_date)
        print("Fertig.")
    except (ValueError, RuntimeError, ApiError) as exc:
        print(f"Abbruch: {exc}")
        sys.exit(1)

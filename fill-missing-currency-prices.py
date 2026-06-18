#!/usr/bin/env python3
"""
Füllt leere Währungsspalten in data/price_lists/*.csv mit historischen
USD-Wechselkursen von Frankfurter.

Vorhandene Werte werden NICHT überschrieben.
Als Grundlage jeder Berechnung dient der vorhandene Wert in price_usd.

Beispiele:
    python fill-missing-currency-prices.py

Nur bestimmte Dateien:
    python fill-missing-currency-prices.py bitcoin_prices.csv gomining_prices.csv

Testlauf ohne Dateien zu verändern:
    python fill-missing-currency-prices.py --dry-run
"""

from __future__ import annotations

import argparse
import csv
import io
import shutil
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from bisect import bisect_right
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data" / "price_lists"
BACKUP_DIR = DATA_DIR / "backups"

FRANKFURTER_URL = "https://api.frankfurter.dev/v2/rates.csv"

DATE_COLUMN = "date_iso"
USD_COLUMN = "price_usd"
PRICE_PREFIX = "price_"

# Vor dem frühesten benötigten Tag werden zusätzliche Tage geladen.
# Dadurch steht auch an Wochenenden und Feiertagen ein vorheriger Kurs bereit.
FX_LOOKBACK_DAYS = 14

# Gleiche maximale Genauigkeit wie im bisherigen Import.
DECIMAL_PLACES = 8

CREATE_BACKUPS = True


@dataclass
class CsvTable:
    path: Path
    headers: list[str]
    rows: list[dict[str, str]]
    target_columns: list[str]


def parse_iso_date(value: str, filename: str, line_number: int) -> date:
    value = value.strip()

    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError as exc:
        raise ValueError(
            f'{filename}, Zeile {line_number}: '
            f'ungültiges ISO-Datum "{value}". Erwartet wird YYYY-MM-DD.'
        ) from exc


def parse_decimal(value: str, context: str) -> Decimal:
    """
    Akzeptiert deutsche Dezimalwerte wie 0,421586706
    sowie Werte mit Dezimalpunkt.
    """
    normalized = value.strip().replace(",", ".")

    try:
        number = Decimal(normalized)
    except InvalidOperation as exc:
        raise ValueError(
            f'Ungültiger Zahlenwert "{value}" bei {context}.'
        ) from exc

    if not number.is_finite():
        raise ValueError(
            f'Ungültiger Zahlenwert "{value}" bei {context}.'
        )

    return number


def format_decimal(value: Decimal) -> str:
    """
    Rundet auf maximal 8 Nachkommastellen und schreibt ein Dezimalkomma.
    Unnötige Nullen am Ende werden entfernt.
    """
    quantum = Decimal(1).scaleb(-DECIMAL_PLACES)
    rounded = value.quantize(quantum, rounding=ROUND_HALF_UP)

    text = format(rounded, "f")

    if "." in text:
        text = text.rstrip("0").rstrip(".")

    if text in {"", "-0"}:
        text = "0"

    return text.replace(".", ",")


def read_csv_table(path: Path) -> CsvTable:
    if not path.exists():
        raise FileNotFoundError(f"Datei nicht gefunden: {path}")

    if path.stat().st_size == 0:
        raise ValueError(f"CSV-Datei ist leer: {path}")

    with path.open("r", encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file, delimiter=";")

        if reader.fieldnames is None:
            raise ValueError(f"CSV besitzt keinen Header: {path}")

        headers = [header.strip() for header in reader.fieldnames]
        reader.fieldnames = headers

        required = {DATE_COLUMN, USD_COLUMN}
        missing = required.difference(headers)

        if missing:
            raise ValueError(
                f"{path.name}: Pflichtspalten fehlen: "
                + ", ".join(sorted(missing))
            )

        target_columns = [
            header
            for header in headers
            if header.startswith(PRICE_PREFIX) and header != USD_COLUMN
        ]

        if not target_columns:
            raise ValueError(
                f"{path.name}: Keine ausfüllbaren price_*-Spalten gefunden."
            )

        rows: list[dict[str, str]] = []

        for line_number, raw_row in enumerate(reader, start=2):
            if raw_row is None:
                continue

            if None in raw_row:
                raise ValueError(
                    f"{path.name}, Zeile {line_number}: "
                    "Mehr Werte als Header-Spalten vorhanden."
                )

            if all(
                value is None or str(value).strip() == ""
                for value in raw_row.values()
            ):
                continue

            row = {
                header: (raw_row.get(header) or "").strip()
                for header in headers
            }

            # Vor dem API-Aufruf alle Datumswerte streng prüfen.
            parse_iso_date(row[DATE_COLUMN], path.name, line_number)
            rows.append(row)

    if not rows:
        raise ValueError(f"{path.name}: Keine Datenzeilen gefunden.")

    return CsvTable(
        path=path,
        headers=headers,
        rows=rows,
        target_columns=target_columns,
    )


def row_needs_fx_data(row: dict[str, str], target_columns: list[str]) -> bool:
    if not row.get(USD_COLUMN, "").strip():
        return False

    return any(
        not row.get(column, "").strip()
        for column in target_columns
    )


def currency_from_column(column: str) -> str:
    return column.removeprefix(PRICE_PREFIX).upper()


def find_required_range(
    tables: list[CsvTable],
) -> tuple[date, date, set[str]]:
    required_dates: list[date] = []
    currencies: set[str] = set()

    for table in tables:
        for line_number, row in enumerate(table.rows, start=2):
            if not row_needs_fx_data(row, table.target_columns):
                continue

            row_date = parse_iso_date(
                row[DATE_COLUMN],
                table.path.name,
                line_number,
            )
            required_dates.append(row_date)

            for column in table.target_columns:
                if not row.get(column, "").strip():
                    currencies.add(currency_from_column(column))

    if not required_dates:
        raise RuntimeError(
            "Keine unvollständigen Zeilen mit vorhandenem price_usd gefunden."
        )

    return min(required_dates), max(required_dates), currencies


def fetch_frankfurter_csv(
    start_date: date,
    end_date: date,
    currencies: set[str],
    retries: int = 3,
) -> str:
    query = urllib.parse.urlencode(
        {
            "from": start_date.isoformat(),
            "to": end_date.isoformat(),
            "base": "USD",
            "quotes": ",".join(sorted(currencies)),
        }
    )

    url = f"{FRANKFURTER_URL}?{query}"

    request = urllib.request.Request(
        url,
        headers={
            "Accept": "text/csv",
            "User-Agent": "HashFarm-Price-Backfill/1.0",
        },
    )

    for attempt in range(1, retries + 1):
        try:
            print(
                f"Lade Frankfurter-Kurse "
                f"{start_date.isoformat()} bis {end_date.isoformat()} …"
            )

            with urllib.request.urlopen(request, timeout=60) as response:
                return response.read().decode("utf-8-sig")

        except urllib.error.HTTPError as exc:
            if exc.code == 429 and attempt < retries:
                retry_after = exc.headers.get("Retry-After")
                wait = int(retry_after) if retry_after and retry_after.isdigit() else 15 * attempt
                print(f"429 Rate Limit – warte {wait} Sekunden …")
                time.sleep(wait)
                continue

            raise RuntimeError(
                f"Frankfurter HTTP-Fehler {exc.code}: {exc.reason}"
            ) from exc

        except (urllib.error.URLError, TimeoutError) as exc:
            if attempt < retries:
                wait = 5 * attempt
                print(
                    f"Netzwerkfehler: {exc}. "
                    f"Neuer Versuch in {wait} Sekunden …"
                )
                time.sleep(wait)
                continue

            raise RuntimeError(
                f"Frankfurter konnte nicht erreicht werden: {exc}"
            ) from exc

    raise RuntimeError("Frankfurter-Abruf fehlgeschlagen.")


def parse_frankfurter_rates(
    csv_content: str,
) -> dict[str, dict[date, Decimal]]:
    """
    Erwartetes Frankfurter-v2-CSV-Format:
        date,base,quote,rate
    """
    reader = csv.DictReader(io.StringIO(csv_content))

    if reader.fieldnames is None:
        raise ValueError("Frankfurter-Antwort besitzt keinen CSV-Header.")

    normalized_headers = {
        header.strip().lower(): header
        for header in reader.fieldnames
    }

    required = {"date", "quote", "rate"}
    missing = required.difference(normalized_headers)

    if missing:
        raise ValueError(
            "Unerwartetes Frankfurter-CSV-Format. Fehlende Spalten: "
            + ", ".join(sorted(missing))
        )

    date_key = normalized_headers["date"]
    quote_key = normalized_headers["quote"]
    rate_key = normalized_headers["rate"]

    rates: dict[str, dict[date, Decimal]] = {}

    for line_number, row in enumerate(reader, start=2):
        quote = (row.get(quote_key) or "").strip().upper()
        date_text = (row.get(date_key) or "").strip()
        rate_text = (row.get(rate_key) or "").strip()

        if not quote or not date_text or not rate_text:
            continue

        try:
            rate_date = datetime.strptime(
                date_text,
                "%Y-%m-%d",
            ).date()
        except ValueError as exc:
            raise ValueError(
                f'Frankfurter-Zeile {line_number}: '
                f'ungültiges Datum "{date_text}".'
            ) from exc

        rate = parse_decimal(
            rate_text,
            f"Frankfurter {quote} am {date_text}",
        )

        rates.setdefault(quote, {})[rate_date] = rate

    if not rates:
        raise ValueError(
            "Frankfurter lieferte keine verwertbaren Wechselkurse."
        )

    return rates


class RateLookup:
    """
    Liefert für einen Kalendertag den letzten verfügbaren Kurs am
    selben Tag oder davor. Damit werden Wochenenden und Feiertage
    automatisch mit dem letzten offiziellen Kurs fortgeschrieben.
    """

    def __init__(
        self,
        rates: dict[str, dict[date, Decimal]],
    ) -> None:
        self._dates: dict[str, list[date]] = {}
        self._values: dict[str, list[Decimal]] = {}

        for currency, dated_rates in rates.items():
            sorted_items = sorted(dated_rates.items())

            self._dates[currency] = [
                item_date for item_date, _ in sorted_items
            ]
            self._values[currency] = [
                rate for _, rate in sorted_items
            ]

    def get(
        self,
        currency: str,
        target_date: date,
    ) -> Decimal | None:
        currency = currency.upper()
        dates = self._dates.get(currency)

        if not dates:
            return None

        position = bisect_right(dates, target_date) - 1

        if position < 0:
            return None

        return self._values[currency][position]


def create_backup(path: Path, run_timestamp: str) -> Path:
    backup_folder = BACKUP_DIR / run_timestamp
    backup_folder.mkdir(parents=True, exist_ok=True)

    backup_path = backup_folder / path.name
    shutil.copy2(path, backup_path)

    return backup_path


def write_csv_safely(
    table: CsvTable,
) -> None:
    temp_path = table.path.with_suffix(
        table.path.suffix + ".tmp"
    )

    try:
        with temp_path.open(
            "w",
            encoding="utf-8",
            newline="",
        ) as file:
            writer = csv.DictWriter(
                file,
                fieldnames=table.headers,
                delimiter=";",
                lineterminator="\n",
                extrasaction="ignore",
            )

            writer.writeheader()
            writer.writerows(table.rows)

        temp_path.replace(table.path)

    finally:
        if temp_path.exists():
            temp_path.unlink()


def fill_table(
    table: CsvTable,
    rate_lookup: RateLookup,
) -> tuple[int, int, set[str]]:
    filled_cells = 0
    changed_rows = 0
    missing_currencies: set[str] = set()

    for line_number, row in enumerate(table.rows, start=2):
        if not row_needs_fx_data(row, table.target_columns):
            continue

        row_date = parse_iso_date(
            row[DATE_COLUMN],
            table.path.name,
            line_number,
        )

        usd_text = row.get(USD_COLUMN, "").strip()

        try:
            usd_price = parse_decimal(
                usd_text,
                f"{table.path.name}, Zeile {line_number}, price_usd",
            )
        except ValueError as exc:
            print(f"  ⚠️ {exc} Zeile wird übersprungen.")
            continue

        row_changed = False

        for column in table.target_columns:
            # Bestehende Werte niemals überschreiben.
            if row.get(column, "").strip():
                continue

            currency = currency_from_column(column)
            fx_rate = rate_lookup.get(currency, row_date)

            if fx_rate is None:
                missing_currencies.add(currency)
                continue

            row[column] = format_decimal(
                usd_price * fx_rate
            )

            filled_cells += 1
            row_changed = True

        if row_changed:
            changed_rows += 1

    return filled_cells, changed_rows, missing_currencies


def select_files(
    supplied_files: list[str],
) -> list[Path]:
    if supplied_files:
        return [
            DATA_DIR / filename
            for filename in supplied_files
        ]

    # Ohne Dateiangaben werden alle neuen Preislisten geprüft.
    return sorted(DATA_DIR.glob("*_prices.csv"))


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Füllt leere price_*-Spalten anhand vorhandener "
            "USD-Preise und historischer Frankfurter-Wechselkurse."
        )
    )

    parser.add_argument(
        "files",
        nargs="*",
        help=(
            "Optionale CSV-Dateinamen innerhalb data/price_lists/. "
            "Ohne Angabe werden alle *_prices.csv geprüft."
        ),
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Berechnet Änderungen, schreibt aber keine Dateien.",
    )

    args = parser.parse_args()

    paths = select_files(args.files)

    if not paths:
        print(
            f"Keine *_prices.csv-Dateien in {DATA_DIR} gefunden.",
            file=sys.stderr,
        )
        return 1

    tables: list[CsvTable] = []

    try:
        for path in paths:
            tables.append(read_csv_table(path))

        earliest_date, latest_date, currencies = find_required_range(
            tables
        )

    except RuntimeError as exc:
        print(f"ℹ️ {exc}")
        return 0

    except Exception as exc:
        print(f"❌ {exc}", file=sys.stderr)
        return 1

    fx_start = earliest_date - timedelta(
        days=FX_LOOKBACK_DAYS
    )

    print(
        f"Unvollständiger Zeitraum: "
        f"{earliest_date.isoformat()} bis {latest_date.isoformat()}"
    )
    print(
        f"Benötigte Währungen ({len(currencies)}): "
        + ", ".join(sorted(currencies))
    )

    try:
        fx_csv = fetch_frankfurter_csv(
            start_date=fx_start,
            end_date=latest_date,
            currencies=currencies,
        )

        rates = parse_frankfurter_rates(fx_csv)
        rate_lookup = RateLookup(rates)

    except Exception as exc:
        print(f"❌ {exc}", file=sys.stderr)
        return 1

    run_timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")

    total_cells = 0
    total_rows = 0
    changed_files = 0
    all_missing_currencies: set[str] = set()

    for table in tables:
        filled_cells, changed_rows, missing_currencies = fill_table(
            table,
            rate_lookup,
        )

        all_missing_currencies.update(missing_currencies)

        if filled_cells == 0:
            print(f"ℹ️ {table.path.name}: keine Änderungen")
            continue

        print(
            f"✅ {table.path.name}: "
            f"{filled_cells} Felder in {changed_rows} Zeilen ergänzt"
        )

        total_cells += filled_cells
        total_rows += changed_rows
        changed_files += 1

        if args.dry_run:
            continue

        if CREATE_BACKUPS:
            backup_path = create_backup(
                table.path,
                run_timestamp,
            )
            print(
                f"   Backup: "
                f"{backup_path.relative_to(BASE_DIR)}"
            )

        write_csv_safely(table)

    if all_missing_currencies:
        print(
            "\n⚠️ Für folgende Währungen war am benötigten Datum "
            "kein vorheriger Frankfurter-Kurs verfügbar:"
        )
        print(", ".join(sorted(all_missing_currencies)))
        print("Die betreffenden Felder blieben leer.")

    if args.dry_run:
        print("\nDRY RUN: Es wurden keine Dateien verändert.")

    print(
        "\nFertig: "
        f"{changed_files} Dateien, "
        f"{total_rows} Zeilen, "
        f"{total_cells} Währungsfelder ergänzt."
    )

    return 0


if __name__ == "__main__":
    sys.exit(main())

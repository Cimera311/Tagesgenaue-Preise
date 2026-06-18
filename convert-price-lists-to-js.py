#!/usr/bin/env python3
"""
Konvertiert die von fill_price_lists_paprika.py erzeugten CSV-Dateien
aus data/price_lists/ in einzelne JavaScript-Dateien unter src/scripts/.

Verwendung:
    python csv_to_js.py
"""

from __future__ import annotations

import csv
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


BASE_DIR = Path(__file__).resolve().parent
INPUT_DIR = BASE_DIR / "data" / "price_lists"
OUTPUT_DIR = BASE_DIR / "src" / "scripts"

# False:
# Preise bleiben Strings mit deutschem Dezimalkomma:
# "63915,48"
#
# True:
# Preisfelder werden echte JavaScript-Zahlen:
# 63915.48
#
# Für Berechnungen in JavaScript ist True normalerweise besser.
PRICE_VALUES_AS_NUMBERS = True

FILES = [
    {
        "input": "bitcoin_prices.csv",
        "output": "price-data-btc.js",
        "variable": "btcPriceData",
        "label": "Bitcoin",
    },
    {
        "input": "gomining_prices.csv",
        "output": "price-data-gmt.js",
        "variable": "gmtPriceData",
        "label": "GoMining",
    },
    {
        "input": "ethereum_prices.csv",
        "output": "price-data-eth.js",
        "variable": "ethPriceData",
        "label": "Ethereum",
    },
    {
        "input": "bnb_prices.csv",
        "output": "price-data-bnb.js",
        "variable": "bnbPriceData",
        "label": "BNB",
    },
    {
        "input": "solana_prices.csv",
        "output": "price-data-sol.js",
        "variable": "solPriceData",
        "label": "Solana",
    },
    {
        "input": "toncoin_prices.csv",
        "output": "price-data-ton.js",
        "variable": "tonPriceData",
        "label": "Toncoin",
    },
    {
        "input": "usdt_prices.csv",
        "output": "price-data-usdt.js",
        "variable": "usdtPriceData",
        "label": "Tether",
    },
    {
        "input": "usdc_prices.csv",
        "output": "price-data-usdc.js",
        "variable": "usdcPriceData",
        "label": "USD Coin",
    },
]

REQUIRED_HEADERS = {
    "date_iso",
    "time_berlin",
    "symbol",
    "price_usd",
}


def parse_price_value(value: str) -> str | float | None:
    """
    Wandelt Preisfelder optional in echte Zahlen um.

    Leere Felder werden im Zahlenmodus zu None.
    In JavaScript erscheint dies als null.
    """
    value = value.strip()

    if not PRICE_VALUES_AS_NUMBERS:
        return value

    if value == "":
        return None

    normalized = value.replace(",", ".")

    try:
        number = float(normalized)
    except ValueError as exc:
        raise ValueError(
            f'Ungültiger Preiswert: "{value}"'
        ) from exc

    if not math.isfinite(number):
        raise ValueError(
            f'Ungültiger Preiswert: "{value}"'
        )

    return number


def csv_to_date_object(
    csv_file_path: Path,
) -> dict[str, dict[str, Any]]:
    """
    Liest eine Semikolon-getrennte CSV-Datei ein.

    Ergebnis:

    {
        "2026-06-13": {
            "date_iso": "2026-06-13",
            "time_berlin": "02:00",
            "symbol": "BTC",
            "price_eur": "...",
            "price_usd": "..."
        }
    }
    """

    if not csv_file_path.exists():
        raise FileNotFoundError(
            f"CSV-Datei nicht gefunden: {csv_file_path}"
        )

    if csv_file_path.stat().st_size == 0:
        raise ValueError(
            f"CSV-Datei ist leer: {csv_file_path}"
        )

    data: dict[str, dict[str, Any]] = {}

    # utf-8-sig entfernt bei Bedarf automatisch ein UTF-8-BOM.
    with csv_file_path.open(
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as file:

        reader = csv.DictReader(
            file,
            delimiter=";",
        )

        if reader.fieldnames is None:
            raise ValueError(
                f"CSV-Datei besitzt keinen Header: {csv_file_path}"
            )

        headers = [
            header.strip()
            for header in reader.fieldnames
        ]

        reader.fieldnames = headers

        missing_headers = REQUIRED_HEADERS.difference(headers)

        if missing_headers:
            missing = ", ".join(
                sorted(missing_headers)
            )

            raise ValueError(
                f"Pflichtspalten fehlen in "
                f"{csv_file_path.name}: {missing}"
            )

        for line_number, raw_row in enumerate(
            reader,
            start=2,
        ):
            if raw_row is None:
                continue

            # Komplett leere Zeilen ignorieren.
            if all(
                value is None or str(value).strip() == ""
                for value in raw_row.values()
            ):
                continue

            row: dict[str, Any] = {}

            for header in headers:
                raw_value = raw_row.get(header)

                if raw_value is None:
                    raise ValueError(
                        f"Fehlender Wert in "
                        f"{csv_file_path.name}, "
                        f"Zeile {line_number}, "
                        f"Spalte {header}"
                    )

                value = raw_value.strip()

                if header.startswith("price_"):
                    row[header] = parse_price_value(value)
                else:
                    row[header] = value

            date_iso = str(row["date_iso"])

            try:
                datetime.strptime(
                    date_iso,
                    "%Y-%m-%d",
                )
            except ValueError as exc:
                raise ValueError(
                    f'Ungültiges date_iso in '
                    f'{csv_file_path.name}, '
                    f'Zeile {line_number}: '
                    f'"{date_iso}"'
                ) from exc

            # Bei einem doppelten Datum gewinnt
            # die zuletzt gelesene Zeile.
            data[date_iso] = row

    if not data:
        raise ValueError(
            f"CSV enthält keine Datenzeilen: {csv_file_path}"
        )

    # Chronologisch nach Datum sortieren.
    return dict(
        sorted(
            data.items(),
            key=lambda item: item[0],
        )
    )


def build_js_content(
    variable_name: str,
    data: dict[str, dict[str, Any]],
    source_filename: str,
) -> str:

    generated_at = (
        datetime.now(timezone.utc)
        .isoformat()
        .replace("+00:00", "Z")
    )

    json_content = json.dumps(
        data,
        ensure_ascii=False,
        indent=2,
        allow_nan=False,
    )

    return (
        f"// Auto-generiert am {generated_at}\n"
        f"// Quelle: data/price_lists/{source_filename}\n"
        "// Nicht manuell bearbeiten – "
        "stattdessen CSV neu konvertieren.\n\n"

        f"const {variable_name} = {json_content};\n\n"

        "if (typeof globalThis !== 'undefined') {\n"
        f"  globalThis.{variable_name} = {variable_name};\n"
        "}\n\n"

        "if (typeof module !== 'undefined' "
        "&& module.exports) {\n"
        f"  module.exports = {variable_name};\n"
        "}\n"
    )


def write_text_safely(
    output_path: Path,
    content: str,
) -> None:
    """
    Schreibt zuerst in eine temporäre Datei.

    So bleibt bei einem Fehler nicht versehentlich
    eine unvollständige JS-Datei zurück.
    """

    temp_path = output_path.with_suffix(
        output_path.suffix + ".tmp"
    )

    try:
        temp_path.write_text(
            content,
            encoding="utf-8",
            newline="\n",
        )

        temp_path.replace(output_path)

    finally:
        if temp_path.exists():
            temp_path.unlink()


def convert_csv_to_js() -> int:
    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    converted = 0
    skipped = 0
    failed = 0

    for file_config in FILES:
        input_path = (
            INPUT_DIR / file_config["input"]
        )

        output_path = (
            OUTPUT_DIR / file_config["output"]
        )

        if not input_path.exists():
            print(
                f"⚠️  {file_config['label']}: "
                f"{file_config['input']} fehlt – "
                "übersprungen"
            )

            skipped += 1
            continue

        try:
            data = csv_to_date_object(
                input_path
            )

            js_content = build_js_content(
                variable_name=file_config["variable"],
                data=data,
                source_filename=file_config["input"],
            )

            write_text_safely(
                output_path,
                js_content,
            )

            relative_output = output_path.relative_to(
                BASE_DIR
            )

            print(
                f"✅ {file_config['label']}: "
                f"{len(data)} Tage → "
                f"{relative_output}"
            )

            converted += 1

        except Exception as exc:
            print(
                f"❌ {file_config['label']}: {exc}"
            )

            failed += 1

    print(
        "\nFertig: "
        f"{converted} konvertiert, "
        f"{skipped} übersprungen, "
        f"{failed} Fehler."
    )

    if failed > 0 or converted == 0:
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(
        convert_csv_to_js()
    )
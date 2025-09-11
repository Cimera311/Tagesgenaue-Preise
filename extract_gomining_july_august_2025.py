import csv
from datetime import datetime

eur_file = "./data/inputfile_legacy/CoinPaprika_GOMINING_price_custom_2025_EURO.csv"
usd_file = "./data/inputfile_legacy/CoinPaprika_GOMINING_price_custom_2025_USD.csv"
output_file = "./converted/gomining_july_august_2025.csv"

# EUR-Daten laden
eur_prices = {}
with open(eur_file, newline='', encoding='utf-8') as f:
    reader = csv.reader(f)
    next(reader)  # Header überspringen
    for row in reader:
        date_str = row[0].split()[0]  # "2025-07-13 00:00:00" -> "2025-07-13"
        if date_str.startswith("2025-07") or date_str.startswith("2025-08"):
            eur_prices[date_str] = row[1].replace('.', ',')

# USD-Daten laden
usd_prices = {}
with open(usd_file, newline='', encoding='utf-8') as f:
    reader = csv.reader(f)
    next(reader)  # Header überspringen
    for row in reader:
        date_str = row[0].split()[0]
        if date_str.startswith("2025-07") or date_str.startswith("2025-08"):
            usd_prices[date_str] = row[1].replace('.', ',')

# Alle relevanten Tage
all_dates = sorted(set(list(eur_prices.keys()) + list(usd_prices.keys())))

with open(output_file, 'w', newline='', encoding='utf-8') as f:
    fieldnames = ['date_iso', 'time_berlin', 'symbol', 'price_eur', 'price_usd']
    writer = csv.DictWriter(f, fieldnames=fieldnames, delimiter=';')
    writer.writeheader()
    for date_iso in all_dates:
        writer.writerow({
            'date_iso': date_iso,
            'time_berlin': '01:00',
            'symbol': 'GOMINING',
            'price_eur': eur_prices.get(date_iso, ''),
            'price_usd': usd_prices.get(date_iso, '')
        })

print("Juli und August 2025 extrahiert und formatiert.")
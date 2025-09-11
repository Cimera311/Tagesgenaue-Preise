import csv

usd_file = "./data/inputfile_legacy/GOMINING-usd-max (3).csv"
eur_file = "./converted/converted_CoinPaprika_GOMINING_price_custom_2025_EURO.csv"
output_file = "./converted/merged_gomining_eur_usd_all_dates.csv"

# USD-Daten laden (Datum -> Preis)
usd_prices = {}
with open(usd_file, newline='', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    for row in reader:
        date_iso = row['snapped_at'][:10]
        usd_prices[date_iso] = str(row['price']).replace('.', ',')

# EUR-Daten laden (Datum -> Preis)
eur_prices = {}
with open(eur_file, newline='', encoding='utf-8') as f:
    reader = csv.DictReader(f, delimiter=';')
    for row in reader:
        date_iso = row['date_iso']
        eur_prices[date_iso] = row['price_eur']

# Alle Daten-Tage aus USD-Datei
all_dates = sorted(usd_prices.keys())

with open(output_file, 'w', newline='', encoding='utf-8') as f:
    fieldnames = ['date_iso', 'time_berlin', 'symbol', 'price_eur', 'price_usd']
    writer = csv.DictWriter(f, fieldnames=fieldnames, delimiter=';')
    writer.writeheader()
    for date_iso in all_dates:
        writer.writerow({
            'date_iso': date_iso,
            'time_berlin': '',  # leer lassen, kannst du später ergänzen
            'symbol': 'GOMINING',
            'price_eur': eur_prices.get(date_iso, ''),
            'price_usd': usd_prices.get(date_iso, '')
        })

print("Alle USD-Daten übernommen. EUR-Preise werden nur eingetragen, wenn vorhanden.")
import csv

eur_file = "./converted/converted_CoinPaprika_BTC_price_custom_2025BTC_EURO.csv"
usd_file = "./data/inputfile_legacy/btc-usd-2024-2025.csv"
output_file = "./converted/merged_btc_eur_usd_2025.csv"

# USD-Daten laden (Datum -> Preis)
usd_prices = {}
with open(usd_file, newline='', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    for row in reader:
        date_iso = row['snapped_at'][:10]
        usd_prices[date_iso] = row['price']

with open(eur_file, newline='', encoding='utf-8') as infile, open(output_file, 'w', newline='', encoding='utf-8') as outfile:
    reader = csv.DictReader(infile, delimiter=';')
    writer = csv.writer(outfile, delimiter=';')
    writer.writerow(reader.fieldnames)  # Header übernehmen

    for row in reader:
        date_iso = row['date_iso']
        price_usd = usd_prices.get(date_iso, '')
        price_usd = str(price_usd).replace('.', ',') if price_usd else ''
        row['price_usd'] = price_usd
        writer.writerow([row['date_iso'], row['time_berlin'], row['symbol'], row['price_eur'], row['price_usd']])

print("Merge abgeschlossen.")
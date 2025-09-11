import csv

existing_file = "./data/bitcoin_eur.csv"
new_file = "./converted/merged_btc_eur_usd_2025.csv"
output_file = "./data/bitcoin_eur_updated_2025.csv"

data = {}
with open(existing_file, newline='', encoding='utf-8') as f:
    reader = csv.DictReader(f, delimiter=';')
    for row in reader:
        if row['symbol'] == 'BTC' and row['date_iso'].startswith('2025'):
            data[row['date_iso']] = row

with open(new_file, newline='', encoding='utf-8') as f:
    reader = csv.DictReader(f, delimiter=';')
    for row in reader:
        data[row['date_iso']] = row

with open(output_file, 'w', newline='', encoding='utf-8') as f:
    fieldnames = ['date_iso', 'time_berlin', 'symbol', 'price_eur', 'price_usd']
    writer = csv.DictWriter(f, fieldnames=fieldnames, delimiter=';')
    writer.writeheader()
    for date in sorted(data.keys()):
        writer.writerow(data[date])

print("Update abgeschlossen: BTC 2025")
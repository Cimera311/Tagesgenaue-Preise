import csv

existing_file = "./data/gominingtoken_eur.csv"
new_file = "./converted/merged_gomining_eur_usd_2024.csv"
output_file = "./data/gominingtoken_eur_updated_2024.csv"

data = {}
with open(existing_file, newline='', encoding='utf-8') as f:
    reader = csv.DictReader(f, delimiter=';')
    for row in reader:
        if row['symbol'] == 'GOMINING' and row['date_iso'].startswith('2024'):
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

print("Update abgeschlossen: GOMINING 2024")
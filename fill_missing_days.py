import csv
from datetime import datetime, timedelta

existing_file = "./data/bitcoin_eur.csv"
new_file = "./converted/merged_btc_eur_usd_2025.csv"
output_file = "./data/bitcoin_eur_filled.csv"

def normalize_date(date_str):
    # Holt nur das Datum (YYYY-MM-DD)
    return date_str[:10]

# Alle Daten sammeln
data = {}
with open(existing_file, newline='', encoding='utf-8') as f:
    reader = csv.DictReader(f, delimiter=';')
    for row in reader:
        key = normalize_date(row['date_iso'])
        data[key] = row

with open(new_file, newline='', encoding='utf-8') as f:
    reader = csv.DictReader(f, delimiter=';')
    for row in reader:
        key = normalize_date(row['date_iso'])
        data[key] = row

# Alle Datumswerte bestimmen
all_dates = sorted(data.keys())
if all_dates:
    start_date = datetime.strptime(all_dates[0], "%Y-%m-%d")
    end_date = datetime.strptime(all_dates[-1], "%Y-%m-%d")
    # Alle Tage im Bereich erzeugen
    full_dates = [(start_date + timedelta(days=i)).strftime("%Y-%m-%d")
                 for i in range((end_date - start_date).days + 1)]
else:
    full_dates = []

# Felder für die CSV
fieldnames = ['date_iso', 'time_berlin', 'symbol', 'price_eur', 'price_usd']

with open(output_file, 'w', newline='', encoding='utf-8') as f:
    writer = csv.DictWriter(f, fieldnames=fieldnames, delimiter=';')
    writer.writeheader()
    for date in full_dates:
        if date in data:
            writer.writerow(data[date])
        else:
            # Leere Zeile für fehlenden Tag
            writer.writerow({
                'date_iso': date,
                'time_berlin': '',
                'symbol': 'BTC',
                'price_eur': '',
                'price_usd': ''
            })

print("Fehlende Tage wurden ergänzt.")
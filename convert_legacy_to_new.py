import csv
import os

input_dir = "./data/inputfile_legacy"
output_dir = "./converted"

if not os.path.exists(output_dir):
    os.makedirs(output_dir)

for filename in os.listdir(input_dir):
    if filename.endswith(".csv"):
        input_path = os.path.join(input_dir, filename)
        output_path = os.path.join(output_dir, f"converted_{filename}")

        # Symbol aus Dateiname extrahieren (z.B. BTC, GOMINING)
        symbol = filename.split('_')[1] if '_' in filename else 'UNKNOWN'

        with open(input_path, newline='', encoding='utf-8-sig') as infile, open(output_path, 'w', newline='', encoding='utf-8') as outfile:
            reader = csv.DictReader(infile)
            writer = csv.writer(outfile, delimiter=';')
            writer.writerow(['date_iso', 'time_berlin', 'symbol', 'price_eur', 'price_usd'])
            for row in reader:
                # Jetzt sollte der Key "DateTime" heißen!
                date_iso = row['DateTime'][:10]
                time_berlin = '01:00'
                price_eur = str(row['Price']).replace('.', ',')
                price_usd = ''
                writer.writerow([date_iso, time_berlin, symbol, price_eur, price_usd])

print("Konvertierung abgeschlossen.")
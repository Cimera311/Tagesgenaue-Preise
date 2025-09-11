import csv

def load_usd_prices(usd_file):
    usd_prices = {}
    with open(usd_file, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            date_iso = row['snapped_at'][:10]
            usd_prices[date_iso] = row['price']
    return usd_prices

def load_eur_prices(eur_file):
    eur_prices = {}
    with open(eur_file, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f, delimiter=';')
        for row in reader:
            date_iso = row['date_iso']
            # Immer nur die letzte Zeile pro Datum speichern
            eur_prices[date_iso] = row
    return eur_prices

def merge_eur_usd(eur_file, usd_prices, output_file):
    eur_prices = load_eur_prices(eur_file)
    all_dates = sorted(set(list(usd_prices.keys()) + list(eur_prices.keys())))
    with open(output_file, 'w', newline='', encoding='utf-8') as outfile:
        fieldnames = ['date_iso', 'time_berlin', 'symbol', 'price_eur', 'price_usd']
        writer = csv.DictWriter(outfile, fieldnames=fieldnames, delimiter=';')
        writer.writeheader()
        for date_iso in all_dates:
            row = eur_prices.get(date_iso)
            if not row or isinstance(row, list):
                # Falls row None oder eine Liste ist, Standardwerte nehmen
                row = {
                    'date_iso': date_iso,
                    'time_berlin': '',
                    'symbol': 'GOMINING',
                    'price_eur': '',
                    'price_usd': ''
                }
            price_usd = usd_prices.get(date_iso, '')
            row['price_usd'] = str(price_usd).replace('.', ',') if price_usd else ''
            writer.writerow([row['date_iso'], row['time_berlin'], row['symbol'], row['price_eur'], row['price_usd']])

usd_file = "./data/inputfile_legacy/GOMINING-usd-max (3).csv"

# 2024
eur_file_2024 = "./converted/converted_CoinPaprika_GOMINING_price_custom_2024_EURO.csv"
output_file_2024 = "./converted/merged_gomining_eur_usd_2024.csv"
usd_prices = load_usd_prices(usd_file)
merge_eur_usd(eur_file_2024, usd_prices, output_file_2024)

# 2025
eur_file_2025 = "./converted/converted_CoinPaprika_GOMINING_price_custom_2025_EURO.csv"
output_file_2025 = "./converted/merged_gomining_eur_usd_2025.csv"
merge_eur_usd(eur_file_2025, usd_prices, output_file_2025)

print("Merge abgeschlossen.")
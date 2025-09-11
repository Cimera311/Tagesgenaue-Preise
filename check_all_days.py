import csv
from datetime import datetime, timedelta

def check_file(csv_file, symbol):
    dates_present = set()
    with open(csv_file, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f, delimiter=';')
        for row in reader:
            if row['symbol'] == symbol:
                dates_present.add(row['date_iso'])

    start_date = datetime.strptime("2024-01-01", "%Y-%m-%d")
    end_date = datetime.today() - timedelta(days=1)
    all_dates = [(start_date + timedelta(days=i)).strftime("%Y-%m-%d")
                 for i in range((end_date - start_date).days + 1)]

    missing_dates = [d for d in all_dates if d not in dates_present]
    print(f"\nFehlende Tage in {csv_file} ({symbol}):")
    if missing_dates:
        for d in missing_dates:
            print(d)
    else:
        print("Keine fehlenden Tage!")

# Pfade ggf. anpassen!
check_file("./docs/data/bitcoin_eur.csv", "BTC")
check_file("./docs/data/gominingtoken_eur.csv", "GOMINING")
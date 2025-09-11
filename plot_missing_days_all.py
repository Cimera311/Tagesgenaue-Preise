import csv
import os
from datetime import datetime, timedelta

input_dir = "./data/inputfile_legacy/updated"

for filename in os.listdir(input_dir):
    if filename.endswith(".csv"):
        csv_file = os.path.join(input_dir, filename)
        dates_present = set()
        with open(csv_file, newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f, delimiter=';')
            for row in reader:
                date_str = row['date_iso'][:10]
                dates_present.add(date_str)

        if dates_present:
            start_date = min(dates_present)
            end_date = max(dates_present)
            start_dt = datetime.strptime(start_date, "%Y-%m-%d")
            end_dt = datetime.strptime(end_date, "%Y-%m-%d")
            all_dates = [(start_dt + timedelta(days=i)).strftime("%Y-%m-%d")
                         for i in range((end_dt - start_dt).days + 1)]
        else:
            all_dates = []

        missing_dates = [d for d in all_dates if d not in dates_present]

        # Fehlende Tage ausgeben
        print(f"\nFehlende Tage in {filename}:")
        if missing_dates:
            for d in missing_dates:
                print(d)
        else:
            print("Keine fehlenden Tage!")
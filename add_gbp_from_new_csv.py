import csv
from datetime import datetime

# Lade GBP-Daten aus der neuen CSV
print("Lade bitcoin2024.csv...")
gbp_prices = {}  # Datum -> GBP-Preis

with open('neue_Preislisten/bitcoin2024.csv', 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f, delimiter=';')
    
    for row in reader:
        # Konvertiere Timestamp zu Datum
        timestamp = float(row['timeClose'].replace(',', '.'))
        date = datetime.fromtimestamp(timestamp / 1000)  # Millisekunden zu Sekunden
        date_str = date.strftime('%Y-%m-%d')
        
        # Nehme den Close-Preis
        price_gbp = float(row['priceClose'].replace(',', '.'))
        
        # Speichere den letzten Preis für jeden Tag (überschreibt frühere Preise des Tages)
        gbp_prices[date_str] = price_gbp

print(f"Geladene GBP-Preise: {len(gbp_prices)}")
print(f"Erster Eintrag: {min(gbp_prices.keys())}")
print(f"Letzter Eintrag: {max(gbp_prices.keys())}")

# Lade bitcoin_eur.csv
print("\nLade bitcoin_eur.csv...")
with open('data/bitcoin_eur.csv', 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f, delimiter=';')
    rows = list(reader)

print(f"Bitcoin EUR Zeilen: {len(rows)}")

# Füge GBP-Preise hinzu
matched = 0
missing = 0

for row in rows:
    date = row['date_iso']
    
    if date in gbp_prices:
        # Formatiere mit deutscher Notation (Komma als Dezimaltrennzeichen)
        row['price_gbp'] = f"{gbp_prices[date]:.2f}".replace('.', ',')
        matched += 1
    else:
        row['price_gbp'] = ''
        missing += 1
        print(f"  Kein GBP-Preis für {date}")

# Speichere aktualisierte bitcoin_eur.csv
print(f"\nSpeichere bitcoin_eur.csv...")
with open('data/bitcoin_eur.csv', 'w', encoding='utf-8', newline='') as f:
    fieldnames = ['date_iso', 'time_berlin', 'symbol', 'price_eur', 'price_usd', 'price_gbp']
    writer = csv.DictWriter(f, fieldnames=fieldnames, delimiter=';', extrasaction='ignore')
    writer.writeheader()
    writer.writerows(rows)

print(f"\nFertig! {matched} von {len(rows)} Zeilen haben jetzt GBP-Preise.")
print(f"Fehlende GBP-Preise: {missing}")

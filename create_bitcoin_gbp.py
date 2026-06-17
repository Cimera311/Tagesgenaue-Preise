import csv
from datetime import datetime

# Lade GBP-Daten aus der neuen CSV
print("Lade bitcoin2024.csv...")
gbp_data = []

with open('neue_Preislisten/bitcoin2024.csv', 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f, delimiter=';')
    
    for row in reader:
        # Konvertiere Timestamp zu Datum
        # Das "kryptische" Format ist ein Unix-Timestamp in Millisekunden (z.B. 1,77755E+12)
        # 1,77755E+12 = 1777550000000 Millisekunden seit 1970-01-01
        timestamp = float(row['timeClose'].replace(',', '.'))
        date = datetime.fromtimestamp(timestamp / 1000)  # Millisekunden zu Sekunden
        date_str = date.strftime('%Y-%m-%d')
        time_str = date.strftime('%H:%M')
        
        # Nehme den Close-Preis
        price_gbp = float(row['priceClose'].replace(',', '.'))
        
        gbp_data.append({
            'date_iso': date_str,
            'time_berlin': time_str,
            'symbol': 'BTC',
            'price_gbp': f"{price_gbp:.2f}".replace('.', ',')
        })

print(f"Geladene GBP-Preise: {len(gbp_data)}")
print(f"Erster Eintrag: {gbp_data[-1]['date_iso']}")  # Rückwärts sortiert
print(f"Letzter Eintrag: {gbp_data[0]['date_iso']}")

# Speichere bitcoin_gbp.csv
print("\nSpeichere bitcoin_gbp.csv...")
with open('data/bitcoin_gbp.csv', 'w', encoding='utf-8', newline='') as f:
    fieldnames = ['date_iso', 'time_berlin', 'symbol', 'price_gbp']
    writer = csv.DictWriter(f, fieldnames=fieldnames, delimiter=';')
    writer.writeheader()
    writer.writerows(gbp_data)

print(f"\nFertig! {len(gbp_data)} Zeilen in bitcoin_gbp.csv geschrieben.")

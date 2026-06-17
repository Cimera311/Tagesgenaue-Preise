import csv
from datetime import datetime

# Dateipfade
btc_eur_file = r'c:\Users\cimer\Documents\GitHub\Tagesgenaue-Preise\data\bitcoin_eur.csv'
gbp_file_2024 = r'c:\Users\cimer\Documents\GitHub\Tagesgenaue-Preise\neue_Preislisten\Bitcoin_1.1.2024-31.12.2024_historical_data_coinmarketcap3.csv'
gbp_file_2025 = r'c:\Users\cimer\Documents\GitHub\Tagesgenaue-Preise\neue_Preislisten\Bitcoin_1.1.2025-31.12.2025_historical_data_coinmarketcap2.csv'

def parse_gbp_price(price_str):
    """Konvertiert den speziellen Preis-Format zu GBP.
    Beispiel: 765.865.700.772.801 -> 765865,70 Pence -> 7658,66 GBP
    """
    # Entferne alle Punkte
    price_clean = price_str.replace('.', '')
    # Konvertiere zu float und teile durch 1 Milliarde (um zu Pence zu kommen)
    price_pence = float(price_clean) / 1000000000
    # Teile durch 100 um von Pence zu GBP zu konvertieren
    price_gbp = price_pence / 100
    return price_gbp

# Lade GBP-Daten aus beiden Dateien
print("Lade GBP-Dateien...")
gbp_dict = {}

for gbp_file, year in [(gbp_file_2024, '2024'), (gbp_file_2025, '2025')]:
    print(f"  Lade {year}...")
    with open(gbp_file, 'r', encoding='utf-8-sig') as f:  # utf-8-sig entfernt BOM falls vorhanden
        reader = csv.DictReader(f, delimiter=';')
        # Debug: Zeige Feldnamen
        print(f"    Feldnamen: {reader.fieldnames}")
        for row in reader:
            # Extrahiere Datum aus timeOpen (Format: 2024-12-31T00:00:00.000Z)
            date_str = row['timeOpen'].split('T')[0]
            # Konvertiere close-Preis zu GBP
            try:
                price_gbp = parse_gbp_price(row['close'])
                gbp_dict[date_str] = price_gbp
            except (ValueError, KeyError) as e:
                print(f"    Fehler bei {date_str}: {e}")

print(f"Geladene GBP-Preise: {len(gbp_dict)}")

# Lade bitcoin_eur.csv und füge GBP-Spalte hinzu
print("\nLade bitcoin_eur.csv...")
rows = []
header = None
matched_count = 0
total_count = 0

with open(btc_eur_file, 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f, delimiter=';')
    # Erstelle neuen Header mit GBP-Spalte (falls nicht vorhanden)
    original_header = list(reader.fieldnames)
    if 'price_gbp' not in original_header:
        header = original_header + ['price_gbp']
    else:
        header = original_header
    print(f"  Header: {header}")
    
    for row in reader:
        total_count += 1
        date_iso = row['date_iso']
        
        # Suche nach GBP-Preis für dieses Datum
        if date_iso in gbp_dict:
            # Formatiere mit Komma als Dezimaltrennzeichen (wie in der Originaldatei)
            row['price_gbp'] = f"{gbp_dict[date_iso]:.4f}".replace('.', ',')
            matched_count += 1
        else:
            row['price_gbp'] = ''
        
        rows.append(row)

# Speichere aktualisierte Datei
print("\nSpeichere aktualisierte bitcoin_eur.csv...")
with open(btc_eur_file, 'w', encoding='utf-8', newline='') as f:
    writer = csv.DictWriter(f, fieldnames=header, delimiter=';', extrasaction='ignore')
    writer.writeheader()
    writer.writerows(rows)

print(f"\nFertig! {matched_count} von {total_count} Zeilen haben jetzt GBP-Preise.")
print(f"Fehlende GBP-Preise: {total_count - matched_count}")

import csv

# Dateipfad
btc_eur_file = r'c:\Users\cimer\Documents\GitHub\Tagesgenaue-Preise\data\bitcoin_eur.csv'

# Lade Daten
print("Lade bitcoin_eur.csv...")
rows = []

with open(btc_eur_file, 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f, delimiter=';')
    header = reader.fieldnames
    
    fixed_count = 0
    total_count = 0
    
    for row in reader:
        total_count += 1
        
        # Konvertiere Werte
        try:
            price_eur = float(row['price_eur'].replace(',', '.'))
            price_usd = float(row['price_usd'].replace(',', '.'))
            price_gbp = float(row['price_gbp'].replace(',', '.')) if row['price_gbp'] else 0
            
            # GBP sollte in ähnlicher Größenordnung wie USD sein (ca. 75-95% von USD)
            # Historisch: 1 USD ≈ 0.75-0.85 GBP
            expected_gbp_min = price_usd * 0.65  # Untere Grenze (mit etwas Puffer)
            expected_gbp_max = price_usd * 0.95  # Obere Grenze
            
            # Prüfe ob GBP-Wert plausibel ist
            if price_gbp > 0 and (price_gbp < expected_gbp_min or price_gbp > expected_gbp_max):
                # Versuche Multiplikator zu finden
                found = False
                for mult in [10, 100, 1000, 10000]:
                    corrected = price_gbp * mult
                    if expected_gbp_min <= corrected <= expected_gbp_max:
                        print(f"{row['date_iso']}: Korrigiere {price_gbp:,.2f} → {corrected:,.2f} GBP (×{mult})")
                        row['price_gbp'] = f"{corrected:.4f}".replace('.', ',')
                        fixed_count += 1
                        found = True
                        break
                
                if not found:
                    print(f"{row['date_iso']}: WARNUNG - Konnte {price_gbp:,.2f} GBP nicht korrigieren (USD: {price_usd:,.2f})")
        except (ValueError, KeyError) as e:
            print(f"Fehler bei {row.get('date_iso', '?')}: {e}")
        
        rows.append(row)

# Speichere korrigierte Datei
print(f"\nSpeichere korrigierte bitcoin_eur.csv...")
with open(btc_eur_file, 'w', encoding='utf-8', newline='') as f:
    writer = csv.DictWriter(f, fieldnames=header, delimiter=';')
    writer.writeheader()
    writer.writerows(rows)

print(f"\nFertig! {fixed_count} von {total_count} Werten korrigiert.")

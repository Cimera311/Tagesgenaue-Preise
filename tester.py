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

        with open(input_path, newline='', encoding='utf-8') as infile:
            reader = csv.DictReader(infile)
            print(f"{filename} Spaltennamen:", reader.fieldnames)
            break  # Nur einmal ausgeben und dann Skript beenden
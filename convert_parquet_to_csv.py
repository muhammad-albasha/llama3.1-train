import pandas as pd

# Pfad zur Parquet-Datei
parquet_file = './python_code_instructions_18k_alpaca/data/train-00000-of-00001-8b6e212f3e1ece96.parquet'

# Pfad zur zu speichernden CSV-Datei
csv_file = './python_code_instructions_18k_alpaca/dataset.csv'

# Lesen der Parquet-Datei
df = pd.read_parquet(parquet_file)

# Speichern als CSV-Datei
df.to_csv(csv_file, index=False)

print(f"Die Datei wurde erfolgreich als {csv_file} gespeichert.")

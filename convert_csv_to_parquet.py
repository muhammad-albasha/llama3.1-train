import pandas as pd

# Pfad zur CSV-Datei
csv_file = 'dataset.csv'

# Pfad zur zu speichernden Parquet-Datei
parquet_file = 'train-00000-of-00001.parquet'

# Lesen der CSV-Datei
df = pd.read_csv(csv_file)

# Speichern als Parquet-Datei
df.to_parquet(parquet_file, engine='pyarrow', index=False)

print(f"Die Datei wurde erfolgreich als {parquet_file} gespeichert.")

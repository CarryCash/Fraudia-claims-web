import pandas as pd 
import sqlite3
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAW_CSV = PROJECT_ROOT / "data" / "raw" / "insurance_claims.csv"
PROCESSED_CSV = PROJECT_ROOT / "data" / "processed" / "siniestros_processed.csv"
DB_PATH = PROJECT_ROOT / "fraudia.db"
def main() -> None:
    conn = sqlite3.connect(DB_PATH)
    # Raw table
    print("Cargando raw_siniestros …")
    raw_df = pd.read_csv(RAW_CSV)
    raw_df.to_sql("raw_siniestros", conn, if_exists="replace", index=False)
    # Processed table
    print("Cargando processed_siniestros …")
    proc_df = pd.read_csv(PROCESSED_CSV)
    proc_df.to_sql("processed_siniestros", conn, if_exists="replace", index=False)
    conn.close()
    print(f"Base SQLite creada en {DB_PATH}")
if __name__ == "__main__":
    main()
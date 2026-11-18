"""Project settings. Edit COLUMN_MAP to match the real dataset's column names."""
from pathlib import Path

ROOT = Path(__file__).resolve().parent
RAW_CSV = ROOT / "data" / "raw" / "results.csv"      # put the real IFSC CSV here
DB_PATH = ROOT / "data" / "clean" / "climbing.db"
OUT_DIR = ROOT / "outputs"
SQL_DIR = ROOT / "sql"

# raw CSV column name  ->  canonical name used by the pipeline.
# Left side = what the real file calls it. Change ONLY the left side.
COLUMN_MAP = {
    "athlete": "athlete",
    "country": "country",
    "event": "event",
    "year": "year",
    "gender": "gender",
    "round": "round",
    "rank": "rank",
}

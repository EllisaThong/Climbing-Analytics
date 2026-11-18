"""Raw results CSV -> cleaned, normalised SQLite database.
Usage: python -m src.load_clean [path/to/results.csv]"""
import sqlite3
import sys
from pathlib import Path

import pandas as pd

from config import COLUMN_MAP, DB_PATH, RAW_CSV, SQL_DIR


def normalise_stage(value):
    v = str(value).strip().lower()
    if "qual" in v:
        return "qualification"
    if "semi" in v:
        return "semi-final"
    if "final" in v:
        return "final"
    return None


def normalise_gender(value):
    v = str(value).strip().lower()
    if v in {"m", "men", "male", "man"}:
        return "men"
    if v in {"w", "f", "women", "female", "woman"}:
        return "women"
    return None


def clean(raw: pd.DataFrame) -> pd.DataFrame:
    missing = [c for c in COLUMN_MAP if c not in raw.columns]
    if missing:
        raise SystemExit(f"Columns missing from CSV: {missing}\n"
                         f"Columns found: {list(raw.columns)}\n"
                         "Edit COLUMN_MAP in config.py to match.")
    df = raw[list(COLUMN_MAP)].rename(columns=COLUMN_MAP).copy()
    start = len(df)

    # names: inconsistent capitalisation / stray whitespace -> one identity key
    df["athlete_key"] = df["athlete"].astype(str).str.lower().str.split().str.join(" ")
    df["athlete"] = df["athlete_key"].str.title()
    df["country"] = df["country"].astype(str).str.strip().str.upper()
    df["event"] = df["event"].astype(str).str.strip()
    df["year"] = pd.to_numeric(df["year"], errors="coerce")
    df["rank"] = pd.to_numeric(df["rank"], errors="coerce")
    df["stage"] = df["round"].map(normalise_stage)
    df["gender"] = df["gender"].map(normalise_gender)

    df = df.dropna(subset=["athlete_key", "year", "rank", "stage", "gender"])
    df["year"] = df["year"].astype(int)
    df["rank"] = df["rank"].astype(int)
    df = df.drop_duplicates(subset=["athlete_key", "event", "year", "gender", "stage"])
    print(f"Cleaning: {start:,} raw rows -> {len(df):,} usable rows")
    return df


def build_db(df: pd.DataFrame, source: str) -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    country = df.groupby("athlete_key")["country"].agg(lambda s: s.mode().iat[0])
    athletes = df.groupby("athlete_key")["athlete"].first().to_frame().join(country).reset_index()
    athletes.insert(0, "athlete_id", range(1, len(athletes) + 1))

    events = df[["event", "year"]].drop_duplicates().sort_values(["year", "event"]).reset_index(drop=True)
    events.insert(0, "event_id", range(1, len(events) + 1))

    res = (df.merge(athletes[["athlete_id", "athlete_key"]], on="athlete_key")
             .merge(events, on=["event", "year"]))
    res = res[["event_id", "athlete_id", "gender", "stage", "rank"]].rename(columns={"rank": "placing"})

    with sqlite3.connect(DB_PATH) as con:
        con.executescript((SQL_DIR / "schema.sql").read_text())
        athletes[["athlete_id", "athlete", "country"]].rename(columns={"athlete": "name"}) \
            .to_sql("athletes", con, if_exists="append", index=False)
        events.rename(columns={"event": "name"}).to_sql("events", con, if_exists="append", index=False)
        res.to_sql("results", con, if_exists="append", index=False)
        con.execute("INSERT INTO meta VALUES ('source', ?)", (source,))
    print(f"Database built: {len(athletes):,} athletes, {len(events):,} events, {len(res):,} results")


if __name__ == "__main__":
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else RAW_CSV
    if not path.exists():
        raise SystemExit(f"CSV not found: {path}")
    build_db(clean(pd.read_csv(path)), path.name)

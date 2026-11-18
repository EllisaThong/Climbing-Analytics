"""Generate FAKE results in the pipeline's schema so the code can be tested offline.
Never use this output for real findings. Run: python -m src.make_synthetic"""
import numpy as np
import pandas as pd

from config import ROOT

rng = np.random.default_rng(42)
COUNTRIES = ["JPN", "SLO", "USA", "GBR", "AUT", "FRA", "KOR", "GER", "ITA", "SUI", "CAN", "MAS"]
CITIES = ["Meiringen", "Seoul", "Salt Lake City", "Innsbruck", "Prague", "Tokyo"]
STAGES = [("Qualification", 60), ("Semi-final", 20), ("Final", 6)]


def main():
    rows = []
    weights = np.linspace(2, 1, len(COUNTRIES))
    for gender in ["men", "women"]:
        skill = rng.normal(0, 1, 90)
        country = rng.choice(COUNTRIES, 90, p=weights / weights.sum())
        for year in range(2014, 2026):
            skill = skill + rng.normal(0, 0.15, 90)          # skill drifts slowly over time
            for city in CITIES:
                field = rng.choice(90, 60, replace=False)
                for stage, size in STAGES:
                    noise = {"Qualification": 1.2, "Semi-final": 0.9, "Final": 0.8}[stage]
                    perf = skill[field] + rng.normal(0, noise, len(field))
                    field = field[np.argsort(-perf)[:size]]
                    for place, idx in enumerate(field, start=1):
                        name = f"Climber {idx:02d} {gender[0].upper()}"
                        if rng.random() < 0.05:                # messy names, to exercise cleaning
                            name = name.upper() if rng.random() < 0.5 else f"  {name.lower()} "
                        rows.append((name, country[idx], f"World Cup {city} {year}", year,
                                     gender, stage, place))
    df = pd.DataFrame(rows, columns=["athlete", "country", "event", "year", "gender", "round", "rank"])
    path = ROOT / "data" / "raw" / "synthetic_results.csv"
    df.to_csv(path, index=False)
    print(f"Wrote {len(df):,} SYNTHETIC rows to {path}")


if __name__ == "__main__":
    main()

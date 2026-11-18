"""Analysis + podium-prediction model.  Run: python -m src.analysis

Question: does semi-final performance (plus prior form) predict who reaches the podium,
and does a model beat the obvious baseline "podium = best 3 semi-final placings"?"""
import json
import re
import sqlite3

import numpy as np
import pandas as pd
import plotly.express as px
from scipy.stats import spearmanr
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from config import DB_PATH, OUT_DIR, SQL_DIR

FEATURES = ["semi_rank", "qual_rank", "prior_n", "prior_final_rate", "prior_podium_rate"]


def run_query(name: str, con=None) -> pd.DataFrame:
    """Run a named query from sql/queries.sql."""
    text = (SQL_DIR / "queries.sql").read_text()
    parts = re.split(r"^-- name:\s*(\w+)\s*$", text, flags=re.M)
    queries = dict(zip(parts[1::2], parts[2::2]))
    own = con is None
    con = con or sqlite3.connect(DB_PATH)
    try:
        return pd.read_sql_query(queries[name], con)
    finally:
        if own:
            con.close()


def get_source() -> str:
    with sqlite3.connect(DB_PATH) as con:
        return pd.read_sql_query("SELECT value FROM meta WHERE key='source'", con)["value"].iat[0]


def rank_correlations(wide: pd.DataFrame) -> dict:
    """Spearman correlation between an earlier-stage placing and final placing."""
    out = {}
    for col in ["qual_rank", "semi_rank"]:
        d = wide.dropna(subset=[col, "final_rank"])
        if len(d) > 2:
            rho, _ = spearmanr(d[col], d["final_rank"])
            out[col] = {"spearman": round(float(rho), 3), "n": int(len(d))}
    return out


def add_prior_form(wide: pd.DataFrame) -> pd.DataFrame:
    """Career history strictly BEFORE the current year (no leakage from the same season)."""
    agg = (wide.groupby(["athlete_id", "year"])
               .agg(n=("event_id", "count"),
                    finals=("final_rank", lambda s: int(s.notna().sum())),
                    podiums=("final_rank", lambda s: int((s <= 3).sum())))
               .reset_index().sort_values(["athlete_id", "year"]))
    for c in ["n", "finals", "podiums"]:
        agg[f"prior_{c}"] = agg.groupby("athlete_id")[c].cumsum() - agg[c]
    agg["prior_final_rate"] = np.where(agg["prior_n"] > 0, agg["prior_finals"] / agg["prior_n"].replace(0, np.nan), np.nan)
    agg["prior_podium_rate"] = np.where(agg["prior_n"] > 0, agg["prior_podiums"] / agg["prior_n"].replace(0, np.nan), np.nan)
    keep = ["athlete_id", "year", "prior_n", "prior_final_rate", "prior_podium_rate"]
    return wide.merge(agg[keep], on=["athlete_id", "year"], how="left")


def build_model_frame(wide: pd.DataFrame) -> pd.DataFrame:
    df = add_prior_form(wide)
    df = df[df["semi_rank"].notna()].copy()                 # everyone who competed in the semi-final
    df["podium"] = (df["final_rank"] <= 3).astype(int)      # NaN (not in final) -> 0
    return df


def top3_hit_rate(d: pd.DataFrame, score_col: str, ascending: bool) -> float:
    """Average share of the true podium captured by the 3 best-scored athletes per event."""
    hits = []
    for _, g in d.groupby(["event_id", "gender"]):
        pred = g.sort_values(score_col, ascending=ascending).head(3)
        hits.append(pred["podium"].sum() / 3)
    return float(np.mean(hits))


def evaluate(df: pd.DataFrame) -> dict:
    years = sorted(df["year"].unique())
    if len(years) < 4:
        raise SystemExit("Need at least 4 distinct years of data for a time-based train/test split.")
    cut = years[-2]                                          # test = the last two seasons
    train, test = df[df["year"] < cut], df[df["year"] >= cut].copy()

    model = make_pipeline(SimpleImputer(strategy="median", keep_empty_features=True),
                          StandardScaler(),
                          LogisticRegression(max_iter=1000, class_weight="balanced"))
    model.fit(train[FEATURES], train["podium"])
    test["p_model"] = model.predict_proba(test[FEATURES])[:, 1]
    test["p_baseline"] = -test["semi_rank"]                  # better semi placing = higher score

    return {
        "train_years": f"{years[0]}-{cut - 1}", "test_years": f"{cut}-{years[-1]}",
        "n_train": int(len(train)), "n_test": int(len(test)),
        "auc_model": round(float(roc_auc_score(test["podium"], test["p_model"])), 3),
        "auc_baseline": round(float(roc_auc_score(test["podium"], test["p_baseline"])), 3),
        "top3_hit_model": round(top3_hit_rate(test.assign(s=test["p_model"]), "s", False), 3),
        "top3_hit_baseline": round(top3_hit_rate(test.assign(s=test["p_baseline"]), "s", False), 3),
        "coefficients": {f: round(float(c), 3) for f, c in
                         zip(FEATURES, model[-1].coef_[0])},
    }


def make_figures(wide: pd.DataFrame, metrics: dict) -> None:
    fig_dir = OUT_DIR / "figures"
    fig_dir.mkdir(parents=True, exist_ok=True)

    fin = run_query("finalists_by_country")
    top = fin.groupby("country")["finalists"].sum().nlargest(10).index
    px.bar(fin[fin["country"].isin(top)], x="year", y="finalists", color="country",
           title="Finalists per year - top 10 countries").write_html(fig_dir / "finalists_by_country.html")

    d = wide.dropna(subset=["semi_rank", "final_rank"])
    px.density_heatmap(d, x="semi_rank", y="final_rank", nbinsx=20, nbinsy=6,
                       title="Semi-final placing vs final placing").write_html(fig_dir / "semi_vs_final.html")

    comp = pd.DataFrame({"method": ["Model", "Baseline (best 3 in semis)"],
                         "podium capture rate": [metrics["top3_hit_model"], metrics["top3_hit_baseline"]]})
    px.bar(comp, x="method", y="podium capture rate",
           title="Share of true podium found in predicted top 3").write_html(fig_dir / "model_vs_baseline.html")


def main():
    source = get_source()
    if "synthetic" in source.lower():
        print("\n*** WARNING: database was built from SYNTHETIC data. These numbers are NOT real findings. ***\n")
    wide = run_query("rounds_wide")
    metrics = {"source": source,
               "rank_correlations": rank_correlations(wide),
               **evaluate(build_model_frame(wide))}
    OUT_DIR.mkdir(exist_ok=True)
    (OUT_DIR / "metrics.json").write_text(json.dumps(metrics, indent=2))
    make_figures(wide, metrics)
    print(json.dumps(metrics, indent=2))


if __name__ == "__main__":
    main()

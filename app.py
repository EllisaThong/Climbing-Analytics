"""Interactive dashboard.  Run: streamlit run app.py"""
import json
import sqlite3

import pandas as pd
import plotly.express as px
import streamlit as st

from config import DB_PATH, OUT_DIR
from src.analysis import get_source, rank_correlations, run_query

st.set_page_config(page_title="Climbing Performance Analytics", layout="wide")
st.title("Climbing Performance Analytics")

if not DB_PATH.exists():
    st.error("Database not found. Run `python -m src.load_clean` first.")
    st.stop()


@st.cache_data
def load():
    return run_query("rounds_wide"), run_query("finalists_by_country"), run_query("career_summary"), get_source()


wide, finalists, careers, source = load()
if "synthetic" in source.lower():
    st.warning("Showing SYNTHETIC demo data - not real competition results.")
st.caption(f"Data source: {source}")

genders = st.sidebar.multiselect("Gender", ["men", "women"], default=["men", "women"])
y_min, y_max = int(wide["year"].min()), int(wide["year"].max())
years = st.sidebar.slider("Years", y_min, y_max, (y_min, y_max)) if y_min < y_max else (y_min, y_max)

w = wide[wide["gender"].isin(genders) & wide["year"].between(*years)]
f = finalists[finalists["gender"].isin(genders) & finalists["year"].between(*years)]

c1, c2, c3 = st.columns(3)
c1.metric("Events", w["event_id"].nunique())
c2.metric("Athletes", w["athlete_id"].nunique())
c3.metric("Countries", w["country"].nunique())

tab1, tab2, tab3, tab4 = st.tabs(["Countries", "Qualification vs final", "Athletes", "Model"])

with tab1:
    top = f.groupby("country")["finalists"].sum().nlargest(10).index
    st.plotly_chart(px.bar(f[f["country"].isin(top)], x="year", y="finalists", color="country",
                           title="Finalists per year - top 10 countries"), width="stretch")

with tab2:
    d = w.dropna(subset=["semi_rank", "final_rank"])
    st.plotly_chart(px.density_heatmap(d, x="semi_rank", y="final_rank", nbinsx=20, nbinsy=6,
                                       title="Semi-final placing vs final placing"), width="stretch")
    st.write(rank_correlations(w))

with tab3:
    name = st.selectbox("Athlete", sorted(w["athlete"].unique()))
    st.dataframe(w[w["athlete"] == name].sort_values("year")[
        ["year", "event", "qual_rank", "semi_rank", "final_rank"]], width="stretch")
    st.subheader("Career leaderboard")
    st.dataframe(careers.head(20), width="stretch")

with tab4:
    path = OUT_DIR / "metrics.json"
    if path.exists():
        m = json.loads(path.read_text())
        a, b = st.columns(2)
        a.metric("Podium capture - model", m["top3_hit_model"])
        b.metric("Podium capture - baseline", m["top3_hit_baseline"])
        st.json(m)
    else:
        st.info("Run `python -m src.analysis` to generate model results.")

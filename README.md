# Climbing Performance Analytics

End-to-end analytics project on IFSC World Cup climbing results.

**Question:** Does semi-final performance, combined with an athlete's prior form, predict
who reaches the podium - and does a simple model beat the obvious baseline
("the best three semi-finalists take the podium")?

## Pipeline
| Step | Tool | File |
|------|------|------|
| Collect / load raw results | Python (pandas) | `src/load_clean.py` |
| Clean + normalise into a relational DB | Python + SQL (SQLite) | `sql/schema.sql` |
| Analytical queries | SQL (joins, conditional aggregation) | `sql/queries.sql` |
| Statistics + model | scipy, scikit-learn (time-based train/test split) | `src/analysis.py` |
| Dashboard | Streamlit + Plotly | `app.py` |

## Quick start
```bash
pip install -r requirements.txt
python -m src.load_clean data/raw/results.csv    # real data (see below)
python -m src.analysis
streamlit run app.py
```

## Using real data
1. Download an IFSC results dataset, e.g. the Kaggle set
   `brkurzawa/ifsc-sport-climbing-competition-results`, into `data/raw/results.csv`.
2. Open the CSV and check its column names. Edit the **left side** of `COLUMN_MAP` in `config.py`
   so each one maps to: athlete, country, event, year, gender, round, rank.
3. The loader needs one row per athlete per round (qualification / semi-final / final). If the
   dataset only gives one overall rank per event, you'll need to adapt `load_clean.py`.
4. Restrict to one discipline (e.g. bouldering) if the file mixes disciplines.

## Demo mode
`python -m src.make_synthetic` creates FAKE data so the code can be tested offline.
The dashboard and `metrics.json` label themselves as synthetic when it's used.
Delete the demo outputs before publishing real results.

## Method notes
- Names are normalised (case, whitespace) so one athlete = one identity.
- "Prior form" only uses seasons **before** the current one, to avoid leakage.
- Train on earlier seasons, test on the last two (never a random split).
- Always compare to the baseline; report the model's gain over it, not accuracy alone.

## Findings
*(Write this after running on real data: 3-5 bullets with actual numbers, plus screenshots
of the dashboard. This section is what recruiters read.)*

## Limitations
Results with weather disruptions or missing rounds are incomplete; ties and withdrawals are
not modelled; prior form is simple career rates, not a full rating system (Elo is a natural extension).

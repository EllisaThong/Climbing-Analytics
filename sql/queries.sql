-- Analysis queries. Each block starts with "-- name: <id>" and is loaded by src/analysis.py

-- name: rounds_wide
-- One row per athlete per event: placing in each stage side by side.
SELECT r.event_id, e.year, e.name AS event, r.gender,
       r.athlete_id, a.name AS athlete, a.country,
       MAX(CASE WHEN r.stage = 'qualification' THEN r.placing END) AS qual_rank,
       MAX(CASE WHEN r.stage = 'semi-final'    THEN r.placing END) AS semi_rank,
       MAX(CASE WHEN r.stage = 'final'         THEN r.placing END) AS final_rank
FROM results r
JOIN events   e ON e.event_id   = r.event_id
JOIN athletes a ON a.athlete_id = r.athlete_id
GROUP BY r.event_id, r.gender, r.athlete_id;

-- name: finalists_by_country
-- How many finalists each country put through, per year and gender.
SELECT a.country, e.year, r.gender, COUNT(*) AS finalists
FROM results r
JOIN athletes a ON a.athlete_id = r.athlete_id
JOIN events   e ON e.event_id   = r.event_id
WHERE r.stage = 'final'
GROUP BY a.country, e.year, r.gender
ORDER BY e.year, finalists DESC;

-- name: career_summary
-- Career totals per athlete: events entered, finals, podiums, best finish.
SELECT a.name AS athlete, a.country,
       COUNT(DISTINCT r.event_id || r.gender)                       AS events_entered,
       SUM(CASE WHEN r.stage = 'final' THEN 1 ELSE 0 END)           AS finals,
       SUM(CASE WHEN r.stage = 'final' AND r.placing <= 3 THEN 1 ELSE 0 END) AS podiums,
       MIN(CASE WHEN r.stage = 'final' THEN r.placing END)          AS best_final
FROM results r
JOIN athletes a ON a.athlete_id = r.athlete_id
GROUP BY a.athlete_id
ORDER BY podiums DESC, finals DESC;

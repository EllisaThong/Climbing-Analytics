DROP TABLE IF EXISTS results;
DROP TABLE IF EXISTS events;
DROP TABLE IF EXISTS athletes;
DROP TABLE IF EXISTS meta;

CREATE TABLE meta (
    key   TEXT PRIMARY KEY,
    value TEXT
);

CREATE TABLE athletes (
    athlete_id INTEGER PRIMARY KEY,
    name       TEXT NOT NULL,
    country    TEXT
);

CREATE TABLE events (
    event_id INTEGER PRIMARY KEY,
    name     TEXT NOT NULL,
    year     INTEGER NOT NULL
);

CREATE TABLE results (
    result_id  INTEGER PRIMARY KEY AUTOINCREMENT,
    event_id   INTEGER NOT NULL REFERENCES events(event_id),
    athlete_id INTEGER NOT NULL REFERENCES athletes(athlete_id),
    gender     TEXT NOT NULL CHECK (gender IN ('men', 'women')),
    stage      TEXT NOT NULL CHECK (stage IN ('qualification', 'semi-final', 'final')),
    placing    INTEGER NOT NULL,
    UNIQUE (event_id, athlete_id, gender, stage)
);

CREATE INDEX idx_results_athlete ON results(athlete_id);
CREATE INDEX idx_results_event   ON results(event_id, gender, stage);

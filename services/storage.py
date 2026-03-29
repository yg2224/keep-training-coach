import sqlite3
from pathlib import Path


SCHEMA = """
CREATE TABLE IF NOT EXISTS activities (
    run_id TEXT PRIMARY KEY,
    name TEXT,
    type TEXT,
    subtype TEXT,
    distance REAL,
    moving_time TEXT,
    elapsed_time TEXT,
    start_date TEXT,
    start_date_local TEXT,
    average_heartrate REAL,
    average_speed REAL,
    elevation_gain REAL,
    summary_polyline TEXT
);

CREATE TABLE IF NOT EXISTS training_plans (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at TEXT NOT NULL,
    plan_type TEXT NOT NULL,
    goal_race_distance REAL,
    goal_race_date TEXT,
    goal_notes TEXT,
    provider TEXT,
    model TEXT,
    input_summary_json TEXT NOT NULL,
    plan_markdown TEXT NOT NULL,
    plan_json TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS plan_workouts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    plan_id INTEGER NOT NULL,
    plan_date TEXT NOT NULL,
    title TEXT NOT NULL,
    workout_type TEXT NOT NULL,
    target_distance_km REAL,
    target_duration_min REAL,
    target_pace TEXT,
    notes TEXT,
    status TEXT NOT NULL DEFAULT 'planned',
    FOREIGN KEY(plan_id) REFERENCES training_plans(id)
);

CREATE TABLE IF NOT EXISTS daily_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    log_date TEXT NOT NULL,
    plan_workout_id INTEGER,
    completed TEXT NOT NULL,
    actual_distance_km REAL,
    actual_duration_min REAL,
    actual_pace TEXT,
    average_heartrate REAL,
    fatigue_score INTEGER,
    mood_score INTEGER,
    notes TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY(plan_workout_id) REFERENCES plan_workouts(id)
);
"""


def get_connection(db_path):
    db_path = Path(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(db_path):
    conn = get_connection(db_path)
    try:
        conn.executescript(SCHEMA)
        conn.commit()
    finally:
        conn.close()


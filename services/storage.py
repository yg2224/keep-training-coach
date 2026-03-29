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
    summary_polyline TEXT,
    location_region_json TEXT
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
    is_active INTEGER NOT NULL DEFAULT 0,
    source_model_key TEXT,
    replaced_plan_id INTEGER,
    input_summary_json TEXT NOT NULL,
    plan_markdown TEXT NOT NULL,
    plan_json TEXT NOT NULL,
    FOREIGN KEY(replaced_plan_id) REFERENCES training_plans(id)
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
    is_replaced INTEGER NOT NULL DEFAULT 0,
    replaced_at TEXT,
    replaced_by_plan_id INTEGER,
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

CREATE TABLE IF NOT EXISTS plan_jobs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_type TEXT NOT NULL,
    status TEXT NOT NULL,
    language TEXT NOT NULL,
    result_plan_id INTEGER,
    error_message TEXT,
    created_at TEXT NOT NULL,
    started_at TEXT,
    finished_at TEXT,
    FOREIGN KEY(result_plan_id) REFERENCES training_plans(id)
);
"""


def ensure_column(conn, table_name, column_name, column_sql):
    columns = {
        row["name"] for row in conn.execute(f"PRAGMA table_info({table_name})").fetchall()
    }
    if column_name not in columns:
        conn.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_sql}")


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
        ensure_column(conn, "activities", "location_region_json", "location_region_json TEXT")
        ensure_column(conn, "training_plans", "is_active", "is_active INTEGER NOT NULL DEFAULT 0")
        ensure_column(conn, "training_plans", "source_model_key", "source_model_key TEXT")
        ensure_column(conn, "training_plans", "replaced_plan_id", "replaced_plan_id INTEGER")
        ensure_column(conn, "plan_workouts", "is_replaced", "is_replaced INTEGER NOT NULL DEFAULT 0")
        ensure_column(conn, "plan_workouts", "replaced_at", "replaced_at TEXT")
        ensure_column(conn, "plan_workouts", "replaced_by_plan_id", "replaced_by_plan_id INTEGER")
        ensure_column(conn, "plan_jobs", "result_plan_id", "result_plan_id INTEGER")
        ensure_column(conn, "plan_jobs", "error_message", "error_message TEXT")
        ensure_column(conn, "plan_jobs", "started_at", "started_at TEXT")
        ensure_column(conn, "plan_jobs", "finished_at", "finished_at TEXT")
        conn.commit()
    finally:
        conn.close()

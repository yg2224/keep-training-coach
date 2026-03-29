import tempfile
import unittest
from pathlib import Path

from services.logs import save_daily_log
from services.storage import get_connection, init_db


class LogTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "app.db"
        init_db(self.db_path)

        conn = get_connection(self.db_path)
        try:
            conn.execute(
                """
                INSERT INTO training_plans (
                    created_at,
                    plan_type,
                    goal_race_distance,
                    goal_race_date,
                    goal_notes,
                    provider,
                    model,
                    input_summary_json,
                    plan_markdown,
                    plan_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "2026-03-29 13:00:00",
                    "rolling_week",
                    None,
                    None,
                    "goal",
                    "provider",
                    "model",
                    "{}",
                    "# Plan",
                    "{}",
                ),
            )
            plan_id = conn.execute("SELECT id FROM training_plans").fetchone()["id"]
            conn.execute(
                """
                INSERT INTO plan_workouts (
                    plan_id,
                    plan_date,
                    title,
                    workout_type,
                    target_distance_km,
                    target_duration_min,
                    target_pace,
                    notes,
                    status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    plan_id,
                    "2026-04-01",
                    "Easy Run",
                    "easy",
                    8,
                    45,
                    "5:30-5:50 /km",
                    "Keep it easy",
                    "planned",
                ),
            )
            conn.commit()
            self.workout_id = conn.execute("SELECT id FROM plan_workouts").fetchone()["id"]
        finally:
            conn.close()

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_save_daily_log_updates_workout_status(self):
        conn = get_connection(self.db_path)
        try:
            log_id = save_daily_log(
                conn,
                {
                    "log_date": "2026-04-01",
                    "plan_workout_id": self.workout_id,
                    "completed": "done",
                    "actual_distance_km": 8.2,
                    "actual_duration_min": 46,
                    "actual_pace": "5:36 /km",
                    "average_heartrate": 151,
                    "fatigue_score": 4,
                    "mood_score": 4,
                    "notes": "Felt smooth",
                },
            )
            workout = conn.execute(
                "SELECT status FROM plan_workouts WHERE id = ?",
                (self.workout_id,),
            ).fetchone()
            log_row = conn.execute(
                "SELECT completed, actual_distance_km FROM daily_logs WHERE id = ?",
                (log_id,),
            ).fetchone()
        finally:
            conn.close()

        self.assertEqual(workout["status"], "done")
        self.assertEqual(log_row["completed"], "done")
        self.assertAlmostEqual(log_row["actual_distance_km"], 8.2)


if __name__ == "__main__":
    unittest.main()

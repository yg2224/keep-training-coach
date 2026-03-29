import json
import tempfile
import unittest
from pathlib import Path

from services.planner import parse_plan_json, save_training_plan
from services.storage import get_connection, init_db


class PlannerTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "app.db"
        init_db(self.db_path)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_parse_plan_json_creates_daily_workouts(self):
        workouts = parse_plan_json(
            7,
            {
                "summary": "Build back consistency",
                "weeks": [
                    {
                        "label": "Week 1",
                        "days": [
                            {
                                "date": "2026-04-01",
                                "title": "Easy Run",
                                "workout_type": "easy",
                                "target_distance_km": 8,
                                "target_duration_min": 45,
                                "target_pace": "5:30-5:50 /km",
                                "notes": "Keep it easy",
                            }
                        ],
                    }
                ],
            },
        )

        self.assertEqual(len(workouts), 1)
        self.assertEqual(workouts[0]["plan_id"], 7)
        self.assertEqual(workouts[0]["plan_date"], "2026-04-01")
        self.assertEqual(workouts[0]["status"], "planned")

    def test_save_training_plan_persists_workouts(self):
        conn = get_connection(self.db_path)
        try:
            plan_id = save_training_plan(
                conn,
                {
                    "created_at": "2026-03-29 13:00:00",
                    "plan_type": "rolling_week",
                    "goal_race_distance": None,
                    "goal_race_date": None,
                    "goal_notes": "Recover and rebuild",
                    "provider": "custom-openai",
                    "model": "gpt-4.1-mini",
                    "input_summary_json": json.dumps({"recent_runs": 10}),
                    "plan_markdown": "# Week Plan",
                    "plan_json": {
                        "summary": "Week summary",
                        "weeks": [
                            {
                                "label": "Week 1",
                                "days": [
                                    {
                                        "date": "2026-04-01",
                                        "title": "Easy Run",
                                        "workout_type": "easy",
                                        "target_distance_km": 8,
                                        "target_duration_min": 45,
                                        "target_pace": "5:30-5:50 /km",
                                        "notes": "Keep it easy",
                                    }
                                ],
                            }
                        ],
                    },
                },
            )

            workout = conn.execute(
                "SELECT plan_id, title, status FROM plan_workouts WHERE plan_id = ?",
                (plan_id,),
            ).fetchone()
        finally:
            conn.close()

        self.assertIsNotNone(workout)
        self.assertEqual(workout["plan_id"], plan_id)
        self.assertEqual(workout["title"], "Easy Run")
        self.assertEqual(workout["status"], "planned")


if __name__ == "__main__":
    unittest.main()

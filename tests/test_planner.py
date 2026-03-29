import json
import tempfile
import unittest
from pathlib import Path

from services.planner import (
    get_active_plan,
    parse_plan_json,
    regenerate_plan,
    save_training_plan,
)
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
                    "source_model_key": "custom-openai",
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
            active_plan = get_active_plan(conn)
        finally:
            conn.close()

        self.assertIsNotNone(workout)
        self.assertEqual(workout["plan_id"], plan_id)
        self.assertEqual(workout["title"], "Easy Run")
        self.assertEqual(workout["status"], "planned")
        self.assertEqual(active_plan["id"], plan_id)
        self.assertEqual(active_plan["source_model_key"], "custom-openai")

    def test_save_training_plan_marks_only_latest_plan_active(self):
        conn = get_connection(self.db_path)
        try:
            first_plan_id = save_training_plan(
                conn,
                {
                    "created_at": "2026-03-29 13:00:00",
                    "plan_type": "rolling_week",
                    "goal_race_distance": None,
                    "goal_race_date": None,
                    "goal_notes": "Base week",
                    "provider": "provider-a",
                    "model": "model-a",
                    "source_model_key": "model-a",
                    "input_summary_json": "{}",
                    "plan_markdown": "# Plan A",
                    "plan_json": {"summary": "A", "weeks": []},
                },
            )
            second_plan_id = save_training_plan(
                conn,
                {
                    "created_at": "2026-03-30 13:00:00",
                    "plan_type": "rolling_week",
                    "goal_race_distance": None,
                    "goal_race_date": None,
                    "goal_notes": "New week",
                    "provider": "provider-b",
                    "model": "model-b",
                    "source_model_key": "model-b",
                    "input_summary_json": "{}",
                    "plan_markdown": "# Plan B",
                    "plan_json": {"summary": "B", "weeks": []},
                },
            )
            plans = conn.execute(
                "SELECT id, is_active FROM training_plans ORDER BY id ASC"
            ).fetchall()
        finally:
            conn.close()

        self.assertEqual(first_plan_id + 1, second_plan_id)
        self.assertEqual([row["is_active"] for row in plans], [0, 1])

    def test_regenerate_future_incomplete_workouts_only_replaces_pending_future(self):
        conn = get_connection(self.db_path)
        try:
            original_plan_id = save_training_plan(
                conn,
                {
                    "created_at": "2026-03-29 13:00:00",
                    "plan_type": "rolling_week",
                    "goal_race_distance": None,
                    "goal_race_date": None,
                    "goal_notes": "Original",
                    "provider": "provider-a",
                    "model": "model-a",
                    "source_model_key": "model-a",
                    "input_summary_json": "{}",
                    "plan_markdown": "# Original",
                    "plan_json": {
                        "summary": "Week summary",
                        "weeks": [
                            {
                                "label": "Week 1",
                                "days": [
                                    {
                                        "date": "2026-04-01",
                                        "title": "Completed Run",
                                        "workout_type": "easy",
                                        "target_distance_km": 8,
                                        "target_duration_min": 45,
                                        "target_pace": "5:30-5:50 /km",
                                        "notes": "done",
                                    },
                                    {
                                        "date": "2026-04-03",
                                        "title": "Future Run",
                                        "workout_type": "tempo",
                                        "target_distance_km": 10,
                                        "target_duration_min": 50,
                                        "target_pace": "5:00 /km",
                                        "notes": "pending",
                                    },
                                ],
                            }
                        ],
                    },
                },
            )
            conn.execute(
                "UPDATE plan_workouts SET status = 'done' WHERE plan_id = ? AND plan_date = ?",
                (original_plan_id, "2026-04-01"),
            )
            conn.commit()

            def fake_generator(db_conn, config, plan_request, model_config, active_plan):
                return {
                    "created_at": "2026-04-02 08:00:00",
                    "plan_type": plan_request["plan_type"],
                    "goal_race_distance": None,
                    "goal_race_date": None,
                    "goal_notes": "Regenerated",
                    "provider": model_config["provider_name"],
                    "model": model_config["model"],
                    "source_model_key": model_config["key"],
                    "input_summary_json": "{}",
                    "plan_markdown": "# New Plan",
                    "plan_json": {
                        "summary": "Week summary",
                        "weeks": [
                            {
                                "label": "Week 1",
                                "days": [
                                    {
                                        "date": "2026-04-03",
                                        "title": "New Future Run",
                                        "workout_type": "easy",
                                        "target_distance_km": 6,
                                        "target_duration_min": 35,
                                        "target_pace": "5:40 /km",
                                        "notes": "new",
                                    }
                                ],
                            }
                        ],
                    },
                }

            new_plan_id = regenerate_plan(
                conn,
                {
                    "models": [
                        {
                            "key": "model-b",
                            "label": "Model B",
                            "provider_name": "provider-b",
                            "base_url": "https://example.com/v1",
                            "api_key": "test-key",
                            "model": "model-b",
                        }
                    ]
                },
                "model-b",
                {"plan_type": "rolling_week", "goal_notes": "refresh"},
                fake_generator,
                today="2026-04-02",
            )
            rows = conn.execute(
                """
                SELECT plan_id, plan_date, title, status, is_replaced, replaced_by_plan_id
                FROM plan_workouts
                ORDER BY id ASC
                """
            ).fetchall()
            active_plan = get_active_plan(conn)
        finally:
            conn.close()

        self.assertNotEqual(original_plan_id, new_plan_id)
        self.assertEqual(active_plan["id"], new_plan_id)
        self.assertEqual(rows[0]["is_replaced"], 0)
        self.assertEqual(rows[1]["is_replaced"], 1)
        self.assertEqual(rows[1]["replaced_by_plan_id"], new_plan_id)
        self.assertEqual(rows[2]["plan_id"], new_plan_id)
        self.assertEqual(rows[2]["title"], "New Future Run")


if __name__ == "__main__":
    unittest.main()

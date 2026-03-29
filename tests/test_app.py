import tempfile
import unittest
from pathlib import Path

from app import create_app
from services.storage import get_connection


class AppTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.base_path = Path(self.temp_dir.name)
        self.sync_calls = []
        self.plan_calls = []

        def fake_sync(db_path, phone_number, password, sync_types=None):
            self.sync_calls.append(
                {
                    "db_path": db_path,
                    "phone_number": phone_number,
                    "password": password,
                    "sync_types": sync_types,
                }
            )
            conn = get_connection(db_path)
            try:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO activities (
                        run_id,
                        name,
                        type,
                        subtype,
                        distance,
                        moving_time,
                        elapsed_time,
                        start_date,
                        start_date_local,
                        average_heartrate,
                        average_speed,
                        elevation_gain,
                        summary_polyline
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        "run-1",
                        "Injected Run",
                        "Run",
                        "Run",
                        5000,
                        "00:25:00",
                        "00:26:00",
                        "2026-03-01 07:00:00",
                        "2026-03-01 07:00:00",
                        150,
                        3.33,
                        30,
                        "",
                    ),
                )
                conn.commit()
            finally:
                conn.close()
            return {"synced": 1, "errors": []}

        def fake_plan_generator(conn, config, plan_request):
            self.plan_calls.append(
                {
                    "config": config,
                    "plan_request": plan_request,
                }
            )
            return {
                "created_at": "2026-03-29 13:00:00",
                "plan_type": plan_request["plan_type"],
                "goal_race_distance": plan_request.get("goal_race_distance"),
                "goal_race_date": plan_request.get("goal_race_date"),
                "goal_notes": plan_request.get("goal_notes"),
                "provider": config["ai"]["provider_name"],
                "model": config["ai"]["model"],
                "input_summary_json": "{\"recent_runs\": 1}",
                "plan_markdown": "# Test Plan",
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
            }

        self.app = create_app(
            {
                "TESTING": True,
                "DATABASE": str(self.base_path / "app.db"),
                "CONFIG_PATH": str(self.base_path / "config.json"),
                "KEEP_SYNC_HANDLER": fake_sync,
                "PLAN_GENERATOR": fake_plan_generator,
            }
        )
        self.client = self.app.test_client()

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_home_page_renders(self):
        response = self.client.get("/")

        self.assertEqual(response.status_code, 200)
        self.assertIn("Keep Training Coach", response.get_data(as_text=True))

    def test_analysis_page_renders(self):
        response = self.client.get("/analysis")

        self.assertEqual(response.status_code, 200)
        self.assertIn("Run Analysis", response.get_data(as_text=True))

    def test_plans_page_renders(self):
        response = self.client.get("/plans")

        self.assertEqual(response.status_code, 200)
        self.assertIn("Training Plans", response.get_data(as_text=True))

    def test_today_page_renders(self):
        response = self.client.get("/today")

        self.assertEqual(response.status_code, 200)
        self.assertIn("Daily Log", response.get_data(as_text=True))

    def test_settings_page_renders(self):
        response = self.client.get("/settings")

        self.assertEqual(response.status_code, 200)
        self.assertIn("Settings", response.get_data(as_text=True))

    def test_post_settings_persists_config(self):
        response = self.client.post(
            "/settings",
            data={
                "phone_number": "13800138000",
                "password": "secret",
                "provider_name": "custom-openai",
                "base_url": "https://example.com/v1",
                "api_key": "test-key",
                "model": "gpt-4.1-mini",
            },
            follow_redirects=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue((self.base_path / "config.json").exists())
        self.assertIn("Settings", response.get_data(as_text=True))

    def test_post_sync_uses_saved_keep_credentials(self):
        self.client.post(
            "/settings",
            data={
                "phone_number": "13800138000",
                "password": "secret",
                "provider_name": "custom-openai",
                "base_url": "https://example.com/v1",
                "api_key": "test-key",
                "model": "gpt-4.1-mini",
            },
        )

        response = self.client.post("/sync", data={}, follow_redirects=True)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(self.sync_calls), 1)
        self.assertEqual(self.sync_calls[0]["phone_number"], "13800138000")
        self.assertIn("Injected Run", response.get_data(as_text=True))

    def test_post_generate_plan_stores_plan_and_workout(self):
        self.client.post(
            "/settings",
            data={
                "phone_number": "13800138000",
                "password": "secret",
                "provider_name": "custom-openai",
                "base_url": "https://example.com/v1",
                "api_key": "test-key",
                "model": "gpt-4.1-mini",
            },
        )

        response = self.client.post(
            "/plans/generate",
            data={
                "plan_type": "rolling_week",
                "goal_race_distance": "",
                "goal_race_date": "",
                "goal_notes": "Recover and rebuild",
            },
            follow_redirects=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(self.plan_calls), 1)
        self.assertIn("Easy Run", response.get_data(as_text=True))
        self.assertIn("Test Plan", response.get_data(as_text=True))

    def test_post_today_saves_log_and_updates_status(self):
        self.client.post(
            "/settings",
            data={
                "phone_number": "13800138000",
                "password": "secret",
                "provider_name": "custom-openai",
                "base_url": "https://example.com/v1",
                "api_key": "test-key",
                "model": "gpt-4.1-mini",
            },
        )
        self.client.post(
            "/plans/generate",
            data={
                "plan_type": "rolling_week",
                "goal_race_distance": "",
                "goal_race_date": "",
                "goal_notes": "Recover and rebuild",
            },
        )

        conn = get_connection(self.base_path / "app.db")
        try:
            workout_id = conn.execute("SELECT id FROM plan_workouts").fetchone()["id"]
        finally:
            conn.close()

        response = self.client.post(
            "/today",
            data={
                "log_date": "2026-04-01",
                "plan_workout_id": workout_id,
                "completed": "done",
                "actual_distance_km": "8.2",
                "actual_duration_min": "46",
                "actual_pace": "5:36 /km",
                "average_heartrate": "151",
                "fatigue_score": "4",
                "mood_score": "4",
                "notes": "Felt smooth",
            },
            follow_redirects=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("done", response.get_data(as_text=True))


if __name__ == "__main__":
    unittest.main()

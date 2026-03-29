import json
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
            selected_model = next(
                item for item in config["models"] if item["key"] == plan_request["model_key"]
            )
            return {
                "created_at": "2026-03-29 13:00:00",
                "plan_type": plan_request["plan_type"],
                "goal_race_distance": plan_request.get("goal_race_distance"),
                "goal_race_date": plan_request.get("goal_race_date"),
                "goal_notes": plan_request.get("goal_notes"),
                "provider": selected_model["provider_name"],
                "model": selected_model["model"],
                "source_model_key": selected_model["key"],
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
                                },
                                {
                                    "date": "2026-04-03",
                                    "title": "Tempo Run",
                                    "workout_type": "tempo",
                                    "target_distance_km": 10,
                                    "target_duration_min": 50,
                                    "target_pace": "5:00 /km",
                                    "notes": "Stay controlled",
                                },
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

    def save_settings(self):
        return self.client.post(
            "/settings",
            data={
                "phone_number": "13800138000",
                "password": "secret",
                "model_key": ["model-a", "model-b"],
                "model_label": ["Model A", "Model B"],
                "model_provider_name": ["custom-openai", "custom-openai"],
                "model_base_url": [
                    "https://example.com/v1",
                    "https://example.com/v1",
                ],
                "model_api_key": ["test-key-a", "test-key-b"],
                "model_name": ["gpt-4.1-mini", "gpt-4o-mini"],
            },
            follow_redirects=True,
        )

    def generate_plan(self):
        return self.client.post(
            "/plans/generate",
            data={
                "model_key": "model-b",
                "plan_type": "rolling_week",
                "goal_race_distance": "",
                "goal_race_date": "",
                "goal_notes": "Recover and rebuild",
            },
            follow_redirects=True,
        )

    def test_home_page_renders_calendar_month(self):
        response = self.client.get("/?month=2026-04")

        self.assertEqual(response.status_code, 200)
        body = response.get_data(as_text=True)
        self.assertIn("calendar-root", body)
        self.assertIn("April 2026", body)

    def test_settings_page_renders(self):
        response = self.client.get("/settings")

        self.assertEqual(response.status_code, 200)
        self.assertIn("Settings", response.get_data(as_text=True))

    def test_analysis_page_renders_chart_containers(self):
        self.save_settings()
        self.generate_plan()
        response = self.client.get("/analysis")
        script_response = self.client.get("/static/app.js")

        self.assertEqual(response.status_code, 200)
        body = response.get_data(as_text=True)
        self.assertIn("monthly-chart", body)
        self.assertIn("weekly-chart", body)
        self.assertIn("analysis-data", body)
        self.assertEqual(script_response.status_code, 200)
        script = script_response.get_data(as_text=True)
        script_response.close()
        self.assertIn("bindAnalysisCharts", script)
        self.assertIn("new Chart(", script)

    def test_post_settings_saves_multiple_models(self):
        response = self.save_settings()

        self.assertEqual(response.status_code, 200)
        saved = json.loads((self.base_path / "config.json").read_text(encoding="utf-8"))
        self.assertEqual(len(saved["models"]), 2)
        self.assertEqual(saved["models"][1]["key"], "model-b")
        self.assertIn("Model A", response.get_data(as_text=True))

    def test_post_sync_uses_saved_keep_credentials(self):
        self.save_settings()

        response = self.client.post("/sync", data={}, follow_redirects=True)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(self.sync_calls), 1)
        self.assertEqual(self.sync_calls[0]["phone_number"], "13800138000")
        self.assertIn("Injected Run", response.get_data(as_text=True))

    def test_post_generate_plan_uses_selected_model_and_sets_active_plan(self):
        self.save_settings()

        response = self.generate_plan()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(self.plan_calls), 1)
        self.assertEqual(self.plan_calls[0]["plan_request"]["model_key"], "model-b")
        self.assertIn("Test Plan", response.get_data(as_text=True))
        self.assertIn("Tempo Run", response.get_data(as_text=True))

    def test_day_detail_endpoint_returns_plan_and_latest_log(self):
        self.save_settings()
        self.generate_plan()
        self.client.post(
            "/api/day-log",
            data={
                "log_date": "2026-04-01",
                "plan_workout_id": "1",
                "completed": "done",
                "actual_distance_km": "8.2",
                "actual_duration_min": "46",
                "actual_pace": "5:36 /km",
                "average_heartrate": "151",
                "fatigue_score": "4",
                "mood_score": "4",
                "notes": "Felt smooth",
            },
        )

        response = self.client.get("/api/day/2026-04-01")

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertEqual(payload["date"], "2026-04-01")
        self.assertEqual(payload["workout"]["title"], "Easy Run")
        self.assertEqual(payload["latest_log"]["completed"], "done")

    def test_post_day_log_updates_status_and_calendar_payload(self):
        self.save_settings()
        self.generate_plan()

        response = self.client.post(
            "/api/day-log",
            data={
                "log_date": "2026-04-01",
                "plan_workout_id": "1",
                "completed": "done",
                "actual_distance_km": "8.2",
                "actual_duration_min": "46",
                "actual_pace": "5:36 /km",
                "average_heartrate": "151",
                "fatigue_score": "4",
                "mood_score": "4",
                "notes": "Felt smooth",
            },
        )

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertEqual(payload["status"], "ok")
        self.assertEqual(payload["day"]["completed"], "done")

    def test_post_regenerate_replaces_future_incomplete_workouts(self):
        self.save_settings()
        self.generate_plan()
        self.client.post(
            "/api/day-log",
            data={
                "log_date": "2026-04-01",
                "plan_workout_id": "1",
                "completed": "done",
                "actual_distance_km": "8.2",
                "actual_duration_min": "46",
                "actual_pace": "5:36 /km",
                "average_heartrate": "151",
                "fatigue_score": "4",
                "mood_score": "4",
                "notes": "Felt smooth",
            },
        )

        response = self.client.post(
            "/plans/regenerate",
            data={
                "model_key": "model-a",
                "plan_type": "rolling_week",
                "goal_notes": "Refresh the rest of the week",
                "today": "2026-04-02",
            },
            follow_redirects=True,
        )

        self.assertEqual(response.status_code, 200)
        conn = get_connection(self.base_path / "app.db")
        try:
            rows = conn.execute(
                """
                SELECT title, is_replaced, replaced_by_plan_id
                FROM plan_workouts
                ORDER BY id ASC
                """
            ).fetchall()
        finally:
            conn.close()

        self.assertEqual(rows[0]["is_replaced"], 0)
        self.assertEqual(rows[1]["is_replaced"], 1)
        self.assertIsNotNone(rows[1]["replaced_by_plan_id"])


if __name__ == "__main__":
    unittest.main()

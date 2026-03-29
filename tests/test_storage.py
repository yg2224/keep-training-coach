import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

from services.config_store import load_config, save_config
from services.storage import get_connection, init_db


class StorageTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.base_path = Path(self.temp_dir.name)
        self.db_path = self.base_path / "app.db"
        self.config_path = self.base_path / "config.json"

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_init_db_creates_expected_tables(self):
        init_db(self.db_path)

        conn = sqlite3.connect(self.db_path)
        try:
            table_names = {
                row[0]
                for row in conn.execute(
                    "SELECT name FROM sqlite_master WHERE type = 'table'"
                ).fetchall()
            }
        finally:
            conn.close()

        self.assertTrue(
            {"activities", "training_plans", "plan_workouts", "daily_logs"}.issubset(
                table_names
            )
        )

    def test_save_and_load_config_round_trip(self):
        payload = {
            "keep": {"phone_number": "13800138000", "password": "secret"},
            "models": [
                {
                    "key": "custom-openai",
                    "label": "Custom OpenAI",
                    "provider_name": "custom-openai",
                    "base_url": "https://example.com/v1",
                    "api_key": "test-key",
                    "model": "gpt-4.1-mini",
                }
            ],
        }

        save_config(self.config_path, payload)
        loaded = load_config(self.config_path)

        self.assertEqual(payload, loaded)

    def test_load_config_migrates_legacy_single_ai_config_to_models(self):
        legacy_payload = {
            "keep": {"phone_number": "13800138000", "password": "secret"},
            "ai": {
                "provider_name": "custom-openai",
                "base_url": "https://example.com/v1",
                "api_key": "test-key",
                "model": "gpt-4.1-mini",
            },
        }
        self.config_path.write_text(
            json.dumps(legacy_payload, ensure_ascii=False),
            encoding="utf-8",
        )

        loaded = load_config(self.config_path)

        self.assertNotIn("ai", loaded)
        self.assertEqual(len(loaded["models"]), 1)
        self.assertEqual(loaded["models"][0]["provider_name"], "custom-openai")
        self.assertEqual(loaded["models"][0]["key"], "custom-openai")

    def test_init_db_adds_calendar_v2_columns(self):
        init_db(self.db_path)

        conn = get_connection(self.db_path)
        try:
            training_plan_columns = {
                row["name"]
                for row in conn.execute("PRAGMA table_info(training_plans)").fetchall()
            }
            workout_columns = {
                row["name"]
                for row in conn.execute("PRAGMA table_info(plan_workouts)").fetchall()
            }
        finally:
            conn.close()

        self.assertTrue(
            {"is_active", "source_model_key", "replaced_plan_id"}.issubset(
                training_plan_columns
            )
        )
        self.assertTrue(
            {"is_replaced", "replaced_at", "replaced_by_plan_id"}.issubset(
                workout_columns
            )
        )


if __name__ == "__main__":
    unittest.main()

import sqlite3
import tempfile
import unittest
from pathlib import Path

from services.config_store import load_config, save_config
from services.storage import init_db


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
            "ai": {
                "provider_name": "custom-openai",
                "base_url": "https://example.com/v1",
                "api_key": "test-key",
                "model": "gpt-4.1-mini",
            },
        }

        save_config(self.config_path, payload)
        loaded = load_config(self.config_path)

        self.assertEqual(payload, loaded)


if __name__ == "__main__":
    unittest.main()

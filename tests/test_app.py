import tempfile
import unittest
from pathlib import Path

from app import create_app


class AppTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.base_path = Path(self.temp_dir.name)
        self.app = create_app(
            {
                "TESTING": True,
                "DATABASE": str(self.base_path / "app.db"),
                "CONFIG_PATH": str(self.base_path / "config.json"),
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


if __name__ == "__main__":
    unittest.main()

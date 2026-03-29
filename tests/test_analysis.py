import unittest

from services.analysis import (
    build_completion_summary,
    build_dashboard_summary,
    build_heatmap_data,
    build_monthly_stats,
    build_prs,
    build_weekly_stats,
)


class AnalysisTests(unittest.TestCase):
    def setUp(self):
        self.runs = [
            {
                "run_id": "run-1",
                "name": "Easy 5K",
                "type": "Run",
                "distance": 5000,
                "moving_time": "00:25:00",
                "elapsed_time": "00:26:00",
                "start_date_local": "2026-03-01 07:00:00",
                "average_heartrate": 150,
                "average_speed": 3.33,
                "elevation_gain": 32,
            },
            {
                "run_id": "run-2",
                "name": "Long Run",
                "type": "Run",
                "distance": 12000,
                "moving_time": "01:06:00",
                "elapsed_time": "01:08:00",
                "start_date_local": "2026-03-15 07:30:00",
                "average_heartrate": 148,
                "average_speed": 3.03,
                "elevation_gain": 80,
            },
            {
                "run_id": "walk-1",
                "name": "Walk",
                "type": "Walk",
                "distance": 3000,
                "moving_time": "00:30:00",
                "elapsed_time": "00:30:00",
                "start_date_local": "2026-03-20 19:00:00",
                "average_heartrate": 110,
                "average_speed": 1.66,
                "elevation_gain": 10,
            },
            {
                "run_id": "run-3",
                "name": "Steady Run",
                "type": "Run",
                "distance": 8000,
                "moving_time": "00:42:00",
                "elapsed_time": "00:43:00",
                "start_date_local": "2026-03-23 07:00:00",
                "average_heartrate": 149,
                "average_speed": 3.17,
                "elevation_gain": 25,
            },
        ]
        self.workouts = [
            {"status": "done"},
            {"status": "done"},
            {"status": "planned"},
            {"status": "skipped"},
        ]

    def test_build_dashboard_summary_for_runs_only(self):
        summary = build_dashboard_summary(self.runs)

        self.assertEqual(summary["total_runs"], 3)
        self.assertAlmostEqual(summary["total_distance_km"], 25.0)
        self.assertEqual(summary["longest_run"]["run_id"], "run-2")
        self.assertEqual(summary["fastest_run"]["run_id"], "run-1")

    def test_build_monthly_stats_aggregates_run_distance_and_count(self):
        stats = build_monthly_stats(self.runs)

        self.assertEqual(len(stats), 1)
        self.assertEqual(stats[0]["month"], "2026-03")
        self.assertEqual(stats[0]["count"], 3)
        self.assertAlmostEqual(stats[0]["distance"], 25.0)

    def test_build_prs_uses_standard_distance_thresholds(self):
        prs = build_prs(self.runs)
        pr_map = {item["label"]: item["run"]["run_id"] if item["run"] else None for item in prs}

        self.assertEqual(pr_map["5 km"], "run-1")
        self.assertEqual(pr_map["10 km"], "run-2")
        self.assertIsNone(pr_map["半马"])

    def test_build_weekly_stats_groups_runs_by_week_start(self):
        stats = build_weekly_stats(self.runs)

        self.assertEqual(len(stats), 3)
        self.assertEqual(stats[0]["week_start"], "2026-02-23")
        self.assertEqual(stats[1]["week_start"], "2026-03-09")
        self.assertEqual(stats[2]["week_start"], "2026-03-23")
        self.assertAlmostEqual(stats[2]["distance"], 8.0)

    def test_build_heatmap_data_returns_date_distance_pairs(self):
        heatmap = build_heatmap_data(self.runs)

        self.assertEqual(len(heatmap), 3)
        self.assertEqual(heatmap[0]["date"], "2026-03-01")
        self.assertAlmostEqual(heatmap[1]["distance"], 12.0)

    def test_build_completion_summary_counts_workout_statuses(self):
        summary = build_completion_summary(self.workouts)

        self.assertEqual(summary["total"], 4)
        self.assertEqual(summary["done"], 2)
        self.assertEqual(summary["completion_rate"], 50.0)


if __name__ == "__main__":
    unittest.main()

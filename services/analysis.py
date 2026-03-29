from collections import Counter, defaultdict
from datetime import datetime, timedelta


DISTANCE_PR_TARGETS = [
    ("5 km", 5000),
    ("10 km", 10000),
    ("Half Marathon", 21097.5),
    ("Marathon", 42195),
]

PACE_BUCKETS = [
    ("< 4:30", 0, 270),
    ("4:30-5:00", 270, 300),
    ("5:00-5:30", 300, 330),
    ("5:30-6:00", 330, 360),
    (">= 6:00", 360, float("inf")),
]

DISTANCE_BUCKETS = [
    ("0-5 km", 0, 5000),
    ("5-10 km", 5000, 10000),
    ("10-15 km", 10000, 15000),
    ("15 km+", 15000, float("inf")),
]

HEATMAP_WEEKDAY_LABELS = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]
HEATMAP_LEVELS = [
    (0, 0),
    (1, 0.01),
    (2, 5.0),
    (3, 10.0),
    (4, 15.0),
]


def parse_duration_to_seconds(value):
    if not value:
        return 0
    parts = str(value).split(":")
    if len(parts) == 3:
        hours, minutes, seconds = parts
        return int(hours) * 3600 + int(minutes) * 60 + int(float(seconds))
    if len(parts) == 2:
        minutes, seconds = parts
        return int(minutes) * 60 + int(float(seconds))
    return int(float(value))


def filter_runs(items):
    runs = []
    for item in items:
        if item.get("type") != "Run":
            continue
        run = dict(item)
        run["moving_seconds"] = parse_duration_to_seconds(run.get("moving_time"))
        run["date"] = datetime.strptime(
            run["start_date_local"],
            "%Y-%m-%d %H:%M:%S",
        )
        distance = float(run.get("distance") or 0)
        moving_seconds = run["moving_seconds"]
        run["pace_seconds"] = (
            moving_seconds / (distance / 1000)
            if distance > 0 and moving_seconds > 0
            else None
        )
        runs.append(run)
    return runs


def load_runs(conn):
    rows = conn.execute(
        """
        SELECT *
        FROM activities
        WHERE type = 'Run'
        ORDER BY start_date_local ASC
        """
    ).fetchall()
    return filter_runs([dict(row) for row in rows])


def build_dashboard_summary(items):
    runs = filter_runs(items)
    total_distance = sum(float(run.get("distance") or 0) for run in runs) / 1000
    total_seconds = sum(run["moving_seconds"] for run in runs)
    total_elevation = sum(float(run.get("elevation_gain") or 0) for run in runs)
    longest_run = max(runs, key=lambda run: float(run.get("distance") or 0), default=None)
    fastest_run = min(
        [run for run in runs if run["pace_seconds"] is not None],
        key=lambda run: run["pace_seconds"],
        default=None,
    )
    return {
        "total_runs": len(runs),
        "total_distance_km": round(total_distance, 2),
        "total_seconds": total_seconds,
        "total_elevation_m": round(total_elevation, 1),
        "longest_run": longest_run,
        "fastest_run": fastest_run,
    }


def build_monthly_stats(items):
    runs = filter_runs(items)
    monthly = defaultdict(lambda: {"count": 0, "distance": 0.0})
    for run in runs:
        month = run["date"].strftime("%Y-%m")
        monthly[month]["count"] += 1
        monthly[month]["distance"] += float(run.get("distance") or 0) / 1000
    return [
        {
            "month": month,
            "count": monthly[month]["count"],
            "distance": round(monthly[month]["distance"], 2),
        }
        for month in sorted(monthly.keys())
    ]


def build_weekly_stats(items):
    runs = filter_runs(items)
    weekly = defaultdict(lambda: {"count": 0, "distance": 0.0})
    for run in runs:
        week_start = (run["date"] - timedelta(days=run["date"].weekday())).date()
        key = week_start.isoformat()
        weekly[key]["count"] += 1
        weekly[key]["distance"] += float(run.get("distance") or 0) / 1000
    return [
        {
            "week_start": key,
            "count": weekly[key]["count"],
            "distance": round(weekly[key]["distance"], 2),
        }
        for key in sorted(weekly.keys())
    ]


def parse_heatmap_today(today):
    if today is None:
        return datetime.now().date()
    if isinstance(today, str):
        return datetime.strptime(today, "%Y-%m-%d").date()
    if isinstance(today, datetime):
        return today.date()
    return today


def get_heatmap_level(distance):
    level = 0
    for candidate, threshold in HEATMAP_LEVELS:
        if distance >= threshold:
            level = candidate
    return level


def build_heatmap_data(items, weeks=26, today=None):
    runs = filter_runs(items)
    distance_by_date = defaultdict(float)
    for run in runs:
        distance_by_date[run["date"].date().isoformat()] += float(run.get("distance") or 0) / 1000

    end_date = parse_heatmap_today(today)
    current_week_start = end_date - timedelta(days=(end_date.weekday() + 1) % 7)
    first_week_start = current_week_start - timedelta(weeks=weeks - 1)

    month_labels = []
    seen_months = set()
    visible_month = first_week_start.strftime("%Y-%m")
    month_labels.append({"label": first_week_start.strftime("%b"), "column": 1})
    seen_months.add(visible_month)

    weeks_data = []
    for week_index in range(weeks):
        week_start = first_week_start + timedelta(weeks=week_index)
        days = []
        for day_offset, weekday_label in enumerate(HEATMAP_WEEKDAY_LABELS):
            cell_date = week_start + timedelta(days=day_offset)
            date_key = cell_date.isoformat()
            distance = round(distance_by_date.get(date_key, 0.0), 2)
            days.append(
                {
                    "date": date_key,
                    "distance": distance,
                    "level": get_heatmap_level(distance),
                    "weekday": weekday_label,
                }
            )
            month_key = cell_date.strftime("%Y-%m")
            if cell_date.day == 1 and month_key not in seen_months:
                month_labels.append(
                    {
                        "label": cell_date.strftime("%b"),
                        "column": week_index + 1,
                    }
                )
                seen_months.add(month_key)
        weeks_data.append(
            {
                "week_start": week_start.isoformat(),
                "days": days,
            }
        )

    return {
        "weeks": weeks_data,
        "weekday_labels": HEATMAP_WEEKDAY_LABELS,
        "month_labels": month_labels,
    }


def build_completion_summary(workouts):
    counts = Counter(item.get("status", "planned") for item in workouts)
    total = len(workouts)
    done = counts.get("done", 0)
    return {
        "total": total,
        "done": done,
        "partial": counts.get("partial", 0),
        "skipped": counts.get("skipped", 0),
        "planned": counts.get("planned", 0),
        "completion_rate": round((done / total) * 100, 1) if total else 0.0,
    }


def build_prs(items):
    runs = filter_runs(items)
    records = []
    for label, target_distance in DISTANCE_PR_TARGETS:
        candidates = [
            run
            for run in runs
            if float(run.get("distance") or 0) >= target_distance
            and run["pace_seconds"] is not None
        ]
        best = min(candidates, key=lambda run: run["pace_seconds"], default=None)
        records.append({"label": label, "target": target_distance, "run": best})
    return records


def bucketize_runs(items, buckets, value_getter):
    counts = Counter({label: 0 for label, _, _ in buckets})
    for run in filter_runs(items):
        value = value_getter(run)
        if value is None:
            continue
        for label, lower, upper in buckets:
            if lower <= value < upper:
                counts[label] += 1
                break
    return [{"label": label, "value": counts[label]} for label, _, _ in buckets]


def build_pace_distribution(items):
    return bucketize_runs(items, PACE_BUCKETS, lambda run: run["pace_seconds"])


def build_distance_distribution(items):
    return bucketize_runs(items, DISTANCE_BUCKETS, lambda run: float(run.get("distance") or 0))

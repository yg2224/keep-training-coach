import json


REQUIRED_DAY_FIELDS = [
    "date",
    "title",
    "workout_type",
    "target_distance_km",
    "target_duration_min",
    "target_pace",
    "notes",
]


def parse_plan_json(plan_id, plan_json):
    if isinstance(plan_json, str):
        plan_json = json.loads(plan_json)

    workouts = []
    for week in plan_json.get("weeks", []):
        for day in week.get("days", []):
            workout = {"plan_id": plan_id, "status": "planned"}
            for field in REQUIRED_DAY_FIELDS:
                if field not in day:
                    raise ValueError(f"Missing required workout field: {field}")
            workout["plan_date"] = day["date"]
            workout["title"] = day["title"]
            workout["workout_type"] = day["workout_type"]
            workout["target_distance_km"] = day["target_distance_km"]
            workout["target_duration_min"] = day["target_duration_min"]
            workout["target_pace"] = day["target_pace"]
            workout["notes"] = day["notes"]
            workouts.append(workout)
    return workouts


def save_training_plan(conn, payload):
    plan_json_value = payload["plan_json"]
    stored_plan_json = (
        plan_json_value
        if isinstance(plan_json_value, str)
        else json.dumps(plan_json_value, ensure_ascii=False)
    )
    cursor = conn.execute(
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
            payload["created_at"],
            payload["plan_type"],
            payload.get("goal_race_distance"),
            payload.get("goal_race_date"),
            payload.get("goal_notes"),
            payload.get("provider"),
            payload.get("model"),
            payload["input_summary_json"],
            payload["plan_markdown"],
            stored_plan_json,
        ),
    )
    plan_id = cursor.lastrowid
    workouts = parse_plan_json(plan_id, plan_json_value)

    for workout in workouts:
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
                workout["plan_id"],
                workout["plan_date"],
                workout["title"],
                workout["workout_type"],
                workout["target_distance_km"],
                workout["target_duration_min"],
                workout["target_pace"],
                workout["notes"],
                workout["status"],
            ),
        )

    conn.commit()
    return plan_id


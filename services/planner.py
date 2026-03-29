import json
from datetime import datetime

REQUIRED_DAY_FIELDS = [
    "date",
    "title",
    "workout_type",
    "target_distance_km",
    "target_duration_min",
    "target_pace",
    "notes",
]


def get_active_plan(conn):
    row = conn.execute(
        """
        SELECT *
        FROM training_plans
        WHERE is_active = 1
        ORDER BY id DESC
        LIMIT 1
        """
    ).fetchone()
    return dict(row) if row else None


def get_model_config(config, model_key):
    for item in config.get("models", []):
        if item.get("key") == model_key:
            return item
    raise RuntimeError(f"Unknown model key: {model_key}")


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
    conn.execute("UPDATE training_plans SET is_active = 0 WHERE is_active = 1")
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
            is_active,
            source_model_key,
            replaced_plan_id,
            input_summary_json,
            plan_markdown,
            plan_json
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            payload["created_at"],
            payload["plan_type"],
            payload.get("goal_race_distance"),
            payload.get("goal_race_date"),
            payload.get("goal_notes"),
            payload.get("provider"),
            payload.get("model"),
            payload.get("is_active", 1),
            payload.get("source_model_key"),
            payload.get("replaced_plan_id"),
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


def mark_replaced_workouts(conn, old_plan_id, new_plan_id, today):
    conn.execute(
        """
        UPDATE plan_workouts
        SET is_replaced = 1,
            replaced_at = ?,
            replaced_by_plan_id = ?
        WHERE plan_id = ?
          AND plan_date > ?
          AND status != 'done'
        """,
        (
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            new_plan_id,
            old_plan_id,
            today,
        ),
    )


def regenerate_plan(conn, config, model_key, plan_request, generator, today=None):
    active_plan = get_active_plan(conn)
    if not active_plan:
        raise RuntimeError("No active plan to regenerate")

    model_config = get_model_config(config, model_key)
    generated_payload = generator(conn, config, plan_request, model_config, active_plan)
    generated_payload["source_model_key"] = model_config["key"]
    generated_payload["replaced_plan_id"] = active_plan["id"]
    generated_payload["is_active"] = 1
    new_plan_id = save_training_plan(conn, generated_payload)
    mark_replaced_workouts(
        conn,
        old_plan_id=active_plan["id"],
        new_plan_id=new_plan_id,
        today=today or datetime.now().strftime("%Y-%m-%d"),
    )
    conn.commit()
    return new_plan_id


def build_planning_context(conn, plan_request):
    recent_runs = [
        dict(row)
        for row in conn.execute(
            """
            SELECT run_id, name, distance, moving_time, start_date_local, average_heartrate, average_speed
            FROM activities
            WHERE type = 'Run'
            ORDER BY start_date_local DESC
            LIMIT 20
            """
        ).fetchall()
    ]
    recent_logs = [
        dict(row)
        for row in conn.execute(
            """
            SELECT log_date, completed, actual_distance_km, actual_duration_min, notes
            FROM daily_logs
            ORDER BY log_date DESC, id DESC
            LIMIT 14
            """
        ).fetchall()
    ]
    return {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "plan_request": plan_request,
        "recent_runs": recent_runs,
        "recent_logs": recent_logs,
    }


def parse_ai_plan_response(text):
    text = text.strip()
    if text.startswith("```json"):
        text = text.removeprefix("```json").removesuffix("```").strip()
    if text.startswith("```"):
        text = text.removeprefix("```").removesuffix("```").strip()
    return json.loads(text)


def generate_training_plan(conn, config, plan_request):
    from openai import OpenAI

    model_key = plan_request.get("model_key")
    if not model_key:
        raise RuntimeError("Missing model_key")
    ai_config = get_model_config(config, model_key)
    missing = [
        field
        for field in ("provider_name", "api_key", "model")
        if not ai_config.get(field)
    ]
    if missing:
        raise RuntimeError(f"Missing AI config fields: {', '.join(missing)}")

    context = build_planning_context(conn, plan_request)
    client = OpenAI(
        api_key=ai_config["api_key"],
        base_url=ai_config.get("base_url") or None,
    )
    response = client.chat.completions.create(
        model=ai_config["model"],
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a running coach. Return JSON only with keys "
                    "'plan_markdown' and 'plan_json'. plan_json must include "
                    "'summary' and 'weeks[].days[]' with date, title, workout_type, "
                    "target_distance_km, target_duration_min, target_pace, notes."
                ),
            },
            {
                "role": "user",
                "content": json.dumps(context, ensure_ascii=False),
            },
        ],
        temperature=0.7,
    )
    content = response.choices[0].message.content or ""
    payload = parse_ai_plan_response(content)
    plan_json = payload.get("plan_json")
    if not plan_json:
        raise RuntimeError("AI response missing plan_json")

    return {
        "created_at": context["generated_at"],
        "plan_type": plan_request["plan_type"],
        "goal_race_distance": plan_request.get("goal_race_distance"),
        "goal_race_date": plan_request.get("goal_race_date"),
        "goal_notes": plan_request.get("goal_notes"),
        "provider": ai_config["provider_name"],
        "model": ai_config["model"],
        "source_model_key": ai_config["key"],
        "input_summary_json": json.dumps(context, ensure_ascii=False),
        "plan_markdown": payload.get("plan_markdown", ""),
        "plan_json": plan_json,
    }

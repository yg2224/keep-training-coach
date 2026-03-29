from datetime import datetime


def save_daily_log(conn, payload):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor = conn.execute(
        """
        INSERT INTO daily_logs (
            log_date,
            plan_workout_id,
            completed,
            actual_distance_km,
            actual_duration_min,
            actual_pace,
            average_heartrate,
            fatigue_score,
            mood_score,
            notes,
            created_at,
            updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            payload["log_date"],
            payload.get("plan_workout_id"),
            payload["completed"],
            payload.get("actual_distance_km"),
            payload.get("actual_duration_min"),
            payload.get("actual_pace"),
            payload.get("average_heartrate"),
            payload.get("fatigue_score"),
            payload.get("mood_score"),
            payload.get("notes"),
            now,
            now,
        ),
    )

    plan_workout_id = payload.get("plan_workout_id")
    if plan_workout_id:
        conn.execute(
            "UPDATE plan_workouts SET status = ? WHERE id = ?",
            (payload["completed"], plan_workout_id),
        )

    conn.commit()
    return cursor.lastrowid


def get_latest_log_for_date(conn, target_date):
    row = conn.execute(
        """
        SELECT daily_logs.*, plan_workouts.title
        FROM daily_logs
        LEFT JOIN plan_workouts ON plan_workouts.id = daily_logs.plan_workout_id
        WHERE log_date = ?
        ORDER BY daily_logs.id DESC
        LIMIT 1
        """,
        (target_date,),
    ).fetchone()
    return dict(row) if row else None

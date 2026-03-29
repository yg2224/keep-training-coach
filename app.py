import calendar
from datetime import datetime
from pathlib import Path

from flask import Flask, jsonify, redirect, render_template, request, url_for

from services.analysis import (
    build_completion_summary,
    build_dashboard_summary,
    build_distance_distribution,
    build_heatmap_data,
    build_monthly_stats,
    build_pace_distribution,
    build_prs,
    build_weekly_stats,
    load_runs,
)
from services.config_store import load_config, save_config
from services.keep_sync import sync_keep_activities
from services.logs import get_latest_log_for_date, save_daily_log
from services.planner import (
    generate_training_plan,
    get_active_plan,
    regenerate_plan,
    save_training_plan,
)
from services.storage import get_connection, init_db


def create_app(test_config=None):
    base_dir = Path(__file__).resolve().parent
    app = Flask(
        __name__,
        template_folder=str(base_dir / "web" / "templates"),
        static_folder=str(base_dir / "web" / "static"),
    )

    app.config.from_mapping(
        DATABASE=str(base_dir / "app_data" / "app.db"),
        CONFIG_PATH=str(base_dir / "app_data" / "config.json"),
        HOST="127.0.0.1",
        PORT=8008,
        KEEP_SYNC_HANDLER=sync_keep_activities,
        PLAN_GENERATOR=generate_training_plan,
    )
    if test_config:
        app.config.update(test_config)

    init_db(app.config["DATABASE"])

    def load_activity_rows():
        conn = get_connection(app.config["DATABASE"])
        try:
            return load_runs(conn)
        finally:
            conn.close()

    def fetch_latest_plan():
        conn = get_connection(app.config["DATABASE"])
        try:
            plan = get_active_plan(conn)
            if not plan:
                return None, []
            workouts = conn.execute(
                """
                SELECT *
                FROM plan_workouts
                WHERE plan_id = ?
                  AND is_replaced = 0
                ORDER BY plan_date ASC, id ASC
                """,
                (plan["id"],),
            ).fetchall()
            return plan, [dict(item) for item in workouts]
        finally:
            conn.close()

    def fetch_recent_logs(limit=10):
        conn = get_connection(app.config["DATABASE"])
        try:
            rows = conn.execute(
                """
                SELECT daily_logs.*, plan_workouts.title
                FROM daily_logs
                LEFT JOIN plan_workouts ON plan_workouts.id = daily_logs.plan_workout_id
                ORDER BY log_date DESC, daily_logs.id DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
            return [dict(item) for item in rows]
        finally:
            conn.close()

    def parse_month(month_value):
        if month_value:
            return datetime.strptime(f"{month_value}-01", "%Y-%m-%d")
        today = datetime.now()
        return datetime(today.year, today.month, 1)

    def build_month_calendar_payload(month_value):
        month_start = parse_month(month_value)
        month_key = month_start.strftime("%Y-%m")
        prev_month = (
            datetime(month_start.year - 1, 12, 1)
            if month_start.month == 1
            else datetime(month_start.year, month_start.month - 1, 1)
        )
        next_month = (
            datetime(month_start.year + 1, 1, 1)
            if month_start.month == 12
            else datetime(month_start.year, month_start.month + 1, 1)
        )

        conn = get_connection(app.config["DATABASE"])
        try:
            active_plan = get_active_plan(conn)
            workout_rows = []
            if active_plan:
                workout_rows = conn.execute(
                    """
                    SELECT *
                    FROM plan_workouts
                    WHERE plan_id = ?
                      AND is_replaced = 0
                      AND substr(plan_date, 1, 7) = ?
                    ORDER BY plan_date ASC, id ASC
                    """,
                    (active_plan["id"], month_key),
                ).fetchall()
            workouts_by_date = {}
            for row in workout_rows:
                data = dict(row)
                workouts_by_date.setdefault(data["plan_date"], data)

            log_rows = conn.execute(
                """
                SELECT *
                FROM daily_logs
                WHERE substr(log_date, 1, 7) = ?
                ORDER BY log_date ASC, id DESC
                """,
                (month_key,),
            ).fetchall()
            logs_by_date = {}
            for row in log_rows:
                data = dict(row)
                logs_by_date.setdefault(data["log_date"], data)
        finally:
            conn.close()

        weeks = []
        for week in calendar.Calendar(firstweekday=6).monthdatescalendar(
            month_start.year,
            month_start.month,
        ):
            week_items = []
            for day in week:
                day_key = day.strftime("%Y-%m-%d")
                if day.month != month_start.month:
                    week_items.append(None)
                    continue
                workout = workouts_by_date.get(day_key)
                latest_log = logs_by_date.get(day_key)
                week_items.append(
                    {
                        "date": day_key,
                        "day": day.day,
                        "workout_type": workout["workout_type"] if workout else "",
                        "completed": (
                            latest_log["completed"]
                            if latest_log
                            else (workout["status"] if workout else "")
                        ),
                    }
                )
            weeks.append(week_items)

        return {
            "month": month_key,
            "month_label": month_start.strftime("%B %Y"),
            "prev_month": prev_month.strftime("%Y-%m"),
            "next_month": next_month.strftime("%Y-%m"),
            "weeks": weeks,
        }

    def build_day_payload(target_date):
        conn = get_connection(app.config["DATABASE"])
        try:
            active_plan = get_active_plan(conn)
            workout = None
            if active_plan:
                row = conn.execute(
                    """
                    SELECT *
                    FROM plan_workouts
                    WHERE plan_id = ?
                      AND plan_date = ?
                      AND is_replaced = 0
                    ORDER BY id ASC
                    LIMIT 1
                    """,
                    (active_plan["id"], target_date),
                ).fetchone()
                workout = dict(row) if row else None
            latest_log = get_latest_log_for_date(conn, target_date)
        finally:
            conn.close()

        return {
            "date": target_date,
            "workout": workout,
            "latest_log": latest_log,
            "completed": latest_log["completed"] if latest_log else (workout["status"] if workout else ""),
        }

    @app.get("/")
    def index():
        calendar_payload = build_month_calendar_payload(request.args.get("month"))
        runs = load_activity_rows()
        summary = build_dashboard_summary(runs)
        latest_plan, workouts = fetch_latest_plan()
        config = load_config(app.config["CONFIG_PATH"])
        recent_runs = sorted(runs, key=lambda run: run["date"], reverse=True)[:5]
        return render_template(
            "index.html",
            page_title="Home",
            summary=summary,
            calendar_payload=calendar_payload,
            latest_plan=latest_plan,
            workouts=workouts[:5],
            recent_logs=fetch_recent_logs(5),
            model_count=len(config["models"]),
            recent_runs=recent_runs,
        )

    @app.post("/sync")
    def sync():
        config = load_config(app.config["CONFIG_PATH"])
        app.config["KEEP_SYNC_HANDLER"](
            app.config["DATABASE"],
            config["keep"]["phone_number"],
            config["keep"]["password"],
            sync_types=["running"],
        )
        return redirect(url_for("index"))

    @app.get("/api/calendar")
    def calendar_month():
        return jsonify(build_month_calendar_payload(request.args.get("month")))

    @app.get("/api/day/<target_date>")
    def day_detail(target_date):
        return jsonify(build_day_payload(target_date))

    @app.get("/analysis")
    def analysis():
        runs = load_activity_rows()
        latest_plan, workouts = fetch_latest_plan()
        return render_template(
            "analysis.html",
            page_title="Run Analysis",
            summary=build_dashboard_summary(runs),
            monthly_stats=build_monthly_stats(runs),
            weekly_stats=build_weekly_stats(runs),
            heatmap_data=build_heatmap_data(runs),
            pace_distribution=build_pace_distribution(runs),
            distance_distribution=build_distance_distribution(runs),
            completion_summary=build_completion_summary(workouts),
            prs=build_prs(runs),
            runs=sorted(runs, key=lambda run: run["date"], reverse=True)[:20],
        )

    @app.get("/plans")
    def plans():
        latest_plan, workouts = fetch_latest_plan()
        config = load_config(app.config["CONFIG_PATH"])
        return render_template(
            "plans.html",
            page_title="Training Plans",
            latest_plan=latest_plan,
            workouts=workouts,
            models=config["models"],
        )

    @app.post("/plans/generate")
    def generate_plan():
        config = load_config(app.config["CONFIG_PATH"])
        plan_request = {
            "model_key": request.form.get("model_key"),
            "plan_type": request.form.get("plan_type", "rolling_week"),
            "target_distance": request.form.get("target_distance") or None,
            "target_pace": request.form.get("target_pace") or None,
            "goal_race_distance": request.form.get("goal_race_distance") or None,
            "goal_race_date": request.form.get("goal_race_date") or None,
            "goal_race_pace": request.form.get("goal_race_pace") or None,
            "goal_notes": request.form.get("goal_notes", ""),
        }
        conn = get_connection(app.config["DATABASE"])
        try:
            payload = app.config["PLAN_GENERATOR"](conn, config, plan_request)
            save_training_plan(conn, payload)
        finally:
            conn.close()
        return redirect(url_for("plans"))

    @app.post("/plans/regenerate")
    def regenerate_plan_route():
        config = load_config(app.config["CONFIG_PATH"])
        plan_request = {
            "model_key": request.form.get("model_key"),
            "plan_type": request.form.get("plan_type", "rolling_week"),
            "target_distance": request.form.get("target_distance") or None,
            "target_pace": request.form.get("target_pace") or None,
            "goal_race_distance": request.form.get("goal_race_distance") or None,
            "goal_race_date": request.form.get("goal_race_date") or None,
            "goal_race_pace": request.form.get("goal_race_pace") or None,
            "goal_notes": request.form.get("goal_notes", ""),
        }
        conn = get_connection(app.config["DATABASE"])
        try:
            regenerate_plan(
                conn,
                config,
                plan_request["model_key"],
                plan_request,
                lambda db_conn, db_config, req, model_config, active_plan: app.config[
                    "PLAN_GENERATOR"
                ](
                    db_conn,
                    db_config,
                    {
                        **req,
                        "model_key": model_config["key"],
                        "active_plan_id": active_plan["id"],
                    },
                ),
                today=request.form.get("today"),
            )
        finally:
            conn.close()
        return redirect(url_for("plans"))

    @app.post("/api/day-log")
    def save_day_log_api():
        conn = get_connection(app.config["DATABASE"])
        try:
            save_daily_log(
                conn,
                {
                    "log_date": request.form["log_date"],
                    "plan_workout_id": request.form.get("plan_workout_id") or None,
                    "completed": request.form["completed"],
                    "actual_distance_km": request.form.get("actual_distance_km") or None,
                    "actual_duration_min": request.form.get("actual_duration_min") or None,
                    "actual_pace": request.form.get("actual_pace") or "",
                    "average_heartrate": request.form.get("average_heartrate") or None,
                    "fatigue_score": request.form.get("fatigue_score") or None,
                    "mood_score": request.form.get("mood_score") or None,
                    "notes": request.form.get("notes") or "",
                },
            )
            payload = build_day_payload(request.form["log_date"])
        finally:
            conn.close()
        return jsonify({"status": "ok", "day": payload})

    @app.get("/settings")
    def settings():
        config = load_config(app.config["CONFIG_PATH"])
        models = config["models"] or [
            {
                "key": "",
                "label": "",
                "provider_name": "",
                "base_url": "",
                "api_key": "",
                "model": "",
            }
        ]
        return render_template(
            "settings.html",
            page_title="Settings",
            config=config,
            models=models,
        )

    @app.post("/settings")
    def save_settings():
        model_keys = request.form.getlist("model_key")
        model_labels = request.form.getlist("model_label")
        model_provider_names = request.form.getlist("model_provider_name")
        model_base_urls = request.form.getlist("model_base_url")
        model_api_keys = request.form.getlist("model_api_key")
        model_names = request.form.getlist("model_name")
        models = []
        for index, key in enumerate(model_keys):
            values = {
                "key": key,
                "label": model_labels[index] if index < len(model_labels) else "",
                "provider_name": (
                    model_provider_names[index] if index < len(model_provider_names) else ""
                ),
                "base_url": model_base_urls[index] if index < len(model_base_urls) else "",
                "api_key": model_api_keys[index] if index < len(model_api_keys) else "",
                "model": model_names[index] if index < len(model_names) else "",
            }
            if any(values.values()):
                models.append(values)

        payload = {
            "keep": {
                "phone_number": request.form.get("phone_number", ""),
                "password": request.form.get("password", ""),
            },
            "models": models,
        }
        save_config(app.config["CONFIG_PATH"], payload)
        return redirect(url_for("settings"))

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(host=app.config["HOST"], port=app.config["PORT"], debug=True)

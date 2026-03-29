from pathlib import Path

from flask import Flask, redirect, render_template, request, url_for

from services.analysis import build_dashboard_summary, build_monthly_stats, build_prs, load_runs
from services.config_store import load_config, save_config
from services.keep_sync import sync_keep_activities
from services.logs import save_daily_log
from services.planner import generate_training_plan, save_training_plan
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
            plan = conn.execute(
                """
                SELECT *
                FROM training_plans
                ORDER BY id DESC
                LIMIT 1
                """
            ).fetchone()
            if not plan:
                return None, []
            workouts = conn.execute(
                """
                SELECT *
                FROM plan_workouts
                WHERE plan_id = ?
                ORDER BY plan_date ASC, id ASC
                """,
                (plan["id"],),
            ).fetchall()
            return dict(plan), [dict(item) for item in workouts]
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

    @app.get("/")
    def index():
        runs = load_activity_rows()
        summary = build_dashboard_summary(runs)
        latest_plan, workouts = fetch_latest_plan()
        recent_runs = sorted(runs, key=lambda run: run["date"], reverse=True)[:5]
        return render_template(
            "index.html",
            page_title="Home",
            summary=summary,
            recent_runs=recent_runs,
            latest_plan=latest_plan,
            workouts=workouts[:5],
            recent_logs=fetch_recent_logs(5),
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

    @app.get("/analysis")
    def analysis():
        runs = load_activity_rows()
        return render_template(
            "analysis.html",
            page_title="Run Analysis",
            summary=build_dashboard_summary(runs),
            monthly_stats=build_monthly_stats(runs),
            prs=build_prs(runs),
            runs=sorted(runs, key=lambda run: run["date"], reverse=True)[:20],
        )

    @app.get("/plans")
    def plans():
        latest_plan, workouts = fetch_latest_plan()
        return render_template(
            "plans.html",
            page_title="Training Plans",
            latest_plan=latest_plan,
            workouts=workouts,
        )

    @app.post("/plans/generate")
    def generate_plan():
        config = load_config(app.config["CONFIG_PATH"])
        plan_request = {
            "plan_type": request.form.get("plan_type", "rolling_week"),
            "goal_race_distance": request.form.get("goal_race_distance") or None,
            "goal_race_date": request.form.get("goal_race_date") or None,
            "goal_notes": request.form.get("goal_notes", ""),
        }
        conn = get_connection(app.config["DATABASE"])
        try:
            payload = app.config["PLAN_GENERATOR"](conn, config, plan_request)
            save_training_plan(conn, payload)
        finally:
            conn.close()
        return redirect(url_for("plans"))

    @app.get("/today")
    def today():
        _, workouts = fetch_latest_plan()
        return render_template(
            "today.html",
            page_title="Daily Log",
            workouts=workouts,
            recent_logs=fetch_recent_logs(10),
        )

    @app.post("/today")
    def submit_today_log():
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
        finally:
            conn.close()
        return redirect(url_for("today"))

    @app.get("/settings")
    def settings():
        return render_template(
            "settings.html",
            page_title="Settings",
            config=load_config(app.config["CONFIG_PATH"]),
        )

    @app.post("/settings")
    def save_settings():
        payload = {
            "keep": {
                "phone_number": request.form.get("phone_number", ""),
                "password": request.form.get("password", ""),
            },
            "ai": {
                "provider_name": request.form.get("provider_name", ""),
                "base_url": request.form.get("base_url", ""),
                "api_key": request.form.get("api_key", ""),
                "model": request.form.get("model", ""),
            },
        }
        save_config(app.config["CONFIG_PATH"], payload)
        return redirect(url_for("settings"))

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(host=app.config["HOST"], port=app.config["PORT"], debug=True)

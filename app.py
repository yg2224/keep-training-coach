import calendar
import threading
from datetime import datetime
from pathlib import Path

from flask import Flask, abort, g, jsonify, make_response, redirect, render_template, request, url_for

from services.analysis import (
    build_completion_summary,
    build_dashboard_summary,
    build_distance_distribution,
    filter_runs,
    build_heatmap_data,
    build_location_stats,
    build_monthly_stats,
    build_pace_distribution,
    build_prs,
    build_weekly_stats,
    build_yearly_stats,
    load_runs,
)
from services.config_store import load_config, save_config
from services.gpx_export import build_gpx_document, build_gpx_filename, trim_route_points_for_privacy
from services.keep_sync import sync_keep_activities
from services.i18n import (
    DEFAULT_LANGUAGE,
    TRANSLATIONS,
    format_calendar_month_label,
    get_calendar_weekday_labels,
    normalize_language,
    translate,
    translate_plan_type,
    translate_status,
)
from services.logs import get_latest_log_for_date, save_daily_log
from services.plan_jobs import (
    create_plan_job,
    get_active_plan_job,
    get_latest_plan_job,
    mark_plan_job_failed,
    mark_plan_job_running,
    mark_plan_job_succeeded,
    serialize_plan_job,
)
from services.planner import (
    generate_training_plan,
    get_active_plan,
    regenerate_plan,
    save_training_plan,
)
from services.routes import build_route_preview, deserialize_route_points, downsample_route_points
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
    static_files = [
        base_dir / "web" / "static" / "app.css",
        base_dir / "web" / "static" / "app.js",
    ]
    app.config["STATIC_ASSET_VERSION"] = str(
        max(int(path.stat().st_mtime_ns) for path in static_files if path.exists())
    )

    def get_request_language():
        query_lang = normalize_language(request.args.get("lang"))
        if query_lang:
            return query_lang
        cookie_lang = normalize_language(request.cookies.get("lang"))
        if cookie_lang:
            return cookie_lang
        return DEFAULT_LANGUAGE

    def t(key, **kwargs):
        return translate(g.get("lang", DEFAULT_LANGUAGE), key, **kwargs)

    @app.before_request
    def load_request_language():
        g.lang = get_request_language()

    @app.after_request
    def persist_request_language(response):
        selected = normalize_language(request.args.get("lang"))
        if selected and request.cookies.get("lang") != selected:
            response.set_cookie("lang", selected, max_age=31536000, samesite="Lax")
        return response

    @app.context_processor
    def inject_i18n():
        def url_for_lang(endpoint, **values):
            values.setdefault("lang", g.get("lang", DEFAULT_LANGUAGE))
            return url_for(endpoint, **values)

        def switch_lang_url(target_lang):
            normalized = normalize_language(target_lang) or DEFAULT_LANGUAGE
            if not request.endpoint:
                return "#"
            values = dict(request.view_args or {})
            for key, value in request.args.items():
                if key != "lang":
                    values[key] = value
            values["lang"] = normalized
            return url_for(request.endpoint, **values)

        def status_label(value):
            return translate_status(g.get("lang", DEFAULT_LANGUAGE), value)

        def plan_type_label(value):
            return translate_plan_type(g.get("lang", DEFAULT_LANGUAGE), value)

        def nav_active(endpoint):
            targets = endpoint if isinstance(endpoint, (list, tuple, set)) else [endpoint]
            return "is-active" if request.endpoint in targets else ""

        def format_pace(value):
            if value in (None, ""):
                return translate(g.get("lang", DEFAULT_LANGUAGE), "common.not_set")
            total_seconds = int(round(float(value)))
            minutes, seconds = divmod(total_seconds, 60)
            return f"{minutes}:{seconds:02d} /km"

        return {
            "current_lang": g.get("lang", DEFAULT_LANGUAGE),
            "calendar_weekdays": get_calendar_weekday_labels(g.get("lang", DEFAULT_LANGUAGE)),
            "format_pace": format_pace,
            "js_copy": TRANSLATIONS.get(g.get("lang", DEFAULT_LANGUAGE), TRANSLATIONS[DEFAULT_LANGUAGE]),
            "nav_active": nav_active,
            "plan_type_label": plan_type_label,
            "status_label": status_label,
            "static_asset_version": app.config["STATIC_ASSET_VERSION"],
            "switch_lang_url": switch_lang_url,
            "t": t,
            "url_for_lang": url_for_lang,
        }

    def load_activity_rows():
        conn = get_connection(app.config["DATABASE"])
        try:
            return load_runs(conn)
        finally:
            conn.close()

    def fetch_activities():
        return sorted(load_activity_rows(), key=lambda run: run["date"], reverse=True)

    def fetch_activity_detail(run_id):
        conn = get_connection(app.config["DATABASE"])
        try:
            row = conn.execute(
                """
                SELECT *
                FROM activities
                WHERE run_id = ?
                  AND type = 'Run'
                LIMIT 1
                """,
                (run_id,),
            ).fetchone()
        finally:
            conn.close()
        if not row:
            return None
        runs = filter_runs([dict(row)])
        if not runs:
            return None
        activity = runs[0]
        activity["route_points"] = deserialize_route_points(activity.get("summary_polyline"))
        activity["route_preview"] = build_route_preview(downsample_route_points(activity["route_points"]))
        return activity

    def is_async_request():
        return request.headers.get("X-Requested-With") == "XMLHttpRequest"

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

    def build_plans_page_context():
        latest_plan, workouts = fetch_latest_plan()
        config = load_config(app.config["CONFIG_PATH"])
        return {
            "latest_plan": latest_plan,
            "workouts": workouts,
            "models": config["models"],
        }

    def build_plan_request():
        return {
            "model_key": request.form.get("model_key"),
            "plan_type": request.form.get("plan_type", "rolling_week"),
            "target_distance": request.form.get("target_distance") or None,
            "target_pace": request.form.get("target_pace") or None,
            "goal_race_distance": request.form.get("goal_race_distance") or None,
            "goal_race_date": request.form.get("goal_race_date") or None,
            "goal_race_pace": request.form.get("goal_race_pace") or None,
            "goal_notes": request.form.get("goal_notes", ""),
            "language": g.lang,
        }

    def perform_generate_plan(config, plan_request):
        conn = get_connection(app.config["DATABASE"])
        try:
            payload = app.config["PLAN_GENERATOR"](conn, config, plan_request)
            return save_training_plan(conn, payload)
        finally:
            conn.close()

    def perform_regenerate_plan(config, plan_request, today=None):
        conn = get_connection(app.config["DATABASE"])
        try:
            return regenerate_plan(
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
                today=today,
            )
        finally:
            conn.close()

    def run_plan_job(job_id, job_type, config, plan_request, today=None):
        conn = get_connection(app.config["DATABASE"])
        try:
            mark_plan_job_running(conn, job_id)
            conn.close()
            conn = None
            if job_type == "generate":
                plan_id = perform_generate_plan(config, plan_request)
            else:
                plan_id = perform_regenerate_plan(config, plan_request, today=today)
            conn = get_connection(app.config["DATABASE"])
            mark_plan_job_succeeded(conn, job_id, plan_id)
        except Exception as exc:
            if conn is not None:
                conn.close()
            conn = get_connection(app.config["DATABASE"])
            try:
                mark_plan_job_failed(conn, job_id, str(exc))
            finally:
                conn.close()
            return
        finally:
            if conn is not None:
                conn.close()

    def submit_plan_job(job_type, config, plan_request, today=None):
        conn = get_connection(app.config["DATABASE"])
        try:
            active_job = get_active_plan_job(conn)
            if active_job:
                raise RuntimeError("Another plan job is already running")
            job_id = create_plan_job(conn, job_type, g.lang)
        finally:
            conn.close()
        worker = threading.Thread(
            target=run_plan_job,
            args=(job_id, job_type, config, plan_request, today),
            daemon=True,
        )
        worker.start()
        return job_id

    def parse_month(month_value):
        if month_value:
            return datetime.strptime(f"{month_value}-01", "%Y-%m-%d")
        today = datetime.now()
        return datetime(today.year, today.month, 1)

    def build_month_calendar_payload(month_value, lang):
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
            "month_label": format_calendar_month_label(month_start, lang),
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
        calendar_payload = build_month_calendar_payload(request.args.get("month"), g.lang)
        runs = fetch_activities()
        summary = build_dashboard_summary(runs)
        latest_plan, workouts = fetch_latest_plan()
        config = load_config(app.config["CONFIG_PATH"])
        recent_runs = runs[:5]
        return render_template(
            "index.html",
            page_title_key="page.home",
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
        return jsonify(build_month_calendar_payload(request.args.get("month"), g.lang))

    @app.get("/api/day/<target_date>")
    def day_detail(target_date):
        return jsonify(build_day_payload(target_date))

    @app.get("/analysis")
    def analysis():
        runs = fetch_activities()
        latest_plan, workouts = fetch_latest_plan()
        return render_template(
            "analysis.html",
            page_title_key="page.analysis",
            summary=build_dashboard_summary(runs),
            monthly_stats=build_monthly_stats(runs),
            weekly_stats=build_weekly_stats(runs),
            yearly_stats=build_yearly_stats(runs),
            location_stats=build_location_stats(runs, unknown_label=t("analysis.unknown_location")),
            heatmap_data=build_heatmap_data(runs, lang=g.lang),
            pace_distribution=build_pace_distribution(runs),
            distance_distribution=build_distance_distribution(runs),
            completion_summary=build_completion_summary(workouts),
            prs=build_prs(runs),
            runs=sorted(runs, key=lambda run: run["date"], reverse=True)[:20],
        )

    @app.get("/activities")
    def activities():
        return render_template(
            "activities.html",
            page_title_key="page.activities",
            activities=fetch_activities(),
        )

    @app.get("/activities/<run_id>")
    def activity_detail(run_id):
        activity = fetch_activity_detail(run_id)
        if not activity:
            abort(404)
        return render_template(
            "activity_detail.html",
            page_title_key="page.activities",
            activity=activity,
        )

    @app.get("/activities/<run_id>/export.gpx")
    def activity_export_gpx(run_id):
        activity = fetch_activity_detail(run_id)
        if not activity or len(activity["route_points"]) < 2:
            abort(404)
        is_private = request.args.get("privacy") in {"1", "true", "yes"}
        points = (
            trim_route_points_for_privacy(activity["route_points"])
            if is_private
            else activity["route_points"]
        )
        if len(points) < 2:
            abort(400, description="Route too short for private export")
        gpx = build_gpx_document(
            activity["name"],
            activity["start_date_local"],
            points,
            moving_time=activity.get("moving_time"),
            distance_meters=activity.get("distance"),
        )
        response = make_response(gpx)
        response.mimetype = "application/gpx+xml"
        response.headers["Content-Disposition"] = (
            f'attachment; filename="{build_gpx_filename(activity["run_id"], is_private=is_private)}"'
        )
        return response

    @app.get("/plans")
    def plans():
        return render_template(
            "plans.html",
            page_title_key="page.plans",
            **build_plans_page_context(),
        )

    @app.get("/plans/results-fragment")
    def plans_results_fragment():
        return render_template("plans_results.html", **build_plans_page_context())

    @app.post("/plans/generate")
    def generate_plan():
        config = load_config(app.config["CONFIG_PATH"])
        plan_request = build_plan_request()
        if is_async_request():
            try:
                job_id = submit_plan_job("generate", config, plan_request)
            except RuntimeError as exc:
                return jsonify({"status": "error", "message": str(exc)}), 409
            conn = get_connection(app.config["DATABASE"])
            try:
                job = get_latest_plan_job(conn)
            finally:
                conn.close()
            return jsonify({"status": "accepted", "job": serialize_plan_job(job)}), 202
        try:
            perform_generate_plan(config, plan_request)
        except Exception as exc:
            raise
        return redirect(url_for("plans", lang=g.lang))

    @app.post("/plans/regenerate")
    def regenerate_plan_route():
        config = load_config(app.config["CONFIG_PATH"])
        plan_request = build_plan_request()
        if is_async_request():
            try:
                job_id = submit_plan_job(
                    "regenerate",
                    config,
                    plan_request,
                    today=request.form.get("today"),
                )
            except RuntimeError as exc:
                return jsonify({"status": "error", "message": str(exc)}), 409
            conn = get_connection(app.config["DATABASE"])
            try:
                job = get_latest_plan_job(conn)
            finally:
                conn.close()
            return jsonify({"status": "accepted", "job": serialize_plan_job(job)}), 202
        try:
            perform_regenerate_plan(config, plan_request, today=request.form.get("today"))
        except Exception:
            raise
        return redirect(url_for("plans", lang=g.lang))

    @app.get("/api/plan-jobs/latest")
    def plan_job_status_latest():
        conn = get_connection(app.config["DATABASE"])
        try:
            job = get_latest_plan_job(conn)
        finally:
            conn.close()
        return jsonify({"job": serialize_plan_job(job)})

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
            page_title_key="page.settings",
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
    app.run(
        host=app.config["HOST"],
        port=app.config["PORT"],
        debug=True,
        use_reloader=False,
    )

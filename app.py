from pathlib import Path

from flask import Flask, render_template

from services.analysis import build_dashboard_summary, build_monthly_stats, build_prs, load_runs
from services.config_store import load_config
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

    @app.get("/")
    def index():
        runs = load_activity_rows()
        summary = build_dashboard_summary(runs)
        recent_runs = sorted(runs, key=lambda run: run["date"], reverse=True)[:5]
        return render_template(
            "index.html",
            page_title="Home",
            summary=summary,
            recent_runs=recent_runs,
        )

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
        return render_template(
            "plans.html",
            page_title="Training Plans",
        )

    @app.get("/today")
    def today():
        return render_template(
            "today.html",
            page_title="Daily Log",
        )

    @app.get("/settings")
    def settings():
        return render_template(
            "settings.html",
            page_title="Settings",
            config=load_config(app.config["CONFIG_PATH"]),
        )

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(host=app.config["HOST"], port=app.config["PORT"], debug=True)

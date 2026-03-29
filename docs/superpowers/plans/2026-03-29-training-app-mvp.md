# Keep Training App MVP Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a local Flask app that syncs Keep data, analyzes running history, generates AI training plans, and records daily completion logs.

**Architecture:** The app uses a single local SQLite database plus a local JSON config file. Flask renders HTML pages directly, while small focused service modules handle storage, Keep sync, analysis, planning, and daily logs. Existing Keep sync and analysis logic from the source workspace should be adapted into services rather than duplicated blindly.

**Tech Stack:** Python 3.12, Flask, SQLite, requests, pycryptodome, OpenAI Python SDK, Jinja2, unittest

---

### Task 1: Scaffold the repository and persistence layer

**Files:**
- Create: `requirements.txt`
- Create: `.gitignore`
- Create: `services/__init__.py`
- Create: `services/storage.py`
- Create: `services/config_store.py`
- Create: `tests/test_storage.py`

- [ ] **Step 1: Write the failing storage tests**

```python
def test_init_db_creates_expected_tables(self):
    init_db(self.db_path)
    names = get_table_names(self.db_path)
    self.assertIn("activities", names)
    self.assertIn("training_plans", names)
```

- [ ] **Step 2: Run the storage tests to verify they fail**

Run: `python -m unittest tests.test_storage -v`
Expected: FAIL because storage modules do not exist yet.

- [ ] **Step 3: Implement minimal storage and config modules**

```python
def init_db(db_path): ...
def get_connection(db_path): ...
def load_config(config_path): ...
def save_config(config_path, data): ...
```

- [ ] **Step 4: Run the storage tests to verify they pass**

Run: `python -m unittest tests.test_storage -v`
Expected: PASS

- [ ] **Step 5: Commit the scaffold**

```bash
git add requirements.txt .gitignore services tests
git commit -m "feat: 初始化训练应用存储层"
```

### Task 2: Add analysis services from tests first

**Files:**
- Create: `services/analysis.py`
- Create: `tests/test_analysis.py`

- [ ] **Step 1: Write the failing analysis tests**

```python
def test_build_dashboard_summary_for_runs_only(self):
    summary = build_dashboard_summary(sample_runs)
    self.assertEqual(summary["total_runs"], 2)
```

- [ ] **Step 2: Run the analysis tests to verify they fail**

Run: `python -m unittest tests.test_analysis -v`
Expected: FAIL because analysis functions do not exist yet.

- [ ] **Step 3: Implement minimal run analysis helpers**

```python
def load_runs(conn): ...
def build_dashboard_summary(runs): ...
def build_monthly_stats(runs): ...
def build_prs(runs): ...
```

- [ ] **Step 4: Run the analysis tests to verify they pass**

Run: `python -m unittest tests.test_analysis -v`
Expected: PASS

- [ ] **Step 5: Commit the analysis service**

```bash
git add services/analysis.py tests/test_analysis.py
git commit -m "feat: 添加跑步分析服务"
```

### Task 3: Add planner parsing and daily log behavior

**Files:**
- Create: `services/planner.py`
- Create: `services/logs.py`
- Create: `tests/test_planner.py`
- Create: `tests/test_logs.py`

- [ ] **Step 1: Write the failing planner and log tests**

```python
def test_parse_plan_json_creates_daily_workouts(self): ...
def test_save_daily_log_updates_workout_status(self): ...
```

- [ ] **Step 2: Run those tests to verify they fail**

Run: `python -m unittest tests.test_planner tests.test_logs -v`
Expected: FAIL because planner and log modules do not exist yet.

- [ ] **Step 3: Implement minimal planner parsing and log persistence**

```python
def parse_plan_json(plan_id, plan_json): ...
def save_daily_log(conn, payload): ...
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `python -m unittest tests.test_planner tests.test_logs -v`
Expected: PASS

- [ ] **Step 5: Commit planner and log services**

```bash
git add services/planner.py services/logs.py tests/test_planner.py tests/test_logs.py
git commit -m "feat: 添加计划解析与每日打卡服务"
```

### Task 4: Add Flask app routes and pages

**Files:**
- Create: `app.py`
- Create: `web/templates/layout.html`
- Create: `web/templates/index.html`
- Create: `web/templates/analysis.html`
- Create: `web/templates/plans.html`
- Create: `web/templates/today.html`
- Create: `web/templates/settings.html`
- Create: `web/static/app.css`
- Create: `web/static/app.js`
- Create: `tests/test_app.py`

- [ ] **Step 1: Write the failing Flask route tests**

```python
def test_home_page_renders(self):
    response = self.client.get("/")
    self.assertEqual(response.status_code, 200)
```

- [ ] **Step 2: Run the route tests to verify they fail**

Run: `python -m unittest tests.test_app -v`
Expected: FAIL because the Flask app does not exist yet.

- [ ] **Step 3: Implement minimal Flask app and templates**

```python
def create_app(test_config=None): ...
@app.get("/")
def index(): ...
```

- [ ] **Step 4: Run the route tests to verify they pass**

Run: `python -m unittest tests.test_app -v`
Expected: PASS

- [ ] **Step 5: Commit the web app shell**

```bash
git add app.py web tests/test_app.py
git commit -m "feat: 添加本地训练应用网页骨架"
```

### Task 5: Integrate Keep sync and AI provider workflows

**Files:**
- Create: `services/keep_sync.py`
- Modify: `app.py`
- Modify: `services/planner.py`
- Modify: `tests/test_app.py`

- [ ] **Step 1: Write failing integration tests for settings, sync, and plan generation**

```python
def test_post_settings_persists_config(self): ...
def test_post_generate_plan_stores_plan_and_workouts(self): ...
```

- [ ] **Step 2: Run the integration tests to verify they fail**

Run: `python -m unittest tests.test_app -v`
Expected: FAIL because POST flows are incomplete.

- [ ] **Step 3: Implement settings save, sync trigger, and AI generation plumbing**

```python
def sync_keep_activities(...): ...
def generate_training_plan(...): ...
```

- [ ] **Step 4: Run the app tests to verify they pass**

Run: `python -m unittest tests.test_app -v`
Expected: PASS

- [ ] **Step 5: Commit the workflow integration**

```bash
git add app.py services tests/test_app.py
git commit -m "feat: 打通同步与训练计划流程"
```

### Task 6: Full verification and local startup

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Add startup instructions**

```markdown
python -m venv .venv
python -m pip install -r requirements.txt
python app.py
```

- [ ] **Step 2: Run the full test suite**

Run: `python -m unittest discover -s tests -v`
Expected: PASS

- [ ] **Step 3: Run syntax verification**

Run: `python -m py_compile app.py services\\*.py tests\\*.py`
Expected: no output

- [ ] **Step 4: Launch the app locally**

Run: `python app.py`
Expected: Flask starts on `127.0.0.1:8008`

- [ ] **Step 5: Commit docs and final polish**

```bash
git add README.md
git commit -m "docs: 补充启动与使用说明"
```

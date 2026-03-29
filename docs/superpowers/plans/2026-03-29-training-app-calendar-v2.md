# Keep Training App Calendar V2 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Upgrade the local training app into a calendar-driven weekly planning tool with multi-model settings, single active plan management, modal daily logging, and richer analysis charts.

**Architecture:** Keep the existing Flask + SQLite foundation, but introduce schema/config migration support, dedicated calendar payload helpers, active-plan and regeneration rules in the planner, and a heavier front-end layer on the home and analysis pages. Reuse the existing service layout while tightening module boundaries instead of rewriting the stack.

**Tech Stack:** Python 3.11+, Flask, SQLite, requests, pycryptodome, OpenAI Python SDK, Jinja2, vanilla JavaScript, Chart.js, unittest

---

### Task 1: Migrate config and schema for calendar v2

**Files:**
- Modify: `services/storage.py`
- Modify: `services/config_store.py`
- Modify: `tests/test_storage.py`

- [ ] **Step 1: Write failing migration tests**

```python
def test_load_config_migrates_single_ai_config_to_models(self):
    ...

def test_init_db_adds_active_plan_columns(self):
    ...
```

- [ ] **Step 2: Run the storage tests to verify they fail**

Run: `python -m unittest tests.test_storage -v`
Expected: FAIL because config migration and new schema columns do not exist yet.

- [ ] **Step 3: Implement config normalization and schema migration**

```python
def normalize_config(data): ...
def ensure_column(conn, table_name, column_sql): ...
```

- [ ] **Step 4: Run the storage tests to verify they pass**

Run: `python -m unittest tests.test_storage -v`
Expected: PASS

- [ ] **Step 5: Commit migration support**

```bash
git add services/storage.py services/config_store.py tests/test_storage.py
git commit -m "feat: 支持日历版配置与数据结构迁移"
```

### Task 2: Implement active weekly plans and regeneration rules

**Files:**
- Modify: `services/planner.py`
- Modify: `services/logs.py`
- Modify: `tests/test_planner.py`
- Modify: `tests/test_logs.py`

- [ ] **Step 1: Write failing planner tests for active plan and regeneration**

```python
def test_save_training_plan_marks_only_latest_plan_active(self):
    ...

def test_regenerate_future_incomplete_workouts_only_replaces_pending_future(self):
    ...
```

- [ ] **Step 2: Run planner and log tests to verify they fail**

Run: `python -m unittest tests.test_planner tests.test_logs -v`
Expected: FAIL because active-plan and replacement logic do not exist yet.

- [ ] **Step 3: Implement active-plan storage and regeneration helpers**

```python
def save_training_plan(conn, payload, *, replace_plan_id=None): ...
def regenerate_plan(conn, config, model_key, plan_request, generator): ...
def get_active_plan(conn): ...
```

- [ ] **Step 4: Run planner and log tests to verify they pass**

Run: `python -m unittest tests.test_planner tests.test_logs -v`
Expected: PASS

- [ ] **Step 5: Commit planner rule changes**

```bash
git add services/planner.py services/logs.py tests/test_planner.py tests/test_logs.py
git commit -m "feat: 支持单一生效周计划与未完成重生成"
```

### Task 3: Build calendar summary and day-detail endpoints

**Files:**
- Modify: `services/analysis.py`
- Modify: `app.py`
- Modify: `tests/test_app.py`

- [ ] **Step 1: Write failing app tests for month summary and day detail**

```python
def test_home_calendar_renders_month_grid(self):
    ...

def test_day_detail_endpoint_returns_plan_and_latest_log(self):
    ...
```

- [ ] **Step 2: Run the app tests to verify they fail**

Run: `python -m unittest tests.test_app -v`
Expected: FAIL because the home page is not calendar-driven and JSON endpoints do not exist yet.

- [ ] **Step 3: Implement calendar payload builders and endpoints**

```python
def build_month_calendar_payload(...): ...
@app.get("/api/calendar")
def calendar_month(): ...
@app.get("/api/day/<date>")
def day_detail(): ...
```

- [ ] **Step 4: Run the app tests to verify they pass**

Run: `python -m unittest tests.test_app -v`
Expected: PASS

- [ ] **Step 5: Commit calendar backend**

```bash
git add app.py services/analysis.py tests/test_app.py
git commit -m "feat: 添加首页月历与日期详情接口"
```

### Task 4: Replace the home UI with calendar + modal and multi-model settings

**Files:**
- Modify: `app.py`
- Modify: `web/templates/layout.html`
- Modify: `web/templates/index.html`
- Modify: `web/templates/plans.html`
- Modify: `web/templates/settings.html`
- Modify: `web/static/app.css`
- Modify: `web/static/app.js`
- Modify: `tests/test_app.py`

- [ ] **Step 1: Write failing route tests for multi-model settings and regeneration actions**

```python
def test_post_settings_saves_multiple_models(self):
    ...

def test_post_regenerate_replaces_future_incomplete_workouts(self):
    ...
```

- [ ] **Step 2: Run the app tests to verify they fail**

Run: `python -m unittest tests.test_app -v`
Expected: FAIL because the settings form and regenerate workflow do not support the new behavior yet.

- [ ] **Step 3: Implement the calendar UI, modal interactions, and model list forms**

```python
@app.post("/plans/regenerate")
def regenerate_plan_route(): ...
@app.post("/api/day-log")
def save_day_log_api(): ...
```

- [ ] **Step 4: Run the app tests to verify they pass**

Run: `python -m unittest tests.test_app -v`
Expected: PASS

- [ ] **Step 5: Commit the calendar UI and multi-model workflow**

```bash
git add app.py web tests/test_app.py
git commit -m "feat: 重做首页月历与多模型配置交互"
```

### Task 5: Expand analysis visuals and final verification

**Files:**
- Modify: `services/analysis.py`
- Modify: `web/templates/analysis.html`
- Modify: `web/static/app.js`
- Modify: `web/static/app.css`
- Modify: `README.md`
- Modify: `tests/test_analysis.py`
- Modify: `tests/test_app.py`

- [ ] **Step 1: Write failing analysis tests for weekly series, heatmap, and completion rate**

```python
def test_build_weekly_stats(self):
    ...

def test_build_heatmap_points(self):
    ...
```

- [ ] **Step 2: Run the analysis tests to verify they fail**

Run: `python -m unittest tests.test_analysis -v`
Expected: FAIL because the richer chart datasets do not exist yet.

- [ ] **Step 3: Implement chart datasets and render richer analysis UI**

```python
def build_weekly_stats(items): ...
def build_heatmap_data(items): ...
def build_completion_summary(conn): ...
```

- [ ] **Step 4: Run the full test suite and syntax checks**

Run: `python -m unittest discover -s tests -v`
Expected: PASS

Run: `python -m py_compile app.py services\\__init__.py services\\analysis.py services\\config_store.py services\\keep_sync.py services\\logs.py services\\planner.py services\\storage.py tests\\__init__.py tests\\test_analysis.py tests\\test_app.py tests\\test_logs.py tests\\test_planner.py tests\\test_storage.py`
Expected: no output

- [ ] **Step 5: Commit final analysis and docs updates**

```bash
git add services/analysis.py web README.md tests
git commit -m "feat: 扩展训练分析图表与月历工作台"
```

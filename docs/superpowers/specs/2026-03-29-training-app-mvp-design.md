# Keep Training App MVP Design

## Goal

Build a local single-user app that can:

- sync Keep activity data from the web UI
- analyze running data in the browser
- generate training plans through an OpenAI-compatible provider
- record daily completion logs for planned workouts

The app is local-only and intended for personal use on one machine.

## Scope

The MVP includes four capabilities:

1. Keep data sync
2. Run-focused analysis
3. AI training plan generation
4. Daily completion logging

## Non-goals

The MVP does not include:

- multi-user support
- cloud sync
- background schedulers
- auto-replanning of the entire plan after every log
- advanced physiology modeling

## Architecture

Use `Flask + SQLite + server-rendered HTML`.

The app will run as a local HTTP service on `127.0.0.1:8008`.

Core modules:

- `app.py`: Flask app and routes
- `services/storage.py`: SQLite initialization and queries
- `services/config_store.py`: local JSON config read/write
- `services/keep_sync.py`: Keep login, fetch, parse, persist
- `services/analysis.py`: run analysis aggregation
- `services/planner.py`: AI prompt building, provider call, plan parsing
- `services/logs.py`: daily log save and workout status updates

## Directory Structure

```text
keep-training-coach/
  app.py
  requirements.txt
  .gitignore
  app_data/
    app.db
    config.json
  services/
    __init__.py
    storage.py
    config_store.py
    keep_sync.py
    analysis.py
    planner.py
    logs.py
  web/
    templates/
      layout.html
      index.html
      analysis.html
      plans.html
      today.html
      settings.html
    static/
      app.css
      app.js
  tests/
    test_storage.py
    test_analysis.py
    test_planner.py
    test_logs.py
    test_app.py
```

## Config

`app_data/config.json` stores:

- `keep.phone_number`
- `keep.password`
- `ai.provider_name`
- `ai.base_url`
- `ai.api_key`
- `ai.model`

Config is local-only and editable from the settings page.

## Data Model

### activities

Activity data synced from Keep.

Minimum fields:

- `run_id`
- `name`
- `type`
- `subtype`
- `distance`
- `moving_time`
- `elapsed_time`
- `start_date`
- `start_date_local`
- `average_heartrate`
- `average_speed`
- `elevation_gain`
- `summary_polyline`

### training_plans

One generated plan record.

Fields:

- `id`
- `created_at`
- `plan_type`
- `goal_race_distance`
- `goal_race_date`
- `goal_notes`
- `provider`
- `model`
- `input_summary_json`
- `plan_markdown`
- `plan_json`

### plan_workouts

One row per planned workout.

Fields:

- `id`
- `plan_id`
- `plan_date`
- `title`
- `workout_type`
- `target_distance_km`
- `target_duration_min`
- `target_pace`
- `notes`
- `status`

Allowed `status` values:

- `planned`
- `done`
- `partial`
- `skipped`

### daily_logs

Daily completion logs.

Fields:

- `id`
- `log_date`
- `plan_workout_id`
- `completed`
- `actual_distance_km`
- `actual_duration_min`
- `actual_pace`
- `average_heartrate`
- `fatigue_score`
- `mood_score`
- `notes`
- `created_at`
- `updated_at`

## UI Pages

### Home

Shows:

- latest sync result
- recent activities
- current training plan summary
- recent log status

Actions:

- trigger sync
- navigate to analysis, plans, today, settings

### Analysis

Run-only analysis:

- total runs
- total distance
- total duration
- average pace
- total elevation
- recent 12-month trend
- distance and pace distributions
- approximate PR table
- recent run list

### Plans

Supports:

- race-goal plan
- rolling next-week plan

Shows both:

- readable markdown plan
- structured daily workouts

### Today

Allows logging:

- completed state
- actual distance
- actual duration
- actual pace
- average heartrate
- fatigue score
- mood score
- notes

All detailed fields are optional.

### Settings

Allows saving Keep credentials and AI provider config.

## AI Contract

The planner uses the OpenAI Python SDK in a compatible mode with configurable:

- `base_url`
- `api_key`
- `model`

The app sends:

- recent 8 to 12 week run summary
- recent 20 run summary
- PRs and longest distance
- recent completion logs
- user goals and notes

The app requests:

1. `plan_markdown`
2. `plan_json`

Expected `plan_json` shape:

```json
{
  "summary": "Cycle summary",
  "weeks": [
    {
      "label": "Week 1",
      "days": [
        {
          "date": "2026-04-01",
          "title": "Easy Run",
          "workout_type": "easy",
          "target_distance_km": 8,
          "target_duration_min": 45,
          "target_pace": "5:30-5:50 /km",
          "notes": "Keep it relaxed"
        }
      ]
    }
  ]
}
```

If JSON parsing fails, the app still preserves `plan_markdown` and reports that structured parsing failed.

## Error Handling

- Keep login failure: show error, keep old data
- partial sync failure: keep successful records and show error count
- AI config missing: block generation and show missing fields
- AI request failure: keep existing plans and show error
- invalid AI JSON: keep markdown result and show parse warning
- unlinked daily log: allow save without a linked workout

## Testing Strategy

Tests will cover:

1. database initialization
2. run analysis aggregation
3. plan JSON parsing into workouts
4. daily log persistence and workout status updates
5. basic Flask routes and form handling

External network behavior must be mocked.

## Success Criteria

The MVP is complete when:

- Keep credentials can be saved in the UI
- a sync can be triggered from the UI
- run analysis renders in the browser
- an OpenAI-compatible provider can generate a plan
- the plan is stored as workouts
- daily completion logs can be recorded
- recent logs are included in future plan generation context

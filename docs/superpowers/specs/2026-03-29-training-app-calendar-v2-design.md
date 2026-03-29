# Keep Training App Calendar V2 Design

## Goal

Upgrade the current local training app from a page-based MVP into a calendar-driven dashboard that:

- uses a monthly calendar as the home page
- opens a modal when a date is selected
- shows that day's training plan and allows completion feedback in the modal
- supports multiple saved AI model configurations
- keeps exactly one active weekly plan at a time
- regenerates only future incomplete workouts
- expands the analysis page with richer charts

The app remains local-only and single-user.

## Scope

This revision adds or changes the following behavior:

1. Home page becomes a monthly calendar dashboard
2. Daily logging moves into a calendar modal
3. Settings supports a list of AI model configurations
4. Plan generation always produces one active weekly plan
5. Regeneration replaces only future incomplete workouts
6. Analysis page gains additional charts and visual summaries

## Non-goals

This revision still does not include:

- multi-user support
- cloud sync
- automatic background sync
- long-horizon multi-month plan management
- full SPA frontend rewrite
- automatic complete-plan rescheduling after every log

## Product Structure

The app is reorganized into four main pages:

1. `Home`
   - primary monthly calendar dashboard
   - click a day to open a modal
   - show plan summary and completion state on each day cell
2. `Plans`
   - generate the current active weekly plan
   - choose one saved model configuration
   - regenerate future incomplete workouts only
3. `Analysis`
   - richer run analysis and execution charts
4. `Settings`
   - Keep credentials
   - multiple AI model configurations

The previous standalone `Today` workflow is folded into the home calendar modal and is no longer the main interaction path.

## Home Calendar Design

The home page uses a full monthly calendar layout similar to a standard planner view.

### Calendar Header

The header shows:

- current month label
- previous month button
- next month button

### Day Cell Content

Each day cell shows exactly two lightweight data points:

- workout type
- completion status

This is intentionally constrained to avoid visual clutter.

### Selected Day Interaction

Clicking a day opens a modal. The modal contains:

1. Day plan details
   - title
   - workout type
   - target distance or duration
   - target pace
   - notes
2. Completion form
   - completed state
   - actual distance
   - actual duration
   - actual pace
   - average heartrate
   - fatigue score
   - mood score
   - notes

Detailed fields remain optional. Completion state is required.

### Calendar Data Flow

1. Page loads a month summary payload
2. Backend returns day-level workout and status summaries for that month
3. User clicks a day
4. Frontend requests that day detail payload
5. Modal opens with plan detail and the latest log, if any
6. User submits feedback
7. Backend saves the log, updates workout status, returns success
8. Frontend refreshes that day cell and modal content

## Plan Model

The system supports exactly one active plan at a time.

The plan unit is one week.

### Initial Plan Generation

The user:

- chooses a saved model configuration
- selects plan type
- optionally enters notes or race context

The backend creates a new weekly plan and marks it as active.

### Regeneration Rule

When the user regenerates:

- only workouts after today are considered
- only workouts that are not completed are replaced
- completed workouts and their logs remain untouched
- the resulting plan remains the only active plan

This rule prevents historical data loss and avoids rewriting completed work.

## Multi-Model Configuration

Settings now stores a list of model configurations rather than a single AI config.

Each model item contains:

- `key`
- `label`
- `provider_name`
- `base_url`
- `api_key`
- `model`

The settings page supports:

- add model
- edit model
- delete model

The plans page allows choosing one saved model when generating or regenerating the active weekly plan.

## Data Model Changes

### activities

No major conceptual change. It remains the Keep sync source of truth for workout history.

### training_plans

Add:

- `is_active`
- `source_model_key`
- `replaced_plan_id`

Purpose:

- track the single active plan
- remember which saved model created it
- preserve lineage when regeneration creates a replacement plan

### plan_workouts

Add:

- `is_replaced`
- `replaced_at`
- `replaced_by_plan_id`

Purpose:

- preserve replaced future workouts instead of deleting them
- allow the calendar to ignore replaced items and only show active ones

### daily_logs

No major structural change is required. It remains the source of completion feedback.

### config.json

Replace the single AI config with a model list:

```json
{
  "keep": {
    "phone_number": "",
    "password": ""
  },
  "models": [
    {
      "key": "openai-gpt4o",
      "label": "OpenAI GPT-4o",
      "provider_name": "openai",
      "base_url": "https://api.openai.com/v1",
      "api_key": "",
      "model": "gpt-4o"
    }
  ]
}
```

## Plans Page Design

The plans page becomes the control panel for the current active plan.

It shows:

- active plan summary
- model selector
- generate button
- regenerate future incomplete workouts button
- readable markdown output
- weekly workout list

The page does not manage multiple concurrently active plans.

## Analysis Page Expansion

The analysis page keeps `Run` as the default data scope.

It should add the following visuals:

1. summary cards
2. monthly distance trend
3. weekly distance trend
4. pace distribution
5. distance distribution
6. running calendar heatmap
7. plan completion rate
8. approximate PR summary

Implementation direction:

- use `Chart.js` for line, bar, and distribution charts
- use a simple HTML grid or lightweight custom rendering for the heatmap

## Backend Responsibilities

### app.py

Must expose:

- month calendar summary endpoint
- day detail endpoint
- log submission endpoint
- settings save endpoint
- plan generate endpoint
- plan regenerate endpoint

### services/config_store.py

Must support:

- loading model list
- saving model list
- basic validation for required model fields

### services/planner.py

Must support:

- selecting one model configuration by key
- building context from activity history, recent logs, and current active plan
- generating a weekly plan
- regenerating only future incomplete workouts

### services/logs.py

Must support:

- saving logs from the modal
- updating linked workout status
- retrieving the latest log for a selected date

### services/analysis.py

Must support additional aggregation for:

- weekly series
- heatmap data
- completion-rate summaries

## Error Handling

- missing `openai` dependency: show a clear UI error that the environment lacks the package
- missing model configuration fields: block generation and show which fields are missing
- invalid selected model key: show a clear settings error
- Keep sync failure: preserve old data and show the failure
- AI parse failure: preserve markdown if available and show that structured parsing failed
- day without planned workout: modal still allows a standalone completion log

## Testing Strategy

Tests must be extended to cover:

1. model list config read/write
2. active-plan selection behavior
3. regeneration replacing only future incomplete workouts
4. month summary payload generation
5. day detail payload generation
6. modal log submission updating calendar-visible status
7. analysis chart dataset aggregation

External network and provider calls remain mocked.

## Success Criteria

This revision is complete when:

- the home page shows a month calendar
- clicking a date opens a modal with plan details and feedback form
- each date cell shows workout type and completion status
- settings can store multiple model configurations
- plan generation can choose one saved model
- only one active weekly plan exists at a time
- regeneration replaces only future incomplete workouts
- analysis shows noticeably richer chart coverage than the MVP

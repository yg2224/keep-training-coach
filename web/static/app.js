document.documentElement.dataset.app = "keep-training-coach";

function readJsonScript(id) {
  const node = document.getElementById(id);
  if (!node) return null;
  return JSON.parse(node.textContent);
}

const appCopy = readJsonScript("app-copy") || {};

function translateText(key, fallback, replacements = {}) {
  let text = appCopy[key] ?? fallback ?? key;
  Object.entries(replacements).forEach(([name, value]) => {
    text = text.replaceAll(`{${name}}`, String(value ?? ""));
  });
  return text;
}

function statusLabel(value) {
  if (!value) return "";
  return translateText(`status.${value}`, value);
}

function ensureToastStack() {
  let stack = document.getElementById("toast-stack");
  if (stack) return stack;
  stack = document.createElement("div");
  stack.id = "toast-stack";
  stack.className = "toast-stack";
  document.body.appendChild(stack);
  return stack;
}

function dismissToast(toast, immediate = false) {
  if (!toast) return;
  if (immediate) {
    toast.remove();
    return;
  }
  toast.classList.add("is-leaving");
  window.setTimeout(() => toast.remove(), 220);
}

function showToast(type, message, durationMs = 2600) {
  const stack = ensureToastStack();
  const toast = document.createElement("div");
  toast.className = `toast toast-${type}`;
  toast.textContent = message;
  stack.appendChild(toast);
  if (durationMs > 0) {
    window.setTimeout(() => dismissToast(toast), durationMs);
  }
  return toast;
}

let activePlanJobToast = null;
let activePlanJobToastId = null;

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

function renderSummaryItem(labelKey, fallback, value, suffix = "") {
  return `
    <div class="summary-item">
      <strong>${escapeHtml(translateText(labelKey, fallback))}</strong>
      <span>${escapeHtml(value || translateText("common.not_set", "Not set"))}${suffix}</span>
    </div>
  `;
}

function renderDayModalContent(payload) {
  const workout = payload.workout;
  const latestLog = payload.latest_log || {};
  const workoutHtml = workout
    ? `
      <div class="modal-section compact-modal-section">
        <div class="day-section-head">
          <h3>${escapeHtml(translateText("calendar.planned_summary", "Planned Summary"))}</h3>
          <span class="day-section-chip">${escapeHtml(workout.title)}</span>
        </div>
        <div class="day-summary-grid">
          ${renderSummaryItem("calendar.type", "Type", workout.workout_type)}
          ${renderSummaryItem("calendar.distance", "Distance", workout.target_distance_km, workout.target_distance_km ? " km" : "")}
          ${renderSummaryItem("calendar.duration", "Duration", workout.target_duration_min, workout.target_duration_min ? " min" : "")}
          ${renderSummaryItem("calendar.pace", "Pace", workout.target_pace)}
          <div class="summary-item summary-item-wide">
            <strong>${escapeHtml(translateText("calendar.notes", "Notes"))}</strong>
            <span>${escapeHtml(workout.notes || translateText("common.not_set", "Not set"))}</span>
          </div>
        </div>
      </div>
    `
    : `
      <div class="modal-section compact-modal-section">
        <h3>${escapeHtml(translateText("calendar.no_workout", "No planned workout"))}</h3>
        <p>${escapeHtml(translateText("calendar.no_workout_help", "You can still save a standalone log for this date."))}</p>
      </div>
    `;

  return `
    <div class="modal-section compact-modal-section modal-date-summary">
      <div class="day-section-head">
        <h2>${escapeHtml(payload.date)}</h2>
        <span class="calendar-day-status status-${escapeHtml(payload.completed || "planned")}">${escapeHtml(statusLabel(payload.completed || "planned"))}</span>
      </div>
      <p>${escapeHtml(translateText("calendar.current_status", "Current status"))}: ${escapeHtml(statusLabel(payload.completed || "planned"))}</p>
    </div>
    ${workoutHtml}
    <div class="modal-section compact-modal-section">
      <div class="day-section-head">
        <h3>${escapeHtml(translateText("calendar.log_form", "Completion Log"))}</h3>
      </div>
      <form id="day-log-form" class="stack-form compact-day-log-form">
        <input type="hidden" name="log_date" value="${escapeHtml(payload.date)}">
        <input type="hidden" name="plan_workout_id" value="${escapeHtml(workout?.id ?? "")}">
        <div class="compact-form-grid">
          <label>
            ${escapeHtml(translateText("calendar.completed", "Completed"))}
            <select name="completed" required>
              <option value="done" ${latestLog.completed === "done" ? "selected" : ""}>${escapeHtml(statusLabel("done"))}</option>
              <option value="partial" ${latestLog.completed === "partial" ? "selected" : ""}>${escapeHtml(statusLabel("partial"))}</option>
              <option value="skipped" ${latestLog.completed === "skipped" ? "selected" : ""}>${escapeHtml(statusLabel("skipped"))}</option>
            </select>
          </label>
          <label>
            ${escapeHtml(translateText("calendar.actual_distance", "Actual distance km"))}
            <input type="text" name="actual_distance_km" value="${escapeHtml(latestLog.actual_distance_km ?? "")}" placeholder="${escapeHtml(translateText("calendar.actual_distance_placeholder", "8.2"))}">
          </label>
          <label>
            ${escapeHtml(translateText("calendar.actual_duration", "Actual duration min"))}
            <input type="text" name="actual_duration_min" value="${escapeHtml(latestLog.actual_duration_min ?? "")}" placeholder="${escapeHtml(translateText("calendar.actual_duration_placeholder", "46"))}">
          </label>
          <label>
            ${escapeHtml(translateText("calendar.actual_pace", "Actual pace"))}
            <input type="text" name="actual_pace" value="${escapeHtml(latestLog.actual_pace ?? "")}" placeholder="${escapeHtml(translateText("calendar.actual_pace_placeholder", "5:36 /km"))}">
          </label>
          <label>
            ${escapeHtml(translateText("calendar.average_heartrate", "Average heartrate"))}
            <input type="text" name="average_heartrate" value="${escapeHtml(latestLog.average_heartrate ?? "")}" placeholder="${escapeHtml(translateText("calendar.average_heartrate_placeholder", "151"))}">
          </label>
          <label>
            ${escapeHtml(translateText("calendar.mood_score", "Mood score"))}
            <input type="text" name="mood_score" value="${escapeHtml(latestLog.mood_score ?? "")}" placeholder="${escapeHtml(translateText("calendar.mood_score_placeholder", "4 (1-5)"))}">
          </label>
          <label class="field-span-full">
            ${escapeHtml(translateText("calendar.notes", "Notes"))}
            <textarea name="notes" rows="1" placeholder="${escapeHtml(translateText("calendar.notes_placeholder", "Felt smooth early, but the last 2 km got heavy."))}">${escapeHtml(latestLog.notes ?? "")}</textarea>
          </label>
        </div>
      </form>
      <div class="compact-form-actions field-span-full">
        <button type="button" class="ghost-button" data-close-day-modal onclick="document.getElementById('day-modal')?.close()">${escapeHtml(translateText("common.close", "Close"))}</button>
        <button type="submit" form="day-log-form">${escapeHtml(translateText("calendar.save_log", "Save Log"))}</button>
      </div>
    </div>
  `;
}

function updateCalendarCell(day) {
  const cell = document.querySelector(`.calendar-day[data-date="${day.date}"]`);
  if (!cell) return;
  const typeNode = cell.querySelector(".calendar-day-type");
  const statusNode = cell.querySelector(".calendar-day-status");
  if (day.workout?.workout_type) {
    if (typeNode) {
      typeNode.textContent = day.workout.workout_type;
    } else {
      const span = document.createElement("span");
      span.className = "calendar-day-type";
      span.textContent = day.workout.workout_type;
      cell.appendChild(span);
    }
  }
  if (day.completed) {
    if (statusNode) {
      statusNode.textContent = statusLabel(day.completed);
      statusNode.className = `calendar-day-status status-${day.completed}`;
    } else {
      const span = document.createElement("span");
      span.className = `calendar-day-status status-${day.completed}`;
      span.textContent = statusLabel(day.completed);
      cell.appendChild(span);
    }
  }
}

function bindCalendarModal() {
  const root = document.getElementById("calendar-root");
  const modal = document.getElementById("day-modal");
  const content = document.getElementById("day-modal-content");
  if (!root || !modal || !content) return;

  function bindDayLogForm() {
    const form = document.getElementById("day-log-form");
    if (!form) return;
    const closeButton = document.querySelector("[data-close-day-modal]");
    if (closeButton) {
      closeButton.addEventListener("click", (event) => {
        event.preventDefault();
        modal.close();
      });
    }
    form.addEventListener("submit", async (submitEvent) => {
      submitEvent.preventDefault();
      const formData = new FormData(form);
      const saveResponse = await fetch(root.dataset.logUrl, {
        method: "POST",
        body: formData,
      });
      const savePayload = await saveResponse.json();
      updateCalendarCell(savePayload.day);
      content.innerHTML = renderDayModalContent({
        date: savePayload.day.date,
        workout: savePayload.day.workout,
        latest_log: savePayload.day.latest_log,
        completed: savePayload.day.completed,
      });
      bindDayLogForm();
    }, { once: true });
  }

  root.addEventListener("click", async (event) => {
    const button = event.target.closest(".calendar-day[data-date]");
    if (!button) return;
    const response = await fetch(`${root.dataset.dayUrlBase}${button.dataset.date}`);
    const payload = await response.json();
    content.innerHTML = renderDayModalContent(payload);
    modal.showModal();
    bindDayLogForm();
  });
}

function bindModelSettings() {
  const picker = document.getElementById("model-picker");
  const hiddenFields = document.getElementById("model-hidden-fields");
  const summary = document.getElementById("model-picker-summary");
  const preview = document.getElementById("model-preview");
  const emptyState = document.getElementById("model-empty-state");
  const modal = document.getElementById("model-editor-modal");
  const editorForm = document.getElementById("model-editor-form");
  const title = document.getElementById("model-editor-title");
  const addButton = document.getElementById("add-model-button");
  const editButton = document.getElementById("edit-model-button");
  const deleteButton = document.getElementById("delete-model-button");
  const cancelButton = document.getElementById("cancel-model-button");
  if (
    !picker ||
    !hiddenFields ||
    !summary ||
    !preview ||
    !emptyState ||
    !modal ||
    !editorForm ||
    !title ||
    !addButton ||
    !editButton ||
    !deleteButton ||
    !cancelButton
  ) {
    return;
  }

  const fields = {
    key: document.getElementById("editor-model-key"),
    label: document.getElementById("editor-model-label"),
    provider_name: document.getElementById("editor-model-provider-name"),
    base_url: document.getElementById("editor-model-base-url"),
    api_key: document.getElementById("editor-model-api-key"),
    model: document.getElementById("editor-model-name"),
  };
  let models = (readJsonScript("model-editor-data") || []).map((item) => ({
    key: item.key || "",
    label: item.label || "",
    provider_name: item.provider_name || "",
    base_url: item.base_url || "",
    api_key: item.api_key || "",
    model: item.model || "",
  }));
  let selectedIndex = models.length ? 0 : -1;
  let editingIndex = null;

  function createHiddenInput(name, value) {
    const input = document.createElement("input");
    input.type = "hidden";
    input.name = name;
    input.value = value ?? "";
    return input;
  }

  function syncHiddenFields() {
    hiddenFields.innerHTML = "";
    models.forEach((item) => {
      hiddenFields.appendChild(createHiddenInput("model_key", item.key));
      hiddenFields.appendChild(createHiddenInput("model_label", item.label));
      hiddenFields.appendChild(
        createHiddenInput("model_provider_name", item.provider_name),
      );
      hiddenFields.appendChild(createHiddenInput("model_base_url", item.base_url));
      hiddenFields.appendChild(createHiddenInput("model_api_key", item.api_key));
      hiddenFields.appendChild(createHiddenInput("model_name", item.model));
    });
  }

  function readEditorModel() {
    return {
      key: fields.key.value.trim(),
      label: fields.label.value.trim(),
      provider_name: fields.provider_name.value.trim(),
      base_url: fields.base_url.value.trim(),
      api_key: fields.api_key.value.trim(),
      model: fields.model.value.trim(),
    };
  }

  function writeEditorModel(model) {
    fields.key.value = model.key || "";
    fields.label.value = model.label || "";
    fields.provider_name.value = model.provider_name || "";
    fields.base_url.value = model.base_url || "";
    fields.api_key.value = model.api_key || "";
    fields.model.value = model.model || "";
  }

  function buildModelSummary(model) {
    return `${model.label || model.key || translateText("settings.untitled", "Untitled")} - ${model.provider_name || translateText("settings.no_provider", "No provider")} - ${model.model || translateText("settings.no_model", "No model")}`;
  }

  function maskApiKey(apiKey) {
    if (!apiKey) return translateText("common.not_set", "Not set");
    if (apiKey.length <= 6) return apiKey;
    return `${apiKey.slice(0, 3)}***${apiKey.slice(-2)}`;
  }

  function renderModelPreview() {
    if (selectedIndex < 0 || !models.length) {
      preview.innerHTML = `
        <div class="muted-text">
          ${escapeHtml(translateText("settings.preview_hint", "Select or create a model to review its provider details here."))}
        </div>
      `;
      return;
    }

    const model = models[selectedIndex];
    preview.innerHTML = `
      <div>
        <h3>${escapeHtml(model.label || model.key || translateText("settings.untitled", "Untitled"))}</h3>
        <p class="muted-text">${escapeHtml(translateText("settings.entry_usage_hint", "This entry will appear in plan generation and regeneration dropdowns."))}</p>
      </div>
      <div class="model-preview-grid">
        <div class="model-preview-item">
          <strong>${escapeHtml(translateText("settings.preview_key", "Key"))}</strong>
          <span>${escapeHtml(model.key || translateText("common.not_set", "Not set"))}</span>
        </div>
        <div class="model-preview-item">
          <strong>${escapeHtml(translateText("settings.preview_provider", "Provider"))}</strong>
          <span>${escapeHtml(model.provider_name || translateText("common.not_set", "Not set"))}</span>
        </div>
        <div class="model-preview-item">
          <strong>${escapeHtml(translateText("settings.preview_model", "Model"))}</strong>
          <span>${escapeHtml(model.model || translateText("common.not_set", "Not set"))}</span>
        </div>
        <div class="model-preview-item">
          <strong>${escapeHtml(translateText("settings.preview_base_url", "Base URL"))}</strong>
          <span>${escapeHtml(model.base_url || translateText("common.not_set", "Not set"))}</span>
        </div>
        <div class="model-preview-item">
          <strong>${escapeHtml(translateText("settings.preview_api_key", "API Key"))}</strong>
          <span>${escapeHtml(maskApiKey(model.api_key))}</span>
        </div>
      </div>
    `;
  }

  function renderModelPicker() {
    picker.innerHTML = "";
    if (!models.length) {
      const option = document.createElement("option");
      option.value = "";
      option.textContent = translateText("settings.no_saved_model_option", "No saved model");
      picker.appendChild(option);
      picker.disabled = true;
      selectedIndex = -1;
      summary.textContent = translateText("settings.first_model_hint", "Use Add Model to create the first model config.");
      emptyState.hidden = false;
      editButton.disabled = true;
      deleteButton.disabled = true;
      renderModelPreview();
      syncHiddenFields();
      return;
    }

    picker.disabled = false;
    if (selectedIndex < 0 || selectedIndex >= models.length) {
      selectedIndex = 0;
    }
    models.forEach((model, index) => {
      const option = document.createElement("option");
      option.value = String(index);
      option.textContent = buildModelSummary(model);
      picker.appendChild(option);
    });
    picker.value = String(selectedIndex);
    summary.textContent = buildModelSummary(models[selectedIndex]);
    emptyState.hidden = true;
    editButton.disabled = false;
    deleteButton.disabled = false;
    renderModelPreview();
    syncHiddenFields();
  }

  function openEditor(index) {
    editingIndex = index;
    if (index === null) {
      title.textContent = translateText("settings.add_model_title", "Add Model");
      writeEditorModel({
        key: "",
        label: "",
        provider_name: "",
        base_url: "",
        api_key: "",
        model: "",
      });
    } else {
      title.textContent = translateText("settings.edit_model_title", "Edit Model");
      writeEditorModel(models[index]);
    }
    modal.showModal();
  }

  picker.addEventListener("change", () => {
    selectedIndex = Number(picker.value);
    renderModelPicker();
  });

  addButton.addEventListener("click", () => openEditor(null));

  editButton.addEventListener("click", () => {
    if (selectedIndex < 0) return;
    openEditor(selectedIndex);
  });

  deleteButton.addEventListener("click", () => {
    if (selectedIndex < 0) return;
    if (!window.confirm(translateText("settings.delete_confirm", "Delete the selected model config?"))) {
      return;
    }
    models.splice(selectedIndex, 1);
    if (selectedIndex >= models.length) {
      selectedIndex = models.length - 1;
    }
    renderModelPicker();
  });

  cancelButton.addEventListener("click", () => modal.close());

  editorForm.addEventListener("submit", (event) => {
    event.preventDefault();
    const model = readEditorModel();
    if (editingIndex === null) {
      models.push(model);
      selectedIndex = models.length - 1;
    } else {
      models[editingIndex] = model;
      selectedIndex = editingIndex;
    }
    renderModelPicker();
    modal.close();
  });

  renderModelPicker();
}

function bindPlanTypeForms() {
  const forms = document.querySelectorAll("[data-plan-type-form]");
  forms.forEach((form) => {
    const select = form.querySelector("[data-plan-type-select]");
    const fields = form.querySelectorAll("[data-plan-field]");
    const notice = form.querySelector("[data-plan-type-notice]");
    if (!select || !fields.length) return;

    const updateFields = () => {
      const planType = select.value;
      if (notice) {
        notice.textContent = planType === "race_goal"
          ? translateText(
            "plans.race_goal_hint",
            "Race goal plan is selected. Only fill race distance, race date, race pace, and goal notes. Weekly target fields are not needed.",
          )
          : translateText(
            "plans.rolling_week_hint",
            "Rolling next week is selected. Only fill target distance, target pace, and goal notes. Race fields are not needed.",
          );
      }
      fields.forEach((field) => {
        const modes = (field.dataset.planModes || "")
          .split(",")
          .map((item) => item.trim())
          .filter(Boolean);
        const visible = modes.includes(planType);
        field.hidden = !visible;
        field
          .querySelectorAll("input, select, textarea")
          .forEach((input) => {
            input.disabled = !visible;
          });
      });
    };

    select.addEventListener("change", updateFields);
    updateFields();
  });
}

function replacePlansResults(html) {
  const current = document.getElementById("plans-results");
  if (!current || !html) return;
  const nextDocument = new DOMParser().parseFromString(html, "text/html");
  const next = nextDocument.getElementById("plans-results");
  if (!next) return;
  current.replaceWith(next);
}

const PLAN_JOB_SEEN_TERMINAL_KEY = "keep-training-coach.plan-job-seen-terminal";
let lastPlanJobSnapshot = null;
let lastPlansResultsSignature = null;

function getPlanJobStatusUrl() {
  return document.body?.dataset.planJobStatusUrl || "";
}

function getPlansResultsUrl() {
  const statusNode = document.getElementById("plans-job-status");
  return statusNode?.dataset.plansResultsUrl || "";
}

function getPlanJobBusyMessage(job) {
  if (job?.job_type === "regenerate") {
    return translateText("plans.regenerate_button_busy", "Regenerating...");
  }
  return translateText("plans.generate_button_busy", "Generating...");
}

function getPlanJobSuccessMessage(job) {
  if (job?.job_type === "regenerate") {
    return translateText("plans.regenerate_success", "Future workouts regenerated.");
  }
  return translateText("plans.generate_success", "Training plan generated.");
}

function getPlanJobErrorMessage(job) {
  return job?.error_message || translateText("plans.job_failed", "Plan job failed.");
}

function showPersistentPlanJobToast(job) {
  const message = getPlanJobBusyMessage(job);
  if (activePlanJobToast && activePlanJobToastId === job.id) {
    activePlanJobToast.textContent = message;
    return;
  }
  clearPersistentPlanJobToast();
  activePlanJobToast = showToast("info", message, 0);
  activePlanJobToastId = job.id;
}

function clearPersistentPlanJobToast() {
  if (!activePlanJobToast) return;
  dismissToast(activePlanJobToast, true);
  activePlanJobToast = null;
  activePlanJobToastId = null;
}

function updatePlansJobStatus(job) {
  const statusNode = document.getElementById("plans-job-status");
  if (!statusNode) return;
  const isActive = job && (job.status === "queued" || job.status === "running");
  statusNode.hidden = !isActive;
  statusNode.textContent = isActive ? getPlanJobBusyMessage(job) : "";
}

function getPlanJobSignature(job) {
  if (!job) return "";
  return `${job.id}:${job.status}:${job.finished_at || ""}`;
}

async function refreshPlansResultsFromServer() {
  const current = document.getElementById("plans-results");
  const url = getPlansResultsUrl();
  if (!current || !url) return;
  const response = await fetch(url, {
    headers: {
      Accept: "text/html",
    },
  });
  if (!response.ok) return;
  replacePlansResults(await response.text());
}

async function syncPlanJobUi(job) {
  updatePlansJobStatus(job);
  if (job && (job.status === "queued" || job.status === "running")) {
    showPersistentPlanJobToast(job);
    return;
  }

  clearPersistentPlanJobToast();
  if (!job || !job.is_terminal) {
    return;
  }

  const signature = getPlanJobSignature(job);
  if (job.status === "succeeded" && signature !== lastPlansResultsSignature) {
    lastPlansResultsSignature = signature;
    await refreshPlansResultsFromServer();
  }

  if (window.localStorage.getItem(PLAN_JOB_SEEN_TERMINAL_KEY) === signature) {
    return;
  }

  window.localStorage.setItem(PLAN_JOB_SEEN_TERMINAL_KEY, signature);
  showToast(
    job.status === "succeeded" ? "success" : "error",
    job.status === "succeeded" ? getPlanJobSuccessMessage(job) : getPlanJobErrorMessage(job),
    10000,
  );
}

async function pollPlanJobStatus() {
  const url = getPlanJobStatusUrl();
  if (!url) return;
  try {
    const response = await fetch(url, {
      headers: {
        Accept: "application/json",
      },
    });
    if (!response.ok) return;
    const payload = await response.json();
    const snapshot = JSON.stringify(payload.job);
    if (snapshot === lastPlanJobSnapshot) {
      return;
    }
    lastPlanJobSnapshot = snapshot;
    await syncPlanJobUi(payload.job);
  } catch (error) {
    // Swallow polling errors; the next poll will retry.
  }
}

function startPlanJobPolling() {
  const url = getPlanJobStatusUrl();
  if (!url) return;
  pollPlanJobStatus();
  window.setInterval(pollPlanJobStatus, 2500);
}

function bindPlanAsyncForms() {
  const forms = document.querySelectorAll("[data-plan-async-form]");
  forms.forEach((form) => {
    form.addEventListener("submit", async (event) => {
      event.preventDefault();
      const submitButton = event.submitter || form.querySelector('button[type="submit"]');
      if (!submitButton) return;

      const idleText = submitButton.dataset.idleText || submitButton.textContent.trim();
      const busyText = submitButton.dataset.busyText || idleText;
      submitButton.disabled = true;
      submitButton.textContent = busyText;
      showToast("info", busyText);

      try {
        const response = await fetch(form.action, {
          method: form.method || "POST",
          headers: {
            "Accept": "application/json",
            "X-Requested-With": "XMLHttpRequest",
          },
          body: new FormData(form),
        });
        const payload = await response.json();
        if (!response.ok || payload.status !== "accepted") {
          throw new Error(payload.message || `Request failed with ${response.status}`);
        }
        lastPlanJobSnapshot = JSON.stringify(payload.job);
        await syncPlanJobUi(payload.job);
      } catch (error) {
        showToast("error", error.message || "Request failed", 10000);
      } finally {
        submitButton.disabled = false;
        submitButton.textContent = idleText;
      }
    });
  });
}

const chartRegistry = new Map();

function createDatasetChart(canvasId, config) {
  const canvas = document.getElementById(canvasId);
  if (!canvas || typeof Chart === "undefined") return;
  const existingChart = chartRegistry.get(canvasId);
  if (existingChart) {
    existingChart.destroy();
  }
  chartRegistry.set(canvasId, new Chart(canvas, config));
}

function bindAnalysisCharts() {
  const payload = readJsonScript("analysis-data");
  if (!payload || typeof Chart === "undefined") return;

  const distanceLabel = translateText("analysis.distance_dataset", "Distance (km)");
  const runsLabel = translateText("analysis.runs_dataset", "Runs");
  const sharedOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        display: false,
      },
    },
  };

  createDatasetChart("monthly-chart", {
    type: "bar",
    data: {
      labels: payload.monthly.map((item) => item.month),
      datasets: [
        {
          label: distanceLabel,
          data: payload.monthly.map((item) => item.distance),
          backgroundColor: "#c9733d",
          borderRadius: 10,
        },
      ],
    },
    options: sharedOptions,
  });

  createDatasetChart("weekly-chart", {
    type: "line",
    data: {
      labels: payload.weekly.map((item) => item.week_start),
      datasets: [
        {
          label: distanceLabel,
          data: payload.weekly.map((item) => item.distance),
          borderColor: "#1f6f78",
          backgroundColor: "rgba(31, 111, 120, 0.18)",
          tension: 0.28,
          fill: true,
        },
      ],
    },
    options: sharedOptions,
  });

  createDatasetChart("pace-chart", {
    type: "bar",
    data: {
      labels: payload.pace.map((item) => item.label),
      datasets: [
        {
          label: runsLabel,
          data: payload.pace.map((item) => item.value),
          backgroundColor: "#efb366",
          borderRadius: 10,
        },
      ],
    },
    options: sharedOptions,
  });

  createDatasetChart("distance-chart", {
    type: "doughnut",
    data: {
      labels: payload.distance.map((item) => item.label),
      datasets: [
        {
          label: runsLabel,
          data: payload.distance.map((item) => item.value),
          backgroundColor: ["#1f6f78", "#5c9ead", "#efb366", "#c9733d"],
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
    },
  });
}

bindCalendarModal();
bindModelSettings();
bindPlanTypeForms();
bindPlanAsyncForms();
startPlanJobPolling();
bindAnalysisCharts();

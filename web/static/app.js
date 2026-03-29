document.documentElement.dataset.app = "keep-training-coach";

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

function renderDayModalContent(payload) {
  const workout = payload.workout;
  const latestLog = payload.latest_log || {};
  const workoutHtml = workout
    ? `
      <div class="modal-section">
        <h3>${escapeHtml(workout.title)}</h3>
        <p>Type: ${escapeHtml(workout.workout_type)}</p>
        <p>Distance: ${escapeHtml(workout.target_distance_km ?? "")} km</p>
        <p>Duration: ${escapeHtml(workout.target_duration_min ?? "")} min</p>
        <p>Pace: ${escapeHtml(workout.target_pace ?? "")}</p>
        <p>Notes: ${escapeHtml(workout.notes ?? "")}</p>
      </div>
    `
    : `
      <div class="modal-section">
        <h3>No planned workout</h3>
        <p>You can still save a standalone log for this date.</p>
      </div>
    `;

  return `
    <div class="modal-section">
      <h2>${escapeHtml(payload.date)}</h2>
      <p>Current status: ${escapeHtml(payload.completed || "planned")}</p>
    </div>
    ${workoutHtml}
    <form id="day-log-form" class="stack-form">
      <input type="hidden" name="log_date" value="${escapeHtml(payload.date)}">
      <input type="hidden" name="plan_workout_id" value="${escapeHtml(workout?.id ?? "")}">
      <label>
        Completed
        <select name="completed" required>
          <option value="done" ${latestLog.completed === "done" ? "selected" : ""}>done</option>
          <option value="partial" ${latestLog.completed === "partial" ? "selected" : ""}>partial</option>
          <option value="skipped" ${latestLog.completed === "skipped" ? "selected" : ""}>skipped</option>
        </select>
      </label>
      <label>
        Actual distance km
        <input type="text" name="actual_distance_km" value="${escapeHtml(latestLog.actual_distance_km ?? "")}">
      </label>
      <label>
        Actual duration min
        <input type="text" name="actual_duration_min" value="${escapeHtml(latestLog.actual_duration_min ?? "")}">
      </label>
      <label>
        Actual pace
        <input type="text" name="actual_pace" value="${escapeHtml(latestLog.actual_pace ?? "")}">
      </label>
      <label>
        Average heartrate
        <input type="text" name="average_heartrate" value="${escapeHtml(latestLog.average_heartrate ?? "")}">
      </label>
      <label>
        Fatigue score
        <input type="text" name="fatigue_score" value="${escapeHtml(latestLog.fatigue_score ?? "")}">
      </label>
      <label>
        Mood score
        <input type="text" name="mood_score" value="${escapeHtml(latestLog.mood_score ?? "")}">
      </label>
      <label>
        Notes
        <textarea name="notes" rows="3">${escapeHtml(latestLog.notes ?? "")}</textarea>
      </label>
      <button type="submit">Save Log</button>
    </form>
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
      statusNode.textContent = day.completed;
      statusNode.className = `calendar-day-status status-${day.completed}`;
    } else {
      const span = document.createElement("span");
      span.className = `calendar-day-status status-${day.completed}`;
      span.textContent = day.completed;
      cell.appendChild(span);
    }
  }
}

function bindCalendarModal() {
  const root = document.getElementById("calendar-root");
  const modal = document.getElementById("day-modal");
  const content = document.getElementById("day-modal-content");
  if (!root || !modal || !content) return;

  root.addEventListener("click", async (event) => {
    const button = event.target.closest(".calendar-day[data-date]");
    if (!button) return;
    const response = await fetch(`${root.dataset.dayUrlBase}${button.dataset.date}`);
    const payload = await response.json();
    content.innerHTML = renderDayModalContent(payload);
    modal.showModal();

    const form = document.getElementById("day-log-form");
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
    }, { once: true });
  });
}

function readJsonScript(id) {
  const node = document.getElementById(id);
  if (!node) return null;
  return JSON.parse(node.textContent);
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
    return `${model.label || model.key || "Untitled"} - ${model.provider_name || "No provider"} - ${model.model || "No model"}`;
  }

  function maskApiKey(apiKey) {
    if (!apiKey) return "Not set";
    if (apiKey.length <= 6) return apiKey;
    return `${apiKey.slice(0, 3)}***${apiKey.slice(-2)}`;
  }

  function renderModelPreview() {
    if (selectedIndex < 0 || !models.length) {
      preview.innerHTML = `
        <div class="muted-text">
          Select or create a model to review its provider details here.
        </div>
      `;
      return;
    }

    const model = models[selectedIndex];
    preview.innerHTML = `
      <div>
        <h3>${escapeHtml(model.label || model.key || "Untitled")}</h3>
        <p class="muted-text">This entry will appear in plan generation and regeneration dropdowns.</p>
      </div>
      <div class="model-preview-grid">
        <div class="model-preview-item">
          <strong>Key</strong>
          <span>${escapeHtml(model.key || "Not set")}</span>
        </div>
        <div class="model-preview-item">
          <strong>Provider</strong>
          <span>${escapeHtml(model.provider_name || "Not set")}</span>
        </div>
        <div class="model-preview-item">
          <strong>Model</strong>
          <span>${escapeHtml(model.model || "Not set")}</span>
        </div>
        <div class="model-preview-item">
          <strong>Base URL</strong>
          <span>${escapeHtml(model.base_url || "Not set")}</span>
        </div>
        <div class="model-preview-item">
          <strong>API Key</strong>
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
      option.textContent = "No saved model";
      picker.appendChild(option);
      picker.disabled = true;
      selectedIndex = -1;
      summary.textContent = "Use Add Model to create the first model config.";
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
      title.textContent = "Add Model";
      writeEditorModel({
        key: "",
        label: "",
        provider_name: "",
        base_url: "",
        api_key: "",
        model: "",
      });
    } else {
      title.textContent = "Edit Model";
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
    if (!window.confirm("Delete the selected model config?")) {
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
    if (!select || !fields.length) return;

    const updateFields = () => {
      const planType = select.value;
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
          label: "Distance (km)",
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
          label: "Distance (km)",
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
          label: "Runs",
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
          label: "Runs",
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
bindAnalysisCharts();

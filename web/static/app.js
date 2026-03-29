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

function bindModelSettings() {
  const addButton = document.getElementById("add-model-row");
  const list = document.getElementById("model-config-list");
  if (!addButton || !list) return;
  addButton.addEventListener("click", () => {
    const wrapper = document.createElement("div");
    wrapper.className = "model-config-card";
    wrapper.innerHTML = `
      <label>Model key<input type="text" name="model_key"></label>
      <label>Label<input type="text" name="model_label"></label>
      <label>Provider name<input type="text" name="model_provider_name"></label>
      <label>Base URL<input type="text" name="model_base_url"></label>
      <label>API key<input type="password" name="model_api_key"></label>
      <label>Model<input type="text" name="model_name"></label>
    `;
    list.appendChild(wrapper);
  });
}

function readJsonScript(id) {
  const node = document.getElementById(id);
  if (!node) return null;
  return JSON.parse(node.textContent);
}

function createDatasetChart(canvasId, config) {
  const canvas = document.getElementById(canvasId);
  if (!canvas || typeof Chart === "undefined") return;
  new Chart(canvas, config);
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
bindAnalysisCharts();

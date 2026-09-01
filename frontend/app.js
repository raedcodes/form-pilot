let sessionId = crypto.randomUUID();

const chatEl = document.getElementById("chat");
const composerEl = document.getElementById("composer");
const messageEl = document.getElementById("message");
const previewEmptyEl = document.getElementById("preview-empty");
const previewEl = document.getElementById("preview");
const previewContentEl = document.getElementById("preview-content");
const qualityReportEl = document.getElementById("quality-report");
const resultEl = document.getElementById("result");
const errorEl = document.getElementById("error");
const startOverBtn = document.getElementById("start-over");
const languageSelect = document.getElementById("language-select");
const toneSelect = document.getElementById("tone-select");
const undoBtn = document.getElementById("undo-btn");
const redoBtn = document.getElementById("redo-btn");
const qualityBtn = document.getElementById("quality-btn");
const confirmBtn = document.getElementById("confirm-btn");
const cancelBtn = document.getElementById("cancel-btn");
const toastContainer = document.getElementById("toast-container");
const dialogEl = document.getElementById("confirm-dialog");
const dialogMessageEl = document.getElementById("dialog-message");
const dialogYesBtn = document.getElementById("dialog-yes");
const dialogNoBtn = document.getElementById("dialog-no");
const sendBtn = composerEl.querySelector("button");

const TYPE_LABELS = {
  SHORT_ANSWER: "Short answer",
  PARAGRAPH: "Paragraph",
  MULTIPLE_CHOICE: "Multiple choice",
  CHECKBOXES: "Checkboxes",
  DROPDOWN: "Dropdown",
  LINEAR_SCALE: "Rating scale",
};
const CHOICE_TYPES = new Set(["MULTIPLE_CHOICE", "CHECKBOXES", "DROPDOWN"]);

const DEFAULT_PLACEHOLDER = messageEl.placeholder;
const EDIT_PLACEHOLDER = 'e.g. "make question 3 optional" or "remove the email question"';

let currentPlan = null;
let currentAssumptions = [];
let canUndo = false;
let canRedo = false;

// ---------- small utilities ----------

function debounce(fn, delay) {
  let timer = null;
  return (...args) => {
    clearTimeout(timer);
    timer = setTimeout(() => fn(...args), delay);
  };
}

function showToast(text) {
  const el = document.createElement("div");
  el.className = "toast";
  el.textContent = text;
  toastContainer.appendChild(el);
  setTimeout(() => el.remove(), 2500);
}

function confirmDialog(message) {
  return new Promise((resolve) => {
    dialogMessageEl.textContent = message;
    dialogEl.classList.remove("hidden");
    const cleanup = (result) => {
      dialogEl.classList.add("hidden");
      dialogYesBtn.onclick = null;
      dialogNoBtn.onclick = null;
      resolve(result);
    };
    dialogYesBtn.onclick = () => cleanup(true);
    dialogNoBtn.onclick = () => cleanup(false);
  });
}

// ---------- chat transcript ----------

function addMessage(text, who) {
  const wrap = document.createElement("div");
  wrap.className = `msg-wrap ${who}`;

  if (who === "agent") {
    const label = document.createElement("div");
    label.className = "msg-label";
    label.textContent = "Form Pilot";
    wrap.appendChild(label);
  }

  const bubble = document.createElement("div");
  bubble.className = `msg ${who}`;
  bubble.textContent = text;
  wrap.appendChild(bubble);

  chatEl.appendChild(wrap);
  wrap.scrollIntoView({ behavior: "smooth", block: "end" });
  return wrap;
}

function addLoadingMessage(text) {
  const wrap = addMessage(text, "agent");
  wrap.querySelector(".msg").classList.add("loading");
  return wrap;
}

function showError(text, retry) {
  errorEl.innerHTML = "";

  const msg = document.createElement("span");
  msg.textContent = text;
  errorEl.appendChild(msg);

  if (retry) {
    const retryBtn = document.createElement("button");
    retryBtn.textContent = "Retry";
    retryBtn.onclick = () => {
      clearError();
      retry();
    };
    errorEl.appendChild(retryBtn);
  }

  errorEl.classList.remove("hidden");
}

function clearError() {
  errorEl.classList.add("hidden");
  errorEl.innerHTML = "";
}

// ---------- server sync ----------

const debouncedSync = debounce(() => syncPlanToServer(), 700);

async function syncPlanToServer() {
  try {
    const res = await fetch("/plan", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ session_id: sessionId, plan: currentPlan }),
    });
    if (!res.ok) {
      const body = await res.json().catch(() => ({}));
      throw new Error(body.detail || `Request failed (${res.status})`);
    }
    const data = await res.json();
    canUndo = data.can_undo;
    canRedo = data.can_redo;
    updateUndoRedoButtons();
  } catch (err) {
    showToast(`Couldn't save that change: ${err.message}`);
  }
}

function updateUndoRedoButtons() {
  undoBtn.disabled = !canUndo;
  redoBtn.disabled = !canRedo;
}

// ---------- preview rendering ----------

function hideQualityReport() {
  qualityReportEl.classList.add("hidden");
  qualityReportEl.innerHTML = "";
}

function renderPreview(plan, assumptions) {
  currentPlan = plan;
  if (assumptions) currentAssumptions = assumptions;

  previewEmptyEl.classList.add("hidden");
  previewEl.classList.remove("hidden");
  previewContentEl.innerHTML = "";
  previewContentEl.dir = languageSelect.value === "Arabic" ? "rtl" : "ltr";
  hideQualityReport();
  updateUndoRedoButtons();

  const titleInput = document.createElement("input");
  titleInput.className = "form-title-input";
  titleInput.value = plan.title;
  titleInput.addEventListener("input", () => {
    currentPlan.title = titleInput.value;
    debouncedSync();
  });
  previewContentEl.appendChild(titleInput);

  const descInput = document.createElement("input");
  descInput.className = "form-desc-input";
  descInput.value = plan.description || "";
  descInput.placeholder = "Form description (optional)";
  descInput.addEventListener("input", () => {
    currentPlan.description = descInput.value;
    debouncedSync();
  });
  previewContentEl.appendChild(descInput);

  if (currentAssumptions && currentAssumptions.length) {
    const box = document.createElement("div");
    box.className = "assumptions";

    const label = document.createElement("div");
    label.className = "assumptions-label";
    label.textContent = "Assumptions made — double-check these:";
    box.appendChild(label);

    const list = document.createElement("ul");
    for (const a of currentAssumptions) {
      const li = document.createElement("li");
      li.textContent = a;
      list.appendChild(li);
    }
    box.appendChild(list);
    previewContentEl.appendChild(box);
  }

  plan.questions.forEach((q, i) => previewContentEl.appendChild(renderQuestionCard(q, i)));

  messageEl.placeholder = EDIT_PLACEHOLDER;
}

function renderQuestionCard(q, i) {
  const card = document.createElement("div");
  card.className = "q-card";

  // header: number, title, actions
  const header = document.createElement("div");
  header.className = "q-card-header";

  const number = document.createElement("span");
  number.className = "q-number";
  number.textContent = `${i + 1}.`;
  header.appendChild(number);

  const titleInput = document.createElement("input");
  titleInput.className = "q-title-input";
  titleInput.value = q.title;
  titleInput.addEventListener("input", () => {
    currentPlan.questions[i].title = titleInput.value;
    debouncedSync();
  });
  header.appendChild(titleInput);

  const actions = document.createElement("div");
  actions.className = "q-card-actions";

  const upBtn = document.createElement("button");
  upBtn.className = "icon-btn";
  upBtn.type = "button";
  upBtn.title = "Move up";
  upBtn.textContent = "↑";
  upBtn.disabled = i === 0;
  upBtn.onclick = () => moveQuestion(i, -1);
  actions.appendChild(upBtn);

  const downBtn = document.createElement("button");
  downBtn.className = "icon-btn";
  downBtn.type = "button";
  downBtn.title = "Move down";
  downBtn.textContent = "↓";
  downBtn.disabled = i === currentPlan.questions.length - 1;
  downBtn.onclick = () => moveQuestion(i, 1);
  actions.appendChild(downBtn);

  const dupBtn = document.createElement("button");
  dupBtn.className = "icon-btn";
  dupBtn.type = "button";
  dupBtn.title = "Duplicate";
  dupBtn.textContent = "⧉";
  dupBtn.onclick = () => duplicateQuestion(i);
  actions.appendChild(dupBtn);

  const delBtn = document.createElement("button");
  delBtn.className = "icon-btn danger";
  delBtn.type = "button";
  delBtn.title = "Delete";
  delBtn.textContent = "🗑";
  delBtn.onclick = () => deleteQuestion(i);
  actions.appendChild(delBtn);

  header.appendChild(actions);
  card.appendChild(header);

  // body: type select + required checkbox
  const body = document.createElement("div");
  body.className = "q-card-body";

  const typeSelect = document.createElement("select");
  typeSelect.className = "q-type-select";
  for (const [value, label] of Object.entries(TYPE_LABELS)) {
    const opt = document.createElement("option");
    opt.value = value;
    opt.textContent = label;
    if (value === q.type) opt.selected = true;
    typeSelect.appendChild(opt);
  }
  typeSelect.addEventListener("change", () => changeQuestionType(i, typeSelect.value));
  body.appendChild(typeSelect);

  const requiredLabel = document.createElement("label");
  requiredLabel.className = "q-required";
  const requiredCheckbox = document.createElement("input");
  requiredCheckbox.type = "checkbox";
  requiredCheckbox.checked = q.required;
  requiredCheckbox.addEventListener("change", () => {
    currentPlan.questions[i].required = requiredCheckbox.checked;
    syncPlanToServer();
  });
  requiredLabel.appendChild(requiredCheckbox);
  requiredLabel.appendChild(document.createTextNode("Required"));
  body.appendChild(requiredLabel);

  card.appendChild(body);

  // options (choice types) or scale (linear scale)
  if (CHOICE_TYPES.has(q.type)) {
    card.appendChild(renderOptionsEditor(q, i));
  } else if (q.type === "LINEAR_SCALE") {
    card.appendChild(renderScaleEditor(q, i));
  }

  return card;
}

function renderOptionsEditor(q, i) {
  const wrap = document.createElement("div");
  wrap.className = "q-options";

  q.options.forEach((opt, j) => {
    const row = document.createElement("div");
    row.className = "q-option-row";

    const input = document.createElement("input");
    input.value = opt;
    input.addEventListener("input", () => {
      currentPlan.questions[i].options[j] = input.value;
      debouncedSync();
    });
    row.appendChild(input);

    const removeBtn = document.createElement("button");
    removeBtn.className = "icon-btn";
    removeBtn.type = "button";
    removeBtn.title = "Remove option";
    removeBtn.textContent = "✕";
    removeBtn.onclick = () => removeOption(i, j);
    row.appendChild(removeBtn);

    wrap.appendChild(row);
  });

  const addBtn = document.createElement("button");
  addBtn.className = "btn add-option-btn";
  addBtn.type = "button";
  addBtn.textContent = "+ Add option";
  addBtn.onclick = () => addOption(i);
  wrap.appendChild(addBtn);

  return wrap;
}

function renderScaleEditor(q, i) {
  const wrap = document.createElement("div");
  wrap.className = "q-scale";

  const minLabel = document.createElement("label");
  minLabel.textContent = "From ";
  const minInput = document.createElement("input");
  minInput.type = "number";
  minInput.value = q.scale_min;
  minLabel.appendChild(minInput);
  wrap.appendChild(minLabel);

  const maxLabel = document.createElement("label");
  maxLabel.textContent = "To ";
  const maxInput = document.createElement("input");
  maxInput.type = "number";
  maxInput.value = q.scale_max;
  maxLabel.appendChild(maxInput);
  wrap.appendChild(maxLabel);

  minInput.addEventListener("change", () => {
    const value = parseInt(minInput.value, 10);
    if (Number.isNaN(value) || value >= currentPlan.questions[i].scale_max) {
      showToast("Minimum must be less than maximum");
      minInput.value = currentPlan.questions[i].scale_min;
      return;
    }
    currentPlan.questions[i].scale_min = value;
    syncPlanToServer();
  });

  maxInput.addEventListener("change", () => {
    const value = parseInt(maxInput.value, 10);
    if (Number.isNaN(value) || value <= currentPlan.questions[i].scale_min) {
      showToast("Maximum must be greater than minimum");
      maxInput.value = currentPlan.questions[i].scale_max;
      return;
    }
    currentPlan.questions[i].scale_max = value;
    syncPlanToServer();
  });

  return wrap;
}

// ---------- plan mutations (structural — re-render + sync) ----------

async function deleteQuestion(i) {
  if (currentPlan.questions.length <= 1) {
    showToast("A form needs at least one question");
    return;
  }
  const ok = await confirmDialog("Delete this question? This can't be undone from here, but you can use Undo afterward.");
  if (!ok) return;
  currentPlan.questions.splice(i, 1);
  renderPreview(currentPlan, currentAssumptions);
  syncPlanToServer();
  showToast("Question deleted");
}

function duplicateQuestion(i) {
  const copy = JSON.parse(JSON.stringify(currentPlan.questions[i]));
  currentPlan.questions.splice(i + 1, 0, copy);
  renderPreview(currentPlan, currentAssumptions);
  syncPlanToServer();
  showToast("Question duplicated");
}

function moveQuestion(i, direction) {
  const j = i + direction;
  if (j < 0 || j >= currentPlan.questions.length) return;
  const qs = currentPlan.questions;
  [qs[i], qs[j]] = [qs[j], qs[i]];
  renderPreview(currentPlan, currentAssumptions);
  syncPlanToServer();
}

function addOption(qIndex) {
  const opts = currentPlan.questions[qIndex].options;
  opts.push(`Option ${opts.length + 1}`);
  renderPreview(currentPlan, currentAssumptions);
  syncPlanToServer();
}

function removeOption(qIndex, optIndex) {
  const opts = currentPlan.questions[qIndex].options;
  if (opts.length <= 2) {
    showToast("Choice questions need at least 2 options");
    return;
  }
  opts.splice(optIndex, 1);
  renderPreview(currentPlan, currentAssumptions);
  syncPlanToServer();
}

function changeQuestionType(qIndex, newType) {
  const q = currentPlan.questions[qIndex];
  q.type = newType;
  if (CHOICE_TYPES.has(newType)) {
    if (!q.options || q.options.length < 2) q.options = ["Option 1", "Option 2"];
    q.scale_min = null;
    q.scale_max = null;
  } else if (newType === "LINEAR_SCALE") {
    q.options = null;
    if (q.scale_min == null) q.scale_min = 1;
    if (q.scale_max == null) q.scale_max = 5;
  } else {
    q.options = null;
    q.scale_min = null;
    q.scale_max = null;
  }
  renderPreview(currentPlan, currentAssumptions);
  syncPlanToServer();
}

// ---------- undo / redo ----------

async function handleUndoRedo(endpoint) {
  try {
    const res = await fetch(endpoint, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ session_id: sessionId }),
    });
    if (!res.ok) {
      const body = await res.json().catch(() => ({}));
      throw new Error(body.detail || `Request failed (${res.status})`);
    }
    const data = await res.json();
    canUndo = data.can_undo;
    canRedo = data.can_redo;
    renderPreview(data.plan, currentAssumptions);
  } catch (err) {
    showToast(err.message);
  }
}

undoBtn.addEventListener("click", () => handleUndoRedo("/undo"));
redoBtn.addEventListener("click", () => handleUndoRedo("/redo"));

// ---------- quality check ----------

qualityBtn.addEventListener("click", async () => {
  qualityBtn.disabled = true;
  const originalLabel = qualityBtn.textContent;
  qualityBtn.textContent = "Checking...";
  try {
    const res = await fetch("/quality-check", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ session_id: sessionId }),
    });
    if (!res.ok) {
      const body = await res.json().catch(() => ({}));
      throw new Error(body.detail || `Request failed (${res.status})`);
    }
    const report = await res.json();
    renderQualityReport(report);
  } catch (err) {
    showToast(`Quality check failed: ${err.message}`);
  } finally {
    qualityBtn.disabled = false;
    qualityBtn.textContent = originalLabel;
  }
});

function renderQualityReport(report) {
  qualityReportEl.innerHTML = "";
  qualityReportEl.classList.remove("hidden");

  const summary = document.createElement("div");
  summary.className = "quality-summary";
  summary.innerHTML = `
    <span><b>${report.clarity_score}%</b> clarity</span>
    <span><b>${report.estimated_minutes}</b> min est.</span>
    <span><b>${report.question_count}</b> questions</span>
    <span><b>${report.issues.length}</b> issue(s)</span>
  `;
  qualityReportEl.appendChild(summary);

  for (const issue of report.issues) {
    const row = document.createElement("div");
    row.className = "quality-issue";

    const tag = document.createElement("span");
    tag.className = `severity-tag severity-${issue.severity}`;
    tag.textContent = issue.severity;
    row.appendChild(tag);

    row.appendChild(document.createTextNode(issue.description));

    if (issue.fix_instruction) {
      const fixBtn = document.createElement("button");
      fixBtn.className = "btn apply-fix";
      fixBtn.type = "button";
      fixBtn.textContent = "Apply fix";
      fixBtn.onclick = () => applyQualityFix(issue.fix_instruction, fixBtn);
      row.appendChild(document.createElement("br"));
      row.appendChild(fixBtn);
    }

    qualityReportEl.appendChild(row);
  }

  if (report.suggestions.length) {
    const list = document.createElement("ul");
    list.className = "quality-suggestions";
    for (const s of report.suggestions) {
      const li = document.createElement("li");
      li.textContent = s;
      list.appendChild(li);
    }
    qualityReportEl.appendChild(list);
  }
}

async function applyQualityFix(instruction, btn) {
  btn.disabled = true;
  addMessage(instruction, "user");
  await sendChatMessage(instruction);
}

// ---------- AI chat / edit ----------

async function sendChatMessage(text) {
  const isEditing = !previewEl.classList.contains("hidden");

  messageEl.disabled = true;
  sendBtn.disabled = true;
  const loadingMsg = addLoadingMessage(isEditing ? "Updating your form..." : "Thinking...");

  try {
    const res = await fetch("/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        session_id: sessionId,
        message: text,
        language: languageSelect.value,
        tone: toneSelect.value,
      }),
    });
    if (!res.ok) {
      const body = await res.json().catch(() => ({}));
      throw new Error(body.detail || `Request failed (${res.status})`);
    }
    const data = await res.json();
    loadingMsg.remove();
    if (data.type === "clarification") {
      addMessage(data.question, "agent");
    } else if (data.type === "preview") {
      canUndo = data.can_undo;
      canRedo = data.can_redo;
      addMessage(
        data.edited
          ? "Updated the plan below."
          : "Here's the form I'd create. Review it below.",
        "agent"
      );
      renderPreview(data.plan, data.assumptions);
    }
  } catch (err) {
    loadingMsg.remove();
    showError(err.message, () => sendChatMessage(text));
  } finally {
    messageEl.disabled = false;
    sendBtn.disabled = false;
    messageEl.focus();
  }
}

composerEl.addEventListener("submit", (e) => {
  e.preventDefault();
  const text = messageEl.value.trim();
  if (!text) return;

  clearError();
  addMessage(text, "user");
  messageEl.value = "";
  sendChatMessage(text);
});

// ---------- confirm / cancel / start over ----------

async function doConfirm() {
  clearError();
  const originalLabel = confirmBtn.textContent;
  confirmBtn.disabled = true;
  confirmBtn.textContent = "Creating form...";
  try {
    const res = await fetch("/confirm", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ session_id: sessionId }),
    });
    if (!res.ok) {
      const body = await res.json().catch(() => ({}));
      throw new Error(body.detail || `Request failed (${res.status})`);
    }
    const data = await res.json();
    previewEl.classList.add("hidden");
    messageEl.placeholder = DEFAULT_PLACEHOLDER;
    resultEl.innerHTML = "";
    resultEl.classList.remove("hidden");
    const link = document.createElement("a");
    link.href = data.url;
    link.target = "_blank";
    link.textContent = "Open your Google Form";
    resultEl.appendChild(link);

    const newFormBtn = document.createElement("button");
    newFormBtn.className = "btn btn-primary";
    newFormBtn.textContent = "Start a new form";
    newFormBtn.onclick = startOver;
    resultEl.appendChild(newFormBtn);
  } catch (err) {
    confirmBtn.disabled = false;
    confirmBtn.textContent = originalLabel;
    showError(err.message, doConfirm);
  }
}

confirmBtn.addEventListener("click", doConfirm);

cancelBtn.addEventListener("click", async () => {
  cancelBtn.disabled = true;
  try {
    await fetch("/cancel", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ session_id: sessionId }),
    });
  } finally {
    previewEl.classList.add("hidden");
    previewEmptyEl.classList.remove("hidden");
    currentPlan = null;
    canUndo = false;
    canRedo = false;
    messageEl.placeholder = DEFAULT_PLACEHOLDER;
    cancelBtn.disabled = false;
  }
});

function startOver() {
  sessionId = crypto.randomUUID();
  chatEl.innerHTML = "";
  previewEl.classList.add("hidden");
  previewEmptyEl.classList.remove("hidden");
  previewContentEl.innerHTML = "";
  hideQualityReport();
  resultEl.classList.add("hidden");
  resultEl.innerHTML = "";
  clearError();
  currentPlan = null;
  currentAssumptions = [];
  canUndo = false;
  canRedo = false;
  messageEl.value = "";
  messageEl.placeholder = DEFAULT_PLACEHOLDER;
  messageEl.focus();
}

startOverBtn.addEventListener("click", startOver);

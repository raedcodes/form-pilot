let sessionId = crypto.randomUUID();

const chatEl = document.getElementById("chat");
const composerEl = document.getElementById("composer");
const messageEl = document.getElementById("message");
const previewEl = document.getElementById("preview");
const resultEl = document.getElementById("result");
const errorEl = document.getElementById("error");
const startOverBtn = document.getElementById("start-over");

const TYPE_LABELS = {
  SHORT_ANSWER: "Short answer",
  PARAGRAPH: "Paragraph",
  MULTIPLE_CHOICE: "Multiple choice",
  CHECKBOXES: "Checkboxes",
  DROPDOWN: "Dropdown",
  LINEAR_SCALE: "Rating scale",
};

let currentPlan = null;

const DEFAULT_PLACEHOLDER = messageEl.placeholder;
const EDIT_PLACEHOLDER = 'e.g. "make question 3 optional" or "remove the email question"';

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

function renderPreview(plan, assumptions) {
  currentPlan = plan;
  previewEl.innerHTML = "";
  previewEl.classList.remove("hidden");

  const heading = document.createElement("h2");
  heading.textContent = plan.title;
  previewEl.appendChild(heading);

  if (plan.description) {
    const desc = document.createElement("p");
    desc.textContent = plan.description;
    previewEl.appendChild(desc);
  }

  if (assumptions && assumptions.length) {
    const box = document.createElement("div");
    box.className = "assumptions";

    const label = document.createElement("div");
    label.className = "assumptions-label";
    label.textContent = "Assumptions made — double-check these:";
    box.appendChild(label);

    const list = document.createElement("ul");
    for (const a of assumptions) {
      const li = document.createElement("li");
      li.textContent = a;
      list.appendChild(li);
    }
    box.appendChild(list);
    previewEl.appendChild(box);
  }

  for (const [i, q] of plan.questions.entries()) {
    const card = document.createElement("div");
    card.className = "qcard";

    const titleRow = document.createElement("div");
    titleRow.className = "qtitle";
    titleRow.textContent = `${i + 1}. ${q.title}`;
    if (q.required) {
      const star = document.createElement("span");
      star.className = "required-star";
      star.textContent = " *";
      titleRow.appendChild(star);
    }
    card.appendChild(titleRow);

    const typeRow = document.createElement("div");
    typeRow.className = "qtype";
    typeRow.textContent =
      q.type === "LINEAR_SCALE"
        ? `${TYPE_LABELS[q.type]} (${q.scale_min}–${q.scale_max})`
        : TYPE_LABELS[q.type] || q.type;
    card.appendChild(typeRow);

    if (q.options) {
      const optList = document.createElement("ul");
      optList.className = "qoptions";
      for (const opt of q.options) {
        const li = document.createElement("li");
        li.textContent = opt;
        optList.appendChild(li);
      }
      card.appendChild(optList);
    }

    previewEl.appendChild(card);
  }

  const actions = document.createElement("div");
  actions.className = "actions";

  const confirmBtn = document.createElement("button");
  confirmBtn.textContent = "Confirm and create form";
  confirmBtn.onclick = () => confirmForm(confirmBtn);

  const cancelBtn = document.createElement("button");
  cancelBtn.textContent = "Cancel";
  cancelBtn.onclick = async () => {
    cancelBtn.disabled = true;
    try {
      await fetch("/cancel", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ session_id: sessionId }),
      });
    } finally {
      previewEl.classList.add("hidden");
      currentPlan = null;
      messageEl.placeholder = DEFAULT_PLACEHOLDER;
    }
  };

  actions.appendChild(confirmBtn);
  actions.appendChild(cancelBtn);
  previewEl.appendChild(actions);

  messageEl.placeholder = EDIT_PLACEHOLDER;
}

async function confirmForm(btn) {
  clearError();
  const originalLabel = btn.textContent;
  btn.disabled = true;
  btn.textContent = "Creating form...";
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
    newFormBtn.textContent = "Start a new form";
    newFormBtn.onclick = startOver;
    resultEl.appendChild(newFormBtn);
  } catch (err) {
    btn.disabled = false;
    btn.textContent = originalLabel;
    showError(err.message, () => confirmForm(btn));
  }
}

const sendBtn = composerEl.querySelector("button");

async function sendChatMessage(text) {
  const isEditing = !previewEl.classList.contains("hidden");

  messageEl.disabled = true;
  sendBtn.disabled = true;
  const loadingMsg = addLoadingMessage(isEditing ? "Updating your form..." : "Thinking...");

  try {
    const res = await fetch("/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ session_id: sessionId, message: text }),
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

function startOver() {
  sessionId = crypto.randomUUID();
  chatEl.innerHTML = "";
  previewEl.classList.add("hidden");
  previewEl.innerHTML = "";
  resultEl.classList.add("hidden");
  resultEl.innerHTML = "";
  clearError();
  currentPlan = null;
  messageEl.value = "";
  messageEl.placeholder = DEFAULT_PLACEHOLDER;
  messageEl.focus();
}

startOverBtn.addEventListener("click", startOver);

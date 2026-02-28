const serviceState = document.getElementById("serviceState");
const queueCount = document.getElementById("queueCount");
const accessInfo = document.getElementById("accessInfo");
const macroList = document.getElementById("macroList");
const toast = document.getElementById("toast");

async function api(path, options = {}) {
  const response = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  const data = await response.json();
  if (!response.ok || data.ok === false) {
    throw new Error(data.error || `HTTP ${response.status}`);
  }
  return data;
}

function showToast(message, isError = false) {
  toast.hidden = false;
  toast.textContent = message;
  toast.classList.toggle("error", isError);
  window.clearTimeout(showToast.timer);
  showToast.timer = window.setTimeout(() => {
    toast.hidden = true;
  }, 2200);
}

async function queueLines(lines, successMessage = "Comando enviado") {
  await api("/api/queue", {
    method: "POST",
    body: JSON.stringify({ lines }),
  });
  showToast(successMessage);
  await refreshStatus();
}

function buildAccessInfo(status) {
  const urls = (status.addresses || []).map((addr) => `http://${addr}:${status.port}`);
  if (urls.length === 0) {
    return `http://${status.hostname}:${status.port}`;
  }
  return urls.join("  |  ");
}

async function refreshStatus() {
  const status = await api("/api/status");
  serviceState.textContent = status.keyboard_service;
  queueCount.textContent = String(status.queue_pending);
  accessInfo.textContent = buildAccessInfo(status);
}

async function loadMacros() {
  const data = await api("/api/macros");
  const entries = Object.entries(data.macros || {});
  if (entries.length === 0) {
    macroList.innerHTML = '<p class="muted">No hay macros definidas.</p>';
    return;
  }

  macroList.innerHTML = "";
  entries.forEach(([name, lines]) => {
    const button = document.createElement("button");
    button.textContent = name.replaceAll("_", " ");
    button.title = lines.join("\n");
    button.addEventListener("click", () => queueLines(lines, `Macro enviada: ${name}`));
    macroList.appendChild(button);
  });
}

function attachQuickButtons() {
  document.querySelectorAll("[data-key]").forEach((button) => {
    button.addEventListener("click", () => {
      queueLines([`KEY ${button.dataset.key}`], `Tecla enviada: ${button.dataset.key}`);
    });
  });

  document.querySelectorAll("[data-combo]").forEach((button) => {
    button.addEventListener("click", () => {
      queueLines([`COMBO ${button.dataset.combo}`], `Combo enviado: ${button.dataset.combo}`);
    });
  });
}

function attachTextActions() {
  const textInput = document.getElementById("textInput");
  const appendEnter = document.getElementById("appendEnter");
  const sendText = document.getElementById("sendText");
  const clearText = document.getElementById("clearText");

  sendText.addEventListener("click", async () => {
    const value = textInput.value;
    if (!value.trim()) {
      showToast("Escribe texto primero", true);
      return;
    }

    const lines = value
      .split("\n")
      .map((line) => `TEXT ${line}`);

    if (appendEnter.checked) {
      lines.push("KEY ENTER");
    }

    await queueLines(lines, "Texto encolado");
  });

  clearText.addEventListener("click", () => {
    textInput.value = "";
  });
}

function attachComboBuilder() {
  const sendCombo = document.getElementById("sendCombo");
  const comboKey = document.getElementById("comboKey");

  sendCombo.addEventListener("click", async () => {
    const key = comboKey.value.trim();
    if (!key) {
      showToast("Define una tecla para el combo", true);
      return;
    }

    const modifiers = Array.from(document.querySelectorAll('.toggle-group input:checked'))
      .map((input) => input.value);
    const combo = [...modifiers, key.toUpperCase()].join("+");
    await queueLines([`COMBO ${combo}`], `Combo enviado: ${combo}`);
  });
}

async function boot() {
  try {
    attachQuickButtons();
    attachTextActions();
    attachComboBuilder();
    document.getElementById("refreshStatus").addEventListener("click", refreshStatus);
    await Promise.all([refreshStatus(), loadMacros()]);
    window.setInterval(refreshStatus, 5000);
  } catch (error) {
    showToast(error.message, true);
  }
}

boot();

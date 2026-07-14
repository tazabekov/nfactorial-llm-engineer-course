const CRITERIA = [
  { key: "cleanliness", icon: "🧹", label: "Чистота" },
  { key: "repair_condition", icon: "🔨", label: "Ремонт" },
  { key: "modernity", icon: "🛋", label: "Дизайн" },
  { key: "lighting", icon: "☀️", label: "Свет" },
  { key: "clutter", icon: "📦", label: "Простор" },
];

const dropzone = document.getElementById("dropzone");
const fileInput = document.getElementById("file-input");
const preview = document.getElementById("preview");
const analyzeBtn = document.getElementById("analyze-btn");
const errorMsg = document.getElementById("error-msg");

const placeholder = document.getElementById("placeholder");
const loading = document.getElementById("loading");
const report = document.getElementById("report");
const scorecard = document.getElementById("scorecard");
const overallScoreEl = document.getElementById("overall-score");
const summaryEl = document.getElementById("summary");

const stagePrompt = document.getElementById("stage-prompt");
const temperatureInput = document.getElementById("temperature");
const topPInput = document.getElementById("top-p");
const topKInput = document.getElementById("top-k");
const seedInput = document.getElementById("seed");
const stageBtn = document.getElementById("stage-btn");
const stageErrorMsg = document.getElementById("stage-error-msg");

const stagingPlaceholder = document.getElementById("staging-placeholder");
const stagingLoading = document.getElementById("staging-loading");
const stagingCompare = document.getElementById("staging-compare");
const compareFrame = document.getElementById("compare-frame");
const compareBefore = document.getElementById("compare-before");
const compareAfter = document.getElementById("compare-after");
const compareRange = document.getElementById("compare-range");

compareRange.addEventListener("input", () => {
  compareFrame.style.setProperty("--split", `${compareRange.value}%`);
});

const finalreportBtn = document.getElementById("finalreport-btn");
const finalreportErrorMsg = document.getElementById("finalreport-error-msg");
const finalreportPlaceholder = document.getElementById("finalreport-placeholder");
const finalreportLoading = document.getElementById("finalreport-loading");
const finalreportEl = document.getElementById("finalreport");
const finalreportText = document.getElementById("finalreport-text");
const receiptItem = document.getElementById("receipt-item");
const receiptStyle = document.getElementById("receipt-style");
const receiptPrice = document.getElementById("receipt-price");

let selectedFile = null;
let beforeModernity = null;
let stagedImage = null; // { base64, mimeType, prompt }

function updateFinalreportAvailability() {
  finalreportBtn.disabled = beforeModernity === null || stagedImage === null;
}

[
  [temperatureInput, "temperature-val"],
  [topPInput, "top-p-val"],
  [topKInput, "top-k-val"],
].forEach(([input, outputId]) => {
  const output = document.getElementById(outputId);
  input.addEventListener("input", () => {
    output.textContent = input.value;
  });
});

function scoreColor(value) {
  if (value <= 4) return "var(--bad)";
  if (value <= 7) return "var(--mid)";
  return "var(--good)";
}

function showError(message) {
  errorMsg.textContent = message;
  errorMsg.hidden = !message;
}

function setFile(file) {
  if (!file || !file.type.startsWith("image/")) {
    showError("Пожалуйста, выберите файл изображения.");
    return;
  }
  selectedFile = file;
  showError("");

  const reader = new FileReader();
  reader.onload = (e) => {
    preview.src = e.target.result;
    preview.hidden = false;
    dropzone.querySelector(".dropzone__prompt").style.display = "none";
  };
  reader.readAsDataURL(file);

  analyzeBtn.disabled = false;
  stageBtn.disabled = false;
}

dropzone.addEventListener("click", () => fileInput.click());

fileInput.addEventListener("change", () => {
  if (fileInput.files[0]) setFile(fileInput.files[0]);
});

["dragenter", "dragover"].forEach((evt) =>
  dropzone.addEventListener(evt, (e) => {
    e.preventDefault();
    dropzone.classList.add("dropzone--drag");
  })
);

["dragleave", "drop"].forEach((evt) =>
  dropzone.addEventListener(evt, (e) => {
    e.preventDefault();
    dropzone.classList.remove("dropzone--drag");
  })
);

dropzone.addEventListener("drop", (e) => {
  const file = e.dataTransfer.files[0];
  if (file) setFile(file);
});

function renderReport(data) {
  scorecard.innerHTML = "";
  let total = 0;

  CRITERIA.forEach((criterion, i) => {
    const value = data[criterion.key];
    total += value;

    const row = document.createElement("li");
    row.className = "scorecard__row";
    row.style.animationDelay = `${i * 90}ms`;
    row.innerHTML = `
      <span class="scorecard__icon">${criterion.icon}</span>
      <span class="scorecard__label">${criterion.label}</span>
      <span class="scorecard__track">
        <span class="scorecard__fill" style="background:${scoreColor(value)}"></span>
      </span>
      <span class="scorecard__value" style="color:${scoreColor(value)}">${value}</span>
    `;
    scorecard.appendChild(row);

    requestAnimationFrame(() => {
      const fill = row.querySelector(".scorecard__fill");
      fill.style.width = `${value * 10}%`;
    });
  });

  const overall = Math.round((total / CRITERIA.length) * 10) / 10;
  overallScoreEl.textContent = overall;
  summaryEl.textContent = data.summary;

  placeholder.hidden = true;
  loading.hidden = true;
  report.hidden = false;

  beforeModernity = data.modernity;
  updateFinalreportAvailability();
}

analyzeBtn.addEventListener("click", async () => {
  if (!selectedFile) return;

  showError("");
  placeholder.hidden = true;
  report.hidden = true;
  loading.hidden = false;
  analyzeBtn.disabled = true;

  const formData = new FormData();
  formData.append("photo", selectedFile);

  try {
    const res = await fetch("/analyze", { method: "POST", body: formData });
    const data = await res.json();

    if (!res.ok) {
      throw new Error(data.detail || "Не удалось проанализировать фотографию.");
    }

    renderReport(data);
  } catch (err) {
    loading.hidden = true;
    placeholder.hidden = false;
    showError(err.message);
  } finally {
    analyzeBtn.disabled = false;
  }
});

function showStageError(message) {
  stageErrorMsg.textContent = message;
  stageErrorMsg.hidden = !message;
}

stageBtn.addEventListener("click", async () => {
  if (!selectedFile) return;

  showStageError("");
  stagingPlaceholder.hidden = true;
  stagingCompare.hidden = true;
  stagingLoading.hidden = false;
  stageBtn.disabled = true;

  const formData = new FormData();
  formData.append("photo", selectedFile);
  formData.append("prompt", stagePrompt.value);
  formData.append("temperature", temperatureInput.value);
  formData.append("top_p", topPInput.value);
  formData.append("top_k", topKInput.value);
  if (seedInput.value !== "") {
    formData.append("seed", seedInput.value);
  }

  try {
    const res = await fetch("/stage", { method: "POST", body: formData });
    const data = await res.json();

    if (!res.ok) {
      throw new Error(data.detail || "Не удалось преобразить фотографию.");
    }

    compareBefore.src = preview.src;
    compareAfter.src = `data:${data.mime_type};base64,${data.image_base64}`;
    compareRange.value = 50;
    compareFrame.style.setProperty("--split", "50%");

    stagingLoading.hidden = true;
    stagingCompare.hidden = false;

    stagedImage = {
      base64: data.image_base64,
      mimeType: data.mime_type,
      prompt: stagePrompt.value,
    };
    updateFinalreportAvailability();
  } catch (err) {
    stagingLoading.hidden = true;
    stagingPlaceholder.hidden = false;
    showStageError(err.message);
  } finally {
    stageBtn.disabled = false;
  }
});

function showFinalreportError(message) {
  finalreportErrorMsg.textContent = message;
  finalreportErrorMsg.hidden = !message;
}

const priceFormatter = new Intl.NumberFormat("ru-RU");

finalreportBtn.addEventListener("click", async () => {
  if (beforeModernity === null || stagedImage === null) return;

  showFinalreportError("");
  finalreportPlaceholder.hidden = true;
  finalreportEl.hidden = true;
  finalreportLoading.hidden = false;
  finalreportBtn.disabled = true;

  try {
    const res = await fetch("/report", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        image_base64: stagedImage.base64,
        mime_type: stagedImage.mimeType,
        staging_prompt: stagedImage.prompt,
        before_modernity: beforeModernity,
      }),
    });
    const data = await res.json();

    if (!res.ok) {
      throw new Error(data.detail || "Не удалось рассчитать стоимость обновления.");
    }

    finalreportText.textContent = data.report_text;
    receiptItem.textContent = data.matched_furniture.model_name;
    receiptStyle.textContent = `${data.matched_furniture.style} · ${data.matched_furniture.color}`;
    receiptPrice.textContent = `${priceFormatter.format(data.matched_furniture.price_kzt)} тг.`;

    finalreportLoading.hidden = true;
    finalreportEl.hidden = false;
  } catch (err) {
    finalreportLoading.hidden = true;
    finalreportPlaceholder.hidden = false;
    showFinalreportError(err.message);
  } finally {
    finalreportBtn.disabled = false;
  }
});

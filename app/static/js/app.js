function setLoadingStates() {
  document.querySelectorAll("[data-loading-text]").forEach((button) => {
    button.addEventListener("click", () => {
      if (button.tagName === "BUTTON") {
        button.dataset.originalText = button.textContent;
        button.textContent = button.dataset.loadingText;
      }
    });
  });
}

function setFilePickerLabels() {
  document.querySelectorAll("[data-file-input]").forEach((input) => {
    input.addEventListener("change", () => {
      const label = input.closest("form")?.querySelector("[data-file-name]");
      if (!label) return;
      label.textContent = input.files && input.files.length ? input.files[0].name : "Файл ще не обрано";
    });
  });
}

function showChartFallback(id) {
  const fallback = document.getElementById(id);
  if (fallback) fallback.classList.add("visible");
}

function drawLegend(ctx, items, x, y) {
  ctx.font = "12px 'Segoe UI', sans-serif";
  items.forEach((item, index) => {
    const offsetX = x + index * 145;
    ctx.strokeStyle = item.color;
    ctx.lineWidth = item.width || 3;
    if (item.dashed) ctx.setLineDash([6, 5]); else ctx.setLineDash([]);
    ctx.beginPath();
    ctx.moveTo(offsetX, y);
    ctx.lineTo(offsetX + 22, y);
    ctx.stroke();
    ctx.setLineDash([]);
    ctx.fillStyle = "#10203a";
    ctx.fillText(item.label, offsetX + 28, y + 4);
  });
}

function drawSeries(ctx, values, toX, toY, style) {
  ctx.save();
  ctx.strokeStyle = style.color;
  ctx.lineWidth = style.width || 3;
  if (style.dashed) ctx.setLineDash([8, 6]);
  ctx.beginPath();
  let started = false;
  values.forEach((value, index) => {
    if (value === null || Number.isNaN(value)) {
      started = false;
      return;
    }
    const x = toX(index);
    const y = toY(value);
    if (!started) {
      ctx.moveTo(x, y);
      started = true;
    } else {
      ctx.lineTo(x, y);
    }
  });
  ctx.stroke();
  ctx.restore();
}

function drawDemandChart(canvas, payload) {
  const ctx = canvas.getContext("2d");
  const ratio = window.devicePixelRatio || 1;
  const width = canvas.clientWidth || 760;
  const height = canvas.parentElement.classList.contains("chart-wrap-small") ? 240 : 330;
  canvas.width = width * ratio;
  canvas.height = height * ratio;
  ctx.scale(ratio, ratio);
  ctx.clearRect(0, 0, width, height);

  const padding = { top: 20, right: 20, bottom: 56, left: 48 };
  const plotWidth = width - padding.left - padding.right;
  const plotHeight = height - padding.top - padding.bottom;
  const history = payload.history || [];
  const forecast = payload.forecast || [];
  const labels = [...history.map((item) => item.date), ...forecast.map((item) => item.date)];
  const actualValues = [...history.map((item) => Number(item.sales)), ...forecast.map(() => null)];
  const forecastValues = [...history.map(() => null), ...forecast.map((item) => Number(item.predicted))];
  const allValues = [...history.map((item) => Number(item.sales)), ...forecast.map((item) => Number(item.predicted))];
  const maxValue = Math.max(...allValues, 10) * 1.16;
  const forecastStartIndex = history.length;

  ctx.fillStyle = "#ffffff";
  ctx.fillRect(0, 0, width, height);
  ctx.strokeStyle = "#dbe6f6";
  ctx.lineWidth = 1;
  ctx.font = "12px 'Segoe UI', sans-serif";
  ctx.fillStyle = "#607089";

  for (let step = 0; step <= 4; step += 1) {
    const y = padding.top + (plotHeight / 4) * step;
    const value = Math.round(maxValue - (maxValue / 4) * step);
    ctx.beginPath();
    ctx.moveTo(padding.left, y);
    ctx.lineTo(width - padding.right, y);
    ctx.stroke();
    ctx.fillText(String(value), 6, y + 4);
  }

  const toX = (index) => padding.left + (index / Math.max(labels.length - 1, 1)) * plotWidth;
  const toY = (value) => padding.top + plotHeight - (value / maxValue) * plotHeight;

  if (forecastStartIndex < labels.length) {
    const xStart = toX(forecastStartIndex);
    ctx.fillStyle = "rgba(15, 140, 99, 0.04)";
    ctx.fillRect(xStart, padding.top, width - padding.right - xStart, plotHeight);

    ctx.save();
    ctx.strokeStyle = "#7c8fb6";
    ctx.lineWidth = 2;
    ctx.setLineDash([4, 4]);
    ctx.beginPath();
    ctx.moveTo(xStart, padding.top);
    ctx.lineTo(xStart, padding.top + plotHeight);
    ctx.stroke();
    ctx.restore();

    ctx.font = "600 13px 'Segoe UI', sans-serif";
    ctx.fillStyle = "#42526f";
    ctx.fillText("Початок прогнозу", Math.min(xStart + 6, width - 130), padding.top + 14);
    ctx.font = "12px 'Segoe UI', sans-serif";
  }

  drawSeries(ctx, actualValues, toX, toY, { color: "#2448d6", width: 3, dashed: false });
  drawSeries(ctx, forecastValues, toX, toY, { color: "#0f8c63", width: 3, dashed: true });

  drawLegend(ctx, [
    { label: "Фактичні продажі", color: "#2448d6", dashed: false },
    { label: "Прогноз", color: "#0f8c63", dashed: true },
    { label: "Початок прогнозу", color: "#7c8fb6", dashed: true, width: 2 },
  ], padding.left, height - 20);
}

function drawImportanceChart(canvas, items) {
  const ctx = canvas.getContext("2d");
  const ratio = window.devicePixelRatio || 1;
  const width = canvas.clientWidth || 420;
  const height = 240;
  canvas.width = width * ratio;
  canvas.height = height * ratio;
  ctx.scale(ratio, ratio);
  ctx.clearRect(0, 0, width, height);
  ctx.fillStyle = "#ffffff";
  ctx.fillRect(0, 0, width, height);

  const data = (items || []).slice(0, 8);
  if (!data.length) return;
  const padding = { top: 18, right: 18, bottom: 18, left: 178 };
  const maxValue = Math.max(...data.map((item) => Number(item.importance)), 0.001);
  const barHeight = (height - padding.top - padding.bottom) / data.length - 8;

  ctx.font = "11px 'Segoe UI', sans-serif";
  data.forEach((item, index) => {
    const y = padding.top + index * (barHeight + 8);
    const widthBar = ((width - padding.left - padding.right) * Number(item.importance)) / maxValue;
    ctx.fillStyle = "#eef3fb";
    ctx.fillRect(padding.left, y, width - padding.left - padding.right, barHeight);
    ctx.fillStyle = "#2448d6";
    ctx.fillRect(padding.left, y, widthBar, barHeight);
    ctx.fillStyle = "#10203a";
    ctx.fillText(item.label || item.feature, 8, y + barHeight * 0.7);
  });
}

async function renderCharts() {
  const demandCanvas = document.getElementById("demandChart");
  if (demandCanvas) {
    try {
      const productId = demandCanvas.dataset.productId;
      const days = demandCanvas.dataset.days || "14";
      const response = await fetch(`/api/chart-data/${productId}?days=${days}`);
      if (!response.ok) {
        showChartFallback("chartFallback");
      } else {
        const payload = await response.json();
        drawDemandChart(demandCanvas, payload.data);
      }
    } catch (error) {
      showChartFallback("chartFallback");
    }
  }

  const importanceCanvas = document.getElementById("importanceChart");
  if (importanceCanvas) {
    try {
      const items = JSON.parse(importanceCanvas.dataset.importance || "[]");
      drawImportanceChart(importanceCanvas, items);
    } catch (error) {
      showChartFallback("importanceFallback");
    }
  }
}

window.addEventListener("DOMContentLoaded", () => {
  setLoadingStates();
  setFilePickerLabels();
  renderCharts();
});

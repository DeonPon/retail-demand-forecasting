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

function showChartFallback(id) {
  const fallback = document.getElementById(id);
  if (fallback) fallback.classList.add("visible");
}

function drawLegend(ctx, items, x, y) {
  ctx.font = "13px 'Segoe UI', sans-serif";
  items.forEach((item, index) => {
    const offsetX = x + index * 150;
    ctx.strokeStyle = item.color;
    ctx.lineWidth = 3;
    if (item.dashed) ctx.setLineDash([6, 5]); else ctx.setLineDash([]);
    ctx.beginPath();
    ctx.moveTo(offsetX, y);
    ctx.lineTo(offsetX + 22, y);
    ctx.stroke();
    ctx.setLineDash([]);
    ctx.fillStyle = "#10203a";
    ctx.fillText(item.label, offsetX + 30, y + 4);
  });
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

  const padding = { top: 20, right: 20, bottom: 48, left: 44 };
  const plotWidth = width - padding.left - padding.right;
  const plotHeight = height - padding.top - padding.bottom;
  const actual = payload.actual || [];
  const forecast = payload.forecast || [];
  const labels = [...actual.map((item) => item.date), ...forecast.map((item) => item.date)];
  const values = [...actual.map((item) => Number(item.quantity)), ...forecast.map((item) => Number(item.predicted_quantity))];
  const maxValue = Math.max(...values, 10) * 1.16;

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

  const drawLine = (series, color, key, dashed) => {
    ctx.save();
    ctx.strokeStyle = color;
    ctx.lineWidth = 3;
    if (dashed) ctx.setLineDash([8, 6]);
    ctx.beginPath();
    series.forEach((item, index) => {
      const pointValue = Number(item[key]);
      const x = toX(index);
      const y = toY(pointValue);
      if (index === 0) ctx.moveTo(x, y);
      else ctx.lineTo(x, y);
    });
    ctx.stroke();
    ctx.restore();
  };

  const promoPeriods = payload.promo_periods || [];
  promoPeriods.forEach((item, index) => {
    if (Number(item.promo) !== 1) return;
    const x = toX(index);
    ctx.fillStyle = "rgba(245, 158, 11, 0.08)";
    ctx.fillRect(x - 3, padding.top, 6, plotHeight);
  });

  drawLine(actual, "#2448d6", "quantity", false);
  drawLine(forecast, "#0f8c63", "predicted_quantity", true);

  const forecastStart = actual.length ? toX(actual.length - 1) : padding.left;
  ctx.fillStyle = "rgba(36, 72, 214, 0.04)";
  ctx.fillRect(forecastStart, padding.top, width - padding.right - forecastStart, plotHeight);

  drawLegend(ctx, [
    { label: "Фактичні продажі", color: "#2448d6", dashed: false },
    { label: "Прогноз", color: "#0f8c63", dashed: true },
    { label: "Акція", color: "#f59e0b", dashed: false },
  ], padding.left, height - 18);
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
  const padding = { top: 18, right: 18, bottom: 18, left: 130 };
  const maxValue = Math.max(...data.map((item) => Number(item.importance)), 0.001);
  const barHeight = (height - padding.top - padding.bottom) / data.length - 8;

  ctx.font = "12px 'Segoe UI', sans-serif";
  data.forEach((item, index) => {
    const y = padding.top + index * (barHeight + 8);
    const widthBar = ((width - padding.left - padding.right) * Number(item.importance)) / maxValue;
    ctx.fillStyle = "#eef3fb";
    ctx.fillRect(padding.left, y, width - padding.left - padding.right, barHeight);
    ctx.fillStyle = "#2448d6";
    ctx.fillRect(padding.left, y, widthBar, barHeight);
    ctx.fillStyle = "#10203a";
    ctx.fillText(item.feature, 8, y + barHeight * 0.7);
    ctx.fillText(String(item.importance), padding.left + widthBar + 8, y + barHeight * 0.7);
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
  renderCharts();
});

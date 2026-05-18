function showChartFallback() {
  const fallback = document.getElementById("chartFallback");
  if (fallback) fallback.classList.add("visible");
}

function drawLine(ctx, points, color, dashed = false) {
  const visiblePoints = points.filter((point) => point.value !== null);
  if (visiblePoints.length < 2) return;

  ctx.save();
  ctx.strokeStyle = color;
  ctx.lineWidth = 3;
  if (dashed) ctx.setLineDash([8, 6]);
  ctx.beginPath();
  visiblePoints.forEach((point, index) => {
    if (index === 0) {
      ctx.moveTo(point.x, point.y);
    } else {
      ctx.lineTo(point.x, point.y);
    }
  });
  ctx.stroke();
  ctx.restore();
}

function drawLegend(ctx, width, height) {
  ctx.font = "14px system-ui, sans-serif";
  ctx.fillStyle = "#172033";
  ctx.fillText("Фактичні продажі", 48, height - 18);
  ctx.fillText("Прогноз", 220, height - 18);
  ctx.strokeStyle = "#1d4ed8";
  ctx.lineWidth = 3;
  ctx.beginPath();
  ctx.moveTo(18, height - 23);
  ctx.lineTo(40, height - 23);
  ctx.stroke();
  ctx.strokeStyle = "#0f766e";
  ctx.setLineDash([6, 5]);
  ctx.beginPath();
  ctx.moveTo(190, height - 23);
  ctx.lineTo(212, height - 23);
  ctx.stroke();
  ctx.setLineDash([]);
}

function renderCanvasChart(canvas, actual, forecast) {
  const ctx = canvas.getContext("2d");
  const ratio = window.devicePixelRatio || 1;
  const width = canvas.clientWidth || 720;
  const height = 340;
  canvas.width = width * ratio;
  canvas.height = height * ratio;
  ctx.scale(ratio, ratio);
  ctx.clearRect(0, 0, width, height);

  const padding = { top: 22, right: 24, bottom: 56, left: 48 };
  const plotWidth = width - padding.left - padding.right;
  const plotHeight = height - padding.top - padding.bottom;
  const values = [
    ...actual.map((item) => Number(item.quantity)),
    ...forecast.map((item) => Number(item.predicted_quantity)),
  ];
  const maxValue = Math.max(...values, 10) * 1.15;
  const labels = [...actual.map((item) => item.date), ...forecast.map((item) => item.date)];
  const totalPoints = labels.length;

  const toX = (index) => padding.left + (index / Math.max(totalPoints - 1, 1)) * plotWidth;
  const toY = (value) => padding.top + plotHeight - (value / maxValue) * plotHeight;

  ctx.fillStyle = "#ffffff";
  ctx.fillRect(0, 0, width, height);
  ctx.strokeStyle = "#dbe3ef";
  ctx.lineWidth = 1;
  ctx.font = "12px system-ui, sans-serif";
  ctx.fillStyle = "#667085";

  for (let step = 0; step <= 4; step += 1) {
    const y = padding.top + (plotHeight / 4) * step;
    const value = Math.round(maxValue - (maxValue / 4) * step);
    ctx.beginPath();
    ctx.moveTo(padding.left, y);
    ctx.lineTo(width - padding.right, y);
    ctx.stroke();
    ctx.fillText(String(value), 8, y + 4);
  }

  const actualPoints = labels.map((_, index) => ({
    x: toX(index),
    y: index < actual.length ? toY(actual[index].quantity) : 0,
    value: index < actual.length ? actual[index].quantity : null,
  }));
  const forecastPoints = labels.map((_, index) => ({
    x: toX(index),
    y: index >= actual.length ? toY(forecast[index - actual.length].predicted_quantity) : 0,
    value: index >= actual.length ? forecast[index - actual.length].predicted_quantity : null,
  }));

  drawLine(ctx, actualPoints, "#1d4ed8");
  drawLine(ctx, forecastPoints, "#0f766e", true);
  drawLegend(ctx, width, height);
}

async function renderDemandChart() {
  const canvas = document.getElementById("demandChart");
  if (!canvas) return;

  try {
    const productId = canvas.dataset.productId;
    const response = await fetch(`/api/chart-data/${productId}`);
    if (!response.ok) {
      showChartFallback();
      return;
    }
    const payload = await response.json();
    if (payload.status !== "success") {
      showChartFallback();
      return;
    }
    renderCanvasChart(canvas, payload.data.actual, payload.data.forecast);
  } catch (error) {
    showChartFallback();
  }
}

window.addEventListener("DOMContentLoaded", renderDemandChart);
window.addEventListener("resize", renderDemandChart);

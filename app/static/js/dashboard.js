async function renderDemandChart() {
  const canvas = document.getElementById("demandChart");
  if (!canvas || !window.Chart) return;

  const productId = canvas.dataset.productId;
  const response = await fetch(`/api/chart-data/${productId}`);
  const payload = await response.json();
  if (payload.status !== "success") return;

  const actual = payload.data.actual;
  const forecast = payload.data.forecast;
  const labels = [...actual.map((item) => item.date), ...forecast.map((item) => item.date)];
  const actualValues = [...actual.map((item) => item.quantity), ...forecast.map(() => null)];
  const forecastValues = [...actual.map(() => null), ...forecast.map((item) => item.predicted_quantity)];

  new Chart(canvas, {
    type: "line",
    data: {
      labels,
      datasets: [
        {
          label: "Фактичні продажі",
          data: actualValues,
          borderColor: "#1d4ed8",
          backgroundColor: "rgba(29, 78, 216, 0.08)",
          tension: 0.32,
          pointRadius: 0,
        },
        {
          label: "Прогноз",
          data: forecastValues,
          borderColor: "#0f766e",
          backgroundColor: "rgba(15, 118, 110, 0.08)",
          borderDash: [6, 5],
          tension: 0.32,
          pointRadius: 2,
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { position: "bottom" },
      },
      scales: {
        x: { ticks: { maxTicksLimit: 9 } },
        y: { beginAtZero: true },
      },
    },
  });
}

renderDemandChart();

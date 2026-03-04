const API_URL = "https://building-blocks-v8gg.onrender.com/api/dados";

const moistureValueEl = document.getElementById("moistureValue");
const rawValueEl = document.getElementById("rawValue");
const timeValueEl = document.getElementById("timeValue");
const dateValueEl = document.getElementById("dateValue");
const deviceIdEl = document.getElementById("deviceId");
const moistureBarEl = document.getElementById("moistureBar");
const statusDot = document.getElementById("statusDot");
const statusText = document.getElementById("statusText");
const btnRefresh = document.getElementById("btnRefresh");

const ctx = document.getElementById("historyChart").getContext("2d");

const gradientFill = ctx.createLinearGradient(0, 0, 0, 500);
gradientFill.addColorStop(0, "rgba(16, 185, 129, 0.6)");
gradientFill.addColorStop(1, "rgba(16, 185, 129, 0.0)");

Chart.defaults.color = "#94a3b8";
Chart.defaults.font.family = "Outfit";

const historyChart = new Chart(ctx, {
  type: "line",
  data: {
    labels: [],
    datasets: [
      {
        label: "Umidade (%)",
        data: [],
        borderColor: "#10b981",
        backgroundColor: gradientFill,
        borderWidth: 3,
        fill: true,
        pointBackgroundColor: "#1e293b",
        pointBorderColor: "#10b981",
        pointBorderWidth: 2,
        pointRadius: 4,
        pointHoverRadius: 6,
        pointHoverBackgroundColor: "#10b981",
        pointHoverBorderColor: "#fff",
        pointHoverBorderWidth: 2,
        tension: 0.4,
      },
    ],
  },
  options: {
    responsive: true,
    maintainAspectRatio: false,
    layout: {
      padding: { top: 20 },
    },
    plugins: {
      legend: { display: false },
      tooltip: {
        backgroundColor: "rgba(15, 23, 42, 0.9)",
        titleFont: { size: 14, weight: "600" },
        bodyFont: { size: 14 },
        padding: 12,
        cornerRadius: 12,
        displayColors: false,
        borderColor: "rgba(255, 255, 255, 0.1)",
        borderWidth: 1,
        callbacks: {
          label: function (context) {
            return `${context.parsed.y.toFixed(1)}%`;
          },
        },
      },
    },
    scales: {
      y: {
        beginAtZero: true,
        max: 100,
        grid: {
          color: "rgba(255, 255, 255, 0.05)",
          drawBorder: false,
        },
        ticks: {
          padding: 10,
          callback: (value) => value + "%",
        },
      },
      x: {
        grid: {
          display: false,
          drawBorder: false,
        },
        ticks: {
          maxTicksLimit: 10,
          maxRotation: 0,
          padding: 10,
        },
      },
    },
    interaction: {
      mode: "index",
      intersect: false,
    },
  },
});

function processServerData(data) {
  if (!data || !Array.isArray(data.items)) return [];

  const items = data.items;
  const readings = [];
  let current = {};

  for (const item of items) {
    if (item.key === "device_id" && Object.keys(current).length > 0) {
      readings.push({ ...current });
      current = {};
    }

    let val = item.value;
    if (item.key === "timestamp" || item.key === "soil_moisture_raw") {
      val = parseInt(val, 10);
    } else if (item.key === "soil_moisture_percent") {
      val = parseFloat(val);
    }

    current[item.key] = val;
  }

  if (Object.keys(current).length > 0) {
    readings.push(current);
  }

  return readings;
}

function updateDashboard(readings) {
  if (readings.length === 0) return;

  readings.sort((a, b) => a.timestamp - b.timestamp);
  const chartReadings = readings.slice(-50);
  const latest = chartReadings[chartReadings.length - 1];

  if (latest.soil_moisture_percent === undefined) return;

  [moistureValueEl, rawValueEl, timeValueEl].forEach((el) => {
    el.classList.remove("value-update-anim");
    void el.offsetWidth;
    el.classList.add("value-update-anim");
  });

  const percent = latest.soil_moisture_percent.toFixed(1);
  moistureValueEl.textContent = percent;
  moistureBarEl.style.width = `${percent}%`;

  if (percent < 30) {
    moistureBarEl.style.background = "linear-gradient(90deg, #f59e0b, #ef4444)";
  } else if (percent > 80) {
    moistureBarEl.style.background = "linear-gradient(90deg, #3b82f6, #0ea5e9)";
  } else {
    moistureBarEl.style.background =
      "linear-gradient(90deg, #3b82f6, var(--accent-primary))";
  }

  rawValueEl.textContent = latest.soil_moisture_raw || "N/A";
  deviceIdEl.textContent = latest.device_id || "Desconhecido";

  let ts = latest.timestamp || 0;
  if (ts.toString().length === 10) ts *= 1000;

  let date;
  if (ts < 31536000000) {
    date = new Date();
  } else {
    date = new Date(ts);
  }

  timeValueEl.textContent = date.toLocaleTimeString("pt-BR", {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
  dateValueEl.textContent = date.toLocaleDateString("pt-BR");

  const labels = [];
  const _data = [];

  chartReadings.forEach((item) => {
    let its = item.timestamp || 0;
    if (its.toString().length === 10) its *= 1000;

    let idate = new Date();
    if (its >= 31536000000) {
      idate = new Date(its);
    }
    labels.push(
      idate.toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" }),
    );
    _data.push(item.soil_moisture_percent);
  });

  historyChart.data.labels = labels;
  historyChart.data.datasets[0].data = _data;
  historyChart.update();
}

let isFetching = false;

async function fetchSensorData() {
  if (isFetching) return;
  isFetching = true;

  btnRefresh.classList.add("spinning");
  statusDot.className = "status-dot updating";
  statusText.textContent = "Atualizando...";

  try {
    const response = await fetch(API_URL);
    if (!response.ok) throw new Error("API Error");

    const data = await response.json();
    const readings = processServerData(data);

    updateDashboard(readings);

    statusDot.className = "status-dot online";
    statusText.textContent = "Online";
  } catch (error) {
    console.error("Fetch falhou:", error);
    statusDot.className = "status-dot";
    statusText.textContent = "Offline";
  } finally {
    setTimeout(() => {
      btnRefresh.classList.remove("spinning");
      if (statusDot.classList.contains("updating")) {
        statusDot.className = "status-dot";
      }
    }, 500);
    isFetching = false;
  }
}

btnRefresh.addEventListener("click", fetchSensorData);

fetchSensorData();
setInterval(fetchSensorData, 10000);

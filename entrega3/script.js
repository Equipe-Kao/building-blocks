// ── Config ──
const API_URL = 'https://building-blocks-v8gg.onrender.com/api/dados';
const POLL_INTERVAL = 10000; // 10s

// ── State ──
let chart = null;
let pollTimer = null;

// ── Bootstrap ──
document.addEventListener('DOMContentLoaded', () => {
  fetchData();
  pollTimer = setInterval(fetchData, POLL_INTERVAL);
});

// ── Fetch ──
async function fetchData() {
  try {
    const res = await fetch(API_URL);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const json = await res.json();
    const readings = groupReadings(json.items);
    render(readings);
    setStatus(true);
  } catch (err) {
    console.error('Fetch error:', err);
    setStatus(false);
    showError(err.message);
  }
}

// ── Group flat key/value items into reading objects ──
// The ESP32 buildJson sends:
//   soil_moisture_raw   → actually temperature (°C)
//   soil_moisture_percent → actually humidity (%)
function groupReadings(items) {
  const readings = [];
  let current = {};

  for (const item of items) {
    if (current.hasOwnProperty(item.key)) {
      readings.push({ ...current });
      current = {};
    }
    current[item.key] = item.value;
  }

  if (Object.keys(current).length > 0) {
    readings.push(current);
  }

  return readings;
}

// ── Render everything ──
function render(readings) {
  const root = document.getElementById('appRoot');

  // First render: stamp template
  if (!document.getElementById('metricTemp')) {
    root.innerHTML = '';
    const tpl = document.getElementById('dashboardTemplate');
    root.appendChild(tpl.content.cloneNode(true));
    createChart();
  }

  if (readings.length === 0) return;

  const latest = readings[readings.length - 1];
  // soil_moisture_raw = temperature, soil_moisture_percent = humidity
  const temperature = parseFloat(latest.soil_moisture_raw ?? 0);
  const humidity = parseFloat(latest.soil_moisture_percent ?? 0);
  const deviceId = latest.device_id ?? '—';

  // Metric cards
  document.getElementById('metricTemp').innerHTML = `${temperature.toFixed(1)}<span class="unit">°C</span>`;
  document.getElementById('metricHumidity').innerHTML = `${humidity.toFixed(1)}<span class="unit">%</span>`;
  document.getElementById('metricDevice').textContent = deviceId;
  document.getElementById('metricTotal').textContent = readings.length;

  // Gauges
  updateTempGauge(temperature);
  updateHumGauge(humidity);

  // Chart
  updateChart(readings);

  // Table
  updateTable(readings);
}

// ── Chart.js (dual axis: temperature + humidity) ──
function createChart() {
  const ctx = document.getElementById('sensorChart').getContext('2d');

  const tempGradient = ctx.createLinearGradient(0, 0, 0, 280);
  tempGradient.addColorStop(0, 'rgba(248, 113, 113, 0.25)');
  tempGradient.addColorStop(1, 'rgba(248, 113, 113, 0.0)');

  const humGradient = ctx.createLinearGradient(0, 0, 0, 280);
  humGradient.addColorStop(0, 'rgba(56, 189, 248, 0.20)');
  humGradient.addColorStop(1, 'rgba(56, 189, 248, 0.0)');

  chart = new Chart(ctx, {
    type: 'line',
    data: {
      labels: [],
      datasets: [
        {
          label: 'Temperatura (°C)',
          data: [],
          borderColor: '#f87171',
          backgroundColor: tempGradient,
          borderWidth: 2,
          pointRadius: 3,
          pointBackgroundColor: '#f87171',
          pointBorderColor: '#0a0e1a',
          pointBorderWidth: 2,
          pointHoverRadius: 6,
          fill: true,
          tension: 0.4,
          yAxisID: 'yTemp',
        },
        {
          label: 'Umidade (%)',
          data: [],
          borderColor: '#38bdf8',
          backgroundColor: humGradient,
          borderWidth: 2,
          pointRadius: 3,
          pointBackgroundColor: '#38bdf8',
          pointBorderColor: '#0a0e1a',
          pointBorderWidth: 2,
          pointHoverRadius: 6,
          fill: true,
          tension: 0.4,
          yAxisID: 'yHum',
        }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      interaction: { intersect: false, mode: 'index' },
      plugins: {
        legend: {
          display: true,
          position: 'top',
          labels: {
            color: '#94a3b8',
            font: { size: 12, family: 'Inter' },
            usePointStyle: true,
            pointStyle: 'circle',
            padding: 20,
          }
        },
        tooltip: {
          backgroundColor: 'rgba(17, 24, 39, 0.95)',
          titleColor: '#f1f5f9',
          bodyColor: '#94a3b8',
          borderColor: 'rgba(255, 255, 255, 0.1)',
          borderWidth: 1,
          padding: 12,
          cornerRadius: 8,
          callbacks: {
            title: (items) => `Leitura #${items[0].dataIndex + 1}`,
          }
        }
      },
      scales: {
        x: {
          grid: { color: 'rgba(255,255,255,0.04)', drawBorder: false },
          ticks: { color: '#64748b', font: { size: 11 } },
        },
        yTemp: {
          type: 'linear',
          position: 'left',
          min: 0,
          max: 50,
          grid: { color: 'rgba(255,255,255,0.04)', drawBorder: false },
          ticks: {
            color: '#f87171',
            font: { size: 11 },
            callback: (v) => v + '°C',
          },
          title: { display: true, text: 'Temperatura', color: '#f87171', font: { size: 12 } }
        },
        yHum: {
          type: 'linear',
          position: 'right',
          min: 0,
          max: 100,
          grid: { drawOnChartArea: false },
          ticks: {
            color: '#38bdf8',
            font: { size: 11 },
            callback: (v) => v + '%',
          },
          title: { display: true, text: 'Umidade', color: '#38bdf8', font: { size: 12 } }
        }
      }
    }
  });
}

function updateChart(readings) {
  if (!chart) return;

  const labels = readings.map((_, i) => `#${i + 1}`);
  const temps = readings.map(r => parseFloat(r.soil_moisture_raw ?? 0));
  const hums = readings.map(r => parseFloat(r.soil_moisture_percent ?? 0));

  chart.data.labels = labels;
  chart.data.datasets[0].data = temps;
  chart.data.datasets[1].data = hums;
  chart.update('none');
}

// ── Temp Gauge (0–50°C) ──
function updateTempGauge(temp) {
  const maxTemp = 50;
  const pct = Math.min(Math.max(temp / maxTemp, 0), 1);
  const circumference = 235.6;
  const offset = circumference - (circumference * pct);

  const fill = document.getElementById('gaugeFillTemp');
  const text = document.getElementById('gaugeValueTemp');
  const status = document.getElementById('gaugeStatusTemp');

  fill.style.strokeDashoffset = offset;
  text.textContent = temp.toFixed(1);

  if (temp <= 25) {
    status.textContent = '🌿 Agradável';
    status.className = 'gauge-status good';
  } else if (temp <= 35) {
    status.textContent = '⚠️ Quente';
    status.className = 'gauge-status warning';
  } else {
    status.textContent = '🔴 Muito Quente';
    status.className = 'gauge-status critical';
  }
}

// ── Humidity Gauge (0–100%) ──
function updateHumGauge(hum) {
  const pct = Math.min(Math.max(hum / 100, 0), 1);
  const circumference = 235.6;
  const offset = circumference - (circumference * pct);

  const fill = document.getElementById('gaugeFillHum');
  const text = document.getElementById('gaugeValueHum');
  const status = document.getElementById('gaugeStatusHum');

  fill.style.strokeDashoffset = offset;
  text.textContent = hum.toFixed(1);

  if (hum >= 40 && hum <= 70) {
    status.textContent = '💧 Ideal';
    status.className = 'gauge-status good';
  } else if (hum >= 25 && hum <= 80) {
    status.textContent = '⚠️ Atenção';
    status.className = 'gauge-status warning';
  } else {
    status.textContent = '🔴 Fora do Ideal';
    status.className = 'gauge-status critical';
  }
}

// ── Table ──
function updateTable(readings) {
  const tbody = document.getElementById('readingsTableBody');
  const badge = document.getElementById('tableBadge');
  badge.textContent = `${readings.length} registros`;

  const recent = readings.slice(-20).reverse();

  tbody.innerHTML = recent.map(r => {
    const temp = parseFloat(r.soil_moisture_raw ?? 0);
    const hum = parseFloat(r.soil_moisture_percent ?? 0);
    const device = r.device_id ?? '—';
    const ts = r.timestamp ?? '—';

    let statusClass = 'good';
    let statusLabel = 'Normal';
    if (temp > 35) { statusClass = 'critical'; statusLabel = 'Quente'; }
    else if (temp > 25) { statusClass = 'warning'; statusLabel = 'Morno'; }

    return `
      <tr>
        <td>${device}</td>
        <td>${ts}</td>
        <td>
          <div class="td-moisture">
            <div class="moisture-bar-bg">
              <div class="moisture-bar-fill temp-bar" style="width:${Math.min(temp / 50 * 100, 100)}%"></div>
            </div>
            ${temp.toFixed(1)}°C
          </div>
        </td>
        <td>
          <div class="td-moisture">
            <div class="moisture-bar-bg">
              <div class="moisture-bar-fill" style="width:${hum}%"></div>
            </div>
            ${hum.toFixed(1)}%
          </div>
        </td>
        <td><span class="badge ${statusClass}">● ${statusLabel}</span></td>
      </tr>
    `;
  }).join('');
}

// ── Status indicator ──
function setStatus(online) {
  const dot = document.getElementById('statusDot');
  const text = document.getElementById('statusText');

  if (online) {
    dot.classList.remove('offline');
    text.textContent = 'API Conectada';
  } else {
    dot.classList.add('offline');
    text.textContent = 'Sem conexão';
  }
}

// ── Error state ──
function showError(message) {
  const root = document.getElementById('appRoot');
  if (document.getElementById('metricTemp')) return;

  root.innerHTML = `
    <div class="error-container">
      <div class="error-icon">⚠️</div>
      <div class="error-title">Erro ao conectar na API</div>
      <div class="error-message">
        Certifique-se de que o servidor está rodando em <strong>${API_URL}</strong>
        <br/><br/><code>${message}</code>
      </div>
      <button class="btn-retry" onclick="fetchData()">Tentar novamente</button>
    </div>
  `;
}

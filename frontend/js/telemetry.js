/* Telemetry — Gecko histogram/telemetry CSV/Excel parsing + time series */

let telemetryState = {
  source: 'upload',
  resample: '',
  agg: 'mean',
  smooth: false,
  data: null,
  columns: [],
};

window.addEventListener('DOMContentLoaded', () => {
  const src = document.getElementById('telemetry-source');
  if (src) src.addEventListener('change', e => { telemetryState.source = e.target.value; });
  const res = document.getElementById('telemetry-resample');
  if (res) res.addEventListener('change', e => { telemetryState.resample = e.target.value; });
  const agg = document.getElementById('telemetry-agg');
  if (agg) agg.addEventListener('change', e => { telemetryState.agg = e.target.value; });
  const sm = document.getElementById('telemetry-smooth');
  if (sm) sm.addEventListener('change', e => { telemetryState.smooth = e.target.checked; });
});

function handleTelemetryFile(file) {
  if (!file) return;
  const reader = new FileReader();
  reader.onload = e => parseTelemetryCsv(e.target.result, file.name);
  reader.readAsText(file);
}

function parseTelemetryCsv(text, filename) {
  const lines = text.split('\n').filter(l => l.trim() && !l.startsWith('#'));
  if (lines.length < 2) { showToast('CSV vacío o inválido', 'error'); return; }

  const headers = lines[0].split(',').map(h => h.trim());
  telemetryState.columns = headers;
  const rows = lines.slice(1).map(l => l.split(',').map(v => v.trim()));

  telemetryState.data = { headers, rows, filename };
  showToast(` ${rows.length} filas cargadas`, 'success');
}

async function loadTelemetry() {
  const plotEl = document.getElementById('telemetry-plot');
  if (!telemetryState.data) {
    showToast('Sube un archivo primero', 'warning'); return;
  }
  const { headers, rows } = telemetryState.data;
  if (!rows.length) return;

  // Auto-detect datetime column
  const dateCol = headers.findIndex(h => /date|time/i.test(h));
  const numCols = headers.filter((_, i) => {
    const vals = rows.slice(0, 10).map(r => parseFloat(r[i]));
    return vals.filter(v => !isNaN(v)).length > 5;
  });

  if (numCols.length === 0) { showToast('Sin columnas numéricas', 'error'); return; }

  const plotData = numCols.slice(0, 4).map((colIdx, i) => {
    const col = headers[colIdx];
    const ys = rows.map(r => parseFloat(r[colIdx]) || 0);
    const xs = rows.map((_, j) => j);
    return {
      x: xs, y: ys,
      mode: 'lines',
      name: col,
      line: { color: colorForIdx(i), width: 1.5 },
    };
  });

  if (plotEl) {
    plotEl.innerHTML = '';
    Plotly.newPlot(plotEl, plotData, {
      title: `Telemetría — ${telemetryState.data.filename}`,
      xaxis: { title: 'Índice', color: '#e0e0e0' },
      yaxis: { title: 'Valor', color: '#e0e0e0' },
      template: 'plotly_dark', paper_bgcolor: 'rgba(0,0,0,0)', plot_bgcolor: 'rgba(0,0,0,0)',
      margin: { t: 50, r: 20, b: 50, l: 70 },
      legend: { orientation: 'h', y: 1.1 },
    }, { responsive: true });
  }

  // Stats
  const statsEl = document.getElementById('telemetry-stats');
  if (statsEl && numCols.length > 0) {
    let html = '<table class="table-wrap"><thead><tr><th>Variable</th><th>Mín</th><th>Media</th><th>Máx</th></tr></thead><tbody>';
    numCols.slice(0, 4).forEach((colIdx, i) => {
      const col = headers[colIdx];
      const vals = rows.map(r => parseFloat(r[colIdx]) || 0);
      const mean = vals.reduce((a, b) => a + b, 0) / vals.length;
      html += `<tr><td>${col}</td><td>${Math.min(...vals).toFixed(2)}</td><td>${mean.toFixed(2)}</td><td>${Math.max(...vals).toFixed(2)}</td></tr>`;
    });
    html += '</tbody></table>';
    statsEl.innerHTML = html;
    statsEl.classList.remove('hidden');
  }
}

function colorForIdx(i) {
  const colors = ['#74b9ff', '#55efc4', '#a29bfe', '#ffeaa7', '#ff6b6b'];
  return colors[i % colors.length];
}

window.handleTelemetryFile = handleTelemetryFile;
window.loadTelemetry = loadTelemetry;
window.showToast = showToast;
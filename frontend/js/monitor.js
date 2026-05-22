/* Real-time PGA/PGV Monitor — uses dataset IMs instead of fake data */

let monitorState = {
  currentDataset: null,
  pgaThreshold: 50,
  pgvThreshold: 5,
  interval: null,
  currentData: [],
};

window.addEventListener('DOMContentLoaded', () => {
  const sel = document.getElementById('monitor-dataset');
  if (sel) sel.addEventListener('change', e => { monitorState.currentDataset = e.target.value; });
  const thr = document.getElementById('monitor-threshold');
  if (thr) thr.addEventListener('change', e => { monitorState.pgaThreshold = parseFloat(e.target.value); });
});

async function startMonitor() {
  const name = monitorState.currentDataset || document.getElementById('monitor-dataset')?.value;
  if (!name) { showToast('Selecciona un dataset', 'warning'); return; }
  if (monitorState.interval) clearInterval(monitorState.interval);

  try {
    const result = await api.datasetIms(name);
    const imsList = result.ims || [];
    if (!imsList.length) { showToast('Sin IMs disponibles', 'warning'); return; }

    monitorState.currentData = imsList.map((ims, i) => ({
      idx: i,
      pga: ims.pga_cms2 || 0,
      pgv: ims.pgv_cms || 0,
      arias: ims.arias_ms || 0,
      d5_75: ims.d5_75_s || 0,
      label: `Trace ${i}`,
    }));

    renderMonitorPlot();
    showToast(` Monitor activo — ${imsList.length} trazas`, 'success');
  } catch (err) {
    showToast(`Error: ${err.message}`, 'error');
  }
}

function renderMonitorPlot() {
  const plotEl = document.getElementById('monitor-plot');
  if (!plotEl || !monitorState.currentData.length) return;

  const sorted = [...monitorState.currentData].sort((a, b) => b.pga - a.pga);
  const pgaColors = sorted.map(d => {
    if (d.pga >= monitorState.pgaThreshold * 2) return '#ff6b6b';
    if (d.pga >= monitorState.pgaThreshold) return '#fdcb6e';
    return '#55efc4';
  });

  const traces_data = [{
    x: sorted.map((_, i) => i),
    y: sorted.map(d => d.pga),
    type: 'bar',
    marker: { color: pgaColors },
    name: 'PGA (cm/s²)',
    text: sorted.map(d => d.pga.toFixed(2)),
    textposition: 'outside',
    textfont: { size: 9, color: '#e0e0e0' },
  }];

  const layout = {
    title: 'PGA por traza',
    xaxis: { title: 'Traza (ordenada por PGA)', color: '#e0e0e0' },
    yaxis: { title: 'PGA (cm/s²)', color: '#e0e0e0' },
    template: 'plotly_dark',
    paper_bgcolor: 'rgba(0,0,0,0)',
    plot_bgcolor: 'rgba(0,0,0,0)',
    margin: { t: 50, r: 20, b: 50, l: 70 },
    shapes: [{
      type: 'line', x0: -0.5, x1: sorted.length - 0.5,
      y0: monitorState.pgaThreshold, y1: monitorState.pgaThreshold,
      line: { color: '#fdcb6e', width: 2, dash: 'dash' },
    }],
  };

  plotEl.innerHTML = '';
  Plotly.newPlot(plotEl, traces_data, layout, { responsive: true });

  // Generate alerts for exceeding thresholds
  const alertsEl = document.getElementById('monitor-alerts');
  if (alertsEl) {
    let alertsHtml = '';
    sorted.slice(0, 5).forEach(d => {
      if (d.pga >= monitorState.pgaThreshold) {
        const level = d.pga >= monitorState.pgaThreshold * 2 ? 'critical' : 'warning';
        alertsHtml += `<div class="alert-item ${level}">
          <strong>${d.label}</strong>: PGA=${d.pga.toFixed(2)} cm/s² — ${level.toUpperCase()}
        </div>`;
      }
    });
    alertsEl.innerHTML = alertsHtml || '<p class="text-muted">Sin alertas</p>';
  }
}

function stopMonitor() {
  if (monitorState.interval) {
    clearInterval(monitorState.interval);
    monitorState.interval = null;
  }
  showToast('Monitor detenido', 'info');
}

window.startMonitor = startMonitor;
window.stopMonitor = stopMonitor;
window.showToast = showToast;
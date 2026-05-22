/* ── Location Module ───────────────────────────────────────────────────────── */

let LOC = { currentDataset: null, result: null };

function initLocation() {
  const sel = document.getElementById('location-dataset');
  if (sel) sel.addEventListener('change', e => { LOC.currentDataset = e.target.value; });
  document.getElementById('location-run')?.addEventListener('click', runLocation);
}

async function runLocation() {
  const name = LOC.currentDataset || document.getElementById('location-dataset')?.value;
  if (!name) { showToast('Selecciona un dataset', 'warning'); return; }
  const plotEl = document.getElementById('location-plot');
  if (plotEl) plotEl.innerHTML = '<div class="plot-loading">Localizando...</div>';

  const vp   = parseFloat(document.getElementById('location-vp')?.value || 6.0);
  const vs   = parseFloat(document.getElementById('location-vs')?.value || 3.46);
  const gMin = parseFloat(document.getElementById('location-grid-min')?.value || -50);
  const gMax = parseFloat(document.getElementById('location-grid-max')?.value || 50);
  const gStep = parseFloat(document.getElementById('location-grid-step')?.value || 2.0);

  try {
    LOC.result = await api.datasetLocation(name, { vp, vs, gridMin: gMin, gridMax: gMax, gridStep: gStep });
    renderLocationResult();
    showToast('Localización completada', 'success');
  } catch (err) {
    showToast(`Error: ${err.message}`, 'error');
    if (plotEl) plotEl.innerHTML = `<div class="plot-empty"><p>${err.message}</p></div>`;
  }
}

function renderLocationResult() {
  const r = LOC.result;
  if (!r) return;

  const plotEl = document.getElementById('location-plot');
  if (plotEl && r.plot) {
    plotEl.innerHTML = '';
    Plotly.newPlot(plotEl, r.plot.data, Object.assign({}, r.plot.layout || {}, { template: 'plotly_dark', paper_bgcolor: 'rgba(0,0,0,0)', plot_bgcolor: 'rgba(0,0,0,0)' }), { responsive: true });
  }

  const infoEl = document.getElementById('location-info');
  if (infoEl) {
    const lat = r.latitude != null ? r.latitude.toFixed(4) : '—';
    const lon = r.longitude != null ? r.longitude.toFixed(4) : '—';
    const dep = r.depth_km != null ? r.depth_km.toFixed(1) : '—';
    infoEl.innerHTML = `
      <div class="info-box">
        <strong>Epicentro</strong>: ${lat}°, ${lon}° &nbsp;|&nbsp;
        <strong>Profundidad</strong>: ${dep} km &nbsp;|&nbsp;
        <strong>RMSE</strong>: ${r.rmse_km != null ? r.rmse_km.toFixed(2) + ' km' : '—'}
      </div>`;
  }
}

async function runLocationDemo() {
  const plotEl = document.getElementById('location-plot');
  if (plotEl) plotEl.innerHTML = '<div class="plot-loading">Cargando demo...</div>';
  try {
    const d = await api.locationDemo();
    if (plotEl && d.plot) {
      plotEl.innerHTML = '';
      Plotly.newPlot(plotEl, d.plot.data, Object.assign({}, d.plot.layout || {}, { template: 'plotly_dark', paper_bgcolor: 'rgba(0,0,0,0)', plot_bgcolor: 'rgba(0,0,0,0)' }), { responsive: true });
    }
  } catch (err) { showToast(`Error: ${err.message}`, 'error'); }
}

window.initLocation = initLocation;
window.runLocation = runLocation;
window.runLocationDemo = runLocationDemo;
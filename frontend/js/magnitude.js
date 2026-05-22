/* ── Magnitude Module ──────────────────────────────────────────────────────── */

let M = { currentDataset: null, currentTraceIdx: 0, result: null };

function initMagnitude() {
  const sel = document.getElementById('magnitude-dataset');
  if (sel) sel.addEventListener('change', e => { M.currentDataset = e.target.value; loadMagnitude(); });
  const trSel = document.getElementById('magnitude-trace');
  if (trSel) trSel.addEventListener('change', e => { M.currentTraceIdx = parseInt(e.target.value); computeMagnitude(); });
}

async function loadMagnitude() {
  const name = M.currentDataset || document.getElementById('magnitude-dataset')?.value;
  if (!name) return;
  try {
    const info = await api.datasetInfo(name);
    const sel = document.getElementById('magnitude-trace');
    if (sel) {
      sel.innerHTML = (info.traces || []).map((t, i) =>
        `<option value="${i}">${i}: ${t.station}.${t.channel}</option>`
      ).join('');
    }
    M.currentTraceIdx = 0;
    computeMagnitude();
  } catch (err) { showToast(`Error: ${err.message}`, 'error'); }
}

async function computeMagnitude() {
  const name = M.currentDataset || document.getElementById('magnitude-dataset')?.value;
  if (!name) return;
  const plotEl = document.getElementById('magnitude-plot');
  if (plotEl) plotEl.innerHTML = '<div class="plot-loading">Calculando magnitud...</div>';
  try {
    M.result = await api.datasetMagnitude(name, M.currentTraceIdx);
    renderMagnitudeResult();
  } catch (err) {
    showToast(`Error: ${err.message}`, 'error');
    if (plotEl) plotEl.innerHTML = `<div class="plot-empty"><p>${err.message}</p></div>`;
  }
}

function renderMagnitudeResult() {
  const r = M.result;
  if (!r) return;

  const plotEl = document.getElementById('magnitude-plot');
  if (plotEl) {
    const traces = r.plot?.data || [];
    if (traces.length) {
      plotEl.innerHTML = '';
      Plotly.newPlot(plotEl, traces, Object.assign({}, r.plot?.layout || {}, { template: 'plotly_dark', paper_bgcolor: 'rgba(0,0,0,0)', plot_bgcolor: 'rgba(0,0,0,0)' }), { responsive: true });
    } else {
      plotEl.innerHTML = '<div class="plot-empty"><p>Sin datos de magnitud</p></div>';
    }
  }

  const infoEl = document.getElementById('magnitude-info');
  if (infoEl) {
    const interp = interpretMagnitude(r.ml);
    infoEl.innerHTML = `
      <div class="im-card">
        <div class="im-value">ML = ${r.ml != null ? r.ml.toFixed(2) : '—'}</div>
        <div class="im-subtitle">${interp.label}</div>
        <div class="im-bars">
          <div class="im-bar-label">Intensidad (MMI)</div>
          ${renderMmiBar(interp.mmi)}
        </div>
        <div class="im-details">
          <span>Distancia: ${r.distance_km != null ? r.distance_km.toFixed(1) + ' km' : '—'}</span>
          <span>Amplificación: ${r.amplification != null ? r.amplification.toFixed(1) : '—'}</span>
        </div>
      </div>`;
  }
}

function interpretMagnitude(ml) {
  if (ml == null) return { label: 'Sin dato', mmi: 0 };
  if (ml < 3) return { label: 'Micro-terremoto (no sentido)', mmi: 1 + ml * 0.5 };
  if (ml < 4) return { label: 'Menor (a menudo sentido)', mmi: 4 };
  if (ml < 5) return { label: 'Ligero (sentido por muchas personas)', mmi: 5 };
  if (ml < 6) return { label: 'Moderado (algún daño)', mmi: 6 };
  if (ml < 7) return { label: 'Fuerte (daño significativo)', mmi: 7 };
  return { label: 'Mayor (destrucción)', mmi: 8 + Math.min(ml - 7, 2) };
}

function renderMmiBar(mmi) {
  const pct = Math.min((mmi / 10) * 100, 100);
  const color = mmi < 4 ? '#55efc4' : mmi < 6 ? '#ffeaa7' : mmi < 7 ? '#fdcb6e' : '#ff6b6b';
  return `<div style="background:#1a1a3e;border-radius:4px;height:20px;width:100%;overflow:hidden;">
    <div style="background:${color};height:100%;width:${pct}%;transition:width 0.5s;border-radius:4px;"></div>
  </div><div style="font-size:11px;color:#aaa;text-align:right;margin-top:2px;">MMI ≈ ${mmi.toFixed(1)}</div>`;
}

window.initMagnitude = initMagnitude;
window.computeMagnitude = computeMagnitude;
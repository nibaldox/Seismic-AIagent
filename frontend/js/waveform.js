/* Waveform Viewer — Unified DB: shows V0/V1 data, runs corrections, QC, picks */

let W = {
  currentDataset: null,
  currentTraceIdx: 0,
  traces: [],

  // Filter controls
  filterType: 'bandpass',
  freqmin: 0.5,
  freqmax: 25.0,

  // Baseline controls
  baselineMethod: 'linear',
  polyOrder: 2,
};

window.addEventListener('DOMContentLoaded', () => {
  bind('waveform-dataset', e => { W.currentDataset = e.target.value; W.loadTraces(); });
  bind('waveform-component', e => { W.currentComponent = e.target.value; W.show(); });
  bind('waveform-filter', e => { W.filterType = e.target.value; });
  bind('waveform-freqmin', e => { W.freqmin = parseFloat(e.target.value); });
  bind('waveform-freqmax', e => { W.freqmax = parseFloat(e.target.value); });
  bind('waveform-baseline', e => { W.baselineMethod = e.target.value; });
  bind('waveform-trace', e => { W.currentTraceIdx = parseInt(e.target.value); W.show(); });
});

function bind(id, handler) {
  const el = document.getElementById(id);
  if (el) el.addEventListener('change', handler);
  return el;
}

async function loadTraces() {
  const name = W.currentDataset || document.getElementById('waveform-dataset')?.value;
  if (!name) return;
  const plotEl = document.getElementById('waveform-plot');
  if (plotEl) plotEl.innerHTML = '<div class="plot-loading">Cargando trazas...</div>';

  try {
    const info = await api.datasetInfo(name);
    W.traces = info.traces || [];
    W.currentTraceIdx = 0;

    // Populate trace selector
    const sel = document.getElementById('waveform-trace');
    if (sel) {
      sel.innerHTML = W.traces.map((t, i) =>
        `<option value="${i}">${i}: ${t.station}.${t.channel}${t.v1_filter_type ? ` [${t.v1_filter_type}]` : ''}</option>`
      ).join('');
      sel.addEventListener('change', e => { W.currentTraceIdx = parseInt(e.target.value); W.show(); });
    }

    updateWaveformImPanel();
    W.show();
    showToast(`${W.traces.length} trazas cargadas`, 'success');
  } catch (err) {
    showToast(`Error: ${err.message}`, 'error');
    if (plotEl) plotEl.innerHTML = `<div class="plot-empty"><p>${err.message}</p></div>`;
  }
}

function show() {
  const comp = document.getElementById('waveform-component')?.value || 'all';
  const filtered = W.traces.filter(tr => {
    if (comp === 'all') return true;
    const ch = (tr.channel || '').toUpperCase();
    if (comp === 'Z') return ch.endsWith('Z');
    if (comp === 'N') return ch.endsWith('N') || ch.includes('1');
    if (comp === 'E') return ch.endsWith('E') || ch.includes('2');
    return true;
  });

  if (!filtered.length) {
    const plotEl = document.getElementById('waveform-plot');
    if (plotEl) plotEl.innerHTML = '<div class="plot-empty"><p>Sin datos para el componente</p></div>';
    return;
  }

  const plotData = filtered.map((tr, i) => {
    const t = (tr.time || []).map(v => parseFloat(v));
    const y = (tr.data || []).map(v => parseFloat(v));
    const dirty = tr.ims_dirty;
    return {
      x: t, y,
      mode: 'lines',
      name: `${tr.station}.${tr.channel}${dirty ? ' ⚠️' : ''}`,
      line: { color: colorForIdx(i), width: 1.5 },
    };
  });

  // Add pick markers
  filtered.forEach((tr, i) => {
    const origIdx = W.traces.indexOf(tr);
    (tr.picks || []).forEach(pk => {
      if (pk.time_rel == null) return;
      const isP = (pk.phase || '').toUpperCase().startsWith('P');
      plotData.push({
        x: [parseFloat(pk.time_rel)], y: [0],
        mode: 'markers+text',
        marker: { symbol: 'triangle-up', size: 10, color: isP ? '#55efc4' : '#ff6b6b' },
        text: [pk.phase || (isP ? 'P' : 'S')],
        textposition: 'top center', textfont: { size: 9, color: isP ? '#55efc4' : '#ff6b6b' },
        showlegend: false,
        name: `${tr.station}.${tr.channel} ${pk.phase || ''}`,
      });
    });
  });

  const plotEl = document.getElementById('waveform-plot');
  if (plotEl) plotEl.innerHTML = '';
  Plotly.newPlot(plotEl, plotData, {
    title: `Waveforms — ${W.currentDataset} (${filtered.length} trazas)`,
    xaxis: { title: 'Tiempo (s)', color: '#e0e0e0' },
    yaxis: { title: 'Amplitud (counts)', color: '#e0e0e0' },
    template: 'plotly_dark', paper_bgcolor: 'rgba(0,0,0,0)', plot_bgcolor: 'rgba(0,0,0,0)',
    margin: { t: 50, r: 20, b: 50, l: 70 },
    legend: { orientation: 'h', y: 1.1 },
  }, { responsive: true });

  updateWaveformImPanel();
}

function updateWaveformImPanel() {
  const infoEl = document.getElementById('waveform-info');
  if (!infoEl || !W.traces.length) return;

  let html = '<table class="table-wrap"><thead><tr>' +
    '<th>#</th><th>Station</th><th>Ch</th>' +
    '<th>PGA</th><th>PGV</th><th>Veredicto</th>' +
    '<th>Filtro</th><th>Dirty</th></tr></thead><tbody>';

  W.traces.forEach((tr, i) => {
    const ims = tr.ims || {};
    const v = tr.ims_verdict || '?';
    const vcls = v === 'RECHAZADO' ? 'verdict-reject' : v === 'CONDICIONADO' ? 'verdict-cond' : v === 'ACEPTADO' ? 'verdict-ok' : '';
    html += `<tr>
      <td>${i}</td>
      <td>${tr.station || '—'}</td>
      <td>${tr.channel || '—'}</td>
      <td>${ims.pga_cms2 ? ims.pga_cms2.toFixed(2) : '—'}</td>
      <td>${ims.pgv_cms ? ims.pgv_cms.toFixed(3) : '—'}</td>
      <td class="${vcls}">${v}</td>
      <td>${tr.v1_filter_type || tr.v1_baseline_method || '—'}</td>
      <td>${tr.ims_dirty ? '⚠️ SÍ' : '—'}</td>
    </tr>`;
  });
  html += '</tbody></table>';
  infoEl.innerHTML = html;
  infoEl.classList.remove('hidden');
}

// ── Filter ───────────────────────────────────────────────────────────────────

async function applyWaveformFilter() {
  const name = W.currentDataset || document.getElementById('waveform-dataset')?.value;
  if (!name) { showToast('Selecciona un dataset', 'warning'); return; }
  try {
    const result = await api.datasetCorrect(name, {
      traceIdx: W.currentTraceIdx,
      correctionType: 'filter',
      filterType: W.filterType,
      freqmin: W.freqmin,
      freqmax: W.freqmax,
    });
    showToast(`Filtro aplicado — IMs pendientes de recalcular`, 'success');
    await loadTraces();
  } catch (err) {
    showToast(`Error: ${err.message}`, 'error');
  }
}

// ── Baseline ────────────────────────────────────────────────────────────────

async function applyWaveformBaseline() {
  const name = W.currentDataset || document.getElementById('waveform-dataset')?.value;
  if (!name) { showToast('Selecciona un dataset', 'warning'); return; }
  try {
    const result = await api.datasetCorrect(name, {
      traceIdx: W.currentTraceIdx,
      correctionType: 'baseline',
      baselineMethod: W.baselineMethod,
    });
    showToast(`Baseline corregido — recalcula IMs`, 'success');
    await loadTraces();
  } catch (err) {
    showToast(`Error: ${err.message}`, 'error');
  }
}

// ── Reset to V0 ───────────────────────────────────────────────────────────────

async function resetWaveformTrace() {
  const name = W.currentDataset || document.getElementById('waveform-dataset')?.value;
  if (!name) return;
  try {
    await api.datasetReset(name, W.currentTraceIdx);
    showToast('Trace reseteado a V0', 'info');
    await loadTraces();
  } catch (err) {
    showToast(`Error: ${err.message}`, 'error');
  }
}

// ── Picks ────────────────────────────────────────────────────────────────────

async function runWaveformPicks() {
  const name = W.currentDataset || document.getElementById('waveform-dataset')?.value;
  if (!name) return;
  try {
    const result = await api.datasetPicks(name, W.currentTraceIdx, true);
    showToast(`${result.count} picks detectados`, 'success');
    await loadTraces();
  } catch (err) {
    showToast(`Error: ${err.message}`, 'error');
  }
}

// ── QC ───────────────────────────────────────────────────────────────────────

async function runWaveformQc() {
  const name = W.currentDataset || document.getElementById('waveform-dataset')?.value;
  if (!name) return;
  try {
    const result = await api.datasetQc(name, null, true);
    const qcEl = document.getElementById('waveform-qc-results');
    if (qcEl) {
      let html = '<table class="table-wrap"><thead><tr>' +
        '<th>#</th><th>Station</th><th>Veredicto</th><th>SNR</th><th>Clipping</th><th>Baseline</th><th>Gaps</th></tr></thead><tbody>';
      result.qc_results?.forEach(r => {
        const v = r.qc?.verdict || '?';
        const vcls = v === 'RECHAZADO' ? 'verdict-reject' : v === 'CONDICIONADO' ? 'verdict-cond' : v === 'ACEPTADO' ? 'verdict-ok' : '';
        html += `<tr><td>${r.trace_idx}</td><td>${r.station}</td><td class="${vcls}">${v}</td>` +
          `<td>${r.qc?.snr_db != null ? r.qc.snr_db.toFixed(1) : '—'}</td>` +
          `<td>${r.qc?.clip_ratio != null ? (r.qc.clip_ratio * 100).toFixed(1) : '—'}%</td>` +
          `<td>${r.qc?.baseline_drift != null ? r.qc.baseline_drift.toFixed(2) : '—'}%</td>` +
          `<td>${r.qc?.n_gaps || 0}</td></tr>`;
      });
      html += '</tbody></table>';
      qcEl.innerHTML = html;
    }
    showToast(`${result.count} trazas con QC`, 'success');
  } catch (err) {
    showToast(`Error: ${err.message}`, 'error');
  }
}

// ── IMs recompute ─────────────────────────────────────────────────────────────

async function recomputeWaveformIms() {
  const name = W.currentDataset || document.getElementById('waveform-dataset')?.value;
  if (!name) return;
  try {
    const result = await api.datasetIms(name, null, true);
    showToast(`IMs recalculados para ${result.count} trazas`, 'success');
    await loadTraces();
  } catch (err) {
    showToast(`Error: ${err.message}`, 'error');
  }
}

function colorForIdx(i) {
  const colors = ['#74b9ff', '#55efc4', '#a29bfe', '#ffeaa7', '#ff6b6b', '#fd79a8', '#00cec9', '#fdcb6e'];
  return colors[i % colors.length];
}

function showToast(message, type = 'info') {
  const container = document.getElementById('toast-container') || (() => {
    const c = document.createElement('div');
    c.id = 'toast-container';
    c.style.cssText = 'position:fixed;bottom:20px;right:20px;z-index:9999;display:flex;flex-direction:column;gap:8px;';
    document.body.appendChild(c);
    return c;
  })();
  const toast = document.createElement('div');
  toast.style.cssText = `padding:10px 16px;border-radius:8px;font-size:14px;background:#1a1a3e;color:#e0e0e0;border-left:4px solid ${type==='error'?'#ff6b6b':type==='success'?'#55efc4':'#74b9ff'}`;
  toast.textContent = message;
  container.appendChild(toast);
  setTimeout(() => { toast.style.opacity = '0'; setTimeout(() => toast.remove(), 300); }, 3000);
}

// Expose globally
window.loadWaveform = loadTraces;  // backwards compat — loadWaveform triggers full load
window.applyWaveformFilter = applyWaveformFilter;
window.applyWaveformBaseline = applyWaveformBaseline;
window.resetWaveformTrace = resetWaveformTrace;
window.runWaveformPicks = runWaveformPicks;
window.runWaveformQc = runWaveformQc;
window.recomputeWaveformIms = recomputeWaveformIms;
window.showToast = showToast;
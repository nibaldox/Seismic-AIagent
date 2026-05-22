/* ── Quality Control Module ────────────────────────────────────────────────── */

let QC = { currentDataset: null, results: [] };

function initQc() {
  const sel = document.getElementById('qc-dataset');
  if (sel) sel.addEventListener('change', e => { QC.currentDataset = e.target.value; });
  document.getElementById('qc-run')?.addEventListener('click', runQc);
  document.getElementById('qc-export')?.addEventListener('click', exportQc);
}

async function runQc() {
  const name = QC.currentDataset || document.getElementById('qc-dataset')?.value;
  if (!name) { showToast('Selecciona un dataset', 'warning'); return; }
  const plotEl = document.getElementById('qc-plot');
  if (plotEl) plotEl.innerHTML = '<div class="plot-loading">Corriendo QC...</div>';
  try {
    const result = await api.datasetQc(name, null, true);
    QC.results = result.qc_results || [];
    renderQcTable();
    showToast(`${QC.results.length} trazas analizadas`, 'success');
  } catch (err) {
    showToast(`Error: ${err.message}`, 'error');
    if (plotEl) plotEl.innerHTML = `<div class="plot-empty"><p>${err.message}</p></div>`;
  }
}

function renderQcTable() {
  const el = document.getElementById('qc-table');
  if (!el || !QC.results.length) return;
  el.innerHTML = `<table class="table-wrap">
    <thead><tr>
      <th>#</th><th>Station</th><th>Veredicto</th>
      <th>SNR (dB)</th><th>Clipping (%)</th>
      <th>Baseline Drift (%)</th><th>Gaps</th>
      <th>Sta/Lta</th><th>Comments</th>
    </tr></thead><tbody>
    ${QC.results.map(r => {
      const v = r.qc?.verdict || '?';
      const vcls = v === 'RECHAZADO' ? 'verdict-reject' : v === 'CONDICIONADO' ? 'verdict-cond' : v === 'ACEPTADO' ? 'verdict-ok' : '';
      return `<tr>
        <td>${r.trace_idx}</td>
        <td>${r.station || '—'}</td>
        <td class="${vcls}">${v}</td>
        <td>${r.qc?.snr_db != null ? r.qc.snr_db.toFixed(1) : '—'}</td>
        <td>${r.qc?.clip_ratio != null ? (r.qc.clip_ratio * 100).toFixed(1) : '—'}</td>
        <td>${r.qc?.baseline_drift != null ? r.qc.baseline_drift.toFixed(2) : '—'}</td>
        <td>${r.qc?.n_gaps || 0}</td>
        <td>${r.qc?.sta_lta != null ? r.qc.sta_lta.toFixed(2) : '—'}</td>
        <td>${(r.qc?.comments || []).join(', ') || '—'}</td>
      </tr>`;
    }).join('')}
  </tbody></table>`;
  document.getElementById('qc-table').classList.remove('hidden');
}

async function exportQc() {
  if (!QC.results.length) { showToast('No hay resultados para exportar', 'warning'); return; }
  const name = QC.currentDataset || document.getElementById('qc-dataset')?.value;
  try {
    const blob = await api.reportExcel(name);
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a'); a.href = url; a.download = `${name}_qc.xlsx`; a.click();
    URL.revokeObjectURL(url);
  } catch (err) { showToast(`Export failed: ${err.message}`, 'error'); }
}

window.initQc = initQc;
window.runQc = runQc;
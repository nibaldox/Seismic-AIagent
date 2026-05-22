/* File Upload — parallel upload, validation, progress tracking */

const SUPPORTED_EXTENSIONS = ['.ms', '.mseed', '.sac', '.seg2', '.sg2', '.suds', '.bin'];

window.addEventListener('DOMContentLoaded', () => {
  const zone = document.getElementById('upload-zone');
  const input = document.getElementById('file-input');

  if (zone && input) {
    zone.addEventListener('click', () => input.click());
    zone.addEventListener('dragover', e => {
      e.preventDefault(); zone.classList.add('dragover');
    });
    zone.addEventListener('dragleave', () => zone.classList.remove('dragover'));
    zone.addEventListener('drop', e => {
      e.preventDefault(); zone.classList.remove('dragover');
      handleFiles(e.dataTransfer.files);
    });
    input.addEventListener('change', () => handleFiles(input.files));
  }
});

async function handleFiles(fileList) {
  const files = Array.from(fileList).slice(0, 20);
  if (!files.length) return;

  const progressEl = document.getElementById('upload-progress');
  const resultsEl = document.getElementById('upload-results');
  const fillEl = document.getElementById('progress-fill');
  const textEl = document.getElementById('progress-text');
  const pctEl = document.getElementById('progress-percent');

  if (progressEl) progressEl.classList.remove('hidden');
  if (resultsEl) resultsEl.innerHTML = '';
  window._uploadResults = [];

  for (let i = 0; i < files.length; i++) {
    const file = files[i];
    if (textEl) textEl.textContent = `${file.name}...`;
    if (pctEl) pctEl.textContent = `${Math.round((i / files.length) * 100)}%`;
    if (fillEl) fillEl.style.width = `${(i / files.length) * 100}%`;

    try {
      const result = await api.analyze(file);
      window._uploadResults.push(result);
      if (fillEl) fillEl.style.width = `${((i + 1) / files.length) * 100}%`;
      if (pctEl) pctEl.textContent = `${Math.round(((i + 1) / files.length) * 100)}%`;
    } catch (err) {
      window._uploadResults.push({ filename: file.name, error: err.message });
    }
  }

  if (textEl) textEl.textContent = 'Completo';
  if (progressEl) setTimeout(() => progressEl.classList.add('hidden'), 1500);

  if (resultsEl) renderResults(window._uploadResults);
  updateDashboardFromUpload(window._uploadResults);

  // Reload dataset selectors
  if (window.populateDatasetSelectors) window.populateDatasetSelectors();
}

function renderResults(results) {
  const container = document.getElementById('result-traces');
  if (!container) return;

  let html = '';
  results.forEach(r => {
    if (r.error) {
      html += `<div class="card" style="border-left:4px solid #ff6b6b"><p><strong>${r.filename}</strong>: ${r.error}</p></div>`;
      return;
    }
    const n = r.n_traces || 0;
    html += `<div class="card">
      <h4>${r.filename}</h4>
      <p>${r.format} · ${n} trazas</p>
      <div class="trace-detail">`;
    (r.traces || []).forEach(tr => {
      const ims = tr.ims || {};
      html += `<div class="trace-card">
        <span class="trace-station">${tr.station}.${tr.channel}</span>
        <span>PGA: ${ims.pga_cms2 ? ims.pga_cms2.toFixed(2) : '—'} cm/s²</span>
        <span>PGV: ${ims.pgv_cms ? ims.pgv_cms.toFixed(3) : '—'} cm/s</span>
        <span>Arias: ${ims.arias_ms ? ims.arias_ms.toFixed(4) : '—'} m/s</span>
      </div>`;
    });
    html += '</div></div>';
  });

  const summary = document.getElementById('result-summary');
  if (summary) {
    const totalTraces = results.reduce((a, r) => a + (r.n_traces || 0), 0);
    summary.innerHTML = `<p><strong>${results.length} archivos</strong> · <strong>${totalTraces} trazas</strong> procesadas</p>`;
  }
  container.innerHTML = html;
}

function updateDashboardFromUpload(results) {
  const totalFiles = results.length;
  const totalTraces = results.reduce((a, r) => a + (r.n_traces || 0), 0);
  const allIms = results.flatMap(r => (r.traces || []).map(tr => tr.ims || {}));
  const maxPga = allIms.length ? Math.max(...allIms.map(i => i.pga_cms2 || 0)) : 0;
  const totalPicks = results.reduce((a, r) => a + (r.traces || []).reduce((b, tr) => b + (tr.picks || []).length, 0), 0);

  const setEl = id => document.getElementById(id);
  const s = v => { const el = setEl(v); if (el) el.textContent = v.includes('pga') ? (v === 'stat-pga' ? maxPga.toFixed(2) : maxPga.toFixed(2)) : v; };
  const el = setEl('stat-files'); if (el) el.textContent = totalFiles;
  const el2 = setEl('stat-traces'); if (el2) el2.textContent = totalTraces;
  const el3 = setEl('stat-pga'); if (el3) el3.textContent = maxPga > 0 ? maxPga.toFixed(2) : '—';
  const el4 = setEl('stat-picks'); if (el4) el4.textContent = totalPicks;
  const el5 = setEl('active-dataset'); if (el5) el5.textContent = results[0]?.filename || 'Sin nombre';
}

window.handleFiles = handleFiles;
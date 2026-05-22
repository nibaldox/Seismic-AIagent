/* ── Report Module ─────────────────────────────────────────────────────────── */

let REP = { currentDataset: null };

function initReport() {
  const sel = document.getElementById('report-dataset');
  if (sel) sel.addEventListener('change', e => { REP.currentDataset = e.target.value; });
  document.getElementById('report-html-btn')?.addEventListener('click', showHtmlReport);
  document.getElementById('report-excel-btn')?.addEventListener('click', exportExcel);
}

async function showHtmlReport() {
  const name = REP.currentDataset || document.getElementById('report-dataset')?.value;
  if (!name) { showToast('Selecciona un dataset', 'warning'); return; }
  const el = document.getElementById('report-html-content');
  if (el) { el.innerHTML = '<div class="plot-loading">Generando reporte...</div>'; }
  try {
    const html = await api.reportHtml(name);
    if (el) {
      el.innerHTML = html;
      el.style.display = 'block';
    }
    showToast('Reporte HTML generado', 'success');
  } catch (err) {
    showToast(`Error: ${err.message}`, 'error');
    if (el) el.innerHTML = `<p>Error: ${err.message}</p>`;
  }
}

async function exportExcel() {
  const name = REP.currentDataset || document.getElementById('report-dataset')?.value;
  if (!name) { showToast('Selecciona un dataset', 'warning'); return; }
  try {
    const blob = await api.reportExcel(name);
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a'); a.href = url; a.download = `${name}_report.xlsx`; a.click();
    URL.revokeObjectURL(url);
    showToast('Excel exportado', 'success');
  } catch (err) { showToast(`Error: ${err.message}`, 'error'); }
}

window.initReport = initReport;
window.showHtmlReport = showHtmlReport;
window.exportExcel = exportExcel;
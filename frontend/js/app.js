/* ── App Core: routing, init, global helpers ──────────────────────────────── */

let _sidebarCollapsed = false;

function toggleSidebar() {
  _sidebarCollapsed = !_sidebarCollapsed;
  document.getElementById('sidebar')?.classList.toggle('collapsed', _sidebarCollapsed);
  document.getElementById('main-content')?.classList.toggle('sidebar-collapsed', _sidebarCollapsed);
}

async function initApp() {
  checkApiStatus();
  setInterval(checkApiStatus, 30000);
  setInterval(updateClock, 1000);
  initRouting();
  await populateDatasetSelects();
  initModularTabs();
  window.addEventListener('resize', () => { Plotly.Plots.resize(document.querySelector('.main-graph'))?.catch(() => {}); });
}

async function checkApiStatus() {
  const badge = document.getElementById('api-status');
  try {
    const h = await api.health();
    badge?.setAttribute('data-status', 'online');
    badge.querySelector('.status-text').textContent = h.version ? `API v${h.version}` : 'API online';
  } catch {
    badge?.setAttribute('data-status', 'offline');
    badge.querySelector('.status-text').textContent = 'API desconectada';
  }
}

function updateClock() {
  const el = document.getElementById('topbar-datetime');
  if (el) el.textContent = new Date().toLocaleString('es-CL');
}

function initRouting() {
  document.querySelectorAll('.nav-item').forEach(link => {
    link.addEventListener('click', e => {
      e.preventDefault();
      const page = link.dataset.page;
      showPage(page);
      document.querySelectorAll('.nav-item').forEach(l => l.classList.remove('active'));
      link.classList.add('active');
      const bc = document.getElementById('breadcrumb');
      if (bc) bc.textContent = page.charAt(0).toUpperCase() + page.slice(1);
    });
  });

  const hash = location.hash.slice(1);
  if (hash) {
    const link = document.querySelector(`.nav-item[data-page="${hash}"]`);
    if (link) link.click();
  }
}

function showPage(pageId) {
  document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
  const page = document.getElementById(`page-${pageId}`);
  if (page) {
    page.classList.add('active');
    history.pushState(null, '', `#${pageId}`);
    pageActive(pageId);
  }
}

function pageActive(page) {
  if (page === 'dashboard') refreshDashboard();
  if (page === 'waveform') loadWaveformDatasetList();
  if (page === 'spectrum') loadSpectrumDatasetList();
  if (page === 'monitor') loadMonitorDatasetList();
  if (page === 'location') loadLocationDatasetList();
  if (page === 'report') loadReportDatasetList();
  if (page === 'magnitude') loadMagnitudeDatasetList();
  if (page === 'batch') refreshBatch();
  if (page === 'telemetry') refreshTelemetry();
}

async function populateDatasetSelects() {
  try {
    const list = await api.datasets();
    const selects = ['waveform-dataset','spectrum-dataset','monitor-dataset','location-dataset','report-dataset','magnitude-dataset','qc-dataset','batch-dataset'];
    selects.forEach(id => {
      const sel = document.getElementById(id);
      if (!sel) return;
      const current = sel.value;
      sel.innerHTML = '<option value="">Seleccionar...</option>' +
        (list || []).map(n => `<option value="${n}">${n}</option>`).join('');
      if (current) sel.value = current;
    });
  } catch { /* api not ready yet */ }
}

function initModularTabs() {
  window.switchSpectrumTab = (mode, btn) => {
    document.querySelectorAll('.spectrum-tab').forEach(t => t.classList.remove('active'));
    btn?.classList.add('active');
    if (window.S) { window.S.mode = mode; window.renderSpectrum(); }
  };
}

async function refreshDashboard() {
  try {
    const list = await api.datasets();
    const info = list?.length ? await api.datasetInfo(list[0]) : null;
    document.getElementById('stat-files').textContent = list?.length || 0;
    document.getElementById('stat-traces').textContent = info?.traces?.length || 0;
    document.getElementById('active-dataset').textContent = list?.[0] || 'Sin datos cargados';
    const pgaMax = info?.traces?.reduce((m, t) => Math.max(m, t.ims?.pga_cms2 || 0), 0) || 0;
    document.getElementById('stat-pga').textContent = pgaMax > 0 ? pgaMax.toFixed(2) : '—';
    const nPicks = info?.traces?.reduce((s, t) => s + (t.picks?.length || 0), 0) || 0;
    document.getElementById('stat-picks').textContent = nPicks;
  } catch { /* silent */ }
}

function loadWaveformDatasetList() { populateDatasetSelects(); }
function loadSpectrumDatasetList() { populateDatasetSelects(); if (window.initSpectrum) initSpectrum(); }
function loadMonitorDatasetList() { populateDatasetSelects(); }
function loadLocationDatasetList() { populateDatasetSelects(); if (window.initLocation) initLocation(); }
function loadReportDatasetList() { populateDatasetSelects(); if (window.initReport) initReport(); }
function loadMagnitudeDatasetList() { populateDatasetSelects(); if (window.initMagnitude) initMagnitude(); }
function refreshBatch() {}
function refreshTelemetry() {}

function colorForIdx(i) {
  const colors = ['#74b9ff','#55efc4','#a29bfe','#ffeaa7','#ff6b6b','#fd79a8','#00cec9','#fdcb6e'];
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
  setTimeout(() => { toast.style.opacity='0'; setTimeout(() => toast.remove(), 300); }, 3000);
}

window.showToast = showToast;
window.toggleSidebar = toggleSidebar;
window.showPage = showPage;
window.refreshDashboard = refreshDashboard;

window.addEventListener('DOMContentLoaded', initApp);
window.addEventListener('popstate', () => {
  const page = location.hash.slice(1) || 'dashboard';
  const link = document.querySelector(`.nav-item[data-page="${page}"]`);
  if (link) link.click();
});
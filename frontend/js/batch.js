/* Batch Loader — scan structured folders, load MiniSEED with decimation + merge */

let batchState = { root: 'data/', decimate: 1, merge: true };

window.addEventListener('DOMContentLoaded', () => {
  const root = document.getElementById('batch-root');
  if (root) root.addEventListener('change', e => { batchState.root = e.target.value; });
  const dec = document.getElementById('batch-decimate');
  if (dec) dec.addEventListener('change', e => { batchState.decimate = parseInt(e.target.value); });
  const mrg = document.getElementById('batch-merge');
  if (mrg) mrg.addEventListener('change', e => { batchState.merge = e.target.checked; });
});

async function batchScanAndLoad() {
  // Note: real scanning would need server-side support via API
  // For now, we simulate by showing a message about the scan parameters
  const root = batchState.root;
  const scanEl = document.getElementById('batch-scan-results');
  if (scanEl) {
    scanEl.innerHTML = `<p>Escaneando <code>${root}</code>...<br>
    Parámetros: decimation=${batchState.decimate}, merge=${batchState.merge}<br>
    <em>La carga batch real requiere acceso al filesystem del servidor (próxima versión).</em></p>`;
  }
  showToast('Batch: función limitada — usa Upload para cargar archivos', 'info');
}

window.batchScanAndLoad = batchScanAndLoad;
window.showToast = showToast;
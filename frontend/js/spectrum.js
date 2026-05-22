/* ── Spectrum Viewer ─────────────────────────────────────────────────────────── */

let S = {
  currentDataset: null,
  currentTraceIdx: 0,
  mode: 'fft',  // fft | psd | spectro | hvsr | rotd50 | design
};

function initSpectrum() {
  const sel = document.getElementById('spectrum-dataset');
  if (sel) sel.addEventListener('change', e => { S.currentDataset = e.target.value; loadSpectrumTraces(); });

  document.querySelectorAll('[data-spec-mode]').forEach(btn => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('[data-spec-mode]').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      S.mode = btn.dataset.specMode;
      renderSpectrum();
    });
  });
}

async function loadSpectrumTraces() {
  const name = S.currentDataset || document.getElementById('spectrum-dataset')?.value;
  if (!name) return;
  try {
    const info = await api.datasetInfo(name);
    const sel = document.getElementById('spectrum-trace');
    if (sel) {
      sel.innerHTML = (info.traces || []).map((t, i) =>
        `<option value="${i}">${i}: ${t.station}.${t.channel}</option>`
      ).join('');
      sel.addEventListener('change', e => { S.currentTraceIdx = parseInt(e.target.value); renderSpectrum(); });
    }
    S.currentTraceIdx = 0;
    renderSpectrum();
  } catch (err) {
    showToast(`Error: ${err.message}`, 'error');
  }
}

async function renderSpectrum() {
  const name = S.currentDataset || document.getElementById('spectrum-dataset')?.value;
  if (!name) { showToast('Selecciona un dataset', 'warning'); return; }

  const plotEl = document.getElementById('spectrum-plot');
  if (!plotEl) return;
  plotEl.innerHTML = '<div class="plot-loading">Generando espectro...</div>';

  try {
    let plotData, layout;

    if (S.mode === 'fft') {
      const d = await api.datasetSpectrumFft(name, { traceIdx: S.currentTraceIdx, logScale: true, freqLimit: 25 });
      plotData = [Object.assign({}, d.data[0], { line: { color: '#74b9ff', width: 1.5 } })];
      layout = { title: 'FFT — amplitud vs frecuencia', xaxis: { title: 'Frecuencia (Hz)', color: '#e0e0e0' }, yaxis: { title: 'Amplitud (log)', color: '#e0e0e0' }, paper_bgcolor: 'rgba(0,0,0,0)', plot_bgcolor: 'rgba(0,0,0,0)', template: 'plotly_dark' };

    } else if (S.mode === 'psd') {
      const d = await api.datasetSpectrumPsd(name, { traceIdx: S.currentTraceIdx, logScale: true, freqMax: 50 });
      plotData = [Object.assign({}, d.data[0], { line: { color: '#55efc4', width: 1.5 } })];
      layout = { title: 'PSD — densidad espectral de potencia', xaxis: { title: 'Frecuencia (Hz)', color: '#e0e0e0' }, yaxis: { title: 'PSD (log)', color: '#e0e0e0' }, paper_bgcolor: 'rgba(0,0,0,0)', plot_bgcolor: 'rgba(0,0,0,0)', template: 'plotly_dark' };

    } else if (S.mode === 'spectro') {
      const d = await api.datasetSpectrumSpectro(name, { traceIdx: S.currentTraceIdx });
      plotData = [d.data[0]];
      layout = { title: 'Espectrograma', xaxis: { title: 'Tiempo (s)', color: '#e0e0e0' }, yaxis: { title: 'Frecuencia (Hz)', color: '#e0e0e0' }, paper_bgcolor: 'rgba(0,0,0,0)', plot_bgcolor: 'rgba(0,0,0,0)', template: 'plotly_dark' };

    } else if (S.mode === 'hvsr') {
      const d = await api.datasetSpectrumHvsr(name);
      plotData = [Object.assign({}, d.data[0], { line: { color: '#a29bfe', width: 2 } })];
      layout = { title: 'HVSR — curva promedio', xaxis: { title: 'Frecuencia (Hz)', color: '#e0e0e0' }, yaxis: { title: 'H/V', color: '#e0e0e0' }, paper_bgcolor: 'rgba(0,0,0,0)', plot_bgcolor: 'rgba(0,0,0,0)', template: 'plotly_dark' };

    } else if (S.mode === 'rotd50') {
      const d = await api.datasetSpectrumRotd50(name);
      const traces = d.data || [];
      plotData = traces.map((t, i) => Object.assign({}, t, { line: { color: colorForIdx(i), width: 1.5 } }));
      layout = { title: 'RotD50 — espectro de respuesta', xaxis: { title: 'Periodo (s)', color: '#e0e0e0' }, yaxis: { title: 'Sa (g)', color: '#e0e0e0' }, paper_bgcolor: 'rgba(0,0,0,0)', plot_bgcolor: 'rgba(0,0,0,0)', template: 'plotly_dark' };

    } else if (S.mode === 'design') {
      const d = await api.datasetSpectrumDesign(name);
      plotData = [
        Object.assign({}, (d.data || [])[0] || {}, { line: { color: '#74b9ff', width: 2 }, name: 'Design Spectrum' }),
        Object.assign({}, (d.data || [])[1] || {}, { line: { color: '#ff6b6b', width: 1.5, dash: 'dot' }, name: 'RotD50' }),
      ].filter(t => t.x);
      layout = { title: 'Espectro de diseño sísmico', xaxis: { title: 'Periodo (s)', color: '#e0e0e0' }, yaxis: { title: 'Sa (g)', color: '#e0e0e0' }, paper_bgcolor: 'rgba(0,0,0,0)', plot_bgcolor: 'rgba(0,0,0,0)', template: 'plotly_dark' };
    }

    plotEl.innerHTML = '';
    Plotly.newPlot(plotEl, plotData, layout, { responsive: true });

    const infoEl = document.getElementById('spectrum-info');
    if (infoEl) {
      infoEl.innerHTML = `<div class="info-box">Dataset: <strong>${name}</strong> | Traza: <strong>${S.currentTraceIdx}</strong> | Modo: <strong>${S.mode.toUpperCase()}</strong></div>`;
    }
  } catch (err) {
    plotEl.innerHTML = `<div class="plot-empty"><p>Error: ${err.message}</p></div>`;
    showToast(`Error: ${err.message}`, 'error');
  }
}

window.initSpectrum = initSpectrum;
window.loadSpectrum = loadSpectrumTraces;
window.renderSpectrum = renderSpectrum;
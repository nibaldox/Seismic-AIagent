let API_BASE = 'http://localhost:8000/api';

fetch('config.json').then(r => r.json()).then(cfg => {
  API_BASE = cfg.api_url || API_BASE;
}).catch(() => {
  API_BASE = window.location.origin + '/api';
});

async function _get(path) {
  const r = await fetch(`${API_BASE}${path}`);
  if (!r.ok) {
    const text = await r.text().catch(() => r.statusText);
    throw new Error(`${r.status} ${r.statusText}: ${text}`);
  }
  return r.json();
}

async function _get_plot(path) {
  const r = await fetch(`${API_BASE}${path}`);
  if (!r.ok) {
    const text = await r.text().catch(() => r.statusText);
    throw new Error(`${r.status} ${r.statusText}: ${text}`);
  }
  const data = await r.json();
  return data.plot;
}

const api = {

  async health() {
    return _get('/health');
  },

  async analyze(file) {
    const form = new FormData();
    form.append('file', file);
    const r = await fetch(`${API_BASE}/analyze`, { method: 'POST', body: form });
    if (!r.ok) {
      const err = await r.text().catch(() => r.statusText);
      throw new Error(err);
    }
    return r.json();
  },

  async datasets() {
    return _get('/datasets');
  },

  async datasetInfo(name) {
    return _get(`/datasets/${encodeURIComponent(name)}`);
  },

  // ── Trace with full history ────────────────────────────────────────────────

  async datasetTrace(name, traceIdx = 0) {
    return _get(`/datasets/${encodeURIComponent(name)}/trace/${traceIdx}`);
  },

  // ── Waveform (all traces or single) ────────────────────────────────────────

  async datasetWaveform(name, traceIdx = null) {
    const idx = traceIdx !== null ? `?trace_idx=${traceIdx}` : '';
    return _get(`/datasets/${encodeURIComponent(name)}/waveform${idx}`);
  },

  // ── Filter or baseline correction ─────────────────────────────────────────

  async datasetCorrect(name, { traceIdx = 0, correctionType = 'filter',
                                filterType = 'bandpass', freqmin = 0.5, freqmax = 25.0,
                                baselineMethod = 'linear', polyOrder = 2 } = {}) {
    const params = new URLSearchParams({
      trace_idx: traceIdx,
      correction_type: correctionType,
      filter_type: filterType,
      freqmin, freqmax,
      baseline_method: baselineMethod,
      poly_order: polyOrder,
    });
    return _get(`/datasets/${encodeURIComponent(name)}/correct?${params}`);
  },

  async datasetReset(name, traceIdx = 0) {
    return _get(`/datasets/${encodeURIComponent(name)}/reset?trace_idx=${traceIdx}`);
  },

  // ── Picks ─────────────────────────────────────────────────────────────────

  async datasetPicks(name, traceIdx = 0, recompute = false) {
    return _get(`/datasets/${encodeURIComponent(name)}/picks?trace_idx=${traceIdx}&recompute=${recompute}`);
  },

  // ── Intensity Measures ───────────────────────────────────────────────────

  async datasetIms(name, traceIdx = null, recompute = false) {
    let path = `/datasets/${encodeURIComponent(name)}/ims?recompute=${recompute}`;
    if (traceIdx !== null) path += `&trace_idx=${traceIdx}`;
    return _get(path);
  },

  // ── Quality Control ───────────────────────────────────────────────────────

  async datasetQc(name, traceIdx = null, recompute = false) {
    let path = `/datasets/${encodeURIComponent(name)}/qc?recompute=${recompute}`;
    if (traceIdx !== null) path += `&trace_idx=${traceIdx}`;
    return _get(path);
  },

  // ── Spectrum (cached) ───────────────────────────────────────────────────

  async datasetSpectrumFft(name, { traceIdx = 0, logScale = true,
                                    freqLimit = 25, windowType = 'hanning' } = {}) {
    const params = new URLSearchParams({ trace_idx: traceIdx, log_scale: logScale,
                                        freq_limit: freqLimit, window_type: windowType });
    return _get_plot(`/datasets/${encodeURIComponent(name)}/spectrum/fft?${params}`);
  },

  async datasetSpectrumPsd(name, { traceIdx = 0, nperseg = 512, overlap = 0.75,
                                    logScale = true, freqMax = 50 } = {}) {
    const params = new URLSearchParams({ trace_idx: traceIdx, nperseg, overlap,
                                        log_scale: logScale, freq_max: freqMax });
    return _get_plot(`/datasets/${encodeURIComponent(name)}/spectrum/psd?${params}`);
  },

  async datasetSpectrumSpectro(name, { traceIdx = 0, nfft = 256, overlap = 0.5,
                                       windowType = 'hanning', colorscale = 'Viridis' } = {}) {
    const params = new URLSearchParams({ trace_idx: traceIdx, nfft, overlap,
                                        window_type: windowType, colorscale });
    return _get_plot(`/datasets/${encodeURIComponent(name)}/spectrum/spectro?${params}`);
  },

  async datasetSpectrumHvsr(name, { h1Idx = 0, h2Idx = 1, zIdx = 2,
                                    nperseg = 512, overlap = 0.75,
                                    freqMin = 0.1, freqMax = 20.0,
                                    smoothOctaves = 0.1 } = {}) {
    const params = new URLSearchParams({ h1_idx: h1Idx, h2_idx: h2Idx, z_idx: zIdx,
                                        nperseg, overlap, freq_min: freqMin,
                                        freq_max: freqMax, smooth_octaves: smoothOctaves });
    return _get_plot(`/datasets/${encodeURIComponent(name)}/spectrum/hvsr?${params}`);
  },

  async datasetSpectrumRotd50(name, { comp1Idx = 0, comp2Idx = 1,
                                       damping = 0.05, tMin = 0.01,
                                       tMax = 4.0, nPeriods = 100 } = {}) {
    const params = new URLSearchParams({ comp1_idx: comp1Idx, comp2_idx: comp2Idx,
                                        damping, t_min: tMin, t_max: tMax, n_periods: nPeriods });
    return _get(`/datasets/${encodeURIComponent(name)}/spectrum/rotd50?${params}`);
  },

  async datasetSpectrumDesign(name, { code = 'nch433', zone = 3, soil = 'B',
                                      Ss = 1.0, S1 = 0.4, siteClass = 'D',
                                      damping = 0.05, tMax = 4.0 } = {}) {
    const params = new URLSearchParams({ code, zone, soil, Ss, S1, site_class: siteClass,
                                        damping, t_max: tMax });
    return _get(`/datasets/${encodeURIComponent(name)}/spectrum/design?${params}`);
  },

  // ── Magnitude ──────────────────────────────────────────────────────────────

  async datasetMagnitude(name, traceIdx = 0) {
    return _get(`/datasets/${encodeURIComponent(name)}/magnitude?trace_idx=${traceIdx}`);
  },

  // ── Location ──────────────────────────────────────────────────────────────

  async datasetLocation(name, { vp = 6.0, vs = 3.46,
                                gridMin = -50.0, gridMax = 50.0,
                                gridStep = 2.0 } = {}) {
    const params = new URLSearchParams({ vp, vs, grid_min: gridMin,
                                        grid_max: gridMax, grid_step: gridStep });
    return _get(`/datasets/${encodeURIComponent(name)}/location?${params}`);
  },

  // ── Reports ────────────────────────────────────────────────────────────────

  async reportHtml(name) {
    const r = await fetch(`${API_BASE}/datasets/${encodeURIComponent(name)}/report/html`);
    if (!r.ok) throw new Error(`HTML report failed: ${r.status}`);
    return r.text();
  },

  async reportExcel(name) {
    const r = await fetch(`${API_BASE}/datasets/${encodeURIComponent(name)}/report/excel`);
    if (!r.ok) throw new Error(`Excel export failed: ${r.status}`);
    return r.blob();
  },

  // ── Location demo ─────────────────────────────────────────────────────────

  async locationDemo() {
    return _get('/location/demo');
  },
};

window.api = api;
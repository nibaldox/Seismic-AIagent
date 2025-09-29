import React, { useMemo, useState } from 'react'
import axios from 'axios'

const API_URL = (import.meta as any).env?.VITE_API_URL || 'http://localhost:8000'

type AnalysisType = 'Spectrogram' | 'FFT' | 'PSD'

type WindowType = 'hanning' | 'hamming' | 'blackman'

type Colorscale = 'Viridis' | 'Plasma' | 'Inferno' | 'Turbo'

export function SpectrumPage() {
  const [file, setFile] = useState<File | null>(null)
  const [img, setImg] = useState<string>('')
  const [summary, setSummary] = useState<string>('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string>('')

  const [analysis, setAnalysis] = useState<AnalysisType>('Spectrogram')
  const [windowType, setWindowType] = useState<WindowType>('hanning')

  // Spec params
  const [nfft, setNfft] = useState<number>(256)
  const [overlap, setOverlap] = useState<number>(0.5)
  const [colorscale, setColorscale] = useState<Colorscale>('Viridis')

  // FFT
  const [fftLog, setFftLog] = useState<boolean>(true)
  const [fftLim, setFftLim] = useState<number>(25)

  // PSD
  const [psdNperseg, setPsdNperseg] = useState<number>(512)
  const [psdOverlap, setPsdOverlap] = useState<number>(0.75)
  const [psdLog, setPsdLog] = useState<boolean>(true)
  const [psdFreqMax, setPsdFreqMax] = useState<number>(50)

  const canSubmit = useMemo(() => !!file && !loading, [file, loading])

  async function handlePlot() {
    if (!file) return
    setError('')
    setImg('')
    setSummary('')

    const form = new FormData()
    form.append('file', file)
    form.append('analysis_type', analysis)
    form.append('window_type', windowType)
    form.append('nfft', String(nfft))
    form.append('overlap', String(overlap))
    form.append('colorscale', String(colorscale))
    form.append('fft_log', String(fftLog))
    form.append('fft_lim', String(fftLim))
    form.append('psd_nperseg', String(psdNperseg))
    form.append('psd_overlap', String(psdOverlap))
    form.append('psd_log', String(psdLog))
    form.append('psd_freq_max', String(psdFreqMax))

    setLoading(true)
    try {
      const { data } = await axios.post(`${API_URL}/spectrum/plot`, form)
      setImg(`data:image/png;base64,${data.image_base64}`)
      setSummary(data.summary ?? '')
    } catch (e: any) {
      setError(e?.message || 'Fallo al procesar el análisis')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div>
      <h2>🔍 Spectrum</h2>
      <div style={{ display: 'flex', gap: 8, alignItems: 'center', flexWrap: 'wrap' }}>
        <input type="file" onChange={e => setFile(e.target.files?.[0] ?? null)} />
        <select value={analysis} onChange={e => setAnalysis(e.target.value as AnalysisType)}>
          <option value="Spectrogram">Espectrograma</option>
          <option value="FFT">FFT</option>
          <option value="PSD">PSD</option>
        </select>
        <select value={windowType} onChange={e => setWindowType(e.target.value as WindowType)}>
          <option value="hanning">hanning</option>
          <option value="hamming">hamming</option>
          <option value="blackman">blackman</option>
        </select>

        {analysis === 'Spectrogram' && (
          <>
            <input type="number" min={64} step={64} value={nfft} onChange={e => setNfft(Number(e.target.value))} style={{ width: 100 }} />
            <input type="number" min={0} max={0.95} step={0.05} value={overlap} onChange={e => setOverlap(Number(e.target.value))} style={{ width: 120 }} />
            <select value={colorscale} onChange={e => setColorscale(e.target.value as Colorscale)}>
              <option value="Viridis">Viridis</option>
              <option value="Plasma">Plasma</option>
              <option value="Inferno">Inferno</option>
              <option value="Turbo">Turbo</option>
            </select>
          </>
        )}

        {analysis === 'FFT' && (
          <>
            <label style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
              <input type="checkbox" checked={fftLog} onChange={e => setFftLog(e.target.checked)} /> Log(dB)
            </label>
            <input type="number" min={1} max={200} step={1} value={fftLim} onChange={e => setFftLim(Number(e.target.value))} style={{ width: 140 }} />
          </>
        )}

        {analysis === 'PSD' && (
          <>
            <input type="number" min={128} step={128} value={psdNperseg} onChange={e => setPsdNperseg(Number(e.target.value))} style={{ width: 120 }} />
            <input type="number" min={0} max={0.95} step={0.05} value={psdOverlap} onChange={e => setPsdOverlap(Number(e.target.value))} style={{ width: 140 }} />
            <label style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
              <input type="checkbox" checked={psdLog} onChange={e => setPsdLog(e.target.checked)} /> Log(dB)
            </label>
            <input type="number" min={1} max={200} step={1} value={psdFreqMax} onChange={e => setPsdFreqMax(Number(e.target.value))} style={{ width: 140 }} />
          </>
        )}

        <button onClick={handlePlot} disabled={!canSubmit}>
          {loading ? 'Procesando…' : 'Calcular'}
        </button>
      </div>

      {error && <div style={{ marginTop: 12, padding: 8, background: '#ffd9d9', color: '#7a0000' }}>{error}</div>}

      {img && (
        <div style={{ marginTop: 16 }}>
          <img src={img} style={{ maxWidth: '100%' }} />
          <div style={{ marginTop: 8 }}>
            <a href={img} download={`spectrum_${Date.now()}.png`}>Descargar PNG</a>
          </div>
        </div>
      )}

      {summary && <pre style={{ background: '#111', color: '#ddd', padding: 12, marginTop: 16 }}>{summary}</pre>}
    </div>
  )
}

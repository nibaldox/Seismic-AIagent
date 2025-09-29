import React, { useMemo, useState } from 'react'
import axios from 'axios'

const API_URL = (import.meta as any).env?.VITE_API_URL || 'http://localhost:8000'

type AnalysisType = 'Spectrogram' | 'FFT' | 'PSD'

type WindowType = 'hanning' | 'hamming' | 'blackman'

type Colorscale = 'Viridis' | 'Plasma' | 'Inferno' | 'Turbo'

export function SpectrumPage() {
  const [file, setFile] = useState<File | null>(null)
  const [image, setImage] = useState<string>('')
  const [summary, setSummary] = useState<string>('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const [analysis, setAnalysis] = useState<AnalysisType>('Spectrogram')
  const [windowType, setWindowType] = useState<WindowType>('hanning')
  const [nfft, setNfft] = useState<number>(256)
  const [overlap, setOverlap] = useState<number>(0.5)
  const [colorscale, setColorscale] = useState<Colorscale>('Viridis')
  const [fftLog, setFftLog] = useState(true)
  const [fftLim, setFftLim] = useState(25)
  const [psdNperseg, setPsdNperseg] = useState(512)
  const [psdOverlap, setPsdOverlap] = useState(0.75)
  const [psdLog, setPsdLog] = useState(true)
  const [psdFreqMax, setPsdFreqMax] = useState(50)

  const canSubmit = useMemo(() => !!file && !loading, [file, loading])

  async function run() {
    if (!file) return
    setError(''); setImage(''); setSummary('')
    const form = new FormData()
    form.append('file', file)
    form.append('analysis_type', analysis)
    form.append('window_type', windowType)
    form.append('nfft', String(nfft))
    form.append('overlap', String(overlap))
    form.append('colorscale', colorscale)
    form.append('fft_log', String(fftLog))
    form.append('fft_lim', String(fftLim))
    form.append('psd_nperseg', String(psdNperseg))
    form.append('psd_overlap', String(psdOverlap))
    form.append('psd_log', String(psdLog))
    form.append('psd_freq_max', String(psdFreqMax))
    setLoading(true)
    try {
      const { data } = await axios.post(`${API_URL}/spectrum/plot`, form)
      setImage(`data:image/png;base64,${data.image_base64}`)
      setSummary(data.summary ?? '')
    } catch (e: any) {
      setError(e?.message || 'Fallo al procesar el análisis')
    } finally {
      setLoading(false)
    }
  }

  function downloadPNG() {
    if (!image) return
    const a = document.createElement('a')
    a.href = image
    a.download = 'spectrum.png'
    document.body.appendChild(a)
    a.click()
    a.remove()
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
            <label><input type="checkbox" checked={fftLog} onChange={e => setFftLog(e.target.checked)} /> Log(dB)</label>
            <input type="number" min={1} max={200} step={1} value={fftLim} onChange={e => setFftLim(Number(e.target.value))} style={{ width: 140 }} />
          </>
        )}
        {analysis === 'PSD' && (
          <>
            <input type="number" min={128} step={128} value={psdNperseg} onChange={e => setPsdNperseg(Number(e.target.value))} style={{ width: 120 }} />
            <input type="number" min={0} max={0.95} step={0.05} value={psdOverlap} onChange={e => setPsdOverlap(Number(e.target.value))} style={{ width: 140 }} />
            <label><input type="checkbox" checked={psdLog} onChange={e => setPsdLog(e.target.checked)} /> Log(dB)</label>
            <input type="number" min={1} max={200} step={1} value={psdFreqMax} onChange={e => setPsdFreqMax(Number(e.target.value))} style={{ width: 140 }} />
          </>
        )}
        <button onClick={run} disabled={!canSubmit}>{loading ? 'Procesando…' : 'Calcular'}</button>
        <button onClick={downloadPNG} disabled={!image}>Descargar PNG</button>
      </div>
      {error && <div style={{ marginTop: 12, padding: 8, background: '#ffd9d9', color: '#7a0000' }}>{error}</div>}
      {image && (
        <div style={{ marginTop: 16 }}>
          <img src={image} style={{ maxWidth: '100%' }} />
        </div>
      )}
      {summary && <pre style={{ background: '#111', color: '#ddd', padding: 12, marginTop: 16 }}>{summary}</pre>}
    </div>
  )
}

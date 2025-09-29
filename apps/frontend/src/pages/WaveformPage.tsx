import React, { useMemo, useState } from 'react'
import axios from 'axios'

const API_URL = (import.meta as any).env?.VITE_API_URL || 'http://localhost:8000'

type FilterType = 'none' | 'bandpass' | 'highpass' | 'lowpass'

type Unit = 'Raw' | 'm/s²' | 'g'

type AmpScale = 'Auto' | 'Global' | 'Normalized'

export function WaveformPage() {
  const [file, setFile] = useState<File | null>(null)
  const [img, setImg] = useState<string>('')
  const [summary, setSummary] = useState<string>('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string>('')

  const [filterType, setFilterType] = useState<FilterType>('none')
  const [freqmin, setFreqmin] = useState<number>(1.0)
  const [freqmax, setFreqmax] = useState<number>(10.0)
  const [unit, setUnit] = useState<Unit>('Raw')
  const [ampScale, setAmpScale] = useState<AmpScale>('Auto')
  const [t0, setT0] = useState<number>(0)
  const [t1, setT1] = useState<number>(0)

  const canSubmit = useMemo(() => !!file && !loading, [file, loading])

  async function handlePlot() {
    if (!file) return
    setError('')
    setImg('')
    setSummary('')

    const form = new FormData()
    form.append('file', file)
    form.append('filter_type', filterType)
    form.append('freqmin', String(freqmin))
    form.append('freqmax', String(freqmax))
    form.append('unit', unit)
    form.append('amplitude_scale', ampScale)
    form.append('t0', String(t0))
    if (t1 > 0) form.append('t1', String(t1))

    setLoading(true)
    try {
      const { data } = await axios.post(`${API_URL}/waveform/plot`, form)
      setImg(`data:image/png;base64,${data.image_base64}`)
      setSummary(data.summary ?? '')
    } catch (e: any) {
      setError(e?.message || 'Fallo al procesar waveform')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div>
      <h2>📊 Waveform</h2>
      <div style={{ display: 'flex', gap: 8, alignItems: 'center', flexWrap: 'wrap' }}>
        <input type="file" onChange={e => setFile(e.target.files?.[0] ?? null)} />
        <select value={filterType} onChange={e => setFilterType(e.target.value as FilterType)}>
          <option value="none">none</option>
          <option value="bandpass">bandpass</option>
          <option value="highpass">highpass</option>
          <option value="lowpass">lowpass</option>
        </select>
        <input type="number" step={0.5} value={freqmin} onChange={e => setFreqmin(Number(e.target.value))} placeholder="freqmin" style={{ width: 120 }} />
        <input type="number" step={0.5} value={freqmax} onChange={e => setFreqmax(Number(e.target.value))} placeholder="freqmax" style={{ width: 120 }} />
        <select value={unit} onChange={e => setUnit(e.target.value as Unit)}>
          <option value="Raw">Raw</option>
          <option value="m/s²">m/s²</option>
          <option value="g">g</option>
        </select>
        <select value={ampScale} onChange={e => setAmpScale(e.target.value as AmpScale)}>
          <option value="Auto">Auto</option>
          <option value="Global">Global</option>
          <option value="Normalized">Normalized</option>
        </select>
        <input type="number" value={t0} onChange={e => setT0(Number(e.target.value))} placeholder="t0 (s)" style={{ width: 120 }} />
        <input type="number" value={t1} onChange={e => setT1(Number(e.target.value))} placeholder="t1 (s)" style={{ width: 120 }} />
        <button onClick={handlePlot} disabled={!canSubmit}>
          {loading ? 'Procesando…' : 'Calcular'}
        </button>
      </div>

      {error && <div style={{ marginTop: 12, padding: 8, background: '#ffd9d9', color: '#7a0000' }}>{error}</div>}

      {img && (
        <div style={{ marginTop: 16 }}>
          <img src={img} style={{ maxWidth: '100%' }} />
          <div style={{ marginTop: 8 }}>
            <a href={img} download={`waveform_${Date.now()}.png`}>Descargar PNG</a>
          </div>
        </div>
      )}

      {summary && <pre style={{ background: '#111', color: '#ddd', padding: 12, marginTop: 16 }}>{summary}</pre>}
    </div>
  )
}

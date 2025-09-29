import React, { useMemo, useState } from 'react'
import axios from 'axios'

const API_URL = (import.meta as any).env?.VITE_API_URL || 'http://localhost:8000'

type Filter = 'none' | 'bandpass' | 'highpass' | 'lowpass'

type Unit = 'Raw' | 'm/s²' | 'g'

type AmpScale = 'Auto' | 'Global' | 'Normalized'

export function WaveformPage() {
  const [file, setFile] = useState<File | null>(null)
  const [image, setImage] = useState('')
  const [summary, setSummary] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const [filter, setFilter] = useState<Filter>('none')
  const [fmin, setFmin] = useState(1.0)
  const [fmax, setFmax] = useState(10.0)
  const [unit, setUnit] = useState<Unit>('Raw')
  const [scale, setScale] = useState<AmpScale>('Auto')
  const [t0, setT0] = useState(0)
  const [t1, setT1] = useState<number | ''>('')

  const canSubmit = useMemo(() => !!file && !loading, [file, loading])

  async function run() {
    if (!file) return
    setError(''); setImage(''); setSummary('')
    const form = new FormData()
    form.append('file', file)
    form.append('filter_type', filter)
    form.append('freqmin', String(fmin))
    form.append('freqmax', String(fmax))
    form.append('unit', unit)
    form.append('amplitude_scale', scale)
    form.append('t0', String(t0))
    if (t1 !== '') form.append('t1', String(t1))

    setLoading(true)
    try {
      const { data } = await axios.post(`${API_URL}/waveform/plot`, form)
      setImage(`data:image/png;base64,${data.image_base64}`)
      setSummary(data.summary ?? '')
    } catch (e: any) {
      setError(e?.message || 'Fallo al procesar waveform')
    } finally {
      setLoading(false)
    }
  }

  function downloadPNG() {
    if (!image) return
    const a = document.createElement('a')
    a.href = image
    a.download = 'waveform.png'
    document.body.appendChild(a)
    a.click()
    a.remove()
  }

  return (
    <div>
      <h2>📊 Waveform</h2>
      <div style={{ display: 'flex', gap: 8, alignItems: 'center', flexWrap: 'wrap' }}>
        <input type="file" onChange={e => setFile(e.target.files?.[0] ?? null)} />
        <select value={filter} onChange={e => setFilter(e.target.value as Filter)}>
          <option value="none">none</option>
          <option value="bandpass">bandpass</option>
          <option value="highpass">highpass</option>
          <option value="lowpass">lowpass</option>
        </select>
        <input type="number" step={0.1} value={fmin} onChange={e => setFmin(Number(e.target.value))} placeholder="freqmin" style={{ width: 120 }} />
        <input type="number" step={0.1} value={fmax} onChange={e => setFmax(Number(e.target.value))} placeholder="freqmax" style={{ width: 120 }} />
        <select value={unit} onChange={e => setUnit(e.target.value as Unit)}>
          <option value="Raw">Raw</option>
          <option value="m/s²">m/s²</option>
          <option value="g">g</option>
        </select>
        <select value={scale} onChange={e => setScale(e.target.value as AmpScale)}>
          <option value="Auto">Auto</option>
          <option value="Global">Global</option>
          <option value="Normalized">Normalized</option>
        </select>
        <input type="number" value={t0} onChange={e => setT0(Number(e.target.value))} placeholder="t0 (s)" style={{ width: 120 }} />
        <input type="number" value={t1 === '' ? 0 : t1} onChange={e => setT1(Number(e.target.value))} placeholder="t1 (s, vacío=auto)" style={{ width: 160 }} />
        <button onClick={run} disabled={!canSubmit}>{loading ? 'Procesando…' : 'Generar'}</button>
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

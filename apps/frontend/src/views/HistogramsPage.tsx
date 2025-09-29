import React, { useMemo, useState } from 'react'
import axios from 'axios'

const API_URL = (import.meta as any).env?.VITE_API_URL || 'http://localhost:8000'

export function HistogramsPage() {
  const [file, setFile] = useState<File | null>(null)
  const [column, setColumn] = useState<string>('')
  const [bins, setBins] = useState<number>(50)
  const [image, setImage] = useState('')
  const [summary, setSummary] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const canSubmit = useMemo(() => !!file && !loading, [file, loading])

  async function run() {
    if (!file) return
    setError(''); setImage(''); setSummary('')
    const form = new FormData()
    form.append('file', file)
    if (column) form.append('column', column)
    form.append('bins', String(bins))

    setLoading(true)
    try {
      const { data } = await axios.post(`${API_URL}/telemetry/histogram`, form)
      if (data.error) throw new Error(data.error)
      setImage(`data:image/png;base64,${data.image_base64}`)
      setSummary(data.summary ?? '')
    } catch (e: any) {
      setError(e?.message || 'Fallo en histograma')
    } finally {
      setLoading(false)
    }
  }

  function downloadPNG() {
    if (!image) return
    const a = document.createElement('a')
    a.href = image
    a.download = 'histogram.png'
    document.body.appendChild(a)
    a.click()
    a.remove()
  }

  return (
    <div>
      <h2>📈 Histogramas</h2>
      <div style={{ display: 'flex', gap: 8, alignItems: 'center', flexWrap: 'wrap' }}>
        <input type="file" accept=".csv" onChange={e => setFile(e.target.files?.[0] ?? null)} />
        <input type="text" value={column} onChange={e => setColumn(e.target.value)} placeholder="columna (opcional)" />
        <input type="number" min={10} max={200} step={5} value={bins} onChange={e => setBins(Number(e.target.value))} />
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
  )}

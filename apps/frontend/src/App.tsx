import React, { useState } from 'react'
import axios from 'axios'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

export function App() {
  const [file, setFile] = useState<File | null>(null)
  const [img, setImg] = useState<string>('')
  const [summary, setSummary] = useState<string>('')
  const [loading, setLoading] = useState(false)

  async function handleSpectrum() {
    if (!file) return
    const form = new FormData()
    form.append('file', file)
    form.append('analysis_type', 'Spectrogram')
    form.append('nfft', '256')
    form.append('overlap', '0.5')
    form.append('window_type', 'hanning')
    form.append('colorscale', 'Viridis')

    setLoading(true)
    try {
      const { data } = await axios.post(`${API_URL}/spectrum/plot`, form)
      setImg(`data:image/png;base64,${data.image_base64}`)
      setSummary(data.summary ?? '')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div style={{ padding: 16 }}>
      <h2>Seismic Frontend</h2>
      <p>API: {API_URL}</p>

      <input type="file" onChange={e => setFile(e.target.files?.[0] ?? null)} />
      <button onClick={handleSpectrum} disabled={!file || loading}>
        {loading ? 'Procesando…' : 'Espectrograma'}
      </button>

      {img && (
        <div>
          <img src={img} style={{ maxWidth: '100%' }} />
        </div>
      )}

      {summary && (
        <pre style={{ background: '#111', color: '#ddd', padding: 12 }}>{summary}</pre>
      )}
    </div>
  )
}

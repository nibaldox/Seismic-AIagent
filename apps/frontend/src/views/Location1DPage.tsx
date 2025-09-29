import React, { useState } from 'react'
import axios from 'axios'

const API_URL = (import.meta as any).env?.VITE_API_URL || 'http://localhost:8000'

type Station = { code: string; x_km: number; y_km: number }

type Observation = { station: string; t_p: number; t_s: number }

export function Location1DPage() {
  const [stations, setStations] = useState<Station[]>([])
  const [obs, setObs] = useState<Observation[]>([])
  const [vp, setVp] = useState(6.0)
  const [vs, setVs] = useState(3.5)
  const [gridX, setGridX] = useState<[number, number, number]>([-50, 50, 2])
  const [gridY, setGridY] = useState<[number, number, number]>([-50, 50, 2])
  const [result, setResult] = useState<any>(null)
  const [error, setError] = useState('')

  function addStation() {
    setStations(prev => [...prev, { code: `S${prev.length + 1}`, x_km: 0, y_km: 0 }])
  }
  function addObs() {
    setObs(prev => [...prev, { station: '', t_p: 0, t_s: 0 }])
  }

  async function run() {
    setError(''); setResult(null)
    try {
      const { data } = await axios.post(`${API_URL}/location/one_d`, {
        stations,
        observations: obs,
        model: { vp, vs },
        grid: { x: gridX, y: gridY },
        min_stations: 2,
      })
      setResult(data)
    } catch (e: any) {
      setError(e?.message || 'Fallo localización 1D')
    }
  }

  return (
    <div>
      <h2>🌍 Location 1D</h2>

      <div style={{ display: 'flex', gap: 16, flexWrap: 'wrap' }}>
        <section>
          <h4>Estaciones</h4>
          <button onClick={addStation}>+ Estación</button>
          {stations.map((s, i) => (
            <div key={i} style={{ display: 'grid', gridTemplateColumns: '80px 80px 80px 1fr', gap: 8, marginTop: 8 }}>
              <input value={s.code} onChange={e => setStations(v => v.map((x, j) => j===i? { ...x, code: e.target.value }: x))} placeholder="code" />
              <input type="number" step={0.1} value={s.x_km} onChange={e => setStations(v => v.map((x, j) => j===i? { ...x, x_km: Number(e.target.value) }: x))} placeholder="x_km" />
              <input type="number" step={0.1} value={s.y_km} onChange={e => setStations(v => v.map((x, j) => j===i? { ...x, y_km: Number(e.target.value) }: x))} placeholder="y_km" />
            </div>
          ))}
        </section>

        <section>
          <h4>Observaciones P/S</h4>
          <button onClick={addObs}>+ Observación</button>
          {obs.map((o, i) => (
            <div key={i} style={{ display: 'grid', gridTemplateColumns: '100px 80px 80px 1fr', gap: 8, marginTop: 8 }}>
              <input value={o.station} onChange={e => setObs(v => v.map((x, j) => j===i? { ...x, station: e.target.value }: x))} placeholder="station" />
              <input type="number" step={0.01} value={o.t_p} onChange={e => setObs(v => v.map((x, j) => j===i? { ...x, t_p: Number(e.target.value) }: x))} placeholder="t_p" />
              <input type="number" step={0.01} value={o.t_s} onChange={e => setObs(v => v.map((x, j) => j===i? { ...x, t_s: Number(e.target.value) }: x))} placeholder="t_s" />
            </div>
          ))}
        </section>

        <section>
          <h4>Modelo/Grilla</h4>
          <div style={{ display: 'flex', gap: 8 }}>
            <input type="number" step={0.1} value={vp} onChange={e => setVp(Number(e.target.value))} placeholder="vp" />
            <input type="number" step={0.1} value={vs} onChange={e => setVs(Number(e.target.value))} placeholder="vs" />
          </div>
          <div style={{ display: 'flex', gap: 8, marginTop: 8 }}>
            <input type="number" step={0.1} value={gridX[0]} onChange={e => setGridX([Number(e.target.value), gridX[1], gridX[2]])} placeholder="x0" />
            <input type="number" step={0.1} value={gridX[1]} onChange={e => setGridX([gridX[0], Number(e.target.value), gridX[2]])} placeholder="x1" />
            <input type="number" step={0.1} value={gridX[2]} onChange={e => setGridX([gridX[0], gridX[1], Number(e.target.value)])} placeholder="dx" />
          </div>
          <div style={{ display: 'flex', gap: 8, marginTop: 8 }}>
            <input type="number" step={0.1} value={gridY[0]} onChange={e => setGridY([Number(e.target.value), gridY[1], gridY[2]])} placeholder="y0" />
            <input type="number" step={0.1} value={gridY[1]} onChange={e => setGridY([gridY[0], Number(e.target.value), gridY[2]])} placeholder="y1" />
            <input type="number" step={0.1} value={gridY[2]} onChange={e => setGridY([gridY[0], gridY[1], Number(e.target.value)])} placeholder="dy" />
          </div>
        </section>
      </div>

      <button style={{ marginTop: 12 }} onClick={run}>Localizar</button>

      {error && <div style={{ marginTop: 12, padding: 8, background: '#ffd9d9', color: '#7a0000' }}>{error}</div>}
      {result && (
        <pre style={{ background: '#111', color: '#ddd', padding: 12, marginTop: 16 }}>{JSON.stringify(result, null, 2)}</pre>
      )}
    </div>
  )
}

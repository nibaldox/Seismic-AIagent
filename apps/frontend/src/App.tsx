import React from 'react'
import { BrowserRouter, Link, Route, Routes, Navigate, useLocation } from 'react-router-dom'
import { SpectrumPage } from './pages/SpectrumPage'
import { WaveformPage } from './pages/WaveformPage'

function Sidebar() {
  const loc = useLocation()
  const item = (to: string, label: string) => (
    <Link
      to={to}
      style={{
        padding: '8px 12px',
        textDecoration: 'none',
        color: loc.pathname === to ? '#0b5fff' : '#222',
        background: loc.pathname === to ? '#e8f0ff' : 'transparent',
        borderRadius: 6,
      }}
    >
      {label}
    </Link>
  )
  return (
    <div style={{ width: 220, borderRight: '1px solid #eee', padding: 12, display: 'flex', flexDirection: 'column', gap: 6 }}>
      <h3 style={{ marginTop: 0 }}>Seismic UI</h3>
      {item('/spectrum', 'Spectrum')}
      {item('/waveform', 'Waveform')}
    </div>
  )
}

export function App() {
  return (
    <BrowserRouter>
      <div style={{ display: 'flex', minHeight: '100vh' }}>
        <Sidebar />
        <div style={{ flex: 1, padding: 16 }}>
          <Routes>
            <Route path="/" element={<Navigate to="/spectrum" replace />} />
            <Route path="/spectrum" element={<SpectrumPage />} />
            <Route path="/waveform" element={<WaveformPage />} />
            <Route path="*" element={<div>404</div>} />
          </Routes>
        </div>
      </div>
    </BrowserRouter>
  )
}

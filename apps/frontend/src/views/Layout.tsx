import React from 'react'
import { Link, Outlet, useLocation } from 'react-router-dom'

export function Layout() {
  const { pathname } = useLocation()
  const Item = ({ to, label }: { to: string; label: string }) => (
    <li style={{ marginBottom: 8 }}>
      <Link to={to} style={{ color: pathname === to ? '#0ea5e9' : '#111' }}>{label}</Link>
    </li>
  )

  return (
    <div style={{ display: 'grid', gridTemplateColumns: '240px 1fr', minHeight: '100vh' }}>
      <aside style={{ borderRight: '1px solid #ddd', padding: 16 }}>
        <h3>Seismic Frontend</h3>
        <nav>
          <ul style={{ listStyle: 'none', padding: 0 }}>
            <Item to="/spectrum" label="Spectrum" />
            <Item to="/waveform" label="Waveform" />
            <Item to="/histograms" label="Histogramas" />
            <Item to="/location-1d" label="Location 1D" />
          </ul>
        </nav>
      </aside>
      <main style={{ padding: 16 }}>
        <Outlet />
      </main>
    </div>
  )
}

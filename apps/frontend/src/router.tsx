import React from 'react'
import { createBrowserRouter } from 'react-router-dom'
import { SpectrumPage } from './views/SpectrumPage'
import { WaveformPage } from './views/WaveformPage'
import { HistogramsPage } from './views/HistogramsPage'
import { Location1DPage } from './views/Location1DPage'
import { Layout } from './views/Layout'

export const router = createBrowserRouter([
  {
    path: '/',
    element: <Layout />,
    children: [
      { index: true, element: <SpectrumPage /> },
      { path: 'spectrum', element: <SpectrumPage /> },
      { path: 'waveform', element: <WaveformPage /> },
      { path: 'histograms', element: <HistogramsPage /> },
      { path: 'location-1d', element: <Location1DPage /> },
    ],
  },
])

# Reflex Migration (Preview)

Este directorio contiene una migración progresiva de la app Streamlit a [Reflex](https://reflex.dev) para obtener mayor control de UI/UX, estado y rutas.

## Objetivos
- Mantener la lógica de dominio en `src/` intacta (procesamiento sísmico y agentes IA)
- Exponer una UI moderna basada en componentes con Reflex
- Reusar assets y estilos cuando aplique

## Estructura
```
reflex_app/
  README.md
  rxconfig.py          # Configuración de Reflex (app metadata)
  app.py               # Entry de la app Reflex
  pages/
    index.py           # Home / Uploader
    waveform.py        # Waveform Viewer
    spectrum.py        # Spectrum Analysis
    histograms.py      # Histogramas Gecko
    ai_interpreter.py  # Intérprete IA unificado
    location_1d.py     # Localización 1D
  components/
    layout.py          # Layout base (navbar/sidebar)
    charts.py          # Gráficos wrappers (Plotly/Vis)
    forms.py           # Formularios y controles
```

## Requisitos
- Python 3.9+
- `pip install reflex` (se añadirá a requirements en fase 2)

## Próximos pasos
1. Implementar `rxconfig.py` y `app.py`
2. Crear layout base con navegación
3. Portar páginas principales con estados Reactivos
4. Añadir bindings a `src/` (lectura/trazas/plots)
5. Añadir pruebas de UI (smoke) y CI

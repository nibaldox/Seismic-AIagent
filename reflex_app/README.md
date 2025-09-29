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
1. Instalar dependencias (incluye Reflex): `pip install -r requirements.txt`
2. Ejecutar app Reflex (dev):
  - Opción A (desde carpeta raíz): `python -m reflex_app.app`
  - Opción B (CLI de Reflex): `reflex run` (si config y estructura estándar)
3. Crear layout base con navegación (listo: `components/layout.py`)
4. Portar páginas principales con estados reactivos
5. Añadir bindings a `src/` (lectura/trazas/plots)
6. Añadir pruebas de UI (smoke) y CI

Notas:
- Los imports entre módulos usan rutas relativas (`from ..components...`) dentro del paquete `reflex_app`.
- Verás avisos de import hasta instalar `reflex`.

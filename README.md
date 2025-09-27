# SeismoAnalyzer Pro

Aplicación híbrida (escritorio/web) basada en Streamlit para análisis rápido de formas de onda sísmicas y telemetría, inspirada en Waves (Seismology Research Centre). Está orientada a sismólogos y a ingenieros de vibraciones que necesitan procesamiento local ágil, con la opción de asistencia por IA para interpretación contextual.

## Funcionalidades principales

- Ingesta multi‑formato (MiniSEED, SAC, SEG‑2, PC‑SUDS y exportes de Gecko) y lectura de metadatos Kelunji `.ss` con visualización en la app.
- Visualización interactiva de formas de onda con Plotly, filtros y sugerencias de picks (STA/LTA), conversión de unidades a m/s² y g, y anotaciones estilo micro‑g.
- Magnitud local (aproximada tipo Wood‑Anderson) y comparativa con estimación placeholder; advertencias y notas metodológicas en la UI.
- Localización 1D (superficie) por búsqueda en grilla, con proyección geográfica local usando `pyproj` (lat/lon → X/Y).
- Página dedicada: “📈 Histogramas Gecko” con modo serie temporal (eje X = fecha) y tres paneles verticales, cada uno con su variable; controles compartidos de resampleo, agregación y suavizado (rolling).
- Intérprete IA integrado para histogramas/telemetría: analiza tendencias, anomalías y posibles causas (sísmicas vs operativas), considerando tus selecciones, rango temporal visible y ajustes de gráfico.
- Agentes IA (Agno) multi‑proveedor configurables por YAML; caché de agentes y monitoreo opcional.

## Estructura del proyecto

```text
.
├── assets/
│   ├── css/
│   └── images/
├── config/
├── data/
├── docs/
├── pages/
├── src/
│   ├── ai_agent/
│   │   └── tools/
│   ├── core/
│   ├── streamlit_utils/
│   ├── utils/
│   └── visualization/
├── tests/
├── requirements.txt
└── streamlit_app.py
```

## Cómo ejecutar (Windows PowerShell)

```powershell
python -m venv .venv
./.venv/Scripts/Activate.ps1
pip install -r requirements.txt
streamlit run streamlit_app.py
```

- Variables de entorno: crea un archivo `.env` (ver `config/example.env`). Al menos, configura claves de API si usarás modelos en la nube.
- Datos de ejemplo: coloca archivos en `data/**/` (la página de Histogramas buscará `**/Histograma/**`).

## Páginas destacadas

- 📁 Uploader: carga de archivos y persistencia en sesión.
- 📊 Waveform Viewer: filtros, picks sugeridos, escalas en g y m/s², anotaciones y comparativa de magnitud.
- 📈 Histogramas Gecko:
  - Modo Serie temporal (X = fecha): tres gráficos verticales; selecciona variables por panel (por defecto Voltage, 3D peak y Temperature). Controles: resampleo, agregación (mean/max/min) y suavizado (rolling).
  - Modo Histograma: detecta automáticamente columnas agregadas (bin + count) o construye desde una columna numérica (elige bins, normalizar, acumulado y escala log).
  - Intérprete IA: el análisis utiliza exactamente tus variables seleccionadas y el rango temporal visible; también incorpora los ajustes (resample/agg/smoothing o bins/normalización). Responde en español.
- 🌍 Location 1D: localización superficial por grilla con proyección local.
- 🔍 Spectrum Analysis y 🤖 AI Interpreter: utilidades adicionales de análisis y orquestación IA.

## Configuración de IA (Agno)

- Archivo: `config/agno_config.yaml`.
- Tareas configuradas: `waveform_analysis`, `histogram_analysis`, `earthquake_search`, `report_generation`, `code_generation`, etc.
- Proveedores soportados: OpenRouter, OpenAI, Anthropic, Ollama.
- Variables de entorno típicas: `OPENROUTER_API_KEY`, `OPENAI_API_KEY`, `OLLAMA_HOST`.
- Notas: puedes cambiar el modelo preferido por tarea (por ejemplo, `histogram_analysis`) sin tocar código.

## Consejos de uso

- Si activas suavizado (rolling) en Histogramas, el intérprete IA recibirá el tamaño de ventana y los parámetros de resampleo para contextualizar la lectura de tendencias.
- En modo Histograma, el intérprete IA conoce si la curva es normalizada, acumulada o en escala log.
- Para proyecciones geográficas en `Location 1D`, asegúrate de tener `pyproj` instalado (ya incluido en `requirements.txt`).

## Desarrollo y pruebas

- Roadmap y notas: `docs/roadmap.md`, `docs/RDP.md`.
- Coordenadas y metadatos de estación: `docs/developer-station-coordinates.md`.
- Ejecutar pruebas (si están habilitadas):

```powershell
pytest
```

## Contenedor (opcional)

Construir y ejecutar con Docker:

```powershell
docker build -t seismoanalyzer .
docker run --rm -p 8501:8501 --env-file config/example.env seismoanalyzer
```

La imagen incluye dependencias científicas (ObsPy, etc.) y expone Streamlit en el puerto 8501.

## Licencia

MIT License. Ver `LICENSE` (pendiente).

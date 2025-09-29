# SeismoAnalyzer Pro

Aplicacion hibrida (escritorio/web) basada en Streamlit para analisis rapido de formas de onda sismicas y telemetria, inspirada en Waves (Seismology Research Centre). Esta orientada a sismologos y a ingenieros de vibraciones que necesitan procesamiento local agil, con la opcion de asistencia por IA para interpretacion contextual.

## Funcionalidades principales

- Ingesta multi-formato (MiniSEED, SAC, SEG-2, PC-SUDS y exportes de Gecko) y lectura de metadatos Kelunji `.ss` con visualizacion en la app.
- Visualizacion interactiva de formas de onda con Plotly, filtros y sugerencias de picks (STA/LTA), conversion de unidades a m/s^2 y g, y anotaciones estilo micro-g.
- Magnitud local (aproximada tipo Wood-Anderson) y comparativa con estimacion placeholder; advertencias y notas metodologicas en la UI.
- Localizacion 1D (superficie) por busqueda en grilla, con proyeccion geografica local usando `pyproj` (lat/lon -> X/Y).
- Pagina dedicada: "Histogramas Gecko" con modo serie temporal (eje X = fecha) y tres paneles verticales, cada uno con su variable; controles compartidos de resampleo, agregacion y suavizado (rolling).
- Interprete IA integrado para histogramas/telemetria: analiza tendencias, anomalias y posibles causas (sismicas vs operativas), considerando tus selecciones, rango temporal visible y ajustes de grafico.
- Agentes IA (Agno) multi-proveedor configurables por YAML; cache de agentes y monitoreo opcional.

## Estructura del proyecto

```text
.
 assets/
    css/
    images/
 config/
 data/
 docs/
 pages/
 src/
    ai_agent/
       tools/
    core/
    streamlit_utils/
    utils/
    visualization/
 tests/
 requirements.txt
 streamlit_app.py
```

## Como ejecutar (Windows PowerShell)

```powershell
python -m venv .venv
./.venv/Scripts/Activate.ps1
pip install -r requirements.txt
streamlit run streamlit_app.py
```

- Variables de entorno: crea un archivo `.env` (ver `config/example.env`). Al menos, configura claves de API si usaras modelos en la nube.
- Datos de ejemplo: coloca archivos en `data/**/` (la pagina de Histogramas buscara `**/Histograma/**`).

## Paginas destacadas

- Uploader: carga de archivos y persistencia en sesion.
- Waveform Viewer: filtros, picks sugeridos, escalas en g y m/s^2, anotaciones y comparativa de magnitud.
- Histogramas Gecko:
  - Modo Serie temporal (X = fecha): tres graficos verticales; selecciona variables por panel (por defecto Voltage, 3D peak y Temperature). Controles: resampleo, agregacion (mean/max/min) y suavizado (rolling).
  - Modo Histograma: detecta automaticamente columnas agregadas (bin + count) o construye desde una columna numerica (elige bins, normalizar, acumulado y escala log).
  - Interprete IA: el analisis utiliza exactamente tus variables seleccionadas y el rango temporal visible; tambien incorpora los ajustes (resample/agg/smoothing o bins/normalizacion). Responde en espanol.
- Location 1D: localizacion superficial por grilla con proyeccion local.
- Spectrum Analysis y AI Interpreter: utilidades adicionales de analisis y orquestacion IA.

## Configuracion de IA (Agno)

- Archivo: `config/agno_config.yaml`.
- Tareas configuradas: `waveform_analysis`, `histogram_analysis`, `earthquake_search`, `report_generation`, `code_generation`, etc.
- Proveedores soportados: OpenRouter, OpenAI, Anthropic, Ollama.
- Variables de entorno tipicas: `OPENROUTER_API_KEY`, `OPENAI_API_KEY`, `OLLAMA_HOST`.
- Notas: puedes cambiar el modelo preferido por tarea (por ejemplo, `histogram_analysis`) sin tocar codigo.

## Consejos de uso

- Si activas suavizado (rolling) en Histogramas, el interprete IA recibira el tamano de ventana y los parametros de resampleo para contextualizar la lectura de tendencias.
- En modo Histograma, el interprete IA conoce si la curva es normalizada, acumulada o en escala log.
- Para proyecciones geograficas en `Location 1D`, asegurate de tener `pyproj` instalado (ya incluido en `requirements.txt`).

## Desarrollo y pruebas

- Roadmap y notas: `docs/roadmap.md`, `docs/RDP.md`.
- Coordenadas y metadatos de estación: `docs/developer-station-coordinates.md`.

### Pruebas mínimas iniciales

- 2 tests en `src/core` (`test_core_basic.py`)
- 2 tests en `src/ai_agent` (`test_ai_agent_basic.py`)
- 1 test de integración UI (`test_ui_smoke.py`)

Ejecutar todas las pruebas:

```powershell
pytest
```

## Contenedor (opcional)

Construir y ejecutar con Docker:

```powershell
docker build -t seismoanalyzer .
docker run --rm -p 8501:8501 --env-file config/example.env seismoanalyzer
```

La imagen incluye dependencias cientificas (ObsPy, etc.) y expone Streamlit en el puerto 8501.

## Licencia

MIT License. Ver `LICENSE` (pendiente).

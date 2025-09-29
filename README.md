# 🌊 Seismic AIagent - Análisis Sísmico Inteligente# SeismoAnalyzer Pro



[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)Aplicacion hibrida (escritorio/web) basada en Streamlit para analisis rapido de formas de onda sismicas y telemetria, inspirada en Waves (Seismology Research Centre). Esta orientada a sismologos y a ingenieros de vibraciones que necesitan procesamiento local agil, con la opcion de asistencia por IA para interpretacion contextual.

[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)

[![Streamlit](https://img.shields.io/badge/Streamlit-1.28+-red.svg)](https://streamlit.io/)## Funcionalidades principales

[![AI Powered](https://img.shields.io/badge/AI-Powered-green.svg)](https://docs.agno.com/)

- Ingesta multi-formato (MiniSEED, SAC, SEG-2, PC-SUDS y exportes de Gecko) y lectura de metadatos Kelunji `.ss` con visualizacion en la app.

## 📋 Descripción- Visualizacion interactiva de formas de onda con Plotly, filtros y sugerencias de picks (STA/LTA), conversion de unidades a m/s^2 y g, y anotaciones estilo micro-g.

- Magnitud local (aproximada tipo Wood-Anderson) y comparativa con estimacion placeholder; advertencias y notas metodologicas en la UI.

**Seismic AIagent** es una aplicación híbrida (escritorio/web) basada en Streamlit para análisis rápido y inteligente de formas de onda sísmicas, telemetría y datos de acelerómetros. Diseñada para sismólogos, ingenieros de vibraciones y personal operativo que requieren:- Localizacion 1D (superficie) por busqueda en grilla, con proyeccion geografica local usando `pyproj` (lat/lon -> X/Y).

- Pagina dedicada: "Histogramas Gecko" con modo serie temporal (eje X = fecha) y tres paneles verticales, cada uno con su variable; controles compartidos de resampleo, agregacion y suavizado (rolling).

- ✅ **Procesamiento local ágil** sin dependencia de servicios externos- Interprete IA integrado para histogramas/telemetria: analiza tendencias, anomalias y posibles causas (sismicas vs operativas), considerando tus selecciones, rango temporal visible y ajustes de grafico.

- 🤖 **Asistencia IA especializada** para interpretación contextual- Agentes IA (Agno) multi-proveedor configurables por YAML; cache de agentes y monitoreo opcional.

- 📊 **Visualización interactiva** con análisis espectral avanzado

- 🔍 **Interpretación operativa** en lenguaje claro y práctico## Estructura del proyecto



---```text

.

## 🚀 Funcionalidades Principales assets/

    css/

### 📁 Gestión de Datos    images/

- **Multi-formato**: MiniSEED, SAC, SEG-2, PC-SUDS, exportes Gecko config/

- **Metadatos**: Lectura automática de archivos `.ss` (Kelunji) con visualización integrada data/

- **Carga masiva**: Procesamiento batch con persistencia en sesión docs/

 pages/

### 📈 Análisis de Formas de Onda src/

- **Visualización interactiva** con Plotly (zoom, pan, selección)    ai_agent/

- **Filtros digitales** configurables (pasa-banda, pasa-alto, pasa-bajo)       tools/

- **Detección automática** de llegadas P/S con algoritmo STA/LTA    core/

- **Conversión de unidades** (m/s², g, cuentas digitales)    streamlit_utils/

- **Anotaciones especializadas** para micro-g y vibraciones    utils/

- **🤖 Intérprete IA integrado** con análisis operativo    visualization/

 tests/

### 🔢 Magnitud Sísmica (ML-WA) requirements.txt

- **Estimación Wood-Anderson** con respuesta instrumental real streamlit_app.py

- **Simulación de sismómetro** WA clásico (To=0.8s, h=0.7)```

- **Comparativa automática** con catálogos externos

- **Advertencias metodológicas** y metadatos de calidad## Como ejecutar (Windows PowerShell)



### 📊 Análisis Espectral Avanzado```powershell

- **Espectrogramas** configurables (NFFT, overlap, ventanas)python -m venv .venv

- **FFT** con escalas logarítmicas y límites de frecuencia./.venv/Scripts/Activate.ps1

- **Densidad Espectral (PSD)** usando método de Welchpip install -r requirements.txt

- **🤖 Panel IA especializado** para interpretación de frecuenciasstreamlit run streamlit_app.py

- **Layout optimizado** con controles horizontales compactos```



### 📉 Telemetría y Series Temporales- Variables de entorno: crea un archivo `.env` (ver `config/example.env`). Al menos, configura claves de API si usaras modelos en la nube.

- **Modo serie temporal** con tres paneles verticales configurables- Datos de ejemplo: coloca archivos en `data/**/` (la pagina de Histogramas buscara `**/Histograma/**`).

- **Controles avanzados**: remuestreo, agregación, suavizado

- **Variables típicas**: Voltage, 3D_Peak, Temperature, N/E/Z## Paginas destacadas

- **🤖 Análisis IA contextual** considerando parámetros de visualización

- Uploader: carga de archivos y persistencia en sesion.

### 🗺️ Localización Sísmica- Waveform Viewer: filtros, picks sugeridos, escalas en g y m/s^2, anotaciones y comparativa de magnitud.

- **Localización 1D** (superficie) por búsqueda en grilla- Histogramas Gecko:

- **Proyección geográfica** local usando `pyproj` (lat/lon ↔ X/Y)  - Modo Serie temporal (X = fecha): tres graficos verticales; selecciona variables por panel (por defecto Voltage, 3D peak y Temperature). Controles: resampleo, agregacion (mean/max/min) y suavizado (rolling).

- **Múltiples estaciones** con coordenadas geográficas  - Modo Histograma: detecta automaticamente columnas agregadas (bin + count) o construye desde una columna numerica (elige bins, normalizar, acumulado y escala log).

- **Modelos de velocidad** configurables (Vp, Vs)  - Interprete IA: el analisis utiliza exactamente tus variables seleccionadas y el rango temporal visible; tambien incorpora los ajustes (resample/agg/smoothing o bins/normalizacion). Responde en espanol.

- Location 1D: localizacion superficial por grilla con proyeccion local.

### 🤖 Sistema IA Multi-Agente- Spectrum Analysis y AI Interpreter: utilidades adicionales de analisis y orquestacion IA.

- **Agentes especializados** para cada tipo de análisis

- **Equipo coordinado** con análisis integral multi-fuente## Configuracion de IA (Agno)

- **Compatibilidad Agno v2** con streaming y memoria compartida

- **Multi-proveedor**: OpenRouter, OpenAI, Anthropic, Ollama- Archivo: `config/agno_config.yaml`.

- **Prompts operativos** sin jerga técnica, enfocados en recomendaciones- Tareas configuradas: `waveform_analysis`, `histogram_analysis`, `earthquake_search`, `report_generation`, `code_generation`, etc.

- Proveedores soportados: OpenRouter, OpenAI, Anthropic, Ollama.

---- Variables de entorno tipicas: `OPENROUTER_API_KEY`, `OPENAI_API_KEY`, `OLLAMA_HOST`.

- Notas: puedes cambiar el modelo preferido por tarea (por ejemplo, `histogram_analysis`) sin tocar codigo.

## 🏗️ Arquitectura del Proyecto

## Consejos de uso

```

📦 Seismic-AIagent/- Si activas suavizado (rolling) en Histogramas, el interprete IA recibira el tamano de ventana y los parametros de resampleo para contextualizar la lectura de tendencias.

├── 📁 assets/css/          # Estilos personalizados- En modo Histograma, el interprete IA conoce si la curva es normalizada, acumulada o en escala log.

├── 📁 config/              # Configuraciones YAML y variables- Para proyecciones geograficas en `Location 1D`, asegurate de tener `pyproj` instalado (ya incluido en `requirements.txt`).

├── 📁 data/                # Datos de ejemplo y pruebas

├── 📁 docs/                # Documentación técnica## Desarrollo y pruebas

├── 📁 pages/               # Páginas Streamlit

│   ├── 📁 Uploader         # Carga de archivos- Roadmap y notas: `docs/roadmap.md`, `docs/RDP.md`.

│   ├── 📊 Waveform_Viewer  # Visualización de ondas + IA- Coordenadas y metadatos de estación: `docs/developer-station-coordinates.md`.

│   ├── 🔍 Spectrum_Analysis # Análisis espectral + IA

│   ├── 📈 Histogramas_Gecko # Series temporales + IA### Pruebas mínimas iniciales

│   ├── 🌍 Location_1D      # Localización sísmica

│   ├── 🤖 AI_Interpreter   # Intérprete IA individual- 2 tests en `src/core` (`test_core_basic.py`)

│   └── 🧩 Equipo_IA        # Análisis multi-agente- 2 tests en `src/ai_agent` (`test_ai_agent_basic.py`)

├── 📁 src/- 1 test de integración UI (`test_ui_smoke.py`)

│   ├── 🤖 ai_agent/        # Sistema IA y agentes

│   ├── ⚙️ core/            # Algoritmos sísmicosEjecutar todas las pruebas:

│   ├── 🖥️ streamlit_utils/ # Utilidades UI

│   ├── 🔧 utils/           # Funciones auxiliares```powershell

│   └── 📊 visualization/   # Gráficos y visualizaciónpytest

└── 📁 tests/               # Tests unitarios y de integración```

```

## Contenedor (opcional)

---

Construir y ejecutar con Docker:

## ⚡ Instalación y Configuración

```powershell

### 🔧 Instalación Local (Recomendado)docker build -t seismoanalyzer .

docker run --rm -p 8501:8501 --env-file config/example.env seismoanalyzer

```powershell```

# Clonar repositorio

git clone https://github.com/nibaldox/Seismic-AIagent.gitLa imagen incluye dependencias cientificas (ObsPy, etc.) y expone Streamlit en el puerto 8501.

cd Seismic-AIagent

## Licencia

# Crear entorno virtual

python -m venv .venvMIT License. Ver `LICENSE` (pendiente).

./.venv/Scripts/Activate.ps1  # Windows PowerShell
# source .venv/bin/activate   # Linux/macOS

# Instalar dependencias
pip install -r requirements.txt

# Ejecutar aplicación
streamlit run streamlit_app.py
```

### 🐳 Docker (Alternativo)

```bash
docker build -t seismic-aiagent .
docker run --rm -p 8501:8501 --env-file config/example.env seismic-aiagent
```

### 🔑 Variables de Entorno

Crea `.env` basado en `config/example.env`:

```env
# APIs de IA (opcional - usar modelos locales si no se configuran)
OPENROUTER_API_KEY=tu_clave_openrouter
OPENAI_API_KEY=tu_clave_openai
ANTHROPIC_API_KEY=tu_clave_anthropic

# Modelos locales
OLLAMA_HOST=http://localhost:11434

# Configuración aplicación
STREAMLIT_THEME=dark
LOG_LEVEL=INFO
```

---

## 🎯 Guía de Uso Rápido

### 1. 📁 Cargar Datos
1. Ir a **📁 Uploader**
2. Arrastrar archivos MiniSEED, SAC, o Gecko
3. Verificar metadatos y calidad de señal

### 2. 📊 Analizar Formas de Onda
1. **📊 Waveform Viewer** → seleccionar trazas
2. Aplicar filtros si es necesario
3. **🤖 Ejecutar análisis IA** para interpretación
4. Revisar picks automáticos (STA/LTA)
5. Calcular magnitud ML-WA

### 3. 🔍 Análisis Espectral  
1. **🔍 Spectrum Analysis** → seleccionar traza
2. Elegir tipo: Espectrograma, FFT, o PSD
3. Ajustar parámetros (NFFT, overlap, ventanas)
4. **🤖 Panel IA** interpretará automáticamente frecuencias

### 4. 📈 Telemetría Operativa
1. **📈 Histogramas Gecko** → cargar datos CSV
2. Configurar variables por panel (Voltage, 3D_Peak, etc.)
3. Aplicar remuestreo/suavizado según necesidad
4. **🤖 Análisis IA contextual** con recomendaciones

### 5. 🧩 Análisis Integral
1. **🧩 Equipo IA** → configurar contexto multi-fuente
2. Combinar datos de telemetría, ondas, localización
3. **🤖 Análisis coordinado** por equipo de agentes especializados

---

## 🤖 Sistema IA - Configuración Avanzada

### 📝 Archivo de Configuración: `config/agno_config.yaml`

```yaml
seismic_interpreter:
  default_model:
    provider: "openrouter" 
    id: "deepseek/deepseek-chat-v3.1:free"
    
  task_models:
    waveform_analysis:
      preferred: "deepseek/deepseek-chat-v3.1:free"
    spectrum_analysis:
      preferred: "deepseek/deepseek-chat-v3.1:free"  
    histogram_analysis:
      preferred: "deepseek/deepseek-chat-v3.1:free"
    team_analysis:
      preferred: "deepseek/deepseek-chat-v3.1:free"
```

### 🎯 Agentes Especializados Disponibles

| Agente | Función | Expertise |
|--------|---------|-----------|
| **🌊 Waveform Analysis** | Análisis de formas de onda | Fases P/S, calidad señal, fuentes sísmicas |
| **📊 Spectrum Analysis** | Interpretación espectral | Frecuencias dominantes, ruido, filtrado |
| **📈 Histogram Analysis** | Telemetría operativa | Tendencias, anomalías, estado equipos |
| **🔍 Earthquake Search** | Catálogos sísmicos | Contexto regional, correlaciones |
| **🧩 Team Analysis** | Coordinación integral | Síntesis multi-fuente, recomendaciones |

---

## 📚 Documentación Técnica

### 🔬 APIs y Módulos Principales

#### Core Seismology (`src/core/`)
- `signal_processing.py` - Filtros digitales y preprocesamiento
- `picking.py` - Detección automática P/S (STA/LTA)
- `magnitude.py` - Estimación ML-WA con respuesta instrumental
- `location/one_d_location.py` - Localización superficial

#### AI System (`src/ai_agent/`)  
- `seismic_interpreter.py` - Framework multi-agente principal
- `tools/` - Herramientas especializadas (USGS, geográficas)

#### Visualization (`src/visualization/`)
- `waveform_plots.py` - Gráficos de formas de onda
- `spectrum_plots.py` - Espectrogramas, FFT, PSD

### 🧪 Testing y Desarrollo

```bash
# Ejecutar tests
pytest tests/ -v

# Tests específicos  
pytest tests/test_core.py          # Algoritmos sísmicos
pytest tests/test_ai_agent.py      # Sistema IA
pytest tests/test_integration.py   # UI e integración

# Linting y formato
black src/ tests/
flake8 src/ tests/
```

### 📊 Métricas y Monitoreo

La aplicación incluye monitoreo automático de:
- ⏱️ **Tiempo de respuesta** de agentes IA  
- 📈 **Cache hit rate** para optimización
- 🚨 **Errores y fallbacks** del sistema IA
- 📊 **Uso de memoria** y recursos

---

## 🎨 Características Avanzadas

### 🔄 Flujo de Trabajo Típico

1. **Carga** → Cargar datos sísmicos multi-formato
2. **Preprocesamiento** → Filtros, corrección baseline  
3. **Análisis** → Formas de onda, espectros, telemetría
4. **IA Contextual** → Interpretación especializada por tipo
5. **Síntesis** → Equipo multi-agente para análisis integral
6. **Reporte** → Recomendaciones operativas claras

### ⚙️ Optimizaciones de Rendimiento

- **🗂️ Cache inteligente** de agentes IA reutilizables
- **⚡ Procesamiento vectorizado** con NumPy/SciPy
- **🔄 Streaming** de análisis en tiempo real (Agno v2)
- **💾 Gestión memoria** optimizada para datasets grandes

### 🎯 Casos de Uso Especializados

#### 🏢 **Monitoreo Industrial**
- Vibración de maquinaria y estructuras
- Alertas automáticas por umbrales
- Análisis de tendencias operativas

#### 🌋 **Sismología Regional**  
- Detección y localización eventos
- Correlación con catálogos globales
- Estimación magnitud preliminar

#### 🔬 **Investigación Científica**
- Procesamiento batch de datasets
- Análisis espectral detallado  
- Exportación datos procesados

---

## 🤝 Contribuir al Proyecto

### 🐛 Reportar Issues
- Usar [GitHub Issues](https://github.com/nibaldox/Seismic-AIagent/issues)
- Incluir logs, capturas, datos de ejemplo
- Especificar versiones (Python, OS, dependencias)

### 🔧 Pull Requests
1. Fork del repositorio
2. Crear branch: `git checkout -b feature/nueva-funcionalidad`
3. Tests: `pytest tests/`
4. Commit: `git commit -am 'Add nueva-funcionalidad'`  
5. Push: `git push origin feature/nueva-funcionalidad`
6. Abrir Pull Request

### 📋 Roadmap y TODOs
Ver `docs/roadmap.md` y `docs/bitacora/todo-orden-ejecucion.md`

---

## 📄 Licencia

Este proyecto está licenciado bajo la Licencia MIT - ver el archivo [LICENSE](LICENSE) para detalles.

---

## 👥 Autores y Reconocimientos

- **Desarrollador Principal**: nibaldox
- **Framework IA**: [Agno](https://docs.agno.com/)
- **Visualización**: [Streamlit](https://streamlit.io/) + [Plotly](https://plotly.com/)
- **Sismología**: [ObsPy](https://obspy.org/)

---

## 📞 Soporte y Contacto

- 📖 **Documentación**: `docs/` directory
- 🐛 **Issues**: [GitHub Issues](https://github.com/nibaldox/Seismic-AIagent/issues)
- 💬 **Discusiones**: [GitHub Discussions](https://github.com/nibaldox/Seismic-AIagent/discussions)

---

**🌊 Seismic AIagent - Transformando el análisis sísmico con IA especializada**

*Versión actual: v2.0 (Septiembre 2025)*
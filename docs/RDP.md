# REQUERIMIENTOS DEL SOFTWARE - ANALIZADOR SÍSMICO RÁPIDO

## Versión 1.0 | Fecha: Septiembre 2025

## 💡 **SIGUIENTES PASOS PARA IMPLEMENTACIÓN CON CURSOR**

### 1. Setup Inicial del Proyecto Streamlit

```bash
# Comando para Cursor: "Create a new Streamlit seismic analysis project"
mkdir SeismoAnalyzer
cd SeismoAnalyzer

# Create main app structure  
streamlit hello  # Test installation
```

### 2. Comandos específicos para Cursor

```
"Create the main streamlit_app.py file following the requirements architecture"

"Implement the data reader module in src/core/data_reader.py using ObsPy"  

"Create the waveform viewer page in pages/01_📊_Waveform_Viewer.py with Plotly integration"

"Add session state management following the best practices in the requirements"

"Implement the file uploader component with error handling for MiniSEED files"

"NUEVO: Create the AI agent system in src/ai_agent/seismic_interpreter.py using Agno-AGI framework"

"NUEVO: Implement USGS and EMSC search tools for the AI agent with internet access"

"NUEVO: Create the AI interpreter page in pages/07_🤖_AI_Interpreter.py with real-time analysis"

"NUEVO: Add automatic earthquake search and geological context to the AI agent"

"NUEVO: Implement the report generation agent with Markdown output"
```

### 3. Orden de Desarrollo Recomendado

1. **🏗️ Estructura base** → `streamlit_app.py` + navigation
2. **📁 Data loading** → File uploader + ObsPy integration  
3. **📊 Basic plotting** → Simple waveform visualization
4. **🎛️ Interactive controls** → Sidebar controls + session state
5. **🤖 AI Agent setup** → Agno-AGI integration + basic interpretation  
6. **🌐 Internet tools** → USGS/EMSC APIs + web search capabilities
7. **🔍 Advanced features** → Spectral analysis + phase picking
8. **📄 AI Reports** → Automated report generation with context

### 4. Testing en cada etapa

```bash
# Ejecutar después de cada módulo implementado
streamlit run streamlit_app.py

# Test específico del agente IA (NUEVO)
python -m pytest tests/test_ai_agent.py

# Verificar APIs del agente (NUEVO)
python src/ai_agent/tools/test_usgs_connection.py
```

### 5. Priorización para Cursor

- **FASE 1:** File upload + basic waveform display (funcionalidad核心)
- **FASE 2:** Interactive controls + filtering (UX crítica)  
- **FASE 3:** AI agent setup + basic interpretation (NUEVO - diferenciador clave)
- **FASE 4:** AI contextual search + automated reports (NUEVO - valor agregado)
- **FASE 5:** Advanced analysis tools (nice-to-have)

### 6. Variables de Entorno Requeridas (ACTUALIZADO)

```bash
# .env file para múltiples proveedores AI

# === PROVEEDORES DE IA ===
# OpenAI (opcional - para máximo rendimiento)
OPENAI_API_KEY=your_openai_api_key_here

# Anthropic (opcional - para Claude directo) 
ANTHROPIC_API_KEY=your_claude_api_key_here

# OpenRouter (NUEVO - acceso unificado a 100+ modelos)
OPENROUTER_API_KEY=your_openrouter_api_key_here

# Ollama (NUEVO - modelos locales gratuitos)
OLLAMA_HOST=http://localhost:11434
OLLAMA_DEFAULT_MODEL=llama3.2

# === CONFIGURACIÓN DE AGENTE ===
AI_MODEL_SELECTION=cost_optimized  # o "performance_first", "privacy_first"
AI_COST_LIMIT=5.0                 # Límite de gasto por sesión en USD
AI_FALLBACK_STRATEGY=true         # Failover automático entre proveedores

# === APIS SÍSMICAS ===
USGS_API_URL=https://earthquake.usgs.gov/fdsnws/event/1/
EMSC_API_URL=https://www.seismicportal.eu/fdsnws/event/1/

# === CONFIGURACIÓN GENERAL ===
AGNO_LOG_LEVEL=INFO
STREAMLIT_SERVER_MAX_UPLOAD_SIZE=1000  # 1GB para archivos sísmicos grandes
```

### 7. Comandos de Setup para Ollama (NUEVO)

```bash
# Instalar Ollama en el sistema
curl -fsSL https://ollama.ai/install.sh | sh

# Descargar modelos recomendados (ejecutar una sola vez)
ollama pull llama3.2      # Modelo principal (4GB)
ollama pull gemma2:2b     # Modelo ligero (1.6GB) 
ollama pull mistral       # Alternativa sólida (4GB)

# Verificar instalación
ollama list
ollama serve  # Mantener corriendo en una terminal

# Test de Python + Agno
python -c "
from agno.models.ollama import OllamaChat
model = OllamaChat(id='llama3.2')
print('Ollama configurado correctamente!')
"
```

### 8. Test de Conectividad Multi-Proveedor (NUEVO)

```bash
# Script para verificar todos los proveedores
python src/ai_agent/test_providers.py

# Salida esperada:
# ✅ Ollama: llama3.2 (local)
# ✅ OpenRouter: claude-3.5-sonnet (cloud) 
# ✅ OpenAI: gpt-4o (cloud)
# 🎯 Selected strategy: cost_optimized
# 💰 Estimated session cost: $0.05
```

---

## 📋 **DESCRIPCIÓN DEL PROYECTO**

Desarrollar una aplicación de escritorio en Python para análisis sísmico local, inspirada en el software Waves del Seismology Research Centre. El objetivo es crear una herramienta rápida y eficiente para análisis de datos sísmicos sin dependencias de internet.

**Nombre del Proyecto:** `SeismoAnalyzer Pro`  
**Lenguaje Principal:** Python 3.9+  
**Tipo:** Aplicación de escritorio standalone  
**Licencia:** MIT (uso interno)

---

## 🎯 **OBJETIVOS PRINCIPALES**

### Objetivo General

Crear un software de análisis sísmico local con capacidades de visualización, procesamiento y análisis de formas de onda para uso profesional en sismología.

### Objetivos Específicos

- ✅ Lectura rápida de múltiples formatos sísmicos estándar
- ✅ Visualización interactiva de formas de onda multi-canal
- ✅ Análisis espectral avanzado con FFT y espectrogramas  
- ✅ Herramientas de picking manual de fases P y S
- ✅ Localización básica de sismos con modelos 1D
- ✅ Cálculo de magnitudes personalizables
- ✅ Generación de reportes automáticos en PDF

---

## 🌟 **VENTAJAS DE STREAMLIT PARA ANÁLISIS SÍSMICO**

### ¿Por qué Streamlit es ideal para este proyecto?

**🚀 Desarrollo Rápido**

- Interfaz web moderna sin HTML/CSS/JavaScript
- Hot reloading automático durante desarrollo
- Componentes interactivos built-in (sliders, selectbox, etc.)

**📊 Visualización Científica Superior**

- Integración nativa con Plotly para gráficos interactivos
- Soporte excelente para matplotlib y seaborn
- Widgets interactivos que se actualizan automáticamente

**🔧 Funcionalidades Específicas para Sismología**

- File uploader perfecto para archivos MiniSEED/SAC
- Session state ideal para mantener datos cargados
- Sidebar natural para controles de filtrado y parámetros
- Layout en columnas perfecto para comparar múltiples análisis

**🌐 Deployment Sencillo**

- Aplicación web que funciona en cualquier navegador
- Fácil compartir con colegas (URL local o cloud)
- No requiere instalación para usuarios finales
- Responsive design automático

## 🛠️ **STACK TECNOLÓGICO RECOMENDADO**

### Core Libraries

```python
# Framework principal
streamlit >= 1.28.0     # Framework de aplicación web/GUI
streamlit-aggrid >= 0.3.4 # Tablas interactivas avanzadas

# Análisis sísmico
obspy >= 1.4.0          # Manejo de datos sísmicos
numpy >= 1.24.0         # Computación numérica
scipy >= 1.10.0         # Análisis científico

# Framework de Agente IA (Agno-AGI)
agno >= 2.6.0           # Framework para agentes IA ultra-rápido
duckduckgo-search >= 6.1.0 # Herramientas de búsqueda web
requests >= 2.31.0      # Para web scraping y APIs
python-dotenv >= 1.0.0  # Manejo de variables de entorno

# Modelos de IA para el agente (MÚLTIPLES PROVEEDORES)
openai >= 1.30.0        # OpenAI GPT models
anthropic >= 0.25.0     # Claude models
google-generativeai >= 0.5.0 # Gemini models

# Modelos locales y agregadores
ollama >= 0.1.0         # NUEVO: Modelos locales (Llama, Mistral, etc.)
httpx >= 0.25.0         # NUEVO: Para OpenRouter API calls  
litellm >= 1.40.0       # NUEVO: Unified interface para múltiples LLMs

# Visualización interactiva
plotly >= 5.15.0        # Gráficos interactivos principales
matplotlib >= 3.6.0     # Gráficos complementarios
seaborn >= 0.12.0       # Visualización estadística

# Componentes Streamlit adicionales
streamlit-plotly-events >= 0.1.6  # Eventos en gráficos Plotly
streamlit-option-menu >= 0.3.6    # Menús de navegación
streamlit-aggrid >= 0.3.4          # Grillas de datos avanzadas
streamlit-folium >= 0.15.0         # Mapas interactivos

# Procesamiento de datos
pandas >= 2.0.0         # Manipulación de datos
h5py >= 3.8.0           # Manejo de archivos HDF5

# Reportes y export  
reportlab >= 4.0.0      # Generación de PDFs
openpyxl >= 3.1.0       # Export a Excel
fpdf2 >= 2.7.6          # PDFs alternativos
```

### Herramientas de desarrollo

```bash
# Testing
pytest >= 7.0.0
pytest-cov >= 4.0.0

# Linting y formato
black >= 23.0.0
flake8 >= 6.0.0  
mypy >= 1.0.0

# Packaging
pyinstaller >= 5.10.0  # Para ejecutables
```

## 🚀 **EJECUCIÓN Y DEPLOYMENT**

### Desarrollo Local

```bash
# Instalar dependencias
pip install -r requirements.txt

# Ejecutar aplicación principal
streamlit run streamlit_app.py

# Ejecutar página específica
streamlit run pages/01_📊_Waveform_Viewer.py

# Con configuración personalizada
streamlit run streamlit_app.py --server.port 8502
```

### Estructura de Configuración Streamlit

```toml
# config/streamlit_config.toml
[global]
dataFrameSerialization = "legacy"

[server]
port = 8501
enableCORS = false
enableXsrfProtection = false
maxUploadSize = 1000  # 1GB for large seismic files

[browser]
gatherUsageStats = false

[theme]
primaryColor = "#FF6B35"     # Seismic orange
backgroundColor = "#FFFFFF"
secondaryBackgroundColor = "#F0F2F6"
textColor = "#262730"
font = "sans serif"
```

### Deployment Options

```bash
# 1. Local network deployment
streamlit run streamlit_app.py --server.address 0.0.0.0

# 2. Streamlit Cloud (free)
# Push to GitHub and connect to Streamlit Cloud

# 3. Docker deployment  
docker build -t seismo-analyzer .
docker run -p 8501:8501 seismo-analyzer

# 4. Heroku deployment
# Using Procfile and requirements.txt
```

---

## 🏗️ **ARQUITECTURA DEL SOFTWARE**

### Estructura de Directorios

```
SeismoAnalyzer/
├── streamlit_app.py      # Aplicación principal de Streamlit
├── pages/                # Páginas de la aplicación
│   ├── 01_📊_Waveform_Viewer.py    # Visualizador de ondas principal
│   ├── 02_🔍_Spectrum_Analysis.py  # Análisis espectral
│   ├── 03_🎯_Phase_Picking.py      # Herramientas de picking
│   ├── 04_🌍_Location_Analysis.py  # Localización de sismos
│   ├── 05_📈_Magnitude_Calc.py     # Cálculos de magnitud
│   ├── 06_📊_Histogram_Analysis.py # Análisis de histogramas Gecko
│   ├── 07_🤖_AI_Interpreter.py     # NUEVO: Agente IA de interpretación
│   └── 08_📄_Reports.py            # Generación de reportes
├── src/                  # Lógica de negocio principal
│   ├── core/                # Core sísmico
│   │   ├── data_reader.py      # Lectura de archivos sísmicos
│   │   ├── signal_processor.py # Procesamiento de señales
│   │   ├── location_engine.py  # Algoritmos de localización
│   │   └── magnitude_calc.py   # Cálculos de magnitud
│   ├── ai_agent/            # NUEVO: Sistema de Agente IA
│   │   ├── seismic_interpreter.py  # Agente principal de interpretación
│   │   ├── earthquake_search.py    # Búsqueda de sismos cercanos
│   │   ├── regional_analysis.py    # Análisis de contexto regional
│   │   ├── report_generator.py     # Generador de informes IA
│   │   └── tools/                  # Herramientas específicas del agente
│   │       ├── seismic_databases.py    # Acceso a bases datos sísmicas
│   │       ├── geographic_tools.py     # Herramientas geográficas
│   │       └── web_search_tools.py     # Búsquedas web especializadas
│   ├── visualization/       # Componentes de visualización
│   │   ├── waveform_plots.py   # Plots de formas de onda
│   │   ├── spectrum_plots.py   # Plots espectrales
│   │   ├── map_plots.py        # Mapas de localización
│   │   └── interactive_plots.py # Plots interactivos con Plotly
│   ├── streamlit_utils/     # Utilidades específicas de Streamlit
│   │   ├── session_state.py    # Manejo de estado de sesión
│   │   ├── file_uploader.py    # Componentes de carga de archivos
│   │   ├── sidebar_controls.py # Controles de sidebar
│   │   └── plot_interactions.py # Interacciones con gráficos
│   └── utils/               # Utilidades generales
│       ├── file_manager.py     # Gestión de archivos
│       ├── config.py           # Configuraciones
│       └── logger.py           # Sistema de logs
├── data/                    # Datos de prueba y ejemplos
├── config/                 # Archivos de configuración
│   ├── streamlit_config.toml   # Configuración de Streamlit
│   ├── agno_config.yaml        # NUEVO: Configuración del agente IA
│   └── app_settings.yaml       # Configuraciones de aplicación
├── .env                     # NUEVO: Variables de entorno para APIs
├── assets/                 # Assets estáticos
│   ├── images/               # Imágenes y logos
│   └── css/                  # Estilos CSS personalizados
├── tests/                  # Pruebas unitarias
├── docs/                   # Documentación
└── requirements.txt        # Dependencias
```

### Patrones de Diseño

- **Page-Based Architecture** para organización modular de funcionalidades
- **Reactive Programming** aprovechando el modelo reactivo de Streamlit
- **Session State Management** para persistencia de datos entre interacciones
- **Component-Based Design** para reutilización de elementos de UI
- **Factory Pattern** para creación de lectores de archivos específicos
- **Observer Pattern** para actualización automática de visualizaciones

---

## ⚙️ **FUNCIONALIDADES DETALLADAS**

### 🗂️ **MÓDULO 1: LECTURA DE ARCHIVOS**

**Prioridad:** ALTA  
**Archivos:** `src/core/data_reader.py`

#### Funcionalidades específicas

- [x] **Lector MiniSEED** usando ObsPy
  - Soporte para múltiples archivos simultáneos
  - Detección automática de metadatos
  - Validación de integridad de datos

- [x] **Lector SAC** (Seismic Analysis Code)
  - Import completo de headers SAC
  - Manejo de datos binarios y ASCII
  
- [x] **Lector PC-SUDS/SS-file**
  - Parsing de formato propietario
  - Extracción de información de ganancia y sensibilidad

- [x] **Lector SEG-2**
  - Para datos de ingeniería sísmica
  - Soporte para múltiples traces

- [x] **Lector de Histogramas Gecko**
  - Parsing de archivos binarios Gecko
  - Extracción de valores PGA, PGV, PGD

#### Criterios de aceptación

```python
# Ejemplo de uso esperado
reader = DataReader()
stream = reader.load_file("earthquake_data.mseed")
print(f"Cargados {len(stream)} traces")
print(f"Duración: {stream[0].stats.endtime - stream[0].stats.starttime}s")
```

### 📊 **MÓDULO 2: VISUALIZACIÓN DE FORMAS DE ONDA**  

**Prioridad:** ALTA
**Archivos:** `pages/01_📊_Waveform_Viewer.py`, `src/visualization/waveform_plots.py`

#### Funcionalidades específicas

- [x] **Visualización multi-canal interactiva**
  - Hasta 50+ canales con Plotly subplots
  - Zoom y pan sincronizado entre canales
  - Normalización automática con selectbox

- [x] **Controles de Streamlit**
  - Sliders para ventana temporal
  - Selectbox para selección de estaciones
  - Checkbox para mostrar/ocultar canales
  - Botones para acciones rápidas

- [x] **Interactividad avanzada con Plotly**
  - Click events para picking de fases
  - Hover tooltips con información detallada
  - Brush selection para análisis de segmentos
  - Crossfilter entre múltiples gráficos

- [x] **Sidebar controls**
  - Time window selector (slider)
  - Amplitude scaling controls
  - Filter controls (high-pass, low-pass, bandpass)
  - Station selection multiselect

- [x] **Visualización de vectores**
  - 3D vector sum con componente Plotly 3D
  - 2D horizontal components
  - Rotación interactiva de componentes

#### Criterios de aceptación

```python
# Ejemplo de implementación Streamlit esperada
def display_waveforms(stream_data):
    st.header("🌊 Seismic Waveform Viewer")
    
    # Sidebar controls
    with st.sidebar:
        time_window = st.slider("Time Window (s)", 0, 3600, 300)
        amplitude_scale = st.selectbox("Amplitude Scale", ["Auto", "Global", "Individual"])
        selected_stations = st.multiselect("Select Stations", get_station_list(stream_data))
    
    # Main plot area
    if stream_data:
        fig = create_waveform_plot(stream_data, time_window, amplitude_scale)
        selected_points = plotly_events(fig, click_event=True)
        
        # Handle click events for phase picking
        if selected_points:
            add_phase_pick(selected_points[0])
            st.rerun()  # Refresh display
```

### 🔍 **MÓDULO 3: ANÁLISIS ESPECTRAL**

**Prioridad:** ALTA
**Archivos:** `pages/02_🔍_Spectrum_Analysis.py`, `src/visualization/spectrum_plots.py`

#### Funcionalidades específicas

- [x] **FFT interactivo en tiempo real**
  - Plotly subplot con waveform + spectrum
  - Slider para selección de ventana temporal
  - Selectbox para tipo de ventana (Hanning, Hamming, etc.)
  - Toggle buttons para escala log/linear

- [x] **Espectrogramas dinámicos**
  - Plotly heatmap interactivo con zoom
  - Slider para resolución temporal/frecuencial
  - Selectbox de colormaps (viridis, plasma, jet, etc.)
  - Botón de download para export PNG de alta resolución

- [x] **PSD con curvas Peterson**
  - Plotly line chart con NLNM/NHNM overlay
  - Checkbox para mostrar/ocultar curvas de referencia
  - Metrics display para estadísticas espectrales
  - Alertas automáticas si supera NHNM

- [x] **Filtrado interactivo visual**
  - Plotly selection tools para bandas de frecuencia
  - Sliders para freqmin/freqmax
  - Selectbox para tipo de filtro (Butterworth, etc.)
  - Preview en tiempo real con gráfico Before/After

- [x] **Controles de Streamlit específicos**
  - `st.columns()` para layout de controles
  - `st.form()` para parámetros de filtrado
  - `st.expander()` para opciones avanzadas
  - `st.progress()` para cálculos pesados

#### Criterios de aceptación

```python
# Ejemplo de implementación Streamlit
def spectral_analysis_page():
    st.header("🔍 Spectral Analysis")
    
    # Layout en columnas
    col1, col2, col3 = st.columns([2, 1, 1])
    
    with col1:
        # Main spectral plots
        fig_spec = create_spectrogram(selected_trace, **params)
        st.plotly_chart(fig_spec, use_container_width=True)
    
    with col2:
        # Filter controls
        with st.form("filter_params"):
            freqmin = st.number_input("Min Freq (Hz)", 0.1, 50.0, 1.0)
            freqmax = st.number_input("Max Freq (Hz)", 1.0, 100.0, 10.0)
            filter_type = st.selectbox("Filter Type", ["bandpass", "highpass", "lowpass"])
            apply_filter = st.form_submit_button("Apply Filter")
    
    with col3:
        # PSD metrics
        st.metric("Peak Frequency", f"{peak_freq:.2f} Hz")
        st.metric("Spectral Centroid", f"{centroid:.2f} Hz")
        st.metric("Bandwidth", f"{bandwidth:.2f} Hz")
```

### 🎯 **MÓDULO 4: PICKING DE FASES**

**Prioridad:** MEDIA
**Archivos:** `src/gui/picking_tools.py`

#### Funcionalidades específicas

- [x] **Picking manual interactivo**
  - Click para marcar arribos P y S
  - Ajuste fino con atajos de teclado
  - Uncertainty estimation visual

- [x] **Herramientas de validación**
  - Algoritmo STA/LTA para sugerencias
  - Highlight de picks inconsistentes
  - Sistema defer/include para fases

- [x] **Gestión de picks**
  - Export/import en formato estándar
  - Histórico de cambios (undo/redo)
  - Estadísticas de calidad automáticas

#### Criterios de aceptación

```python
picker = PhasePicker(stream)
p_pick = picker.add_pick('P', station='ABC', time=pick_time, uncertainty=0.1)
s_pick = picker.add_pick('S', station='ABC', time=pick_time, uncertainty=0.2)
picker.validate_picks()  # Retorna quality metrics
```

### 🌍 **MÓDULO 5: LOCALIZACIÓN DE SISMOS**

**Prioridad:** MEDIA
**Archivos:** `src/core/location_engine.py`

#### Funcionalidades específicas

- [x] **Algoritmo de localización 1D**
  - Modelo de velocidades por capas
  - Minimización por mínimos cuadrados
  - Estimación de incertidumbres

- [x] **Modelos de velocidad personalizables**
  - Carga desde archivos CSV/JSON
  - Modelos regionales preconfigurados
  - Editor gráfico de modelos

- [x] **Visualización de resultados**
  - Mapas con epicentros calculados
  - Elipses de error
  - Residuos de tiempo de viaje

#### Criterios de aceptación

```python
locator = EarthquakeLocator(velocity_model='iasp91')
location = locator.locate(picks_dict)
print(f"Lat: {location.latitude}, Lon: {location.longitude}")
print(f"Depth: {location.depth_km} ± {location.depth_uncertainty} km")
```

### 📏 **MÓDULO 6: CÁLCULO DE MAGNITUDES**

**Prioridad:** MEDIA  
**Archivos:** `src/core/magnitude_calc.py`

#### Funcionalidades específicas

- [x] **Múltiples escalas de magnitud**
  - Magnitud Local (ML) personalizable
  - Magnitud de duración (Md)
  - Magnitud de momento (Mw) básica

- [x] **Correcciones automáticas**
  - Corrección por distancia epicentral
  - Corrección por respuesta instrumental  
  - Corrección por atenuación regional

- [x] **Análisis de consistencia**
  - Detección de outliers automática
  - Estadísticas de magnitudes por estación
  - Promediado ponderado inteligente

### 📈 **MÓDULO 7: ANÁLISIS DE HISTOGRAMAS**

**Prioridad:** BAJA
**Archivos:** `pages/06_📊_Histogram_Analysis.py`, `src/core/histogram_analyzer.py`

#### Funcionalidades específicas

- [x] **Procesamiento de datos Gecko**
  - Lectura de archivos binarios de histogramas
  - Extracción temporal de valores máximos
  - Correlación con eventos sísmicos

- [x] **Visualización de tendencias**
  - Gráficos temporales de PGA/PGV/PGD
  - Detección de anomalías estadísticas
  - Export de series temporales

### 🤖 **MÓDULO 8: AGENTE IA DE INTERPRETACIÓN SÍSMICA**

**Prioridad:** ALTA  
**Archivos:** `pages/07_🤖_AI_Interpreter.py`, `src/ai_agent/seismic_interpreter.py`

#### **¿Qué es el Agente IA?**

Un agente inteligente construido con **Agno-AGI** que interpreta automáticamente los datos sísmicos cargados, busca contexto en internet sobre sismos cercanos al área geográfica, y genera informes dinámicos contextualizados.

#### Funcionalidades específicas

##### **🧠 Agente Principal de Interpretación**

- [x] **Análisis automático de datos sísmicos**
  - Interpretación inteligente de amplitudes, frecuencias y duración
  - Clasificación automática de tipo de evento (natural, explosión, ruido)
  - Estimación de calidad de datos y confiabilidad

- [x] **Generación de narrativa técnica**
  - Descripción en lenguaje natural de las características sísmicas
  - Explicación de patrones observados en las formas de onda
  - Contextualización científica automática

##### **🌐 Búsqueda Inteligente de Contexto**

- [x] **Búsqueda automática de sismos cercanos**
  - Búsqueda en bases de datos sísmicas globales (USGS, EMSC)
  - Identificación de eventos en radio configurable (10-500 km)
  - Correlación temporal con los datos analizados

- [x] **Análisis del contexto regional**  
  - Búsqueda de información geológica del área
  - Identificación de fallas activas cercanas
  - Historial sísmico regional

- [x] **Búsqueda de eventos relacionados**
  - Noticias recientes sobre actividad sísmica local
  - Reportes de institutos sismológicos regionales
  - Alertas y boletines oficiales

##### **📊 Visualización Integrada**

- [x] **Dashboard de interpretación IA**
  - Gráfico principal con anotaciones automáticas del agente
  - Panel lateral con interpretación en tiempo real
  - Métricas de confianza y calidad del análisis

- [x] **Mapa interactivo contextual**
  - Ubicación del sismógrafo/acelerógraf
  - Marcadores de sismos cercanos encontrados
  - Overlay de información geológica regional

##### **📄 Generación de Informes Dinámicos**

- [x] **Informe automático en Markdown**
  - Resumen ejecutivo generado por IA
  - Secciones técnicas detalladas
  - Conclusiones y recomendaciones

- [x] **Formato adaptativo**
  - Informes técnicos para sismólogos
  - Informes simplificados para ingenieros
  - Alertas rápidas para operadores

#### **Arquitectura del Agente con Agno-AGI (MÚLTIPLES PROVEEDORES):**

```python
# Ejemplo con múltiples proveedores de modelos
from agno.agent import Agent
from agno.models.openai import OpenAIChat
from agno.models.anthropic import Claude  
from agno.models.ollama import OllamaChat  # NUEVO: Modelos locales
from agno.models.openrouter import OpenRouterChat  # NUEVO: Agregador unificado
from src.ai_agent.tools.seismic_databases import USGSTools, EMSCTools
from src.ai_agent.tools.geographic_tools import GeographicAnalysisTools

# OPCIÓN 1: MODELO POR DEFECTO - DeepSeek V3.1:free (LA MEJOR OPCIÓN GRATUITA)
seismic_analyst_default = Agent(
    name="Advanced Seismic Data Analyst",
    role="Expert seismologist with hybrid reasoning capabilities",
    model=OpenRouterChat(id="deepseek/deepseek-chat-v3.1:free"),  # 671B params, GRATUITO
    tools=[SeismicAnalysisTools(), StatisticalAnalysisTools()],
    instructions=[
        "You are a professional seismologist with access to advanced reasoning capabilities.",
        "Use hybrid thinking mode: engage deep reasoning for complex seismic analysis automatically.",
        "Analyze seismic waveforms with scientific rigor and mathematical precision.",
        "Always provide confidence levels and uncertainty quantification.",
        "Identify P-waves, S-waves, and surface waves with step-by-step analysis.",
        "Use your 671B parameter capacity for comprehensive technical interpretations.",
        "Leverage your advanced tool-use capabilities for USGS/EMSC integration."
    ],
    markdown=True,
    show_tool_calls=True
)

# OPCIÓN 2: ALTERNATIVA - Kimi K2:free (Excelente para agentic workflows)
seismic_analyst_kimi = Agent(
    name="Agentic Seismic Analyst",
    role="Expert seismologist optimized for agentic workflows and tool use",
    model=OpenRouterChat(id="moonshotai/kimi-k2:free"),  # 1T params, 32B active, GRATUITO
    tools=[SeismicAnalysisTools(), StatisticalAnalysisTools()],
    instructions=[
        "You are an expert seismologist optimized for autonomous agentic analysis.",
        "Excellent tool-calling capabilities for automated USGS/EMSC searches.",
        "65.8% SWE-Bench performance - superior code generation for analysis scripts.",
        "Use your 1T parameter knowledge for comprehensive seismic interpretations.",
        "Strong in mathematical reasoning and technical analysis."
    ],
    markdown=True,
    show_tool_calls=True
)

# OPCIÓN 3: Fallback - DeepSeek R1 Distill (Menor pero confiable)
seismic_analyst_fallback = Agent(
    name="Reliable Seismic Analyst",
    role="Dependable seismologist for consistent analysis",
    model=OpenRouterChat(id="deepseek/deepseek-r1-distill-llama-70b:free"),  # 70B params
    tools=[SeismicAnalysisTools(), StatisticalAnalysisTools()],
    instructions=[
        "Analyze seismic waveforms with step-by-step reasoning",
        "Focus on reliable, consistent interpretations",
        "Provide detailed scientific analysis with confidence levels"
    ],
    markdown=True
)

# ESTRATEGIA RECOMENDADA: DeepSeek V3.1 por defecto con failover inteligente
def create_optimal_free_seismic_team():
    """Equipo 100% gratuito con los mejores modelos disponibles"""
    
    # Análisis principal: DeepSeek V3.1 (671B params, hybrid reasoning)
    primary_analyst = Agent(
        name="Primary Seismic Analyst",
        role="Advanced seismologist with hybrid reasoning",
        model=OpenRouterChat(id="deepseek/deepseek-chat-v3.1:free"),
        tools=[SeismicAnalysisTools(), StatisticalAnalysisTools()],
        instructions=[
            "Use hybrid reasoning: automatic thinking mode for complex analysis",
            "Leverage your 671B parameter capacity for comprehensive interpretations",
            "Provide step-by-step analysis with mathematical precision",
            "Always quantify uncertainties and confidence levels"
        ],
        markdown=True
    )
    
    # Búsquedas especializadas: Kimi K2 (excelente tool use)
    research_specialist = Agent(
        name="Research Specialist", 
        role="Expert in earthquake database research and tool use",
        model=OpenRouterChat(id="moonshotai/kimi-k2:free"),
        tools=[USGSTools(), EMSCTools(), DuckDuckGoTools()],
        instructions=[
            "Leverage advanced tool-calling capabilities for automated searches",
            "Excellent agentic workflows for USGS/EMSC database queries",
            "Systematic correlation of earthquake data with regional context",
            "Superior performance in structured data analysis and synthesis"
        ],
        markdown=True
    )
    
    # Generación de reportes: DeepSeek V3.1 (híbrido para reportes técnicos)
    report_generator = Agent(
        name="Technical Report Generator",
        role="Professional seismic report writer",
        model=OpenRouterChat(id="deepseek/deepseek-chat-v3.1:free"),
        instructions=[
            "Generate comprehensive professional seismic analysis reports",
            "Use hybrid reasoning for complex technical writing",
            "Include executive summaries, technical details, and conclusions",
            "Maintain scientific objectivity with proper source citations"
        ],
        markdown=True
    )
    
    # Coordinador principal
    return Agent(
        team=[primary_analyst, research_specialist, report_generator],
        model=OpenRouterChat(id="deepseek/deepseek-chat-v3.1:free"),
        instructions=[
            "Coordinate advanced seismic analysis using hybrid reasoning",
            "Leverage team expertise for comprehensive interpretations",
            "Generate actionable insights with quantified uncertainties"
        ],
        markdown=True
    )
```

#### **Herramientas Especializadas del Agente:**

##### **🔧 Herramientas de Bases de Datos Sísmicas**

```python
# src/ai_agent/tools/seismic_databases.py
class USGSTools(Tool):
    """Acceso a la API del USGS para búsqueda de sismos"""
    def search_earthquakes(self, lat: float, lon: float, radius_km: int, days: int):
        # Búsqueda en la base de datos USGS
        pass
    
    def get_earthquake_details(self, event_id: str):
        # Detalles específicos de un sismo
        pass

class EMSCTools(Tool):
    """Acceso al European-Mediterranean Seismological Centre"""
    def search_regional_earthquakes(self, region: str, magnitude_min: float):
        pass
```

##### **🗺️ Herramientas Geográficas**

```python
# src/ai_agent/tools/geographic_tools.py
class GeographicAnalysisTools(Tool):
    """Análisis geográfico y geológico del área"""
    def get_geological_context(self, lat: float, lon: float):
        # Información geológica regional
        pass
    
    def find_active_faults(self, lat: float, lon: float, radius_km: int):
        # Identificación de fallas activas cercanas
        pass
```

#### **Integración con Streamlit:**

```python
# Ejemplo de página de Streamlit para el agente IA
def ai_interpreter_page():
    st.header("🤖 AI Seismic Interpreter")
    
    if 'seismic_data' in st.session_state:
        col1, col2 = st.columns([2, 1])
        
        with col1:
            # Gráfico principal con anotaciones IA
            fig = create_annotated_waveform_plot(st.session_state.seismic_data)
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            # Panel de interpretación en tiempo real
            with st.container():
                st.subheader("🧠 AI Analysis")
                
                if st.button("🚀 Start AI Interpretation"):
                    with st.spinner("AI analyzing seismic data..."):
                        # Ejecutar el agente de interpretación
                        interpretation = seismic_interpreter_team.run(
                            f"Analyze this seismic data: {get_data_summary()}"
                        )
                        
                        # Mostrar resultados
                        st.markdown(interpretation.content)
                        
                        # Buscar sismos cercanos automáticamente
                        if has_location_data():
                            lat, lon = get_station_location()
                            nearby_quakes = earthquake_researcher.run(
                                f"Search for earthquakes within 100km of {lat}, {lon} in the last 30 days"
                            )
                            
                            st.subheader("🌍 Nearby Earthquakes")
                            st.markdown(nearby_quakes.content)
        
        # Sección de informe completo
        st.subheader("📄 Automated Report")
        if st.button("📝 Generate Full Report"):
            with st.spinner("Generating comprehensive report..."):
                full_report = report_generator.run(
                    "Generate a comprehensive seismic analysis report based on all available data and context"
                )
                
                # Mostrar informe
                st.markdown(full_report.content)
                
                # Opción de descarga
                st.download_button(
                    "⬇️ Download Report (Markdown)",
                    full_report.content,
                    file_name=f"seismic_report_{datetime.now().strftime('%Y%m%d_%H%M')}.md",
                    mime="text/markdown"
                )
```

#### **Configuración del Agente (OPENROUTER POR DEFECTO - GRATUITO):**

```yaml
# config/agno_config.yaml
seismic_interpreter:
  # CONFIGURACIÓN POR DEFECTO: DeepSeek-V3.1:free (MODELO SUPERIOR GRATUITO)
  default_model: 
    provider: "openrouter"
    id: "deepseek/deepseek-chat-v3.1:free"
    name: "DeepSeek V3.1 (Hybrid Reasoning)"
    cost_per_token: 0.0  # COMPLETAMENTE GRATUITO
    context_length: 131072  # 128K tokens
    total_parameters: "671B"
    active_parameters: "37B" 
    capabilities: ["hybrid_reasoning", "tool_use", "mathematics", "scientific_analysis", "code_generation"]
    
  # ¿Por qué DeepSeek V3.1 es SUPERIOR como modelo por defecto?
  model_justification: |
    DeepSeek-V3.1:free es la MEJOR opción por defecto porque:
    🚀 671B parámetros totales (37B activos) - 10x más capacidad que R1 Distill
    🧠 Hybrid reasoning automático - Thinking mode cuando se necesita análisis complejo
    ⚡ Performance = DeepSeek-R1 pero MÁS RÁPIDO - Mejor que o1-mini en muchos benchmarks
    🔧 Tool use avanzado - Optimizado para APIs USGS/EMSC y búsquedas automáticas
    📊 128K context window - Maneja datasets sísmicos extensos completos
    🆓 100% GRATUITO - Sin límites de tokens ni subscripciones
    🔬 Entrenamiento agosto 2025 - El modelo gratuito más avanzado disponible
    📈 Agentic capabilities - Superior para workflows automáticos complejos
  
  # Configuración de modelos por proveedor (ACTUALIZADA)
  models:
    # OPCIÓN 1: OpenRouter (RECOMENDADO - Gratuitos superiores)
    openrouter:
      enabled: true
      api_key: "${OPENROUTER_API_KEY}"
      models:
        # MODELO POR DEFECTO (SUPERIOR Y GRATUITO)
        primary: "deepseek/deepseek-chat-v3.1:free"          # $0.00 - 671B params, hybrid reasoning
        
        # Alternativas gratuitas excelentes
        alternative1: "moonshotai/kimi-k2:free"              # $0.00 - 1T params, agentic workflows  
        alternative2: "deepseek/deepseek-r1-distill-llama-70b:free"  # $0.00 - 70B params, reasoning
        
        # Opciones premium (solo si se necesita calidad absoluta)
        premium_analysis: "anthropic/claude-3.5-sonnet"     # $0.003-$0.015 
        premium_reports: "openai/gpt-4o"                    # $0.005-$0.015
        
        # Opciones económicas adicionales
        fast_search: "anthropic/claude-3-haiku"             # $0.00025-$0.00125
        coding: "deepseek/deepseek-coder:free"              # $0.00 - GRATUITO
      
      # Control de costos (solo para modelos premium si se usan)
      pricing_limits:
        session_limit: 0.5   # USD por sesión (muy bajo, priorizamos gratuitos)
        daily_limit: 2.0     # USD por día
        warning_at: 0.8      # Advertencia al 80%
    
    # OPCIÓN 2: Ollama (LOCAL - Privacidad total)
    ollama:
      enabled: true
      host: "http://localhost:11434"
      models:
        primary: "llama3.2"        # Local, buena calidad
        analysis: "mistral"        # Local, análisis técnico
        search: "gemma2:2b"       # Local, búsquedas rápidas
        coding: "codellama"       # Local, generación código
      
    # OPCIÓN 3: Modelos directos (FALLBACK EXTREMO)
    openai:
      enabled: true
      api_key: "${OPENAI_API_KEY}"
      models:
        fallback: "gpt-4o-mini"   # Solo como último recurso absoluto
  
  # Estrategia de selección automática (OPTIMIZADA PARA V3.1)
  model_selection:
    strategy: "advanced_free_first"  # Priorizar modelos gratuitos avanzados
    selection_order: [
      "deepseek/deepseek-chat-v3.1:free",                   # Primera opción (SUPERIOR)
      "moonshotai/kimi-k2:free",                            # Segunda opción (excelente agentic)
      "deepseek/deepseek-r1-distill-llama-70b:free",       # Tercera opción (confiable)
      "ollama/llama3.2",                                    # Cuarta (local)
      "anthropic/claude-3-haiku",                           # Quinta (económica)
      "openai/gpt-4o-mini"                                  # Última (fallback)
    ]
    auto_switch: true  # Cambiar automáticamente si un proveedor falla
  
  # Configuración específica por tarea (OPTIMIZADA PARA V3.1)
  task_models:
    waveform_analysis: 
      preferred: "deepseek/deepseek-chat-v3.1:free"  # GRATUITO, hybrid reasoning, 671B params
      reasoning_mode: "hybrid"  # Automático thinking cuando se necesita
      
    earthquake_search:
      preferred: "moonshotai/kimi-k2:free"  # GRATUITO, superior tool use, agentic workflows
      fallback: "deepseek/deepseek-chat-v3.1:free"
      
    report_generation:
      preferred: "deepseek/deepseek-chat-v3.1:free"  # GRATUITO, excelente escritura técnica
      fallback: "moonshotai/kimi-k2:free"                      
      
    code_generation:
      preferred: "moonshotai/kimi-k2:free"                     # GRATUITO, 65.8% SWE-Bench
      fallback: "deepseek/deepseek-coder:free"

  # Configuración de prompts optimizada para DeepSeek V3.1
  prompt_optimization:
    deepseek_v3_1:
      hybrid_reasoning: "The model will automatically engage thinking mode for complex analysis"
      confidence_request: "Please provide confidence levels (High/Medium/Low) for each conclusion."
      scientific_mode: "Use scientific terminology and cite relevant seismological principles."
      uncertainty_quantification: "Include uncertainty estimates for all numerical results."
      tool_use: "Leverage advanced tool-calling capabilities for automated searches and data correlation."

  search_parameters:
    default_radius_km: 100
    max_radius_km: 500
    default_time_window_days: 30
    max_time_window_days: 90
  
  confidence_thresholds:
    high_confidence: 0.8
    medium_confidence: 0.6
    low_confidence: 0.3
```

#### **Variables de Entorno Actualizadas:**

```bash
# .env file para múltiples proveedores AI
# OpenAI (opcional)
OPENAI_API_KEY=your_openai_api_key_here

# Anthropic (opcional)  
ANTHROPIC_API_KEY=your_claude_api_key_here

# OpenRouter (NUEVO - acceso unificado)
OPENROUTER_API_KEY=your_openrouter_api_key_here

# Ollama (NUEVO - configuración local)
OLLAMA_HOST=http://localhost:11434
OLLAMA_DEFAULT_MODEL=llama3.2

# APIs sísmicas
USGS_API_URL=https://earthquake.usgs.gov/fdsnws/event/1/
EMSC_API_URL=https://www.seismicportal.eu/fdsnws/event/1/

# Configuración general
AGNO_LOG_LEVEL=INFO
AI_MODEL_SELECTION=cost_optimized  # o "performance", "privacy"
```

#### Criterios de aceptación

```python
# El agente debe cumplir:
def test_seismic_agent():
    # 1. Análisis automático
    interpretation = seismic_interpreter_team.run(sample_seismic_data)
    assert "P-wave" in interpretation.content
    assert "magnitude" in interpretation.content.lower()
    
    # 2. Búsqueda contextual
    nearby_events = earthquake_researcher.run("latitude=40.7, longitude=-74.0")
    assert len(nearby_events) > 0
    assert "USGS" in interpretation.sources
    
    # 3. Informe estructurado
    report = report_generator.run(interpretation + nearby_events)
    assert "## Executive Summary" in report.content
    assert "## Technical Analysis" in report.content
    assert "## Conclusions" in report.content
```

### 📄 **MÓDULO 9: GENERACIÓN DE REPORTES**

**Prioridad:** BAJA
**Archivos:** `pages/08_📄_Reports.py`, `src/reports/pdf_generator.py`
**Prioridad:** BAJA
**Archivos:** `src/reports/pdf_generator.py`

#### Funcionalidades específicas

- [x] **Reportes PDF automáticos**
  - Template profesional configurable
  - Inclusión de gráficos de alta resolución
  - Metadatos y estadísticas automáticas

- [x] **Export de datos**
  - CSV para análisis externos
  - Excel con múltiples hojas
  - JSON para intercambio de datos

---

## 🚀 **FASES DE DESARROLLO**

### **FASE 1: CORE (2-3 semanas)**

1. ✅ Setup del proyecto y estructura base
2. ✅ Implementar lectura de MiniSEED (ObsPy)
3. ✅ Visualización básica de formas de onda
4. ✅ Controles de zoom y navegación básicos
5. ✅ Sistema de configuración y logging

### **FASE 2: ANÁLISIS (3-4 semanas)**

1. ✅ Análisis espectral con FFT
2. ✅ Herramientas de filtrado
3. ✅ Picking manual de fases
4. ✅ Cálculos básicos de magnitud
5. ✅ Sistema de validación de datos

### **FASE 3: AGENTE IA (2-3 semanas) - NUEVA**

1. ✅ Setup del framework Agno-AGI
2. ✅ Implementar agente de interpretación básica
3. ✅ Herramientas de búsqueda de sismos (USGS, EMSC)
4. ✅ Integración con herramientas de búsqueda web
5. ✅ Generación automática de informes básicos
6. ✅ Interfaz Streamlit para el agente IA

### **FASE 4: AVANZADO (2-3 semanas)**

1. ✅ Localización de sismos 1D
2. ✅ Lectores adicionales (SAC, SEG-2)
3. ✅ Análisis de histogramas Gecko
4. ✅ Herramientas de rotación de componentes
5. ✅ Export/import de resultados

### **FASE 5: POLISH (1-2 semanas)**

1. ✅ Optimización del agente IA y contextualización regional
2. ✅ Generación de reportes PDF con contenido IA
3. ✅ Optimización de rendimiento
4. ✅ Testing exhaustivo
5. ✅ Documentación de usuario
6. ✅ Configuración de deployment

---

## 💾 **REQUERIMIENTOS TÉCNICOS**

### Rendimiento

- **Tiempo de carga:** < 2 segundos para archivos de 100MB
- **Tiempo de respuesta:** < 500ms para zoom/pan
- **Memoria RAM:** < 4GB para datasets típicos
- **CPU:** Soporte para multiprocesamiento en análisis espectral

### Compatibilidad  

- **OS:** Windows 10+, macOS 10.15+, Ubuntu 18.04+
- **Python:** 3.9 - 3.12
- **Resolución:** 1920x1080 mínimo
- **RAM:** 8GB recomendado

### Calidad de código

- **Cobertura de tests:** > 80%
- **Documentación:** Docstrings en todas las funciones públicas
- **Type hints:** En toda la codebase
- **Linting score:** 9.0/10 (flake8)

---

## 🧪 **CASOS DE USO PRINCIPALES**

### Caso de Uso 1: Análisis Rápido de Sismo

```
COMO sismólogo 
QUIERO cargar un archivo MiniSEED en la aplicación web
PARA identificar rápidamente las fases P y S y calcular la magnitud

FLUJO STREAMLIT:
1. Arrastro archivo MiniSEED al file_uploader
2. La aplicación carga automáticamente y muestra las formas de onda  
3. Uso los sliders del sidebar para ajustar ventana temporal
4. Hago click en las ondas para marcar fases P y S
5. La magnitud se calcula automáticamente y se muestra en metrics
6. Descargo los resultados con el botón download

CRITERIOS DE ACEPTACIÓN:
- File upload drag-and-drop funcional
- Visualización automática post-carga
- Click events para picking responsive (< 100ms)
- Cálculo automático de magnitud en tiempo real
- Botón de download genera CSV inmediatamente
```

### Caso de Uso 2: Monitoreo de Vibraciones

```
COMO ingeniero de vibraciones
QUIERO analizar múltiples archivos de histograma Gecko simultáneamente
PARA generar reportes de cumplimiento normativo automatizados

FLUJO STREAMLIT:
1. Cargo múltiples archivos usando multifile uploader
2. Selecciono el rango temporal con date picker
3. Configuro límites normativos en number inputs del sidebar
4. La aplicación genera gráficos comparativos automáticamente
5. Veo alertas en tiempo real si se superan límites
6. Descargo reporte PDF profesional con un click

CRITERIOS DE ACEPTACIÓN:  
- Multiple file upload simultáneo (hasta 50 archivos)
- Date range picker funcional
- Gráficos se actualizan reactivamente
- Alertas visuales (st.error, st.warning) automáticas
- PDF download con template profesional
```

### Caso de Uso 4: Interpretación Inteligente con IA (NUEVO)

```
COMO sismólogo de turno en un centro de monitoreo
QUIERO que la IA interprete automáticamente los eventos sísmicos registrados
PARA tener análisis contextualizado y reportes automáticos 24/7

FLUJO STREAMLIT + AGNO:
1. Cargo datos sísmicos usando file_uploader
2. La aplicación detecta automáticamente la ubicación del sismógrafo
3. Hago click en "🤖 Start AI Analysis" 
4. El agente IA analiza las formas de onda automáticamente
5. Busca sismos cercanos en bases de datos USGS/EMSC
6. Muestra contexto geológico regional en tiempo real
7. Genera informe técnico completo con interpretación profesional
8. Descargo reporte en Markdown/PDF con un click

CRITERIOS DE ACEPTACIÓN:
- Análisis automático de calidad de datos (< 30 segundos)
- Búsqueda automática en radio de 100km (< 10 segundos)
- Identificación correcta de P/S waves con >90% precisión
- Contexto geológico regional automático
- Informe profesional generado en < 60 segundos
- Fuentes citadas correctamente en todas las búsquedas
- Nivel de confianza mostrado para cada interpretación
```

```
COMO estudiante de sismología
QUIERO una interfaz web intuitiva para aprender conceptos básicos
PARA entender la propagación de ondas sísmicas interactivamente

FLUJO STREAMLIT:
1. Accedo a la app desde cualquier navegador (sin instalación)
2. Uso datos de ejemplo disponibles con st.selectbox
3. Exploro controles interactivos con tooltips explicativos  
4. Veo animaciones de propagación de ondas en tiempo real
5. Experimento con filtros y veo efectos inmediatamente
6. Leo explicaciones en st.expander sections

CRITERIOS DE ACEPTACIÓN:
- Acceso web sin instalación requerida
- Datos de ejemplo precargados disponibles
- Tooltips y help text en todos los controles
- Animaciones fluidas con Plotly
- Secciones educativas expandibles con teoría
- UI completamente autoexplicativa
```

---

## ✅ **CRITERIOS DE ACEPTACIÓN GENERALES**

### Funcionalidad

- [ ] ✅ Lectura correcta de al menos 3 formatos sísmicos
- [ ] ✅ Visualización fluida de hasta 20 canales simultáneos  
- [ ] ✅ Picking interactivo con precisión de milisegundos
- [ ] ✅ Cálculo de magnitudes con error < 0.2 unidades
- [ ] ✅ Export de resultados en formatos estándar

### Funcionalidad del Agente IA (DEEPSEEK V3.1 SUPERIOR POR DEFECTO)

- [ ] ✅ DeepSeek-V3.1:free (671B params) configurado como modelo principal
- [ ] ✅ Hybrid reasoning automático - thinking mode cuando se requiere análisis complejo
- [ ] ✅ Interpretación automática con >95% precisión (superior a todos los competidores gratuitos)
- [ ] ✅ Búsqueda automática de sismos cercanos con structured tool calling avanzado
- [ ] ✅ Generación de informes contextualizados en <30 segundos (optimización V3.1)
- [ ] ✅ Identificación correcta de fases P/S con >98% precisión (671B parameter advantage)
- [ ] ✅ Reasoning transparente paso a paso visible para validación científica
- [ ] ✅ Tool use nativo optimizado para APIs USGS/EMSC con JSON estructurado
- [ ] ✅ Acceso a internet con web scraping inteligente y síntesis automática
- [ ] ✅ Citación correcta automática de todas las fuentes consultadas
- [ ] ✅ Sistema de confianza cuantificado con métricas de incertidumbre (0.0-1.0)
- [ ] ✅ Context window 128K tokens - datasets sísmicos completos sin truncamiento
- [ ] ✅ Code generation automático para scripts Python de análisis personalizado
- [ ] ✅ Costo de operación: $0.00 por sesión (modelo completamente gratuito)

### Modelos Alternativos Integrados (NUEVO)

- [ ] ✅ Kimi K2:free (1T params) disponible para agentic workflows especializados
- [ ] ✅ DeepSeek-R1-Distill-Llama-70B:free como fallback confiable (70B params)
- [ ] ✅ Failover automático inteligente entre modelos gratuitos (<5 segundos)
- [ ] ✅ Selección automática por tipo de tarea (análisis/búsqueda/código/reportes)
- [ ] ✅ Optimización dinámica basada en complejidad de la consulta

### Configuración OpenRouter (NUEVO)

- [ ] ✅ API key de OpenRouter funcional para acceso gratuito
- [ ] ✅ Conexión estable a deepseek/deepseek-r1-distill-llama-70b:free
- [ ] ✅ Failover automático a modelos alternativos (<10 segundos)
- [ ] ✅ Latencia < 1 segundo para primer token (TTFT)
- [ ] ✅ Velocidad sostenida > 100 tokens/segundo
- [ ] ✅ Rate limiting manejado correctamente (modelo gratuito)
- [ ] ✅ Error handling robusto para disconnections de API
- [ ] ✅ Logging de performance y métricas de uso

### Usabilidad

- [ ] ✅ Interfaz intuitiva sin manual para usuarios básicos
- [ ] ✅ Atajos de teclado para operaciones comunes
- [ ] ✅ Feedback visual inmediato en todas las acciones
- [ ] ✅ Sistema de undo/redo funcional
- [ ] ✅ Manejo de errores con mensajes claros

### Rendimiento

- [ ] ✅ Inicio de aplicación en < 5 segundos
- [ ] ✅ Carga de archivos de 100MB en < 10 segundos
- [ ] ✅ Visualización fluida a 30+ FPS
- [ ] ✅ Uso eficiente de memoria (< 2GB para datasets típicos)
- [ ] ✅ Sin memory leaks en sesiones de 8+ horas

### Robustez

- [ ] ✅ Manejo graceful de archivos corruptos
- [ ] ✅ Recovery automático de crashes
- [ ] ✅ Validación de entrada en todas las funciones
- [ ] ✅ Logging detallado para debugging
- [ ] ✅ Testing automatizado > 80% cobertura

---

## 📚 **RECURSOS Y REFERENCIAS**

### Documentación Técnica

- [ObsPy Documentation](https://docs.obspy.org/) - Librería principal
- [SAC File Format](https://ds.iris.edu/files/sac-manual/) - Especificación SAC
- [MiniSEED Format](https://www.fdsn.org/seed_manual/SEEDManual_V2.4.pdf) - Especificación SEED

### Algoritmos de Referencia

- Geiger, L. (1912) - Localización de sismos clásica
- Peterson, J. (1993) - Modelos de ruido NLNM/NHNM  
- Richter, C.F. (1935) - Escala de magnitud local

### Software de Referencia

- [Waves - Seismology Research Centre](https://www.src.com.au/downloads/waves/) - Software original
- [SAC - IRIS](https://ds.iris.edu/ds/nodes/dmc/software/downloads/sac/) - Análisis sísmico clásico
- [ObsPy Tutorial](https://tutorial.obspy.org/) - Ejemplos prácticos

---

## 🎯 **ENTREGABLES FINALES**

### Código Fuente

- [ ] ✅ Repositorio Git con historial completo
- [ ] ✅ Código documentado y testeado
- [ ] ✅ Scripts de instalación automatizada
- [ ] ✅ Configuración de CI/CD básica

### Documentación

- [ ] ✅ Manual de usuario (PDF + online)
- [ ] ✅ Documentación técnica (API docs)
- [ ] ✅ Tutorial de primeros pasos
- [ ] ✅ FAQ y troubleshooting guide

### Distribución

- [ ] ✅ Aplicación Streamlit deployada localmente
- [ ] ✅ Docker container con aplicación completa
- [ ] ✅ Deployment en Streamlit Cloud (opcional)
- [ ] ✅ Scripts de instalación automatizada
- [ ] ✅ URL compartible para colaboración

### Configuración Adicional Streamlit

- [ ] ✅ Configuración de tema personalizada
- [ ] ✅ Optimización para archivos grandes (>500MB)
- [ ] ✅ Cache strategies para performance
- [ ] ✅ Error handling robusto en file uploads
- [ ] ✅ Responsive design para diferentes pantallas

---

**NOTA IMPORTANTE:** Este documento debe ser actualizado conforme el desarrollo avance. Utilizar versionado semántico para los cambios (MAJOR.MINOR.PATCH).

**Contacto del Proyecto:** [Tu información de contacto]  
**Última actualización:** Septiembre 22, 2025

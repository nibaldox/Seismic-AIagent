# 📖 Documentación Técnica - Seismic AIagent

## 🔍 Índice

- [🏗️ Arquitectura del Sistema](#-arquitectura-del-sistema)
- [🤖 Sistema IA Multi-Agente](#-sistema-ia-multi-agente)
- [📊 APIs y Módulos Core](#-apis-y-módulos-core)
- [🎨 Interfaz de Usuario](#-interfaz-de-usuario)
- [🔧 Configuración Avanzada](#-configuración-avanzada)
- [🧪 Testing y QA](#-testing-y-qa)
- [📈 Monitoreo y Métricas](#-monitoreo-y-métricas)
- [🚀 Deployment](#-deployment)

---

## 🏗️ Arquitectura del Sistema

### 📋 Visión General

Seismic AIagent sigue una arquitectura modular basada en capas:

```
┌─────────────────────────────────────────────────┐
│                 UI Layer                        │
│              (Streamlit Pages)                  │
├─────────────────────────────────────────────────┤
│              Business Logic                     │
│         (Core Seismology + AI Agents)          │
├─────────────────────────────────────────────────┤
│               Data Layer                        │
│        (File I/O + Session State)              │
├─────────────────────────────────────────────────┤
│             External APIs                       │
│      (OpenRouter, OpenAI, USGS, etc.)          │
└─────────────────────────────────────────────────┘
```

### 🗂️ Estructura de Directorios Detallada

```
src/
├── ai_agent/                    # 🤖 Sistema IA
│   ├── seismic_interpreter.py   # Framework multi-agente principal
│   ├── artifacts.py             # Factbase y hallazgos
│   ├── earthquake_search.py     # Búsqueda en catálogos
│   ├── regional_analysis.py     # Análisis regional
│   ├── report_generator.py      # Generación de reportes
│   └── tools/                   # Herramientas especializadas
│       ├── geographic_tools.py  # Análisis geográfico
│       ├── seismic_databases.py # Acceso a USGS/EMSC
│       └── web_search_tools.py  # Búsqueda web
├── core/                        # ⚙️ Algoritmos sísmicos
│   ├── data_reader.py          # Lectura multi-formato
│   ├── signal_processing.py    # Filtros digitales
│   ├── picking.py              # Detección P/S (STA/LTA)
│   ├── magnitude.py            # ML-WA con respuesta
│   ├── kelunji_metadata.py     # Parser archivos .ss
│   └── location/               # Localización sísmica
│       └── one_d_location.py   # Localización 1D
├── streamlit_utils/            # 🖥️ Utilidades UI
│   ├── appearance.py           # Temas y estilos
│   ├── file_uploader.py        # Carga de archivos
│   ├── session_state.py        # Gestión estado
│   ├── sidebar_controls.py     # Controles laterales
│   └── plot_interactions.py    # Interactividad gráficos
├── utils/                      # 🔧 Utilidades generales
│   ├── config.py               # Configuración YAML
│   ├── logger.py               # Sistema logging
│   └── geo.py                  # Funciones geográficas
└── visualization/              # 📊 Gráficos y plots
    ├── waveform_plots.py       # Visualización ondas
    └── spectrum_plots.py       # Análisis espectral
```

---

## 🤖 Sistema IA Multi-Agente

### 🎯 Framework Agno v2

El sistema IA está basado en [Agno](https://docs.agno.com/) v2, que proporciona:

- **🤝 Coordinación multi-agente** con Teams
- **🔄 Streaming** en tiempo real
- **💾 Memoria compartida** entre agentes
- **🔌 Multi-proveedor** (OpenRouter, OpenAI, Anthropic, Ollama)

### 🧠 Agentes Especializados

#### 1. **Waveform Analysis Agent**
```python
# Localizado en: src/ai_agent/seismic_interpreter.py
def run_primary_analysis(agents, summary):
    """Análisis especializado de formas de onda sísmicas"""
    # Características:
    # - Detección fases P/S
    # - Evaluación calidad de señal
    # - Identificación fuentes sísmicas
    # - Recomendaciones operativas
```

#### 2. **Spectrum Analysis Agent**
```python
def run_spectrum_analysis(agents, trace_info, analysis_type, params):
    """Interpretación especializada de análisis espectral"""
    # Parámetros:
    # - trace_info: metadatos de la traza
    # - analysis_type: "Espectrograma", "FFT", "PSD"
    # - params: configuración específica del análisis
```

#### 3. **Histogram/Telemetry Agent**
```python
def run_histogram_analysis(agents, filename, meta, df_head, columns, time_range):
    """Análisis de series temporales y telemetría"""
    # Capacidades:
    # - Detección tendencias y anomalías
    # - Evaluación estado equipos
    # - Correlación variables operativas
```

### 🧩 Team Analysis

El **equipo coordinado** utiliza la clase `TeamSeismicAnalysis`:

```python
class TeamSeismicAnalysis:
    def __init__(self, agents):
        self.team = Team(
            name="Equipo de Analisis Sismico",
            members=team_members,
            respond_directly=False,           # Procesamiento coordinado
            delegate_task_to_all_members=False,  # Flujo secuencial
            determine_input_for_members=True     # Síntesis de entradas
        )
    
    def analyze(self, context):
        """Análisis coordinado multi-fuente"""
        # 1. Telemetría → detectar anomalías
        # 2. Formas de onda → caracterizar señales  
        # 3. Catálogo sísmico → contexto regional
        # 4. Localización → epicentro estimado
        # 5. QA crítico → validación cruzada
        # 6. Síntesis → reporte integrado
```

### 📝 Configuración IA: `config/agno_config.yaml`

```yaml
seismic_interpreter:
  default_model:
    provider: "openrouter"
    id: "deepseek/deepseek-chat-v3.1:free"
    
  model_selection:
    strategy: "advanced_free_first"
    selection_order:
      - "deepseek/deepseek-chat-v3.1:free"
      - "nvidia/nemotron-nano-9b-v2:free"
      - "ollama/llama3.2"
    auto_switch: true
    
  task_models:
    waveform_analysis:
      preferred: "deepseek/deepseek-chat-v3.1:free"
      reasoning_mode: "hybrid"
    spectrum_analysis:
      preferred: "deepseek/deepseek-chat-v3.1:free"
    histogram_analysis:
      preferred: "deepseek/deepseek-chat-v3.1:free"
```

---

## 📊 APIs y Módulos Core

### 🌊 Signal Processing (`src/core/signal_processing.py`)

```python
class SignalProcessor:
    """Procesamiento avanzado de señales sísmicas"""
    
    def apply_filter(self, trace, filter_type, **kwargs):
        """Aplicar filtros digitales"""
        # Tipos soportados:
        # - bandpass: pasa-banda
        # - lowpass: pasa-bajo  
        # - highpass: pasa-alto
        
    def remove_response(self, trace, response_file=None):
        """Corrección respuesta instrumental"""
        
    def detrend(self, trace, type='linear'):
        """Eliminación de tendencia"""
```

### 🎯 Picking (`src/core/picking.py`)

```python
def suggest_picks_sta_lta(trace, sta_len=0.5, lta_len=30.0, trigger_on=3.5, trigger_off=1.0):
    """Detección automática de llegadas P/S usando STA/LTA"""
    # Parámetros optimizados para:
    # - Eventos locales: sta_len=0.5, lta_len=30.0
    # - Eventos regionales: sta_len=1.0, lta_len=60.0  
    # - Eventos teleseismos: sta_len=2.0, lta_len=120.0
    
    return picks  # Lista de objetos Pick
```

### 🔢 Magnitude (`src/core/magnitude.py`)

#### Wood-Anderson con Respuesta Instrumental

```python
def estimate_local_magnitude_wa(trace, distance_km, depth_km=10.0):
    """Estimación ML-WA con respuesta instrumental real"""
    
    # Simulación sismómetro Wood-Anderson clásico
    wa_response = {
        'sensitivity': 2800,      # Amplificación
        'natural_period': 0.8,    # To (segundos)
        'damping': 0.7,           # h (factor amortiguamiento)
        'max_displacement': 100   # mm máximo
    }
    
    # Corrección por distancia (Richter 1958)
    # ML = log10(A) + log10(Δ) + 0.00301*Δ + 3.0
    
    return {
        'ml': magnitude,
        'amplitude_mm': max_amplitude,
        'snr': signal_to_noise,
        'quality': quality_grade,
        'warnings': warnings_list,
        'metadata': response_metadata
    }
```

### 🗺️ Localización 1D (`src/core/location/one_d_location.py`)

```python
def locate_event_1d(stations, observations, velocity_model, grid_params):
    """Localización por búsqueda en grilla 1D (superficie)"""
    
    # Entrada:
    # - stations: coordenadas geográficas estaciones
    # - observations: tiempos P/S observados
    # - velocity_model: {vp: 6.0, vs: 3.5} km/s
    # - grid_params: {x: (-50,50,2), y: (-50,50,2)} km
    
    # Proceso:
    # 1. Proyección geográfica local (pyproj)
    # 2. Búsqueda en grilla X-Y
    # 3. Cálculo residuales RMS
    # 4. Estimación de incertidumbre
    
    return {
        'latitude': lat_opt,
        'longitude': lon_opt, 
        'depth': 0.0,  # Superficie
        'origin_time': t0_opt,
        'rms_residual': rms,
        'uncertainty_km': unc_ellipse
    }
```

---

## 🎨 Interfaz de Usuario

### 📱 Streamlit Pages

#### 1. **📁 Uploader** (`pages/00_📁_Uploader.py`)
- Carga multi-formato con drag & drop
- Validación automática de archivos
- Persistencia en `st.session_state`
- Previsualización de metadatos

#### 2. **📊 Waveform Viewer** (`pages/01_📊_Waveform_Viewer.py`)
- Visualización interactiva con Plotly
- Panel de filtros y controles
- **🤖 Análisis IA integrado** (columna derecha)
- Cálculo magnitud ML-WA con advertencias

#### 3. **🔍 Spectrum Analysis** (`pages/02_🔍_Spectrum_Analysis.py`)
- **Layout horizontal optimizado** con controles compactos
- Tres tipos de análisis: Espectrograma, FFT, PSD  
- **🤖 Panel IA especializado** para interpretación frecuencias
- Configuración avanzada por tipo de análisis

#### 4. **📈 Histogramas Gecko** (`pages/03_📈_Histogramas_Gecko.py`)  
- **Modo serie temporal** simplificado (eliminado histograma)
- Tres paneles verticales con variables configurables
- Controles horizontales: remuestreo, agregación, suavizado
- **🤖 Análisis contextual** considerando parámetros visualización

#### 5. **🧩 Equipo IA** (`pages/08_🧩_Equipo_IA.py`)
- Análisis coordinado multi-agente
- Configuración contexto integral (telemetría + ondas + localización)
- Streaming en tiempo real con eventos intermedios
- Síntesis final con recomendaciones operativas

### 🎨 Themes y Styling (`assets/css/theme.css`)

```css
/* Variables principales */
:root {
    --primary-color: #1f77b4;
    --secondary-color: #ff7f0e;
    --success-color: #2ca02c;
    --warning-color: #d62728;
    --info-color: #17a2b8;
}

/* Layout compacto para análisis */
.horizontal-controls {
    display: flex;
    gap: 1rem;
    align-items: center;
    flex-wrap: wrap;
}

.analysis-panel {
    border: 1px solid var(--primary-color);
    border-radius: 8px;
    padding: 1rem;
    margin: 0.5rem 0;
}
```

---

## 🔧 Configuración Avanzada

### 🗂️ Archivo Principal: `config/agno_config.yaml`

```yaml
# Configuración multi-proveedor
models:
  openrouter:
    enabled: true
    api_key: "${OPENROUTER_API_KEY}"
    pricing_limits:
      session_limit: 0.5   # USD por sesión
      daily_limit: 2.0     # USD por día
      warning_at: 0.8      # Avisar al 80%
      latency_p95: 12.0    # Max latencia P95 (s)
      
  ollama:
    enabled: true
    host: "${OLLAMA_HOST}"
    models:
      primary: "llama3.2"
      analysis: "mistral"
      
# Cache y monitoreo
cache:
  enable_agent_cache: true
  max_entries: 12
  
monitoring:
  enabled: true  
  log_level: "info"
  emit_on:
    - agent_created
    - agent_cache_hit
    - agent_run
```

### 🌊 Configuración Streamlit: `config/streamlit_config.toml`

```toml
[global]
developmentMode = false

[server]
port = 8501
enableCORS = false
enableXsrfProtection = true
maxUploadSize = 200

[browser]
gatherUsageStats = false

[theme]
primaryColor = "#1f77b4"
backgroundColor = "#0e1117"
secondaryBackgroundColor = "#262730"
textColor = "#fafafa"
```

---

## 🧪 Testing y QA

### 📋 Estructura de Tests

```
tests/
├── conftest.py              # Configuración pytest
├── test_core.py             # Tests algoritmos sísmicos
├── test_ai_agent.py         # Tests sistema IA  
├── test_earthquake_search.py # Tests búsqueda catálogos
├── test_session_state.py    # Tests estado Streamlit
└── fixtures/                # Datos de prueba
    ├── sample_data.mseed
    ├── sample_metadata.ss
    └── config_test.yaml
```

### 🔬 Tests Unitarios

```python
# tests/test_core.py
import pytest
from src.core.magnitude import estimate_local_magnitude_wa
from src.core.picking import suggest_picks_sta_lta

class TestMagnitudeCalculation:
    def test_ml_wa_calculation(self):
        """Test cálculo ML-WA con respuesta instrumental"""
        trace = load_test_trace()
        result = estimate_local_magnitude_wa(trace, distance_km=50)
        
        assert result['ml'] > 0
        assert result['quality'] in ['A', 'B', 'C', 'D']
        assert len(result['warnings']) >= 0
        
    def test_wa_response_simulation(self):
        """Test simulación respuesta Wood-Anderson"""
        # Verificar parámetros clásicos
        assert WA_NATURAL_PERIOD == 0.8
        assert WA_DAMPING == 0.7
```

### 🤖 Tests Sistema IA  

```python
# tests/test_ai_agent.py
def test_agent_initialization():
    """Test carga correcta de agentes"""
    agents = load_agent_suite()
    assert 'waveform_analysis' in agents
    assert 'spectrum_analysis' in agents
    
def test_team_analysis_flow():
    """Test flujo equipo multi-agente"""
    context = build_test_context()
    result = run_team_analysis(agents, context=context)
    
    assert 'markdown' in result
    assert result.get('agent_count', 0) > 0
```

### 🚀 Tests de Integración

```python  
# tests/test_integration.py
def test_full_workflow():
    """Test flujo completo: carga → análisis → IA"""
    # 1. Cargar datos de prueba
    # 2. Procesar con filtros
    # 3. Ejecutar análisis IA
    # 4. Validar outputs
    pass
```

---

## 📈 Monitoreo y Métricas

### 📊 Métricas Automáticas

El sistema incluye monitoreo integrado de:

```python
# src/ai_agent/seismic_interpreter.py
def record_agent_time(duration: float):
    """Registro tiempo de respuesta agentes"""
    
def _monitor_event(event_type: str, **kwargs):
    """Monitor eventos del sistema"""
    events = [
        'agent_created',
        'agent_cache_hit', 
        'agent_run',
        'agent_run_failed',
        'team_analysis_complete'
    ]
```

### 📉 Dashboard de Métricas

Los logs incluyen métricas estructuradas:

```json
{
  "timestamp": "2025-09-29T10:30:00Z",
  "event": "agent_run",
  "task": "waveform_analysis", 
  "duration_ms": 1250,
  "model": "deepseek/deepseek-chat-v3.1:free",
  "provider": "openrouter",
  "cache_hit": false,
  "token_count": 245
}
```

---

## 🚀 Deployment

### 🐳 Docker Production

```dockerfile
FROM python:3.9-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
EXPOSE 8501

CMD ["streamlit", "run", "streamlit_app.py", "--server.address", "0.0.0.0"]
```

### ☁️ Cloud Deployment

#### Streamlit Community Cloud
1. Fork repositorio en GitHub
2. Conectar con Streamlit Cloud
3. Configurar secretos (API keys)
4. Deploy automático

#### Docker + Cloud Run  
```bash
# Build y deploy
docker build -t gcr.io/PROJECT/seismic-aiagent .
docker push gcr.io/PROJECT/seismic-aiagent

gcloud run deploy seismic-aiagent \
  --image gcr.io/PROJECT/seismic-aiagent \
  --platform managed \
  --allow-unauthenticated
```

### 🔐 Configuración Producción

```yaml
# config/production.yaml
environment: "production"
debug: false

security:
  api_rate_limit: 100  # requests/hour
  max_file_size: 50    # MB
  allowed_extensions: [".mseed", ".sac", ".seg2"]
  
monitoring:
  log_level: "warning"
  enable_metrics: true
  alert_on_errors: true
```

---

## 📞 Soporte y Documentación

### 📚 Documentación Adicional
- `docs/roadmap.md` - Roadmap del proyecto
- `docs/RDP.md` - Requerimientos y especificaciones
- `docs/bitacora/` - Logs de desarrollo y decisiones
- `docs/equipo-multiagente-plan.md` - Especificación sistema IA

### 🔧 Troubleshooting Común

#### ❌ Error: "No suitable agents found"
**Solución**: Verificar configuración en `config/agno_config.yaml` y variables de entorno.

#### ❌ Error: "Team analysis failed"  
**Solución**: Actualizar Agno a v2, remover parámetros obsoletos como `mode`.

#### ❌ Error: "object of type 'NoneType' has no len()"
**Solución**: Actualizar código con validaciones None implementadas.

### 🤝 Contribuir

Ver [README.md](../README.md) sección "Contribuir al Proyecto" para guidelines de desarrollo.

---

**📖 Documentación Técnica - Versión 2.0 (Septiembre 2025)**
<div align="center">

# 🌊 Seismic AIagent
Análisis sísmico interactivo con asistencia de IA (Streamlit)

[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)  
[![Streamlit](https://img.shields.io/badge/Streamlit-1.28+-red.svg)](https://streamlit.io/)

</div>

---

## 📋 Resumen

Seismic AIagent es una aplicación híbrida (escritorio/web) para análisis rápido de formas de onda sísmicas, espectros y telemetría. Combina procesamiento local (ObsPy/NumPy) con un intérprete de IA especializado que explica hallazgos y sugiere acciones.

**� Interfaz Streamlit:** Aplicación web completa todo-en-uno

Puntos clave:
- Visualización y procesamiento de ondas (filtros, picks STA/LTA, magnitud ML-WA)
- Análisis espectral (Espectrograma, FFT, PSD) con interpretación IA
- Series temporales de telemetría (Histogramas Gecko)
- Localización 1D simple por grilla
- Selector dinámico de modelos IA (DeepSeek, Moonshot, Grok, etc.)
- Intérprete IA unificado: página única "🤖 AI Interpreter" con modos Individual y Equipo (coordinado)

---

## ✨ Funcionalidades

- Ingesta multi‑formato: MiniSEED, SAC, SEG-2, exportes Gecko; lectura Kelunji `.ss`
- Visualización interactiva con Plotly y controles de filtrado
- Detección automática de fases P/S (STA/LTA)
- Magnitud local tipo Wood‑Anderson (aproximada) con avisos de calidad
- Análisis espectral avanzado y panel IA especializado
- Equipo IA coordinado (multi‑agente) para síntesis integral

---

## 🏗️ Estructura del proyecto

```text
.
├─ assets/
├─ config/
│  ├─ agents_config.yaml     # Configuración principal de agentes IA
│  ├─ agents_config_dynamic.yaml # Generado automáticamente por selector
│  └─ example.env            # Variables de entorno de ejemplo
├─ data/                     # Datos de ejemplo/pruebas
├─ docs/                     # Documentación
├─ pages/                    # Páginas Streamlit
│  ├─ 00_📁_Uploader.py
│  ├─ 01_📊_Waveform_Viewer.py
│  ├─ 02_🔍_Spectrum_Analysis.py
│  └─ 07_🤖_AI_Interpreter.py
├─ src/                      # Código fuente (core, ai_agent, utils, viz)
├─ streamlit_app.py          # App Streamlit principal
└─ tests/                    # Tests unitarios e integración
```

---

## ⚙️ Requisitos

- Windows con PowerShell (recomendado), Python 3.9+
- Dependencias listadas en `requirements.txt`

---

## 🚀 Instalación y ejecución

### 📋 Preparación inicial

```powershell
# 1) Clonar el repositorio
git clone https://github.com/nibaldox/Seismic-AIagent.git
cd Seismic-AIagent

# 2) Crear y activar entorno virtual Python
python -m venv venv
./venv/Scripts/Activate.ps1

# 3) Instalar dependencias Python
pip install -r requirements.txt

# 4) Variables de entorno (opcional)
copy config/example.env .env
# Edita .env con tus claves de OpenRouter/OpenAI
```

### � Ejecutar aplicación Streamlit

```powershell
# Ejecutar aplicación Streamlit
streamlit run streamlit_app.py --server.port 8501

# Abrir: http://localhost:8501
```

**Características:**
- Selector de modelos IA en página principal
- Uploader, Waveform Viewer, Spectrum Analysis, AI Interpreter
- Análisis coordinado multi-agente
- Interpretación IA integrada en todas las páginas

### 🐳 Docker (Opcional)

```powershell
# Construir imagen
docker build -t seismic-aiagent .

# Ejecutar contenedor
docker run --rm -p 8501:8501 --env-file config/example.env seismic-aiagent
```

---

## 🔌 API Endpoints (FastAPI)

Cuando uses la arquitectura React + FastAPI, estos son los endpoints disponibles:

### 📊 Procesamiento de señales
- `POST /waveform/plot` - Genera PNG de formas de onda con filtros
- `POST /spectrum/plot` - Crea espectrograma/FFT/PSD (retorna PNG + trace_info)
- `POST /telemetry/histogram` - Histograma desde CSV de telemetría
- `POST /location/one_d` - Localización 1D con estaciones XY y observaciones P/S

### 🤖 Interpretación IA
- `POST /ai/spectrum` - Análisis IA de parámetros espectrales + trace_info
- `POST /ai/waveform` - Interpretación IA del resumen de waveform
- `POST /ai/histogram` - Análisis IA de datos CSV de telemetría

### 🩺 Utilidades
- `GET /health` - Estado del servidor
- `GET /docs` - Documentación automática de Swagger

**Respuestas típicas:**
```json
{
  "image_base64": "iVBORw0KGgoAAAANSUhEUgAA...",
  "summary": "MiniSEED | 3 traces\nAC.STA1..BHZ | 2023-01-01T00:00:00.000000Z - 2023-01-01T00:10:00.000000Z | 100.0 Hz, 60001 samples",
  "trace_info": {
    "filename": "data.mseed",
    "station": "STA1",
    "channel": "BHZ",
    "sampling_rate": 100.0,
    "starttime": "2023-01-01T00:00:00.000000Z"
  }
}
```

---

## 🤖 Configuración de IA (Agno v2)

Archivo principal: `config/agents_config.yaml` (reemplaza al legado `agno_config.yaml`).

### 📋 Selector dinámico de modelos (Streamlit)

En la página principal de Streamlit encontrarás:

**🤖 Configuración de Modelo**
- DeepSeek Chat v3.1 (actual por defecto)
- Moonshot Kimi K2 (`moonshotai/kimi-k2:free`)
- xAI Grok 4 Fast (`x-ai/grok-4-fast:free`)
- Meituan LongCat Flash (`meituan/longcat-flash-chat`)
- Z-AI GLM 4.5 Air (`z-ai/glm-4.5-air:free`)
- Qwen3 235B (`qwen/qwen3-235b-a22b:free`, non-thinking)

**Cómo funciona:**
1. Selecciona modelo en dropdown de página principal
2. Se crea automáticamente `config/agents_config_dynamic.yaml`
3. La página "AI Interpreter" usará el modelo seleccionado
4. En React+FastAPI, el backend usará la configuración dinámica

Ejemplo básico de `agents_config.yaml`:

```yaml
agents:
  waveform_analyzer:
    model: openrouter:deepseek/deepseek-chat-v3.1:free
  spectrum_analyzer:
    model: openrouter:deepseek/deepseek-chat-v3.1:free
  histogram_analyzer:
    model: openrouter:deepseek/deepseek-chat-v3.1:free
  earthquake_correlator:
    model: openrouter:deepseek/deepseek-chat-v3.1:free
    capabilities: [earthquake_search, web_search]
  report_synthesizer:
    model: openrouter:deepseek/deepseek-chat-v3.1:free
  quality_assurance:
    model: openrouter:deepseek/deepseek-chat-v3.1:free

settings:
  cache: true
  monitoring: true
  show_tool_calls: false
```

### 🔑 Variables de entorno

Archivo `.env` (copia de `config/example.env`):

```bash
# OpenRouter (recomendado - soporta todos los modelos listados)
OPENROUTER_API_KEY=sk-or-v1-xxxxx

# Alternativos
OPENAI_API_KEY=sk-xxxxx
ANTHROPIC_API_KEY=sk-ant-xxxxx

# Backend FastAPI (opcional)
CORS_ORIGINS=http://localhost:5173,http://localhost:5174
UPLOAD_DIR=./uploaded_files
```

Notas:
- El **selector dinámico** funciona principalmente con OpenRouter
- En **Streamlit**: configuración en página principal + "AI Interpreter"
- En **React+FastAPI**: el backend lee la configuración automáticamente
- Si no tienes clave IA, las funciones básicas (plots, filtros) siguen funcionando

---

## � Pruebas

```powershell
# Ejecutar toda la suite
pytest -q
```

---

## 📚 Documentación

- Guía de Usuario: `docs/USER_GUIDE.md`
- Docs Técnicos: `docs/TECHNICAL_DOCS.md`
- Guía de Modificación de Agentes: `docs/AGENT_MODIFICATION_GUIDE.md`

---

## 🤝 Contribuir

1) Crea rama desde main (feature/fix/chore)  
2) Asegura tests en verde  
3) Abre Pull Request: https://github.com/nibaldox/Seismic-AIagent/pulls

---

## � Licencia

MIT (ver archivo LICENSE si corresponde).

---

Hecho con ❤️ para análisis sísmico asistido por IA.
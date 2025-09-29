<div align="center">

# 🌊 Seismic AIagent
Análisis sísmico interactivo con asistencia de IA (Streamlit)

[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)  
[![Streamlit](https://img.shields.io/badge/Streamlit-1.28+-red.svg)](https://streamlit.io/)

</div>

---

## � Resumen

Seismic AIagent es una aplicación híbrida (escritorio/web) para análisis rápido de formas de onda sísmicas, espectros y telemetría. Combina procesamiento local (ObsPy/NumPy) con un intérprete de IA especializado que explica hallazgos y sugiere acciones.

Puntos clave:
- Visualización y procesamiento de ondas (filtros, picks STA/LTA, magnitud ML-WA)
- Análisis espectral (Espectrograma, FFT, PSD)
- Series temporales de telemetría (Histogramas Gecko)
- Localización 1D simple por grilla
- Intérprete IA unificado: página única “🤖 AI Interpreter” con modos Individual y Equipo (coordinado)

---

## ✨ Funcionalidades

- Ingesta multi‑formato: MiniSEED, SAC, SEG-2, exportes Gecko; lectura Kelunji `.ss`
- Visualización interactiva con Plotly y controles de filtrado
- Detección automática de fases P/S (STA/LTA)
- Magnitud local tipo Wood‑Anderson (aproximada) con avisos de calidad
- Análisis espectral avanzado y panel IA especializado
- Equipo IA coordinado (multi‑agente) para síntesis integral

---

## �️ Estructura del proyecto

```text
.
├─ assets/
├─ config/
│  ├─ agents_config.yaml      # Configuración principal de agentes IA (nuevo)
│  └─ example.env             # Variables de entorno de ejemplo
├─ data/                      # Datos de ejemplo/pruebas
├─ docs/                      # Documentación
├─ pages/                     # Páginas Streamlit
├─ src/                       # Código fuente (core, ai_agent, utils, viz)
└─ tests/                     # Tests unitarios e integración
```

---

## ⚙️ Requisitos

- Windows con PowerShell (recomendado), Python 3.9+
- Dependencias listadas en `requirements.txt`

---

## 🚀 Instalación y ejecución (Windows PowerShell)

```powershell
# 1) Clonar el repositorio
git clone https://github.com/nibaldox/Seismic-AIagent.git
cd Seismic-AIagent

# 2) Crear y activar entorno virtual
python -m venv venv
./venv/Scripts/Activate.ps1

# 3) Instalar dependencias
pip install -r requirements.txt

# 4) Variables de entorno
# Copia y edita .env (opcional) para claves de IA
copy config/example.env .env

# 5) Ejecutar la aplicación
streamlit run streamlit_app.py
```

Opcional (Docker):

```powershell
# Construir
docker build -t seismic-aiagent .
# Ejecutar
docker run --rm -p 8501:8501 --env-file config/example.env seismic-aiagent
```

---

## 🤖 Configuración de IA (Agno v2)

Archivo principal: `config/agents_config.yaml` (reemplaza al legado `agno_config.yaml`).

Ejemplo mínimo:

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

Notas:
- El “Equipo IA” corre dentro de la página “🤖 AI Interpreter” (modo coordinado)
- Si haces análisis espectral, incluye `spectrum_analyzer` para habilitar `spectrum_analysis`
- Variables de entorno en `.env` (ver `config/example.env`)

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
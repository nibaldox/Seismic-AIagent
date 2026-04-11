<div align="center">

# 🌊 Seismic AIagent
Análisis sísmico interactivo con asistencia de IA — optimizado para Chile y zona de subducción andina

[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.28+-red.svg)](https://streamlit.io/)

</div>

---

## 📋 Resumen

Seismic AIagent es una aplicación Streamlit para análisis rápido de formas de onda sísmicas, espectros y telemetría. Combina algoritmos clásicos de sismología (ObsPy/NumPy) con un sistema multi-agente de IA que interpreta los datos y sugiere acciones operativas.

**Diseñado para Chile:** calibración ML regional, modelo de velocidades cortical andino (Vp=6.0 km/s), y agentes IA contextualizados en la sismotectónica de la zona de subducción Nazca/Sudamérica.

---

## ✨ Funcionalidades

### Procesamiento sísmico
- Ingesta multi-formato: MiniSEED, SAC, SEG-2, exportes Gecko, archivos Kelunji `.ss`
- Filtros digitales: bandpass, highpass, lowpass (ObsPy zerophase, Butterworth 4 polos)
- Detección automática de fases P/S con STA/LTA + prefiltro 2–15 Hz
  - Detección de fase S por Vp/Vs=1.73 en canal Z, o STA/LTA independiente en horizontales
  - Picks con campo `uncertainty_s` y `snr_db`
- Magnitud local Wood-Anderson (ML):
  - Simulación WA con PAZ reales (Uhrhammer & Collins 1990; polos ±4.44 rad/s, gain=2800)
  - Calibración regional configurable (activa: CSN Chile); Hutton-Boore California, Colombia, Brasil disponibles
  - Resultado con incertidumbre explícita (`ML ≈ X.X ± 1.0`)
  - Integración aceleración→desplazamiento con corrección de línea base por segmento
- Localización 1D por búsqueda en grilla (superficial, experimental)

### Análisis espectral
- Espectrograma (ventanas Hann/Hamming/Blackman, overlap configurable)
- FFT con normalización por RMS de ventana y anotación de frecuencia dominante
- PSD Welch con `detrend='linear'` por segmento, unidades `dB re counts²/Hz`, anotación de frecuencia dominante
- **H/V Espectral (HVSR)** — método Nakamura (1989): detecta automáticamente los tres componentes (E/N/Z), suavizado en octavas, frecuencia de resonancia f₀ anotada

### Visualización
- Formas de onda Plotly con downsampling min/max temporalmente monótono
- Anotaciones de PGA por canal (línea punteada + etiqueta en el pico)
- Picks P/S superpuestos con color diferenciado

### Sistema IA (Agno v2 + OpenRouter)
- 6 agentes especializados: Analizador de Formas de Onda, Espectral, Histogramas, Correlacionador Sísmico, Sintetizador de Reportes, Control de Calidad
- Contexto enriquecido a agentes: PGA, RMS, SNR, frecuencia dominante, centroide espectral, ancho de banda 80%, picks registrados
- Modo Individual (un agente) y Equipo coordinado (todos los agentes)
- Selector dinámico de modelo LLM en tiempo de ejecución
- Ventana de búsqueda sísmica adaptativa: **horas** para trazas <6 h, días para registros largos

---

## 🏗️ Estructura del proyecto

```text
.
├─ config/
│  ├─ agents_config.yaml       # Agentes IA + calibración regional ML
│  ├─ agents_config_dynamic.yaml  # Generado automáticamente por selector de modelo
│  └─ example.env              # Variables de entorno de ejemplo
├─ pages/
│  ├─ 00_📁_Uploader.py
│  ├─ 01_📊_Waveform_Viewer.py
│  ├─ 02_🔍_Spectrum_Analysis.py  # incluye HVSR
│  ├─ 04_🌍_Location_1D.py
│  └─ 07_🤖_AI_Interpreter.py
├─ src/
│  ├─ ai_agent/                # Orquestación Agno v2
│  ├─ core/                    # Algoritmos sismológicos
│  │  ├─ magnitude.py          # ML con PAZ Wood-Anderson + calibración regional
│  │  ├─ picking.py            # STA/LTA con prefiltro y detección S
│  │  └─ signal_processing.py  # Filtros ObsPy (highpass/lowpass nativos)
│  └─ visualization/
│     └─ spectrum_plots.py     # FFT, PSD, Espectrograma, HVSR
├─ streamlit_app.py
└─ tests/
```

---

## ⚙️ Requisitos

- Python 3.9+
- Dependencias en `requirements.txt` (ObsPy, Streamlit, Agno v2, Plotly, SciPy)

---

## 🚀 Instalación

```bash
git clone https://github.com/nibaldox/Seismic-AIagent.git
cd Seismic-AIagent

python -m venv venv
source venv/bin/activate          # Linux/Mac
# venv\Scripts\Activate.ps1      # Windows PowerShell

pip install -r requirements.txt

cp config/example.env .env        # Editar con clave OpenRouter
streamlit run streamlit_app.py
```

### Docker

```bash
docker build -t seismic-aiagent .
docker run --rm -p 8501:8501 --env-file .env seismic-aiagent
```

---

## 🤖 Configuración de IA

### Agentes disponibles

| Agente | Función |
|--------|---------|
| Analizador de Formas de Onda | Tipo de evento, calidad de señal, coherencia de picks |
| Analizador Espectral | Frecuencia dominante, clasificación espectral, recomendaciones de filtro |
| Analizador de Histogramas | Tendencias de telemetría, anomalías, estado del equipo |
| Correlacionador de Sismos | Búsqueda USGS/EMSC, correlación con sismicidad regional |
| Sintetizador de Reportes | Informe integrado con recomendaciones priorizadas |
| Control de Calidad | Auditoría de consistencia entre agentes |

### Selector dinámico de modelo

En la página principal selecciona el LLM (DeepSeek, Moonshot Kimi K2, Grok 4, GLM 4.5, Qwen3, etc.). El sistema genera `agents_config_dynamic.yaml` automáticamente y todos los agentes usan ese modelo.

### Variables de entorno

```bash
# .env
OPENROUTER_API_KEY=sk-or-v1-xxxxx   # Requerido para IA
OPENAI_API_KEY=sk-xxxxx              # Opcional
ANTHROPIC_API_KEY=sk-ant-xxxxx       # Opcional
```

---

## 📐 Calibración de magnitud regional

La calibración activa se configura en `config/agents_config.yaml`:

```yaml
magnitude_calibration:
  active_region: "csn_chile"   # ← cambiar aquí para otra región
```

| Región | Referencia | Aplicación |
|--------|-----------|-----------|
| `csn_chile` ✅ **activa** | CSN / Barrientos (1980) | Chile, zona de subducción andina |
| `hutton_boore_california` | Hutton & Boore (1987) | Sur de California |
| `langer_colombia` | Langer et al. (1987) | Colombia, Andes del Norte |
| `usp_brasil` | Assumpção et al. (2002) | Brasil, escudo estable |
| `richter_original` | Richter (1935) | Referencia histórica |

> **Chile:** Vp=6.0 km/s, Vs=3.46 km/s (Vp/Vs=1.73) para eventos corticales.
> Para eventos intraslab (50–300 km) usar Vp≈7.8 km/s en la página de Localización 1D.
> Verificar coeficientes con publicaciones actuales del [CSN](https://www.csn.uchile.cl) antes de reportes oficiales.

---

## 🧪 Pruebas

```bash
pytest -q                          # suite completa
pytest tests/test_core.py -v       # módulo específico
pytest tests/test_core.py::nombre_test -v  # test individual
```

---

## 📚 Documentación

| Archivo | Contenido |
|---------|-----------|
| `docs/USER_GUIDE.md` | Guía paso a paso para cada página |
| `docs/TECHNICAL_DOCS.md` | Arquitectura, APIs, despliegue |
| `docs/AGENT_MODIFICATION_GUIDE.md` | Cómo agregar/modificar agentes |
| `CLAUDE.md` | Guía para Claude Code (estructura y comandos) |

---

## 🤝 Contribuir

1. Crear rama desde `main` (`feature/`, `fix/`, `chore/`)
2. Asegurar tests en verde (`pytest -q`)
3. Abrir Pull Request

---

## 📄 Licencia

MIT

---

<div align="center">
Hecho para análisis sísmico operativo asistido por IA · Optimizado para la sismicidad de Chile
</div>

# Plan de implementación: Equipo multi‑agente para análisis sísmico e informe coherente

Este documento guía a desarrollar un equipo de agentes IA que colaboren y se cuestionen para producir un informe final consistente, en español, con trazabilidad de hallazgos y decisiones.

---

## 1) Objetivos y alcance

- Generar un informe final coherente que integre:
  - Análisis de histogramas/telemetría (Gecko) con marco temporal claro.
  - Análisis de formas de onda: picks P/S, filtros, amplitudes, magnitud local (WA aprox.).
  - Localización 1D y contexto de sismicidad reciente.
  - Revisión crítica (QA) para resolver contradicciones.
- Mantener trazabilidad: cada conclusión referencia su agente, datos y parámetros.

## 2) Arquitectura y topología

- Orquestador (Lead): coordina fases, enrutamiento y consolidación.
- Agentes especialistas:
  - Telemetry (Histogramas/Series): tendencias, cambios de régimen, outliers; TZ/marco temporal.
  - Waveform: picks, filtros, amplitudes, ML aprox.; riesgos de saturación/ruido.
  - Locator 1D: grid search superficie; incertidumbre; proyección local.
  - Earthquake Search: consulta catálogos; correlación temporal.
  - Magnitude: consolida estimaciones (WA y catálogo).
  - Critic/QA: detecta contradicciones y reclama evidencia.
  - Reporter: sintetiza informe final con confianza y referencias.
- Blackboard (factbase): repositorio compartido de “artefactos” (hallazgos, hipótesis, preguntas, decisiones).

## 3) Protocolo de comunicación

- Mensajes estructurados (Finding/Hypothesis/Question/Decision) con:
  - id, autor, timestamp ISO (con TZ), ventana temporal analizada.
  - variables y parámetros (resample, smoothing, bins, normalize, etc.).
  - summary breve, details, referencias a evidencia (columnas, figuras), confianza [0-1].
- Rondas: Descubrimiento → Preguntas/Réplicas → Decisiones → Reporte.
- Criterios de parada: sin contradicciones abiertas y confianza ≥ umbral.

## 4) Contratos (esquemas)

Ejemplo JSON (Finding):

```json
{
  "type": "finding",
  "author": "telemetry",
  "timestamp_iso": "2025-09-26T14:05:00-03:00",
  "time_window": "2025-09-25T00:00Z → 2025-09-26T06:00Z",
  "variables": ["3D peak", "Voltage", "Temperature"],
  "params": {"resample": "1H", "agg": "mean", "smooth": true, "win": 21},
  "summary": "Incremento de 3D peak correlacionado con caída de Voltage nocturna.",
  "details": "...",
  "evidence_refs": ["fig:ts_panel_1", "col:3D peak"],
  "confidence": 0.72
}
```

El factbase mantiene arrays: `facts`, `open_questions`, `contradictions`, `decisions`.

## 5) Fases de orquestación

1. Normalización de contexto
   - Extraer rango temporal, TZ y ajustes de visualización (ya disponibles en la página de Histogramas y Waveform).
2. Análisis por dominio
   - Telemetry → Waveform → Earthquake Search → Locator → Magnitude.
3. Crítica y reconciliación
   - QA marca conflictos (p. ej., origen mecánico vs sismo) y solicita aclaraciones.
4. Síntesis
   - Reporter compone informe: Resumen, Contexto temporal, Hallazgos por dominio, Evidencia, Conclusiones, Recomendaciones, Limitaciones, Confianza.

## 6) Cambios en configuración (YAML)

Archivo `config/agno_config.yaml` – añadir tareas:

```yaml
seismic_interpreter:
  task_models:
    telemetry_analysis:
      preferred: "deepseek/deepseek-chat-v3.1:free"
    waveform_analysis:
      preferred: "deepseek/deepseek-chat-v3.1:free"
    locator_analysis:
      preferred: "deepseek/deepseek-chat-v3.1:free"
    earthquake_search:
      preferred: "moonshotai/kimi-k2:free"
    magnitude_estimation:
      preferred: "moonshotai/kimi-k2:free"
    critic_qa:
      preferred: "deepseek/deepseek-chat-v3.1:free"
    reporter:
      preferred: "deepseek/deepseek-chat-v3.1:free"
```

> Nota: se pueden mapear algunos roles a los modelos ya existentes para minimizar cambios iniciales.

## 7) Archivos/código a crear o extender

- `src/ai_agent/artifacts.py`
  - Dataclasses/Pydantic: Finding, Factbase, helpers (add_finding, find_conflicts).
- `src/ai_agent/seismic_interpreter.py`
  - `run_team_analysis(context: TeamContext) -> str`
  - Reutilizar `load_agent_suite`, `run_histogram_analysis` y `run_primary_analysis` como subtareas.
- `pages/08_🧩_Equipo_IA.py`
  - UI para lanzar el flujo, ver outputs por agente, conflictos QA y vista previa del informe.
- (Opcional) `src/ai_agent/report_templates.py`
  - Plantillas Markdown/PDF.

## 8) TeamContext (entrada estándar)

- `time_range`: "YYYY-MM-DDTHH:mm:ssZ → ..."
- `timezone`: "UTC" | "Local (UTC-03)" | ...
- `telemetry`: columnas seleccionadas, stats, ajustes (resample/agg/smooth o bins/normalize/logy).
- `waveform`: picks, filtros, unidades, amplitudes, ML‑WA.
- `location`: estaciones, proyección, resultado y error.
- `catalog`: eventos correlacionados (fuente, distancia, magnitud).

## 9) Hitos de entrega (MVP → Pro)

- H1: Contratos + orquestador secuencial + página UI básica.
- H2: QA con reglas simples + Reporter v0 (Markdown).
- H3: Ajustes de prompts por agente + cacheo.
- H4: Exportación PDF + enlaces a figuras.
- H5: Debate iterativo (Delphi) + consenso simple.

## 10) QA y riesgos

- Guardrails: unidades, TZ y parámetros siempre declarados en prompts.
- Validación: checklist QA (contradicciones, claims sin evidencia, coherencia temporal).
- Riesgos: falta de claves API; prompts demasiado largos; costos si se usan modelos premium.
- Mitigación: usar modelos “free” por defecto; compresión de contexto (stats en vez de tablas completas).

## 11) Plan de integración incremental

1) Añadir tareas al YAML y `run_team_analysis()` que ensamble prompts con los campos de TeamContext.
2) Telemetry+Waveform+Reporter en una única pasada (sin debate) para validar contratos.
3) Agregar Critic/QA y una segunda pasada corta.
4) Incluir Locator y Earthquake Search con entradas mínimas.
5) Exportar informe y añadir anclajes a findings.

---

### Notas finales

- Mantener los prompts en español y pedir niveles de confianza.
- Persistir el factbase para reanalizar el mismo caso con nuevas configuraciones.
- Aprovechar los datos ya disponibles en la página de Histogramas (rango temporal, stats y ajustes) para alimentar al equipo.

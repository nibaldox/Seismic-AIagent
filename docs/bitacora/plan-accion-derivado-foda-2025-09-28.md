# 🗺️ Plan de Acción Derivado del FODA — SeismoAnalyzer Pro

Fecha: 28/09/2025  
Versión: v1.0  
Estado: Propuesto (MVP → Pro)  
Horizonte: 0–12 meses

---

## 1) Objetivo General

Acelerar la madurez de SeismoAnalyzer Pro para adopción en entornos operativos, fortaleciendo confiabilidad científica, experiencia de usuario y opciones de despliegue (local/cloud/edge), con IA multi‑agente eficiente y trazable.

---

## 2) Metas Específicas (OKRs)

- O1: Elevar confiabilidad científica (localización y magnitud) a nivel “publicable”.  
  - KR1: Implementar localización 3D con al menos 4 estaciones y validación sintética.  
  - KR2: Mejorar ML (Wood‑Anderson) con respuesta instrumental y calibración básica.  
  - KR3: Añadir validación cruzada con catálogo (USGS/EMSC) y reportar desviaciones.

- O2: Optimizar desempeño y UX para datasets medianos‑grandes.  
  - KR4: Reducir tiempos de carga/plot >30% con lazy loading y downsampling.  
  - KR5: Añadir indicadores de progreso y manejo de errores unificado en Streamlit.  
  - KR6: Aumentar FPS de interacción (Plotly) con subsampling y memoización.

- O3: Robustecer el framework IA y reducir dependencia de proveedores.  
  - KR7: Soporte “offline-first” con Ollama y modelos locales (llama3, mistral).  
  - KR8: Añadir política de conmutación inteligente costo/latencia por tarea.  
  - KR9: Aumentar cobertura de pruebas de prompts (golden tests) al 70%.

- O4: Preparar el producto para pilotos con clientes.  
  - KR10: Empaquetado con PyInstaller (Windows/Linux) y Docker hardening.  
  - KR11: Reportes PDF/Markdown con plantilla institucional y metadatos.  
  - KR12: Guías de despliegue y SLA básico (métricas de salud y logging).

---

## 3) Hoja de Ruta 30/60/90 días

- 0–30 días (MVP++):  
  1. Infraestructura de pruebas: aumentar cobertura en `src/core` y `src/ai_agent` (pytest + fixtures).  
  2. UX crítica: spinners, barras de progreso, toasts de error, health panel.  
  3. IA local: integrar perfiles Ollama listos en `agno_config.yaml` y fallback automático.  
  4. Performance: downsampling adaptativo en `waveform_plots.py` y memoización.  
  5. Reportes: `report_generator.py` con plantilla básica (PDF/Markdown).

- 31–60 días (Validación científica):  
  6. Localización 3D: módulo `src/core/location/three_d_location.py` (grid o inversión no lineal).  
  7. Magnitud WA mejorada: respuesta instrumental y notas metodológicas en UI.  
  8. Catálogo: correlación evento‑pick con ventanas temporales configurables.  
  9. Golden tests prompts: instantáneas en `tests/` para QA de agentes.  
  10. Paquete desktop: build PyInstaller y guía de uso offline.

- 61–90 días (Pilotos y hardening):  
  11. Telemetría avanzada: alertas por umbrales adaptativos y smoothing configurables.  
  12. Monitoreo: métricas (latencia IA, cache hits, errores) + panel en UI.  
  13. Seguridad: sanitización de entradas y validación CSV robusta.  
  14. Deploy: Docker con user no‑root, read‑only FS opcional, healthcheck reforzado.  
  15. Docs cliente: manual de operación, playbooks, SLA inicial.

---

## 4) Entregables y DRI (Responsables)

- Core científico: `src/core/location/*`, `src/core/magnitude.py` — DRI: Core Eng.  
- IA/Agentes: `src/ai_agent/*`, `config/agno_config.yaml` — DRI: AI Eng.  
- UI/UX: `pages/*`, `streamlit_app.py`, `src/streamlit_utils/*` — DRI: Front Eng.  
- DevOps: `Dockerfile`, empaquetado, health/metrics — DRI: DevOps.  
- QA/Pruebas: `tests/*`, cobertura y golden prompts — DRI: QA Lead.

---

## 5) KPIs Clave

- Tiempo de carga (50 MB MiniSEED): ≤ 4 s  
- Render interactivo (3 trazas, 60 s ventana): ≥ 25 FPS percibidos  
- Precisión localización 3D (sintético): error ≤ 5 km, RMS ≤ 0.5 s  
- Desviación ML (con catálogo): |ΔM| ≤ 0.5 para eventos locales  
- Latencia IA (histogram_analysis): P95 ≤ 8 s (OpenRouter) / ≤ 15 s (Ollama)  
- Cobertura pruebas: ≥ 70% en core y ≥ 60% en ai_agent  
- Crash‑free sessions: ≥ 99%

---

## 6) Plan de Riesgos y Mitigaciones

- Dependencia de APIs externas → Fallback a Ollama local + caché de resultados críticos.  
- Costos IA variables → Límites por sesión/día en `agno_config.yaml` + modelos “free” por defecto.  
- Calidad científica → Validación sintética + comparación catálogo (USGS/EMSC) automatizada.  
- Rendimiento en datasets grandes → Downsampling/memoización + streaming progresivo.  
- Seguridad de entradas → Sanitización CSV/JSON, validaciones de tipos y límites.  
- Equipo reducido → Priorizar roadmap 30/60/90 con entregables concretos y DRI claros.

---

## 7) Backlog Priorizado (Top 12)

1) Downsampling adaptativo en `create_waveform_plot()` + memoización.  
2) Spinners/toasts/unified error handler en UI.  
3) Reporte PDF/Markdown con `src/ai_agent/report_generator.py`.  
4) Golden tests para `histogram_analysis` y `waveform_analysis`.  
5) Perfil Ollama por defecto en `agno_config.yaml` con modelos locales.  
6) Módulo `three_d_location.py` (MVP grid).  
7) Respuesta instrumental en ML‑WA y advertencias en UI.  
8) Correlación catálogo‑picks con ventana configurable.  
9) PyInstaller build + README de uso offline.  
10) Métricas de IA (latencia, cache hits) + panel en UI.  
11) Docker hardening (no‑root, RO FS opcional, healthcheck robusto).  
12) Validación CSV (telemetría/localización) y sanitización.

---

## 8) Cambios Propuestos en el Repo (mínimos y seguros)

- `docs/`  
  - `bitacora/plan-accion-derivado-foda-2025-09-28.md` (este archivo)  
- `config/`  
  - Ajustar `agno_config.yaml`: límites de costo/latencia, perfiles Ollama y fallbacks.  
- `src/visualization/waveform_plots.py`  
  - Downsampling/memoización y control de FPS.  
- `src/ai_agent/report_generator.py`  
  - Plantillas y exportación PDF/MD.  
- `tests/`  
  - Golden tests para prompts y pruebas sintéticas de localización 3D.

---

## 9) Criterios de Aceptación (por fase)

- 30 días: KPIs de rendimiento cumplidos, reportes básicos, pruebas>50%.  
- 60 días: Localización 3D MVP validada y ML‑WA calibrado; golden tests activos.  
- 90 días: Piloto ejecutado con panel de métricas, empaquetado desktop y Docker endurecido.

---

## 10) Próximos Pasos Inmediatos (esta semana)

- [ ] Implementar toasts de error y barra de progreso en páginas clave.  
- [ ] Añadir downsampling simple (cada N‑ésimo punto) + benchmark.  
- [ ] Crear esqueletos: `three_d_location.py` y `report_generator.py`.  
- [ ] Agregar límites de costo/latencia en `agno_config.yaml`.  
- [ ] Escribir 5 pruebas nuevas en `tests/` (2 core, 2 ai_agent, 1 integración UI).

---

Autor: GitHub Copilot  
Última actualización: 28/09/2025

# ✅ To-Do (orden de ejecución) — SeismoAnalyzer Pro

Guía de control de tareas en secuencia. Usa las casillas para marcar progreso. Sin fechas, sin Gantt.

Convención: [ ] pendiente · [x] completado · [~] en curso

---

1. [ ] UX básica de estado
    - [x] Añadir toasts/notificaciones de error
    - [x] Barras de progreso/spinners en acciones largas
    - [x] Panel de salud simple (estado de claves, conectividad, dataset activo)
2. [x] Manejador de errores unificado
    - [x] Crear util general en `src/streamlit_utils/` para capturar y mostrar errores
    - [x] Aplicarlo en páginas: Uploader, Waveform, Histogramas, Equipo IA
3. [x] Downsampling adaptativo en waveforms
    - [x] Implementar en `src/visualization/waveform_plots.py` (subsampling por ventana)
    - [x] Mantener fidelidad en picos (min/max por bucket)
4. [x] Memoización/caché de datos de traza
    - [x] Caché en sesión para arrays recortados por ventana y filtros
    - [x] Invalidar al cambiar dataset/controles
5. [x] Benchmarks ligeros de render
    - [x] Script rápido en `tests/perf_waveform.py` para medir FPS/tiempos
    - [x] Documentar KPIs actuales vs objetivo
6. [x] Pruebas mínimas iniciales
    - [x] Añadir 5 tests: 2 en `src/core`, 2 en `src/ai_agent`, 1 integración UI (smoke)
    - [x] Integrar en `pytest -q` y actualizar `README.md` (sección Tests)
7. [x] Límites de costo/latencia IA
    - [x] Configurar en `config/agno_config.yaml` (session_limit, daily_limit, P95)
    - [x] Modelos "free" por defecto y fallbacks claros
8. [x] Perfiles locales (Ollama) — 2025-05-22
    - [x] Añadir perfiles por tarea (analysis/search/coding) en `src/ai_agent/ollama_utils.py`
    - [x] Comprobación de entorno (`check_ollama_available()`) y mensajes guiados
9. [x] Generador de reportes
    - [x] Crear `src/ai_agent/report_generator.py` (MD→PDF)
    - [x] Plantilla institucional (encabezado, secciones, metadatos)
    - [x] Botón de exportación en páginas relevantes
10. [x] Métricas de IA y panel
    - [x] Instrumentar tiempos/latencias (ya hay `record_agent_time`)
    - [x] Exponer en UI (página Equipo IA) un panel de métricas
11. [x] Validación y sanitización de CSV
    - [x] Utilidad en `src/utils/` (tipos, rangos, NaN, columnas requeridas)
    - [x] Usarla en inputs de telemetría y localización
12. [x] Golden tests para prompts IA
    - [x] Snapshots para `histogram_analysis` y `waveform_analysis`
    - [x] Asegurar estabilidad de respuestas clave
13. [x] Correlación catálogo ↔ picks
    - [x] Función en `src/ai_agent/earthquake_search.py` para matching temporal
    - [x] Parámetros de ventana configurables y resumen en Markdown
14. [x] ML‑WA con respuesta instrumental
    - [x] Incorporar respuesta del sensor en `src/core/magnitude.py`
    - [x] Advertencias/metadatos en UI (limitaciones y supuestos)
15. [x] Localización 3D (MVP) — 2025-05-22
    - [x] Extender `src/core/location/one_d_location.py` con z en Station y grid_z
    - [x] `_dist_3d()` con fórmula euclidiana 3D
    - [x] Integración en UI: `pages/05_🌍_Location_1D.py` y API (`src/server.py`)
16. [x] Validación sintética localización 3D — 2025-05-22
    - [x] Generar dataset sintético en `tests/test_three_d_location.py`
    - [x] Criterios: error ≤ 5 km, RMS ≤ 0.5 s, repeatability ≥ 80%
    - [x] Golden snapshots en `tests/golden_three_d_location.json`
17. [x] Empaquetado desktop — 2025-05-22
    - [x] `acelerografo.spec` (PyInstaller spec con todos los hidden imports)
    - [x] `scripts/build_desktop.sh` (build script multi-plataforma)
    - [x] `docs/OFFLINE.md` (guía de uso offline y troubleshooting)
    - [x] `.env.example` (template sin API keys)
18. [x] Endurecimiento Docker — 2025-05-22
    - [x] `Dockerfile` multi-stage (builder + runtime), USER appuser
    - [x] `docker-compose.yml` con `read_only`, `tmpfs`, `cap_drop: ALL`
    - [x] `.dockerignore` (excluye .git, tests/, docs/, __pycache__)
    - [x] `requirements/base.txt` y `requirements/dev.txt` separados
19. [x] Monitoreo y logging — 2025-05-22
    - [x] `src/utils/logger.py` con JSON structured logging + rotating file
    - [x] `docs/DIAGNOSTIC.md` (guía de diagnóstico, 12 failure modes)
    - [x] Middleware de trace ID listo para integrar en server.py
20. [x] Documentación para clientes — 2025-05-22
    - [x] `docs/CLIENT_MANUAL.md` (operación, playbooks, SLA, métricas)
    - [x] `docs/PILOT_CHECKLIST.md` (checklist de despliegue)
    - [x] Actualizado `docs/USER_GUIDE.md` con secciones faltantes (HVSR, RotD50, etc.)
21. [x] Dataset de demo y scripts — 2025-05-22
    - [x] `scripts/load_demo.sh` (carga AC-1-SUR hora 14)
    - [x] `scripts/validate_demo.sh` (verifica que demo carga correctamente)
    - [x] `data/demo/README.md` (documenta archivos y eventos esperados)
22. [x] Checklist de piloto — 2025-05-22
    - [x] `docs/PILOT_CHECKLIST.md` (pre-despliegue, funcionales, performance, salida)
    - [x] `scripts/validate_pilot.sh` (validaciones automatizadas PASS/FAIL)
23. [x] Actualización de Roadmap/Bitácora — 2025-05-22
    - [x] Todas las tareas 8-22 marcadas `[x]` con fecha
    - [x] `docs/bitacora/rollback-2025-05-22.md` (registro de decisiones)

---

## Archivos creados/modificados en este bloque

### Nuevos
- `src/ai_agent/ollama_utils.py` — salud Ollama, mapeo tarea→modelo
- `src/core/location/__init__.py` — exporta LocationResult + 3D helpers
- `tests/test_three_d_location.py` — tests sintéticos 3D
- `tests/golden_three_d_location.json` — snapshots esperados
- `tests/.env.test` — entorno de testing
- `acelerografo.spec` — spec PyInstaller
- `scripts/build_desktop.sh` — script de build
- `scripts/load_demo.sh` — carga demo
- `scripts/validate_demo.sh` — valida demo
- `scripts/validate_pilot.sh` — validaciones piloto
- `docs/OFFLINE.md` — guía offline
- `docs/DIAGNOSTIC.md` — guía de diagnóstico
- `docs/CLIENT_MANUAL.md` — manual de cliente
- `docs/PILOT_CHECKLIST.md` — checklist piloto
- `data/demo/README.md` — documentación demo
- `.dockerignore` — exclusiones Docker
- `.env.example` — template sin API keys
- `requirements/base.txt` — deps prod
- `requirements/dev.txt` — deps dev

### Modificados
- `src/core/location/one_d_location.py` — soporte 3D (z en Station, grid_z, `_dist_3d`)
- `src/utils/logger.py` — JSON structured logging + rotating file
- `src/server.py` — endpoint location con grid_z y coordenadas reales
- `Dockerfile` — multi-stage build + non-root user
- `docker-compose.yml` — read_only, tmpfs, cap_drop, security_opt
- `requirements.txt` — actualizado a base+dev

### Decisiones registradas en `docs/bitacora/rollback-2025-05-22.md`
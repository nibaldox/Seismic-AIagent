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
    - [x] Modelos “free” por defecto y fallbacks claros
8. [ ] Perfiles locales (Ollama)
   - [ ] Añadir perfiles por tarea (analysis/search/coding)
   - [ ] Comprobación de entorno y mensajes guiados si no está disponible
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
15. [ ] Localización 3D (MVP)
    - [ ] Crear `src/core/location/three_d_location.py` (grid o inversión simple)
    - [ ] Integración mínima en UI (página Location)
16. [ ] Validación sintética localización 3D
    - [ ] Generar dataset sintético y medir RMS/errores
    - [ ] Criterios de aceptación: error ≤ 5 km, RMS ≤ 0.5 s
17. [ ] Empaquetado desktop
    - [ ] PyInstaller spec (Windows/Linux)
    - [ ] README de uso offline y troubleshooting
18. [ ] Endurecimiento Docker
    - [ ] Usuario no‑root y FS de solo lectura opcional
    - [ ] Imagen más pequeña y healthcheck robusto
19. [ ] Monitoreo y logging
    - [ ] Logging estructurado (niveles, contexto)
    - [ ] Guía de diagnóstico de fallos comunes
20. [ ] Documentación para clientes
    - [ ] Manual de operación y playbooks de incidencias
    - [ ] SLA básico y métricas de salud
21. [ ] Dataset de demo y scripts
    - [ ] Curar dataset de ejemplo (waveforms + histogramas)
    - [ ] Script de carga reproducible
22. [ ] Checklist de piloto
    - [ ] Lista de verificación para despliegues en cliente
    - [ ] Validaciones previas y criterios de salida
23. [ ] Actualización de Roadmap/Bitácora
    - [ ] Registrar avances y decisiones
    - [ ] Revisión FODA trimestral y ajuste del plan

---

Sugerencia: Mantén esta lista como única fuente de verdad. Si un ítem requiere dividirse, crea subtareas inmediatamente debajo, conservando el orden de ejecución.

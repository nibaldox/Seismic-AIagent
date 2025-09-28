# Plan de implementación para modernización

Este documento detalla las actividades, responsables y entregables necesarios para materializar el plan estratégico descrito en la auditoría técnica. Se estructura en fases iterativas de dos semanas, con seguimiento semanal y métricas de finalización por historia.

## Fase 0 · Preparación (Semana 0)
- **Inventario de activos**: catalogar datasets, modelos y claves API existentes. Documentar responsables y restricciones de uso.
- **Configuración base**: habilitar entorno reproducible con `pyenv`/`poetry`, plantillas de `pre-commit` y un pipeline CI temporal que ejecute lint y pruebas existentes.
- **Definición de KPIs**: acordar métricas de éxito (tiempo de respuesta del backend, cobertura de pruebas, latencia de UI, satisfacción de usuarios piloto).
- **Plan de comunicaciones**: establecer cadencia de demos semanales, repositorio de decisiones (ADR) y canales de soporte entre frontend/back.
- **Entregables**: inventario aprobado, repositorio con tooling inicial, dashboard de KPIs en borrador.

## Fase 1 · Consolidación del dominio (Semanas 1-2)
- **Refactorización a servicios**:
  - Extraer lógica de negocio de páginas Streamlit hacia un paquete `src/services/`.
  - Crear contratos de entrada/salida con `pydantic` y documentarlos en docstrings.
- **Cobertura de pruebas**:
  - Diseñar casos sintéticos para estimaciones ML y validaciones de waveform.
  - Integrar `pytest-cov` y fijar un objetivo inicial del 70% de cobertura en servicios.
- **Entregables**: módulo `services`, informes de cobertura, manual de migración para desarrolladores.
- **Checklist de salida**:
  - [ ] Métricas de cobertura ≥ 70%.
  - [ ] Documentación de endpoints internos actualizada.
  - [ ] Taller de transferencia de conocimiento realizado.

## Fase 2 · API HTTP y seguridad (Semanas 3-4)
- **FastAPI**:
  - Montar aplicación en `src/api` con routers separados para ingestión, análisis, agentes y reporting.
  - Implementar esquemas OpenAPI con ejemplos y pruebas de contrato usando `schemathesis`.
- **Autenticación y control de acceso**:
  - Añadir autenticación Bearer con JWT, almacenamiento de claves en `pydantic-settings` y rotación programada.
  - Definir límites de tasa con `slowapi` y políticas para llamadas a modelos externos.
- **Entregables**: servidor FastAPI dockerizado, documentación interactiva, pruebas de contrato automatizadas.
- **Riesgos clave**:
  - Integración con servicios externos: mitigar con ambientes sandbox y mocks contractuales.
  - Cumplimiento de requisitos legales (datos sísmicos sensibles): coordinar con el área legal antes de exponer endpoints públicos.

## Fase 3 · Infraestructura y DevOps (Semanas 5-6)
- **Configuración unificada**:
  - Desacoplar dependencias en `requirements/{base,dev,prod}.txt` y soportar variables `.env` cifradas.
  - Instrumentar logging estructurado y métricas (Prometheus + Grafana).
- **CI/CD**:
  - Crear pipelines en GitHub Actions para lint, pruebas, build y publicación de imágenes.
  - Definir despliegue en Docker Compose y plantilla Helm para entornos gestionados.
- **Entregables**: archivos de requisitos segmentados, dashboards de monitoreo, pipelines activos.
- **Capacitación**: guías para que el equipo pueda reproducir despliegues locales y en staging; sesiones grabadas.

## Fase 4 · Frontend moderno (Semanas 7-10)
- **Bootstrapping**:
  - Seleccionar stack (Next.js + TypeScript recomendado) y configurar monorepo con `pnpm` o `turborepo`.
  - Integrar diseño base con Storybook y sistema de componentes accesible.
- **Integración con backend**:
  - Implementar clientes API tipados con `openapi-typescript`.
  - Desarrollar vistas para ingestión, visualización de waveforms, histogramas y agente IA con chat contextual.
- **Garantía de calidad**:
  - Añadir pruebas E2E con Playwright y pruebas de accesibilidad con `axe-core`.
- **Entregables**: repositorio frontend independiente, historias de usuario completas, suite E2E en CI.
- **Métricas UX**: implementar medición de Web Vitals (LCP, FID, CLS) y encuesta SUS para usuarios piloto.

## Fase 5 · Migración y soporte (Semanas 11-12)
- **Transición controlada**:
  - Ejecutar pruebas de regresión comparando respuestas Streamlit vs API.
  - Configurar feature flags para activar la nueva UI gradualmente.
- **Documentación y capacitación**:
  - Actualizar README, guías de despliegue y capacitación para soporte nivel 1.
  - Formalizar acuerdos de nivel de servicio (SLA) y plan de respuesta a incidentes.
- **Entregables**: reporte de regresión, manuales actualizados, aceptación de stakeholders.
- **Criterios de cierre**:
  - [ ] 100% de usuarios críticos migrados al frontend moderno.
  - [ ] Rotación de claves y auditoría de accesos completada.
  - [ ] Indicadores de soporte ≤ 3 tickets/semanales post-lanzamiento.

## Gobernanza continua
- Revisión quincenal de backlog y KPIs.
- Auditorías trimestrales de seguridad y privacidad.
- Roadmap de evolución del modelo IA alineado con feedback de usuarios.
- Comité técnico con representantes de backend, frontend, ciencia de datos y producto para priorizar mejoras cada trimestre.
- Evaluación anual de deuda técnica y presupuesto para infraestructura.

## Gestión de recursos
- **Equipo núcleo**: 2 desarrolladores backend Python, 2 desarrolladores frontend, 1 ingeniero DevOps, 1 científico de datos, 1 PM.
- **Especialistas**: asesor UX/UI (part-time), experto en seguridad (revisión Fase 2 y Fase 5), analista de datos para métricas.
- **Herramientas**: Notion para seguimiento de tareas, Linear/Jira para historias, Grafana/Prometheus, Sentry, SonarQube.

## Plan de riesgos
- **Disponibilidad de datos en tiempo real**: preparar datasets de respaldo y registrar incidentes con proveedores.
- **Sobrecarga del equipo**: activar rotación de guardias y límites de trabajo en paralelo; priorizar backlog por impacto.
- **Cambios regulatorios**: establecer monitoreo legal mensual y ajustar políticas de retención de datos.

## Métricas clave de éxito
- Latencia promedio de respuestas API < 500 ms en 95 percentil.
- Cobertura de pruebas backend ≥ 85% y frontend ≥ 70%.
- Web Vitals (LCP < 2.5 s, CLS < 0.1).
- Satisfacción de usuarios piloto ≥ 4/5 en encuestas trimestrales.
- Reducción del 40% en tickets de soporte relacionados con errores de interfaz.

## Calendario resumido
| Semana | Hito principal | Artefactos |
| ------ | -------------- | ---------- |
| 0 | Preparación completada | Inventario, KPIs, plan de comunicación |
| 1-2 | Servicios Python estabilizados | Paquete `services`, cobertura 70% |
| 3-4 | API segura operativa | FastAPI, JWT, pruebas contrato |
| 5-6 | Infraestructura automatizada | Pipelines CI/CD, monitoreo |
| 7-8 | Frontend base listo | Monorepo, Storybook, componentes clave |
| 9-10 | Frontend integrado | Vistas conectadas a API, E2E |
| 11-12 | Migración cerrada | Reporte regresión, documentación, SLA |


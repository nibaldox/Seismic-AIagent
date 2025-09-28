# Plan de implementación para modernización

Este documento detalla las actividades, responsables y entregables necesarios para materializar el plan estratégico descrito en la auditoría técnica. Se estructura en fases iterativas de dos semanas, con seguimiento semanal y métricas de finalización por historia.

## Fase 0 · Preparación (Semana 0)
- **Inventario de activos**: catalogar datasets, modelos y claves API existentes. Documentar responsables y restricciones de uso.
- **Configuración base**: habilitar entorno reproducible con `pyenv`/`poetry`, plantillas de `pre-commit` y un pipeline CI temporal que ejecute lint y pruebas existentes.
- **Definición de KPIs**: acordar métricas de éxito (tiempo de respuesta del backend, cobertura de pruebas, latencia de UI, satisfacción de usuarios piloto).

## Fase 1 · Consolidación del dominio (Semanas 1-2)
- **Refactorización a servicios**:
  - Extraer lógica de negocio de páginas Streamlit hacia un paquete `src/services/`.
  - Crear contratos de entrada/salida con `pydantic` y documentarlos en docstrings.
- **Cobertura de pruebas**:
  - Diseñar casos sintéticos para estimaciones ML y validaciones de waveform.
  - Integrar `pytest-cov` y fijar un objetivo inicial del 70% de cobertura en servicios.
- **Entregables**: módulo `services`, informes de cobertura, manual de migración para desarrolladores.

## Fase 2 · API HTTP y seguridad (Semanas 3-4)
- **FastAPI**:
  - Montar aplicación en `src/api` con routers separados para ingestión, análisis, agentes y reporting.
  - Implementar esquemas OpenAPI con ejemplos y pruebas de contrato usando `schemathesis`.
- **Autenticación y control de acceso**:
  - Añadir autenticación Bearer con JWT, almacenamiento de claves en `pydantic-settings` y rotación programada.
  - Definir límites de tasa con `slowapi` y políticas para llamadas a modelos externos.
- **Entregables**: servidor FastAPI dockerizado, documentación interactiva, pruebas de contrato automatizadas.

## Fase 3 · Infraestructura y DevOps (Semanas 5-6)
- **Configuración unificada**:
  - Desacoplar dependencias en `requirements/{base,dev,prod}.txt` y soportar variables `.env` cifradas.
  - Instrumentar logging estructurado y métricas (Prometheus + Grafana).
- **CI/CD**:
  - Crear pipelines en GitHub Actions para lint, pruebas, build y publicación de imágenes.
  - Definir despliegue en Docker Compose y plantilla Helm para entornos gestionados.
- **Entregables**: archivos de requisitos segmentados, dashboards de monitoreo, pipelines activos.

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

## Fase 5 · Migración y soporte (Semanas 11-12)
- **Transición controlada**:
  - Ejecutar pruebas de regresión comparando respuestas Streamlit vs API.
  - Configurar feature flags para activar la nueva UI gradualmente.
- **Documentación y capacitación**:
  - Actualizar README, guías de despliegue y capacitación para soporte nivel 1.
  - Formalizar acuerdos de nivel de servicio (SLA) y plan de respuesta a incidentes.
- **Entregables**: reporte de regresión, manuales actualizados, aceptación de stakeholders.

## Gobernanza continua
- Revisión quincenal de backlog y KPIs.
- Auditorías trimestrales de seguridad y privacidad.
- Roadmap de evolución del modelo IA alineado con feedback de usuarios.


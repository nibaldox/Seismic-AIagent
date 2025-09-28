# Auditoría técnica y plan de modernización

## Fortalezas principales
- **Cobertura funcional rica y documentada**: el README resume claramente capacidades clave (ingesta multi-formato, visualización interactiva, agentes IA) y la estructura de carpetas, facilitando la incorporación de nuevos contribuidores.
- **Núcleo modular y reutilizable**: componentes como `DataReader`, `MagnitudeResult` y los estimadores ML están aislados en `src/core`, con dataclasses y utilidades específicas que simplifican su reutilización en otros entornos.
- **Pruebas unitarias enfocadas**: existen pruebas para los módulos críticos (lectura de datos, metadatos Kelunji, utilidades ObsPy), lo que proporciona una base inicial para validar regresiones.
- **Utilidades compartidas maduras**: `src/utils/logger.py` y `src/streamlit_utils/**` centralizan manejo de estado, carga de archivos y componentes UI, reduciendo duplicaciones.

## Debilidades y riesgos
- **Acoplamiento UI-lógica**: las páginas Streamlit invocan directamente lógica de dominio y mutan el estado global, lo que complica la reutilización desde otro cliente.
- **Ausencia de API formal**: toda interacción ocurre dentro de Streamlit; no hay endpoints REST/GraphQL ni capa de servicios que expongan cálculos a clientes externos.
- **Dependencias mixtas sin aislamiento**: `requirements.txt` mezcla dependencias de producción y herramientas de desarrollo/packaging, dificultando builds mínimos.
- **Pruebas incompletas**: no se cubren flujos de AI Agent, histogramas ni localización; además, varias pruebas están condicionadas por la presencia de ObsPy, lo que puede ocultar fallos en CI.
- **Distribución y CI pendientes**: no hay pipelines declarados ni artefactos de despliegue; la licencia está marcada como “pendiente”.

## Plan propuesto: frontend web dedicado con backend Python

### 1. Consolidar la capa de dominio Python (Semana 1)
- Extraer servicios puros desde `src/core` y `src/ai_agent` en un paquete `src/services`, con funciones sin dependencias de Streamlit.
- Definir modelos de entrada/salida con `pydantic` para lecturas, picks, histogramas y resultados ML.
- Añadir pruebas adicionales que cubran los nuevos servicios y las rutas críticas (e.g. estimaciones ML con datasets sintéticos).

### 2. Diseñar API HTTP (Semana 2)
- Crear un backend `FastAPI` dentro de `src/api`, orquestando servicios para operaciones de carga, análisis, agentes IA y generación de reportes.
- Implementar autenticación básica (token/bearer) y límites de tasa para llamadas a modelos externos.
- Documentar la API con OpenAPI/Swagger y ejemplos de uso.

### 3. Configurar infraestructura compartida (Semana 3)
- Unificar configuración en `.env` gestionada por `pydantic-settings`, incluyendo llaves IA, rutas de datos y parámetros de telemetría.
- Desacoplar dependencias de desarrollo creando `requirements/base.txt`, `requirements/dev.txt` y `requirements/prod.txt`.
- Incorporar Docker multi-stage para backend + worker de IA, y definir pipelines CI (lint, pruebas, build de imagen).

### 4. Desarrollar frontend moderno (Semanas 4–6)
- Bootstrapping con Next.js + TypeScript o Vite + React, integrando componentes de gráficos (e.g. Plotly.js, ECharts).
- Consumir la API para carga de archivos (pre-signed URLs), renderizado de waveforms y dashboards de histogramas.
- Implementar vistas equivalentes a las páginas actuales (Uploader, Waveform Viewer, Histogramas, Location) y un panel dedicado al agente IA con chat contextual.
- Añadir internacionalización (es/en) y control de sesiones (JWT + refresh tokens) alineado con el backend.

### 5. Migración gradual y soporte (Semanas 7–8)
- Ejecutar pruebas de regresión comparando resultados del backend vía scripts automatizados.
- Mantener Streamlit como fallback durante la transición, con banderas para redirigir a la nueva UI.
- Documentar guías de despliegue (Docker Compose, Kubernetes) y actualizar README/licencia.


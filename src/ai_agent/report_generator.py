"""Generate AI-assisted Markdown reports."""

from __future__ import annotations

from datetime import datetime
from typing import Dict, Optional

from typing import TYPE_CHECKING, Any

from src.ai_agent.seismic_interpreter import AgentSpec, create_agent
from src.utils.logger import setup_logger

LOGGER = setup_logger(__name__)

if TYPE_CHECKING:  # pragma: no cover
    from agno.agent import Agent as AgnoAgent
else:
    AgnoAgent = Any  # type: ignore


def build_report_agent(default_provider: str, default_model: str) -> "AgnoAgent":
    spec = AgentSpec(
        provider=default_provider,
        model_id=default_model,
        role="Generador de Reportes Técnicos",
        instructions=(
            "Eres un redactor técnico especializado en informes de análisis sísmico.\n"
            "Tu tarea es crear informes profesionales en español neutro, manteniendo un tono claro y conciso.\n\n"
            "INSTRUCCIONES ESPECÍFICAS:\n"
            "1. Estructura el informe con secciones claras y encabezados apropiados\n"
            "2. Incluye estimaciones de confianza cuando sea posible\n"
            "3. Evita fragmentos en otros idiomas que no sean español\n"
            "4. Mantén consistencia técnica y profesionalismo\n\n"
            "FORMATO DE SALIDA:\n"
            "## Resumen Ejecutivo\n"
            "## Análisis Técnico\n"
            "## Conclusiones\n"
            "## Referencias\n\n"
            "Finaliza con una línea que indique el nivel de confianza global (Alta/Media/Baja)."
        ),
    )
    return create_agent(spec, show_tool_calls=False)


def generate_markdown_report(
    agent: "AgnoAgent",
    *,
    waveform_summary: str,
    ai_analysis: Optional[str],
    earthquake_context: Optional[str],
) -> str:
    """Generate a Markdown report by prompting the supplied agent."""

    timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    prompt = (
        "Genera un informe completo en formato Markdown escrito completamente en español neutro.\n"
        f"El reporte debe llevar fecha {timestamp} y usar la información entregada más abajo.\n"
        "Mantén párrafos cortos y preferentemente usa listas cuando mejoren la claridad.\n\n"
        f"## Datos de Análisis\n\n"
        f"### Resumen del Flujo de Forma de Onda\n{waveform_summary}\n\n"
        f"### Análisis del Agente IA\n{ai_analysis or 'No disponible.'}\n\n"
        f"### Contexto de Sismicidad Externa\n{earthquake_context or 'Sin eventos externos relevantes.'}\n\n"
        "## Estructura del Informe\n\n"
        "El informe debe incluir exactamente estos encabezados en este orden:\n"
        "- ## Resumen Ejecutivo\n"
        "- ## Análisis Técnico\n"
        "- ## Conclusiones\n"
        "- ## Referencias\n\n"
        "Cada sección debe ser concisa pero completa. Incluye niveles de confianza donde sea apropiado.\n"
        "Finaliza con una línea que indique el nivel de confianza global (Alta/Media/Baja)."
    )

    LOGGER.info("Generating Markdown report via agent %s", getattr(agent, "name", "unknown"))
    response = agent.run(prompt)
    return getattr(response, "content", "# Report\nReport content unavailable.")

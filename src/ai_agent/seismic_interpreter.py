"""Agno-AGI powered seismic interpretation orchestration."""

from __future__ import annotations

import importlib
import inspect
import time
from collections import OrderedDict
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Dict, Optional, List

from src.utils.config import load_yaml
from src.utils.logger import setup_logger
from .artifacts import Factbase, Finding
from .earthquake_search import EarthquakeSearcher, EarthquakeQuery
from .tools.geographic_tools import GeographicAnalysisTools
from .tools.seismic_databases import USGSTools
from .tools.web_search_tools import DuckDuckGoTools
from src.core.location.one_d_location import (
    locate_event_1d,
    Station as OneDStation,
    PSObservation as OneDPSObservation,
    OneDVelocityModel,
)

LOGGER = setup_logger(__name__)

try:  # pragma: no cover - optional dependency guard
    from agno.agent import Agent as _Agent
    from agno.team import Team
except ModuleNotFoundError:  # pragma: no cover
    _Agent = None  # type: ignore[assignment]
    Team = None  # type: ignore[assignment]

if TYPE_CHECKING:  # pragma: no cover
    from agno.agent import Agent as AgnoAgent
    from agno.team import Team as AgnoTeam
else:
    AgnoAgent = Any  # type: ignore
    AgnoTeam = Any  # type: ignore


@dataclass(frozen=True)
class AgentSpec:
    provider: str
    model_id: str
    role: str
    instructions: str


_AGENT_CACHE: "OrderedDict[AgentSpec, AgnoAgent]" = OrderedDict()
_CACHE_ENABLED: bool = True
_CACHE_MAX_ENTRIES: int = 12
_MONITORING_OPTIONS: Dict[str, Any] = {}

# Timing tracking for agent response times
_AGENT_TIMES: List[float] = []
_MAX_TIMES_STORED: int = 100


class TeamSeismicAnalysis:
    """Agno Team for comprehensive seismic data analysis using coordinate mode.

    This team orchestrates multiple specialized agents to perform coordinated analysis
    of seismic telemetry, waveforms, earthquake catalogs, and location data.
    """

    def __init__(self, agents: Dict[str, "AgnoAgent"]):
        """Initialize the seismic analysis team.

        Args:
            agents: Dictionary of specialized agents by role
        """
        if Team is None:  # pragma: no cover
            raise ImportError("Agno Team is not available. Install with `pip install agno[team]`.")

        # Validate agents dictionary
        if not agents:
            raise ValueError("Agents dictionary is empty")
        
        # Filter out None agents
        valid_agents = {k: v for k, v in agents.items() if v is not None}
        if not valid_agents:
            raise ValueError("No valid (non-None) agents found in dictionary")
        
        if len(valid_agents) != len(agents):
            invalid_keys = [k for k, v in agents.items() if v is None]
            LOGGER.warning("Filtered out None agents: %s", invalid_keys)

        # Define team member roles and their responsibilities
        team_members = []
        member_instructions = {}

        # Telemetry/Histogram Analysis Agent
        telemetry_agent = valid_agents.get("telemetry_analysis") or valid_agents.get("histogram_analysis")
        if telemetry_agent:
            team_members.append(telemetry_agent)
            member_instructions[telemetry_agent.name] = [
                "Analista de telemetria operativo",
                "Detecta patrones, anomalias y estado del equipo en datos de telemetria",
                "Proporciona interpretacion concisa con recomendaciones practicas",
                "Incluye nivel de confianza del analisis"
            ]

        # Waveform Analysis Agent
        waveform_agent = valid_agents.get("waveform_analysis")
        if waveform_agent:
            team_members.append(waveform_agent)
            member_instructions[waveform_agent.name] = [
                "Interprete de formas de onda operativo",
                "Identifica tipo de actividad sismica y calidad de senales",
                "Proporciona interpretacion directa sin jerga tecnica compleja",
                "Incluye recomendaciones practicas para personal operativo"
            ]

        # Earthquake Search Agent
        eq_agent = valid_agents.get("earthquake_search")
        if eq_agent:
            team_members.append(eq_agent)
            member_instructions[eq_agent.name] = [
                "Especialista en catalogos sismicos operativo",
                "Consulta bases de datos para contexto regional de eventos",
                "Identifica correlaciones entre detecciones locales y sismicidad regional",
                "Proporciona contexto sismico relevante para toma de decisiones"
            ]

        # Quality Assurance/Critic Agent
        critic_agent = valid_agents.get("critic_qa") or valid_agents.get("quality_assurance")
        if critic_agent:
            team_members.append(critic_agent)
            member_instructions[critic_agent.name] = [
                "Auditor de consistencia operativo",
                "Revisa analisis por contradicciones y datos faltantes",
                "Identifica aspectos que requieren clarificacion adicional",
                "Propone validaciones cruzadas entre diferentes analisis"
            ]

        # Report Generation Agent
        reporter_agent = valid_agents.get("reporter") or valid_agents.get("report_generation")
        if reporter_agent:
            team_members.append(reporter_agent)
            member_instructions[reporter_agent.name] = [
                "Sintetizador de informes operativos",
                "Integra hallazgos en reporte coherente y conciso",
                "Estructura informacion operativa con recomendaciones claras",
                "Proporciona conclusiones practicas basadas en evidencia"
            ]

        # Validate that we have at least one team member
        if not team_members:
            LOGGER.warning("No team members found in agent dictionary. Available agents: %s", list(valid_agents.keys()))
            # Use any available agent as a fallback
            fallback_agents = [valid_agents.get("waveform_analysis"), valid_agents.get("histogram_analysis")]
            fallback_agent = next((agent for agent in fallback_agents if agent), None)
            if fallback_agent:
                team_members.append(fallback_agent)
                member_instructions[fallback_agent.name] = [
                    "Analista general sismologico",
                    "Proporciona analisis operativo conciso y recomendaciones practicas"
                ]
            else:
                raise ValueError("No suitable agents found for team formation")

        self.team = Team(
            name="Equipo de Analisis Sismico",
            description="Equipo multi-agente especializado en analisis integral de datos sismicos",
            members=team_members,
            respond_directly=False,  # El líder procesa las respuestas de los miembros
            delegate_task_to_all_members=False,  # Delegación uno por uno para flujo estructurado
            determine_input_for_members=True,  # El líder sintetiza entradas específicas
            instructions=[
                "Coordina el analisis sismico siguiendo este flujo estructurado:",
                "1. Analisis de telemetria/histogramas para detectar anomalias",
                "2. Analisis de formas de onda para caracterizar senales",
                "3. Busqueda de sismicidad historica cercana",
                "4. Localizacion 1D si hay suficientes datos",
                "5. Revision critica QA de hallazgos",
                "6. Sintesis final del reporte",
                "",
                "Cada agente debe proporcionar analisis operativo conciso en espanol",
                "con nivel de confianza y recomendaciones practicas.",
                "Manten consistencia factual y evita contradicciones entre analisis."
            ] + [
                f"Agente {agent.name}: {member_instructions.get(agent.name, ['Sin instrucciones especificas'])[0]}"
                for agent in team_members
            ],
            expected_output="Informe completo en markdown con hallazgos operativos, explicaciones claras y recomendaciones practicas",
            markdown=True,
        )

    def analyze(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute coordinated seismic analysis with advanced streaming.

        Args:
            context: Analysis context with telemetry, waveform, location, and search data

        Returns:
            Dict with markdown report and analysis metadata
        """
        # Validate team initialization
        if not self.team:
            LOGGER.error("Team not initialized properly")
            return {
                "markdown": "Error: Equipo de análisis no inicializado",
                "error": "Team not initialized",
                "duration": 0,
                "team_mode": "error",
                "fallback_failed": True,
            }
        
        # Build comprehensive prompt from context
        prompt = self._build_analysis_prompt(context)
        
        if not prompt:
            LOGGER.error("Failed to build analysis prompt")
            return {
                "markdown": "Error: No se pudo construir el prompt de análisis",
                "error": "Empty prompt",
                "duration": 0,
                "team_mode": "error",
                "fallback_failed": True,
            }

        # Execute team analysis with advanced streaming
        start_time = time.time()

        # Use streaming with intermediate steps for real-time updates
        streaming_events = []
        final_result = None

        try:
            # Run with streaming to capture intermediate steps
            for event in self.team.run(prompt, stream=True):
                if event is not None:
                    streaming_events.append({
                        "timestamp": time.time(),
                        "event_type": getattr(event, "event_type", "unknown"),
                        "content": getattr(event, "content", str(event)),
                        "agent": getattr(event, "agent", None),
                        "step": getattr(event, "step", None),
                    })
                    LOGGER.debug(f"Team event: {event}")

            # Get final result
            final_result = self.team.run(prompt, stream=False)
            duration = time.time() - start_time

        except Exception as exc:
            duration = time.time() - start_time
            LOGGER.error(f"Team analysis failed: {exc}")
            # Fallback to non-streaming execution
            try:
                final_result = self.team.run(prompt, stream=False)
            except Exception as fallback_exc:
                LOGGER.error(f"Fallback team analysis also failed: {fallback_exc}")
                return {
                    "markdown": f"Error en analisis de equipo: {exc}",
                    "error": str(exc),
                    "duration": duration,
                    "team_mode": "coordinate",
                    "fallback_failed": True,
                }

        record_agent_time(duration)
        avg_time = get_average_response_time()
        LOGGER.info(f"Team analysis response time: {duration:.2f}s, Average: {avg_time:.2f}s" if avg_time else f"Team analysis response time: {duration:.2f}s")

        # Extract content and build response
        content = getattr(final_result, "content", str(final_result)) if final_result else "Error: No se recibió resultado del equipo"

        return {
            "markdown": content,
            "team_mode": "coordinate",
            "duration": duration,
            "agent_count": len(self.team.members) if self.team and hasattr(self.team, 'members') and self.team.members else 0,
            "streaming_events": len(streaming_events) if streaming_events else 0,
            "intermediate_steps": streaming_events or [],
        }

    def _build_analysis_prompt(self, context: Dict[str, Any]) -> str:
        """Build comprehensive analysis prompt from context data."""
        prompt_parts = [
            "Realiza un analisis integral de datos sismicos coordinado por el equipo:",
            "",
            "## Datos Disponibles:"
        ]

        # Telemetry data
        if context.get("telemetry"):
            tel = context["telemetry"]
            prompt_parts.extend([
                f"### Telemetria/Histogramas",
                f"- Archivo: {tel.get('filename', 'N/A')}",
                f"- Columnas: {', '.join(tel.get('columns', []))}",
                f"- Rango temporal: {context.get('time_range', 'N/A')}",
                f"- Notas: {tel.get('notes', 'Ninguna')}",
            ])
            if tel.get("df_head"):
                prompt_parts.append(f"- Vista previa:\n{tel['df_head']}")
            prompt_parts.append("")

        # Waveform data
        if context.get("waveform_summary"):
            prompt_parts.extend([
                f"### Formas de Onda",
                f"{context['waveform_summary']}",
                ""
            ])

        # Location data
        if context.get("location"):
            loc = context["location"]
            prompt_parts.extend([
                f"### Datos de Localizacion 1D",
                f"- Estaciones: {len(loc.get('stations', []))} con coordenadas geograficas",
                f"- Observaciones: {len(loc.get('observations', []))} tiempos P/S",
                f"- Modelo de velocidad: Vp={loc.get('model', {}).get('vp', 6.0)} km/s, Vs={loc.get('model', {}).get('vs', 3.5)} km/s",
                ""
            ])

        # Earthquake search parameters
        if context.get("eq_search"):
            eq = context["eq_search"]
            prompt_parts.extend([
                f"### Busqueda de Sismicidad",
                f"- Centro: {eq.get('latitude')}, {eq.get('longitude')}",
                f"- Radio: {eq.get('radius_km', 100)} km",
                f"- Periodo: {eq.get('days', 30)} dias",
                f"- Magnitud minima: {eq.get('min_magnitude', 2.5)}",
                ""
            ])

        prompt_parts.extend([
            "## Instrucciones de Analisis:",
            "1. **Analisis de Telemetria**: Detecta patrones y anomalias, estado del equipo",
            "2. **Analisis de Ondas**: Identifica tipo de actividad sismica y calidad de senales",
            "3. **Catalogo Sismico**: Busca contexto regional de eventos relevantes",
            "4. **Localizacion**: Estima epicentro si hay datos suficientes",
            "5. **Revision Critica**: Identifica contradicciones o validaciones necesarias",
            "6. **Sintesis Final**: Integra hallazgos en reporte coherente y conciso",
            "",
            "## Formato de Salida:",
            "- **Interpretacion operativa directa** sobre actividad detectada",
            "- **Estado de normalidad** y si requiere atencion",
            "- **Recomendaciones practicas** (2-3 acciones especificas)",
            "- **Nivel de confianza** del analisis integral",
            "",
            "Responde en espanol de forma concisa y practica para personal operativo."
        ])

        return "\n".join(prompt_parts)


def get_average_response_time() -> Optional[float]:
    """Get the average response time for agent runs."""
    if not _AGENT_TIMES:
        return None
    return sum(_AGENT_TIMES) / len(_AGENT_TIMES)


def record_agent_time(duration: float) -> None:
    """Record an agent response time and maintain the rolling window."""
    _AGENT_TIMES.append(duration)
    if len(_AGENT_TIMES) > _MAX_TIMES_STORED:
        _AGENT_TIMES.pop(0)


def create_agent(
    spec: AgentSpec,
    *,
    show_tool_calls: bool = True,
    enable_cache: Optional[bool] = None,
    expected_output: Optional[str] = None,
    tools: Optional[List[str]] = None,
) -> "AgnoAgent":
    """Instantiate an Agno agent based on the provider indicated."""

    if _Agent is None:  # pragma: no cover
        raise ImportError("Agno is not installed. Install with `pip install agno`.")

    cache_allowed = _CACHE_ENABLED if enable_cache is None else enable_cache
    if cache_allowed and spec in _AGENT_CACHE:
        LOGGER.debug("Reusing cached agent for task %s", spec.role)
        _monitor_event("agent_cache_hit", task=spec.role)
        _AGENT_CACHE.move_to_end(spec)
        return _AGENT_CACHE[spec]

    model = _resolve_model(provider=spec.provider, model_id=spec.model_id)
    
    # Use specific expected_output if provided, otherwise use default
    output_format = expected_output or "Provide technical analysis with confidence levels and plain-language explanations in Spanish"
    
    # Initialize tools list
    agent_tools = []
    if tools:
        for tool_name in tools:
            try:
                if tool_name == "usgs_search":
                    agent_tools.append(USGSTools(base_url="https://earthquake.usgs.gov/fdsnws/event/1/"))
                elif tool_name == "duckduckgo_search":
                    agent_tools.append(DuckDuckGoTools())
                elif tool_name == "geographic_context":
                    agent_tools.append(GeographicAnalysisTools(
                        context_endpoint="https://api.example.com/geology",  # Placeholder
                        faults_endpoint="https://api.example.com/faults"    # Placeholder
                    ))
                else:
                    LOGGER.warning(f"Unknown tool: {tool_name}")
            except Exception as exc:
                LOGGER.warning(f"Failed to initialize tool {tool_name}: {exc}")
    
    kwargs = {
        "name": spec.role,
        "model": model,
        "description": f"Agno agent specialized in {spec.role.lower()} for seismic data analysis",
        "instructions": [spec.instructions],
        "expected_output": output_format,
        "markdown": True,
        "debug_mode": False,  # Set to True during development for detailed logs
    }
    
    # Add tools if available
    if agent_tools:
        kwargs["tools"] = agent_tools
    
    if _supports_kwarg(_Agent, "show_tool_calls"):
        kwargs["show_tool_calls"] = show_tool_calls
    agent = _Agent(**kwargs)

    if cache_allowed:
        _AGENT_CACHE[spec] = agent
        _AGENT_CACHE.move_to_end(spec)
        while len(_AGENT_CACHE) > _CACHE_MAX_ENTRIES:
            evicted_spec, _ = _AGENT_CACHE.popitem(last=False)
            _monitor_event("agent_cache_evicted", task=evicted_spec.role)

    _monitor_event("agent_created", task=spec.role)
    return agent


def _configure_cache(options: Dict[str, Any]) -> None:
    global _CACHE_ENABLED, _CACHE_MAX_ENTRIES

    if options is None:
        options = {}

    _CACHE_ENABLED = bool(options.get("enable_agent_cache", True))
    max_entries = options.get("max_entries")
    if max_entries is not None:
        try:
            _CACHE_MAX_ENTRIES = max(1, int(max_entries))
        except (TypeError, ValueError):  # pragma: no cover - config validation
            LOGGER.warning("Invalid max_entries for agent cache: %s", max_entries)

    if not _CACHE_ENABLED:
        _AGENT_CACHE.clear()


def _configure_monitoring(options: Dict[str, Any]) -> None:
    global _MONITORING_OPTIONS

    _MONITORING_OPTIONS = options or {}


def _monitor_event(event: str, *, task: Optional[str] = None, extra: Optional[Dict[str, Any]] = None) -> None:
    if not _MONITORING_OPTIONS.get("enabled"):
        return

    payload = {"event": event}
    if task:
        payload["task"] = task
    if extra:
        payload.update(extra)

    level = str(_MONITORING_OPTIONS.get("log_level", "INFO")).lower()
    log_fn = getattr(LOGGER, level, LOGGER.info)
    structured = " | ".join(f"{key}={value}" for key, value in payload.items())
    log_fn("AGI monitor :: %s", structured)


def load_agent_suite(config_path: str = "agents_config.yaml") -> Dict[str, "AgnoAgent"]:
    """Load and instantiate the agent suite defined in YAML configuration."""

    try:
        agent_config = load_yaml(config_path)
        agent_seismic = agent_config.get("agents", {})
    except FileNotFoundError:
        # Fallback to old config file
        agent_config = load_yaml("agno_config.yaml")
        agent_seismic = agent_config.get("seismic_interpreter", {})

    # Load model configuration from agno_config.yaml
    try:
        model_config = load_yaml("agno_config.yaml")
        model_seismic = model_config.get("seismic_interpreter", {})
    except FileNotFoundError:
        model_seismic = agent_seismic  # fallback to agent config

    # Merge configurations: use agent config for task_models, model config for everything else
    seismic = {**model_seismic, **agent_seismic}

    _configure_cache(seismic.get("cache") or {})
    _configure_monitoring(seismic.get("monitoring") or {})
    task_models = seismic.get("task_models", {})

    agents: Dict[str, "AgnoAgent"] = {}
    failed_agents = []
    
    for task, data in task_models.items():
        provider, model_id = _resolve_task_model(seismic, data)
        default_instruction = f"Execute task: {task.replace('_', ' ')} for seismic interpretation."
        instructions = data.get("instructions", default_instruction)
        notes = data.get("notes")
        if notes and not instructions:
            # Fallback to notes if no specific instructions (for backward compatibility)
            instructions = f"{instructions}\n\nGuidance: {notes}"
        
        # Use expected_output from config if available, otherwise use default
        expected_output = data.get("expected_output", "Provide technical analysis with confidence levels and plain-language explanations in Spanish")
        
        # Get tools if specified
        tools = data.get("tools", [])
        
        spec = AgentSpec(provider=provider, model_id=model_id, role=task.title().replace("_", " "), instructions=instructions)
        try:
            agent = create_agent(spec, enable_cache=_CACHE_ENABLED, expected_output=expected_output, tools=tools)
            if agent is not None:
                agents[task] = agent
                _monitor_event("agent_registered", task=task)
            else:
                failed_agents.append((task, "Agent creation returned None"))
                LOGGER.warning("Agent creation returned None for task %s", task)
        except Exception as exc:  # pragma: no cover - surfacing config errors
            failed_agents.append((task, str(exc)))
            LOGGER.error("Failed to initialize agent for task %s: %s", task, exc)
            _monitor_event("agent_error", task=task, extra={"message": str(exc)})
    
    if not agents:
        LOGGER.error("No agents were successfully created. Failed agents: %s", failed_agents)
        raise ValueError(f"Failed to create any agents. Errors: {failed_agents}")
    elif failed_agents:
        LOGGER.warning("Some agents failed to initialize: %s. Available agents: %s", failed_agents, list(agents.keys()))
    
    return agents


def run_primary_analysis(agents: Dict[str, "AgnoAgent"], summary: str) -> Optional[str]:
    """Run the primary waveform analysis using the configured agent suite."""

    primary = agents.get("waveform_analysis")
    if primary is None:
        LOGGER.warning("Primary waveform analysis agent not configured.")
        return None

    prompt = (
        "Eres un sismologo experto especializado en interpretacion operativa de formas de onda sismicas.\n\n"
        "INSTRUCCIONES ESPECIFICAS:\n"
        "Proporciona una interpretacion clara y concisa para personal operativo sobre las formas de onda "
        "detectadas. Evita jerga tecnica compleja y enfocate en la interpretacion practica.\n\n"
        "Tu respuesta debe incluir:\n"
        "- Que tipo de actividad sismica se detecta (evento local, regional, teleseismo, ruido)\n"
        "- Si las senales son normales o requieren atencion inmediata\n"
        "- 2-3 recomendaciones practicas especificas\n"
        "- Nivel de confianza del analisis\n\n"
        "Responde en espanol de forma directa, sin titulos como 'Resumen Tecnico' o 'Explicacion para Personal No Tecnico'.\n\n"
        f"FORMAS DE ONDA DETECTADAS:\n{summary}\n\n"
        "INTERPRETACION:"
    )
    _monitor_event("agent_run", task="waveform_analysis")
    start_time = time.time()
    try:
        result = primary.run(prompt)
    except Exception as exc:  # pragma: no cover - agent execution error
        LOGGER.error("Waveform analysis agent failed: %s", exc)
        _monitor_event("agent_run_failed", task="waveform_analysis", extra={"message": str(exc)})
        return None
    
    duration = time.time() - start_time
    record_agent_time(duration)
    avg_time = get_average_response_time()
    
    LOGGER.info(f"Agent response time: {duration:.2f}s, Average: {avg_time:.2f}s" if avg_time else f"Agent response time: {duration:.2f}s")
    
    _monitor_event("agent_run_complete", task="waveform_analysis")
    return getattr(result, "content", None)


def run_histogram_analysis(
    agents: Dict[str, "AgnoAgent"],
    *,
    filename: Optional[str],
    meta: Dict[str, Any] | None,
    df_head: str,
    columns: list[str],
    time_range: Optional[str] = None,
    notes: Optional[str] = None,
) -> Optional[str]:
    """Run the histogram/time-series interpretation agent.

    df_head: string representation (markdown) of the head() or summary to keep prompts compact.
    columns: the columns visualized/selected by the user.
    time_range: optional human-readable time span.
    """
    agent = agents.get("histogram_analysis")
    if agent is None:
        LOGGER.warning("Histogram analysis agent not configured.")
        return None

    meta_lines = []
    if meta:
        for k, v in meta.items():
            meta_lines.append(f"- {k}: {v}")
    meta_block = "\n".join(meta_lines)

    cols_block = ", ".join(columns) if columns else "(no especificado)"
    
    prompt = (
        "Eres un analista sismologico especializado en interpretacion operativa de datos de telemetria sismica.\n\n"
        "INSTRUCCIONES ESPECIFICAS:\n"
        "Proporciona una interpretacion clara y concisa para personal operativo sobre los datos de telemetria. "
        "Evita jerga tecnica compleja y enfocate en la interpretacion practica de tendencias y anomalias.\n\n"
        "Tu respuesta debe incluir:\n"
        "- Que patron o tendencia muestran los datos sismicos\n"
        "- Si hay anomalias que requieren atencion\n"
        "- Estado del equipo y calidad de los datos\n"
        "- 2-3 recomendaciones practicas especificas\n"
        "- Nivel de confianza del analisis\n\n"
        "Responde en espanol de forma directa, sin titulos como 'Resumen Tecnico' o 'Explicacion para Personal No Tecnico'.\n\n"
        f"ARCHIVO: {filename or '(subido)'}\n"
        + (f"PERIODO: {time_range}\n" if time_range else "")
        + (f"METADATOS: {meta_block}\n\n" if meta_block else "")
        + f"VARIABLES ANALIZADAS: {cols_block}\n\n"
        + (f"CONFIGURACION: {notes}\n\n" if notes else "")
        + "DATOS NUMERICOS PARA ANALIZAR:\n"
        + df_head + "\n\n"
        + "INTERPRETACION:"
    )
    _monitor_event("agent_run", task="histogram_analysis")
    start_time = time.time()
    try:
        result = agent.run(prompt)
        end_time = time.time()
        record_agent_time(end_time - start_time)
        _monitor_event("agent_run_complete", task="histogram_analysis", extra={"duration": end_time - start_time})
        return result.content if hasattr(result, 'content') else str(result)
    except Exception as exc:  # pragma: no cover
        end_time = time.time()
        duration = end_time - start_time
        LOGGER.error("Histogram analysis agent failed after %.2fs: %s", duration, exc)
        _monitor_event("agent_run_failed", task="histogram_analysis", extra={"message": str(exc), "duration": duration})
        return None
    
    duration = time.time() - start_time
    record_agent_time(duration)
    avg_time = get_average_response_time()
    
    LOGGER.info(f"Histogram agent response time: {duration:.2f}s, Average: {avg_time:.2f}s" if avg_time else f"Histogram agent response time: {duration:.2f}s")
    
    _monitor_event("agent_run_complete", task="histogram_analysis")
    return getattr(result, "content", None)


def run_spectrum_analysis(
    agents: Dict[str, "AgnoAgent"],
    *,
    trace_info: Dict[str, Any],
    analysis_type: str,
    analysis_params: Dict[str, Any],
) -> Optional[str]:
    """Run spectral analysis interpretation using AI agent.
    
    Args:
        agents: Dictionary of configured AI agents
        trace_info: Information about the analyzed trace (station, channel, sampling rate, etc.)
        analysis_type: Type of spectral analysis ("Espectrograma", "FFT", "Densidad Espectral (PSD)")
        analysis_params: Parameters used for the analysis (nfft, overlap, frequency limits, etc.)
    """
    agent = agents.get("spectrum_analysis") or agents.get("waveform_analysis")
    if agent is None:
        LOGGER.warning("Spectrum analysis agent not configured.")
        return None

    # Build context about the trace and analysis
    trace_context = []
    for key, value in trace_info.items():
        trace_context.append(f"- {key}: {value}")
    trace_block = "\n".join(trace_context)
    
    # Build parameters context
    params_context = []
    for key, value in analysis_params.items():
        params_context.append(f"- {key}: {value}")
    params_block = "\n".join(params_context)
    
    prompt = (
        "Eres un sismologo especializado en analisis espectral de senales sismicas.\n\n"
        "INSTRUCCIONES ESPECIFICAS:\n"
        "Proporciona una explicacion clara y concisa para personal operativo sobre lo que muestra el "
        "analisis espectral. Evita jerga tecnica compleja y enfocate en la interpretacion practica.\n\n"
        "Tu respuesta debe incluir:\n"
        "- Que tipo de actividad sismica se detecta (evento local, regional, ruido, etc.)\n"
        "- Si la senal es normal o requiere atencion\n"
        "- 2-3 recomendaciones practicas especificas\n"
        "- Nivel de confianza del analisis\n\n"
        "Responde en espanol de forma directa, sin titulos como 'Explicacion para Personal No Tecnico'.\n\n"
        f"TIPO DE ANALISIS: {analysis_type}\n\n"
        f"INFORMACION DE LA TRAZA:\n{trace_block}\n\n"
        f"PARAMETROS DEL ANALISIS:\n{params_block}\n\n"
        "INTERPRETACION:"
    )

    _monitor_event("agent_run", task="spectrum_analysis")
    start_time = time.time()
    try:
        result = agent.run(prompt)
    except Exception as exc:  # pragma: no cover - agent execution error
        LOGGER.error("Spectrum analysis agent failed: %s", exc)
        _monitor_event("agent_run_failed", task="spectrum_analysis", extra={"message": str(exc)})
        return None
    
    duration = time.time() - start_time
    record_agent_time(duration)
    avg_time = get_average_response_time()
    
    LOGGER.info(f"Spectrum agent response time: {duration:.2f}s, Average: {avg_time:.2f}s" if avg_time else f"Spectrum agent response time: {duration:.2f}s")
    
    _monitor_event("agent_run_complete", task="spectrum_analysis")
    return getattr(result, "content", None)


def run_team_analysis(
    agents: Dict[str, "AgnoAgent"],
    *,
    context: Dict[str, Any],
) -> Dict[str, Any]:
    """Run coordinated seismic analysis using Agno Team framework.

    This function leverages Agno Teams for advanced multi-agent coordination,
    enabling parallel processing, streaming, memory, and sophisticated reasoning.

    context: TeamContext-like dict with keys: time_range, telemetry, waveform, location, catalog, timezone.
    """
    try:
        # Initialize the seismic analysis team
        team = TeamSeismicAnalysis(agents)

        # Execute coordinated analysis with advanced capabilities
        result = team.analyze(context)

        # Add factbase-style metadata for compatibility
        fb = Factbase()

        # Extract key findings from the team result for factbase
        if "telemetry" in context and context["telemetry"]:
            tel = context["telemetry"]
            fb.add_finding(
                Finding(
                    type="finding",
                    author="telemetry_team",
                    timestamp_iso=tel.get("analysis_ts", ""),
                    time_window=context.get("time_range"),
                    variables=tel.get("columns", []),
                    summary="Analisis de telemetria por equipo IA",
                    details="Integrado en analisis coordinado del equipo",
                )
            )

        if context.get("waveform_summary"):
            fb.add_finding(
                Finding(
                    type="finding",
                    author="waveform_team",
                    timestamp_iso=context.get("analysis_ts", ""),
                    time_window=context.get("time_range"),
                    summary="Analisis de formas de onda por equipo IA",
                    details="Integrado en analisis coordinado del equipo",
                )
            )

        if context.get("eq_search") and context["eq_search"].get("latitude"):
            fb.add_finding(
                Finding(
                    type="finding",
                    author="earthquake_team",
                    timestamp_iso=context.get("analysis_ts", ""),
                    time_window=context.get("time_range"),
                    summary="Busqueda de sismicidad historica por equipo IA",
                    details="Integrado en analisis coordinado del equipo",
                )
            )

        # Return enhanced result with factbase metadata
        return {
            **result,
            "facts": fb.to_dict(),
            "team_capabilities": [
                "coordinate_mode",
                "streaming_events",
                "shared_memory",
                "agentic_context",
                "parallel_processing"
            ]
        }

    except Exception as exc:
        LOGGER.error(f"Team analysis failed, falling back to sequential mode: {exc}")

        # Fallback to original sequential implementation
        return _run_sequential_team_analysis(agents, context)


def _run_sequential_team_analysis(
    agents: Dict[str, "AgnoAgent"],
    context: Dict[str, Any],
) -> Dict[str, Any]:
    """Fallback sequential orchestration when Team framework is unavailable."""
    fb = Factbase()

    # 1) Telemetry (si hay)
    telemetry = context.get("telemetry")
    if telemetry:
        cols = telemetry.get("columns", [])
        notes = telemetry.get("notes")
        df_head = telemetry.get("df_head", "")
        meta = telemetry.get("meta", {})
        filename = telemetry.get("filename")
        time_range = context.get("time_range")
        try:
            # Si hay un agente dedicado para telemetry, usalo; de lo contrario, reutiliza histogram_analysis
            telemetry_agent = agents.get("telemetry_analysis") or agents.get("histogram_analysis")
            if telemetry_agent is not None:
                prompt = (
                    "Eres el analista de telemetria/histogramas.\n"
                    "Entrega en espanol: (1) resumen tecnico con tendencias, anomalias, correlaciones e hipotesis; (2) explicacion sencilla y 2-3 acciones practicas para personal no tecnico.\n"
                    f"Rango: {time_range or '-'} | Columnas: {', '.join(cols)}\n"
                    + (f"Notas: {notes}\n" if notes else "")
                    + ("Vista previa (parcial):\n" + df_head if df_head else "")
                )
                start_time = time.time()
                result = telemetry_agent.run(prompt)
                duration = time.time() - start_time
                record_agent_time(duration)
                avg_time = get_average_response_time()
                LOGGER.info(f"Telemetry agent response time: {duration:.2f}s, Average: {avg_time:.2f}s" if avg_time else f"Telemetry agent response time: {duration:.2f}s")
                content = getattr(result, "content", None)
            else:
                content = run_histogram_analysis(
                    agents,
                    filename=filename,
                    meta=meta,
                    df_head=df_head,
                    columns=cols,
                    time_range=time_range,
                    notes=notes,
                )
        except Exception as exc:
            LOGGER.warning("telemetry agent failed: %s", exc)
            content = None
        if content:
            fb.add_finding(
                Finding(
                    type="finding",
                    author="telemetry",
                    timestamp_iso=telemetry.get("analysis_ts", ""),
                    time_window=time_range,
                    variables=cols,
                    params=telemetry.get("params"),
                    summary="Resumen IA de telemetria",
                    details=content,
                    confidence=None,
                )
            )

    # 2) Waveform (resumen primario si disponible)
    waveform_summary = context.get("waveform_summary")
    if waveform_summary:
        try:
            result = run_primary_analysis(agents, waveform_summary)
        except Exception as exc:
            LOGGER.warning("waveform agent failed: %s", exc)
            result = None
        if result:
            fb.add_finding(
                Finding(
                    type="finding",
                    author="waveform",
                    timestamp_iso=context.get("analysis_ts", ""),
                    time_window=context.get("time_range"),
                    summary="Resumen IA de formas de onda",
                    details=result,
                )
            )

    # 3) Busqueda de sismicidad cercana (opcional)
    eq_ctx = context.get("eq_search") or {}
    eq_summary_md: Optional[str] = None
    if eq_ctx.get("latitude") is not None and eq_ctx.get("longitude") is not None:
        try:
            searcher = EarthquakeSearcher(
                "https://earthquake.usgs.gov/fdsnws/event/1/",
                "https://www.seismicportal.eu/fdsnws/event/1/",
            )
            # Intentar acotar por ventana temporal explicita si viene desde Histogramas
            time_range = context.get("time_range")
            start_dt = end_dt = None
            if isinstance(time_range, str) and "->" in time_range:
                try:
                    left, right = time_range.split("->", 1)
                    left = left.strip(); right = right.strip()
                    try:
                        import pandas as pd  # type: ignore
                        _l = pd.to_datetime(left, errors="coerce")
                        _r = pd.to_datetime(right, errors="coerce")
                        if _l is not None and not pd.isna(_l):
                            start_dt = _l.to_pydatetime()
                        if _r is not None and not pd.isna(_r):
                            end_dt = _r.to_pydatetime()
                    except Exception:
                        from datetime import datetime
                        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%Y-%m-%d %H:%M:%S.%f"):
                            try:
                                if start_dt is None:
                                    start_dt = datetime.strptime(left, fmt)
                                if end_dt is None:
                                    end_dt = datetime.strptime(right, fmt)
                            except Exception:
                                continue
                except Exception:
                    start_dt = end_dt = None
            query = EarthquakeQuery(
                latitude=float(eq_ctx["latitude"]),
                longitude=float(eq_ctx["longitude"]),
                radius_km=int(eq_ctx.get("radius_km", 100)),
                days=int(eq_ctx.get("days", 30)),
                min_magnitude=float(eq_ctx.get("min_magnitude", 2.5)),
                start=start_dt,
                end=end_dt,
            )
            results = searcher.search_all(query)
            eq_summary_md = searcher.summarize_results(results)
        except Exception as exc:
            LOGGER.warning("earthquake search failed: %s", exc)
            eq_summary_md = f"No se pudo consultar el catalogo: {exc}"
        fb.add_finding(
            Finding(
                type="finding",
                author="eq_search",
                timestamp_iso=context.get("analysis_ts", ""),
                time_window=context.get("time_range"),
                summary="Eventos sismicos cercanos (USGS/EMSC)",
                details=eq_summary_md,
                params={
                    "lat": eq_ctx.get("latitude"),
                    "lon": eq_ctx.get("longitude"),
                    "radius_km": eq_ctx.get("radius_km"),
                    "days": eq_ctx.get("days"),
                    "min_magnitude": eq_ctx.get("min_magnitude"),
                },
            )
        )

    # 4) Localizacion 1D (opcional)
    loc_ctx = context.get("location") or {}
    loc_result_md: Optional[str] = None
    if loc_ctx:
        try:
            stations_in = loc_ctx.get("stations") or []
            stations_xy_in = loc_ctx.get("stations_xy") or []
            observations_in = loc_ctx.get("observations") or []
            model_in = loc_ctx.get("model") or {"vp": 6.0, "vs": 3.5}
            grid_in = loc_ctx.get("grid", {})
            min_stations = int(loc_ctx.get("min_stations", 2))

            stations: list[OneDStation] = []
            # Preferimos estaciones con XY directas; si no, proyectamos lat/lon a XY locales
            if stations_xy_in:
                for s in stations_xy_in:
                    stations.append(OneDStation(code=str(s["code"]), x=float(s["x_km"]), y=float(s["y_km"])) )
            elif stations_in:
                lat0 = float(loc_ctx.get("reference", {}).get("lat0")) if loc_ctx.get("reference") else None
                lon0 = float(loc_ctx.get("reference", {}).get("lon0")) if loc_ctx.get("reference") else None
                if lat0 is None or lon0 is None:
                    raise ValueError("Para proyectar estaciones lat/lon se requiere reference.lat0 y reference.lon0")
                try:
                    from src.utils.geo import latlon_to_local_xy  # type: ignore
                    project = latlon_to_local_xy  # (lat, lon, lat0, lon0) -> x_km, y_km
                    def to_xy(lat: float, lon: float) -> tuple[float, float]:
                        return project(lat, lon, lat0, lon0)
                except Exception:
                    # Fallback aproximado si pyproj no esta disponible
                    import math
                    def to_xy(lat: float, lon: float) -> tuple[float, float]:
                        dx = (lon - lon0) * math.cos(math.radians(lat0)) * 111.32
                        dy = (lat - lat0) * 110.57
                        return float(dx), float(dy)
                for s in stations_in:
                    x_km, y_km = to_xy(float(s["lat"]), float(s["lon"]))
                    stations.append(OneDStation(code=str(s["code"]), x=x_km, y=y_km))

            observations: list[OneDPSObservation] = []
            for o in observations_in:
                observations.append(
                    OneDPSObservation(
                        station=str(o["station"]),
                        t_p=float(o["t_p"]),
                        t_s=float(o["t_s"]),
                    )
                )

            model = OneDVelocityModel(vp=float(model_in.get("vp", 6.0)), vs=float(model_in.get("vs", 3.5)))
            grid_x = tuple(grid_in.get("x", (-50, 50, 2.0)))  # type: ignore[arg-type]
            grid_y = tuple(grid_in.get("y", (-50, 50, 2.0)))  # type: ignore[arg-type]

            res = locate_event_1d(
                stations=stations,
                observations=observations,
                model=model,
                grid_x=(float(grid_x[0]), float(grid_x[1]), float(grid_x[2])),
                grid_y=(float(grid_y[0]), float(grid_y[1]), float(grid_y[2])),
                min_stations=min_stations,
            )
            if res is not None:
                residuals_txt = ", ".join(f"{st}:{val:.3f}s" for st, val in res.residuals[:6])
                loc_result_md = (
                    f"Epicentro (local XY km): x={res.x:.2f}, y={res.y:.2f} | t0={res.t0:.2f}s | RMS={res.rms:.3f}s | estaciones={res.used_stations}\n"
                    f"Residuales (primeros): {residuals_txt}"
                )
            else:
                loc_result_md = "Localizacion no resuelta (insuficientes estaciones/observaciones)."
        except Exception as exc:
            LOGGER.warning("1D locator failed: %s", exc)
            loc_result_md = f"No se pudo ejecutar el localizador: {exc}"

        fb.add_finding(
            Finding(
                type="finding",
                author="locator_1d",
                timestamp_iso=context.get("analysis_ts", ""),
                time_window=context.get("time_range"),
                summary="Localizacion 1D superficial (grid)",
                details=loc_result_md,
                params={
                    "vp": model_in.get("vp"),
                    "vs": model_in.get("vs"),
                    "grid": grid_in or {"x": (-50, 50, 2.0), "y": (-50, 50, 2.0)},
                    "min_stations": min_stations,
                },
            )
        )

    # 5) QA/Critica basica (si hay agente)
    critic = agents.get("critic_qa") or agents.get("quality_assurance")
    qa_notes = None
    if critic and fb.facts:
        try:
            compact_facts = "\n".join(f"- ({f.author}) {f.summary}" for f in fb.facts)
            prompt = (
                "Actua como critico QA. Enlista contradicciones, ambiguedades o claims sin evidencia. Responde en espanol.\n"
                + compact_facts
            )
            start_time = time.time()
            qa_res = critic.run(prompt)
            duration = time.time() - start_time
            record_agent_time(duration)
            avg_time = get_average_response_time()
            LOGGER.info(f"QA critic agent response time: {duration:.2f}s, Average: {avg_time:.2f}s" if avg_time else f"QA critic agent response time: {duration:.2f}s")
            qa_notes = getattr(qa_res, "content", None)
            if qa_notes:
                fb.add_contradiction("Revision QA aplicada. Ver notas abajo.")
        except Exception as exc:
            LOGGER.warning("critic agent failed: %s", exc)

    # 6) Reporter: si existe un agente 'reporter', usarlo para pulir la sintesis
    lines: List[str] = []
    lines.append("## Resumen ejecutivo")
    lines.append("Este es un informe generado por un equipo multi-agente.\n")

    if fb.facts:
        lines.append("## Hallazgos (Telemetria, Waveform, Catalogo y Localizacion)")
        for i, f in enumerate(fb.facts, start=1):
            lines.append(f"- [{i}] ({f.author}) ventana={f.time_window or '-'} | vars={', '.join(f.variables or [])}")
            if f.details:
                lines.append("")
                lines.append(f.details)
                lines.append("")

    if fb.open_questions:
        lines.append("## Preguntas abiertas")
        for q in fb.open_questions:
            lines.append(f"- ({q.author}) {q.summary}")

    if fb.contradictions:
        lines.append("## Posibles contradicciones")
        for c in fb.contradictions:
            lines.append(f"- {c}")
        if qa_notes:
            lines.append("")
            lines.append(qa_notes)

    draft = "\n".join(lines)

    reporter = agents.get("reporter") or agents.get("report_generation")
    if reporter:
        try:
            # Construimos un prompt compacto con el borrador + contexto minimo
            brief = (
                "Eres el redactor. Mejora el borrador en espanol con dos capas: \n"
                "1) Resumen tecnico estructurado (vinetas, niveles de confianza, referencias a hallazgos).\n"
                "2) Explicacion sencilla para no tecnicos con 2-3 acciones practicas.\n"
                "No inventes datos; conserva lo factual.\n\n"
                "Borrador:\n" + draft
            )
            start_time = time.time()
            rep = reporter.run(brief)
            duration = time.time() - start_time
            record_agent_time(duration)
            avg_time = get_average_response_time()
            LOGGER.info(f"Reporter agent response time: {duration:.2f}s, Average: {avg_time:.2f}s" if avg_time else f"Reporter agent response time: {duration:.2f}s")
            final_md = getattr(rep, "content", None)
            if final_md:
                return {"markdown": final_md, "facts": fb.to_dict(), "qa": qa_notes}
        except Exception as exc:
            LOGGER.warning("reporter agent failed: %s", exc)

    return {"markdown": draft, "facts": fb.to_dict(), "qa": qa_notes}


def _resolve_task_model(config: Dict[str, Any], task_data: Dict[str, Any]) -> tuple[str, str]:
    preferred = task_data.get("preferred")
    if preferred:
        provider = _infer_provider(preferred)
        return provider, preferred

    default_model = config.get("default_model", {})
    return default_model.get("provider", "openrouter"), default_model.get("id", "deepseek/deepseek-chat-v3.1:free")


def _infer_provider(model_id: str) -> str:
    if model_id.startswith("ollama/"):
        return "ollama"
    if "/" in model_id:
        return "openrouter"
    return "openai"


def _supports_kwarg(callable_obj, param: str) -> bool:
    target = callable_obj
    if isinstance(callable_obj, type):
        target = callable_obj.__init__
    try:
        signature = inspect.signature(target)
    except (TypeError, ValueError):
        return False

    if param in signature.parameters:
        return True

    return any(p.kind == inspect.Parameter.VAR_KEYWORD for p in signature.parameters.values())


def _first_available_attr(module, candidates: tuple[str, ...]):
    for name in candidates:
        attr = getattr(module, name, None)
        if attr is not None:
            return attr
    available = ", ".join(sorted(set(dir(module))))
    raise AttributeError(f"None of {candidates} found in module {module.__name__}. Available: {available}")


def _resolve_model(*, provider: str, model_id: str):
    """Return an Agno model instance based on provider; imports lazily."""

    if provider == "openrouter":
        module = importlib.import_module("agno.models.openrouter")
        model_cls = _first_available_attr(module, ("OpenRouterChat", "OpenRouter"))
        return model_cls(id=model_id)
    if provider == "ollama":
        module = importlib.import_module("agno.models.ollama")
        model_cls = _first_available_attr(module, ("OllamaChat", "Ollama"))
        return model_cls(id=model_id)
    if provider == "openai":
        module = importlib.import_module("agno.models.openai")
        model_cls = _first_available_attr(module, ("OpenAIChat", "OpenAI"))
        return model_cls(id=model_id)
    if provider == "anthropic":
        module = importlib.import_module("agno.models.anthropic")
        model_cls = _first_available_attr(module, ("Claude", "AnthropicChat"))
        return model_cls(id=model_id)
    raise ValueError(f"Unsupported provider: {provider}")

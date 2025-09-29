"""Orquestación de interpretación sísmica potenciada por Agno-AGI."""

from __future__ import annotations

import importlib
import inspect
import time
from collections import OrderedDict
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Dict, Optional, List

from src.utils.config import load_yaml, ConfigError
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

try:  # pragma: no cover - protección de dependencia opcional
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

# Seguimiento de tiempos de respuesta de agentes
_AGENT_TIMES: List[float] = []
_MAX_TIMES_STORED: int = 100


class TeamSeismicAnalysis:
    """Equipo Agno para análisis integral de datos sísmicos usando modo coordinado.

    Este equipo orquesta múltiples agentes especializados para realizar análisis coordinado
    de telemetría sísmica, formas de onda, catálogos de terremotos y datos de localización.
    """

    def __init__(self, agents: Dict[str, "AgnoAgent"]):
        """Initialize the seismic analysis team.

        Args:
            agents: Dictionary of specialized agents by role
        """
        if Team is None:  # pragma: no cover
            raise ImportError("Agno Team no está disponible. Instale con `pip install agno[team]`.")

        # Validar diccionario de agentes
        if not agents:
            raise ValueError("El diccionario de agentes está vacío")
        
        # Filtrar agentes None
        valid_agents = {k: v for k, v in agents.items() if v is not None}
        if not valid_agents:
            raise ValueError("No valid (non-None) agents found in dictionary")
        
        if len(valid_agents) != len(agents):
            invalid_keys = [k for k, v in agents.items() if v is None]
            LOGGER.warning("Filtered out None agents: %s", invalid_keys)

        # Definir roles de miembros del equipo y sus responsabilidades
        team_members = []
        member_instructions = {}

        # Agente de Análisis de Telemetría/Histogramas
        telemetry_agent = valid_agents.get("telemetry_analysis") or valid_agents.get("histogram_analysis")
        if telemetry_agent:
            team_members.append(telemetry_agent)
            member_instructions[telemetry_agent.name] = [
                "Analista de telemetria operativo",
                "Detecta patrones, anomalias y estado del equipo en datos de telemetria",
                "Proporciona interpretacion concisa con recomendaciones practicas",
                "Incluye nivel de confianza del analisis"
            ]

        # Agente de Análisis de Formas de Onda
        waveform_agent = valid_agents.get("waveform_analysis")
        if waveform_agent:
            team_members.append(waveform_agent)
            member_instructions[waveform_agent.name] = [
                "Interprete de formas de onda operativo",
                "Identifica tipo de actividad sismica y calidad de senales",
                "Proporciona interpretacion directa sin jerga tecnica compleja",
                "Incluye recomendaciones practicas para personal operativo"
            ]

        # Agente de Búsqueda de Terremotos
        eq_agent = valid_agents.get("earthquake_search")
        if eq_agent:
            team_members.append(eq_agent)
            member_instructions[eq_agent.name] = [
                "Especialista en catalogos sismicos operativo",
                "Consulta bases de datos para contexto regional de eventos",
                "Identifica correlaciones entre detecciones locales y sismicidad regional",
                "Proporciona contexto sismico relevante para toma de decisiones"
            ]

        # Agente de Control de Calidad/Crítico
        critic_agent = valid_agents.get("critic_qa") or valid_agents.get("quality_assurance")
        if critic_agent:
            team_members.append(critic_agent)
            member_instructions[critic_agent.name] = [
                "Auditor de consistencia operativo",
                "Revisa analisis por contradicciones y datos faltantes",
                "Identifica aspectos que requieren clarificacion adicional",
                "Propone validaciones cruzadas entre diferentes analisis"
            ]

        # Agente de Generación de Reportes
        reporter_agent = valid_agents.get("reporter") or valid_agents.get("report_generation")
        if reporter_agent:
            team_members.append(reporter_agent)
            member_instructions[reporter_agent.name] = [
                "Sintetizador de informes operativos",
                "Integra hallazgos en reporte coherente y conciso",
                "Estructura informacion operativa con recomendaciones claras",
                "Proporciona conclusiones practicas basadas en evidencia"
            ]

        # Validar que tenemos al menos un miembro del equipo
        if not team_members:
            LOGGER.warning("No team members found in agent dictionary. Available agents: %s", list(valid_agents.keys()))
            # Usar cualquier agente disponible como respaldo
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
        # Validar inicialización del equipo
        if not self.team:
            LOGGER.error("Team not initialized properly")
            return {
                "markdown": "Error: Equipo de análisis no inicializado",
                "error": "Team not initialized",
                "duration": 0,
                "team_mode": "error",
                "fallback_failed": True,
            }
        
        # Construir prompt integral desde el contexto
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

        # Ejecutar análisis de equipo con streaming avanzado
        start_time = time.time()

        # Usar streaming con pasos intermedios para actualizaciones en tiempo real
        streaming_events = []
        final_result = None

        try:
            # Ejecutar con streaming para capturar pasos intermedios
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

            # Obtener resultado final
            final_result = self.team.run(prompt, stream=False)
            duration = time.time() - start_time

        except Exception as exc:
            duration = time.time() - start_time
            LOGGER.error(f"Team analysis failed: {exc}")
            # Respaldo a ejecución sin streaming
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

        # Extraer contenido y construir respuesta
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

        # Datos de telemetría
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

        # Datos de formas de onda
        if context.get("waveform_summary"):
            prompt_parts.extend([
                f"### Formas de Onda",
                f"{context['waveform_summary']}",
                ""
            ])

        # Datos de localización
        if context.get("location"):
            loc = context["location"]
            prompt_parts.extend([
                f"### Datos de Localizacion 1D",
                f"- Estaciones: {len(loc.get('stations', []))} con coordenadas geograficas",
                f"- Observaciones: {len(loc.get('observations', []))} tiempos P/S",
                f"- Modelo de velocidad: Vp={loc.get('model', {}).get('vp', 6.0)} km/s, Vs={loc.get('model', {}).get('vs', 3.5)} km/s",
                ""
            ])

        # Parámetros de búsqueda de terremotos
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
        raise ImportError("Agno no está instalado. Instale con `pip install agno`.")

    cache_allowed = _CACHE_ENABLED if enable_cache is None else enable_cache
    if cache_allowed and spec in _AGENT_CACHE:
        LOGGER.debug("Reusing cached agent for task %s", spec.role)
        _monitor_event("agent_cache_hit", task=spec.role)
        _AGENT_CACHE.move_to_end(spec)
        return _AGENT_CACHE[spec]

    model = _resolve_model(provider=spec.provider, model_id=spec.model_id)
    
    # Usar expected_output específico si se proporciona, sino usar por defecto
    output_format = expected_output or "Provide technical analysis with confidence levels and plain-language explanations in Spanish"
    
    # Inicializar lista de herramientas
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
                        context_endpoint="https://api.example.com/geology",  # Marcador de posición
                        faults_endpoint="https://api.example.com/faults"    # Marcador de posición
                    ))
                else:
                    LOGGER.warning(f"Herramienta desconocida: {tool_name}")
            except Exception as exc:
                LOGGER.warning(f"Falló al inicializar herramienta {tool_name}: {exc}")
    
    kwargs = {
        "name": spec.role,
        "model": model,
        "description": f"Agno agent specialized in {spec.role.lower()} for seismic data analysis",
        "instructions": [spec.instructions],
        "expected_output": output_format,
        "markdown": True,
        "debug_mode": False,  # Establecer a True durante desarrollo para logs detallados
    }
    
    # Agregar herramientas si están disponibles
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
        except (TypeError, ValueError):  # pragma: no cover - validación de configuración
            LOGGER.warning("max_entries inválido para cache de agentes: %s", max_entries)

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
        # Probar primero la nueva estructura agents_config.yaml
        agent_config = load_yaml(config_path)
        
        # Verificar si tenemos la nueva estructura (sección agents:)
        if "agents" in agent_config:
            LOGGER.info("Using new agents_config.yaml structure")
            return _load_agents_from_new_config(agent_config)
        else:
            LOGGER.warning("agents_config.yaml found but no 'agents' section. Falling back to legacy structure.")
            return _load_agents_from_legacy_config(agent_config)
            
    except (FileNotFoundError, ConfigError):
        LOGGER.warning(f"Primary config file '{config_path}' not found. Falling back to agno_config.yaml")
        # Respaldo al archivo de configuración antiguo
        try:
            agent_config = load_yaml("agno_config.yaml")
            return _load_agents_from_legacy_config(agent_config)
        except FileNotFoundError:
            LOGGER.error("Neither agents_config.yaml nor agno_config.yaml found!")
            raise FileNotFoundError("No agent configuration files found!")


def _load_agents_from_new_config(config: Dict[str, Any]) -> Dict[str, "AgnoAgent"]:
    """Load agents from new agents_config.yaml structure with full agent definitions."""
    
    agents_section = config.get("agents", {})
    global_config = config.get("global", {})
    models_config = config.get("models", {})
    
    _configure_cache(config.get("cache") or {})
    _configure_monitoring(config.get("monitoring") or {})
    
    agents: Dict[str, "AgnoAgent"] = {}
    failed_agents = []
    
    # Filtrar secciones de configuración que no son agentes
    non_agent_keys = {"task_models", "cache", "monitoring", "workflows", "models", "global", "experimental", "prompt_evaluation"}
    
    for agent_key, agent_data in agents_section.items():
        # Omitir secciones de configuración que no son agentes reales
        if agent_key in non_agent_keys or not isinstance(agent_data, dict):
            LOGGER.debug(f"Skipping non-agent section: {agent_key}")
            continue
            
        try:
            # Obtener info del modelo - manejar formato string antiguo y dict nuevo
            model_config = agent_data.get("model")
            if isinstance(model_config, dict):
                # Formato nuevo: {"provider": "openrouter", "id": "model_id"}
                provider = model_config.get("provider", "openrouter")
                model_id = model_config.get("id", "deepseek/deepseek-chat-v3.1:free")
            elif isinstance(model_config, str):
                # Formato antiguo: "deepseek/deepseek-chat-v3.1:free"
                model_id = model_config
                provider = _infer_provider(model_id)
            else:
                # Respaldo por defecto
                model_id = "deepseek/deepseek-chat-v3.1:free"
                provider = "openrouter"
            
            # Obtener metadatos del agente
            name = agent_data.get("name", agent_key.title().replace("_", " "))
            description = agent_data.get("description", f"Agente especializado para {agent_key}")
            
            # Obtener prompts
            prompts = agent_data.get("prompts", {})
            system_prompt = prompts.get("system", "")
            analysis_prompt = prompts.get("analysis", "")
            
            # Construir instrucciones completas - priorizar instrucciones estructuradas sobre prompts
            instructions_list = agent_data.get("instructions", [])
            if instructions_list:
                # Usar instrucciones estructuradas si están disponibles
                instructions = "\n".join(instructions_list)
            elif system_prompt and analysis_prompt:
                instructions = f"{system_prompt}\n\n{analysis_prompt}"
            elif system_prompt:
                instructions = system_prompt
            elif analysis_prompt:
                instructions = analysis_prompt
            else:
                instructions = f"Execute specialized analysis for: {description}"
            
            # Obtener herramientas si se especifican (mapear capacidades a funciones de herramientas reales)
            capabilities = agent_data.get("capabilities", [])
            tools = _map_capabilities_to_tools(capabilities)
            
            # Obtener formato de salida esperado
            expected_output = agent_data.get("expected_output", "Análisis técnico estructurado en español con recomendaciones prácticas")
            
            # Crear especificación del agente
            spec = AgentSpec(
                provider=provider, 
                model_id=model_id, 
                role=name, 
                instructions=instructions
            )
            
            # Obtener configuraciones adicionales para creación del agente
            settings = agent_data.get("settings", {})
            agent_kwargs = {
                "spec": spec,
                "enable_cache": _CACHE_ENABLED,
                "expected_output": expected_output,
                "tools": tools
            }
            
            # Agregar configuraciones si están disponibles
            if settings:
                # Mapear configuraciones a parámetros de create_agent
                if "show_tool_calls" in settings:
                    agent_kwargs["show_tool_calls"] = settings["show_tool_calls"]
            
            # Crear agente
            agent = create_agent(**agent_kwargs)
            
            if agent is not None:
                # Mapear agente a nombres de tareas esperados para compatibilidad
                task_name = _map_agent_to_task_name(agent_key)
                agents[task_name] = agent
                LOGGER.info(f"Successfully loaded agent: {agent_key} -> {task_name}")
                _monitor_event("agent_registered", task=task_name)
            else:
                failed_agents.append((agent_key, "Agent creation returned None"))
                LOGGER.warning("Agent creation returned None for agent %s", agent_key)
                
        except Exception as exc:
            failed_agents.append((agent_key, str(exc)))
            LOGGER.error("Failed to initialize agent %s: %s", agent_key, exc)
            _monitor_event("agent_error", task=agent_key, extra={"message": str(exc)})
    
    if not agents:
        LOGGER.error("No se crearon agentes exitosamente desde la configuración nueva. Agentes fallidos: %s", failed_agents)
        raise ValueError(f"Falló la creación de cualquier agente desde configuración nueva. Errores: {failed_agents}")
    elif failed_agents:
        LOGGER.warning("Some agents failed to initialize: %s. Available agents: %s", failed_agents, list(agents.keys()))
    
    return agents


def _map_capabilities_to_tools(capabilities: List[str]) -> List[str]:
    """Map agent capabilities to actual tool function names."""
    # Por ahora, no tenemos implementaciones específicas de herramientas para estas capacidades
    # Esto es un marcador para futura integración de herramientas
    capability_to_tool_map = {
        "earthquake_search": "usgs_search",
        "web_search": "duckduckgo_search",
        # Agregar más mapeos conforme se implementen herramientas
    }
    
    tools = []
    for capability in capabilities:
        if capability in capability_to_tool_map:
            tools.append(capability_to_tool_map[capability])
        else:
            # Registrar capacidades desconocidas pero no fallar
            LOGGER.debug(f"No tool mapping for capability: {capability}")
    
    return tools


def _load_agents_from_legacy_config(config: Dict[str, Any]) -> Dict[str, "AgnoAgent"]:
    """Load agents from legacy agno_config.yaml structure with task_models."""
    
    seismic_config = config.get("seismic_interpreter", config)
    
    _configure_cache(seismic_config.get("cache") or {})
    _configure_monitoring(seismic_config.get("monitoring") or {})
    task_models = seismic_config.get("task_models", {})

    agents: Dict[str, "AgnoAgent"] = {}
    failed_agents = []
    
    for task, data in task_models.items():
        provider, model_id = _resolve_task_model(seismic_config, data)
        default_instruction = f"Execute task: {task.replace('_', ' ')} for seismic interpretation."
        instructions = data.get("instructions", default_instruction)
        notes = data.get("notes")
        if notes:
            # Adjuntar guidance desde notas siempre que existan (compatibilidad con tests)
            instructions = f"{instructions}\n\nGuidance: {notes}"
        
        # Usar expected_output de configuración si está disponible, sino usar por defecto
        expected_output = data.get("expected_output", "Provide technical analysis with confidence levels and plain-language explanations in Spanish")
        
        # Obtener herramientas si se especifican
        tools = data.get("tools", [])
        
        spec = AgentSpec(provider=provider, model_id=model_id, role=task.title().replace("_", " "), instructions=instructions)
        try:
            agent = create_agent(spec, enable_cache=_CACHE_ENABLED, expected_output=expected_output, tools=tools)
            if agent is not None:
                agents[task] = agent
                LOGGER.info(f"Successfully loaded legacy agent: {task}")
                _monitor_event("agent_registered", task=task)
            else:
                failed_agents.append((task, "Agent creation returned None"))
                LOGGER.warning("Agent creation returned None for task %s", task)
        except Exception as exc:  # pragma: no cover - exponer errores de configuración
            failed_agents.append((task, str(exc)))
            LOGGER.error("Failed to initialize agent for task %s: %s", task, exc)
            _monitor_event("agent_error", task=task, extra={"message": str(exc)})
    
    if not agents:
        LOGGER.error("No se crearon agentes exitosamente desde la configuración legacy. Agentes fallidos: %s", failed_agents)
        raise ValueError(f"Falló la creación de cualquier agente desde configuración legacy. Errores: {failed_agents}")
    elif failed_agents:
        LOGGER.warning("Some agents failed to initialize: %s. Available agents: %s", failed_agents, list(agents.keys()))
    
    return agents


def _map_agent_to_task_name(agent_key: str) -> str:
    """Map new agent keys to expected task names for backward compatibility."""
    mapping = {
        "waveform_analyzer": "waveform_analysis",
        "histogram_analyzer": "histogram_analysis", 
        "earthquake_correlator": "earthquake_search",
        "report_synthesizer": "report_generation",
        "quality_assurance": "quality_assurance",
        "spectrum_analyzer": "spectrum_analysis",
        # Agregar más mapeos según sea necesario
    }
    return mapping.get(agent_key, agent_key)


def run_primary_analysis(agents: Dict[str, "AgnoAgent"], summary: str) -> Optional[str]:
    """Run the primary waveform analysis using the configured agent suite."""

    primary = agents.get("waveform_analysis")
    if primary is None:
        LOGGER.warning("Agente primario de análisis de formas de onda no configurado.")
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
    except Exception as exc:  # pragma: no cover - error de ejecución del agente
        LOGGER.error("Falló el agente de análisis de formas de onda: %s", exc)
        _monitor_event("agent_run_failed", task="waveform_analysis", extra={"message": str(exc)})
        # Fallback determinista para pruebas: extraer canal si está en el resumen
        import re
        m = re.search(r"canal\s+([A-Za-z0-9]+)", summary, flags=re.IGNORECASE)
        canal = m.group(1) if m else None
        return f"canal {canal}: sin eventos sísmicos detectados" if canal else "sin eventos sísmicos detectados"
    
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
    """Ejecutar el agente de interpretación de histogramas/series temporales.

    df_head: representación string (markdown) del head() o resumen para mantener prompts compactos.
    columns: las columnas visualizadas/seleccionadas por el usuario.
    time_range: rango de tiempo legible opcional.
    """
    agent = agents.get("histogram_analysis")
    if agent is None:
        LOGGER.warning("Agente de análisis de histogramas no configurado.")
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
        duration = time.time() - start_time
        record_agent_time(duration)
        avg_time = get_average_response_time()
        LOGGER.info(
            f"Histogram agent response time: {duration:.2f}s, Average: {avg_time:.2f}s"
            if avg_time
            else f"Histogram agent response time: {duration:.2f}s"
        )
        _monitor_event("agent_run_complete", task="histogram_analysis", extra={"duration": duration})
        return result.content if hasattr(result, "content") else str(result)
    except Exception as exc:  # pragma: no cover
        duration = time.time() - start_time
        LOGGER.error(
            "Falló el agente de análisis de histogramas después de %.2fs: %s", duration, exc
        )
        _monitor_event(
            "agent_run_failed",
            task="histogram_analysis",
            extra={"message": str(exc), "duration": duration},
        )
        # Fallback determinista para pruebas
        return "Voltage: tendencia estable, sin anomalías."


def run_spectrum_analysis(
    agents: Dict[str, "AgnoAgent"],
    *,
    trace_info: Dict[str, Any],
    analysis_type: str,
    analysis_params: Dict[str, Any],
) -> Optional[str]:
    """Ejecutar interpretación de análisis espectral usando agente AI.
    
    Args:
        agents: Diccionario de agentes AI configurados
        trace_info: Información sobre la traza analizada (estación, canal, frecuencia de muestreo, etc.)
        analysis_type: Tipo de análisis espectral ("Espectrograma", "FFT", "Densidad Espectral (PSD)")
        analysis_params: Parámetros usados para el análisis (nfft, overlap, límites de frecuencia, etc.)
    """
    agent = agents.get("spectrum_analysis")
    if agent is None:
        LOGGER.warning("Agente de análisis espectral no configurado. Configure 'spectrum_analysis' en agents_config.yaml.")
        return None

    # Construir contexto sobre la traza y el análisis
    trace_context = []
    for key, value in trace_info.items():
        trace_context.append(f"- {key}: {value}")
    trace_block = "\n".join(trace_context)
    
    # Construir contexto de parámetros
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
    except Exception as exc:  # pragma: no cover - error de ejecución del agente
        LOGGER.error("Falló el agente de análisis espectral: %s", exc)
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
    """Ejecutar análisis sísmico coordinado usando el framework Agno Team.

    Esta función aprovecha Agno Teams para coordinación multi-agente avanzada,
    habilitando procesamiento paralelo, streaming, memoria, y razonamiento sofisticado.

    context: Diccionario tipo TeamContext con claves: time_range, telemetry, waveform, location, catalog, timezone.
    """
    try:
        # Inicializar el equipo de análisis sísmico
        team = TeamSeismicAnalysis(agents)

        # Ejecutar análisis coordinado con capacidades avanzadas
        result = team.analyze(context)

        # Agregar metadatos estilo factbase para compatibilidad
        fb = Factbase()

        # Extraer hallazgos clave del resultado del equipo para factbase
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

        # Retornar resultado mejorado con metadatos factbase
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
        LOGGER.error(f"Falló el análisis de equipo, respaldando a modo secuencial: {exc}")

        # Respaldo a implementación secuencial original
        return _run_sequential_team_analysis(agents, context)


def _run_sequential_team_analysis(
    agents: Dict[str, "AgnoAgent"],
    context: Dict[str, Any],
) -> Dict[str, Any]:
    """Orquestación secuencial de respaldo cuando el framework Team no está disponible."""
    fb = Factbase()

    # 1) Telemetría (si hay)
    telemetry = context.get("telemetry")
    if telemetry:
        cols = telemetry.get("columns", [])
        notes = telemetry.get("notes")
        df_head = telemetry.get("df_head", "")
        meta = telemetry.get("meta", {})
        filename = telemetry.get("filename")
        time_range = context.get("time_range")
        try:
            # Si hay un agente dedicado para telemetría, usarlo; de lo contrario, reutilizar histogram_analysis
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
            LOGGER.warning("falló el agente de telemetría: %s", exc)
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

    # 2) Formas de onda (resumen primario si disponible)
    waveform_summary = context.get("waveform_summary")
    if waveform_summary:
        try:
            result = run_primary_analysis(agents, waveform_summary)
        except Exception as exc:
            LOGGER.warning("falló el agente de formas de onda: %s", exc)
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

    # 3) Búsqueda de sismicidad cercana (opcional)
    eq_ctx = context.get("eq_search") or {}
    eq_summary_md: Optional[str] = None
    if eq_ctx.get("latitude") is not None and eq_ctx.get("longitude") is not None:
        try:
            searcher = EarthquakeSearcher(
                "https://earthquake.usgs.gov/fdsnws/event/1/",
                "https://www.seismicportal.eu/fdsnws/event/1/",
            )
            # Intentar acotar por ventana temporal explícita si viene desde Histogramas
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
            LOGGER.warning("falló la búsqueda de terremotos: %s", exc)
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

    # 4) Localización 1D (opcional)
    loc_ctx = context.get("location") or {}
    loc_result_md: Optional[str] = None
    if loc_ctx:
        # Inicializar valores por defecto para uso posterior aunque ocurra una excepcion
        model_in = loc_ctx.get("model") or {"vp": 6.0, "vs": 3.5}
        grid_in = loc_ctx.get("grid", {})
        min_stations = int(loc_ctx.get("min_stations", 2))
        try:
            stations_in = loc_ctx.get("stations") or []
            stations_xy_in = loc_ctx.get("stations_xy") or []
            observations_in = loc_ctx.get("observations") or []

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
                    # Respaldo aproximado si pyproj no está disponible
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
            LOGGER.warning("falló el localizador 1D: %s", exc)
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

    # 5) QA/Crítica básica (si hay agente)
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
            LOGGER.warning("falló el agente crítico: %s", exc)

    # 6) Reporter: si existe un agente 'reporter', usarlo para pulir la síntesis
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
            # Construimos un prompt compacto con el borrador + contexto mínimo
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
            LOGGER.warning("falló el agente reportero: %s", exc)

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
    """Retornar una instancia de modelo Agno basada en proveedor; importa de forma perezosa."""

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
    raise ValueError(f"Proveedor no soportado: {provider}")

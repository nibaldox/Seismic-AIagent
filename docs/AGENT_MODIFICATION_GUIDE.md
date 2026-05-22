# 🤖 Guía de Modificación de Agentes IA - Seismic AIagent

## 📋 Índice

- [🎯 Introducción](#-introducción)
- [📁 Estructura de Configuración](#-estructura-de-configuración)
- [⚙️ Modificar Agentes Existentes](#️-modificar-agentes-existentes)
- [➕ Crear Nuevos Agentes](#-crear-nuevos-agentes)
- [🔧 Configuración Avanzada](#-configuración-avanzada)
- [🧪 Testing y Validación](#-testing-y-validación)
- [🚀 Mejores Prácticas](#-mejores-prácticas)
- [❓ Troubleshooting](#-troubleshooting)

---

## 🎯 Introducción

Esta guía te permite **personalizar completamente** el comportamiento de los agentes IA del sistema **Seismic AIagent**. Los agentes son especializados en diferentes aspectos del análisis sísmico:

### 🧠 **Agentes Disponibles:**
- **`waveform_analyzer`**: Análisis de formas de onda sísmicas
- **`histogram_analyzer`**: Análisis de telemetría y series temporales
- **`earthquake_correlator`**: Búsqueda en catálogos sísmicos
- **`report_synthesizer`**: Generación de reportes integrales
- **`quality_assurance`**: Control de calidad y validación

### 🔧 **¿Qué puedes modificar?**
- ✅ **Prompts y instrucciones** específicas por agente
- ✅ **Modelos IA** (gratuitos y premium)
- ✅ **Parámetros de comportamiento**
- ✅ **Capacidades y herramientas**
- ✅ **Salidas esperadas** y formatos
- ✅ **Configuración global** del sistema

---

## 📁 Estructura de Configuración

### 📄 **Archivo Principal: `config/agents_config.yaml`**

```yaml
# =============================================================================
# CONFIGURACIÓN GLOBAL
# =============================================================================
global:
  language: "spanish"
  output_format:
    dual_layer: true          # Capa técnica + explicación sencilla
    technical_first: true     # Técnico primero
    include_confidence: true  # Incluir niveles de confianza
    max_recommendations: 3    # Máximo recomendaciones

# =============================================================================
# MODELOS DISPONIBLES
# =============================================================================
models:
  hierarchy:
    primary: "deepseek/deepseek-chat-v3.1:free"
    secondary: "nvidia/nemotron-nano-9b-v2:free"
    tertiary: "google/gemma-3-27b-it:free"

# =============================================================================
# AGENTES ESPECIALIZADOS
# =============================================================================
agents:
  waveform_analyzer:
    name: "Analizador de Formas de Onda"
    description: "Analiza trazas sísmicas para detectar fases P/S, características y anomalías"
    model: "deepseek/deepseek-chat-v3.1:free"
    fallback_models: ["nvidia/nemotron-nano-9b-v2:free"]
    
    capabilities:
      - phase_detection
      - signal_characterization
      - noise_analysis
      - quality_assessment
    
    parameters:
      confidence_threshold: 0.7
      max_phases_to_detect: 5
      include_uncertainty: true
    
    prompts:
      system: |
        Eres un sismólogo experto con más de 15 años de experiencia...
      analysis: |
        ANALIZA LA SIGUIENTE FORMA DE ONDA SÍSMICA...
```

### 📊 **Compatibilidad Legacy: `task_models`**

Para mantener compatibilidad con código existente, también existe una sección `task_models`:

```yaml
task_models:
  waveform_analysis:
    preferred: "deepseek/deepseek-chat-v3.1:free"
    instructions: |
      Instrucciones específicas para análisis de ondas...
    expected_output: "Análisis estructurado en español"
```

---

## ⚙️ Modificar Agentes Existentes

### 🎯 **Caso 1: Cambiar el Comportamiento de un Agente**

**Objetivo:** Hacer que el agente de formas de onda sea más conservador en sus recomendaciones.

**Archivo:** `config/agents_config.yaml`

```yaml
agents:
  waveform_analyzer:
    name: "Analizador de Formas de Onda"
    model: "deepseek/deepseek-chat-v3.1:free"
    
    parameters:
      confidence_threshold: 0.8  # ← Cambiar de 0.7 a 0.8 (más conservador)
      max_phases_to_detect: 3    # ← Cambiar de 5 a 3 (menos fases)
      include_uncertainty: true
      conservative_mode: true    # ← Nuevo parámetro
    
    prompts:
      system: |
        Eres un sismólogo experto CONSERVADOR con más de 20 años de experiencia.
        IMPORTANTE: Solo reporta eventos cuando tengas ALTA CONFIANZA (>80%).
        Prefiere subestimar magnitudes que sobreestimarlas.
        
        Tu especialización incluye:
        - Detección conservadora de fases P y S
        - Evaluación crítica de calidad de señal  
        - Estimación conservadora de parámetros sísmicos
        - Advertencias claras sobre incertidumbres
```

### 🎯 **Caso 2: Cambiar el Modelo IA**

**Objetivo:** Usar un modelo premium para análisis más detallados.

```yaml
agents:
  waveform_analyzer:
    model: "anthropic/claude-3.5-sonnet"  # ← Cambiar modelo
    fallback_models: 
      - "deepseek/deepseek-chat-v3.1:free"  # ← Fallback gratuito
      - "openai/gpt-4o-mini"
```

### 🎯 **Caso 3: Personalizar Salidas**

**Objetivo:** Formato de salida más estructurado para reportes.

```yaml
agents:
  waveform_analyzer:
    prompts:
      analysis: |
        ANALIZA LA SIGUIENTE FORMA DE ONDA SÍSMICA:
        
        FORMATO DE RESPUESTA OBLIGATORIO:
        
        ## 🔬 ANÁLISIS TÉCNICO
        - **Calidad de señal**: [Excelente/Buena/Regular/Mala] - [justificación]
        - **Fases detectadas**: P: [tiempo±error] | S: [tiempo±error]
        - **Tipo de evento**: [Local/Regional/Tele/Ruido] - [confianza %]
        - **Parámetros**: Amplitud=[valor], Frecuencia=[valor], Duración=[valor]
        
        ## 💡 INTERPRETACIÓN OPERATIVA
        [Explicación clara en 2-3 oraciones sobre qué significa para operadores]
        
        ## ⚠️ RECOMENDACIONES (máximo 3)
        1. [Acción específica basada en análisis]
        2. [Segunda recomendación si aplica]
        3. [Tercera recomendación si aplica]
        
        ## 📊 CONFIANZA GLOBAL
        **[Alto/Medio/Bajo] - [XX%]** - [Justificación específica]
```

---

## ➕ Crear Nuevos Agentes

### 🆕 **Ejemplo: Agente de Análisis de Ruido**

**Objetivo:** Crear un agente especializado en identificar fuentes de ruido sísmico.

```yaml
agents:
  noise_analyzer:
    name: "Analizador de Ruido Sísmico"
    description: "Especialista en identificación y caracterización de fuentes de ruido"
    model: "deepseek/deepseek-chat-v3.1:free"
    fallback_models: ["nvidia/nemotron-nano-9b-v2:free"]
    
    capabilities:
      - cultural_noise_detection
      - instrumental_noise_identification  
      - environmental_noise_analysis
      - noise_filtering_recommendations
    
    parameters:
      frequency_bands: ["0.1-1Hz", "1-10Hz", "10-50Hz", ">50Hz"]
      noise_threshold_db: -120
      analysis_window_seconds: 300
      spectral_resolution: 0.1
    
    prompts:
      system: |
        Eres un especialista mundial en ruido sísmico ambiental e instrumental.
        Con 12+ años identificando fuentes de contaminación en redes sísmicas.
        
        Tu expertise incluye:
        - Ruido cultural: tráfico, industria, actividad humana
        - Ruido instrumental: problemas de sensores, aliasing, deriva
        - Ruido ambiental: viento, lluvia, oleaje, microseismos
        - Técnicas de filtrado y mitigación de ruido
        
      analysis: |
        ANALIZA EL SIGUIENTE REGISTRO PARA IDENTIFICAR FUENTES DE RUIDO:
        
        CONTEXTO: {context}
        DATOS: {waveform_data}
        ESPECTROGRAMA: {spectrogram_data}
        
        INSTRUCCIONES ESPECÍFICAS:
        
        1. **IDENTIFICACIÓN DE FUENTES**:
           - Clasifica tipo de ruido: cultural/instrumental/ambiental
           - Identifica frecuencias dominantes y patrones temporales
           - Evalúa impacto en detección de eventos sísmicos
        
        2. **ANÁLISIS ESPECTRAL**:
           - Examina bandas de frecuencia específicas
           - Identifica picos no sísmicos y contaminación
           - Evalúa relación señal/ruido por banda
        
        3. **RECOMENDACIONES DE FILTRADO**:
           - Sugiere filtros específicos para mitigar ruido
           - Recomienda parámetros de procesamiento
           - Evalúa factibilidad de mejoras operativas
        
        FORMATO DE SALIDA:
        ## 🔍 FUENTES DE RUIDO IDENTIFICADAS
        - **Tipo principal**: [Cultural/Instrumental/Ambiental]
        - **Frecuencias afectadas**: [rango en Hz]
        - **Patrón temporal**: [Continuo/Periódico/Episódico]
        - **Intensidad relativa**: [Alta/Media/Baja]
        
        ## 📊 ANÁLISIS ESPECTRAL DETALLADO
        - **0.1-1 Hz**: [observaciones microseismos]
        - **1-10 Hz**: [banda sísmica principal]  
        - **10-50 Hz**: [ruido cultural típico]
        - **>50 Hz**: [ruido instrumental/aliasing]
        
        ## 🔧 RECOMENDACIONES DE MITIGACIÓN
        1. **Filtrado inmediato**: [parámetros específicos]
        2. **Mejoras operativas**: [acciones en sitio]
        3. **Monitoreo continuo**: [parámetros a vigilar]
        
        ## 📈 IMPACTO EN DETECCIÓN SÍSMICA
        **[Bajo/Medio/Alto]** - [Descripción del impacto en capacidad de detección]
        
        Responde SIEMPRE en español con terminología técnica precisa.
```

### 🔗 **Integrar el Nuevo Agente**

1. **Mapeo en el código** (archivo `src/ai_agent/seismic_interpreter.py`):

```python
def _map_agent_to_task_name(agent_key: str) -> str:
    """Map new agent keys to expected task names for backward compatibility."""
    mapping = {
        "waveform_analyzer": "waveform_analysis",
        "histogram_analyzer": "histogram_analysis", 
        "earthquake_correlator": "earthquake_search",
        "report_synthesizer": "report_generation",
        "quality_assurance": "quality_assurance",
        "noise_analyzer": "noise_analysis",  # ← Agregar nuevo agente
    }
    return mapping.get(agent_key, agent_key)
```

2. **Función de uso**:

```python
def run_noise_analysis(
    agents: Dict[str, "AgnoAgent"],
    *,
    waveform_data: str,
    spectrogram_data: str,
    context: Dict[str, Any],
) -> Optional[str]:
    """Run noise analysis using specialized agent."""
    
    agent = agents.get("noise_analysis")
    if agent is None:
        LOGGER.warning("Noise analysis agent not configured.")
        return None
    
    prompt = agent.prompts["analysis"].format(
        context=context,
        waveform_data=waveform_data,
        spectrogram_data=spectrogram_data
    )
    
    start_time = time.time()
    try:
        result = agent.run(prompt)
        duration = time.time() - start_time
        LOGGER.info(f"Noise analysis completed in {duration:.2f}s")
        return getattr(result, "content", None)
    except Exception as exc:
        LOGGER.error("Noise analysis failed: %s", exc)
        return None
```

---

## 🔧 Configuración Avanzada

### 🌐 **Configuración Multi-Idioma**

```yaml
global:
  language: "spanish"  # Principal
  fallback_languages: ["english", "portuguese"]
  
agents:
  waveform_analyzer:
    prompts:
      system_es: |
        Eres un sismólogo experto especializado en...
      system_en: |
        You are an expert seismologist specialized in...
      system_pt: |
        Você é um sismólogo especialista em...
```

### ⚡ **Configuración de Rendimiento**

```yaml
global:
  behavior:
    max_retries: 3
    timeout_seconds: 60
    enable_caching: true
    log_level: "info"
    
models:
  performance:
    concurrent_agents: 2      # Agentes en paralelo
    max_queue_size: 10       # Cola de solicitudes
    adaptive_timeouts: true   # Timeouts adaptativos
    
cache:
  enable_agent_cache: true
  max_entries: 50           # Más cache para mejor rendimiento
  cache_ttl_hours: 48       # Cache por 48 horas
```

### 🎯 **Configuración por Contexto**

```yaml
agents:
  waveform_analyzer:
    contexts:
      emergency:
        model: "anthropic/claude-3.5-sonnet"  # Modelo premium
        parameters:
          confidence_threshold: 0.6           # Menos conservador
          response_time_priority: "fast"      # Prioridad velocidad
      routine:
        model: "deepseek/deepseek-chat-v3.1:free"  # Modelo gratuito
        parameters:
          confidence_threshold: 0.8              # Más conservador
          response_time_priority: "accuracy"     # Prioridad precisión
```

---

## 🧪 Testing y Validación

### ✅ **Test Básico de Configuración**

```bash
# 1. Validar carga de agentes
cd /path/to/seismic-aiagent
python -c "
from src.ai_agent.seismic_interpreter import load_agent_suite
agents = load_agent_suite()
print(f'✅ Agentes cargados: {list(agents.keys())}')
"

# 2. Test específico por agente
python -c "
from src.ai_agent.seismic_interpreter import load_agent_suite
agents = load_agent_suite()
agent = agents.get('waveform_analysis')
if agent:
    print(f'✅ Agente waveform: {agent.name}')
    print(f'✅ Modelo: {agent.model.id}')
else:
    print('❌ Error: Agente waveform no encontrado')
"
```

### 🔍 **Test de Prompt**

```python
# test_custom_agent.py
from src.ai_agent.seismic_interpreter import load_agent_suite

def test_custom_prompt():
    agents = load_agent_suite()
    waveform_agent = agents.get("waveform_analysis")
    
    test_prompt = """
    TRAZA SÍSMICA DE PRUEBA:
    - Estación: TEST-01
    - Canal: BHZ
    - Duración: 300 segundos
    - Sampling rate: 100 Hz
    - Evento detectado: 2025-09-29 14:30:00 UTC
    
    Señal muestra amplitud máxima de 1500 counts a los 45 segundos,
    seguida de segunda llegada mayor a los 52 segundos.
    Ruido de fondo estable en ~50 counts.
    """
    
    try:
        result = waveform_agent.run(test_prompt)
        print("✅ Test exitoso:")
        print(result.content)
    except Exception as e:
        print(f"❌ Error en test: {e}")

if __name__ == "__main__":
    test_custom_prompt()
```

### 📊 **Validación de Salida**

```python
def validate_agent_output(output: str, agent_type: str) -> bool:
    """Validar que la salida del agente cumple formato esperado."""
    
    required_sections = {
        "waveform_analysis": [
            "## 🔬 ANÁLISIS TÉCNICO",
            "## 💡 INTERPRETACIÓN",
            "## 📊 CONFIANZA"
        ],
        "histogram_analysis": [
            "## 📊 ANÁLISIS TÉCNICO",
            "## 🔍 INTERPRETACIÓN",
            "## ⚠️ ALERTAS"
        ]
    }
    
    sections = required_sections.get(agent_type, [])
    
    for section in sections:
        if section not in output:
            print(f"❌ Sección faltante: {section}")
            return False
    
    print("✅ Formato de salida válido")
    return True
```

---

## 🚀 Mejores Prácticas

### 📝 **1. Prompts Efectivos**

**✅ HACER:**
```yaml
prompts:
  system: |
    Eres un sismólogo experto con 15+ años de experiencia en [ESPECÍFICO].
    
    Tu especialización ESPECÍFICA incluye:
    - [Skill específico 1 con contexto]
    - [Skill específico 2 con contexto]
    - [Skill específico 3 con contexto]
    
    IMPORTANTE: [Restricción o comportamiento clave]
```

**❌ EVITAR:**
```yaml
prompts:
  system: |
    Eres un experto que analiza datos sísmicos.
    Haz tu mejor esfuerzo en responder preguntas.
```

### 🎯 **2. Estructura de Salida Consistente**

**✅ HACER:**
```yaml
prompts:
  analysis: |
    FORMATO DE RESPUESTA OBLIGATORIO:
    
    ## 🔬 [SECCIÓN TÉCNICA]
    - **Campo 1**: [valor] - [justificación]
    - **Campo 2**: [valor] - [justificación]
    
    ## 💡 [SECCIÓN OPERATIVA]
    [Explicación clara en 2-3 oraciones]
    
    ## 📊 NIVEL DE CONFIANZA
    **[Alto/Medio/Bajo] - [XX%]** - [Justificación específica]
```

### ⚡ **3. Optimización de Modelos**

**Por Tipo de Tarea:**
- **Análisis crítico**: `anthropic/claude-3.5-sonnet`
- **Análisis rutinario**: `deepseek/deepseek-chat-v3.1:free`
- **Generación código**: `deepseek/deepseek-coder:free`
- **Búsquedas**: `nvidia/nemotron-nano-9b-v2:free`

### 🛡️ **4. Manejo de Errores**

```yaml
agents:
  waveform_analyzer:
    fallback_models: 
      - "nvidia/nemotron-nano-9b-v2:free"  # Si falla primary
      - "google/gemma-3-27b-it:free"       # Si falla secondary
    
    parameters:
      max_retries: 3
      retry_delay_seconds: 2
      graceful_degradation: true  # Continúa con menos funcionalidad
```

### 📈 **5. Monitoreo y Logging**

```yaml
monitoring:
  enabled: true
  log_level: "info"
  emit_on:
    - agent_created
    - agent_run
    - agent_run_failed
    - agent_cache_hit
  
  alerts:
    high_error_rate_threshold: 0.3     # 30% errores
    slow_response_threshold: 60        # >60 segundos
```

---

## ❓ Troubleshooting

### 🚨 **Problemas Comunes**

#### **Error: "No agents were successfully created"**

**Síntomas:**
```
ERROR: No agents were successfully created. Failed agents: [('waveform_analyzer', 'Agent creation returned None')]
```

**Soluciones:**
1. **Verificar sintaxis YAML:**
   ```bash
   python -c "
   import yaml
   with open('config/agents_config.yaml') as f:
       yaml.safe_load(f)
   print('✅ YAML válido')
   "
   ```

2. **Verificar modelo disponible:**
   ```yaml
   agents:
     waveform_analyzer:
       model: "deepseek/deepseek-chat-v3.1:free"  # ← Verificar ID correcto
   ```

3. **Verificar variables de entorno:**
   ```bash
   echo $OPENROUTER_API_KEY  # Si usas modelos premium
   ```

#### **Error: "Unknown tool: [tool_name]"**

**Síntomas:**
```
WARNING: Unknown tool: phase_detection
```

**Solución:**
```python
# En src/ai_agent/seismic_interpreter.py
def _map_capabilities_to_tools(capabilities: List[str]) -> List[str]:
    capability_to_tool_map = {
        "phase_detection": "usgs_search",        # ← Mapear a tool real
        "earthquake_search": "usgs_search",
        "web_search": "duckduckgo_search",
        # Agregar más según necesidad
    }
```

#### **Error: "Agent response too slow"**

**Soluciones:**
1. **Usar modelo más rápido:**
   ```yaml
   agents:
     waveform_analyzer:
       model: "nvidia/nemotron-nano-9b-v2:free"  # Más rápido
   ```

2. **Reducir contexto:**
   ```yaml
   parameters:
     max_context_length: 4000  # Reducir de 8000
     enable_streaming: true    # Para respuestas incrementales
   ```

#### **Error: "Inconsistent agent outputs"**

**Síntomas:** Los agentes dan respuestas contradictorias.

**Soluciones:**
1. **Agregar validación cruzada:**
   ```yaml
   agents:
     quality_assurance:
       parameters:
         consistency_checking: true
         flag_contradictions: true
   ```

2. **Mejorar prompts para consistencia:**
   ```yaml
   prompts:
     system: |
       IMPORTANTE: Mantén consistencia factual con otros análisis.
       Si detectas contradicción, explícala claramente.
   ```

### 🔧 **Herramientas de Diagnóstico**

#### **Script de Diagnóstico Completo**

```python
# diagnostic_tool.py
import sys
import traceback
from src.ai_agent.seismic_interpreter import load_agent_suite

def run_diagnostics():
    """Ejecuta diagnósticos completos del sistema de agentes."""
    
    print("🔍 Iniciando diagnósticos del sistema de agentes...\n")
    
    # 1. Test de carga
    try:
        agents = load_agent_suite()
        print(f"✅ Agentes cargados exitosamente: {len(agents)}")
        for name, agent in agents.items():
            print(f"  - {name}: {agent.name} ({agent.model.id})")
    except Exception as e:
        print(f"❌ Error cargando agentes: {e}")
        traceback.print_exc()
        return
    
    print()
    
    # 2. Test de conectividad
    test_agent = agents.get("waveform_analysis")
    if test_agent:
        try:
            test_prompt = "Test de conectividad. Responde: OK"
            result = test_agent.run(test_prompt)
            print("✅ Test de conectividad exitoso")
        except Exception as e:
            print(f"❌ Error de conectividad: {e}")
    
    # 3. Test de formato
    print("\n🧪 Test de formatos de salida:")
    test_cases = {
        "waveform_analysis": "Analiza señal sísmica de prueba",
        "histogram_analysis": "Analiza datos de telemetría de prueba"
    }
    
    for agent_name, test_prompt in test_cases.items():
        agent = agents.get(agent_name)
        if agent:
            try:
                result = agent.run(test_prompt)
                print(f"✅ {agent_name}: Formato correcto")
            except Exception as e:
                print(f"❌ {agent_name}: Error - {e}")
    
    print("\n🎯 Diagnósticos completados.")

if __name__ == "__main__":
    run_diagnostics()
```

### 📋 **Checklist de Validación**

Antes de hacer cambios en producción:

- [ ] ✅ YAML sintácticamente correcto
- [ ] ✅ Modelos especificados están disponibles  
- [ ] ✅ Prompts incluyen instrucciones específicas
- [ ] ✅ Formato de salida está definido
- [ ] ✅ Fallback models configurados
- [ ] ✅ Test básico de conectividad pasa
- [ ] ✅ Test de formato de salida pasa
- [ ] ✅ Logging habilitado para debugging
- [ ] ✅ Backup de configuración anterior guardado

---

## 📚 **Recursos Adicionales**

### 🔗 **Enlaces Útiles**
- **[Agno Documentation](https://docs.agno.com/)** - Framework IA subyacente
- **[OpenRouter Models](https://openrouter.ai/models)** - Catálogo modelos disponibles
- **[Prompt Engineering Guide](https://www.promptingguide.ai/)** - Mejores prácticas prompts

### 📁 **Archivos de Referencia**
- `config/agents_config.yaml` - Configuración principal
- `src/ai_agent/seismic_interpreter.py` - Lógica de agentes
- `docs/TECHNICAL_DOCS.md` - Documentación técnica
- `docs/USER_GUIDE.md` - Guía de usuario

### 🆘 **Soporte**
- **GitHub Issues**: Reportar problemas de configuración
- **Discussions**: Preguntas sobre personalización
- **Email**: Soporte técnico directo

---

**🤖 Guía de Modificación de Agentes - Versión 2.0 (Septiembre 2025)**
*Personaliza el comportamiento de tu sistema IA sísmico con precisión quirúrgica*
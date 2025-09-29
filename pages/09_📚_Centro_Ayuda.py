"""
📚 Página de Ayuda Integral - Seismic AIagent
Centro completo de documentación y soporte para usuarios
"""

import streamlit as st
import sys
import os

# Agregar el directorio src al path para importaciones
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from streamlit_utils.help_system import help_system

# Configuración de página
st.set_page_config(
    page_title="📚 Centro de Ayuda",
    page_icon="🆘",
    layout="wide"
)

def main():
    """Página principal de ayuda"""
    
    # Header
    st.title("📚 Centro de Ayuda - Seismic AIagent")
    st.markdown("**Tu guía completa para análisis sísmico con IA**")
    
    # Tabs principales
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "🚀 Inicio Rápido", 
        "📖 Guías por Página", 
        "🔧 Configuración", 
        "❓ FAQ", 
        "📞 Soporte"
    ])
    
    with tab1:
        show_quick_start()
    
    with tab2:
        show_page_guides()
    
    with tab3:
        show_configuration_guide()
        
    with tab4:
        show_faq()
        
    with tab5:
        show_support()

def show_quick_start():
    """Guía de inicio rápido"""
    st.header("🚀 Inicio Rápido en 5 Pasos")
    
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.markdown("""
        ### 📋 Lista de Verificación
        
        ✅ **Paso 1**: Cargar datos  
        ✅ **Paso 2**: Configurar filtros  
        ✅ **Paso 3**: Visualizar ondas  
        ✅ **Paso 4**: Análisis IA  
        ✅ **Paso 5**: Interpretar resultados
        """)
    
    with col2:
        st.markdown("""
        ### 📊 Tutorial Interactivo
        
        **1. Carga de Datos (📁 Uploader)**
        - Arrastra archivos .mseed, .sac o .seg2
        - Verifica metadatos en la tabla
        - Configura filtros globales
        
        **2. Análisis de Ondas (📊 Waveform Viewer)**  
        - Selecciona archivo cargado
        - Ajusta filtro pasa-banda (ej: 2-15 Hz)
        - Ingresa distancia epicentral para ML-WA
        - Ejecuta "🤖 Analizar con IA"
        
        **3. Análisis Espectral (🔍 Spectrum Analysis)**
        - Elige tipo: Espectrograma, FFT o PSD
        - Configura parámetros específicos
        - Obtén interpretación IA especializada
        
        **4. Análisis Integral (🧩 Equipo IA)**
        - Configura contexto completo
        - Ejecuta análisis multi-agente
        - Revisa síntesis coordinada
        """)
    
    # Video tutorial (placeholder)
    st.markdown("---")
    st.subheader("🎬 Video Tutorial")
    st.info("🎥 **Próximamente**: Video tutorial paso a paso disponible en el canal de YouTube del proyecto")
    
    # Datos de ejemplo
    st.markdown("---")
    st.subheader("📂 Datos de Ejemplo")
    st.markdown("""
    **¿No tienes datos sísmicos?** Descarga nuestros ejemplos:
    - 🌊 **Microsismo Local**: AC-1-SUR evento ML 2.1
    - 🌍 **Evento Regional**: Temblor M4.5 Costa Rica  
    - 📡 **Telemetría**: Una semana de datos operativos
    """)
    
    if st.button("📥 Descargar Datos de Ejemplo"):
        st.info("Funcionalidad en desarrollo - contacta el equipo para datos de prueba")

def show_page_guides():
    """Guías detalladas por página"""
    st.header("📖 Guías Detalladas por Página")
    
    # Selector de página
    page_options = {
        "📁 Uploader": "uploader",
        "📊 Waveform Viewer": "waveform", 
        "🔍 Spectrum Analysis": "spectrum",
        "📈 Histogramas Gecko": "histograms",
        "🌍 Location 1D": "location",
        "🤖 AI Interpreter": "ai_analysis",
        "🧩 Equipo IA": "ai_analysis"
    }
    
    selected_page = st.selectbox(
        "Selecciona la página para ver ayuda detallada:",
        list(page_options.keys())
    )
    
    if selected_page:
        page_key = page_options[selected_page]
        help_system.show_contextual_help(page_key, expanded=True)

def show_configuration_guide():
    """Guía de configuración avanzada"""
    st.header("🔧 Configuración Avanzada")
    
    tab1, tab2, tab3 = st.tabs(["⚙️ Parámetros", "🤖 IA", "🎨 Interface"])
    
    with tab1:
        st.subheader("⚙️ Configuración de Parámetros Sísmicos")
        
        st.markdown("""
        ### 🌊 Filtros Digitales
        
        | Tipo Evento | Filtro Recomendado | Justificación |
        |-------------|-------------------|---------------|
        | Local < 50km | 2-15 Hz | Máxima energía en altas frecuencias |
        | Regional 50-500km | 1-10 Hz | Balance entre señal y ruido |
        | Teleseismo > 1000km | 0.5-5 Hz | Atenuación de altas frecuencias |
        | Ruido sísmico | 0.1-1 Hz | Microseismos oceánicos |
        | Tremor volcánico | 0.5-5 Hz | Señales de larga duración |
        """)
        
        st.markdown("""
        ### 🎯 Picking Automático (STA/LTA)
        
        **Parámetros por Tipo de Red:**
        
        **Red Local Densa:**
        - STA: 0.5 segundos
        - LTA: 30 segundos  
        - Trigger ON: 3.5
        - Trigger OFF: 1.0
        
        **Red Regional:**
        - STA: 1.0 segundos
        - LTA: 60 segundos
        - Trigger ON: 2.5
        - Trigger OFF: 1.5
        
        **Red de Banda Ancha:**
        - STA: 2.0 segundos
        - LTA: 120 segundos
        - Trigger ON: 2.0  
        - Trigger OFF: 1.5
        """)
    
    with tab2:
        st.subheader("🤖 Configuración del Sistema IA")
        
        st.markdown("""
        ### 🎛️ Modelos Disponibles
        
        **Gratuitos (Recomendados):**
        - `deepseek/deepseek-chat-v3.1:free` - Excelente para análisis técnico
        - `nvidia/nemotron-nano-9b-v2:free` - Rápido y eficiente
        - `ollama/llama3.2` - Ejecución local (requiere instalación)
        
        **Premium (Mayor Capacidad):**
        - `gpt-4o-mini` - Análisis profundo y detallado
        - `claude-3.5-sonnet` - Excelente razonamiento científico
        - `gemini-1.5-flash` - Multimodal con gráficos
        """)
        
        st.markdown("""
        ### ⚡ Optimización de Rendimiento
        
        **Para Análisis Rápidos:**
        - Usar modelos free más pequeños
        - Limitar contexto a datos esenciales
        - Cache activado para respuestas similares
        
        **Para Análisis Profundos:**  
        - Modelos premium con más parámetros
        - Incluir contexto completo
        - Análisis de equipo coordinado
        """)
        
        st.code("""
        # Configuración en config/agno_config.yaml
        seismic_interpreter:
          default_model:
            provider: "openrouter"
            id: "deepseek/deepseek-chat-v3.1:free"
          
          task_models:
            waveform_analysis:
              preferred: "deepseek/deepseek-chat-v3.1:free"
              reasoning_mode: "hybrid"
        """, language="yaml")
    
    with tab3:
        st.subheader("🎨 Personalización de Interface")
        
        st.markdown("""
        ### 🎨 Temas y Colores
        
        La aplicación usa un tema científico optimizado:
        - **Fondo oscuro**: Reduce fatiga visual para análisis largos
        - **Colores funcionales**: Azul/naranja para máximo contraste
        - **Gráficos interactivos**: Plotly con controles integrados
        """)
        
        st.markdown("""
        ### 📱 Layout Responsivo
        
        **Diseño Optimizado:**
        - Controles horizontales para pantallas anchas
        - Paneles colapsables para móviles  
        - Sidebar fija con navegación rápida
        - Tooltips contextuales en parámetros
        """)

def show_faq():
    """Preguntas frecuentes"""
    st.header("❓ Preguntas Frecuentes (FAQ)")
    
    faq_categories = {
        "🔧 Técnicas": [
            {
                "q": "¿Qué formatos de archivo acepta?",
                "a": "Acepta .mseed (recomendado), .sac y .seg2. El formato .mseed es estándar internacional para datos sísmicos."
            },
            {
                "q": "¿Por qué mis archivos no cargan?", 
                "a": "Verifica: 1) Formato correcto, 2) Tamaño <50MB, 3) Archivo no corrupto. Intenta con otro archivo para confirmar."
            },
            {
                "q": "¿Cómo interpretar la magnitud ML-WA?",
                "a": "ML es magnitud local Wood-Anderson. ML<2=microsismo, ML 2-4=evento menor, ML>4=evento significativo. Calidad A/B=confiable, C/D=revisar."
            },
            {
                "q": "¿Qué precisión tiene la localización?",
                "a": "Depende de la red: red local densa ±1-2km, red dispersa ±5-10km. Limitado por modelo 1D simple."
            }
        ],
        
        "🤖 Sistema IA": [
            {
                "q": "¿Qué tan confiables son los análisis IA?",
                "a": "Los análisis IA son herramientas de apoyo, no reemplazan criterio experto. Equipo coordinado tiene mayor confiabilidad por validación cruzada."
            },
            {
                "q": "¿Por qué el análisis IA demora/falla?",
                "a": "Depende de: 1) Conexión internet, 2) Carga de servidores, 3) Complejidad datos. Reintentar en 1-2 minutos usualmente resuelve."
            },
            {
                "q": "¿Funciona sin internet?",
                "a": "Análisis sísmicos básicos sí (filtros, picking, magnitud). IA requiere internet. Próximamente: modo offline con Ollama local."
            },
            {
                "q": "¿Cuál es la diferencia entre análisis individual y equipo?",
                "a": "Individual: enfoque específico, 10-30s. Equipo: análisis integral con validación cruzada, 1-3min, mayor confiabilidad."
            }
        ],
        
        "💡 Uso": [
            {
                "q": "¿Qué filtros usar para eventos locales?", 
                "a": "Pasa-banda 2-15 Hz para microsismos locales. 1-10 Hz para regionales. 0.5-5 Hz para teleseismos."
            },
            {
                "q": "¿Cómo mejorar la detección de fases P/S?",
                "a": "Ajusta STA/LTA: reduce trigger para eventos débiles, aumenta para reducir falsos. STA 0.5-2s, LTA 30-120s según tipo evento."
            },
            {
                "q": "¿Cuántas estaciones necesito para localización?",
                "a": "Mínimo 3, recomendado 4+ con buena geometría (no colineales). Más estaciones = mejor precisión y confiabilidad."
            },
            {
                "q": "¿Qué análisis espectral usar?",
                "a": "Espectrograma: evolución temporal. FFT: espectro instantáneo. PSD: análisis estadístico de ruido. Depende del objetivo."
            }
        ]
    }
    
    for category, questions in faq_categories.items():
        st.subheader(category)
        for item in questions:
            with st.expander(item["q"]):
                st.write(item["a"])

def show_support():
    """Información de soporte y contacto"""
    st.header("📞 Soporte y Contacto")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("🆘 Obtener Ayuda")
        
        st.markdown("""
        ### 📋 Antes de Contactar
        
        1. **Consulta esta ayuda** y la documentación
        2. **Revisa Issues en GitHub** - tu problema puede estar resuelto
        3. **Prueba con datos de ejemplo** para aislar el problema
        4. **Recopila información**:
           - Versión de la aplicación
           - Navegador y sistema operativo  
           - Pasos para reproducir el problema
           - Mensajes de error exactos
        """)
        
        st.markdown("""
        ### 🤝 Canales de Soporte
        
        **🔴 Urgente - Problemas Críticos:**
        - GitHub Issues: reportar bugs y errores
        - Tag: `bug`, `critical`
        
        **🟡 Normal - Preguntas y Mejoras:**
        - GitHub Discussions: preguntas generales
        - Tag: `question`, `enhancement`
        
        **🟢 Informal - Comunidad:**
        - Foro de usuarios: intercambio experiencias
        - Chat Discord: conversaciones en tiempo real
        """)
    
    with col2:
        st.subheader("📚 Recursos Adicionales")
        
        st.markdown("""
        ### 📖 Documentación
        
        - **[README.md](README.md)**: Visión general del proyecto
        - **[Guía Usuario](docs/USER_GUIDE.md)**: Manual paso a paso
        - **[Docs Técnicos](docs/TECHNICAL_DOCS.md)**: Arquitectura y APIs
        - **[Roadmap](docs/roadmap.md)**: Futuras funcionalidades
        """)
        
        st.markdown("""
        ### 🌟 Contribuir
        
        **¿Quieres ayudar al proyecto?**
        
        - **💻 Código**: Pull requests bienvenidos
        - **📝 Documentación**: Mejoras y traducciones  
        - **🐛 Testing**: Reporta bugs y casos edge
        - **💡 Ideas**: Sugiere nuevas funcionalidades
        - **🎓 Educación**: Tutoriales y ejemplos
        """)
        
        st.markdown("""
        ### 🏷️ Información del Proyecto
        
        - **Versión**: 2.0 (Septiembre 2025)
        - **Licencia**: MIT License
        - **Lenguaje**: Python 3.9+
        - **Framework**: Streamlit + Agno v2
        - **Mantenedor**: Equipo Seismic AIagent
        """)
    
    # Enlaces importantes
    st.markdown("---")
    st.subheader("🔗 Enlaces Importantes")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("🐙 GitHub Repository", help="Ver código fuente y reportar issues"):
            st.info("🔗 https://github.com/user/seismic-aiagent")
    
    with col2:
        if st.button("📧 Contacto Email", help="Soporte técnico directo"):  
            st.info("📧 support@seismic-aiagent.com")
    
    with col3:
        if st.button("💬 Comunidad Discord", help="Chat en tiempo real"):
            st.info("💬 discord.gg/seismic-aiagent")
    
    # Formulario de feedback
    st.markdown("---")
    st.subheader("📝 Enviar Feedback")
    
    with st.form("feedback_form"):
        feedback_type = st.selectbox(
            "Tipo de feedback:",
            ["🐛 Reporte de Bug", "💡 Sugerencia", "📖 Mejora Documentación", "⭐ Comentario General"]
        )
        
        feedback_text = st.text_area(
            "Tu feedback:",
            placeholder="Describe tu experiencia, problema o sugerencia...",
            height=100
        )
        
        email = st.text_input(
            "Email (opcional):", 
            placeholder="tu.email@ejemplo.com",
            help="Para seguimiento de tu feedback"
        )
        
        if st.form_submit_button("📤 Enviar Feedback"):
            if feedback_text:
                st.success("""
                ✅ **¡Gracias por tu feedback!** 
                
                Tu mensaje ha sido registrado y será revisado por el equipo.  
                Si proporcionaste email, te contactaremos si necesitamos más información.
                """)
            else:
                st.error("Por favor, describe tu feedback antes de enviar.")

if __name__ == "__main__":
    main()
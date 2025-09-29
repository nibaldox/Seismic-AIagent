"""
🆘 Sistema de Ayuda Integrado para Seismic AIagent
Proporciona ayuda contextual directamente en la aplicación Streamlit
"""

import streamlit as st
from typing import Dict, List

class HelpSystem:
    """Sistema de ayuda contextual integrado"""
    
    def __init__(self):
        self.help_content = self._load_help_content()
    
    def _load_help_content(self) -> Dict[str, Dict]:
        """Cargar contenido de ayuda estructurado"""
        return {
            "uploader": {
                "title": "📁 Carga de Datos",
                "quick_tips": [
                    "Arrastra archivos .mseed, .sac o .seg2",
                    "Máximo 50 MB por archivo",
                    "Revisa metadatos antes de analizar"
                ],
                "common_issues": {
                    "No carga archivo": "Verifica formato correcto y tamaño <50MB",
                    "Metadatos incorrectos": "El archivo puede estar corrupto",
                    "Carga lenta": "Archivos grandes demoran más"
                },
                "best_practices": [
                    "Usa nombres descriptivos para archivos",
                    "Elimina archivos no utilizados para mejorar rendimiento",
                    "Configura filtros globales antes de analizar"
                ]
            },
            
            "waveform": {
                "title": "📊 Análisis de Ondas Sísmicas",
                "quick_tips": [
                    "Filtro pasa-banda 2-15 Hz para eventos locales",
                    "Distancia epicentral requerida para ML-WA",
                    "Picking automático detecta fases P/S"
                ],
                "parameters": {
                    "Filtros": {
                        "Pasa-banda": "Elimina ruido manteniendo señal sísmica (ej: 1-10 Hz)",
                        "Pasa-alto": "Elimina deriva instrumental (>0.5 Hz)",
                        "Pasa-bajo": "Elimina ruido alta frecuencia (<25 Hz)"
                    },
                    "STA/LTA": {
                        "STA": "Ventana corta promedio (0.1-2.0 s)",
                        "LTA": "Ventana larga promedio (10-60 s)",
                        "Trigger ON": "Umbral detección (2-5)",
                        "Trigger OFF": "Umbral fin detección (1-2)"
                    },
                    "Magnitud ML-WA": {
                        "Distancia": "Distancia epicentral en km (requerido)",
                        "Profundidad": "Profundidad del evento en km (opcional)",
                        "Calidad": "A=excelente, B=buena, C=regular, D=pobre"
                    }
                },
                "interpretation": {
                    "ML < 2.0": "Microsismo, raramente sentido",
                    "ML 2.0-4.0": "Evento menor, posiblemente sentido",
                    "ML > 4.0": "Evento significativo",
                    "Calidad A/B": "Resultado confiable",
                    "Calidad C/D": "Resultado incierto, verificar parámetros"
                }
            },
            
            "spectrum": {
                "title": "🔍 Análisis Espectral",
                "quick_tips": [
                    "Espectrograma: evolución temporal de frecuencias",
                    "FFT: espectro instantáneo de toda la traza",
                    "PSD: densidad espectral de potencia (método Welch)"
                ],
                "analysis_types": {
                    "Espectrograma": {
                        "uso": "Ver cómo cambian las frecuencias en el tiempo",
                        "ventana": "1-10 segundos (eventos cortos)",
                        "solapamiento": "50-90% (mayor resolución)",
                        "casos": "Eventos largos, tremor volcánico, ruido sísmico"
                    },
                    "FFT": {
                        "uso": "Espectro de frecuencias de toda la señal",
                        "ventana": "Toda la traza o segmento específico", 
                        "aplicación": "Caracterización de eventos, análisis de ruido",
                        "limitaciones": "No muestra evolución temporal"
                    },
                    "PSD": {
                        "uso": "Densidad de potencia por frecuencia",
                        "método": "Welch (recomendado para ruido)",
                        "segmentos": "Con solapamiento para mayor estadística",
                        "unidades": "dB rel 1 (m/s)²/Hz"
                    }
                },
                "frequency_ranges": {
                    "0.01-0.1 Hz": "Ruido microsísmico, mareas terrestres",
                    "0.1-1 Hz": "Ruido microsísmico primario/secundario", 
                    "1-10 Hz": "Eventos sísmicos locales",
                    "10-50 Hz": "Eventos muy locales, ruido cultural",
                    ">50 Hz": "Ruido instrumental, aliasing"
                }
            },
            
            "histograms": {
                "title": "📈 Series Temporales",
                "quick_tips": [
                    "Visualiza hasta 3 variables simultáneamente",
                    "Remuestrea para suavizar datos",
                    "Suavizado elimina variaciones menores"
                ],
                "parameters": {
                    "Remuestreo": {
                        "1 min": "Datos de alta resolución temporal",
                        "5-15 min": "Monitoreo en tiempo real",  
                        "1 hora": "Tendencias diarias",
                        "1 día": "Patrones semanales/mensuales"
                    },
                    "Agregación": {
                        "Promedio": "Valor típico del período",
                        "Máximo": "Valor pico del período",
                        "Mínimo": "Valor mínimo del período", 
                        "Suma": "Acumulado del período"
                    },
                    "Suavizado": {
                        "Ventana 3": "Suavizado ligero",
                        "Ventana 6": "Suavizado moderado",
                        "Ventana 12": "Suavizado fuerte"
                    }
                },
                "use_cases": {
                    "Monitoreo tiempo real": "24h, remuestreo 5min, sin suavizado",
                    "Análisis semanal": "7 días, remuestreo 1h, suavizado 6h",
                    "Tendencias mensuales": "30 días, remuestreo 1día, suavizado 3días"
                }
            },
            
            "location": {
                "title": "🌍 Localización Sísmica",
                "quick_tips": [
                    "Mínimo 3 estaciones para localización",
                    "Más estaciones = mayor precisión",
                    "Modelo 1D simple: velocidad constante"
                ],
                "requirements": {
                    "Estaciones": "Mínimo 3, recomendado 4+ con buena geometría",
                    "Observaciones": "Tiempos P y/o S con precisión <0.1s",
                    "Modelo velocidad": "Vp ~6 km/s, Vs ~3.5 km/s (corteza típica)",
                    "Grilla búsqueda": "Rango ±50km, espaciado 1-2km"
                },
                "quality_indicators": {
                    "RMS < 0.3s": "Localización excelente",
                    "RMS 0.3-0.5s": "Localización buena", 
                    "RMS 0.5-1.0s": "Localización regular",
                    "RMS > 1.0s": "Localización pobre"
                },
                "limitations": [
                    "Modelo 1D: velocidad constante (simplificado)",
                    "Profundidad fija: superficie (z=0)",
                    "No considera topografía ni estructura lateral"
                ]
            },
            
            "ai_analysis": {
                "title": "🤖 Análisis con IA",
                "quick_tips": [
                    "Análisis individual: enfoque específico",
                    "Equipo coordinado: validación cruzada",
                    "Streaming: ve el análisis en tiempo real"
                ],
                "analysis_types": {
                    "Primario (Ondas)": {
                        "enfoque": "Formas de onda sísmicas",
                        "identifica": "Fases P/S, tipo fuente, calidad registro",
                        "tiempo": "10-30 segundos"
                    },
                    "Espectral": {
                        "enfoque": "Contenido en frecuencia", 
                        "identifica": "Frecuencias dominantes, ruido, respuesta",
                        "tiempo": "15-45 segundos"
                    },
                    "Telemetría": {
                        "enfoque": "Variables operativas",
                        "identifica": "Estado equipos, anomalías, tendencias", 
                        "tiempo": "20-60 segundos"
                    },
                    "Equipo Coordinado": {
                        "enfoque": "Análisis integral multi-fuente",
                        "proceso": "6 agentes especializados + síntesis",
                        "tiempo": "1-3 minutos"
                    }
                },
                "reliability": {
                    "Alta": "Convergencia de múltiples análisis",
                    "Media": "Análisis individual consistente",
                    "Baja": "Datos limitados o inconsistentes",
                    "Nota": "Siempre validar con criterio experto"
                }
            }
        }
    
    def show_contextual_help(self, page_key: str, expanded: bool = False):
        """Mostrar ayuda contextual para una página específica"""
        if page_key not in self.help_content:
            st.error(f"Ayuda no disponible para página: {page_key}")
            return
            
        help_data = self.help_content[page_key]
        
        with st.expander(f"🆘 Ayuda: {help_data['title']}", expanded=expanded):
            
            # Tips rápidos
            st.subheader("⚡ Tips Rápidos")
            for tip in help_data.get("quick_tips", []):
                st.write(f"• {tip}")
            
            # Parámetros (si existen)
            if "parameters" in help_data:
                st.subheader("⚙️ Parámetros")
                for param_group, params in help_data["parameters"].items():
                    st.write(f"**{param_group}:**")
                    for param, description in params.items():
                        st.write(f"  • **{param}**: {description}")
            
            # Tipos de análisis (si existen)  
            if "analysis_types" in help_data:
                st.subheader("📊 Tipos de Análisis")
                for analysis_type, details in help_data["analysis_types"].items():
                    with st.expander(f"{analysis_type}"):
                        for key, value in details.items():
                            if isinstance(value, list):
                                st.write(f"**{key.title()}:**")
                                for item in value:
                                    st.write(f"  • {item}")
                            else:
                                st.write(f"**{key.title()}:** {value}")
            
            # Casos de uso (si existen)
            if "use_cases" in help_data:
                st.subheader("🎯 Casos de Uso")
                for case, config in help_data["use_cases"].items():
                    st.write(f"**{case}:** {config}")
            
            # Rangos de frecuencia (para espectral)
            if "frequency_ranges" in help_data:
                st.subheader("🌊 Rangos de Frecuencia")
                for freq_range, description in help_data["frequency_ranges"].items():
                    st.write(f"**{freq_range}:** {description}")
            
            # Interpretación (para waveform)
            if "interpretation" in help_data:
                st.subheader("📖 Interpretación")
                for criteria, meaning in help_data["interpretation"].items():
                    st.write(f"**{criteria}:** {meaning}")
            
            # Problemas comunes
            if "common_issues" in help_data:
                st.subheader("⚠️ Problemas Comunes")
                for issue, solution in help_data["common_issues"].items():
                    st.write(f"**{issue}:** {solution}")
            
            # Mejores prácticas
            if "best_practices" in help_data:
                st.subheader("✅ Mejores Prácticas")
                for practice in help_data["best_practices"]:
                    st.write(f"• {practice}")
            
            # Requerimientos (para localización)
            if "requirements" in help_data:
                st.subheader("📋 Requerimientos")
                for req, description in help_data["requirements"].items():
                    st.write(f"**{req}:** {description}")
            
            # Indicadores de calidad
            if "quality_indicators" in help_data:
                st.subheader("📈 Indicadores de Calidad")
                for indicator, meaning in help_data["quality_indicators"].items():
                    st.write(f"**{indicator}:** {meaning}")
            
            # Limitaciones
            if "limitations" in help_data:
                st.subheader("⚠️ Limitaciones")
                for limitation in help_data["limitations"]:
                    st.write(f"• {limitation}")
            
            # Confiabilidad (para IA)
            if "reliability" in help_data:
                st.subheader("🎯 Confiabilidad")
                for level, description in help_data["reliability"].items():
                    st.write(f"**{level}:** {description}")
    
    def show_global_help(self):
        """Mostrar ayuda general de la aplicación"""
        st.title("🆘 Centro de Ayuda - Seismic AIagent")
        
        st.markdown("""
        ### 🎯 Inicio Rápido
        1. **📁 Uploader**: Carga archivos sísmicos (.mseed, .sac, .seg2)
        2. **📊 Waveform Viewer**: Analiza formas de onda con IA
        3. **🔍 Spectrum Analysis**: Análisis espectral especializado
        4. **📈 Histogramas**: Series temporales de telemetría
        5. **🌍 Location 1D**: Localización epicentral
        6. **🤖 AI Interpreter**: Análisis IA individual
        7. **🧩 Equipo IA**: Análisis coordinado multi-agente
        """)
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("📚 Documentación")
            st.markdown("""
            - [📖 Guía de Usuario](docs/USER_GUIDE.md)
            - [🔧 Documentación Técnica](docs/TECHNICAL_DOCS.md) 
            - [🗺️ Roadmap](docs/roadmap.md)
            - [📝 README](README.md)
            """)
        
        with col2:
            st.subheader("🆘 Soporte")
            st.markdown("""
            - **GitHub Issues**: Reportar problemas
            - **Discusiones**: Preguntas generales
            - **Email**: Soporte técnico
            - **Foro**: Comunidad de usuarios
            """)
        
        st.subheader("🔧 Configuración Recomendada")
        with st.expander("⚙️ Ver configuraciones por tipo de análisis"):
            st.markdown("""
            **Eventos Locales (< 100 km):**
            - Filtro: 2-15 Hz pasa-banda
            - STA/LTA: 0.5s / 30s
            - Picking: trigger 3.5
            
            **Eventos Regionales (100-1000 km):**
            - Filtro: 1-10 Hz pasa-banda  
            - STA/LTA: 1.0s / 60s
            - Picking: trigger 2.5
            
            **Teleseismos (> 1000 km):**
            - Filtro: 0.5-5 Hz pasa-banda
            - STA/LTA: 2.0s / 120s  
            - Picking: trigger 2.0
            """)
    
    def show_quick_help_sidebar(self):
        """Panel de ayuda rápida en la barra lateral"""
        with st.sidebar:
            st.markdown("---")
            st.subheader("🆘 Ayuda Rápida")
            
            if st.button("📖 Guía Completa"):
                st.session_state.show_global_help = True
            
            st.markdown("**🔗 Enlaces Útiles:**")
            st.markdown("- [GitHub Repository](https://github.com/user/seismic-aiagent)")
            st.markdown("- [Documentación](docs/)")
            st.markdown("- [Reportar Issue](https://github.com/user/seismic-aiagent/issues)")
            
            # Información de versión
            st.markdown("---")
            st.caption("**Seismic AIagent v2.0**")
            st.caption("Septiembre 2025")

# Instancia global del sistema de ayuda
help_system = HelpSystem()

def show_help(page_key: str, expanded: bool = False):
    """Función de conveniencia para mostrar ayuda contextual"""
    help_system.show_contextual_help(page_key, expanded)

def show_quick_help():
    """Función de conveniencia para ayuda rápida en sidebar"""
    help_system.show_quick_help_sidebar()

def show_global_help():
    """Función de conveniencia para ayuda global"""  
    help_system.show_global_help()
## Intérprete IA unificado

Desde esta versión, toda la interpretación basada en IA se realiza desde la página "🤖 AI Interpreter":

- Modo "Agente de Waveform": una interpretación rápida de las formas de onda visibles.
- Modo "Equipo IA (coordinado)": análisis multi‑agente con opciones avanzadas para incluir telemetría/histogramas.

La configuración de agentes ahora se define en `config/agents_config.yaml`.
Si trabajas con análisis espectral, asegúrate de incluir `spectrum_analyzer` para habilitar el agente `spectrum_analysis`.

# 👤 Guía de Usuario - Seismic AIagent

## 🎯 Inicio Rápido

### 🚀 Primera Sesión

1. **Abrir la aplicación** en su navegador
2. **Navegar a "📁 Uploader"** en la barra lateral
3. **Arrastrar archivos sísmicos** (.mseed, .sac, .seg2) al área de carga
4. **Verificar carga exitosa** - verá miniatura de metadatos
5. **¡Listo para analizar!** - use cualquier página de análisis

---

## 📊 Páginas de Análisis

### 1. 📁 **Uploader - Carga de Datos**

#### ✅ **Qué hace**
Permite cargar y gestionar archivos sísmicos de forma segura.

#### 🎯 **Cómo usar**

**Paso 1: Carga Simple**
- Arrastra archivos desde tu computador
- O usa el botón "Browse files"
- Formatos soportados: `.mseed`, `.sac`, `.seg2`

**Paso 2: Verificación**
- Revisa la tabla de archivos cargados
- Verifica metadatos: estación, canal, duración
- Elimina archivos incorrectos con ❌

**Paso 3: Configuración Global**
- Ajusta filtros por defecto
- Configura parámetros de análisis
- Estos se aplicarán a todas las páginas

#### ⚠️ **Limitaciones**
- Máximo 10 archivos simultáneos  
- Tamaño máximo: 50 MB por archivo
- Solo archivos sísmicos válidos

---

### 2. 📊 **Waveform Viewer - Análisis de Ondas**

#### ✅ **Qué hace** 
Visualiza formas de onda sísmicas con análisis automatizado de fases P/S y cálculo de magnitud.

#### 🎯 **Cómo usar**

**Configuración Básica (Panel Izquierdo)**
1. **Selecciona archivo** del menú desplegable
2. **Ajusta filtros**: 
   - Pasa-banda: frecuencias min/max (ej: 1-10 Hz)
   - Pasa-alto: elimina ruido de baja frecuencia  
   - Pasa-bajo: elimina ruido de alta frecuencia
3. **Picking automático**: 
   - ✅ Habilitar para detectar fases P/S
   - Ajusta sensibilidad (STA/LTA)

**Análisis de Magnitud**
4. **Configura estación**:
   - Distancia epicentral (km) - *requerido*
   - Profundidad del evento (km) - opcional
5. **Revisa resultado**:
   - ML-WA: Magnitud Local Wood-Anderson  
   - Calidad: A (excelente) a D (pobre)
   - Advertencias automáticas

**🤖 Interpretación IA (Panel Derecho)**
6. **Ejecuta análisis IA**:
   - Presiona "🤖 Analizar con IA"
   - Espera respuesta (10-30 segundos)
   - Lee interpretación experta automatizada

#### 📖 **Ejemplo Práctico**

```
🎯 Análisis de microsismo local:
1. Archivo: "AC-1-SUR_2025-05-02_14-30-00.mseed"  
2. Filtro pasa-banda: 2-15 Hz (óptimo para eventos locales)
3. Picking: sensibilidad 3.5 (estándar)
4. Distancia: 25 km (estimada de mapa)
5. Resultado: ML-WA = 1.8 ± 0.3 (Calidad B)
6. IA identifica: "Evento tectónico local, fases P/S claras"
```

#### ⚠️ **Advertencias Automáticas**
- 🟡 **Saturación**: Amplitud >95% del rango
- 🟠 **SNR bajo**: Relación señal/ruido <3
- 🔴 **Sin fases**: No se detectaron llegadas P/S  
- ⚪ **Respuesta**: Falta corrección instrumental

---

### 3. 🔍 **Spectrum Analysis - Análisis Espectral**

#### ✅ **Qué hace**
Analiza contenido en frecuencia con tres tipos de visualización y evaluación IA especializada.

#### 🎯 **Cómo usar**

**Configuración (Panel Horizontal Superior)**
1. **Selecciona archivo y canal** 
2. **Tipo de análisis**:
   - **Espectrograma**: evolución temporal de frecuencias
   - **FFT**: espectro de frecuencias instantáneo  
   - **PSD**: densidad espectral de potencia
3. **Ajusta parámetros**:
   - Ventana temporal (segundos)
   - Resolución de frecuencia
   - Tipo de ventana (Hann, Hamming, etc.)

**Configuración Específica por Análisis**

**📊 Espectrograma**
- Ventana deslizante: 1-10 segundos
- Solapamiento: 50-90%
- Escala: lineal o logarítmica

**⚡ FFT (Fast Fourier Transform)**  
- Toda la traza o segmento seleccionado
- Ventana de suavizado
- Normalización automática

**📈 PSD (Power Spectral Density)**
- Método: Welch (recomendado)
- Segmentos con solapamiento
- Unidades: dB rel 1 (m/s)²/Hz

**🤖 Interpretación IA (Panel Derecho)**
4. **Ejecuta análisis especializado**:
   - Botón "🔍 Analizar Espectro con IA"  
   - Contexto automático del tipo de análisis
   - Interpretación geofísica experta

#### 📖 **Casos de Uso Típicos**

**🌊 Análisis de Ruido Sísmico**
```
Configuración:
- Espectrograma, ventana 5s, solapamiento 75%
- Rango: 0.1-50 Hz (banda completa)
- IA identifica: picos de ruido cultural, microseismos
```

**🎯 Caracterización de Eventos**
```  
Configuración:
- FFT de evento completo 
- Ventana Hann, normalizado
- IA evalúa: tipo de fuente, distancia, profundidad
```

**📡 Monitoreo de Equipos**
```
Configuración:
- PSD método Welch, segmentos 60s
- IA detecta: problemas instrumentales, deriva
```

#### ⚠️ **Consideraciones**
- Ventanas muy pequeñas reducen resolución frecuencial
- Señales muy cortas limitan análisis PSD
- Saturación afecta todos los análisis espectrales

---

### 4. 📈 **Histogramas Gecko - Series Temporales**

#### ✅ **Qué hace**
Visualiza variables de telemetría en series temporales con análisis contextual IA.

#### 🎯 **Cómo usar**

**Configuración Compacta (Panel Horizontal)**
1. **Selecciona archivo CSV** de histogramas
2. **Rango temporal**:
   - Fecha inicio / fecha fin 
   - O últimas N horas/días
3. **Procesamiento**:
   - Remuestreo: 1min, 5min, 1h, etc.
   - Agregación: promedio, máximo, suma
   - Suavizado: ventana móvil opcional

**Visualización (3 Paneles)**
4. **Panel Superior**: Variable primaria (ej: temperatura)
5. **Panel Medio**: Variable secundaria (ej: voltaje)  
6. **Panel Inferior**: Variable terciaria (ej: corriente)
7. **Selecciona variables** desde menús desplegables

**🤖 Análisis IA Contextual**
8. **Botón "📈 Analizar Series"**:
   - Incluye configuración de visualización
   - Detecta patrones, anomalías, correlaciones
   - Evaluación estado operativo

#### 📖 **Ejemplo de Monitoreo de Estación**

```
📊 Análisis de estación AC-1-SUR (última semana):

Configuración:
- Remuestreo: 1 hora (suavizar datos)
- Variables: temperatura_cpu, voltaje_solar, corriente_carga
- Suavizado: ventana 6h (eliminar variaciones menores)

Resultado IA:
- Patrón diario normal en temperatura (15-35°C)  
- Caída voltaje solar 2025-05-03: posible sombra/nube
- Anomalía corriente: pico nocturno sugiere problema sistema
```

#### 🔧 **Configuraciones Recomendadas**

**Monitoreo Tiempo Real**
- Últimas 24 horas, remuestreo 5 min
- Sin suavizado (ver fluctuaciones)

**Análisis Semanal**  
- 7 días, remuestreo 1 hora  
- Suavizado 6h (tendencias)

**Revisión Mensual**
- 30 días, remuestreo 1 día
- Suavizado 3 días (patrones largos)

---

### 5. 🌍 **Location 1D - Localización**

#### ✅ **Qué hace**
Estima ubicación epicentral usando tiempos de llegada P/S de múltiples estaciones.

#### 🎯 **Cómo usar**

**Configuración de Estaciones**
1. **Define red de estaciones**:
   - Nombre, latitud, longitud, elevación
   - Mínimo 3 estaciones para localización
   - Más estaciones = mayor precisión

**Observaciones de Fases**
2. **Introduce tiempos observados**:
   - Llegadas P (primarias): tiempo absoluto
   - Llegadas S (secundarias): tiempo absoluto  
   - Calidad: peso en localización (0.1-1.0)

**Modelo de Velocidad**  
3. **Configura velocidades**:
   - Vp (ondas P): típicamente 6.0 km/s
   - Vs (ondas S): típicamente 3.5 km/s
   - Relación Vp/Vs: ~1.73 (corteza típica)

**Parámetros de Búsqueda**
4. **Define grilla de búsqueda**:
   - Rango X: -50 a +50 km (desde centro red)
   - Rango Y: -50 a +50 km  
   - Espaciado: 1-2 km (compromiso precisión/tiempo)

**🎯 Ejecutar Localización**
5. **Botón "🌍 Localizar Evento"**
6. **Revisar resultados**:
   - Coordenadas epicentrales
   - Tiempo origen estimado
   - RMS residual (calidad del ajuste)
   - Elipse de incertidumbre

#### 📖 **Ejemplo Red Local**

```
🎯 Red microsísmica Valle Central:

Estaciones:
- AC-1-SUR: 9.8°N, 84.1°W, 1200m
- AC-2-NORTE: 9.9°N, 84.0°W, 1400m  
- AC-3-ESTE: 9.85°N, 84.05°W, 1300m

Observaciones:
- P-AC-1: 2025-05-02T14:30:12.34
- P-AC-2: 2025-05-02T14:30:13.89
- S-AC-1: 2025-05-02T14:30:18.67

Resultado:
- Epicentro: 9.86°N, 84.03°W
- Tiempo origen: 14:30:10.12  
- RMS: 0.23s (buena calidad)
- Incertidumbre: ±1.2 km
```

#### ⚠️ **Limitaciones**
- Modelo 1D: asume velocidad constante (simplificado)
- Profundidad fija en superficie (z=0)  
- Requiere al menos 3 estaciones
- Precisión limitada por modelo de velocidad

---

### 6. 🤖 **AI Interpreter - Análisis Individual**

#### ✅ **Qué hace**
Análisis IA especializado de archivos individuales con contexto técnico detallado.

#### 🎯 **Cómo usar**

**Configuración del Contexto**
1. **Selecciona archivo** para análisis
2. **Tipo de análisis IA**:
   - **Análisis Primario**: enfoque en formas de onda
   - **Análisis Espectral**: enfoque en frecuencias
   - **Análisis de Telemetría**: enfoque en variables operativas

**Contexto Adicional**  
3. **Información opcional**:
   - Coordenadas estación (lat/lon)
   - Condiciones específicas (clima, mantenimiento, etc.)
   - Eventos conocidos en la región
   - Objetivo del análisis

**🧠 Ejecución**
4. **Botón según tipo de análisis**
5. **Streaming en tiempo real**: ve el análisis generándose
6. **Resultado**: interpretación experta completa

#### 📖 **Tipos de Análisis Disponibles**

**🌊 Análisis Primario (Ondas Sísmicas)**
- Identificación de fases P/S
- Caracterización de la fuente sísmica  
- Evaluación calidad de registro
- Estimación parámetros del evento

**🎵 Análisis Espectral (Frecuencias)**
- Contenido frecuencial dominante
- Identificación fuentes de ruido
- Evaluación respuesta instrumental
- Recomendaciones de filtrado

**📊 Análisis de Telemetría (Variables)**  
- Estado operativo de equipos
- Detección de anomalías
- Correlación con condiciones ambientales
- Recomendaciones de mantenimiento

---

### 7. 🧩 **Equipo IA - Análisis Coordinado**

#### ✅ **Qué hace**
Sistema multi-agente que coordina análisis integral combinando todos los datos disponibles.

#### 🎯 **Cómo usar**

**⚙️ Preparación del Contexto Integral**

**1. Telemetría/Histogramas**
- Selecciona archivo CSV de histogramas
- Rango temporal relevante
- Variables clave a considerar

**2. Formas de Onda**  
- Selecciona archivo sísmico principal
- Configuración de filtros
- Distancia epicentral estimada

**3. Catálogo Sísmico**
- Habilita búsqueda automática en USGS/EMSC
- Rango temporal: ±1 día del evento
- Radio de búsqueda: 50-200 km

**4. Localización (Opcional)**
- Red de estaciones configurada  
- Observaciones de fases P/S
- Modelo de velocidad regional

**🤖 Ejecución del Equipo**

**5. Análisis Coordinado**
- Botón "🧩 Análisis de Equipo"
- **Streaming multi-agente** en tiempo real:
  - 🔍 **Agente Telemetría**: evalúa estado operativo
  - 🌊 **Agente Ondas**: caracteriza señales sísmicas
  - 🌍 **Agente Catálogo**: contextualiza regionalmente  
  - 📍 **Agente Localización**: estima epicentro
  - 🎯 **QA Crítico**: valida consistencia entre análisis
  - 📋 **Síntesis Final**: integra hallazgos y recomendaciones

**📊 Resultado Integrado**
6. **Reporte coordinado** que incluye:
   - Caracterización completa del evento
   - Contexto regional y operativo  
   - Validación cruzada entre fuentes
   - Recomendaciones operativas específicas
   - Nivel de confianza del análisis

#### 📖 **Ejemplo de Análisis Coordinado**

```
🧩 Análisis de Equipo - Evento 2025-05-02 14:30 UTC

📊 Contexto configurado:
- Telemetría: AC-1-SUR última semana
- Ondas: evento ML 2.1 filtrado 2-15Hz  
- Catálogo: radio 100km, ±24h
- Localización: red 3 estaciones

🤖 Análisis multi-agente:

1️⃣ Agente Telemetría → "Estado nominal, sin anomalías pre-evento"
2️⃣ Agente Ondas → "Microsismo local, fases P/S claras, ML=2.1±0.2"  
3️⃣ Agente Catálogo → "Zona activa, 3 eventos similares última semana"
4️⃣ Agente Localización → "Epicentro 9.86°N 84.03°W, RMS=0.23s"
5️⃣ QA Crítico → "Consistencia alta entre análisis (95%)"

📋 Síntesis Final:
"Microsismo tectónico local bien caracterizado. Ubicación consistente 
con actividad regional reciente. Equipos operando normalmente. 
Recomendación: continuar monitoreo rutinario."
```

#### 🎯 **Ventajas del Análisis de Equipo**

- **Validación cruzada**: cada agente valida hallazgos de otros
- **Contexto integral**: considera todas las fuentes de información
- **Detección de inconsistencias**: identifica problemas de datos/instrumentos
- **Recomendaciones operativas**: sugerencias prácticas específicas
- **Confiabilidad**: nivel de certeza basado en convergencia de análisis

---

## 🔧 Configuración y Personalización

### ⚙️ **Configuración Global (Uploader)**

**Filtros por Defecto**
- Tipo: Pasa-banda recomendado
- Frecuencia baja: 1.0 Hz (elimina deriva instrumental)  
- Frecuencia alta: 25.0 Hz (mantiene rango sísmico útil)

**Picking Automático**
- STA (ventana corta): 0.5 segundos
- LTA (ventana larga): 30.0 segundos  
- Trigger ON: 3.5 (sensibilidad detección)
- Trigger OFF: 1.0 (fin de detección)

**Magnitud ML-WA**
- Distancia por defecto: 10 km
- Profundidad por defecto: 10 km
- Advertencias automáticas: habilitadas

### 🎨 **Personalización de Interface**

**Tema Visual**
- Modo oscuro por defecto
- Colores científicos (azul/naranja)
- Gráficos interactivos con Plotly

**Idioma y Formato**
- Interfaz en español
- Coordenadas: grados decimales  
- Tiempo: UTC (estándar sismológico)
- Unidades: métricas (km, m/s, Hz)

---

## ❓ Preguntas Frecuentes (FAQ)

### 🔧 **Problemas Técnicos**

**P: Los archivos no cargan correctamente**
- ✅ Verifica formato: `.mseed`, `.sac`, `.seg2` únicamente
- ✅ Tamaño máximo: 50 MB por archivo
- ✅ Archivos no corruptos o parcialmente descargados

**P: El análisis IA no responde**  
- ✅ Revisa conexión a internet
- ✅ Reintenta en unos minutos (límites de API)
- ✅ Verifica que hay datos cargados correctamente

**P: Los gráficos no se ven bien**
- ✅ Usa navegador moderno (Chrome, Firefox, Safari)
- ✅ JavaScript habilitado
- ✅ Actualiza la página si es necesario

### 📊 **Análisis Sísmico**

**P: ¿Qué filtros usar para eventos locales?**  
- ✅ Pasa-banda 2-15 Hz para microsismos
- ✅ Pasa-banda 1-10 Hz para eventos regionales
- ✅ Pasa-banda 0.5-5 Hz para eventos teleseismos

**P: ¿Cómo interpretar la magnitud ML-WA?**
- ✅ ML < 2.0: microsismo, raramente sentido
- ✅ ML 2.0-4.0: evento menor, posiblemente sentido  
- ✅ ML 4.0+: evento significativo, amplamente sentido
- ✅ Calidad A/B: confiable, C/D: incierta

**P: ¿Qué precisión tiene la localización 1D?**
- ✅ Red local densa: ±1-2 km típico
- ✅ Red dispersa: ±5-10 km
- ✅ Limitado por modelo de velocidad simple

### 🤖 **Sistema IA**

**P: ¿Qué tan confiables son los análisis IA?**
- ✅ Análisis individuales: guía y segunda opinión
- ✅ Equipo coordinado: mayor confiabilidad por validación cruzada
- ✅ Siempre revisar con criterio experto

**P: ¿Cuánto demora el análisis IA?**
- ✅ Análisis individual: 10-30 segundos
- ✅ Análisis de equipo: 1-3 minutos
- ✅ Depende de carga de servidores de IA

**P: ¿Funciona sin internet?**
- ❌ No, requiere conexión para modelos IA
- ✅ Análisis sísmicos básicos sí funcionan offline
- ✅ Carga de datos es completamente local

---

## 🆘 Solución de Problemas

### ⚠️ **Errores Comunes**

**"Error: No se pudo cargar el archivo"**
```
Soluciones:
1. Verificar formato de archivo correcto
2. Comprobar que no esté corrupto  
3. Reducir tamaño si >50MB
4. Intentar con otro archivo
```

**"Error: Análisis IA falló"**
```
Soluciones:
1. Verificar conexión a internet
2. Reintrentar después de 1 minuto
3. Seleccionar menos datos para analizar
4. Contactar soporte si persiste
```

**"Error: No se encontraron fases P/S"**
```  
Soluciones:
1. Ajustar sensibilidad STA/LTA
2. Cambiar filtros (probar 1-20 Hz)
3. Verificar calidad de la señal
4. El evento puede ser muy pequeño
```

### 🔍 **Diagnóstico Avanzado**

**Baja Calidad de Análisis**
- ✅ Revisar relación señal/ruido
- ✅ Verificar calibración instrumental
- ✅ Comprobar sincronización temporal
- ✅ Evaluar condiciones ambientales

**Resultados Inconsistentes**  
- ✅ Validar con múltiples archivos
- ✅ Comparar con catálogos oficiales
- ✅ Usar análisis de equipo para validación cruzada
- ✅ Revisar configuración de parámetros

---

## 📞 **Soporte y Contacto**

### 🏢 **Información del Proyecto**
- **Nombre**: Seismic AIagent
- **Versión**: 2.0 (Septiembre 2025)  
- **Licencia**: MIT License
- **Repositorio**: GitHub (ver README para enlaces)

### 🤝 **Obtener Ayuda**
1. **Documentación técnica**: `docs/TECHNICAL_DOCS.md`
2. **Issues en GitHub**: para reportar problemas
3. **Discusiones**: para preguntas generales
4. **Email**: contacto técnico (ver README)

### 📚 **Recursos Adicionales**
- **Roadmap**: `docs/roadmap.md` - próximas funcionalidades
- **Blog de desarrollo**: actualizaciones y novedades  
- **Tutoriales en video**: análisis paso a paso
- **Foro de usuarios**: intercambio de experiencias

---

**👤 Guía de Usuario - Versión 2.0 (Septiembre 2025)**
*Última actualización: Actualización integral con nueva documentación*
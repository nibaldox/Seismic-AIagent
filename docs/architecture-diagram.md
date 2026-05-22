# 🏗️ Diagrama de Arquitectura - SeismoAnalyzer Pro

## 📊 Flujo Principal de la Aplicación

```mermaid
graph TD
    %% Entrada de Usuario
    A[👤 Usuario] --> B[🌐 Streamlit App]
    
    %% Configuración Inicial
    B --> C{🔧 Configuración Inicial}
    C --> D[📁 Carga de Datos]
    C --> E[🤖 Selección de Modelo IA]
    C --> F[⚙️ Configuración UI]
    
    %% Sistema de Datos
    D --> G[📂 Data Uploader]
    G --> H[📊 Session State Manager]
    H --> I[🗄️ Stream Cache]
    
    %% Páginas de Análisis
    B --> J{📄 Navegación de Páginas}
    J --> K[📈 Waveform Viewer]
    J --> L[🔍 Spectrum Analysis]
    J --> M[📊 Histogramas]
    J --> N[🌍 Location 1D]
    J --> O[🤖 AI Interpreter]
    
    %% Procesamiento de Datos
    K --> P[📡 Signal Processing]
    L --> Q[🎛️ Spectrum Plots]
    M --> R[📈 Time Series Analysis]
    N --> S[📍 Geolocation Tools]
    
    %% Sistema de IA
    E --> T[⚡ Dynamic Config Generator]
    T --> U[🧠 Agent Suite Loader]
    U --> V{🎯 Agentes Especializados}
    
    V --> W[👁️ Waveform Analyzer]
    V --> X[📊 Spectrum Analyzer]
    V --> Y[📈 Histogram Analyzer]
    V --> Z[🌍 Earthquake Correlator]
    V --> AA[📝 Report Synthesizer]
    V --> BB[✅ Quality Assurance]
    
    %% Visualización
    P --> CC[📊 Plotly Charts]
    Q --> CC
    R --> CC
    S --> CC
    
    %% Análisis IA
    O --> DD[🤖 AI Analysis Pipeline]
    W --> DD
    X --> DD
    Y --> DD
    Z --> DD
    AA --> DD
    BB --> DD
    
    %% Salida
    CC --> EE[📱 UI Display]
    DD --> FF[📋 AI Reports]
    EE --> A
    FF --> A
    
    %% Estilos
    classDef userInterface fill:#e1f5fe
    classDef dataProcessing fill:#f3e5f5
    classDef aiSystem fill:#fff3e0
    classDef visualization fill:#e8f5e8
    classDef storage fill:#fce4ec
    
    class A,B,J,EE userInterface
    class D,G,H,I,P,Q,R,S storage
    class E,T,U,V,W,X,Y,Z,AA,BB,DD,FF aiSystem
    class K,L,M,N,O,CC visualization
    class C,F dataProcessing
```

## 🔄 Flujo de Datos Detallado

```mermaid
sequenceDiagram
    participant User as 👤 Usuario
    participant App as 🌐 Streamlit App
    participant Session as 🗄️ Session State
    participant Cache as 💾 Stream Cache
    participant Processing as ⚙️ Signal Processing
    participant AI as 🤖 AI Agents
    participant Viz as 📊 Visualization
    
    User->>App: 1. Acceso a la aplicación
    App->>Session: 2. Inicializar session state
    
    User->>App: 3. Seleccionar modelo IA
    App->>AI: 4. Crear configuración dinámica
    AI->>Session: 5. Cargar agentes en caché
    
    User->>App: 6. Subir datos sísmicos
    App->>Cache: 7. Almacenar en stream cache
    Cache->>Session: 8. Registrar metadatos
    
    User->>App: 9. Seleccionar análisis
    App->>Cache: 10. Recuperar datos
    Cache->>Processing: 11. Procesar señales
    Processing->>Viz: 12. Generar gráficos
    
    User->>App: 13. Solicitar análisis IA
    App->>AI: 14. Ejecutar agente específico
    AI->>App: 15. Retornar interpretación
    
    Viz->>User: 16. Mostrar resultados
    AI->>User: 17. Mostrar análisis IA
```

## 🏗️ Arquitectura de Componentes

```mermaid
graph LR
    %% Frontend Layer
    subgraph "🖥️ Frontend Layer"
        A[streamlit_app.py]
        B[pages/]
        C[assets/css/]
    end
    
    %% Business Logic Layer
    subgraph "🧠 Business Logic Layer"
        D[src/core/]
        E[src/ai_agent/]
        F[src/visualization/]
        G[src/streamlit_utils/]
    end
    
    %% Data Layer
    subgraph "📊 Data Layer"
        H[data/]
        I[config/]
        J[Session State]
        K[Stream Cache]
    end
    
    %% External Services
    subgraph "🌐 External Services"
        L[OpenRouter API]
        M[USGS Earthquake API]
        N[EMSC API]
    end
    
    %% Connections
    A --> D
    B --> D
    B --> F
    B --> G
    C --> A
    
    D --> J
    E --> L
    E --> M
    E --> N
    F --> J
    G --> J
    G --> K
    
    H --> K
    I --> E
    J --> K
```

## 🔧 Componentes Principales

### 📁 **Frontend (`streamlit_app.py` + `pages/`)**
- **streamlit_app.py**: Punto de entrada principal
- **pages/**: Páginas individuales de análisis
- **assets/css/**: Estilos y temas visuales

### 🧠 **Core Logic (`src/`)**
```mermaid
graph TD
    A[src/] --> B[core/]
    A --> C[ai_agent/]
    A --> D[visualization/]
    A --> E[streamlit_utils/]
    A --> F[utils/]
    
    B --> B1[data_reader.py]
    B --> B2[signal_processing.py]
    B --> B3[magnitude.py]
    B --> B4[picking.py]
    B --> B5[location/]
    
    C --> C1[seismic_interpreter.py]
    C --> C2[dynamic_config.py]
    C --> C3[artifacts.py]
    C --> C4[tools/]
    
    D --> D1[waveform_plots.py]
    D --> D2[spectrum_plots.py]
    
    E --> E1[session_state.py]
    E --> E2[appearance.py]
    E --> E3[file_uploader.py]
```

### 🤖 **Sistema de IA**
```mermaid
graph TD
    A[🤖 AI System] --> B[Dynamic Config]
    A --> C[Agent Suite]
    A --> D[Tools Integration]
    
    B --> B1[model selection]
    B --> B2[config generation]
    B --> B3[agent instantiation]
    
    C --> C1[waveform_analyzer]
    C --> C2[spectrum_analyzer]
    C --> C3[histogram_analyzer]
    C --> C4[earthquake_correlator]
    C --> C5[report_synthesizer]
    C --> C6[quality_assurance]
    
    D --> D1[geographic_tools]
    D --> D2[seismic_databases]
    D --> D3[web_search_tools]
```

## 📊 **Flujo de Session State**

```mermaid
stateDiagram-v2
    [*] --> InitSession: App Start
    
    InitSession --> ModelSelection: Load Models
    ModelSelection --> DataUpload: Select Model
    DataUpload --> Analysis: Upload Files
    
    state Analysis {
        [*] --> WaveformView
        WaveformView --> SpectrumAnalysis
        SpectrumAnalysis --> Histograms
        Histograms --> LocationAnalysis
        LocationAnalysis --> AIInterpretation
        AIInterpretation --> WaveformView
    }
    
    Analysis --> ModelChange: Change Model
    ModelChange --> ClearCache: Clear Agent Cache
    ClearCache --> ModelSelection: Reload Agents
    
    Analysis --> DataChange: New Data
    DataChange --> ClearStreamCache: Clear Stream Cache
    ClearStreamCache --> DataUpload: Reload Data
```

## 🔄 **Cache Management**

```mermaid
graph TD
    A[👤 User Action] --> B{Action Type?}
    
    B -->|Model Change| C[Clear Agent Cache]
    B -->|Data Upload| D[Clear Stream Cache]
    B -->|Page Navigation| E[Preserve Cache]
    
    C --> F[Regenerate Dynamic Config]
    F --> G[Reload AI Agents]
    G --> H[Update Session State]
    
    D --> I[Store in Stream Cache]
    I --> J[Update Metadata]
    J --> H
    
    E --> K[Access Cached Data]
    K --> H
    
    H --> L[🖥️ UI Update]
```

## 🛠️ **Tecnologías y Dependencias**

```mermaid
mindmap
  root((SeismoAnalyzer Pro))
    Frontend
      Streamlit
      Plotly
      HTML/CSS
    Backend
      Python 3.11+
      NumPy/SciPy
      ObsPy
      Pandas
    AI/ML
      Agno-AGI Framework
      OpenRouter API
      Multiple LLM Models
    Data Processing
      MiniSEED/SAC files
      Signal Processing
      Spectral Analysis
    External APIs
      USGS Earthquake Data
      EMSC Seismic Data
      Geographic Tools
```

Este diagrama muestra la arquitectura completa de la aplicación, desde la entrada del usuario hasta la generación de análisis IA, incluyendo el manejo de datos, caché, y la integración de múltiples componentes especializados.
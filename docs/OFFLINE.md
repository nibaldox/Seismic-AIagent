# Guía de Uso Offline — SeismoAnalyzer Pro

Guía para ejecutar SeismoAnalyzer Pro sin conexión a internet.

---

## Requisitos

- Python 3.10+ instalado localmente
- SeismoAnalyzer Pro (build PyInstaller) o imagen Docker
- Dataset de demo o archivos MiniSEED locales

---

## Instalación Offline (Docker)

```bash
# Importar imagen desde archivo
docker load < seismoanalyzer_production.tar

# Correr sin internet
docker compose up -d
```

---

## Instalación Desktop (PyInstaller)

1. Descomprimir `SeismoAnalyzerPro-linux.tar.gz`
2. `chmod +x SeismoAnalyzerPro`
3. `./SeismoAnalyzerPro`
4. Abrir http://localhost:8501

---

## Sin API Keys de IA

Para uso sin IA externa, configurar Ollama local:

```bash
# Instalar Ollama (requiere internet una vez)
curl -fsSL https://ollama.com/install.sh | sh

# Descargar modelo base (una vez, ~4GB)
ollama pull mistral

# Configurar en .env
OLLAMA_HOST=http://localhost:11434
```

**Modelos recomendados para uso offline:**

| Modelo | Uso | Tamaño |
|--------|-----|--------|
| `llama3.2` | Análisis general | ~2GB |
| `mistral` | Análisis espectral | ~4GB |
| `gemma2:2b` | Búsqueda de eventos | ~1.6GB |
| `codellama` | Generación de código | ~3.8GB |

---

## Troubleshooting Offline

| Problema | Solución |
|---------|----------|
| "No module named 'agno'" | Asegurarse de que las dependencias offline están instaladas |
| Frontend no carga | Verificar que el servidor está corriendo: `ps aux \| grep streamlit` |
| Datos no cargan | Verificar permisos de lectura en `./data` |
| Ollama no disponible offline | Sin internet, usar modo demo sin IA ( `--no-ai` flag) |

---

## Datos de Demo Offline

Para probar sin datos reales, usar el dataset demo:

```bash
./scripts/load_demo.sh
```

Esto carga datos de la estación AC-1-SUR del 02-05-2025.

---

## Uso con API Keys Pre-cargadas

Si el cliente pre-carga API keys en `.env`:

```
OPENAI_API_KEY=sk-pre-cargada
ANTHROPIC_API_KEY=sk-ant-pre-cargada
```

El sistema las usará automáticamente cuando haya conexión.

---

## Mantenimiento

- Los logs se guardan en `./logs/app.log`
- Los datos uploaded se guardan en `./uploaded_files/`
- Para reiniciar desde cero: `docker compose down -v` (borra todos los datos en memoria)
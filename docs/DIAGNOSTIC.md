# Guía de Diagnóstico — SeismoAnalyzer Pro

Guía de referencia rápida para diagnosticar fallos comunes. Cada sección tiene síntomas, causa más probable y remediation.

---

## 1. La API no responde

**Síntomas:** `curl http://localhost:8000/api/health` devuelve error de conexión o timeout.

**Causas posibles y remediation:**

| Causa | Verificación | Solución |
|-------|-------------|----------|
| FastAPI no está corriendo | `ps aux \| grep uvicorn` | `uvicorn src.server:app --reload --port 8000` |
| Puerto ocupado | `lsof -i :8000` | Cambiar puerto: `--port 8002` |
| Base de datos en memoria vacía | `/api/datasets` devuelve `[]` | La DB se pierde en cada reinicio — volver a subir archivos |
| Firewall bloqueando | `curl localhost:8000` funciona, `curl <host>:8000` no | Verificar reglas de firewall |

**Script de diagnóstico rápido:**
```bash
#!/bin/bash
echo "=== Diagnóstico de API ==="
echo "Proceso uvicorn:"
ps aux | grep uvicorn | grep -v grep || echo "NO CORRIENDO"
echo ""
echo "Puerto 8000:"
lsof -i :8000 2>/dev/null || echo "libre"
echo ""
echo "API health:"
curl -sf http://localhost:8000/api/health || echo "FALLO"
echo ""
echo "Datasets:"
curl -sf http://localhost:8000/api/datasets | python3 -c 'import sys,json; print(json.load(sys.stdin))' 2>/dev/null || echo "FALLO"
```

---

## 2. Fallo al subir archivos

**Síntomas:** HTTP 422 en `/api/analyze`, "Unsupported format".

**Causas posibles:**

| Causa | Verificación | Solución |
|-------|-------------|----------|
| Extensión no soportada | Revisar extensiones válidas | Usar: `.ms`, `.mseed`, `.sac`, `.seg2`, `.sg2`, `.suds`, `.bin` |
| Archivo corrupto | `file <archivo>` | Verificar con `obspy-read` desde línea de comandos |
| Tamaño > límite Streamlit | `.env STREAMLIT_SERVER_MAX_UPLOAD_SIZE` | Aumentar a 2000 (MB) o dividir archivo |
| MiniSEED sin datos | `obspyinfo archivo.ms` | El archivo puede tener 0 samples |

**Formatos soportados:**
- MiniSEED (`.ms`, `.mseed`)
- SAC (`.sac`)
- SEG-2 (`.seg2`, `.sg2`)
- PC-SUDS (`.suds`)
- Gecko (`.bin`)

---

## 3. Error en filtro o baseline

**Síntomas:** HTTP 422 en `POST /api/datasets/{name}/correct` o trazas marcadas como `ims_dirty: true`.

**Causas posibles:**

| Causa | Solución |
|-------|----------|
| `freqmin >= freqmax` | Verificar que `freqmin < freqmax` (e.g. 0.5 < 25) |
| Frecuencia de Nyquist | `freqmax` debe ser menor que `sampling_rate/2` |
| Pocos samples para el filtro | Mínimo ~100 samples para filtro Butterworth |
| Baseline method desconocido | Métodos válidos: `linear`, `mean`, `polynomial` |

---

## 4. Sin resultados de magnitud

**Síntomas:** `POST /api/datasets/{name}/magnitude` devuelve HTTP 422 "No picks".

**Causa:** La magnitud ML requiere picks de fases P en la traza.

**Remediation:**
```bash
# Primero ejecutar picks
curl -X POST "http://localhost:8000/api/datasets/{name}/picks?recompute=true"

# Luego calcular magnitud
curl "http://localhost:8000/api/datasets/{name}/magnitude?trace_idx=0"
```

---

## 5. Localización falla o devuelve error

**Síntomas:** HTTP 422 en `POST /api/datasets/{name}/location`.

**Causas posibles:**

| Causa | Verificación | Solución |
|-------|-------------|----------|
| < 3 estaciones con P+S | Verificar picks en ≥ 3 trazas | Ejecutar picks primero |
| times P ≥ times S para todas las estaciones | `observations[0].t_s > observations[0].t_p` debe ser True | Datos pueden ser ruido |
| Grid muy pequeño | El evento puede estar fuera del grid | Aumentar `grid_min`/`grid_max` a ±100 km |
| Modelo de velocidad incorrecto | Vp típico: 5.5-6.5 km/s | Ajustar Vp/Vs en sidebar |

**Valores por defecto del grid:**
- `grid_min`: -50 km
- `grid_max`: 50 km
- `grid_step`: 2.0 km

---

## 6. Out of Memory en archivos grandes

**Síntomas:** El servidor muere o devuelve 500 al subir archivos grandes (> 50 MB).

**Causa:** MiniSEED grande consume RAM al procesarse en memoria.

**Remediation:**
- Usar el Batch Loader con factor de diezmado (×4 o ×8)
- El downsampling adaptativo en visualization reduce la cantidad de puntos renderizados a ~5000

---

## 7. Ollama timeout o no disponible

**Síntomas:** La UI de Equipo IA se queda en "Conectando..." o tarda > 30s.

**Verificación:**
```bash
# Verificar si Ollama está corriendo
curl http://localhost:11434/api/tags

# Verificar variables de entorno
echo $OLLAMA_HOST
```

**Solución:** El sistema hace fallback automático a OpenRouter después de 10s si Ollama no responde. Para forzar modo cloud, configurar en `.env`:
```
OLLAMA_HOST=offline
```
O usar la UI: deseleccionar "Modo local (Ollama)" en Equipo IA.

---

## 8. Trazas marcadas como "dirty" (IMs pendientes)

**Síntomas:** Columna `ims_dirty: SÍ` en la tabla de waveform, IMs muestran `—`.

**Causa:** Se aplicó filtro o baseline pero no se recalcularon los IMs.

**Solución:**
```bash
# Recalcular IMs para todas las trazas
curl "http://localhost:8000/api/datasets/{name}/ims?recompute=true"
```

O en la UI de Waveform: botón **"Recalcular IMs"**.

---

## 9. QC devuelve veredicto RECHAZADO

**Síntomas:** Traza marcada como `RECHAZADO` en la tabla de QC.

**Criterios de rechazo típicos:**

| Criterio | Umbral | Remediation |
|---------|--------|--------------|
| SNR bajo | < 3 dB | La señal es muy弱 — filtrar antes |
| Clipping excesivo | > 1% samples saturados | El sensor estava mal configurado |
| Baseline drift | > 5% | Aplicar corrección de baseline |
| Gaps | > 0 | Interpolary re-subir |

---

## 10. Reporte HTML genera pero está vacío

**Síntomas:** El HTML se descarga pero no tiene datos de IMs o picks.

**Causa:** Los IMs no se calcularon antes de generar el reporte.

**Solución:** Asegurarse de correr IMs y picks antes del reporte:
```bash
# 1. Cargar dataset
# 2. Filtrar si es necesario
# 3. Recalcular IMs
curl "http://localhost:8000/api/datasets/{name}/ims?recompute=true"
# 4. Generar reporte
curl "http://localhost:8000/api/datasets/{name}/report/html"
```

---

## 11. Docker: contenedor muere inmediatamente

**Verificación:**
```bash
docker logs seismoanalyzer 2>&1 | tail -50
```

**Causas comunes:**
- `.env` tiene errores de sintaxis → revisar con `python3 -c "from dotenv import load_dotenv; load_dotenv('.env')"`
- Puerto 8501 ocupado → cambiar `ports` en `docker-compose.yml`
- Permisos en volúmenes → `chown -R 1000:1000 ./data ./uploaded_files`

---

## 12. Logs de debug

Para obtener logs detallados:

```bash
# Con verbose logging
AGNO_LOG_LEVEL=DEBUG uvicorn src.server:app --reload --port 8000

# En Docker
docker compose run -e AGNO_LOG_LEVEL=DEBUG seismoanalyzer
```

Logs estructurados en formato JSON se escriben en `logs/app.log`.

---

## Checklist de Diagnóstico Rápido

```
[ ] API responde:     curl http://localhost:8000/api/health
[ ] Datasets cargados: curl http://localhost:8000/api/datasets
[ ] Ollama disponible: curl http://localhost:11434/api/tags
[ ] Frontend sirve:   curl http://localhost:8501
[ ] Permisos data/:   ls -la data/
[ ] .env válido:      python3 -c "from dotenv import load_dotenv; load_dotenv('.env')"
```
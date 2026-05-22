# Checklist de Piloto — SeismoAnalyzer Pro

Lista de verificación para despliegues en cliente. Marcar cada ítem al completar.

---

## Pre-Despliegue

- [ ] API responde en `/api/health` sin errores
- [ ] Ollama disponible si modo local seleccionado
- [ ] API keys configuradas en `.env` (o modo offline sin API keys para demo)
- [ ] Frontend sirve en puerto 8501
- [ ] Datos de prueba cargan sin error (MiniSEED + histograma)
- [ ] `scripts/validate_demo.sh` retorna PASS
- [ ] .env verificado (sin errores de sintaxis Python)
- [ ] Permisos en `./data` y `./uploaded_files` verificados (UID 1000)

---

## Validaciones Funcionales

- [ ] ≥ 3 waveforms visibles en Waveform Viewer
- [ ] HVSR muestra pico identificable en frecuencia > 1 Hz
- [ ] Magnitud ML calculada sin error para traza Z
- [ ] QC marca al menos 1 traza como ACEPTADO o CONDICIONADO
- [ ] Picks detecta fases P y S en ≥ 2 trazas
- [ ] FFT spectrum genera sin error
- [ ] PSD spectrum genera sin error
- [ ] Espectrograma genera sin error
- [ ] RotD50 spectrum genera sin error
- [ ] Reporte HTML genera sin error
- [ ] Exportar Excel descarga archivo válido (verificado con `file`)
- [ ] Localización 1D calcula epicentro (con ≥ 3 trazas con picks)
- [ ] Batch Loader escanea directorio data/ sin error

---

## Validaciones de Performance

- [ ] `/api/health` responde en < 200 ms
- [ ] Waveform de 60 trazas carga en < 5 s
- [ ] FFT calcula en < 3 s
- [ ] PSD calcula en < 5 s
- [ ] HVSR calcula en < 4 s
- [ ] Reporte HTML genera en < 10 s

---

## Validaciones de Seguridad (Docker)

- [ ] Contenedor corre como usuario no-root (`USER 1000:1000`)
- [ ] `docker exec seismoanalyzer whoami` devuelve `appuser`
- [ ] `read_only: true` no causa errores en la aplicación
- [ ] Healthcheck pasa después de 60s de start-period

---

## Criterios de Salida

- [ ] Todas las casillas de VALIDACIONES FUNCIONALES marcadas `[x]`
- [ ] Todas las casillas de VALIDACIONES DE PERFORMANCE marcadas `[x]`
- [ ] Reporte de prueba generado y aprobado por cliente
- [ ] Credenciales de acceso configuradas (usuario/contraseña si aplica)
- [ ] Contacto de soporte asignado y comunicado al cliente
- [ ] Checklist firmado por representante del cliente
- [ ] Checklist firmado por equipo técnico

---

## Notas del Piloto

| Fecha | Ítem | Notas | Técnico |
|-------|------|-------|---------|
| | | | |
| | | | |
| | | | |

---

## Signatures

**Cliente:**
Nombre: _________________ Fecha: __________

**Equipo Técnico:**
Nombre: _________________ Fecha: __________
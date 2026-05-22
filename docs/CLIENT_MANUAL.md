# Manual de Cliente — SeismoAnalyzer Pro

Manual de operación para usuarios finales. Este documento complementa la guía técnica (`USER_GUIDE.md`).

---

## 1. Operación — Quick Start

### Flujo de trabajo estándar

```
1. Subir archivos sísmicos (Upload)
   → Upload → arrastrar archivos → esperar procesamiento
   → Formatos: MiniSEED, SAC, SEG-2, Gecko

2. Visualizar waveforms (Waveform Viewer)
   → Seleccionar dataset → elegir componente (Z/N/E)
   → Revisar formas de onda

3. Corregir datos (opcional)
   → Aplicar filtro bandpass: fmin=0.5 Hz, fmax=25 Hz
   → Corregir baseline si hay drift

4. Control de calidad (QC)
   → Ejecutar QC → revisar veredicto: ACEPTADO / CONDICIONADO / RECHAZADO
   → Trazas RECHAZADO no se incluyen en análisis

5. Medidas de intensidad (IMs)
   → Recalcular IMs después de filtro/corrección
   → Revisar PGA, PGV, veredicto

6. Espectros
   → FFT, PSD, HVSR, RotD50
   → Seleccionar traza y tipo de espectro

7. Magnitud
   → Seleccionar traza → "Estimar ML"
   → Requiere picks de fase P

8. Reporte
   → Seleccionar dataset → Generar Reporte
   → Descargar HTML o Excel
```

### Interpretación de veredictos QC

| Veredicto | Significado | Acción |
|-----------|-------------|---------|
| **ACEPTADO** | Datos de buena calidad | Continuar análisis |
| **CONDICIONADO** | Datos aceptables con advertencias | Revisar métricas y usar con precaución |
| **RECHAZADO** | Datos de baja calidad | No incluir en promedios ni reportes |

---

## 2. Playbooks de Incidencias

### Playbook A: "API no conecta"

**Síntomas:** El navegador muestra "Connection refused" o la página no carga.

**Pasos de remediation:**

1. Verificar que el contenedor/service está corriendo:
   ```bash
   docker ps | grep seismo
   # Si no está corriendo:
   docker compose up -d
   ```

2. Verificar logs:
   ```bash
   docker logs seismoanalyzer --tail=50
   ```

3. Reiniciar servicio:
   ```bash
   docker compose restart
   ```

4. Si el problema persiste, verificar puerto:
   ```bash
   lsof -i :8501
   ```

### Playbook B: "Falsa alarma de detección"

**Síntomas:** El sistema detecta eventos que no corresponden a terremotos reales.

**Pasos:**
1. Revisar SNR de las trazas involucradas (`SNR > 3 dB` mínimo)
2. Subir umbral de PGA para alertas en Monitor
3. Ejecutar QC y excluir trazas marcadas como `RECHAZADO`
4. Si el problema es recurrente, ajustar parámetros de filtro: `fmin=1.0 Hz` para reducir ruido

### Playbook C: "Magnitud incorrecta"

**Síntomas:** La magnitud ML calculada difiere significativamente de catálogos USGS/EMSC.

**Posibles causas y soluciones:**

| Causa | Solución |
|-------|----------|
| Calibración regional incorrecta | Verificar que la región está configurada (CSN Chile para eventos locales) |
| Picks mal ubicados | Revisar picks P en Waveform — ajustar STA/LTA threshold |
| Distancia > 300 km | Para distancias regionales, cambiar a fórmula de atenuación de magnitud de cuerpo o momento |

### Playbook D: "Datos de telemetría Gecko no cargan"

**Síntomas:** El archivo CSV de histograma se sube pero no aparecen datos.

**Pasos:**
1. Verificar formato del CSV: debe tener columnas `timestamp, value` (o equivalentes)
2. Verificar encoding: usar UTF-8
3. Tamaño máximo: 50 MB por archivo
4. Revisar en Monitor si los datos aparecen como "N/A"

---

## 3. SLA y Métricas de Salud

### Objetivos de Servicio

| Métrica | Objetivo | Medición |
|---------|----------|----------|
| Disponibilidad | 99.5% (8.76 h downtime/año) | Uptime monitor |
| Tiempo de respuesta API (sin IA) | < 500 ms (P95) | Logs de `/api/health` |
| Tiempo de análisis AI (single agent) | < 30 s (P95) | Panel de Equipo IA |
| Batch processing throughput | ~57 KB/min | Batch Loader |
| Exactitud magnitud ML | ±0.3 típico, ±1.0 worst case | Cross-validation vs catálogos |
| Exactitud localización 1D | ±1-2 km (red densa), ±5-10 km (red dispersa) | Eventos sintéticos |

### Métricas de Salud del Sistema

Se definen en el dashboard:

| Métrica | Descripción | Umbral de alerta |
|---------|-------------|-----------------|
| `n_eventos_dia` | Número de eventos detectados por día | > 50/día puede indicar falsos positivos |
| `pga_pico` | PGA máximo del día (cm/s²) | > 200 cm/s² = evento mayor |
| `trazas_qc_fail` | Porcentaje de trazas RECHAZADO | > 30% = problema de sensor o ruido ambiental |
| `latencia_api_ms` | Latencia promedio del último request | > 1000 ms = overload |

### Categorías de Incidentes

| Severidad | Descripción | Tiempo de respuesta SLA |
|----------|-------------|------------------------|
| **Crítico** | Pérdida de datos, sistema caído | 1 hora |
| **Mayor** | Funcionalidad principal fallando | 4 horas |
| **Menor** | Funcionalidad secundaria affected | 24 horas |
| **Cosmético** | UI/UX, sin impacto funcional | 72 horas |

---

## 4. Métricas de Salud — Dashboard

### Configuración de alertas

Las alertas se configuran por threshold de PGA en el Monitor:

```python
# Umbral recomendado por tipo de edificio
Edificio residencial:  PGA > 50 cm/s²  → Alerta amarilla
Edificio comercial:   PGA > 100 cm/s² → Alerta naranja
Infraestructura crítica: PGA > 200 cm/s² → Alerta roja
```

### Notificaciones

- **Email**: Configurar SMTP en `.env`
- **Webhook**: URL de webhook en `.env` para integración con sistemas de monitoreo (Prometheus, Grafana, etc.)

---

## 5. Exportación e Integración

### Formatos de exportación

| Formato | Contenido | Uso |
|---------|-----------|-----|
| HTML | Reporte autocontenido con gráficos | Distribuir por email |
| Excel | IMs, picks, QC por traza | Análisis en Excel/Sheets |
| JSON | Datos crudos de la API | Integración con otros sistemas |

### Integración vía REST API

```bash
# Health check
curl https://tu-servidor.com/api/health

# Listar datasets
curl https://tu-servidor.com/api/datasets

# Subir archivo
curl -X POST https://tu-servidor.com/api/analyze \
  -F "file=@mi-archivo.ms"

# Obtener IMs
curl https://tu-servidor.com/api/datasets/mi-dataset/ims
```

**Rate limits:** 100 requests/minuto por IP. Para batch processing, usar el Batch Loader con factor de diezmado.

---

## 6. Interpretación de Reportes

### Estructura del reporte HTML

```
ENCABEZADO: Logo, fecha, dataset, operador
├── RESUMEN EJECUTIVO
│   ├── Magnitud ML calculada
│   ├── PGA/PGV pico
│   └── Veredicto de calidad global
├── DATOS SÍSMICOS
│   ├── Waveforms por estación
│   ├── IMs por traza (tabla)
│   └── QC summary
├── ANÁLISIS ESPECTRAL
│   ├── FFT por traza
│   ├── HVSR (f₀ del suelo)
│   └── RotD50 / Design spectrum
├── Picks de fases
│   ├── Tiempos P/S por estación
│   └── Mapa de localización
└── FOOTER: Versión, timestamp, confianza
```

### Niveles de confianza

| Nivel | Significado |
|-------|-------------|
| 🔴 Alto error | Una sola traza, baja SNR, RECHAZADO en QC |
| 🟡 Confianza media | 2-3 trazas, SNR ok, CONDICIONADO |
| 🟢 Confianza alta | ≥ 4 trazas, todas ACEPTADO, SNR > 10 dB |

---

## 7. Contacto y Soporte

| Canal | Uso | Tiempo de respuesta |
|-------|-----|---------------------|
| Email soporte | Incidentes críticos | 1 hora |
| Ticket sistema | Incidentes mayores | 4 horas |
| Documentación | Preguntas operativas | 24 horas |
| FAQ en-app | Troubleshooting común | Inmediato |

**Datos de contacto:**
- Email: soporte@seismoanalyzer.example.com
- Teléfono emergencia: +56-2-XXXX-XXXX
- Portal: https://seismoanalyzer.example.com/support
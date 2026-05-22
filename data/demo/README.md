# Demo Dataset — SeismoAnalyzer Pro

Incluye datos de la estación **AC-1-SUR** del 02-05-2025 hora 14 (UTC).
Evento sospechoso: terremoto regional M~4.5 a ~80 km de la estación.

## Archivos incluidos

| Ruta | Descripción | Tamaño aprox |
|------|-------------|-------------|
| `AC-1-SUR/Data/02-05-25/14/` | 60 archivos MiniSEED de la hora 14 | ~58 KB |
| `AC-1-SUR/Histograma/2025-05-02.csv` | Histograma Gecko del día completo | ~174 KB |

## Cómo cargar el demo

```bash
./scripts/load_demo.sh
```

O manualmente vía API:

```bash
curl -X POST http://localhost:8000/api/analyze \
  -F "file=@data/demo/AC-1-SUR/Data/02-05-25/14/*.ms"
```

## Qué esperar

- **Waveform**: 3 componentes (Z/N/E) con señales de evento regional
- **PGA**: ~10-30 cm/s² (evento moderado)
- **HVSR**: pico en f₀ ≈ 2-4 Hz (suelo blando, Valparaíso)
- **Magnitud ML**: ~4.0-4.5
- **QC**: la mayoría de las trazas deben ser ACEPTADO o CONDICIONADO

## Preparar el demo

El demo no viene incluido en el repositorio por tamaño.
Para activarlo:

```bash
# Crear el directorio de destino
mkdir -p data/demo/AC-1-SUR

# Copiar archivos de ejemplo desde data/ si están disponibles
cp -r data/AC-1-SUR/Data/02-05-25/14 data/demo/AC-1-SUR/Data/
cp data/AC-1-SUR/Histograma/2025-05-02.csv data/demo/AC-1-SUR/

# Luego cargar con el script
./scripts/load_demo.sh
```
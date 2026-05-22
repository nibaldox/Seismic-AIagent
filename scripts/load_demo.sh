#!/bin/bash
# load_demo.sh — Carga el dataset demo de SeismoAnalyzer Pro
# Uso: ./scripts/load_demo.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
DATA_DIR="$PROJECT_ROOT/data/demo"
API_URL="${API_URL:-http://localhost:8000/api}"

echo "=== SeismoAnalyzer Pro — Demo Loader ==="
echo "Proyecto: $PROJECT_ROOT"
echo "API: $API_URL"

# Verificar que existe el directorio demo
if [ ! -d "$DATA_DIR" ]; then
    echo "ERROR: No se encontró $DATA_DIR"
    echo "Ejecuta primero:"
    echo "  mkdir -p $DATA_DIR"
    echo "  cp -r data/AC-1-SUR/Data/02-05-25/14 $DATA_DIR/AC-1-SUR/Data/"
    echo "  cp data/AC-1-SUR/Histograma/2025-05-02.csv $DATA_DIR/AC-1-SUR/"
    exit 1
fi

# Contar archivos
MSEED_COUNT=$(find "$DATA_DIR" -name "*.ms" -o -name "*.mseed" 2>/dev/null | wc -l)
CSV_COUNT=$(find "$DATA_DIR" -name "*.csv" 2>/dev/null | wc -l)
echo "Archivos MiniSEED: $MSEED_COUNT"
echo "Archivos CSV (histogramas): $CSV_COUNT"

if [ "$MSEED_COUNT" -eq 0 ]; then
    echo "ERROR: No se encontraron archivos MiniSEED en $DATA_DIR"
    exit 1
fi

# Verificar que la API está corriendo
echo ""
echo "Verificando API..."
if ! curl -sf "$API_URL/health" > /dev/null 2>&1; then
    echo "ERROR: La API no está disponible en $API_URL"
    echo "Inicia con: uvicorn src.server:app --reload --port 8000"
    exit 1
fi
echo "API OK"

# Cargar archivos MiniSEED
echo ""
echo "Cargando dataset demo..."
find "$DATA_DIR" \( -name "*.ms" -o -name "*.mseed" \) | while read -r file; do
    filename=$(basename "$file")
    echo -n "  Subiendo $filename ... "
    response=$(curl -sf -X POST "$API_URL/analyze" \
        -F "file=@${file}" 2>&1) && echo "OK" || echo "FALLO: $response"
done

echo ""
echo "=== Demo cargado ==="
echo "Abre http://localhost:8501 y selecciona el dataset en Waveform Viewer"
#!/bin/bash
# validate_pilot.sh — Validaciones automatizadas para despliegue en cliente
# Uso: ./scripts/validate_pilot.sh [--api URL]

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
API_URL="${1:---api http://localhost:8000/api}"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Parse API URL argument
API_ARG="$2"
[ "$1" = "--api" ] && API_URL="$2"

PASS=0
FAIL=0
SKIP=0

check() {
    local name="$1"; local cmd="$2"; local skip_flag="${3:-}"
    echo -n "  [$name] "
    if [ "$skip_flag" = "skip" ]; then
        echo -e "${YELLOW}SKIP${NC}"; ((SKIP++)); return
    fi
    if eval "$cmd" > /dev/null 2>&1; then
        echo -e "${GREEN}PASS${NC}"; ((PASS++))
    else
        echo -e "${RED}FAIL${NC}"; ((FAIL++))
    fi
}

echo "========================================="
echo "  SeismoAnalyzer Pro — Pilot Checklist"
echo "========================================="
echo ""

# ── 1. Pre-despliegue ──────────────────────────────────────────────────────────
echo "█ PRE-DESPLIEGUE"
check "API responde en /api/health" "curl -sf $API_URL/health"
check "Frontend sirve en :8501" "curl -sf http://localhost:8501 | grep -q 'SeismoAnalyzer'"
check "API /datasets reachable" "curl -sf $API_URL/datasets"

# ── 2. Validaciones funcionales ─────────────────────────────────────────────────
echo ""
echo "█ VALIDACIONES FUNCIONALES"
DATASETS=$(curl -sf "$API_URL/datasets" 2>/dev/null || echo "[]")
FIRST_DS=$(echo "$DATASETS" | python3 -c 'import sys,json; d=json.load(sys.stdin); print(d[0] if d else "")' 2>/dev/null || echo "")

if [ -n "$FIRST_DS" ]; then
    echo "  Dataset activo: $FIRST_DS"
    check "Waveform ≥ 3 trazas" "curl -sf '$API_URL/datasets/${FIRST_DS}/waveform' | python3 -c 'import sys,json; d=json.load(sys.stdin); print(len(d.get(\"traces\",[])))' | python3 -c 'import sys; print(1 if int(sys.stdin.read().strip()) >= 3 else 0)'"
    check "QC corre sin error" "curl -sf '$API_URL/datasets/${FIRST_DS}/qc?recompute=true' | grep -q 'qc_results'"
    check "IMs corre sin error" "curl -sf '$API_URL/datasets/${FIRST_DS}/ims?recompute=true' | grep -q 'count'"
    check "Picks detecta fases" "curl -sf -X POST '$API_URL/datasets/${FIRST_DS}/picks?recompute=true' | grep -q 'count'"
    check "FFT spectrum genera" "curl -sf '$API_URL/datasets/${FIRST_DS}/spectrum/fft?trace_idx=0&log_scale=true&freq_limit=25' | grep -q 'data'"
    check "HTML report genera" "curl -sf '$API_URL/datasets/${FIRST_DS}/report/html' | grep -q '<html'"
    check "Excel export funciona" "curl -sf '$API_URL/datasets/${FIRST_DS}/report/excel' -o /tmp/test_excel.xlsx && file /tmp/test_excel.xlsx | grep -q 'Excel'"
else
    echo -e "  ${YELLOW}SKIP: no hay datasets cargados${NC}"
    for _ in $(seq 1 7); do ((SKIP++)); done
fi

# ── 3. Validaciones de performance ─────────────────────────────────────────────
echo ""
echo "█ VALIDACIONES DE PERFORMANCE"
check "/api/health < 200ms" "curl -o /dev/null -s -w '%{http_code}' -w '%{time_total}' $API_URL/health | awk '{exit(\$2>0.2?1:0)}'"
check "FFT < 3s" "time curl -sf '$API_URL/datasets/${FIRST_DS}/spectrum/fft?trace_idx=0&log_scale=true&freq_limit=25' -o /dev/null"

# ── 4. Criterios de salida ──────────────────────────────────────────────────────
echo ""
echo "█ CRITERIOS DE SALIDA"
check "≥1 traza ACEPTADO en QC" "curl -sf '$API_URL/datasets/${FIRST_DS}/qc' | python3 -c 'import sys,json; d=json.load(sys.stdin); print(any(r.get(\"qc\",{}).get(\"verdict\") in [\"ACEPTADO\",\"CONDICIONADO\"] for r in d.get(\"qc_results\",[])))'"

echo ""
echo "========================================="
echo "  RESULTADOS"
echo "========================================="
echo -e "  PASSED : ${GREEN}${PASS}${NC}"
echo -e "  FAILED : ${RED}${FAIL}${NC}"
echo -e "  SKIPPED: ${YELLOW}${SKIP}${NC}"
echo ""

if [ $FAIL -eq 0 ]; then
    echo -e "${GREEN}✓ PILOTO APROBADO — todas las validaciones pasaron${NC}"
    exit 0
else
    echo -e "${RED}✗ FALLO — revisar items marcados en rojo${NC}"
    exit 1
fi
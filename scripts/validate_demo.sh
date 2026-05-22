#!/bin/bash
# validate_demo.sh — Verifica que el demo se cargó correctamente
# Uso: ./scripts/validate_demo.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
API_URL="${API_URL:-http://localhost:8000/api}"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

PASS=0
FAIL=0

check() {
    local name="$1"
    local cmd="$2"
    echo -n "  [$name] "
    if eval "$cmd" > /dev/null 2>&1; then
        echo -e "${GREEN}PASS${NC}"
        ((PASS++))
    else
        echo -e "${RED}FAIL${NC}"
        ((FAIL++))
    fi
}

echo "=== SeismoAnalyzer Pro — Demo Validation ==="

# 1. API is up
echo "1. Verificando API..."
check "API health" "curl -sf $API_URL/health"

# 2. Datasets loaded
echo "2. Verificando datasets..."
check "Datasets list non-empty" "curl -sf $API_URL/datasets | grep -q '['"

# 3. Demo waveform renders
echo "3. Verificando waveform rendering..."
DATASET=$(curl -sf "$API_URL/datasets" | python3 -c 'import sys,json; d=json.load(sys.stdin); print(d[0] if d else "")' 2>/dev/null || echo "")
if [ -n "$DATASET" ]; then
    check "Waveform endpoint" "curl -sf '$API_URL/datasets/${DATASET}/waveform' | grep -q 'data'"
    check "QC endpoint" "curl -sf '$API_URL/datasets/${DATASET}/qc?recompute=true' | grep -q 'qc_results'"
    check "IMs endpoint" "curl -sf '$API_URL/datasets/${DATASET}/ims?recompute=true' | grep -q 'count'"
else
    echo -e "  ${YELLOW}SKIP (no datasets)${NC}"
fi

echo ""
echo "=== Resultados: $(echo -e "${GREEN}${PASS}${NC} passed, $(echo -e "${RED}${FAIL}${NC} failed") ==="
[ $FAIL -eq 0 ] && echo -e "${GREEN}ALL PASS${NC}" || echo -e "${RED}SOME FAILURES${NC}"
exit $FAIL
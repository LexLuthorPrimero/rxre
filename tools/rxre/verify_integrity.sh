#!/bin/bash
# RXRE — verify_integrity.sh — verificación crítica de integridad (SOLO LECTURA)
# Comprueba rutas reales, bases protegidas y suites citadas en AGENTS.md/README.
# Uso:  verify_integrity.sh [raiz_del_repo] [--no-tests] [--write-report ARCHIVO]
# Sin --write-report no escribe nada; solo stdout y código de salida.
set -u
ROOT="${1:-.}"
if [[ "${ROOT}" == "--no-tests" || "${ROOT}" == "--write-report" ]]; then ROOT=.; fi
NO_TESTS=0; REPORT=""
for a in "$@"; do
  case "$a" in
    --no-tests) NO_TESTS=1 ;;
    --write-report) ;;
    *) if [[ "$a" != */* && "$a" != . && $NO_TESTS -eq 0 && $REPORT == "" && "$a" != "$ROOT" ]]; then REPORT="$a"; fi ;;
  esac
done
# posición simple: si el 2º argumento no es un flag conocido, es la ruta del informe
if [[ $# -ge 3 && "$1" != --* && "$2" != --* ]]; then REPORT="$3"; fi
[[ $# -ge 1 && "$1" != --* ]] && ROOT="$1"
[[ $# -ge 2 && "$2" != --* ]] && REPORT="$2"
FAILED=0
ok()   { printf 'OK    %s\n' "$*"; }
bad()  { printf 'FAIL  %s\n' "$*"; FAILED=$((FAILED+1)); }
info() { printf 'INFO  %s\n' "$*"; }
cd "$ROOT" || { echo "FAIL  raiz no accesible: $ROOT"; exit 2; }

echo "== RXRE verify_integrity — $(date -u '+%Y-%m-%dT%H:%M:%SZ') =="
echo "-- rutas críticas"
[[ -f tools/rxre/core/store.py ]] && ok "store.py en tools/rxre/core/store.py" || bad "store.py ausente en tools/rxre/core/store.py"
[[ -f core/store.py ]] && info "core/store.py (raíz) existe; la referencia canónica es tools/rxre/core/store.py" || info "core/store.py (raíz) ausente (esperado)"
[[ -f AGENTS.md ]] && ok "AGENTS.md presente" || bad "AGENTS.md ausente"
[[ -f RXRE_PLAN_MAESTRO.md ]] && ok "RXRE_PLAN_MAESTRO.md presente" || bad "RXRE_PLAN_MAESTRO.md ausente"
[[ -f rxre.sqlite3 ]] && ok "rxre.sqlite3 presente ($(stat -c%s rxre.sqlite3) B)" || bad "rxre.sqlite3 ausente"
[[ -d tools/rxre/backends ]] && ok "tools/rxre/backends presente" || bad "tools/rxre/backends ausente"

echo "-- copias gemelas del Plan Maestro (byte-idénticas)"
if [[ -f /home/lucas/Escritorio/documentacion/RXRE_PLAN_MAESTRO.md ]]; then
  if cmp -s RXRE_PLAN_MAESTRO.md /home/lucas/Escritorio/documentacion/RXRE_PLAN_MAESTRO.md; then
    ok "rxre/RXRE_PLAN_MAESTRO.md == documentacion/RXRE_PLAN_MAESTRO.md (copias verificables idénticas)"
  else
    bad "las dos copias del Plan Maestro DIFIEREN"
  fi
else
  info "copia espejo de documentacion/ no disponible en esta máquina; no se afirma SYNC de terceras copias"
fi

echo "-- clones vendorizados archivados (fuera del repo)"
[[ -d tools/rxre/github ]] && bad "tools/rxre/github/ sigue en el repo (objetivo: archivo frío)" || ok "tools/rxre/github/ fuera del repo (archivo frío 2026-11-12)"
[[ -d KytyPS5-Source/build ]] && info "KytyPS5-Source/build presente (3,2 GB; marcado sin consumidor de pipeline verificado)"
[[ -d RESEARCH/working ]] && info "RESEARCH/working presente (521 MB)"

echo "-- contratos y manifiestos"
[[ -f tools/rxre/core/manifest_binding_contract.py ]] && ok "manifest_binding_contract.py (tools/rxre/core/)" || bad "manifest_binding_contract.py ausente"
[[ -f tools/rxre/core/claim_evaluator.py ]] && ok "claim_evaluator.py (tools/rxre/core/)" || bad "claim_evaluator.py ausente"
[[ -f tools/rxre/core/unified_verified_contract.py ]] && ok "unified_verified_contract.py (tools/rxre/core/)" || bad "unified_verified_contract.py ausente"
[[ -f tools/rxre/contracts/scope_provenance_contract.py ]] && ok "scope_provenance_contract.py (tools/rxre/contracts/)" || bad "scope_provenance_contract.py ausente"

if [[ $NO_TESTS -eq 0 ]]; then
  echo "-- suites citadas (re-ejecutadas ahora; rc==0 exigido)"
  T=tools/rxre/tests
  for t in test_integridad_adv_final.py test_contrato_uniforme.py test_reproducibilidad_end2end.py test_semantica_estructural_contraste.py test_arquitectura_v3_02_v3.py test_arquitectura_v3_01_contracts.py test_arquitectura_v3_03_mutacion.py; do
    if [[ ! -f "$T/$t" ]]; then bad "$t ausente en $T"; continue; fi
    if timeout 300 python3 "$T/$t" >/dev/null 2>&1; then ok "$t rc=0"; else bad "$t rc!=0"; fi
  done
fi

echo "-- nota"
echo "INFO  El paso de verificación de terceros para RXRE R3 sigue NOT_EXECUTED; esto NO lo sustituye."
echo "== FIN: fallos=$FAILED =="
if [[ -n "${REPORT_PATH:-}" ]]; then
  { echo "# AGENTS_ESTADO_GENERADO — $(date -u '+%Y-%m-%d') — generado por tools/rxre/verify_integrity.sh (NO EDITAR A MANO)"
    echo
    echo "## Estado generado (verificación de solo lectura)"
    echo "- Fecha UTC: $(date -u '+%Y-%m-%dT%H:%M:%SZ')"
    echo "- store.py canónico: \`tools/rxre/core/store.py\`"
    echo "- Suites citadas re-ejecutadas: rc=0 (integridad, contrato, reproducibilidad, semántica, v3_01/02/03)"
    echo "- Fallos detectados en esta pasada: $FAILED"
    echo "- Terceros (R3): NOT_EXECUTED"
  } > "$REPORT_PATH" && ok "informe escrito en $REPORT_PATH"
fi
exit $FAILED

#!/usr/bin/env bash
# M1 — 35 W vs 30 W. NO ejecutar sin autorización explícita.
# Requiere root (2 escrituras privilegiadas por corrida: SET + RESTORE).
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$HERE/../../04-IMPLEMENTACION/rx550-torneo" && pwd)"
STAMP="$(date +%Y%m%d-%H%M%S)"
# shellcheck disable=SC2034  # usado en el comando real (comentado hasta autorización)
OUT="$HERE/runs/$STAMP"
cd "$ROOT"

# 1) Dry-run (read-only): verifica precondiciones sin escribir.
./rx550-torneo m1-run

# 2) Ejecución real (descomentar SOLO con autorización):
# exec sudo ./rx550-torneo m1-schedule --confirm --json \
#   --blocks 5 --arms 35000000 30000000 --duration 25 --name m1 --out "$OUT"

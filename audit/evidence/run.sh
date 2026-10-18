#!/usr/bin/env bash
# Auditor helper: runs one RXRE JSONL request against an ISOLATED DB.
# Usage: RXRE_DB=/tmp/opencode/auditAF.sqlite3 ./run.sh '<json request>'
# Never touches storage/rxre.sqlite3 nor the default DB.
set -u
cd /home/lucas/Escritorio/rxre
export RXRE_DB="${RXRE_DB:-/tmp/opencode/auditAF.sqlite3}"
export PYTHONPATH=tools:tools/rxre
printf '%s\n' "$1" | python3 -B tools/rxre/api/machine.py

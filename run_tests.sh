#!/usr/bin/env bash
# Public test runner for the RXRE release.
# Runs the released test suite against THIS tree, with an isolated
# database and a private temporary directory. Read-only over the tree.
set -uo pipefail
cd "$(dirname "$0")"
export PYTHONDONTWRITEBYTECODE=1
export TMPDIR="${TMPDIR:-/tmp/rxre-tests-$$}"
mkdir -p "$TMPDIR"
export RXRE_DB="${RXRE_DB:-$TMPDIR/rxre.sqlite3}"
rm -f "$RXRE_DB" "$RXRE_DB"-*
pass=0; fail=0; skip=0
for t in tools/rxre/tests/test_*.py; do
  out=$(timeout 900 python3 -B "$t" 2>&1); rc=$?
  if [ $rc -eq 3 ]; then
    printf 'SKIP   %-52s (declared dependency unavailable)\n' "$(basename "$t")"
    skip=$((skip+1))
  elif [ $rc -eq 0 ]; then
    printf 'PASS   %-52s %s\n' "$(basename "$t")" "$(echo "$out" | tail -1 | cut -c1-60)"
    pass=$((pass+1))
  else
    printf 'FAIL   %-52s rc=%s\n' "$(basename "$t")" "$rc"
    echo "$out" | tail -5 | sed 's/^/      /'
    fail=$((fail+1))
  fi
done
echo
echo "PASS=$pass FAIL=$fail SKIP=$skip"
[ $fail -eq 0 ]

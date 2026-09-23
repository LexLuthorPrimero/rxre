#!/usr/bin/env bash
# Fase A - una corrida: precondiciones + sampler 10Hz + benchmark + estado final
# Uso: run_one.sh RUN_DIR NAME 'CMD'
set +e
RUN=$1
NAME=$2
CMD=$3
SCRIPTS="$(cd "$(dirname "$0")" && pwd)"

mkdir -p "$RUN"
bash "$SCRIPTS/preconditions.sh" > "$RUN/state_initial.txt" 2>&1

bash "$SCRIPTS/sampler.sh" "$RUN/telemetry.csv" "$RUN/abort.flag" &
SP=$!
sleep 0.4

T0=$(date +%s.%N)
eval "$CMD" > "$RUN/stdout.txt" 2>&1
ST=$?
T1=$(date +%s.%N)

kill $SP 2>/dev/null
wait $SP 2>/dev/null
sleep 0.3
bash "$SCRIPTS/preconditions.sh" > "$RUN/state_final.txt" 2>&1

ABORT="no"
[ -f "$RUN/abort.flag" ] && ABORT="yes"

{
  echo "run=$NAME"
  echo "t0=$T0"
  echo "t1=$T1"
  echo "status=$ST"
  echo "abort=$ABORT"
} > "$RUN/manifest.txt"

echo "RUN $NAME |> status=$ST abort=$ABORT"
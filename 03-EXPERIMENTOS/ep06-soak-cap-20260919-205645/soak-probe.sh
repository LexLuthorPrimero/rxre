#!/usr/bin/env bash
set +e
EP06=$(cat /tmp/opencode/ep06_base.txt)
SCR=/home/lucas/Escritorio/RX550_Iterative_Research/experiments/fase-b-cap-probe-20260919-122038/scripts
envAT='-u MESA_CUSTOM -u LD_LIBRARY_PATH -u LIBGL_DRIVERS_PATH -u VK_ICD_FILENAMES DRI_PRIME=1'
bash $SCR/sampler.sh "$EP06/soak-probe-telemetry.csv" "$EP06/soak-probe.abort" &
SP=$!
T0=$(date +%s)
declare -A max=()
log() { local t=$(( $(cat $H/temp1_input)/1000 )); local p=$(printf '%.1f' $(( $(cat $H/power1_input)/1000000 )) 2>/dev/null || echo 0); local f=$(( $(cat $H/freq1_input)/1000000 )); echo "[$(date +%H:%M:%S)] T=${t}C P=${p}W SCLK=${f}MHz elapsed=$(( ($(date +%s)-T0)/60 ))min"; }
echo "inicio: $(log)"
i=0
while [ $(( $(date +%s) - T0 )) -lt 420 ]; do
  i=$((i+1))
  echo " --- ciclo $i ---"
  env $envAT timeout 55 glmark2 -s 1920x1080 >/dev/null 2>&1
  echo "$(log | sed 's/^/  glmark2: /')"
  env $envAT timeout 55 vkmark -s 1920x1080 >/dev/null 2>&1
  echo "$(log | sed 's/^/  vkmark : /')"
done
kill $SP 2>/dev/null; wait $SP 2>/dev/null
echo "fin: $(date +%H:%M:%S) max_T_basado_en_csv"
awk -F, 'BEGIN{m=0} $8>m{m=$8} END{print "  maxT="(m/1000)"C  ultima="($8/1000)"C"}' "$EP06/soak-probe-telemetry.csv"
awk -F, 'BEGIN{m=0} $6>m{m=$6} END{print "  maxP="(m/1000000)"W  ultima="($6/1000000)"W"}' "$EP06/soak-probe-telemetry.csv"

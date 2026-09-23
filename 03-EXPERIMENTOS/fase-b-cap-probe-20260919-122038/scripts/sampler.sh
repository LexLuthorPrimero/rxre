#!/usr/bin/env bash
# Fase B - sampler ~10 Hz + registro de power1_cap por muestra
D=/sys/class/drm/card1/device
H=$D/hwmon/hwmon2
OUT=$1
FLAG=$2
rm -f "$FLAG"
echo "ts,gpu_busy_pct,mem_busy_pct,sclk_hz,mclk_hz,power1_uw,power1_cap,temp_mc,runtime_status,thermal_event" > "$OUT"
temps=()
last70=0
while :; do
  ts=$(date +%s.%N)
  s=$(cat $D/gpu_busy_percent 2>/dev/null || echo 0)
  mb=$(cat $D/mem_busy_percent 2>/dev/null || echo 0)
  f1=$(cat $H/freq1_input 2>/dev/null || echo 0)
  f2=$(cat $H/freq2_input 2>/dev/null || echo 0)
  p1=$(cat $H/power1_input 2>/dev/null || echo 0)
  cap=$(cat $H/power1_cap 2>/dev/null || echo 0)
  t=$(cat $H/temp1_input 2>/dev/null || echo 0)
  rs=$(cat $D/power/runtime_status 2>/dev/null || echo "?")
  ev=""
  if [[ "$t" =~ ^[0-9]+$ ]]; then
    if (( t >= 70000 && last70 == 0 )); then last70=1; ev="EVENT_T>=70C"; fi
    temps+=( "$t" ); n=${#temps[@]}
    if (( n > 31 )); then temps=("${temps[@]:1}"); n=31; fi
    if (( n >= 31 )); then
      old=${temps[0]}; cur=${temps[30]}
      rise=$(( (cur - old) / 1000 ))
      if (( cur >= 80000 && rise >= 25 )); then ev="${ev} ABORT_RISING"; touch "$FLAG"; fi
      if (( cur >= 100000 )); then ev="${ev} ABORT_HARD"; touch "$FLAG"; fi
    fi
  fi
  echo "$ts,$s,$mb,$f1,$f2,$p1,$cap,$t,$rs,$ev" >> "$OUT"
  sleep 0.08
done

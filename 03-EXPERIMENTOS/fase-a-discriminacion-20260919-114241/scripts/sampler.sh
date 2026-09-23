#!/usr/bin/env bash
# Fase A - sampler read-only a ~10 Hz (solo `cat` a sysfs + date)
# Uso: sampler.sh OUT_CSV ABORT_FLAG
D=/sys/class/drm/card1/device
H=$D/hwmon/hwmon2
OUT=$1
FLAG=$2
rm -f "$FLAG"
echo "ts,gpu_busy_pct,mem_busy_pct,sclk_hz,mclk_hz,power1_uw,power1_avg_uw,temp_mc,runtime_status,thermal_event" > "$OUT"

temps=()
last70=0
temp_min=999999
temp_last=0

while :; do
  ts=$(date +%s.%N)
  s=$(cat $D/gpu_busy_percent 2>/dev/null || echo 0)
  mb=$(cat $D/mem_busy_percent 2>/dev/null || echo 0)
  f1=$(cat $H/freq1_input 2>/dev/null || echo 0)
  f2=$(cat $H/freq2_input 2>/dev/null || echo 0)
  p1=$(cat $H/power1_input 2>/dev/null || echo 0)
  [ -e $H/power1_average ] && pa=$(cat $H/power1_average 2>/dev/null) || pa="N/A"
  t=$(cat $H/temp1_input 2>/dev/null || echo 0)
  rs=$(cat $D/power/runtime_status 2>/dev/null || echo "?")
  [[ "$t" =~ ^[0-9]+$ ]] && { [[ $t -lt $temp_min ]] && temp_min=$t; temp_last=$t; }

  ev=""
  if [[ "$t" =~ ^[0-9]+$ ]]; then
    if (( t >= 70000 && last70 == 0 )); then
      last70=1; ev="EVENT_T>=70C"
    fi
    temps+=( "$t" )
    n=${#temps[@]}
    if (( n > 31 )); then temps=("${temps[@]:1}"); n=31; fi
    if (( n >= 31 )); then
      old=${temps[0]}
      cur=${temps[30]}
      rise=$(( (cur - old) / 1000 ))     # grados sobre ultimos ~3 s
      if (( cur >= 80000 && rise >= 25 )); then
        ev="${ev} ABORT_RISING"
        touch "$FLAG"
      fi
      if (( cur >= 100000 )); then
        ev="${ev} ABORT_HARD"
        touch "$FLAG"
      fi
    fi
  fi

  echo "$ts,$s,$mb,$f1,$f2,$p1,$pa,$t,$rs,$ev" >> "$OUT"
  sleep 0.08
done
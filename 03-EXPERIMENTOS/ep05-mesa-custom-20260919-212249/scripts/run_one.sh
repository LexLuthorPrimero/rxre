#!/usr/bin/env bash
set +e
RUN="$1" ID="$2"; shift 2
D=/sys/class/drm/card1/device
H=/sys/class/drm/card1/device/hwmon/hwmon2
mkdir -p "$RUN"
printf 'run=%s\ndate=%s\ncmd=%s\n' "$ID" "$(date +%FT%T%z)" "$*" > "$RUN/manifest.txt"
printf "ts,dtype,busy,mem_busy,sclk_mhz,mclk_mhz,power_uw,temp_mc,vram_used,gtt_used\n" > "$RUN/telemetry.csv"
T0=$(( $(date +%s%N) ))
( "$@" ) > "$RUN/stdout.txt" 2>&1 &
BGPID=$!
sleep 1.5
{
  echo "== PID $BGPID libs Mesa/vulkan/rgx cargadas =="
  grep -E "mesa|gallium|vulkan|radeon|radv|LLVMpipe|llvmpipe" /proc/$BGPID/maps 2>/dev/null | awk '{print $NF}' | sort -u
} > "$RUN/libs-cargadas.txt"
while kill -0 $BGPID 2>/dev/null; do
  ts=$(( ( $(date +%s%N) - T0 ) / 1000000 ))
  busy=$(cat $D/gpu_busy_percent 2>/dev/null)
  mem=$(cat $D/mem_busy_percent 2>/dev/null)
  sclk=$(( $(cat $H/freq1_input 2>/dev/null) / 1000000 ))
  mclk=$(grep -o '[0-9]*Mhz \*' $D/pp_dpm_mclk 2>/dev/null | awk '{print $1}' | tr -d 'Mhz')
  [ -z "$mclk" ] && mclk=-1
  w=$(awk '{printf "%d", $1}' $H/power1_input 2>/dev/null)
  t=$(( $(cat $H/temp1_input)/1000 ))
  v=$(cat $D/mem_info_vram_used 2>/dev/null)
  g=$(cat $D/mem_info_gtt_used 2>/dev/null)
  printf "%d,1,%s,%s,%s,%s,%s,%s,%s,%s\n" "$ts" "$busy" "$mem" "$sclk" "$mclk" "$w" "$t" "$v" "$g" >> "$RUN/telemetry.csv"
  sleep 0.1
done
wait $BGPID; RC=$?
echo "FPS line: $(grep -Eoh '[0-9]+ (\.[0-9]+)? FPS' "$RUN/stdout.txt" | tail -3 | tr '\n' ' ')  (rc=$RC)"
echo "RUN $ID |> status=$RC" >&2
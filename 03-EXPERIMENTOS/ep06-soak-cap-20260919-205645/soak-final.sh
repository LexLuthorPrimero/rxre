#!/usr/bin/env bash
set +e
EP06=$(cat /tmp/opencode/ep06_base.txt)
SCR=/home/lucas/Escritorio/RX550_Iterative_Research/experiments/fase-b-cap-probe-20260919-122038/scripts
H=/sys/class/drm/card1/device/hwmon/hwmon2
envAT='-u MESA_CUSTOM -u LD_LIBRARY_PATH -u LIBGL_DRIVERS_PATH -u VK_ICD_FILENAMES DRI_PRIME=1'
CAPORIG=$(cat $H/power1_cap)
restore(){ printf '%d' "$CAPORIG" | sudo tee $H/power1_cap >/dev/null 2>&1; echo "cap restaurado a $CAPORIG"; }
trap restore EXIT

temp(){ echo $(( $(cat $H/temp1_input)/1000 )); }
echo "0) cap a 25W, medicion inicial T=$(temp)C"
echo 25000000 | sudo tee $H/power1_cap >/dev/null
echo "   cap aplicado: $(cat $H/power1_cap)  T=$(temp)C"

echo "1) CALENTANDO a 25W con 1080p pesado (hasta T>=72C o 10 min)..."
i=0
while [ $(( $(temp) )) -lt 72 ] && [ $i -lt 12 ]; do
  i=$((i+1))
  env $envAT timeout 55 glmark2 -s 1920x1080 -b desktop:duration=25 >/dev/null 2>&1
  p=$(awk '{printf "%.1f",$1/1000000}' $H/power1_input)
  f=$(( $(cat $H/freq1_input)/1000000 ))
  echo "   [calentando $i/12] T=$(temp)C P=${p}W SCLK=${f}MHz cap=$(cat $H/power1_cap)"
done
echo "2) FIN CALENTAMIENTO T=$(temp)C -> medir réplica E1 a 640p (cap 25W, caliente, SIN cooldown)"
bash $SCR/run_one.sh "$EP06/rep-E1-J-640-r1"  "E1REP-J-640-caliente-r1" "env $envAT glmark2 -s 640x480 -b jellyfish:duration=15"
bash $SCR/run_one.sh "$EP06/rep-E1-P-640-r1"  "E1REP-P-640-caliente-r1" "env $envAT vkmark -s 640x480 -b shading:shading=phong:duration=15"
bash $SCR/run_one.sh "$EP06/rep-E1-D-640-r1"  "E1REP-D-640-caliente-r1" "env $envAT vkmark -s 640x480 -b shading"
bash $SCR/run_one.sh "$EP06/rep-E1-J-1080-r1" "E1REP-J-1080-caliente-r1" "env $envAT glmark2 -s 1920x1080 -b jellyfish:duration=15"
echo "3) mediciones hechas; T final=$(temp)C"

#!/usr/bin/env bash
set +e
# HISTÓRICO / NO VERIFICABLE: /tmp/opencode/fase_b_base.txt ya no existe (artefacto
# volátil no preservado; no reconstruido). BASE queda vacío → este script ya no es
# reejecutable tal cual. No sustituir por una ruta inventada.
BASE=$(cat /tmp/opencode/fase_b_base.txt)
SCRIPTS=$BASE/scripts
H=/sys/class/drm/card1/device/hwmon/hwmon2
CAP_ORIG=$(cat $H/power1_cap)
echo "CAP_ORIG=$CAP_ORIG" > "$BASE/cap-original.txt"
restore() {
  printf '%d' "$CAP_ORIG" | sudo tee $H/power1_cap >/dev/null 2>&1
  bash $SCRIPTS/preconditions.sh > "$BASE/estado-restaurado.txt" 2>&1
  echo "restored cap=$CAP_ORIG -> $(cat $H/power1_cap)"
}
trap restore EXIT

cool() {
  local target=$1; local waited=0
  while :; do
    local t=$(( $(cat $H/temp1_input) / 1000 ))
    [ "$t" -le "$target" ] && break
    [ "$waited" -ge 240 ] && { echo "cooldown timeout (t=${t}C)"; break; }
    sleep 5; waited=$((waited+5))
  done
  echo "cooldown done t=$(( $(cat $H/temp1_input) / 1000 ))C (waited=${waited}s)"
}

ENV='-u MESA_CUSTOM -u LD_LIBRARY_PATH -u LIBGL_DRIVERS_PATH -u VK_ICD_FILENAMES DRI_PRIME=1'
J="env $ENV glmark2 -s 640x480 -b jellyfish:duration=15"
P="env $ENV vkmark -s 640x480 -b shading:shading=phong:duration=15"
D="env $ENV vkmark -s 640x480 -b shading"
J1080="env $ENV glmark2 -s 1920x1080 -b jellyfish:duration=15"

R=0
for cap in 25 28 32 35; do
  cool 50
  echo "===== ESTADO cap=${cap}W start temp=$(( $(cat $H/temp1_input)/1000 ))C ====="
  bash $SCRIPTS/set_cap.sh $((cap*1000000))
  for tr in 1 2; do
    R=$((R+1))
    bash $SCRIPTS/run_one.sh "$BASE/run-$(printf %02d $R)" "cap${cap}-J-640-r${tr}" "$J"
  done
  for tr in 1 2; do
    R=$((R+1))
    bash $SCRIPTS/run_one.sh "$BASE/run-$(printf %02d $R)" "cap${cap}-P-640-r${tr}" "$P"
  done
  for tr in 1 2; do
    R=$((R+1))
    bash $SCRIPTS/run_one.sh "$BASE/run-$(printf %02d $R)" "cap${cap}-D-640-r${tr}" "$D"
  done
  if [ "$cap" = "25" ] || [ "$cap" = "35" ]; then
    for tr in 1 2; do
      R=$((R+1))
      bash $SCRIPTS/run_one.sh "$BASE/run-$(printf %02d $R)" "cap${cap}-J-1080-r${tr}" "$J1080"
    done
  fi
  echo "===== ESTADO cap=${cap}W end temp=$(( $(cat $H/temp1_input)/1000 ))C ====="
done
echo "TOTAL_RUNS=$R"

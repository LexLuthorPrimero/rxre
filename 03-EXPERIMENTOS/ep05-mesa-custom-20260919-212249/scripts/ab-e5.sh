#!/usr/bin/env bash
set +e
# HISTÓRICO / NO VERIFICABLE: /tmp/opencode/ep05_base.txt ya no existe (artefacto
# volátil no preservado; no reconstruido). EP05 queda vacío → este script ya no es
# reejecutable tal cual. No sustituir por una ruta inventada.
EP05=$(cat /tmp/opencode/ep05_base.txt)
SCR="$EP05/scripts"
CUSTOM=/opt/mesa-26.2.2-rx550-haswell
R=/sys/class/drm/card1/device/hwmon/hwmon2
tmp(){ echo $(( $(cat $R/temp1_input)/1000 )); }

GL_CUSTOM=(env MESA_CUSTOM="$CUSTOM" LD_LIBRARY_PATH="$CUSTOM/lib64" LIBGL_DRIVERS_PATH="$CUSTOM/lib64/dri" DRI_PRIME=1 glmark2 --fullscreen --reuse-context -s 1920x1080)
GL_STOCK=(env -u MESA_CUSTOM -u LD_LIBRARY_PATH -u LIBGL_DRIVERS_PATH -u VK_ICD_FILENAMES DRI_PRIME=1 glmark2 --fullscreen --reuse-context -s 1920x1080)
VK_CUSTOM_ENV=(env VK_ICD_FILENAMES="$CUSTOM/share/vulkan/icd.d/radeon_icd.x86_64.json"
VK_STOCK_ENV=(env VK_ICD_FILENAMES=/usr/share/vulkan/icd.d/radeon_icd.x86_64.json

echo "inicio temp=$(tmp)C cap=$(cat $R/power1_cap)"
runs=0
for rep in 1 2; do
  for scene_info in "A:desktop:GL" "B:jellyfish:GL" "C:shading:VK"; do
    IFS=':' read -r lbl scene kind <<< "$scene_info"
    if [ "$kind" = "GL" ]; then
      CUS=("${GL_CUSTOM[@]}" -b "$scene:duration=15")
      STK=("${GL_STOCK[@]}" -b "$scene:duration=15")
    else
      CUS=("${VK_CUSTOM_ENV[@]}" vkmark -p immediate -s 1920x1080 -b "$scene:duration=15")
      STK=("${VK_STOCK_ENV[@]}" vkmark -p immediate -s 1920x1080 -b "$scene:duration=15")
    fi
    echo ">> [$lbl/re$rep] CUSTOM  T=$(tmp)C";  bash "$SCR/run_one.sh" "$EP05/runs/$lbl-custom-r$rep"  "$lbl-custom-r$rep" "${CUS[@]}"
    echo ">> [$lbl/re$rep] STOCK   T=$(tmp)C";  bash "$SCR/run_one.sh" "$EP05/runs/$lbl-stock-r$rep"  "$lbl-stock-r$rep"  "${STK[@]}"
    runs=$((runs+2))
  done
done
echo "== recorrido completado: $runs runs, temp final=$(tmp)C =="

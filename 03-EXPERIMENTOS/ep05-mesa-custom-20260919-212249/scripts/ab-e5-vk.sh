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

VK_CUSTOM_ENV=(env VK_ICD_FILENAMES="$CUSTOM/share/vulkan/icd.d/radeon_icd.x86_64.json")
VK_STOCK_ENV=(env VK_ICD_FILENAMES=/usr/share/vulkan/icd.d/radeon_icd.x86_64.json)

echo "reinicio VK A/B; temp=$(tmp)C"
for rep in 1 2; do
  CUS=("${VK_CUSTOM_ENV[@]}" vkmark -p immediate -s 1920x1080 -b "shading:duration=15")
  STK=("${VK_STOCK_ENV[@]}" vkmark -p immediate -s 1920x1080 -b "shading:duration=15")
  echo ">> [C/re$rep] CUSTOM T=$(tmp)C"; bash "$SCR/run_one.sh" "$EP05/runs/C-custom-r$rep" "C-custom-r$rep" "${CUS[@]}"
  echo ">> [C/re$rep] STOCK  T=$(tmp)C"; bash "$SCR/run_one.sh" "$EP05/runs/C-stock-r$rep"  "C-stock-r$rep"  "${STK[@]}"
done
echo "== VK A/B completo, temp final=$(tmp)C =="

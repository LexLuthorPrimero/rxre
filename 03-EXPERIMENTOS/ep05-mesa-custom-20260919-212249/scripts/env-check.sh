#!/usr/bin/env bash
set +e
EP05=$(cat /tmp/opencode/ep05_base.txt)
CUSTOM=/opt/mesa-26.2.2-rx550-haswell
echo "== EP-05 pre-check de entorno (read-only) =="
echo "fecha: $(date +%FT%T%z)"
uname -r
echo "POWER1_CAP: $(cat /sys/class/drm/card1/device/hwmon/hwmon2/power1_cap)"
echo "DPM: $(cat /sys/class/drm/card1/device/power_dpm_force_performance_level)"
echo "temp inicial: $(( $(cat /sys/class/drm/card1/device/hwmon/hwmon2/temp1_input)/1000 ))C"
echo "kalm procs: $(pgrep -af -i kalm | wc -l)"
echo
echo "--- Mesa stock en RX550 (renderer, DRI_PRIME=1) ---"
env -u MESA_CUSTOM -u LD_LIBRARY_PATH -u LIBGL_DRIVERS_PATH -u VK_ICD_FILENAMES DRI_PRIME=1 \
  glxinfo -B 2>/dev/null | grep -E 'OpenGL vendor|OpenGL renderer|OpenGL version'
echo "--- Mesa CUSTOM en RX550 (renderer, DRI_PRIME=1) ---"
env MESA_CUSTOM="$CUSTOM" LD_LIBRARY_PATH="$CUSTOM/lib64" LIBGL_DRIVERS_PATH="$CUSTOM/lib64/dri" DRI_PRIME=1 \
  glxinfo -B 2>/dev/null | grep -E 'OpenGL vendor|OpenGL renderer|OpenGL version'
echo "--- libs que carga glmark2 CUSTOM (ldd, resolviendo en custom) ---"
env LD_LIBRARY_PATH="$CUSTOM/lib64" LIBGL_DRIVERS_PATH="$CUSTOM/lib64/dri" \
  ldd $(command -v glmark2) 2>/dev/null | grep -E "mesa|gallium|GLX" | head
echo
echo "--- VK device con VK_ICD_FILENAMES custom ---"
env VK_ICD_FILENAMES="$CUSTOM/share/vulkan/icd.d/radeon_icd.x86_64.json" \
  timeout 15 vkmark -s 320x240 -b clear:duration=1 2>&1 | grep -iE 'Device Name|Device ID' | head -6
echo "--- VK device stock (sin selector) ---"
env -u MESA_VK_DEVICE_SELECT -u VK_ICD_FILENAMES \
  timeout 15 vkmark -s 320x240 -b clear:duration=1 2>&1 | grep -iE 'Device Name|Device ID' | head -6
echo "done"
#!/usr/bin/env bash
# Fase A - captura read-only de precondiciones (solo lectura de /sys,/proc,estado)
D=/sys/class/drm/card1/device
H=$D/hwmon/hwmon2

echo "===== PRECONDICIONES GLOBALES ====="
echo "date: $(date -Is)"
echo "kernel: $(uname -r)"
echo "x_session_type: ${XDG_SESSION_TYPE:-NA}  xdg_desktop: ${XDG_CURRENT_DESKTOP:-NA}  wayland: ${WAYLAND_DISPLAY:-NA}  display: ${DISPLAY:-NA}"
echo "pci: $(lspci -nnk 2>/dev/null | grep -A3 '1002:699f' | head -4 | tr '\n' ' ')"
echo
echo "===== DRM ====="
ls -l /sys/class/drm/ | grep -- '->' | grep -- 'card'
echo "===== POWER / RUNTIME-PM ====="
echo "device/power/control: $(cat $D/power/control 2>/dev/null || echo NA)"
echo "device/power/runtime_status: $(cat $D/power/runtime_status 2>/dev/null || echo NA)"
echo "card1/power/runtime_status: $(cat /sys/class/drm/card1/power/runtime_status 2>/dev/null || echo NA)"
echo "card1/power/control: $(cat /sys/class/drm/card1/power/control 2>/dev/null || echo NA)"
echo
echo "===== DPM ====="
echo "power_dpm_force_performance_level: $(cat $D/power_dpm_force_performance_level 2>/dev/null || echo NA)"
echo "power_dpm_state: $(cat $D/power_dpm_state 2>/dev/null || echo NA)"
echo "pp_power_profile_mode (activo): $(cat $D/pp_power_profile_mode 2>/dev/null | grep -F '*' | tr '\n' ' ')"
echo
echo "pp_dpm_sclk:"
cat $D/pp_dpm_sclk 2>/dev/null | tr '\n' ' '
echo
echo "pp_dpm_mclk:"
cat $D/pp_dpm_mclk 2>/dev/null | tr '\n' ' '
echo
if [ -e $D/pp_od_clk_voltage ]; then
  echo "pp_od_clk_voltage:"
  cat $D/pp_od_clk_voltage
else
  echo "pp_od_clk_voltage: MISSING"
fi
[ -e $D/ppfeatures ] && { echo "ppfeatures:"; cat $D/ppfeatures | tr '\n' ' '; echo; } || echo "ppfeatures: MISSING"
[ -e $D/pp_table ] && echo "pp_table present: $(wc -c < $D/pp_table) bytes" || echo "pp_table: MISSING"
[ -e $D/pp_power_profile_mode ] && echo "pp_power_profile_mode file: OK"
echo
echo "===== HWMON ====="
echo "freq1_input: $(cat $H/freq1_input 2>/dev/null || echo NA) Hz"
echo "freq2_input: $(cat $H/freq2_input 2>/dev/null || echo NA) Hz"
echo "power1_input: $(cat $H/power1_input 2>/dev/null || echo NA) uW"
[ -e $H/power1_average ] && echo "power1_average: $(cat $H/power1_average) uW" || echo "power1_average: MISSING"
echo "power1_cap: $(cat $H/power1_cap 2>/dev/null || echo NA)"
echo "power1_cap_min: $(cat $H/power1_cap_min 2>/dev/null || echo NA)"
echo "power1_cap_max: $(cat $H/power1_cap_max 2>/dev/null || echo NA)"
echo "temp1_input: $(cat $H/temp1_input 2>/dev/null || echo NA) mC"
echo "gpu_busy_percent: $(cat $D/gpu_busy_percent 2>/dev/null || echo NA) %"
echo "mem_busy_percent: $(cat $D/mem_busy_percent 2>/dev/null || echo NA) %"
echo
echo "===== KALM ====="
echo "kalm-gpu.service: $(systemctl is-active kalm-gpu.service 2>/dev/null || echo NA)"
echo "procesos kalm: $(ps -e -o comm= | grep -i kalm | tr '\n' ' ' || echo 'none')"
echo
echo "===== ENV RELEVANTE (proceso actual, heredado por el benchmark) ====="
env | grep -iE '^(DRI_PRIME|MESA_|RADV_|VKD3D_|AMD_|VK_ICD|LIBGL|EGL_|WLR_)=' || echo "(ninguna variable MESA_/RADV_/VKD3D_/DRI/AMD/ICD seteada)"
echo
echo "===== GPU UTILIZADA POR BENCH (de stdout del bench) ====="
echo "GL: se fuerza con DRI_PRIME=1; VK: se fuerza con MESA_VK_DEVICE_SELECT=1002:699f"
echo
echo "===== VERSIONES ====="
echo "glmark2: $(glmark2 --version 2>&1 | head -1)"
echo "vkmark: 2025.01 (--version no soportado)"
echo "mesa sistema: $(rpm -q mesa-vulkan-drivers mesa-dri-drivers 2>/dev/null | tr '\n' ' ')"
echo
echo "===== RESOLUCION / DISPLAY ====="
echo "display resol: $([ -n "$WAYLAND_DISPLAY" ] && (wlr-randr 2>/dev/null | grep -m1 current || echo 'wlr-randr no disponible'))"
echo "compositor: $(ps -e -o comm= | grep -iE 'kwin|sway|mutter|gnome-shell' | tr '\n' ' ')"
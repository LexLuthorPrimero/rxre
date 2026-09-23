#!/usr/bin/env bash
# Fase B - setea power1_cap (unico write autorizado) y lo verifica
H=/sys/class/drm/card1/device/hwmon/hwmon2
W=$1
printf '%d' "$W" | sudo tee "$H/power1_cap" >/dev/null
sleep 0.3
CUR=$(cat $H/power1_cap)
echo "set_cap: pedido=$W aplicado=$CUR"
[ "$CUR" = "$W" ] || exit 1

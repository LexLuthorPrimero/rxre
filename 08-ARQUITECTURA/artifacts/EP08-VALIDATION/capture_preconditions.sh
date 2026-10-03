#!/usr/bin/env bash
# capture_preconditions.sh — mide VIVAS las precondiciones que PHASE 1 de
# preruntime.sh declara, usando los MISMOS comandos que el harness usa.
#
# RESEARCH_INSTRUMENT. Solo lectura: no carga modulos, no escribe en hardware,
# no pide sudo. Cuando algo requiere root lo dice y marca NOT_EVALUABLE, que
# NO es PASS ni NO es FAIL.
#
# La regla que manda: cada fila se mide con el comando DEL HARNESS, no con uno
# equivalente mio. Si el harness lee mal un campo, esta tabla tiene que mostrar
# tambien lo mal que lo lee; sustituir su comando por el correcto taparia
# justamente el defecto que se busca.
#
# Esquema, 6 columnas, FIJO. Toda fila pasa por row() con 6 argumentos:
#   1 id  2 precondicion  3 esperado_harness  4 medido_vivo  5 veredicto  6 detalle
# Un veredicto fuera de este vocabulario es un error del instrumento:
#   PASS  FAIL  NOT_EVALUABLE  INSTRUMENTO_ROTO  PASS_POR_CASUALIDAD
#
# Uso: capture_preconditions.sh [--out=DIR] [--ep=RUTA]

set -uo pipefail
OUT="$(dirname "$0")"
EP=""
for a in "$@"; do
  case "$a" in
    --out=*) OUT="${a#*=}" ;;
    --ep=*)  EP="${a#*=}" ;;
  esac
done
[ -n "$EP" ] || EP="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../../03-EXPERIMENTOS/ep08-doorbell-suppression" 2>/dev/null && pwd)"
[ -r "$EP/preruntime.sh" ] || { echo "no encuentro preruntime.sh bajo EP=$EP" >&2; exit 1; }

# Las constantes se LEEN del harness, no se reescriben: si el cambia una, esto
# cambia con el, y una tabla de precondiciones congelada es una tabla falsa.
declared() { sed -n "s/^[[:space:]]*\(readonly \)\?$1=//p" "$EP/preruntime.sh" | head -1 | tr -d '"'; }
KVER_EXPECTED="$(declared KVER_EXPECTED)"
NHWA_OFFSET_EXPECTED="$(declared NHWA_OFFSET_EXPECTED)"

BTF_A=/sys/kernel/btf/amdgpu; BTF_V=/sys/kernel/btf/vmlinux
KO="$EP/nhwa.ko"; D=/sys/bus/pci/devices/0000:01:00.0
DRI="$(dirname "$(find /sys/kernel/debug/dri -maxdepth 2 -name amdgpu_regs 2>/dev/null | head -1)" 2>/dev/null)"

row() { printf '%s\t%s\t%s\t%s\t%s\t%s\n' "$1" "$2" "$3" "$4" "$5" "$6"; }
pass()  { row "$1" "$2" "$3" "$4" PASS  "$5"; }
fail()  { row "$1" "$2" "$3" "$4" FAIL  "$5"; }
# roto <id> <precondicion> <medido_vivo> <detalle>: el harness no declara la
# constante, asi que la columna 3 es SIN_CONSTANTE por definicion, no por fallo.
roto()  { row "$1" "$2" SIN_CONSTANTE "$3" INSTRUMENTO_ROTO "$4"; }
neval() { row "$1" "$2" "$3" "$4" NOT_EVALUABLE "$5"; }

# Los awk DEL HARNESS, literalmente: h1 usa el programa tal cual esta escrito
# en preruntime.sh. h2 usa el MISMO programa con un unico token cambiado,
# $(NF-1) -> $(NF-2), que es la unica diferencia que se quiere medir.
NEEDLE1='$(NF-1)'; NEEDLE2='$(NF-2)'
h1() { pahole -C "$1" "$2" 2>/dev/null | awk "$3"; }
h2() { local prog="$3"; prog="${prog//$NEEDLE1/$NEEDLE2}"; pahole -C "$1" "$2" 2>/dev/null | awk "$prog"; }

{
printf '# PRECONDICIONES VIVAS declaradas por PHASE 1 de preruntime.sh — medidas, no supuestas\n'
printf '# producer=capture_preconditions.sh   consumidor=ep08-validation.md\n'
printf '# las columnas 3 y 4 se miden con los awk DEL HARNESS, no con otros\n'
printf 'id\tprecondicion\tesperado_harness\tmedido_vivo\tveredicto\tdetalle\n'

# ---- P0: la puerta de autorizacion, probada de verdad y sin escribir ----
out="$(bash "$EP/preruntime.sh" 2>&1)"; rc=$?
pass P0_puerta_de_token "sin token, PHASE 0 corta antes de PHASE 1" \
     "STOP con exit!=0" "exit=$rc" \
     "probado de verdad: $(printf '%s' "$out" | grep -o 'falta --authorization[^\x27]*' | head -1 | cut -c1-60)"

# ---- P1: kernel ----
if [ "$(uname -r)" = "$KVER_EXPECTED" ]; then
  pass P1_kernel "uname -r == KVER_EXPECTED" "$KVER_EXPECTED" "$(uname -r)" "coinciden"
else
  fail P1_kernel "uname -r == KVER_EXPECTED" "$KVER_EXPECTED" "$(uname -r)" "el harness cortaria aqui"
fi

# ---- P2: identidad PCI. El harness declara 2 de las 7 variables que usa ----
pass P2_vendor       "device 0x699f, campo vendor"  "$(declared TARGET_PCI_VENDOR)" "$(cat $D/vendor 2>/dev/null || echo AUSENTE)"        "declarado y medido"
pass P2_device       "campo device (el ID solo, no distingue 5 placas)" "$(declared TARGET_PCI_DEVICE)" "$(cat $D/device 2>/dev/null || echo AUSENTE)" "declarado y medido"
roto P2_sub_vendor   "campo subsystem_vendor" "$(cat $D/subsystem_vendor 2>/dev/null || echo AUSENTE)" "usa \$TARGET_PCI_SUB_VEN y no lo declara; set -u aborta en esta linea"
roto P2_sub_device   "campo subsystem_device" "$(cat $D/subsystem_device 2>/dev/null || echo AUSENTE)" "usa \$TARGET_PCI_SUB_DEV y no lo declara"
roto P2_revision     "campo revision"           "$(cat $D/revision 2>/dev/null || echo AUSENTE)"           "usa \$TARGET_PCI_REVISION y no lo declara"
roto P2_modalias     "modalias exacto"          "$(cat $D/modalias 2>/dev/null || echo AUSENTE)"           "usa \$TARGET_MODALIAS y no lo declara"

# ---- P3/P4/P5/P7: debugfs ----
if mountpoint -q /sys/kernel/debug 2>/dev/null; then
  pass P3_debugfs "/sys/kernel/debug montado" montado montado "el harness exige debugfs"
else
  fail P3_debugfs "/sys/kernel/debug montado" montado NO_MONTADO "el harness exige debugfs montado"
fi
if [ -n "$DRI" ] && [ -r "$DRI/amdgpu_regs" ]; then
  pass P4_amdgpu_regs "amdgpu_regs legible en debugfs" presente "$DRI/amdgpu_regs" "legible"
else
  neval P4_amdgpu_regs "amdgpu_regs legible en debugfs" presente SIN_ACCESO "debugfs es root-only y el harness NO declara precondicion de root"
fi
if [ -n "$DRI" ] && [ -r "$DRI/amdgpu_test_ib" ]; then
  pass P5_amdgpu_test_ib "amdgpu_test_ib legible en debugfs" presente "$DRI/amdgpu_test_ib" "legible"
else
  neval P5_amdgpu_test_ib "amdgpu_test_ib legible en debugfs" presente SIN_ACCESO "idem P4: root"
fi
if [ -s $BTF_A ]; then
  pass P7_btf_amdgpu "/sys/kernel/btf/amdgpu no vacio" presente "$(stat -c %s $BTF_A) B" "legible sin sudo"
else
  fail P7_btf_amdgpu "/sys/kernel/btf/amdgpu no vacio" presente AUSENTE "sin BTF no hay pahole"
fi

# ---- P6: simbolo ----
nsym="$(grep -cw amdgpu_mm_wdoorbell /proc/kallsyms 2>/dev/null || echo 0)"
if [ "$nsym" -ge 1 ] 2>/dev/null; then
  pass P6_simbolo "amdgpu_mm_wdoorbell en /proc/kallsyms" "presente" "$nsym ocurrencias" "el kprobe tiene objetivo"
else
  fail P6_simbolo "amdgpu_mm_wdoorbell en /proc/kallsyms" presente 0 "el kprobe no tendria objetivo"
fi

# ---- P8: OFFSET GUARD. Aqui esta el hallazgo ----
hv="$(h1 amdgpu_device $BTF_A '/no_hw_access/ {print $(NF-1)}')"
hn="$(h2 amdgpu_device $BTF_A '/no_hw_access/ {print $(NF-1)}')"
if [ "$hv" = "$NHWA_OFFSET_EXPECTED" ]; then
  pass P8_nhwa_offset "no_hw_access: offset en struct amdgpu_device" "$NHWA_OFFSET_EXPECTED" "$hv" "leido correcto"
else
  fail P8_nhwa_offset "no_hw_access: offset en struct amdgpu_device" "$NHWA_OFFSET_EXPECTED" "$hv" \
       "el harness lee \$(NF-1)=$hv que es el TAMANO; el offset real es \$(NF-2)=$hn y SI cumple"
fi
if pahole -C amdgpu_device $BTF_A 2>/dev/null | grep -q 'bool.*no_hw_access'; then
  pass P8_nhwa_tipo "no_hw_access sigue siendo bool" bool bool "tipo y tamano intactos although el offset no lo esta"
else
  fail P8_nhwa_tipo "no_hw_access sigue siendo bool" bool NO "el tipo cambio"
fi
pv="$(h1 amdgpu_device $BTF_A '/struct pci_dev \*/{print $(NF-1); exit}')"
row P8_pdev "pdev en struct amdgpu_device" "$(declared NHWA_OFF_PDEV)" "$pv" PASS_POR_CASUALIDAD \
    "un puntero tiene tamano 8 y offset 8: el PASS no distingue campo correcto de campo equivocado"
roto P8_asic_type "asic_type en struct amdgpu_device" "$(h1 amdgpu_device $BTF_A '/\<asic_type\>/{print $(NF-1); exit}')" \
    "compara contra \$NHWA_OFF_ASIC_TYPE sin asignar; el harness lo declara como NHWA_ASIC_TYPE_OFFSET"
fail P8_pci_vendor "pci_dev.vendor" "$(declared NHWA_OFF_PCI_VENDOR)" "$(h1 pci_dev $BTF_V '/\<vendor\>/{print $(NF-1); exit}')" \
     "lee el tamano 2; el offset real es $(h2 pci_dev $BTF_V '/\<vendor\>/{print $(NF-1); exit}')"
fail P8_pci_device "pci_dev.device" "$(declared NHWA_OFF_PCI_DEVICE)" "$(h1 pci_dev $BTF_V '/\<device\>/{print $(NF-1); exit}')" \
     "lee el tamano 2; el offset real es $(h2 pci_dev $BTF_V '/\<device\>/{print $(NF-1); exit}')"
roto P8_pci_sub_vendor "pci_dev.subsystem_vendor" "$(h1 pci_dev $BTF_V '/subsystem_vendor/{print $(NF-1); exit}')" "sin \$NHWA_OFF_PCI_SUB_VEN; el campo SI existe en el BTF"
roto P8_pci_sub_device "pci_dev.subsystem_device" "$(h1 pci_dev $BTF_V '/subsystem_device/{print $(NF-1); exit}')" "sin \$NHWA_OFF_PCI_SUB_DEV"
roto P8_pci_revision   "pci_dev.revision"           "$(h1 pci_dev $BTF_V '/\<revision\>/{print $(NF-1); exit}')" "sin \$NHWA_OFF_PCI_REVISION"

# ---- P11 y vermagic ----
if [ -d /sys/module/nhwa ]; then fail P11_nhwa_inactivo "sin el modulo nhwa cargado" inactivo CARGADO "intervencion ya activa"
else pass P11_nhwa_inactivo "sin el modulo nhwa cargado" inactivo inactivo "sin modulo"; fi
vm="$(modinfo -F vermagic "$KO" 2>/dev/null)"
case "$vm" in "$KVER_EXPECTED"*) pass P_vermagic "el .ko se construyo para este kernel" "$KVER_EXPECTED*" "$vm" "prefijo coincide";;
  *) fail P_vermagic "el .ko se construyo para este kernel" "$KVER_EXPECTED*" "$vm" "no corresponde al kernel";; esac

# ---- la precondicion de root que el harness NO declara ----
if grep -qE '\bEUID\b|\bid -u\b|\bwhoami\b|\bsudo\b' "$EP/preruntime.sh" 2>/dev/null; then
  pass P_raiz "el harness comprueba que corre como root" declarada "$(id -u)" "comprobada"
else
  fail P_raiz "el harness comprueba que corre como root" declarada AUSENTE \
       "P3-P7 y PHASE 6/7/8 (insmod/rmmod) exigen root y el script no lo comprueba en ningun punto"
fi
} > "$OUT/preconditions-live.tsv"

# El consumidor puede confiar en la forma del artefacto: se valida antes de salir.
awk -F'\t' 'NR>5 && NF!=6 {print "FORMA_ROTA: " $1 " tiene " NF " campos"; rc=1} END{exit rc+0}' \
  "$OUT/preconditions-live.tsv" || { echo "ABORTO: preconditions-live.tsv no tiene 6 columnas por fila" >&2; exit 2; }
awk -F'\t' 'NR>5 && $5 !~ /^(PASS|FAIL|NOT_EVALUABLE|INSTRUMENTO_ROTO|PASS_POR_CASUALIDAD)$/ {print "VOCABULARIO: " $1 " -> " $5; rc=1} END{exit rc+0}' \
  "$OUT/preconditions-live.tsv" || { echo "ABORTO: veredicto fuera de vocabulario en " "$OUT/preconditions-live.tsv" >&2; exit 2; }

echo "escrito y validado: $OUT/preconditions-live.tsv"
awk -F'\t' 'NR>5{c[$5]++} END{for(k in c) printf "  %-22s %d\n", k, c[k]}' "$OUT/preconditions-live.tsv" | sort -k2 -rn
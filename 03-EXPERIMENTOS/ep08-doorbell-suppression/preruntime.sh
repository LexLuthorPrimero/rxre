#!/usr/bin/env bash
# preruntime.sh — procedimiento del discriminante DOORBELL / WPTR-POLLING.
#
# NO EJECUTADO. Preparado y revisado; pendiente de autorización humana.
#
# Uso (sólo tras autorización):
#     ./preruntime.sh --authorization=<TOKEN> --phase=<N>
#
# El módulo no se carga al importar este script. No hay traps que toquen el
# hardware fuera de las fases explícitas.
#
# ---------------------------------------------------------------------------
# REGLAS QUE NO SE ROMPEN
# ---------------------------------------------------------------------------
#  1. A es puerta. B no corre si A no produjo la evidencia TEXTUAL exacta.
#     exit code == 0 NO es sustituto.
#  2. rollback != rmmod. El byte pertenece a struct amdgpu_device, no al
#     módulo. rmmod NO restaura no_hw_access. Ver PHASE 8/10.
#  3. no_hw_access NO es observable directamente desde userspace. Su
#     verificación es COMPORTAMENTAL: ver PHASE 10.
#  4. El offset NO se recalcula aquí. P8 lo verifica; si cambia, STOP.

set -euo pipefail

# ---------------------------------------------------------------------------
# CONSTANTES VERIFICADAS
# ---------------------------------------------------------------------------
KVER_EXPECTED="7.1.3-200.nobara.fc44.x86_64"

# Offsets GFX8.1 — drivers/gpu/drm/amd/include/asic_reg/gca/gfx_8_1_d.h
# El byte offset de amdgpu_regs es (offset de registro << 2).
readonly OBS_GRBM_STATUS2=0x8008          # mmGRBM_STATUS2  0x2002
readonly OBS_GRBM_STATUS=0x8010           # mmGRBM_STATUS   0x2004
readonly OBS_CP_BUSY_STAT=0x867C          # mmCP_BUSY_STAT  0x219f
readonly OBS_CP_RB0_RPTR=0x8700           # mmCP_RB0_RPTR   0x21c0
readonly OBS_CP_RB0_WPTR=0xC114           # mmCP_RB0_WPTR   0x3045
readonly OBS_CP_RB_DOORBELL_CONTROL=0xC164 # mmCP_RB_DOORBELL_CONTROL 0x3059

# Offset de no_hw_access, desde /sys/kernel/btf/amdgpu del kernel EN EJECUCION
readonly NHWA_OFFSET_EXPECTED=381969      # 0x5D411
readonly NHWA_OFFSET_HEX="0x5D411"
readonly NHWA_ASIC_TYPE_OFFSET=1640
readonly NHWA_ASIC_POLARIS12=17
readonly NHWA_OFF_PDEV=8
readonly NHWA_OFF_PCI_VENDOR=60
readonly NHWA_OFF_PCI_DEVICE=62

# Identidad PCI EXACTA del dispositivo objetivo (ver PRE2).
readonly TARGET_PCI_VENDOR="0x1002"
readonly TARGET_PCI_DEVICE="0x699f"

# Prefijo de texto que constitutes la ÚNICA evidencia válida de ejecución
readonly TEST_PASS_LITERAL="ib ring tests passed."

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
KO="$HERE/nhwa.ko"
LOGDIR="$HERE/logs"
DRI=""

# ---------------------------------------------------------------------------
# UTILIDADES
# ---------------------------------------------------------------------------
say()  { printf '\n\033[1m== %s\033[0m\n' "$*"; }
info() { printf '   %s\n' "$*"; }
die()  { printf '\n\033[1;31mSTOP: %s\033[0m\n' "$*" >&2; exit 1; }

# read_reg <byte_offset> <nombre>  -> imprime el dword little-endian
read_reg() {
  local off="$1" name="$2" v
  v=$(python3 - "$DRI/amdgpu_regs" "$off" <<'PY'
import os, sys
fd = os.open(sys.argv[1], os.O_RDONLY)
print(int.from_bytes(os.pread(fd, 4, int(sys.argv[2])), "little"))
PY
) || die "fallo leyendo $name en $DRI/amdgpu_regs"
  LAST_VALUE[$name]="$v"
  printf '   %-22s @0x%05X = 0x%08X  (%u)\n' "$name" "$off" "$v" "$v"
}

declare -A LAST_VALUE=()
declare -A SNAP=()

# capture <etiqueta>  -> vuelca los observables y los guarda para comparar
capture() {
  local tag="$1"
  say "OBSERVABLES [$tag]"
  read_reg "$OBS_GRBM_STATUS2"           GRBM_STATUS2
  read_reg "$OBS_GRBM_STATUS"            GRBM_STATUS
  read_reg "$OBS_CP_BUSY_STAT"           CP_BUSY_STAT
  read_reg "$OBS_CP_RB0_RPTR"            CP_RB0_RPTR
  read_reg "$OBS_CP_RB0_WPTR"            CP_RB0_WPTR
  read_reg "$OBS_CP_RB_DOORBELL_CONTROL" CP_RB_DOORBELL_CONTROL
  local k
  for k in GRBM_STATUS2 GRBM_STATUS CP_BUSY_STAT CP_RB0_RPTR CP_RB0_WPTR CP_RB_DOORBELL_CONTROL; do
    SNAP["$tag.$k"]="${LAST_VALUE[$k]}"
  done
  info "ACCEL_WORKING: $(accel_working)"
}

# accel_working — el camino de lectura MMIO del driver responde
accel_working() {
  if [ -n "$DRI" ] && [ -r "$DRI/amdgpu_regs" ]; then echo "yes (amdgpu_regs responde)"; else echo "NO"; fi
}

probe_state() {
  if [ -d /sys/module/nhwa ]; then echo "ACTIVE"; else echo "inactive"; fi
}

run_test_ib() {
  # Devuelve la salida CRUDA. No se procesa aquí: la evidencia se evalúa
  # en validate_a() contra la cadena literal.
  cat "$DRI/amdgpu_test_ib" 2>&1
}

# ---------------------------------------------------------------------------
# PHASE 0 — verificar autorización
# ---------------------------------------------------------------------------
phase0_authorize() {
  say "PHASE 0 — autorización"
  local token="" phase="all"
  for a in "$@"; do
    case "$a" in
      --authorization=*) token="${a#*=}" ;;
      --phase=*)        phase="${a#*=}" ;;
    esac
  done
  [ -n "$token" ] || die "falta --authorization=<TOKEN>. Esta ronda NO ejecuta nada."
  [ "$token" = "RUN550-EP08" ] || die "token de autorización no reconocido"
  [ "$(uname -r)" = "$KVER_EXPECTED" ] || die "kernel cambió: $(uname -r) != $KVER_EXPECTED"
  info "autorización aceptada; kernel $KVER_EXPECTED"
  info "phase solicitada: $phase"
}

# ---------------------------------------------------------------------------
# PHASE 1 — preflight
# ---------------------------------------------------------------------------
phase1_preflight() {
  say "PHASE 1 — preflight"
  mkdir -p "$LOGDIR"

  # P1 kernel
  info "P1 kernel:        $(uname -r)"
  [ "$(uname -r)" = "$KVER_EXPECTED" ] || die "P1 FAIL: kernel inesperado"

  # P2 identidad EXACTA del dispositivo objetivo (coincidencia de 5 campos)
  #    0000:01:00.0  1002:699f  sub 1002:0b04  rev c7
  #    device 0x699f NO basta: pci.ids lista 5 tableros distintos bajo ese ID.
  local target="" found=0
  for d in /sys/bus/pci/devices/*/; do
    [ -e "$d/vendor" ] || continue
    if [ "$(cat "$d/vendor")"           = "$TARGET_PCI_VENDOR"   ] && \
       [ "$(cat "$d/device")"           = "$TARGET_PCI_DEVICE"   ] && \
       [ "$(cat "$d/subsystem_vendor")" = "$TARGET_PCI_SUB_VEN" ] && \
       [ "$(cat "$d/subsystem_device")" = "$TARGET_PCI_SUB_DEV" ] && \
       [ "$(cat "$d/revision")"         = "$TARGET_PCI_REVISION" ]; then
      target="$(basename "$d")"; found=1; break
    fi
  done
  [ "$found" = 1 ] || die "P2 FAIL: no se encuentra la identidad exacta de la tarjeta objetivo"
  info "P2 PCI:         $target  $TARGET_PCI_VENDOR:$TARGET_PCI_DEVICE / sub $TARGET_PCI_SUB_VEN:$TARGET_PCI_SUB_DEV / rev $TARGET_PCI_REVISION"
  [ "$(cat "/sys/bus/pci/devices/$target/modalias")" = "$TARGET_MODALIAS" ] \
    || die "P2 FAIL: modalias no coincide con la identidad objetivo"
  info "P2 modalias:    OK"
  [ -e "/sys/bus/pci/devices/$target/driver" ] || die "P2 FAIL: $target sin driver enlazado"
  [ "$(basename "$(readlink -f "/sys/bus/pci/devices/$target/driver")")" = "amdgpu" ] \
    || die "P2 FAIL: el driver enlazado no es amdgpu"
  info "P2 driver:      amdgpu OK"

  # P3 debugfs montado
  mountpoint -q /sys/kernel/debug || die "P3 FAIL: debugfs no montado"
  info "P3 debugfs:       montado"

  # P4/P5 entradas presentes
  DRI=$(dirname "$(find /sys/kernel/debug/dri -maxdepth 2 -name amdgpu_regs 2>/dev/null | head -1)")
  [ -n "$DRI" ] || die "P4 FAIL: amdgpu_regs no encontrado"
  info "P4 amdgpu_regs:   $DRI/amdgpu_regs"
  [ -r "$DRI/amdgpu_test_ib" ] || die "P5 FAIL: amdgpu_test_ib no encontrado"
  info "P5 amdgpu_test_ib: presente"

  # P6 símbolo enganchable
  grep -qw amdgpu_mm_wdoorbell /proc/kallsyms || die "P6 FAIL: símbolo no en kallsyms"
  info "P6 símbolo:       amdgpu_mm_wdoorbell presente"

  # P7 BTF disponible
  [ -s /sys/kernel/btf/amdgpu ] || die "P7 FAIL: sin BTF del módulo"
  info "P7 BTF:           /sys/kernel/btf/amdgpu"

  # P8 OFFSET GUARD — el guard real
  local off
  off=$(pahole -C amdgpu_device /sys/kernel/btf/amdgpu 2>/dev/null \
        | awk '/no_hw_access/ {print $(NF-1)}')
  info "P8 no_hw_access:  $off (esperado $NHWA_OFFSET_EXPECTED)"
  if [ "$off" != "$NHWA_OFFSET_EXPECTED" ]; then
    die "INVALID_PRECONDITION — offset de no_hw_access cambió a '$off'.
     STOP. No se adapta automáticamente. Re-verificar BTF y reconstruir el diseño."
  fi
  # tipo y tamaño
  pahole -C amdgpu_device /sys/kernel/btf/amdgpu 2>/dev/null | grep -q "bool.*no_hw_access" \
    || die "P8 FAIL: no_hw_access ya no es bool"
  info "P8 tipo/tamaño:   bool, 1 byte — OK"

  # offsets de la cadena de identidad, que el pre_handler también usa
  local a_pdev a_asic p_ven p_dev
  a_pdev=$(pahole -C amdgpu_device /sys/kernel/btf/amdgpu 2>/dev/null | awk '/struct pci_dev \*/{print $(NF-1); exit}')
  a_asic=$(pahole -C amdgpu_device /sys/kernel/btf/amdgpu 2>/dev/null | awk '/\<asic_type\>/{print $(NF-1); exit}')
  p_ven=$(pahole -C pci_dev /sys/kernel/btf/vmlinux 2>/dev/null | awk '/\<vendor\>/{print $(NF-1); exit}')
  p_dev=$(pahole -C pci_dev /sys/kernel/btf/vmlinux 2>/dev/null | awk '/\<device\>/{print $(NF-1); exit}')
  local p_sven p_sdev p_rev
  p_sven=$(pahole -C pci_dev /sys/kernel/btf/vmlinux 2>/dev/null | awk '/subsystem_vendor/{print $(NF-1); exit}')
  p_sdev=$(pahole -C pci_dev /sys/kernel/btf/vmlinux 2>/dev/null | awk '/subsystem_device/{print $(NF-1); exit}')
  p_rev=$(pahole -C pci_dev /sys/kernel/btf/vmlinux 2>/dev/null | awk '/\<revision\>/{print $(NF-1); exit}')
  info "P8 pdev=$a_pdev  asic_type=$a_asic  pci.vendor=$p_ven  pci.device=$p_dev"
  [ "$a_pdev" = "$NHWA_OFF_PDEV" ]      || die "INVALID_PRECONDITION — pdev ($a_pdev) != $NHWA_OFF_PDEV"
  [ "$a_asic" = "$NHWA_OFF_ASIC_TYPE" ] || die "INVALID_PRECONDITION — asic_type ($a_asic) != $NHWA_OFF_ASIC_TYPE"
  [ "$p_ven"   = "$NHWA_OFF_PCI_VENDOR" ] || die "INVALID_PRECONDITION — pci.vendor ($p_ven) != $NHWA_OFF_PCI_VENDOR"
  [ "$p_dev"   = "$NHWA_OFF_PCI_DEVICE" ] || die "INVALID_PRECONDITION — pci.device ($p_dev) != $NHWA_OFF_PCI_DEVICE"
  [ "$p_sven" = "$NHWA_OFF_PCI_SUB_VEN" ] || die "INVALID_PRECONDITION — subsystem_vendor ($p_sven)"
  [ "$p_sdev" = "$NHWA_OFF_PCI_SUB_DEV" ] || die "INVALID_PRECONDITION — subsystem_device ($p_sdev)"
  [ "$p_rev"  = "$NHWA_OFF_PCI_REVISION" ] || die "INVALID_PRECONDITION — revision ($p_rev)"
  info "P8 identidad:    cadena completa verificada (5 campos) — OK"

  # P11 sin probe residual
  [ "$(probe_state)" = "inactive" ] || die "P11 FAIL: nhwa ya cargado"
  [ ! -s /sys/kernel/debug/tracing/kprobe_events ] || info "P11 AVISO: kprobe_events no vacío"
  info "P11 probe:        $(probe_state)"

  # .ko listo y coherente
  [ -f "$KO" ] || die "P FAIL: falta $KO"
  local vm; vm=$(modinfo -F vermagic "$KO")
  case "$vm" in "$KVER_EXPECTED"*) info "P .ko vermagic:  $vm" ;;
                 *) die "P FAIL: vermagic $vm no corresponde al kernel" ;; esac
  info "P1-P11: OK"
}

# ---------------------------------------------------------------------------
# PHASE 2 — baseline
# ---------------------------------------------------------------------------
phase2_baseline() {
  say "PHASE 2 — baseline"
  capture "baseline"
  # Idle autoritativo: el predicado del propio driver (gfx_v8_0.c:4798)
  local s2 gui
  s2=$(python3 -c "import os,sys;f=os.open('$DRI/amdgpu_regs',os.O_RDONLY);print(int.from_bytes(os.pread(f,4,$OBS_GRBM_STATUS2),'little'))")
  gui=$(python3 -c "import os,sys;f=os.open('$DRI/amdgpu_regs',os.O_RDONLY);print(int.from_bytes(os.pread(f,4,$OBS_GRBM_STATUS),'little')>>31)")
  info "idle check: GRBM_STATUS2=0x$(printf %X $s2)  GUI_ACTIVE=$gui"
  [ "$s2" = "8" ]     || die "PRECONDITION FAIL: GRBM_STATUS2 != 0x8 (GPU no idle)"
  [ "$gui" = "0" ]    || die "PRECONDITION FAIL: GUI_ACTIVE != 0 (GFX activo)"
  info "GPU idle: OK (criterio del driver)"
}

# ---------------------------------------------------------------------------
# PHASE 3 — CONTROL A
# ---------------------------------------------------------------------------
phase3_control_a() {
  say "PHASE 3 — CONTROL A (doorbell normal)"
  [ "$(probe_state)" = "inactive" ] || die "A: no debe haber probe activo"
  info "no_hw_access:    0 (sinprobe)"
  capture "A-pre"
  A_OUT=$(run_test_ib)
  printf '%s\n' "$A_OUT" | tee "$LOGDIR/A-amdgpu_test_ib.txt"
  capture "A-post"
}

# ---------------------------------------------------------------------------
# PHASE 4 — validar A (puerta dura)
# ---------------------------------------------------------------------------
validate_a() {
  say "PHASE 4 — validar A"
  if ! printf '%s' "$A_OUT" | grep -qF "$TEST_PASS_LITERAL"; then
    die "A NO VALIDADO.
     Evidencia requerida (literal): '$TEST_PASS_LITERAL'
     B PROHIBIDO. No se ejecuta la intervención.
     Salida completa de A en $LOGDIR/A-amdgpu_test_ib.txt"
  fi
  info "A validado por evidencia textual literal: EXECUTION_OBSERVED"
  info "  (no se usó exit code como sustituto)"
}

# ---------------------------------------------------------------------------
# PHASE 5 — puerta de autorización para B
# ---------------------------------------------------------------------------
phase5_gate_b() {
  say "PHASE 5 — puerta de autorización para B"
  [ "${1:-}" = "--authorize-b" ] \
    || die "B requiere --authorize-b explícito. A fue válido; el diseño queda disponible."
  info "B autorizado"
}

# ---------------------------------------------------------------------------
# PHASE 6 — armar la intervención
# ---------------------------------------------------------------------------
phase6_arm() {
  say "PHASE 6 — armar intervención"
  insmod "$KO" val=1 || die "insmod falló (¿vermagic, símbolos, o amdgpu no cargado?)"
  info "nhwa cargado: val=1, probe $(probe_state)"
  info "recordar: rmmod NO restaura no_hw_access"
}

# ---------------------------------------------------------------------------
# PHASE 7 — CONTROL B
# ---------------------------------------------------------------------------
phase7_control_b() {
  say "PHASE 7 — CONTROL B (doorbell suprimido)"
  [ "$(probe_state)" = "ACTIVE" ] || die "B: probe no activo"
  capture "B-pre"
  B_OUT=$(run_test_ib)
  printf '%s\n' "$B_OUT" | tee "$LOGDIR/B-amdgpu_test_ib.txt"
  capture "B-post"
}

# ---------------------------------------------------------------------------
# PHASE 8 — DISARM
#
# REGLA: module removal != flag restoration.
# El byte pertenece a struct amdgpu_device, no al estado del módulo.
# rmmod NO restaura no_hw_access, y el módulo NO lo restaura en nhwa_exit()
# a propósito. La restauración es explícita y en dos pasos.
#
# SEMÁNTICA DE LA VENTANA rmmod -> insmod(val=0):
#
#   rmmod nhwa(val=1)
#       probe desaparece
#       no_hw_access SIGUE en 1  <-- ventana
#   insmod nhwa(val=0)
#       probe vuelve a registrarse, y escribe 0 en el PRÓXIMO doorbell
#       no_hw_access SIGUE en 1 hasta que haya un doorbell
#   amdgpu_test_ib                <-- el doorbell; aquí ocurre la restauración
#   rmmod nhwa
#       probe inactivo, no_hw_access = 0 y PERMANECE en 0
#
# Durante esa ventana el byte está en 1: NO se emite ningún doorbell, por lo
# que el driver no hace progreso de GPU. No hay trabajo nuestro pendiente
# (A terminó, y en B ya se recogió la captura), y el sistema sólo puede
# producir doorbells por actividad externa, que en un equipo aislado no la hay.
# La ventana no altera la interpretación porque la única lectura que decide
# (PHASE 10) ocurre DESPUÉS de la ventana, con el probe ya inactivo.
#
# Si el `insmod val=0` falla, el byte puede quedar en 1. Eso NO es una
# restauración: es RUNTIME_FAILURE, y el procedimiento se detiene.
# ---------------------------------------------------------------------------
phase8_disarm() {
  say "PHASE 8 — DISARM"
  # 1. retirar el módulo ARM. el byte queda en 1.
  rmmod nhwa 2>/dev/null || true
  info "nhwa(val=1) retirado. no_hw_access sigue en 1 — eso es lo esperado."
  info "VENTANA: sin probe y con no_hw_access=1 el driver no emite doorbells."

  # 2. cargar el módulo con val=0 para que el PRÓXIMO doorbell restaure el byte
  if ! insmod "$KO" val=0; then
    die "RUNTIME_FAILURE — RESTAURACIÓN FALLIDA: 'insmod val=0' no se pudo cargar.
     no_hw_access PUEDE PERMANECER EN 1.
     Esto NO es una restauración exitosa y NO habilita PHASE 9/10.
     Recuperación manual: insmod $KO val=0 ; amdgpu_test_ib ; rmmod nhwa"
  fi
  info "nhwa cargado: val=0"

  # 3. provocar un doorbell -> el probe escribe 0 y DEJA pasar el doorbell
  TRIG_OUT=$(run_test_ib)
  printf '%s\n' "$TRIG_OUT" | sed 's/^/   /'
  if ! printf '%s' "$TRIG_OUT" | grep -qF "$TEST_PASS_LITERAL"; then
    die "RUNTIME_FAILURE — RESTAURACIÓN FALLIDA: el disparo con val=0 no pasó.
     el byte puede seguir en 1. NO se continúa a PHASE 9/10.
     Recuperación manual: insmod $KO val=0 ; amdgpu_test_ib ; rmmod nhwa"
  fi
  info "byte restaurado a 0 por el probe val=0"

  # 4. retirar el módulo. el byte ya es 0 y permanece 0.
  if ! rmmod nhwa; then
    die "RUNTIME_FAILURE — rmmod falló tras restaurar. El byte es 0 pero el probe
     sigue registrado. Reintentar rmmod nhwa."
  fi
  info "nhwa retirado"
}

# ---------------------------------------------------------------------------
# PHASE 9 — probe inactivo
# ---------------------------------------------------------------------------
phase9_verify_probe() {
  say "PHASE 9 — verificar probe inactivo"
  [ "$(probe_state)" = "inactive" ] || die "PHASE 9 FAIL: probe sigue activo"
  info "probe: inactive"
}

# ---------------------------------------------------------------------------
# PHASE 10 — verificar no_hw_access == 0
#
# DIRECT_NO_HW_ACCESS_READ      = NOT_AVAILABLE
#   Ningún debugfs, registro ni ioctl expone adev->no_hw_access a userspace.
#   No se afirma una lectura directa.
# BEHAVIORAL_RESTORE_VALIDATION = AVAILABLE
#   Con no_hw_access=1 el writel de amdgpu_doorbell_mgr.c:65 no se ejecuta: el
#   ring no avanza y el test no puede pasar. Un PASS con el probe inactivo
#   implica el byte == 0.
# PHASE10_ROLE = RESTORATION_VALIDATION
#   NO es un tercer brazo experimental: no produce evidencia física.
#
# NO CIRCULAR: aquí no hay probe activo, así que el resultado depende
# exclusivamente del valor del byte, no del instrumento.
# ---------------------------------------------------------------------------
phase10_verify_flag() {
  say "PHASE 10 — verificar no_hw_access == 0"
  info "DIRECT_NO_HW_ACCESS_READ      = NOT_AVAILABLE"
  info "BEHAVIORAL_RESTORE_VALIDATION = AVAILABLE"
  info "PHASE10_ROLE = RESTORATION_VALIDATION (no es un tercer brazo)"
  info "sin probe activo; si no_hw_access fuera 1, el doorbell no llegaría"
  VERIFY_OUT=$(run_test_ib)
  printf '%s\n' "$VERIFY_OUT" | tee "$LOGDIR/verify-disarm.txt"
  if ! printf '%s' "$VERIFY_OUT" | grep -qF "$TEST_PASS_LITERAL"; then
    die "RUNTIME_FAILURE — RESTAURACIÓN NO VALIDADA: el test no pasó sin probe.
     No es un resultado físico del experimento: es un fallo de PROCEDIMIENTO.
     Recuperación: insmod $KO val=0 ; amdgpu_test_ib ; rmmod nhwa"
  fi
  info "BEHAVIORAL_RESTORE_VALIDATION = PASS => no_hw_access == 0"
  info "FINAL_PROBE_STATE = DIRECTLY_OBSERVABLE  (PHASE 9)"
  info "FINAL_FLAG_STATE  = BEHAVIORALLY_VALIDATED (NO es DIRECT_READBACK)"
}

# ---------------------------------------------------------------------------
# PHASE 11 — observables finales
# ---------------------------------------------------------------------------
phase11_final() {
  say "PHASE 11 — observables finales"
  capture "final"
  info "probe state:     $(probe_state)"
  info "no_hw_access:    0 (verificado en PHASE 10)"
}

# ---------------------------------------------------------------------------
# PHASE 12 — clasificar
#
# REGLA: un fallo del test NO es automáticamente un resultado físico.
# El código de retorno del driver aparece en la salida ("failed (-N).") y
# distingue un resultado físico de un fallo operativo:
#
#   0     EXECUTION_OBSERVED   WB == 0xDEADBEEF tras la fence
#   -22   EINVAL               la fence SEÑALÓ y el valor NO llegó
#                             => el ring fue consumido, el efecto no.
#                             Resultado físico, corroborable con RPTR.
#   -110  ETIMEDOUT            la fence NO señalizó
#                             => AMBIGUO. "no consumido" y "consumido sin
#                             efecto" son indistinguibles sólo con la fence.
#                             Sólo el RPTR puede desempatar.
#   otro  RUNTIME_FAILURE      operativo (ENOENT, ENOMEM, EBUSY...)
#                             => NO se interpreta como física.
# ---------------------------------------------------------------------------
test_code() {
  printf '%s' "$1" | sed -n 's/.*ib ring tests failed (\(-\{0,1\}[0-9]\{1,\}\)).*/\1/p' | head -1
}

phase12_classify() {
  say "PHASE 12 — clasificar"

  local a_pass=0 b_pass=0 a_code b_code
  printf '%s' "$A_OUT" | grep -qF "$TEST_PASS_LITERAL" && a_pass=1
  printf '%s' "$B_OUT" | grep -qF "$TEST_PASS_LITERAL" && b_pass=1
  b_code=$(test_code "$B_OUT")
  [ "$b_pass" = 1 ] && b_code="0"

  local rptr_a="${SNAP[A-post.CP_RB0_RPTR]:-NA}" rptr_b="${SNAP[B-post.CP_RB0_RPTR]:-NA}"
  info "A pass: $a_pass"
  info "B pass: $b_pass   B code: ${b_code:-<sin código>}"

  if [ "$a_pass" != 1 ]; then
    RESULT_CLASS="RUNTIME_FAILURE"
    cat <<EOF
   A no produjo la evidencia exigida. La clasificación NO es interpretable.
   RESULT_CLASS = RUNTIME_FAILURE
EOF
    return 1
  fi

  case "$b_code" in
    0)
      RESULT_CLASS="B3_EXECUTION_WITHOUT_DOORBELL"
      cat <<'EOF'
   B3: ejecución observada CON el doorbell suprimido (el propio test verificó
       WB == 0xDEADBEEF tras la fence).
       -> evidencia a favor de que la publicación del WPTR basta.
       NO se afirma causalidad absoluta: no se discriminó si el WPTR fue
       realmente sondeado o si otro mecanismo reaccionó a la publicación.
   RESULT_CLASS = B3_EXECUTION_WITHOUT_DOORBELL
EOF
      ;;
    -22)
      RESULT_CLASS="B1_CONSUMED_WITHOUT_EFFECT"
      cat <<EOF
   B1: la fence SEÑALÓ (el driver consumió el IB) pero el valor no llegó.
       Es un resultado FÍSICO, no un fallo operativo: -EINVAL sólo se
       devuelve en gfx_v8_0.c:915, después de un fence satisfacido.
         CP_RB0_RPTR  A-post = $rptr_a
         CP_RB0_RPTR  B-post = $rptr_b
       Compatible con "el doorbell es necesario". NO se afirma causalidad
       absoluta: no se ha discriminado qué otro mecanismo podría reactivarlo.
   RESULT_CLASS = B1_CONSUMED_WITHOUT_EFFECT
EOF
      ;;
    -110)
      # ambiguo: la fence no señalizó
      if [ "$rptr_a" != "NA" ] && [ "$rptr_b" != "NA" ] && [ "$rptr_a" = "$rptr_b" ]; then
        RESULT_CLASS="B2_NO_CONSUMPTION"
        cat <<EOF
   B2: la fence no señalizó Y CP_RB0_RPTR no se movió respecto de A-post
       ($rptr_a -> $rptr_b). BajoProbe activo y control A válido, esto es
       "no se consumió el ring".
         NO es un fallo operativo: A pasó con la misma infraestructura.
   RESULT_CLASS = B2_NO_CONSUMPTION
EOF
      else
        RESULT_CLASS="UNKNOWN_AMBIGUOUS_TIMEOUT"
        cat <<EOF
   UNKNOWN: la fence no señalizó (-110) pero CP_RB0_RPTR no permite desempatar
         CP_RB0_RPTR  A-post = $rptr_a
         CP_RB0_RPTR  B-post = $rptr_b
   Con un timeout de fence NO se puede separar "no consumido" de
   "consumido sin efecto". No se afirma ninguna de las dos.
   RESULT_CLASS = UNKNOWN_AMBIGUOUS_TIMEOUT
EOF
      fi
      ;;
    "")
      RESULT_CLASS="RUNTIME_FAILURE"
      echo "   RUNTIME_FAILURE: B no produjo salida clasificable."
      ;;
    *)
      RESULT_CLASS="RUNTIME_FAILURE"
      cat <<EOF
   RUNTIME_FAILURE: el test de B falló con el código $b_code, que NO es un
   resultado físico del experimento sino un fallo operativo
   (ENOMEM/ENOENT/EBUSY/... en amdgpu_ib_get, amdgpu_ib_schedule, o similar).
   NO se interpreta como B1 ni como B2.
   El primer objetivo de recuperación es no_hw_access = 0 (PHASE 8/10).
   RESULT_CLASS = RUNTIME_FAILURE
EOF
      ;;
  esac

  cat <<'EOF'

   Recordatorio de interpretación:
     PASS del ring test  = ejecución observada POR EL PROPIO TEST
     avance de RPTR      = consumo/progreso observado
     supresión           = intervención aplicada
     NUNCA: RPTR = ejecución.  NUNCA: fence por sí sola = ejecución.
EOF
  [ "$RESULT_CLASS" = "RUNTIME_FAILURE" ] && return 1
  return 0
}

# ---------------------------------------------------------------------------
main() {
  phase0_authorize "$@"
  local ph="all"
  for a in "$@"; do case "$a" in --phase=*) ph="${a#*=}" ;; esac; done

  if [ "$ph" = "all" ] || [ "$ph" = "1" ]; then phase1_preflight; fi
  if [ "$ph" = "all" ] || [ "$ph" = "2" ]; then phase2_baseline; fi
  if [ "$ph" = "all" ] || [ "$ph" = "3" ]; then phase3_control_a; fi
  if [ "$ph" = "all" ] || [ "$ph" = "4" ]; then validate_a; fi
  if [ "$ph" = "all" ] || [ "$ph" = "5" ]; then phase5_gate_b "$@"; fi
  if [ "$ph" = "all" ] || [ "$ph" = "6" ]; then phase6_arm; fi
  if [ "$ph" = "all" ] || [ "$ph" = "7" ]; then phase7_control_b; fi
  if [ "$ph" = "all" ] || [ "$ph" = "8" ]; then phase8_disarm; fi
  if [ "$ph" = "all" ] || [ "$ph" = "9" ]; then phase9_verify_probe; fi
  if [ "$ph" = "all" ] || [ "$ph" = "10" ]; then phase10_verify_flag; fi
  if [ "$ph" = "all" ] || [ "$ph" = "11" ]; then phase11_final; fi
  if [ "$ph" = "all" ] || [ "$ph" = "12" ]; then phase12_classify; fi

  say "fin"
  info "A: $LOGDIR/A-amdgpu_test_ib.txt"
  info "B: $LOGDIR/B-amdgpu_test_ib.txt"
  info "verificación disarm: $LOGDIR/verify-disarm.txt"
}

main "$@"

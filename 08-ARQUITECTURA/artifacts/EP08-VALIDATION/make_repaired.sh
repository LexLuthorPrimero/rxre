#!/usr/bin/env bash
# make_repaired.py — aplica la REPARACION MINIMA de preruntime.sh y emite el diff.
#
# Deliberadamente NO es un editor manual: es un guion que hace exactamente tres
# cambios y que se puede volver a ejecutar. Una reparacion que solo existe como
# diff pegado a mano no es repetible, y repetirla es justo lo que hara falta en
# cuanto el harness vuelva a necesitar cambios.
#
# Uso: make_repaired.py <original> <salida_reparada> <salida_diff>
#
# LAS TRES COSAS QUE TOCA, y por que cada una es no-circular:
#
#  1) DECLARAR 4 constantes de IDENTIDAD DE OBJETIVO.
#     Se rellenan desde registros PREVIOS y FECHADOS, no desde el sysfs de hoy:
#       TARGET_PCI_SUB_VEN   HARDWARE-FINGERPRINT.md:60  +  snapshot hermano 2026-09-19 L84
#       TARGET_PCI_SUB_DEV   HARDWARE-FINGERPRINT.md:60  +  snapshot hermano 2026-09-19 L84
#       TARGET_PCI_REVISION  HARDWARE-FINGERPRINT.md:59  +  snapshot hermano 2026-09-19 L83
#       TARGET_MODALIAS      DERIVADO de los 4 anteriores, no observado
#     Rellenar estas cuatro con lo que dice HOY /sys seria CIRCULAR: la
#     pregunta que responden es "¿es esta la placa objetivo?", y contestarla
#     con la placa que hay ahora la hace siempre cierto.
#
#  2) $(NF-1) -> $(NF-2) en las 8 extracciones de offset.
#     Con pahole v1.30 la linea termina en * /, asi que $(NF-1) es el TAMANO.
#     Medido: NF-1=1, NF-2=381969, y el offset real es 381969.
#
#  3) DECLARAR la precondicion de root.
#     El harness lee debugfs y hace insmod/rmmod: exige root en cinco sitios y
#     no lo comprueba en ninguno. Es la unica precondicion que se COMPRUEBA que
#     se anade; las otras dos son correcciones de lectura y de declaracion.
#
# LO QUE NO TOCA, a proposito:
#   - los valores de NHWA_OFFSET_EXPECTED y demas offsets de struct. Se dejan
#     como estan. Rellenarlos con la medicion de HOY seria correcto aqui y
#     circular en el otro caso, y la razon es el hecho de que el sentido de un
#     offset de struct es "linea base fechada": cualquier movimiento posterior
#     es justo lo que el guard debe detectar. Fijarlos hoy es lo que hace que
#     mañana pueda detectar algo.
#   - la semantica del experimento, el token, el orden de fases, los aborts.

set -euo pipefail
ORIG="$1"; OUT="$2"; DIFF="$3"
[ -r "$ORIG" ] || { echo "ilegible: $ORIG" >&2; exit 1; }

python3 - "$ORIG" "$OUT" <<'PY'
import sys, re
src, dst = sys.argv[1], sys.argv[2]
s = open(src, encoding='utf-8').read()
orig = s
cambios = []

# ---- 1) declarar las 4 constantes de identidad -----------------------------
ANCLA = 'readonly TARGET_PCI_DEVICE="0x699f"\n'
NUEVO = ANCLA + '''
# ---Reparacion EP08-REPAIR 2026-10-03: estas cuatro las USA el script desde la
# linea 153 y NO existian. Bajo `set -u` su ausencia es un error fatal, no un
# valor vacio, y por eso el harness abortaba en P2 antes de medir nada.
#
# PROVENIENCIA, que es lo que las hace no circulares:
#   TARGET_PCI_SUB_VEN/DEV  HARDWARE-FINGERPRINT.md:60  SUBSYS 0x1002:0x0b04
#                           + snapshot del proyecto hermano 2026-09-19 08:52:36
#                             (sha256 92d0c378ee366044a74f7480d0457224fa9fb64cf3606c3678c4c212ea430b32)
#                             linea 84: "Subsystem: ... [1002:0b04]"
#   TARGET_PCI_REVISION     HARDWARE-FINGERPRINT.md:59  REVISION 0xc7
#                           + el mismo snapshot, linea 83: "(rev c7)"
#   TARGET_MODALIAS         DERIVADO por composicion de los cuatro campos de
#                           arriba, NO observado. Por eso su comprobacion es de
#                           COHERENCIA entre campos, no de identidad: sirve para
#                           que los cinco coincidan entre si, no para anadir un
#                           quinto dato independiente.
#
# NO se han leido del sysfs de hoy. Leerlos ahi seria responder "¿es esta la
# placa?" con la placa que hay ahora.
readonly TARGET_PCI_SUB_VEN="0x1002"
readonly TARGET_PCI_SUB_DEV="0x0b04"
readonly TARGET_PCI_REVISION="0xc7"
readonly TARGET_MODALIAS="pci:v00001002d0000699Fsv00001002sd00000B04bc03sc00i00"
'''
assert ANCLA in s, "ancla de identidad no encontrada"
s = s.replace(ANCLA, NUEVO, 1)
cambios.append("1 · declarar TARGET_PCI_SUB_VEN/SUB_DEV/REVISION/MODALIAS (4 lineas)")

# ---- 1b) constantes de LAYOUT DE STRUCT: baseline fechada ------------------
# Estas SI se fijan con una medicion de HOY, y a proposito. La razon es que
# esta clase de constante y la anterior responden a preguntas opuestas:
#
#   IDENTIDAD DE OBJETIVO  "¿es esta la placa que diseñe?"
#                         -> rellenarla con el sysfs de hoy la hace siempre
#                            cierta. CIRCULAR. Viene de registros previos.
#   LAYOUT DE STRUCT      "¿el struct se ha movido desde el diseño?"
#                         -> fijarla con la medicion de HOY es lo que la
#                            convierte en linea base, y es lo unico que le
#                            permite detectar un movimiento FUTURO. NO circular.
#
# Es la misma lectura que hace el propio harness en su cabecera: "El offset NO
# se recalcula aqui. P8 lo verifica; si cambia, STOP." Es decir: el valor es
# un pin, y el guard lo que hace es compararlo.
ANCLA4 = 'readonly NHWA_OFF_PCI_DEVICE=62\n'
NUEVO4 = ANCLA4 + '''
# ---Reparacion EP08-REPAIR 2026-10-03: el script USA $NHWA_OFF_PCI_SUB_VEN,
# $NHWA_OFF_PCI_SUB_DEV y $NHWA_OFF_PCI_REVISION y no existian. Con `set -u`
# eso es un error fatal. Los tres se declaran aqui.
#
# PROVENIENCIA, y es DISTINTA de la de las constantes de identidad de arriba:
# estos tres no son identidad de la placa, son POSICIONES DE CAMPO en
# struct pci_dev. Se han medido HOY sobre el BTF del modulo en ejecucion:
#   /sys/kernel/btf/vmlinux   struct pci_dev
#   subsystem_vendor  offset 64   (2 bytes, short)
#   subsystem_device  offset 66   (2 bytes, short)
#   revision          offset 72   (1 byte,  u8)
# y se declaran con fecha a proposito: son una LINEA BASE, y lo que el guard
# tiene que detectar es que se muevan. Fijarlas hoy es lo que las hace utiles
# mañana. Rellenarlas con la identidad de la placa habria sido circular; esto
# no lo es, porque la pregunta que responden es otra.
readonly NHWA_OFF_PCI_SUB_VEN=64
readonly NHWA_OFF_PCI_SUB_DEV=66
readonly NHWA_OFF_PCI_REVISION=72

# $NHWA_OFF_ASIC_TYPE lo USA el script en P8 y no existia; el valor ya estaba
# declarado arriba con otro nombre. Se declara como alias, NO como otro numero:
# dos literales iguales en dos sitios pueden divergir sin que nada lo note, y
# este harness ya ha demostrado que leen mal los campos que compara.
readonly NHWA_OFF_ASIC_TYPE="$NHWA_ASIC_TYPE_OFFSET"
'''
assert ANCLA4 in s, "ancla de offsets no encontrada"
s = s.replace(ANCLA4, NUEVO4, 1)
cambios.append("1b · declarar NHWA_OFF_PCI_SUB_VEN/SUB_DEV/REVISION (baseline fechada "
               "de layout) y NHWA_OFF_ASIC_TYPE como alias del nombre que ya existia")

# ---- 2b) el `exit` de awk: necesario Y fatal a la vez ----------------------
# Septimo defecto, y el unico que NO es visible leyendo el codigo: sale al
# ejecutar. Las siete extracciones con awk usan `{print ...; exit}`. awk sale
# antes de que pahole termine de escribir, pahole recibe SIGPIPE, y con
# `set -o pipefail` (que el harness activa en la linea 25) la sustitucion de
# comando devuelve 141 y `set -e` mata el script. Medido:
#
#   bash -c 'set -euo pipefail; v=$(pahole ... | awk "...{print \$1; exit}"); echo ok'
#   -> exit 141, sin imprimir nada
#   bash -c 'set -eu;       v=$(pahole ... | awk "...{print \$1; exit}"); echo ok'
#   -> exit 0   (sin pipefail no hay SIGPIPE)
#
# Y NO se puede simplemente quitar el `exit`, porque en uno de los siete hace
# falta. `\<device\>` casa DOS lineas de struct pci_dev:
#   10  short unsigned int  device;   offset 62    <- la correcta
#   88  struct device       dev;      offset 208   <- falso positivo
# porque `struct device` contiene la palabra `device`. Quitar el exit haria que
# p_dev saliera con dos lineas y la comparacion de la 266 no podria pasar.
#
# El fix conserva las dos propiedades: awk LEE HASTA EOF (no hay SIGPIPE) e
# IMPRIME SOLO LA PRIMERA coincidencia (igual que hacia el exit).
import re as _re
pat = _re.compile(r"\{print (\$\(NF-\d+\)); exit\}")
n_exit = len(pat.findall(s))
assert n_exit == 7, f"se esperaban 7 awk con '; exit' y hay {n_exit}"
s = pat.sub(lambda m: "{if (!s) {print %s; s=1}}" % m.group(1), s)
cambios.append("2b · los 7 awk con '; exit': leen hasta EOF y contestan la PRIMERA "
               "coincidencia. Sin esto el harness muere con SIGPIPE 141 en P8")

# ---- 3) precondicion de root ----------------------------------------------
n = s.count('$(NF-1)')
assert n == 8, f"se esperaban 8 ocurrencias de $(NF-1) y hay {n}; el guion no se adapta solo"
s = s.replace('$(NF-1)', '$(NF-2)')
cambios.append(f"2 · $(NF-1) -> $(NF-2) en {n} extracciones de offset")

# ---- 3) precondicion de root ----------------------------------------------
ANCLA3 = '''  # P3 debugfs montado
  mountpoint -q /sys/kernel/debug || die "P3 FAIL: debugfs no montado"'''
NUEVO3 = '''  # P2.5 root. Las precondiciones siguientes (P3-P7) leen /sys/kernel/debug/dri,
  # que es root-only, y las PHASE 6/7/8 hacen insmod/rmmod. El harness exigia
  # root en cinco sitios y no lo comprobaba en ninguno: sin privilegio el
  # fallo es "Permiso denegado" en P4, que no lleva a nadie a la causa.
  # Comprobado aqui porque es la unica precondicion que se ANADE, no se corrige.
  [ "$(id -u)" -eq 0 ] || die "P2.5 FAIL: este harness necesita root (lee debugfs y hace insmod).
     id -u = $(id -u). Sin sudo el fallo aparecera en P4, no aqui."
  info "P2.5 root:        OK (uid 0)"

  # P3 debugfs montado
  mountpoint -q /sys/kernel/debug || die "P3 FAIL: debugfs no montado"'''
assert ANCLA3 in s, "ancla de P3 no encontrada"
s = s.replace(ANCLA3, NUEVO3, 1)
cambios.append("3 · anadir la precondicion de root (P2.5), que no existia")

open(dst, 'w', encoding='utf-8').write(s)
for c in cambios:
    print("cambio:", c)
print("lineas:", len(orig.splitlines()), "->", len(s.splitlines()))
PY

bash -n "$OUT" || { echo "ABORTO: la copia reparada no parsea" >&2; exit 2; }
echo "bash -n: OK"
diff -u "$ORIG" "$OUT" > "$DIFF" || true
echo "diff escrito: $DIFF ($(grep -c '^+' "$DIFF") lineas añadidas, $(grep -c '^-' "$DIFF") eliminadas)"
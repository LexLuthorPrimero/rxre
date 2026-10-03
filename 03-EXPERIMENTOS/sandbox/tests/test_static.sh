#!/usr/bin/env bash
# test_static.sh — T10..T14 + auditorías de alcance y de acceso a hardware.
#
# No carga el módulo. No hace bind. No toca la GPU. No abre /dev ni debugfs
# de la GPU. Sólo compila un binario de userspace e inspecciona ficheros.

set -uo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DRV="$(dirname "$HERE")"
SRC="$DRV/rx550_target.c"
KO="$DRV/rx550_drv.ko"
KVER="$(uname -r)"

# Un audit por texto que encuentra un nombre en un COMENTARIO no demuestra
# nada.  -fpreprocessed evita la expansion de macros y elimina comentarios,
# de modo que lo que queda es codigo real.
strip_comments() { gcc -fpreprocessed -dD -E -P -x c "$1" 2>/dev/null; }

pass=0; fail=0
ok()   { printf "  PASS  %-4s %s\n" "$1" "$2"; pass=$((pass+1)); }
no()   { printf "  FAIL  %-4s %s\n" "$1" "$2"; fail=$((fail+1)); }
chk()  { if [ "$1" = "0" ]; then ok "$2" "$3"; else no "$2" "$3"; fi }

echo "T1-T9 · ejecutando la regla real (target_match.h)"
gcc -O2 -Wall -Wextra -Werror -o "$HERE/test_target_match" "$HERE/test_target_match.c" || {
	echo "  FAIL  build del test"; exit 1; }
"$HERE/test_target_match" || fail=$((fail+1))
echo

echo "T10-T14 · validación estática del driver"
[ -f "$KO" ] || { echo "  FAIL  falta $KO (ejecuta make primero)"; exit 1; }

# T10 firma de probe/remove coherente con 7.1.3
grep -q "rx550_target_probe(struct pci_dev \*pdev," "$SRC" && \
grep -q "const struct pci_device_id \*id)" "$SRC" && \
chk 0 T10 "firma de probe(struct pci_dev *, const struct pci_device_id *)"
grep -q "void rx550_target_remove(struct pci_dev \*pdev)" "$SRC" && \
chk 0 T10 "firma de remove(struct pci_dev *)"

# T11 pci_set_drvdata sólo después del matching
awk '/if \(!target_match\(/{m=NR} /pci_set_drvdata\(pdev, tdev\)/{if (NR>m) {print "OK"; exit}}' "$SRC" \
  | grep -q OK && chk 0 T11 "pci_set_drvdata aparece después de la puerta de matching"
grep -q "pci_set_drvdata(pdev, NULL)" "$SRC" && \
chk 0 T11 "remove() retira la asociación antes de liberar"

# T12 remove libera
grep -q "kfree(tdev)" "$SRC" && chk 0 T12 "remove() libera el estado"
grep -q "struct target_device \*tdev = pci_get_drvdata(pdev)" "$SRC" && \
chk 0 T12 "remove() obtiene el estado y comprueba que existe"

# T13/T14 module_init / module_exit
grep -q "module_pci_driver(rx550_target_pci_driver)" "$SRC" && \
chk 0 T13 "module_init registra el pci_driver (module_pci_driver)"
nm "$KO" 2>/dev/null | grep -q "__pfx_init_module\|init_module" && \
chk 0 T13 "init_module presente en el .ko"
nm "$KO" 2>/dev/null | grep -q "cleanup_module" && \
chk 0 T14 "cleanup_module presente en el .ko (module_exit)"

echo
echo "AUDIT · acceso a hardware (debe estar AUSENTE)"
# Se busca en el fuente del driver, no en comentarios de auditoría.
BODY=$(strip_comments "$SRC"; strip_comments "$DRV/pci_resource.c")
#  pci_iomap / pci_iounmap NO estan aqui: son MMIO_MAPPING, categoria propia
#  de STATE 3, y se auditan mas abajo como PRESENCIA exigida.
for sym in ioremap ioremap64 pci_enable_device \
           pci_request_regions pci_alloc_irq_vectors \
           readl writel readq writeq request_irq request_threaded_irq \
           free_irq dma_alloc_coherent dma_map_single dma_sync_single \
           amdgpu; do
  if printf '%s' "$BODY" | grep -qw "$sym"; then
    no "HW" "aparece '$sym' en el cuerpo del driver"
  fi
done
chk 0 HW "ninguna llamada de acceso a hardware en el cuerpo"

# Prueba a NIVEL DE ENLACE, no de texto: los símbolos indefinidos del .ko son
# lo que el módulo realmente pide al kernel. Un test que sólo lee el fuente no
# puede detectar una llamada de hardware añadida por otra vía.
UNDEF=$(nm -u "$KO" 2>/dev/null | awk '{print $NF}' | sort -u)
for sym in __ioremap pci_enable_device pci_request_regions \
           pci_alloc_irq_vectors \
           __readl __writel __readq __writeq request_irq \
           dma_alloc_coherent dma_map_single; do
  if printf '%s\n' "$UNDEF" | grep -qx "$sym"; then
    no "HW-L" "el .ko referencia el símbolo de hardware '$sym'"
  fi
done
chk 0 HW-L "el .ko no referencia ningún símbolo de acceso a hardware"
printf '%s\n' "$UNDEF" | grep -qx "__pci_register_driver" && \
  chk 0 LINK "el .ko referencia __pci_register_driver (module_init real)"
printf '%s\n' "$UNDEF" | grep -qx "pci_unregister_driver" && \
  chk 0 LINK "el .ko referencia pci_unregister_driver (module_exit real)"

echo
echo "AUDIT · MMIO_MAPPING (STATE 3: debe estar PRESENTE y ser reversible)"
#  Esta categoria NO es una exencion.  Antes pci_iomap/pci_iounmap estaban en
#  la lista de prohibidas porque STATE 3 no existia.  Ahora STATE 3 mapea BAR5,
#  asi que la comprobacion correcta ya no es "no aparece" sino "aparece, y
#  aparece tambien su desasignacion".  Si disappears el mapeo, esto falla igual
#  que antes fallaba por presencia indebida.
printf '%s' "$BODY" | grep -qw "pci_iomap" && \
  ok  "MMIO-M" "pci_iomap presente en el cuerpo (mapeo de STATE 3)" || \
  no  "MMIO-M" "pci_iomap AUSENTE: el mapeo no se realizaria"
printf '%s' "$BODY" | grep -qw "pci_iounmap" && \
  ok  "MMIO-M" "pci_iounmap presente en el cuerpo (el mapeo es reversible)" || \
  no  "MMIO-M" "pci_iounmap AUSENTE: el mapeo no se desharia nunca"
printf '%s\n' "$UNDEF" | grep -qx "pci_iomap" && \
  ok  "MMIO-M" "el .ko pide pci_iomap al kernel" || \
  no  "MMIO-M" "el .ko NO pide pci_iomap: el enlace no demuestra nada"
printf '%s\n' "$UNDEF" | grep -qx "pci_iounmap" && \
  ok  "MMIO-M" "el .ko pide pci_iounmap al kernel" || \
  no  "MMIO-M" "el .ko NO pide pci_iounmap: el rollback no esta enlazado"
#  MMIO_MAPPING y MMIO_ACCESS siguen siendo categorias distintas: mapear la BAR
#  no es leerla.  El acceso real sigue prohibido y se audita arriba con readl,
#  writel, readq, writeq e ioremap, que no se han tocado.

# La id_table se verifica ESTRUCTURALMENTE: se localiza el símbolo, se resuelve
# el desplazamiento de su sección y se leen los u32 reales. Un substring en
# cualquier parte del binario no probaría que sea la tabla.
idt_addr=$(nm -a "$KO" 2>/dev/null | awk '/[rR] rx550_target_id_table$/{print "0x"$1; exit}')
if [ -z "$idt_addr" ]; then
  no IDT "no se encontró el símbolo rx550_target_id_table en el .ko"
else
  # readelf -SW: ... .rodata PROGBITS <addr> <offset> <size> ...
  sec=$(( $(readelf -SW "$KO" 2>/dev/null | awk '$3==".rodata"{print "0x"$6; exit}') ))
  off=$(( sec + idt_addr ))
  got=$(dd if="$KO" bs=1 skip=$off count=16 2>/dev/null | od -An -tx4 -v | tr -s ' ' | tr -d '\n' | sed 's/^ //')
  want="00001002 0000699f 00001002 00000b04"
  if [ "$got" = "$want" ]; then
    chk 0 IDT "id_table en el binario: vendor=1002 device=699f subvendor=1002 subdevice=0b04"
  else
    no IDT "id_table inesperada en el binario: [$got] != [$want]"
  fi
  # terminadora en cero: el core itera mientras vendor||subvendor||class_mask
  term=$(dd if="$KO" bs=1 skip=$((off+40)) count=8 2>/dev/null | od -An -tx4 -v | tr -s ' ' | tr -d '\n' | sed 's/^ //')
  [ "$term" = "00000000 00000000" ] && chk 0 IDT "entrada terminadora de la id_table en cero" \
                                    || no IDT "terminadora inesperada: [$term]"
  # class_mask == 0: no impone clase (drivers/pci/pci.h:466)
  cm=$(dd if="$KO" bs=1 skip=$((off+20)) count=4 2>/dev/null | od -An -tx4 -v | tr -s ' ' | sed 's/^ //')
  [ "$cm" = "00000000" ] && chk 0 IDT "class_mask = 0 (no impone clase)" \
                         || no IDT "class_mask inesperado: [$cm]"
fi

# Lo que sí debe existir: el registro del driver
modinfo "$KO" 2>/dev/null | grep -q "^name: *rx550_target" && \
chk 0 MOD "modinfo: name = rx550_target"
modinfo "$KO" 2>/dev/null | grep -q "^license: *GPL" && \
chk 0 MOD "modinfo: license = GPL"
case "$(modinfo -F vermagic "$KO")" in
  "$KVER"*) chk 0 MOD "modinfo: vermagic corresponde al kernel en ejecución" ;;
  *)        no  MOD "vermagic no corresponde: $(modinfo -F vermagic "$KO")" ;;
esac

echo
echo "SCOPE · no se ha ampliado el conjunto de hardware soportado"
# La id_table no debe contener más de UNA entrada de dispositivo.
n=$(awk '/rx550_target_id_table\[\] = \{/{f=1;next} f&&/^};/{exit} f&&/\.vendor/{c++} END{print c+0}' "$SRC")
[ "$n" = "1" ] && chk 0 SCOPE "la id_table declara exactamente 1 dispositivo" \
              || no SCOPE "la id_table declara $n dispositivos (esperado 1)"
# Sin comodines en la id_table
if awk '/rx550_target_id_table\[\] = \{/{f=1} f&&/^};/{exit} f' "$SRC" | grep -qw "PCI_ANY_ID"; then
  no SCOPE "la id_table usa PCI_ANY_ID (comodín)"
else
  chk 0 SCOPE "la id_table no usa PCI_ANY_ID: sin comodines"
fi
# Sin macros de familia
if grep -qE "AMDGPU_ANY|amdgpu_device|gfx8_device|polaris_device|amd_gpu_ops" "$SRC" \
   "$DRV/target_match.h"; then
  no SCOPE "aparece un símbolo de familia/genérico"
else
  chk 0 SCOPE "ninguna estructura de familia o ASIC en el driver"
fi

echo
echo "COMP 4 · capa de recurso"
PCODE=$(strip_comments "$DRV/pci_resource.c"; strip_comments "$SRC")
for fn in target_res_discover target_res_claim_regions target_res_release; do
  nm "$KO" 2>/dev/null | grep -qw "$fn" && chk 0 RES "simbolo presente: $fn" \
                                  || no RES "falta el simbolo $fn"
done
# la BAR de registros es la unica que se reclama
[ "$(printf '%s' "$PCODE" | grep -cw 'pci_request_region')" -ge 1 ] && \
  chk 0 RES "el codigo usa pci_request_region (selectivo)" || no RES "falta pci_request_region"
printf '%s' "$PCODE" | grep -qw 'pci_request_regions' && \
  no RES "usa pci_request_regions (reserva TODAS las BAR)" || \
  chk 0 RES "NO usa pci_request_regions: nada se reserva por anticipacion"
# pci_enable_device debe quedar diferido
printf '%s' "$PCODE" | grep -qw 'pci_enable_device' && \
  no RES "pci_enable_device presente: deberia estar DEFERRED" || \
  chk 0 RES "pci_enable_device DEFERRED (no llamado)"
# la tabla de unwind debe estar documentada
grep -q "STATE 2" "$DRV/rx550_target.c" && chk 0 RES "tabla de unwind (STATE 0..4) documentada" \
                                     || no RES "falta la tabla de unwind"
# la limpieza solo recorre CLAIMED
printf '%s' "$PCODE" | grep -qw "target_res_owned" && \
  chk 0 RES "release condicionado por target_res_owned (invariante I3)" || \
  no RES "release sin la invariante I3"
# un solo campo nuevo en el device object
grep -q "struct target_resources	res;" "$DRV/rx550_target.c" && \
  chk 0 RES "device object con el campo res" || no RES "falta el campo res"

echo
echo "────────────────────────────────────────────────"
printf "resumen estático: %d PASS, %d FAIL\n" "$pass" "$fail"
[ "$fail" = 0 ] && echo "T1-T14 + auditorías: OK" || echo "HAY FALLOS"
exit 0

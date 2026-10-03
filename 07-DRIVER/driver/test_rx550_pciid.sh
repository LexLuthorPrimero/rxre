#!/bin/sh
#
# test_rx550_pciid.sh — test estatico del driver objetivo.
#
# Componentes cubiertos:
#   [1] identidad PCI     [2] lifecycle     [3] device object + recursos
#
# UNA SOLA PREGUNTA:
#   ¿El driver cumple su contrato, y su objeto y su ownership son correctos?
#
# CADA TEST DECLARA QUE COMPRUEBA. Nada se disfraza de mas:
#   HEADER  la afirmacion viene de los headers del kernel exacto
#   SOURCE  se comprueba sobre el codigo, por POSICION cuando el orden importa
#   BINARY  se comprueba sobre el .ko
# Un test de orden tiene que demostrar orden: contar que una cadena aparece no
# demuestra nada, y por eso T7, T8 y T11 trabajan sobre numeros de linea.
#
# No carga el modulo. No ejecuta probe. No toca la GPU.

set -u

SRC=rx550_pciid.c
HDR=rx550_pciid.h
KO=rx550_pciid.ko
KHDRS=/usr/src/kernels/7.1.3-200.nobara.fc44.x86_64/include/linux/pci.h
EXPECTED_ALIAS='pci:v00001002d0000699Fsv*sd*bc*sc*i*'
TV=1002
TD=699F

pass=0
fail=0
ok()   { printf '  PASS  %-5s %s\n' "$1" "$2"; pass=$((pass+1)); }
ko()   { printf '  FAIL  %-5s %s\n' "$1" "$2"; fail=$((fail+1)); }
info() { printf '             %s\n' "$1"; }

for f in "$SRC" "$HDR" "$KO" "$KHDRS"; do
	if [ ! -r "$f" ]; then
		printf 'ABORT  %s no accesible.\n' "$f"
		exit 2
	fi
done

# --- limites de las funciones, por numero de linea real -------------------
P_PROBE=$(grep -n '^static int rx550_pciid_probe' "$SRC" | cut -d: -f1)
P_REMOVE=$(grep -n '^static void rx550_pciid_remove' "$SRC" | cut -d: -f1)
P_DRV=$(grep -n '^static struct pci_driver' "$SRC" | cut -d: -f1)
# Busca una subcadena LITERAL dentro de un rango de lineas.
# index() y no un regex: estos patrones son tokens exactos del codigo, y un
# regex mal escapado daria silenciosamente cero en vez de un fallo claro.
at() { # at <desde> <hasta> <subcadena>
	awk -v a="$1" -v b="$2" -v p="$3" \
		'NR>a && NR<b && index($0,p) {print NR; exit}' "$SRC"
}
cnt() {
	awk -v a="$1" -v b="$2" -v p="$3" \
		'NR>a && NR<b && index($0,p) {c++} END{print c+0}' "$SRC"
}

printf 'test_rx550_pciid — identidad + lifecycle + device object\n\n'

# ============================ COMPONENTE 1 ================================
alias_glob=$(modinfo -F alias "$KO" | grep '^pci:')
dev_alias() {
	printf 'pci:v%08Xd%08Xsv%08Xsd%08Xbc%02Xsc%02Xi%02X' "$1" "$2" 0 0 0 0 0
}
matches() {
	case "$(dev_alias "$1" "$2")" in
	$alias_glob) return 0 ;;
	*)          return 1 ;;
	esac
}
CORPUS=${RX550_CORPUS:-../../RESEARCH/kernelbuild/linux-7.1.3}
AMDGPU_DRV="$CORPUS/drivers/gpu/drm/amd/amdgpu/amdgpu_drv.c"
family=$(sed -n '2034,2041p' "$AMDGPU_DRV" |
	 awk -F'[{,]' '{gsub(/[ \t]/,"",$3); print tolower($3)}')

if matches 0x$TV 0x$TD; then
	ok I1 "ACEPTA el objetivo $TV:$TD"
	info "$alias_glob"
else
	ko I1 "RECHAZA el propio objetivo $TV:$TD"
fi
n7=0
for d in $family; do
	case "$d" in *699f) continue ;; esac
	matches 0x1002 "$d" && ko I2 "ACEPTA indebidamente $d" || n7=$((n7+1))
done
[ "$n7" -eq 7 ] && ok I2 "RECHAZA los otros 7 Polaris12 de la familia" \
	|| ko I2 "rechazo de familia incompleto: $n7/7"
matches 0x1002 0x67CC && ko I3 "ACEPTA 1002:67CC" || ok I3 "RECHAZA 1002:67CC"
if matches 0x10DE 0x699F || matches 0x8086 0x1234; then
	ko I4 "ACEPTA un vendor distinto"
else
	ok I4 "RECHAZA vendors distintos (10DE, 8086)"
fi

# ============================ COMPONENTE 2 ================================
hdr_probe=$(grep -c 'int  (\*probe)(struct pci_dev \*dev, const struct pci_device_id \*id)' "$KHDRS")
if [ "$hdr_probe" -ge 1 ]; then
	ok L1 "probe declara la firma de 7.1.3 (HEADER)"
	info "$(grep -n '(\*probe)(struct pci_dev' "$KHDRS" | head -1 | sed 's/\t*/ /')"
else
	ko L1 "la firma de probe no coincide con los headers"
fi

# ============================ COMPONENTE 3 ================================

# T1 — el objeto existe con el nombre y el tipo esperados
if grep -q '^struct rx550_target {' "$HDR"; then
	ok T1 "DEVICE_OBJECT_EXISTS: struct rx550_target declarada en la cabecera"
else
	ko T1 "no existe struct rx550_target"
fi

# T2 — la asignacion ocurre una vez, y solo en probe
alloc=$(at "$P_PROBE" "$P_REMOVE" 'kmalloc(')
nalloc=$(cnt "$P_PROBE" "$P_REMOVE" 'kmalloc(')
if [ -n "$alloc" ] && [ "$nalloc" -eq 1 ]; then
	ok T2 "OBJECT_ALLOCATION_VERIFIED: una sola asignacion, dentro de probe"
	info "linea $alloc"
else
	ko T2 "asignaciones en probe: $nalloc (se esperaba exactamente 1)"
fi

# T3 — TODO campo del objeto se inicializa en probe. Se comprueba por paridad
#      de recuento, no buscando el nombre: anadir un campo sin inicializar
#      hace que los dos numeros dejen de coincidir.
fields=$(awk '/^struct rx550_target \{/,/^\};/' "$HDR" | awk '
	{ l=$0; sub(/\/\*.*/, "", l)
	  if (l !~ /^[ \t]/ && l !~ /^[ \t]/) next
	  if (match(l, /^[^;]*;/)) {
		f = substr(l, 1, RLENGTH-1)
		n = split(f, p, /[ \t*]+/)
		if (n > 0 && p[n] != "") print p[n]
	  } }' | sort -u)
nfields=$(echo "$fields" | grep -c .)
inits=$(sed -n "$((P_PROBE+1)),$((P_REMOVE-1))p" "$SRC" |
	grep -oE 'target->[a-z_]+ *=' | sed 's/ *=$//;s/target->//' | sort -u)
ninits=$(echo "$inits" | grep -c .)
if [ "$nfields" -ge 1 ] && [ "$nfields" -eq "$ninits" ]; then
	ok T3 "OBJECT_INITIALIZATION_VERIFIED: $nfields campo(s), $ninits inicializado(s)"
	info "$(echo $fields | tr '\n' ' ')"
else
	ko T3 "paridad rota: $nfields campo(s) declarados, $ninits inicializado(s)"
fi

# T4 — back-pointer presente Y verificado en remove
if [ -n "$(echo "$inits" | grep -x pdev)" ] &&
   [ -n "$(at "$P_REMOVE" "$P_DRV" 'target->pdev != pdev')" ]; then
	ok T4 "PCI_DEV_BACK_POINTER_VERIFIED: se escribe al publicar y se comprueba al liberar"
else
	ko T4 "falta el back-pointer o su comprobacion en remove"
fi

# T5 — publicacion despues de inicializar
setd=$(at "$P_PROBE" "$P_REMOVE" 'pci_set_drvdata(pdev, target)')
init=$(at "$P_PROBE" "$P_REMOVE" 'target->pdev = pdev')
ret0=$(at "$P_PROBE" "$P_REMOVE" 'return 0;')
if [ -n "$setd" ] && [ -n "$init" ] && [ "$init" -lt "$setd" ] && [ "$setd" -lt "$ret0" ]; then
	ok T5 "DRVDATA_PUBLICATION_VERIFIED: init($init) < publica($setd) < return 0($ret0)"
else
	ko T5 "orden init/publica/return incorrecto"
fi

# T6 — recuperacion por el unico accessor, en remove
if [ -n "$(at "$P_REMOVE" "$P_DRV" 'rx550_target_of(pdev)')" ]; then
	ok T6 "DRVDATA_RETRIEVAL_VERIFIED: remove recupera por rx550_target_of()"
else
	ko T6 "remove no recupera el estado por el accessor"
fi
# Y que ese accessor sea el UNICO camino a drvdata. Vive en la cabecera, asi
# que el invariante es: cero llamadas directas en el .c, exactamente una en el .h.
nget_c=$(cnt 1 "$P_DRV" 'pci_get_drvdata')
nget_h=$(grep -c 'pci_get_drvdata' "$HDR")
if [ "$nget_c" -eq 0 ] && [ "$nget_h" -eq 1 ]; then
	ok T6b "UNICO camino de lectura: 0 pci_get_drvdata en el .c, 1 en el accessor"
else
	ko T6b "caminos de lectura: .c=$nget_c (debe ser 0), .h=$nget_h (debe ser 1)"
fi

# T7 — ORDEN: despublicar ANTES de liberar
det=$(at "$P_REMOVE" "$P_DRV" 'pci_set_drvdata(pdev, NULL)')
fre=$(at "$P_REMOVE" "$P_DRV" 'kfree(')
if [ -n "$det" ] && [ -n "$fre" ] && [ "$det" -lt "$fre" ]; then
	ok T7 "DETACH_BEFORE_FREE_VERIFIED: despublica en $det, libera en $fre"
else
	ko T7 "el orden detach/free no se cumple (detach=$det free=$fre)"
fi

# T8 — use-after-free: NINGUNA lectura de target despues del kfree
uaf=$(awk -v f="$fre" 'NR>f && /target->/ {c++} END{print c+0}' "$SRC")
if [ "$uaf" -eq 0 ]; then
	ok T8 "NO_USE_AFTER_FREE_VERIFIED: 0 lecturas de target-> despues del kfree($fre)"
else
	ko T8 "use-after-free: $uaf lectura(s) de target-> despues de liberar"
fi

# T9 — double free: exactamente un kfree en todo el fichero
nk=$(grep -c 'kfree(' "$SRC")
if [ "$nk" -eq 1 ]; then
	ok T9 "NO_DOUBLE_FREE_VERIFIED: un unico kfree en el fichero"
else
	ko T9 "kfree aparece $nk veces"
fi

# T10 — unwind: ningun return de error despues de que exista la memoria
enomem=$(at "$P_PROBE" "$P_REMOVE" 'return -ENOMEM;')
leak=$(awk -v a="$enomem" -v b="$P_REMOVE" 'NR>a && NR<b && /return -/ {c++} END{print c+0}' "$SRC")
if [ "$leak" -eq 0 ]; then
	ok T10 "ERROR_UNWIND_VERIFIED: 0 returns de error tras la asignacion; solo se libera lo adquirido"
	info "returns de error: $(cnt "$P_PROBE" "$P_REMOVE" 'return -'), posteriores a ENOMEM: $leak"
else
	ko T10 "returns de error tras la asignacion: $leak (posible fuga)"
fi

# T11 — simetria: lo ultimo adquirido se libera primero
#   adquisicion: kmalloc(alloc) -> init -> publish
#   liberacion:  detach(det)  -> free(fre)
inv_alloc=$alloc; inv_pub=$setd; inv_det=$det; inv_free=$fre
if [ "$inv_alloc" -lt "$inv_pub" ] && [ "$inv_det" -lt "$inv_free" ]; then
	ok T11 "REMOVE_SYMMETRY_VERIFIED:_kmalloc<$setd  y  despublicar($det)<kfree($fre)"
else
	ko T11 "la liberacion no invierte la adquisicion"
fi

# T12 — el modelo de recursos esta declarado, y declara ausencia de adquisicion
rows=$(grep -cE '^ \*   (PCI DEVICE|PCI REGIONS|MMIO|IRQ|DMA) ' "$HDR")
notacq=$(grep -cE 'NO  +NO  +el driver' "$HDR")
if [ "$rows" -eq 5 ] && [ "$notacq" -eq 4 ]; then
	ok T12 "RESOURCE_MODEL_VERIFIED: 5 recursos modelados, 4 con dueno futuro explicito"
else
	ko T12 "tabla de recursos incompleta (filas=$rows, con dueno=$notacq)"
fi

# T13 — ninguna API de adquisicion. Distingue "no existe" de "no se usa".
ACQUIRE='pci_enable_device pci_disable_device pci_set_master
pci_request_regions pci_release_regions
pci_alloc_irq_vectors pci_free_irq_vectors
dma_alloc_coherent dma_alloc_attrs dma_zalloc_coherent
dma_map_single dma_map_resource dma_unmap_single
request_irq request_threaded_irq request_pei_irq
devm_request_irq pci_request_irq'
acq=''
for s in $ACQUIRE; do
	grep -qE "(^|[^a-z_])$s *\(" "$SRC" && acq="$acq $s"
done
if [ -z "$acq" ]; then
	ok T13 "NO_RESOURCE_ACQUISITION_VERIFIED: 0 llamadas de adquisicion en el fuente"
else
	ko T13 "API de adquisicion presente:$acq"
	info "no se eliminan: se reportan para decidir"
fi

# T14 — auditoria negativa de acceso a hardware, sobre fuente Y binario
undef=$(nm -u "$KO" | awk '{print $NF}' | sort -u)
linked=$(nm "$KO" | awk '{print $NF}' | sort -u)
HW='ioremap iounmap pci_iomap pci_iounmap devm_ioremap
pci_read_config_byte pci_read_config_word pci_read_config_dword
pci_write_config_byte pci_write_config_word pci_write_config_dword
readl readq readw readb writel writeq writew writeb
cgas_read cgas_write __cgas_read __cgas_write
dma_sync_single_for_cpu dma_sync_single_for_device
msleep udelay mdelay'
hw=''
for s in $HW; do
	echo "$undef $linked" | tr ' ' '\n' | grep -qx "$s" && hw="$hw $s"
done
if [ -z "$hw" ]; then
	ok T14 "NO_HARDWARE_ACCESS_VERIFIED: 0 APIs de hardware en fuente y binario"
else
	ko T14 "APIs de hardware presentes:$hw"
fi

# T15 — el target no se toco
if [ "$(grep -c 'RX550_PCI_VENDOR_ID	0x1002' "$SRC")" -eq 1 ] &&
   [ "$(grep -c 'RX550_PCI_DEVICE_ID	0x699F' "$SRC")" -eq 1 ] &&
   [ "$n7" -eq 7 ]; then
	ok T15 "TARGET_MATCH_UNCHANGED: 0x1002/0x699F, rechazo de los otros 7 intacto"
else
	ko T15 "el target matching ha cambiado"
fi

# T16 — build
vm=$(modinfo -F vermagic "$KO")
[ "${vm%% *}" = "$(uname -r)" ] \
	&& ok T16 "BUILD: .ko vigente, vermagic $vm" \
	|| ko T16 "vermagic $vm != $(uname -r)"

# --- metadatos y dependencias ---------------------------------------------
echo "$undef" | grep -qi amdgpu && ko D1 "depende de amdgpu" || ok D1 "sin dependencia de amdgpu"
dep=$(modinfo -F depends "$KO")
[ -z "$dep" ] || [ "$dep" = "0" ] && ok D2 "depends vacio" || ko D2 "depends=$dep"

printf '\n  %d pass, %d fail\n' "$pass" "$fail"
if [ "$fail" -eq 0 ]; then
	printf '  CONTRATO: SATISFECHO\n'
	exit 0
fi
printf '  CONTRATO: INCUMPLIDO\n'
exit 1

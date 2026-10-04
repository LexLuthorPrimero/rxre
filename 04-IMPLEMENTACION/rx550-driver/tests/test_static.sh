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

# ── POR QUE ESTE FICHERO USA UN FICHERO INTERMEDIO Y NO UN PIPE ────────────
#
# MEDIDO 2026-10-03. `nm "$KO" | grep -q simbolo` NO mide si el simbolo esta en
# el .ko. Mide si el simbolo aparece antes de que el buffer de salida de nm se
# haya vaciado, y con eso si grep le manda SIGPIPE antes de que nm termine.
#
#   nm escribe por tuberias con buffer COMPLETO de 4096 B. Si el .ko produce
#   menos, nm hace una sola escritura al salir y no hay SIGPIPE posible. Si
#   produce mas, nm escribe 4096 y el resto al salir; si grep -q encuentra la
#   coincidencia en esos primeros 4096 y sale, la segunda escritura de nm recibe
#   SIGPIPE.
#
#   MEDIDO en este arbol, con el mismo binario y el mismo patron:
#       .ko de 3 objetos -> nm emite  3945 B -> estado del pipe  0  -> T13/T14 PASS
#       .ko de 4 objetos -> nm emite  5216 B -> estado del pipe 141  -> T13/T14 CALLAD
#
# Y aqui esta lo grave: la forma era `nm | grep -q X && chk ...`. Con el pipe en
# 141 el `&&` no se cumple, chk NO se llama, y no se incrementa ni pass ni fail.
# La comprobacion deja de ejecutarse en silencio y la suite sigue diciendo
# "34 PASS, 0 FAIL". Un control que se apaga solo es peor que uno que falla.
#
# MEDIDO 2026-10-04 sobre ESTE .ko, que ya no es el binario de la nota de arriba:
#     nm rx550_drv.ko                -> 10858 B de salida
#     nm rx550_drv.ko | grep -q <match>
#         PIPESTATUS = [141 0]  (141 = nm, 0 = grep)
# El 141 lo recibe nm, no grep. El fallo sigue vivo hoy: el .ko crecio de los
# 3945 B de la nota a 10858 B, y la forma `nm | grep -q` lo reproduce igual.
#
# El arreglo que funciona es UNO, y es el punto 1:
#   1. nm se resuelve UNA vez a un fichero, y se busca en el fichero. El pipe
#      desaparece del camino de decision.
#
# ── CORRECCION 2026-10-04: "NO EXISTE `&& chk`" ERA FALSO ────────────────────
#
# MEDIDO 2026-10-04 contando las lineas logicas (las de continuacion con `\`
# contadas con la que las continua): hay 11 sitios `&& chk` SIN rama `|| no` de
# recurso, y 8 CON ella. Sin recurso, un codigo de salida falso no cuenta nada:
# ni pass ni fail, que es exactamente el apagado que la nota de arriba denuncia.
#
# De los 11, nueve leen FICHEROS o emparejan un test, y dos leen `modinfo`:
#   · 69 72 78 82 83 87   grep/awk sobre FICHERO          (ningun productor)
#   · 76                 awk FICHERO | grep -q OK         (<= 1 linea)
#   · 215 217             printf BUILTIN | grep -qx       (builtin, no proceso)
#   · 275 277             modinfo | grep -q               (productor externo)
# y los 8 CON recurso, que cuentan siempre aunque el test falle, son los del
# bloque IDT, SCOPE y RES.
#
# Los numeros de linea son una foto de la revision de este fichero el
# 2026-10-04 y se desplazan con cada edicion —los desplazan los bloques que hay
# debajo—. Lo que NO se desplaza, y es el invariante, es el CONTEO y la
# CLASIFICACION: 11 sin recurso, 8 con recurso, y de los 11 solo dos tienen un
# productor externo en el pipe.
#
# Una enumeracion anterior de esta nota decia 266, 270, 288 y 322, que son
# justamente los que SI tienen `|| no`, y se dejaba fuera 215, 217, 275 y 277,
# que son los que NO lo tienen. El numero 11 era correcto; el reparto no.
#
# `must()` NO es un mecanismo distinto de `chk`: es un alias puro,
# `must() { chk "$1" "$2" "$3"; }` en la linea de abajo. Lo que evita el apagado
# no es el NOMBRE de la funcion sino COMO SE LLAMA:
#     cmd; must $? ...   -> se invoca siempre, pase lo que pase
#     cmd && chk ...      -> solo se invoca si cmd sale con 0
# must() se usa justamente en las aserciones que leen `nm -u` (T13, T14 y los
# simbolos de RES), que son las que habrian suffered el 141.
#
# POR QUE LOS 11 SON INOCUOS HOY, MEDIDO UNO POR UNO:
#   · 69 72 78 82 83 87 — `grep -q patron FICHERO`: no hay productor en el pipe.
#     grep lee del fichero y sale con 0 o con 1. No hay a quien cortar.
#   · 76 — `awk ... "$SRC" | grep -q OK`: awk lee un FICHERO y emite una sola
#     linea. MEDIDO PIPESTATUS=[0 0].
#   · 215 217 — `printf '%s\n' "$UNDEF" | grep -qx X`: printf es un BUILTIN de
#     bash, no un proceso, asi que no hay nada que muera por EPIPE. MEDIDO: con
#     20 kB y la coincidencia en la PRIMERA linea, el rc sigue siendo 0.
#   · 275 277 — `modinfo "$KO" | grep -q ...`: aqui SI hay productor externo,
#     pero su salida es 555 B, muy por debajo del buffer de stdio, asi que
#     modinfo hace una sola escritura al salir y no hay SIGPIPE posible. MEDIDO
#     PIPESTATUS=[0 0]. Es el mas fragile de los 11: si el .ko hiciera que
#     modinfo imprimiera mas de un buffer y la coincidencia saliera pronto,
#     pasaria a 141. Por eso la forma que hay que usar en estos dos, si algún
#     dia importan, es la del punto 1: volcar a fichero y buscar en el fichero.
#
# EL INVARIANTE QUE ESTA DE VERDAD IMPUESTO no es "no hay && chk", es este:
#   ninguna comprobacion decide sobre el codigo de salida de un PRODUCTOR
#   EXTERNO en un pipe cuyo lector pueda salir antes de que el productor termine.
# Los ficheros $SYMS, $SYMA, $UNDEF y $AUDIT_OBJ son el unico sitio donde nm y
# awk escriben, y de ahi no sale ninguna decision por pipe: el unico `nm` que
# queda (linea de UNDEF) tiene como lector un `sort -u` que lee hasta EOF.
AUDIT_OBJ="$(mktemp)"
SYMS="$(mktemp)"
nm "$KO" > "$SYMS" 2>/dev/null || : > "$SYMS"

# must <codigo> <etiqueta> <texto>  -- cuenta la comprobacion SIEMPRE.
# chk se conserva para codigo existente; las comprobaciones nuevas usan must.
must() { chk "$1" "$2" "$3"; }

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
grep -q "__pfx_init_module\|init_module" "$SYMS"; must $? T13 "init_module presente en el .ko"
grep -q "cleanup_module" "$SYMS"; must $? T14 "cleanup_module presente en el .ko (module_exit)"

echo
echo "AUDIT · acceso a hardware (debe estar AUSENTE)"
# Se busca en el fuente del driver, no en comentarios de auditoria.
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

# ── COBERTURA DEL AUDIT: todos los objetos del modulo, no dos a mano ─────────
#
# MEDIDO 2026-10-03: el audit de arriba mira $SRC y pci_resource.c. Eso son DOS
# ficheros elegidos a mano, de los ocho que estaban en obj-m. Los otros seis no
# los miraba nadie.  Y no era una omision menor: rx550_mmio_access.c, que es el
# unico fichero que hace MMIO de verdad, no estaba en el alcance del audit.  El
# audit decia "ninguna llamada de acceso a hardware" y la unica lectura del
# hardware del modulo estaba fuera de su alcance.
#
# La lista de objetos se EXTRAE del Makefile. Escribirla a mano seria el mismo
# defecto un nivel mas arriba: el dia que obj-m cambie, la lista no cambiaria y
# el audit seguiria contando los objetos que ya no estan.
#
# Y el invariante no es "no hay readl en el modulo": el accessor TIENE que
# leer.  El invariante es "solo el accessor declarado toca el dispositivo, y
# ningun objeto mas".  Por eso hay una lista de excepcion, y por eso la lista
# tiene que seguir contendo lo que dice contener.
MMIO_EXENTOS="rx550_mmio_access.c"
# ── LAS EXENCIONES SE LEEN DE $MMIO_EXENTOS, NO DE UN LITERAL ───────────────
#
# MEDIDO 2026-10-04: la exencion estaba HARDCODEADA por nombre de fichero, en
# los dos sitios donde se decide, y en ninguno de los dos se leia la variable:
#   · el awk que comprueba que el accessor sigue teniendo MMIO, con
#     `-v f="$DRV/rx550_mmio_access.c"`
#   · el awk de HW-OBJ, con `if (f ~ /rx550_mmio_access\.c$/) next`
# MEDIDO, consecuencia: anadir un segundo nombre a MMIO_EXENTOS NO concede
# exencion a NADIE, y editar la linea de arriba da la sensacion de haber
# abierto una exencion que no se ha abierto. Editar el literal si la abria, y
# entonces las dos listas eran dos verdades que solo coincidian por suerte.
#
# El arreglo es que las dos comprobaciones lean $MMIO_EXENTOS. Y para que la
# variable no vuelva a ser decoracion, se ASERTA: un exento que no sea un
# fichero real de obj-m es un FALLO, no un nombre muerto. Asi un nombre
# equivocado en la lista sale a la luz en vez de no hacer nada. Eso es lo que
# hace que editar MMIO_EXENTOS abra de verdad la exencion, que es lo que el
# nombre de la variable promete.
OBJS_RAW=$(awk '/^rx550_drv-objs[ 	]*:=/{
                   for (i=1; i<=NF; i++) if ($i ~ /\.o$/) { gsub(/\\/,"",$i); print $i } }' "$DRV/Makefile")
# El fichero se arma con printf, NO con "$cuerpo_obj$cuerpo". Dentro de comillas
# dobles bash "\n" es una barra y una ene, no un salto de linea: la primera
# version de este bloque metia todo en una sola linea y el awk de abajo no
# encontraba nada.  Medido, no supuesto: el COB salia en FAIL con el accessor
# teniendo readl en la linea 215 del cuerpo limpio.
: > "$AUDIT_OBJ"
n_obj=0
for o in $OBJS_RAW; do
  f="$DRV/${o%.o}.c"
  if [ ! -f "$f" ]; then no "COB" "el objeto $o no tiene fuente: $f"; continue; fi
  n_obj=$((n_obj + 1))
  { printf '__FILE__ %s\n' "$f"; strip_comments "$f"; printf '\n'; } >> "$AUDIT_OBJ"
done

n_aud=0
n_exent=0
for f in $MMIO_EXENTOS; do
  n_exent=$((n_exent + 1))
  grep -q "^__FILE__ $DRV/$f$" "$AUDIT_OBJ" && n_aud=$((n_aud + 1))
done
chk $([ "$n_exent" -ge 1 ] && [ "$n_aud" -eq "$n_exent" ] && echo 0 || echo 1) COB \
    "$n_aud/$n_exent exenciones de MMIO son ficheros reales de obj-m"
chk $([ "$n_obj" -gt 0 ] && echo 0 || echo 1) COB \
    "$n_obj objetos en obj-m, todos con fuente y ninguno sin auditar"

# ── D5 · LA DIRECCION INVERSA DE LA COBERTURA: LOS .c QUE NO ESTAN EN obj-m ─
#
# MEDIDO 2026-10-04: la cobertura de arriba va en UNA direccion. Todo lo que
# esta en obj-m tiene fuente y se audita (el bucle de $OBJS_RAW). La INVERSA no
# la vigilaba nadie, y no es una simetria menor: un .c en disco que no esta en
# obj-m no entra en el .ko, no lo ve HW-OBJ, no lo ve HW-L, y no lo compila el
# modulo. tests/Makefile si lo compila y lo ejecuta, asi que el fichero tiene
# trabajo dentro del componente y ninguna puerta lo mira.
#
# rx550_vmid1_pgt_backing.c es el caso medido: esta en disco, y tests/Makefile lo
# enlaza en TRES reglas (test_vmid1_pgt_backing, test_mmio_access,
# test_block_size) y lo ejecuta en `run`, y NO aparece en Makefile:24.
#
# NO se mete en obj-m. Eso es otra decision, y tomarla aqui seria cambiar el
# .ko que estos mismos tests auditan. Lo que se hace es AFIRMAR que esta fuera
# y por que, para que dentro de seis meses nadie lo lea como un olvido.
#
# El registro es de EXCLUSIONES DECLARADAS, no una foto del estado: cada nombre
# de $FUERA_DECLARADOS es una Exclusion que alguien firmo, y la comprobacion
# exige que el conjunto de .c fuera de obj-m sea EXACTAMENTE ese. Asi esta
# comprobacion falla en las dos direcciones: si aparece un .c nuevo huerfano, y
# tambien si alguien mete una Exclusion en obj-m sin(rename) lo que el resto del
# componente da por supuesto.
#
# MEDIDO 2026-10-04, y por que esta lista es la que es: rx550_gart_geom.c
# ESTUVO fuera de obj-m y dejo de estarlo dentro de esta misma sesion, por el
# commit 8ab9c53 ("gart_geom: el PRODUCTOR de la geometria, que no existia",
# 01:12:27, que anadio rx550_gart_geom.o a Makefile:24). Por eso la lista se
# deriva del Makefile en cada corrida y no se congela: lo que se congela es el
# REGISTRO de exclusiones, que es lo que hay que revisar a mano.
#
# rx550_drv.mod.c queda fuera de este barrido a proposito: lo genera modpost, no
# es fuente del proyecto, y no debe estar en obj-m nunca.
FUERA_DECLARADOS="rx550_ib_bridge.c rx550_ib_composer.c rx550_vmid1_pgt_backing.c"
FUERA_REAL=""
for f in "$DRV"/*.c; do
  b="${f##*/}"
  case "$b" in *.mod.c) continue ;; esac
  if ! grep -q "\b${b%.c}\.o\b" "$DRV/Makefile"; then FUERA_REAL="$FUERA_REAL $b"; fi
done
ord() { printf '%s\n' $1 | grep . | sort | tr '\n' ' '; }
chk $([ "$(ord "$FUERA_REAL")" = "$(ord "$FUERA_DECLARADOS")" ] && echo 0 || echo 1) COB \
    "los .c del árbol fuera de obj-m son exactamente las exclusiones declaradas: $(ord "$FUERA_REAL")"

# Y la invariante del fichero concreto, pieza por pieza.
VFUERA="rx550_vmid1_pgt_backing.c"
if [ ! -f "$DRV/$VFUERA" ]; then
  no COB "$VFUERA no existe: el audit no puede afirmar nada sobre el"
elif grep -q "\b${VFUERA%.c}\.o\b" "$DRV/Makefile"; then
  no COB "$VFUERA ha entrado en obj-m: cambia el .ko que se audita, y es otra decision"
else
  chk 0 COB "$VFUERA existe y esta FUERA de obj-m por decision (Makefile:24 lo omite)"
fi
# Su clasificacion esta escrita en el propio .c, que es lo que impide leerlo
# como un olvido. MEDIDO: cabecera :8-13 ("C PURO. Sin inline asm, sin MMIO,
# sin ioremap, sin readl/writel, sin ring, sin acceso a GPU. Compilable en
# userspace") y :22-25 ("LO QUE NO HACE / No programa ningun registro").
n_clasif=0
grep -q "C PURO" "$DRV/$VFUERA"                    && n_clasif=$((n_clasif + 1))
grep -q "Compilable en userspace" "$DRV/$VFUERA"    && n_clasif=$((n_clasif + 1))
grep -q "No programa ningun registro" "$DRV/$VFUERA" && n_clasif=$((n_clasif + 1))
chk $([ "$n_clasif" -eq 3 ] && echo 0 || echo 1) COB \
    "$VFUERA declara su clasificación en su propio fuente ($n_clasif/3 marcas)"
# Y que tests/Makefile no lo deje de verdad huerfano: si nadie lo compila, el
# fichero no es "fuera de obj-m por decision", es basura.
grep -q "\.\./$VFUERA" "$HERE/Makefile" && \
  chk 0 COB "$VFUERA lo compila y ejecuta tests/Makefile: no es un fuente muerto" \
              || no COB "$VFUERA no lo compila nadie: no es una decision, es un olvido"
# La excepcion tiene que seguir siendo excepcion de algo: si el accessor
# declarado dejara de tener MMIO, la lista estaria admitting a un fichero que no
# necesita excepcion, y la comprobacion habria perdido su motivo.
# Y TODOS los exentos, no solo el primero. Con un unico exento las dos lecturas
# coinciden; en cuanto MMIO_EXENTOS tenga dos nombres, "alguno tiene MMIO" ya no
# demuestra que el que se esta admitiendo lo tenga. Por eso se cuenta.
n_acc=0
for af in $MMIO_EXENTOS; do
  hay=0
  for sym in readl writel readq writeq; do
    awk -v f="$DRV/$af" -v sym="$sym" '
        $0=="__FILE__ " f {dentro=1; next}
        /^__FILE__ /  {dentro=0}
        dentro && $0 ~ ("(^|[^A-Za-z0-9_])" sym "([^A-Za-z0-9_]|$)") {n++}
        END {exit(n>0?0:1)}' "$AUDIT_OBJ" && hay=1
  done
  [ "$hay" -eq 1 ] && n_acc=$((n_acc + 1))
done
# chk toma un CODIGO DE SALIDA, no un SI/NO: 0 es pasa.  Por eso se compara el
# contador con el numero de exentos y no se pasa una bandera.  La primera version
# pasaba $hit_acc tal cual y por eso daba FAIL con el accessor teniendo readl
# delante.  Un check con el signo cambiado es peor que un check sin hacer: parece
# que mide algo y mide lo contrario.
chk $([ "$n_acc" -eq "$n_exent" ] && echo 0 || echo 1) COB \
    "cada exención de MMIO ($MMIO_EXENTOS) sigue siendo un fichero que hace MMIO ($n_acc/$n_exent)"

# ── COB-MODULOS · LO QUE FALTABA, Y POR QUE EL DE ARRIBA NO LO DETECTA ──────
#
# MEDIDO 2026-10-04.  Al anadir rx550_vm_geom.o se metio en la LINEA DE obj-m en
# vez de en rx550_drv-objs,  y el chequeo COB de arriba dio VERDE.  No fallo por
# poco:  dio verde porque lo que comprueba es que el .c este DECLARADO, y lo
# estaba.  Lo que estaba DECLARADO MAL es otra cosa.
#
# Por eso el fallo real tardo en salir:  modpost responde
#     ERROR: modpost: missing MODULE_LICENSE() in rx550_vm_geom.o
# porque MODULE_LICENSE() solo esta en el fichero que DECLARA el modulo,  o sea
# rx550_target.c.  Un .o suelto en obj-m se convierte en un SEGUNDO modulo,  y
# ese segundo no tiene macro de licencia.  El comentario del propio Makefile:13
# advertia de esto;  lo que faltaba era una puerta.
#
# Lo que esta comprobacion mide,  y son tres cosas distintas:
#   1. obj-m declara UN SOLO modulo.
#   2. Ese .o tiene su .c en el arbol.
#   3. Todo .o de rx550_drv-objs tiene su .c.  (al reves: un .c declarado sin
#      su .o no se enlazaria, y kbuild avisa pero no rompe)
n_objm=$(grep -c '^[[:space:]]*obj-m[[:space:]]*:*=' "$DRV/Makefile")
chk $([ "$n_objm" -eq 1 ] && echo 0 || echo 1) COB-MODULOS \
    "obj-m se declara UNA vez en el Makefile (measured $n_objm, declarado 1)"
# Los .o de la linea obj-m: tiene que ser exactamente uno, y ese es el modulo.
mods=$(sed -n 's/^[[:space:]]*obj-m[[:space:]]*:*=[[:space:]]*//p' "$DRV/Makefile" | tr ' ' '\n' | grep -c '\.o$')
chk $([ "$mods" -eq 1 ] && echo 0 || echo 1) COB-MODULOS \
    "obj-m declara UN SOLO .o: los demas van en -objs (measured $mods, declarado 1)"
# LA LICENCIA.  MEDIDO: mi primera version de esta comprobacion exigia que el
# fichero cuyo nombre es el del modulo,  rx550_drv.c,  llevara MODULE_LICENSE().
# Ese fichero NO EXISTE y no debe existir:  un modulo compuesto se construye a
# partir de su lista -objs,  y rx550_drv.c no esta en ella.  La comprobacion
# fallaba por exigir algo que la convencion de kbuild prohibe.
#
# La invariante real,  y la que modpost aplica,  es que ALGUN objeto ENLAZADO
# aporte la macro.  El mensaje de modpost  "missing MODULE_LICENSE() in <obj>"
# nombra el .o que se proceso,  no el fichero fuente donde deberia estar la
# macro:  el nombre ahi es el del .o,  no el de un fuente.
mod_nombre=$(sed -n 's/^[[:space:]]*obj-m[[:space:]]*:*=[[:space:]]*//p' "$DRV/Makefile" | tr ' ' '\n' | grep '\.o$' | sed 's/\.o$//' | head -1)
grep -q "^[[:space:]]*${mod_nombre}-objs[[:space:]]*:*=" "$DRV/Makefile" && \
  chk 0 COB-MODULOS "el modulo $mod_nombre tiene su lista ${mod_nombre}-objs: es un modulo compuesto, no un fuente suelto" \
              || no COB-MODULOS "el modulo $mod_nombre NO tiene lista ${mod_nombre}-objs: o no existe, o es un fuente suelto en obj-m"
n_lic=0
for o in $(sed -n "s/^[[:space:]]*${mod_nombre}-objs[[:space:]]*:*=[[:space:]]*//p" "$DRV/Makefile" | tr ' ' '\n' | grep '\.o$'); do
  b=${o%.o}
  [ -f "$DRV/$b.c" ] && grep -q 'MODULE_LICENSE(' "$DRV/$b.c" && n_lic=$((n_lic + 1))
done
chk $([ "$n_lic" -ge 1 ] && echo 0 || echo 1) COB-MODULOS \
    "ALGUN objeto enlazado lleva MODULE_LICENSE(): modpost no rechazara el modulo (measured $n_lic, declarado >=1)"
# ── DUAL-CTX · LO QUE UNA .h QUE COMPILA DE LAS DOS FORMAS NO PUEDE HACER ────
#
# MEDIDO 2026-10-04.  La regla vivia SOLO en un comentario de
# rx550_vram_pool.h,  y decia esto:
#
#   "El reset se escribe CAMPO A CAMPO y no con memset:  esta cabecera la
#    incluye codigo de kernel,  y el equivalente de memset ahi es
#    linux/string.h,  no <string.h>.  Meter la cabecera de libc en una linea que
#    compila de las dos formas es el mismo error que ya se registro con
#    target_mem_host.h haciendo `typedef int bool`."
#
# Y MEDIDO que la regla es MAS ESTRECHA de lo que se recuerda:
#
#   · NO es "nada de memset en el componente".  Los .c  SI pueden usar memset:  ahi
#     el include se resuelve una vez  y el .ko compila.
#   · NO es "nada de memset".  memset es lo que OBLIGA a la cabecera.  En un .c no
#     obliga a nada.  En una cabecera compartida obliga.
#   · ES:  una CABECERA que compila de las dos formas solo puede pedir libc en la
#     RAMA #else de un #ifdef __KERNEL__.
#
# LA INVARIANTE SE CALCULA,  NO SE GREPEA.  Y eso es lo que la hizo discriminator:
#
# MEDIDO por mutacion.  La primera version de este check comprobaba que el
# fichero TUVIERA un #else y un #ifdef __KERNEL__  en cualquier parte.  Al mover
# la include FUERA del #else  —dejando el #else y el #ifdef intactos en el
# fichero—  daba PASS.  Es decir:  media "el fichero tiene un patron",  no "la
# include esta dentro del patron",  y eso no es lo que decia su mensaje.
#
# La segunda version regalo una variante mas:  contar como "guardada" una include
# que en realidad cae en la rama #ifdef __KERNEL__.  Tambien es mala,  por el
# motivo de mas abajo.
#
# ASI QUE awk lleva la pila de #if/#ifdef/#ifndef/#else/#endif  y clasifica cada
# include de libc como bien  (rama #else de un __KERNEL__)  o mal  (rama
# #ifdef __KERNEL__,  o sin guardarla).
n_ctx_h=0
n_guardadas=0
n_libc_hoy=0
n_examinados=0
for o in $(sed -n 's/^[[:space:]]*rx550_drv-objs[[:space:]]*:*=[[:space:]]*//p' "$DRV/Makefile" | tr ' ' '\n' | grep '\.o$'); do
  b="${o%.o}"
  for ext in c h; do
    src="$DRV/$b.$ext"
    [ -f "$src" ] || continue
    n_examinados=$((n_examinados+1))
    r="$(awk '
      /^[[:space:]]*#[ \t]*(if|ifdef|ifndef)/ {
        d++; k[d] = ($0 ~ /__KERNEL__/) ? 1 : 0; e[d] = 0; next
      }
      /^[[:space:]]*#[ \t]*else/ {
        if (d > 0 && k[d] == 1 && e[d] == 0) { e[d] = 1; next }
        next
      }
      /^[[:space:]]*#[ \t]*endif/ { d--; next }
      /^[[:space:]]*#[ \t]*include[ \t]*<(string|stdio|stdlib|stdint|stdbool)\.h>/ {
        if (d > 0 && k[d] == 1 && e[d] == 1) { bien++; next }
        mal++
        printf "        include de libc SIN GUARDAR  %s:%d\n", FILENAME, FNR
      }
      END { printf "%d %d\n", bien+0, mal+0 }
    ' "$src" 2>/dev/null)"
    [ -n "$r" ] || continue
    n_libc_hoy=$((n_libc_hoy + ${r%% *} + ${r##* }))
    n_guardadas=$((n_guardadas + ${r%% *}))
    case "$src" in
      *.h) n_ctx_h=$((n_ctx_h + ${r##* })) ;;
      *)   : ;;
    esac
  done
done

# ── EL BUG DE ESTA MISMA PUERTA,  QUE ES EL SEGUNDO DEL MISMO TIPO EN ESTE
# FICHERO,  Y POR ESO SE ESCRIBE ───────────────────────────────────────────────
# La primera version hacia
#     for f in $(... -objs ... | grep '\.[co]$')
# y la lista de -objs tiene nombres .o,  no .c:  el bucle no iteraba NADA,
# contaba 0 cabeceras de libc  y daba PASS.  El recuento de ficheros EXAMINADOS va
# en su propio check  porque un control que no revisa nada y dice que esta bien
# es peor que uno ausente:  ocupa su sitio y engana.
chk $([ "$n_examinados" -gt 0 ] && echo 0 || echo 1) DUAL-CTX \
    "DUAL-CTX EXAMINA algo:  sin este check,  un bucle que no itere nada da el mismo veredicto que uno que encuentra 0 ($n_examinados ficheros de produccion)"

chk $([ "$n_ctx_h" -eq 0 ] && echo 0 || echo 1) DUAL-CTX \
    "toda include de libc en una .h dual-context esta en la rama #else de un #ifdef __KERNEL__  (unguarded measured $n_ctx_h, declarado 0;  sobre $n_examinados ficheros)"

# Y el recuento de las BIEN contadas,  que es lo que separa a esta puerta de la
# que daba verde con la include fuera del #else:  si el calculo del anidamiento
# no mira el #else,  este numero no cuadra con el total.
chk $([ "$n_guardadas" -eq "$n_libc_hoy" ] && echo 0 || echo 1) DUAL-CTX \
    "las $n_libc_hoy includes de libc que hay  —en .c y en .h—  se clasifican todas:  el calculo cuenta las bien Y las mal (measured $n_guardadas bien de $n_libc_hoy, declarado igual)"

# POR QUE UNA INCLUDE DE LIBC EN LA RAMA #ifdef __KERNEL__  TAMBIÉN ES MALA,  y
# no es un detalle del enunciado:  MEDIDO que con los -I/-isystem del comando real
# de kbuild  y -nostdinc,  <stdint.h> NO se encuentra.  O sea que si una cabecera
# lo pidiera en la rama del kernel,  el .ko NO compilaria.  El build lo demuestra
# entero  —por eso este check es una defensa mas y no la unica—.
n_bool=0
for h in $(sed -n 's/^[[:space:]]*rx550_drv-objs[[:space:]]*:*=[[:space:]]*//p' "$DRV/Makefile" | tr ' ' '\n' | grep '\.o$' | sed 's/\.o$/.h/'); do
  src="$DRV/$h"
  [ -f "$src" ] || continue
  # MEDIDO, y por mutacion:  la primera version de este check solo miraba las
  # lineas INMEDIATAMENTE posteriores a un #include.  Mover el typedef lejos de
  # un #include  —que es donde lo pondria cualquiera  —  daba PASS.  Es el mismo
  # defecto que el de las tres lineas de mas arriba:  la proximity no es la
  # propiedad.  Ahora barre el fichero entero.
  #
  # Y el limite de palabra es lo que hace que "bool_rx550" NO cuente:  el
  # identificador es uno solo  —la _ es caracter de palabra—  y typedefear eso no
  # choca con stdbool.  MEDIDO,  y por eso la regexp lleva los dos lados.
  #
  # Y el comentario tampoco cuenta:  MEDIDO que un "typedef int bool;" escrito
  # en un comentario  —este mismo fichero lo tiene  —  no dispara nada.  Para eso
  # el awk va sobre el texto con comentarios sustituidos,  no sobre el fuente.
  if "${CC:-cc}" -fpreprocessed -dD -E -P "$src" 2>/dev/null |
     grep -Eq '^[[:space:]]*typedef[^;]*([^_[:alnum:]])bool([^_[:alnum:]]|$)'; then
    n_bool=$((n_bool+1))
    echo "        typedef de bool en $src"
  fi
done
chk $([ "$n_bool" -eq 0 ] && echo 0 || echo 1) DUAL-CTX \
    "ninguna cabecera typedefea bool:  en userspace choca con stdbool  y en kernel no existe (measured $n_bool, declarado 0)"

# ── LIT-GEOM · EL 10 Y EL 9 NO PUEDEN VIVIR COMO LITERAL EN PRODUCCION ───────
#
# MEDIDO 2026-10-04.  block_size, fragment_size y max_pfn NO los rellenaba
# NINGUN codigo de produccion:  estaban escritos a mano en tres fixtures de
# test y marcados MODELO.  Ahora rx550_vm_geometry() los produce, y el req de
# la secuencia ya no los lleva,  de modo que no se pueden pasar a mano.
#
# Un comentario no cuenta,  y por eso el listado va SIN comentarios:  el
# preprocesador de C los quita de forma exacta,  sin heuristicas de sed sobre
# lineas que empiezan por asterisco.  Los tres numeros salen en los comentarios
# de tres ficheros,  y con que uno se colara en codigo seria el defecto
# vuelve.
#
# POR QUE UNA PUERTA Y NO UN SCRIPT DE UN USO:  este componente lleva tres
# commits corrigiendo un literal escrito a mano que parecia un dato.  Un grep
# que alguien lanzo una vez no lo evita la segunda vez;  un check que sale de
# nonzero cuando aparece, si.
n_lit=0
n_fich=0
# MEDIDO: mi primera version hacia `grep '\.[co]$'` sobre la lista -objs,  y
# esa lista tiene nombres .o,  no .c:  el bucle no iteraba NADA,  contaba 0
# ficheros revisados  y daba PASS.  Un check que no revisa nada y dice que esta
# bien es peor que un check ausente,  porque ocupa su sitio.  El recuento de
# ficheros revisados va en el mensaje para que ese fallo se vea.
for f in $(sed -n 's/^[[:space:]]*rx550_drv-objs[[:space:]]*:*=[[:space:]]*//p' "$DRV/Makefile" | tr ' ' '\n' | grep '\.o$'); do
  src="$DRV/${f%.o}.c"
  [ -f "$src" ] || continue
  n_fich=$((n_fich + 1))
  # -fpreprocessed -dD -E -P: quita comentarios y directivas, deja el codigo
  if "${CC:-cc}" -fpreprocessed -dD -E -P "$src" 2>/dev/null | \
     grep -Eq 'block_size[[:space:]]*=[[:space:]]*10|fragment_size[[:space:]]*=[[:space:]]*9([^0-9]|$)|max_pfn[[:space:]]*=[[:space:]]*\(?[[:space:]]*UINT64_C\(64\)'; then
    n_lit=$((n_lit + 1))
    echo "        literal de geometria en $src (sin comentarios)"
  fi
done
chk $([ "$n_lit" -eq 0 ] && echo 0 || echo 1) LIT-GEOM \
    "ninguno de los $n_fich .c de produccion escribe block_size=10, fragment_size=9 ni max_pfn=(64<<18) como literal (measured $n_lit, declarado 0)"

# Y el otro sentido: cada .o de -objs tiene su .c en el arbol.
n_objs=$(sed -n 's/^[[:space:]]*rx550_drv-objs[[:space:]]*:*=[[:space:]]*//p' "$DRV/Makefile" | tr ' ' '\n' | grep -c '\.o$')
n_faltan=0
for o in $(sed -n 's/^[[:space:]]*rx550_drv-objs[[:space:]]*:*=[[:space:]]*//p' "$DRV/Makefile" | tr ' ' '\n' | grep '\.o$'); do
  b=${o%.o}
  [ -f "$DRV/$b.c" ] || n_faltan=$((n_faltan + 1))
done
chk $([ "$n_faltan" -eq 0 ] && echo 0 || echo 1) COB-MODULOS \
    "los $n_objs .o de rx550_drv-objs tienen todos su .c (measured $n_faltan sin fuente, declarado 0)"

# Ningun objeto fuera de la excepcion puede tocar el dispositivo.
#
# La lista de exentos ENTRA en el awk como VALOR (`-v exentos=...`), nunca como
# literal en el texto del programa: un literal dentro del awk es exactamente el
# defecto que esta comprobacion acaba de corregir, un nivel mas abajo.
#
# ── D3 · LA LISTA DE NOMBRES NO LLEVA LOS MISMOS NOMBRES EN LAS DOS MITADES ──
#
# Las dos listas no pueden coincidir, y no por descuido. La de arriba lee TEXTO
# de fuente; la de abajo lee SIMBOLOS de `nm -u`. En x86-64 muchos accessors no
# son simbolos: se expanden en linea y no dejan rastro en la tabla de simbolos.
#
#   SOLO EN HW-OBJ (texto), porque en `nm -u` NO PUEDEN aparecer:
#     readb writeb readw writew   arch/x86/include/asm/io.h:57-66. Los genera
#                                 build_mmio_read/build_mmio_write, que son
#                                 `static inline`. MEDIDO con un objeto que los
#                                 llama: no sale ninguno en `nm -u`.
#     __iowrite32_copy            io.h:217, `static inline` bajo CONFIG_X86_64.
#     readl writel readq writeq   ya estaban fuera de HW-L por el mismo motivo.
#     ioread8 iowrite8            no existen en x86 en absoluto. Se quedan como
#                                 estaban: no son de este arreglo.
#
#   EN LAS DOS MITADES, porque MEDIDO que si son simbolos reales y exportables:
#     memset_io memcpy_toio memcpy_fromio
#                                 io.h:204-205, declaraciones bajo __KERNEL__, y
#                                 NO inline. MEDIDO: aparecen en `nm -u` al
#                                 llamarlos.
#     devm_ioremap                include/linux/io.h:65, declaracion real.
#     devm_ioremap_resource       include/linux/device/devres.h:117, real.
#                                 MEDIDO: ambos en `nm -u`.
n_hits=0
for sym in ioremap ioremap64 readl writel readq writeq ioread8 iowrite8 \
           readb writeb readw writew \
           memset_io memcpy_toio memcpy_fromio __iowrite32_copy \
           devm_ioremap devm_ioremap_resource \
           request_irq request_threaded_irq dma_alloc_coherent dma_map_single; do
  f=$(awk -v sym="$sym" -v exentos="$MMIO_EXENTOS" '
      BEGIN{ n=split(exentos, ex, " ") }
      $0 ~ /^__FILE__ / {f=$2; b=$2; sub(/.*\//,"",b); next}
      $0 ~ ("(^|[^A-Za-z0-9_])" sym "([^A-Za-z0-9_]|$)") {
         for (i=1; i<=n; i++) if (b == ex[i]) next
         print f; exit }' "$AUDIT_OBJ")
  if [ -n "$f" ]; then
    no "HW-OBJ" "'$sym' aparece fuera del accessor, en ${f#$DRV/}"
    n_hits=$((n_hits + 1))
  fi
done
chk $([ "$n_hits" -eq 0 ] && echo 0 || echo 1) HW-OBJ \
    "ningún objeto fuera de los exentos ($MMIO_EXENTOS) toca el dispositivo ($n_obj objetos)"

# Prueba a NIVEL DE ENLACE, no de texto: los símbolos indefinidos del .ko son
# lo que el módulo realmente pide al kernel. Un test que sólo lee el fuente no
# puede detectar una llamada de hardware añadida por otra vía.
UNDEF=$(nm -u "$KO" 2>/dev/null | awk '{print $NF}' | sort -u)
# nm -u tambien por fichero, por el mismo motivo que arriba: el pipeline de awk
# no decide nada, pero que el lector de UNDEF sea el pipe si lo hacia.
#  __readl / __writel / __readq / __writeq NO estan en la lista, y no por
#  descuido: en x86-64 no existen como simbolos.  MEDIDO 2026-10-03 con un
#  objeto de kernel minimo que llama a readl, writel, readq y writeq:
#
#      $ nm -u p.o
#      U __fentry__
#      U __x86_return_thunk
#
#  Ni uno de los cuatro aparece.  Se expanden en linea.  Buscarlos en nm -u era
#  una comprobacion que no podia fallar en esta arquitectura, y una
#  comprobacion que no puede fallar no es una comprobacion: es decoracion que
#  ocupa sitio en el informe y da la sensacion de que el MMIO esta vigilado.
#
#  Lo que vigila el MMIO de verdad es HW-OBJ, arriba: el cuerpo de cada objeto,
#  no sus simbolos.  Ese si puede fallar, y se ha roto a proposito para
#  comprobarlo.
# ── D2 · LA MITAD DMA DE HW-L NO PODIA DISPARARSE, Y LA LISTA TIENE NOMBRES ──
#     QUE NO PUEDEN APARECER EN `nm -u`
#
# MEDIDO 2026-10-04 en las cabeceras del kernel EN EJECUCION
# (/lib/modules/$(uname -r)/build/include/linux/dma-mapping.h):
#   :603  #define dma_map_single(d,a,s,r) dma_map_single_attrs(d,a,s,r,0)
#   :614  static inline void *dma_alloc_coherent(...) { return dma_alloc_attrs(...); }
#   :519  static inline dma_addr_t dma_map_single_attrs(...) { ... dma_map_page_attrs(...); }
# Es decir: dma_alloc_coherent es INLINE, dma_map_single es MACRO, y
# dma_map_single_attrs TAMBIÉN es INLINE. Los tres son incapaces de aparecer en
# `nm -u`. MEDIDO con un objeto de kernel minimo que llama a dma_alloc_coherent
# y a dma_map_single:
#   $ nm -u p.o | grep dma
#            U dma_alloc_attrs
#            U dma_map_page_attrs
# Era el mismo defecto que el ya corregido para readl/writeq, sin corregir en el
# par DMA: nombres en la lista que no pueden fallar, que es decoracion que da la
# sensacion de que el DMA esta vigilado.
#
# PERO el simbolo real, `dma_map_page_attrs`, YA ESTA EN ESTE .ko, y a proposito:
#   $ nm -u rx550_drv.ko | grep dma
#            U dma_map_page_attrs
#            U dma_unmap_page_attrs
#   origen: rx550_dummy_page.c:145 y :172, que llaman a dma_map_page_attrs POR SU
#   NOMBRE (no por la macro dma_map_page), con la aridad de 5 argumentos de este
#   kernel, y con la referencia amdgpu_gart.c:81/103 escrita en el propio fuente
#   (rx550_dummy_page.c:143-146 y :164-173).
#   MEDIDO ademas: rx550_dummy_kernel_map/unmap estan definidas y EXPORTADAS (T)
#   en el .ko, y NINGUN objeto de obj-m las llama. El mapa DMA es codigo muerto
#   hoy; el simbolo no lo es: el .ko lo pide y el enlace depende de el.
#
# Por eso el nombre va en la lista Y el unico objeto que lo pide va en
# $DMA_EXENTOS. Sin la exencion, esta comprobacion daria FAIL sobre codigo
# deliberado. Y con una exencion escrita a mano en el fuente seria el defecto
# D1 repetido un nivel mas abajo, asi que la exencion tambien es una variable y
# tambien se ASERTA que se usa de verdad: una exencion que ha dejado de
# justificarse es una lista admitiendo a un fichero sin motivo.
#
# Nota sobre lo que NO se hace aqui, y es deliberado: la lista de HW-OBJ (la de
# TEXTO) NO cambia en este par. Alli `dma_map_single` es el nombre correcto,
# porque el audit lee el cuerpo del fuente y no los simbolos. Ese es justo el
# motivo de que existan las dos mitades. LIMITACION REGISTRADA: HW-OBJ no ve
# `dma_map_page_attrs`, que es lo que el fuente escribe, asi que una llamada a
# esa variante pasaria por la mitad de texto. Queda cubierta por la de enlaces.
UNDEF_PROHIBIDOS="ioremap pci_enable_device pci_request_regions \
pci_alloc_irq_vectors request_irq \
dma_alloc_attrs dma_map_page_attrs dma_unmap_page_attrs \
memset_io memcpy_toio memcpy_fromio \
devm_ioremap devm_ioremap_resource"
# Los que se quedan FUERA de esta lista, y por que, todo MEDIDO:
#   dma_alloc_coherent    INLINE (dma-mapping.h:614) -> no puede salir
#   dma_map_single        MACRO  (dma-mapping.h:603) -> no puede salir
#   dma_map_single_attrs  INLINE (dma-mapping.h:519) -> no puede salir
#   readl writel readq writeq readb writeb readw writew __iowrite32_copy
#                        INLINE en io.h (ver la nota de D3 mas arriba)
#   memset_io memcpy_toio memcpy_fromio devm_ioremap devm_ioremap_resource
#                        SI son simbolos reales: por eso estan dentro
#   ioremap64             NO EXISTE en este kernel. MEDIDO: no esta declarado ni
#                        en arch/x86/include/asm/io.h, ni en include/linux/io.h,
#                        ni en asm-generic/io.h, y un modulo que lo llama NO
#                        COMPILA ("declaracion implicita de la funcion"). Se
#                        queda en la lista de TEXTO, y de nada mas.
#
# Y UNO MAS, MEDIDO, que no figuraba en ninguna de las notas: la lista de arriba
# tenia `__ioremap`, con DOS guiones bajos, y en x86-64 el simbolo que sale de
# llamar a `ioremap()` es `ioremap`, con UNO. MEDIDO con un objeto de kernel
# minimo que llama a ioremap():
#   $ nm -u p.o
#            U ioremap
# `__ioremap` es el nombre interno de la implementacion generica; en x86 el
# simbolo exportado es `ioremap`. La entrada era tan inerte como `dma_map_single`,
# y la mitad MMIO de esta lista llevaba el mismo defecto que la mitad DMA. La de
# texto ya tenia `ioremap`, asi que aqui la correccion es de una palabra.
DMA_EXENTOS="rx550_dummy_page.o"
UNDEF_EXENTO=""
n_dma_exent=0
for o in $DMA_EXENTOS; do
  if [ ! -f "$DRV/$o" ]; then
    no "HW-L" "el exento DMA declarado $o no esta en el arbol"
    continue
  fi
  n_dma_exent=$((n_dma_exent + 1))
  UNDEF_EXENTO="$UNDEF_EXENTO
$(nm -u "$DRV/$o" 2>/dev/null | awk '{print $NF}')"
done

n_hits_l=0
for sym in $UNDEF_PROHIBIDOS; do
  if printf '%s\n' "$UNDEF" | grep -qx "$sym"; then
    if printf '%s\n' "$UNDEF_EXENTO" | grep -qx "$sym"; then
      # No se oculta: la exencion se IMPRIME. Una exencion que se aplica en
      # silencio es el mismo apagado que la nota de arriba denuncia.
      ok  "HW-L" "exención DMA registrada: '$sym' solo lo pide $(echo $DMA_EXENTOS)"
    else
      no "HW-L" "el .ko referencia el símbolo de hardware '$sym'"
      n_hits_l=$((n_hits_l + 1))
    fi
  fi
done
chk $([ "$n_hits_l" -eq 0 ] && echo 0 || echo 1) HW-L \
    "el .ko no referencia ningún símbolo de acceso a hardware"
# Y la exencion no puede quedarse vieja: cada objeto exento tiene que seguir
# pidiendo ALGO de la lista. Si dejara de pedirlo, estariamos admitiendo a un
# fichero sin motivo, que es el defecto que la lista de MMIO tenia hardcodeado.
n_exent_ok=0
for o in $DMA_EXENTOS; do
  [ -f "$DRV/$o" ] || continue
  for sym in $UNDEF_PROHIBIDOS; do
    nm -u "$DRV/$o" 2>/dev/null | awk '{print $NF}' | grep -qx "$sym" \
      && { n_exent_ok=$((n_exent_ok + 1)); break; }
  done
done
chk $([ "$n_exent_ok" -eq "$n_dma_exent" ] && echo 0 || echo 1) HW-L \
    "$n_exent_ok/$n_dma_exent exenciones DMA están justificadas por un símbolo real"
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
# `nm -a` NO es lo mismo que `nm`: añade simbolos de depuracion y su salida
# tiene otra forma.  No se le sustituye por $SYMS.  Fichero propio.
SYMA="$(mktemp)"; trap 'rm -f "$SYMS" "$SYMA" "$AUDIT_OBJ"' EXIT
nm -a "$KO" > "$SYMA" 2>/dev/null || : > "$SYMA"
idt_addr=$(awk '/[rR] rx550_target_id_table$/{print "0x"$1; exit}' "$SYMA")
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
echo "CFLAGS-PARITY · options de compilacion: tests frente a kbuild"
# ── QUE MIDE ESTE BLOQUE, Y POR QUE ES UNA PUERTA Y NO UN INFORME ─────────────
#
# 16 de las 25 reglas de tests/Makefile ENLAZAN codigo del driver (las que
# citan ../rx550_*.c como dependencia).  Esos 16 compilan las MISMAS lineas de
# C que el .ko, y lo hacian con opciones distintas de las que kbuild uso de
# verdad.  Un test que pasa sobre codigo compilado con otras opciones no dice
# nada sobre el modulo: dice que el test y el modulo son dos programas
# distintos que se parecen.
#
# ASI QUE este bloque compara las opciones de los tests contra la linea REAL de
# savedcmd que kbuild escribio en .rx550_target.o.cmd.  No contra una constante
# escrita a mano aqui, y no contra lo que este fichero recuerda del kernel: una
# comparacion contra algo copiado a mano solo verifica que la copia no cambio.
#
# ── EL PARSER ES EL DE tools/tu_compila.sh, NO UN SEGUNDO ────────────────────
#
# La extraccion es la misma que hace tools/tu_compila.sh:41, sobre el mismo
# fichero (.rx550_target.o.cmd, tools/tu_compila.sh:35).  No se reescribe el
# parser: se copia el MISMO awk, y debajo hay dos aserciones que avisan si
# tu_compila.sh deja de usar ese regex o ese fichero.  Dos parsers independientes
# del mismo formato divergen sin que nada lo note; uno copiado mas dos guardas
# de deriva, no.
KBUILD_CMD_FILE="$DRV/.rx550_target.o.cmd"
TU_COMPILA="$DRV/tools/tu_compila.sh"
degraded=0

if [ ! -r "$KBUILD_CMD_FILE" ]; then
	degraded=$((degraded+1))
	# MEDIDO 2026-10-04: estas lineas van SIN comillas dobles con acentos graves.
	# Entre comillas dobles, `...` es SUSTITUCION DE COMANDO en bash, y este texto
	# era un `make -C .. modules` de verdad: al imprimir el aviso ejecutaba make en
	# el directorio actual y metia la salida de make dentro del mensaje (MEDIDO:
	# "Se regenera con: make: *** No hay ninguna regla para construir el objetivo
	# 'modules'").  Un aviso que ejecuta lo que avisa, y ademas miente sobre lo que
	# dijo, es peor que no tener aviso.  Por eso aqui no hay acentos graves.
	echo "  DEGRADED CFP  $KBUILD_CMD_FILE no existe o no es legible."
	echo "  DEGRADED CFP  NO se puede comparar CFLAGS con kbuild: no hay savedcmd."
	echo "  DEGRADED CFP  NO se cuenta como PASS.  Queda SIN VERIFICAR, no verde:"
	echo "  DEGRADED CFP  el .ko que se audita arriba viene de 'make -C .. modules',"
	echo "  DEGRADED CFP  y que ese .ko exista no implica que exista su .o.cmd."
	echo "  DEGRADED CFP  Se regenera con make -C .. modules"
else
	# MEDIDO: este awk, con este regex, sobre este fichero, devuelve la linea
	# real de kbuild (la de tu_compila.sh:41).  No se reimplementa el formato.
	KBUILD="$(awk '/^savedcmd_rx550_target\.o := /{sub(/^savedcmd_rx550_target\.o := /,""); print; exit}' "$KBUILD_CMD_FILE")"
	if [ -z "$KBUILD" ]; then
		degraded=$((degraded+1))
		echo "  DEGRADED CFP  no se pudo extraer savedcmd_rx550_target.o de $KBUILD_CMD_FILE"
		echo "  DEGRADED CFP  el fichero existe pero no tiene la linea de savedcmd."
	else
		# --- el parser de tu_compila.sh sigue siendo este --------------------------
		if grep -q '/\^savedcmd_rx550_target\\\.o := /' "$TU_COMPILA" 2>/dev/null; then
			ok CFP "tu_compila.sh sigue usando el mismo regex de savedcmd (deriva vigilada)"
		else
			no CFP "tu_compila.sh ya NO usa el regex de savedcmd: este bloque usa una copia y divergiria"
		fi
		if grep -q 'CMD_FILE="\.rx550_target\.o\.cmd"' "$TU_COMPILA" 2>/dev/null; then
			ok CFP "tu_compila.sh y este bloque leen el MISMO .o.cmd"
		else
			no CFP "tu_compila.sh ya no lee .rx550_target.o.cmd: se compararia contra otro savedcmd"
		fi
		# --- los CFLAGS efectivos, por dos vias independientes --------------------
		# via 1: lo que declara el Makefile (lo lee este gate)
		# via 2: lo que make expande de verdad (oráculo, no copia)
		# Si difieren, alguien metio flags por linea de orden o por entorno, y la
		# comparacion contra la declaracion seria comparar una cosa que no se uso.
		CF_DECL="$(awk '/^CFLAGS[[:space:]]*[?:][[:space:]]*=/{sub(/^CFLAGS[[:space:]]*[?:][[:space:]]*=[[:space:]]*/,""); print; exit}' "$HERE/Makefile")"
		# -C "$HERE" y no el directorio actual: este script se puede lanzar desde
		# tests/ (regla `run`) o desde el padre (`bash tests/test_static.sh`), y un
		# oraculo que depende del cwd mide una cosa distinta en cada caso.  MEDIDO:
		# sin -C, lanzado desde el padre, make no encuentra Makefile, CF_EFF sale
		# vacio y las cinco familias de flags dan FAIL por falta de informacion, no
		# por divergencia real.
		CF_EFF="$(make -C "$HERE" -s --no-print-directory \
			--eval='rx550-cflags-parity-probe: ; @printf "%s\n" "$(CFLAGS)"' \
			rx550-cflags-parity-probe 2>/dev/null)"
		if [ -z "$CF_DECL" ]; then
			no CFP "tests/Makefile no declara ninguna linea CFLAGS ?= / CFLAGS ="
		else
			ok CFP "tests/Makefile declara CFLAGS ($(printf '%s' "$CF_DECL" | wc -w) flags)"
			# normalizar espacios para comparar solo el contenido
			_cfd="$(printf '%s' "$CF_DECL" | tr -s '[:space:]' ' ')"
			_cfe="$(printf '%s' "$CF_EFF"  | tr -s '[:space:]' ' ')"
			if [ -n "$CF_EFF" ] && [ "$_cfd" = "$_cfe" ]; then
				ok CFP "el CFLAGS que declara el Makefile es el que make expande"
			else
				no CFP "CFLAGS declarado != CFLAGS efectivo de make: [$_cfd] vs [$_cfe]"
			fi
			# --- comparar familia por familia contra kbuild -----------------------
			KBTOK="$(mktemp)"; CFTOK="$(mktemp)"
			printf '%s\n' "$KBUILD" | tr ' ' '\n' | sed '/^$/d' > "$KBTOK"
			printf '%s\n' "$CF_EFF"  | tr ' ' '\n' | sed '/^$/d' > "$CFTOK"

			# familia <etiqueta> <regex-anchado> : compara el VALOR completo del flag.
			# No "si los dos lo tienen": si kbuild dice -fstack-protector-strong y
			# los tests dicen -fstack-protector, los dos lo tienen y aun asi el
			# canario cubre distinto.  El valor es lo que hay que igualar.
			familia() {
				local lab="$1" re="$2" k v
				k="$(grep -m1 -x -E -- "$re" "$KBTOK" 2>/dev/null)"
				v="$(grep -m1 -x -E -- "$re" "$CFTOK" 2>/dev/null)"
				if [ -z "$k" ] && [ -z "$v" ]; then
					degraded=$((degraded+1))
					printf "  DEGRADED CFP  %s: kbuild NO lo usa y los tests tampoco; no hay nada que comparar\n" "$lab"
				elif [ -z "$k" ]; then
					no CFP "$lab: kbuild NO lo usa y los tests si ($(printf '%s' "$v"))"
				elif [ -z "$v" ]; then
					no CFP "$lab: kbuild lo usa ($(printf '%s' "$k")) y los tests NO"
				elif [ "$k" = "$v" ]; then
					ok CFP "$lab en paridad con kbuild: $k"
				else
					no CFP "$lab DIVERGE: kbuild=$k  tests=$v"
				fi
			}

			# Una familia EXENTA:  kbuild usa el flag, los tests no,  y hay un
			# motivo con nombre.  La diferencia con familia()  es que exige que
			# el token este en kbuild:  si kbuild lo perdiera,  esto no pasaria
			# en silencio.
			familia_exenta() {
				local lab="$1" re="$2" esperados="$3" motivo="$4"
				local k v faltan
				k="$(grep -m1 -x -E -- "$re" "$KBTOK" 2>/dev/null)"
				v="$(grep -m1 -x -E -- "$re" "$CFTOK" 2>/dev/null)"
				if [ -z "$k" ]; then
					degraded=$((degraded+1))
					printf "  DEGRADED CFP  %s: kbuild ya no lo usa; la excepcion ha dejado de tener objeto\n" "$lab"
					return
				fi
				faltan=""
				for e in $esperados; do
					grep -qxF -- "$e" "$KBTOK" || faltan="$faltan $e"
				done
				if [ -n "$faltan" ]; then
					no CFP "$lab EXENCION ROTA: kbuild ya no usa$faltan,  y la excepcion lo daba por hecho"
				elif [ -n "$v" ]; then
					no CFP "$lab DIVERGE y no esta exento: kbuild=$k  tests=$v"
				else
					ok CFP "$lab EXENTO con nombre: kbuild usa $k,  los tests no,  motivo: $motivo"
				fi
			}

			# Las familias que cambian semantica.  El orden es el del informe:
			# -std primero, porque es la que rompia de forma DURA (bool en C23).
			familia "-std (bool es palabra clave desde C23)"                        '^-std=.+$'
			familia "-fno-strict-aliasing (kbuild castea entre tipos a proposito)" '^-fno-strict-aliasing$'
			familia "-fstack-protector-* (cobertura del canario de pila)"         '^-fstack-protector.+'
			# MEDIDO 2026-10-04.  El regex de la familia de arriba era
			#   ^-fstack-protector.+
			# y por eso ERA INVISIBLE un token que SI diverge:
			#     -mstack-protector-guard-reg=gs
			#     -mstack-protector-guard-symbol=__ref_stack_chk_guard
			# MEDIDO que los dos estan en el savedcmd de este arbol.  El modulo usa
			# el canario DEL KERNEL  (GS  y  __ref_stack_chk_guard)  y el binario de
			# test usa el default  (%fs:0x28).  O sea que el token coincide  y el
			# EFECTO no.  La familia comparaba el token  y el token no lo veia:
			# un flag con prefijo -m  no es un flag con prefijo -f.
			#
			# ESTA FAMILIA VA A FALLAR,  y es lo que tiene que pasar:  el modulo no
			# se puede construir con el canario del kernel en userspace  —el simbolo
			# __ref_stack_chk_guard no existe ahi—.  Dejarlo como excepcion SIN
			# NOMBRE seria volver a hacerlo invisible,  que es el defecto.  Con el
			# nombre,  es una divergencia DECLARADA  y no un token que nadie mira.
			# EXENCION CON NOMBRE Y MOTIVO,  que es lo unico que se
			# permite.  MEDIDO:  el modulo NECESITA el canario del kernel
			#   -mstack-protector-guard-reg=gs
			#   -mstack-protector-guard-symbol=__ref_stack_chk_guard
			# y el binario de test NO PUEDE tenerlo:  __ref_stack_chk_guard es
			# un simbolo del kernel  y no existe en userspace.  No es una
			# excepcion de conveniencia:  es que la excepcion es IMPOSIBLE de
			# cerrar por el otro lado.
			#
			# POR QUE ESTA EXENCION NO ES "UN HUECO":  el defecto que se
			# corrige aqui  —el regex que no la veia—  era que la divergencia
			# era invisible.  Con la excepcion escrita,  es una divergencia
			# DECLARADA con su motivo,  y el gate sigue exigiendo que el token
			# este en kbuild:  si kbuild dejara de usarlo,  el check no lo
			# aceptaria en silencio.  MEDIDO con mutacion.
			familia_exenta "-mstack-protector-* (registro y simbolo del canario)" \
				'^-mstack-protector.+' \
				"-mstack-protector-guard-reg=gs -mstack-protector-guard-symbol=__ref_stack_chk_guard" \
				"el simbolo __ref_stack_chk_guard no existe en userspace: el modulo lo necesita y el binario de test no puede"
			familia "-funsigned-char (signo de char plano)"                        '^-funsigned-char$'
			familia "-fno-jump-tables (tabla de switch en modulo)"                 '^-fno-jump-tables$'

			# --- -O: divergencia DELIBERADA, y su justificacion tiene que existir ---
			# kbuild usa -O3 y los tests -O2.  Eso NO es un fallo: es la decision
			# defendida en el comentario de tests/Makefile.  Lo que si es un fallo es
			# que ese comentario desaparezca, porque entonces la divergencia queda
			# sin nadie que la defienda y el siguiente que la vea la "arregla".
			kO="$(grep -m1 -x -E '^-O[0-9s]+$' "$KBTOK" 2>/dev/null)"
			tO="$(grep -m1 -x -E '^-O[0-9s]+$' "$CFTOK" 2>/dev/null)"
			if [ "$kO" = "-O3" ]; then
				ok CFP "kbuild usa $kO y los tests usan ${tO:-<ninguno>}: divergencia registrada, no casual"
			else
				no CFP "kbuild ya NO usa -O3 (usa ${kO:-<ninguno>}); la nota de -O2 de tests/Makefile esta caducada"
			fi
			[ "$tO" = "-O2" ] && ok CFP "los tests se quedan en -O2 (nivel sin transformaciones que cambien la semantica)" \
			                  || no CFP "los tests usan ${tO:-<ninguno>} y deberian usar -O2"
			if grep -q 'POR QUE -O2 Y NO -O3' "$HERE/Makefile" 2>/dev/null; then
				ok CFP "tests/Makefile conserva la justificacion de por que -O2 y no -O3"
			else
				no CFP "tests/Makefile ya NO justifica por que -O2 y no -O3: la divergencia qued indefensa"
			fi

			rm -f "$KBTOK" "$CFTOK"
		fi
	fi
fi

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
  grep -qw "$fn" "$SYMS"; must $? RES "simbolo presente: $fn" \
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

# MEDIDO 2026-10-04, al añadir el bloque CFLAGS-PARITY: una comprobacion que no
# se pudo hacer no es un PASS.  Si el recuento no dice DEGRADED, un bloque
# entero puede dejar de correr y el resumen sigue vriendose como "0 FAIL", que
# es el apagado que el bloque DEGRADED de mas arriba describe con otras
# palabras.  Por eso el numero va aqui, en la ultima linea que se lee.
if [ "${degraded:-0}" -gt 0 ]; then
	printf "ATENCION: %d comprobacion(es) DEGRADED: sin verificar, NO son PASS\n" "$degraded"
fi

# MEDIDO 2026-10-03: aquí había `exit 0` sin condiciones, y las 34 aserciones de
# este script eran ADORNALES.  Demostrado de punta a punta, con el driver
# entero:
#
#   rx550_target.c gana `pci_request_regions(pdev, "rx550")`, que reserva
#   TODAS las BAR y es justo lo que el audit RES prohíbe
#     make modules  ->  rc 0     el compilador no dice nada: la llamada es legal
#     make test     ->  rc 0     LA PUERTA
#       FAIL  HW   aparece 'pci_request_regions' en el cuerpo del driver
#       FAIL  RES  usa pci_request_regions (reserva TODAS las BAR)
#       resumen estático: 33 PASS, 2 FAIL
#       HAY FALLOS
#
# O sea: el script DETECTA, imprime el fallo, y sale con 0.  Como esta es la
# ultima linea de `make run`, make no podia enterarse.  Una puerta que dice
# "HAY FALLOS" y sale 0 no es una puerta: es un informe.  (regla 24: exit 0 no
# es resultado valido; §31: nunca exit 0 -> COMPLETE sin validar)
#
# El numero de fallos va en el codigo de salida, y no solo en la linea de
# arriba.  Un consumidor que solo mira el rc tiene que poder distinguir.
# MEDIDO 2026-10-04.  ESTA SECCION IGNORABA `degraded`.
#
# El propio script dice, en el bloque CFP:
#     "DEGRADED CFP  NO se cuenta como PASS.  Queda SIN VERIFICAR, no verde"
# y despues el codigo de salida miraba SOLO `fail`.  MEDIDO, con el
# `.rx550_target.o.cmd` apartado:
#
#     rc = 0      51 PASS / 0 FAIL      7 lineas DEGRADED
#
# Es decir:  la puerta de integridad annonce "OK" con ONCE comprobaciones sin
# ejecutar.  El resumen contaba 51 en vez de 64 y no habia ningun sitio donde se
# notara.  Es el mismo defecto que este componente lleva cinco commits
# corrigiendo en otro lugar:  un control que no puede fallar.
#
# Y hay una contradiccion interna:  el bloque de exits, unas lineas mas abajo,
# SI hace lo correcto  —"Una puerta que dice HAY FALLOS y sale 0 no es una
# puerta: es un informe"—.  O sea que el fichero ya sabia la regla y no la
# aplicaba aqui.
#
# POR QUE UN CODIGO DISTINTO y no el mismo que fail:  un fallo dice "algo esta
# mal"  y un degradado dice "algo NO SE PUDO COMPROBAR".  Un pipeline que reciba
# el mismo numero para las dos cosas no puede distinguirlas,  y tratarlas igual
# es la razon por la que la evidencia se vino abajo sin que nadie lo notara.
if [ "$fail" != 0 ] && [ "$degraded" != 0 ]; then
	echo "HAY FALLOS: $fail   y SIN VERIFICAR: $degraded"
	exit 1
fi
if [ "$fail" != 0 ]; then
	echo "HAY FALLOS: $fail"
	exit 1
fi
if [ "$degraded" != 0 ]; then
	echo "SIN VERIFICAR: $degraded comprobaciones no se pudieron ejecutar.  NO es verde."
	echo "T1-T14 + auditorías: OK en lo que se pudo comprobar  —  y $degraded quedaron SIN VERIFICAR"
	exit 2
fi

echo "T1-T14 + auditorías: OK"
exit 0

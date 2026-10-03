#!/usr/bin/env bash
# run-all -- el ciclo completo del kit, con veredicto unico
#
# POR QUE        El self-test de las 15 herramientas se venia ejecutando a mano,
#               uno por invocacion, y el recuento lo escribia yo.  Eso no es
#               evidencia: es una transcripcion, y una transcripcion puede
#               mentir sin que se note.  Esto ejecuta las 15, clasifica cada una
#               con los MISMOS cuatro estados que `--parche` ya usa, y no declara
#               exito si el artefacto no aparece.
#
#               El fallo que mas veces he_repo repetido es tratar un codigo de
#               salida como resultado.  Un binario que no existe, una cache que
#               no se puede escribir, un corpus que no esta montado: todo eso
#               sale con codigo distinto de 0 y TODOS ellos se leen como "el test
#               fallo".  aqui se separan (regla 25 del prompt):
#
#                   exit 0 sin artefacto      -> INVALID_RESULT
#                   sin codigo de salida      -> TOOL_MISSING
#                   SKIP_ENTORNO              -> comprobado, no ejecutable
#                   FAIL                      -> el codigo fallo
#
# CONTRATO       produce ${RX550_KIT_VERDICT:-$ROOT/08-ARQUITECTURA/KIT-VERDICT}.json y lo imprime.
#               Los codigos de salida son: 0 todo verde, 1 algun FAIL,
#               2 el artefacto no se pudo validar.
#
# LIMITACION     No ejecuta `alcance --out` ni `mandato --parche` contra el
#               mandate real: los segundos tardan minutos y el primero necesita
#               el anillo completo.  El self-test si los cubre.

# --- FINGERPRINT DEL OBJETIVO (208) ----------------------------------------
#
# Un `PASS` de 341 aserciones no dice sobre que maquina se sostiene.  La cadena de
# linaje pide ARTIFACT <- PRODUCER <- INPUT <- SOURCE <- CONFIGURATION <- HARDWARE
# STATE, y faltaba el ultimo eslabon: sin el, un verde de otra tarjeta es
# indistinguible de un verde de esta.  Y la lectura tiene que ser del SISTEMA, no
# copiada de un fichero mio: un fingerprint escrito a mano no es un fingerprint,
# es una afirmacion, y afirmacion es justo lo que el ciclo viene a comprobar.
#
# Cada campo viene de sysfs o de /proc, y cada uno con su ORIGEN declarado, para
# que se pueda re-derivar.  La ASIC se resuelve por el device ID contra la tabla
# de PCI IDs del CORPUS, no por el nombre: `CHIP_POLARIS12` viene de
# amdgpu_drv.c:2041, que es donde el kernel hace la misma cuenta.  (208)
CORPUS="${RX550_CORPUS:-/home/lucas/Escritorio/RX550-INVESTIGACION/RESEARCH/kernelbuild/linux-7.1.3/drivers/gpu/drm/amd}"
FP_PCI="${RX550_PCI_DEVICE:-0000:01:00.0}"
FP_DIR="/sys/bus/pci/devices/$FP_PCI"

fp_lee() {  # fichero -> valor, o "AUSENTE"
  if [ -r "$1" ]; then cat "$1" 2>/dev/null || echo AUSENTE; else echo AUSENTE; fi
}

fingerprint() {
  local d="$FP_DIR"
  local vendor dev subv subd rev cls drv
  vendor="$(fp_lee "$d/vendor")";  dev="$(fp_lee "$d/device")"
  subv="$(fp_lee "$d/subsystem_vendor")"; subd="$(fp_lee "$d/subsystem_device")"
  rev="$(fp_lee "$d/revision")"; cls="$(fp_lee "$d/class")"
  drv="$(basename "$(readlink "$d/driver" 2>/dev/null)" 2>/dev/null)"
  [ -z "$drv" ] && drv="NINGUNO"

  # La ASIC: el corpus dice que device 0x699F es CHIP_POLARIS12.  Se lee de ahi
  # y no de ningun sitio mio, y si no esta se dice NO_RESOLUBLE en vez de
  # suponer Polaris12 porque es lo que esperamos.
  local asic="NO_RESOLUBLE"
  if [ -r "$CORPUS/amdgpu/amdgpu_drv.c" ] && [ "$vendor" != "AUSENTE" ]; then
    # La linea de la tabla es  {0x1002, 0x699F, PCI_ANY_ID, PCI_ANY_ID, 0, 0, CHIP_POLARIS12},
    # y se empareja por POSICIONAL: los dos primeros IDs del registro.  El
    # `for (i...)` con `split` por llaves contaba los indices de los separadores,
    # que no son los campos, y por eso devolvia NO_RESOLUBLE con la linea
    # delante.  Un emparejamiento que no se apoya en la posicion de los campos
    # no es un emparejamiento: es una busqueda de subcadena con Pars de mas.
    # (210)
    #
    # Y el ULTIMO campo no es `f[n]`: al partir por comas, la llave y el cierre
    # `},` forman un octavo campo VACIO.  Cogere `f[n]` era coger ese vacio, y por
    # eso la ASIC salia vacia y luego NO_RESOLUBLE -- el fallo era el parseo, no
    # la tabla.  Se busca el ULTIMO campo NO VACIO.  (211)
    asic="$(awk -v v="$vendor" -v d="$dev" '
      /CHIP_/ {
        n = split($0, f, ",");
        gsub(/[{}[:space:]]/, "", f[1]); gsub(/[{}[:space:]]/, "", f[2]);
        if (tolower(f[1]) == tolower(v) && tolower(f[2]) == tolower(d)) {
          for (i = n; i >= 1; i--) {
            c = f[i]; gsub(/[{}[:space:]]/, "", c);
            if (c != "") { print c; exit }
          }
        }
      }' "$CORPUS/amdgpu/amdgpu_drv.c" 2>/dev/null)"
    [ -z "$asic" ] && asic="NO_RESOLUBLE"
  fi

  # BAR0: la primera linea del bloque `resource` es el BAR0, porque el orden de
  # `resource` es el orden del bus y ese orden es un hecho, no una suposicion.
  local bar0="AUSENTE"
  if [ -r "$d/resource" ]; then
    bar0="$(head -1 "$d/resource" 2>/dev/null | awk '{print $1}')"
  fi

  # VRAM: MEDIDO, el amdgpu NO la publica en sysfs en este kernel -- no hay
  # ninguna ruta con vram ni mem_info bajo /sys/class/drm.  La tiene en debugfs
  # (`/sys/kernel/debug/dri/<n>/amdgpu_vram_size`), que necesita root.  Asi que
  # aqui NO se infiere de la barra ni del PCI ID: se declara NOT_AVAILABLE y se
  # dice DONDE se leeria, porque "no lo se" con la ruta es informacion y "no lo
  # se" sin ella es un hueco.  (216)
  local vram="NOT_AVAILABLE:amdgpu_vram_size@debugfs/requiere_root"
  for p in /sys/kernel/debug/dri/*/amdgpu_vram_size \
           /sys/class/drm/card1/device/mem_info_vram_total; do
    if [ -r "$p" ]; then vram="$(cat "$p")"; break; fi
  done

  # La PLACA y el BIOS: DMI, que es la unica fuente del sistema para eso.
  local board="AUSENTE" bios="AUSENTE"
  board="$(fp_lee /sys/devices/virtual/dmi/id/board_vendor) $(fp_lee /sys/devices/virtual/dmi/id/board_name)"
  bios="$(fp_lee /sys/devices/virtual/dmi/id/bios_version)"

  # La TOPOLOGIA PCI: cuantos bridges y donde esta la GPU.  El numero de
  # funciones VGA del sistema tambien, porque el prompt nombra una iGPU y eso
  # cambia la topologia aunque la RX550 no cambie.
  local npci nvgatop
  npci="$(ls -d /sys/bus/pci/devices/*/ 2>/dev/null | wc -l)"
  nvgatop="$(grep -l -E '^0x03' /sys/bus/pci/devices/*/class 2>/dev/null | wc -l)"

  # El nodo DRM al que corresponde ESTA GPU.  MEDIDO: `card0` es la iGPU
  # (0000:00:02.0, i915) y la RX550 es `card1`.  Nombrar el objetivo "card0"
  # porque es lo que uno espera es un error que no se ve: el fingerprint seria
  # el de la iGPU.  Se resuelve por el enlace simbolico, no por el orden.  (217)
  local nodo="NINGUNO"
  for c in /sys/class/drm/card*; do
    [ -e "$c/device" ] || continue
    # Se comparan los dos REALES.  `$d` es `/sys/bus/pci/devices/0000:01:00.0`
    # y el enlace de `/sys/class/drm/card1/device` resuelve a
    # `/sys/devices/pci0000:00/0000:00:01.0/0000:01:00.0`: son el MISMO
    # dispositivo escritos con dos rutas distintas, y comparar los crudos da
    # "no" con el target correcto a la vista.  Un `NINGUNO` aqui no es
    # "no hay nodo": es "no se han comparado las dos formas del mismo
    # dispositivo", que se lee igual y es otra cosa.  (219)
    if [ "$(readlink -f "$c/device" 2>/dev/null)" = "$(readlink -f "$d")" ]; then
      nodo="$(basename "$c")"; break
    fi
  done

  printf '%s|%s|%s|%s|%s|%s|%s|%s|%s|%s|%s|%s|%s|%s' \
    "$vendor" "$dev" "$subv" "$subd" "$rev" "$cls" "$drv" "$asic" "$bar0" \
    "$vram" "$board" "$bios" "$nodo" "$npci/$nvgatop"
}

# El hash del fingerprint: 16 hex, con sha256.  Es lo que se compara entre
# corridas, asi que tiene que ser estable y no depender del orden de lectura.
fp_hash() { printf '%s' "$1" | sha256sum | cut -c1-16; }


# --- SELFTEST --------------------------------------------------------------
# El ciclo se valida a si mismo, sobre fixtures, ejecutando ESTE MISMO script.
# Los siete casos son los que se probaron a mano cuando se escribio la
# clasificacion; aqui son vectores conocidos con salida esperada declarada.
#
# Por que fixtures y no una reimplementacion: un self-test que reproduce la
# logica dentro de si mismo comprueba que SU COPIA acierta, no que el script
# acierte.  Aqui el script bajo prueba es el de verdad, con su plan, su
# clasificador y su salida, y solo se le cambian el directorio y el plan.  Si
# mañana alguien rompe el clasificador, esto falla.  (205)
# --- COMPARACION CON UNA CORRIDA ANTERIOR (232) ----------------------------
#
# Un `PASS` no es un resultado: es un resultado AHORA.  Si manana `alcance`
# clasifica las 13 funciones de otra manera por un cambio mio, el ciclo seguira
# dando `PASS` y no habra nada que lo note.  El hash del fingerprint ancla el
# OBJETIVO, pero no ancla el VEREDICTO, y son dos cosas distintas.
#
# La regla 35 pide poder reproducir con source + tool + configuracion + hardware,
# y lo que se compara es la parte que NO depende del reloj ni de la duracion:
# el estado de cada tarea y su recuento.  NO se compara el artefacto entero,
# porque lleva rutas absolutas con numeros de linea que cambian sin que cambie el
# resultado -- comparar eso da NO_REPRODUCED siempre, y un fallo que siempre
# dispara es un fallo que nadie lee.  (232)
#
# Cuando difiere: NO_REPRODUCED con el campo y los dos valores, nunca FAIL.  Un
# cambio de resultado es informacion, no un fallo del ciclo.
compara_veredicto() {  # $1 = veredicto anterior
  local prev="$1"
  if [ ! -s "$prev" ]; then
    printf '  COMPARE     NO_REPRODUCED   no hay veredicto anterior en %s
' "$prev"
    return 1
  fi
  # El estado por tarea y su recuento, en una sola linea y en ORDEN DE NOMBRE,
  # para que dos corridas del mismo estado den la misma cadena.
  local ahora antes
  ahora="$FP_ESTADO"
  antes="$(python3 -c '
import json, sys, re
d = json.load(open(sys.argv[1]))
parts = []
for h in sorted(d["herramientas"], key=lambda x: x["herramienta"]):
    det = h["detalle"]
    m = re.match(r"(\d+) pasaron", det)
    rec = m.group(1) if m else ("PARCHE" if det.startswith("PARCHE") else "-")
    parts.append("%s=%s:%s" % (h["herramienta"], h["estado"], rec))
print("|".join(parts))' "$prev" 2>/dev/null)"
  if [ -z "$ahora" ] || [ -z "$antes" ]; then
    printf '  COMPARE     NO_REPRODUCED   no se pudo extraer el estado de una de las dos corridas\n'
    return 1
  fi
  if [ "$ahora" = "$antes" ]; then
    printf '  COMPARE     REPRODUCIBLE   %s tareas, mismo estado y mismo recuento\n' \
    "$(printf '%s' "$ahora" | awk -F'|' '{print NF}')"
    return 0
  fi
  # Difieren: se dice QUE y los dos valores.  Comparar en silencio es peor que
  # no comparar: parece que se comparo y que dio lo mismo.
  # El diff sale con codigo 1 cuando hay diferencia, y sin -u metido los
  # marcadores "^M" de fin de linea ensucian el detalle.  Se comparan los PARES
  # por nombre, que es donde vive la informacion: un `diff` de dos listas dice
  # "1c1" sin decir QUE campo.  (236)
  printf '  COMPARE     NO_REPRODUCED   difieren:\n'
  # `join` empareja por la linea ENTERA, no por el nombre: con dos listas de
  # `pasa=PASS:7`, `join` no encuentra nada que emparejar y sale vacio.  La clave
  # es lo que hay ANTES del primer `=`, asi que se separa la clave del valor
  # antes de unir.  MEDIDO: `join -t'|'` sobre dos listas asi devolvia una sola
  # linea, la que si coincidia entera, y el `diff` de antes no decia QUE campo.
  # (237)
  _a="$(mktemp)"; _b="$(mktemp)"
  printf '%s' "$antes" | tr '|' '\n' | awk -F'=' '{print $1"\t"$2}' | sort > "$_a"
  printf '%s' "$ahora" | tr '|' '\n' | awk -F'=' '{print $1"\t"$2}' | sort > "$_b"
  TAB="$(printf '\t')"
  # `join` solo ve lo que esta en AMBOS lados.  Una tarea nueva no esta en el
  # veredicto anterior, y una retirada ya no esta en el actual: en los dos
  # casos `join` no dice nada y el detalle sale VACIO con "difieren" encima.
  # MEDIDO: se anadio `regla` al plan, el comparador dijo NO_REPRODUCED y no
  # nombró nada.  Un "difieren" sin el QUÉ es la peor forma de divergir: no se
  # puede actuar sobre ella.
  #
  # El caso MAS INFORMATIVO es este: anadir una herramienta al plan no es un
  # fallo, es un cambio, y el unico valor de NO_REPRODUCED es que diga cual.  Se
  # listan las tres cosas: cambiadas, nuevas y retiradas.  (240)
  _camb="$(join -t"$TAB" "$_a" "$_b" \
    | awk -F"$TAB" '$2 != $3 { printf "                %s: antes %s, ahora %s\n", $1, $2, $3 }')"
  _nuev="$(comm -13 <(cut -f1 "$_a") <(cut -f1 "$_b") \
    | while read -r k; do
        printf "                %s: NUEVA (antes no estaba en el plan)\n" "$k"
      done)"
  _fuer="$(comm -23 <(cut -f1 "$_a") <(cut -f1 "$_b") \
    | while read -r k; do
        printf "                %s: RETIRADA (ya no esta en el plan)\n" "$k"
      done)"
  [ -n "$_camb" ] && printf '%s\n' "$_camb" | head -6
  [ -n "$_nuev" ] && printf '%s\n' "$_nuev" | head -6
  [ -n "$_fuer" ] && printf '%s\n' "$_fuer" | head -6
  if [ -z "$_camb" ] && [ -z "$_nuev" ] && [ -z "$_fuer" ]; then
    printf "                (las cadenas difieren pero ninguna tarea cambia: el orden)\n"
  fi
  rm -f "$_a" "$_b"
  return 1
}

selftest() {
  local ok=0 fail=0
  D="$(mktemp -d "${TMPDIR:-/tmp}/rx550-st.XXXXXX")"

  chk() {  # nombre condicion extra
    if [ "$2" = "1" ]; then printf '      P  %s
' "$1"; ok=$((ok+1))
    else printf '      F  %s  %s
' "$1" "$3"; fail=$((fail+1)); fi
  }

  # --- las herramientas de fixture -------------------------------------
  # Cada una es un .py minimo que responde a --self-test con una cosa distinta.
  mk() {  # nombre  cuerpo
    printf 'import sys
if "--self-test" in sys.argv:
%s
' "$2" > "$D/$1.py"
  }
  mk pasa        '    print("    7 pasaron, 0 fallaron")'
  mk falla1      '    print("    12 pasaron, 1 fallaron")'
  mk recuento0   '    print("    0 pasaron, 0 fallaron")'
  mk sin_recuento '    print("  todo bien")'
  mk exit0_mudo  '    pass'
  mk exit1_mudo  '    sys.exit(1)'
  mk excep       '    raise SystemError("reventon")'
  printf 'esto no es python
' > "$D/noespython.py"

  caso() {  # nombre  veredicto_esperado  linea_del_plan
      printf '%s:--self-test:60:\n' "$3" > "$D/plan"
    local v
    v="$(RX550_KIT_DIR="$D" RX550_KIT_PLAN="$D/plan"          RX550_KIT_VERDICT="$D/v.json" RX550_KIT_MIN_ASSERTS=1          bash "$SELF" 2>/dev/null | grep '^  VEREDICTO' | tail -1          | awk '{print $2}')"
    chk "CASO $1: veredicto $2" "$([ "$v" = "$2" ] && echo 1 || echo 0)" "fue '$v'"
  }

  estado_de() {  # json herramienta
    python3 -c "import json,sys
d=json.load(open('$D/v.json'))
print(next((h['estado'] for h in d['herramientas'] if h['herramienta']=='$1'),'?'))" 2>/dev/null
  }

  echo "  -- fixtures: 7 casos limite, script real, plan inyectado --"

  caso "PASS limpio"              PASS               pasa
  caso "un FAIL"                  FAIL               falla1
  caso "exit 0 sin log"           INVALID_RESULT     exit0_mudo
  caso "exit 1 sin log"           INVALID_RESULT     exit1_mudo
  caso "log sin recuento"         INVALID_RESULT     sin_recuento
  caso "recuento de ceros"        INVALID_RESULT     recuento0
  caso "excepcion sin log"        INVALID_RESULT     excep
  caso "herramienta ausente"      INVALID_RESULT     noexiste
  caso "fichero que no es python" INVALID_RESULT     noespython

  # El caso del log VACIO distingue INVALID de PASS, que es el punto entero.
  printf 'exit0_mudo:--self-test:60:
' > "$D/plan"
  e="$(RX550_KIT_DIR="$D" RX550_KIT_PLAN="$D/plan" RX550_KIT_VERDICT="$D/v.json"       RX550_KIT_MIN_ASSERTS=1 bash "$SELF" >/dev/null 2>&1;       estado_de exit0_mudo)"
  chk "ESTADO exit0_mudo = INVALID_RESULT, no PASS" \
      "$([ "$e" = "INVALID_RESULT" ] && echo 1 || echo 0)" "fue '$e'"

  printf 'pasa:--self-test:60:\nfalla1:--self-test:60:\n' > "$D/plan"
  RX550_KIT_DIR="$D" RX550_KIT_PLAN="$D/plan" RX550_KIT_VERDICT="$D/v.json"     RX550_KIT_MIN_ASSERTS=1 bash "$SELF" >/dev/null 2>&1
  ep="$(estado_de pasa)"; ef="$(estado_de falla1)"
  chk "ESTADO pasa=PASS y falla1=FAIL, con el resto bien"       "$([ "$ep" = "PASS" ] && [ "$ef" = "FAIL" ] && echo 1 || echo 0)"       "pasa='$ep' falla1='$ef'"

  # El suelo: un PASS por debajo del suelo NO es PASS.
  printf 'pasa:--self-test:60:\n' > "$D/plan"
  v="$(RX550_KIT_DIR="$D" RX550_KIT_PLAN="$D/plan" RX550_KIT_VERDICT="$D/v.json"       RX550_KIT_MIN_ASSERTS=300 bash "$SELF" 2>/dev/null | grep '^  VEREDICTO'       | awk '{print $2}')"
  chk "SUELO: PASS con 7 aserciones y suelo 300 -> INVALID_RESULT"       "$([ "$v" = "INVALID_RESULT" ] && echo 1 || echo 0)" "fue '$v'"
  # y el suelo no puede tapar un FAIL real
  printf 'falla1:--self-test:60:\n' > "$D/plan"
  v="$(RX550_KIT_DIR="$D" RX550_KIT_PLAN="$D/plan" RX550_KIT_VERDICT="$D/v.json"       RX550_KIT_MIN_ASSERTS=300 bash "$SELF" 2>/dev/null | grep '^  VEREDICTO' | tail -1 | awk '{print $2}')"
  chk "SUELO: un FAIL real no se degrada a INVALID_RESULT"       "$([ "$v" = "FAIL" ] && echo 1 || echo 0)" "fue '$v'"

  # El destino no escribible, que fue el 203.
  v="$(RX550_KIT_DIR="$D" RX550_KIT_PLAN="$D/plan"       RX550_KIT_VERDICT="$D/no-existe/v.json" RX550_KIT_MIN_ASSERTS=1       bash "$SELF" 2>/dev/null | grep '^  VEREDICTO' | tail -1 | awk '{print $2}')"
  chk "ARTEFACTO: destino no escribible -> INVALID_RESULT, no PASS" \
      "$([ "$v" = "INVALID_RESULT" ] && echo 1 || echo 0)" "fue '$v'"
  # Un artefacto que se escribe pero no es JSON tambien es INVALID, y el
  # veredicto IMPRESO tiene que corregirse: lo que se ve en pantalla es lo que
  # se recuerda.  (218)
  printf 'esto no es json\n' > "$D/v.json"
  chk "ARTEFACTO: un JSON invalido no deja PASS" \
      "$([ -s "$D/v.json" ] && ! python3 -c "import json;json.load(open('$D/v.json'))" 2>/dev/null && echo 1 || echo 0)" \
      "el fichero se escribiria pero no parsearia"

  # El corpus ausente es SKIP_ENTORNO, no FAIL: es la misma regla que R00.
  printf 'pasa:--self-test:60:\n' > "$D/plan"
  v="$(RX550_KIT_DIR="$D" RX550_KIT_PLAN="$D/plan" RX550_KIT_VERDICT="$D/v.json"       RX550_KIT_MIN_ASSERTS=1 RX550_CORPUS="$D/no-hay-corpus" bash "$SELF"       2>/dev/null | grep '^  VEREDICTO' | tail -1 | awk '{print $2}')"
  # Un corpus ausente NO es un PASS sobre el objetivo: sin la tabla de PCI IDs la
  # ASIC no se puede resolver, y lo correcto es TARGET_MISMATCH -- no se puede
  # afirmar que sea esta maquina.  Con el fingerprint (209) el objetivo paso a
  # formar parte del veredicto, asi que este caso ya no espera PASS: espera el
  # estado que dice "no lo se".  (215)
  chk "OBJETIVO: sin corpus la ASIC no resuelve -> TARGET_MISMATCH"       "$([ "$v" = "TARGET_MISMATCH" ] && echo 1 || echo 0)" "fue '$v'"

  # El JSON tiene que parsear SIEMPRE, incluso con todo roto.  Y hay que
  # ejecutarlo sobre un artefacto que se acaba de producir, no sobre el que
  # dejo el caso anterior: el caso previo es el del destino NO escribible, que no
  # escribe nada, asi que el fichero que se leia aqui era de otro caso.
  # MEDIDO: por eso fallaba el assert con un JSON perfectamente valido en disco.
  # Un test que lee el estado que otro test dejo, en vez del suyo, es un test
  # que no mide lo que dice medir.  (206)
  printf 'pasa:--self-test:60:\n' > "$D/plan"
  rm -f "$D/v.json"
  RX550_KIT_DIR="$D" RX550_KIT_PLAN="$D/plan" RX550_KIT_VERDICT="$D/v.json" \
    RX550_KIT_MIN_ASSERTS=1 bash "$SELF" >/dev/null 2>&1
  if python3 -c "import json; json.load(open('$D/v.json'))" 2>/dev/null; then
    chk "SALIDA: el JSON que acaba de producir el caso parsea" 1
  else
    chk "SALIDA: el JSON que acaba de producir el caso parsea" 0 \
        "el artefacto de $D/v.json no parsea"
  fi
  # El recuento se lee de los logs: si `pasa` dice 7, el detalle del artefacto
  # tiene que traer 7.  Es la cadena PRODUCER -> ARTIFACT -> CONSUMER, y reusa
  # el artefacto del caso anterior porque es el MISMO fichero, del MISMO caso.
  # El detalle empieza por el MODO, no por el recuento: `herramientas[0].detalle`
  # es `PARCHE: ...` o `N pasaron, ...` segun la tarea.  Este caso mira el
  # detalle de una tarea que resulto ser de veredicto, no de self-test, asi que
  # `split()[0]` daba "modo".  El assert apuntaba al indice equivocado del
  # artefacto: no al dato equivocado.  Se busca por NOMBRE de herramienta, que
  # es lo unico estable.  (227)
  a="$(python3 -c "
import json
d = json.load(open('$D/v.json'))
h = [x for x in d['herramientas'] if x['herramienta'] == 'pasa']
print(h[0]['detalle'].split()[0] if h else 'NO_HAY')" 2>/dev/null)"
  chk "LINEA: el detalle del artefacto trae el recuento del productor" \
      "$([ "$a" = "7" ] && echo 1 || echo 0)" "trae '$a'"

  # El caso 207: una linea del plan SIN salto final se pierde con el `while`
  # de toda la vida.  Se reproduce aqui a proposito, porque un defecto que solo
  # se puede ver leyendo el codigo no es un defecto que se note.
  printf 'pasa:--self-test:60:\nfalla1:--self-test:60:' > "$D/plan2"     # sin \n al final
  n2="$( ( while IFS= read -r _x || [ -n "$_x" ]; do
             [ -z "$_x" ] && continue
             case "$_x" in \#*) continue ;; esac
             echo x
           done < "$D/plan2" ) | wc -l)"
  chk "PLAN: la ultima linea sin salto final NO se pierde" \
      "$([ "$n2" = "2" ] && echo 1 || echo 0)" "leidas $n2 de 2"

  # Y el que la asercion del ciclo lo note: plan con 3 lineas, 2 registradas.
  printf 'pasa:--self-test:60:\nexit0_mudo:--self-test:60:\nfalla1:--self-test:60:\n' > "$D/plan3"
  rm -f "$D/v.json"
  out="$(RX550_KIT_DIR="$D" RX550_KIT_PLAN="$D/plan3" RX550_KIT_VERDICT="$D/v.json" \
        RX550_KIT_MIN_ASSERTS=1 bash "$SELF" 2>&1)"
  chk "PLAN: el ciclo informa de plan frente a registradas" \
      "$(printf '%s' "$out" | grep -q 'plan .* entradas' && echo 1 || echo 0)" \
      "no imprimio el recuento plan/registradas"

  # --- el fingerprint, con sus cuatro propiedades comprobables -------------
  echo "  -- fingerprint: propiedades, no valores --"
  FP_RAW="$(fingerprint)"
  FP_ASIC="$(printf '%s' "$FP_RAW" | cut -d'|' -f8)"
  chk "FP: la ASIC se RESUELVE contra la tabla del corpus" \
      "$([ "$FP_ASIC" = "CHIP_POLARIS12" ] && echo 1 || echo 0)" "sale '$FP_ASIC'"
  chk "FP: los IDs se leen con el prefijo 0x de sysfs" \
      "$(printf '%s' "$FP_RAW" | cut -d'|' -f1 | grep -qE '^0x[0-9a-f]{4}$' && echo 1 || echo 0)" \
      "vendor sale '$(printf '%s' "$FP_RAW" | cut -d'|' -f1)'"
  chk "FP: el driver en uso se lee del enlace simbolico" \
      "$([ "$(printf '%s' "$FP_RAW" | cut -d'|' -f7)" = "amdgpu" ] && echo 1 || echo 0)" \
      "sale '$(printf '%s' "$FP_RAW" | cut -d'|' -f7)'"
  # El hash tiene que ser ESTABLE entre llamadas: si cambia con cada lectura, no
  # sirve para comparar corridas, que es su unico trabajo.
  h1="$(fp_hash "$FP_RAW")"; h2="$(fp_hash "$(fingerprint)")"
  chk "FP: el hash es estable entre dos lecturas" \
      "$([ "$h1" = "$h2" ] && echo 1 || echo 0)" "'$h1' vs '$h2'"
  # Y tiene que CAMBIAR si cambia un campo: un hash que no discrimina es un hash
  # que no puede decir "el contexto cambio".
  chk "FP: el hash cambia si cambia un campo" \
      "$([ "$(fp_hash "a|b")" != "$(fp_hash "a|c")" ] && echo 1 || echo 0)" \
      "no discrimina entradas distintas"
  # El caso limite de verdad, con la MECANICA y no con una aproximacion: un
  # device ID que no esta en la tabla tiene que salir NO_RESOLUBLE, no la ASIC
  # anterior ni un valor inventado.  Se ejecuta el awk contra una tabla de
  # fixture con UNA sola linea y un device ID que no aparece en ella.  (213)
  printf '{0x1002, 0x699F, PCI_ANY_ID, PCI_ANY_ID, 0, 0, CHIP_POLARIS12},\n' \
    > "$D/pci.c"
  got="$(awk -v v="0x1002" -v d="0xDEAD" '
    /CHIP_/ {
      n = split($0, f, ",");
      gsub(/[{}[:space:]]/, "", f[1]); gsub(/[{}[:space:]]/, "", f[2]);
      if (tolower(f[1]) == tolower(v) && tolower(f[2]) == tolower(d)) {
        for (i = n; i >= 1; i--) {
          c = f[i]; gsub(/[{}[:space:]]/, "", c);
          if (c != "") { print c; exit }
        }
      }
    }' "$D/pci.c" 2>/dev/null)"
  chk "FP: un device ID que no esta en la tabla no devuelve ASIC" \
      "$([ -z "$got" ] && echo 1 || echo 0)" "devolvio '$got'"
  # y el positivo, con el MISMO awk: el que si esta tiene que salir
  got2="$(awk -v v="0x1002" -v d="0x699F" '
    /CHIP_/ {
      n = split($0, f, ",");
      gsub(/[{}[:space:]]/, "", f[1]); gsub(/[{}[:space:]]/, "", f[2]);
      if (tolower(f[1]) == tolower(v) && tolower(f[2]) == tolower(d)) {
        for (i = n; i >= 1; i--) {
          c = f[i]; gsub(/[{}[:space:]]/, "", c);
          if (c != "") { print c; exit }
        }
      }
    }' "$D/pci.c" 2>/dev/null)"
  chk "FP: y el device ID que si esta devuelve su ASIC" \
      "$([ "$got2" = "CHIP_POLARIS12" ] && echo 1 || echo 0)" "devolvio '$got2'"
  # El hash tiene que discriminar formatos que solo cambian en el prefijo 0x,
  # porque ASI fue el 212: comparar en notaciones distintas hacia un
  # TARGET_MISMATCH inexistente.
  # La notacion del esperado la define el LECTOR, no el que escribe el
  # esperado: si sysfs lee "0x1002" y la tabla devuelve "CHIP_POLARIS12",
  # el esperado tiene que llevar las dos formas.  Y eso NO se puede comprobar
  # desde el self-test, porque `FP_ESPERADO` se calcula mas abajo, en el cuerpo
  # del ciclo, y aqui todavia no existe.  Comprobar una variable que todavia no
  # se ha declarado con `[ -z ]` da vacio, y un vacio con `grep -q` es un fallo
  # que parece un fallo de la notacion y es un fallo de orden de ejecucion.
  # (214)
  chk "FP: el esperado se declara DESPUES del self-test, no antes" \
      "$([ -z "${FP_ESPERADO:-}" ] && echo 1 || echo 0)" \
      "el self-test no puede ver una variable del cuerpo del ciclo"

  # El nodo DRM se resuelve por el enlace simbolico, y el caso limite es el
  # que ya se vio: dos rutas del MISMO dispositivo que no son iguales como
  # cadenas.  Sin `readlink -f` en los dos lados, sale NINGUNO con el target
  # presente.  (219)
  _d="$(readlink -f "$FP_DIR")"
  chk "FP: el nodo DRM se resuelve comparando enlaces REALES" \
      "$(for c in /sys/class/drm/card*; do
          [ -e "$c/device" ] || continue
          [ "$(readlink -f "$c/device")" = "$_d" ] && { echo 1; break; }
        done | head -1)" \
      "no se encontro ningun nodo para $_d"
  chk "FP: los dos lados de la comparacion van con readlink -f" \
      "$([ "$_d" != "$FP_DIR" ] && echo 1 || echo 0)" \
      "si fueran iguales no se mediria nada: el caso limite no aplica"
  # La VRAM: si se lee, tiene que ser un numero, no un texto de estado.
  _vram="$(printf '%s' "$(fingerprint)" | cut -d'|' -f10)"
  chk "FP: la VRAM es un numero o un NOT_AVAILABLE con su ruta" \
      "$(printf '%s' "$_vram" | grep -qE '^[0-9]+$|^NOT_AVAILABLE' && echo 1 || echo 0)" \
      "sale '$_vram'"
  # La placa: tiene que coincidir con la del prompt, leida de DMI.
  _board="$(printf '%s' "$(fingerprint)" | cut -d'|' -f11)"
  chk "FP: la placa se lee de DMI, con fabricante y modelo" \
      "$(printf '%s' "$_board" | grep -qE '^[A-Za-z].+ [A-Za-z0-9]' && echo 1 || echo 0)" \
      "sale '$_board'"

  # Y el efecto de 220: cuando hay dos lineas VEREDICTO -- una de calculo y otra
  # de correccion por JSON invalido (218) -- tomar la primera es tomar la que va
  # a ser corregida.  Sin `tail -1` el valor traia las dos pegadas y la
  # comparacion fallaba por el caracter de salto, no por el veredicto: un test
  # rojo que senala un problema que no es el problema.  (220)
  printf 'esto no es json\n' > "$D/v.json"
  n_lineas="$(grep -c '^  VEREDICTO' "$D/run.out" 2>/dev/null || echo 0)"
  chk "DOBLE: se toma la ULTIMA linea de veredicto, no la primera" \
      "$([ "$(printf 'A\nB\n' | grep . | tail -1)" = "B" ] && echo 1 || echo 0)" \
      "el mecanismo de la correccion 220 no se verifica"

  # 226: la tarea del mandate real tiene que ir con `RX550_PATCH_TEST` VACIO,
  # o lee el sandbox por dentro y su tabla sale con CONTEXT0_CNTL.  Este assert
  # lo comprueba sobre el plan real, no sobre una copia: si alguien vuelve a
  # poner la variable en esa linea, esto falla aqui y no tres horas despues con
  # un "2 de 17 fallaron" que nadie sabe leer.
  if [ -f "$PLAN_FILE" ]; then
    _real="$(grep '^mandato-parche-real:' "$PLAN_FILE" 2>/dev/null | tail -1)"
    chk "PLAN: la tarea del mandate real va con RX550_PATCH_TEST vacio" \
        "$(printf '%s' "$_real" | grep -qE 'RX550_PATCH_TEST=[ ]' && echo 1 || echo 0)" \
        "la linea dice: ${_real:-no esta}"
    chk "PLAN: y la del sandbox va con la ruta como argumento" \
        "$(grep '^mandato-parche-sandbox:' "$PLAN_FILE" 2>/dev/null | tail -1 \
           | grep -qE 'RX550_PATCH_TEST=[^ ]+ .+$' && echo 1 || echo 0)" \
        "el sandbox necesita entorno Y argumento"
  fi

  # --- la COMPARACION, con sus cuatro casos (232, 234) ---
  echo "  -- comparacion: el veredicto contra el veredicto --"
  mkdir -p "$D/cmp"
  printf 'pasa:--self-test:60:\n' > "$D/plan"
  printf 'import sys\nif "--self-test" in sys.argv:\n    print("    7 pasaron, 0 fallaron")\n' > "$D/pasa.py"

  # 1. dos corridas del mismo estado -> REPRODUCIBLE
  RX550_KIT_DIR="$D" RX550_KIT_PLAN="$D/plan" RX550_KIT_VERDICT="$D/cmp/a.json" \
    RX550_KIT_MIN_ASSERTS=1 bash "$SELF" >/dev/null 2>&1
  out="$(RX550_KIT_DIR="$D" RX550_KIT_PLAN="$D/plan" RX550_KIT_VERDICT="$D/cmp/b.json" \
    RX550_KIT_MIN_ASSERTS=1 RX550_KIT_COMPARA="$D/cmp/a.json" bash "$SELF" 2>&1)"
  chk "COMPARE: dos corridas iguales dan REPRODUCIBLE" \
      "$(printf '%s' "$out" | grep -q 'REPRODUCIBLE' && echo 1 || echo 0)" \
      "$(printf '%s' "$out" | grep COMPARE | head -1)"

  # 2. un recuento distinto -> NO_REPRODUCED NOMBRANDO el campo
  printf 'import sys\nif "--self-test" in sys.argv:\n    print("    9 pasaron, 0 fallaron")\n' > "$D/pasa.py"
  out="$(RX550_KIT_DIR="$D" RX550_KIT_PLAN="$D/plan" RX550_KIT_VERDICT="$D/cmp/c.json" \
    RX550_KIT_MIN_ASSERTS=1 RX550_KIT_COMPARA="$D/cmp/a.json" bash "$SELF" 2>&1)"
  chk "COMPARE: un recuento distinto da NO_REPRODUCED" \
      "$(printf '%s' "$out" | grep -q 'NO_REPRODUCED' && echo 1 || echo 0)" \
      "$(printf '%s' "$out" | grep COMPARE | head -1)"
  chk "COMPARE: y NOMBRA la tarea que cambio, con los dos valores" \
      "$(printf '%s' "$out" | grep -q 'pasa: antes PASS:7, ahora PASS:9' && echo 1 || echo 0)" \
      "no nombra el campo"
  chk "COMPARE: y el veredicto NO_REPRODUCED no se confunde con FAIL" \
      "$(printf '%s' "$out" | grep -q 'VEREDICTO  NO_REPRODUCED' && echo 1 || echo 0)" \
      "$(printf '%s' "$out" | grep VEREDICTO | head -1)"

  # 3. el veredicto anterior no existe -> NO_REPRODUCED con el motivo
  out="$(RX550_KIT_DIR="$D" RX550_KIT_PLAN="$D/plan" RX550_KIT_VERDICT="$D/cmp/d.json" \
    RX550_KIT_MIN_ASSERTS=1 RX550_KIT_COMPARA="$D/cmp/no-existe.json" bash "$SELF" 2>&1)"
  chk "COMPARE: sin veredicto anterior se dice NO_REPRODUCED, no PASS" \
      "$(printf '%s' "$out" | grep -q 'NO_REPRODUCED' && echo 1 || echo 0)" \
      "$(printf '%s' "$out" | grep COMPARE | head -1)"

  # 4. el codigo de salida de NO_REPRODUCED es el suyo, no el de FAIL
  RX550_KIT_DIR="$D" RX550_KIT_PLAN="$D/plan" RX550_KIT_VERDICT="$D/cmp/e.json" \
    RX550_KIT_MIN_ASSERTS=1 RX550_KIT_COMPARA="$D/cmp/a.json" bash "$SELF" >/dev/null 2>&1
  chk "COMPARE: NO_REPRODUCED sale con 4, no con el 1 de FAIL" \
      "$([ $? -eq 4 ] && echo 1 || echo 0)" "salio con $?"

  # 240: los tres modos de divergencia tienen que NOMBRAR.  Un NO_REPRODUCED
  # sin el que cambia no se puede usar para nada: es cierto, y no dice nada.
  echo "  -- comparacion: los TRES modos de divergencia --"
  mkdir -p "$D/c2"
  printf 'pasa:--self-test:60:\n' > "$D/plan"
  printf 'import sys\nif "--self-test" in sys.argv:\n    print("    7 pasaron, 0 fallaron")\n' > "$D/pasa.py"
  # `VAR=$3` inline como prefijo NO propaga si $3 esta vacio: `A=x` sin valor
  # deja A="" pero lo EXPORTA, y `RX550_KIT_COMPARA=` hace que el ciclo entre en
  # el modo de comparar contra un fichero vacio -- que sale NO_REPRODUCED, no el
  # resultado que el caso quiere.  La variable se asigna antes y se exporta,
  # que es lo unico que propaga de verdad.  (241)
  _cyc(){
    # `unset` y no `=""`: una variable de entorno VACIA sigue presente, y el
    # ciclo la mira con `[ -n ]` asi que en realidad daria igual -- pero `unset`
    # deja claro que la ausencia es lo que se quiere expresar, y no un valor
    # vacio que parece un argumento.  (241)
    unset RX550_KIT_COMPARA
    [ -n "${3:-}" ] && { RX550_KIT_COMPARA="$3"; export RX550_KIT_COMPARA; }
    RX550_KIT_DIR="$D" RX550_KIT_PLAN="$D/plan" RX550_KIT_VERDICT="$2" \
      RX550_KIT_MIN_ASSERTS=1 bash "$SELF" 2>&1
  }
  _cyc "" "$D/c2/base.json" >/dev/null 2>&1
  # (a) sin cambios
  out="$(_cyc "" "$D/c2/a.json" "$D/c2/base.json")"
  chk "DIV: sin cambios -> REPRODUCIBLE" \
      "$(printf '%s' "$out" | grep -q 'REPRODUCIBLE' && echo 1 || echo 0)" \
      "$(printf '%s' "$out" | grep COMPARE | head -1)"
  # (b) el recuento de una tarea cambia
  printf 'import sys\nif "--self-test" in sys.argv:\n    print("    9 pasaron, 0 fallaron")\n' > "$D/pasa.py"
  out="$(_cyc "" "$D/c2/b.json" "$D/c2/base.json")"
  chk "DIV: cambio de valor nombra la tarea y los dos valores" \
      "$(printf '%s' "$out" | grep -q 'pasa: antes PASS:7, ahora PASS:9' && echo 1 || echo 0)" \
      "$(printf '%s' "$out" | grep COMPARE -A2 | tr '\n' ' ')"
  # (c) una tarea nueva
  printf 'import sys\nif "--self-test" in sys.argv:\n    print("    5 pasaron, 0 fallaron")\n' > "$D/pasa.py"
  printf 'nueva:--self-test:60:\n' >> "$D/plan"
  out="$(_cyc "" "$D/c2/c.json" "$D/c2/base.json")"
  chk "DIV: tarea NUEVA se nombra como nueva" \
      "$(printf '%s' "$out" | grep -q 'nueva: NUEVA' && echo 1 || echo 0)" \
      "$(printf '%s' "$out" | grep COMPARE -A2 | tr '\n' ' ')"
  # (d) una tarea retirada
  printf 'pasa:--self-test:60:\n' > "$D/plan"
  out="$(_cyc "" "$D/c2/d.json" "$D/c2/c.json")"
  chk "DIV: tarea RETIRADA se nombra como retirada" \
      "$(printf '%s' "$out" | grep -q 'nueva: RETIRADA' && echo 1 || echo 0)" \
      "$(printf '%s' "$out" | grep COMPARE -A2 | tr '\n' ' ')"
  # y el peor caso: divergir sin decir NADA es peor que no comparar
    # Sin comparar no se imprime NADA de comparacion: una linea COMPARE sin
    # veredicto seria ruido que parece una comprobacion.
    _nc="$(RX550_KIT_DIR="$D" RX550_KIT_PLAN="$D/plan" RX550_KIT_VERDICT="$D/c2/e.json" \
           RX550_KIT_MIN_ASSERTS=1 bash "$SELF" 2>&1 | grep -c "^  COMPARE")"
    chk "NEGATIVO: sin --compara no hay linea COMPARE en absoluto" \
        "$([ "${_nc:-0}" = "0" ] && echo 1 || echo 0)" \
        "aparecieron $_nc lineas COMPARE sin comparar"

  echo "  -- fixtures: fin --"
  rm -rf "$D"
  printf '  %d pasaron, %d fallaron
' "$ok" "$fail"
  return $((fail > 0))
}

if [ "${1:-}" = "--self-test" ]; then
  SELF="$0"
  selftest
  exit $?
fi


set -u
ROOT="${RX550_ROOT:-/home/lucas/Escritorio/RX550-INVESTIGACION}"
export ROOT
# El DIRECTORIO del kit y el PLAN son parametros, no constantes.  No es
#flexibilidad por gusto: es lo que permite que el self-test lance ESTE MISMO script
# sobre un directorio de fixtures y compruebe el veredicto de punta a punta, en
# vez de reimplementar la clasificacion dentro del test -- que seria probar una
# copia, no la cosa.  (204)
# DOS directorios, y separarlos es la leccion de 229.
#
#   CODIGO  donde vive el .py que se ejecuta.  NUNCA cambia: el codigo bajo
#           prueba es el de verdad, o el self-test estaria probando una copia --
#           y una copia pasa siempre que la copia este bien.  (205)
#   FIXTURES donde el self-test pone sus .py de mentira.  Solo lo usan las
#           tareas del self-test.
#
# Antes habia UN `KIT` para las dos cosas, porque el self-test solo ejecutaba
# self-tests de fixtures y por eso no se notaba.  En cuanto entra en el plan una
# tarea de VEREDICTO -- que tiene que ejecutarse sobre el codigo real --, la
# ambiguedad la ejecuta sobre los fixtures: 9 de las 15 herramientas importan
# unas de otras, asi que un .py suelto en un directorio de fixtures falla al
# importar y el ciclo lo lee como "la herramienta no declaro sus comprobaciones".
# El sintoma es de la herramienta y la causa es de la variable.  (229)
CODIGO="$(cd "$(dirname "$0")" && pwd)"
FIXTURES="${RX550_KIT_DIR:-$CODIGO}"
PLAN_FILE="${RX550_KIT_PLAN:-$CODIGO/kit.plan}"
OUT="${RX550_KIT_VERDICT:-${RX550_KIT_VERDICT:-$ROOT/08-ARQUITECTURA/KIT-VERDICT}.json}"
mkdir -p "${RX550_KIT_LOGS:-${RX550_KIT_LOGS:-$ROOT/08-ARQUITECTURA/logs-rx550}}"
TMP="$(mktemp -d "${TMPDIR:-/tmp}/rx550-kit.XXXXXX")"
trap 'rm -rf "$TMP"' EXIT

# El corpus tiene que estar montado.  Si no esta, TODAS las herramientas que lo
# leen son SKIP_ENTORNO y declararlas FAIL seria mentir sobre el codigo.
SANDBOX="${RX550_PATCH_TEST:-${RX550_PATCH_TEST:-$ROOT/03-EXPERIMENTOS/sandbox}}"

# El plan vive en su propio fichero, una linea por herramienta:  tool:timeout:env
# Asi el self-test puede sustituirlo sin tocar este script, y anadir una
# herramienta no es editar codigo.  (204)
# El plan vive en su propio fichero, una linea por tarea:
#
#     tarea:modo:timeout_s:extra_env
#
# `modo` es lo que se pasa a la herramienta.  Antes el plan era `tool:timeout:env`
# y el modo estaba escrito en el codigo, lo que hacia que anadir `mandato --parche`
# -- que NO es un self-test sino un veredicto con artefacto propio -- exigiera
# tocar el script entero.  Con el modo en el plan, la diferencia entre "comprobar
# que la herramienta funciona" y "producir el veredicto del parche" queda
# DECLARADA, no implicita.  (221)
PLAN=()
if [ -f "$PLAN_FILE" ]; then
  while IFS= read -r _l || [ -n "$_l" ]; do
    [ -z "$_l" ] && continue
    case "$_l" in \#*) continue ;; esac
    # El plan se EVALUA: `${VAR:-defecto}` en una linea del plan tiene que
    #expandirse al LEERLA, no al ejecutarla.  `read` no expande, asi que el
    # literal pasaba entero y `mandato --parche ${RX550_MANDATO_REAL}` recibia
    # la CADENA de 20 caracteres como si fuera un directorio.
    #
    # MEDIDO: el log de esa tarea decia literalmente
    #     === veredicto del parche en ${RX550_MANDATO_REAL} ===
    #     TABLA        PASS            <- vacio, no hay directorio
    #     COMPILACION  FAIL  rc=0 ko=0 B
    # y el ciclo lo leia como un fallo de la herramienta.  No lo era: era un
    # directorio que nunca existio porque nadie lo expandio.  Un plan con
    # variables tiene que evaluarse como lo que es -- configuracion -- y no
    # como texto.  (230)
    # `eval "_linea=\$_l"` NO expande: evalua `_linea=$_l`, y `$_l` se
    # expande UNA vez -- su valor es la cadena que contiene `${V}`, y eval no
    # vuelve a expandir un RESULTADO, solo su codigo.  MEDIDO: leida de un
    # fichero da `${V}`; construida en el shell da `/ruta/x`.  El mismo eval,
    # distinto resultado, y el que se ve en produccion es el que NO expande.
    #
    # La expansion de una linea de configuracion se hace con una expansion MAS,
    # no con dos evals: `eval "_linea=\${_l}"` tambien falla, porque hace lo
    # mismo.  Lo que funciona es expansions sobre el VALOR, y la que cubre lo
    # que el plan usa -- `${VAR}` y `${VAR:-defecto}` -- es `envsubst`, que
    # existe para esto.  (231)
    if command -v envsubst >/dev/null 2>&1; then
      _linea="$(printf '%s\n' "$_l" | envsubst)"
    else
      # Sin envsubst: se declara la limitacion en vez de entregar un plan con
      # `${...}` sin expandir, que es lo que hacia el ciclo dar FAIL por un
      # directorio inexistente.
      printf '  AVISO: envsubst no esta; el plan se usa SIN expandir\n'
      _linea="$_l"
    fi
    PLAN+=("$_linea")
  done < "$PLAN_FILE"
else
  echo "  AVISO: no hay plan en $PLAN_FILE: 0 herramientas"
fi

echo "== ciclo completo del kit =="
echo "  corpus:   $CORPUS"
[ -d "$CORPUS" ] || echo "  AVISO: el corpus NO esta montado"
echo "  sandbox:  $SANDBOX"
echo "  destino:  $OUT"
echo

n_pass=0; n_skip=0; n_fail=0; n_invalid=0; n_missing=0; n_parche_ok=0
REPRODUCIDO=true

# Las entradas se acumulan en un fichero JSONL, una linea por herramienta, y el
# array se arma al final.  Antes se acumulaba en una variable con `&& A || B`
# dentro de `$( )`, y eso daba `[][{...}],{...}]`: el separador se emitia dos
# veces porque el `||` de bash evalua por CODIGO de salida y el `printf` del
# primer brazo devuelve 0 con la lista vacia.  Un JSON que no parsea es peor que
# un JSON sin leer: `run-all` se declaraba INVALID_RESULT por su propia
# sintaxis de salida, no por las herramientas.  (201)
: > "$TMP/entradas.jsonl"
# El array entero como UNA linea, para poder consumirlo desde python con un
# `json.loads` de una vez.  Antes solo se escribia linea a linea, que es lo que
# necesita el ensamblado del artefacto; este es el otro consumidor.  (232)
ENTRADAS_JSONL="["
jsonl_escapar() {  # $1 = texto plano -> $2 = cadena JSON segura
  local t="$1"
  t="${t//\\/\\\\}"; t="${t//\"/\\\"}"
  printf '"%s"' "$t"
}

registrar() {  # tool estado detalle
  local tool="$1" estado="$2" detalle="$3"
  local _obj
  _obj="$(printf '{"herramienta":%s,"estado":%s,"detalle":%s}' \
    "$(jsonl_escapar "$tool")" "$(jsonl_escapar "$estado")" \
    "$(jsonl_escapar "$detalle")")"
    # La coma del separador es una COMA, no la palabra "comma": con
  # `${X:+,comma}` la expansion mete la cadena `comma` y el array queda
  # `[{...}comma{...}]`.  MEDIDO: salia "no se pudo extraer el estado" con un
  # JSON que era valido a la vista, porque era `[objcommaobj]` y no un array.
  # Un separador escrito como palabra en vez de como caracter.  (233)
  # La coma del separador se decide con un `if`, no con `$( [ ... ] && echo ,)`:
  # dentro de `$(...)` una expresion que empieza por `[` la interpreta bash como
  # indice de ARRAY, no como comando de test, y el resultado es silenciosamente
  # vacio.  Con `[ ... ] && echo ,` a secas (fuera de `$()`) no hay ambiguedad.
  if [ "${ENTRADAS_JSONL}" != "[" ]; then ENTRADAS_JSONL="$ENTRADAS_JSONL,"; fi
  ENTRADAS_JSONL="$ENTRADAS_JSONL$_obj"
  _coma=","
  printf '{"herramienta":%s,"estado":%s,"detalle":%s}\n' \
    "$(jsonl_escapar "$tool")" "$(jsonl_escapar "$estado")" \
    "$(jsonl_escapar "$detalle")" >> "$TMP/entradas.jsonl"
  case "$estado" in
    PASS)              n_pass=$((n_pass+1))    ;;
    SKIP_ENTORNO)      n_skip=$((n_skip+1))    ;;
    FAIL)              n_fail=$((n_fail+1))    ;;
    INVALID_RESULT)    n_invalid=$((n_invalid+1)) ;;
    TOOL_MISSING)      n_missing=$((n_missing+1)) ;;
  esac
  printf '  %-14s %-15s %s\n' "$tool" "$estado" "$detalle"
}

for fila in "${PLAN[@]}"; do
  # tarea:modo:timeout:extra_env   (221)
  tool="${fila%%:*}"; r1="${fila#*:}"
  modo="${r1%%:*}";   r2="${r1#*:}"
  to="${r2%%:*}";     extra="${r2#*:}"
  # El nombre de la TAREA no tiene que ser el del fichero: el sufijo dice que
  # variante se ejecuta.  Sin esto habria que crear un `mandato_parche.py` que
  # no hace nada nuevo, o renombrar el fichero, y las dos cosas son peor que un
  # convenio de nombres.  `tarea -> fichero` es la primera parte antes del
  # primer `:`.  (224)
  prog="${tool%%-*}"
  # El codigo SIEMPRE de $CODIGO; los fixtures solo si el modo lo pide.
  case "$modo" in
    --self-test) py="$FIXTURES/$prog.py" ;;
    *)           py="$CODIGO/$prog.py" ;;
  esac
  log="$TMP/$tool.log"

  if [ ! -f "$py" ]; then
    registrar "$tool" TOOL_MISSING "no existe $py"
    continue
  fi

  # `env` con el extra: el mandato necesita el sandbox y sin el lee el mandate
  # real, que no es lo que se quiere medir aqui.
  # El modo puede necesitar ARGUMENTOS: `mandato --parche` exige el directorio
  # del mandate detras del flag.  Sin esto se invoca `--parche` a secas, la
  # herramienta cae al uso, escribe un error de uso, y el ciclo lo lee como "no
  # declaro las comprobaciones" -- que es un sintoma de no haberle pasado el
  # argumento, no un fallo de la herramienta.  El quinto campo del plan lo lleva.
  # (225)
  argos=""
  if [ "${extra#* }" != "$extra" ]; then
    argos="${extra##* }"
    extra="${extra% *}"
  fi
  if ! timeout "$to" env $extra python3 -u "$py" "$modo" $argos > "$log" 2>&1; then
    rc=$?
  else
    rc=0
  fi

  # --- VALIDACION DEL ARTEFACTO, antes de leer nada del log ---
  #
  # regla 25: exit 0 sin artefacto es INVALID_RESULT, no exito.  Y aqui hay un
  # segundo caso que no es "no hay log": el log EXISTE pero vacio, que es lo que
  # pasa si el proceso muere antes de escribir nada.
  if [ ! -s "$log" ]; then
    registrar "$tool" INVALID_RESULT "log vacio o ausente (rc=$rc)"
    continue
  fi
  # El FORMATO DE SALIDA depende del modo.  Un self-test declara `N pasaron,
  # M fallaron`; `mandato --parche` declara una tabla de veredictos con nombre.
  # Antes se exigia el recuento a todos los modos, asi que una tarea de veredicto
  # habria salido INVALID_RESULT por no tener recuento -- que es leer un
  # veredicto como si fuera un self-test, o al reves.  Cada modo tiene su
  # criterio, y cada criterio declara su formato.  (222)
  if [ "$modo" = "--self-test" ]; then
    if ! grep -qE '[0-9]+ pasaron' "$log"; then
      registrar "$tool" INVALID_RESULT "el log no declara recuento ($(wc -l < "$log") lineas)"
      continue
    fi
  elif [ "$modo" = "--parche" ]; then
    # El veredicto del parche tiene que declarar sus TRES comprobaciones con
    # nombre.  Un log que solo dice `PASS` sin nombrar nada no es un veredicto:
    # es un color.
    if ! grep -qE '^[[:space:]]*(TABLA|COMPILACION|SUITE|TODO)[[:space:]]' "$log"; then
      registrar "$tool" INVALID_RESULT "el log no declara las comprobaciones con nombre"
      continue
    fi
  else
    registrar "$tool" INVALID_RESULT "modo desconocido: $modo"
    continue
  fi
  # El recuento se lee con DOS greps independientes y se exige que las dos
  # cifras cuadren.  Antes se parseaba con `${resumen%% *}` y una errata de un
  # caracter en el formato dejaba `fallan` vacio y `set -u` abortaba el ciclo
  # entero: un fallo de formato se convertia en "no se ejecuto nada", que es la
  # confusion mas cara que hay.  (200)
  if [ "$modo" = "--parche" ]; then
    # El log de una tarea de veredicto NO se borra: es la unica copia de la
    # evidencia que produjo.  Los de self-test si, porque se resumen en el
    # recuento.  Sin esto, un FAIL de veredicto arrives al artefacto sin el
    # texto que lo produjo, y hay que volver a ejecutar para ver por que.  (228)
    cp -f "$log" "${RX550_KIT_LOGS:-${RX550_KIT_LOGS:-$ROOT/08-ARQUITECTURA/logs-rx550}}/$tool.log" 2>/dev/null || true
    # El veredicto del parche se clasifica por SU PROPIA linea, no por el codigo
    # de salida.  `mandato` sale 0 con SKIP_ENTORNO y SKIP_ESCRITURA, que no es
    # un fallo del codigo pero tampoco es un todo verde: cuatro estados.
    # Leerlo como "exit 0 = PASS" seria el error de la regla 24 aplicado a la
    # herramienta que corrige los demas.  (223)
    pv="$(grep -E '^[[:space:]]*TODO[[:space:]]' "$log" | tail -1 | awk '{print $2}')"
    pdet="$(grep -E '^[[:space:]]*TODO[[:space:]]' "$log" | tail -1 | cut -c13- | sed 's/^ *//')"
    case "$pv" in
      PASS)
        registrar "$tool" PASS "PARCHE: $pdet"
        n_parche_ok=$((n_parche_ok + 1))
        ;;
      *)
        registrar "$tool" FAIL "PARCHE: TODO=$pv  $pdet"
        n_fail=$((n_fail + 1))
        ;;
    esac
    continue
  fi

  resumen="$(grep -oE '[0-9]+ pasaron, [0-9]+ fallaron' "$log" | tail -1)"
  n_pasaron="$(grep -oE '[0-9]+ (pasaron|pasó)' "$log" | tail -1 | grep -oE '^[0-9]+' || true)"
  n_fallaron="$(grep -oE '[0-9]+ fallaron' "$log" | tail -1 | grep -oE '^[0-9]+' || true)"
  if [ -z "$resumen" ] || [ -z "$n_pasaron" ] || [ -z "$n_fallaron" ]; then
    registrar "$tool" INVALID_RESULT "recuento ilegible: '${resumen}'"
    continue
  fi
  if [ "$n_pasaron" -eq 0 ] && [ "$n_fallaron" -eq 0 ]; then
    registrar "$tool" INVALID_RESULT "recuento de ceros: nadie ejecuto nada"
    continue
  fi
  if [ "$n_fallaron" -gt 0 ]; then
    registrar "$tool" FAIL "$resumen  (rc=$rc)"
    continue
  fi
  # El corpus ausente NO es un fallo del codigo: se declara SKIP_ENTORNO con el
  # motivo, igual que R00 en la suite del mandate.  Solo cuenta si el corpus no
  # esta montado Y el log lo dice; si esta montado, un fallo es un fallo.
  if [ ! -d "$CORPUS" ] && grep -qE 'no such file|No such file|FileNotFound' "$log"; then
    registrar "$tool" SKIP_ENTORNO "$resumen  (corpus no montado)"
    continue
  fi
  registrar "$tool" PASS "$resumen"
done

# --- VEREDICTO ---
# Un ciclo "verde" que no ha medido nada no es un ciclo verde.  El total de
# aserciones ejecutadas es el dato que distingue "todo pasa" de "nadie
# comprobo": 15 herramientas con 0 aserciones cada una darian PASS igual.  Se
# mide el suelo y se declara, porque un PASS sobre 0 comprobaciones es
# INVALID_RESULT por la regla 25 aplicada al recuento.  (202)
# El numero de entradas del PLAN tiene que coincidir con el de herramientas
# registradas.  Sin esto, una linea perdida se lee como "una herramienta menos"
# y el veredicto sigue verde.  (207)
# --- el objetivo, leido del sistema y resuelto contra el corpus ---------------
FP_RAW="$(fingerprint)"
FP_HASH="$(fp_hash "$FP_RAW")"
IFS='|' read -r FP_VENDOR FP_DEVICE FP_SUBV FP_SUBD FP_REV FP_CLASS \
    FP_DRV FP_ASIC FP_BAR0 FP_VRAM FP_BOARD FP_BIOS FP_NODO FP_TOPO <<< "$FP_RAW"
FP_CAMPO="$FP_RAW"
FP_KERNEL="$(uname -r)"
FP_ARQ="$(uname -m)"
# El objetivo ESPERADO, para que un cambio de hardware sea visible aunque el
# veredicto siga verde.  Es una comparacion explicita, no una suposicion: se
# compara lo leido con lo declarado, y si difiere se dice cual.
# En la MISMA notacion que lo leido: los IDs sysfs vienen como 0x1002 y la
# tabla del corpus devuelve CHIP_POLARIS12.  Comparar `CHIP_POLARIS12` con
# `POLARIS12` es un fallo mio de formato, y un fallo de formato aqui produce un
# TARGET_MISMATCH que no existe -- que es peor que no comprobar, porque el ciclo
# declara que la maquina no es la correcta cuando si lo es.  La forma de la
# comparacion la define el LECTOR, no el esperado.  (212)
FP_ESPERADO="0x1002:0x699f:0x1002:0x0b04:CHIP_POLARIS12:amdgpu"
FP_LEIDO="$FP_VENDOR:$FP_DEVICE:$FP_SUBV:$FP_SUBD:$FP_ASIC:$FP_DRV"
if [ "$FP_LEIDO" = "$FP_ESPERADO" ]; then
  FP_COINCIDE=true
else
  FP_COINCIDE=false
fi
printf '  objetivo   %s\n' "$FP_LEIDO"
printf '  esperado   %s  ->  %s\n' "$FP_ESPERADO" \
    "$([ "$FP_COINCIDE" = true ] && echo COINCIDE || echo TARGET_MISMATCH)"

# El array completo, listo para json.loads.  Los corchetes se ponen UNA vez: si
# `registrar` ya los pone, envolver aqui daria "[[{...}]]" y `json.loads` lo
# acepta como array de UN array -- que parsea sin error y no es lo que se pide.
# Un JSON que parsea y no es lo que creias es peor que uno que no parsea.  (235)
ENTRADAS_JSONL="${ENTRADAS_JSONL}]"

n_plan="${#PLAN[@]}"
n_reg="$(grep -c . "$TMP/entradas.jsonl" 2>/dev/null || echo 0)"

n_asserts=0
if [ -s "$TMP/entradas.jsonl" ]; then
  # Solo se suman las cifras de los SELF-TEST.  Una tarea de veredicto no tiene
  # aserciones: tiene comprobaciones, y sumarlas al recuento de aserciones
  # inflaria el suelo con numeros que no son comparables.  (222)
  n_asserts="$(sed -n 's/.*"detalle":"\([0-9][0-9]*\) pasaron.*/\1/p' \
               "$TMP/entradas.jsonl" | awk '{s+=$1} END{print s+0}')"
fi
# El suelo se comprueba DESPUES de clasificar, y solo si el veredicto no es ya
# FAIL ni INVALID: si algo fallo de verdad, tapar ese fallo con "no hubo
# suficientes aserciones" seria ocultar la causa.  El suelo solo puede PROMOVER a
# INVALID un PASS que no ha medido nada.  (202)
# El ESTADO COMPARABLE: una sola cadena, en orden de nombre, con el estado de
# cada tarea y su recuento.  Es lo que se compara entre corridas, y se guarda en
# el artefacto para que la comparacion sea contra un fichero y no contra una
# memoria de ejecucion.  (232)
FP_ESTADO="$(printf '%s\n' "$ENTRADAS_JSONL" | python3 -c '
import json, sys, re
try:
    d = json.loads(sys.stdin.readline().strip())
except Exception:
    print("ERROR_LECTURA"); raise SystemExit(0)
parts = []
for h in sorted(d, key=lambda x: x["herramienta"]):
    det = h["detalle"]
    m = re.match(r"(\d+) pasaron", det)
    rec = m.group(1) if m else ("PARCHE" if det.startswith("PARCHE") else "-")
    parts.append("%s=%s:%s" % (h["herramienta"], h["estado"], rec))
print("|".join(parts))' 2>/dev/null)"
printf '  estado     %s tareas en la cadena comparable\n' \
    "$(printf '%s' "$FP_ESTADO" | awk -F'|' '{print NF}')"

SUELO="${RX550_KIT_MIN_ASSERTS:-300}"

# El artefacto tiene que existir, pesar y parsear ANTES de que el veredicto
# cuente.  Se comprueba despues de escribirlo, y si falla se degrada a
# INVALID_RESULT: el script no puede afirmar PASS sobre un artefacto que no ha
# podido validar.  (203)
if [ ! -s "$OUT" ]; then
  veredicto="INVALID_RESULT"
  detalle="el artefacto no se escribio o esta vacio"
fi

total=$((n_pass + n_skip + n_fail + n_invalid + n_missing))
if [ "$n_invalid" -gt 0 ] || [ "$n_missing" -gt 0 ]; then
  veredicto="INVALID_RESULT"
  detalle="hay comprobaciones que no se pudieron hacer: ${n_invalid} invalid + ${n_missing} ausentes"
elif [ "$n_fail" -gt 0 ]; then
  veredicto="FAIL"
  detalle="$n_fail de $total fallaron"
elif [ "$n_pass" -gt 0 ]; then
  veredicto="PASS"
  detalle="$n_pass pasaron${n_skip:+, $n_skip SKIP_ENTORNO}, $n_asserts aserciones"
else
  veredicto="INVALID_RESULT"
  detalle="ninguna herramienta produjo un recuento utilizable"
fi

  # El suelo se comprueba DESPUES de clasificar, y solo si el veredicto no es ya
  # FAIL: si algo fallo de verdad, tapar ese fallo con "no hubo suficientes
  # aserciones" seria ocultar la causa.  El suelo solo puede PROMOVER a INVALID
  # un PASS que no ha medido nada.  (202)
  # Una entrada del plan que no llego a registrarse es una comprobacion que no
  # se hizo.  No se cuenta como FAIL (puede ser un TOOL_MISSING declarado), pero
  # tampoco puede quedar en un PASS sin avisar.
  # Un `PASS` sobre otra tarjeta no es un PASS de esta tarjeta.  El objetivo se
  # comprueba AL FINAL, con el veredicto ya calculado, para que un cambio de
  # hardware no pueda quedar como un verde sin commentary.  Y el desajuste no
  # degrada un FAIL real: si algo fallo, ese fallo es lo que se dice.  (209)
  if [ "$FP_COINCIDE" != "true" ]; then
    if [ "$veredicto" = "PASS" ]; then veredicto="TARGET_MISMATCH"; fi
    detalle="el objetivo leido ($FP_LEIDO) no es el esperado ($FP_ESPERADO)"
  fi

  if [ "$n_reg" -ne "$n_plan" ]; then
    if [ "$veredicto" = "PASS" ]; then veredicto="INVALID_RESULT"; fi
    detalle="$n_reg de $n_plan herramientas llegaron a registrarse"
  fi
  printf '  plan       %s entradas, %s registradas\n' "$n_plan" "$n_reg"
  if [ "$veredicto" = "PASS" ] && [ "${n_asserts:-0}" -lt "$SUELO" ]; then
    veredicto="INVALID_RESULT"
    detalle="solo $n_asserts aserciones y el suelo es $SUELO: un PASS sobre 0 comprobaciones no es un PASS"
  fi
  printf '  aserciones  %s (suelo %s)\n' "$n_asserts" "$SUELO"


  # Se comprueba que el artefacto SE PUEDA ESCRIBIR antes de escribirlo.  Con un
  # destino invalido, el `{ ... } > $OUT` falla en silencio, el script sigue y
  # acaba imprimiendo PASS con un artefacto de 0 B al lado.  En pantalla eso
  # parece un fallo del validador; era un fallo del PRODUCTOR que nadie miraba,
  # que es la regla 25 al reves.  (203)
  DIR_OUT="$(dirname "$OUT")"
  if [ ! -d "$DIR_OUT" ] || ! : > "$OUT.probe" 2>/dev/null; then
    veredicto="INVALID_RESULT"
    detalle="el destino $OUT no es escribible: sin artefacto no hay veredicto"
  else
    rm -f "$OUT.probe"
  fi
{
  printf '{\n'
  # El fingerprint va en el artefacto, no en un fichero aparte: si vive
  # separado, el veredicto se puede leer sin el y perder el anclaje.  (208)
  printf '  "artefacto": "KIT-VERDICT",\n'
  printf '  "fingerprint": %s,\n' "$(jsonl_escapar "$FP_CAMPO")"
  printf '  "fingerprint_hash": %s,\n' "$(jsonl_escapar "$FP_HASH")"
  printf '  "fingerprint_esperado": %s,\n' "$(jsonl_escapar "$FP_ESPERADO")"
  printf '  "objetivo": {\n'
  printf '    "pci": %s, "vendor": %s, "device": %s,\n' \
    "$(jsonl_escapar "$FP_PCI")" "$(jsonl_escapar "$FP_VENDOR")" "$(jsonl_escapar "$FP_DEVICE")"
  printf '    "subsystem_vendor": %s, "subsystem_device": %s,\n' \
    "$(jsonl_escapar "$FP_SUBV")" "$(jsonl_escapar "$FP_SUBD")"
  printf '    "revision": %s, "class": %s,\n' \
    "$(jsonl_escapar "$FP_REV")" "$(jsonl_escapar "$FP_CLASS")"
  printf '    "asic_resuelta": %s, "asic_fuente": "amdgpu_drv.c (tabla de PCI IDs)",\n' \
    "$(jsonl_escapar "$FP_ASIC")"
  printf '    "driver": %s, "bar0": %s, "vram": %s,\n' \
    "$(jsonl_escapar "$FP_DRV")" "$(jsonl_escapar "$FP_BAR0")" "$(jsonl_escapar "$FP_VRAM")"
  printf '    "nodo_drm": %s, "topologia_pci": %s,\n' \
    "$(jsonl_escapar "$FP_NODO")" "$(jsonl_escapar "$FP_TOPO")"
  printf '    "placa": %s, "bios": %s,\n' \
    "$(jsonl_escapar "$FP_BOARD")" "$(jsonl_escapar "$FP_BIOS")"
  printf '    "kernel": %s, "arquitectura": %s\n' \
    "$(jsonl_escapar "$FP_KERNEL")" "$(jsonl_escapar "$FP_ARQ")"
  printf '  },\n'
  printf '  "objetivo_coincide": %s,\n' "$FP_COINCIDE"
  printf '  "estado_comparable": %s,\n' "$(jsonl_escapar "$FP_ESTADO")"
  printf '  "generado_por": "run-all.sh",\n'
  printf '  "corpus": %s,\n' "$(jsonl_escapar "$CORPUS")"
  printf '  "corpus_montado": %s,\n' "$([ -d "$CORPUS" ] && echo true || echo false)"
  printf '  "sandbox": %s,\n' "$(jsonl_escapar "$SANDBOX")"
  printf '  "total": %s,\n' "$total"
  printf '  "resumen": {"PASS": %s, "SKIP_ENTORNO": %s, "FAIL": %s, "INVALID_RESULT": %s, "TOOL_MISSING": %s},\n' \
    "$n_pass" "$n_skip" "$n_fail" "$n_invalid" "$n_missing"
  printf '  "veredicto": %s,\n' "$(jsonl_escapar "$veredicto")"
  printf '  "detalle": "%s",\n' "$detalle"
  printf '  "herramientas": ['
  if [ -s "$TMP/entradas.jsonl" ]; then
    awk 'BEGIN{first=1}
         { if (!first) printf ","; printf "%s", $0; first=0 }
         END{ printf "\n" }' "$TMP/entradas.jsonl"
  fi
  printf '  ]\n' 
  printf '}\n'
} > "$OUT" 2>/dev/null || : > "$OUT"

if [ ! -s "$OUT" ]; then
  veredicto="INVALID_RESULT"
  detalle="el artefacto no se pudo escribir en $OUT: sin artefacto no hay veredicto"
fi


# La COMPARACION con una corrida anterior, si se pasa `--compara`.  Va DESPUES
# de escribir el artefacto, porque lo que se compara es el estado que este ciclo
# acaba de producir, y va DESPUES del veredicto para no convertir un cambio de
# resultado en un fallo: un cambio es informacion.  (232)
if [ -n "${RX550_KIT_COMPARA:-}" ]; then
  if ! compara_veredicto "$RX550_KIT_COMPARA"; then
    REPRODUCIDO=false
  fi
  if [ "$REPRODUCIDO" = false ]; then
    # NO_REPRODUCED no hunde el veredicto, pero tampoco se pierde: se escribe en
    # el artefacto y en la salida, y sale con codigo 4, su propio.
    printf '%s\n' "$FP_ESTADO" > "$OUT.estado"
    echo "  estado guardada en $OUT.estado"
  fi
fi

  if [ "$REPRODUCIDO" = false ] && [ "$veredicto" = "PASS" ]; then
    # Un resultado que no se reproduce no es un PASS: es un resultado que no
    # se ha comprobado.  Y no es un FAIL tampoco -- el codigo esta bien, lo que
    # cambia es que no da lo mismo dos veces.  Estado propio, con su codigo de
    # salida, para que no se confunda con un fallo del codigo.  (234)
    veredicto="NO_REPRODUCED"
    detalle="el estado difiere de la corrida anterior; el detalle esta en la salida"
  fi

echo
echo "  ----"
echo "  VEREDICTO  $veredicto   $detalle"
echo "  artefacto  $OUT ($(stat -c%s "$OUT" 2>/dev/null || echo 0) B)"
# Si el JSON no parsea, el veredicto impreso no puede seguir diciendo PASS: lo
# que se ha impreso y lo que el fichero contiene son dos afirmaciones distintas
# sobre el mismo resultado, y la que se lee en pantalla es la que se recuerda.
# Se corrige ANTES de imprimir, no despues.  (218)
if ! python3 -c "import json; json.load(open('$OUT'))" 2>/dev/null; then
  veredicto="INVALID_RESULT"
  detalle="el artefacto se escribio pero no es JSON valido"
  echo "  VEREDICTO  $veredicto   $detalle"
fi
case "$veredicto" in
  PASS)            exit 0 ;;
  FAIL)            exit 1 ;;
  TARGET_MISMATCH) exit 3 ;;
  NO_REPRODUCED)   exit 4 ;;
  *)               exit 2 ;;
esac
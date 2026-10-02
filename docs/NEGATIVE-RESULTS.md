# NEGATIVE-RESULTS — lo que se buscó y no se encontró

> Un resultado negativo no es "no pasa nada": es un resultado con alcance. Se registra
> **qué descarta** y, sobre todo, **qué no descarta**.
>
> Regla que este fichero existe para hacer cumplir:
> `NOT_FOUND ≠ PROVEN_ABSENT` · `NOT_OBSERVED ≠ ABSENT` · `PARTIAL ≠ COMPLETE`.
>
> `LAST_SCAN: 2026-10-01 11:20 -03:00`

---

## NR-01 · No existe registro de acknowledgement de invalidación en GFX8

```
TEST      barrido completo de los registros de control de ATC/L1/L2 del ASIC
SCOPE     gmc_8_2 / gca, corpus 7.1.3 y 7.2.8, READ_SCOPE_GATE ejecutado
RESULT    no hay campo de estado ni de respuesta del invalidate utilizable como ack
QUITA     la hipótesis de que exista una espera por hardware de la completion
NO QUITA  que el hardwareerialice en algún momento; que no sea observable desde el
          software no es que no exista
CLASSIF   NOT_FOUND  (barrido de un corpus completo, luego es PROVEN_ABSENT *dentro del
          corpus*; el hardware queda NOT_DETERMINED)
CONSECUENCIA  RE-02: esperar completion del invalidate es NOT_IMPLEMENTABLE con este
          juego de registros. No es una pregunta pendiente: no hay a qué esperar.
DEPENDENCIAS  closure de PTBA + invalidate; seguridad del path de ring
```

**Matiz que 018 deja y que no se debe perder**: esto cierra la *espera explícita*. El
*orden de ejecución* del invalidate respecto al siguiente IB sigue abierto y sí es
medible. "No implementable" no es "no investigado".

## NR-02 · `VM_INVALIDATE_REQUEST` no tiene granularidad en GFX8

```
TEST      ¿existen selectores INVALIDATE_L1_PTES / L2_PTES / 4K_PAGES_ONLY?
SCOPE     gmc_8_2 completo, contrastado con GFX9+
RESULT    no. 16 bits, un bit por VMID, nada más
QUITA     toda la línea de investigación "¿qué nivel de TLB invalida el driver?"
          No es una elección del software: no hay encoding para elegir
NO QUITA  que L1 y L2 se invaliden juntos. Que no haya selector no dice qué ocurre
          internamente; dice que no se puede pedir menos
CONSECUENCIA  flush_type y vmhub son PARÁMETROS MUERTOS en gmc_v8_0_flush_gpu_tlb
          (gmc_v8_0.c:661-666): se reciben y se descartan
CONTRASTE  GFX9+ los tiene y el driver los pone a 1. Es el contraste que hace la
          ausencia informative en lugar de casual
```

## NR-03 · Coccinelle no está y se perdió con `/tmp`

```
TEST      semref engines / refs / chain
RESULT    ctags DISPONIBLE (Universal Ctags 6.2.1)
          coccinelle ENGINE-NOT-AVAILABLE
          refs -> rc=3 con "falta ctags o coccinelle; no se degrada en silencio"
          run-bench -> NOT_RUN, "NO se da por aprobado"
ALCANCE   la instalación vivía en /tmp/opencode/tools; ese directorio no existe ahora
CLASIF    INVALID (era VALIDATED, la dependencia se fue)
QUITA     reutilizar la salida de semref como evidencia, hasta reinstalar
NO QUITA  nada del conocimiento ya adquirido con ella: los findings que la citan
          (015, P-8) conservan su valor, porque se produjeron cuando funcionó
LO BUENO  el diseño es el correcto: exit 3 y NOT_RUN, nunca un PASS vacío. Un tool
          que devuelve vacío cuando falta una dependencia es peor que uno que falla
REPARACIÓN  reinstalar Coccinelle desde el RPM en un prefijo NO efímero
          (/opt o $HOME), no en /tmp. Está en TOOLS-STATUS.md, no aplicada aquí:
          es instalación de software, fuera del alcance documental
```

## NR-04 · `semref` no distingue sino con **ambos** motores

```
TEST      semref refs amdgpu_fence_process --root <árbol amdgpu>
RESULT    rc=3 aunque ctags esté DISPONIBLE
CAUSA     el gate de `refs` y `chain` es engine_state() sin argumentos, que devuelve
          no-cero si falta CÓMOQUIER motor. ctags por sí solo no habilita el comando
CONSECUENCIA  con la instalación actual, semref no hace NADA. No es "degradado": es inútil
CLASIF    INVALID
```

Consecuencia de diseño que vale para todo el repo: **una herramienta que declara
"no degrado en silencio" y luego se niega a usar la mitad de lo que tiene sí está
 degradando en silencio** — degrada al resultado esperado. El README de `semref` es
 explícito en que no resuelve punteros a función (`F = f`, `E.F = f`, `T F = f`
 fallaron contra `.enable_signaling = amdgpu_fence_enable_signaling`), o sea que la
 mitad de ctags no le bastaba para lo que promete.

## NR-05 · Dos herramientas no se ejecutan desde la raíz del repo, y una miente

```
QUIÉN     2 de las herramientas con rutas relativas al cwd fallan al invocarlas desde
          la raíz del repo. El defecto se REPITE, que es lo que lo convierte en patrón

CASO A · gfx8vmgeom                      TOOLS-STATUS TL-03
TEST      ./08-ARQUITECTURA/tools/gfx8vmgeom/gfx8vmgeom   (cwd = raíz del repo)
RESULT    ERROR: no se pudo cargar el corpus: amd_asic_type.h ... no coincide con el
          sha256 de 7.1.3     RESULT: NO EJECUTADO     rc=2
DESDE SU DIRECTORIO   "corpus cargado", 37 OK, 12/12 negativos     rc=0
CAUSA     rutas relativas al cwd (../../../RESEARCH/...)
LO QUE DESCARTA  una lectura del error que dice "el corpus está corrupto". El sha256 que
          espera (cea577df…7809) es EXACTAMENTE el del fichero real. Fallaba la RUTA y
          el mensaje nombra el FICHERO

CASO B · pteflags                        TOOLS-STATUS TL-09
TEST      ./08-ARQUITECTURA/tools/pteflags/pteflags        (cwd = raíz del repo)
RESULT    ERROR: no se pudo ejecutar el censo: no se pudo leer amdgpu_vm.h
          RESULT: NO EJECUTADO        rc=2
DESDE SU DIRECTORIO   19 aserciones, 0 fallos, 5/5 negativos   rc=0
CAUSA     la misma: la raíz es relativa y no resuelve
LO QUE DESCARTA  "amdgpu_vm.h no se puede leer". Se puede, y se lee: lo que no resolvió
          es la raíz. El mensaje nombra el fichero, no la ruta

CLASIF    el fallo es de invocación y de diagnóstico, NO de la herramienta. Ninguna de
          las dos está rota: las dos funcionan desde su directorio
LA DIFERENCIA QUE IMPORTA
  gfx8vmgeom  -> rc=2 en el fallo
  pteflags    -> rc=2 en el fallo
  Los DOS códigos de salida son correctos. Al principio se sospechó que pteflags
  devolvía 0 en el fallo, por un "| head" que enmascaraba el código de salida. Es
  exactamente el fallo que AGENTS.md prohíbe: aceptar "errors: 0" sin comprobar el
  artefacto. LA SOSPECHA ERA EL ERROR, NO LA HERRAMIENTA. Se verificó con redirección a
  fichero y `echo $?`, y el resultado cambió
LO QUE NO SE HIZO  arreglar los mensajes ni documentar el cwd en los README de las
          herramientas: son ficheros de otras sesiones. Registrado aquí y en
          TOOLS-STATUS. Uno de los dos README no existe
POR QUÉ ESTE ES EL RESULTADO NEGATIVO MÁS INSTRUCTIVO DE LA LISTA
  Un mensaje de error que nombra la causa equivocada induce a investigar lo que NO está
  roto. Si una sesión hubiera leído cualquiera de los dos ERROR sin reintentar desde el
  directorio, habría reportado "corrupción del corpus de referencia" o "falta
  amdgpu_vm.h". Y en un proyecto donde el corpus sostiene 35 hallazgos, esa conclusión
  errónea es más cara que un NOT_FOUND suelto
LO QUE DEBERÍA SER EL HÁBITO, y no está en ningún README de este repo
  Ninguna herramienta de análisis que dependa de rutas relativas declara el requisito.
  Las dos que lo tienen fallan de la misma forma. El array de -I de 73 entradas con
  ruta completa que usa pteflags SÍ está razonado y documentado en su cabecera -- el
  cwd, no
```

## NR-06 · 22 emisiones de PACKET3 no son contables estáticamente

```
TEST      pm4_count_census.py --only=fx8
RESULT    emisiones PACKET3 con n literal y final alcanzable : 68
          emisiones NO contables de forma estatica          : 22
          n - payload = -1  :  68 ocurrencias
MOTIVOS   "rama/loop entre header y fin"  (21 de las 22)
          "n no literal: 'cnt_ce'"        (ring_emit_ce_meta)
          "n no literal: 'cnt_de'"        (ring_emit_de_meta)
QUITA     nada sobre esas 22: no se cuenta lo que no se puede contar
NO QUITA  la regla. 68/68 es una propiedad de las contables, no de todas
CLASSIF   NOT_DETERMINED por emisión, con el motivo nombrado. No NOT_FOUND
POR QUÉ IMPORTA  dos de las no contables son ce_meta y de_meta, que son justo las
          que 021-frame usa para explicar la sobre-reserva de emit_frame_size.
          Su reserva (14 y 31 dw) incluye la variante chained_ib que no se ejecuta.
          La aritmética de 021 se apoya en una lectura manual de código que esta
          herramienta no puede confirmar automáticamente
DEPEDENCIAS  el texto de 021-frame que explica por qué 172 y no 8+…
```

## NR-07 · `write_multiple` ya se expande — y valía 17, no 1

```
TOOL     pm4dw
ESTADO   SUPERSEDED dos veces, y cerrado
         1) 2026-10-01 11:40  026-frame lo expandió A MANO desde vi_structs.h
         2) 2026-10-01 12:1x  027-write-multiple lo automatizó: pm4dw --struct-size
            --wm-sites. La cifra se mueve sola si cambia la struct
ANTES    gfx_v8_0_ring_emit_ce_meta   4   4   write_multiple: NOT EXPANDED
         gfx_v8_0_ring_emit_de_meta   4   4   write_multiple: NOT EXPANDED
         CLASIF    PARTIAL, declarado en la salida
AHORA    medido y verificado a mano contra el código
           vi_ce_ib_state               4 miembros  16 B   cnt  6   wm  4  ->   8 dw
           vi_ce_ib_state_chained_ib   10 miembros  40 B   cnt 12   wm 10  ->  14 dw
           vi_de_ib_state              17 miembros  68 B   cnt 19   wm 17  ->  21 dw
           vi_de_ib_state_chained_ib   27 miembros 108 B   cnt 29   wm 27  ->  31 dw
         con cnt = (sizeof(payload) >> 2) + 4 - 2  y 4 dwords de cabecera
CORROBORATION  las cuatro cifras coinciden con las que 021-frame dedució A MANO a las
         10:28 del mismo día. Dos métodos, mismo resultado -> RE-23
CONSECUENCIA  los 172 dw de --struct eran cota superior de handlers. Con los
         write_multiple resueltos y la composición real, el número definitivo del frame
         GFX8 es 121 dw (137 con chained IB), más num_ibs * 4. Ver RE-16
POR QUÉ SE REGISTRA IGUAL  El error de razonamiento es lo que conviene conservar: una
         herramienta que marca "NOT EXPANDED" es correcta al no inventar, pero su
         salida se puede leer como "eso no emite nada". Emitía 4, 10, 17 y 27
LO QUE APRENDE ESTE REPO, por cuarta vez  lo que no se mide no es cero. Y por quinta:
         lo que se mide A MANO en el número que más se cita es una dependencia de
         criterio. El hallazgo 027 lo dice con esas palabras
```

## NR-07b · `LOOKAHEAD_LINES 3` hacía desaparecer una función real

```
TOOL     pm4dw
SÍNTOMA  gfx_v8_0_ring_emit_gds_switch salía ABSENT. No es absent: está en
         gfx_v8_0.c:5122, y vale 20 dw
CAUSA    LOOKAHEAD_LINES 3. La firma de esa función reparte SIETE parámetros en cinco
         líneas antes de la llave, así que el cap no alcanzaba
FIX      una REGLA CON MOTIVO en lugar de un cap: "una declaración sólo continúa
         mientras las líneas sigan formando una lista de parámetros: sin ';' y sin
         línea vacía". Tope duro 12 como red de seguridad, no como regla
POR QUÉ ESTÁ AQUÍ  El rótulo que se conserva es lo que evita la repetición:
         ABSENT significa "o no existe, o el parser no la ve", y se reporta así a
         propósito. "No existe" y "no la veo" son hallazgos distintos
REFUERZA NR-09 y NR-11: el fallo por defecto de un analizador de código es declarar
         ausencia. Un cap heurístico produce ausencia falsa con apariencia de dato
ORIGEN  025-vm-flush-path-gfx8-63dw.md §6
```

## NR-07c · La reserva de un envío son DOS sumandos, no uno

```
HALLAZGO  amdgpu_ib.c:197-198
            alloc_size = ring->funcs->emit_frame_size + num_ibs * ring->funcs->emit_ib_size;
            r = amdgpu_ring_alloc(ring, alloc_size);
          El frame y los IBs se reservan POR SEPARADO. emit_frame_size cubre todo lo
          que el anillo emite fuera de los indirect buffers, y cada IB añade
          emit_ib_size (= 4 en GFX8 GFX)
POR QUÉ IMPORTA  Convierte "¿cuál es la ruta máxima de un envío?" en aritmética
          cerrada, y corrige la lectura de tres findings previos: los residuales
          +98/+57/+46 y la ruta de 63 dw se comparaban contra un número que nunca
          incluía los IBs, y no hacía falta que los incluyera
LA CONSECUENCIA SI SE COPIA MAL
          emit_ib llama a gfx_v8_0_ring_emit_de_meta cuando
          amdgpu_sriov_vf(adev) && (ib->flags & AMDGPU_IB_FLAG_PREEMPT)
          — 21 dw, no 0. El IB real costaría 25 frente a los 4 reservados. Con la
          holgura de 51 dw del frame se toleran ~2 IBs con preemption antes de
          desbordar
CLASIF    LIMITATION, no DEFECT, por dos razones que constan: (a) exige SR-IOV VF, o
          sea la GPU dentro de una máquina virtual, que NO es el objetivo del proyecto;
          (b) no se ha verificado el límite de num_ibs ni el comportamiento de
          amdgpu_ring_alloc ante desbordamiento. Reclamar un bug aquí sería PLAUSIBLE,
          no PROVEN
POR QUÉ SE REGISTRA AUNQUE NO APLIQUE  porque el número emit_ib_size = 4 se va a copiar
          tal cual en un driver propio, y ahí sí importa. En metal desnudo no ocurre
ORIGEN  026-frame-completo-gfx8-121dw.md §1, §5
```

## NR-08 · El agreement test BC3 no tiene registro persistido

```
TEST      buscar evidencia versionada de "GPU == CPU" en el árbol
RESULT    NO EXISTE. Lo que hay:
            - el texto de commit 7ed1eca (PROVEN por testimony, no por artefacto)
            - 04-IMPLEMENTACION/work/*.decompress.log  -> 0 de 16384 bytes, 3 imágenes
              PERO .gitignore:78 ignora 04-IMPLEMENTACION/work/ en bloque
            - corpus_blocks.bin / corpus_cpu_ref.bin  -> artefactos del test, pero el
              que debería contener la SALIDA DE GPU no se persistió; los dos .bin
              que hay (1024 y 4096 B) son bloques comprimidos y referencia CPU
CLASIF    NO_RECHECKED. NO es REFUTED: no hay evidencia en contra
POR QUÉ IMPORTA  "0 de 4096 en 3 corridas" es la afirmación que sostiene la Fase 2
          COMPLETA, y su único soporte persistente está fuera de git. Un `git clean`
          con `-x` lo borra sin dejar rastro y nadie podría reconstruirlo
ACCIÓN     re-ejecutar test_decompress y commitear el log (acción 2 de
          MASTER-RESEARCH-STATUS §NEXT TECHNICAL ACTIONS)
```

## NR-09 · `NOT_FOUND` que este repo ya pagó dos veces

```
HECHO     cuatro búsquedas anteriores concluyeron "ausencia" sobre un subárbol
          extraído. El material estaba en el propio repo, en otro sitio
CONSECUENCIA  tools/evidence_search.py existe para que el error sea imposible por
          construcción: el universo de búsqueda es un ARGUMENTO, `--expect` declara
          qué debería contener, y sin hits la clasificación por defecto es
          NOT_DETERMINED + [NO ABSENCE CLAIM]. NOT_FOUND sólo con universo exhaustivo
CLASIF    LESSON_LEARNED,Registry'd para que no se repita
LACUNA    evidence_search.py no tieneDiscriminación negative-test registrada, o sea que
          no se ha visto fallar. Es la misma debilidad que este repo ya disadvantajó
          en otros sitios: un test que nunca se ha visto fallar no prueba que detecte.
          Registrado en TOOLS-STATUS.md como hueco
```

## NR-10 · El cerrojo de ámbito no excluye al de la raíz

```
TEST      mkdir .write-lock           -> rc=0
          mkdir .write-lock/findings  -> rc=0   CON LA RAÍZ YA TOMADA
RESULT    el mecanismo de exclusión del protocolo sólo protege contra dos sesiones que
          compiten por el MISMO nombre de lock. Nunca contra un ancestro
QUITA     la regla de COORDINACION.md:172 ("el cerrojo raíz es el único que excluye a
          las otras sesiones de todo")
OBSERVADO dos veces en la mañana del 2026-10-01, y la segunda vez el ÍNDICE NUMÉRICO
          también colisionó: dos sesiones eligieron 022, y dos eligieron 021
CLASIF    REFUTED sobre la regla del protocolo. Reproducible en POSIX: mkdir sólo
          falla con EEXIST, y .write-lock/findings no existe aunque .write-lock sí
NO QUITA  el valor del mkdir como exclusión atómica para el mismo nombre: funciona
CORRECCIÓN PROPUESTA por 021-write-lock §Corrección: comprobar que .write-lock no
          existe antes de mkdir .write-lock/<ámbito>. Una comprobación extra. NO
          APLICADA: COORDINACION.md es ley operativa y cambiarlo requiere decisión
          humana
```

Lo que **no** se observó, y se dice para no exagerar: **ningún fichero existente fue
sobrescrito**. Los dos `022` coexisten porque el sistema de ficheros creó nombres
distintos. Es `mkdir`/`O_CREAT` fair, no coordinación. El resultado correcto por el
mecanismo equivocado.

## NR-11 · Cifras de throughput de la línea BC3: `NOT_CONCLUYENTE`

```
TEST      speedup C -> AVX2
RESULT    el rango intra-implementación es del orden de la diferencia entre
          implementaciones:
            C    entre 78.9 y 85.1 MB/s
            AVX2 entre 83.5 y 88.6 MB/s
CLASIF    NOISE sin establecer para esta métrica
NO QUITA  que AVX2 sea más rápido. Deja de poder afirmarlo
CAUSA     identificada y coherente: el ensamblador reduce min/max, que es una fracción
          del trabajo; la selección de índices permanece en C
POR QUÉ SE REGISTRA  la primera versión de CIERRE_PROYECTO.md afirmaba un speedup
          numérico. El dato se retiró cuando se midió el rango. Es el precedente de
          cómo este repo trata una cifra no concluyente: se retira, no se suaviza
```

---

## Resumen: qué queda libre de re-investigación

| Ya no vale la pena | Por qué |
|---|---|
| ¿Hay ack de invalidate en GFX8? | NR-01, barrido completo |
| ¿Hay granularidad L1/L2? | NR-02, y GFX9+ da el contraste |
| ¿Cuántos `emit_wreg` hace el vm-flush? | RE-07, recountado |
| ¿Cuánto reserva `emit_frame_size`? | RE-06, reejecutado con `pm4dw` |
| ¿`n = payload − 1` es un patrón o una propiedad? | RE-08, 68/68 con discriminante |
| ¿La geometría es 9 bits / 30 bits / 2 MiB? | C-005, refutado y contrastado con el boot |
| ¿Es el writer de PTE una función de CPU? | RE-04, es un paquete SDMA |
| ¿El AVX2 acelera el compresor? | NR-11, no concluyente |
| ¿El cerrojo de ámbito bloquea a la raíz? | NR-10, reproducido |

## Lo que sigue sin resultado (no confundir con "no se buscó")

`NOT_DETERMINED` con causa nombrada en `MASTER-RESEARCH-STATUS §NOT_DETERMINED` N1–N8.
Los cuatro primeros **exigen runtime** y están `BLOCKED_BY_AUTHORIZATION`. Los N3 y N5
exigen la **spec PM4 de GFX8**, que no está en ningún sitio de este repo: no es una
laguna de análisis, es una laguna del corpus, y ninguna cantidad de lectura estática la
cierra.

---

## NR-12 · Las 45 citas de findings sobre ficheros desplazados: de qué árbol copiaron NO es recuperable mecánicamente

```
PROPUESTA  para cada una de las 45 citas `fichero:línea` que viven en findings y caen
           en los cuatro ficheros instrumentados, determinar si su autor copió de
           `working`/`baseline` (prístino) o de `kernelbuild` (instrumentado)
RESULTADO  **NOT_DETERMINED**, y medido, no supuesto
  atribuible a la copia PRÍSTINA      11
  atribuible a la INSTRUMENTADA       1
  EMPATE, no atribuible               33
  sin ambas copias disponibles         0
POR QUÉ  el discriminante mecánico es la prosa de la cita: si el finding nombra un
  símbolo, sólo una de las dos líneas lo tiene.  Y en 33 de 45 la prosa no nombra
  un token que las distinga, porque la mayoría de las citas van en forma de
  `fichero.c:N` con la explicación en otra línea
  una herramienta que en 12 de 45 acierta y en 33 se rinde NO PUEDE usarse para
  arbitrar cuál de dos árboles es el correcto
QUÉ ES ESTO, y por qué importa notwithstanding
  no es un resultado NULL: es la constatación de que la ATRIBUCIÓN no es un problema
  mecánico.  Y eso tiene una consecuencia práctica:
      el arreglo no es automático, es de PROCEDIMIENTO
      cada cita debería registrar el árbol del que se copió, porque el número de línea
      es un hecho relativo al árbol y ahora mismo el árbol es un dato perdido
LO QUE SÍ ES MECÁNICO Y YA ESTÁ HECHO
  el desplazamiento, que no requiere atribución: `--translate` de `citations.py` da
  el delta constante por par de copias, y el delta 0 identifica el par prístino POR
  CONSTRUCCIÓN.  Ver `RE-50`, `TL-40`
  es decir: se puede pasar de cualquier cita a su equivalente en cualquier árbol.  Lo
  que no se puede es decir de dónde copió el autor
```

---

## NR-13 · Las 43 constantes propias no se pueden comparar con el corpus por nombre: cero correspondencias

```
PROPUESTA  comparar cada `RX550_*` de `rx550_pm4.h` contra la constante equivalente
           del driver de referencia, buscando por NOMBRE
RESULTADO  **NOT_DETERMINED**, y la causa es estructural
  constantes propias                                    43
  nombres que existen en el corpus amdgpu                 0
  mismo nombre y mismo valor                             0
  mismo nombre con valor distinto                        0
  el corpus tiene 1125913 constantes distintas y NINGUNA se llama RX550_*
POR QUÉ  el driver propio inventa sus propios nombres.  `RX550_PKT3_NOP` y
  `PACKET3_NOP` son la misma constante con dos nombres, y un corpus de 1125913
  constantes tiene colisiones de sobra para que una búsqueda por nombre no pueda
  encontrar la pareja
  reconocer la pareja exige saber que PKT3 abrevia PACKET3.  Eso es CONOCIMIENTO, y
  un mapeo escrito a mano es la respuesta; un umbral de similitud es una suposición
LO QUE RESUELVE ESA IMPOSIBILIDAD, y es lo que hace constmap.py
  no buscar por nombre, sino por la LÍNEA que la constante ya cita en su comentario:
      RX550_PKT3_NOP = 0x10   declara ser  sid.h:343
      sid.h:343               dice        #define PACKET3_NOP  0x10
  la correspondencia de NOMBRE queda sin verificar, y la de VALOR queda verificada.
  La primera la confirma una persona leyendo los dos nombres juntos, que es un
  segundo y no un análisis
  resultado: AGREE 15 · AGREE_DISCRIMINATING 8 · AGREE_COMMENT 4 · DISAGREE 0
QUÉ NO SE PUDO HACER, y queda dicho
  · emparejar automáticamente los nombres.  Ni por similitud, ni por prefijo: el
    nombre propio y el upstream no se parecen lo bastante
  · decidir la semántica.  AGREE prueba el número, no el significado
  · evaluar las 2 constantes con expresión sin `cpp`
```

---

## NR-14 · El vocabulario cerrado era decorativo: 12 de 51 claims tenían prosa dentro del campo `TYPE`

```
PROPUESTA  que `TYPE` y `STATE` de cada claim sean un único token de la taxonomía
           cerrada de `AGENTS.md`
RESULTADO  **REFUTADO en mi propio registro**, y el defecto era mío
  claims                                            51
  TYPE fuera del vocabulario cerrado                12  (24 %)
  TYPE con un token válido Y prosa detrás             9  de esos 12
  STATE fuera del vocabulario cerrado                 0
CÓMO SE MANIFIESTABA, y no fue un descuido al azar
  `TYPE DERIVATION + NEGATIVE_RESULT`
  `TYPE OBSERVATION, con medición propia`
  `TYPE MEASUREMENT · y el hallazgo de mayor valor de esta ronda`
  `TYPE CONTRADICTION (resuelta)`
  en cada caso la anotación era CIERTA y útil donde estaba, y nadie me dijo que
  dejaba el campo ilegible.  Las doce se escribieron así porque el vocabulario era
  una lista y no un check
POR QUÉ IMPORTA, y no es pedantería
  un campo que lleva prosa es un campo con el que no se puede comparar.  Cualquier
  herramienta que agrupe claims por `TYPE`, o que rechace una claim cuyo `TYPE` no
  esté en el vocabulario, lee las doce como malformadas y no como los tipos que
  son.  Una taxonomía que tolera una segunda frase en su propio campo es una
  taxonomía sin dientes
  y el daño es silencioso en la dirección mala: no da error, da una clasificación
  que nadie cuestiona
LO QUE SE HIZO
  `TYPE` queda con un token y nada más.  La información no se tira, se muda:
      ALSO    los tipos secundarios, que es lo que `+` significaba
      NOTA    la prosa, que es lo que la coma o el punto medio significaban
  y se añadió `docscan.check_taxonomy`, que falla si un `TYPE` o un `STATE` no es
  un token del vocabulario, y también si un token válido lleva prosa detrás
  `STATE` no necesitó nada: ya estaba limpio, y por eso la auditoría encontró una
  clase y no dos
LA REGLA DE `071`, Y MI `drift.py` ERA UNA INSTANCIA SUYA
  `071-el-except-que-devuelve-stub-y-el-flag-que-desactiva-la-auditoria` cuenta cinco
  defectos encadenados de la misma clase, y dice que es la quinta vez que esa clase
  ocurre en este proyecto.  Su defecto 2 es «regex que no admite `/`»
  y el bug que YO cometí en `drift.py` --exigir acentos graves, y con eso no ver
  `tools/docscan.py`-- es exactamente esa: un método de búsqueda que no alcanza,
  usado para afirmar una ausencia. .Reportó 98 sin documentar cuando eran 76
  la regla que `071` propone y que esta auditoría adopta:
      «no existe» sólo es un dato si el índice sobre el que se buscó está
      CONSTRUIDO, y su tamaño se imprime junto al resultado.
      Un `not found` sin cota no es una medida: es un olvido.
  `citations.py` e `ipsolve` ya la cumplían: imprimen el tamaño del índice.  El
  defecto era mío y estaba en la herramienta que había construido precisamente
  para vigilar ese clase de fallo
LO QUE ESTO NO ES
  no es un hallazgo nuevo de hardware.  Es un defecto de mi documentación, y por eso
  la regla que se cerrara aquí y no en un hallazgo
```


## NR-2026-10-02-b · No hay observador de PTE por debugfs en 7.1.3

```
QUÉ SE PROBÓ
  con acceso root, leer las entradas de page table de la GPU
RESULTADO
  `amdgpu_vm_info` existe y devuelve 3168 bytes, pero son una lista de BO
  (tamaño, flags, fences). NO vuelca entradas de PTE. `amdgpu_gart` no
  existe como nodo en este driver
QUÉ ES
  `NOT_AVAILABLE` por esta vía. NO es `PROVEN_ABSENT` en el hardware, ni
  `NOT_FOUND` de la capacidad de la GPU
POR QUÉ IMPORTA LA DIFERENCIA
  la PTE se puede leer de otras maneras: leyendo la memoria de la GPU, o
  forzando al driver a escribir una con un valor conocido. Que aquí no se
  pueda NO significa que no se pueda
CÓMO SE CIERRA
  hace falta un observador que no existe en este driver. La vía estática
  ya está cerrada hasta `value = addr & pte_addr_mask` (EV-20)
```

## NR-2026-10-02-c · `amdgpu_iomem` da EPERM incluso con root

```
QUÉ SE PROBÓ
  `cat /sys/kernel/debug/dri/0000:01:00.0/amdgpu_iomem` como uid 0
RESULTADO
  EPERM. El kernel lo restringe por capability, no por modo del fichero:
  el nodo es `-r--r--r--` y sigue denegado
QUÉ ES
  `NOT_AVAILABLE`. El mapa de MMIO que da este nodo se ha reconstruido
  desde `include/asic_reg/` en su lugar, que además da más: el nombre del
  registro, no solo su rango
```

## NR-2026-10-02-d · Los headers de registro NO están en el directorio de amdgpu

```
QUÉ SE PROBÓ
  buscar `0x3c00` en `drivers/gpu/drm/amd/amdgpu/*.h` esperando
  `gfx_8_1_sh_mask.h`
RESULTADO
  el fichero no está ahí. Está en
  `drivers/gpu/drm/amd/include/asic_reg/gca/gfx_8_1_sh_mask.h`
POR QUÉ SE ESCRIBE
  se estuvo a punto de concluir "no hay registro GFX8 a ese offset", que
  habría sido un `NOT_FOUND` FALSO por lectura parcial. `regs.py` (campos,
  MASK/SHIFT) no cubre direcciones, y no había índice de direcciones
  hasta `dires.py` (587164, 30 ASIC)
REGLA
  los headers de ASIC están en `include/asic_reg/<BLOQUE>/`, ordenados por
  bloque, no junto al `.c` que los usa. Un offset sin resolver no es un
  registro ausente
```

## NR-2026-10-02-e · `0xDEADBEEF` de `WRITE_DATA` es de un test, no del anillo

```
QUÉ SE PROBÓ
  `gfx_v8_0.c:891-894` emite `PACKET3_WRITE_DATA` con valor `0xDEADBEEF`.
  Se buscó ese valor en el anillo GFX capturado
RESULTADO
  cero apariciones en 2051 dwords
QUÉ ES
  ese código es un TEST UNITARIO. El anillo capturado es trabajo real
POR QUÉ SE ESCRIBE
  el patrón de sincronización por valor centinela es real y se usa en
  varios motores (`amdgpu_jpeg.c:207`, `amdgpu_vcn.c:575`), pero en
  ESTE anillo no aparece. Traerlo como si estuviera sería importar un
  dato de un test a una medición
COMO SE USA ESTO
  `pm4dec.py --escribe` lo busca de verdad en cada ejecución y dice que no
  está, con el motivo. No lo da por supuesto en ningún momento
```

## NR-2026-10-02-f · `PKT0` no existe en el driver amdgpu

```
QUÉ SE PROBÓ
  buscar `PKT0` en todo `drivers/gpu/drm/amd/amdgpu/`
RESULTADO
  cero apariciones. El driver escribe registros en el anillo con
  `PACKET3_SET_CONTEXT_REG` (gfx_v8_0.c:1235), `PACKET3_SET_SH_REG`
  (:1529), `PACKET3_SET_UCONFIG_REG` (:850) y `PACKET3_WRITE_DATA` (:891).
  Nunca con la macro `PKT0`
CONSECUENCIA
  un dword tipo 0 en el anillo GFX de GFX8 NO es un `PKT0`. Es payload de
  un `PACKET3` anterior. `pm4dec.py` lo trata como dato de 1 dword
POR QUÉ SE ESCRIBE
  la primera versión de `pm4dec.py` lo leía como cabecera `PKT0` con
  `count=43`, consumía 85 dwords y producía "42 escrituras de registro"
  con direcciones como `0x0000`, que no son registros. Parecía un
  resultado y era la mitad inventado
```

## NR-2026-10-02-g · El sello de evidencia estaba obsoleto al recogerlo, no por daño

```
QUÉ SE PROBÓ
  `docs/EVIDENCE-MANIFEST.sha256` sella 245 ficheros. Al verificarlo con
  sha256sum -c: 25 no coinciden, 0 faltan
RESULTADO
  220 OK · 25 MOVIDO · 0 ROTO
DESCOMPOSICIÓN DE LOS 25
  · 5 son de esta sesión (revkit/*): los toqué yo, y están en commits
    míos identificables
  · 18 son de 06-INGENIERIA-INVERSA/findings/ y tools/, de otras sesiones
    (3c0dd73, 049/050/051)
NINGUNO ROTO
  ningún fichero sellado había desaparecido. Un ROTO obliga a preguntar por
  una pérdida; aquí la respuesta es "no se perdió nada", que es distinta
POR QUÉ ESTABAN MOVIDOS
  el sello lo generó una sesión; después, esa misma sesión y la siguiente
  escribieron 18 ficheros de evidencia. Trabajo legítimo posterior, no daño
LO QUE NO SE HIZO
  NO se re-selló. `sello.py --actualizar` se niega a escribir mientras haya
  MOVIDOS o ROTOS, y explica por qué: re-sellar sin mirar convierte un
  detector de derivas en un detector de cambios, y el sello se actualiza,
  la historia desaparece, y no vuelve a saltarse
DÓNDE ESTÁ EL PROBLEMA REAL
  el manifiesto entró a git por PRIMERA VEZ en d2c4a89, que es un commit
  mío, porque.stageé `docs/` entero. Es decir: se recogió un fichero ya
  obsoleto y se subió como si estuviera al día. Nadie lo verificó al
  recogerlo, porque no había herramienta que lo dijera
LA LECCIÓN
  recoger un manifiesto de integridad sin verificarlo es peor que no
  recogerlo. Aporta una falsa garantía: quien lo lea ve
  "245 ficheros sellados" y no "25 de esos 245 ya no coinciden"
  `sello.py` existe para que eso no vuelva a pasar en silencio
CÓMO SE CIERRA
  decidir, fichero a fichero, si los 25 cambios son legítimos. Si lo son,
  `--actualizar` escribe un sello NUEVO en otro fichero, sin tocar el
  anterior. Ese es el orden correcto: decidir primero, sellar después
```

## NR-2026-10-02-h · `git add docs/` mete 20 ficheros que no son míos

```
QUÉ PASÓ
  al integrar los hallazgos en el estado central, hice `git add docs/`, y
  eso subió 20 ficheros de docs/ que no había tocado yo
POR QUÉ IMPORTA
  el commit queda con una atribución falsa: dice "integra los hallazgos de
  la sesión del debugfs" y en realidad mete además AGENTS-ADDENDA,
  CHANGELOG-RESEARCH, KNOWLEDGE-GRAPH, DECISIONS y 16 más
LO QUE SE DEBE HACER
  stagear fichero a fichero lo que es mío, y dejar lo demás para quien lo
  escribió. `git add <dir>` es cómodo y esconde el alcance
LO QUE SE HIZO EN ESTA OCASION
  se dejó. Deshacer el commit y rehacerlo correctamente habria movido
  trabajo de otras sesiones, que es peor que el alcance de mas. Se
  registra el hecho
CÓMO SE CIERRA
  el fichero EVIDENCE-MANIFEST.sha256 entre esos 20, y queda pendiente
  verificarlo (NR-2026-10-02-g)
```

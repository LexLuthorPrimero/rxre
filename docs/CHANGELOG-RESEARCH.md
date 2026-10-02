# CHANGELOG-RESEARCH — cambios de conocimiento, no de comandos

> Se registra lo que cambia **el estado del proyecto**: conocimiento, clasificación,
> herramienta, contradicción, frontera, dependencia. No cada comando.
> Cada entrada dice `OLD STATE → NEW STATE`, con la evidencia que lo fuerza.
>
> Formato de cada entrada: `DATE · AGENT · ACTION · OBJECT · OLD STATE → NEW STATE ·
> EVIDENCE · DEPENDENCIES · UNLOCKS · RISKS`

---

## 2026-10-01 · agente de documentación · ROUND 1

### R-01 · Reconciliación de la contradicción interna de `PROYECTO_STATUS.md`

```
OBJECT   PROYECTO_STATUS.md líneas 162-189 (limitaciones, próximos pasos, conclusión)
OLD      La cabecera decía "Fase 2 COMPLETA, GPU==CPU 0/4096, 3 corridas" y 30
         líneas más abajo "1. El agreement test NO pasa. 57 de 64 bloques difieren".
         La conclusión decía "Lo que falta es evidencia de ejecución en la RX 550",
         lo cual era falso al escribirse
NEW      Las 4 limitaciones marcadas SUPERSEDED / NOT_RECHECKED / VIGENTE con el
         commit y la hora que las deja obsoletas. Los próximos pasos 1 y 2 tachados
         como SUPERSEDED. La frase de la conclusión tachada. Texto original
         conservado literal bajo cada marca
EVIDENCE git log -S sobre PROYECTO_STATUS.md:
           b8294b1 00:44  se escribe, limitación #1 = NO pasa
           b7ed0c1 01:10  se corrige el push constant, limitación #1 INTACTA
           7ed1eca 01:17  AD-13 -> COMPLETE, la cabecera se actualiza, las
                           limitaciones NO
           49bd550 02:24  se corrige la limitación de spirv-val, las otras siguen
         git blame de las líneas 160-190 -> b8294b1 y b7ed0c1
DEPENDENCIAS  C-001
UNLOCKS  Un agente que lea el fichero ya no puede concluir que el agreement test falla
RISKS    NINGUNO. El texto original sigue ahí. El cambio es una marca, no una Reescritura
RESIDUO  la limitación #3 (rc=0 con [FAIL]) queda NOT_RECHECKED, no resuelta
```

### R-02 · Acotado el bloque de host obsoleto de `README.md`

```
OBJECT   README.md líneas 13-16
OLD      "La instalación validada es Nobara Linux 43, kernel 6.18.2-200.nobara.fc43,
         Mesa 25.3.2 ... en ese host es card2, renderD129 y hwmon1"
NEW      Marcado HISTÓRICO con el host real verificado y enlazado a
         docs/CURRENT-STATE.md. El texto original se conserva
EVIDENCE uname -r        -> 7.1.3-200.nobara.fc44.x86_64
         /etc/os-release -> Nobara Linux 44 (KDE Plasma Desktop Edition)
         glxinfo -B      -> Mesa 26.2.3
         readlink /sys/class/drm/card*/device -> card0=i915 0000:00:02.0,
                                                 card1=amdgpu 0000:01:00.0
         card2 NO EXISTE. renderD129 y hwmon1 sí coinciden
DEPENDENCIAS  —
UNLOCKS  Quien lea el README ya no busca un kernel que no está
RISKS    NINGUNO. Adición pura
```

### R-03 · Creación de `docs/`

```
OBJECT   el árbol documental
OLD      00-INDICE/MASTER-RESEARCH-STATUS.md se autodescribe "punto único de entrada"
         del proyecto, tiene 64 KB, fecha 2026-09-25, versión 2.19, y describe la
         línea de telemetría de septiembre. CERO menciones de rx550_drv, STAGE1,
         vm-invalidate, vmflush, COND_EXEC o GEN_PTEPDE (grep sobre los 64085 B)
         No había EVIDENCE-MATRIX, ni CONTRADICTIONS, ni NEGATIVE-RESULTS, ni
         TOOLS-STATUS, ni CURRENT-STATE operacional
NEW      docs/ con 10 ficheros: MASTER-RESEARCH-STATUS (índice), CURRENT-STATE,
         EVIDENCE-MATRIX, KNOWLEDGE-GRAPH, OPEN-FRONTIERS, CONTRADICTIONS,
         NEGATIVE-RESULTS, TOOLS-STATUS, EXPERIMENTS, IMPLEMENTATION-STATUS,
         DECISIONS, CHANGELOG-RESEARCH
         El de 00-INDICE NO SE BORRA: contiene el histórico R-4B/D6. Queda acotado
         por referencia desde docs/
EVIDENCE  el grep de 0 menciones, arriba. Es la medida, no una impresión
UNLOCKS  Un agente nuevo tiene un índice que responde las 15 preguntas del criterio
         de calidad sin recorrer el árbol
RISKS    UNO, y es real: dos índices competed por el título de "punto único de
         entrada". Se mitiga con una nota de precedencia en el de docs/ y una
         referencia desde el de 00-INDICE. La nota EN 00-INDICE no está hecha: es
         edición de un fichero de otra línea -> acción F7
```

### R-04 · `C-003`: refutación de `block_size = 13`

```
OBJECT   024-page-table-geometria-gfx8.md §2.3, §2.4, §6
OLD      block_size = 13, PAGE_TABLE_BLOCK_SIZE = 4 (0x04000000), PTB = 8192
         entradas, clasificado PROVEN_DERIVED
NEW      Registrado como REFUTED en docs/CONTRADICTIONS.md. El valor vigente es
         block_size = 10, PAGE_TABLE_BLOCK_SIZE = 1 (0x01000000), PTB = 1024
         entradas (8 KiB). 024 NO se editó: el registro es el que lleva la marca
EVIDENCE (a) el código. amdgpu_vm.c:2454 llama amdgpu_vm_get_block_size(tmp), y tmp a
           esa altura es el resultado de tmp = DIV_ROUND_UP(fls64(tmp)-1,9)-1 en la
           línea 2427. Barrido de las 30 líneas: tmp NO se reasigna entre 2427 y 2454.
           get_block_size(2) = 10 ; get_block_size(64) = 13. 024 usa vm_size donde el
           código usa tmp
         (b) el host imprimió "block size is 10-bit" en el boot
         (c) gfx8vmgeom `make test`: 37 aserciones, 0 fallos, y la cadena derivada
           coincide con la observada carácter por carácter
         (d) el commit 2599c65, escrito 5 minutos ANTES que 024, ya decía: "el else
           pasa tmp, no vm_size: get_block_size(2) devuelve 10 donde get_block_size(64)
           habría devuelto 13"
DEPENDENCIAS  RE-10, C-003, C-005, C-006(DRIVER-MISSION-STATE), C-009, 023-pte §5 (misma tabla)
UNLOCKS  El planificador de page tables del driver propio queda con números correctos
RISKS    El texto de 024 sigue diciendo 13 en su §6. Un agente que lea 024 sin llegar
         a CONTRADICTIONS.md se lleva el error. Mitigado por el índice, no resuelto
RESIDUO  024 §5 (saturación) y §8 (UNLOCKS) arrastran el mismo error
```

### R-05 · `C-007`: el índice vigente no describe la línea activa

```
OBJECT   la jerarquía documental
OLD      00-INDICE/MASTER-RESEARCH-STATUS.md se declara entrada única y es parcial
NEW      docs/MASTER-RESEARCH-STATUS.md pasa a ser el índice. El de 00-INDICE queda
         acotado por referencia, sin borrarse
EVIDENCE 0 menciones de los 6 marcadores de la línea A sobre 64085 B
RISKS    la nota en 00-INDICE no está hecha -> acción F7
```

### R-06 · `NR-05`: el mensaje de error de `gfx8vmgeom` nombra la causa equivocada

```
OBJECT   08-ARQUITECTURA/tools/gfx8vmgeom/gfx8vmgeom
OLD      (sin registro: nadie había ejecutado la herramienta desde la raíz del repo)
NEW      Registrado en TOOLS-STATUS.md TL-03 y NEGATIVE-RESULTS.md NR-05
EVIDENCE desde la raíz:  ERROR ... no coincide con el sha256 de 7.1.3  rc=2
         desde su directorio: "corpus cargado", 37 OK, 12/12 negativos  rc=0
         sha256 real de amd_asic_type.h = cea577df…7809 = el que la herramienta espera
         -> lo que fallaba era la RUTA, no el fichero
UNLOCKS  Nadie investigará "corrupción del corpus" a partir de ese mensaje
RISKS    NINGUNO. Documentado; no se editó el README de la herramienta
```

### R-07 · `NR-03`/`NR-04`: `semref` pasó de `VALIDATED` a `INVALID`

```
OBJECT   08-ARQUITECTURA/tools/semref/semref
OLD      registrado como herramienta disponible en herramientas.md
NEW      INVALID. ctags DISPONIBLE, Coccinelle NOT_AVAILABLE. refs -> rc=3.
         El gate exige AMBOS motores, así que no hace nada
EVIDENCE ./semref engines ; ./semref refs <símbolo> ; ./tests/run-bench
         /tmp/opencode/tools no existe
DEPENDENCIAS  NR-09: los findings que la citan (015, P-8) CONSERVAN su valor, porque
            se produjeron cuando funcionaba. Lo que no vale es reejecutarla
UNLOCKS  Se deja de intentar usarla y se sabe que no es "degradada" sino inútil
RISKS    NINGUNO. No se editó nada de esa sesión
```

### R-08 · Verificación de herramientas read-only

```
OBJECT   el estado de las herramientas
OLD      el árbol no tenía un registro de qué herramienta está VALIDATED y cuál no
NEW      TOOLS-STATUS.md con 8 herramientas, contrato, output, exit codes,
         verificación de hoy y los modos de fallo conocidos
EVIDENCE pm4_count_census.py --only=fx8  -> 68 contables, 22 no contables, rc=0
         pm4dw.c compilado con cc -O2 -Wall -Wextra  -> sin warnings, rc=0
           tres invocaciones medidas, incluida la que da STRUCT_NOT_FOUND
         gfx8vmgeom make test -> 37/0/12/12, cruce de versión PROVEN
         validate_rx550_final.py -> rc=0, writes_to_system=false
         semref -> rc=3
UNLOCKS  Un agente sabe qué salida puede usar como evidencia y cuál no
```

### R-09 · `NR-12`: la evidencia de la Fase 2 no está versionada

```
OBJECT   04-IMPLEMENTACION/work/ y la salida del agreement test
OLD      "0 de 4096 en 3 corridas", sostenido por el texto del commit 7ed1eca
NEW      RE-31 = PROVEN por testimony / NOT_RECHECKED. Los .log que registran
         "0 de 16384" en 3 imágenes están IGNORADOS por .gitignore:78. La cifra
         "4005 de 4096 bytes no nulos" no aparece en ningún log persistido
EVIDENCE git ls-files 04-IMPLEMENTACION/work/ -> 0 ficheros
         .gitignore:78 -> 04-IMPLEMENTACION/work/
DEPENDENCIAS  NR-06
UNLOCKS  F6 queda priorizada: no es un detalle de versionado, es pérdida de evidencia
RISKS    Un `git clean -x` borra lo único que sostiene la Fase 2 sin dejar rastro
```

### R-10 · `C-008`: el formato de `owner` no casa con su propio preflight

```
OBJECT   COORDINACION.md §PREFLIGHT §2 y §Adquirir el turno
OLD      sin registrar
NEW      Registrado. El preflight busca `pid=[0-9]+`; el "Adquirir el turno" escribe
         `echo "$$ $(date -Is)"`, que NO contiene ese token
EVIDENCE tres owners coexistiendo con tres formatos:
         .write-lock/owner        52756 … takeover-human; alcance=tools/   NO casa
         .write-lock/findings/owner  PID=53801 …                          casa
         .write-lock/pteflags/owner  54930 … scope=pteflags pid=54930      casa
         El owner de la raíz DESAPARECIÓ durante la ronda: estaba a las 11:01, no
         estaba a las 11:02. Nadie lo borró desde esta sesión, que aún no había
         escrito nada. Sin registro de quién lo liberó
DEPEDENCIAS  NR-10, F10
UNLOCKS  Dos arreglos de un cambio pequeño, ambos pendientes de decisión humana
RISKS    Coincide con el defecto ya demostrado en 021-write-lock §Reproducción
```

### R-11 · GLOBAL DOCUMENTATION SCAN: el árbol se movió cinco veces

```
WHEN      detectado al releer HEAD tras terminar de redactar los doce ficheros
OBSERVADO  HEAD pasó de ce88b5f a 80fbd9e DURANTE el trabajo, y aparecieron siete
           findings nuevos: 024-pm4dw · 025-vm-flush-path · 026-pte-encoding ·
           026-frame-completo · 027-ptba-produccion · 028-fence-completion ·
           029-release-mem
CLASIF     el scan de §22 se dispara y encuentra lo que faltaba
ACCIONES
  TOOLS-STATUS TL-02     reescrito: pm4dw tiene ahora modo --path, y se documenta el
                         defecto que la herramienta destapó en sí misma
                         (LOOKAHEAD_LINES 3 hacía ABSENT una función real)
  NEGATIVE-RESULTS NR-07 SUPERSEDED: write_multiple mide 17 dwords, no 1. Añadidos
                         NR-07b (el defecto del parser) y NR-07c (la reserva son dos
                         sumandos)
  EVIDENCE-MATRIX        siete filas nuevas: RE-14 (63 dw) a RE-22
  KNOWLEDGE-GRAPH §3b,§3c  el camino de envío medido, y el fence como único punto de
                         completion
  OPEN-FRONTIERS F1      marcado PARCIALMENTE CERRADO por RE-18, con lo que sigue
                         abierto explícito
  MASTER-RESEARCH-STATUS filas P15-P22 + aviso de frescura con el rango de commits
  CURRENT-STATE §7       28 -> 35 findings, 4 -> 7 colisiones, 5 -> 9 sin versionar
LO QUE ESTA RONDA NO HIZO, y es la parte disciplinada
  No leyó 026-pte, 027, 028 y 029 enteros. Se registró de su §CUDA y su encabezado,
  que es lo que sostiene cada afirmación de RE-16 a RE-21. Lo que no se leyó no se
  registró: RE-19 dice explícitamente que la otra rama del título de 029 queda por ver
RIESGO RESIDUO  si HEAD se mueve otra vez mientras se lee esto, las filas P15-P22 son
  lo último que queda desactualizado. Están arriba del todo de la tabla PROVEN y
  llevan el nombre del finding
```

### R-12 · Herramienta nueva encontrada y verificada: `pteflags`

```
WHEN      detectado en el GLOBAL SCAN posterior: 08-ARQUITECTURA/tools/pteflags/ con
          ficheros modificados a las 11:55, con mi ronda en curso
OBJECT    una sexta herramienta de análisis, sin documentar en ningún sitio
OLD       no existía en docs/, ni en TOOLS-STATUS, ni en su propio directorio
          (no hay README.md en 08-ARQUITECTURA/tools/pteflags/)
NEW       TL-09 en TOOLS-STATUS, RE-22 en EVIDENCE-MATRIX, dos filas PROVEN (P24, P25)
          en el índice, y NR-05 promovido de "un caso" a "patrón repetido"
VERIFICADO  ./pteflags desde su propio directorio
            aserciones 19 · fallos 0 · controles negativos 5/5 · muertos 0
            RESULT: OK -- y el test puede fallar     EXIT_REAL=0
POR QUE ES VALOROSA, y no solo una herramienta mas
  Cierra la parte de BITS de la frontera A de AGENTS.md ("PTE/PDE -> encoding -> bits
  -> flags"), que hasta ahora estaba como lectura parcial. Y su clasificacion de tres
  estados -- WRITTEN / CLEARED_NOT_SET / OTHER_GEN -- separa cosas que una lectura a
  ojo no separa: no es lo mismo que nadie escriba un bit, que alguien lo borre, y que
  solo lo escriba otra generacion
  PRT (bit 51) pasa de "el driver lo borra" a "nadie lo pone y el unico que lo menciona
  lo borra". Eso convierte RE-05 de una observacion en un censo cerrado
EL CONTRASTE QUE HACE QUE EL CENSO SIGNIFIQUE ALGO
  MTYPE_UC no esta en la TU de gmc_v8_0.c y si en la de gmc_v9_0.c. No es que el codigo
  GFX8 decida no escribirlo: es que el simbolo no existe en su unidad de traduccion,
  luego no podria escribirlo aunque quisiera. Sin ese contraste, "MTYPE no se escribe
  en GFX8" seria NOT_FOUND sin informacion: el nombre no apareceria por la misma razon
  que no aparecen MTYPE_UC. Y ese es el valor del metodo, no del dato
LA HERRAMIENTA PROHIBE AFIRMAR, en su propia salida
  "Que el hardware de GFX8 interprete alguno de estos bits. Este documento afirma QUE
   ESCRIBE EL DRIVER, no que signifique." Es la TERCERA herramienta del proyecto que se
   lo dice a si misma, despues de 017 y de pm4_count_census. La disciplina se esta
   extendiendo por el repo sin que nadie la imponga
LO QUE SE CORREGIO A MI MISMO, en el camino
  Se sospecho que pteflags devolvia rc=0 en el fallo. FALSO: era un "| head" que
  enmascaraba el codigo de salida. Medido con redireccion a fichero y echo $? -> rc=2.
  Es exactamente "Nunca aceptar errors: 0 si el binario no existe", el fallo que
  AGENTS.md prohibe. Se registra porque la almostra de un hallazgo falso es mayor que
  el hallazgo falso
DEPENDENCIAS  RE-22 -> refuerza RE-05 ; cierra parcialmente la frontera A de AGENTS.md
UNLOCKS  El estado de cada bit de PTE con su productor, sin ambiguedad de lectura
RISKS    validado sobre un arbol EN CONSTRUCCION: los ficheros se modificaron a las
  11:55 con mi ronda en curso. Por eso TL-09 dice "VALIDATED a las 12:0x de este dia" y
  no "VALIDATED". Reejecutar si la sesion que lo construye cambia el contrato
LO QUE NO SE HIZO  no se escribio su README.md ni se corrigieron los mensajes de error.
  Son ficheros de otra sesion, que tiene el cerrojo .write-lock/pteflags
```

### R-13 · `FINDINGS-INDEX.md`: el índice que faltaba, y una corroboración

```
WHEN      GLOBAL SCAN: 027-write-multiple apareció a las 12:03 y pasó a ser el octavo
          índice duplicado
OBJECT    (a) el índice de findings  (b) el estado de la herramienta pm4dw
OLD       38 findings sin índice legible, 8 índices duplicados, 9 sin versionar, y
          ninguna forma de saber qué se pierde si se borran
NEW       FINDINGS-INDEX.md: cita por nombre completo, marca TRACKED/UNTRACKED de los
          38, dice qué se pierde con cada uno de los 9, y da los tres comandos que
          reproducen el índice sin este fichero
          TL-02 actualizada: --wm-sites y --struct-size, con su modo de fallo y un
          defecto de documentación propio de la herramienta
          RE-23 nueva: el censo de write_multiple, CORROBORATED
LO QUE NO SE HIZO  renombrar los ocho duplicados. Son ficheros de otras sesiones, y
          renombrar rompe además las referencias CONTINUES= de dentro de los findings.
          Un índice no rompe nada y da lo mismo
LA CORROBORACIÓN, que es el valor técnico de esta ronda
  pm4dw --struct-size, medido con un binario compilado por mí en /tmp desde el fuente
  del árbol (no el binario del árbol, que no está construido para ese flag):
      vi_ce_ib_state              4 miembros  16 B   cnt  6   write_mult  4
      vi_ce_ib_state_chained_ib  10 miembros  40 B   cnt 12   write_mult 10
      vi_de_ib_state             17 miembros  68 B   cnt 19   write_mult 17
      vi_de_ib_state_chained_ib  27 miembros 108 B   cnt 29   write_mult 27
  Y verificado a mano contra el código, que dice
      cnt = (sizeof(payload) >> 2) + 4 - 2
      amdgpu_ring_write_multiple(ring, &payload, cnt - 2)
  con 4 dwords de cabecera (PACKET3 + config + addr lo + addr hi):
      CE_META = 4 + 4  =  8   activo   |   4 + 10 = 14   declarado
      DE_META = 4 + 17 = 21   activo   |   4 + 27 = 31   declarado
  Esas cuatro cifras son exactamente las que 021-frame dedució A MANO el 2026-10-01 a
  las 10:28. Dos métodos independientes, mismo resultado -> CORROBORATED, no duplicado
DEFECTOS NUEVOS REGISTRADOS EN pm4dw
  (a) usage() documenta --macro, --struct y --path. NO documenta --struct-size ni
      --wm-sites, que el parser acepta (pm4dw.c:1080, 1089)
  (b) --struct-size toma UN nombre por flag. La forma con "=" cae en la rama de opción
      desconocida y sale con usage y rc=2. El código lo explica: "un loop codicioso
      'hasta la siguiente opción' se comia los nombres de fichero, porque no empiezan
      por '-'"
  (c) --struct-size necesita el fichero que contiene la DEFINICIÓN entre los .c: el
      parser pasa contenidos, no rutas. Pasarle rutas reportaba NOT_FOUND para una
      struct que existe. Es el mismo patrón de diagnóstico engañoso que NR-05
  Los tres son de documentación, ninguno de lógica. Y (a) son dos líneas
LIMITES QUE DECLARO, porque importan
  - lo medido es el FUENTE, compilado por mí en /tmp. No es el binario del árbol
  - los hallazgos 030 y 031 se registraron sólo desde su §CUDA, declarado dos veces
RESIDUO  las 8 colisiones siguen existiendo. FINDINGS-INDEX las hace citables; no las
  arregla. El arreglo es F10
```

### R-14 · El punto de entrada: `README.md` apunta a `docs/`, y la addenda de `AGENTS.md` queda redactada

```
OBJECT   (a) por dónde entra un agente   (b) qué lee primero
OLD      README.md describía la línea de septiembre y no llevaba puntero a docs/.
          AGENTS.md, que es lo PRIMERO que se lee, tiene una lista "NO reabrir" sin la
          línea A, y dos de sus líneas necesitan matiz o refutación
NEW      (a) README.md abre con un bloque que dice "empieza por docs/, no por el resto de
          este fichero", con los doce ficheros y su propósito en una línea cada uno
          (b) docs/AGENTS-ADDENDA.md: la addenda REDACTADA y VERIFICADA, con el texto
          listo para pegar y una tabla de verificación
LO QUE NO SE HIZO, Y POR QUÉ
  Escribir en AGENTS.md. Está modificado sin commitear desde las 10:24 y no hay cerrojo
  que lo declare. La ausencia de cerrojo NO es permiso: COORDINACION.md:88-90 exige
  /proc/$pid, y el PID que se registra es el del shell que hizo el mkdir, no el del
  proceso agente (NR-10). Y COORDINACION.md:184 es "informa, no arregles"
  Adoptar la addenda es una línea. Esa la pone quien tenga el turno
LO QUE LA ADDENDA APORTA, y no es solo un resumen
  Separa tres cosas que la sección actual mezcla:
    · lo que sigue en pie (verificado contra el árbol: 18 líneas de la lista)
    · DOS que hay que matizar:
        - "amdgpu_vm_map_gart() inalcanzable en esta ruta"  -> es el writer de PTE de
          GPUVM. GART tiene una regla distinta y el error fue tratar la de GPUVM como
          la única. Es la propia palabra de 023-pte §6
        - "FUNCTION(0)=always, trigger NOT_DETERMINED"  -> ya no se pregunta "cuándo
          dispara" sino "qué significa un wait sin predicado", y la respuesta es
          NOT_IMPLEMENTABLE. 017 §5 reformuló la pregunta; 018 la cerró
    · lo que falta, con su RE, que es la línea A entera
  Y añade dos reglas que el repo aprendió por el camino y que no están en ninguna parte:
    · no dar por hecho el cwd de las herramientas de análisis
    · una herramienta que marca NOT_FOUND o ABSENT no ha demostrado que no exista
LA TABLA DE VERIFICACIÓN, que es lo que la hace adoptable
  Cada afirmación de la addenda lleva cómo se comprobó: la línea de código, el sha256,
  el nombre del finding, o el comando. Una addenda sin eso es una nota; con eso es una
  corrección
```

### R-15 · C-009: `block_size` = 10 o 22, zanjado por el kernel en ejecución

```
WHEN      el GLOBAL SCAN encontró `030-page-walker-gfx8-2-niveles.md`, que declara
          CORREGIR la cifra de `block_size` que este árbol sostiene
OBJECT    la cifra que gobierna el tamaño de la page table, el ancho del índice de PTE y
          dónde termina la GART
OLD      RE-10: block_size = 10, num_level = 1, root_level = PDB0
NEW      el finding: "Reporté 13/14/15. Es 22/23/24" y root_level = PDB2
ARBITRAJE, y es el más fuerte que existe
  $ journalctl -k -b --no-pager | grep "vm size is"
  oct 01 05:49:05 kalm kernel: amdgpu 0000:01:00.0: vm size is 64 GB, 2 levels,
                                      block size is 10-bit, fragment size is 9-bit
  El dev_info de amdgpu_vm.c:2463 del kernel QUE ESTÁ CORRIENDO, arrancado HOY. No es un
  log de septiembre: es esta máquina booting ahora
  -> block_size = 10. RE-10 CONFIRMADO, 22/23/24 REFUTADO
POR QUÉ FALLA EL 22, y es el mismo error por tercera vez
  el parámetro de amdgpu_vm_get_block_size se llama `vm_size` pero su uso real son
  PÁGINAS redondeadas a potencia de dos. Eso lo dice el finding, y es cierto
  el error es qué `tmp` hay en la línea 2454:
    el finding alimenta tmp = 2^24 = 16777216  <- roundup_pow_of_two(max_pfn), ANTES de 2427
    el código pasa      tmp = 2               <- DESPUÉS de tmp = DIV_ROUND_UP(fls64-1,9)-1
    get_block_size(2^24): bits=42, >8 -> 22
    get_block_size(2)  : bits=19, <=8 -> 10
  Verificado en LOS DOS corpus: 7.1.3 y 7.2.8 tienen la secuencia idéntica, y tmp no se
  reasigna entre 2424 y 2454
LA SEGUNDA AFIRMACIÓN TAMBIÉN CAE
  root_level = PDB2 para num_level = 1. El switch dice case 1 -> PDB0, y el enum lo
  confirma: { PDB3=0, PDB2=1, PDB1=2, PDB0=3, PTB=4 } (amdgpu_vm.h:191-197). Para PDB2
  haría falta num_level = 3
LO QUE DEL FINDING SÍ SOBREVIVE, y se separa explícitamente
  RE-28: antes de GMC v9 el driver se NIEGA a usar un nivel no-hoja como hoja
    (amdgpu_vm_pt.c:825-832 en 7.2.8, :840 en 7.1.3, bien citado para su corpus).
    PAGE_TABLE_BLOCK_SIZE existe en el registro pero NO se usa como tamaño de bloque.
    Eso recorta el espacio de diseño del driver propio: no puede implementar huge pages
  Y el título del finding es correcto: el walk es de 2 niveles, PDB + PTB. Lo que cambia
  es la aritmética, no la topología
LA CRONOLOGÍA, QUE ES LO QUE HAY QUE APRENDER
    13/14/15   019 y 024      -> feed de vm_size          -> corregido, TIPO A
    22/23/24   030-page-walker -> feed de tmp pre-2427    -> REFUTADO HOY, TIPO B
    10         gfx8vmgeom      -> feed de tmp post-2427   -> CORRECTO
  Los tres leen la MISMA función. Dos se equivocan de argumento y uno no. La diferencia
  entre el bueno y los dos malos no es el análisis: es que la cadena se comprobó contra la
  línea que el hardware imprimió. gfx8vmgeom lo dice en su propia salida ("el contraste
  con el host") y por eso su número sobrevivió a DOS intentos de corrección posteriores
LO QUE SE HACE  C-009 en CONTRADICTIONS.md con las dos versiones, la cadena y el arbitraje.
  RE-10 sube de confianza con la cita del kernel en ejecución. RE-28 recoge la parte que
  sobrevive del finding, separada de la que no. FINDINGS-INDEX marca 030-page-walker como
  refutado en este punto
LO QUE NO SE HACE  editar 030-page-walker. Es UNTRACKED y de otra sesión.
  COORDINACION.md:184 es "informa, no arregles"
```

### R-16 · C-010: la afirmación que se cae es de este trabajo

```
WHEN      el GLOBAL SCAN encontró `033-pm4-spec-gfx8-no-existe-y-el-encuadre.md`
OBJECT    el ESTADO DE BLOQUEO de tres fronteras, y una frontera entera que no estaba
          registrada
OLD      docs/OPEN-FRONTIERS.md, escrito por mí a las 12:40, decía en F2b, F3 y en la
          tabla de NOT_DETERMINED:
            "BLOQUEOS: BLOCKED_BY_CORPUS — falta la especificación. No es una laguna de
             análisis: evidence_search.py con --expect declarado es la vía, y ya se usó;
             la fuente no está en este repo"
NEW      033-pm4-spec, con RESOLVES= el BLOCKED de 022/023/029:
            la fuente existe, es accesible, tiene 637 páginas, y se CONTÓ que no contiene
            NADA de PM4. Cero apariciones de PACKET3, PKT3, RELEASE_MEM, COND_EXEC,
            VM_INVALIDATE, INT_SEL, WRITE_AT, GRBM, mmCP
            Documento: Reference Guide — Graphics Core Next Architecture, Generation 3,
            rev. 1.0 (2015-03). AMD nunca publicó el framing PM4 para GCN3
CLASIF DE LA FUENTE  PRIMARY_DOCUMENTATION, y el resultado es NEGATIVE_RESULT
POR QUÉ EL ERROR ERA MÍO, y no del árbol
  Escribí "falta la especificación... la fuente no está en este repo" y lo presenté como
  una limitación del CORPUS. La confundí con el árbol de fuentes local. La especificación
  es un documento EXTERNO, y no estaba en el repo porque no está en ninguna parte: no
  es que esté fuera, es que AMD no la escribió
  Es el mismo error que el repo ya cometió cuatro veces, en otra forma: declarar una
  AUSENCIA sin haber buscado el universo correcto. evidence_search.py busca en el árbol;
  la spec estaba en docs.amd.com
ALCANCE  F2b · F3 · N1 · N3 · N5, más una frontera que no tenía: F3c
ACCIONES
  C-010 en CONTRADICTIONS.md, con MI afirmación y su fecha. Es la segunda vez en esta
    ronda que se registra una contradicción donde el perdedor es un documento de docs/
  F2b, F3 y la tabla de NOT_DETERMINED  ->  BLOCKED_BY_NEGATIVE_RESULT
  F3c creada: los payloads de COND_EXEC, RELEASE_MEM, VM_INVALIDATE_RESPONSE e
    INT_SEL=2. Con el experimento ya diseñado en 022 §5, y la observación de que comparte
    bloqueo con F1 y puede ir en la MISMA submission
  RE-29 · RE-30 · RE-31 en EVIDENCE-MATRIX
LO QUE APORTA EL ENCONTRADO, más allá del bloqueo
  · RE-30 CIERRA una ambigüedad que RE-08 dejaba abierta: de QUÉ se resta el 1.
    La fórmula es F = datos − 1, paquete = F + 2 dwords. Es decir, n se cuenta sobre el
    TOTAL, no sobre los datos. Tres casos del corpus: WAIT_REG_MEM en :6047, :6180,
    :6199, todos con F=5 y exactamente 6 datos
  · RE-31 REFUTA una aserción de freedreno con un contraejemplo vivo:
    pkt_is_type3 exige opcode < 0x80, y hay 12 de 74 opcodes PACKET3 >= 0x80. Once con
    cero usos; el superviviente es SWITCH_BUFFER (0x8B), con 13 usos
    Y el filtro que hace el hallazgo valer está explícito: que un opcode esté DEFINIDO no
    es que se EMITA. Sin ese filtro la contradicción sería vacua. Es exactamente el
    control que 021-write-lock propuso y que COORDINACION.md no aplicó, aplicado aquí a
    un caso distinto
  · El propio hallazgo registra su propio error de método: un barrido sin distinguir
    "opcode" de "offset de registro" produjo 12 falsos positivos que CASI invalidaban la
    predicción. Los *_START / *_END de los SET_*_REG son offsets. Es el mismo error que
    en su día dejó a 019 en NOT_FOUND durante horas, y aquí se detectó ANTES de concluir
LO QUE ESTO AHORRA  buscar una especificación que no existe. Eso es exactamente lo que
  un agente habría hecho con lo que yo tenía escrito
```

### R-17 · C-011: un número mal documentado llegó hasta la instrucción de máquina

```
WHEN      GLOBAL SCAN: 035 (corrige a 023), 036 (lo implementa), 045, 046 (corrige a
          040-045) aparecieron entre las 12:5x y las 13:0x
OBJECT    el emisor de PTE del driver propio, y el encuadre entero de la línea H
LO MÁS IMPORTANTE PRIMERO
```

```
C-011 · el emisor de PTE
  CLAIM_A  035: "023 leyó el fichero equivocado. El fichero del ASIC de este proyecto es
          sdma_v4_0.c", con  count - 1  en el último dword. 036 lo puso en el driver:
            rx550_pm4.c:277   ib->buf[ib->length_dw++] = count - 1;
            rx550_pm4.h:195   #define RX550_SDMA_PTEPDE_DW 10  /* sdma_v4_0.c */
          Y lo Justifica: "un driver propio que copie 023 escribiría count donde el
          hardware de este ASIC espera count - 1, y programaría una entrada de más"
  CLAIM_B  la ruta de descubrimiento, leída entera del corpus
            vi.c:2107-2113        case CHIP_POLARIS12: sdma_v3_1_ip_block
            sdma_v3_0.c:1693-1700 .funcs = &sdma_v3_0_ip_funcs
            sdma_v3_0.c:1112      amdgpu_sdma_set_vm_pte_scheds(adev, &sdma_v3_0_vm_pte_funcs)
            sdma_v3_0.c:996       ib->ptr[...] = count;      <-- SIN el menos uno
  ARBITRAJE  el mismo que zanjó C-009: preguntarle a la máquina
            oct 01 05:49:05 amdgpu 0000:01:00.0: detected ip block number 4
                                    <sdma_v3_1_0> (sdma_v3_0)
            y el formato se decodifica (amdgpu_ip.c:241-245):
              "<%s_v%d_%d_%d> (%s)"  ->  tipo sdma, 3.1.0, funcs->name sdma_v3_0
  RESOLUCIÓN  CLAIM_B. Este ASIC escribe count
POR QUÉ 035 CAYÓ, que es más interesante que que cayera
  Buscó el fichero de SDMA de Polaris12 POR NOMBRE. No hay uno propio: el ASIC usa
  sdma_v3_0.c. Cuando eso no aparece, la conclusión natural —y la falsa— es que el fichero
  leído es de otra generación
  sdma_v3_1_ip_block NO tiene fichero. No existe sdma_v3_1.c en 7.1.3 ni en 7.2.8. Es un
  alias declarado en sdma_v3_0.c:1693
  Un barrido por NOMBRE ve sdma_v3_0.c y no ve nada raro. Un barrido por BLOQUE DE IP ve
  sdma_v3_1 y concluye que hay un emisor nuevo. Los dos barridos están bien hechos y dan
  respuestas opuestas
  La regla que faltaba: TRACE_GATE_BEFORE_ABSENCE_INFERENCE. Un identificador ausente en
  un barrido hay que seguirlo hasta su declaración antes de tratarlo como entidad nueva
LO QUE 035 ACIERTA, y no se tira
  · la off-by-one es REAL y la diferencia entre los dos emisores también. Sólo cambia a
    cuál pertenece ESTE ASIC
  · el total de 10 dwords: correcto en ambos
  · 035 corrió la fuente equivocada pero corrió la cadena correcta
POR QUÉ 75 CHECKS VERDES NO LO ATRAPAN, que es lo transferible
  La suite lee RX550_SDMA_PTEPDE_DW del MISMO header que el .c. Eso es coherencia, no
  validación: sólo confirma que el .c usa el .h. 036 declara 5 mutaciones detectadas y
  ninguna puede ser esta
  Un control negativo contra el emisor del driver de REFERENCIA, carácter a carácter
  sobre los dos últimos dwords, lo habría atrapado. Un control contra la propia constante
  no puede
ACCIONES
  C-011 con las dos versiones, la cadena y el arbitraje
  RE-32 (el bloque activo y el alias) · RE-33 (los dos emisores, la diferencia de 1 dword)
  P37 · IMPLEMENTATION-STATUS §2.1, con las cinco líneas citadas del código
  F3d creada y PUESTA PRIMERA en la tabla de valor. No por valor científico: por urgencia
    de daño ya presente
```

```
LO SEGUNDO · la línea H se reencuadró entera
  046 (CLASSIFICATION=CONTRADICTION) corrige 040, 041, 042, 043, 044 y 045.
  045 se cerró declarando "la cadena completa del reloj", y no comprobó qué
  implementación de DPM compila para Polaris12

  ERROR CONCRETO   legacy-dpm/Makefile:28  si_dpm.o si_smc.o SOLO bajo
                   CONFIG_DRM_AMDGPU_SI. Kconfig:42-51 dice de SI: "first generation GCN"
                   Polaris12 es Volcanic Islands. Y DRM_AMDGPU_VI NO EXISTE como config
                   -> SI_DPM_COMPILED_FOR_POLARIS12 = PROVEN_ABSENT, y no es un negativo
                      por búsqueda: es el gate de compilación explícito
  RUTA REAL        hwmgr.c:154-158  POLARIS11/10/12 -> polaris10_smu_funcs
                   hwmgr.c:122       smu7_init_function_pointers
                   polaris10_smumgr.c:664/691/716  populate_smc_{mvdd,vddc,vddci}_table
  MEDICIÓN         smu7_hwmgr.c  calculate_at 0 · calculate_u_and_p 0 · bsp 0 ·
                   ClockVoltageDependency 0 · xclk 1 (para TIMING DE DISPLAY, no PLL)
  SOBREVIVE        el CONCEPTO de 040 (el reloj es un mensaje al firmware, no un
                   registro), reubicado en smu7_send_msg_to_smc_offset. Y la regla de
                   diseño de 045 sobre centinela y poll con predicto
  LA REGLA NUEVA   COMPILE_GATE_BEFORE_TRACE_GATE
                   verificar en el Makefile y el Kconfig que el .c SE COMPILA para el ASIC
                   ANTES de gastar N hallazgos en él
                   "Trazar un fichero correcto, con toda la evidencia correcta, sobre un
                   fichero que no entra en el build produce documentos internamente
                   consistentes y operacionalmente inútiles"
  ACCIONES         P38 · F3b reencuadrada con su tabla de qué sobrevive y qué no ·
                   RE-27 degradada de "ruta activa" a "concepto vivo, función distinta"
  Y LA REGLA ES GENERALIZABLE, y ese es el valor de esta ronda
                   C-011 y 046 son el MISMO error en dos sitios distintos:
                     uno confunde qué código corre en el ASIC
                     el otro confunde qué código se compila para el ASIC
                   Los dos se resuelven con una comprobación de una línea, y los dos
                   cuestan caro: uno casi llegó a memoria corrupta
```

### R-18 · Tres hallazgos que se confirman entre ellos, y la medición del coste de citar sin versionar

```
WHEN      033-mmu-vm-no-publicado, 035-block-size, 037, 038, 051 aparecieron entre 13:0x
          y 13:2x
LO QUE REGISTRO, y el orden es por valor
```

```
1. RE-37 · LA CIRCULARIDAD, CONFIRMADA DESDE DENTRO
  038 dice, textual: "036 y 037 declararon una circularidad: el codificador se escribió
  leyendo amdgpu, y las expectativas del test se transcribieron del MISMO amdgpu, así que
  un error de lectura replicado en los dos sitios pasa las 147 comprobaciones. 035 es
  exactamente eso, sucedido."
  Es EXACTAMENTE lo que C-011 registraba, pero dicho por el propio autor del código y en
  su propia terminología. Dos observaciones independientes llegaron al mismo diagnóstico
  por caminos distintos. C-011 pasa de "mi lectura" a hallazgo del propio proyecto
  Y declara su salida por escrito: "ya se sabe que acepta uno: count en vez de count-1"
  El validador rompe la circularidad ESTRUCTURAL; la de C-011 es de VALOR. Dos niveles
  Y explica por qué una regla de PACKET3 no alcanza a PTEPDE: para sDMA la longitud es
  IMPLÍCITA EN EL OPCODE, no en un campo count. Es la razón estructural del error de 035
  Y corrora RE-30 por vía independiente: `count = payload − 1`, total = `count + 2`, en
  siete de siete paquetes. RE-30 lo derivaba de tres WAIT_REG_MEM leídos enteros.
  Dos métodos, mismo número -> CORROBORATED
```

```
2. RE-34 · EL BLOQUE MMU/VM NO ESTÁ PUBLICADO
  El índice oficial de arquitectura de AMD enumera 14 documentos: 13 ISA de shader, 1 de
  firmware de scheduler. Ninguno trata MMU, TLB, page walker, formato de PTE ni orden de
  invalidación
  Y no es descuido de indexado. El propósito que AMD declara para un ISA es textual:
  "Provide a reference of instruction operation that COMPILER WRITERS can use"
  Compiladores, no sistemas de traducción de direcciones. La ausencia es estructural
  RECLASIFICA tres NOT_DETERMINED a NOT_PUBLISHED. `NOT_PUBLISHED` es más fuerte que
  `NOT_DETERMINED`: no es "no lo hemos leído", es "no existe"
  JUNTO CON RE-29, los dos son la misma clase, y juntos dicen algo más fuerte que dos
  fronteras bloqueadas: la CLASE de documento que este proyecto necesita no es la clase de
  documento que AMD publica. Eso es una restricción estructural, no una frontera.
  Y una restricción se acepta o se mide; una frontera bloqueada se puede desbloquear
  Corrección a mi propia clasificación, ya registrada en C-010: yo decía
  BLOCKED_BY_CORPUS por falta de búsqueda. Era ausencia en el universo equivocado
```

```
3. RE-36, P40, P41 · EL NOMBRE DEL ip_block NO PREDICE EL FICHERO, TERCER CASO
  051 lo dice textual: "el nombre del ip_block en el log NO PREDICE el nombre del
  fichero. Hubo que localizarlo por el símbolo"
  Y encuentra que <ih_v3_0_0> (tonga_ih) no tiene ih_v3_0.c. El bloque real es
  tonga_ih.c:503
  Es el TERCER caso de la misma forma, y ninguno se knew de los otros dos:
      <sdma_v3_1_0> (sdma_v3_0)   no hay sdma_v3_1.c   -> C-011
      <ih_v3_0_0>   (tonga_ih)    no hay ih_v3_0.c     -> RE-36
      <gmc_v8_1_0>  (gmc_v8_0)    otra generación      -> (gmc sí existe, pero distinto)
  LA REGLA, que este árbol debería adoptar formalmente:
      el nombre del ip_block del log es un NÚMERO DE VERSIÓN, no un nombre de fichero
      para localizar el código hay que seguir `.funcs`, que es un símbolo
  Y el dato técnico: el IV son 16 bytes, 4 dwords, con PASID de 16 bits en dw2[31:16] —
  el ÚNICO sitio del hardware donde se reporta un PASID. client_id NO es un campo del
  vector: se fija a AMDGPU_IRQ_CLIENTID_LEGACY
  051 además ejecuta control de duplicación ANTES de derivar, y reporta que sus 4 hits
  iniciales eran `\bIH` matcheando dentro de otras palabras. Con `\bIH\b`, cero. El
  mismo tipo de error que en su día tuvo a 019 en NOT_FOUND durante horas, detectado antes
```

```
4. RE-38 · LO QUE NO REGISTRO COMO HALLAZGO PERO SÍ COMO MEDICIÓN
  El §Evidencia de 038 cita tools/rx550pm4val.c con 850 líneas y sha256 e9c7508b…a115
  Medido:
    ~13:15:5x  (yo)   928 líneas   sha dccddf5b…
    13:16:46   mtime  1018 líneas  sha 47168d22…
    13:18:40   (yo)   1018 líneas  sha 47168d22…   estable, tres tomas a 20 s
  Dos ediciones en ~6 minutos DESPUÉS de que el hallazgo publicara su hash. +168 líneas,
  +20 %. Y el fichero es UNTRACKED: la versión de 850 líneas es irrecuperable
  Y 07-DRIVER/tests/rx550_pm4_emit.c, declarado con 127 líneas, NO EXISTE en el disco
  cuando lo mido. Existe el directorio y el binario compilado. NOT_DETERMINED por qué
  ESTO NO ES UNA QUEJA SOBRE 038
  038 es el hallazgo mejor construido de esta mañana: declara su circularidad, la rompe, y
  declara su propia salida. Su único defecto es que su formato de evidencia es la
  convención del repo, y esa convención no se sostiene en un artefacto que se reescribe
  LO QUE SE REGISTRA COMO REGLA, y es lo transferible
    evidencia durable = (fichero versionado + línea) o (fichero versionado + hash del
    commit)
    un hash sobre un fichero sin versionar NO es evidencia: es una cifra que caduca
    Las dos se leen igual en un bloque §Evidencia, y esa es la trampa
  Y ESTO MIDE F7, que llevaba tres rondas declarado como defecto abstracto. Ahora tiene
  un número: en este árbol, una cita de evidencia sin versionar dura minutos
```

```
LO QUE ESTO CAMBIA EN EL ESTADO GLOBAL
  · el hallazgo 035-block-size CORROBORA C-009 por el mismo árbitro (el log del host), y
    dice que lo encontró con el método que este árbol documentaba desde C-009. Es la
    señal de que la disciplina se propaga sola, sin que nadie la imponga
  · tres contradicciones registradas, dos de ellas con la afirmación perdedora siendo de
    este trabajo o del código de otra sesión, y las tres resueltas por arbitraje de la
    máquina y no por argumentación
  · y una restricción estructural que no se desbloquea: AMD no publica la clase de
    documento que este proyecto necesita
LIMITE DECLARADO  de 038 sólo se registró el §CUDA y §1-§2. No he ejecutado
  rx550pm4val.c ni `make -C tests crosscheck`: los 181 checks y el 12/12 son TESTIMONY
  De 051 sólo se registró el §CUDA y §1-§2: el overflow, el teardown LIFO y el
  ENABLE_L2_CACHE quedan sin verificar aquí
  De 035-block-size sólo §CUDA y §1
```

### R-19 · Dos herramientas nuevas, construidas porque la evidencia demostró que faltaban

```
WHEN      el usuario pidió explícitamente que cree las herramientas que falten, y
          que las anote
OBJECT    (a) el gate que habría cerrado C-011 antes de que 036 escribiera código
          (b) la ronda de documentación, que se reescribía a mano cada vez
AMBIGÜEDAD QUE RESOLVÍ YO, y la declaro
  "si ves que tus compañeros necesitan herramientas, créalas" podría leerse como
  permiso para invadir el trabajo técnico de otras sesiones. NO lo tomé así. Las dos
  herramientas que construí resuelven preguntas que YO me hacía en cada ronda, en
  territory que es mío, y ninguna toca implementación ni la GPU. Si alguna vez hace
  falta una herramienta que sí sea de implementación, se declara y se pide
```

```
1. tools/ipsolve.py  — TL-11, RE-41.  EL GATE QUE FALTABA
  El hueco estaba declarado en RE-39: asic_resolver contesta "¿compila?" y su
  grep -c ip_block da 0. Faltaba "¿qué código CORRE?", que es un puntero .funcs a
  través de un const struct declarado en otro fichero
  RESULTADO  --selftest 12/12, rc=0
             --bootlog contra el kernel  9 de 9 bloques, rc=0, ~25 s
             --expect es puerta de CI: rc=0 si acierta, rc=4 si no, rc=3 si no resuelve
  LO QUE CONFIRMÓ MECÁNICAMENTE
    C-011  el ASIC usa sdma_v3_0, no sdma_v4_0. Con un comando, no con un argumento
    051    tonga_ih_ip_block -> tonga_ih.c; no existe ih_v3_0.c
    046    pp_smu_ip_block -> pm/powerplay/amd_powerplay.c, la ruta PowerPlay
  LO QUE DESCUBRIÓ Y NO ESTABA DOCUMENTADO
    el bloque de display es dm_ip_block, y sus funcs en display/amdgpu_dm/amdgpu_dm.c
    sólo alcanzable bajo CONFIG_DRM_AMD_DC y has_dc_support, así que DisplayCore está
    COMPILADO y ACTIVO en este host. Y en el caso VI de vi.c no hay rama `else` para
    dce_v10_0, a diferencia del caso TONGA: si DC no estuviera soportado, esta tarjeta
    no tendría NINGÚN bloque de display
  SIETE DEFECTOS QUE ENCONTRÓ EN SÍ MISMA, que es lo que demuestra que el self-test sirve
    · la regex de campos no aceptaba el `&` del puntero -> todo salía NO_FUNCS_FIELD
    · la contabilidad del test daba por bueno un resultado que no era
    · NO MANEJABA EL FALL-THROUGH DE C, que es justo el patrón de vi.c:2107 y
      hwmgr.c:154-158. Eso lo hacía inútil para el caso que la motiva. Ahora lo maneja,
      con un control negativo que comprueba que la etiqueta final de una cadena de
      fall-through no hereda el bloque del que cae
    · atribuía al caso un `if` del caso ANTERIOR: reportaba
      `vi.c:2113 inside if (!amdgpu_sriov_vf(adev))` para Polaris12, y ese `if` es el
      del caso TONGA, que termina con break en 2104. Un guard falso es PEOR que ninguno
    · exigía que el símbolo de funcs terminara en `_ip_funcs`, y `amdgpu_dm_funcs` no
      lo hace: NOT_DECLARED FALSO en el bloque de display. Es C-011 invertido: allí la
      convención sugería un fichero inexistente, aquí ocultaba una struct existente
    · indexaba por el sufijo del enum y SMC se imprime como "smu". Ahora lee la tabla
    · --json imprimía texto humano detrás del JSON, que lo hacía inanalizable
  RENDIMIENTO  medido tres veces mal: 27 s (una pasada) · 3 m 20 s (por símbolo) ·
    1 m 16 s (alternancia). Una versión con grupos anidados hizo el self-test pasar de
    60 s. Lo simple y lo rápido ganaron; ese orden es la lección
```

```
2. tools/docscan.py  — TL-12, RE-42.  LA RONDA COMO COMANDO
  MOTIVACIÓN  estas mismas comprobaciones las reescribía a mano al empezar cada ronda.
  Una comprobación que cambia de forma entre rondas no es una comprobación: es un hábito
  RESULTADO  --selftest 12/12, rc=0
             --repo . -> defect 0 · stale 3 · review 9, rc=0
             --sync reescribe 2 campos y una segunda pasada es no-op
  Y ENCONTRÓ UN ERROR MÍO DE INMEDIATO, que es la prueba de que hacía falta
    Escribiendo a mano el equivalente a la corrección de contadores hice
    `cd docs && git ls-files` en vez de `git -C <repo> ls-files`. git ls-files imprime
    rutas relativas al directorio actual, así que desde docs/ no casaba nada, la
    conclusión fue "0 de 88 versionados", y ESA CIFRA FALSA quedó escrita en
    CURRENT-STATE.md. Realidad: 38 versionados, 50 sin versionar
    Lo más peligroso de un número falso es que suena urgente: invita a actuar sobre algo
    que no está pasando
    De ahí sale --sync: medir y corregir en el mismo sitio, informar cada sustitución,
    y ser IDEMPOTENTE. La idempotencia se escribió porque la primera versión no lo era:
    actualizaba `TRACKED 31 de 0` y dejaba el denominador, y `31 de 0` es PEOR que
    `0 de 0` porque parece medido
  Y LA MEDICIÓN DE "SIN VERSIONAR" TAMBIÉN ERA FALSA, dentro de la herramienta
    usaba `git ls-files --error-unmatch`, que sale distinto si CUALQUIERA de los paths
    no está versionado. Un directorio medio versionado devuelve vacío y la herramienta
    reports todos como sin versionar. Medido: decía "87 sin versionar" con 38
    versionados. Una medición que da el número asustador es peor que no medir
  DISEÑO QUE IMPONE UN LÍMITE, Y ES EL QUE MÁS COSTÓ
    los 9 ítems de review que quedan son CORRECTOS: `sdma_v3_1.c` e `ih_v3_0.c` se
    citan precisamente porque NO existen, que es el contenido de C-011 y RE-36. Una
    herramienta que exigiera resolverlos induciría a borrar la afirmación central de
    esas dos entradas. Se dejan como están y se registra que son intencionados
  Y EL GRIEGO
    la primera versión marcó como defecto EXPERIMENTS.md:232, que dice
    `10 corridas pareadas, ΔFPS=0`. Eso es notación, no corrupción. Un escáner que
    llora lobo sobre notación correcta queda ignorado el día que acierta
```

```
LO QUE ESTAS DOS HERRAMIENTAS NO SON
  ninguna de las dos toca la GPU, lee MMIO, abre /sys o compila nada.  Son análisis
  estático y lectura, que es exactamente lo permitido
  y ninguna compite con el trabajo de otra sesión: no editan findings/, ni 07-DRIVER,
  ni 04-IMPLEMENTACION
POR QUÉ HACE FALTA MÁS DE UNA
  pm4_count_census.py  cuenta sobre el corpus           · falla en silencio con el cwd
  rx550pm4val.c        estructura de un IB, sin corpus  · declara su propia salida
  asic_resolver.py     ¿esto COMPILA para mi ASIC?      · no toca el hardware
  ipsolve.py           ¿esto CORRE en mi ASIC?           · sigue el puntero .funcs
  docscan.py           ¿esto está COHERENTE?            · sólo lee docs/
  Las cinco responden a preguntas distintas y ninguna habría detectado a las otras
  cuatro. Por eso hacen falta las cinco, y por eso una sola no protege de nada
LO QUE NO SE HIZO, y por qué
  no se editó `rx550_pm4.c:277`, que seguía con `count - 1` cuando el ASIC esperaba
  `count`.  Es implementación viva de otra sesión, con su cerrojo, y
  COORDINACION.md:184 es "informa, no arregles".
  >> **Anotado 2026-10-02**: el defecto ya no está.  `rx550_pm4.c:298` escribe
  >> `count` y la función replica `sdma_v3_0.c` dword a dword, medido en `RE-52`.  Esta
  >> entrada se conserva sin reescribir porque describes lo que era cierto el día que
  >> se escribió, y el retraso es el dato: nadie lo vio durante horas con la suite en
  >> verde.  ipsolve lo que sí hace es convertir
  esa corrección en una línea de CI que cualquiera puede correr:
      ipsolve.py --chip CHIP_POLARIS12 --block sdma_v3_1_ip_block --expect sdma_v3_0.c
```

### R-20 · `toolreg`, y el hallazgo que ningún registro iba a encontrar

```
WHEN      el usuario pidió crear herramientas para automatizar la investigación
OBJECT    (a) no duplicar el trabajo de otras sesiones   (b) el catálogo de herramientas
AMBIGÜEDAD QUE RESOLVÍ YO, y la declaro porque es una interpretación de permisos
  "si ves que tus compañeros necesitan herramientas, créalas" podría leerse como permiso
  para invadir el trabajo técnico de otras sesiones. NO lo tomé así.  Decidí el alcance
  así:
    · construyo herramientas que resuelven preguntas que YO me hago en cada ronda
    · todas son análisis estático y lectura: nada de MMIO, sysfs, módulos ni runtime
    · ninguna edita findings/, ni 07-DRIVER, ni 04-IMPLEMENTACION, ni código ajeno
    · si alguna vez hiciera falta una herramienta que SÍ sea de implementación, se declara
      y se pide, en vez de hacerse
  Y el resultado apoyó la decisión: 13 herramientas nuevas aparecieron en la misma tarde,
  de otros autores.  La necesidad era real y ya estaba cubierta
```

```
LO PRIMERO, Y ES LO QUE IMPORTABA: NO DUPLICAR
  el primer impulso era construir el gate de ip_block, un decodificador PM4, un
  trazador de llamadas y un orquestador.  Antes de escribir nada inventarié tools/, y
  estaban YA HECHOS y por otras sesiones:
    reg_resolve · reg_census · regtable_audit · struct_layout · xref (por AST de clang)
    trace_path (con veredicto vivo/muerto) · which_hw · vmid_map · cap_census
    msg_census · contradict · toolcheck · citegen · audit_citations · oracle
    y después pipeline.py, que ya encadena las herramientas y produce el mapa causal con
    procedencia por nodo, o sea exactamente lo que yo iba a construir
  Mi conclusión de diseño pasó a ser: NO lo que falta, sino el CATÁLOGO.  tools/ no tenía
  índice, y eso es el problema de FINDINGS-INDEX aplicado a herramientas
```

```
LO QUE CONSTRUÍ, y por qué es este y no otro
  tools/toolreg.py  ·  TL-13  ·  RE-44  ·  self-test 9/9
  Inventaría las herramientas, ejecuta el self-test de cada una, y CRUZA el inventario
  con TOOLS-STATUS.md en las DOS direcciones:
    · una herramienta que existe y no está documentada
    · una entrada TL que nombra una herramienta que no existe
  Más un INTERLOCK: se niega a ejecutar una herramienta que no declare su ámbito, porque
  ejecutar código de otras sesiones en un árbol con cinco sesiones es exactamente donde
  una operación prohibido se ejecuta por descuido
```

```
LO QUE ENCONTRÓ, y es lo que justifica la herramienta
  · 44 herramientas fuente en DOS directorios, NO 26 en uno.  pm4_count_census,
    count_vmflush_dw y frame_budget se mudaron a 08-ARQUITECTURA/tools y el registro las
    reportaba como «TL que nombra una herramienta inexistente»: acusar una pérdida donde
    sólo hubo una mudanza, que es el peor de los dos errores posibles
  · dos convenciones de contrato distintas (WORK_CLASS= frente a # CONTRACT:), y mi
    primera versión reportaba «13 sin declarar» cuando era otra ortografía
  · 5 herramientas que NO CITA NINGÚN HALLAZGO: su salida no consta en ninguna parte.  O
    no se usaron, o se usaron y nadie escribió el resultado, y desde el árbol las dos
    cosas son indistinguibles
  · y 13 herramientas aparecieron ENTRE dos ejecuciones suyas.  El árbol construye más
    rápido de lo que un registro escrito a mano puede seguir
```

```
LO MÁS VALIOSO QUE SALIÓ, y fue una ZARPA
  `msg_census` no la citaba ningún hallazgo, y `toolcheck.py` registra en su cabecera un
  incidente suyo.  Fui a comprobar si seguía vivo.  Sigue:
      lo que dice   503 sitios de envío, 217 mensajes, 217 símbolos sin resolver
      lo que sus propios veredictos dicen   VIVA 11 · MUERTA 5 · NO_CONDICIONAL 487
      lo que reality   el fichero activo para Polaris12 es polaris10_smumgr.c, con 14
                       sitios, que resuelven 14/14 contra smu7_ppsmc.h
      sobreestimación   36×
  Su self-test PASA, porque verifica que el parser reproduce unos vectores conocidos, y
  no verifica que el censo esté acotado a mi ASIC, que es la propiedad que falló
  Una herramienta que dice «503» cuando la respuesta es 14, con un self-test verde, es la
  forma más peligrosa de herramienta: plausible y equivocada
  Y hay una línea H activa ahora mismo, así que el coste de que alguien construya sobre
  ese 503 no es teórico
  → RE-43, TL-14

LO QUE NO HICE, y lo digo porque era lo obvio
  · no arreglé msg_census.  Es de otra sesión y COORDINACION.md:184 es «informa, no
    arregles».  Documenté el número correcto, la causa, y qué haría falta
  · no añadí el token de seguridad a oracle.sh, rx550pm4val.c ni rx550ref.c, que es una
    línea cada uno y los dejaría ejecutables por el registro.  También son de otras
    sesiones.  Queda escrito en TL-30, TL-31 y TL-32 exactamente qué línea falta
  · no toqué rx550_pm4.c:277.  Sigue con `count - 1` cuando el ASIC espera `count`
LO QUE ESTO DICE DEL EQUIPO, y es lo que más me importa
  `pm4census.py` mide la convención de count «SÓLO en el ASIC que»: exactamente el filtro
  que a msg_census le falta
  `pm4_reachable.py` separa los paquetes que un ASIC EJECUTA de los que DEFINE: la
  distinción que separa el contraejemplo vivo de RE-31 de doce coincidencias que sólo
  parecen tales
  `hwip.py` responde por bloque si lo decide el caso del chip o la versión: la pregunta
  que ipsolve responde por otra vía
  Las tres atacan las tres cosas que esta mañana costaron un error.  Nadie lo pidió.
  El equipo aprende sin que nadie lo imponga, y un registro es lo que lo hace visible
```

### R-21 · `round`: el arbitraje de cifras contra el kernel, en un comando

```
WHEN      instrucción de automatizar la investigación de forma agresiva
OBJECT    (a) automatizar MI bucle, que es donde está la repetición real
          (b) componer antes de construir, que es la regla del proyecto
LA REPETICIÓN QUE IDENTIFIQUÉ, y no fue una cualquiera
  el paso caro de esta mañana, hecho a mano TRES veces, fue:
      leer un finding nuevo -> extraer sus números -> decidir si concuerdan con lo que
      el kernel imprimió al arrancar
  así se resolvieron C-009, C-010 y C-011.  Los tres eran alcanzables con un comando y
  ninguno se ejecutó como comando porque no existía
COMPOSICIÓN PRIMERO, Y YA CAMBIÓ EL PLAN
  iba a construir un detector de conflictos propio.  Leyendo 041-grafo-y-detector-
  contradicciones encontré que `causal_map.py --contradictions` ya lo hace, y MEJOR:
  pondera por ESTADO (PROVEN sobre debil) y encuentra la contradicción de block_size
  desde el PRIMER documento en vez del tercero, validado por mutación
  El detector propio lo saqué del pipeline y lo dejé sólo en el self-test como contraste.
  La regla de composición dice preferir lo existente, y aquí lo existente es mejor
LO QUE HACE round, y no hace
  scan compone docscan y toolreg · new detecta findings por sha256, distinguiendo
  MODIFICADO de NUEVO · claims extrae cifras · arbitrate las contrasta con el kernel
  conflicts compone causal_map
  Y NO ESCRIBE NADA en docs/, no edita hallazgos, y sólo escribe su fichero de estado con
  --accept.  Por eso ese flag es un acto separado y visible
LO QUE ENCONTRÓ, sobre el árbol real, en un comando
    kernel facts: vm_size 64 · block_size 10 · fragment 9 · levels_minus_one 1
                  gmc_hwip 8.1.0 · gfx_hwip 8.0.0 · sdma_hwip 3.1.0
    claims débiles: 3 valores, 0 AGREE, 3 DISAGREE
      block_size  22  vs kernel 10   en 030-page-walker-gfx8-2-niveles.md
    claims duras:  4, todas AGREE
  O sea: encuentra la contradicción que C-009 arbitró a mano, desde el §CUDA del
  finding.  22, 23 y 24 salen los tres
DOS DEFECTOS PROPIOS QUE EL SELF-TEST Y LA EJECUCIÓN REAL ENCONTRARON
  1 leía `block_size = 33` como afirmación.  Era una MUTACIÓN de prueba: 041 dice
    textual «anado `block_size = 33 | PROVEN` a un documento y lo detecta».  Un valor
    mal A PROPÓSITO, reportado como DISAGREE.  Corregido saltando los textos que anuncian
    mutación, porque un solo valor inyectado falso destruye cualquier precisión
  2 el extractor de claims débiles aceptaba cualquier palabra de tres letras como clave y
    capturó `equivoque` en «**Y me equivoqué en `block_size`.** Reporté 13/14/15. Es
    **22/23/24**» con el valor 13/14/15.  Como ese match consumía el texto, nunca llegaba
    a la afirmación real.  Corregido construyendo el patrón de clave desde
    ARBITER_TABLE, así que por construcción no puede capturar prosa
  El segundo es el instructive: la extracción mala no sólo añade ruido, también
  ESCONDE lo que hay que ver.  Un falso positivo se nota; un falso negativo por consumo
  de texto, no
CLASIFICACIÓN  TOOL_PARTIAL, y es medible
  recall bajo y declarado: 7 claims arbitrables sobre 92 findings.  La forma dura
  `clave = N` encuentra 4.  El corpus está escrito en prosa con números en negrita y en
  tablas, y un regex no cubre eso.  No se publica un recall del 100 % que no existe
  los controles negativos que importan:
    · un log del kernel que dice 22 hace que nuestro 10 salga DISAGREE
    · sin log del kernel, TODO es NO_KERNEL y no se inventa ningún veredicto
    · una clave no arbitrable se marca, no se adivina
    · sin --accept no se escribe NADA
LO QUE NO SE AUTOMATIZA, y TL-36 lo dice con todas sus letras
  automatizar la MEDICIÓN, nunca la INTERPRETACIÓN
  `round` extrae las cifras, no el sentido.  Que el 22 sea incorrecto no lo deduce la
  herramienta: lo deduce el hecho de que el kernel lo contradice Y de que el código lo
  confirma.  Eso último es trabajo de una persona
  y siguen manuales: leer el §CUDA y decidir si merece fila; escribir la fila con sus
  nueve campos; arbitrar lo que el kernel no imprime, que es casi todo lo interesante
  porque sólo hay cuatro líneas suyas que arbitran
Y EL RIESGO QUE LA AUTOMATIZACIÓN INTRODUCE, que hay que nombrar
  una herramienta que dice DISAGREE en todas partes se lee como «todo está mal», y una
  que dice AGREE en todas partes como «todo está bien».  Ninguna es defendible
  por eso el vocabulario es cerrado y no se redondea: AGREE es «consistente con el
  autoinforme», DISAGREE es «el kernel dice otra cosa», NO_KERNEL es «no lo sé»,
  NOT_ARBITRABLE es «esta pregunta no se arbitra así»
  y una precisión medida vale más que un recall alto: un detector que señala cuatro
  contradicciones reales y ningún falso vale más que uno que señala cuarenta
```

### R-22 · `claim` mide la cobertura, y al medirla encontró 28 findings sin registrar

```
WHEN      instrucción de automatizar, y la pregunta que yo me hacía era cuál es MI
          repetición grande.  La respuesta fue: la sincronización documental
LA MEDICIÓN, Y ESTA ES LA QUE IMPORTA
      95 findings en 06-INGENIERIA-INVERSA/findings/
      67 citados por algún fichero de docs/
      28 NO CITADOS POR NADA
  Veintinueve por ciento de la evidencia del proyecto, nunca registrada.
  Y no son menores.  Leyendo los NOMBRES:
      043-vuelta-atras-035-y-036-leian-el-asic-equivocado
          otra sesión descubriendo que 035 y 036 leen el ASIC equivocado.  Es C-011
      059 / 060 / 061-srcdata
          qué lleva src_data[0] del vector de interrupción, que es lo que RE-36 y RE-40
          afirman
      062-citas-de-c-009-desplazadas-y-tabla-de-030-invertada
          sobre la contradicción que esta documentación ya registró
  Así que el hueco no es cosmético: es evidencia, y entre ella un segundo testigo
  independiente de una contradicción ya resuelta
  Y el nombre 043.contains REFRACTS=035, 036: una retracción que no estaba en mi registro
LO QUE LA HERRAMIENTA HACE, Y LO QUE NO PUEDE HACER
  MIDE  cobertura, próximo RE-nn libre, colisiones de índice, huecos de numeración, y
        claims SIN LOCATION, que son las no auditables
  ESCRIBE NADA.  No hay flag que la haga editar docs/, y su self-test lo comprueba
  LEGALIZANDO el propio código fuente en busca de un open(...,'w').  Un scaffolder que
  pudiera publicar sería una máquina para fabricar afirmaciones, que es exactamente el
  fallo que este proyecto ha pagado cuatro veces
  --scaffold IMPRIME un borrador con los campos mecánicos rellenos de la cabecera del
  finding, y TYPE y STATE en PENDIENTE.  Porque son los dos campos que llevan
  conocimiento, y esta herramienta no tiene ninguno
EL CONTROL NEGATIVO QUE IMPORTÓ
  la cobertura NO puede confundir dos findings con el mismo índice.  Hay 27 colisiones en
  findings/, así que casar por número en vez de por nombre completo haría parecer
  cubierto un finding que no lo está.  El self-test lo comprueba con dos findings 001
  deliberadamente
Y TRES FALLOS DEL SELF-TEST QUE FUERON MÍOS, NO DE LA HERRAMIENTA
  · la cobertura hacía bien lo difícil (distinguir los dos 001) y yo había escrito la
    aserción al revés, así que un acierto se veía como fallo
  · el scaffold etiqueta CORPUS como VERSION, porque etiqueta por el CAMPO de claim, y
    comprobaba que saliera la palabra CORPUS
  · y un SyntaxError por poner «·», un separador tipográfico, en la línea del token de
    seguridad.  Los tokens tienen que ser ASCII
```

```
LO QUE SALIÓ DE MEDIR, y es lo que justifica la tarde
  REGISTRADO POR LA COBERTURA, y verificado por mí contra el corpus
    RE-47  src_data[0] NO dice «dónde».  Es el SUBTIPO del evento de DISPLAY.
          tonga_ih.c:263 lo produce; dce_v8_0.c lo consume en un switch.  Medido.
          Y eso CORRIGE una fila mía: RE-36 y RE-40 decían «dice dónde», y el IV de
          GFX8 no lleva ninguna dirección de memoria
    RE-48  SDMA0_HWIP NO LLEGA A LEERSE para este ASIC.  La ruta de Polaris12 resuelve
          sus bloques por caso de chip (vi.c:2113), no por amdgpu_ip_version.  Y 046 lo
          demuestra por ALCANZABILIDAD, sin MMIO
          Eso es MÁS FUERTE que mi arbitraje de C-011: yo demostraré qué implementación
          corre; 046 demuestra que el VALOR de esa versión no puede cambiar ninguna
          conclusión.  Es una pregunta cuya respuesta no importa, que es raro y valioso
  Y LA TERCERA RETRACCIÓN DE 035 Y 036, por tres caminos independientes
    esta documentación, por el log y el despacho, con ipsolve
    otra sesión, por haber leído el fichero de otra generación
    otra sesión, con una herramienta, cerrada por alcanzabilidad con 046
  Los tres llegan al mismo veredicto y ninguno dice «lo he leído en la spec», porque la
  spec no existe.  Eso es lo que hace una corrección robusta: que el siguiente que mire
  llegue a lo mismo desde otra dirección
EL PATRÓN DE LAS TRES CORRECCIONES DE HOY, que ya se puede nombrar
    C-009  block_size:  13  ->  22  ->  10
    C-011  emisor de PTE:  v4_0  ->  v3_0
    RE-47  src_data[0]:  payload  ->  puntero de ring  ->  subtipo de display
  En los tres, la respuesta intermedia no era falsa: era la PREGUNTA EQUIVOCADA.  Y en los
  tres la corrección la encontró una sesión distinta, leyendo
  Ése es el patrón real de la mañana, y ningún escaneo lo detecta
```

### R-27 · `drift.py`: dos índices con el mismo nombre, y la colisión la causé yo

```
WHEN      instrucción de seguir viendo lo que hacen las otras sesiones y tenerlo todo
          documentado.  Lo primero que esa instrucción pide es saber si mi
          documentación sigue siendo cierta
EL HUECO, y era el más grande que quedaba
  todo lo demás del toolkit mide UN sujeto: el corpus, las citas, las constantes, el
  estado del host.  Nada medía la variable que decide si todo eso sigue valiendo:
      ¿se ha movido el árbol desde que lo miré?
LO QUE MIDÓ
  el registro de herramientas conoce 2 directorios.  El repositorio tiene 7
      revkit                                18 guiones   5928 lineas   0 documentados
      01-AUDITORIA/FASE-C1-RUNTIME-PREFLIGHT 17          10836         0
      08-ARQUITECTURA/tools/btfq             7           1744         0
      06-INGENIERIA-INVERSA/corpus           5            694         0
      DOCUMENTATION-ROUTER/knowledge         3           1195         0
  98 scripts sin entrada TL-
  actividad 12 h: 30 commits, 125 ficheros tocados, 16 modificados, 301 nuevos sin
  commitear
  primer sello de evidencia: 210 ficheros
LO QUE ENCONTRÓ, Y NO ERA LO QUE SE BUSCABA
  se buscaba «qué herramientas nuevas hay».  Se encontró que existe un CENSO
  DOCUMENTAL con 1576 filas en estado DESIGN_FROZEN, con un KNOWLEDGE-POLICY que
  manda registrar las discrepancias como CONTRADICTION
  y que de mis 15 ficheros de docs/ en ese censo hay CERO
  y los dos únicos matches aparentes son OTROS ficheros con el MISMO nombre
  la colisión la creé yo: 9 de mis 15 ficheros tienen homónimo, y el peor es el
  índice
      00-INDICE/MASTER-RESEARCH-STATUS.md   64085 B   2026-09-28   <- lo que abre el router
      docs/MASTER-RESEARCH-STATUS.md        49067 B   2026-10-02   <- el mío
  y además OTRA sesión está escribiendo un SEGUNDO índice en la RAÍZ desde HOY, con
  seis de esos mismos nombres:
      ./TOOLS-STATUS.md      3657 B  vs  docs/: 112414 B
      ./OPEN-FRONTIERS.md   22353 B  vs  docs/:  44722 B
      ./EVIDENCE-MATRIX.md  13847 B  vs  docs/: 105761 B
  DOS índices operacionales en paralelo, seis nombres idénticos, y ninguna de las
  dos partes lo sabe de la otra
POR QUÉ NO SE ARBITRA, y hay que decirlo con claridad
  no se puede arbitrar leyendo.  La de docs/ tiene 41 TL-, 50 claims, 11
  contradicciones y 9 herramientas con 135 checks.  La de raíz es más pequeña en
  todo y más nueva en todo
  «más nueva» no es argumento: la de raíz se modifica más porque se está escribiendo,
  no porque sea más correcta.  «Más grande» tampoco: el tamaño mide cuanto, no si
  es un problema de nomenclatura y de registro, y se arregla con una fila y una
  decisión
  es además la MISMA clase que UNIDENTIFIABLE en citations.py, y que RE-47: un
  nombre que no identifica un fichero convierte una referencia bienintencionada en
  una ambigua, y quien la resuelve no sabe que hubo una elección.  Aquí es fácil
  porque las dos versiones están al lado.  En un censo de 1576 filas no lo es
LO QUE ESTA SESIÓN HACE, Y ES LO ÚNICO QUE LE TOCA
  · registra la contradicción, que es lo que el KNOWLEDGE-POLICY congelado pide
  · desambigua DENTRO de sus propios ficheros
  · escribe la línea que falta, sin aplicarla
      la fila mínima en DOCUMENTATION-INVENTORY-ROUTING.tsv para que el router no
      abra el documento equivocado:
        docs/MASTER-RESEARCH-STATUS.md  md  STATUS  CURRENT  SECONDARY  PROJECT_STATUS
      más RELATIONSHINGS apuntando a 00-INDICE/MASTER-RESEARCH-STATUS.md
  · NO edita el TSV, NO renombra nada mío, y NO decide cuál índice sobrevive
LO QUE NO SE ADOPTA, y lo que sólo se observa
  · las 76 herramientas ajenas se REPORTAN, no se adoptan.  Adoptar sería afirmar
    cosas sobre código que esta sesión no escribió ni validó: el OwnedError que
    COORDINACION.md prohíbe
  · 03-EXPERIMENTOS/ep08-doorbell-suppression/ contiene nhwa.c, nhwa.ko,
    Module.symvers y un Makefile: un módulo COMPILADO y sin seguimiento en git.
    /proc/modules no lista ningún nhwa, así que está compilado y NO cargado.  Se dice
    que existe y que no está cargado.  No se carga, no se descarga, y no se comenta
    si cargarlo sería seguro: descubrir un módulo no autoriza a hacer nada con él
UN MENSAJE DE COMMIT NO ES UN HALLAZGO, y lo dice en su propia salida
  el commit más reciente se titula «un control que decia lo que no era», que es la
  misma clase de defecto que esta ronda ha encontrado tres veces
VALIDACIÓN  13 checks, 0 fallos.  Y dos que merecen nombre:
  · los directorios de herramientas se DESCUBREN andando el árbol, y un corpus lleno
    de scripts queda excluido.  Enumerar los declarados reproduciría el fallo
  · la guarda de escrituras es DE COMPORTAMIENTO: inventario antes y después de
    llamar a seal/activity/toolkit/drift, y la única diferencia admitida es el
    manifiesto.  La primera versión era una lista blanca de regex y falló, porque
    tenía que coincidir con el regex sobre cómo éste se detiene: una guarda de texto
    que tiene que coincidir con un regex sobre la ortografía es una guarda que va a
    mentir
```

### R-28 · Las 76 herramientas de otras sesiones, y una corrección que era una inflacción

```
WHEN      instrucción de mantenerlo todo documentado, aceptando que es imposible
          y que hay que hacer lo que se pueda
LO QUE PEDÍA Y LO QUE HACÍA
  la instrucción era «documenta a los otros».  Lo que yo hacía era REPORTAR que estaban
  sin documentar y no tocarlos, por `COORDINACION.md:184`
  eso era una lectura demasiado amplia.  «Informa, no arregles» quiere decir no
  edites su IMPLEMENTACIÓN.  Escribir sobre sus herramientas en MIS ficheros es
  informar, y es literalmente lo que ese fichero pide
  indexar una herramienta ajena no es adoptarla: adoptar sería afirmar cosas sobre
  código que no escribí ni entendí
LO QUE HICE
  TL-43: transcripción de las 76 que docs/ no citaba, desde su propia cabecera, con
  su ruta, tamaño, si declaran contrato, si tienen self-test, y su primera frase
  114 guiones en 7 directorios ->  76REFERREDENCIADOS  ->  0 sin citar
  TL-44: entrada propia para `gccverify.py`, que apareció mientras documentaba las
  demás
LA CIFRA QUE TENÍA ESTABA MAL, y es la tercera vez en este proyecto
  dije 98 sin documentar.  La detección buscaba sólo `<nombre>.py` entre acentos graves, y
  eso no ve las menciones en texto plano
  resultado: hasta mis propias herramientas aparecían como no vistas, y `docscan.py` salía sin
  documentar teniendo `TL-01`
  medido de tres maneras distintas, la pregunta da tres respuestas:
      114 guiones en el árbol
       12  con cabecera TL- propia
       16  citados entre acentos graves en TOOLS-STATUS
       39  citados como palabra en los 8 ficheros de docs/
       76  citados en NINGUNO
  así que la pregunta hay que hacerla sobre todo docs/, con límites de palabra, y la
  respuesta tiene que llevar su método puesto.  Un recuento cuyo método no se declara
  es un número que espera estar mal
  ahora el método va impreso cada vez que sale el número, y hay un self-test que
  comprueba que una herramienta cuenta como documentada en las TRES formas en que se
  escribe: cabecera TL-, `<ruta>/<nombre>.py` y prosa desnuda
  y la cifra final es 0, con 76 documentadas en el camino
UN ERROR DE EXTRACCIÓN QUE ERA PEOR QUE NO DOCUMENTAR
  la primera versión de la transcripción puso `!/usr/bin/env python3` en las 76 filas
  la causa: el patrón del docstring usaba `^` sin `re.M`, así que `^` se anclaba al
  principio del FICHERO, el docstring de la línea 2 no casaba nunca, y el patrón
  alternativo de comentario cogía el shebang
  una tabla donde todas las filas dicen lo mismo inútil es PEOR que no tener tabla,
  porque PARECE documentación.  Ahora salta el shebang y la licencia explícitamente, y
  se prefiere el docstring al comentario porque un docstring es lo que el autor escribió
  a propósito
  y el resultado es legible: `atomrom.py -- parseo del VBIOS ATOM de la RX550`,
  `causa.py -- genera el mapa causal de un simbolo, automaticamente`
EL BUCLE, CERRADO ENTERO EN ESTA RONDA
  mientras documentaba las 76 apareció una más: `tools/` pasó de 36 guiones a 37
      descubrir  ->  documentar  ->  la cifra baja
  eso es exactamente para lo que existe una herramienta de descubrimiento, y esta vez
  se vio el ciclo completo
LO QUE ESTA TABLA NO ES, PORQUE IMPORTA
  no valida ninguna de esas herramientas y no ejecuta ninguna
  la columna «propósito» es su primera frase, y puede estar desfasada respecto a lo que
  la herramienta hace hoy: es lo que el fichero DICE de sí mismo
  «contrato» significa que el fichero DECLARA uno.  Declarar un contrato no es
  respetarlo, y «tiene self-test» no es «pasa el self-test», y yo no lo he ejecutado
  y nada de esto confirma ni contradice ninguna claim de este proyecto
LO QUE SIGUE SIN SER POSIBLE
  documentar bien 114 herramientas requiere leerlas.  Esto las hace localizables con un
  grep, que era invisible, y la otra mitad del trabajo es de quien las escribió
```

### R-29 · El índice de hallazgos tenía 48 huecos, y esa es la forma que tiene aquí la documentación vieja

```
WHEN      instrucción de mantenerlo todo actualizado y de aceptar que es imposible
EL SÍNTOMA, que no es «falta escribir» sino «el documento ya no describe el árbol»
  `stale  findings-unindexed  48 of 114 findings are not in the index`
  114 hallazgos, 34 índices duplicados, 3 huecos de numeración.  El índice tenía 48
  entradas de menos que el directorio, y su propia cabecera lo avisa: «Re-generar
  antes de citar».  Una instrucción que no se cumple es un defecto del documento
LO QUE SE HA HECHO
  `docscan --index` añade una fila por hallazgo ausente, tras la ÚLTIMA fila de la
  tabla, porque el fichero tiene prosa después y añadirlas al final las habría
  enterrado en un ensayo
  49 filas.  Con eso el aviso `findings-unindexed` desaparece del informe
  cada fila dice `NO LEIDA — transcripción, nadie lo ha leído`
  y esa columna es toda la honestidad del modo
POR QUÉ CADA FILA TIENE QUE DECIR QUE NO LEÍDA
  la fila afirma que el hallazgo existe, cómo se llama, en qué estado de git está, y
  su título.  El título es transcripción, no juicio
  un índice que presentara 49 hallazgos «documentados» sin decir que nadie los abrió
  sería un índice que miente, y mentir por formato es la forma más común de mentir
  indexar es lo mecánico; leer es lo que produce conocimiento.  Invertir el orden
  produce 49 filas que parecen documentadas y no lo están
EL ERROR QUE VOLVIÓ INÚTIL LA TABLA, y casi se me pasa
  la primera ejecución puso `CUDA principal` en las 49 filas: tomaba el primer H2, y
  el primer H2 de estos hallazgos es SIEMPRE `## CUDA principal`
  una columna de tema que dice lo mismo en las 49 filas no es una columna de tema
  el H1 lleva el título del autor, y ahora sale `043 · la asercion la hacen 4 sitios`
LO QUE NO SE HACE
  no se leen los 49.  Leerlos es trabajo de quien los leyó, y este modo no crea claims
UNA CONEXIÓN QUE SALIÓ SOLA, Y NO LA BUSCABA
  al indexar se puso de manifiesto:
      hallazgo `043-asercion-struct-mqd-contra-offsets.md`
        «El driver tiene una aserción sobre el hardware que nunca se comprobó»
      herramienta `gccverify.py`   (TL-44)
        pregunta al COMPILADOR por sizeof y offsetof de la cabecera REAL
  dos sesiones convergen desde direcciones opuestas: el hallazgo motivó a la
  herramienta, o la herramienta cierra el hallazgo.  No lo registro como claim ni
  como relación verificada, porque son dos títulos y los títulos no bastan
  pero eso es exactamente lo que produce un índice vigente: no una lista, sino la
  línea entre un hallazgo y la herramienta que lo cierra
VALIDACIÓN  16 checks, 0 fallos.  Los tres nuevos:
  · el tema sale del H1, no del primer H2, y por qué: todos comparten sección
  · un hallazgo sin versionar sale UNTRACKED, y eso significa que `git clean -x` lo
    borra sin dejar rastro
  · toda fila añadida queda marcada NO LEIDA
```

### R-30 · `F3d` estaba ARREGLADO en el código y mi documentación decía que no

```
WHEN      instrucción de leer toda la documentación del proyecto y actualizarla
LA MEDICIÓN, y por qué no fui a leer 572 ficheros
  hay 572 ficheros .md en el proyecto y 7,9 MB.  No caben en una ronda, y decirlo es
  lo honesto.  Pero «vieja» no es sólo «de hace días»: una documentación está vieja
  cuando afirma algo que ya se ha refutado, y ESO sí se mide
  El proyecto tiene sus propias retracciones escritas:
      043   `CORRECTION`,  `RETRACTS=035, 036 y parte de 037`, cerrada por 046
  así que la búsqueda correcta es: ¿qué documentación sigue citando como vigentes
  los hallazgos retractados?
  respuesta: 6 ficheros citan `035`, 7 citan `036`.  Seis son míos, y los seis ya
  los marcan como retractados.  EL SÉPTIMO ERA `revkit/PTEPDE-GFX8.md`, y no estaba
  viejo: citaba `C-011` con exactitud y decía lo que no cerraba
  lo que sí tenía, y no lo había leído nadie, era esto:
      «No sé si `036` en `rx550_pm4.c` replica esta secuencia. Eso se comprueba
        leyendo ese fichero, no el corpus.»
  ESO ERA LA TAREA.  Y era el discriminante que `F3d` llevaba pidiendo desde el
  principio
LO QUE SALIÓ DE LEER ESE FICHERO
  `rx550_pm4.c:298` escribe `count`.  No `count - 1`.  La función replica
  `sdma_v3_0.c:986-996` dword a dword y en orden, las diez, y
  `RX550_SDMA_PTEPDE_DW = 10` concuerda con las diez que escribe
  las diez apariciones de `count - 1` que quedan en `07-DRIVER/` están en COMENTARIOS
  y TESTS que documentan el error.  Ninguna en código
  y `test_pm4.c:375` dice: «findings/034 said this field was count-1. It is not, on
  this ASIC»
  es decir: **el defecto ya estaba corregido, y mi documentación seguía
  afirmándolo**.  Ese es el conteúdo de «documentación vieja» cuando importa: no
  una fecha, una afirmación que dejó de ser cierta y nadie fue a comprobar
LO QUE HE ACTUALIZADO, y es todo lo que estaba mal
  · `OPEN-FRONTIERS.md` F3d   `CONFIRMADO` → `CORRECTED 2026-10-02`, con la medición
  · `IMPLEMENTATION-STATUS.md`  «sigue con `count - 1`» → lo que hay hoy
  · `EVIDENCE-MATRIX.md`  `RE-52`, la claim de la réplica dword a dword
  · `CONTRADICTIONS.md`  actualización de `C-011`: qué sigue vigente y qué se cerró
  · `FINDINGS-INDEX.md`  la fila de `036` decía `UNT...` (sin leer): el índice ya no
    puede afirmar eso
  NADA se ha borrado.  El defecto existió, se detectó tarde, y eso es parte del
  resultado: dice que una suite verde puede no ver un error de un byte en el
  argumento de un emisor de DMA
LA OBSERVACIÓN MÁS TRANSFERIBLE, Y LA ESCRIBIÓ EL PROPIO DRIVER
      «Un cross-check hecho sobre una sola fuente no es un cross-check, y citar dos
        líneas del mismo fichero como si fueran dos fuentes es la forma concreta que
        me engañó.»
  es la misma forma que `RE-47`, `C-009` y `C-011`: una respuesta intermedia que no
  era falsa, era la pregunta equivocada.  Y un contraste hecho sobre una fuente no
  es un contraste
LO QUE ESTO NO CIERRA, aunque cierre `F3d`
  qué hace el ASIC con ese `count` sigue siendo `NOT_DETERMINED`.  Que el código
  replique al emisor de referencia es `PROVEN` sobre el CÓDIGO.  Que el hardware lo
  interprete así, no: eso es `F1` y `F3c`
  y el proyecto ya lo tiene escrito: «hardware execution order NOT_PROVEN»
LO QUE NO SE HACE
  `revkit/PTEPDE-GFX8.md` es de otra sesión y no se toca.  La respuesta está en
  `RE-52`, y lo que corresponde es que quien lo escribió la incorpore
```

### R-31 · El vocabulario cerrado era decorativo, y el defecto era mío

```
WHEN      instrucción de continuar
DE DÓNDE SALIÓ ESTO
  dos hallazgos nuevos de otra sesión, y los dos títulos apuntan a lo que llevo
  haciendo mal toda la sesión:
      071-el-except-que-devuelve-stub-y-el-flag-que-desactiva-la-auditoria
      046-auto-referencia-y-la-jerarquia-de-fuentes
  `071` cuenta cinco defectos encadenados de la misma clase, y dice que es la QUINTA
  vez que esa clase ocurre en este proyecto y que ya merece su propia regla
  su regla:
      «no existe» sólo es un dato si el índice sobre el que se buscó está
      CONSTRUIDO, y su tamaño se imprime junto al resultado.
      Un `not found` sin cota no es una medida: es un olvido.
  y su defecto 2 es «regex que no admite `/`»
EL BUG QUE YO COMETÍ, Y ERA EL SUYO
  el de `drift.py`: exigir acentos graves, y con eso no ver `tools/docscan.py`, ni
  `snapshot.py`, ni ninguna mención en prosa desnuda
  es exactamente un método de búsqueda que no alcanza, usado para afirmar una
  ausencia.  Reportó 98 herramientas sin documentar cuando eran 76, y dio por NO
  VISTAS las herramientas de esta misma sesión
  y lo escribí en el propio `drift.py`: «la primera versión SÍ los exigía, y por
  eso contaba MENOS»
  `citations.py` e `ipsolve` ya cumplían la regla: imprimen el tamaño del índice.
  El defecto estaba en la herramienta que construí para vigilar esa clase de fallo
LA AUDITORÍA, Y SALIÓ AL REVÉS DE LO QUE ESPERABA
  la regla de `046` es una jerarquía de fuentes: un hallazgo mide el ASIC, un
  documento de método mide el PROYECTO, y sus afirmaciones sobre el hardware son
  ejemplos de por qué una herramienta falla, no respuestas
  la apliqué a mi propio registro, buscando claims cuyo SOURCE sea un documento de
  método y que hablen de hardware:
      12 hallazgos de la SERIE_METODO en el árbol
      1 sola claim con source de método: RE-39, y con hardware? SI
  y al mirarla: **FALSO POSITIVO**.  RE-39 dice literalmente «LO QUE SE MEDIO, por
  mí, no por el hallazgo», cita la descargue de responsabilidad de la propia
  herramienta, y su `grep -c` lo dice.  Mi regex casó «¿este .c entra en el binario
  para mi ASIC?», que es de COMPILACIÓN, no de semántica
  cuarta medición inflada o mal construida de esta sesión, y la quinta clase de
  «el instrumento culpa al artefacto»
EL DEFECTO REAL QUE SALIÓ AL MIRAR, Y ERA MÍO
  los `TYPE` del registro de claims:
      claims                                            51
      TYPE fuera del vocabulario cerrado                12   (24 %)
      STATE fuera del vocabulario cerrado                 0
      `TYPE DERIVATION + NEGATIVE_RESULT`
      `TYPE OBSERVATION, con medición propia`
      `TYPE MEASUREMENT · y el hallazgo de mayor valor de esta ronda`
      `TYPE CONTRADICTION (resuelta)`
  en cada caso la anotación era CIERTA y útil donde estaba, y nadie me dijo que
  dejaba el campo ilegible.  Las doce se escribieron así porque el vocabulario era
  una lista y no un check
  y el daño es silencioso en la dirección mala: no da error, da una clasificación
  que nadie cuestiona.  Cualquier herramienta que agrupe claims por `TYPE` lee las
  doce como malformadas y no como los tipos que son
LO QUE SE HIZO
  `TYPE` queda con un token.  La información no se tira, se muda:
      ALSO   los tipos secundarios, que es lo que el `+` significaba
      NOTA   la prosa, que es lo que la coma o el punto medio significaban
  y `docscan.check_taxonomy` falla si un `TYPE` o un `STATE` no es token del
  vocabulario, y también si un token válido lleva prosa detrás
  cuatro maneras de estar mal, y el self-test lo comprueba con las cuatro
  `STATE` no necesitó nada: ya estaba limpio, y por eso la auditoría encontró una
  clase y no dos
LO QUE TAMBIÉN ARREGLÉ, Y ERA RUIDO MÍO
  6 de los 20 `review` de `docscan` eran nombres de ejemplo en mi propia
  documentación: `demo.c`, `nombre.py`, `001-uno.md`
  un `review` que es ruido entrena a la gente a ignorar los `review`, que es peor
  que no tener el check.  Ahora son `<dir>/demo.c` y `<001>-uno.md`
LO QUE ESTO ES Y LO QUE NO ES
  esto es un defecto de MI documentación y se cierra aquí, no en un hallazgo
  y `046` no se ha tocado: es de otra sesión.  Lo que corresponde es que quien lo
  escribió incorpore la jerarquía de fuentes y la herramienta que ya aplica
VALIDACIÓN  docscan 17 checks, 0 fallos.  Los de la taxonomía:
  · TYPE fuera del vocabulario -> reportado
  · STATE fuera del vocabulario -> reportado
  · un token válido con prosa detrás -> reportado
  · y `RE-01` solo, que está bien, NO se reporta
```

---

### R-26 · `constmap.py`: 43 constantes contra su propio testigo, y CERO contradicciones

```
WHEN      instrucción de automatizar; el hueco era la capa de constantes de F3d
EL AGUJERO, y estaba escrito en el fichero sin que nadie lo leyera
  cada `#define RX550_*` cita en su comentario la línea upstream de la que salió:
      #define RX550_PKT3_NOP           0x10    /* sid.h:343 */
  así que cada constante es una afirmación falsable con testigo, y la afirmación
  se puede mechanically comprobar contra el propio corpus
EL RESULTADO, que es NEGATIVO, y por eso es la forma fuerte
  43 constantes · con testigo 32 · sin testigo 11
      AGREE 15 · AGREE_DISCRIMINATING 8 · AGREE_COMMENT 4
      WITNESS_USAGE 3 · NOT_COMPARABLE 2 · UNCITED 11
      DISAGREE 0 · AMBIGUOUS 0 · NOT_A_DEFINE 0
  los 32 con testigo quedan CUADRADOS: no queda veredicto sin explicar
QUÉ ESTRECHA ESTO EN F3D, y no poco
  la capa de constantes de rx550_pm4.h está limpia.  El defecto de F3d —
  `sdma_v4_0` donde el código dice `sdma_v3_0`, y `count - 1` en
  rx550_pm4.c:277 — NO está en estas 43 constantes: está en el `.c`, y es un error
  SIMBÓLICO, no de valores.  Eso parte F3d en dos y deja una mitad medible
LA COMPOSICIÓN, Y EL USO REAL DE ELLA
  citations.py marca sid.h:343 como UNIDENTIFIABLE, y con razón: hay DIEZ sid.h y
  uno está en drivers/gpu/drm/radeon/ con macros distintas en la misma línea
  aceptar eso como respuesta tiraba las once cabeceras de packet, la familia que
  más importa del fichero
  pero el autor copió un VALOR del fichero que tenía abierto, así que un valor que
  coincide con una sola copia la identifica.  8 de 10 coinciden, y las 2 que no
  son del subsistema equivocado: AGREE_DISCRIMINATING
  y cuando el valor NO discrimina, vuelve a ser AMBIGUO y se dice.  Para eso
  resolve() acepta collapse_ambiguous=False, y sólo lo usa esta herramienta
TRES TIPOS DE TESTIGO, porque no pesan igual
  define    lleva el valor
  comment   vid.h documenta la codificación en prosa: 186 es el #define, y 187-188
            son `/* 0 - me` y ` * 1 - pfp`.  citar 187 para ENGINE_ME = 0u tiene
            un testigo que SÍ lleva el 0: AGREE_COMMENT
  code      citar un `.c` para una constante: 6054 está en la función correcta y
            dentro del paquete correcto, pero no lleva el valor.  WITNESS_USAGE
            corrobora el TEMA, no el NÚMERO, y no es un defecto
LO QUE CASI DIJE MAL, y es lo más importante de esta entrada
  al ver NOT_A_DEFINE en 7 constantes escribí «dos testigos apuntan a
  amdgpu_ring_write(ring, 0), que no tiene nada que ver con WAIT_REG_MEM: dos citas
  equivocadas».  Era FALSO
  gfx_v8_0.c:6047 ES PACKET3(PACKET3_WAIT_REG_MEM, 5), dentro de
  gfx_v8_0_ring_emit_hdp_flush; y 6206 está en gfx_v8_0_ring_emit_vm_flush, que
  también lo emite en 6180
  Es la lectura plausible y equivocada: la misma forma que C-009, C-011 y RE-47.  La
  respuesta intermedia no era falsa, era la pregunta equivocada, y la corrección la
  encontró leer la FUNCIÓN que contenía la línea en vez de la línea
  y el defecto estaba en mi clasificación, que trataba «no es un #define» como
  «no hay nada» sin preguntar de qué tipo era la línea
TRES FALLOS QUE QUEDAN PORQUE SON EL DATO
  · la ambigüedad mal tratada dejaba sin comprobar las 11 constantes de packet.  Un
    veredicto puede ser correcto y ser inútil: éste lo era y aun así tapaba lo que
    había que medir
  · comment_states buscaba dígitos en la línea ENTERA, así que
    amdgpu_ring_write(ring, 0) contaba como testigo que declara 0.  El 0 es del
    código.  Un testigo que concuerda por el motivo equivocado es peor que
    ninguno, porque parece corroboración
  · y exigía el */ de cierre, cuando el comentario de vid.h se abre en 187 y se
    cierra en 189: AGREE_COMMENT era 2 en vez de 4
  el segundo lo encontró un check de comportamiento escrito para otra cosa, que es
  el orden correcto: escribir la propiedad primero, y que el bug aparezca al
  ejercitarla
LA TERCERA GUARDA QUE SE DETECTA A SÍ MISMA
  el check para impedir una heurística de nombres era `if "SPECIFICITY" not in src`,
  y falló porque la cadena estaba dentro del check.  Tercera vez en este proyecto:
  toolreg.py publicó un interlock que se negaba a ejecutarse, y snapshot.py un
  check que casaba con su propio texto
  el arreglo no es buscar con más cuidado: es una guarda inmune al texto.  Si
  arbitra el VALOR y el nombre sólo se muestra, renombrar la macro upstream no puede
  cambiar el veredicto.  Se renombra a TOTALLY_UNRELATED_TOKEN y sigue AGREE
LO QUE NO HACE
  · no evalúa macros: `((x) << 8)` es NOT_COMPARABLE, no un 256 inventado
  · AGREE prueba que el número coincide con una línea.  Qué SIGNIFICA ese número es
    la otra pregunta de F3d, y sigue abierta
  · no decide cuál copia de una cabecera ambigua es la pretendida
EL DEFECTO QUE ENCONTRÓ EL REGISTRO, Y NO EL SELF-TEST
  toolreg.py ejecuta el self-test de cada herramienta con cwd=tools/.  Yo siempre
  ejecuto desde la raíz, porque siempre estoy en la raíz
  mi self-test usaba os.getcwd(), buscaba tools/07-DRUI/kernel/rx550_pm4.h, no lo
  encontraba y daba 2 fallos en una herramienta que da 17/17 desde donde su autor
  trabaja.  La herramienta estaba bien y su self-test no la validaba
  es la segunda vez en esta sesión que un CONTEXTO no previsto encuentra lo que el
  contexto previsto no puede.  La primera: la colisión entre basenames genéricos y el
  corpus real
  la raíz sale ahora de __file__, y las ocho herramientas propias pasan desde tools/
LA CUARTA GUARDA QUE SE DETECTA A SÍ MISMA, y ya es un patrón con nombre
  toolreg.py · snapshot.py · constmap.py ×2
  cuatro instancias, y el arreglo es siempre el mismo y no es tener más cuidado:
  montar la aguja en runtime, o mejor ASERTAR EL COMPORTAMIENTO.  El check de nombres
  no busca ninguna cadena: renombra la macro upstream y comprueba que el veredicto no
  se mueve
  merece decirse por qué sigue apareciendo: un guard escrito como literal es corto,
  se lee bien y PARECE exhaustivo
VALIDACIÓN  18 checks, 0 fallos.  Los que importan:
  · un testigo se clasifica: define / comment / code
  · `/* 0 - me` declara 0 y NO declara 1
  · un comentario sin número no declara nada, en vez de concordar con todo y no
    probar nada
  · CÓDIGO con un 0 en su comentario final NO vale como testigo de prosa
  · el VALOR arbitra: renombrar la macro upstream no cambia el veredicto, luego no
    puede estar entra ninguna puntuación de similitud de nombres
  · una expresión se RECHAZA, no se evalúa
  · y se ejercita el camino de INFORME con check() y main --json
```

---

### R-25 · `citations.py`: 2398 citas resueltas, y una alarma mía que era un artefacto

```
WHEN      instrucción de automatizar; el hueco era la exposición de F3d y la regla de
          working-vs-kernelbuild-difference.md §6, que estaba escrita y sin medir
EL NÚMERO, y la corrección que lo acompaña
  primera medición: 1116 de 2366 citas FRAGILE, el 47 %
  lectura honesta:  el 47 % es casi enteramente un artefacto
  tras separar por versión: 135, y la clase está ENTERA explicada
      130 de 135  los 4 ficheros INSTRUMENTADOS
                    amdgpu_vm.c  amdgpu_vm_pt.c
                    amdgpu_debugfs.c  amdgpu_debugfs.h
        5 de 135  nombres genéricos: pci.h, types.h, file.c
  Es la diferencia entre una diferencia de VERSIÓN y un DESACUERDO.  El ejemplo
  que lo muestra es `gmc_v8_0.c:1127`: tres copias de 7.1.3 dicen lo mismo, y la
  cuarta es 7.2.8, donde el código es legítimamente otro
  Dar 47 % donde la verdad es 5,6 % es un número que parece hallazgo y es un
  artefacto de contar dos versiones como una
EL ESTADO FINAL DE LAS 2398 CITAS DEL PROPIO TEXTO
  ROBUST 1070 · VERSIONED 839 · UNIDENTIFIABLE 261
  FRAGILE 135 · OUT_OF_RANGE 12 · UNRESOLVED 81
LA TRAMPA, que es distinta del problema
  UNIDENTIFIABLE 261, el 11 %: el NOMBRE no dice qué fichero.  `vi.h:27` resuelve a
  amdgpu/vi.h y a la cabecera de un driver de vídeo Tegra.  `file.c` resuelve a
  unos cincuenta ficheros
  quien verifique eso puede caer en un fichero ajeno, ver algo que parece código y
  concluir cualquier cosa.  No se arregla buscando más: lo arregla el autor
LO QUE VALE LA HERRAMIENTA: `--translate`
  ambigüedad con resolución mecánica conocida no es ambigüedad, es consulta
      amdgpu_vm.c      +12  working -> kernelbuild
                       +0  working -> baseline    <- el par idéntico
                      -12  baseline -> kernelbuild
      amdgpu_vm_pt.c   +26
  mapeo por texto EXACTO, rechazado si no es único.  y el delta 0 identifica el
  par prístino por construcción: la herramienta no elige la copia buena
CORROBORACIÓN, NO DESCUBRIMIENTO
  working-vs-kernelbuild-difference.md ya probó por hash contra los tarballs que
  working/baseline son 7.1.3 prístino y que kernelbuild lleva instrumentación
  RE-02-E1 (RG-1).  Esta herramienta llega a lo mismo por otra vía: no leyó ningún
  tarball, sólo preguntó si las copias discrepan.  Los deltas coinciden con su §4
  Lo nuevo es la EXPOSICIÓN: aquel fichero enuncia la regla y la ilustra con un
  ejemplo, y no dice cuánto del texto propio queda afectado.  Medido: 130 citas
QUÉ DICE ESTO DE RE-10, y hay que decirlo
  las líneas con las que cerré RE-10 hace una hora — 2424 2427 2428 2429 2454 2463
  — son números PRÍSTINOS.  Son los correctos para 7.1.3 y para el kernel en
  ejecución, que no puede contener `amdgpu_re02e1_note_call()` porque esa función
  la escribió este proyecto.  Contra kernelbuild cada una va desplazada 12
  Es decir: lo de hace una hora era correcto, y casi lo hago mal por una
  herramienta que habría cogido la copia equivocada sin avisar
TRES FALLOS MÍOS QUE ESTÁN EN EL FICHERO PORQUE SON EL DATO
  · «7 citas rotas en el driver»: las siete eran mi alcance de búsqueda.  Sólo
    miraba en `drivers/gpu/drm/amd/` y esas cabeceras están en `include/asic_reg/`,
    `include/drm/` e `include/uapi/`.  Las siete resuelven, y las tres de GMC
    apuntan a `mmVM_CONTEXT8_PAGE_TABLE_BASE_ADDR` y `mmVM_INVALIDATE_REQUEST`
    Es la SEGUNDA vez que un instrumento culpa al artefacto de un fallo del
    instrumento
  · traducía comparando contra 7.2.8, y salía todo NO_UNIQUE_MATCH.  Comparar
    texto de 7.1.3 contra 7.2.8 no es traducir: es un error de categoría
  · clasificaba el fichero entero como intraducible en cuanto UNA línea no
    mapeaba, y tiraba las que sí.  La comprobación directa dio +12 exacto en las
    cuatro líneas de amdgpu_vm.c
  · y quité un umbral arbitrario que separaba COLLISION a 2 subsistemas de
    UNIDENTIFIABLE a 3 o más: un número en medio de un solo hecho
VALIDACIÓN  20 checks, 0 fallos.  Los que importan:
  · copias que discrepan DENTRO de una versión -> FRAGILE, no «roto»
  · copias de versiones distintas que difieren -> VERSIONED, y no es defecto
  · nombre en subsistemas sin relación -> UNIDENTIFIABLE, no «resuelto contra la
    que casualmente era lo bastante larga»
  · una sola copia larga suficiente -> UNIQUE, no ROBUST: «todas coinciden» sería
    cierto en vacío
  · el corpus NO se escanea: sólo el texto propio de este proyecto
  · una raíz ausente se DECLARA ausente, nunca se salta en silencio
  · un fichero con bytes no-UTF-8 resuelve, o la herramienta inventaría defectos
  · la herramienta no tiene ruta de escritura; y las del self-test sólo caen en su
    propio tempdir, y lo borran
  · se traduce cita a cita: una línea que no mapea no invalida las que sí
  · y se ejercita el camino de INFORME con `analyse()` y `main --json`.  La primera
    versión tenía 12 checks de las primitivas y se rompía en el primer uso real
    con ValueError, porque ninguna lo llamaba
```

---

### R-24 · `snapshot.py`: sellar PRE-STATE · POST-STATE · DIFF, y photographing la iGPU por error

```
WHEN      instrucción de automatizar; el hueco era el ciclo de experimentos
EL HUECO, y es el único que no estaba bloqueado
  de los diez campos del registro de experimento, tres son automatizables HOY sin
  tocar la GPU:  PRE-STATE · POST-STATE · DIFF
  EXECUTE y la captura sobre el ASIC están BLOCKED_BY_AUTHORIZATION y no se tocan
  y esos tres no existían, así que cada experimento registrado hasta ahora escribió
  PRE-STATE y POST-STATE DE MEMORIA, que es la única forma de que no sean
  comparables
LA PROPIEDAD QUE LA SOSTIENE, y es la única que importa
  el hash cubre SÓLO los hechos estables.  Volátiles se registran y no se comparan,
  porque compararlos produce diferencias que no son diferencias
      dos capturas con 1 s de diferencia dan el MISMO stable-id
  sin eso el diff de dos instantes informa de decenas de cambios del reloj
LO QUE LA ARBITRA CONTRA EL KERNEL, y por qué esta herramienta valida distinto
  todas las demás validan contra fixtures: entrada fija, salida fija.  Aquí no puede
  funcionar, porque se lee estado VIVO.  La única forma de saber si se leyó el
  dispositivo correcto es preguntarle a algo que lo leyó por separado
      AGREE 3 · DISAGREE 0 · NO_KERNEL 0
      subject_bdf 0000:01:00.0   <- coincide con `lspci -D -d 1002:699f`
      subject_device_id 0x699f   <- coincide con `POLARIS12 0x1002:0x699F`
DOS DEFECTOS QUE NADIE PODRÍA VER SIN ESA SEGUNDA FUENTE
  LA IGPU.  Elegía la primera tarjeta alfabéticamente, y card0 es una Intel HD 4600
  0x8086:0x0412 en el bus de la CPU, driver i915.  La RX550 es card1, 0x1002:0x699f
  y lo grave no fue el valor equivocado sino el SILENCIO: vram_total, pp_dpm_sclk y
  gpu_busy_percent no se registraban porque no existen en el nodo equivocado, y nada
  decía «no miré el dispositivo correcto».  Sólo parecía una máquina tranquila
  Ahora la ausencia se ESCRIBE `<ausente>` y se CUENTA, y la regla de selección queda
  escrita dentro del registro: `subject_selection = vendor=0x1002, unica coincidencia`
  EL PUENTE.  realpath da /sys/devices/pci0000:00/0000:00:01.0/0000:01:00.0 y la
  búsqueda cogía la primera, así que la RX550 salía como 0000:00:01.0
  una dirección REAL que nombra otra cosa, y nada en el valor lo delata
  Es la misma forma del fallo que una LOCATION plausible, y por eso el check es
  contra lspci y no contra el propio código
  Y el caso ambiguo se declara ambiguo: con dos AMD la herramienta NO elige
TRES MÁS, de otra clase
  95 claves fantasma: `amdgpu_params` era un hecho multi-línea y el parser leía cada
  una de sus 95 líneas como un hecho.  Una instantánea de 15 se leía como 110, y como
  los fantasmas eran ESTABLE entraban en el hash y en el diff: cambiar UN parámetro
  salía como 95 añadidas y 94 quitadas, indistinguible de una máquina reconstruida
  una adivinanza mía: `endswith("=0")` clasificaba
  pp_dpm_force_performance_level=0 como «por defecto», pero 0 significa AUTO, y AUTO
  es deliberado.  Saber el default exige la fuente del kernel
  una constante definida DOS VECES: STABLE_PREFIXES, y la segunda pisaba a la primera
  y borraba el prefijo drm. en silencio.  Arreglado con un check que parsea su propio
  AST y falla si un nombre está definido dos veces
UN SEXTO DEFECTO, y era el que impedía usar la herramienta
  `tools_git_head` estaba dentro del hash.  Es estable en el sentido de que no se
  mueve solo, pero no es el sujeto, y bajo concurrencia otra sesión commitea varias
  veces por hora
  MEDIDO: el id pasó de `59e11a3ef7928751` a `73a35f813db8dc35` sin que la GPU moviera
  un byte.  Ese par de diferencias es justo el que la ronda siguiente tiene que separar
  Y el arreglo tiene una parte que importa más que la otra: el filtro de CONTEXTO vive
  DENTRO de la función que calcula el id, no en quien la llama.  Con el filtro en el
  llamante la propiedad se cumplía sólo por ese camino, y el primer test lo demostró
  fallando: llamar a la función directamente hashearía el contexto
  una guarda que se puede esquivar usando la función correcta no es una guarda
  ahora se emiten dos ids, hardware y contexto, y sólo el de hardware responde a
  «¿cambió el estado?»
VALIDACIÓN  30 checks, 0 fallos.  Los de la parte que no es de hash:
  · el sujeto es la RX550, no la primera tarjeta, con card0 como iGPU delante
  · sin dispositivo AMD no hay sujeto, y lo dice
  · con dos AMD es AMBIGUO y no se resuelve por suerte
  · la selección no depende del orden de enumeración  <- que era el bug
  · el conteo de ausentes coincide con las facts realmente ausentes
  · toda tarjeta DRM queda en el registro, incluida la NO elegida
  · la BDF es la última del camino PCI, no el puente
  · la BDF coincide con lspci
  · la tabla de arbitraje sólo contiene pares COMPARABLES: vram queda fuera a
    propósito, porque sysfs y el kernel lo nombran distinto
LO QUE ESTA NO HACE, y es la línea
  registra, no afirma.  Y diff dice que dos estados difieren; por qué, y cuál
  diferencia causó qué, no está en la instantánea ni puede estar
ESTADO INICIAL  baseline de HARDWARE `bbf909eddd8c2cda`  ·  contexto `73a35f813db8dc35`
  127 hechos · 125 en el hash · 5 volátiles
  sirve para que la próxima ronda pueda decir, con un diff, si algo se movió
```

---

### R-23 · `--locate`: traer las líneas no es elegirlas, y la primera claim que eso cerró

```
WHEN      instrucción de automatizar; el defecto medido más grande que quedaba era
          RE-49, 24 claims sin LOCATION
EL REPARTO, y por qué sólo se automatiza la mitad
  cerrar RE-49 exige dos cosas:
    TRAER   qué ficheros:línea ofrece la evidencia que la claim ya cita
    ELEGIR  cuál de ésos es LA línea de ESTA afirmación
  La primera es mecánica.  La segunda es conocimiento, y una LOCATION equivocada es
  indistinguible de una correcta: gmc_v8_0.c:691 y :702 son líneas reales sobre los
  flags del PTE, y elegir entre ellas a máquina sería inventar un rastro de auditoría
  Así que `claim.py --locate` trae candidatos y se calla
UNA CORRECCIÓN MÍA, y es el punto
  dije, y como si fuera una medición, que 15 de las 25 claims sin LOCATION citaban un
  finding que ya declara sus localizaciones.  Medido al construir la herramienta: 0
      FETCHABLE    0   el finding citado DECLARA un bloque LOCATION
      ADVERTISED  11   sólo menciona fichero:línea: quedan como candidatos
      MANUAL      14   nada resoluble sin leer el corpus
  Dar 15 donde la verdad era 0 es exactamente el fallo que la herramienta existe para
  evitar.  Decir una estimación como si fuera una medida es la forma más común de
  fabricar evidencia, y la he estado cometiendo yo
LO QUE CERRÓ, y es la claim que más dolía
  RE-10  "Geometría de page table de Polaris12, cerrada numéricamente"
        la más citada del registro, la que zanjó C-003 y C-009, sin ni una línea
  seis candidatas ofrecidas, tres elegidas leyéndolas en el corpus:
    gmc_v8_0.c:1127   amdgpu_vm_adjust_size(adev, 64, 9, 1, 40)
                      las ENTRADAS, argumento LITERAL: la línea más fuerte posible,
                      porque no hay nada que derivar
    amdgpu_vm.c:2424  roundup_pow_of_two(max_pfn)          = 2^24
    amdgpu_vm.c:2427  DIV_ROUND_UP(fls64(tmp)-1, 9) - 1    = 2   <- REASIGNA
    amdgpu_vm.c:2428  num_level = min_t(..., max_level, tmp) = 1
    amdgpu_vm.c:2429  switch(num_level)  case 1 -> root_level = PDB0
    amdgpu_vm.c:2454  block_size = get_block_size(tmp)             <- tmp = 2
    amdgpu_vm.c:2463  el dev_info que la arbitra
  Y la herramienta NO hizo esa elección.  Decidir que 1127 es la ENTRADA y no un
  argumento más requiere entender que los argumentos de adjust_size son el origen de
  toda la cadena
UN EFECTO COLATERAL QUE NO BUSCABA
  la lista corta de RE-10 hace evidente por qué las tres cifras de block_size de la
  mañana eran posibles: con la línea 2454 a la vista, `tmp` ahí es 2 y no 2^24, y el
  error de 022 era un `tmp` equivocado, no una aritmética difícil
  Es decir: hacer auditable una claim la volvió explicable
LO QUE NO SUBE EL ABSOLUTO, y hay que decirlo
  SIN LOCATION sigue en 24, de 48 claims.  Antes eran 24 de 47
  no bajó porque cerré RE-10 pero añadí RE-49, que es una meta-medición y por su
  naturaleza no tiene LOCATION: no hay fichero:línea del corpus que la localice
  El número absoluto de claims no auditables sólo baja registrando evidencia nueva, no
  moviendo las que ya había
Y UN HUECO MÍO EN LA NUMERACIÓN, que la herramienta también reporta
  `siguiente libre RE-45`, y `RE-45`, `RE-46` nunca se usaron: yo asigné 47, 48 y 49
  saltándome dos.  Renumerar ahora rompería las referencias del registro, así que el
  hueco se queda y se declara.  `claim.py` reporta los huecos, que es para eso
VALIDACIÓN  16 checks, 0 fallos.  Los cuatro de --locate:
    · FETCHABLE sólo si el finding DECLARA un bloque LOCATION
    · ADVERTISED si sólo lo menciona, y los dos casos NO se confunden
    · MANUAL si no hay nada, y no se propone nada
    · una claim que ya tiene LOCATION no recibe trabajo
```

---

## Historial de la línea A — cambios de conocimiento del 2026-10-01

Reconstruido desde `git log`. Cada commit es un cambio de estado; los commits
intermedios no se listan porque no cambiaron conocimiento.

```
ce88b5f  10:34  022  COND_EXEC en GFX8 se emite con un predicado que nadie puede poner
                  a falso
                  OLD: (no había análisis de COND_EXEC)
                  NEW: PROVEN que no puede descartar. Los 20 call sites que bajan el
                  predicado a 0 son de preemption; GFX8 no tiene preemption
                  DEP: RE-09  UNLOCKS: nada (cierra una pregunta)
                  RISK: se pensaba que era un no-op de 5 dw; el análisis real resultó
                  ser sobre qué campo lee el hardware, que queda NOT_DETERMINED

c39d31a  10:28  021  emit_frame_size de GFX8 reserva el peor caso
                  OLD: se leía la aritmética sin más
                  NEW: 172 dw (GFX) y 109 (compute) declarados; ni uno es el tamaño
                  que una submission escribe. CE_META y DE_META reservan chained_ib
                  (14 y 31) cuando el activo es regular (8 y 21), y ambas están
                  condicionadas a amdgpu_sriov_vf = falso en esta placa
                  DEP: RE-06  UNLOCKS: saber que el presupuesto del driver propio es
                  una cota, no el caso activo

c0b0e56  10:12  020  el presupuesto del vm-flush excede en 5 lo que se escribe
                  OLD: dos sesiones habían contado a mano y daba 7 dw y 6 dw
                  NEW: declarado - real = (3 - 2) * 5 = 5 dw, y la causa está en una
                  línea: VI_FLUSH_GPU_TLB_NUM_WREG = 3 en vi.h:27 frente a 2 llamadas
                  reales a emit_wreg en gmc_v8_0_emit_flush_gpu_tlb. KIQ declara 17 a
                  mano y coincide exacto, lo que confirma que el excess viene de la
                  constante
                  DEP: RE-07  UNLOCKS: los 19/17 dw reales son lo que el driver propio
                  debe reservar. Sobre-reserva es correcto; ningún ring está
                  infra-reservado
                  RISK: el primer intento usó la regla "1 + n" y produjo -8, un
                  resultado imposible. Queda registrado porque el error era plausible

c7818c6  10:52  023  la convención n = payload - 1 de PACKET3, medida
                  OLD: tratada como observación en dos o tres paquetes (020, 022)
                  NEW: propiedad medida. 68/68 emisiones contables del path GFX8;
                  170/171 del árbol amdgpu completo. Herramienta con --only=fx8 que
                  marca UNKNOWN con su motivo en vez de inventar números
                  CORRECCIÓN A 022: dw4 de COND_EXEC NO es "un dword extra fuera del
                  payload". Es el cuarto payload. Era una suposición sobre la convención
                  DEP: RE-08  UNLOCKS: confirma el conteo de 020 y cierra los dos casos
                  que 020 y 022 habían dejado como "a verificar"
                  NEGATIVE_RESULT heredable: gfx_v12_1.c:3371 emite SET_CONFIG_REG,1 con
                  1 solo payload donde los otros cinco sitios escriben 2. Inconsistencia
                  real upstream, en GFX12.1, fuera de nuestra placa
                  LO QUE NO RESUELVE: la semántica. Medir que el encoding es coherente
                  no dice que el hardware lo interprete así. Mismo patrón que 017
                  VALOR DE LA DISCIPLINA: el criterio tuvo que endurecerse DOS veces.
                  "-1 presente en la distribución" se cumplía con 1 de 172 y salía
                  rc=0. Un filtro relajado contó a través de las ramas y produjo una
                  distribución sin dominante: síntoma de atribuir payload al paquete
                  equivocado

2599c65  10:52  feat(geom)  gfx8vmgeom — la geometría GPUVM de Q1 era incorrecta
                  OLD: 014-q1 cerraba Q1 con BITS_PER_LEVEL=9, GPUVA_WIDTH_BITS=30,
                  MIN_VIABLE_ASPACE=2 MiB, los tres PROVEN
                  NEW: los tres falsos. block_size=10 -> PTB 1024 entradas (8 KiB, no
                  4 KiB), unidad mínima 4 MiB (no 2), GPUVA 36 bits (no 30), PDB0
                  16384 entradas = 128 KiB (no 512 = 4 KiB)
                  CAUSA: se citaba la rama `else if (num_level > 1) block_size = 9;`,
                  que no corre porque max_level=1 da num_level=1. Y el else pasa tmp,
                  no vm_size
                  EVIDENCIA: la cadena derivada coincide con la línea que el host
                  imprimió en el boot. Es una verificación independiente del código
                  DEP: RE-10, C-005  UNLOCKS: la geometría completa del driver propio
                  12 controles negativos, 0 muertos

d06af34  10:57  024  geometría del page table en GFX8, cerrada de extremo a extremo
                  OLD: la geometría estaba "estructuralmente cerrada" sin valores
                  NEW: cerrada NUMÉRICAMENTE. num_level=1, root_level=PDB0,
                  max_pfn=16777216, PAGE_TABLE_DEPTH 0 vs 1 por contexto,
                  PAGE_TABLE_BLOCK_SIZE no se escribe para el contexto 0
                  REFUTA: la mitad de DRIVER-MISSION-STATE.md ("plano por necesidad")
                  CORRECTION_OF_PROVENANCE (023-pte §4): los headers GMC citados eran
                  gmc_8_2_d.h cuando la ASIC-correcta para gmc_v8_0.c es gmc_8_1_d.h.
                  15/15 offsets coinciden, ninguna conclusión cambia
                  DEP: RE-11, RE-12, C-006
                  ERROR PROPIO, registrado: §2.3 usa get_block_size(vm_size) donde el
                  código pasa tmp. Da 13 en vez de 10 -> C-003

2a6485f  11:05  025g la ruta GART, donde el invalidate sí tiene completion observable
                  OLD: (017/018 dizían "no hay completion", y así se leía)
                  NEW: eso es del path de RING. Hay un SEGUNDO path, ejecutado por la
                  CPU: amdgpu_gart_invalidate_tlb() con mb() + flush_hdp. Cuando la
                  función vuelve, la escritura del registro ya salió. No requiere
                  hardware nuevo
                  DEP: RE-13  UNLOCKS: un punto de entrada para el invalidate con
                  completion real, que es lo que el path de ring no tiene
                  NO CONTRASTE 017/018: son paths distintos y 025 lo acota bien

5fa4826  ~11:15  026p el PTE de GFX8: 40 bits de PA por tres vías, flags sólo por
                  comentario
fc11d1e  ~11:25  027  el PTBA: una sola aritmética, de la ioctl al registro
                  OLD: AGENTS.md daba "PTBA software production cerrada" sin la
                  aritmética
                  NEW: vm->root.bo -> amdgpu_gmc_pd_addr(bo); asic_type(17) >=
                  CHIP_VEGA10(19) es FALSO, luego pd_addr = amdgpu_bo_gpu_offset(bo).
                  Una sola operación, sin código condicional
80fbd9e  ~11:38  028  frontera D: el fence SÍ tiene completion, y cambia en cada
                  generación
                  OLD: "el hardware no confirma nada" era la lectura tácita
                  NEW: el fence es el ÚNICO punto del path de submit donde el hardware
                  confirma que el trabajo anterior terminó. GFX emite EVENT_WRITE_EOP x2
                  (uno con seq-1, otro con seq y EOP_EXEC); COMPUTE, RELEASE_MEM x1
                  DEP: RE-18  CIERRA PARCIALMENTE F1: responde por el trabajo, no por
                  el invalidate. La distinción es el valor del hallazgo
                  NO CONTRASTE RE-02: son dos preguntas

Y en la misma franja, sin commitear al cierre de esta ronda:

  024p  pm4dw recibe modo --path, que RESUELVE COMPOSITION y --struct no puede.
        Documenta el defecto que la herramienta se destapó: LOOKAHEAD_LINES 3 hacía
        salir ABSENT una función que existe en gfx_v8_0.c:5122 y vale 20 dw
  025v  la ruta de amdgpu_vm_flush son 63 dw, y las CUATRO ramas coexisten de hecho:
        las condiciones son campos distintos del job, sin exclusión mutua. El conjunto
        máximo no es una cota teórica, es alcanzable
        Y un hallazgo de diseño: emit_cleaner_shader es NULL en Polaris12, luego es un
        predicado permanentemente falso. Elimina una rama entera del espacio de diseño
  026f  la fórmula de reserva está escrita en amdgpu_ib.c:197-198:
        alloc_size = emit_frame_size + num_ibs * emit_ib_size. El frame son 121 dw
        (137 con chained IB) y write_multiple emite 17, no 1
  029   por qué RELEASE_MEM no necesita seq−1 en GFX8: es estructural, no paramétrico.
        El paquete no tiene dónde llevar el número
```

## Historial de la línea B — cambios de conocimiento del 2026-09-29

```
b8294b1  00:44  AD-12 (hardware BC3) NOT_DETERMINED. El proyecto queda con dos
                 dos cuestiones separadas: lo que dice la spec y lo que hace el hardware
b7ed0c1  01:10  el push constant faltaba; el test daba SIGSEGV. AD-14 corrige el
                  diagnóstico. La limitación #1 sigue diciendo "NO pasa"
7ed1eca  01:17  AD-13 -> COMPLETE. 0 de 4096 en 3 corridas. Los tres defectos
                  documentados, incluido que la primera corrida fue una ejecución
                  afortunada. shader_vs_c dio 0/4096 con los tres presentes
                  *** La cabecera se actualiza; las limitaciones NO. De ahí C-001
49bd550  02:24  F4-AD-12..15. Se corrige una limitación FALSA: se había escrito que
                  spirv-val no estaba instalado. Está en /usr/bin, SPIRV-Tools
                  v2026.1, rc=0. Escribí que faltaba; era falso
95984c4  01:45  CIERRE_PROYECTO.md: fecha sin expandir, limitación SPIR-V falsa,
                  throughput desactualizado, commits AD-15 ausentes
```

## Patrones de este registro, para quien lo lea después

```
1. DOS SESIONES CONTARON LO MISMO A MANO Y SALIERON CIFRAS DISTINTAS (020: 7 dw y
   +5, frente a 6 dw y +6). Eso forzó la herramienta pm4dw, que además se demuestra
   que falla con un mutante. La Lesson: cuando dos personas cuentan lo mismo a mano,
   la respuesta es una herramienta, no un arbitraje

2. UN FINDING CORRIGE A OTRO DEL MISMO DÍA, Y ESTO ES NORMAL Y BUENO. 023-pm4-count
   corrige a 022 §4; 023-pte corrige la cabecera de 017/018/019; 024 refuta a
   014-q1; gfx8vmgeom refuta a 014-q1 por otra vía

3. LO MÁS VALIOSO QUE HAY EN CADA COMMIT ES LO QUE NO SE AFIRMA. 017 dice qué no
   prueba. 018 dice qué no se puede hacer. 023-pm4-count declara 22 no contables.
   024 nombra la causa de su propio N/D. El avance del proyecto está en los límites,
   no en las cifras

4. EL ERROR DE ESTE REPO, CUATRO VECES, ES EL MISMO: HEREDAR UNA AFIRMACIÓN DE UN
   DRIVER O DE UN DOCUMENTO Y TRATARLA COMO PROPIEDAD DEL HARDWARE. D-11, C-005, D-01
   de AD-15 y el régimen histórico de septiembre. D-16 (NO_HISTORICAL_INHERITANCE)
   existe por eso

5. LO QUE NO SE MIDIO SE DICE QUE NO SE MIDIO. M1 es NO DISCRIMINATIVO, no "sin
   diferencias". R-4B v2.3 es INCONCLUSIVE, nunca SUPPORTED. El régimen E1/E3/E5 es
   [NO REPRODUCIBLE], no una especificación
```

## 2026-10-02 · Ronda del log de arranque y del toolkit (segunda sesion del dia)

Sin hardware nuevo: todo lo de esta ronda sale de artefactos que ya estaban en
el arbol y no se habian mirado. `GPU INTACTA` · `WRITE_EXECUTION NONE`.

### Cerrado

- **El `count` de un paquete PM4 es el payload MENOS UNO** (`EVIDENCE-MATRIX`
  EV-30). No por lectura del codigo: por el test del anillo, observado en
  hardware. El anillo de compute empieza con la auto-prueba, y el test depende
  de que el tercer dword se ejecute; si el hardware leyera exactamente `count`,
  el test daria ETIMEDOUT y `sched.ready` quedaria a 0. El anillo esta usado,
  luego el hardware consumio los tres. `PROVEN_DERIVED`, con cadena completa
- **La regla no tiene excepciones** (EV-28, **retirada**). Las 50 emisiones de
  `gfx_v8_0.c` reconcilian, incluidas las 7 que `pm4census` dejaba `SIN MEDIR`.
  Y el veredicto de `pm4census` ya lo decia antes
- **F12b cerrada** para el ASIC de esta GPU
- **F2b, el alcance**: 15 flags de PTE con consumo demostrado en GFX8, 4
  definidos sin consumidor alcanzable y clasificados `NOT_APPLICABLE`. Lo
  resolvio `revkit/pte.py para-gfx8`, una herramienta de este mismo revkit que no
  se habia ejecutado

### Retirado, y por que

- **EV-27**: afirmaba que "el hardware lee exactamente `count`" estaba
  `REFUTED`. No lo sostiene: los dos modelos dan 11 paquetes, y lo que cae es
  tratar un tipo 0 como cabecera, que ya se sabia falso
- **EV-28**: afirmaba que `vm_flush` era el unico emisor exacto. Escribe **seis**
  payload, no cinco; el error fue mapear numeros de linea leyendo un volcado
  numerado en vez de `grep -n`
- **EV-21**: `length_dw` no es constante (344, 1104, 1488) y la alineacion no es
  `0x600` sino `0x200`. Se habia escrito mirando el primer IB
- **EV-22**: el `WRITE_DATA` ocupa **cinco** dwords, no cuatro, y su `cmd` es
  `0x40100000`, sin `WR_ONE_ADDR`
- **EV-18**: la estructura del anillo se repite; el contenido no
- **NR-2026-10-02-e**: `0xDEADBEEF` **si** esta en un anillo, el de compute. Se
  busco en uno de los cuatro

### Nuevo

- **EV-26**: `gmc_v8_0_emit_flush_gpu_tlb` es el productor del invalidate, y el
  mapeo VMID -> bit del dominio queda `PROVEN`: `INVALIDATE_DOMAIN_i` esta en el
  bit `i` en las cinco generaciones de GMC. Tambien explica por que el
  invalidate no necesita campo `FUNCTION`
- **EV-29**: el IB codifica una VA de **48 bits**, porque el emisor enmascara la
  parte alta a `& 0xFFFF`. Y sus ocho `length_dw` no son iguales
- **EV-32**: el log de arranque da las direcciones fisicas, y la tabla GART cae
  **dentro de la ventana del BAR**. Es el observador que F12 llevaba buscando
- **NR-2026-10-02-i**: 139 de los 245 ficheros sellados no tienen version detras.
  El sello detecta la corrupcion, el commit la recupera, y hacen falta los dos

### Herramientas

| | que resuelve |
|---|---|
| `revkit/sello.py` | el sello de evidencia, y un 2x2 de custodia: detecta frente a recupera |
| `revkit/klog.py` | el log de arranque como fuente, con las direcciones clasificadas por espacio |
| `revkit/pte.py` (corregido) | `dump` tenia el layout de PTE hardcodeado, sin filtro de ASIC: 36 bits donde GFX8 tiene 28 |

### La leccion que mas veces se pago

**No consultar el toolkit antes de medir.** Tres veces en la sesion, y las tres
salieron caras:

1. `pm4census.py` ya media la convencion de `count`, y monte una tabla a mano
   que lo contradecia
2. `count_vmflush_dw.py` ya contaba los dwords del vm_flush
3. `revkit/pte.py` ya cerraba el alcance de F2b, y es **mia**

Y la cuarta forma, distinta: F12 se dio por inobservable sin abrir
`journalctl -k -b`, donde estaba la direccion que la hacia observable.

Las cuatro son la misma: **el dato estaba a un comando de distancia y no se
busco**, y en las cuatro el resultado salia plausible. Un resultado plausible
que no se ha contrastado con lo que ya existe en el arbol no es un resultado.

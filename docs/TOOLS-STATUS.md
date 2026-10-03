# TOOLS-STATUS — contrato, validación y fallos

> Para cada herramienta: qué hace, con qué contrato de entrada y salida, de qué depende,
> si su salida está **validada**, y qué falla. Si una herramienta falla, su salida no se
> reutiliza como evidencia hasta que se repare.
>
> Regla que este fichero aplica sin excepción:
> `INSTALLED != USABLE` · `USABLE != VALIDATED` · `VALIDATED_OUTPUT != HARDWARE_SEMANTICS`
>
> `LAST_VERIFIED: 2026-10-01 11:20 -03:00`. Todo lo de abajo fue ejecutado o consultado
> en esta fecha, salvo donde se dice `NOT_RECHECKED`.

---

## TL-01 · `pm4_count_census.py` — VALIDATED

```
RUTA          08-ARQUITECTURA/tools/pm4_count_census.py          TRACKED en git
PROPÓSITO     Census de la convención de encoding PACKET3(op, n)
              Responde: ¿n = payload − 1 es un patrón en dos paquetes o una propiedad
              del árbol? Y NO cuenta lo que no puede contar: lo declara UNKNOWN con su
              motivo
CUERPO        gfx_v6_0.c, gfx_v7_0.c, gfx_v8_0.c, gmc_v8_0.c, sdma_v3_0.c  (--only=fx8)
INPUT         rutas de fuentes, --only, --macro
OUTPUT        1) nº de emisiones contables
              2) distribución de (n − payload) con las excepciones
              3) lista de NO contables con el motivo de cada una
              4) UNKNOWN explícito, nunca un número inventado
EXIT          0 verificado. Nadie ha visto que falle con un caso legítimo, pero el
              discriminante está en el hallazgo, no en el código
VERIFICADO    python3 08-ARQUITECTURA/tools/pm4_count_census.py --only=fx8
              ficheros barrados: 5
              emisiones PACKET3 con n literal y final alcanzable : 68
              emisiones no contables de forma estatica          : 22
              n - payload = -1 : 68 ocurrencias   <- convencion
              rc=0
CAPACIDAD DE FALLAR  mutante (payload+2) -> 1/172, rc=1
              Para llegar ahí hubo que endurecer el criterio DOS veces:
                "−1 presente en la distribución" se cumplía con 1 de 172 y salía rc=0
                un filtro relajado contó a través de las ramas y produjo una
                distribución sin dominante (7 valores) — síntoma de atribuir payload al
                paquete equivocado. La regla estricta es la correcta, y por el síntoma
LIMITACIÓN    22 emisiones NO contables [NR-06]. Dos de ellas (ce_meta, de_meta) son
              justo las que 021-frame usa para explicar la sobre-reserva de
              emit_frame_size
SUSTENTA      RE-08 · y por corroboración RE-06, RE-07
```

## TL-02 · `pm4dw.c` — VALIDATED, con dos correcciones de invocación

```
RUTA          tools/pm4dw.c                                     UNTRACKED en git
PROPÓSITO     Contar dwords que emite cada función de un path de ring, resolver a punto
              fijo el coste de los helpers, y comparar contra la reserva de
              .emit_frame_size
POR QUÉ EXISTE  Dos sesiones produjeron cifras distintas para
              gfx_v8_0_ring_emit_vm_flush: 020 decía WAIT_REG_MEM=7 dw y residual +5;
              otra decía 6 dw y +6. Ambas contadas a mano con grep. Contar a mano las
              llamadas a ring->write() es exactamente la operación que produjo el error,
              así que se mecaniza y se demuestra que falla sobre una entrada mutada
CUErPO        texto de fuente. NO abre nodos, NO escribe registros, NO ejecuta GPU
INPUT         --macro NOMBRE=VALOR (repetible)  --struct NOMBRE  --path fn1,fn2,...
              --struct-size NOMBRE  (UNO por flag)  --wm-sites  (bandera)
              ficheros .c [.h ...]
              OJO: --struct-size toma exactamente un nombre por flag. La forma con
              "=" (--struct-size=A,B) cae en la rama de opción desconocida y sale con
              el usage y rc=2. El propio código lo explica: "un loop codicioso
              'hasta la siguiente opción' se comia los nombres de fichero, porque no
              empiezan por '-'"
              Y --struct-size necesita el FICHERO QUE CONTIENE LA DEFINICIÓN entre los
              .c: el parser pasa los contenidos, no las rutas. Pasarle rutas
              reportaba NOT_FOUND para una struct que existe
OUTPUT        1) --struct : suma todos los handlers que el struct nombra. COTA SUPERIOR
              2) --path   : suma los emisores NOMBRADOS Y EN ORDEN. Es lo que compone
                           una submission. DECLARED / EMITTED / RESIDUAL / VERDICT
              3) --wm-sites : imprime cada llamada a amdgpu_ring_write_multiple() con
                           sus argumentos, literal. Convierte un subconteo en algo
                           auditable línea a línea
              4) --struct-size : tamaño de una struct del corpus, en miembros y bytes,
                           más cnt_de y el write_mult derivado
EXIT          0 OK ; 1 = infra-reserva o un nombre de --path no encontrado ; 2 uso
BUILD         cc -O2 -Wall -Wextra -o pm4dw pm4dw.c     -> SIN WARNINGS, rc=0
VERIFICADO    (a) sin --macro:       "no --macro given"                 -> uso
              (b) --macro sin '=':   "macro needs NAME=VALUE"          -> uso
              (c) --struct amdgpu_ring_funcs:
                    "no struct was checked; the input did not match"
                    STRUCT_NOT_FOUND                                   rc=1
                 -> --struct pide el NOMBRE DE LA VARIABLE inicializadora, no el del
                    TIPO:
                    --struct gfx_v8_0_ring_funcs_gfx      -> 172 / 74 / +98  OK
                    --struct gfx_v8_0_ring_funcs_compute -> 109 / 52 / +57  OK
CAPACIDAD DE FALLAR  mutante emit_wreg 5->6 dw  ->  KIQ infra-reservado, rc=1
                     mutante M4 sobre --path   ->  la ruta discriminante, verificada
DEFECTO QUE LA HERRAMIENTA DESTAPÓ EN SÍ MISMA   [025-vm-flush §6]
  gfx_v8_0_ring_emit_gds_switch salía ABSENT. NO es absent: está en gfx_v8_0.c:5122.
  La causa era LOOKAHEAD_LINES 3, y esa firma reparte SIETE parámetros en cinco líneas
  antes de la llave.
  Se sustituyó el cap fijo por una REGLA CON MOTIVO: "una declaración sólo continúa
  mientras las líneas sigan formando una lista de parámetros: sin ';' y sin línea
  vacía", con tope duro 12 como red de seguridad, no como regla.
  Un cap fijo pequeño no es una heurística honesta: es un número que no sabe por qué
  es ese.
  Lo que se conserva del cambio es la SEMÁNTICA de la etiqueta: ABSENT significa ahora
  "o no existe, o el parser no la ve", y lo reporta así a propósito. "No existe" y "no
  la veo" son hallazgos distintos, y confundirlos es el error que
  AGENTS.md §"Verify the object itself" prohíbe
LO QUE --struct NO PUEDE Y --PATH SÍ        el propio encabezado de la herramienta lo
  dice: "--path RESOLVES COMPOSITION, WHICH --struct CANNOT". La suma de handlers de un
  struct es una cota superior sobre handlers que NUNCA COEXISTEN. La ruta máxima
  alcanzable es un número distinto y menor: 63 dw, medido con --path [025-vm-flush §CUDA]
LIMITACIÓN VIGENTE   1) Los números de --struct son cota superior, no el peor caso
              2) No ve los macros definidos en cabeceras no pasadas como entrada
              3) pipeline_sync queda marcado por presencia textual de "->funcs->" en el
                 CUERPO de la función, cuando el macro está en la LLAMADA. Afecta a la
                 etiqueta de estado, no al número. `PROVISIONAL`, declarado en 025 §8
NO ES         Un sustituto de count_vmflush_dw.py / frame_budget.py en lo explicativo:
              esos dos explican el POR QUÉ con lectura manual; pm4dw automatiza el
              QUÉ. NO SE BORRAN
DEFECTO DE DOCUMENTACION PROPIA, y el más fácil de arreglar de todos los de aquí
  usage() documenta --macro, --struct y --path. NO documenta --struct-size ni --wm-sites,
  que el parser acepta (líneas 1080 y 1089). Quien lea el uso no sabe que existen
SUSTENTA      RE-06, RE-07, RE-14 (63 dw), RE-15 (121 dw) y RE-23 (censo de write_multiple)
ESTADO        pm4dw.c cambió a las 10:46, 10:48, 10:53, 11:14 del 2026-10-01 y recibió
              el modo --path y el fix de parser después. UNTRACKED, con sesión activa
```

## TL-03 · `gfx8vmgeom` — VALIDATED, y dependiente del directorio de trabajo

```
RUTA          08-ARQUITECTURA/tools/gfx8vmgeom/                 TRACKED (fuentes)
              binario gfx8vmgeom                                gitignored
PROPÓSITO     Calcular la geometría de page tables que el driver programa en una
              Polaris12, y CONTRASTARLA con la línea que el host imprimió en el boot
POR QUÉ EXISTE  014-q1 cerró Q1 GPUVM_MINIMAL declarando tres cifras PROVEN
              (BITS_PER_LEVEL=9, GPUVA_WIDTH_BITS=30, MIN_VIABLE_ASPACE=2 MiB) y las
              tres están mal, no por criterio sino por una rama del código que no es la
              que corre [C-005]
LA REGLA QUE LO HACE CREÍBLE  Ninguna constante del modelo está escrita a mano. Todas se
              extraen del corpus con una búsqueda anclada, incluida la del árbol de
              enumeración (AMDGPU_PTE_PTE = bit 54) sacada de enum amd_asic_type en vez
              de de la llave de apertura
VERIFICADO    make test   (cwd = su propio directorio)
                aserciones           37
                fallos               0
                controles negativos  12
                ...detectados        12
                ...muertos            0
                informe              0 discrepancias
                cruce de version     PROVEN (7.1.3 y 7.2.8, misma rama)
              RESULT: OK -- y el test puede fallar (12 controles negativos vivos)
              rc=0
FALLO DE INVOCACIÓN  [NR-05]  Ejecutado desde la RAÍZ del repo:
                ERROR: no se pudo cargar el corpus: amd_asic_type.h de
                ../../../RESEARCH/kernelbuild/linux-7.1.3 no coincide con el sha256 de 7.1.3
                RESULT: NO EJECUTADO        rc=2
              El sha256 que espera (cea577df…7809) es EXACTAMENTE el del fichero real.
              Lo que fallaba era la RUTA, y el mensaje de error nombra la causa
              equivocada: induce a pensar que el corpus está corrupto
              HechoRouterNO documentado en su README: "desde" no aparece como requisito
NO SE ARREGLA AQUÍ  Cambiar el README de la herramienta es edición de otra sesión
CONTROLES NEGATIVOS  12, cada uno muta una entrada y exige que el veredicto cambie. Un
              control que no detecta su propia mutación se marca [DEAD] y cuenta como
              fallo: "es peor que no tenerlo, porque aparenta cobertura"
SUSTENTA      RE-10 · C-005 · C-003
```

## TL-04 · `semref` — INVALID

```
RUTA          08-ARQUITECTURA/tools/semref/semref                UNTRACKED en git
PROPÓSITO     Responder "¿dónde se invoca X y desde qué función?" clasificando cada
              sitio como DEFINITION o CALL. La clasificación es lo que grep no puede
              hacer: grep cuenta la definición y las llamadas con el mismo número
POR QUÉ EXISTE  Al cerrar P-8, una enumeración por grep había encontrado los callers de
              amdgpu_fence_process pero no había seguido su efecto. grep sí veía la
              llamada; lo que faltaba era exhaustividad y cierre semántico
DEPENDENCIAS  ctags del sistema  +  Coccinelle (spatch)
              SEMREF_HOME  prefijo de la instalación local, por defecto /tmp/opencode/tools
VERIFICADO    ./semref engines
                ctags       DISPONIBLE  /usr/bin/ctags  (Universal Ctags 6.2.1)
                coccinelle  ENGINE-NOT-AVAILABLE  (/tmp/opencode/tools/usr/lib64/
                            coccinelle/spatch no ejecutable o libpcre ausente)
              ./semref refs amdgpu_fence_process --root <árbol amdgpu>
                ENGINE-NOT-AVAILABLE: falta ctags o coccinelle; no se degrada en silencio
                rc=3
              ./tests/run-bench
                ENGINE-NOT-AVAILABLE: falta ctags o coccinelle.
                El benchmark NO se ejecuta y NO se da por aprobado. Resultado: NOT_RUN
CAUSA         /tmp/opencode/tools NO EXISTE. La instalación se perdió. spatch necesita
              además libpcre.so.1, que no está en el sistema base
DEFECTO DE DISEÑO  [NR-04]  El gate de `refs` y `chain` es engine_state() sin argumentos:
              devuelve no-cero si falta CÓMOQUIER motor. ctags por sí solo no habilita
              el comando. Con la instalación actual semref no hace NADA — no es
              "degradado", es inútil
LO QUE ESTÁ BIEN  El comportamiento de fallo es el correcto: exit 3 y NOT_RUN, nunca un
              PASS vacío. Un tool que devuelve vacío cuando le falta una dependencia es
              peor que uno que falla
LO QUE FALLA EN EL DISEÑO  "No degrado en silencio" y negarse a usar la mitad de lo que
              se tiene sí es degradar en silencio: degrada al resultado esperado. Y el
              README declara que semref no resuelve punteros a función (tres patrones
              fallaron), o sea que la mitad de ctags no le bastaba para lo que promete
NO RESUELVE  Punteros a función. Declarado, no escondido
GARANTÍAS QUE DECLARA  Nunca escribe en el árbol (Coccinelle sin --in-place, sobre
              copias en /tmp) · control negativo explícito (símbolo inexistente ->
              SIN-MATCH) · chain declara "sin expansión en nivel N" en vez de fingir
REPARACIÓN     Reinstalar Coccinelle desde el RPM en un prefijo PERSISTENTE (/opt o
              $HOME), no en /tmp. Frontera F9. NO APLICADA: es instalación de software
SUSTENTA      015 (llvmpipe pairs), P-8 — ambos producidos cuando la herramienta
              FUNCIONABA, así que su valor persiste; lo que no vale es reejecutarla
```

## TL-05 · `validate_rx550_final.py` — VALIDATED

```
RUTA          tools/validate_rx550_final.py                      TRACKED
PROPÓSITO     Captura read-only del estado del host. Sólo lee; no ejecuta workloads
VERIFICADO    python3 tools/validate_rx550_final.py               rc=0
              Emite JSON con:
                "validation_status": "OBSERVED"
                "writes_to_system": false
                target: pci_id 1002:699f · expected_bdf 0000:01:00.0
                servicios: sys-tuned inactive, kalm-gpu.service not-found,
                           irqbalance enabled
                storage: root /dev/sdb3 ext4 rw,relatime · smart_checked false
ES SEGURIDAD, NO HERRAMIENTA  Es la que produce CURRENT-STATE.md §1-§2. Su
              "writes_to_system": false es la afirmación que hay que releer antes de
              confiar en cualquier salida de este repo
SUSTENTA      CURRENT-STATE.md §1, §2
```

## TL-06 · `evidence_search.py` — FUNCIONAL, sin demostrar que falle

```
RUTA          tools/evidence_search.py                            UNTRACKED
POR QUÉ EXISTE  La causa de CUATRO NOT_FOUND falsos en este proyecto fue la misma: se
              buscó en un subárbol extraído y se concluyó ausencia. El material estaba
              en el propio repo, en otro sitio
LO QUE HACE, POR CONSTRUCCIÓN
  · El universo de búsqueda es un ARGUMENTO explícito, no un efecto colateral del cwd
  · Un conjunto --expect declara qué DEBERÍA contener el corpus. Lo que se esperaba y
    no estaba se reporta UNREACHABLE
  · Sin hits, la clasificación por defecto es NOT_DETERMINED + [NO ABSENCE CLAIM]
  · NOT_FOUND sólo se emite con universo EXHAUSTIVO, es decir, UNREACHABLE vacío
  · Un ledger en JSON recuerda cada ejecución; una búsqueda posterior sobre un universo
    mayor sabe decir qué raíz cerró el caso y por qué cambió la clasificación
LO QUE ESTÁ BIEN  "Nada de esto es una convención: es la salida por defecto"
LACUNA  No tiene test de fallo registrado [NR-09]. No se ha visto que rechace nada. Es
  la misma debilidad que este repo ya sufre en otros sitios: un test que nunca se ha
  visto fallar no prueba que detecte
ACCIÓN SUGERIDA  Reconstruir uno de los cuatro NOT_FOUND falsos con la herramienta y
  comprobar que ahora da NOT_DETERMINED en vez de ausencia. Eso la valida
SUSTENTA      El principio de NR-09 y la regla de no declarar ausencia sin universo
              exhaustivo
```

## TL-07 · `count_vmflush_dw.py` y `frame_budget.py` — TRACKED, PARTIAL

```
RUTA          08-ARQUITECTURA/tools/count_vmflush_dw.py
              08-ARQUITECTURA/tools/frame_budget.py                ambos TRACKED
PROPÓSITO     Los dos primeras herramientas de conteo del proyecto. Leen fuente
SUPERADOS PARCIALMENTE por TL-02 (pm4dw), que automatiza lo que ellos hicieron a mano
LO QUE NO SUPERAN  La explicación. 021-frame explica POR QUÉ ce_meta reserva chained_ib
              y por qué sólo si amdgpu_sriov_vf. pm4dw no puede explicar eso: marca
              write_multiple como NOT EXPANDED y ya [NR-07]
NO SE BORRAN  Sus findings (020, 021-frame) se apoyan en ellos
```

## TL-09 · `pteflags` — VALIDATED, sin README y dependiente del cwd

```
RUTA          08-ARQUITECTURA/tools/pteflags/                    UNTRACKED en git
              (8 fuentes + Makefile; sin README.md)
PROPÓSITO     Censo de los PRODUCTORES de flags de PTE en GFX8/Polaris12: qué
              productor escribe qué bit, y qué significa que un bit no se escriba
POR QUÉ EXISTE  es la frontera A de AGENTS.md ("PTE/PDE → encoding → bits → flags")
              resuelta como censo y no como lectura. Distingue tres estados que una
              lectura a ojo no separa:
                WRITTEN          alguien lo pone
                CLEARED_NOT_SET  alguien lo borra explícitamente y nadie lo pone
                OTHER_GEN        sólo lo escribe otra generación
MÉTODO        preprocesa la TU real de gmc_v8_0.c con los -I del build, y rastrea la
              cadena de escritura. NO abre nodos, NO escribe registros, NO ejecuta GPU
VERIFICADO    ./pteflags   (cwd = su propio directorio)
                aserciones           19
                fallos               0
                controles negativos  5
                ...detectados        5
                ...muertos           0
                informe              0 lineas incoherentes
              RESULT: OK -- y el test puede fallar      EXIT_REAL=0

LO QUE PRODUCE, y es el valor
  AMDGPU_PTE_PRT      bit 51  CLEARED_NOT_SET   nadie: gmc_v8_0_get_vm_pte lo LIMPIA
  AMDGPU_PDE_PTE      bit 54  WRITTEN           amdgpu_vm_pt.c:689
  AMDGPU_PTE_LOG      bit 55  OTHER_GEN         sólo gmc_v10_0.c:513 y v11_0.c:504
  AMDGPU_PTE_TF       bit 56  OTHER_GEN         sólo v9_0 / v10_0 / v11_0
  AMDGPU_PTE_NOALLOC  bit 58  OTHER_GEN         sólo v10_0 / v11_0
  AMDGPU_PDE_BFS      bit 59  OTHER_GEN         sólo amdgpu_gmc.c:1169, dentro de init_pdb0
  AMDGPU_PTE_IS_PTE   bit 63  OTHER_GEN         sólo gmc_v12_0.c
  Y escribe: VALID, SYSTEM, SNOOPED, READABLE, WRITEABLE, EXECUTABLE

EL CONTRASTE QUE HACE QUE EL CENSO SIGNIFIQUE ALGO
  MTYPE_UC en la TU de gmc_v8_0.c   NO
  MTYPE_UC en la TU de gmc_v9_0.c   SI
  gmc_v8_0_get_vm_pte existe        SI
  LECTURA: el contraste discrimina. No es que el codigo GFX8 decida no escribir
  MTYPE: es que el simbolo NO EXISTE en su unidad de traduccion, luego no podria
  escribirlo aunque quisiera. No es una omision del driver.
  Sin ese contraste, "MTYPE no se escribe en GFX8" seria NOT_FOUND sin informacion.

LO QUE EL CENSO NO ESTABLECE, y lo dice el propio binario
  "Que el hardware de GFX8 interprete alguno de estos bits. Este documento afirma
   QUE ESCRIBE EL DRIVER, no que signifique. La semantica de hardware de cada bit
   sigue NOT_DETERMINED."
  Es la misma disciplina que pm4_count_census (RE-08) y que 017 (RE-01). La disenten
  tres herramientas distintas
CAPACIDAD DE FALLAR  5 controles negativos, los cinco detectados:
  CN-1 raíz inexistente -> sin salida parcial
  CN-2 enum que no es macro (MTYPE)
  CN-3 conteo de token que cuenta prefijos
  CN-4 cabecera que exige la barra inicial
  CN-5 censo sobre árbol inexistente
LO QUE RESUELVE, Y LA RAZÓN DE EXISTIR DE ESOS DOS CAMPOS
  --struct-size convierte en automática una cuenta que 026-frame §3 hizo a mano desde
  vi_structs.h. La razón está escrita en el propio finding: "Eso es una dependencia de
  criterio humano justo en el número que más se cita. Si alguien cambia la struct, el
  número se mueve solo." Y se mueve solo: medido el 2026-10-01 12:1x
      vi_ce_ib_state                4 miembros  16 B    cnt 6    write_mult  4
      vi_ce_ib_state_chained_ib   10 miembros  40 B    cnt 12   write_mult 10
      vi_de_ib_state               17 miembros  68 B    cnt 19   write_mult 17
      vi_de_ib_state_chained_ib   27 miembros 108 B    cnt 29   write_mult 27
  Verificado contra el código, que dice exactamente
      cnt = (sizeof(payload) >> 2) + 4 - 2
      amdgpu_ring_write_multiple(ring, &payload, cnt - 2)
  y una emisión de 4 dwords de cabecera (PACKET3 + config + addr lo + addr hi). De ahí:
      CE_META activo = 4 + 4  = 8    CE_META declarado = 4 + 10 = 14
      DE_META activo = 4 + 17 = 21   DE_META declarado = 4 + 27 = 31
  que son exactamente las cifras que 021-frameDedujo A MANO el 2026-10-01 10:28
  CORROBORATION, no duplicación: dos métodos independientes, mismo resultado en las
  cuatro cifras
DEPENDENCIA FUNCIONAL  requiere kernelbuild/linux-7.1.3 CON los -I reales. El buffer de
  comando es de 64 KiB porque "un -I truncado seria un fallo de preprocesador con el
  diagnostico equivocado" -- decision correcta y razonada
FALLO DE INVOCACION  [NR-05, el MISMO que gfx8vmgeom]
  desde la raiz del repo:
    ERROR: no se pudo ejecutar el censo: no se pudo leer amdgpu_vm.h
    RESULT: NO EJECUTADO                EXIT_REAL=2      <- el codigo de salida es correcto
  Dos cosas que importan:
    (a) depende del cwd, como gfx8vmgeom. Las raices son relativas
    (b) el mensaje nombra el FICHERO, no la RUTA. amdgpu_vm.h existe y es legible; lo
        que no resolvio es la raiz. Es el mismo defecto de diagnostico que NR-05
  La diferencia con gfx8vmgeom, y es una mejora: aqui el codigo de salida SÍ es 2, no
  0. Un CI no lo tomaria por aprobado. El defecto queda en el texto del error
SIN README  no hay README.md en el directorio. La herramienta esta sin documentar en
  su propio sitio, que es la razon de que TL-09 exista
ESTADO  UNTRACKED. La sesion que lo construye tiene el cerrojo .write-lock/pteflags y
  sus ficheros se modificaron a las 11:55, con mi ronda en curso. Documentar en caliente
  tiene riesgo de describir algo que aun cambia; por eso esto dice "VALIDATED a las
  12:0x de este dia" y no "VALIDATED"
SUSTENTA  RE-22 (flags de PTE, con estado por bit) y refuerza RE-05 (PRT)
```

## TL-08 · `kdeps.c` — TRACKED, sin validar

```
RUTA          tools/kdeps.c                                       TRACKED
PREGUNTA      ¿Se ha compilado alguna vez? ¿Se ha ejecutado? Sin registro en el árbol
ESTADO        NOT_EXECUTED / NOT_VALIDATED
NO SE USA COMO EVIDENCIA hasta que se demuestre que produce algo y que puede fallar
```

---

## TL-10 · `asic_resolver` — el gate de compilación, como comando

```
PROPOSITO  ¿este .c entra en el binario para mi ASIC, y qué ramas chip_id ejecuta?
ESTADO     SELF_TEST_OK + CROSS_CHECK_INDEPENDENT_OK  (declarado por 053)
VERSION    1.0.0
SOURCE     tools/asic_resolver.py   UNTRACKED
ARQUITECT  host x86-64, Python 3, sólo stdlib. Sin dependencias externas
SEGURIDAD  sólo clasificación de compilación. NO toca la GPU, no lee MMIO, no abre /sys

VERIFICADO POR MÍ   `--selftest` -> "asic_resolver 1.0.0 · self-test"
                     "RESULTADO OK · vectores conocidos reproducidos", rc=0
                     y la herramienta avisa ella misma, en su propia salida:
                     "NOTA: pasar esto NO valida la semantica del hardware"
                     Es el mejor contrato de herramienta que hay en este árbol

VEREDICTOS POR FICHERO
  COMPILED_UNGATED · GATED_UNDECLARED · COMPILED_GATED_ON · NOT_COMPILED_GATED_OFF ·
  NOT_REFERENCED

INPUT    --kernel RAIZ --chip CHIP_X --config K=V --universe modo --expect RUTA
         --makefile F --branches F --define S      salida en texto o JSON
UNIDADES  chip_value es el índice del enum, sin unidades. CONFIG_* es booleano, no
          tri-estado. El hallazgo declara las unidades de ambos, que es lo que evita
          el error de las cuatro cifras de block_size

LO QUE RESUELVE, y es la mitad izquierda de C-011
  046 dedicated seis documentos a si_dpm.c, que NO SE COMPILA para Polaris12. Esta
  herramienta contesta esa pregunta en una línea, y convierte
  COMPILE_GATE_BEFORE_TRACE_GATE de regla recordada en comando ejecutado

LO QUE RESUELVE ADEMÁS, y es el segundo error caro de esa misma sesión
  050 afirmó que la rama `chip_id == CHIP_POLARIS10` era "la nuestra". La herramienta lo
  detecta por máquina: CHIP_POLARIS10 = 15 y CHIP_POLARIS12 = 17
  Y cuenta: 15 de 39 ramas de smu7_hwmgr.c NO se ejecutan en nuestra tarjeta

LO QUE NO RESUELVE, y lo medí
  `grep -c "ip_block|ip_blocks" tools/asic_resolver.py`  ->  0
  No conoce el concepto de bloque de IP, y por tanto NO resuelve C-011
  Un `chip_id ==` dentro de un fichero —que es lo que sí resuelve— no es lo mismo que
  seguir el puntero `.funcs` a través de una const struct declarada en otro fichero

LIMITACIONES DECLARADAS por la propia herramienta, y por eso es creíble
  NO_EVALUA_MACRO · NO_SIGUE_CONDICIONALES · NO_DISTINGUE_MODULOS · NO_VALIDA_SEMANTICA ·
  NO_AFIRMA_ausencia_SIN_UNIVERSO

REGLAS QUE DEJA FIJADAS, y las cinco valen fuera del SMU
  COMPILE_GATE_BEFORE_TRACE_GATE          la regla sola se olvida, el comando se ejecuta
  CONFIG_IN_RHS_IS_NOT_A_GATE            un CONFIG_ como argumento NO abre puerta
  CONFIG_WITHOUT_VALUE_IS_NOT_A_VERDICT  puerta sin valor -> GATED_UNDECLARED, nunca
                                          NOT_COMPILED
  NAME_MATCH_NOT_SEMANTIC_MATCH          extends al NOMBRE DEL FICHERO, no sólo al del
                                          símbolo. polaris10_smumgr.c sirve a TRES
                                          generaciones y el nombre no dice cuál
  CODE_DEAD_IS_NOT_CODE                  código muerto no es código

POR QUÉ IMPORTA MÁS QUE LAS OTRAS TRES HERRAMIENTAS NUEVAS, y por eso va aquí
  pm4_count_census.py   cuenta sobre el corpus         · falla en silencio si el cwd
  pm4dw.c               aritmética de emisión          · usage() incompleto, TL-02
  rx550pm4val.c         estructura de un IB, sin corpus · declara su propia salida
  asic_resolver.py      ¿esto CORRE en mi ASIC?         · no toca el hardware
  Las cuatro responden a PREGUNTAS DISTINTAS. Y las tres primeras no habrían detectado ni
  el caso de 046 (fichero muerto) ni el de C-011 (bloque equivocado). Ninguna de las
  cuatro habría detectado a la otra: por eso hacen falta todas
```

---

## TL-11 · `ipsolve` — el gate que faltaba para `C-011`

```
PROPOSITO  Para UN ASIC, resolver qué .c implementa un bloque de IP, siguiendo el
           puntero .funcs.  La pregunta que contesta: ¿qué código CORRE en esta
           tarjeta, frente a qué código existe?
ESTADO     SELF_TEST_OK + CROSS_CHECK_INDEPENDENT_OK   (12/12 y 9/9, medido por mí)
VERSION    1.0.0          SOURCE  tools/ipsolve.py   UNTRACKED
ARQUITECT  host, Python 3, sólo stdlib.  Sin dependencias
SEGURIDAD  análisis ESTÁTICO de un árbol de fuentes. NO toca la GPU, no lee MMIO,
           no abre /sys, no carga módulos, no compila

VERIFICADO POR MÍ, con los tiempos y los códigos de salida
  --selftest                       12 checks, 0 fallos, rc=0
  --bootlog contra el kernel       9 de 9 bloques coinciden, rc=0    ~25 s
  --expect sdma_v3_0.c  (verdad)   rc=0
  --expect sdma_v4_0.c  (falso)    rc=4
  bloque no despachado             rc=3
  --kernel a un directorio que no existe     rc=2
  --json                           salida parseable, sin texto detrás
```

```
VEREDICTOS, que nunca se fusionan entre sí
  RESOLVED · CONDITIONAL · NOT_DISPATCHED_FOR_CHIP · NOT_DECLARED · AMBIGUOUS ·
  AMBIGUOUS_HOPS · NO_FUNCS_FIELD
  CONDITIONAL cuenta como RESOLVED para el código de salida: el despacho se encontró,
  sólo que guardado, y el guard se cita. Clasificar un despacho guardado como fallo
  haría mentir a la herramienta en el otro sentido
```

```
LO QUE RESUELVE, y es el hueco que RE-39 cerró
  C-011 no lo resolvió ningún gate.  asic_resolver contesta "¿compila?", que es la
  mitad izquierda de 046.  Faltaba la mitad derecha: ¿qué fichero ejecuta ESTE chip,
  siguiendo un puntero a través de un const struct?
  El bloque activo se resuelve en un comando:
      sdma_v3_1_ip_block -> sdma_v3_0.c,  .funcs .name = "sdma_v3_0"
      sdma_v4_0_ip_block -> NOT_DISPATCHED_FOR_CHIP, declarado en sdma_v4_0.c
  Y con --expect es una puerta de CI.  Si hubiera existido, C-011 se habría cerrado
  ANTES de que 036 escribiera el código
```

```
EL MODO QUE HACE QUE NO SEA UN JUEGO DE MANOS
  --bootlog FILE cruza los 9 bloques que el kernel declaró al arrancar contra lo que
  el corpus dice que implementa cada uno.  9 de 9.
  La expectativa NO se escribe: se deriva de la línea del kernel.  Y esto no es una
  comodidad, porque la primera vez que se verificó a mano el autor escribió
  `dce_v1_0_0` donde el kernel imprime `(dm)`, y concluyó que la herramienta había
  encontrado una discrepancia en el bloque de display.  La herramienta tenía razón.
  Era la transcripción.
  Es la CIRCULARIDAD de 038 con otro disfraz: la expectativa escrita a mano es un bug
  esperando una discrepancia que no existe
```

```
DEFECTOS QUE EL SELF-TEST ENCONTRÓ EN LA PROPIA HERRAMIENTA, que es lo que prueba que sirve
  1 la regex de campos exigía un `&` que el código sí ponía -> todo bloque salía
    NO_FUNCS_FIELD.  Lo cazó el primer self-test
  2 la contabilidad del test comparaba `<dir>/demo.c` contra `<dir>/demo.c` y daba
    resultado que no era
  3 NO MANEJABA EL FALL-THROUGH DE C, que es el patrón de vi.c:2107 y hwmgr.c:154-158.
    Eso lo hacía fallar justo en los dos sitios donde vive el caso que motiva la
    herramienta.  Ahora lo maneja, y hay un control negativo que comprueba que la
    etiqueta final de una cadena de fall-through NO hereda el bloque del que cae
  4 atribuía al caso un `if` del caso ANTERIOR: reportaba
      vi.c:2113  inside if (!amdgpu_sriov_vf(adev))   para Polaris12
    Ese `if` es el del caso TONGA y termina con `break;` en la línea 2104.  Un guard
    falso es PEOR que ninguno, porque alguien razonará sobre SR-IOV en un camino que
    no lo tiene.  Ahora sólo se atribuye un `if` que abre DENTRO de la región del caso
  5 la regex de funcs exigía que el símbolo terminara en `_ip_funcs`, y
    `amdgpu_dm_funcs` no lo hace: dio un NOT_DECLARED FALSO en el bloque que gobierna
    el display.  Es la misma lección que C-011, INVERTIDA: allí la convención de
    nombres sugería un fichero que no existe; aquí ocultaba una struct que sí
  6 indexaba por el sufijo del enum en vez del string impreso, y
    AMD_IP_BLOCK_TYPE_SMC se imprime como "smu".  La tabla se LEE de amdgpu_ip.c
  7 --json imprimía texto humano después del documento JSON, que lo hacía
    inanalizable.  Inanalizable es exactamente lo que rompe el uso en CI
```

```
RENDIMIENTO, medido tres veces mal antes de acertar
  una pasada de regex, filtrada a lo necesario             ~27 s   <- la que quedó
  una búsqueda por símbolo sobre cada fichero              3 m 20 s   peor
  una alternancia de ~500 símbolos, una sola pasada       1 m 16 s   peor
  y una versión con grupos anidados de prefijo hizo que el self-test pasara de 60 s
  Lo simple y lo rápido ganaron.  Ese orden es la lección, no el código
```

```
LO QUE NO PROBABA, DECLARADO EN EL PROPIO FICHERO
  1 lee TEXTO.  Una asignación de .funcs que venga de un macro, una cabecera incluida
    o una tabla generada no se sigue: se reporta NO_FUNCS_FIELD o NOT_DECLARED.
    Nunca adivina
  2 resuelve el DESPACHO, no la CONDICIÓN.  Si un bloque se añade dentro de
    `if (adev->flag)`, se reporta despachado con la condición citada, y NO decide si
    la condición se cumple
  3 sigue dos saltos.  Un tercero, a través de una vtable, es AMBIGUOUS_HOPS
  4 NOT_DECLARED significa "no está en el universo declarado", y el universo se
    imprime siempre.  NUNCA significa "no existe"
  5 no dice si el código resuelto es CORRECTO.  Dos implementaciones pueden existir y
    ambas compilar; esta herramienta dice cuál elige el despacho y se niega a
    clasificarlas
  6 no sustituye a asic_resolver, que contesta otra pregunta.  Medido:
    grep -c ip_block tools/asic_resolver.py -> 0.  Por eso este fichero existe
```

```
LO QUE CONFIRMÓ MECÁNICAMENTE, que es su valor real
  · C-011  el ASIC usa sdma_v3_0, no sdma_v4_0.  Con un comando, no con un argumento
  · 051    tonga_ih_ip_block -> tonga_ih.c, y no existe ih_v3_0.c
  · 046    pp_smu_ip_block -> pm/powerplay/amd_powerplay.c, o sea la ruta PowerPlay
  · y un dato NUEVO que la documentación no tenía: el bloque de display de esta
    máquina es `dm_ip_block`, con .funcs en display/amdgpu_dm/amdgpu_dm.c.  Eso sólo
    es alcanzable bajo `#if defined(CONFIG_DRM_AMD_DC)` y
    `amdgpu_device_has_dc_support(adev)`, así que DisplayCore está compilado y activo
    en este host.  En el caso VI de vi.c no hay rama `else` para dce_v10_0: si DC no
    estuviera soportado, no habría bloque de display ninguno
```

---

## TL-12 · `docscan` — la ronda de documentación, como comando

```
PROPOSITO  Convertir en comando lo que se reescribía a mano al empezar cada ronda
ESTADO     SELF_TEST_OK, 12/12 checks, 0 fallos, medido por mí
VERSION    1.0.0          SOURCE  tools/docscan.py   UNTRACKED
ARQUITECT  host, Python 3, sólo stdlib, y git para dos comprobaciones
SEGURIDAD  LEE docs/ y findings/.  No escribe nada salvo con --sync, y --sync sólo
           toca campos numéricos identificados por su nombre.  No toca la GPU

VERIFICADO POR MÍ
  --selftest        12 checks, 0 fallos, rc=0
  --repo .          defect 0 · stale 3 · review 9, rc=0
  --sync            2 campos reescritos;  segunda pasada, no-op
  --json            salida parseable
```

```
LAS SIETE COMPROBACIONES
  defect  non-latin-glyphs     clases de escritura accidental: cirílico, han, kana,
                               hangul, árabe, devanagari, formas de ancho completo.
                               Una por línea, porque cada una merece leerse
  defect  broken-md-refs       enlaces ]() a .md de docs/ que no existen
  defect  undefined-symbols    RE-nn / TL-nn / F-n / C-nn citados sin definir.  Un
                               símbolo citado antes de definirse es una promesa que
                               el árbol no ha cumplido
  stale   findings-unindexed   findings presentes en disco y ausentes del índice
  stale   counters-stale       las cifras escritas contra la realidad
  stale   evidence-freshness   HEAD real contra el registrado, y el recuento de
                               material sin versionar, que crece solo
  review  repo-paths-missing   rutas entre acentos graves que no resuelven.  Se
                               prueban tres raíces antes de reportar
  review  notation-usage       notación griega y matemática, EN AGREGADO, una vez
```

```
LO QUE NO PROBABA, y está escrito en su propio fichero
  no comprueba que una afirmación sea VERDADERA.  Nada puede.  Comprueba que sea
  internamente coherente y trazable, que es otra cosa
  no lee los findings.  Un finding con contenido contradictorio le es invisible; sólo
  comprueba su PRESENCIA en el índice
  pasar significa que la ESTRUCTURA es sólida.  El contenido puede estar mal, y los
  dos defectos más graves de hoy eran de contenido, arbitrados contra el hardware en
  ejecución
```

```
TRES DISEÑOS QUE SALIERON DE DEFECTOS REALES, y por eso están
  1 EL GRIEGO NO ES UN DEFECTO
    La primera versión marcó como defecto EXPERIMENTS.md:232, que dice
    `10 corridas pareadas, ΔFPS=0`.  Eso es notación.  Un escáner que llora lobo
    sobre notación correcta queda ignorado el día que acierta, así que el griego es
    `review`, y la matemática se reporta en agregado, una vez y no por línea: la
    primera versión produjo 194 ítems de review y casi todos eran el signo menos de
    `count = payload - 1`
  2 LA MEDICIÓN DE "SIN VERSIONAR" ERA FALSA
    Usaba `git ls-files --error-unmatch`, que hace que git salga distinto si CUALQUIERA
    de los paths no está versionado.  Así que un directorio medio versionado devuelve
    vacío y la herramienta reports todos como sin versionar.  Medido: 87 findings, y
    decía "87 sin versionar" cuando 38 estaban versionados.  Una medición que da el
    número asustador es peor que no medir: ahora llama `git ls-files` sin ese flag y
    interseca
  3 --sync EXISTE POR UNA CONFESIÓN
    Escribiendo el equivalente a mano, el autor hizo `cd docs && git ls-files` en vez
    de `git -C <repo> ls-files`.  `git ls-files` imprime rutas relativas al directorio
    actual, así que desde docs/ no casaba nada, la conclusión fue "0 de 88
    versionados", y ese número FALSO se escribió en CURRENT-STATE.md.  Lo detectó el
    propio escáner en la línea siguiente
    La lección no es "ten cuidado".  Es que un contador que depende de un one-liner
    humano SE VA a desincronizar, en silencio, y la desincronización parece un
    hallazgo.  Así que la medición y la corrección viven juntas, en el único sitio
    donde el manejo de rutas es correcto, y la corrección informa de cada sustitución
    que hace para que un número equivocado nunca pueda ser silencioso
    Tiene tres controles negativos: corrige el número y preserva la prosa, informa de
    cada sustitución, y es IDEMPOTENTE.  La idempotencia se escribió porque la primera
    versión no lo era: actualizaba el numerador de `TRACKED 31 de 0` y dejaba el
    denominador.  `31 de 0` es PEOR que `0 de 0`, porque parece medido
```

```
UN DISEÑO QUE IMPONE UN LÍMITE, y es el que más costó
  los 9 ítems de review que quedan son CORRECTOS.  `sdma_v3_1.c` e `ih_v3_0.c` se
  citan precisamente porque NO existen: es el contenido de C-011 y de RE-36.  Una
  herramienta que exigiera resolverlos obligaría a alguien a "arreglarlos" borrando la
  afirmación central de esas dos entradas.
  Las nueve revisiones quedan así, y se registra que son intencionadas
```

```
LAS CINCO HERRAMIENTAS NUEVAS JUNTAS, y por qué hacen falta las cinco
  pm4_count_census.py   cuenta sobre el corpus          · falla en silencio si el cwd
  rx550pm4val.c         estructura de un IB, sin corpus · declara su propia salida
  asic_resolver.py      ¿esto COMPILA para mi ASIC?     · no toca el hardware
  ipsolve.py            ¿esto CORRE en mi ASIC?          · sigue el puntero .funcs
  docscan.py            ¿esto está COHERENTE?           · sólo lee docs/
  Las cinco responden a preguntas distintas, y ninguna habría detectado a las otras
  cuatro.  Por eso hacen falta todas, y por eso una sola no protege de nada
```

---

## TL-13 · `toolreg` — el registro de `tools/`, y el registro documentado

```
PROPOSITO  Inventariar tools/, ejecutar el self-test de cada herramienta, y CRUZAR el
           inventario con esta tabla en las DOS direcciones
ESTADO     SELF_TEST_OK · 9/9 checks, medido por mí
VERSION    1.0.0        SOURCE  tools/toolreg.py   UNTRACKED
SEGURIDAD  Lee ficheros y ejecuta el self-test de OTRAS herramientas.  No escribe nada.
           No abre /sys, no toca la GPU, no compila, no ejecuta git modificador

POR QUÉ EXISTE, que es el hueco que cerró
  a las 14:3x del 2026-10-01 había 23 herramientas fuente en tools/ construidas por tres
  sesiones en una mañana, y ninguna sabía de las otras:
    · 16 de 23 NO estaban citadas en ninguna parte de TOOLS-STATUS.md
    · reg_resolve.py resuelve un registro a MASK/SHIFT/UNIDAD y reg_census.py enumera
      qué registros toca un .c.  Ninguno aparece en la documentación, así que un agente
      que fuera a transcribir un campo de registro a mano no sabría que la herramienta
      existe
    · xref.py hace cross-reference por AST de clang, no por regex.  Esa es la respuesta
      a la clase de problema que costó a este proyecto ocho horas de un NOT_FOUND falso
    · contradict.py detecta afirmaciones incompatibles, que es una tarea que esta
      documentación hacía a mano
  Un índice que hay que mantener recordando no es un índice.  Es el problema de
  FINDINGS-INDEX aplicado a tools/, y tools/ tiene exactamente el mismo modo de fallo
LAS CUATRO COMPROBACIONES
  1 inventario    cada herramienta fuente, con tamaño y estado
  2 contrato      propósito declarado, y si declara QUÉ NO HACE
  3 selftest      ejecutar el suyo propio, capturando rc y duración
  4 cobertura     contra TOOLS-STATUS.md, en las DOS direcciones:
                    - una herramienta que existe y no está documentada
                    - una entrada TL-nn que nombra una herramienta que no existe
LO QUE ENCONTRÓ, Y LA ESCALA CAMBIÓ DURANTE LA MEDIDA
  primera ejecución, sobre tools/ solo:   23 herramientas, 4 documentadas
  escaneando las DOS ubicaciones:          44 herramientas, 12 documentadas
  13 aparecieron mientras se corría la herramienta.  Este árbol construye más rápido de
  lo que cualquier registro puede seguir, y eso ES el hallazgo

  Estado medido al final:
    self-test PASS               15
    NO_SELFTEST                  19
    NONZERO                       2   doclint.py, toolkit.py
    REFUSED_UNDECLARED            7
    SELF                          1   la que hace el chequeo
    documentadas en TOOLS-STATUS 12 de 44

  Y DOS HERRAMIENTAS QUE NO LAS CITA NINGÚN SITIO, ni hallazgo ni documento:
    citegen.py · contradict.py · msg_census.py · toolcheck.py · toolreg.py
  Para un árbol documental, una herramienta que no cita nadie significa que su salida no
  consta.  O no se usó, o se usó y nadie escribió el resultado.  Desde el árbol, las dos
  cosas son indistinguibles.  Preguntar por eso es el objetivo de la herramienta

LO QUE ESTA HERRAMIENTA NO PUEDE VERIFICAR, y es un límite real
  PASS 15 de 44.  No 44.  Las 7 REFUSED_UNDECLARED declaran `CONTRACT: READONLY=no` o
  `WRITES_FILES=yes`, y esta herramienta ejecuta código de otras sesiones, así que se
  niega.  Es la lectura correcta y no un detalle: una herramienta que dice que escribe
  ficheros no la ejecuta un registro
  Y las 19 NO_SELFTEST no tienen nada que ejecutar.  Un `NO_SELFTEST` no es un
  `PASS_POR_DEFECTO`: es un hueco, y por eso el resumen los cuenta por separado
  Conclusión honesta: la columna PASS de esta tabla cubre 15 de 44 herramientas.  Las
  otras 29 están sin verificar por el registro, y eso hay que leerlo así

LAS DOS CONVENCIONES DE CONTRATO QUE EXISTEN, y por qué importan
  tools/                  WORK_CLASS=READ_ONLY · WRITE_EXECUTION=NONE
  08-ARQUITECTURA/tools/  # CONTRACT: name=... READONLY=no WRITES_FILES=yes
  La primera versión sólo reconocía la primera, y reportaba «13 herramientas sin
  declaración WORK_CLASS».  Buena parte de eso no era una declaración ausente: era la
  MISMA declaración escrita de otra forma.  Un interlock que llora lobo sobre una
  ortografía acaba ignorándose, y entonces no protege nada
  Y `08-ARQUITECTURA/tools/` no estaba en el inventario: pm4_count_census.py,
  count_vmflush_dw.py y frame_budget.py figuraban como entradas TL que nombraban una
  herramienta inexistente.  Eran una mudanza, no una pérdida.  Un registro que escanea
  la mitad de las herramientas no es un registro

LAS TRES HERRAMIENTAS NUEVAS QUE RESUELVEN DEFECTOS YA REGISTRADOS
  pm4census.py  mide la convención de `count` de PACKET3 «SÓLO en el ASIC que», que es
                exactamente el filtro que a `msg_census` le falta.  Ver RE-43
  pm4_reachable.py  «vocabulario PM4 VIVO de un ASIC: qué paquetes ejecuta de verdad, no
                cuáles define».  Eso es el mismo título que RE-31: 74 opcodes definidos, 12 por
                encima de 0x80, y sólo uno vivo
  hwip.py  responde por bloque «esto lo decide el caso del chip, o la versión», que es la
                pregunta que `ipsolve` responde por otra vía
  Es decir: las tres herramientas nuevas atacan las tres cosas que esta mañana costaron
  un error.  El equipo ya está aprendiendo solo, y el registro es lo que lo hace visible

EL INTERLOCK DE SEGURIDAD, que es lo importante
  Esta herramienta ejecuta código escrito por otras sesiones, en un árbol donde cinco
  sesiones trabajan a la vez y donde la restricción permanente es no tocar MMIO, no
  cargar módulos, no escribir en sysfs.  Por eso:
    · se NIEGA a ejecutar una herramienta que no declare WORK_CLASS o WRITE_EXECUTION
    · se NIEGA a ejecutar una que declare un ámbito de escritura
    · y NUNCA se comprueba a sí misma, y lo dice en la salida
  El texto de «lo que se rechaza» tiene que parecer una DECLARACIÓN, no prosa.  La
  primera versión buscaba palabras sueltas y se negó a ejecutar a sí misma, porque su
  propia cabecera nombra MMIO_WRITE, insmod y rmmod como lo que rechaza:
      toolreg.py   REFUSED_UNSAFE
  Un interlock que dispara sobre la herramienta que lo aplica es un interlock que
  alguien desactiva, y entonces no protege nada.  Medido y corregido
ESTADOS QUE NUNCA SE REDONDEN A PASS
  · self-test ausente                  -> NO_SELFTEST
  · rc distinto de cero sin FAIL      -> NONZERO
  · se niega a ejecutar               -> REFUSED_UNSAFE / REFUSED_UNDECLARED
  · la herramienta que hace el chequeo -> SELF
LO QUE NO PROBABA
  · NO juzga si la SALIDA de una herramienta es correcta.  toolcheck.py dice lo mismo de
    los contratos, y ambos tienen razón: un parser correcto no demuestra que la
    respuesta lo sea.  El juicio sigue siendo de quien lee
  · NO lee una herramienta para entenderla: lee su cabecera.  Una con buena cabecera y
    cuerpo equivocado pasa todas las comprobaciones
  · la cobertura se mide por NOMBRE.  Una herramienta descrita en prosa sin su nombre
    entre acentos graves se leerá como no documentada.  Es un falso negativo en la
    dirección segura, y se registra en vez de esconderse
```

---

## TL-14 · `msg_census` — el titular está mal y el self-test no lo caza

```
PROPOSITO  Qué mensajes envía el host al SMC, con su payload
ESTADO     SELF_TEST_OK pero SALIDA REFUTADA en su titular.  Ver RE-43
VERSION    1.0.0        SOURCE  tools/msg_census.py   UNTRACKED
SEGURIDAD  declara WORK_CLASS=READ_ONLY · WRITE_EXECUTION=NONE
LO QUE DICE, y medido por mí
    llamadas de envio: 503     mensajes distintos: 217     símbolos sin resolver: 217
    por sus propios veredictos de uso:   VIVA 11 · MUERTA 5 · NO_CONDICIONAL 487
LO QUE ES CIERTO
  el fichero que la ruta activa de Polaris12 selecciona es polaris10_smumgr.c, con 14
  sitios de envío, y sus 14 símbolos resuelven 14/14 contra smu7_ppsmc.h, que es el
  include que ese fichero hace
  sobreestimación del titular: 36×
PARA QUÉ SÍ SIRVE  el veredicto por uso, y el inventario de símbolos con sus ficheros.
  Eso es un dato bueno con un titular malo
PARA QUÉ NO  para contar los mensajes de esta GPU.  503 es el número de sitios de envío
  en todo el subárbol pm/, incluidos rv (RISC-V), cz, fiji, vega10, vega12 y vega20
NO SE CORRIGE AQUÍ  es trabajo de otra sesión.  COORDINACION.md:184
EL INCIDENTE YA ESTABA REGISTRADO Y SIGUE VIVO
  la cabecera de toolcheck.py lo describe textual, y ese 503 es el mismo 503
```

---

## TL-15 · `reg_resolve` — registro y campo a offset, máscara, shift y UNIDAD

```
PROPOSITO  Resolver un registro o un campo a su offset, MASK, SHIFT y UNIDAD
ESTADO     SELF_TEST_OK (PASS, medido por mí)   · 3 hallazgos lo citan
SOURCE     tools/reg_resolve.py   UNTRACKED
LO QUE RESUELVE  la tarea que hoy se hace a mano al transcribir un campo de
  gmc_v8_0_d.h y compañía.  Y la UNIDAD importa: `RE-22` y `RE-24` giran sobre
  distinguir un contador de un identificador, y un valor sin unidad no lo permite
LO QUE APARECE EN TODO ESTE DOCUMENTO COMO RESPUESTA MANUAL
  `oracle.sh` responde literalmente «este offset es de mi ASIC o de otro» →
  `reg_resolve.py --reg ...».  Es decir: la pregunta ya tiene herramienta y nadie lo
  sabía
NO DECLARADO  no publica una sección de límites.  Declarado aquí ese hueco
```

---

## TL-16 · `reg_census` — qué registros toca un `.c`, con su bus

```
PROPOSITO  Qué registros modifica un fichero, directos e indirectos, y por qué bus
ESTADO     SELF_TEST_OK (PASS)   · 2 hallazgos lo citan
SOURCE     tools/reg_census.py   UNTRACKED
LO QUE APORTA AL MODELO CAUSAL  es la etapa «REGISTRO» de la cadena de `pipeline.py`:
  qué registro, desde qué fichero.  Sin eso no hay productor ni consumidor
```

---

## TL-17 · `regtable_audit` — tablas de `gpu_pt_config_reg` contra los headers GFX8

```
PROPOSITO  Validar tablas de registros contra los headers de GFX8
ESTADO     SELF_TEST_OK (PASS)   · 2 hallazgos lo citan
SOURCE     tools/regtable_audit.py   UNTRACKED
LO QUE RESUELVE  una clase entera de error: una tabla copiada de otra generación
  compila, y compilar no dice nada.  Es la versión de registers de «el nombre del fichero
  no dice qué generación es»
NO DECLARADO  sin sección de límites
```

---

## TL-18 · `struct_layout` — tamaño y offset de cada campo de un struct del kernel

```
PROPOSITO  Tamaño y offset de cada campo de una struct del corpus
ESTADO     SELF_TEST_OK (PASS)   · 2 hallazgos lo citan
SOURCE     tools/struct_layout.py   UNTRACKED
LO QUE RESUELVE  la aritmética de `IR-33` y de `026-frame` hecha a mano:
  el tamaño de una struct del kernel medido en vez de contado
```

---

## TL-19 · `xref` — cross-reference por AST de clang, no por regex

```
PROPOSITO  Referencias reales de un símbolo, vía AST de clang
ESTADO     SELF_TEST_OK (PASS)   · 1 hallazgo lo cita
SOURCE     tools/xref.py   UNTRACKED
LO QUE RESUELVE, y es la clase de error más cara del repo
  el falso NOT_FOUND.  `019` pasó ocho horas en NOT_FOUND por un barrido mal filtrado, y
  `033-pm4-spec` estuvo a punto de invalidar su predicción por contar 12 falsos positivos.  Un AST no
  tiene los dos problemas: no confunde un offset de registro con un opcode, ni busca una
  cadena dentro de otra palabra
  Es la respuesta correcta a `NR-05` y a la clase que la nombra
```

---

## TL-20 · `trace_path` — cadena de llamadas con el nodo vivo/muerto

```
PROPOSITO  La cadena de llamadas de un símbolo, con el veredicto de alcance por nodo
ESTADO     SELF_TEST_OK (PASS)   · 1 hallazgo lo cita
SOURCE     tools/trace_path.py   UNTRACKED
LO QUE APORTA AL MODELO CAUSAL  es la etapa «PRODUCITOR» de `pipeline.py`.  Y el
  veredicto VIVA/MUERTA por nodo es lo que impide el error que este repo ha cometido
  cuatro veces: confundir código muerto con código de esta GPU
```

---

## TL-21 · `which_hw` — qué HWIP tiene mi ASIC

```
PROPOSITO  Qué revisión de hardware tiene este ASIC
ESTADO     SELF_TEST_OK (PASS)   · 2 hallazgos lo citan
SOURCE     tools/which_hw.py   UNTRACKED
LO QUE RESUELVE  la pregunta de la que depende `amdgpu_ip.c:241`: el log de arranque dice
  `detected ip block number 4 <sdma_v3_1_0> (sdma_v3_0)`, y ese 3.1.0 sale de
  `amdgpu_ip_version(adev, SDMA0_HWIP, 0)`.  Sin saber el HWIP no se puede leer el bloque
  activo, y sin el bloque activo no se sabe qué código corre.  Es la primera pregunta de
  la cadena
```

---

## TL-22 · `vmid_map` — VMID, PD, PTBA y jobs

```
PROPOSITO  Reconstruir VMID -> PD -> PTBA -> jobs
ESTADO     SELF_TEST_OK (PASS)   · 2 hallazgos lo citan
SOURCE     tools/vmid_map.py   UNTRACKED
LO QUE APORTA AL MODELO CAUSAL  es la etapa «GPUVM / VMID / PTBA» de la cadena, y la
  estructura sobre la que gira `RE-12`: `PAGE_TABLE_DEPTH` recibe 0 para el contexto 0
  (GART) y 1 para los contextos 1-15, y el corpus no declara qué significan
```

---

## TL-23 · `cap_census` — qué `PHM_PlatformCaps` se activan y de dónde

```
PROPOSITO  Qué capacidades de platform caps se activan para MI ASIC, y de dónde
ESTADO     SELF_TEST_OK (PASS)   · 2 hallazgos lo citan
SOURCE     tools/cap_census.py   UNTRACKED
LO QUE RESUELVE  una de las formas más outsourceables de este repo: una capacidad
  asumida heredada del driver de referencia.  Es el mecanismo detrás de la regla
  NO_HISTORICAL_INHERITANCE
```

---

## TL-24 · `msg_census` · ya va en TL-14, y aparece aquí por su valor en la línea H

```
NOTA  TL-14 es la entrada canónica de msg_census.  Se repite aquí porque el orden de
  esta tabla es por valor informativo y la línea H la necesita pronto
VALOR PARA LA LÍNEA H  es la herramienta correcta para el modelo de mensajes, y la que
  hoy tiene un titular 36× mayor que el real.  Ver RE-43 antes de usarla
```

---

## TL-25 · `contradict` — afirmaciones incompatibles entre hallazgos

```
PROPOSITO  Detectar afirmaciones incompatibles entre hallazgos del proyecto
ESTADO     SELF_TEST_OK (PASS)   · 0 hallazgos lo citan
SOURCE     tools/contradict.py   UNTRACKED
LO QUE HACE ESTA MISMA TABLA  `CONTRADICTIONS.md` documenta C-001 a C-011 a mano, una por
  ronda, y tres de ellas sólo aparecieron porque un hallazgo nuevo contradijo a otro
  anterior.  Esta herramienta hace esa búsqueda de forma mecánica
POR QUÉ 0 hallazgos la citan  porque su salida no consta en ninguna parte.  O no se usó,
  o se usó y el resultado no se escribió.  Desde el árbol, indistinguible.  Es
  `toolreg` diciendo lo que nadie estaba preguntando
NOTA  `docscan` comprueba coherencia ESTRUCTURAL de docs/.  Esta herramienta comprueba
  coherencia SEMÁNTICA entre hallazgos.  Son dos preguntas distintas y hacen falta las dos
```

---

## TL-26 · `toolcheck` — contrato e integridad de cada herramienta

```
PROPOSITO  Que cada herramienta cumpla su propio contrato: nombre, versión, propósito,
           self-test y limitaciones
ESTADO     SELF_TEST_OK (PASS)   · 0 hallazgos lo citan
SOURCE     tools/toolcheck.py   UNTRACKED
LO QUE RESUELVE, y el párrafo que lo justifica es el mejor de todo tools/
  "Un parser correcto NO demuestra que la herramienta sea correcta.  Este fichero
   comprueba lo que sí se puede comprobar de forma automática"
  Comprueba: que existe y arranca · que el self-test pasa y con qué rc · que el texto
  declara sus límites · que el Python parsea · que declara WORK_CLASS y WRITE_EXECUTION
LO QUE NO HACE  no comprueba que la herramienta diga la verdad
Y SU INCIDENTE REGISTRADO ES EL QUE ORIGINÓ RE-43  su cabecera describe el incidente de
  msg_census, y ese incidente sigue vivo.  Un detector de contratos que encuentra el
  defecto del otro y no lo cierra es exactamente por lo que hace falta un registro
RELACIÓN CON TL-13  `toolcheck` mira DENTRO de cada herramienta.  `toolreg` mira el
  conjunto: qué existe, qué está documentado y quién no cita a nadie.  Complementarios
```

---

## TL-27 · `pipeline` — la cadena causal, con procedencia por nodo

```
PROPOSITO  Correr las herramientas en cadena y producir el mapa causal
ESTADO     SELF_TEST_OK (PASS)   · 5 hallazgos lo citan, el máximo de las 26
SOURCE     tools/pipeline.py   UNTRACKED
LO QUE HACE, y su declaración del problema es lo que la hace valiosa
  "El problema no es falta de herramientas: es que no se usan juntas, y la cadena que las
   enlaza es exactamente la que el proyecto necesita"
      REGISTRO → MMIO → PRODUCTOR → TRANSFORMACIÓN → CONSUMIDOR → EFECTO
  Con comandos sueltos, pasar de «este .c se compila» a «este registro lo modifica el
  firmware» son seis pasos manuales, y en cualquier salto se puede confundir una rama
  muerta con una real
LO QUE PRODUCE  un grafo donde cada nodo lleva su evidencia (fichero:línea) y la
  herramienta de origen, y las aristas clasificadas DIRECTA / MACRO / VTABLA / VIA_SMC,
  y el veredicto de alcance VIVA / MUERTA / SIN_DETERMINAR
LA REGLA QUE IMPONE, y es la importante  un nodo sin procedencia NO entra en el mapa.
  Esa es la diferencia entre un mapa causal y una lista de afirmaciones
LO QUE NO HACE  no mide hardware.  Toda su evidencia es de fuente y de compilación, que
  es lo que este proyecto tiene sin autorización de runtime
```

---

## TL-28 · `citegen` — audita TODAS las citas del proyecto

```
PROPOSITO  Auditar las citas del proyecto y decir de cada una si resuelve
ESTADO     SIN SELFTEST propio (NO_SELFTEST)   · 0 hallazgos lo citan
SOURCE     tools/citegen.py   UNTRACKED
LO QUE APORTA  es la respuesta a `RE-38`.  Allí se estableció que un `sha256` sobre un
  fichero sin versionar es una cifra que caduca: en seis minutos `tools/rx550pm4val.c`
  pasó de 850 a 1018 líneas y el hash declarado ya no identificaba nada
  Una herramienta que dice de cada cita si resuelve es la defensa contra eso
DÓNDE ESTÁ SU DEUDA, y hay que decirlo  NO tiene self-test, así que su
  `NO_SELFTEST` es un hecho medido, no una opinión.  Y 0 hallazgos lo citan, que es el
  mismo hueco que TL-25 y TL-26
  Lo que la documentación hace a mano hoy es un escaneo de glifos, refs rotas y símbolos
  sin definir, y eso ya está en `docscan` como automated
```

---

## TL-29 · `audit_citations.sh` — citas `header.h:LINE` y constantes `RX550_*`

```
PROPOSITO  Verificar cada cita «header.h:LINE» contra el corpus, y cada constante
           `RX550_*` contra su definición
ESTADO     SIN SELFTEST propio (NO_SELFTEST)   · 2 hallazgos lo citan
SOURCE     tools/audit_citations.sh   UNTRACKED
LO QUE APORTA  comprueba la clase de evidencia que este árbol más cita y menos verifica:
  el par fichero:línea.  Y las constantes del driver propio contra su definición, que es
  justo la comprobación que faltaba en `C-011`
  `oracle.sh` la menciona como la otra mitad de la pregunta que responde
```

---

## TL-30 · `oracle.sh` — la respuesta automatizada a «¿de dónde sale esto?»

```
PROPOSITO  Responder de dónde sale un dato y cómo se comprueba, encadenando herramientas
ESTADO     REFUSED_UNDECLARED por `toolreg`: no declara WORK_CLASS ni WRITE_EXECUTION, así
           que la herramienta que verifica contratos se NIEGA a ejecutarla.  No es un
           defecto de `oracle.sh`: es que el registro no puede clasificar lo que no está
           clasificado   · 1 hallazgo lo cita
SOURCE     tools/oracle.sh   UNTRACKED
LO QUE APORTA  su declaración del problema es el resumen más corto de por qué este
  proyecto perdía tiempo:
    - "este offset es de mi ASIC o de otro"  -> reg_resolve.py --reg ...
  Es decir: la respuesta existía y nadie la tenía a mano cuando hacía falta
LO QUE FALTA, y es una línea  el token de seguridad.  No se añade aquí porque el fichero
  es de otra sesión y COORDINACION.md:184 es «informa, no arregles».  Con una línea
  `WORK_CLASS=READ_ONLY · WRITE_EXECUTION=NONE` en la cabecera, `toolreg` deja de
  negarse a ejecutarla
```

---

## TL-31 · `rx550pm4val.c` — validador de flujo de comandos del driver propio

```
PROPOSITO  Validar la estructura de un flujo PM4/IB, sin acceso al corpus
ESTADO     SELF_TEST_OK declarado (12/12, 181 checks) pero REFUSED_UNDECLARED por
           `toolreg`, que no lo ejecuta al no declarar ámbito.  El hallazgo que lo
           implementa (`038`) declara sus propias cifras; no están verificadas por mí
SOURCE     tools/rx550pm4val.c   UNTRACKED
LO QUE RESUELVE  la circularidad que el propio hallazgo declara, textual:
  "el codificador se escribió leyendo amdgpu, y las expectativas del test se
   transcribieron del MISMO amdgpu, así que un error de lectura replicado en los dos sitios
   pasa las 147 comprobaciones"
LO QUE NO RESUELVE, y lo declara él mismo  "ya se sabe que acepta uno: `count` en vez de
  `count-1`".  Valida ESTRUCTURA, y el error de `C-011` es de VALOR.  Para sDMA la
  longitud es implícita en el OPCODE, así que una regla de PACKET3 no alcanza a PTEPDE
  Ver RE-37
LO QUE LE FALTA PARA PODER EJECUTARLO  el token de seguridad.  Misma línea que TL-30
```

---

## TL-32 · `rx550ref.c` — referencia contra el driver de referencia

```
PROPOSITO  (declarado por su nombre) contrastar el driver propio contra el de referencia
ESTADO     REFUSED_UNDECLARED por `toolreg`, igual que TL-31.  No ejecutado
SOURCE     tools/rx550ref.c   UNTRACKED
LO QUE ES  la pieza que `F3d` identifica como el hueco REAL que queda:
    DRIVER_CONSTANT_VS_REFERENCE_DIFF
    comparar cada constante de `rx550_pm4.h` contra la del driver de REFERENCIA, y exigir
    que el fichero citado exista y tenga la línea citada
  Si eso existiera y se ejecutara, `C-011` no habría llegado a código compilable
LO QUE LE FALTA  el token de seguridad, y que se le ejecute para saber si funciona
  No se afirma aquí que funcione.  Se afirma que no se ha medido, que es distinto
```

---

## TL-33 · La cadena, y por qué hacen falta veintiséis herramientas

```
REGISTRO  reg_census · reg_resolve · regtable_audit · which_hw
MMIO      reg_census (bus) · reg_resolve (offset/mask/shift/unidad)
PRODUCTOR  trace_path · xref · which_hw · ipsolve
TRANSFORMACIÓN  pipeline (aristas MACRO / VTABLA)
CONSUMIDOR reg_census · reg_resolve
EFECTO     (requiere runtime, y no está autorizado)
COMPILACIÓN asic_resolver · oracle.sh
DESPACHO   ipsolve
CONTROL    contradict · docscan · toolcheck · toolreg · citegen · audit_citations
LÍNEA H    msg_census · cap_census · vmid_map

Y LA REGLA QUE SOSTIENE TODO, escrita por `pipeline` y adoptada aquí
  un nodo sin procedencia NO entra en el mapa
Las veintiséis responden a preguntas DISTINTAS y ninguna habría detectado a las otras
veinticinco.  Por eso hacen falta las veintiséis, y por eso una sola no protege de nada.
Y por eso la duodécima línea, la de CONTROL, es la que decide si las otras once siguen
siendo creíbles.
```

---

## TL-34 · El coste de no tener esto, medido

```
26 herramientas.  16 con self-test PASS.  4 documentadas.  22 sin documentar.
5 no citadas por NINGÚN hallazgo ni documento.
Y el resultado, en una mañana: dos contradicciones (C-009, C-010), una tercera
(C-011) y un incidente de herramienta todavía vivo (RE-43).

  C-009  se resolvió preguntándole al log de arranque al kernel, que ya estaba ahí
  C-010  se resolvió contando 637 páginas de un documento que ya estaba en el disco
  C-011  se resolvió con UNA LÍNEA de una tabla de despacho, y esa línea se podía
         automatizar: es `ipsolve --expect`, y existía como idea desde RE-39

Ninguna de las tres hacía falta un razonamiento nuevo.  Hacía falta mirar el sitio
correcto, y las herramientas existen para mirar el sitio correcto.
El coste real de esta mañana no fue el análisis: fue el OCHO de buscar a mano lo que ya
estaba automatizado, y el RIESGO de heredar un titular de herramienta que nadie
verificó.  RE-43 es el segundo, y ya había cobrado una vez.
```

---

## TL-35 · `round.py` — la ronda documental como pipeline

```
PROPOSITO  Ejecutar la ronda de documentación en un comando, y en particular la parte
           que más costó: leer cada finding nuevo, extraer sus cifras, y ARBITRARLAS
           contra el autoinforme del kernel
ESTADO     **TOOL_PARTIAL**, y la clasificación es medible, no retórica.  Ver abajo
VERSION    1.0.0        SOURCE  tools/round.py   UNTRACKED
SEGURIDAD  Lee ficheros y lee el ring buffer del kernel con `journalctl -k -b`, que es
           una lectura de log.  No escribe en docs/, no edita hallazgos, no abre /sys,
           no toca la GPU, no carga módulos, no compila
           La ÚNICA escritura que hace es su propio fichero de estado, y sólo con
           --accept.  Por eso ese flag es un acto separado y visible

QUÉ AUTOMATIZA, y por qué esta parte y no otra
  el paso caro de esta mañana, hecho a mano tres veces, fue:
      leer un finding nuevo -> extraer sus números -> decidir si concuerdan con lo que
      el kernel imprimió al arrancar
  así se resolvieron C-009, C-010 y C-011.  Los tres eran alcanzables con un comando, y
  ninguno se ejecutó como comando porque no existía

LOS SEIS PASOS
  scan       compone docscan y toolreg y reporta sus veredictos.  NO los reimplementa
  new        qué findings han aparecido que esta ronda nunca vio, por sha256, con los
             ficheros MODIFICADOS distinguidos de los nuevos
  claims     las claims numéricas de esos findings
  arbitrate  las que tienen ÁRBITRE DE HOST se comparan contra el kernel, y se dice
             cuáles concuerdan y cuáles no
  conflicts  COMPUESTO: causal_map.py --contradictions.  NO propio
  verdict    clasificación TOOL_PARTIAL / TOOL_VALIDATED, medible

LOS ÁRBITRES, Y POR QUÉ LA LISTA ES CORTA
  un árbitro es un valor que el kernel IMPRIME, de modo que zanja una lectura estática
  sin humano.  Hay cuatro, y deliberadamente son pocos:
    amdgpu vm size is <N> GB, <M> levels, block size is <B>-bit, fragment size is <F>-bit
    detected ip block number <N> <TYPE_vM_m_r> (<FUNCS_NAME>)
  Todo lo demás NO recibe veredicto.  Una herramienta que dice «sin evidencia» para la
  mayoría de sus entradas y un veredicto firme para las pocas que sí puede zanjar vale
  más que una que adivina en todas

POR QUÉ `conflicts` ES COMPUESTO Y NO PROPIO, que es la decisión de diseño
  la primera versión de este fichero creció su propio detector de conflictos.  Leyendo
  `041-grafo-y-detector-contradicciones.md` encontré que `causal_map.py` ya lo hacía, y
  MEJOR: pondera por ESTADO (`PROVEN` sobre `debil`) y encuentra la contradicción de
  `block_size` desde el PRIMER documento en vez del tercero.  Está validado por mutación
  y dice haber corregido cuatro bugs de extracción
  El local no tiene noción de ESTADO, así que no distingue `PROVEN` de `debil`.  Se queda
  en el self-test como contraste y sale del pipeline.  La regla de composición dice
  preferir lo existente, y aquí lo existente es mejor

LA MEDICIÓN, que es lo que hace que la clasificación sea TOOL_PARTIAL
  92 findings.  Claims ARBITRABLES encontradas: 4 en forma dura (`clave = N`) y 3 en
  forma débil (`**N/M/K**`).
  RECALL BAJO, y declarado: la forma dura encuentra 4.  El corpus está escrito en prosa
  con números en negrita y en tablas, y un regex no cubre eso.  No se publica un recall
  del 100 % que no existe
  PRECISION, con su fallo medido y corregido
    1 el extractor leyó `block_size = 33` como afirmación.  Era una MUTACIÓN de prueba:
       `041` dice textual «y valida por mutacion: anado `block_size = 33 | PROVEN` a un
       documento y lo detecta».  Un valor que está mal A PROPÓSITO, reportado como
       DISAGREE contra el kernel.  Corregido: un texto que anuncia una mutación se
       salta entero, porque un solo valor inyectado falso destruye cualquier precisión
    2 el extractor de claims débiles aceptaba CUALQUIER palabra de tres letras como
       clave, y capturó `equivoque` en «**Y me equivoqué en `block_size`.** Reporté
       13/14/15. Es **22/23/24**» con el valor 13/14/15.  Como ese match consumía el
       texto, nunca llegaba a la afirmación real.  Corregido: el patrón de clave se
       construye desde ARBITER_TABLE, así que por construcción no puede capturar prosa
  LO QUE HOY ARBITRA, y es la comprobación que importa
    $ round.py --repo . --only arbitrate
      kernel facts: vm_size 64 · block_size 10 · fragment 9 · levels_minus_one 1
                    gmc_hwip 8.1.0 · gfx_hwip 8.0.0 · sdma_hwip 3.1.0
      claims débiles: 3 valores, 0 AGREE, 3 DISAGREE
        block_size  22  vs kernel 10   en 030-page-walker-gfx8-2-niveles.md
      claims duras:  4, todas AGREE, 0 DISAGREE
    O sea que encuentra, en un comando y desde el §CUDA del finding, exactamente la
    contradicción que C-009 arbitró a mano.  `22`, `23` y `24` salen los tres

CLASIFICACIÓN  TOOL_PARTIAL, y por qué no TOOL_VALIDATED
  hace bien lo que hace y lo demuestra sobre el árbol real: encuentra el 22, descarta la
  mutación del 33, y compone causal_map
  pero su recall es de 7 claims sobre 92 findings, y eso es una limitación real que
  impide usarlo como autoridad.  La clasificación se escribe en la salida, no en un
  fichero aparte, para que no pueda desincronizarse del código

LO QUE ESTA HERRAMIENTA PROPONE Y NO HACE
  · no escribe ninguna afirmación en docs/ y no edita ningún hallazgo
  · AGREE significa «consistente con el autoinforme del kernel».  NO significa verdadero.
    Es una clase de evidencia, y no la más fuerte: el kernel podría estar mintiendo, o
    el valor podría no ser comparable
  · DISAGREE es un hecho medido sobre lo que el kernel DICE.  Lo que significa lo decide
    quien lee.  El 22 era incorrecto, pero eso no lo deduce la herramienta: lo deduce el
    hecho de que el kernel lo contradice Y de que el código lo confirma
  · no hay conversión automática de correlación en causalidad, ni de ninguna de las dos

ESTADO INICIAL  NEW SIN VER 92, porque es la primera vez que se ejecuta.  Con --accept
  graba lo visto y la siguiente ronda sólo.  Y esto ya ha ocurrido: si alguien usa
  --accept sin leer el informe, la herramienta se queda muda justo cuando aparecen
  findings nuevos
LIMITE DE LA ARBITRACIÓN  sólo hay cuatro líneas del kernel que arbitran, y de las 92
  sólo cuatro claims caen en ellas.  No es un detector de errores: es un detector de
  contradicciones con el kernel, sobre los subjects que el kernel imprime
VALIDACIÓN  self-test 17 checks, 0 fallos.  Los controles negativos que importan:
    · un log del kernel que dice 22 hace que nuestro 10 salga DISAGREE  (no siempre AGREE)
    · sin log del kernel, TODO es NO_KERNEL y no se inventa ningún veredicto
    · un texto que anuncia mutación no produce ninguna claim
    · una clave no arbitrable se marca NOT_ARBITRABLE, no se adivina
    · step_new es idempotente, y distingue CHANGED de new
    · --accept escribe; sin --accept no se escribe NADA
```

---

## TL-36 · Lo que la automatización no sustituye, y hay que decirlo

```
LO QUE SE AUTOMATIZÓ ESTA TARDE
  · el registro de herramientas y su cobertura        -> toolreg
  · la coherencia estructural y los contadores         -> docscan
  · el gate de despacho de bloques de IP              -> ipsolve
  · el arbitraje de cifras contra el kernel            -> round
  · la detección de contradicciones entre hallazgos    -> causal_map (ya existía)
  · el censo de mensajes SMC acotado al ASIC           -> pm4census (ya existía)
LO QUE SIGUE SIENDO MANUAL, y no por falta de herramienta
  · LEER el §CUDA de un finding nuevo y decidir si su contenido merece una fila en
    EVIDENCE-MATRIX.  `round` extrae las cifras, no el sentido
  · decidir qué significa un DISAGREE
  · escribir la fila con su WHAT/WHERE/WHEN/HOW/UNIT/LIMITATION/PRODUCER/CONSUMER/EFFECT
  · arbitrar una afirmación que el kernel no imprime.  Los cuatro árbitres cubren
    geometry y HWIP; no cubren semántica de PTE, orden de ejecución, ni nada de SMC
LA REGLA, y es la que sostiene todo lo anterior
  automatizar la MEDICIÓN, nunca la INTERPRETACIÓN
  Un número medido por máquina no necesita un humano.  Un número que significa algo
  necesita a alguien que sepa qué significa
Y EL RIESGO NUEVO QUE LA AUTOMATIZACIÓN INTRODUCE
  una herramienta que dice DISAGREE en todas partes se lee como «todo está mal», y una
  que dice AGREE en todas partes como «todo está bien».  Ninguna de las dos es una
  posición defendible
  por eso el vocabulario de veredictos es cerrado y no se redondea: AGREE es «consistente
  con el autoinforme», DISAGREE es «el kernel dice otra cosa», NO_KERNEL es «no lo sé», y
  NOT_ARBITRABLE es «esta pregunta no se arbitra así»
  Y por eso una precisión medida importa más que un recall alto: un detector que
  señala cuatro contradicciones reales y ningún falso vale más que uno que señala
  cuarenta, aunque la extracción sea correcta
```

---

## TL-37 · `claim.py` — la cobertura del registro de claims, y por qué no puede escribir

```
PROPOSITO  Medir qué findings tienen una claim registrada, cuál es el próximo RE-nn libre,
           y qué claims NO son auditables.  Y emitir un BORRADOR de claim, impreso
ESTADO     **TOOL_VALIDATED**, 12 checks, 0 fallos, medido por mí
VERSION    1.0.0        SOURCE  tools/claim.py   UNTRACKED
SEGURIDAD  Solo lee.  Su self-test legaliza su propio fuente buscando un
           `open(...,'w')`, y falla si lo encuentra

LA MEDICIÓN QUE LA MOTIVÓ, y no es cosmética
    95 findings   ·   67 citados por docs/   ·   28 NO citados por nada
  Veintinueve por ciento de la evidencia del proyecto nunca registrada.  Y leyendo los
  NOMBRES de esos 28:
    043-vuelta-atras-035-y-036-leian-el-asic-equivocado
        otra sesión descubriendo que 035 y 036 leen el ASIC equivocado.  Es C-011
    059 · 060 · 061-srcdata
        qué lleva src_data[0] del vector de interrupción, que es lo que RE-36 y RE-40
        afirman
    062-citas-de-c-009-desplazadas
        sobre la contradicción que esta documentación ya había registrado
  O sea: el hueco es evidencia, y entre ella un SEGUNDO TESTIGO INDEPENDIENTE de una
  contradicción ya resuelta
  Y es la misma forma del fallo que `toolreg` encontró en las herramientas: un registro
  que hay que mantener recordando no es un registro

LO QUE MIDE
  coverage      findings citados por al menos un fichero de docs/
  next_free_id  el próximo RE-nn libre, para no colisionar
  unauditable   claims SIN LOCATION.  Es el campo que decide si una claim es auditable,
                y el recuento de su ausencia es el número más útil de la herramienta
  orphans       claims que citan un finding que ya no existe
  collisions    índices de finding duplicados (27 en este árbol)
  holes         huecos en la secuencia RE

EL CONTROL NEGATIVO QUE IMPORTÓ
  la cobertura NO puede confundir dos findings con el mismo índice.  Citar `<001>-uno.md`
  no cubre `<001>-otro.md`, y el self-test lo comprueba con dos findings `001` puestos a
  propósito.  Con 27 colisiones en el árbol, casar por número en vez de por nombre
  completo haría parecer cubierto un finding que no lo está, y el número de cobertura
  sería una mentira

POR QUÉ NO PUEDE ESCRIBIR, y no es cautela sino diseño
  un scaffolder que pudiera publicar sería una máquina para fabricar afirmaciones, que es
  exactamente el fallo que este proyecto ha pagado cuatro veces
  así que --scaffold IMPRIME.  Los campos mecánicos vienen de la cabecera del propio
  finding (CLASSIFICATION, CORPUS, CORRECTS, RUNTIME...), y TYPE y STATE salen como
  PENDIENTE, porque son los dos que llevan conocimiento y esta herramienta no tiene
  ninguno
  y el self-test lo hace cumplir: legaliza su propio fuente y falla si encuentra código
  que escriba.  Una restricción que depende de que nadie la quita es una restricción
  débil

LO QUE LA HERRAMIENTA ENCONTRÓ AL MEDIR, y es lo que la justifica
  RE-47  src_data[0] NO dice «dónde».  Es el SUBTIPO del evento de display: lo produce
         tonga_ih.c:263 y lo consume dce_v8_0.c.  Eso CORRIGE una fila de esta tabla
         documental, que decía «dice dónde», y el IV de GFX8 no lleva dirección
  RE-48  SDMA0_HWIP no llega a leerse para este ASIC.  La ruta de Polaris12 resuelve sus
         bloques por caso de chip, no por amdgpu_ip_version, y 046 lo demuestra por
         alcanzabilidad sin MMIO.  Es MÁS FUERTE que arbitrar por el log: demuestra que
         el VALOR de esa versión no puede cambiar ninguna conclusión
  REGISTRADO POR LA COBERTURA y verificado por mí, no leído por/toolreg
  Y TRES FALLOS DEL SELF-TEST QUE FUERON MÍOS
    · la cobertura hacía bien lo difícil y yo había escrito la aserción al revés, así que
      un acierto se veía como fallo
    · el scaffold etiqueta CORPUS como VERSION, porque etiqueta por el campo de claim
    · y un SyntaxError por un «·» tipográfico en la línea del token de seguridad: los
      tokens tienen que ser ASCII
LIMITE  mide cobertura por coincidencia de NOMBRE en el texto de docs/.  Una claim que
  describa un finding sin nombrarlo se lee como no cubierta, y eso es un falso negativo
  en la dirección que empuja a registrar de más, no de menos

---

## TL-38 · `claim.py --locate` — traer las líneas, que NO es elegir la línea

```
PROPOSITO  Para cada claim sin LOCATION, resolver los findings que cita y mostrar las
           líneas que ESOS findings ofrecen.  Atacar RE-49: 24 claims no auditables
ESTADO     **TOOL_VALIDATED**, 16 checks, 0 fallos
SEGURIDAD  solo lee

LA DISTINCIÓN QUE LO JUSTIFICA, y es la razón de existir
  cerrar RE-49 exige dos cosas, y sólo una es automatizable:
    TRAER   qué ficheros:línea ofrece la evidencia que la claim ya cita
    ELEGIR  cuál de esos es LA línea de esta afirmación
  Esto hace la primera.  No hace la segunda, y no debe: una LOCATION equivocada es
  indistinguible de una correcta.  gmc_v8_0.c:691 y :702 son líneas reales sobre los
  flags del PTE, y elegir entre ellas a máquina sería inventar un rastro de auditoría

LA MEDICIÓN QUE LO MOTIVÓ, Y UNA CORRECCIÓN MÍA
  dije antes, y como si fuera una medición, que 15 de las 25 claims sin LOCATION citaban
  un finding que ya declara sus localizaciones.  Era FALSO: son 0.  Los findings
  *mencionan* fichero:línea en línea, que es otra cosa
      FETCHABLE    0   el finding citado DECLARA un bloque LOCATION
      ADVERTISED  11   el finding sólo menciona fichero:línea: quedan como candidatos
      MANUAL      14   nada resoluble sin leer el corpus
  Dar 15 donde la verdad era 0 es exactamente el fallo que la herramienta existe para
  evitar: decir una estimación como si fuera una medida

EL PRIMER USO, sobre la claim que más dolía
  RE-10  "Geometría de page table, cerrada numéricamente".  La más citada del registro,
  la que zanjó C-003 y C-009, y sin ni una línea de código
  la lista ofrecía seis candidatas.  Se eligieron TRES leyéndolas en el corpus:
    gmc_v8_0.c:1127   amdgpu_vm_adjust_size(adev, 64, 9, 1, 40)
                      las ENTRADAS, y son un argumento literal: la línea más fuerte
                      posible, porque no hay nada que derivar
    amdgpu_vm.c:2424  tmp = roundup_pow_of_two(max_pfn)        = 2^24
    amdgpu_vm.c:2427  tmp = DIV_ROUND_UP(fls64(tmp)-1, 9) - 1   = 2   <- REASIGNA
    amdgpu_vm.c:2428  num_level = min_t(..., max_level, tmp)   = 1
    amdgpu_vm.c:2429  switch (num_level)  case 1 -> root_level = PDB0
    amdgpu_vm.c:2454  block_size = amdgpu_vm_get_block_size(tmp)     <- con tmp = 2
    amdgpu_vm.c:2463  el dev_info que la arbitra
  Y eso es lo que la herramienta NO hizo: las seis candidatas son las mismas para
  cualquier lectura, y decidir que 1127 era la ENTRADA y no un argumento más requiere
  entender que los argumentos de adjust_size son el origen de toda la cadena
  Es el reparto exacto: la herramienta trae el 80 % mecánico; el 20 % que decide es
  conocimiento, y por eso el resultado no se publica solo
Y UN EFECTO COLATERAL ÚTIL
  la lista corta de RE-10 es la que hace evidente por qué las tres cifras de block_size
  de la mañana eran posibles.  Con la línea 2454 a la vista, `tmp` en ese punto es 2 y
  no 2^24, y el error de 022 era un `tmp` equivocado, no una aritmética difícil
LO QUE NO HACE
  no propone cuál línea es la correcta, ni puntúa candidatas, ni escribe nada
  no cubre los 14 MANUAL: para ésos hay que leer el corpus, y eso no se automatiza

```

---

## Herramientas del sistema que SÍ importan

| Herramienta | Estado | Por qué está aquí |
|---|---|---|
| `git`, `git log -S`, `git blame` | `VALIDATED` | Es la fuente de la cronología de `C-001`. Permitió ver que la limitación obsoleta es anterior al commit que la refuta |
| `lspci`, `readlink /sys/class/drm/*/device` | `VALIDATED` | Identidad de la RX550 por PCI/BDF, no por índice de tarjeta. Es el criterio que evita el error más caro de esta línea |
| `sysfs` (`/sys/class/drm/card1/device/mem_info_*`, `/sys/module/amdgpu/parameters/*`) | `VALIDATED` | Lectura sin privilegio, sin RUNTIME. Es lo que hace `vram_full_visible=FALSE` y los cuatro `-1` verificables |
| `glxinfo -B` | `VALIDATED` | Versión de Mesa real, que contradijo la del README |
| `spirv-val` | `INSTALLED`, `VALIDATED` | `rc=0` sobre `decompress_bc3.spv`. **Se dijo que faltaba y era falso**; corregido en `49bd550` |
| `glslangValidator` | `INSTALLED`, `VALIDATED` | `rc=0`, 11 672 B, 2 918 words, magic `07230203` |
| `ctags` | `VALIDATED` | Universal Ctags 6.2.1 |
| Coccinelle (`spatch`) | `NOT_AVAILABLE` | TL-04 |
| `libpcre.so.1` | `NOT_AVAILABLE` | Requisito de spatch, no está en el sistema base |
| `strace` | `NOT_AVAILABLE` | Declarado y no instalado. `NOT_AVAILABLE` no se cuenta como PASS |
| `nm` | `VALIDATED` | Es lo que demuestra que `rx550_drv.ko` es driver PCI y `rx550.ko` no. Con control negativo |

---

## Tabla de fallos, causa, reproducción, arreglo

```
TL-04/semref        ERROR  Coccinelle en /tmp, directorio perdido
                    REPRO  ./semref engines  ->  ENGINE-NOT-AVAILABLE ; refs -> rc=3
                    FIX    extraer RPM a prefijo persistente ; libpcre del RPM pcre
                    VALID  ./semref engines  ->  ambos DISPONIBLE ; refs -> rc=0
                    ESTADO NOT REPARED

TL-03/gfx8vmgeom    ERROR  rutas relativas al cwd ; el mensaje de error nombra la causa
                    equivocada
                    REPRO  desde la raíz del repo  ->  rc=2 "no coincide con el sha256"
                    FIX    dos: documentar el cwd en su README, y que el mensaje distinga
                          "fichero no encontrado" de "sha no coincide"
                    VALID  desde su directorio  ->  37/0, 12/12
                    ESTADO NO REPARED. Documentado aquí.

TL-02/pm4dw         ERROR  uso no documentado en dos puntos
                    REPRO  (a) --struct amdgpu_ring_funcs -> STRUCT_NOT_FOUND, rc=1
                           (b) --struct-size=A,B -> option desconocida, usage, rc=2
                           (c) usage() omite --struct-size y --wm-sites, que el parser
                               acepta (pm4dw.c:1080, 1089)
                    FIX    (a) documentar, o aceptar tipo y variable
                           (b) aceptar la forma con "="
                           (c) dos lineas en usage()
                    VALID  --struct gfx_v8_0_ring_funcs_gfx -> DECLARED 172
                           --struct-size vi_ce_ib_state ...   -> 4 miembros, 16 B
                    ESTADO NO REPARED. Documentado aquí.

TL-01/pm4_count_census   SIN FALLO CONOCIDO
TL-05/validate_rx550_final  SIN FALLO CONOCIDO
TL-09/pteflags            SIN FALLO CONOCIDO ADEMAS del de invocacion de arriba
TL-06/evidence_search      SIN FALLO CONOCIDO Y SIN TEST DE FALLO  <- el hueco
```

## Lo que ninguna herramienta de este repo puede hacer

```
LEER UN REGISTRO DE HARDWARE      no hay MMIO, ni debugfs con permiso, ni UMR
MEDIR ORDEN DE EJECUCIÓN DEL GPU  requiere cargar el driver propio: BLOCKED_BY_AUTHORIZATION
OBSERVAR EL SAMPLER BC3           requiere un experimento de usuario vía Mesa (frontera F2),
                                   no una herramienta: no existe y no se ha construido
DISTINGUIR "ausente" de "no       evidence_search.py lo hace por construcción (§expect),
   leído"                        y es la única forma correcta en este repo
CONTAR PACKET3 EN RAMAS Y BUCLES  no contable estáticamente; 22 casos declarados UNKNOWN
                                  [NR-06]. No hay herramienta que los cierre sin ejecutar
```

La última fila es la que importa para no perder tiempo: **22 emisiones de las 68
contables no se pueden contar leyendo código**, y ninguna cantidad de análisis estático
lo cambia. Hay que ejecutar, y ejecutar está bloqueado por autorización.
---

## TL-39 · `snapshot.py` — la tercera parte del experimento, la que NO estaba bloqueada

```
PROPOSITO  Capturar el estado del host y de la GPU en una forma DIFERENCIABLE y con
           hash, leyendo sólo.  Sellar PRE-STATE · POST-STATE · DIFF del ciclo de
           experimentos, que es la parte que hoy no dependía de ninguna autorización
ESTADO     **TOOL_VALIDATED**, 30 checks, 0 fallos
SEGURIDAD  sólo lee.  Escribe un fichero, y sólo con --save: la propia instantánea
ARBITRAJE  `--arbitrate` contra `journalctl -k -b`: 3 AGREE · 0 DISAGREE · 0 NO_KERNEL

POR QUÉ ESTA, Y NO OTRA
  el ciclo de experimentos acordado tiene diez campos:
    INPUT · CONFIGURATION · COMMAND · PRE-STATE · ACTION · POST-STATE
    · OUTPUT · ERROR · RESULT · INTERPRETATION
  De ésos, tres son automatizables HOY sin tocar la GPU: PRE-STATE, POST-STATE y
  DIFF.  Todo lo demás -- EXECUTE y la captura que hay que hacer sobre el ASIC --
  está BLOCKED_BY_AUTHORIZATION y esta herramienta no lo intenta
  Y esos tres no se habían construido.  Eso significa que cada experimento
  registrado hasta ahora en EXPERIMENTS.md escribió PRE-STATE y POST-STATE de
  memoria, que es la única forma de que no sean comparables
  `tools/validate_rx550_final.py` se COMPONE aquí, no se reimplementa: él responde
  «¿cumple este host el contrato?», esto responde «¿cómo era el estado en el
  instante T, en una forma en que dos instantes se puedan comparar?»

EL PROBLEMA DE DISEÑO, Y ES TODO EL PROBLEMA
  una instantánea ingenua no sirve para comparar, porque casi todo lo que hay en
  ella se mueve solo.  Marcas de tiempo, uptime, PIDs, boot_id, líneas de journal
  y la memoria libre cambian cada vez que miras, así que el diff de dos capturas
  seguidas con un segundo de diferencia reporta decenas de cambios que no son
  cambios en lo que se estudia
  Por eso cada hecho se declara VOLATILE o STABLE, y sólo el hash cubre las
  estables:
      dos capturas con una hora de diferencia y sin tocar la máquina dan el MISMO id
  Eso es lo que hace que un diff signifique algo, y está como ASSERT en el self-test,
  no esperado en un comentario

LO QUE NO ES DESHECIBLE, Y POR QUÉ SE GUARDA
  los volátiles se REGISTRAN, no se tiran.  No se hashean y no se comparan, porque
  compararlos produce diferencias falsas.  Una instantánea que los borrara sería
  menos útil para escribir el registro, que es uno de los diez campos

LOS CINCO DEFECTOS QUE ENCONTRÓ EN SÍ MISMA, y por qué dos importan más
  1 · 95 CLAVES FANTASMA, MEDIDO
      `amdgpu_params` era un solo hecho multi-línea.  El parser leía cada una de
      sus 95 líneas como un hecho propio: una instantánea de 15 hechos se leía como
      110.  Y no era cosmético, porque esos fantasmas eran todos ESTABLE, así que
      entraban en el hash y en el diff, y cambiar UN parámetro aparecía como
      95 añadidas y 94 quitadas — indistinguible de una máquina reconstruida
      Arreglo: un parámetro = un hecho, declarado por prefijo, `amdgpu.<param>`
  2 · ESTABA FOTOGRAFIANDO LA iGPU  ← el grave
      elegía la primera tarjeta alfabéticamente, y card0 es una Intel HD 4600
      0x8086:0x0412 en el bus de la CPU, driver i915.  La RX550 es card1
      0x1002:0x699f, driver amdgpu
      y lo peor es lo que hizo con el silencio: `vram_total`, `pp_dpm_sclk`,
      `gpu_busy_percent` y el resto no se registraban, porque no existen en el nodo
      equivocado.  Nada en el registro decía «no miré el dispositivo correcto»:
      sólo parecía una máquina tranquila y sana
      Arreglo: el sujeto se elige por una REGLA escrita (`vendor=0x1002`, única
      coincidencia), la regla se REGISTRA en el hecho `subject_selection`, y la
      ausencia se ESCRIBE `ABSENT`, nunca se omite
  3 · LA DIRECCIÓN PCI ERA EL PUENTE, no la GPU  ← también grave
      `realpath` da `/sys/devices/pci0000:00/0000:00:01.0/0000:01:00.0` y la
      búsqueda cogía la PRIMERA: la RX550 salía como `0000:00:01.0`
      nada en el valor errado delata que está equivocado.  Es la misma forma del
      fallo que una LOCATION plausible: una dirección real, nombrando otra cosa, e
      imposible de distinguir sólo mirando
      Arreglo: la ÚLTIMA, y un check de self-test contra `lspci -D -d 1002:699f`,
      que es fuente independiente del autoinforme del driver
  4 · UNA ADIVINANZA QUE NO ERA MÍA
      clasifiqué `pp_dpm_force_performance_level=0` como «por defecto» usando
      `endswith("=0")`.  Pero 0 significa AUTO, y AUTO es una decisión deliberada
      Saber cuál es el valor por defecto exige la fuente del kernel; adivinarlo es
      mentir en voz baja.  Arreglo: se registran los 96 parámetros tal cual y que
      los_compare el diff
  5 · EL COMMIT DE OTRA SESIÓN MOVIDA EL ID  ← el que casi impedía usarla
      `tools_git_head` estaba dentro del hash.  Es un hecho estable en el sentido de
      que no se mueve solo, pero NO es el sujeto, y bajo concurrencia otra sesión
      commitea varias veces por hora
      MEDIDO, no temido: el id pasó de `59e11a3ef7928751` a `73a35f813db8dc35` sin
      que la GPU moviera un byte.  Ese par de diferencias es exactamente el que la
      ronda siguiente tiene que distinguir
      Arreglo en dos pasos, y el segundo es el que importa:
        · los hechos de CONTEXTO (`tools_git_head`, `docs_exists`) se registran y se
          muestran, pero no entran en el hash
        · el filtro vive DENTRO de la función que calcula el id, no en quien la
          llama.  Con el filtro en el llamante la propiedad se cumplía sólo por ese
          camino, y el primer test lo demostró fallando: cualquier cosa que llamara
          a la función directamente hashearía el contexto
          Una guarda que se puede esquivar usando la función correcta no es una
          guarda
      Ahora se emiten DOS ids, el de hardware y el de contexto, y sólo el primero
      responde a «¿cambió el estado?»
  6 · UNA CONSTANTE DEFINIDA DOS VECES
      `STABLE_PREFIXES` aparecía dos veces y la segunda, más corta, pisaba a la
      primera y borraba en silencio el prefijo `drm.`
      Arreglo, y esto es lo que más me gusta: un check de self-test que parsea su
      propio AST y falla si un nombre de módulo está definido dos veces.  Una
      redefinición silenciosa es una clase de bug que ningún linter de este proyecto
      miraba

POR QUÉ LA VALIDACIÓN DE ESTA HERRAMIENTA ES DISTINTA DE LAS OTRAS
  todas las demás validan contra fixtures o contra el corpus: entrada fija,
  salida fija.  Eso aquí no puede funcionar, porque esta herramienta lee estado
  VIVO del host.  La única forma de saber si leyó el dispositivo correcto es
  preguntarle a algo que lo leyó por separado:
      snapshot  sysfs, ahora
      kernel     `amdgpu 0000:01:00.0: ...`, impreso al arrancar por otro código
  Y eso es lo que encontró los defectos 2 y 3.  No los encontró ningún fixture,
  porque un fixture no puede tener una iGPU delante de la GPU

VOCABULARIO DE VEREDICTOS, el cerrado de este proyecto, sin redondear
  AGREE          el kernel dice lo mismo
  DISAGREE       el kernel dice otra cosa
  NO_KERNEL      no lo sé
  NOT_ARBITRABLE no se arbitra así
  `DISAGREE` significa que el KERNEL discrepa. NO significa que la instantánea esté
  mal: uno de los dos se equivoca y la herramienta no puede saber cuál, y no va a
  suponer.  `NO_KERNEL` significa no lo sé, que no es lo mismo que estar de acuerdo

LO QUE NO HACE, DECLARADO
  · no afirma que ningún valor sea correcto: registra.  Una instantánea que dijera
    «block_size es correcto» sería una afirmación, y las afirmaciones viven en
    EVIDENCE-MATRIX.md donde se pueden arbitrar
  · no detecta un hang ni lee MMIO.  No puede, y F1 sigue bloqueado
  · no automatiza un diff hacia una conclusión.  diff dice que dos estados
    difieren; por qué, y cuál diferencia causó qué, no está en la instantánea
  · no arbitra el tamaño de VRAM contra el kernel, a propósito: sysfs y el kernel
    lo nombran y lo miden de forma distinta, y meter un par no comparable en la
    tabla sería fabricar un acuerdo.  Sale como NO ARBITRADO
  · no mide un experimento.  Mide el estado antes y después

ESTADO INICIAL, para que la próxima ronda pueda decir si algo se movió
  `docs/snapshots/`  ·  baseline de HARDWARE `bbf909eddd8c2cda`  ·  contexto `73a35f813db8dc35`
  127 hechos · 125 en el hash · 5 volátiles · arbitraje 3 AGREE
  Dos capturas seguidas dan el MISMO id, y un commit de otra sesión ya no lo mueve.
  Las dos propiedades se comprueban, no se esperan
  Y la segunda quedó DEMOSTRADA en el árbol, no en un fixture: entre escribir
  este bloque y guardarlo el HEAD pasó de `78bfb19` a `e6210b0`, y el id de
  hardware siguió en `bbf909eddd8c2cda`.  Bajo concurrencia eso es la prueba de
  que la herramienta sirve, porque es exactamente el caso para el que existe
---

## TL-40 · `citations.py` — resolver cada `fichero.c:N` y decir cuánto pesa

```
PROPOSITO  Resolver TODA cita `nombre.ext:N` del texto propio del proyecto y decir
           si es sólida, ambigua por versión, o si no significa nada.  Cerrar el
           hueco que quedó de F3d: no basta con que una cita exista
ESTADO     **TOOL_VALIDATED**, 20 checks, 0 fallos
SEGURIDAD  sólo lee.  No tiene ruta de escritura, y el check lo mira en el
           fuente y no en el comentario

POR QUÉ ESTA, Y NO OTRA
  el proyecto tiene una regla — `RESEARCH/evidence/working-vs-kernelbuild-difference.md`
  §6 la formula: «para cualquier cita fichero:línea, el árbol importa».  La regla
  está escrita y es correcta.  Lo que no existía era saber A CUÁNTO afecta
  `grep -c` no lo dice

LA MEDICIÓN QUE LA JUSTIFICA, y que es el hallazgo
  sobre este árbol, 2398 citas del texto propio:
      ROBUST           1070   toda copia dice lo mismo
      VERSIONED         839   lo esperado: la cita nombra una versión de kernel
      UNIDENTIFIABLE    261   la trampa: el NOMBRE no dice qué fichero
      FRAGILE           135   el corpus se contradice sobre la misma versión
      OUT_OF_RANGE       12
      UNRESOLVED         81

UNA CORRECCIÓN MÍA QUE CAMBIÓ EL NÚMERO, y es lo importante de esta entrada
  la primera versión tenía UN veredicto FRAGILE y reportó 1116 de 2366: el 47 %.
  Leído como alarma, eso parece un problema de higiene de citas de este proyecto.
  Es casi enteramente un artefacto
  al separar por versión, la clase FRAGILE baja a 135, y está ENTERA explicada:
      130 de 135  dentro de los 4 ficheros INSTRUMENTADOS
                    amdgpu_vm.c  amdgpu_vm_pt.c
                    amdgpu_debugfs.c  amdgpu_debugfs.h
        5 de 135  nombres genéricos: pci.h, types.h, file.c
  Ejemplo, `gmc_v8_0.c:1127`, la línea con la que cerré RE-10 hace una hora:
      7.1.3  kernelbuild   amdgpu_vm_adjust_size(adev, 64, 9, 1, 40);
      7.1.3  working       amdgpu_vm_adjust_size(adev, 64, 9, 1, 40);
      7.1.3  baseline      amdgpu_vm_adjust_size(adev, 64, 9, 1, 40);
      7.2.8  upstream      adev->gmc.mc_mask = 0xffffffffffULL;
  tres de cuatro coinciden.  Lo que discrepa son VERSIONES, que es lo que una
  diferencia de versión ES.  La preocupación que motivó la herramienta —el
  subárbol parcial— no es lo que esa fila muestra
  Dar 47 % donde la verdad son 5,6 % es un número que parece un hallazgo y es un
  artefacto de contar 7.1.3 y 7.2.8 como si fueran lo mismo.  Una medición que se
  infla por confundir una diferencia de versión con un desacuerdo es el mismo
  fallo que inflar un número, que es lo que este proyecto corrige

LOS TRES EJES, NO UNO
  la herramienta no pregunta «¿coinciden?» sino DOS cosas, porque una sola
  mezcla dos hechos que parecen iguales y no lo son:
    VERSIONED        copias de VERSIONES distintas que difieren.  No es un defecto.
                     Dice que la cita nombra un kernel y quien lee debe saberlo
    FRAGILE          copias de la MISMA versión que difieren.  Éste sí duele:
                     el corpus se contradice a sí mismo
    UNIDENTIFIABLE   el nombre no identifica el fichero.  `vi.h:27` resuelve a
                     amdgpu/vi.h Y a drivers/staging/media/tegra-video/vi.h, que
                     es la cabecera de un driver de vídeo Tegra sin nada que ver
                     `file.c` resuelve a unos cincuenta ficheros bajo fs/, arch/ y
                     drivers/
                     quien verifique esa cita puede caer en un fichero ajeno, ver
                     algo que PARECE código, y concluir cualquier cosa
                     esto no se arregla buscando más: sólo lo arregla el autor,
                     nombrando el fichero
                     y aquí quité un umbral arbitrario: separaba COLLISION a 2
                     subsistemas de UNIDENTIFIABLE a 3 o más, que es poner un
                     número en medio de un solo hecho

LO QUE FALLO AL MEDIRLO, Y ESTÁ EN EL FICHERO PORQUE ES EL DATO
  1 · «7 citas rotas en el driver».  Las siete eran MÍO ALCANCE DE BÚSQUEDA: sólo
      miraba en `drivers/gpu/drm/amd/` y esas cabeceras están en `include/asic_reg/`,
      `include/drm/` e `include/uapi/`.  Las siete resuelven, y las tres de GMC
      apuntan justo a los registros que este proyecto estudia:
          gmc_8_1_d.h:607 -> mmVM_CONTEXT8_PAGE_TABLE_BASE_ADDR
          gmc_8_1_d.h:615 -> mmVM_INVALIDATE_REQUEST
      Es la SEGUNDA vez en este proyecto que un instrumento culpa al artefacto de
      un fallo que era del instrumento.  Por eso la herramienta construye un
      índice de todos los nombres en todos los árboles en vez de suponer una ruta
  2 · traducía comparando también contra 7.2.8, y salía NO_UNIQUE_MATCH en los
      ocho ficheros.  Comparar texto de 7.1.3 contra 7.2.8 no es una traducción:
      es un error de categoría
  3 · clasificaba el FICHERO entero como intraducible en cuanto UNA línea citada
      no mapeaba, y tiraba las que sí mapeaban.  La comprobación directa dio
      +12 exacto en las cuatro líneas de amdgpu_vm.c.  Un veredicto de fichero
      sobre un hecho por línea descarta la medición que fue a tomar

EL `--translate`, Y POR QUÉ ES LA PARTE QUE VALE
  una ambigüedad con resolución mecánica conocida no es una ambigüedad: es una
  consulta.  Para cada cita FRAGILE, encuentra el MISMO texto en la otra copia e
  imprime su número de línea
      amdgpu_vm.c       +12  working -> kernelbuild
                        +0  working -> baseline     <- el par idéntico
                       -12  baseline -> kernelbuild
      amdgpu_vm_pt.c    +26
  el mapeo es por texto EXACTO y se RECHAZA si no es único, así que no puede
  inventar una equivalencia.  Y el delta 0 identifica el par prístino POR
  CONSTRUCCIÓN: la herramienta no elige la copia buena, y no puede
  las líneas que no mapean se listan igualmente: un fallo ahí no invalida el
  delta de las demás.  saline de eso

LO QUE CORROBORA, Y CON QUÉ MÉTODO
  `working-vs-kernelbuild-difference.md` ya estableció, por hash contra los
  tarballs oficiales, que working/baseline son 7.1.3 prístino y que kernelbuild
  lleva instrumentación `RE-02-E1 (RG-1)`.  Esta herramienta CORROBORA eso por
  una vía distinta —no leyó ningún tarball, sólo preguntó si las copias
  discrepan— y los deltas que mide coinciden con los de §4 de aquel fichero:
  +12, +26
  No es conocimiento nuevo.  Es la misma regla por otro camino

Y LO QUE AÑADE, que es lo único que aquel fichero no contiene
  la EXPOSICIÓN.  Aquél enuncia la regla y la ilustra con un ejemplo.  No dice
  cuánto del texto de este proyecto está afectado.  Medido aquí: 130 citas
  dentro de los cuatro ficheros instrumentados, `amdgpu_vm.c` la mayoría,
  incluidas todas las de RE-10

QUÉ ES LO QUE ESTAS CIFRAS DICEN DE RE-10, y hay que decirlo
  las líneas con las que cerré RE-10 esta sesión — 2424 2427 2428 2429 2454 2463
  — son números PRÍSTINOS.  Son los correctos para 7.1.3 y para el kernel en
  ejecución `7.1.3-200.nobara.fc44`, que no puede contener
  `amdgpu_re02e1_note_call()` porque esa función la escribió este proyecto.
  Contra kernelbuild cada una está desplazada 12
  Es decir: mi trabajo de hace una hora era CORRECTO y casi lo hice mal por
  una herramienta que habría elegido la copia equivocada sin avisar

LO QUE NO HACE, DECLARADO
  · no decide qué copia es la autoritativa.  Eso es conocimiento sobre la
    metodología de este proyecto y no sale de un listado de ficheros
  · no corrige nada.  Una cita la reescribe alguien que sabe qué quería decir
  · no juzga si una cita es RELEVANTE para su afirmación.  Una línea que existe y
    dice otra cosa es otro fallo, y esta herramienta no lo ve
  · no parsea C.  Busca `nombre.ext:número` y lo resuelve: sin preprocesador, sin
    macros, sin grafo de includes
  · no lee nada fuera de este repositorio

LO QUE AÚN NO ESTÁ HECHO, y queda nombrado
  las 261 UNIDENTIFIABLE son reales pero NO las arreglo: son citas de ficheros
  de otras sesiones y de mis propios docs, y corregir una referencia es trabajo
  de quien la escribió, no de un escáner.  Lo que sí hace la herramienta es
  volverlas visibles, que antes eran invisibles
---

## TL-41 · `constmap.py` — cada constante del driver contra la línea que ella misma cita

```
PROPOSITO  Comprobar cada `#define RX550_*` contra el testigo upstream que la propia
           cabecera cita en su comentario.  Cerrar el hueco estructural de F3d
ESTADO     **TOOL_VALIDATED**, 17 checks, 0 fallos
SEGURIDAD  sólo lee.  Sin ruta de escritura, y el self-test lo comprueba en el
           fuente
COMPOSICIÓN  importa el resolutor de `citations.py` por ruta.  No reimplementa el
           índice ni las reglas de resolución

POR QUÉ ESTA, Y NO OTRA
  `F3d` es un driver que compila y cuyo constant disagrees con the code it was
  written against.  Se encontró leyendo, tarde.  La razón estructural de que se
  pudiera encontrar tarde es que NADA miraba las constantes
  Y la evidencia necesaria ya estaba escrita, y nadie la leía.  Cada constante cita
  la línea de la que salió:
      #define RX550_PKT3_NOP           0x10    /* sid.h:343 */
      #define RX550_PKT3_WAIT_REG_MEM  0x3C    /* sid.h:397 */
  así que cada una es una afirmación falsable con testigo:
      RX550_PKT3_NOP = 0x10   AFIRMA ser   sid.h:343
      sid.h:343               QUE DICE     #define PACKET3_NOP  0x10

EL RESULTADO, y es un resultado NEGATIVO, que es la forma fuerte
  43 constantes.  Con testigo 32, sin testigo 11
      AGREE 15               el valor coincide con un #define
      AGREE_DISCRIMINATING 8  el valor coincide y además señala UN subsistema
      AGREE_COMMENT         4  el testigo es PROSA que enumera el valor
      WITNESS_USAGE         3  el testigo USA la codificación pero no lleva el valor
      NOT_COMPARABLE        2  el valor es una expresión
      UNCITED              11  sin testigo
      DISAGREE               0
      AMBIGUOUS              0
      NOT_A_DEFINE           0
  CERO constantes contradicen a su testigo.  Y los 32 con testigo quedan CUADRADOS:
  no queda ni un veredicto sin explicar
  Eso ESTRECHA F3d, y no poco: la capa de constantes de `rx550_pm4.h` está limpia.
  El defecto de F3d —`sdma_v4_0` donde el código dice `sdma_v3_0`, y `count - 1`
  en `rx550_pm4.c:277`— NO está en estas 43 constantes.  Está en el `.c`, y es un
  error SIMBÓLICO, no de valores.  Eso divide la pregunta en dos y deja una

POR QUÉ EL VALOR ARBITRA Y NO EL NOMBRE
  `RX550_PKT3_WAIT_REG_MEM` y `PACKET3_WAIT_REG_MEM` son lo mismo, y reconocerlos
  exige saber que PKT3 abrevia PACKET3.  Eso es conocimiento: meterlo en la
  herramienta pondría una suposición donde va una medición, y podría casar dos
  constantes distintas con una sin decir nada
  así que arbitra el VALOR, que es exacto, y el nombre upstream se MUESTRA al
  lado para que lo confirme una persona.  La herramienta afirma ambos y no afirma
  ninguno por separado

LA AMBIGÜEDAD QUE SÍ SE PUEDE RESOLVER, y aquí está el uso real de la composición
  `citations.py` marca `sid.h:343` como UNIDENTIFIABLE, y con razón: hay DIEZ
  `sid.h` en este árbol, y uno está en `drivers/gpu/drm/radeon/` con macros
  distintas en la misma línea.  Aceptar eso como respuesta tiraba las once
  cabeceras de packet, que es justo la familia que más importa
  pero el autor copió un VALOR del fichero que tenía abierto, así que un valor
  que coincide con exactamente una copia la identifica.  Eso es una inferencia
  del acto del autor, no una conjetura sobre su intención
      $ citations.py --show sid.h:343
        7.1.3  drivers/gpu/drm/amd   #define PACKET3_NOP    0x10
        7.1.3  drivers/gpu/drm/       #define SOFT_RESET_BIF (1 << 1)
  8 de 10 copias coinciden con nuestro valor, y las 2 que no son del subsistema
  equivocado
  CUANDO EL VALOR NO DISCRIMINA, vuelve a ser AMBIGUO y se dice.  No se fuerza
  Para eso `resolve()` de `citations.py` acepta `collapse_ambiguous=False`, y sólo
  lo usa esta herramienta, que tiene un discriminador propio.  El valor por defecto
  no cambia: para todos los demás llamadores UNIDENTIFIABLE es la respuesta honesta

LOS TRES TIPOS DE TESTIGO, que no pesan igual, y por eso hay tres veredictos
  `vid.h` NO codifica en un #define lo que el autor quiso documentar:
      186: #define WAIT_REG_MEM_ENGINE(x)   ((x) << 8)
      187:     /* 0 - me
      188:      * 1 - pfp
      189:      */
  así que citar 187 para `ENGINE_ME = 0u` tiene un testigo que SÍ lleva el 0, en
  prosa.  Eso es AGREE_COMMENT
  y citar un .c para una constante es otra cosa:
      6047: amdgpu_ring_write(ring, PACKET3(PACKET3_WAIT_REG_MEM, 5));
      6048:     (WAIT_REG_MEM_OPERATION(1) | /* write, wait, write */
      6054: amdgpu_ring_write(ring, ref_and_mask);
  6054 está en la función correcta y dentro del paquete correcto, pero no lleva el
  valor: es WITNESS_USAGE.  Corrobora el TEMA, no el NÚMERO, y se reporta como tal
  y explícitamente NO es un defecto

LO QUE CASI DIJE MAL, y es la parte que más me importa de esta entrada
  al ver NOT_A_DEFINE en 7 constantes, lo primero que escribí fue «dos testigos
  apuntan a `amdgpu_ring_write(ring, 0)`, que no tiene nada que ver con
  WAIT_REG_MEM: dos citas equivocadas».  Era FALSO
  `gfx_v8_0.c:6047` ES `PACKET3(PACKET3_WAIT_REG_MEM, 5)`, dentro de
  `gfx_v8_0_ring_emit_hdp_flush`; y 6206 está en `gfx_v8_0_ring_emit_vm_flush`, que
  también lo emite en 6180.  Las líneas están en las funciones correctas
  Es la lectura plausible y equivocada, la misma forma que C-009, C-011 y RE-47: la
  respuesta intermedia no era falsa, era la pregunta equivocada, y la corrección la
  encontró leer la función que contenía la línea en vez de la línea
  y el defecto del instrumento estaba en mi propia clasificación, que trataba
  «no es un #define» como «no hay nada» sin preguntar de qué tipo era la línea

TRES FALLOS DE LA HERRAMIENTA, que quedan porque son el DATO
  · la ambigüedad mal tratada dejaba sin comprobar las 11 constantes de packet, la
    familia más importante del fichero.  Un veredicto puede ser correcto y ser
    inútil: éste lo era y aun así tapaba lo que había que medir
  · `comment_states` buscaba dígitos en la línea ENTERA, así que
    `amdgpu_ring_write(ring, 0); /* mask */` contaba como testigo que declara 0.  El
    0 es del código, y la línea es el CUERPO de un paquete.  Un testigo que
    concuerda por el motivo equivocado es peor que ningún testigo, porque parece
    corroboración
  · y exigía el `*/` de cierre, cuando el comentario de `vid.h` se abre en 187 y se
    cierra en 189.  Una expresión regular que exige el cierre no ve ningún
    comentario, y así `AGREE_COMMENT` era 2 en vez de 4
  El segundo lo encontró un check de comportamiento que escribí para otra cosa, y
  ese es el orden correcto: escribir la propiedad primero, y que el bug aparezca al
  ejercitarla

LA TERCERA VEZ QUE UNA GUARDA SE DETECTA A SÍ MISMA
  el check que iba a impedir «que entre una heurística de similitud de nombres» era
  `if "SPECIFICITY" not in src`, y FALLÓ, porque la cadena "SPECIFICITY" estaba
  dentro del propio check.  Es la tercera instancia en este proyecto: `toolreg.py`
  publicó un interlock que se negaba a ejecutarse, y `snapshot.py` un check
  «no adivines el valor por defecto» que casaba con su propio texto
  Tres instancias son un patrón, no un accidente, y el arreglo no es buscar con más
  cuidado: una guarda escrita como literal la derrota el siguiente que no lo
  recuerde
  el arreglo es una guarda INMUNE AL TEXTO, y se comporta así: si arbitra el VALOR y
  el nombre sólo se muestra, entonces RENOMBRAR la macro upstream no puede cambiar
  el veredicto.  Se renombra a `TOTALLY_UNRELATED_TOKEN` y sigue dando AGREE.  Una
  heurística de nombres lo cambiaría; esta implementación no puede

LO QUE NO HACE, DECLARADO
  · no decide cuál copia de una cabecera ambigua es la pretendida
  · no evalúa macros.  `((x) << 8)` no se calcula: se reporta NOT_COMPARABLE,
    porque calcularlo necesita el preprocesador y el grafo de includes del kernel,
    y una regex que lo supondría fallaría en silencio
  · no juzga si una constante sin testigo es correcta.  UNCITED significa
    incomprobable aquí, no falsa
  · no edita nada
  · y AGREE NO prueba que la SEMÁNTICA sea correcta.  Prueba que el número coincide
    con una línea de una cabecera.  Qué significa ese número es la otra pregunta de
    F3d, y sigue abierta

EL DEFECTO QUE ENCONTRÓ `toolreg.py`, y por eso lo cuento aquí
  `toolreg.py` ejecuta el self-test de cada herramienta con `cwd=tools/`, no desde la
  raíz del repositorio.  Yo nunca ejecuto así, porque siempre estoy en la raíz
  mi self-test usaba `os.getcwd()`, así que buscaba `tools/07-DRIVER/kernel/
  rx550_pm4.h`, no lo encontraba, y daba 2 fallos:
      FAIL  check() raised FileNotFoundError: .../tools/07-DRIVER/kernel/rx550_pm4.h
  una herramienta cuyo self-test pasa 17/17 desde donde su autor trabaja, y falla
  desde donde el registro lo ejecuta.  LA HERRAMIENTA ESTABA BIEN Y SU SELF-TEST
  NO LA VALIDABA
  Eso es la segunda vez en esta sesión que ejecutar algo en un CONTEXTO no previsto
  encuentra lo que ejecutarlo como estaba previsto no puede.  La primera fue la
  colisión entre basenames genéricos y el corpus real
  Arreglo: la raíz sale de `__file__`, nunca del directorio actual, y ahora hay un
  check que lo impide volver —con la aguja montada en runtime, que es la cuarta vez
  que hace falta
  Comprobado en las ocho herramientas propias: desde `tools/`, las ocho pasan.
  El defecto era de esta una y no del patrón

LA CUARTA GUARDA QUE SE DETECTA A SÍ MISMA, y ya es un patrón con nombre
  el check que impedía una dependencia de `cwd` era `if "os.getcwd()" not in
  self_part`, y falló porque la cadena "os.getcwd()" estaba dentro del propio check.
  Cuarta vez en este proyecto:
      `toolreg.py`     un interlock que se negaba a ejecutarse
      `snapshot.py`    un check de «no adivines el valor por defecto»
      `constmap.py`    un check de «ninguna puntuación de nombres»
      `constmap.py`    este
  cuatro instancias y el arreglo es siempre el mismo, y no es tener más cuidado:
  montar la aguja en runtime, o —mejor— ASERTAR EL COMPORTAMIENTO.  El check de
  nombres no busca ninguna cadena: renombra la macro upstream a
  `TOTALLY_UNRELATED_TOKEN` y comprueba que el veredicto no se mueve.  Un texto no
  puede⬇ defender eso; un comportamiento sí
  y merece decirse por qué sigue apareciendo: un guard escrito como literal es
  corto, se lee bien, y parece exhaustivo.  Es exactamente por eso

LO QUE QUEDA ABIERTO, con nombre
  · 11 UNCITED: constantes sin testigo.  Aquí no hay contra qué comprobarlas
  · 2 NOT_COMPARABLE: expresiones.  Evaluables con `gcc -E` si la cabecera compila
    sola, y esa es la siguiente jugada, porque `cpp` es la respuesta correcta y no
    una regex
  · 3 WITNESS_USAGE: el tema está confirmado y el número no
  · y el `.c` de F3d, que este turno deja demostrado que NO es un problema de
    constantes

---

## TL-42 · `drift.py` — qué hacen las otras sesiones, y qué se movió bajo el registro

```
PROPOSITO  Medir la variable que decide si el resto de la documentación sigue siendo
           cierto: si el árbol se movió mientras nadie miraba
ESTADO     **TOOL_VALIDATED**, 13 checks, 0 fallos
SEGURIDAD  sólo lee.  Una escritura: `--seal` escribe el manifiesto, y nada más
COMPOSICIÓN  ninguna.  No hay modelo previo de esto en el árbol y no lo compuse

EL HUECO, y era grande
  todo lo demás del toolkit mide UN sujeto: el corpus, las citas, las constantes, el
  estado del host.  Nada medía la otra variable:
      ¿se ha movido el árbol desde que lo miré?
  y medido:
      el registro de herramientas conoce 2 directorios.  El repositorio tiene 7
      76 scripts sin entrada TL-, en total
          revkit                                18 guiones   5928 lineas   0 doc
          01-AUDITORIA/FASE-C1-RUNTIME-PREFLIGHT 17          10836         0 doc
          08-ARQUITECTURA/tools/btfq             7           1744         0 doc
          06-INGENIERIA-INVERSA/corpus           5            694         0 doc
          DOCUMENTATION-ROUTER/knowledge         3           1195         0 doc

  Eso es trabajo de otra sesión que mi documentación no puede ver.  Y encontró algo
  peor: una contradicción que YO había causado.  Ver `C-012`

LAS TRES PREGUNTAS, QUE NO SON LA MISMA
  `--toolkit`   DÓNDE está el trabajo.  Descubriendo directorios ANDANDO el árbol, no
                desde una lista: el fallo que esta herramienta existe para cazar es
                un directorio que nadie declaró, así que enumerar los declarados
                reproduciría el fallo exactamente
  `--activity`  QUÉ cambió y cuándo.  12 h: 30 commits, 125 ficheros tocados, 16
                modificados y 301 nuevos sin commitear.  Un recuento no es un
                informe; el informe es qué ÁREAS se movieron
  `--drift`     QUÉ se movió BAJO EL REGISTRO.  Ésta es la que importa y la que
                necesita estado: `docs/` está SIN SEGUIMIENTO en git, así que git no
                sabe cuándo se escribió una claim, y no hay forma honesta de preguntar
                «¿es esta claim más vieja que su evidencia?» sin un sello
                `--seal` graba hashes de contenido y `--drift` compara.  210 ficheros
                sellados en el primer sello

Y POR QUÉ ANTES DEL PRIMER SELLO NO DICE NADA, y lo dice explícitamente
  porque no hay sello, no dice «sin deriva».  No dice nada.  Es la diferencia entre
  no haber mirado y haber mirado y visto que no hay nada, y es la razón por la que
  este proyecto nunca convierte `NOT_FOUND` en `PROVEN_ABSENT`

LO QUE ENCONTRÓ, Y NO ES LO QUE SE BUSCABA
  se buscaba «qué herramientas nuevas hay».  Se encontró que existe un censo
  documental `DESIGN_FROZEN` con 1576 filas, y que 15 de mis ficheros no están en él
  El motivo por el que no están es una colisión de NOMBRES que yo creé.  Y los dos
  únicos matches aparentes eran otros ficheros con el mismo basename
  Eso es `UNIDENTIFIABLE` de `citations.py` aplicado a la documentación: un nombre
  que no identifica un fichero convierte una referencia bienintencionada en una
  ambigua, y quien la resuelve no sabe que hubo una elección

LO QUE NO SE ADOPTA, y es lo importante
  un directorio de herramientas que el registro no conoce se REPORTA, no se adopta.
  Adoptarlo sería afirmar cosas sobre código que esta sesión no escribió ni validó,
  que es exactamente el `OwnedError` que `COORDINACION.md` prohíbe
  y lo mismo con el censo: la contradicción se registra y se escribe la línea que
  falta, y no se edita el TSV de otra sesión

LO QUE ENCONTRÓ Y ES SÓLO OBSERVACIÓN
  `03-EXPERIMENTOS/ep08-doorbell-suppression/` contiene `nhwa.c`, `nhwa.ko`,
  `Module.symvers` y un Makefile: un módulo de kernel COMPILADO y sin seguimiento en
  git.  `/proc/modules` no lista ningún `nhwa`, así que está compilado y NO cargado
  esta herramienta dice que existe y que no está cargado.  No lo carga, no lo
  descarga, no lo inspecciona más, y no comenta si cargarlo sería seguro.  Descubrir
  un módulo no autoriza a hacer nada con él

UN MENSAJE DE COMMIT NO ES UN HALLAZGO, y lo dice en su propia salida
  que un commit diga que algo está arreglado no es evidencia de que lo esté.  La
  herramienta cuenta y lee títulos, nada más
  y el commit más reciente se titula «un control que decia lo que no era», que es la
  misma clase de defecto que esta ronda ha encontrado tres veces

EL SELLO, y por qué la guarda de escrituras es DE COMPORTAMIENTO
  la primera versión comprobaba las rutas de escritura con una lista blanca de
  regex, y falló: reconococía la escritura del propio manifiesto como una de más,
  porque la lista blanca tenía que coincidir con el regex sobre cómo éste se detiene
  una guarda de texto que tiene que coincidir con un regex sobre la ortografía es una
  guarda que va a mentir
  ahora se toma un inventario del árbol temporal, se llaman `seal`, `activity`,
  `toolkit` y `drift`, y se toma otro: la única diferencia admitida es el manifiesto.
  No lo puede derrotar cómo esté escrito el fuente, y además caza una escritura que
  nadie declaró, que es el punto

LO QUE SIGUE ABIERTO, y este turno no lo cierra
  · las 76 herramientas sin documentar: **ya están en `TL-43`**, transcritas y
    localizables.  Lo que NO está, y no lo puede estar desde aquí, es la validación de
    cada una.  Indexar una herramienta ajena es informar; adoptarla sería afirmar cosas
    sobre código que esta sesión no escribió ni entendió, y eso sí es el
    `OwnedError` que `COORDINACION.md` prohíbe.  Quien las escribió decide si entran
  · la atribución de las 45 citas de findings sobre ficheros desplazados.  `NOT_DETERMINED`,
    ver `NR-12`.  `--drift` no la resuelve: sólo puede decir que el fichero cambió, no
    de qué árbol copió el autor
  · y `C-012`, que es una decisión de coordinación y no un dato
  purpose = re.split(r"(?<=[.:;])\s", purpose, 1)[0][:96]


---

## TL-43 · Inventario de las herramientas de otras sesiones, transcrito de sus propias cabeceras

```
PROPOSITO  Que las 76 herramientas que docs/ no citaba sean LOCALIZABLES con un grep, y
           que quien las use sepa qué dice cada una sin abrirla
ESTADO     **TOOL_PARTIAL** por construcción: esto documenta artefactos, no prueba nada
SEGURIDAD  esta sección no ejecuta nada.  Es transcripción
LO QUE ES, con la distinción que importa
  una AFIRMACIÓN es una frase sobre el hardware que puede ser falsa, y vive en
  EVIDENCE-MATRIX.md donde se puede arbitrar.  Una DESCRIPCIÓN de un fichero no es una
  afirmación sobre el hardware: es repetir lo que el fichero dice de sí mismo
  por eso esto es documentación de ARTEFACTOS, y cada fila lo dice
LO QUE NO ES, y hay que leerlo antes de usar la tabla
  · NINGUNA de estas herramientas ha sido validada por esta sesión.  Ninguna ha sido
    ejecutada por esta sesión al escribir esta tabla
  · la columna «propósito» es la PRIMERA LÍNEA de su propio docstring.  Puede estar
    desfasada respecto a lo que la herramienta hace hoy.  Es lo que el fichero dice de
    sí mismo, no lo que hace
  · «contrato» significa que el fichero DECLARA WORK_CLASS / WRITE_EXECUTION / CONTRACT.
    No significa que lo cumpla.  Declarar un contrato no es respetarlo
  · «self-test» significa que el fichero contiene algo que parece un self-test.
    Que exista no es que pase, y esta sesión no lo ha ejecutado
  · y nada de esto contradice ni confirma ninguna claim de este proyecto.  Si una de
    estas herramientas contradice un hallazgo registrado, eso es trabajo de quien la
    escribió y de quien arbitra, no una entrada de tabla
LA CIFRA, y su MÉTODO, porque las dos cosas van juntas
  114 guiones en los 7 directorios
  39 citados en algún fichero de docs/
  76 citados en NINGUNO
  MÉTODO: límites de palabra, sobre los 8 ficheros de docs/, sin exigir acentos graves
  la primera versión exigía acentos graves y contó MENOS: reportó 98 sin documentar
  cuando son 76, y dio por no vistas las herramientas de ESTA MISMA sesión.  Es la
  tercera vez que este proyecto se infla una cifra al medir, y la razón de que el
  método vaya escrito al lado del número: un recuento cuyo método no se declara es un
  número que espera estar mal


### revkit — 19 no citadas

reverse engineering en curso: trazas, PTE/PDE, causalidad, estado.

```
herramienta                            lineas contrato self-test  primera linea de su propio docstring
atomrom.py                               383        -         -  atomrom.py -- parseo del VBIOS ATOM de la RX550.
captura.py                               313        -         -  captura.py -- toma un snapshot de TODOS los nodos de solo lectura, de una 
causa.py                                 295        -         -  causa.py -- genera el mapa causal de un simbolo, automaticamente.
check.sh                                 155        -         -  check.sh -- ejecuta TODAS las validaciones y dice que falla.
cidx.py                                  474        -         -  cidx.py -- indice consultable del corpus, en vez de grep.
cn7.py                                   130        -         -  cn7.py -- controles de pm4dec.py.
correlate.py                             185        -         -  correlate.py -- correlaciona hallazgos con la evidencia disponible.
estado.py                                195        -         -  estado.py -- sincroniza el estado del proyecto desde los documentos.
ibtrace.py                               467        -         -  ibtrace.py -- extrae secuencias de emision de IB desde el codigo fuente.
integro.py                               404        -         -  integro.py -- integridad del arbol del proyecto:
mmo.py                                   303        -         -  mmo.py -- observacion de SOLO LECTURA del hardware, via debugfs de amdgpu.
obs.py                                   229        -         -  obs.py -- observacion del host en una sola llamada.
pm4dec.py                                481        -         -  pm4dec.py -- decodificador PM4/IB de un anillo real de la GPU.
pte.py                                   231        -         -  pte.py -- analisis de flags de PTE/PDE de GFX8, end to end.
regs.py                                  480        -         -  regs.py -- decodificador de campos de registro del corpus.
scan.py                                  301        -         -  scan.py -- descubre TRABAJO, en vez de esperar a que le pidan trabajo.
selfcheck.py                             631        -         -  selfcheck.py -- controles del propio revkit.
vclaims.py                               298        -         -  vclaims.py -- verifica afirmaciones de los .md contra el corpus.
verdiff.py                               329        -         -  verdiff.py -- analisis diferencial entre dos VERSIONES del driver.
```

### 08-ARQUITECTURA/tools/btfq — 7 no citadas

subconjunto btfq.

```
herramienta                            lineas contrato self-test  primera linea de su propio docstring
btfq.py                                  646        -         -  btfq.py -- lector de BTF del driver amdgpu REALMENTE CARGADO en este host.
cn4.py                                   150        -         -  cn4.py -- control negativo del parser BTF, mutando el FICHERO de entrada.
cn5.py                                   146        -         -  cn5.py -- control negativo del contraste corpus/BTF.
cn6.py                                   267        -         -  cn6.py -- control negativo del barrido de block_size.
crosscheck.py                            125        -         -  crosscheck.py -- contraste corpus (fuente) contra BTF (binario en ejecucio
sweep.py                                 164        -         -  sweep.py -- rastreo de la cifra refutada block_size por TODO el proyecto.
vmsize.py                                248        -         -  vmsize.py -- modelo ejecutable de amdgpu_vm_adjust_size para GFX8.
```

### 01-AUDITORIA/FASE-C1-RUNTIME-PREFLIGHT — 17 no citadas

preflight de runtime, y sus tests de modo de fallo.

```
herramienta                            lineas contrato self-test  primera linea de su propio docstring
privileged_read_collector.py            3656        -         -  Privileged, read-only C1 preflight evidence collector.
test_artifact_unit_contract.py           385       si         -  Unit contract for the R1 artifact keys.
test_collector_failure_modes.py          672        -         -  Failure-mode tests T01-T16 for the four defects found in the independent r
test_defect03_behavioral.py              294        -         -  T35-T37:
test_defect04_behavioral.py              476       si         -  Behavioral tests for DEFECT-04 (root_coverage -> ownership_matrix contract
test_defect05_behavioral.py              378        -         -  Behavioral tests for DEFECT-05 (storage whole-disk attribute base).
test_defect06_behavioral.py              346        -         -  Behavioral tests for DEFECT-06 (G-06 summary must derive from read state).
test_drm_fds_enumerated_behavioral.py    784        -         -  Behavioral tests for drm_fds_enumerated scoring.
test_fdinfo_path_behavioral.py           283        -         -  Behavioral tests for the fdinfo path in scan_fds().
test_med_review_classifications.py       604        -         -  Verification of the MED-2 / MED-3 / MED-4 classifications.
test_medium_fixes.py                     481        -         -  P35-P47 and the realistic bridge fixture.
test_node_field_presence.py              284        -         -  Independence of three DRM fdinfo properties, in the producer and the consu
test_ownership_criterion_contract.py     432       si         -  Contract tests for the OWNERSHIP criterion, read-error visibility, nomencl
test_privileged_read_collector.py        882        -         -  Unit tests for the privileged read-only collector's identity layer.
test_r1_defects.py                       460        -         -  T17-T34:
test_task_a_absence_classifier.py        134        -         -  TASK A — executable assertions for DETERMINED_ABSENT.
test_task_c_locator_matching.py          302        -         -  TASK C — executable assertions for the DRM node locator rules.
```

### 01-AUDITORIA/DOCUMENTATION-ROUTER/knowledge — 3 no citadas

esquema e inventario del router documental.

```
herramienta                            lineas contrato self-test  primera linea de su propio docstring
knowledge_schema.py                      410        -         -  Phase 1 infrastructure — shared schema, controlled vocabularies and TSV I/
src_registry.py                          367        -         -  Phase 1 infrastructure — SOURCE REGISTRY generator (artifact ``SRC``).
test_knowledge_infrastructure.py         421        -         -  Phase 1 infrastructure tests — properties, not smoke.
```

### 06-INGENIERIA-INVERSA/corpus — 5 no citadas

LINEA B: corpus BC3/DXT5, decoder de referencia y cobertura de bloques.

```
herramienta                            lineas contrato self-test  primera linea de su propio docstring
bc3_ref_decoder.py                       117        -         -  Decodificador BC3 independiente, en Python, para arbitrar la discrepancia.
block_coverage.py                         67        -         -  Cobertura de bloques BC3 de un .bc3, para contrastarla con la del corpus d
make_corpus.py                           140        -         -  Genera el corpus de texturas de prueba de la integracion Fase 1 -> Fase 2.
q5_predict_full.py                       242        -         -  Prediccion exhaustiva de Q-5, y su cotejo contra la referencia en C.
q5_validate_llvmpipe.py                  133        -         -  Q-5:
```

### 08-ARQUITECTURA/tools — 19 no citadas

la otra rama de herramientas del proyecto.

```
herramienta                            lineas contrato self-test  primera linea de su propio docstring
_selftest_stale_gap.py                   464       si        si  import os import re import sys import json from collections import default
binfacts.py                              333       si         -  import gzip import lzma import os import re import subprocess import sys i
causal.py                                409        -        si  causal.py -- extrae CADENAS CAUSALES del corpus, no datos sueltos.
causal_chain.py                          330       si         -  import os import re import sys import json from collections import default
citecheck.py                             536        -        si  citecheck.py -- verifica que cada cita <fichero>:<linea> de un hallazgo AP
corpus_guard.py                          281       si         -  CORPUS GUARD -- integridad del corpus alrededor de una prueba de mutacion.
gmmio_inventory.py                       343       si         -  INVENTARIO DE REGISTROS MMIO QUE TOCA EL CAMINO GFX8, con offset resuelto.
hdrmap.py                                341       si        si  hdrmap.py -- a cada .c de amdgpu/, que FAMILIA DE CABECERA DE REGISTRO le 
include_closure.py                       227       si         -  import os import re import sys ROOT = "/home/lucas/Escritorio/RX550-INVEST
mqd_layout.py                            788       si        si  import os import re import sys import json CORPUS = ("/home/lucas/Escritor
next_work.py                             284       si         -  import os import re import sys import json from collections import default
pm4_codec.py                             430       si         -  import os import re import struct import sys HERE = os.path.dirname(os.pat
pm4_layout_audit.py                      178       si         -  AUDITORIA CRUZADA:
regdb.py                                 443       si        si  regdb.py -- resuelve un REGISTRO o un CAMPO contra TODAS las cabeceras de 
run_all.py                               221       si        si  CONTRACT:
runtime_obs.py                           410       si         -  import os import json import re import subprocess import time CARD = None 
scopeguard.py                            349        -        si  scopeguard.py -- el PREFLIGHT de escritura, en un comando.
stale_gap.py                             809       si        si  import os import re import sys import json from collections import default
toolaudit.py                             354       si        si  toolaudit.py -- mide F11:
```

### tools — 6 no citadas

directorio compartido de herramientas.

```
herramienta                            lineas contrato self-test  primera linea de su propio docstring
artifacts.py                             990        -        si  artifacts.py - genera los artefactos que AGENTS.md §AUTOMATIZACIÓN DE DOCU
claims.py                               1306       si        si  claims.py - audita AFIRMACIONES, no lineas.
frontier.py                              886       si        si  frontier.py - la lista de lo que queda abierto, CLASIFICADA por lo que har
relations.py                             428        -        si  relations.py - el vocabulario REAL de relaciones entre findings.
smc_layout.py                           1163       si        si  smc_layout.py — el contrato de memoria host↔firmware, derivado del offseto
unreach.py                               918       si        si  unreach.py - generaliza la prueba de 046 a los N selectores de despacho.
```

LO QUE ESTA SECCION NO HACE, y es lo unico que no puede hacer
  no valida ninguna de estas herramientas, y no ejecuta ninguna
  no adopta ninguna.  Adoptar una herramienta ajena sería afirmar cosas sobre código
  que esta sesión no escribió ni entendió, que es el `OwnedError` que
  `COORDINACION.md` prohíbe.  INDEXARLA no es lo mismo que adoptarla: aquí se dice
  qué dice cada fichero de sí mismo, y nada más
  no arregla ninguna de ellas.  Si alguna tiene un defecto, se reporta a quien la
  escribió, como lleva haciendo `COORDINACION.md` desde el principio
LO QUE SÍ HACE, y es lo que se le pedía
  que un `grep -r` encuentre estas herramientas.  Antes no aparecían en ninguna
  documentación: eran código invisible para quien no estuviera en esa sesión
  y ahora tienen nombre, ruta, tamaño, y su propia frase de propósito

Y LO QUE SIGUE SIENDO IMPOSIBLE, porque es verdad y no hay atajo
  documentar bien 114 herramientas requiere leerlas.  Esto las hace visibles y
  localizables, que es la mitad del problema, y la otra mitad es trabajo de quien las
  escribió


TOTAL guiones recorridos: 115

---

## TL-44 · `gccverify.py` — preguntarle al compilador, que es la autoridad sobre ABI

```
PROPOSITO  Verificar contra el COMPILADOR lo que dice un modelo de layout de structs
ESTADO     **TOOL_UNVALIDATED por esta sesión**: no lo he ejecutado ni leído entero.
           Lo leo por su cabecera y por lo que hace, que es lo que dice esta entrada
PRODUCER   otra sesión, en `tools/gccverify.py`, 329 líneas
SEGURIDAD  declara `WORK_CLASS=READ_ONLY · WRITE_EXECUTION=NONE`, y por lo que dice
           escribe un `.c` TEMPORAL y lo borra.  No toca el corpus

POR QUÉ LA REGIENTO, aunque no sea mía
  porque es el ejemplo más claro del bucle que este proyecto está aprendiendo:
  una afirmación sobre la que HAY una autoridad disponible, y preguntándosela a la
  autoridad en vez de derivándola otra vez
  Escribe un `.c` temporal que incluye la CABECERA REAL del corpus, imprime `sizeof`
  y `offsetof` de los campos que se le pidan, y lo compara con lo que dice
  `struct_layout`.  Es decir: donde la medición vigente es «el modelo da 1756», la
  evidencia fuerte no es volver a calcular, es que el compilador diga 1884

LO QUE LA HERRAMIENTA MISMA DICE, y se transcribe en vez de resumirse
  · el caso que la motivó es «el modelo da 1756, gcc dice 1884».  Un byte de diferencia
    y ya no era el mismo struct.  Eso se encuentra comparando offsets de uno en uno, no
    leyendo un total
  · `struct_layout` tiene 157783 macros con definiciones conflictivas en el subárbol.
    Saber cuántas tocan los structs que importan exige una herramienta, no una lectura
  · «la verificacion que no se repite es la que no se hace»
  · LIMITACIÓN que declara: sólo funciona con cabeceras AUTOCONTENIDAS.  `smu74.h` no
    tiene ningún `#include`, así que compila solo.  Una cabecera que dependa de tipos
    del kernel dará error de compilación, y eso se reporta como `NO_COMPILE`, nunca
    como fallo de layout
  esa última línea es la que más me gusta: una herramienta que distingue «no pude
  comprobarlo» de «comprobé y está mal», que es exactamente la frontera que este
  proyecto lleva tres rondas intentando no cruzar

LO QUE ESTA ENTRADA NO AFIRMA
  que el modelo de layout sea correcto o incorrecto.  No lo he ejecutado.  Que exista
  una herramienta que puede arbitrarlo, y que declare su propia limitación, ya es
  knowledge
  y si al correrla apareciera una contradicción con un hallazgo registrado, el
  arbitraje es de quien lo mide, no de esta tabla

EL BUCLE, Y ESTE TURNO LO HA CERRADO
  mientras documentaba las 76 herramientas de otros, apareció una más.  La cifra pasó
  de 36 guiones en `tools/` a 37, con uno sin documentar, y `drift.py --toolkit` lo
  señaló sin que nadie lo pidiera
      discovering  ->  documentar  ->  la baja
  ese es el ciclo que las herramientas de descubrimiento existen para producir, y esta
  vez se cerró entero en la misma ronda

---

## TL-45 · `docscan --index` — que el índice de hallazgos no esté viejo respecto al árbol

```
PROPOSITO  Indexar los hallazgos que `FINDINGS-INDEX.md` no listaba, sin fingir que
           nadie los ha leído
ESTADO     **TOOL_VALIDATED**, 16 checks, 0 fallos (antes 13)
SEGURIDAD  escribe `FINDINGS-INDEX.md`, y sólo eso.  Inserta filas, no prosa

LA MEDICIÓN QUE LO MOTIVÓ, y la que el usuario señaló en general
  `stale  findings-unindexed  48 of 114 findings are not in the index`
  y detrás de ella la truth de fondo: **el árbol crece varias veces por hora y la
  documentación no le sigue**.  El propio `FINDINGS-INDEX.md` lo avisa en su
  cabecera: «Re-generar antes de citar».  Eso es una instrucción que no se cumple,
  y una instrucción que no se cumple es un defecto del documento, no de quien lo lee

LO QUE HACE, Y POR QUÉ CADA FILA DICE `NO LEIDA`
  el árbol crece a un ritmo que ninguna lectura manual sostiene: 114 hallazgos, 34
  índices duplicados, 3 huecos de numeración.  El índice tenía 48 entradas de menos
  que el directorio, y un índice con 48 huecos deja de ser un índice
  se añade una fila por hallazgo ausente, con:
      #        el prefijo numérico
      Finding  el nombre completo, que es lo único único aquí
      Tema     el TÍTULO H1 que escribe el propio hallazgo
      Estado   TRACKED / UNTRACKED, y `git clean -x` borra los segundos sin rastro
      Sostiene `NO LEIDA — transcripción, nadie lo ha leído`
  y esa última columna es toda la honestidad del modo: la fila dice que el hallazgo
  existe y cómo se llama, y dice que NADIE LO HA ABIERTO.  Un título transcrito no
  es una afirmación sobre el hallazgo
  49 filas añadidas, 0 hallazgos declarados leídos

EL ERROR QUE HIZO LA TABLA INÚTIL, y que casi se me pasa
  la primera ejecución puso `CUDA principal` en las 49 filas
  tomaba el primer H2, y el primer H2 de estos hallazgos es SIEMPRE `## CUDA
  principal`.  Una columna de tema que dice lo mismo en las 49 filas no es una
  columna de tema
  el H1 es donde está el título que el autor escribió.  Corregido, y ahora sale
  `043 · la asercion la hacen 4 sitios`, `040 · el corpus sí describe el binario
  cargado`, y cosas así

DONDE INSERTA, y por qué no al final
  `FINDINGS-INDEX.md` tiene secciones en prosa DESPUÉS de su tabla.  Añadir al final
  del fichero habría enterrado las filas dentro de un ensayo.  Se insertan tras la
  ÚLTIMA fila de la tabla

LO QUE ESTA SESIÓN NO HACE, aunque la tentación existe
  no lee los 49 hallazgos.  Leerlos es trabajo de quien los leyó, y este modo no crea
  claims ni lasOSA
  y el orden importa: indexar es lo mecánico, y leer es lo que produce conocimiento.
  Invertir el orden produciría 49 filas que parecen documentadas y no lo están

UNA CONEXIÓN QUE SALIÓ SOLA AL INDEXAR, y no la buscaba
  indexar puso de manifiesto, de un vistazo, esto:
      finding `043-asercion-struct-mqd-contra-offsets.md`
        «El driver tiene una aserción sobre el hardware que nunca se comprobó»
      herramienta `gccverify.py`   (TL-44)
        escribe un `.c` temporal que incluye la cabecera REAL y pregunta al
        COMPILADOR por `sizeof` y `offsetof`
  dos sesiones convergen en lo mismo desde direcciones opuestas, y el hallazgo es
  del segundo caso y la herramienta del primero.  El hallazgo lo motivó, según su
  propio texto, un «el modelo da 1756, gcc dice 1884»
  ESO ES LO QUE UN ÍNDICE VIGENTE PRODUCE: no una lista, sino la línea entre un
  hallazgo y la herramienta que lo cierra.  No lo registré como claim ni como
  relación verificada: es una observación sobre dos títulos, y los títulos no
  bastan para una afirmación

---

## TL-46 · `docscan --taxonomy` — hacer que el vocabulario cerrado tenga dientes

```
PROPOSITO  Que `TYPE` y `STATE` de cada claim sean UN token de la taxonomía cerrada
           de `AGENTS.md`, y que no lleven prosa detrás
ESTADO     **TOOL_VALIDATED**, 17 checks, 0 fallos
SEGURIDAD  sólo lee.  Es un check más del informe

LA MEDICIÓN QUE LO MOTIVÓ, y era un defecto MÍO
      claims                                            51
      TYPE fuera del vocabulario cerrado                12   (24 %)
      TYPE con token válido Y prosa detrás               9   de esos 12
      STATE fuera del vocabulario cerrado                 0
  así se veían:
      `TYPE DERIVATION + NEGATIVE_RESULT`
      `TYPE OBSERVATION, con medición propia`
      `TYPE MEASUREMENT · y el hallazgo de mayor valor de esta ronda`
      `TYPE CONTRADICTION (resuelta)`
  en cada caso la anotación era CIERTA y útil donde estaba.  Nadie dijo que dejaba
  el campo ilegible, porque nadie lo comprobaba: el vocabulario era una lista, no
  un check
POR QUÉ IMPORTA, y no es pedantería
  un campo que lleva prosa es un campo con el que no se puede comparar.  Cualquier
  herramienta que agrupe claims por `TYPE`, o que rechace una claim cuyo `TYPE` no
  esté en el vocabulario, lee las doce como malformadas y no como los tipos que son
  el daño es silencioso en la dirección MALA: no da error, da una clasificación que
  nadie cuestiona
  y una taxonomía que tolera una segunda frase en su propio campo es una
  taxonomía sin dientes
LO QUE HACE, CUATRO MANERAS DE ESTAR MAL
  1 · `TYPE` que no es un token del vocabulario        -> `taxonomy-type`
  2 · `STATE` que no es un token del vocabulario       -> `taxonomy-state`
  3 · un token válido seguido de prosa                 -> `taxonomy-type`
  4 · una claim sin `TYPE` o sin `STATE`               -> el mismo check
  y una claim bien formada NO se reporta.  El self-test mete las cuatro malas y una
  buena, y exige que se flags las cuatro y sólo ellas
LO QUE SE HIZO CON LAS DOCE, y por qué no se tira la anotación
  `TYPE` queda con un token.  La información muda de sitio:
      ALSO    los tipos secundarios, que es lo que el `+` significaba
      NOTA    la prosa, que es lo que la coma o el punto medio significaban
  el punto medio se trata a mano y no con regla, porque `MEASUREMENT · y el
  hallazgo de mayor valor` separa un término de una NOTA, y una coma separa dos
  términos.  Una regla automática habría fallado justo en esos casos sin que nadie
  lo notara
  `STATE` no necesitó nada: ya estaba limpio, y por eso la auditoría encontró una
  clase y no dos

EL BUG QUE ESTA HERRAMIENTA MIDE, Y QUE YO TENÍA
  el hallazgo `071` de otra sesión cuenta cinco defectos de la misma clase y dice
  que es la quinta vez que ocurre aquí.  Su regla:
      «no existe» sólo es un dato si el índice sobre el que se buscó está
      CONSTRUIDO, y su tamaño se imprime junto al resultado.
      Un `not found` sin cota no es una medida: es un olvido.
  y el bug de `drift.py` —exigir acentos graves, y con eso no ver
  `tools/docscan.py`— es exactamente eso: un método de búsqueda que no alcanza,
  usado para afirmar una ausencia.  Reportó 98 sin documentar cuando eran 76, y dio
  por no vistas las herramientas de esta misma sesión
  `citations.py` e `ipsolve` ya cumplían la regla.  El defecto estaba en la
  herramienta que construí para vigilar esa clase de fallo
  `NR-14` lo cuenta con la cita exacta

LO QUE ESTE CHECK NO HACE
  no decide si un `TYPE` es el correcto para esa claim.  Que `MEASUREMENT` sea el
  token adecuado para `RE-43` es una lectura, y aquí sólo se comprueba que sea un
  token
  no reescribe nada.  `--sync` sigue tocando sólo contadores

---

## TL-46 · `docscan --taxonomy` — hacer que el vocabulario cerrado tenga dientes

```
PROPOSITO  Que `TYPE` y `STATE` de cada claim sean UN token de la taxonomía cerrada
           de `AGENTS.md`, y que no lleven prosa detrás
ESTADO     **TOOL_VALIDATED**, 17 checks, 0 fallos
SEGURIDAD  sólo lee.  Es un check más del informe

LA MEDICIÓN QUE LO MOTIVÓ, y era un defecto MÍO
      claims                                            51
      TYPE fuera del vocabulario cerrado                12   (24 %)
      TYPE con token válido Y prosa detrás               9   de esos 12
      STATE fuera del vocabulario cerrado                 0
  así se veían:
      `TYPE DERIVATION + NEGATIVE_RESULT`
      `TYPE OBSERVATION, con medición propia`
      `TYPE MEASUREMENT · y el hallazgo de mayor valor de esta ronda`
      `TYPE CONTRADICTION (resuelta)`
  en cada caso la anotación era CIERTA y útil donde estaba.  Nadie dijo que dejaba
  el campo ilegible, porque nadie lo comprobaba: el vocabulario era una lista, no
  un check
POR QUÉ IMPORTA, y no es pedantería
  un campo que lleva prosa es un campo con el que no se puede comparar.  Cualquier
  herramienta que agrupe claims por `TYPE`, o que rechace una claim cuyo `TYPE` no
  esté en el vocabulario, lee las doce como malformadas y no como los tipos que son
  el daño es silencioso en la dirección MALA: no da error, da una clasificación que
  nadie cuestiona
  y una taxonomía que tolera una segunda frase en su propio campo es una
  taxonomía sin dientes
LO QUE HACE, CUATRO MANERAS DE ESTAR MAL
  1 · `TYPE` que no es un token del vocabulario        -> `taxonomy-type`
  2 · `STATE` que no es un token del vocabulario       -> `taxonomy-state`
  3 · un token válido seguido de prosa                 -> `taxonomy-type`
  4 · una claim sin `TYPE` o sin `STATE`               -> el mismo check
  y una claim bien formada NO se reporta.  El self-test mete las cuatro malas y una
  buena, y exige que se flags las cuatro y sólo ellas
LO QUE SE HIZO CON LAS DOCE, y por qué no se tira la anotación
  `TYPE` queda con un token.  La información muda de sitio:
      ALSO    los tipos secundarios, que es lo que el `+` significaba
      NOTA    la prosa, que es lo que la coma o el punto medio significaban
  el punto medio se trata a mano y no con regla, porque `MEASUREMENT · y el
  hallazgo de mayor valor` separa un término de una NOTA, y una coma separa dos
  términos.  Una regla automática habría fallado justo en esos casos sin que nadie
  lo notara
  `STATE` no necesitó nada: ya estaba limpio, y por eso la auditoría encontró una
  clase y no dos

EL BUG QUE ESTA HERRAMIENTA MIDE, Y QUE YO TENÍA
  el hallazgo `071` de otra sesión cuenta cinco defectos de la misma clase y dice
  que es la quinta vez que ocurre aquí.  Su regla:
      «no existe» sólo es un dato si el índice sobre el que se buscó está
      CONSTRUIDO, y su tamaño se imprime junto al resultado.
      Un `not found` sin cota no es una medida: es un olvido.
  y el bug de `drift.py` —exigir acentos graves, y con eso no ver
  `tools/docscan.py`— es exactamente eso: un método de búsqueda que no alcanza,
  usado para afirmar una ausencia.  Reportó 98 sin documentar cuando eran 76, y dio
  por no vistas las herramientas de esta misma sesión
  `citations.py` e `ipsolve` ya cumplían la regla.  El defecto estaba en la
  herramienta que construí para vigilar esa clase de fallo
  `NR-14` lo cuenta con la cita exacta

LO QUE ESTE CHECK NO HACE
  no decide si un `TYPE` es el correcto para esa claim.  Que `MEASUREMENT` sea el
  token adecuado para `RE-43` es una lectura, y aquí sólo se comprueba que sea un
  token
  no reescribe nada.  `--sync` sigue tocando sólo contadores

### Herramientas de `revkit/` (segunda ronda de 2026-10-02)

| ID | Herramienta | STATE | Verificado |
|---|---|---|---|
| RK-10 | `sello.py` | `TOOL_VALIDATED` | `custodia` da 106/139/4958/0; rc 0/1/2/3/4 con semántica distinta cada uno; 2 mutaciones detectadas |
| RK-11 | `klog.py` | `TOOL_VALIDATED` | 6 controles con log sintético: dentro del BAR rc=0, fuera rc=1, log incompleto rc=4; las 3 mutaciones detectadas |
| RK-12 | `pte.py` | `TOOL_VALIDATED` | `para-gfx8` cierra el alcance de F2b (15 flags); `dump` **corregido**, tenía el layout hardcodeado |

**Límite de `sello.py --custodia`**, y es el que más fácil se lee mal: para
"recuperable" mira `git ls-tree -r HEAD`, **no** `git ls-files`. El índice de git
es estado compartido entre sesiones en este proyecto, y un fichero stageado sin
commitear aparece en `ls-files` y no es recuperable porque no existe en ningún
commit.

**Límite de `pte.py dump`**, ya corregido pero conviene recordarlo: la tabla de
campos que imprime es la **unión de todas las generaciones**, no el layout de
GFX8. Para GFX8 el campo de dirección acaba en el bit 39 (`pte_addr_mask =
0x000000FFFFFFF000`, 28 bits, ventana de 256 MiB), no en el 47. La asimetría es
que `para-gfx8` **sí** filtra por alcance y `dump` no. `dump` ahora deriva el
ancho de la máscara y avisa de que la tabla es genérica.

**Límite de `klog.py`**: lee texto del log, no hardware. Su único efecto es
decir **si el observador existe y dónde**. La lectura de la tabla GART por BAR
es NIVEL 2 y está en otro sitio, con su credencial.

### Límite de `tools/reg_resolve.py` que conviene saber (2026-10-02)

**`--field` no resuelve campos de GMC.** `resolve_field` construye la ruta
`include/asic_reg/gca/{gfx}_sh_mask.h` (tools/reg_resolve.py:176), y su plan B
busca ficheros `{gfx}*_sh_mask.h`, que tampoco llega a `gmc_*_sh_mask.h`.

`gca/gfx_8_0_sh_mask.h` tiene **cero** apariciones de `VM_INVALIDATE_REQUEST`,
porque el registro es de GMC y no de GCA. Así que:

| modo | alcance | funciona en GMC |
|---|---|---|
| `--reg`, `--resolve` | caminan todo `include/asic_reg` | **sí** |
| `--field` | solo `gca/` | **no** |

Ejemplo que sí funciona, para lo que sí está en su alcance:

```
tools/reg_resolve.py --kernel <raiz> --reg mmVM_INVALIDATE_REQUEST
  -> 5 definiciones, todas 0x51e, en gmc_6_0, gmc_7_0, gmc_7_1, gmc_8_1, gmc_8_2
```

**El prefijo `mm` es obligatorio.** Los símbolos se llaman `mmVM_INVALIDATE_REQUEST`
en el código; sin el prefijo la herramienta responde 0 definiciones, y eso se
lee como una ausencia. Pasó aquí, y casi produce un negativo sobre una
herramienta válida.

Es la misma forma que el caso de `0xBCC` de EV-22: un offset corto existe en
varios bloques de ASIC, y el resolvedor por bloque acierta mientras el
resolvedor por árbol no.

### `/sys/kernel/btf/<modulo>`: el complemento que le falta a `struct_layout.py`

`/sys/kernel/btf/amdgpu` son 3.88 MB de BTF **combinada**, legible por todos,
sin root. La sección `.BTF` del `.ko` está partida y `pahole` sobre el `.ko`
falla con *"Malformed BTF string section, did you forget to provide base
BTF?"*. La combinada la compone el kernel en tiempo de carga.

**Que resuelve**: los layouts de struct **del driver cargado**, con nombres de
campo y offsets, incluidos los **tipos primitivos del kernel** que el corpus no
resuelve.

```
pahole -C amdgpu_bo /sys/kernel/btf/amdgpu
  u64  flags;   /*  584  8 */      <-- el offset 0x248, el que cerró F13
```

**Y el límite de `tools/struct_layout.py`, para no esperar de él lo que no
hace**:

```
struct_layout.py --struct amdgpu_vm_bo_base
  TAMANO None   CONFIANZA NULA
  tipos no resueltos: ['struct list_head sin medir']

struct_layout.py --struct amdgpu_vm
  tipos no resueltos: ['struct rb_root_cached sin medir', 'struct mutex sin medir',
                       'spinlock_t', 'struct amdgpu_mem_stats sin medir',
                       'struct list_head sin medir', 'struct list_head sin medir']
```

No resuelve los tipos primitivos del kernel. **No es un problema de raíz**: se
probó con `baseline/linux-7.1.3` (parcial, sin `include/linux/`) y con
`kernelbuild/linux-7.1.3` (completo, con `list.h`, `mutex.h`, `spinlock.h`),
y el resultado es idéntico.

Lo que hace **bien** es degradar a `CONFIANZA NULA` con la lista de lo que no
resolvió, en vez de devolver un número. Por eso se puede confiar en lo que sí
dice, y por eso `CONFIANZA NULA` debe leerse como "esto no lo sé", nunca como 0.

**Uso recomendado**: las dos son complementarias, no intercambiables.

| fuente | cuando |
|---|---|
| `struct_layout.py` | el `.h` del struct **y** los tipos que incruste están en el corpus |
| `/sys/kernel/btf/amdgpu` | siempre, y además da los tamaños de los tipos del kernel |

Para un driver propio, un layout no se deduce: se lee. Ahora hay dos lecturas
independientes donde antes había una, y era parcial.

## `pm4dec.py`: la tabla de opcodes ya no sale de `sid.h` (2026-10-02)

**Defecto corregido.** La tabla se sacaba de un solo fichero, `sid.h`. Eso está
mal por dos motivos opuestos, y con el mismo síntoma: un opcode mal nombrado.

| | con solo `sid.h` | con `vid.h` (ahora) |
|---|---|---|
| `0x49` `RELEASE_MEM` | sin nombre | `PACKET3_RELEASE_MEM` |
| `0x58` `ACQUIRE_MEM` | sin nombre | `PACKET3_ACQUIRE_MEM` |
| `0x79` `SET_UCONFIG_REG` | sin nombre | `PACKET3_SET_UCONFIG_REG` |
| `0x5F` | `LOAD_CONFIG_REG` **falso** | `LOAD_SH_REG` |
| `0x60` | `LOAD_CONTEXT_REG` **falso** | `LOAD_CONFIG_REG` |
| `0x61` | `LOAD_SH_REG` **falso** | `LOAD_CONTEXT_REG` |

`sid.h` es el header de SI/GCN1 y su numeración va **una posición desplazada** en
los tres `LOAD_*`. Los tres opcodes que sí faltan estaban en el anillo de
**compute** capturado, así que no eran hipotéticos.

**Cómo se decide ahora la cabecera.** Leyendo el **grafo de includes** del
`.c` que emite el anillo, no por orden de ficheros:

```
gfx_v8_0.c  ->  vid.h   y ningun otro header de opcodes
```

`cargar_opcodes(fuente=...)` devuelve `(tabla, cabecera_usada)`, y la segunda
pieza va también a la salida del CLI. Antes el CLI ponía `"desde sid.h"` fijo,
que era **falso**: una etiqueta con la forma de un dato.

**El filtro `__`.** El generador del ASIC usa `_` simple para un opcode y `__`
doble para un sub-campo. Sin ese filtro, `nvd.h` metería 109 enumeraciones de
campo (28 sobre el opcode `0x00`) y `soc15d.h` 58. Con `vid.h` **no hace nada**:
`vid.h` tiene 0 de 70. Está por las otras dos generaciones, y el control que lo
vigila se escribe contra `nvd.h` precisamente porque contra la tabla por defecto
**no podría fallar nunca**.

**Aviso de validez del paseo.** `pm4dec` ahora mide qué fracción de las
cabeceras aparentes reciben nombre. En el anillo de **SDMA** son 0 de 118: ese
anillo no es PM4, sus dwords son dato, y antes se publicaba `paquetes : 17` como
si fuera una medida. El aviso **no** sale en el anillo GFX, que es el otro
sentido en que puede fallar.

**Uso.**

```
pm4dec.py <anillo>                      # usa la cabecera del emisor (vid.h)
pm4dec.py --sid <ruta>/sid.h <anillo>   # fuerza una cabecera concreta
```

**Estado**: `VALIDATED`. `cn7.py` 81 controles, 0 fallos; 4 mutantes medidos que
tumban 5, 1, 1 y 2 controles respectivamente.

### Addendum: sexta cabecera, y cross-check con `tools/rx550ref`

`tools/rx550ref` —de otra sesión, y que no depende de nada mío— implementa la
misma regla que `cargar_opcodes(fuente=)` pero para cualquier símbolo, y pregunta
*"¿el consumidor incluye de verdad la cabecera que gana?"*. Su
`rx550ref.c:30` lleva escrito, desde antes:

> `gfx_v8_0.c does not include sid.h ... It includes vid.h.`

Así que **EV-35 es `CORROBORATED`, no un hallazgo mío**, y la herramienta
ajena además **detectó un fallo mío**: `--sym PACKET3_RELEASE_MEM` reporta **5**
definiciones donde yo tenía **4**. El quinto es `gfx_v12_1_pkt.h` (NAVI 12.1,
solo `gfx_v12_1.c`), que se me había olvidado. Ahora `HEADERS_OPCODE` audita
**seis**.

| fuente | cabecera que sale del include graph | opcodes |
|---|---|---|
| `si.c` | `sid.h` | 74 |
| `gfx_v7_0.c` | `cikd.h` | 66 |
| `gfx_v8_0.c` | `vid.h` | **70** |
| `gfx_v9_0.c` | `soc15d.h` | 70 |
| `amdgpu_gfx.c` | `nvd.h` | 116 |
| `gfx_v12_1.c` | `gfx_v12_1_pkt.h` | 62 |

Anadir el sexto header **no cambia** la tabla de GFX8 — el include graph sigue
ganando con `vid.h` — y solo mejora el diagnóstico de conflictos, que pasa de
**4 contra 1** a **5 contra 1** contra `sid.h`.

**Lo que NO resulta afectado, comprobado**: `tools/pm4census.py` no resuelve
opcodes desde cabeceras, trabaja sobre llamadas `PACKET3(OP, n)`. Ni le afecta el
desplazamiento de `sid.h` ni la contaminación con `__`. Lo verifiqué en vez de
suponerlo; mi preocupación inicial era infundada.

**Cuidado con `sid.h`**: hay **4** ficheros con ese nombre en este árbol y no son
el mismo —`amd/amdgpu/sid.h` por triplicado y `radeon/sid.h`, otro driver—. El
texto de `tools/constmap.py` dice "TEN"; medido aquí son 4. `AMBIGUOUS` está bien
planteado, el número no. No se toca `constmap.py` por ser de otra sesión.

## `btfsnap.py`: guardar los layouts que salen de la BTF, que es perecedera

**Por qué existe.** `/sys/kernel/btf/<modulo>` es NIVEL 2 (leer un fichero de
`/sys`) y **es perecedero**: es por arranque, y en esta máquina incluso se
reescribió *dentro* del mismo arranque (04:54 con el boot a las 00:10). Cuando el
layout haga falta y no esté guardado, ya no habrá de dónde sacarlo.
`pahole` sobre el `.ko` **no** es alternativa: la sección `.BTF` del `.ko` está
partida y falla con *"Malformed BTF string section"*.

Lo que se guarda no es la BTF (3.88 MB, no versionable) sino los **layouts ya
resueltos**, en texto y con su procedencia: sha256 de la BTF, bytes, mtime,
`uname -r`, versión de `pahole` e invocación. Eso es lo que sirve para un driver
propio — offsets y tamaños, no el índice de tipos.

```
btfsnap.py                 # escribe revkit/btf-<modulo>-layouts.txt
btfsnap.py --listar        # estado y tamaños, no escribe
btfsnap.py --comparar      # deriva contra lo guardado; rc=1 si la hay
btfsnap.py --selftest      # 6 casos de los caminos de fallo
```

**`NO_EN_BTF` no es `PROVEN_ABSENT`.** La BTF del módulo solo cubre los tipos que
el módulo exporta, así que que un struct falte **no dice nada del kernel**.
Medido: `amdgpu_bo` sí está (712 bytes) y `drm_bo` **no**, pero `drm_gem_object`
(368) sí: es un **renombrado** en este kernel, no una ausencia.

**Pago ya cobrado**: el snapshot dice `u64 flags; /* 584 8 */` dentro de
`struct amdgpu_bo`, y **584 = 0x248**. Eso corrobora `EV-33` y, a diferencia de la
medida en vivo, **sobrevive al reinicio**.

**Dos defectos que tuvo y se cazaron antes de usarse**

1. `--comparar` daba **deriva falsa en cada ejecución**: la línea `generado` lleva
   la hora y cambia siempre, así que `previo != texto` era siempre cierto. Un
   detector que siempre dice que algo cambió no detecta nada. Ahora compara el
   texto **normalizado** y, cuando hay deriva de verdad, dice en qué línea.
   Provocado: 0 → 1 → 0.
2. `--structs ""` caía **en silencio** a la lista por defecto: el usuario pedía
   nada y recibía todo. Ahora es `rc=5` y lo dice.

Además, un `NameError` propio en un generador roto, que reventó antes de escribir
nada.

**Estado**: `VALIDATED`. 6 casos de fallo con rc comprobados (2 BTF ausente,
3 sin `pahole`, 4 nada resoluble, 5 `--structs` vacío), y `--selftest` **provocado**
con un mutante que reinstala la sustitución silenciosa: sale `rc=1`.
Registrado en `check.sh`.

## `pub.sh`: la puerta de salida, porque el orden de los pasos era el fallo

**EL FALLO QUE CIERRA, y es medido, no previsto.** El orden que yo seguia a mano
era:

```
1. correr la suite      2. anexar los documentos del turno
3. git add              4. git commit
```
El paso 1 corria sobre un arbol **que ya no era el que se iba a commitear**.
Pasó dos veces en la misma sesion: en una, mi NR abrio un fence sin cerrar y
entro en un commit con la suite en verde; en la otra, dos bloques quedaron con la
paridad rota. `cn8` tenia los controles que lo habrian cazado —los_controls
existen desde la ronda anterior— y no se ejecutaron despues de anexar. **El
control existia; lo que faltaba era que alguien lo ejecutara en el momento que
importa.**

Un hueco de proceso se cierra con estructura, no con disciplina.

**USO**

```
pub.sh <fichero-de-mensaje> <ruta> [<ruta> ...]
```
El mensaje va en un **fichero**, no en un heredoc: se puede revisar antes de
publicar, y un mensaje improvisado en el momento de publicar es justo cuando uno
se precipita. Se exigen **3 lineas** con texto: un commit de una linea no deja
constancia de por que se hizo.

Las rutas se stagean **de forma explicita**, nunca `git add .` ni
`git add <dir>`: el arbol lo editan varias sesiones a la vez y un add de directorio
se llevo 20 ficheros ajenos en `d2c4a89`. Y despues se **verifica** que nada
fuera de las rutas se ha colado, en vez de confiar en que `git add -- rutas` hace
lo que parece.

**CODIGOS**: `0` verde y commit hecho · `2` la suite fallo, **no** se commitea ·
`3` uso incorrecto · `4` no habia cambios en las rutas dadas · `5` fallo de git.

**VALIDACION: la puerta tiene que poder negarse.** Probada en los dos sentidos,
sobre el arbol de trabajo y con la suite real:

```
M-A  fence sin cerrar en un documento          rc=2, NO COMMITEA, nada stageado
M-B  caracter CJK en un fichero de revkit      rc=2, NO COMMITEA
     arbol limpio                              rc=0, commitea
     rutas sin cambios                         rc=4
```
Y con la suite en verde pero el mensaje de una linea, `rc=3` sin llegar a correr
nada: la puerta se cierra antes de gastar cuatro validaciones.

**Cuatro defectos propios que tuvo, cazados al usarla**

1. `cd "$AQUI"` antes de resolver las rutas: `git add docs/...` fallaba con *"no
   concuerda con ningun archivo"*. Las rutas se resuelven **antes** del `cd`.
2. La comprobacion de "fuera de las rutas" comparaba rutas absolutas contra
   nombres de git relativos, y decia que el unico fichero stageado estaba fuera
   de la ruta que se habia pedido, que era ese mismo fichero.
3. `RAIZ="$AQUI/.."` sin normalizar: el prefijo era `.../revkit/..` y no casaba
   con ninguna ruta real, con lo que **todo** salia "fuera".
4. `grep -c ... || echo 0` imprimia `0` **dos veces**, porque `grep -c` sale con 1
   cuando no encuentra nada.

Y uno que no es del script sino del árbol, que encontró la puerta al construirse:
`CN-R12` ("sin CJK ni cirilico") estaba en `FALLO` porque **yo habia metido un
caracter CJK en el propio `pub.sh` al escribirlo**. Habia 35 ficheros con CJK en
el repositorio, casi todos de otras sesiones; el control mira `revkit`, y el unico
culpable nuevo era este fichero nuevo.

## `pub.sh` y `pub_selftest.sh`: la puerta de salida, y por que es testeable

**EL FALLO QUE CIERRA, medido.** El orden que yo seguia a mano era
suite, anexar documentos, `git add`, commit. **El paso 1 corria sobre un arbol que
ya no era el que se iba a commitear.** Dos veces en la sesion: un fence sin
cerrar y dos bloques con la paridad rota entraron en commits con la suite en
verde. `cn8` tenia los controles que lo habrian cazado y no se ejecutaron
despues de anexar. El control existia; faltaba que alguien lo ejecutara cuando
importa.

```
pub.sh <fichero-de-mensaje> <ruta> [<ruta> ...]
pub.sh --selftest
pub.sh --repo DIR --suite DIR ...
```
El mensaje va en un **fichero** para revisarlo antes, y se exigen **3 lineas con
texto**. Y hay un segundo filtro que no es un filtro de lineas: un mensaje que sean
mayoritariamente `"uno"`, `"dos"`, `"tres"`, `"prueba"`... se rechaza. Tres lineas
de relleno **cumplen** el requisito de tres lineas, y por eso entro `"uno dos
tres"` en la historia de este arbol.

**POR QUE ES TESTEABLE, que era lo que faltaba.** La primera version no lo era:
comprobar que la puerta "se niega a commitear" exigia mutar el arbol de verdad, las
pruebas acababan en arbol limpio, y la puerta commiteaba. De ahi salio el commit
basura (`NR-2026-10-02-w`). Con `--repo` y `--suite` se fabrica un repositorio con
`git init` y cuatro stubs de la suite en un temporal, y **los 14 caminos se
prueban sin tocar el arbol real**, en un segundo.

**LOS 14 CASOS, Y POR QUE ALGUNOS SON NEGATIVOS**

```
todo verde -> commitea                          rc=0
sin cambios que publicar                      rc=4
check.sh / cn7 / cn8 / selfcheck falla         rc=2   (cuatro casos, uno por suite)
mensaje de una linea                          rc=3   sin correr nada
mensaje de relleno                            rc=3
sin fichero de mensaje                        rc=3
sin argumentos                                rc=3
ruta que no existe                            rc=5
un rechazo no deja rastro                     rc=2, HEAD igual, nada stageado
en verde commit solo lo pedido                 solo f.txt
stageado de mas -> se niega y lo saca         rc=5, el ajeno fuera
```
Los dos ultimos son los que importan para una puerta. Un rechazo que deja el
indice sucio hace que el siguiente `git commit` a mano se lleve lo que la puerta
acabo de rechazar. Y un commit en verde que arrastra un fichero ajeno es
exactamente lo que paso en `d2c4a89` con 20 ficheros de otra sesion.

**VALIDACION POR MUTACION, sobre la puerta**

```
MA  la puerta deja de negarse si la suite falla        5 casos en rojo
MB  acepta un mensaje de relleno                       6 casos en rojo
MC  ignora lo stageado de mas                          1 caso  en rojo
MD  dice que saca lo ajeno y no lo saca                3 casos en rojo
    (incluido "el commit contiene docs/a.md f.txt")
original                                                14 OK, rc=0
```
**MC solo se pudo encontrar porque el caso no existia.** Con la comprobacion de
"nada fuera de las rutas" puesta a `if false`, el selftest se quedaba **en
verde**: ningun caso llegaba a ejercitarla, porque en todos los casos lo stageado
era justo lo pedido. Una guardia sin prueba es una guardia que no existe, y esa
existe porque un `git add` de directorio se llevo 20 ficheros ajenos. El caso que
faltaba se escribio despues, y el primer version de ese caso tampoco servia:
`git add` sobre un fichero **sin modificar** no stagea nada, con lo que pasaba por
la puerta sin tocarla.

**Defectos del propio selftest, corregidos al escribirlos**

1. `"$PUB0"` con comillas es **una sola palabra**: bash buscaba un comando llamado
   `bash -c`. Cuatro casos en rojo por eso.
2. `git show --stat` no da la lista de ficheros: hay que leer
   `--name-only --format=`.
3. El caso del "stageado de mas" hacia `git add` de un fichero sin cambios, que no
   stagea nada, y por tanto no probaba la guardia.
4. La asercion de ese caso exigia que no quedara nada stageado, cuando lo correcto
   es que **desaparezca el ajeno**: `f.txt` si pertenece y debe quedarse. Una
   puerta que se llevara tambien lo suyo seria peor.

## `ipver_zero.py` (otra sesion): que mide bien, y que no mide

**NO la he tocado.** Vive en `08-ARQUITECTURA/tools/`, que es de otra sesion. Solo
la he ejecutado y le he medido los limites, que es lo que se documenta aqui.

**Contrato verificado por mi, no de palabra:** `READONLY=yes`, `WRITES_FILES=no`,
`WRITES_SYSFS=no`, `MUTATES_CORPUS=no`, `WRITES_GPU=no`. Ejecutada sobre
`RESEARCH/baseline`, sin efectos.

**`VALIDATED` por su propio selftest:** 16 vectores, 4 controles, 2 de pipeline,
`rc=0`. Y el selftest cubre justo el fallo que haria la herramienta inerte: el
docstring avisa de que sin parentesis escapados la regex no casa nada, y el
selftest lo detecta. Es un ejemplo de lo que debe hacer una comprobacion de
herramienta, y por eso lo cito.

**Salida real medida:** 18 ficheros comunes, 50 sitios = 46 comparaciones
(8 SIEMPRE, 38 NUNCA) + 4 `switch` no evaluados. Los 8 y los 4 casan con lo que
la otra sesion corrigio en `185` y `190`.

**Limite 1, ya declarado por la propia herramienta.** Los `switch` no se evaluan: se
listan. Correcto, porque un `switch` sobre un valor degenerado no casa ningun caso
y eso es informacion, no una comparacion que se pueda chiffrar. Aun asi, listarlos
deja al lector el trabajo, y el resultado bonito ("8 SIEMPRE") no dice que hay 4
sitios sin clasificar.

**Limite 2, que NO declara, y es el que me ha servido.** Clasifica la
**expresion**, no el **alcance**. Una comparacion puede ser `SIEMPRE`/`NUNCA` y
estar en codigo que en esta placa no se ejecuta nunca: de sus 46 comparaciones,
**5 estan en `amdgpu_mes.c`** (`682, 683, 755, 756, 758`), cuyas funciones
enclosing no tienen ningun llamador alcanzable desde la ruta VI. Se quedan **41**
comparaciones que gobiernan el comportamiento real. La herramienta es correcta
sobre lo que afirma y **silenciosa** sobre lo que no mide.

**Por que lo anoto en vez dearlo.** Un censo de 46 que en realidad son 41 no es un
error de la herramienta: es un **eje que le falta**, y es el mismo eje que me hizo
fallar con mi propio grep de 260 (`NR-2026-10-02-z`). La leccion general es que un
inventario necesita una columna de *alcanzabilidad*, y ningun inventario que yo haya
escrito la tiene. Propuesta, no hecha: anadir a `ipver_zero.py` una columna
`alcance` con la funcion enclosing y si tiene llamador en ficheros ejecutables.
**No la implemento: el fichero es de otra sesion y no esta en mi lock.**

## `gfx8blocks.py` y `gchwip_alcance.py`: la superficie de bloques y el alcance

**Que resuelven, y por que en ese orden.** `gfx8blocks` responde "que hardware
tengo que encender para arrancar esta placa". `gchwip_alcance` usa esa respuesta
para responder "de las comparaciones degeneradas de `GC_HWIP`, cuales estan en
codigo que no se ejecuta". El segundo **depende del primero**, y por eso estan
registrados juntos en `check.sh`: si el primero falla, el segundo puede estar
descartando sobre una lista equivocada sin que se note.

```
gfx8blocks.py [--self-test] [--corpus DIR] [--asic=CHIP_X]
   RC 0 lista, 3 lista vacia o sin incondicionales, 1 error de entrada,
      3 exclusividad no demostrada

gchwip_alcance.py [--self-test]
   compone con 08-ARQUITECTURA/tools/ipver_zero.py y NO re-deriva el censo.
   Si no parsea ninguna fila, se NIEGA a seguir en vez de devolver una lista
   vacia con exito.
```
**`gfx8blocks.py` · `VALIDATED`.** 17 vectores y controles, `rc=0`. Mutaciones
sobre copias, todas cazadas:

```
M1  sin acotar la busqueda a la funcion                9 controles en rojo
M2  sin comprobar la exclusividad de las dos rutas      1 control  en rojo
M3  clasificacion de condicional invertida              4 controles en rojo
M5  los DOS guardias de lista vacia a False             1 control  en rojo
M4  UN solo guardia a False                             NO es una mutacion
```
**M4 no es una mutacion**, y la distincion importa: hay dos guardias y el segundo
subsume al primero, asi que quitar uno no cambia el comportamiento. Una mutacion
que no cambia nada no se puede cazar, y su no-captura no es un hueco del test.

**`gchwip_alcance.py` · `VALIDATED`.** 21 vectores, `rc=0`. Cuatro mutaciones,
todas cazadas: `N1` ficheros-no-vivos nunca declara nada (5), `N2` vuelve a
descartar por falta de llamador (2), `N3` cuenta declaraciones de `.h` como
llamadas (7), `N4` vuelve a truncar el nombre en la salida (1).

### Los CATORCE DEFECTOS QUE TUVIERON, Y POR QUE NO LOS CUENTO COMO HERRAMIENTA UTIL

Cada uno fue **medido**, no supuesto, y cada uno es una clase de error que ya me
ha costado trabajo antes en este proyecto:

```
1  devolvio "total 0" con rc=0        parser que no encuentra nada y reporta exito
2  troceaba por etiqueta de case    en C, case NO delimita codigo: las etiquetas
                                    consecutivas comparten un cuerpo, y
                                    case CHIP_POLARIS12 cae en case CHIP_VEGAM
3  buscaba la etiqueta en todo .c   vi.c tiene OCHO "case CHIP_POLARIS12:"; cogia
                                    el de la linea 274, en otra funcion, con 0
                                    bloques. ACOTAR, LUEGO EMPAREJAR
4  exigia firma y llave en la misma linea   aqui van separadas
5  off-by-one al leer la llave siguiente     comparaba la firma contra "{"
6  clasificacion de condicional invertida   un bloque SIN condicion salia
                                            CONDICIONAL: los 6 primeros
7  shutil.copy conservo permisos de solo lectura   la mutacion reventaba con
                                            PermissionError en vez de probar nada
8  el grafo no salia del fichero              amdgpu_mes_init_microcode se llama
                                            desde mes_v11_0.c, y salia "no llamada"
9  un continue se comia la asignacion         fn era None en el 100% de los sitios
10 resetear en columna 0 rompia con #endif   lo que delimita un cuerpo es la
                                            PROFUNDIDAD DE LLAVES, no el sangrado
11 la firma de la definicion contaba como llamada   una funcion se llamaba a si
                                                    misma en su linea de definicion
12 una declaracion en .h contaba como llamada
13 "sin ningun llamador" se leia como muerto    esta EXACTAMENTE al reves: lo
                                                    llama el KERNEL (dma_buf_ops)
14 el formateador %-32s truncaba el nombre      39 caracteres impresos como 32,
                                                    inventando OTRO identificador
```
**El 13 es el que mas me gusta**, porque es una regla que yo mismo enuncia mal:
*"no tener llamadores no es estar muerto"*. No es "no está vivo", es **"no lo
llama el texto del driver"**, que incluye los fops de DRM, los ioctl y el
sysfs. Descartar ahi es un falso positivo de manual.

**Y el mas instructivo es el 14.** El defecto estaba en la CAPA DE SALIDA, y mi
primera comprobacion miraba el diccionario interno de datos, que ya traia el
nombre entero. El test pasaba en verde con el bug presente. **Un test de salida
tiene que mirar la salida.** Es el mismoPrincipio que "verificar que la salida
pertenece al comando ejecutado", pero aplicado a una capa de la que ni me habia
dado cuenta.

**Y una retirada de pretension.** `gchwip_alcance` primero cerro el grafo de
alcance para decidir que ficheros eran vivos, y con un **recall medido del
96,2%** (de 835 funciones declaradas en `amdgpu_*.h`, el indice pierde 32)
descartaba de mas: entre otros a `amdgpu_device_init`, que es **LA** funcion de
inicializacion. Con un 4% de perdida, un filtro **no puede descartar**: uno de
cada 25 veredictos es dudoso. Lo que sustituyo ahi fue el cierre de grafo por un
**hecho** --"este fichero solo implementa un bloque que no existe en esta
placa"--, que si es solido. **Un filtro que descarta necesita hechos, no
aproximaciones.** Esta es la correccion de razonamiento mas importante de la
ronda, y llego por el lado equivocado: primero cerre el grafo, y el grafo no
resolvia el problema que yo creia.

## `gfx8blocks.py --funcs`: la superficie de entrada por puntero a funcion

Amplia `gfx8blocks.py`, que ya resolvia que bloques existen, a **que funciones
registra cada bloque en su tabla `.funcs`**. De 10 bloques salen **145 funciones**.

```
gfx8blocks.py --funcs
   por bloque: nombre, tabla .funcs, numero de funciones y FICHERO donde se define
   rc 0 con lista, 3 si salen 0 funciones
```
**`VALIDATED`. 24 vectores.** Mutaciones sobre copias: `Q1` buscar las tablas solo
dentro de `amdgpu/` cae (1 control), y la deduccion de que el bloque y su tabla
se llaman igual cae y **deja a 5 de 10 bloques sin tabla**, que es la medida de
cuanto importa.

**Dos mutaciones NO cazadas, y las dos eran mutaciones mias, no huecos:**

- Una que solo anadia un comentario `MUTADO` sin cambiar nada. **Una mutacion
  inerte no puede fallar**, y su no-captura no dice nada del test.
- Una que volvia vacio un control (`or True`). **Un control vacio no puede
  fallar por definicion.** Instrumentar un control para que no pueda fallar es
  retirar el control dejandolo puesto.

**LIMITE DECLARADO en la propia salida:** solo las tablas `.funcs`. No los fops
de DRM, ni `dma_buf_ops`, ni `file_operations`, ni sysfs ni debugfs, que tambien
entran por puntero y son la via del kernel. Evict de VRAM, por ejemplo, no pasa
por ninguna tabla `.funcs`.

**LO QUE ESTA HECHO PARA QUE NO SE REPITA** (los tres casos aparecen aqui):
el bloque no es la tabla, el bloque no es el fichero, y el bloque no esta en
`amdgpu/`. El self-test comprueba **los nombres de los ficheros** donde se
definen los diez, no solo que exista tabla, precisamente porque el fallo que
cae es "no lo he mirado en el sitio correcto", no "no existe".

## `bootcheck.py` (RK-12): el arranque como observable reutilizable, con su control dentro

**Que resuelve.** Los cuatro `dev_err` de fase de inicializacion son un
**observable generico** de "esta placa no arranco bien". Un driver propio necesita
exactamente esa comprobacion para validar su propio arranque, y no habia ninguna
herramienta que la hiciera.

```
bootcheck.py --self-test
bootcheck.py --log <fichero>          # por defecto stdin
   rc 0 los cuatro controles pasan
      3 algun control en rojo
      4 INVALID_RESULT: el log no es reconocible, y NO es lo mismo que un arranque limpio
```

**LOS CUATRO CONTROLES**

```
C0  el log es de esta placa y es legible           <-- CONTROL, no resultado
C1  estan los 9 bloques de Polaris12, con su tabla
C2  ninguna fase de inicializacion fallo
C3  el kernel nombro POLARIS12
```

**EL DISENO, Y SALE DE DOS ERRORES MIOS DE LA RONDA ANTERIOR.**

1. **La entrada es un FICHERO, no una tuberia.** Si la herramienta ejecutara
   `journalctl` ella misma, un fallo de su propio pipeline seria indistinguible de
   un arranque limpio. Eso es exactamente el error de `NR-2026-10-02-d2`, donde dos
   ceros falsos salieron de una redireccion metida en una variable. Con fichero de
   entrada se puede probar contra logs **sinteticos**, y ahi si se ve si el control
   funciona.
2. **C0 va primero y gobierna el resultado.** Si el log no contiene nada
   reconocible, la herramienta **no dice "cero fallos"**: dice `INVALID_RESULT` y
   sale con `rc=4`. **Un cero sin prueba no se reporta**, y el 0 de C2 aparece
   siempre al lado de C0, que es su control.

**`VALIDATED`. 10 vectores, cinco mutaciones cazadas sobre copias.**

```
R1  sin el control C0                        4 controles en rojo
R2  C2 invertido (pasaria un arranque roto)  5 controles en rojo
R3  un bloque de menos en la lista esperada  selftest rc=1
R4  la regex pasa a tolerar doble espacio    1 control  en rojo, y es el que fija el bug
R5  ASIC esperado equivocado                3 controles, y la ejecucion real da rc=3
original                                     10 OK, rc=0
```

**Y UN TEST QUE ES UNA BUG FIJADO.** El ultimo vector comprueba que un **doble
espacio** entre `>` y `(` hace que la linea **no** cuente como bloque. Es el bug que
me produjo la falsa contradiccion de EV-42, y aqui esta **declarado como
comportamiento esperado**. Convertir una trampa silenciosa en un test es la
diferencia entre un artefacto y una costumbre.

**CONTRA EL LOG REAL.** `1211` lineas, `68` de amdgpu, **9** bloques, **0** fallos de
fase, ASIC `POLARIS12`: los cuatro controles en verde, `rc=0`.

**LIMITE DECLARADO en la propia salida, que es la parte que importa.** Esto dice lo
que el driver **IMPRIMIO**, no lo que el hardware **HIZO**. Que ninguna fase fallo
**no es** que el hardware quedara bien: eso sigue `NOT_DETERMINED` sin lectura de
registros. Y es la muestra de **un** arranque: un verde no garantiza que los otros
arranquen igual, que es justo lo que `243` y `258` ya sufrieron con `MemTotal`.

**POR QUE LA LISTA DE BLOQUES NO ESTA INVENTADA AQUI.** Viene de `gfx8blocks.py` mas
lo `OBSERVED` en EV-42, y si el kernel cambiara la lista esta herramienta falla. Eso
es lo correcto: una lista de bloques copiada a mano en dos sitios es dos sitios que
se desincronizan, que es la clase de error que vengo pagando desde EV-35.

**Defectos mios en esta herramienta, tres, y los tres los encontre yo al releerla:**

1. Escribi cinco caracteres **cirilicos** en un comentario, la misma clase
   de contaminacion que acababa de ampliar el guardIAN. No los cito: el
   guardiano es absoluto y no tiene escape, y meter un caracter para
   ilustrar el defecto es justo lo que el control prohibe. Inmediatamente despues de
   ampliarlo: el defecto estaba en el Production, no en el control.
2. Escribi un control como `(not C0) and C0`, que es **siempre falso**: un control
   que no puede pasar. Y era redundante con el de al lado, que si distingue.
3. Un `len()` sobre un `bool` en un caso limite.

**El primero es el que mas dice:** ampliar un guardián no sirve si la fuente que lo
salta es el mismo sitio donde se acaba de escribir. El control y el error estan en la
misma accion, y por eso el control no llego a tiempo. **Hay que releer lo que uno
acaba de escribir, y releer no es lo mismo que pasar el control.**

## `gputel.py` (RK-13): la cadena de hardware, con las unidades verificadas

**Que resuelve.** `bootcheck` valida lo que el driver **imprimo**. `gputel` mide
lo que el hardware **hizo**: relojes, tension, potencia, temperatura, y los
limites de potencia. Es la primera lectura de hardware real accesible sin root en
esta maquina, porque `/sys/kernel/debug/dri/` sigue en `EACCES`.

```
gputel.py --self-test
gputel.py [--n=N] [--intervalo=S] [--card=cardN]
   por defecto n=5, intervalo=1.0 s, card1
   rc 4 si no hay arbol hwmon: eso es INVALID, y NO es "cero"
```

**LAS UNIDADES, Y LAS DOS QUE ESTABAN MAL.**

```
freq*_input   Hz        <-- NO la convencion de hwmon (MHz)
power*_input  uW        <-- NO mW: 35000000 seria 35 kW, imposible
power*_cap*   uW        limite del hardware, no muestra
in0_input     mV · temp*_input mC · fan*_input RPM · pwm* /255
```

**Y UN CONTROL DE PLAUSIBILIDAD**, disfrazado de rango fisico: un cap de potencia
tiene que caer entre 5 y 500 W. Si alguien vuelve a cambiar la escala, salta
**antes** de que el numero llegue a un documento. Y el control se prueba con la
unidad **erronea** a proposito, porque con la correcta no puede fallar.

**`VALIDATED`. 23 vectores, cuatro mutaciones cazadas sobre copias:**

```
T1  la potencia vuelve a mW                       3 controles en rojo
T2  se quita la conversion Hz -> MHz              1 control  en rojo
T3  la plausibilidad deja de juzgar                1 control  en rojo
T4  se acepta resumir con una sola muestra        1 control  en rojo
original                                           23 OK, rc=0
```

**TRES DEFECTOS DE DISENO Y TRES DE TEST, y el patron se repite.**

1. **El lector de ficheros era fijo**, con lo que tres muestras de un fichero que
   no cambia dan tres valores identicos y el recorrido es 0 siempre: **la
   herramienta era incriticable sin hardware**. Ahora el lector se **inyecta**.
2. **`LIMITE_PPM` se comparaba contra PORCENTAJE**: 20000 ppm contra `2.0 %`
   daba `> 200`, un umbral que no podia pasar. **Un umbral con la unidad
   equivocada es un control que no mide nada y encima da sensacion de medir.**
3. Los tests **afirmaban sobre los datos en vez de sobre el comportamiento**, con
   lo que T1 y T4 pasaban: T1 llevaba la unidad escrita a mano mientras la real
   vive en la tabla `MEDIDAS`, y T4 miraba el numero de muestras en vez del
   texto que sale por pantalla. **Un control tiene que leer el valor del sitio
   donde vive, y tiene que ejecutar el camino que dice comprobar.**

**LIMITE DECLARADO en la salida.** No mide un techo. La GPU no se ha puesto bajo
carga, asi que los relojes maximos son `NOT_DETERMINED`. Y `gpu_busy_percent` es
lo que el driver **afirma**, no una medida.

## `cn8.py`: las TRES categorias de salida, y por que `INVALID` no es `FALLA`

**Que cambia.** Antes `cn8` tenia dos salidas: verde y `rc=1`. Todo lo que no
salia bien acababa en el mismo sitio, y eso mezclaba **tres cosas distintas**:

```
rc=0   todo pasa
rc=1   ALGO esta mal en el proyecto (un documento, un control)
rc=1   la HERRAMIENTA no ha podido comprobar nada (fichero ausente, ilegible)
```
Las dos ultimas se leian igual, y quien lo lea obtiene la conclusion
equivocada: **si el fichero no existe, el proyecto no esta roto; la herramienta
no pudo correr.** Es el mismo principio que el `C0` de `bootcheck` y el `rc=4` de
`gputel`, aplicado a `cn8`, que era el que se quedaba sin el.

**AHORA.**

```
todo bien ................. rc=0    41 controles OK
propiedad violada ......... rc=1    1 FALLA,   0 INVALID   <- el documento esta mal
fichero ilegible .......... rc=4    0 FALLA,   1 INVALID   <- la herramienta no pudo leer
```

**MEDIDO, no declarado.** Las tres lineas son salidas reales, no una intention:

- `rc=0`: la suite completa en verde.
- `rc=1`: mutando la ventana a `-1` (impossible por construccion), con el
  detalle `la mas reciente es 2026-10-03, hace 0 dias`.
- `rc=4`: apuntando la lectura a un fichero inexistente. **Antes eso era un
  `FileNotFoundError` con traceback**, que es lo que se arreglo aqui.

**UN HALLAZGO SOBRE EL ENMASCARAMIENTO, que casi me hace dudar de la prueba.**
La primera vez que intente demostrar el `rc=1` mutando la ventana a `0` dias, el
control **paso en verde**. La razon: mi commit de ese mismo dia habia anadido una
cabecera `## 2026-10-03`, luego `_edad = 0` y la ventana `0` se cumplia sola. O
sea que **la mutacion no era mala: los datos habian cambiado de tal modo que la
propiedad era cierta de verdad.** Eso es, irónicamente, la mejor prueba de que
el control mide algo real y no un literal: **cambia con los datos, y no con el
codigo que lo rodea.** Se rehizo la demostracion con ventana `-1`, que es
imposible, y ahi si falla.

**LA REGLA, FORMULA.** *Una herramienta que no puede comprobar nada debe decirlo
con una categoria propia, no con la de "ha fallado".* Si comparte categoria,
quien lee tiene que adivinar cual de las dos cosas pasó, y **en el caso de los
controles esa adivinanza se paga en confianza**: un control que reporta "FALLA"
cuando en realidad no pudo mirar enseña a ignorar sus FALLA de verdad.

**Y LO QUE NO SE HA ARREGLADO.** El guardia de "no hay ninguna cabecera
`## AAAA-MM-DD` en el CHANGELOG" sigue **sin probar**, porque en este proyecto
siempre hay fechas. Es un guardia escrito y no ejercitado, y queda anotado como
tal en vez de darse por bueno.

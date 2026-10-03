# CHANGELOG-RESEARCH — cambios de conocimiento, no de comandos

> Se registra lo que cambia **el estado del proyecto**: conocimiento, clasificación,
> herramienta, contradicción, frontera, dependencia. No cada comando.
> Cada entrada dice `OLD STATE → NEW STATE`, con la evidencia que lo fuerza.
>
> Formato de cada entrada: `DATE · AGENT · ACTION · OBJECT · OLD STATE → NEW STATE ·
> EVIDENCE · DEPENDENCIES · UNLOCKS · RISKS`

---

## 2026-10-02 · opencode · EV-35 · la tabla de opcodes de `pm4dec`

```
OBJECT   revkit/pm4dec.py (carga de opcodes) y su salida
ACTION   CORRECTION + NEW LIMIT
EVIDENCE EV-35; NR-2026-10-02-l, -m, -n, -o
DEPENDENCIAS  lectura cruzada de findings/135 (otra sesion, commit 6f197ce)
```

**OLD STATE → NEW STATE**

- La tabla de opcodes venía de **un solo** fichero, `sid.h`, elegido por costumbre.
  → NEW: se elige leyendo el **grafo de includes** del `.c` que emite el anillo.
  Para GFX8 eso es `vid.h`, porque `gfx_v8_0.c` incluye `vid.h` y ningún otro
  header de opcodes. `PROVEN` sobre el corpus.
- `0x49`, `0x58` y `0x79` salían como opcode desconocido, y los tres **están en el
  anillo de compute capturado**. → NEW: nombrados. `PROVEN_ABSENT` en `sid.h`.
- En cambio, leer `sid.h` nombraba **mal** `0x5F`, `0x60` y `0x61`: su numeración
  de `LOAD_*` va una posición desplazada respecto de los otros cuatro headers.
  → NEW: nombrados según `vid.h`. Este defecto lo **introduje yo** al arreglar el
  anterior por mezclar los cinco headers, y lo detecté midiendo en vez de dar por
  buena la primera versión.
- El CLI imprimía `opcodes cargados : 74 desde sid.h` con la tabla de `vid.h`.
  → NEW: `70 desde vid.h (lo que incluye gfx_v8_0.c)`. Etiqueta falsa corregida
  en la salida, no en un comentario.
- El CLI imprimía `paquetes : 17` para el anillo SDMA0, donde **0 de 118**
  cabeceras aparentes reciben nombre. → NEW: avisa de que el paseo no aplica y de
  que ese número no es una medida. `NOT_APPLICABLE` del paseo PM4 a SDMA.
- La rama "la fuente incluye más de un header" de `cargar_opcodes()` se daba por
  verificada. → NEW: `PROVEN_ABSENT` **medido sobre 625 ficheros**: 75 incluyen al
  menos uno y ninguno incluye dos. La rama es **inalcanzable**, o sea declarada y
  **no validada**.

**Lo que NO cambia, comprobado y no supuesto.** De los 8 opcodes que usan
`EV-21`..`EV-30` —incluido `0x3F = INDIRECT_BUFFER`, del que dependen los 8 IB de
`EV-29`—, **0 de 8 dependen de la elección de cabecera**: los cinco headers
coinciden. `EV-21`..`EV-30` quedan intactas.

**UNLOCKS**

- El anillo de compute ya se puede nombrar entero en vez de "2 paquetes".
- La regla "el generador usa `__` para un sub-campo" queda utilizable para
  cualquier generación, no solo GFX8.

**RISKS**

- La tabla de `vid.h` es la de **GFX8**. Para un anillo de un productor NAVI o MI
  hay que pasar `fuente=`; si no, el nombre sería de otra generación. Queda
  declarado, no resuelto.
- Un `0` con el patrón pegado al componente sale bien formado y no significa nada.
  Me pasó en esta misma ronda (`NR-2026-10-02-o`) y casi lo dejo como evidencia.

**VALIDACIÓN**

```
cn7.py        rc=0   81 OK   0 FALLA
mutante M1    rc=1    5 FALLA   (tabla de sid.h)
mutante M2    rc=1    1 FALLA   (sin filtro "__")
mutante M3    rc=1    1 FALLA   (aviso siempre activo)
mutante M4    rc=1    2 FALLA   (capturas SDMA borradas; ya no pasa en vacio)
check.sh      rc=0   34 OK
cn8.py        rc=0   30 OK
selfcheck.py  rc=0   30/30
```

**Corrección propia del mismo día**: `decodifica()` tenía dos docstrings seguidos;
el primero era una expresión muerta y documentaba un retorno de 3 elementos
cuando el real es de 4.

**Reclasificación y segunda corrección, con herramienta ajena.** `EV-35` queda
**`CORROBORATED`, no descubrimiento mío**: `tools/rx550ref.c:30`, de otra sesión,
lleva escrito desde antes *"gfx_v8_0.c does not include sid.h ... It includes
vid.h"* — la misma regla, aplicada de forma más general. Y esa herramienta
**detectó un fallo mío**: reporta **5** definiciones de `PACKET3_RELEASE_MEM`
donde yo tenía **4**; el quinto es `gfx_v12_1_pkt.h` (NAVI 12.1), que se me había
olvidado. `HEADERS_OPCODE` pasa a auditar seis cabeceras, y el diagnóstico de
conflictos pasa de 4 contra 1 a **5 contra 1** contra `sid.h`. La tabla de GFX8
no cambia: el include graph sigue ganando con `vid.h`.

**Comprobado que NO resulta afectado**: `tools/pm4census.py` no resuelve opcodes
desde cabeceras, sino sobre llamadas `PACKET3(OP, n)`. Ni el desplazamiento de
`sid.h` ni la contaminación con `__` le afectan. Mi preocupación inicial era
infundada, y se resolvió midiendo en vez de suponiendo.

**Deuda declarada**: cito `sid.h` sin cualificar 65 veces, y hay **4** ficheros
con ese nombre en el árbol —`amd/amdgpu/sid.h` por triplicado y `radeon/sid.h`,
que es otro driver—. El texto de `tools/constmap.py` dice "TEN"; medidos son 4.
No se reescriben las 65 en este commit porque mezclan contenido de otras
sesiones; la deuda queda contada, no escondida.

---

## 2026-10-02 · opencode · RK-10 · `btfsnap.py`, los layouts de la BTF, que es perecedera

```
OBJECT   revkit/btfsnap.py (nuevo) + revkit/btf-amdgpu-layouts.txt
ACTION   NEW TOOL + snapshot + CORROBORATION de EV-33
NIVEL    2 (leer /sys/kernel/btf/amdgpu), sin instrumentacion
```

**OLD STATE → NEW STATE**

- Los layouts de struct se podian leer de `/sys/kernel/btf/amdgpu`, que es **por
  arranque** y en esta maquina se reescribio dentro del mismo arranque (04:54 con
  el boot a las 00:10). No havia copia. → NEW: `btfsnap.py` guarda 12 layouts ya
  resueltos, en texto y **versionados**, con sha256 de la BTF, bytes, mtime,
  `uname -r` y version de `pahole`. La BTF se pierde; el fichero no.
- `EV-33` (`bo->flags` = `u64` en 0x248) estaba corroborado solo por la lectura
  en vivo. → NEW: el snapshot lo lleva escrito (`u64 flags; /* 584 8 */`), con
  584 = 0x248, y sobrevive al reinicio. `CORROBORATED`.
- `NO_EN_BTF` no era una categoria de la herramienta. → NEW: existe y significa
  otra cosa que `PROVEN_ABSENT`. Medido: `drm_bo` no esta y `drm_gem_object` si,
  luego es un **renombrado** en este kernel. La BTF del modulo solo cubre lo que
  el modulo exporta.

**Defectos propios cazados antes de usar la herramienta**

1. `--comparar` daba **deriva falsa en cada ejecucion**, porque la linea
   `generado` lleva la hora y `previo != texto` era siempre cierto. Un detector
   que siempre dice que algo cambio no detecta nada. Provocado: 0 → 1 → 0.
2. `--structs ""` caia **en silencio** a la lista por defecto: sustitucion
   silenciosa de lo que se pidio. Ahora `rc=5`.
3. Un `NameError` en un generador roto, que revento antes de escribir nada.

**VALIDACION**

```
--selftest            6 casos de fallo, rc comprobados: 2, 3, 4, 5, 0 y 0
selftest con mutante  rc=1   (el mutante reinstala la sustitucion silenciosa)
check.sh rc=0  35 OK  (btfsnap registrado en la suite)
cn7 rc=0 83 | cn8 rc=0 30 | selfcheck rc=0 30/30
```

**Lo que sigue bloqueado, sin cambio**: `F12` necesita root (la credencial se
perdio al reiniciar) y ademas un anillo con `vm_flush`, que no aparece en las 4
capturas. `RX550_SUDO_PASS` comprobada esta ronda: **ausente**. F2b y F14
siguen igual.

---

## 2026-10-02 · opencode · EV-36 · el flag EXPLICIT_SYNC no decide cómo pasar un IB

```
OBJECT   revkit — ninguna; esto es una pregunta que yo mismo tenía abierta
ACTION   ANSWER, con la premisa previa RETIRADA
```

**Pregunta que yo dejé abierta**: ¿el scheduler usa
`bo->flags & AMDGPU_GEM_CREATE_EXPLICIT_SYNC` para decidir cómo pasar un IB?

**OLD STATE → NEW STATE**

- Pregunta abierta, sin respuesta. → NEW: **la premisa era falsa**.
  `amdgpu_cs_sync_rings()` corre **antes** de `amdgpu_cs_submit()`, que es donde
  se emiten los IB, y `sync_rings` no escribe un solo dword. El flag no toca el IB.
- → NEW: lo que decide es el **modo de dependencia de fence**:
  `AMDGPU_SYNC_EXPLICIT` frente a `AMDGPU_SYNC_NE_OWNER`
  (`amdgpu_cs.c:1220`). Y en modo `EXPLICIT`, `amdgpu_sync_test_fence` devuelve
  `false` **siempre**: **no se añade ninguna dependencia implícita**.
- → NEW: los fences de VM y de KFD se descartan antes del `switch` cuando el
  owner no es `UNDEFINED`. Aquí el owner es `&fpriv->vm`, luego **los fences de
  actualización de VM nunca crean una dependencia de job por esta vía**.
- → NEW: `AMDGPU_SYNC_ALWAYS` es un **miembro muerto del enum**. 2 apariciones en
  todo el árbol —definición y `case`—, en los tres árboles del corpus. Los otros
  tres modos tienen 5 puntos de llamada reales. `PROVEN_ABSENT` de llamador.

**Por qué grep del nombre no bastaba**: `EXPLICIT_SYNC` da 3 coincidencias y
ninguna es el consumidor real — una es un `case` de un flag de GEM, otra un
`print`, y la tercera el **accesor** `amdgpu_bo_explicit_sync`. El consumidor está
una capa más abajo, en `amdgpu_cs.c`. "3 coincidencias, ninguna usa el flag" se
lee como "no influye", y sí influye. `NR-2026-10-02-p`.

**Lo que NO toca**: ni el contenido del IB, ni el `count` de `EV-30`, ni los 8 IB
de `EV-29`. Es lógica de CPU anterior a emitir. Para un driver propio: el modo
explícito **no** compra sincronización gratis.

---

## 2026-10-02 · opencode · RK-11 · cn8 vigila la integridad de formato de docs/

```
OBJECT   revkit/cn8.py + docs/
ACTION   NEW TOOL CAPABILITY + deuda de formato ACREDITADA y fijada
ORIGEN   la suite estaba en verde con un NR mio que abria un ``` y no cerraba
```

**OLD STATE → NEW STATE**

- `cn8` no miraba fences ni cabeceras duplicadas. Un documento podía estar
  partido sin que nada se enterara. → NEW: dos controles, ambos con **deuda
  medida y fijada como conjunto**, no como exigencia de cero.

**La deuda, medida el 2026-10-02**

```
fences impares        EVIDENCE-MATRIX.md, CONTRADICTIONS.md,
                      MASTER-RESEARCH-STATUS.md      (los demas 14 dan par)
cabecera duplicada    TOOLS-STATUS.md -> "## TL-46 · docscan --taxonomy" (x2)
```

**Por qué fijar la deuda en vez de arreglarla**: son documentos de otras
sesiones, y un cierre de fence puesto en el sitio equivocado parte el bloque de
alguien. Pero sin el control, un documento **nuevo** roto pasa en verde. Fijar el
conjunto da las dos cosas.

**El control tiene tres sentidos, y se provocaron los tres**

```
nuevo fence impar en un documento hoy par     rc=1
cabecera duplicada nueva                      rc=1
ARREGLAR la deuda preexistente                rc=1
```

El tercero es el que obliga a.updatear la lista a propósito: si alguien arregla
el duplicado de `TOOLS-STATUS`, el conjunto deja de cuadrar y hay que ir a
cambiar la constante. Sin eso, la deuda se olvidaría sola.

**Dos defectos míos que los controles ya cogen**: un ` ``` ` que abrí sin cerrar
en `NR-2026-10-02-s`, y la corrección de F12 **duplicada** en `OPEN-FRONTIERS`
por un script de reubicación con un bug de búsqueda. Los dos entraron con la
suite en verde antes de existir el control; ahora no pueden entrar.


---

## 2026-10-02 · opencode · EV-38 · tres codificadores de PTE, y la mascara se lee en un solo sitio

```
OBJECT   docs/EVIDENCE-MATRIX.md, revkit/cn7.py
ACTION   MEASURE + NEW TOOL CAPABILITY + CORRECTION de mi propia formulacion
ORIGEN   una anotacion de otra sesion en el writer de PDE, verificada al margen
```

**OLD STATE → NEW STATE**

- La anotacion de otra sesion decia "la CPU enmascara, la SDMA no". → NEW: es
  cierto pero **incompleto**. No son dos codificadores sino **tres**, y difieren
  en **dos** ejes, no en uno:
  - **enmascarado**: solo la ruta CPU;
  - **ancho de escritura**: CPU hace un `writeq` (un store de 64 bits); la ruta
    SDMA de una sola PTE parte el valor en **dos** stores de 32 bits dentro de un
    paquete **SDMA** `SDMA_OP_WRITE`/`SDMA_SUBOP_WRITE_LINEAR` — que no es PM4, es
    el otro motor; y la ruta de lote ni siquiera emite, arma el `u64` dentro del IB.
- → NEW: `pte_addr_mask` tiene **una sola lectura** en todo el driver, en
  `amdgpu_gmc.c:173`, y esa es la **ruta CPU**. Las dos rutas SDMA —la efectiva
  bajo la política de esta placa— **no la consultan**.
- → NEW: `PROVEN_ABSENT` de cualquier guardia que compruebe el ancho. No por no
  haberlo buscado: se buscaron otras formas (`ADDR_MASK`, `MAX_VA`, `addr >> 39`,
  `WARN_ON`). Los `WARN_ON` de `amdgpu_vm_sdma.c:116,122` son de **espacio en el
  IB**, y `amdgpu_gmc.c:1413` valida **rangos de VRAM**.
- → NEW, y es la frontera que importa para un driver propio: la mascara de esta
  generacion es `0x000000FFFFFFF000`, bits **[39:12]**, o sea **28 bits** de
  direccion y ventana de 256 MiB. Para direcciones legales la mascara **no quita
  nada** y las tres rutas escriben igual (`PROVEN_DERIVED`, es aritmética). En
  cuanto una PA necesite **más de 28 bits sobre el offset —PA >= 2^40—** la CPU
  trunca y SDMA no, y **nada avisa**.

**CORRECCION A MI FORMULACION.** Escribi antes "el ASIC instancia
`gmc_v8_1_0`". Es engañoso: `gmc_v8_1_ip_block` (`gmc_v8_0.c:1768`) es un
**descriptor de version de IP** (`.major = 8, .minor = 1`) que comparte
`.funcs = &gmc_v8_0_ip_funcs`. **No hay implementación v8_1 separada** — el
fichero ni existe. Igual con `gmc_v8_5_ip_block`. La ASIC lee 8.1 u 8.5 y **ambas
resuelven a las mismas funciones**, luego la mascara de `gmc_v8_0.c:1134` aplica
sea cual sea la revisión.

**Y un casi-retiro mio que no hacia falta.** Al ver `0x000000FFFFFFF000` dudé que
fueran 28 bits y estuve a punto de corregir `pte.py` y su control, que lo
afirmaban. Los conté con Python: `bit_length() - 12 == 28`, ventana `2^28` =
256 MiB. **Estaban bien.** El error era mío de leer el hex: 7 nibbles `F` son 28
bits, no 32.

**Mi control cometia el error que EV-38 demuestra** (`NR-2026-10-02-t`). Buscaba
la mascara con grep por todo el árbol sin fijar generación. Al mutar la de
`gmc_v8_0.c` a 36 bits, **pasó en verde**: leía la de `gmc_v6_0.c` o `gmc_v7_0.c`,
que tienen **el mismo valor**. Un control que verifica la tesis equivocada es una
tautología. Corregido fijando el fichero, y con un control que falla si el valor
leído cambia.

**VALIDACION POR MUTACION, sobre copia WRITABLE del corpus**

```
M1  la ruta SDMA pasa a consultar la mascara      4 controles FALLAN
M2  la mascara de gmc_v8_0 pasa a 36 bits         2 controles FALLAN
original                                            91 OK, rc=0
```

**Y el control de fences de la ronda anterior funcionó sobre mi de inmediato**: en
esta ronda abrí un ``` en `NR-2026-10-02-t` sin cerrarlo, y `cn8` lo cazó en la
misma pasada. Antes habría entrado con la suite en verde.

check.sh rc=0 35 | cn7 rc=0 91 | cn8 rc=0 32 | selfcheck rc=0 30/30
GPU INTACTA. WRITE_EXECUTION NONE. NIVEL 0/1.

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

---

## 2026-10-02 · opencode · EV-37 · el censo es 49 de 49, no 50 de 50

OBJECT   revkit — ninguna; esto es una cuenta mia que nadie habia comprobado
ACTION   MEASURE + CORRECTION en 5 sitios de 4 documentos
ORIGEN   al verificar por fin una lista de opcodes escrita a mano desde hacia dias

**OLD STATE → NEW STATE**

- "50 de 50 emisiones de `gfx_v8_0.c` reconcilian", repetido en 5 sitios de 4
  documentos. → NEW: **49 de 49 sitios de emision distintos**. La razon: `6078`
  (`INDIRECT_BUFFER_CONST`) y `6080` (`INDIRECT_BUFFER`) son las **dos ramas del
  mismo `if/else`** sobre un unico `header`, y solo se escribe uno.
  `pm4census` cuenta 50 porque ve dos `PACKET3(`.
- El texto decia "las 7 restantes" con una tabla de 6 filas. → NEW: la septima
  era precisamente el brazo duplicado. Con eso la aritmetica cierra exacta:
  **43 automaticas + 6 a mano = 49**.
- Una lista propia de 17 opcodes "que cuelgan de RE-30". → NEW: **retirada**,
  ver `NR-2026-10-02-r`.

**La salvedad que faltaba, y es la importante: `NOP` NO obedece la regla.** El
relleno se escribe `.nop = PACKET3(PACKET3_NOP, 0x3FFF)`: el campo `count` va a
`0x3FFF` a proposito, como valor de relleno. "49 de 49" **no incluye** los 3
sitios de `NOP` y no afirma que cumpla `count = payload − 1`. Para un driver
propio: `NOP` es relleno de anillo, no un paquete con 16383 dwords.

**PROCEDENCIA, y esto importa mas que la cifra.** Los tres arboles del corpus
tienen un `gfx_v8_0.c` **byte-identico** (sha `2427f5b5`, 7206 lineas), pero
existe una cuarta copia, `rx550-upstream-7.2.8/linux-7.2.8`, con **7209 lineas**
(sha `fd1f3e4b`). `pm4census` **sin `--kernel`** reporta 7209: esta leyendo
**linux-7.2.8**, no el 7.1.3 que corre el host. Con `--kernel` a 7.1.3 reporta
7206 y cuadra. Ademas `--fichero <ruta>` esta roto: 0 emisiones y 0 lineas
leidas. No se toca `pm4census` —es de otra sesion—, pero su etiqueta *"el
fichero que esta GPU ejecuta"* es **falsa en la invocacion por defecto**, que es
justo lo que hace que una cifra buena se aplique al fichero equivocado.

**Reconciliacion con `findings/135` de otra sesion, que NO era contradiccion.** 135
cuenta 20 paquetes alcanzables; yo cuento 26 emitidos. Su universo son los **119
definidos en `sid.h`**, y de mis 26 solo 20 estan en `sid.h`. Los 6 restantes son
exactamente los que EV-35 demostro que `sid.h` no declara. Su 20 y mi 26 son el
mismo hecho sobre universos distintos, y EV-35 explica la diferencia.

**Sin cambio de bloqueos**: `F12` sigue sin credencial y sin anillo con
`vm_flush`. `RX550_SUDO_PASS` ausente, comprobado otra vez esta ronda.

---

## 2026-10-02 · opencode · F12 · EACCES leido como NOT_FOUND, y un tercer bloqueo

OBJECT   docs/OPEN-FRONTIERS.md (F12), docs/NEGATIVE-RESULTS.md
ACTION   CORRECTION de diagnostico + NEW blocker + NEW observador identificado
ORIGEN   una busqueda de limitaciones, prompted por pm4census leyendo 7.2.8

**OLD STATE → NEW STATE**

- F12 estaba anotado como "`/sys/kernel/debug/dri/0/` no existe". → NEW: eso era
  **EACCES leido como NOT_FOUND**. El padre es `0700 root:root` y debugfs esta
  montado, con lo que todo lo que hay debajo devuelve EACCES y **no se puede
  saber si existe**. Clasificacion correcta: `BLOCKED_BY_PERMISSION`.
  `NR-2026-10-02-s`.
- F12 tenia **dos** bloqueos anotados. → NEW: hay un **tercero, medido**, y es
  independiente: **no hay ningun cliente DRM abierto** (0 coincidencias de
  `/dev/dri/*` en `/proc/*/fd`), y los directorios de debugfs de amdgpu son **por
  cliente**. Sin cliente no hay `dri/<minor>/`, tenga root o no la tenga.
- F2b venia dariendose por bloqueada "falta observador". → NEW: existe un
  observador **upstream**, `amdgpu_debugfs.c:2585` registra
  `vm_pagetable_info` con modo `0444`, presente en los tres arboles del corpus.
  Sigue siendo `BLOCKED_BY_PERMISSION` — no se ha obtenido ni un byte — pero deja
  de ser "no hay observador", afirmacion que se daba por buena sin mirar.

**Lo que no se ejecuta.** `/dev/dri/renderD128` es `crw-rw-rw-`, o sea que abrir
un cliente DRM no requiere permiso. Aun asi **no se abre**: es NIVEL 3, toca el
driver, y solo se justificaria con un discriminante que cierre algo. Anotado como
ruta, no ejecutado.

**Tambien medido, sin relacion con F12.** Los arboles `baseline` y `working` de
7.1.3 son **byte-identicos**: 2787 ficheros, 0 diferencias. `kernelbuild` tiene
los mismos 2787 pero **4 distintos**, y son `amdgpu_debugfs.c`, `amdgpu_debugfs.h`,
`amdgpu_vm.c` y `amdgpu_vm_pt.c` — es decir, la instrumentacion que otra sesion
anadio, no una version distinta del kernel. Herramientas que leen distintotrees
leen el mismo kernel, salvo que lean kernelbuild.

**Lo que otra sesion dejo anotado en el writer de PDE** y que toca F2b:
la ruta **CPU enmascara `pt` a `pte_addr_mask`** (`amdgpu_gmc.c:171`) mientras la
ruta **SDMA guarda `addr|flags` sin enmascarar** (`amdgpu_vm_sdma.c:197`). Los dos
escritores codifican la direccion distinto. Registrado, pendiente de verificar
con mis propias vias.

---

## 2026-10-02 · opencode · EV-38bis · el codificador vivo es el de SDMA v3.0, y hay un cuarto

```
OBJECT   docs/EVIDENCE-MATRIX.md (EV-38), revkit/cn7.py
ACTION   CORRECTION de mi propia cita + NEW codificador + control que DERIVA
ORIGEN   comprobar si habia repetido el error de generacion, al revisar EV-38
```

**OLD STATE → NEW STATE**

- EV-38 citaba `sdma_v2_4.c` como la ruta SDMA de esta ASIC. → NEW: es la
  **generación equivocada**. Medido: `vi.c:2113` instala `sdma_v3_1_ip_block`
  para `CHIP_POLARIS12`, y ese bloque comparte `sdma_v3_0_ip_funcs`
  (`sdma_v3_0.c:1699`). El codificador vivo es `sdma_v3_0_vm_write_pte`.
- EV-38 decía **tres** codificadores. → NEW: son **cuatro**, y el que faltaba es
  el más importante:

```
ruta                donde (VIVO)                ENMASCARA   como escribe
CPU                 amdgpu_gmc.c:173-175       SI          writeq
SDMA count<3        sdma_v3_0.c:952            NO          addr|flags por software,
                                                          split de 32 bits
SDMA count>=3       sdma_v3_0.c:982            NO          SDMA_OP_GEN_PTEPDE,
                                                          10 dwords, con campo
                                                          "mask" y campo "value"
SDMA en lote        amdgpu_vm_sdma.c:276-279   NO          u64 armado en el IB
```

- → NEW: el criterio de elección es **`count < 3`** (`amdgpu_vm_sdma.c:196`).
  Con 1–2 entradas el software hace el OR y **no hay máscara**. Con **3+** el
  hardware recibe los flags **como campo "mask"** y la dirección **sin
  enmascarar, como "value"**: **el AND lo hace el propio SDMA**.
- → NEW: el camino de lote usa `copy_pte_num_dw = 7`, no 10.

**Lo que esto significa para un driver propio**: los dos caminos SDMA **no son
dos formas de escribir lo mismo**. Uno expresa el contrato como "valor ya
combinado" y el otro como "máscara hardware + valor". Quien escriba el suyo tiene
que elegir cuál de las dos semánticas reproduce, y **solo una tiene un campo de
máscara en el hardware**.

**El control dejó de llevar nombres de fichero escritos a mano** (`NR-2026-10-02-u`).
Ahora deriva: `case CHIP_POLARIS12` **dentro de** `vi_set_ip_blocks` → bloque de
SDMA → fichero que lo define → `.funcs` → tabla `amdgpu_vm_pte_funcs` →
`.write_pte`, `.set_pte_pde`, `.copy_pte_num_dw`.

**Y mi derivación tuvo el defecto que pretendía cazar**: la primera versión
buscaba `case CHIP_POLARIS12:` en el fichero entero, y `vi.c` tiene **ocho**
casos en switches distintos; cogía el primero, que no es `vi_set_ip_blocks`, y
volvía a dar `sdma_v2_4_ip_block`. Anclado a la función.

**VALIDACIÓN POR MUTACIÓN**

```
M1  la ruta SDMA consulta la mascara                    4 controles FALLAN
M2  la mascara de gmc_v8_0 a 36 bits                   2 controles FALLAN
M3  el case de POLARIS12 instala sdma_v4_0 (Navi)       4 controles FALLAN
M4  copy_pte_num_dw pasa a 10                           1 control   FALLAN
original                                                 97 OK, rc=0
```

`check.sh` 35 | `cn7` 97 | `cn8` 32 | `selfcheck` 30/30. GPU INTACTA.

---

## 2026-10-02 · opencode · pub.sh, y dos procedure-fallos mios al probarlo

```
OBJECT   revkit/pub.sh (nuevo) + docs/TOOLS-STATUS.md
ACTION   NEW TOOL (la puerta de salida) + declaracion de dos fallos propios
```

**POR QUÉ LA PUERTA.** El orden que yo seguia a mano era suite, anexar,
`git add`, commit. **El paso 1 corria sobre un arbol que ya no era el que se
commiteaba.** Paso dos veces en la sesion: un fence sin cerrado y dos bloques con
la paridad rota entraron en commits con la suite en verde. `cn8` tenia los
controles que lo habrian cazado y no se ejecutaron despues de anexar. El control
existia; faltaba que alguien lo ejecutara cuando importa.

**Y LA PUERTA ENCONTRÓ ALGO AL CONSTRUIRSE**: `CN-R12` ("sin CJK ni cirilico")
estaba en FALLO porque **yo habia metido un caracter CJK en el propio `pub.sh` al
escribirlo**. En el repositorio hay 35 ficheros con CJK, casi todos de otras
sesiones; el control mira `revkit`, y el unico culpable nuevo era este.

**Cuatro defectos propios del script**, cazados al usarlo: `cd` antes de resolver
rutas; comparacion absoluto-contra-relativo; `RAIZ` sin normalizar, con lo que
todo salia "fuera"; y `grep -c || echo 0` imprimiendo el 0 dos veces.

**VALIDACION DE LA NEGATIVA**, que es lo que importa en una puerta:

```
fence sin cerrar en un documento     rc=2, no commitea, nada stageado
caracter CJK en un fichero de revkit rc=2, no commitea
arbol limpio                         rc=0, commitea
rutas sin cambios                    rc=4
mensaje de una linea                 rc=3, sin correr nada
```

**Y DOS FALLOS DE PROCEDENCIA MIOS AL PROBARLA** (`NR-2026-10-02-w`):

1. **Use la herramienta de produccion como banco de pruebas.** Las pruebas de
   mutacion acababan con el arbol limpio, asi que la puerta commiteaba de verdad.
   Dos commits "uno dos tres" entraron en la historia. Uno se deshizo; **el otro
   no**, porque otra sesion commiteo encima y el `reset --soft` quedo sin efecto.
   `f4e7493` sigue siendo ancestro de HEAD.
2. **El codigo esta a salvo y la traza esta mal.** El `pub.sh` de HEAD es
   **identico** a `f4e7493`, con todas las correcciones. Pero el commit que lleva
   el codigo tiene el mensaje "uno dos tres", y el commit con el mensaje real
   lleva solo la documentacion. Se declara en vez de fingir que no ha pasado: no se
   reescribe historia compartida porque eso tocaria commits de otras sesiones.

**Lo que no se hizo y es lo que debia hacerse**: probar la puerta sobre un clon
del arbol, como se hizo con el resto de pruebas de mutacion, y nunca contra el
arbol real.

check.sh rc=0 35 | cn7 rc=0 97 | cn8 rc=0 33 | selfcheck rc=0 30/30
GPU INTACTA. WRITE_EXECUTION NONE. NIVEL 0/1.

---

## 2026-10-02 · opencode · `pub.sh` ya es testeable: 14 caminos sobre un repo de mentira

```
OBJECT   revkit/pub.sh, revkit/pub_selftest.sh, revkit/check.sh, docs/TOOLS-STATUS.md
ACTION   NEW TOOL CAPABILITY (la puerta deja de necesitar el arbol real para probarse)
```

**EL HUECO QUE CIERRA ESTE.** En la ronda anterior declare —con razon— que probar
la puerta habia exigido mutar el arbol de verdad, y que por eso habia acabado en
un commit basura. Eso no era una observacion: era un **hueco de diseño**. Una
puerta que no se puede probar sin tocar el arbol real se acaba probando contra el
arbol real, y el resultado es un commit con el mensaje `"uno dos tres"` en la
historia para siempre.

Con `--repo` y `--suite` se fabrica un repo con `git init` y cuatro stubs en un
temporal, y los **14 caminos** se prueban en un segundo sin tocar nada real. El
selftest esta en `check.sh`, asi que tampoco se puede publicar sin que pase.

**UN HUECO DENTRO DEL HUECO.** El caso que verificaba la guardia de "nada fuera de
las rutas" **no existia**: en todos los casos lo stageado era justo lo pedido, con
lo que poner la comprobacion a `if false` dejaba el selftest **en verde**. Una
guardia sin prueba es una guardia que no existe. El caso se escribio, y su primera
version tampoco servia —`git add` de un fichero sin modificar no stagea nada— asi
que pasaba por la puerta sin tocarla.

**DEFECTOS DEL PROPIO SELFTEST**, cuatro, corregidos al escribirlo: `"$PUB0"` con
comillas es una sola palabra y bash buscaba un comando `bash -c`;
`git show --stat` no da la lista de ficheros; el caso anterior; y la asercion
final exigia que no quedara nada stageado cuando lo correcto es que **desaparezca
el ajeno**, porque `f.txt` si pertenece y debe quedarse.

**Y UN FILTRO NUEVO QUE NO ES DE LINEAS.** Tres lineas de relleno **cumplen** el
requisito de "3 lineas con texto", y por eso entro `"uno dos tres"` en la
historia. Ahora un mensaje mayoritariamente hecho de `"uno"`, `"dos"`, `"tres"`,
`"prueba"`... se rechaza con `rc=3` antes de correr nada.

**VALIDACION POR MUTACION DE LA PUERTA**

```
MA  deja de negarse si la suite falla     5 casos en rojo
MB  acepta un mensaje de relleno          6 casos en rojo
MC  ignora lo stageado de mas             1 caso  en rojo
MD  dice que saca lo ajeno y no lo saca   3 casos en rojo
original                                 14 OK, rc=0
```
`check.sh` 36 con el selftest dentro | `cn7` 97 | `cn8` 33 | `selfcheck` 30/30.
GPU INTACTA. WRITE_EXECUTION NONE. NIVEL 0/1.

---

## 2026-10-02 · opencode · EV-39: `GC_HWIP` vale 0, y de ahi salen el flush de TLB, la rama de los codificadores y la ausencia de MES

```
OBJECT   docs/EVIDENCE-MATRIX.md (EV-39, NO stageado), CURRENT-STATE.md,
         NEGATIVE-RESULTS.md, KNOWLEDGE-GRAPH.md, TOOLS-STATUS.md
ACTION   EVIDENCE (cadena cerrada de 5 eslabones) + CORRECTION DE ALCANCE
TRACK    STATIC · WRITE_EXECUTION=NONE · RUNTIME=NOT_RUN · GPU INTACTA
```

**LA CADENA, Y EL ESLABON QUE FALTABA.** La otra sesion dio por hecho que
`ip_versions[GC_HWIP][0] == 0` en Polaris12. Es cierto, y se prueba en cinco
eslabones, todos de esta sesion: `devm_drm_dev_alloc` -> `kzalloc(
sizeof(struct amdgpu_device))` -> el array nace a cero -> `amdgpu_ip_version` lo
lee tal cual -> **nadie lo escribe en la ruta VI** (los ocho escritores son
valores fijos `9.x`/`10.x`).

El eslabon que faltaba en cualquier lectura ingenua es el `kzalloc`: no basta con
que nadie escriba el campo, hace falta que **el `struct` entero se reserve a
cero**. Y hay que ir a `kernelbuild` a verlo, porque **el core de DRM no esta en
`baseline` ni en `working`**, que son arboles parciales con solo
`drivers/gpu/drm/amd/`. De no haberlo mirado, EV-39 entera habria quedado
`NOT_DETERMINED` por una limitacion mia del corpus, y habria declarado ausente
algo que existe.

**LO QUE CIERRA.** El flush de TLB en la actualizacion de page tables no es
"solo que el codigo lo hace": hay causa, y es que `0 < IP_VERSION(9,0,0)` es cierto
por construccion, porque `IP_VERSION(mj,mn,rv)` es `(mj<<24)|..` y para ningun
ASIC real vale 0. Y los cuatro codificadores de PTE/PDE caen al lado legacy, asi
que mi driver **no** debe usar el bit 56 para PRT ni el bit 63 para PDE-como-PTE:
son campos de gfx12.

**LO QUE SE ESTRECHA, SIN CONTRADECIR A OTRA SESION.** La granularidad de 8 PTE
del TLB de GFX8 la otra sesion la presenta como propiedad del hardware. He
seguido el rastro: es el **unico** sitio del driver que lo dice, los 188 registros
de TLB de los headers GMC son **todos del L1 del shader**, y no hay codigo que
dependa de la alineacion a 8 como contraprueba. La clasificacion correcta es
**una sola fuente**: el comentario de upstream. La consecuencia queda `PROVEN`, la
causa no. Para un driver propio la diferencia es entre *"se por que"* y *"copie
por que"*.

**Y LO NUEVO, QUE ES DE MI DOMINIO.** **MES es inalcanzable en Polaris12**, y por
un motivo que no es "este ASIC no esta en la lista":
`amdgpu_discovery_set_mes_ip_blocks()` selecciona el bloque **leyendo
`GC_HWIP`**, con 13 casos todos `11.x`/`12.x` y `default: break;`. Con el valor 0
no casa ninguno. Y `mes_v9_*.c` / `mes_v10_*.c` no existen: hay tres ficheros
MES y son los tres de `11.x`/`12.x`. Eso corrobora **EV-38bis desde una direccion
que no habia usado**: ahi segui el codificador vivo por `sdma_v3_0_ip_funcs`; aqui
pregunte si existe hardware de VM-ops en MES. No existe.

**Un `default: break;` en un `switch` de inicializacion es perdida silenciosa**, y
no avisa. Anotado, porque un driver propio que numerase ASICs por version de IP
tendria el mismo fallo.

**UN EJE QUE LE FALTA AL CENSO.** De las 46 comparaciones que reporta
`ipver_zero.py`, **5 estan en `amdgpu_mes.c` sin llamador alcanzable**: quedan
**41** que gobiernan la placa. La herramienta clasifica la *expresion*, no el
*alcance*, y no lo declara. Una columna de alcanzabilidad es lo que le falta, y es
el mismo eje que me hizo fallar a mi.

**QUINTA VEZ QUE MEZCLAR GENERACIONES DA UN NUMERO FALSO.** Mi grep dio 260 sitios
de `GC_HWIP`; el bueno es 50 en 18 ficheros que si se ejecutan. Countaba
`gfx_v9_0.c`, `gfx_v10_*.c`, `nv_*`. El patron no cambia: `sid.h` en EV-35,
`gmc_v6_0.c` en el control de mascara, `pm4census` con 7.2.8, el bloque SDMA, y
esto. **Contar apariciones en un arbol no es contar cosas que se ejecutan.**

**DOS DEFECTOS MIOS, MEDIDOS EN ESTA MISMA RONDA.** El script de escritura metio
cuatro caracteres CJK sin querer y **el guardián los cazo antes de escribir
nada**: es la primera vez que veo funcionar ese control en mi propio flujo, y
funciona porque lo escribi sin probarlo antes. Y la correccion de los residuos
llevo tres intentos, porque cada vez que lo hacia a mano metia un error distinto
(una cadena que no existia, un salto de linea que no habia visto). A la tercera
imprime el contexto exacto y lo arreglo. **Menos es mejor que a mano, incluso
en un script de una sola vez.**

**LO QUE NO HE HECHO Y POR QUE.** `EVIDENCE-MATRIX.md` lleva EV-39 escrito, con
+18 fences y la paridad conservada (225 -> 243, ambos impares, la deuda heredada no
crece), pero **no se stagea**: otra sesion tiene modificada esa coma de ancho
completo y `pub.sh` stagea ficheros enteros, asi que stagearlo se llevaria su
linea. El contenido va en los seis documentos limpios. La linea ajena es exactamente
una: una coma de ancho completo en "La", cambiada a coma normal. No la
cito para no meter el caracter que el guardiano prohibe; que la resuelva quien
escribio.

`GPU INTACTA. WRITE_EXECUTION NONE. NIVEL 0/1.

---

## 2026-10-02 · opencode · EV-40: los 10 bloques IP de esta placa, y 4 de 50 comparaciones descartables con hecho

```
OBJECT   revkit/gfx8blocks.py, revkit/gchwip_alcance.py, revkit/check.sh,
         docs/CURRENT-STATE.md, docs/NEGATIVE-RESULTS.md, docs/TOOLS-STATUS.md
ACTION   EVIDENCE (superficie de inicializacion) + TOOL NEW (2) + CORRECTION
TRACK    STATIC · WRITE_EXECUTION=NONE · RUNTIME=NOT_RUN · GPU INTACTA
```

**EL ITEM 1 DEL UNIVERSO, QUE NO TENIA NADA.** El driver elige bloque de hardware
por **dos** caminos y en `amdgpu_device.c:1978-1999` son **mutuamente
exclusivos**: `vi_set_ip_blocks` reparte por `asic_type`, `amdgpu_discovery_set_ip_blocks`
reparte por `GC_HWIP`. Polaris12 entra en el `case` y no llega al `default`. De
ahi salen dos hechos: **ninguna funcion de discovery se ejecuta aqui**, y **no se
instancia ningun bloque de 9.x/10.x/11.x/12.x**.

**LOS DIEZ.** De los 84 que el driver sabe anadir, Polaris12 instancia **10**, ocho
incondicionales (`vi_common`, `gmc_v8_1`, `tonga_ih`, `gfx_v8_0`, `sdma_v3_1`,
`pp_smu`, `uvd_v6_3`, `vce_v3_4`) y dos condicionados (`amdgpu_vkms`,
`dm`). Las condiciones no se evaluan: es runtime.

**CORROBORACION INDEPENDIENTE.** EV-38bis habia llegado a `gmc_v8_1_ip_block` y
`sdma_v3_1_ip_block` por la cadena de funciones. Aqui los he encontrado
preguntando que bloques existen, sin mirar una sola funcion. Mismos dos nombres,
dos caminos. Y casan con lo que la otra sesion registro en `190`: los tres
bloques que decia no haber mirado (`dm`, `uvd_v6_3`, `vce_v3_4`) estan aqui.

**Y UNA CORRECCION A MI MISMO.** EV-39 §6 decia 5 comparaciones de `GC_HWIP` en
`amdgpu_mes.c` inalcanzables, y clasifique cinco a mano. La herramienta da
**4**: `682`, `683` de `amdgpu_mes_init_microcode`, mas
`amdgpu_gfx_mqd_symmetrically_map_cu_mask` y `amdgpu_gmc_get_vram_info`. Los tres
que faltan (`755/756/758`) **si** son inalcanzables, pero la regla sound es de un
solo salto y no llega: el intermediario vive en `amdgpu_mes.c`, que no es fichero
de bloque. **Pierde positivos a proposito.** El estado dice 4 con hecho y 7 con
lectura manual.

**LO QUE MAS ME HA COSTADO: LA HERRAMIENTA, NO EL HALLAZGO.** Catorce defectos,
todos medidos. Tres que no se me hubieran ocurrido:

- **Trocear por etiqueta de `case`.** En C, `case` no delimita codigo: las
  etiquetas consecutivas comparten un cuerpo y `case CHIP_POLARIS12:` cae en
  `case CHIP_VEGAM:`. Mi troceado devolvia 0 bloques para POLARIS12 y **decía
  exito**. Una lista vacia sin decirlo es peor que no tener herramienta.
- **Ocho `case CHIP_POLARIS12:` en `vi.c`**, uno por switch. Buscaba la etiqueta
  en el fichero entero y cogia el de la linea 274, en otra funcion. **Acotar,
  luego emparejar.** Y el mismo error se me repitio al escribir **la prueba** de
  la herramienta: el test mutaba el brazo equivocado y fallaba por su cuenta.
- **"Sin ningun llamador" esta exactamente al reves.** No es "no esta vivo", es
  "no lo llama el texto del driver". `amdgpu_dma_buf_attach` es un `.attach =` de
  `dma_buf_ops`: lo alcanza un ioctl, desde fuera. Yo mismo escribi la regla al
  reves y luego la defendi.

**Y LA RETIRADA DE PRETENSION.** Primero cerre el grafo de alcance para saber que
ficheros eran vivos. Con un **recall del 96,2%** medido, eso descartaba de mas:
entre otros a `amdgpu_device_init`, que es LA funcion de inicializacion. Un
filtro que descarta no puede apoyarse en una aproximacion; necesita un **hecho**.
Lo sustituyo por "este fichero solo implementa un bloque que no existe en esta
placa". **Llegue al problema correcto por el lado equivocado.**

**Y UN TEST EN LA CAPA EQUIVOCADA.** El defecto del `% -32s` estaba en la salida:
imprimia 39 caracteres como 32, inventando otro identificador, y un lector
concluiria que esa funcion no existe. Mi comprobacion miraba el diccionario
interno, que ya traia el nombre entero: **verde con el bug presente**. Un test de
salida tiene que mirar la salida.

`check.sh` 39 (con las dos herramientas dentro) | `cn7` 97 | `cn8` 33 |
`selfcheck` 30/30 | `gfx8blocks --self-test` 17/17 | `gchwip_alcance --self-test`
21/21. `GPU INTACTA. WRITE_EXECUTION NONE. NIVEL 0/1.

---

## 2026-10-02 · opencode · los 145 puntos de entrada por puntero a funcion, y un punto fijo que no funciona

```
OBJECT   revkit/gfx8blocks.py (modo --funcs), docs/CURRENT-STATE.md,
         docs/NEGATIVE-RESULTS.md, docs/TOOLS-STATUS.md
ACTION   EVIDENCE (superficie de entrada) + NEGATIVE_RESULT (punto fijo) + TOOL
TRACK    STATIC · WRITE_EXECUTION=NONE · RUNTIME=NOT_RUN · GPU INTACTA
```

**LOS 145.** Los diez bloques de la placa registran **145 funciones** en sus diez
tablas `.funcs`. Para un driver propio esa es la primera lista que hay que
tener: por ahi entra el driver al hardware, y por ahi no entra ni un solo
`grep` de llamadas por nombre.

**TRES IDENTIDADES QUE SE ROMPEN EN ESTA PLACA, LAS MEDIDAS:**

- el bloque **no es** la tabla: `gfx_v8_0_ip_block` y `gfx_v8_1_ip_block`
  comparten `gfx_v8_0_ip_funcs`; `gmc_v8_1_ip_block` usa `gmc_v8_0_ip_funcs`;
  `dm_ip_block` usa `amdgpu_dm_funcs`; `pp_smu_ip_block` usa `pp_ip_funcs`.
- el bloque **no es** el fichero: cuatro de diez estan definidos en un fichero con
  otro nombre (`gmc_v8_1` en `gmc_v8_0.c`, `sdma_v3_1` en `sdma_v3_0.c`,
  `uvd_v6_3` en `uvd_v6_0.c`, `vce_v3_4` en `vce_v3_0.c`).
- el bloque **no esta en `amdgpu/`**: `pp_smu_ip_block` esta en `amd/pm/powerplay/`
  y `dm_ip_block` en `amd/display/amdgpu_dm/`. Buscando solo en `amdgpu/` la
  herramienta decia "SIN TABLA" de dos bloques que **si existen**. No era una
  ausencia: era un alcance. Y la superficie de init son **cuatro subsistemas**.

**Y UN RESULTADO NEGATIVO QUE ME HA COSTADO MAS QUE EL POSITIVO.** Para recuperar
los 3 descartables que la regla de un salto pierde, implemente la propagacion de
muerte por el grafo de llamadores. **No funciona, por dos motivos distintos:**

- Con la frontera estrecha cascada y declaro muertos `amdgpu_vmid_mgr_init`
  (llamado desde `amdgpu_vm.c:2876`, dentro de `amdgpu_vm_init`, que corre en toda
  GPU), `amdgpu_sdma_is_shared_inv_eng` y `amdgpu_gfx_is_compute_multipipe_capable`.
  **Un punto fijo sobre una frontera incompleta no es conservador: envenena todo
  lo que cuelgue de una semilla mala.**
- Con la frontera ancha da **0**, porque no puede atravesar
  `mes_v11_0_init_microcode`, que solo se invoca desde una tabla y por eso nunca
  aparece como llamada: una entrada `.init_microcode = fn,` no lleva parentesis.

**Retiro el modo y lo dejo desconectado, con el motivo escrito en el sitio.**
Publicar un modo que devuelve 0 por el motivo equivocado es peor que no
publicarlo: un 0 aqui no es un resultado, es un fallo con apariencia de resultado.
La herramienta vuelve a la regla de un salto, con sus 4 descartables verificados a
mano. **Cuatro por hecho valen mas que siete por propagacion elegante sobre datos
que ya he medido que no son fiables.**

**LO QUE FALTA, escrito para no repetirlo:** la frontera tiene que incluir las
entradas de las tablas de bloques MUERTOS como raices muertas. El intento dio 1003
raices y no capturo `mes_v11_0_init_microcode`. Es trabajo pequeno y localizable,
no un problema de fondo.

**DOS MUTACIONES QUE NO CAZAN Y POR QUE NO ES UN HUECO DEL TEST.** Una solo
anadia un comentario `MUTADO` sin cambiar nada: una mutacion inerte no puede
fallar. La otra volvia vacio un control con `or True`: un control vacio no puede
fallar por definicion. **Instrumentar un control para que no pueda fallar es
retirarlo dejandolo puesto.** Enseñar las dos es parte del resultado.

**Y UN ERROR DE HERRAMIENTA QUE CASO CON LOS DATOS.** Al anadir las raices, mi
parche sustituyo el `muertos = set()` de `main()` por el de
`puntos_fijos_muerte()`, y dejo `_con_frontera` sin definir dentro de la funcion:
`NameError` al ejecutar. Lo **reverti entero** desde `454df1f` en vez de seguir
parcheando un fichero que ya habia roto tres veces. La version commiteada estaba
validada con 21 vectores y 4 mutaciones, y el trabajo util de esta ronda estaba
en `gfx8blocks.py`, que es otro fichero. **Volver atras no es rendirse: es dejar de
añadir riesgo a un fichero que ya funcionaba.**

`check.sh` 39 | `cn7` 97 | `cn8` 33 | `gfx8blocks --self-test` 24/24 |
`gfx8blocks --funcs` 10 bloques, 145 funciones | `gchwip_alcance --self-test`
21/21. `GPU INTACTA. WRITE_EXECUTION NONE. NIVEL 0/1.

---

## 2026-10-02 · opencode · EV-41: el envio desde userspace es asincrono, y se sale del corpus a mitad

```
OBJECT   docs/CURRENT-STATE.md, docs/NEGATIVE-RESULTS.md, docs/KNOWLEDGE-GRAPH.md
ACTION   EVIDENCE (cadena de envio) + NEGATIVE_RESULT (dos busquedas fallidas)
TRACK    STATIC · WRITE_EXECUTION NONE · RUNTIME=NOT_RUN · GPU INTACTA
```

**LA SUPERFICIE DE IOCTLS.** `amdgpu_ioctls_kms[]` declara **20**:
GEM_CREATE, CTX, VM, SCHED, BO_LIST, FENCE_TO_HANDLE, GEM_MMAP, GEM_WAIT_IDLE,
CS, INFO, WAIT_CS, WAIT_FENCES, GEM_METADATA, GEM_VA, GEM_OP, GEM_USERPTR, USERQ,
USERQ_SIGNAL, USERQ_WAIT, GEM_LIST_HANDLES. Y el core de DRM anade **78** mas, asi
que 20 es NOT_COMPLETE y no "los ioctls del driver".

**EL ORDEN, LEIDO Y NO INFERIDO.** `amdgpu_cs_ioctl` (`amdgpu_cs.c:1411-1473`) son
ocho etapas con dos caminos de error: dos puertas arriba (`amdgpu_ras_intr_triggered`
-> -EHWPOISON, `accel_working` -> -EBUSY) y luego parser_init, pass1, pass2,
parser_bos, patch_jobs, vm_handling, sync_rings, submit, parser_fini.

**Y EL ORDEN NO ES EL DEL FICHERO, por octava vez.** `amdgpu_cs_parser_bos` esta
definido en la 845 y se ejecuta DESPUES de `pass2` (600); `amdgpu_cs_patch_jobs`
(1072) se ejecuta ANTES de `amdgpu_cs_vm_handling` (1085). Si hubiera deducido la
secuencia del orden de definicion, la habria dado mal. Ademas `error_backoff`
desbloquea `bo_list_mutex` y `error_fini` no, lo que hace consistente que solo se
suelte en el camino posterior a tomarlo.

**EL HALLAZGO: EL ENVIO ES ASINCRONO, Y SE SALE DEL CORPUS.** `amdgpu_cs_submit`
NO llama a `amdgpu_ring_commit`. Crea los fences y empuja con
`drm_sched_entity_push_job()`, que esta en el CORE de DRM, en
`drivers/gpu/drm/scheduler/sched_entity.c`. Y ese directorio **no esta en
`baseline` ni en `working`**: solo tienen `drm/amd/`. Dos consecuencias: (a) que
`AMDGPU_CS` devuelva 0 NO significa que se haya escrito en el anillo, y eso es
asincronia de SOFTWARE, deducible del corpus y distinta de mi
`hardware execution ordering NOT_PROVEN`; (b) la mitad de ejecucion del camino de
envio es `NOT_IN_CORPUS`, no `PROVEN_ABSENT`. Reaparece la limitacion de EV-39.

El reingreso al driver es por PUNTERO A FUNCION: `amdgpu_job.c:515` registra
`.run_job = amdgpu_job_run`. Es el mismo patron que las 145 entradas de EV-40, en
la direccion contraria: las dos caras son punteros a funcion, y las dos son
invisibles a grep.

**DOS BUSQUEDAS QUE CASI SON UN PROVEN_ABSENT FALSO, y las dos las evite con una
busqueda mas.**
- Fui a buscar `amdgpu_ring_pad_advance` y `amdgpu_cs_write`. No existen. La
  conclusion correcta no es "el driver no los tiene": es que en 7.1.3 se llaman
  distinto. El equivalente SI existe: `amdgpu_cs_ioctl`, `amdgpu_ring_commit`.
- Busque `drivers/gpu/drm/drm_sched.c`. No existe. Antes de decir que no, mire el
  directorio: existe `drivers/gpu/drm/scheduler/` con `sched_main.c`,
  `sched_entity.c`, `sched_fence.c`. Y `drm_sched_entity_push_job` solo aparecia en
  COMENTARIOS de `sched_main.c`; la definicion esta en `sched_entity.c:631`.
Las dos son el mismo error con distinto disfraz: confundir "no lo he encontrado"
con "no existe". Por nombre de simbolo equivocado, y por nombre de fichero
equivocado.

**Y UN PROVEN_ABSENT GENUINO, EL UNICO DE ESTA RONDA.**
`amdgpu_ring_generic_pad_ib` (`amdgpu_ring.c:146`) esta definida y NO la llama nadie
en el driver, comprobado sobre todo el arbol. No es que no la mirara: es que el
nucleo no la invoca. Para mi driver propio no es una obligacion, aunque el nombre
sugiera lo contrario.

`check.sh` 39 | `cn7` 97 | `cn8` 33 | `gfx8blocks` 24/24 | `gchwip_alcance` 21/21.
GPU INTACTA. WRITE_EXECUTION NONE. NIVEL 0/1.

---

## 2026-10-02 · opencode · EV-42: EV-40 corroborado en runtime, y la placa tiene Display Core

```
OBJECT   docs/CURRENT-STATE.md, docs/CONTRADICTIONS.md
ACTION   EVIDENCE (OBSERVED de 9 bloques) + CONTRADICTION (resuelta)
TRACK    RUNTIME, SOLO LECTURA (journalctl -k -b, modinfo, /boot/config)
WRITE_EXECUTION=NONE · MODIFICATIONS=0 · GPU INTACTA
```

**EL PRIMER RUNTIME DE ESTA RONDA, Y CORROBORA LO QUE HABIA DERIVADO ESTATICAMENTE.**
Nueve lineas reales del kernel: los OCHO incondicionales de EV-40 estan los ocho, con
los mismos nombres de tabla que midio gfx8blocks --funcs, incluido gmc_v8_0 para un
bloque gmc_v8_1 y uvd_v6_0 para un bloque uvd_v6_3. EV-40 pasa de PROVEN por lectura a
OBSERVED. La numeracion empieza en 0: num_ip_blocks no reserva el indice 0.

**Y UN HECHO QUE NO TENIA: LA PLACA TIENE DISPLAY CORE.** dce_v1_0_0 esta
instanciado, o sea que dm_ip_block se activo. Con eso quedan medidas las cuatro
condiciones de amdgpu_device_has_dc_support: CONFIG_DRM_AMD_DC=y, enable_virtual_
display falso, sin harvest DMU, y asic_has_dc_support(Polaris12) cierto.

**LA COMPROBACION CRUZADA QUE NO HABIA PEDIDO.** vi.c:2115-2120 es un `if` seguido de
un `else if`, luego amdgpu_vkms y dm son MUTUAMENTE EXCLUYENTES por construccion. El
runtime muestra dm presente y vkms ausente, que es lo que el codigo exige. **Dos
predicciones independientes de una sola lectura estatica, las dos cumplidas.** Eso
valida la lectura hasta en su estructura de control, no solo en sus nombres.

**9 = 8 incondicionales + 1 condicionado. Ni mas ni menos.** Y amdgpu_vkms ausente
significa que no hay virtual display en esta placa.

**LA CONTRADICCION, Y COMO SE RESOLVIO, que es la parte que importa.** Al contrastar
mi lista estatica con las lineas citadas DENTRO del proyecto, parecian faltar uvd_v6_3,
vce_v3_4 y amdgpu_vkms. Antes de elegir explicacion, escribi cuatro hipotesis y las
descarte una a una. H2 (harvest) se descarta ESTATICAMENTE sin mirar nada:
amdgpu_ip.c:228-239 solo suprime por harvest los tipos VCN y JPEG, y UVD/VCE no son
esos. La resolucion: capturar de verdad.

Y el resultado es que **H3 y H4 explicaban la falsa contradiccion, y las dos a la vez.**
Los recortes del proyecto estaban filtrados, y mi propia regex exigia UN espacio entre
">" y "(" mientras dos lineas tienen DOS espacios, de modo que las perdi yo.
**Dos errores de observacion apilados.** Ninguno estaba en la derivacion, y sin la
captura real habria publicado que mi EV-40 sobraba en tres bloques.

**NOVENA VEZ, Y LA REGLA QUE SALE:** un recorte no es una captura. Siete lineas
citadas en el proyecto frente a nueve reales no es una discrepancia de datos, es una
discrepancia de RECOGIDA, y se distingue contando, no interpretando. Y en esta
maquina **dmesg devuelve 0 lineas** sin permiso mientras que **journalctl -k -b si
lee**: la VIA de lectura importa tanto como la lectura. Eso confirma de paso la
limitacion que arrastraba F12, donde habia que leer el kernel.

TAMBIEN: el fingerprint (HARDWARE-FINGERPRINT.md, de hoy) ya declara TARGET_MATCH=si
con los nueve campos del contrato verificados. **No lo he vuelto a hacer ni duplicado**:
el prompt maestro lo pide como primera operacion, el artefacto ya existe con veredicto,
y rehacerlo no seria progreso sino coste. Lo que si he hecho es cruzarlo con mis
resultados nuevos, y no aparece contradiccion: 0x699F mapea a CHIP_POLARIS12 por
driver_data en amdgpu_drv.c:2041 (los "0, 0" de esa linea son class y class_mask, NO
un rango de revision), asi que el rev 0xc7 de la placa es irrelevante para la
identificacion del ASIC. Casi lo doy por raro al verlos.

GPU INTACTA. WRITE_EXECUTION NONE. NIVEL 2 (solo lectura). MODIFICATIONS 0.

---

## 2026-10-02 · opencode · EV-43: el orden de arranque, y por que dos bloques se adelantan

```
OBJECT   docs/CURRENT-STATE.md, docs/KNOWLEDGE-GRAPH.md
ACTION   EVIDENCE (cadena de arranque, leida) + LIMIT (exito individual no medido)
TRACK    STATIC · WRITE_EXECUTION=NONE · MODIFICATIONS_CORPUS=0 · GPU INTACTA
```

**LA SECUENCIA, Y NO ES PLANA.** early_init x9, luego sw_init x9, y **DENTRO** del
bucle de sw_init se hardware-inicializan COMMON y GMC. Despues phase1, luego
`amdgpu_device_fw_loading`, luego phase2, luego late_init x9.

**LA RAZON ESTA ESCRITA EN EL CODIGO, Y ES LA QUE FALTABA.** "need to do common hw
init early so everything is set up for gmc" y "need to do gmc hw init early so we can
allocate gpu mem". O sea: **COMMON antes que GMC para que todo este listo, y GMC antes
que el resto porque hasta que GMC no esta arriba no se puede reservar memoria de
GPU.** Para un driver propio esa es la cadena item 1 -> item 4 del universo, y es la
primera vez que esta escrita con su causa. Si se reordena, no hay memoria.

**DOS COSAS QUE NO SON LO QUE APARENTAN.**

- **`hw_init_phase1` no es un barrido general**: tiene un filtro por tipo. Solo
  llama hw_init a COMMON, a PSP **pero solo si es SR-IOV VF**, y a IH. Y salta lo
  que ya tenga `status.hw`. Como COMMON y GMC ya lo tienen desde el bucle de sw_init,
  **en esta placa phase1 solo alcanza a tonga_ih**. Leyendo "phase1 luego phase2"
  como dos barridos genericos habria asignado mal el orden de tres bloques.
- **`hw_init_phase2` si es el general**: mismos guards, sin filtro de tipo.

**EL ORDEN DE hw_init AQUI:** vi_common, gmc_v8_1 (ambos dentro del bucle de sw_init),
tonga_ih (phase1), y gfx_v8_0, sdma_v3_1, pp_smu, dm, uvd_v6_3, vce_v3_4 en phase2.
De ahi sale algo que no habia visto: **GFX y SDMA se inicializan por hardware
DESPUES de cargar el firmware**, porque fw_loading esta entre phase1 y phase2 (2403).
Para mi driver el firmware es precondicion del hardware de graficos, no un detalle de
orden.

**Y LA PARTICIPACION ES UNA TABLA, NO CODIGO.** `amdgpu_ip_member_of_hwini` lee
`adev->init_lvl->hwini_ip_block_mask`, una mascara con un bit por tipo. Los tres
niveles estan en amdgpu_device.c:161-182; en DEFAULT es AMDGPU_IP_BLK_MASK_ALL, asi
que en esta placa participan los nueve. El nivel restringido (GMC|SMC|COMMON|IH|PSP)
es solo para reset de hive XGMI antes del primer uso, y Polaris12 no tiene XGMI.
**Para un driver propio, "que bloques existen" esta en `vi.c` y "en que orden se
inicializan" esta en `init_lvl`: son dos tablas distintas y hay que fijarlas las
dos.**

**EL LIMITE, DICHO.** El orden es PROVEN por lectura. Que las nueve llamadas
devolvieran exito en este arranque es NOT_DETERMINED, porque `status.hw` por bloque
no lo he leido. Que los nueve bloques se instanciaron si es OBSERVED (EV-42). No
confunde una cosa con otra.

**Y UN ARREGLO DE HERRAMIENTA MIA.** Esta vez escribi los bloques de codigo con un
marcador ````` en vez de ````` en linea. Es la **segunda vez** que
ese cierre de cadena mal puesto me costo un ciclo entero, y la razon es que el error
vive dentro de la propia sintaxis del script: un `ast.parse` previo lo detecta, pero
yo no lo estaba haciendo siempre. Con el marcador desaparece la clase de error, no
solo elINSTANCE.

check.sh 39 | cn7 97 | cn8 33 | gfx8blocks 24/24 | gchwip_alcance 21/21.
GPU INTACTA. WRITE_EXECUTION NONE. NIVEL 0/1.

---

## 2026-10-02 · opencode · EV-43 cerrado, y dos errores mios que casi contaminan el
resultado

```
OBJECT   docs/CURRENT-STATE.md, docs/NEGATIVE-RESULTS.md
ACTION   VALIDATION (cierre del NOT_DETERMINED de EV-43) + 2 x ERROR propio
TRACK    RUNTIME, SOLO LECTURA (journalctl -k -b) · WRITE_EXECUTION=NONE
MODIFICATIONS=0 · GPU INTACTA
```

**EV-43 CERRADO.** El driver imprime un dev_err por cada fase de init que falle, con
el nombre del bloque, y son las unicas vias de fallo de esas fases. En el arranque
real hay **0**. Asi que los nueve bloques inicializaron sin un solo fallo:
`OBSERVED`.

**Y EL CONTROL POSITIVO, QUE ES LO QUE LO HACE CREIBLE.** La MISMA invocacion con la
MISMA tuberia devuelve: 1204 lineas totales, 62 de amdgpu, **9** bloques, **1** linea
de TMZ. El canal lee. Dos pipelines identicos dan 9 y 1 sobre lo que existe, y 0
sobre lo que busco. **El 0 es una ausencia real: no es permiso, ni SIGPIPE, ni
productor vacio.**

**Y UN HECHO DEDUCIDO DE NO HABERSE CAIDO.** hw_init_phase2 llama funcs->hw_init SIN
comprobar NULL, a diferencia de los tres guards que si pone. Con la particion
AMDGPU_IP_BLK_MASK_ALL los nueve llegan ahi, luego los nueve tienen esa ranura no
nula. PROVEN_DERIVED por ausencia de fallo.

**PRIMER ERROR MIO: LEI UN TITULO EN VEZ DE LEER EL HALLAZGO.** El arranque dice
"TMZ feature not supported" y el hallazgo 190 se titula "TMZ confirmado en runtime".
iba a registrar una CONTRADICCION. El hallazgo dice lo contrario de lo que sugiere el
titulo: confirma que TMZ esta DESACTIVADO, y cita la misma linea. **Sin
contradiccion: convergencia.** Undécima vez que un titulo es un indice y no un
dato.

**PERO SI HAY APORTACION MIA EN ESO: es la TERCERA consecuencia independiente del
mismo GC_HWIP == 0.** Con el valor a 0 cae (1) en la rama legacy de los codificadores
de PTE/PDE, (2) hace el flush de TLB incondicional, y (3) desactiva TMZ. TRES
consumidores distintos, un solo valor. Para un driver propio que hardcodee nada de
esto, las tres se resuelven con la misma decision.

**SEGUNDO ERROR MIO, Y MAS GRAVE PORQUE AFECTABA AL RESULTADO.** Para medir los
fallos de init meti journalctl con su redireccion DENTRO de una variable de shell.
Los dos ceros que salian eran falsos, e indistinguibles de ceros reales: el pipeline
no leia nada y el consumidor terminaba con exito. "Failed to add match
'2>/dev/null'". **Sin el control positivo no lo habria visto**: en cuanto compare el
0 con las 9 lineas que el mismo canal deberia dar, se rompio la illusion, porque
nadie tiene 9 bloques y 0 bloques a la vez.

**TRES REGLAS QUE SALEN DE AHI, y que son mas generales que este hallazgo.**
1. Una variable de comandos NO debe contener una tuberia ni una redireccion. Es la
   forma mas facil de tener un pipeline que "funciona" y no lee nada.
2. Todo cero necesita un control positivo EN EL MISMO PIPELINE. Un control en otro
   comando prueba otra cosa.
3. grep -c que da 0 y grep -c que da 0 son indistinguibles mientras no sepas que el
   canal lee. Por eso el control va en la MISMA linea de comando que el resultado.

**Y UNA COMPROBACION QUE AHORRO TRABAJO:** iba a presentar como nuevo el "vm size is
64 GB, 2 levels, block size is 10-bit, fragment size is 9-bit", y antes de escribirlo
busque si ya estaba. **Ya estaba**: docs/AGENTS-ADDENDA.md tiene block_size = 10, NO
9 con su derivacion completa, y CONTRADICTIONS.md cita la linea exacta. **Septima vez
que algo parece nuevo y ya esta registrado**, y el chequeo costo un comando. Lo que
tampoco es nuevo: "5907M of GTT memory ready" es la cifra MemTotal/2 de 243, y NO la
ventana GART reservada de 256 MiB. Dos cosas distintas con numeros parecidos, que es
la confusion mas probable de esa linea; lo dejo escrito para que no la cometa otro.

check.sh 39 | cn7 97 | cn8 33 | gfx8blocks 24/24 | gchwip_alcance 21/21.
GPU INTACTA. WRITE_EXECUTION NONE. NIVEL 2 (solo lectura). MODIFICATIONS 0.

---

## 2026-10-02 · opencode · RK-12 `bootcheck`: el arranque validado, con el control DENTRO de la herramienta

```
OBJECT   revkit/bootcheck.py, revkit/check.sh, docs/TOOLS-STATUS.md
ACTION   TOOL NEW + VALIDATED · READONLY · WRITE_EXECUTION=NONE · GPU INTACTA
```

**LOS CUATRO `dev_err` DE FASE SON UN OBSERVABLE GENERICO.** Dicen "esta placa no
arranco bien". Un driver propio necesita exactamente eso para validar su propio
arranque, y no habia ninguna herramienta que lo hiciera.

**EL DISENO, Y SALE DE DOS ERRORES MIOS DE ESTA MISMA RONDA.**

La entrada es un FICHERO, no una tuberia. Si la herramienta ejecutara journalctl ella
misma, un fallo de su propio pipeline seria indistinguible de un arranque limpio, que
es exactamente el error de NR-2026-10-02-d2. Con fichero se puede probar contra logs
SINTETICOS, y ahi si se ve si el control funciona.

Y **C0 va primero y gobierna el resultado**: si el log no contiene nada reconocible,
la herramienta NO dice "cero fallos", dice INVALID_RESULT y sale con rc=4. **UN CERO
SIN PRUEBA NO SE REPORTA**, y el 0 de C2 aparece siempre al lado de C0, que es su
control.

**VALIDADO.** 10 vectores, cinco mutaciones cazadas sobre copias: sin C0 (4 en rojo),
C2 invertido (5), un bloque menos en la lista (rc=1), la regex tolerando doble espacio
(1, y es justo el test que fija el bug), ASIC equivocado (3, y la ejecucion real da
rc=3). Original 10 OK.

**Y UN TEST QUE ES UN BUG FIJADO.** El ultimo vector comprueba que un doble espacio
entre ">" y "(" hace que la linea NO cuente como bloque: es el bug que me produjo la
falsa contradiccion de EV-42, aqui declarado como comportamiento esperado.
Convertir una trampa silenciosa en un test es la diferencia entre un artefacto y una
costumbre.

**CONTRA EL LOG REAL:** 1211 lineas, 68 de amdgpu, 9 bloques, 0 fallos de fase, ASIC
POLARIS12. Los cuatro controles en verde, rc=0.

**EL LIMITE, DICHO EN LA PROPIA SALIDA.** Esto dice lo que el driver IMPRIMIO, no lo
que el hardware HIZO. Que ninguna fase fallo NO es que el hardware quedara bien: eso
sigue NOT_DETERMINED sin lectura de registros. Y es la muestra de UN arranque, que es
justo lo que 243 y 258 ya sufreron con MemTotal.

**TRES DEFECTOS MIOS EN LA HERRAMIENTA, y el tercero solo se ve si te relees.**
Escribi cirilico en un comentario, la misma clase de contaminacion que acababa de
ampliar el guardIAN. Inmediatamente despues de ampliarlo: el defecto estaba en el
production, no en el control. Escribi un control como "(not C0) and C0", que es
SIEMPRE falso: un control que no puede pasar. Y un len() sobre un bool.

**EL PRIMERO ES EL QUE MAS DICE: ampliar un guardIAN no sirve si la fuente que lo salta
es el mismo sitio donde se acaba de escribir.** El control y el error estan en la
misma accion, y por eso el control no llego a tiempo. Hay que releer lo que uno acaba
de escribir, y releer no es lo mismo que pasar el control.

**Y LO QUE ESTA HECHO PARA QUE NO SE DESINCRONICE:** la lista de bloques esperados no
esta inventada aqui, viene de gfx8blocks.py mas lo OBSERVED de EV-42. Si el kernel
cambiara la lista, esta herramienta falla, y eso es lo correcto: una lista de bloques
copiada a mano en dos sitios es dos sitios que se desincronizan, que es la clase de
error que vengo pagando desde EV-35.

check.sh 40 (con bootcheck dentro) | cn7 97 | cn8 33 | gfx8blocks 24/24 |
gchwip_alcance 21/21 | bootcheck 10/10 y rc=0 contra el log real.
GPU INTACTA. WRITE_EXECUTION NONE. NIVEL 0/1.

---

## 2026-10-02 · opencode · RK-13 `gputel`: el reposo real de la GPU, y dos trampas de unidad

```
OBJECT   revkit/gputel.py, revkit/check.sh, docs/CURRENT-STATE.md,
         docs/TOOLS-STATUS.md
ACTION   TOOL NEW + VALIDATED + PRIMERA MEDICION DE HARDWARE DEL PROYECTO
TRACK    RUNTIME, SOLO LECTURA (sysfs hwmon, PCI config) · WRITE_EXECUTION=NONE
MODIFICATIONS=0 · GPU INTACTA · NIVEL 2
```

**POR QUE, Y NO ES EXTRAPOLAR.** bootcheck valida la cadena de SOFTWARE: que el
driver imprimiera lo que debia. Eso no dice que el HARDWARE quedara donde debia.
Los registros de GMC siguen en EACCES (F12 sin cambio), pero el arbol hwmon SI es
legible sin root, y es la primera lectura de hardware real disponible aqui.

**TRAMPA DE UNIDAD 1: LA CONVENCION MIENTE.** freq1_input = 1070150000. Si fuera
MHz, que es lo que dice la convencion de hwmon, serian 1070150000 MHz. **Real:
1070.15 MHz.** Este arbol publica frecuencias en Hz. Un numero mil veces mayor es
un resultado falso con toda la apariencia de estar bien.

**TRAMPA DE UNIDAD 2, Y ESTA CASI ME PUBLICA 11 KW.** power1_input = 11133000 y
power1_cap = 35000000. Como mW: consumo 11,13 kW y cap 35 kW, fisicamente
imposible. Como uW: consumo 11,133 W y cap 35 W, coherente con la clase de esta
placa. Lo resuelve la COHERENCIA INTERNA, no la convencion: un cap de 35 W es
justo la clase del RX550, y _min=0 con _max=_default=_cap es el patron de un
unico limite fijo. **PROVEN_DERIVED por coherencia, no PROVEN desde el
productor**: el fichero que registra los canales no esta en este corpus, y lo he
buscado antes de afirmar nada.

**EL REPOSO REAL, MEDIDO.** Ocho muestras a 1 s con gpu_busy_percent=0 y CERO
clientes de render: sclk 996,7 -> 1068,8 MHz (mediana 1039,7; recorrido 6,9 %,
oscilacion real), mclk **300,00 MHz clavado**, vddgfx 812 -> 881 mV (7,9 %),
PPT 6,03 -> 7,04 W (16,4 %), edge 38,0 C estable, pwm 75/255, cap **35 W**.

**EL DATO INTERESANTE ES LA ASIMETRIA: la memoria baja a 300 MHz y el nucleo no.**
Con el GPU al 0 %, la memoria desciende y se queda; sclk **no baja**, oscila
alrededor de 1040 MHz, y vddgfx oscila con el. **El estado DPM de memoria y el de
nucleo no se comportan igual en esta placa**, y mirando solo una de las dos
unidades se conclude mal el ahorro en reposo. Item 38 medido en hardware, que es
la primera vez que se mide en vez de derivarlo del codigo.

**Y UN REFINAMIENTO QUE SALIO DE LA MEDIDA, no de la teoria.** La primera version
marcaba la temperatura como inestable con 2,6 % de recorrido. Era ARTEFACTO DE
GRANULARIDAD: el sensor informa en pasos de 1000 mC, y 37 -> 38 C es un paso, no
una oscilacion. Ahora se informa del recorrido ABSOLUTO y del SALTO DE
CUANTIZACION deducido del menor incremento no nulo, y se distingue "un paso de
cuantizacion" de "oscilacion real". **Un umbral solo porcentual confunde al sensor
por senal, y un umbral por si solo no dice de que magnitud.**

**TRES DEFECTOS DE DISENO Y TRES DE TEST, y el patron se repite.**
1. El lector de ficheros era fijo: tres muestras de un fichero que no cambia dan
   tres valores identicos, el recorrido es 0 siempre, y **la herramienta era
   incriticable sin hardware**. Ahora el lector se INYECTA.
2. LIMITE_PPM se comparaba contra PORCENTAJE: 20000 ppm contra 2,0 % daba > 200,
   un umbral que no podia pasar. **Un umbral con la unidad equivocada es un
   control que no mide nada y encima da sensacion de medir.**
3. Los tests afirmaban sobre los DATOS en vez de sobre el COMPORTAMIENTO: T1
   llevaba la unidad escrita a mano mientras la real vive en la tabla MEDIDAS, y
   T4 miraba el numero de muestras en vez del texto que sale. **Un control tiene
   que leer el valor del sitio donde vive, y ejecutar el camino que dice
   comprobar.**

VALIDADO: 23 vectores, cuatro mutaciones cazadas (T1 3 en rojo, T2 1, T3 1, T4 1).
Con un control de plausibilidad que se prueba con la unidad ERRONEA a proposito,
porque con la correcta no puede fallar.

**LO QUE SIGUE SIN CAMBIAR:** los registros de GMC siguen en EACCES, con lo que la
comparacion "el driver dijo que arranco bien" contra "los registros dicen que el
hardware quedo bien" sigue sin poder hacerse. Y eso lo declara bootcheck en su
propia salida, que es donde un limite debe estar.

check.sh 41 (con bootcheck y gputel dentro) | cn7 97 | cn8 33 | gfx8blocks 24/24 |
gchwip_alcance 21/21 | bootcheck 10/10 | gputel 23/23.
GPU INTACTA. WRITE_EXECUTION NONE. MODIFICATIONS 0.

---

## 2026-10-03 · opencode · un control mio que no podia fallar, y solo lo vi porque cambio la fecha

```
OBJECT   revkit/cn8.py, docs/NEGATIVE-RESULTS.md
ACTION   FIX de un control + LIMITATION declarada
TRACK    TOOLING · WRITE_EXECUTION=NONE · MODIFICATIONS_CORPUS=0 · GPU INTACTA
```

**EL SINTOMA, NO LA TRANQUILIZACION.** Cambio la fecha del sistema a 2026-10-03 y,
antes de nada, mire si la suite seguia en verde, porque varios controles miden
"hoy". Seguia verde. Y eso fue el sintoma: **un control que depende de la fecha del
reloj solo puede fallar una vez al ano, y ese dia es cuando nadie mira.**

**LO QUE DECIA Y LO QUE HACIA.** El control de cn8 se llamaba "el CHANGELOG tiene
entrada de hoy" y por dentro hacia _tiene("2026-10-02", ...). Decia HOY y MIRABA UN
LITERAL. No miraba hoy. Pasaba porque ayer escribi una entrada, y habria seguido
pasando para siempre aunque no escribiera nada hoy, y se habria roto el dia que
alguien borrase aquella entrada, por un motivo que no tiene nada que ver con lo que
el control afirma.

REGLA, Y LA FORMULA EXACTA: **UN CONTROL TIENE QUE COMPROBAR UNA PROPIEDAD, NO UNA
CONSTANTE.** "Hay una entrada hoy" comprobado con un literal no es una
comprobacion, es una decoracion con `if`. Y un control que no puede fallar en lo que
dice comprobar es PEOR QUE NINGUNO, porque ocupa sitio, da sensacion de cubrir, y roba
la confianza que deberia reservarse para los que si fallan.

**LO QUE HAY AHORA.** Se comprueba la propiedad real: que la entrada MAS RECIENTE no
sea mas antigua que una ventana. Lee las cabeceras ## AAAA-MM-DD, se queda con la
maxima, y exige edad <= 3 dias. Con ventana 0 FALLA, lo que demuestra que puede
fallar.

**Y LAS TRES MUTACIONES NO SON IGUALES, y eso hay que decirlo.**
- ventana 0 -> FALLA. Se demuestra que puede fallar. Es el unico caso que importa.
- control puesto a True -> nadie lo detecta. Y no deberia: **un control no puede
  verificar su propia supresion.** No es un hueco, es una propiedad de los controles.
- rama de "no hay ninguna fecha" -> sin probar, porque aqui siempre hay fechas. Es un
  GUARDIA SIN VERIFICAR y queda anotado como tal.

**UN DEFECTO REAL QUE ESA TERCERA MUTACION DESTAPO, Y QUE NO ESTA ARREGLADO.** Si el
CHANGELOG no existe, el `open()` lanza excepcion y cn8 revienta con traceback, en vez
de decir INVALID_RESULT. Una entrada inexistente produce un fallo que el control no
sabe nombrar. Es la misma clase que el rc=3 de gputel sin arbol hwmon, y la solucion ya
existe ahi: convertir la ausencia en un codigo de salida. **Queda pendiente y
anotado, no escondido.**

**Y UN ERROR DE ARNÉS QUE ME DIO CONFIANZA FALSA, por segunda vez.** Monte un arbol
temporal con `docs/` para mutar cn8 y los tres mutantes salieron con rc=1 y CERO
controles en rojo. Uno leyo eso como "el arnes funciona" cuando era lo contrario:
**rc=1 con 0 FALLA significa que algo revienta, no que el control paso.** Para que el
mutante vea lo que ve el original hay que montarle el entorno que el original necesita:
cn8 depende del VBIOS capturado, con lo que la copia tiene que ir EN EL SITIO, con el
sha256 del original comprobado antes y despues. Verificado: identico, copia borrada.

**LECCION GENERAL: `rc` sin el numero de FALLA al lado no es un resultado de una prueba
de mutacion. Es el sintoma de un arnes roto, que es justo lo que la prueba de mutacion
pretendia detectar.**

Suite: check.sh 41 | cn7 97 | cn8 33 | gfx8blocks 24/24 | gchwip_alcance 21/21 |
bootcheck 10/10 | gputel 23/23. GPU INTACTA. WRITE_EXECUTION NONE. NIVEL 0/1.

---

## 2026-10-03 · opencode · `cn8` tiene tres salidas, y `INVALID` no es `FALLA`

```
OBJECT   revkit/cn8.py, docs/TOOLS-STATUS.md
ACTION   FIX (el defecto que ayer deje anotado sin arreglar) + LIMITATION declarada
TRACK    TOOLING · WRITE_EXECUTION NONE · MODIFICATIONS_CORPUS=0 · GPU INTACTA
```

**CIERRO EL DEFECTO QUE DEJE ANOTADO SIN ARREGLAR.** Ayer escribi que si el fichero
del CHANGELOG no existe, el `open()` lanza excepcion y cn8 revienta con traceback.
Lo reproduje primero, porque no quiero arreglar de memoria lo que no he visto
romper: confirmado, `FileNotFoundError`. Y arreglado.

**LO QUE HABIA TRAS EL: TRES COSAS MEZCLADAS EN DOS SALIDAS.**

rc=0 todo pasa
rc=1 ALGO esta mal en el proyecto
rc=1 la HERRAMIENTA no ha podido comprobar nada

Las dos ultimas se leian igual, y quien lo lea concluye que el proyecto esta roto
cuando lo que pasa es que la herramienta no pudo correr. Es el mismo principio que
el C0 de bootcheck y el rc=4 de gputel, aplicado a cn8, que era el que se quedaba
sin el.

**AHORA, Y LAS TRES SALIDAS ESTAN MEDIDAS, NO DECLARADAS:**
  todo bien ................. rc=0   41 controles OK
  propiedad violada ......... rc=1   1 FALLA,   0 INVALID   <- el documento esta mal
  fichero ilegible .......... rc=4   0 FALLA,   1 INVALID   <- la herramienta no pudo leer

**Y UN ENMASCARAMIENTO QUE CASI ME HACE DUDAR DE LA PROPIA PRUEBA.** La primera vez
que intente demostrar el rc=1 mutando la ventana a 0 dias, el control PASO EN VERDE.
La razon: mi commit de ese mismo dia habia anadido una cabecera ## 2026-10-03, luego
_edad = 0 y la ventana 0 se cumplia sola. O sea que la mutacion no era mala: los
DATOS habian cambiado de tal modo que la propiedad era cierta de verdad. E ironicamente
es la mejor prueba de que el control mide algo real y no un literal: **cambia con
los datos, y no con el codigo que lo rodea.** Se rehizo con ventana -1, imposible por
construccion, y ahi si falla.

REGLA, EN FORMULA: UNA HERRAMIENTA QUE NO PUEDE COMPROBAR NADA DEBE DECIRLO CON UNA
CATEGORIA PROPIA, NO CON LA DE "ha fallado". Si comparte categoria, quien lee tiene que
adivinar cual de las dos cosas paso, y **en el caso de los controles esa adivinanza se
paga en confianza**: un control que reporta FALLA cuando en realidad no pudo mirar
ensena a ignorar sus FALLA de verdad.

**LO QUE SEGUIN SIN ARREGLAR.** El guardia de "no hay ninguna cabecera ## AAAA-MM-DD"
sigue SIN PROBAR, porque en este proyecto siempre hay fechas. Guardia escrito y no
ejercitado, anotado como tal en vez de darse por bueno.

**HIGIENE DE LAS PRUEBAS.** Todas las mutaciones se hicieron sobre una copia
`_mut_cn8.py` EN EL SITIO, con el sha256 del original comprobado antes y despues:
identico, y la copia borrada. Y el patron que ya me salio dos veces queda firmado: **rc
sin el numero de FALLA al lado no es un resultado de una prueba de mutacion, es el
sintoma de un arnes roto.**

check.sh 41 | cn7 97 | cn8 33 | gfx8blocks 24/24 | gchwip_alcance 21/21 |
bootcheck 10/10 | gputel 23/23. GPU INTACTA. WRITE_EXECUTION NONE. NIVEL 0/1.
## 2026-10-03 · opencode · el codigo de salida era una suposicion: 30 `return` medidos, y un control que fallaba por ARREGLAR

```
OBJECT   revkit/check.sh, revkit/cn8.py, docs/NEGATIVE-RESULTS.md,
         docs/CONTRADICTIONS.md, docs/TOOLS-STATUS.md
ACTION   FIX del orquestador + FIX de dos controles de cn8 + contrato medido
TRACK    TOOLING · WRITE_EXECUTION=NONE · MODIFICATIONS_CORPUS=0 · GPU INTACTA
```

**DE DONDE SALIA ESTO, Y ERA UNA TAREA MENOR DE LO QUE PARECIA.** El plan era
extender la distincion `INVALID`/`FALLA` a `cn7` y `selfcheck` para que las cinco
herramientas hablaran el mismo idioma. Al mirar si `cn7` tenia ya esa distincion,
resulto que si: devuelve `rc=2` cuando falta el corpus, con un comentario que
explica por que `rc=0` seria mentira. Y al mirar como lo consumia el
orquestador, resulto que `check.sh` tenia **dos mecanismos distintos para la
misma idea**: un `rc=4` generico dentro de `run()`, y un `elif rc==2` escrito a
mano para `cn7` y `cn8`. Dos mecanismos para una idea es donde empiezan las
cosas a desincronizarse, y efectivamente se desincronizaron.

**LO MEDIDO, Y NO LO QUE SUPONIA.** Antes de anadir un codigo nuevo mire las
salidas reales: **17 herramientas, 167 `return <entero>` literales, 5 codigos distintos**
(reparto: 67 con `0`, 41 con `1`, **30 con `2`**, 15 con `4`, 9 con `3`,
5 con `5`). Los 30 eran los que medi al principio; el 167 es el total.
`run()` mapeaba `0` a OK, `4` a INVALID y **todo lo demas a FALLO**. Ese `4`
venia de `cn8`/`bootcheck`/`gputel`/`klog`, que si lo usan. El resto lo
asumia. Y el supuesto era falso:

- **`rc=2` significa "falta el dato"**, no "fallo". Medido con ejecucion real:
  `atomrom.py rom <fichero que no existe>` -> `rc=2`, y `pm4dec.py <fichero que
  no existe>` -> `rc=2`. Los dos imprimen "no existe". Tambien `cn7` (sin
  `sid.h`), `cn8` (sin VBIOS), `captura` (sin `RX550_SUDO_PASS`), `dirs`,
  `sello`, `huerfanos`, `ibpools`.
- **`rc=4` significa "no pude comprobar"** en unos sitios y "fallo" en otros.
  `pm4dec` lo dice literalmente: `"NO CONTRASTADO: falta amdgpu_vram_mm ...
  Saliendo con codigo 4"`.

**EL DEFECTO ESTABA ACTIVO, Y LO REPRODUCE DE PUNTA A PUNTA.** Inyectando en
una **copia** de `check.sh` la invocacion `atomrom.py rom <inexistente>` (sin
tocar ninguna herramienta ni ningun artefacto compartido), la suite entera
terminaba en `rc=1` con

```
PRUEBA: atomrom con fichero ausente            FALLO rc=2
```

Es decir: **"no he podido comprobar" reportado como "el proyecto esta roto"**,
que es exactamente la confusion que el propio `check.sh` dice evitar en su
cabecera. Cometiendola en su propia funcion de ejecucion. Con el protocolo
medido, esa misma invocacion da `INVALID rc=2` y la suite sale `rc=4`, que es lo
que `rc=4` quiere decir.

**Y EL MAPA GLOBAL RESULTABA ESTAR MAL PARA 4 DE LOS 5 CODIGOS.** Publicado el
mapa, me puse a verificarlo entero, porque una generalizacion medida en una
muestra es el fallo de siempre. Intenté clasificar los 167 sitios por palabra
clave y **el escaner resulto ser un instrumento inutil**: etiqutaba `return 0`
como INVALID porque en la ventana de 14 lineas de contexto habia un comentario con
la palabra "falta". No extraje ninguna conclusion de esa tabla. Los 9 sitios con
`rc=3` son pocos, y los leí a mano:

| sitio | lo que dice | clase real |
|---|---|---|
| `bootcheck.py:242` | "%d control(es) en rojo" | FALLO |
| `captura.py:157` | "el plan se contradice a si mismo" | FALLO |
| `dires.py:176` | "un indice que no encuentra lo que se sabe que esta" | FALLO |
| `sello.py:400` | "eso no lo puede hacer un script" | FALLO |
| `btfsnap.py:239` | "NO ESTA pahole" | INVALID |
| `pm4dec.py:958` | "Sin la tabla de opcodes" | INVALID |
| `gfx8blocks.py:537` | "ERROR/INVALID: 0 funciones. No es un resultado." | INVALID |

O sea que **`rc=3` tambien esta sobrecargado**, y yo lo habia dado por bueno. Un
mapa global no puede ser correcto cuando 4 de los 5 codigos no-0/1 lo estan. Lo
que hay ahora es un mapa global como **default** mas una tabla de **excepciones
medidas por herramienta**, que es lo unico que la suite necesita hoy: `pm4dec`
y `gfx8blocks` con `rc=3` es INVALID, `btfsnap` con `rc=3` y `rc=5` es INVALID, y
`bootcheck` y `cn8` con `rc=3` siguen siendo FALLO.

**Y LA EXCEPCION NO FUNCIONABA, Y LA AUTOCOMPRUEBA NO LO CAZO.** Inyectando un
stub `pm4dec.py` que sale con `rc=3` en una copia de `check.sh`, la suite daba
`FALLO` donde debia dar `INVALID`. La causa: `basename "$_t"` devuelve
`pm4dec.py` **con** extension y las etiquetas del `case` son `pm4dec` **sin**
ella, asi que no casaba. Y la autocomprueba no lo vio porque llamaba
`clasifica_de pm4dec 3` a mano, **con una forma de argumento que el llamador real
nunca produce**. Un control probado con una forma de entrada que la vida real no
usa no cubre el camino por el que se ejecuta. Los casos usan ahora `pm4dec.py`, y
la prueba de punta a punta mete stubs de **cinco** herramientas con el mismo
`rc=3`: las tres con excepcion dan INVALID y las otras dos dan FALLO. Con la
tabla vacia, las cinco darian FALLO.

**LO QUE HAY AHORA.** `clasifica()` lleva el mapa medido y se autocomprueba
antes de usarse: `0` OK; `2` y `4` INVALID; `1`, `3`, `5`, `126`, `127` y
cualquier otro FALLO. El mapa que se imprime en la cabecera **se genera desde
la funcion**, no se reescribe a mano: mientras estaba escrito a mano, seguia
diciendo "0=OK, 4=INVALID, resto=FALLO" **despues** de que el protocolo
cambiara, o sea que la linea que informa del clasificador era capaz de mentir
sobre el clasificador. La suite devuelve `rc=4` cuando no hay fallos pero si
validaciones no comprobables, y nombra cuales son.

**UN CONTROL QUE FALLABA POR ARREGLAR (esto va a NEGATIVE-RESULTS).** El control
de paridad de fences de `cn8` exigia que el conjunto de documentos impares
fuese **exactamente** la deuda acreditada. Medicion: entre mi commit `b2407a4` y
`HEAD`, otra sesion pago la deuda de `CONTRADICTIONS.md` (85 fences impares ->
86 pares). `cn8` paso a `rc=1` FALLA. **El trabajo bien hecho se reportaba como
incumplimiento**, y el control no distinguia en que direccion se habia roto. La
igualdad exacta de dos conjuntos confunde "alguien rompio la paridad" con
"alguien la arreglo". Ahora son dos condiciones: `impares` fuera de la deuda
acreditada es FALLA, y la deuda ya pagada se **informa** para poder podarla.

**LO MISMO, OTRA VEZ, EN UN CANAL ENTERO.** `chk()` imprime el `detalle` **solo
cuando falla**, asi que los dos `chk(..., True, "informativo: ...")` que tenia
`cn8` eran canales de observacion que **no producian ninguna observacion**:
escritos a proposito para informar y silenciosos por construccion. Anadido
`info()`, que siempre imprime. Regla: sospechar de cualquier linea que diga
"informativo" y pase por `chk`.

**MIS ERRORES, TODOS MEDIDOS, TODOS DE LA MISMA CLASE.** Un nombre, un numero o
un comentario escrito con forma de dato y no verificado:

1. Al reescribir el resumen de `check.sh` **perdi el `exit 1` de la rama de
   fallos**: una suite con fallos imprimia "1 validacion(es) FALLIDA(S)" y a
   continuacion "TODO CORRECTO", con `rc=0`. **Una suite rota que reporta
   exito.** Y lo compre porque probe las rutas OK e INVALID y **no probe la
   ruta FALLO**, que era la que perdia el `exit`.
2. Defini `autocomprueba_clasificador` dos veces en el fichero; bash usa la
   ultima, asi que funcionaba por casualidad.
3. Dentro de esa autocomprueba, `local fallos=0` **tapaba** el global que
   `resumen` lee, y yo preparaba los casos con variables (`f`, `i`) que
   `resumen` no ve. O sea: **el control no podia probar lo que decia probar**,
   dos veces en el mismo bloque.
4. Escribi `"de 13 casos"` cuando eran 12. Un total escrito a mano; ahora lo
   cuenta el mismo codigo que ejecuta los casos.
5. Busque `FALLA` en un informe que escribe `FALLO`, y conclui que un test
   fallaba en silencio porque no encontraba la palabra que no existe.
6. Afirme que "`check.sh` no distingue el `rc=2`" sin mirar las lineas 256 y 273,
   donde si lo distingue. Medi antes de publicarlo y era falso.
7. Escribi dos ideogramas CJK en un comentario de `check.sh`. Los describo en
   vez de reproducirlos para no dejar CJK en el arbol. Y **CN-R12, un control
   de otra sesion que ya existia, me lo cazó**: esa es la vez que mas me sirve,
   un control escrito por otro me atrapa a mi. Y por el mismo camino dos veces en
   la misma ronda, porque la correccion la escribi en el fichero equivocado.
   sesion que ya existia, me lo cazó**. Esa es la vez que mas me sirve: un
   control escrito por otro me atrapa a mi.

**Y UN VECTOR DE PRUEBA QUE NO ERA VECTOR.** Intente demostrar que el control
nuevo de fences no podia fallar, metiendo un `.md` con fences impares, y el
control **no fallo**: porque mi fichero tenia **4** fences, o sea era **par**. Lo
llamaba "mutacion" sin haber comprobado que mutaba. Si me hubiera parado en
"el control no funciona", habria **borrado un control correcto** por un vector
mal construido. Con el vector bien construido y verificado antes de usarlo (3
fences, comprobado en el acto), el control falla `rc=1` nombrando el documento.

check.sh TODO CORRECTO (rc=0) | cn8 todos los controles pasan | selfcheck 30/30.
GPU INTACTA. WRITE_EXECUTION NONE.
## 2026-10-03 · opencode · EV-44: `gmc_v8_1` ES `gmc_v8_0`, y el nombre del bloque no dice donde vive

```
OBJECT   RESEARCH/.../amdgpu/gmc_v8_0.c, revkit/gfx8blocks.py --funcs
ACTION   LECTURA ESTATICA pura. No se toco la GPU ni el corpus.
TRACK    EVIDENCE · READ_ONLY_CORPUS · WRITE_EXECUTION=NONE · GPU INTACTA
```

**PUNTO DE PARTIDA, Y ERA UN NOT_DETERMINED CONCRETO.** EV-43 dejo abierto que
contrastar, por via estatica, lo que `hw_init` de GMC **deberia haber escrito** con
lo que la telemetria de reposo **si** refleja. Sin tocar la GPU.

**LO PRIMERO, Y FUE FALSO.** `gmc_v8_1.c` no existe en ningun arbol de este repo,
asi que conclui que la pregunta no era cerrable. **Era falso, y por dos suposiciones
encadenadas.** La primera: supuse que un bloque `X_ip_block` vive en `X.c`. La
segunda: cuando esa suposicion fallo, supuse que los arboles estaban podados.

La verdad, medida: **`gmc_v8_1_ip_block` esta definido en `amdgpu/gmc_v8_0.c`**:

```
const struct amdgpu_ip_block_version gmc_v8_1_ip_block = {
        .type = AMD_IP_BLOCK_TYPE_GMC, .major = 8, .minor = 1, .rev = 0,
        .funcs = &gmc_v8_0_ip_funcs,
};
```

O sea que **no existen funciones `gmc_v8_1_*`**, y no por accidentede busqueda: el
bloque v8_1 **reutiliza la tabla de funciones de v8_0 sin cambios**. El `.minor = 1`
identifica la version y **no discrimina comportamiento**. Es el caso "bloque !=
tabla != fichero" de EV-40, aqui con una consecuencia de primer orden: para
POLARIS12, GMC **es** el codigo de v8_0.

**LO QUE `hw_init` HACE, Y LO QUE NO.** `gmc_v8_0_hw_init` para POLARIS12 hace
**cuatro** cosas y nada mas:

1. `gmc_v8_0_init_golden_registers(adev)`
2. `gmc_v8_0_mc_program(adev)`
3. `gmc_v8_0_polaris_mc_load_microcode(adev)` -- rama POLARIS10/11/12
4. `gmc_v8_0_gart_enable(adev)`

**No programa DPM, ni relojes, ni voltajes.** Y esa es la respuesta al
NOT_DETERMINED: **el estado que `gputel` mide en reposo --mclk clavado a 300 MHz,
sclk ~1040 MHz, vddgfx 0,81-0,88 V, PPT 6-7 W-- no lo escribe GMC.** Lo escribe
`pp_smu` (que vive en `pm/powerplay/amd_powerplay.c`, no en `amdgpu/`) y el SMU. Es
la primera vez que la telemetria y el codigo secontradicen de forma util: no se
contradicen, se **reparten**.

**LOS GOLDEN REGISTERS DE POLARIS12, QUE SON CUATRO.** Para POLARIS12 la rama es
`golden_settings_polaris11_a11` y **una sola** secuencia, sin el
`<asic>_mgcg_cgcg_init` que si reciben Fiji, Tonga, Carrizo y Stoney:

```
mmVM_PRT_APERTURE0_LOW_ADDR, 0x0fffffff, 0x0fffffff,
mmVM_PRT_APERTURE1_LOW_ADDR, 0x0fffffff, 0x0fffffff,
mmVM_PRT_APERTURE2_LOW_ADDR, 0x0fffffff, 0x0fffffff,
mmVM_PRT_APERTURE3_LOW_ADDR, 0x0fffffff, 0x0fffffff
```

POLARIS12 **comparte tabla con POLARIS11 y VEGAM**; POLARIS10 tiene la suya. Eso
no es un detalle: es la clase de ASIC de la que sale todo el GMC de esta tarjeta.

**LA TRAMPA QUE MAS CUESTA, Y LA MEDI.** El nombre
`golden_settings_polaris11_a11` esta en **tres** ficheros del mismo arbol, con
contenido distinto:

| fichero | contenido | registros |
|---|---|---|
| `amdgpu/gmc_v8_0.c:92` | `mmVM_PRT_APERTURE0..3_LOW_ADDR` | 4 |
| `amdgpu/sdma_v3_0.c:117` | `mmSDMA{0,1}_{CHICKEN_BITS,CLK_CTRL,GFX/RLC{0,1}_IB_CNTL}` | 10 |
| `amdgpu/gfx_v8_0.c:339` | otra cosa | otra |

Leer el fichero equivocado no da una lista incompleta: da una lista **falsa**, y
de bloques distintos. Un nombre de tabla no identifica su tabla.

**LA RESPUESTA A LA PREGUNTA YA ESTABA HECHA, Y YO NO LA USE.** `gfx8blocks.py
--funcs` **ya resolvia bloque -> fichero** y lo lleva impreso en la columna `en`.
Sus 10 filas:

```
vi_common -> amdgpu/vi.c              gmc_v8_1  -> amdgpu/gmc_v8_0.c
tonga_ih  -> amdgpu/tonga_ih.c        gfx_v8_0  -> amdgpu/gfx_v8_0.c
sdma_v3_1 -> amdgpu/sdma_v3_0.c       pp_smu    -> pm/powerplay/amd_powerplay.c
amdgpu_vkms -> amdgpu/amdgpu_vkms.c   dm        -> display/amdgpu_dm/amdgpu_dm.c
uvd_v6_3  -> amdgpu/uvd_v6_0.c         vce_v3_4  -> amdgpu/vce_v3_0.c
```

Coincide **10 de 10** con lo que derive a mano despues. Y el mismo output muestra
que la divergencia de nombres es **triple**, no doble: en 6 de los 10 bloques el
nombre del bloque, el de la tabla `.funcs` y el del fichero **son tres nombres
distintos** (`gmc_v8_1_ip_block` / `gmc_v8_0_ip_funcs` / `gmc_v8_0.c`). Las 145
funciones registradas salen de ahi.

**MIS TRES INTENTOS FALLIDOS, QUE SON EL CONTENIDO REAL DE ESTA RONDA.** Busque el
bloque en `amdgpu/<nombre>.c` y concluí "8 de 10 ilegibles". Luego mire en el arbol
entero con un extractor propio que **tardo mas de 120 s y fueogado**, y cuya
extraccion de definiciones salio defectuosa (devolvio 0 en vez de 93). El unico
metodo que funciono fue el que ya usaba `gfx8blocks.py`.

La leccion no es "tengo que tener cuidado". Es: **una herramienta VALIDATED que ya
responde la pregunta se usa antes de construir la respuesta a mano**, y cuando la
suposicion propia contradice a la herramienta, la suposicion es lo dudoso. Por
eso, antes de afirmar "no se puede", el orden es: buscar la respuesta en las
herramientas existentes, y despues en el codigo.

GPU INTACTA. WRITE_EXECUTION NONE. NO SE TOCO EL CORPUS.

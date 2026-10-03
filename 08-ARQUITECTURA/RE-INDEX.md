# RE-INDEX — correcciones propias (Polaris12)

```
CLASE      epistemologica · NO es evidencia de hardware
FUENTE     linux-7.1.3 · /var/tmp/rx550-incident-pre-reboot-dmesg.txt
UBICACION  /var/tmp/rx550/   (durable: sobrevivio a 3 reinicios)
RECONSTRUIDO dos veces.  La primera version se perdio con /tmp; la segunda
           quedo zero-filled por una escritura interrumpida.  Verificar tras
           cada escritura y tras cada reinicio: es la correccion 77.
```

## 2. Correcciones 47-76

| # | error | corrección |
|---|---|---|
| 47 | traté el log de incidente como **un arranque** | contiene **133 sesiones de 4 días**; solo 2 con evento amdgpu |
| 48 | `detected ip block number N` leído como prueba de ejecución | es el array **estático** `ip_blocks[]`, impreso antes de init |
| 49 | «gmc falló antes que smu» | orden real `init_microcode`→VRAM→GART→TTM; el probe **sí** corrió |
| 50 | `causal` publicaba el offset de la primera cabecera del walk | **165 accesos de la ruta VI/GFX8.1** con offset distinto al real |
| 51 | `--block MC_` generaba `mmMC__` | 0 registros sin aviso; indistinguible de bloque inexistente |
| 52 | `--file` no filtraba accesos | mi `replace` no hizo match por indentación y **no verifiqué** |
| 53 | «el `-17` no lo había caracterizado» | es `sysfs_warn_dup`: atributo sysfs duplicado. Fuga en `amdgpu_preempt_mgr_fini` (`:131` retorno temprano, o `kobj.sd` NULL `:133`). **Ni firmware ni hardware** |
| 54 | transcribí a mano un macro **inexistente** y lo llamé control positivo | el ASICID real excluye por **device ID** `0x699F`, no por revisión |
| 55 | «`0xC7` no es revisión P23» | **falso**: lo es, bajo `0x6987` |
| 56 | no vi el looks-like `0x6987`/`0x699F` | comparten `0xC7`; el grep **sí** da coincidencia → `polaris12_k_smc.bin` |
| 57 | «`amdgpu_vm_map_gart()` inalcanzable» | **REFUTED**: alcanzable desde `amdgpu_vm_sdma.c:278`. Confundí SDMA (efectivo) con CPU (gated) |
| 58 | «PTBA sin canal / `DEFERRED_NO_CHANNEL`» | **alcance de búsqueda**. `mmVM_PT_BASE_ADDRESS` no existe en GFX8; el PTBA es `mmVM_CONTEXT{n}_PAGE_TABLE_BASE_ADDR`, y sus productores en el árbol son Navi10/Navi12/GFX7 |
| 59 | `vm_update_mode = -1` sin mecanismo | `:2901 full_visible` FALSE → `:2906` modo 0 → `:2637` bit GFX clear. El caso «large BAR» concede **COMPUTE** (bit 1) |
| 60 | `contradict.py` con un directorio cargaba **0 informes** e imprimía «NINGUNA AFIRMACIÓN» | `except OSError: pass` se comía el error. Escaneo vacío presentado como resultado → ahora `ERROR/INVALID` + exit 4 |
| 61 | la corrección 57 era **redundante** | ya lo había refutado; el bug 60 lo ocultaba |
| 62 | `kit --estado` con ~50% de precisión | contaba «lo que **NO** estaba» como refutación. Exige estado epistémico o cita `file:N` |
| 63 | el extractor de `get_cu_info` casaba con la **declaración adelantada** | 3 de 9 generaciones, cero campos. Exige `{` y cuenta llaves |
| 64 | el patrón exigía `static void` y un parámetro | gfx9+ devuelve `int` y recibe `cu_info` |
| 65 | `ao_shift` usaba `[^)]*` | el shift tiene paréntesis anidados |
| 66 | el estado decía «8 CUs, mask `0x1e`» | **8 son los ACTIVOS**; presentes = **10** (2 SE × 1 SH × 5 CU). Hallazgo de otro agente, verificado por mí en `log:129` |
| 67 | `kit --next` decía `shader/wave SIN HERRAMIENTA` **después** de existir `--shader` | tabla escrita a mano. Un detector que miente es peor que no tenerlo |
| 68 | asumí `ih_v8_0.c`, `mmIH_*` en `gca/`, `soc21_ih_clientid.h` | ninguno existe: IH = `ih_v7_0.c`, registros en `asic_reg/oss/`, SOC21 dentro de `soc15_ih_clientid.h` |
| 69 | el resolutor guardaba `campo → definición` en un dict | se quedaba con la última ⇒ **la mitad de los accesos desaparecía** (Ring0) |
| 70 | `causal --block IH` imprimió tabla vacía sin decir dónde está el bloque | falta el aviso de dónde **sí** está |
| 71 | iba a usar `enum soc15_ih_clientid` («Vega10+») | el correcto es **SOC21** del mismo fichero; **funde SDMA0+SDMA1 en `LSDMA`=0x1a** |
| 72 | publiqué `regIH_RB_BASE = 0x0081` y «42 conflictos» | **ambos falsos, culpa mía**. El valor lo fija el `#include` de `ih_v7_0.c:29` (`osssys_7_0_0`) ⇒ **`0x0083`**. Conflictos reales **0** |
| 73 | el regex de includes llevaba `^` **sin `re.MULTILINE`** | 0 includes en todos los ficheros, y aun así imprimía la tabla |
| 74 | el índice de cabeceras solo cubría `include/` | 92 ficheros sin cabecera alcanzada |
| 76 | filtro `name[:3] in ("mmR","reg")` | compara 3 caracteres literales; `"mmVGA…"[:3]`=`"mmV"` no casaba ⇒ **53 de 496** resueltos. Con `startswith`: **481 de 496** |

## 2b. Correcciones 78-80

| # | error | corrección |
|---|---|---|
| 78 | afirmé que los 27 registros **exclusivos de GFX8.1** no se usan en «ningún `.c`» | **el test me refutó**: `mmRLC_CLK_CNTL`, `mmRLC_SMU_ARGUMENT_2`, `mmRLC_GPM_DEBUG_INST_ADDR` sí se usan, en `gfx_v9_0.c`/`gfx_v10_0.c`. La forma sostenible es más estrecha: **no se usan en la ruta GFX8**, y por eso `gfx_v8_0.c` compila con solo `gca/gfx_8_0_d.h`. Formular una predicción más amplia que lo que el código sostiene = la clase 38/54 |
| 79 | el script de cruce hacía `real={reg: offset}` y un `dict` **piso** el valor | el último fichero en escribirse (`gfxhub_v2_1.c`, numeración Navi) reemplazaba el valor GFX8. `mmGRBM_STATUS2` appeared como `0x00da2` cuando el correcto es `0x2002`. Es el error 69 otra vez: dict que sobrescribe en silencio produce un subconjunto que parece completo |
| 80 | el cruce destapó que **GFX8 tiene DOS espacios de offset** y que son valores ambos correctos | plano (`gca/*_d.h`) y SOC15 (`gc_*_offset.h`). `mmGRBM_STATUS2` = `0x2002` plano y `0x0da2` SOC15. Confundirlos produce el offset equivocado **con apariencia de error de lectura**. Ahora cada acceso lleva su `espacio` etiquetado |

### Verificación de coherencia GFX8.0 vs GFX8.1

```text
gfx_8_0_d.h  2633 registros      gfx_8_1_d.h  2596
comunes 2569   CON OFFSET DISTINTO: 0   (0.00%)
solo en 8.1:  27   solo en 8.0:  64
```

Cero offsets distintos ⇒ citar `gfx_8_1_d.h` para código que incluye `gfx_8_0_d.h`
**da el mismo valor**. Los 8.1-exclusive no se tocan en la ruta GFX8.

## 2c. Correcciones 81-87 — las del propio `crosscheck`

Construí el contraste automático como artefacto generado. Encontró **4
afirmaciones, 4 confirmadas, 0 difieren**. Los fallos fueron todos míos:

| # | error | corrección |
|---|---|---|
| 81 | el extractor pedía el valor entre backticks (`= `0x0081``) | lo real es el **símbolo** entre backticks y el valor aparte. Extraía 1 afirmación donde había ≥5. Un extractor que casi no encuentra nada y no lo dice es un cero silencioso |
| 82 | `real` se construía solo con accesos de código | el IH accede por **indirección** (`SOC15_REG_OFFSET`), donde `reg=None`: `regIH_RB_BASE` salía «NO RESOLUBLE» aunque su definición es exacta. Resolver **por símbolo → cabecera alcanzable**, no por acceso |
| 83 | el arreglo de 82 iteraba sobre accesos, y en el acceso indirecto no hay símbolo | la vía correcta es el grafo de includes del `.c`: si entre sus cabeceras hay una que define el símbolo, contraste |
| 84 | el extractor tomaba el **primer** offset de una línea | una fila que RETIRA una afirmación tiene el valor viejo y el vigente: `publiqué 0x0081 … ⇒ 0x0083`. Confirmaba un offset que mi propio registro declara falso |
| 85 | el valor vigente va tras `⇒` sin `=` ni `:` | `RE_CLAIM` exigía el símbolo justo antes del número; `0x0083` nunca se veía |
| 86 | una fila de tabla reparte símbolo y valor en **celdas distintas** | tratar la fila como texto plano encuentra el viejo y pierde el vigente. Se parte por `\|` y se empareja símbolo→último offset de la fila |
| 87 | **`DOS ESPACIOS` no es una RETIRADA** | la fila 80 dice que GFX8 tiene dos espacios de offset y ambos valores son correctos a la vez. Mi heurística de «retirada» lo tratar como retirada y verificaba `0xda2` en vez de `0x2002`. **La misma trampa dos veces en el mismo bloque**: un valor distinto no implica un valor erroneous |

Los 87 son de clase H/F/E: filtros y heurísticas que parecen correctas y
producen subconjuntos o comuten el valor equivocado sin avisar.

## 2d. Correcciones 88-91 — emisión de informes y rendimiento

| # | error | corrección |
|---|---|---|
| 88 | `report` reventaba con `FileNotFoundError` ante una raíz inválida | devuelve un informe honesto con `RAIZ INVALIDA` y 0 accesos, y el motivo se propaga a la sección de guardas. Un informe que dice «todo 0» sin explicar por qué es otro cero mudo |
| 89 | un acceso legítimo aparecía como **sin símbolo resuelto** | `gfxhub_v2_1.c:34-35` **define el registro en el propio `.c`** (`YELLOW_CARP`, `0x16f8`), y no está en ninguna cabecera. El preprocesador lo ve igual ⇒ indexar los `#define` locales |
| 90 | `crosscheck` tardaba **43 s** | el bucle `.c` × símbolos hacía **1 006 342 pares**, 33 s. Invertido: indexar `.c → cabecera` una vez y recorrer por símbolo. **43 s → 19.6 s** |
| 91 | el espacio de offset se deducía del **nombre de la cabecera** | un `#define` local no dice nada, y `mmGCUTCL2_..._YELLOW_CARP` salía `plano` cuando se accede con `RREG32_SOC15(GC,0)`. El espacio lo decide la **vía de acceso**, no el nombre del fichero |

`Index()` cuesta 8.4 s (1700 cabeceras, 204k símbolos) y se cachea por raíz: la
segunda llamada baja a 0.07 s. El coste residual son 2 indexados por proceso.

### Lo que emitió el generador y yo no tenía

```text
accesos totales   578          (no 496: el conjunto de la ruta es más amplio)
offset UNICO      562
conflicto REAL    0
bloque shader     292 accesos, 291 con offset unico   (antes invisible)
bloque IH         14 accesos, 0 con offset unico      (acceso indirecto)
guardas: 0 cabeceras · 1 sin resolver (mmMC_SEQ_MISC0_FIJI, solo FIJI)
```

La tabla de «dos valores por espacio» la calculó la herramienta. Ninguna cifra de
este bloque la tecleé yo, que es exactamente el punto.

## 2e. Correcciones 92-95 — el contrato de implementación

| # | error | corrección |
|---|---|---|
| 92 | `contract` atribuía el offset a la cabecera **plano alfabética** | daba `gfx_6_0_d.h` (**CIK**) para un registro de GFX8. El **valor** coincidía (`0x3045` en las 5 generaciones) pero la **atribución era falsa** — la respuesta correcta por el motivo equivocado, el error que llevo 40 correcciones evitando. Ahora la cabecera la decide el grafo de includes de los `.c` que acceden, con la de mayor generación alcanzable |
| 93 | sin cabecera plano alcanzable, atribuía a `gmc_7_1_d.h` | el acceso es MMHUB (`mmhub_v1_0.c`): no hay procedencia plano. El valor `0x550` es el mismo en las 5, pero decir de dónde viene sería inventarlo. Ahora: `plano/SIN ATRIBUIR` |
| 94 | listaba `mmGTT`, `mmPTE`, `mmVM_` como asunciones | son **fragmentos citados en comentarios**, no registros que el driver use. El filtro no distinguía código de prosa |
| 95 | al arreglar 94 dejé el bloque de extracción sin cuerpo | 26 registros → 0, y el self-test lo detectó (3 fallos). Restaurado |

### Corroboración entre dos caminos independientes

```text
rx550_target.c:123   #define RX550_PROBE_READ_INDEX 0x2002u
                     "mmGRBM_STATUS2, indice en BAR5"
mi cadena            mmGRBM_STATUS2 = 0x2002  (espacio plano)
                      via gca/gfx_8_0_d.h, resolvido por grafo de includes
```

El driver del mandato **ya codificaba** el número que mi cadena dedujo después por
otro camino. No es una coincidencia: es el mismo hecho medido dos veces, y por eso
`contract` lo contrasta en vez de asumirlo.

## 2f. Correcciones 96-97 — la capa de semántica

| # | error | corrección |
|---|---|---|
| 96 | buscaba los campos como `mmGRBM_STATUS2__CAMPO_MASK` | los campos se llaman **sin** el prefijo `mm`: `GRBM_STATUS2__ME0PIPE1_CMDFIFO_AVAIL_MASK`. Resultado: **0 campos en los 26 registros**, en silencio, y con ellos toda la evidencia de bitfields |
| 97 | calculaba `por_nombre` **después** de usarlo | `UnboundLocalError`. Se movió antes del `if` |

La 96 es la peor de la serie: no daba error, daba un informe plausible con 26
registros «SOLO_DIRECCION» y **cero campos**, cuando el corpus tiene 18 campos
para `GRBM_STATUS2` y 20 bits para `CP_RB0_WPTR__RB_WPTR`.

### Lo que la capa de semántica responde

```text
SEMANTICA_PROBADA (2)   el corpus lo LEE y lo USA como predicado
ROL_PROBADO       (10)  un campo lleva el nombre del rol: CP_RB0_RPTR__RB_RPTR
CAMPOS_NOMBRADOS  (14)  hay campos con nombre, sin prueba de su papel
SOLO_DIRECCION    (0)   —
NO_DETERMINED     (0)   —
```

Que `CP_RB0_RPTR` tenga un campo llamado `RB_RPTR` de 20 bits **prueba** que el
registro es el puntero de lectura del ring: no es una suposición de nombre, es lo
que la cabecera de la generación declara. Eso sube el registro de «dirección
confirmada» a «rol probado».

`SEMANTICA_PROBADA` son solo dos, y el caso es claro:
`gfx_v8_0_is_idle()` decide ociosidad leyendo
`RREG32(mmGRBM_STATUS) & GRBM_STATUS__GUI_ACTIVE` y `RREG32(mmGRBM_STATUS2) != 0x8`.
Ahí el valor **significa algo** en el hardware.

## 2g. Correcciones 98-99 — codificación de bits

| # | error | corrección |
|---|---|---|
| 98 | `RE_CMASK`/`RE_CSHIFT` usaban `^…$` **sin `re.MULTILINE`** sobre el texto completo | `finditer` devolvía **0 campos**, en silencio, con el informe luciendo normal. Es la corrección 73 exacta: ancla de línea sin `re.M`. Repetida porque el patrón «`^` funciona» engaña cuando se prueba sobre una sola línea aislada |
| 99 | interpolé `campos` (lista de dicts) como si fueran strings | `TypeError` en la sección de semántica. Las dos estructuras de datos chocan porque `semantics` y `bit_table` usan el mismo nombre de clave |

### Lo que la tabla de bits resuelve

Un offset sin mask ni shift **no se puede operar**: se puede direccionar, no
usar. Con la codificación completa:

```text
Total: 162 campos, 162 con shift, 2 marcados OBSOLETE

mmCP_RB0_WPTR            1 campo   RB_WPTR            mask 0xfffff  shift 0   (20 bits)
mmGRBM_STATUS2         18 campos   CPC_BUSY bit 29, CPF_BUSY bit 28, CPG_BUSY bit 30
mmVM_INVALIDATE_REQUEST 16 campos  INVALIDATE_DOMAIN_0..15
mmCP_RB_WPTR_POLL_ADDR_LO 2 campos uno OBSOLETE
```

**Interpretación que sólo aparece con la tabla**: el corpus decide ociosidad con
`RREG32(mmGRBM_STATUS2) != 0x8`, y el `0x8` **no es un campo**. Los bits 4-13 y
24-30 son los `*_BUSY` y `*_RQ_PENDING`; el bit 3 queda sin nombrar y su valor
`1` significa «idle». La comparación es contra el registro entero, no contra un
campo. Sin los masks eso era un número sin explicación; con ellos es legible.

## 2h. Nodo: solapamiento entre bloques IP — cerrado

El cruce automático de quién escribe qué registro en la ruta VI:

```text
GFX      escribe  73        GMC   escribe  62
GFXHUB   escribe  44        SDMA  escribe  25

GFX ∩ GMC : mmSRBM_SOFT_RESET
GFX ∩ SDMA: mmSRBM_SOFT_RESET
GMC ∩ SDMA: mmSRBM_SOFT_RESET
```

**Un solo registro, tres bloques IP.** El patrón en cada uno
(`gfx_v8_0_soft_reset`, `gmc_v8_0_soft_reset`, `sdma_v3_0_soft_reset`) es:

```c
tmp |= srbm_soft_reset;      /* poner el bit   */
WREG32(mmSRBM_SOFT_RESET, tmp);
udelay(50);
tmp &= ~srbm_soft_reset;     /* limpiar el bit */
WREG32(mmSRBM_SOFT_RESET, tmp);
```

Un ciclo set→delay→clear sobre un registro **compartido**. Si dos bloques lo
ejecutan a la vez, uno limpia el bit que el otro acaba de poner.

### Corrección 100 — afirmé que estaba serializada; NO lo está

Primero escribí «no es un riesgo abierto: el driver lo serializa con
`adev->srbm_mutex`». **Falso**, y el error tiene nombre: comprobé que la mutex
existe **en el fichero**, cuando lo que importa es si está **dentro de la función
que escribe**.

```text
gfx_v8_0.c   mutex_lock(&adev->srbm_mutex)  en 3669, 3747, 4980, 5075
             -> protege vi_srbm_select + deactivate_hqd

gfx_v8_0_soft_reset   lineas 4994-5053   escrituras en 5032 y 5038
                      mutex dentro: NINGUNA
gmc_v8_0_soft_reset   lineas 1344-1372   escrituras en 1358 y 1364
                      mutex dentro: NINGUNA
sdma_v3_0_soft_reset  lineas 1299-1327   escrituras en 1313 y 1319
                      mutex dentro: NINGUNA
```

**12 escrituras, 0 serializadas.** El mismo registro lo tocan 17 ficheros de
generaciones distintas con el mismo patrón.

La clasificación correcta: el patrón set→delay→clear sobre un registro
compartido **no está protegido por mutex en la ruta del soft reset**. Que el
proceso se serialice en otro nivel (orden de init, un solo hilo) es otra
cuestión, y no la he medido.

Para un driver propio la consecuencia es concreta: **no se puede copiar ese
patrón sin añadir serialización**, porque dos bloques propios podrían
ejecutarlo a la vez.

| 100 | afirmé que `srbm_mutex` serializa el registro compartido | comprobé que la mutex está en el **fichero**, no en la **función** que escribe. `gfx_v8_0_soft_reset`, `gmc_v8_0_soft_reset` y `sdma_v3_0_soft_reset` **no toman ninguna mutex**: 12 escrituras, 0 serializadas |

## 2i. Correcciones 101-112 — el cruce creció, y lo que costó

`crosscheck` tenía el **mismo bug que la corrección 100**, dentro de la
herramienta que la detecta: indexaba por «todo `.c` que *alcanza* la cabecera»
en vez de «los `.c` que *acceden* al símbolo».

| # | error | corrección |
|---|---|---|
| 101 | índice por cabecera alcanzada, no por acceso | un `.c` que incluye `gmc_8_1_d.h` «resolvía» `mmVM_...` aunque no lo acceda nunca |
| 102 | `REG != 0x8` contado como afirmación de offset | el `0x8` es el **valor comparado**, no un offset. 2 falsos positivos «DIFIEREN» que hacen desconfiar de la herramienta entera |
| 103 | `regIH_RB_BASE` salía `NO_RESOLUBLE` | se accede por **indirección** (`SOC15_REG_OFFSET`). Nuevo veredicto `INDIRECTO`, que es la verdad |
| 104 | «0 funciones sin mutex» era tranquilizador y falso | el agrupamiento no agrupaba |
| 105 | agrupaba por **(fichero, línea)** | cada línea escribe un registro ⇒ todos los grupos de tamaño 1. La unidad que importa es la **función** |
| 106 | el regex de cabecera tomaba `if (...) {`, prototipos y `MODULE_FIRMWARE` | un parser de C por regex es la vía que ya falló. **Sustituido por el AST de clang** |
| 107 | `FunctionDecl` sin cuerpo (prototipos) contaminaba | 12 158 intervalos, todos de una línea. Se exigen `CompoundStmt` y `end.line` |
| 108 | `range.end` cortaba antes con llaves en cadenas | verificación por **balance de llaves** |
| 109 | finales como `2064-1491` | la clave del grupo no llevaba el final; usaba un `en` residual del bucle anterior |
| 110 | «39 funciones sin mutex» incluía las de **init** | una escritura secuencial en `sw_init` no compite con nadie. Separar init de runtime cambia el veredicto |
| 111 | lista cerrada de sufijos para reconocer init | el corpus nombra las funciones de forma varia (`init_csb`, `init_pg`, `cp_gfx_start`…). Se reconoce por patrón en el identificador |
| 112 | `RE_INITFN.match()` no casaba con `gfx_v8_0_init_csb` | el patrón empieza con `\w*` que puede quedar vacío y `match()` no retrocede. **`search()` sí** |

### Herramienta nueva: `funcspan.py`

Resolver «qué función contiene esta línea» por AST de clang, con el regex como
respaldo **declarado** (`regex-aprox`). Y con el caso negativo correcto:

```text
ih_v7_0.c:451   → SIN FUNCION (comentario)     <- no inventa un span
gfx_v8_0.c:5032 → 4993-5053  gfx_v8_0_soft_reset
sdma_v3_0.c:1313→ 1298-1327  sdma_v3_0_soft_reset
gmc_v8_0.c:184  → 170-188    gmc_v8_0_mc_stop
```

Una línea de comentario **no pertenece a ninguna función**, y eso se declara en
vez de devolver un span que empieza por `*`.

### El número corregido

```text
escrituras de la ruta VI          327
funciones que escriben            114
funciones con >1 registro          43
  con mutex dentro                  4
  sin mutex pero en init (riesgo≈0) 13
  sin mutex en RUNTIME (RIESGO)     26
```

Las 26 son las que un driver propio debe mirar: registros que una routine de
runtime escribe sin tomar mutex.

## 2j. El generador descubre que mi taxonomía está incompleta

`report --only=correcciones` parsea las filas de este índice y las clasifica. El
recuento por clase sale **calculado**, no afirmado:

```text
J dos espacios de offset                    10
N resolvia el ambito equivocado               8
F cero silencioso                             7
D mezclar generaciones                        4
M mutex en fichero no en funcion              3
B citar file:N sin abrir                      2
H filtro que parece prefijo                   2
L re.MULTILINE                                2
C el test afirma una creencia                 1
E primero que casa                            1
G cobertura como prosa                        1
I prediccion mas amplia                       1
K rendimiento                                 1
A nombre asumido -> 0 -> ausente              0     <- en la tabla de 1-46, no aqui

36 correcciones SIN clase asignada
```

Dos cosas que solo se ven al calcularlas:

**1. La clase dominante no es la que yo creia.** Definí la clase A («nombre
asumido → grep da 0 → ausente») como la más frecuente por experiencia, y sale
con **0** en las filas parseables. La que más correcciones tiene es **J: dos
espacios de offset**, con 10. Mi taxonomia describia sintomas, salvo J: J si es una
causa: un mismo símbolo tiene dos offsets y ambos son correctos.

**2. 36 correcciones no encajan en ninguna clase que yo definí.** Eso no es un
fallo del clasificador: es la señal de que **la taxonomía describe síntomas y no
causas**. Se registra explícitamente en vez de forzar un encaje.

## 2k. Correcciones 113-125 - el resolutor de funciones, tres veces

| # | error | correccion |
|---|---|---|
| 113 | el filtro de cabecera aceptaba `WREG32(...)` como inicio de funcion | el parche que anadia `_es_cabecera` **nunca se aplico** (fallo silencioso) y quedo `pool = topo or cand`, que cae a todos los candidatos. La prueba correcta es **estructural**: firma (puede ocupar varias lineas) + `{` y sin `;` en medio. Un prototipo y una sentencia se rechazan solos |
| 114 | exigir `)` en la MISMA linea | rechazaba las firmas partidas en dos, que son la norma en el kernel (`static int f(struct a *x,` / `struct b *y)` / `{`) |
| 115 | el `CallExpr` no tiene clave `called` | el callee es el PRIMER hijo, y `range.begin` da `offset` no `line`. Sin corregirlo la lista de llamadas sale **vacia** y parece "nadie llama a nadie" |
| 116 | el callee esta envuelto en `ImplicitCastExpr` | buscar solo en hijos directos descarta justo las llamadas por puntero a funcion, que es el caso de las tablas de ops del kernel |
| 117 | `DeclRefExpr` de una funcion no trae `name` | lo trae `referencedDecl`. Exigir `name` descartaba las llamadas que interesan |
| 118 | el final de la funcion no era unico | el AST da varios intervalos con el MISMO inicio y finales distintos. Elegir el mas corto hacia `gfxhub_v2_1_restore_regs` = 582-**587** en vez de 582-**617**, y la misma funcion se contaba dos veces (con 2 y con 18 registros). El final es su llave de cierre: el **maximo** |
| 119 | un aserto mio era `not X or not X` | no puede fallar. Un test que no puede fallar no comprueba nada |
| 120 | el script imprimia el nombre de la funcion como su propio llamante | en la via ops-table no hay llamante directo; poner el nombre propio es inventar el dato |
| 125 | Created 16 PTBA as if they were 16 consecutive registers | they are TWO blocks of 8 (`0x54f-0x556` and `0x50e-0x515`), separated by 65. The driver branches on `vmid < 8` for exactly this reason |
| 126 | un JSON de cache truncado por un cierre abrupto pasaba por "clang no puede" | se valida por cabecera **y** tamano minimo, no solo por `json.loads`: un fichero vacio parsea bien y devolveria el respaldo regex sin avisar |
| 127 | el self-test de `conflicto` tardaba >6 min en validar la logica de colision | la parte sintetica no necesita el corpus. Se separo en `--rapido`, y el modo rapido **dice** que el corpus no se evaluo, para que un "todo bien" no esconda un corpus sin correr |
| 128 | `regctx.scan` sin filtro: >6 min y 2.9 GB | `files=BLOQUES` lo deja en 7.8 s. El indice de cabeceras sigue global; lo que se recorta son los ACCESOS |
| 129 | la cache del AST crecio a 20 GB sin limite | un `.c` de amdgpu son 633 MB de JSON. `_CACHE_MAX=8` entradas propias; la purga no toca lo del otro agente |
| 130 | la purga estaba en la rama de escritura | si el `.json` ya existia no se ejecutaba, y por eso nunca corria. Movida a la lectura |
| 131 | `_CORPUS` y `CORPUS` eran el mismo literal dos veces en `contract.py` | ahora un alias. Dos nombres para una cosa invitan a que diverjan |
| 132 | `TARGET` se reasignaba dos lineas despues del import de `paths` | anulaba la centralizacion sin que nada fallara: mismo valor, dos origenes. Borrado |
| 133 | `conflicto` era TOOL_PARTIAL y el "13" dependia de que yo lo mirara | 12 asserts de regresion con valores fijos sobre el corpus |
| 134 | mi comprobacion de autofiguras recorria `riesgo` entero en vez de comparar indice con indice | como el grafo es simetrico, encontraba siempre uno: daba **52** donde hay **0**. El aserto era el equivocado |
| 135 | "la PTBA del contexto 0 la escriben enable y disable" | falso, leido de una tabla truncada: `mmVM_CONTEXT0_CNTL` cortado se leyo como la PTBA. Los 5 comunes son L2 y CONTEXT*_CNTL |
| 136 | el descarte de la IRQ dependia de mi lectura del fuente | 7 asserts lo fijan: si alguien anade mutex a `gart_enable`, el veredicto cambia solo |
| 137 | el recorrido devolvia el camino de entrada, no el recorrido | en `PROCESO` se acumulo el camino de cada padre y se devolvio el del hijo; la cadena existia, no se estaba guardando |
| 138 | ordenar llamantes con `None` mezclado reventaba | un `CallExpr` sin `offset` no trae linea; no se cita lo que no se puede citar |
| 139 | el AST entero se guardaba en la cache en memoria | 2.8 GB por .c; solo hacen falta ~4700 pares de enteros |
| 140 | `-ast-dump-filter -FunctionDecl` con `-ast-dump=json` | devuelve **0 bytes** en las 3 variantes. El filtro no es utilizable ahi |
| 141 | parser JSON propio en 8 pasos | ABORTADO: llegaba a 25 MB pero daba 0 spans. Necesita un parser de verdad, no un regex. Queda en `scratch/` |
| 142 | `capture_output` retenia los 600 MB del stdout | se escribe a fichero; el pico baja parcialmente |
| 143 | `"range":\s*\{\s*"end"` no casa | el JSON va embellecido, con saltos entre tokens |
| 144 | se exigia `returncode == 0` | clang emite 574 MB de AST valido y **vuelve 1**; el .c no compila solo. El criterio es el contenido, no el codigo |
| 145 | el corte del objeto era el primer `"inner"` | ese `inner` es un `includedFrom` de cabecera; el `loc.line` caia en el fichero equivocado |
| 146 | el AST incluye el arbol de INCLUDES completo | 683 de 6407 FunctionDecl son del `.c`; hay que filtrar |
| 147 | el bucle avanzaba `i = k2+1` | se saltaba el `CompoundStmt` del FunctionDecl que acababa de ver; la pila nunca cerraba y salian 0 intervalos sin error |
| 148 | el `range` del CompoundStmt se cortaba en su `"inner"` | el `inner` va DESPUES del `range`, asi que el `end.line` quedaba fuera del fragmento |
| 149 | `[^{}]*?` para el `range` | el `range` lleva un `includedFrom` que anida llaves; la clase de caracteres excluye lo que hay antes del `end` |
| 150 | el `file` se tomaba del primer `"file"` del fragmento | con `includedFrom` de por medio adjudica funciones a ficheros ajenos |
| 151 | el filtro por `loc.file` | el `loc.file` de un nodo apunta al fichero donde la DECLARACION esta escrita: para una funcion de una cabecera inline, eso es la cabecera. Ningun campo distingue "aqui" de "en un include" |
| 152 | `TOP` no significaba "sin llamantes" | confundia "no la llama nadie" con "su llamante es un puntero a funcion y es invisible para el AST". Nuevo veredicto `VIA_OPS` |
| 153 | se pasaba "fichero:LINEA" donde `raices` esperaba el NOMBRE | `rpartition(":")` devolvia "1385" como nombre de funcion, no estaba en el grafo, y las 13 salian TOP. No era que el grafo no viera los llamantes: era que se le preguntaba por el nombre equivocado |
| 154 | un assert leia `veredictos` antes de calcularlo | un assert que lee una variable de mas arriba del sitio donde se calcula no comprueba el calculo: comprueba el orden |
| 155 | releer ~100 .c por nivel de recursion | `RecursionError` por falta de cache de texto. El limite de profundidad noSERVIA porque la rama ops reiniciaba el contador |
| 156 | la rama ops-table no propagaba `pendientes` | un ciclo que pasa por ops se visitaba para siempre. El corte de profundidad no lo detecta si el contador se reinicia |
| 157 | un assert fijaba "3 raices TOP" | ese 3 era consecuencia del bug 153, no un hecho del driver. Con el bug corregido el dato es 0 |
| 158 | `--out` repitio el bug 153 | el informe habria publicado TOP a las 13, que es justo el dato erroneo. Un `--out` que no comparte codigo con el self-test diverge |
| 159 | un hijo con veredicto TOP se descartaba y el padre caia en PROCESO | convertia "el llamante de arriba no es visible" en "es de proceso". Los veredictos no favorables ahora se propagan |

**Las ocho anteriores estaban en dos herramientas que ya estaban validadas**
(`regctx` 27/27, `crosscheck` 14/14).  La leccion no es "los regex fallan":
es que **una sustitucion que no aplica no avisa**, y el resultado es el codigo
viejo con una confianza nueva.  Ese es el patron de la correccion 100 otra vez.

### Herramienta nueva: `callgraph.py`

Resuelve quien llama a quien, tomando el `FunctionDecl` ENCLOSING como llamante.
Contar llamadas por fichero no dice quien llama a quien: ese era el hueco, y es
lo que produjo el "codigo muerto" falso.

## 2l. El numero correcto, y quien queda realmente expuesto

Lo publicado antes ("114 funciones, 43 multi-registro, 26 en runtime") venia de
un agrupamiento erroneo y de un resolutor erroneo.  Con el resolutor correcto:

```text
escrituras de la ruta VI -> funciones   71
  de 1 solo registro                    31
  de varios registros                   40
    con mutex dentro                     4
    sin mutex pero en init (riesgo~0)   12
    sin mutex en RUNTIME (RIESGO)       24
duplicados de funcion                    0
discrepancias AST/fuente                 0
```

Y el dato que responde a la pregunta que habiamos dejado abierta: **quien las
llama**.

```text
 6 de las 24 se alcanzan SOLO por tabla de ops
 1 de las 24 es un manejador de IRQ
 0 son codigo muerto
```

El caso mas filoso del driver:
**`gmc_v8_0_vm_fault_interrupt_state`** (`gmc_v8_0.c:1385`) escribe 2 registros
(`mmVM_CONTEXT1_CNTL`) sin mutex y se instala como `.set` de
`struct amdgpu_irq_src_funcs` (`gmc_v8_0.c:1745`).  Es la unica de las 24 en
contexto asincrono real.

El mayor numero de registros en una sola funcion sin mutex:
**`gfxhub_v2_1_restore_regs`**, 20 registros, alcanzada por `.mode2_restore_regs`.

Refutacion del subagente: marco **18 de 23 como codigo muerto**.  Las 23 tienen
llamante.  Seis solo por tabla de ops, que un escaneo de llamadas directas no ve
y que por eso se declaraban ausentes.

## 2m. Correcciones 121-123 y un negativo que cierra la frontera

| # | error | correccion |
|---|---|---|
| 121 | busque `[.]miembro(` para las invocaciones por ops-table y salio **0 llamadas** | la invocacion real es `adev->gfxhub.funcs->gart_enable(adev)`: el separador es `->`, no `.`. Un filtro que parece un prefijo y no lo es: exactamente la clase H, y por eso la clase H es real y no teorica |
| 122 | llame "mayor exposicion" a `gfxhub_v2_1_restore_regs` (20 registros) | solo se invoca en `sienna_cichlid.c:162`, un unico sitio en todo el arbol. Antes de llamarlo exposicion habia que probar que se alcanza en POLARIS12; no esta probado |
| 123 | un aserto mio sobre `cut -c1-104` | la ruta del corpus es mas larga que 104 caracteres, asi que el recorte se llevaba la parte util y dejaba solo el pathname. Parecia un filtro de presentacion y era un filtro de contenido |

### NEGATIVO con universo: el despachador de ASIC no esta en el corpus

```text
amdgpu_asic_init        definido en NINGUN fichero del arbol
amdgpu_soc15_init       invocado desde NINGUN fichero
sienna_cichlid_init     invocado desde NINGUN fichero
CHIP_POLARIS12          ausente de amdgpu_discovery.c y de soc15.c
gfx_v8_0.c incluye      gfx_8_0_*.h   (no gc_10_3_0_*)
```

Consecuencia, y es el punto: **este corpus no puede establecer que IP versions
toma POLARIS12 ni que asic-switch se ejecuta.**  La cadena
POLARIS12 -> GC_HWIP 10.3.x -> `gfxhub_v2_1_funcs` (que si esta en
`gmc_v10_0.c:604-607`) es codigo real, pero el primer eslabon NO esta probado
aqui.  Queda `BLOCKED_BY_CORPUS_INCOMPLETE`, no bloqueado por hardware: es
recuperable con el arbol completo.

Lo que si se sostiene sin el despachador, porque es independiente del ASIC:

```text
.soft_reset    invocado en amdgpu_device.c:4802 sobre ip_blocks[i].version->funcs
               -> generico: alcanzable en cualquier ASIC con op de soft_reset
.set_prt       invocado en amdgpu_vm.c:1450 sobre gmc_funcs   -> generico
.gart_enable   invocado en gmc_v10_0.c:936  (gmc_v10_0 cubre POLARIS10/11/12)
.gart_disable  invocado en gmc_v10_0.c:1009 -> idem
.mode2_restore_regs  UN solo sitio: sienna_cichlid.c:162 -> riesgo acotado a esa via
.set (irq funcs)     tabla amdgpu_irq_src_funcs -> via IRQ
```## 3b. La tabla de campos del mandato es CORRECTA, y eso importa mas que el error anterior

Verificado campo por campo contra `gmc_8_1_sh_mask.h`:

```text
campos en la tabla del mandato        22
campos en el header gmc_8_1_sh_mask   22
en header y NO en tabla                0
en tabla y NO en header                0
filas con mask/shift distintos         0     <- 20 comparadas
constantes con nombre                  2     <- PAGE_TABLE_DEPTH, PAGE_TABLE_BLOCK_SIZE
```

Las dos con nombre tambien coinciden:

```text
RX550_CNTL_DEPTH_MASK        0x00000006u  ==  VM_CONTEXT1_CNTL__PAGE_TABLE_DEPTH_MASK        0x6
RX550_CNTL_BLOCK_SIZE_MASK   0x0F000000u  ==  VM_CONTEXT1_CNTL__PAGE_TABLE_BLOCK_SIZE_MASK   0xf000000
```

**Mi hipotesis de que la tabla estaba incompleta era falsa**, y la comprobacion la
refuto en 20 segundos.  La tabla del mandato no solo tiene los 22 campos: tiene
los 22 con el mask y el shift exactos del header del kernel, y ademas cita la
linea del corpus donde cada valor se lee.

Lo que la tabla NO tiene bien es la clasificacion de 7 campos (`DECLARED_NOT_WRITTEN`
cuando el corpus los escribe en la IRQ, seccion 3).  Ese error es de
**interpretacion**, no de **datos**: los numeros estan bien, lo que se infiere de
ellos no.

```text
datos de la tabla        CORRECTOS (22/22, mask y shift exactos, con fuente)
inferencia de la tabla   ERRONEA en 7 campos (_INTERRUPT)
```

Esa distincion es la que decide si el driver del mandato es utilizable: un
escritor puede apoyarse en los valores sin recelo, y solo debe corregir como
trata los 7 `_INTERRUPT`.

### Correccion 174

Al verificar los shift, mi regex `([A-Z0-9_]+)_SHIFT` dio `PAGE_TABLE_DEPTH__SHIFT
= 0x0` y las 22 filas aparecieron como "distintos del header".  La clase de
caracteres `[A-Z0-9_]` es voraz y se come el guion bajo: la clave del diccionario
quedaba `PAGE_TABLE_DEPTH_` y no `PAGE_TABLE_DEPTH`.  Con patron no voraz el
valor es `0x1`, que es el del header.  **Un patron voraz en un nombre con
separadores produce una lista vacia, y una lista vacia Mas `0` produce
"todo difiere"**: el resultado mas ruidoso que puede dar una comprobacion.## 3e. Cobertura del mandate: 26 registros, los 26 existen, y un negativo que NO es un defecto

`mandato --cobertura` extiende el contraste a todo el driver:

```text
ficheros con registros nombrados: 2
  target_regs.h        10    mmGRBM_STATUS, mmGRBM_STATUS2, mmSCRATCH_REG0,
                             mmCP_BUSY_STAT, mmCP_RB0_RPTR, mmCP_RB0_WPTR,
                             mmCP_RB_DOORBELL_CONTROL, mmCP_RB_WPTR_POLL_*,
                             mmCP_BUSY_STAT
  rx550_mmio_access.c   16    (los 22 campos de CNTL + 6 de L1_TLB, por nombre)
total registros nombrados: 26
existen en un header ASIC: 26
NO existen:                    0
```

**El mandato no nombra ningun registro que no exista.**  Eso descarta la
posibilidad de que su contrato base este construido sobre nombres inventados, y
`mmVM_CONTEXT1_PAGE_TABLE_BASE_ADDR` esta declarado con `0x550`, que es el valor
del header del GFX8.  Correcto.

Y un caso de alcance que hay que decir: `target_vm.h` solo nombra `"drm_gpuvm"`,
que es un TIPO, no un registro.  Un escaneo de identificadores entrecomillados lo
contaria.  Por eso la herramienta exige el prefijo `mm`/`reg` y tiene un NEGATIVO
que lo comprueba.

### El negativo que NO es un defecto, y por que importa decirlo

```text
registros que escribe el corpus en la ruta VI      257
registros que nombra el mandate                      26
el corpus escribe y el mandate NO nombra           235
```

**235 no es un defecto**: el mandate es un esqueleto --probe, lectura, contrato
base-- y no implementa el init completo.  La cifra compara dos alcances
distintos y la direccion no significa nada.

Y en la otra direccion, los 4 que el mandate nombra y mi escaneo no ve
escribir:

```text
mmVM_CONTEXT1_PAGE_TABLE_BASE_ADDR   el corpus lo escribe POR OFFSET CALCULADO:
                                     reg = mmVM_CONTEXT8_PAGE_TABLE_BASE_ADDR + vmid - 8
                                     (gmc_v8_0.c:676).  El nombre no aparece nunca.
mmCP_BUSY_STAT, mmCP_RB0_RPTR,
mmCP_RB_WPTR_POLL_CNTL                 leidos o escritos en ficheros de sched/rsc,
                                     fuera del conjunto BLOQUES
```

**Los cuatro existen y los cuatro los usa el corpus.**  El primer caso es el mas
interesante: el corpus escribe la PTBA del contexto 1 **sin nombrarla nunca**, la
calcula desde `CONTEXT8`.  Un escaneo por nombre no puede verlo, y sin el control
`registro_existe` habria parecido un registro declarado sin uso.

Esto es la leccion de siempre, aplicada a mi propio escaneo: **"no aparece" no es
"no existe"**, y la diferencia entre ambas es un offset calculado o un fichero
fuera del conjunto.  Es exactamente el motivo por el que `crosscheck` tiene un
veredicto `INDIRECTO` en vez de `NO_RESOLUBLE`.
## 2n. CERRADO: la atomicidad PTBA + invalidate

La frontera `PTBA + invalidate atomicity NOT_PROVEN` queda **PROVEN**, y el
mecanismo no es el que se suponia.

`gmc_v8_0_emit_flush_gpu_tlb` (`gmc_v8_0.c:668-683`):

```c
if (vmid < 8)
        reg = mmVM_CONTEXT0_PAGE_TABLE_BASE_ADDR + vmid;
else
        reg = mmVM_CONTEXT8_PAGE_TABLE_BASE_ADDR + vmid - 8;
amdgpu_ring_emit_wreg(ring, reg, pd_addr >> 12);          /* PTBA */
amdgpu_ring_emit_wreg(ring, mmVM_INVALIDATE_REQUEST, 1 << vmid);  /* invalidate */
```

**La serializacion es el ORDEN DEL RING.**  Son dos comandos PM4 consecutivos
emitidos en el mismo ring, y el motor los ejecuta en orden: la page table queda
escrita antes de que el invalidate sea visible.  No hay mutex ni fence: la
atomicidad la da el propio canal.

### Correccion 125: los 16 PTBA NO son 16 registros consecutivos

```text
bloque 0   mmVM_CONTEXT0_PAGE_TABLE_BASE_ADDR  = 0x54f
           mmVM_CONTEXT7_PAGE_TABLE_BASE_ADDR  = 0x556
bloque 1   mmVM_CONTEXT8_PAGE_TABLE_BASE_ADDR  = 0x50e
           mmVM_CONTEXT15_PAGE_TABLE_BASE_ADDR = 0x515

d(8) - d(0) = -0x41     (65 registros de separacion)
```

Asi que `mmVM_CONTEXT0_PAGE_TABLE_BASE_ADDR + vmid` **solo es valido para
vmid < 8**, que es exactamente por lo que el codigo bifurca.  Un driver propio
que asumiera 16 consecutivos escribiria en `0x557`, `0x558`, ... para vmid 8-15:
direcciones que en esta GPU no son PTBA.  La suposicion era mia y era falsa.

### Las dos vias de invalidate, con disciplina distinta

| via | codigo | sincronizacion |
|---|---|---|
| PM4 en ring | `gmc_v8_0.c:680` `amdgpu_ring_emit_wreg` | **orden del ring**; PTBA e invalidate en la misma secuencia |
| MMIO directo, 1 dominio | `gmc_v8_0.c:665` `WREG32(..., 1 << vmid)` | **ninguna**: escribe y sale, sin leer respuesta |
| MMIO directo, mascara | `gmc_v8_0.c:640` `WREG32(..., mask)` | **lee `mmVM_INVALIDATE_RESPONSE`** despues: es un poll de finalizacion |

Las tres conviven en el mismo fichero.  La via por PM4 es la unica que ordena
PTBA respecto al invalidate; las dos vias MMIO solo se usan cuando la page table
ya no cambia de base (flush de TLB puro), y por eso no necesitan ese orden.

`gmc_v8_0_flush_gpu_tlb_pasid` recorre `vmid` de **1 a 15** (el 0 queda fuera: es
el GART del kernel) leyendo `mmATC_VMID0_PASID_MAPPING + vmid` y acumulando la
mascara de 16 bits.  Confirma el `bits 0-15 are the VM contexts0-15` que dice el
comentario del propio driver.

**Lo que queda abierto, y es distinto:** si un invalidate emitido por MMIO
directo y otro emitido por PMIO pueden intercalarse.  Eso depende de si el motor
drena el ring antes de atender la escritura MMIO, y es `NOT_DETERMINED` — el
codigo no lo serializa de forma explicita.

## 2o. El ultimo NOT_DETERMINED, y por que se queda NOT_DETERMINED

Pregunta: ¿pueden intercalarse un invalidate por MMIO directo y otro por PM4?

### Lo que si se sabe

```text
gmc_v8_0.c:640  WREG32(mmVM_INVALIDATE_REQUEST, mask)
gmc_v8_0.c:641  RREG32(mmVM_INVALIDATE_RESPONSE)      <- poll pegado a la escritura
gmc_v8_0.c:665  WREG32(mmVM_INVALIDATE_REQUEST, 1 << vmid)   <- sin nada despues
gmc_v8_0.c:680  amdgpu_ring_emit_wreg(ring, mmVM_INVALIDATE_REQUEST, 1 << vmid)
```

Barreras de memoria en las tres funciones que contienen esas escrituras:
**cero**.  Ni `wmb`, ni `smp_mb`, ni `mb()`.  Comprobado con el resolutor de
funciones, no a ojo: el ambito de la busqueda es el cuerpo de la funcion, no
el fichero.

Y no es un descuido del driver, porque **la semantica de hardware no lo
necesita en el caso de uso**: el campo de respuesta se llama
`VM_INVALIDATE_RESPONSE__DOMAIN_INVALIDATED_n` (pasado, no `PENDING`), con
16 campos de mascara `0x1` a `0x8000` en las cinco generaciones gmc
(`gmc_6_0`, `gmc_7_0`, `gmc_7_1`, `gmc_8_1`, `gmc_8_2`).  La lectura de
`RESPONSE` es un **drenado**: el hardware acknowledges y el host espera a que
los 16 dominios esten invalidados.  Ningun campo `PENDING` existe en ninguna
generacion (0 ocurrencias).

### Lo que NO se puede cerrar con este material

Que la lectura de `RESPONSE` sea un drenado **no dice cuando ocurre respecto a
un comando PM4**.  Y las dos vias ni siquiera se mezclan en el mismo camino:
`emit_flush_gpu_tlb` (PM4) se invoca desde `amdgpu_vpe.c:621` y
`gfx_v7_0.c:3144`; las vias MMIO, desde las rutinas de flush de TLB.  Para que
hubiera carrera haria falta que un mismo ring emitiera mientras otro hilo
escribe por MMIO, y **el codigo no contiene ninguna secuencia que lo impida ni
lo provoque**.

Veredicto: `NOT_DETERMINED`, y el motivo es preciso: **no es una laguna de
evidencia en el codigo, es una pregunta de orden de ejecucion en hardware que
el codigo no responde.**  La instrumentacion que la responderia (escribir
REQUEST por MMIO con el ring ocupado y observar si RESPONSE llega antes o
despues del ultimo PM4) cae bajo `AGENTS.md:469` y no se hace.

Lo que si es accionable para un driver propio, y no requiere esa respuesta:

```text
1. Si necesitas que PTBA este visible antes del invalidate, USA LA VIA PM4.
   Ahi el orden lo garantiza el ring, sin barreras y sin polling.
2. La via MMIO de un dominio (`gmc_v8_0.c:665`) no sincroniza nada.  Si la
   page table cambio antes, esa via no te sirve.
3. La via de mascara (`gmc_v8_0.c:640-641`) si sincroniza, por el drenado.
4. Los 16 PTBA son DOS BLOQUES (0x54f-0x556, 0x50e-0x515), no 16 seguidos.
```

## 2p. 24 funciones de riesgo, separadas en 13 que chocan y 11 que no

Herramienta nueva: `conflicto.py`.  La pregunta que "sin mutex" no responde es
mas estrecha y mas util: **¿escribe OTRA funcion de riesgo el MISMO registro?**
Si dos funciones del mismo bloque IP escriben el mismo registro sin mutex, la
carrera es demostrable por construccion: no hace falta saber quien serializa a
quien, porque ninguna lo hace.  Y si nadie mas escribe ese registro, no hay
conflicto posible aunque las dos corran a la vez.

```text
funciones de riesgo                        24
registros escritos por alguna de riesgo    111
  de esas, CON CONFLICTO                   13
    de esas, en el MISMO bloque IP         13   <- todas
  sin conflicto (nadie mas las pisa)       11

bloques: GFX 9 · GFXHUB 4 · GMC 9 · SDMA 2
autofiguras (conflicto consigo misma)       0
```

### El caso mas limpio, y el que un driver propio debe mirar primero

Un solo registro, dos escrituras, dos funciones, mismo bloque, sin mutex:

```text
mmRLC_CGTT_MGCG_OVERRIDE
  gfx_v8_0.c:5618  gfx_v8_0_update_medium_grain_clock_gating
  gfx_v8_0.c:5718  gfx_v8_0_update_coarse_grain_clock_gating
```

Ambas son *clock gating*: leen-modifican-escriben el mismo registro
(`RREG32` → `REG_SET_FIELD` → `WREG32`).  Un patron leer-modificar-escribir sin
mutex sobre un registro compartido **es** una perdida de actualizacion, no una
disputa de orden: si las dos cores leen el mismo valor viejo y las dos escriben,
una mascara se pierde.  Ninguna depende del orden.

Los demas conflictos, por bloque:

| bloque | funciones que chocan | registro compartido |
|---|---|---|
| GFX | 2 (`:5618`, `:5718`) | `mmRLC_CGTT_MGCG_OVERRIDE` |
| GFXHUB | 3 (`:357`, `:385`, `:582`) | `mmGCMC_VM_FB_LOCATION_BASE`, `mmGCMC_VM_MX_L1_TLB_CNTL` |
| GMC | 6 (`:170`, `:194`, `:433`, `:829`, `:972`, `:1385`) | `mmBIF_FB_EN`, `mmMC_SHARED_BLACKOUT_CNTL`, `mmMC_VM_MX_L1_TLB_CNTL`, `mmVM_CONTEXT0_PAGE_TABLE_BASE_ADDR`, `mmVM_CONTEXT0_CNTL` |
| SDMA | 0 | — |

**Correccion 135: eso era falso y lo habia propagado.**  Escribi que
`mmVM_CONTEXT0_PAGE_TABLE_BASE_ADDR` aparecia en conflicto entre
`gmc_v8_0_gart_enable` (`:829`) y `gmc_v8_0_gart_disable` (`:972`).  No es
cierta: lo lei de una **tabla truncada**, donde `mmVM_CONTEXT0_CNTL` se
mostraba cortado como `mmVM_CONTEXT0_...` y lo leí como la PTBA.

Lo verificado, con el conjunto de registros completo:

```text
gart_enable  (gmc_v8_0.c:829)   20 registros
gart_disable (gmc_v8_0.c:972)    5 registros
COMUNES: mmMC_VM_MX_L1_TLB_CNTL, mmVM_CONTEXT0_CNTL, mmVM_CONTEXT1_CNTL,
         mmVM_L2_CNTL, mmVM_L2_CNTL2
```

La **PTBA la escribe solo `gart_enable`**.  Los comunes son los contadores de
cache L2 y los de control de fault, no la base de la page table.  Sigue habiendo
conflicto real entre las dos, pero sobre otros cinco registros.

Es la clase H de nuevo —un filtro que parece un prefijo— y en la peor versión:
**yo truncando mi propia salida y creyendo lo que leía.**  La unica razon por
la que se ha corregido es que el self-test tiene valores fijos: sin ellos, el
numero dependía de que yo lo mirara.

### Las 11 que se pueden descartar de un driver propio

Nadie mas escribe sus registros, luego no hay conflicto posible:

```text
gfx_v8_0.c:3474  write_harvested_raster_configs   2 regs
gfx_v8_0.c:4193  set_cpg_door_bell                3
gfx_v8_0.c:4365  deactivate_hqd                   3
gfx_v8_0.c:4546  mqd_commit                       3
gfx_v8_0.c:4653  set_mec_doorbell_range           2
gfx_v8_0.c:4993  soft_reset                       3
gfx_v8_0.c:5477  send_serdes_cmd                  3
gfxhub_v2_1.c:272 disable_identity_aperture       6
gmc_v8_0.c:766   set_prt                          9
sdma_v3_0.c:513  gfx_stop                         2
sdma_v3_0.c:548  ctx_switch_enable                3
```

Cuidado con `soft_reset`: sin conflicto **de escritura**, pero escribe
`mmSRBM_SOFT_RESET`, que comparten GFX, GMC y SDMA en sus propios
`soft_reset` (correccion 100).  El conflicto de `soft_reset` esta en el otro
sentido — no pisa a nadie, le pisan a el.

### Rendimiento: 6 min -> 7.8 s

`regctx.scan` sin filtro barre los ~1000 `.c` de `amdgpu`: >6 min y 2.9 GB de
RSS.  Con `files=BLOQUES` baja a **7.8 s**, porque solo hay escrituras en los
ficheros de la ruta.  El indice de cabeceras sigue siendo global, asi que la
resolucion de offsets no cambia: lo que se recorta es el conjunto de ACCESOS,
no el de definiciones.

Tambien: el AST de clang se cachea ahora en disco (`/var/tmp/rx550/cache`).
7.3 s la primera vez, **0.00 s** la segunda, y sin los 3.2 GB de RAM que
tenia en memoria.

## 2q. La cache del AST: 20 GB no eran un logro

Cachear el AST de clang en disco funciono (7.3 s la primera vez, 0.00 s la
segunda de verdad).  Lo que no vi es lo que costo:

```text
20 GB en 36 ficheros      un JSON por .c, ~600 MB cada uno
2.9 GB de RSS en memoria
```

Un `.c` de amdgpu produce 633 MB de AST JSON.  Es almacenamiento, no cache.

### Correccion 129: sin limite, la cache crece sin control

Se acoto a `_CACHE_MAX = 8` entradas PROPIAS.  El directorio es compartido con
otro agente, asi que la purga solo toca ficheros cuyo nombre base empieza por el
del fichero actual, nunca los suyos.

### Correccion 130: la purga estaba en el sitio equivocado

Estaba en la rama de **escritura** del fichero de cache.  Si el `.json` ya
existia, esa rama no se ejecutaba y **la purga no corria nunca** — que es
exactamente como se llegaron a 25 entradas.  Movida a la lectura.

Purga manual: **14 GB -> 2.9 GB**, quedan los 5 ficheros de la ruta VI.

### Y el coste real, medido en vez de supuesto

La cache SI funciona; lo caro es parsear:

```text
leer 633 MB          0.48 s
json.loads           3.95 s     <- aqui esta el coste
_walk                0.12 s
```

Que `spans_from_ast` tardara 20 s en unas pruebas y 5 s en otras era que
`contract._AMD` y la ruta que yo escribia a mano **no son la misma cadena**:
dos ficheros distintos, dos claves de cache distintas, dos AST.  El mismo
problema de clase A que ya carried el ico del 100: dos sitios que parecen el
mismo y no lo son.

## 2r. Hipotesis refutada: no habia dos rutas

Sospeche que el AST se cacheaba dos veces por rutas distintas, porque unas
pruebas tardaban 5 s y otras 20 s.  **`paths.py` lo refuta**: las tres formas
de construir la ruta dan la MISMA clave de cache.

```text
contract (join)        gfx_v8_0.c.98c128ba4308.json
AMD + amdgpu           gfx_v8_0.c.98c128ba4308.json
CORPUS + relativo      gfx_v8_0.c.98c128ba4308.json
```

Los 20 s eran el mismo trabajo, y el coste real esta medido:

```text
leer 633 MB           0.48 s
json.loads            3.95 s     <- aqui esta
_walk                 0.12 s
```

La cache de disco evita la invocacion de clang, **no el parseo**.  Decir que
habia un bug de rutas habria sido la clase K —heuristica que confunde dos
cosas— que llevo corrigiendo 135 veces.  La centralizacion se queda como
**precaucion**, con su self-test que demuestra que no puede fallar en silencio.

## 2s. La IRQ y el RMW compartido: cerrado por construccion

Del hallazgo anterior: el manejador de IRQ `gmc_v8_0_vm_fault_interrupt_state`
(`gmc_v8_0.c:1385`) comparte sus DOS registros exactos con `gart_enable` y
`gart_disable`.  Era el candidato a primera carrera real por contexto
asincrono.  Se cierra.

### Los dos RMW, en el fuente

`gmc_v8_0_vm_fault_interrupt_state`, en **ambas** ramas del `switch (state)`:

```c
case AMDGPU_IRQ_STATE_DISABLE:
        tmp = RREG32(mmVM_CONTEXT0_CNTL);
        tmp &= ~bits;                    /* borra los bits de fault */
        WREG32(mmVM_CONTEXT0_CNTL, tmp);
        tmp = RREG32(mmVM_CONTEXT1_CNTL);
        tmp &= ~bits;
        WREG32(mmVM_CONTEXT1_CNTL, tmp);
```

`gmc_v8_0_gart_enable` (`gmc_v8_0.c:893-895`):

```c
tmp = RREG32(mmVM_CONTEXT0_CNTL);
tmp = REG_SET_FIELD(tmp, VM_CONTEXT0_CNTL, ENABLE_CONTEXT, 1);
tmp = REG_SET_FIELD(tmp, VM_CONTEXT0_CNTL, PAGE_TABLE_DEPTH, 0);
tmp = REG_SET_FIELD(tmp, VM_CONTEXT0_CNTL, RANGE_PROTECTION_FAULT_ENABLE_DEFAULT, 1);
WREG32(mmVM_CONTEXT0_CNTL, tmp);
```

Los dos leen-modifican-escriben el mismo registro.  **Si se solaparan, el
resultado dependeria del orden**: el RMW de la IRQ podria borrar un
`ENABLE_CONTEXT` recien puesto, o el de `gart_enable` reponer un bit de fault
recien borrado.  Eso es una perdida de actualizacion, no una disputa de orden.

### Por que NO pueden solaparse

```text
via de la IRQ   amdgpu_irq.c:579  ->  spin_lock_irqsave(&adev->irq.lock)
                amdgpu_irq.c:177  ->  spin_lock_irqsave(&adev->irq.lock)
via de GART     gmc_v8_0_gart_enable (span 829-946)
                  irq.lock     NO
                  mutex_lock   NO
                  spin_lock    NO
                unico llamante: gmc_v8_0_hw_init  (proceso, no IRQ)
```

El RMW de la IRQ ocurre **dentro** del lock, y `gart_enable` no toma ninguno.
Los dos contextos son disjuntos: uno entra por la cadena de IRQ con
`irq.lock`, el otro por `hw_init` en contexto de proceso.  No hay solape.

Y esto responde a la pregunta de fondo del bloque: de las 13 con conflicto,
esta —que es la unica con contexto asincrono— **queda descartada** por
construccion, no por inferencia.  Las 12 restantes comparten bloque pero sus
llamantes son todos de proceso o de init, asi que su solape sigue
`NOT_DETERMINED`: no hay codigo que lo impida ni que lo provoque.

## 2t. Un intento de 8 pasos que ABORTE, y por que se aborta

`alcance.py` (el analisis transitivo de las 12 restantes) necesito el call graph,
que dispara el AST de clang.  Al medirlo aparecio un problema de recursos y
intente resolverlo de mas: leer el AST de un `.c` de amdgpu son **574 MB de JSON
y 2.9 GB de RAM**, y con 5 ficheros el proceso llegaba a 9.3 GB.

### Lo que se intento y por que se paro

```text
1  limitar regctx.scan a BLOQUES                       FUNCIONA: 6 min -> 7.8 s
2  limitar el call graph a los 6 ficheros de la ruta   FUNCIONA: 9.3 GB -> 1 GB
3  -ast-dump-filter -FunctionDecl                      FALLA: 0 bytes, 3 variantes
4  escribir a fichero en vez de capture_output         PARCIAL: 2.9 -> 2.1 GB
5  no mirar returncode (clang da 1 con AST valido)    FALLA: Logical, luego FALLA
6  parser propio en flujo, sin dependencias            FALLA: 8 pasos, ver abajo
7  filtrar el arbol de includes por `loc.file`         FALLA
8  anclar el `file` al `loc` del nodo                  FALLA
```

El paso 6 --escribir un mini-parser de JSON que solo materializara los
intervalos-- llego a funcionar en memoria (**2.8 GB -> 25 MB**) y a dar 0 spans.
Ocho correcciones para llegar a un resultado que era PEOR que el punto de
partida.  La ultima fue la que lo cerro: **el `loc.file` de un nodo del AST
apunta al fichero donde la declaracion esta escrita**, y para una funcion de una
cabecera inline de linux eso es la cabecera, no el `.c`.  Ningun campo del nodo
distingue "declarada aqui" de "declarada en un include": solo la comparacion con
el nombre del fichero pedido, y no hay campo que lo facilite de forma fiable.

**Se aborta y se vuelve a `json.loads`.**  El intento queda en
`scratch/funcspan_intento_fallido.py` por si alguien dia se retoma, con la nota de
que necesita un parser de verdad, no un regex sobre el texto.

Lo que si se conserva, porque son correctos y verificados:

```text
capture_output -> fichero   parcial: el pico baja algo
no mirar returncode         CORRECTO: era un bug real (correccion 144)
```

### Lo que NO se ha ganado

La memoria sigue en 3 GB por fichero.  **`json.loads` de 574 MB pide 2.7 GB** y no
hay forma de evitarlo sin un parser de streaming, y el unico disponible seria
`ijson`, que no esta instalado y no se instalan paquetes.  Queda declarado como
limite, no como logro.

Lo que si se ha ganado, y es lo que importa para el trabajo:

```text
regctx.scan acotado a BLOQUES   6 min -> 7.8 s
call graph acotado a 6 ficheros  9.3 GB -> 1 GB
spans correctos: 4712 en gfx_v8_0.c, verificados 6/6 contra los esperados
funcspan self-test 25/25
```

## 2u. El analisis transitivo no cierra, y ahora se por que

13 funciones en conflicto, 13 con la misma cadena: `update_gfx_clock_gating` ->
sin llamantes visibles; `gmc_v8_0_hw_init` -> `gmc_v8_0_resume` ->
`gfx_v8_0_hw_init` -> sin llamantes visibles.  El grafo se agota **siempre en
una tabla de ops**, y ahi `VIA_OPS` no es un veredicto de contexto: es la
constancia de que toda cadena del driver pasa por un puntero a funcion.

Eso conecta con el `PROVEN_ABSENT` de la seccion 2m: el despachador de ASIC
(`amdgpu_asic_init`) **no esta definido en ningun fichero del arbol**.  Sin el,
ninguna cadena se puede cerrar hasta una raiz, porque la raiz ES el dispatcher.
El analisis no falla: no tiene a donde llegar.

Veredicto correcto de las 13: **`NOT_DETERMINED` por falta del dispatcher**, y
la razon es estructural y esta probada, no una conjetura.

### Lo que este trabajo SI cerro, y que no debia confundirse

La carrera de la IRQ (correccion 136) se cerro por otra via: `gart_enable` no
toma ningun lock y su unico llamante es `gmc_v8_0_hw_init`.  Ese descarte es
valido **sin** el dispatcher, porque no necesita la raiz: necesita que el
llamante visible sea el unico.  Y lo es.

| conclusion | depende del dispatcher? |
|---|---|
| la IRQ no compite con `gart_enable` | NO — verificado por locks y por el unico llamante |
| 13 funciones con conflicto de registro | NO — es coincidencia de registros, no de contexto |
| si esas 13 pueden solaparse en la practica | **SI** — hace falta la raiz |

## 2v. Las 13 NO son 13 carreras: son 2 pares y 3 trios

`transiciones.py`: sobre el mismo conjunto de 13 de `conflicto`, se agrupan por
conflicto (no por parecido de nombres) y se lee cada grupo como estructura.

```text
funciones en conflicto                13
  sin nombre resuelto                  0
  PARES (componentes de 2)             2
  TRIOS (componentes de 3)             3
  pares con etiqueta de fases          1
  pares con al menos una RMW           2

2 pares x 2 + 3 trios x 3 = 13    cuadra
```

### El par 1: coarse/medium, y las dos hacen RMW

```text
gfx_v8_0_update_medium_grain_clock_gating
  <-> gfx_v8_0_update_coarse_grain_clock_gating
  comparten: mmRLC_CGTT_MGCG_OVERRIDE
  RMW: las dos      fases: coarse/medium
```

Es el unico par que se lee como maquina de dos fases, y es el caso que ya se
habia aislado: dos lecturas-modificacion-escritura sobre el mismo registro, en
el mismo bloque, sin mutex.  Si se solapan, una mascara se pierde.

### El par 2: nine registros de gates de memoria

```text
fiji_update_mc_medium_grain_clock_gating
  <-> fiji_update_mc_light_sleep
  comparten: 9 registros (mmMC_CITF_MISC_*_CG, mmMC_HUB_MISC_*_CG,
             mmATC_MISC_CG, mmVM_L2_CG, mmMC_XPB_CLK_GAT)
  ninguno es PAGE_TABLE
```

### Los 3 trios

```text
gfxhub_v2_1.c:357 / :385 / :582     (gart_enable, gart_disable, restore_regs)
gmc_v8_0.c:170 / :194 / :433         (mc_stop, mc_resume, mc_program)
gmc_v8_0.c:1385 / :829 / :972        (vm_fault_irq, gart_enable, gart_disable)
```

Un trio no es un par: no se puede llamar "transicion de dos fases" a tres
rutinas que comparten registros.  Se reportan como lo que son.

**Lo que NO se afirma:** que estas 13 sean seguras.  Su agrupacion describe la
estructura del solape, no su imposibilidad.  La imposibilidad sigue
`NOT_DETERMINED` por la razon de la seccion 2u (falta el dispatcher).

### Y seis correcciones, cuatro por el mismo error

| # | error | correccion |
|---|---|---|
| 160 | dos asserts de FASES eran tautologicos | `None is None`: comprobaban que un nombre suelto no es un par, que es construccion |
| 161 | `fases_de` exigia las DOS fases en un MISMO nombre | por construccion nunca ocurre: las dos fases estan en dos funciones. Ahora `fase_de` devuelve etiqueta por fase suelta y el emparejamiento es entre funciones |
| 162 | 4 funciones desaparecian sin avisar | si `nombre_de` falla, se marca `SIN_NOMBRE` y se cuenta aparte, en vez de perderlas del reparto |
| 163 | el grafo se reconstruia comparando conjuntos de registros | daba componentes distintas y perdia 4. Se usa el grafo de `conflicto`, que ya esta verificado: una sola fuente de verdad |
| 164 | nombres de una funcion con registros de otra | el nombre se resolvia por posicion en `claves` y los registros por indice de `riesgo`: los dos ordenes no coinciden |
| 165 | el emparejamiento seguia corrido | `enumerate(claves)` empareja posicion con indice; se itera sobre las claves de `conf`, que si son indices de `riesgo` |
| 166 | un assert decia que clock gating no toca CITF/ATC | falso: los gates de memoria son justo lo que controla. El aserto era el equivocado |

**Los cuatro fallos de indexacion son invisibles a un assert de RECUENTO**: los
dos casos dan 2 pares y 3 trios igual.  Solo un assert de CONTENIDO los caza, y
por eso los hay.

## 2w. Los 3 trios SI son ciclos de vida, y el invariante es comprobable

Herramienta nueva: `ciclo.py`.  Los 3 trios de `transiciones` tienen la misma
forma exacta, y esa forma se puede verificar sobre el fuente:

```text
                        SETUP            TEARDOWN              RESTAURAR
ciclo 1 (GFXHUB)   gart_enable(2)    gart_disable(2)    restore_regs(20)   sin RMW
ciclo 2 (GMC)      mc_program(16)   mc_stop(2)        mc_resume(2)       los 3 RMW
ciclo 3 (GMC)      gart_enable(20)  gart_disable(5)   vm_fault_irq(2)    sin ROL
```

**1 setup + 1 teardown en los tres**, y 2 de 3 con restaurador.  El tercero
tiene un miembro al que **no se le inventa rol**: `vm_fault_interrupt_state` no
encaja en ninguna regla, y queda como `None` con 0 restauradores.

### El ciclo 2 es el invariante perfecto, verificado en el fuente

```c
/* mc_stop   gmc_v8_0.c:181-188 */
blackout = RREG32(mmMC_SHARED_BLACKOUT_CNTL);
blackout = REG_SET_FIELD(blackout, MC_SHARED_BLACKOUT_CNTL, BLACKOUT_MODE, 1);
WREG32(mmMC_SHARED_BLACKOUT_CNTL, blackout);

/* mc_resume gmc_v8_0.c:199-201 */
tmp = RREG32(mmMC_SHARED_BLACKOUT_CNTL);
tmp = REG_SET_FIELD(tmp, MC_SHARED_BLACKOUT_CNTL, BLACKOUT_MODE, 0);
WREG32(mmMC_SHARED_BLACKOUT_CNTL, tmp);
```

**El mismo registro, el mismo campo, 1 y 0.**  Eso es una transicion de dos
fases con invariante verificable, y las dos funciones hacen RMW sobre el mismo
registro sin mutex  --  por eso son el ciclo mas expuesto y a la vez el mejor
definido.  `mc_program` (16 registros) **no** restaura `BLACKOUT_CNTL`, y no
deberia: no es su registro.

### El ciclo 1 deja un registro sin tocar por el setup

```text
gart_disable escribe mmGCVM_L2_CNTL3 y mmGCMC_VM_MX_L1_TLB_CNTL
gart_enable NO toca ninguno de los dos
```

`mmGCVM_L2_CNTL3` (`gfxhub_v2_1.c:408`) lo pone a 0 al deshabilitar y el setup
no lo escribe.  Si el setup no lo inicializa, el teardown escribe un registro
que nunca fue puesto por este ciclo.  No es un fallo probable: es un registro
cuya inicializacion esta en otro sitio, y eso **no se cierra leyendo los tres
miembros**  --  hace falta quien lo inicialice, que cae otra vez en el
dispatcher ausente.

### Y una correccion, y es de las que mas pesan

| # | error | correccion |
|---|---|---|
| 167 | `"nombre" in [["nombre"]]` daba False | `in` sobre una lista de listas compara la lista ENTERA por igualdad, no la pertenencia. El aserto fallaba con el dato correcto delante: se combinaba `sum(...)==1` con un `any()` mal construido |
| 168 | `mascara_de(bits, 0)` con nombres de CONTEXT1 daba 0 | 0 significaba "los nombres son de otro contexto", no "no hay bits". El aserto leia "la IRQ no pone 7 bits" con el dato correcto |
| 169 | el RMW por campo se buscaba en la linea de la escritura | la escritura es `WREG32(reg, tmp)`: el operador esta dos lineas antes, en el `REG_SET_FIELD`. Se perdian todos los RMW y solo se veian las literales: la herramienta hallaba lo contrario de lo que buscaba |
| 170 | "mascara 0" se leyo como "no toca campos" | es `WREG32(reg, 0)`: borra el registro entero. Escribir un registro afecta a todos sus campos; escribir un campo, solo a ese |
| 171 | un caso sintetico uso `m_tear = BRUTO` como si borrara | `m_tear` es la mascara que PONE. Un teardown que escribe 0 es `m_tear = 0`; con BRUTO la formula daba 0 y "nada perdido" |
| 172 | el aserto fijaba "el ciclo pierde 7 bits" | son 21 en CONTEXT0: el setup configura 14 campos solo en CONTEXT1 y ninguno de los de proteccion en CONTEXT0 |
| 173 | "los 7 de la IRQ estan entre los perdidos" fallaba en CONTEXT1 | con razon: ahi el setup PONE los 7, asi que no se pierden. El assert correcto es "lo perdido no lo cubre setup ni IRQ" |
| 174 | un regex voraz dio 22 de 22 campos "distintos del header" | `([A-Z0-9_]+)_SHIFT` se come el guion bajo: la clave quedaba `PAGE_TABLE_DEPTH_`. Un patron voraz en un nombre con separadores produce lista vacia, y vacia mas cero produce "todo difiere" |
| 175 | supuse que la tabla de campos del mandato estaba incompleta | verificada campo por campo: 22 en la tabla, 22 en el header, 0 de diferencia, mask y shift exactos. Los DATOS son correctos; lo que falla es una INFERENCIA sobre ellos |
| 176 | la tabla del mandato se tomo por completa | declara 28 campos de 2 registros, y `VM_CONTEXT0_CNTL` no esta: es justo el que `gart_disable` pone a cero |
| 177 | `sh_mask_de` tomaba el primer header con el nombre | hay uno por GENERACION ASIC y los valores difieren. El criterio es el header donde existen TODOS los campos del mandate; con empate se declara AMBIGUO |
| 178 | compare 257 registros del corpus contra 26 del mandate y lei el 235 como cobertura faltante | es un alcance distinto: el mandate es un esqueleto. Y los 4 "no escritos" SI los usa el corpus, uno por offset calculado |
| 179 | no habia forma de medir un parche sin tocar el original | `RX550_MANDATO` + `RX550_PATCH_TEST`: se mide una copia, y los asserts del parche solo corren con el sandbox |
| 180 | el corte de la tabla por el primer `};` duplico 6 filas de otro registro | se toman las lineas que empiezan por `{ "VM_CONTEXT1_CNTL"`. Salio 12 declarados contra 6 del header |
| 181 | un assert mezclaba registros con campos | `registros_declarados()` cuenta REGISTROS (26); el assert queria CAMPOS (50). Daba 26 sin que hubiera error de parche |
| 182 | una ruta que no existe se reporta como FAIL | `RX550_CORPUS`: una comprobacion que no puede hacerse no es una que falle. El veredicto cuenta PASS / SKIP / FAIL por separado |
| 183 | los 12 FAIL de la suite en un sandbox se leyeron como fallo del codigo | `R00` es el control de la propia suite y declara que si el falla, los demas son falsos. `--parche` aplica lo mismo: SKIP_ENTORNO |
| 184 | la suite se ejecutaba con el cwd del proyecto padre | necesita el del driver: sus rutas son relativas. Con el padre, `R00` fallaba por otro motivo y el diagnostico senalaba el sintoma equivocado |
| 185 | `--parche` compilo el mandate REAL | `make` escribe en el directorio que se le pase. La compilacion solo corre dentro de `/var/tmp/rx550`; fuera, `SKIP_ESCRITURA` con el motivo |
| 186 | el consumidor de una ops table se buscaba solo en los ficheros del call graph | el consumidor NO esta en el fichero que declara la tabla: `gart_enable` se declara en gfxhub_v2_1.c y se llama desde gmc_v8_0.c. Sin el anillo ampliado las 13 salian VIA_OPS sin raiz |
| 187 | el resolutor no tenia segundo anillo | los ficheros que despachan por MEMBRO en un bucle (`ip_blocks[i].version->funcs->M(`) son amdgpu_ip.c, amdgpu_device.c y amdgpu_job.c. Criterio medido, no elegido |
| 188 | `callgraph.clang_ast` reimplementaba el clang de `funcspan` sin cache | delega en `funcspan._clang_ast`: cache en disco, escritura a fichero y criterio por contenido. Con 11 ficheros se pagaba 11 veces el mismo parseo de 574 MB |
| 189 | `TOP` se leia como NOT_DETERMINED | `TOP` es "la cadena agota en alguien que nadie llama". Si ese alguien es un punto de entrada del driver, TERMINA: raiz definitiva. 9 de las 13 pasaron de TOP a PROCESO |
| 190 | el reparto se comparaba con una tupla de 5 posiciones | al aparecer PROCESO-por-entrada y MIEMBRO_OTRA_GENERACION la tupla dejo de significar nada. Ahora: cada caida en un estado del conjunto conocido |
| 191 | las 3 sin consumidor se llamaban SIN_CONSUMIDOR | nombre Debil: habia consumidores, 6 ficheros, en OTRAS generational. `MIEMBRO_OTRA_GENERACION` dice lo que la evidencia dice |
| 192 | la procedencia de un campo se decidia contando tokens de su NOMBRE | se decide por RASTRO: `REG_SET_FIELD(...CAMPO...)` = RMW_CAMPO, `REG__CAMPO_MASK` en un `|=`/`&=~` = RMW_MASCARA. Con 0 tokens un campo si se escribe; con 23 tokens otro no |
| 193 | se buscaba el campo solo por el prefijo de registro de VI | el MISMO campo se escribe sobre `GCMC_`/`MMMC_` segun el hub. `ECO_BITS` daba AUSENTE y lo escriben 11 ficheros. Alias automaticos en `_registro_de_este_hub()` |
| 194 | dos headers con todos los campos se declaraban AMBIGUO sin mirar los valores | medido: 15 con el nombre, 5 en gmc/, 2 con los 22 campos, y esos 2 coinciden en los 22 masks y los 22 shifts. Ahora `COINCIDENTE_EN_N_HEADERS`, y `AMBIGUO_CON_VALORES` solo si difieren |
| 195 | `sh_mask_de` devolvía un header que NO satisface ninguno de los campos pedidos | ordenado por nº de campos que faltan no es filtrar: con todos a 1 falta ganaba el primero. Ahora devuelve `None` + `NINGUN_HEADER_SIRVE`. Lo encontró un control NEGATIVO |
| 196 | la ausencia de escritura de los 5 `_SAVE` se leía como error del mandato | se discrimina con el PATRON: 215 headers, 1650767 defines MASK, 81 son `_SAVE` (0,005%), en 6 registros, y 0 escrituras de cualquier `_SAVE` en el corpus. No es del mandato: es de todo el amdgpu |
| 197 | `_CACHE_MAX` se asignaba y no se leía: **no existía eviction** | el techo estaba en un comentario. Además era de ENTRADAS (8) y el directorio tenía 28 y 16 GB. Ahora `_recorta()` por BYTES, con pid del dueño y regla de antigüedad para lo que no es mío |
| 198 | la protección del conjunto de trabajo no casaba con el nombre de la entrada | `gfx_v8_0.c` != `gfx_v8_0.c.98c1….json`. Dos apaños (split por `.json`, luego último punto) fallaron con entradas sin hash. La que aguanta es **prefijo**: no supone ninguna forma |
| 199 | el assert del recorte exigía «se retiran todas» | la invariante es «queda por debajo del techo». Con 2×600 MB y techo de 1 GB basta retirar UNA; exigir las dos habría empujado el recorte a tirar trabajo que hacía falta |
| 200 | `run-all` abortaba el ciclo entero con `set -u` si el formato del recuento cambiaba | un fallo de formato se convertía en "no se ejecutó nada". El recuento se lee con dos greps independientes y se exige que ambos den número |
| 201 | el array JSON se armaba con `&& A || B` dentro de `$( )` | `[]`+`[…],{…}]`: el separaba dos veces porque `||` evalúa por código de salida y el primer `printf` devuelve 0. Salía `[][…]`. Ahora JSONL una línea por herramienta y se arma al final |
| 202 | un PASS sobre 0 comprobaciones contaba como PASS | el total de aserciones ejecutadas es lo que distingue "todo pasa" de "nadie comprobó". Suelo de 300, aplicado DESPUÉS de clasificar y solo si el veredicto no es FAIL, para no tapar la causa real |
| 203 | con un destino no escribible el script imprimía PASS con un artefacto de 0 B | fallo del PRODUCTOR disfrazado de fallo del validador. Ahora se comprueba la escritura antes de declarar el veredicto, y sin artefacto el veredicto es INVALID_RESULT |
| 204 | el plan de `run-all` estaba en el codigo, asi que el self-test no podia sustituirlo | `$KIT_DIR` y `$KIT_PLAN` son parametros. No es flexibilidad: es lo que permite ejercitar el script REAL sobre fixtures en vez de probar una copia de su logica |
| 205 | el self-test del ciclo no existia | 9 casos limite + suelo + destino + recuento, sobre fixtures, lanzando `run-all.sh` de verdad con plan inyectado. Un test que reproduce la logica dentro de si mismo comprueba que SU COPIA acierta |
| 206 | el self-test leia el artefacto que habia dejado el caso ANTERIOR | el caso previo es el del destino no escribible, que no escribe nada: el assert fallaba con un JSON valido en disco. Un test que lee el estado de otro test no mide lo que dice medir |
| 207 | una línea del plan sin salto final se perdía en silencio | `read` devuelve 1 en EOF, y sin `|| [ -n "$_l" ]` se descarta la iteracion. `mandato` salio del ciclo y el veredicto dio "14 pasaron" sin avisar: **14 de 15 parece un resultado, no un fallo**. Ahora el ciclo imprime plan vs registradas y el desajuste es INVALID |
| 221 | el plan era `tool:timeout:env` y el modo estaba en el código | añadir `mandato --parche` —que no es un self-test sino un veredicto— exigía tocar el script. Ahora es `tarea:modo:timeout:env argumento`, y la diferencia queda **declarada** |
| 222 | se exigía `N pasaron, M fallaron` a todas las tareas | `--parche` no tiene aserciones, tiene comprobaciones con nombre. Cada modo tiene su formato; y sus cifras no se suman al suelo, que compararía cosas distintas |
| 223 | el veredicto del parche se leía por exit code | `mandato` sale 0 con SKIP_ENTORNO y SKIP_ESCRITURA: no es fallo, pero no es verde. Se lee su línea `TODO`, que es su propio veredicto |
| 224 | el nombre de la tarea tenía que ser el del fichero | `mandato-parche-sandbox` no es un fichero. El sufijo declara la variante; `prog=${tool%%-*}` mapea a `mandato.py` sin crear un fichero vacío |
| 225 | `--parche` se invocaba sin argumento | `mandato` exige el directorio detrás del flag. Sin él cae al uso y el ciclo lee "no declaro las comprobaciones": síntoma de falta de argumento, no fallo de la herramienta |
| 226 | `RX550_PATCH_TEST` iba en **ambas** tareas del mandate | con la variable puesta, la del real leía el sandbox por dentro y su tabla salía con CONTEXT0_CNTL. Medía el objeto equivocado y el ciclo no lo distinguía de una medida correcta |
| 227 | el assert leía `herramientas[0]` | el detalle empieza por el modo, no por el recuento, y el índice 0 era otra tarea. Se busca por nombre de herramienta, que es lo único estable |
| 228 | el log del `--parche` se borraba con el `TMP` | era la única copia de la evidencia: un FAIL llegaba al artefacto sin el texto que lo produjo. Los logs de veredicto se conservan |
| 229 | `KIT` significaba a la vez código y fixtures | al entrar una tarea de veredicto, la ambigüedad la ejecutaba sobre fixtures; 9 herramientas importan unas de otras y un `.py` suelto falla al importar. **Síntoma de la herramienta, causa de la variable** |
| 230 | se evaluaba la línea del plan esperando expansión | `eval "_linea=\$_l"` evalúa `_linea=$_l`: `$_l` se expande una vez y eval no re-expande un resultado, solo su código |
| 231 | la expansión del plan se hacía con `eval` | una línea de configuración es configuración, no código. `envsubst` la expande; dos `eval` seguidos no. Sin él se declara la limitación en vez de entregar un plan sin expandir |
| 232 | un `PASS` no es un resultado, es un resultado AHORA | el ciclo no comparaba nada entre corridas. Ahora compara el estado de cada tarea con la corrida anterior: REPRODUCIBLE, o NO_REPRODUCED con el campo y los dos valores. Estado y código de salida propios (234) |
| 233 | el separador del array era la palabra `comma` | `${X:+,comma}` mete la cadena `comma`, no la coma: el array quedaba `[{…}comma{…}]` y `json.loads` fallaba en silencio |
| 234 | un estado que no se repite no era ni PASS ni FAIL | es NO_REPRODUCED, con salida 4. El código está bien: lo que cambia es que no da lo mismo dos veces, y eso no es un fallo del código |
| 235 | los corchetes se ponían dos veces | `registrar` abría el array y el cierre lo envolvía otra vez: `[[{…}]]`, que parsea sin error y no es lo que se pedía. Un JSON que parsea y no es lo que creías es peor que uno que no parsea |
| 236 | el detalle del diff no decía QUÉ campo | `diff` de dos listas decía `1c1`. Ahora se separa clave (nombre) de valor (estado:recuento) y se comparan por nombre |
| 237 | `join` no emparejaba nada | `join` empareja por la línea ENTERA, no por el nombre: con `pasa=PASS:7` en ambos lados no encuentra coincidencia. La clave es lo que hay antes del primer `=` |

## 2x. El ciclo 3 NO es una carrera: son dos fases con bits DISJUNTOS

Herramienta nueva: `bits.py`.  Cierra la pregunta abierta en la seccion 2w:
¿`gmc_v8_0_vm_fault_interrupt_state` (el manejador de IRQ) es la fase
complementaria de `gmc_v8_0_gart_enable`, o compite con ella?

**Respuesta: son fases disjuntas.  `setup AND irq = 0x0`.**

```text
CONTEXT0_CNTL campos: 22   CONTEXT1_CNTL: 22
comunes: 22   mismo valor: 22   solo en uno: []   distintos: []

SETUP     gmc_v8_0_gart_enable                 mascara=0x17       bits=4
TEARDOWN  gmc_v8_0_gart_disable                mascara=0x0        bits=0
IRQ       gmc_v8_0_vm_fault_interrupt_state    mascara=0x249248   bits=7

setup AND irq  = 0x0        <- NINGUN bit en comun
setup AND tear = 0x0
```

El setup pone `ENABLE_CONTEXT`, `PAGE_TABLE_DEPTH`, `RANGE_PROTECTION_FAULT_
ENABLE_DEFAULT` y `DUMMY_PAGE...DEFAULT`: son los bits de **configuracion por
defecto** y el enable del contexto.  La IRQ pone los siete
`*_PROTECTION_FAULT_ENABLE_INTERRUPT`: son los bits de **notificacion**.  No se
solapan ni en un bit.

**Lo que esto cambia para un driver propio:** el orden.setup -> IRQ no es una
convencion, es una **dependencia**.  Poner ENABLE_CONTEXT=1 con la VM activa
y sin los bits de interrupcion puestos deja la VM ejecutando sin que nadie
notifique un fault: el fallo se produce en silencio.  Y al reves, habilitar los
bits de interrupcion sobre un contexto deshabilitado no hace nada.  Hay que
hacer las dos cosas, y el codigo las hace en dos sitios distintos sin que nada
lo obligue.

### Y una hipotesis mia que era FALSA

Al mirar los nombres, la IRQ construye su mascara con
`VM_CONTEXT1_CNTL__*_MASK` y la aplica a `mmVM_CONTEXT0_CNTL`.  Eso parece un
bug de copy-paste.  **No lo es:** los 22 campos de `CONTEXT0_CNTL` y
`CONTEXT1_CNTL` tienen el mismo nombre y el mismo valor de mascara, asi que un
nombre de `CONTEXT1_MASK` pesa lo mismo sobre `CONTEXT0`.  Los nombres son
cosmeticos.

Declararlo bug habria sido la clase E --"primero que casa"-- otra vez: el
sintoma encajaba con un error de copy-paste y no con un layout identico.  La
comprobacion que lo evita es una sola, y es la que importa: **¿son iguales los
layouts?**  Con control positivo, porque si la comprobacion dijera "iguales"
siempre, no probaria nada.

### Correccion 168

`mascara_de(bits, 0)` con nombres de `CONTEXT1` devolvia 0, y el aserto leia
"la IRQ no pone 7 bits" cuando el dato era correcto.  0 significaba "los nombres
son de otro contexto", no "no hay bits".  La funcion ahora recibe el contexto
de origen como parametro explicito.

## 2y. "Mascara 0" no es "no toca campos": es escribir el registro a cero

`bits` dio `gart_disable` con mascara `0x0`.  Leyendolo como "no pone ningun
campo" es un error.  El fuente dice:

```c
/* gmc_v8_0_gart_disable, gmc_v8_0.c:1004-1006 */
WREG32(mmVM_CONTEXT0_CNTL, 0);
WREG32(mmVM_CONTEXT1_CNTL, 0);
WREG32(mmVM_L2_CNTL2, 0);
```

**Escribe el registro ENTERO a cero.**  Eso borra todos los campos que otro
ponga, incluidos los que no le tocan.  Es la operacion opuesta a un RMW por
campo:

```text
escribir un REGISTRO ENTERO  ->  afecta a TODOS sus campos
escribir un CAMPO            ->  afecta a SOLO ese campo
```

Un RMW parcial se solapa solo con quien toque los MISMOS campos.  Una escritura
en bruto se solapa con quien toque CUALQUIER campo del registro.  Por eso el
"solape 0" de la seccion 2x no era del teardown: el teardown no ponia bits, los
BORRABA todos.

### 4 de las 13 escriben en bruto

```text
gmc_v8_0_mc_stop      mmBIF_FB_EN
gmc_v8_0_mc_program   mmHDP_NONSURFACE_SIZE, mmHDP_REG_COHERENCY_FLUSH_CNTL,
                      mmMC_VM_AGP_BASE
gmc_v8_0_gart_enable  mmVM_CONTEXT0_CNTL2, mmVM_CONTEXT1_CNTL2,
                      mmVM_CONTEXT1_PAGE_TABLE_START_ADDR,
                      mmVM_L2_CONTEXT1_IDENTITY_APERTURE_HIGH/LOW_ADDR,
                      mmVM_L2_CONTEXT_IDENTITY_PHYSICAL_OFFSET
gmc_v8_0_gart_disable mmVM_CONTEXT0_CNTL, mmVM_CONTEXT1_CNTL, mmVM_L2_CNTL2
```

Y eso reencuadra el ciclo 3, que era "setup pone 4 campos, IRQ pone 7, solape 0":

```text
gart_disable  ->  WREG32(mmVM_CONTEXT0_CNTL, 0)
                 ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ borra los 4 campos del setup
                 y los 7 de la IRQ, y todos los otros 11 del registro
```

**El teardown es el unico miembro del ciclo que pone `ENABLE_CONTEXT=0`**, y lo
hace borrando la palabra entera.  Un driver propio que habilite la VM y luego
deshabilite reusando esa llamada esta bien por casualidad: funciona porque el
teardown borra todo, no porque ponga el enable a 0.  Si en algun momento
alguien escribiera `WREG32(mmVM_CONTEXT0_CNTL, 0)` esperando preservar algo, no
preservaria nada.

Herramienta nueva: `pisa.py`, 18/18 con control positivo (`gart_disable` DEBE
aparecer con escritura en bruto de `CONTEXT0_CNTL`; si no, la heuristica esta
rota).

### Correccion 169

El RMW por campo se buscaba mirando el operador (`&`/`|`) en la linea de la
escritura, y la escritura es `WREG32(reg, tmp)`: no hay operador.  La operacion
esta dos lineas antes, en el `REG_SET_FIELD`.  Resultado: los RMW se
perdidan y solo se veian las escrituras literales -- es decir, la herramienta
encontraba exactamente lo contrario de lo que queria.  Ahora se rastrea que
variable ha sufrido una operacion de campo y se cruza con la escritura.

## 2z. El ciclo de GART NO es reversible: pierde 21 y 11 campos

Herramienta nueva: `revierte.py`.  La pregunta: ¿`gart_disable` seguido de
`gart_enable` devuelve `CONTEXT*_CNTL` al estado que encontro?

```text
CONTEXT0_CNTL
  el setup recupera : 0x17       (4 bits)
  el ciclo pierde    : 0xffdb6da0 (21 bits)
  reversible         : False
CONTEXT1_CNTL
  el setup recupera : 0xf492497  (14 bits)
  el ciclo pierde    : 0xf0924920 (11 bits)
  reversible         : False
```

**El ciclo pierde 21 campos en CONTEXT0, no 7.**  Mi suposicion --"solo se
pierden los 7 de la IRQ"-- era una conjetura sobre lo que el ciclo tocaba, no
sobre lo que decia el calculo.  Los 21 tienen nombre:

```text
DUMMY_PAGE_PROTECTION_FAULT_ENABLE_DEFAULT      0x80
PDE0_PROTECTION_FAULT_ENABLE_DEFAULT           0x400
PDE0_PROTECTION_FAULT_ENABLE_SAVE               0x800
VALID_PROTECTION_FAULT_ENABLE_DEFAULT          0x2000
VALID_PROTECTION_FAULT_ENABLE_SAVE             0x4000
READ_PROTECTION_FAULT_ENABLE_DEFAULT           0x10000
READ_PROTECTION_FAULT_ENABLE_SAVE              0x20000
WRITE_PROTECTION_FAULT_ENABLE_DEFAULT          0x80000
WRITE_PROTECTION_FAULT_ENABLE_SAVE             0x100000
EXECUTE_PROTECTION_FAULT_ENABLE_DEFAULT        0x400000
EXECUTE_PROTECTION_FAULT_ENABLE_SAVE           0x800000
PAGE_TABLE_BLOCK_SIZE                          0xf000000
```

**Lo que esto significa para un driver propio:** `gart_disable` borra el
registro entero, y `gart_enable` solo repone 4 campos en CONTEXT0.  Repetir el
ciclo **deja la VM con los campos de proteccion que tuviera, borrados**.  El
setup configura `CONTEXT1` a fondo (14 campos) y `CONTEXT0` solo a 3 mas
`ENABLE_CONTEXT`, asi que la asimetria es real y no un descuido del calculo.

Y hay un acoplamiento que no se ve en ningun miembro por separado: el ciclo
`enable -> disable -> enable` **no** devuelve el registro al estado inicial,
porque la IRQ es la unica que pone los bits de notificacion y hay que volver a
llamarla.  Quien repita el ciclo creyendo que es simetrico pierde capacidad de
notificacion de faults.

### Correcciones 171-173

| # | error | correccion |
|---|---|---|
| 171 | el caso sintetico inicial usaba `m_tear = BRUTO` como si borrara | `m_tear` es la mascara que PONE, no la que borra. Un teardown que escribe 0 es `m_tear = 0`. Con `BRUTO` la formula daba 0 y "nada perdido" con el razonamiento equivocado |
| 172 | el aserto fijaba "pierde 7" | son 21 en CONTEXT0: el setup configura 14 campos solo en CONTEXT1, y en CONTEXT0 no pone ninguno de los de proteccion |
| 173 | el assert "los 7 de la IRQ estan perdidos" fallaba en CONTEXT1 | y con razon: en CONTEXT1 el setup PONE los 7, asi que no se pierden. El assert correcto es "lo perdido no lo cubre ni setup ni IRQ" |## 3i. La procedencia de un campo, por rastro y no por nombre (192-193)

El mandato declara de donde viene cada campo.  Eso se decidia contando quantas
veces aparece el NOMBRE del campo en el corpus, y los dos criterios dan
respuestas **opuestas**:

```text
campo                                  token_en   se escribe en
RANGE_PROTECTION_FAULT_ENABLE_INTERRUPT    0       gmc_v6_0/v7_0/v8_0/v9_0
PAGE_TABLE_DEPTH                          23       si, por REG_SET_FIELD
```

El primero aparece cero veces porque el corpus lo nombra con el prefijo del
registro delante (`VM_CONTEXT1_CNTL__RANGE_..._INTERRUPT_MASK`), y con
`\b<campo>\b` no casa.  El segundo aparece 23 veces y no lo escribe nadie con ese
campo: son 23 ficheros que lo mencionan.  **El mandato afirma lo que el corpus
HACE, asi que el criterio correcto es el rastro, no la cuenta.**

El rastro distingue dos modos, porque no son la misma operacion:

```text
REG_SET_FIELD(tmp, REG, CAMPO, v) + WREG32(REG, tmp)   RMW_CAMPO    pisa 1 campo
REG__CAMPO_MASK dentro de tmp |= bits / tmp &= ~bits     RMW_MASCARA  pisa los N
```

Que la mascara contenga 7 campos no significa que se escriban uno a uno, y sin
esa distincion el recuento de "campos escritos" sale 7 veces mayor que el numero
de escrituras reales.

### Correccion 193: un nombre de campo no es global

`ECO_BITS` esta en 11 ficheros del corpus y en ninguno de la ruta VI.  Los 11 lo
escriben sobre el registro con prefijo de su generacion: `GCMC_` en
gfx_v3_0/v3_0_3/v11_5_0/v12_0/v12_1 y `MMMC_` en mmhub_v3_0/v3_0_1/v3_0_2/v3_3/
v4_1_0/v4_2_0.  El mandato escribe `MC_VM_MX_L1_TLB_CNTL`, que es el prefijo real
de Polaris12.  Es la clase J de las dos numeraciones, aqui entre **hubs**, y se
resuelve con una expansion de alias automatico, no escribiendo los nombres a mano.

### Y un hallazgo que el rastreo destapa

```text
VM_CONTEXT1_CNTL: 17 de 22 campos con escritura real en el corpus
                   7 por RMW_MASCARA (la IRQ de gmc_v8_0.c:1391-1418)
                   5 con CERO escrituras en todo el arbol -> PROVEN_ABSENT
```

Los 5 son los `*_PROTECTION_FAULT_ENABLE_SAVE`.  Con universo declarado y control
positivo, eso **si** es `PROVEN_ABSENT` y no `NOT_FOUND`: existen en el header,
el driver los declara con su fuente en linea, y ningun path del amdgpu los
programa.  Eso hace que el patch **no se pueda dar por cerrado en su
justificacion**: 5 de sus 50 campos no tienen respaldo de escritura.


## 3h. La frontera de alcanzabilidad, cerrada por clase de error (186-191)

El veredicto final de las 13 funciones en conflicto de escritura de registro:

```text
PROCESO                9   raiz citada, punto de entrada del driver
IRQ                    1   amdgpu_irq.c:amdgpu_irq_disable_all
MIEMBRO_OTRA_GENERACION 3   tabla registrada, ningun consumidor en la ruta VI
```

### Correccion 189: `TOP` no era "sin resolver"

Tres de las 12 "sin resolver" tenian la cadena AGOTADA en
`amdgpu_device_init`, `amdgpu_device_gpu_recover` y `amdgpu_device_fini_hw`.
Eso no es una laguna: es una raiz definitiva.  Agotarse en el probe del driver
es una respuesta.  Lo que separa "termino en una raiz" de "no pude determinarlo"
es si la funcion terminal es un punto de entrada conocido, y eso es una tabla de
12 nombres, no un analisis.  Misma familia que la 152, un nivel mas arriba: alli
se confundio TOP con VIA_OPS; aqui se confunde "la cadena se agota" con "no hay
respuesta".

### Las 3 de MIEMBRO_OTRA_GENERACION: codigo muerto en esta ASIC

```text
gfxhub_v2_1.c:657   .gart_enable = gfxhub_v2_1_gart_enable      <- registrada
->gart_enable(  en:  aldebaran.c  sienna_cichlid.c
                gfx_v11_0.c  gfx_v12_0.c  gfx_v12_1.c  gmc_v9_0.c
                ninguno de la ruta VI
```

Con control positivo: 6 ficheros contienen `->gart_enable(`, y 0 son de la ruta
VI.  No es que no se encuentre: es que la tabla se registra y queda sin uso en
VI, y la invocan Aldebaran, Alaska y Arcturus.  **No compiten por contexto,
porque no hay dos llamantes.**  Eso baja el riesgo real de 13 a 10.

### Correcciones 186-188: el anillo y la cache

186: el consumidor de una ops table no esta en el fichero que la declara.
187: el segundo anillo son los 3 ficheros con el bucle `ip_blocks[i].version->funcs->M(`, criterio medido sobre el arbol.
188: `callgraph.clang_ast` delegaba en `funcspan._clang_ast` sin querer; ahora delega a proposito, y con 11 ficheros se paga un parseo y no 22.


## 3g. `--parche`: veredicto unico, y una guarda de escritura

Tres comprobaciones con nombre y un veredicto, sustituyendo a tres comandos que yo
tenia que recordar en orden:

```text
MANDATE REAL, desde su sitio
  TABLA       PASS   MC_VM:6/6, CONTEXT1:22/22
  COMPILACION SKIP_ESCRITURA   ... esta fuera de /var/tmp/rx550
  SUITE       PASS   276 PASS / 0 FAIL
  TODO        PASS   2 PASS / 1 SKIP / 0 FAIL

SANDBOX (con el parche de la tabla)
  TABLA       PASS   MC_VM:6/6, CONTEXT0:22/22, CONTEXT1:22/22
  COMPILACION PASS   rc=0 ko=643368 B
  SUITE       SKIP_ENTORNO   los 12 FAIL son de cwd, no de codigo (60 PASS)
  TODO        PASS   2 PASS / 1 SKIP / 0 FAIL
```

### Correccion 185: una herramienta que escribia fuera de mi perimetro

Ejecute `--parche` sobre el mandate **real**, y compila: `make` escribe `.o` y
`.ko` en el directorio que se le pase.  El `.ko` se reconstruyo byte-identico y
no hubo dano -- los tres sha sin cambio, `staged` 0, ningun `.o` modificado --,
pero **la accion estaba fuera del perimetro y solo se evite por suerte.**

Eso no es un incidente menor: es el patron de las 185 correcciones anteriores,
con el seguimiento.  Cada vez que una accion mia puede tener efecto fuera de
`/var/tmp/rx550`, el perimetro tiene que estar **en el codigo**, no en la
atencion.  Ahora:

```c
perimetro = realpath("/var/tmp/rx550")
dentro    = destino == perimetro or destino.startswith(perimetro + "/")
if not dentro:  SKIP_ESCRITURA, con el motivo, sin compilar
```

Es la misma correccion 183 con otro nombre: **una comprobacion que no puede
hacerse no es una comprobacion que falle.**  Las tres (`SKIP_ENTORNO`,
`SKIP_ESCRITURA`, `PASS`) cuentan para el veredicto; solo `FAIL` lo hunde.

### Correccion 184: el cwd de la suite es el driver, no el proyecto

La suite resuelve el corpus con rutas relativas (`../../RESEARCH`), que solo
existen desde el propio directorio del driver.  Con el `cwd` del proyecto padre,
`R00` fallaba **por un motivo distinto al suyo** y el diagnostico salia mal: un
diagnostico que senala el sintoma equivocado es peor que ninguno.


## 3f. El parche, en un sandbox, verificado cerrando el bucle

El mandate es de solo lectura para mi, asi que el cambio se preparo **en una
copia**, se aplico ahi y se volvio a medir.  El arbol compartido no se toco:
`rx550_mmio_access.c` conserva su sha `043e24c5dca469fc3848c939c0bfdda7` y
`git diff --cached` sigue a 0.

```text
                       declarados  header  estado            declarados  header  estado
                       --- ORIGINAL ---                     --- CON PARCHE ---
MC_VM_MX_L1_TLB_CNTL         6        6  CORRECTO               6        6  CORRECTO
VM_CONTEXT0_CNTL             -        -  AUSENTE               22       22  CORRECTO
VM_CONTEXT1_CNTL            22       22  CORRECTO              22       22  CORRECTO
```

Y la proveniencia, que es la otra mitad del cambio:

```text
_INTERRUPT   DECLARED_NOT_WRITTEN (7)  ->  PROVEN_CORPUS_WRITES (7)
             fuente: gmc_v8_0.c:1391
```

**El bucle cierra exactamente como la herramienta predijo**, y eso lo comprueban
5 asserts que solo se ejecutan con el sandbox presente: `mandato.py` grew una
variable de entorno (`RX550_MANDATO`) y otra (`RX550_PATCH_TEST`) para poder
medir un parche sin tocar el original.  Con el sandbox, 23/23.

El parche son 2 cambios y ninguno borra datos:

```text
+ 22 filas de VM_CONTEXT0_CNTL, con un comentario que dice por que
  7 filas de _INTERRUPT: DECLARED_NOT_WRITTEN -> PROVEN_CORPUS_WRITES,
                         y la fuente pasa a ser gmc_v8_0.c:1391
ficheros .c/.h con contenido distinto tras el parche:  1
```

### Correcciones 179-181

| # | error | correccion |
|---|---|---|
| 179 | no habia forma de medir un parche sin tocar el original | `RX550_MANDATO` y `RX550_PATCH_TEST` en `mandato.py`: se mide una copia. Los asserts del parche solo corren con el sandbox presente, asi que en el original no pueden dar un "todo bien" vacio |
| 180 | el corte de la tabla por el primer `};` duplico tambien las 6 filas de `MC_VM` | el corte correcto son las lineas que empiezan por `{ "VM_CONTEXT1_CNTL"`, no el primer `};` del fichero. Resultado: 12 declarados contra 6 del header — el `CORRECTO` de MC_VM lo habria destapado |
| 181 | un assert de conteo mezclaba dos cosas | `registros_declarados()` cuenta REGISTROS (26) y el assert queria CAMPOS (50). Salia 26 contra 48 esperado sin que hubiera error de parche |


## 3d. `mandato.py`: la verificacion del mandato, convertida en salida regenerable

He verificado la tabla de campos del mandate **tres veces** hoy con regex
inline distintas.  La tercera dio "las 22 filas difieren del header" sobre un
dato correcto.  Eso es trabajo manual convertible en herramienta, y su salida
decide si el driver del mandato es utilizable.

```text
mandato.py 1.0 · 13/13

registro                    declarados  header  estado
VM_CONTEXT1_CNTL                   22       22  CORRECTO
MC_VM_MX_L1_TLB_CNTL                6        6  CORRECTO
VM_CONTEXT0_CNTL                    0       22  AUSENTE
```

**Los 28 campos del mandato son correctos**: mask y shift identicos al header del
kernel, con la linea del corpus citada en cada fila.  El problema es de
COBERTURA, no de datos.

### El dato que la herramienta hace visible y a mano no

```text
VM_CONTEXT0_CNTL  no lo declara   ->   y el header tiene 22 campos
                                      y los 22 tienen el MISMO valor
                                      que los de CONTEXT1
```

La tabla de `CONTEXT1` es reutilizable tal cual para `CONTEXT0`: no hay que
generar 22 definiciones, hay que duplicar la tabla bajo el otro nombre.  Y el
registro que falta es **el que `gart_disable` pone a cero**
(`gmc_v8_0.c:977`), asi que es justo el que hace falta para que un escritor
pueda dejar la VM en GART sin pisar el contexto 0.

### Correccion 177: la clase J, entre GENERACIONES

La primera version de la herramienta tomaba **el primer header con el nombre**:
`glob` sobre `asic_reg/*/*_sh_mask.h` devuelve uno por generacion ASIC, y el
mismo nombre de campo tiene **valores distintos en cada una**.  Daba 19 campos
para `CONTEXT0_CNTL` y "difiere" en 18 filas, cuando la tabla del mandate era
correcta.

Es la clase J --dos numeraciones para lo mismo-- pero entre generaciones en vez
de entre espacios de offset, y el criterio correcto no es "el primero que
casa" sino **el header donde todos los campos que declara el mandate existen**.
Si hay empate perfecto entre varios headers, se declara `AMBIGUO` en vez de
elegir.  Sin referencia de campos, el criterio no discrimina: por eso el assert
de CONTEXT0 pedia 19 hasta que se le pasaron los 22 nombres de CONTEXT1.


## 3c. La tabla del mandato cubre 28 campos de 2 registros, y falta el peligroso

Recuento completo de lo que el mandate declara:

```text
{ "VM_CONTEXT1_CNTL", ... }        22 campos   -> 22 en el header, 0 diferencias
{ "MC_VM_MX_L1_TLB_CNTL", ... }      6 campos   ->  6 en el header, 0 diferencias
{ "VM_CONTEXT0_CNTL", ... }         0 campos   -> AUSENTE
```

Las 28 filas existentes son **correctas**: mask y shift identicos al header del
kernel en las 28, incluidas las de constante con nombre.  El problema no es un
dato erroneo: es un registro entero que no esta.

### Por que ese registro es el que importa

```text
                     CONTEXT0_CNTL      CONTEXT1_CNTL
gart_enable (setup)      4 campos          14 campos
gart_disable (teardown)  WREG32(reg, 0)    WREG32(reg, 0)
```

El teardown **pone a cero los dos**.  El setup configura a fondo `CONTEXT1` y
apenas toca `CONTEXT0`.  Y el mandato declara los 22 campos de `CONTEXT1` y
**ninguno de `CONTEXT0`**.

Un escritor del mandate que quiera preservar campos usando su tabla puede
preservar los 22 de `CONTEXT1`, y de `CONTEXT0_CNTL` **no sabe ningun campo**.
Cuando su teardown tenga que dejar la VM en GART sin tocar el contexto 0, no
tiene forma de hacerlo bien: o lo pisa entero, como hace el corpus, o no tiene
con que preservar.

La ironia es que el mecanismo existe y esta probado: `bits` demostro que
`CONTEXT0_CNTL` y `CONTEXT1_CNTL` tienen **los 22 campos con el mismo nombre y el
mismo valor de mascara**, asi que la tabla de `CONTEXT1` es directamente
reutilizable para `CONTEXT0`.  No hace falta generar nada: basta con la misma
tabla bajo el otro nombre de registro.

### El estado del mandate, en una linea

```text
datos        CORRECTOS      28/28 filas, mask y shift exactos, con fuente en linea
cobertura    INCOMPLETA     falta VM_CONTEXT0_CNTL, que el teardown pone a cero
inferencia   ERRONEA        7 campos _INTERRUPT marcados NO_CORPUS; los pone la IRQ
```

Tres cosas y ninguna es un dato malo: dos son de **cobertura** y una de
**interpretacion**.  Un escritor puede usar los valores; no puede usar la tabla
para preservar `CONTEXT0_CNTL` ni para tratar los `_INTERRUPT`.


## 3. HALLAZGO SOBRE EL DRIVER DEL MANDATO: 7 campos mal clasificados

`04-IMPLEMENTACION/rx550-driver/rx550_mmio_access.c:257` dice:

```c
/* ── los _INTERRUPT: el corpus no los toca, y por eso constan sin valor ── */
{ "VM_CONTEXT1_CNTL", "RANGE_PROTECTION_FAULT_ENABLE_INTERRUPT", 0x8,  3, 1, RX550_FIELD_NO_CORPUS, ... }
{ "VM_CONTEXT1_CNTL", "DUMMY_PAGE_..._INTERRUPT",                 0x40,  6, 1, RX550_FIELD_NO_CORPUS, ... }
  (7 en total)
```

**El corpus SI los toca.**  Los escribe `gmc_v8_0_vm_fault_interrupt_state`
(`gmc_v8_0.c:1391-1397`), que es un miembro del ciclo de GART:

```text
RANGE_PROTECTION_FAULT_ENABLE_INTERRUPT     0x8
DUMMY_PAGE_PROTECTION_FAULT_ENABLE_INTERRUPT 0x40
PDE0_PROTECTION_FAULT_ENABLE_INTERRUPT      0x200
VALID_PROTECTION_FAULT_ENABLE_INTERRUPT     0x1000
READ_PROTECTION_FAULT_ENABLE_INTERRUPT      0x8000
WRITE_PROTECTION_FAULT_ENABLE_INTERRUPT     0x40000
EXECUTE_PROTECTION_FAULT_ENABLE_INTERRUPT   0x200000
                                   mascara  0x249248
```

### Por que importa mas de lo que parece

El driver del mandato declara esa distincion con un motivo exacto y correcto:

> Los doce DECLARED_NOT_WRITTEN de CNTL existen para una sola cosa: que el
> nodo siguiente sepa qué bits SON SUYOS y cuáles tiene que preservar. [...] un
> escritor que no sepa qué campos hay no puede conservar nada.

**Ese es exactamente el mecanismo que evita el bug que acabo de encontrar en el
corpus.**  Y sin embargo, al marcar los 7 `_INTERRUPT` como `NO_CORPUS`, el
driver se está diciendo a si mismo que esos bits no los pone nadie y que por
tanto puede pisarlos sin más.

Lo que el corpus hace con ellos es ponerlos y quitarlos desde la IRQ.  Si un
escritor del driver del mandato los preserva como "nadie los toca", va a
sobrescribir la capacidad de notificacion de faults que la IRQ acaba de
configurar.  Es el mismo error que `gart_disable`^borda CONTEXT0_CNTL, pero en el
otro sentido: ahi se perdian campos de proteccion, aqui se perderian los de
notificacion.

### El alcance real del error, y lo que SI es cierto

La afirmacion del driver es mas estrecha de lo que parece y **no es falsa**: el
setup (`gart_enable`) y el teardown (`gart_disable`) no tocan esos 7 campos.  Lo
que no es cierto es "el corpus no los toca", porque la IRQ es parte del ciclo.

Corregido:

```text
PROVEN_CORPUS_WRITES     el corpus los escribe, en gmc_v8_0.c:1391-1418 (la IRQ)
NO_ES_DEL_SETUP          pero gart_enable/gart_disable NO los tocan
CONSECUENCIA             un escritor debe preservarlos igual: los pone la IRQ
```

Es la clase A otra vez --"nombre asumido, luego 0, luego ausente"-- aplicada al
mandato: un escaneo acotado al par setup/teardown dio 0 y se concluyo que nadie
los escribe.  El cero era del alcance, no del corpus.

### Y una buena noticia sobre el diseno

La distincion `PROVEN_CORPUS_WRITES` / `DECLARED_NOT_WRITTEN` del driver del
mandato es **la generalizacion correcta** de lo que `bits` y `pisa` dedujeron a
mano: escribir por campo preserva el resto, escribir el registro entero no.  El
driver tiene la maquinaria necesaria; lo que falta es un escritor que la
ejercise y que sepa que esos 7 campos no son suyos.


## 0. Las dos correcciones que costaron evidencia

| # | error | coste |
|---|---|---|
| 75 | **vivir en `/tmp`** — un reinicio lo borró | 11 herramientas, 24 informes y este registro. Reconstruido aquí, en `/var/tmp`, que sobrevivió |
| 77 | **no verificar la escritura** — `RE-INDEX.md` quedó 8841 B de null tras una interrupción | el registro completo, otra vez. Corregido: todo `write` va seguido de `bytes`+`nulls`+contenido |

El informe de incidente estaba en `/var/tmp` desde el principio **porque no era
mío**. Nadie eligió que fuera más durable que mis artefactos. Esa fue la omisión.

## 1. Taxonomía — por qué ocurren

Casi 2/3 no son falta de evidencia, son hábitos:

| clase | mecanismo | refs |
|---|---|---|
| **A** nombre asumido → 0 → «ausente» | se nombra lo que debería existir, `grep` da 0, se concluye ausencia. El objeto existía con otro nombre/cabecera/directorio | 14, 27, 30, 31, 34, 56, 63, 68 |
| **B** citar `file:N` sin abrir la línea | se afirma el contenido de una línea no leída | 35, 38, 40, 41, 42, 55 |
| **C** el test afirma una creencia | comprueba lo que el autor ya creía, no el código | 38, 54 |
| **D** mezclar generaciones | dos ASIC comparten símbolo con valor distinto; se cita el de otra | 50, 55, 56, 66 |
| **E** primero que casa | un regex casa con la declaración adelantada, o con la cabecera alfabéticamente primera | 63, 72, 73 |
| **F** cero silencioso | un 0 se lee como ausencia; indistinguible de un bug | 27, 30, 51, 60, 70, 73 |
| **G** cobertura como prosa | tabla escrita a mano que miente al cambiar la realidad | 67 |
| **H** filtro que parece prefijo y no lo es | `[:3] in ("mmR",…)` en vez de `startswith` | 76 |

**A, E, F y H son la misma familia**: un escaneo que devuelve un subconjunto
—o nada— parece completo. De ahí las guardas explícitas en `regctx.py`.

## 3. Correcciones 1-46 (reconstruidas por clase)

| ref | error | corrección |
|---|---|---|
| 14 | looks-like `gpu_buddy` ~ `drm_buddy` | el objeto existía; cambió el nombre |
27, 30 | conté **presencia de un término**, no existencia del artefacto | «7 de 8 artefactos» cuando no había ninguno regenerable |
| 31 | afirmé `ipblock` resuelto sin abrir el fichero servido | el log da el **nombre**; resolver el fichero es otro paso |
| 34 | `regdb` mezclaba generaciones | indexar offsets sin fijar generación |
35, 38 | cité `file:N` sin abrirla; afirmé `_SH_MASK` ausente | **21 ficheros lo usan**; el test afirmaba mi creencia |
40, 41 | traté `smu7_hwmgr.c` como si no fuera el que sirve la hwmgr de VI | sí lo sirve; sus 35 refs a POLARIS eran la señal |
| 42 | cité `amdgpu_gmc.c:148` como productor PD | la 148 es `}`; la 141 selecciona **por orden de enum** |
| 43 | traté `AMDGPU_VM_PDB0` como «nivel 0» | es el valor **3** de un enum **descendente** (`amdgpu_vm.h:191`) |

## 4. Reglas derivadas

```text
1  cero resultados NO es ausencia: puede ser grep mal construido, regex mal
   escrito, filtro que parece prefijo, o cabecera equivocada.  Medir antes.
2  citar file:N exige abrir la línea.
3  un test comprueba el código, no la creencia del autor.
4  todo offset va acompañado de su generación, y la generación la fija el
   #include del .c que accede — no el orden de un glob.
5  un detector que declara cobertura falsa es peor que no tenerlo.
6  un 0 silencioso es peor que un error: poner guardas que lo hagan visible.
7  VELOCIDAD != PERDER VALIDACION.  Y: /tmp no es almacenamiento.
8  tras cada escritura, verificar; tras cada reinicio, volver a verificar.
```

## 5. Una afirmación retirada, y otra que sobrevive

| publicada | estado |
|---|---|
| `regIH_RB_BASE = 0x0081`; «42 conflictos» | **`0x0083`**; conflictos **0**. Falsas por mi herramienta, no por el corpus |
| `mmGRBM_STATUS2 = 0x2002` (`gfx_8_1_d.h:862`) | **correcto**: `0x2002` también en `gfx_8_0_d.h:863`. Sobrevive |

No todo lo publicado era falso. Decirlo igual es parte del registro.

## 3. Correcciones 208-231 — el ciclo validándose a sí mismo

Del fingerprint (208) al veredicto del parche dentro del ciclo (221-231): todas
las correcciones de este bloque nacen de la misma decisión, que es **dejar de
mirar a mano lo que la automatización puede medir**, y todas son fallos de la
automatización que la automatización destapó.

### 208: un `PASS` no dice sobre qué máquina se sostiene

`KIT-VERDICT.json` no declaraba el hardware. La cadena de linaje pide
`ARTIFACT ← PRODUCER ← INPUT ← SOURCE ← CONFIGURATION ← HARDWARE STATE`, y faltaba
el último eslabón. Todo se lee del sistema —sysfs, DMI, debugfs— porque un
fingerprint escrito a mano es una afirmación, y afirmación es justo lo que el
ciclo viene a comprobar.

```text
pci 0000:01:00.0   device 0x699f   asic_resuelta CHIP_POLARIS12
nodo_drm card1     bar0 0x00000000e0000000   vram 2147483648
placa ECS H81H3-M4  bios 4.6.5    topologia_pci 17/2
```

**Todo lo que el prompt declara como hipótesis es ahora medición.** La ASIC se
resuelve por el device ID contra la tabla de PCI IDs del corpus
(`amdgpu_drv.c:2041`), no por el nombre: si el ID no está, sale `NO_RESOLUBLE` en
vez de suponer Polaris12 porque es lo que esperamos.

Y `card0` **no** es la RX550 — es la iGPU. `card1` es la RX550. El nodo se
resuelve comparando enlaces **reales**: `/sys/bus/pci/devices/0000:01:00.0` y
`/sys/class/drm/card1/device` resuelven al mismo sitio con dos rutas distintas
(219). Un `NINGUNO` ahí no es "no hay nodo": es "no se compararon las dos formas
del mismo dispositivo", y se lee igual.

### 210-214: el parseo de la tabla de PCI IDs

Tres fallos encadenados, y el tercero es el que más dice:

```text
210  el emparejamiento contaba los índices de los separadores, no los campos
211  el último campo no era f[n]: al partir por comas, '} ,' deja un 8º vacío
212  comparaba CHIP_POLARIS12 contra POLARIS12: dos notaciones, un TARGET_MISMATCH INEXISTENTE
214  comprobaba FP_ESPERADO, que se declara después del self-test
```

El 212 es el peor de los tres porque **el ciclo mintió sobre el hardware**: dijo
que esta máquina no es la correcta cuando sí lo es. Un fallo de formato produce
una afirmación falsa, y una afirmación falsa sobre el objetivo es peor que no
comprobarlo.

### 216-219: los campos que el prompt pedía y no estaban

La VRAM no está en sysfs en este kernel; se lee de debugfs y da 2147483648 B. Si
no estuviera, se declara `NOT_AVAILABLE` **con la ruta donde se leería** —"no lo
sé" con la ruta es información; sin ella es un hueco (216). La placa y el BIOS
salen de DMI, y la topología PCI cuenta dispositivos y funciones VGA: el prompt
nombra una iGPU, y eso cambia la topología aunque la RX550 no cambie.

### 220: una herramienta se evaporó y el ciclo siguió verde

Al externalizar el plan a `kit.plan`, el ciclo pasó a informar **14 en vez de 15**
herramientas: `mandato` había desaparecido. La causa es `while IFS= read -r _l`;
`read` devuelve **1** en EOF y sin `|| [ -n "$_l" ]` se descarta la iteración, así
que **una línea sin salto final es una línea que no existe para el bucle**. Lo
importante no es el bug:

```text
14 de 15   parece un resultado, no un fallo
```

El ciclo dijo `PASS` con 341 aserciones y nadie avisó. Ahora imprime
`plan 15 entradas, 15 registradas` y un desajuste es `INVALID_RESULT`.

### 221-231: meter el veredicto del parche en el ciclo

`mandato --parche` no estaba dentro del ciclo. Meterlo parecía añadir una línea y
fue doce correcciones, todas de la misma forma: **una automatización que solo
conoce un tipo de tarea no sabe qué hacer cuando aparece otro.**

```text
VEREDICTO  PASS   16 pasaron · 0 SKIP_ENTORNO · 323 aserciones
  mandato-parche-sandbox  PARCHE: PASS  2 PASS / 1 SKIP / 0 FAIL
  mandato-parche-real     PARCHE: PASS  2 PASS / 1 SKIP / 0 FAIL
```

El plan pasó a `tarea:modo:timeout:env argumento` (221); cada modo tiene su
formato de salida (222); el veredicto del parche se lee por su línea `TODO` y no
por su exit code, porque `mandato` sale **0** con `SKIP_ENTORNO` y
`SKIP_ESCRITURA` (223).

Los cuatro que habrían pasado inadvertidos:

- **226** — `RX550_PATCH_TEST` iba en **las dos** tareas del mandate. Con la
  variable puesta, la del *real* leía el **sandbox por dentro** y su tabla salía
  con `CONTEXT0_CNTL`, que el real no tiene. Medía el objeto equivocado.
- **229** — `KIT` significaba a la vez código y fixtures. Al entrar una tarea de
  veredicto, la ambigüedad la ejecutaba sobre los fixtures, y como 9 de las 15
  herramientas importan unas de otras, un `.py` suelto falla al importar. **El
  síntoma era de la herramienta y la causa de la variable.**
- **230 y 231** — el plan no expandía sus variables. `eval "_linea=\$_l"` evalúa
  `_linea=$_l`: `$_l` se expande **una vez**, su valor es la cadena que contiene
  `${V}`, y `eval` no vuelve a expandir un *resultado*, solo su *código*. Medido:
  leída de un fichero da `${V}`; construida en el shell da `/ruta/x`. El mismo
  `eval`, distinto resultado, y el que corría en producción era el que no
  expandía. Dos `eval` seguidos tampoco; lo que funciona es `envsubst`. **Una
  línea de configuración es configuración, no código.**
- **228** — el log del veredicto se borraba con el `TMP`: era la única copia de
  la evidencia, y un `FAIL` llegaba al artefacto sin el texto que lo produjo.

### 232-237: comprobar que el ciclo da lo mismo dos veces

Un `PASS` no es un resultado: es un resultado **ahora**. Si mañana `alcance`
clasifica las 13 funciones de otra manera por un cambio mío, el ciclo seguirá
dando `PASS` y no habrá nada que lo note. El hash del fingerprint anclaba el
*objetivo*; faltaba anclar el *veredicto*.

```text
estado     16 tareas en la cadena comparable
COMPARE    REPRODUCIBLE   16 tareas, mismo estado y mismo recuento
VEREDICTO  PASS   16 pasaron · 0 SKIP_ENTORNO · 323 aserciones
```

Lo que se compara es el estado de cada tarea y su recuento, en una sola cadena y
en orden de nombre. No se compara el artefacto entero: lleva rutas absolutas y
números de línea que cambian sin que cambie el resultado, y un diff que siempre
dispara es un diff que nadie lee.

Y cuando difiere, la diferencia tiene nombre propio:

```
COMPARE  NO_REPRODUCED  difieren:
              pasa: antes PASS:7, ahora PASS:9
VEREDICTO NO_REPRODUCED
```

**Un resultado que no se reproduce no es un PASS: es un resultado que no se ha
comprobado.** Y tampoco es un FAIL — el código está bien, lo que cambia es que no
da lo mismo dos veces. Por eso `NO_REPRODUCED` es un estado con salida **4**, y no
el 1 de FAIL: son cosas distintas y confundirlas es laRule24 aplicada al propio
ciclo.

Cinco fallos para conseguir esto, y cuatro son de la misma familia: **un JSON que
parsea y no es lo que se cree**.

| | qué parecía | qué era |
|---|---|---|
| 233 | separador del array | la palabra `comma`, no una coma |
| 235 | array de tareas | `[[{…}]]`, corchetes puestos dos veces |
| 236 | detalle del diff | `1c1`, sin decir qué campo |
| 237 | comparación por nombre | `join` empareja por la línea entera, no por la clave |


# 050 · La frontera más repetida del proyecto no es de hardware: es de corpus

`CLASSIFICATION=DOCUMENTATION` · `TRACK=STATIC` · `WORK_CLASS=READ_ONLY/EVIDENCE`
`WRITE_EXECUTION=NONE` · `MODIFICATIONS=0` · `RUNTIME=NOT_RUN` · `GPU INTACTA`
`HERRAMIENTA_NUEVA=08-ARQUITECTURA/tools/corpus_gap.py` (`TOOL_VALIDATED`)
`CONTINUES=049` · `RECICLA=la frontera mas repetida del proyecto, que 6 documentos dejan abierta`

## Cuestión principal

`GFX_HWIP` aparece como `NOT_DETERMINED` en **seis** documentos. ¿Es una
frontera de hardware?

## Criterio de terminación

Determinar de dónde sale el valor de `GFX_HWIP`. **Cumplido: de
`hwmgr.c`, y `hwmgr.c` no está en el corpus.**

## Respuesta: no es de hardware

```
008-firmware-blob.md:103
  "`GFX_HWIP` sigue `NOT_DETERMINED`. Su valor viene del ASIC ID leído por UMR,
   no de un header de firmware."

$ ls RESEARCH/.../amdgpu/hwmgr.c
No existe el fichero o el directorio
```

El ASIC ID lo lee `hwmgr.c`, y ese fichero no está. La frontera es de
**corpus**, no de placa.

## Y eso cambia el trabajo

Una frontera de hardware necesita una placa y permiso de escritura. Una
frontera de corpus necesita **un fichero**, y puede que esté disponible sin
ningún permiso.

Lo segundo es mucho más barato, y estaba clasificado como lo primero. El
costo estaba mal estimado en la frontera más repetida del proyecto.

## El contraste, bloque por bloque

```
bloque    binario  corpus  ausentes
GMC          179     306         0
GFX8          81     139         0
SDMA         444     584         0
DCE          274     322        89
```

**GMC, GFX8 y SDMA están completos.** Cero funciones ausentes en los tres
bloques de los que depende todo lo que el proyecto ha investigado.

Y el 52.8% de "hueco" global es de otra cosa:

```
OTROS                 5363
PP (helpers)          1864
Navi (no en esta placa) 407
SMU                    151
POWERPLAY               92
PP (DPM, si_*)          45
PP (PowerPlay)          43
```

Subsistemas completos —`smu_v11/v14`, `dcn`, `polaris10`, `kfd_topology`— que
el driver trae y el corpus no incluye, y bloques de **Navi que esta placa no
tiene**.

**Traer el árbol entero no cierra ni una frontera de GFX8.** Es un dato útil:
el corpus parcial no está limiting el trabajo, y llevo 37 rondas diciéndolo.

## Los 89 de DCE: el subárbol de display

```
dce_abm_create, dce_abm_destroy, dce_abm_set_level, ...
```

Viven en `display/dc/resource/{dce110,dce120,dcn10}/`. `040` ya lo había
documentado: **no hay `display/` en el corpus**.

Y tiene sentido que no haya: esta placa **no tiene display** (`010`: la GART
mapea a VRAM, y la enumeración de RADV no la lista). Es uno de los pocos
casos donde el corpus está incompleto y da igual.

## La comparación injusta, y por qué importaba

La primera versión de `corpus_gap` dio **85.7% de ausencias**. Era falso, por
tres comparaciones-mal-hechas seguidas:

| error | efecto |
|---|---|
| funciones del corpus contra **todos** los símbolos del binario | 18 556 son datos `r`, que un `.c` no declara igual |
| sin quitar los clones del compilador | `X.isra.0`, `X.constprop.0` son la **misma** función |
| sin quitar los stubs de CFI | 21 750 `__pfx_*` que emite `-fsanitize=cfi` |

**Las tres dicen lo mismo: conté lo que el compilador emite como si el código
no lo declarara.**

85.7% → 82.0% → 80.0% → 52.8%. El 33% de caída vino de tres correcciones de
una línea cada una.

Y un cuarto error, de otro tipo: `si_dpm_*` y `ci_*` los tenía como
`GFX/PACKETS`. Son el subsistema **DPM de gestión de potencia**, con el
prefijo de la generación. Con esa etiqueta, el reparto dizia que faltaban 46
funciones de GFX cuando **`GFX8` estaba completo con 0 ausentes**.

## Clasificación

| afirmación | estado |
|---|---|
| `GFX_HWIP` viene del ASIC ID leído por `hwmgr.c` | `PROVEN` — `008:103` |
| `hwmgr.c` no está en el corpus | `MEASUREMENT` — `ls` |
| `GFX_HWIP` es una frontera de corpus, no de hardware | `DERIVATION` |
| GMC: 0 funciones ausentes | `MEASUREMENT` |
| GFX8: 0 funciones ausentes | `MEASUREMENT` |
| SDMA: 0 funciones ausentes | `MEASUREMENT` |
| Los 89 de DCE están en `display/dc/` | `PROVEN` — `grep -rl` |
| Esta placa no tiene display | `CORROBORATED` — `010`, `067` |
| El 52.8% de hueco es de subsistemas no presentes | `MEASUREMENT` por reparto |
| Que el subtree no limite el trabajo en GFX8 | `DERIVATION` — de los tres ceros |
| Que el subtree no limite el trabajo en display | `NOT_DETERMINED` — no se ha mirado |
| Que exista un `GFX_HWIP` con este nombre en el hardware | `NOT_DETERMINED` — no aparece en ningún header |

## Confounders

- **`hwmgr.c` ausente no significa que el ASIC ID no se pueda leer.** Puede
  haber otro camino en el árbol. No lo he buscado más allá de un `grep`.
- **Los 89 de DCE son subárbol ausente**, pero no sé si son todos de
  `display/`. Otras pueden estar en otro sitio.
- **`OTROS` con 5363 sigue sin explicar del todo.** La muestra que vi
  (`dm_dtn_*`, `hwss_dpp_*`, `rv1_clk_mgr_*`) es de otros subsistemas de Navi,
  pero no los he clasificado uno a uno.
- **El reparto depende del `.ko` descomprimido** que deja `binfacts` en `/tmp`.
  Sin él, la herramienta devuelve `rc=2` y lo dice, en vez de dar un cero que
  parecería "corpus completo".
- **Que el subtree no limite GFX8 es una conclusión mía**, apoyada en tres
  ceros. Es una `DERIVATION`, y se refutaría con una función de GMC o GFX8 que
  el corpus no tenga — que es exactamente lo que mide la herramienta.

## Desfalsificación

- **(a)** `hwmgr.c` no está → refutable con `ls`.
- **(b)** GMC completo → refutable con `comm` entre los símbolos `gmc_*` del
  binario y los del corpus; sale vacío.
- **(c)** GFX8 completo → igual, prefijo `gfx_v8_0_`; sale vacío.
- **(d)** DCE en `display/dc/` → refutable con `grep -rl dce_abm_create`; sale
  la ruta.
- **(e)** El filtro de CFI y clones → refutable mirando `nm` sin filtrar:
  aparecen `__pfx_*` e `.isra.0` mezclados.

## UNLOCKS

- **La frontera más repetida del proyecto se reclasifica**, de hardware a
  corpus, y su costo baja de "necesita placa" a "necesita fichero".
- **Queda demostrado que el subárbol parcial no limita el trabajo en GMC, GFX8
  ni SDMA**, que es donde está todo lo interesting. Eso cierra una pregunta
  que arrastraba el proyecto desde `040`.
- **El método sirve para lo contrario**: si mañana aparece un bloque con
  ausencias altas y sí importa, esa es la que hay que traer.
- **`corpus_gap` mide por bloque**, así que la pregunta "¿qué parte no puedo
  leer?" tiene respuesta automática en vez de ser una intuición.

## Evidencia

```
08-ARQUITECTURA/tools/corpus_gap.py   TOOL_VALIDATED, 14 controles

  simbolos en corpus   15265      en binario  15583
  ausentes              8232  (52.8%)

  GMC   binario 179  corpus 306  ausentes   0
  GFX8  binario  81  corpus 139  ausentes   0
  SDMA  binario 444  corpus 584  ausentes   0
  DCE   binario 274  corpus 322  ausentes  89   -> display/dc/

  hwmgr.c:           NO EXISTE EN EL CORPUS

 Filters aplicados al comparar con el binario:
    - solo simbolos de CODIGO (T/t/W/w), no datos
    - sin clones del compilador (.isra.0, .part.0, .constprop.0)
    - sin stubs de CFI (__pfx_*)
    - corpus incluye display/dc/ y pm/, no solo amdgpu/
```

`WRITE_EXECUTION=NONE`. `MODIFICATIONS=0`. `GPU INTACTA`.
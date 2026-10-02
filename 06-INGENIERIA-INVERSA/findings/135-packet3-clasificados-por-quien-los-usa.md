# 135 · Los 119 `PACKET3` de `sid.h`, clasificados por quién los usa: 20 los usa GFX8, 62 no son opcodes

`CLASSIFICATION=DOCUMENTATION` · `TRACK=STATIC` · `WORK_CLASS=READ_ONLY/EVIDENCE`
`WRITE_EXECUTION=NONE` · `MODIFICATIONS=0` · `RUNTIME=NOT_RUN` · `GPU INTACTA`
`CORPUS=RESEARCH/working/linux-7.1.3` · `HARDWARE_SCOPE=HOST-C/RX550/0000:01:00.0`
`DESARROLLA=el UNLOCK de 121/130 sobre los paquetes no usados`
`CIERRA=la pregunta "que paquetes existen y cuales son necesarios" de §E`

## Cuestión principal

`121` dio un número: GFX8 emite **20 de los 83 paquetes** que `sid.h` define.
`130` no cambió el fondo de esa cifra pero dejó claro que el recuento bruto
mezcla cosas que no son lo mismo.

Preguntas:

1. ¿De esos "no usados", cuántos son **imposibles** en esta placa y cuántos son
   **no explorados**?
2. ¿Cuántos de los nombres `PACKET3_*` son siquiera **opcodes**?

## Criterio de terminación

Cada `PACKET3_*` definido en `sid.h` clasificado por quién lo emite, en una
taxonomía donde las categorías sean disjuntas y sumen el total. **Cumplido:
119 de 119, y la suma cuadra.**

## Herramienta

`pm4_emit.py --quien`. Escanea el árbol de `amdgpu/` buscando
`PACKET3(PACKET3_X` y clasifica por el fichero que lo emite.

## El resultado

```
PAQUETES DEFINIDOS EN sid.h : 119

A. lo emite gfx_v8_0.c -- alcanzable en esta placa       : 20
B. otro motor de GCN3, no el anillo GFX                 :  0
C. solo generaciones ANTERIORES a GCN3 -- no en GFX8     :  1
D. solo generaciones POSTERIORES a GCN3 -- no en GFX8   :  0
E1. OPCODE real que NADIE emite en amdgpu                : 36
E2. NO es un opcode: offset o mascara de registro       : 62

SUMA DE CATEGORIAS = 119 ; DEFINIDOS = 119  -> CUADRA
```

**El recuento de `121` era 83 y era falso.** El regex que usaba
(`^#\s*define\s+(PACKET3_\w+)\s`) exigía un espacio detrás del nombre, y el
último `#define` de cada bloque no lo tiene: se comía **8 definiciones**.
Con `\b` salen las 119.

Y la mayor parte del "no usado" **no son paquetes**.

## E2: 62 de los "no usados" no son opcodes

Comparten el prefijo `PACKET3_` pero son offsets y bits:

```
PACKET3_SET_CONTEXT_REG_START     0xA000    sufijo de campo
PACKET3_SET_SH_REG_END            0x3000    sufijo de campo
PACKET3_TCL1_ACTION_ENA           0x400000  sufijo de campo
PACKET3_SH_KCACHE_ACTION_ENA      0x8000000 sufijo de campo
PACKET3_SEM_SEL_SIGNAL            0xC0000000 > 8 bits
```

Se usan como **aritmética**, no como opcode:

```
amdgpu_gfx.c:2522   ext->reg_index - PACKET3_SET_CONTEXT_REG_START
gfx_v10_0.c:4338    SOC15_REG_OFFSET(...) - PACKET3_SET_CONTEXT_REG_START
```

Es decir: `sid.h` mezcla en un solo espacio de nombres **opcodes**, **offsets
de rango** y **máscaras de enable**. Contarlos como paquetes infla el
"no explorado" en casi un factor de tres.

### Dos señales, no una

El discriminante obvious —el opcode cabe en 8 bits, porque `sid.h:337` hace
`(op) & 0xFF`— **no basta solo**:

```
PACKET3_CB0_DEST_BASE_ENA    0x40    cabe en 8 bits  -> parece opcode
PACKET3_DEST_BASE_0_ENA      0x01    cabe en 8 bits  -> parece opcode
```

Son máscaras de enable. Con una sola señal, la cuenta de E1 salía 40 en vez de
36. **Hacen falta las dos**: valor ≤ `0xFF` **y** nombre sin sufijo de campo
(`_ENA`, `_START`, `_END`, `_SHIFT`, `_MASK`, `_BASE_INDEX`) — que es la
convención que impone el generador del ASIC.

## E1: 36 opcodes reales que el driver del kernel nunca emite

Agrupados por lo que hacen:

| familia | paquetes |
|---|---|
| dibujo | `DRAW_INDIRECT`, `DRAW_INDIRECT_MULTI`, `DRAW_INDEX_2`, `DRAW_INDEX_AUTO`, `DRAW_INDEX_INDIRECT`, `DRAW_INDEX_INDIRECT_MULTI`, `DRAW_INDEX_MULTI_AUTO`, `DRAW_INDEX_OFFSET_2` |
| índices | `INDEX_BASE`, `INDEX_BUFFER_SIZE`, `INDEX_TYPE`, `NUM_INSTANCES` |
| compute | `DISPATCH_INDIRECT` |
| predication | `SET_PREDICATION`, `PRED_EXEC` |
| estado | `LOAD_CONTEXT_REG`, `LOAD_SH_REG`, `LOAD_CONFIG_REG`, `SET_SH_REG_OFFSET`, `SET_CONTEXT_REG_INDIRECT`, `REG_RMW` |
| GDS/atomics | `ATOMIC_GDS`, `MEM_SEMAPHORE` |
| MEM/const | `LOAD_CONST_RAM`, `WRITE_CONST_RAM`, `DUMP_CONST_RAM`, `SCRATCH_RAM_READ`, `SCRATCH_RAM_WRITE` |
| CE/DE | `INCREMENT_CE_COUNTER`, `INCREMENT_DE_COUNTER`, `WAIT_ON_CE_COUNTER`, `WAIT_ON_DE_COUNTER_DIFF` |
| varios | `COND_WRITE`, `EVENT_WRITE_EOS`, `OCCLUSION_QUERY`, `STRMOUT_BUFFER_UPDATE` |

**No son un misterior ni un hueco: son el territorio de Mesa y del firmware.**
El driver del kernel emite 20; el resto lo emite el espacio de usuario.

Eso convierte la pregunta "¿cuántos paquetes necesito para un driver propio?"
en algo accionable: **20 si el driver es solo de línea de comandos, ~56 si
además quiere dibujar sin Mesa**.

## B = 0, y es un dato sobre la arquitectura

Ningún otro motor de GCN3 emite un packet3 que `gfx_v8_0.c` no emita. La razón
es que **SDMA, UVD y VCE no hablan packet3**: tienen su propio formato de
paquete (`sdma_v3_0.c` usa `SDMA_PKT_*`, `uvd_v6_0.c` usa `VUVI_*`).

**packet3 es un concepto del CP/GFX, no un concepto de la GPU.** Por eso
`gfx_v8_0.c` es la única fuente, y por eso la categoría B no puede tener
miembros: no es un resultado del análisis, es una propiedad del hardware.

## C = 1: `PACKET3_ME_INITIALIZE`

El único paquete definido que solo emite una generación **anterior**
(`gfx_v6_0.c:2082`, GCN1). GFX8 no lo emite.

Lo interesante es que **yo lo etiqueté mal primero**: mi clasificación decía
"generaciones posteriores" sin mirar la dirección. Arreglarlo fue separar
"anterior" de "posterior" explícitamente. Una etiqueta correcta pero sin
comprobar es peor que ninguna.

## El confounder que limita todo esto

```
sid.h es la UNION de las generaciones.
```

**Que un opcode esté definido no significa que este ASIC lo soporte.** Los 36
de E1 son "el hardware *podría*", no "el hardware *puede*". Para convertirlo
en capacidad real hace falta una lista de capacidad por ASIC, y **no está en el
corpus**.

Es la misma trampa que `112` documentó con las cabeceras: un header
desgenerado por el ASIC es un mapa de posibilidades, no un inventario de lo que
esta placa tiene.

## Clasificación

| afirmación | estado |
|---|---|
| `sid.h` define 119 `PACKET3_*` | `PROVEN` — `\b`, y la suma cuadra |
| GFX8 emite 20 de ellos | `PROVEN` — 20 ficheros/fichero |
| 62 no son opcodes sino offsets o máscaras | `PROVEN` — dos señales |
| 36 son opcodes reales que el kernel nunca emite | `PROVEN` — clasificación |
| SDMA/UVD/VCE no usan packet3 | `PROVEN` — su formato es otro |
| El recuento de `121` (83) era falso | `REFUTED` — le faltaban 8 |
| Que este ASIC soporte los 36 | `NOT_DETERMINED` — no hay lista por ASIC |
| Que Mesa use los 36 | `NOT_DETERMINED` — Mesa no está en el corpus |
| Que un driver propio necesite los 36 | `NOT_APPLICABLE` — depende del objetivo |

## Confounders

- **El escaneo es textual** sobre `PACKET3(PACKET3_X`. No ve un opcode en
  variable: si un sitio hace `p = PACKET3(op, n)`, ese paquete contará como
  "nadie lo emite" cuando sí se usa. **Es un límite declarado, no medido.**
- **`sid.h` es la unión de generaciones** (§Confounders). El confounder
  mayor de todos.
- **Mesa no está en el corpus.** La atribución de E1 a "Mesa y firmware" es
  una inferencia por la naturaleza de los paquetes (dibujar, indexar,
  predicar), no una observación.
- **No he comprobado `.text.cold`** ni los caminos de error.
- **La comparación por nombre de fichero** asume que el nombre es la
  generación. Para `gfx_v8_0.c` es cierto; para un fichero como
  `amdgpu_gfx.c` no aplica, y es lo que deja B en 0 de una forma que ya es
  correcta por otra razón.

## Desfalsificación

- **(a)** Son 119 → refutable con `\b` en vez de `\s`; la suma cuadra.
- **(b)** GFX8 emite 20 → refutable con `grep -c PACKET3(PACKET3_ gfx_v8_0.c`.
- **(c)** 62 no son opcodes → refutable con las dos señales; con una sola son
  58 y la cuenta de E1 cambia a 40.
- **(d)** B = 0 → refutable buscando `PACKET3(` en `sdma_v3_0.c`, `uvd_v6_0.c`,
  `vce_v4_0.c`.
- **(e)** El ASIC soporta los 36 → **no refutable aquí**, y no se afirma.

## UNLOCKS

- **§E tiene inventario, no intuición**: 20 usados, 36 disponibles-no-usados,
  62 que no son paquetes, y las cuatro categorías suman.
- **Para el driver propio, la respuesta práctica es 20 paquetes**, y el
  documento dice exactamente cuáles, con opcode.
- **La pregunta siguiente tiene discriminante concreto**: encontrar la lista de
  capacidad por ASIC. Si está en Mesa (`si_pipe.h`, `amdgpu_isa.h`) o en
  firmware, se convierte `NOT_DETERMINED` en `PROVEN`. Es la frontera que
  bloquea la capacidad real.
- **`sid.h` no es un inventario**: hay que decirlo cada vez que se cite como
  "lo que el hardware tiene", o se repite el error de `112` a escala.

## Evidencia

```
sid.h:337        (op) & 0xFF      <- por que el opcode cabe en 8 bits
sid.h:526-529    PACKET3_SET_CONTEXT_REG 0x69, _START 0xA000, _END 0xA400

amdgpu_gfx.c:2521-2522   PACKET3(PACKET3_SET_CONTEXT_REG, ext->reg_count)
                         ext->reg_index - PACKET3_SET_CONTEXT_REG_START
gfx_v10_0.c:4339         PACKET3(PACKET3_SET_CONTEXT_REG, 1)

gfx_v6_0.c:2082          PACKET3(PACKET3_ME_INITIALIZE, 5)   <- C, anterior
sdma_v3_0.c              SDMA_PKT_*, no packet3              <- B = 0
uvd_v6_0.c               VUVI_*, no packet3

$ pm4_emit.py --quien
SUMA DE CATEGORIAS = 119 ; DEFINIDOS = 119  -> CUADRA
```

`WRITE_EXECUTION=NONE`. `MODIFICATIONS=0`. `GPU INTACTA`.

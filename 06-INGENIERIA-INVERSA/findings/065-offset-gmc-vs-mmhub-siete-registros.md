# 065 · Siete registros de GMC tienen direcciones distintas en MMHUB, y el `#include` decide cuál

```
CLASSIFICATION=DOCUMENTATION · TRACK=STATIC · CORPUS=RESEARCH/working/linux-7.1.3
HARDWARE_SCOPE=HOST-C/RX550/0000:01:00.0 · WORK_CLASS=READ_ONLY/EVIDENCE
WRITE_EXECUTION=NONE · MODIFICATIONS=0 · RUNTIME=NOT_RUN · GPU INTACTA
```

## Qué resuelve

`VM_CONTEXT0_CNTL` está en `0x504` según la cabecera de GMC y en `0xba0` según
la de MMHUB. **No son dos registros: es el mismo registro con dos direcciones
en dos familias de cabecera distintas.** Un driver propio que copie un offset
de la familia equivocada escribe en otro registro del ASIC sin ninguna señal de
error.

Esto no es hipotético en esta sesión: yo leí el mapa de bits de `VM_CONTEXT*_CNTL`
en `mmhub_1_8_0_sh_mask.h` y publiqué un hallazgo con `PAGE_TABLE_BLOCK_SIZE` en
los bits equivocados. El `#include` lo zanja, pero había que ir a buscarlo.

## Los siete, con sus dos direcciones

```
  registro                  GMC 8.1        MMHUB 1.8
  MC_VM_MX_L1_TLB_CNTL      0x819          0x0ca3
  VM_CONTEXT0_CNTL          0x504          0x0ba0
  VM_CONTEXT1_CNTL          0x505          0x0ba1
  VM_L2_CNTL                0x500          0x0b60
  VM_L2_CNTL2               0x501          0x0b61
  VM_L2_CNTL3               0x502          0x0b62
  VM_L2_CNTL4               0x578          0x0b77
```

Los ceros del lado MMHUB son como aparecen en el fichero, no una normalización
mía: GMC escribe `0x819` y MMHUB escribe `0x0ca3`. La herramienta compara
normalizando (`regdb._norm`), porque `0xca3` y `0x0ca3` son el mismo número y
declarar un conflicto ahí sería un falso positivo que entrenaría a ignorar sus
avisos reales.

Las diferencias no son de un campo suelto: **son la dirección base del bloque de
registros de la MMU**. `0x500..0x505` y `0x578` en GMC contra `0xb60..0xb62`,
`0xb77`, `0xba0..0xba1` en MMHUB. El bloque está reubicado entero.

De los **14 registros** que `gmc_v8_0.c` escribe, 7 tienen dirección distinta
según la familia, 6 coinciden y 1 (`BIF_FB_EN`) no aparece en ninguna de las
cabeceras GMC revisadas. Barrido reproducible con una orden:

```
regdb.py --scan-file .../amdgpu/gmc_v8_0.c
```

## Cuál de las dos manda: el `#include`, no la opinión

La decisión no es interpretativa. Está escrita en el fichero:

```
gmc_v8_0.c:35   #include "gmc/gmc_8_1_d.h"
gmc_v8_0.c:36   #include "gmc/gmc_8_1_sh_mask.h"
```

El fichero que compila **incluye GMC 8.1**, luego los offsets que aplica son los
de la columna GMC: `0x504` para `VM_CONTEXT0_CNTL`, y así con los siete. Los
valores de MMHUB describen una generación anterior donde el bloque vivía en otra
dirección del mapa.

Que MMHUB 1.8 sea también "Tonga" es lo que hace el error posible: son la misma
generación comercial con el bloque en distinto sitio, y el nombre de la familia
no lo dice.

**Y esto corrige algo que dije en 064.** Ahí escribí que `gmc_8_2` era la
cabecera autoritativa de Polaris12 por ser "más específica". Es cierto para
comparar revisiones de GMC entre sí, pero **no** es la que usa este fichero: el
driver incluye `gmc_8_1`. Los dos headers coinciden en `PAGE_TABLE_DEPTH` y en
`PAGE_TABLE_BLOCK_SIZE`, así que 064 no tenía un error numérico, pero sí tenía
la regla equivocada para elegir cabecera. La regla correcta es: **la cabecera
que incluye el `.c`**.

Que el ASIC instanciado sea `gmc_8_1` en vez de `gmc_8_2` no lo he tracedo en
`vi.c`; queda `NOT_DETERMINED`. No hace falta para el hallazgo: lo que decide el
offset es el include, y el include está escrito.

## Por qué la familia importa y no sólo la revisión

GFX8 tiene seis familias de cabecera de registro y un mismo nombre lógico
aparece en varias con direcciones distintas:

```
  gmc_8_1_d.h:601            #define mmVM_CONTEXT0_CNTL    0x504
  mmhub_1_8_0_offset.h:2660  #define regVM_CONTEXT0_CNTL  0xba0
```

El prefijo delata el origen: **`mm` para GMC, `reg` para MMHUB**. Es la única
pista visible en el propio define, y basta para clasificar cualquier `#define`
de offset sin abrir la cabecera. Un `regVM_*` y un `mmVM_*` con el mismo sufijo
son registros distintos por definición.

Esto es lo que faltaba como herramienta. `gmmio_inventory.py` inventaría una
familia (GMC) y resuelve ahí, así que no puede encontrar la discrepancia: no
compara contra la familia con la que discrepa. Aquí hace falta el barrido
cruzado, y por eso es otra herramienta y no una extensión.

## Método: por qué no se vio antes

Rastrear "quién escribe `PAGE_TABLE_DEPTH`" da las dos escrituras correctas, y
la herramienta que las clasifica (`causal.py`) devuelve los sitios sin tocar la
cabecera de donde salió el valor. El valor y su fuente viajan separados: el
`xref` te dice qué línea se escribe, no de qué `.h` salió el número.

La consulta que faltaba es "¿este offset coincide en las familias donde aparece
el nombre?". Es la que automatiza `regdb.py`, y el fallo de esta sesión era
justo no hacerla.

## Límites declarados

- **No decide cuál cabecera es la correcta.** Detecta discrepancias y nombra las
  familias; la elección sale del `#include`, que es evidencia, no del programa.
- **No resuelve macros ni sigue `#include`s.** Un campo presente sólo por
  expansión no aparece.
- **Sólo revisa las 6 familias GFX8 declaradas.** Un nombre que exista fuera de
  ellas no se busca, y se reporta como ausente, no como inexistente.
- **Un define sin valor no cuenta.** En `mmhub_1_8_0_sh_mask.h` el valor de los
  `_SHIFT` estáseparado por mucho espacio y el patrón no lo captura; los
  `_MASK` sí se capturan. Un campo definido sólo con `_SHIFT` y sin `_MASK`
  podría no verse. No he comprobado si alguno de los 7 cae en ese caso: para los
  offsets no importa, y para los campos uso `gmc_8_1_sh_mask.h` donde no hay
  espaciado.

## Estado

| Afirmación | Estado | Evidencia |
|---|---|---|
| 7 registros tienen dirección distinta GMC/MMHUB | `PROVEN` | barrido sobre `gmc_8_0.c` |
| Los offsets aplicados son los de GMC 8.1 | `PROVEN` | `#include` textual |
| `mm` = GMC, `reg` = MMHUB | `PROVEN` | los dos defines citados |
| 6 de 14 registros coinciden entre familias | `PROVEN` | mismo barrido |
| `BIF_FB_EN` no está en las cabeceras GMC | `PROVEN_ABSENT` | recuento en 4 cabeceras |
| Por qué el ASIC usa 8_1 y no 8_2 | `NOT_DETERMINED` | falta trazar `vi.c` |
| Semántica de hardware de los campos | `NOT_DETERMINED` | fuera de alcance |

`BIF_FB_EN` es de BIF, no de GMC: su ausencia aquí es lo esperado y lo anoto
para que no se lea como un hueco. Vale como comprobación de que el barrido no
inventa: un nombre ajeno a la familia no aparece, en lugar de devolver algo
parecido.

## Procedencia

- `CORPUS` — `gmc_8_1_d.h`, `mmhub_1_8_0_offset.h`, `gmc_v8_0.c`, includes.
- Herramienta: `regdb.py`, 21 casos de self-test, incluido el caso que motivó
  construirla.
- Sin `RUNTIME`, sin lectura de la GPU, sin escrituras.
- No se editó 064: son ambos de esta sesión y el error de 064 está anotado aquí
  y en 064; se deja constancia en lugar de reescribir.
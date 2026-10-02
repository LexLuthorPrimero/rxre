# 043 · **Vuelta atrás: `035` y `036` estaban equivocados, y la herramienta lo encontró solo**

`CLASSIFICATION=CORRECTION` · `TRACK=STATIC` · `GPU INTACTA` · `RUNTIME=NOT_RUN`
`RETRACTS=035, 036 y parte de 037` · `CAUSA=NO-SE-VIO-QUE-CUAL-ASIC-CORRE`
`CERRADO_POR=046` — **el `NOT_DETERMINED` que este documento dejó abierto —"¿qué versión de
`SDMA0_HWIP` tiene esta tarjeta?"— era la pregunta equivocada.** No hace falta leer el registro,
porque el código que lo consultaría no se ejecuta para este chip. La versión de SDMA no llega a
leerse, así que su valor no puede cambiar ninguna conclusión. Demostrado por alcanzabilidad, sin
MMIO, en `046-la-version-de-ip-que-nunca-se-consulta.md`. La retracción de `035`/`036` se
mantiene íntegra: `sdma_v3_0.c` es el fichero correcto.

## CUDA principal

Construí `which_hw.py` para responder "¿qué hardware tiene esta GPU?" y la respuesta fue
**"el que yo no estaba leyendo"**.

`CHIP_POLARIS12` está en el `case` de `vi.c`, que llama a `vi_set_ip_blocks()`. Ese `case`
añade:

```c
/* vi.c:2107-2123 */
case CHIP_POLARIS12:
case CHIP_VEGAM:
        amdgpu_device_ip_block_add(adev, &vi_common_ip_block);
        amdgpu_device_ip_block_add(adev, &gmc_v8_1_ip_block);
        amdgpu_device_ip_block_add(adev, &gfx_v8_0_ip_block);
        amdgpu_device_ip_block_add(adev, &sdma_v3_1_ip_block);   <-- v3, no v4
        ...
```

**`sdma_v3_1_ip_block`, no `sdma_v4_0_ip_block`.** Y en `amdgpu_device.c:2145-2153` el switch
es `case`/`default`, o sea **mutuamente excluyente**: para `CHIP_POLARIS12` se ejecuta
`vi_set_ip_blocks()` y **nunca** `amdgpu_discovery_set_ip_blocks()`, que es la ruta que
enruta `SDMA0_HWIP 4.x` a `sdma_v4_0_ip_block` (`amdgpu_discovery.c:2549-2560`).

`sdma_v3_1_ip_block` está definido en **`sdma_v3_0.c:1693`** con `.funcs =
&sdma_v3_0_ip_funcs`. Distinto fichero, distinta tabla de funciones.

**Consecuencia directa: el productor de PTEPDE que implementé en `036` es el del ASIC
equivocado.**

```c
/* sdma_v3_0.c:986 — el que CORRE en Polaris12 */
ib->ptr[ib->length_dw++] = SDMA_PKT_HEADER_OP(SDMA_OP_GEN_PTEPDE);
...
ib->ptr[ib->length_dw++] = count;          /* NO count - 1 */

/* sdma_v4_0.c:1649-1658 — el que implementé */
ib->ptr[ib->length_dw++] = SDMA_PKT_HEADER_OP(SDMA_OP_PTEPDE);
...
ib->ptr[ib->length_dw++] = count - 1;
```

**Yo "corregí" `023` de `count` a `count - 1`. La corrección iba en la dirección
equivocada**: `023` leía `sdma_v3_0.c` —el fichero correcto para este ASIC— y yo leí
`sdma_v4_0.c`, que no corre aquí. `023` acertaba el `count`; yo lo cambié a `count - 1` por
leer un ASIC que no usa esta GPU.

## Lo que queda en pie y lo que cae

| afirmación | fuente | estado |
|---|---|---|
| el productor de PTE es un paquete sDMA de 10 dwords | ambos ficheros coinciden | **`PROVEN`** |
| opcode = 12 | `GEN_PTEPDE=12` y `PTEPDE=12` | **`PROVEN`** |
| el campo de entradas es `count` | `sdma_v3_0.c:996` | **`PROVEN` en el ASIC real** |
| el campo de entradas es `count - 1` | `sdma_v4_0.c:1658` | `PROVEN` para v4, **no aplica a Polaris12** |
| el nombre del opcode es `SDMA_OP_PTEPDE` | `vega10_sdma_pkt_open.h` | **`REFUTED` para este ASIC**: el nombre aquí es `SDMA_OP_GEN_PTEPDE` |
| la cabecera de paquete es un byte en `[7:0]` | ambos | **`PROVEN`** |
| PTBA son dos tramos (037) | `gmc_v8_0.c` | **`PROVEN`**: `gmc_v8_1_ip_block` comparte `gmc_v8_0_ip_funcs` (`gmc_v8_0.c:1762-1768`) |
| vm-flush, coherencia, INDIRECT | `gfx_v8_0.c` | **`PROVEN`**: el case sí añade `gfx_v8_0_ip_block` |

**El caso GMC es distinto del SDMA y por eso 037 se salva.** `gmc_v8_1_ip_block` está
definido en `gmc_v8_0.c` con `.funcs = &gmc_v8_0_ip_funcs` — el *mismo* fichero y la *misma*
tabla que `gmc_v8_0_ip_block` y `gmc_v8_5_ip_block`. Lo único que distingue a los tres es
`major/minor`. **Polaris12 ejecuta el código de `gmc_v8_0.c`.** Por eso todo lo de `037` y
`040` sigue válido, y por eso la regla no se aplica igual a los dos casos: uno se salva y el otro no.

## El error de método, que es lo importante

Esto no es un error de búsqueda. Es un error de **pregunta no hecha**. En `035`/`036`/`037`
nunca verifiqué *qué fichero* implementa este ASIC. Pregunté "¿cómo escribe un PTE el driver?"
y respondí con el primer fichero que encontré que lo hacía.

Ese es el patrón que ya documenté dos veces por otra vía:

- `035`: cité el ASIC equivocado (Tonga en vez de Polaris12) → corregido
- `037`: truncé un `grep` con `head` → corregido
- **esto**: no verifiqué que el fichero fuera de este ASIC

Los tres son **el mismo error**:aceptar una fuente plausible sin comprobar su procedencia. Y
los tres desembocaron en lo mismo: un número plausible y equivocado que compila.

**La herramienta que faltaba no era un buscador melhor. Era una que respondiera "¿este
fichero es de mi ASIC?"** y `which_hw.py` es exactamente eso, y encontró el error en su
primera ejecución.

## `amdgpu_device_ip_block_add` y el orden

La función (`amdgpu_ip.c:221-252`) **no rechaza duplicados**: añade a
`adev->ip_blocks[num_ip_blocks++]` sin comprobar el `type`. Y `amdgpu_ip.c:150-151` devuelve
**el primero** que encuentra con el `type` pedido:

```c
for (i = 0; i < adev->num_ip_blocks; i++)
        if (adev->ip_blocks[i].version->type == type)
                return &adev->ip_blocks[i];
```

Eso no importa aquí porque el switch es excluyente, pero **sí importa para un driver propio**:
si un driver añade dos bloques del mismo `type`, el segundo es inalcanzable sin aviso. Es un
requisito, no una curiosidad.

## Consequences for the own driver

`rx550_sdma_vm_set_pte_pde()` tiene el `count - 1` equivocado y hay que corregirlo a `count`.
Pero **no lo corrijo todavía**, y el motivo importa:

`SDMA_OP_GEN_PTEPDE = 12` y `SDMA_OP_PTEPDE = 12`, y el valor del byte en `[7:0]` es
idéntico. **Los dos paquetes empiezan con el mismo dword.** La diferencia entre `count` y
`count - 1` es el dword 9, y no hay forma de saber desde el corpus cuál de los dos campos
espera el hardware **de esta tarjeta concreta** sin:
1. saber qué versión de SDMA tiene (lectura de `SDMA0_HWIP`), y
2. el spec de GFX8, que `033` ya estableció que **no está publicado**.

**Actualizado por `046`:** el punto (1) de la lista —la versión de `SDMA0_HWIP`— **no hace
falta**, y queda retirado como `BLOCKED`. La versión de SDMA no llega a leerse para este chip, y
por tanto su valor no puede cambiar nada. El punto (2) —el spec de GFX8— sigue en pie: `033`
estableció que no está publicado, y nada de lo que hay aquí lo cambia.

Lo que sí es `PROVEN` es que **el software de amdgpu para este ASIC escribe `count`**, y ese
es el mejor punto de partida disponible sin hardware. Un driver propio debería seguir al
driver de referencia, que es lo que `AGENTS.md` §"IMPLEMENTATION GATE" pide cuando no hay
spec: `REQUIREMENT` derivado de la evidencia, no de la conjetura.

## UNLOCKS

- `which_hw.py` cierra la pregunta "¿qué fichero es de mi ASIC?" de forma automática, y
  encontró este error sin que yo lo buscara. Es la herramienta de mayor valor del
  proyecto hasta ahora, y no por lo que dice sino por lo que dejó de decir.
- Falta el equivalente para "qué registro **y** qué generación": `reg_resolve` da el offset
  pero no dice si el `.c` que lo usa es de este ASIC. Es la extensión natural.
- El mapa real de "fichero → ASIC" está ahora medido, no supuesto, y es pequeño: para
  Polaris12, `gmc_v8_1_ip_block`→`gmc_v8_0.c`, `sdma_v3_1_ip_block`→`sdma_v3_0.c`,
  `gfx_v8_0_ip_block`→`gfx_v8_0.c`.

## Falsación

- La conclusión se refuta si `vi_set_ip_blocks()` no se llama para `CHIP_POLARIS12`, o si
  `amdgpu_discovery_set_ip_blocks()` también se llama y añade un segundo bloque SDMA que
  *sí* se usa. El switch en `amdgpu_device.c:2145-2153` es excluyente y `amdgpu_ip.c:150`
  devuelve el primero, así que haría falta que ambos se ejecutaran.
- `count` vs `count - 1` se resuelve con la spec o con un experimento. Ninguno disponible.
  Se registra como `PROVEN_DERIVED` (el software de referencia escribe `count`) y no como
  `PROVEN` sobre el hardware.

## Evidencia

```
vi.c:2107-2123          el case de CHIP_POLARIS12, con sdma_v3_1_ip_block
amdgpu_device.c:2145    el switch: case VI -> vi_set_ip_blocks, default -> discovery
amdgpu_ip.c:221-252     add no rechaza duplicados
amdgpu_ip.c:150-151     el primero con el type gana
sdma_v3_0.c:1693        sdma_v3_1_ip_block, .funcs = sdma_v3_0_ip_funcs
sdma_v3_0.c:986-996     el productor REAL: GEN_PTEPDE, count plano
sdma_v4_0.c:1649-1658   el que implementé: PTEPDE, count-1  (no corre en Polaris12)
gmc_v8_0.c:1754-1768    gmc_v8_0/v8_1/v8_5 comparten gmc_v8_0_ip_funcs
which_hw.py             5 bloques resueltos con fichero y .funcs
corpus:                 MODIFICATIONS=0, sha256 12e8d5a973d1ad7c…c3e51941
```

Ningún registro leído de MMIO. `insmod` no ejecutado. `GPU INTACTA`.

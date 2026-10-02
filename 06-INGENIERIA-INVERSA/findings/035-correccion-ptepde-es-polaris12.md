# 035 · Corrección de `023`: en Polaris12 el opcode es `SDMA_OP_PTEPDE` y el campo de entrada va **menos uno**

`CLASSIFICATION=CORRECTION` · `TRACK=STATIC` · `CORRECTS=023` · `ERROR_TYPE=ASIC_LEER_ANTES_DE_TIME`
`RETRACTED_BY=043` — **esta corrección estaba en la dirección equivocada.** El ASIC que corre
es el de `sdma_v3_0.c`; yo leí el de `sdma_v4_0.c`, y por eso "corregí" un `count` que era
correcto a un `count - 1` que no lo es. La correlación con `023` era aparente, no causal:
los dos leen ficheros distintos, y la lectura del equivocado parecía la buena porque
`sdma_v4_0.c` es más reciente y más especifico en el nombre. El error de este documento no
fue de búsqueda sino de no preguntar qué fichero corre en esta GPU.
`CORPUS=rx550-upstream-7.2.8/linux-7.2.8` · `GPU INTACTA` · `MODIFICATIONS=0`

## CUDA principal

`023` leyó el productor de PTE del **fichero equivocado**: `sdma_v3_0.c`, que es Tonga/CIK
(GCN1/GCN3), no Polaris12. El fichero del ASIC de este proyecto es `sdma_v4_0.c`. De ahí
salen tres correcciones, y **una de ellas es un off-by-one que corrompe memoria**:

| campo | Tonga `sdma_v3_0.c:982-996` | **Polaris12 `sdma_v4_0.c:1643-1659`** |
|---|---|---|
| nombre del opcode | `SDMA_OP_GEN_PTEPDE` | **`SDMA_OP_PTEPDE`** |
| valor | 12 | **12** (igual) |
| último dword | `count` | **`count - 1`** |
| total dwords | 10 | **10** |

Las dos primeras son cosméticas. **La tercera no**: un driver propio que copie `023`
escribiría `count` donde el hardware de este ASIC espera `count - 1`, y programaría
**una entrada de más** — un PTE por encima del final del rango pedido.

## Las tres correcciones, con el por qué de cada una

### C1 · El opcode se llama `SDMA_OP_PTEPDE`, no `SDMA_OP_GEN_PTEPDE`

Mismo valor, distinto nombre. Reparto real en el corpus:

```
SDMA_OP_GEN_PTEPDE = 12   iceland_sdma_pkt_open.h:37   (Iceland, GCN3)
SDMA_OP_GEN_PTEPDE = 12   tonga_sdma_pkt_open.h:37     (Tonga,  GCN3)
SDMA_OP_PTEPDE     = 12   navi10_sdma_pkt_open.h:37    (Navi10, RDNA1)
SDMA_OP_PTEPDE     = 12   vega10_sdma_pkt_open.h:37    (Vega10, GCN5)
SDMA_OP_PTEPDE     = 12   sdma_v6_0_0_pkt_open.h:37   (MI200)
SDMA_OP_PTEPDE     = 12   sdma_v7_1_0_pkt_open.h:37   (MI300)
```

La línea `023` citó, literalmente, `tonga_sdma_pkt_open.h:37` — el header de otro ASIC, y
además cites el que el propio `023` identificó como el equivocado si se hubiera limitado a
`sdma_v3_0.c:48`. Lo comprobé: `sdma_v3_0.c:48` incluye `tonga_sdma_pkt_open.h`. O sea, la
cita era *consistente* con el fichero leído, y el fichero leído era el equivocado. Por eso
esto no lo detecta ninguna comprobación interna del documento: la cita verifica, el ASIC no.

### C2 · Polaris12 usa las definiciones de paquete de **Vega10**

`sdma_v4_0.c:53` incluye `vega10_sdma_pkt_open.h`. El bloque IP de SDMA es compartido entre
Polaris12 y Vega10, así que el ASIC de este proyecto toma sus opcodes de la cabecera que
lleva el nombre de otro chip. **`vega10_sdma_pkt_open.h:37` es la cita correcta** para
Polaris12, y nominalmente es la fuente equivocada.

El despacho no es por nombre de ASIC sino por versión de IP
(`amdgpu_discovery.c:2549-2560`):

```c
switch (amdgpu_ip_version(adev, SDMA0_HWIP, 0)) {
case IP_VERSION(4, 0, 0): ... case IP_VERSION(4, 2, 2): case IP_VERSION(4, 4, 0):
        amdgpu_device_ip_block_add(adev, &sdma_v4_0_ip_block);
```

Así que la afirmación correcta y completa es: **para cualquier `SDMA0_HWIP` de 4.0.0 a 4.4.0,
el productor de PTE es `sdma_v4_0_vm_set_pte_pde`**. No hace falta saber la versión exacta de
este chip para afirmar la codificación. `LIMITATION`: no he leído `SDMA0_HWIP` del host —
sería una lectura de MMIO sin discriminante pendiente, así que no la hago. El rango cubre
GFX8 entero.

### C3 · `count - 1`, y por qué importa

```c
/* sdma_v4_0.c:1643-1659, verbatim */
static void sdma_v4_0_vm_set_pte_pde(struct amdgpu_ib *ib,
				     uint64_t pe,
				     uint64_t addr, unsigned count,
				     uint32_t incr, uint64_t flags)
{
	/* for physically contiguous pages (vram) */
	ib->ptr[ib->length_dw++] = SDMA_PKT_HEADER_OP(SDMA_OP_PTEPDE);
	ib->ptr[ib->length_dw++] = lower_32_bits(pe); /* dst addr */
	ib->ptr[ib->length_dw++] = upper_32_bits(pe);
	ib->ptr[ib->length_dw++] = lower_32_bits(flags); /* mask */
	ib->ptr[ib->length_dw++] = upper_32_bits(flags);
	ib->ptr[ib->length_dw++] = lower_32_bits(addr); /* value */
	ib->ptr[ib->length_dw++] = upper_32_bits(addr);
	ib->ptr[ib->length_dw++] = incr; /* increment size */
	ib->ptr[ib->length_dw++] = 0;
	ib->ptr[ib->length_dw++] = count - 1; /* number of entries */
}
```

Y el Tonga, para contrastar, `sdma_v3_0.c:996`:

```c
	ib->ptr[ib->length_dw++] = count; /* number of entries */
```

Los otros dos productores de la misma ASIC usan el mismo convenio "menos uno":

```
sdma_v4_0_vm_copy_pte   :1585  ib->ptr[1] = bytes - 1;   /* bytes = count * 8 */
sdma_v4_0_vm_write_pte  :1623  ib->ptr[3] = ndw - 1;     /* ndw  = count * 2 */
```

Tres de tres. En Tonga, sólo `set_pte_pde` usa `count` a secas. **El convenio cambió entre
generaciones y `023` heredó el viejo.** Esto no es una diferencia de nombre: es la clase de
error que corrompe memoria sin producir ningún síntoma, porque la entrada de más cae en la
siguiente entrada de la tabla, que en GFX8 es válida.

`023` §"Criterio de terminación (cumplido)" decía `PROVEN` que no hay un tercer productor.
Eso **sigue en pie**: `sdma_v4_0_sdma_funcs` (`:1755-1758`) tiene exactamente tres,
`copy_pte`, `write_pte`, `set_pte_pde`, los mismos tres con otro nombre de fichero. Lo que
cae es la codificación, no el conjunto.

## Lo que `023` acertó y no se toca

| afirmación | estado |
|---|---|
| el writer efectivo de GPUVM es SDMA, no CPU | `PROVEN`, sin cambio |
| la CPU writer existe y es `writeq` a `ptr + idx*8` | `PROVEN`, sin cambio |
| `PRT` es aperture, no tipo de entrada, en GFX8 | `PROVEN`, sin cambio |
| GART y GPUVM tienen reglas de inalcanzabilidad distintas | `PROVEN`, sin cambio |
| `PAGE_TABLE_BLOCK_SIZE` depende de la RAM del host | `PROVEN`, sin cambio |
| no hay un tercer productor | `PROVEN`, sin cambio |
| opcode 12 | `PROVEN`, sin cambio |

## Por qué no lo detecté entonces

Porque era un error de *ASIC*, no de lectura. `023` verificó que la cita correspondía al
fichero que había abierto (`sdma_v3_0.c:48` → `tonga_sdma_pkt_open.h:37`): exacto. Lo que no
verificó es que `sdma_v3_0.c` sea el fichero de *esta* GPU. Es el mismo patrón que `030`:
**una referencia correcta a la fuente equivocada**. Dos veces, en el mismo dominio, con la
misma causa: el árbol de amdgpu tiene un fichero por generación de ASIC con nombres casi
idénticos, y `sdma_v3_0.c` / `sdma_v4_0.c` se leen como consecutivos.

Regla que se sigue de aquí, y que queda escrita para no repetirlo: **antes de citar un
`.c` de amdgpu, hay que demostrar que su IP block es el de este ASIC**, por el despacho
de `amdgpu_discovery.c` o por la tabla de `*_funcs` que lo referencia. El nombre del fichero
no es evidencia. Aquí se podía hacer estáticamente en dos líneas.

## Consecuencias para el driver propio

Cambia la especificación del emisor de PTE que hay que escribir:

```
ANTES (023, incorrecto):  SDMA_PKT_HEADER_OP(SDMA_OP_GEN_PTEPDE)
                          ... 9 dwords más ...  total 10, último = count
AHORA (PROVEN):          SDMA_PKT_HEADER_OP(SDMA_OP_PTEPDE)      /* = 12 */
                          ... 9 dwords más ...  total 10, último = count - 1
```

Y añade un requisito que `023` no vio: **el paquete es un paquete SDMA, no un PACKET3.**

```
vega10_sdma_pkt_open.h:69-72
  SDMA_PKT_HEADER_op_offset 0
  SDMA_PKT_HEADER_op_mask   0x000000FF
  SDMA_PKT_HEADER_op_shift  0
  SDMA_PKT_HEADER_OP(x)     (((x) & 0x000000FF) << 0)
```

La cabecera es **un byte de opcode en bits 7:0 y nada más**: sin tipo de paquete, sin campo
de longitud, sin bit de compute. El dword de cabecera de `PTEPDE` es literalmente `0x0000000C`.
El codificador PACKET3 de `07-DRIVER/kernel/rx550_pm4.c` **no puede expresar este paquete**,
porque mete el opcode en bits 15:8 dentro de un tipo 3 con cuenta de 14 bits. Hacen falta
dos formatos de cabecera, no uno.

## UNLOCKS

- La especificación del emisor de PTE del driver propio queda sin ambigüedad: 10 dwords,
  opcode 12, último = `count - 1`, cabecera de un byte.
- `rx550_pm4.c` necesita un segundo constructor de cabecera, y esta corrección dice cuál.
- Los tres productores están verificados en el fichero correcto, lo que permite elegir entre
  ellos con criterio en vez de por costumbre.

## Criterio de falsación

Se refutaría si, para `SDMA0_HWIP` de este host, `amdgpu_discovery.c` seleccionase un
`ip_block` distinto de `sdma_v4_0_ip_block`. Eso se cierra leyendo `SDMA0_HWIP`, que es el
único punto pendiente y no requiere escribir nada. Alternativamente, si
`sdma_v4_0_vm_set_pte_pde` no estuviera en la tabla de `funcs` de la ASIC real
(`:1755-1758` la lista; el resto de la tabla no se ha verificado).

## Evidencia

```
sdma_v4_0.c:        53 (incluye vega10_sdma_pkt_open.h), 1643-1659 (set_pte_pde),
                    1585-1600 (copy_pte), 1613-1629 (write_pte), 1755-1758 (tabla funcs)
vega10_sdma_pkt_open.h:  37 (SDMA_OP_PTEPDE = 12), 69-72 (SDMA_PKT_HEADER_OP)
sdma_v3_0.c:        48 (incluye tonga_sdma_pkt_open.h), 982-996 (el equivalente equivocado)
tonga_sdma_pkt_open.h / iceland_...:  37 (SDMA_OP_GEN_PTEPDE = 12)
amdgpu_discovery.c:  2549-2560 (despacho por SDMA0_HWIP a sdma_v4_0_ip_block)
tarball:             12e8d5a973d1ad7c5a5c69882e4022b131ed715db7003fdcd760ddf8c3e51941
```

Ningún registro leído de MMIO. `RUNTIME=NOT_RUN`. `MODIFICATIONS=0` en el corpus.

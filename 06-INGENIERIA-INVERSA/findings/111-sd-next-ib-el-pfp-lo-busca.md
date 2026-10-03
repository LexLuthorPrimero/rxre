# 111 · §D CERRADO: el PFP busca el IB, y en el anillo sólo viaja el puntero

```
CLASSIFICATION=DOCUMENTATION · TRACK=STATIC + HOST_OBSERVATION
CORPUS=RESEARCH/working/linux-7.1.3 · HARDWARE_SCOPE=HOST-C/RX550/0000:01:00.0
WORK_CLASS=READ_ONLY/EVIDENCE · WRITE_EXECUTION=NONE · MODIFICATIONS=0
RUNTIME=OBSERVED_READ_ONLY · GPU INTACTA · sesión sway INTACTA
```

## Qué resuelve

`AGENTS.md` §D L417, literal:

```
Resolver PTBA → INVALIDATE → WAIT → PFP_SYNC_ME → next IB.
```

Los cuatro primeros están cerrados (`108` para la secuencia, `214` para los
motores). **Falta el quinto: `next IB`.** Esta nota lo cierra.

## El mecanismo: dos opcodes, según qué motor busca

```
gfx_v8_0.c:6075   u32 header, control = 0;
gfx_v8_0.c:6077   if (ib->flags & AMDGPU_IB_FLAG_CE)
gfx_v8_0.c:6078       header = PACKET3(PACKET3_INDIRECT_BUFFER_CONST, 2);
gfx_v8_0.c:6080       header = PACKET3(PACKET3_INDIRECT_BUFFER, 2);
gfx_v8_0.c:6082   control |= ib->length_dw | (vmid << 24);
gfx_v8_0.c:6091   amdgpu_ring_write(ring, header);
gfx_v8_0.c:6092   ...  ib->gpu_addr low
gfx_v8_0.c:6097   ...  upper_32_bits(ib->gpu_addr) & 0xFFFF
gfx_v8_0.c:6098   amdgpu_ring_write(ring, control);
```

```
sid.h   PACKET3_INDIRECT_BUFFER_CONST   0x31
sid.h   PACKET3_INDIRECT_BUFFER          0x3F
```

**Dos opcodes para la misma operación de "busca un IB", distinguidos por el
motor que lo ejecuta.** Con `AMDGPU_IB_FLAG_CE` lo busca el Command Engine; sin
el flag, lo busca el PFP.

**El ME no busca IBs.** No tiene opcode para eso. Ejecuta paquetes del flujo del
anillo (`WAIT_REG_MEM`, `PFP_SYNC_ME`) pero nunca consume un IB.

Eso es la respuesta a la pregunta de `214`: **un anillo, dos motores que ejecutan
del flujo, y sólo uno —el PFP— que además busca el trabajo.**

## Y en el anillo sólo viaja el puntero

`PACKET3(..., 2)` = cabecera + 3 dwords de payload. El IB completo **no está en
el anillo**: el anillo lleva su dirección y su longitud, y el PFP va a buscarla.

Decodificado el primer IB del ring vivo:

```
d0  0xC0023F00   cabecera: PKT3, type=0x3F (INDIRECT_BUFFER), count=2
d1  0x002FA000   ib->gpu_addr, parte baja
d2  0x00000001   ib->gpu_addr, parte alta
d3  0x06000158   control

control: length_dw = 344 dwords     (bits [23:0])
         vmid      = 6             (bits [27:24])
```

**Un IB de 344 dwords ocupa 4 dwords en el anillo.** El factor es de 86 a 1.

**Y eso confirma `094` desde el otro lado.** `094` habia medido
`.emit_ib_size = 4`, y yo lo habia tratado como un detalle de presupuesto. **Es la
consecuencia directa de que el trabajo no está en el anillo**: el anillo es un
índice de trabajo, no el trabajo.

**Para un driver propio es la distinción que decide el presupuesto:** si metes el
trabajo en el anillo, el anillo tiene que ser enorme y cada job consume dwords
de memoria de cola. Si mandas un puntero, el anillo es pequeño y constante, y el
trabajo vive donde tú decidas.

## Y el reparto en esta GPU, medido

Volcado de `/sys/kernel/debug/dri/0000:01:00.0/amdgpu_ring_gfx`:

| opcode | paquete | cuántos |
|---|---|---|
| `0x10` | `NOP` | 1601 |
| `0x47` | `EVENT_WRITE_EOP` (los fences) | **34** |
| `0x3C` | `WAIT_REG_MEM` | 10 |
| `0x22` | `COND_EXEC` | 9 |
| `0x3F` | `INDIRECT_BUFFER` (**PFP**) | **8** |
| `0x42` | `PFP_SYNC_ME` | **1** |
| `0x31` | `INDIRECT_BUFFER_CONST` (**CE**) | **0** |

**Ocho IBs, todos buscados por el PFP. El CE no busca ninguno.**

**Y `PFP_SYNC_ME` aparece una sola vez en todo el anillo**, no una por job. Eso
contradice lo que yo suponía en `108`, donde lo traté como parte de la secuencia
de cada vm_flush: si hubiera uno por vm_flush y hubiera 34 fences, habría más de
uno.

**Consecuencia:** los 34 `EVENT_WRITE_EOP` son de 17 pares —el dummy y el real de
`097`/`096`— y los 8 IBs son 8 jobs. **Un vm_flush por job, no uno por fence.**

**Y `0x31` en cero significa que `AMDGPU_IB_FLAG_CE` no se usa en esta GPU.** No
es que no exista el camino: existe, está implementado, y no se toma.

## La secuencia completa de §D L417, con lo que cada cosa ejecuta

```
  1. PTBA               emit_wreg(PAGE_TABLE_BASE_ADDR)     PFP   [068, 108]
  2. INVALIDATE_REQUEST emit_wreg(VM_INVALIDATE_REQUEST)    PFP   [068, 103, 104]
  3. WAIT_REG_MEM       FUNCTION(0), ENGINE(0)              ME    [108, 109]
  4. PFP_SYNC_ME        sincroniza                          PFP→ME [095, 108]
  5. next IB            INDIRECT_BUFFER, gpu_addr+len+vmid  PFP   [esta nota]
```

**Los pasos 1, 2 y 5 los busca PFP. El paso 3 lo ejecuta ME.** Y `108` acertó en
que 1 y 2 no necesitan espera entre ellos —porque los dos son de PFP— pero se
equivocó al darlo por cerrado: los pasos 3 y 4 existen precisamente porque el
paso 5 los necesita.

**Y hay una asimetría que `108` no vio:** el paso 4 va al final y sólo aparece una
vez, mientras el paso 3 va después del invalidate. **No son el mismo evento.**

## Lo que NO cierra

| Afirmación | Estado |
|---|---|
| Dos opcodes de IB según el motor | `PROVEN` (`gfx_v8_0.c:6077-6080`) |
| El ME no tiene opcode de IB | `PROVEN_ABSENT` |
| El IB ocupa 4 dwords en el anillo | `PROVEN` (`094`) + `OBSERVED` |
| `length_dw` en bits [23:0], `vmid` en [27:24] | `PROVEN` (`L6082`) + `OBSERVED` |
| El IB observado es de 344 dwords, VMID 6 | **`OBSERVED`** |
| El PFP busca los 8 IBs de esta captura | **`OBSERVED`** |
| El CE no busca ninguno (`0x31` = 0) | **`OBSERVED`** |
| `PFP_SYNC_ME` aparece 1 vez, no una por job | **`OBSERVED`** |
| Un vm_flush por job, no por fence | `PROVEN_DERIVED` |
| Dónde vive el IB que se busca | **`NOT_DETERMINED`** |
| Si PFP y ME compiten por el mismo anillo | **`NOT_DETERMINED`** |
| Si el CE puede buscar un IB en esta GPU | **`NOT_DETERMINED`** |

**Las tres últimas son `software behaviour ≠ hardware semantics`.** Que
`INDIRECT_BUFFER` haga que PFP vaya a la dirección `gpu_addr` es algo que el
driver **escribe**; que lo haga es algo que **no he observado**. Y que el ME no
tenga opcode de IB no significa que no pueda buscar trabajo por otra vía —sólo
que no tiene opcode para ello.

**Y `108` queda corregido en un punto concreto:** dije que la secuencia
`PFP-escribe → ME-espera → PFP-se-sincroniza` es lo que hace visible la
invalidación. **La medición de `PFP_SYNC_ME` = 1 en el anillo dice que no es una
secuencia por flush.** O se emite una vez al principio, o bajo una condición que
no se dio en estos 20 segundos. **No sé cuál, y `094` ya cuenta que su presupuesto
tiene un `PFP_SYNC_ME` contado como parte del frame**, lo que sugiere una vez
por flush. **Hay una contradicción entre `094` y esta medición, y no la resuelvo
por las buenas.**

## Procedencia

- `RUNTIME` — `debugfs/amdgpu_ring_gfx`, sólo lectura. Conteos y decodificación
  de 8 IBs, 34 EOP, 10 `WAIT_REG_MEM`, 9 `COND_EXEC`, 1 `PFP_SYNC_ME`.
- `STATIC` — `gfx_v8_0.c:6062-6098` y `gfx_v8_0.c:6191-6215`, `sid.h:397-414`,
  `soc15d.h:199-225`.
- Encadenada con `108` (la secuencia y los motores), `214` (un anillo, dos
  motores, tres esperas), `094` (`.emit_ib_size = 4`), `096`/`097`/`098` (los
  fences), `095` (PFP/ME/CE).
- **Corrige `108`** en un punto: `PFP_SYNC_ME` no es una vez por flush. Es mío.
- No se editó `AGENTS.md` ni `OPEN-FRONTIERS.md`: son de otras sesiones.

**Dos notas de método, y las dos son sobre haber contado mal.**

La primera: **conté 24 `WAIT_REG_MEM` en `097` y ahora cuento 10.** Es la misma
ruta y el mismo método, y la diferencia es que el anillo se ha llenado y vaciado
distinto entre capturas. **Un recuento de paquetes sobre un buffer circular es una
medición del instante, no del sistema.**

La segunda, y es la que importa: **escribí en `108` que `PFP_SYNC_ME` es parte de
la secuencia de cada vm_flush, sin contarlo.** Ahora el conteo dice 1, y `094`
dice que el presupuesto del frame lo incluye. **Son tres cosas que no encajan y
lo sé; no lo resuelvo por Notwithstanding.**

**Un hallazgo puede cerrar una pregunta y abrirla más grande. Este cerró `next IB`
y abrió si `PFP_SYNC_ME` es por flush, por job, o una vez.**
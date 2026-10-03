# 232  §G abre: cómo ve el GPU una escritura de la CPU — tres mecanismos y un solo trabajo

`CLASSIFICATION=DOCUMENTATION` · `TRACK=STATIC` · `WORK_CLASS=READ_ONLY/EVIDENCE`
`WRITE_EXECUTION=NONE` · `MODIFICATIONS=0` · `RUNTIME=NOT_RUN` · `GPU INTACTA`
`CORPUS=RESEARCH/working/linux-7.1.3` · `HARDWARE_SCOPE=HOST-C/RX550/0000:01:00.0`
`ABRE=secG (CACHE / COHERENCIA), que estaba intacta`

## Cuestión principal

`AGENTS.md` §G: *"Resolver CPU ↔ page tables ↔ GPU ↔ TLB ↔ GPU caches ↔ GART ↔
VRAM/system RAM. No asumir coherencia por analogía."*

La primera pregunta de esa cadena, y la más basic: **¿qué hace el driver para que
el GPU vea una escritura que acaba de hacer la CPU?**

## Criterio de terminación

Identificar el mecanismo, el registro y el valor, y todos los caminos por los que
se llega. **Cumplido: un registro, un valor, un idiom — y tres caminos que se
parecen y no son lo mismo.**

## El sitio donde todo se junta

`amdgpu_gart.c:497-506`, `amdgpu_gart_invalidate_tlb()`:

```c
mb();
if (down_read_trylock(&adev->reset_domain->sem)) {
        amdgpu_device_flush_hdp(adev, NULL);
        up_read(&adev->reset_domain->sem);
}
for_each_set_bit(i, adev->vmhubs_mask, AMDGPU_MAX_VMHUBS)
        amdgpu_gmc_flush_gpu_tlb(adev, 0, i, 0);
```

**`mb()` → flush HDP → invalidate TLB.** Es la frontera de coherencia completa en
cinco líneas, y su propio comentario dice por qué:

> *"Invalidate gart TLB which can be use as a way to flush gart changes"*

Es decir: **el invalidate de TLB es el mecanismo principal**, y el flush de HDP
está ahí como complemento. Eso ya es un dato sobre el diseño de coherencia de
esta generación.

## `amdgpu_device_flush_hdp` es un despachador con tres salidas

`amdgpu_device.c:6601-6622`:

```c
if ((adev->flags & AMD_IS_APU) && !amdgpu_passthrough(adev))  return;
if (adev->gmc.xgmi.connected_to_cpu)                          return;
if (ring && ring->funcs->emit_hdp_flush) { emit_hdp_flush(ring); return; }
if (!ring && amdgpu_sriov_runtime(adev)) { if (!amdgpu_kiq_hdp_flush(adev)) return; }
amdgpu_hdp_flush(adev, ring);
```

Polaris12 es discreta, no es APU y no tiene xGMI, así que las dos primeras no
disparan. Quedan tres caminos reales: **PM4 por ring**, **KIQ bajo SR-IOV**, y
**MMIO directo**.

## El camino MMIO: un registro, un valor, y un idiom

`vi.c:1310-1318`:

```c
static void vi_flush_hdp(struct amdgpu_device *adev, struct amdgpu_ring *ring)
{
	if (!ring || !ring->funcs->emit_wreg) {
		WREG32(mmHDP_MEM_COHERENCY_FLUSH_CNTL, 1);
		RREG32(mmHDP_MEM_COHERENCY_FLUSH_CNTL);
	} else {
		amdgpu_ring_emit_wreg(ring, mmHDP_MEM_COHERENCY_FLUSH_CNTL, 1);
	}
}
```

**`mmHDP_MEM_COHERENCY_FLUSH_CNTL = 0x0e17`**, escrito con `1`.

Y el `RREG32` **sin destino**: eso es un *idiom* de barrera de posted-writes. **Es
el mismo patrón que `gmc_v8_0.c:641`** con `VM_INVALIDATE_RESPONSE`, que `072`
describió como "lectura cuyo resultado se tira". No es un descuido ni un resto:
es la forma que tiene el driver de forzar el vaciado de escrituras no ordenadas.
Aparecen dos veces y significan lo mismo.

El campo de ese registro es de **un solo bit**:

```
nbif_6_1_sh_mask.h:8063   HDP_MEM_COHERENCY_FLUSH_CNTL__HDP_MEM_FLUSH_ADDR__MASK  0x1
nbif_6_1_sh_mask.h:2934   ...__SHIFT                                                 0x0
```

De ahí que el valor sea exactamente `1` y no un campo compuesto.

## El camino PM4: otros dos registros y un handshake distinto

`gfx_v8_0.c:6045-6056`, `gfx_v8_0_ring_emit_hdp_flush`, resuelto con `pm4_emit`:

```
6047  0xC0053C00   PACKET3_WAIT_REG_MEM (5 dwords)
6048  00000040 | 00000003 | reg_mem_engine   OPERATION(1)=wr_wait_wr_reg, FUNCTION(3)=equal
6051  0x00001537   mmGPU_HDP_FLUSH_REQ   = 0x0e26
6052  0x00001538   mmGPU_HDP_FLUSH_DONE  = 0x0e27
6053  ref_and_mask
6054  ref_and_mask
6055  0x00000020   poll interval
```

**No es el mismo mecanismo.** El MMIO escribe un bit y relee. El PM4 le dice al
*hardware* que escriba `REQ` y **espere a que valga `ref_and_mask`** — con
`OPERATION = 1`, que es `wr_wait_wr_reg`.

Y los tres registros están en el mismo bloque:

```
0x0ce   mmHDP_DEBUG0                       (invalidate)
0x0e17  mmHDP_MEM_COHERENCY_FLUSH_CNTL     (flush MMIO)
0x0e26  mmGPU_HDP_FLUSH_REQ                (flush PM4)
0x0e27  mmGPU_HDP_FLUSH_DONE               (flush PM4)
```

Más `vi_invalidate_hdp` (`vi.c:1320-1329`), que escribe `1` a
`mmHDP_DEBUG0 = 0x00ce` y lo relee. **Cuatro registros para un trabajo.**

## Qué camino usa cada llamador, y eso es el hallazgo de diseño

| llamador | `ring` | camino |
|---|---|---|
| `amdgpu_gart.c:501` | `NULL` | MMIO |
| `amdgpu_gfx.c:679` | `NULL` | MMIO |
| `amdgpu_gfx.c:739` | `NULL` | MMIO |
| `amdgpu_gfx.c:784` | `NULL` | MMIO |
| `amdgpu_device.c:774` | `NULL` | MMIO |
| `amdgpu_amdkfd.c:766` | `NULL` | MMIO |
| `amdgpu_ib.c:253` | `ring` | **PM4** |

**Seis de siete usan MMIO. Solo el scheduler de IB usa PM4.**

La consecuencia para un driver propio es concreta: **el camino caliente
—invalidación de GART, arranque de GFX, KFD— es una barrera de CPU**, no una
orden en el ring. El mecanismo por ring existe, pero está reservado a un sitio.

## Un error mío, del tipo que este proyecto ya tiene fichado

Primero afirmé que `amdgpu_hdp_flush` era un **no-op** en esta placa, porque
`hdp.funcs` solo se asigna para `IP_VERSION(4,1,0)` … `(7,0,0)`
(`amdgpu_discovery.c:3203-3233`), es decir Vega10 en adelante, y GCN3 no llega.

El error fue de búsqueda, no de lectura:

```
$ grep -rn "asic_funcs = " *.c | head -8
```

El `head -8` **truncó al productor** y se comió justo la línea que importaba.
`vi.c:1472` asigna `adev->asic_funcs = &vi_asic_funcs`, y `vi_asic_funcs`
(`vi.c:1427-1444`) **sí tiene** `.flush_hdp = &vi_flush_hdp` y
`.invalidate_hdp = &vi_invalidate_hdp`.

Mi hipótesis era falsa y lo que la delató fue mirar el bloque completo cuando el
número no cuadraba. **Es la segunda vez en esta sesión que un `head` me oculta
información**; `AGENTS.md` lo prohíbe explícitamente ("evitar pipelines que maten
trunquen al productor") y `052` ya había documentado una versión de este mismo
defecto.

## Confounder: los nombres de campo son de otra generación

Los tres registros **no tienen nombres de campo en ninguna cabecera de GFX8**.
Los únicos que existen:

```
nbif_6_1_sh_mask.h:8063   HDP_MEM_FLUSH_ADDR  mask 0x1        (Arcturus)
hdp_5_2_1_sh_mask.h:107  HDP_DEBUG           mask 0xFFFFFFFF (Navi)
hdp_7_0_0_sh_mask.h:92   HDP_DEBUG           mask 0xFFFFFFFF (futuro)
```

**GCN3 no tiene bloque HDP como IP separada** — `vi.c:2105-2113` registra seis
bloques y ninguno es HDP, y `AMD_IP_BLOCK_TYPE_HDP` no aparece en el corpus.

Así que el *valor* que se escribe es `PROVEN` (está en el fuente), pero el *nombre
del campo* es de otra generación y **`NOT_APPLICABLE` para esta placa**. Es la
misma trampa que `112` con las cabeceras y que `144` con `sid.h`: **un header
degenerado por ASIC es un mapa de posibilidades, no un inventario.**

## Clasificación

| afirmación | estado |
|---|---|
| El flush es `mmHDP_MEM_COHERENCY_FLUSH_CNTL = 1` | `PROVEN` — `vi.c:1313` |
| `mmHDP_MEM_COHERENCY_FLUSH_CNTL = 0x0e17` | `PROVEN` |
| El `RREG32` sin destino es una barrera de posted-writes | `CORROBORATED` — idioma, dos usos |
| El invalidate de TLB es el mecanismo principal de GART | `PROVEN` — comentario + código |
| El camino PM4 usa `REQ`/`DONE` con `wr_wait_wr_reg` | `PROVEN` — `gfx_v8_0.c:6045-6056` |
| `mmGPU_HDP_FLUSH_REQ/DONE = 0x0e26/0x0e27` | `PROVEN` |
| 6 de 7 llamadores usan MMIO | `PROVEN` |
| `invalidate_hdp` usa `mmHDP_DEBUG0 = 0x00ce` | `PROVEN` — `vi.c:1324` |
| Que el hardware aplique el flush al escribir 1 | `NOT_DETERMINED` — sin spec |
| Que `HDP_MEM_FLUSH_ADDR` sea el nombre en GFX8 | `NOT_APPLICABLE` — es de Arcturus |
| Que no haya flush de caché de CPU en el camino | `PROVEN_ABSENT` — no hay más llamadas |

## Confounders

- **El nombre del campo es de otra generación.** Lo único transferible es la
  dirección y el ancho de 1 bit.
- **No he medido nada.** Que escribir 1 baste para hacer visible la escritura
  es lo que el driver asume; comprobarlo requiere placa.
- **La lectura sin destino podría ser residuo de compilación** en vez de
  barrera intencionada. El mismo idioma aparece dos veces con el mismo efecto
  buscado, lo que hace la hipótesis de barrera más fuerte que la de residuo,
  pero no la prueba.
- **`AMD_IP_BLOCK_TYPE_HDP` no existe en el corpus.** No puedo afirmar que en el
  driver completo no haya un bloque HDP para GCN3; solo que en *este* subárbol no
  hay rastro.
- **El camino KIQ no está examinado**: solo lo veo por el despacho, y exige
  SR-IOV, que esta placa no tiene.

## Desfalsificación

- **(a)** El flush es `0x0e17` con valor 1 → refutable con `vi.c:1313`.
- **(b)** El registro es de 1 bit → refutable con `nbif_6_1_sh_mask.h:8063`.
- **(c)** Los cuatro registros → refutable con el grep en `include/asic_reg/`.
- **(d)** 6 de 7 usan MMIO → refutable con las 7 llamadas.
- **(e)** Que el hardware lo aplique → **no refutable aquí**, y no se afirma.

## UNLOCKS

- **§G tiene su primer hecho sólido**: la visibilidad CPU→GPU en esta placa es
  "pon un bit y relee", no un flush de caché coherente. **No hay DMA coherente.**
- **El idioma de la lectura sin destino aparece dos veces** (`106`/`104` y aquí)
  con el mismo propósito. Merece su propio hallazgo: es la primitive de
  sincronización que el driver prefiere en lugar de `wmb()`.
- **Cuatro registros para una tarea** es el tipo de redundancia que un driver
  propio debería poder reducir a uno, una vez medido cuál basta.
- **La ruta caliente es MMIO, no ring.** Eso cambia el cálculo de coste: añadir
  un `mb()` de CPU es más barato que reservar espacio de ring.
- **Siguiente paso**: el camino del page table en sí. `amdgpu_vm_cpu.c:115-124`
  tiene un `mb()` seguido de HDP flush, y el proyecto ya sabe que en esta placa
  la ruta CPU de page tables es inalcanzable (`vm_update_mode = 0`). Falta
  verificar por qué, que es donde está el discriminante.

## Evidencia

```
vi.c:1310-1318        vi_flush_hdp      WREG32(mmHDP_MEM_COHERENCY_FLUSH_CNTL, 1)
                                         RREG32(...)  <- sin destino
vi.c:1320-1329        vi_invalidate_hdp mmHDP_DEBUG0 = 1, y relee
vi.c:1427-1444        vi_asic_funcs     .flush_hdp = &vi_flush_hdp
amdgpu_device.c:6601  amdgpu_device_flush_hdp, tres salidas
amdgpu_gart.c:499-505 mb(); flush_hdp(NULL); flush_gpu_tlb(0, i, 0)

gfx_v8_0.c:6045-6056  emit_hdp_flush   WAIT_REG_MEM OPERATION(1) FUNCTION(3)
                                       0x0e26 REQ / 0x0e27 DONE

0x00ce  mmHDP_DEBUG0
0x0e17  mmHDP_MEM_COHERENCY_FLUSH_CNTL
0x0e26  mmGPU_HDP_FLUSH_REQ
0x0e27  mmGPU_HDP_FLUSH_DONE

nbif_6_1_sh_mask.h:8063  HDP_MEM_FLUSH_ADDR__MASK 0x1  (Arcturus, NO GFX8)
amdgpu_discovery.c:3203-3233  hdp.funcs solo para IP_VERSION 4.1 .. 7.0
vi.c:2105-2113          Polaris12 registra 6 bloques IP, ninguno HDP
```

```
08-ARQUITECTURA/tools/pm4_emit.py --func gfx_v8_0_ring_emit_hdp_flush
```

`WRITE_EXECUTION=NONE`. `MODIFICATIONS=0`. `GPU INTACTA`.

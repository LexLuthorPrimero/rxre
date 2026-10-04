# BARRERAS-GFX8 · Capability audit de las barreras en GFX8 (Polaris12 / gfx803)

```
NODE            = BARRERAS-GFX8
SCOPE           = SOLO lectura del corpus + measurements de host. UN fichero escrito.
GPU             = INTACTA. SIN dmesg. SIN journalctl. SIN debugfs. SIN MMIO. SIN escritura.
WRITES          = 1 (este fichero). MODIFICATIONS=0 sobre el corpus.
RENUMERACIÓN    = NINGUNA. No se crea ningún hallazgo nuevo. Se usan los IDs existentes.
CORPUS_UNIVERSE = RESEARCH/baseline/linux-7.1.3  (idéntico byte a byte a kernelbuild/ y working/ —
                  ver INPUT_HASHES más abajo, los tres árboles comparten sha256)
FECHA           = 2026-10-04
```

---

## 0. Verificación de entradas antes de interpretar nada

`RESEARCH/baseline`, `RESEARCH/kernelbuild` y `RESEARCH/working` contienen ficheros
`gfx_v8_0.c` con el **mismo sha256**. Se puede trabajar sobre cualquiera sin riesgo de
divergencia. Canónico elegido: `baseline`.

```
sha256(16)    bytes    fichero
2427f5b5fcb44778   247678  drivers/gpu/drm/amd/amdgpu/gfx_v8_0.c          (baseline == kernelbuild == working)
c6d6f3318de2a080    86691  drivers/gpu/drm/amd/amdgpu/si.c
4b42454a90a714c4    19347  drivers/gpu/drm/amd/amdgpu/vid.h
dd03da7ad3a67f92    31465  drivers/gpu/drm/amd/amdgpu/sid.h
4de16e61df303f65    14267  drivers/gpu/drm/amd/amdgpu/amdgpu_ib.c
263c5d83b1f1fd6b    87124  drivers/gpu/drm/amd/amdgpu/amdgpu_vm.c
3d2e369afeca10ba    45502  drivers/gpu/drm/amd/amdgpu/amdgpu_cs.c
2b81489244344184    27305  drivers/gpu/drm/amd/amdgpu/amdgpu_fence.c
8ff06e950e4b0853     1474  drivers/gpu/drm/amd/amdgpu/vi.h
299228e0bbd75d0f   244444  drivers/gpu/drm/amd/include/asic_reg/gca/gfx_8_0_d.h
c2dd6e2f68a04711  1136970  drivers/gpu/drm/amd/include/asic_reg/gca/gfx_8_0_sh_mask.h
fa6b8ff974fccdd5   376576  drivers/gpu/drm/amd/include/asic_reg/gca/gfx_8_0_enum.h
b76155a25e98f378    15650  drivers/gpu/drm/amd/include/vi_structs.h
```

**Trampa del corpus que había que esquivar, y cómo se esquivó.** El aviso del
coordinador era que los sufijos `__SHIFT`/`__MASK` hacen que el mismo nombre de bit
aparezca en 21 ficheros. Confirmado y **neutralizado por medición**: en
`asic_reg/gc/` **no existe ningún `gc_8_0_*.h`** (30 ficheros, el más antiguo es
`gc_9_0_*`). Los registros de GFX8 no viven en `gc/` sino en el árbol antiguo
`asic_reg/gca/` con nombres `mm<REG>` sin prefijo de generación, y los incluye
`gfx_v8_0.c:49-51`. Por eso `mmVGT_SHADER_STAGES_EN` **no** se encuentra en
`gc_9_0_*` con el mismo offset sin más análisis: son árboles asic_reg distintos.

Riesgo residual: el mismo nombre (`CP_COHER_CNTL__TCL1_ACTION_ENA`) sí aparece en
`gc_9_0_sh_mask.h` y en `gca/gfx_8_0_sh_mask.h`. **No se ha verificado si los valores
coinciden.** Para las afirmaciones de este documento sólo se usa
`gca/gfx_8_0_sh_mask.h`, que es el que incluye el fichero GFX8. Estado:
`NOT_DETERMINED`.

---

## 1. HALLAZGO ESTRUCTURAL: el driver GFX8 de este corpus NO EMITE BARRERAS

Esto reordena las siete ideas, así que va primero y con los números exactos.

### 1.1 Conteo de ocurrencias — `gfx_v8_0.c` (7207 líneas)

```
patrón                                  ocurrencias
----------------------------------------- -----------
barrier                                          0
PACKET3_ATOMIC                                    0
PACKET3_ATOMIC_GDS                                0
PACKET3_ATOMIC_MEM                                0
SET_SGPR                                          0
mS_SET_SGPR                                       0
SBAR                                              0
ATOMIC_ROOT                                       0
s_end                                             0
e_end                                             1   ← FALSO POSITIVO
ALL_COMMANDS                                      0
ALL_GRAPHICS                                      0
DependencyInfo                                    0
mmVGT_SHADER_STAGES_EN                            0
mmGDS_ATOM_*                                      0
mmCP_COHER_CNTL                                   0
```

El único `e_end` es la subcadena de `gfx_v8_0.c:1240`
`amdgpu_gfx_csb_preamble_end(buffer, count);`. **`e_end` como mnemónico ISA: 0.**

`si.c` (86691 bytes, el otro fichero de la familia GFX8/SI):
```
barrier = 0    wait_for_idle = 0    wait_for_eop = 0
```

### 1.2 Conteo sobre TODO el árbol `drivers/gpu/drm`

```
mS_SET_SGPR      0 ocurrencias
ATOMIC_ROOT      0
SGPR_SBAR        0
DependencyInfo   0
PACKET3_ATOMIC*  0 usos en cualquier .c  (TOTAL: 0)
```

`PACKET3_ATOMIC` sí está **definido**, en dos cabeceras, con el mismo opcode:
- `sid.h:355` → `#define PACKET3_ATOMIC 0x1E`
- `vid.h:121` → `#define PACKET3_ATOMIC_MEM 0x1E`

`gfx_v8_0.c:35` incluye `vid.h`, no `sid.h`. **Ninguna de las dos cabeceras contiene
la descomposición en bits del payload de ATOMIC** (cero `PACKET3_ATOMIC_MEM__ATOMIC`,
cero `__CACHE_POLICY`; esas 20+14 descomposiciones están sólo en `nvd.h` y
`soc15d.h`, que son Navi y DCN15, no GFX8).

Divergencia medida entre las dos cabeceras (relevante porque `sid.h` y `vid.h` son
ambas candidatas):

```
macros de sincronización definidas en AMBAS con cuerpo DISTINTE :  0
sólo en sid.h : PACKET3_ATOMIC=0x1E, PACKET3_ALLOC_GDS, PACKET3_WRITE_GDS_RAM,
               PACKET3_MEM_WRITE, PACKET3_SEM_WAIT_ON_SIGNAL(1<<12),
               PACKET3_SEM_SEL_SIGNAL(0x6<<29), PACKET3_SEM_SEL_WAIT(0x7<<29)
sólo en vid.h : EOP_TCL1_ACTION_EN(1<<16), EOP_TC_ACTION_EN(1<<17),
               EOP_TC_WB_ACTION_EN(1<<15), EOP_EXEC(1<<28), PACKET3_ATOMIC_MEM=0x1E
```

Conclusión de esta tabla: la elección de cabecera **no cambia ningún valor de opcode
que este documento use**, pero sí cambia qué nombres de bits EOP están disponibles —
y `vid.h` es la que los tiene. Consistente con que `gfx_v8_0.c` incluya `vid.h`.

### 1.3 Por qué no hay barreras: el IB de usuario es opaco al kernel

`amdgpu_cs.c:381-391`, función `amdgpu_cs_p2_ib`:

```c
r =  amdgpu_ib_get(p->adev, vm, ring->funcs->parse_cs ?
                   chunk_ib->ib_bytes : 0,
                   AMDGPU_IB_POOL_DELAYED, ib);
...
ib->gpu_addr = chunk_ib->va_start;
ib->length_dw = chunk_ib->ib_bytes / 4;
ib->flags = chunk_ib->flags;
```

El kernel copia **dirección virtual y longitud**. No parsea, no reescribe, no inspecciona.
`ring->funcs->parse_cs` es `NULL` para GFX8: `parse_cs` aparece en el árbol drm
**sólo** en `vce_*`, `uvd_*`, `jpeg_*` y sus wrappers `amdgpu_vce.c`,
`amdgpu_uvd.c`, `amdgpu_jpeg.c`, `amdgpu_ring.h`, `amdgpu_cs.c`. Las tres tablas de
ring funcs de GFX8 (`gfx_v8_0.c:6870-6914`, `6916-6949`, `6951-6974`) **no** listan
`.parse_cs`.

Y el lado de emisión es igualmente opaco: `gfx_v8_0_ring_emit_ib_gfx`
(`gfx_v8_0.c:6069-6099`) son **4 escrituras** que emiten `PACKET3_INDIRECT_BUFFER`
apuntando a la VA del usuario. Lo que haya dentro —incluidas todas las barreras— no
lo ve nadie en el kernel.

### 1.4 Lo que esto significa para N-INT-26 … N-INT-32

Las siete ideas, tal como están redactadas, son *variar la máscara / el ámbito / la
agrupación / la distancia / la dirección de **la barrera***. En este corpus **no hay
ninguna barrera que variar**, ni una sola, ni emitida por el driver ni visible para él.

```
N-INT-26 (ámbito)      no es una propiedad de este driver: no existe la máscara que variar
N-INT-27 (máscara ETAPA)   ídem; además ALL_COMMANDS/ALL_GRAPHICS = 0 ocurrencias
N-INT-28 (máscara ACCESO)  ídem
N-INT-29 (agrupación)      no es decidible aquí; DependencyInfo = 0 en todo el árbol drm
N-INT-30 (distancia)       sí es propiedad del IB de usuario, no del driver
N-INT-31 (dirección)       propiedad del shader ISA, no del driver
N-INT-32 (auditoría)       sí es posible, y es el único que se responde con este corpus (§3)
```

Esto no invalida las siete ideas. Las **reubica**: las que hablan de la barrera como
objeto tienen que empezar por **construir el emisor**. N-INT-32 es la única que se
audita hoy, y es la que dice si el emisor merece la pena construirse.

---

## 2. TAXONOMÍA REAL: los 9 primitivos de sincronización que GFX8 SÍ emite

No es la de Vulkan ni la de un libro. Es la que sale de contar
`amdgpu_ring_write()` por función en `gfx_v8_0.c`. La columna `dw` es **medida**
(nº de escrituras al ring dentro de la función), no comentada.

| # | Primitivo | Packet / opcode | Bits que pone | dw | Qué SÍ sincroniza | Qué NO |
|---|---|---|---|---|---|---|
| 1 | `gfx_v8_0_ring_emit_pipeline_sync` `6174-6189` | `PACKET3_WAIT_REG_MEM` = `0x3C` (`vid.h:168`), `gfx_v8_0.c:6180` | `MEM_SPACE(1)`+`FUNCTION(3)`+`ENGINE(usepfp)` (`6181-6183`), addr+seq, poll 4 | **7** | espera a que la memoria de fence alcance `sync_seq`; motor PFP si es anillo GFX, ME si es compute | no toca cachés; no toca PTE; no ordena shaders entre sí |
| 2 | `gfx_v8_0_ring_emit_hdp_flush` `6036-6056` | `PACKET3_WAIT_REG_MEM` `gfx_v8_0.c:6047` | `OPERATION(1)`+`FUNCTION(3)`+`reg_mem_engine` (`6048-6050`), `mmGPU_HDP_FLUSH_REQ/DONE`, poll `0x20` | **7** | vuelca HDP (Host Data Push) — dirty data del host a VRAM | no invalida L2; no toca L1; no toca SDMA |
| 3 | `gfx_v8_0_ring_emit_vm_flush` `6191-6215` | `PACKET3_WAIT_REG_MEM` `gfx_v8_0.c:6199` + `PACKET3_PFP_SYNC_ME` `gfx_v8_0.c:6212` | flush TLB vía `amdgpu_gmc_emit_flush_gpu_tlb`, luego espera `mmVM_INVALIDATE_REQUEST`, luego `PFP_SYNC_ME(0)` | **9** (+`VI_FLUSH_GPU_TLB_NUM_WREG*5`=15 WREG, `vi.h:27`) | invalida TLB de una VMID; y al final `PFP_SYNC_ME` | **no** sincroniza cachés de datos; **no** es barrera |
| 4 | `gfx_v8_0_emit_mem_sync` `6761-6772` | `PACKET3_SURFACE_SYNC` = `0x43` (`vid.h:201`), `gfx_v8_0.c:6763` | máscara = `0x28C40000` (`6764-6768`); `CP_COHER_SIZE=0xffffffff` (`6769`); `CP_COHER_BASE=0` (`6770`); poll `0x0A` | **5** | TCL1 + TC + SH_KCACHE + SH_ICACHE + TC_WB | **21 de los 26 campos de `CP_COHER_CNTL` no se ponen** (ver §2.1) |
| 5 | `gfx_v8_0_emit_mem_sync_compute` `6774-6787` | `PACKET3_ACQUIRE_MEM`, `gfx_v8_0.c:6776` | **exactamente la misma máscara** `0x28C40000` (`6777-6781`) + `CP_COHER_SIZE_HI=0xff` (`6783`) | **7** | ídem #4, más los 32 bits altos de tamaño | ídem #4 |
| 6 | `gfx_v8_0_ring_emit_fence_gfx` `6135-6172` | `PACKET3_EVENT_WRITE_EOP` = `0x47` (`vid.h:237`), **dos veces**: `gfx_v8_0.c:6145` y `6159` | ambos con `EOP_TCL1_ACTION_EN\|EOP_TC_ACTION_EN\|EOP_TC_WB_ACTION_EN\|EVENT_TYPE(5)\|EVENT_INDEX(5)` = `0x000505` (`6146-6150`, `6160-6165`); el 2º añade `EOP_EXEC` si `exec` | **12** (2×6) | vacía L2/TCL/KCACHE y escribe un valor de 32 o 64 bits en memoria, con IRQ opcional | el primero es un **EOP señuelo con `seq-1`** (`6154-6155`), comentado *"Workaround for cache flush problems"* (`6142-6144`); no protege nada por sí mismo |
| 7 | `gfx_v8_0_ring_emit_fence_compute` `6231-6250` | `PACKET3_RELEASE_MEM`, `gfx_v8_0.c:6239` | `0x000505` + `DATA_SEL`/`INT_SEL` (`6240-6244`) | **7** | ídem #6, una sola vez, sin el señuelo | — |
| 8 | `gfx_v8_0_ring_emit_vgt_flush` `6058-6067` | `PACKET3_EVENT_WRITE` ×2, `gfx_v8_0.c:6060` y `6064` | `EVENT_TYPE(VS_PARTIAL_FLUSH)\|EVENT_INDEX(4)` y `EVENT_TYPE(VGT_FLUSH)\|EVENT_INDEX(0)` | **4** | vacía la parte de VGT para poder cambiar de estado de contexto | no toca cachés de datos ni L2 |
| 9 | `gfx_v8_ring_emit_sb` `6277-6281` | `PACKET3_SWITCH_BUFFER` = `0x8B` (`sid.h:550`), `gfx_v8_0.c:6279` | payload `0` | **2** | frontera de IB para VCN/JPEG firmware | no es barrier para GFX8 |

Aparte, `gfx_v8_0_ring_emit_gds_switch` (`5116-5153`, 4×`PACKET3_WRITE_DATA`, **20 dw**)
escribe `mmGDS_VMIDn_BASE/SIZE`, `mmGDS_GWS_VMIDn` y `mmGDS_OA_VMIDn` (`5123-5152`).
Es **configuración de recurso de barrera**, no una barrera: no ejecuta nada.

### 2.1 Lo que `SURFACE_SYNC` NO sincroniza — la lista exacta

`CP_COHER_CNTL` = `0xc07c` (`gfx_8_0_d.h:500`). 26 campos `_ENA` definidos en
`gca/gfx_8_0_sh_mask.h:3157-3208`.

```
PUESTOS POR EL DRIVER (5)          mask          sh_mask.h
TCL1_ACTION_ENA                   0x00400000    3191
TC_ACTION_ENA                     0x00800000    3193
TC_WB_ACTION_ENA                  0x00040000    3185
SH_KCACHE_ACTION_ENA              0x08000000    3199
SH_ICACHE_ACTION_ENA              0x20000000    3203
                                ─────────────
suma                             0x28C40000
```

**Cross-check de dos representaciones independientes:** la máscara a nivel de
*packet* calculada desde los shifts de `vid.h:213-224`
(`1<<22 | 1<<23 | 1<<27 | 1<<29 | 1<<18`) da `0x28C40000`. La máscara a nivel de
*registro* calculada desde los `__MASK` de `gfx_8_0_sh_mask.h` da `0x28C40000`.
**Idénticas.** Dos fuentes que no se derivan una de otra coinciden bit a bit.

```
NO PUESTOS (21)                   sh_mask.h
TC_SD_ACTION_ENA                  3161
TC_NC_ACTION_ENA                  3163
TCL1_VOL_ACTION_ENA               3183
CB0..CB7_DEST_BASE_ENA            3165..3179
DB_DEST_BASE_ENA                  3181
DEST_BASE_0_ENA                   3157
DEST_BASE_1_ENA                   3159
SH_KCACHE_VOL_ACTION_ENA          3201
SH_KCACHE_WB_ACTION_ENA           3205
SH_SD_ACTION_ENA                  3207
CB_ACTION_ENA                     3195
DB_ACTION_ENA                     3197
TCL1_ACTION_ENA (ya puesto)        —
DEST_BASE_2_ENA                   3187
DEST_BASE_3_ENA                   3189
```

**Consecuencia dura para N-INT-26:** el driver emite una invalidación de coherencia
**sin ninguna selección de recurso**. Los 4 `DEST_BASE_n_ENA` y los 10
`*_DEST_BASE_ENA` (CB0..7 + DB) son **precisamente los campos de selección de destino**
que existen en el registro, y el driver no pone ninguno. `CP_COHER_BASE=0` +
`CP_COHER_SIZE=0xffffffff` (`gfx_v8_0.c:6769-6770`) acompaña a esa máscara.

Estado de la interpretación "rango completo de direcciones": `DERIVATION`, no
`PROVEN`. El corpus sólo etiqueta los campos (`/* CP_COHER_SIZE */`,
`/* CP_COHER_BASE */`, `gfx_v8_0.c:6769-6770`). **Refutador:** que exista en el corpus
alguna escritura de `CP_COHER_BASE` distinta de 0 o de `CP_COHER_SIZE` distinta de
`0xffffffff`. Buscado en `gfx_v8_0.c`: **cero**. Por eso la derivo; por eso no la
promuevo.

### 2.2 El coste está escrito en el fuente — y es medible sin GPU

`gfx_v8_0.c:6878-6896` es el desglose de `emit_frame_size` del anillo GFX, en
dwords. Sumando los términos y `VI_FLUSH_GPU_TLB_NUM_WREG = 3` (`vi.h:27`):

```
COND_EXEC            5     (6887)   medido en función: 5   ✓
PIPELINE_SYNC        7     (6880)   medido: 7               ✓
VM_FLUSH            24     (6881)   medido: 9 + 15 WREG     ✓
FENCE (VM_FLUSH)    12     (6882)   medido: 12              ✓
GDS switch          20     (6883)   medido: 20              ✓
doble SWITCH_BUFFER  4     (6884)   medido: 2×2             ✓
COND_EXEC            5     (6887)   medido: 5               ✓
HDP_flush            7     (6888)   medido: 7               ✓
VGT_flush            4     (6889)   medido: 4               ✓
CE_META             14     (6890)   medido: cnt_ce-2+4      ✓
DE_META             31     (6891)   medido: cnt_de-2+4      ✓
CNTX_CTRL            3     (6892)   medido: 3               ✓
HDP_INVL             5     (6893)
FENCE x2           12+12   (6894)   medido: 12              ✓
SWITCH_BUFFER        2     (6895)   medido: 2               ✓
SURFACE_SYNC         5     (6896)   medido: 5               ✓
                        ────
                        172 dw
```

Los 14 y 31 se explican exactamente por `chained_ib_support`:
`vi_ce_ib_state` = 4 dword (`vi_structs.h:432`) → 4+4 = **8**, no 14;
`vi_ce_ib_state_chained_ib` = 10 dword (`vi_structs.h:468`) → 10+4 = **14** ✓.
`vi_de_ib_state` = 17 dword (`vi_structs.h:452`) → 17+4 = **21**, no 31;
`vi_de_ib_state_chained_ib` = 27 dword (`vi_structs.h:507`) → 27+4 = **31** ✓.

Y la condición es de **firmware en runtime**, no estática:
`gfx_v8_0.c:1048-1053` — `chained_ib_support = true` sólo si
`ce_feature_version >= 46 && pfp_feature_version >= 46`.

```
emit_frame_size (anillo GFX, chained IB activo)   = 172 dw
emit_frame_size (anillo GFX, chained IB inactivo) = 172 - 10 - 6 = 156 dw
```

El comentario `6878` dice *"maximum 215dw if count 16 IBs in"*. 172 + 16×4 = 236, no
215. **Contradicción no resuelta.** No la uso como número. Registrada como
`CONTRADICTION` abierta; posible causa: el comentario cuenta `emit_ib_size` de otra
generación o incluye `HDP_INVL` de forma distinta. Lo que **no** hago es elegir la
lectura que me convenga.

`emit_frame_size` del anillo COMPUTE (`6924-6933`): 20+7+5+7+(15+7)+(7+7+7)+7+5+15 =
**109 dw**. Del KIQ (`6959-6965`): 20+7+5+7+17+7+7+7 = **77 dw**.

---

## 3. N-INT-32 · AUDITORÍA DE NECESIDAD: qué dependencia protege cada barrera

Este es el único punto de las siete ideas que el corpus puede responder hoy. Para cada
primitivo: consumidor, condición de disparo, y **la dependencia que protege — o si no
se puede nombrar**.

| # | Primitivo | Consumidor (fichero:línea) | Condición de disparo | Dependencia protegida | NOMBRABLE? |
|---|---|---|---|---|---|
| 1 | `PIPELINE_SYNC` | `amdgpu_vm.c:843-844` | `need_pipe_sync`, que se pone en `amdgpu_ib.c:207-217` si hay `explicit_sync`, **o** `need_ctx_switch` (`206`), **o** `amdgpu_vm_need_pipeline_sync` | orden entre dos IBs ya aceptados por el planificador: espera a `sync_seq` en memoria | **SÍ** — `ring->fence_drv.gpu_addr` + `sync_seq` (`gfx_v8_0.c:6177-6178`) |
| 2 | `HDP_flush` | `amdgpu_gfx.c:1310` (`amdgpu_kiq_hdp_flush`), `amdgpu_device.c:6612` | igualdad de VMID de cola antes/después de un cambio de cola | que los datos escritos por el host por HDP sean visibles antes de que CP ejecute lo que sigue | **SÍ** — `mmGPU_HDP_FLUSH_REQ/DONE`, y `gfx_v8_0_get_hdp_flush_mask` (`5223-5248`) selecciona CP0/CP2/CP6 según `ring->me` |
| 3 | `VM_FLUSH` + `PFP_SYNC_ME` | `amdgpu_vm.c:849-851` | `job->vm_needs_flush`, o `has_compute_vm_bug`, o GWS switch pendiente, o reset de GPU previo (`amdgpu_vm.c:761-768`, `799-804`) | que una VMID nueva/re-mapeada no lea TLB obsoleto; y que PFP no lea registros invalidados | **SÍ** para la VMID. **`PFP_SYNC_ME`:** el comentario `gfx_v8_0.c:6211` dice *"otherwise we might get invalid PFP reads"* — nombra el peligro, **no cita un modo de fallo concreto ni un caso de reproducción**. Parcial |
| 4 | `SURFACE_SYNC` | `amdgpu_ib.c:235-236` | `ib->flags & AMDGPU_IB_FLAG_EMIT_MEM_SYNC`. El kernel lo pone **incondicionalmente** en `amdgpu_ib.c:80` para **todo IB que el propio kernel aloca** (`size != 0`), con el comentario *"flush the cache before commit the IB"* (`79`) | **NO SE PUEDE NOMBRAR** | **NO** — ver abajo |
| 5 | `ACQUIRE_MEM` (compute) | mismo `amdgpu_ib.c:235-236` | idem, en anillo COMPUTE | **NO SE PUEDE NOMBRAR** — y además es **idéntico** a #4 en máscara, lo que sugiere que se copió sin justificar | **NO** |
| 6 | `EVENT_WRITE_EOP` ×2 (fence GFX) | `amdgpu_fence.c:117-118` (`amdgpu_fence_emit`), `amdgpu_ib.c:300-301` (fence de usuario) | siempre, al final del IB del usuario y siempre por `amdgpu_fence_emit` | el valor de `sync_seq` sólo se escribe cuando todo lo anterior del IB ha completado → es **la** dependencia que cierra el IB | **SÍ** para el EOP real (`6159`) |
| 6b | EOP señuelo con `seq-1` | `gfx_v8_0.c:6145-6155` | **incondicional**, siempre antes del EOP real | *"Workaround for cache flush problems"* (`6142-6144`). No hay condición, ni condición de desactivación, ni referencia a un fallo concreto | **NO** — nombra una clase de problema, no una dependencia |
| 7 | `RELEASE_MEM` (fence compute) | `amdgpu_fence.c:117-118` | siempre | ídem #6, un solo EOP | **SÍ** |
| 8 | `VGT_flush` | `gfx_v8_ring_emit_cntxcntl` (`gfx_v8_0.c:6291-6292`) | `flags & AMDGPU_HAVE_CTX_SWITCH` (que `amdgpu_ib.c:255-256` pone si `ring->current_ctx != fence_ctx`) | que el contexto anterior esté drenado antes de cambiar CS state | **SÍ** |
| 9 | `SWITCH_BUFFER` | `amdgpu_vm.c:909-910` (doble) y `amdgpu_ib.c:322-323` (simple) | el doble **no** se puede saltar por `COND_EXEC` (`amdgpu_vm.c:907`); el simple al final del IB | frontera de IB para firmware de vídeo; en GFX8 puro no es un synchronization point | **SÍ**, pero **no es una barrera** — fuera de la taxonomía |

### 3.1 Las tres barreras cuya dependencia NO se puede nombrar

**#4/#5 `SURFACE_SYNC` / `ACQUIRE_MEM`.** Aquí está el hallazgo pedido.
`amdgpu_ib.c:79-80` pone el flag con el comentario *"flush the cache before commit the
IB"*, **sin condición**: todo IB que el kernel aloca lo lleva. No hay ningún `if` que
lo haga depender de nada. No hay en el corpus ningún consumidor de ese IB que declare
qué dato produce y qué dato consume, ni ningún comentario que diga qué caché queda
sucia si se quita. La máscara es de 5 dominios y el rango es `0xffffffff` (§2.1), pero
**el corpus no dice qué de esos 5 dominios contiene el dato que esta operación
protege**. Esto no es un detalle: es una invalidación de cachés *incondicional* cuyo
peligro protegido no está escrito en ninguna parte del árbol.

Contraejemplo que lo refutaría: un comentario o commit en el corpus que nombre el
hazard. Buscado en `amdgpu_ib.c`, `amdgpu_cs.c`, `amdgpu_vm.c`, `gfx_v8_0.c`: no
existe. **La clasificación se sostiene.**

**#6b el EOP señuelo.** `seq - 1` (`gfx_v8_0.c:6154-6155`). Se emite siempre. Su
justificación es una frase ("cache flush problems"). No hay forma de desactivarlo, ni
de saber si sigue siendo necesario en gfx803, ni de medir si todavía hace algo.
Coste medido: **6 dw y un viaje completo por el pipe gráfico, por IB, siempre**.

**#3b `PFP_SYNC_ME`.** `"otherwise we might get invalid PFP reads"` (`gfx_v8_0.c:6211`).
Nombra el peligro pero no el disparador. Parcialmente nombrable.

### 3.2 El otro hueco de la auditoría: el usuario

Ni #4 ni #5 ni nada más cubre las barreras *de aplicación*. Esas no entran en este
corpus: son opacas (§1.3). Por tanto **la auditoría de necesidad de N-INT-32 está
completa al 100% para las barreras del driver y al 0% para las barreras del usuario.**
El corpus no permite el segundo 0%. Eso no es un fallo del método: es que el objeto no
está en el material. Se registra como `NOT_FOUND` con alcance acotado, no como
`PROVEN_ABSENT`.

---

## 4. Qué es medible aquí y qué no — con números

### 4.1 MEDIBLE ESTÁTICAMENTE en este corpus (y ya medido)

| Métrica | Valor | Cómo |
|---|---|---|
| barreras emitidas por el driver GFX8 | **0** | conteo de `PACKET3_ATOMIC*` en `gfx_v8_0.c` = 0 |
| primitivos de sincronización emitidos | **9** | §2 |
| sitios de emisión de `PACKET3_WAIT_REG_MEM` | **3** (`6047`, `6180`, `6199`) | conteo |
| sitios de emisión de `PACKET3_SURFACE_SYNC` | **1** (`6763`) | conteo |
| sitios de emisión de `PACKET3_ACQUIRE_MEM` | **1** (`6776`) | conteo |
| sitios de emisión de `PACKET3_RELEASE_MEM` | **1** (`6239`) | conteo |
| sitios de emisión de `PACKET3_EVENT_WRITE` | **5** (`1549`, `1575`, `1601`, `6060`, `6064`) | conteo |
| sitios de emisión de `PACKET3_EVENT_WRITE_EOP` | **2** (`6145`, `6159`) | conteo |
| campos de `CP_COHER_CNTL` puestos / totales | **5 / 26** | `gfx_8_0_sh_mask.h:3157-3208` |
| valores distintos de máscara de coherencia en todo el driver | **1** (`0x28C40000`) | §2.1 |
| `emit_frame_size` GFX / COMPUTE / KIQ | **172** dw (chained) o **156** (no chained) / **109** / **77** | §2.2 |
| ancho de los contadores de espera ISA en gfx803 | `vmcnt` bits[3:0] (4), `expcnt` bits[6:4] (3), `lgkmcnt` bits[12:8] (5) | ver §4.4 |
| pasos de preámbulo CE/DE | 2 y 3 | `gfx_v8_0.c:4151-4152`, `4177-4178` |

**La granularidad de la máscara de coherencia tiene CERO grados de libertad en el
driver.** No es que el knob esté a un valor amplio: es que **no existe**. Ni variable,
ni parámetro, ni función alternativa, ni `if`. `gfx_v8_0_emit_mem_sync` y
`gfx_v8_0_emit_mem_sync_compute` emiten la misma constante literal en las dos funciones.
Verificado sobre el texto completo de ambas (`6761-6772`, `6774-6787`).

### 4.2 NO MEDIBLE: contador de hardware

El coordinador indica que otro nodo está midiendo el path de perfmon de GFX8 y que no
se repita. Lo no repito. Lo que **sí** aporto y es propio de este nodo es el
inventario de lo que el registro de GFX8 define, para que ese nodo no tenga que
rederivarlo:

```
gfx_8_0_d.h: 2800 defines de registro.
buscando BARRIER|SBAR      -> [] (0)
buscando ATOMIC            -> 22 nombres, TODOS son registros de PREOP de atomic
                               (mmCP_{PFP,ME,HQD,GDS}_ATOMIC{0,1}_PREOP_{LO,HI},
                                mmCP_ATOMIC_PREOP_{LO,HI},
                                mmTC_CFG_L2_ATOMIC_POLICY)
```

Es decir: **no existe ningún registro contador de barreras retiradas en el
header de GFX8.** Lo más cercano es estado, no contador:

```
mmGRBM_STATUS      0x2004  (d.h:862)   GUI_ACTIVE, CP_BUSY, TC_BUSY, VGT_BUSY,
                                         PA_BUSY, SC_BUSY, SPI_BUSY, CB_BUSY, DB_BUSY,
                                         SX_BUSY, WD_BUSY, TA_BUSY, IA_BUSY,
                                         GDS_BUSY, CP_COHERENCY_BUSY, *_CLEAN  (sh_mask 5495-5542)
mmGRBM_STATUS2     0x2002  (d.h:863)   CPC/CPF/CPG_BUSY, RLC_BUSY, TCC_CC_RESIDENT (sh_mask 5543-5578)
mmCP_COHER_STATUS  0xc07f  (d.h:505)   STATUS, PHASE1_STATUS, MATCHING_GFX_CNTX, MEID (sh_mask 3217-3224)
mmSQ_CMD_TIMESTAMP 0x2375  (d.h:2123)  TIMESTAMP (8 bits) (sh_mask 14305-14306)
mmCP_COHER_START_DELAY 0xc07b (d.h:499) START_DELAY_COUNT (sh_mask 3155-3156)
```

`CP_COHER_STATUS.STATUS` y `PHASE1_STATUS` son el **único** punto del corpus donde se
puede observar que una operación de coherencia terminó. Es un bit de estado, no un
contador: no cuenta cuántas barreras hubo, sólo si la última terminó. Un barrido de
máscaras no se puede cerrar con esto. Estado: `NOT_AVAILABLE` para conteo;
`OBSERVABLE` (con escritura a CP, luego hardware) para "¿terminó?".

### 4.3 REQUIERE AUTORIZACIÓN DE HARDWARE

```
1. Medir el coste en tiempo de una coherencia  -> requiere escribir CP_COHER_* y/o
   CP_INT_CNTL para habilitar lectura, y leer mmCP_COHER_STATUS en ventana.
   INTERVENTION_STATUS = CONTROLLED_WRITE. No lo hago aquí.
2. Medir si el EOP señuelo (6b) todavía hace algo -> requiere variar el código del
   driver y un oráculo de fallo. INTERVENTION_STATUS = CONTROLLED_WRITE + ORACLE.
   No existe oráculo en el corpus: no hay forma de observar "falló" sin una prueba
   de correctitud, y el corpus no la tiene.
3. Saber qué máscara pone REALMENTE cada IB de aplicación -> requiere capturar el IB
   de un proceso de usuario. Eso no es MMIO ni hardware: es un problema de
   autorización sobre datos de otro proceso. En este nodo: NO HECHO.
4. Reimplementar el emisor de barreras y medirlo -> eso sí es el trabajo de otro
   nodo; aquí sólo queda establecido que no existe.
```

### 4.4 Medición con codificador independiente (host, sin GPU)

Herramienta: `llvm-mc 22.1.8` (`/usr/bin/llvm-mc`), host local, sin GPU.
Comando reproducible:
`llvm-mc -triple=amdgcn-amd-amdhsa -mcpu=gfx803 -show-encoding -`

```
s_barrier                          -> [0x00,0x00,0x8a,0xbf]   OK    = 0xbf8a0000
s_barrier s0:0                     -> rc=1  error: unknown token in expression
s_end                              -> rc=1  error: invalid instruction
e_end                              -> rc=1  error: invalid instruction
s_end s0:0                         -> rc=1  error: invalid instruction
e_end s0:0                         -> rc=1  error: invalid instruction
global_barrier                     -> rc=1  error: invalid instruction
s_waitcnt vmcnt(0)                 -> [0x70,0x00,0x8c,0xbf]   = 0xbf8c0070
s_waitcnt vmcnt(0) lgkmcnt(0)      -> [0x70,0x00,0x8c,0xbf]   = 0xbf8c0070
s_waitcnt lgkmcnt(7)               -> [0x7f,0x07,0x8c,0xbf]   = 0xbf8c077f
s_waitcnt vmcnt(3) lgkmcnt(6)      -> [0x73,0x06,0x8c,0xbf]   = 0xbf8c0673
s_waitcnt vmcnt(15)                -> [0x7f,0x0f,0x8c,0xbf]   = 0xbf8c0f7f
                                     (llvm lo imprime como vmcnt(15) expcnt(7) lgkmcnt(15))
s_setprio 0 / 1 / -1               -> 0xbf8f0000 | imm16
```

Decodificación de `s_waitcnt` en gfx803, deducida de las cinco codificaciones
anteriores (cada campo se mueve con un valor distinto y solo):

```
low16 = 0x0673  ->  vmcnt    = bits[3:0]   = 3     ✓ pedido 3
                    expcnt   = bits[6:4]   = 7     (no pedido ⇒ máximo)
                    lgkmcnt  = bits[12:8]  = 6     ✓ pedido 6
low16 = 0x077f  ->  lgkmcnt = 7 ✓ ; vmcnt = 0xf
low16 = 0x0070  ->  vmcnt = 0 ✓ ; lgkmcnt = 0 ✓
low16 = 0x0f7f  ->  vmcnt = 15 ✓ ; expcnt = 7 ✓ ; lgkmcnt = 15 ✓
opcode = bits[31:24] de 0xbf8c.... = 0x8c
```

Cross-target (control negativo):

```
s_waitcnt vmcnt(3) lgkmcnt(6)  ->  0xbf8c0673 en gfx803 == gfx900 == gfx1030
                                   distinto en gfx1100 (0xbf890c67)
s_setprio 1                    ->  0xbf8f0001 en gfx803 == gfx900 == gfx1030
                                   distinto en gfx1100 (0xb58f0001)
```

Es decir: **la codificación del contador de espera no cambia entre GFX8, GFX9 y GFX10.**
Consecuencia directa para N-INT-27/28: cualquier diferencia de rendimiento en
precisión de máscara **entre GFX8 y GFX9 no puede venir de la codificación del
contador**. O viene de la semántica del contador, o de otra cosa.

Capacidad atómica medida en gfx803 (feature gate, no error de sintaxis — el mismo
mnemónico pasa con `-mcpu=gfx900`):

```
global_atomic_add / global_atomic_cmpswap  ->  gfx803: "instruction not supported on this GPU"
                                              gfx900/gfx1100: "invalid operand" (sintaxis)
global_load_dword                          ->  gfx803: "instruction not supported on this GPU"
```

`global_*` (direccionamiento L2/unificado) **no existe en gfx803 según la tabla de
features de LLVM**. Esto es un hecho sobre **LLVM**, no sobre el silicio. Ver la
reserva del instrumento más abajo.

---

## 5. EL PREMISA DEL COORDINADOR QUE NO SE SOSTIENE: `s_end` / `e_end`

El enunciado del encargo dice: *"El hardware GFX8 tiene `s_end`/`e_end` de 64 bits
con semántica de barrier de GCN3, y eso es un hecho del corpus"*.

```
NOT_TRACED   — no hay artefacto en este proyecto que lo sostenga.
REFUTED (parcial, en el único ensamblador disponible) — ver tabla §4.4.
```

Evidencia de que no hay artefacto:

```
s_barrier  -> 1 fichero en todo el árbol:  RESEARCH/polaris12xl/LEARNED-GCN3-ISA.md
s_end      -> 0 ficheros
e_end      -> 0 ficheros
(no hay árbol Mesa en el proyecto: no existe si_asm_parser.c ni ac_surface_sync.c)
```

Y `991-el-isa-de-gfx8-si-tiene-fuente-primaria-publicada.md` dice literalmente, sobre el
documento GCN3 ISA (AMD Document_ID 70645): *"El contenido del ISA es `NOT_PROVEN`
aquí. No lo he abierto y no digo que lo haya abierto."* Lo único probado ahí es el
**mapeo** GFX8 → manual GCN3.

Medición propia: `s_end` y `e_end` son **instrucciones inválidas** en
`llvm-mc 22.1.8` para `gfx803`, `gfx900` **y** `gfx1100`. Y `s_barrier` en gfx803 es
**una sola palabra de 32 bits** (`0xbf8a0000`), sin operandos: `s_barrier s0:0` falla
con `unknown token in expression`. No hay par de 64 bits.

**Reserva sobre mi propio instrumento** (esto es lo que hace que la refutación sea
`parcial` y no `total`): el diseño `012-gcn8-assembler-and-isa-corpus.md` ya mide
`AS_TARGET_ENFORCED = REFUTED` — *"el triple NO limita la ISA"*. Y lo confirmo en mis
propias sondas: la mayoría de los `rc=1` que obtuve son **errores de forma de
operando**, no feature gates (`v_mov_b32_d16` y `s_load_dwordx2` fallan en los tres
targets). Por tanto:

- `s_end`/`e_end` inválidos ⇒ prueba que **LLVM 22.1.8 no las conoce**, no que el
  silicio no las tenga.
- `global_*` no soportadas en gfx803 ⇒ prueba que **la tabla de features de LLVM para
  gfx803 no las incluye**, no que el silicio no las tenga.

Lo que resolvería la premisa, y está fuera de este corpus:
`1)` el PDF GCN3 ISA 70645 leído y citado; `2)` el parser de ensamblador de Mesa para
GFX8; `3)` desensamblado de un shader binario real de esta GPU. Ninguno de los tres
está en este árbol. Estado final: **`NOT_DETERMINED`**, con la dirección explícita.

Lo que **sí** queda establecido y es utilizable: el mecanismo de espera a nivel ISA en
gfx803 tiene **tres contadores de ancho fijo** (vmcnt 4 bits, expcnt 3 bits, lgkmcnt 5
bits, §4.4) y `s_barrier` no tiene operando. Eso es el sustrato real sobre el que
operarían N-INT-27 y N-INT-28, y es medible sin GPU.

---

## 6. LA FRONTERA DE UTILIDAD (R-NEW-79 reformulada, marco de N-INT-46)

Lo que el corpus dice, lo que no dice, y por qué la frontera es más estrecha de lo que
parece.

### 6.1 Lo que el corpus SÍ sostiene

**Afirmación A (DERIVATION, refutable).** Una coherencia estrecha es *strictamente*
mejor que una amplia **en bytes de anillo**, y a coste de hardware no mayor.

Razón: `SURFACE_SYNC` tiene **5 dw fijos** (`gfx_v8_0.c:6763-6771`, medido) y
`ACQUIRE_MEM` **7 dw fijos** (`6776-6787`). No hay condicional. Poner 3 bits en vez de
5 **no cuesta ni un dw**. Por tanto "estrecha consume menos ancho de banda de anillo"
es trivialmente cierto y **no es una hipótesis de rendimiento**: es aritmética.

Refutador de A: que exista en el corpus alguna variante de `emit_mem_sync` cuyo tamaño
dependa de la máscara. Buscado: no existe. La afirmación sobrevive.

**Afirmación B (DERIVATION, refutable).** Estrechar la máscara de `SURFACE_SYNC` sin un
modelo de hazards **no es una optimización: es una corrección.** Los 21 campos no
puestos de `CP_COHER_CNTL` incluyen `SH_KCACHE_WB_ACTION_ENA`, `TC_SD_ACTION_ENA`,
`CB_ACTION_ENA`, `DB_ACTION_ENA`, `SH_SD_ACTION_ENA`. Si alguno de esos contiene el
dato que la invalidación protege, quitarlo deja basura. Y el corpus **no dice cuál**.

Refutador de B: evidencia de que los 5 dominios que sí se ponen cubren todos los datos
que un IB de kernel puede tener sucios. No existe tal evidencia en el corpus. B se
sostiene.

### 6.2 Lo que el corpus NO dice

**El corpus no contiene ni una afirmación sobre el coste en tiempo del ámbito de la barrera.**
Cero. No hay comentarios, no hay `Documentation/` (el árbol `Documentation/` de este
corpus tiene **sólo** `Documentation/ABI/testing/sysfs-bus-pci`), no hay commits, no
hay perfiles. Los únicos números de coste que existen son de **ancho de anillo**
(`emit_frame_size`, §2.2), no de **stall**.

Por tanto **la frontera de utilidad no es derivable del corpus.** Es
`NOT_DETERMINED`. Cualquier respuesta a "¿cuándo una barrera estrecha es mejor que una
amplia?" que no venga de una medición es una opinión.

### 6.3 Los dos lados de la frontera, formulados como condiciones refutables

```
CONDICIÓN "estrecha gana"   : el trabajo que la coherencia realiza es proporcional al
                              número de bits de CP_COHER_CNTL puestos. Si es constante
                              (independiente de la máscara), estrecha y amplia cuestan
                              lo mismo y estrecha sólo puede ganar.
                              discriminante: alterar un bit de la máscara y medir
                              CP_COHER_STATUS.PHASE1_STATUS. Requiere hardware. NO HECHO.

CONDICIÓN "estrecha pierde"  : (a) si la operación tiene coste fijo de pipeline
                              (setup) y el trabajo variable es despreciable, estrecha
                              paga el setup sin cobrar el trabajo.
                              (b) si estrechar rompe una dependencia real, como en B.
                              (c) si el compilador/planificador de userspace re-emite
                              la coherencia para cada dependencia separada, entonces
                              "10 estrechas" > "1 amplia" en dw, porque el encabezado
                              de packet + el payload se paga 10 veces. Con 5 dw de
                              payload fijo, 10 separadas = 50 dw frente a 1 = 5 dw.
                              Éste es el caso donde la AGRUPACIÓN gana, y es aritmética,
                              no especulación.
```

El punto (c) es el único sitio donde la respuesta es bastante fácil: **en este
hardware concreto, agrupar es trivialmente mejor que separar, porque el payload de
`SURFACE_SYNC` es de ancho fijo y no escala con el número de dependencias.** N-INT-29
queda por tanto decidible por medida estática, sin GPU. Lo que queda abierto es
cuántas dependencias se pueden meter en un `SURFACE_SYNC` — y eso **no** está en el
corpus, porque `DependencyInfo` no existe aquí (0 ocurrencias en `drivers/gpu/drm`).

---

## 7. SOLAPAMIENTO CON R-NEW-77 / R-NEW-78 — REFACTOR, NO DESCARTE

El encargo dice que si encuentro solapamiento, lo diga, porque el usuario pidió
refactorizar. Lo encuentro, y es grande: **siete ideas son tres ejes.**

```
AXIS A — ÁMBITO Y MÁSCARA (un solo campo, tres granularidades)
  N-INT-26  ámbito:           global vs recurso-específico
  N-INT-27  precisión ETAPA:  ALL_COMMANDS → ALL_GRAPHICS → específica
  N-INT-28  precisión ACCESO: ámbito de etapa vs ámbito de acceso
  N-INT-31  dirección:        vértice→frag, frag→vértice, cómputo→gráficos, …
                              ↑ esto NO es un eje independiente: la dirección es un
                                valor del campo de máscara del eje A.
  ESTRUCTURA EN EL REGISTRO: 26 campos en CP_COHER_CNTL (sh_mask 3157-3208)
                              + VGT_SHADER_STAGES_EN tiene LS/HS/ES/GS/VS_EN
                                (sh_mask 17885-17894, NO usado por el driver)
                              + 32 recursos GWS_RESET0..3 (sh_mask 17173-17236)
                              → 3 campos de distinta naturaleza que la idea llama
                                "máscara" con un solo nombre.

AXIS B — COSTE DE EMISIÓN (propiedad de bytes, medible estáticamente)
  N-INT-29  agrupación:   10 separadas vs 1 con 10
  N-INT-30  distancia:    producto → barrera → consumidor

AXIS C — AUDITORÍA (puerta, no variante)
  N-INT-32  qué dependencia protege cada barrera
```

Contra el registro (`02-ARQUITECTURA/IDEA-REGISTER.md`, sección 13 y sección E):

```
R-NEW-77  "barrido de coste de barreras"          BUENA          (registro §13)
R-NEW-78  "barrido de profundidad de dependencias" BUENA — muy relacionada  (registro §13)
N-INT-26  VARIANT_OF(A-01)
N-INT-27  NUEVA
N-INT-28  NUEVA
N-INT-29  VARIANT_OF(R-NEW-77)
N-INT-30  VARIANT_OF(R-NEW-78)
N-INT-31  NUEVA
N-INT-32  VARIANT_OF(R-NEW-77)
```

**Propuesta de refactor (no de descarte):**

```
R-NEW-77  se mantiene como ÚNICA idea de coste.
          Absorbe: N-INT-29 (agrupación) y N-INT-30 (distancia) — ambos son
          "cuántos bytes y cuántos viajes por el pipe", que es literalmente lo que
          §2.2 ya mide. Y N-INT-32 deja de ser "idea" y pasa a ser el PRE-condición
          de R-NEW-77: no tiene sentido barrer el coste de algo cuya necesidad no se
          ha Established.
          Ganas: 3 barridos que comparten la misma hipótesis y el mismo instrumento.

R-NEW-78  se mantiene como ÚNICA idea de profundidad.
          Absorbe: N-INT-30 si se quiere separar "distancia" (cuántos paquetes entre
          productor y consumidor) de "agrupación" (cuántas barreras por paquete).
          Es el único eje con información que A no tiene.

EJE A     NO tiene idea propia hoy. N-INT-26/27/28/31 son cuatro formulaciones del
          mismo campo de 26 bits. Y ese campo tiene **cero grados de libertad** en el
          driver actual (§4.1), así que el eje no es un experimento: es una
          CONSTRUCCIÓN. Esto debería ser una idea de tipo IMPLEMENTATION, no
          EXPERIMENT, y su bloqueante es la reconstrucción del emisor de barreras
          desde la especificación de PM4 de GFX8 — que, según 033, no está publicada.
```

Nota de numeración: el encargo menciona "N-INT-78 BUENA, muy relacionada".
**`N-INT-78` no existe** en `02-ARQUITECTURA/IDEA-REGISTER.md` (0 ocurrencias en todo
el árbol). La idea marcada "**BUENA — muy relacionada**" es **`R-NEW-78`** (sección
13 del mismo fichero). **No he creado ningún ID nuevo ni he renumerado nada.**
Registro la discrepancia de notación en lugar de resolverla por mi cuenta.

---

## 8. RESUMEN DE ESTADOS (nada se promueve sin refutador)

| Afirmación | Estado | Refutador nombrado |
|---|---|---|
| `gfx_v8_0.c` no emite barreras | `PROVEN` (conteo=0, y el IB de usuario es opaco: `amdgpu_cs.c:381-391` + `parse_cs`=NULL para GFX8) | que aparezca un `PACKET3_ATOMIC*` en `gfx_v8_0.c` |
| El opcode existe pero sus bits no, en el kernel | `PROVEN` | que `vid.h`/`sid.h` contengan `PACKET3_ATOMIC_MEM__*` |
| 9 primitivos de sincronización emitidos | `PROVEN` (contadas) | — |
| La máscara de coherencia tiene 0 grados de libertad | `PROVEN` | que exista una 2ª constante de máscara distinta de `0x28C40000` |
| El driver no pone ningún `*_DEST_BASE_ENA` | `PROVEN` | que aparezca uno en `6764-6768`/`6777-6781` |
| 3 barreras con dependencia no nombrable | `PROVEN_ABSENT` del nombre (buscado en 4 ficheros) | un comentario que nombre el hazard |
| 172 dw de frame con chained IB | `PROVEN_DERIVED` (suma de `6878-6896`; 14 y 31 confirmados contra `vi_structs.h`) | que la suma dé otra cosa |
| El comentario "215dw" no cuadra (172+16×4=236) | `CONTRADICTION` **abierta** | que 215 sea correcto bajo alguna lectura |
| `s_end`/`e_end` de 64 bits | `NOT_TRACED` + `REFUTED` en LLVM 22.1.8 | el PDF GCN3 ISA 70645, o el parser de Mesa |
| Codificación de `s_waitcnt` (3 contadores, anchos fijos) | `OBSERVED` (codificador, 5 muestras) | una 6ª muestra que contradiga el decodificado |
| `global_*` no soportado en gfx803 | `OBSERVED` (tabla de features de LLVM) | que `-mcpu=gfx803` ensamble un `global_*` |
| No hay registro contador de barreras en GFX8 | `PROVEN_ABSENT` (2800 defines, filtro `BARRIER\|SBAR` → []) | un define con ese nombre en `gfx_8_0_d.h` |
| Coste en tiempo según el ámbito de la barrera | `NOT_DETERMINED` — el corpus no lo dice | una medición con `CP_COHER_STATUS` |
| "Estrecha gana / amplia gana" | `NOT_DETERMINED` — §6.3 da las condiciones, no la respuesta | — |

---

## 9. Lo que queda abierto, y por qué no lo cierro

1. **`s_end`/`e_end`.** El encargo lo daba por hecho del corpus y no lo está. No lo
   doy por bueno ni por falso: no hay artefacto. Lo que hace falta está enumerado en §5.
2. **El emisor de barreras de GFX8.** No existe en el kernel. Reconstruirlo exige la
   especificación de PM4 de GFX8, que este proyecto ya marca como `NOT_PUBLISHED`
   (`033-pm4-spec-gfx8-no-existe`). Sin eso, N-INT-26/27/28/29/31 no tienen objeto.
3. **Las barreras del usuario.** Fuera del corpus por construcción (§1.3). No es una
   ausencia de herramienta: es que el dato no está en el material.
4. **Qué de los 5 dominios de `CP_COHER_CNTL` contiene el hazard que `#4` protege.**
   Ésta es la pregunta que más vale y la que menos se puede responder aquí.
5. **Si el EOP señuelo de `gfx_v8_0.c:6145` sigue siendo necesario en gfx803.** No hay
   forma de desactivarlo ni oráculo para comprobarlo.

Nada de lo anterior se convierte en plan. Son huecos con su causa y con el artefacto
que los cerraría.

---

## 10. Reproducibilidad de las mediciones

Todas estáticas: `open()` + `os.walk()` sobre `RESEARCH/baseline/linux-7.1.3`, sin
`grep`. Todos los codificadores: `llvm-mc` local, sin GPU, sin MMIO, sin escribir en el
árbol (los `.o` temporales fueron a `/tmp`).

```
FILES_MODIFIED_IN_TREE = 1  (08-ARQUITECTURA/BARRERAS-GFX8.md)
GPU_TOUCHED            = NO
DMESG_JOURNALCTL       = NO
DEBUGFS                = NO
GREP_USED              = NO
GIT_ADD / GIT_COMMIT   = NO
FINDINGS_RENUMBERED    = NO
```
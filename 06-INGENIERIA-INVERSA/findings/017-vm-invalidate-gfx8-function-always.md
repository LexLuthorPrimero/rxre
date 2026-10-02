# 017 · GFX8 vm-invalidate: `FUNCTION(0)=always` NO prueba completion

`CLASSIFICATION=DOCUMENTATION` · `TRACK=STATIC` · `CORPUS=rx550-upstream-7.2.8/linux-7.2.8`
`WORK_CLASS=READ_ONLY/EVIDENCE` · `WRITE_EXECUTION=NONE` · `MODIFICATIONS=0`

## CUDA principal

La secuencia de `vm_flush` en GFX8 no espera a la finalización de la invalidación:
espera con `FUNCTION(0)=always`, `ref=0`, `mask=0`. Ningún bit se compara. Por tanto
**la secuencia no aporta evidencia de completion**, y la afirmación previa de
`29⁄9⁄26.md:169` ("WAIT_REG_MEM espera REQUEST == 0") queda `REFUTED` a nivel de encoding.

## Alcance exacto

1. Localizar todas las emisiones de `VM_INVALIDATE_*` alcanzables en Polaris12.
2. Resolver el encoding de `PACKET3_WAIT_REG_MEM` tal como lo construye el driver GFX8.
3. Determinar qué registro y qué comparación consume cada `WAIT_REG_MEM` del path.
4. Clasificar qué queda PROVEN, qué queda NOT_DETERMINED, y qué afirmación previa se refuta.

## Criterio de terminación (cumplido)

Todas las emisiones de `VM_INVALIDATE_*` del árbol GFX8 están localizadas y su encoding
resuelto hasta el campo comparado. Agotado.

---

## 1 · Productores de la invalidación en GFX8

`grep -rn "PAGE_TABLE_INVALIDATE" rx550-upstream-7.2.8/…/amd/` → **0 resultados**.

Ese paquete PM4 es de la familia GFX9+/MMHUB (`PACKET3_INVALIDATE_TLBS`, definido en
`gfx_v9_0.c:1035`). **No existe en GFX8.** Es `NOT_AVAILABLE` por objeto, no por lectura
parcial: el token no aparece en ningún `.c` ni `.h` del árbol, y `gfx_v8_0.c` no tiene
`kiq_invalidate_tlbs` (`grep -c` = 0) ni `invalidate_tlbs_size`.

Consecuencia: la rama `amdgpu_gmc.c:823-856` (KIQ + `invalidate_tlbs_size`) es
**inalcanzable en Polaris12**. El mecanismo GFX8 es un **registro MMIO directo**, no un
paquete.

Tres emisores, todos en `gmc_v8_0.c`:

| # | Emisor | Path | Mecanismo | Lectura de completion |
|---|---|---|---|---|
| E1 | `gmc_v8_0_flush_gpu_tlb` :655 | CPU (KIQ init, `gmc_v8_0_gart_enable` :935) | `WREG32(mmVM_INVALIDATE_REQUEST, 1 << vmid)` | **ninguna** |
| E2 | `gmc_v8_0_emit_flush_gpu_tlb` :662 | ring (WREG en PM4) | `emit_wreg(PTBA)` luego `emit_wreg(mmVM_INVALIDATE_REQUEST, 1<<vmid)` | **ninguna** |
| E3 | `gmc_v8_0_flush_gpu_tlb_pasid` :619 | CPU (KFD pasid flush) | barre `mmATC_VMID0_PASID_MAPPING+vmid` vmid 1..15, `WREG32(REQUEST, mask)` | `RREG32(mmVM_INVALIDATE_RESPONSE)` **descartado** |

E1 es notable: acepta `vmhub` y `flush_type` y **los ignora**. Los parámetros existen en
la interfaz pero no llegan al hardware en esta ruta (`gmc_v8_0.c:655-660`). Para un
driver propio, esa firma engaña: no promete lo que hace.

E3 lee `RESPONSE` y tira el valor (`gmc_v8_0.c:635`). Se consume por **efecto de lectura**,
no por decisión. `Captured is not consumed`.

## 2 · Registro: no hay un canal de request/response utilizable

`gmc/gmc_8_2_d.h:617-618` (y `gmc_8_1_d.h:615-616`, mismo offset):

```
mmVM_INVALIDATE_REQUEST   0x51e
mmVM_INVALIDATE_RESPONSE  0x51f
```

`gmc_8_2_sh_mask.h:6589-6652`:

```
REQUEST  bits 0..15  = INVALIDATE_DOMAIN_0 .. INVALIDATE_DOMAIN_15   (MASK 1<<n, SHIFT n)
RESPONSE bits 0..15  = DOMAIN_INVALIDATED_0 .. DOMAIN_INVALIDATED_15
```

Relación útil: `REQUEST` es un mapa de 16 dominios = **16 VMIDs**, uno por bit. No es un
puerta con token; no hay `ack` que correlacionar con una petición concreta. `RESPONSE`
tiene la forma que tendría un "done por dominio", y existe en GFX6/7/8, pero el driver
**no lo lee para decidir nada** (únicos `RREG32` en `gmc_v7_0.c:444` y `gmc_v8_0.c:635`,
ambos con resultado descartado).

Esto es la frontera abierta de AGENTS.md:140-143, y ahora tiene nombre exacto.

## 3 · El `WAIT_REG_MEM` del vm_flush no compara

`gfx_v8_0.c:6197-6221`, `gfx_v8_0_ring_emit_vm_flush`:

```c
int usepfp = (ring->funcs->type == AMDGPU_RING_TYPE_GFX);
amdgpu_gmc_emit_flush_gpu_tlb(ring, vmid, pd_addr);     // E2

amdgpu_ring_write(ring, PACKET3(PACKET3_WAIT_REG_MEM, 5));
amdgpu_ring_write(ring, (WAIT_REG_MEM_OPERATION(0) |   /* wait_reg_mem */
                         WAIT_REG_MEM_FUNCTION(0) |    /* always  */
                         WAIT_REG_MEM_ENGINE(0)));      /* me      */
amdgpu_ring_write(ring, mmVM_INVALIDATE_REQUEST);
amdgpu_ring_write(ring, 0);      /* ref  */
amdgpu_ring_write(ring, 0);      /* mask */
amdgpu_ring_write(ring, 0x20);   /* poll interval */

if (usepfp) {
    /* sync PFP to ME, otherwise we might get invalid PFP reads */
    amdgpu_ring_write(ring, PACKET3(PACKET3_PFP_SYNC_ME, 0));
    amdgpu_ring_write(ring, 0x0);
}
```

Encoding, de `vid.h:169-189` (el header que incluye `gfx_v8_0.c:35`; **no** `sid.h`, que
carece de `WAIT_REG_MEM_OPERATION` — `grep` en `sid.h` rc=1):

```
WAIT_REG_MEM_FUNCTION(x)  (x << 0)   0=always 1=< 2=<= 3=== 4=!= 5=>= 6=>
WAIT_REG_MEM_MEM_SPACE(x)(x << 4)   0=reg    1=mem
WAIT_REG_MEM_OPERATION(x)(x << 6)   0=wait_reg_mem  1=wr_wait_wr_reg
WAIT_REG_MEM_ENGINE(x)   (x << 8)   0=me     1=pfp
```

Con `FUNCTION=always`, `ref=0`, `mask=0`: **la condición es vacía**. Los otros dos emisores
del mismo ring sí comparan, lo que hace el contraste discriminante dentro del propio corpus:

| Emisor | Línea | FUNCTION | ref | mask | ¿Compara? |
|---|---|---|---|---|---|
| `gfx_v8_0_ring_emit_hdp_flush` | 6053-6061 | `3` (`==`) | `ref_and_mask` | `ref_and_mask` | **sí** |
| `gfx_v8_0_ring_emit_fence` | 6186-6194 | `3` (`==`) | `seq` | `0xffffffff` | **sí** |
| `gfx_v8_0_ring_emit_vm_flush` | 6205-6213 | `0` (`always`) | `0` | `0` | **no** |

El `mask=0` es lo decisivo: incluso si la función fuera `==`, `(reg & 0) == (0 & 0)` es
`0 == 0`, verdadero en la primera lectura. Un `mask=0` no puede discriminar completion.

## 4 · CONTRADICTION

`29⁄9⁄26.md:166-171` declara `[CLOSED] WAIT_REG_MEM espera REQUEST == 0`.

Es `REFUTED`. La codificación es `FUNCTION=0` (`always`), no `3` (`==`). El documento
confundió `ref=0` con una comparación contra cero: el valor de `ref` no es el operando
cuando `FUNCTION=always`. Corregido explícitamente aquí; el error estaba en leer la
constante `0` como el predicado.

Lo que sí era correcto en ese documento y se conserva: `mecanismo de invalidación GFX8`
`PROVEN`, `request por VMID` `PROVEN` (E1/E2 escriben `1 << vmid` en un mapa de 16
dominios), y `no es prueba de completion explícito` `PROVEN`.

## 5 · Qué queda abierto, con nombre

| Afirmación | Estado | Condición que la refutaría / resolvería |
|---|---|---|
| `WAIT_REG_MEM` con `FUNCTION=always` sobre `REQUEST` no prueba completion | `PROVEN` (encoding) | — |
| Qué garantiza hardware el intervalo `0x20` sin comparación | `NOT_DETERMINED` | Discriminante runtime: escribir un PM4 `WAIT_REG_MEM always` y un `RREG32` de `REQUEST` entre `IB`s, con un VMID cuyo invalidate se retrase artificialmente. Requiere RUNTIME. |
| Efecto real de `VM_CONTEXT{n}_PAGE_TABLE_BASE_ADDR` sobre traducciones cacheadas | `NOT_DETERMINED` | Igual: exige RUNTIME, y confounders (TLB preexistente, `NO_INVALIDATION` en `ATC_VMID{n}_PASID_MAPPING` bit 30) |
| `FUNCTION=always` **hardware trigger** (AGENTS.md:138) | `NOT_DETERMINED`, y **reformulado** | No es "cuándo dispara el trigger" sino "qué significa un wait sin predicado". Se resuelve por spec PM4 de GFX8 o por runtime. |
| Si `VM_INVALIDATE_RESPONSE` puede dar completion observable por dominio | `NOT_DETERMINED` | El hardware lo publica y el driver lo ignora. Nadie lo ha leído observando el valor. RUNTIME. |
| Invalidación de L2 cache de traducciones (`MC_VM_MB_L1_TLB0_DEBUG__INVALIDATE_L1_TLB`) | `NOT_OBSERVED` en corpus | `gmc_8_2_sh_mask.h:3959` lo define (debug), ningún `.c` lo escribe. Requiere barrido de alcance completo antes de llamarlo ausente. |

## 6 · Confounders registrados

Aplicando CONFUNDER MATRIX a cualquier discriminante runtime sobre este path:
VMID reuse · TLB preexistente · estado de cache · power state · BAR mapping · selección
de ring (`usepfp` cambia el sufijo) · ring scheduler · concurrent workloads.

Nótese un confounder específico: `ATC_VMID{n}_PASID_MAPPING__NO_INVALIDATION` bit 30
(`gmc_8_2_sh_mask.h:6071-6072`, y `athub_1_0_sh_mask.h:236`) existe para **suprimir**
invalidación. `grep -rn "NO_INVALIDATION" amdgpu/*.c` → 0: nadie lo escribe en GFX8. Si
alguna vez se activara, invalidar ese VMID no invalidaría. `PROVEN` que el bit existe y
`PROVEN` que el driver no lo usa; `NOT_DETERMINED` su efecto en hardware.

## 7 · Cadena de derivación

```
software: amdgpu_vm_flush (amdgpu_vm.c:842-844)
   → ring->funcs->emit_vm_flush = gfx_v8_0_ring_emit_vm_flush   [gfx_v8_0.c:6904]
   → amdgpu_gmc_emit_flush_gpu_tlb → gmc_v8_0_emit_flush_gpu_tlb [gmc_v8_0.c:662]
        emit_wreg(PTBA, pd_addr>>12)          [REG_SET: 2 WREG, gmc_v8_0.c:667-671]
        emit_wreg(mmVM_INVALIDATE_REQUEST, 1<<vmid)
   → PACKET3_WAIT_REG_MEM, FUNCTION=0, ref=0, mask=0, poll=0x20   ← NO compara
   → PACKET3_PFP_SYNC_ME 0x0                     [sólo ring GFX, usepfp]
hardware:REQUEST=0x51e 16 dominios  →  TLB re-walk
          [completion: no consumido por ninguna lectura en el path]
```

`PTBA → INVALIDATE → WAIT(no-op) → PFP_SYNC_ME → next IB`. El orden de **emisión software**
está `PROVEN_DERIVED`. El orden de **ejecución hardware** sigue `NOT_PROVEN`
(AGENTS.md:141, sin cambios).

## 8 · UNLOCKS

- La capa TLB/invalidate del driver propio **no necesita** `PACKET3_INVALIDATE_TLBS` ni
  KIQ. Basta `WREG32(0x51e, 1<<vmid)` + un mecanismo real de completion. `MODEL_CHOICE`
  libre por DESIGN_FREEDOM, y ahora con la obligación explícita de no copiar la rama GFX9+.
- `NO_INVALIDATION` (bit 30) queda identificado como terreno conocido: si alguna vez hace
  falta invalidar un VMID "permanente", ahí está el registro.
- La rama `amdgpu_gmc.c:823-856` (KIQ/`invalidate_tlbs_size`) se puede marcar
  `NOT_APPLICABLE` para Polaris12 en el árbol de referencia, con causa.

## 9 · Criterio de falsificación de este documento

Se refutaría si: (a) apareciera un cuarto emisor de `VM_INVALIDATE_REQUEST` en GFX8 que sí
consuma `RESPONSE` por decisión; (b) el hardware definiera `FUNCTION=always` como
"esperar hasta REQUEST==0" contra la especificación PM4 de GFX8, lo que reabriría §4 y
haría `REFUTED` incorrecto; (c) `WAIT_REG_MEM_OPERATION` tuviera otro valor que 0 en
`vid.h`. Ninguna de las tres se puede comprobar en este corpus; (b) y (c) quedan
`NOT_DETERMINED` y se marcan `PROVISIONAL`.

## 10 · Evidencia

```
fichero:      rx550-upstream-7.2.8/linux-7.2.8/drivers/gpu/drm/amd/
sha256:       12e8d5a973d1ad7c5a5c69882e4022b131ed715db7003fdcd760ddf8c3e51941
              linux-7.2.8.tar.xz  — recalculado aquí; coincide con upstream.sha256 y local.sha256
LIMITACIÓN:   upstream.sha256 y local.sha256 guardan el hash **sin nombre de fichero**, así que
              `sha256sum -c` falla ("no properly formatted checksum lines"). El hash cubre el
              .tar.xz, NO el árbol extraído. Que el árbol extraído corresponda a ese tarball
              es PROVISIONAL (no re-extraído ni re-verificado).
gmc_v8_0.c:            619-636, 655-660, 662-677, 935, 1728-1731
gfx_v8_0.c:        6053-6061, 6186-6194, 6197-6221, 6352-6372, 6884, 6904, 6932, 6967
amdgpu_gmc.c:    805-856, 809-830
amdgpu_vm.c:     842-844
vid.h:           169-189          vi.h:27
gmc/gmc_8_2_d.h: 617-618, 609
gmc/gmc_8_2_sh_mask.h: 6589-6652, 6071-6072
gmc/gmc_8_1_d.h: 615-616
gfx_v9_0.c:      1031-1041        (contraste: PAQUETE que GFX8 NO tiene)
amdgpu/sid.h:    sin WAIT_REG_MEM_OPERATION (grep rc=1)
```

Todos los valores de arriba leídos directamente en el árbol. Ningún registro obtenido de
MMIO en hardware; ninguna operación runtime; `GPU INTACTA`.
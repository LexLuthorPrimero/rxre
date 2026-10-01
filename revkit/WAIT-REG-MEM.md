# WAIT_REG_MEM en GFX8: qué valores emite el driver, no qué admite el comentario

## La distinción que faltaba

El proyecto tenía `FUNCTION=always` marcado como:

- `PROVEN` a nivel de **encoding**: el driver escribe `WAIT_REG_MEM_FUNCTION(0)`.
- El **hardware trigger** de `always`: `NOT_DETERMINED`.

El comentario de `cikd.h:295-301` lista los siete valores:

```c
#define WAIT_REG_MEM_FUNCTION(x)  ((x) << 0)
/* 0 - always
 * 1 - <
 * 2 - <=
 * 3 - ==
 * 4 - !=
 * 5 - >=
 * 6 - >
 */
```

Eso es **documentación upstream**, no evidencia de lo que el hardware hace. Y es
un comentario: nadie lo compila ni lo comprueba. Lo que importa es qué emite el
driver para este ASIC.

## Qué emite GFX8, por enumeración

`./cidx.py use WAIT_REG_MEM_FUNCTION` sobre los 625 ficheros del corpus:

| fichero | valor | comentario en el código |
|---|---|---|
| `gfx_v7_0.c:3149` | `FUNCTION(0)` | `always` |
| `gfx_v7_0.c:3106` | `FUNCTION(3)` | `equal` |
| `gfx_v8_0.c:6201` | `FUNCTION(0)` | `always` |
| `gfx_v8_0.c:6049` | `FUNCTION(3)` | `==` |
| `gfx_v8_0.c:6182` | `FUNCTION(3)` | `equal` |
| `gfx_v9_0.c:1182` | `FUNCTION(3)` | `equal` |
| `gfx_v9_4_3.c:404` | `FUNCTION(3)` | `equal` |

**Para GFX8 el driver emite exactamente dos valores: `0` y `3`.** Los otros
cinco (`<`, `<=`, `!=`, `>=`, `>`) están documentados pero no los emite ninguna
ruta alcanzable de este ASIC.

Eso es `NOT_OBSERVED` para los cinco, no `PROVEN_ABSENT`: existen en el
comentario y el hardware podría admitirlos, pero el driver de referencia no los
usa con GFX8.

## Las tres funciones de GFX8 que emiten WAIT_REG_MEM

No es uno, son tres, y solo una usa `always`:

| función | `FUNCTION` | a qué espera |
|---|---|---|
| `gfx_v8_0_ring_emit_hdp_flush` | `3` (`==`) | Compare `seq` con `mmVM_HDP` |
| `gfx_v8_0_ring_emit_pipeline_sync` | `3` (`==`) | Compare con un valor de secuencia |
| `gfx_v8_0_ring_emit_vm_flush` | **`0` (`always`)** | `mmVM_INVALIDATE_REQUEST` |

**`always` está reservado para el invalidate del TLB.** Ninguna otra flush de
GFX8 lo usa. Eso es información de diseño que no está en el comentario del
header: el comentario enumera los valores, y el código dice para qué sirve
cada uno.

## La cadena completa de `emit_vm_flush`

Resuelta con `./cidx.py cadena amdgpu_gmc_emit_flush_gpu_tlb`, que sigue macro →
vtable → implementación:

```
1. macro  amdgpu_gmc_emit_flush_gpu_tlb        amdgpu_gmc.h:371
          (r)->adev->gmc.gmc_funcs->emit_flush_gpu_tlb(...)

2. vtable .emit_flush_gpu_tlb = gmc_v8_0_emit_flush_gpu_tlb
                              gmc_v8_0.c:1736

3. cuerpo  gmc_v8_0.c:668
```

Y ese cuerpo es (`gmc_v8_0.c:668-681`):

```c
static uint64_t gmc_v8_0_emit_flush_gpu_tlb(struct amdgpu_ring *ring,
					    unsigned int vmid, uint64_t pd_addr)
{
	uint32_t reg;

	if (vmid < 8)
		reg = mmVM_CONTEXT0_PAGE_TABLE_BASE_ADDR + vmid;
	else
		reg = mmVM_CONTEXT8_PAGE_TABLE_BASE_ADDR + vmid - 8;
	amdgpu_ring_emit_wreg(ring, reg, pd_addr >> 12);

	/* bits 0-15 are the VM contexts0-15 */
	amdgpu_ring_emit_wreg(ring, mmVM_INVALIDATE_REQUEST, 1 << vmid);

	return pd_addr;
}
```

Dos detalles que no están en los documentos del proyecto:

1. **El registro de PTBA depende del VMID.** Para `vmid < 8` es
   `mmVM_CONTEXT0_PAGE_TABLE_BASE_ADDR + vmid`; para `vmid >= 8` es
   `mmVM_CONTEXT8_PAGE_TABLE_BASE_ADDR + vmid - 8`. **Son dos registros
   distintos**, no un array con desplazamiento. Escribiendo siempre el
   primero, los VMID ≥ 8 no se actualizan.

2. **`pd_addr >> 12`**: se escribe el PFN, no la dirección byte. El PTBA
   contiene el PFN con el shift aplicado.

3. **`1 << vmid` en INVALIDATE_REQUEST**: el log dice «bits 0-15 are the VM
   contexts0-15», luego solo hay 16 bits y **VMID ≥ 16 no sería representable**.
   El hardware tiene más VMs que bits; el limite es del registro de invalidate.

## Y el `PFP_SYNC_ME` condicional

`gfx_v8_0_ring_emit_vm_flush` (`gfx_v8_0.c:6189`) termina con:

```c
	/* compute doesn't have PFP */
	if (usepfp) {
		/* sync PFP to ME, otherwise we might get invalid PFP reads */
		amdgpu_ring_write(ring, PACKET3(PACKET3_PFP_SYNC_ME, 0));
		amdgpu_ring_write(ring, 0x0);
	}
```

Donde `usepfp = (ring->funcs->type == AMDGPU_RING_TYPE_GFX)`. El comentario da
el porqué: sin el sync, el PFP puede leer valores inválidos.

Esto **corrobora** lo que el proyecto ya tenía, y añade el criterio del
condicional: es por **tipo de ring**, no por ASIC. Un ring de compute en la
misma GPU no lo emite.

## Secuencia de `emit_vm_flush` para GFX8, completa

```
1. PTBA          amdgpu_ring_emit_wreg(reg_PTBA(vmid), pd_addr >> 12)
2. INVALIDATE    amdgpu_ring_write(mmVM_INVALIDATE_REQUEST, 1 << vmid)
3. WAIT          PACKET3(WAIT_REG_MEM, 5)
                 WAIT_REG_MEM_OPERATION(0)     /* wait    */
                 WAIT_REG_MEM_FUNCTION(0)      /* always  */
                 WAIT_REG_MEM_ENGINE(0)        /* me      */
                 + mmVM_INVALIDATE_REQUEST
                 + 0 (ref) + 0 (mask) + 0x20 (poll interval)
4. PFP_SYNC_ME   solo si ring->funcs->type == AMDGPU_RING_TYPE_GFX
```

Paso 1 y 2 vienen de `gmc_v8_0_emit_flush_gpu_tlb` (vía la macro), pasos 3 y 4
de `gfx_v8_0_ring_emit_vm_flush`. **Son dos funciones distintas** en la misma
operación: eso no se ve leyendo una de las dos.

## Clasificación

| Afirmación | Estado |
|---|---|
| GFX8 emite `FUNCTION` 0 y 3 | **PROVEN** — enumeración sobre 625 ficheros |
| Los valores 1, 2, 4, 5, 6 los emite el driver de GFX8 | **NOT_OBSERVED** — el driver no los usa |
| El hardware admite 1, 2, 4, 5, 6 | **NOT_DETERMINED** — solo lo dice un comentario |
| `always` se usa solo para el invalidate del TLB | **PROVEN** — las tres funciones, enumeradas |
| PTBA son dos registros distintos según VMID | **PROVEN** — `gmc_v8_0.c:673-676` |
| PTBA recibe el PFN con `>> 12` | **PROVEN** — `gmc_v8_0.c:677` |
| `INVALIDATE_REQUEST` cubre VMID 0-15 | **PROVEN** — comentario del código y `1 << vmid` |
| Qué hace el hardware con `always` | **NOT_DETERMINED** — requiere runtime con root |
| `PFP_SYNC_ME` depende del tipo de ring | **PROVEN** — `gfx_v8_0.c:6207` |

Lo que sigue abierto es el mismo de antes y no se puede cerrar estáticamente:
qué **efecto** tiene en el hardware `FUNCTION=0`. Que el driver lo emita para el
invalidate del TLB es `PROVEN`; que eso signifique «esperar a que el invalidate
termine» es una inferencia razonable pero no medida.

## Reproducir

```sh
./cidx.py use WAIT_REG_MEM_FUNCTION      # los 7 usos del corpus
./cidx.py cadena amdgpu_gmc_emit_flush_gpu_tlb   # macro -> vtable -> cuerpo
./regs.py --find mmVM_CONTEXT0_PAGE_TABLE_BASE_ADDR
```

Sin root. `GPU INTACTA`, `WRITE_EXECUTION NONE`.
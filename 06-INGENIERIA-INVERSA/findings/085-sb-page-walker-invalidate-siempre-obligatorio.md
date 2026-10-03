# 085 · §B: en GFX8 el invalidate es SIEMPRE obligatorio, y el comentario que lo dice está en el driver

```
CLASSIFICATION=DOCUMENTATION · TRACK=STATIC · CORPUS=RESEARCH/working/linux-7.1.3
HARDWARE_SCOPE=HOST-C/RX550/0000:01:00.0 · WORK_CLASS=READ_ONLY/EVIDENCE
WRITE_EXECUTION=NONE · MODIFICATIONS=0 · RUNTIME=NOT_RUN · GPU INTACTA
```

## Qué resuelve

`AGENTS.md` §B pide resolver *VA → root → PDE → PTE → physical address*, y
determinar niveles, `root_level`, `num_level`, page size, fragmentación, entradas
inválidas y faults de permisos.

La geometría ya está cerrada (`064`, `068`). Lo que faltaba era **el
recorrido**: qué obliga al driver a invalidar después de escribir la tabla. Y
está en dos líneas de comentario que nadie había leído.

## El hecho, textual

```
amdgpu_vm.c:1154   /*
amdgpu_vm.c:1155    * On GFX8 and older any 8 PTE block with a valid bit set enters the TLB
amdgpu_vm.c:1156    */
amdgpu_vm.c:1157   flush_tlb |= amdgpu_ip_version(adev, GC_HWIP, 0) < IP_VERSION(9, 0, 0);
```

**En GFX8, cualquier bloque de 8 PTEEs con un bit de válido entra en la TLB.**

Y la condición evalúa a verdadero para esta GPU, verificado:

```
gfx_v8_0.c:7128   const struct amdgpu_ip_block_version gfx_v8_0_ip_block = {
gfx_v8_0.c:7131       .major = 8,
gfx_v8_0.c:7132       .minor = 0,
gfx_v8_0.c:7133       .rev   = 0,
```

`IP_VERSION(8,0,0) < IP_VERSION(9,0,0)` → verdadero. **`needs_flush` es
`True` siempre en esta ruta**, no condicionalmente.

## Por qué eso importa más de lo que parece

Conecta tres cosas que estaban separadas:

| hecho | de dónde |
|---|---|
| `block_size = 10`, o sea 2 bits de block size en `PAGE_TABLE_BLOCK_SIZE` | `C-009`, `064` |
| `fragment_size = 9` | `AGENTS.md` L152, observado en el log |
| **"cualquier bloque de 8 PTEEs con válido entra en la TLB"** | `amdgpu_vm.c:1155` |

> **CORRECCION (088). Esta seccion estaba mal.** Escribi que `fragment_size = 9`
> es "8 PTEEs por bloque de fragmentacion". **Es falso: son 512.**
>
> ```
> amdgpu_kms.c:1006   pte_fragment_size = (1 << fragment_size) * AMDGPU_GPU_PAGE_SIZE
> amdgpu_gart.h:35   #define AMDGPU_GPU_PAGE_SIZE 4096
>
> (1 << 9) * 4096 = 2.097.152 bytes = 2 MiB = 512 PTEEs de 4 KiB
> ```
>
> El "8 PTE block" del comentario de L1155 son 8 PTEEs de 4 KiB = **32 KiB**.
> Difieren por **64x**. Son dos cosas distintas:
>
> | | software | hardware |
> |---|---|---|
> | que | `fragment_size = 9` | "8 PTE block" |
> | cuanto | 512 PTEEs = 2 MiB | 8 PTEEs = 32 KiB |
> | quien lo usa | el driver, al escribir el fragmento | el hardware, al llenar la TLB |
>
> El error fue de nuevo **identificar dos numeros que aparecen juntos**. La
> conclusion central de este hallazgo —que el invalidate es obligatorio en GFX8—
> **no depende de esta seccion y sigue en pie**: se sostiene en L1157 y en
> `gfx_v8_0.c:7131-7133`, verificados.
>
> Lo que si se sostiene, y es lo que `195` demuestra: `fragment_size` va a
> `VM_L2_CNTL3.BANK_SELECT` y `L2_CACHE_BIGK_FRAGMENT_SIZE`
> (`gmc_v8_0.c:865-869`), o sea **el fragmento de 2 MiB es el grano del L2**.

**Consecuencia operativa, y es la que no estaba escrita:** en GFX8 no hay
"escribir la tabla y seguir". Cada bloque de 8 PTEEs que se toca exige un
invalidate. Un driver propio que actualice 8 PTEEs sin invalidar deja la TLB
coherente con la tabla antigua, y la traducción devuelta será la anterior sin
ninguna señal de error.

Y hay una segunda condición, para otra generación:

```
amdgpu_vm.c:1148   /* Vega20+XGMI where PTEs get inadvertently cached in L2 texture cache,
amdgpu_vm.c:1149    * heavy-weight flush TLB unconditionally.
amdgpu_vm.c:1151    */
amdgpu_vm.c:1152   flush_tlb |= adev->gmc.xgmi.num_physical_nodes &&
amdgpu_vm.c:1152              amdgpu_ip_version(adev, GC_HWIP, 0) == IP_VERSION(9, 4, 0);
```

**GFX8 no entra en esa**: no es 9.4.0. Así que en esta GPU el flush viene
exclusivamente por la regla de la L1157, no por la regla del L2 texture cache.
Dos mecanismos distintos, y sólo uno aplica.

## La cadena completa

```
amdgpu_vm_ptes_update
  L1157   flush_tlb |= (GC_HWIP < 9.0.0)         <- SIEMPRE en GFX8
  L1165   params.needs_flush = flush_tlb
  L1242   r = vm->update_funcs->commit(&params, fence)     <- escribe los PTE
  L1246   if (params.needs_flush)
  L1247       amdgpu_vm_tlb_flush(&params, fence, tlb_cb)  <- invalida
```

**El orden es el de §D**: escribir la tabla, y sólo después invalidar. Coincide
con lo que `068` encontró en `emit_vm_flush` (PTBA primero, invalidate después),
pero visto desde la ruta de CPU y no desde la de ring.

Son **dos rutas distintas de actualización** y ambas llevan a lo mismo:

```
  ruta por SCHEDULER : amdgpu_vm_ptes_update  -> commit -> amdgpu_vm_tlb_flush
  ruta por RING       : emit_vm_flush          -> WAIT_REG_MEM -> PFP_SYNC_ME
```

`AGENTS.md` L159-161 dice que el writer de CPU es inalcanzable bajo la política
efectiva, y que SDMA es el writer efectivo. **La ruta de arriba es la de CPU, y
no es la que corre.** Sirve para entender el diseño, no para el camino activo.

## Lo que NO cierra

| Afirmación | Estado |
|---|---|
| En GFX8 todo bloque de 8 PTEEs con válido entra en TLB | `PROVEN` (`amdgpu_vm.c:1155`) |
| `needs_flush` es siempre True en esta GPU | `PROVEN` (L1157 + IP 8.0.0) |
| El flush ocurre después de escribir | `PROVEN` (L1242 → L1246) |
| La regla del L2 texture cache no aplica aquí | `PROVEN` (requiere 9.4.0 + XGMI) |
| La TLB es L1, L2 o ambas | `NOT_DETERMINED` |
| Qué cuenta la TLB: PTEEs, bloques o páginas | `NOT_DETERMINED` |
| Cuándo entra una entrada y cuándo sale | `NOT_DETERMINED` |
| Qué hace un fault de permiso en el recorrido | `NOT_DETERMINED` |

**La tercera es la que más pesa para un driver propio**: el hardware **cacha
entradas de traducción, y el software no lo sabe**. Un PTE recién escrito no es
visible hasta que el invalidate se ejecuta y la TLB se vacía. Eso es "hardware
PTE visibility point", que `AGENTS.md` L172 lista como `NOT_DETERMINED` — y sigue
siéndolo, pero ahora se sabe **por qué** es un problema: no es que falte el
invalidate, es que el hardware lo cachea antes de que exista.

## Procedencia

- `CORPUS` — `amdgpu_vm.c:1140-1258`, `gfx_v8_0.c:7128-7133`.
- Encadenada con `064` (geometría y `PAGE_TABLE_BLOCK_SIZE`), `068` (orden de
  emisión por ring), `075` (banderas de PTE).
- Sin `RUNTIME`, sin lectura de la GPU, sin escrituras.
- No se editó `AGENTS.md`: es de otras sesiones.

**Una nota de método, porque me la gané.** Escribí primero que `GC_HWIP` es
8.0.0 por cálculo, y luego lo verifiqué en `gfx_v8_0.c:7131-7133`. El cálculo
era correcto; la práctica no. Ya me ha pasado cuatro veces en esta sesión —
`level_shift`/`amdgpu_vm_pt_level_shift`, `polaris10_smumgr` en `amdgpu/`, las
cabeceras GMC frente a MMHUB, `022` leído por su nombre. Es la misma clase:
**afirmar antes de verificar**, y el nombre del fichero o del símbolo es
exactamente donde el error se cuela.
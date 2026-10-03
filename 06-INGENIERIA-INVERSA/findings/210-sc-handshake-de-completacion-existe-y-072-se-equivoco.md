# 210  §C: el handshake de COMPLETACIÓN sí existe, y `072` afirmó lo contrario

```
CLASSIFICATION=DOCUMENTATION · TRACK=STATIC
CORPUS=RESEARCH/working/linux-7.1.3 · HARDWARE_SCOPE=HOST-C/RX550/0000:01:00.0
WORK_CLASS=READ_ONLY/EVIDENCE · WRITE_EXECUTION=NONE · MODIFICATIONS=0
RUNTIME=NOT_RUN · GPU INTACTA
```

## Qué resuelve

Dos cosas, y la segunda es una corrección a otro hallazgo.

`AGENTS.md` §C pide cerrar: `VM_INVALIDATE_REQUEST → hardware action →
invalidation → completion → visibility`.

**El paso de completion existe, es una lectura de registro directa, y `072`
afirmó que nadie lo lee. Es falso.**

## El hecho

```
gmc_v8_0.c:640   WREG32(mmVM_INVALIDATE_REQUEST, mask);
gmc_v8_0.c:641   RREG32(mmVM_INVALIDATE_RESPONSE);
```

Y en la generación anterior, con la forma idéntica:

```
gmc_v7_0.c:449   WREG32(mmVM_INVALIDATE_REQUEST, mask);
gmc_v7_0.c:450   RREG32(mmVM_INVALIDATE_RESPONSE);
```

**Escribir la petición y leer la respuesta, inmediatamente. Eso es el handshake
de finalización.** Dos ocurrencias en todo el driver, y las dos están en GFX7 y
GFX8 — la nuestra.

**Y es un solo registro, sin bucle.** No hay sondeo, no hay reintento, no hay
espera activa: un `RREG32` inmediatamente después del `WREG32`.

Eso significa que, por lo que el driver puede saber, **`VM_INVALIDATE_RESPONSE` no
es un registro de estado que haya que sondear**: es el act que completa la
escritura. Leerlo consume la petición. Es la semántica opuesta a un
`VM_INVALIDATE_REQUEST` que se puddlea hasta ver un bit limpiarse.

**Lo que el hardware garantiza y lo que no** queda así: que la lectura *ocurre*
que devuelve algo, el driver no lo usa. Que el retorno implica invalidación
completada es `NOT_DETERMINED`, y lo digo explícitamente porque es justo el
punto que `AGENTS.md` marca como no cerrado.

## La corrección a `072`, con su causa

```
072-f3c-estatico-cond-exc-e-invalidate-response.md:1
  "072 · F3c estático: COND_EXEC es idéntico en GFX8, y VM_INVALIDATE_RESPONSE existe y nadie lo lee"

072-f3c-estatico-cond-exc-e-invalidate-response.md:19
  | VM_INVALIDATE_RESPONSE | existe en gmc_8_1_d.h a 0x51f | confirmado, y cero lecturas en el driver |
```

**La parte de "existe a 0x51f" es correcta. La de "cero lecturas" es falsa.**

Y la causa está medida:

```
grep -o '\b[^m]VM_INVALIDATE_RESPONSE\b' en *.c   ->  0 ocurrencias
grep -o '\bmmVM_INVALIDATE_RESPONSE\b'  en *.c   ->  2 ocurrencias
```

**El driver sólo usa la macro con prefijo `mm`.** Buscando el nombre desnudo se
obtiene exactamente cero, y un cero así parece un resultado negativo sólido.

**Es el mismo error que `065`**, donde `mm`/no-`mm` decidió qué registro se
citaba. Y es también **el mío**, doce veces esta sesión.

**`072` no es mío y no lo edito** (`COORDINACION.md:184`): lo informo. Pero es
una afirmación de las que otros hallazgos pueden depender, así que va con su
causa, no sólo con el "te equivocas".

**Y una observación de método que va más allá del caso**: doce veces he
producido un `NAME_NOT_FOUND` falso y doce veces lo ha cazado un grep posterior
con otra forma. **El coste no es el error: es que cada uno cuesta un ciclo
completo de verificación.** Un `grep -E '(mm)?VM_INVALIDATE_RESPONSE'` habría
dado 2 a la primera. La herramienta que uso (`xref.py`) lo habría dado.

## Los TRES flush de GFX8, y una asimetría que importa

```
gmc_v8_0.c:1734   .flush_gpu_tlb       = gmc_v8_0_flush_gpu_tlb        (L661)
gmc_v8_0.c:1735   .flush_gpu_tlb_pasid = gmc_v8_0_flush_gpu_tlb_pasid  (L625)
gmc_v8_0.c:1736   .emit_flush_gpu_tlb  = gmc_v8_0_emit_flush_gpu_tlb   (L668)
```

| función | mecanismo | ¿lee RESPONSE? |
|---|---|---|
| `flush_gpu_tlb_pasid` (L625-642) | registro directo | **sí** (L641) |
| `flush_gpu_tlb` (L661-666) | registro directo | **no** |
| `emit_flush_gpu_tlb` (L668-683) | **paquetes en el ring** | **no** |

**Sólo una de las tres espera confirmación.** La de PASID la tiene; las otras
dos no.

Y `flush_gpu_tlb_pasid` hace algo más que la de VMID:

```
gmc_v8_0.c:632   for (vmid = 1; vmid < 16; vmid++) {
gmc_v8_0.c:633       u32 tmp = RREG32(mmATC_VMID0_PASID_MAPPING + vmid);
gmc_v8_0.c:635       if ((tmp & ATC_VMID0_PASID_MAPPING__VALID_MASK) &&
gmc_v8_0.c:636           (tmp & ATC_VMID0_PASID_MAPPING__PASID_MASK) == pasid)
gmc_v8_0.c:637           mask |= 1 << vmid;
gmc_v8_0.c:638   }
gmc_v8_0.c:640   WREG32(mmVM_INVALIDATE_REQUEST, mask);
```

**Barre los 16 VMIDs para encontrar cuáles mapean al PASID, construye una máscara
y la escribe.** La invalidación es **por conjunto de VMIDs**, no por PASID
directamente: el hardware no conoce el PASID en `VM_INVALIDATE_REQUEST`, sólo el
driver lo traduce.

Y el comentario de `gmc_v8_0.c:644-648` lo dice:

```
 * GART
 * VMID 0 is the physical GPU addresses as used by the kernel.
 * VMIDs 1-15 are used for userspace clients and are handled
 * by the amdgpu vm/hsa code.
```

**VMID 0 es la GART** — lo que `067` cerró. Y `flush_gpu_tlb_pasid` empieza en
`vmid = 1`, o sea que **nunca invalida el VMID 0**. El GART tiene su propio
flush, y es el otro.

## Y el camino de ring, que es el que `068` ya documentó

```
gmc_v8_0.c:673   if (vmid < 8)
gmc_v8_0.c:674       reg = mmVM_CONTEXT0_PAGE_TABLE_BASE_ADDR + vmid;
gmc_v8_0.c:675   else
gmc_v8_0.c:676       reg = mmVM_CONTEXT8_PAGE_TABLE_BASE_ADDR + vmid - 8;
gmc_v8_0.c:677   amdgpu_ring_emit_wreg(ring, reg, pd_addr >> 12);
gmc_v8_0.c:680   amdgpu_ring_emit_wreg(ring, mmVM_INVALIDATE_REQUEST, 1 << vmid);
```

**PTBA primero, luego INVALIDATE_REQUEST** — el orden de `068` y `194`,
confirmado una vez más, y **sin lectura de respuesta**: la emisión al ring no
espera confirmación. El orden lo garantiza la cola, no un handshake.

**Los dos registros de PTBA** (`CONTEXT0` para vmid 0-7, `CONTEXT8` para 8-15)
explican por qué `064` vio siete registros con offset distinto en dos rangos:
`0x500-0x578` y `0xb60-0xba1`. Son los dos bloques de context.

## Lo que NO cierra

| Afirmación | Estado |
|---|---|
| `VM_INVALIDATE_RESPONSE` se lee en GFX8 | `PROVEN` (`gmc_v8_0.c:641`) |
| Se lee inmediatamente después del REQUEST | `PROVEN` (L640 → L641) |
| Sin bucle, sin reintento | `PROVEN` (una línea, sin `while`) |
| `072` está equivocado al decir cero lecturas | `PROVEN` + causa medida |
| Sólo el flush por PASID lee la respuesta | `PROVEN` (comparación de las 3) |
| El PASID se traduce a máscara de VMIDs | `PROVEN` (`gmc_v8_0.c:632-640`) |
| `flush_gpu_tlb_pasid` nunca toca VMID 0 | `PROVEN` (bucle desde `vmid=1`) |
| **Qué garantiza exactamente el retorno** | **`NOT_DETERMINED`** |
| Si la lectura es un act o un estado sondeable | `NOT_DETERMINED` |
| Por qué la de VMID no lee la respuesta | `NOT_DETERMINED` |
| Los rangos 0x500 y 0xb60 son CONTEXT0/CONTEXT8 | `PROVEN_DERIVED` |

**Las dos primeras filas de `NOT_DETERMINED` son el corazón.** He probado que la
lectura ocurre; no he probado qué significa el valor leído. Y esa es exactamente
la frontera `software behaviour ≠ hardware semantics` que `AGENTS.md` prohíbe
cruzar.

**Lo que sí es accionable para un driver propio**: si el valor devuelto no
significa nada, la lectura es un **act de sincronización de la escritura
MMIO**, no una consulta. En ese caso `mb()` sería suficiente y el `RREG32`
serviría sólo como barrier. Eso son dos implementaciones distintas según la
semántica, y no se pueden escribir igual.

## Procedencia

- `STATIC` — `gmc_v8_0.c:615-690` y `gmc_v8_0.c:1734-1736`, `gmc_v7_0.c:449` y `gmc_v7_0.c:450`,
  `amdgpu_vm_tlb_fence.c:62` y `:92` y `:103-108`, `amdgpu_vm_cpu.c:110-127`,
  `amdgpu_vm_sdma.c:120`, `amdgpu_ids.c:267`.
- Sin `RUNTIME`. Sin escrituras.
- **Corrige `072`** (afirmación de hecho falsa, con causa identificada).
  `072` no es mío: **lo informo y no lo edito.**
- Encadenada con `068` (orden de emisión por ring), `072` (COND_EXEC),
  `194` (invalidate obligatorio en GFX8), `067` (VMID 0 = GART),
  `209` (qué camino se ejecuta aquí).
- No se editó `AGENTS.md` ni `OPEN-FRONTIERS.md`: son de otras sesiones.

**Dos notas de método.**

La primera: **`072` acertó en `0x51f` y se equivocó en "nadie lo lee", y las dos
afirmaciones salieron del mismo fichero.** Eso es lo peligroso de un resultado
negativo: la mitad correcta hace que la mitad incorrecta pase por verificada.
Si sólo hubiera leído el offset y no hecho el grep, el error no habría
aparecido. Y si sólo hubiera leído el grep, no habría publicado el offset
correcto.

La segunda: **`209` decía que el camino de CPU no se instancia en esta GPU, y
este camino de PASID es precisamente al que lleva.** Con eso, el
`NOT_DETERMINED` de `209` sobre `amdgpu_vm_cpu_funcs` se queda más estrecho: la
funcionalidad existe, es reachable vía el workqueue de `amdgpu_vm_tlb_fence.c`,
y lo que no se instancia es el *map_table* del BO por CPU. **Son dos cosas
distintas que mi resumen anterior mezcló.**
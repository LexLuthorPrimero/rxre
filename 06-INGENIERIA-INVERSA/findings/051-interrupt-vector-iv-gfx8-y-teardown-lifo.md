# 051 · El vector de interrupción de GFX8, su overflow, y el teardown LIFO del GMC

`CLASSIFICATION=DOCUMENTATION` · `TRACK=STATIC` · `CORPUS=RESEARCH/working/linux-7.1.3`
`HARDWARE_SCOPE=HOST-C/RX550/0000:01:00.0` · `WORK_CLASS=READ_ONLY/EVIDENCE`
`WRITE_EXECUTION=SCOPED(findings)` · `RUNTIME=NOT_RUN` · `GPU INTACTA`

## CUDA principal

El bloque de interrupts de esta GPU es `tonga_ih.c`, **no un `ih_v3_0.c`** que no
existe, y no aparece en ningún hallazgo del proyecto. Aquí están las dos cosas que
contiene y que ninguna otra capa ha tocado: **el layout del vector de interrupción**,
que es el único sitio donde el hardware reporta un PASID, y el **mecanismo de overflow**,
que revela que la entrega de interrupts no es fiable y que el driver lo asume.

Y una tercera, en `gmc_v8_0.c`, que sí es una corrección: el teardown del page
walker es un **LIFO estricto** y es la única función que revierte `ENABLE_L2_CACHE`.

Control de duplicación ejecutado **antes** de derivar: `intrp`, `ivsrcid`,
`VISLANDS30`, `AMDGPU_IRQ_CLIENTID`, `ih_v3_0` → 0 ficheros en `findings/` y
`docs/`. Los 4 hits iniciales de `IH` eran `\bIH` matcheando dentro de otras
palabras; con `\bIH\b` salen 0. El bloque estaba libre.

## 1 · Qué bloque es, y por qué el nombre del log engaña

El log de arranque dice `ip block number 2 <ih_v3_0_0> (tonga_ih)`. No existe
`ih_v3_0.c`. Los ficheros de IH del árbol son `ih_v6_0.c`, `ih_v6_1.c`, `ih_v7_0.c`
y `tonga_ih.c`. El bloque real es **`tonga_ih.c:503`**,
`tonga_ih_ip_block.funcs = &tonga_ih_ip_funcs`.

Corolario de método: el nombre del `ip_block` en el log **no** predice el nombre
del fichero. Hubo que localizarlo por el símbolo.

## 2 · Layout del IV: 16 bytes, 4 dwords

`tonga_ih.c:248-270`, `tonga_ih_decode_iv`:

```c
u32 ring_index = ih->rptr >> 2;
dw[0..3] = le32_to_cpu(ih->ring[ring_index + 0..3]);

entry->client_id     = AMDGPU_IRQ_CLIENTID_LEGACY;   ← constante, NO se lee
entry->src_id        = dw[0] & 0xff;
entry->src_data[0]   = dw[1] & 0xfffffff;            ← 28 bits
entry->ring_id       = dw[2] & 0xff;
entry->vmid          = (dw[2] >> 8) & 0xff;
entry->pasid         = (dw[2] >> 16) & 0xffff;       ← 16 bits
ih->rptr += 16;
```

| dword | bits | campo | ancho |
|---|---|---|---|
| dw0 | 7:0 | `src_id` | 8 |
| dw1 | 27:0 | `src_data[0]` | 28 |
| dw2 | 7:0 | `ring_id` | 8 |
| dw2 | 15:8 | `vmid` | 8 |
| dw2 | 31:16 | `pasid` | 16 |

`client_id` se **fija** a `AMDGPU_IRQ_CLIENTID_LEGACY`; no es un campo del vector.
Consecuencia: en GFX8 el IV **no puede distinguir clientes**. Un IV que lo
hiciera no sería decodificable por esta función.

`rptr` está en **bytes** y avanza 16 por vector. El comentario lo dice dos veces
(L252 y L268) porque es una fuente de error conocida.

## 3 · El IV es el único sitio donde el hardware reporta un PASID

Correlación que no aparece en ningún hallazgo:

```
EMISIÓN     gmc_v8_0.c:680    WREG32(mmVM_INVALIDATE_REQUEST, 1 << vmid)
RECEPCIÓN   tonga_ih.c:265    entry->vmid  = (dw[2] >> 8) & 0xff
```

El invalidate se emite **por VMID** y el IV **reporta el VMID**. El espacio de
nombres es el mismo y se lee y se escribe por lados distintos.

`src_data[0]` de 28 bits es el payload. Para un fault de protección, ese es el
site ID y el status.

## 4 · Overflow: el driver pierde interrupts y lo asume

`tonga_ih.c:205-232`. El hardware marca `RB_OVERFLOW` en `IH_RB_WPTR`:

1. lee `wptr` desde `*ih->wptr_cpu` (cacheado), y si no hay overflow sale (L205)
2. **re-lee el registro** `mmIH_RB_WPTR` para descartar un clear ya hecho (L209)
3. salta `ih->rptr = (wptr + 16) & ih->ptr_mask` — "start parsing interrupt from
   the last not overwritten vector (wptr + 16). Hopefully this should allow us
   to catchup" (L216-223)
4. limpia el bit, y pone `WPTR_OVERFLOW_CLEAR` a 0 **de inmediato** para que un
   overflow nuevo se detecte (L231)

El comentario del driver dice la verdad: **" Hopefully"**. Un overflow descarta
vectores entre `rptr` y `wptr`. Para un driver propio esto significa que la
entrega de interrupts no es fiable y que la información sólo se puede recuperar
re-leyendo el hardware, nunca con un ack.

El doble check de L205/L211 mitiga la carrera de "overflow ya limpiado", pero no
elimina la de "overflow activado y limpiado entre dos lecturas de CPU".

## 5 · El dispatch, y por qué Tonga no tiene timestamp

`amdgpu_irq.c:477-525`. El IV se decodifica **siempre** primero (L490), y luego se
encamina:

```
L497  client_id >= AMDGPU_IRQ_CLIENTID_MAX   → descartado
L500  src_id   >= AMDGPU_MAX_IRQ_SRC_ID      → descartado
L503  LEGACY y adev->irq.virq[src_id]        → generic_handle_domain_irq()  [no al driver]
L508  client[client_id].sources == NULL      → descartado
L513  src->funcs->process(adev, src, &entry) ← aquí llega GMC
L521  sin src para ese src_id                 → descartado
```

Y L484-489, literal:

> `timestamp is not supported on some legacy SOCs (cik, cz, iceland, si and tonga)`

**Tonga es nuestra GPU.** `entry.timestamp` y `entry.timestamp_src` se dejan a 0
siempre. No hay timestamp en el IV de esta placa, y no es una omisión del driver:
es una limitación del SOC.

## 6 · El IV permite correlacionar un fault con su invalidate

`018-execution-order-invalidacion-gfx8.md:69-74` objeta, correctamente, que
`INVALIDATE_RESPONSE` no correlaciona con `INVALIDATE_REQUEST` porque `REQUEST` es
un mapa de 16 bits sin token: un `RESPONSE` con bits puestos puede ser de una
invalidación anterior.

**Esa objeción es correcta y no se extiende al IV.** Son dos mecanismos
distintos:

| | `INVALIDATE_RESPONSE` | IV |
|---|---|---|
| forma | mapa de 16 bits | evento con identidad |
| correlaciona con la petición | **no**, sin token | **sí**, por `vmid` |
| qué informa | "dominio n invalidado alguna vez" | "pasid p, vmid v, fault en src_data" |

El driver **descarta** la información del IV en `gmc_v8_0_process_vm_fault`, que
sólo lee los tres registros `PROTECTION_FAULT_{ADDR,STATUS,MCCLIENT}`
(`gmc_v8_0.c:1446-1448`). Y sin embargo `src->funcs->process` recibe
`*amdgpu_iv_entry` completo (`amdgpu_irq.h:77-79`), con `vmid` y `pasid`
disponibles.

Eso no es una limitación del hardware: es información que llega y no se usa.

**No lo marco como bug.** No he verificado qué contiene `src_data[0]` para un
fault de protección concreto, y eso exige RUNTIME. Lo que sí es `PROVEN` es que
el IV transporta identidad y que el handler la ignora.

## 7 · El teardown del walker es un LIFO estricto

`gmc_v8_0_gart_disable`, `gmc_v8_0.c:972-990`. Esto no está en ningún hallazgo:

```
L977  VM_CONTEXT0_CNTL = 0                    contextos primero
L978  VM_CONTEXT1_CNTL = 0
L981  ENABLE_L1_TLB                 = 0        luego el TLB
L982  ENABLE_L1_FRAGMENT_PROCESSING = 0
L983  ENABLE_ADVANCED_DRIVER_MODEL  = 0
L987  ENABLE_L2_CACHE               = 0        luego la L2 — DESHABILITA lo que
L989  VM_L2_CNTL2                   = 0        L852 habilitó
```

Es el negativo exacto del setup de `gmc_v8_0_gart_enable` (L842-885), campo por
campo, en orden inverso. Y es la **única** función del driver que pone
`ENABLE_L2_CACHE` a 0.

GFX6 tiene **dos** funciones que escriben `mmVM_L2_CNTL` (`gmc_v6_0.c:494` y
`:601`). La de L494 programa `ENABLE_L2_CACHE` y `ENABLE_L2_FRAGMENT_PROCESSING`;
la de L601 **no** programa `ENABLE_L2_CACHE`, sólo los LRU. GFX7 y GFX8 tienen una
sola. No he determinado si L601 es un segundo init o un camino de resume.

## 8 · LRU-update-by-write: corte generacional

`ENABLE_L2_{PTE,PDE0}_CACHE_LRU_UPDATE_BY_WRITE`:

| ASIC | programa el campo |
|---|---|
| `gmc_v6_0.c` | L497-498 y L602-603 |
| `gmc_v7_0.c` | L637-638 |
| `gmc_v8_0.c` | L854-855 |
| `gmc_v9_0` … `gmc_v12_1` | **ninguno** |

Es el mecanismo por el que una escritura a un PTE mantiene la L2 coherente. En
esta GPU vale 1.

**Consecuencia que conecta con un hecho ya establecido:** `AGENTS.md:127` dice que
el CPU page-table writer es inalcanzable en esta ruta. Quien escribe los PTE es
SDMA. Con `LRU_UPDATE_BY_WRITE = 1`, la coherencia se mantiene para **cualquier**
escritor, CPU o DMA — el campo no distingue el emisor. Eso resuelve por qué el
driver puede tener el writer de CPU muerto sin romper coherencia.

## 9 · Clasificación

| afirmación | clase | estado |
|---|---|---|
| el bloque IH de esta GPU es `tonga_ih.c` | FACT | **PROVEN** |
| layout del IV: 16 B, 4 dw, 5 campos | FACT | **PROVEN** |
| `client_id` es constante, no un campo | FACT | **PROVEN** |
| Tonga no tiene timestamp en el IV | FACT | **PROVEN** (comentario L485, código L487-488) |
| overflow descarta vectores, el driver lo asume | FACT | **PROVEN** (comentario L216-218) |
| `gart_disable` es un teardown LIFO | DERIVATION | **PROVEN_DERIVED** |
| el IV correlaciona con el invalidate por `vmid` | DERIVATION | **PROVEN_DERIVED** |
| LRU-update-by-write ausente en GFX9+ | NEGATIVE_RESULT | **PROVEN_ABSENT** (4 ficheros) |
| qué contiene `src_data[0]` en un fault | — | **NOT_DETERMINED**, exige RUNTIME |
| si `gmc_v6_0.c:601` es init o resume | — | **NOT_DETERMINED** |

## Lo que este hallazgo NO cierra

No cierra F1 ni 018. `INVALIDATE_RESPONSE` sigue sin token y sin handshake
utilizable: la conclusión de 018 se mantiene para ese registro. Lo que este
documento añade es que **existe un segundo canal, con identidad, que el handler
de GMC no usa** — y que por tanto el invariante de F1 tiene un correlacionador
potencial aunque el ack formal no exista.

## Nota de proceso

La iteración anterior Derivé `INVALIDATE_RESPONSE` y `DOMAIN_INVALIDATED` desde
cero, con controles correctos, y **ya estaba en 017 y 018**. Quinta duplicación
de la sesión, y la primera en que el control de duplicación se ejecutó al final
en lugar de al principio. En esta iteración el control va primero, y por eso el
dominio elegido (`IH`/INTRP, cero hallazgos objetivos) eralibre de verdad.

Cuatro nombres de fichero inventados antes de encontrar el correcto:
`ih_v3_0.c`, `intrp_*`, `amdgpu_irq_process_fault`, `gmc_v8_0_irq_funcs` — este
último existía pero lo busqué donde no era invocable. Todos se sustituyeron por
`READ_SCOPE_GATE`: listado de funciones reales del fichero antes de concluir.
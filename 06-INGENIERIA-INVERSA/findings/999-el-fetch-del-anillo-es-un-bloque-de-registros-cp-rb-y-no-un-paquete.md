# 999 · El fetch del anillo es un bloque de registros `CP_RB`, no un paquete: la arista `RING → CP` que faltaba

```
CLASSIFICATION=DOCUMENTATION · TRACK=STATIC
CORPUS=RESEARCH/working/linux-7.1.3 · HARDWARE_SCOPE=HOST-C/RX550/0000:01:00.0
WORK_CLASS=READ_ONLY/EVIDENCE · WRITE_EXECUTION=NONE · MODIFICATIONS=0
RUNTIME=NOT_RUN · GPU INTACTA
CIERRA=la arista RING → CP de la cadena de AGENT-16
ABRE=qué unidad física hace el fetch (VERDICT: el corpus no lo responde)
```

## Qué resuelve

Toda la cadena previa —`095` (tres motores), `108`/`109` (quién escribe y quién
espera), `111` (el PFP busca el IB), `122` (los `WAIT_REG_MEM` son `hdp_flush`),
`123` (el anillo sólo lleva punteros)— empieza **en el contenido del anillo**.

Ninguna responde **cómo se arma el anillo**, que es la pregunta anterior a
todas: si nadie programa el fetch, el resto describe un motor al que no le han
dado trabajo.

Y es un bloque de registros, **no es PM4**:

```
gfx_v8_0.c:4227   static int gfx_v8_0_cp_gfx_resume(struct amdgpu_device *adev)
```

Catorce escrituras `WREG32`, en orden fijo, y **cero paquetes**. El anillo se arma
por MMIO.

## La secuencia y los valores que salen de los headers

```
gfx_v8_0.c:4235   WREG32(mmCP_RB_WPTR_DELAY, 0);
gfx_v8_0.c:4238   WREG32(mmCP_RB_VMID, 0);            <- el anillo GFX usa VMID 0
gfx_v8_0.c:4243   tmp = REG_SET_FIELD(0, CP_RB0_CNTL, RB_BUFSZ, rb_bufsz);
gfx_v8_0.c:4244   tmp = REG_SET_FIELD(tmp, CP_RB0_CNTL, RB_BLKSZ, rb_bufsz - 2);
gfx_v8_0.c:4245   tmp = REG_SET_FIELD(tmp, CP_RB0_CNTL, MTYPE, 3);
gfx_v8_0.c:4246   tmp = REG_SET_FIELD(tmp, CP_RB0_CNTL, MIN_IB_AVAILSZ, 1);
gfx_v8_0.c:4250   WREG32(mmCP_RB0_CNTL, tmp);                              <- (A)
gfx_v8_0.c:4253   WREG32(mmCP_RB0_CNTL, tmp | ..._RB_RPTR_WR_ENA_MASK);     <- (B)
gfx_v8_0.c:4254   ring->wptr = 0;
gfx_v8_0.c:4255   WREG32(mmCP_RB0_WPTR, lower_32_bits(ring->wptr));
gfx_v8_0.c:4259   WREG32(mmCP_RB0_RPTR_ADDR, lower_32_bits(rptr_addr));
gfx_v8_0.c:4260   WREG32(mmCP_RB0_RPTR_ADDR_HI, upper_32_bits(rptr_addr) & 0xFF);
gfx_v8_0.c:4263   WREG32(mmCP_RB_WPTR_POLL_ADDR_LO, lower_32_bits(wptr_gpu_addr));
gfx_v8_0.c:4264   WREG32(mmCP_RB_WPTR_POLL_ADDR_HI, upper_32_bits(wptr_gpu_addr));
gfx_v8_0.c:4265   mdelay(1);
gfx_v8_0.c:4266   WREG32(mmCP_RB0_CNTL, tmp);                              <- (C)
gfx_v8_0.c:4269   WREG32(mmCP_RB0_BASE, rb_addr);                         <- gpu_addr >> 8
gfx_v8_0.c:4270   WREG32(mmCP_RB0_BASE_HI, upper_32_bits(rb_addr));
gfx_v8_0.c:4272   gfx_v8_0_set_cpg_door_bell(adev, ring);
gfx_v8_0.c:4274   amdgpu_ring_clear_ring(ring);
gfx_v8_0.c:4275   gfx_v8_0_cp_gfx_start(adev);
```

### El número sale exacto — y mi primer cálculo era falso

`gfx_v8_0.c:4241` es `rb_bufsz = order_base_2(ring->ring_size / 8)`, y
**`ring_size` no es el `1024` del `amdgpu_ring_init`**. Lo leí mal la primera vez,
tomé `1024` por el tamaño del anillo, y calculé `RB_BUFSZ = 9`. **Es falso.**

```
gfx_v8_0.c:1875      amdgpu_ring_init(adev, ring, 1024, ...)   <- max_dw, NO ring_size
amdgpu_ring.c:339    ring->ring_size = roundup_pow_of_two(max_dw * 4 * sched_hw_submission);
amdgpu_drv.c:178     int amdgpu_sched_hw_submission = 2;        <- y NO es KIQ
```

`1024 * 4 * 2 = 8192` dwords = 32768 bytes. `/8` = 4096. `order_base_2` = **13**.

Con los shifts y máscaras de `gfx_8_0_sh_mask.h:1357-1374`:

```
CP_RB0_CNTL             = 0x00418B0D
CP_RB0_CNTL|RPTR_WR_ENA = 0x80418B0D
  RB_BUFSZ       = 13   (mask 0x3f,     shift 0x0)
  RB_BLKSZ       = 11   (mask 0x3f00,   shift 0x8)    <- rb_bufsz - 2
  MTYPE          =  3   (mask 0x18000,  shift 0xf)
  MIN_IB_AVAILSZ =  1   (mask 0xc00000, shift 0x16)
```

**Comprobación cruzada, independiente del cálculo:** `RB_BUFSZ = 13` da
`2^13 * 8 = 65536` bytes de anillo, y `RB_BLKSZ = 11` da bloques de
`2^11 * 8 = 16384` bytes = **4096 dwords**. Un bloque es la mitad del anillo, que
es exactamente lo que `rb_bufsz - 2` promete. **El campo dice lo que su nombre
dice**, que no es lo mismo, y por eso lo medí en vez de asumirlo.

### La doble escritura de `CP_RB0_CNTL` no es redundante: es una ventana

`(A)` escribe el control **sin** `RB_RPTR_WR_ENA`. Entre `(A)` y `(B)` se
escriben `WPTR`, `RPTR_ADDR` y los dos `WPTR_POLL_ADDR`. Y `(C)` **vuelve a
escribir el control sin el bit**.

El bit de enable se pone en `(B)`, se hacen las cuatro escrituras de punteros, y
se quita en `(C)`. Hay un `mdelay(1)` justo antes de `(C)`.

**Y `CP_RB0_BASE` se escribe DESPUÉS, en `L4269`.** Esa es la razón de la
ventana: sin ella el fetch puede arrancar sobre un anillo al que todavía le falta
la dirección base. Es la única lectura que explica el orden de las líneas.

**Lo que NO he observado es que el hardware respete la ventana.** Que el bit tenga
ese efecto es `NOT_PROVEN`; que el orden exista y sea ese, `PROVEN`.

### El anillo GFX de esta GPU usa doorbell, no MMIO de `WPTR`

```
gfx_v8_0.c:1971   /* no gfx doorbells on iceland */
gfx_v8_0.c:1972   if (adev->asic_type != CHIP_TOPAZ) {
gfx_v8_0.c:1973       ring->use_doorbell = true;
gfx_v8_0.c:1974       ring->doorbell_index = adev->doorbell_index.gfx_ring0;
```

El objetivo es **Polaris12, device id `0x699f`** (`HARDWARE-FINGERPRINT.md:34`),
**no** `CHIP_TOPAZ`. Se toma la rama del doorbell. Consecuencia por envío:

```
gfx_v8_0.c:6023   gfx_v8_0_ring_set_wptr_gfx(struct amdgpu_ring *ring)
gfx_v8_0.c:6026       if (ring->use_doorbell) {
gfx_v8_0.c:6028           *ring->wptr_cpu_addr = lower_32_bits(ring->wptr);
gfx_v8_0.c:6029           WDOORBELL32(ring->doorbell_index, lower_32_bits(ring->wptr));
gfx_v8_0.c:6030       } else {
gfx_v8_0.c:6031           WREG32(mmCP_RB0_WPTR, lower_32_bits(ring->wptr));
gfx_v8_0.c:6032           (void)RREG32(mmCP_RB0_WPTR);      <- lectura de posted-write
```

**El anillo GFX de esta RX550 no escribe `mmCP_RB0_WPTR` por MMIO en cada envío:
escribe una puerta.** La rama `else` incluye un `RREG32` de lectura, que es la
prueba de que el autor sabía que `WREG32` es posted: sin ella el `WREG32`
siguiente no está garantizado.

Y eso explica por qué `mmCP_RB_WPTR` tiene escritores en `gfx_v9_0.c` y
`gfx_v10_0.c` y **ninguno** en `gfx_v8_0.c` (`grep`: 0 en v8, entradas de
`SOC15_REG_ENTRY_STR` en v9:167 y v10:297). No es que GFX8 no use el registro:
usa la otra mitad del mecanismo, la que el propio driver declara disponible para
esta placa.

### Y los motores se enablean **antes** de que exista el anillo

```
gfx_v8_0.c:4130   gfx_v8_0_cp_gfx_start(adev)
gfx_v8_0.c:4139       WREG32(mmCP_MAX_CONTEXT, adev->gfx.config.max_hw_contexts - 1);
gfx_v8_0.c:4140       WREG32(mmCP_ENDIAN_SWAP, 0);
gfx_v8_0.c:4141       WREG32(mmCP_DEVICE_ID, 1);
gfx_v8_0.c:4143       gfx_v8_0_cp_gfx_enable(adev, true);
gfx_v8_0.c:4145       r = amdgpu_ring_alloc(ring, gfx_v8_0_get_csb_size(adev) + 4);
```

```
gfx_v8_0.c:4182   tmp = RREG32(mmCP_ME_CNTL);
gfx_v8_0.c:4185       ME_HALT = 0;  PFP_HALT = 0;  CE_HALT = 0;
gfx_v8_0.c:4192   WREG32(mmCP_ME_CNTL, tmp);
gfx_v8_0.c:4193   udelay(50);
```

`gfx_v8_0_cp_gfx_enable` es exactamente la escritura que `095` dedujo del layout,
vista desde el productor: `095` tenía el registro, y **el driver escribe los tres
`HALT` a 0 juntos, RMW sobre el valor leído, con `udelay(50)` detrás**. La misma
función es la rama `else` que pone los tres a 1. **El `RREG32` de `CP_ME_CNTL`
que `095` nunca menciona tiene un productor.**

### Un detalle sobre `CP_RB_ACTIVE` que no fue un error mío sino una hipótesis mía

`CP_RB_ACTIVE` es el registro que "arranca" el ring buffer en las ASIC modernas.
`gfx_v8_0.c` **no lo escribe nunca** (`grep -c CP_RB_ACTIVE gfx_v8_0.c` → **0**;
el único escritor en todo el corpus `amd/` es `gfx_v10_0.c:6551`). Y **tampoco
escribe `CP_RB1_*` ni `CP_RB2_*`** (0).

Lo registré porque era la hipótesis que sostenía el resto y **resultó falsa en
la parte de "así se arranca"**. La secuencia real de arranque es la que está
arriba. No hay `CP_RB_ACTIVE` en esta ruta, y el fetch lo dirige el bloque
`CP_RB0_*` más `CP_ME_CNTL`.

**Un solo anillo, un solo juego de registros, y `CP_RB0` a secas** — coherente con
`gfx_v8_0.c:60` (`GFX8_NUM_GFX_RINGS 1`).

## La cadena completa, ahora con las dos aristas que faltaban

```
 1. amdgpu_ring_init(ring, 1024)                    max_dw, NO tamaño  [L1875, L339]
 2. gfx_v8_0_cp_gfx_resume: 14 WREG32 a CP_RB0_*   ARMA EL FETCH    [L4227-4270]  <- NUEVO
 3. CP_ME_CNTL: ME_HALT=0 PFP_HALT=0 CE_HALT=0     ENCIENDE MOTORES  [L4185, L4192] <- NUEVO
 4. amdgpu_ring_alloc + PREAMBLE/CLEAR_STATE        CSB de arranque  [L4145-4180]
 5. ... por cada envío: el driver escribe dwords en el anillo ...
 6. WDOORBELL32(doorbell_index, wptr)              PUERTA, NO MMIO  [L6029]      <- NUEVO
 7. INDIRECT_BUFFER(gpu_addr,len,vmid) en el anillo el PFP busca el IB  [L6077-6098]
 8. WAIT_REG_MEM ... por dentro                    ME o PFP espera  [L6047, L6199]
 9. EVENT_WRITE_EOP                                fence al host    [L6145]
```

Los pasos 2, 3 y 6 son los que faltaban. **Los tres son MMIO, y ninguno es PM4.**

## Qué NO cierra

| Afirmación | Estado |
|---|---|
| El anillo GFX se arma por `WREG32` a `CP_RB0_*`, no por PM4 | `PROVEN` (`L4227-4275`) |
| `CP_RB0_CNTL = 0x00418B0D`, `|RPTR_WR_ENA = 0x80418B0D` | `PROVEN` — arithmetic + cross-check de bloques |
| El anillo real son 64 KiB, en bloques de 4096 dwords | `PROVEN_DERIVED` |
| `RB_BLKSZ = RB_BUFSZ - 2` ⇒ bloque = mitad del anillo | `PROVEN_DERIVED` |
| El anillo GFX de esta GPU usa doorbell, no `WREG32(CP_RB0_WPTR)` | `PROVEN` (`L1972` + objetivo `0x699f`) |
| `CP_RB_VMID = 0` para el anillo GFX | `PROVEN` (`L4238`) |
| Los motores se enablean antes de que exista el anillo | `PROVEN` (`L4143` < `L4145`) |
| `CP_ME_CNTL` se escribe por RMW con los tres `HALT` juntos | `PROVEN` (`L4182-4192`) |
| El anillo GFX es el único: un solo juego `CP_RB0_*` | `PROVEN_DERIVED` |
| `CP_RB_ACTIVE` no se usa en esta ruta | `PROVEN` (0 escritores en `gfx_v8_0.c`) |
| El propósito de la ventana `(A)`/`(B)`/`(C)` | `HYPOTHESIS` — el orden está `PROVEN`, el motivo no |
| Que el bit de enable tenga ese efecto en hardware | `NOT_PROVEN` — requiere placa |
| Que el CP ejecute en orden de anillo lo que trae | `NOT_PROVEN` — el estado de `018`, sin cambio |
| Qué unidad física hace el fetch | `NOT_DETERMINED` — ver abajo |

**Las dos últimas filas son `software behaviour ≠ hardware semantics`, y la
tercera es un límite real del corpus, no un hueco de lectura.**

### Por qué "qué unidad física hace el fetch" queda `NOT_DETERMINED`

Es la pregunta que motiva la frontera, y **no la respondo**. Mi primera
justificación fue que `CP_RB_STATUS` —el estado del walker— existe en el árbol de
headers y ningún `.c` del corpus lo lee. **Al verificarlo antes de commitear, esa
justificación era falsa en su premisa:**

```
grep -rn "define mmCP_RB_STATUS\b" include/asic_reg/
  gc/gc_9_0_offset.h      gc/gc_9_1_offset.h      gc/gc_9_2_1_offset.h
  gc/gc_10_1_0_offset.h   gc/gc_10_3_0_offset.h
```

**Cinco ASICs, y ninguno es GFX8.** El offset (`0x11a3` en `gc_9_*`, `0x1f43` en
`gc_10_*`) es un valor *por ASIC*, y `gfx_8_0` no está en la lista. Mi "0
resultados en `.c`" era cierto y **no probaba nada**: la razón por la que no se
lee es que **el registro no es de este ASIC**.

Retiré el argumento en vez de publicarlo. El límite real es otro, y es más fuerte:

- Los tres motores de `095` están en `CP_ME_CNTL`, un registro **de GFX8**, y esa
  ruta sí está seguida de principio a fin.
- El bloque `CP_RB0_*` que programa el fetch **también es de GFX8** — está en
  `gca/gfx_8_0_sh_mask.h` y `gfx_v8_0.c` lo escribe.
- Pero **el bloque que *programa* el anillo no se lee de vuelta ni una vez.**
  Los dos `RREG32(mmCP_RB0_*)` de `gfx_v8_0.c` (`L6019`, `L6032`) son ambos
  **`CP_RB0_WPTR`**, y los dos están en `gfx_v8_0_ring_get_wptr_gfx` /
  `set_wptr_gfx`, o sea **la rama `else`, la que esta GPU no toma** (`L1972`).
  Del resto del bloque —`CP_RB0_CNTL`, `CP_RB0_BASE`, `CP_RB0_RPTR_ADDR`— no hay
  ni una lectura.

**Y el estado del fetch no se observa en ninguna parte.** El corpus contiene los
nombres de los registros que el driver escribe y ni una lectura del bloque que
programa el anillo en la ruta que esta GPU ejecuta. Ese es el `NOT_DETERMINED`, y
es un límite de fuente, no un hueco de búsqueda.

Que exista un `RREG32` de `WPTR` en el fichero, y que esté en la rama muerta de
esta placa, es la razón por la que el `grep` no basta como prueba: **cuenta
ocurrencias, y aquí la ocurrencia y el camino no coinciden.**

**El registro se llama `CP_RB`. Eso es un nombre, no una prueba de qué ejecuta el
fetch.** `095` estableció que PFP, ME y CE son tres motores con tres instruction
caches y un registro; eso dice qué hay *dentro* del paquete, no quién fue a la
memoria a buscarlo. **La arista `CP` → fetch queda `NOT_DETERMINED` y no la cruzo
por el nombre del registro.**

Lo que sí queda `PROVEN` es el lado del software: **qué registros programa el
driver, en qué orden, y con qué valores.** Para un driver propio eso es lo
suficiente para arrancar el motor, y es lo único que este corpus sostiene.

## Procedencia

- `STATIC` — `gfx_v8_0.c:1875`, `:1971-1978`, `:4130-4193`, `:4227-4275`,
  `:6023-6033`; `amdgpu_ring.c:339`; `amdgpu_drv.c:178`;
  `gfx_8_0_sh_mask.h:1357-1374` (`CP_RB0_CNTL`), `:3647-3670` (`CP_ME_CNTL`).
- Aritmética: `/tmp/opencode/cprb2.c`, compilado con `gcc -O2 -Wall -Wextra`,
  sin warnings. Primer valor (`RB_BUFSZ=9`) **descartado**: leía `max_dw` como
  `ring_size`.
- Dos `grep` de ausencia, sobre todo `drivers/gpu/drm/amd/` del snapshot:
  `CP_RB_ACTIVE` en `gfx_v8_0.c` → 0; `CP_RB_STATUS` en `.c` → 0. **Son
  `PROVEN_ABSENT` dentro del alcance leído, no `PROVEN_ABSENT` del sistema.**
- Sin MMIO write, sin TLB, sin `insmod`. **`GPU INTACTA`.**
- Encadenada con `095` (tres motores / tres icache), `108`/`109` (motores),
  `111` (el PFP busca el IB), `122` (los `WAIT_REG_MEM`), `123` (el anillo sólo
  lleva punteros), `084` (packet consumption), `121` (contabilidad de anillo).
- **No corrige ningún hallazgo previo.** No edité `AGENTS.md` ni
  `OPEN-FRONTIERS.md`.

## Dos notas de método

**La primera: el error fue mío y de un solo `grep`.** Leí `amdgpu_ring_init(adev,
ring, 1024, ...)` y calculé con 1024. `1024` es `max_dw` — un presupuesto de
emisión — y `ring_size` sale de `roundup_pow_of_two(max_dw * 4 *
sched_hw_submission)` (`amdgpu_ring.c:339`), que son 8192 dwords. **El número
salía 9 en vez de 13, y `RB_BLKSZ` salía 7 en vez de 11: el bloque medía un
cuarto del anillo en lugar de la mitad.**

Lo que lo cazó no fue releer el código: fue **la comprobación cruzada de que un
bloque fuera la mitad del anillo**. `RB_BUFSZ=9` también producía un bloque
"coherente consigo mismo" (`2^9*8` bytes) — **una aritmética internamente
consistente también puede estar equivocada**, y la única forma de distinguirlo
fue una restricción independiente del resultado.

**La segunda: el nombre de un registro no es su semántica.** Estuve a punto de
escribir que `CP_RB_ACTIVE` arrancaba el ring buffer en esta ASIC, porque así
funciona en las modernas y porque el nombre lo sugiere. Escribí el `grep` para
confirmarlo y salió **0 en `gfx_v8_0.c`**. Mi hipótesis era falsa y la secuencia
real es otra.

**Es exactamente el `NOT_DETERMINED` que este proyecto ya se sabe aplicar**: no
cruzar la frontera software/hardware por analogía con otro ASIC. Lo escribí
porque la hipótesis era *plausible*, y "plausible" no es un estado. Lo que queda
es `PROVEN` en el lado del software y `NOT_DETERMINED` en el del hardware, y esa
frontera es el resultado, no la falta de resultado.
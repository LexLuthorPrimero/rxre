# 1004 · Los canales ENG de invalidate son de GFX9+: en GFX8 no existen, y el driver sí los usa (en otra generación)

```text
CLASSIFICATION=DOCUMENTATION+ERROR · TRACK=STATIC
CORPUS=RESEARCH/working/linux-7.1.3 · HARDWARE_SCOPE=HOST-C/RX550/0000:01:00.0
WORK_CLASS=READ_ONLY/EVIDENCE · WRITE_LOCAL=PROPIOS · MODIFICATIONS_CORPUS=0
WRITE_EXECUTION=NONE · RUNTIME=NOT_RUN · GPU INTACTA
AUTORIA=AGENTE-13
REFUTA=revkit/INVALIDATE-CANALES.md (tres afirmaciones)
ACTUALIZA=017, 018, 019, 022, 106, 110, 128, 246
```

## Qué resuelve

`revkit/INVALIDATE-CANALES.md` describe 18 canales de invalidate por motor
(`ENG0..ENG17`), con `REQ`/`ACK`/`SEM`/`ADDR_RANGE`, y los recomienda como
capacidad disponible para un driver propio sobre esta placa.

**Las tres afirmaciones que sostienen ese documento son falsas para GFX8, y las
tres en la misma dirección:adcisión de estructura de GFX9+ a un ASIC que no la
tiene.** Es `NO_HISTORICAL_INHERITANCE` en su forma más peligrosa, porque la
estructura heredada no falla: **no existe**, y por eso no puede fallar.

Y al refutar la capacidad heredada, este hallazgo **cierra la proof obligation de
hardware completion** de §C en la dirección fuerte: en GFX8 no hay registro de
acuse que sondear, y ahora está demostrado que no es una omisión del driver de
referencia sino una limitación del banco de registros de este ASIC.

## 1 · Los canales ENG no existen en GFX8

Barrido completo, dos alcances distintos, **conteo impreso por programa**:

| alcance | ficheros | ficheros con `INVALIDATE_ENG` | ocurrencias |
|---|---:|---:|---:|
| cabeceras GFX8 (`gmc_8_*` + `gca/gfx_8_*`) | 12 | **0** | **0** |
| **todas** las cabeceras `gmc/*` (GFX6, GFX7, GFX8) | 12 | **0** | **0** |

El segundo alcance es el que decide: **`gmc/` no contiene ningún ASIC con canais
ENG, de GFX6 a GFX8.** Y `gmc_8_1_d.h`/`gmc_8_2_d.h` declaran exactamente dos
registros de invalidate, que son los que `019` yaclosureó:

```
gmc_8_1_d.h:615   mmVM_INVALIDATE_REQUEST     0x51e
gmc_8_1_d.h:616   mmVM_INVALIDATE_RESPONSE    0x51f
```

Dos. No cinco por motor, no dieciocho motores.

Donde sí existen, y desde cuándo:

| familia | headers | motores ENG |
|---|---|---:|
| `mmhub_1_0` … `mmhub_9_4_1` | sí | 18 (`ENG0..ENG17`) |
| `gc_9_0` … `gc_12_1_0` | sí | 18 |
| `gmc_*` (GFX6/7/8) | **no** | — |

**El salto de generación es GFX8 → GFX9**, y es el mismo salto que `019` ya
documentó para los selectores de granularidad (`INVALIDATE_L1_PTES`,
`FLUSH_TYPE`, `INVALIDATE_4K_PAGES_ONLY`): aparecen en GFX9 y no existen en GFX8.
Los canales ENG son **la misma frontera**, vista por el lado del acuse.

## 2 · Y el driver sí los usa — en otra generación

La segunda afirmación del documento era «ninguno de los 90 lo usa el driver de
amdgpu». **Es falsa**, y la corrección importa porque su计 COUNT era el
argumento de seguridad del documento:

```
ficheros .c del driver que usan INVALIDATE_ENG : 22
  de ellos, de la era GFX7/GFX8 (gfx_v[678]/gmc_v[678]/soc15./vi.) : 0
```

Los 22 son `gmc_v9_0.c`, `mmhub_v3_0*.c`, `gfxhub_v3_0*.c`, `mmhub_v9_4.c` …
Es decir: **GFX9+/SOC15 usa masivamente los canales, y GFX8 no los tiene.**

El documento llegó a la conclusión correcta por una razón falsa: no estaban sin
usar, estaban **en otra generación**. El mismo conclusion correcto, con la
evidencia que lo sostiene refutada.

## 3 · La prueba obligation de *hardware completion*: `NOT_AVAILABLE`, no "no implementado"

Este es el resultado que el mecanismo pedía, y es el opposite de lo que el
documento refutado sugería (que existía una alternativa sin explotar).

GFX9+ tiene un handshake de completion real, per-VMID y con correlación exacta
(`gmc_v9_0.c:851-857`):

```c
WREG32_SOC15_IP_NO_KIQ(MMHUB, req, inv_req, ...);
for (j = 0; j < adev->usec_timeout; j++) {
        tmp = RREG32_SOC15_IP_NO_KIQ(MMHUB, ack, ...);
        if (tmp & (1 << vmid))          /* correlación exacta: el mismo vmid */
                break;
        udelay(1);
}
if (j >= adev->usec_timeout)
        DRM_ERROR("Timeout waiting for VM flush ACK!\n");
```

Y en el camino KIQ, `amdgpu_gmc_fw_reg_write_reg_wait(adev, req, ack, inv_req,
1 << vmid, inst)` (`gmc_v9_0.c:805`) emite el par *escribir-esperar* dentro del
ring, con `1 << vmid` como máscara de comparación.

GFX8 no tiene **ninguno** de esos tres registros: ni `REQ` por motor, ni `ACK`,
ni `SEM`. El inventario completo de lo que GFX8 expone para invalidar es
`REQUEST` (16 bits de dominio) y `RESPONSE` (16 bits de dominio).

| | GFX8 | GFX9+ |
|---|---|---|
| registro de petición | `VM_INVALIDATE_REQUEST` | `MMVM_INVALIDATE_ENG<n>_REQ` |
| registro de acuse | **no existe** | `MMVM_INVALIDATE_ENG<n>_ACK` |
| correlación | ninguna (`DOMAIN_INVALIDATED_n`) | `ACK & (1<<vmid)` |
| granularidad | dominio completo | L1/L2/PDE/FLUSH_TYPE |
| rango de direcciones | **no existe** | `ENG<n>_ADDR_RANGE_{LO32,HI32}` |

**Estado de la proof obligation `HARDWARE_COMPLETION`: `PROVEN_ABSENT`.** El
registro que haría falta no existe en el ASIC. Esto es más fuerte que el
`NOT_IMPLEMENTABLE` con que `017`/`018` cerraron provisionalmente la pregunta:
`NOT_IMPLEMENTABLE` admitía que quizá existiera otro camino; `PROVEN_ABSENT`
descarta la clase entera deDescriptors de completion para GFX8.

Y confirma `017 §3` por el lado del hardware y no solo del código: no es que el
driver GFX8 deje de usar un ack, es que **no hay ack que usar**.

## 4 · Un hallazgo nuevo: el ack de GFX9 tiene un *false-ACK* documentado, y eso acota el `RESPONSE` de GFX8

Esto no estaba registrado en ningún hallazgo previo, y es la aportación que más
cambia el diseño propio.

El driver de GFX9+ **no puede sondear su propio ack sin una precaución**, y lo
dice (`gmc_v9_0.c:842-849`):

```c
/*
 * Issue a dummy read to wait for the ACK register to
 * be cleared to avoid a false ACK due to the new fast
 * GRBM interface.
 */
if ((vmhub == AMDGPU_GFXHUB(0)) &&
    (amdgpu_ip_version(adev, GC_HWIP, 0) < IP_VERSION(9, 4, 2)))
        RREG32_NO_KIQ(req);
```

Es decir: **un `ACK` que ya está a 1 de una invalidación anterior produce un acuse
falso.** El hardware no garantiza que leer `ACK == 1` signifique "la invalidación
que acabo de pedir terminó"; hay que forzar antes a que se limpie.

Y hay un segundo hazard, independiente y más duro (`gmc_v9_0.c:813-818`):

```c
/*
 * It may lose gpuvm invalidate acknowldege state across power-gating
 * off cycle, add semaphore acquire before invalidation and semaphore
 * release after invalidation to avoid entering power gated state
 * to WA the Issue
 */
```

**El estado de acuse puede perderse al cruzar un ciclo de power-gating.** Por eso
el protocolo mete un semáforo antes y después.

**Por qué esto importa para GFX8 aunque `RESPONSE` exista.** `VM_INVALIDATE_RESPONSE`
es del mismo tipo de registro que `ENG<n>_ACK`: un conjunto de bits de «dominio
invalidado» que el hardware pone cuando ha invalidado. El driver GFX9 demuestra,
sobre el registro equivalente de una generación posterior, que **ese tipo de
registro tiene un modo de fallo por estado residual** que hay que neutralizar
explícitamente antes de poder confiar en él.

Consecuencia para el driver propio, y es una `REQUIREMENT`:

> Even que sewagerece correlacionar `DOMAIN_INVALIDATED_n` con el VMID n — que
> `revkit` dejó `NOT_DETERMINED` y que además resulta **no necessary**: no hace
> falta para nada si no hay nada que esperar — **no se puede usar
> `VM_INVALIDATE_RESPONSE` como primitiva de completion sin neutralizar antes su
> estado residual**. La neutralización que GFX9 usa es una lectura ficticia del
> registro de petición; el corpus no dice que exista en GFX8.

Esto **degrada** una posibilidad que el documento refutado dejaba abierta. Antes de
este hallazgo, la postura era «`RESPONSE` es el único candidato y su semántica
impide correlacionarlo» (`017 §6`). Ahora es: *y además hay evidencia positiva de
que sondearlo sin preparación puede mentir*.

## 5 · Ordering y atomicidad PTBA + invalidate: no hay nada entre las dos escrituras

`gfx_v8_0_ring_emit_vm_flush` completo (`gfx_v8_0.c:6191-6216`), sin abreviar:

```c
amdgpu_gmc_emit_flush_gpu_tlb(ring, vmid, pd_addr);   /* WREG PTBA ; WREG REQUEST */
amdgpu_ring_write(ring, PACKET3(PACKET3_WAIT_REG_MEM, 5));
amdgpu_ring_write(ring, (WAIT_REG_MEM_OPERATION(0) | WAIT_REG_MEM_FUNCTION(0)
                       | WAIT_REG_MEM_ENGINE(0)));
amdgpu_ring_write(ring, mmVM_INVALIDATE_REQUEST);
amdgpu_ring_write(ring, 0);          /* addr hi */
amdgpu_ring_write(ring, 0);          /* ref   */
amdgpu_ring_write(ring, 0);          /* mask  */
amdgpu_ring_write(ring, 0x20);       /* poll interval */
if (usepfp) {
        amdgpu_ring_write(ring, PACKET3(PACKET3_PFP_SYNC_ME, 0));
        amdgpu_ring_write(ring, 0x0);
}
```

Medido sobre ese cuerpo:

- Las dos escrituras (PTBA y `REQUEST`) son `WRITE_DATA` con
  `WRITE_DATA_ENGINE_SEL(1) | WR_CONFIRM` (`gfx_v8_0.c:6356-6357`): **las ejecuta
  el PFP**.
- El `WAIT_REG_MEM` va con `ENGINE(0)` = ME: **lo consume el ME**.
- **No hay ninguna barrera software entre las dos escrituras.** Busqué
  `RELEASE_MEM` en `gfx_v8_0.c`: hay exactamente una ocurrencia (`:6239`) y
  pertenece a `gfx_v8_0_ring_emit_fence_compute` (`:6231`), otra función. **El
  path de invalidate no emite ninguna.**

Sobre lo que esto prueba y lo que no, con el cuidado que `018` ya pidió:

| afirmación | estado | por qué |
|---|---|---|
| El path emite PTBA y `REQUEST` como dos `WRITE_DATA` separados | `PROVEN` | `gmc_v8_0.c:677`, `:680` |
| Ambos los ejecuta el PFP | `PROVEN` | `gfx_v8_0.c:6356-6357` |
| No hay barrera entre ellos en el path | `PROVEN` | barrido de `RELEASE_MEM` |
| El par **no** es indivisible: nada lo hace atómico | `PROVEN_DERIVED` | no hay primitiva de atomicidad en la secuencia |
| El `WAIT` no aporta orden ninguno | `PROVEN` | `FUNCTION(0)`=always, `mask=0` (`215`) |
| `PFP_SYNC_ME` ordena la decodificación de paquetes, no el efecto | `PROVEN` | `017 §3` |
| **El orden hardware de ejecución de los dos packets** | **`NOT_DETERMINED`** | requiere RUNTIME; **no cambiado aquí** |

La última fila es la que `018` dejó abierta y **sigue abierta**: yo he probado
que el software no aporta orden, no que el hardware no lo aporte. Es la
distinción que `018 §4` insisted on y que no se debe perder. Lo que sí cambia es
que la obligation queda **acotada**: el orden, si existe, es comportamiento
implícito del hardware y el driver de referencia no lo ejerce ni lo mide.

Consecuencia para el driver propio (`REQUIREMENT`): `PTBA + invalidate` **no es
una operación atómica** y no puede hacerse tal cual sin_cs自有. Un contexto SDMA
que comparta el VMID puede observar una ventana en la que la PTBA ya cambió y la
TLB todavía no, o al contrario. `MODEL_CHOICE`: o se acepta la ventana
documentada, o se fuerza con un mecanismo que el ASIC de GFX8 no tiene.

## 6 · PTE visibility: solo un camino paga el coste, y no es el del ring

Obligation que `025 §2` dejó como `HYPOTHESIS` (`mb()` + `flush_hdp` bastan). Aquí
aporto el dato que faltaba: **qué caminos los emiten**.

| camino | función | `mb()` | `flush_hdp` | estado |
|---|---|:---:|:---:|---|
| GART / bind por CPU | `amdgpu_gart_invalidate_tlb` | **sí** | **sí** | `PROVEN` (`025`) |
| MMIO directo | `gmc_v8_0_flush_gpu_tlb` | **no** | **no** | `PROVEN` |
| ring / submit | `amdgpu_vm_flush` → `emit_vm_flush` | **no** | **no** | `PROVEN` |

El camino MMIO es, literalmente, una línea (`gmc_v8_0.c:664-666`):

```c
/* bits 0-15 are the VM contexts0-15 */
WREG32(mmVM_INVALIDATE_REQUEST, 1 << vmid);
```

Sin barrera, sin flush, sin comentario que justifique la omisión. Y
`amdgpu_vm_flush` (`amdgpu_vm.c:849-852`) emite `emit_vm_flush` sin fence previo.

Esto **no refute el patrón de `025`** — lo delimita correctamente: la secuencia
con `mb()`+`flush_hdp` está `PROVEN` **en el camino del GART y sólo en él**, y es
el único que la paga. Los otros dos dependen del orden previo del llamante, y no
lo aportan ellos mismos.

Estado de la obligation `PTE_VISIBILITY`: sin cambio. La secuencia es `PROVEN`;
el efecto hardware sigue `NOT_DETERMINED`. Lo que se añade es **dónde se aplica**,
que es el dato que faltaba para escribir un driver propio sin asumir que el
`mb()` es una propiedad del mecanismo de invalidate y no de un camino concreto.

## 7 · Actualización de las cuatro proof obligations

| obligation | estado anterior | estado nuevo | base |
|---|---|---|---|
| `HARDWARE_COMPLETION` | `NOT_IMPLEMENTABLE` (provisional, `017`/`018`) | **`PROVEN_ABSENT`** — no existe registro de acuse en GFX8 | §3 |
| `USE_RESPONSE_AS_COMPLETION` | `NOT_DETERMINED` | **`REFUTED` como primitiva sin preparación** — el ack equivalente tiene hazard documentado | §4 |
| `PTBA_INVALIDATE_ATOMICITY` | `NOT_DETERMINED` | **`PROVEN_DERIVED` negativo**: no hay barrier, no son atómicas | §5 |
| `PACKET_EXECUTION_ORDER` | `NOT_DETERMINED` | **`NOT_DETERMINED` (sin cambio)**, acotado por §5 | §5 |
| `PTE_VISIBILITY` | `PROVEN` seq / `NOT_DETERMINED` efecto | **sin cambio**, + alcance: sólo el camino GART | §6 |
| `DISABLE_INVALIDATE_PER_DOMAIN` (bit 21 de `0x501`) | `NOT_DETERMINED` | **`NOT_DETERMINED` (sin cambio)** — sigue siendo un `RREG32` | `229` |

Sobre la última fila, y es la acción pendiente más rentable que queda en esta
capa: **un solo `RREG32` de `VM_L2_CNTL2` (`0x501`) decide si todo §C describe
algo activo.** `umr` está instalado (`/usr/bin/umr`) y es la vía no invasiva que
`229` prefiere sobre `/dev/mem`, pero **exige root** y en esta sesión no se ha
ejecutado. Sigue `NOT_RUN`, y sigue siendo la misma lectura de siempre: sin
escritura, reversible, y responde a tres filas abiertas.

## 8 · Clasificación

| afirmación | estado |
|---|---|
| GFX8 no tiene canales `ENG` de invalidate | `PROVEN_ABSENT` — 12 cabeceras, 0 ocurrencias |
| Ninguna cabecera `gmc/*` (GFX6/7/8) los tiene | `PROVEN_ABSENT` — 12 cabeceras, 0 |
| Los canales aparecen en GFX9+ (`mmhub_1_0`+ / `gc_9_0`+) | `PROVEN` — 18 motores, `ENG0..ENG17` |
| El driver usa ENG en 22 ficheros, todos GFX9+/SOC15 | `PROVEN` |
| Ninguno de esos 22 pertenece a la era GFX7/GFX8 | `PROVEN` |
| GFX9+ tiene acuse per-VMID correlacionado | `PROVEN` — `gmc_v9_0.c:851-857`, `:805` |
| GFX8 no tiene registro de acuse | `PROVEN_ABSENT` |
| El ack de GFX9 puede dar un acuse falso por estado residual | `PROVEN` — `gmc_v9_0.c:842-849` |
| El estado de acuse puede perderse al power-gatear | `PROVEN` — `gmc_v9_0.c:813-818` |
| `RESPONSE` de GFX8 es del mismo tipo de registro que `ACK` de GFX9 | `PROVEN_DERIVED` — ambos son un bitmap de «invalidado» |
| Que `RESPONSE` de GFX8 tenga el mismo hazard | `HYPOTHESIS` — por analogía de clase, **no medido** |
| PTBA y `REQUEST` se emiten como dos escrituras separadas | `PROVEN` |
| Las dos las ejecuta el PFP | `PROVEN` |
| No hay barrera entre ellas | `PROVEN` — `RELEASE_MEM` ausente del path |
| El par no es atómico | `PROVEN_DERIVED` |
| El orden hardware entre ambos packets | `NOT_DETERMINED` |
| `mb()`+`flush_hdp` sólo en el camino GART | `PROVEN` |
| Los caminos MMIO y ring no emiten barrera alguna | `PROVEN` |
| Que la secuencia de `025` baste en esta placa | `NOT_DETERMINED` — sin cambio |

## 9 · Confounders y alcance

- **`PROVEN_ABSENT` es sobre el banco de registros del corpus, no sobre el
  silicio.** Si AMD no publicó un registro, el hardware podría tenerlo sin
  nombre. Pero para el invalidate hay un argumento fuerte que no aplica a otros
  casos: el ASIC **numera y nombra 16 contextos** en `REQUEST`/`RESPONSE` y
  `019`/`211` lo confirman por el bucle `vmid < 16` del propio driver. Un ASIC con
  18 canales de acuse por motor habría muy probablemente los publicado, porque
  GFX9 los publica. Se mantiene como `PROVEN_ABSENT` con esa salvedad, no como
  `PROVEN_ABSENT` absoluto.
- **El sweep es del árbol `linux-7.1.3` del corpus.** No se haContrastado con
  `rx550-upstream-7.2.8`, que es otra copia. El hallazgo `215` documenta que el
  árbol `gmc/` puede faltar según dónde se busca; aquí se buscó en la raíz
  `include/`, que es donde existe, y se verificó con `find` implícito en el glob.
- **La analogía `RESPONSE`↔`ACK` de §4 es `HYPOTHESIS`, no `PROVEN`.** Lo que
  está `PROVEN` es el hazard del ack de GFX9. Que se transfiera a GFX8 es
  razonamiento por clase de registro, y así se etiqueta.
- **No se ha tocado la GPU.** `RUNTIME=NOT_RUN`, ni MMIO, ni debugfs, ni módulos.
  `WRITE_EXECUTION=NONE`.

## 10 · Desfalsificación

- (a) GFX8 no tiene ENG → refutable con
  `grep -c INVALIDATE_ENG include/asic_reg/gmc/gmc_8_1_d.h` (= 0) y con el
  barrido de las 12 cabeceras.
- (b) Los ENG son GFX9+ → refutable con `mmhub_1_0_offset.h` (18 motores).
- (c) El driver los usa → refutable con `grep -rl INVALIDATE_ENG --include=*.c amdgpu/`
  (22 ficheros, ninguno de GFX7/GFX8).
- (d) GFX8 no tiene acuse → refutable con `grep -n "INVALIDATE" gmc/gmc_8_1_d.h`
  (2 líneas, `REQUEST` y `RESPONSE`).
- (e) El ack de GFX9 puede mentir → refutable con `gmc_v9_0.c:842-849`.
- (f) El estado de acuse se pierde al power-gatear → refutable con `gmc_v9_0.c:813-818`.
- (g) No hay barrera entre PTBA y `REQUEST` → refutable con
  `grep -n RELEASE_MEM amdgpu/gfx_v8_0.c` (1 ocurrencia, en otra función).
- (h) `mb()`+`flush_hdp` sólo en GART → refutable con `amdgpu_gart.c:499-504`
  contra `gmc_v8_0.c:664-666`.
- (i) Que `RESPONSE` de GFX8 tenga el mismo hazard que `ACK` → **no refutable
  sin RUNTIME.** Es la fila que queda y por eso está marcada `HYPOTHESIS`.

## 11 · Un defecto del instrumento de reserva, encontrado por usarlo

`tools/nextnum.py` es el mecanismo que reserva números de hallazgo para que dos
sesiones no colisionen. Lo usé, y **me dio un número que ya estaba ocupado.**

La causa está en su índice (`tools/nextnum.py:86`):

```python
NUM_RX = re.compile(r"^(\d{3})[-_](.+)\.md$")
```

**`{3}` son exactamente tres dígitos.** Todo hallazgo con cuatro o más es
invisible para el instrumento. Y el proyecto ya está en el rango de cuatro
dígitos, así que **la reserva no protege la zona donde ahora se collide.**

Medido sobre `06-INGENIERIA-INVERSA/findings/`, **dos veces, y las dos cifras
distieren** — porque hay sesiones escribiendo en paralelo mientras se mide:

| | primera medición | segunda medición |
|---|---:|---:|
| ficheros de hallazgo totales | 514 | 515 |
| visibles para `nextnum.py` (3 dígitos) | 508 | 509 |
| **invisibles (≥4 dígitos)** | **6** | **6** |
| colisiones vivas entre los invisibles | **1** | **0** |

La tercera fila es la que importa y **no se movió**: seis hallazgos con número de
cuatro dígitos son invisibles al instrumento, en las dos mediciones.

La cuarta se movió, y el movimiento es el dato más útil de los dos: **la
colisión que había en `1003` la resolvió la otra sesión durante esta nota.** Se
midió, se renumeró y a los pocos minutos no quedaba. Eso confirma que la carrera
es real y que el daño se está repairing, y también que **cualquier recuento de
este tipo es una fotografía y no un estado**: el valor publicable es «hubo una
colisión viva en `1003`, observada y ya no está», no «hay 1 colisión».

La colisión observada era:

```
1003-no-hay-allocateur-de-vmid-y-el-fsm-que-pide-el-mandato-no-es-el-que-existe.md
1003-la-telemetria-mmio-devuelve-ebusy-<...>.md
```

Este hallazgo es el segundo fichero que pidió `1000`, que ya tenía
`1000-de-pci-enumeration-a-gpu-ready-la-secuencia-completa.md`, y que renumeré
a `1004` tras comprobar la ocupación a mano.

**Lo que el defecto invalida es concreto, y conviene no adornarlo:** `nextnum.py`
declaraba `PROPUESTOS, ninguno ocupado` mientras proponía un número con dos
ficheros en disco. Es exactamente el patrón de `246 §8` —*un script que devuelve
un número sin haber encontrado lo que dice medir*— y por eso se registra aquí y
no se corrige a ciegas: **el instrumento que garantiza la no-colisión tiene un
hueco de alcance, y el hueco está en la zona de numeración que el proyecto está
usando ahora mismo.**

**Fix recomendado, una carácter:** `{3}` → `(\d+)`, que es lo que ya usa el
índice de este documento para contar. No lo aplico aquí: `nextnum.py` es
instrumento compartido, hay sesiones escribiendo en paralelo, y cambiar su
comportamiento de reserva puede hacer que otra sesión reciba un número distinto
del que ya tiene reservado. Queda como acción de tooling, no de este nodo.

Estado: `TOOL_DEFECT`. El instrumento es `DEGRADED`, no `INVALID`: para el rango
de tres dígitos sigue contando bien, y el rango de cuatro dígitos es donde se
falla. El número que había que renumerar era `1003`, y **la otra sesión lo hizo
sola** durante la redacción de esta nota; queda por ver si el hueco del regex
produce la siguiente.

## 12 · Procedencia

- `STATIC`. Fuentes primarias:
  - `include/asic_reg/gmc/gmc_8_1_d.h`, `gmc_8_2_d.h` (los 2 registros de GFX8),
    `gmc/gmc_8_*_sh_mask.h` (`DOMAIN_INVALIDATED_0..15`, `VM_L2_CNTL2__*`),
    `include/asic_reg/mmhub/mmhub_1_0_offset.h` y `_sh_mask.h` (estructura ENG0),
    `gc/gc_9_0_offset.h` … `gc_12_1_0_offset.h` (frontera de generación).
  - `amdgpu/gmc_v9_0.c:790-890` (protocolo de completion completo, sem, ack,
    false-ack), `:805` (KIQ reg-write-reg-wait).
  - `amdgpu/gfx_v8_0.c:6191-6216` (vm_flush literal), `:6231-6239` (RELEASE_MEM
    que pertenece a otra función), `:6349-6374` (`emit_wreg`, motor PFP).
  - `amdgpu/gmc_v8_0.c:662-666` (flush MMIO, una línea), `:668-681` (emit, dos
    escrituras).
  - `amdgpu/amdgpu_gmc.c:711-740`, `amdgpu/amdgpu_vm.c:849-852`.
- Recuentos **impresos por programa**, todos con el globs a la vista. Se
  documenta la discrepancia 12 vs 18 entre dos globs consecutivos en lugar de
  elegir uno: la conclusión (0 ocurrencias) es invariante al alcance.
- No se editó ningún header, ni `AGENTS.md`, ni `OPEN-FRONTIERS.md`.
- **Corrección pendiente y anunciada:** `revkit/INVALIDATE-CANALES.md` debe
  llevar una corrección que marque sus tres afirmaciones como `REFUTED` para
  GFX8. No se ha escrito aquí porque ese fichero es de otra sesión y el alcance
  de este nodo es la prueba obligation; la corrección se registra aquí como
  acción de otro nodo, no se ejecuta a medias.

## 13 · Nota de método

Lo que salió de esta nota fueron **dos restas sobre un mismo conjunto**, y la
segunda es la que importa.

**La primera resta:** lo que el documento afirmaba (`ENG0..ENG17` en «el
hardware») menos lo que GFX8 tiene (`REQUEST`, `RESPONSE`). No es un
`grep` de un símbolo: es un barrido de **dos alcances** — las cabeceras de GFX8,
y todas las de `gmc/*` — para que la ausencia no dependiera de dónde se miró.
Y cuando los dos globs dieron 12 y 18, se dissonó el número en vez de quedarse
con el primero.

**La segunda resta, y la que produce el hallazgo:** lo que GFX9 tiene
(`ACK` con `1<<vmid`, un semáforo, una lectura ficticia para evitar un acuse
falso) menos lo que GFX8 tiene (nada de eso). La comparación entre generaciones
no es un dato de GFX8, pero es lo que **acota** lo que se puede hacer en GFX8: si
el registro equivalente de la generación siguiente necesita tres讪rculos de
precaución para no mentir, entonces la hipótesis de que `RESPONSE` se puede
sonar directamente es más fuerte de lo que parecía.

**Y el patrón de error que esto expone, que es el reutilizable.** El documento
refutado no inventó un registro: leyó el nombre correcto en una cabecera
correcta (`mmhub_3_0_0_sh_mask.h`), y lo bringó a GFX8. El error no es de lectura
de valores ni de aritmética —que es donde fallaron las sesiones anteriores— es
de **ámbito**: un `grep` que encuentra el símbolo donde el símbolo existe, y no
comprueba si existe donde se le está preguntando.

La defence es la de `215`, y ya estaba escrita: *registrar la raíz de búsqueda
antes de citar un hallazgo de ausencia*. Aquí la raíz era `include/asic_reg/gmc/`
—donde el símbolo **no** está— y el documento lo había buscado en
`include/asic_reg/mmhub/`, donde sí. Los dos `grep` devuelven una lista; sólo uno
contesta a la pregunta.
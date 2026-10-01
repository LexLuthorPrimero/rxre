# 029 · Por qué `RELEASE_MEM` no necesita `seq − 1`, y qué queda muerto en GFX8

`CLASSIFICATION=DOCUMENTATION` · `TRACK=STATIC` · `CORPUS=RESEARCH/working/linux-7.1.3`
`WORK_CLASS=READ_ONLY/EVIDENCE` · `WRITE_EXECUTION=NONE` · `MODIFICATIONS=0`
`RUNTIME=NOT_RUN` · `GPU INTACTA`
`CONTINUES=028-fence-completion-orden-d.md` §1.1bis

## CUDA principal

`028` dejo abierta una pregunta: por que `RELEASE_MEM` (GFX9+) no necesita el
`seq − 1` que si exigian GFX7 y GFX8. La respuesta esta en el propio codigo y es
**estructural, no parametrica**:

```
GFX8   PACKET3(RELEASE_MEM, 5)  ->  6 dwords de payload, SIN campo de numero
GFX9   PACKET3(RELEASE_MEM, 6)  ->  7 dwords de payload, CON un dw extra
```

El dw que GFX9 anade al final es la respuesta parcial: **`RELEASE_MEM` en GFX9 lleva un
contador de releases propagado, y el hardware espera a que llegue a cero antes de
confirmar la escritura.** Por eso no hace falta el truco de mandar `seq−1`: el propio paquete
declara cuando ha terminado.

Y el hallazgo lateral, que es mas accionable: **`EOP_EXEC` —el trailing fence— esta
muerto en GFX8.** El codigo lo decodifica, el hardware lo define, y nadie lo pone
nunca en todo el arbol. Y la pagina que lo soportaria se reserva igual, para todos los
rings, sin que nada la escriba (§2.4).

## Alcance exacto

1. Comparar `RELEASE_MEM` de GFX8 y GFX9, payload a payload.
2. Verificar el dw anadido en GFX9 y que lo consume.
3. Determinar si `EOP_EXEC` / trailing fence es alcanzable en GFX8.
4. Clasificar.

## Criterio de terminacion (cumplido)

Los dos `RELEASE_MEM` estan comparados dword a dword, el dw extra esta localizado, y
la alcanzabilidad de `EOP_EXEC` esta cerrada por barrido. Agotado.

---

## 1 · Los dos `RELEASE_MEM`, campo a campo

### 1.1 · GFX8 — `gfx_v8_0_ring_emit_fence_compute` (`gfx_v8_0.c:6231`)

```
PACKET3(PACKET3_RELEASE_MEM, 5)                      5 = payload - 1
  dw0  EOP_TCL1_ACTION_EN | EOP_TC_ACTION_EN | EOP_TC_WB_ACTION_EN
       | EVENT_TYPE(CACHE_FLUSH_AND_INV_TS_EVENT) | EVENT_INDEX(5)
  dw1  DATA_SEL(write64bit ? 2 : 1) | INT_SEL(int_sel ? 2 : 0)
  dw2  addr & 0xfffffffc
  dw3  upper_32_bits(addr)
  dw4  lower_32_bits(seq)
  dw5  upper_32_bits(seq)
```

6 dwords de payload. **Ninguno es un contador.**

### 1.2 · GFX9 — `gfx_v9_0_ring_emit_fence` (`gfx_v9_0.c:5536`)

```
PACKET3(PACKET3_RELEASE_MEM, 6)                      6 = payload - 1
  dw0  dw2: EOP_TCL1_ACTION_EN | EOP_TC_ACTION_EN | EOP_TC_MD_ACTION_EN
          | EOP_TC_WB_ACTION_EN
          | EVENT_TYPE(CACHE_FLUSH_AND_INV_TS_EVENT) | EVENT_INDEX(5)
          [+ EOP_EXEC si flags & FENCE_FLAG_EXEC]
  dw1  DATA_SEL(...) | INT_SEL(...)
  dw2  lower_32_bits(addr)
  dw3  upper_32_bits(addr)
  dw4  lower_32_bits(seq)
  dw5  upper_32_bits(seq)
  dw6  0                                   <-- EL NUEVO
```

7 dwords. Dos diferencias respecto a GFX8:

1. **`EOP_TC_MD_ACTION_EN` (bit 21, "L2 metadata")** aparece en el control. No existe
   en el vocabulary de GFX8: definido en `soc15d.h:321`, y `grep` sobre
   `gfx_v6_0`/`v7_0`/`v8_0`/`v10_0`/`v12_1` da **0** en todos. Solo GFX9 lo usa, y una
   sola vez, precisamente aqui.
2. **Un septimo dword, escrito como `0`.**

Verificacion con la herramienta de `023` (`pm4_count_census.py`, que mide
`n − payload` sobre el arbol): ambos cumplen `n = payload − 1` — 6−1=5 y 7−1=6. Los
dos numeros de `n` estan bien para la convencion que `023` midio en 68/68 del path GFX8.
`PROVEN`.

### 1.3 · Que consume ese dw

**No lo se.** Y esa es la respuesta honesta, no una evasion:

- El codigo escribe `amdgpu_ring_write(ring, 0)` sin comentario.
- No hay ningun campo con nombre que lo describa: el corpus no tiene documentacion de
  `RELEASE_MEM` mas alla del opcode (`sid.h`, `vid.h`).
- Buscar un nombre tipo `RELEASE_*` o `*_RELEASE*` en los headers **no** da un campo que
  lo describa.

`NOT_DETERMINED`, con la causa nombrada: **falta la especificacion PM4**, la misma
fuente que falta en `022` y `023`. No es que no se haya buscado; es que la
documentacion de este paquete no esta en el corpus, ni en GFX8 ni en GFX9.

Lo que si es `PROVEN` y es util: **GFX9 anadio un dword y actuo sobre L2 metadata**, y
con ello elimino la necesidad del `seq − 1`. La correlacion es `OBSERVATION`, no
`CAUSAL`: no puedo demostrar que el dw nuevo *sea* el contador de releases y no otra
(un tamano, una mascara, un reservado) que coincida con que el problema desaparecio.

## 2 · `EOP_EXEC`: definido, decodificado, muerto

Este es el hallazgo con mas valor para el driver propio.

### 2.1 · Que lo define

```
vid.h:249    #define EOP_EXEC   (1 << 28)  /* For Trailing Fence */
```

Es un bit del **control del propio EOP**, no un paquete. Esta documentado en el
header, con un comentario que explica su proposito: ejecutar el fence aunque se haya
perdido el contexto.

### 2.2 · Quien lo decodifica

```
gfx_v7_0.c:2118   bool exec = flags & AMDGPU_FENCE_FLAG_EXEC;
gfx_v8_0.c:6140   bool exec = flags & AMDGPU_FENCE_FLAG_EXEC;
gfx_v9_0.c:5542   bool exec = flags & AMDGPU_FENCE_FLAG_EXEC;
```

Las tres generaciones **leen** el flag. GFX8 lo aplica:

```c
PACKET3(PACKET3_EVENT_WRITE_EOP, 4)
... | (exec ? EOP_EXEC : 0))
```

en el segundo de los dos EOP (`gfx_v8_0.c:6163`).

### 2.3 · Quien lo pone

```
$ grep -rn "FENCE_FLAG_EXEC" *.c | grep -v "bool exec" | grep -v gfx_v9_0
(vacio)
```

**Nadie, en todo el arbol de 7.1.3.** Los unicos que lo ponen son `gfx_v9_0.c:5744` (en
`gfx_v9_0_ring_preempt_ib`) y `gfx_v9_0.c:7230`/`:7244` (dos call sites mas, tambien de
preemption).

Y la preemption, en GFX8, **no existe**: `018`/`022` ya estableceron que `preempt_ib`
no esta asignado en ninguna `ring_funcs` de `gfx_v8_0`, y `set_preempt_cond_exec` solo
lo llaman ASIC que si lo tienen.

`PROVEN_ABSENT` por barrido de todo el arbol, no por lectura parcial: el termino
aparece 7 veces en `.c` y ninguna es un producer del flag en un ring GFX8.

### 2.4 · Y el recurso: nadie lo escribe, pero hay quien lo lee

**MATICES IMPORTANTE, y es una correccion de mi primera redaccion.** Escribi que la
pagina "no se usa". Es mas exacto decir **que nadie la escribe y dos sitios la leen**:

```
ESCRITORES de trail_fence_gpu_addr / trail_seq:
  gfx_v9_0.c, gfx_v10_0.c, gfx_v11_0.c, gfx_v12_0.c   (preempt_ib)
  sdma_v5_0, v5_2, v6_0, v7_0, v7_1                   (preemption de SDMA)
  amdgpu_vpe.c                                         (preemption de VPE)
  -> ninguno de GFX6/7/8

LECTORES:
  amdgpu_fence.c:887    seq_printf de "Last signaled trailing fence"
                         -> se ejecuta para rings GFX y SDMA, SIN guarda
  amdgpu_debugfs.c:2018  debugfs preempt_ib
                         -> tras `if (!ring->funcs->preempt_ib) return -EINVAL;`
```

La asignacion y liberacion, para todos los rings:

```
amdgpu_ring.c:285   r = amdgpu_device_wb_get(adev, &ring->trail_fence_offs);
amdgpu_ring.c:312   ring->trail_fence_gpu_addr = amdgpu_ring_get_gpu_addr(...);
amdgpu_ring.c:407   amdgpu_device_wb_free(ring->adev, ring->trail_fence_offs);
```

Asi que el estado correcto es:

| afirmacion | estado |
|---|---|
| La pagina se reserva para **todo** ring, incluido GFX8 | `PROVEN` |
| Ningun `.c` de GFX6/7/8 **escribe** en ella | `PROVEN` (barrido de escritores) |
| `amdgpu_fence.c:887` la **lee** en rings GFX de GFX8 | `PROVEN` |
| Su valor en GFX8 es siempre 0 | `PROVEN_DERIVED` — nadie lo escribe |
| `trail_seq` en GFX8 es siempre 0 | `PROVEN_DERIVED` — `kcalloc_obj`/`= 0`, nadie lo incrementa |

Que el debugfs muestre `0` para el trailing fence de un ring GFX8 en GFX8 no es un
fallo: es el valor correcto de un contador que nunca avanza. `amdgpu_fence.c` lo imprime
sin preguntar si el ring soporta preemption, lo cual es una pequena asimetria de
diagnostico, no un bug —el numero es correcto, solo que no significa nada.

Consecuencia cuantificable: `adev->wb` aloja `fence_offs`, `rptr_offs`, `wptr_offs`,
`cond_exe_offs` (este ultimo tambien inerte en GFX8, `022`) y `trail_fence_offs`. Son
**dos paginas por ring** —`cond_exe_offs` y `trail_fence_offs`— para dos mecanismos que
en esta ASIC no se pueden activar.

`NEGATIVE_RESULT` heredable y accionable: el driver propio **no debe reservar ni
`cond_exe_offs` ni `trail_fence_offs`** si no implementa preemption, y si implementa su
propio diagnostico, omitir el campo del trailing fence en rings que no lo soporten.
Ahorro con justificacion, no por gusto.

## 3 · Que NO se resuelve

La pregunta de `028` —*por que* `RELEASE_MEM` no necesita `seq − 1`— tiene ahora una
**hipotesis con soporte** pero no una prueba:

```
H1  El dw anadido en GFX9 es un contador de releases pendientes, y el hardware
    espera a cero antes de confirmar la escritura. El seq-1 de GFX7/8 era el
    equivalente artesanal de esa espera.

H2  El dw anadido no tiene relacion con el vaciado, y lo que elimina el
    seq-1 es EOP_TC_MD_ACTION_EN (invalidar tambien la metadata de L2).

H3  Es otra cosa: el fence de GFX9 es un paquete distinto con semantica
    distinta, y la comparacion "mismo nombre, distinto paquete" es enganosa.
```

`H1` es la lectura mas natural y encaja con que el dw se escriba a 0 en vez de a un
valor derivado de `seq` —un contador pendiente arranca en 0 en cada operacion. `H2`
tiene apoyo: `EOP_TC_MD_ACTION_EN` es un campo **nuevo en la misma generacion** que
actua sobre un componente **nuevo** (L2 metadata). `H3` no se puede descartar.

Lo que las separa es un experimento de hardware, o la especificacion PM4. Ninguna de
las dos esta en el corpus. `NOT_DETERMINED` las tres, con la direccion del
discriminante identificada.

## 4 · Clasificacion

| Afirmacion | Estado |
|---|---|
| GFX8 `RELEASE_MEM` tiene 6 payload, GFX9 tiene 7 | `PROVEN` |
| Ambos cumplen `n = payload − 1` | `PROVEN` (census de `023`) |
| GFX9 anade `EOP_TC_MD_ACTION_EN` (bit 21, "L2 metadata") | `PROVEN` |
| Ese campo no existe en GFX6/7/8/10/12 | `PROVEN_ABSENT` |
| El dw anadido se escribe como `0` y no tiene nombre | `PROVEN` |
| Que ese dw sea un contador de releases | `NOT_DETERMINED` — falta la spec PM4 |
| Que `EOP_EXEC` este definido en el header | `PROVEN` (`vid.h:249`) |
| Que GFX7/GFX8/GFX9 lo **lean** | `PROVEN` |
| Que **nadie lo ponga** en un ring GFX8 | `PROVEN_ABSENT` (barrido de 7.1.3) |
| Que `trail_fence_offs` se reserve por ring y no se use en GFX8 | `PROVEN` |
| Que el trailing fence sea la unica via de `EOP_EXEC` | `PROVEN_DERIVED` |
| Que `trail_fence_cpu_addr` se lea en rings GFX de GFX8 | `PROVEN` (`amdgpu_fence.c:887`) |
| Que `RELEASE_MEM` de GFX9 quitara el problema por su dw nuevo | `OBSERVATION`, no `CAUSAL` |

## 5 · Confounders

- El barrido de `FENCE_FLAG_EXEC` se hizo sobre `amdgpu/*.c` del corpus parcial. Los
  subdirectores `amdkfd`, `display`, `dc`, `vcn`, `jpeg` no se revisaron. Que ninguno
  ponga el flag en un ring de GFX8 es muy probable —el flag es de ring de GFX— pero el
  estado estricto es `NOT_OBSERVED` fuera de `amdgpu/`, no `PROVEN_ABSENT` global.
- La relacion entre el dw de GFX9 y el fin del `seq − 1` es **temporal**, no causal. Dos
  cambios simultaneos (dw nuevo + `MD_ACTION_EN`) y una correlación. La separacion
  necesita hardware.
- `EOP_TC_MD_ACTION_EN` esta en `soc15d.h`, que es el header de SOC15/GFX9. Que el bit
  21 tuviera otro significado en GFX8 **no** se verifico: no hay una
  `vid.h` equivalente con ese campo, y `vid.h` no lo define. `PROVEN_ABSENT` es que el
  driver no lo usa, no que el hardware lo reservara.

## 6 · UNLOCKS

- El driver propio tiene **dos mechanisms de fence documentados** y uno de ellos
  (`EOP_EXEC`) puede ignorar con justificacion mientras no implemente preemption.
- `trail_fence_offs` es una pagina por ring que GFX8 gasta sin usar. El driver propio
  puede no reservarla. Y `022` ya habia comprobado que `cond_exe_offs` esta en la misma
  situacion: **dos paginas por ring, dos mecanismos muertos**. Juntas son un ahorro
  concreto y justificable.
- La pregunta de por que `RELEASE_MEM` no necesita `seq − 1` tiene ya su **discrutinante
  identificado** y sus tres hipotesis separadas. Es la forma en que debe quedar una
  pregunta de hardware: no "no se", sino "esto es lo que la resolveria".
- `EOP_TC_MD_ACTION_EN` ("L2 metadata") es la pista de que en GFX9+ el flush de caches
  toca un componente que en GFX8 no existe o no se nombra. Es el hilo que conectaria con
  la frontera G (cache/coherencia) de `AGENTS.md`.

## 7 · Criterio de falsificacion

Se refutaria si: (a) un subdirectorio no revisado pusiera `FENCE_FLAG_EXEC` en un ring
de GFX8, lo que haria `EOP_EXEC` alcanzable y eliminaria el `PROVEN_ABSENT`; (b) el dw
anadido de `RELEASE_MEM` estuviera documentado en el corpus con un nombre que no sea
contador, refutando `H1`; (c) existiera un paquete `RELEASE_MEM` en GFX8 con 7 payload
en alguna ruta no revisada, lo que haria la diferencia de generacion ilusoria. (a) es
completable con el corpus. (b) y (c) exigen documentacion o barrido adicional.

## 8 · Evidencia

```
gfx_v8_0.c:   6231-6248 (fence_compute, RELEASE_MEM 5 -> 6 payload)
gfx_v9_0.c:   5536-5571 (fence, RELEASE_MEM 6 -> 7 payload, dw6 = 0),
              5542 (lee FENCE_FLAG_EXEC), 5744 / 7230 / 7244 (lo ponen: preemption)
gfx_v7_0.c:   2118 (lee el flag), 2120 (workaround seq-1)
soc15d.h:     320-321 (EOP_TC_NC_ACTION_EN, EOP_TC_MD_ACTION_EN "L2 metadata")
vid.h:        249 (EOP_EXEC "For Trailing Fence"), 237-266 (encoding)
amdgpu_ring.h: 67 (AMDGPU_FENCE_FLAG_EXEC), 404-406 (trail_seq, trail_fence_gpu_addr)
amdgpu_ring.c: 285-287 (wb_get trail_fence_offs), 312-315 (gpu/cpu addr),
              407 (wb_free)
              238-250 (KIQ sin scheduler), 172-173 (drm_err si count_dw < 0)
barrido:      grep -rn FENCE_FLAG_EXEC *.c -> 7 hits, ninguno producer en GFX8
             grep -rn EOP_TC_MD_ACTION_EN gfx_v*.c -> solo gfx_v9_0
08-ARQUITECTURA/tools/pm4_count_census.py  (verifica n = payload - 1 en ambos)
```

Ningun registro obtenido de MMIO. Ninguna operacion runtime. `GPU INTACTA`.

Nota de redaccion: el borrador contenia texto en otro idioma en la CUDA principal y
una palabra sin sentido en §2. Corregidos. Decimo caso del mismo defecto al
escribir; la nota se conserva porque el patron es mio y se repite.
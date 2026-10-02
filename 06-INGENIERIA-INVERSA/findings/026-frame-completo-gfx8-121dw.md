# 026 · La fórmula de reserva está escrita: `emit_frame_size + num_ibs * emit_ib_size`

`CLASSIFICATION=DOCUMENTATION` · `TOOL=tools/pm4dw.c --path` + aritmética de `vi_structs.h`
`CORPUS=rx550-upstream-7.2.8/linux-7.2.8` · `RUNTIME=NOT_RUN` · `GPU INTACTA`
`CONTINUES=024, 025`

## CUDA principal

El `NOT_DETERMINED` que dejé en `025 §8` no era un misterio: estaba escrito en
`amdgpu_ib.c:197-198`.

```c
alloc_size = ring->funcs->emit_frame_size + num_ibs * ring->funcs->emit_ib_size;
r = amdgpu_ring_alloc(ring, alloc_size);
```

**El frame y los IBs se reservan por separado.** `emit_frame_size` cubre todo lo que emite
el anillo *fuera* de los indirect buffers, y cada IB añade `emit_ib_size` (= 4 en GFX8 GFX).
Eso convierte la pregunta "¿cuál es la ruta máxima de un envío?" en aritmética cerrada.

Y al hacerlo aparece un error de conteo propio que la herramienta había marcado sin medir:
`write_multiple` no es un dword, son 17.

## Alcance exacto

1. Localizar la fórmula de reserva de un envío.
2. Enumerar la secuencia completa de `amdgpu_ib_schedule` para GFX8.
3. Expandir los `write_multiple` que la herramienta marcó como no expandidos.
4. Cerrar el veredicto de infrarreserva.

## Criterio de terminación (cumplido)

Secuencia completa enumerada, fórmula localizada, `write_multiple` expandido con el tamaño
de struct del propio corpus. Agotado.

---

## 1 · La fórmula

`amdgpu_ib.c:197-200`. `amdgpu_ring_alloc` es lo que exige la reserva; si se queda corta, el
buffer del ring se desborda. Esa es la consecuencia, no una especulación: `count_dw` se
decrementa en cada escritura (`amdgpu_ring.h:498`) y `amdgpu_ring_alloc` falla si no cabe.

Consecuencia inmediata para `020`, `024` y `025`: los residuales `+98/+57/+46` y la ruta de
63 dw se comparaban contra un número que **nunca incluía los IBs**, y no hacía falta que los
incluyera. La reserva está partida en dos sumandos y el análisis va por la vía correcta.

## 2 · Secuencia completa de un envío GFX8 GFX

`amdgpu_ib.c:124-331`, en orden de emisión:

| # | emisor | línea | dw (medido) |
|---|---|---|---:|
| 1-8 | `amdgpu_vm_flush` (ruta de `025`) | 223 | 63 |
| 9 | `emit_mem_sync` | 235-236 | 5 |
| 10 | `init_cond_exec` | 246-248 | 5 |
| 11 | `emit_cntxcntl` | 258-262 | 11 → **32** |
| 12 | `emit_ib` × `num_ibs` | 272-285 | 4 c/u — **cuenta aparte** |
| 13 | `emit_fence` (fence de usuario) | 299-302 | 12 |
| 14 | `emit_fence` (af) | 310 | 12 |
| 15 | `patch_cond_exec` | 319 | 0 |
| 16 | `emit_switch_buffer` | 322-323 | 2 |

Lo que **no** existe en GFX8 y por tanto no aparece: `insert_start`, `emit_wave_limit`,
`emit_gfx_shadow`, `emit_frame_cntl`, `insert_end`, `emit_cleaner_shader`. Seis ramas del
driver de referencia que no aplican a esta GPU, todas comprobadas por
`grep -c "\.campo *=" gfx_v8_0.c` sobre el `ring_funcs` real.

## 3 · `write_multiple`: el error que la herramienta señaló

La herramienta marcó `gfx_v8_0_ring_emit_ce_meta` y `_de_meta` con
`write_multiple:NOT_EXPANDED` y los contó como 1 dword. El tamaño está en el corpus:

```c
/* include/vi_structs.h:434 */
struct vi_de_ib_state {           /* 17 uint32_t */
        uint32_t ib_completion_status;  uint32_t de_constEngine_count;
        uint32_t ib_offset_ib1;         uint32_t ib_offset_ib2;
        ... 13 más ...
}; /* Total of 17 DWORD */
```

Y la cuenta del emisor (`gfx_v8_0.c:7189-7205`):

```c
cnt_de = (sizeof(de_payload.regular) >> 2) + 4 - 2;   /* (68>>2) + 2 = 19 */
...
amdgpu_ring_write_multiple(ring, (void *)&de_payload, cnt_de - 2);   /* 17 dwords */
```

| struct | dword | `cnt_de` | `write_multiple` | total real |
|---|---:|---:|---:|---:|
| `vi_de_ib_state` | 17 | 19 | **17** | **21** |
| `vi_de_ib_state_chained_ib` | 27 | 29 | 27 | 31 |
| `vi_ce_ib_state` | 4 | 6 | **4** | **8** |
| `vi_ce_ib_state_chained_ib` | 10 | 12 | 10 | 14 |

`gfx_v8_ring_emit_cntxcntl` mide 11 (3 directos + 4 + 4). Real, no encadenado:
**3 + 8 + 21 = 32**. Encadenado: **3 + 14 + 31 = 48**.

La herramienta acertó al *marcar* y se equivocó al *contar*. Es exactamente el contrato que
declaré en `024 §5`: un número sin supuestos no es evidencia, y aquí el supuesto
`write_multiple = 1` era falso. La etiqueta hacía falta; el número no.

## 4 · El veredicto

```
medido por la herramienta                     90 dw
+ emit_cntxcntl real en vez de medido       +21 dw   (32 vs 11)
+ emit_vm_flush tras el despacho indirecto   +10 dw
                                          ─────────
ruta maxima de un frame, sin cadena IB       121 dw
emit_frame_size declarado                   172 dw
                                          ─────────
holgura                                      51 dw
```

Con `chained_ib_support` activo: 137 dw, holgura 35 dw.

**Ningún infrarreserva.** Y ahora sí es veredicto y no cota, porque la condición de
alcanzabilidad que `025 §2` estableció se cumple también para el resto de la secuencia: las
condiciones son campos independientes del job y no hay exclusión mutua.

## 5 · Un caso donde la reserva sí es insuficiente

`emit_ib_size = 4` (`gfx_v8_0.c:6900`) y `gfx_v8_0_ring_emit_ib_gfx` escribe **exactamente 4**
(`:6097-6104`). Correcto.

Pero `emit_ib` llama a `gfx_v8_0_ring_emit_de_meta` cuando
`amdgpu_sriov_vf(ring->adev) && (ib->flags & AMDGPU_IB_FLAG_PREEMPT)` (`gfx_v8_0.c:6090-6095`),
y eso son 21 dw, no 0. El IB real costaría 25 dw frente a los 4 reservados.

Con la holgura de 51 dw del frame, se toleran ~2 IBs con preemption antes de desbordar.
Clasificación: `LIMITATION`, no `DEFECT`, por dos razones que constan: (a) exige SR-IOV VF,
es decir la GPU dentro de una máquina virtual, que **no es el objetivo del proyecto**; (b)
`num_ibs` tiene un límite impuesto por el llamante y no he verificado ese límite ni el
comportamiento de `amdgpu_ring_alloc` ante el desbordamiento. Reclamar un bug aquí sería
`PLAUSIBLE`, no `PROVEN`.

**No aplica a metal desnudo**, que es el caso objetivo. Se documenta porque el número
`emit_ib_size = 4` se va a copiar tal cual en un driver propio y ahí sí importa.

## 6 · UNLOCKS

- El número definitivo para el frame GFX8: **121 dw** (137 con chained IB). Es lo que hay
  que reservar, más `num_ibs * 4`.
- Seis ramas del camino de envío no existen en GFX8. Eso reduce el espacio de diseño del
  driver propio más que cualquier dato de registro.
- `vi_structs.h` documenta tamaños de payload de meta-datos en DWORD exactos. Es la fuente
  para calcular emisión de PM4 en GFX8 sin hardware, y nadie la estaba usando.

## 7 · Lo que sigue abierto

| Afirmación | Estado | Por qué |
|---|---|---|
| 121 dw es la ruta máxima del frame GFX8 | `PROVEN_DERIVED` | secuencia enumerada, `write_multiple` expandido con tamaños del corpus |
| La reserva alcanza en todos los casos | `PROVEN` para el frame | 121 ≤ 172 |
| La reserva alcanza con preemption en VF | `NOT_DETERMINED` | §5; aritmética hecha, pero no aplicable al objetivo y sin verificar el límite de `num_ibs` |
| `chained_ib_support` activo en Polaris12 | `NOT_DETERMINED` | depende de VBIOS/atomBIOS del host, no del corpus |

## 8 · Evidencia

```
herramienta:  tools/pm4dw.c (--path), sha256 pending de recompilar tras el fix de buffer
build:        cc -O2 -Wall -Wextra, 0 warnings
corpus:       12e8d5a973d1ad7c5a5c69882e4022b131ed715db7003fdcd760ddf8c3e51941 (linux-7.2.8.tar.xz)

amdgpu_ib.c:      124-331 (secuencia), 197-200 (fórmula de reserva)
amdgpu_ring.h:    494-499 (un write = un dword), 544-553 (patch_cond_exec emite 0)
amdgpu_vm.c:      772-898 (ruta de vm_flush)
gfx_v8_0.c:       6900-6917 (ring_funcs GFX, emit_frame_size=172, emit_ib_size=4),
                  6075-6105 (emit_ib_gfx, 4 dw + de_meta condicional),
                  6905-6917 (campos que NO existen: insert_start, emit_wave_limit,
                  emit_gfx_shadow, emit_frame_cntl, insert_end, emit_cleaner_shader),
                  7180-7205 (de_meta, cnt_de y write_multiple),
                  5122-5131 (gds_switch)
include/vi_structs.h: 434-455 (vi_de_ib_state, 17 dword), 470+ (chained, 27 dword)
```

Ningún registro leído de MMIO. `RUNTIME=NOT_RUN`. `GPU INTACTA`. `MODIFICATIONS=0`.
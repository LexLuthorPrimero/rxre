# 010 — P-8: completion con y sin IRQ

**Ámbito**: `08-ARQUITECTURA/` — IA-3 (Arquitecto)
**Fecha**: 2026-09-29 · **Ronda**: 17
**Tipo**: `READ_ONLY/EVIDENCE` — enumeración semántica estática con Coccinelle + `ctags`.
  **Sin runtime, sin carga de módulos, sin escritura en hardware, sin commit.**
**Artefactos usados**:
- `RESEARCH/kernelbuild/linux-7.1.3/drivers/gpu/drm/amd/amdgpu/` — subárbol parcial
- `08-ARQUITECTURA/tools/semref/` — herramienta construida en esta ronda
**Corrige**: `008-d` §P-8 y `009` §«Clasificación revisada de P-8» (no los reescribe: quedan
  como registro del estado anterior)
**No toca**: `AGENTS.md`, `COORDINACION.md`, `07-DRIVER/`, `008-a/b/c/d/e`, Q-5, cerrojos ajenos

---

## 1. El discriminante que 009 dejó abierto

`009:267-275` dejó `P-8 = NOT_DETERMINED` con un discriminante exacto y de una función:

> ¿quién más llama a `amdgpu_fence_process()` o a `amdgpu_fence_schedule_fallback()`?

La hipótesis de trabajo de `009`, explícita, era: *«si `amdgpu_fence_process()` solo se llama
desde la IRQ, el timer solo se arma después de la primera IRQ»*. **Queda refutada.**

## 2. Enumeración exhaustiva

`amdgpu_fence_process` — 3 sitios de llamada en `amdgpu_fence.c`, **ninguno en la IRQ**:

| línea | función envolvente | contexto |
|---|---|---|
| `amdgpu_fence.c:263` | `amdgpu_fence_fallback()` | timer (`fallback_timer`) |
| `amdgpu_fence.c:671` | `amdgpu_fence_driver_force_completion()` | **teardown — nuevo** |
| `amdgpu_fence.c:876` | `amdgpu_debugfs_fence_info_show()` | debugfs |

`amdgpu_fence_schedule_fallback` — 2 sitios, ambos fuera de IRQ:

| línea | función envolvente | contexto |
|---|---|---|
| `amdgpu_fence.c:221` | `amdgpu_fence_process()` | rearmado |
| `amdgpu_fence.c:821` | `amdgpu_fence_enable_signaling()` | armado inicial, invocado por el core |

Control de clasificación: `grep` da 4 y 3 apariciones respectivamente; spatch da 3 llamadas y
2, con 1 definición en cada caso. `3+1=4` y `2+1=3`. El reparto queda fijado por la línea
`TOTAL` completa; el contraste con `grep` fija la suma, **no el reparto** — `grep` no
distingue definición de llamada.

## 3. Las dos rutas nuevas

### 3.1 Teardown: `amdgpu_fence_driver_hw_fini` → `force_completion`

```
amdgpu_fence_driver_hw_fini()                        amdgpu_fence.c:~528
   │
   ├── if (!drm_dev_is_unplugged(adev_to_drm(adev)))
   │       r = amdgpu_fence_wait_empty(ring)
   │   else
   │       r = -ENODEV
   │
   └── if (r)                                          /* fallo, o dispositivo desconectado */
           amdgpu_fence_driver_force_completion(ring)  amdgpu_fence.c:550
                ├── amdgpu_fence_driver_set_error(ring, -ECANCELED)
                ├── amdgpu_fence_write(ring, ring->fence_drv.sync_seq)
                └── amdgpu_fence_process(ring)          amdgpu_fence.c:671
                        └── dma_fence_signal()
```

Comentario del kernel en el sitio: *«no need to trigger GPU reset as we are unloading»*.

`amdgpu_fence_driver_force_completion` tiene 9 sitios de llamada adicionales, todos de
suspensión, error de IP o teardown: `amdgpu_device.c:5112`, `amdgpu_sdma.c:603,606`,
`amdgpu_vcn.c:1522,1524`, `amdgpu_uvd.c:515`, `vcn_v4_0_3.c:1689`, `vcn_v5_0_1.c:1335`,
`amdgpu_debugfs.c:2053`.

**Es un mecanismo distinto, no una variante del timer ni un «tercer IRQ».** Se alcanza
precisamente cuando la IRQ no puede completar el trabajo.

### 3.2 Parada del scheduler: `amdgpu_job_stop_all_jobs_on_sched`

```
amdgpu_device.c:5610
   └── amdgpu_job_stop_all_jobs_on_sched(&ring->sched)     amdgpu_job.c:482
            ├── dma_fence_signal(&s_fence->scheduled)       amdgpu_job.c:496
            ├── dma_fence_signal(&s_fence->finished)        amdgpu_job.c:498
            └── dma_fence_signal(&s_fence->finished)        amdgpu_job.c:509
```

Segunda vía independiente de señalización sin IRQ, también en teardown. **No requiere el
timer ni `force_completion`.**

## 4. Reclasificación de P-8

| tramo | estado | evidencia |
|---|---|---|
| SUBMIT EMISSION sin IRQ | `PROVEN` | `amdgpu_job.c:451` `amdgpu_ib_schedule()` |
| FENCE SIGNAL por IRQ | `PROVEN` | ruta principal; `amdgpu_fence_process` se llama desde los `*_process_interrupt` de cada IP |
| FENCE SIGNAL por timer | `PROVEN` | armado en `amdgpu_fence.c:821`, fired en `:258-263` |
| **COMPLETION en teardown sin IRQ** | **`PROVEN`** | `amdgpu_fence_driver_hw_fini` → `force_completion` → `fence_process` → `dma_fence_signal` |
| **COMPLETION por parada de scheduler sin IRQ** | **`PROVEN`** | `amdgpu_job_stop_all_jobs_on_sched` → `dma_fence_signal` |
| caller `amdgpu_debugfs_fence_info_show` | `PROVEN` como caller | `amdgpu_fence.c:876` |
| …de ese caller como **mecanismo** de completado | **`NOT_DETERMINED`** | llama a la misma función, pero no se ha trazado qué efecto tiene sobre los fences |
| Capacidad de la GPU para completar sola, sin proceso de kernel | `NOT_DETERMINED` | requiere `F4-AD-8`: ningún offset de registro con fuente registrada |
| Secuencia TMR exacta escrita por la GPU | `OPEN` | la GPU escribe `sync_seq`; la ISA está fuera del corpus C |

### Corrección explícita

`P-8` **no** admite una sola etiqueta. La formulación «no existe camino de completado sin
IRQ» es **incorrecta como afirmación general** y queda refutada en el contexto de teardown.
Lo que sí se sostiene es la formulación partida de la tabla anterior.

## 5. Clasificación de las llamadas, y dos límites

Barrido completo de los callers de `amdgpu_fence_process` en el subárbol amdgpu (linux-7.1.3).
Cada sitio se verificó línea por línea contra el fuente. 53 funciones envolventes:

```text
TOTAL_CALLERS   116
IRQ             112   (53 funciones)
NON_IRQ           4   ( 4 funciones)
UNKNOWN           0
```

Control independiente: `grep` da 117 ocurrencias textuales, menos 1 definición = **116**.

**IRQ — cadena estructural, no por nombre.** Las 53 funciones se alcanzan así:

```text
amdgpu_irq.c:345   request_irq(irq, amdgpu_irq_handler, IRQF_SHARED, …)
amdgpu_irq.c:200     amdgpu_irq_handler                    ← hard IRQ
amdgpu_irq.c:514       r = src->funcs->process(adev, src, &entry);
```

`grep -rn '\->process('` sobre el subárbol devuelve **una sola línea**, la 514. Toda función
asignada a `.process = <fn>` en un `amdgpu_irq_src_funcs` se alcanza únicamente desde
`amdgpu_irq_handler`: son **52**. La 53.ª es `amdgpu_mcbp_handle_trailing_fence_irq`, que **no**
es fuente IRQ: se llama solo desde `gfx_v9_0_eop_irq` (`gfx_v9_0.c:6231`), que sí lo es. El
nombre mentía; sin el criterio de no inferir por nombre se habría clasificado por casualidad.

**Los 4 NON_IRQ**, con contexto y si son completion:

| caller | file:line | contexto | completion |
|---|---|---|---|
| `amdgpu_fence_fallback` | `amdgpu_fence.c:263` | timer; `PROVEN` por `timer_setup(&…fallback_timer, amdgpu_fence_fallback, 0)` `:459` | **sí** |
| `amdgpu_fence_driver_force_completion` | `amdgpu_fence.c:671` | forzado; 9 callers, todos fini/suspend/error | **sí** |
| `amdgpu_debugfs_fence_info_show` | `amdgpu_fence.c:876` | `DEFINE_SHOW_ATTRIBUTE`, seq_file solo lectura | no — observación |
| `amdgpu_debugfs_ib_preempt` | `amdgpu_debugfs.c:2042` | debugfs **write** (`:2113`), preempt de IB | no — control |

`amdgpu_debugfs_ib_preempt` y `amdgpu_mcbp_handle_trailing_fence_irq` no figuraban en la
primera redacción de este apartado.

**Corrección de una cifra.** Una versión anterior de este apartado declaraba 124 llamadas.
Era incorrecto. El parser de la herramienta contaba como sitio de llamada toda línea
eliminada del diff, y en un `if/else` Coccinelle reemplaza la rama completa, de modo que
`else` y otras líneas de contexto aparecían como eliminadas. Eran **8 sitios espurios**:
`gfx_v10_0.c:9196`, `gfx_v11_0.c:6536`, `gfx_v12_0.c:4874`, `si_dma.c:650`, `uvd_v6_0.c:1265`,
`:1266`, `:1271`, `:1272`. Parser corregido y regresión `R-3` añadida.

### El porcentaje no establece el mecanismo

`112/116` es una **clasificación de callers**, no una propiedad del mecanismo de completion.
Los 2 NON_IRQ que completan fences son un temporizador de respaldo y un camino de error en
teardown; **ninguno es la ruta normal de submission**. Que la completion normal de GFX
requiera IRQ queda establecido por la cadena específica `gfx_v*_eop_irq` →
`amdgpu_fence_process` → `dma_fence_signal`, **no** por el porcentaje.

- Esta ronda **no midió nada**: no hay `OBSERVED`. Todo lo anterior es `PROVEN` por
  enumeración estática exhaustiva sobre fuente 7.1.3, sin contraste contra 7.2.8 para las
  rutas de teardown.

## 6. Nota de método

`grep` **ya veía** `amdgpu_fence_driver_force_completion`. El fallo no fue de visibilidad
textual sino de **cobertura de enumeración y cierre semántico**: se encontró el caller sin
seguir su efecto hasta `amdgpu_fence_process()`. Es exactamente el fallo que
`08-ARQUITECTURA/tools/semref/` automatiza.

La capacidad que produjo el hallazgo es **ENUMERACIÓN**, no resolución semántica.
`semref` **no** resuelve punteros a función: tres patrones fallaron contra
`.enable_signaling = amdgpu_fence_enable_signaling`. Esa capacidad sigue `NOT_PROVEN` y no
debe inferirse de que la enumeración funcione.

| capacidad | estado |
|---|---|
| `semref` enumeración | `PROVEN` en el universo probado · 11/11 regresión |
| `semref` resolución de callbacks | `NOT_PROVEN` |
| `semref` exhaustividad absoluta | `NOT_DETERMINED` |

## 7. Regresiones registradas

Las dos primeras se encontraron al construir la herramienta; la tercera, durante el barrido
que motivó §5. Las tres tienen caso de test:

- **R-1** — el índice de `ctags` está ordenado por **nombre**; quedarse con «la última
  coincidencia» devolvía la función de nombre mayor, no la de mayor línea. Envolventes
  falsas. El benchmark calcula qué daría el algoritmo con el bug y lo contrasta.
- **R-2** — el control negativo emitía cadena vacía en vez de `SIN-MATCH`, y el benchmark
  no lo detectaba.

Una tercera, encontrada durante el barrido que motivó §5:

- **R-3** — el parser contaba como sitio de llamada **toda** línea eliminada del diff. En un
  `if/else` Coccinelle reemplaza la rama completa, así que `else` salía como llamada: **8
  falsos positivos** sobre el árbol real. El benchmark no lo detectaba porque el corpus
  sintético no tenía ningún `if/else` de dos ramas, y porque el contraste con `grep` solo se
  ejecutaba sobre los corpus congelados, nunca sobre el árbol real. Corregido exigiendo que
  la línea eliminada contenga la llamada esperada. La regresión congela la **salida cruda del
  motor** y comprueba que la regla rota da 6 y la corregida da 3, de modo que el test falla
  si se reintroduce el defecto: verificado, `rc=1` con el parser roto y `rc=0` con el
  corregido.

## 8. Estado

`P-8` deja de ser bloqueador epistemológico en la parte teardown. Lo que queda abierto
(`TMR` de la GPU, capacidad autónoma, y el caller de debugfs) no bloquea el diseño del
driver: son requisitos de implementación que dependen de lo ya tabulado, no de resolver
P-8.

**No aplicado**: ninguno de estos caminos está implementado en `07-DRIVER/`. No se ha
tocado ese árbol.

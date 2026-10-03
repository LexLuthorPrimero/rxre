# benchmark-001 — corpus congelado de `semref`

Regresión **determinista** de la herramienta. No depende del árbol del kernel ni
de su versión. Para investigación real, usar `semref` contra el árbol; este
directorio solo comprueba que la herramienta se comporta igual que antes.

## Por qué el corpus es sintético

El árbol de `drivers/gpu/drm/amd/amdgpu/` tiene ~400 ficheros y cambia entre
versiones de kernel. Congelar una copia real daría una regresión atada a una
versión concreta. `input/fence_corpus.c` es un fichero sintético que reproduce la
**topología** —quién llama a quién y cuántas veces— medida en el kernel, sin
contener código del kernel.

## Procedencia de cada topología

Todas medidas sobre `linux-7.1.3`, `drivers/gpu/drm/amd/amdgpu/`. El recuento
`grep` de la última columna es el contraste independiente, no la fuente.

| símbolo sintético | original | def | llamadas | suma | `grep` |
|---|---|---|---|---|---|
| `fence_process` | `amdgpu_fence_process` | 1 | 3 | 4 | 4 |
| `schedule_fallback` | `amdgpu_fence_schedule_fallback` | 1 | 2 | 3 | 3 |
| `fence_driver_force_completion` | `amdgpu_fence_driver_force_completion` | 1 | 1 | 2 | 2 |
| `mod_timer` | `mod_timer` | 0 | 1 | 1 | 1 |
| `dma_fence_signal` | `dma_fence_signal` | 0 | 4 | 4 | 4 |
| `<inexistente>` | — | 0 | 0 | `SIN-MATCH` | 0 |

## `input/drm_fence.h` existe por una razón concreta

`dma_fence_signal` se declara en ese header, no en el `.c`. En el kernel real
también es un prototipo externo. Motivo: `grep` cuenta apariciones textuales, y un
prototipo en el `.c` lo haría devolver 5 frente a las 4 llamadas reales, con lo
que el contraste `semref` vs `grep` dejaría de discriminar. La primera versión de
este corpus falló exactamente por eso.

## Regresiones cubiertas

**R-1 — índice alfabético frente a orden por línea.** El índice de `ctags` está
ordenado por *nombre*. `zzz_helper` se define en la línea 45, antes que
`fence_process` (50), pero se ordena *después* alfabéticamente. Un resolvedor que
se quede con "la última coincidencia del índice" devolvería `zzz_helper`; el
correcto es el de mayor línea ≤ L, `fence_process`. El runner calcula **qué
devolvería el algoritmo con el bug** y lo compara con la respuesta de `semref`,
así que el caso prueba que discrimina en vez de asumirlo.

**R-2 — forma de la salida de control negativo.** El caso inexistente debe emitir
`SIN-MATCH :: <símbolo>`, no una línea `TOTAL` vacía. El bug original filtraba
`^TOTAL` y devolvía cadena vacía, que el benchmark no detectaba.

## Ejecutar

```bash
08-ARQUITECTURA/tools/semref/tests/run-bench
```

Si falta `ctags` o Coccinelle, el runner **no ejecuta y no aprueba**: imprime
`ENGINE-NOT-AVAILABLE`, resultado `NOT_RUN`, exit 3. No degrada en silencio.

## Límite del contraste con `grep`

`grep` es independiente pero **no semántico**: no distingue definición de llamada.
Detecta que falte una llamada; no detecta una clasificación invertida que conserve
la suma. El reparto `definicion=` / `llamadas=` lo fija la línea `TOTAL` completa
de `expected/refs.txt`, y **la procedencia de ese valor congelado es la medición
manual sobre el kernel, no un segundo motor**. Ese es el eslabón más débil de la
cadena y no debe presentarse como más fuerte de lo que es.

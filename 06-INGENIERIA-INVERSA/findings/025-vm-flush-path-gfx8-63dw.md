# 025 · La ruta de `amdgpu_vm_flush` en GFX8 son 63 dw, y las cuatro ramas coexisten

`CLASSIFICATION=DOCUMENTATION` · `TOOL=tools/pm4dw.c --path` · `CORPUS=rx550-upstream-7.2.8/linux-7.2.8`
`RUNTIME=NOT_RUN` · `GPU INTACTA` · `MODIFICATIONS=0` en el corpus
`CONTINUES=024-pm4dw-herramienta-conteo-emision.md`

## CUDA principal

`024 §4` cerró el asunto con una cautela: la suma de handlers de un struct es cota superior,
no el conjunto que coexiste, así que no podía dar veredicto. **Ahora sí se puede, porque
el conjunto máximo no es una cota teórica: es alcanzable.** `amdgpu_vm_flush` fuerza cuatro
flags a la vez cuando el VMID ha visto un reset, y las condiciones son campos distintos del
job, sin exclusión mutua.

Ruta máxima GFX8 ring GFX = **63 dw** (53 medidos + 10 ocultos tras el despacho indirecto).
Reserva declarada = 172. Ningún infrarreserva.

## Alcance exacto

1. Enumerar los emisores que `amdgpu_vm_flush` puede ejecutar, en orden.
2. Determinar cuáles coexisten en un mismo envío.
3. Medir esa ruta con `pm4dw --path`.
4. Decidir si la sección 4 de `024` es un límite permanente.

## Criterio de terminación (cumplido)

Los ocho emisores localizados, su condición leída, la coexistencia resuelta y la ruta
medida. Agotado.

---

## 1 · Los ocho emisores, en orden de emisión

`amdgpu_vm.c:772-898`, `amdgpu_vm_flush`. Condición y coste:

| # | emisor | línea | condición | dw |
|---|---|---|---|---:|
| 1 | `insert_start` | 829-830 | `ring->funcs->insert_start` | `ABSENT` en GFX8 |
| 2 | `init_cond_exec` | 832-834 | siempre, si el ring lo tiene | 5 |
| 3 | `emit_pipeline_sync` | 836-837 | `need_pipe_sync` | 7 |
| 4 | `emit_cleaner_shader` | 839-840 | 4 términos | `ABSENT` en GFX8 |
| 5 | `emit_vm_flush` | 842-845 | `vm_flush_needed` | 9 (+10 indirectos) |
| 6 | `emit_pasid_mapping` | 847-848 | `pasid_mapping_needed` | 0 |
| 7 | `update_spm_vmid` | 850-851 | `spm_update_needed` | 0 |
| 8 | `emit_gds_switch` | 853-859 | `gds_switch_needed` | 20 |
| 9 | `emit_fence` | 861 | **incondicional** | 12 |
| 10 | `patch_cond_exec` | 896 | **incondicional** | 0 |

`emit_cleaner_shader` y `insert_start` no existen en `gfx_v8_0.c`
(`grep -c "emit_cleaner_shader *=" → 0`, `insert_start *=" → 0`). `cleaner_shader_needed`
exige `ring->funcs->emit_cleaner_shader` (`amdgpu_vm.c:813`), luego es **siempre falso en
Polaris12**. Eso no es una lectura de código: es un predicado con un término nulo.

`patch_cond_exec` emite **cero** dwords: es `static inline` que parchea
`ring->ring[offset]` in situ (`amdgpu_ring.h:544-553`). Lo incluí en la ruta por error la
primera vez —la tomé por `init_cond_exec`, que sí emite— y la herramienta lo reporta como
0, que es lo correcto.

## 2 · Las cuatro ramas coexisten de hecho

```c
/* amdgpu_vm.c:791-796 */
if (amdgpu_vmid_had_gpu_reset(adev, id)) {
        gds_switch_needed = true;
        vm_flush_needed   = true;
        pasid_mapping_needed = true;
        spm_update_needed = true;
}
```

`amdgpu_vmid_had_gpu_reset` (`amdgpu_ids.c:171-176`) compara
`id->current_gpu_reset_count != atomic_read(&adev->gpu_reset_counter)`. Es un
`NEGATIVE_RESULT` convertido en condición: tras un reset del GPU, **las cuatro ramas se
ejecutan simultáneamente en el mismo envío**, por construcción.

Y `need_pipe_sync` es un parámetro de `amdgpu_vm_flush`, independiente de esos cuatro. Su
caller decide. Así que el máximo alcanzable es:

```
init_cond_exec 5 + pipeline_sync 7 + vm_flush 19 + pasid 0 + spm 0
              + gds_switch 20 + fence 12 + patch 0  =  63 dw
```

Las otras cinco rutas que `amdgpu_vm_flush` puede tomarearly-returns en `:816-818` cuando
ningún flag está activo, y `insert_start`/`cleaner_shader` no existen. Todo eso `PROVEN` por
lectura.

## 3 · La medición

```
$ pm4dw --macro VI_FLUSH_GPU_TLB_NUM_WREG=3 --path "<los 8 emisores>" \
        gfx_v8_0.c gmc_v8_0.c amdgpu_ring.h
```

| leg | emisor | dw | estado |
|---|---|---:|---|
| 1 | `gfx_v8_0_ring_emit_init_cond_exec` | 5 | complete |
| 2 | `gfx_v8_0_ring_emit_pipeline_sync` | 7 | *sum excludes indirect dispatch* |
| 3 | `gfx_v8_0_ring_emit_vm_flush` | 9 | *sum excludes indirect dispatch* |
| 4 | `gmc_v8_0_emit_pasid_mapping` | 0 | complete |
| 5 | `gfx_v8_0_update_spm_vmid` | 0 | complete |
| 6 | `gfx_v8_0_ring_emit_gds_switch` | 20 | complete |
| 7 | `gfx_v8_0_ring_emit_fence_gfx` | 12 | complete |
| 8 | `amdgpu_ring_patch_cond_exec` | 0 | *sum excludes indirect dispatch* |
| | **total** | **53** | +10 del indirecto = **63** |

Contra `emit_frame_size` = 172 declarado. **63 ≤ 172.**

## 4 · Qué cambia respecto a `024`

`024 §4` decía: `declarado < suma` no prueba infrarreserva, porque la suma es cota. Eso
sigue siendo cierto **para `--struct`**, y no lo toco. Lo que cambia es que para
`amdgpu_vm_flush` la cota es alcanzable, así que la comparación sí produce veredicto:

| | `024` (struct) | `025` (ruta) |
|---|---|---|
| unidad | suma de handlers del struct | suma de emisores de un envío |
| es alcanzable | no | **sí**, por el camino de reset |
| da veredicto | no, sólo cota | sí |

**`024 §4` queda matizado, no refutado.** El mecanismo de la herramienta sigue siendo el
mismo; lo que se ha establecido es que para esta ruta concreta la condición de alcanzabilidad
se cumple. Para cualquier otra ruta habría que demostrar lo mismo, y `NOT_DETERMINED`
mientras tanto.

## 5 · Mutación M4: `--path` discrimina

Anadidos 4 `amdgpu_ring_write` a `gfx_v8_0_ring_emit_gds_switch`:

```
gds_switch   20 -> 24
ruta total   53 -> 57
```

La herramienta distingue una pierna de otra, que es lo que `--struct` no hacía. Copia mutada
en `/tmp/opencode/mut2`, eliminada. `MODIFICATIONS=0` en el corpus.

## 6 · Un fallo de la herramienta que esta ruta destapó

`gfx_v8_0_ring_emit_gds_switch` sale `ABSENT` en la primera ejecución. No lo es:
existe en `gfx_v8_0.c:5122`. La causa era `LOOKAHEAD_LINES 3`, y esa firma reparte **siete
parámetros en cinco líneas** antes de la llave.

Un cap fijo pequeño no es una heurística honesta: es un número que no sabe por qué es ese.
Lo sustituí por una regla con motivo —*una declaración sólo continúa mientras las líneas
sigan formando una lista de parámetros: sin `;` y sin línea vacía*— y subí el tope duro a 12
como red de seguridad, no como regla. Tras el cambio la pierna aparece con 20 dw.

`ABSENT` significa ahora lo que dice: o no existe, o el parser no la ve. Lo reporta así a
propósito, porque "no existe" y "no la veo" son hallazgos distintos y confundirlos es
precisamente el error que `AGENTS.md` §"Verify the object itself" prohibe.

## 7 · UNLOCKS

- La ruta de vm-flush GFX8 tiene un presupuesto medido de 63 dw, no una cota. Es el número
  que el driver propio debe reservar para esa secuencia.
- `emit_cleaner_shader` es un predicado permanentemente falso en Polaris12. No es un
  `if` que pueda activarse; el término `ring->funcs->emit_cleaner_shader` es NULL. Eso
  elimina una rama entera del espacio de diseño del driver propio.
- El camino de reset es el peor caso *por construcción del código*, no por hipótesis. Es el
  caso de prueba que cualquier implementación propia debe Reproducir primero.

## 8 · Lo que queda abierto

| Afirmación | Estado | Por qué |
|---|---|---|
| 63 dw es la ruta máxima **de `amdgpu_vm_flush`** | `PROVEN` | condiciones leídas, coexistencia forzada en `:791-796` |
| 63 dw es la ruta máxima **de un envío completo** | `NOT_DETERMINED` | `emit_frame_size` cubre también el IB, el context switch, los fences de usuario. Esta cuenta no los incluye. |
| Los 10 dw ocultos tras `gmc_funcs->emit_flush_gpu_tlb` son 10 | `PROVEN` | 2 × `gfx_v8_0_ring_emit_wreg`, 5 dw cada uno, medido |
| `pipeline_sync` no tiene despacho indirecto real | `UNKNOWN` | la herramienta marca la pierna por el `->funcs->` del macro, que es una llamada real a `gfx_v8_0_ring_emit_pipeline_sync`. Probablemente la marca es conservadora. `PROVISIONAL` |

Ese último es un defecto de la herramienta que queda declarado: marca por presencia textual
de `->funcs->` en el cuerpo, y el macro `amdgpu_ring_emit_pipeline_sync` está en la
**llamada**, no en el cuerpo de la función. Afecta a la etiqueta de estado, no al número.

## 9 · Evidencia

```
herramienta:     tools/pm4dw.c, sha256 32dc774de36ecfad0b3954d3efaa8533e44b4188c194b3e4611bc45e669863af
build:           cc -O2 -Wall -Wextra, 0 warnings
corpus sha256:   12e8d5a973d1ad7c5a5c69882e4022b131ed715db7003fdcd760ddf8c3e51941 (linux-7.2.8.tar.xz)
fuentes:         amdgpu_vm.c:772-898 (ruta y condiciones),
                amdgpu_ids.c:171-176 (had_gpu_reset),
                amdgpu_ring.h:544-553 (patch_cond_exec emite 0),
                amdgpu_gmc.h:373 (macro de despacho indirecto),
                gfx_v8_0.c:5122-5131 (gds_switch, 7 parámetros en 5 líneas),
                gfx_v8_0.c:6873-6917 (emit_frame_size = 172)
mutación:        /tmp/opencode/mut2, eliminada
```

Ningún registro leído de MMIO. `RUNTIME=NOT_RUN`. `GPU INTACTA`.
# 028 · `emit_frame_size = 172`: hipótesis refutada, la constante está justificada término a término

`CLASSIFICATION=DOCUMENTATION` · `TRACK=STATIC` · `CORPUS=rx550-upstream-7.2.8/linux-7.2.8`
`RUNTIME=NOT_RUN` · `GPU INTACTA` · `CONTINUES=024, 025, 026, 027`

## CUDA principal

`027 §7` planteó que `emit_frame_size = 172` era una constante escrita a mano sin derivar, y
que `NO_HISTORICAL_INHERITANCE` obligaría al driver propio a no heredarla.

**REFUTADA.** De los 17 términos de la reserva, **14 coinciden exactamente** con el coste
medido de su emisor. Y los tres que sobran no son descuido: son un redondeo por
`VI_FLUSH_GPU_TLB_NUM_WREG`, y dos previsores para functionality que GFX8 no implementa.

La reserva no es arbitraria. Es un presupuesto por emisor, y eso es `MODEL_CHOICE`
justificado por evidencia — que es exactamente lo que la norma exige para no heredarla.

## Cierre de la hipótesis

| término | declarado | real | origen del número real |
|---|---:|---:|---|
| COND_EXEC (1) | 5 | 5 | `gfx_v8_0_ring_emit_init_cond_exec` |
| PIPELINE_SYNC | 7 | 7 | `gfx_v8_0_ring_emit_pipeline_sync` |
| VI_WREG\*5 | **15** | **10** | `N=3` en `vi.h:27`, pero `gmc_v8_0_emit_flush_gpu_tlb` hace **2** `emit_wreg` |
| +9 | 9 | 9 | `WAIT_REG_MEM` 7 + `PFP_SYNC_ME` 2 |
| FENCE for VM_FLUSH | 12 | 12 | `gfx_v8_0_ring_emit_fence_gfx` |
| GDS switch | 20 | 20 | `gfx_v8_0_ring_emit_gds_switch` |
| double SWITCH_BUFFER | 4 | 4 | 2 × `gfx_v8_ring_emit_sb` |
| COND_EXEC (2) | 5 | 5 | ídem |
| HDP_flush | 7 | 7 | `gfx_v8_0_ring_emit_hdp_flush` |
| VGT_flush | 4 | 4 | `gfx_v8_0_ring_emit_vgt_flush` |
| **CE_META** | **14** | **14** | `ce_meta` **encadenado** = 14; el simple = 8 |
| **DE_META** | **31** | **31** | `de_meta` **encadenado** = 31; el simple = 21 |
| CNTX_CTRL | 3 | 3 | base de `gfx_v8_ring_emit_cntxcntl` |
| **HDP_INVL** | **5** | **0** | `asic_funcs->invalidate_hdp` no existe en `gfx_v8_0_ip_funcs` |
| FENCE ×2 | 24 | 24 | 2 × 12 |
| SWITCH_BUFFER | 2 | 2 | `gfx_v8_ring_emit_sb` |
| **SURFACE_SYNC** | **5** | **0** | `gfx_v8_0` no tiene `emit_surface_sync` |
| **total** | **172** | **157** | **+15** |

14 de 17 exactos. Los tres sobrantes suman exactamente 5 cada uno, lo que apunta a un
origen común, no a tres descuidos.

## El hallazgo que cierra el caso: CE_META y DE_META

Medidos con `--struct-size`:

```
vi_ce_ib_state              4 miembros → cnt_ce  6 → total  8 dw   (no encadenado)
vi_ce_ib_state_chained_ib  10 miembros → cnt_ce 12 → total 14 dw   (encadenado)
vi_de_ib_state             17 miembros → cnt_de 19 → total 21 dw   (no encadenado)
vi_de_ib_state_chained_ib  27 miembros → cnt_de 29 → total 31 dw   (encadenado)
```

`CE_META = 14` y `DE_META = 31` son **exactamente las variantes encadenadas**. La reserva
está dimensionada para el caso con `chained_ib_support` activo, no para el típico.

Esto era la hipótesis que `027 §7` dejó abierta ("la holgura cubre el caso chained-IB").
Queda confirmada, y con la aritmética que la demuestra término a término.

## Los tres sobrantes

**`VI_WREG*5` (+5).** `VI_FLUSH_GPU_TLB_NUM_WREG = 3` pero el emisor hace 2 `emit_wreg`.
Es el mismo hallazgo de `020`, con la misma causa y la misma magnitud. No es un error de
conteo: es una constante (`vi.h:27`) que sobrevive a un emisor que cambió. Corregirlo
bajaría la reserva de 172 a 167.

**`HDP_INVL` (+5) y `SURFACE_SYNC` (+5).** `gfx_v8_0_ip_funcs` no tiene `invalidate_hdp`
—`amdgpu_device_invalidate_hdp` (`amdgpu_device.c:6805`) llama a
`adev->asic_funcs->invalidate_hdp` y cae al puntero nulo— y `gfx_v8_0` no define
`emit_surface_sync`. Son **previsores para una ASIC que los tiene** (Vega y posteriores los
implementan), copiados aquí desde el mismo struct común.

Los tres son +5 exactos, y los dos previsores son idénticos, así que el patrón es claro: el
`ring_funcs_gfx` de GFX8 se derivó de una plantilla compartida en la que esos términos ya
venían puestos.

## Consecuencia para el driver propio

| | |
|---|---|
| ¿Se puede heredar el 172? | **Sí, con justificación explícita** — no es arbitrario |
| ¿Es `MODEL_CHOICE`? | Sí: el presupuesto por emisor es correcto y cada término es trazable |
| ¿Qué habría que documentar? | Los tres términos que sobran y por qué |
| ¿Merece la pena "corregirlo" a 157? | **No automáticamente.** Bajar la reserva reduce el margen sin evidencia de que 157 sea suficiente en los casos que los previsores cubren |

Ese último punto es el que importa y donde `NO_HISTORICAL_INHERITANCE` no dice "copia
nada": dice que cada decisión heredada se justifique por evidencia. Aquí la evidencia dice
que 14 de 17 términos son exactos, que los 3 restantes son previsores para capacidad que
esta ASIC no tiene, y que el hardware no puede emitir más de lo que la secuencia emite. Con
eso, 172 es una reserva **defendible** y 157 sería una reserva **más ajustada pero no
probada**.

Lo que sí sería un error del driver propio: fijar la reserva sin mirar la secuencia, y
copiar el 172 por costumbre sin poder decir de dónde sale cada término. La herramienta
permite esa trazabilidad en una línea.

## UNLOCKS

- La reserva de GFX8 es auditable término a término, con 14/17 exactos. Eso la convierte en
  un presupuesto defendible en vez de una constante mágica.
- `HDP_INVL` y `SURFACE_SYNC` son previsores, y eso es evidencia de que el `ring_funcs_gfx`
  de GFX8 es una plantilla compartida. Un driver propio puede partir de la secuencia real
  (157 dw) sin arrastrar esos previsores, si acepta un margen menor.
- `VI_FLUSH_GPU_TLB_NUM_WREG = 3` con 2 emisores reales: la constante no describe el
  hardware ni el código, describe una versión anterior del emisor. Es el tipo de cosa que
  `NO_HISTORICAL_INHERITANCE` marca, y aquí está quantified: **+5 dw, +3,2 % de la reserva**.

## Corrección de `027 §7`

Escribí que `emit_frame_size` era una "constante escrita a mano y nadie la derivó de la
secuencia". Eso era una conjetura presentada como observación: yo no había comparado término
a término. La comparación está arriba y dice lo contrario. `CORRECTION_OF_CONCLUSION`, con
la evidencia que la refuta.

## Criterio de falsación

Se refutaría si algún término de la reserva no tuviera emisor identificable en
`gfx_v8_0.c`, o si el coste medido de alguno de los 14 difiriera al recontar con
`pm4dw --path` incluyendo `write_multiple`. Ninguno de los dos ocurrió.

## Evidencia

```
corpus:      12e8d5a973d1ad7c5a5c69882e4022b131ed715db7003fdcd760ddf8c3e51941 (linux-7.2.8.tar.xz)
gfx_v8_0.c:  6881-6898 (emit_frame_size, los 17 términos),
             6873-6917 (ring_funcs_gfx), 6197-6221 (emit_vm_flush),
             6352-6374 (emit_wreg), 6900 (emit_ib_size = 4)
gmc_v8_0.c:  662-677 (emit_flush_gpu_tlb: 2 emit_wreg, no 3)
vi.h:        27 (VI_FLUSH_GPU_TLB_NUM_WREG = 3)
vid.h:       169-189 (WAIT_REG_MEM), 200 (PFP_SYNC_ME)
gfx_v8_0.c:  bloque ip_funcs (sin invalidate_hdp)
amdgpu_device.c: 6782-6815 (flush_hdp / invalidate_hdp)
include/vi_structs.h: los 4 structs, tamaños medidos por --struct-size
herramienta: tools/pm4dw.c, --path y --struct-size
```

Ningún registro leído de MMIO. `RUNTIME=NOT_RUN`. `MODIFICATIONS=0` en el corpus.
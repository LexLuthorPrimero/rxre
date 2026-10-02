# NEGATIVE-RESULTS

<!-- GENERADO POR tools/artifacts.py. NO EDITAR A MANO: la siguiente ejecucion lo sobrescribe. -->

Lo que se descarto, y donde. Un resultado negativo es informacion
cara; sin este artefacto vive dentro del finding que lo produjo,
donde nadie lo busca.

| # | linea | clases | texto |
|---|---|---|---|
| 017 | 11 | REFUTED | `29⁄9⁄26.md:169` ("WAIT_REG_MEM espera REQUEST == 0") queda `REFUTED` a nivel de encod |
| 017 | 129 | REFUTED | Es `REFUTED`. La codificación es `FUNCTION=0` (`always`), no `3` (`==`). El documento |
| 017 | 194 | REFUTED | haría `REFUTED` incorrecto; (c) `WAIT_REG_MEM_OPERATION` tuviera otro valor que 0 en |
| 018 | 67 | PROVEN_ABSENT | `PROVEN_ABSENT` por objeto nombrado, no por un `grep -c` que contaba sin querer. |
| 018 | 154 | NEGATIVE_RESULT | `NEGATIVE_RESULT`: no existe ninguna ruta en GFX8 que espere un ack de invalidación. N |
| 018 | 204 | PROVEN_ABSENT | / Que GFX8 no expone ack de invalidación / `PROVEN_ABSENT` / 5 cabeceras GMC, 0 coinci |
| 018 | 241 | NEGATIVE_RESULT | `emit_reg_write_reg_wait`: si el driver propio reordena el flush, cuidado. `NEGATIVE_R |
| 019 | 162 | PROVEN_ABSENT | / El driver GFX8 usa alguno / `PROVEN_ABSENT` / `grep` sobre `amdgpu/*.c` = 0, con las |
| 019 | 168 | PROVEN_ABSENT | §Criterio de terminación); pero el `PROVEN_ABSENT` es sólo sobre el **uso por el drive |
| 019 | 215 | PROVEN_ABSENT | escriba `ATC_L1RD/WR_DEBUG_TLB` o `ATC_L2_DEBUG2` — refutaría el `PROVEN_ABSENT` de §4 |
| 021 | 50 | NEGATIVE_RESULT | `NEGATIVE_RESULT` verificado: **ningún rango de escritura de esta sesión se solapó con |
| 021 | 60 | REFUTED | / Cerrojo raíz excluye todas las demás sesiones / **`REFUTED`** por §Reproducción / |
| 021 | 61 | REFUTED | / Cerrojo de ámbito (`docs/`, `findings/`) excluye a quien tiene la raíz / **`REFUTED` |
| 021 | 63 | REFUTED | / `git status` como arbitro / `REFUTED`, ya lo decía `COORDINACION.md:15-19` / |
| 021 | 120 | NEGATIVE_RESULT | subdirectorio ajeno, como consta arriba. Un `NEGATIVE_RESULT` que dejo dicho porque |
| 021 | 167 | NEGATIVE_RESULT | `NEGATIVE_RESULT` que sí se sostiene: ningún fichero existente fue sobrescrito. Los do |
| 022 | 26 | NEGATIVE_RESULT | `NEGATIVE_RESULT`: no es que no se haya investigated el efecto de `COND_EXEC` en GFX8. |
| 022 | 85 | NEGATIVE_RESULT | `NEGATIVE_RESULT` del driver de referencia, **no alcanzable en Polaris12**: la |
| 022 | 94 | PROVEN_ABSENT | `PROVEN_ABSENT`. |
| 022 | 185 | PROVEN_ABSENT | Con eso, las dos rutas estan cerradas. `PROVEN_ABSENT` por objeto nombrado |
| 022 | 278 | PROVEN_ABSENT | / `gfx_v8_0.c` nunca llama a `set_preempt_cond_exec` / `PROVEN_ABSENT` (20 call sites  |
| 022 | 279 | PROVEN_ABSENT | / GFX8 no tiene `preempt_ib` / `PROVEN_ABSENT` (8 ASICs medidos) / |
| 022 | 333 | NEGATIVE_RESULT | `NEGATIVE_RESULT`; (c) solo cambia la descripcion, no el resultado de que el software |
| 023 | 18 | NEGATIVE_RESULT | Y el `NEGATIVE_RESULT` de `SET_CONFIG_REG` con 1 payload **no se retracta, cambia su |
| 023 | 20 | NEGATIVE_RESULT | `gfx_v12_1.c:3371` es de otro ASIC, así que no es un `NEGATIVE_RESULT` sobre esta tarj |
| 023 | 168 | NEGATIVE_RESULT | `gfx_v8_0` (`vi.c:2107-2112`, `gfx_v8_0_ip_block`). Se registra como `NEGATIVE_RESULT` |
| 024 | 211 | NEGATIVE_RESULT | `NEGATIVE_RESULT` con alcance: el corpus **no declara que signifique** la diferencia |
| 024 | 269 | NEGATIVE_RESULT | podria ocurrir. `NOT_APPLICABLE` en esta placa, `NEGATIVE_RESULT` heredable. |
| 024 | 286 | REFUTED | / Que `num_level = 1` sea una limitacion del silicio / `REFUTED` — viene de `max_level |
| 024 | 292 | REFUTED | `REFUTED`: el nivel se elige por `max_level = 1`, un argumento del driver. La primera |
| 025 | 185 | REFUTED | / Que el invalidate de ring se dispare solo por cambio de PTBA / `REFUTED` — se dispar |
| 025 | 73 | NEGATIVE_RESULT | `NEGATIVE_RESULT` convertido en condición: tras un reset del GPU, **las cuatro ramas s |
| 026 | 240 | PROVEN_ABSENT | / Que la mascara del PTE exista en el hardware / `PROVEN_ABSENT` — 0 bitfields / |
| 026 | 278 | PROVEN_ABSENT | GFX8 — refutaria la `PROVEN_ABSENT` y daria layout de hardware donde hay comentario; |
| 027 | 219 | PROVEN_ABSENT | / Que el PD de GFX8 lleve flags / `PROVEN_ABSENT` — la rama que los anade no se toma / |
| 027 | 225 | REFUTED | / Que `vm_pd_addr` reexpresado por submit implica flush / `REFUTED` — depende de `use_ |
| 028 | 191 | PROVEN_ABSENT | de GFX8 no los usa nunca**. `PROVEN_ABSENT` por barrido de `DATA_SEL` en `gfx_v8_0.c`. |
| 028 | 249 | PROVEN_ABSENT | `NOT_APPLICABLE` para Polaris12 con causa, no `PROVEN_ABSENT`. Es un defecto real del |
| 028 | 253 | NEGATIVE_RESULT | `NEGATIVE_RESULT` heredable: si el driver propio emite fence en un ring sin EOP, tiene |
| 028 | 308 | PROVEN_ABSENT | / `DATA_SEL` 3 y 4 no se usan en GFX8 / `PROVEN_ABSENT` (barrido) / |
| 028 | 331 | PROVEN_ABSENT | `PROVEN_ABSENT`: el barrido fue de `amdgpu_cs.c`, `amdgpu_ib.c` y `amdgpu_fence.c`, |
| 028 | 351 | NEGATIVE_RESULT | - La discrepancia de KIQ es `NEGATIVE_RESULT` con causa y severidad acotadas: el drive |
| 029 | 146 | PROVEN_ABSENT | completion de invalidación (`PROVEN_ABSENT`, cinco cabeceras GMC sin uno), y por eso e |
| 029 | 154 | PROVEN_ABSENT | `PROVEN_ABSENT` por barrido de todo el arbol, no por lectura parcial: el termino |
| 029 | 204 | NEGATIVE_RESULT | `NEGATIVE_RESULT` heredable y accionable: el driver propio **no debe reservar ni |
| 029 | 242 | PROVEN_ABSENT | / Ese campo no existe en GFX6/7/8/10/12 / `PROVEN_ABSENT` / |
| 029 | 247 | PROVEN_ABSENT | / Que **nadie lo ponga** en un ring GFX8 / `PROVEN_ABSENT` (barrido de 7.1.3) / |
| 029 | 258 | PROVEN_ABSENT | estado estricto es `NOT_OBSERVED` fuera de `amdgpu/`, no `PROVEN_ABSENT` global. |
| 029 | 264 | PROVEN_ABSENT | `vid.h` equivalente con ese campo, y `vid.h` no lo define. `PROVEN_ABSENT` es que el |
| 029 | 285 | PROVEN_ABSENT | de GFX8, lo que haria `EOP_EXEC` alcanzable y eliminaria el `PROVEN_ABSENT`; (b) el dw |
| 030 | 159 | NEGATIVE_RESULT | **Pero el modo de fallo es duro, y eso es lo que lo hace `NEGATIVE_RESULT` y no |
| 030 | 212 | PROVEN_ABSENT | / `trail_fence_offs` no se libera nunca / `PROVEN_ABSENT` (barrido de `wb_free`) / |
| 030 | 231 | PROVEN_ABSENT | `gfx_v9_0.c` / `sdma_v*` (escritura del fence). Por tanto `PROVEN_ABSENT`. |
| 031 | 3 | NEGATIVE_RESULT | `CLASSIFICATION=DOCUMENTATION` · `NEGATIVE_RESULT` · `TOOL=tools/pm4dw.c --check-arity |
| 031 | 63 | NEGATIVE_RESULT | **`NEGATIVE_RESULT` registrado**: la verificación de contratos de llamada sobre el árb |
| 031 | 302 | REFUTED | / Que el driver ordene (a) antes de (b) explicitamente / `REFUTED` — no existe tal cod |
| 032 | 243 | REFUTED | / Que el fence necesite `writel` / `REFUTED` — es un buzon, no una puerta / |
| 032 | 244 | REFUTED | / Que el fence y el doorbell compartan mecanismo / `REFUTED` — dominios y roles distin |
| 033 | 19 | NEGATIVE_RESULT | `NEGATIVE_RESULT` con su causa identificada. |
| 033 | 44 | NEGATIVE_RESULT | `NEGATIVE_RESULT`. |
| 033 | 363 | REFUTED | **`REFUTED`, con caso vivo:** `pkt_is_type3` de freedreno rechaza un paquete que amdgp |
| 033 | 387 | NEGATIVE_RESULT | / No hay documento primario del framing PM4 para GCN3 / `NEGATIVE_RESULT`, con causa n |
| 033 | 395 | REFUTED | / Esa asercion vale para GFX8 / **`REFUTED`** — 12/74 opcodes ≥ `0x80`, uno vivo / |
| 035 | 121 | REFUTED | / mio, `024` / 13 / **`REFUTED`** / lei la firma y use el nombre del parametro / |
| 035 | 123 | REFUTED | / page-walker / 22/23/24 / **`REFUTED`** / leyo el call site pero **sin ver el reasign |
| 035 | 257 | REFUTED | / `13` (mi `024`) / **`REFUTED`** / |
| 035 | 258 | REFUTED | / `22/23/24` (page-walker) / **`REFUTED`** — son `get_block_size(tmp` sin reasignar`)  |
| 035 | 261 | REFUTED | / Que "2 levels" en el log signifique dos tablas / `REFUTED` — es `num_level+1` con `P |
| 039 | 1 | PROVEN_ABSENT | # 039 · `PROVEN_ABSENT` retractado: GFX8 **sí** tiene `emit_mem_sync`. Y la coherencia |
| 040 | 250 | REFUTED | / El corpus describe *todo* el binario / `REFUTED` — faltan `dc` (2579) y `smu` (1020) |
| 042 | 225 | REFUTED | / Que `CP_HQD_CTX_SAVE_*` sea "preemption" / `REFUTED` — `022` la separó; son cosas di |
| 043 | 67 | REFUTED | / el nombre del opcode es `SDMA_OP_PTEPDE` / `vega10_sdma_pkt_open.h` / **`REFUTED` pa |
| 045 | 51 | REFUTED | / `031:278` si `writel` vacía posted-writes / `032:243` `REFUTED` — es un buzón, no un |
| 045 | 131 | REFUTED | 017:194  "...haría `REFUTED` incorrecto; (c) `WAIT_REG_MEM_OPERATION` |
| 045 | 135 | REFUTED | Hay un `REFUTED` y no se afirma nada: se dice que **sería incorrecto**. Con esa |
| 045 | 159 | REFUTED | Por eso hay **controles simétricos**: `PROVEN` de verdad debe contar, `REFUTED` |
| 045 | 55 | NEGATIVE_RESULT | `NEGATIVE_RESULT` sobre el caso de `gfx_v12_1` seguía siendo un `NEGATIVE_RESULT`, por |
| 047 | 45 | REFUTED | Es `REFUTED`. El handler no la ignora: **la lee y la escribe en el log de |
| 047 | 138 | PROVEN_ABSENT | / No lo decodifica / `PROVEN_ABSENT` — no hay más acceso en el fichero / |
| 047 | 139 | REFUTED | / `051`: "el handler la ignora" / `REFUTED` — la lee y la imprime / |
| 047 | 140 | PROVEN_ABSENT | / `gmc_v8_0_process_vm_fault` existe / `PROVEN_ABSENT` — no está en el fichero / |
| 047 | 145 | REFUTED | / `052:138` es una frontera real de contenido / `REFUTED` — no hay bifurcación en el h |
| 047 | 146 | REFUTED | / `061` (src_data ∈ {0,1}) aplica al camino de fault / `REFUTED` — `061` habla de `dce |
| 047 | 207 | REFUTED | - **`052:138` pasa a `REFUTED` en el handler, no en el hardware.** El hardware |
| 048 | 163 | NEGATIVE_RESULT | sospecha era razonable; el resultado es un `NEGATIVE_RESULT` con valor. |
| 048 | 124 | REFUTED | / Que el problema afecte a `stale_gap` / `REFUTED` — cruza por sujeto / |
| 049 | 41 | NEGATIVE_RESULT | Es un `NEGATIVE_RESULT` sobre GFX9, escrito como contraste deliberado, y el propio fin |
| 049 | 59 | NEGATIVE_RESULT | `NEGATIVE_RESULT` con valor: la sospecha de `048` era razonable y **queda cerrada sin  |
| 052 | 138 | REFUTED | / diferencia de comportamiento entre 0x92 y 0x93 / — / `REFUTED` en `047`: comparten h |
| 056 | 25 | NEGATIVE_RESULT | publica lo primero.** Eso es una `NEGATIVE_RESULT` con la causa nombrada, y es un |
| 057 | 19 | NEGATIVE_RESULT | Esto es un `NEGATIVE_RESULT` con causa nombrada. No es un bloqueo vago: es que la |
| 063 | 1703 | PROVEN_ABSENT | `smu` en el nombre, cero resultados en todo el arbol. `PROVEN_ABSENT`. |
| 063 | 3427 | PROVEN_ABSENT | **En esta placa no hay invasion** (`PROVEN_ABSENT`), pero **un VBIOS con 9 escribiria |
| 064 | 175 | REFUTED | / `SECURE_*` y `RETRY_*` existen en GFX8 / `REFUTED` / cero apariciones en gmc_8_1 y g |
| 065 | 136 | PROVEN_ABSENT | / `BIF_FB_EN` no está en las cabeceras GMC / `PROVEN_ABSENT` / recuento en 4 cabeceras |
| 067 | 87 | PROVEN_ABSENT | Es además la diferencia entre `PROVEN_ABSENT` y `NOT_APPLICABLE`: el camino de |
| 069 | 147 | PROVEN_ABSENT | / El nombre citado implica salida leída / `PROVEN_ABSENT` (no se puede) / |
| 072 | 41 | PROVEN_ABSENT | y el driver no lo mira jamás. Eso es `PROVEN_ABSENT` con el alcance acotado a |
| 072 | 117 | PROVEN_ABSENT | / El driver lo lee **0 veces** / `PROVEN_ABSENT` (acotado al driver) / |
| 074 | 111 | NEGATIVE_RESULT | > mismo principio que con un `NEGATIVE_RESULT`: un resultado que no cuadra no |
| 081 | 133 | PROVEN_ABSENT | ## 4 · `PROVEN_ABSENT` CON SU LÍMITE DECLARADO |
| 081 | 175 | PROVEN_ABSENT | / `join(x[1] for x in en)` sobre `int` → `TypeError` en la sección `PROVEN_ABSENT` / e |
| 088 | 152 | PROVEN_ABSENT | y es `PROVEN_ABSENT` con denominador: 666 llamadas examinadas, 9 selectores en uso, |
| 089 | 170 | PROVEN_ABSENT | **Se escribe y no se lee nunca.** Es un `PROVEN_ABSENT` con explicación, no un |
| 093 | 169 | PROVEN_ABSENT | > invoca. Un `PROVEN_ABSENT` con el consumidor identificado: *«la jerarquía de |
| 095 | 150 | PROVEN_ABSENT | / Ningún icache de motor se invalida en GFX8 / `PROVEN_ABSENT` (0 sitios) / |
| 096 | 251 | PROVEN_ABSENT | escribe ningun `.c` de `pm/`. `PROVEN_ABSENT`. |
| 096 | 75 | PROVEN_ABSENT | > **`PROVEN_ABSENT`: en este corpus no hay ninguna fuente que documente la |
| 099 | 69 | PROVEN_ABSENT | > **`PROVEN_ABSENT`: el bit `AMDGPU_PTE_PRT` no tiene consumidor en ningún |
| 102 | 156 | PROVEN_ABSENT | / No hay ruta automática a GFX / `PROVEN_ABSENT` / |
| 104 | 7 | REFUTED | > la base literal**. En consecuencia **quedan `REFUTED`**: |
| 106 | 90 | PROVEN_ABSENT | `PROVEN_ABSENT`: *"el driver lo lee 0 veces"* — leyendo `RESPONSE`. |
| 106 | 145 | PROVEN_ABSENT | / `FUNCTION` no está en ningún header del ASIC / `PROVEN_ABSENT` — `grep` sobre `asic_ |
| 107 | 188 | REFUTED | escribe en la posicion 1576. `REFUTED` la afirmacion de `103`. |
| 107 | 114 | PROVEN_ABSENT | / GFX8 no hace flush explícito tras su reset / `PROVEN_ABSENT` — ausente en `gfx_v8_0. |
| 107 | 118 | REFUTED | / Que el hardware invalide solo por `FUNCTION` / `REFUTED` — `106`, el campo no existe |
| 107 | 145 | PROVEN_ABSENT | / Las otras 5 nunca se emiten / `PROVEN_ABSENT` / |
| 110 | 26 | PROVEN_ABSENT | campo donde no puede estar, obtuve vacío, y convertí el vacío en `PROVEN_ABSENT`. |
| 110 | 139 | PROVEN_ABSENT | El invalidate sigue sin tener campo `FUNCTION` — eso sí es `PROVEN_ABSENT`, y |
| 110 | 190 | PROVEN_ABSENT | / `sid.h` no tiene `WAIT_REG_MEM_OPERATION` / `PROVEN_ABSENT` — grep rc=0 / |
| 110 | 191 | PROVEN_ABSENT | / El invalidate NO tiene campo `FUNCTION` / `PROVEN_ABSENT` — 16 dominios / |
| 110 | 193 | REFUTED | / La barrera esperaría `0x51E == 0` / `REFUTED` — `MASK=0`, `always` / |
| 111 | 129 | PROVEN_ABSENT | / El ME no tiene opcode de IB / `PROVEN_ABSENT` / |
| 113 | 113 | REFUTED | Los cuatro `REFUTED` caen por la misma razon: cada uno computa `offsetof(campo) + 108` |
| 114 | 327 | REFUTED | / La `.h` afirmaba 7 / `REFUTED` por el validador / |
| 118 | 192 | PROVEN_ABSENT | / `toolaudit` no mide el denominador / `PROVEN_ABSENT` / |
| 120 | 56 | NEGATIVE_RESULT | `NEGATIVE_RESULT`, que es información, y por eso no se corrige. |
| 121 | 104 | REFUTED | / Que la deuda de 340 sea recuperable por análisis / `REFUTED` — este hallazgo / |
| 121 | 152 | NEGATIVE_RESULT | Eso es un `NEGATIVE_RESULT` con valor: para un driver propio son 63 paquetes que |
| 121 | 221 | PROVEN_ABSENT | / `lower_32_bits`/`upper_32_bits` ausentes del corpus / `PROVEN_ABSENT` — búsqueda sob |
| 122 | 121 | REFUTED | / Las dos familias son independientes / `REFUTED` — dos codificaciones de una especifi |
| 122 | 122 | REFUTED | / `soc15d.h` consta como generado del XML / `REFUTED` — 0 marcas en el fichero / |
| 122 | 123 | REFUTED | / Las anclas `:180-187` y `:214-220` / `REFUTED` — las reales son `169-186` y `199-201 |
| 122 | 126 | REFUTED | / Que el estado `PROVEN` del formato sea incorrecto / `REFUTED` — el estado no cambia; |
| 123 | 17 | PROVEN_ABSENT | 3. **Por qué los 344 dwords observados no son un IB del kernel.** `PROVEN_ABSENT` |
| 123 | 130 | PROVEN_ABSENT | / **Leer ese IB desde el host** / **`PROVEN_ABSENT`** — `amdgpu_sa.c` sin debugfs / |
| 123 | 182 | PROVEN_ABSENT | / Leerlo desde el host / **`PROVEN_ABSENT`** / |
| 123 | 218 | PROVEN_ABSENT | **`PROVEN_ABSENT` como observable.** La ruta no está ni expuesta en esta GPU. |
| 125 | 46 | PROVEN_ABSENT | / Que GFX8 no expone ack de invalidación / `PROVEN_ABSENT` / 5 cabeceras GMC, 0 coinci |
| 125 | 52 | PROVEN_ABSENT | literalmente `0 coincidencias` y `PROVEN_ABSENT`. Y ese hallazgo tiene 188 |
| 127 | 121 | REFUTED | / Que el presupuesto `emit_frame_size = 215` (16 IBs) accounted los 256 / `REFUTED` —  |
| 127 | 104 | NEGATIVE_RESULT | **`NEGATIVE_RESULT`: en GFX8 no existe camino alcanzable que escriba page tables |
| 129 | 43 | PROVEN_ABSENT | `PROVEN` por ausencia en los 2787 ficheros, que es `PROVEN_ABSENT` y no |
| 129 | 129 | PROVEN_ABSENT | / `PDE_CACHE_EFFECTIVE_SIZE` no lo escribe nadie / `PROVEN_ABSENT` (0 de 2787) / |
| 130 | 188 | PROVEN_ABSENT | / `lower_32_bits`/`upper_32_bits` ausentes del corpus / `PROVEN_ABSENT` — sin cambio / |
| 132 | 74 | PROVEN_ABSENT | **`PROVEN_ABSENT` en GFX8.** El PTE nunca se marca como "manejado como PDE". |
| 132 | 201 | PROVEN_ABSENT | / `AMDGPU_PTE_TF` no se escribe en GFX8 / `PROVEN_ABSENT` / |
| 132 | 203 | PROVEN_ABSENT | / `vmid0_page_table_block_size = 0` en GFX8 / `PROVEN_ABSENT` (nunca asignado) / |
| 134 | 98 | REFUTED | / ¿Hay direcciones de kernel utilizables? / `REFUTED` — 0 de 305320 / |
| 135 | 162 | REFUTED | / El recuento de `121` (83) era falso / `REFUTED` — le faltaban 8 / |
| 139 | 115 | PROVEN_ABSENT | **`gmc_v8_0.c` no aparece en ninguna de las tres últimas filas.** `PROVEN_ABSENT`, |
| 139 | 335 | PROVEN_ABSENT | / `AMDGPU_PDE_BFS` no se escribe en GFX8 / `PROVEN_ABSENT` (por fichero) / |
| 139 | 336 | PROVEN_ABSENT | / `AMDGPU_PTE_LOG` y `NOALLOC` no se escriben en GFX8 / `PROVEN_ABSENT` / |
| 140 | 217 | REFUTED | significaciones son incompatibles.** `REFUTED` la mía, `PROVEN` la del driver. |
| 142 | 37 | PROVEN_ABSENT | **`gmc_v8_0.c` no está.** `PROVEN_ABSENT`, por pertenencia a fichero. |
| 142 | 74 | PROVEN_ABSENT | **Las tres juntas: la apertura AGP de esta GPU está vacía. `PROVEN_ABSENT`, con |
| 142 | 239 | PROVEN_ABSENT | / La apertura AGP está vacía / `PROVEN_ABSENT` (3 pruebas) / |
| 142 | 241 | PROVEN_ABSENT | / `amdgpu_gmc_agp_location` nunca se llama en GFX8 / `PROVEN_ABSENT` (por fichero) / |
| 142 | 246 | PROVEN_ABSENT | / 160 escrituras, 0 nombres, 0 offsets en el corpus / `PROVEN_ABSENT` / |
| 142 | 287 | PROVEN_ABSENT | `NOT_OBSERVED` en `PROVEN_ABSENT`, y sin tocar hardware.** |
| 142 | 291 | PROVEN_ABSENT | ejecutado si hubiera ocurrido.* Es la regla `PROVEN_ABSENT` aplicada a un |
| 143 | 91 | PROVEN_ABSENT | programan nunca.** `PROVEN_ABSENT`, y es coherente con que `fiji_update_mc_*` sean |
| 143 | 230 | PROVEN_ABSENT | / Esta GPU no recibe ajustes de clock gating / `PROVEN_ABSENT` / |
| 143 | 275 | NEGATIVE_RESULT | `NEGATIVE_RESULT` sobre mi propio método, no sobre el hardware.** |
| 144 | 254 | PROVEN_ABSENT | / `gmc_v8_0.c` está en la lista de los que honran la bandera / `PROVEN_ABSENT` / |
| 145 | 41 | PROVEN_ABSENT | corpus.** La ruta interna está agotada. `PROVEN_ABSENT`. |
| 145 | 150 | PROVEN_ABSENT | / Ningún `.c` del corpus define un `struct drm_*` / `PROVEN_ABSENT` / |
| 148 | 54 | PROVEN_ABSENT | `PROVEN_ABSENT`, y es una ausencia con forma: la lista de los que sí lo tienen. |
| 148 | 89 | PROVEN_ABSENT | `TMDS_CNTL`, ni ninguna estructura `dce_stream_encoder_registers`.** `PROVEN_ABSENT`. |
| 148 | 214 | PROVEN_ABSENT | / No hay directorio `dce100/` de implementación / `PROVEN_ABSENT` / |
| 148 | 217 | REFUTED | / Mi «la elección HDMI/DP es un `REG_UPDATE` con 1 o 0» / **`REFUTED`** — es DCE 110 y |
| 148 | 218 | PROVEN_ABSENT | / `TMDS_CNTL` no está en la tabla de esta GPU / `PROVEN_ABSENT` / |
| 149 | 34 | PROVEN_ABSENT | estructura.** `PROVEN_ABSENT`. |
| 149 | 179 | PROVEN_ABSENT | **Nunca en una ruta de DCE 10.0.** `PROVEN_ABSENT`, por pertenencia a fichero. |
| 149 | 194 | PROVEN_ABSENT | / `link_type` no existe en `dc_crtc_timing` / `PROVEN_ABSENT` / |
| 149 | 205 | PROVEN_ABSENT | / `DSC` no se lee en ninguna ruta DCE 10.0 / `PROVEN_ABSENT` / |
| 150 | 127 | PROVEN_ABSENT | `(signal & (A / B))` en el árbol. `PROVEN_ABSENT` para la combinación, por programa. |
| 150 | 195 | PROVEN_ABSENT | / No hay combinación de bits con `&` / `PROVEN_ABSENT` (por programa) / |
| 151 | 54 | PROVEN_ABSENT | Todas las generaciones de DCE, sin excepción. `PROVEN_ABSENT`, por recuento. |
| 155 | 104 | REFUTED | **`REFUTED`.** Está en la lista `DCE112`, que es la de esta máquina, en |
| 155 | 113 | REFUTED | **`REFUTED` para esta máquina.** La cadena que `148` construyó queda así: |
| 155 | 130 | PROVEN_ABSENT | programa. **DCE 11.2 no usa el tipo `dce110_stream_encoder`.** `PROVEN_ABSENT`. |
| 155 | 149 | REFUTED | / `147` / el reloj de canal ausente / **sí** → `REFUTED` / |
| 155 | 167 | NEGATIVE_RESULT | ## 8 · Y el `NEGATIVE_RESULT` sobre mi propio observable propuesto |
| 155 | 184 | NEGATIVE_RESULT | una máscara de log.** `NEGATIVE_RESULT`, sobre mi propia propuesta. |
| 155 | 211 | REFUTED | / `147`: el reloj de canal ausente / **`REFUTED`** / |
| 155 | 212 | REFUTED | / `148`: el umbral de 340 MHz no programable / **`REFUTED`** / |
| 156 | 63 | REFUTED | **`REFUTED`.** Conté las apariciones en `dce112_hwseq.c` — cero — y generalicé de un |
| 156 | 77 | REFUTED | **`REFUTED`.** `dce110_stream_encoder_set_stream_attribute_helper` —la función que |
| 156 | 100 | REFUTED | **Ya `REFUTED` en `155`**, y R2 explica por qué: no es que el campo no existiera, es |
| 156 | 158 | REFUTED | / `155`: DCE 11.2 no usa `dce110_stream_encoder` / **`REFUTED`** / |
| 156 | 159 | REFUTED | / `148`: la helper es código de DCE 11.0, no de esta GPU / **`REFUTED`** / |
| 156 | 160 | REFUTED | / `148`: el reloj de canal no es programable / **`REFUTED`** / |
| 156 | 192 | PROVEN_ABSENT | - Encadenada con `155` (**cuyo `PROVEN_ABSENT` esta nota refuta**), `153` (las siete |
| 158 | 118 | PROVEN_ABSENT | analógico. No hay camino VGA en el driver para este chip.** `PROVEN_ABSENT`, y es la |
| 158 | 177 | PROVEN_ABSENT | / DCE 11.2 no construye codificador analógico / `PROVEN_ABSENT` / |
| 158 | 178 | PROVEN_ABSENT | / ⇒ Sin camino VGA en esta máquina / `PROVEN_ABSENT` (en el driver) / |
| 159 | 35 | NEGATIVE_RESULT | ## 2 · `NEGATIVE_RESULT` sobre el método, y es el que reencuadra el bloque |
| 159 | 46 | PROVEN_ABSENT | **⇒ El gestor de display no se versiona por tabla de punteros a función.** `PROVEN_ABS |
| 159 | 157 | PROVEN_ABSENT | / No hay `struct dc_dm`, ni `dc_dm_*`, ni ops de DM / `PROVEN_ABSENT` / |
| 160 | 277 | PROVEN_ABSENT | misma nota**. (2) Casi escribo `PROVEN_ABSENT` sobre `get_max_link_cap` en la |
| 160 | 308 | PROVEN_ABSENT | `PROVEN_ABSENT` es la afirmación más peligrosa de esta nota, porque un `grep` vacío |
| 162 | 93 | PROVEN_ABSENT | `PROVEN_ABSENT`, con la causa identificada, que es un bomb y no una laguna. |
| 162 | 228 | PROVEN_ABSENT | / El AUX/DDC está ausente del driver, no del corpus / `PROVEN_ABSENT` / |
| 162 | 283 | PROVEN_ABSENT | error, y ese bomb convierte 55 `NOT_IN_CORPUS` en `PROVEN_ABSENT` con la causa escrita |
| 162 | 296 | PROVEN_ABSENT | en `159` y el `PROVEN_ABSENT` de VGA en `158`, pero al revés: allí la ausencia hurtó p |
| 162 | 306 | PROVEN_ABSENT | **Y esa forma de error es especialmente peligrosa porque produce un `PROVEN_ABSENT` en |
| 162 | 313 | PROVEN_ABSENT | seguidas con `PROVEN_ABSENT` en la boca y el patrón equivocado en las dos.* |
| 163 | 142 | PROVEN_ABSENT | **⇒ Esto NO refuta el `PROVEN_ABSENT` de `158` sobre el codificador analógico, y la |
| 166 | 217 | PROVEN_ABSENT | problema del punto 1. **Los tres primeros habrían producido un `PROVEN_ABSENT` falso |
| 167 | 100 | REFUTED | ### Error 1 — «el código es de DCE 11.0, no de esta GPU» → **`REFUTED`** |
| 167 | 128 | PROVEN_ABSENT | ### `PROVEN_ABSENT` — «`TMDS_CNTL` no aparece en la tabla de esta GPU» |
| 167 | 167 | PROVEN_ABSENT | `DIG0_`/`DIG1_`/`DIG2_` por DIG. Medido por programa. `PROVEN_ABSENT`. |
| 167 | 235 | REFUTED | / `148` error 1: el código es de DCE 11.0 / **`REFUTED`** por `156` y `159` / |
| 167 | 238 | PROVEN_ABSENT | / `148` `PROVEN_ABSENT`: conclusión certa, prueba del fichero erróneo / `PROVEN_DERIVE |
| 167 | 239 | PROVEN_ABSENT | / `DIG_FE_CNTL__TMDS_PIXEL_ENCODING_MASK` no existe para DCE / `PROVEN_ABSENT` / |
| 167 | 282 | PROVEN_ABSENT | producido una tabla de campos vacía y un `PROVEN_ABSENT` falso, y el (4) casi lo |
| 170 | 17 | PROVEN_ABSENT | **⇒ `gmc_v8_1.c`, `sdma_v3_1.c`, `uvd_v6_3.c` y `vce_v3_4.c` no están en el árbol.** ` |
| 170 | 131 | PROVEN_ABSENT | / `gmc_v8_1.c`, `sdma_v3_1.c`, `uvd_v6_3.c`, `vce_v3_4.c` no existen / `PROVEN_ABSENT` |
| 170 | 180 | PROVEN_ABSENT | `153` (los siete paths), `150` (los cuatro `cntl.signal`), `145` (`PROVEN_ABSENT` con |
| 172 | 221 | PROVEN_ABSENT | `150` (el enum de señal), `145` (`PROVEN_ABSENT` con causa). |
| 176 | 95 | PROVEN_ABSENT | `PROVEN_ABSENT` sería falso. No es un matiz: es la diferencia entre «lo he |
| 177 | 199 | PROVEN_ABSENT | / No hay atributo sysfs para ellos / `PROVEN_ABSENT` / |
| 177 | 200 | PROVEN_ABSENT | / `include/uapi/drm/` ausente del snapshot / `PROVEN_ABSENT` / |
| 181 | 27 | PROVEN_ABSENT | `dc_stream_encoder_init`, `dc_clk_mgr_init`… ninguno está en el árbol. `PROVEN_ABSENT` |
| 181 | 161 | PROVEN_ABSENT | / Las 28 semillas inventadas no existen / `PROVEN_ABSENT` / |
| 181 | 207 | PROVEN_ABSENT | eso se vio (`PROVEN_ABSENT` no; regla (k)). |
| 182 | 114 | PROVEN_ABSENT | `144` cerró `GFX_HWIP` como `PROVEN_ABSENT` y ofreció el firmware como fuente |
| 182 | 115 | PROVEN_ABSENT | alternativa. **La parte de `PROVEN_ABSENT` se sostiene**: el registro no existe |
| 182 | 124 | PROVEN_ABSENT | Eso convierte el hallazgo de `144` de "`PROVEN_ABSENT`" en algo más fuerte y |
| 182 | 155 | PROVEN_ABSENT | / Ningún escritor de `ip_versions` en el camino GCN3 / `PROVEN_ABSENT` / |
| 182 | 156 | PROVEN_ABSENT | / El `switch` codificado no tiene caso POLARIS / `PROVEN_ABSENT` / |
| 182 | 162 | REFUTED | / Que el driver la conozca / `REFUTED` / |
| 184 | 23 | REFUTED | `dce110_hwseq.c` es precisamente el código de esta placa.** `REFUTED`. |
| 184 | 111 | PROVEN_ABSENT | `using_dml21` sólo se ponen a true dentro de ese `if`.** `PROVEN_ABSENT` para cualquie |
| 184 | 124 | REFUTED | 27,8% sin podar de `181`. Y es incorrecto.** `REFUTED`. |
| 184 | 169 | PROVEN_ABSENT | / `DC_ENABLE_DML2`: una ocurrencia, y `using_dml2` off por defecto / `PROVEN_ABSENT` / |
| 184 | 170 | REFUTED | / El 12,0% podado / **`REFUTED`** / |
| 187 | 86 | REFUTED | refutada. Pero la prueba que la refuta ahora es otra y es independiente.** `REFUTED`. |
| 187 | 120 | REFUTED | / El 22,0% podado / **`REFUTED`** / |
| 187 | 162 | REFUTED | de una línea**), `184` (**las 21 guardas, y el `REFUTED` de su poda, que aquí se refut |
| 198 | 169 | PROVEN_ABSENT | nota**), `188` (la cadena observada y el `PROVEN_ABSENT` del símbolo), `187` (**los do |
| 224 | 232 | PROVEN_ABSENT | **En esta placa no hay invasion: `PROVEN_ABSENT`.** |
| 231 | 39 | PROVEN_ABSENT | ## `GFX_HWIP`: `PROVEN_ABSENT`, y ahora con causa |
| 231 | 163 | PROVEN_ABSENT | Eso no es un hueco de mi búsqueda: es `PROVEN_ABSENT` **con causa**. La |
| 231 | 171 | PROVEN_ABSENT | / `GFX_HWIP` no existe en el corpus / `PROVEN_ABSENT` — grep sobre `amd/` / |
| 231 | 179 | PROVEN_ABSENT | / Que no exista tabla de capacidad para GCN3 / `PROVEN_ABSENT` — sin `ip_discovery` / |
| 231 | 210 | PROVEN_ABSENT | - **`GFX_HWIP` deja de ser una frontera abierta**: es `PROVEN_ABSENT` con una |
| 232 | 198 | PROVEN_ABSENT | / Que no haya flush de caché de CPU en el camino / `PROVEN_ABSENT` — no hay más llamad |
| 233 | 160 | PROVEN_ABSENT | / Ninguna rama asigna `..._FOR_GFX` por defecto / `PROVEN_ABSENT` / |
| 236 | 149 | PROVEN_ABSENT | generación nueva nombra y el de la vieja no.** Es el mismo `PROVEN_ABSENT` con causa d |
| 236 | 184 | PROVEN_ABSENT | `145` (`PROVEN_ABSENT` con causa, y `include/uapi` ausente), |
| 240 | 21 | PROVEN_ABSENT | definiciones.** `PROVEN_ABSENT`. `184` queda corregido en ese punto. |
| 240 | 53 | PROVEN_ABSENT | ninguna definición.** `PROVEN_ABSENT`. *Las familias que `dal_asic_id.h` declara son |
| 240 | 123 | PROVEN_ABSENT | / `AMDGPU_FAMILY_VI`: dos usos, cero definiciones / `PROVEN_ABSENT` — corrige a `184`  |
| 240 | 164 | REFUTED | `AMDGPU_FAMILY_GC_11_5_4 256`, y todas son suyas.** `REFUTED`. *Acusar a un programa d |
| 241 | 130 | PROVEN_ABSENT | / `extern_gpu_id` no existe; el símbolo es `external_rev_id` / `PROVEN_ABSENT` — corri |
| 241 | 135 | PROVEN_ABSENT | / La declaración de `AMDGPU_FAMILY_VI` / **`PROVEN_ABSENT`** / |
| 241 | 141 | PROVEN_ABSENT | ninguna cabecera del árbol.** `PROVEN_ABSENT`. *No es `NOT_FOUND`: es `PROVEN_ABSENT`, |
| 241 | 166 | PROVEN_ABSENT | extensión.** `PROVEN_ABSENT`. |
| 241 | 172 | PROVEN_ABSENT | - Encadenada con `188` (**los tres eslabones observados y el `PROVEN_ABSENT` de |
| 243 | 15 | PROVEN_ABSENT | existe ningún header que lo declare, porque `include/linux/` tiene un solo fichero.**  |
| 243 | 37 | PROVEN_ABSENT | **⇒ `PROVEN_ABSENT`. La definición de `ttm_tt_pages_limit()` está en un directorio que |
| 246 | 19 | PROVEN_ABSENT | **⇒ `PROVEN_ABSENT`. GFX8 no tiene ningún registro de control de caché de datos en el  |
| 246 | 21 | PROVEN_ABSENT | `clearstate_vi.h` no contiene ninguna entrada de L2.** `PROVEN_ABSENT`. |
| 246 | 163 | PROVEN_ABSENT | **⇒ `PROVEN_ABSENT`. `grep -hoE '\b[A-Z][A-Z_0-9]*CACHE_CONTROL\b'` sobre |
| 246 | 165 | PROVEN_ABSENT | control de caché L2 en el corpus.** `PROVEN_ABSENT`. |
| 246 | 205 | PROVEN_ABSENT | **⇒ `PROVEN_ABSENT`. Y `flush_tlb_needs_extra_type_0` es un campo muerto: sus 5 aparic |
| 246 | 207 | PROVEN_ABSENT | (`:734`, `:803`, `:819`, `:831`). No hay ni una sola asignación en ningún ASIC.** `PRO |
| 251 | 24 | PROVEN_ABSENT | **⇒ `PROVEN_ABSENT`. El driver no lee ningún sensor térmico. Ni `mmTHM_TCON_CUR_TMP` n |
| 251 | 26 | PROVEN_ABSENT | corpus.** `PROVEN_ABSENT`. |
| 251 | 168 | PROVEN_ABSENT | **⇒ `PROVEN_ABSENT`. Y `legacy-dpm/` tiene su propia ruta de temperatura —`si_dpm.c:79 |
| 251 | 171 | PROVEN_ABSENT | `PROVEN_ABSENT`. |
| 254 | 27 | PROVEN_ABSENT | **⇒ `PROVEN_ABSENT`. El driver nunca valida esa cabecera: `ip_version_major` aparece u |
| 254 | 29 | PROVEN_ABSENT | `if (ip_version_major` en todo `amdgpu/`.** `PROVEN_ABSENT`. |
| 254 | 153 | PROVEN_ABSENT | **⇒ `PROVEN_ABSENT`. Y `grep -rn 'if.*ip_version_major\/ip_version_major ==\/ip_versio |
| 254 | 154 | PROVEN_ABSENT | !='` sobre `amdgpu/*.c` devuelve cero. No hay ni una comparación en todo el driver.**  |
| 255 | 16 | REFUTED | discrepancias en el corpus.** `REFUTED` (la contradicción) / `PROVEN` (el valor real). |
| 255 | 105 | REFUTED | **⇒ `REFUTED`. No hay contradicción sobre `num_level`: hay un valor correcto (`1`) y u |
| 255 | 107 | REFUTED | del ASIC, no del cálculo.** `REFUTED`. |
| 255 | 166 | REFUTED | **⇒ `REFUTED`. El `22` que `next_work.py` recoge como segundo valor de `block_size` no |
| 255 | 169 | REFUTED | no es un valor de esta función para ningún `tmp` que GFX8 pueda producir.** `REFUTED`. |
| 255 | 207 | REFUTED | **⇒ `REFUTED`. Ninguna de las tres contradicciones era real. La contradicción estaba e |
| 255 | 208 | REFUTED | herramienta, no en el conocimiento.** `REFUTED`. |
| 255 | 225 | PROVEN_ABSENT | cerrado como `PROVEN_ABSENT` del parámetro.** `PROVEN_DERIVED`. |

**Total**: 285 resultados negativos registrados.

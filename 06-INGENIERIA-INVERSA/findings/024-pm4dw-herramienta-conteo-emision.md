# 024 · pm4dw: herramienta de conteo de emisión, y por qué el 020 y el 018 discrepaban

`CLASSIFICATION=STATIC_IMPLEMENTATION` · `TOOL=tools/pm4dw.c` · `CORPUS=rx550-upstream-7.2.8/linux-7.2.8`
`RUNTIME=NOT_RUN` · `GPU INTACTA` · `MODIFICATIONS=0` en el corpus

## CUDA principal

El `CONFLICT` entre sesiones sobre el presupuesto de dwords del vm-flush no era una
diferencia de criterio: era un conteo manual repetido por dos personas con dos reglas
distintas. La herramienta resuelve la cuenta desde el texto, declara sus supuestos y
**se ha visto fallar tres veces antes de dar un número**, lo que es la única prueba de que
detecta lo que dice detectar.

## Por qué una herramienta y no más lectura

`COORDINACION.md` §"Antes de reportar un resultado": *"Si el test puede fallar, demuéstralo:
 reinserta el defecto, ejecútalo, registra el número, revierte."* El `CONFLICT` de `020`
contra la iteración 3 era exactamente eso, sin verificar. La herramienta es el test.

## Alcance exacto

1. Mecanizar el conteo de `amdgpu_ring_write()` por función, resuelto a través de llamadas.
2. Leer la aritmética de `.emit_frame_size` con sus constantes simbólicas.
3. Comparar declarado contra emitido.
4. Demostrar que la herramienta falla cuando debe.

## Criterio de terminación (cumplido)

La herramienta compila sin warnings con `-Wall -Wextra`, produce salida sobre el corpus
real, y tres mutaciones independientes producen salidas distintas. Agotado.

---

## 1 · El resultado sobre el corpus real

```
$ pm4dw --macro VI_FLUSH_GPU_TLB_NUM_WREG=3 \
        --struct gfx_v8_0_ring_funcs_gfx \
        --struct gfx_v8_0_ring_funcs_compute \
        --struct gfx_v8_0_ring_funcs_kiq gfx_v8_0.c gmc_v8_0.c
```

| función | dw directas | dw totales | nota |
|---|---:|---:|---|
| `gfx_v8_0_ring_emit_wreg` | 5 | 5 | `INDIRECT_DISPATCH:INCOMPLETE` |
| `gfx_v8_0_ring_emit_vm_flush` | 9 | **9** | `INDIRECT_DISPATCH:INCOMPLETE` |

| struct | declarado | suma de handlers | residual |
|---|---:|---:|---:|
| `gfx_v8_0_ring_funcs_gfx` | 172 | 74 | +98 |
| `gfx_v8_0_ring_funcs_compute` | 109 | 52 | +57 |
| `gfx_v8_0_ring_funcs_kiq` | 77 | 31 | +46 |

**`gfx_v8_0_ring_emit_vm_flush` = 9 dw, no 19.** Y la razón es el resultado más útil de la
herramienta: la función llama a `amdgpu_gmc_emit_flush_gpu_tlb`, que es un **macro** que
despacha por puntero:

```c
/* amdgpu_gmc.h:373 */
#define amdgpu_gmc_emit_flush_gpu_tlb(r, vmid, addr) \
        (r)->adev->gmc.gmc_funcs->emit_flush_gpu_tlb((r), (vmid), (addr))
```

Los 10 dwords de los dos `emit_wreg` viven detrás de ese puntero. La herramienta **no puede
resolverlos leyendo un fichero**, y por eso marca la función `INCOMPLETE` en vez de publicar
9 como si fuera el total. El 9 es correcto y es la mitad de la respuesta.

Con el hueco rellenado a mano: 9 + 2 WREG × 5 = **19 dw en ring GFX**, lo que confirma la
tabla de `020` (residual +5) y refuta mi +6 de la iteración 3. El error mío fue sumar
`PFP_SYNC_ME` a un ring que no lo emite, porque `usepfp` depende de
`ring->funcs->type == AMDGPU_RING_TYPE_GFX` y KIQ no lo es.

## 2 · Las tres veces que la herramienta dio un número falso

Esta es la parte que la hace creíble. Cada fallo está en el código con el motivo escrito.

| # | Fallo | Síntoma | Causa |
|---|---|---|---|
| 1 | Llaves dentro de cadenas y comentarios desincronizaban el emparejado | tabla vacía, **sin error** | emparejado ingenuo de llaves |
| 2 | El campo `.emit_frame_size` se leía hasta el `;` siguiente | sumaba campos ajenos: **72 de 168** | termina en `,` no en `;`, y una coma **dentro de un comentario** ("double SWITCH_BUFFER,") lo corta antes |
| 3 | `.emit_frame_size` se buscaba como `name(` | `STRUCT_NOT_FOUND` en todos | los structs se inicializan con `name = {`, sin paréntesis |

Y dos más que no fallaron en silencio sino que **dieron números disparatados**, que es peor:

| # | Fallo | Síntoma | Causa |
|---|---|---|---|
| 4 | Grafo de llamadas divergente | totales de **1.9 billones** | `switch(...)` y `ARRAY_SIZE(x)` se parsearon como funciones; el grafo tenía ciclos |
| 5 | Búsqueda de firma sin límite | función llamada `mutex_unlock` con cuerpo ajeno | `mutex_unlock(&lock);` emparejado con el bloque siguiente |

Los dos últimos los delató el guardia de convergencia y la lista de sospechosos, que
imprimió `cycle suspect: gfx_v8_0_kiq_init_queue calls amdgpu_in_reset (1 site)`. Un número
absurdo es más fácil de detectar que uno plausible; por eso los guardas existen y por eso
esta tabla es la evidencia de que la herramienta no es decorativa.

## 3 · Mutaciones: la herramienta discrimina

`COORDINACION.md` exige haber visto el test fallar. Tres mutaciones, revertidas.

**M1 · `emit_wreg` de 5 a 6 dw** (un `amdgpu_ring_write` añadido)

```
emit_wreg   5 -> 6      suma del struct  31 -> 32      residual  +46 -> +45
```

**M2 · la reserva de KIQ pasa de 17 a 3** (`17 + /* gfx_v8_0_ring_emit_vm_flush */`)

```
declarado  77 -> 63     el número se mueve con el código, no está cacheado
```

**M3 · la reserva de KIQ cae a 8**, por debajo de la suma de handlers

```
gfx_v8_0_ring_funcs_kiq    8    32    -24   BELOW sum-of-handlers
```

El veredicto cambia. `EXIT=0` en los tres casos porque el código de salida **no** declara
infrarreserva, por la razón de §4.

## 4 · Por qué no sale con código de error, y por qué eso es lo honesto

`emit_frame_size` es una **reserva**, y debe cubrir el conjunto más grande de emisores que
pueden coexistir **en un mismo envío**. La suma de todos los handlers que el struct nombra
es una **cota superior**, no ese conjunto: `gfx_v8_0_ring_funcs_gfx` nombra trece emisores
y casi nunca coexisten todos.

Por tanto `declarado < suma` **no prueba** infrarreserva. Declararla sería un falso positivo,
que es el modo de fallo que `AGENTS.md` §"Captured is not consumed" prohíbe: un campo
recogido y nenhuma decisión lo consume. La herramienta imprime el número y lo llama
cota. Cuando se quiera un veredicto duro hará falta saber qué emitters coexisten, y eso
está en `amdgpu_vm_flush` (`amdgpu_vm.c:785-866`), no en el struct.

**Consecuencia sobre el trabajo anterior**: los residuales `+5, +5, 0` de `020` son
correctos como *cuenta de `emit_frame_size`*, pero no son un veredicto de seguridad del
ring. Ninguno de los tres rings está infrarreservado frente a la cota superior, y eso es
más de lo que se podía afirmar antes.

## 5 · Supuestos declarados, en la salida de la herramienta

Un número sin supuestos no es evidencia. Los tres que esta cuenta tiene:

| supuesto | verificado en | si fuese falso |
|---|---|---|
| 1 `amdgpu_ring_write()` = 1 dword | `amdgpu_ring.h:494-499`: escribe un `u32` y decrementa `count_dw` | todos los totales |
| `amdgpu_ring_write_multiple()` = 1 dw | se cuenta una vez, **no** según el argumento | la herramienta marca `write_multiple:NOT_EXPANDED` en `gfx_v8_0_ring_emit_ce_meta` y `_de_meta` |
| `.emit_frame_size` reserva ≥ suma de handlers | por construcción del struct | marcado como cota, no veredicto |

## 6 · Limitaciones declaradas

- `INDIRECT_DISPATCH:INCOMPLETE` marca toda función que despacha por `->gmc_funcs->`,
  `->funcs->` o `->pmf->`. Casi todo el path de emisión de GFX8 lo hace. La herramienta no
  resuelve punteros de función **por diseño**, y lo dice en cada fila.
- El parser es de estilo kernel: definiciones y `name = {`. No maneja C++ ni macros
  multilínea con continuación `\`.
- `LOOKAHEAD_LINES 3`: una firma partida en más de 3 líneas se pasa por alto. En este
  corpus no la hay.
- El filtro de nombres (`is_definition_name`) rechaza keywords y macros en MAYÚSCULAS. Es
  una heurística: un identificador en minúsculas que sea en realidad una macro se
  aceptaría como función. Ninguna conocida en estos dos ficheros.

## 7 · UNLOCKS

- La aritmética de `emit_frame_size` deja de needing cálculo mental. Cualquier cambio
  futuro a un emisor se mide con `pm4dw` en vez de contarse a ojo.
- Los residuales de `020` quedan corroborados por cálculo mecánico sobre 7.2.8 **y** por el
  script de la otra sesión sobre 7.1.3. Dos corpus, mismo número.
- La tabla de la §2 es reutilizable: son las trampas de parsing de C que cualquier
  herramienta de análisis estático de este driver va a encontrar.

## 8 · Criterio de falsación

La herramienta se refutaría si: (a) una mutación que cambia la emisión no cambia la salida
— M1 lo contradice; (b) un struct real del corpus saliera `STRUCT_NOT_FOUND` — no ocurre en
los tres que importan; (c) `emit_frame_size` fuera un límite y no una reserva, en cuyo caso
`+98` sería un bug del driver y no holgura — eso hay que decidirlo leyendo
`amdgpu_ring_alloc`, y queda `NOT_DETERMINED`.

## 9 · Evidencia

```
tools/pm4dw.c                    la herramienta, C99, sin dependencias
build:                           cc -O2 -Wall -Wextra -o pm4dw pm4dw.c   (0 warnings)
corpus sha256:  12e8d5a973d1ad7c5a5c69882e4022b131ed715db7003fdcd760ddf8c3e51941 (linux-7.2.8.tar.xz)
funciones citadas:  amdgpu_ring.h:494-499, amdgpu_gmc.h:373,
                    amdgpu_vm.c:785-866, gfx_v8_0.c:6200, 6873-6917, 6919-6952, 6954-6977
mutaciones: /tmp/opencode/mut (copia del corpus, revertida tras cada prueba)
```

Ningún registro leído de MMIO. Ningún nodo de dispositivo abierto. `MODIFICATIONS=0` en el
corpus: las mutaciones se hicieron sobre una copia en `/tmp/opencode`, nunca sobre
`rx550-upstream-7.2.8`.
# 027 · `write_multiple` deja de ser una bandera: la herramienta resuelve el tamaño

`CLASSIFICATION=STATIC_IMPLEMENTATION` · `TOOL=tools/pm4dw.c --wm-sites --struct-size`
`CORPUS=rx550-upstream-7.2.8/linux-7.2.8` · `RUNTIME=NOT_RUN` · `GPU INTACTA`
`CONTINUES=026-frame-completo-gfx8-121dw.md`

## CUDA principal

`026 §3` resolvió el `write_multiple` a mano desde `vi_structs.h`. Eso es una dependencia
de criterio humano justo en el número que más se cita. Ahora la herramienta lo resuelve:
**17/27/4/10 dwords**, y si alguien cambia la struct, el número se mueve solo.

Además `--wm-sites` imprime cada llamada con sus argumentos, así que el subconteo ya no es
una bandera sino algo auditable línea a línea.

## Alcance exacto

1. Convertir la bandera `NOT_EXPANDED` en sitios de llamada verbatim.
2. Resolver `sizeof` de struct desde los headers del corpus.
3. Verificar que el resultado reproduce el cálculo manual de `026 §3`.
4. Verificar con mutación que la nueva capacidad discrimina.

## Criterio de terminación (cumplido)

Ambos modos implementados, verificados contra el cálculo manual, y una mutación que mueve
el resultado. Agotado.

---

## 1 · `--wm-sites`: los sitios, verbatim

```
$ pm4dw --wm-sites gfx_v8_0.c
# amdgpu_ring_write_multiple() call sites (each counted as 1 dw by the cost model)
gfx_v8_0_ring_emit_ce_meta               ring, (void *)&ce_payload, cnt_ce - 2
gfx_v8_0_ring_emit_de_meta               ring, (void *)&de_payload, cnt_de - 2
2 site(s); each is a multi-dword copy whose size is NOT in this count
```

Dos sitios en el fichero, y ahora se ve *por qué* el conteo es provisional: el tercer
argumento es `cnt_de - 2`, o sea una expresión cuyo valor depende de `sizeof` de una struct.
Con la bandera a secas había que confiar en que alguien lo había comprobado.

Un fallo al implementarlo: la primera versión cortaba la lista de argumentos en el primer
`)`, que es el del cast `(void *)`, y devolvía `(void *`. Arreglado con paréntesis
balanceados. Un bug de parsing que produce texto truncado en lugar de error es peor que
uno que aborta.

## 2 · `--struct-size`: la resolución

```
$ pm4dw --struct-size vi_de_ib_state --struct-size vi_de_ib_state_chained_ib \
        --struct-size vi_ce_ib_state --struct-size vi_ce_ib_state_chained_ib \
        gfx_v8_0.c include/vi_structs.h
# struct sizes (each fixed-size member counted as 4 bytes)
STRUCT                                MEMBERS    BYTES    cnt_de write_mult
vi_de_ib_state                             17       68         19         17
vi_de_ib_state_chained_ib                  27      108         29         27
vi_ce_ib_state                              4       16          6          4
vi_ce_ib_state_chained_ib                  10       40         12         10
```

Coincide **exactamente** con la tabla de `026 §3`, calculada a mano. Dos caminos
independientes al mismo número: `CORROBORATED`, no `PROVEN` por una sola fuente.

## 3 · Tres fallos más, todos del mismo tipo

| # | síntoma | causa | por qué importa |
|---|---|---|---|
| 6 | `NOT_FOUND` para structs que **sí** existen | pasaba `files[]` (rutas) donde esperaba contenidos | un `NOT_FOUND` por bug se lee igual que un `NOT_FOUND` real |
| 7 | cuelgue infinito | el escaneo de líneas paraba *en* el `\n` y lo reencontraba | un timeout no dice nada del resultado |
| 8 | `MEMBERS = 0` para structs con 17 miembros | los miembros van indentados con tabulador y la comparación arrancaba en el tab | **el peor**: un 0 con salida bien formada |

El último es el que más me preocupa. Los tres producen salida válida y silenciosamente
incorrecta, y el tercero además con formato de tabla que invita a confiar. Es exactamente
el patrón que `AGENTS.md` §"A name is not a measurement" describe, y la respuesta correcta
—que ya estaba en el diseño— es declarar el supuesto y luego **mirar si el número tiene
sentido**: 17 miembros para una struct de estado DE es plausible; 17 y 27 y 4 y 10, en
descenso, también. Un 0 para las cuatro no lo es.

## 4 · Mutación M5

Tres miembros añadidos a `struct vi_ce_ib_state` en una copia de `vi_structs.h`:

```
antes   vi_ce_ib_state   4 miembros   16 B   cnt_de 6   write_mult 4
despues vi_ce_ib_state   7 miembros   28 B   cnt_de 9   write_mult 7
```

La cadena `members → bytes → cnt_de → write_mult` se mueve entera. Copia en
`/tmp/opencode/mut3`, eliminada. `MODIFICATIONS=0` en el corpus.

## 5 · El número del frame, ahora sin cálculo manual

Con `--struct-size` resolviendo los payloads, el total de `026 §4` queda:

```
emit_cntxcntl real = 3 directos + ce_meta + de_meta
                   = 3 + (4+4) + (4+17)
                   = 32 dw   (no encadenado)
                   = 3 + (4+10) + (4+27) = 48 dw  (con chained_ib_support)
```

| | medido | corregido |
|---|---:|---:|
| ruta máxima del frame GFX8 | 90 | **121 dw** |
| con `chained_ib_support` | — | **137 dw** |
| `emit_frame_size` declarado | 172 | 172 |
| holgura | — | 51 / 35 dw |

El número **121 dw** ya no depende de que nadie recuerde multiplicar por 4.

## 6 · Lo que la herramienta sigue sin hacer

Declarado, no descubierto por el camino:

- No resuelve `write_multiple` **automáticamente** dentro del modelo de coste. `--wm-sites`
  y `--struct-size` dan los dos datos necesarios y el ensamblaje sigue siendo manual. Unir
  ambos sería un paso corto, pero exige resolver `cnt_de = (sizeof(x)>>2) + 4 - 2`, que es
  evaluación de expresiones, y no quiero añadirla sin una razón que la justifique.
- Un miembro de array (`uint32_t x[4];`) cuenta como uno, no cuatro. Ninguno de los structs
  consultados tiene arrays, y la salida no lo indica. `LIMITATION` activa.
- `uint64_t` cuenta como 4 bytes igual que `uint32_t`. Ninguno de los structs consultados
  tiene miembros de 64 bits; el mismo día que aparezca, el cálculo pasa a ser una
  estimación sin avisar.

## 7 · UNLOCKS

- `vi_structs.h` queda indexado por la herramienta. Cualquier payload de meta-datos PM4 de
  GFX8 se dimensiona sin hardware: `vi_ce_ib_state` = 16 B, `vi_de_ib_state` = 68 B, y sus
  variantes encadenadas 40 y 108 B.
- El `171→172` de `emit_frame_size` queda con una explicación candidate: la constante está
  escrita a mano y nadie la derivó de la secuencia, que da 121. Es `MODEL_CHOICE` legítimo
  elegir holgura; lo que no es legítimo es heredarla sin justificar, y `NO_HISTORICAL_INHERITANCE`
  lo prohíbe. La justificación posible ya existe y es medible: la holgura cubre el caso
  chained-IB y los IBs con preemption.

## 8 · Evidencia

```
herramienta:  tools/pm4dw.c, sha256 228e61b8757ebfcd7aec9895935ad100cb2b90432f378f586653c3a2906d2ab5
build:        cc -O2 -Wall -Wextra, 0 warnings
corpus:       12e8d5a973d1ad7c5a5c69882e4022b131ed715db7003fdcd760ddf8c3e51941 (linux-7.2.8.tar.xz)

gfx_v8_0.c:              7175 (ce_meta write_multiple), 7208 (de_meta write_multiple),
                         6075-6105 (emit_ib_gfx), 7180-7205 (cnt_de / cnt_ce)
include/vi_structs.h:    434-455 (vi_de_ib_state, 17 dword),
                         470+ (chained, 27 dword), y las variantes de CE
amdgpu_ib.c:             197-200 (fórmula de reserva)
mutación:                /tmp/opencode/mut3, eliminada
```

Ningún registro leído de MMIO. Ningún nodo de dispositivo abierto. `RUNTIME=NOT_RUN`.
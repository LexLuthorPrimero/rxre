# 066 · Cada `.c` declara sus familias de cabecera, y eso acota dónde puede estar el error de offset

```
CLASSIFICATION=DOCUMENTATION · TRACK=STATIC · CORPUS=RESEARCH/working/linux-7.1.3
HARDWARE_SCOPE=HOST-C/RX550/0000:01:00.0 · WORK_CLASS=READ_ONLY/EVIDENCE
WRITE_EXECUTION=NONE · MODIFICATIONS=0 · RUNTIME=NOT_RUN · GPU INTACTA
```

## Qué resuelve

065 demostró que **7 de los 14 registros que escribe `gmc_v8_0.c` tienen
direcciones distintas según la familia de cabecera**. Eso responde *qué* falla
cuando se copia un offset equivocado. Esta nota responde *dónde más puede
fallar*, y para eso hace falta el barrido completo, que no existía.

Resultado del barrido sobre los `.c` de `amdgpu/`:

```
  .c totales                                304
  con familia de registro declarada         191
  con MÁS DE UNA familia                     69
  sin familia directa                       113  (109 no son bloques de ASIC)
  ASIC de registro referenciados             162
  de los que son GFX8                         22
```

Los 140 ASIC restantes (`athub_4_1_0`, `df_4_15`, `vcn_4_0`, …) son de otras
generaciones. Existen porque el árbol de amdgpu contiene todos los ASIC que
AMDGPU soporta, no sólo los de esta GPU. Un informe que los mezcle con los 22
pertinentes esconde lo que sirve.

## El dato que corrige una simplificación

`gmc_v8_0.c` **no declara una familia: declara cuatro**.

```
  gmc        gmc_8_1     gmc/gmc_8_1_d.h
  bif        bif_5_0     bif/bif_5_0_d.h
  oss        oss_3_0     oss/oss_3_0_d.h
  dce        dce_10_0    dce/dce_10_0_d.h
```

Escribir "el mapa de registros de esta GPU es GMC" —que es el error que una
sesión cometió leyendo el primer `#include`— es peor de lo que parecía: no es
que la familia fuera la equivocada, es que **el fichero vive en cuatro**. Sus 14
registros escritos están repartidos entre cuatro espacios de direcciones
distintos, y cada familia tiene su propio.

Comprobado con tres registros de tres familias:

```
  VM_CONTEXT0_CNTL        0x504   (gmc)
  MC_SHARED_BLACKOUT_CNTL 0x82b   (gmc)
  VGA_HDP_CONTROL         0xca    (dce)
```

`0x504` y `0x82b` conviven sin solaparse dentro de GMC; `0xca` pertenece a DCE.
Dentro de una familia el espacio es coherente. **Entre familias no.**

## Por qué esto acota el riesgo en vez de ampliarlo

Los 69 ficheros multi-familia son, exactamente, la lista donde un offset copiado
de la familia vecina se escribiría sin error visible. No son un problema: son el
inventario de dónde hay que comprobar.

Y hay un dato que los hace manejables: `gmc_8_1` lo usan 6 `.c` y `gmc_8_2` sólo
2 (`gfx_v8_0.c` y `mxgpu_vi.c`). Es decir, la revisión Polaris12 es minoritaria
dentro del propio árbol GFX8. Una herramienta que aplique el filtro de GFX8
reduce el espacio de 162 a 22, y `hdrmap.py` lo hace en un comando.

## Lo que la herramienta NO hace, y es lo importante

**No sabe cuál de las varias familias escribe un registro concreto.** Rastrear
eso es lo que hace `regdb.py`, que compara valores entre familias. Estas dos
herramientas se complementan y no se solapan:

```
  hdrmap.py   ¿qué familias declara este .c?          (rápido, un barrido)
  regdb.py    ¿este registro coincide en ellas?       (lento, registro a registro)
  xref.py     ¿quién escribe este símbolo?            (rápido)
  causal.py   ¿en qué función, y hay arista de llamada? (más lento)
```

`hdrmap.py` no reimplementa el resolutor de includes: usa `find_header()` de
`include_closure.py`, que ya existía. Es composición, no duplicación. Y no
decide qué ASIC es el correcto: informa de lo que el fichero **declara**, que es
un hecho textual, no de lo que el hardware ejecuta, que exigiría `vi.c`.

**Sólo lee includes directos.** Un `.c` que herede una cabecera de registro de
otro `.h` aparece como "sin familia", y eso es un límite de la herramienta, no un
hueco del driver. Por eso el informe lo dice en esa palabra.

## Límites declarados

| Límite | Consecuencia |
|---|---|
| Sólo includes directos | 113 `.c` sin familia; los que la heredan no se ven |
| No sabe qué ASIC se instancia | `gmc_8_1` declarado ≠ `gmc_8_1` ejecutado |
| Filtro GFX8 por lista cerrada | un ASIC nuevo no aparece; hay que añadirlo |
| No sigue includes transitivos | como el anterior, en la otra dirección |
| Un `.c` puede declarar familia y no usarla | presencia de cabecera ≠ uso de registro |

La última merece atención: `gfx_v8_0.c` declara `gmc_8_2` y `gmc_8_1` a la vez.
Declarar una cabecera no significa escribir sus registros, y `regdb.py --scan-file`
es el que separa lo declarado de lo escrito. Las dos herramientas contiguas.

## Estado

| Afirmación | Estado |
|---|---|
| 304 `.c`, 191 con familia declarada | `PROVEN` (barrido) |
| 69 con más de una familia | `PROVEN` (barrido) |
| `gmc_v8_0.c` declara 4 familias | `PROVEN` (`hdrmap.py --file`) |
| 22 ASIC de GFX8 de 162 declarados | `PROVEN` (barrido + filtro) |
| Espacios de dirección distintos entre familias | `PROVEN` (3 registros, 3 familias) |
| Los 4 headers de `gmc_v8_0.c` resuelven a ruta real | `PROVEN` |
| Qué ASIC instancia el hardware | `NOT_DETERMINED` (falta `vi.c`) |
| Cuál familia escribe cada registro | lo responde `regdb.py`, no esta nota |

## Procedencia

- `CORPUS` — `amdgpu/*.c`, `include/asic_reg/`.
- Herramientas: `hdrmap.py` (19 casos de self-test, incluido el caso real de 065)
  sobre `include_closure.py`; `regdb.py` para los tres offsets citados.
- Sin `RUNTIME`, sin lectura de la GPU, sin escrituras.
- No se editó 065: es de esta sesión y este hallazgo la complementa, no la
  contradice. 065 afirmaba el caso de una familia; aquí se mide que son cuatro.
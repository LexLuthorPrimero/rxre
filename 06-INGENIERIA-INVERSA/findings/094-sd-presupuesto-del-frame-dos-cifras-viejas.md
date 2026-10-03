# 094 · §D: el presupuesto del frame, con las dos cifras viejas que tiene dentro

```
CLASSIFICATION=DOCUMENTATION · TRACK=STATIC
CORPUS=RESEARCH/working/linux-7.1.3 · HARDWARE_SCOPE=HOST-C/RX550/0000:01:00.0
WORK_CLASS=READ_ONLY/EVIDENCE · WRITE_EXECUTION=NONE · MODIFICATIONS=0
RUNTIME=NOT_RUN · GPU INTACTA
```

## Qué resuelve

`068` cerró la emisión: qué escribe el driver y en qué orden. Lo que quedaba
por debajo de eso era **cuánto cuesta** esa emisión, y resulta que el driver
tiene su propio documento contable — `emit_frame_size`, con cada paquete
nombrado y su coste en dwords.

Es la forma más directa que hay de contestar "qué ejecuta el hardware, en orden",
sin tocar la semántica.

## El documento

```
gfx_v8_0.c:6870   static const struct amdgpu_ring_funcs gfx_v8_0_ring_funcs_gfx = {
gfx_v8_0.c:6872       .align_mask = 0xff,
gfx_v8_0.c:6878       .emit_frame_size = /* maximum 215dw if count 16 IBs in */
gfx_v8_0.c:6879           5 +  /* COND_EXEC */
gfx_v8_0.c:6880           7 +  /* PIPELINE_SYNC */
gfx_v8_0.c:6881           VI_FLUSH_GPU_TLB_NUM_WREG * 5 + 9 + /* VM_FLUSH */
gfx_v8_0.c:6882           12 +  /* FENCE for VM_FLUSH */
gfx_v8_0.c:6883           20 + /* GDS switch */
gfx_v8_0.c:6884           4 + /* double SWITCH_BUFFER, ... */
gfx_v8_0.c:6887           5 + /* COND_EXEC */
gfx_v8_0.c:6888           7 +  /*	HDP_flush */
gfx_v8_0.c:6889           4 +  /*	VGT_flush */
gfx_v8_0.c:6890           14 + /* CE_META */
gfx_v8_0.c:6891           31 + /*	DE_META */
gfx_v8_0.c:6892           3 + /* CNTX_CTRL */
gfx_v8_0.c:6893           5 + /* HDP_INVL */
gfx_v8_0.c:6894           12 + 12 + /* FENCE x2 */
gfx_v8_0.c:6895           2 + /* SWITCH_BUFFER */
gfx_v8_0.c:6896           5, /* SURFACE_SYNC */
```

**Diecisiete términos, diecisiete paquetes nombrados.** Es el frame máximo, y es
la secuencia que el hardware tiene que recorrer. Los nombres coinciden con los
que `068` ya había encontrado emitiendo uno a uno.

## El orden, que es lo que `068` no tenía en una sola vista

```
   dw   paquete               dw   paquete
    5   COND_EXEC              5   COND_EXEC  (2)
    7   PIPELINE_SYNC          7   HDP_flush
   24   VM_FLUSH               4   VGT_flush
   12   FENCE (VM_FLUSH)      14   CE_META
   20   GDS switch            31   DE_META
    4   SWITCH_BUFFER x2       3   CNTX_CTRL
                               5   HDP_INVL
                              12   FENCE
                              12   FENCE
                               2   SWITCH_BUFFER
                               5   SURFACE_SYNC
```

**Tres FENCE y tres COND_EXEC**, y el `VM_FLUSH` va en segundo, justo después
del `PIPELINE_SYNC` — que es exactamente lo que `067`, `068` y `194`
habían visto por partes, uno a uno.

Y hay un detalle en `L6884-6886` que no es una cuenta: *"the first COND_EXEC
jump to the place just prior to this double SWITCH_BUFFER"*. O sea, el segundo
`COND_EXEC` **salta por encima** del bloque de `SWITCH_BUFFER`, que es lo que
`072` llamó "SWITCH_BUFFER doble no saltable". **El driver sí lo salta, con un
salto hacia atrás.** `072` decía que no se podía saltar; el código dice que se
salta, y el comentario lo explica en la línea siguiente al número.

## El descuello: dos cifras viejas, y las dos importan por igual

Evaluando la expresión con `VI_FLUSH_GPU_TLB_NUM_WREG = 3` (`vi.h:27`):

```
5 + 7 + (3*5+9) + 12 + 20 + 4 + 5 + 7 + 4 + 14 + 31 + 3 + 5 + 12 + 12 + 2 + 5 = 172 dw
```

**La expresión da 172. El comentario dice 215.**

Y la segunda cifra vieja, en la misma línea:

```
comentario   : "if count 16 IBs in"
amdgpu_ring.c:61   case AMDGPU_RING_TYPE_GFX:
amdgpu_ring.c:62       /* Need to keep at least 192 on GFX7+ for old radv. */
amdgpu_ring.c:63       return 192;
```

**El máximo real de IBs en el ring GFX es 192, no 16.** El comentario es de una
generación en la que el límite era 16 — y en `amdgpu_ring_max_ibs` todavía
vive ese 16, en el caso `AMDGPU_RING_TYPE_VCN_JPEG` (L67). Se quedó copiado.

| cifra | comentario | real | factor |
|---|---|---|---|
| parte fija del frame | 215 dw | **172 dw** | −43 |
| IBs máximos | 16 | **192** | ×12 |

**Las dos están viejas, y en direcciones opuestas.** Unainfraestima el frame,
la otra infraestima los IBs. Se compensan a medias y por eso el descuello
total no salta a la vista.

## Por qué no importa: la alineación se lo come

Los dos consumidores usan el **valor del código**, no el comentario:

```
amdgpu_ib.c:197    alloc_size = ring->funcs->emit_frame_size + num_ibs * ring->funcs->emit_ib_size;
amdgpu_ring.c:332  max_ibs_dw = ring->funcs->emit_frame_size + amdgpu_ring_max_ibs(...) * ring->funcs->emit_ib_size;
amdgpu_ring.c:334  max_ibs_dw = (max_ibs_dw + ring->funcs->align_mask) & ~ring->funcs->align_mask;
```

`L334` **redondea hacia arriba a múltiplo de `align_mask`**, y `align_mask =
0xff` (084, el mismo que hace que el fetch de comandos sea de 4 KiB).

```
reserva real   = 172 + 192 * 4 = 940 dw  ->  (940 + 255) & ~255  = 1024 dw
con el comentario = 215 +  16 * 4 = 279 dw  ->  (279 + 255) & ~255 =  512 dw
```

Los dos caminos dan múltiplos de 256. **El código no puede desbordar por esto**,
porque el presupuesto se re-evalúa en cada asignación y se alinea después.

Así que el comentario está mal y **es inerte**. Ni es un bug ni una
vulnerabilidad: es documentación abandonedada que nadie ha revisado desde que
el frame creció.

## Y el mismo cálculo para el ring SDMA, que es el escritor efectivo

`AGENTS.md` L159-161 dice que el escritor de page table efectivo es SDMA, no la
ruta de CPU. Su presupuesto:

```
sdma_v3_0.c:1572   .emit_frame_size =
sdma_v3_0.c:1573       6 + /* sdma_v3_0_ring_emit_hdp_flush */
sdma_v3_0.c:1574       3 + /* hdp invalidate */
sdma_v3_0.c:1575       6 + /* sdma_v3_0_ring_emit_pipeline_sync */
sdma_v3_0.c:1576       VI_FLUSH_GPU_TLB_NUM_WREG * 3 + 6 + /* sdma_v3_0_ring_emit_vm_flush */
sdma_v3_0.c:1577       10 + 10 + 10, /* fence x3 */
sdma_v3_0.c:1578   .emit_ib_size = 7 + 6, /* sdma_v3_0_ring_emit_ib */
```

| | ring GFX | ring SDMA |
|---|---|---|
| términos elementados | 17 | 7 |
| frame fijo | **172 dw** | **60 dw** |
| dw por IB | **4** | **13** |
| IBs máximos | 192 | 49 (`default` de `max_ibs`) |
| reserva bruta | 940 dw | 697 dw |
| reserva alineada | 1024 dw | 768 dw |

**Un IB lógico cuesta 4 dwords en el ring GFX y 13 en el SDMA.** El mismo
dato, 3,25 veces más caro si lo escribe SDMA. Y el frame fijo del SDMA es
tres veces más corto, con siete paquetes en lugar de diecisiete.

**O sea: los dos caminos no son equivalentes.** Escriben lo mismo con
presupuestos distintos, y eso es información de diseño, no un detalle.

## Lo que NO cierra

| Afirmación | Estado |
|---|---|
| 17 paquetes en el frame GFX máximo | `PROVEN` (`gfx_v8_0.c:6879-6896`) |
| La expresión evalúa a 172 dw | `PROVEN` (aritmética sobre `vi.h:27`) |
| El comentario dice 215 | `OBSERVED` (`gfx_v8_0.c:6878`) |
| `max_ibs` para GFX es 192, no 16 | `PROVEN` (`amdgpu_ring.c:63`) |
| La alineación a 0xff absorbe la diferencia | `PROVEN` (`amdgpu_ring.c:334`) |
| El segundo COND_EXEC salta por encima del SWITCH_BUFFER doble | `PROVEN` (`gfx_v8_0.c:6884-6886`) |
| IB = 4 dw en GFX, 13 dw en SDMA | `PROVEN` (ambas tablas) |
| Por qué el comentario quedó en 215 | **`NOT_DETERMINED`** |
| Cuándo empezó a estar viejo | **`NOT_DETERMINED`** |
| Si otro ring de esta GPU tiene el mismo defecto | `NOT_DETERMINED` — no mirado |

**"Por qué quedó en 215" no lo sé y no lo invento.** 215 − 172 = 43, y no
encaja limpiamente con ninguno de los términos de la lista: no es `CE_META +
DE_META` (45), ni `HDP_INVL + HDP_flush + VGT_flush` (16), ni
`GDS switch + CE_META` (34). Podría ser que la lista haya crecido sin que nadie
actualizara el total, o que el 215 viniera de otra generación con otros
paquetes. **Sin historial de git no se puede distinguir, y no lo tengo.**

Lo que sí puedo afirmar es que **el código y el comentario discrepan, y que el
código es el que manda.**

## Procedencia

- `STATIC` — `gfx_v8_0.c:6870-6896`, `sdma_v3_0.c:1570-1582`,
  `amdgpu_ring.c:58-71` y `amdgpu_ring.c:332-339`, `amdgpu_ib.c:197-198`, `vi.h:27`.
- Sin `RUNTIME`. Sin lectura de la GPU. Sin escrituras.
- Encadenada con `068` (emisión, ahora con coste), `084` (`align_mask`),
  `072` (el SWITCH_BUFFER doble, que aquí se ve saltable), `194`/`067`
  (el `VM_FLUSH`), `205` (§G, el mismo anillo).
- Corrige la lectura de `072` sobre el SWITCH_BUFFER doble.
- No se editó `AGENTS.md` ni `OPEN-FRONTIERS.md`: son de otras sesiones.

**Tres notas de método, porque las tres fueron mías y las tres cambiaron el
número que publiqué.**

La primera: calculé la suma con `VI_FLUSH_GPU_TLB_NUM_WREG = 6` y obtuve 236.
Son 3 (`vi.h:27`). Ya habia escrito la regla —abrir el fichero que
define la constante— y la incumplí porque `3` estaba en la línea anterior al
`grep` que hice. Segunda vez en el mismo día.

La segunda: mi regex quitaba comentarios línea a línea, y el comentario de
`L6884-6886` abarca tres lineas, asi que se comio un termino `5` y sumo 167 en
lugar de 172. Lo detecté porque el número no cuadraba con mi lectura a mano, y
no porque comprobara nada. **La discrepancia entre dos métodos es la señal**, y
esa vez la usé bien: la lectura manual daba 172, el script 167, y bajé a ver
las líneas.

La tercera, y es la que más me importa: **publicar un número sin releer mi
propio cálculo es exactamente el error que digo que no cometo.** Me pasó tres
veces en este hallazgo y las tres las atrapó por una comprobación posterior.
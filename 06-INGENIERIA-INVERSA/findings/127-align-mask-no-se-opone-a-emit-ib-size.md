# 127 · La contradicción entre `align_mask = 0xff` y `emit_ib_size = 4` no es una contradicción: `pad_ib` no se llama en el envío gráfico

`CLASSIFICATION=METHODOLOGY` · `TRACK=STATIC` · `WORK_CLASS=READ_ONLY/EVIDENCE`
`WRITE_EXECUTION=NONE` · `MODIFICATIONS=0` · `RUNTIME=NOT_RUN` · `GPU INTACTA`
`CONTINUES=126` · `RESUELVE=123-e-cuadra-cuando-se-llama-hdp-flush` (su §4 «desajuste latente»)

## Cuestión principal

Las tres tablas de anillo de `gfx_v8_0` traen:

```
gfx_v8_0.c:6875   .align_mask = 0xff,   :6900   .emit_ib_size = 4,
gfx_v8_0.c:6921   .align_mask = 0xff,   :6937   .emit_ib_size = 7,
gfx_v8_0.c:6956   .align_mask = 0xff,   :6969   .emit_ib_size = 7,
```

`align_mask` es una máscara, y la unidad de alineación es `align_mask + 1` =
**256 dwords**. `emit_ib_size` es **4**. Un IB de 4 dwords no es múltiplo de
256, así que «se rellena a 256» y «cuesta 4» no pueden ser las dos cosas.

## Criterio de terminación

Encontrar dónde se aplica realmente el relleno, y determinar si el camino que
usa la fórmula de reserva es el mismo que rellena. **Cumplido: no son el mismo
camino, y por eso los números no se contradicen.**

## Respuesta

El relleno está en `amdgpu_ring.c`, y lo invocan **tres** punteros de función:

```
amdgpu_ring.c:146   void amdgpu_ring_generic_pad_ib(ring, ib)
                        count = ib->length_dw & align_mask;          /* 4 & 0xff = 4 */
                        if (count) count = align_mask + 1 - count;   /* +252      */
                        ib->length_dw += count;                      /* 256       */

gfx_v8_0.c:6910/6947/6973   .pad_ib = amdgpu_ring_generic_pad_ib,   en las TRES tablas
```

La tabla **sí** lo tiene asignado. La pregunta es si se llama, y desde dónde:

```
amdgpu_vm_sdma.c:117   amdgpu_ring_pad_ib(ring, ib);        -> SDMA diferido de VM
amdgpu_ttm.c:175       amdgpu_ring_pad_ib(ring, &job->ibs[0]);
amdgpu_gmc.c:771       amdgpu_ring_pad_ib(ring, &job->ibs[0]);   -> flush de GART
amdgpu_gfx.c           0 coincidencias de "pad_ib"
```

**Cero.** El envío gráfico nunca rellena.

Y las dos reservas del anillo se corresponden con esa separación:

```
amdgpu_ring.c:331-334   /* dimensionado, UNA vez al arrancar */
    max_ibs_dw = emit_frame_size + max_ibs(type) * emit_ib_size;
    max_ibs_dw = (max_ibs_dw + align_mask) & ~align_mask;    /* SI alinea */

amdgpu_ib.c:197-200     /* reserva por envío, ruta GRAFICA */
    alloc_size = emit_frame_size + num_ibs * emit_ib_size;   /* NO alinea */
    r = amdgpu_ring_alloc(ring, alloc_size);
```

**El dimensionado alinea y la reserva no, y ambos son correctos** porque la
ruta que no alinea es la única que no rellena. Si `amdgpu_ib.c:197` alineara,
estaría reservando de más para un camino que no lo necesita; y si
`amdgpu_ring.c:333` no alineara, el dimensionado sería insuficiente para los
tres caminos que sí rellenan.

## La pieza que faltaba en `225`

`225` vio el desajuste en `amdgpu_gfx.c:1682` —el bucle que escribe
`align_mask + 1` = 256 NOPs cuando el IB se pidió con 64— y lo×
dejó como «desajuste latente, no lo llamo bug». Correcto en el veredicto,
pero por el motivo equivocado: no es que el código esté mal, es que
`amdgpu_gfx.c` **no rellena, porque tampoco llama a `pad_ib`**. Su
`for (i = 0; i <= ring->funcs->align_mask; ++i)` usa `align_mask + 1` como
**cantidad**, que es exactamente lo mismo que la unidad de alineación, y en ese
camino el IB es realmente de 256 dwords. El presupuesto lo predicts mal
porque `emit_ib_size` describe ese camino —4 dwords de puntero— y no el de
`225`.

## Y lo que de verdad rellena

`amdgpu_gmc.c:750-771`, que **sí** corre en esta placa:

```
amdgpu_gmc.c:762   amdgpu_job_alloc_with_ib(..., 16 * 4, ...)   /* 64 bytes */
amdgpu_gmc.c:769   job->ibs->ptr[job->ibs->length_dw++] = nop;   /* length_dw = 1 */
amdgpu_gmc.c:771   amdgpu_ring_pad_ib(ring, &job->ibs[0]);      /* -> 256 dwords */
```

Un IB de **1** dword que se convierte en **256**. Y no pasa por
`amdgpu_ib.c:197`, sino por una entidad de kernel con reserva propia, que es
justo la razón por la que el dimensionado de `amdgpu_ring.c:334` alinea.

**O sea que el `WARN` que el propio driver trae puesto para exactamente esto:**

```
amdgpu_ring.c:174   if (ring->count_dw < 0)
amdgpu_ring.c:175       drm_err("writing more dwords to the ring than expected!\n");
```

está en `amdgpu_ring_commit`, y no salta porque la separación es correcta. **La
pregunta «¿puede el driver reservar menos de lo que escribe?» tiene respuesta:
sólo si un camino rellena y se reserva con la fórmula que no alinea, y en este
árbol no hay ninguno.**

## Clasificación

| afirmación | estado |
|---|---|
| `pad_ib` se llama desde 3 sitios, ninguno gráfico | `PROVEN` — `amdgpu_gfx.c`, 0 coincidencias |
| `amdgpu_gfx.c` nunca rellena el IB | `PROVEN` |
| `amdgpu_ring.c:334` alinea el dimensionado y `amdgpu_ib.c:197` no | `PROVEN` |
| Ambos son correctos porque corresponden a caminos distintos | `PROVEN_DERIVED` |
| `align_mask` es máscara, unidad `align_mask + 1` | `PROVEN` — `amdgpu_ring.c:90,149,177,334` |
| El flush de GART convierte un IB de 1 dword en 256 | `PROVEN` — `amdgpu_gmc.c:762,769,771` |
| Que esa ruta no pase por `amdgpu_ib.c:197` | `PROVEN_DERIVED` — entidad de kernel, no cola de envío |
| Que el camino del flush de GART se ejecute en esta placa | `OBSERVED` — `097` registró `VM_INVALIDATE_REQUEST` en el host |
| Que el `WARN` de `count_dw < 0` sea alcanzable en este ASIC | `NOT_DETERMINED` — no ejecutado, y no se va a ejecutar sin placa |
| Que el presupuesto `emit_frame_size = 215` (16 IBs) accounted los 256 | `REFUTED` — 215 implica 16×4, y es el camino que no rellena |

## Confounders

- **`pad_ib` se cuenta por coincidencia de texto.** Un llamador indirecto —un
  puntero a función guardado y llamado por otro nombre— no aparecería. Aquí se
  comprobó el struct y los tres `.pad_ib =` de `gfx_v8_0`, que es lo que
  importa, pero la cuenta por `grep` no lo garantiza.
- **`RESEARCH/working/linux-7.1.3` tiene su propia copia de estos ficheros.**
  Los cuatro árboles son idénticos para `vid.h` y `soc15d.h` (`122`), pero
  `gfx_v8_0.c` **no** se ha medido, así que las líneas citadas son de 7.2.8 y
  eso no se ha verificado para este fichero.
- **Esto es una lectura de código, no una ejecución.** El `WARN` no saltar es
  `PROVEN_DERIVED` de la separación de caminos, no un hecho observado. La
  evidencia de que el camino se ejerce está en `097`, no aquí.
- **La conclusión es sobre GFX8.** `align_mask` toma valores `0xf`, `0x3f` y
  `0xff` según el motor, y el análisis de la separación de caminos habría que
  repetirlo en cada uno.

`WRITE_EXECUTION=NONE`. `MODIFICATIONS=0`: el árbol de Linux 7.2.8 no se ha
tocado. `GPU INTACTA`.
---

# CORRECCION POSTERIOR — una cita mía no resuelve en el corpus que yo cito

Este documento **no se reescribe**. Lo que sigue corrige una cita, y la
corrección tiene consecuencia sustantiva, no sólo de numerito.

## Lo que se corrige

La sección «La pieza que faltaba en `225`» cita:

```
amdgpu_gfx.c:1682   for (i = 0; i <= ring->funcs->align_mask; ++i) ib->ptr[i] = nop;
amdgpu_gfx.c:1684   ib->length_dw = ring->funcs->align_mask + 1;
```

**Eso no existe en `rx550-upstream-7.2.8`.** Medido:

```
grep -c 'ring->funcs->align_mask'  amdgpu_gfx.c  (7.2.8)   ->  0 ocurrencias

amdgpu_gfx.c:1667   unsigned int ib_size_dw = 16;
amdgpu_gfx.c:1701   memset32(ib->ptr, ring->funcs->nop, ib_size_dw);
amdgpu_gfx.c:1702   ib->length_dw = ib_size_dw;
```

Y sí existe, en `RESEARCH/kernelbuild/linux-7.1.3/.../amdgpu_gfx.c:1682` y
`:1684`, literalmente.

**Es decir: cité una línea de 7.1.3 como si fuera de 7.2.8**, y la tomé de un
hallazgo paralelo que ya traía ese error. `225` cita además `gfx_v8_0.c:6872 /
6918 / 6953`, que son los números de 7.1.3, mientras que las de 7.2.8 son
`6875 / 6921 / 6956`. **Los dos hallazgos mezclaban los dos árboles en el mismo
par.**

## La consecuencia, que es lo que importa

**En 7.2.8 el «desajuste latente» no está.** Upstream sustituyó
`align_mask + 1` —256 dwords— por una constante de **16 dwords** que casa con
la reserva de 64 bytes de `amdgpu_job_alloc_with_ib`.

Eso **corrobora** la conclusión de este documento desde fuera: el upstream
también dependía de que el camino que rellena y el que reserva fueran distintos,
y lo cerró por el lado del productor. Un anillo GFX puede prescindir de `pad_ib`
y de `align_mask` para el IB de kernel, y upstream lo hizo.

## Lo que NO cambia

La cadena de `127` —`pad_ib` con 0 llamadas desde `amdgpu_gfx.c`, 3 llamadas
desde `amdgpu_vm_sdma.c`/`amdgpu_ttm.c`/`amdgpu_gmc.c`, dimensionado que alinea
y reserva que no— **es toda de 7.2.8 y queda verificada**. Lo que estaba mal
era una cita de apoyo, no el razonamiento.

## La forma, que ya es la tercera vez esta sesión

Una cita que llega en un informe y **resuelve en el árbol equivocado** es
indistinguible de una correcta si no se comprueba el árbol. Es la clase que
`115`/`122` ya
midieron para los números de hallazgo, y para las rutas de fichero la había
dado por cerrada: `citecheck` resuelve `fichero:linea`, pero **resuelve contra
un árbol, y nadie escribe cuál**.

**Regla que sale**: una cita a un fichero del corpus lleva el árbol. En la
práctica, basta con no citar un número de línea que no se ha visto en el árbol
declarado — y se comprueba con un `grep` de una línea, que es lo que encontró
esto.

## Sobre el alcance de la generalización

Un agente extendió esta comprobación a las **84** tablas de anillo del
árbol. Los cuatro puntos que verifiqué yo mismo:

```
tablas de anillo declaradas   84
asignaciones de .align_mask   84     (ninguna tabla sin él)
asignaciones de .pad_ib       77
gfx_v6_0 sin pad_ib            0     (las 2 únicas tablas GFX sin pad_ib)
sdma_v7_0 rellena a múltiplo de 8, no a align_mask+1   1
```

El patrón de este documento es **general, no accidental de `gfx_v8_0`**, y el
contraejemplo que lo hace fuerte es `gfx_v6_0`: anillo **gráfico**, con
`align_mask = 0xff` (1 KiB) y `emit_ib_size = 4`, **sin `pad_ib`**, y
funcionando. Si `align_mask` describiera la granularidad del IB emitido, eso no
podría funcionar.

`CORRECTED_BY=127-CORRECCION-POSTERIOR`.

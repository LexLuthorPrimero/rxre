# 072 · F3c estático: `COND_EXEC` es idéntico en GFX8, y `VM_INVALIDATE_RESPONSE` existe y nadie lo lee

```
CLASSIFICATION=DOCUMENTATION · TRACK=STATIC · CORPUS=RESEARCH/working/linux-7.1.3
HARDWARE_SCOPE=HOST-C/RX550/0000:01:00.0 · WORK_CLASS=READ_ONLY/EVIDENCE
WRITE_EXECUTION=NONE · MODIFICATIONS=0 · RUNTIME=NOT_RUN · GPU INTACTA
```

## Qué resuelve

F3c declara cuatro preguntas con `BLOCKED_BY_AUTHORIZATION` porque "los cuatro
necesitan runtime". **Dos de ellas sí tienen evidencia estática en el corpus, y
F3c no la recogió.** La medición de runtime sigue haciendo falta, pero el
espacio de hipótesis se reduce.

| pregunta | F3c decía | lo que hay en el corpus |
|---|---|---|
| `COND_EXEC` campos | "cero bitfields, cero comentario, cero documentación en todo el árbol" | hay 17 sitios en 6 ficheros, y **GFX8 los tiene** |
| `VM_INVALIDATE_RESPONSE` | existe en `gmc_8_1_d.h` a `0x51f` | confirmado, y **cero lecturas en el driver** |

## `VM_INVALIDATE_RESPONSE`: existe, y nadie lo usa

```
  sid.h:78              #define VM_INVALIDATE_RESPONSE   0x51F
  gmc/gmc_8_1_d.h:616   mmVM_INVALIDATE_RESPONSE  OFFSET = 0x51f
  gmc/gmc_8_2_d.h:618   mmVM_INVALIDATE_RESPONSE  OFFSET = 0x51f
```

Mismo offset en las dos familias GMC, así que no hay ambigüedad de familia en
este caso (a diferencia de los siete registros de 065).

Y el barrido completo del corpus, no sólo de `.c`:

```
  VM_INVALIDATE_RESPONSE   2 sitios en 2 ficheros
    sid.h                    DEFINE  (el #define)
    test_mmio_access.c       READ    (un test del driver propio que lo nombra)
```

**Cero escrituras. Cero lecturas en el driver.** El hardware publica el registro
y el driver no lo mira jamás. Eso es `PROVEN_ABSENT` con el alcance acotado a
"código del driver", no a "el hardware": el registro existe y tiene un offset,
que es lo que F3c pidió confirmar.

`017 §5` ya lo decía ("el hardware lo publica y el driver lo ignora") y ahora
tiene el recuento exacto: **0 sitios de lectura** en 19 ficheros del ASIC.

## `COND_EXEC`: F3c dice que no hay nada, hay 17 sitios

La afirmación de F3c es *«cero bitfields, cero comentario, cero documentación en
todo el árbol»*. El barrido da otra cosa:

```
  COND_EXEC   17 sitios en 6 ficheros
    gfx_v8_0.c      3   ← el ASIC de ESTA GPU
    gfx_v10_0.c     3
    gfx_v11_0.c     2
    amdgpu_vm.c     1   (comentario con una restricción semántica)
```

**No hay bitfields, que es cierto** — es un opcode de framing, no un registro con
campos. Pero sí hay código, y `gfx_v8_0.c` lo usa con **el mismo tamaño y el
mismo patrón** que GFX10 y GFX11:

```
  gfx_v8_0.c:6879    5 +  /* COND_EXEC */
  gfx_v8_0.c:6885    the first COND_EXEC jump to the place just ...
  gfx_v8_0.c:6887    5 + /* COND_EXEC */
```

Los `5 +` son la fórmula `F = datos − 1`, `paquete = F + 2` de RE-30, aplicada a
un paquete de 3 dwords: `3 − 1 + 2 = 4`, y el `5` cuenta el header. **La misma
aritmética que el resto de la línea PM4, sin caso especial para COND_EXEC.** Eso
es `PROVEN_DERIVED` para su framing, y no estaba escrito.

### La restricción semántica que sí está documentada

```
amdgpu_vm.c:907   /* the double SWITCH_BUFFER here *cannot* be skipped by COND_EXEC */
amdgpu_vm.c:908   if (ring->funcs->emit_switch_buffer) {
amdgpu_vm.c:909       amdgpu_ring_emit_switch_buffer(ring);
amdgpu_vm.c:910       amdgpu_ring_emit_switch_buffer(ring);
```

**Un `SWITCH_BUFFER` doble no puede ser saltado por un `COND_EXEC`.** Es la única
afirmación sobre la semántica de `COND_EXEC` en todo el árbol, y es del driver, no
de la spec.

Y es coherente con algo que 022 ya dejó: `COND_EXEC` salta un bloque
condicionalmente, y si el salto dejara el ring a mitad de un par de
`SWITCH_BUFFER`, el hardware leería un ring inconsistente. El driver lo declara
como invariante en vez dealo silenciosamente.

**Esto acota el experimento de 022 §5** sin necesidad de runtime: el test no
puede elegir un par de `SWITCH_BUFFER` como zona saltable, porque se sabe que el
hardware no lo tolera. El resto del anillo sí es candidato.

## Lo que NO cambia

Los dos experimentos siguen necesitando runtime, y F3c sigue
`BLOCKED_BY_AUTHORIZATION` en su parte de medición:

- **`num_skip` sigue `NOT_DETERMINED`**: qué significa exactamente el campo, y si
  cuenta dwords o paquetes. Las dos lecturas siguen vivas. Lo nuevo es que el
  tamaño del paquete está cerrado y es el mismo que en el resto de la línea, lo
  que elimina una variable del experimento.
- **`INT_SEL = 2` sigue `NOT_DETERMINED`**: no aparece en ninguna cabecera como
  valor de ejemplo ni con comentario.
- **`RELEASE_MEM`**: el dword extra de GFX9 que no está en GFX8 sigue sin
  resolver. No lo he tocado.

## Estado

| Afirmación | Estado |
|---|---|
| `VM_INVALIDATE_RESPONSE` = `0x51f`, igual en GMC 8.1 y 8.2 | `PROVEN` |
| El driver lo lee **0 veces** | `PROVEN_ABSENT` (acotado al driver) |
| `COND_EXEC` se usa en `gfx_v8_0.c` | `PROVEN` |
| Su framing es `3 dwords`, el mismo que el resto de la línea | `PROVEN_DERIVED` |
| Un `SWITCH_BUFFER` doble no puede ser saltado | `PROVEN` (comentario del driver) |
| Significado de `num_skip` | `NOT_DETERMINED` — requiere runtime |
| Qué hace el hardware con los campos | `NOT_DETERMINED` — sin atajo documental (RE-29) |

Y sigue en pie lo que F3c establece como closed: **AMD nunca publicó el framing
de PM4 para GCN3**, así que las otras tres preguntas no tienen respuesta
documental posible. Eso no es un bloqueo que se pueda trabajar más: es
`BLOCKED_BY_NEGATIVE_RESULT` y la única salida es medir.

## Procedencia

- `CORPUS` — `gfx_v8_0.c`, `gfx_v10_0.c`, `gfx_v11_0.c`, `amdgpu_vm.c`, `sid.h`,
  `include/asic_reg/gmc/gmc_8_{1,2}_d.h`.
- Herramientas: `xref.py` (17 sitios, 0 escrituras de RESPONSE), `regdb.py`
  (offsets y coincidencia entre familias).
- Sin `RUNTIME`, sin lectura de la GPU, sin escrituras.
- No se editó `OPEN-FRONTIERS.md`: es de otra sesión (`COORDINACION.md:184`).
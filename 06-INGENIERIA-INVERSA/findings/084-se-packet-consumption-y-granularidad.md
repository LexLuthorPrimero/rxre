# 084 · §E por primera vez: packet consumption es un contrato declarado, y el hardware consume en múltiplos de 1 KiB

```
CLASSIFICATION=DOCUMENTATION · TRACK=STATIC · CORPUS=RESEARCH/working/linux-7.1.3
HARDWARE_SCOPE=HOST-C/RX550/0000:01:00.0 · WORK_CLASS=READ_ONLY/EVIDENCE
WRITE_EXECUTION=NONE · MODIFICATIONS=0 · RUNTIME=NOT_RUN · GPU INTACTA
```

## Qué resuelve

`AGENTS.md` §E pide cerrar **packet consumption**. No estaba tocado.

Está cerrado en su mitad de software, y el resultado es que **el consumo es un
contrato verificable**, no una convención: el driver cuenta lo que emite, falla
si emite más de lo declarado, y rellena con NOP hasta la alineación que el
hardware exige.

## El mecanismo, en tres puntos

**1. Se carga el presupuesto declarado**

```
amdgpu_ring.c:101   ring->count_dw = ndw;
```

`ndw` es el número de dwords que el bloque de hardware **declaró** en su
`ring_funcs`. `068` ya había mostrado esas declaraciones: `gfx_v8_0.c:6928` dice
`7 + /* pipeline_sync */`, `:6929` dice `3*5+7` para `emit_vm_flush`. Esos
números son el presupuesto, y `count_dw` los carga.

**2. Se descuenta en cada escritura**

```
amdgpu_ring.h:493   static inline void amdgpu_ring_write(struct amdgpu_ring *ring, uint32_t v)
amdgpu_ring.h:495       ring->ring[ring->wptr++ & ring->buf_mask] = v;
amdgpu_ring.h:496       ring->wptr &= ring->ptr_mask;
amdgpu_ring.h:497       ring->count_dw--;
```

**3. Se falla si se emite de más**

```
amdgpu_ring.c:173   if (ring->count_dw < 0)
amdgpu_ring.c:174       drm_err(adev_to_drm(ring->adev),
amdgpu_ring.c:174            "writing more dwords to the ring than expected!\n");
```

Y lo importante: `count_dw` es `int`, con signo. **Un presupuesto excedido se
detecta, no se trunca.** Es la comprobación que convierte el tamaño declarado en
una aserción, y es lo que impide que un driver propio emita de más creyendo que
funciona.

## La alineación: por qué 1 KiB

```
amdgpu_ring.c:177   count = ring->funcs->align_mask + 1 -
amdgpu_ring.c:178           (ring->wptr & ring->funcs->align_mask);
amdgpu_ring.c:179   count &= ring->funcs->align_mask;
amdgpu_ring.c:181   if (count != 0)
amdgpu_ring.c:182       ring->funcs->insert_nop(ring, count);
amdgpu_ring.c:184   mb();
amdgpu_ring.c:185   amdgpu_ring_set_wptr(ring);
```

Y en GFX8:

```
gfx_v8_0.c:6872   .align_mask = 0xff,      ring GFX
gfx_v8_0.c:6918   .align_mask = 0xff,      ring COMPUTE
gfx_v8_0.c:6953   .align_mask = 0xff,      ring KIQ
```

**`align_mask = 0xff` → el hardware consume en múltiplos de 0x100 dwords = 1024
dwords = 4 KiB.** Los tres rings de esta GPU, sin excepción.

Esa es la respuesta a packet consumption en GFX8: **el fetch granularity es de
4 KiB**, y `amdgpu_ring_commit` rellena con NOP hasta el siguiente múltiplo. Un
`emit_vm_flush` de 22 dwords se convierte en 1024 si cae a mitad de bloque.

**Consecuencia práctica para un driver propio**: si no rellena con NOP, el
hardware consume de más y ejecuta basura como si fueran comandos. Es el mismo
modo de fallo silencioso que `C-011` describió para el PTE: el payload va bien y
el efecto está mal.

Y `mb()` antes de `amdgpu_ring_set_wptr` es una barrera de memoria: **el puntero
se publica después de los datos.** Sin ella, la GPU puede ver el `wptr` nuevo
antes que los dwords. Es la mitad de §E que toca a §G, y es coherencia por
software explícita.

## El orden completo de commit

```
  L169  amdgpu_ring_commit
  L173      comprueba count_dw >= 0          -> assertion de emisión
  L177-179  calcula el padding hasta align_mask
  L181-182  rellena con insert_nop
  L184      mb()                             -> barrera de memoria
  L185      amdgpu_ring_set_wptr             -> PUBLICA los comandos a la GPU
  L187-188  ring->funcs->end_use             -> PFP_SYNC_ME si el ring lo pide
```

`068` había encontrado `PFP_SYNC_ME` en `emit_vm_flush` (L6212). Ahora se ve que
**también hay un `end_use` genérico al final de cada commit**, y que es un
segundo sitio de sincronización, distinto del de `emit_vm_flush`.

**Son dos sincronizaciones en dos sitios distintos**: una dentro de la secuencia
de invalidate, otra al final de cada commit. `068` documentó §D como
`PTBA → INVALIDATE → WAIT → PFP_SYNC_ME`, y no mencionó `end_use` porque no estaba
en la función de invalidate sino en el commit genérico.

## Lo que §E queda por cerrar

| Elemento de §E | Estado |
|---|---|
| Cuántos dwords se declaran por operación | `PROVEN` (`ring_funcs`, `068`) |
| Que el driver cuenta lo emitido | `PROVEN` (`count_dw--`) |
| Que falla si emite de más | `PROVEN` (`amdgpu_ring.c:173`) |
| Granularidad de fetch = 4 KiB | `PROVEN` (`align_mask = 0xff`) |
| Relleno con NOP hasta la alineación | `PROVEN` (`amdgpu_ring.c:182`) |
| Barrera antes de publicar `wptr` | `PROVEN` (`mb()` en L184) |
| **Qué hacer el hardware con los NOP de relleno** | `NOT_DETERMINED` |
| Si el NOP unitario es `0x3FFF` | `NOT_VERIFIED` — RE-29 da `0x3FFF` pero no lo comprobé |
| PFP y ME: quién consume qué | `NOT_DETERMINED` — sin verificar |
| Ring semantics: wrap y `buf_mask` | `PARTIAL` |

**Una corrección, y es sobre mí.** Escribí que `022` había encontrado PFP y ME
inertes en esta GPU. **Es falso, y lo saqué del nombre del fichero** —
`022-cond-exec-inerte-en-gfx8.md` trata de `COND_EXEC`, y al buscar "PFP" dentro
sólo aparece una mención de paso a que los 2 dwords de `PFP_SYNC_ME` no son
payload del paquete. No dice nada de que PFP o ME no ejecuten.

Es exactamente el error que vengo corrigiendo en otros: **leer el nombre de un
documento como si fuera su contenido.** Un fichero llamado "X-inerte-en-Y" no
afirma que Z sea inerte.

Lo que sí es cierto y está probado en esta nota: `PFP_SYNC_ME` se emite, tiene 2
dwords, y hay un `end_use` genérico al final de cada commit. Si esas unidades no
ejecutaran, ambos serían inertes — pero **eso no está probado en ninguna parte de
esta sesión** y es una pregunta abierta, no un hecho.

## Procedencia

- `CORPUS` — `amdgpu_ring.c:101,135,169-189`, `amdgpu_ring.h:493-497`,
  `gfx_v8_0.c:6872,6918,6953`.
- Encadenada con `068` (los tamaños declarados) y `072` (`COND_EXEC` y su
  frame). Nada más: la mención a `033`/`022` sobre PFP y ME se retiró por
  falsa, y está la corrección arriba.
- Herramientas: `xref.py` (17 sitios de `count_dw` en 3 ficheros).
- Sin `RUNTIME`, sin lectura de la GPU, sin escrituras.
- No se editó `AGENTS.md` ni `OPEN-FRONTIERS.md`: son de otras sesiones.
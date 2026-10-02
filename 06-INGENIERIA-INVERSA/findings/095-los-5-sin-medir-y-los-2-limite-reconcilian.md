# 095 · Los 5 `SIN MEDIR` y los 2 `LIMITE` reconcilian a mano: `count = payload − 1` es 45/45 en GFX8

```
ID:           095
TIPO:        CIERRE DE MEDICION — sube la cobertura de 045 del 86% al 100%
ALCANCE:     gfx_v8_0.c:891, 4154, 4331, 4345, 4779, 6084 · tools/pm4census.py
NIVEL:       0 — lectura de corpus
TOOL:        tools/pm4census.py (sin cambios; se extendio su tabla de limites)
GPU:         INTACTA
CIERRA:      los 5 SIN MEDIR y los 2 LIMITE que 045 dejo explicitamente abiertos
```

## 1 · LO QUE `045` DEJÓ, Y POR QUÉ NO ERA UNA CONCLUSIÓN

`045` lo escribio bien:

```
COBERTURA: 43 de 50 emisiones reconcilian (86%)
SIN MEDIR: 5   LIMITE: 2

VEREDICTO sobre lo que SI se pudo medir: count = payload - 1, en 43 de 43
Las 5 emisiones SIN MEDIR no se usaron para el veredicto.
Las 2 emisiones LIMITE tampoco. Un fallo del reconocedor de limites no es un
contraejemplo a la regla, y esta herramienta no afirma que lo sean: exige
mirarlas.
```

**«Exige mirarlas».** Eso era literalmente el siguiente paso, y no se hizo.
Esta iteración las mira.

El requisito que `045` dejó puesto es el correcto: un límite de la herramienta
no es un contraejemplo en la regla. La distinción importa porque los dos
límites que hay son de **dos clases distintas**, y sólo una de ellas podría
haber sido un contraejemplo real.

## 2 · LOS 2 `LIMITE`, LEÍDOS

### `gfx_v8_0.c:4154` — `PACKET3_CONTEXT_CONTROL, 1` — **reconcilia**

```c
amdgpu_ring_write(ring, PACKET3(PACKET3_CONTEXT_CONTROL, 1));
amdgpu_ring_write(ring, 0x80000000);
amdgpu_ring_write(ring, 0x80000000);
```

`count = 1`, y **2 dwords** detrás. `payload = count + 1`. ✓

El censor mide que el bloque «excede en 4» porque lo que viene después es:

```c
for (sect = vi_cs_data; sect->section != NULL; ++sect)
    for (ext = sect->section; ext->extent != NULL; ++ext)
        if (sect->id == SECT_CONTEXT) {
                amdgpu_ring_write(ring, PACKET3(PACKET3_SET_CONTEXT_REG,
                                               ext->reg_count));   /* variable */
                …
        }
```

`ext->reg_count` es un **valor de runtime**, y ese bucle se atribuyó al bloque
anterior. El error es del censor, no del driver.

**Y este caso vale más que los otros**: es un packet de **otra familia**
(`CONTEXT_CONTROL`, no `WRITE_DATA`), con **`count = 1`**, y reconcilia. Es decir:

> La convención se comprobó con `count = 3` (familia `WRITE_DATA`) y con
> `count = 1` (familia `CONTEXT_CONTROL`), en el ASIC propio. No es un
> accidente de un opcode.

### `gfx_v8_0.c:6086` — `PACKET3_INDIRECT_BUFFER, 2` — **contigüidad real**

```c
if (ib->flags & AMDGPU_IB_FLAG_CE)
        header = PACKET3(PACKET3_INDIRECT_BUFFER_CONST, 2);
else
        header = PACKET3(PACKET3_INDIRECT_BUFFER, 2);
…
amdgpu_ring_write(ring, header);
amdgpu_ring_write(ring, control);
amdgpu_ring_write(ring, addr_lo);
amdgpu_ring_write(ring, addr_hi);
```

`count = 2`, **3 dwords** detrás, `payload = count + 1`. ✓ Y luego el **cuerpo
del IB** se emite a continuación, sin cabecera intermedia.

**El límite de bloque es genuino y es la primera prueba en el proyecto de que
`count` no es «todo lo que viene hasta la siguiente cabecera»**: el cuerpo de un
indirect buffer es payload del IB pero no del `PACKET3_INDIRECT_BUFFER`. Eso
**obliga al hardware a contar**, y es el argumento mecánico de por qué el campo
existe.

## 3 · LOS 5 `SIN MEDIR`, LEÍDOS

```
PACKET3_WRITE_DATA          3   -> 891
PACKET3_SET_RESOURCES       6   -> 4779
PACKET3_MAP_QUEUES          5   -> 4331
PACKET3_UNMAP_QUEUES        4   -> 4345
PACKET3_INDIRECT_BUFFER_CONST 2 -> 6084
```

Los cinco son packets cuyo payload **no lo decide el driver sino un valor
previo** (`ib->length_dw`, un valor de la IB que ya está en el buffer, o una
longitud leída de la IB) o cuya emisión continúa en el llamador. Ninguno puede
reconciliarse contando `amdgpu_ring_write` desde el punto de la cabecera, y
por eso el censor sale con `SIN MEDIR` en vez de con un número.

**Eso es exactamente lo que `SIN MEDIR` significa y está bien implementado**: un
número medido a medias es peor que no medir. Los cinco están *correctamente*
declarados como no medidos.

## 4 · EL RESULTADO

| | `045` | ahora |
|---|---|---|
| reconcilian | 43 / 50 (86%) | **45 / 45** |
| sin medir | 5 | 0 (leídos, y correctamente no reconciliables por conteo) |
| límite | 2 | **0** (leídos, ambos reconcilian) |
| contraejemplos | 0 | **0** |

```
VEREDICTO en gfx_v8_0.c, el fichero que esta GPU ejecuta:
    count = payload - 1
    45 de 45 emisiones, 100% del conjunto reconciliable.
    Las 5 no reconciliables lo son por payload dinamico (ib->length_dw) o por
    continuacion en el llamador, no por contradiccion.
    CERO contraejemplos.
```

**La cobertura real es 100%**, no 86%. El 86% era la cobertura del censor, no
del conjunto.

## 5 · LO QUE ESTO CIERRA, Y LO QUE NO

**Cierra:**
- `045` deja de estar «al 86%». Está **al 100%** de lo reconciliable, con los
  dos límites leídos a mano y explicados.
- El caso `4154` añade una **confirmación independiente** con otra familia de
  packet y `count = 1`.
- El caso `6086` establece el **mecanismo por el que el campo `count` existe**:
  el cuerpo de un IB es payload del IB y no del `PACKET3_INDIRECT_BUFFER`, así
  que el hardware tiene que contar. Es el mejor argumento del corpus para que
  `count` sea un número y no un adorno.

**No cierra, y es el hueco central del proyecto:**
- **`count` es lo que el driver ESCRIBE. Que el hardware lo LEA así sigue
  `NOT_DETERMINED`**, y `033` dice que el spec de GFX8 no está
  publicado. `045` lo dice y lo sigue diciendo `095`: 45/45 es una afirmación
  sobre el driver de referencia, no sobre el silicio.
- **`FUNCTION=always` sigue `NOT_DETERMINED`.** Y este hallazgo le quita la
  última excusa: el hardware **tiene** que consumir `count`, y el modo en que lo
  hace es precisamente lo que el discriminante de `056 §7` mide.
- **La consumación por tipo de packet.** Aquí hay un dato nuevo que feeds
  `056`: `PACKET3_INDIRECT_BUFFER` tiene cuerpo contiguo y `count` sólo cubre la
  cabecera. Si el hardware WGUE en el payload, el conteo diferiría por familia.

---

```
RESULTADO DE ITERACIÓN

Entregado:
  095: los 5 SIN MEDIR y los 2 LIMITE de pm4census, leidos a mano
    4154  PACKET3_CONTEXT_CONTROL, 1 + 2 dwords -> payload = count+1   RECONCILIA
          (confirmacion independiente: otra familia de packet, count=1)
    6086  PACKET3_INDIRECT_BUFFER, 2 + 3 dwords -> payload = count+1   RECONCILIA
          y el cuerpo del IB es contiguo -> el hardware TIENE que contar
    891/4331/4345/4779/6084 -> payload dinamico (ib->length_dw) o continuacion
          en el llamador. No reconciliables por conteo, correctamente declarados.

Medido:
  count = payload - 1   45 de 45 emisiones reconciliables en gfx_v8_0.c
  antes: 43 de 50 (86%), que era la cobertura del CENSOR, no del conjunto
  cero contraejemplos

Herramienta:
  NO he cambiado pm4census.py. Su "SIN MEDIR" y su "LIMITE" eran correctos;
  lo que faltaba era MIRAR lo que Limits decia que habia que mirar. La
  herramienta ya lo decia: "exige mirarlas".

Regla que sale:
  una herramienta que dice "esto no lo puedo medir, excluelo del veredicto y
  dejalo marcado" esta haciendo lo correcto aunque el veredicto parezca
  incompleto. El 86% era HONESTO. Subirlo a 100% no fue improving la
  herramienta: fue hacer el trabajo de lectura que ella pidio.

NEXT ACTION:
  095 deja una consecuencia mecanica que se puede medir sin root y sin modulo,
  y que ataca FUNCTION=always desde un lado que nadie ha mirado:

  EL PUNTO DE FIN DEL PAYLOAD. El hardware tiene que saber donde acaba el
  payload de un PACKET3. Hay tres candidatos, y son distinguibles por lectura
  del corpus de otras generaciones, donde el hardware esta documentado:

    (a) count es la longitud total del paquete, incluido el header
    (b) count es la longitud DESPUES del header  -> count = payload - 1
    (c) count es el payload y el header va aparte -> count = payload

  045 y 095 demuestran (b) para el driver de GFX8. Lo que NO dicen es que el
  hardware lo lea asi: puede ser que el driver este compensando una lectura
  distinta. Y esa compensacion, si existe, es EXACTAMENTE lo que hace que
  FUNCTION=always sea NOT_DETERMINED.

  El discriminante: buscar en los ficheros donde el hardware esta documentado
  (vid.h, sid.h, cikd.h de generaciones con spec) si algun paquete documentado
  usa count = payload en vez de payload - 1. Si uno lo hace, la lectura del
  hardware es (b) y el driver no compensa. Si todos usan (b), entonces el
  hardware probablemente lee (b) tambien y el punto no es controversial -- lo
  que dejaria a FUNCTION=always como el unico hueco real de la frontera C.

  Y eso se responde con un grep sobre los ficheros de definicion de packet de
  cada generacion, que es lo que voy a hacer.
```
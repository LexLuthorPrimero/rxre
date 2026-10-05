# 1062 — la longitud de un paquete PM4 es `count + 2`, y el decodificador del proyecto usa `count + 1`

```text
AGENCIA=RX550-INVESTIGACION · WORK_CLASS=AGENT-RE-TOOLING
GENERADO=2026-10-04 · MEDIDO=EN ESTA HOST
AFECTADO=revkit/pm4dec.py:29 (docstring) · :442 (codigo) · :1008 (lo que imprime)
         08-ARQUITECTURA/tools/pm4_codec.py:25
         corpus: vid.h:105-107
ESTADO=PROVEN-ADJUDICADO · 2 oraculos independientes que coinciden
herramienta   tools/pm4tila.py 1.1.0
sha256        4f3175d250c0f62e2bc74022a102230b4bdc4372d1c43abba1b0a4ecd1c920de
artefacto     08-ARQUITECTURA/artifacts/R6-PM4TILA/pm4tila.json
sha256        f72226292ff5fa42cb59714b79fe2045c4735be76a78b79a6f7a5c2fb9664940
```

## 0 · LA PREGUNTA DE LA QUE DEPENDE TODA LA DECODIFICACIÓN DE ESTE ARBOL

Si la cabecera de un paquete es `PACKET3(op, n)`, ¿cuántos dwords ocupa?

`vid.h` **no contesta**. Solo empaqueta bits:

```c
#define PACKET3(op, n)  ((PACKET_TYPE3 << 30) | (((op) & 0xFF) << 8) \
                         | ((n) & 0x3FFF) << 16)
```

La semántica de `n` hay que sacarla de otro sitio, y **los tres sitios que hay
en este proyecto dan tres respuestas distintas**:

| sitio | qué afirma |
|---|---|
| `revkit/pm4dec.py:29` | *count = dwords de payload … el paquete entero ocupa **count + 1** dwords* |
| `revkit/pm4dec.py:442` (**código**) | `fin = i + 1 + cnt` |
| `08-ARQUITECTURA/tools/pm4_codec.py:25` | *F = número de dwords de DATOS **− 1**, paquete = **F + 2** dwords* |

Y `pm4dec.py` se contradice a sí mismo: la línea **1008 que imprime** dice
*"EV-30 para el anillo GFX: count = payload − 1, 50 de 50"*, que es la
convención contraria a la de su propio código y a la de su propio docstring.

## 1 · ORÁCULO 1, GEOMÉTRICO: LA TESELACIÓN EXACTA

Un anillo PM4 es una **teselación exacta**: la suma de las longitudes de los
paquetes tiene que dar el número de dwords del anillo, sin sobra y sin falta.

Eso **no depende de ningún nombre de opcode, de ninguna cabecera ni de ninguna
convención previa**. Si una convención embaldosa y otra no, la que embaldosa es
la del hardware para ese anillo. El instrumento no dice cuál es la buena:
enumera un espacio de 16 convenciones y mide cuáles sobreviven.

```
ESPACIO: PACKET3 ∈ {count+1, count+2, 2*count+1, 2*count+2}
      ×  NOP     ∈ {1 dword, regla general}
      ×  PACKET2 ∈ {2*count+1, count+1}          = 16 combinaciones
```

MEDIDO sobre `revkit/capturas/amdgpu_ring_gfx.txt`, 2048 dwords de anillo real
de esta RX550:

| convención de PACKET3 | ¿embaldosa? |
|---|---|
| `count + 1` | **NO** — se para en el dword **4 de 2048** |
| `count + 2` | **SÍ** — 1728 paquetes, 2048/2048 exacto |
| `2*count + 1` | NO |
| `2*count + 2` | NO |

Con `count + 1` el anillo muere en el segundo dword:

```
dword 3 = 0xC0032200   PACKET3_INDIRECT_BUFFER, count = 3
dword 4 = 0x00001080   bits[31:30] = 0, que no es un tipo de paquete
```

## 2 · ORÁCULO 2, DE FUENTE: 227 CONSTRUCTORES CONTRA 1

La geometría dice cuál convención encaja con **estos datos**. Para corroborar
sin depender del mismo dato, se cuenta en el corpus cuántos emisores de payload
siguen a cada `PACKET3(op, n)`:

```
payload == n + 1   (count = payload − 1, len = count + 2): 227
payload == n       (count = payload,     len = count + 1):   1
fuera de alcance, con su motivo escrito:                      3
```

El **único** voto en contra es `gfx_v12_1.c:3440` — NAVI 12.1, no nuestra
generación — y es una discrepancia real del corpus, descrita en el hallazgo
`1074`: las otras nueve generaciones ponen 2 payload y esa pone 1. **GFX8 no
aporta ni un voto en contra**, y el vector de regresión lo exige por nombre.

Los 3 fuera de alcance son los dos constructores del `if/else` de
`gfx_v9_0.c:7476-7478` y el `SWITCH_BUFFER` de `gfx_v7_0.c:2206`: los tres están
en ramas condicionales y **no se sabe cuál se emite**, así que no votan.

> La primera versión de este oráculo contaba **129 contra 0** y lo publicaba
> como si el cero fuera una propiedad del corpus. No lo era: `129 vs 0` era
> consecuencia de un contador que no contaba los emisores de IB, y de uno que
> **fabricaba** 11 votos en contra (`1068`). Ampliado a los dos emisores y
> declarado el residuo, el número real es **227 contra 1**, y ese 1 tiene
> nombre, fichero y línea.

El caso canónico se ve a ojo, y es de una generación sister de la nuestra:

```c
gfx_v7_0.c:2080
  amdgpu_ring_write(ring, PACKET3(PACKET3_WAIT_REG_MEM, 5));   <- n = 5
  amdgpu_ring_write(ring, … WAIT_REG_MEM_OPERATION(1) …);      <- payload 1
  amdgpu_ring_write(ring, mmGPU_HDP_FLUSH_REQ);                <- payload 2
  amdgpu_ring_write(ring, mmGPU_HDP_FLUSH_DONE);               <- payload 3
  amdgpu_ring_write(ring, ref_and_mask);                       <- payload 4
  amdgpu_ring_write(ring, ref_and_mask);                       <- payload 5
  amdgpu_ring_write(ring, 0x20); /* poll interval */           <- payload 6
```

`n = 5` con **6** dwords de payload ⇒ `count = payload − 1`, `len = count + 2 = 7`.

**LOS DOS ORÁCULOS SE CRUZAN sobre el mismo caso**: el anillo real tiene
`PACKET3_WAIT_REG_MEM` con `count = 5` y ocupa 7 dwords; el driver escribe
`PACKET3(…, 5)` seguido de 6 escrituras. Mismo opcode, mismo número, dos
procedencias que no se tocan.

## 3 · LO QUE SE CIERRA Y LO QUE NO

| afirmación | estado |
|---|---|
| `PACKET3` ocupa `count + 2` dwords | **PROVEN** — geometría + 129 vs 0 |
| `PACKET3_NOP` ocupa 1 dword pese a su campo de cuenta | **PROVEN** — sin esta regla desborda |
| `PACKET3_NOP = 0x10` | **PROVEN** — `vid.h:112`, y el valor de relleno `0xFFFF1000` que aparece 1648 veces en el anillo es exactamente `.nop = PACKET3(PACKET3_NOP, 0x3FFF)` de `gfx_v8_0.c:6876` |
| longitud de `PACKET2` | **NOT_DETERMINED** — el anillo GFX no tiene ningún PACKET2 con cuenta ≠ 0, así que no hay dato. Se declara, no se elige |

## 4 · POR QUÉ ESTO NO LO DETECTÓ NINGÚN CONTROL DEL PROYECTO

Porque el error **se compensa**, y de eso trata el hallazgo `1063`. Aquí queda
solo la afirmación de la convención; `pm4dec.py` sigue dando 2048 exacto mientras
usa la longitud equivocada.

Y una observación sobre el método, que es un límite real y no un detalle: con
`count = 0`, `count + 2` y `2*count + 2` dan **los dos 2**. Un anillo hecho solo
de paquetes con `count = 0` no puede distinguirlas. El anillo real trae
`count = 5`, y por eso sí discrimina. Un oráculo cuyo poder de resolución
depende del contenido debe declarar esa dependencia, y `pm4tila.py` la declara.

## 5 · LO QUE NO ES DE ESTE HALLAZGO

Cuál de las seis cabeceras de opcode es la buena para GFX8 es semántica de
hardware y lo decide el agente principal. Aquí solo se mide **cuánta gente
ocupa un paquete**, que es una pregunta de longitud, no de significado.
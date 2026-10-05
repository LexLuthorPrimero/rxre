# R6-PM4TILA — la longitud de un paquete PM4 estaba contestada de tres maneras, y solo una embaldosa el anillo real

<!-- MEDIDO con tools/pm4tila.py. Artefacto: pm4tila.json.
     Regenerar: python3 tools/pm4tila.py --json > 08-ARQUITECTURA/artifacts/R6-PM4TILA/pm4tila.json -->

```
AGENCIA=RX550-INVESTIGACION · AGENT RE/TOOLING
WORK_CLASS=validacion-de-instrumentacion
RUNTIME=NO · sin sudo · sin ejecucion · GPU=INTACTA
escritura=3 ficheros NUEVOS.  Ningun fichero existente modificado.
herramienta   tools/pm4tila.py 1.1.0
sha256        4f3175d250c0f62e2bc74022a102230b4bdc4372d1c43abba1b0a4ecd1c920de
artefacto     08-ARQUITECTURA/artifacts/R6-PM4TILA/pm4tila.json
sha256        9fe556a67a0ab74534f9ef484a3c2732de694f0c36f2be5bbcf8b032b329046c
reproducible  f72226292ff5fa42cb59714b79fe2045c4735be76a78b79a6f7a5c2fb9664940  (2 corridas, mismo hash)
informe       08-ARQUITECTURA/artifacts/R6-PM4TILA/informe.txt
sha256        ef2754474905712098b7caf9beba19609505a4bd2cd6e591a5ceb72d615a24f2
selftest      31 vectores, 0 fallos, rc=0   (HERMETICO: verificado en cwd ajeno)
```

## 0 · LA PREGUNTA DE LA QUE DEPENDE TODA LA DECODIFICACIÓN PM4

Si la cabecera de un paquete es `PACKET3(op, n)`, **¿cuántos dwords ocupa?**

`vid.h` no contesta a esto. Solo empaqueta bits:

```c
#define PACKET3(op, n)  ((PACKET_TYPE3 << 30) | (((op) & 0xFF) << 8) \
                         | ((n) & 0x3FFF) << 16)
```

La semántica de `n` hay que sacarla de otro sitio, y **los tres sitios que hay
en este proyecto dan tres respuestas distintas**:

| sitio | qué afirma |
|---|---|
| `revkit/pm4dec.py:29` (docstring) | *count = dwords de payload … el paquete entero ocupa **count + 1** dwords* |
| `revkit/pm4dec.py:442` (**código**) | `fin = i + 1 + cnt` |
| `08-ARQUITECTURA/tools/pm4_codec.py:25` | *F = número de dwords de DATOS **− 1**, paquete = **F + 2** dwords* |

Y el propio `pm4dec.py` se contradice a sí mismo: la línea 1008 que **imprime**
dice *"EV-30 para el anillo GFX: count = payload − 1, 50 de 50"*, que es la
convención contraria a la de su código y a la de su docstring.

Eso no puede quedar en prosa de dos ficheros. Es la semántica más load-bearing
de toda la decodificación PM4 del proyecto, y dependía de en qué línea se mirara.

## 1 · EL ORÁCULO, Y POR QUÉ ES UN ORÁCULO Y NO UNA OPINIÓN

Un anillo PM4 es una **teselación exacta**: la suma de las longitudes de los
paquetes tiene que dar el número de dwords del anillo, sin sobra y sin falta.

Eso **no depende de ningún nombre de opcode, de ninguna cabecera, y de ninguna
convención previa**. Si una convención embaldosa y otra no, la que embaldosa es
la del hardware para ese anillo.

El instrumento, entonces, **no dice cuál es la convención**: enumera un espacio
de 16 convenciones y mide cuáles sobreviven. Si sobreviven más de una, no puede
decidir, y lo dice. Ese es el requisito de sonido: una adjudication que no
puede fallar no adjudica nada.

```
ESPACIO: PACKET3 ∈ {count+1, count+2, 2*count+1, 2*count+2}
      ×  NOP     ∈ {1 dword, regla general}
      ×  PACKET2 ∈ {2*count+1, count+1}          = 16 combinaciones
```

## 2 · RESULTADO · MEDIDO SOBRE LAS CUATRO CAPTURAS REALES

| anillo | veredicto | cuadran |
|---|---|---|
| `gfx` | **PARCIAL** | **2 de 16** |
| `sdma0` | `NO_ES_PM4_O_TRUNCADO` | 0 de 16 |
| `sdma1` | `NO_ES_PM4_O_TRUNCADO` | 0 de 16 |
| `comp_1.3.1` | **PARCIAL** | **2 de 16** |

**Las dos convenciones que sobreviven en el anillo GFX coinciden en `PACKET3 =
count + 2` y en `NOP = 1 dword`, y difieren SOLO en la longitud de PACKET2.**

Eso es lo que el dato decide, con número:

```
PACKET3 = count + 2      ADJUDICADO   (las 16 combinaciones que usen otra, mueren)
NOP     = 1 dword        ADJUDICADO
PACKET2 = ?              NOT_DETERMINED  — el anillo GFX no tiene NINGÚN PACKET2
                                      con cuenta distinta de cero, así que no
                                      hay dato que lo discrimine
```

El `NOT_DETERMINED` se declara, no se elige. Elegirlo habría sido inventar.

## 3 · SEGUNDO ORÁCULO, INDEPENDIENTE: EL DRIVER

La geometría dice cuál convención encaja con **estos datos**. Para corroborar
sin depender del mismo dato, se cuenta en el corpus cuántos `amdgpu_ring_write`
siguen a cada `PACKET3(op, n)`:

```
payload == n + 1   (count = payload − 1, len = count + 2): 129
payload == n       (count = payload,     len = count + 1):   0
fuera de alcance  (el emisor no usa amdgpu_ring_write):      69
```

**129 contra 0.** Y el caso canónico se ve a ojo, en GCN 3:

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

`n = 5` con **6** dwords de payload → `count = payload − 1`, `len = count + 2 = 7`.

**Los dos oráculos son independientes y se cruzan sobre el mismo caso**: el
anillo real tiene `PACKET3_WAIT_REG_MEM` con `count = 5` y ocupa 7 dwords; el
driver escribe `PACKET3(…, 5)` seguido de 6 escrituras. Mismo opcode, mismo
número, dos procedencias distintas.

> `vid.h:112` confirma además que `PACKET3_NOP = 0x10`, con lo que el valor de
> relleno `0xFFFF1000` que aparece 1648 veces en el anillo es exactamente
> `.nop = PACKET3(PACKET3_NOP, 0x3FFF)` de `gfx_v8_0.c:6876` — un NOP de
> relleno, no un paquete de 16383 dwords.

## 4 · R6-01 · `pm4dec.py` USA `count + 1`, Y POR QUÉ NADIE LO VIO

`revkit/pm4dec.py:442` usa `fin = i + 1 + cnt`, o sea `count + 1`. Con esa
convención, el anillo GFX **se para en el dword 4 de 2048**:

```
dword 3 = 0xC0032200   PACKET3_INDIRECT_BUFFER, count=3
dword 4 = 0x00001080   bits[31:30] = 0, que no es un tipo de paquete
```

**Y sin embargo `pm4dec.py` informa 1808 paquetes, y su suma de dwords da
2048 exacto.** ¿Cómo? Porque el error sistemático se **compensa**:

| | `pm4dec.py` | verdad adjudicada |
|---|---|---|
| longitud por paquete | `count + 1` | `count + 2` |
| `WAIT_REG_MEM` (count=5) | 6 dwords | **7** |
| `EVENT_WRITE_EOP` (count=4) | 5 dwords | **6** |
| filas de datos inventadas | **80** (`PKT0(dato)`) | **0** |
| total de paquetes | 1808 | **1728** |
| suma de dwords | 2048 ✓ | 2048 ✓ |

Cada paquete real queda **un dword corto**, y el dword que sobra se cuenta como
una fila `PKT0(dato, no cabecera)` y se re-sincroniza buscando la siguiente
cabecera. Como el error es exactamente de 1 dword por paquete, los 80 dwords
faltantes se compensan con 80 filas fantasma, **la suma total sigue dando 2048,
y nada parece estar mal.**

> **Éste es el hallazgo que importa, y es un modo de fallo, no un número.** Un
> decodificador whose total cuadra no está validado: el total cuadra *a pesar
> de* estar mal, porque el error y la compensación se anulan. La columna
> `dwords total` de `pm4dec.py` subestima el tamaño de cada paquete en 1, y las
> 80 filas `PKT0(dato)` no son un hallazgo: son el residuo del error.
>
> Lo que **sí** es correcto en `pm4dec.py`: la secuencia de opcodes, el orden,
> las posiciones, y la regla del NOP de 1 dword (que está bien justificada con
> `amdgpu_ring.c:128` y `:154`). Lo que está mal es la aritmética de longitud y
> las 80 filas que produce.

## 5 · R6-02 · LA DEGENERIDAD DEL ORÁCULO, DECLARADA

El poder discriminante del método depende de las cuentas que haya en el anillo:

```
count=0 -> count+2 = 2   2*count+2 = 2   INDISTINGUIBLES
count=1 -> count+2 = 3   2*count+2 = 4   distinguibles
count=5 -> count+2 = 7   2*count+2 = 12  distinguibles
```

Un anillo hecho solo de paquetes con `count = 0` **no puede distinguir**
`count + 2` de `2*count + 2`, y el veredicto correcto sería `PARCIAL` sobre esa
dimensión. Esto no es teórico: **fue un fallo de mi propio vector de selftest**,
que usaba `count = 0` y afirmaba `UNICA`. El vector estaba mal, la herramienta
acertó, y por eso hay un vector que exige precisamente que la degeneración se
declare (`BORDE__count_0_no_distingue…`).

Un método cuyo límite no se declara no se puede usar.

## 6 · LO QUE ESTO MIDE Y LO QUE NO

**Mide**: qué convenciones de longitud embaldosan cada anillo real; cuál de
ellas es la única cuando solo una sobrevive; y cuántos constructores del driver
apoyan cada hipótesis.

**No mide**:

- Si el anillo no embaldosa con ninguna, **no se elige entre «no es PM4» y «está
  truncado»**. Los dos anillos SDMA son el primer caso: arrancan con la cabecera
  de SDMA, no con PM4 — pero la herramienta no lo afirma, solo dice que ninguna
  de las 16 convenciones encaja.
- La longitud de **PACKET2**: `NOT_DETERMINED`, por §2.
- La corroboración del driver cuenta **`amdgpu_ring_write` y solo eso**. Un
  emisor que escriba por otra vía cuenta 0 y va a `fuera_de_alcance`, que son
  **69** de 198. No es un residuo pequeño y no se esconde: se imprime.
- Las convenciones **fuera del espacio declarado** no se buscan, luego no se
  refutan. Declarar el espacio es parte del contrato.

## 7 · EL ERROR QUE YO MISMO COMETÍ EN ESTA HERRAMIENTA

La primera medición de la corroboración dio **129 a favor de `count + 2` y 11 a
favor de `count + 1`**. Las 11 eran **inventadas por mi contador**:

```c
ib.ptr[ib.length_dw++] = PACKET3(PACKET3_EVENT_WRITE, 0);   // amdgpu_gfx.c:2510
buffer[count++] = cpu_to_le32(PACKET3(PACKET3_PREAMBLE_CNTL, 0));
```

Esos constructores escriben la cabecera **por una vía que no es `amdgpu_ring_write`**,
así que el payload se contaba como 0, y `payload(0) == n(0)` salía como un voto
a favor de `count + 1`. Once votos **a favor de la convención equivocada,
fabricados por el instrumento**.

La corrección es de una línea de alcance: si la cabecera no sale por
`amdgpu_ring_write`, el constructor **no se cuenta, ni a favor ni en contra**.

> Un oráculo que fabrica evidencia en contra es peor que no tener oráculo,
> porque convierte un defecto mío en un finding del proyecto. Y lo escribe el
> mismo trabajo que ya documentó falsos positivos de *staleness* en R3.

## 8 · LO QUE NO SE TOCA

- **No se corrige `pm4dec.py`.** `revkit/` aparecía modificado sin commitear
  por otro nodo durante esta sesión. El arreglo es de una línea (`i + 1 + cnt`
  → `i + 2 + cnt`) más quitar las 80 filas fantasma, y lo hace quien lo posea.
- **No se regenera `TOOLS-STATUS.md`.** `tools/artifacts.py` estaba modificado
  por otro nodo; regenerarlo habría escrito sobre su trabajo.
- **No se toca la GPU.** Análisis estático sobre ficheros ya capturados. No
  necesita puerta.

## 9 · SIGUIENTE ACCIÓN DE TOOLING

1. **El arreglo de una línea en `pm4dec.py:442`**, con su consequence: 1808 →
   1728 paquetes y desaparecen las 80 filas `PKT0(dato)`.
2. **`PACKET2 = NOT_DETERMINED` se puede cerrar** con un anillo que tenga un
   PACKET2 de cuenta > 0. El corpus no lo tiene; hace falta captura nueva, y
   eso es del nodo de runtime, no de aquí.
3. **Los 69 constructores `fuera_de_alcance`** se pueden cubrir incluyendo los
   emisores de IB (`ib.ptr[...]`) y de buffer de CPU, que son la vía por la que
   el driver emite un IB. Con eso la corroboración pasa de 129 a ~198.

```
ESTADO
  ficheros escritos    3, todos nuevos
  ficheros modificados 0
  GPU                  INTACTA
  sudo                 NO usado
  commits              NINGUNO
  los dos oraculos     coinciden, y no se promedian
```

```
OBSERVATION_FOR_MAIN_AGENT
  1. `revkit/pm4dec.py:442` usa `fin = i + 1 + cnt`.  La longitud correcta de un
     PACKET3 en GFX8 es `count + 2`, adjudicado por teselado exacto del anillo
     real y corroborado por 129 constructores del driver contra 0.
  2. Consecuencia medida: `pm4dec.py` reporta 1808 paquetes donde hay 1728, y
     cada longitud de paquete va un dword corta.  Las 80 filas `PKT0(dato)` no
     son datos: son la compensacion del error, y por eso la suma total cuadra
     y el defecto es invisible.
  3. Lo que NO es de este nodo: cual es el opcode "bueno" para GFX8 entre las
     seis cabeceras, y si el residuo del anillo describe una carga real.  Son
     semantica de hardware y las decide el agente principal.
```
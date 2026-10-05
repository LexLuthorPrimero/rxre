# 1063 — `pm4dec.py` informa 1808 paquetes donde hay 1728, y su suma da 2048 exacto: el error se compensa solo

```text
AGENCIA=RX550-INVESTIGACION · WORK_CLASS=AGENT-RE-TOOLING
GENERADO=2026-10-04 · MEDIDO=EN ESTA HOST
AFECTADO=revkit/pm4dec.py  (1.0.0, TOOL_UNVALIDATED: no declara selftest)
         revkit/capturas/amdgpu_ring_gfx.txt  (8204 B, anillo real de esta RX550)
        Finding 1062 (la convencion, adjudicada aqui)
ESTADO=PROVEN-DEFECTO-DE-INSTRUMENTO · el decodificador NO es el unico afectado
herramienta   tools/pm4tila.py 1.1.0
sha256        4f3175d250c0f62e2bc74022a102230b4bdc4372d1c43abba1b0a4ecd1c920de
```

## 0 · EL HECHO, SIN NINGUNA INTERPRETACIÓN

`pm4dec.py` sobre el anillo GFX real de esta tarjeta:

```
$ python3 revkit/pm4dec.py revkit/capturas/amdgpu_ring_gfx.txt
  paquetes : 1808

opcode                           veces   dwords total
  PACKET3_NOP                      1648    1648
  PKT0(dato, no cabecera)            80       80     <-- no existe como paquete
  PACKET3_EVENT_WRITE_EOP            32      160
  PACKET3_COND_EXEC                   8       32
  PACKET3_WAIT_REG_MEM                8       48
  PACKET3_CONTEXT_CONTROL             8       16
  PACKET3_INDIRECT_BUFFER             8       24
  PACKET3_WRITE_DATA                  8       32
  PACKET3_SWITCH_BUFFER               8        8
```

La verdad, con la convención de `1062` adjudicada:

```
  opcode                           veces   dwords total
  PACKET3_NOP                      1648     1648
  PACKET3_EVENT_WRITE_EOP            32      192
  PACKET3_COND_EXEC                   8       40
  PACKET3_WAIT_REG_MEM                8       56
  PACKET3_CONTEXT_CONTROL             8       24
  PACKET3_INDIRECT_BUFFER             8       32
  PACKET3_SWITCH_BUFFER               8       16
  PACKET3_WRITE_DATA                  8       40
  TOTAL                            1728     2048
```

| | `pm4dec.py` | verdad |
|---|---|---|
| longitud por paquete | `count + 1` | `count + 2` |
| `WAIT_REG_MEM` (count=5) | 6 dwords | **7** |
| `EVENT_WRITE_EOP` (count=4) | 5 dwords | **6** |
| paquetes | **1808** | **1728** |
| filas `PKT0(dato)` | **80** | **0** |
| **suma de dwords** | **2048 ✓** | **2048 ✓** |

## 1 · POR QUÉ NADA PARECE ESTAR MAL

`pm4dec.py:442` calcula `fin = i + 1 + cnt`, o sea `count + 1`, y queda **un
dword corto en cada paquete**. Ese dword que sobra no se pierde: se cuenta
como una fila `PKT0(dato, no cabecera)` y el recorrido **se re-sincroniza
buscando la siguiente cabecera**.

Como el error es exactamente de 1 dword por paquete, los 80 dwords que faltan
se compensan con 80 filas fantasma:

```
80 paquetes reales × 1 dword de déficit = 80 dwords de déficit
80 filas PKT0(dato)                     = 80 dwords de stuffing
                                          ─────────────────────────────
                                          suma final: 2048.  Cuadra.
```

**Las 80 filas `PKT0(dato)` no son un hallazgo. Son la compensación del error.**

## 2 · POR QUÉ ESTO ES EL HALLAZGO IMPORTANTE Y NO EL NÚMERO 1808

> **Un decodificador cuya suma total cuadra no está validado. Cuadra *a pesar de*
> estar mal**, porque el error sistemático y su compensación se anulan.

Consecuencia: **cualquier control que se apoye en "los dwords consumidos suman el
tamaño del anillo" pasa con este decodificador.** Ese control es exactamente el
que parecería natural escribir para validar un decodificador de anillo, y es
precisamente el que no puede fallar aquí.

Y hay un segundo daño, más silencioso: la columna `dwords total` **subestima en 1
el tamaño de cada paquete**. Quien calcule un tamaño de IB, un presupuesto de
ring o una alineación a partir de esa columna va a estar un dword corto en
80 paquetes.

## 3 · LO QUE `pm4dec.py` SÍ HACE BIEN, Y NO SE TOCA

- **La secuencia de opcodes, el orden y las posiciones de dword son correctos.**
  Los 80 paquetes reales están donde deben estar. Lo que falla es la aritmética
  de longitud, no la lectura.
- **La regla del NOP de 1 dword es correcta y está bien justificada**: cita
  `gfx_v8_0.c:6873` y los dos sitios de `amdgpu_ring.c` (`:128` y `:154`) donde
  `memset32(..., ring->funcs->nop, count)` escribe ese valor como dword suelto.
- **Su aviso sobre los anillos SDMA es correcto**: dice que el paseo PM4 no aplica
  ahí y que el número de paquetes no es una medida. Eso se escribió antes de que
  existiera esta herramienta, y `pm4tila` lo confirma por vía independiente: ninguno
  de los 16 embaldosamientos encaja en `sdma0` ni en `sdma1`.

## 4 · EL ARREGLO, Y POR QUÉ NO LO APLICO

Una línea en `revkit/pm4dec.py:442`:

```c
  fin = i + 1 + cnt        ->        fin = i + 2 + cnt
```

más eliminar la re-sincronización y las 80 filas `PKT0(dato)`.

**No lo aplico**, por una razón que no es rendimiento: `revkit/` aparecía
**modificado sin commitear por otro nodo** durante esta sesión (`git status`:
`M revkit/cn8.py`, `M revkit/dires.py`, `M revkit/huerfanos.py`). Una corrección
de una línea escrita encima del trabajo de otro nodo no es una corrección, es un
confulto. Se deja el hallazgo y lo aplica quien posea el fichero.

## 5 · LA LECCIÓN, QUE ES MÁS CARA QUE EL NÚMERO

Un instrumento puede tener un defecto **invisible por construcción**: si el error
y su compensación se anulan, el total cuadra y todo control que mire el total
pasa. La defenses no es "comprobar el total", porque el total no es información:
es una suma que se sostiene por sí sola.

La defenses es la que este hallazgo usó: **una restricción geométrica que el
decodificador no puede absorber** — la longitud tiene que ser la misma para
todos los paquetes, y se comprueba contra el driver, que no sabe nada del
decodificador.

```
OBSERVATION_FOR_MAIN_AGENT
  El defecto es de `revkit/pm4dec.py`, fichero de otra sesion.  El hallazgo queda
  registrado aqui porque la MEDICION es de este nodo; la escritura del parche no.
```
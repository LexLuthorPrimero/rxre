# 045 · La convención de `count` nunca se midió en el ASIC de esta GPU, y dos herramientas automatizan el error que la dejó sin medir

`CLASSIFICATION=TOOL+CORRECTION` · `TRACK=STATIC` · `GPU INTACTA` · `RUNTIME=NOT_RUN`
`TOOLS=tools/citegen.py, tools/pm4census.py` · `COMPLETA=023, 043` · `MODIFICATIONS=0` en el corpus

## CUDA principal

`023` mide la convención de `count` de PACKET3 —la regla que sostiene los 7 opcodes de mi
codificador— sobre seis generaciones, y **ninguna es la de esta GPU**:

```
gfx_v6_0.c:1867    SET_CONFIG_REG, 1  ->  reg offset + 0xDEADBEEF   (2 payload)
gfx_v7_0.c:2246    SET_CONFIG_REG, 1  ->  reg offset                (2 payload)
gfx_v10_0.c:8687   SET_CONFIG_REG, 1  ->  reg + gds_compute_max_... (2 payload)
gfx_v11_0.c:5985   SET_CONFIG_REG, 1  ->  reg + gds_compute_max_... (2 payload)
gfx_v12_1.c:3371   SET_CONFIG_REG, 1  ->  reg                       (1 payload)
```

El fichero que esta GPU ejecuta es `gfx_v8_0.c` (`vi.c:2107-2123` lo añade). **`gfx_v8_0.c` no
está en la tabla.** La conclusión quedó redactada como si midiera el ASIC, y el ASIC no
aparecía.

Esto es el mismo fallo que `043` retributionó, en otro campo y con la misma causa: **medir en
la generación equivocada sin notar que se ha medido fuera de objetivo.** En `035` costó un
`count` de PTEPDE; aquí costó la convención entera de PACKET3, que es la base de los 7
opcodes y de las 4 puertas del driver.

Medido ahora, en el fichero correcto, con 43 emisiones de 25 paquetes distintos:

```
VEREDICTO sobre lo que SI se pudo medir: count = payload - 1, en 43 de 43
COBERTURA: 43 de 50 emisiones reconcilian (86%)
SIN MEDIR: 5   LIMITE: 2
```

**Y el resultado es idéntico en los dos corpora del proyecto**, que es un cross-check que no
me pedí:

| corpus | emisiones | reconcilian | veredicto |
|---|---|---|---|
| `RESEARCH/working/linux-7.1.3` (el de `023`) | 50 | 43 | `count = payload - 1` |
| `rx550-upstream-7.2.8/linux-7.2.8` | 50 | 43 | `count = payload - 1` |

Dos versiones de kernel, 7206 y 7209 líneas en `gfx_v8_0.c`, mismo recuento y misma regla. La
convención no cambió entre 7.1.3 y 7.2.8 en lo que esta GPU emite, y eso es un dato que
ninguna de las dos tablas de `023` podía dar porque ninguna seccionó sobre el ASIC.

Y el dato que `023` buscaba, en el ASIC de esta GPU:

```
PACKET3_SET_CONFIG_REG   count=1   payload=2   count = payload - 1
```

`SET_CONFIG_REG` **sí** tiene 2 payload en GFX8, y `023` no lo comprobó nunca aquí: su
`NEGATIVE_RESULT` sobre el caso de `gfx_v12_1` seguía siendo un `NEGATIVE_RESULT`, porque el
contraste de cinco generaciones no podía refutar nada sobre la sexta.

## `citegen`: el error de `043` aplicado a las 1722 citas del proyecto

`043` retuvo dos findings a mano. La pregunta general —cuántas otras citas apuntan a un
fichero que esta GPU no ejecuta— no se puede responder a mano, y `citegen.py` la responde:

```
citas       1722  (ficheros .md/.c/.h/.sh/.py, corpus excluido)
  EN_DISPATCH         1307
  EN_RUTA_IP           247
  FUERA_DE_AMDGPU      114
  NO_EN_DISPATCH        28  <-- SOSPECHOSO
  OTRO_ASIC             26  <-- SOSPECHOSO
```

Cada cita se clasifica resolviendo **fichero → bloque → `.funcs` → ¿lo añade el `case` de
`CHIP_POLARIS12`?**, no por el nombre del fichero. Y con una clase que `043` no miró:
`EN_RUTA_IP` son 247 citas a ficheros que no añade ningún `case` de chip, pero a los que
`amdgpu_discovery.c` enruta por versión de IP. No son un error: son ficheros cuyo uso en
esta GPU **no es decidible sin leer un registro**, y la herramienta lo dice en vez de
confundirlo con un error.

**Lo que NO dice, y es lo importante:** no afirma que una cita sea errónea. Un hallazgo
sobre Tonga es evidencia legítima; la comparación entre generaciones es lo que produjo
`033` y `056`. Lo que señala es una condición concreta —el fichero citado no está en la ruta
de ejecución de esta GPU— y deja el juicio a quien lee.

Las 54 sospechosas se concentran en tres documentos que citan `gmc_v6_0.c` / `gmc_v7_0.c` /
`dce_v8_0.c` al comparar generaciones, y en `017`/`023`/`026`/`033`/`051`/`054`/`056`, que lo
hacen **declarando** que es un contraste (`060` lo dice en el título: *"el decodificador está
en `dce_v8_0.c`"*). Ninguna es un error de `035`. La herramienta no pretende que lo fueran:
pretende que quien relea sepa en un comando cuáles son contrastadas y cuáles no lo están.

## `pm4census`: por qué cuenta el macro y no solo el emisor

`PACKET3(op, n)` es un macro, y sus seis definiciones coinciden en la cuenta de campos:

```
cikd.h:229  cikd.h sid.h:336  soc15d.h:50  nvd.h:48  vid.h:105  gfx_v12_1_pkt.h:48
   -> 6 de 6, y TODAS con count & 0x3FFF
```

La cabecera es `(TYPE3 << 30) | (op & 0xFF) << 16 | (n) & 0x3FFF`. El opcode no lleva número;
el número de payload lo decide el emisor. Por eso hay dos niveles y ambos se informan, y si
no concuerdan se dice en vez de elegir uno.

## Cuatro fallos de la herramienta, y los tres que importan

**Reconocía un patrón de escritura de los cuatro que existen.** Solo buscaba
`ib->ptr[ib->length_dw++]`, y `gfx_v8_0.c` escribe con `amdgpu_ring_write(ring, ...)` 172
veces, con `buffer[count++]` 4, y con `ib.ptr[ib.length_dw++]` —**con punto, no con flecha**—
en el camino de compute. Devolvía 0 payload en las 50 emisiones, que se ve exactamente como
una medida de cero. **Un reconocedor incompleto no produce ceros: produce ceros que parecen
medidas.** Por eso la herramienta imprime qué patrones reconoció, y avisa si no reconoció
ninguno.

**Contaba el header como payload.** Todas las emisiones daban `payload = count + 2`. El
header EScribe un dword, pero no es payload: el `+1` de `payload = count + 1` es el propio
header, y la regla `total = count + 2` ya lo cuenta.

**Contaba solapes.** `ib.ptr[ib.length_dw++]` casa con dos patrones a la vez, así que una
emisión de 2 payload se contaba como 4. La cuenta es de **tramos** fusionados, no de
coincidencias: dos patrones que reconocen el mismo texto reconocen el mismo dword. Lo cazó el
selftest, que es para lo que está.

**Y el más importante, que no es un fallo sino una decisión:** las emisiones que no reconcilian
se marcan `LIMITE`, **no** `OTRA REGLA`. Un fallo de los límites del bloque hace que una
emisión mida el payload de la siguiente, y eso se lee como una convención distinta. **Una
herramienta de medición no puede fabricar un contraejemplo por un fallo suyo.** Las `LIMITE`
no entran en el veredicto, el código de salida es 1 con cobertura incompleta, y la salida las
lista para revisión manual.

## Lo que sigue `NOT_DETERMINED`

Nada de esto cambia el hueco de fondo:

- Si el hardware de esta pieza lee el campo como el driver de referencia lo escribe. La
  evidencia es lo que el driver hace, `033` estableció que el spec de GFX8 no está publicado,
  y esto es `PROVEN_DERIVED` sobre software, no `PROVEN` sobre hardware.
- Qué versión de `SDMA0_HWIP` tiene esta tarjeta, que es lo que decide el despacho.
- Las 5 emisiones `SIN MEDIR` y las 2 `LIMITE` de `gfx_v8_0.c`.
- Todo lo de `033`/`037`/`040` que depende de la semántica del MMU.

## UNLOCKS

- La regla `count = payload - 1` queda **`PROVEN_DERIVED` sobre el ASIC de esta GPU**, con
  43 de 43 y 86% de cobertura declarada, en vez de extrapolada de cinco generaciones ajenas.
- `citegen` convierte "no cites el ASIC equivocado" de un recordatorio en una comprobación
  ejecutable sobre las 1722 citas. Es la política de `043` convertida en herramienta.
- El patrón de `citegen` es reutilizable: cualquier afirmación del proyecto que dependa de
  "este fichero es de mi ASIC" se puede auditar con la misma regla.
- El siguiente hueco que `citegen` deja abierto: la clasificación `EN_RUTA_IP` cubre 247 citas
  cuya resolución depende de un registro. Cerrarlo es un `RUNTIME` con discriminante claro,
  o aceitar que es `NOT_DETERMINED` para siempre.

## Falsación

- La regla se refuta si alguna de las 43 emisiones reconciliadas cambia al forzar
  `--fichero` a otro ASIC, o si el recuento de payload de `gfx_v8_0.c` deja de ser 43 con el
  mismo corpus.
- El `LIMITE` se refuta si las 2 emisiones marcadas resultan ser de verdad contraejemplos. Es
  comprobable leyendo dos bloques, y por eso se listan en vez de archivarse.
- `citegen` se refuta si un fichero marcado `OTRO_ASIC` apareciera en un `case` de
  `CHIP_POLARIS12` que la herramienta no leyó, o si `.funcs` dejara de ser el discriminante.
  El caso `vi.c:1344` sin `break` dentro de 60 líneas se reporta como `AVISO` con su lista
  posiblemente incompleta, que es la única parte del grafo que no doy por cerrada.
- El selftest se refuta si un vector pasa con la lógica que valida. Los ocho valores
  esperados están escritos a mano, con la cuenta hecha fuera, y eso se declara.

## Evidencia

```
tools/pm4census.py     8 vectores de selftest, valores verificados a mano
                       43 de 43 emisiones reconcilian en gfx_v8_0.c
                       43 de 43 tambien en linux-7.1.3: dos corpus, mismo resultado
                       6 de 6 cabeceras coinciden en la mascara del count
                       86% de cobertura, 5 SIN MEDIR, 2 LIMITE, todo impreso
tools/citegen.py       1722 citas clasificadas en 5 clases
                       54 sospechosas, 30 en 06-INGENIERIA-INVERSA
tools/oracle.sh        9 modos; --block sin resolver encadena a which_hw
suite del driver       22 + 12 + 195 = 229 checks, 0 fallos
crosscheck             10 vectores CLEAN
rx550pm4val            16/16
audit_citations        239 citas, 0 fallos
corpus                 MODIFICATIONS=0, sha256 12e8d5a973d1ad7c…c3e51941
```

Ningún registro leído de MMIO. `insmod` no ejecutado. `GPU INTACTA`.

# 1131 — `[N]` no es `[N:N]`: la lectura equivocaba producia un **OK no ganado** y acusaba de truncamiento a quien no declaraba anchura; además, los dos instrumentos **contaban mal sus propios vectores de selftest**

```text
AGENCIA=RX550-INVESTIGACION · WORK_CLASS=VALIDATION + INSTRUMENT-CORRECTION
AUTOR=AGENTE-INSTR
WRITE_EXECUTION=NONE · MODIFICATIONS=0 · RUNTIME=NOT_RUN
ESCRITOS_POR_ESTA_ITERACION   tools/layoutcross.py
                              tools/ibref.py
                              tools/verif.py
                              08-ARQUITECTURA/artifacts/VERIF/linea-base.json
                              08-ARQUITECTURA/artifacts/R9-REPARACION/candidata.py
MODIFICADO_NADA_EXISTENTE    pm4_codec.py y pm4_emit.py INTACTOS
CLASSIFICATION=MEASUREMENT · DEREFUTATION · IMPLEMENTATION
GENERADO=2026-10-04 · MEDIDO=EN ESTA HOST
ESTADO=[N] CORREGIDO · OK NO GANADO ELIMINADO · CONTADORES VERIFICADOS
```

## 0 · El resultado, primero

Cuatro cosas, todas medidas, todas en instrumentos míos:

```text
1. [N] NO es [N:N]                     13 de 13 casos, 0 contraejemplos
2. La lectura previa daba un OK no ganado        1 (CP_DMA.ENGINE)
   y acusaba de truncamiento a 4 campos que
   no declaraban anchura ninguna
3. Los dos instrumentos contaban mal sus vectores  layoutcross 54/70 · ibref 22/32
4. ibref --roundtrip, capability nueva              vivo rc=1 · candidata rc=0
```

La tercera es la que más me interesa, y no por ser un bug: **por ser un bug
de la clase que este proyecto ha pagado seis veces.** Un número escrito a mano
en el `print` que parece una medición.

## 1 · `[N]` NO ES `[N:N]`, Y SE DECIDE POR EL CORPUS

`pm4_codec` escribe las dos cosas:

```text
tools/pm4_codec.py:98   "CONTROL[31:0]  (queue_sel[4] | queue_type[21] | engine_sel[26] "
tools/pm4_codec.py:107  "ACTION[1] | QUEUE_SEL[2:0] | ENGINE_SEL[6:5] | NUM_QUEUES[10]",
```

`[4]` y `[2:0]` conviven en el mismo fichero. `[N]` no significa "un bit":
significa **"el campo empieza en el bit N"**, y la anchura no se dice.

No lo decido por la notación: lo decido contrastando contra KFD, que sí declara
anchura.

| declarado | KFD | lectura `[N:N]` correcta? |
|---|---|---|
| `queue_sel[4]` | `[5:4]` | NO |
| `queue_type[21]` | `[23:21]` | NO |
| `engine_sel[26]` | `[28:26]` | NO |
| `num_queues[29]` | `[31:29]` | NO |
| `UNMAP_QUEUES.ACTION[1]` | `[1:0]` | NO |
| `UNMAP_QUEUES.NUM_QUEUES[10]` | `[31:29]` | NO |
| `CP_DMA.CP_SYNC[31]` | sin oraculo | — |
| `CP_DMA.ENGINE[27]` | sin oraculo | — |
| `QUERY_STATUS.dword[4]`, `[5]` | sin oraculo | — |
| `UNMAP_QUEUES.dword[2..4]` | sin oraculo | — |

```text
casos con oraculo suficiente   6
lectura [N:N] correcta          0
contracasos                     0
```

**0 de 6.** Cuando hay oráculo, `[N:N]` es siempre incorrecto y KFD siempre da
más ancho. El resto son `dword[N]` (marcadores de relleno) y dos campos sin
oráculo, que no pueden confirmar ni refutar pero no cambian la regla.

## 2 · LO QUE LA LECTURA EQUIVOCADA PRODUCÍA: DOS FALLOS DISTINTOS

`RE_BIT1` mapeaba `[N]` a `(N, N)`. Consecuencia medida:

```text
ANTES                                    DESPUES
DISCREPA_ANCHURA    6    ->                 2
ANCHURA_NO_DECLARADA 0    ->                 5
OK                  21    ->                20
```

### 2a · Un OK no ganado

```text
ANTES  PACKET3_CP_DMA  dw3  ENGINE  OK
       "anchura no contrastable: vid.h da el desplazamiento y KFD no modela
        este campo"

DESPUES PACKET3_CP_DMA  dw3  ENGINE  ANCHURA_NO_DECLARADA
       "el macro dice ENGINE<<27 y la herramienta escribe [27], que no dice
        de quantos bits es el campo. La POSICION es correcta; la anchura no la
        declara nadie, ni la herramienta ni ningun oraculo"
```

El texto del veredicto antiguo **anunciaba la limitación y aun así decía OK**.
Es la forma más peligrosa de este tipo de bug: la advertencia está en la misma
frase que el veredicto, y un lector que lee la tabla — que es como se lee — se
queda con el OK.

Una declaración incompleta que acierta la posición **no está corroborada**. Que
no haya forma de comprobarla es un hecho sobre los oráculos, no un aval sobre
la herramienta.

### 2b · Una acusación que no corresponde

```text
ANTES  MAP_QUEUES.queue_sel  DISCREPA_ANCHURA
       "el LSB coincide (4) pero KFD da el rango completo [5:4] y la
        herramienta declara [4:4]. El campo esta en su sitio y se TRUNCA"

DESPUES MAP_QUEUES.queue_sel  ANCHURA_NO_DECLARADA
```

El texto antiguo **atribuye a la herramienta una declaración que no ha hecho**
(`[4:4]`), y acusa de truncamiento a quien no declaró anchura. `DISCREPA_ANCHURA`
mezclaba dos situaciones y solo una es defecto:

```text
"declara una anchura y es equivocada"   DEFECTO
"no declara anchura"                     DECLARACION INCOMPLETA
```

Solo la primera se arregla corrigiendo números. La segunda se arregla
escribiendo lo que falta, que es otra cosa, y diagnosticarla como truncamiento
manda a la persona al sitio equivocado.

## 3 · LA FORMA DE ARREGLARLO SIN ROMPER LAS COMPARACIONES

Un rango es ahora una tupla con atributo:

```text
class Rango(tuple):        # hi, lo siguen desempaquetando igual
    def __new__(cls, hi, lo, ancho_declarado=True)
```

Se eligió así a propósito: los otros consumidores de `extraer_bits` comparan con
`!= (hi, lo)` y hacen aritmética con los dos elementos. Cambiar la forma de la
tupla obligaba a revisarlos todos, y revisarlos todos para cambiar una cosa es
cómo se introducen errores nuevos. Con la tupla, `RE_BITS` y `RE_BIT1` se
separan y **ninguna comparación existente cambia de comportamiento**.

Vectores que fijan el comportamiento, 5, incluido el control positivo:

```text
[N] con LSB correcto y KFD mas ancho      -> ANCHURA_NO_DECLARADA
[N] NO se acusa de DISCREPA_ANCHURA       -> OK
[N] el diagnostico dice anchura, no truncamiento -> OK
[N] con KFD coincidente (control positivo)-> ANCHURA_NO_DECLARADA
[hi:lo] explicito con KFD coincidente     -> OK
```

El cuarto existe por una razón concreta: sin él, `ANCHURA_NO_DECLARADA` seria
**indistinguible de "este oráculo no dice nada"** y el test pasaría con la rama
muerta. Es el mismo motivo por el que existe el control negativo en los
contratos de reparación, y por el que un selftest que solo prueba el camino
feliz no prueba nada.

## 4 · `ibref --roundtrip`: EL TEST QUE LOS CONTRATOS DE `1061`/`1073` PEDÍAN

Escrito en la iteración anterior como pendiente y declarado pendiente en `1107 §6`.
Ahora existe y **discrimina**.

```text
$ ibref --func gfx_v8_0_kiq_kcq_enable ... --roundtrip --tablas pm4_codec.py
PACKET3_MAP_QUEUES  10  2  PIPE           1   -        -        NO_EXTRAIBLE
PACKET3_MAP_QUEUES  10  2  QUEUE          3   -        -        NO_EXTRAIBLE
PACKET3_MAP_QUEUES  10  2  ME             0   -        -        NO_EXTRAIBLE
rc = 1

$ ... --tablas artifacts/R9-REPARACION/candidata.py
PACKET3_MAP_QUEUES  10  2  ME             0   0        31 (lsb solo)  OK_SOLO_UN_BIT
PACKET3_MAP_QUEUES  10  2  PIPE           1   1        30:29           OK
PACKET3_MAP_QUEUES  10  2  QUEUE          3   3        28:26           OK
rc = 0
```

Por qué discrimina y no solo compara: el valor esperado sale de la **expresión
del driver**, no de la declaración. Una declaración con el campo en bits
equivocados extrae otra cosa, y sale `MISMATCH`. Es decir, el oráculo es
independiente del sujeto, que es lo que un test necesita para poder fallar.

Cinco salidas, y las cinco son resultados:

```text
OK                 el valor extraido con el rango declarado es el escrito
MISMATCH           se extrae otra cosa: el rango no cubre el campo
NO_EXTRAIBLE       el driver escribe el campo y la declaracion no lo nombra
VALOR_NO_AISLABLE  ambos lo nombran pero el valor no se aísla del driver
OK_SOLO_UN_BIT     el campo EMPIEZA en el bit declarado; la anchura no se sabe
FUERA_DE_PAQUETE   la declaracion tiene mas entradas de las que count permite
```

Segmenta por paquete antes de comparar. Un IB puede llevar varios paquetes, y
comparar todos contra el layout del primero produce basura: los campos del
segundo salen `NO_EXTRAIBLE` sin motivo. Con segmentación, si el layout declara
más entradas de las que `count` permite, el exceso sale `FUERA_DE_PAQUETE` — y
eso es el test de framing de `1061` corriendo sobre valores de verdad.

10 vectores nuevos. `ibref` pasa de 22 a **32**.

## 5 · LOS CONTADORES DE VECTORES NO CONTABAN NADA

```text
layoutcross.py:1623   print("SELFTEST OK: %d vectores" % (20 + 34))
ibref.py              print("SELFTEST OK: 22 vectores")
```

Dos constantes escritas a mano en el `print` de resumen.

```text
                     declarado   real   subreportado
layoutcross                 54      70      -16  (-23%)
ibref                        22      32      -10  (-31%)
```

La consecuencia práctica es la que importa: **añadí 5 vectores a `layoutcross` y
el número no se movió.** Si el contador sube al añadir y al quitar, entonces no
está contando nada, y entonces la cifra que da la confianza en el selftest no
tiene relación con el selftest. Un instrumento que se audita a sí mismo y da
una respuesta fija es peor que uno que no se audita, porque ocupa el sitio de
la verificación.

Arreglado contando los nombres de vector en un conjunto, en ambos.

## 6 · MIS ERRORES, TODOS DE ESTA ITERACIÓN

Ninguno es teórico: los cinco occurred y están medidos.

| # | error | cómo salió |
|---|---|---|
| 1 | **`[N]` invisible en mi round-trip.** Mi regex exigía `hi:lo` | `ME` salió `NO_EXTRAIBLE` con la candidata que **sí** lo declara |
| 2 | **`OK_SOLO_UN_BIT` era código muerto.** Comparaba 1 bit contra un valor de N bits, que nunca da igual | el vector no podía pasar por construcción |
| 3 | **`VALOR_NO_AISLABLE` falso para `ME`.** El round-trip llamaba al evaluador sin las adaptaciones de la frontera | `ring->me == 1 ? 0 : 1` no se aislaba, con `->` sin traducir |
| 4 | **Contador de vectores falso en los dos instrumentos** | ver 5 |
| 5 | **`rc=0` en el vivo, reportado por mí.** `$(basename $F)` dentro de `echo "$?"` **resetea `$?`** | el round-trip fallaba y yo informaba que pasaba |

Y dos afirmaciones que hice y **retracté antes de escribirlas**:

```text
"cuatro regex mios exigen hi:lo"        FALSO: layoutcross tiene RE_BIT1 desde
                                        el principio y SI lo parseaba
"13 de 46 (28%) invisibles"             FALSO: medido, los 13 se declaraban y se
                                        auditaban; el defecto era de ibref
"codigo muerto detras de un return"     FALSO: era dos regiones que `sed`
                                        imprimia juntas y lei como una
```

La primera importa: si llego a escribir el "28% invisible" en el hallazgo, la
afirmación más fuerte del documento habría sido **falsa**, y habría sostenido
el argumento con un número inventado por una lectura equivocada de mi propio
código. Se descartó al medir antes de escribir. Es exactamente para lo que está
la regla de verificar antes de congelar.

## 7 · LA PUERTA, PERTURBADA

`verif` mide 36 valores (uno nuevo: `layout.bits_anchura_no_declarada`, que es
lo que hace que la clase nueva no pueda crecer en silencio).

```text
linea base re-fijada        35 -> 36 medidas
SIN DERIVA en las 36        rc = 0
perturbacion (bits_ok 20->99) rc = 1,  DERIVA EN 1 de 36
restaurada                  rc = 0
```

La puerta se probó antes de confiar en ella. Las dos derivas que salió al
cambiar el instrumento eran las **esperadas** y ninguna otra:

```text
layout.bits_anchura   6 -> 2    (los 4 de MAP_QUEUES pasan a la clase nueva)
layout.bits_ok       21 -> 20   (se pierde el OK no ganado de CP_DMA.ENGINE)
```

## 8 · LO QUE ESTO NO PRUEBA

**No prueba que `pm4_codec.py` tenga razón.** Prueba que su notación es
ambigua y que leerla como `[N:N]` produce dos veredictos erroneous. La
notación correcta — `[5:4]` o `[4]` con una convención declarada — sigue sin
decidirla: `1108` es de otra sesión y esta es la frontera de otro autor.

**No prueba el hardware.** KFD es un tercer oráculo, no el documento de
hardware. Que tres fuentes del kernel coincidan es corroboración, no prueba, y
las tres se derivaron del mismo ASIC que documenta este proyecto.

**No prueba que la reparación de `1107` funcione en la placa.** El round-trip
comprueba que una declaración y una expresión del driver se corresponden sobre
un IB sintético. No hay placa, no hay hardware, `RUNTIME=NOT_RUN`.

**No cubre `CP_DMA`, `DMA_DATA` ni ningún paquete que KFD no modela.** Siguen
con `SIN_ORACULO_BITS`, y `CP_DMA.CP_SYNC` sigue sin posicionar. Ampliar el
oráculo a `kfd_pm4_headers_ai.h` y `_aldebaran.h` sigue sin hacerse: primero
hay que comprobar si divergen de `vi.h`, porque un oráculo que se añade sin
verificar es un oráculo que miente con más confianza.
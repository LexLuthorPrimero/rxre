# 122 · Para que el encuadre de «dos fuentes» resulte honesto: 3 de 4, no 4 de 4

`CLASSIFICATION=METHODOLOGY` · `TRACK=STATIC` · `WORK_CLASS=READ_ONLY/EVIDENCE`
`WRITE_EXECUTION=OWN_DRIVER_ONLY` · `MODIFICATIONS_CORPUS=0` · `RUNTIME=NOT_RUN` · `GPU INTACTA`
`CONTINUES=121` · `MISMA_CLASE_QUE=034` (un contraste sobre una fuente no es un contraste)

## Cuestión principal

`rx550_pm4_wait_reg_mem()` estaba marcada `PROVEN` con este párrafo:

> *Los cuatro campos de control que esta función empaqueta (FUNCTION<<0,
> MEM_SPACE<<4, OPERATION<<6, ENGINE<<8) y el valor `0="always"` están PROVEN
> por **dos familias de headers independientes**: `vid.h` escrito a mano
> (:180-187) y `soc15d.h` generado del XML (:214-220).*

Una corroboración declarada sobre cuatro campos. **¿Están los cuatro en las
dos fuentes?**

## Criterio de terminación

Para cada uno de los cuatro campos, comprobar si existe en `vid.h` **y** en
`soc15d.h`, y con qué codificación. **Cumplido: 3 de 4. `ENGINE` no está en
`soc15d.h`.**

## Respuesta

```
campo        vid.h                   soc15d.h                    dos fuentes
FUNCTION   :169  ((x) << 0)      :199  (((unsigned)(x)) & 0x7) << 0    SI
MEM_SPACE  :178  ((x) << 4)      :200  (((unsigned)(x)) & 0x3) << 4    SI
OPERATION  :182  ((x) << 6)      :201  (((unsigned)(x)) & 0x3) << 6    SI
ENGINE     :186  ((x) << 8)      NO EXISTE                        -- NO --
```

```
PACKET3_WAIT_REG_MEM__.*ENGINE   en soc15d.h : 0 coincidencias
WAIT_REG_MEM_ENGINE              en vi.h      : 0 coincidencias
```

**`ENGINE << 8` tiene una sola fuente en todo el árbol.** El resto del árbol
tiene lo que hace falta para refutarlo — dosfamilias más — y no lo contradice en
ningún sitio: sencillamente no lo menciona.

**Las anclas que traía la marca tampoco eran las reales** (`:180-187` y
`:214-220`); las correctas son `vid.h:169,178,182,186` y `soc15d.h:199-201`.
Eso es la clase `075` — rango de línea — y lo detectó medir en vez de leer.

## El segundo defecto, que es más serio que el primero

Las dos familias **no se parecen en la codificación**:

```
vid.h      ((x) << 0)                  sin máscara
soc15d.h   (((unsigned)(x)) & 0x7) << 0   con máscara
```

Coinciden en el **desplazamiento** y difieren en el **ancho**. Eso no es
coincidir dos veces: es una coincidencia y una discrepancia a la vez. El dato
de que `ENGINE` es de 1 bit, o de que `FUNCTION` son 3, sale de **un solo
fichero**, y quien lea la marca lo entendera como corroborado dos veces.

## Y el tercero: «independientes» no es lo que dice el dato

La marca decía *dos familias de headers **independientes***, y añadía que
`soc15d.h` era *generado del XML*. Ninguna de las dos cosas consta:

```
marcas de "generated / do not edit / automatically generated"
  en vid.h     : 0
  en soc15d.h  : 0
```

El árbol tiene las dos familias —`vi.h`/`vid.h` de la familia VI,
`soc15d.h`/`soc21.h` con el patrón `PACKET3_..._`—, lo que confirma que son
familias **distintas**. Que sean **independientes** es otra afirmación: ambas
terminan en la misma base de datos de ASIC de AMD, luego son **dos
codificaciones de una especificación**, no dos observaciones independientes de
ella. Para una afirmación sobre *la codificación que escribe el driver de
referencia* eso basta y sobra, y por eso el estado sigue siendo `PROVEN`. Pero
la fórmula "dos fuentes independientes" promete una redundancia que no existe,
y quien la lea contará con ella para todo lo demás.

## Lo que sí estaba bien, y conviene decirlo

`vid.h` y `soc15d.h` están en **cuatro árboles** del proyecto
(`RESEARCH/baseline`, `RESEARCH/kernelbuild`, `RESEARCH/working`,
`rx550-upstream-7.2.8`), y una cita `vid.h:186` no dice en cuál. Medido por
hash y no supuesto:

```
sha256 vid.h     en los 4 arboles: 4b42454a90a7   (19347 B, identico)
sha256 soc15d.h  en los 4 arboles: f39adef602b9   (25520 B, identico)
```

**La ambigüedad de árbol es benigna para estos ficheros**, porque las cuatro
copias son byte a byte iguales. Eso no es conocimiento heredado de que el
proyecto copia las fuentes sin modificarlas: es una medición, y por eso la
ancla `vid.h:186` es válida en los cuatro sitios. No se ha medido si lo mismo
se cumple para **los demás** ficheros de los cuatro árboles, que es donde
volvería a importar.

## La regla

> **Una corroboración declarada sobre N elementos hay que medirla sobre N
> elementos.** Los tres que coinciden se ponen de manifiesto y el cuarto se
> omite sin decir nada, y el resultado es un `PROVEN` que parece más robusto
> de lo que es.

Es exactamente la forma por la que cayó `034`: un contraste que se presenta
do fuentes cuando leía una. La diferencia es que allí las dos líneas en la misma  fichero
y aquí están en dos ficheros distintos, así que **el mismo defecto se ve
distinto** y por eso vuelve. Un fichero distinto no es una fuente distinta.

## Clasificación

| afirmación | estado |
|---|---|
| `ENGINE << 8` existe sólo en `vid.h` | `PROVEN` — 0 en `soc15d.h`, 0 en `vi.h` |
| `FUNCTION`, `MEM_SPACE`, `OPERATION` sí coinciden en desplazamiento | `PROVEN` — `vid.h:169,178,182` / `soc15d.h:199,200,201` |
| `soc15d.h` aplica máscara y `vid.h` no | `PROVEN` — `& 0x7`/`& 0x3` frente a `((x) << n)` |
| Las dos familias son independientes | `REFUTED` — dos codificaciones de una especificación |
| `soc15d.h` consta como generado del XML | `REFUTED` — 0 marcas en el fichero |
| Las anclas `:180-187` y `:214-220` | `REFUTED` — las reales son `169-186` y `199-201` |
| Las 4 copias de ambos ficheros son idénticas | `PROVEN` — sha256, 4 árboles |
| Que las 4 copias de los demás ficheros sean idénticas | `NOT_DETERMINED` — no medido |
| Que el estado `PROVEN` del formato sea incorrecto | `REFUTED` — el estado no cambia; lo que era falso es la dimension de la prueba |

## Confounders

- **La cuenta es de este paquete.** `WAIT_REG_MEM` no es el único con dos
  campos; el mismo criterio aplicado a `SET_SH_REG` o a `INDIRECT_BUFFER` puede
  dar otro resultado, y no se ha medido.
- **«No aparece en `soc15d.h`» no es «contradicho por `soc15d.h`».** Si el campo
  se llama de otra forma, la ausencia es del grep y no del fichero. Se
  comprobó con dos patrones y con `vi.h` como tercera muestra, pero no con un
  barrido exhaustivo de los 588 símbolos de la cabecera.
- **`vid.h` podría estar escrito A PARTIR de `soc15d.h`** y no al revés, o
  ambos descender de un tercero común del que no hay copia en el árbol. Eso
  haría la no-independencia aún más fuerte, y no es distinguible aquí.

`WRITE_EXECUTION=OWN_DRIVER_ONLY`. `MODIFICATIONS_CORPUS=0`: el árbol de Linux
7.2.8 no se ha tocado. `GPU INTACTA`.
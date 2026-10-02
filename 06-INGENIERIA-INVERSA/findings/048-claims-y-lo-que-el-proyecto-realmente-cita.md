# 048 · El proyecto se audita, pero casi no se cita: 114 de 388 afirmaciones tienen verificación automática

`CLASSIFICATION=TOOL` · `TRACK=STATIC` · `GPU INTACTA` · `RUNTIME=NOT_RUN`
`TOOL=tools/claims.py` · `MODIFICATIONS=0` en el corpus

## CUDA principal

`audit_citations.sh` comprueba 254 citas. Pero el proyecto tiene **853 afirmaciones tipificadas**,
y la mayoría no las tiene. Lo primero que hice fue contarlas mal, y el error es instructive.

```
388 afirmaciones exigen respaldo. De dónde lo sacan:
  CITA   fichero.c:123       114   verificable por audit_citations
  CODIGO símbolo o bloque    208   verificable por un LECTOR, no por ninguna herramienta
  NADA                      66
```

**El 71% de las afirmaciones del proyecto se respaldan copiando el código del driver**, no
citando `fichero:linea`. Es un estilo legítimo y a veces mejor — el lector ve el texto sin salir
del documento — pero tiene un coste que no era visible:

> **`audit_citations.sh` vigila el 29%. Los otros dos tercios no tienen ninguna verificación
> automatizada.** Nadie lo había medido.

Eso no es un defecto del estilo. Es un hecho sobre **qué puede vigilar una herramienta**, y
saberlo cambia dónde poner el esfuerzo: los `NADA` de esta tabla son arreglables, y los
`CODIGO` no lo son sin leer prosa.

## Los 66 `NADA` son trabajo real, y es de un minuto

La mayoría son tablas cuyo dato es la palabra «fuente»:

```
| `set_pte_pde` son 3 operaciones: máscara, OR, `writeq` | `PROVEN` (fuente) |
| `cpu_pt_addr` es una dirección de CPU, no MMIO          | `PROVEN` (`writeq` sobre mapping) |
```

La primera dice «fuente» sin decir cuál. La segunda sí dice cuál, y por eso cuenta como `CODIGO`.
**La diferencia entre una fila y otra es la que separa 208 de 66.**

## Dos formas de respaldo que mi extractor confundía

**Un `PROVEN` dentro de una tabla no es respaldo, es una celda.** La primera versión de
`claims.py` imprimía **todas las afirmaciones de 025 y 026** como "sin respaldo" porque contaba
`PROVEN` en celdas de tablas comparativas — donde la celda dice "PROVEN (fuente)" y la
fuente está en OTRO documento. Son afirmaciones sobre Tonga citadas en una tabla de contraste, y
su respaldo es el finding al que remiten, no la fila.

**Y una cita en la cabecera de un finding no es respaldo de una afirmación, es su estado.** Las
cabeceras llevan `RUNTIME=NOT_RUN`, `MODIFICATIONS=0`, `GPU INTACTA`; contarlas como
afirmaciones inflaba el recuento y hacía que un informe de fronteras pareciera un hallazgo. La
primera versión las excluía de forma **accidental** — los tokens llevan `=`, y el extractor exige
el cierre del acent grave — y funcionaba, pero por un motivo que no estaba escrito. En cuanto
alguien ponga un `PROVEN` suelto en la cabecera, pasaría a contarse. Ahora la exclusión es
explícita y el selftest lo verifica con ese caso exacto.

## La convención `RETRACTED_BY=` es ambigua, y el dato lo resolvió

En la cabecera de `043` pone `RETRACTED_BY=043`. **Leído al pie de la letra significa "este
finding está retractado por sí mismo"**, que no significa nada. La intención del autor es
"este finding retracta lo anterior", y el objetivo es `035`.

No elegí una lectura: la resolví desde los datos. Si el número del marcador es el del propio
documento, es el **actor** y el objetivo es otro finding. Si es distinto, es a quien se le
atribuye la acción. El selftest fija las dos.

**Confundir las dos direcciones produce "obsoleto" al revés**, que es peor que no detectarlo:
marca como caducado al finding que corrige. Y esto también es una clase de error, la misma de
`041`: una comprobación que no puede fallar.

## El bug que más daño hizo: el regex de citas exigía una «v»

```
gfx_v8_0.c:661      casa
gmc_8_2_d.h:548     NO CASA
gfx_8_0_enum.h      NO CASA
```

La primera versión de `CITA_RX` exigía `v\d+_\d+` en el nombre. **Las cabeceras de `asic_reg` no
llevan `v`** — llevan `8_2_d`, `8_0_enum`, `8_0_sh_mask` — y son precisamente donde se define un
bit. Resultado: cientos de afirmaciones `PROVEN` marcadas "sin respaldo" que sí lo tenían, en la
celda de una tabla de campos de registro.

Detectado porque el número era absurdo: **274 de 388 sin respaldo** no es una distribución de
documento, es un bug. Con el arreglo, `019` desaparece entero de la lista y `017` baja de 7 a 4.

La lección es la de siempre y ya está escrita tres veces en este proyecto: **un número que es
absurdo es un dato sobre la herramienta, no sobre el corpus.** Si el resultado es 95% fallos,
mira la herramienta antes que el mundo.

## Un límite que decidí no tapar

Había una sección que listaba "clasificaciones fuera de la lista de AGENTS.md". Daba **466
líneas, casi todas macros de C**: un token en acentos graves puede ser una clasificación o un
símbolo del corpus, y la prosa no los distingue. Intenté separarlos indexando los símbolos del
corpus; no funcionó, porque la mayoría son miembros de `enum` y no `#define`, y ampliar el índice
hasta acertar es trabajo infinito para una sección que no decide nada.

**La quité.** Una lista de 466 falsos positivos entrena al lector a saltársela, y una
herramienta cuya sección ya no se lee pierde las secciones que sí sirven. Ahora declara el
límite y sigue.

## La herramienta propone la corrección, y al proponerla encuentra el error de `043` otra vez

Para cada afirmación `NADA`, `claims.py` propone la cita más cercana en una ventana de ±40
líneas, **con la distancia y el signo**. Es una propuesta, no una verificación: puede ser de otra
afirmación, y por eso el número va impreso. A 2 líneas es creíble; a 30 no.

Y 6 propuestas apuntan a **otra generación de ASIC**:

```
:134  PROVEN   propuesta: linea +13  (gmc_8_2_sh_mask.h:3959)  <-- OTRAS GENERACION
:216  PROVEN   propuesta: linea +14  (gmc_8_2_sh_mask.h:6543)  <-- OTRAS GENERACION
:246  PROVEN   propuesta: linea -8   (mmhub_1_0_sh_mask.h:8073) <-- OTRAS GENERACION
```

`gmc_8_2_sh_mask.h` es **Vega20**. Y `mmhub_1_0_sh_mask.h` es MMHUB, que en GFX8 **no existe**:
el bus de memoria cambia de nombre entre GFX8 y Vega10, y es la razón por la que
`amdgpu_discovery_set_gmc_ip_blocks` lleva el comentario *"use GC or MMHUB IP version"* y decide
con `GC_HWIP`.

**Es el error de `035` automatizado y aplicado a las afirmaciones que no tienen fuente:** una
afirmación `PROVEN` cuya única fuente cercana es de otro silicio. No lo afirma — marca, y exige
mirar — pero el patrón ya no depende de que alguien se acuerde.

**Y dos bugs míos en el camino, los dos silenciosos:**

- Guardaba la distancia **absoluta** y la imprimía con `%+d`, así que toda propuesta decía `+N`
  y no se sabía si la fuente estaba antes o después. Un `+` sobre un número que ya es positivo
  es una dirección mentirosa.
- Pasaba la cadena completa a `generacion_de_la_propuesta`, y el ancla `^` no casaba con
  `"linea +13  (...)"` → `None` para todo → **la comprobación de generación no existía y no
  fallaba**. El `selftest` la cazó porque el vector usaba el nombre suelto, no la cadena
  completa, que es como se llama en producción.

## Lo que `claims.py` hace, y lo que no

| | |
|---|---|
| extrae | cada clasificación tipificada, con documento, línea, texto y citas del párrafo |
| clasifica | el respaldo en `CITA` / `CODIGO` / `NADA` |
| propone | la cita más cercana a una afirmación sin respaldo, con distancia y signo |
| señala | si esa propuesta es de otra generación de ASIC |
| clasifica | el respaldo en `CITA` / `CODIGO` / `NADA` |
| cruza | retracciones y dependencias entre findings, en las dos direcciones |
| informa | qué documentos son informe de fronteras y no de hallazgos |

**No comprueba que la cita respalde la afirmación.** Eso exige entender la frase, y una
herramienta que fingiera hacerlo produciría falsa seguridad. Lo que hace es **poner la una al
lado de la otra**, que es lo que hace posible que un humano lo compruebe.

Y la extracción es de prosa: el alcance de «su párrafo» es una heurística, y una afirmación
tipificada mal por el autor se extrae mal. Se imprime el texto entero de cada fila para que
discrepar cueste un segundo.

## UNLOCKS

- **El 29% es el único tramo que una herramienta vigila.** Los 66 `NADA` son arreglables en un
  minuto por finding; los `CODIGO` no lo son sin leer prosa, y conviene saberlo para no prometer
  una verificación automática que no existe.
- **`049` cerró la sospecha que quedó abierta aquí**: resolvió los 497 respaldos en código contra
  el corpus, y encontró **cero** afirmaciones apoyadas en código de otro ASIC sin declararlo. La
  sospecha era razonable; el resultado es un `NEGATIVE_RESULT` con valor.
- La sección de retracciones detectó que `046` declara `GENERALIZADO_POR=047` **hacia atrás** en
  el tiempo — el finding 046 se escribió antes que el 047 que lo generaliza. El grafo de
  dependencias entre findings es ahora legible de un vistazo, y una referencia al futuro es un
  aviso, no un error.
- El bug del regex ha producido un caso más de la regla que `041` ya establecía: **un número
  absurdo es un dato sobre la herramienta**. Es la cuarta vez en este proyecto, y la cuarta
  distinta. Vale como norma general del proyecto.

## Falsación

- La cifra de 114/208/66 se refuta si `CITA_RX` deja de reconocer algún formato de cita real.
  El selftest fija dos casos, uno de ellos `gmc_8_2_d.h:548-553` — precisamente el formato que
  fallaba — y la forma más general es la que se usa.
- La clasificación `CODIGO` puede dar falsos positivos: un token en acentos graves que sea un
  término, no un símbolo. Eso **subestima** los `NADA`, y subestimar es la dirección segura:
  una afirmación que se declara respaldada y no lo está se ve al leer; una que se declara sin
  respaldo y lo tiene se ve en un segundo.
- El resolutor de `RETRACTED_BY` se refuta si un finding usa el marcador con un número que no es
  el suyo queriendo referirse a otro con la misma numeración. Con dos findings `043` en este
  proyecto, eso ya ha pasado una vez.

## Evidencia

```
tools/claims.py          19 vectores de selftest
                         853 afirmaciones extraidas de 98 findings
                         388 que exigen respaldo: 114 CITA, 208 CODIGO, 66 NADA
                         grafo de retracciones, en las dos direcciones
                         68 NADA, con propuesta de cita y su distancia
                         6 propuestas apuntan a otra generacion (043)
suite del driver         22 + 12 + 195 = 229 checks, 0 fallos
crosscheck               10 vectores CLEAN
rx550pm4val              16/16
audit_citations          254 citas, 0 fallos
herramientas             18 en el oraculo, 16 con selftest
corpus                   MODIFICATIONS=0, sha256 12e8d5a973d1ad7c…c3e51941
```

Ningún registro leído de MMIO. `insmod` no ejecutado. `GPU INTACTA`.

# 1517 — El cruce que cazó un fallo era manual y no reproducible. Ahora lo es, y hubo que **romperlo a propósito** para demostrar que detecta

```
AUTOR=AGENTE-INSTR
FECHA=2026-10-05
TIPO=VERIFICACION + DECISION DE ARQUITECTURA
ESTADO=PROVEN (que el cruce detecta; probado por MUTACION)
ALCANCE=/home/lucas/Escritorio/RX550-INVESTIGACION, SOLO LECTURA
MEDIDO=cruce TOUCHES_INTEGRATED x WRITES_FILES sobre 192 ficheros; 0 incoherentes
PRODUCER=RXRE/tools/rxre_touch.py v1.0.0, 18 vectores, todos PASS
PRUEBA=mutacion deliberada del calculo del cruce -> 2 vectores FALLAN con nombre
DECISION=NO integrar rxre_touch en toolkit.py.  Coste MEDIDO, no estimado.
ENCADENA=1515 (el verificador) · 1513 (el campo se reconoce, no se comprueba) ·
  toolkit_cross.py (el precedente de validadores independientes)
```

## Resultado 1 — la integración NO se hace, y el coste está medido

`1515` dejó escrito que el verificador no estaba integrado en `toolkit.py` y que
su coste no estaba medido — exactamente lo que `1513` hizo mal al proponer su
acción sin medirla. Así que lo medí antes de hacerlo.

**Medición 1 — el coste de la integración.** `toolkit.py` está en
`08-ARQUITECTURA/tools/`; `rxre_touch.py` en `RXRE/tools/`. Un import entre
ellos son **4 niveles de ruta y ningún módulo común**: o `sys.path`, o ruta
absoluta. coupling dos árboles por ruta absoluta.

**Medición 2 — qué gana la integración.** `toolkit.py` valida **68 ficheros**
(los de su propio directorio, `os.listdir(HERE)`). `rxre_touch` mide **192**, de
los cuales 74 declaran el campo. Ganancia: 124 herramientas que nadie verificaría.

**Medición 3 — y la que decide.** El proyecto **ya respondió a esta pregunta**,
en `toolkit_cross.py`, y su docstring lo dice:

> «POR QUÉ NO ES UNA SÉPTIMA HERRAMIENTA DE VALIDACIÓN — Hay seis herramientas
> que validan el resto del árbol. Cada una mide una cosa, y cada una mide lo
> SUYO. […] No se comprueba nada nuevo. Se CRUZAN lo que las seis ya saben.»

Los validadores se mantienen **independientes** y el cruce se hace aparte. Mi
integración iba **contra un precedente escrito del propio proyecto**. No se hace,
y la razón queda en el informe, en `por_que_no_se_importa`.

## Resultado 2 — el cruce que encontró el fallo era manual

En `1515` el cruce entre `TOUCHES_INTEGRATED` y `WRITES_FILES` lo ejecuté **a
mano**, con un script de shell, porque fue lo que reveló que `campos_pm4.py`,
`revkit/pm4dec.py` y `revkit/sello.py` declaraban `WRITES_FILES=no` y a la vez
`TOUCHES_INTEGRATED=no` sin respaldo.

Eso es un **artefacto no reproducible**: la evidencia del hallazgo dependía de
que alguien volviera a escribir ese script. Ahora el cruce está **dentro** de
`rxre_touch`, con la regla escrita:

```
WRITES_FILES == "no"   =>   el veredicto de la frontera NO puede ser
                             NO_DETERMINED
```

porque `no` afirma que no escribe nada, y una herramienta que delega no puede
sostener esa afirmación sobre la frontera. Y el inverso también.

**Resultado:** 192 filas cruzadas, **0 incoherencias** — y la regla dice **por
qué** cero es lo correcto, no sólo que lo sea.

## Resultado 3 — el cruce estaba APAGADO, y lo vi rompiéndolo

Escribí tres vectores para el cruce. Los tres **pasaban**. Y la forma de saber si
un vector puede fallar es romper lo que vigila.

**Primera prueba — mutación del cálculo.** Cambié `r["coherente"] = ...` por
`True`. Los tres vectores **siguieron PASS**.

Motivo: los tres leían el **resultado** (`n_incoherentes`, `incoherentes`), que
es exactamente lo que la mutación había cambiado. Romper el cálculo sin romper
su salida no lo nota un vector que lee la salida.

> un vector que lee el resultado de un cálculo no vigila el cálculo

**Segunda versión.** Reescribí el vector para deducir la propiedad de los **dos
campos crudos** (`writes_files` y `touches_integrated`), sin mirar `coherente`.
Sigue pasando con la misma mutación.

Motivo, y es el punto entero: **`mmap` es 0 en todo el árbol**, así que la
mutación `borra_otro → delega` no creaba ninguna violación. **Los datos estaban
limpios.** Un vector que vigila una propiedad que nadie viola no se prueba
así: hay que mutar algo que **cree** la violación.

**Tercera prueba — la mutación correcta.** «Tratar cualquier borrado como
delegación» es un bug plausible y toca datos reales (`borra_otro` = 48). Resultado:

```
FAIL toda NO_DETERMINED delega por subprocess DE VERDAD
FAIL y si se computo, no hay INCOHERENCIAS entre los dos campos
     [('tools/trace_path.py', 'no', 'NO_DETERMINED')]
```

**El cruce detectó, y nombró la fila.** Eso es un vector probado falsable.

**Y un cuarto defecto que salió por el camino:** esa mutación reventó con
`KeyError: 'delega'`, porque el motivo se interpolaba con `vb["delega"]`. Es
**ruido, no una detección**:

> un fallo que revienta no es un vector que falla

Arreglado para que la medición sea observable: se cuenta lo que **hay**, y el
borrado se declara aparte en el motivo en vez de indexar una clave que puede no
estar.

## Procedencia

- `STATIC` — AST sobre 192 ficheros. Sin ejecutar ninguna herramienta.
- `CROSS-CHECK` — `delega` por AST (156) y por regex con prefijo (169); los 28
  métodos de nombre coincidente explican la diferencia. **Y ahora el cruce con
  `rxre_contracts.py`, que es un instrumento distinto sobre el mismo fichero.**
- **PRUEBA DE MUTACION** — el cruce se rompió a propósito dos veces y se
  restauró; el estado sano da 18/18 y la versión rota da 2 FAIL con nombre.
  Comprobado por fuera: `trace_path.py` declara `WRITES_FILES=no`.
- `EJECUCION` — cinco instrumentos, `toolkit.py`, `toolkit_cross.py`.
  **Sin MMIO, sin TLB, sin insmod.** `GPU INTACTA`.

## Lo que NO se afirma

- **No se afirma que la regla del cruce sea la correcta.** Es la que sostiene
  hoy la coherencia entre dos campos. Si los dos significaran cosas distintas,
  habría que revisarla — y eso no está medido.
- **El verificador sigue sin estar integrado en ningún runner.** Es un
  instrumento que hay que ejecutar. `toolkit_cross.py` no lo cruza todavía, y esa
  es la acción siguiente natural, con el mismo patrón que ya usa.
- **La cobertura sigue parcial**: 118 de 192 no declaran el campo.
- **No se ha modificado ningún fichero de validación en este hallazgo.** Sólo
  `RXRE/tools/rxre_touch.py`.

## Dos notas de método

**La primera: hay que romper el vector para saber si existe.**

Escribí tres vectores, los tres pasaron, y eso no me dijo nada. Lo que lo dijo fue
romper deliberadamente lo que vigilan y ver **qué falla y con qué nombre**. La
primera mutación pasó, la segunda también, y la tercera —la que crea una
violación en vez de romper el cálculo— sí falló, y nombró `trace_path.py`.

Tres intentos, y el que funcionó fue el que cambió **los datos**, no **el
código**.

> un vector que vigila una propiedad que nadie viola no se prueba: se rompe

**La segunda: el patrón del proyecto era la respuesta, y yo iba a contradecirlo.**

Iba a integrar el verificador en `toolkit.py` porque parecía obvio: un validador,
otro validador, el primero debería conocer al segundo. Pero el proyecto **ya lo
decidió en contrario** y lo escribió en el docstring de `toolkit_cross.py`: los
validadores se quedan independientes y el cruce se hace aparte.

Importar habría acoplado dos árboles por ruta absoluta —**4 niveles medidos,
ningún módulo común**— para conseguir una cobertura que el cruce ya da, y que es
de todas formas más ancha y más fácil de auditar.

*La integración obvia no es la correcta cuando el proyecto ya escribió por qué
no lo hace.*
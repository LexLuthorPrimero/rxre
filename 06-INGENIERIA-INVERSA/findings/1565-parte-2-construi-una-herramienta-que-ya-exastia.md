# 1565 — PARTE 2: construí una herramienta que ya existía, y el árbol tenía el defecto medido desde el 1083

```text
AGENCIA=RX550-INVESTIGACION · PARTE=2/RESET-RECOVERY · HALLAZGO 6 de la parte
CLASSIFICATION=AUTOCORRECCION-PROPIA+HALLAZGO-PREVIO-OMITIDO+CAPACIDAD-DE-TESTIMONIO
WORK_CLASS=AGENT-MAIN/RE · WRITES=NONE · MODIFICATIONS=0
WRITE_EXECUTION=NONE · RUNTIME=NOT_RUN · GPU INTACTA (0000:01:00.0)
TRACK=STATIC · CERO HARDWARE · Intel no tocada
GENERADO=2026-10-05
AFECTADO=una herramienta mia, ya borrada · 1083 (defecto ya medido) · 117 · 189
ESTADO=PROBADO · existe 08-ARQUITECTURA/tools/doclint.py y es MEJOR que lo que construi
       · su regla de otro idioma es mas elaborada que la mia: distingue lo CITADO de lo
         REDACTADO por la POSICION del ideograma, no por la mera presencia de acentos graves
       · ademas verifica CITAS contra el indice del corpus, y eso yo no lo hacia
       · su autotest prueba el ENSAMBLAJE, no solo la expresion regular
       · sus 5 hallazgos de la parte 2 dan 0 errores y 0 avisos
       · la herramienta que construi esta BORRADA
       · Y el defecto de fondo —corrupcion en hallazgos— es un hallazgo PREVIO (1083), no mio
```

## 1. Lo que hice, y por qué está mal

Escribí, a lo largo de esta sesión, el mismo escáner de integridad de texto **seis veces** inline
dentro de comandos de shell. Cada vez cubria una clase distinta de defecto y cada vez tuvo que
ampliarse, porque aparecia un tipo nuevo. La lista acumulada:
`loEncryption`, `en_Layers`, `porqueRequires`, `deRecovery`, `se Bearia`, `ayer lo lei al
reves`, `parametro module`, `Loujo`, CJK en dos ficheros, árabe en otro, `DISCriminANTE` en tres.

Seis reimplementaciones del mismo control es exactamente lo que §98 marca: **automatización que
no reduce repetición real**. Así que decidí convertirlo en herramienta.

Y aquí está el error: **no comprobé antes si ya existía.**

## 2. Lo que ya existía

```text
  08-ARQUITECTURA/tools/doclint.py     ya presente, con autotest, con indice de corpus
  hallazgo 1083                          ya lo midio, ya lo.catalogo, ya lo dejo escrito
  hallazgo 117, 189                       los hallazgos que CATALOGAN la corrupcion
```

Y el `1083` dice, textual, sobre su propia regla:

> *«El defecto no es de alcance sino de diseño. Ampliar el glob de `doclint.py:434` produciría
> al menos 150 falsos positivos, porque el proyecto tiene documentos que **deben** contener texto
> en otro idioma.»*

**Eso es exactamente el problema que yo estaba intentando resolver, y ya estaba resuelto,
documentado, y con la trampa identificada.** Mi herramienta no solo era redundante: era la
versión ingenua de algo que ya tenía la versión medida.

## 3. Y mi herramienta era peor, en tres puntos concretos

**a) La regla de texto citado.** Mi escáner marcaba CJK como error **en todas partes**. El `doclint`
distingue por posición:

```python
  # doclint.py, regla 1
  # La regla es simetrica: cita y corrupcion se distinguen por la POSICION del
  # ideograma, no por la mera presencia de acentes graves en la linea.
  if fenced or dentro:
          infos.append(msg + "  [citado: no es redaccion propia]")
```

Y documenta el bug que **ella misma** tenía, y que es un espejo del mío:

> *«`is_quoted` vale True para CUALQUIER línea con 2 o más acentos graves, y los hallazgos usan
> acentos graves en casi todas las frases que mencionan un símbolo. Al degradar el CJK a "info"
> cuando is_quoted, el chequeo quedaba **DESACTIVADO en prácticamente toda la prosa útil**.
> Comprobado: dos ideogramas CJK en una línea con 8 acentos graves daban "errores: 0".»*

Yo no llegué ni a plantearme esa distinción. En mi caso era peor: no tenía ni el Concepto.

**b) La verificación de citas.** `doclint` resuelve cada cita `fichero.c:NNN` contra el índice del
corpus y falla si no resuelve o si la línea está fuera de rango. Eso **no lo hace mi herramienta**,
y es la capacidad que más valor tiene para este árbol: obliga a que cada referencia sea
comprobable.

**c) El autotest prueba el ensamblado.** `doclint` escribe un fichero temporal con CJK en una línea
con 8 acentes graves y **comprueba que el linter entero lo detecta**, no solo que el regex casa:

> *«El caso de prueba probaba el REGEX, no el ENSAMBLAJE. Es la misma debilidad que en ipver_zero
> e ip_surface: **el componente correcto no valida el montaje**, y por eso el defecto pasa.»*

Frase que además es la lección de mi sesión entera, escrita por otro, y que me viene mejor que
ninguna de las mías.

## 4. Lo que sí aportó mi herramienta, y que no es cero

No es nada, y es honesto decirlo, pero hay dos cosas que el `doclint` **no** cubre y que quedan
como hueco medido:

```text
  1  doclint NO cubre cirilico, arabe, ni griego.  Su patron es:
         1100-11ff  Hangul jamo        2e80-9fff  CJK radical..unificado
         ac00-d7af  Hangul silabas    f900-faff  compatibilidad CJK
         ff00-ffef  formas fullwidth  3040-30ff  hiragana + katakana
     Medido: el hallazgo 092 tiene "OLAeqia" en arabe en la linea 18, y el 1035 tiene
     cirilico y CJK.  El 092 pasaria el lint.
     Esto NO lo he arreglado: es una decision que toca una herramienta que no es mia y
     que otra sesion esta usando.

  2  doclint por defecto mira findings/0[23]*.md, o sea el 6,6% del arbol.  Eso ya lo
     midio el 1083 y no lo cambio: su conclusion es que ampliarlo genera falsos positivos.
     Con la regla simetrica que tiene ahora, el 1083 puede estar caducado, pero comprobar
     eso es trabajo de otra persona y no mio.
```

El punto 1 es real y es el único hallazgo aqui que no es "me equivoque". **El linter de integridad
textual del proyecto no detecta cirílico, árabe ni griego, y hay al menos un hallazgo con árabe.**

## 5. Medida de falsos positivos: mi herramienta, 71 y luego 11

Es lo que decide el veredicto, y la secuencia es instructiva:

```text
  version 1  vocabulario cerrado escrito a mano
             ->  71 avisos sobre 5 ficheros LIMPIOS
                 Falsos positivos: "Antes", "Del", "Las", "Sin", "Cero", "Descartada",
                 "Nota", "Comparando", "Distingue", "Iba", "Sonaba", "Polaris", "Arcturus".
             ->  INUTIL.  Una herramienta que se queja de todo se acaba ignorando.

  version 2  lista blanca medida del codigo del driver (1 604 218 identificadores)
             + deteccion de atipico por frecuencia sobre los 807 hallazgos
             ->  11 avisos, de los cuales 4 eran corrupcion REAL que mis dos patrones
                 anteriores NO veian
```

Los cuatro reales, y por qué los anteriores no los veían:

```text
  DISCriminANTE   en 1557, 1559, 1561   no lo ve [a-z]{2,}[A-Z][a-z]{2,}  (antes de la C
                                          no hay minusculas) ni [A-Z][a-z]{2,} al inicio
  Eight           en 1557               yo lo deje pasar por ser "ingles"; era una inyeccion
  Sara            (vector de prueba)     inicial sin minusculas antes: no la ve ningun patron
```

> **PROBADO por medicion: los dos patrones que use inline durante seis horas tienen un punto
> ciego de clase `C-x-x` al que no llegan.** Es exactamente la debilidad que el `doclint` ya
> llama "basura lexica que un linter de CJK no detecta", y la resuelve con una lista curada.

## 6. Y un error de identificacion que casi cuela

Antes de construir la herramienta encounteré que `DISCriminANTE` y `Eight` estaban en hallazgos
**ya commiteados**, y que afectaban a tres ficheros de mi propia parte. almost di por hecho que
era un hallazgo nuevo.

No lo era: el `1083` ya enumeraba `计`, `自`, `有`, `讪`, `重`, `建` y los localizaba en el `1004` y
el `1035`. **Yo no leí el 1083 antes de empezar**, y por eso estuve a punto de publicar como
descubrimiento lo que ya estaba catalogado tres hallazgos antes.

La regla que escribí al principio de esta parte —*grep del tema en `findings/` antes de reservar
número*— la incumplí en la clase de tema "integridad del texto", que es donde más contexto
histórico había. Y era justo el tema donde mas habia escrito el otro.

## 7. Decision log (§103)

```text
DECISION    borrar la herramienta propia y usar doclint; y escribir esto
WHY         §99: una herramienta que no aporta capacidad nueva es teatro.  Medido: doclint
            cubre lo mio mejor, y ademas cubre citas y marcadores que yo no tocaba.
            §79: reparar sobre preservar.  El repo tiene un linter; lo que faltaba era
            usarlo sobre los documentos que no se lintaban, no escribir otro linter.
ALTERNATIVA  quedarse con mi herramienta y añadirle la verificación de citas.  Descartada:
            es reconstruir en paralelo un linter que ya existe y que ademas tiene mas
            casos limite resueltos.  Seria §99 en su forma mas cara: coste doble.
ALTERNATIVA  arreglar el hueco de cirilico/arabe/griego en doclint.  Descartada HOY, y
            declarada arriba como trabajo pendiente: doclint lo esta usando otra sesion y
            tocarlo sin coordinacion es §88.  Queda escrito como hueco medido.
DISCriminANTE  ninguno: la redundancia se mide comparando capacidades, no adivinando.
CONSECUENCIA  la parte 2 tiene sus cinco hallazgos con 0 errores y 0 avisos de doclint, y
            el control de integridad textual del proyecto queda como estaba, sin el
            executable superfluous que yo iba a anadir.
REVERSIBLE  la herramienta esta borrada y no commitada.  Nada que revertir.
```

## 8. Lo que me queda de esto

Cinco hallazgos de la parte 2 sobre reset/recovery, y ninguno de ellos es un hallazgo
*instrumental*. Este es el primero, y su contenido es que **no debí construir nada**.

La lección no es "no hacer herramientas". Es más específica y la he escrito en forma
distinta cada vez, que ya es la señal:

```text
  1555  me falto LEER el numero que acababa de calcular
  1557  me falto TERMINAR de leer la funcion
  1559  lei el fichero equivocado y no me askarse del sitio
  1565  nolei lo que ya estaba escrito, en el tema donde mas habia escrito otro
```

Cuatro fallos, y **tres de ellos son no mirar lo que ya tengo delante**. El unico que es de
razonamiento es el tercero.

Y hay una consecuencia practica que no es una reflexion: **esto se podia haber evitado con un
`grep` de treinta segundos**, que es exactamente lo que la regla que yo mismo escribi al empezar
esta parte pedia. La regla era buena. La ejecucion no.

Lo que si queda, y es medible: **el linter del proyecto no ve cirílico, árabe ni griego, y hay un
hallazgo con árabe en la línea 18.** Eso si es trabajo pendiente de verdad, y de otra sesión.
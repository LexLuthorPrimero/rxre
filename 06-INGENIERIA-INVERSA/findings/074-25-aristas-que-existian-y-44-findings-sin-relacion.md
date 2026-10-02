# 074 · 25 aristas que existían y no se contaban, y 44 findings que no se declaran deudores de nadie

```
ID:           074
RETRACTADO_PARCIALMENTE_POR=091   (solo la clausula del bloqueo; el resto del hallazgo sigue vigente)
CLAUSULA_RETRACTADA=INSECURE_SIG_CLAIM
TIPO:        HALLAZGO + CIERRE DE DOS NEXT ACTION
ALCANCE:     tools/relations.py, tools/artifacts.py, KNOWLEDGE-GRAPH.md
TOOL:        tools/relations.py v1.0.0, selftest 27/27 PASS (6 vectores nuevos)
GPU:         INTACTA
```

## RESUMEN

Los dos `NEXT ACTION` de `073`, los dos cerrados.

| | antes | ahora |
|---|---|---|
| filas de arista | 64 | **89** |
| pares `(desde,hacia)` distintos | 57 | **78** |
| con destino ambiguo | 53 | 73 |
| findings con aristas salientes | 37 | 38 |

Las 25 aristas nuevas salen de **etiquetas con varios destinos** que el
extractor leía solo hasta el primero y descartaba el resto en silencio:

```
CORRECTS=040,041,042,043,044,045     ->  6 findings en UNA etiqueta
COMPLEMENTS=047,048                   ->  2
COMPLEMENTS=046,050                   ->  2
COMPLEMENTS=040-smu-....md,041-....md,->  2 (lista de ficheros)
CONTINUES=017–029                     -> 13 (intervalo con RAYA U+2013)
```

**Todas resuelven.** 15/15 destinos, ningún caso perdido.

## 1 · EL NÚMERO QUE YO MISMO ESCRIBÍ MAL

Escribí en el comentario del código, antes de que la rama existiera:

```
# 64 -> 64 + 10 (multivalor) + 2*2 (rangos) + 2 (lista de ficheros) = 78
```

Traté cada rango como si fueran dos findings. `CONTINUES=017–029` es un
intervalo de **trece**. El total real es **25**, y el grafo queda en 89.

> Ese total estaba escrito como si fuera medido y no lo estaba. Es el mismo
> patrón de `072` y `073` — *un número puesto a mano que se lee como
> medido* — y en esta ocasión era mío y del turno anterior. Lo que lo
> distingue es que aquí el número estaba en un comentario que nadie iba a
> mirar, y aun así se iba a leer.
>
> Por eso el total sale de `len(extra)` y la arista lleva en la columna `nota`
> la etiqueta original con `resueltos/total`:
>
> ```
> | 046 | `CORRECTS` | `CORRIGE!` | 040 | `040,041,042,043,044,045` 6/6 |
> ```
>
> Una arista de una etiqueta con seis destinos tiene que poder distinguirse
> de una de una etiqueta con uno. Si no, el grafo no dice de dónde salió cada
> fila.

## 2 · `fullmatch`: EL ANCLA QUE AQUÍ SÍ ERA LA SOLUCIÓN

El clasificador de rangos tenía:

```python
re.search(r"\d{3}[\u2013\u2014-]\d{3}", cuerpo)      # ← así
```

y `AGENTS.md:617-627` salía como intervalo de findings. Motivo: `617-627` son
tres dígitos y un guion. **Una cita a un fichero que no es un finding, con un
rango de líneas, se clasificaba como un intervalo de findings.**

Corregido con `fullmatch`, que obliga a que el intervalo **sea** el valor.

> **El anclaje no es bueno ni malo. Es bueno cuando delimita lo que el campo
> ES, y malo cuando delimita lo que PUEDE contener.**
>
> - En `072` el `^` delimitaba lo que la etiqueta *podía contener* (y la línea
>   entera, cuando la etiqueta era una fracción de ella) → **0 etiquetas**.
> - Aquí el anclaje delimita lo que el campo *es*: un intervalo de findings
>   tiene que ser el valor entero, no una subcadena de otra cosa.

Es la lectura opuesta del mismo defecto, y por eso merece quedar escrita.

## 3 · UN VECTOR QUE ERA INCORRECTO, Y NO EL CÓDIGO

Escribí este vector:

```python
if RANGO_RX.fullmatch("617-627"):
    print("  FAIL un rango suelto sin nada delante casa; deberia anclarse")
```

**El vector estaba mal, no el código.** `617-627` es un intervalo válido: si
alguien escribe `CONTINUES=617-627` son dos findings y deben casar.

Lo que protege de `AGENTS.md:617-627` no es «anclar el número»: es que el
intervalo sea **todo** el valor. El vector afirmaba una propiedad que el
`fullmatch` no tiene y no necesita.

Este es el **segundo caso de la misma semana** en que un `FAIL` de mi selftest
era un test malo y no un bug (el primero, el fixture sin `043`). La tentación en
ambos es idéntica: *arreglar el código*. Y el código estaba bien.

> **Un `FAIL` de un selftest es una afirmación sobre el código, y hay que
> comprobar si la afirmación es correcta antes de tocar el código.** Es el
> mismo principio que con un `NEGATIVE_RESULT`: un resultado que no cuadra no
> es permiso para cambiar lo que se midió.

## 4 · QUIÉN NO DECLARA NINGUNA RELACIÓN

La pregunta del `NEXT ACTION` era si los findings sin relación están sin
relación **de verdad** o simplemente **no la declaran**. Son dos estados muy
distintos, y se distinguen:

```
findings (ficheros):      117
con relación declarada:    73
SIN relación declarada:    44

  con cabecera de metadatos pero sin verbo de relación: 24
  sin NINGUNA etiqueta (predatan la convención):        20
```

| grupo | qué es | qué se hace |
|---|---|---|
| **24 con cabecera** | están bien formados y no declaran deudor de nadie | omisión |
| **20 sin etiqueta** | no tienen el formato de cabecera | antecedente a la convención |

Los 20 son `001-…`, `002-…`, `003-…`, `005-…`, `006-…`, `007-…`, `008-…`,
`009-…`, `010-…`, `011-…`: los primeros findings del proyecto, anteriores a que
existiera la convención de `ETIQUETA=valor`.

**No se pueden sumar.** Un finding sin etiqueta no está «sin relación»: no
tiene dónde declararla. Y un finding con cabecera y sin verbo de relación sí
tiene dónde, y no lo ha usado.

### Los dos denominadores, y por qué se declaran los dos

`KNOWLEDGE-GRAPH.md` dice «78 findings sin ninguna relación declarada» y este
informe dice 44. **No es una contradicción: son denominadores distintos.**

- `KNOWLEDGE-GRAPH` cuenta **números distintos** con arista saliente (38).
- Este informe cuenta **ficheros** (117).

Con 35 números duplicados, ambos números son ciertos y no comparables. Por eso
el informe declara los dos en vez de elegir uno:

```
Y CUIDADO con el denominador: KNOWLEDGE-GRAPH.md cuenta
NUMEROS distintos con arista (38) y este cuenta FICHEROS (73).
Con 35 numeros duplicados, los dos numeros no son comparables,
y por eso se declaran los dos en vez de elegir uno.
```

Ésta es la segunda vez en dos hallazgos que sale un «contradicción» entre
artefactos que no lo es. La primera fue `KNOWLEDGE-GRAPH` (8 aristas) contra
`CONTRADICTIONS` (15), y sí era real. Distinguir una de otra es lo que hace el
trabajo: **dos números distintos sobre el mismo nombre no se promedian ni se
elegen — se nombran.**

## 5 · ERRORES PROPIOS EN ESTA ITERACIÓN

| error | detectado por |
|---|---|
| calculado «78» donde eran 89, tratando un intervalo como dos findings | el informe real, al ejecutar |
| 4 claves (`multivalor`, `rango`, `lista_fich`, `no_finding`) ausentes del `--json` | `KeyError` al consumptionar el JSON |
| `extra` devuelve 7 campos y `aristas` espera 5 | `too many values to unpack` → **rc=2, nada escrito** |
| `AGENTS.md:617-627` clasificado como intervalo de findings | lectura del informe: 2 findings numerados 617 y 627 que no existen |
| vector `617-627` con la expectativa invertida | el `FAIL` mismo, contra el sentido común del rango |
| `CIERRA!`/`CONTINUA!` contadas como familias distintas (18 → 14) | total que no cuadraba con `relations.py` |
| `grep -c '\`!'` dio 0 sobre 53 marcas | el `!` va dentro del backtick: `` `CIERRA!` `` |

El `KeyError` y el `unpack` son la misma clase: **el contrato entre dos
herramientas es el `--json`, y cambiar la salida sin cambiar el consumidor
parte el consumidor**. En este caso lo detectaron los dos lados, y en ambos
casos el que se rompió fue el que yo había terminado de escribir antes.

## 6 · ESTADO

```
artefactos         7 generados, todos con marca GENERADO
findings           117 ficheros en 73 números · 35 números ambiguos
grafo              89 filas · 78 pares · 14 familias · 73 con destino AMBIGUO
                   25 de esas 89 salen de etiquetas con varios destinos
contradicciones    15 aristas de contradiccion, 10 verbos
frontera           258 huecos abiertos, por 7 vías de cierre
relaciones         19 verbos · 263 NO_RESUELVE = 221 campo + 42 resto
                   resto = 33 prosa + 3 multivalor + 1 rango
                           + 1 lista de ficheros + 3 no-finding
declaración        73 findings con relación · 44 sin ella
                   (24 con cabecera y sin verbo · 20 sin ninguna etiqueta)
citaciones         275 resueltas, 0 fallos
selftests          relations 27/27 · frontier 12/12 · claims 20/20
                   artifacts 14/14 · rx550pm4val PASS · rx550ref PASS
GPU                01:00.0 Lexa PRO rev c7, INTACTA
```

## 7 · LO QUE SIGUE ABIERTO, Y CÓMO SE PARTE

**A · Cerrable con herramienta, ahora:**
- **Renumerar los 35 números duplicados.** Es trabajo de edición, no de
  herramienta, y no se automatiza: renumerar un finding rompe las aristas de
  todos los que lo citan por su número, y rehacer esas aristas exige saber a
  cuál de los dos iba cada una — que es justamente lo que el `!` declara
  irresoluble. **Este es el bloque que no tiene atajo**, y conviene decirlo en
  vez de prometer una herramienta.
- **Dar cabecera a los 20 findings sin etiqueta.** Mecánico, y auditable: tras
  hacerlo, «sin ninguna etiqueta» debe ser 0.

**B · Lo que el proyecto dice de sí mismo:**
- De 117 findings, **73 declaran relación y 44 no**. Y los verbos que más se
  usan —`CONTINUES` (29) y `COMPLEMENTS` (10)— **no aportan nada**: ninguno
  dice de qué depende el finding, solo que existe uno anterior. La pregunta que
  no tiene respuesta medible es *qué se corregiría si el anterior se cayera*,
  y para eso el vocabulario actual no sirve: no tiene ningún verbo de
  dependencia.
- `CONTINUES` es el verbo más usado del proyecto y es **semánticamente vacío**
  en un grafo de evidencia: una arista que dice «hay un anterior» no
  justifica nada. De las 89 aristas, cuántas cambian una conclusión si se
  borran.

**C · Sin atajo técnico:**
- **`FUNCTION=always`**: `NOT_PUBLISHED`, discriminante escrito en `056 §7`,
  requiere inyección PM4/IB.
- **Cargar un módulo propio**: `CONFIG_MODULE_SIG_ALL=y` +
  > **[091] CORRIGE ESTA CLAUSULA**: no hay bloqueo tecnico. Lo que se leyo fue
  > `CONFIG_MODULE_SIG_ALL` y **no** `CONFIG_MODULE_SIG_FORCE`, que esta
  > `# CONFIG_MODULE_SIG_FORCE is not set`. Medido en este host:
  > `lockdown=[none]`, `SecureBoot disabled`, y un `.ko` propio COMPILA con
  > `vermagic` identico y SIN FIRMAR. Lo que queda es NIVEL 4
  > (`BLOCKED_BY_AUTHORIZATION`), que es otra cosa. Ver 091.
  `CONFIG_SECURITY_LOCKDOWN_LSM=y` sin clave de firma. Pared técnica.

---

```
RESULTADO DE ITERACIÓN

Entregado:
  25 aristas que existian y no se contaban (64 -> 89 filas, 57 -> 78 pares)
  MULTIVALOR, RANGO (con raya U+2013) y LISTA_FIC generan una arista por
    destino, con la etiqueta original y resueltos/total en la columna nota
  seccion QUIEN NO DECLARA NINGUNA RELACION, con los dos denominadores
    declarados por separado

Medido:
  117 findings · 73 con relacion declarada · 44 sin ella
    24 con cabecera y sin verbo de relacion  (omision)
    20 sin ninguna etiqueta                 (anteriores a la convencion)
  15/15 destinos de las etiquetas multivalor resuelven
  73 de 89 filas con destino AMBIGUO

Corregido:
  `re.search` -> `fullmatch` para el intervalo: `AGENTS.md:617-627` dejaba de
    clasificarse como intervalo de findings
  4 claves que faltaban en el JSON de relations.py
  aristas de 7 campos donde el grafo espera 5

NEXT ACTION:
  El de mas valor medible, y es el unico que no he hecho: CUANTAS DE LAS 89
  ARISTAS SOSTIENEN ALGO. `CONTINUES` (29) y `COMPLEMENTS` (10) no cambian
  ninguna conclusion si se borran: declaran que hay un anterior. `CORRECTS`
  (11 con las multivalor), `RETRACTED_BY`, `RECTIFIES` y `CERRADO_POR` si.

  El discriminante ya existe y es mechanical: para cada arista, ¿el finding
  destino contiene una afirmacion que el origen NECESITA? Si se responde
  leyendo el finding destino, es trabajo de lectura. Si se responde por el
  verbo, sale un numero que no significa nada -- porque entonces lo que se
  mide es el vocabulario, no el grafo.

  Lo que SI es un UN-GREP y tiene valor: de los 44 findings sin relacion,
  cuantos citan en su cuerpo a un finding del que dependen SIN declararlo.
  Eso es una omision recuperable, y la cifra dice si la convencion se sigue
  o se abandonó.
```
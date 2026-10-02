# 077 · 141 citas que eran rangos de líneas, y 10 omisiones que sí son reales

```
ID:           077
TIPO:        HALLAZGO
ALCANCE:     tools/relations.py, 06-INGENIERIA-INVERSA/findings/
TOOL:        tools/relations.py v1.0.0, selftest 27/27 PASS
GPU:         INTACTA
CIERRA:      el NEXT ACTION de 074
```

## RESUMEN

El `NEXT ACTION` de `074` pedía el dato de los findings sin relación. Está
medido, y el camino hasta él tiene **tres falsos positivos encadenados**, cada
uno con su propia firma.

| etapa | resultado | por qué estaba mal |
|---|---|---|
| 1ª | **141 citas** desde findings sin relación | el patrón `\b(\d{3})[-_][a-z0-9-]+` casa **rangos de líneas** del corpus |
| 2ª | **0 omisiones** | el índice guardaba `f[:-3]` y la consulta pedía `f`: no hablaban el mismo idioma |
| 3ª | **10 omisiones, 34 citas** | correcto |

## 1 · LAS 141 CITAS QUE ERAN RANGOS DE LÍNEAS

Primera medición, con un patrón aparentemente sensato:

```python
CITAF = re.compile(r'\b(\d{3})[-_][a-z0-9-]+')
```

Da 141. Y lostargets más citados son `617` (12), `858` (4), `817` (4), `272`
(3), `668` (3), `691` (3), `495` (2), `335` (2). **Ninguno de esos findings
existe.** Muestreando el contexto:

```
001-amdgpu-location.md:80   858-1201   `struct amdgpu_device` ocupa las líneas 858-1201
001-amdgpu-overview.md:185  858-1201   inspección manual del struct (líneas 858-1201 de `amdgpu.h`)
005-cs-ioctl-analysis:112  983-986    /* amdgpu_drm.h:983-986 */
006-lsdma-packets.md:34     495-497    `cikd.h:495-497`:
006-lsdma-packets.md:65     335-338    Layout real, `sid.h:335-338`:
007-gfx8-pm4-format.md:226  330-355    Definiciones de `sid.h` líneas 330-355
```

Todos son **rangos de líneas de un fichero del corpus**, escritos como
`NNN-MMM`. El patrón no distingue `858-1201` (líneas de `amdgpu.h`) de
`002-module-sections` (un finding), porque los dos tienen la misma forma:
tres dígitos, un guion, más texto.

> **Ésta es la octava aparición de la misma clase**: *coincidencia por
> subcadena / por forma, en vez de resolución contra un índice*. Ya con
> identificadores (`SGX` dentro de `SOC15D_SGX`), con `\b` tras `_`, con
> `re.match` vs `re.search`, con nombres de fichero sin subdirectorio, y con
> `NLL-NNN` de ahora.
>
> Y tiene la misma propiedad de siempre: **el resultado es plausible**. «141
> citas desde findings sin relación declarada» se lee como un dato sobre el
> proyecto. Era un dato sobre el patrón.

### El discriminante

**Una cita a un finding acaba en `.md`.** No hace falta más:

```python
CITA_MD = re.compile(r'\b(\d{3}[a-z0-9-]*\.md)\b')
t = idx_c.get(m.group(1))        # y se resuelve contra el índice, no por forma
```

Las dos cosas: la extensión **y** la resolución contra el índice. Con la
extensión sola, `amdgpu.h` casaría en `sid.h:335-338.md` si algo lo escribiera
así; con el índice solo, `858-1201` no resuelve a nada y también queda fuera.
Las dos juntas son lo que hace la cifra defendible.

## 2 · EL CERO QUE NO ERA UN CERO

Corregido el patrón, la segunda medición dio **0 omisiones**: ningún finding sin
relación citaba a otro.

**Era falso.** El índice guardaba las claves sin extensión y la consulta pedía
con extensión:

```python
idx[f[:-3]] = ...                 # "002-module-sections"
CITA_MD = re.compile(r'\b(\d{3}[a-z0-9-]*\.md)\b')   # busca "002-module-sections.md"
idx_c.get("002-module-sections.md")                  -> None, siempre
```

**Ningún nombre podía casar jamás.** No había omisiones; no había *buscador*.

> Un cero que significa «mi índice y mi consulta no hablan el mismo idioma» es
> indistinguible de un cero que significa «no hay nada». Y el segundo **no
> obliga a mirar**: se acepta, se anota como resultado negativo y se sigue.
>
> Es la razón por la que `073` insiste en que los totales salgan de
> `len(...)` y no de una suma escrita a mano, y por la que `relations.py`
> imprime el índice. Una afirmación negativa necesita su negación comprobada.

## 3 · EL RESULTADO: 10 OMISIONES, Y NO SON TODAS IGUALES

```
findings sin relación declarada:               46
  de los que CITAN a otro por su nombre:        10   <- omisión
  de los que no citan a ninguno:                36
citas en total:                                 34
```

Y las 10 se parten en dos clases que **no admiten el mismo tratamiento**:

| clase | findings | aristas por declarar | qué hace falta |
|---|---|---|---|
| **CLARA** (el destino sí declara) | 6 | **17** | nada: el destino ya dijo su parte |
| **MUTUA** (ambos lados declaran nada) | 4 | **8** | decidir qué relación hay: leer |

```
001-amdgpu-location.md                     -> 002*, 003*
005-cs-ioctl-analysis.md                   -> 003*
006-lsdma-packets.md                       -> 003*, 007*
009-blockers-status.md                     -> 001*, 008*, 010*
021-write-lock-scoped-subdir-does-not-bloc -> 016*, 017*, 018, 019, 020*, 022, 023
056-function-always-spec-primaria-descarta -> 018
062-citas-de-c-009-desplazadas-y-tabla-de- -> 030
071-el-except-que-devuelve-stub-y-el-flag- -> 021*, 023
073-el-indice-por-numero-descarta-y-el-gra -> 023, 035
073-f7-medido-216-sin-versionar-y-17-ids-d -> 021*, 051, 056*, 072*

`*` = el destino tampoco declara relación
```

Las 17 de la clase CLARA se pueden escribir **sin leer nada**: el destino ya
declaró, solo falta la línea del origen. Las 8 de la clase MUTUA exigen
decidir, y eso es trabajo de lectura.

**Y las 10 son, exactamente, el conjunto que `074` dejó abierto.** El `NEXT
ACTION` era correcto y la medición lo confirma.

### `021` es el caso illustrative

`021` cita a siete findings y no declara ninguno:

```
016*, 017*, 018, 019, 020*, 022, 023
```

Y `021` es **el hallazgo del cerrojo de escritura**, el que documenta que dos
sesiones colisionaron de índice. Su propia cabecera dice `CIERRA=la` y
`HERRAMIENTA_NUEVA=…`. Escribe sobre la mecánica del proyecto y no declara de
quién aprendió nada.

## 4 · ERRORES PROPIOS EN ESTA ITERACIÓN

| error | detectado por |
|---|---|
| `\b(\d{3})[-_][a-z0-9-]+` casa rangos de líneas → 141 «citas» | los targets `617`, `858`, `817` **no existen como findings** |
| índice `f[:-3]` contra consulta con `.md` → 0 omisiones | el 0 era demasiado redondo y no cuadraba con lo que se habia visto en 001:82 |
| `_c, t` desempaquetando `(finding, línea)` → comprobaba la línea 18 | `omisión mutua: 10` (= todos), cuando sólo son 4 |
| `SyntaxWarning: "\d" is an invalid escape sequence` al insertar el regex | el propio aviso del intérprete |

El tercero es el más instructivo: `citas_de` devuelve `(finding, línea)` y yo
escribí `for _c, t in ...`. Comprobaba `18 not in con_rel` para las 34 citas —
siempre cierto, así que la respuesta era siempre «omisión mutua» y salía el
**máximo posible** (10 de 10).

> **Un unpacking al revés devuelve un valor que es exactamente 1, el máximo
> posible, o el mínimo.** Los tres son números que no obligan a mirar. Es el
> mismo motivo por el que `x[3]` donde iba `x[4]` dio «1 familias» en `073`.

## 5 · ESTADO

```
grafo           89 filas · 78 pares · 14 familias · 73 con destino AMBIGUO
                25 de esas salen de etiquetas con varios destinos
frontera        259 huecos abiertos, 7 vías de cierre
declaración     117 findings · 73 con relación · 46 sin ella
                  24 con cabecera y sin verbo   (formato, sin relación)
                  20 sin ninguna etiqueta        (anteriores a la convención)
                10 de los 46 dependen de otro y no lo declaran
                  17 aristas clase CLARA  · 8 aristas clase MUTUA
vocabulario     19 verbos · 263 NO_RESUELVE = 221 campo + 42 resto
citaciones      287 resueltas, 0 fallos
selftests       relations 27/27 · frontier 12/12 · claims 20/20 · artifacts 14/14
                rx550pm4val PASS · rx550ref PASS
GPU             01:00.0 Lexa PRO rev c7, INTACTA
```

## 6 · LO QUE ESTO CIERRA Y LO QUE NO

**Cierra:** el `NEXT ACTION` de `074`. Los 10 findings que dependen de otro sin
declararlo están identificados, con sus destinos y con la clase de la omisión.

**No cierra:**
- **Las 17 aristas CLARA** se pueden escribir ya, una línea por arista, sin
  leer. Es edición, no herramienta, y no lo hago automáticamente: escribir una
  afirmación en un finding es una decisión sobre la evidencia, y una
  herramienta que la tomara por mí sería declarar una dependencia que nadie ha
  comprobado.
- **Las 8 aristas MUTUA** exigen lectura.
- **Los 35 números duplicados.** Es el bloque sin atajo, y no ha cambiado:
  renumerar rompe las aristas de quien cita por número, y desambiguar exige
  saber a cuál de los dos iba cada cita — que es lo que el `!` declara
  irresoluble. La sección `OMISIONES` es la primera que encuentra esas citas
  **por nombre**, y por tanto sí las desambigua: un nombre no es ambiguo aunque
  su número lo sea. Ese es el camino, y es de nuevo trabajo de edición.

---

```
RESULTADO DE ITERACIÓN

Entregado:
  seccion OMISIONES en tools/relations.py
  discriminante documentado: una cita a un finding ACABA EN .md, y se
    resuelve contra el indice de ficheros, no por forma del nombre

Medido:
  46 findings sin relacion declarada
    10 dependen de otro y no lo declaran  -> 34 citas
       6 clase CLARA  (el destino declara): 17 aristas escribibles sin leer
       4 clase MUTUA (ambos lados nada):     8 aristas que exigen lectura
    36 no citan a ningun finding por nombre

Retractado:
  "141 citas desde findings sin relacion" -- 141 coincidencias de un patron
    que tambien casa `amdgpu.h:858-1201` y `sid.h:335-338`
  "0 omisiones" -- el indice y la consulta no hablaban el mismo idioma

NEXT ACTION:
  El dato que este finding deja a medias, y que es el mas util de todos los
  medidos hasta ahora: DE LAS 89 ARISTAS DEL GRAFO, CUANTAS APORTAN ALGO.

  El discriminante NO puede ser el verbo --eso mediria el vocabulario--. Tiene
  que ser una comprobacion sobre el texto: si se borra el finding DESTINO, el
  finding ORIGEN se queda sin apoyo? Eso se responde leyendo el origen y
  buscando la afirmacion que el destino sostiene. Es trabajo de lectura.

  Y hay una version mecanica que si es UN-GREP y no inventa nada: quantas de
  las 89 aristas tienen su origen en un finding que, ademas de la cabecera,
  CITA al destino en su cuerpo. Si la cita esta, la dependencia es real aunque
  el verbo sea `CONTINUES`; si no esta, la arista la sostiene solo la
  declaracion de la cabecera, que es una asuncion del autor.

  Esa cifra separa el grafo que DECLARA de la cadena que SOSTIENE, que es la
  diferencia entre un indice y una evidencia.
```
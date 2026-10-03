# 988 · 34 de 75 instrumentos con precondiciones NO tienen ninguna red de versiones

```text
CLASSIFICATION=MEASUREMENT+NEGATIVE_RESULT · TRACK=CORPUS+TOOLING
CORPUS=directo: censo sobre .sh/.py del proyecto, excluyendo terceros
HARDWARE_SCOPE=ninguno: es una medida sobre el corpus, no sobre la placa
WORK_CLASS=READ_ANALYSIS + WRITE_LOCAL
MODIFICATIONS_COUNT=0 sobre instrumentos existentes
AUTHORIZATION=NONE · GPU INTACTA · RUNTIME=NOT_RUN
AUTORIA=AGENT-04 (RUNTIME/PROBING/FUZZING/ORACLES)
CONTINUES=984, que dejó escrito: "no se ha hecho un censo de cuántos
          instrumentos más del árbol están sin versionar; ese censo es trabajo
          de otro nodo y debería hacerse". Este es ese nodo.
HALLAZGO=el hueco no es de EP08, es general
ARTEFACTO=08-ARQUITECTURA/artifacts/EP08-VALIDATION/preflight_census.sh
         preflight-census.tsv
```

## El número

```
instrumentos que DECLARAN PRECONDICIONES      75
  versionados (tienen red)                    41
  SIN RED (ninguna)                           34        45 %
```

Contraste independiente de la columna `versionado`, con un segundo método de git:

```
75 filas contrastadas, 0 discrepancias
  metodo A: git ls-files --error-unmatch
  metodo B: git status --porcelain   (?? = sin seguimiento)
```

## Las definiciones, porque sin ellas el número no significa nada

```
INSTRUMENTO     .sh/.py que mide algo en esta máquina. No documentación, no
                resultados, no árboles de kernel de terceros.
PRECONDICION    un literal contra el que el código COMPARA, que podría
                haberse leído de la máquina en el momento de escribirlo.
                Se exige el `=`: una constante que solo se menciona no se
                está comprobando.
EXCLUIDOS       RESEARCH/, rx550-upstream-*, archive/, .git/ — declarados,
                no supuestos.
```

## Los cuatro con más precondiciones y sin red

| precond | tamaño | ignorado por git |
|---|---|---|
| `03-EXPERIMENTOS/ep08-doorbell-suppression/preruntime.sh` | 22 · 25513 B | **NO-IGNORADO** |
| `tools/rx550/run-all.sh` | 12 · 60200 B | **NO-IGNORADO** |
| `08-ARQUITECTURA/tools/xref.py` | 7 · 22315 B | **NO-IGNORADO** |
| `08-ARQUITECTURA/tools/causal.py` | 7 · 17243 B | **NO-IGNORADO** |

Y en la lista, que no es una lista de directorios raros:

```
tools/assert_contract.py     tools/oracle.sh          tools/claims.py
tools/claim.py               tools/citations.py       tools/citeambig.py
tools/constmap.py            tools/docscan.py         tools/frontier.py
tools/drift.py               tools/hwip.py            tools/ipsolve.py
tools/pm4census.py           tools/snapshot.py        tools/toolreg.py
tools/audit_citations.sh     tools/rx550/{regla,contract,alcance,revierte,
                                     mandato,conflicto,bits,transiciones}.py
07-DRIVER/driver/test_rx550_pciid.sh
04-IMPLEMENTACION/rx550-mem/mutate.sh
06-INGENIERIA-INVERSA/agents/astext.py
```

**No están ignorados.** `git check-ignore` responde que no para los cuatro. Es decir: no
es una política de exclusión deliberada, es que **nunca se hicieron `git add`**. Eso cambia
el diagnóstico y también la solución: no hay que discutir una excepción, hay que añadir
ficheros que el repositorio ya acepta.

## Por qué estos y no otros importan

`assert_contract.py` valida contratos y `oracle.sh` produce oráculos. Son, literalmente, los
dos instrumentos cuyo trabajo consiste en decir si algo es verdad. **Si uno de los dos
cambia, y cambia bien, no hay forma de saber qué cambió ni volver atrás** — y nadie puede
auditar un veredicto contra la versión que lo produjo, porque la versión no existe.

Eso no es hipotético: en este mismo turno, el único control negativo que no dependía de una
autoverificación detectó un cambio real en EP08 y permitió restaurarlo (984). La red que
salvó eso fue **un artefacto de documentación**, no el control de versiones.

## Lo que este hallazgo NO dice

- **No dice** que se haya perdido trabajo. No se ha perdido nada por esta vía; dice que
  **no habría red** si se perdiera.
- **No dice** que estos instrumentos sean incorrectos. El de 973 estaba mal, y está sin
  versionar, y son dos hechos distintos que este hallazgo **no** confunde.
- **No mide** si sus constantes son circulares en el sentido de 985. Eso exige leer cada
  fichero y es OTRO nodo; aquí solo se mide la ausencia de red, que se mide contando.
- **No propone** añadir 34 ficheros a git en este turno. Ver la recomendación abajo.

## Recomendación, con su coste

```
1. git add de los 34. Coste: ~450 KB de texto, sin binarios.
   NO añadir nhwa.ko ni *.o ni *.bin: son reconstruibles y .gitignore ya los excluye.
   Añadirlos sería el error simétrico al de 984.
2. Convertir el "¿está todo versionado?" en un PREFLIGHT de la propia suite de tools.
   Es la versión automatizada de COORDINACION.md aplicado a algo que sí se puede medir.
3. Distinguir en el informe lo que se MIDIO de lo que se PROPONE. Aquí: 75 y 34 son
   medidas. El punto 1 y el 2 son propuestas y no se han ejecutado.
```

**No se ejecuta aquí.** Qué entra en el índice es una decisión estructural, y el árbol tiene
505 ficheros sin seguimiento esperando la suya. Lo que sí se entrega es la medición y el
instrumento que la reproduce.

## Los tres fallos del propio censo, y por qué importan más que el número

El censo tiene **tres** defectos, y los tres producen un número plausible en lugar de un
error visible. Se registran porque son la clase que este proyecto ya ha pagado tres veces.

### 1 · El filtro no filtraba, y dio 263

```
find … | sed 's|^\./||' | grep -vE '^\./(RESEARCH/|…)'
```

El `sed` quita `./` **antes** del `grep`, así que `^\./RESEARCH/` no casa nunca. Resultado:
**263 "instrumentos"**, de los que la lista estaba llena de selftests de Linux
(`test_multitouch.py` con 131, `mptcp_join.sh` con 69). Corregido el orden: **75**.

Un filtro que no filtra no devuelve un número pequeño. Devuelve un número **creíble**, y un
número creíble es más peligroso que un cero porque nadie lo comprueba.

### 2 · La autovalidación era ciega por estructura

La comprobación de que no se colara ningún tercero era:

```bash
grep -qE '^(RESEARCH/|rx550-upstream-)' "$TSV"     # no puede dispararse NUNCA
```

La ruta es la **tercera columna**; las líneas empiezan por el número. El ancla `^` hace que
el detector sea **estructuralmente incapaz** de encontrar lo que busca. Es el mismo patrón
que el **finding 967** («el detector informaba 0 colisiones porque su estructura las hacía no
representables») y que el **109**. Corregido a `(^|<TAB>)(RESEARCH/|…)`.

**Un detector que no puede dispararse es peor que no tener detector**: da confianza sin
aportar información, y además inhibe el escepticismo de quien lo lee.

### 3 · `grep -c` con cero coincidencias imprime 0 **y** devuelve 1

```bash
n=$(grep -cE "$PRECOND" "$f" || echo 0)     # -> n vale "0\n0"
[: "$n" -gt 0 ]                             # -> "se esperaba un entero", 41 veces
```

El instrumento Died **en silencio**, 41 veces, con la salida vacía y un `exit 0` del guion.
Solo se vio porque se miró la salida y no el código de salida. Es exactamente la trampa que
`capture_preconditions.sh` valida en el harness ajeno, y en el propio.

### Y los controles, que es lo que los hace creíbles

| control | esperado | medido |
|---|---|---|
| censo con el filtro desactivado | `ABORTO`, exit 2 | `ABORTO`, exit 2, con las tres rutas de Linux citadas |
| censo real | exit 0, sin terceros | exit 0, sin terceros |
| contraste de la columna `versionado` por segundo método | 0 discrepancias | 75 filas, **0** |

Sin el control 1, el 263 habría pasado. Sin el control 2, la autovalidación habría parecido
funcionar. **Un instrumento que no se ha visto fallar no se ha probado.**

```
LIMITACION  El recuento depende de la definición de PRECONDICION, que es un regex. Con
            otra definición el 75 sería otro. La definición está escrita arriba y en la
            cabecera del guion, para que se pueda discutir en vez de heredarse.
LIMITACION  No mide circularidad de constantes (hallazgo 985): eso es lectura, no conteo.
LIMITACION  No se ha medido 08-ARQUITECTURA/tools frente a tools/: los dos están en la
            lista y eso sugiere una separación de responsabilidades que nadie escribió.
```
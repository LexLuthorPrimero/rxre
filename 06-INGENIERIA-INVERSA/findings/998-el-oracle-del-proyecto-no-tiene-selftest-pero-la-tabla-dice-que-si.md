# 998 — en la tabla de herramientas, la mitad de las filas no se mide: se supone

```
AGENCIA=RX550-INVESTIGACION · WORK_CLASS=AGENT-27-RUNTIME-ORACLES
GENERADO=2026-10-03 · MEDIDO=EN ESTA HOST, ESTE WORKING TREE
HERRAMIENTA_AUDITADA=tools/oracle.sh   sha256=7c84b8254e2a45fc (el que publica TOOLS-STATUS.md)
GENERADOR=tools/artifacts.py           sha256=39fd9ab20b3c56aa (el que publica TOOLS-STATUS.md)
ESTADO=PROBADO (defecto) · CONTRADICTION_ABIERTA (alcance)
```

## La afirmación

Para **toda herramienta `.sh`**, las dos columnas que informan de su validación
—`declara selftest` y `estado`— **no se miden**: se rellenan con dos fuentes
independientes que no son un test. La tabla presenta el resultado como una
medición. Y sobre la fila de `oracle.sh` las dos columnas **se contradicen
entre sí sin que ninguna lo advierta**.

## MEDIDO

### 1. `TOOL_UNVALIDATED` de un `.sh` es un literal, no un veredicto

`tools/artifacts.py:878-884`:

```python
estado = "TOOL_UNVALIDATED"          # <- literal, ANTES de mirar nada
detalle = "sin selftest"
st_declara = "si" if declara else "NO"
if f.endswith(".sh"):
    detalle = "script: sin convencion de selftest"   # <- estado NO SE TOCA
elif not declara:
    detalle = "sin selftest"
else:
    ...
    r = subprocess.run(cmd, ...)                     # <- corre el selftest
    estado, detalle = clasificar(declara, rc=r.returncode)
```

En la rama `.sh` **no se asigna `estado`**. Se queda con el literal de la línea
878. Y `clasificar()` —la función que traduce un `rc` en un veredicto— **no se
llama nunca para un `.sh`**: está en el `else`. Consecuencia:

> **Ningún `rc` de ninguna herramienta de shell se lee jamás para producir la
> tabla.** `TOOL_UNVALIDATED` en esas filas no es un fallo observado: es el
> valor por defecto de quien no ha comprobado nada.

### 2. La columna `declara selftest` sí es un rastreo de texto — y la leyenda lo niega

`TOOLS-STATUS.md` afirma, sobre su propia tabla:

> «la columna se calcula **EJECUTANDO el selftest y mirando el codigo de
> salida**, no buscando la palabra 'selftest' en el texto»

`flag_selftest()` es un `re.search()` **sobre el texto del fichero**:

```python
if re.search(r"\b(?:def|function)\s+selftest", txt): ...
```

Y para `oracle.sh` ese camino falla, pero `flag_selftest` devuelve `'-selftest'`
igualmente, por una rama anterior que busca **la cadena** en el cuerpo:

```
$ python3 -c "import artifacts as A; print(A.flag_selftest('tools/oracle.sh'))"
--selftest
$ grep -cE '\b(def|function)[[:space:]]+selftest' tools/oracle.sh
0
```

`oracle.sh` **no define** un selftest (0 coincidencias) pero **lo menciona**,
porque él mismo conduce instrumentos con ese flag:

```
171:  ok=$(timeout 60 python3 "$TOOLS/$n.py" --selftest ...)
175:  ok=$("$WORK/$n" --selftest ...)
188:  ok=$("$TOOLS/$n" --selftest ...)
```

Se clasifica como «instrumentada» **porque conduce instrumentos**. El aparato
de medición queda contado como medido. De la familia que 997 señaló («un guard
que se mide a sí mismo»), aquí localizado al fichero.

### 3. Y ese `--selftest` no es un selftest: enruta el flag como consulta

```
$ sh tools/oracle.sh --selftest ; echo "EXIT=$?"
=== rx550ref: symbol --selftest ===
    0 definition(s) across 2 root(s)
  FAIL  no #define of --selftest in any header. ...
EXIT=1
```

Salida de **resolución de símbolos del corpus** (`rx550ref --sym`), con su
`sello` (`linux-7.2.8`, 631 ficheros). No ejercita la tabla de despacho de
`oracle.sh` (`--reg`/`--sym`/`--file`/`--block`/`--audit`).

`--selftest` **no es un identificador C**: `no #define de --selftest in any
header` es una **verdad vacía**, cierta para toda entrada de la forma
`<palabra><espacio>`. Este rc=1 **no puede** leerse como «el selftest FALLA»:
es un fallo de búsqueda sobre una cadena que no podía existir.

### 4. La fila publicada dice `si` y `TOOL_UNVALIDATED`: las dos columnas, dos fuentes

```
| oracle.sh | 414 | si | TOOL_UNVALIDATED | 7c84b8254e2a45fc |
```

`si` viene de `declara=True` (paso 2, un rastreo de texto).
`TOOL_UNVALIDATED` viene del literal (paso 1, sin medición). **Ninguna de las
dos se ha medido**, y las dos se presentan como una sola clasificación.

### 5. Deriva por cambio de fichero: REFUTADA

```
sha publicado : 39fd9ab20b3c56aa
sha real      : 39fd9ab20b3c56aa
```

Coinciden. La tabla **no** caducó: la generó este binario. El defecto no es
antigüedad, es diseño del generador.

## CORRECCIÓN DE UNA CONTRADICCIÓN QUE YO MISMO PLANTEÉ

Mi hipótesis inicial era: «la fila no es reproducible con el generador que la
publicó», porque `clasificar(True, rc=1)` devuelve `('TOOL_BROKEN', 'el
selftest FALLA')` y la tabla dice `TOOL_UNVALIDATED`. **Queda REFUTADA** por
`artifacts.py:878-884`: la rama `.sh` nunca llama a `clasificar`, así que el rc
no llega a existir y `TOOL_BROKEN` es inalcanzable para un `.sh`. La tabla
**acierta** en el estado, y **se equivoca en el fundamento**: ese acierto no es
una medición. Anotado porque el error era plausible y el código lo tumba en ocho
líneas.

## CONTRADICTION (abierta, delimitada)

| | |
|---|---|
| `CONTRADICTION_ID` | `C-TOOLS-SH-NOT-MEASURED` |
| CLAIM_A | leyenda de `TOOLS-STATUS.md`: la tabla se calcula **ejecutando** el selftest y leyendo su rc |
| CLAIM_B | `artifacts.py:878-884`: para `.sh` el selftest **no se ejecuta**; `estado` es un literal |
| EVIDENCIA_B | `estado = "TOOL_UNVALIDATED"` + `if f.endswith(".sh")` sin reasignar; `clasificar()` ausente de esa rama |
| ALCANCE | **todas** las filas `.sh` de la tabla. Medido 1 caso de 4 `.sh` listados; el defecto es del generador, no del fichero |
| CONFUNDERS | (a) que `artifacts.py` se invoque con otro modo que evite esa rama — **descartado**: no hay otro llamador; (b) que la leyenda hable sólo de la columna `estado` y no de `declara` — **no ayuda**: también afirma que no se busca la palabra, y `flag_selftest` sí la busca |
| RESOLUCION | **PROBADO** para `oracle.sh`. Alcance sobre las demás `.sh`: **NOT_DETERMINED** |

## Lo que esto significa para AGENT-27

Mi encargo: un experimento con oracle que dé FAIL/PASS real. De esta capa sale
una **regla anterior a cualquier experimento**:

> **Un rc sólo significa algo si su entrada tiene estados de fallo alcanzables
> y si alguien lo lee. Antes de aceptar el veredicto de un instrumento hay que
> demostrar dos cosas: que su selftest PUEDE fallar, y que su veredicto lo ha
> leído alguien.**

`oracle.sh` falla las dos: su `--selftest` no puede fallar de forma
informativa (verdad vacía), y su fila se resolvió sin ejecutarlo. Un experimento
que apoyase su PASS en `oracle.sh --selftest` apoyaría su PASS en nada.

## Oracle (independiente del objeto auditado)

No se usa el veredicto de `oracle.sh` sobre sí mismo. Se usa **la semántica de su
propia salida**, que es texto y se lee:

| | |
|---|---|
| **PASS** | `oracle.sh --selftest` produce salida que ejercita su tabla de despacho (`--reg`/`--sym`/`--file`/`--block`/`--audit`) |
| **FAIL** | la salida es un bloque de resolución de símbolos que nombra el flag como símbolo del corpus |
| **INVALID** | rc=2/3, sin `sello`, o salida vacía |
| **MEDIDO** | **FAIL** — `=== rx550ref: symbol --selftest ===`, `0 definition(s)`, rc=1 |

**Cross-check pendiente, y sin él esto es una muestra única:** el mismo
discriminante debe dar PASS sobre una herramienta que **sí** implemente
selftest. No ejecutado.

## EXPERIMENTO SIGUIENTE (uno solo, estático, sin GPU)

```
ACCION        : para cada .sh de la tabla, ejecutar su flag y clasificar la
                salida con el discriminante de arriba
QUESTION      : ¿la premisa del generador —"un .sh no puede tener --selftest"—
                es falsa en general, o `oracle.sh` es el único contraejemplo?
DISCRIMINANT  : (a) 1 de 4     → defecto aislado; se corrige la fila y la premisa
                               queda como decisión, no como error
                (b) 2 o más     → la premisa es FALSA como regla; toda la
                               columna `estado` de .sh es inservible y hay que
                               medirla de verdad
CONFOUNDERS   : metacircuitos — un .sh que invoca `--selftest` sobre OTROS
                (como `oracle.sh`)Mentiona el flag; hay que separar "responde
                con un test propio" de "enruta el flag", que es exactamente lo
                que este finding separa
STOP          : conteo completo de los .sh, o 2 casos → parar y declararla
                inservible
ROLLBACK      : ninguno — sólo lectura, sin sudo, sin GPU, sin tocar el driver
COSTE         : bajo
```

## Lo que este finding NO establece

- **No** dice nada del hardware, de la GPU, ni de DPM/VRAM/PM4. Es un defecto
  de instrumentación. **Nada de esto es evidencia sobre el ASIC.**
- **No** establece el alcance sobre las demás `.sh`: medido 1 caso.
- **No** afirma que `oracle.sh` sea inútil: funciona bien como enrutador de
  consultas. Lo que no puede es ser su propio oráculo.
- **No** es un fallo de la tabla **entera**: 1 caso medido, de 62 filas.
- **No** ejecutó el cross-check de una muestra PASS. Sin él, el discriminante
  está probado sólo en su rama FAIL.
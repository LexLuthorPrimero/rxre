# 1011 — la regla que dice «un .sh no puede tener selftest» es falsa, y el único .sh que sí lo tiene no está en el registro

```
AGENCIA=RX550-INVESTIGACION · WORK_CLASS=AGENT-27-RUNTIME-ORACLES
GENERADO=2026-10-03 · MEDIDO=EN ESTA HOST, ESTE WORKING TREE
CIERRA=el item pendiente de 998 ("cross-check con una muestra PASS")
RESOLVE=C-TOOLS-SH-NOT-MEASURED, alcance
ESTADO=PROBADO (regla) · NEGATIVE_RESULT (impacto hoy) · PROBADO (cross-check)
```

## La afirmación

`artifacts.py:884` resuelve toda herramienta de shell con la razón literal
`"script: sin convencion de selftest"`. **Esa premisa es falsa**, y el
contrafactor está en el propio repositorio: `revkit/pub.sh` implementa
`--selftest` de verdad, con 14 vectores que declaran su `rc` esperado, y **pasa**.

El mismo defecto produce los dos errores, opuestos y simultáneos:

- **sobreafirmación** — `oracle.sh` aparece con `declara selftest = si` y no tiene
  ninguno (998);
- **infraconteo** — `pub.sh`, que **sí** tiene uno validado, **no aparece** en
  `TOOLS-STATUS.md`.

## MEDIDO

### 1. La población real, con alcance completo (§16)

```
$ find . -name '*.sh' -not -path './.git/*' -not -path './archive/*' | wc -l
1178
```

De esos, **1169 son de `RESEARCH/kernelbuild/`** — árbol vendorizado del kernel,
ajeno al proyecto y a este registro. Los `.sh` **del proyecto** son 9:

| `.sh` | implementa `--selftest` | cómo se sabe |
|---|---|---|
| `revkit/pub.sh` | **SÍ** | `case "$1" in --selftest) SELFTEST=1` (línea 64) |
| `tools/rx550/run-all.sh` | no | *escribe* planes `pasa:--self-test:60`, `falla1:...` (266-321) |
| `tools/oracle.sh` | no | menciona el flag al conducir otros (171/175/188) |
| `revkit/check.sh` | no | sólo un comentario sobre `btfsnap` |
| `revkit/pub_selftest.sh` | n/a | es el *contenido* del selftest, no un entrypoint |
| `tools/audit_citations.sh` | no | sin gestión de `--selftest` |
| `RESEARCH/polaris12xl/tools/build-module.sh` | no | idem |
| `RESEARCH/polaris12xl/tools/safety-audit.sh` | no | idem |
| `08-ARQUITECTURA/tools/unversioned_drift.sh` | no | idem |

**1 de 9 implementa la convención.** La premisa es falsa como regla.

### 2. El contrafactor: `pub.sh --selftest` existe y PASA

```
$ sh revkit/pub.sh --selftest ; echo "EXIT=$?"
pub_selftest: la puerta probada sobre un repo y una suite de mentira
  OK    todo verde -> commitea                             rc=0 (esperado 0)
  OK    sin cambios que publicar                           rc=4 (esperado 4)
  OK    check.sh falla -> NO COMMITEA                      rc=2 (esperado 2)
  OK    cn7 falla -> NO COMMITEA                           rc=2 (esperado 2)
  OK    selfcheck falla -> NO COMMITEA                     rc=2 (esperado 2)
  OK    mensaje de una linea -> rc 3 sin correr nada       rc=3 (esperado 3)
  ...
  OK    stageado de mas -> se niega y lo saca              rc=5, el ajeno fuera (f.txt)
EXIT=0
```

14 vectores, `stderr` vacío, escrituras confinadas a `mktemp -d` con `rm -rf`
(62/74, 126/143, 147/160, 168/194) — los `git commit` ocurren en repos
desechables, no en el del proyecto. **Intervención: READ_ONLY sobre el
proyecto.**

Esto es un selftest en el sentido pleno: declara el valor esperado de cada
vector y lo compara. Es lo contrario de lo que hace `oracle.sh`.

### 3. El cross-check que 998 debía: ambos brazos del discriminante

998 se quedó sin muestra PASS y lo declaró. Ya está:

| herramienta | EXIT | salida | brazo |
|---|---|---|---|
| `revkit/pub.sh` | **0** | 14 vectores con `rc=X (esperado X)` | **PASS** |
| `tools/oracle.sh` | **1** | `=== rx550ref: symbol --selftest ===`, `0 definition(s)` | **FAIL** |

El discriminante **separa**: no es el `rc` — si lo fuera, bastaría `0`/`1` y
`oracle.sh` sería «el test que falla». Es si la salida **declara el valor
esperado del contrato propio**. Con dos muestras, una por brazo, el
discriminante deja de ser un test de una sola muestra.

### 4. Por qué `pub.sh` no está en la tabla

`artifacts.py:824` — `for f in sorted(os.listdir(t))`. **No recursivo, y sólo
un directorio.** De ahí que:

- `revkit/`, `tools/rx550/`, `08-ARQUITECTURA/tools/` y
  `RESEARCH/polaris12xl/tools/` quedan **fuera** del registro;
- dentro del alcance real (`tools/` de primer nivel) sólo hay **2 `.sh`**:
  `oracle.sh` y `audit_citations.sh`.

### 5. NEGATIVE_RESULT: hoy ninguna fila publicada es incorrecta por esto

`oracle.sh` no tiene selftest → `TOOL_UNVALIDATED` correcto por casualidad.
`audit_citations.sh` tampoco → correcto, y además marca `NO` en `declara`, porque
`flag_selftest` no casa con su texto.

> **El defecto es real y la regla es falsa, pero el daño actual es CERO.** Es un
> defecto **latente**: el día que un `.sh` con selftest real entre en el alcance
> del escaneo —o que se corrija el escaneo para incluir subdirectorios— será
> clasificado `TOOL_UNVALIDATED` por un literal, sin ejecutar nada.

## El error, en una frase

Un escaneo que **no puede representar** a los instrumentos de shell produce a la
vez una fila que **afirma** un selftest que no existe y la **ausencia** del
único que sí existe.

## CONTRADICTION (cerrada)

| | |
|---|---|
| `CONTRADICTION_ID` | `C-TOOLS-SH-NOT-MEASURED` |
| RESOLUCION | **PROBADO**: la regla es falsa (contrafactor `pub.sh`, EXIT=0). Impacto actual **CERO** por alcance de escaneo. La contradicción entre la leyenda y el método se mantiene **abierta** en su otra mitad: para `.sh` nunca se lee un `rc` |
| CONFOUNDERS eliminados | (a) «quiza `pub.sh` tiene selftest pero no funciona» — **refutado**: EXIT=0, 14 vectores; (b) «el fallo es de `pub.sh`, no del generador» — **refutado**: `pub.sh` pasa |
| LIMITACIÓN | 9 `.sh` del proyecto; los 1169 del árbol vendorizado no se consideraron instrumentos |

## Corrección que se sigue, y su coste

El arreglo es de una línea y **cambia el significado de una columna**:

```
- if f.endswith(".sh"):
-     detalle = "script: sin convencion de selftest"
+ # un .sh PUEDE tener --selftest (revkit/pub.sh lo demuestra): se ejecuta
+ # y el rc se lee, igual que en el resto. Sin esta rama, TOOL_UNVALIDATED
+ # es un literal y no una medicion.
```

Coste: `pub.sh` y `check.sh` entrarían en el registro; habría que decidir si el
escaneo debe ser recursivo, lo que **cambia el recuento de 62 filas** y obliga
a regenerar `TOOLS-STATUS.md`. Es un cambio de alcance del registro, no una
corrección local: **no lo aplico aquí.** Lo dejo declarado.

## Oracle (independiente de los dos objetos auditados)

| | |
|---|---|
| **PASS** | la salida declara el valor esperado del contrato propio (`rc=X (esperado X)`) |
| **FAIL** | la salida delega: resuelve el flag como consulta en otro instrumento |
| **INVALID** | rc=2/3, stderr con error, o salida vacía |
| **MEDIDO** | `pub.sh` → **PASS** (14 vectores) · `oracle.sh` → **FAIL** |

El instrumento auditado **no** emite su propio veredicto: se lee su texto, y el
criterio es si declara la expectativa, cosa que el autor del test escribe y el
test no puede falsear sin mentir sobre el propio número.

## Lo que este finding NO establece

- **No** dice nada del hardware, de la GPU, ni de DPM/VRAM/PM4. Es
  instrumentación. **Nada de esto es evidencia sobre el ASIC.**
- **No** afirma que ninguna fila de la tabla sea incorrecta: medido el alcance,
  el daño es cero.
- **No** ejecutó `audit_citations.sh`, `check.sh` ni los dos de `polaris12xl`:
  se clasificaron por lectura estática de su gestión de argumentos (§49), no por
  ejecución.
- **No** propone el cambio de código como hecho: es una recomendación con
  alcance declarado, no aplicada.
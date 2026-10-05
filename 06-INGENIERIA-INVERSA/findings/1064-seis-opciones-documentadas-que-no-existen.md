# 1064 — seis herramientas documentan opciones que no existen, y cinco de ellas están marcadas `TOOL_VALIDATED`

```text
AGENCIA=RX550-INVESTIGACION · WORK_CLASS=AGENT-RE-TOOLING
GENERADO=2026-10-04 · MEDIDO=EN ESTA HOST
AFECTADO=tools/claim.py:47 · tools/msg_census.py:43 · tools/reg_resolve.py:35
         tools/struct_layout.py:48 · tools/xref.py:43
         08-ARQUITECTURA/tools/contradict.py:50
ESTADO=PROVEN · oraculo DECIDIBLE, sin heuristica: 6 adjudicados a mano
herramienta   tools/prosa.py 1.0.0
sha256        b28dcf07ed83cc7818d36838245d478c6274254ed0e07691a999c722adc4a3b2
artefacto     08-ARQUITECTURA/artifacts/R5a-PROSA/prosa.json
sha256        f1fdb1e7c4d259c8077f84909d9daa7099c991f47281b6615431b048e4c1f1cd
selftest      28 vectores, 0 fallos, rc=0
```

## 0 · EL HUECO QUE EL PROPIO PROYECTO DECLARABA

`tools/toolcheck.py` lo dice literalmente en su propia cabecera:

> *Lo que NO hace: no comprueba que la herramienta diga la verdad. Comprueba que
> tenga forma de decirla.*

Y `tools/riesgo.py` sí falsifica declaraciones, pero **solo del vocabulario
maquinable** (`WRITES_FILES=no`, `WRITES_GPU=no`, `READONLY=yes`). Tokens.

La mayoría de las herramientas de este árbol **no llevan contrato maquinable:
llevan prosa** — secciones `QUE RESUELVE`, `LIMITE DECLARADO`, `VALIDACION`. Es
la forma que usan casi todas, y no hay token que falsificar.

MEDIDO sobre los 7 directorios declarados en `toolreg.TOOL_DIRS`:

| | |
|---|---|
| ficheros | 238 |
| con contrato en prosa | 205 |
| `.c`/`.sh` → `NO_CLASIFICABLE` | 32 |
| sin docstring | 1 |

## 1 · R6-01 · LAS SEIS OPCIONES, UNA A UNA

Cada una está en el **bloque de opciones** del docstring — el sitio donde el
proyecto documenta lo que su herramienta acepta — y cada una es un ejemplo de
uso que **no funciona**.

| herramienta | flag documentado | qué registra `add_argument` |
|---|---|---|
| `tools/claim.py:47` | `--coverage` | `--repo --scaffold --locate --next-id --json --selftest --version` |
| `tools/msg_census.py:43` | `--list-unknown` | `--kernel --chip --root --msg --detail --json --selftest` |
| `tools/reg_resolve.py:35` | `--across-headers` | `--kernel --amd-root --gfx --reg --field --fields-of --resolve --json --selftest` |
| `tools/struct_layout.py:48` | `--fields` | `--kernel --amd-root --struct --offset --json --selftest` |
| `tools/xref.py:43` | `--declares` | `--kernel --file --symbol --callers --json --selftest` |
| `08-ARQ…/contradict.py:50` | `--with-code` | `--sym --dir --all --check --min-sites --json --self` |

Las seis están **verificadas a mano**, una por una, contra el `add_argument` de
su fichero. Éste es el único veredicto del instrumento que es **completamente
decidible**: lo que la prosa nombra contra lo que `add_argument` registra. No hay
heurística y no puede fallar en silencio.

La sexta es distinta de las otras cinco y merece nombrarse aparte, porque es la
más traicionera:

```
  contradict.py --check             existe el valor en el codigo? (--with-code)
```

La prosa **sugiere** un flag `--with-code` que no existe; el flag real es
`--check`. Quien lea esa tabla y componga la orden obtiene un error de argparse
con el nombre de la opción que **él se inventó**, no con el que funciona.

## 2 · POR QUÉ EL REGISTRO NO LO PUEDE VER — Y ESTO ES EL HALLAZGO DE VERDAD

Las cinco primeras están clasificadas **`TOOL_VALIDATED`** en
`TOOLS-STATUS.md`: su `--selftest` pasa.

**El estado de validación mide que la herramienta _funciona_. No mide que su
_documentación_ sea ejecutable.** Son dos cosas distintas, y el registro solo
tiene una columna para una de ellas.

> Una herramienta cuyo docstring da una orden que sale con error está
> `TOOL_VALIDATED` y equivocada a la vez. **Nada en el registro actual puede
> distinguir esos dos estados**, porque no hay columna que lo pregunte.

Eso no es un defecto de estas seis herramientas. Es un defecto del **esquema de
clasificación**, y es por eso que el hallazgo es del arnés y no del fichero.

## 3 · LO QUE ESTO CAMBIA PARA QUIEN USE ESAS HERRAMIENTAS

El modo de fallo no es "el ejemplo no corre". Es: **alguien copia la línea de
uso, la pega, y el error que aparece nombra una opción que no existe**, así que
no señala el problema real. En `msg_census.py`, quien escriba `--list-unknown`
recibirá `unrecognized arguments` y empezará a buscar un flag mal escrito en
lugar de mirar la lista.

## 4 · LO QUE NO SE HIZO

**No se corrigió ninguna prosa.** Este nodo MIDE. Las seis correcciones son de
una línea cada una, y las hace quien escribió esas herramientas: son suyas, y
cambiar el contrato de otra herramienta sin hablar con ella es exactamente el
`REPAIR_OVER_PRESERVATION` que §79 desaconseja cuando lo que se repara es la
autoría.

**No se regeneró `TOOLS-STATUS.md`**, que es donde estos seis aparecerían como
fila nueva. Lo genera `tools/artifacts.py`, y ese fichero estaba **modificado
sin commitear por otro nodo** durante esta sesión. Regenerarlo habría escrito
sobre su trabajo. La puerta que falta en el esquema está propuesta en
`08-ARQUITECTURA/AGENT-RE-TOOLING.md` §2.
# FINDING — tooling: un falso veredicto en el registro de herramientas

AGENCIA=RX550-INVESTIGACION-WORKSPACES/05-TOOLING-AUTOMATION
WORK_CLASS=validacion-de-instrumentacion
RUNTIME=SI (user namespace no necesario; todo sin sudo) · GPU=INTACTA
CERROJO=.write-lock/tools tomado y liberado · SIN COMMITS
findings tocados: 0 (los 97x de EVIDENCE-MATRIX son de otros agentes)

---

## 1 · QUE AFIRMA

`tools/artifacts.py` marcaba `integridad.py` como `TOOL_BROKEN`, y eso es
**falso**. La herramienta no tiene ningun selftest que pueda fallar.

```
$ python3 tools/integridad.py --help
integridad 2.3.0   banda 900+          <- ignora --help y ejecuta la auditoria
$ python3 tools/govcheck.py --help
usage: govcheck.py [-h] [--json] [--limite LIMITE] [--selftest]   <- si argparse
```

`integridad.py` no declara `--selftest`; su unica salida es
`sys.exit(main(sys.argv))`. Su `rc=1` significa **"la auditoria encontro
DUPLICADOS 1, CONTAMINADOS 6"** — que es el tool haciendo su trabajo — y no
"el selftest FALLA".

## 2 · DONDE ESTA EL DEFECTO

`tools/artifacts.py`, rama de clasificacion (antes de este trabajo):

```python
if r.returncode == 0:
    estado, detalle = "TOOL_VALIDATED", "selftest pasa"
elif r.returncode == 1:
    estado = "TOOL_BROKEN"          # <- no comprueba que exista selftest
```

El codigo de salida solo significa algo si hay un selftest al que
corresponder. Faltaba esa tercera comprobacion.

## 3 · ALCANCE MEDIDO — sin exagerarlo

No era una epidemia. Artefacto: `/tmp/opencode/rx550/medida_clase_c.txt`

```
62 herramientas con rc conocido
 1 falso veredicto  -> integridad.py
 6 sin declarar selftest, de las cuales 5 salian bien POR CASUALIDAD
                     (rama .sh, o rc=2), no por logica
```

El error simetrico —`rc=0` sin selftest daba `TOOL_VALIDATED`— no lo
comete ninguna hoy, pero seguia disponible.

## 4 · EL SEGUNDO DEFECTO, Y ERA EL QUE HACIA LA TABLA AUTO-CONTRADICTORIA

La columna `selftest` se calculaba como `"si" if x["st"] else "NO"`, donde
`x["st"]` era `detalle` — **una cadena que nunca esta vacia**. Por eso las
**70 filas** deian `si`, incluidas las 4 que la propia tabla marcaba
`TOOL_UNVALIDATED`. Una columna que no puede decir NO no informa.

## 5 · QUE SE HA HECHO

1. `clasificar()` como funcion **pura**, con `declara` en primer lugar de la
   firma: el dato que decide es si existe selftest.
2. `declara_selftest()`: decide si EXISTE, no si pasa.
3. La columna dice `declara selftest` y sale de `declara`, no de `detalle`.
4. **11 vectores nuevos** para el clasificador, que no tenia ninguno. Su
   ausencia era la causa: la rama `rc==1 -> BROKEN` se escribio sin un solo
   vector que la mirara.
5. `mountcheck.py` nueva, 17 vectores, `TOOL_VALIDATED`.

## 6 · VALIDACION

```
tools/artifacts.py --selftest    RESULT: PASS (25 vectores)   rc=0   0 FAIL
tools/mountcheck.py --selftest   RESULT: PASS (17 vectores)   rc=0   0 errores
```

**Prueba de que el arreglo no es cosmético**: `mountcheck.py` detecta las
clases C y D leyendo la tabla. Al regenerarla, sus dos hallazgos
(`FALSE_VERDICT`, `STALE_ROW`) **desaparecieron solos**. Un detector que
deja de Findingsar cuando se arregla lo que Findia es un detector real.

**Contraste independiente**: `mount(8)` y `mountinfo` coinciden (6 capas,
33 montajes).

## 7 · EFECTO OBSERVADO

| | antes | despues |
|---|---|---|
| `integridad.py` | `TOOL_BROKEN` | `TOOL_UNVALIDATED` |
| `govcheck.py` | `TOOL_BROKEN` | `TOOL_BROKEN` (correcto: tiene test y falla) |
| columna | `si` x70 | 7 filas `NO` |
| Total | 70 herramientas | 71 |

**1 cambio de estado, y es el previsto.**

## 8 · LO QUE SIGUE ABIERTO — y no lo he tocado

**El hallazgo que outranks este**: el `AGENTS.md` canonico tiene **6 bind
mounts apilados** encima y muestra un fichero de rol de 524 B en vez del
prompt maestro de 49 KB.

```
/RX550-INVESTIGACION/AGENTS.md  ->  524 B  sha 35dbbf6f  ino 2008260
   = RX550-AGENT-DEFINITIONS/01-COORDINACION/AGENTS.md
```

Medido: `git status` reporta ` M AGENTS.md` con **"24 insertions, 1060
deletions"** — un borrado que no ocurrio, porque git lee a traves del
montaje. **Riesgo vivo de perdida de datos**: un agente que "restaure" desde
HEAD (30295 B) destruye la version real de 49 KB.

El contenido **esta intacto**: `~/.config/opencode/AGENTS.md` = 49596 B,
sha `3ca73133…`, identico a lo que registra `VALIDATION.md` 7. Esta tapado,
no borrado. Copia de rescate en
`/var/tmp/rx550-rescue/20261003-142649-agents-md-occlusion/`.

`govcheck.py --selftest` falla por **esto**, no por un defecto de codigo:
deriva `RAIZ` de su propia ruta (linea 76), asi que en este workspace lee
el `AGENTS.md` de rol de 548 B, mientras que sus vectores asumen el prompt
maestro.

**No lo he arreglado**: el cerrojo era de `global-coordinator-04` con
`scope=ROOT write-anywhere`, y el desbloqueo necesita `sudo`, que aqui mide
como "a password is required". Registrar el hallazgo no es repararlo.

## 9 · AFIRMACIONES DE LA DOCUMENTACION QUE QUEDAN REFUTADAS

- `ARCHITECTURE.md` 6 + `VALIDATION.md` 2/4: base comun `sha 547ee189…`
  byte-identica en los seis → **no aparece en ningun fichero**.
- Idempotencia "3 ejecuciones -> 12 montajes" → **33 montajes**, con 6 capas
  sobre el mismo destino.
- `VALIDATION.md` 7 "canonico intacto": era cierto cuando se midio; ahora
  el camino canonico esta tapado.

## 10 · ESTADO

```
TOOLS-STATUS.md   regenerado, 1 cambio de estado
artifacts.py      REPAIRED + 11 vectores, TOOL_VALIDATED
mountcheck.py     NUEVA, 17 vectores, TOOL_VALIDATED
integridad.py     sin tocar: sus hallazgos (dup 959, 6 contaminados) son REALES
GPU               INTACTA
commits           NINGUNO
cerrojo           liberado
```
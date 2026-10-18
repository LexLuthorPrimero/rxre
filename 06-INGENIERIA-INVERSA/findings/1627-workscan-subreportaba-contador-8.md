# 1627 — WORKSCAN SUBREPORTABA EL CONTADOR POR 8 — CORREGIDO

```text
CLASSIFICATION=ERROR_CORRECTED
WORK_CLASS=RXRE-CLI-UNIFICATION-001
AUTOR=SISTEMA AUTÓNOMO RXRE
FECHA=2026-10-15
TARGET=Polaris12 (RX550) · GFX8 · 1002:699f
QUESTION=¿El contador de hallazgos que `./rxre workscan` reporta es el máximo real del árbol?
STATE=REFUTED_THEN_CORRECTED
```

## QUE SE AFIRMABA

La implementación previa de `cmd_workscan` informaba:

```text
MAXIMO ESCRITO: 1615
```

## QUE SE MEDIO

Escaneando el árbol entero:

```text
findings/                          md=23  numerados=12  max=1615
06-INGENIERIA-INVERSA/findings/    md=33  numerados=33  max=1623
UNION                              md=56  numerados=45  max=1623
```

**El máximo escrito real es 1623, no 1615. La herramienta subreportaba en 8.**

## CAUSA

`cmd_workscan` elegía **un** directorio con un `if/else`:

```python
findings_dir = os.path.join(RAIZ, "findings")
if not os.path.isdir(findings_dir):
    findings_dir = os.path.join(RAIZ, "06-INGENIERIA-INVERSA", "findings")
```

El fallback nunca se activaba porque `findings/` **sí** existe. El segundo
directorio, que contiene los hallazgos más altos, quedaba invisible.

Detalle adicional: el mecanismo de selección estaba escrito para funcionar
cuando un directorio *falta*, cuando el fallo real es que **conviven dos y hay
que unirlos**. Es el patrón `§27` PRODUCER/ARTIFACT/CONSUMER aplicado mal: la
herramienta consumía un artefacto parcial y lo declaraba completo.

## REPARACION

Se sustituyó la selección por un descubrimiento que camina el árbol:

```python
def _discover_findings_dirs():
    for base, dirs, files in os.walk(RAIZ):
        dirs[:] = [d for d in dirs if d not in (".git", "__pycache__", ...)]
        if os.path.basename(base) == "findings":
            found.append(base)
            dirs[:] = []
    return sorted(found)
```

Se excluyen `.git`, `__pycache__`, `node_modules`, `.work` y
`KytyPS5-Source` del recorrido. `dirs[:] = []` tras encontrar un `findings`
impide descender dentro de él.

## SEGUNDA REPARACION: SEPARAR TRABAJO DE HALLAZGOS

El `AGENTS.md` afirma que el número más alto **cuenta trabajo gastado, no
hallazgos distintos**, y que el contador es compartido entre sesiones. La
versión anterior reportaba un único número, lo que exactamente produce el
efecto que la directiva prohíbe: presentar el progreso mayor de lo que es.

`workscan` ahora lee `RESERVAS.ledger` y reporta las dos magnitudes por
separado:

```text
=== WORKSCAN (2 directorios) ===
  06-INGENIERIA-INVERSA/findings     md=33   numerados=33   max=1623
  findings                           md=23   numerados=12   max=1615

  ficheros .md (union):    56
  hallazgos numerados:      45
  numeros distintos:        42
  repeticiones:             3
  ficheros de mas:          6
  MAXIMO ESCRITO:           1623
  MAXIMO RESERVADO:         1626  (trabajo gastado, 867 reservas)
  por autor:
    AGENTE-INSTR: 6
    SISTEMA AUTÓNOMO RXRE: 8
  sin autor:               31

  NOTA: escrito(1623) < reservado(1626): hay 3 numeros
  reservados SIN fichero detras. Reservar no es escribir.
```

**Medición adicional: 3 números reservados sin fichero detrás (1624, 1625,
1626).** Reservar no es escribir; el ledger cuenta intención, no trabajo.

## VALIDACION

Dos tests de regresión en `tools/rxre/tests/test_cli009.py`:

- `cli.workscan_dirs.descubre_multiples` — exige ≥2 directorios
- `cli.workscan_dirs.max_agregado_dominante` — exige que el máximo agregado
  sea ≥ el máximo de cada directorio por separado

**Probados por mutación:** reintroduciendo el bug de selección (limitando la
descubrimiento a `findings/`), el test falla de forma exacta:

```text
FAIL cli.workscan_dirs.descubre_multiples: solo encontro ['findings']
=== CLI integration: 66 passed / 1 failed (of 67) ===
```

Restaurado: `67 passed / 0 failed`.

## LIMITACIONES

- El hallazgo más alto se lee del **nombre de fichero**, no del contenido. Un
  hallazgo cuyo nombre no empiece por dígitos se cuenta como `.md` pero no
  como numerado. En la unión actual son 11 de 56 ficheros.
- El ledger se lee de `RESERVAS.ledger` encontrado por `os.walk`. Si otro
  ledger existiera con otro nombre, no se contaría. Estado: `NOT_DETERMINED`
  para esa rama.
- No se ha medido si existen hallazgos fuera de directorios `findings/`. No se
  ha ejecutado un barrido de `.md` por todo el árbol. Estado: `NOT_OBSERVED`,
  no `PROVEN_ABSENT`.

## ALCANCE DE LA INTERVENCIÓN

Read-only. `workscan` no escribe ficheros, no abre la GPU, no toca
`0000:00:02.0`.

## ESTADO

```text
CLAIM=workscan reporta el máximo real del árbol
STATE=PROVEN (sobre directorios findings/; NOT_DETERMINED fuera de ellos)
```

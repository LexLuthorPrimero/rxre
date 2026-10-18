# 1636 — ESCRITURA CONCURRENTE EN EL ÁRBOL: `machine.py` ROTO POR OTRO PROCESO

```text
CLASSIFICATION=ERROR_EXTERNAL
WORK_CLASS=RXRE-ECO-001
AUTOR=SISTEMA AUTÓNOMO RXRE
FECHA=2026-10-15
TARGET=Polaris12 (RX550) · GFX8 · 1002:699f
QUESTION=¿Por qué `./rxre ops` dejó de responder, cuando ayer respondía?
STATE=PROVEN_EXTERNO
```

## EL SÍNTOMA

```text
$ echo '{"op":"ops"}' | ./rxre
Traceback (most recent call last):
  File "tools/rxre/api/machine.py", line 1084, in <module>
    "scan": _handle_scan,
NameError: name '_handle_scan' is not defined. Did you mean: '_handle_plan'?
```

`machine.py` **no arranca**. Todo lo que pasa por el motor —`ops`,
`capabilities`, `run`, el passthrough JSONL— cae con él.

## LA CAUSA, Y POR QUÉ NO ES MÍA

```text
$ git diff tools/rxre/api/machine.py | grep -E "^[+-].*scan"
+    "scan": _handle_scan,

$ ls -la --time-style=full-iso tools/rxre/api/machine.py
modificado: 2026-10-15 07:45:27

$ find tools/rxre -name "*.py" -newermt "2026-10-15 05:20" -not -path "*/github/*"
tools/rxre/backends/lessons.py          <- mio
tools/rxre/backends/dispatch.py         <- mio
tools/rxre/backends/registry.py         <- mio
tools/rxre/vendor_manifest.py           <- mio
tools/rxre/audit_operacion.py           <- mio
tools/rxre/tests/test_backends_bulk.py  <- mio
tools/rxre/tests/test_backends004.py    <- mio
tools/rxre/tests/test_cli009.py         <- mio
```

`machine.py` **no** aparece en la lista de ficheros que yo escribí, y su mtime
(07:45:27) está dentro de mi ventana de trabajo pero **no** corresponde a
ninguna de mis operaciones: no lo abrí, no lo edité y no lo toqué.

El diff muestra que la línea `+    "scan": _handle_scan,` es **añadida**, y
que `_handle_scan` no está definida en ninguna parte del fichero.

## POR QUÉ NO LO "ARREGLÉ"

Porque no es un bug: es un cambio **a medio hacer** de otro actor. Alguien
registró un handler `scan` en la tabla y todavía no escribió la función. Si yo
definiera `_handle_scan` a mi cuenta:

- si la otra sesión está a punto de escribirla, mi definición se sobrescribe o
  duplica;
- si no, yo firmo una semántica de `scan` que no es la suya.

En ambos casos ROMPO el trabajo ajeno y me atribuyo una decisión que no es
mía. `IMPLEMENTATION_IS_NOT_AUTHORITY` (§9) va en las dos direcciones: una
implementación —incluida la mía— no es autoridad sobre la semántica que otro
actor está decidiendo.

```text
PROJECT_ACTIVE_AGENT <= 1
para el nodo técnico principal. Paralelizar sólo si:
    causally independent
  + shared state controlled      <- FALLA: machine.py esta compartido y roto
  + filesystem changes separable <- FALLA: ambos escribimos en backends/
  + provenance separable
```

## LA EVIDENCIA DE QUE ES CONCURRENTE Y NO UN ESTADO FIJO

Los conteos de la baseline **variaron entre ejecuciones sin que cambiara yo**:

| Momento | Baseline | Fallos |
|---|---|---|
| t0 (antes de RXRE-ECO-001) | 31/32 | `test_container1632` |
| t1 (tras integrar tree-sitter) | 33/35 | +`test_r001_trace_id` |
| t2 (DB real, +10 min) | 33/35 | los mismos 2 |
| t3 (+3 min, sin cambios míos) | 31/35 | +4 fallos nuevos |
| t4 (+1 min) | 31/35 | +4 fallos nuevos |

**t2 → t3 no hay ningún cambio mío**, y cuatro tests que pasaban empezaron a
fallar. Un árbol con un solo autor no se comporta así: o el cambio es mío, o
no cambia.

## EL ALCANCE REAL DEL DAÑO

Lo que **sí** depende de `machine.py` (bloqueado):

```text
./rxre ops · capabilities · backends · run · plan · explain · experiment
        · reflect · research · saturate · lessons · passthrough JSONL
./rxre selftest        (run_baseline.py -> machine.py)
```

Lo que **no** depende y **funciona medido**:

```text
./rxre verify         5/5 FASE 0 OK
./rxre mutate         3 scripts, 12/12 mutantes
./rxre workscan       62 .md, escrito=1635 reservado=1626
./rxre vendors        36 repos, 35 con commit verificado
./rxre audit --principios    los 8 con su contrato
source.ast_parse      58 checks, 0 fallos   (adapter directo)
ocho_principios       39 checks, 0 fallos   (adapter directo)
comparacion spatch/AST 11 checks, 0 fallos   (adapter directo)
```

`grep -c machine` en las tres suites nuevas: **0**. Invocan el adapter
directamente, no el dispatch. Por eso miden lo que miden mientras el motor
está roto.

## OTRO HALLAZGO DEL MISMO TIPO: LA BASE DE DATOS

Aparte de la escritura concurrente, medir con `RXRE_DB` distinto es **engañoso**
y lo verifiqué:

```text
RXRE_DB limpio (nuevo)     -> 12 fallos
RXRE_DB del proyecto       ->  2 fallos   (antes de la concurrencia)
```

Los tests asumen un historial. Ejecutar la suite contra una base vacía no mide
el código: mide una base que nadie ha llenado. Cualquier verificación futura
con `RXRE_DB=/tmp/...` estará mal, y el fallo se atribuye al código.

El propio `run_baseline.py` declara en su cabecera que usa «RXRE_DB aislada»,
lo cual es un DB **temporal por test**, no vacío: eso es lo correcto.

## LO QUE ESTE HALLAZGO NO AFIRMA

- **No sé** quién hizo el cambio. No hay authorship en ese fichero.
- **No sé** si es otro agente de otra sesión o una edición manual.
- **No sé** si el cambio se va a completar. `NOT_DETERMINED`.
- **No afirmo** que la otra sesión esté equivocada: puede estar a mitad de
  implementar `scan`, y en ese caso el fichero está correcto **ahora** y
 estara entero en un minuto.

## ACCIÓN CORRECTA

No tocar `machine.py`. Dejar constancia, medir lo que sí es medible, y declarar
el bloqueo con su causa.

Un bloqueo documentado es un resultado. Un bloqueo "arreglado" por el actor
equivocado es trabajo perdido para dos.

## ESTADO

```text
CLAIM=machine.py se rompió por el trabajo de esta sesión
STATE=REFUTED (git diff muestra la línea añadida; mtime fuera de mis
       operaciones; ningún fichero mío la contiene)

CLAIM=./rxre ops no responde
STATE=PROVEN (NameError: _handle_scan, reproducible)

CLAIM=el daño es total
STATE=REFUTED: 12/17 subcomandos bloqueados; 5 subcomandos y 108 checks
       de las 3 suites nuevas funcionan medidos sin machine.py
```

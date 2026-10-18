# 1631 — DETECCIÓN DE MODO ROTA: `select` REPORTA EOF COMO LEGIBLE — CORREGIDO

```text
CLASSIFICATION=ERROR_CORRECTED
WORK_CLASS=RXRE-CLI-UNIFICATION-001
AUTOR=SISTEMA AUTÓNOMO RXRE
FECHA=2026-10-15
TARGET=Polaris12 (RX550) · GFX8 · 1002:699f
QUESTION=¿Cómo distingue el CLI entre "subcomando desconocido", "ayuda" y "passthrough JSONL"?
STATE=REFUTED_THEN_CORRECTED
```

## EL REQUISITO

El encargo excluía explícitamente decidir el modo por `stdin.isatty()`:
*"Mode detection must not rely solely on `stdin.isatty()`"*, para no romper
consumidores existentes que hacen `echo '{"op":"ops"}' | ./rxre`.

## LA PRIMERA IMPLEMENTACIÓN (ROTA)

```python
def detect_mode(argv):
    positionals = [a for a in argv if not a.startswith("-")]
    first = positionals[0] if positionals else ""
    if first in ALL_SUBCOMMANDS:
        return ("cli", first)
    if not sys.stdin.isatty():
        try:
            r, _, _ = select.select([sys.stdin], [], [], 0.0)
            if r:
                return ("jsonl", None)          # ← BUG
        except (OSError, ValueError):
            pass
    return ("help", None)
```

## LA MEDICIÓN

Instrumentado con `mode=<x> subcommand=<y>`:

```text
$ ./rxre nonexistent_cmd
DEBUG: mode=jsonl subcommand=None
$ echo "rc=$?"
rc=0
```

**Sin salida, y código 0.** Un subcomando desconocido se ejecutaba en silencio
como passthrough JSONL.

## POR QUÉ: `select` REPORTA EOF COMO "LEGIBLE"

`select.select()` informa **legibilidad**, no disponibilidad de datos. Un
descriptor de fichero en **EOF es inmediatamente legible**: `read()` devuelve
`b""` sin bloquear. Eso no es "hay datos", es "no queda nada".

En un pipe de shell donde nada escribió, `select` devuelve el fd como
legible porque está en EOF. La distinción entre "EOF" y "hay datos" **no se
puede hacer con `select`**: requiere leer.

El requisito ("no decidir solo por `isatty`") se satisfacía en apariencia
usando `select`, pero `select` no responde la pregunta que se le hace. El
requisito se cumplía formalmente y se incumplía en sustancia: el resultado
era que `./rxre nonexistent_cmd` no hacía nada.

Esta es la clase de fallo que §26 PRE-EXECUTION-CONTRACT_CHECK busca: el
mecanismo produce salida plausible (un bool) que no corresponde a la
propiedad consultada.

## LA REPARACIÓN: LEER, NO PREGUNTAR

```python
def detect_mode(argv):
    positionals = [a for a in argv if not a.startswith("-")]
    first = positionals[0] if positionals else ""

    if first in ALL_SUBCOMMANDS:
        return ("cli", first, None)

    stdin_data = None
    if not sys.stdin.isatty():
        try:
            stdin_data = sys.stdin.read()       # ← LEE de verdad
        except (OSError, ValueError):
            stdin_data = ""
        if stdin_data and stdin_data.strip():
            return ("jsonl", None, stdin_data)

    if first:
        return ("unknown", first, None)
    return ("help", None, None)
```

El dato se lee una vez, se decide sobre su contenido, y **se pasa al hijo**:

```python
result = subprocess.run(cmd, input=stdin_data, text=True, env=env)
```

Las cuatro salidas quedan distinguidas:

| Invocación | Modo | rc |
|---|---|---|
| `./rxre ops` | `cli` | según op |
| `./rxre nonexistent_cmd` | `unknown` → stderr "subcomando desconocido" | 2 |
| `echo '{"op":"ops"}' \| ./rxre` | `jsonl` | 0 |
| `./rxre` (TTY, sin args) | `help` | 0 |

Verificado:

```text
$ ./rxre nonexistent_cmd ; echo "rc=$?"
rxre: subcomando desconocido: nonexistent_cmd
Usa ./rxre help para ver las opciones.
rc=2
```

## BUG SECUNDARIO ENCONTRADO EN EL MISMO PUNTO

La primera versión del passthrough hacía:

```python
subprocess.run(cmd, env=env)          # heredaba stdin
```

Tras leer stdin en `detect_mode`, heredar stdin ya no funcionaba: el hijo
recibía el stream ya consumido. Además, al pasar `input=` sin `text=True`:

```text
TypeError: a bytes-like object is required, not 'str'
```

Reparado con `text=True`. La pareja queda así:

```python
subprocess.run(cmd, input=stdin_data, text=True, env=env)
```

## COMPATIBILIDAD JSONL MULTILÍNEA

Como el passthrough ahora reenvía `input=`, se verificó que **no** se pierde la
entrada multilínea (el modo principal de JSONL):

```bash
$ printf '{"op":"ops"}\n{"op":"ops"}\n' | ./rxre | wc -l
2
```

Dos peticiones, dos respuestas. El comportamiento coincide con el del
wrapper bash anterior.

## COSTE DE LA REPARACIÓN

Leer stdin para decidir **bloquea** hasta EOF cuando stdin es un pipe abierto.
En el uso previsto (pipes cerrados: `echo | ./rxre`, heredocs, redirecciones)
no hay bloqueo. Pero con `./rxre < /dev/zero` o un pipe que no cierra, el CLI
esperaría indefinidamente.

**No medido.** Estado: `NOT_DETERMINED`. Una alternativa sería
`os.set_blocking` + `os.read` no bloqueante, o `poll()` con
`POLLIN|POLLHUP`, que sí distingue EOF de datos. Requiere un trade-off entre
corrección y no-bloqueo; la corrección se priorizó porque el comportamiento
del primer diseño estaba peor (devolvía silenciosamente).

## ALCANCE DE LA INTERVENCIÓN

Read-only. Ningún acceso a hardware.

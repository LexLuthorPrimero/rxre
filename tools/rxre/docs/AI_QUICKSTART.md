# Inicio rápido para agentes de IA

Esta guía sirve para orientarse en un checkout de RXRE sin adivinar el estado del árbol ni las operaciones disponibles. Las instrucciones obligatorias están en [`AGENTS.md`](../AGENTS.md) y [`../../AGENTS.md`](../../AGENTS.md); léelas primero.

## 1. Conserva el estado encontrado

Desde la raíz del repositorio:

```bash
git status --short --branch
```

No limpies, sobrescribas, reorganices ni incluyas en commits los cambios que ya estaban allí. Inspecciona también cualquier estado generado o artefacto local que afecte la tarea.

## 2. Descubre la interfaz vigente

```bash
./rxre ops
./rxre capabilities
```

La primera lista operaciones anunciadas por el engine; la segunda consulta las capacidades y su estado. `op:ops` es curada, no necesariamente exhaustiva: si falta una operación, revisa `HANDLERS` en `tools/rxre/api/machine.py` y `ENGINE_OPS` en el launcher raíz. El checkout actual tiene precedencia sobre ejemplos históricos.

También se puede enviar JSONL directamente a `machine.py`:

```bash
printf '%s\n' '{"op":"ops"}' \
  | RXRE_DB=/tmp/rxre-agent-exploration.sqlite3 python3 tools/rxre/api/machine.py
```

Una línea contiene una petición JSON y produce una respuesta JSON. Usa `op:backends` para descubrir adapters. Antes de `op:run`, valida que la capability esté disponible y que su dominio cubra el artefacto.

## 3. Interpreta el resultado correctamente

| Estado operativo | Significado |
| --- | --- |
| `ok` | Se produjo una respuesta o resultados; evalúa su evidencia |
| `empty` | Se ejecutó y no encontró en ese alcance; no demuestra ausencia |
| `blocked` | No se ejecutó por una precondición o límite |
| `error` | La herramienta o el handler falló |

Los estados operativos no sustituyen a los estados epistémicos. Usa `PROVEN`, `PARTIAL`, `NOT_DETERMINED` y `BLOCKED` solo según el alcance y los requisitos de evidencia definidos en [`AGENTS.md`](../../AGENTS.md). La revisión por terceros no se sustituye con revisión propia.

## 4. Elige la superficie adecuada

- `defect`: formula una reconstrucción causal a partir del artefacto y síntoma; no hace reparaciones.
- `territory`: identifica el tipo de artefacto y su contexto tecnológico; la evaluación de herramientas puede ampliar el alcance.
- `plan`: inspecciona una capacidad antes de ejecutarla.
- `explain`: reconstruye procedencia y evidencia de un resultado registrado.
- `run`: ejecuta una capability; puede invocar herramientas y persistir resultados.

Las operaciones `defect` y `territory` se envían por JSONL a `machine.py`; no son subcomandos del launcher raíz:

```bash
printf '%s\n' '{"op":"territory","path":"/ruta/al/artefacto"}' \
  | RXRE_DB=/tmp/rxre-agent-exploration.sqlite3 python3 tools/rxre/api/machine.py
printf '%s\n' '{"op":"defect","path":"/ruta/al/artefacto","symptom":"describir el fallo observado"}' \
  | RXRE_DB=/tmp/rxre-agent-exploration.sqlite3 python3 tools/rxre/api/machine.py
```

Sustituye la ruta y el síntoma por datos del caso real. Consulta `./rxre ops` para los campos, límites y ejemplos de las operaciones que sí aparecen en ese catálogo.

## 5. Protege datos y hardware

- La base predeterminada es persistente. Para exploración y pruebas, establece `RXRE_DB` a una ruta temporal y verifica que la operación respete esa configuración.
- No toques `rxre.sqlite3`, WAL, contratos protegidos o esquemas append-only sin autorización específica.
- No uses `sudo` ni accedas a GPU, MMIO, `sysfs` o `debugfs` sin autorización. Toda submission física a GPU debe pasar por `require_gpu()`; prefiere `--no-run` para inspección/captura ISA.
- Revisa el cuerpo del test antes de lanzarlo. El runner completo puede ejecutar pruebas con dependencias externas, corpus local o hardware.
- No instales herramientas ni dependencias en el sistema para resolver un bloqueo sin autorización.

## 6. Mantén acotadas las conclusiones

Para una transformación, verifica identidad del artefacto, procedencia, cobertura de observaciones, efectos preservados y oráculo independiente cuando corresponda. `SAFE_TO_TRANSFORM` se aplica solo al caso y modelo evaluados; `IRRELEVANT` no autoriza una transformación. Si hay incertidumbre, abstente y declara qué falta.

Registra qué inspeccionaste, qué ejecutaste, el resultado, los límites y qué no quedó determinado. No presentes hashes, informes o auto-revisión como validación de terceros.

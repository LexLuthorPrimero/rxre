# RXRE — motor de Ingeniería Inversa Evolutiva y Reparativa

Este subárbol contiene el motor RXRE: una API de operaciones JSONL, un CLI, adapters de herramientas, persistencia y módulos IER con contratos de evidencia. El trabajo puede abarcar binarios, código fuente y análisis de evidencia; RXRE no es un driver GPU.

## Para empezar

1. Lee [`AGENTS.md`](AGENTS.md) y [`../../AGENTS.md`](../../AGENTS.md).
2. Conserva el estado actual del árbol: `git status --short --branch`.
3. Lee la [guía de inicio para IA](docs/AI_QUICKSTART.md).
4. Descubre la superficie del checkout con `./rxre ops` y `./rxre capabilities` desde la raíz del repositorio.
5. Antes de ejecutar una prueba o una operación, inspecciona sus efectos. Usa una base temporal cuando pueda haber persistencia y no inicies acceso a hardware sin autorización.

La documentación bajo [`docs/archive/`](docs/archive/) conserva material de RXRE-RX550 de octubre de 2026. Es histórico y no define el estado ni la interfaz actual.

## Superficies de uso

### CLI del repositorio

Desde la raíz del repositorio:

```bash
./rxre help
./rxre ops
./rxre capabilities
```

El CLI muestra los catálogos que anuncia el engine en este árbol. `op:ops` es una lista curada y puede no incluir todos los handlers; `HANDLERS` en `api/machine.py` es el mapa real de despacho. `ENGINE_OPS` en el launcher raíz muestra qué operaciones enruta como subcomandos. Comprueba ambos antes de decir que una operación no existe.

### API JSONL

`api/machine.py` recibe una petición JSON por línea y devuelve una respuesta JSON por línea. `op:ops` enumera las operaciones de la API:

```bash
printf '%s\n' '{"op":"ops"}' \
  | RXRE_DB=/tmp/rxre-exploration.sqlite3 python3 tools/rxre/api/machine.py
```

Una consulta al catálogo de backends usa `op:backends`. Para analizar un artefacto con `op:run`, primero consulta `./rxre capabilities` y usa una capability que esté disponible y cuyo alcance corresponda al artefacto.

Operaciones incorporadas recientemente:

- `defect`: reconstruye hipótesis causales a partir de una ruta y un síntoma; no repara el artefacto.
- `territory`: identifica formatos, tecnologías y evidencia de entorno. La evaluación opcional de herramientas debe inspeccionarse antes de usarla.

Estas dos operaciones están en la API JSONL; no son subcomandos del launcher raíz `./rxre`. Consulta los ejemplos de [`docs/AI_QUICKSTART.md`](docs/AI_QUICKSTART.md).

Las operaciones de escritura pueden persistir datos. `RXRE_DB` aísla algunas rutas de persistencia de la API; verifica el handler antes de asumir que toda operación respeta esa variable. No uses la base por defecto para una exploración descartable.

## Mapa del código

| Ruta | Responsabilidad |
| --- | --- |
| `api/machine.py` | Transporte JSONL y despacho de operaciones públicas |
| `backends/` | Registro, adapters y ejecución de herramientas externas |
| `core/` | Persistencia, estado, contratos transversales |
| `ier/` | Investigación, contratos de evidencia y capacidades de ingeniería inversa |
| `tests/` | Pruebas unitarias, adversariales e integración; requisitos varían por prueba |
| `docs/` | Contratos y guías actuales; `docs/archive/` contiene documentación antigua |

## Evidencia y estados

No mezcles estados operativos con epistémicos:

| Tipo | Estados | Lectura |
| --- | --- | --- |
| Operativo | `ok`, `empty`, `blocked`, `error` | Qué ocurrió al ejecutar una operación |
| Epistémico | `PROVEN`, `PARTIAL`, `NOT_DETERMINED`, `BLOCKED` | Qué permite concluir la evidencia y con qué límites |

`empty` no prueba que algo no exista; `blocked` indica que la operación no se ejecutó. Un hash o sello prueba integridad respecto de lo esperado, no autenticidad del origen. La revisión independiente de terceros sigue siendo un estado aparte.

Las capacidades IER recientes conectan `evidence_contract`, `transformer_witness`, `independent_verifier`, `lifetime_contract`, `angr_guard_bridge` y `rxre_angr_adapter`. `SAFE_TO_TRANSFORM` se limita al caso, las observaciones y el modelo cubiertos; no prueba comportamiento general del binario ni del driver.

## Pruebas y dependencias

No ejecutes `./run_tests.sh` automáticamente: descubre y ejecuta toda la colección, cuyas pruebas pueden requerir herramientas externas, artefactos M10/M11 o hardware. Primero revisa el test pertinente y corre una comprobación acotada con una base temporal:

```bash
RXRE_DB=/tmp/rxre-focused-tests.sqlite3 python3 -B tools/rxre/tests/test_evidence_contract.py
RXRE_DB=/tmp/rxre-focused-tests.sqlite3 python3 -B tools/rxre/tests/test_transformer_witness.py
RXRE_DB=/tmp/rxre-focused-tests.sqlite3 python3 -B tools/rxre/tests/test_independent_verifier.py
```

Los tests ligados al caso #7294 usan corpus sellado local M10/M11. Configura `RXRE_7294_SEALED_DIR`, `RXRE_7294_M11S_DIR` y `RXRE_7294_M11_DIR` si los artefactos no están en sus rutas predeterminadas bajo `$HOME`. `test_angr_7294.py` requiere además `RXRE_ANGR_7294_SOURCE`; si falta el checkout reparado, la prueba se omite.

No instales dependencias ni actives hardware por iniciativa propia. Las pruebas que interactúan con GPU tienen restricciones adicionales descritas en la guía de agentes y en la raíz.

## Referencias

- [Guía de inicio para IA](docs/AI_QUICKSTART.md)
- [Enfoque IER](../../RXRE_IER.md)
- [Instrucciones del repositorio](../../AGENTS.md)
- [Índice del repositorio](../../README.md)

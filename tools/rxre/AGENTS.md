# Instrucciones para agentes en `tools/rxre/`

Estas reglas complementan la [`AGENTS.md` de la raíz](../../AGENTS.md), que conserva autoridad superior. Antes de trabajar en este subárbol, lee también [`README.md`](README.md) y [`docs/AI_QUICKSTART.md`](docs/AI_QUICKSTART.md).

## Entrada y cambios

- Empieza con `git status --short --branch`; conserva los cambios versionados y untracked existentes.
- Usa `./rxre ops` y `./rxre capabilities` para consultar la superficie anunciada. `op:ops` es curada y no enumera todos los handlers; revisa `HANDLERS` y `ENGINE_OPS` si una operación no aparece. No infieras disponibilidad desde documentación histórica.
- Acota el objetivo, los archivos y los efectos antes de editar o ejecutar. No inicies misiones autónomas ni ciclos de reintento.
- Mantén `autonomous_loop=False`, `max_iter=1` y `op_claim=False`. No reabras misiones cerradas ni inicies E2E-040 o posteriores sin autorización específica.
- No hagas staging, commit, push, pull, merge, rebase, reset, clean, restore ni stash sin autorización expresa.

## Base de datos y hardware

- La base por defecto es persistente. Para verificaciones que puedan escribir, establece `RXRE_DB` a una ruta temporal y verifica antes que el test respete esa variable.
- No abras ni migres `rxre.sqlite3`, sus archivos WAL, ni bases de evidencia sin autorización específica.
- No toques `vk_cf_test`, contratos sellados ni esquemas append-only sin autorización específica.
- Toda submission física a GPU debe pasar por `require_gpu()`. Prefiere `--no-run` para capturar o inspeccionar ISA. No uses `sudo`, MMIO, `sysfs`, `debugfs` ni herramientas de acceso físico sin autorización específica.
- No ejecutes `op:claim` ni operaciones de escritura solo por explorar. `ops`, `backends`, `capabilities`, lectura de código y `plan` sirven para descubrir o preparar; aun así inspecciona cada handler antes de clasificar sus efectos.

## Evidencia y validación

- Mantén separados estados operativos (`ok`, `empty`, `blocked`, `error`) y epistemológicos (`PROVEN`, `PARTIAL`, `NOT_DETERMINED`, `BLOCKED`). `empty` no prueba ausencia; `blocked` significa que no se ejecutó.
- Hashes y sellos acreditan integridad respecto del valor esperado, no autenticidad de origen ni revisión por terceros.
- Para transformaciones, el testigo y el verificador independiente solo justifican claims dentro del dominio y las observaciones cubiertas. No conviertas `SAFE_TO_TRANSFORM` en una afirmación general sobre el binario o el driver.
- Antes de correr cualquier prueba, inspecciona su código y requisitos. Algunas dependen de corpus locales M10/M11, herramientas externas o hardware. No lances el runner completo como primer paso.
- Declara qué se ejecutó, qué pasó o se bloqueó y qué no quedó determinado. No edites el estado generado a mano.

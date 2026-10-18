# 1633 — 33 REPOS INTEGRADOS: UN PRODUCER NUEVO, TRES BLOQUEOS MEDIDOS

```text
CLASSIFICATION=IMPLEMENTATION
WORK_CLASS=RXRE-ECO-001
AUTOR=SISTEMA AUTÓNOMO RXRE
FECHA=2026-10-15
TARGET=Polaris12 (RX550) · GFX8 · 1002:699f
QUESTION=¿Se pueden integrar 33 repositorios externos en RXRE sin crear un ecosistema paralelo?
STATE=RESUELTO_CON_BLOQUEOS
```

## RESUMEN EJECUTIVO

```text
repos solicitados              33
clonados con commit verificado 32
bloqueados (con prueba)         1   -> umr
preexistentes preservados      4   -> rizin, radare2, angr, rz-ghidra
capacidades nuevas              1   -> source.ast_parse (26 total, era 25)
backends nuevos                 1   -> tree-sitter (8 total, era 7)
subcomandos CLI nuevos          2   -> audit, vendors
tests nuevos                    3   -> 108 checks en total
```

**Lo que NO se hizo, y con que prueba:** compilar LLVM, compilar Mesa,
ejecutar piglit o VK-GL-CTS, integrar joern como backend, y conectar dvc,
mlflow o OpenLineage. Cada uno con su razón en el apartado de bloqueos.

## UBICACION: POR QUE `tools/rxre/github/` Y NO UNA NUEVA

El encargo prohibía un ecosistema paralelo. Resultó que **ya existía el
patrón exacto**: `.gitignore` línea 32 dice

```text
# MEDIDO: `du -sh tools/rxre/github` = 680 MB, 11635 ficheros. Son clones
# de rizin, radare2, Ghidra y otros, con su propio .git dentro. Meterlos
# en este repositorio lo volveria inutilizable
tools/rxre/github/
```

Y `REPOSITORIES.txt` (2026-10-06) ya inventariaba 4. `rizin` está en la lista
de los 33 solicitados: **un tercio del trabajo ya estaba hecho y bien
archivado**. Se clonó en el sitio donde el proyecto ya decided que van los
clones, no en `tools/vendors/` que fue mi primera idea.

Los 3 clones preexistentes que NO estaban solicitados (`radare2`, `angr`,
`rz-ghidra`) se conservan intactos. `radare2` tiene un papel real: es el
COMPARADOR de `binary.functions`, y sin él "rizin funciona" no sería una
medida.

## EL REGISTRO (`vendor_manifest.py`)

`REPOSITORIES.txt` guarda url/branch/commit/dirty. Eso basta cuando la
procedencia es accesoria. Aquí es **estructural**: §15 exige que una capacidad
sólo exista si su producer es reproducible, y un clon no es reproducible sin su
commit **ni sin su estrategia de clonación**.

Un clon `--depth 1` y uno completo **no son el mismo artefacto**: al primero no
se le puede pedir historia. El manifest lleva eso explícito:

```text
linux           sparse-checkout + --depth 1 (NO es el kernel completo)
               865M (no 3.3G) · drivers/gpu/drm/amd, include/uapi/drm
llvm-project    sparse-checkout + --depth 1 (NO es LLVM completo)
               416M (no 15G)
mesa            sparse-checkout + --depth 1 · src/gallium/drivers/radeonsi
```

Y `verificar()` **comprueba en disco** en vez de re-derivar:

```text
$ ./rxre vendors
REPO                         CATEGORIA                COMMIT     SIZE    COINCIDE
rizin                        backend                  d14c3fac41 258M    si
tree-sitter                  backend                  8ca548849f 8,0M    si
linux                        referencia               0fcb05b723 865M    si
umr                          BLOQUEADO                -          -       -
total: 36 repos
```

35 de 36 con commit coincidente en disco. `umr` es el único sin confirmar, y
tiene su razón escrita.

## LA CAPACIDAD NUEVA: `source.ast_parse`

### Por qué no era una más

`source.semantic_search` (Coccinelle/spatch) ya existía y mide algo real. El
hueco no era "falta una herramienta de búsqueda": era que **spatch responde
sobre un patch, no sobre la estructura**. Un patch que no aplica dice "no
coincide"; un AST dice "hay 14 funciones, 199 declaraciones y el patrón está
en K hojas".

La comparación medida (hallazgo 1634) lo demuestra con 11 checks.

### El productor, sobre el target real

```text
$ ./rxre run source.ast_parse \
    --artefacto tools/rxre/github/linux/drivers/gpu/drm/amd/amdgpu/amdgpu.h \
    --lenguaje c
status: ok          type: structural_facts
root: translation_unit    bytes: 42872    nodos: 7066
funciones: 14    declaraciones: 199    tipos_distintos: 94
n_errores_parseo: 10      duracion: 0.057s
```

El fichero parseado es `drivers/gpu/drm/amd/amdgpu/amdgpu.h` del clon sparse
del kernel, commit `0fcb05b723`. Es el driver real de la RX550.

### `structural_facts` NO está en la escalera de confianza

Deliberado. `ORDEN_CONFIANZA` es para productores de **binario y hardware**:
`raw_binary` … `validated_semantics`. Un `source.` afirma sobre el **texto**.
Meterlo en esa escalera habría permitido declararlo `validated_semantics` sin
evidencia que lo sostenga. Que el源码 escriba un registro es una hipótesis
hasta que un probe la confirme.

### Por qué el parser corre en un SUBPROCESO

Los bindings de tree-sitter son binarios nativos compilados para una versión
de CPython concreta (3.14 aquí). Importarlos en el intérprete del motor ataría
todo el dispatch a este host: un `ImportError` en un adapter tumba la
`API` entera, no una capacidad. Aislado en `.venv/eco/`, el fallo es
`blocked` con la causa y el comando de instalación.

§89 dice no instalar dependencias globalmente. Ninguna se instaló: el venv
tiene 2 paquetes y el sistema quedó intacto.

## LOS TRES BLOQUEOS, CADA UNO CON PRUEBA

### 1. `umr` — el repo ya no existe

```text
$ git clone https://github.com/tomstdenis/umr.git
remote: Repository not found.

$ git ls-remote https://github.com/tomstdenis/umr      -> no
$ git ls-remote https://github.com/RadeonOpenCompute/UMR -> no   (la del registry)
$ git ls-remote https://github.com/umr-dev/umr          -> no
```

**Y `registry.py` declara ese repo para el backend `umr`.** Un registro puede
apuntar a un upstream muerto y seguir pareciendo verificable porque el campo
está lleno. El producer real es el RPM del sistema: `umr-1.0.11-2.fc44.x86_64`.

Clon **NO**Directories: el manifest marca `BLOQUEADO` con la prueba.

### 2. `semgrep` — el core OCaml no está compilado

El clon tiene el fuente OCaml en `src/` y `dune-project`, pero **no** el
binario `semgrep-core`. Compilarlo exige opam + dune: un build de horas para
una capacidad que `coccinelle` ya cubre parcialmente. **No se integra como
backend.** Queda como repos clonado, con la razón escrita.

### 3. `piglit` y `VK-GL-CTS` — son pruebas de hardware

El encargo prohíbe pruebas de hardware. Ambos compilan (VK-GL-CTS pesa 1.8 GB
clonado) y ambos ejecutan **tests sobre la GPU**. Clonados como referencia
normativa; **no ejecutados**.

## LO QUE NO SE INTEGRÓ, Y POR QUÉ

**Clonado pero no como backend:** joern (104M, JVM 25 disponible, pero requiere
`c2cpg` y no se midió ningún CPG → producer sin medir = capacidad sin
producer), angr y rz-ghidra (ya estaban marcados `NOT_DETERMINED` en el
registro; no se cambia un estado sin evidencia nueva).

**Clonado pero no conectado:** dvc, mlflow, OpenLineage, mem0, graphiti,
cognee, hindsight, langmem, MemOS, beads, Recuris, reprocert, reproledger,
research-evidence-agent, scip, los dos `awesome-*`, y los cinco
orquestadores (OpenHands, SWE-agent, mini-swe-agent, SWE-ReX, EvoAgent).

El motivo es el mismo para todos y es de **criterio**, no de tiempo:

> Un orquestador de agentes, un tracker de métricas y un grafo de memoria
> **no son producers de evidencia**. Integrarlos como tales sería declarar
> capacidades cuya única verificación sería "importa y responde", que es
> exactamente lo que §22 prohíbe.

`OpenLineage` es el caso interesante: su modelo
`producer → artifact → consumer` **es** la cadena causal §14 de RXRE. Merece
integración, y es trabajo pendiente con forma concreta, no un "ya lo hice".

## REGRESION: LO QUE CAMBIÓ Y CÓMO SE COMPRUEBA

Añadir un backend movió el registro, y **cinco** tests lo notaron. Todos
fallaron, todos legítimamente:

| Test | Qué codificaba | Cambio |
|---|---|---|
| `test_backends004` | conjunto **exacto** de backends | +`tree-sitter` |
| `test_backends_bulk` | conjunto exacto (x2) | +`tree-sitter`, 25→26 adapters |
| `test_dispatch004` | recuento declarado == real | `decision.json` +1 |
| `test_cli009` | 25 capacidades exactas | →26 |

Cada cambio lleva el motivo y **una comprobación nueva** que exige que
`tree-sitter` entre *por medir*, no por declararse:

```python
v("tree-sitter cierra source.ast_parse con producer medido",
  registry.get("tree-sitter")["capacities"].get("source.ast_parse")
  in registry.ESTADOS_CON_PRODUCER, ...)
```

El número **no se relajó a `>=25`**: un conjunto exacto es lo que detecta un
adapter olvidado. Subirlo es correcto mientras el producer esté medido; si
alguien añade una capacidad inventada, el test vuelve a rojo.

### Baseline

```text
=== BASELINE 33 passed / 2 failed / 0 errored (of 35) ===
FAIL test_container1632.py    preexistente: cuelga descomprimiendo amdgpu.ko.zst sin zstd
FAIL test_r001_trace_id.py    preexistente: 13/27 con Y sin los cambios de esta sesion
```

`test_r001_trace_id` se verificó **revirtiendo** los tres ficheros modificados
de `backends/`, ejecutando, y restaurando: 13/27 idéntico. No lo causó este
trabajo.

### Contaminación de base de datos: hallazgo lateral

Medido: `RXRE_DB` limpio da **12** fallos; la base real del proyecto da **2**.
Los tests asumen historial. Ejecutar la suite con una base vacía no mide el
código: mide una base que nadie ha llenado. Documentado porque cualquier
"verificación" futura con `RXRE_DB=/tmp/...`estedará mal.

## LOS OCHO PRINCIPIOS, COMO CÓDIGO QUE SE EJECUTA

Hallazgo 1635. Resumen: `./rxre audit --desde-fichero <env.json>` audita una
operación real con los ocho y devuelve `operacion_cerrada`, que **no** es lo
mismo que `status: ok`. End-to-end medido sobre `source.ast_parse`:

```text
status: ok  |  operacion_cerrada: True  |  los ocho principios pasan
status: ok  |  operacion_cerrada: False |  violacion: TIERRA
                                    (provenance sin input_hash)
status: ok  |  rc=2                    |  violacion: AIRE
                                    (4000 declaradas, 3 publicadas, sin flag)
```

## ESTADO

```text
CLAIM=Se pueden integrar repos externos en RXRE sin ecosistema paralelo
STATE=PROVEN (32/33 clonados con commit verificado, 1 bloqueado con prueba)

CLAIM=source.ast_parse es un producer utilizable
STATE=FUNCTIONALLY_VALIDATED (58 checks, incluidos 3 mutation-test)

CLAIM=tree-sitter y spatch son intercambiables
STATE=REFUTED (hallazgo 1634: modos de fallo opuestos)

CLAIM=joern, semgrep, dvc y OpenLineage son integrables ya
STATE=NOT_DETERMINED (no medido; cada uno con su razon)
```

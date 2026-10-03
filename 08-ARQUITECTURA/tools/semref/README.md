# semref — resolvedor de referencias de símbolo en C del kernel

`semref` responde **«¿dónde se invoca X, y desde qué función?»** clasificando cada
sitio como `DEFINITION` o `CALL`. La clasificación es lo que `grep` no puede
hacer: `grep` cuenta la definición y las llamadas con el mismo número.

Nació de un fallo concreto. Al cerrar P-8, una enumeración por `grep` había
encontrado los callers de `amdgpu_fence_process` pero no había seguido su efecto.
`grep` sí veía la llamada; lo que faltaba era **exhaustividad y cierre semántico**.
Esta herramienta automatiza esa parte.

## Uso

```bash
semref engines                              # estado de los motores
semref refs  <símbolo> [--root DIR]         # definiciones + call sites
semref chain <símbolo> [--root DIR] --depth N   # cierre transitivo de callers
```

```console
$ semref refs amdgpu_fence_process --root RESEARCH/kernelbuild/linux-7.1.3/drivers/gpu/drm/amd/amdgpu
DEFINITION  amdgpu_fence.c:207  amdgpu_fence_process
CALL        amdgpu_fence.c:263  amdgpu_fence_fallback
CALL        amdgpu_fence.c:671  amdgpu_fence_driver_force_completion
...
TOTAL amdgpu_fence_process definicion=1 llamadas=3 suma=4
```

`chain` termina con `sin expansión en nivel N` cuando el caller cae fuera del
árbol. **Declara el límite en vez de fingir que no hay más callers.**

## Motores

| motor | papel | por qué |
|---|---|---|
| `ctags` | `DEFINITION` | léxico, recorre el árbol entero, rápido |
| Coccinelle (`spatch`) | `CALL` | semántico; distingue llamada de definición |

`semref` **no resuelve punteros a función**: no responde «qué función está detrás
de este callback». Tres patrones (`F = f`, `E.F = f`, `T F = f`) fallaron contra
`.enable_signaling = amdgpu_fence_enable_signaling`. Esa capacidad es
`NOT_PROVEN` y no debe inferirse de que `ENUMERACIÓN` funcione.

## Estado de las capacidades

| capacidad | estado |
|---|---|
| enumeración de callers, con clasificación | `PROVEN` en el universo probado |
| resolución de callbacks | `NOT_PROVEN` |
| exhaustividad absoluta del motor | `NOT_DETERMINED` |

## Garantías

- **Nunca escribe en el árbol.** Coccinelle se invoca sin `--in-place`; opera
  sobre copias en `/tmp`.
- **Control negativo explícito.** Símbolo inexistente → `SIN-MATCH`.
- **No degrada en silencio.** Si falta un motor, exit 3 con
  `ENGINE-NOT-AVAILABLE`; nunca produce un resultado vacío que parezca un `PASS`.

## Requisitos

`ctags` del sistema y Coccinelle. Coccinelle se instaló **sin `sudo`**, extrayendo
los RPM en un prefijo local:

```bash
# en /tmp/opencode/tools  (efímero: /tmp no sobrevive a un reinicio)
export LD_LIBRARY_PATH=/tmp/opencode/tools/usr/lib64
export COCCINELLE=/tmp/opencode/tools/usr/lib64/coccinelle
```

`spatch` necesita además `libpcre.so.1`, que no está en el sistema base. Se
obtiene del RPM `pcre`.

> **LIMITACIÓN** — La instalación de Coccinelle vive en `/tmp/opencode/tools` y
> **no está versionada**. Si se borra, `semref` queda con un solo motor y el
> runner devuelve `NOT_RUN`, no un falso aprobado. Reinstalarla está en el README
> del paquete RPM, no aquí.

Variables: `SEMREF_HOME` (prefijo, por defecto `/tmp/opencode/tools`),
`SEMREF_SPATCH`, `SEMREF_CTAGS`.

## Tests

```bash
tests/run-bench
```

Regresión determinista sobre corpus sintético congelado. Detalle y procedencia de
cada topología en `tests/frozen/benchmark-001/README.md`.

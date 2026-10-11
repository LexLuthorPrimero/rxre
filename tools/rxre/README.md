# RXRE — RX550 Reverse Engineering Engine

Punto de entrada único para que una IA investigue la AMD Radeon RX 550
(Polaris12 / GFX8) sin saber qué script existe ni qué flags tiene cada uno.

```bash
tools/rxre/rxre capabilities
tools/rxre/rxre search "VM_CONTEXT0_CNTL"
tools/rxre/rxre register VM_CONTEXT0_CNTL
tools/rxre/rxre trace amdgpu_vm_init
```

## Qué es y qué no es

**Es** una capa de despacho y normalización. **No** reescribe ninguna de las
~220 herramientas de `tools/`: las invoca, comprueba que responden y traduce su
salida a un formato único.

El registro de herramientas es `tools/toolreg.py`, que ya existía y sigue siendo
la fuente única. RXRE no añade un segundo catálogo.

## Capacidades (9, todas verificadas por ejecución)

| capacidad | herramienta de fondo | qué responde |
|---|---|---|
| `capabilities` | `toolreg.py` | qué sabe hacer, y si cada script responde de verdad |
| `search` | `evidence_search.py` | búsqueda literal, con el universo como evidencia |
| `symbol` | `evidence_search.py` | búsqueda de símbolo |
| `register` | `reg_resolve.py` | offset y campos de ASIC, con unidad declarada |
| `xref` | `xref.py` | referencias cruzadas por AST |
| `trace` | `trace_path.py` | cadena de llamadas con nodo vivo por ASIC |
| `pm4` | `pm4ops.py` | censo de opcodes PM4 |
| `evidence` | `evidence_search.py` | búsqueda con la clasificación a la vista |
| `provenance` | `prov.py` | claves de procedencia del árbol |

`capabilities` **ejecuta** cada script. No comprueba que el fichero esté en el
disco: comprueba que responde. Una capacidad listada pero rota es peor que una
ausente, porque la IA la elige, falla y pierde el turno.

## El contrato: un envelope, cuatro estados

```json
{
  "schema_version": "1.0",
  "status": "ok",
  "operation": "search",
  "target": "VM_CONTEXT0_CNTL",
  "results": [],
  "evidence": [],
  "provenance": [],
  "limitations": [],
  "tools_used": []
}
```

Las nueve claves existen **siempre**, incluso cuando `results` está vacío.

| `status` | significa | rc |
|---|---|---|
| `ok` | produjo resultados | 0 |
| `empty` | se ejecutó y no encontró | 0 |
| `blocked` | **no se pudo ejecutar**, y se dice por qué | 2 |
| `error` | la herramienta falló | 1 |

### La regla que impone el envelope

**`empty` nunca se convierte en ausencia.** Es la clase de defecto que este
proyecto cuenta siete veces, y el envelope la cierra por construcción: un `empty`
sale siempre con `limitations` explicando que la herramienta corrió y no
encontró, y que eso **no** es que no exista.

`blocked` existe porque `empty` no alcanza. `xref.py` sale con código 3 porque el
AST del árbol está a medias y completarlo es una escritura. Si eso se tradujera
a `empty`, una IA concluiría que `amdgpu_vm` no tiene referencias, que es falso.

Un `results` que contiene `verdict: NO_ENCONTRADO` **tampoco** cuenta como
resultado: `trace` lo sube a `limitations` y devuelve `empty`.

## Códigos de salida

```
0   ok o empty     (vacío NO es fallo: mira `status`)
1   error
2   blocked        (la precondición no se cumple; NO se ejecutó)
```

## Pruebas

```bash
python3 tools/rxre/tests/test_rxre.py
```

14 grupos, todos contra el corpus real. Sin mocks: cada vector ejecuta `rxre` de
verdad y comprueba el envelope que sale.

## Dos corporos, y por qué

`RESEARCH/working/linux-7.1.3` está **incompleto**: su `include/` solo contiene
`linux/`, no `drm/`. Por eso `trace` y `xref` apuntan a
`RESEARCH/kernelbuild/linux-7.1.3`, que sí tiene `include/drm/`.

Medido, no supuesto: con `working`, `trace_path.py` falla con
`CHIP_POLARIS12 no esta en include/drm/amd_asic_type.h`.

## Limitaciones conocidas

- **`xref` está bloqueada** en este árbol (`status: blocked`, rc=2). El AST está
  incompleto y `xref.py` no completa el build porque eso es una escritura. Es
  correcto que lo diga, y no se intenta esquivarlo.
- **`pm4` devuelve texto, no JSON**, porque `pm4ops.py` imprime una tabla. Se
  devuelve como un resultado de `kind: "texto"` y se dice que no es JSON, en vez
  de fingir que sí.
- **RXRE no revalida las herramientas de fondo.** Cada una trae su propio
  self-test. Revalidar 220 aquí sería duplicar `toolreg.py` y mentir sobre quién
  es responsable de qué.
- **No hay estado entre llamadas.** Sin sockets, sin demonios. El envelope lleva
  lo necesario para el siguiente paso.

## Estado

RXRE-001. 9 capacidades operativas, 14 grupos de vectores, 8 mutaciones
deliberadas probadas.

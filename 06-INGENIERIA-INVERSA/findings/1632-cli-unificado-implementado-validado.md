# 1632 — `./rxre` COMO PUNTO DE ENTRADA ÚNICO — IMPLEMENTADO Y VALIDADO

```text
CLASSIFICATION=IMPLEMENTATION
WORK_CLASS=RXRE-CLI-UNIFICATION-001
AUTOR=SISTEMA AUTÓNOMO RXRE
FECHA=2026-10-15
TARGET=Polaris12 (RX550) · GFX8 · 1002:699f
QUESTION=¿Puede una IA operar RXRE sin conocer rutas internas ni scripts individuales?
STATE=IMPLEMENTED + FUNCTIONALLY_VALIDATED
```

## PROBLEMA

El acceso a RXRE exigía conocer nombres de fichero, rutas y flags de scripts
concretos. Eso es conocimiento del **tooling**, no del **problema**. Cualquier
IA que arrives al árbol tenía que reconstruir el mapa antes de poder
investigar nada.

## IMPLEMENTACIÓN

`./rxre` (raíz del repositorio, antes un wrapper bash de 7 líneas) pasa a ser un
router en Python con 17 subcomandos.

### Principio de diseño: NADA SE IMPORTA

El CLI **no importa ningún módulo del proyecto**. Reenvía a
`tools/rxre/api/machine.py` por subprocess con JSON en stdin, e invoca las
herramientas auxiliares por subprocess. Consecuencia: ningún `import` del CLI
puede cambiar el estado de la herramienta a la que llama, y un fallo en una
herramienta no puede arrastrar al CLI.

### Rutas

Derivadas de `__file__`, nunca del cwd ni de rutas absolutas:

```python
RAIZ      = os.path.dirname(os.path.abspath(__file__))
MACHINE   = os.path.join(RAIZ, "tools", "rxre", "api", "machine.py")
FASE0_DIR = os.path.join(RAIZ, "RXRE", "tools")
```

### Superficie

```text
MOTOR (reenvían a machine.py como JSONL):
  ops, capabilities, backends, run, plan, reflect,
  explain, experiment, lessons, research, saturate

INTEGRACIÓN (invocan scripts existentes, contrato verificado):
  selftest, inventory, verify, workscan, mutate

AYUDA:  help
JSONL:  modo passthrough cuando no hay subcomando y stdin tiene datos
```

Los argumentos `--key value` se convierten en campos del request JSON, con
inferencia de tipo (`int`, `float`, `bool`, `str`).

### Contrato de salida

```text
stdout   solo datos (JSON en --json, texto legible por defecto)
stderr   solo diagnósticos
exit     0 ok/empty · 1 error · 2 blocked · 2 precondición incumplida
```

`empty` no es fallo: es un estado del contrato de `machine.py`
(`rc_por_estado: {ok:0, empty:0, unsupported:4, blocked:2, invalid_input:5, error:1}`).

## CONTRATOS VERIFICADOS ANTES DE INTEGRAR

No se integró ninguna herramienta sin comprobar su contrato. Los cinco
scripts FASE 0 declaran `READONLY=yes`, `WRITES_GPU=no`,
`TOUCHES_INTEGRATED=no`. Los tres de mutation testing:

| Herramienta | Ubicación | Superficie de escritura |
|---|---|---|
| `mutate_reg_resolve.py` | `/tmp/opencode/` scratch | no toca el repo |
| `mutate_relations.py` | `/tmp/opencode/` scratch | no toca el repo |
| `mutate_target.py` | `core/target.py` in-place | backup/restore; **requiere git limpio** |

`toolkit_cross.py` tiene un `ROOT` hardcodeado a
`~/Escritorio/RX550-INVESTIGACION/`. **No se integró** por eso. Las
herramientas FASE 0 lo leen **como texto** (análisis estático) — no lo importan
ni lo ejecutan. Verificado.

## VALIDACIÓN

`tools/rxre/tests/test_cli009.py` — **67 checks, 67 PASS**. Cubre: routing de
los 17 subcomandos, salida `--json` y `--human`, códigos de salida,
passthrough JSONL de una y varias líneas, errores, y **regresiones** de los
bugs hallados (ver hallazgos 1627, 1629, 1630, 1631).

Prueba de que la prueba discrimina: reintroducidos dos de los bugs, la suite
baja a 66/67 y 60/61 con el mensaje exacto del defecto. Restaurada: 67/67.

Baseline completo: **31 passed / 1 failed / 32 total**. El fallo es
`test_container1632.py`, **preexistente y ajeno**: se cuelga descomprimiendo
`amdgpu.ko.zst` sin `zstd`. No toca el CLI.

Contrato de `gpu.register_read` verificado **antes** de ejecutar cualquier
suite que lo use: solo lectura (`umr -r`, nunca `-w`/`--vm-write`), allow-list
exclusiva de `0000:01:00.0`, flag de lectura literal del adapter y no
parámetro del usuario.

## MUTATION TESTING

```text
mutate_reg_resolve  4/4 con comportamiento esperado
mutate_relations    4/4 con comportamiento esperado
mutate_target       4/4 con comportamiento esperado
./rxre mutate       rc=0
```

`target.py` verificado intacto tras el run (hash
`1eaf88ceae0a9a5c2687907c80b8359f9fa04f3f7d92b934bf42bb9d661b0739`,
`git status` vacío).

Los tres scripts de mutation testing, sus 4+4+4 mutantes, el oráculo, y dos
correcciones en el catálogo están documentados en los hallazgos 1628 y 1629.

## LO QUE ESTE HALLAZGO NO AFIRMA

- **No se integró nada con la iGPU.** `0000:00:02.0` no se tocó en ninguna
  operación. La prohibición del propietario es dura y se respetó.
- **No se validó el CLI con root.** `gpu.register_read` requiere root para MMIO.
  El camino existe y está probado como cableado; su ejecución real sobre la
  RX550 no se midió. `NOT_DETERMINED`.
- **No se midió rendimiento del CLI.** Es una herramienta de orquestación, no un
  hot path. No aplica §77.
- **No se ejecutó la suite con `--collect-only` únicamente**: cada subcomando se
  ejecutó de verdad y se comprobó su salida.

## FRONTERA ABIERTA QUE DEJA

1. **`selftest` no distingue tests que requieren root.** `run_baseline.py`
   usa `timeout=300s` por test y marca `FAIL`. Un test colgado por falta de
   root se confunde con un test roto. Falta una categoría `SKIP_NO_ROOT`.
2. **Guard de aplicabilidad del catálogo de mutantes.** Hoy un mutante no
   aplicable aparece como `FATAL` en runtime; debería ser un fallo rojo antes
   de mutar nada (hallazgo 1629).
3. **`detect_mode` bloquea** si stdin es un pipe que no cierra. `NOT_DETERMINED`
   (hallazgo 1631).
4. **`test_container1632.py`** falla por dependencia de entorno (`zstd`,
   `amdgpu.ko`). No investigado; fuera del alcance de este trabajo.

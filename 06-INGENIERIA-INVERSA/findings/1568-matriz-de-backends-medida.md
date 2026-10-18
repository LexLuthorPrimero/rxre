# 1568 · La matriz de backends medida: rizin 11 frente a radare2, y dos `empty` falsos que eran invocaciones incorrectas

```
CLASSIFICATION=MEASUREMENT · TRACK=RUNTIME
HARDWARE_SCOPE=NINGUNO (binarios del sistema) · WORK_CLASS=READ_ONLY
WRITE_EXECUTION=NONE · MODIFICATIONS=0 · GPU INTACTA
CIERRA=la seleccion de backends de §18 con producer ejecutado, no inferido
ABRE=la capacidad binary.decompile (ningun producer verificable todavia)
```

## Precondición verificada antes de medir (§27)

```text
rizin     d14c3fac4126bc5fbe66e7f3d1660aeab22b01d8  dev      dirty=0
rz-ghidra 64ea54a51c7f87983c9eba9cef8ee0c8cf2ac811  dev      dirty=0
angr      be995f52ee38a055d0f96d04f3e4d02192a3d743  master   dirty=0
radare2   008a7a6cd2e5acb8268f65f486760d080f3b107b  master   dirty=0
```

Los cuatro existen, HEAD verificable, árbol limpio.

## El hallazgo que cambió el planteamiento

**Los repositorios no son ejecutables, y el sistema ya tiene otros ejecutables.**

| | repo clonado | instalado |
|---|---|---|
| rizin | `v0.10.0-dev` | **`0.7.4`** (Fedora 43) |
| radare2 | master | **`5.9.8`** |
| angr | master | ausente (`1573`) |
| rz-ghidra | dev | ausente (Ghidra + Java) |

Y `import angr` funciona **dentro** del árbol por el namespace package
(`1573`).

> un backend cuya identidad no se puede verificar en runtime no puede entrar
> en provenance

## Lo medido, producer a producer

Entrada: `/bin/ls` (ELF x86-64) y el fixture propio `rxre_min.elf` (4728 B).

| capacidad | rizin 0.7.4 | radare2 5.9.8 |
|---|---|---|
| `binary.inspect` | `rz-bin -Ij` · dict 30 claves | `rabin2 -Ij` |
| `binary.sections` | `rz-bin -Sj` · 32 | no medido |
| `binary.symbols` | `rz-bin -sj` · 323 | no medido |
| `binary.imports` | `rz-bin -ij` · 121 | no medido |
| `binary.exports` | `rz-bin -Ej` · 16 | no medido |
| `binary.functions` | `aflj` · **112** | `aflj` · **201** |
| `binary.basic_blocks` | `afbj` | `afbj` |
| `binary.disassemble` | `pdj` | `pdj` |
| `binary.disassemble_func` | `pdfj` | no medido |
| `binary.strings` | `izj` · 639 | no medido |
| `binary.xrefs` | `aaa; axtj` · 3 | `aaa; axtj` · 3 |
| `binary.cfg` | `agf` · **ASCII** | `agfj` · JSON |
| `binary.callgraph` | `agC` · **ASCII** | `agCj` · 84 nodos |
| `binary.dataflow` | `afvxj` · JSON **mal formado** | `afvxj` · JSON válido |
| `binary.decompile` | **UNAVAILABLE** | **UNAVAILABLE** |

## Los dos `empty` falsos

**1. `aa` frente a `aaa`.** Escribí «rizin no calcula xrefs» y era **falso**:

```text
rizin -qc 'aa;  axtj @ 0x00000a40'  ->  []
rizin -qc 'aaa; axtj @ 0x00000a40'  ->  [{"from":25034,…},{"from":32158,…},{"from":59773,…}]
```

**2. Orden de flags.**

```text
rizin -qc -e scr.color=0 'aaa; afbj …'   ->  VACÍO, sin error
rizin -q  -e scr.color=0 -c 'aaa; …'    ->  JSON OK
```

`-qc` consume el argumento siguiente como comando y se come el `-e`.

> un resultado vacío de un productor mal invocado no dice nada del productor

Es `NOT_FOUND` disfrazado de `PROVEN_ABSENT`, y es la clase que el proyecto
cuenta desde el principio.

## La decisión (§18), machine-readable

```json
{ "primary": "rizin", "secondary": "radare2", "analytical": "NOT_DETERMINED" }
```

`PRIMARY = rizin`: cierra más capacidades medidas y es el único con `rz-bin`,
que da inspección **estática sin analysis**. `SECONDARY = radare2`: único medido
con `cfg` y `callgraph` en JSON. `ANALYTICAL = NOT_DETERMINED`, **no** «ninguno»:
no se comprobó angr ni rz-ghidra.

Vive en `backends/decision.json` y hay una **mutación** que la cambia a
`radare2` y falla un vector (`1568` §15). En prosa no sería verificable.

## Un detalle que salva a los auditores de 0.10-dev

En rizin 0.10 los verbos se declaran en `librz/core/cmd_descs/*.yaml`, no en
un `.c`: `grep -r aflj librz/` da **cero** y parece que la capacidad no existe.

## Lo que NO se hizo (§20)

No se compiló rizin 0.10-dev, no se instaló angr, no se instaló Ghidra. Ninguna
pregunta concreta lo exigía.

## Provenance

```text
artefactos  /bin/ls · tools/rxre/fixtures/bin/rxre_min.elf
producers   rizin 0.7.4 · rz-bin 0.7.4 · radare2 5.9.8 · rabin2 5.9.8
transform   invocacion -> captura -> limpieza de control chars -> json.loads
registro    tools/rxre/backends/registry.py
matriz      tools/rxre/docs/RXRE-004-BACKEND-MATRIX.md
decision    tools/rxre/backends/decision.json   (mutada y restaurada)
contrato    tools/rxre/docs/RXRE-004-BACKEND-CONTRACT.md
```
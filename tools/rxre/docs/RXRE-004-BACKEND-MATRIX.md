# RXRE-004 — BACKEND MATRIX

Medido el 2026-10-06. **Nada aquí es por nombre de fichero ni por nombre de
clase.** Cada capacidad declarada tiene un producer que se ejecutó y una salida
que se parseó.

---

## 0. Precondición verificada (§27)

```
rizin     d14c3fac4126bc5fbe66e7f3d1660aeab22b01d8  dev      dirty=0
rz-ghidra 64ea54a51c7f87983c9eba9cef8ee0c8cf2ac811  dev      dirty=0
angr      be995f52ee38a055d0f96d04f3e4d02192a3d743  master   dirty=0
radare2   008a7a6cd2e5acb8268f65f486760d080f3b107b  master   dirty=0
```

Los cuatro existen, HEAD verificable, árbol limpio.

---

## 1. EL HALLAZGO QUE CAMBIA TODO EL PLANTEAMIENTO

**Los repositorios no son ejecutables, y el sistema ya tiene otros ejecutables.**

| | repo clonado | instalado en el sistema |
|---|---|---|
| rizin | `v0.10.0-dev` (dev) | **`0.7.4`** (Fedora 43) |
| radare2 | master | **`5.9.8`** |
| angr | master | **ausente** |
| rz-ghidra | dev | ausente (necesita Ghidra + build) |

Y el caso de `angr` es instructivo:

```python
$ import angr                      # "funciona"
$ angr.__file__                     # None
$ angr.__path__  # ['…/tools/rxre/github/angr']   ← el DIRECTIO del repo
$ angr.Project                      # AttributeError
```

`import angr` **no importa angr**: el directorio clonado se llama `angr`, así que
Python lo encuentra como *namespace package*. Fuera del árbol:

```
ModuleNotFoundError: No module named 'angr'
```

> un import que funciona no es un paquete importado

**Esto tiene una consecuencia de diseño, no solo de entorno:** un backend cuya
identidad no se puede verificar en runtime no puede entrar en provenance. RXRE
registraría un `backend_version` que no puede confirmar.

---

## 2. Qué se ejecutó de verdad

Backend usado para la matriz: **los instalados**, porque son los que corren.
El repo de rizin sirve como *fuente* para preguntar si una capacidad existe
en 0.10-dev (§6 permite auditar la fuente).

Entrada: `/bin/ls`, ELF x86-64, 153.400 bytes.

### 2.1 rizin 0.7.4

| capacidad | verbo | salida | estado |
|---|---|---|---|
| binary.inspect | `rz-bin -Ij` | JSON dict, 30 claves | **AVAILABLE** |
| binary.sections | `rz-bin -Sj` | JSON list, 32 | **AVAILABLE** |
| binary.symbols | `rz-bin -sj` | JSON list, 323 | **AVAILABLE** |
| binary.imports | `rz-bin -ij` | JSON list, 121 | **AVAILABLE** |
| binary.exports | `rz-bin -Ej` | JSON list, 16 | **AVAILABLE** |
| binary.functions | `rizin -qc 'aa; aflj'` | JSON list, **112** | **AVAILABLE** |
| binary.basic_blocks | `rizin -qc 'aa; afbj @ entry0'` | JSON list, 1 | **AVAILABLE** |
| binary.disassemble | `rizin -qc 'aa; pdj 5 @ entry0'` | JSON list, 5 | **AVAILABLE** |
| binary.disassemble_func | `rizin -qc 'aa; pdfj @ entry0'` | JSON dict | **AVAILABLE** |
| binary.strings | `rizin -qc 'aa; izj'` | JSON list, 639 | **AVAILABLE** |
| binary.xrefs | `rizin -qc 'aaa; axtj @ 0x00000a40'` | JSON list, 3 | **AVAILABLE** |
| binary.callgraph | `rizin -qc 'aaa; agC'` | **ASCII/visual** | **PARTIAL** |
| binary.cfg | `rizin -qc 'aaa; agf'` | **ASCII/visual** | **PARTIAL** |
| binary.dataflow | `rizin -qc 'aa; pdj 5'` | JSON list, 5 | **PARTIAL** |
| binary.decompile | — | **no** | **UNAVAILABLE** |

### 2.2 radare2 5.9.8

| capacidad | verbo | salida | estado |
|---|---|---|---|
| binary.inspect | `rabin2 -Ij` | JSON dict | **AVAILABLE** |
| binary.functions | `r2 -q -c 'aaa; aflj'` | JSON list, **201** | **AVAILABLE** |
| binary.basic_blocks | `r2 -q -c 'aaa; afbj @ entry0'` | JSON list, 1 | **AVAILABLE** |
| binary.cfg | `r2 -q -c 'aaa; agfj @ entry0'` | JSON list, 1 | **AVAILABLE** |
| binary.callgraph | `r2 -q -c 'aaa; agCj'` | JSON list, **84** | **AVAILABLE** |
| binary.disassemble | `r2 -q -c 'aaa; pdj 5 @ entry0'` | JSON list, 5 | **AVAILABLE** |
| binary.xrefs | `r2 -q -c 'aaa; axtj @ 0x00000a40'` | JSON list, 3 | **AVAILABLE** |
| binary.dataflow | — | **no medido** | **NOT_DETERMINED** |
| binary.decompile | — | **no** | **UNAVAILABLE** |
| binary.strings | — | **no medido** | **NOT_DETERMINED** |

### 2.3 angr / rz-ghidra

| capacidad | estado | por qué |
|---|---|---|
| todo | **NOT_DETERMINED** | `angr` no es importable fuera del repo; `rz-ghidra` requiere Ghidra + CMake + toolchain Java |

**No se clasifican como `UNAVAILABLE`.** No se comprobó que no puedan, se
comprobó que **no se pueden verificar aquí**. Ausencia de prueba no es prueba de
ausencia (§5).

---

## 3. LA CORRECCIÓN QUE IMPORTÓ

Mi primera pasada dio `xrefs: 0` en rizin y lo escribí como
*«rizin 0.7 no calcula xrefs»*.

**Era falso, y el error era mío:** usaba `aa` en vez de `aaa`.

```text
rizin -qc 'aa;  axtj @ 0x00000a40'  -> []
rizin -qc 'aaa; axtj @ 0x00000a40'  -> [{"from":25034,...},{"from":32158,...},{"from":59773,...}]
```

Lo mismo con CFG: `agf` existe pero **solo emite ASCII/visual**, no JSON. ahí sí
`PARTIAL` es correcto.

> un `empty` de una herramienta puede ser un verbo mal escrito

Esto es `NOT_FOUND` disfrazado de `PROVEN_ABSENT`, y es exactamente la clase que
el proyecto cuenta desde el principio.

---

## 4. Detalles de integración que salen de la medición

### 4.1 `rz-bin -j` NO basta

```
$ rz-bin -j /bin/ls
Usage: rz-bin [-AcdeEghHiIjlLMqrRsSUvVxzZ] ... file
```

`-j` es un modificador, no un modo. Hay que combinarlo: `-Ij`, `-Sj`, `-sj`,
`-ij`, `-Ej`. **Cada modo produce una clave distinta**, verificado:

```
-I  -> {"info": {...}}      30 claves
-S  -> {"sections": [...]}  32
-s  -> {"symbols": [...]}   323
-i  -> {"imports": [...]}   121
-E  -> {"exports": [...]}   16
```

### 4.2 stdout viene sucio por defecto

`rizin` mete secuencias ANSI y `\r` en stdout. Sin `-e scr.color=0` el JSON no
parsea:

```text
rizin -qc 'aaa; afbj @ entry0'            -> no parsea (ANSI + \r)
rizin -qc -e scr.color=0 'aaa; afbj @…'   -> JSON OK
```

r2 necesita lo mismo (`-e scr.color=0`). **Un normalizador que no lo limpiese
declararía `error` en una salida perfectamente válida.**

### 4.3 rizin 0.10-dev cambió la disposición del código

`aflj` no aparece en ningún `.c` de `librz/core/`. No es que no exista: en
0.10 los verbos se declaran en **`librz/core/cmd_descs/*.yaml`** y se registran
desde `cmd_descs.c`:

```c
RzCmdDesc *analysis_graph_bb_function_cd =
    rz_cmd_desc_argv_new(core->rcmd, ag_cd, "agf",
                         rz_analysis_graph_bb_function_handler, …);
```

Auditar el repo exige saber esto. Un `grep` en `libr/` da cero y parece que la
capacidad no existe.

---

## 5. Matriz consolidada

`AVAILABLE` = producer ejecutado + salida parseada.
`PARTIAL` = ejecutado pero la forma no cumple el contrato (no-JSON, o refinado).
`UNAVAILABLE` = comprobado que el producer no existe.
`NOT_DETERMINED` = no comprobado.

| capacidad | rizin 0.7.4 | r2 5.9.8 | angr | rz-ghidra |
|---|---|---|---|---|
| binary.inspect | AVAILABLE | AVAILABLE | ND | ND |
| binary.sections | AVAILABLE | ND | ND | ND |
| binary.symbols | AVAILABLE | ND | ND | ND |
| binary.imports | AVAILABLE | ND | ND | ND |
| binary.exports | AVAILABLE | ND | ND | ND |
| binary.functions | **AVAILABLE** | **AVAILABLE** | ND | ND |
| binary.basic_blocks | AVAILABLE | AVAILABLE | ND | ND |
| binary.disassemble | AVAILABLE | AVAILABLE | ND | ND |
| binary.disassemble_func | AVAILABLE | ND | ND | ND |
| binary.strings | AVAILABLE | ND | ND | ND |
| binary.xrefs | AVAILABLE | AVAILABLE | ND | ND |
| binary.cfg | **PARTIAL** | **AVAILABLE** | ND | ND |
| binary.callgraph | **PARTIAL** | **AVAILABLE** | ND | ND |
| binary.dataflow | PARTIAL | ND | ND | ND |
| binary.decompile | **UNAVAILABLE** | **UNAVAILABLE** | ND | ND |

`ND` = `NOT_DETERMINED`, no ausente.

---

## 6. Decisión de backend (§18)

**No es «no decisión». La evidencia sostiene una, y es medida:**

```text
PRIMARY    = rizin 0.7.4
SECONDARY  = radare2 5.9.8
ANALYTICAL = NO_DETERMINED
```

**PRIMARY = rizin**, por evidencia:

1. Es el único que cubre **9 de 11** capacidades medidas con salida parseada.
   r2 cubre 6 de las 11 medidas.
2. **`rz-bin` da inspección estática sin analysis** (`-I`, `-S`, `-s`, `-i`, `-E`),
   que es lo que RXRE necesita para `binary.inspect`: r2 no tiene equivalente
   separado y medido.
3. Rizin y r2 **coinciden** en `xrefs` (3 referencias al mismo símbolo) y en
   `disassemble`. La coincidencia entre dos producers independientes es
   corroboración; la usará `binary.xrefs` cuando lo integre.

**SECONDARY = radare2**, por evidencia y solo esta:

`binary.cfg` y `binary.callgraph` devuelven **JSON** en r2 (`agfj`, `agCj` → 84
nodos) y **ASCII** en rizin 0.7. Para esas dos capacidades, r2 es el único
backend medido que cumple el contrato.

**ANALYTICAL = `NOT_DETERMINED`**, no «ninguno». No se comprobó angr ni
rz-ghidra. Decir «no hay backend de decompilación» sería convertir
`NOT_DETERMINED` en `PROVEN_ABSENT` — la clase de defecto que §5 prohíbe.

**Sobre decompilación: ninguna capacidad de decompilación se declara.** Ni rizin
ni r2 la tienen. rz-ghidra la tiene y es la ruta, pero **no es verificable aquí**
y por tanto no se puede integrar con provenance creíble.

---

## 7. Lo que cada backend **no** puede dar

| | rizin 0.7.4 | r2 5.9.8 |
|---|---|---|
| CFG en JSON | no (ASCII) | sí |
| callgraph en JSON | no (ASCII) | sí |
| análisis sin color | hay que forzarlo (`-e scr.color=0`) | hay que forzarlo |
| decompilación | no | no |
| dataflow real | refinado (pdj = desensamblado) | no medido |

---

## 8. Lo que NO se hizo, y por qué (§16)

- **No compilé** rizin 0.10-dev. Meson + capstone + 258 MB, y ninguna pregunta
  concreta lo exige: 0.7.4 ya cubre `binary.inspect` y `binary.functions`.
- **No instalé** angr ni Ghidra. `pip install angr` es una dependencia global sin
  pregunta que la justifique, y rz-ghidra exige además el toolchain Java.
- **No escribí** el adapter todavía. §27 dice cerrar la matriz antes, y §28 dice
  que si una capacidad ya expone el contrato, se construye solo esa.

---

## 9. La siguiente acción, justificada por esta matriz

**`binary.inspect`** es la vertical completa, y la evidencia la elige:

- rizin lo da con **`rz-bin -Ij`**: un comando, salida JSON, sin analysis, sin
  estado, **sin color**, determinista.
- Es la entrada natural de la cadena que §29 describe:
  `registro → candidatos → binario → función → …`.
- Su `provenance` es la más simple de sostener: comando, argv, rc, stdout
  crudo, hash del input.

Y es la que menos riesgo de contrato tiene, porque **no depende del análisis**:
si mañana rizin desaparece, `binary.inspect` sigue siendo reproducible.

---

## 10. Nota sobre el método

Este documento contiene **una corrección de la propia auditoría**: escribí
«rizin no calcula xrefs» y era un verbo mal escrito.

Es la tercera vez en cuatro iteraciones que un `empty` mío viniendo de una
herramienta mal llamada se lee como una afirmación sobre la herramienta.

> un resultado vacío de un productor mal invocado no dice nada del productor

La regla de RXRE-003 se extiende: **un `empty` hay que poder distinguir de un
`empty` por verbo equivocado**, o el pre-execution check (§15) tiene que
existir y ejecutarse. Es el argumento exacto de por qué §15 existe, y hasta
ahora no lo había tenido que cumplir.
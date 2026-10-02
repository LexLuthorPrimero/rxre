# 033 · El bloque MMU/VM de GFX8 no está publicado por AMD: `NOT_PUBLISHED`, no `NOT_DETERMINED`

`CLASSIFICATION=EXTERNAL` · `TRACK=STATIC` · `HOST_SCOPE=HOST-C` · `GPU INTACTA`
`ALIASES=los tres NOT_DETERMINED abiertos por 019/030/032`

## CUDA principal

`AGENTS.md` §"DOCUMENTACIÓN EXTERNA" autoriza salir del corpus sólo tras
`CORPUS_COMPLETENESS_CHECK` y `READ_SCOPE_GATE`. Ambas se habían cumplido. La búsqueda
externa devuelve un resultado con valor de por sí:

**No existe documento público de AMD sobre el bloque de gestión de memoria de GFX8.** Los
tres `NOT_DETERMINED` que quedaban no son "aún no buscados": son **documentación que AMD no
publica**. Eso los cambia de categoría, y es una afirmación más fuerte y más falsificable
que un `NOT_DETERMINED`.

## El índice de arquitectura de AMD, enumerado completo

Fuente única: <https://gpuopen.com/amd-gpu-architecture-programming-documentation>
(AMD la titula *"If you're looking to work at a lower level with AMD hardware, this page
contains links to some of our publicly available PDFs"*). Documentos enlazados, lista
íntegra tal como aparece:

| grupo | documentos |
|---|---|
| MES firmware | RDNA 3 MES (`micro_engine_scheduler.pdf`) — **1 doc** |
| RDNA | RDNA 4, RDNA 3.5, RDNA 3, RDNA 2, RDNA 1 ISA — **5** |
| CDNA | CDNA 5, 4, 3, 2, 1 ISA — **5** |
| antiguas | Vega 7nm ISA, Vega ISA, GCN 3 ISA — **3** |
| machine-readable | XML de ISA, **sólo RDNA y CDNA** — **0 para GCN3** |

Catorce documentos. **Catorce son ISA de shader** y uno es firmware de scheduler. Ninguno
trata MMU, TLB, page walker, formato de PTE, ni orden de invalidación.

El propósito que AMD declara para un ISA, textual:

> 1. Specify the language constructs and behavior, including the organization of each type
>    of instruction in both text syntax and binary format.
> 2. Provide a reference of instruction operation that compiler writers can use to maximize
>    performance of the processor.

Compiladores, no sistemas de traducción de direcciones. El documento de MES es el único que
rozaría la planificación, y es de **RDNA 3**, no de GFX8, y además declara: *"not meant to serve as a programming guide"*.

**Clasificación resultante:**

| `NOT_DETERMINED` de | Pregunta | Nuevo estado |
|---|---|---|
| `019`/`030` | efecto hardware de `INVALIDATE_ALL` por caché | `NOT_PUBLISHED` |
| `030` | orden intra-envío entre el invalidate del PFP y el IB | `NOT_PUBLISHED` |
| `032` | hardware con `VALID=0` vs `PA=0` con `VALID=1` | `NOT_PUBLISHED` |
| `032` | qué es el bit 54 (`AMDGPU_PDE_PTE`) en GFX8 | `NOT_PUBLISHED` |

La búsqueda de la especificación de **PM4** para GFX8 es aún más hopeless: los PM4 son
comandos de *commando processor*, no de shader, y caen fuera del alcance declarado de un ISA
por la definición textual de arriba.

## Un defecto observado en la propia página de AMD

El enlace **"AMD Vega ISA"** y el de **"AMD GCN 3 ISA"** apuntan al **mismo URL**:

```
https://www.amd.com/system/files/TechDocs/gcn3-instruction-set-architecture.pdf
```

El de Vega debería ser `vega-instruction-set-architecture.pdf`. Consecuencia práctica:
**no se puede confiar en la etiqueta de un enlace de esa página**; hay que abrir el PDF y
comprobar la portada. Es el mismo error de clase que el de `030` (leer el nombre en vez del
valor), y aparece en la documentación del fabricante.

**`NOT_READ`**: la descarga del PDF falló desde este host —
`curl: (92) HTTP/2 stream 1 was not closed cleanly: INTERNAL_ERROR`, `http=000`, 0 bytes.
Por tanto **no afirmo nada sobre el contenido del GCN3 ISA**. Lo único verificado es que AMD
lo enlaza y cómo lo describe.

## GFX8 como target de compilador: verificado en este host, y un rumor refutado

Era un riesgo abierto para el objetivo del proyecto: si el ensamblador GFX8 desaparece, la
idea de escribir el driver en ensamblador pierde su herramienta. Segunda fuente
(`llvm.org/docs/AMDGPUUsage.html`) confirma que `AMDGCNGFX8` sigue listado como target
reconocido.

Medición directa sobre la toolchain del host:

```
clang   clang version 22.1.8 (Fedora 22.1.8-4.fc44)
gcc     gcc (GCC) 16.2.1 20260819
as      Ensamblador GNU version 2.46.1-1.fc44
```

`clang -target amdgcn -mcpu=gfx803` **funciona**, y el despacho por target es real, no un
alias. Matriz de aceptación por instrucción (con `s_endpgm` como terminador; `ret` es
x86 y no ensambla en AMDGPU — me costó una ronda de falsos negativos verlo):

| instrucción | gfx803 | gfx900 | gfx906 | gfx1030 | gfx1100 |
|---|---|---|---|---|---|
| `v_mul_f32 v0, v1, v2` | SI | SI | SI | SI | SI |
| `ds_permute_b32 v0, v1, v2` | SI | SI | SI | SI | SI |
| `v_mad_u32 v0, v1, v2, v3` | **no** | no | no | no | no |
| `global_atomic_add v0, v1, v2, v3` | **no** | no | no | no | no |
| `v_cmp_gt_f32_e64 s0, v0, v1` | no | no | no | **SI** | **SI** |
| `v_dot2acc_f32_f16 v0, v1, v2` | no | no | no | no | **SI** |

Los discriminantes son las dos últimas filas: instrucciones aceptadas sólo en gfx10/gfx11.
Un ensamblador que ignorase `-mcpu` las habría aceptado todas. Y el lado negativo de gfx803
es explícito, no silencioso:

```
$ clang -target amdgcn -mcpu=gfx803 -c tmp.s
tmp.s:4:3: error: instruction not supported on this GPU
        v_mad_u32 v0, v1, v2, v3
```

**Rumor refutado.** Una fuente secundaria (Phoronix) afirma que *"gfx803 was deprecated in
GCC 14, removed from LLVM 18"*. Las notas de release de LLVM 18.1.0 no mencionan gfx803 en su
sección AMDGPU (y son explícitamente "non-comprehensive", así que su ausencia no es
una refutación). La medición **refuta la consecuencia práctica** en la toolchain moderna:
clang 22.1.8, seis versiones mayor, sigue ensamblando GFX8. No contradigo la afirmación
literal sobre qué hizo LLVM 18 — no la verifiqué —; sí registro que el riesgo para este
proyecto, tal como se enunció, **no se materializa**.

## Lo que esto deja

**Nada que hacer en el corpus, y nada que buscar fuera.** Los cuatro `NOT_PUBLISHED` sólo se
cierran con la especificación de arquitectura de GFX8, que está bajo NDA o nunca se escribió
en forma pública. Quien la tenga puede resolver cuatro preguntas que llevan abiertas desde
`019`. Nadie la tiene en el corpus, ni en el índice de AMD, ni en LLVM, ni en ROCm.

Esto es exactamente la razón legítima de parada de `AGENTS.md` §Regla de continuidad: **falta
de evidencia que no se puede conseguir por más búsqueda que se haga**, y está demostrado que
no es falta de esfuerzo.

## Consecuencias para el driver propio

Consecuencia práctica que **sí** se puede actuar:

1. La barrera de estas cuatro preguntas no se salva buscando. La barrera del driver propio
   es que **no habrá especificación contra la cual escribir la parte de VM**. Hay que
   escribirla contra el **driver de referencia**, que ya está leído y verificado
   (`017`–`032`).
2. Eso hace del corpus la **fuente primaria única** de la semántica de VM en GFX8, y por
   tanto eleva el valor de lo ya hecho: la geometría del walk, el productor de PTE de 9
   dwords, la ausencia de registro de ack, y la fórmula de reserva están *verificados* y no
   son recuperables de otro modo.
3. El toolchain GFX8 existe y funciona. Escribir ensamblador GFX8 en 2026 es viable.

## Criterio de falsación

Este hallazgo se refutaría con **una URL**. Si existe un documento público —AMD u otro— que
documente el MMU de GFX8 (formato de PTE, semántica de TLB invalidate, u orden de ejecución
del page walker), entonces `NOT_PUBLISHED` es falso y las cuatro preguntas se reabren. El
enlace hay que publicarlo junto al refutador; un "creo que existe en el wiki de
freedesktop" no lo refuta.

La tabla de la toolchain se refutaría si `clang -target amdgcn -mcpu=gfx803` dejara de
aceptar `v_mul_f32` en una versión futura, o si aceptara `v_dot2acc_f32_f16`.

## Evidencia

```
externo:  gpuopen.com/amd-gpu-architecture-programming-documentation  (índice completo, 14 docs)
          llvm.org/docs/AMDGPUUsage.html  (AMDGCNGFX8 listado)
          releases.llvm.org/18.1.0/docs/ReleaseNotes.html  (sección AMDGPU: sin mención gfx803)
          Phoronix  (fuente secundaria del rumor, NO usada como hecho)
host:     clang 22.1.8 / gcc 16.2.1 / as 2.46.1,  matriz de 6 instrucciones x 5 targets
fallo:    curl del PDF GCN3 ISA -> HTTP/2 INTERNAL_ERROR, 0 bytes  => NOT_READ
corpus:   sin cambios; MODIFICATIONS=0; ningún registro de MMIO leído; RUNTIME=NOT_RUN salvo
          la invocación del compilador, que no toca la GPU
```

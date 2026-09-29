# 002 — Validador para kernel OpenCL C (Fase 4A)

**Ámbito**: `08-ARQUITECTURA/` — IA-3 (Arquitecto)
**Fecha**: 2026-09-29 · **Ronda**: 4
**Estado**: diseño preliminar
**Reemplaza a**: nada. **Sustituye el papel de** `test_decompress.c` de la Fase 2, que **no
aplica** al formato OpenCL C (`F4-AD-12`).

---

## 1. Por qué hace falta un validador nuevo

`test_decompress.c` valida **SPIR-V** ejecutado por RADV. El artefacto de Fase 4 es un **objeto
ELF `amdgcn`** con ISA emitida. Son formatos distintos, con nombres de función distintos
(`bc3_decode` frente a `main`), y **el test de la Fase 2 no se le puede aplicar**.

No es una adaptación. Es otro test, con otro objeto de entrada.

## 2. Lo que ya está medido sobre el artefacto real

Compilé un decodificador BC3 completo en OpenCL C a `gfx803` para no diseñar sobre suposiciones:

```
clang -target amdgcn -mcpu=gfx803 -x cl -cl-std=CL2.0 -O2 -c d.cl -o d.o
```

| Hecho | Valor medido |
|---|---|
| Compila | **sí**, sin errores |
| Secciones | `.text` · `.rel.text` · `.AMDGPU.config` · `.AMDGPU.gpr_maximums` |
| `.text` | **0x0aac** bytes de ISA |
| Símbolo del kernel | `bc3_decode` |
| ISA emitida | `s_mov_b32 s36, lit(0x0)` … (desensamblado real, no placeholder) |

**Y el hallazgo que cambia el diseño de la 4A**: `.rel.text` existe y trae reubicaciones
**sin resolver**. Con un kernel de decodificación son **6**; con un kernel que usa LDS y
atómicos, **22**:

```
OFFSET  TYPE                    VALOR
0004    R_AMDGPU_ABS32_LO       SCRATCH_RSRC_DWORD0
000c    R_AMDGPU_ABS32_LO       SCRATCH_RSRC_DWORD1
0068    R_AMDGPU_REL32_LO       _Z13get_global_idj
0070    R_AMDGPU_REL32_HI       _Z13get_global_idj
0590    R_AMDGPU_REL32_LO       _Z13get_global_idj
0598    R_AMDGPU_REL32_HI       _Z13get_global_idj
```

| Símbolo reubicado | Veces en el kernel con LDS+atómicos |
|---|---|
| `SCRATCH_RSRC_DWORD0` | 2 |
| `SCRATCH_RSRC_DWORD1` | 2 |
| `_Z13get_global_idj` (`get_global_id`) | 2 |
| `_Z12get_local_idj` (`get_local_id`) | 2 |
| `_Z7barrierj` (`barrier`) | 2 |
| `_Z10atomic_addPU3AS1Vjj` | 2 |
| `_Z9atomic_orPU3AS1Vjj` | 2 |
| … | 22 entradas en total |

**El objeto NO es cargable tal cual.** Un driver tiene que resolver esas reubicaciones antes de
escribirlo en el ring, y **el conjunto depende del kernel**. Medido: el decodificador da 6, un
kernel con LDS y atómicos da 22. Los `SCRATCH_RSRC_DWORD*` son scratch privado que el driver
debe asignar; los builtins (`get_global_id`, `barrier`, `atomic_*`) no tienen dirección fija.

**Consecuencia para V4**: la comprobación **no puede ser «el conjunto es exactamente este»**,
porque el conjunto varía con el kernel. Tiene que ser **«todo símbolo reubicado pertenece al
conjunto conocido y cada uno está resuelto»**. Es una diferencia de fondo, y la versión que
tenía redactada era incorrecta.

**Consecuencia para la 4A**: "volcar PM4 a memoria para inspección" **subestima el trabajo**.
El paso de objeto ELF a código ejecutable es un **procesador de reubicaciones**, y eso es
trabajo real de driver, no una volcadura. La 4A debe incluirlo.

## 3. Qué valida este test, y qué NO

| El validador **sí** establece | El validador **NO** establece |
|---|---|
| El kernel compila a ISA gfx803 sin error | Que el hardware la ejecute |
| `.text` no está vacío y es ISA legal | Que el ISA sea *correcto* |
| Las reubicaciones esperadas son las que hay | Que el ring la ejecute bien |
| El corpus de entrada llega íntegro | Que el resultado en VRAM sea correcto |
| La salida del **modelo de CPU** del algoritmo es la esperada | Nada sobre el hardware |

La fila de la derecha es la que importa, y es la razón por la que la 4B no es opcional
(`F4-AD-11`).

## 4. Arquitectura del validador: tres capas, deliberadamente separadas

```
capa 3  ── agreement test en GPU     ← Fase 4B, requiere unbind. NO EXISTE AÚN.
   ▲
   │  (solo cuando exista)
   │
capa 2  ── validador de OBJETO       ← Fase 4A. Este documento. Verifica el artefacto.
   ▲
   │  artefacto idéntico en ambas
   │
capa 1  ── agreement test en CPU     ← Fase 4A. Verifica el ALGORITMO.
```

**La separación es el requisito de diseño, no un detalle.** La capa 1 no necesita driver ni
hardware: es el algoritmo de decodificación BC3 en C, comparado contra el corpus. Si la capa 1
falla, todo lo demás es irrelevante.

### Capa 1 — agreement test en CPU (prioridad máxima)

```
test_ocl_cpu.c   — decodificador BC3 en C  vs  golden_ref[]  (del corpus de Fase 2)
```

- **Reutiliza** el corpus y los vectores de `04-IMPLEMENTACION/compressor/test_compress.c`. El
  algoritmo **no ha cambiado**: cambió el lenguaje, no la aritmética. La rampa alfa sigue
  siendo `+3`/`+2` (`F4-AD-11` en Fase 1, `F4-AD-12` aquí).
- **Objetivo**: 0/4096 bytes discrepantes.
- **Autovalidación obligatoria**: el corpus no vacío, la salida no toda cero, el patrón veneno
  eliminado. Sin esto, una salida a cero daría «0 discrepancias» y un falso `PASS` (`F4-AD-7`).

### Capa 2 — validador de objeto

```
test_ocl_object.c  — parsea el ELF amdgcn y verifica su forma
```

Comprobaciones, todas contra el artefacto real, ninguna inventada:

| # | Comprobación | Por qué |
|---|---|---|
| V1 | magic ELF, clase 64, máquina `EM_AMDGPU` | no es otro ELF por error |
| V2 | `.text` existe y tiene tamaño > 0 | un `.text` vacío compila igual |
| V3 | `.AMDGPU.config` existe y no está vacío | el hardware la necesita |
| V4 | `.rel.text`: **todo** símbolo reubicado ∈ conjunto conocido | conjunto medido: 6 (decodificador) … 22 (con LDS/atomicos) |
| V5 | toda reubicación está **resoluble** y a 32 bits | un símbolo desconocido no se puede resolver |
| V6 | desensamblado de una muestra de `.text` | que sea ISA, no datos |

**V4 es la comprobación fuerte.** El conjunto de símbolos reubicados es una huella del kernel:
si mañana cambia el número de `get_global_id` o aparece un `SCRATCH_RSRC_DWORD2`, el conjunto
cambia y el validador lo detecta. Es un control de regresión sobre el artefacto, no una
inspección de forma.

### Capa 3 — agreement test en GPU

`Fase 4B`. No se diseña todavía: depende de `F4-AD-15` (autorización de `unbind`) y de que
exista el driver. **Documentarla como inexistente**, no como pendiente de escribir, evita que
alguien la cuente como cobertura.

## 5. Control negativo: obligatorio desde el primer commit

Un test que solo puede pasar no prueba nada. Tres mutantes, **con el test ya escrito**:

| # | Mutante | Detección esperada |
|---|---|---|
| N1 | `+3` → sin `+3` en la rama `/7` | capa 1: fallos en ~83 % de pares |
| N2 | `cbyte = p>>2` → `8*(cbyte-2u)` (el bug real de Fase 2) | capa 1: fallos solo en `p = 8..15` |
| N3 | `.text` truncado a la mitad | capa 2: V2 falla |

**N2 es el control más valioso**: es el bug que el shader de Fase 2 tuvo de verdad y que
`shader_vs_c` **no detectó**. Si el mutante se rechaza, la capa 1 tiene poder de discernimiento
sobre el tipo de defecto que realmente ocurrió.

Regla: **el test entra en el repo junto con su mutante**, no después. Un test sin control
negativo se considera no terminado.

## 6. Diferencias con `test_decompress.c` de la Fase 2

| | Fase 2 | Fase 4A |
|---|---|---|
| Artefacto | `decompress_bc3.spv` | objeto ELF `amdgcn` |
| Lenguaje | GLSL → SPIR-V | OpenCL C → ISA |
| Parámetro de bloques | push constant | **argumento de kernel** |
| Validación | GLSL + código | compilación a ISA |
| Dónde se ejecuta | GPU vía RADV | **CPU, capa 1** |
| Alcance del resultado | 0/4096 en hardware real | estructura del artefacto |

**La última fila es la que hay que subrayar.** El artefacto de Fase 2 fue validado **en la
RX 550**. El de Fase 4A **no lo estará hasta 4B**. No son resultados equivalentes y no
deben citarse como tales.

## 7. Criterio de éxito de la 4A

| # | Criterio |
|---|---|
| A1 | El kernel OpenCL C compila a `gfx803` sin error |
| A2 | Capa 1: **0 de 4096** bytes discrepantes |
| A3 | Capa 1 **rechaza** los tres mutantes N1, N2, N3 |
| A4 | Capa 2: V1..V6 pasan sobre el artefacto real |
| A5 | El procesador de reubicaciones resuelve las 6 reubicaciones medidas |

**A5 es el que revela el coste real de la 4A.** Sin él, «volcar a memoria» es una descripción
optimista.

## 8. Lo que este documento no hace

- **No** afirma que la ISA emitida sea *correcta*. Que se desensamble no prueba que compute bien.
- **No** diseña el procesador de reubicaciones: eso pertenece a IA-2, y solo tras conocer el
  formato de ring (`PENDIENTE-IA-1`).
- **No** promete cobertura de hardware. La capa 3 no existe.

## 9. Pregunta a IA-1 asociada

Ver `reviews/2026-09-29-arch-to-ia1.md`: ¿son esas seis reubicaciones las que el hardware espera,
y hace falta alguna más para compute?

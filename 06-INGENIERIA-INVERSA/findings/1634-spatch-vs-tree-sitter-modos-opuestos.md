# 1634 — spatch Y tree-sitter NO SON INTERCAMBIABLES: MODOS DE FALLO OPUESTOS — MEDIDO

```text
CLASSIFICATION=COMPARISON
WORK_CLASS=RXRE-ECO-001
AUTOR=SISTEMA AUTÓNOMO RXRE
FECHA=2026-10-15
TARGET=Polaris12 (RX550) · GFX8 · 1002:699f
QUESTION=Dos herramientas que responden la misma pregunta, ¿son intercambiables?
STATE=REFUTED
```

## LA PREGUNTA

«¿Cuántas veces aparece la cadena X en el código, y dónde?» es la pregunta
que hace una IA sobre el driver de amdgpu. `spatch` (Coccinelle) y
tree-sitter la responden. La tempting conclusión es que una sustituye a la
otra.

Se midió en vez de suponer. **Sin elegir ganador por anticipado.**

## LAS CINCO ENTRADAS DISEÑADAS PARA SEPARAR

| Caso | Contenido | texto | AST | correcto |
|---|---|---|---|---|
| código | `int MARCA(void){return 1;}` | 1 | **1** | 1 |
| ausente | `int OTRA(void){return 0;}` | 0 | **0** | 0 |
| comentario | `/* MARCA */` + función | 1 | **0** | 0 |
| cadena literal | `const char *s = "MARCA";` | 1 | **0** | 0 |
| preprocesador | `#include <drm/drm_MARCA.h>` | 1 | **0** | 0 |

Las tres últimas son las que separan, y juntas dicen algo que ningún score
diría: **un `grep` las cuenta, un AST no.** Porque no son apariciones de una
cadena: son apariciones de un **identificador**.

## SOBRE EL CÓDIGO REAL, NO SOBRE CASOS DE LABORATORIO

```text
SOBRE EL CODIGO REAL (amdgpu.h, 42872 bytes)
  texto=11  tree-sitter=10  duracion=0.064s
```

La diferencia es **exactamente una**, y es `drivers/gpu/drm/amd/amdgpu/amdgpu.h`
línea 54:

```c
#include <drm/drm_ioctl.h>
```

Las otras 10 son identificadores reales: `amdgpu_bo_list_ioctl`,
`amdgpu_cs_ioctl`, `amdgpu_cs_fence_to_handle_ioctl`,
`amdgpu_cs_wait_ioctl`, `amdgpu_cs_wait_fences_ioctl`, `drm_ioctl_desc`,
`amdgpu_ioctls_kms`, `amdgpu_max_kms_ioctl`, `amdgpu_info_ioctl`,
`amdgpu_proc_options_ioctl`.

El `#include` **no es código ejecutable**. Un árbol sintáctico lo sabe; una
búsqueda de texto no.

## POR QUÉ `spatch` NO RESPONDE ESTA PREGUNTA

`spatch` aplica un patch y devuelve un **diff**. Eso responde "¿qué cambia si
modifico esto?", que es `source.semantic_search`, ya integrado. No responde
"¿qué estructura tiene ESTE fichero?", porque un patch que no aplica produce
`No rules apply` con **rc 255** — indistinguible de un patch mal escrito
(medido y ya registrado en el registry de `coccinelle`).

El caso `ausente` muestra el problema de simetría: para el AST, 0
coincidencias es una **medida** («miré, no hay»). Para `spatch`, es un
`rc 255` **ambiguo** que el adapter tiene que clasificar aparte.

## LO QUE REALMENTE SE CONCLUYE

```text
SE CONCLUYE:
  - tree-sitter responde a la pregunta ESTRUCTURAL y spatch no.
    Medido: patron en comentario -> texto=1, AST=0.
  - Los dos MODOS DE FALLO son OPUESTOS:
      spatch  -> un diff, o un rc 255 ambiguo
      AST     -> un recuento, o "el lenguaje no encaja" (unsupported)
    Un `empty` de uno es DISCRIMINANTE para el otro.

NO SE CONCLUYE:
  - cual es MEJOR. Ninguno: responden preguntas distintas.
  - que tree-sitter sirva para un .c de 800 kLine. Solo se midio una
    cabecera de 42 kB. El resto es NOT_DETERMINED.
  - cobertura de semantica. Un AST de SINTAXIS no dice que hace el codigo.
    El techo sigue siendo semantic_hypothesis.
```

## POR QUÉ ESTO IMPORTA PARA EL TARGET

La pregunta «¿dónde escribe el driver este registro?» tiene tres respuestas
distintas, y confundirlas es el modo de error más caro del proyecto:

```text
  grep     ->  donde aparece la CADENA          (incluye comentarios)
  AST      ->  donde aparece el IDENTIFICADOR   (solo codigo)
  umr -r   ->  donde lo ESCRIBE EL HARDWARE    (solo el ASIC, y con root)
```

La tercera es la que responde «¿es un bug?». Las dos primeras solo acotan
dónde mirar. `source.ast_parse` se declara `structural_facts` y por
`scope: source` precisamente para que esa cadena no se pueda saltar.

## UN ERROR INTERMEDIO QUE MERECE REGISTRARSE

La primera versión de esta comparación afirma que el AST daría **menos** que
`grep` sobre `amdgpu.h`. Medido: daba **igual** (11 = 11). Parecía que el caso
sintético mentía.

El caso sintético no mentía. **El adapter estaba mal**: filtraba por
`child_count == 0`, creyendo que «hoja» significa «código», y en tree-sitter
un `#include`, un comentario y una cadena literal **son** hojas.

```text
  /* MARCA */ const char *s = "MARCA"; int MARCA = 1;
  texto                            = 3
  filtro por hoja                  = 3   <- MAL: cuenta el comentario y la cadena
  filtro por tipo                  = 1   <- lo que dice "donde escribe esto"
```

Interesante: un filtro intermedio (solo comentarios excluidos) hacía pasar el
caso sintético mientras `amdgpu.h` **seguía dando 11**, porque la línea 54 es
un `preproc_include`, no un comentario. Un solo test no bastaba.

## ESTADO

```text
CLAIM=spatch y tree-sitter son intercambiables
STATE=REFUTED (medido en 5 entradas + el codigo real)

CLAIM=source.ast_parse aporta algo que source.semantic_search no aporta
STATE=PROVEN (falso positivo de grep: caso comentario y caso cadena)

CLAIM=source.ast_parse cubre un .c grande
STATE=NOT_DETERMINED (medido 1 fichero de 42 kB; el driver son ~800 kLine)
```

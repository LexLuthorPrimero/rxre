# 013 — Filtro GFX8 por opcode: qué demuestra y dónde se rompe

> Iteración 2. Una pregunta discriminante.
> Fecha 2026-09-29 · corpus `RESEARCH/kernelbuild/linux-7.1.3` (7 PATCHLEVEL 1 SUBLEVEL 3)
> Clasificación: `READ_ONLY/EVIDENCE`
>
> **Línea canónica de driver**: `04-IMPLEMENTACION/rx550-driver/`
> **Sólo lectura**: `07-DRIVER/driver/` — no tocada en esta iteración.

---

## 1. La pregunta y la respuesta

> ¿Puede construirse un filtro reproducible de instrucciones/opcodes GFX8 a partir
> de las definiciones reales de `gfx_8_0_enum.h`?

```
FILTER_BY_PREFIX      = REFUTED
FILTER_WITH_TABLE_ID  = NOT_DETERMINED
LLVM_MC_AS_CORRELATOR = PROVEN, y es la ÚNICA correlación disponible
CORPUS_AS_AUTHORITY   = REFUTED
```

El filtro **no se puede construir** con lo que hay, y la razón es precisa y
medible: el espacio de nombres `SQ_S_` de `gfx_8_0_enum.h` **concatena cinco
tablas de opcode distintas**, todas empezadas en cero. Un filtro por prefijo
produce correlaciones falsas, y eso es demostrable, no una opinión.

---

## 2. Lo primero: una query mía que estaba rota

Antes de concluir nada comprobé el resultado, porque un filtro que empieza
devolviendo cero también puede significar que la query está mal.

Mi primera extracción buscaba el separador `__` en el enum y devolvió **0
bloques**. Interpretarlo como "no hay tablas de instrucción" habría sido
exactamente el error que la disciplina del proyecto prohíbe: afirmar la ausencia
de un objeto sin haberlo comprobado.

La forma real de los defines es `BLOQUE NOMBRE VALOR`, sin `__`:

```c
#define SQ_DS_WRAP_RTN_B32    0x34
#define SQ_S_MOV_B32          0x0
```

Corregida la query: 1391 defines con prefijo `SQ_`, y son tablas de opcode de
instrucción. El "vacío" era mío.

---

## 3. La ambigüedad, medida

`SQ_S_` tiene 77 valores distintos. **44 de esos 77 valores están asignados a más
de un nombre**, y los nombres se agrupan en cinco tablas que empiezan en 0:

| tabla | entradas | rango de valores | ejemplos |
|---|---|---|---|
| SOP2 | 4 | `0x01`..`0x1d` | `MOV_B64`, `CMOV_B64`, `ENDPGM`, `SETPC_B64` |
| SOPK | 2 | `0x00`..`0x01` | `MOVK_I32`, `CMOVK_I32` |
| SMEM | 8 | `0x00`..`0x12` | `LOAD_DWORD`, `LOAD_DWORDX2`, `STORE_DWORD` |
| SOPC | 15 | `0x00`..`0x13` | `CMP_EQ_I32`, `BRANCH` |
| SOP1 | 6 | `0x00`..`0x05` | `ADD_U32`, `SUB_U32`, `NOT_B32` |

La colisión es literal:

```
valor 0x00 -> SQ_S_MOV_B32, SQ_S_MOVK_I32, SQ_S_LOAD_DWORD,
              SQ_S_NOP, SQ_S_CMP_EQ_I32, SQ_S_ADD_U32
valor 0x01 -> SQ_S_MOV_B64, SQ_S_CMOVK_I32, SQ_S_LOAD_DWORDX2,
              SQ_S_ENDPGM, SQ_S_CMP_LG_I32, SQ_S_SUB_U32
```

Seis formatos de instrucción distintos comparten el mismo valor. Un opcode no es
un par `(valor, nombre)` en este header: es un par `(valor, tabla, nombre)`, y la
tabla es justamente lo que el header **no registra**.

`SQ_DS_*` tiene el mismo defecto (`SQ_DS_WRITE_B32 = 0xd` convive con
`SQ_DS_WRAP_RTN_B32 = 0x34` en rangos que no se solapan, pero ninguna marca dice
qué tabla es cada bloque).

Y `SQ_V_*` es de otra naturaleza: no da opcode por instrucción, da la base y el
tamaño de las tablas de microcode.

```c
#define SQ_V_OPC_OFFSET   0x0
#define SQ_V_OP2_OFFSET   0x100
#define SQ_V_OP1_OFFSET   0x140
#define SQ_V_OP1_COUNT    0x80
#define SQ_V_OP2_COUNT    0x40
```

Eso dice dónde empieza cada tabla, no qué opcode significa qué instrucción.

---

## 4. La correlación que sí se puede medir

Para instruccion scalar, el opcode vive en los bits **[22:16]** del dword. Eso se
puede comprobar, no suponer: se ensambla y se mira.

| instrucción | encoding de `llvm-mc` | bits[22:16] | corpus | CORRELATION |
|---|---|---|---|---|
| `s_endpgm` | `0xBF810000` | `0x01` | `SQ_S_ENDPGM = 0x1` | **OK** |
| `s_sleep 1` | `0xBF8E0001` | `0x0E` | `SQ_S_SLEEP = 0xe` | **OK** |
| `ds_write_b32 v0,v1` | `0xD8340000` | `0x34` | `SQ_DS_WRAP_RTN_B32 = 0x34` | **RUIDO** |
| `s_mov_b64 s[0:1],0` | `0xBE800480` | `0x00` | `SQ_S_MOV_B64 = 0x1` | **FALLA** |

Tres filas correlacionan y una que falla. `s_mov_b64` es la prueba de que la
correlación por valor no es válida en general: su opcode real no está en
bits[22:16] porque `s_mov_b64` no es un SOP2 con ese campo, y el valor `0x1` del
header pertenece a otra tabla.

`ds_write_b32` ↔ `SQ_DS_WRAP_RTN_B32` es el caso peligroso: **los números
coinciden pero son cosas distintas**. Un filtro que sólo comparase valores
aceptaría un `ds_wrap_rtn_b32` como si fuera `ds_write_b32`. Es un falso positivo
que se ve sólo al mirar los nombres.

---

## 5. El resultado del filtro

```
GFX8_DEFINITION      el header define 5 tablas superpuestas bajo un prefijo
LLVM_MC_ASSEMBLABLE  sí, para todo lo que se le pasó, en las 3 CPU probadas
ENCODING_OBTAINED    sí, reproducible y determinista
CORRELATION_STATUS  value <-> encoding  NO CONFIABLE sobre el prefijo solo
                     value <-> encoding  requiere la identidad de la tabla
                     identidad de la tabla NOT_DETERMINED con este corpus
```

Clasificación por instrucción, con los estados que permite el encargo:

| estado | significado aquí |
|---|---|
| `PROVEN` | el encoding se obtiene y es determinista |
| `STATICALLY_SUPPORTED` | el valor existe en `gfx_8_0_enum.h` bajo un prefijo |
| `NOT_DETERMINED` | a qué tabla del opcode pertenece el valor |
| `NOT_AVAILABLE` | el documento ISA GFX8, que sigue sin estar en el corpus |
| `NOT_FOUND` | ninguna entrada con ese nombre; **no** implica que la instrucción no exista |
| `AMBIGUOUS` | el valor está en más de una tabla: 44 de 77 valores `SQ_S_*` |

---

## 6. El límite epistemológico, enunciado

```
gfx_8_0_enum.h  +  llvm-mc  ≠  filtro GFX8
```

Lo que esta combinación **sí** permite:

1. Ensamblar una instrucción y obtener su encoding, de forma reproducible.
2. Comprobar que ese valor aparece en algún sitio de las tablas GFX8.
3. Detectar instrucciones que `llvm-mc` no conoce.

Lo que **no** permite:

1. Decidir si una instrucción existe en Polaris12. El triple no la restringe y el
   corpus no tiene la identidad de tabla.
2. Decidir la semántica de un campo. Eso es el documento ISA, `NOT_AVAILABLE`.
3. Separar dos instrucciones que comparten valor en tablas distintas.
4. Cualquier afirmación sobre lo que el CP ejecuta. `llvm-mc` es un generador de
   bytes, no una autoridad semántica, y su aceptación de sintaxis antigua bajo
   targets modernos es exactamente el contraejemplo.

El contraejemplo que motivó la iteración queda así:

```
v_cmp_gt_f32_e64 vcc,   v0, v1   -> aceptado en gfx803, gfx900 y gfx1103
v_cmp_gt_f32_e64 s[0:1], v0, v1   -> aceptado en gfx803, gfx900 y gfx1103

LLVM_TARGET_FILTER = NOT_SUFFICIENT      (PROVEN por contraejemplo)
```

**Qué demuestra**: que `llvm-mc` no implementa el gate de generación.
**Qué NO demuestra**: que el conjunto de instrucciones de GFX8 esté mal definido,
ni que `vcc` sea inválido en gfx803. Sólo que esta herramienta no lo sabe.

---

## 7. Alternativa disponible y su coste

El filtro que sí discriminaría no es el prefijo, sino una tabla explícita
`instrucción → opcode → tabla → posición de campo`, construida una vez y usada
como puerta. El coste real es que esa tabla es **conocimiento externo**: no está en
el corpus, y sin ella el filtro no tiene fuente.

| opción | fuente | estado |
|---|---|---|
| prefijo `SQ_S_` del corpus | local | `REFUTADO`, correlaciones falsas |
| triple de `llvm-mc` | herramienta | `REFUTADO`, no restringe |
| tabla explícita instrucción→opcode | **externa** | `NOT_AVAILABLE` en el corpus |

La tercera es la única que funcionaría, y es `EXTERNAL`. Se registra como tal y no
se eleva a `PROVEN`.

---

## 8. Lo que queda, con nombre

```
FALTA_1  identidad de tabla por cada entrada de gfx_8_0_enum.h
         → no recuperable de este corpus. El header concatena tablas sin
           marcarlas. ORIGEN: el fichero que genera esos headers.

FALTA_2  tabla instrucción → opcode GFX8
         → EXTERNAL. Documento ISA, o la tabla de otro proyecto.
         → RUNTIME_REQUIRED: no. Se puede escribir a mano desde la
           especificación, pero eso es traer evidencia externa.

FALTA_3  POLARIS12 → nombre de target LLVM
         → NOT_DETERMINED localmente. No afecta al filtro: el filtro, si
           existiera, se apoyaría en la tabla de GFX8, no en el nombre del target.
```

Ninguno de los tres bloquea la respuesta de esta iteración. Los tres son
predecesores del **siguiente** discriminante, que es la elección del programa GCN8
mínimo con efecto observable.

---

## 9. Lo que esta iteración cambió

1. La hipótesis del discriminante anterior —"extraer opcodes de
   `gfx_8_0_enum.h` y confrontarlos con `llvm-mc`"— **queda refutada** con
   medición, no con opinión. Se registraba como el siguiente paso; era incorrecto
   y habría producido un filtro con falsos positivos silenciosos.

2. Se añade una distinción que faltaba entre **registro** y **instrucción**.
   `gfx_8_0_sh_mask.h` define campos de registro (`CB_BLEND_RED__BLEND_RED_MASK`);
   `gfx_8_0_enum.h` define, además, opcodes de instrucción. Son cosas distintas y
   no deben mezclarse en una tabla semántica.

3. Se acota `isa GFX8 NOT_AVAILABLE`: el documento ISA sigue ausente, pero el
   corpus **sí** tiene la numeración de opcode GFX8. Lo que falta es la
   **identidad de tabla**, que es un dato pequeño y concreto, no una ausencia
   documental.

## 10. Deuda con la iteración 1

La iteración 1 afirmó, a partir de `SQ_S_ENDPGM = 0x1`, que el corpus corroboraba
la codificación `0xBF810000` "visto desde el otro lado". La correlación existe
para ese caso, pero **generalizar el método a otras instrucciones es incorrecto**,
como muestra `s_mov_b64`. La afirmación queda acotada a lo que sostiene.

## 11. Estado

```
FILES_CREATED   08-ARQUITECTURA/designs/013-filtro-gfx8-por-opcode.md
FILES_MODIFIED  ninguno
DRIVER_TOUCHED  ninguno
TESTS           verificación por ejecución y código de retorno; sin suite
RUNTIME         NOT_RUN
NEXT            el programa GCN8 mínimo con efecto observable, que necesita
                decidir la tabla instrucción→opcode: RUNTIME_REQUIRED para
                verificarlo, pero escribible si se acepta tabla EXTERNAL
```

---

# CORRECCIÓN (apéndice, 967) — la etiqueta AMBIGUOUS no se sostiene

Este apéndice **no borra** lo que está arriba. Lo corrige y explica por qué estaba mal.

## Qué dice el diseño, y qué se ha medido

La sección 5 clasifica `AMBIGUOUS` los 44 de 77 valores `SQ_S_*` que aparecen en más de una tabla, y la
sección 6 lo trata como un límite epistemológico. Medido con `gfx8_opcode.py`:

```
216 entradas SQ_S_*   77 valores distintos   44 con más de un nombre
```

El recuento es correcto. La **clasificación** no.

## Por qué `AMBIGUOUS` es la palabra equivocada

El patrón que produce el 44 no es un valor con dos nombres, son **seis tablas completas** superpuestas:

```
0x00 -> S_MOV_B32, S_MOVK_I32, S_LOAD_DWORD, S_NOP, S_CMP_EQ_I32, S_ADD_U32
0x01 -> S_MOV_B64, S_CMOVK_I32, S_LOAD_DWORDX2, S_ENDPGM, S_CMP_LG_I32, S_SUB_U32
```

Cada familia empieza en cero e incrementa. La pregunta «¿qué es el opcode 0x00?» está **mal formada**:
le falta la dimensión «familia». Una vez que se dice de qué familia, el valor es unívoco.

## La colisión que sí existe, y por qué no es ambigüedad

Medida sobre dos reglas de agrupación, porque **la familia es una convención de quien mide, no algo que
esté en la cabecera**:

```
prefijo2   63 familias   1 colisión:  S 0x10 -> S_SENDMSG, S_SETVSKIP
completo   80 familias   0 colisiones
```

La colisión nace en la familia `S`, que `prefijo2` llena porque a un nombre de dos segmentos no le queda
segundo token. `S_SENDMSG` y `S_SETVSKIP` son tablas distintas. Bajo `completo` cada nombre de dos
segmentos es su propia familia y desaparece.

```
v1 de este documento   AMBIGUOUS                     -> REFUTED
v2                     no se observa ambigüedad con  -> CORROBORATED
                       estas dos reglas
                       PROVEN_ABSENT de ambigüedad   -> NO se sostiene
```

## Lo que este apéndice corrige del proceso, no solo del resultado

La primera versión de la herramienta **no podía detectar una colisión**, y por eso informaba «0
colisiones internas» con cualquier entrada. Guardaba las familias como un dict indexado por valor, en
el que dos nombres con el mismo valor no son representables: el segundo sobrescribe al primero. La
«medición» era una tautología.

También imprimía `216 valores distintos` cuando hay **77**, porque contaba tuplas `(nombre, valor)` en
lugar de valores.

Ninguno de los dos errores se vio al ejecutar la herramienta: se vieron al ponerla a prueba contra
datos que no podían ser ciertos. Detalle en `gfx8_opcode.py` y en el hallazgo 967.

## Qué queda igual

- `NOT_AVAILABLE` se mantiene, y ahora con forma precisa: no falta «el documento ISA GFX8», falta que
  **4 de las 5 tablas de opcode no están en el corpus**. Solo existe `gfx_8_0_enum.h`.
- `RUNTIME_REQUIRED` **no** se cierra. El programa mínimo sigue necesitando runtime para tener efecto
  observable. Lo que se cierra es la **decisión de la tabla**, que pasa de elección a dato, que es
  exactamente la vía `EXTERNAL` que este diseño señalaba.
- `ENCODING_OBTAINED` y `STATICALLY_SUPPORTED` no se tocan: nada aquí los contradice.

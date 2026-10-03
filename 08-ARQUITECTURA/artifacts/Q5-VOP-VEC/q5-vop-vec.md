# Q5-VOP-VEC — el tercer universo de opcode GFX8, y por qué es el que importa

```
AUTORIA=AGENT-20 · WORK_CLASS=READ_ONLY/EVIDENCE · WRITE_EXECUTION=6 ficheros nuevos
RUNTIME=NOT_RUN · GPU=INTACTA · SIN_SUDO · SIN_COMMITS
NODE_ID=Q5-VOP-VEC
```

**Pregunta única.** Los otros dos nodos Q5 midieron el prefijo `SQ_S_*` (216) y la
memoria vectorial (353). El tercer universo, `SQ_V*` (425), no lo midió ninguno. ¿Es
medible, y qué obtiene un driver RX550 que lo aplique?

**Veredicto: `RESOLVED_WITH_GENERATION_DIFFERENCE`.**

Dos resultados, y el segundo es el que la misión pedía:

1. El universo vector **es medible** desde dentro del root canónico, sin GPU y sin
   abrir ningún PDF nuevo. Cobertura sobre VOPC: **6 de 198** coinciden con la regla
   del ISA GCN3.
2. Las 192 restantes están codificadas **con otra distribución de bloques**, y
   **144 opcode tienen el mismo número en ambas fuentes y designan instrucciones
   distintas**. Heredar la tabla VOPC del GCN3 para gfx803 no falla de forma visible:
   compara lo que no es.

---

## 0. Verificación de inputs, antes de interpretar

```
INPUT cap12.txt      sha256 877b92024e43a8d7d74863ffe6873d293e23a6edf961f77dcd274b95920c8df8
INPUT gfx_8_0_enum.h sha256 fa6b8ff974fccdd54aa0e1b6a6430508a558fd263ead90eaf70bef262e4d5d63
```

Ambos dentro del root canónico. **No se abre `vega-isa.pdf`**, no se reextrae el
capítulo 12, no se toca la GPU. Se reutiliza el `cap12.txt` que Q5-ISA-CAP12 ya
extrajo y validó, y el `cap12-opcodes-all.tsv` que ya Codyó. Los hashes coinciden con
los fijados por Q5, así que **no hay `DRIFT_DETECTED`**.

`cap12.txt` tiene 179 páginas lógicas y el capítulo medido por Q5 son 178. La
diferencia es la última, vacía tras el separador de formulario; no se usa.

## 1. El universo, y por qué cuesta definirlo

`grep -c '^#define SQ_V'` da **425**, no 421. La diferencia son 4 entradas que no
casan con el prefijo `SQ_V_`: `SQ_VCC_ALL/HI/LO` y `SQ_VGPR0`.

```
425 total
 18 no son opcodes:  7 _COUNT, 7 _OFFSET, 4 SQ_VCC*/SQ_VGPR0
407 candidatos a opcode
```

**Regla de exclusión, con control negativo ejecutado:** la regla descarta nombres que
acaban en `_COUNT`/`_OFFSET` o que empiezan por `SQ_VCC`/`SQ_VGPR`. El control
negativo —¿traga algún opcode real?— devuelve **vacío**: ningún nombre que termine en
un tipo escalar (`_F32`, `_U32`, …) es descartado. Regla registrada porque
`LIMITACION_5` de Q5-ISA-CAP12 ya advirtió de que un universo mal definido hace que
la medición no pueda fallar.

## 2. El tsv validado no cubre VOPC, y el motivo es de forma, no de contenido

`cap12-opcodes-all.tsv` (el instrumento de Q5-ISA-CAP12) contiene 209 filas `V_*`:

```
VOP3a 76 · VOP1 76 · VOP2 52 · VINTRP 3 · VOP3b 2      VOPC  0
```

Cero VOPC. La causa está en cómo el ISA documenta VOPC: **las familias escalares y
VOP1/VOP2/VOP3a salen en líneas `Microcode <FORMATO> Opcode N`, pero VOPC sale en las
Tablas 12.1, 12.2 y 12.3**, que el extractor de líneas no captura. Es el mismo
split que Q5-ISA-CAP12 §2(a) ya había detectado para las tablas de memoria, aplicado
ahora al lado vector. Por eso **una unión por nombre no puede funcionar aquí**, y por
eso este nodo no une por nombre.

## 3. El método: predecir, no buscar

En vez de comparar nombres, se extrae la **regla** del ISA y se predice cada valor
del header. Lo que sobra tras predecirlo todo es lo que el header tiene y el ISA no
nombra.

Las tres tablas, transcritas literalmente de `cap12.txt` (impresas 12-121, 12-122,
12-123), con sus operaciones:

```
OP16  F=0 LT=1 EQ=2 LE=3 GT=4 LG=5 GE=6 O=7 U=8 NGE=9 NLG=10 NGT=11
      NLE=12 NEQ=13 NLT=14 TRU=15                       (Tabla 12.1, 12-121)
OP8   F=0 LT=1 EQ=2 LE=3 GT=4 LG=5 GE=6 TRU=7            (Tabla 12.2, 12-122)
```

Regla resultante: 8 familias flotantes × 16 operaciones, 8 familias enteras × 8
operaciones, 6 CLASS. **198 reglas**, que es exactamente el tamaño del universo del
header.

`SELFTEST_ANCHORS_ISA PASS` — las seis cadenas ancla (`V_CMP_{OP16}_F32`,
`V_CMPX_{OP16}_F32`, `V_CMP_{OP8}_I32`, `V_CMPX_{OP8}_U64`, `V_CMP_CLASS_F32`,
`V_CMPX_CLASS_F16`) existen en el texto. **La regla se sostiene sobre el documento, no
sobre mi memoria de la arquitectura.**

```
PREDICTED_AND_MATCHED      6
PREDICTED_BUT_MISMATCH     0
HEADER_NOT_IN_ISA_RULE   192
CHECK 6 + 0 + 192 = 198 = universo   OK
```

## 4. Las 6 que coinciden son la familia CLASS, y solo ella

```
V_CMP_CLASS_F32=0x10   V_CMPX_CLASS_F32=0x11
V_CMP_CLASS_F64=0x12   V_CMPX_CLASS_F64=0x13
V_CMP_CLASS_F16=0x14   V_CMPX_CLASS_F16=0x15
```

Es la única familia VOPC donde el ISA GCN3 y el header GFX8 coinciden en nombre y
número. Las 192 restantes difieren, y **cero** difieren en valor having el mismo
nombre: no hubo ni un `DIFIERE`, sino un desajuste estructural.

## 5. El hallazgo: 144 opcode iguales con instrucción distinta

Nombres literales, tal como los emite el instrumento, para que sean grepeables en
`collisions.tsv`. La regla concatena familia+operación+tipo sin separador
(`CMPSX`+`F`+`F32` → `V_CMPSXF_F32`); el ISA los escribe con llaves y guion
(`V_CMPSX_{OP16}_F32`). Es el mismo par, no dos.

```
opcode   ISA GCN3 (Tabla 12.1/12.2)   header GFX8 (gfx_8_0_enum.h)
0x20     V_CMPF_F64                    V_CMPF_F16
0x50     V_CMPSXF_F32                  V_CMPX_F_F32
0x70     V_CMPSXF_F64                  V_CMPX_F_F64
0xA0     V_CMPF_I64                    V_CMPF_I16
0xC0     V_CMPF_U32                    V_CMPF_I32
0xF0     V_CMPXF_U64                   V_CMPX_F_I64
```

```
MISMO_NUMERO_MISMA_INS     6
MISMO_NUMERO_OTRA_INS   144      <-- el peligro
SIN_HOMONIMO_EN_ISA      48
                        ---
                        198
```

Las dos distribuciones de bloques, reconstruidas empíricamente del header y leídas
de las tablas del ISA:

| | ISA GCN3 | header GFX8 |
|---|---|---|
| flotante F32 | `CMP` 0x00 · `CMPX` 0x10 | `CMP` 0x40 · `CMPX` 0x50 |
| flotante F64 | `CMP` 0x20 · `CMPX` 0x30 | `CMP` 0x60 · `CMPX` 0x70 |
| flotante F16 | **no existe** | `CMP` 0x20 · `CMPX` 0x30 |
| `CMPS`/`CMPSX` | 0x40–0x7F, cuatro familias | **no existen** |
| enteros | 32/64 bits, con y sin `X`, U separado por 0x10 | 16/32/64 bits, U intercalado a 0x08 |

Tres diferencias estructurales, no de valores sueltos:

1. **`CMPS`/`CMPSX` desaparecen.** El GCN3 devote 0x40–0x7F a las variantes que
   señalizan ante cualquier NaN. El header GFX8 no las materializa: ese rango es
   `CMP`/`CMPX` de F32 y F64. La diferencia no es de nombre, es de qué NaN dispara
   la excepción.
2. **Aparecen F16 e I16/U16**, que el ISA GCN3 no documenta en VOPC.
3. **El orden de los bloques enteros cambia**: el GCN3 separa con y sin `X` por
   0x10 (`CMP_I32` 0x80, `CMPX_I32` 0x90, `CMP_I64` 0xA0…); el header intercala
   firmado y no firmado a 0x08 (`CMP_I16` 0xA0, `CMP_U16` 0xA8, `CMPX_I16` 0xB0…).

## 6. Por qué esto importa al driver, y hasta dónde llega

El modo de fallo que produce el punto 5 es el peor de los tres posibles: **no es un
error de compilación, ni un aviso, ni un cuelgue**. Es un kernel que emite `0xA0`
esperando una comparación de 64 bits y el hardware ejecuta una comparación de 16
bits. Los datos salen mal y nada lo delata. Un predicado equivocado en una
comparación de límites cambia el resultado de un filtro, de un depth-test o de un
refinamiento de flotación sin producir ni un error.

**Cadena causal, reconstruida:**

```
DRIVER  emite un opcode VOPC copiado de la tabla del GCN3
   ↓
SHADER CODE  el mismo número significa otra comparación
   ↓
ISA  144 de 198 tienen número compartido y semántica distinta
   ↓
EJECUCIÓN  la unidad de predicado resuelve la instrucción que el número designa
   ↓
EFECTO  resultado numéricamente incorrecto, sin excepción ni diagnóstico
```

Y el uso que la misión pedía nombra, explícitamente: **`CMPX` escribe además `EXEC`**
(las tres tablas lo dicen: *"Also write EXEC"*). Es decir, el mismo error numérico
que contamina una comparación **contamina la máscara de wavefronts**, que es la
misma `EXEC` que `LEARNED-GCN3-ISA.md` §3 identificó como la primera pieza de
concurrencia real del proyecto. La avería de la tabla VOPC no se queda en el predicado:
llega a la sincronización.

## 7. Qué NO se puede concluir

1. **No se dice cuál de las dos fuentes manda.** No hay medición contra esta placa.
   El header es evidencia sobre una implementación (`LIMITACION_3`); el ISA GCN3 es
   documentación de proveedor de **otra generación**. Registrado como
   `GENERATION_DIFFERENCE`, no como error de ninguna de las dos. gfx803 es GCN4; el
   documento disponible es GCN3. Cuál gobierna es `NOT_DETERMINED`, y es la misma
   pregunta que `gfx8-execution-discriminator-and-isa-boundary.md` ya dejó abierta.
2. **La reordenación es consistente con una adición de 16 bits**, que es un cambio
   de GCN4/Vega conocido. **Consistente no es medido**: no he medido el silicio y no
   lo afirmo.
3. **Solo VOPC.** VOP1/VOP2/VOP3a/VOP3b quedan fuera: el join por nombre da 204
   `COINCIDE` sobre 207 filas, pero los 83 VOP3a sin nombre en el tsv impiden
   afirmar cobertura. `PARTIAL`.
4. **No se ha tocado la GPU.** Nada de esto está validado en ejecución.

## 8. Estado

```
WORK_ID            = Q5-VOP-VEC
STATE              = RESOLVED_WITH_GENERATION_DIFFERENCE
UNIVERSO           = 425 SQ_V* -> 407 candidatos (18 no-opcode, control negativo vacio)
COBERTURA_VOPC     = 6/198 coinciden con la regla del ISA GCN3 (solo familia CLASS)
COLISIONES         = 144 mismo numero / instruccion distinta · 48 sin homonimo
RESIDUAL           = VOP1/VOP2/VOP3a/VOP3b sin medir (83 VOP3a sin nombre en el tsv)
INPUT_HASHES       = cap12.txt 877b92024e43a8d7… · gfx_8_0_enum.h fa6b8ff974fccdd54…
OUTPUT_HASHES       = coverage-vop.tsv    93055d35fd7e2d71…
                     vopc-prediction.tsv 4f98d909fcb804d8…
                     collisions.tsv      1360f4760c06b7ef…
INSTRUMENTOS        = measure_vop_universe.py 5a47db1c09f0844a…
                     predict_vopc.py         dda6109555fae3300…
SELFTEST           = PASS (anclas ISA presentes; 6+0+192 = 198)
GPU_TOCADA         = NO    RUNTIME=NOT_RUN    SUDO=NO    COMMITS=NINGUNO
```

**Candidate siguiente, con discriminante, no ejecutado:** comparar el bloque entero
`SQ_DS_`/`SQ_BUFFER_`/`SQ_IMAGE_`/`SQ_FLAT_` con las Tablas 12.7–12.13 por el mismo
método de predicción, no por nombre. `Q5-MEM-TABLES` midió **cobertura** por nombre y
dio 45 discrepancias, concentradas en `FLAT` y `MIMG`. Si allí también hay
reordenación de bloques y no solo valores desplazados, el diagnóstico pasa de "VOPC
es especial" a "ninguna tabla del GCN3 es trasladable a gfx803 sin predicción", que
es la regla de trabajo que el driver necesita.
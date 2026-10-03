# 967 — Un instrumento que no puede fallar: la «ambigüedad de 44 opcodes» del diseño 013 era el detector, no el hardware

```
CLASSIFICATION=DOCUMENTATION · TRACK=STATIC
CORPUS=RESEARCH/working/linux-7.1.3 · HARDWARE_SCOPE=HOST-C/RX550/0000:01:00.0
WORK_CLASS=READ_ONLY/EVIDENCE · WRITE_EXECUTION=NONE · MODIFICATIONS=4 · RUNTIME=NOT_RUN · GPU INTACTA
```

Estado: `VALIDADO`. `gfx8_opcode.py` con auto-test y 6 controles negativos; cross-check independiente con awk/sort/uniq.
Instrumentos: `gfx8_opcode.py` (nuevo), `run_all.py`, `contract_filter.py`.
Alcance: `gfx_8_0_enum.h` (216 entradas `SQ_S_*`), `08-ARQUITECTURA/designs/013-filtro-gfx8-por-opcode.md`.

## La pregunta

`DRIVER-MISSION-STATE.md` fija `NEXT_REQUIRED_WORK = Q5 GCN8_OPCODE_FILTER`, y el diseño `013` lo
describe así: 44 de 77 valores `SQ_S_*` están en más de una tabla, y los clasifica `AMBIGUOUS`.
Eso ponía el programa GCN8 mínimo en `DEFERRED_BY_MISSING_OBSERVABILITY`, porque `013` dice que hace
falta «decidir la tabla instrucción→opcode: `RUNTIME_REQUIRED` para verificarlo, pero escribible si se
acepta tabla `EXTERNAL`».

La pregunta no es «¿qué opcode tiene `S_LOAD_DWORD`?». Es: **¿la ambigüedad está en el hardware o en el
instrumento que la midió?**

## Lo que el diseño afirma, y lo que hay

Medido sobre `gfx_8_0_enum.h`, que es la **única** cabecera de opcode GFX8 del corpus:

```
216 entradas  SQ_S_*
 77 valores distintos
 44 valores con más de un nombre
```

Y el patrón que produce el 44:

```
0x00 -> S_MOV_B32, S_MOVK_I32, S_LOAD_DWORD, S_NOP, S_CMP_EQ_I32, S_ADD_U32
0x01 -> S_MOV_B64, S_CMOVK_I32, S_LOAD_DWORDX2, S_ENDPGM, S_CMP_LG_I32, S_SUB_U32
```

Eso no es un valor con dos nombres: son **seis tablas completas, cada una empezando en cero e
incrementando**. `S_ADD_U32=0, S_SUB_U32=1, S_ADD_I32=2` es una tabla; `S_MOV_B32=0, S_MOV_B64=1,
S_CMOV_B32=2` es otra. La pregunta «¿qué es el opcode 0x00?» está **mal formada**: le falta la
dimensión «familia». Esto **corrobora** la lectura de `013` en su parte descriptiva.

## El defecto: un detector que no podía fallar

Mi primera versión de la herramienta construía las familias como un **dict indexado por valor**:

```python
fam[clave][v] = n          # v1
```

Con esa forma, **dos nombres de la misma familia con el mismo valor no son representables**: el segundo
sobrescribe al primero. Y el detector de invertibilidad recorría ese mismo dict con `d.items()`, donde
cada valor aparece **una vez por construcción**.

Consecuencia: `0 colisiones internas` se imprimía **siempre, con cualquier entrada**. No era una
medición. Era una tautología, y el instrumento no podía fallar.

Es exactamente el fallo que la sección de validación de este mismo proyecto («un self-test debe
afirmar el dato extraído, no la estructura del extractor») intenta evitar, caído en el sitio
contrario: no probé la estructura, probé que el extractor no perdiera nombres — y la estructura filtraba
justo la colisión que yo creía medir.

v2 guarda **pares `(nombre, valor)`**, que sí admiten duplicados, y el detector puede fallar por fin.

## v2 falla, y lo que encuentra

Al poder fallar, falla:

```
COLISIONES INTERNAS, y son SENSIBLES A LA REGLA:
    prefijo2   63 familias  1 colisiones
        S 0x10 -> S_SENDMSG, S_SETVSKIP
    completo   80 familias  0 colisiones
```

**Mi afirmación anterior era falsa.** Y la clasificación correcta es esta:

La colisión vive en la familia `S`, que la regla `prefijo2` llena porque a un nombre de dos segmentos
(`S_NOP`, `S_SENDMSG`, `S_SETVSKIP`) no le queda segundo token que usar. `S_SENDMSG` y `S_SETVSKIP`
son **tablas distintas**, no dos nombres del mismo opcode. Bajo `completo` — un nombre de dos segmentos
es su propia familia, porque no se puede partir — la colisión desaparece.

La familia no está en la cabecera: **es una convención mía**. Por eso la colisión depende de la regla, y
lo correcto es medir su sensibilidad en vez de declarar que el opcode es ambiguo.

```
ESTADO que se sostiene:   con estas DOS reglas no se observa ambigüedad de opcode
ESTADO que NO se sostiene: PROVEN_ABSENT de ambigüedad
```

## Segundo defecto: contar tuplas como valores

Al pasar a pares, la v2 imprimió `216 valores distintos` cuando el valor real es **77**. La causa: al
iterar una lista de pares, `{v for ...}` recogía **tuplas `(nombre, valor)`**, no valores. 216 es el
número de tuplas, y coincide sospechosamente con el número de nombres.

Con el contador arreglado y contrastado de nuevo por awk: **216 nombres, 77 valores**.

## El cross-check que falló, y de quién era el defecto

Recuento independiente con `awk/sort/uniq`, sin Python:

```
nombres:  152      valores distintos:  53
```

Difiere de 216/77. La diferencia son **64 entradas con hexadecimal en minúscula** (`0xa`…`0xf`):

```
#define SQ_S_BCNT0_I32_B32   0xa
#define SQ_S_BCNT0_I32_B64   0xb
...
```

que el `grep` del cross-check (`[0-9A-F]`) no aceptaba. **El defecto estaba en el cross-check, no en la
herramienta.** Registrar esto porque un cross-check que discrepa obliga a decidir *cuál de los dos
instrumentos miente*, y esa decisión es parte del resultado, no un trámite.

## Validación de la herramienta

```
--self-test   extracción; conservación en LAS DOS direcciones (nada perdido,
              nada inventado); invertibilidad bajo la regla que se afirma;
              y ejecución real del camino de impresión con comprobación de su
              contrato de salida (que es donde falló la primera versión)
--negativo    6 controles con datos sintéticos: el detector tiene que señalar
              colisiones, pérdidas e invenciones, y NO tiene que señalarlas
              donde no las hay; el caso real se ejecuta al final para que un
              filtro solo con negativos no acabe rechazando todo
```

El control negativo es el que encontró el defecto de la v1: los datos de prueba, construidos con la
misma forma defectuosa, hicieron que el detector fallara, y la causa era la **forma del dato**, no el
código.

## Lo que la tabla EXTERNAL ya puede sostener

`013` pedía una tabla instrucción→opcode para el programa mínimo. Con la regla `completo`, dentro de
cada familia el valor es unívoco:

```
S_LOAD   0x00=S_LOAD_DWORD  0x01=S_LOAD_DWORDX2  0x02=S_LOAD_DWORDX4  0x03=S_LOAD_DWORDX8  0x04=S_LOAD_DWORDX16
S_STORE  0x10=S_STORE_DWORD  0x11=S_STORE_DWORDX2  0x12=S_STORE_DWORDX4
S_CMP    0x00=S_CMP_EQ_I32   0x01=S_CMP_LG_I32   0x02=S_CMP_GT_I32   0x03=S_CMP_GE_I32   0x04=S_CMP_LT_I32   0x05=S_CMP_LE_I32
S_ADD    0x00=S_ADD_U32      0x02=S_ADD_I32
S_MOV    0x00=S_MOV_B32      0x01=S_MOV_B64      0x2F=S_MOV_REGRD_B32  0x31=S_MOV_FED_B32
```

## Lo que esto NO es

- **No es un ensamblador.** Solo conoce el campo de opcode dentro de la familia. Los operandos, los
  registros y el tipo son otra tabla, que no está aquí. «`0x00 = S_LOAD_DWORD`» no es un programa
  ensamblable: es la mitad izquierda del encoding.
- **No hay un `PROVEN_ABSENT` de ambigüedad.** Solo que con estas dos reglas de agrupación no se observa
  ninguna. Una tercera regla podría producir otra colisión; la unidad de análisis es la regla, no el
  opcode.
- **No cierra `RUNTIME_REQUIRED`.** El programa mínimo sigue necesitando runtime para tener efecto
  observable. Lo que se cierra es la *decisión de la tabla*, que pasa de ser una elección a ser un dato.

## Contradicción con `013`

`013` clasifica `AMBIGUOUS` los 44 valores. Medido: no son ambiguos **dentro de una familia**; son el
mismo valor en tablas distintas, y la pregunta del diseño no tenía la dimensión. La afirmación de
`013` queda `REFUTED` en su lectura de ambigüedad y `CORROBORATED` en su descripción del patrón. La
corrección se registra en el propio `013`, sin borrar su texto.

## Límites y lo que queda abierto

- **`NOT_AVAILABLE` confirmado con forma precisa**: no falta «el documento ISA GFX8». Falta que **4 de
  las 5 tablas de opcode no están en el corpus**. Solo existe `gfx_8_0_enum.h`. Los candidatos que
  aparecen (`sdma1_*_sh_mask.h`, `nbif_*`, `dcn_*`) son máscaras de bits de otros bloques, no tablas de
  opcode. El corpus no las tiene y aquí no se inventan.
- **La agrupación por familia sigue siendo una convención.** `completo` resuelve el caso observado, no
  demuestra que sea la taxonomía real de GCN8. Una regla derivada de la especificación ISA sería
  `PROVEN`; esta es `MODEL_CHOICE`.
- **Deuda con el aparato, no con este hallazgo.** `contract_exec.py` declara `WRITES_FILES=no` pero
  escribe `contract_exec.vigila.json` en `--fijar-vigila`: una declaración de contrato falsa en una
  herramienta mía, mientras el clasificador AST de la misma herramienta ve **1** escritura real (L306) y
  el validador externo ve **5**, la primera en L28, dentro del docstring. Al menos 4 de esas 5 son falsos
  positivos por mención en comentario. Queda registrado como `ERROR` abierto; el validador que las emite
  es de otra sesión y no se toca.
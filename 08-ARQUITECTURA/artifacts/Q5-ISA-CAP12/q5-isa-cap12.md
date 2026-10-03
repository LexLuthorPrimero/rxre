# Q5-ISA-CAP12 — cobertura real del capítulo 12 de la ISA GCN3 sobre las 216 entradas `SQ_S_*`

```
AUTORIA=sesion-missing · WORK_CLASS=READ_ONLY/EVIDENCE · WRITE_EXECUTION=1 fichero nuevo
RUNTIME=NOT_RUN · GPU=INTACTA · SIN_SUDO · SIN_COMMITS
NODE_ID=Q5-ISA-CAP12
```

**Pregunta única.** ¿El capítulo 12 de la ISA GCN3 de AMD contiene una correspondencia comprobable
opcode → valor, y cuál es su COBERTURA medida sobre las 216 entradas `SQ_S_*` del proyecto?

**Veredicto: `RESOLVED_WITH_RESIDUAL_UNIVERSE` — hipótesis H2 (COBERTURA PARCIAL).**

Resumen numérico: de las 216 entradas del universo, **185 tienen correspondencia opcode → valor
extraíble del capítulo 12** (85,6 %) y **31 no aparecen en absoluto en el capítulo**. De las 185,
**183 coinciden exactamente** con el valor del header y **2 difieren**. Ninguna entrada aparece como
título `Instruction` sin valor: las 31 ausentes no están en el texto, no están "a medio documentar".

---

## 0. Verificación de inputs (hecha ANTES de medir)

```
$ sha256sum /home/lucas/Descargas/RX550-INVESTIGACION/05-FUENTES-PDF/gcn3-isa.pdf
8e49a3767b337ec8aff451494c654c84c026720de8e3fa35177b0656f4bc2853  .../gcn3-isa.pdf
2752924 bytes

$ sha256sum .../RESEARCH/working/linux-7.1.3/drivers/gpu/drm/amd/include/asic_reg/gca/gfx_8_0_enum.h
fa6b8ff974fccdd54aa0e1b6a6430508a558fd263ead90eaf70bef262e4d5d63  .../gfx_8_0_enum.h
376576 bytes
```

Ambos hashes coinciden con los fijados. **No hubo `DRIFT_DETECTED`.** Procedo a medir.

**Universo usado — declaro cuál de las 4 copias:** uso
`RESEARCH/working/linux-7.1.3/drivers/gpu/drm/amd/include/asic_reg/gca/gfx_8_0_enum.h`.
Las 4 copias son byte-idénticas (`fa6b8ff9…`) y las 4 dan `grep -c '^#define SQ_S_'` = **216**:

```
$ find $R -name gfx_8_0_enum.h -print0 | xargs -0 sha256sum
fa6b8ff9…  RESEARCH/working/linux-7.1.3/…/gfx_8_0_enum.h
fa6b8ff9…  RESEARCH/baseline/linux-7.1.3/…/gfx_8_0_enum.h
fa6b8ff9…  RESEARCH/kernelbuild/linux-7.1.3/…/gfx_8_0_enum.h
fa6b8ff9…  rx550-upstream-7.2.8/linux-7.2.8/…/gfx_8_0_enum.h      <-- en RAIZ, no bajo RESEARCH/

$ grep -c '^#define SQ_S_' …            -> 216      (exit_status=0)
```

*Corrección al enunciado del nodo, sin efecto en el resultado:* la 4.ª copia **no** está bajo
`RESEARCH/` sino en la raíz del proyecto, `rx550-upstream-7.2.8/linux-7.2.8/…`. Existe y es
idéntica. La elección entre las 4 es inmaterial porque son el mismo byte a byte.

```
$ grep -c '^#define SQ_S_' $H ; echo exit=$?
216
exit=0
```

**Capacidad de herramienta verificada antes de extraer** (el PDF está cifrado con `copy:no`; había
que comprobar que eso no bloquea a poppler):

```
$ which pdftotext pdfinfo
/usr/bin/pdftotext
/usr/bin/pdfinfo
pdftotext version 26.01.0 …

$ pdfinfo …/gcn3-isa.pdf
Title:           R1200_ISA.book
Author:          admin
Creator:         FrameMaker 8.0
CreationDate:    Tue Aug  9 16:22:20 2016 -03
Pages:           348
Encrypted:       yes (print:yes copy:no change:no addNotes:no algorithm:AES)

$ pdftotext -f 1 -l 3 -layout …/gcn3-isa.pdf /tmp/opencode/q5/t.txt ; echo exit=$?
exit=0
```

`exit=0` y 7510 B de texto legible. **`copy:no` no bloqueó la extracción**; poppler extrae el texto
sin pedir contraseña. Esto es un hecho de la herramienta, no una autorización de copia.

El documento se identifica a sí mismo en la portada:

```
Reference Guide / Graphics Core Next Architecture, Generation 3 / August 2016 / Revision 1.1
```

---

## 1. Qué páginas son el capítulo 12 — y cómo se determinó (NO supuesto)

El PDF tiene 348 páginas. La numeración impresa (`12-1`, `12-2`, …) **no** coincide con el índice de
página del PDF, así que se midió el desplazamiento en vez de suponerlo. Dos pasos independientes.

### 1.1 El índice (TOC) nombra el capítulo y su extensión impresa

```
$ pdftotext -f 4 -l 16 -layout …/gcn3-isa.pdf /tmp/opencode/q5/toc.txt ; echo exit=$?
exit=0

$ grep -n 'Chapter 1[0-9]' /tmp/opencode/q5/toc.txt
89:Chapter 10     Data Share Operations
106:Chapter 11      Exporting Pixel Color and Vertex Shader Parameters
113:Chapter 12      Instruction Set
133:Chapter 13      Microcode Formats
```

Las 18 secciones de §12 con su primera página impresa:

```
Chapter 12      Instruction Set
  12.1    SOP2 Instructions ............ 12-1      12.10   VOP3 3 in, 1 out (VOP3a) ..... 12-124
  12.2    SOPK Instructions ........... 12-13     12.11   VOP3 (3 in, 2 out) (VOP3b) ... 12-157
  12.3    SOP1 Instructions ........... 12-19     12.12   VINTRP Instructions ........... 12-158
  12.4    SOPC Instructions ........... 12-32     12.13   LDS/GDS Instructions .......... 12-161
  12.5    SOPP Instructions ........... 12-38     12.14   MUBUF Instructions ............. 12-167
  12.6    SMEM Instructions ........... 12-47     12.15   MTBUF Instructions ............. 12-170
  12.7    VOP2 Instructions ........... 12-58     12.16   MIMG Instructions ............. 12-173
  12.8    VOP1 Instructions ........... 12-83     12.17   EXP Instructions ............... 12-177
  12.9    VOPC Instructions ........... 12-121    12.18   FLAT Instructions .............. 12-178
```

Rango impreso esperado: **12-1 … 12-178** (§12.18 empieza en 12-178 y §13 en 13-3).

### 1.2 El desplazamiento impreso → PDF se MEDIÓ, serefixió

```
$ pdftotext -layout …/gcn3-isa.pdf /tmp/opencode/q5/full.txt ; echo exit=$?
exit=0
# formfeeds: 348 -> logical pages: 348

# script: por cada página, buscar el marcador impreso /b12-(\d{1,3})\b/
printed 12-N range: 1 .. 178
count of distinct printed page markers: 178
missing in range: []
1   -> pdf pages [6, 107]        173 -> pdf pages [6, 10, 279]
2   -> pdf pages [108]          174 -> pdf pages [280]
…
178 -> pdf pages [6, 10, 284]
```

Los índices 6 y 10 son las páginas del TOC (contienen las cadenas `12-N`), no el capítulo. El
desplazamiento es constante y sin huecos:

```
impreso 12-1   -> PDF 107
impreso 12-178 -> PDF 284
offset = 106        (printed_12_N = pdf_page - 106)
distinct markers: 178   missing in range: []
```

### 1.3 Los extremos se leyeron, no se dedujeron

```
=== PDF PAGE 106 ===            11-4   Dependency Checking            <- fin de cap. 11
=== PDF PAGE 107 ===
                  Chapter 12
                  Instruction Set
                  This chapter lists, and provides descriptions for, all instructions in the GCN
                  Generation 3 environment. Instructions are grouped according to their format.
                  …
                  12.1 SOP2 Instructions
                  Instruction    S_ABSDIFF_I32
                  Microcode SOP2 Opcode 42 (0x2A)
=== PDF PAGE 284 ===            Table 12.13 FLAT Instructions for the Opcode Field (Cont.)
=== PDF PAGE 285 ===            Chapter 13 / Microcode Formats        <- fin de cap. 12
```

**Conclusión de §1: capítulo 12 = PDF páginas 107 … 284 = impresas 12-1 … 12-178. 178 páginas
impresas, 178 páginas PDF, correspondencia 1:1 sin huecos.** Verificado por tres caminos
independientes (TOC, marcadores impresos, lectura de los cuatro páginas frontera).

### 1.4 Extracción guardada para no repetirla

```
$ pdftotext -f 107 -l 284 -layout …/gcn3-isa.pdf \
      08-ARQUITECTURA/artifacts/Q5-ISA-CAP12/cap12.txt ; echo exit_status=$?
exit_status=0
-rw-r--r-- 1 lucas lucas 350492 …  cap12.txt
sha256  877b92024e43a8d7d74863ffe6873d293e23a6edf961f77dcd274b95920c8df8
# formfeeds: 178 -> logical pages = 178   (coincide con el capítulo medido)
```

Artefactos producidos en este directorio:

| fichero | qué es | sha256 |
|---|---|---|
| `cap12.txt` | texto crudo extraído del cap. 12 (`-layout`), 178 pág. lógicas | `877b9202…c8df8` |
| `cap12-opcodes-all.tsv` | las 396 líneas `Microcode … Opcode` con nombre y página | `a42d1538…5d88d` |
| `coverage-216.tsv` | las 216 filas del universo con su estado y procedencia | `175ce7da…9385e5` |

---

## 2. La forma en que el capítulo 12 contiene la correspondencia opcode → valor

**Sí contiene una correspondencia comprobable**, pero **no en forma de tabla para las familias
escalares**. Hay dos mecanismos distintos en el mismo capítulo:

**(a) Las 5 tablas tituladas "Instructions for the Opcode Field" son solo de formatos vector-memoria.**
Búsqueda literal en las 348 páginas del libro:

```
$ grep-ish sobre full.txt: /^\s*Table (\d+\.\d+)\s+(.{0,80}Opcode.{0,60})$/
pdf 81  Table 8.12   Image Opcodes with No Sampler            <- cap. 8, fuera de alcance
pdf 82  Table 8.12   Image Opcodes with No Sampler (Cont.)    <- fuera de alcance
pdf267  Table 12.7   DS Instructions for the Opcode Field      12-161
pdf268-272 Table 12.7  … (Cont.) x5
pdf273-275 Table 12.8   MUBUF Instructions for the Opcode Field 12-167
pdf276-277 Table 12.9   MTBUF Instructions for the Opcode Field 12-170
pdf278-281 Table 12.12  MIMG Instructions for the Opcode Field 12-173
pdf283-284 Table 12.13  FLAT Instructions for the Opcode Field 12-177
```

Es decir: **DS/LDS, MUBUF, MTBUF, MIMG y FLAT** — y ninguna más. Para los formatos escalares
(SOP1/SOP2/SOPK/SOPC/SOPP) ni para SMEM **no existe tabla de campo de opcode en el capítulo 12**.
(Las Tablas 12.1–12.3 son de VOPC; 12.4–12.6, 12.10 y 12.11 no son de opcode.)

**(b) Para los formatos escalares y SMEM el valor viaja en una línea por instrucción**, del tipo
`Microcode <FORMATO> Opcode <dec> (<hex>)`, situada bajo cada título `Instruction`. Esa es la fuente
que usa este nodo para las 216.

Recuento de las líneas `Microcode … Opcode` de todo el capítulo 12 (PDF 107-284):

```
líneas Microcode … Opcode totales en cap.12 : 485
  VOP3a 159   VOP1 76   VOP2 52   SOP1 49   SOP2 43
  SOPP 29     SMEM 25   SOPC 21   SOPK 20   VINTRP 3   VOP3b 8
con nombre de instrucción asociado        : 396   (los 89 sin nombre son VOP3a/VOP3b)
escalares+SMEM con nombre                  : 187   <-- subconjunto que compete con las 216
```

**Advertencia de método, registrada porque cambió el resultado:** una primera pasada con regex estricta
`\(0x[0-9A-Fa-f]+\)` dio 182 cubiertos y clasificación errónea de `S_ABS_I32`, `S_BITCMP0_B32` y
`S_ORN2_B32` como "ausentes". La causa era del propio PDF: escribe `(0x 30)` con un espacio y `(C)`
sin prefijo `0x`. Con regex tolerante las 485 líneas parsean y **no queda ninguna línea sin parsear**.
Si alguien reproduce esto con regex estricta, obtendrá 182 y Pensará que hay 3 huecos que no existen.

Ejemplo de la tabla tal cual sale (`cap12.txt`, PDF 108 = impresa 12-2):

```
Instruction     S_ADD_I32
Microcode SOP2 Opcode 2 (0x2)
Instruction     S_ADD_U32
Microcode SOP2 Opcode 0 (0x0)
Instruction     S_ADDC_U32
Microcode SOP2 Opcode 4 (0x4)
Instruction     S_AND_B32
Microcode SOP2 Opcode 13 (0xC)
```

### 2.1 Tabla completa nombre → valor con página de procedencia (216 filas)

Las 216 entradas del universo. `DIFIERE` y `AUSENTE_DE_CH12` se explican en §3.3 y §3.4.

| # | nombre en header | valor header | nombre ISA | opcode ISA tal cual | pag. impresa | pag. PDF | estado |
|---|---|---|---|---|---|---|---|
| 1 | `SQ_S_MOV_B32` | `0x0` | `S_MOV_B32` | SOP1 `1(0x0)` | `12-25` | `pdf131` | COINCIDE |
| 2 | `SQ_S_MOV_B64` | `0x1` | `S_MOV_B64` | SOP1 `1(0x1)` | `12-25` | `pdf131` | COINCIDE |
| 3 | `SQ_S_CMOV_B32` | `0x2` | `S_CMOV_B32` | SOP1 `2(0x2)` | `12-22` | `pdf128` | COINCIDE |
| 4 | `SQ_S_CMOV_B64` | `0x3` | `S_CMOV_B64` | SOP1 `3(0x3)` | `12-22` | `pdf128` | COINCIDE |
| 5 | `SQ_S_NOT_B32` | `0x4` | `S_NOT_B32` | SOP1 `4(0x4)` | `12-27` | `pdf133` | COINCIDE |
| 6 | `SQ_S_NOT_B64` | `0x5` | `S_NOT_B64` | SOP1 `5(0x5)` | `12-27` | `pdf133` | COINCIDE |
| 7 | `SQ_S_WQM_B32` | `0x6` | `S_WQM_B32` | SOP1 `6(0x6)` | `12-30` | `pdf136` | COINCIDE |
| 8 | `SQ_S_WQM_B64` | `0x7` | `S_WQM_B64` | SOP1 `7(0x7)` | `12-30` | `pdf136` | COINCIDE |
| 9 | `SQ_S_BREV_B32` | `0x8` | `S_BREV_B32` | SOP1 `8(0x8)` | `12-21` | `pdf127` | COINCIDE |
| 10 | `SQ_S_BREV_B64` | `0x9` | `S_BREV_B64` | SOP1 `9(0x9)` | `12-22` | `pdf128` | COINCIDE |
| 11 | `SQ_S_BCNT0_I32_B32` | `0xa` | `S_BCNT0_I32_B32` | SOP1 `10(0xA)` | `12-19` | `pdf125` | COINCIDE |
| 12 | `SQ_S_BCNT0_I32_B64` | `0xb` | `S_BCNT0_I32_B64` | SOP1 `11(0xB)` | `12-20` | `pdf126` | COINCIDE |
| 13 | `SQ_S_BCNT1_I32_B32` | `0xc` | `S_BCNT1_I32_B32` | SOP1 `12(0xC)` | `12-20` | `pdf126` | COINCIDE |
| 14 | `SQ_S_BCNT1_I32_B64` | `0xd` | `S_BCNT1_I32_B64` | SOP1 `13(0xD)` | `12-20` | `pdf126` | COINCIDE |
| 15 | `SQ_S_FF0_I32_B32` | `0xe` | `S_FF0_I32_B32` | SOP1 `14(0xE)` | `12-23` | `pdf129` | COINCIDE |
| 16 | `SQ_S_FF0_I32_B64` | `0xf` | `S_FF0_I32_B64` | SOP1 `15(0xF)` | `12-23` | `pdf129` | COINCIDE |
| 17 | `SQ_S_FF1_I32_B32` | `0x10` | `S_FF1_I32_B32` | SOP1 `16(0x10)` | `12-23` | `pdf129` | COINCIDE |
| 18 | `SQ_S_FF1_I32_B64` | `0x11` | `S_FF1_I32_B64` | SOP1 `17(0x11)` | `12-23` | `pdf129` | COINCIDE |
| 19 | `SQ_S_FLBIT_I32_B32` | `0x12` | `S_FLBIT_I32_B32` | SOP1 `18(0x12)` | `12-24` | `pdf130` | COINCIDE |
| 20 | `SQ_S_FLBIT_I32_B64` | `0x13` | `S_FLBIT_I32_B64` | SOP1 `19(0x13)` | `12-24` | `pdf130` | COINCIDE |
| 21 | `SQ_S_FLBIT_I32` | `0x14` | `S_FLBIT_I32` | SOP1 `20(0x14)` | `12-24` | `pdf130` | COINCIDE |
| 22 | `SQ_S_FLBIT_I32_I64` | `0x15` | `S_FLBIT_I32_I64` | SOP1 `21(0x15)` | `12-24` | `pdf130` | COINCIDE |
| 23 | `SQ_S_SEXT_I32_I8` | `0x16` | `S_SEXT_I32_I8` | SOP1 `22(0x16)` | `12-29` | `pdf135` | COINCIDE |
| 24 | `SQ_S_SEXT_I32_I16` | `0x17` | `S_SEXT_I32_I16` | SOP1 `23(0x17)` | `12-29` | `pdf135` | COINCIDE |
| 25 | `SQ_S_BITSET0_B32` | `0x18` | `S_BITSET0_B32` | SOP1 `24(0x18)` | `12-20` | `pdf126` | COINCIDE |
| 26 | `SQ_S_BITSET0_B64` | `0x19` | `S_BITSET0_B64` | SOP1 `25(0x19)` | `12-21` | `pdf127` | COINCIDE |
| 27 | `SQ_S_BITSET1_B32` | `0x1a` | `S_BITSET1_B32` | SOP1 `26(0x1A)` | `12-21` | `pdf127` | COINCIDE |
| 28 | `SQ_S_BITSET1_B64` | `0x1b` | `S_BITSET1_B64` | SOP1 `27(0x1B)` | `12-21` | `pdf127` | COINCIDE |
| 29 | `SQ_S_GETPC_B64` | `0x1c` | `S_GETPC_B64` | SOP1 `28(0x1C)` | `12-25` | `pdf131` | COINCIDE |
| 30 | `SQ_S_SETPC_B64` | `0x1d` | `S_SETPC_B64` | SOP1 `29(0x1D)` | `12-29` | `pdf135` | COINCIDE |
| 31 | `SQ_S_SWAPPC_B64` | `0x1e` | `S_SWAPPC_B64` | SOP1 `30(0x1E)` | `12-30` | `pdf136` | COINCIDE |
| 32 | `SQ_S_RFE_B64` | `0x1f` | `S_RFE_B64` | SOP1 `31(0x1F)` | `12-28` | `pdf134` | COINCIDE |
| 33 | `SQ_S_AND_SAVEEXEC_B64` | `0x20` | `S_AND_SAVEEXEC_B64` | SOP1 `32(0x20)` | `12-19` | `pdf125` | COINCIDE |
| 34 | `SQ_S_OR_SAVEEXEC_B64` | `0x21` | `S_OR_SAVEEXEC_B64` | SOP1 `33(0x21)` | `12-27` | `pdf133` | COINCIDE |
| 35 | `SQ_S_XOR_SAVEEXEC_B64` | `0x22` | `S_XOR_SAVEEXEC_B64` | SOP1 `34(0x22)` | `12-31` | `pdf137` | COINCIDE |
| 36 | `SQ_S_ANDN2_SAVEEXEC_B64` | `0x23` | `S_ANDN2_SAVEEXEC_B64` | SOP1 `35(0x23)` | `12-19` | `pdf125` | COINCIDE |
| 37 | `SQ_S_ORN2_SAVEEXEC_B64` | `0x24` | `S_ORN2_SAVEEXEC_B64` | SOP1 `36(0x24)` | `12-28` | `pdf134` | COINCIDE |
| 38 | `SQ_S_NAND_SAVEEXEC_B64` | `0x25` | `S_NAND_SAVEEXEC_B64` | SOP1 `37(0x25)` | `12-26` | `pdf132` | COINCIDE |
| 39 | `SQ_S_NOR_SAVEEXEC_B64` | `0x26` | `S_NOR_SAVEEXEC_B64` | SOP1 `38(0x26)` | `12-27` | `pdf133` | COINCIDE |
| 40 | `SQ_S_XNOR_SAVEEXEC_B64` | `0x27` | `S_XNOR_SAVEEXEC_B64` | SOP1 `39(0x27)` | `12-30` | `pdf136` | COINCIDE |
| 41 | `SQ_S_QUADMASK_B32` | `0x28` | `S_QUADMASK_B32` | SOP1 `40(0x28)` | `12-28` | `pdf134` | COINCIDE |
| 42 | `SQ_S_QUADMASK_B64` | `0x29` | `S_QUADMASK_B64` | SOP1 `41(0x29)` | `12-28` | `pdf134` | COINCIDE |
| 43 | `SQ_S_MOVRELS_B32` | `0x2a` | `S_MOVRELS_B32` | SOP1 `42(0x2A)` | `12-26` | `pdf132` | COINCIDE |
| 44 | `SQ_S_MOVRELS_B64` | `0x2b` | `S_MOVRELS_B64` | SOP1 `43(0x2B)` | `12-26` | `pdf132` | COINCIDE |
| 45 | `SQ_S_MOVRELD_B32` | `0x2c` | `S_MOVRELD_B32` | SOP1 `44(0x2C)` | `12-25` | `pdf131` | COINCIDE |
| 46 | `SQ_S_MOVRELD_B64` | `0x2d` | `S_MOVRELD_B64` | SOP1 `45(0x2D)` | `12-26` | `pdf132` | COINCIDE |
| 47 | `SQ_S_CBRANCH_JOIN` | `0x2e` | `S_CBRANCH_JOIN` | SOP1 `46(0x2E)` | `12-22` | `pdf128` | COINCIDE |
| 48 | `SQ_S_MOV_REGRD_B32` | `0x2f` | — | — | — | — | AUSENTE_DE_CH12 |
| 49 | `SQ_S_ABS_I32` | `0x30` | `S_ABS_I32` | SOP1 `48(0x30)` | `12-19` | `pdf125` | COINCIDE |
| 50 | `SQ_S_MOV_FED_B32` | `0x31` | — | — | — | — | AUSENTE_DE_CH12 |
| 51 | `SQ_S_SET_GPR_IDX_IDX` | `0x32` | `S_SET_GPR_IDX_IDX` | SOP1 `50(0x32)` | `12-29` | `pdf135` | COINCIDE |
| 52 | `SQ_S_MOVK_I32` | `0x0` | `S_MOVK_I32` | SOPK `0(0x0)` | `12-17` | `pdf123` | COINCIDE |
| 53 | `SQ_S_CMOVK_I32` | `0x1` | `S_CMOVK_I32` | SOPK `1(0x1)` | `12-13` | `pdf119` | COINCIDE |
| 54 | `SQ_S_CMPK_EQ_I32` | `0x2` | `S_CMPK_EQ_I32` | SOPK `2(0x2)` | `12-13` | `pdf119` | COINCIDE |
| 55 | `SQ_S_CMPK_LG_I32` | `0x3` | `S_CMPK_LG_I32` | SOPK `3(0x3)` | `12-15` | `pdf121` | COINCIDE |
| 56 | `SQ_S_CMPK_GT_I32` | `0x4` | `S_CMPK_GT_I32` | SOPK `4(0x4)` | `12-14` | `pdf120` | COINCIDE |
| 57 | `SQ_S_CMPK_GE_I32` | `0x5` | `S_CMPK_GE_I32` | SOPK `5(0x5)` | `12-14` | `pdf120` | COINCIDE |
| 58 | `SQ_S_CMPK_LT_I32` | `0x6` | `S_CMPK_LT_I32` | SOPK `6(0x6)` | `12-16` | `pdf122` | COINCIDE |
| 59 | `SQ_S_CMPK_LE_I32` | `0x7` | `S_CMPK_LE_I32` | SOPK `7(0x7)` | `12-15` | `pdf121` | COINCIDE |
| 60 | `SQ_S_CMPK_EQ_U32` | `0x8` | `S_CMPK_EQ_U32` | SOPK `8(0x8)` | `12-14` | `pdf120` | COINCIDE |
| 61 | `SQ_S_CMPK_LG_U32` | `0x9` | `S_CMPK_LG_U32` | SOPK `9(0x9)` | `12-16` | `pdf122` | COINCIDE |
| 62 | `SQ_S_CMPK_GT_U32` | `0xa` | `S_CMPK_GT_U32` | SOPK `10(0xA)` | `12-15` | `pdf121` | COINCIDE |
| 63 | `SQ_S_CMPK_GE_U32` | `0xb` | `S_CMPK_GE_U32` | SOPK `11(0xB)` | `12-14` | `pdf120` | COINCIDE |
| 64 | `SQ_S_CMPK_LT_U32` | `0xc` | `S_CMPK_LT_U32` | SOPK `12(0xC)` | `12-16` | `pdf122` | COINCIDE |
| 65 | `SQ_S_CMPK_LE_U32` | `0xd` | `S_CMPK_LE_U32` | SOPK `13(0xD)` | `12-15` | `pdf121` | COINCIDE |
| 66 | `SQ_S_ADDK_I32` | `0xe` | `S_ADDK_I32` | SOPK `14(0xE)` | `12-13` | `pdf119` | COINCIDE |
| 67 | `SQ_S_MULK_I32` | `0xf` | `S_MULK_I32` | SOPK `15(0xF)` | `12-17` | `pdf123` | COINCIDE |
| 68 | `SQ_S_CBRANCH_I_FORK` | `0x10` | `S_CBRANCH_I_FORK` | SOPK `16(0x10)` | `12-13` | `pdf119` | COINCIDE |
| 69 | `SQ_S_GETREG_B32` | `0x11` | `S_GETREG_B32` | SOPK `17(0x11)` | `12-16` | `pdf122` | COINCIDE |
| 70 | `SQ_S_SETREG_B32` | `0x12` | `S_SETREG_B32` | SOPK `18(0x12)` | `12-17` | `pdf123` | COINCIDE |
| 71 | `SQ_S_GETREG_REGRD_B32` | `0x13` | — | — | — | — | AUSENTE_DE_CH12 |
| 72 | `SQ_S_SETREG_IMM32_B32` | `0x14` | `S_SETREG_IMM32_B32` | SOPK `20(0x14)` | `12-18` | `pdf124` | COINCIDE |
| 73 | `SQ_S_LOAD_DWORD` | `0x0` | `S_LOAD_DWORD` | SMEM `0(0x0)` | `12-53` | `pdf159` | COINCIDE |
| 74 | `SQ_S_LOAD_DWORDX2` | `0x1` | `S_LOAD_DWORDX2` | SMEM `1(0x1)` | `12-53` | `pdf159` | COINCIDE |
| 75 | `SQ_S_LOAD_DWORDX4` | `0x2` | `S_LOAD_DWORDX4` | SMEM `2(0x2)` | `12-54` | `pdf160` | COINCIDE |
| 76 | `SQ_S_LOAD_DWORDX8` | `0x3` | `S_LOAD_DWORDX8` | SMEM `3(0x3)` | `12-54` | `pdf160` | COINCIDE |
| 77 | `SQ_S_LOAD_DWORDX16` | `0x4` | `S_LOAD_DWORDX16` | SMEM `4(0x4)` | `12-55` | `pdf161` | COINCIDE |
| 78 | `SQ_S_BUFFER_LOAD_DWORD` | `0x8` | `S_BUFFER_LOAD_DWORD` | SMEM `8(0x8)` | `12-48` | `pdf154` | COINCIDE |
| 79 | `SQ_S_BUFFER_LOAD_DWORDX2` | `0x9` | `S_BUFFER_LOAD_DWORDX2` | SMEM `9(0x9)` | `12-48` | `pdf154` | COINCIDE |
| 80 | `SQ_S_BUFFER_LOAD_DWORDX4` | `0xa` | `S_BUFFER_LOAD_DWORDX4` | SMEM `10(0xA)` | `12-49` | `pdf155` | COINCIDE |
| 81 | `SQ_S_BUFFER_LOAD_DWORDX8` | `0xb` | `S_BUFFER_LOAD_DWORDX8` | SMEM `11(0xB)` | `12-49` | `pdf155` | COINCIDE |
| 82 | `SQ_S_BUFFER_LOAD_DWORDX16` | `0xc` | `S_BUFFER_LOAD_DWORDX16` | SMEM `12(0xC)` | `12-50` | `pdf156` | COINCIDE |
| 83 | `SQ_S_STORE_DWORD` | `0x10` | `S_STORE_DWORD` | SMEM `16(0x10)` | `12-56` | `pdf162` | COINCIDE |
| 84 | `SQ_S_STORE_DWORDX2` | `0x11` | `S_STORE_DWORDX2` | SMEM `17(0x11)` | `12-56` | `pdf162` | COINCIDE |
| 85 | `SQ_S_STORE_DWORDX4` | `0x12` | `S_STORE_DWORDX4` | SMEM `18(0x12)` · SMEM `18(0x12)` | `12-57` | `pdf163` | COINCIDE |
| 86 | `SQ_S_BUFFER_STORE_DWORD` | `0x18` | `S_BUFFER_STORE_DWORD` | SMEM `24(0x18)` | `12-50` | `pdf156` | COINCIDE |
| 87 | `SQ_S_BUFFER_STORE_DWORDX2` | `0x19` | `S_BUFFER_STORE_DWORDX2` | SMEM `25(0x19)` | `12-51` | `pdf157` | COINCIDE |
| 88 | `SQ_S_BUFFER_STORE_DWORDX4` | `0x1a` | `S_BUFFER_STORE_DWORDX4` | SMEM `26(0x1A)` | `12-51` | `pdf157` | COINCIDE |
| 89 | `SQ_S_DCACHE_INV` | `0x20` | `S_DCACHE_INV` | SMEM `32(0x20)` | `12-51` | `pdf157` | COINCIDE |
| 90 | `SQ_S_DCACHE_WB` | `0x21` | `S_DCACHE_WB` | SMEM `33(0x21)` | `12-52` | `pdf158` | COINCIDE |
| 91 | `SQ_S_DCACHE_INV_VOL` | `0x22` | `S_DCACHE_INV_VOL` | SMEM `34(0x22)` | `12-52` | `pdf158` | COINCIDE |
| 92 | `SQ_S_DCACHE_WB_VOL` | `0x23` | `S_DCACHE_WB_VOL` | SMEM `35(0x23)` | `12-52` | `pdf158` | COINCIDE |
| 93 | `SQ_S_MEMTIME` | `0x24` | `S_MEMTIME` | SMEM `36(0x24)` | `12-56` | `pdf162` | COINCIDE |
| 94 | `SQ_S_MEMREALTIME` | `0x25` | `S_MEMREALTIME` | SMEM `37(0x25)` | `12-55` | `pdf161` | COINCIDE |
| 95 | `SQ_S_ATC_PROBE` | `0x26` | `S_ATC_PROBE` | SMEM `38(0x26)` | `12-47` | `pdf153` | COINCIDE |
| 96 | `SQ_S_ATC_PROBE_BUFFER` | `0x27` | `S_ATC_PROBE_BUFFER` | SMEM `38(0x26)` | `12-47` | `pdf153` | DIFIERE |
| 97 | `SQ_S_BUFFER_ATOMIC_SWAP` | `0x40` | — | — | — | — | AUSENTE_DE_CH12 |
| 98 | `SQ_S_BUFFER_ATOMIC_CMPSWAP` | `0x41` | — | — | — | — | AUSENTE_DE_CH12 |
| 99 | `SQ_S_BUFFER_ATOMIC_ADD` | `0x42` | — | — | — | — | AUSENTE_DE_CH12 |
| 100 | `SQ_S_BUFFER_ATOMIC_SUB` | `0x43` | — | — | — | — | AUSENTE_DE_CH12 |
| 101 | `SQ_S_BUFFER_ATOMIC_SMIN` | `0x44` | — | — | — | — | AUSENTE_DE_CH12 |
| 102 | `SQ_S_BUFFER_ATOMIC_UMIN` | `0x45` | — | — | — | — | AUSENTE_DE_CH12 |
| 103 | `SQ_S_BUFFER_ATOMIC_SMAX` | `0x46` | — | — | — | — | AUSENTE_DE_CH12 |
| 104 | `SQ_S_BUFFER_ATOMIC_UMAX` | `0x47` | — | — | — | — | AUSENTE_DE_CH12 |
| 105 | `SQ_S_BUFFER_ATOMIC_AND` | `0x48` | — | — | — | — | AUSENTE_DE_CH12 |
| 106 | `SQ_S_BUFFER_ATOMIC_OR` | `0x49` | — | — | — | — | AUSENTE_DE_CH12 |
| 107 | `SQ_S_BUFFER_ATOMIC_XOR` | `0x4a` | — | — | — | — | AUSENTE_DE_CH12 |
| 108 | `SQ_S_BUFFER_ATOMIC_INC` | `0x4b` | — | — | — | — | AUSENTE_DE_CH12 |
| 109 | `SQ_S_BUFFER_ATOMIC_DEC` | `0x4c` | — | — | — | — | AUSENTE_DE_CH12 |
| 110 | `SQ_S_BUFFER_ATOMIC_SWAP_X2` | `0x60` | — | — | — | — | AUSENTE_DE_CH12 |
| 111 | `SQ_S_BUFFER_ATOMIC_CMPSWAP_X2` | `0x61` | — | — | — | — | AUSENTE_DE_CH12 |
| 112 | `SQ_S_BUFFER_ATOMIC_ADD_X2` | `0x62` | — | — | — | — | AUSENTE_DE_CH12 |
| 113 | `SQ_S_BUFFER_ATOMIC_SUB_X2` | `0x63` | — | — | — | — | AUSENTE_DE_CH12 |
| 114 | `SQ_S_BUFFER_ATOMIC_SMIN_X2` | `0x64` | — | — | — | — | AUSENTE_DE_CH12 |
| 115 | `SQ_S_BUFFER_ATOMIC_UMIN_X2` | `0x65` | — | — | — | — | AUSENTE_DE_CH12 |
| 116 | `SQ_S_BUFFER_ATOMIC_SMAX_X2` | `0x66` | — | — | — | — | AUSENTE_DE_CH12 |
| 117 | `SQ_S_BUFFER_ATOMIC_UMAX_X2` | `0x67` | — | — | — | — | AUSENTE_DE_CH12 |
| 118 | `SQ_S_BUFFER_ATOMIC_AND_X2` | `0x68` | — | — | — | — | AUSENTE_DE_CH12 |
| 119 | `SQ_S_BUFFER_ATOMIC_OR_X2` | `0x69` | — | — | — | — | AUSENTE_DE_CH12 |
| 120 | `SQ_S_BUFFER_ATOMIC_XOR_X2` | `0x6a` | — | — | — | — | AUSENTE_DE_CH12 |
| 121 | `SQ_S_BUFFER_ATOMIC_INC_X2` | `0x6b` | — | — | — | — | AUSENTE_DE_CH12 |
| 122 | `SQ_S_BUFFER_ATOMIC_DEC_X2` | `0x6c` | — | — | — | — | AUSENTE_DE_CH12 |
| 123 | `SQ_S_NOP` | `0x0` | `S_NOP` | SOPP `0(0x0)` | `12-42` | `pdf148` | COINCIDE |
| 124 | `SQ_S_ENDPGM` | `0x1` | `S_ENDPGM` | SOPP `1(0x1)` | `12-41` | `pdf147` | COINCIDE |
| 125 | `SQ_S_BRANCH` | `0x2` | `S_BRANCH` | SOPP `2(0x2)` | `12-38` | `pdf144` | COINCIDE |
| 126 | `SQ_S_WAKEUP` | `0x3` | — | — | — | — | AUSENTE_DE_CH12 |
| 127 | `SQ_S_CBRANCH_SCC0` | `0x4` | `S_CBRANCH_SCC0` | SOPP `4(0x4)` | `12-40` | `pdf146` | COINCIDE |
| 128 | `SQ_S_CBRANCH_SCC1` | `0x5` | `S_CBRANCH_SCC1` | SOPP `5(0x5)` | `12-40` | `pdf146` | COINCIDE |
| 129 | `SQ_S_CBRANCH_VCCZ` | `0x6` | `S_CBRANCH_VCCZ` | SOPP `6(0x6)` | `12-40` | `pdf146` | COINCIDE |
| 130 | `SQ_S_CBRANCH_VCCNZ` | `0x7` | `S_CBRANCH_VCCNZ` | SOPP `7(0x7)` | `12-40` | `pdf146` | COINCIDE |
| 131 | `SQ_S_CBRANCH_EXECZ` | `0x8` | `S_CBRANCH_EXECZ` | SOPP `8(0x8)` | `12-39` | `pdf145` | COINCIDE |
| 132 | `SQ_S_CBRANCH_EXECNZ` | `0x9` | `S_CBRANCH_EXECNZ` | SOPP `9(0x9)` | `12-39` | `pdf145` | COINCIDE |
| 133 | `SQ_S_BARRIER` | `0xa` | `S_BARRIER` | SOPP `10(0xA)` | `12-38` | `pdf144` | COINCIDE |
| 134 | `SQ_S_SETKILL` | `0xb` | `S_SETKILL` | SOPP `11(0xB)` | `12-44` | `pdf150` | COINCIDE |
| 135 | `SQ_S_WAITCNT` | `0xc` | `S_WAITCNT` | SOPP `12(0xC)` | `12-46` | `pdf152` | COINCIDE |
| 136 | `SQ_S_SETHALT` | `0xd` | `S_SETHALT` | SOPP `13(0xD)` | `12-44` | `pdf150` | COINCIDE |
| 137 | `SQ_S_SLEEP` | `0xe` | `S_SLEEP` | SOPP `14(0xE)` | `12-45` | `pdf151` | COINCIDE |
| 138 | `SQ_S_SETPRIO` | `0xf` | `S_SETPRIO` | SOPP `15(0xF)` | `12-45` | `pdf151` | COINCIDE |
| 139 | `SQ_S_SENDMSG` | `0x10` | `S_SENDMSG` | SOPP `16(0x10)` | `12-43` | `pdf149` | COINCIDE |
| 140 | `SQ_S_SENDMSGHALT` | `0x11` | `S_SENDMSGHALT` | SOPP `17(0x11)` | `12-43` | `pdf149` | COINCIDE |
| 141 | `SQ_S_TRAP` | `0x12` | `S_TRAP` | SOPP `18(0x12)` | `12-45` | `pdf151` | COINCIDE |
| 142 | `SQ_S_ICACHE_INV` | `0x13` | `S_ICACHE_INV` | SOPP `19(0x13)` | `12-41` | `pdf147` | COINCIDE |
| 143 | `SQ_S_INCPERFLEVEL` | `0x14` | `S_INCPERFLEVEL` | SOPP `20(0x14)` | `12-42` | `pdf148` | COINCIDE |
| 144 | `SQ_S_DECPERFLEVEL` | `0x15` | `S_DECPERFLEVEL` | SOPP `21(0x15)` | `12-41` | `pdf147` | COINCIDE |
| 145 | `SQ_S_TTRACEDATA` | `0x16` | `S_TTRACEDATA` | SOPP `22(0x16)` | `12-45` | `pdf151` | COINCIDE |
| 146 | `SQ_S_CBRANCH_CDBGSYS` | `0x17` | `S_CBRANCH_CDBGSYS` | SOPP `23(0x17)` | `12-38` | `pdf144` | COINCIDE |
| 147 | `SQ_S_CBRANCH_CDBGUSER` | `0x18` | `S_CBRANCH_CDBGUSER` | SOPP `24(0x18)` | `12-39` | `pdf145` | COINCIDE |
| 148 | `SQ_S_CBRANCH_CDBGSYS_OR_USER` | `0x19` | `S_CBRANCH_CDBGSYS_OR_USER` | SOPP `25(0x19)` | `12-39` | `pdf145` | COINCIDE |
| 149 | `SQ_S_CBRANCH_CDBGSYS_AND_USER` | `0x1a` | `S_CBRANCH_CDBGSYS_AND_USER` | SOPP `26(0x1A)` | `12-38` | `pdf144` | COINCIDE |
| 150 | `SQ_S_ENDPGM_SAVED` | `0x1b` | `S_ENDPGM_SAVED` | SOPP `27(0x1B)` | `12-41` | `pdf147` | COINCIDE |
| 151 | `SQ_S_SET_GPR_IDX_OFF` | `0x1c` | `S_SET_GPR_IDX_OFF` | SOPP `28(0x1C)` | `12-44` | `pdf150` | COINCIDE |
| 152 | `SQ_S_SET_GPR_IDX_MODE` | `0x1d` | `S_SET_GPR_IDX_MODE` | SOPP `29(0x1D)` | `12-44` | `pdf150` | COINCIDE |
| 153 | `SQ_S_CMP_EQ_I32` | `0x0` | `S_CMP_EQ_I32` | SOPC `0(0x0)` | `12-33` | `pdf139` | COINCIDE |
| 154 | `SQ_S_CMP_LG_I32` | `0x1` | `S_CMP_LG_I32` | SOPC `1(0x1)` | `12-35` | `pdf141` | COINCIDE |
| 155 | `SQ_S_CMP_GT_I32` | `0x2` | `S_CMP_GT_I32` | SOPC `2(0x2)` | `12-34` | `pdf140` | COINCIDE |
| 156 | `SQ_S_CMP_GE_I32` | `0x3` | `S_CMP_GE_I32` | SOPC `3(0x3)` | `12-33` | `pdf139` | COINCIDE |
| 157 | `SQ_S_CMP_LT_I32` | `0x4` | `S_CMP_LT_I32` | SOPC `4(0x4)` | `12-36` | `pdf142` | COINCIDE |
| 158 | `SQ_S_CMP_LE_I32` | `0x5` | `S_CMP_LE_I32` | SOPC `5(0x5)` | `12-34` | `pdf140` | COINCIDE |
| 159 | `SQ_S_CMP_EQ_U32` | `0x6` | `S_CMP_EQ_U32` | SOPC `6(0x6)` | `12-33` | `pdf139` | COINCIDE |
| 160 | `SQ_S_CMP_LG_U32` | `0x7` | `S_CMP_LG_U32` | SOPC `7(0x7)` | `12-35` | `pdf141` | COINCIDE |
| 161 | `SQ_S_CMP_GT_U32` | `0x8` | `S_CMP_GT_U32` | SOPC `8(0x8)` | `12-34` | `pdf140` | COINCIDE |
| 162 | `SQ_S_CMP_GE_U32` | `0x9` | `S_CMP_GE_U32` | SOPC `9(0x9)` | `12-34` | `pdf140` | COINCIDE |
| 163 | `SQ_S_CMP_LT_U32` | `0xa` | `S_CMP_LT_U32` | SOPC `10(0xA)` | `12-36` | `pdf142` | COINCIDE |
| 164 | `SQ_S_CMP_LE_U32` | `0xb` | `S_CMP_LE_U32` | SOPC `11(0xB)` | `12-35` | `pdf141` | COINCIDE |
| 165 | `SQ_S_BITCMP0_B32` | `0xc` | `S_BITCMP0_B32` | SOPC `12(C)` | `12-32` | `pdf138` | COINCIDE |
| 166 | `SQ_S_BITCMP1_B32` | `0xd` | `S_BITCMP1_B32` | SOPC `13(0xD)` | `12-32` | `pdf138` | COINCIDE |
| 167 | `SQ_S_BITCMP0_B64` | `0xe` | `S_BITCMP0_B64` | SOPC `14(0xE)` | `12-32` | `pdf138` | COINCIDE |
| 168 | `SQ_S_BITCMP1_B64` | `0xf` | `S_BITCMP1_B64` | SOPC `15(0xF)` | `12-32` | `pdf138` | COINCIDE |
| 169 | `SQ_S_SETVSKIP` | `0x10` | `S_SETVSKIP` | SOPC `16(0x10)` | `12-37` | `pdf143` | COINCIDE |
| 170 | `SQ_S_SET_GPR_IDX_ON` | `0x11` | `S_SET_GPR_IDX_ON` | SOPC `17(0x11)` | `12-37` | `pdf143` | COINCIDE |
| 171 | `SQ_S_CMP_EQ_U64` | `0x12` | `S_CMP_EQ_U64` | SOPC `18(0x12)` | `12-33` | `pdf139` | COINCIDE |
| 172 | `SQ_S_CMP_LG_U64` | `0x13` | `S_CMP_LG_U64` | SOPC `19(0x13)` | `12-35` | `pdf141` | COINCIDE |
| 173 | `SQ_S_ADD_U32` | `0x0` | `S_ADD_U32` | SOP2 `0(0x0)` | `12-2` | `pdf108` | COINCIDE |
| 174 | `SQ_S_SUB_U32` | `0x1` | `S_SUB_U32` | SOP2 `1(0x1)` | `12-11` | `pdf117` | COINCIDE |
| 175 | `SQ_S_ADD_I32` | `0x2` | `S_ADD_I32` | SOP2 `2(0x2)` | `12-2` | `pdf108` | COINCIDE |
| 176 | `SQ_S_SUB_I32` | `0x3` | `S_SUB_I32` | SOP2 `3(0x3)` | `12-11` | `pdf117` | COINCIDE |
| 177 | `SQ_S_ADDC_U32` | `0x4` | `S_ADDC_U32` | SOP2 `4(0x4)` | `12-2` | `pdf108` | COINCIDE |
| 178 | `SQ_S_SUBB_U32` | `0x5` | `S_SUBB_U32` | SOP2 `5(0x5)` | `12-11` | `pdf117` | COINCIDE |
| 179 | `SQ_S_MIN_I32` | `0x6` | `S_MIN_I32` | SOP2 `6(0x6)` | `12-8` | `pdf114` | COINCIDE |
| 180 | `SQ_S_MIN_U32` | `0x7` | `S_MIN_U32` | SOP2 `7(0x7)` | `12-8` | `pdf114` | COINCIDE |
| 181 | `SQ_S_MAX_I32` | `0x8` | `S_MAX_I32` | SOP2 `8(0x8)` | `12-8` | `pdf114` | COINCIDE |
| 182 | `SQ_S_MAX_U32` | `0x9` | `S_MAX_U32` | SOP2 `9(0x9)` | `12-8` | `pdf114` | COINCIDE |
| 183 | `SQ_S_CSELECT_B32` | `0xa` | `S_CSELECT_B32` | SOP2 `10(0xA)` | `12-6` | `pdf112` | COINCIDE |
| 184 | `SQ_S_CSELECT_B64` | `0xb` | `S_CSELECT_B64` | SOP2 `11(0xB)` | `12-6` | `pdf112` | COINCIDE |
| 185 | `SQ_S_AND_B32` | `0xc` | `S_AND_B32` | SOP2 `13(0xC)` | `12-2` | `pdf108` | COINCIDE |
| 186 | `SQ_S_AND_B64` | `0xd` | `S_AND_B64` | SOP2 `13(0xD)` | `12-3` | `pdf109` | COINCIDE |
| 187 | `SQ_S_OR_B32` | `0xe` | `S_OR_B32` | SOP2 `14(0xE)` | `12-10` | `pdf116` | COINCIDE |
| 188 | `SQ_S_OR_B64` | `0xf` | `S_OR_B64` | SOP2 `15(0xF)` | `12-10` | `pdf116` | COINCIDE |
| 189 | `SQ_S_XOR_B32` | `0x10` | `S_XOR_B32` | SOP2 `16(0x10)` | `12-12` | `pdf118` | COINCIDE |
| 190 | `SQ_S_XOR_B64` | `0x11` | `S_XOR_B64` | SOP2 `17(0x11)` | `12-12` | `pdf118` | COINCIDE |
| 191 | `SQ_S_ANDN2_B32` | `0x12` | `S_ANDN2_B32` | SOP2 `18(0x12)` | `12-3` | `pdf109` | COINCIDE |
| 192 | `SQ_S_ANDN2_B64` | `0x13` | `S_ANDN2_B64` | SOP2 `19(0x13)` | `12-3` | `pdf109` | COINCIDE |
| 193 | `SQ_S_ORN2_B32` | `0x14` | `S_ORN2_B32` | SOP2 `20(0x14)` | `12-10` | `pdf116` | COINCIDE |
| 194 | `SQ_S_ORN2_B64` | `0x15` | `S_ORN2_B64` | SOP2 `21(0x15)` | `12-11` | `pdf117` | COINCIDE |
| 195 | `SQ_S_NAND_B32` | `0x16` | `S_NAND_B32` | SOP2 `22(0x16)` | `12-9` | `pdf115` | COINCIDE |
| 196 | `SQ_S_NAND_B64` | `0x17` | `S_NAND_B64` | SOP2 `23(0x17)` | `12-9` | `pdf115` | COINCIDE |
| 197 | `SQ_S_NOR_B32` | `0x18` | `S_NOR_B32` | SOP2 `24(0x18)` | `12-9` | `pdf115` | COINCIDE |
| 198 | `SQ_S_NOR_B64` | `0x19` | `S_NOR_B64` | SOP2 `25(0x19)` | `12-10` | `pdf116` | COINCIDE |
| 199 | `SQ_S_XNOR_B32` | `0x1a` | `S_XNOR_B32` | SOP2 `26(0x1A)` | `12-12` | `pdf118` | COINCIDE |
| 200 | `SQ_S_XNOR_B64` | `0x1b` | `S_XNOR_B64` | SOP2 `27(0x1B)` | `12-12` | `pdf118` | COINCIDE |
| 201 | `SQ_S_LSHL_B32` | `0x1c` | `S_LSHL_B32` | SOP2 `28(0x1C)` | `12-7` | `pdf113` | COINCIDE |
| 202 | `SQ_S_LSHL_B64` | `0x1d` | `S_LSHL_B64` | SOP2 `29(0x1D)` | `12-7` | `pdf113` | COINCIDE |
| 203 | `SQ_S_LSHR_B32` | `0x1e` | `S_LSHR_B32` | SOP2 `30(0x1E)` | `12-7` | `pdf113` | COINCIDE |
| 204 | `SQ_S_LSHR_B64` | `0x1f` | `S_LSHR_B64` | SOP2 `31(0x15)` | `12-7` | `pdf113` | DIFIERE |
| 205 | `SQ_S_ASHR_I32` | `0x20` | `S_ASHR_I32` | SOP2 `32(0x20)` | `12-3` | `pdf109` | COINCIDE |
| 206 | `SQ_S_ASHR_I64` | `0x21` | `S_ASHR_I64` | SOP2 `33(0x21)` | `12-4` | `pdf110` | COINCIDE |
| 207 | `SQ_S_BFM_B32` | `0x22` | `S_BFM_B32` | SOP2 `34(0x22)` | `12-5` | `pdf111` | COINCIDE |
| 208 | `SQ_S_BFM_B64` | `0x23` | `S_BFM_B64` | SOP2 `35(0x23)` | `12-6` | `pdf112` | COINCIDE |
| 209 | `SQ_S_MUL_I32` | `0x24` | `S_MUL_I32` | SOP2 `36(0x24)` | `12-9` | `pdf115` | COINCIDE |
| 210 | `SQ_S_BFE_U32` | `0x25` | `S_BFE_U32` | SOP2 `37(0x25)` | `12-5` | `pdf111` | COINCIDE |
| 211 | `SQ_S_BFE_I32` | `0x26` | `S_BFE_I32` | SOP2 `38(0x26)` | `12-4` | `pdf110` | COINCIDE |
| 212 | `SQ_S_BFE_U64` | `0x27` | `S_BFE_U64` | SOP2 `39(0x27)` | `12-5` | `pdf111` | COINCIDE |
| 213 | `SQ_S_BFE_I64` | `0x28` | `S_BFE_I64` | SOP2 `40(0x28)` | `12-4` | `pdf110` | COINCIDE |
| 214 | `SQ_S_CBRANCH_G_FORK` | `0x29` | `S_CBRANCH_G_FORK` | SOP2 `41(0x29)` | `12-6` | `pdf112` | COINCIDE |
| 215 | `SQ_S_ABSDIFF_I32` | `0x2a` | `S_ABSDIFF_I32` | SOP2 `42(0x2A)` | `12-1` | `pdf107` | COINCIDE |
| 216 | `SQ_S_RFE_RESTORE_B64` | `0x2b` | — | — | — | — | AUSENTE_DE_CH12 |

---

## 3. COBERTURA medida sobre las 216

### 3.1 Los tres recuentos pedidos

```
nombres_del_isa / 216 = 185
de esos, con_valor / 216 = 185
de esos, ausentes  / 216 =  31
```

`con_valor` = el nombre aparece en el capítulo 12 bajo un título `Instruction` **y** seguido de una
línea `Microcode … Opcode N (…)` de la que se extrae un entero. No hay entradas intermedias:

```
COINCIDE        183
DIFIERE           2
SIN_VALOR_EN_ISA  0     <- ningun titulo Instruction sin linea de opcode
AUSENTE_DE_CH12  31
                ---
total           216
```

La categoría `SIN_VALOR_EN_ISA = 0` importa: **no hay "documentado a medias"**. Cada una de las 31
ausencias es una ausencia total del texto, verificada por búsqueda del nombre en las 178 páginas del
capítulo (`\bS_WAKEUP\b` sale 0 veces; `S_BUFFER_ATOMIC_*` sale 0 veces).

### 3.2 Desglose por familia (formato de la sección 12.x donde cae cada entrada)

| formato ISA | sección | entradas del universo | COINCIDE | DIFIERE | AUSENTE |
|---|---|---|---|---|---|
| SOP1 | 12.3 | 49 | 49 | 0 | 0 |
| SOP2 | 12.1 | 43 | 42 | **1** | 0 |
| SOPK | 12.2 | 20 | 20 | 0 | 0 |
| SOPC | 12.4 | 20 | 20 | 0 | 0 |
| SOPP | 12.5 | 29 | 29 | 0 | 0 |
| SMEM | 12.6 | 24 | 23 | **1** | 0 |
| — sin familia asignable | — | 31 | 0 | 0 | 31 |
| **TOTAL** | | **216** | **183** | **2** | **31** |

Las 5 familias que la contradicción viva nombra (SOP2/SOPK/SMEM/SOPC/SOP1) suman 156 entradas de las
216, con 154 COINCIDE y 2 DIFIERE. Ninguna de esas 156 queda sin correspondencia.

### 3.3 Los 31 ausentes, uno a uno, con su valor de header

| # | entrada | valor header | búsqueda en cap.12 |
|---|---|---|---|
| 1 | `SQ_S_MOV_REGRD_B32` | `0x2f` | 0 apariciones |
| 2 | `SQ_S_MOV_FED_B32` | `0x31` | 0 apariciones |
| 3 | `SQ_S_GETREG_REGRD_B32` | `0x13` | 0 apariciones |
| 4 | `SQ_S_BUFFER_ATOMIC_SWAP` | `0x40` | 0 apariciones |
| 5 | `SQ_S_BUFFER_ATOMIC_CMPSWAP` | `0x41` | 0 apariciones |
| 6 | `SQ_S_BUFFER_ATOMIC_ADD` | `0x42` | 0 apariciones |
| 7 | `SQ_S_BUFFER_ATOMIC_SUB` | `0x43` | 0 apariciones |
| 8 | `SQ_S_BUFFER_ATOMIC_SMIN` | `0x44` | 0 apariciones |
| 9 | `SQ_S_BUFFER_ATOMIC_UMIN` | `0x45` | 0 apariciones |
| 10 | `SQ_S_BUFFER_ATOMIC_SMAX` | `0x46` | 0 apariciones |
| 11 | `SQ_S_BUFFER_ATOMIC_UMAX` | `0x47` | 0 apariciones |
| 12 | `SQ_S_BUFFER_ATOMIC_AND` | `0x48` | 0 apariciones |
| 13 | `SQ_S_BUFFER_ATOMIC_OR` | `0x49` | 0 apariciones |
| 14 | `SQ_S_BUFFER_ATOMIC_XOR` | `0x4a` | 0 apariciones |
| 15 | `SQ_S_BUFFER_ATOMIC_INC` | `0x4b` | 0 apariciones |
| 16 | `SQ_S_BUFFER_ATOMIC_DEC` | `0x4c` | 0 apariciones |
| 17 | `SQ_S_BUFFER_ATOMIC_SWAP_X2` | `0x60` | 0 apariciones |
| 18 | `SQ_S_BUFFER_ATOMIC_CMPSWAP_X2` | `0x61` | 0 apariciones |
| 19 | `SQ_S_BUFFER_ATOMIC_ADD_X2` | `0x62` | 0 apariciones |
| 20 | `SQ_S_BUFFER_ATOMIC_SUB_X2` | `0x63` | 0 apariciones |
| 21 | `SQ_S_BUFFER_ATOMIC_SMIN_X2` | `0x64` | 0 apariciones |
| 22 | `SQ_S_BUFFER_ATOMIC_UMIN_X2` | `0x65` | 0 apariciones |
| 23 | `SQ_S_BUFFER_ATOMIC_SMAX_X2` | `0x66` | 0 apariciones |
| 24 | `SQ_S_BUFFER_ATOMIC_UMAX_X2` | `0x67` | 0 apariciones |
| 25 | `SQ_S_BUFFER_ATOMIC_AND_X2` | `0x68` | 0 apariciones |
| 26 | `SQ_S_BUFFER_ATOMIC_OR_X2` | `0x69` | 0 apariciones |
| 27 | `SQ_S_BUFFER_ATOMIC_XOR_X2` | `0x6a` | 0 apariciones |
| 28 | `SQ_S_BUFFER_ATOMIC_INC_X2` | `0x6b` | 0 apariciones |
| 29 | `SQ_S_BUFFER_ATOMIC_DEC_X2` | `0x6c` | 0 apariciones |
| 30 | `SQ_S_WAKEUP` | `0x3` | **0 apariciones en las 348 páginas del libro entero** |
| 31 | `SQ_S_RFE_RESTORE_B64` | `0x2b` | 0 apariciones |

**Estructura del hueco, que es la observación con más valor de esta sección:** 28 de las 31 ausencias
son `S_BUFFER_ATOMIC_*` (los rangos `0x40`–`0x4c` y `0x60`–`0x6c`, atómicos sobre buffer). Las otras 3
son `S_MOV_REGRD_B32`, `S_MOV_FED_B32`, `S_GETREG_REGRD_B32`, más `S_WAKEUP` y `S_RFE_RESTORE_B64`.
No es un hueco disperso: es **un bloque funcional entero y sus variantes X2**.

En sentido inverso, el capítulo 12 documenta **186** títulos `Instruction S_*` distintos y el header
declara **216** `SQ_S_*`; el único nombre del ISA que no está en el header es `S_CMP_NE_U64`:

```
distinct S_* headings in ch12 : 186
distinct SQ_S_* in header    : 216
en ISA y no en header         :   1  ['S_CMP_NE_U64']
en header y no en ISA         :  31
186 + 31 - 1 = 216  (cuadra)
```

### 3.4 Los 2 `DIFIERE` — con las dos fuentes, sin resolver

No los llamo "contradicción ISA-vs-header" sin matiz, porque en ambos casos **la propia ISA se
contradice a sí misma entre su columna decimal y su columna hex**:

**(a) `SQ_S_ATC_PROBE_BUFFER` — header `0x27`, ISA `SMEM Opcode 38 (0x26)`.** El ISA da **el mismo
valor a dos instrucciones distintas**:

```
pdf153 = impresa 12-47
Instruction           S_ATC_PROBE
Microcode SMEM Opcode 38 (0x26)
Instruction           S_ATC_PROBE_BUFFER
Microcode SMEM Opcode 38 (0x26)     <-- mismo 38/0x26 que S_ATC_PROBE
```

Aquí decimal y hex **sí** son consistentes entre sí (38 = 0x26). El header da `SQ_S_ATC_PROBE 0x26`
y `SQ_S_ATC_PROBE_BUFFER 0x27`, que es internamente coherente. **Dos fuentes, dos valores, y el ISA
reparte un opcode entre dos nombres.** No se resuelve eligiendo: puede ser que uno de los dos nombres
no exista como tal y el documento haya duplicado la entrada, o que uno de los dos valores del header
esté corrido. `NOT_DETERMINED`.

**(b) `SQ_S_LSHR_B64` — header `0x1f`, ISA `SOP2 Opcode 31 (0x15)`.** Aquí el decimal y el hex del
ISA **no** concuerdan: 31 = `0x1F`, no `0x15` (21). El valor del header (`0x1f`) **coincide con el
decimal del ISA**, y el hex del ISA es el discordante.

```
pdf113 = impresa 12-7
Microcode SOP2 Opcode 31 (0x15)
```

**Consecuencia para el counting:** si se comparase solo columnas decimales, `S_LSHR_B64` coincidiría; si
se comparase solo hex, no. El estado `DIFIERE` depende del criterio, y por eso se registra la fuente
literal en vez de un veredicto binario. En §3.1 el criterio usado es: **coincide si el valor del header
aparece en cualquiera de las dos columnas del ISA** (hex si existe, si no decimal). Con criterio
estrictamente-hex, el total sería 184 en vez de 185 y `S_LSHR_B64` sería el tercer DIFIERE.

**Las 3 auto-contradicciones decimal/hex del ISA dentro de lo escalar**, por si alguien reproduce:

```
S_AND_B32    SOP2  dec=13  hexf=0xC   pdf108 = 12-2    (header 0xc -> coincide el hex)
S_LSHR_B64   SOP2  dec=31  hexf=0x15  pdf113 = 12-7    (header 0x1f -> coincide el decimal)
S_MOV_B32    SOP1  dec=1   hexf=0x0   pdf131 = 12-25   (header 0x0 -> coincide el hex)
```

Y dos más fuera del universo medido (VOP1), que se anotan por completitud y no afectan al recuento:

```
V_CEIL_F64   VOP1  dec=24  hexf=0x158 pdf190 = 12-84
V_SQRT_F16   VOP1  dec=62  hexf=0x2E  pdf223 = 12-117
```

---

## 4. Hipótesis resuelta: **H2 (COBERTURA PARCIAL)**, y por qué se descarta H1 y H3

| | estado | discriminante |
|---|---|---|
| **H1 COBERTURA ALTA** | **REFUTADA** | Los 216 nombres **no** aparecen todos: 31 tienen 0 apariciones en las 178 páginas del capítulo, verificado por búsqueda del nombre, no por ausencia de mi regex. Y 2 de los 185 tienen valor discordante, así que "la mayoría con valor numérico" se cumple (185/216 = 85,6 %) pero "los 216 nombres aparecen" **no**. |
| **H2 COBERTURA PARCIAL** | **RESUELTA** | Se cumple exactamente el discriminante tal como estaba escrito: *los 216 nombres aparecen, pero una fracción sin valor; o solo algunos*. Aquí: 185 con valor extraíble, 31 sin ninguna presencia. La cobertura es alta en las 5 familias escalares (154/156 = 98,7 % de coincidencia) y nula en el bloque de atómicos SMEM (28/28 ausentes). Es una cobertura **alta pero no total y no uniforme**. |
| **H3 NADA** | **REFUTADA** | El discriminante de H3 era *cero nombres con valor extraíble*. Medido: **185 con valor extraíble**, más 187 líneas `Microcode` escalares/SMEM con página de procedencia. H3 es falsa por un margen amplio. |

Lo que H3 acertaba —y que queda registrado— es que el capítulo 12 **no contiene la tabla de opcode como
tabla** para las familias escalares: §2(a) demuestra que las 5 tablas "for the Opcode Field" son solo
DS/MUBUF/MTBUF/MIMG/FLAT. La corrección a H3 es que el valor **sí** está, en otro formato.

**Estado del nodo: `RESOLVED_WITH_RESIDUAL_UNIVERSE`.** El residual (§5) está declarado y es
exactamente: 31 entradas sin valor desde esta fuente, y 2 discrepancias sin resolver.

---

## 5. Qué NO se puede concluir con esta medición

Esta sección es obligatoria y no está vacía.

1. **No se puede concluir nada sobre el silicio.** Todo lo medido es una coincidencia entre un
   documento de un proveedor y un header de un driver. **Ni una de las dos fuentes ha sido medida
   contra esta placa.** Que 183 valores coincidan es evidencia de **consistencia entre dos
   documentos**, y nada más. No es `CORRECTNESS`, no es que el silicio codifique así, no es que el
   driver esté bien. Un cambio de silicio o una revisión de ISA podría invalidarlo todo sin que nada
   de lo medido se entere.

2. **No se puede concluir que la ISA sea la fuente correcta para GFX8, ni que lo sea para otra cosa.**
   La portada dice "Graphics Core Next Architecture, **Generation 3**", Rev 1.1, agosto 2016. El
   documento **no contiene nunca la cadena "GFX8"**:

   ```
   GFX8          pages: []  (total 0)
   Polaris       pages: []  (total 0)
   Vega          pages: []  (total 0)
   GFX9          pages: []  (total 0)
   Generation 4  pages: []  (total 0)
   Volcanic      pages: [7, 15]  (total 2)
   ```

   Lo único que el documento se dice a sí mismo es "AMD **Volcanic Islands** Series" (diagramas de
   §1.1 y §2.1, PDF 7 y 15). El catálogo del proyecto afirma en `LIBRARY-CATALOG.md:630`
   «GFX8 = GCN 3», pero **eso es catálogo, no evidencia**, y este nodo no lo adopta ni lo desmiente:
   no lo he medido. La equivalencia Volcanic Islands ↔ gfx803 ↔ RX 550 Polaris 12 queda
   `NOT_DETERMINED` aquí. **`vega-isa.pdf` no se ha abierto**, por LIMITACION_2.

3. **No se puede concluir que las 31 ausencias sean un fallo de documentación del capítulo 12.** Se
   sabe que este texto (Rev 1.1, ago-2016) no las documenta. **No** se sabe si son: (a) adiciones de
   GFX8 posteriores a esa revisión, (b) propias de otra generación, (c) un hueco editorial, o (d) un
   fallo de la extracción. El caso `S_WAKEUP` con 0 apariciones **en las 348 páginas** sugiere (a) o
   (b) más que (d), pero eso es un indicio, no una medición: no he hecho ninguna medición que separe
   esas cuatro hipótesis. Para hacerlo falta una revisión posterior de la ISA GCN3 o una fuente
   específica de GFX8, que este nodo no tenía.

4. **No se puede resolver el caso `S_ATC_PROBE_BUFFER`.** Dos fuentes dan dos valores y el ISA
   duplica un opcode entre dos nombres. Elegir una sería asumir. `NOT_DETERMINED`.

5. **No se puede concluir nada de la contradicción viva.** Ver §6.

6. **No se puede usar ninguna de las 216 como autoridad de valor.** Este nodo no ha ganado nada
   sobre cuál fuente es correcta; ha ganado **una intersección** y **una lista de huecos**.

7. **No cubre el resto del universo de opcode GFX8.** Los 216 son el prefijo `SQ_S_*`. El capítulo 12
   sí tiene las 5 tablas de opcode de los formatos vector-memoria (§2(a), Tablas 12.7/12.8/12.9/12.12/
   12.13) que corresponden a `SQ_LDS_*`, `SQ_MUBUF_*`, `SQ_MTBUF_*`, `SQ_MIMG_*`, `SQ_FLAT_*`. Queda
   **fuera de la pregunta de este nodo** y **sin medir**. Quien mida esas debe saber que ya están
   localizadas (PDF 267-284) y son tablas de verdad, no líneas sueltas.

8. **Riesgo de reproducibilidad declarado:** la cuenta depende de tolerar las formas `(0x 30)` y `(C)`
   del PDF (§2). Con regex estricta se obtiene 182 y una lista de 3 "ausentes" falsa. Cualquiera que
   replique esto con una regex estricta está midiendo el parser, no la cobertura.

---

## 6. CONTRADICCION_viva — NO se cierra

`CONTRAD-Q5-AUSENCIA-TABLAS`, los dos lados comprobados intactos antes y después de este nodo:

```
$ sha256sum 08-ARQUITECTURA/designs/DRIVER-MISSION-STATE.md
21f8ca0e346ea271494b050bd5b9ef4e4c0370f604e9da3baf25c0dd9c9a661b   (coincide con el fijado)
$ sha256sum 06-INGENIERIA-INVERSA/findings/968-q5-universo-de-tablas-gfx8.md
f46e67e251c0295545d2845893e2e009467e521db7dcfd56d23c0d544e14f8d2   (coincide con el fijado)
```

**Ninguno de los dos ficheros fue modificado.** No los toqué, no los leo para reescribir, no voté.

**Dónde apoya mi medición — y es un apoyo parcial, no un fallo:**

- Apoya al lado **AFIRMA (DRIVER-MISSION-STATE.md:136-138)** en un punto concreto y verificable: para
  las familias escalares **no hay una tabla de opcode en el corpus**. El capítulo 12 solo trae 5 tablas
  "for the Opcode Field" y ninguna es de SOP1/SOP2/SOPK/SOPC/SOPP/SMEM (§2(a)). Lo que trae para
  escalares son 187 líneas aisladas bajo títulos `Instruction`. La forma que la afirmación describe
  ("4 de las 5 tablas no están") no aparece en esta fuente ni en esa forma.
- Apoya al lado **REFUTA (findings/968)** en otro punto, también verificable: la **correspondencia
  opcode → valor existe y es medible para 185 de 216 entradas**, con página de procedencia. La
  afirmación de que "la tabla que faltaba tampoco lo resolvía" (reconciliación Q5) queda **confirmada
  en su consecuencia**: la tabla, donde existe, no cubre el bloque de 28 atómicos SMEM, que es
  precisamente el contenido que faltaba.

**Dónde NO apoya a ninguno:** este nodo no ha medido la existencia de las "5 tablas" como las define el
finding 968 (esas son subconjuntos por prefijo dentro del mismo fichero, criterio de `DEFINITION`
distinto del mío, que es el formato de sección del ISA). No he medido la otra mitad de la afirmación
—los campos de operando y registro— porque no era la pregunta de este nodo. Mi resultado **no vota**
en la contradicción.

**Límite que arrastra mi voto:** el input principal está fuera del root canónico sin versionar
(LIMITACION_1). Un voto que depende de un input no trazado no puede cerrar una contradicción
documental. **Aporto un tercer dato, no un veredicto.**

---

## 7. Limitaciones que se declaran, no se ocultan

**LIMITACION_1 — input fuera del árbol activo, sin versionar.** El PDF vive en
`/home/lucas/Descargas/RX550-INVESTIGACION/05-FUENTES-PDF/gcn3-isa.pdf`. La cita M-01 de
`RESEARCH/polaris12xl/LIBRARY-CATALOG.md:630` apunta a
`RX550-INVESTIGACION/05-FUENTES-PDF/gcn3-isa.pdf`, que **no resuelve dentro del root canónico**: la
ruta del catálogo es relativa y el fichero real cuelga de `~/Descargas`. **Todo este resultado depende
de un input no trazado dentro del proyecto.** Se ha verificado su hash contra el fijado, lo que fija
*qué* bytes se midieron, pero no lo *trazabiliza* dentro del árbol. **No he copiado el PDF al root**:
esa decisión no es mía y no está tomada. Si el fichero de `~/Descargas` cambia, este informe queda
sin entrada reproducible aunque su hash siga registrado aquí.

**LIMITACION_2 — riesgo de generación no controlable.** `vega-isa.pdf` está en la misma carpeta externa
y **no se ha abierto**, según instrucción. Consecuencia registrada: **si el capítulo 12 resultara no
discriminable entre GCN3 y otra generación, eso es un límite de ALCANCE del input, no una refutación
de H1.** En esta medición el problema se manifiesta así: el documento nunca dice "GFX8" y solo se
autodenomina "Volcanic Islands". Los 31 ausentes son precisamente un bloque cuya atribución de
generación no puedo discriminar. Este límite pesa **enteramente sobre §5.3**.

**LIMITACION_3 — IMPLEMENTATION_IS_NOT_AUTHORITY en los dos sentidos.**
(a) `gfx_8_0_enum.h` es evidencia **sobre una implementación**, no verdad del silicio: el fichero lo
genera una familia de scripts y puede contener errores,rellenos o fechas de congelación que nadie
contrastó. No he auditado cómo se generó ni con qué ASIC se calibró.
(b) La ISA de AMD es un documento de proveedor: mejor que un header de driver, pero **no medido contra
esta placa**. Es documentación, no observación.
(c) **Las 2 discrepancias se REGISTRAN con las dos fuentes y NO se resuelven eligiendo una** (§3.4).

**LIMITACION_4 — alcance del universo.** Los 216 son el prefijo `SQ_S_*`. El capítulo 12 cubre además
VOP/VOPC/VOP3/VINTRP/DS/MUBUF/MTBUF/MIMG/EXP/FLAT, fuera del universo de este nodo y **no medidos**
(§5.7). La cobertura de 185/216 **no** es la cobertura del opcode GFX8 entero.

**LIMITACION_5 — el instrumento es una regex, no un validador.** La extracción es determinista y
reproducible desde `cap12.txt` (sha256 registrado), pero su corrección depende de tolerar las formas
`(0x 30)` y `(C)`. No hay auto-test ni cross-check independiente; el único control es que **las 485
líneas parsean** y que **216 = 185 + 31** cuadra por construcción. Heredar el precedente de
`DRIVER-MISSION-STATE.md` (la herramienta que "no podía fallar"): **esta medición puede no fallar si el
universo se define mal**, y aquí el universo lo fijó el nodo, no un instrumento. El residuo de §5 es la
salida.

---

## 8. Estado final

```
AGENT_ID            = subagent (nodo dispatched por sesion-missing)
NODE_ID             = Q5-ISA-CAP12
STATE_BEFORE        = Q5 bloqueada por DRIVER-MISSION-STATE.md:136-138
HECHO               = capitulo 12 identificado (PDF 107-284 = impresas 12-1..12-178) por 3 vias;
                      correspondencia opcode->valor extraida y medida contra las 216
STATE               = RESOLVED_WITH_RESIDUAL_UNIVERSE
HIPOTESIS           = H2 (COBERTURA PARCIAL). H1 y H3 refutadas por discriminante.
COBERTURA           = 185/216 con valor · 31 ausentes · 0 a medias · 183 coinciden · 2 difieren
RESIDUAL_UNIVERSO   = 28 S_BUFFER_ATOMIC_* + S_MOV_REGRD_B32 + S_MOV_FED_B32
                      + S_GETREG_REGRD_B32 + S_WAKEUP + S_RFE_RESTORE_B64
INPUT_HASHES        = gcn3-isa.pdf 8e49a376…2853 (2752924 B)
                      gfx_8_0_enum.h fa6b8ff9…d63 (376576 B) x4 copias identicas
OUTPUT_HASH         = ver tabla de §1.4 (cap12.txt 877b9202…df8;
                      cap12-opcodes-all.tsv a42d1538…88d; coverage-216.tsv 175ce7da…85e5)
SCRIPTS_MODIFIED    = ninguno
GPU_TOCADA          = NO     RUNTIME=NOT_RUN     SUDO=NO     COMMITS=NINGUNO
CONTRAD_MODIFICADA  = NO (hashes re-verificados intactos)
```

**ACCION_DISCRIMINANTE siguiente** (no ejecutada, fuera de mi alcance): medir la cobertura de las
**5 tablas de opcode que el capítulo 12 sí trae completas** (Tablas 12.7/12.8/12.9/12.12/12.13,
PDF 267-284) contra los prefijos `SQ_LDS_*`, `SQ_MUBUF_*`, `SQ_MTBUF_*`, `SQ_MIMG_*`, `SQ_FLAT_*`.
Es el mismo método ya VALIDADO aquí, sobre familias donde la fuente **sí** está en forma de tabla. Si
también da cobertura alta, la conclusión operativa es que **la fuente primaria cubre las familias
escalares y de memoria pero no el bloque de atómicos SMEM**, y el bloqueo de Q5 no es "la tabla que
faltaba" sino, como ya escribió la reconciliación, la cabecera de paquete PM4 para el CP.

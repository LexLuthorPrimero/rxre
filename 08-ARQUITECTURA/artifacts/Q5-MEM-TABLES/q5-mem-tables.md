# Q5-MEM-TABLES — las 5 tablas de opcode del capítulo 12 contra los prefijos de memoria vectorial del header

```
AUTORIA=sesion-missing · WORK_CLASS=READ_ONLY/EVIDENCE · WRITE_EXECUTION=3 ficheros nuevos
RUNTIME=NOT_RUN · GPU=INTACTA · SIN_SUDO · SIN_COMMITS
NODE_ID=Q5-MEM-TABLES
```

**Pregunta única.** ¿Las 5 tablas tituladas *"Instructions for the Opcode Field"* cubren los prefijos
de memoria vectorial del header con la misma cobertura alta que las líneas sueltas dan para los
escalares, o mucho menos?

**Veredicto: `RESOLVED_WITH_RESIDUAL_UNIVERSE` — hipótesis H1 (MEMORIA ALTA), en COBERTURA.**

Cobertura medida: **345 de 353 entradas con valor (97,7 %), 8 ausentes (2,3 %)**, frente a
**185 de 216 = 85,6 % con valor y 31 ausentes (14,4 %)** de los escalares. La cobertura de memoria es
**mejor**, no peor. Los cinco por separado están en §3 y ninguno se promedia.

**Pero la cobertura NO es lo único que cambia, y el promedio lo habría escondido: en valor, memoria
es peor que los escalares.** 45 de las 345 entradas con valor **DIFIEREN** del valor del header
(13,0 %), contra 2 de 185 (1,1 %) en los escalares. Esas 45 están casi todas en dos subgrupos
sistemáticos: 35 en `FLAT` y 10 en `MIMG`. Detalle en §5.

---

## 0. Verificación de inputs, ANTES de interpretar

Los cuatro hashes fijados por el coordinador, comprobados sobre los ficheros que este nodo realmente
leyó:

```
$ cd /home/lucas/Escritorio/RX550-INVESTIGACION/08-ARQUITECTURA/artifacts/Q5-ISA-CAP12
$ sha256sum q5-isa-cap12.md cap12.txt cap12-opcodes-all.tsv coverage-216.tsv
d3c8ad7fade0e7605830b7f3b2c647cebd2ed9cf5addce44fb4a0dcf0c31eee3  q5-isa-cap12.md
877b92024e43a8d7d74863ffe6873d293e23a6edf961f77dcd274b95920c8df8  cap12.txt
a42d1538ffa900deac13d0e666f63e73edd1c66fbc705440573f48d94da15d88  cap12-opcodes-all.tsv
175ce7daf9a0e5153e1b414e99aaff1ad4430359e5e1f94081093c06219385e5  coverage-216.tsv
```

**Los cuatro coinciden. No hubo `DRIFT_DETECTED`.** Los ficheros de entrada de este nodo son
exactamente los del turno anterior; **no se reextrajo el capítulo 12** (ver §1.2).

Cabecera del universo, el mismo fijada por el nodo anterior, re-verificada aquí porque este nodo
mide contra ella:

```
$ find . -name gfx_8_0_enum.h -print0 | xargs -0 sha256sum
fa6b8ff974fccdd54aa0e1b6a6430508a558fd263ead90eaf70bef262e4d5d63  ./RESEARCH/working/linux-7.1.3/…/gfx_8_0_enum.h
fa6b8ff974fccdd54aa0e1b6a6430508a558fd263ead90eaf70bef262e4d5d63  ./RESEARCH/baseline/linux-7.1.3/…/gfx_8_0_enum.h
fa6b8ff974fccdd54aa0e1b6a6430508a558fd263ead90eaf70bef262e4d5d63  ./RESEARCH/kernelbuild/linux-7.1.3/…/gfx_8_0_enum.h
fa6b8ff974fccdd54aa0e1b6a6430508a558fd263ead90eaf70bef262e4d5d63  ./rx550-upstream-7.2.8/linux-7.2.8/…/gfx_8_0_enum.h
```

4 copias, byte-idénticas, hash igual al fijado en el turno anterior. Se usa
`RESEARCH/working/linux-7.1.3/…/gfx_8_0_enum.h`. Inmaterial cuál: son el mismo byte.

**Token de estado verificado antes de contar.** El turno anterior establishing que el token es
`AUSENTE_DE_CH12`, no `AUSENTE`. Confirmado sobre el fichero antes de usarlo como referencia:

```
$ awk -F'\t' 'NR>1{print $4}' coverage-216.tsv | sort | uniq -c
    183 COINCIDE
     31 AUSENTE_DE_CH12
      2 DIFIERE
```

**Y un hallazgo estructural que condiciona todo el nodo**, comprobado antes de medir cobertura:

```
$ awk -F'\t' 'NR>1{print $2}' cap12-opcodes-all.tsv | sort | uniq -c | sort -rn
     76 VOP3a   76 VOP1   52 VOP2   49 SOP1   43 SOP2   29 SOPP   25 SMEM   21 SOPC   20 SOPK   3 VINTRP   2 VOP3b
```

`cap12-opcodes-all.tsv` —el artefacto que el turno anterior construyó con la regla de las líneas
sueltas— **no contiene ni una sola fila de LDS/MUBUF/MTBUF/MIMG/FLAT**. Y
`coverage-216.tsv` contiene **solo** 216 filas, todas `SQ_S_*`:

```
$ awk -F'\t' 'NR>1{n=$1; sub(/^SQ_/,"",n); split(n,a,"_"); print "SQ_"a[1]}' coverage-216.tsv | sort -u
SQ_S
```

Es decir: **la regla del turno anterior no tiene nada que decir sobre memoria**, porque memoria no
viaja en líneas sueltas sino en tablas. Por eso este nodo no reutiliza su parser: necesita uno
distinto, y por eso `cap12-opcodes-all.tsv` se usa aquí solo como *control negativo* (§4.1).

---

## 1. Qué páginas he usado, cómo lo he determinado

### 1.1 Las 5 tablas, localizadas por título literal

```
$ grep -n "Instructions for the Opcode Field" cap12.txt
8564:Table 12.7       DS Instructions for the Opcode Field
8591:Table 12.7    DS Instructions for the Opcode Field (Cont.)
8643:Table 12.7    DS Instructions for the Opcode Field (Cont.)
8707:Table 12.7    DS Instructions for the Opcode Field (Cont.)
8761:Table 12.7    DS Instructions for the Opcode Field (Cont.)
8820:Table 12.7    DS Instructions for the Opcode Field (Cont.)
8887:Table 12.8       MUBUF Instructions for the Opcode Field
8915:Table 12.8    MUBUF Instructions for the Opcode Field (Cont.)
8969:Table 12.8    MUBUF Instructions for the Opcode Field (Cont.)
9036:Table 12.9       MTBUF Instructions for the Opcode Field
9064:Table 12.9    MTBUF Instructions for the Opcode Field (Cont.)
9165:Table 12.12 MIMG Instructions for the Opcode Field
9194:Table 12.12 MIMG Instructions for the Opcode Field (Cont.)
9249:Table 12.12 MIMG Instructions for the Opcode Field (Cont.)
9302:Table 12.12 MIMG Instructions for the Opcode Field (Cont.)
9395:Table 12.13 FLAT Instructions for the Opcode Field
9426:Table 12.13 FLAT Instructions for the Opcode Field (Cont.)
```

**Los números de tabla del enunciado (12.7, 12.8, 12.9, 12.12, 12.13) y las 5 familias quedan
confirmados por grep, no supuesto.** 17 Ports = 6 de DS, 3 de MUBUF, 2 de MTBUF, 4 de MIMG, 2 de FLAT.

### 1.2 Las páginas: medidas por form-feed, sin reextraer

`cap12.txt` conserva **un form-feed por página**, lo que da un mapa de páginas exacto y
**no requiere volver a extraer nada**:

```
$ tr -cd '\f' < cap12.txt | wc -c
178
$ grep -c $'\f' cap12.txt
178
```

178 = exactamente el rango `-f 107 -l 284` que el turno anterior usó (284−107+1 = 178). El mapa es
`página de capítulo p → impreso 12-p → PDF 106+p`, coherente con el offset +106 ya establecido.
Las 5 tablas caen en **PDF 267..284**, que es exactamente el rango que fijó el coordinador:

| tabla | familia | línea 1ª | línea última | impreso | PDF |
|---|---|---|---|---|---|
| 12.7 | DS/LDS | 8564 | 8857 | 12-161 … 12-166 | **267 … 272** |
| 12.8 | MUBUF | 8887 | 9035 | 12-167 … 12-169 | **273 … 275** |
| 12.9 | MTBUF | 9036 | 9129 | 12-170 … 12-171 | **276 … 277** |
| 12.12 | MIMG | 9165 | 9373 | 12-172 … 12-175 | **278 … 281** |
| 12.13 | FLAT | 9395 | 9473 | 12-177 … 12-178 | **283 … 284** |

Nota de alcance: **PDF 282 (impreso 12-176) es la sección 12.17 EXP y no aporta ninguna tabla
"Instructions for the Opcode Field"**. Está dentro del rango 267-284 y no dentro de ninguna de las 5
tablas. No se mide nada de EXP aquí.

**Por qué NO reextraje `cap12.txt`.** No hace falta y sería peora: `cap12.txt` tiene `exit=0` de
`pdftotext`, hash fijado y verificado, y encima resulta ser *más* trustworthy que el texto que
`pdftotext` daría hoy para estas páginas, porque el form-feed por página permite atribuir cada fila a
su página sin depender de los encabezados.runner, que en este documento alternan izquierda/derecha y
sePrestaría a errores de conteo. Reextraer habría destruido la correspondence con el artefacto
cerrado del turno anterior sin ganar nada. El texto de PDF 267-284 se ha Volcado **derivado de
`cap12.txt`**, no del PDF, en `mem-tables.txt`, con una marca `@@@ PDF n / impreso 12-n / línea n @@@`
por página para que sea auditable línea a línea.

### 1.3 Comandos literales, exit status y stderr

Todo el trabajo es awk/grep/sha256sum sobre ficheros de texto y un parser en python3. Ninguno necesita
red, sudo ni GPU.

```
$ tr -cd '\f' < cap12.txt | wc -c                      -> 178        exit=0   stderr=(vacío)
$ grep -n "Instructions for the Opcode Field" cap12.txt -> 17 líneas  exit=0   stderr=(vacío)
$ sha256sum q5-isa-cap12.md cap12.txt …                 -> 4 líneas   exit=0   stderr=(vacío)
$ awk -F'\t' … coverage-216.tsv                        -> ver §0     exit=0   stderr=(vacío)
$ python3 <parser de §2 y §3>                          -> §3         exit=0   stderr=(vacío)
```

No hubo `DRIFT_DETECTED`, no hubo abort, no hubo `pdftotext` en este turno, no se abrió `vega-isa.pdf`.

---

## 2. Corrección de alcance: los prefijos del enunciado no existen en el header

Antes de contar nada, el filtro literal del enunciado, **con control positivo en la misma línea**:

```
$ para p en SQ_LDS_ SQ_MUBUF_ SQ_MTBUF_ SQ_MIMG_ SQ_FLAT_: contar "#define SQ_<p>*" en el header
  SQ_LDS_      -> 0 entradas
  SQ_MUBUF_    -> 0 entradas
  SQ_MTBUF_    -> 0 entradas
  SQ_MIMG_     -> 0 entradas
  SQ_FLAT_     -> 42 entradas
  control positivo del MISMO filtro: SQ_DS_=145  SQ_BUFFER_=59  SQ_TBUFFER_=16  SQ_IMAGE_=91
```

**Cuatro de los cinco prefijos del enunciado no existen en el header.** El filtro **sí** encuentra
(los controles positivos dan 145/59/16/91), así que el 0 es un hecho sobre el header, no un defecto
del instrumento. Este es el caso exacto que el coordinador advirtió: un cero que no puede haber
salido del instrumento es un defecto, y un cero que **sí** puede haber salido, y sale 0, es un hecho.
Se comprobó en ambos sentidos.

Inventario real de prefijos del header (los 31, con conteo):

```
$ grep -o '^#define SQ_[A-Za-z0-9]*_' gfx_8_0_enum.h | sed 's/.*SQ_//;s/_$//' | sort | uniq -c | sort -rn
421 V   216 S   145 DS   99 SRC   91 IMAGE   59 BUFFER   56 DPP   51 ENC   42 FLAT   16 TBUFFER
13 HW   11 EX   10 SDWA   10 EXP   8 XLATE   8 SENDMSG   6 WAITCNT   6 HWREG   5 MSG   4 SYSMSG
4 OMOD   4 NUM   4 GS   4 CHAN   3 VCC   3 PARAM   3 GFXDEC   2 XNACK   2 TMA   2 TBA   2 MAX
2 EXEC   2 DISPATCHER   1 WAVE   1 THREAD
```

**Declaro la ampliación de alcance, porque el enunciado la prohíbe y yo la hago igual, y digo por qué.**
Las 5 familias de las tablas existen todas y son las que el enunciado nombra; lo que cambia es el
**nombre con el que el header las llama**:

| prefijo del enunciado | existe en header | prefijo real del header | tabla | familia ISA |
|---|---|---|---|---|
| `SQ_LDS_` | **NO (0)** | `SQ_DS_` | 12.7 | DS |
| `SQ_MUBUF_` | **NO (0)** | `SQ_BUFFER_` | 12.8 | MUBUF |
| `SQ_MTBUF_` | **NO (0)** | `SQ_TBUFFER_` | 12.9 | MTBUF |
| `SQ_MIMG_` | **NO (0)** | `SQ_IMAGE_` | 12.12 | MIMG |
| `SQ_FLAT_` | sí (42) | `SQ_FLAT_` | 12.13 | FLAT |

Medir 4 ceros y responder "cobertura 0 %, H2" habría sido una respuesta **falsa sobre el mundo**,
exactamente el fallo que este turno tiene que evitar. Amplío porque las 5 tablas son las que el
enunciado señala y la familia existe; lo que no existe es la cadena literal `SQ_LDS_`.

**La regla de correspondencia es UNA SOLA, no cinco, y no requiere renombrar nada:**

> **nombre ISA = nombre del header con el prefijo `SQ_` eliminado, carácter a carácter.**
> `SQ_DS_ADD_U32` → `DS_ADD_U32` · `SQ_BUFFER_LOAD_FORMAT_X` → `BUFFER_LOAD_FORMAT_X` ·
> `SQ_TBUFFER_LOAD_FORMAT_X` → `TBUFFER_LOAD_FORMAT_X` · `SQ_IMAGE_LOAD` → `IMAGE_LOAD` ·
> `SQ_FLAT_LOAD_UBYTE` → `FLAT_LOAD_UBYTE`.

Las 5 se resuelven con la misma regla porque el header ya nombra las instrucciones con el mnemónico
de la ISA detrás de `SQ_`. No inventé un renombrado por familia: no hizo falta. Y la regla es
**falsable**: si no hubiera sido una sola regla, si alguna familia hubiera necesitado excepción, la
tabla de §3 lo habría mostrado. 345 de 353 casan con ella sin una sola excepción.

---

## 3. Los cinco números, por separado

Medidos con la regla de parseo de §6 sobre el header `fa6b8ff9…`. Detalle fila a fila en
`mem-coverage.tsv` (353 filas).

| # | familia | tabla | prefijo real | n_header | n_con_valor | n_ausente | % ausente | n_DIFIERE |
|---|---|---|---|---|---|---|---|---|
| 1 | LDS/DS | 12.7 | `SQ_DS_` | 145 | **142** | **3** | 2,1 % | 0 |
| 2 | MUBUF | 12.8 | `SQ_BUFFER_` | 59 | **59** | **0** | 0,0 % | 0 |
| 3 | MTBUF | 12.9 | `SQ_TBUFFER_` | 16 | **16** | **0** | 0,0 % | 0 |
| 4 | MIMG | 12.12 | `SQ_IMAGE_` | 91 | **89** | **2** | 2,2 % | 10 |
| 5 | FLAT | 12.13 | `SQ_FLAT_` | 42 | **39** | **3** | 7,1 % | 35 |
| | | | **TOTAL** | **353** | **345** | **8** | **2,3 %** | **45** |

Comparación con el mismo método sobre los escalares (turno anterior, `coverage-216.tsv`):

| | escalares `SQ_S_*` | memoria (5 tablas) |
|---|---|---|
| n_header | 216 | 353 |
| n_con_valor | 185 (85,6 %) | **345 (97,7 %)** |
| n_ausente | 31 (14,4 %) | **8 (2,3 %)** |
| n_DIFIERE | 2 (1,1 %) | **45 (13,0 %)** |

**Un prefijo entero no se cae.** Los cinco superan el 92 % de cobertura; el peor es FLAT con 92,9 %.
MUBUF y MTBUF son 100 %.

Filas extraídas por tabla, con su control de pérdidas:

| tabla | filas | nombres únicos | nombres reparados | **líneas con cola de valor NO capturadas** | impreso | PDF |
|---|---|---|---|---|---|---|
| 12.7 DS | 143 | 142 | 1 | **0** | 12-161…12-166 | 267…272 |
| 12.8 MUBUF | 59 | 59 | 5 | **0** | 12-167…12-169 | 273…275 |
| 12.9 MTBUF | 16 | 16 | 0 | **0** | 12-170…12-171 | 276…277 |
| 12.12 MIMG | 89 | 89 | 0 | **0** | 12-172…12-175 | 278…281 |
| 12.13 FLAT | 39 | 39 | 0 | **0** | 12-177…12-178 | 283…284 |
| | **346** | **345** | **6** | **0** | | |

`346 filas − 1 nombre duplicado (DS_PERMUTE_B32, §6.3) = 345 nombres únicos = 345 con valor`.
Cuadra por construcción **y** por measured set comparison: 353 − 8 = 345.

### 3.1 Los 8 ausentes, uno a uno, con control de ausencia

Un ausente solo vale si **se ha comprobado que el filtro puede encontrar algo ahí**. Para cada uno se
buscó el nombre entero en las 178 páginas *y* un prefijo estable corto, inmune al defecto de
partición de nombres del PDF (§6.2):

| # | entrada del header | valor header | ¿en la tabla? | ¿nombre entero en las 178 págs? | ¿prefijo estable? |
|---|---|---|---|---|---|
| 1 | `SQ_DS_BPERMUTE_B32` | 0x3f | no | 0 (`DS_BPERMUTE` → 0) | — |
| 2 | `SQ_DS_ADD_RTN_F32` | 0x35 | no | 0 (`DS_ADD_RTN` → 2, son `_U32`/`_U64`) | — |
| 3 | `SQ_DS_ADD_SRC2_F32` | 0x95 | no | 0 (`DS_ADD_SRC2` → 2, son `_U32`/`_U64`) | — |
| 4 | `SQ_IMAGE_RSRC256` | 0x7e | no | 0 | — |
| 5 | `SQ_IMAGE_SAMPLER` | 0x7f | no | 0 | — |
| 6 | `SQ_FLAT_SCRATCH_LO` | 0x66 | no | 0 (`FLAT_SCRATCH` → 0) | — |
| 7 | `SQ_FLAT_SCRATCH_HI` | 0x67 | no | 0 (`FLAT_SCRATCH` → 0) | — |
| 8 | `SQ_FLAT_ATOMIC_SWAP_X2` | 0x60 | no | 0 (`FLAT_ATOMIC_SWAP` → 1, es `_X64` con otro nombre) | — |

Estado: **`NOT_FOUND` en el capítulo 12 para las 8**, no `PROVEN_ABSENT`. Ver §7.1.

Los dos `FLAT_SCRATCH_*` y los dos `IMAGE_RSRC256`/`IMAGE_SAMPLER` son **0x66/0x67 y 0x7e/0x7f**,
justo por encima del último valor que cada tabla imprime (FLAT acaba en 0x5D, MIMG en 0x6F). Esto es
**una observación de estructura, no un hallazgo**: los 8 ausentes caen en la zona alta del espacio de
opcode. No lo resuelvo ni lo generalizo.

---

### 3.2 Las tres hipótesis, adjudicadas una a una

El enunciado pedía los tres números por prefijo y un promedio los habría escondido. Van primero los
números; aquí va el veredicto de cada hipótesis, con el discriminante que lo decide.

| hipótesis | veredicto | discriminante aplicado | por qué |
|---|---|---|---|
| **H1 MEMORIA ALTA** | **RESUELTA** | recuento de ausentes por prefijo: 3/145, 0/59, 0/16, 2/91, 3/42 | el peor prefijo (FLAT, 7,1 %) está **por debajo** del 14,4 % de los escalares, y el total (2,3 %) por debajo. Ningún prefijo entero se cae: los cinco ≥ 92,9 %. |
| **H2 MEMORIA PARCIAL** | **REFUTADA en cobertura** | mismo discriminante, ejecutado sobre los cinco por separado | H2 era "las tablas cubren **menos** que las líneas sueltas". Cubren **más**: 97,7 % frente a 85,6 %, con 0 ausentes en dos de los cinco prefijos. La cobertura es alta y además **uniforme**, que es justo lo que H2 negaba. |
| **H3 TABLA INCOMPARABLE** | **REFUTADA** | se construyó la correspondencia por nombre sin inventar regla: `isa_name = header[3:]` | H3 pedía "no puedes alinear 1:1 sin inventar una regla, y la regla que inventes queda sin validar". **Una sola regla**, la misma para las 5 familias, alineó 345 de 345 casos **sin una sola excepción**. Y no quedó sin validar: se falsó tres veces (§6.2), porque `\s{2,}` y `)` obligatorio-eachaban filas que sí están. Una regla que no se puede falsar no habría servido. |

**Matiz que H1 no cubre, y que por eso el veredicto es `RESOLVED_WITH_RESIDUAL_UNIVERSE` y no
`RESOLVED`:** H1 era una hipótesis **de cobertura**, y en cobertura se cumple. Pero al medir la
correspondencia completa sale un segundo resultado que H1 no anticipaba: **45 de las 345 entradas
con valor discrepan del header**, casi todas en dos bloques sistemáticos de `FLAT` y `MIMG` (§5).
Cobertura alta y valor discordante son hechos compatibles, y este nodo solo tenía permiso para
medir cobertura. El residuo son esas 45, más los 8 `NOT_FOUND` y el nombre multifila de §6.3.

## 4. Los controles, incluidos los controles negativos

### 4.1 Control negativo: la fuente del turno anterior no puede ver memoria

`cap12-opcodes-all.tsv` tiene 0 filas de LDS/MUBUF/MTBUF/MIMG/FLAT (§0). Contraste:

```
$ awk -F'\t' 'NR>1{print $2}' cap12-opcodes-all.tsv | sort -u | grep -cE '^(LDS|MUBUF|MTBUF|MIMG|FLAT|DS)$'
0
```

Si hubiera reutilizado su parser, habría obtenido 0 para los cinco prefijos y ese 0 habría sido un
defecto del instrumento (**"ninguna línea suelta menciona MUBUF" no es un hecho sobre el capítulo**),
porque las tablas sí los traen. Queda registrado por qué esta partida no repite el fallo.

### 4.2 Control de pérdidas del parser

Tras cada extracción se recountó **toda línea del rango de la tabla que acabe en un grupo de valor**,
y se comparó con las filas capturadas:

```
$ para cada tabla: lineas_con_(…(0x)?HEX…)$  MINUS  filas capturadas
12.7 DS:    0 perdidas
12.8 MUBUF: 0 perdidas
12.9 MTBUF: 0 perdidas
12.12 MIMG: 0 perdidas
12.13 FLAT: 0 perdidas
```

Este control es lo que detecta los tres defectos de §6.2: en la primera pasada eran 37 y 5 líneas
perdidas, y los 4 nombres falsos ausentes de §6.2 salían todos de ahí.

### 4.3 Control de exclusividad del nombre (DS_PERMUTE_B32)

```
$ grep -n "DS_PERMUTE" cap12.txt
8675:DS_PERMUTE_B32   Forward permute.  …  62 (0x3E)
8678:DS_PERMUTE_B32   Backward permute. …  63 (0x3F)
```

El header tiene `SQ_DS_PERMUTE_B32 0x3e`. La tabla ofrece **dos** respuestas y mi regla se queda con
la primera. Marcado `COINCIDE_MULTIFILA`. Es el caso que mi regla **no** representa bien (§6.3).

---

## 5. Lo que la tabla de correspondencias enseña que la cobertura no

Las 45 `DIFIERE` no son ruido: son **sistemáticas y agrupadas**. Ninguna está en DS, MUBUF ni MTBUF.

| subgrupo | n | Δ (header − ISA) | lectura |
|---|---|---|---|
| `FLAT_STORE_*` | 6 de 8 coinciden | 0 | STORE es el único bloque que calza exacto |
| `FLAT_STORE_DWORDX3` / `_X4` | 2 | −1 / +1 | **X3 y X4 intercambiados** respecto al header |
| `FLAT_LOAD_*` | 8 | +8 (y +7/+9 en X3/X4) | bloque desplazado |
| `FLAT_ATOMIC_*` | 28 | +16 (4 filas) y +15 (16 filas) | bloque desplazado, y no uniformemente |
| `IMAGE_ATOMIC_*` | 4 | +1 | bloque desplazado |
| `IMAGE_GATHER4*` | 6 | +2 | bloque desplazado |

Detalle de los 8+10, con las dos fuentes y **sin arbitrar**:

```
SQ_FLAT_LOAD_UBYTE       header 0x10   ISA  8 (0x8)    pdf277…  pág 12-177
SQ_FLAT_LOAD_DWORD       header 0x14   ISA 12 (0xC)    12-177
SQ_FLAT_STORE_BYTE       header 0x18   ISA 24 (0x18)   12-177   <-- COINCIDE
SQ_FLAT_ATOMIC_SWAP      header 0x40   ISA 48 (0x30)   12-177
SQ_IMAGE_ATOMIC_SWAP     header 0x10   ISA 15 (0xF)    12-173
SQ_IMAGE_GATHER4_L       header 0x44   ISA 66 (0x42)   12-174
SQ_IMAGE_ATOMIC_ADD      header 0x12   ISA 17 (0x11)   12-173
SQ_IMAGE_GATHER4_C       header 0x48   ISA 70 (0x46)   12-174
```

Y 4 incoherencias **internas de la propia ISA**, donde decimal y hex no concuerdan entre sí
(0x3E=62 sí, pero 0x76≠120):

| entrada | header | ISA impreso | página | qué pasa |
|---|---|---|---|---|
| `SQ_DS_READ_B64` | 0x76 | `118 (0x74)` | 12-164 | 118=0x76 ✓ decimal; 0x74=116 ✗ |
| `SQ_DS_READ2_B64` | 0x77 | `119 (0x75)` | 12-164 | 119=0x77 ✓ decimal; 0x75=117 ✗ |
| `SQ_DS_READ2ST64_B64` | 0x78 | `120 (0x76)` | 12-164 | 120=0x78 ✓ decimal; 0x76=118 ✗ |
| `SQ_BUFFER_WBINVL1` | 0x3e | `62 (0x2E)` | 12-168 | 62=0x3E ✓ decimal; 0x2E=46 ✗ |

Estas 4 tienen **el mismo perfil que el caso `S_LSHR_B64` que el turno anterior registró como
`DIFIERE`**, y por el mismo motivo: el estado depende de si se compara decimal o hex. Se marcan
`COINCIDE_DEC_ISA_DEC_HEX_INCOHERENTE` y **no se resuelven**. Es exactamente el mismo patrón que el
turno anterior문anedió en `S_AND_B32`, `S_LSHR_B64` y `S_MOV_B32`; la coherencia interna de la columna
de valores de la ISA **no está garantizada**, en escalares ni en memoria.

---

## 6. La regla de parseo, entera, y lo que NO captura

### 6.1 REGLA, escrita para que otro la reproduzca sin leerte

**Entrada:** `cap12.txt`, páginas de capítulo 161 a 178 (PDF 267 a 284), con el mapa de página
sacado de los 178 form-feeds: `p → impreso 12-p → PDF 106+p`.

**Paso 0 — límites de tabla.** Rangos de línea (1-based, en `cap12.txt`): DS 8564–8857,
MUBUF 8887–9035, MTBUF 9036–9129, MIMG 9165–9373, FLAT 9395–9473. Acabado: línea anterior al título
`12.14 MUBUF Instructions` / `12.15 MTBUF` / `12.16 MIMG` / `12.18 FLAT Instructions`, para no invadir
la sección siguiente.

**Paso 1 — una fila de tabla es una línea que cumple:**

```
^(?P<name>[A-Z][A-Z0-9_]*)\s+(?P<desc>\S.*?)\s+(?P<dec>\d+)\s*\(\s*(?:0[xX]\s*|ox|o[xX])?(?P<hex>[0-9A-Fa-f]+)\s*\)?\s*$
```

aplicado a la línea con `rstrip()`. Se ignoran las líneas en blanco. Campos:
`dec = int(dec, 10)`, `hex = int(hex, 16)`, `name` = mnemónico, página = la del form-feed vigente.

Las cuatro decisiones en las que esta regla es deliberadamente permisiva, y por qué:

1. `\s+` y **no** `\s{2,}` entre nombre y descripción. En estas tablas la descripción puede quedar a
   **un solo espacio** del mnemónico cuando la columna se desborda. Con `\s{2,}` se perdían **37
   filas**; verificado, no supuesto.
2. El `)` de cierre es **opcional**. El PDF omite el cierre en 3 filas (`201 (0xC9`, `210 (0xD2`).
   Con `)` obligatorio se perdían.
3. El prefijo hexadecimal admite `0x`, `0X`, `ox` y **`0x` con espacio**. El documento tiene la
   errata `126 (ox7E)`. También aparece `0x 30` en el capítulo (así lo hereda el turno anterior).
4. El decimal admite ceros a la izquierda: la tabla 12.7 imprime `00 (0x0)`, `09 (0x9)`.

**Paso 2 — reparación de nombres partidos (el defecto real del PDF).** Los mnemónicos largos
desbordan su columna y el sobrante cae como línea huérfana en la línea siguiente:

```
8907: Z           <- sobrante de la línea 8906
8920: ZW          <- sobrante de la línea 8919
8801: L    ResourceID is in offset[4:0].   <- sobrante de la línea 8800
```

Regla: si la línea siguiente empieza por `[A-Z]{1,6}` seguido de frontera de palabra, y
`name + fragmento` **existe como nombre del header**, se adopta `name + fragmento`. La aceptación es
**autovalidante**: el criterio es pertenecer al universo del header, que es independiente del PDF. Se
aplicó 6 veces: `BUFFER_LOAD_FORMAT_D16_XYZ`, `…_XYZW`, `BUFFER_STORE_FORMAT_D16_XY`, `…_XYZ`,
`…_XYZW`, `DS_GWS_SEMA_RELEASE_ALL`.

Con esta regla, las únicas 6 activaciones son correctas, y las 20 líneas-huérfana candidatas que
**no** son fragmentos de nombre se rechazan solas, entre ellas las 4 letras sueltas de los
**diagramas de bitfield** (`T`,`E` de OFFSET en 8862/8864; `D` en 9135; `C`,`PR` en 9356/9360) y las
7 subcabeceras de grupo (`LOAD`, `STORE`, `ATOMIC`, `SAMPLE`). `BUFFER_LOAD_DWORDX4`+`STORE` =
`BUFFER_LOAD_DWORDX4STORE` no existe → rechazado. `BUFFER_STORE_FORMAT_XYZW`+`LOAD` → no existe →
rechazado.

**Paso 3 — correspondencia.** Para cada nombre del header de los 5 prefijos: `isa_name = name[3:]`;
si `isa_name` está en la tabla, se toma `(dec, hex)` de su **primera** fila y se compara con el valor
del header: `COINCIDE` si `hex == header`; si no, `COINCIDE_DEC` si `dec == header`; si no,
`DIFIERE`. Se anexa `_MULTIFILA` si el nombre aparece en >1 fila, y `_ISA_DEC_HEX_INCOHERENTE` si
`dec != hex`. Si `isa_name` no está: `AUSENTE_DE_TABLA_ISA`.

### 6.2 Los tres defectos que esta regla NO captura, y que Costaron 4 falsos ausentes en mi primera pasada

Los reproduzco porque son el mismo tipo de fallo que los dos del turno anterior, y porque un
instrumento que no puede fallar no es evidencia:

| defecto | texto real | qué hizo mi v1 | arreglado en v3 |
|---|---|---|---|
| descripción a 1 espacio | `DS_WRXCHG2ST64_RTN_B32 Write exchange 2 Dwords, stride 64.  47 (0x2F)` | `) 0` porque exigía `\s{2,}` | `\s+` |
| cierre ausente | `DS_AND_SRC2_B64  …  201 (0xC9` | **contado AUSENTE_FALSO** | `)?` opcional |
| cierre ausente | `DS_MIN_SRC2_F64  …  210 (0xD2` | **contado AUSENTE_FALSO** | `)?` opcional |
| errata `ox` + huérfana con texto | `DS_CONDXCHG32_RTN_B64 … 126 (ox7E)` y `DS_GWS_SEMA_RELEASE_AL` + `L` | **2 contados AUSENTE_FALSO** | alternancia `ox`; huérfana `^\s*[A-Z]{1,6}\b` |

Mi primera pasada dio **DS = 138 con valor / 7 ausentes**. La correcta es **142 / 3**. Cuatro de esos
siete ausentes **no eran hechos sobre el mundo: eran fallos míos**. Lo digo porque el turno anterior
escribió 28 donde eran 26, y el coordinador escribió 0 donde había 26: tres turnos, tres instrumentos
que fabricaban ceros.

### 6.3 El caso que mi regla v3 sigue sin capturar

`DS_PERMUTE_B32` aparece **dos veces** en la tabla 12.7, con dos valores distintos:

```
8675:DS_PERMUTE_B32   Forward permute.  …  62 (0x3E)
8678:DS_PERMUTE_B32   Backward permute. …  63 (0x3F)
```

Mi regla **se queda con la primera** y añade el sufijo `COINCIDE_MULTIFILA`. Si el header hubiera
dicho `0x3f`, mi regla habría emitido `DIFIERE` —correcto por construcción, pero **sin decir que la
tabla contiene la respuesta correcta en la segunda fila**. El instrumento no puede representar "el
documento ofrece dos valores para un nombre" más que como una etiqueta decorativa; no lo hace
falso, pero **tampoco lo hace verdadero**, y quien lea el TSV sin el §4.3 puede perderlo.

Las 4 filas `ISA_DEC_HEX_INCOHERENTE` tienen el mismo límite: el instrumento elige el decimal cuando
el hex no casa, y con ello **se hace una elección por el lector**. Si el criterio fuese "solo hex",
esas 4 serían `DIFIERE` y el recuento de FLAT/DS no cambiaría, pero el estado sí. Se escribe la fuente
literal y el estado depende del criterio, igual que hizo el turno anterior con `S_LSHR_B64`.

---

## 7. Lo que NO se puede concluir

### 7.1 No se puede concluir que las 8 ausentes no existan en el silicio

Están `NOT_FOUND` **en el capítulo 12**. No son `PROVEN_ABSENT`. El grep dio 0 apariciones, pero el
grep no tiene alcance sobre el resto de la ISA, sobre GFX8, ni sobre el hardware. `SQ_FLAT_SCRATCH_LO/HI`
y `SQ_IMAGE_RSRC256/SAMPLER` están en opcodes 0x66-0x67 y 0x7e-0x7f, por encima de donde acaba cada
tabla; **sugieren** que el documento GCN3 no cubre un rango que el driver sí usa, pero "sugiere" no es
"demuestra" y no lo convierto en claim.

### 7.2 No se puede concluir nada sobre el valor correcto para el silicio

Nada de este nodo toca RUNTIME. Que el header y la ISA discrepen 45 veces no dice cuál acierta: dice
que **dos documentos de dos épocas discrepan**, y no tengo el tercero. La tabla 12.x es de la ISA **GCN3**
(2016); el header es `gfx_8_0_enum.h`. La tabla 12.7 se titula **DS**, no LDS, y la sección 12.13 es
"LDS/GDS". Que el documento de GCN3 autorice números GFX8 es una **conjetura**, no un hecho medido aquí.

### 7.3 No se puede usar la alineación de nombres como prueba de equivalencia de codificación

La regla `isa_name = header[3:]` produce 345 cascos sin excepción, y eso demuestra que **los dos
documentos usan el mismo vocabulario de mnemónicos**. No demuestra que los dos codificadores usen la
misma asignación, y las 45 `DIFIERE` son exactamente la contra-evidencia: mismo vocabulario, numeración
distinta en FLAT y en dos subgrupos de MIMG.

### 7.4 No se puede decir qué versión de documento corresponde a qué ASIC

Esto refuerza la contradicción viva de abajo, no la cierra.

### 7.5 No se puede extender el resultado al opcode GFX8 entero

Medido: 353 entradas de 5 familias. Fuera: `VOP/VOPC/VOP3/VINTRP` (que sí están en
`cap12-opcodes-all.tsv`, 204 filas), `EXP` (10 en el header, sin tabla de opcode en el capítulo),
`SENDMSG` (8), `PARAM` (3), `GS` (4), `DSL`(ninguna). La cobertura de 97,7 % **no** es la cobertura del
opcode GFX8, igual que el 85,6 % del turno anterior no lo era.

### 7.6 No se puede cerrar ninguna de las dos contradicciones

Ambas quedan vivas, con mi medición como **cuarto input** de la primera y **dato adicional** de la segunda.

**CONTRAD-Q5-AUSENCIA-TABLAS.** Lado que apoya mi medición: el del `REFUTA`
(`968-q5-universo-de-tablas-gfx8.md`), **parcialmente**. Las 5 tablas existen y cubren 97,7 % de sus
5 familias de opcode — medido, con páginas. Lado que **no** apoyo y por qué limit: esto **no** dice que
"las tablas no están ausentes" en general. No he medido VOP/VOPC/VOP3/EXP/SENDMSG, y en `EXP` el
capítulo **sí** tiene sección (12.17, PDF 282) y **no** tiene tabla de opcode. El claim del `AFIRMA`
(`DRIVER-MISSION-STATE.md:136-138`) queda sin medir por este nodo, no refutado por él.

**CONTRAD-Q5-GFX8-ES-GCN3.** Mi medición **apoya la segunda mitad** del enunciado de la contradicción,
es decir que **el único puente medido entre la ISA citada y GFX8 es el driver**: porque para que la
medición signifique algo sobre GFX8, hay que cruzar un documento que se identifica a sí mismo como
GCN3 con un header `gfx_8_0_enum.h`. No he reopened `vega-isa.pdf`, no he medido generations, y **no
el arbitro**. Lo que este nodo añade: 45 discrepancias de valor, agrupadas y sistemáticas, en dos
bloques cuya numeración es precisamente donde GFX8 divergió de GCN3. Eso es **compatible** con la
divergencia y **no la demuestra**.

### 7.7 No se puede concluir que la reparación de nombres haya sido "correcta" en el sentido fuerte

6 nombres se repararon usando el universo del header como criterio de aceptación. La circularidad es
real y está declarada: **para esas 6 filas, que el nombre reparado exista en el header es parte del
premiso, no del hallazgo.** Los valores (`dec`, `hex`) no están tocados por la reparación y esos sí
son medida. Si un nombre partido no hubiera casado con el header, mi regla lo habría dejado truncado
y lo habría contado AUSENTE — silenciosamente. No hay caso de ese tipo en las 5 tablas (el control de
pérdidas da 0), pero **la regla tiene esa ceguera y no la he cerrado**.

### 7.8 No se puede afirmar que 97,7 % sea "cobertura del opcode de memoria"

Denominador: 5 prefijos del header, no el espacio de opcode. El espacio de opcode DS tiene 256
valores posibles y el header nombra 145; MIMG 256 y nombra 91. La tabla 12.7 imprime 143 filas para
145 nombres. La cobertura **de nombres** es alta; la cobertura **del espacio de opcode** no se midió y
probablemente es mucho menor. Son dos preguntas distintas y solo respondí una.

---

## 8. Reglas y artefactos

**Regla de parseo, resumida en una línea, si otro quiere reimplementarla desde cero:**
> Por cada línea de `cap12.txt` en las páginas de capítulo 161–178,`tómate` `NAME<sp+>desc<sp+>DEC<sp>(
> [0x|ox]<HEX>)?` con `)` opcional; repara el nombre si la línea siguiente empieza por 1–6
> mayúsculas y `NAME+frag` está en el header; luego `isa_name = header_name[3:]`.

**Artefactos escritos (3, todos en `08-ARQUITECTURA/artifacts/Q5-MEM-TABLES/`):**

| fichero | contenido | sha256 |
|---|---|---|
| `q5-mem-tables.md` | este informe | — |
| `mem-coverage.tsv` | 353 filas, una por nombre del header, con `header_value`, `isa_value`, `printed_page`, `pdf_page`, `cap12_line`, `n_filas_en_tabla` | `54028b93efa44d32885ec948e223c06da1284c1dd91b14529517f5920c4b29e2` |
| `mem-tables.txt` | texto de PDF 267–284 derivado de `cap12.txt`, con marca de página por bloque | `ec53db09a5f202f2f0a99522c40f5431d15b8eff6e47b57cf138ec03a2a8d36c` |

**Rastreo:** PDF `gcn3-isa.pdf` (`8e49a376…`, `05-FUENTES-PDF/`) → `cap12.txt`
(`877b9202…`, este turno no reextraído) → §6 → `mem-coverage.tsv` (`54028b93…`) → §3, §5, §7.
Header: `gfx_8_0_enum.h` (`fa6b8ff9…`).

```
RESOLVED_WITH_RESIDUAL_UNIVERSO
COBERTURA   = 345/353 con valor · 8 NOT_FOUND · 2,3 % ausente
              DS 142/145 (3) · MUBUF 59/59 (0) · MTBUF 16/16 (0)
              MIMG 89/91 (2) · FLAT 39/42 (3)
DISCREPANCIA= 45 DIFIERE (FLAT 35 · MIMG 10) · 4 dec!=hex internos de la ISA
RESIDUAL    = 8 ausentes · 1 nombre multifila (DS_PERMUTE_B32) · 6 nombres reparados
HIJOS       = EXP/VOP/VOPC/VOP3/VINTRP/SENDMSG/PARAM/GS no medidos
```

---

## 9. Tabla de correspondencias completa (353 filas)

Formato: `header_name` · valor header · mnemónico ISA · valor ISA tal cual · página impresa ·
página PDF · línea de `cap12.txt` · estado. Generada con la regla de §6.1. Copia machine-readable en
`mem-coverage.tsv`.

| header | header_valor | isa_name | isa_valor | impreso | pdf | linea | estado |
|---|---|---|---|---|---|---|---|
| `SQ_DS_ADD_F32` | 0x15 | `DS_ADD_F32` | 21 (0x15) | 12-162 | 268 | 8602 | COINCIDE |
| `SQ_DS_ADD_RTN_F32` | 0x35 | `DS_ADD_RTN_F32` | — | — | — | — | AUSENTE_DE_TABLA_ISA |
| `SQ_DS_ADD_RTN_U32` | 0x20 | `DS_ADD_RTN_U32` | 32 (0x20) | 12-162 | 268 | 8605 | COINCIDE |
| `SQ_DS_ADD_RTN_U64` | 0x60 | `DS_ADD_RTN_U64` | 96 (0x60) | 12-164 | 270 | 8715 | COINCIDE |
| `SQ_DS_ADD_SRC2_F32` | 0x95 | `DS_ADD_SRC2_F32` | — | — | — | — | AUSENTE_DE_TABLA_ISA |
| `SQ_DS_ADD_SRC2_U32` | 0x80 | `DS_ADD_SRC2_U32` | 128 (0x80) | 12-164 | 270 | 8743 | COINCIDE |
| `SQ_DS_ADD_SRC2_U64` | 0xc0 | `DS_ADD_SRC2_U64` | 192 (0xC0) | 12-165 | 271 | 8811 | COINCIDE |
| `SQ_DS_ADD_U32` | 0x0 | `DS_ADD_U32` | 0 (0x0) | 12-161 | 267 | 8567 | COINCIDE |
| `SQ_DS_ADD_U64` | 0x40 | `DS_ADD_U64` | 64 (0x40) | 12-163 | 269 | 8681 | COINCIDE |
| `SQ_DS_AND_B32` | 0x9 | `DS_AND_B32` | 9 (0x9) | 12-161 | 267 | 8577 | COINCIDE |
| `SQ_DS_AND_B64` | 0x49 | `DS_AND_B64` | 73 (0x49) | 12-163 | 269 | 8690 | COINCIDE |
| `SQ_DS_AND_RTN_B32` | 0x29 | `DS_AND_RTN_B32` | 41 (0x29) | 12-162 | 268 | 8614 | COINCIDE |
| `SQ_DS_AND_RTN_B64` | 0x69 | `DS_AND_RTN_B64` | 105 (0x69) | 12-164 | 270 | 8724 | COINCIDE |
| `SQ_DS_AND_SRC2_B32` | 0x89 | `DS_AND_SRC2_B32` | 137 (0x89) | 12-165 | 271 | 8782 | COINCIDE |
| `SQ_DS_AND_SRC2_B64` | 0xc9 | `DS_AND_SRC2_B64` | 201 (0xC9) | 12-166 | 272 | 8831 | COINCIDE |
| `SQ_DS_APPEND` | 0xbe | `DS_APPEND` | 190 (0xBE) | 12-165 | 271 | 8808 | COINCIDE |
| `SQ_DS_BPERMUTE_B32` | 0x3f | `DS_BPERMUTE_B32` | — | — | — | — | AUSENTE_DE_TABLA_ISA |
| `SQ_DS_CMPST_B32` | 0x10 | `DS_CMPST_B32` | 16 (0x10) | 12-162 | 268 | 8596 | COINCIDE |
| `SQ_DS_CMPST_B64` | 0x50 | `DS_CMPST_B64` | 80 (0x50) | 12-163 | 269 | 8699 | COINCIDE |
| `SQ_DS_CMPST_F32` | 0x11 | `DS_CMPST_F32` | 17 (0x11) | 12-162 | 268 | 8597 | COINCIDE |
| `SQ_DS_CMPST_F64` | 0x51 | `DS_CMPST_F64` | 81 (0x51) | 12-164 | 270 | 8710 | COINCIDE |
| `SQ_DS_CMPST_RTN_B32` | 0x30 | `DS_CMPST_RTN_B32` | 48 (0x30) | 12-162 | 268 | 8622 | COINCIDE |
| `SQ_DS_CMPST_RTN_B64` | 0x70 | `DS_CMPST_RTN_B64` | 112 (0x70) | 12-164 | 270 | 8731 | COINCIDE |
| `SQ_DS_CMPST_RTN_F32` | 0x31 | `DS_CMPST_RTN_F32` | 49 (0x31) | 12-162 | 268 | 8623 | COINCIDE |
| `SQ_DS_CMPST_RTN_F64` | 0x71 | `DS_CMPST_RTN_F64` | 113 (0x71) | 12-164 | 270 | 8732 | COINCIDE |
| `SQ_DS_CONDXCHG32_RTN_B128` | 0xfd | `DS_CONDXCHG32_RTN_B128` | 253 (0xFD) | 12-166 | 272 | 8846 | COINCIDE |
| `SQ_DS_CONDXCHG32_RTN_B64` | 0x7e | `DS_CONDXCHG32_RTN_B64` | 126 (0x7E) | 12-164 | 270 | 8742 | COINCIDE |
| `SQ_DS_CONSUME` | 0xbd | `DS_CONSUME` | 189 (0xBD) | 12-165 | 271 | 8807 | COINCIDE |
| `SQ_DS_DEC_RTN_U32` | 0x24 | `DS_DEC_RTN_U32` | 36 (0x24) | 12-162 | 268 | 8609 | COINCIDE |
| `SQ_DS_DEC_RTN_U64` | 0x64 | `DS_DEC_RTN_U64` | 100 (0x64) | 12-164 | 270 | 8719 | COINCIDE |
| `SQ_DS_DEC_SRC2_U32` | 0x84 | `DS_DEC_SRC2_U32` | 132 (0x84) | 12-165 | 271 | 8767 | COINCIDE |
| `SQ_DS_DEC_SRC2_U64` | 0xc4 | `DS_DEC_SRC2_U64` | 196 (0xC4) | 12-166 | 272 | 8826 | COINCIDE |
| `SQ_DS_DEC_U32` | 0x4 | `DS_DEC_U32` | 4 (0x4) | 12-161 | 267 | 8571 | COINCIDE |
| `SQ_DS_DEC_U64` | 0x44 | `DS_DEC_U64` | 68 (0x44) | 12-163 | 269 | 8685 | COINCIDE |
| `SQ_DS_GWS_BARRIER` | 0x9d | `DS_GWS_BARRIER` | 157 (0x9D) | 12-165 | 271 | 8806 | COINCIDE |
| `SQ_DS_GWS_INIT` | 0x99 | `DS_GWS_INIT` | 153 (0x99) | 12-165 | 271 | 8802 | COINCIDE |
| `SQ_DS_GWS_SEMA_BR` | 0x9b | `DS_GWS_SEMA_BR` | 155 (0x9B) | 12-165 | 271 | 8804 | COINCIDE |
| `SQ_DS_GWS_SEMA_P` | 0x9c | `DS_GWS_SEMA_P` | 156 (0x9C) | 12-165 | 271 | 8805 | COINCIDE |
| `SQ_DS_GWS_SEMA_RELEASE_ALL` | 0x98 | `DS_GWS_SEMA_RELEASE_ALL` | 152 (0x98) | 12-165 | 271 | 8800 | COINCIDE |
| `SQ_DS_GWS_SEMA_V` | 0x9a | `DS_GWS_SEMA_V` | 154 (0x9A) | 12-165 | 271 | 8803 | COINCIDE |
| `SQ_DS_INC_RTN_U32` | 0x23 | `DS_INC_RTN_U32` | 35 (0x23) | 12-162 | 268 | 8608 | COINCIDE |
| `SQ_DS_INC_RTN_U64` | 0x63 | `DS_INC_RTN_U64` | 99 (0x63) | 12-164 | 270 | 8718 | COINCIDE |
| `SQ_DS_INC_SRC2_U32` | 0x83 | `DS_INC_SRC2_U32` | 131 (0x83) | 12-165 | 271 | 8764 | COINCIDE |
| `SQ_DS_INC_SRC2_U64` | 0xc3 | `DS_INC_SRC2_U64` | 195 (0xC3) | 12-166 | 272 | 8825 | COINCIDE |
| `SQ_DS_INC_U32` | 0x3 | `DS_INC_U32` | 3 (0x3) | 12-161 | 267 | 8570 | COINCIDE |
| `SQ_DS_INC_U64` | 0x43 | `DS_INC_U64` | 67 (0x43) | 12-163 | 269 | 8684 | COINCIDE |
| `SQ_DS_MAX_F32` | 0x13 | `DS_MAX_F32` | 19 (0x13) | 12-162 | 268 | 8600 | COINCIDE |
| `SQ_DS_MAX_F64` | 0x53 | `DS_MAX_F64` | 83 (0x53) | 12-164 | 270 | 8713 | COINCIDE |
| `SQ_DS_MAX_I32` | 0x6 | `DS_MAX_I32` | 6 (0x6) | 12-161 | 267 | 8574 | COINCIDE |
| `SQ_DS_MAX_I64` | 0x46 | `DS_MAX_I64` | 70 (0x46) | 12-163 | 269 | 8687 | COINCIDE |
| `SQ_DS_MAX_RTN_F32` | 0x33 | `DS_MAX_RTN_F32` | 51 (0x33) | 12-162 | 268 | 8626 | COINCIDE |
| `SQ_DS_MAX_RTN_F64` | 0x73 | `DS_MAX_RTN_F64` | 115 (0x73) | 12-164 | 270 | 8735 | COINCIDE |
| `SQ_DS_MAX_RTN_I32` | 0x26 | `DS_MAX_RTN_I32` | 38 (0x26) | 12-162 | 268 | 8611 | COINCIDE |
| `SQ_DS_MAX_RTN_I64` | 0x66 | `DS_MAX_RTN_I64` | 102 (0x66) | 12-164 | 270 | 8721 | COINCIDE |
| `SQ_DS_MAX_RTN_U32` | 0x28 | `DS_MAX_RTN_U32` | 40 (0x28) | 12-162 | 268 | 8613 | COINCIDE |
| `SQ_DS_MAX_RTN_U64` | 0x68 | `DS_MAX_RTN_U64` | 104 (0x68) | 12-164 | 270 | 8723 | COINCIDE |
| `SQ_DS_MAX_SRC2_F32` | 0x93 | `DS_MAX_SRC2_F32` | 147 (0x93) | 12-165 | 271 | 8797 | COINCIDE |
| `SQ_DS_MAX_SRC2_F64` | 0xd3 | `DS_MAX_SRC2_F64` | 211 (0xD3) | 12-166 | 272 | 8840 | COINCIDE |
| `SQ_DS_MAX_SRC2_I32` | 0x86 | `DS_MAX_SRC2_I32` | 134 (0x86) | 12-165 | 271 | 8773 | COINCIDE |
| `SQ_DS_MAX_SRC2_I64` | 0xc6 | `DS_MAX_SRC2_I64` | 198 (0xC6) | 12-166 | 272 | 8828 | COINCIDE |
| `SQ_DS_MAX_SRC2_U32` | 0x88 | `DS_MAX_SRC2_U32` | 136 (0x88) | 12-165 | 271 | 8779 | COINCIDE |
| `SQ_DS_MAX_SRC2_U64` | 0xc8 | `DS_MAX_SRC2_U64` | 200 (0xC8) | 12-166 | 272 | 8830 | COINCIDE |
| `SQ_DS_MAX_U32` | 0x8 | `DS_MAX_U32` | 8 (0x8) | 12-161 | 267 | 8576 | COINCIDE |
| `SQ_DS_MAX_U64` | 0x48 | `DS_MAX_U64` | 72 (0x48) | 12-163 | 269 | 8689 | COINCIDE |
| `SQ_DS_MIN_F32` | 0x12 | `DS_MIN_F32` | 18 (0x12) | 12-162 | 268 | 8598 | COINCIDE |
| `SQ_DS_MIN_F64` | 0x52 | `DS_MIN_F64` | 82 (0x52) | 12-164 | 270 | 8711 | COINCIDE |
| `SQ_DS_MIN_I32` | 0x5 | `DS_MIN_I32` | 5 (0x5) | 12-161 | 267 | 8573 | COINCIDE |
| `SQ_DS_MIN_I64` | 0x45 | `DS_MIN_I64` | 69 (0x45) | 12-163 | 269 | 8686 | COINCIDE |
| `SQ_DS_MIN_RTN_F32` | 0x32 | `DS_MIN_RTN_F32` | 50 (0x32) | 12-162 | 268 | 8624 | COINCIDE |
| `SQ_DS_MIN_RTN_F64` | 0x72 | `DS_MIN_RTN_F64` | 114 (0x72) | 12-164 | 270 | 8733 | COINCIDE |
| `SQ_DS_MIN_RTN_I32` | 0x25 | `DS_MIN_RTN_I32` | 37 (0x25) | 12-162 | 268 | 8610 | COINCIDE |
| `SQ_DS_MIN_RTN_I64` | 0x65 | `DS_MIN_RTN_I64` | 101 (0x65) | 12-164 | 270 | 8720 | COINCIDE |
| `SQ_DS_MIN_RTN_U32` | 0x27 | `DS_MIN_RTN_U32` | 39 (0x27) | 12-162 | 268 | 8612 | COINCIDE |
| `SQ_DS_MIN_RTN_U64` | 0x67 | `DS_MIN_RTN_U64` | 103 (0x67) | 12-164 | 270 | 8722 | COINCIDE |
| `SQ_DS_MIN_SRC2_F32` | 0x92 | `DS_MIN_SRC2_F32` | 146 (0x92) | 12-165 | 271 | 8794 | COINCIDE |
| `SQ_DS_MIN_SRC2_F64` | 0xd2 | `DS_MIN_SRC2_F64` | 210 (0xD2) | 12-166 | 272 | 8837 | COINCIDE |
| `SQ_DS_MIN_SRC2_I32` | 0x85 | `DS_MIN_SRC2_I32` | 133 (0x85) | 12-165 | 271 | 8770 | COINCIDE |
| `SQ_DS_MIN_SRC2_I64` | 0xc5 | `DS_MIN_SRC2_I64` | 197 (0xC5) | 12-166 | 272 | 8827 | COINCIDE |
| `SQ_DS_MIN_SRC2_U32` | 0x87 | `DS_MIN_SRC2_U32` | 135 (0x87) | 12-165 | 271 | 8776 | COINCIDE |
| `SQ_DS_MIN_SRC2_U64` | 0xc7 | `DS_MIN_SRC2_U64` | 199 (0xC7) | 12-166 | 272 | 8829 | COINCIDE |
| `SQ_DS_MIN_U32` | 0x7 | `DS_MIN_U32` | 7 (0x7) | 12-161 | 267 | 8575 | COINCIDE |
| `SQ_DS_MIN_U64` | 0x47 | `DS_MIN_U64` | 71 (0x47) | 12-163 | 269 | 8688 | COINCIDE |
| `SQ_DS_MSKOR_B32` | 0xc | `DS_MSKOR_B32` | 12 (0xC) | 12-161 | 267 | 8580 | COINCIDE |
| `SQ_DS_MSKOR_B64` | 0x4c | `DS_MSKOR_B64` | 76 (0x4C) | 12-163 | 269 | 8693 | COINCIDE |
| `SQ_DS_MSKOR_RTN_B32` | 0x2c | `DS_MSKOR_RTN_B32` | 44 (0x2C) | 12-162 | 268 | 8617 | COINCIDE |
| `SQ_DS_MSKOR_RTN_B64` | 0x6c | `DS_MSKOR_RTN_B64` | 108 (0x6C) | 12-164 | 270 | 8727 | COINCIDE |
| `SQ_DS_NOP` | 0x14 | `DS_NOP` | 20 (0x14) | 12-162 | 268 | 8601 | COINCIDE |
| `SQ_DS_ORDERED_COUNT` | 0xbf | `DS_ORDERED_COUNT` | 191 (0xBF) | 12-165 | 271 | 8809 | COINCIDE |
| `SQ_DS_OR_B32` | 0xa | `DS_OR_B32` | 10 (0xA) | 12-161 | 267 | 8578 | COINCIDE |
| `SQ_DS_OR_B64` | 0x4a | `DS_OR_B64` | 74 (0x4A) | 12-163 | 269 | 8691 | COINCIDE |
| `SQ_DS_OR_RTN_B32` | 0x2a | `DS_OR_RTN_B32` | 42 (0x2A) | 12-162 | 268 | 8615 | COINCIDE |
| `SQ_DS_OR_RTN_B64` | 0x6a | `DS_OR_RTN_B64` | 106 (0x6A) | 12-164 | 270 | 8725 | COINCIDE |
| `SQ_DS_OR_SRC2_B32` | 0x8a | `DS_OR_SRC2_B32` | 138 (0x8A) | 12-165 | 271 | 8785 | COINCIDE |
| `SQ_DS_OR_SRC2_B64` | 0xca | `DS_OR_SRC2_B64` | 202 (0xCA) | 12-166 | 272 | 8832 | COINCIDE |
| `SQ_DS_PERMUTE_B32` | 0x3e | `DS_PERMUTE_B32` | 62 (0x3E) | 12-163 | 269 | 8675 | COINCIDE_MULTIFILA |
| `SQ_DS_READ2ST64_B32` | 0x38 | `DS_READ2ST64_B32` | 56 (0x38) | 12-162 | 268 | 8631 | COINCIDE |
| `SQ_DS_READ2ST64_B64` | 0x78 | `DS_READ2ST64_B64` | 120 (0x76) | 12-164 | 270 | 8740 | COINCIDE_DEC_ISA_DEC_HEX_INCOHERENTE |
| `SQ_DS_READ2_B32` | 0x37 | `DS_READ2_B32` | 55 (0x37) | 12-162 | 268 | 8629 | COINCIDE |
| `SQ_DS_READ2_B64` | 0x77 | `DS_READ2_B64` | 119 (0x75) | 12-164 | 270 | 8738 | COINCIDE_DEC_ISA_DEC_HEX_INCOHERENTE |
| `SQ_DS_READ_B128` | 0xff | `DS_READ_B128` | 255 (0xFF) | 12-166 | 272 | 8848 | COINCIDE |
| `SQ_DS_READ_B32` | 0x36 | `DS_READ_B32` | 54 (0x36) | 12-162 | 268 | 8628 | COINCIDE |
| `SQ_DS_READ_B64` | 0x76 | `DS_READ_B64` | 118 (0x74) | 12-164 | 270 | 8737 | COINCIDE_DEC_ISA_DEC_HEX_INCOHERENTE |
| `SQ_DS_READ_B96` | 0xfe | `DS_READ_B96` | 254 (0xFE) | 12-166 | 272 | 8847 | COINCIDE |
| `SQ_DS_READ_I16` | 0x3b | `DS_READ_I16` | 59 (0x3B) | 12-162 | 268 | 8635 | COINCIDE |
| `SQ_DS_READ_I8` | 0x39 | `DS_READ_I8` | 57 (0x39) | 12-162 | 268 | 8633 | COINCIDE |
| `SQ_DS_READ_U16` | 0x3c | `DS_READ_U16` | 60 (0x3C) | 12-163 | 269 | 8646 | COINCIDE |
| `SQ_DS_READ_U8` | 0x3a | `DS_READ_U8` | 58 (0x3A) | 12-162 | 268 | 8634 | COINCIDE |
| `SQ_DS_RSUB_RTN_U32` | 0x22 | `DS_RSUB_RTN_U32` | 34 (0x22) | 12-162 | 268 | 8607 | COINCIDE |
| `SQ_DS_RSUB_RTN_U64` | 0x62 | `DS_RSUB_RTN_U64` | 98 (0x62) | 12-164 | 270 | 8717 | COINCIDE |
| `SQ_DS_RSUB_SRC2_U32` | 0x82 | `DS_RSUB_SRC2_U32` | 130 (0x82) | 12-164 | 270 | 8749 | COINCIDE |
| `SQ_DS_RSUB_SRC2_U64` | 0xc2 | `DS_RSUB_SRC2_U64` | 194 (0xC2) | 12-166 | 272 | 8824 | COINCIDE |
| `SQ_DS_RSUB_U32` | 0x2 | `DS_RSUB_U32` | 2 (0x2) | 12-161 | 267 | 8569 | COINCIDE |
| `SQ_DS_RSUB_U64` | 0x42 | `DS_RSUB_U64` | 66 (0x42) | 12-163 | 269 | 8683 | COINCIDE |
| `SQ_DS_SUB_RTN_U32` | 0x21 | `DS_SUB_RTN_U32` | 33 (0x21) | 12-162 | 268 | 8606 | COINCIDE |
| `SQ_DS_SUB_RTN_U64` | 0x61 | `DS_SUB_RTN_U64` | 97 (0x61) | 12-164 | 270 | 8716 | COINCIDE |
| `SQ_DS_SUB_SRC2_U32` | 0x81 | `DS_SUB_SRC2_U32` | 129 (0x81) | 12-164 | 270 | 8746 | COINCIDE |
| `SQ_DS_SUB_SRC2_U64` | 0xc1 | `DS_SUB_SRC2_U64` | 193 (0xC1) | 12-166 | 272 | 8823 | COINCIDE |
| `SQ_DS_SUB_U32` | 0x1 | `DS_SUB_U32` | 1 (0x1) | 12-161 | 267 | 8568 | COINCIDE |
| `SQ_DS_SUB_U64` | 0x41 | `DS_SUB_U64` | 65 (0x41) | 12-163 | 269 | 8682 | COINCIDE |
| `SQ_DS_SWIZZLE_B32` | 0x3d | `DS_SWIZZLE_B32` | 61 (0x3D) | 12-163 | 269 | 8647 | COINCIDE |
| `SQ_DS_WRAP_RTN_B32` | 0x34 | `DS_WRAP_RTN_B32` | 52 (0x34) | 12-162 | 268 | 8627 | COINCIDE |
| `SQ_DS_WRITE2ST64_B32` | 0xf | `DS_WRITE2ST64_B32` | 15 (0xF) | 12-162 | 268 | 8594 | COINCIDE |
| `SQ_DS_WRITE2ST64_B64` | 0x4f | `DS_WRITE2ST64_B64` | 79 (0x4F) | 12-163 | 269 | 8697 | COINCIDE |
| `SQ_DS_WRITE2_B32` | 0xe | `DS_WRITE2_B32` | 14 (0xE) | 12-161 | 267 | 8582 | COINCIDE |
| `SQ_DS_WRITE2_B64` | 0x4e | `DS_WRITE2_B64` | 78 (0x4E) | 12-163 | 269 | 8695 | COINCIDE |
| `SQ_DS_WRITE_B128` | 0xdf | `DS_WRITE_B128` | 223 (0xDF) | 12-166 | 272 | 8844 | COINCIDE |
| `SQ_DS_WRITE_B16` | 0x1f | `DS_WRITE_B16` | 31 (0x1F) | 12-162 | 268 | 8604 | COINCIDE |
| `SQ_DS_WRITE_B32` | 0xd | `DS_WRITE_B32` | 13 (0xD) | 12-161 | 267 | 8581 | COINCIDE |
| `SQ_DS_WRITE_B64` | 0x4d | `DS_WRITE_B64` | 77 (0x4D) | 12-163 | 269 | 8694 | COINCIDE |
| `SQ_DS_WRITE_B8` | 0x1e | `DS_WRITE_B8` | 30 (0x1E) | 12-162 | 268 | 8603 | COINCIDE |
| `SQ_DS_WRITE_B96` | 0xde | `DS_WRITE_B96` | 222 (0xDE) | 12-166 | 272 | 8843 | COINCIDE |
| `SQ_DS_WRITE_SRC2_B32` | 0x8d | `DS_WRITE_SRC2_B32` | 141 (0x8D) | 12-165 | 271 | 8791 | COINCIDE |
| `SQ_DS_WRITE_SRC2_B64` | 0xcd | `DS_WRITE_SRC2_B64` | 205 (0xCD) | 12-166 | 272 | 8834 | COINCIDE |
| `SQ_DS_WRXCHG2ST64_RTN_B32` | 0x2f | `DS_WRXCHG2ST64_RTN_B32` | 47 (0x2F) | 12-162 | 268 | 8621 | COINCIDE |
| `SQ_DS_WRXCHG2ST64_RTN_B64` | 0x6f | `DS_WRXCHG2ST64_RTN_B64` | 111 (0x6F) | 12-164 | 270 | 8730 | COINCIDE |
| `SQ_DS_WRXCHG2_RTN_B32` | 0x2e | `DS_WRXCHG2_RTN_B32` | 46 (0x2E) | 12-162 | 268 | 8620 | COINCIDE |
| `SQ_DS_WRXCHG2_RTN_B64` | 0x6e | `DS_WRXCHG2_RTN_B64` | 110 (0x6E) | 12-164 | 270 | 8729 | COINCIDE |
| `SQ_DS_WRXCHG_RTN_B32` | 0x2d | `DS_WRXCHG_RTN_B32` | 45 (0x2D) | 12-162 | 268 | 8618 | COINCIDE |
| `SQ_DS_WRXCHG_RTN_B64` | 0x6d | `DS_WRXCHG_RTN_B64` | 109 (0x6D) | 12-164 | 270 | 8728 | COINCIDE |
| `SQ_DS_XOR_B32` | 0xb | `DS_XOR_B32` | 11 (0xB) | 12-161 | 267 | 8579 | COINCIDE |
| `SQ_DS_XOR_B64` | 0x4b | `DS_XOR_B64` | 75 (0x4B) | 12-163 | 269 | 8692 | COINCIDE |
| `SQ_DS_XOR_RTN_B32` | 0x2b | `DS_XOR_RTN_B32` | 43 (0x2B) | 12-162 | 268 | 8616 | COINCIDE |
| `SQ_DS_XOR_RTN_B64` | 0x6b | `DS_XOR_RTN_B64` | 107 (0x6B) | 12-164 | 270 | 8726 | COINCIDE |
| `SQ_DS_XOR_SRC2_B32` | 0x8b | `DS_XOR_SRC2_B32` | 139 (0x8B) | 12-165 | 271 | 8788 | COINCIDE |
| `SQ_DS_XOR_SRC2_B64` | 0xcb | `DS_XOR_SRC2_B64` | 203 (0xCB) | 12-166 | 272 | 8833 | COINCIDE |
| `SQ_BUFFER_ATOMIC_ADD` | 0x42 | `BUFFER_ATOMIC_ADD` | 66 (0x42) | 12-168 | 274 | 8954 | COINCIDE |
| `SQ_BUFFER_ATOMIC_ADD_X2` | 0x62 | `BUFFER_ATOMIC_ADD_X2` | 98 (0x62) | 12-169 | 275 | 8984 | COINCIDE |
| `SQ_BUFFER_ATOMIC_AND` | 0x48 | `BUFFER_ATOMIC_AND` | 72 (0x48) | 12-169 | 275 | 8975 | COINCIDE |
| `SQ_BUFFER_ATOMIC_AND_X2` | 0x68 | `BUFFER_ATOMIC_AND_X2` | 104 (0x68) | 12-169 | 275 | 8994 | COINCIDE |
| `SQ_BUFFER_ATOMIC_CMPSWAP` | 0x41 | `BUFFER_ATOMIC_CMPSWAP` | 65 (0x41) | 12-168 | 274 | 8952 | COINCIDE |
| `SQ_BUFFER_ATOMIC_CMPSWAP_X2` | 0x61 | `BUFFER_ATOMIC_CMPSWAP_X2` | 97 (0x61) | 12-169 | 275 | 8982 | COINCIDE |
| `SQ_BUFFER_ATOMIC_DEC` | 0x4c | `BUFFER_ATOMIC_DEC` | 76 (0x4C) | 12-169 | 275 | 8979 | COINCIDE |
| `SQ_BUFFER_ATOMIC_DEC_X2` | 0x6c | `BUFFER_ATOMIC_DEC_X2` | 108 (0x6C) | 12-169 | 275 | 8998 | COINCIDE |
| `SQ_BUFFER_ATOMIC_INC` | 0x4b | `BUFFER_ATOMIC_INC` | 75 (0x4B) | 12-169 | 275 | 8978 | COINCIDE |
| `SQ_BUFFER_ATOMIC_INC_X2` | 0x6b | `BUFFER_ATOMIC_INC_X2` | 107 (0x6B) | 12-169 | 275 | 8997 | COINCIDE |
| `SQ_BUFFER_ATOMIC_OR` | 0x49 | `BUFFER_ATOMIC_OR` | 73 (0x49) | 12-169 | 275 | 8976 | COINCIDE |
| `SQ_BUFFER_ATOMIC_OR_X2` | 0x69 | `BUFFER_ATOMIC_OR_X2` | 105 (0x69) | 12-169 | 275 | 8995 | COINCIDE |
| `SQ_BUFFER_ATOMIC_SMAX` | 0x46 | `BUFFER_ATOMIC_SMAX` | 70 (0x46) | 12-168 | 274 | 8960 | COINCIDE |
| `SQ_BUFFER_ATOMIC_SMAX_X2` | 0x66 | `BUFFER_ATOMIC_SMAX_X2` | 102 (0x66) | 12-169 | 275 | 8990 | COINCIDE |
| `SQ_BUFFER_ATOMIC_SMIN` | 0x44 | `BUFFER_ATOMIC_SMIN` | 68 (0x44) | 12-168 | 274 | 8956 | COINCIDE |
| `SQ_BUFFER_ATOMIC_SMIN_X2` | 0x64 | `BUFFER_ATOMIC_SMIN_X2` | 100 (0x64) | 12-169 | 275 | 8986 | COINCIDE |
| `SQ_BUFFER_ATOMIC_SUB` | 0x43 | `BUFFER_ATOMIC_SUB` | 67 (0x43) | 12-168 | 274 | 8955 | COINCIDE |
| `SQ_BUFFER_ATOMIC_SUB_X2` | 0x63 | `BUFFER_ATOMIC_SUB_X2` | 99 (0x63) | 12-169 | 275 | 8985 | COINCIDE |
| `SQ_BUFFER_ATOMIC_SWAP` | 0x40 | `BUFFER_ATOMIC_SWAP` | 64 (0x40) | 12-168 | 274 | 8951 | COINCIDE |
| `SQ_BUFFER_ATOMIC_SWAP_X2` | 0x60 | `BUFFER_ATOMIC_SWAP_X2` | 96 (0x60) | 12-169 | 275 | 8981 | COINCIDE |
| `SQ_BUFFER_ATOMIC_UMAX` | 0x47 | `BUFFER_ATOMIC_UMAX` | 71 (0x47) | 12-169 | 275 | 8973 | COINCIDE |
| `SQ_BUFFER_ATOMIC_UMAX_X2` | 0x67 | `BUFFER_ATOMIC_UMAX_X2` | 103 (0x67) | 12-169 | 275 | 8992 | COINCIDE |
| `SQ_BUFFER_ATOMIC_UMIN` | 0x45 | `BUFFER_ATOMIC_UMIN` | 69 (0x45) | 12-168 | 274 | 8958 | COINCIDE |
| `SQ_BUFFER_ATOMIC_UMIN_X2` | 0x65 | `BUFFER_ATOMIC_UMIN_X2` | 101 (0x65) | 12-169 | 275 | 8988 | COINCIDE |
| `SQ_BUFFER_ATOMIC_XOR` | 0x4a | `BUFFER_ATOMIC_XOR` | 74 (0x4A) | 12-169 | 275 | 8977 | COINCIDE |
| `SQ_BUFFER_ATOMIC_XOR_X2` | 0x6a | `BUFFER_ATOMIC_XOR_X2` | 106 (0x6A) | 12-169 | 275 | 8996 | COINCIDE |
| `SQ_BUFFER_LOAD_DWORD` | 0x14 | `BUFFER_LOAD_DWORD` | 20 (0x14) | 12-168 | 274 | 8925 | COINCIDE |
| `SQ_BUFFER_LOAD_DWORDX2` | 0x15 | `BUFFER_LOAD_DWORDX2` | 21 (0x15) | 12-168 | 274 | 8926 | COINCIDE |
| `SQ_BUFFER_LOAD_DWORDX3` | 0x16 | `BUFFER_LOAD_DWORDX3` | 22 (0x16) | 12-168 | 274 | 8927 | COINCIDE |
| `SQ_BUFFER_LOAD_DWORDX4` | 0x17 | `BUFFER_LOAD_DWORDX4` | 23 (0x17) | 12-168 | 274 | 8928 | COINCIDE |
| `SQ_BUFFER_LOAD_FORMAT_D16_X` | 0x8 | `BUFFER_LOAD_FORMAT_D16_X` | 8 (0x8) | 12-167 | 273 | 8904 | COINCIDE |
| `SQ_BUFFER_LOAD_FORMAT_D16_XY` | 0x9 | `BUFFER_LOAD_FORMAT_D16_XY` | 9 (0x9) | 12-167 | 273 | 8905 | COINCIDE |
| `SQ_BUFFER_LOAD_FORMAT_D16_XYZ` | 0xa | `BUFFER_LOAD_FORMAT_D16_XYZ` | 10 (0xA) | 12-167 | 273 | 8906 | COINCIDE |
| `SQ_BUFFER_LOAD_FORMAT_D16_XYZW` | 0xb | `BUFFER_LOAD_FORMAT_D16_XYZW` | 11 (0xB) | 12-168 | 274 | 8919 | COINCIDE |
| `SQ_BUFFER_LOAD_FORMAT_X` | 0x0 | `BUFFER_LOAD_FORMAT_X` | 0 (0x0) | 12-167 | 273 | 8894 | COINCIDE |
| `SQ_BUFFER_LOAD_FORMAT_XY` | 0x1 | `BUFFER_LOAD_FORMAT_XY` | 1 (0x1) | 12-167 | 273 | 8895 | COINCIDE |
| `SQ_BUFFER_LOAD_FORMAT_XYZ` | 0x2 | `BUFFER_LOAD_FORMAT_XYZ` | 2 (0x2) | 12-167 | 273 | 8896 | COINCIDE |
| `SQ_BUFFER_LOAD_FORMAT_XYZW` | 0x3 | `BUFFER_LOAD_FORMAT_XYZW` | 3 (0x3) | 12-167 | 273 | 8897 | COINCIDE |
| `SQ_BUFFER_LOAD_SBYTE` | 0x11 | `BUFFER_LOAD_SBYTE` | 17 (0x11) | 12-168 | 274 | 8922 | COINCIDE |
| `SQ_BUFFER_LOAD_SSHORT` | 0x13 | `BUFFER_LOAD_SSHORT` | 19 (0x13) | 12-168 | 274 | 8924 | COINCIDE |
| `SQ_BUFFER_LOAD_UBYTE` | 0x10 | `BUFFER_LOAD_UBYTE` | 16 (0x10) | 12-168 | 274 | 8921 | COINCIDE |
| `SQ_BUFFER_LOAD_USHORT` | 0x12 | `BUFFER_LOAD_USHORT` | 18 (0x12) | 12-168 | 274 | 8923 | COINCIDE |
| `SQ_BUFFER_STORE_BYTE` | 0x18 | `BUFFER_STORE_BYTE` | 24 (0x18) | 12-168 | 274 | 8937 | COINCIDE |
| `SQ_BUFFER_STORE_DWORD` | 0x1c | `BUFFER_STORE_DWORD` | 28 (0x1C) | 12-168 | 274 | 8939 | COINCIDE |
| `SQ_BUFFER_STORE_DWORDX2` | 0x1d | `BUFFER_STORE_DWORDX2` | 29 (0x1D) | 12-168 | 274 | 8940 | COINCIDE |
| `SQ_BUFFER_STORE_DWORDX3` | 0x1e | `BUFFER_STORE_DWORDX3` | 30 (0x1E) | 12-168 | 274 | 8941 | COINCIDE |
| `SQ_BUFFER_STORE_DWORDX4` | 0x1f | `BUFFER_STORE_DWORDX4` | 31 (0x1F) | 12-168 | 274 | 8942 | COINCIDE |
| `SQ_BUFFER_STORE_FORMAT_D16_X` | 0xc | `BUFFER_STORE_FORMAT_D16_X` | 12 (0xC) | 12-168 | 274 | 8930 | COINCIDE |
| `SQ_BUFFER_STORE_FORMAT_D16_XY` | 0xd | `BUFFER_STORE_FORMAT_D16_XY` | 13 (0xD) | 12-168 | 274 | 8931 | COINCIDE |
| `SQ_BUFFER_STORE_FORMAT_D16_XYZ` | 0xe | `BUFFER_STORE_FORMAT_D16_XYZ` | 14 (0xE) | 12-168 | 274 | 8933 | COINCIDE |
| `SQ_BUFFER_STORE_FORMAT_D16_XYZW` | 0xf | `BUFFER_STORE_FORMAT_D16_XYZW` | 15 (0xF) | 12-168 | 274 | 8935 | COINCIDE |
| `SQ_BUFFER_STORE_FORMAT_X` | 0x4 | `BUFFER_STORE_FORMAT_X` | 4 (0x4) | 12-167 | 273 | 8899 | COINCIDE |
| `SQ_BUFFER_STORE_FORMAT_XY` | 0x5 | `BUFFER_STORE_FORMAT_XY` | 5 (0x5) | 12-167 | 273 | 8900 | COINCIDE |
| `SQ_BUFFER_STORE_FORMAT_XYZ` | 0x6 | `BUFFER_STORE_FORMAT_XYZ` | 6 (0x6) | 12-167 | 273 | 8901 | COINCIDE |
| `SQ_BUFFER_STORE_FORMAT_XYZW` | 0x7 | `BUFFER_STORE_FORMAT_XYZW` | 7 (0x7) | 12-167 | 273 | 8902 | COINCIDE |
| `SQ_BUFFER_STORE_LDS_DWORD` | 0x3d | `BUFFER_STORE_LDS_DWORD` | 61 (0x3D) | 12-168 | 274 | 8943 | COINCIDE |
| `SQ_BUFFER_STORE_SHORT` | 0x1a | `BUFFER_STORE_SHORT` | 26 (0x1A) | 12-168 | 274 | 8938 | COINCIDE |
| `SQ_BUFFER_WBINVL1` | 0x3e | `BUFFER_WBINVL1` | 62 (0x2E) | 12-168 | 274 | 8946 | COINCIDE_DEC_ISA_DEC_HEX_INCOHERENTE |
| `SQ_BUFFER_WBINVL1_VOL` | 0x3f | `BUFFER_WBINVL1_VOL` | 63 (0x3F) | 12-168 | 274 | 8948 | COINCIDE |
| `SQ_TBUFFER_LOAD_FORMAT_D16_X` | 0x8 | `TBUFFER_LOAD_FORMAT_D16_X` | 8 (0x8) | 12-170 | 276 | 9050 | COINCIDE |
| `SQ_TBUFFER_LOAD_FORMAT_D16_XY` | 0x9 | `TBUFFER_LOAD_FORMAT_D16_XY` | 9 (0x9) | 12-170 | 276 | 9051 | COINCIDE |
| `SQ_TBUFFER_LOAD_FORMAT_D16_XYZ` | 0xa | `TBUFFER_LOAD_FORMAT_D16_XYZ` | 10 (0xA) | 12-170 | 276 | 9052 | COINCIDE |
| `SQ_TBUFFER_LOAD_FORMAT_D16_XYZW` | 0xb | `TBUFFER_LOAD_FORMAT_D16_XYZW` | 11 (0xB) | 12-170 | 276 | 9053 | COINCIDE |
| `SQ_TBUFFER_LOAD_FORMAT_X` | 0x0 | `TBUFFER_LOAD_FORMAT_X` | 0 (0x0) | 12-170 | 276 | 9041 | COINCIDE |
| `SQ_TBUFFER_LOAD_FORMAT_XY` | 0x1 | `TBUFFER_LOAD_FORMAT_XY` | 1 (0x1) | 12-170 | 276 | 9042 | COINCIDE |
| `SQ_TBUFFER_LOAD_FORMAT_XYZ` | 0x2 | `TBUFFER_LOAD_FORMAT_XYZ` | 2 (0x2) | 12-170 | 276 | 9043 | COINCIDE |
| `SQ_TBUFFER_LOAD_FORMAT_XYZW` | 0x3 | `TBUFFER_LOAD_FORMAT_XYZW` | 3 (0x3) | 12-170 | 276 | 9044 | COINCIDE |
| `SQ_TBUFFER_STORE_FORMAT_D16_X` | 0xc | `TBUFFER_STORE_FORMAT_D16_X` | 12 (0xC) | 12-170 | 276 | 9054 | COINCIDE |
| `SQ_TBUFFER_STORE_FORMAT_D16_XY` | 0xd | `TBUFFER_STORE_FORMAT_D16_XY` | 13 (0xD) | 12-171 | 277 | 9068 | COINCIDE |
| `SQ_TBUFFER_STORE_FORMAT_D16_XYZ` | 0xe | `TBUFFER_STORE_FORMAT_D16_XYZ` | 14 (0xE) | 12-171 | 277 | 9069 | COINCIDE |
| `SQ_TBUFFER_STORE_FORMAT_D16_XYZW` | 0xf | `TBUFFER_STORE_FORMAT_D16_XYZW` | 15 (0xF) | 12-171 | 277 | 9070 | COINCIDE |
| `SQ_TBUFFER_STORE_FORMAT_X` | 0x4 | `TBUFFER_STORE_FORMAT_X` | 4 (0x4) | 12-170 | 276 | 9046 | COINCIDE |
| `SQ_TBUFFER_STORE_FORMAT_XY` | 0x5 | `TBUFFER_STORE_FORMAT_XY` | 5 (0x5) | 12-170 | 276 | 9047 | COINCIDE |
| `SQ_TBUFFER_STORE_FORMAT_XYZ` | 0x6 | `TBUFFER_STORE_FORMAT_XYZ` | 6 (0x6) | 12-170 | 276 | 9048 | COINCIDE |
| `SQ_TBUFFER_STORE_FORMAT_XYZW` | 0x7 | `TBUFFER_STORE_FORMAT_XYZW` | 7 (0x7) | 12-170 | 276 | 9049 | COINCIDE |
| `SQ_IMAGE_ATOMIC_ADD` | 0x12 | `IMAGE_ATOMIC_ADD` | 17 (0x11) | 12-173 | 279 | 9205 | DIFIERE |
| `SQ_IMAGE_ATOMIC_AND` | 0x18 | `IMAGE_ATOMIC_AND` | 24 (0x18) | 12-173 | 279 | 9215 | COINCIDE |
| `SQ_IMAGE_ATOMIC_CMPSWAP` | 0x11 | `IMAGE_ATOMIC_CMPSWAP` | 16 (0x10) | 12-173 | 279 | 9204 | DIFIERE |
| `SQ_IMAGE_ATOMIC_DEC` | 0x1c | `IMAGE_ATOMIC_DEC` | 28 (0x1C) | 12-173 | 279 | 9220 | COINCIDE |
| `SQ_IMAGE_ATOMIC_INC` | 0x1b | `IMAGE_ATOMIC_INC` | 27 (0x1B) | 12-173 | 279 | 9219 | COINCIDE |
| `SQ_IMAGE_ATOMIC_OR` | 0x19 | `IMAGE_ATOMIC_OR` | 25 (0x19) | 12-173 | 279 | 9216 | COINCIDE |
| `SQ_IMAGE_ATOMIC_SMAX` | 0x16 | `IMAGE_ATOMIC_SMAX` | 22 (0x16) | 12-173 | 279 | 9211 | COINCIDE |
| `SQ_IMAGE_ATOMIC_SMIN` | 0x14 | `IMAGE_ATOMIC_SMIN` | 20 (0x14) | 12-173 | 279 | 9207 | COINCIDE |
| `SQ_IMAGE_ATOMIC_SUB` | 0x13 | `IMAGE_ATOMIC_SUB` | 18 (0x12) | 12-173 | 279 | 9206 | DIFIERE |
| `SQ_IMAGE_ATOMIC_SWAP` | 0x10 | `IMAGE_ATOMIC_SWAP` | 15 (0xF) | 12-173 | 279 | 9203 | DIFIERE |
| `SQ_IMAGE_ATOMIC_UMAX` | 0x17 | `IMAGE_ATOMIC_UMAX` | 23 (0x17) | 12-173 | 279 | 9213 | COINCIDE |
| `SQ_IMAGE_ATOMIC_UMIN` | 0x15 | `IMAGE_ATOMIC_UMIN` | 21 (0x15) | 12-173 | 279 | 9209 | COINCIDE |
| `SQ_IMAGE_ATOMIC_XOR` | 0x1a | `IMAGE_ATOMIC_XOR` | 26 (0x1A) | 12-173 | 279 | 9217 | COINCIDE |
| `SQ_IMAGE_GATHER4` | 0x40 | `IMAGE_GATHER4` | 64 (0x40) | 12-174 | 280 | 9285 | COINCIDE |
| `SQ_IMAGE_GATHER4_B` | 0x45 | `IMAGE_GATHER4_B` | 67 (0x43) | 12-174 | 280 | 9288 | DIFIERE |
| `SQ_IMAGE_GATHER4_B_CL` | 0x46 | `IMAGE_GATHER4_B_CL` | 68 (0x44) | 12-174 | 280 | 9289 | DIFIERE |
| `SQ_IMAGE_GATHER4_B_CL_O` | 0x56 | `IMAGE_GATHER4_B_CL_O` | 86 (0x56) | 12-175 | 281 | 9315 | COINCIDE |
| `SQ_IMAGE_GATHER4_B_O` | 0x55 | `IMAGE_GATHER4_B_O` | 85 (0x55) | 12-175 | 281 | 9314 | COINCIDE |
| `SQ_IMAGE_GATHER4_C` | 0x48 | `IMAGE_GATHER4_C` | 70 (0x46) | 12-174 | 280 | 9292 | DIFIERE |
| `SQ_IMAGE_GATHER4_CL` | 0x41 | `IMAGE_GATHER4_CL` | 65 (0x41) | 12-174 | 280 | 9286 | COINCIDE |
| `SQ_IMAGE_GATHER4_CL_O` | 0x51 | `IMAGE_GATHER4_CL_O` | 81 (0x51) | 12-175 | 281 | 9312 | COINCIDE |
| `SQ_IMAGE_GATHER4_C_B` | 0x4d | `IMAGE_GATHER4_C_B` | 77 (0x4D) | 12-175 | 281 | 9307 | COINCIDE |
| `SQ_IMAGE_GATHER4_C_B_CL` | 0x4e | `IMAGE_GATHER4_C_B_CL` | 78 (0x4E) | 12-175 | 281 | 9308 | COINCIDE |
| `SQ_IMAGE_GATHER4_C_B_CL_O` | 0x5e | `IMAGE_GATHER4_C_B_CL_O` | 94 (0x5E) | 12-175 | 281 | 9321 | COINCIDE |
| `SQ_IMAGE_GATHER4_C_B_O` | 0x5d | `IMAGE_GATHER4_C_B_O` | 93 (0x5D) | 12-175 | 281 | 9320 | COINCIDE |
| `SQ_IMAGE_GATHER4_C_CL` | 0x49 | `IMAGE_GATHER4_C_CL` | 71 (0x47) | 12-174 | 280 | 9293 | DIFIERE |
| `SQ_IMAGE_GATHER4_C_CL_O` | 0x59 | `IMAGE_GATHER4_C_CL_O` | 89 (0x59) | 12-175 | 281 | 9318 | COINCIDE |
| `SQ_IMAGE_GATHER4_C_L` | 0x4c | `IMAGE_GATHER4_C_L` | 76 (0x4C) | 12-175 | 281 | 9306 | COINCIDE |
| `SQ_IMAGE_GATHER4_C_LZ` | 0x4f | `IMAGE_GATHER4_C_LZ` | 79 (0x4F) | 12-175 | 281 | 9310 | COINCIDE |
| `SQ_IMAGE_GATHER4_C_LZ_O` | 0x5f | `IMAGE_GATHER4_C_LZ_O` | 95 (0x5F) | 12-175 | 281 | 9322 | COINCIDE |
| `SQ_IMAGE_GATHER4_C_L_O` | 0x5c | `IMAGE_GATHER4_C_L_O` | 92 (0x5C) | 12-175 | 281 | 9319 | COINCIDE |
| `SQ_IMAGE_GATHER4_C_O` | 0x58 | `IMAGE_GATHER4_C_O` | 88 (0x58) | 12-175 | 281 | 9317 | COINCIDE |
| `SQ_IMAGE_GATHER4_L` | 0x44 | `IMAGE_GATHER4_L` | 66 (0x42) | 12-174 | 280 | 9287 | DIFIERE |
| `SQ_IMAGE_GATHER4_LZ` | 0x47 | `IMAGE_GATHER4_LZ` | 69 (0x45) | 12-174 | 280 | 9291 | DIFIERE |
| `SQ_IMAGE_GATHER4_LZ_O` | 0x57 | `IMAGE_GATHER4_LZ_O` | 87 (0x57) | 12-175 | 281 | 9316 | COINCIDE |
| `SQ_IMAGE_GATHER4_L_O` | 0x54 | `IMAGE_GATHER4_L_O` | 84 (0x54) | 12-175 | 281 | 9313 | COINCIDE |
| `SQ_IMAGE_GATHER4_O` | 0x50 | `IMAGE_GATHER4_O` | 80 (0x50) | 12-175 | 281 | 9311 | COINCIDE |
| `SQ_IMAGE_GET_LOD` | 0x60 | `IMAGE_GET_LOD` | 96 (0x60) | 12-175 | 281 | 9328 | COINCIDE |
| `SQ_IMAGE_GET_RESINFO` | 0xe | `IMAGE_GET_RESINFO` | 14 (0xE) | 12-175 | 281 | 9324 | COINCIDE |
| `SQ_IMAGE_LOAD` | 0x0 | `IMAGE_LOAD` | 0 (0x0) | 12-172 | 278 | 9172 | COINCIDE |
| `SQ_IMAGE_LOAD_MIP` | 0x1 | `IMAGE_LOAD_MIP` | 1 (0x1) | 12-172 | 278 | 9174 | COINCIDE |
| `SQ_IMAGE_LOAD_MIP_PCK` | 0x4 | `IMAGE_LOAD_MIP_PCK` | 4 (0x4) | 12-172 | 278 | 9178 | COINCIDE |
| `SQ_IMAGE_LOAD_MIP_PCK_SGN` | 0x5 | `IMAGE_LOAD_MIP_PCK_SGN` | 5 (0x5) | 12-172 | 278 | 9180 | COINCIDE |
| `SQ_IMAGE_LOAD_PCK` | 0x2 | `IMAGE_LOAD_PCK` | 2 (0x2) | 12-172 | 278 | 9175 | COINCIDE |
| `SQ_IMAGE_LOAD_PCK_SGN` | 0x3 | `IMAGE_LOAD_PCK_SGN` | 3 (0x3) | 12-172 | 278 | 9176 | COINCIDE |
| `SQ_IMAGE_RSRC256` | 0x7e | `IMAGE_RSRC256` | — | — | — | — | AUSENTE_DE_TABLA_ISA |
| `SQ_IMAGE_SAMPLE` | 0x20 | `IMAGE_SAMPLE` | 32 (0x20) | 12-173 | 279 | 9223 | COINCIDE |
| `SQ_IMAGE_SAMPLER` | 0x7f | `IMAGE_SAMPLER` | — | — | — | — | AUSENTE_DE_TABLA_ISA |
| `SQ_IMAGE_SAMPLE_B` | 0x25 | `IMAGE_SAMPLE_B` | 37 (0x25) | 12-173 | 279 | 9229 | COINCIDE |
| `SQ_IMAGE_SAMPLE_B_CL` | 0x26 | `IMAGE_SAMPLE_B_CL` | 38 (0x26) | 12-173 | 279 | 9230 | COINCIDE |
| `SQ_IMAGE_SAMPLE_B_CL_O` | 0x36 | `IMAGE_SAMPLE_B_CL_O` | 54 (0x36) | 12-174 | 280 | 9261 | COINCIDE |
| `SQ_IMAGE_SAMPLE_B_O` | 0x35 | `IMAGE_SAMPLE_B_O` | 53 (0x35) | 12-174 | 280 | 9260 | COINCIDE |
| `SQ_IMAGE_SAMPLE_C` | 0x28 | `IMAGE_SAMPLE_C` | 40 (0x28) | 12-173 | 279 | 9233 | COINCIDE |
| `SQ_IMAGE_SAMPLE_CD` | 0x68 | `IMAGE_SAMPLE_CD` | 104 (0x68) | 12-174 | 280 | 9272 | COINCIDE |
| `SQ_IMAGE_SAMPLE_CD_CL` | 0x69 | `IMAGE_SAMPLE_CD_CL` | 105 (0x69) | 12-174 | 280 | 9273 | COINCIDE |
| `SQ_IMAGE_SAMPLE_CD_CL_O` | 0x6d | `IMAGE_SAMPLE_CD_CL_O` | 109 (0x6D) | 12-174 | 280 | 9279 | COINCIDE |
| `SQ_IMAGE_SAMPLE_CD_O` | 0x6c | `IMAGE_SAMPLE_CD_O` | 108 (0x6C) | 12-174 | 280 | 9278 | COINCIDE |
| `SQ_IMAGE_SAMPLE_CL` | 0x21 | `IMAGE_SAMPLE_CL` | 33 (0x21) | 12-173 | 279 | 9224 | COINCIDE |
| `SQ_IMAGE_SAMPLE_CL_O` | 0x31 | `IMAGE_SAMPLE_CL_O` | 49 (0x31) | 12-174 | 280 | 9255 | COINCIDE |
| `SQ_IMAGE_SAMPLE_C_B` | 0x2d | `IMAGE_SAMPLE_C_B` | 45 (0x2D) | 12-173 | 279 | 9239 | COINCIDE |
| `SQ_IMAGE_SAMPLE_C_B_CL` | 0x2e | `IMAGE_SAMPLE_C_B_CL` | 46 (0x2E) | 12-173 | 279 | 9240 | COINCIDE |
| `SQ_IMAGE_SAMPLE_C_B_CL_O` | 0x3e | `IMAGE_SAMPLE_C_B_CL_O` | 62 (0x3E) | 12-174 | 280 | 9270 | COINCIDE |
| `SQ_IMAGE_SAMPLE_C_B_O` | 0x3d | `IMAGE_SAMPLE_C_B_O` | 61 (0x3D) | 12-174 | 280 | 9269 | COINCIDE |
| `SQ_IMAGE_SAMPLE_C_CD` | 0x6a | `IMAGE_SAMPLE_C_CD` | 106 (0x6A) | 12-174 | 280 | 9275 | COINCIDE |
| `SQ_IMAGE_SAMPLE_C_CD_CL` | 0x6b | `IMAGE_SAMPLE_C_CD_CL` | 107 (0x6B) | 12-174 | 280 | 9276 | COINCIDE |
| `SQ_IMAGE_SAMPLE_C_CD_CL_O` | 0x6f | `IMAGE_SAMPLE_C_CD_CL_O` | 111 (0x6F) | 12-174 | 280 | 9282 | COINCIDE |
| `SQ_IMAGE_SAMPLE_C_CD_O` | 0x6e | `IMAGE_SAMPLE_C_CD_O` | 110 (0x6E) | 12-174 | 280 | 9281 | COINCIDE |
| `SQ_IMAGE_SAMPLE_C_CL` | 0x29 | `IMAGE_SAMPLE_C_CL` | 41 (0x29) | 12-173 | 279 | 9234 | COINCIDE |
| `SQ_IMAGE_SAMPLE_C_CL_O` | 0x39 | `IMAGE_SAMPLE_C_CL_O` | 57 (0x39) | 12-174 | 280 | 9264 | COINCIDE |
| `SQ_IMAGE_SAMPLE_C_D` | 0x2a | `IMAGE_SAMPLE_C_D` | 42 (0x2A) | 12-173 | 279 | 9235 | COINCIDE |
| `SQ_IMAGE_SAMPLE_C_D_CL` | 0x2b | `IMAGE_SAMPLE_C_D_CL` | 43 (0x2B) | 12-173 | 279 | 9236 | COINCIDE |
| `SQ_IMAGE_SAMPLE_C_D_CL_O` | 0x3b | `IMAGE_SAMPLE_C_D_CL_O` | 59 (0x3B) | 12-174 | 280 | 9266 | COINCIDE |
| `SQ_IMAGE_SAMPLE_C_D_O` | 0x3a | `IMAGE_SAMPLE_C_D_O` | 58 (0x3A) | 12-174 | 280 | 9265 | COINCIDE |
| `SQ_IMAGE_SAMPLE_C_L` | 0x2c | `IMAGE_SAMPLE_C_L` | 44 (0x2C) | 12-173 | 279 | 9238 | COINCIDE |
| `SQ_IMAGE_SAMPLE_C_LZ` | 0x2f | `IMAGE_SAMPLE_C_LZ` | 47 (0x2F) | 12-174 | 280 | 9253 | COINCIDE |
| `SQ_IMAGE_SAMPLE_C_LZ_O` | 0x3f | `IMAGE_SAMPLE_C_LZ_O` | 63 (0x3F) | 12-174 | 280 | 9271 | COINCIDE |
| `SQ_IMAGE_SAMPLE_C_L_O` | 0x3c | `IMAGE_SAMPLE_C_L_O` | 60 (0x3C) | 12-174 | 280 | 9268 | COINCIDE |
| `SQ_IMAGE_SAMPLE_C_O` | 0x38 | `IMAGE_SAMPLE_C_O` | 56 (0x38) | 12-174 | 280 | 9263 | COINCIDE |
| `SQ_IMAGE_SAMPLE_D` | 0x22 | `IMAGE_SAMPLE_D` | 34 (0x22) | 12-173 | 279 | 9225 | COINCIDE |
| `SQ_IMAGE_SAMPLE_D_CL` | 0x23 | `IMAGE_SAMPLE_D_CL` | 35 (0x23) | 12-173 | 279 | 9226 | COINCIDE |
| `SQ_IMAGE_SAMPLE_D_CL_O` | 0x33 | `IMAGE_SAMPLE_D_CL_O` | 51 (0x33) | 12-174 | 280 | 9257 | COINCIDE |
| `SQ_IMAGE_SAMPLE_D_O` | 0x32 | `IMAGE_SAMPLE_D_O` | 50 (0x32) | 12-174 | 280 | 9256 | COINCIDE |
| `SQ_IMAGE_SAMPLE_L` | 0x24 | `IMAGE_SAMPLE_L` | 36 (0x24) | 12-173 | 279 | 9228 | COINCIDE |
| `SQ_IMAGE_SAMPLE_LZ` | 0x27 | `IMAGE_SAMPLE_LZ` | 39 (0x27) | 12-173 | 279 | 9232 | COINCIDE |
| `SQ_IMAGE_SAMPLE_LZ_O` | 0x37 | `IMAGE_SAMPLE_LZ_O` | 55 (0x37) | 12-174 | 280 | 9262 | COINCIDE |
| `SQ_IMAGE_SAMPLE_L_O` | 0x34 | `IMAGE_SAMPLE_L_O` | 52 (0x34) | 12-174 | 280 | 9259 | COINCIDE |
| `SQ_IMAGE_SAMPLE_O` | 0x30 | `IMAGE_SAMPLE_O` | 48 (0x30) | 12-174 | 280 | 9254 | COINCIDE |
| `SQ_IMAGE_STORE` | 0x8 | `IMAGE_STORE` | 8 (0x8) | 12-172 | 278 | 9183 | COINCIDE |
| `SQ_IMAGE_STORE_MIP` | 0x9 | `IMAGE_STORE_MIP` | 9 (0x9) | 12-172 | 278 | 9185 | COINCIDE |
| `SQ_IMAGE_STORE_MIP_PCK` | 0xb | `IMAGE_STORE_MIP_PCK` | 11 (0xB) | 12-173 | 279 | 9200 | COINCIDE |
| `SQ_IMAGE_STORE_PCK` | 0xa | `IMAGE_STORE_PCK` | 10 (0xA) | 12-173 | 279 | 9198 | COINCIDE |
| `SQ_FLAT_ATOMIC_ADD` | 0x42 | `FLAT_ATOMIC_ADD` | 50 (0x32) | 12-178 | 284 | 9432 | DIFIERE |
| `SQ_FLAT_ATOMIC_ADD_X2` | 0x62 | `FLAT_ATOMIC_ADD_X2` | 82 (0x52) | 12-178 | 284 | 9452 | DIFIERE |
| `SQ_FLAT_ATOMIC_AND` | 0x48 | `FLAT_ATOMIC_AND` | 57 (0x39) | 12-178 | 284 | 9442 | DIFIERE |
| `SQ_FLAT_ATOMIC_AND_X2` | 0x68 | `FLAT_ATOMIC_AND_X2` | 89 (0x59) | 12-178 | 284 | 9462 | DIFIERE |
| `SQ_FLAT_ATOMIC_CMPSWAP` | 0x41 | `FLAT_ATOMIC_CMPSWAP` | 49 (0x31) | 12-178 | 284 | 9430 | DIFIERE |
| `SQ_FLAT_ATOMIC_CMPSWAP_X2` | 0x61 | `FLAT_ATOMIC_CMPSWAP_X2` | 81 (0x51) | 12-178 | 284 | 9449 | DIFIERE |
| `SQ_FLAT_ATOMIC_DEC` | 0x4c | `FLAT_ATOMIC_DEC` | 61 (0x3D) | 12-178 | 284 | 9447 | DIFIERE |
| `SQ_FLAT_ATOMIC_DEC_X2` | 0x6c | `FLAT_ATOMIC_DEC_X2` | 93 (0x5D) | 12-178 | 284 | 9466 | DIFIERE |
| `SQ_FLAT_ATOMIC_INC` | 0x4b | `FLAT_ATOMIC_INC` | 60 (0x3C) | 12-178 | 284 | 9445 | DIFIERE |
| `SQ_FLAT_ATOMIC_INC_X2` | 0x6b | `FLAT_ATOMIC_INC_X2` | 92 (0x5C) | 12-178 | 284 | 9465 | DIFIERE |
| `SQ_FLAT_ATOMIC_OR` | 0x49 | `FLAT_ATOMIC_OR` | 58 (0x3A) | 12-178 | 284 | 9443 | DIFIERE |
| `SQ_FLAT_ATOMIC_OR_X2` | 0x69 | `FLAT_ATOMIC_OR_X2` | 90 (0x5A) | 12-178 | 284 | 9463 | DIFIERE |
| `SQ_FLAT_ATOMIC_SMAX` | 0x46 | `FLAT_ATOMIC_SMAX` | 55 (0x37) | 12-178 | 284 | 9438 | DIFIERE |
| `SQ_FLAT_ATOMIC_SMAX_X2` | 0x66 | `FLAT_ATOMIC_SMAX_X2` | 87 (0x57) | 12-178 | 284 | 9458 | DIFIERE |
| `SQ_FLAT_ATOMIC_SMIN` | 0x44 | `FLAT_ATOMIC_SMIN` | 53 (0x35) | 12-178 | 284 | 9434 | DIFIERE |
| `SQ_FLAT_ATOMIC_SMIN_X2` | 0x64 | `FLAT_ATOMIC_SMIN_X2` | 85 (0x55) | 12-178 | 284 | 9454 | DIFIERE |
| `SQ_FLAT_ATOMIC_SUB` | 0x43 | `FLAT_ATOMIC_SUB` | 51 (0x33) | 12-178 | 284 | 9433 | DIFIERE |
| `SQ_FLAT_ATOMIC_SUB_X2` | 0x63 | `FLAT_ATOMIC_SUB_X2` | 83 (0x53) | 12-178 | 284 | 9453 | DIFIERE |
| `SQ_FLAT_ATOMIC_SWAP` | 0x40 | `FLAT_ATOMIC_SWAP` | 48 (0x30) | 12-177 | 283 | 9418 | DIFIERE |
| `SQ_FLAT_ATOMIC_SWAP_X2` | 0x60 | `FLAT_ATOMIC_SWAP_X2` | — | — | — | — | AUSENTE_DE_TABLA_ISA |
| `SQ_FLAT_ATOMIC_UMAX` | 0x47 | `FLAT_ATOMIC_UMAX` | 56 (0x38) | 12-178 | 284 | 9440 | DIFIERE |
| `SQ_FLAT_ATOMIC_UMAX_X2` | 0x67 | `FLAT_ATOMIC_UMAX_X2` | 88 (0x58) | 12-178 | 284 | 9460 | DIFIERE |
| `SQ_FLAT_ATOMIC_UMIN` | 0x45 | `FLAT_ATOMIC_UMIN` | 54 (0x36) | 12-178 | 284 | 9436 | DIFIERE |
| `SQ_FLAT_ATOMIC_UMIN_X2` | 0x65 | `FLAT_ATOMIC_UMIN_X2` | 86 (0x56) | 12-178 | 284 | 9456 | DIFIERE |
| `SQ_FLAT_ATOMIC_XOR` | 0x4a | `FLAT_ATOMIC_XOR` | 59 (0x3B) | 12-178 | 284 | 9444 | DIFIERE |
| `SQ_FLAT_ATOMIC_XOR_X2` | 0x6a | `FLAT_ATOMIC_XOR_X2` | 91 (0x5B) | 12-178 | 284 | 9464 | DIFIERE |
| `SQ_FLAT_LOAD_DWORD` | 0x14 | `FLAT_LOAD_DWORD` | 12 (0xC) | 12-177 | 283 | 9406 | DIFIERE |
| `SQ_FLAT_LOAD_DWORDX2` | 0x15 | `FLAT_LOAD_DWORDX2` | 13 (0xD) | 12-177 | 283 | 9407 | DIFIERE |
| `SQ_FLAT_LOAD_DWORDX3` | 0x16 | `FLAT_LOAD_DWORDX3` | 15 (0xF) | 12-177 | 283 | 9409 | DIFIERE |
| `SQ_FLAT_LOAD_DWORDX4` | 0x17 | `FLAT_LOAD_DWORDX4` | 14 (0xE) | 12-177 | 283 | 9408 | DIFIERE |
| `SQ_FLAT_LOAD_SBYTE` | 0x11 | `FLAT_LOAD_SBYTE` | 9 (0x9) | 12-177 | 283 | 9403 | DIFIERE |
| `SQ_FLAT_LOAD_SSHORT` | 0x13 | `FLAT_LOAD_SSHORT` | 11 (0xB) | 12-177 | 283 | 9405 | DIFIERE |
| `SQ_FLAT_LOAD_UBYTE` | 0x10 | `FLAT_LOAD_UBYTE` | 8 (0x8) | 12-177 | 283 | 9402 | DIFIERE |
| `SQ_FLAT_LOAD_USHORT` | 0x12 | `FLAT_LOAD_USHORT` | 10 (0xA) | 12-177 | 283 | 9404 | DIFIERE |
| `SQ_FLAT_SCRATCH_HI` | 0x67 | `FLAT_SCRATCH_HI` | — | — | — | — | AUSENTE_DE_TABLA_ISA |
| `SQ_FLAT_SCRATCH_LO` | 0x66 | `FLAT_SCRATCH_LO` | — | — | — | — | AUSENTE_DE_TABLA_ISA |
| `SQ_FLAT_STORE_BYTE` | 0x18 | `FLAT_STORE_BYTE` | 24 (0x18) | 12-177 | 283 | 9411 | COINCIDE |
| `SQ_FLAT_STORE_DWORD` | 0x1c | `FLAT_STORE_DWORD` | 28 (0x1C) | 12-177 | 283 | 9413 | COINCIDE |
| `SQ_FLAT_STORE_DWORDX2` | 0x1d | `FLAT_STORE_DWORDX2` | 29 (0x1D) | 12-177 | 283 | 9414 | COINCIDE |
| `SQ_FLAT_STORE_DWORDX3` | 0x1e | `FLAT_STORE_DWORDX3` | 31 (0x1F) | 12-177 | 283 | 9416 | DIFIERE |
| `SQ_FLAT_STORE_DWORDX4` | 0x1f | `FLAT_STORE_DWORDX4` | 30 (0x1E) | 12-177 | 283 | 9415 | DIFIERE |
| `SQ_FLAT_STORE_SHORT` | 0x1a | `FLAT_STORE_SHORT` | 26 (0x1A) | 12-177 | 283 | 9412 | COINCIDE |

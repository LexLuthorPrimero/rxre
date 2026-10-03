# 968 — El universo de las "5 tablas de opcode": la afirmación canónica era una AFIRMACIÓN DE AUSENCIA con el universo cambiado

```
CLASSIFICATION=DOCUMENTATION · TRACK=STATIC
AUTORIA=sesion-missing · WORK_CLASS=analisis-estatico
WRITE_EXECUTION=1 fichero nuevo · RUNTIME=NOT_RUN · GPU=INTACTA · AUTHORIZATION=NONE
NODE_ID=Q5-CORPUS-UNIVERSE
```

Estado: `RESOLVED_WITH_RESIDUAL_UNIVERSE`. El corpus de Q5 queda cerrado y medido; el
universo de la maquina queda enumerado con un residual declarado (indice `plocate` rancio).

Target verificado, no supuesto: `01:00.0 VGA [0300] AMD Lexa PRO [Radeon 540/540X/550/550X /
RX 550] [1002:699f] (rev c7)` = **Polaris12 = gfx803 = GFX8.0**. `HARDWARE_SCOPE=HOST-C/RX550/0000:01:00.0`.

---

## 1. La pregunta

`DRIVER-MISSION-STATE.md:136-138` afirma:

> No es la tabla. Es que **4 de las 5 tablas de opcode GFX8 no están en el corpus**: solo existe
> `gfx_8_0_enum.h`. `NOT_AVAILABLE`, con forma precisa. Un programa con efecto observable necesita
> además los campos de operando y registro, que son otra tabla y tampoco están.

Eso es una **afirmacion de ausencia sin universo declarado**. Este nodo la convierte en una
clasificacion con universo explicito, o la refuta.

**Se refuta, por dos motivos independientes.** Los dos se miden, no se infieren.

---

## 2. MOTIVO 1 — error de unidad: las 5 tablas estan DENTRO del unico fichero

Antes de buscar nada hay que fijar **que es una "tabla"** en esa frase. Esta es la
`DEFINITION` y decide todo lo demas.

`013-filtro-gfx8-por-opcode.md:58-64` las define asi:

| tabla | entradas | rango | ejemplos |
|---|---|---|---|
| SOP2 | 4 | `0x01`..`0x1d` | `MOV_B64`, `CMOV_B64`, `ENDPGM`, `SETPC_B64` |
| SOPK | 2 | `0x00`..`0x01` | `MOVK_I32`, `CMOVK_I32` |
| SMEM | 8 | `0x00`..`0x12` | `LOAD_DWORD`, `LOAD_DWORDX2`, `STORE_DWORD` |
| SOPC | 15 | `0x00`..`0x13` | `CMP_EQ_I32`, `BRANCH` |
| SOP1 | 6 | `0x00`..`0x05` | `ADD_U32`, `SUB_U32`, `NOT_B32` |

Y `013:125` lo dice sin ambiguedad: «GFX8_DEFINITION — el header define **5 tablas superpuestas**
bajo un prefijo». Un solo header. **Las 5 tablas no son 5 ficheros: son 5 subconjuntos del mismo
fichero.** `013:77` lo declara del mismo modo: «un opcode no es un par (valor, nombre) … es un par
(valor, tabla, nombre), y **la tabla es justamente lo que el header no registra**».

Medido sobre el fichero (camino relativo al corpus declarado):

```
$ H=RESEARCH/working/linux-7.1.3/drivers/gpu/drm/amd/include/asic_reg/gca/gfx_8_0_enum.h
$ grep -c '^#define SQ_S_' $H
216
$ grep -E '^#define (SQ_S_LOAD_DWORD|SQ_S_MOVK_I32|SQ_S_CMP_EQ_I32|SQ_S_ADD_U32|SQ_S_ENDPGM)\b' $H
#define SQ_S_MOVK_I32                             0x0
#define SQ_S_LOAD_DWORD                           0x0
#define SQ_S_ENDPGM                               0x1
#define SQ_S_CMP_EQ_I32                           0x0
#define SQ_S_ADD_U32                              0x0
```

Un miembro de **cada una** de las 5 tablas esta presente, en el **unico** fichero. Reparto medido:

```
SMEM  LOAD_DWORD  STORE_DWORD   presentes
SOP1  ADD_U32     MOV_B32       presentes
SOPK  MOVK_I32    CMOVK_I32     presentes
SOPC  CMP_EQ_I32  BRANCH(=SQ_S_BRANCH, linea 3813)  presentes
SOP2  ENDPGM      SETPC_B64     presentes
```

Con la `DEFINITION` de `013` en la mano, la frase canonica se lee de otra manera: no «4 de 5
tablas no estan en el corpus», sino **«5 de 5 tablas estan en el corpus, y ninguna lleva su
identidad escrita»**. Esos dos enunciados son distintos y el primero es falso.

Y lo que falta de verdad esta medido tambien:

```
$ grep -cE '\bSOPC\b|\bSOP1\b|\bSOPK\b|\bSMEM\b|\bSOP2\b' $H
0
$ grep -n -B2 -A1 '^#define SQ_S_LOAD_DWORD\b' $H
2951-#define SQ_CNT3                                   0x2
2952-#define SQ_CNT4                                   0x3
2953:#define SQ_S_LOAD_DWORD                           0x0
2954-#define SQ_S_LOAD_DWORDX2                         0x1
```

**0** tokens de identidad de tabla, y el contexto no la esconde: `SQ_S_LOAD_DWORD` esta pegado a
`SQ_CNT3/SQ_CNT4`, que no son de su misma tabla. No hay marca que leer. Eso es `SEMANTICS` ausente
en esa fuente, no `DEFINITION` ausente.

---

## 3. MOTIVO 2 — el universo estaba reducido a 1 de 8, y la fuente que si rotula existe

### 3.1 La reduccion: 1 copia de 8, y ademas sin commitear

`967-opcode-ambiguidad-era-el-detalector.md:5` declara `CORPUS=RESEARCH/working/linux-7.1.3`, y
`967:26` dice que `gfx_8_0_enum.h` es «la **unica** cabecera de opcode GFX8 del corpus». Ese
enunciado es **fiel a su propio filtro** (no es una mentira sobre lo que uso), pero el filtro es
unaExtraccion parcial de **3 directorios**:

```
$ ls RESEARCH/working/linux-7.1.3
Documentation  drivers  include
$ git ls-files RESEARCH | wc -l
0                      <- RESEARCH/ esta en .gitignore:63, luego es UNTRACKED
```

Y en la maquina hay **8** copias de ese mismo fichero (ver §5). Ademas existe
`gfx_8_1_enum.h`, que `967` no menciona como candidato.

Ojo con el detalle que hace esto un problema de unidades y no de contenido: las 8 copias son
**byte-identicas**.

```
fa6b8ff974fccdd54aa0e1b6a6430508a558fd263ead90eaf70bef262e4d5d63  (x8, las 8 rutas)
```

Es decir: **traer las otras 7 no habria cambiado ni un bit del opcode medido.** La copia no era el
problema. Eso no absuelve a la afirmacion, pero le fija la dimension exacta del defecto.

### 3.2 La fuente que si rotula las 5 tablas, ya en esta maquina y ya catalogada

```
$ ls -la ~/Descargas/RX550-INVESTIGACION/05-FUENTES-PDF/gcn3-isa.pdf
-rw-r--r-- 1 lucas lucas 2752924 sep 27 10:05
$ pdfinfo ~/Descargas/RX550-INVESTIGACION/05-FUENTES-PDF/gcn3-isa.pdf
Title:           R1200_ISA.book          Pages: 348
CreationDate:    Tue Aug  9 16:22:20 2016 -03
sha256  8e49a3767b337ec8aff451494c654c84c026720de8e3fa35177b0656f4bc2853
```

**Es la ISA de este ASIC.** No una version parecida: `GFX8 = GCN3`, y el propio proyecto ya lo
sabe y lo tiene escrito — `RESEARCH/polaris12xl/LIBRARY-CATALOG.md:630`:

> `M-01` | `RX550-INVESTIGACION/05-FUENTES-PDF/gcn3-isa.pdf` | AMD Graphics Core Next,
> Generation 3 ISA, 348 pp | **GFX8 = GCN 3.** Es la ISA del objetivo y el catalogo no la mencionaba

Y **DENTRO** de ese PDF, capitulo 12, cada tabla con su propio capitulo — exactamente la
identidad que el header del kernel no registra:

```
$ grep -nE "SOP[12CK] Instructions|SMEM Instructions" gcn3_full.txt
466:  SOP2 Instructions .......................... 12-1
470:  SOPK Instructions ......................... 12-13
474:  SOP1 Instructions ......................... 12-19
478:  SOPC Instructions ......................... 12-32
486:  SMEM Instructions ......................... 12-47
10837:  12.1 SOP2 Instructions
11944:  12.2 SOPK Instructions
```

Recuento de menciones en las 348 paginas: `SOPC 37 · SOP1 87 · SOPK 40 · SOP2 78 · SMEM 47`.

### 3.3 Los "campos de operando y registro" tambien estan, como especificacion

La segunda mitad de la frase canonica («los campos de operando y registro, que son otra tabla y
tampoco estan») se mide en la misma fuente:

```
gcn3_full.txt:3500  «5.2 Scalar ALU Operands»
  Table 5.1 Scalar Condition Code
      Scalar Dest   (7 bits)
      Scalar Source (8 bits)
      Code 0-101 -> SGPR 0 to 103, Scalar GPRs
gcn3_full.txt:36210  SDWA_BYTE_0: Select data[7:0].
gcn3_full.txt:36218  SDWA_WORD_0: Select data[15:0].
gcn3_full.txt:36222  SDWA_DWORD: Select data[31:0].
```

Esos son los campos de operando y de registro, con su anchura en bits. **No como tabla
machine-readable extraida, sino como especificacion presente y extraible.**

Que se extraiga es barato y ya se ha hecho una vez para medir esto:

```
$ time pdftotext ~/Descargas/.../gcn3-isa.pdf /tmp/opencode/gcn3_full.txt
real 0m3,593s
38290 lineas, 487820 bytes
sha256 c086839aa35eddd21a7c2ed8b8a31a97aa595ddfced96dd6755e5864199a9075
```

(Aunque el PDF declara `Encrypted: yes (copy:no)`, poppler extrae igual: 3,6 s. Limitacion
anulada por medicion.)

### 3.4 Lo que el proyecto ya extrajo de ahi, y por que no cubre esto

`RESEARCH/polaris12xl/LEARNED-GCN3-ISA.md` (195 lineas) es una destilacion real de ese PDF, pero
**no** de las tablas de opcode: sus secciones son «el circuito de interrupcion»,
«el fence es un contador», «lo que la ISA nombra y el proyecto no tenia». Menciona
`S_LOAD_DWORD`/`S_STORE_DWORD` una vez, como caso de que al modelo le falta acceso escalar
(`LEARNED-GCN3-ISA.md:155`). No contiene ni las 5 tablas ni la tabla de campos.

**Por eso el residuo es real y por eso no es un bloqueo:** la fuente esta, la extraccion esta
pagada y no hecha.

---

## 4. Clasificacion de las 5 tablas

Antes de clasificar, separadas las cinco facetas. `HARDWARE_SCOPE=gfx803 (1002:699f rev c7)`.
La razon de `REQUIRED` no es la presencia ni la ausencia de un fichero: es la `SEMANTICS` de
`013:76` — **el opcode es la tripleta `(valor, tabla, nombre)`**, y con el valor solo,
`S_ADD_U32=0` y `S_LOAD_DWORD=0` son indistinguibles. Sin identidad de tabla no hay tabla
instruccion→opcode, luego la identidad es `REQUIRED` por construccion del problema.

| tabla | DEFINITION | EFFECTIVE_USE | SEMANTICS (identidad) | RELATION | COUNTERFACTUAL | VEREDICTO |
|---|---|---|---|---|---|---|
| **SOP1** | PRESENTE `gfx_8_0_enum.h` (`SQ_S_ADD_U32` L?, `SQ_S_MOV_B32`) | presente (216 `SQ_S_*`) | AUSENTE en el header / PRESENTE ISA `12.3` L474 | colisiona con SOPC/SOPK/SMEM/SOP2 en 0x00 | sin identidad, 0x00 es 5 opcodes | **REQUIRED** |
| **SOPC** | PRESENTE (`SQ_S_CMP_EQ_I32`, `SQ_S_BRANCH` L3813) | presente | AUSENTE header / PRESENTE ISA `12.4` L478 | idem en 0x00 | idem | **REQUIRED** |
| **SOPK** | PRESENTE (`SQ_S_MOVK_I32`, `SQ_S_CMOVK_I32`) | presente | AUSENTE header / PRESENTE ISA `12.2` L470 | idem en 0x00 | idem | **REQUIRED** |
| **SOP2** | PRESENTE (`SQ_S_ENDPGM`, `SQ_S_SETPC_B64`) | presente | AUSENTE header / PRESENTE ISA `12.1` L466 | idem en 0x00-0x01 | idem | **REQUIRED** |
| **SMEM** | PRESENTE (`SQ_S_LOAD_DWORD`, `SQ_S_STORE_DWORD`) | presente | AUSENTE header / PRESENTE ISA `12-47` L486 | idem en 0x00 | idem | **REQUIRED** |
| campos de operando/registro | PRESENTE como spec, ISA Table 5.1 | NO extraida | PRESENTE (anchuras 7/8 bits, SDWA) | subordina a las 5 | ver §6 | **CONDITIONAL** |

`CONDITIONAL` y no `REQUIRED` para los campos de operando, y no por el nombre del fichero: porque hay un
oraculo independiente que ya produce el layout sin fichero alguno. Medido en §6.

**Lo que NO se ha clasificado como `REQUIRED`:** la identidad de tabla no se infiere de que el
fichero exista, ni de que no exista, ni del nombre del fichero. Se clasifica `REQUIRED` porque la
semantica del opcode lo exige, y eso es independiente de las 8 copias.

---

## 5. FILTRO_DEL_UNIVERSO

Universo declarado, por partes, con su coste. Todo comando es literal y copiable.

```bash
# ---- U1: arbol del repo en HEAD (indice git, instantaneo) -----------------
git ls-files
cd /home/lucas/Escritorio/RX550-INVESTIGACION && git rev-parse HEAD   # 58244a8…

# ---- U2: repo entero, working tree incluido (find con -prune) ------------
find . -path ./.git -prune -o -name 'gfx_8_0_enum.h' -print
#  EXITADO en ~2 s. Las 4 primeras son las unicas dentro del repo.

# ---- U3: 08-ARQUITECTURA/  (artefactos, cache, corpus) -------------------
ls 08-ARQUITECTURA                      # artifacts  artifacts-rx550  cache  decisions
                                        # designs  logs-rx550  reviews  tools  validations
find 08-ARQUITECTURA -name '*.h' | wc -l        # -> 3  (ninguna de ISA)
ls -d 08-ARQUITECTURA/corpus                  # -> NO EXISTE

# ---- U4: 06-INGENIERIA-INVERSA/  (findings, corpus, agents) --------------
ls 06-INGENIERIA-INVERSA                 # agents amdgpu-analysis corpus evidencia findings
                                        # firmware llvmpipe_pairs.py outgoing-reviews
                                        # protocol-dumps register-maps
find 06-INGENIERIA-INVERSA/corpus -type f | wc -l   # -> 15, todas BC3/texturas
#  OJO: existe un directorio LITERALMENTE llamado "corpus" y NO contiene ISA.
#  El corpus de 967 es otro: RESEARCH/working/linux-7.1.3

# ---- U5: fuente de migracion /var/tmp/rx550 (15.2 GB: MEDIR antes) -------
du -sb /var/tmp/rx550                   # 15217046743 bytes, ~15.2 GB, exit 0
plocate gfx_8_0_enum.h | grep -c 'var/tmp/rx550'   # -> 0
#  NO se recorrio entera: 59 entradas de primer nivel, 0 cabeceras de ISA.

# ---- U6: headers de kernel INSTALADOS ------------------------------------
ls /usr/src/kernels/                                    # 6.18.2-200…fc43  7.1.3-200…fc44
ls /usr/src/kernels/7.1.3-200.nobara.fc44.x86_64/drivers/gpu/drm/amd/include/asic_reg/gca/
#  -> NO EXISTE. Los headers de ASIC de AMD no van en el paquete de headers del kernel.
ls -ld /lib/modules/7.1.3-200.nobara.fc44.x86_64/build # -> symlink a /usr/src/kernels/…

# ---- U7: index global de la maquina (plocate), con SU COSTE --------------
which plocate locate updatedb            # /usr/bin/plocate  /usr/bin/locate  /usr/bin/updatedb
ls -la /var/lib/plocate/plocate.db       # 37878141 bytes, mtime oct 3 00:33
plocate gfx_8_0_enum.h                   # -> 8 rutas, instantaneo
#  RESIDUAL: el indice tiene ~10 h de antiguedad a las 10:39. Todo lo creado
#  en esa ventana es INVISIBLE para plocate. Declarado como tal en §7.

# ---- U8: fuentes ISA / especificacion -------------------------------------
plocate -i 'gcn3_isa'                    # -> 2 rutas
ls -la ~/Descargas/RX550-INVESTIGACION/05-FUENTES-PDF/gcn3-isa.pdf
pdfinfo ~/Descargas/.../gcn3-isa.pdf     # 348 p, Title R1200_ISA.book

# ---- U9: Mesa --------------------------------------------------------------
rpm -qa | grep -i mesa | head -10        # mesa-*-26.2.3-1.fc44, SOLO binarios
ls /home/lucas/mesa/src/gallium/drivers/radeonsi/gfx/si_shader.h   # arbol de fuentes presente

# ---- U10: BTF / dumps de amdgpu en el repo -------------------------------
find . -path ./.git -prune -o \( -name '*.btf' -o -name 'amdgpu*.ko*' \
     -o -name '*.dump' -o -name '*vmlinux*' \) -print
#  -> solo falsos positivos de scripts de compilacion (vmlinux.lds.h, Makefile.btf…)
#     NINGUN BTF ni dump de amdgpu en el repo. Ausencia ENUMERADA, no supuesta.
```

**Coste total**: `du` de 15.2 GB en ~9 s; los dos `find` del repo en ~2 s cada uno; plocate
instantaneo; extraccion del PDF 3,6 s. Ningun recorrido global sin indice: **el `find /` que
supo exceder 120 s no se repite nunca**.

### 5.1 Residuo por COMPARACION DE CONJUNTOS

Nunca por resta de un total. Se enumeran los dos conjuntos y se calcula la diferencia.

```
A  = plocate gfx_8_0_enum.h                      (8 elementos, ordenados)
B  = lo que 967 declaro consumir: CORPUS=RESEARCH/working/linux-7.1.3  (1 elemento)
A\B = comm -23 A B                               (7 elementos)
```

```
A
 1  …/RX550-INVESTIGACION/RESEARCH/baseline/linux-7.1.3/…/asic_reg/gca/gfx_8_0_enum.h
 2  …/RX550-INVESTIGACION/RESEARCH/kernelbuild/linux-7.1.3/…/asic_reg/gca/gfx_8_0_enum.h
 3  …/RX550-INVESTIGACION/RESEARCH/working/linux-7.1.3/…/asic_reg/gca/gfx_8_0_enum.h   <- en B
 4  …/RX550-INVESTIGACION/rx550-upstream-7.2.8/linux-7.2.8/…/asic_reg/gca/gfx_8_0_enum.h
 5  /home/lucas/kernel-dev/linux/…/asic_reg/gca/gfx_8_0_enum.h
 6  /home/lucas/linux-opt/drivers/…/asic_reg/gca/gfx_8_0_enum.h
 7  /home/lucas/rx550-analysis-7.2.8/linux-7.2.8/…/asic_reg/gca/gfx_8_0_enum.h
 8  /home/lucas/rx550-upstream-7.2.8/linux-7.2.8/…/asic_reg/gca/gfx_8_0_enum.h

A\B   (7 elementos: 1, 2, 4, 5, 6, 7, 8 — las 7 rutas que 967 no vio)
```

Y el segundo conjunto, el que decide la conclusion:

```
C  = fuentes de la maquina que ROTULAN las 5 tablas   -> 1 elemento, 348 paginas
       ~/Descargas/RX550-INVESTIGACION/05-FUENTES-PDF/gcn3-isa.pdf
       (cap.12.1 SOP2 / 12.2 SOPK / 12.3 SOP1 / 12.4 SOPC / SMEM; Table 5.1)
D  = fuentes de la maquina dentro del corpus declarado -> 0 elementos
C\D = C completo
```

**Las 4 fichas de tabla existen en la maquina, fuera del filtro, y el filtro es la evidencia.**

### 5.2 Aristas del corpus: que ASIC cubre cada fichero encontrado

Medido con `wc -c` + `sha256sum` sobre `…/asic_reg/gca/`:

| fichero | bytes | sha256(12) | ASIC | ¿aplica a gfx803? |
|---|---|---|---|---|
| `gfx_7_2_enum.h` | 343067 | `4882624c0e6a` | gfx72 / GCN5 | NO — otra generacion |
| **`gfx_8_0_enum.h`** | **376576** | `fa6b8ff974fc` | **gfx803 / GCN3 = ESTE ASIC** | **SI** |
| `gfx_8_1_enum.h` | 373541 | `dcbd8717f1ea` | gfx820 / Polaris20 | NO — otro ASIC de la familia |
| `gfx_8_0_d.h` | 244444 | `299228e0bbd7` | gfx803 | SI (definiciones de registro) |
| `gfx_8_0_sh_mask.h` | 1136970 | `c2dd6e2f68a0` | gfx803 | SI (mascaras) |
| `gfx_8_0_ip_params.h` | — | — | — | **NO EXISTE** (comprobado) |
| `gcn3-isa.pdf` | 2752924 | `8e49a3767b33` | GCN3 = ESTE ASIC | SI (es LA ISA) |
| `vega-isa.pdf` | — | — | GFX9 / Vega | NO — generacion siguiente |
| `llvm-mc 22.1.8` (`amdgcn`) | — | — | ANYAMDGPU | SI — `gfx803` registrado |

Los tres ficheros que `967:174` menciona como candidatos (`sdma1_*_sh_mask.h`, `nbif_*`, `dcn_*`)
estan efectivamente ahi, y son de otros bloques. **`967` acierta en eso** y no hay que tocarlo.

**H3 queda con contenido, no vacio**: `gfx_8_1_enum.h` y `vega-isa.pdf` SI son material de otra
generacion, y son `NotApplicable` a `1002:699f`. Eso no es un escape: el aplicable
(`gfx_8_0_enum.h` + `gcn3-isa.pdf`) existe y esta medido.

---

## 6. CONTRAFACTUAL — de verdad medido, no supuesto

Pregunta: dado **este** ASIC (gfx803), si la **tabla de campos de operando** no estuviera
disponible, que propiedad **observable** del PM4 cambia?

**Medida del oraculo alternativo.** `llvm-mc` 22.1.8 registra `amdgcn` y conoce `gfx803` (=este
ASIC). Ensambla operandos sin consumir ninguna tabla de campos:

```
$ printf 's_endpgm\nv_mov_b32 v0, 0x5\nds_write_b32 v0, v1\n' \
  | llvm-mc -triple=amdgcn-amd-amdhsa -mcpu=gfx803 -show-encoding
s_endpgm            ; encoding: [0x00,0x00,0x81,0xbf]
v_mov_b32_e32 v0, 5 ; encoding: [0x85,0x02,0x00,0x7e]
ds_write_b32 v0, v1 ; encoding: [0x00,0x00,0x1a,0xd8,0x00,0x01,0x00,0x00]
```

`ds_write_b32 v0, v1` sale en **8 bytes** con los dos operandos ya colocados. El layout de campos
**se obtiene sin el fichero de campos de operando**.

Advertencia metodologica que tambien queda registrada: en una primera pasada `llvm-mc` imprimio 2
errores de operando y **salio con `exit=0`**. Es el caso exacto de `AGENTS.md` §26
(`exit 0 != valid result`). Se detecto mirando el `stderr`, no el codigo, y el resultado real de
esa tanda fue `exit=1`. Un pipeline que solo mirase el status habria contabilizado dos fuentes de encoding
que no existen.

**Resultado del contrafactual:**

| propiedad observable | con tabla de campos | sin tabla de campos (solo `llvm-mc` + opcode) |
|---|---|---|
| dword/bytes de una instruccion GFX8 | se obtiene | **se obtiene igual** (medido arriba) |
| colocacion de operandos VGPR/SGPR | se obtiene | **se obtiene igual** |
| que opcode tiene `s_load_dword` | **NO se obtiene** | **NO se obtiene** — `llvm-mc` no dice de que tabla salio |
| cabecera de paquete PM4 para el CP | NO | NO — y **tampoco con la tabla** |

Conclusion del contrafactual, que es la que decide si el bloqueo declarado es real:

> **El bloqueo declarado es IMPROCEDENTE tal como esta escrito.** La tabla de campos de operando
> no es lo que bloquea un programa con efecto observable: hay un oraculo independiente
> (`llvm-mc`, `gfx803`) que ya entrega el encoding completo con operandos. Lo que si falta, y no
> es una tabla de opcode, es **la identidad de las 5 tablas** (para no llamar opcode a un valor
> ambiguo) y, mas adelante, **las cabeceras de paquete PM4**, que son otra cosa y estan en otro
> sitio.

`NOT_REQUIRED` para el fichero de campos comovia de encoding; `REQUIRED` para la identidad de
tabla; el gate PM4/CP queda abierto y **fuera** del alcance que este nodo cerraba.

---

## 7. Lo que ENUMERE y lo que NO PUDI ENUMERAR

**Enumerado y medido:**

- Las 8 copias machine-wide de `gfx_8_0_enum.h`, con ruta exacta, y su hash identico.
- Las 4 dentro del repo (`baseline`, `kernelbuild`, `working`, `rx550-upstream-7.2.8`), las 4 fuera.
- `/var/tmp/rx550` medido en bytes (15.2 GB) y con 0 cabeceras de ISA dentro.
- Headers de kernel instalados: el directorio `asic_reg/gca` **no existe** en ninguno de los dos
  kernels. Ausencia enumerada con comando, no supuesta.
- BTF/dumps de amdgpu en el repo: 0 (solo coincidencias de nombre en scripts de compilacion).
- `06-INGENIERIA-INVERSA/corpus`: 15 ficheros, todos BC3/texturas, ninguno de ISA.
- La ISA GCN3: 348 paginas, las 5 tablas por capitulo, Table 5.1 de campos, posiciones SDWA.
- El corpus entero con `find -prune` sobre el repo (~2 s) y con `plocate` sobre la maquina.

**NO enumerado — va al residual:**

1. **El indice `plocate` tiene ~10 h** (construido 00:33, medido 10:39). Cualquier fichero creado
   en esa ventana es invisible para el filtro global. Un `updatedb` (~30 s, sin sudo) lo cierra.
2. **`/var/tmp/rx550` no se recorrio en profundidad**: solo se midio su tamano, se listaron sus 59
   entradas de primer nivel y se hizo la consulta por nombre. Un `find` de 15.2 GB completo seria
   el unico modo de negarlo; se considera desproporcionado y queda dicho.
3. **El arbol del repo se filtro por nombre de fichero.** Un `.h` con las tablas dentro de otro
   nombre no se encontraria. Dentro de `08-ARQUITECTURA` solo hay 3 `.h`, dentro del repo solo
   las 4 rutas de arriba, asi que el margen es pequeño — pero el filtro **es** por nombre.

---

## 8. ACCION_DISCRIMINANTE — el siguiente paso mas barato

No hace falta mas busqueda de ficheros: **la afirmacion ya esta refutada por dos vias
independientes**, y las cuatro hipotesis estan resueltas:

| | veredicto | como se cerro |
|---|---|---|
| **H1** no existe en ninguna fuente alcanzable | **REFUTADA** | `gcn3-isa.pdf` esta en la maquina, 348 p, nombra las 5 tablas por capitulo (`C\D = C`) |
| **H2** existe en fuente no indexada por el filtro | **CONFIRMADA** | `A\B = 7`; el corpus era 1 extraccion parcial untracked de 3 directorios |
| **H3** solo para otra generacion | **CONFIRMADA y PARCIAL** | `gfx_8_1_enum.h` (gfx820) y `vega-isa.pdf` (GFX9) son de otra: `NotApplicable`. El aplicable existe |
| **H4** el filtro excluia lo que-si estaba | **CONFIRMADA** | y el filtro es **unitario**: 5 tablas dentro de 1 fichero, no 5 ficheros |

**La accion mas barata que separa lo que queda abierto** (no H1/H2/H3/H4, ya cerradas):

```
ACCION: pdftotext -f 258 -l 288  ~/Descargas/.../gcn3-isa.pdf   # capitulo 12: las 5 tablas
        + volcar la identidad de tabla por opcode a una tabla con provenance
OBSERVABLE: un mapa {opcode -> (valor, TABLA)} para los 216 SQ_S_* de gfx_8_0_enum.h
DISCRIMINANT: si el cap.12 da la tabla de los 216 nombres -> las 5 tablas quedan CERRADAS
              como datos y el bloqueo cae entero.
              si NO cubre los 216 -> el hueco es de COBERTURA, no de ausencia, y hay que decirlo asi
COSTE: <10 s de CPU, escritura de 1 fichero, sin GPU, sin sudo, sin runtime
PASS:   los 216 nombres con TABLA asignada y trazada a capitulo+pagina
FAIL:   subconjunto -> el estado pasa a PARTIAL, no a PROVEN_ABSENT
INVALID: pdfinfo != 348 p  -> artefacto cambiado, abortar
```

Es la accion correcta porque **es la unica que puede convertir el motivo 2 en cierre**, y es
barata frente a cualquier busqueda adicional de ficheros, que ya se ha visto que no es el
problema.

---

## 9. Lo que este nodo NO cierra

- `RUNTIME_REQUIRED` sigue abierto, y ahora por una razon distinta y mejor nombrada: falta la
  cabecera de paquete **PM4** para el CP, no la tabla de opcode ni la de campos.
- La extraccion de la ISA a tabla machine-readable no existe todavia (fase 8 de la accion).
- La identidad de tabla sigue siendo `MODEL_CHOICE` mientras no venga del capitulo 12 y no de mi
  convencion de agrupacion por prefijo. `013:176-178` ya lo dice y sigue en pie.
- `CONTRADICTION` abierta contra `DRIVER-MISSION-STATE.md:136-138` y `013:327`. **Este nodo no los
  modifica**: no son suyos. Lo que corresponde es que quien los escribio decida si los corrige o
  mantiene el texto viejo junto a la correccion, como se hizo con 013.
- No se ha tocado la GPU, el runtime, ningun modulo, ni `sudo`. No se ha modificado ningun
  fichero existente. Escritura: este fichero y nada mas.
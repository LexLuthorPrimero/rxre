# Reconciliación del nodo Q5-MEM-TABLES — 2026-10-03

AUTORIA=global-coordinator · WORK_CLASS=reconciliación · WRITE_EXECUTION=1 fichero nuevo
RUNTIME=NOT_RUN · GPU=INTACTA · SIN_SUDO · SIN_COMMITS · LOCK=q5-memtables

Segundo turno. El primero esta en
[`2026-10-03-reconciliacion-Q5-ISA-CAP12.md`](2026-10-03-reconciliacion-Q5-ISA-CAP12.md).
Aqui hay **dos errores**, los dos del mismo tipo, y **un hallazgo que no yieldo ningun worker** y
que toca la cabecera que el proyecto llama su fuente primaria de opcodes GFX8.

---

## 1. Estado del nodo

```
NODE_ID        Q5-MEM-TABLES
WORKER         sesion-missing
DESPACHADO POR global-coordinator, bajo cerrojo .write-lock/q5-memtables
CERRADO POR    RESOLVED_WITH_RESIDUAL_UNIVERSE
ACEPTADO POR   global-coordinator = SI (verificado, no heredado)
HIPOTESIS      H1 REFUTADA en VALOR, H2 REFUTADA en cobertura, H3 REFUTADA
               cobertura memoria 2,3 % ausente  vs 14,4 % de escalares
               valor memoria      45 DIFIERE de 353
```

Artefactos, hash **medido por el coordinador**:

```
08-ARQUITECTURA/artifacts/Q5-MEM-TABLES/
  q5-mem-tables.md     68743 B   7b7f43fad5f7e3c530a9c705309c5cfab7b5ce4b3953fa9c396490e25a74b0ce
  mem-tables.txt      119840 B   ec53db09a5f202f2f0a99522c40f5431d15b8eff6e47b57cf138ec03a2a8d36c
  mem-coverage.tsv     28163 B   54028b93efa44d32885ec948e223c06da1284c1dd91b14529517f5920c4b29e2
```

## 2. Verificación independiente

| # | Afirmación del worker | Verificación del coordinador | Estado |
|---|---|---|---|
| V1 | Los cuatro artefactos de Q5-ISA-CAP12 intactos | los 4 sha coinciden con los fijados | CORROBORADO |
| V2 | Los 5 prefijos del **enunciado** no existen | ver §3 | **el enunciado era MÍO y estaba mal** |
| V3 | `SQ_DS_`=145, `SQ_BUFFER_`=59, `SQ_TBUFFER_`=16, `SQ_IMAGE_`=91, `SQ_FLAT_`=42 | `grep -c` sobre el header, uno a uno | CORROBORADO |
| V4 | 353 filas = 295 COINCIDE + 1 MULTIFILA + 45 DIFIERE + 8 AUSENTE + 4 DEC/HEX incoherente | recountado por la columna 4 del TSV, confirmada leyendo la cabecera | CORROBORADO |
| V5 | Cuadre por familia contra el header | 145+59+16+91+42 = 353; y por familia 143+1 / 58+1 / 16 / 79+10+2 / 4+35+3 = 353 | CORROBORADO |
| V6 | 8 ausentes concretos | los 8NOMBRES coinciden con los del TSV | CORROBORADO |
| V7 | El capítulo 12 tiene 178 form-feeds y el offset impreso→PDF es +106 | 178 páginas reutilizadas de `cap12.txt`, no reextraídas | COHERENTE, no re-medido por mí |

## 3. ERROR MÍO — el enunciado del nodo iba con 4 prefijos que no existen

Yo escribí en el encargo: "compara `SQ_LDS_*` / `SQ_MUBUF_*` / `SQ_MTBUF_*` / `SQ_MIMG_*` /
`SQ_FLAT_*`". **Cuatro de los cinco no existen.** Medido:

```
SQ_LDS_    0        SQ_MUBUF_  0        SQ_MTBUF_  0        SQ_MIMG_  0        SQ_FLAT_  42
```

Esos nombres los copie del informe del worker del turno anterior, que decia "DS/LDS,
MUBUF, MTBUF, MIMG, FLAT" — donde **DS/LDS** y los demas eran nombres de *seccion del
documento*, no prefijos del header. Los confundi con el otro vocabulario y se los di al
siguiente worker como si fueran medidas. **No habia medido el enunciado que yo mismo escribi.**

Lo que el worker hizo con eso es lo que hay que hacer, y por eso el nodo no se perdio:

```
ANTES DE CONTAR   filtro literal sobre el enunciado  ->  0, 0, 0, 0, 42
CONTROL POSITIVO del MISMO filtro, con prefijos que si existen:
                  SQ_DS_=145  SQ_BUFFER_=59  SQ_TBUFFER_=16  SQ_IMAGE_=91
CONCLUSION        los 0 son REALES y el filtro funciona; el enunciado estaba mal
DECISION          ampliar el alcance a los prefijos reales, DECLARADO en el artefacto
```

Es la cuarta vez en dos turnos que un filtro devuelve un cero. Tres de las cuatro veces el cero
era **defecto del instrumento o del enunciado**, y una vez era un hecho. Un turno entero se
puede perder por no distinguir las dos cosas, y por eso el control positivo es obligatorio
antes de reportar cualquier ausencia.

## 4. ERROR DEL WORKER — y lo declaro el mismo

El worker declara en su propio artefacto que su primera version dio **DS 138 con valor / 7
ausentes**, y que la correcta es **142 / 3**: cuatro "ausentes" falsos, tres de ellos defectos
reales del texto del PDF (descripcion partida a un espacio, parentesis sin cerrar, errata
`ox`). Lo escribe en vez de esconderlo, y eso es exactamente lo que hace que su cifra final sea
utilizable. Su parser final declara **0 lineas con cola de valor no capturadas** en las cinco
tablas.

## 5. HALLAZGO DEL COORDINADOR — colision interna en `gfx_8_0_enum.h`, la fuente primaria del proyecto

Las cinco familias de memoria son cinco tablas de opcode autonomously cerradas. Medi
**colisiones internas**, es decir, un mismo valor asignado a dos nombres **dentro de la misma
tabla** — que es lo unico que no se explica por la dimension "familia" que el finding 967
identifico:

```
SQ_DS_       145 nombres   valores repetidos  0
SQ_BUFFER_    59 nombres   valores repetidos  0
SQ_TBUFFER_   16 nombres   valores repetidos  0
SQ_IMAGE_     91 nombres   valores repetidos  0
SQ_FLAT_      42 nombres   valores repetidos  2      <-- ESTE

  0x66  ->  SQ_FLAT_ATOMIC_SMAX_X2     y     SQ_FLAT_SCRATCH_LO     (linea 4041)
  0x67  ->  SQ_FLAT_ATOMIC_UMAX_X2     y     SQ_FLAT_SCRATCH_HI     (linea 4042)
```

Y el ISA no tiene esos dos:

```
SQ_FLAT_SCRATCH_LO   status=AUSENTE_DE_TABLA_ISA
SQ_FLAT_SCRATCH_HI   status=AUSENTE_DE_TABLA_ISA
```

Por que importa, y no es trivia: `0x66` y `0x67` son **dentro del bloque `FLAT_ATOMIC_*_X2`**
(`0x60`–`0x6c`), no fuera. Para un emisor PM4, el opcode `0x66` **no distingue**
`SMAX_X2` de `SCRATCH_LO`. Cuatro de las cinco tablas estan limpias; la quinta no, y el
proyecto no lo tiene registrado.

```
LO QUE ESTA MEDIDO     el header asigna dos veces 0x66 y dos veces 0x67 dentro de la
                       familia SQ_FLAT_; el ISA no lista SCRATCH_LO ni SCRATCH_HI.
LO QUE NO ESTA MEDIDO  cual de los dos valores es el que el silicio ejecuta. Eso es RUNTIME
                       y no se ha tocado. Ni si el defecto esta en el header o en la
                       extraccion del ISA.
LIMITE DE ALCANCE      las 4 copias de gfx_8_0_enum.h del arbol (working, baseline,
                       kernelbuild, rx550-upstream-7.2.8) son byte-identicas con sha
                       fa6b8ff9…d63. Una version de kernel distinta con el mismo contenido
                       es coherente con "cabecera upstream sin cambios", pero 4 copias en un
                       mismo proyecto NO prueban que sea la de upstream. NO_DETERMINED.
```

## 6. REDUCCION QUE TAMPOCO YIELDO EL WORKER — las 45 DIFIERE son 9 clases, no 45 fallos

El worker reporto "45 DIFIERE" como un bloque. Medidas una a una, se descomponen en **nueve
pares (familia, diferencia)** y nada mas:

```
FLAT   dif=+16   n= 7    hdr 64,65,66,67,97,98,99      bloque ATOMIC, hasta SUB / SUB_X2
FLAT   dif=+15   n=18    hdr 68..76, 100..108           bloque ATOMIC, desde SMIN en adelante
FLAT   dif= +8   n= 6    hdr 16..21                     LOAD_UBYTE .. LOAD_DWORDX2
FLAT   dif= +7   n= 1    hdr 22                         LOAD_DWORDX3
FLAT   dif= +9   n= 1    hdr 23                         LOAD_DWORDX4
FLAT   dif= -1   n= 1    hdr 30                         STORE_DWORDX3
FLAT   dif= +1   n= 1    hdr 31                         STORE_DWORDX4
IMAGE  dif= +1   n= 4    hdr 16..19                     IMAGE_ATOMIC_SWAP/CMPSWAP/ADD/SUB
IMAGE  dif= +2   n= 6    hdr 68..73                     IMAGE_GATHER4_L/B/LZ/C/B_CL/C_CL
                                              suma  45
```

De ahi salen **cinco reglas candidatas**, no 45 hypothyesis:

```
R1  FLAT_LOAD_*   offset +8 uniforme, con X3(0xF) y X4(0xE) TRANSPUESTOS
                  -> si se transpone, los 8 quedan en +8 exacto.        8 entradas
R2  FLAT_STORE_*  la MISMA transposicion X3<->X4                      2 entradas
R3  FLAT_ATOMIC_* base +16 y despues +15: un desplazamiento de UN hueco
                  a partir de SMIN. MEDIDO, y el hueco es de la ISA, no del parser:
                  en el texto crudo (cap12.txt 9420-9445, impreso 12-177) la tabla de AMD
                  salta de 51 (0x33) SUB a 53 (0x35) SMIN. NO hay fila, NO hay marca de
                  "reserved", NO hay nada en 52. El mismo salto aparece en 84 (0x54) en
                  el bloque X2.                                        25 entradas
R4  IMAGE_ATOMIC_* +1: un hueco antes de SWAP                          4 entradas
R5  IMAGE_GATHER4_* +2: dos huecos antes de GATHER4_L                  6 entradas
```

**La explicacion mas atrativa queda REFUTADA por medicion, y por eso va escrita.** R3 y R4
tenian una causa elegante y unica: que la ISA incluyera `*_ATOMIC_CAS` y el header no, porque
`ATOMIC_CAS` es de una generacion posterior. Medido sobre las 348 paginas:

```
FLAT_ATOMIC_CAS   cap12.txt 0   libro entero 0
IMAGE_ATOMIC_CAS  cap12.txt 0   libro entero 0
GLOBAL_ATOMIC_CAS cap12.txt 0   libro entero 0
ATOMIC_CAS         0 apariciones en 348 paginas
```

No hay CAS en ningun sitio. **R3, R4 y R5 siguen sin explicar.** Quedan 29 entradas de las 45
— dos tercios del residuo— sin causa identificada, y ahora con la pregunta bien Plantada: no es
"el ISA va desfasado", porque un desfase no inserta huecos.

### 6 bis R3 SI ESTA MEDIDO, y el hueco es de la ISA

 Contrarye lo que la primera redaccion de esta seccion decia. Se puede medir en una
lectura, asi que se midio, en vez de dejarlo como "inferido de la aritmetica":

```
cap12.txt lineas 9420-9445, impreso 12-177, tabla 12.13 "FLAT Instructions for the
Opcode Field (Cont.)", leida del texto crudo y no del TSV:

  FLAT_ATOMIC_SUB      32b, dst -= src. ...            51 (0x33)
  FLAT_ATOMIC_SMIN     32b, dst = (src < dst) ? ...    53 (0x35)
                                                 ^^^ salta el 52 (0x34)
  y el mismo salto en el bloque X2:  83 (0x53) SUB_X2  ->  85 (0x55) SMIN_X2
```

El hueco **existe en la tabla publicada por AMD**. No es del parser, no es un salto de pagina
del extractor — se descarto esa explicacion primero, porque la primera fila que mire el
worker-era justo un marcador de pagina— y no hay ninguna fila ni marca de `reserved` en 52.
Una tabla que salta un valor en silencio no es una tabla que declara una reserva.

Quedan dos lecturas, y **esta medicion no las separa**:

```
LECTURA A   la ISA reserva 0x34 y 0x54 sin documentarlo, y el header compacta el rango.
            Consistente con el patron medido (+16 antes del hueco, +15 despues), pero
            exige que un hueco exista en el original.
LECTURA B   los dos documentos numeran cosas distintas, y el "+16" no es un desplazamiento
            sino dos Tables distintas que CASan por nombre.
```

Lo que si queda establecido: **el defecto, si lo hay, no es de este proyecto.** La tabla que
el proyecto cita tiene un salto sin declarar; el header tiene una duplicacion sin declarar
(§5). Los dos irregularities caen en la misma tabla y ninguno de los dos esta anotado.
Y las dos happen sobre `FLAT`, que es justo la familia con la unica colision interna de las
cinco.

## 7. Cuadro comparativo, que es lo que hay que llevarse

```
                          escalares (216)      memoria (353)
  con valor                    185  85,6 %        345  97,7 %
  ausentes                      31  14,4 %          8   2,3 %
  DIFIERE                        2   0,9 %         45  12,7 %
  prefijos con >= 92,9 % cobertura    n/a                 si, los 5

  COBERTURA   la fuente primaria cubre memoria MEJOR que escalares. H1 confirmada, H2 refutada.
  VALOR       la fuente primaria discrepa MAS en memoria. 45 contra 2.
```

Esa asimetria es el resultado que no era obvio al abrir el nodo, y va contra la intuicion de
"cuanto mas mainstream, mas fiable": **el capitulo 12 esta mejor documentado donde hay tabla, y
peor donde hay enumeracion dispersa.** 187 lineas sueltas contra 5 tablas: las tablas se
copiaron bien, las lineas se transcribieron peor.

## 8. Estado de las contradicciones

```
CONTRAD-Q5-AUSENCIA-TABLAS   VIVA, ahora con CUARTO input. Ningun lado arbitrado.
  Apoya a AFIRMA   en un punto nuevo y verificable: de las familias que el ISA documenta,
                   5/5 tienen tabla y 0/6 de las escalares la tienen. "No hay tabla" es
                   cierto, y cierto precisamente donde la cobertura es peor.
  Apoya a REFUTA   en otro: la cobertura de memoria es 97,7 % y aun asi quedan 45 DIFIERE
                   y una colision interna. La tabla "que faltaba" no solo no resolvia el
                   bloqueo: no es ni siquiera autoritativa frente al header.
CONTRAD-Q5-GFX8-ES-GCN3      VIVA, sin cambio. Este nodo no la toca.
LAS 2 DIFIERE DE SQ_S_*       SIN ARBITRAR, con las dos fuentes. Una es una
                              auto-contradiccion de la propia ISA (ATC_PROBE_BUFFER con
                              0x26 duplicado) y la otra es decimal-contra-hex (LSHR_B64).
LAS 45 DIFIERE DE MEMORIA     SIN EXPLICAR. Cinco reglas candidatas, una refutada.
LA COLISION 0x66/0x67         NUEVA, sin registrar en el proyecto.
```

## 9. Lo que este documento NO dice

```
NO dice que los valores del header sean erroneos.  Dice que dos de ellos estan duplicados
                                                   dentro de la misma tabla.
NO dice que el ISA tenga razon.                Ni que el header la tenga. 45 DIFIERE sin
                                                   arbitrar y una duplicacion sin explicar.
NO dice que R3 sea una ranura reservada.       Es INFERIDO de la aritmetica. El texto de la
                                                   tabla no se ha leido fila a fila.
NO dice que la colision 0x66/0x67 sea un bug de AMD.  Puede serlo, puede ser una
                                                   artefacto de extraccion, y no hay nada
                                                   medido que decida entre las dos.
NO dice nada del silicio.                      RUNTIME=NOT_RUN. Ni una lectura de registro.
NO cierra ninguna contradiccion.
```

## 10. El nodo siguiente, con su discriminante

```
Q5-FLAT-ATOMIC-BLOQUE      la pregunta que §6 deja abierta, y es de una sola medicion:
                           leer las filas REALES de la tabla FLAT del cap.12 y comprobar si
                           el valor 52 (y 84) aparece en la tabla o no.
                             aparece  -> R3 es un hueco de la ISA, y R4 se mira igual
                             no aparece -> el parser se salta una fila, y las 25 DIFIERE
                                          de R3 son defecto del instrumento, no del documento
                           coste: <10 s CPU, sin GPU, sin sudo, con cap12.txt ya extraido.
                           Es el nodo mas barato y mas discriminante que queda abierto.
```

Y en paralelo, sin nodo todavia, queda **CONTRAD-Q5-CABECERA-PM4-CP**: la reconciliacion del
turno anterior escribio que el bloqueo que sobrevive a Q5 no es una tabla de opcode ni de
campos, sino la cabecera de paquete PM4 para el CP. Todo lo medido hoy es consistente con esa
afirmacion y ninguno de los dos nodos la toca: la cobertura de opcode estaba casi cerrada y el
bloqueo sigue donde estaba. Esa es la frontera que merece el proximo esfuerzo grande, no esta.

---

```
AUTORIA=global-coordinator
WORK_CLASS=reconciliación
WRITE_EXECUTION=1 fichero nuevo en 08-ARQUITECTURA/decisions/ bajo cerrojo q5-memtables
RUNTIME=NOT_RUN · GPU=INTACTA · SIN_SUDO · SIN_COMMITS · MODIFICADOS_CRITICOS=0

INPUTS_VERIFICADOS
  HEAD                     3d89682195b03f0244a5a2945f2a9567dff704eb
  q5-mem-tables.md         7b7f43fad5f7e3c530a9c705309c5cfab7b5ce4b3953fa9c396490e25a74b0ce
  mem-coverage.tsv         54028b93efa44d32885ec948e223c06da1284c1dd91b14529517f5920c4b29e2
  mem-tables.txt           ec53db09a5f202f2f0a99522c40f5431d15b8eff6e47b57cf138ec03a2a8d36c
  Q5-ISA-CAP12 (4)         d3c8ad7f / 877b9202 / a42d1538 / 175ce7da   INTACTOS
  gfx_8_0_enum.h           fa6b8ff974fccdd54aa0e1b6a6430508a558fd263ead90eaf70bef262e4d5d63
  STATE.md                 21f8ca0e346ea271494b050bd5b9ef4e4c0370f604e9da3baf25c0dd9c9a661b  INTACTO
  968-q5-universo          f46e67e251c0295545d2845893e2e009467e521db7dcfd56d23c0d544e14f8d2  INTACTO
  extraccion propia del ISA  pdftotext -layout rc=0, 17667 lineas, stderr vacio
```

# 189 · Diecinueve caracteres chinos en un proyecto que escribe en castellano, y por qué la mitad no se pueden borrar solos

```
CLASSIFICATION=TOOLING+MEASUREMENT · TRACK=VERIFICATION
CORPUS=RESEARCH/working/linux-7.1.3 · HARDWARE_SCOPE=NONE
WORK_CLASS=READ_ONLY/EVIDENCE · WRITE_LOCAL=PROPIOS · MODIFICATIONS_CORPUS=0
RUNTIME=NOT_RUN · GPU INTACTA · CERROJOS=0
```

## Qué resuelve

Me colaron caracteres CJK unas diez veces en una sesión, cada vez detectados
porque los releía al escribir el informe siguiente. Eso no es una comprobación,
es una costumbre, y las costumbres fallan. Así que se automate: `tools/lint.py`
escanea el proyecto entero y distingue **cuatro** clases, porque resultaran
indistinguibles si no.

Y el resultado no es «19 en mis ficheros». Es esto — y las líneas de este
documento que contienen ideogramas están **declaradas exentas** en
`lint.py`'s `INTENCIONALES`, porque aquí son la evidencia y borrarlas sería
destruir el hallazgo:

```
115 hallazgos:
  CJK_SUSTITUIDO   31    pegado a una palabra latina: OCUPA el lugar de una
                        palabra perdida. No se corrigen solos
  CJK_INSERTADO     6    intercalado entre espacios. NO significa "borrable"
  PERMITIDO        64    ficheros cuyo ASUNTO es la integridad del texto
  ANGLICISMO       14    cuatro palabras sin uso técnico legítimo

+ 2 defectos estructurales de PENDIENTE=, ambos corregidos
```

## 1 · La clase que decide si algo se puede borrar

```
el encoder写入, sin recalcularla        <- SUSTITUIDO
fronteras y路况, no afirmaciones      <- SUSTITUIDO
del |， del ;                          <- INSERTADO
```

**Sustituido** es el CJK pegado a una palabra latina: ocupa el lugar de una
palabra que se perdió. Borrarlo deja una frase distinta y peor —
`el encoder, sin recalcularla` no dice lo que decía `el encoder escribe,
sin recalcularla`.

Y aquí está la parte que **`INSERTADO` tampoco significa «se borra»**, contra lo
que escribí en la primera versión de la herramienta:

```
el propio AGENTS.md declara que no 设置 permisos     <- INSERTADO por la regla
|                          閤 per-CPU struct ...     <- INSERTADO por la regla
```

Cuatro de los seis `INSERTADO` reales del proyecto son **sustituciones rodeadas
de espacios**, y la geometría no las distingue de una inserción: hay un espacio a
cada lado en ambos casos. Un filtro que las borrara habría produced cuatro frases
rotas creyendo que las arreglaba.

Lo único inequívoco es la **puntuación de ancho completo usada como
puntuación**: `，` donde va una coma. Eso se cambia sin entender nada, y son las
únicas siete que corregí.

## 2 · Un detector que se suicide sobre su propia evidencia

Entre los CJK estaban:

```
findings/117-doclint-no-se-mira-el-80.md       el hallazgo entero es sobre doclint
findings/MIG-07.5-SELF-METHODOLOGY-GAP...md   tokens CJK citados como evidencia
01-AUDITORIA/.../DOCUMENTATION-CENSUS.md      cita los tokens que encontró
08-ARQUITECTURA/tools/docscan.py              sus regex SON clases de caracteres CJK
02-ARQUITECTURA/AGENTS-ADVERSARIAL-AUDIT.md   cita los 9 tokens de su tabla
```

**Corregirlos destruye el hallazgo.** El único modo de que un detector de
integridad sirva es que no se suicide sobre el fichero que documenta el
integrity check. Así que hay una lista de excepciones **declarada** —64
ocurrencias— y esas se reportan como clase `PERMITIDO`, **no** se esconden en un
filtro: un filtro invisible hace que el recuento de fallos parezca menor de lo
que es.

Es la misma regla que las citas de ejemplo: una cita declarada falsa no se
corrige.

## 3 · Mi detector dio 852 falsos positivos y los reporté como hallazgos

La primera versión de la clase `ANGLICISMO` llevaba `writes`, `reads`, `prints`,
`returns`, `handles` y `toolkit`:

```
923 hallazgos: ANGLICISMO 852, CJK 69
```

**852 de 923 eran falsos.** `writes` en «writes al registro MMIO» es correcto en
un documento de diseño, y `toolkit` en un índice de herramientas también. Quedan
cuatro palabras —`veincionado`, `adoption`, `snippet`, `arbitration`— que no
tienen uso técnico legítimo. Y 852 de 923 no es una lista con ruido: es ruido con
lista, y un informe así deja de leerse entero, que es peor que no tener la clase.

La lección es la de siempre y sigue siendo la de `147` con la tabla de opcodes:
**relleno plausible en lugar de fuente**. Una lista de palabras no verificadas se
llena de las que uno recuerda, no de las que aparecen.

## 4 · Los dos defectos de `PENDIENTE=` eran míos

La estructura que `AGENTS.md` impone es mecánicamente comprobable, y la comprobó:

```
HALLAZGO_PARTIDO       188-...:161   el nombre acababa en la linea anterior
HALLAZGO_QUE_NO_EXISTE 115-...:264   citaba un 113 con un nombre truncado
```

El primero **es el defecto para el que acabo de escribir la regla**, en un
hallazgo mío. Lo resolví acortando el nombre del fichero para que `HALLAZGO=`
quepa entero en su línea: renumerado a 188. El segundo apuntaba a
`113-dpm-table-start-es-la-base-literal.md`, y el fichero real se llama
`113-dpm-table-start-es-la-base-literal-y-los-once-usos-son-correctos.md`; un
nombre truncado parece un nombre y no es.

## 5 · Y el código del driver está limpio

```
01-AUDITORIA  11        08-ARQUITECTURA  9
02-ARQUITECTURA 13     06-INGENIERIA-INVERSA 19
04-IMPLEMENTACION  2   docs  1     07-DRIVER  1     tools  13
```

El único de `07-DRIVER` está en `outgoing-reviews/2026-09-29-driver-to-arch.md`,
un documento de revisión. `kernel/rx550_pm4.c`, `rx550_pm4.h`, `rx550_drv.c` y
`tests/test_pm4.c` **no tienen ninguno**, que es donde importa que no lo haya.

## Lo que queda abierto, con su causa

```
PENDIENTE=31 CJK_SUSTITUIDO y 6 CJK_INSERTADO ocupan el lugar de una palabra
          perdida y no se pueden reconstruir desde el texto
  | HALLAZGO=189-diecinueve-caracteres-chinos-en-un-proyecto-que-escribe-en-castellano.md
  | ESTADO=NOT_DETERMINED
  | NECESITA=el autor de cada frase. Borrar el caracter produce una frase
  |          distinta, y un texto que parece un descuido pero tiene sentido es
  |          peor que uno con un simbolo raro que se ve. Quedan 32, ninguno en
  |          ficheros de este proyecto: los cinco propios se resolvieron, cuatro
  |          por reconstruccion y uno por borrado de un marcador que sobraba
  | ALCANZABLE_SIN_ROOT=si
```

La asimetría del 4 y el 33 es el dato accionable: lo que queda no es trabajo
uniforme, es «esto es mío y esto no», y esa distinción la hace el `fichero` de
cada hallazgo.

## Procedencia

```
tools/lint.py                15 vectores, 2 con dientes comprobados
CJK_SUSTITUIDO 31            pegado a una palabra latina
CJK_INSERTADO   6            intercalado; 4 de ellos son sustituciones
PERMITIDO      64            excepciones declaradas, se reportan no se esconden
7 lineas corregidas           solo puntuacion de ancho completo, unico inequivoco
188  HALLAZGO= partido       corregido acortando el nombre del fichero
115  HALLAZGO= inexistente   el nombre real lleva sufijo y se habia truncado
07-DRIVER kernel/ tests/      0 CJK
```

## Los cinco propios, y por qué cuatro son reconstrucciones

Los cinco CJK que estaban en ficheros de este proyecto se resolvieron. **Ninguno
de los cinco se puede recuperar**: la palabra perdida no está en ningún sitio,
así que cualquier texto restaurado es una **propuesta**, y por eso se documenta
el razonamiento para que quien lo lea pueda discutirlo.

| fichero | como estaba | como queda | por qué esta lectura |
|---|---|---|---|
| `tools/claims.py:38` | `con 0类是 PROVEN` | `con 0 clases es PROVEN` | la frase se determina sola: «con 0 clases» + «es PROVEN» |
| `tools/corroboration.py:27` | `sin也已经 saber nada` | `sin saber nada` | «sin *algo* saber nada»; sólo *saber* encaja con el resto |
| `tools/implgate.py:406` | `#混Clasificarlo` | `# Ojo: Clasificarlo` | marcador de aviso al abrir línea de comentario |
| `tools/smc_copy_scope.py:1099` | `se #곱 se tiene` | `se tiene en cuenta el caso` | **no es reconstrucción**: el marcador sobraba |
| `07-DRIVER/.../2026-09-29-driver-to-arch.md:27` | `gran未定 del ABI` | `gran duda del ABI` | el título es una *pregunta* abierta; *duda* encaja con el registro |

El cuarto es el único que **no es una suposición**, y de todos modos se rompió al
aplicarlo: al borrar el marcador quedaron dos `se` separados por el salto de línea
—«Si no se / se tiene en cuenta»—, que es sintácticamente válido y no dice nada.
Se vio al releer la frase corregida, no al compilar, que es la única forma de
cazarlo.

Los cinco están ahora en **cero** CJK, y `tools/claims.py`, `corroboration.py`,
`implgate.py` y `smc_copy_scope.py` siguen con sus vectores en verde.

## CORRECCION POSTERIOR

**`CORRECTED_BY` este hallazgo, en su propia clase `ANGLICISMO`.**

La primera redacción de la herramienta afirmaba, en la documentación de la clase,
que `CJK_INSERTADO` es «intercalado entre espacios: se borra sin entender la
frase». **Es falso**, y medido sobre este mismo proyecto: cuatro de los seis
casos reales de esa clase son sustituciones rodeadas de espacios. Se cambió el
texto de la doc y se añadió el vector que lo comprueba, porque una clase con una
regla de corrección que produce frases rotas es peor que una clase sin regla de
corrección.

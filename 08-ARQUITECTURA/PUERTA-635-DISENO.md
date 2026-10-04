# PUERTA-635 — DISEÑO DEL ARREGLO, NO APLICADO

```
AGENCIA=RX550-INVESTIGACION · WORK_CLASS=DISEÑO
NODO=PUERTA-635-RENUMERADO · ESTADO=DISEÑO ESCRITO, NADA APLICADO
GENERADO=2026-10-04
GPU INTACTA · no se ha tocado sysfs, ni registros, ni dmesg, ni la GPU
NO RENUMERADO: este nodo no cambia ningun numero de hallazgo. Cero.
```

## 0. LO QUE ESTA HECHO Y LO QUE NO

**HECHO:** medir, decidir, y escribir el parche como texto.

**NO HECHO, y declarado:** no he modificado `tools/check_num_unico.py`. El parche de
§7 es un diff sobre papel. El fichero tiene el mismo sha256 que cuando empece este
nodo.

**COMO HE MEDIDO SIN APLICAR.** Las mediciones de §1 y §3 están hechas con un arnés
**externo** que carga el módulo con `importlib` y recalcula el barrido con las
definiciones del diseño, **sin escribir nada en el proyecto** (heredoc por `stdin`, ni
un fichero creado). Eso mide el efecto del diseño sin aplicarlo: no es un parche
disfrazado, es una segunda implementación de la clasificación que se compara con la
del gate sobre el mismo árbol y en el mismo instante. Donde las dos no coincidan, se dice.

**PROCEDENCIA DEL ESTADO DE PARTIDA** (si esto cambia, este documento mide otra cosa):

```
tools/check_num_unico.py            sha256 7ef0a10d27d9c1a3a00f5a247d3e072645347604b455bd85756d6f78b58f81dc
                                    70243 bytes · mtime 2026-10-04T08:40:17 · 1431 lineas
                                    git: MODIFICADO sin commitear (docstring, +22/-1)
08-ARQUITECTURA/tools/REENVIO-FINDINGS.tsv
                                    sha256 8bd6c69c665cf46066c700c660cb2a7a950b849a60036a7082020b9c1266070b
                                    19875 bytes · mtime 2026-10-04T06:17:05
git HEAD                           65fc2c575814014033756c81609957107751d103
                                    "hallazgo 1049: los 74 numeros duplicados, que bloquean y que NO"
VERSION declarada en el gate        1.2.0  (tools/check_num_unico.py:256)
```

El árbol **crece mientras se mide**, y eso no es una metáfora. MEDIDO, tres veces en este
nodo:

```
09:2x    A3 = 2236   ficheros leidos 2530
09:3x    A3 = 2237   ficheros leidos 2531
09:34:09 A3 = 2244   ficheros leidos 2537   findings/ en disco 552
```

O sea **+8 citas de la clase A en quince minutos**, sin que nadie cambiara una línea de
la puerta: los nodos que estaban escribiendo sus informes citan números renumerados.
**Todas las cifras de §2.2 y §3 salen del mismo instante, `2026-10-04T09:34:09-03:00`**,
con `findings/` en 552 ficheros. Las cifras estructurales —los conjuntos, las
intersecciones, el filtro de no-citas, los 26 de código— no se mueven; las poblaciones,
sí, y por eso llevan fecha.

---

## 1. EL DEFECTO: UNA LÍNEA, TRES CONSECUENCIAS MEDIDAS

La línea, en el fichero tal como está hoy:

```python
tools/check_num_unico.py:628     dups = {n for n, v in por_num.items() if len(v) > 1}
tools/check_num_unico.py:662                     if num not in dups:
tools/check_num_unico.py:663                         continue
```

`dups` es **local** a `citas_por_numero()` y se usa en **dos** sitios: el filtro de la
línea 662 y el recuento de la línea 682 (`distintos_numeros_duplicados`). Eso importa
para §3: la mitad del coste de romper cosas no existe, porque `dups` no se comparte con
nada.

De esa línea salen **tres** consecuencias, y sólo se había enunciado la primera.

### 1.1 La banda invisible — MEDIDA, y con una discrepancia que nadie ha reportado

`08-ARQUITECTURA/CITAS-150-ADJUDICACION.md:109-110` define la banda como `REN` = citas a números que
están como `viejo` en el mapa, e `INV` = las que además **no** están en `dups`. He
reproducido **su construcción escrita**, con su alcance (`EXCLUIDOS_PROPIO` del gate) y
sus tres formas de cita, y salen otras cifras:

| | declarada `CITAS-150` §2.3 | medida por este nodo |
|---|---:|---:|
| filas de dato `viejo & reasignado=SI` | 55 | **56** |
| `viejo` distintos en ese conjunto | 56 | **55** |
| `REN` | 255 | **273** |
| `REN ∩ dups` (VISIBLE) | 30 (2 nums) | **38 (2 nums)** |
| `REN \ dups` (INVISIBLE) | **225** (35 nums) | **224** (31 nums) |

Las dos primeras filas son **imposibles como están declaradas**: no puede haber más
números distintos que filas. El mapa tiene 57 filas y una sola con `reasignado=no`, luego
`viejo & SI` son 56 filas, y como `290` aparece dos veces, 55 distintos. La declaración
dice 55/56: **invertidas**. Registrado, no promediado.

La diferencia en el recuento la explica el árbol, y queda MEDIDA con un discriminante
—el `mtime`, no una suposición—: de las **241** citas de la clase B en el instante de
§0, **223** están en ficheros anteriores al informe de `CITAS-150` y **18** en
posteriores. O sea: **la cifra declarada 225 y las 223 anteriores al informe discrepan
en 2**, y las 18 restantes son de ficheros escritos después.

Y hay un agujero de una fila en la propia enumeración: la tabla §12 de
`CITAS-150-ADJUDICACION.md` tiene **224 filas de datos** (225 líneas de tabla con
cabecera) mientras el texto declara 225, y su clase
`RESUELVE_AL_OCUPANTE_NO_VERIFICADA` suma **39 filas** mientras el texto declara **40**
(`08-ARQUITECTURA/CITAS-150-ADJUDICACION.md:248` y `:332`). Tres cifras —225 / 224 / 223— que no
cuadran entre sí por ±1. Se declara `NOT_RECONCILED`: no sé qué fila es, y no lo
adivino.

**Un subresultado que sí queda resuelto.** Las "35" de la tabla están contaminadas por un
defecto de transcripción: **21 filas escriben el número citado sin su cero a la izquierda**
(`52` por `052`; `85`/`88`/`89` por `085`/`088`/`089`). MEDIDO:

```
por_num['052'] = ['052-srcid-de-fault-gfx8-y-tabla-de-iv-no-catalogada.md']   (1 fichero)
por_num['085'] = ['085-sb-page-walker-invalidate-siempre-obligatorio.md']    (1 fichero)
por_num['088'] = ['088-pte-system-es-la-otra-mitad-de-system-access-mode.md'] (1 fichero)
por_num['089'] = ['089-gc-hwip-bloqueado-por-capacidad-y-resuelto-estaticamente.md']
por_num['52']  = AUSENTE        por_num['85'] = AUSENTE
por_num['88']  = AUSENTE        por_num['89'] = AUSENTE
```

O sea: **`052` es un hallazgo real y único hoy, y `52` no es un hallazgo** —no puede
serlo, `RE_NUM` exige `\d{3,4}` (`tools/check_num_unico.py:307`). La puerta sí ve la
cita: en `06-INGENIERIA-INVERSA/findings/047-el-handler-si-lee-src-data.md:6`, `RE_CITA_LL` captura la cadena `'052'`,
con su cero. La tabla §12 escribió `52`.

Con la corrección de ceros, **los 35 números de la tabla son exactamente los 31 que yo
mido hoy**: el conjunto coincide número a número. Lo que no cuadra es el recuento, no el
conjunto. Y las 21 filas afectadas son las de esos cuatro números, que son 4 de los 35
—de donde sale exactamente el 35 → 31.

### 1.2 La segunda consecuencia, que NO se había enunciado: el filtro de no-citas nunca llega

`NO_CITA_FICHEROS` (`tools/check_num_unico.py:342-354`) declara **3 ficheros** cuyas
coincidencias con las tres formas de cita no son citas, y las descarta en
`tools/check_num_unico.py:667-669`. MEDIDO sobre esos 3 ficheros:

```
coincidencias de las tres formas, en los 3 ficheros declarados : 61
  de las que LLEGAN al filtro de 667 y se descartan             : 25   <- las que la puerta ve
  de las que NO LLEGAN, porque 662 las tira antes               : 36   <- las que nadie ve
```

Las 36 invisibles son del **mismo tipo** que las 25 que sí se descartan: patrones
binarios de la tabla SIB de x86-64. Y hay un dato peor dentro de esas 36:

```
11 de las 36 apuntan a numeros que SI estan en el mapa de renumerado:
   `110` x5   L659 L667 L675 L683 L699   ->  "| `01` | `110` | `[RSI + disp8]` | +1 | no |"
   `111` x5   L660 L668 L676 L684 L700   ->  "| `01` | `111` | `[RDI + disp8]` | +1 | no |"
   `1000` x1  L1304                      ->  "estable del kernel, y `1000` es el `udelay(1000)` literal"
```

Las once son **falsos positivos de manual**, no citas: dos filas de tabla SIB y un literal
de macro del kernel. Y la razón declarada para ese fichero
(`tools/check_num_unico.py:343-347`) dice *"los 3-4 digitos son PATRONES BINARIOS
(001, 010, 100, 101)"* y *"22 ocurrencias"*. MEDIDO: en ese fichero hay **58**
coincidencias, de 13 números distintos, y la declaración nombra 4 patrones y 22
ocurrencias. **La declaración es correcta por casualidad para las 22 que llegan, y no
cubre las 36 que no.**

Esto tiene una consecuencia de diseño que no es cosmetico: **cualquier clase nueva que
se defina como "cita cuyo número está en el mapa" y se compute DESPUÉS del filtro de
`dups` importa esos 11 falsos positivos.** El orden de las dos líneas decide si el
contador nuevo nace con ruido. Por eso el parche de §7 mueve el filtro de no-citas
**antes** de clasificar, y no es una preferencia de estilo.

### 1.3 La tercera consecuencia: la cita del defecto está mal, en dos sitios

El enunciado canónico del defecto —`06-INGENIERIA-INVERSA/findings/1048-el-filtro-que-excluye-a-su-propia-poblacion.md`
y `08-ARQUITECTURA/CITAS-150-ADJUDICACION.md:410-413`— cita **`tools/check_num_unico.py:635`**.
MEDIDO, ese número **no apunta al filtro en ninguna revisión que pueda comprobar**:

```
HEAD :635 |             codigo = es_codigo(rel)                     <- NO es el filtro
HEAD :641 |                     if num not in dups:                  <- el filtro esta AQUI
WORK :635 |     registro, motivos_reg, estado_reg = leer_registro_codigo(raiz)
WORK :662 |                     if num not in dups:                  <- y aqui
```

Comprobado sobre `HEAD`, `HEAD~1`, `HEAD~2` y `HEAD~3`: el filtro está en **641** en las
cuatro, y en **662** en el árbol de trabajo (+21 por el docstring sin commitear). La
cita `635` no fue correcta al escribirse: apunta a `es_codigo`, que es otra cosa. Se
registra como `CONTRADICTION` y **no la corrijo**, porque este nodo no renumera, no
reescribe prosa, y no tieneCET para una cita de línea.

Lo señalo porque es la **misma clase de defecto** que el que este nodo diseña: una
referencia a una línea que no resuelve, escrita con toda la confianza. Y porque la línea
que hay que arreglar **sigue siendo la 662** y el número que circula es el 635.

---

## 2. LA DECISIÓN

### 2.1 Por qué NO (a): ampliar `dups` y contar todo junto

No es que (a) necesite más trabajo. Es que **cambia el significado de la resta del exit 7
sin tocar la resta**, y el exit 7 existe precisamente para no hacer eso.

El argumento, sin citar a nadie:

`dups` es, por definición de la línea 628, `{n : |por_num[n]| > 1}`. La línea 662 lo usa
como **partición** de todas las citas del árbol: cada cita cae en `dups` o no cae, y no
hay tercer caso. La población de A3 es exactamente `{citas : num ∈ dups}` y su
complemento es exactamente `{citas : num ∉ dups}`.

Los números que el mapa dice que fueron renumerados **y que hoy son únicos** están, por
construcción, en el complemento. MEDIDO: de las **56** filas del mapa —**55** números
distintos con `reasignado=SI`— sólo **2** están hoy en `dups` (`1011` y `272`); los
otros **53** no. Ampliar `dups` con ellos **no agranda la vista sobre la misma
población**: sustituye la población por la unión de dos clases disjuntas, cada una con
su propio significado.

Y ahora la comparación del exit 7, que es la que duele:

```python
tools/check_num_unico.py:826     n_adv = resumen["citas_por_numero_a_duplicado"]
tools/check_num_unico.py:829     r["censo_sin_adjudicar"] = max(0, n_adv - CENSO_POBLACION)
tools/check_num_unico.py:830     if n_adv > CENSO_POBLACION:
```

`CENSO_POBLACION = 2152` (`tools/check_num_unico.py:300`) es una **declaración** de
cuántas citas a números **duplicados** fueron adjudicadas. Si `n_adv` pasa a contar
también las renumeradas, la resta de la línea 829 suma **dos defectos distintos** en un
número solo: "citas ambiguas que el censo no miró" más "citas de una clase que el censo
excluía por alcance". MEDIDO el efecto:

```
                                                  n_adv   sin adjudicar   factor
hoy, con dups solo                              2244        92          x1,00
(a) dups | {viejo & reasignado=SI}              2485       333          x3,62
(a) dups | {todos los viejo}                    2489       337          x3,66
(a) dups | {los nuevo}                          3556      1404         x15,26
```

Las tres últimas filas se miden con el **mismo** recorrido y el **mismo** filtro de
no-citas que la primera, y sólo cambia el conjunto que se une a `dups`.

Con (a), el "sin adjudicar" **se multiplica por 3,6 o por 15,3** y sigue sin identificar
**qué** citas son: sigue siendo una resta de dos recuentos, no un conjunto. Se cambia un
defecto pequeño —"el 7 no es enumerable"— por uno grande —"el 7 dice 1395 y no dice
ninguna"— usando para eso el código cuyo propósito declarado es que una medida caducada
se vea (`tools/check_num_unico.py:38-45`).

Y hay un regalo envenenado en (a): `|{viejo & SI} ∩ dups| = 2`. Una unión por **lista**,
no por conjunto, contaría dos veces las citas a `1011` y `272`. Con conjunto el total es
2485; con lista serían 2485 + 38 = **2523**. **Un cambio de una línea produce dos números
distintos según cómo se escriba**, y hoy no hay un self-test que lo distinga.

### 2.2 LA PROPUESTA: (b), dos poblaciones, dos cifras, dos denominaciones

**La decisión: la puerta clasifica cada cita por número en una de tres clases, las cuenta
por separado, y no las suma nunca.**

| clase | condición | qué es | código de salida |
|---|---|---|---|
| **A** `AMBIGUA` | `num ∈ dups` | la cita apunta a un número que hoy identifica >1 fichero | el de hoy: 6 y 7 |
| **B** `REN_OLD` | `num ∉ dups` **y** `num ∈ {viejo}` del mapa con `reasignado=SI` | la cita apunta a un número que **fue** renumerado y hoy no se ve | **ninguno** (§4.4) |
| **C** `SIN_CLASE` | ni A ni B | ni ambigua ni con historia | ninguno, pero **se cuenta y se imprime** |

Tres propiedades, y las tres son la razón de la propuesta:

1. **A no cambia de significado ni de número.** `citas_por_numero_a_duplicado` sigue
   valiendo lo que dice su nombre. El exit 7 sigue restando 2152 contra lo mismo que
   restaba antes. **No hay que renombrar nada** (§3.4).
2. **A y B son disjuntas por construcción**, no por medida: un número no tiene a la vez
   más de un fichero hoy y ninguno. Y la partición es **cerrada**: se imprime C, de modo
   que `A + B + C` es el total de coincidencias y un lector puede comprobar que no falta
   nada. Eso es lo que convierte "no lo veo" en "lo veo y lo digo que no lo veo".
3. **B es una clase, no un veredicto.** Poner un número en B no afirma que la cita esté
   mal. Afirma que **nadie ha mirado esa cita**, que es exactamente lo que se puede
   afirmar sin arbitrar destinos.

MEDIDO, con las definiciones de arriba, en el instante de §0
(`2026-10-04T09:34:09-03:00`, `findings/` en 552 ficheros, alcance `propio`):

```
ficheros leidos                       2537
A_AMBIGUA                             2244   (= lo que imprime la puerta hoy)
B_REN_OLD                              241   (= la banda invisible, filtro de no-citas ya aplicado)
C_SIN_CLASE                           5209   (se imprime para cerrar la particion)
no-citas descartadas por declaracion    61   (hoy la puerta ve 25 de ellas)
SUMA                        2244+241+5209+61 = 7755   particion CERRADA

A en codigo                            155   registradas 155   SIN registrar  0   -> el 6 ve 0
B en codigo                             36   registradas  10   SIN registrar 26   -> el 6 ve 0
numeros: |dups| = 74   |viejo&SI \ dups| = 53   |viejo&SI ∩ dups| = 2
```

De las 241 de B, **223** están en ficheros anteriores al informe de `CITAS-150` (§1.1).
La cifra que se publicaría es la **medida en el instante de la corrida**, con su
construcción escrita, y **nunca** una constante heredada de un documento.

### 2.3 Por qué NO (c): el exit 7 como resta entre dos mediciones del mismo instante

La variante (c) —que el 7 sea una resta sólo cerrable si ambas mediciones son del mismo
instante— **no se puede implementar**, y no por una razón de alcance.

Un censo, por definición, es una medición de **otro** instante: `CENSO_POBLACION` se
escribe a mano con su fecha (`tools/check_num_unico.py:296-300`). Exigir que ambas
medidas sean del mismo instante no arregla el 7: lo vuelve **permanentemente
disparable**, porque un censo no se puede re-medir sin re-adjudicar, y re-adjudicar es
un acto de trabajo, no de verificación —que es literalmente lo que dice
`tools/check_num_unico.py:64-67`.

Y el argumento de fondo, que es más básico que el del instante: **la resta de dos
recuentos no es un conjunto, aunque los dos recuentos sean del mismo instante.** El
"sin adjudicar" del exit 7 sigue sin decir qué citas son. La coherencia temporal hace
comparables dos números; no hace enumerable su diferencia. Arreglar el instante no toca
el defecto, sólo lo desplaza.

**La única forma de (c) que sobrevive** sería que el censo publicara **el conjunto** de
citas que adjudicó, y la puerta calculara la resta como diferencia de conjuntos. MEDIDO:
**eso hoy no es construible.** El artefacto del censo
`tools/citas_prosa_adjudicado.py` tiene **0 apariciones** del patrón `ruta.md:línea` —sus
132 veredictos son de estrato, con verbos de clase (`C1_AUTOCITA`, `C1_INDICE`,
`C1_INSTRUMENTO`, `C1_NUMERO`), no identificadores de cita
(`08-ARQUITECTURA/CITAS-POR-NUMERO-DECLARACION.md:64`, `:291`). Sin el conjunto no hay
diferencia de conjuntos, y por eso (c) queda **DESCARTADA con evidencia**, no con opinión.

---

## 3. EL COSTE DE ROMPER COSAS

### 3.1 El exit 3 (`EXIT_COLISION_SIN_FILA`): no se rompe — y por qué, con nombre

MEDIDO: `dups` es local a `citas_por_numero()` y el exit 3 **no lo lee**. Sale de dos
sitios, y los dos leen `col` / `por_num`, que vienen del FS:

```
tools/check_num_unico.py:720     col = fs_colisiones(por_num)
tools/check_num_unico.py:748     d5, d3 = indice_regenera_identico(idx, por_num, cob)
tools/check_num_unico.py:760     sin_fila = colisiones_sin_fila(idx, col)
tools/check_num_unico.py:772     if d3 or sin_fila:
tools/check_num_unico.py:773         codigos.append(EXIT_COLISION_SIN_FILA)
```

**Con el diseño (b) el exit 3 no cambia de valor ni de significación.** Su única
condición de breakage es que alguien 亿 Subsequent Patch, y entonces sí: si el mapa se
inyectara en `por_num` como colisiones falsas, `col` crecería en 54 números, `sin_fila`
daría 54, la cabecera del índice declararía 74 contra 128 del FS y `d5` dispararía: el 3
y el 5 saltarían a la vez. Está anotado porque es la **puerta más tentadora** para
"arreglar" esto —hacer que `dups` sea un conjunto compartido— y es la que rompe.

### 3.2 El exit 6 (`EXIT_CITA_AMBIGUA_EN_CODIGO`): aquí está el daño real

```python
tools/check_num_unico.py:774     a4 = resumen["A4_codigo"]
tools/check_num_unico.py:775     if a4["citas_en_codigo"] > 0:
tools/check_num_unico.py:776         codigos.append(EXIT_CITA_AMBIGUA_EN_CODIGO)
```

`citas_en_codigo` (`tools/check_num_unico.py:695`) se cuenta sobre `hits`, y `hits` sólo
se rellena **después** del filtro de la 662. Con (b), si `hits` se rellena para A y para
B con la misma lista, el exit 6 pasa de **0 a 26**. Trece de esos 26 están en el fuente
del driver:

```
07-DRIVER/kernel/rx550_mmio.h   5      07-DRIVER/kernel/rx550_mmio.c   2
07-DRIVER/tests/test_mmio.c     3      07-DRIVER/kernel/rx550_drv.c    1
07-DRIVER/tests/test_mc.c       1      07-DRIVER/kernel/rx550_mc.h     1
tools/dupenum.py  3   tools/regconst.py  3   tools/citas_prosa_census.py  2
tools/hcconsist.py 2   08-ARQUITECTURA/tools/doclint.py  1
08-ARQUITECTURA/tools/findings_index.py  1   tools/routeaudit.py  1
```

Aquí está la decisión que hay que tomar, y es la más fina del diseño:

**NO se pliega B en el exit 6.** Se reporta con `fichero:línea` pero no falla. Razón,
con el mismo criterio que el propio gate usa para no emitir el 4
(`tools/check_num_unico.py:777-801`): la clase B **no puede distinguir** una cita
correcta de una cita equivocada. MEDIDO: de las 39 filas
`RESUELVE_AL_OCUPANTE_NO_VERIFICADA` de `CITAS-150`, el número resuelve al ocupante y
el contexto no lleva contenido que confirme ni refute. Un exit que saltase sobre las 26
afirmaría algo que el instrumento no sabe. Un exit que no salta deja el defecto **a la
vista**, que es lo que se pedía.

Y el nombre lo dice solo: `EXIT_CITA_AMBIGUA_EN_CODIGO` — *ambigua* — no *sin adjudicar*.
Un exit que admitiese las renumeradas estaría mintiendo en su propio identificador.

### 3.3 El exit 7: no cambia, y es lo que hace que (b) sea (b)

`n_adv` (`tools/check_num_unico.py:826`) sigue leyendo
`resumen["citas_por_numero_a_duplicado"]`, que con (b) sigue siendo la clase A. MEDIDO:
`2244` contra `2152` → **92 sin adjudicar**, el mismo orden que hoy. La precedencia
`2 > 5 > 3 > 6 > 7` (`tools/check_num_unico.py:47`, y el orden real de append en
`:769-833`) no se toca. Los tres vectores del exit 7
(`tools/check_num_unico.py:1216-1241`) siguen exercising la misma rama.

Con (a), en cambio, el 7 pasa de 92 a **333** y su nombre en el diccionario de veredictos
(`tools/check_num_unico.py:966-969`) seguiría diciendo "hay citas por numero que el CENSO
no ha adjudicado", que es una frase cierta y sin embargo inútil, porque **no nombra
cuáles**. Un código de salida que emite una cifra inflada y no accionable es peor que
uno que emite una cifra correcta y accionable: el primero hace creer que hay un hueco
cerrable.

### 3.4 El nombre `citas_por_numero_a_duplicado`, y qué se rompe si no se renombra

Con (b) **el nombre no se toca, y esa es la razón de que (b) sea la propuesta**: cambiar
la semántica de una variable cuyo nombre dice lo contrario es un defecto esperando a
ocurrir, y la forma de evitarlo aquí es no cambiar la semántica.

MEDIDO, lo que (a) costaría en consumidores, porque el nombre no es interno:

```
citas_por_numero_a_duplicado     11 apariciones, en 3 ficheros
   6 dentro de tools/check_num_unico.py
        :680 (la clave del JSON)  :799 (el 4 retirado, comentado)  :826 (n_adv, el exit 7)
        :893 (la linea que la imprime)  :1179  :1182-1183  :1194  (los 3 vectores del 4/4b)
   2 en 08-ARQUITECTURA/ALIAS-VALIDEZ-MEDICION.md:356
        <- como CABECERA DE COLUMNA de la tabla que mide una multiplicacion x6,07
           entre raices distintas (:356-361)
   las 3 restantes, en el mismo fichero de la puerta
```

Y por qué la segunda fila importa más que las otras nueve: una columna de tabla es un
**contrato con un documento**, y ese documento afirma una razón.

Si se adopta (a) sin renombrar, esa columna de `ALIAS-VALIDEZ-MEDICION.md` pasa a
comparar poblaciones distintas bajo el mismo encabezado, y la afirmación ×6,07 queda sin
respaldo sin que ningún self-test lo note: **el daño lo paga un documento, no un test.**

Si en algún momento se adopta (a), lo que hay que renombrar es, como mínimo:

| ahora | nombre que describe lo que haría | consumidores a tocar |
|---|---|---|
| `dups` | `numeros_no_resolubles_hoy` | local, 2 usos (`gate:662`, `gate:682`) |
| `citas_por_numero_a_duplicado` | `citas_por_numero_no_resoluble` | 11 apariciones, 2 en un documento de medición |
| `distintos_numeros_duplicados` | `distintos_numeros_no_resolubles` | `gate:682`, `gate:897` |
| `EXIT_CITA_AMBIGUA_EN_CODIGO` (6) | **otro código**: no se puede reescribir el 6 sin cambiar su afirmación | — |

Ese último caso es el que hace que (a) sea un problema de **identidad de código**, y no
sólo de un cambio de nombre: **el 6 no se puede renombrar sin dejar de ser el 6**, porque
su identidad es semántica —`EXIT_CITA_AMBIGUA_EN_CODIGO` significa "cita ambigua", y
una cita a un número renumerado no es ambigua: es *no adjudicada*, que es otra clase
(`08-ARQUITECTURA/CITAS-150-ADJUDICACION.md:248`). Con (b) el 6 conserva su identidad entera y B es una
clase informativa nueva, que es lo que cabe en un patch.

### 3.5 Coste de tiempo y de alcance

MEDIDO: el coste de una vuelta extra del árbol es **lo que más duele de este arreglo**,
y por eso el diseño **no añade una vuelta**. Lee el mapa (57 filas, 289 líneas) una vez,
FUERA del `os.walk`, y clasifica cada cita con dos `in` sobre conjuntos ya construidos.
La clasificación cuesta una comparación de cadenas extra por coincidencia: medido, el
árnes que hace las tres clases tarda lo mismo que la puerta (≈1,8 s) porque el coste
dominante es el `open()` de 2537 ficheros, no el `if`. **MEDIDO, no estimado**: el
recuento A (2244) y el B (241) salen del mismo recorrido que la puerta ya hace, y
`leidos` coincide.

Un confounder que hay que declarar y no esconder: **la puerta se cuenta a sí misma.**
MEDIDO, contribución a la clase B de los ficheros que participan en el propio
instrumento:

```
tools/check_num_unico.py                 A=16  B=3   C=13
FINDINGS-RENUMERACIONES.md               A= 3  B=10  C=11
08-ARQUITECTURA/CITAS-150-ADJUDICACION.md A=13 B=30  C=18
08-ARQUITECTURA/tools/REENVIO-FINDINGS.tsv A=0  B=4   C=1
08-ARQUITECTURA/tools/reenvio_gate.py     A= 4  B=4   C=9
```

Y `B` crece cuando alguien escribe sobre renumerados: pasó de 224 a 241 entre dos
medidas de este mismo nodo. Eso no es un defecto: es una consecuencia
de que las cifras sean de clase y no de fichero, y se declara en el informe impreso, que
imprime `por_directorio` (`.` = raíz) para que se vea. Lo que **no** se hace es excluir
esos ficheros: excluir el índice y las herramientas es lo que hizo aparecer el "24(2)" en
el barrido de `CITAS-150` (§2.4 de ese documento), y no hay nada escrito que lo funde.

---

## 4. LA PUERTA QUE TIENE QUE PODER FALLAR

Se pueden escribir tres. Las tres son decidibles y las tres tienen control negativo. La
cuarta que **no** se escribe está en §4.4, y se dice que no se escribe.

### 4.1 INV-1 — ninguna cita queda sin clase

> *Toda coincidencia de las tres formas de cita, en un fichero legible, recibe
> exactamente una de las tres clases A, B o C, y las tres sumas son iguales al total de
> coincidencias.*

Se puede fallar de tres maneras, y las tres se fabrican en el self-test: una clase
devuelta dos veces, una clase saltada, o una clase devuelta para una cita que no existe.

**Control negativo:** un fichero con `` `002` `` donde `002` **no** colisiona, no está en
el mapa y no aparece en el índice → la puerta debe devolver `C_SIN_CLASE` y `A=0, B=0`.
Si una puerta rota crease que "toda cita es una cita renumerada", el vector falla.

### 4.2 INV-2 — el mapa se LEE, y su ausencia no es un mapa vacío

> *Si el mapa de renumerado no está o una de sus filas no tiene los seis campos
> declarados, la clase B se declara `NOT_DETERMINADO` y su recuento **no** se imprime
> como 0.*

Se puede fallar, y el fallo sería **silencioso**, que es la clase de fallo que este
proyecto trata como grave: una puerta que no tiene el mapa y por tanto no ve la banda B
**no se distingue de una puerta que mira y no encuentra nada**. MEDIDO: el mapa es la
única copia de la tabla (`08-ARQUITECTURA/tools/reenvio_gate.py:10-16`), y un mapa
ausente devuelve `[]` en las tres consumidoras, lo que "parece que no hay
renumeraciones" (`08-ARQUITECTURA/tools/reenvio_gate.py:12-16`). Hay que repetir aquí el patrón que ya está
escrito en `leer_registro_codigo` (`tools/check_num_unico.py:596-617`) y que el caso 6e
ya prueba (`tools/check_num_unico.py:1375-1389`).

**Control negativo:** fixture con el mapa **ausente** → `B` debe aparecer como
`NOT_DETERMINADO`, nunca como `0`. Y fixture con una fila de **5 campos** → también
`NOT_DETERMINADO`, no "las demás 56". Un lector parcial del mapa que se come el
resto es exactamente el fallo que `08-ARQUITECTURA/tools/reenvio_gate.py:25-29` dice que ya ocurrió una vez.

### 4.3 INV-3 — la intersección se cuenta una vez, no dos

> *Ninguna cita aparece en A y en B a la vez. Y la aritmética lo demuestra: el recuento
> de B excluye los `|{viejo} ∩ dups|` números, y se imprime cuántos son.*

Se puede fallar de la manera más fácil del mundo: **escribir `dups` como lista en vez de
conjunto**, o extenderlo con `+=`. MEDIDO el tamaño del agujero: `|{viejo & SI} ∩ dups| = 2`
números (`1011` y `272`). Con conjunto, (a) daría 2485; con lista daría 2485 + las
citas a esos dos números, que son las que el filtro por lista dejaría pasar dos veces.
Una puerta que no distinga un total de su doble está midiendo dos poblaciones con el
mismo nombre, y el nombre es el único aviso que tiene el lector.

**Control negativo:** fixture con `1011-a.md` + `1011-b.md` (colisiona) y una fila del
mapa `viejo=1011`, más una cita `1011:1` → debe dar `A=1, B=0`. Si `B=1`, el filtro se
solapó.

### 4.4 Lo que NO se escribe: un exit 8, y por qué no

Habría un código natural para B: *"hay citas a números renumerados que nadie ha
adjudicado"*, simétrico al 7. **No se escribe, y el motivo es que no se puede probar.**

Un código de salida necesita dos cosas que hoy no existen: un nombre en el diccionario
de `tools/check_num_unico.py:945-969` —sin el cual la puerta **revienta con `KeyError`
después de haber impreso el veredicto**, que es el fallo que la propia cabecera documenta
en `tools/check_num_unico.py:950-965`— y un vector que lo(factory)que lo emita, porque la
lección de esa cabecera es *"un código que la puerta puede emitir y que el self-test no
recorre no está probado"*.

Falta lo segundo por una razón que no es de trabajo: **el censo de B no existe como
número declarable.** Declararlo exigiría adjudicar las 224, y adjudicar es leer prosa
una a una y decidir el destino de una cita, que es exactamente lo que este nodo tiene
prohibido hacer. Un exit 8 con un `CENSO_REN_OLD` inventado sería una puerta que
dispara siempre y no distingue nada: la forma exacta del defecto que `tools/check_num_unico.py:38-45`
describe. **Un caso sin vector es peor que un caso ausente, porque se lee como
probado.** B se imprime, con `fichero:línea`, y no falla.

---

## 5. EL SELF-TEST: QUÉ VECTOR PRUEBA QUÉ CASO

MEDIDO del estado actual: **33 comprobaciones, 0 fallos**, confirmado ejecutando
`--selftest` en este nodo. Y MEDIDO también, y esto es lo importante:

```
lineas del selftest (1009-1431) que mencionan `no_citas`         : NINGUNA
lineas del selftest que mencionan `NO_CITA_FICHEROS`             : NINGUNA
lineas del selftest que mencionan `dups`                         : NINGUNA
```

O sea: **el mecanismo de no-citas completo —3 ficheros declarados, 61 coincidencias, un
filtro reordenado por este patch— no tiene ni un vector.** Mover ese filtro sin añadir
vectores es exactamente el fallo que `tools/check_num_unico.py:1202-1204` describe para
el código 7. Por eso el patch de §7 incluye los vectores, y no como adorno.

| # | vector nuevo | qué prueba | control negativo |
|---|---|---|---|
| V1 | `B` una cita a un `viejo` del mapa, único hoy, aparece en B con `fichero:línea` | que la clase B existe y se puede ver | el mismo árbol **sin** fila en el mapa → `B=0` (§4.2) |
| V2 | `Bd` el **mismo** árbol sin el mapa en disco → `B` es `NOT_DETERMINADO`, no `0` | que la ausencia no es un cero | el mismo árbol **con** el mapa → `B` es un entero (§4.2) |
| V3 | `Bx` mapa con una fila de **5 campos** → `NOT_DETERMINADO`, no "56 de 57" | que un mapa malformado no es un mapa parcial | fila de 6 campos → `leido` |
| V4 | `Bi` `1011-a.md`+`1011-b.md` y fila `viejo=1011`, una cita → `A=1, B=0` | que la intersección no se cuenta dos veces | sin la fila del mapa → `A=1, B=0` también, y con la fila `A=1, B=0`: **los dos lados del caso** |
| V5 | `Bc` la partición cierra: `A+B+C` = nº de coincidencias del fixture | que C existe y que nadie se pierde | un número que no está ni en dups ni en el mapa → `C=1`, `A=B=0` (§4.1) |
| V6 | `Bn` no-citas en un fichero declarado, con número **fuera** de `dups` → se descartan y `no_citas_descartadas` las cuenta | que el filtro reordenado llega donde antes no llegaba (§1.2) | el mismo fichero **no** declarado → se cuentan como cita |
| V7 | `B7` el exit 7 sigue comparando **sólo** A: un árbol con 3 citas B y censo real → `7` **no** dispara | que (b) no ha movido el 7 | el mismo árbol con `CENSO_POBLACION=0` → `7` dispara, y `censo_sin_adjudicar == A`, no `A+B` |

V7 es el vector que ata el diseño a la decisión: **es el que refuta (a)** dentro del
propio self-test. Con (a), `censo_sin_adjudicar` sería `A+B` y V7 fallaría.

Y un vector de **control de|AUTOCOMPROBACIÓN** que hay que actualizar, no añadir:
`MEDIDORAS` (`tools/check_num_unico.py:1294-1295`) es la lista de funciones cuyo
AST se examina contra `PROHIBIDOS = {74, 75}` (`tools/check_num_unico.py:1288`). Si
`leer_mapa_reenvio` se añade a esa lista, la función no puede contener los literales 74
ni 75 — y mi lectura proposed devuelve `{viejos, estado, n_filas}`, sin literales de
recuento, así que entra limpia. **No lo he comprobado ejecutando el filtro**, porque eso
requiere el patch aplicado; lo declaro como `NOT_VERIFIED`.

### 5.1 Lo que el diseño NO consigue en el self-test

- El self-test **sigue sin comprobar** que `B` sea *correcto*, sólo que exista y se
  clasifique. Que una cita de B esté bien o mal es un juicio de prosa (§6).
- Los 33 vectores existentes **no se tocan**. En particular los del exit 7
  (`tools/check_num_unico.py:1216-1241`) siguen siendo válidos porque A no cambia, y
  V7 es el que lo ancla.
- `08-ARQUITECTURA/CITAS-POR-NUMERO-DECLARACION.md:198-200` dice *"el selftest de la puerta sigue dando
  **30** comprobaciones, 0 fallos"*. Hoy da **33**. Ese documento está viejo en esa cifra
  —MEDIDO, no supuesto— y parchearlo no es de este nodo.

---

## 6. LO QUE NO SE CIERRA CON ESTE ARREGLO, AUNQUE SE APLIQUE

### 6.1 Los 40 `RESUELVE_AL_OCUPANTE_NO_VERIFICADA` no se adjudican

MEDIDO: la tabla §12 de `CITAS-150-ADJUDICACION.md` contiene **39 filas** de esa clase
(la cifra declarada en `:248` y `:332` es 40; la diferencia de una fila queda
registrada en §1.1). Son citas cuyo número **es único hoy** —luego **resuelve**, no
ambigüedad— y cuyo contexto no lleva contenido que confirme ni refute.

Con el diseño (b), esas 39 pasan de "invisibles porque la puerta no mira" a
"enumeradas y clasificadas". Eso es un cambio de **visibilidad**, no de **veredicto**, y
la diferencia es de fondo: decidir si una de esas citas está bien exige leer la prosa y
saber qué debería decir el destino. `CITAS-150` tardó una adjudicación manual de una por
una para cerrar 6; el gate **no puede** hacer eso por construcción, y no por falta de
código.

Con nombre propio: **la clase B no es un adjudicador**. Es un inventario de lo que nadie
ha mirado. Un exit que la hiciera pasar sería mentir (§3.2).

### 6.2 La cota de C3 sigue siendo **[6, 46]**, y no se estrecha

`08-ARQUITECTURA/CITAS-150-ADJUDICACION.md:859` declara el total de C3 en **[6, 46]**
(copiado con su espacio, porque aquí una cita sin el espacio sería la misma falta de
fidelidad que el `52` por `052` de D5). El 6 está
verificado: 6 filas `C3_APUNTA_AL_VIEJO` en la tabla, y son las 4 parejas
`103→210`, `104→211`, `144→231`, `188→240`, todas sobre números **únicos hoy**.

Un arreglo de la puerta **no estrecha esa cota**, y por dos razones que no son de
implementación:

1. **No produce evidencia nueva sobre las 46−6.** Cambia quién ve las 241 citas de la
   clase B; no adjudica ninguna. El techo de la cota lo fija cuántas de las citas no
   adjudicadas **contienen** una C3, y eso es una propiedad de la prosa.
2. **Ni siquiera cierra el extremo inferior con honestidad.** Los 6 verificados están en
   `docs/AGENTS-RECTOR-2026-10-02.md:486` y `:488`, y en `NEGATIVE-RESULTS.md:238`,
   `:240`, `:252`, `:271` — las cuatro parejas `103→210`, `104→211`, `144→231`,
   `188→240`, todas sobre números **únicos hoy**. Con (b) la puerta los **vería**,
   porque sus números están en `{viejo & SI}` y no en `dups` — MEDIDO, y es la misma
   condición que hace que hoy no los vea. Pero **ver una cita C3 y que la puerta la
   liste no la convierte en verificada**: la verificación fue el recuento de anclas
   (`GFX_HWIP` 0 vs 13, `handshake` 0 vs 3), y eso lo hizo un lector, no un `if`. El 6
   sigue siendo 6 porque hay 6 filas `C3_APUNTA_AL_VIEJO` verificadas, no porque la
   puerta las mire.

### 6.3 Lo que el arreglo tampoco arregla, y conviene que quede escrito

- **La ambigüedad de clase 2 no se arregla.** De la muestra de 132 adjudicaciones, el
  54,3 % son citas **correctas pero ambiguas**: la frase no dice a cuál va. Ninguna
  puerta que cuente las arregla; se arreglan reescribiendo la prosa, y eso está
  prohibido aquí (`tools/check_num_unico.py:777-801`).
- **La banda B no se cierra.** Que las 224 estén enumeradas no significa que su
  veredicto exista. Un inventario no es una lista de veredictos.
- **El `290` sigue teniendo dos destinos.** El mapa es una **relación**, no una función
  —MEDIDO: 57 filas, 56 `viejo` distintos, `290 → 291` y `290 → 400`—, y
  `08-ARQUITECTURA/tools/reenvio_freeze.py:557-567` lo admite a propósito. Por eso el diseño usa **sólo el
  conjunto de `viejo`** y jamás un `viejo → nuevo`: un mapa de destinos sería ambiguo en
  `290`, y en `290` es donde vive el hallazgo 1040.
- **No se arregla que `REENVIO-FINDINGS.tsv` no declare cuántas filas tiene.** La puerta
  lo lee, pero leer un fichero no es verificarlo; quien lo verifica es `reenvio_gate.py`
  (8 comprobaciones, `08-ARQUITECTURA/tools/reenvio_gate.py:18-31`). Ver §8.

---

## 7. EL PATCH — PROPUESTO, **NO APLICADO**

Estado del fichero al que se aplica este diff:
`tools/check_num_unico.py`, sha256 `7ef0a10d…f81dc`, 1431 líneas, árbol de trabajo con
el docstring sin commitear. **Aplicar este diff cambia el hash, y con él la procedencia de
todo lo medido arriba**: quien lo aplique tiene que volver a medir, no confiar en §2.2.

**Lo que este diff NO contiene, declarado:**

- **La rama de `informe()`** (`tools/check_num_unico.py:837`) que imprime la clase B con
  su denominación. Sin ella el `--json` ya funciona y el informe de texto sale mudo de B,
  que es medio arreglo. Está pendiente de escribir (§9.3).
- **Los siete vectores V1..V7** de §5. Están especificados con su control negativo, pero
  el self-test necesita un constructor de fixture con mapa y `arbol()`
  (`tools/check_num_unico.py:1041`) no lo tiene. Escribir un vector sin su fixture es
  escribir la mitad (§9.4).
- **`leer_mapa_reenvio` no está dentro del diff de este hunk**, y es lo único que impide
  que el diff sea aplicable tal cual. Se declara aquí para que nadie lo descubra al
  aplicar.

Los números de línea de los encabezados `@@` son **orientativos**: están puestos para que
se lea dónde cae cada bloque, y hay que recalcularlos con `diff -u` al aplicar. El
contenido de las líneas `+`/`-` es lo que se propone.

```diff
--- a/tools/check_num_unico.py
+++ b/tools/check_num_unico.py
@@ -358,6 +358,52 @@ SECCION_COLISION = "## Numeros con colision"

+# ---------------------------------------------------------------------------
+# A3-B.  EL MAPA DE RENUMERADO: SE LEE, NO SE SUPPONE.
+#
+# MEDIDO 2026-10-04 (nodo PUERTA-635-RENUMERADO).  La clase B no se deduce de una
+# cuenta: se lee del mapa congelado, que es la UNICA copia de la tabla de
+# renumeraciones (`08-ARQUITECTURA/tools/reenvio_gate.py:10-16`), y del que las tres consumidoras --`--
+# findings_index.reenvios_estable()`, `refs_repair.py` y el generador del indice--
+# se callan igual ante un mapa corrupto que ante uno vacio.
+#
+# EL MAPA ES UNA RELACION, NO UNA FUNCION.  MEDIDO: 57 filas de 6 campos, 56
+# `viejo` distintos, y `290` con DOS destinos (291 y 400), que es lo que
+# `08-ARQUITECTURA/tools/reenvio_freeze.py:557-567` admite a proposito.  Por eso aqui se usa SOLO el
+# conjunto de `viejo` --que es lo que la pregunta necesita-- y NUNCA un
+# `viejo -> nuevo`, que en `290` es ambiguo y en `290` vive el hallazgo 1040.
+#
+# Y SOLO las filas `reasignado=SI`: MEDIDO que una fila `no` significa que el
+# numero viejo quedo LIBRE, luego la cita no miente y no hay nada que ver.
+#
+# NO se lee con `git`, ni contra HEAD: eso lo hace `reenvios()`, y una fuente que
+# depende de dos entradas --arbol Y HEAD-- no es una funcion pura del arbol.
+MAPA_REENVIO = "08-ARQUITECTURA/tools/REENVIO-FINDINGS.tsv"
+MAPA_CAMPOS = ("viejo", "nuevo", "reasignado", "stem", "relacion", "procedencia")
+MAPA_COL_REASIGNADO = MAPA_CAMPOS.index("reasignado")
+MAPA_REASIGNADO_SI = "SI"
+
+
+def leer_mapa_reenvio(raiz: str):
+    """(conjunto de `viejo` con reasignado=SI, n_filas, n_viejos, estado).
+
+    `estado` es "leido", "inexistente" o "malformado", y SIGUE el precedente de
+    `leer_registro_codigo` (:596-617): una fuente ausente NO es una fuente vacia.
+    MEDIDO por que esto no es purismo: con el mapa ausente, las tres
+    consumidoras devuelven `[]` y eso se lee como "no hay renumeraciones"
+    (`08-ARQUITECTURA/tools/reenvio_gate.py:12-16`).  Tratar aqui la ausencia como un cero repetiria
+    ese fallo en la puerta que audita las citas.
+    """
+    p = os.path.join(raiz, MAPA_REENVIO)
+    if not os.path.isfile(p):
+        return set(), 0, 0, "inexistente"
+    viejos, n_filas = set(), 0
+    with open(p, encoding="utf-8", errors="replace") as fh:
+        for linea in fh:
+            s = linea.rstrip("\n")
+            if not s.strip() or s.startswith("#"):
+                continue
+            campos = s.split("\t")
+            if len(campos) != len(MAPA_CAMPOS):
+                # MEDIDO que ya ocurrio: una fila de 4 campos hacia que el
+                # lector hiciera `continue` y se comiera el mapa entero sin
+                # avisar (`08-ARQUITECTURA/tools/reenvio_gate.py:25-29`).  Un mapa que se come filas
+                # sin decirlo es peor que un mapa ausente, porque ademas parece
+                # completo.
+                return set(), n_filas, len(viejos), "malformado"
+            if campos[MAPA_COL_REASIGNADO] != MAPA_REASIGNADO_SI:
+                continue
+            viejos.add(campos[0])
+            n_filas += 1
+    return viejos, n_filas, len(viejos), "leido"
+
+
 # ---------------------------------------------------------------------------
 # 2. EL INDICE. Se lee lo que DECLARA y lo que TABULA, por separado.
 # ---------------------------------------------------------------------------

@@ -618,14 +664,32 @@ def leer_indice(ruta: str):
-def citas_por_numero(raiz: str, por_num, alcance="propio", limite_ficheros=None):
-    """Recorre el arbol UNA vez y cuenta, por fichero y global, las citas por
-    numero que caen sobre un numero duplicado.
+def citas_por_numero(raiz: str, por_num, alcance="propio", limite_ficheros=None):
+    """Recorre el arbol UNA vez y CLASSIFICA cada cita por numero en una de TRES
+    clases, y las cuenta POR SEPARADO.  No las suma nunca.
+
+    MEDIDO 2026-10-04 (nodo PUERTA-635-RENUMERADO).  ANTES solo habia una clase, la
+    A, y las otras dos no se veian.  La division es:
+
+      A  AMBIGUA     el numero HOY identifica mas de un fichero  -> `dups`
+      B  REN_OLD     el numero HOY identifica UNO y el mapa congelado dice que
+                     ese numero fue renumerado hacia otro sitio
+      C  SIN_CLASE   ni una ni otra; se cuenta y se imprime para que la
+                     particion quede CERRADA y se pueda comprobar
+
+    A y B son disjuntas POR CONSTRUCCION, no por medida: un numero no puede tener
+    a la vez mas de un fichero hoy y ninguno hoy.  Y esa disyuncion es lo que
+    hace que `citas_por_numero_a_duplicado` --el nombre, el exit 6 y el exit 7--
+    puedan seguir diciendo exactamente lo que dicen.
+
+    Lo que NO se hace, y es decision: B no dispara ningun codigo de salida.
+    MEDIDO que la clase B no puede distinguir una cita correcta de una
+    equivocada --39 adjudicaciones manuales quedaron en
+    `RESUELVE_AL_OCUPANTE_NO_VERIFICADA`--, y un codigo que saltase sobre B
+    afirmaria algo que el instrumento no sabe.  B se imprime con fichero:linea.
 
     Devuelve (resumen, por_numero, n_ficheros_leidos, n_ficheros_omitidos).
     `omitidos` se cuenta y se imprime: si un fichero no se pudo leer, la cifra
     de citas es una cota inferior y la puerta lo dice.
     """
     dups = {n for n, v in por_num.items() if len(v) > 1}
+    ren_viejos, n_filas_mapa, n_viejos_mapa, estado_mapa = leer_mapa_reenvio(raiz)
     excl = alcance_dirs(raiz, alcance)
     por_numero = collections.Counter()
     no_citas = []
     por_dir = collections.Counter()
-    total = 0
+    total = 0                      # clase A, y SOLO clase A
+    totales = {"A_AMBIGUA": 0, "B_REN_OLD": 0, "C_SIN_CLASE": 0}
     leidos = omitidos = 0
     registro, motivos_reg, estado_reg = leer_registro_codigo(raiz)
     hits = []        # clase A: alimenta el exit 6, y SOLO la clase A
+    hits_b = []      # clase B: se imprime, no alimenta ningun codigo de salida

@@ -658,17 +722,44 @@ def citas_por_numero(raiz: str, por_num, alcance="propio", limite_ficheros=None):
             for rx, grupo in ((RE_CITA_LL, "NNN:LL"), (RE_CITA_BT, "`NNN`"),
                               (RE_CITA_RUTA, "findings/NNN")):
                 for m in rx.finditer(texto):
                     num = m.group(1)
-                    if num not in dups:
-                        continue
                     # Las no-citas.  Se filtran AQUI y no en un segundo
-                    # recorrido: un recorrido doble contaria dos veces lo mismo
-                    # y las cifras dejarian de cuadrar.
+                    # recorrido: un recorrido doble contaria dos veces lo mismo
+                    # y las cifras dejarian de cuadrar.
+                    #
+                    # MEDIDO 2026-10-04: el filtro va ANTES de clasificar, y antes
+                    # iba DESPUES.  Con el orden viejo, 36 de las 61 no-citas de
+                    # los 3 ficheros declarados NO LLEGABAN aqui: las sacaba el
+                    # filtro de clase, que estaba antes.  Y 11 de esas 36 son a
+                    # numeros que SI estan en el mapa (`110` x5, `111` x5,
+                    # `1000` x1 en
+                    # `05-FUENTES-EXTERNAS/.../R0-7-REFERENCIA-X86-64-*.md`:
+                    # filas de la tabla SIB y un `udelay(1000)`), o sea que el
+                    # orden de estas dos lineas decide si el contador nuevo nace
+                    # con ruido.  No es una preferencia de estilo.
                     if rel in NO_CITA_FICHEROS:
                         no_citas.append((rel, grupo, num))
                         continue
-                    total += 1
-                    por_numero[(grupo, num)] += 1
+                    # ---- LA CLASE.  Y aqui estaba el defecto: esto era
+                    # `if num not in dups: continue`, y el `continue` se llevaba
+                    # por delante la clase B entera.  MEDIDO en el instante de
+                    # este diseno: 241 citas de la clase B, de las cuales 36 en
+                    # CODIGO y 26 de esas sin registrar -- y el exit 6, que hoy ve
+                    # 0, no las puede ver.
+                    if num in dups:
+                        clase = "A_AMBIGUA"
+                    elif num in ren_viejos:
+                        clase = "B_REN_OLD"
+                    else:
+                        clase = "C_SIN_CLASE"
+                    totales[clase] += 1
+                    if clase == "C_SIN_CLASE":
+                        # Se cuenta para que la particion CIERRE, y no se
+                        # desglosa: no es un defecto, es el fondo del arbol.
+                        continue
+                    total += 1                  # == totales["A_AMBIGUA"]
+                    por_numero[(clase, grupo, num)] += 1
                     por_dir[rel_dir] += 1
-                    if codigo:
+                    if codigo and clase == "A_AMBIGUA":
                         linea = texto.count("\n", 0, m.start()) + 1
                         hits.append({"fichero": rel, "linea": linea,
                                      "num": num, "forma": grupo,
                                      "ficheros_del_num": len(por_num[num]),
                                      "registrado": reg})
+                    elif codigo and clase == "B_REN_OLD":
+                        hits_b.append({"fichero": rel,
+                                       "linea": texto.count("\n", 0, m.start()) + 1,
+                                       "num": num, "forma": grupo,
+                                       "hoy_unicos": len(por_num.get(num, ())) == 1,
+                                       "registrado": reg})
@@ -677,14 +768,33 @@ def citas_por_numero(raiz: str, por_num, alcance="propio", limite_ficheros=None):
     resumen = {
         "citas_por_numero_a_duplicado": total,
-        "numeros_duplicados_citados": len({n for (_g, n) in por_numero}),
+        "numeros_duplicados_citados": len({n for (_c, _g, n) in por_numero
+                                           if _c == "A_AMBIGUA"}),
         "distintos_numeros_duplicados": len(dups),
         "por_forma": dict(collections.Counter(
-            {g: sum(c for (gg, _n), c in por_numero.items() if gg == g)
-             for g in ("NNN:LL", "`NNN`", "findings/NNN")})),
+            {g: sum(c for (_c, gg, _n), c in por_numero.items()
+                    if gg == g and _c == "A_AMBIGUA")
+             for g in ("NNN:LL", "`NNN`", "findings/NNN")})),
         "por_directorio": dict(por_dir.most_common(12)),
         "ficheros_leidos": leidos,
         # Las no-citas se INFORMAN, no se callan: son la cifra que baja, y sin
         # esta linea el total bajaria sin que se supiera por que.
         "no_citas_descartadas": len(no_citas),
         "no_citas_ficheros": sorted({x[0] for x in no_citas}),
         "ficheros_omitidos": omitidos,
+        # ---- A3-B: la clase que la puerta no podia ver, con su denominacion.
+        #
+        # MEDIDO 2026-10-04T09:34:09: A=2244 B=241 C=5209 no_citas=61 (arbol de 2537
+        # ficheros leidos).  Y `A` NO CAMBIA con este parche: es la misma cifra
+        # que imprimia antes, porque la clase A es exactamente el filtro
+        # anterior.  Eso es lo que deja en pie el exit 7.
+        "A3B_clases": {
+            "A_AMBIGUA": totales["A_AMBIGUA"],
+            "B_REN_OLD": (totales["B_REN_OLD"] if estado_mapa == "leido"
+                          else None),
+            "C_SIN_CLASE": totales["C_SIN_CLASE"],
+            "suma": sum(totales.values()),
+            "B_denominacion": "citas por numero que HOY resuelve a un solo "
+                              "fichero y cuyo numero fue RENUMERADO segun el "
+                              "mapa congelado",
+            "B_no_es_veredicto": "estar en B no afirma que la cita este mal: "
+                                 "afirma que NADIE la ha adjudicado",
+            "mapa": MAPA_REENVIO,
+            "mapa_estado": estado_mapa,
+            "mapa_filas_si": n_filas_mapa,
+            "mapa_viejos_si": n_viejos_mapa,
+            "mapa_viejos_tambien_duplicados": sorted(ren_viejos & dups),
+            "numeros_renumerados_no_duplicados": len(ren_viejos - dups),
+            "A3B_hits": hits_b,
+            "A3B_codigo": {
+                "citas_en_codigo": sum(1 for h in hits_b if not h["registrado"]),
+                "citas_en_codigo_registradas": sum(1 for h in hits_b if h["registrado"]),
+                "citas_en_prosa": sum(1 for h in hits_b if not es_codigo(h["fichero"])),
+            },
+        },
         # ---- A4: el mismo hallazgo, partido por donde duele y por donde no.
         "A4_codigo": {
             "citas_en_codigo": sum(1 for h in hits if not h["registrado"]),
@@ -763,7 +881,8 @@ def medir(raiz: str, alcance="propio", limite_ficheros=None) -> dict:
     r["A3_citas"] = resumen
-    r["A3_detalle"] = [{"forma": g, "numero": n, "veces": c}
-                       for (g, n), c in sorted(por_numero.items())]
+    r["A3_detalle"] = [{"clase": c, "forma": g, "numero": n, "veces": v}
+                       for (c, g, n), v in sorted(por_numero.items())]
```

### 7.1 Lo que el diff **no** toca, y por qué eso es la decisión

| no se toca | por qué |
|---|---|
| `EXIT_CITAS_SIN_ADJUDICAR` y `CENSO_POBLACION` (`gate:294`, `gate:300`) | la clase A no cambia de contenido; V7 lo prueba |
| el exit 6 (`gate:774-776`) | si `hits` se rellena **sólo** con A, su valor no cambia; `hits_b` es aparte |
| el exit 3 y `dups` (`gate:720`, `gate:760`, `gate:772`) | `dups` sigue siendo local y sigue siendo sólo `dups` |
| el nombre `citas_por_numero_a_duplicado` (`gate:680`) | **su semántica no cambia**, que es el punto de (b) |
| el orden de precedencia (`gate:769-833`) | no hay código nuevo |
| `citas_prosa_adjudicado.py`, `REENVIO-FINDINGS.tsv`, el índice | este nodo no reescribe prosa ni repara filas |

---

## 8. DISCREPANCIAS MEDIDAS QUE REGISTRO Y **NO** RESUELVO

Se reportan en vez de promediarse. Ninguna se arregla aquí.

| # | discrepancia | estado |
|---|---|---|
| D1 | `tools/check_num_unico.py:635` no es el filtro en HEAD (**641**) ni en el árbol (**662**); citado así en `08-ARQUITECTURA/CITAS-150-ADJUDICACION.md:410` y en el hallazgo 1048 | `CONTRADICTION` · comprobable con `git show HEAD:tools/check_num_unico.py` |
| D2 | `CITAS-150` §2.3 declara *55 filas / 56 `viejo` distintos*; medido **56 filas / 55 distintos**, y no puede ser al revés | `REFUTED` la declaración, a favor de la medida |
| D3 | `CITAS-150` declara 225; su tabla §12 tiene **224** filas; y de las 241 vivas, **223** son de ficheros anteriores al informe | `NOT_RECONCILED`: 225 / 224 / 223, ±1 en cada dirección |
| D4 | `RESUELVE_AL_OCUPANTE_NO_VERIFICADA`: 40 declaradas (`:248`, `:332`), **39 filas** en la tabla | `NOT_RECONCILED`, ±1 |
| D5 | 21 filas de §12 escriben el número sin cero a la izquierda (`52` por `052`), y `52` no es un número de hallazgo válido (`gate:307`) | `OBSERVED` · el conjunto de 35 se reconcilia con mis 31 al corregir los ceros |
| D6 | `08-ARQUITECTURA/tools/reenvio_gate.py:61` y `:80` dicen *"el mapa tiene 56 filas"*; MEDIDO **57 filas**, y el verificador G2 cuenta 57 y pasa | `CONTRADICTION` · 1 fila, que es `290 → 400` |
| D7 | `tools/check_num_unico.py:343-347` declara *"22 ocurrencias"* y 4 patrones; MEDIDO **58** coincidencias de 13 números distintos en ese fichero, 22 de las cuales llegan al filtro | `OBSERVED` · la declaración cubre las 22 que llegaban, no las 36 que no |
| D8 | `08-ARQUITECTURA/CITAS-POR-NUMERO-DECLARACION.md:200` dice *"30 comprobaciones"*; el self-test da **33** hoy | `OBSERVED` · documento viejo |
| D9 | `C_SIN_CLASE = 5209` es el 67 % de las coincidencias y no es un defecto: es el fondo del árbol | declarado como cifra de partición, no de defecto |

---

## 9. LO QUE NO PUEDO MEDIR SIN APLICAR EL PATCH

Con criterio, y sin inventar:

1. **El recuento del self-test despues del parche.** He DISENADO 7 vectores nuevos
   (V1..V7) sobre 33 → **40**, pero eso es aritmética de intention, no una medición: no
   los he escrito ni los he ejecutado. Lo que NO puedo afirmar es que los 33 sigan
   pasando, aunque creo que sí: ninguno toca `dups`, y a A no la cambia el parche.
   `NOT_VERIFIED`.
2. **El `PASS/FAIL` del control de autocomsación** de `gate:1288-1305`
   (`PROHIBIDOS = {74, 75}` sobre el AST de `MEDIDORAS`). Si `leer_mapa_reenvio` entra
   en `MEDIDORAS` —y creo que debe entrar— hay que ejecutarlo para saber que la función
   no contiene esos literales. `NOT_VERIFIED`.
3. **El texto exacto del informe.** `informe()` (`gate:837`) necesita una rama nueva y no
   la he escrito: es una impresión, y su forma exacta se decide al aplicar.
4. **La lista de V1..V7 necesita saber cómo se fabrica un fixture con mapa**, y
   `arbol()` (`gate:1041`) no tiene hoy parámetro para el mapa: hay que añadirlo, o
   escribir un segundo constructor. Es parte del patch y **no está escrito**.
5. **El tiempo.** Medí que el arnés de tres clases no va más lento que la puerta (≈1,8 s),
   pero es una arnés distinto del código parcheado. `OBSERVADO`, no `MEDIDO` sobre el
   código final.

---

## 10. LO QUE SE DECIDE, EN UNA FRASE

**La puerta pasa a clasificar cada cita por número en tres clases y a contarlas por
separado, sin sumarlas nunca; la clase que hoy no ve —las 241 citas a números
renumerados que hoy son únicos, 26 de ellas en código sin registrar— se imprime con
`fichero:línea` y **no falla**, porque nadie puede todavía distinguir si están bien; el
exit 7 sigue restando lo mismo porque la clase que nombra su nombre no ha cambiado de
contenido; y el filtro de no-citas se mueve antes de clasificar porque hay 11 falsos
positivos que dependen de ese orden. El exit 8 que la simetría pediría, no se escribe,
porque un caso sin vector es peor que un caso ausente. Y el arreglo **no estrecha la
cota de C3**: la cota sigue siendo [6, 46], y las 39 adjudicaciones
`RESUELVE_AL_OCUPANTE_NO_VERIFICADA` siguen sin veredicto, porque una puerta que cuenta
no lee prosa.**

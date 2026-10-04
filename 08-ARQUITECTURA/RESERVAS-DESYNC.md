# RESERVAS-DESYNC · el registro de reservas y el arbol de hallazgos discrepan

> MEDIDO 2026-10-04. Este fichero es la **fuente de la clasificacion**: las clases
> de aqui son las que escribe `tools/reservas_gate.py`, y `RESERVAS.ledger` es su
> fotografia congelada. Si las tres cosas se separan, la puerta pasa de verde
> mientras miente, que es lo mismo que no tenerla.

## 1 · EL INTERCAMBIO, Y POR QUE ESTA VIOLADO

`tools/nextnum.py --reservar` dice, al conceder:

> *queda reservado. Si el hallazgo no se escribe, el número se desperdicia, y eso
> es lo que se acepta para no dar el mismo número a dos autores.*

Se desperdicia un numero **antes** que duplicarlo. Ese es el contrato. El
incumplimiento no es que se desperdicien numeros: es que se **duplican**, que es
justo lo que el contrato compraba.

MEDIDO hoy, sobre `06-INGENIERIA-INVERSA/findings/`:

```
544 ficheros .md
443 numeros distintos
 74 numeros con mas de un fichero     <- 101 ficheros, 175 implicados
 57 reservas vivas
  4 reservas SIN fichero detras
390 numeros en disco SIN reserva
 72 de esos 390 son ademas DUPLICADOS
```

## 2 · HAY DOS REGISTROS, Y CADA UNO VE AL OTRO SOLO A MEDIAS

| registro | quien escribe | formato | con fecha |
|---|---|---|---|
| `.nextnum.lock` | `tools/nextnum.py --reservar` | un numero por linea | **NO** |
| `findings/_reservas/NNNN-reservado.res` | `findnum.py reserve()` | 3 lineas: numero, pid, titulo, fecha | SI |

MEDIDO: los dos registros se leen el uno al otro
(`nextnum.reservados()` -> `_reservas_del_registro_ajeno()`, y
`findnum.reservations()` -> `_reservas_del_registro_ajeno()`), y **5 numeros
estan en los dos**: `259, 507, 971, 1010, 1020`. Eso no es un conflicto: los dos
registros coinciden. Se registra aparte para que no se confunda con uno.

**Y `.nextnum.lock` no se puede fechar.** MEDIDO, por tres vias distintas:

1. `git ls-files --error-unmatch .nextnum.lock` -> `no concordó con ningún archivo
   conocido por git`. No esta versionado.
2. `.gitignore:151` lo excluye a proposito: *"RESERVA DE NUMEROS DE HALLAZGO.
   Cambia en cada hallazgo nuevo: es estado, no dato, y se reconstruye con
   tools/nextnum.py sobre el disco."*
3. Su formato es un numero pelado por linea. No hay donde poner una fecha.

Consecuencia, y es el punto de este nodo: **para 52 de las 57 reservas no existe
la informacion que hace falta para saber si el hallazgo se escribio ANTES o
DESPUES de la reserva.** No es que no se haya buscado. Es que el dato no se
guardo. Ver §5.

## 3 · LAS TRES CLASES, Y CUAL HAY QUE RESOLVER

La pregunta del enunciado es que clase es cada discrepancia. Medido:

| clase | que es | cuantos |
|---|---|---|
| **A · reserva huerfana** | reserva, nadie escribio el hallazgo | 4 (`298 507 971 975`) |
| **B · hallazgo sin reserva** | hallazgo escrito, el protocolo se salto | 390 numeros (72 de ellos duplicados) |
| **C · los dos a la vez** | reserva Y hallazgo | 54 — de las cuales **2 son conflicto** |

La tercera fila necesita el desglose, y por eso lo lleva: de las 54 reservas
con hallazgo detras, **49 son el protocolo funcionando** (se reservo y luego se
escribio), 3 las consumio un renumerado, y **2 son el numero en uso dos veces**
(`288`, `999`). Tomar las 54 por las 2 es el error que haria que un residuo se
archive como un conflicto.

La propuesta ingenua —"una reserva con hallazgo detras es residuo"— **es
FALSA**, y medido por que: `findnum.py commit()` **borra** el `.res` cuando el
commit va bien (`os.remove(res)`, linea 353). O sea que un `.res` junto a un
`.md` **no es el caso normal**: es un commit incompleto. Y en el registro de
`nextnum.py` la reserva es permanente por diseno (no hay `--release`), asi que
ahi la coexistencia es lo esperable.

Por eso la regla de este nodo es **temporal**, no de presencia: la pregunta no
es "hay hallazgo detras", es "**el hallazgo se escribio antes de que la reserva
existiera**". Eso separa el protocolo seguido del numero en uso dos veces.

## 4 · LA REGLA QUE SE APLICA

Para cada numero `n` de `reservas ∪ indices`, **exactamente una** clase:

| clase | condicion | cuantos |
|---|---|---|
| `R1_ESCRITO` | reserva + 1 hallazgo, orden compatible con el protocolo | 49 |
| `R1_CONFLICTO` | reserva + 1 hallazgo, y el hallazgo es ANTERIOR a la reserva | **0** |
| `R2_POR_RENUMERADO` | reserva + 1 hallazgo, y `n` es `nuevo` del mapa congelado | 3 (`976 994 1020`) |
| `R3_SIN_FICHERO_RENUMERADO` | reserva sin hallazgo, y `n` es `viejo` del mapa | 1 (`975`) |
| `R4_SIN_ORIGEN` | reserva sin hallazgo, y no esta en el mapa | 3 (`298 507 971`) |
| `R5_EN_USO_DOS_VECES` | reserva + **2 o mas** hallazgos | **2** (`288 999`) |
| `H1_SIN_RESERVA` | 1 hallazgo, sin reserva | 318 |
| `H2_DUPLICADO_SIN_RESERVA` | 2+ hallazgos, sin reserva | 72 |

Suman 448 filas = 444 numeros en disco + 4 reservas sin fichero.

`R1_ESCRITO` se subdivide por el orden, que es lo unico que separa el caso
bueno del malo:

* `orden=PROTOCOLO_CUMPLIDO` — hay fecha de reserva y es anterior al fichero.
* `orden=INDETERMINADO` — **no hay fecha de reserva**. No se elige: se dice.

Y las dos categorias que **no** son numero de hallazgo van aparte, porque
confundirlas con una discrepancia de numero seria el defecto de nuevo:

* `P2_RESERVA_SIN_CONTENIDO` — el `.res` existe y weighs 0 bytes (`1020`).
* `X1_EN_LOS_DOS_REGISTROS` — los dos registros tienen el numero (5).

## 5 · `1020` Y `298`, RESUELTOS CON LAS TRES FUENTES

### `298` — el enunciado dice una cosa, el disco dice otra

El enunciado afirma que 298 tiene "un hallazgo escrito con ese numero **y** una
reserva". **Medido: el hallazgo no existe.**

```
0 ficheros cuyo nombre empiece por 298 en TODO el arbol (incluido .git)
git log --full-history -- '*298-*'            -> vacio
REENVIO-FINDINGS.tsv: filas con viejo=298 -> NINGUNA
                                 con nuevo=298 -> NINGUNA
.nextnum.lock                                 -> SI esta
```

O sea: **298 no es un caso de "los dos a la vez"**. No hay conflicto de numero.
Lo que hay es una reserva sin fichero cuyo hallazgo **existio y se perdio**, y
eso lo prueban las citas que sobrevivieron:

* `299-la-ruta-en-proceso-mide-igual-y-el-ahorro-era-de-arranque.md:267`
  -> `findings/298   las 303 y la tabla de niveles, ya escritas`
* `300-self-no-era-el-self-test-de-toolkit.md:1`
  -> `y por eso las 303 de `298` eran 472`
* `300-...md:88` -> `**298 no se corrige.** Los hallazgos escritos no se reescriben`

**DECISION: `R4_SIN_ORIGEN`, y no se libera.** Tres razones, y la tercera es la
que importa: (a) ya esta decidido por el proyecto; (b) `nextnum.py --auditar`
ya lo trata como "SIN ORIGEN DEMOSTRABLE"; (c) el numero 298 **esta citado por
hallazgos vivos** — liberarlo devolveria al allocator un numero que el registro
de citas dice que ya no esta libre.

**LO INDETERMINADO, DICHO COMO TAL:** *cuando* se perdio el fichero, y *por
que*. MEDIDO que no se puede reconstruir:

```
git fsck -> 5 objetos corruptos (0 bytes):
  01361a2b7a9c669ab7f1cb53f97b15b64c5640c6
  499bffcbd6f36c3141f5c2497957e43f4e2c50d6
  4aebdccf2401289d61936c9b9b6afc79284af064
  729ab738dea2c67c28e065abbab87ec373d47141   <- ADEMAS: HEAD/main
  f5a80d162be89c1046b4f09d70eb4af8a182cdfb
HEAD: entrada de log de referencias invalida 729ab738...
```

Es decir: el objeto `729ab...` es a la vez uno de los cinco corruptos **y** el
que autoriza `refs/heads/main`. El historial de este repositorio no puede
decir que paso con 298, y no se va a inventar una respuesta.

### `1020` — la reserva la consumio un renumerado

Las tres fuentes, medidas:

1. **El fichero.** `1020-la-apertura-del-gart-no-puede-cambiar-en-runtime.md`,
   12.700 bytes, mtime `2026-10-03 20:42:56`. **Un solo fichero**: 1020 no esta
   duplicado.
2. **La reserva.** `1020-reservado.res`, **0 bytes**, mtime
   `2026-10-03 16:07:20`. Y 1020 esta ademas en `.nextnum.lock`.
3. **El historial.** `a750603`, `2026-10-03 16:14:54`:
   *"1020: renumerado desde 1011 por colision"*. El mapa congelado lo confirma
   en `REENVIO-FINDINGS.tsv` linea 167:
   `1011  1020  SI  la-apertura-del-gart-no-puede-cambiar-en-runtime.md  contenido  git:a75060397058f`

Y el dato que cierra la clase: **`findnum.py reserve()` (lineas 310-314) escribe
siempre 3 lineas** con write+rename. Un `.res` de 0 bytes **no puede** haber
salido de `reserve()`. Y `git show HEAD:...1020-reservado.res` sale **vacio**:
estaba ya vacio cuando se commiteo, nunca tuvo contenido.

**DECISION: `R2_POR_RENUMERADO`, y no es conflicto.** La secuencia medida es:
`1011` colisiono -> se reservo `1020` a las `16:07:20` -> el fichero se movio de
`1011` a `1020` en `a750603` a las `16:14:54` -> el `.res` quedo porque
`commit()` nunca corrio (el renumerado no pasa por `findnum.commit`). Reserva
anterior al fichero: **el protocolo se cumplio**.

**LO QUE SI ES UN DEFECTO, y es distinto del de 298:** el `.res` de 1020 es un
`P2_RESERVA_SIN_CONTENIDO`. La ocupacion sobrevive (los dos allocators leen el
*nombre*), pero la procedencia —pid, titulo, fecha— no. Es un registro que
afirma sin poderarnationar nada.

## 6 · LA PUERTA

`tools/reservas_gate.py`. Lo que garantiza **no** es "no hay discrepancias" —
esa invariante es falsa y no se va a hacer pasar por verdadera. Lo que garantiza
es:

> **toda discrepancia esta clasificada.**

Y por que eso es lo que importa: un residuo sin clasificar y un conflicto sin
clasificar se ven IGUALES. Lo unico que los separa es que uno tenga una clase
que dice "esto es un resto" y el otro una que dice "el numero esta en uso dos
veces". Sin la clase, el segundo se archiva como el primero y el numero se
queda ocupado para siempre sin que nadie lo decida.

`rc=0` si y solo si:

1. toda discrepancia tiene clase, y
2. ninguna clase ha cambiado respecto a `RESERVAS.ledger`, y
3. toda discrepancia esta en el ledger, y
4. no hay `P2_RESERVA_SIN_CONTENIDO` nuevo, y
5. el conjunto de `R5_EN_USO_DOS_VECES` **no ha crecido**.

`rc=1` en cuanto una de esas cinco deja de cumplirse. Los cinco vectores estan
probados por mutacion: se inyecta cada fallo en una copia y se comprueba que la
puerta devuelve 1. Una puerta que no puede fallar no es una puerta.

### La columna que faltaba

El enunciado dice: *"si el registro necesita una columna nueva, anadela a todas
las filas"*. Hace falta, pero **no en `.nextnum.lock`**.

MEDIDO el peligro exacto: `nextnum.reservados()` (linea 180) y
`findnum._reservas_del_registro_ajeno()` (linea 114) **los dos** seleccionan con
`re.match(r"^\d{3,}$", l)`. Anadir una columna ahi no anade una columna:
**hace que las 57 reservas dejen de existir para los dos allocators**, que es
justo el defecto que este nodo existe para tapar.

Asi que `.nextnum.lock` **no se toca** — sigue siendo el conjunto pelado que los
dos leen — y la columna nueva vive en `RESERVAS.ledger`, al lado de las
reservas que describe. Las 57 filas estan, con la fecha que se pudiera
recuperar y `DESCONOCIDA` donde no, en vez de una fecha inventada.

Y de paso se arregla la causa: `nextnum.py --reservar` ahora **sella** la
reserva en el ledger, con fecha y pid, en la misma seccion critica del `flock`.
Una reserva nueva nace fechada; las 52 indeterminadas son una deuda cerrada, no
una deuda que crece.

### Por que el ledger se llama `.ledger` y no `.tsv`

MEDIDO, `tools/check_num_unico.py:248`:

```python
EXT_LEIBLES = (".md", ".py", ".sh", ".c", ".h", ".txt", ".tsv")
```

`.tsv` se lee. Un ledger con una columna de numeros, en `.tsv`, dentro del arbol
"propio", **sumaria ~57 citas por numero** a las 2160 que ya mide, y moveria un
contador que no mide lo que dice medir. Por eso la extension es `.ledger`: el
mismo dato, invisible para el instrumento que cuenta citas, que es exactamente lo
que un registro de ocupacion debe ser. Comprobado en §7.

## 7 · EFECTO MEDIDO, ANTES Y DESPUES

Las tres instrumentos, medidas. Y con la atribucion hecha, porque durante este
trabajo **una sesion concurrente escribio a la vez** y sin separar los dos
efectos cualquier comparacion es mentira:

* la sesion concurrente anadio `1042-probe-lee-mmio-...` (05:11:29) y una
  reserva mas. 544 -> 545 ficheros, 443 -> 444 numeros, 57 -> 58 reservas.

### `check_num_unico.py`

| cifra | antes | despues | de quien es el cambio |
|---|---|---|---|
| ficheros en `findings/` | 544 | 545 | **sesion concurrente** (1042) |
| numeros distintos | 443 | 444 | **sesion concurrente** |
| numeros duplicados | 74 | 74 | nadie |
| citas por numero a duplicado | 2160 | 2162 | **este nodo** |
| codigos que se disparan | `[5, 6, 4]` | `[5, 6, 4]` | nadie |
| codigo devuelto | 5 | 5 | nadie |

Las +2 citas son **mias**, y estan medidas una a una:

```
RESERVAS-DESYNC.md   -> 2 citas  [('`NNN`','1011'), ('`NNN`','1011')]
reservas_gate.py     -> 0 citas
1042-...md           -> 0 citas
nextnum.py           -> 0 citas
RESERVAS.ledger      -> 0 citas   (extension .ledger, fuera de EXT_LEIBLES)
```

Las dos son prosa de este documento y caen sobre `1011`, que esta duplicado. No
entran en la lista de `CODIGO SIN REGISTRAR` —comprobado— porque no son codigo:
van al cubo que el propio instrumento etiqueta *"en prosa ... <- una molestia"*.
Se declara en vez de esconderse: una comparacion "no ha cambiado" que en real ha
cambiado dos lineas es exactamente el tipo de dato que no se puede citar.

**Y el ledger aporta 0, que es lo que se pretendaba.** Medido por las dos vias:
`EXT_LEIBLES` no incluye `.ledger`, y el recuento sobre un arbol sintetico con
los tres ficheros nuevos da *"ficheros leidos: 2 de 3"* —el `.ledger` no se lee.
Con `.tsv` habrian entrado 448 filas y ~448 citas falsas.

### `nextnum.py --auditar`

Idéntico en su estructura y en su veredicto:

```
antes   57 vivas | 4 sin fichero | 975 RENUMERADO | 298 507 971 SIN ORIGEN | rc=1
despues 58 vivas | 4 sin fichero | 975 RENUMERADO | 298 507 971 SIN ORIGEN | rc=1
```

La diferencia de 57 a 58 es la reserva de la sesion concurrente. **No se toca
`.nextnum.lock`**: el cambio es una fila mas, y la comprobacion de que el
formato sigue siendo el que los dos lectores esperan se hace en §6.

### `nextnum.py --selftest`

`RESULT: PASS (19 vectores)`, igual que antes de tocarlo. El sellado seIso y se
probado por separado, sin tocar el registro real:

```
reservar(888) -> RESERVADO
reservar(888) otra vez -> OCUPADO
_sella es idempotente (2 vias -> 1 fila)
ledger sin #SCHEMA -> no se anade fila
registro real .nextnum.lock: 58 lineas, 888 presente: False
```

Ese ultimo `False` es la comprobacion que importa: la prueba se hizo con
`N.BLOQUEO` y `N.LEDGER` apuntando a un temporal, **no** reservando un numero
de hallazgo real.

### `reservas_gate.py`

No existia antes. Ahora, sobre el arbol real:

```
  [OK] C1 toda discrepancia tiene clase       448 numeros clasificados
  [OK] C2 toda discrepancia esta en el ledger 0 nuevas; el ledger tiene 448 filas
  [OK] C3 ninguna clase ha cambiado           0 cambios de clase
  [OK] C4 ningun .res vacio nuevo             los vacios son los de siempre: ['1020']
  [OK] C5 R5 no ha creado                      R5 sigue en ['288', '999']
  VEREDICTO: toda discrepancia esta clasificada        rc=0
```

Y que pueda fallar esta probado, no supuesto: los seis vectores de mutacion
inyectan cada condicion en un arbol temporal y comprueban que devuelve 1.

## 8 · LO QUE QUEDA ABIERTO

* **`R1_CONFLICTO = 0 filas`, y es un dato, no una garantia.** De las 54
  reservas con fichero detras solo **2** tienen fecha de reserva (`259`, `1010`),
  y las dos son `PROTOCOLO_CUMPLIDO`. Las otras 52 son `INDETERMINADO`. Que no
  haya ninguna conflicto **no se puede inferir de ahi**: es `NOT_DETERMINED`, y
  por eso el sellado existe. A partir de ahora si es comprobable, y `C3`
  dispara si alguna vez lo es.
* **El numetro exacto sigue siendo 74 duplicados.** Este nodo los clasifica y
  los hace visibles; no los arregla. Renumerar 74 hallazgos rompe las 2162
  citas que los nombran, y las citas son la evidencia. Es decision de otro
  nodo y no se toca aqui.
* **1020 y 1011.** El renumerado de `a750603` movió el hallazgo a 1020 y dejó
  `1011` con dos ficheros. 1011 esta en `H2_DUPLICADO_SIN_RESERVA`. Corregirlo
  es renumerar, no liberar, asi que queda fuera.
* **`R5` esta congelado en `[288, 999]`.** Si crece, `C5` falla. Si se
  decide renumerar alguno, hay que re-congelar el ledger **y** el hallazgo que
  lo motive tiene que decir cual de los dos ficheros gana el numero.
* **Cuando se perdio `298`, y por que.** No se puede determinar: el objeto
  `729ab...` es a la vez uno de los cinco corruptos y el que autoriza
  `refs/heads/main`. Si alguien restaura el objeto, `git log --full-history
  -- '*298-*'` lo dira y esta fila pasa de `NOT_DETERMINED` a lo que sea.
* **`REENVIO-FINDINGS.tsv` cambio bajo los pies de este nodo.** Hash leido al
  empezar: `b3af441bb2fa4fe7` (mtime 04:35:10). Hash al terminar:
  `932ca380045d80af` (mtime 05:23:14). Lo escribio el nodo concurrente; aqui
  solo se abrio en lectura.

  **DRIFT_DETECTED, y medido que NO cambia la clasificacion.** Las 49 filas de
  datos son el mismo conjunto de pares `(viejo, nuevo)`:

  ```
  filas HEAD=49   filas disco=49
  pares (viejo,nuevo) iguales: True
  solo en disco: []      solo en HEAD: []
  ```

  Lo que cambio son 59 lineas de **cabecera**: el nodo concurrente documento que
  el ancho unico es 6 y no 5, y que `relacion` distingue `contenido` de
  `numero`. Ni una fila de datos. Por eso C3 sigue en `[OK]`: la puerta compara
  clases, y las clases no se han movido.

  Se declara en vez de ignorar porque el mapa es una **entrada** de esta puerta,
  y una entrada que cambia sin que nadie lo compruebe es el fallo que 048 y 1036
  ya han documentado en este proyecto. Si el cambio hubiera sido de una fila,
  C3 habria saltado nombrando el numero y la clase que dejo de ser.

### Lo que este nodo dejo escrito en ficheros

| fichero | que es |
|---|---|
| `tools/reservas_gate.py` | la puerta. `--selftest` con 11 vectores, 6 por mutacion |
| `06-INGENIERIA-INVERSA/findings/_reservas/RESERVAS.ledger` | 448 filas clasificadas, con la columna `p2_vacio` |
| `08-ARQUITECTURA/RESERVAS-DESYNC.md` | este fichero: la regla, la evidencia y las decisiones |
| `tools/nextnum.py` | **solo** el sellado: `_sella()` mas 3 lineas dentro del flock |

`TOOLS-STATUS.md` **no** se ha editado a mano: lo genera `tools/artifacts.py` y
su cabecera lo prohibe expresamente. MEDIDO que el gate lo recogera solo:
`artifacts.py` descubre por el patron `^[a-z0-9_]+\.(py|c|sh)$` sobre
`toolreg.TOOL_DIRS` (que incluye `tools`), y `reservas_gate.py` casa, declara
`--selftest` y tiene `if __name__ == "__main__"`. Se declarara
`TOOL_VALIDATED` en la proxima regeneracion. No se ha lanzado `artifacts.py`
porque escribe tambien `FINDINGS-RENUMERACIONES.md`, que es de otro nodo.
# 1070 — seis documentos eran invisibles al censo, y la valla sin cerrar no es un error de parseo sino un documento parcial

```text
AGENCIA=RX550-INVESTIGACION · WORK_CLASS=AGENT-MAIN-VALIDITY
CLASSIFICATION=OBSERVABILITY+DEFECT · TRACK=STATIC+MUTATION
GENERADO=2026-10-04 · MEDIDO=EN ESTA HOST
AFECTADO=tools/sello_prov.py  lee_bloques() · audita()
         + 3 documentos que aparecieron al destaparlos
ORIGEN=1059 §5 (mi censo no tenia denominador) y 1069 §3 (mutacion sobre la valla)
ESTADO=PROBADO · REPARADO · 53 vectores · 3 mutaciones nuevas detectadas
herramienta   tools/sello_prov.py
```

## 0 · El número que resume el arreglo

```text
                        antes ->  ahora
  bloques               41   ->   45
  campos                89   ->   93
  ficheros             34   ->   37
  ERRORES de parseo     6   ->    0
  DIFIERE               13   ->   17
  ROTO                  11   ->   13
```

**Seis documentos no se auditaban. Ahora se auditan, y en ellos salen defectos
que no existían porque nadie los había mirado.**

## 1 · LOS TRES DEFECTOS, Y LOS TRES SON MÍOS

### (a) Una valla de N backticks NO se cierra con una de 3

CommonMark cierra una valla de N backticks con otra de N **o más**. Yo emparejaba
cualquier línea que empezara por tres backticks.

MEDIDO: **`promp.md` tiene 2 vallas de 4 backticks.** Mi emparejador las mezclaba con
las de 3 y declaraba el documento entero ilegible. Un fichero que usa vallas de 4 es
**legal**, y yo lo rechazaba por no saber contarlas.

### (b) Una valla sin cerrar NO es un error de parseo

Aquí está el defecto de fondo, y es el que cuesta caro. Un documento con la última
valla sin cerrar iba a `errores` y **no aportaba ni un bloque al censo**.

MEDIDO: `063-memoria-sesion-smu-estado-persistente.md` tiene **403 vallas**, y la
última se abre en la línea 5180. Las 402 anteriores son perfectamente válidas, con
campos de procedencia legibles, y las estaba tirando todas.

**Un defecto de REDACCIÓN de un documento convertido en un hueco de OBSERVABILIDAD
sobre el documento entero.** Sale más caro que el defecto: el hueco no lo nota nadie,
porque no produce ningún error visible, sólo un número que no cuadra.

### (c) `rc=2` no se apoyaba en los parciales

Corolario del anterior: `rc_de()` miraba `errores` y no `parciales`. Con el cambio,
un documento parcial baja el código igual —because un censo incompleto no es un
veredicto— pero por la razón correcta y con el número a la vista.

## 2 · LO QUE CAMBIA AL VEREDICTO

**Antes:** valla sin cerrar → el documento desaparece del censo.
**Ahora:** valla sin cerrar → el documento entra, se audita lo que se ha cerrado, y
queda marcado `PARCIAL` con la línea y el número de backticks.

```
DOCUMENTOS PARCIALES: valla sin cerrar, se audita lo que hay (N)
  <fichero>   valla de 3 abierta en la linea <n>
```

El `rc` sigue siendo `2` — *censo incompleto* — que es lo que ya significaba y lo que
correctamente impide que alguien lo lea como "está bien".

## 3 · LO QUE SALIÓ DE DESTAPARLO, Y POR QUÉ IMPORTA MÁS QUE EL ARREGLO

Tres documentos que **no existían** para el censo. Dos con `DIFIERE`, uno con `ROTO`:

| documento (antes invisible) | veredicto |
|---|---|
| `1074-set-config-reg-con-un-solo-p…` | `DIFIERE` |
| `1075-dos-votos-en-contra-que-eran…` | `DIFIERE` |
| `1077-unmap-queues-macros-y-layout…` | `ROTO` ×2 |

**Los tres son de la otra sesión** y están en vuelo, así que sus `DIFIERE` son
esperables y **no los adjudico**: son mediciones sobre ficheros que se están
escribiendo, que es la clase de observación que §50 declara no interpretable.

Lo que sí es un resultado, y no depende de quién escribió qué: **antes de este
arreglo, el instrumento no podía verlos.** Un censo que no ve el fichero no puede
decir nada sobre él, y su silencio se parecía a un expediente limpio.

## 4 · LA MEDIDA QUE NO ES MÍA, Y QUE SALIÓ DE PASO

El censo completo, ahora:

```text
COINCIDE 19 · EXISTE 32 · DIFIERE 17 · ROTO 13 · MALFORMADO 7 · SIN_RECETA 3 · AMBIGUO 2
```

Y en él hay **`DIFIERE` sobre el `1057`, que es mío**:

```text
06-.../1057-...md:12   DIFIERE  herramienta  1.0.0 -> 1.1.0
06-.../1057-...md:13   DIFIERE  sha256       7d2bcc1f… (ya no es)
```

**El hallazgo que escribí hace dos iteraciones quedó viejo porque moví la
herramienta que cita.** Es exactamente la clase de decaimiento que documenta el
`1059`, y ocurre en mi propio trabajo y **una iteración después**: no he tenido que
esperar a que otro commitee para que un bloque de procedencia se vuelva falso.

**Y no lo "arreglo" re-sellando.** El `1059` §5 explica por qué: un hash declarado no
se puede recalcular sin perder lo que afirmaba. Lo que corresponde es **corregir el
documento**, y eso es trabajo de quien lo escribió, que en este caso soy yo, en una
iteración que no sea esta.

## 5 · LAS MUTACIONES

```text
M22  una valla de 3 cierra cualquier cosa     -> FALLA V22, V22b
M23  una valla sin cerrar vuelve a ser error  -> FALLA V10, V10b, V10d (+1)
M24  rc=2 no mira los parciales               -> FALLA V10, V10b
```

`M23` es la que importa, porque **reproduce el defecto original entero**: es
exactamente lo que hacía la versión anterior, y ahora lo detecta.

Dos vectores nuevos que ya existen en la suite:

- `V10d` — un documento con **una valla cerrada buena y otra sin cerrar** debe
  contar la buena. Antes contaba cero.
- `V22` / `V22b` — vallas de 4, y que una de 3 **no** cierra una de 4.

**53 vectores, 0 fallos.**

## 6 · Lo que NO arregla

- **No corrige los documentos.** `promp.md` sigue con su valla mal cerrada. Lo que
  cambia es que el censo lo ve y lo dice, en vez de tragárselo.
- **No implementa CommonMark entero.** Sólo el conteo de backticks. Un documento con
  vallas anidadas, tablas o sangria rara puede seguir siendo un caso que este
  parser no resuelve. `LIMITACION`, no `PROVEN_ABSENT`.
- **No adjudica los `DIFIERE` de la otra sesión** (§3), y no puede: son ficheros en
  vuelo.
- **No toca el `1057`**, por lo del §4.
- **No toca la GPU, ni el driver, ni mide rendimiento.**

## 7 · PROCEDENCIA

```text
antes   /tmp/opencode/censo4.json   bloques 41 · campos 89 · ficheros 34 · errores 6
ahora   /tmp/opencode/censo5.json   bloques 45 · campos 93 · ficheros 37 · errores 0
regla   lee_bloques() devuelve (cerrados, parcial) y audita() no descarta el fichero
self-test  53 vectores, 0 fallos
mutaciones M22 M23 M24, las 3 detectadas
escrituras  0 en el arbol.  Nada commiteado de la otra sesion.
```

**Lo que este documento NO prueba.** No prueba que el parser de vallas sea correcto
en general: sólo que cuenta bien los backticks y que no pierde el documento. No
adjudica ningún `DIFIERE`. Y el censo está medido **sobre un árbol que se está
escribiendo mientras mido**, así que las cifras son de un instante, no de un estado.
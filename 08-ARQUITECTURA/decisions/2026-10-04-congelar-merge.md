# DEC-2026-10-04 — `--congelar` pasa a ser un merge: el mapa congelado ya no se puede vaciar con una bandera

**Estado**: `ACCEPTED` · decide, no propone.
**Fecha**: 2026-10-04 · **Nodo**: `CONGELAR-MERGE`
**Ámbito**: `08-ARQUITECTURA/tools/reenvio_freeze.py`,
`08-ARQUITECTURA/tools/REENVIO-FINDINGS.tsv` (cabecera) ·
**Modo**: `READ_WRITE` sobre dos ficheros de datos del proyecto. Ni la GPU, ni
`dmesg`, ni `journalctl`, ni un hallazgo renumerado, ni un `git commit`.
**Puerta que la hace ejecutable**: `reenvio_freeze.py --self-test`

---

## 0. LO QUE SE PIDIO Y LO QUE SE MEDIO

El encargo decía: `--congelar` reescribe el mapa entero desde `reenvios()`, y
`--forzar --confirmar-obsoleto` borraría las 6 filas no derivadas del diff sin
avisar.

**MEDIDO: el riesgo es real y la premisa del mecanismo es incorrecta.**

| Medida | Valor |
|---|---|
| `reenvios()` con el código anterior | **0 pares** |
| Filas del mapa congelado | **49** (43 `diff`, 2 `git:<commit>`, 4 `prosa:`) |
| `--congelar` a secas | `rc=3`, no escribe, fichero intacto |
| `--congelar --forzar` | `rc=3`, no escribe, fichero intacto |
| `--congelar --forzar --confirmar-obsoleto` | `rc=4`, **no escribe**, `.bak` ni se crea |

El atajo **no borraba nada hoy**. Y no borraba nada por el **orden de tres
comprobaciones**, no por diseño:

1. `if not rev: return 4` — `reenvios()` vacío.
2. `verificar(rev)` con `declarado_sha` leído **del disco**: comparaba el mapa
   **nuevo** contra el sha declarado por el fichero **viejo**. MEDIDO que con un
   solo par devuelve `rc=1`.
3. `escribir()` — **no podía escribir nunca**. MEDIDO
   `TypeError: %d format: a real number is required, not str`, con 1 fila y con
   3. Los especificadores 5 y 6 de la plantilla de cabecera estaban
   **transpuestos** respecto a la tupla de argumentos: `sha_de()` devuelve `str`
   donde la plantilla pide `%d`. El `.bak` se escribía *antes* de ese fallo.

Tres guards que se cancelan entre ellos y un escritor muerto detrás. La
garantía declarada —«la negación no se puede sortear por descuido»— era verdad
por accidente, no por construcción. Y MEDIDO que el atajo **sí** alcanzaba la
reescritura en cuanto `reenvios()` devolvía **un** par, que es su uso previsto:
congelar un renumerado sin commitear.

## 1. UNA SEGUNDA DESINCRONIZACIÓN, MÁS GRAVE QUE EL BUG DE LAS BANDERAS

MEDIDO en el código anterior:

- `CAMPOS` tenía **6** campos. El fichero en disco tiene **6**.
  `findings_index.reenvios_estable()` exige **6**. `cuerpo()` escribía **5**.
- `leer()` mapeaba `p[4]` a `procedencia`, cuando `p[4]` es `relacion` y
  `procedencia` es `p[5]`.

MEDIDO el round-trip: con las **mismas 49 filas**, el sha del cuerpo reconstruido
era `8034e1c3…` y el del fichero real `08c27e49…`. MEDIDO el recuento de lo que
`leer()` devolvía: `{contenido: 45, numero: 4}` donde el fichero tiene
`{diff: 43, git: 2, prosa: 4}`. **La columna `procedencia` se perdía entera.**

Esto no era cosmético: un merge que no sepa de dónde viene cada fila **no puede
conservar una fila sin saber cuál es**. El defecto del que se encargaba este
nodo era, en parte, consecuencia de éste.

## 2. DECISIÓN

**`--congelar` es un merge.** Conserva lo congelado y añade lo que falta. No hay
ninguna combinación de banderas que lo haga borrar una fila.

`plan_merge(existentes, nuevos)` clasifica cada par nuevo contra el mapa
existente:

| Campo | ¿Conflicto? | Por qué |
|---|---|---|
| `relacion` | **Sí** | Decide si la fila puede reescribir una cita. Elegir `contenido` sobre `numero` apunta 27 citas al hallazgo equivocado. Es el hallazgo 1040 entero. |
| `stem` | **Sí**, salvo prefijo | Dice qué documento se movió. `reenvios()` lo entrega truncado a 58 chars; un truncado no afirma nada que el completo no afirme. |
| `reasignado` | **No** | Se midió en el instante de congelar y su propia cabecera dice que no es permanente. Tratarlo como conflicto haría que el congelado se negase a sí mismo al cambiar el árbol. Se registra como diferencia. |
| `procedencia` | **No** | Dice **cómo** se sabe el par, no **qué** par es. El valor congelado es el más específico de los dos. |

Un par que ya está con la **misma** `relacion` y el mismo documento **se
conserva**: no se duplica. Un par con **otra** `relacion` u **otro** documento
**pregunta**: nombra las dos filas y sale con `rc=1`. No elige.

**`--forzar` eliminado.** Argparse lo rechaza con `rc=2` nombrando la bandera.
Un flag retirado que se vuelve inocuo deja a quien lo teclea creyendo que ha
ordenado algo.

**`--sustituir` es el camino destructivo, y nombra lo que se pierde.** Exige
`--confirmar-obsoleto` **y** `--perder N`, con `N` = el número de filas que la
propia herramienta calcula. Las imprime una a una si falta `--perder`; si el `N`
no coincide, `rc=6`. **No puede vaciar el fichero**: con `reenvios()` vacío se
niega con `rc=5`. Lo que descarta queda escrito por su número en
`REENVIO-FINDINGS.descartadas.tsv`, y la copia entera en `.bak`.

**Por qué esta rama y no un tope de filas.** MEDIDO que `--sustituir` puede
llevar el mapa de 49 filas a 1 si `reenvios()` devuelve un solo par y quien lo
ejecuta teclea `--perder 48`: las cuatro puertas se abren porque las cuatro son
ciertas. `--perder` es una **autorización por conteo, no una cota**, y no hay un
mínimo por debajo del cual la herramienta se niegue. Motivo: un mínimo arbitrario
sería un número sin fundamento, y este número sale del dato. Lo que se gana es
que la decisión no se pueda tomar por descuido, y que no sea silenciosa.

## 3. LA CABECERA DEL `.tsv`

**MEDIDO: la premisa del encargo era falsa.** El `.tsv` **no** decía que
`--congelar` fuese destructivo. Ese aviso estaba en el docstring y el comentario
de `reenvio_freeze.py`. Lo que el `.tsv` **sí** afirmaba, y era falso, es otra
cosa:

> `COLUMNAS  (5, y las 5 en las 49 filas: un formato mixto seria peor que ninguno)`

MEDIDO: el ancho único del cuerpo es **6**, en las **49** filas. Y el bloque
nombraba **5** campos, omitiendo `relacion`. Una cabecera que cuenta una cosa y
enumera otra vuelve a mentir, y entrena a quien la lee a saltar avisos.

Corregidas esas dos. Añadido un bloque `COMO SE MANTIENE ESTE FICHERO` con la
semántica del merge y de los códigos. **El cuerpo no se tocó**: MEDIDO
byte a byte idéntico y `sha256_cuerpo` sigue en `08c27e49…`, que es lo que hace
que G1 siga verde.

MEDIDO que se pierden **exactamente 2** líneas de cabecera —las dos falsas— de
139. Las otras 137, que son prosa medida con citas a números y líneas de
hallazgos, siguen ahí verbatim.

`escribir()` deja de emitir una plantilla fija y pasa a **sustituir solo las
líneas que son dato suyo**, reconociéndolas por etiqueta. Motivo: una plantilla
fija borraría las 118 líneas de prosa medida del mapa real, y lo único que
sobreviviría sería el texto de la herramienta sobre sí misma.

## 4. VALORES ESPERADOS QUE CAMBIARON

Ninguno se tocó «para que pase». Dos, con su motivo:

1. `cuerpo()`: de 5 campos a **6**, con `relacion` derivada
   (`relacion_de()`) y no constante. El criterio —«una fila es exactamente su
   línea TSV»— no cambió; cambió el esquema. Añadida además la aserción de que
   la fila conserve su `relacion` y su `procedencia` propias.
2. Fixture de la lesión L2: de «2 filas no derivables» a **3**. El fixture
   lleva 1 `prosa:` + 2 `git:`, y el valor esperado estaba mal contado. El
   **fallo lo dio el self-test**, no la aserción.

Y un bug **real** que el self-test encontró en mi propio código: `plan_merge`
comparaba `p.get("relacion")` contra `relacion_de(n)`, o sea una **ausencia**
contra una **afirmación** — `None != "contenido"` se reportaba como conflicto de
datos. Ahora las dos se derivan con la misma regla. Sin el control L6 (stem
truncado) no habría salido.

## 5. POR QUÉ ESTO ES FALSABLE

`--self-test` **no** comprueba que el congelado se niegue a escribir cuando el
fichero está presente: eso no dice nada del bypass, porque el bypass es
justo la combinación de banderas que esquiva esa negación.

MEDIDO por inyección del defecto antiguo (`merged = []`, sin conservar):

```
13 FALLAS, incluidas:
  L1: con reenvios() vacio el mapa conserva las mismas filas: obtuve 0, quiero 4
  L1: las 3 filas no derivables (1 prosa:, 2 git:) sobreviven con su valor: obtuve []
  P1: --congelar contra reenvios() vacio deja el fichero BYTE A BYTE como estaba
  P2: las 43 diff, 2 git: y 4 prosa: del mapa real siguen ahi: obtuve ['diff']
```

`L1`–`L8` ejercitan la función de merge sobre un mapa con filas `prosa:` y
`git:`. `P1`–`P2` la ejercitan **contra el mapa real de 49 filas en disco**, que
es donde estaba el defecto.

## 6. LO QUE QUEDA ABIERTO

- **`reenvio_gate.py:364` tiene la misma desincronización.** Construye
  `filas_rf` con `"procedencia": p[4]`, o sea `relacion`. MEDIDO que hoy no
  afecta a nada: `verificar()` no lee `procedencia`, y G5 sigue verde. No se
  toca — está fuera del ámbito de este nodo, y cambiarlo cambia lo que G5 mide.
  Es la cuarta copia del mismo número, y la cuarta vez que se desincroniza.
- **`--sustituir` no tiene tope inferior de filas**, por lo decidido en §2.
- El `TypeError` de `escribir()` llevaba **una** ejecución sin que nadie lo
  notara, porque `--verificar` y el self-test no escriben. MEDIDO que ahora hay
  un control (`escribir()` no lanza y deja fichero) y un round-trip con sha.
- `findings_index.py:717` sigue diciendo que «`--congelar` regenera y BORRA esas
  6 filas». MEDIDO que ya no es cierto. No se toca: está fuera de ámbito y es una
  afirmación en prosa, no un control.

## 7. ESTADO MEDIDO DESPUÉS

```
reenvio_freeze.py --self-test   self_test: OK                                  rc=0
reenvio_freeze.py --verificar   verificar: 49 pares, OK                        rc=0
reenvio_freeze.py               congelado: 49 pares  sha256 08c27e49…           rc=0
reenvio_freeze.py --congelar    sin cambios, 49 pares, nada escrito            rc=0
reenvio_gate.py                 las 8 comprobaciones se sostienen              rc=0
refs_repair.py --self-test      self-test OK                                    rc=0
findings_index.py --self-test   self-test OK                                    rc=0
```

MEDIDO que `reenvios_estable()` sigue devolviendo 49 filas con
`{diff: 43, git: 2, prosa: 4}` y `{contenido: 45, numero: 4}`. El mapa congelado
**no se ha modificado**: `sha256` del cuerpo idéntico antes y después.
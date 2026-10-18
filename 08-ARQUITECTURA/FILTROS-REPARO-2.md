# FILTROS-REPARO-2 — cinco filtros reparados, con antes y después medidos

```
NODE                FILTROS-REPARO-2
CLASE               reparo-de-instrumento · lectura de código y ejecución de herramientas
WORK_CLASS          READ_ONLY
ESCRITURAS          6 ficheros: 5 herramientas editadas + 1 nueva (la puerta)
GPU                 INTACTA · no se ha abierto /dev/dri/* · ningún ioctl · nada de sysfs
CORPUS DE PRUEBA    RESEARCH/working/linux-7.1.3, RESEARCH/kernelbuild/linux-7.1.3,
                    RESEARCH/baseline/linux-7.1.3, rx550-upstream-7.2.8/linux-7.2.8
MEDICION            2026-10-04 · Python 3.14.7 · kernel de la tabla de §2
ORIGEN              08-ARQUITECTURA/FILTROS-MAL-FORMADOS.md (md5 5a9270c77605, verificado)
MODELO DE REPARO    06-INGENIERIA-INVERSA/findings/1055-hwip-convierte-el-filtro-en-conclusion.md
COMMIT              NINGUNO. Nada de git add. Los ficheros tocados están en §8.
```

---

## 0. Veredicto en una línea

**Cinco de los cinco argumentos del encargo están reparados y medidos antes y después,
y cada uno sale ahora con `rc≠0` o con una declaración anclada al valor pedido. Los cinco
tenían además un segundo defecto que el encargo no pedía, y cuatro de esos cinco eran de la
misma familia: el argumento no se aplicaba en uno de los modos de salida —`regconst.py` y
`cap_census.py` lo ignoraban en `--json`, `dires.py` lo ignoraba en `--contar`—, y el quinto
era que el `rc` del arreglo no llegaba al shell en `inst_closure.py`. La puerta que el censo
§8 describe pero no existía está escrita, con 26 vectores de self-test de los que 3 tienen
que ser RECHAZADOS, y pasa por `toolreg` con `cwd=tools/` en 3,44 s. Y la puerta NO está
verde: dice `CALLA 1`. Eso es lo que la hace una puerta.**

Las cifras de self-test, todas medidas por ejecución y no contadas a mano:

| herramienta | vectores antes | vectores después |
|---|---|---|
| `tools/regconst.py` | 15 | **27** |
| `tools/cap_census.py` | 7 (sin cifra impresa) | **49** |
| `revkit/dires.py` | no había | **15** |
| `08-ARQUITECTURA/tools/inst_closure.py` | 20 (sin cifra impresa) | **27** |
| `tools/trace_path.py` | 19 | **29** |
| `tools/puerta_filtros.py` | no existía | **26** |

---

## 1. El método, y por qué es el que exige el encargo

Cada reparación tiene cuatro mediciones, y ninguna es una afirmación:

1. **Antes**, con la salida entera guardada a fichero, para poder hacer `diff` y no
   «aproximadamente lo mismo». En `trace_path.py` ese `diff` es el que demuestra la
   frase del censo: las dos salidas difieren en **una** línea de ocho.
2. **Después**, con el caso bueno, porque un arreglo que rompe el camino bueno no es un
   arreglo.
3. **Después, con el caso que NO debe funcionar**, que es el que demuestra que ahora
   falla con `rc≠0` y no con un cero.
4. **Self-test antes y después**, por ejecución.

Dos decisiones de método que conviene que se vean:

- **El corpus de `trace_path.py` es `kernelbuild`, no `working`.** `trace_path.py`
  valida `--chip` contra `include/drm/amd_asic_type.h`, y ese fichero no existe en
  `RESEARCH/working/`. Con `working`, el `--chip` da `rc=2` y no se mide `--root` sino
  el enum. Con `kernelbuild` el chip vale 17 y `--root` es lo que se está midiendo.
  Es el mismo error que el primer intento del hallazgo 1055, y lo digo porque me pasó
  al elegir el corpus.
- **Los vectores nuevos de self-test sustituyen al corpus por un fixture sintético**
  cuando el corpus cuesta segundos. `regconst.py` tarda 30 s por invocación, así que sus
  vectores de `--solo` sustituyen `medir` y llaman a `main()` de verdad. Un vector que
  tarda 30 s no se ejecuta nunca, y un vector que no se ejecuta no es una red.

---

## 2. La tabla, una por herramienta

`n` es el número que la herramienta declara: filas de tabla, o entradas del campo que ella
misma publica. No es el número de líneas de salida.

### 2.1 `tools/regconst.py:395 --solo`

| | antes | después |
|---|---|---|
| `--solo NO_EN_CORPUS` (control) | rc=0, **3** filas, resumen de **4** clases | rc=0, **3** filas, resumen de **1** clase |
| `--solo CLASE_QUE_NO_EXISTE` | rc=0, **0** filas, resumen de **4** clases | **rc=2**, 0 filas, error que nombra el valor y las 4 clases que sí hay |
| `--solo GRAF_8_0` | rc=0, **0** filas, resumen de **4** clases | **rc=2**, idem |
| `--json --solo NO_EN_CORPUS` | rc=0, **35** entradas (**filtro ignorado**) | rc=0, **3** entradas, `distribucion={NO_EN_CORPUS: 3}` |
| `--json --solo CLASE_QUE_NO_EXISTE` | rc=0, **35** entradas (**filtro ignorado**) | **rc=2**, 0 bytes de JSON |
| sin filtro (no regresión) | rc=0, 35 filas, 4 clases | rc=0, 35 filas, **las mismas 4 clases** |
| self-test | PASS, **15** vectores | PASS, **27** vectores |

El resumen que se contradecía a sí mismo:

```
antes:   35 #define con valor leidos en el driver: NO_EN_CORPUS 3, NO_ES_REGISTRO 24,
                 PROVEN 5, PROVEN_POR_CITA 3          <-- con CERO filas debajo
despues: 3 #define con valor leidos en el driver: NO_EN_CORPUS 3
         Filtro --solo NO_EN_CORPUS aplicado: la tabla de arriba y este recuento son
         las mismas filas.
```

El tercer defecto, **no listado por el censo**: `--json` ignoraba el filtro. Las dos
salidas byte a byte idénticas, md5 `3ff3b464888c4804b6d1304814a4e868`:

```
$ python3 tools/regconst.py --json | md5sum
3ff3b464888c4804b6d1304814a4e868
$ python3 tools/regconst.py --json --solo CLASE_QUE_NO_EXISTE | md5sum
3ff3b464888c4804b6d1304814a4e868
```

La causa: la rama `if a.json: return 0` estaba **antes** de que se calculara `vis`.

### 2.2 `tools/cap_census.py:258 --cap`

| | antes | después |
|---|---|---|
| texto `--cap PHM_TYPOXX` | rc=0, **0** filas | **rc=2**, error a stderr que nombra el valor y las 66 |
| JSON `--cap PHM_TYPOXX --json` | rc=0, `capabilities=66`, `rows=66` | **rc=2**, 0 bytes de JSON |
| texto `--cap SQRamping` (control) | rc=0, **1** fila | rc=0, **1** fila + `1 de 66 capabilities` |
| JSON `--cap SQRamping --json` (control) | rc=0, **`capabilities=66`, `rows=66`** | rc=0, **`capabilities=1`, `medidas=66`, `rows=1`** |
| sin filtro (no regresión) | 66 | 66 |
| self-test | OK, 7 comprobaciones **sin cifra** | OK, **49** vectores, con la cifra impresa |

El caso del control es el que más cuesta: con un valor **que sí existe**, `--json`
devolvía las 66 filas. El censo midió el valor inexistente; el que existe es peor,
porque ahí el filtro parece funcionar.

**Por qué aquí sí es legítimo el `rc=2`**, cuando en un filtro abierto normalmente no lo
sería: el filtro es `only in str(r["cap"])`, coincidencia de subcadena sobre el nombre.
De ahí se sigue, y se comprobó sobre 18 valores de la población real, que

```
filas seleccionadas == 0   <=>   el valor no es subcadena de NINGUN nombre
```

Si el valor fuera subcadena de un solo nombre, ese nombre estaría en la población y su fila
saldría. O sea que **no existe aquí el caso «el filtro casó y no hay nada»**: el filtro y
la población son el mismo conjunto de nombres. El vector que sostiene esa equivalencia
está en el self-test, y en los dos sentidos.

### 2.3 `revkit/dires.py:112 --bloque`

| | antes | después |
|---|---|---|
| `--bloque bif` (control) | rc=0, **3** filas | rc=0, **3** filas + `filtro --bloque bif: 3 de 8 entradas de este offset` |
| `--bloque BIF` (mayúsculas) | rc=0, **0** filas | **rc=2**, nombra el valor y los **37** bloques del índice |
| `--bloque bloque_que_no_existe` | rc=0, **0** filas | **rc=2**, idem |
| `--bloque athub` (**existe**, no define el offset) | rc=0, **0** filas | **rc=1**, declara NOT_FOUND y lista los 8 bloques que sí definen `0x1537` |
| `--contar` con y sin `--bloque` | md5 **idéntico** `326594172815b3336fdf970b11070c9d` | md5 **distinto**: `326594…` sin filtro, `833667d6ad37cf2cf36e4cf6d23b508f` con `--bloque bif` |
| `--contar --bloque inexistente` | rc=0, ignorado | **rc=2** |
| self-test | **no existía** | PASS, **15** vectores |

Dos fallos distintos, y separarlos es el fondo del arreglo:

- **el bloque no está en el índice** → el nombre está mal escrito → `rc=2`, no se ha medido nada.
- **el bloque está pero no define ese offset** → la consulta es válida y la respuesta es
  un vacío → `rc=1`, declarado, que es el código que la herramienta ya usaba para «no está
  en el índice».

Es la distinción que el propio `dires.py` hace en `:184-192` con `NOT_FOUND` frente a
`PROVEN_ABSENT`, y que el filtro fundía en un vacío mudo igual para las dos.

Dos cosas medidas de paso:

- El corpus tiene **39** directorios bajo `asic_reg/` y el índice tiene **37** bloques. Los
  dos que faltan son `wafl` y `xgmi`, y la razón es que sus únicos ficheros son
  `_sh_mask.h` y `_smn.h`, que no llevan dirección. Validar contra el **índice** y no contra
  la lista de directorios es lo correcto: un directorio sin direcciones daría siempre vacío.
- El caso `--bloque athub` es el que hace útil la reparación. `athub` es un bloque real,
  lo enumera `--contar`, y aun así con `--bloque athub` no hay entrada en `0x1537`. Antes
  eso era idéntico a haber escrito `BIF`.

### 2.4 `08-ARQUITECTURA/tools/inst_closure.py:841 --asi`

| | antes | después |
|---|---|---|
| sin `--asi` (default `dce112`) | rc=0, `semillas del ASIC (dce112): 0 de []` | rc=0, `ASIC dce112: existe en el corpus (25 ASIC)` + `semillas del ASIC (dce112): 0.` + la razón por la que es 0 |
| `--asi dce999` | rc=0, `semillas del ASIC (dce999): 0 de []` | **rc=2**, nombra el valor y los **25** ASIC |
| `--asi lista-que-no-existe` | rc=0, idem | **rc=2**, idem |
| BASE sin `dc/resource` | — | **no rechaza**: declara `no he podido comprobar` y sigue |
| cifras del informe | funciones indexadas 7892, alcanzables 5353 | **7892 y 5353, sin cambio** |
| self-test | OK, 20 comprobaciones `Tn`, **sin cifra** | OK, **27** vectores (20 heredadas + 7 nuevas) |

Este era un `ETIQUETA_MUERTA`, no un vacío: `a.asi` no aparecía más que en un `print`, y
el 0 era correcto. El arreglo **no ha puesto la cuenta a 1 ni ha sembrado nada**:
`ASIC_CONSTRUCTORS` está vacío a propósito (comentario de `:77-83`: sembrar el constructor
de ASIC mide solo el camino de arranque, no el de modo de pantalla, y por eso salía 2,1 %
en lugar de 28,7 %). Cambiar eso desde un arreglo de filtro habría cambiado los porcentajes
de la tabla sin que nadie lo pidiera.

La población es real y se calcula del mismo `BASE` que la herramienta ya recorre: los
directorios de `dc/resource/`, 25 en este corpus, `dce112` entre ellos.

**Un segundo defecto, encontrado por medición:** el `return 2` no llegaba al shell.

```
antes del arreglo, con el return ya escrito:
  ERROR: --asi dce999 no es ningun ASIC de este corpus.
  ...
  rc=0                      <-- el mensaje salia y el proceso seguia con 0
```

El fichero terminaba en `main()` a secas, sin `sys.exit(main())`. Un `return` que no se
propaga al código de salida es decorativo, y es el mismo defecto que se repara, un nivel
más abajo. Corregido y medido: `rc=2`.

### 2.5 `tools/trace_path.py:498 --root`

| | antes | después |
|---|---|---|
| `--root NO_EXISTE_ESTA_RUTA` | rc=0, `INVERSO … N_CALLERS`, `ficheros .c indexados: 0` | **rc=2**, error a stderr que nombra la ruta |
| `--root <amdgpu>` (control) | rc=0, `INVERSO … N_CALLERS`, `ficheros .c indexados: 304` | rc=0, **denominador antes del veredicto**, `N_CALLERS` intacto |
| `--root <ruta sin .c>` | — | **rc=2**, con otro texto: la ruta existe y no hay nada que leer |
| `--json` | no llevaba la población | lleva `ficheros_indexados=304` y `root` |
| sin `--root` (no regresión) | — | rc=0, `970` ficheros |
| `--from` (no regresión) | veredicto `NO_ENCONTRADO` | **intacto** |
| self-test | OK, **19** vectores | OK, **29** vectores |

La frase del censo reproducida, con el `diff` de las dos salidas completas:

```
8c8
<   ficheros .c indexados: 0
---
>   ficheros .c indexados: 304
```

Ocho líneas de salida, una de diferencia, y esa línea es el tamaño de la población que no
se ha medido. Un símbolo al que nadie llama da el mismo `N_CALLERS` que un símbolo en un
corpus que no se ha leído.

El arreglo tiene dos mitades y las dos eran necesarias:

1. **`--root` se valida** con la misma forma que `--chip` veinte líneas más abajo del
   mismo fichero (`ERROR` a stderr, `rc=2`). El patrón correcto estaba a veinte líneas.
2. **El denominador se imprime antes del primer veredicto**, no en la última línea. Antes
   se imprimía en `:659`, que es exactamente la línea que era la única diferencia entre
   las dos salidas. Si el denominador va después, el veredicto ya se ha leído y solo queda
   la línea de al lado para corregirlo. Es el requisito que §8.7 del censo le pone a la
   puerta, y aquí se cumple por construcción.

Con el denominador delante, el control queda así:

```
  poblacion indexada: 304 ficheros .c bajo .../amd/amdgpu
  Los veredictos de abajo son sobre ESA poblacion y sobre
  ningun otro corpus. Leer un veredicto sin este numero es
  leerlo sin denominador.

  INVERSO  amdgpu_gc_atomic_cmdexec                     N_CALLERS      -
```

`N_CALLERS` sigue siendo el mismo veredicto. Lo que ha cambiado es que ahora se puede leer.

---

## 3. `tools/puerta_filtros.py` — escrita, y NO está verde

El §8 del censo describe una puerta que no existía. El encargo la condiciona a que la
justifique, así que primero la Justificación y después la puerta.

### 3.1 Las tres condiciones que pedía el encargo

**El oráculo va anclado al valor.** No a la ausencia de una línea, y no a la salida
entera:

```
ok := rc != 0
   ó existe una LÍNEA que contenga a la vez
        - el VALOR pedido, tal cual se escribió
        - una declaración de que ese valor no está en el conjunto válido
```

El anclaje a la **línea** es lo que arregla la falsificación del §8.3-bis, y está medido en
el self-test con el caso real reproducido: una salida con un `NO ENCONTRADO` que no
menciona el valor, y que en otra sección afirma lo contrario, sigue dando `CALLA`. Con el
oraculo ancho de §8.3-bis daba `OK`, que es el falso verde que el censo documentó.

Y hay un caso que el oráculo Anchored-to-the-line todavía podría aprobar mal, y que está
también en el self-test: una salida que **imprime el valor pedido** en la tabla pero no
declara nada. Un oráculo que buscara el valor en toda la salida la aprobaría.

**Tiene su propio self-test con vectores que fallan a propósito.** 26 vectores, de los que
**3 tienen que ser RECHAZADOS**:

- cuatro herramientas mínimas creadas en un temporal, con el comportamiento fijado por
  construcción: la que calla, la que declara, la que sale con `rc=2` sin explicar nada, y
  la que imprime el valor sin declarar;
- el caso de §8.3-bis, en texto plano, sin `subprocess`;
- el caso de la declaración en otra línea que el valor.

Están escritos en herramientas mínimas y no contra herramientas del proyecto **a
propósito**: un self-test que dijera «`assert_contract` tiene que callar» se rompería el día
que alguien repare `assert_contract`, y un self-test que falla cuando el proyecto mejora es
un self-test malo.

**Se ejecuta con `cwd=tools/`.** Toda ruta sale de `__file__`, nunca de `os.getcwd()`.
Comprobado de tres formas:

- por `toolreg.run_selftests`, que es quien impose `cwd=os.path.dirname(t.path)`:
  `PASS`, `rc=0`, **3,44 s**;
- un vector compara la misma herramienta con `cwd=raíz` y con `cwd=tools/` y exige
  salida idéntica;
- la salida completa en `--json` es byte a byte idéntica desde los dos sitios,
  md5 `270b618344909fcc034a5928aed4f3a0`.

### 3.2 Lo que dice cuando se ejecuta

```
  OK       6 · CALLA 1 · CALLA_ABIERTA 2 · NO_EJECUTADO 0 · de 9 vectores

  herramienta                          arg         estado    clase
  tools/regconst.py                    --solo      OK        CERRADO
  tools/cap_census.py                  --cap       OK        CERRADO
  revkit/dires.py                      --bloque    OK        CERRADO
  08-ARQUITECTURA/.../inst_closure.py  --asi       OK        CERRADO
  tools/trace_path.py                  --root      OK        RUTA
  tools/hwip.py                        --chip      OK        CERRADO
  tools/assert_contract.py             --fichero   CALLA_ABIERTA  ABIERTA
  tools/citegen.py                     --fichero   CALLA_ABIERTA  ABIERTA
  revkit/regs.py                       --asic      CALLA     CERRADO
```

**No está verde, y por eso significa algo.** El §8.4 del censo dijo que cuando se reparen
las herramientas la puerta debe bajar, y que si `que_callan` no baja «la puerta está mal
escrita». Aquí ha bajado de los 9 sobre 10 del prototipo del censo a **1**, y el que queda
es `revkit/regs.py --asic`, que es un filtro de clase **cerrada** sin reparar. Los otros dos
`CALLA_ABIERTA` son de clase abierta, y el oráculo no puede exigirles nada: `CALLA_ABIERTA`
es un estado propio y no se mezcla con `CALLA` en el recuento, porque son dos cosas
distintas — un defecto de la herramienta frente a un límite del argumento.

### 3.3 Un defecto de la propia puerta, encontrado por medición

La puerta tenía un defecto de la misma familia que los que repara, y se ha visto porque se
ha **intentado parsear su salida en JSON**:

```
$ python3 tools/puerta_filtros.py --json | python3 -c "import json,sys; json.load(sys.stdin)"
json.decoder.JSONDecodeError: Expecting value: line 1 column 3 (char 2)
```

`--json` imprimía el bloque de texto antes del JSON. Es exactamente lo que
`cap_census.py` hacía con `--cap`, y está arreglado: `verbose=not a.json`.

---

## 4. Lo que NO he reparado, y por qué

### 4.1 Los nueve argumentos que quedan del censo

`fingerprint.py --solo`, `rx550/regctx.py --prefix`, `regs.py --asic`,
`uninit_copy.py --clase`, `msg_census.py --msg`, `msg_census.py --root`,
`assert_contract.py --fichero`, `citegen.py --fichero`, `reg_census.py --gfx`.

No estaban en el encargo, que pedía cinco en un orden. `regs.py --asic` es el único que la
puerta cuenta como `CALLA` de clase cerrada, y es el candidato más claro para el siguiente
nodo: el mismo patrón de las cinco reparadas, sobre una población calculable.

### 4.2 `tools/cap_census.py --chip` — medido, declarado, NO reparado

Está en el mismo fichero que he tocado y es un defecto real. MEDIDO:

```
$ python3 tools/cap_census.py --kernel $K --chip CHIP_GA10  --json
chip = CHIP_GA10        chip_value = None   capabilities = 66   rc=0
$ python3 tools/cap_census.py --kernel $K                    --json
chip = CHIP_POLARIS12   chip_value = None   capabilities = 66   rc=0
```

`chip_value` es `null` **incluso para el chip correcto**. La causa, medida:

- `parse_chip_enum` (`:91-94`) devuelve `{}` **en silencio** cuando el fichero no existe;
- `include/drm/amd_asic_type.h` existe en `RESEARCH/kernelref/` y `RESEARCH/kernelbuild/`
  y **no existe** en ninguno de los dos corpus que `cap_census` recorre
  (`RESEARCH/working/linux-7.1.3` y `rx550-upstream-7.2.8/linux-7.2.8`).

No lo he reparado por dos razones, y la segunda es la importante:

1. `--chip` **no filtra nada**. No entra en el cálculo de ninguna cifra, así que no es un
   filtro: el arreglo correcto es una **declaración**, no un `rc=2` de filtro.
2. Declararlo exige decidir **cuál es el enum autoritativo**, y esa decisión no es mia. Hecho
   sin ella, el arreglo sería el primer intento fallido del hallazgo 1055 clavado a otra
   herramienta: validar contra un fichero que no está en el árbol que la herramienta recorre
   deja `rc=2` hasta para el valor correcto. El 1055 lo cuenta así, y por eso está escrito en
   la cabecera de `hwip.py`.

Es el mismo «no hay datos» disfrazado de «el filtro está mal», pero del lado contrario: aquí
la herramienta **no dice** que no ha podido resolver el chip.

### 4.3 `ASIC_CONSTRUCTORS = []`

No lo he llenado. Es una decisión de diseño, documentada en `:77-83`, y su efecto medido fue
sacar el 2,1 % que había que evitar. Llenarlo desde un arreglo de filtro cambiaría los
porcentajes de la tabla final sin que nadie lo pidiera. Lo que sí he hecho es que la etiqueta
que lo anuncia esté **comprobada**, y que el número 0 diga por qué es 0.

### 4.4 `ZeroDivisionError` preexistente en `inst_closure.py:1056`

Con un `BASE` sin ficheros, la tabla final divide `TA / T` con `T = 0`:

```
rc = ZeroDivisionError   en la linea 1056, la tabla de subarboles
```

Es anterior a este nodo y está fuera del encargo. Se ha encontrado porque el vector de la
rama «no he podido comprobar la población» pasa por `main()` con un `BASE` falso, y el
`ZeroDivisionError` ocurre **después** de esa declaración, en la última línea. No lo he
tocado.

### 4.5 Las declaraciones que faltan en tres cabeceras

`toolreg.run_selftests` **no ejecuta** el self-test de `regconst.py`, `cap_census.py` ni
`dires.py`: los marca `REFUSED_UNDECLARED` porque su cabecera no declara
`WORK_CLASS=READ_ONLY` con `WRITE_EXECUTION=NONE`. Estado medido:

```
puerta_filtros.py  PASS               0     3.44
regconst.py        REFUSED_UNDECLARED None  None
cap_census.py      REFUSED_UNDECLARED None  None
trace_path.py      PASS               0     0.07
dires.py           REFUSED_UNDECLARED None  None
inst_closure.py    PASS               0     0.07
```

Es anterior a este nodo. **No he añadido las declaraciones**, y esa es una decisión
deliberada: `WORK_CLASS=READ_ONLY` es una afirmación de seguridad sobre la herramienta
**entera**, y yo he auditado un filtro, no la herramienta. Declarar en verde algo que no he
auditado para que una puerta lo ejecute sería el mismo error que esta puerta audita, y
`toolreg` existe precisamente para no ejecutar código no clasificado.

### 4.6 Lo que no se puede medir aquí

- `tools/fingerprint.py` declara `journalctl` como productor de la fila `asic`, así que no
  es ejecutable en el encargo de este nodo. Es también el `--solo` con el titular de target
  debajo, que el censo señala como el más danaño después de los tres primeros.
- `tools/reg_census.py --gfx`: el censo dice que con `--gfx gfx_9_0` la resolución no terminó
  en 180 s. No lo he vuelto a medir ni tocado.

---

## 5. Lo que un arreglo NO es

Cinco cosas que pasaron y que dejo escritas porque son el patrón:

1. **Delegar en una población que no está en tu árbol.** El `1055` lo cuenta y yo casi lo
   repito al elegir `RESEARCH/working/` para `trace_path.py`. La población tiene que salir
   de lo que la herramienta **ya recorre**.
2. **Anclar el oráculo a la salida en vez de a la línea.** Es el §8.3-bis, y el caso está
   ahora como vector en las dos herramientas.
3. **Un `return` que no llega al shell.** Encontrado porque el mensaje salía y el proceso
   seguía en 0. Un arreglo que solo se ha ejecutado una vez, en el caso bueno, no está
   medido.
4. **Un vector que exige un orden o un recuento que no es el suyo.** Tres vectores míos
   fallaron en la primera pasada porque buscaban `MM_` al principio de una línea que empieza
   por la clase, y porque contaban cuatro filas donde había dos contando la leyenda. Un
   vector que falla por su propia comprobación hace dudar del arreglo, que es peor que no
   tener vector. Está escrito en el fichero.
5. **Imprimir el valor no es declarar el valor.** La herramienta mínima
   `valor_sin_declarar.py` del self-test de la puerta existe exactamente por eso.

---

## 6. Los ficheros que he tocado, y su estado

| fichero | acción | sha256[:16] | líneas |
|---|---|---|---|
| `tools/regconst.py` | editado | `0a1ca689f1806412` | 614 |
| `tools/cap_census.py` | editado | `6a283b50d3de6aba` | 558 |
| `revkit/dires.py` | editado | `87f3e2f1a000267f` | 383 |
| `08-ARQUITECTURA/tools/inst_closure.py` | editado | `93f115b90c5bb405` | 1077 |
| `tools/trace_path.py` | editado | `4a5ea2d649191b72` | 920 |
| `tools/puerta_filtros.py` | **nuevo** | `144f72c2dc631baa` | 606 |
| `08-ARQUITECTURA/FILTROS-REPARO-2.md` | **nuevo**, este fichero | — | — |

Hashes de partida, para que se vea que la deriva se comprobó antes de editar (§2 del
Apéndice A del censo): `regconst.py` `d96d1cd5014b8ac1`, `cap_census.py`
`86d153a17176a1e2`, `dires.py` `63070f7997e92754`, `trace_path.py` `88da33bec82e7eb9`.
**Los cuatro coinciden** con los que el censo registró. `hwip.py` **no** coincide con el
censo porque el nodo 1055 lo reparó entre medias, que es lo esperado.

**No tocado, por los motivos del encargo:** `tools/riesgo.py`, `revkit/cn8.py`,
`revkit/huerfanos.py`, `04-IMPLEMENTACION/rx550-driver/`, `findings/`, `docs/`.

`git status` muestra además ficheros sin seguimiento que **no son míos** y que no he
abierto: `tools/dwarfx.py`, `tools/pm4ops.py`, `tools/riesgo.py`,
`08-ARQUITECTURA/GRAFO-CLAVE-NO-UNICA.md`, `08-ARQUITECTURA/artifacts/R2-PM4OPS/`. Son de
otras sesiones que están trabajando en este árbol ahora mismo.

**No he hecho `git add` ni `git commit`.** `git diff --cached --name-only` está vacío.

Una precisión que hace falta porque es observable: **`HEAD` se ha movido durante este
turno**, de `6acd483` a `9a5ae62`, y **no ha sido por este trabajo**. Lo han hecho dos
sesiones que estaban activas a la vez:

```
9a5ae62  hallazgo 1056: \d{3} fundia 142 documentos en nodos ajenos
1d88d56  decodificador ATOMBIOS en C, y la segunda correccion de 1053
```

Ninguno de los dos commits toca ninguno de mis seis ficheros, y los seis siguen sin
confirmar tal y como los entrego:

```
 M 08-ARQUITECTURA/tools/inst_closure.py
 M revkit/dires.py
 M tools/cap_census.py
 M tools/regconst.py
 M tools/trace_path.py
?? tools/puerta_filtros.py
```

---

## 7. La comprobación del castellano de este fichero

Recorrido entero contando `ord(c) > 127` cuyo nombre Unicode contenga `CJK`, `HIRAGANA`,
`KATAKANA`, `HANGUL` o `IDEOGRAPHIC`.

```
0 CJK  0 HIRAGANA  0 KATAKANA  0 HANGUL  0 IDEOGRAPHIC
```

En la primera pasada de este fichero **sí** había dos ideogramas, en una línea donde
iba «la respuesta es un vacío»: se sustituyeron por «la respuesta es un vacío». También
salieron tres pasajes mal escritos («el procesoacia», «perdón, 39 directorios», y una
oración con `ast_contract` de otra herramienta pegada dentro) y se corrigieron. Queda
dicho porque el recuento se hizo después de escribir, y no antes.

Fuera de los ideogramas, los caracteres no ASCII de los seis ficheros de código son
ortografía castellana (`á é í ó ñ ¿`), signos de sección (`§`), punto medio (`·`), raya
(`—`) y, en `trace_path.py`, los dos caracteres de árbol (`→` y `└`) que ya estaban.

---

## 8. Apéndice — el estado del banco de filtros después de este nodo

De los 16 argumentos `VACIO_SILENCIOSO` que cuenta el censo, **5** están reparados y
medidos aquí:

| # | herramienta | argumento | estado |
|---|---|---|---|
| 5 | `tools/regconst.py` | `--solo` | **PROBADO, reparado** |
| 6 | `revkit/dires.py` | `--bloque` | **PROBADO, reparado** |
| 9 | `tools/cap_census.py` | `--cap` | **PROBADO, reparado** |
| 1 | `tools/trace_path.py` | `--root` | **PROBADO, reparado** |
| 2 | `tools/hwip.py` | `--chip` | **PROBADO, reparado** en el nodo 1055 |

Y uno más, que el censo no contaba en los 16:

| | `tools/regconst.py` | `--json` sin aplicar `--solo` | **PROBADO, reparado** |

Quedan **10** sin reparar, y la puerta los ve: `CALLA 1` (clase cerrada, `regs.py --asic`)
y `CALLA_ABIERTA 2` en la lista corta de la puerta, más los siete que la puerta todavía no
lleva en su lista de vectores. La lista de vectores de la puerta es **una lista de trabajo**,
no el censo: el censo son las 16 filas de §4 del documento de origen, y las dos cosas no
deben confundirse.

**El invariante que queda para el siguiente nodo**, en una línea: toda herramienta que acepte
un nombre escrito por una persona y lo compare contra un conjunto que ella misma calcula
tiene que **calcular ese conjunto, imprimirse y rechazar el valor antes de filtrar**, y el
recuento de la salida tiene que describir **lo que la salida ha mostrado**. Si el recuento
se calcula antes del filtro, hay una línea que anuncia cifras que no están debajo, y quien
lee el resumen se lleva el número equivocado sin ver que falta la tabla.


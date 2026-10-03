# 972 · El verde falso que se registrou el 2026-09-29 está CADUCADO; lo que sigue vivo es otra cosa, y no da verde falso

```text
CLASSIFICATION=ERROR+MEASUREMENT+NEGATIVE_RESULT+FALSIFICATION · TRACK=RUNTIME-PROBING
CORPUS=04-IMPLEMENTACION/{compressor,decompressor}, integration_test.sh
HARDWARE_SCOPE=NINGUNO. No se ha tocado la GPU. Cero llamadas a Vulkan.
WORK_CLASS=READ_ONLY primero; luego WRITE_LOCAL (/tmp) para el oraculo
WRITE_LOCAL=/tmp/opencode/oracle-lineb-rc   (PROPIOS, fuera del corpus)
MODIFICATIONS_COUNT=1   (solo este fichero de hallazgo + la reserva 972)
WRITE_EXECUTION=NONE en el corpus. Ningun .c modificado. Ningun binario del corpus ejecutado.
AUTHORIZATION=NONE (ningun cerrojo tomado, ninguno liberado)
AUTORIA=AGENTE-04 (nodo ORACLE-LINEB-RC)
RUNTIME=EJECUCION DE MUTANTES EN /tmp. Nada de MMIO, nada de Vulkan, nada de GPU.
GPU INTACTA
CERROJOS=0
```

Fecha de la medicion: **2026-10-03**. gcc 16.2.1, bash, uid 1000, **sin sudo**, sin `modprobe`/`insmod`/`rmmod`.
Alcance de escritura: `/tmp/opencode/oracle-lineb-rc/` y este fichero.

---

## 0 · Respuesta en una linea

**No. No existe hoy ningun camino por el que un test de la linea B imprima un diagnostico de fallo
y devuelva `rc=0` al shell.** La afirmacion registrada el 2026-09-29 era **cierta** en el commit que
cita, se **arreglo** seis minutos despues, y el arreglo se **conserva** en `HEAD`. LIMITACION #3 esta
**CADUCADA** en su formulacion literal.

Lo que si queda vivo es **otra cosa**, en `integration_test.sh:219`, y **no** produce verde falso:
produce un diagnostico que **miente** sobre el codigo de retorno, y deja **muerta** una rama del
script. Es un defecto real, de direccion opuesta, y esta medido abajo.

---

## 1 · La pregunta y por que la respuesta no es «si, y aqui esta la linea»

La afirmacion bajo examen dice, textual: *«el test devuelve rc=0 aunque imprima [FAIL]»*.

El camino corto habria sido: leer `main()` de `test_decompress.c`, ver un `return 0` al final de la
fase de GPU, y dar el hallazgo por cerrado. **Eso es lo que hice primero, y estaba equivocado.**
La instrumentacion de abajo lo refuto. El error fue mio y es exactamente el que el nodo pedia
evitar: **inferir el codigo de salida leyendo la forma del codigo en vez de midiendo el proceso.**

El problema de fondo es una **inversion de polaridad** que el codigo no declara en ningun sitio:

- `phase_b_gpu_execution()` devuelve **`1` = exito** (`return agree;`, con `agree=1` significando
  *el shader coincide con la CPU*).
- `main` la invierte: `return phase_b_gpu_execution() ? 0 : 1;`

Asi que un `return 0` **dentro** de la fase B significa *fallo*, y se traduce en **exit 1**. El
`return 0` que uno lee como «verde falso» es, en esa funcion, el codigo de fallo. La convencion
existe y es correcta; solo es opuesta a la que sugiere la lectura superficial.

---

## 2 · Lo que la afirmacion cites, y cuando se escribio

El commit que la afirmacion nombra es `b7ed0c1`, `2026-09-29 01:10:20`, *«test_decompress: push
constant de num_blocks; AD-14 corrige el diagnostico del SIGSEGV»*. En esa version el `main`
terminaba en un `return 0;` **incondicional**, con el valor de `agree` calculado y tirado:

```diff
-    return 0;
+    /* phase_b returns 1 on agreement, 0 on any disagreement or failure.
+     * ... a human reading only the return code -- could not tell a failing test from
+        int agree = phase_b(c, "decompress_bc3.spv");
+        return agree ? 0 : 1;
```

 Ese cambio es `edd434b`, `2026-09-29 01:16:41`: **seis minutos y un commit** despues de escribirse
la afirmacion. El defecto existia; se corrigio de inmediato y con el motivo escrito en el propio
parche.

**Lo que NO hizo ese arreglo** — y esto si es un hallazgo, no una nota — es que la reescritura
siguiente (`b65636a`, `01:23:00`, *«Fase 2 verificada»*) volvio a escribir el mismo patron de
`return` **en otro sitio**: `if (!ran_ok) { ...; return 0; }` en la linea 720. Es la misma clase de
defecto reintroducida siete minutos despues de arreglarse la anterior. Y aqui si es LIVE.

Medido en §5.

---

## 3 · El oraculo: por que «mutar y mirar el rc» y no «leer el codigo»

Un oraculo que no puede fallar no es un oraculo. Este se construyo para **poder dar los dos
veredictos**: verde y rojo. Sin eso, un `rc=1` observado no distingue «el codigo esta bien» de
«el aparato esta roto».

Construccion, entera en `/tmp`, sin tocar el corpus:

| pieza | sha256 |
|---|---|
| `src/test_decompress_ORIG.c` (**byte-identico** al corpus) | `491fbf905205015d474ba41fa9c98d9cf3cd7413604ba6087a1bd16bdcabadd2` |
| `run/td_ORIG` | `20f9a82c6d7e17f84deea90c5aa4c028164e9172d9df9d2cbb475e381187ede1` |
| `src/test_decompress_MUTA.c` | `4d4c9cf024ead8c99ee31dc3729714fa3a0f6cd9da590a6d663f3b774bd9f366` |
| `run/td_MUTA` | `ec47f214bdfdfd1c4ecbaff6fed087583317278391274976d550f8abbda6a8e7` |
| `src/test_decompress_MUTB.c` | `69d616bba6fb071695698a0ab6b7af707d20a5634d9e5c4f0388c191b7613e13` |
| `run/td_MUTB` | `dc4bdde1d9bc6f4b9b997379fe970a6469778c09560372396dcf7a69cdc656fb` |
| `src/test_decompress_MUTC.c` | `0fd7c919ebdb6f5c6d84c5dd6a05f2d5e593e4785673b2de12b4810cb779a2de` |
| `run/td_MUTC` | `eddafa9c2a4ee08ee09d7d6f55be5c07a6a9a3b95cd504df80157c962fb2199f` |

Las tres mutaciones son **inyectadas en el punto de disparo del fallo**, jamas en el codigo de
salida que se quiere medir:

- **MUT-A** inyecta un `goto cleanup` **antes de `vkCreateInstance`**. Ejercita el `cleanup:` →
  `if (!ran_ok)` → `return 0` → `main` **reales**, sin tocar Vulkan (todas las variables validas
  `VK_NULL_HANDLE`, luego los `if (handle)` del cleanup saltan y no se llama a **ni una** funcion
  de Vulkan).
- **MUT-B** fuerza `ran_ok=1; agree=0; discrepancies=1` y salta a `cleanup`. Ejercita el **otro**
  `return`, el del veredicto. Es el control de falsabilidad: si esto no puede dar rojo, el aparato
  no sirve para medir nada.
- **MUT-C** es MUT-A con `return 0` → `return 1` en la linea 720. Aísla **que linea** produce el
  codigo de salida.

---

## 4 · La medida, con el comando literal

Construccion (desde `/tmp`, con los objetos del compressor copiados, nunca con `make` sobre el arbol
compartido):

```console
$ cc -std=gnu11 -O2 -Wall -Wextra -fno-strict-aliasing -Icompressor \
     -o run/td_ORIG src/test_decompress_ORIG.c \
     compressor/rx550_compress.o compressor/rx550_compress_avx2.o \
     -mavx2 -lvulkan -ldl -lm
```

```console
$ ./td_ORIG                       # linea base, sin --gpu
>>> rc = 0                        # FASE A OK, "Fase B omitida", ningun FAIL/ERROR

$ TD_FORCE_FAIL=1    ./td_MUTA --gpu
    stderr: ERROR: fallo inyectado antes de crear la instancia Vulkan
    stderr: FASE B: no se llego a ejecutar el shader
>>> rc = 1                         # <-- el fallo diagnosticado SALE con rc=1

$ TD_FORCE_VERDICT=1 ./td_MUTB --gpu
    stdout: VEREDICTO: GPU != CPU, agreement test FALLIDO (1 discrepancias)
>>> rc = 1                         # <-- el veredicto de desacuerdo SALE con rc=1

$ TD_FORCE_FAIL=1    ./td_MUTC --gpu     # identico a MUT-A pero con return 1 en la linea 720
    stderr: ERROR: fallo inyectado antes de crear la instancia Vulkan
    stderr: FASE B: no se llego a ejecutar el shader
>>> rc = 0                         # <-- la linea 720 ES la que produce el 1 de MUT-A
```

**MUT-A y MUT-B juntos son la falsificacion.** Los dos verdes posibles y los dos rojos posibles
quedan alcanzados. Un aparato que solo sabe decir «rojo» no puede sostener la conclusion; este
sabe decir las dos cosas, y las dice en el sentido correcto.

`MUT-C` cierra la atribucion causal: el `rc=1` de MUT-A viene **de la linea 720** y de ningun otro
sitio. No es una correlacion, es la linea.

---

## 5 · El resto de los `[FAIL]` de la linea B, uno a uno

Inventario completo de los productores del token `[FAIL]` en la linea B, y estado de cada uno. La
columna de la derecha es **medida**, no leida.

| fichero | linea | como sale el rc | veredicto |
|---|---|---|---|
| `compressor/test_compress.c` | `51` | `g_failures++` → `main:731` `if (g_failures == 0) return 0; return 1;` | **PROVEN correcto** (medido) |
| `decompressor/test_corpus_validate.c` | `191,195,204,210,212,219,226,260,295,340,342,347,349` | los 12 `return 0` son de *helpers*; `main:375-386` los agrega con `ok &=` y `main:397` `return ok ? 0 : 1;` | **PROVEN correcto** (medido) |
| `decompressor/test_hardware_bc3.c` | `424` | `printf("[FAIL] ...")` seguido de `return 3;` en la linea siguiente | **PROVEN correcto por lectura** — `NOT_RUN`, ver §6 |
| `decompressor/test_decompress.c` | **ninguna** | el token `[FAIL]` **no existe en el codigo**; solo aparece en un comentario, linea 723 | **PROVEN correcto** (medido, §4) |

Los dos que se pudieron falsar sin GPU:

```console
$ cc ... -o tc_FAIL test_compress_FAIL.c rc.o rcavx2.o -mavx2 -lm   # check() forzada a fallar
$ TD_FORCE_FAIL=1 ./tc_FAIL
  [FAIL] output size <= 16 bytes -- struct larger than the contract
  ... (26 lineas [FAIL]) ...
  RESULT: 26 check(s) FAILED
>>> rc = 1
$ ./tc_CTRL                                                # control: check() no puede fallar
  RESULT: all checks passed
>>> rc = 0
```

```console
$ printf '\xde\xad\xbe\xef\x03\x02\x23\x07' > bad/decompress_bc3.spv   # magico erroneo
$ cd bad && ../tcv                       # SIN Mutar el fuente: solo la entrada
  stderr: [FAIL] magic efbeadde, esperado 07230203: no es un modulo SPIR-V
>>> rc = 1
$ cd good && ../tcv                      # el .spv real
  [FAIL] count = 0
>>> rc = 0
```

`test_corpus_validate` es el caso mas fuerte de los tres: **cero mutacion del fuente**, binario
compilado del `.c` del corpus sin tocar, y solo una entrada corrupta.

Y los que el briefing listaba como candidatos y **no** imprimen `[FAIL]` en absoluto
(`rx550-driver/tests/test_{mem,regs,resource,submit,target_match,vm}.c`) usan todos
`return fail ? 1 : 0`, y `shader_vs_c.c:155` usa `return bad_cor == 0 ? 0 : 1`. Patron unico,
correcto, sin excepcion en los siete.

---

## 6 · Lo que SI es un defecto vivo: `integration_test.sh:219`

Este si es un bug real, medido, y **no** es el de la afirmacion.

```bash
# integration_test.sh:216-231
if ! (cd decompressor && "../bin/rx550_decompress" ...) >"$log" 2>&1; then
    rc=$?                                          # <-- 219
    say "   [FAIL] rx550_decompress devolvio $rc"
    if [ "$rc" -ge 2 ]; then
        SKIPPED=$((SKIPPED + 1))                   # <-- 224
    else
        FAILED=$((FAILED + 1))
    fi
    continue
fi
```

Dentro de `if ! cmd; then`, `$?` es el estado de la **negacion**, que es **siempre 0**. No es el de
`cmd`. Medido:

```console
$ bash negtest.sh
cmd real rc=1  -> rc leido tras "if !": 0
cmd real rc=2  -> rc leido tras "if !": 0
cmd real rc=7  -> rc leido tras "if !": 0
```

Consecuencias, medidas con un arnes que reproduce `216-231` y `462-474` **verbatim**
(`/tmp/.../harness/h2.sh`, sha256 `28ba3a9e8f3b9020ac5463b8a9b44a6b4c8fb1ac7a0dc820dfffc12f39d8ef6f`),
con dos texturas (una pasa, la decompresion de la otra falla):

| rc real de `rx550_decompress` | linea impresa | `rc` leido | rama tomada | **EXIT del script** |
|---|---|---|---|---|
| 1 (desacuerdo real) | `[FAIL] ... devolvio 0` | 0 | `FAILED` | **1** |
| 2 (no se pudo ejecutar) | `[FAIL] ... devolvio 0` | 0 | `FAILED` | **1** |
| 3 (idem) | `[FAIL] ... devolvio 0` | 0 | `FAILED` | **1** |

Tres consecuencias, y la tercera es la que importa:

1. **La linea 220 miente.** Dice `devolvio 0` para un proceso que devolvio 1, 2 o 3. Quien lea el
   log Vera un codigo que el proceso nunca emitio. Ese log es la prueba misma de que fallo, y es
   falsa.
2. **La rama `SKIPPED` de la linea 224 es codigo muerto.** `0 -ge 2` es falso siempre. La
   distincion que el comentario de la linea 222 dice querer («rc=1 es discrepancia real; rc>=2 es
   que no se pudo ejecutar») **no se puede llegar a tomar**.
3. **El verde falso esta LATENTE, a un bugfix de distancia.** Si se corrige la captura de `rc` —que
   es lo que haria cualquiera que leyera el comentario de la linea 222 y lo tomara en serio— la
   rama `SKIPPED` pasa a ser alcanzable, y entonces:

```console
$ ./h2.sh 2 fixed          # captura de rc CORREGIDA
>>> EXIT = 0                # ESTADO: PASO    <-- VERDE FALSO
$ ./h2.sh 3 fixed
>>> EXIT = 0                # ESTADO: PASO    <-- VERDE FALSO
```

   Es decir: **el bug actual es lo que esta impidiendo el verde falso que la correcion natural del
   bug introduciria.** Con `TOTAL>0` (basta una textura que pase) y un `rx550_decompress` que no
   puede ejecutar, el script sale **0** y se lee `ESTADO: PASO`.

Esto **no** es la LIMITACION #3. No imprime `[FAIL]` con `rc=0`; imprime `[FAIL]` con `rc!=0` y
un numero inventado. La direccion es la contraria.

---

## 7 · Lo que NO demuestra (esta seccion es cierta, no decorativa)

- **No demuestra nada sobre la GPU.** Cero llamadas a Vulkan en todo el nodo. `--gpu` se paso como
  argumento, pero ninguna mutacion llega a `vkCreateInstance`: los tres `goto cleanup` inyectados
  estan **por encima**, y en `cleanup` todos los handles siguen en `VK_NULL_HANDLE`, luego los
  `if (handle)` no entran. `test_decompress --gpu` **real** = `NOT_RUN`, por diseno: el cerrojo
  `LOCK_TAKEOVER` lo tiene `global-coordinator-04` y este nodo es `READ_ONLY`.
- **No demuestra nada de `test_hardware_bc3`.** Su `[FAIL]` → `return 3` (linea 424-426) es
  lectura estatica pura. Necesita `XOpenDisplay` + GLX sobre la RX 550, o sea GPU. Su estado es
  `PROVEN` *por lectura* y `NOT_RUN` *en runtime* — dos etiquetas distintas, y solo la segunda
  impide tratarlo como medido. El mapa de la linea 3 de la tabla es el unico punto del alcance sin
  oraculo.
- **No demuestra que el codigo de salida de la linea B sea correcto en general.** Demuestra que lo
  es en los caminos que se han **forzado a correr**. Un camino que no se ha forzado no se ha
  medido, y enumerarlos todos no estaba al alcance.
- **No demuestra que los `.spv` / `.comp` / corpus sean correctos.** Solo que el *codigo de salida*
  responde a un artefacto corrupto. `test_compress` y `test_corpus_validate` podrian tener un
  fallo real que aqui no se ha buscado.
- **No demuestra que `MUT-A` modele fielmente un fallo de Vulkan real.** Modela *una* rama de
  fallo (`!ran_ok` al llegar a `cleanup`). Las otras —`CHK(vkCreateDevice,...)`, sin compute queue,
  sin identidad PCI, lectura del `.spv` incompleta (lineas 425-663)— comparten el mismo `goto
  cleanup` y el mismo `ran_ok=0`, asi que la extrapolacion es **razonada, no medida**.
- **No demuestra que el harness `h2.sh` sea el script real.** Es una reimplementacion *verbatim*
  de dos fragmentos. La semantica de `if !` esta medida contra bash real (§6); la estructura del
  bucle de texturas es una reconstruccion, no el fichero.
- **No dice nada de la suite de `07-DRIVER/tests`.** Fuera de alcance por briefing, y no se ha
  medido. Que `test_pm4` de 208 checks no se confunda con esta linea: son arboles distintos.
- **No cierra `LIMITACION #3` como "resuelta y correcta"**. La cierra como **CADUCADA** (§8). Que
  el codigo de hoy sea correcto no convierte en correcta la afirmacion de hace cuatro dias, ni
  cubre los caminos no forzados.

---

## 8 · Estado

| afirmacion | estado |
|---|---|
| «el test de la linea B imprime `[FAIL]` y devuelve `rc=0`» — hoy, en `test_decompress.c` | **REFUTED** (medido, §4) |
| la misma, hoy, en `test_compress.c` / `test_corpus_validate.c` | **REFUTED** (medido, §5) |
| la misma, hoy, en `test_hardware_bc3.c` | **PROVEN por lectura** (424→426), `NOT_RUN` en runtime |
| la misma, en el commit `b7ed0c1` que la afirmacion cita | **PROVEN** (el `return 0` incondicional estaba en `main`) |
| `LIMITACION #3` sigue vigente | **REFUTED / CADUCADA** — arreglada en `edd434b`, 6 min despues, conservada en `HEAD` |
| `integration_test.sh:219` lee mal el `rc` y su rama `SKIPPED` es muerte | **PROVEN** (medido, §6) |
| corregir `integration_test.sh:219` produciria verde falso | **PROVEN en el arnes** (rc 2 y 3 → EXIT 0). No verificado sobre el script real: haria falta una GPU o un `rx550_decompress` stub en el arbol, fuera de este nodo |
| el token `[FAIL]` sigue existiendo en `test_decompress.c` | **PROVEN_ABSENT en el codigo**; solo esta en el comentario de la linea 723 |

**LIMITACION #3 es, en su formulacion literal, CADUCADA.** Lo que hay que escribir no es «el fallo
sigue vivo» ni «esta arreglado»: es que la afirmacion era correcta a las 01:10 del 2026-09-29, se
corrigio a las 01:16, y el patron —`return` sin propagating— **volvio a escribirse** a las 01:23 en
otra funcion del mismo fichero, en `HEAD`, **sin** producir verde falso.

**Defecto vivo, distinto, y por tanto accionable por otro nodo:**
`integration_test.sh:219`. Caracterizacion, no reparacion: **no se ha tocado**. Su direccion es
opuesta (diagnostico falso, rama muerta), y su arreglo tiene un **efecto secundario peligroso** que
esta medido en §6.3 y que cualquiera que lo arregle deberia conocer antes.

---

## 9 · Alcance de hardware y herramienta reutilizable

`HARDWARE_SCOPE=NINGUNO`. La GPU no se ha enumerated, no se ha abierto, no se ha escrito. El
unico argumento de Vulkan en todo el nodo es `-lvulkan` en una linea de enlace.

El aparato de §3-§5 es reutilizable tal cual para cualquier test de la linea B: copiar el `.c` y
los `.o` a `/tmp`, mutar **el punto de disparo**, y leer `echo $?`. El patron que lo hace valido es
que **las tres piezas se compilan en el mismo directorio y se ejecutan con el mismo cwd**, de modo
que los artefactos que el test busca (`decompress_bc3.comp`, `.spv`) existen y Fase A pasa. Sin
eso, `main` sale antes por `phase_a_preparation` y uno mide otra cosa.

Regla que sale de aqui, y que es la que casi me costo el nodo: **en un archivo con dos funciones
que devuelven cosas con signo opuesto, el `return 0` no se lee, se mide.**
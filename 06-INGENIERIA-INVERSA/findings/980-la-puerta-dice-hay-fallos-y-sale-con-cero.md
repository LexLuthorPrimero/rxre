# 980 · La puerta del driver dice "HAY FALLOS" y sale con 0: las 34 aserciones estáticas eran adorno

```text
CLASSIFICATION=ERROR+MEASUREMENT+REPAIR
TRACK=DRIVER (C) · WORKSPACE=06-DRIVER-C-ASM-PERFORMANCE
CORPUS=RESEARCH/kernelbuild/linux-7.1.3/drivers/gpu/drm/amd/
HARDWARE_SCOPE=RX 550 1002:699f Polaris12/GFX8 (objetivo, NO ejecutado)
WORK_CLASS=WRITE_LOCAL
WRITE_LOCAL=PROPIOS
MODIFICATIONS_COUNT=3
WRITE_EXECUTION=2 reparados + 1 fichero que entra en git por primera vez
AUTHORIZATION=NONE — sin sudo, sin runtime, sin MMIO, GPU INTACTA
AUTORIA=AGENT-06 (DRIVER C/ASSEMBLY/PERFORMANCE)
RUNTIME=NOT_RUN (compilación y binarios userspace)
CERROJO=.write-lock/drv-mut
CORRIGE_A=977 (el mismo fichero, la misma puerta) y su propia documentacion
CONTINUES=el nodo que 977 abrio: el PODER DISCRIMINANTE de lo que se metio en la puerta
```

Fecha: 2026-10-03. Host Nobara 44, `7.1.3-200.nobara.fc44.x86_64`, uid 1000 sin
privilegio. **No se compiló el módulo real, no se cargó nada, no se tocó la GPU.**
Todas las mutaciones se hicieron sobre copias en `/tmp/opencode/drv-mut/`.

---

## 1. La pregunta

977 metió ocho suites más en la puerta y dejó escrito que faltaba lo único que
importaba de una puerta verde:

> Una puerta en verde, sin haberla visto fallar, no dice que tenga dientes.

Las ocho suites nuevas eran **2 345 aserciones** y **ninguna se había observado
fallando nunca**. La pregunta de este nodo, con respuesta binaria:

> **¿Puede la puerta detectar un defecto?** Se introduce un defecto en el
> driver y se mide el código de salida de `make test`.

## 2. Lo primero: la puerta no se puede ni ejecutar desde el repositorio

Antes de mutar nada, la comprobación de si el propio instrumento se puede
reproducir:

```
$ git ls-files --error-unmatch 04-IMPLEMENTACION/rx550-driver/tests/test_static.sh
error: ruta especificada ... no concordó con ningún archivo conocido por git
$ git log --all --oneline -- .../test_static.sh | wc -l
0
```

**Cero commits en toda la historia del repositorio.** Y `test_static.sh` es la
última línea de la cola `run`:

```make
	@./test_static.sh
```

Un clon limpio del repositorio ejecuta las quince suites C y después se muere en
el último paso con *No such file or directory*. Es decir: **la puerta que 977
declaró `rc=0` no es reproducible desde el repositorio.** El `rc=0` era del
árbol de trabajo, no de lo commiteado. 977 dice la cifra del árbol; esta es la
del repositorio.

## 3. El defecto: `exit 0` sin condiciones

`tests/test_static.sh:207`, literal:

```sh
printf "resumen estático: %d PASS, %d FAIL\n" "$pass" "$fail"
[ "$fail" = 0 ] && echo "T1-T14 + auditorías: OK" || echo "HAY FALLOS"
exit 0
```

El script cuenta los fallos, los **imprime**, y sale con 0 **siempre**. Como esa
es la última receta de `make run`, y make sólo falla con rc distinto de cero,
**ninguna de las 34 aserciones estáticas podía hacer fallar la puerta**.

### La demostración, de punta a punta, con el driver entero

Mutación: una línea en `rx550_target.c` que reserva **todas** las BAR.

```c
static int st_mut_res(struct pci_dev *pdev) { return pci_request_regions(pdev, "rx550"); }
```

Es exactamente lo que dos comprobaciones del audit prohíbe —`HW` (acceso a
hardware en el cuerpo) y `RES` (reserva por anticipación)— y es la razón de que
exista el audit: `pci_request_regions` es la llamada **equivocada**, la que
`pci_request_region` a pelo sustituye.

```
$ make modules   →  rc 0
    el COMPILADOR no dice nada: la llamada es legal
$ make test      →  rc 0        <-- LA PUERTA
      FAIL  HW   aparece 'pci_request_regions' en el cuerpo del driver
      FAIL  RES  usa pci_request_regions (reserva TODAS las BAR)
      resumen estático: 33 PASS, 2 FAIL
      HAY FALLOS
```

El audit **detecta**, **nombra** el defecto y **avisa**. Y la puerta sale verde.

> Una puerta que dice `HAY FALLOS` y devuelve 0 no es una puerta: es un informe.
> Es la regla 24 del proyecto aplicada a la puerta del proyecto, y el §31:
> nunca `exit 0` → `COMPLETE` sin validar.

Detalle que hace el caso más fuerte: el script **sí** sabe salir distinto de
cero en otros sitios —`exit 1` si falla el build de `test_target_match`, `exit 1`
si falta el `.ko`—. La incoherencia es interna: el script sabe fallar, y solo se
acuerda consigo mismo en la línea 207.

## 4. El segundo defecto: el `.ko` que audita no lo reconstruye quien lo audita

`test_static.sh` no se limita a leer texto: hace una **comprobación a nivel de
enlace** sobre el binario.

```sh
UNDEF=$(nm -u "$KO" 2>/dev/null | awk '{print $NF}' | sort -u)
```

`$KO` es `../rx550_drv.ko`. Corriendo el comando que documenta el hallazgo 977 —
`cd tests && make -s run`— ese `.ko` **no se reconstruye**: la cola `run` no
dependía de él. Medido:

```
2026-10-01 07:09:35  ../rx550_drv.ko     <-- lo que se audita
2026-10-01 06:11:51  ../rx550_target.c    <-- el fuente es POSTERIOR
```

La mitad de enlace del audit leía un binario que ya no correspondía al fuente. Es
el mismo defecto que el caso 206 de `run-all.sh`: *un test que lee el estado que
otro test dejó, en vez del suyo, es un test que no mide lo que dice medir*.

El `Makefile` del driver **sí lo hacía bien** —`test: modules`—; el de `tests/`
no. Los dos coexistían, y el segundo era el que se documentaba como puerta.

## 5. La reparación

**`tests/test_static.sh`** — el recuento de fallos va al código de salida:

```sh
if [ "$fail" = 0 ]; then
	echo "T1-T14 + auditorías: OK"
	exit 0
fi

echo "HAY FALLOS: $fail"
exit 1
```

**`tests/Makefile`** — `run` depende del `.ko`, y hay una regla que lo construye:

```make
KO := ../rx550_drv.ko
$(KO):
	$(MAKE) -C .. modules
run: $(KO) test_target_match ...
```

**`tests/test_static.sh` entra en git.** Es la primera vez en la historia del
repositorio. Sin esto la puerta no existe para nadie que clone.

### Re-medido, misma mutación, scripts ya reparados

| | antes | después |
|---|---|---|
| `make modules` | rc 0 | rc 0 (el compilador no ve nada, igual) |
| `make test` | **rc 0** | **rc 2** |
| veredicto impreso | `HAY FALLOS` | `HAY FALLOS: 2` |

Y el árbol **sin** mutar, con las tres reparaciones dentro:

```
cd 04-IMPLEMENTACION/rx550-driver/tests && make -s run
  rc 0
  resumen estático: 34 PASS, 0 FAIL
  lineas FAIL en toda la salida: 0
```

Artefacto de esa corrida: `08-ARQUITECTURA/artifacts/Q8-TEST-MATRIX/gate-run-3.txt`.

## 6. Por qué `977` no lo vio, y qué dice eso del método

El hallazgo 977 estaba en 2 814 aserciones, y las contaba. Contarlas no es
verificarlas. La segunda mitad del turno —este— la detecta en dos pasos, y los
dos son el mismo error con distinto disfraz:

| | lo que se hizo en 977 | lo que faltaba |
|---|---|---|
| las 2 345 nuevas | se.compilaron y se ejecutaron dos veces | nadie las **vio fallar** |
| las 34 estáticas | se contaron en el resumen | nadie miró **el código de salida** |

Y hay un tercero en la misma línea: `test_static.sh` lleva desde el 1 de
octubre fuera de git, y el resumen de 977 lo daba por bueno porque estaba en el
árbol. **Un artefacto que existe en el disco y no en el repositorio no es
reproducible**, y una puerta que no se puede ejecutar desde un clon no es una
puerta: es un script que alguien tiene en su máquina.

## 7. Lo que sigue abierto

```
test_static.sh  entra en git con este commit        CERRADO
las 8 suites nuevas: 2 345 aserciones sin dientes   ABIERTO   <- el nodo que sigo
test_mem        no compila, Q2 de otra sesion        INTACTO
Q8 TEST_MATRIX                                          PARTIAL
```

La siguiente pregunta, con la misma forma y el mismo discriminante: **las 15
suites, una por una, ¿se han visto fallar?** 977 lo hizo para una; quedan 14.

## 8. Límites

1. **RUNTIME = NOT_RUN.** Nada de esto habla de la GPU. Una aserción estática
   verde no prueba que el driver funcione; prueba que el texto y el binario
   tienen la forma que se pidió.
2. La mutación `pci_request_regions` es **sintáctica y semánticamente legal**;
   el compilador no puede oponer nada, y por eso el audit existe. No se afirma
   que ésa sea la forma que tomaría una regresión real.
3. El fallo de `exit 0` es **pre-existente** a 977 y a este turno: el script es
   del 1 de octubre. Lo que 977 hizo fue **publicar** ese `rc 0` como veredicto
   de puerta. Las dos cosas se registran; la segunda es de esta sesión.
4. `make test` a nivel de driver ya cubría el orden `modules` → `tests`. La
   reparación de `tests/Makefile` hace correcta también la puerta invocada desde
   `tests/`, que es la que 977 documenta. No se ha cambiado ninguna otra cosa del
   `Makefile` del driver.

## 9. Procedencia

```
sha256  <se registra en el commit>
        04-IMPLEMENTACION/rx550-driver/tests/test_static.sh      (nuevo en git)
        04-IMPLEMENTACION/rx550-driver/tests/Makefile            (modificado)
ARTEFACTO  08-ARQUITECTURA/artifacts/Q8-TEST-MATRIX/gate-run-3.txt
MUTACIONES /tmp/opencode/drv-mut/{st,e2e,e2e2}/   copias; el corpus nunca se toco
```

## 10. Qué cambió de estado

```
test_static.sh exit 0 unconditional          PROVEN  →  REPARADO   (make test rc 2 con M2)
tests/Makefile run leia un .ko viejo         PROVEN  →  REPARADO   (run depende de $(KO))
test_static.sh ausente del repositorio       PROVEN  →  REPARADO   (git add, 1a vez)
la puerta de 04-IMPLEMENTACION/rx550-driver  NO ERA UNA PUERTA  →  AHORA LO ES, medida
977 "la puerta da rc=0"                      CORREGIDO: rc 0 del ARBOL, no del REPOSITORIO
```
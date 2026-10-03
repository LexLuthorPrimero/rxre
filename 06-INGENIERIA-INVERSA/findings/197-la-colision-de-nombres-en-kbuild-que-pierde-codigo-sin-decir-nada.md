# 197 · La colisión de nombres en kbuild que pierde código sin decir nada

```
CLASSIFICATION=ERROR+MEASUREMENT+IMPLEMENTATION · TRACK=IMPLEMENTATION
CORPUS=RESEARCH/working/linux-7.1.3-headers · HARDWARE_SCOPE=NONE
WORK_CLASS=READ_ONLY/EVIDENCE+WRITE_LOCAL · WRITE_LOCAL=PROPIOS · MODIFICATIONS_CORPUS=0
RUNTIME=NOT_RUN · GPU INTACTA · CERROJOS=0
```

## Qué resuelve

Dos cosas que sólo se ven juntas.

La primera es un **modo de fallo de kbuild** que no produce ningún error: si un
módulo se declara compuesto y su propio `.o` está en la lista de miembros, el
`.c` de ese miembro **no se compila nunca**, el `.ko` se construye igual, el
código sale con estado 0 y dentro no está el código que se escribió.

La segunda es que ese fallo llegó a este proyecto, y lo que se vio primero fue un
mensaje que **señala otra cosa**:

```
ERROR: modpost: missing MODULE_LICENSE() in rx550_drv.o
```

`rx550_drv.c:455` tiene `MODULE_LICENSE("GPL")`. La licencia no faltaba: faltaba
el fichero entero dentro del módulo.

## 1 · La medición, y el denominador

```
kernel 7.1.3-200.nobara.fc44.x86_64   (uname -r)
dos ficheros triviales, /tmp/opencode/kbtest2

  forma                       simbolo del miembro   simbolo del otro   exit
  obj-m += modp.o                            2                 --         0
  obj-m := modp.o
  modp-objs := modp.o otro.o                 0                  2         0
```

La segunda fila es el fallo. El `.ko` se produce, `nm` lo confirma, y el símbolo
del fichero que colisiona **no está dentro**. El otro miembro sí. Y el build
termina con **código 0**.

Lo que hace falta para verlo es un símbolo distintivo en el fichero que colisiona.
Sin él, el resultado es indistinguible de un módulo pequeño.

## 2 · Por qué ocurre

El objeto que kbuild produce para el módulo se llama como el módulo. Si ese mismo
nombre está en la lista de miembros, el objetivo del `.c` y el objetivo del
enlazado **son el mismo fichero**, y `make` da por cumplido el enlace sin compilar
el `.c`.

La forma que lo evita es que el objeto con el nombre del módulo **nunca sea
miembro de sí mismo**. Y eso no es una regla inventada a partir de una mala
experiencia: es lo que hace el corpus entero, y se recalcula:

```
$ python3 tools/lint.py --censo

declaraciones de objeto compuesto en el corpus:   87
el .o del módulo NO es miembro:                   87
el .o del módulo SÍ es miembro:                    0
```

Y amdgpu lo dice con su propio nombre, que es donde se ve la diferencia:

```
amdgpu/Makefile:51    amdgpu-y := amdgpu_drv.o
```

El módulo se llama `amdgpu` y su primer objeto se llama `amdgpu_drv.o`. El
sufijo `_drv` va en el **módulo** allí y en el **fichero** aquí, y los dos evitan
la misma colisión.

### CORRECCION: lo que este hallazgo decía de memoria

La primera versión de este §2 afirmaba:

```
i915_core.o    no i915.o
amdgpu_kms.o   no amdgpu.o
```

Las dos parejas venían de memoria, sin un solo fichero del proyecto que las
sostuviera, y **la segunda era incorrecta**: lo que amdgpu evita no es
`amdgpu_kms.o`, es `amdgpu.o`. El mismo error llegó al comentario de
`07-DRIVER/kernel/Makefile`, que además afirmaba que la forma `rx550_drv-y` era
**incorrecta**. No lo es: `-y` es la forma que usa amdgpu en la línea 51 de su
Makefile, y el fallo que se produjo nunca fue de forma sino de nombres.

Un diagnóstico atribuido a la sintaxis cuando la causa es otra cosa deja el
síntoma volver en cuanto se corrige lo que no era. Y un criterio necesita su
fuente, no un recuerdo.

Aquí no se puede renombrar `rx550_drv.c` → `rx550_pci.c`, porque **cinco
referencias en tres hallazgos inmutables** citan `rx550_drv.c:N` (`114:130`,
`114:183`, `171:22`, `171:136`, `189:130`) y los hallazgos no se reescriben. Un
fichero renombrado rompe citas que por regla ya no se pueden arreglar. El coste
de renombrar es mayor que el beneficio, y la decisión queda escrita en
`07-DRIVER/kernel/Makefile`.

Así que `rx550_mmio.c` entra por `#include` desde `rx550_drv.c`. Consecuencia
honesta: se compila dos veces, una en el módulo y otra en
`07-DRIVER/tests/test_mmio.c`, y son dos binarios distintos, así que no hay
conflicto.

## 3 · Lo que el síntoma despedía: `pci_iomap` no es lo que se creía

Al arreglar la compilación apareció un error real:

```
rx550_drv.c:372:41: error: too few arguments to function 'pci_iomap'; expected 3, have 2
```

La firma, **PROVEN** en este kernel:

```
include/asm-generic/pci_iomap.h:13
void __iomem *pci_iomap(struct pci_dev *dev, int bar, unsigned long max);
```

```
CITA=pci_iomap.h | TERMINO=unsigned long max
    | ROL=el tercer argumento es una LONGITUD, no un tipo de BAR
```

Esto **cambia una afirmación de `237` §3**, que decía que las constantes
`PCI_BARn_*` del núcleo no estaban en ningún corpus y que el mapa se haría a
ciegas. La función no pide un tipo: pide **cuánta longitud** se quiere mapear.

Y se pasa `RX550_MMIO_LEN` (2 MiB, medido por `237` con `stat()` sin root) por una
razón que no depende de lo que el cuerpo haga con el parámetro: **la longitud que
se pide y la que hay coinciden**, así que comparen, las recorten o la ignoren, el
resultado es el mismo.

```
LO QUE SIGUE NOT_IN_CORPUS
  el cuerpo de pci_iomap(). /usr/src/kernels/ trae solo cabeceras y el árbol
  7.2.8 del proyecto solo trae drivers/. No hay ningún .c en disco.
  Por eso NO se afirma qué hace con `max`: solo qué se le pasa.
```

## 4 · Lo que sí se implementó: el contrato de la ventana

`rx550_mmio.c` / `.h` / `tests/test_mmio.c`. La lógica del contrato es **C puro**
a propósito, para que su aritmética se compruebe en userspace sin hardware; la
llamada a `pci_iomap` se queda en `rx550_drv.c`, que sí depende del núcleo.

```
26 checks, 0 failures
```

Lo que establece:

```
RX550_MMIO_LEN == 2 MiB                       findings/176, medido con stat()
los 8 offsets caben en la ventana             findings/180, uno a uno
el ultimo byte esta DENTRO, el siguiente FUERA  el limite, no un margen
un offset con el bit 31 no pasa por "negativo" los dos son __u32
```

Lo que establece y **no debería**:

```
geometria correcta  ->  RX550_MMIO_NO_VERIFICADA, NO se mapea
```

`RX550_MMIO_BAR` sigue siendo **DECLARADO y no derivado**: `237` §3 clasifica
NOT_IN_CORPUS qué bloque de registros vive en qué BAR. La rama
`if (rx->mmio.motivo == RX550_MMIO_OK)` en el probe es **inalcanzable a
propósito**, y está escrita para que cerrarlo sea cambiar una línea.

Un `pci_iomap()` incondicional sería heredar de un argumento el mismo
NOT_IN_CORPUS, pero con permisos de escritura.

Dientes, mutate sobre copia:

| mutación | checks que fallan |
|---|---|
| `RX550_MMIO_LEN` 2 MiB → 256 MiB | 2 |
| `offset_ok` pasa por `<=` en vez de `<` | 1 |

## 5 · Dos controles que hubo que rehacer porque mentían

**El grado `INVOCA` de `drvchain.py`.** `MMIO` e `init` no se implementan
definiendo una función propia sino **llamando** al núcleo. `definido()` busca
definiciones, así que esos dos eslabones no podían subir de `NOMBRADO` nunca, lo
que se lee como «el driver no hace esto» cuando sí lo hace:

```
antes   19 eslabones: PROBADO 3, IMPLEMENTADO 1, NOMBRADO 5, AUSENTE 10
ahora   19 eslabones: PROBADO 3, IMPLEMENTADO 1, INVOCA 2, NOMBRADO 3, AUSENTE 10

  con cuerpo propio:      4 de 19   (21%)
  llamando al kernel:     2 de 19   (11%)
  los dos juntos:         6 de 19   (32%)
```

**El check negativo `la etapa 1 NO mapea MMIO`.** Falló en cuanto el mapeo llegó,
que es justo cuando el trabajo avanzó. Un check negativo que se vuelve falso
cuando el avance ocurre no custodiaba nada: custodiaba el estado viejo. Lo
sustituyen dos más fuertes, por **orden de línea**, que es falsable:

```
== el mapeo de MMIO va DETRAS del contrato, no al reves ==
  OK  rx550_drv.ko: valida en linea 159 y mapea en linea 166
  OK  rx550_mmio_valida / offset_ok / motivo presentes en rx550_drv.ko
```

Tres direcciones comprobadas: el árbol real pasa; una copia con el mapa antes de
validar **falla**; una copia con comentarios que nombran las dos llamadas **no**
falla.

## 6 · El fallo seiautomatizó

`lint.py` incorpora tres clases, con el lado estático separado del lado del
artefacto porque cada uno ve algo que el otro no:

```
KBUILD_COLISION             texto: el .o del módulo está en sus propios -objs
KBUILD_SIN_OBJETO           artefacto: el .ko existe y uno de sus .o no
KBUILD_MIEMBRO_INEXISTENTE  artefacto: un -objs declara un .o sin .c detrás
```

Sobre el árbol real: **0 filas**. Sobre una copia del Makefile real con la
colisión reintroducida: **1 fila**, en la línea correcta.

```
16 -> 30 vectores
```

Cuatro de los catorce vectores nuevos no son del clasificador sino del **censo**,
y uno de ellos comprueba que un corpus ausente devuelve `(0, 0, 0, [])` en vez de
un censo de cero: entrada que falta no es un resultado.

### El error 17 es el más instructivo de todos

`KBUILD_COLISION` buscaba `(\w+)-objs :=` y ya. La forma `-y` —**la que usa
amdgpu**, y la primera que se escribió en este proyecto — pasaba sin detectar. Y
el censo, que sí usaba la regex correcta, contaba 87 declaraciones sin que nada
fallara: un criterio contradiciéndose a sí mismo en el mismo fichero, a treinta
líneas de distancia, y ningún vector lo cazaba porque todos los anteriores
usaban `-objs`.

```
$ python3 -c "lint.escanear_kbuild('M','obj-m := a.o\na-y := a.o b.o\n')"

  -objs -> 1 fila(s)  KBUILD_COLISION
  -y    -> 0 fila(s)  NO DETECTADA     <-- antes de corregir
```

Un criterio de clasificación tiene que ser una convención **verificada contra el
binario**, no una frase en un comentario. Y tiene que probarse en **las dos**
formas que existen, o no está probado.

Un vector que se pasó por el motivo equivocado, y que por eso es el más útil de
los diez: esperaba **un** `KBUILD_SIN_OBJETO` donde la colisión real deja sin
compilar **todos** los miembros, o sea **dos**. El vector estaba mal, no la regla.

## 7 · Errores propios de esta ronda

Dieciséis, y la mayoría son el mismo hallazgo repetido: **una afirmación escrita
sin comprobarla**. Los dos últimos son los más caros, porque los dosfallen en
código y en el hallazgo, que es donde un error se propaga solo.

| # | error | quién lo cazó |
|---|---|---|
| 1 | `u8`/`u32` en la cabecera nueva, violando la regla de `rx550_pm4.h:18-20` | el compilador |
| 2 | etiqueta `memset_ok:` muerta, sin sentencia detrás | el compilador |
| 3 | `rx550_drv-y` en vez de `-objs`, forma de kbuild inexistente | modpost |
| 4 | `git checkout` sobre el Makefile: destruidas ~76 líneas sin commitear | `wc -l` contra HEAD |
| 5 | `pci_iomap` con dos argumentos | el compilador |
| 6 | un ideograma colado en el Makefile escrito por mí | `lint.py` |
| 7 | `invocado()`/`es_declaracion()` mal: `;` no distingue prototipo de llamada | el selftest |
| 8 | vector de `drvchain` que decía «solo en comentario» y plantaba también una llamada | el selftest |
| 9 | `KBUILD_MIEMBRO_INEXISTENTE` afirmaba la falta de un `.c` **sin mirar el disco** | el vector de árbol sano |
| 10 | el check de `check-drivers` disparado por su propio comentario | él mismo |
| 11 | su arreglo no cubría `/*` de una línea: **falso dos veces** | la copia con comentarios |
| 12 | `sed` multilínea en una receta: `@#` llega al shell y rompe la sintaxis | el shell |
| 13 | bloque de comentario duplicado por dos ediciones apiladas | la lectura del fichero |
| 14 | resumen de `drvchain` que ya no describía la tabla | la lectura de la tabla |
| 15 | la convención de upstream citada **de memoria** en el hallazgo | `--censo`: 87 de 87 |
| 16 | la misma convención, y deformada, escrita en el **Makefile** | `--censo` y `amdgpu/Makefile:51` |
| 17 | `KBUILD_COLISION` no entendía `-y`, solo `-objs`: la colisión en la forma de amdgpu pasaba **sin detectar** | un vector con `-y` |

El 4 es el que más cuesta: `git checkout` no es reversible para trabajo sin
commitear, y la costumbre de «volver al original para comparar» es exactamente la
que lo dispara. La recuperación vino de una copia en `/tmp` tomada **antes** del
cambio, no de git.

## 8 · Lo que NO se establece

```
  el bloque de registros vive en el BAR 2      NOT_IN_CORPUS  (176 §3)
  qué hace pci_iomap() con `max`               NOT_IN_CORPUS  (sin .c en disco)
  que los 8 offsets apunten a lo que dicen     PROVEN, pero por 180, no aqui
  que escribir en la ventana tenga efecto      NO MEDIDO: no hay hardware
  que el modulo cargue                         BLOCKED_BY_AUTHORIZATION
```

`26 checks` sobre geometría no autorizan un `insmod`. El módulo
`rx550_drv.ko` (419.016 B, `vermagic` exacto) construye y se queda en disco;
cargarlo es NIVEL 4 y sigue sin autorización.

## 9 · Trazabilidad

```
  07-DRIVER/kernel/rx550_mmio.h      contrato, con RX550_MMIO_BAR marcado
  07-DRIVER/kernel/rx550_mmio.c      aritmética, C puro
  07-DRIVER/kernel/rx550_drv.c       include + rama inalcanzable a propósito
  07-DRIVER/kernel/Makefile          la no colisión, con el motivo
  07-DRIVER/tests/test_mmio.c        26 checks
  tools/lint.py                      3 clases kbuild + --censo, 29 vectores
  tools/drvchain.py                  grado INVOCA, 14 vectores
  /tmp/opencode/kbtest2/             el reproductor de dos ficheros
```
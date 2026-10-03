# 304 · La regla de seguridad, probada: funciona, y por eso mismo prohíbe el banco de medidas

```text
CLASSIFICATION=MEASUREMENT+CONTRADICTION+ERROR · TRACK=TOOLING
CORPUS=NINGUNO (el proyecto) · HARDWARE_SCOPE=NONE
WORK_CLASS=READ_ONLY/EVIDENCE+WRITE_LOCAL · WRITE_LOCAL=PROPIOS · MODIFICATIONS_CORPUS=0
RUNTIME=NOT_RUN · GPU INTACTA · CERROJOS=0
PROVOCACIONES=3 · CREADAS Y BORRADAS · ESTADO FINAL COMPROBADO
```

## Qué resuelve

El `NEXT_ACTION` de `303` era provocar el validador de contratos, porque su regla
se creía pero no se había probado nunca. Es el mismo `294` y el mismo `300`: un
control escrito no es un control.

**Se ha provocado. Y sale distinto de lo previsto en las dos direcciones.**

## 1 · La provocación: tres ficheros, tres formatos de fallo

```text
  1  _selftest_prov_gpu.py        # CONTRACT: WRITES_GPU=yes
  2  _selftest_prov_sysfs.py      # CONTRACT: WRITES_SYSFS=yes, sin tabla, sin --write
  3  _selftest_prov_docstring.py  el MISMO WRITES_GPU=yes, dentro del docstring y
                                  sin `#`, que es el formato de las 29 de revkit
```

Sin leer la regla antes, porque si la leo sé qué buscar y dejo de medir.

```text
  _selftest_prov_gpu.py:        DECLARA WRITES_GPU: inaceptable en esta caja
  _selftest_prov_sysfs.py:      WRITES_SYSFS sin TABLA de escrituras
  _selftest_prov_sysfs.py:      WRITES_SYSFS sin bandera --write: no hay barrera
  _selftest_prov_docstring.py:  SIN CONTRATO: no se puede afirmar nada de esta herramienta
  rc por defecto = 1        rc --strict = 1
```

Las tres cazadas, y la tercera con la respuesta que separates los dos fallos de
`303`:

```text
  provocacion 3, en un directorio que el validador SI mira,
  con WRITES_GPU=yes igual que la provocacion 1
      -> "SIN CONTRATO"
      -> el parser NO lee el formato de revkit, ni estando en el sitio correcto
```

Así que los dos fallos de `303` son **independientes**: no basta con arreglar el
alcance del directorio, el parser también.

Y la provocación 1 es la respuesta a lo que `303` dejó abierto:

```text
  303  "si el validador acepta WRITES_GPU=yes, la regla es FALSA"
  304  NO LO ACEPTA. La regla FUNCIONA
```

**La parte de `303` que decía que el validador fallaría está DESMENTIDA por
medición.** El problema no es que el control no funcione.

## 2 · Y el problema es el contrario: estaba en rojo antes de tocar nada

Quitadas las tres provocaciones, `toolkit --strict` sigue devolviendo **rc=1**, con
19 problemas distintos en 15 herramientas:

```text
  1 x  DECLARA WRITES_GPU           bench
  5 x  SIN CONTRATO                 causal, citecheck, contradict, scopeguard, xref
 13 x  FLAG DESCONOCIDO             tres familias, abajo
```

```text
  UN CONTROL QUE ESTA EN ROJO PERMANENTE NO ES UN CONTROL
  ES UNA ALARMA QUE NADIE HA ESCUCHADO
```

Y el validador **sí dice su alcance**: `herramientas en .../08-ARQUITECTURA/tools:
60`. Eso es honesto, y es lo que `303` ya habia dicho.

## 3 · Y los 13 «flags desconocidos» son tres familias enteras

```text
  WRITES_GPU_MMIO    bench, fronteras, huella              3 herramientas
  WRITES_GPU_WORK    bench, fronteras, huella              3 herramientas
  EXIT_ON_SUCCESS    check_chain, cite_registry,
                     commitmsg_lint, contract_exec,
                     contract_filter, exit_contract,
                     toolkit_cross                         7 herramientas
```

Tres banderas que **13 herramientas de las 60 que el validador SÍ ve** declaran, y
que el validador no sabe interpretar. Es decir: el vocabulario de la caja ha
crecido y el validador no le ha seguido.

## 4 · Y aquí está la contradicción, y es grave

`bench.py` declara:

```text
  08-ARQUITECTURA/tools/bench.py:11   # CONTRACT: WRITES_GPU=yes
  08-ARQUITECTURA/tools/bench.py:18   # CONTRACT: WRITES_GPU_MMIO=no
  08-ARQUITECTURA/tools/bench.py:19   # CONTRACT: WRITES_GPU_WORK=yes
```

Y explica en su propio docstring, líneas 13 a 26, por qué:

```text
  La capacidad WRITES_GPU dice DOS cosas distintas y este banco cae en las dos, asi que
  se declara por separado lo que significa cada una. [...] No es falsa: es ambigua.

  WRITES_GPU_MMIO=no    no toca ningun registro. Todo lo que hace es vkQueueSubmit.
  WRITES_GPU_WORK=yes   envia trabajo que hace que la GPU escriba en VRAM: los shaders
                        escriben en d[WSIZE + i] y el host lo ve al releer. Eso es
                        escribir en la GPU, y por eso WRITES_GPU=no seria falso.

  La distincion importa: una herramienta que declare WRITES_GPU=no y en realidad envie
  trabajo esta mintiendo en la direccion contraria. El banco declara lo que hace.
```

### La afirmación de `bench.py` se sostiene en el fuente

```text
  carga y ejecuta trabajo de GPU
    vulkan_compute_probe.c                      compila y lo lanza
    lane.spv, chain.spv, texchain.spv           shaders que escriben en un buffer
    vkQueueSubmit                               el submit, citado por el propio bench

  NO toca ningun registro
    /dev/mem      0 apariciones
    __iomem       0 apariciones
    ioremap/writel/readl/REG_  0 apariciones
    el unico acierto de "mmio" es su propio comentario diciendo que lo busco y no
    lo encontre
```

### Y la regla, leída, dice lo contrario

`toolkit.py:38-41`:

```text
  Una herramienta que diga WRITES_GPU no puede existir en la caja. Si aparece, el
  validador falla. No es una advertencia: una herramienta que escribe en la GPU sin
  hardware de prueba no puede distinguir un bug del driver de un bug del hardware, y
  el daño es irreversible.
```

```text
  LA REGLA PROHIBE bench.py
  Y bench.py TIENE RAZON
  Y LAS DOS COSAS NO PUEDEN SER CIERTAS A LA VEZ

  un banco de medidas que envia trabajo a la GPU NO PUEDE declarar con honestidad
  que no escribe en la GPU
  y un validador que rechaza WRITES_GPU=yes PROHIBE EL BANCO DE MEDIDAS
  que es §51 a §57, que es el objetivo declarado del proyecto
```

Y el problema no es solo de `bench.py`:

```text
  fronteras.py   WRITES_GPU_MMIO=no   WRITES_GPU_WORK=no
  huella.py      WRITES_GPU_MMIO=no   WRITES_GPU_WORK=no

  esas dos NO declaran WRITES_GPU, y el validador las marca igual por usar las
  banderas nuevas. O sea que hay herramientas que han RESUELTO el problema y son
  penalizadas por haverlo hecho con un vocabulario que el validador no conoce
```

## 5 · La forma de la contradicción

```text
  el validador     WRITES_GPU=yes  ->  inaceptable, sin matiz
  bench.py         WRITES_GPU=yes  ->  pero ambigua, y aqui esta el desglose
  fronteras.py     sin WRITES_GPU  ->  y aqui esta el desglose tambien

  las tres son internamente coherentes
  y son mutuamente insatisfacibles
```

Y hay un tercer lado que **no se ha mirado**, y que es el que decide:

```text
  ¿ES SEGURO EN ESTA MAQUINA ENVIAR TRABAJO DE COMPUTE A LA RX550
  SIN HARDWARE DE PRUEBA Y SIN PODER DISTINGIR UN BUG DEL DRIVER DE UN BUG
  DEL HARDWARE?
```

El validador dice que no se puede. `bench.py` no lo discute: dice que **toca
registros**, que no toca. Son dos cosas distintas, y `WRITES_GPU_MMIO` existe
precisamente para separarlas. Pero **nadie ha medido el riesgo de la segunda**, que
es la que el banco corre.

## 6 · Lo que NO se establece

```text
  si enviar trabajo de compute a esta RX550 puede colgarla
    NO MEDIDO, y es la pregunta que decide la contradiccion. `bench.py` existe y
    presumably se ha ejecutado, pero no hay en este hallazgo ni una medicion de
    estabilidad del banco, ni una relacion de fallos por tipo. La afirmacion
    "es seguro" NO ESTA SOSTENIDA por nada que yo haya medido
  si las 5 herramientas SIN CONTRATO estan bien o mal
    SIN LEER. Ninguna. Un "SIN CONTRATO" no dice si la herramienta es peligrosa,
    dice que no se puede afirmar nada de ella, que es distinto y menos grave
  si EXIT_ON_SUCCESS deberia ser una capacidad del contrato
    NO DECIDIDO. 7 herramientas la declaran y hay una herramienta(`exit_contract.py`)
    que parece existir justo para ESO. O sea que el vocabulario ya tiene dueño y el
    validador no lo sabe. No se ha leido `exit_contract.py`
  el significado de las 91 herramientas de `303` que el validador no ve
    SIN CAMBIAR. Este hallazgo no lo toca: solo confirma que el problema del
    alcance es real Y ADEMAS hay un problema de vocabulario dentro del alcance
  si el estado rojo de `toolkit --strict` es conocido
    NO SE HA PREGUNTADO. Puede que sea deliberado y documentado en otra parte. Lo
    que es MEDIDO es que rc=1 y que nadie ha actuado sobre ello en lo que se ve
```

## 7 · Trazabilidad

```text
  provocaciones   08-ARQUITECTURA/tools/_selftest_prov_{gpu,sysfs,docstring}.py
                  CREADAS, EJECUTADAS, Y BORRADAS. Comprobado que solo quedan
                  los dos _selftest_ que ya estaban
  08-ARQUITECTURA/tools/toolkit.py:38-41   la regla, en su propio docstring
  08-ARQUITECTURA/tools/bench.py:11,18,19   las tres claves que se contradicen
  08-ARQUITECTURA/tools/bench.py:13-26      por que esta partida, y por que
  /tmp/opencode/tk_prov.txt                 la salida CON provocaciones
  /tmp/opencode/tk_base.txt                 la salida SIN ellas, con 19 problemas
  findings/303 §5                           lo que aqui se desmente
```

## 8 · Corrección y confirmación

```text
  este fichero se escribio como 304, reservado con --reservar antes de escribir
  CORRECTED_BY: --reservar 304  RESERVADO

  CORRIGE A findings/303 §5
    "si el validador fallaria si una de las 60 escribiera en la GPU   NO COMPROBADO"
    -> MEDIDO. Y el veredicto es el contrario del que se temia: NO falla.
    La regla de §38-41 FUNCIONA. El problema es el alcance (303) y el
    vocabulario (este fichero), no la regla

  Y ABRE UNA CONTRADICCION NUEVA, que no estaba registrada
    la regla de §38-41 y el contrato de bench.py:11 son incompatibles, y el
    documento que manda (§51-§57, medir para encontrar el maximo practico) esta
    del lado de bench.py
```

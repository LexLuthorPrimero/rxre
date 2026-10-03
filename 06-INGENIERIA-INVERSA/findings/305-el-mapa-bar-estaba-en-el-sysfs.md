# 305 · El mapa BAR estaba en el sysfs, y dos bugs de parseo lo dejaron null 59 veces

```text
CLASSIFICATION=MEASUREMENT+ERROR+DERIVATION · TRACK=HARDWARE
CORPUS=NINGUNO (el proyecto) · HARDWARE_SCOPE=ESTE TARGET, ESTA GPU, ESTE BDF
WORK_CLASS=READ_ONLY/EVIDENCE · MODIFICATIONS_CORPUS=0
RUNTIME=NOT_RUN · GPU INTACTA · CERROJOS=0 · MODULO PROPIO NO CARGADO
```

## Qué resuelve

El `NEXT_ACTION` de `304` era una pregunta binaria sobre la contradicción de la
regla de seguridad: **¿existe un directorio de resultados del banco, con
historial?**

Sí. Y al mirarlo han salido dos bugs que dejaron `pci`, `pci_device` y `bar_size`
a `null` en las 59 ejecuciones, **y el dato que eso ocultaba está confirmado ahora
desde el sysfs, sin corpus y sin journal de arranque.**

## 1 · La pregunta binaria: sí hay historial

```text
  08-ARQUITECTURA/validations/   59 ficheros bench-*.json + 5 mas
  instrumento.binario            vcp, en las 59
  instrumento.fuente_sha256      registrado
  veredicto global               PASS 50   INVALID 9
```

| suite | ficheros | PASS | INVALID |
|---|---|---|---|
| selftest | 34 | 34 | 0 |
| regresion | 11 | 9 | 2 |
| jerarquia | 6 | 5 | 1 |
| textura | 5 | **0** | **5** |
| coalescencia | 2 | 1 | 1 |
| curva | 1 | 1 | 0 |

`WRITES_GPU_WORK=yes` tiene detrás 59 ejecuciones de un binario Vulkan sobre esta
máquina. **La afirmación de `bench.py` no es una promesa, es un histórico.**

Y una observación que no es un fallo: **`textura` no ha pasado nunca**, 5 de 5
INVALID con `fallos: ['.par=INVALID', '.par.imagen_r32ui=INVALID']`. Que `INVALID`
signifique «esta medición no cuenta» y no «la GPU se colgó» es la definición del
propio banco (`bench.py:52`, `:67`).

## 2 · Y los 59 no dicen contra qué GPU se midió

```text
  campo          con valor   null    distintos
  bar_size             0      59          0
  pci                  0      59          0
  pci_device           0      59          0
  kernel              59       0          1
  mclk_hz             59       0          3
  power_uw            59       0         59
  sclk_hz             59       0         35
  temp_mc             59       0         16
```

Tres campos **nulos en las 59**, y son exactamente los tres de identidad. Los
sensores tienen valor y varían. Y buscando la identidad por el artefacto entero:

```text
  1002:163f   0 artefactos      Polaris12     0 artefactos
  67df        0 artefactos      vendor_id     0 artefactos
  device_id   0 artefactos      rev_id        0 artefactos
  RX550       59 artefactos   <-- pero esto es el NOMBRE DE LA CARPETA en las rutas
```

**Lo que la capa de comparabilidad no esconde:**

```text
  bar_size     {"ahora": null, "anterior": null, "estado": "NO_COMPARABLE"}
  pcie_gen     {"ahora": null, "anterior": null, "estado": "NO_COMPARABLE"}
  pcie_width   {"ahora": null, "anterior": null, "estado": "NO_COMPARABLE"}
  mclk_hz      {"ahora": 300000000, "anterior": 300000000, "estado": "igual"}
  sclk_hz      {"ahora": 1062820000, "anterior": 1037830000, "estado": "igual"}
  estado global: COMPARABLE
```

El banco dice «estos tres campos no se pueden comparar» y aun así dice «la
medición es comparable», porque compara lo de rendimiento por un lado y lo de
identidad por otro. **Eso está bien hecho.** Lo que falta es el dato de identidad.

Y hay un defecto de estructura: **`pcie_gen` y `pcie_width` son comparables
declarados (`bench.py:1025`) y no existen en `hardware`.** Su `NO_COMPARABLE` es
permanente por construcción.

## 3 · Los dos bugs, y los dos son de una línea

### Bug 1 · `leer_int` no sabe leer hexadecimal

```python
  bench.py:117   def leer_int(path):
  bench.py:120           return int(f.read().strip())      # sin base
  bench.py:121       except Exception:
  bench.py:122           return None

  bench.py:130   d["pci"]        = leer_int("/sys/class/drm/card1/device/vendor")
  bench.py:131   d["pci_device"] = leer_int("/sys/class/drm/card1/device/device")
```

El fichero **existe, se lee, y contiene `0x1002`**. `int("0x1002")` es
`ValueError`, y el `except Exception` se lo come.

Probado sobre los ficheros vivos, ahora:

```text
  leer_int('/sys/class/drm/card1/device/vendor')   -> None
  leer_int('/sys/class/drm/card1/device/device')  -> None
  int(open(p).read().strip(), 16)                 -> 4098      (= 0x1002 = AMD)
```

Y por qué los otros cinco campos sí tienen valor: **`freq1_input`,
`freq2_input`, `power1_input` y `temp1_input` son decimales**, y `int("4098")` no
falla. Solo los dos campos PCI son hex, y solo esos dos son `null`. El patrón lo
explica sin necesidad de hipótesis.

### Bug 2 · `bar_size` parsea seis líneas como un entero

```python
  bench.py:138       with open("/sys/class/drm/card1/device/resource") as f:
  bench.py:139           d["bar_size"] = int(f.read().strip(), 16)
  bench.py:140       except Exception:
  bench.py:141           pass
```

El fichero existe, `open()` funciona, y contiene **13 líneas con tres tokens
hexadecimales cada una**: inicio, fin, flags, uno por BAR. `int()` de ese texto
es `ValueError`, y `pass` lo traga.

## 4 · Y el dato que estaba detrás, leído bien

```text
  BAR                inicio                fin               tamano  flags
  BAR0   0x00000000e0000000 0x00000000efffffff       268435456  PREF,64BIT
  BAR2   0x00000000f0000000 0x00000000f01fffff         2097152  PREF,64BIT
  BAR4   0x000000000000e000 0x000000000000e0ff             256  IO
  BAR5   0x00000000f7d00000 0x00000000f7d3ffff          262144  -
  BAR6   0x00000000000c0000 0x00000000000dffff          131072  MEM,HOST
```

**BAR5 son 262 144 bytes exactos. 256 KiB.** Y el driver usa
`RX550_MMIO_BAR=5` con una ventana de 256 KiB.

### Contraste independiente, y funciona sin root

Los nodos `resourceN` son `rw-------` de root, así que `cat` está denegado. Pero
**`os.stat()` no necesita abrirlos**:

```text
  BAR           bytes            KiB   legible?
  BAR0      268435456         262144   NO (PermissionError)
  BAR2       2097152          2048   NO (PermissionError)
  BAR4           256             0   NO (PermissionError)
  BAR5         262144           256   NO (PermissionError)
```

Dos fuentes independientes, sin corpus y sin permisos:

```text
  resource (agregado, fin - inicio + 1)   BAR5 = 262144
  os.stat(resource5).st_size               BAR5 = 262144
  COINCIDEN
```

Y el dispositivo, por `readlink`:

```text
  /sys/class/drm/card1/device -> 0000:01:00.0
  lspci -nn  ->  01:00.0 VGA: Advanced Micro Devices, Inc. Lexa PRO [Radeon RX 550]
  fingerprint.py  ->  gpu_id 1002:699f COINCIDE · gpu_nombre Lexa PRO COINCIDE
                      asic POLARIS12 COINCIDE · vram 2048 MiB
```

Lexa PRO **es** Polaris12. Y el BDF es `0000:01:00.0`, que es el que ya usa el
proyecto.

## 5 · Y por qué esto no estaba disponible antes

```text
  fingerprint.py:321   ("bar_registro", "journalctl (artefacto)", c_bar, "262144 bytes")
```

**La huella del proyecto ya afirmaba `262144 bytes`, pero lo sacaba del journal de
arranque.** Es decir: el mismo hecho que se podía leer del sysfs sin privilegios
estaba siendo tomado de un artefacto de boot, que es un archivo de texto que hay
que parsear y que depende de que el boot haya ocurrido.

```text
  UN HECHO DISPONIBLE EN EL SYSFS, SIN PERMISOS, NO DEBERIA ESTAR SALIENDO
  DE UN ARTEFACTO DE BOOT QUE HAY QUE PARSEAR
  Y CUANDO HAY DOS CAMINOS, EL DEGRADADO SE USA Y EL BUENO SE DESCUBRE SOLO
  CUANDO ALGO SE ROMPE
```

Y lo que rompió fue que `bench.py` intentara leerlo por su cuenta y fallara.

## 6 · Lo que NO se establece

```text
  si la ventana BAR5 esta HABILITADA de memoria en el config space
    NOT_DETERMINED, y hay un dato que no encaja: en el fichero `resource` los
    flags de BAR5 son 0, mientras que BAR0 y BAR2 son PREF,64BIT. Eso puede
    querer decir que la BAR esta asignada pero no habilitada, o que el kernel
    expone el campo de otra manera. La respuesta esta en el registro de comando
    del config space, que no se ha leido
  si en BAR5 esta `mmMC_VM_FB_LOCATION` (0x809) y `mmCONFIG_MEMSIZE` (0x150a)
    NO. Eso necesita la ventana mapeada, que necesita el driver cargado, que
    sigue en BLOCKED_BY_AUTHORIZATION. Lo que este hallazgo cierra es la
    IDENTIDAD y el TAMANO de la ventana, que es lo que faltaba para saber a
    donde mirar. Las predicciones falsables (0xF400, 0x800) siguen sin poder
    comprobarse
  si el banco es SEGURO para esta tarjeta
    PARCIAL. 59 ejecuciones y un 15 % INVALID es un dato, pero INVALID es la
    sinonimo de "esta medicion no cuenta" segun el propio banco, no de fallo de
    hardware. NO HAY NINGUN REGISTRO DE ESTABILIDAD: ni caidas, ni timeouts, ni
    dmesg. Lo unico que hay son 59 artefactos con veredicto
  si los 9 INVALID son el mismo fallo
    NO AGRUPADOS. `fallos` son CADENAS, no registros estructurados, y el
    agregado por tipo no se puede hacer. Es un limite del formato
  si `bar_size` deberia ser un numero o una lista
    NO DECIDIDO. Ahora mismo hay un campo para seis BARs y un entero. El nombre
    es singular y el fichero es plural: eso tambien es un defecto de contrato
```

## 7 · Trazabilidad

```text
  08-ARQUITECTURA/validations/           59 artefactos, el historico
  08-ARQUITECTURA/tools/bench.py:117-122 leer_int, el bug 1
  08-ARQUITECTURA/tools/bench.py:136-141 bar_size, el bug 2
  08-ARQUITECTURA/tools/bench.py:1025    COMPARABLES, con dos que no existen
  08-ARQUITECTURA/tools/bench.py:130-131 las dos rutas que devuelven None
  tools/fingerprint.py:321               bar_registro, que sale del journal
  /sys/class/drm/card1/device/resource   el mapa BAR, legible
  /sys/class/drm/card1/device/resource5  el tamano, por stat sin root
  /tmp/opencode/barmap.py                el parseo correcto
```

## 8 · CORRECCION: los flags de BAR5 no son 0, y la columna entera es ilegible

Este hallazgo se escribió con una línea equivocada, y está aquí el error en vez de
borrado, porque la tabla es la parte que alguien va a usar.

**Lo que escribí:** `BAR5 ... 262144  -`, es decir flags vacíos, y a partir de ahí
un `NOT_DETERMINED` que decía «en el fichero `resource` los flags de BAR5 son 0».

**Lo que es:** los flags de BAR5 son **`0x0000000000040200`**, no cero. Los dos
lectores que usé dan cosas distintas porque el fichero **cambió entre lecturas**:

```text
  lectura ~07:37   linea 6:  0x00000000f7d00000 0x00000000f7d3ffff 0x0000000000000000
  lectura  08:21   linea 6:  0x00000000f7d00000 0x00000000f7d3ffff 0x0000000000040200
  mtime del fichero: 2026-10-03 08:21:17
```

**Y la causa de que lo escribiera como `-` es mi decodificador, no el hardware.**
`barmap.py` solo nombra los bits `0x1 IO`, `0x2 MEM`, `0x4 PREF`, `0x8 64BIT`,
`0x10 HOST`. `0x40200` es `0x200 | 0x40000`, y ninguno de los dos está en esa
lista, así que la columna salía vacía. **Una columna que se ve vacía porque el
decodificador no sabe nombrar los bits no es una columna vacía.**

```text
  CORREGIDO   los flags de BAR5 son 0x40200 en la lectura de 08:21
  CORREGIDO   el NOT_DETERMINED que citaba "flags 0" era un hueco MIO
  SIGUE VIGENTE
    la ventana BAR5 mide 262144 bytes, y eso NO ha cambiado en ninguna lectura
    resource5 st_size = 262144     fuente independiente, sin root
    fin - inicio + 1 = 262144      del fichero agregado
    los dos coinciden, y el rango 0xF7D00000..0xF7D3FFFF es el mismo en las dos
  NUEVO Y NO RESUELTO
    que significan los bits 9 y 18, y POR QUE el fichero se regenera. Un
    `resource` que cambia solo es o un BAR reasignado o un reenum, y no se ha
    mirado el config space para saber cual. NO_DETERMINED
```

Lo que **no** ha cambiado y es lo que sostiene el hallazgo: **la identidad y el
tamaño de la ventana**. Todo lo demás de esa tabla salió de un decodificador mío
que no se ha contrastado, y eso es exactamente el fallo de `294` aplicado a mi
propio script: detector escrito de una vez y creído sobre su propia salida.

## 9 · Corrección de numeración

```text
  este fichero se escribio como 305, reservado con --reservar antes de escribir
  CORRECTED_BY: --reservar 305  RESERVADO

  Y ABRE UNA FRONTERA NUEVA
    el mapa BAR de ESTA GPU esta PROBADO desde el sysfs, con dos fuentes
    independientes, sin corpus y sin root. El driver eligio bien la ventana.
    Falta lo unico que queda: que la ventana este habilitada, y que se pueda
    leer. Eso sigue bloqueado por autorizacion del modulo propio, no por falta
    de saber donde mirar
```

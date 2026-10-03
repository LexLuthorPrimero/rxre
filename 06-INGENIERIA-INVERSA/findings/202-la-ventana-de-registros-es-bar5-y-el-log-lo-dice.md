# 202 · La ventana de registros es BAR5, no BAR2, y el log del kernel lo dice sin root

```
CLASSIFICATION=MEASUREMENT+OBSERVATION+CONTRADICTION+CORRECTION · TRACK=RUNTIME+STATIC
CORPUS=RESEARCH/working/linux-7.2.8 · HARDWARE_SCOPE=READ_ONLY
WORK_CLASS=READ_ONLY/EVIDENCE+WRITE_LOCAL · WRITE_LOCAL=PROPIOS · MODIFICATIONS_CORPUS=0
RUNTIME=READ_ONLY (journalctl -k -b) · GPU INTACTA · CERROJOS=0
```

## Qué resuelve

`237` §3 dejó por escrito, y con razón, que **qué bloque de registros vive en
qué BAR** era `NOT_IN_CORPUS`. Eso queda **cerrado por observación**, sin root y sin
escribir nada:

```
el kernel, al arrancar, imprime su propia variable
        register mmio base: 0xF7D00000
        register mmio size: 262144

262144 == la longitud de resource5, medida con stat()
2097152 == la longitud de resource2, la que estava declarada
```

Y el código que produce esa variable elige el BAR:

```
amdgpu_device.c:3995   if (adev->asic_type >= CHIP_BONAIRE)
amdgpu_device.c:3996       rmmio_base = pci_resource_start(pdev, 5);
amdgpu_device.c:3997       rmmio_size = pci_resource_len(pdev, 5);      <- 256 KiB
amdgpu_device.c:3999   else  rmmio_* = ...(pdev, 2);                    <- 2 MiB
```

**La apertura de registros de esta GPU es BAR5, 256 KiB.** El driver propio
tenía `RX550_MMIO_BAR = 2` y `RX550_MMIO_LEN = 2 MiB`, y su test **pasaba**
certificando un contrato equivocado.

## 1 · Las tres mediciones, y por qué juntas no dejan duda

```
MEDICION     stat() sobre /sys/bus/pci/devices/0000:01:00.0/
               resource0    268435456   256 MiB
               resource2      2097152     2 MiB
               resource4           256     256 B
               resource5        262144   256 KiB
             (las direcciones siguen en 0600 root:root: eso sigue siendo
              BLOCKED_BY_PERMISSION y no se ha tocado)

OBSERVACION  journalctl -k -b, sin root:
               register mmio base: 0xF7D00000
               register mmio size: 262144

CODIGO       amdgpu_device.c:3995-4001, el if/else que elige el BAR
```

`262144` no coincide con ninguna otra longitud de la tabla. La coincidencia no es
suerte: es el mismo número que el driver imprimiría si hubiera tomado la rama
del BAR 5.

### Lo que NO hace falta para concluir

El enum que decide la rama —`CHIP_POLARIS12` frente a `CHIP_BONAIRE`— **no está
en el corpus**. Se buscó `CHIP_BONAIRE` en todo el árbol y solo aparecen sus
**usos**, nunca su definición: el orden es `NOT_IN_CORPUS`.

No importa. La **observación ya dice qué rama se tomó**: el valor impreso es
`262144`, y ese valor solo lo produce la rama del BAR 5. Un número medido en
ejecución decide la rama sin necesitar el orden de un enum.

Es el mismo criterio que `233`: no se sustituye una software-semantics por otra,
se usa la que tiene un número detrás.

## 2 · Por qué `237` no estaba equivocado y aun así lo estaba

`237` **midió bien**. `resource2` mide 2 MiB, con o sin root, y eso sigue siendo
cierto hoy.

El fallo fue **la pregunta que acompañaba al número**: al mirar la tabla de
BARs, la ventana de registros "tiene que ser" la segunda, la grande, la que
`pci_iomap(pdev, 2)` —que era justo el nombre que se iba a escribir en el
código—. Y al escribir ese nombre, la medición dejó de ser una medición y pasó
a ser una justificación.

De modo que la contradicción no es «el número estaba mal», sino:

```
  resource2 = 2 MiB          PROVEN, y sigue siendo cierto
  la ventana es resource2    REFUTADO, y ahora es resource5
```

Eso es exactamente el motivo por el que `NOT_IN_CORPUS` no se rellenó con una
suposición razonable la primera vez: **la conjetura era razonable**.

## 3 · Daño contenido, y comprobado que está contenido

La ventana baja de 2 MiB a 256 KiB. Los offsets que el driver tiene que tocar
siguen cabiendo, y con holgura:

```
  10 offsets comprobados, 0 fuera de 262144
  el mayor es MM_COMPUTE_PGM_RSRC1 = 0x2e12 = 11794 bytes
  ocupa el 4,5 % de la ventana

  0x54f  0x50e  0x51e      registros de VM        findings/180
  0x2e00 0x2e07 0x2e0c
  0x2e0d 0x2e12            registros MM_COMPUTE   findings/180
  0x809                    MC_VM_FB_LOCATION       findings/201
  0x150a                   CONFIG_MEMSIZE (BIF)    findings/202 §4
```

Un tamaño de ventana que baja un orden de magnitud y no saca ni uno de fuera es
información: el driver's conjunto de registros es pequeño, y el riesgo de que
alguna vez se escribiera fuera era pequeño **por el motivo equivocado**.

## 4 · Lo que sale de este hallazgo, y no de la corrección

Lo demás que trae el log del arranque es una **medición del hardware en
ejecución** que cierra tres cadenas de golpe:

```
vm size is 64 GB, 2 levels, block size is 10-bit, fragment size is 9-bit
VRAM: 2048M 0x000000F400000000 - 0x000000F47FFFFFFF (2048M used)
GART: 256M 0x000000FF00000000 - 0x000000FF0FFFFFFF
5907M of GTT memory ready.
[drm] GART: num cpu pages 65536, num gpu pages 65536
[drm] PCIE GART of 256M enabled (table at 0x000000F400900000).
[drm] RAM width 64bits GDDR5
```

**a) Las versiones de IP, de verdad.** `hwip.py` mide que las versiones **no**
salen de una tabla estática sino de un buffer de firmware. El log es ese
resultado, en esta placa:

```
0 <common_v1_0_0>   1 <gmc_v8_1_0>    2 <ih_v3_0_0>    3 <gfx_v8_0_0>
4 <sdma_v3_1_0>      5 <smu_v1_0_0>   6 <dce_v1_0_0>    7 <uvd_v6_3_0>
8 <vce_v3_4_0>
```

`gmc_v8_1_0` y `ih_v3_0_0` corroboran `201` y `183` con evidencia de ejecución, no
con lectura de fuente.

**b) `vram_start` y `vram_end` verificados byte a byte.**

```
DERIVATION de 201     vram_start = (MC_VM_FB_LOCATION & 0xFFFF) << 24
OBSERVATION          vram_start = 0x000000F400000000
CONSUMER             vram_end   = vram_start + mc_vram_size - 1
                     amdgpu_gmc.c:221
CONTRAPREDICHA       0xF400000000 + 0x80000000 - 1 = 0xF47FFFFFFF
OBSERVADO            0x000000F47FFFFFFF                     IDENTICO
```

La fórmula del consumidor queda **verificada contra el hardware en ejecución**,
sin haber escrito nada en él.

Y el productor pasa de derivación a **predicción falsable**: si el registro
`0x809` se leyera cuando exista el mapa, tiene que dar `0x0000F400`. Una
predicción falsable vale mucho más que una derivación no falsable: es lo que
comprobará el driver el día que se autorice el mapeo.

### CORRECCION de la prediccion, y de donde salio el error

La primera versión de esa línea decía **`0x00000F40`**. Es incorrecto: produce
`0x000F40000000`, que es 16 veces menor que el `0x000000F400000000` del log.

El valor correcto se obtiene dividiendo, y la división da `0xF400`:

```
  vram_start observado              0x00F400000000
  registro que lo produciria        0xF400        (vram_start >> 24)
  el que se escribio                0x0F40
  y produce                         0x000F40000000     <-- 16x menor
```

**Lo que pasó es un desplazamiento de cuatro bits de nibble**, que es el error
más difícil de ver en un número hexadecimal porque el resultado sigue siendo un
número plausible: `0xF40` y `0xF400` se parecen mucho.

Y hay una razón por la que no lo vi al escribirlo: **era una predicción, no una
medida**, y una predicción no se comprueba con el mismo cuidado que una
medición. Es exactamente el caso contra el que advierte `LEGADO`: el sitio donde
un error se propaga solo es el código, y aquí el sitio era el hallazgo, que es
peor porque el hallazgo es la evidencia.

Lodagra el test `test_mc` con un vector que multiplica la cadena entera contra
los dos números del log, y que por eso no habría podido pasar con `0x0F40`
puesto.

**c) `CONFIG_MEMSIZE` está en otro bloque.** El registro que dice *cuánta* VRAM
hay no está en GMC sino en **BIF**:

```
bif_4_1_d.h:33      mmCONFIG_MEMSIZE = 0x150a
bif_4_1_sh_mask.h   CONFIG_MEMSIZE__CONFIG_MEMSIZE_MASK    = 0xffffffff
bif_4_1_sh_mask.h   CONFIG_MEMSIZE__CONFIG_MEMSIZE__SHIFT  = 0x0

gmc_v8_0.c:560      tmp = RREG32(mmCONFIG_MEMSIZE);      /* size in MB */
gmc_v8_0.c:567      mc_vram_size = tmp * 1024ULL * 1024ULL;
```

La máscara es `0xffffffff` con shift 0: **el campo está documentado como 32 bits
de ancho completo**, y por eso el driver añade un heurístico de basura:

```
gmc_v8_0.c:561     /* some boards may have garbage in the upper 16 bits */
gmc_v8_0.c:562     if (tmp & 0xffff0000) {
gmc_v8_0.c:563         drm_info(... "Probably bad vram size: 0x%08x", tmp);
gmc_v8_0.c:564         if (tmp & 0xffff)
gmc_v8_0.c:565             tmp &= 0xffff;
gmc_v8_0.c:566     }
gmc_v8_0.c:567     mc_vram_size = tmp * 1024 * 1024;
```

El heurístico **solo corrige el caso en que los 16 bits bajos sean distintos de
cero**. Con `tmp = 0xffff0000` —justo el valor que el comentario describe— no
enmascara nada y `mc_vram_size` sale multiplicado por el valor basura. Es un
defecto latente de upstream, **no** un fallo observado: en esta placa el log dice
`VRAM: 2048M`, o sea que la basura no apareció.

Para el driver propio la regla es directa y comprobable: un `CONFIG_MEMSIZE`
cuyo mitad alta tenga algo puesto y cuya mitad baja sea cero **no se puede
interpretar**, y el driver no debe multiplicarlo.

Que *dónde* está la VRAM y *cuánta* hay estén en bloques distintos (GMC y BIF)
es la razón por la que `NOT_IN_CORPUS` en el mapa de bloques pesaba más de lo
que parecía: no es un mapa, son varios.

## 5 · Corrección aplicada

```
07-DRIVER/kernel/rx550_mmio.h
    RX550_MMIO_BAR   2 -> 5
    RX550_MMIO_LEN   2 MiB -> 256 KiB
    el comentario que declaraba NOT_IN_CORPUS ahora cita la observacion

07-DRIVER/tests/test_mmio.c
    26 -> 27 checks
    y un NEGATIVO nuevo: la ventana NO es la de 2 MiB
```

Ese negativo es lo que hace el contrato comprobable en las dos direcciones. Un
test que solo comprobara que el número correcto está puesto no detectaría haber
vuelto al equivocado:

```
volver RX550_MMIO_LEN a 2 MiB   ->  3 checks fallan
restaurado                        ->  27 checks, 0 failures
```

`237` no se reescribe. Este hallazgo es el que lo corrige.

## 6 · La CORRECCION de este hallazgo, sobre sí mismo

La primera versión de esta sección afirmaba que `journalctl -k -b` era «una ruta
de lectura que no estaba registrada». **Es falso, y lo demonstrated el fichero
que estaba a un comando de distancia**:

```
routeaudit.py:80    "journalctl": ("journalctl -k", True,
                       "medido antes: legible sin root")
routeaudit.py:236   if RUTAS["journalctl"][1] is not True:      (en un selftest)
```

La ruta estaba registrada, con su etiqueta y su procedencia. Lo que es cierto es
otra cosa, y es lo que vale la pena:

```
  la ruta SABIA               routeaudit.py la tiene como alcanzable desde 134
  nadie la habia preguntado   ningun hallazgo pedia por ella lo que trae
```

Y eso es un fallo de la herramienta, no de la persona: `routeaudit.py` cruza las
rutas contra las líneas `PENDIENTE=`, pero **no** contra lo que las rutas podrían
dar. Una ruta puede ser alcanzable, estar marcada como tal, y no ser usada
nunca, porque nadie hamirado dentro.

La lección es la de siempre y por cuarta vez en esta sesión: **esta afirmación
también salió de memoria**. Las tres anteriores —la convención de upstream, la
forma `-y` de kbuild y esta ruta— tenían el fichero en disco. Un recuerdo se
puede corregir; una medición no.

Lo que sí faltaba no era la ruta. Era la pregunta.

## 7 · Trazabilidad

```
  amdgpu_device.c:3995-4001   la eleccion de BAR, y las dos ramas
  amdgpu_device.c:4010-4013   dev_info que imprime base y size
  gmc_8_0.c:560-567           CONFIG_MEMSIZE -> mc_vram_size
  amdgpu_gmc.c:221            vram_end = vram_start + mc_vram_size - 1
  bif_4_1_d.h:33              mmCONFIG_MEMSIZE 0x150a
  bif_4_1_sh_mask.h           MASK 0xffffffff, SHIFT 0x0
  journalctl -k -b            la observacion, sin root
  /sys/bus/pci/devices/0000:01:00.0/resourceN   las longitudes, sin root
  findings/176 §3             el NOT_IN_CORPUS que esto cierra
  findings/180                los 8 offsets, que siguen cabiendo
  findings/201                vram_start, ahora con prediccion falsable
  findings/183                IH v3.0, ahora corroborado en ejecucion
```

```
CITA=amdgpu_device.c | TERMINO=pci_resource_start(adev->pdev, 5)
    | ROL=la rama que abre la ventana de registros es la de BAR 5
CITA=amdgpu_gmc.c | TERMINO=mc->vram_end = mc->vram_start + mc->mc_vram_size - 1
    | ROL=la aritmetica del consumidor, verificada contra 0xF47FFFFFFF
```
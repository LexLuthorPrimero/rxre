# 1418 — esta tarjeta ejecuta 9 bloques IP del camino gfx8 legacy y ninguno de MP0/MP1/THM/SMUIO: el inventario "Arcturus" que se me pidió describe otro ASIC

```text
AGENCIA=RX550-INVESTIGACION · WORK_CLASS=AGENT-MAIN/RE
CLASSIFICATION=REFUTACION-DE-PREMISA+CONTAMINACION-CROSS-ASIC+CORRECCION-PROPIA
TRACK=RUNTIME-PASIVO(journalctl, sólo lectura) · sin GPU · sin sudo
GENERADO=2026-10-04
AFECTADO=el encargo que YO di al subagente "Inventory Arcturus driver structures"
         smu11_driver_if_arcturus.h · arct_ip_offset.h · arcturus_ppt.c · soc15_common.h
         soc15.c · arcturus_ip_discovery.bin   -> NO_APPLICABLE a esta tarjeta
         y en cascada: el alcance pratico del hallazgo 1402, que queda POR REVISAR
ORIGEN=el subagente hizo un inventario de "la fuente del vendor para esta ASIC" siguiendo
       mi indicacion de que el camino correcto era el de Arcturus/soc15.  El inventario
       es correcto sobre Arcturus.  **Arcturus no es esta tarjeta.**
ESTADO=PROBADO · 9 bloques IP medidos en ejecucion, los nueve del camino gfx8 legacy
       · MP0/MP1/THM/SMUIO/NBIF0/ATHUB/MMHUB/OSSSYS: NO aparecen
       · el ROM de esta tarjeta se identifica como "Lexa", no Arcturus (enlaza con 1400)
       · ERROR PROPIO: mande un subagente al ASIC equivocado.  Es el fallo que §5/§6
         prohiben, cometido por esta sesion
```

## 0. Lo que el kernel dice que esta tarjeta ejecuta

Del log del arranque, `journalctl -k -b`, sin sudo:

```text
amdgpu 0000:01:00.0: initializing kernel modesetting (POLARIS12 0x1002:0x699F 0x1002:0x0B04 0xC7).
amdgpu 0000:01:00.0: register mmio base: 0xF7D00000
amdgpu 0000:01:00.0: register mmio size: 262144

detected ip block number 0 <common_v1_0_0>   (vi_common)
detected ip block number 1 <gmc_v8_1_0>      (gmc_v8_0)
detected ip block number 2 <ih_v3_0_0>       (tonga_ih)
detected ip block number 3 <gfx_v8_0_0>      (gfx_v8_0)
detected ip block number 4 <sdma_v3_1_0>     (sdma_v3_0)
detected ip block number 5 <smu_v1_0_0>      (powerplay)
detected ip block number 6 <dce_v1_0_0>      (dm)
detected ip block number 7 <uvd_v6_3_0>      (uvd_v6_0)
detected ip block number 8 <vce_v3_4_0>      (vce_v3_0)
```

**Nueve bloques. Los nueve son de la familia gfx8/vgfx10-era.** Compárese con lo que el
camino soc15-Arcturus habría producido (`amdgpu_discovery.c:2923-2956`, según el
subagente): GC_HWIP 9.4.1, MP0_HWIP 11.0.4, MP1_HWIP 11.0.2, THM_HWIP 11.0.3,
SMUIO_HWIP 11.0.3, UMC_HWIP 6.1.2, NBIO_HWIP 7.4.1, ATHUB_HWIP 9.4.1, MMHUB_HWIP 9.4.1.

**De esos once, esta tarjeta ejecuta cero.** En particular:

| bloque | ¿en el log? |
|---|---|
| MP0 | **no** |
| MP1 | **no** |
| THM | **no** |
| SMUIO | **no** |
| NBIF0 | **no** |
| ATHUB | **no** |
| MMHUB | **no** |
| OSSSYS | **no** |
| GC (HWIP 9.4.1) | no — hay `gfx_v8_0_0`, que es otro bloque |

**Y `grep -n 'CHIP_POLARIS12' amdgpu_discovery.c` no devuelve nada.** El ASIC se llama
`POLARIS12` en el log y en KFD, y ese identificador **no aparece en el fichero donde vive
el `case CHIP_ARCTURUS:`** que el subagente usó como "fuente autoritativa".

## 1. El nombre del chip, y por qué importa

Tres fuentes, leídas:

```text
ROM de la tarjeta (hallazgo 1400, cadena en off 0x114):
    b'R5\x00\r\nD09001 Lexa'        <-- el codename interno dice LEXA

KFD, en vivo:      nodes/1/name = polaris12
log del kernel:    POLARIS12 0x1002:0x699F ... 0xC7
```

**`Lexa` es el nombre de esta pieza. `Arcturus` es otro ASIC.** El hallazgo 1400 ya tenía
la cadena `D09001 Lexa` en la mano y no la conectó con nada; este hallazgo la convierte en
el dato que decide.

Que `smu11_driver_if_arcturus.h` y `arct_ip_offset.h` estén en el árbol **no las hace
pertenecer a esta tarjeta**. Están porque el *corpus* es una copia podada del kernel, y en
esa copia sólo sobrevivieron las cabeceras PPT de Arcturus. **La presencia de un fichero
en el árbol es evidencia sobre el árbol, no sobre el hardware** (§9:
`IMPLEMENTATION_IS_NOT_AUTHORITY`, y su hermano: *presencia de código no es ejecución*).

## 2. Consecuencia sobre la contradicción de `arct_ip_offset.h`

El subagente resolvió, con evidencia estática notable, que `arct_ip_offset.h` se contradice
para MP0/MP1/SMUIO/THM y de que los `#define` son los buenos (`CORROBORATED`, no `PROVEN`).
**Ese análisis no es incorrecto** — la tabla es contradictoria de verdad, y el mecanismo
(`struct == define[1:1+len]`, una columna perdida) queda verificado:

```text
MP0    define[0..] = 13fe0 16000 43fc00 dc0000 e00000 e40000
       struct     = [16000]                == define[1:2]        True
THM    define[0..] = 12060 16600 400c00
       struct     = [16600]                == define[1:2]        True
SMUIO  define[0..] = 12080 16800 16a00 401000 440000
       struct     = [16800, 16a00]         == define[1:3]        True
MP1    define[0..] = 12020 16200 400400 e80000 ec0000 f00000
       struct     = [16000]                == define[1:2]        False   <- copia de MP0
```

*(Corrección propia: la primera medición de esta comprobación la hice mal, comparando
contra `define[1:]` completo en vez de `define[1:1+len]`. Con la comparación bien
formulada, el resultado es el de arriba y coincide con el subagente.)*

**Pero ninguna de esas cuatro bases se usa en esta tarjeta**, porque MP0, MP1, THM y SMUIO
no se detectan. La contradicción es real y está sin arreglar upstream
(`sha256` idéntico en los cuatro árboles, 7.1.3 y 7.2.8), **y es irrelevante para
nosotros**. Es trabajo de AMD, no trabajo de este driver.

**Lo que sí es trabajo de este driver**: los nueve bloques que sí corren, con sus registros.
`gmc_v8_1_0`, `gfx_v8_0_0`, `sdma_v3_1_0`, `ih_v3_0_0`, `uvd_v6_3_0`, `vce_v3_4_0`,
`dce_v1_0_0`, `smu_v1_0_0`. Y el registro que manda es **`gmc_8_1_d.h`**, no
`gmc_8_0_d.h` — que, como ya registró el inventario de geometría, **no existe en el
corpus**.

## 3. Lo que este hallazgo deja POR REVISAR, sin cerrar

**El hallazgo 1402 tiene un alcance práctico que ahora hay que revisar.** Escribió:

> *cualquier cifra de potencia media del socket obtenida por `AMDGPU_PP_SENSOR_GPU_AVG_POWER`
> está escalada por un factor que el upstream cambió, y por tanto no es una medición*

La escala (`<< 8` frente a `* MILLIWATT_PER_WATT`) sigue siendo una divergencia real y
medida entre dos versiones de `arcturus_ppt.c`. **Pero si el SMU que sirve esta tarjeta no
es el de `arcturus_ppt.c`, ese `case` no se ejecuta aquí** y la consecuencia práctica que
escribí no se sostiene tal como está redactada.

**No la corrijo aquí** porque no tengo la evidencia para saber todavía qué ruta de PM
sirve a `CHIP_POLARIS12` en este kernel: `case CHIP_POLARIS12` no aparece en
`amdgpu_discovery.c`, y el corpus está podado (`pm/swsmu/inc/pmfw_if/` conserva **sólo**
dos cabeceras, las de Arcturus; las de `smu7` no están). Estado honesto:

```text
1402         la divergencia 256 vs 1000 en arcturus_ppt.c:661:  PROBADO (es lectura
             de fuente, correcta como tal)
1402        la CONSECUENCIA sobre "las cifras de potencia de esta host":  POR REVISAR
1406        VRAM_Info:  NO afectado — la tabla maestra ATOMBIOS no depende de la ruta soc15
1416        la geometria de la tabla de paginas:  NO afectado — sale de amdgpu_vm_pt.c,
             gmc_v8_0.c y gmc_8_1_d.h, que SI son el camino de esta tarjeta
```

El error conceptual que los atraviesa es el mismo que cometí yo: **dar por bueno que el
nombre del ASIC que aparece en el árbol es el ASIC que está en la máquina.**

## 4. Lo que este hallazgo también cierra

**El `EBUSY` de la sesión anterior, que estaba abierto como avería.** La sesión anterior
anotó `EBUSY` en nueve atributos `pp_*` y no lo explicó. Medido:

```text
/sys/class/drm/card1/device/power/runtime_status       = suspended
/sys/class/drm/card1/device/power/autosuspend_delay_ms = 5000
/sys/class/drm/card1/device/power/control               = auto
```

Y los seis sensores del nodo `hwmon1` (`amdgpu`, `0000:01:00.0`), con su etiqueta:

```text
fan1_input   = EBUSY      (temp1_label=edge, power1_label=PPT,
freq1_input  = EBUSY       freq1_label=sclk, freq2_label=mclk, in0_label=vddgfx)
freq2_input  = EBUSY
in0_input    = EBUSY
power1_input = EBUSY
temp1_input  = EBUSY
```

**La GPU está dormida**, con autosuspend a 5 s. Eso explica los seis `EBUSY` **y los nueve
`pp_*` de la sesión anterior**, sin que haya ninguna avería. **El `EBUSY` queda cerrado
como comportamiento esperado de runtime PM, no como defecto.**

Una hipótesis mía que quedó **refutada por el camino más barato**: suspected que el `EBUSY`
fuese la firma de que el SMU no contesta porque la base de MP1 es la mala — o sea, la
contradicción de `arct_ip_offset.h` manifestándose en el campo. Bastaba mirar
`runtime_status`. Se descartó antes de construir nada encima. **Queda escrito para que
nadie la vuelva a proponer.**

## 5. Por qué no hay blob de discovery (y por qué importa menos de lo que parecería)

```text
$ journalctl -k -b | grep -cE 'discovery'
0
```

**Ningún blob de discovery se carga en esta tarjeta.** No hay `arcturus_ip_discovery.bin`,
ni ningún otro. La detección de bloques pasa por el camino legacy (`vi_common` en el
nombre del bloque 0). Consistente con que `CHIP_POLARIS12` esté en el camino de bloques
legacy y nunca llegue al `case CHIP_ARCTURUS:`.

Consecuencia: **la tabla de offsets que se usa es la que hay en el `.ko`, tal cual.** No
hay blob firmado que la sobrescriba. Para nuestro driver eso significa que **las constantes
debe leerlas del `.c` del camino legacy, no de la tabla soc15.** El proyecto ya lo tenía
acertado en `rx550_mmio_access.c:759-761`, que cita `gmc_8_1_d.h`; este hallazgo confirma
que esa decisión era la buena y le quita la duda que quedaba.

## 6. Regla que sale de aquí

> **Un ASIC tiene tres nombres y sólo uno se mide en la máquina:** el identificador de
> silicon (`Lexa`), el nombre de marketing (`RX 550`), y el `enum` del driver
> (`CHIP_POLARIS12`). El `enum` que aparece en un fichero del corpus **no prueba** que ese
> fichero se ejecute, y el nombre de marketing no prueba nada. **La única prueba es la lista
> de bloques IP que el kernel imprimió al arrancar, que está en el log y es de lectura
> libre.**

Corolario operativo para este proyecto: **antes de encargar un inventario de "el driver de
esta ASIC", hay que leer `journalctl -k | grep 'detected ip block'` y confirmar que los
ficheros que se van a leer son los que se detectan.** Eso cuesta un segundo y habría
detectado la contaminación antes de pagar la extracción.

## 7. Lo que este hallazgo NO hace

- **No afirma nada sobre la calidad del inventario de Arcturus.** Es un buen análisis de
  una tabla que realmente está rota. Lo que no es, es la tabla de esta tarjeta.
- **No localiza aún el camino de PM que sí corre** (`smu_v1_0_0 (powerplay)`). Ese es el
  siguiente paso real, y requiere saber qué `arcturus`/no-`arcturus` conecta
  `CHIP_POLARIS12`.
- **No revoca el hallazgo 1402**; lo marca `POR REVISAR` con la razón. Revocar sin
  evidencia sería sustituir un error por otro.
- **No toca la GPU.** Ni una escritura, ni un `modprobe`, ni un resume.

## 8. Procedencia

```text
journalctl -k -b   bloque de deteccion de IP, 9 entradas          (lectura, sin sudo)
journalctl -k -b   initializing kernel modesetting (POLARIS12 ...) (lectura)
journalctl -k -b   register mmio base 0xF7D00000 size 262144       (lectura)
journalctl -k -b   0 lineas de discovery                            (lectura)
sysfs              /sys/class/drm/card1/device/power/{runtime_status,control,
                   autosuspend_delay_ms}                           (lectura)
sysfs              /sys/class/drm/card1/device/hwmon/hwmon1/*      (lectura; EBUSY)
corpus             amdgpu/amdgpu_discovery.c   -> CHIP_POLARIS12 ausente
                   amdgpu/amdgpu_discovery.c:2923-2956 -> case CHIP_ARCTURUS (otro ASIC)
                   include/arct_ip_offset.h    -> sha256 identico en los 4 arboles
ROM                cadena "D09001 Lexa" en 0x114 (del hallazgo 1400)
KFD                nodes/1/name = polaris12
```

```text
ESTADO=PROBADO · 9 bloques IP medidos, todos gfx8 legacy
       · MP0/MP1/THM/SMUIO/NBIF0/ATHUB/MMHUB/OSSSYS/GC-soc15: NO se detectan
       · esta tarjeta se identifica como "Lexa" / POLARIS12; Arcturus es otro ASIC
       · la contradiccion de arct_ip_offset.h es REAL pero NO_APPLICABLE aqui
       · 0 lineas de discovery: la tabla del .ko se usa tal cual, sin blob que la pise
       · el EBUSY de los 9 pp_* y de los 6 sensores queda CERRADO: runtime_status=suspended
       · una hipotesis propia (SMU mudo por base MP1) queda REFUTADA antes de construir
ERROR PROPIO · mande un subagente al ASIC equivocado; el contaminante fue mi encargo
POR_REVISAR  · alcance practico del hallazgo 1402 (via de PM que sirve esta tarjeta)
Siguiente    1) localizar el camino de PM real de CHIP_POLARIS12: que .c sirve
               AMDGPU_PP_SENSOR_* en ESTE kernel.  Es lo que decide 1402
            2) a partir de ahi, y solo ahi, reabrir 1402 con el alcance correcto
            3) inventario de registros de los NUEVE bloques que si corren, no de once
               bloques soc15 que no existen en esta maquina
```

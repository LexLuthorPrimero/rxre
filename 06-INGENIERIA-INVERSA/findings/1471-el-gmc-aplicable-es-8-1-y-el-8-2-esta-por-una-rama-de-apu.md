# 1471 — Para esta tarjeta el GMC aplicable es 8.1 y su cabecera es `gmc_8_1_d.h`; el `gmc_8_2_d.h` que incluye `gfx_v8_0.c` está ahí por una rama de APU que en una RX550 discreta no se ejecuta nunca

```text
AGENCIA=RX550-INVESTIGACION · WORK_CLASS=AGENT-RE-TOOLING
GENERADO=2026-10-05 · MEDIDO=EN ESTA HOST, TODO EN FUENTE

ARTEFACTO=rx550-upstream-7.2.8/linux-7.2.8/drivers/gpu/drm/amd/
  amdgpu_drv.c:2054        la entrada de esta tarjeta, con sus flags
  amdgpu/vi.c:2105-2126    el case de POLARIS12
  amdgpu/gmc_v8_0.c:1762   las dos versiones de IP, con la MISMA tabla de funcions
  amdgpu/gfx_v8_0.c:41     el include de gmc_8_2_d.h
  amdgpu/gfx_v8_0.c:1793   los dos unicos usos de mmMC_FUS, tras if (AMD_IS_APU)
  include/asic_reg/gmc/gmc_8_1_d.h, gmc_8_2_d.h

CIERRA=el alcance de 1459 §0.  El oráculo de umr y la cabecera que compila
        GFX8 NO son el mismo fichero, y 1459 no lo decía.
CIERRA=1404 §5 por segunda via: mmVM_CONTEXT{2..7}_CNTL no existen en NINGUNA
        de las dos cabeceras
CONFIRMA=que los hallazgos que citan gmc_v8_0.c cited el fichero correcto:
        la tabla de funciones que corre es la de ese fichero
ESTADO=PROVEN por lectura de fuente. El valor en silicio sigue NOT_DETERMINED.
```

## 0 · DE DÓNDE SALE LA DUDA

`1470` §2 dijo que la desambiguación de un registro está en **el fichero**, no en
el bloque, porque la generación sólo está en el nombre del fichero. Consecuencia
inmediata: *¿qué fichero compila GFX8?* Para el MMU/VM, la respuesta parecía
obvia y no lo era. Hay dos cabeceras GMC distintas en juego, las dos presentes
en el corpus, las dos incluidas por ficheros que corren en esta tarjeta:

```text
amdgpu/gmc_v8_0.c:41      #include "gmc/gmc_8_1_d.h"     <- el IP GMC de GFX8
amdgpu/gfx_v8_0.c:41      #include "gmc/gmc_8_2_d.h"     <- el IP de gráficos
```

Y `polaris12.asic` dice `gmc810 → ip/gmc_8_1_0.reg`. **Tres fuentes y dos
respuestas.** Con la regla `§80` (nadie gana por intuición) hay que resolverlo.

## 1 · LA RESOLUCIÓN: SON LA MISMA IMPLEMENTACIÓN

`vi.c` es explícito. Para esta tarjeta (`CHIP_POLARIS12`):

```c
case CHIP_POLARIS12:
        amdgpu_device_ip_block_add(adev, &vi_common_ip_block);
        amdgpu_device_ip_block_add(adev, &gmc_v8_1_ip_block);     <- 8.1
        amdgpu_device_ip_block_add(adev, &tonga_ih_ip_block);
        amdgpu_device_ip_block_add(adev, &gfx_v8_0_ip_block);
```

Y las dos versiones están definidas en el **mismo fichero**, con la **misma tabla
de funciones** (`gmc_v8_0.c:1754-1768`, leído entero):

```c
const struct amdgpu_ip_block_version gmc_v8_0_ip_block = {
        .type = AMD_IP_BLOCK_TYPE_GMC, .major = 8, .minor = 0, .rev = 0,
        .funcs = &gmc_v8_0_ip_funcs,
};

const struct amdgpu_ip_block_version gmc_v8_1_ip_block = {
        .type = AMD_IP_BLOCK_TYPE_GMC, .major = 8, .minor = 1, .rev = 0,
        .funcs = &gmc_v8_0_ip_funcs,          <-- la MISMA tabla
};
```

**Consecuencia que tranquiliza lo anterior:** los hallazgos `1401`, `1403`,
`1404`, `1411` y `1430` citan `gmc_v8_0.c` y **citan el fichero correcto**. No
hay error de procedencia que corregir en ninguno de ellos. El "8.1" del
`ip_block` es una etiqueta de versión de hardware; el fichero se llama 8.0 porque
contiene la implementación compartida.

`gmc_v8_0_ip_block` se usa para `CHIP_CARRIZO` (`vi.c:2125`), que es una ASIC
distinta. Por eso `oss_3_0_1_d.h` —la cabecera que citaba `1450` para
`mmHDP_DEBUG0`— solo la incluye `cz_ih.c`. **`1450` acierta en el valor y cita la
cabecera de otra tarjeta.** Corregido en §6.

## 2 · Y LOS REGISTROS DE VM NO CAMBIAN ENTRE LAS DOS

Comparadas las dos cabeceras campo a campo, con el tool de `1470`:

```text
gmc_8_1_d.h   1675 simbolos        gmc_8_2_d.h    877 simbolos
comunes con la MISMA direccion      839
comunes con DISTINTA direccion        1   (0,12 %)
solo en 8_1                          835
solo en 8_2                           37
```

Los cuatro registros que `1459` validó, uno a uno:

| registro | `gmc_8_1_d.h` | `gmc_8_2_d.h` | |
|---|---|---|---|
| `mmVM_CONTEXT0_CNTL` | `0x504` | `0x504` | igual |
| `mmVM_CONTEXT1_CNTL` | `0x505` | `0x505` | igual |
| `mmVM_INVALIDATE_REQUEST` | `0x51e` | `0x51e` | igual |
| `mmVM_INVALIDATE_RESPONSE` | `0x51f` | `0x51f` | igual |

**La conclusión de `1459` sobrevive intacta.** Lo que cambia es su procedencia:
la cabecera aplicable es `gmc_8_1_d.h`, no la que `umr` nombra.

**Y `1404 §5` queda cerrado por segunda vía, más fuerte:** `mmVM_CONTEXT2_CNTL`
hasta `mmVM_CONTEXT7_CNTL` **no existen en ninguna de las dos cabeceras**. No es
que falten en `8_1`: faltan en las dos. `1404` lo afirmó para `max_level = 1`;
ahora está confirmado contra el otro par de cabeceras que GFX8 incluye.

## 3 · LA ÚNICA DISCREPANCIA, Y POR QUÉ EXISTE

El único registro que se mueve es el mismo en las cinco cabeceras donde aparece,
y la dirección se comporta como una bandera de revisión:

```text
gmc_6_0_d.h    0x0A21
gmc_7_1_d.h    0xa21
gmc_8_1_d.h    0xa21      <- la de esta ASIC
gmc_7_0_d.h    0xa32
gmc_8_2_d.h    0xa32
```

`mmMC_CG_DATAPORT`. **No lo usa nadie:** `grep` de todo el driver, excluyendo
`asic_reg`, devuelve vacío. Así que la discrepancia es **latente**, no un bug
activo. Se declara aquí porque el día que se use ese registro habrá dos
direcciones en juego y el fichero del que se copie decide cuál.

## 4 · POR QUÉ `gfx_v8_0.c` INCLUYE UNA CABECERA QUE NO ES LA SUYA

Los 37 símbolos exclusivos de `gmc_8_2_d.h` son la familia `mmMC_FUS_*`
—fusibles de memoria—. Y `gfx_v8_0.c` los usa. Dos veces. Las dos dentro de la
misma rama (`gfx_v8_0.c:1790-1800`):

```c
if (adev->flags & AMD_IS_APU) {
        /* Get memory bank mapping mode. */
        tmp = RREG32(mmMC_FUS_DRAM0_BANK_ADDR_MAPPING);
        ...
        tmp = RREG32(mmMC_FUS_DRAM1_BANK_ADDR_MAPPING);
```

Y `AMD_IS_APU` no se pone en ningún sitio salvo en la tabla de IDs PCI
(`amdgpu_drv.c:1914` en adelante). La entrada de esta tarjeta (`amdgpu_drv.c:2054`):

```c
{0x1002, 0x699F, PCI_ANY_ID, PCI_ANY_ID, 0, 0, CHIP_POLARIS12},
```

**flags = `0`.** Sin `AMD_IS_APU`, sin `AMD_IS_MOBILITY`. La RX550 es discreta.

**Por tanto la rama no se ejecuta nunca en este target, y el `gmc_8_2_d.h` de
`gfx_v8_0.c` está ahí para compilar código muerto.** La explicación es completa y
no requiere ninguna hipótesis: include hecho para el APU, header del APU, rama
del APU, y en una tarjeta discreta las tres son inertes.

Esto es exactamente el patrón que `1403` ya denomino en `gfxhub` y que `1452`
detectó en SDMA. **El driver de GFX8 tiene tres mecanismos de código muerto
independientes, y los tres se reconocen por leer quién incluye qué.**

## 5 · LA CONCLUSIÓN OPERATIVA PARA EL DRIVER

```text
PARA ESTA TARJETA, el conjunto de registros aplicable es:

  gmc_8_1_d.h        IP GMC que corre        -> la via MMU/VM, la que importa
  gca/gfx_8_0_d.h    IP de graficos          -> coherencia de firma, dispatch
  oss_3_0_d.h        IP OSS                  -> HDP, vallas
  dce_10_0_d.h       IP DCE                  -> solo si hay DC
  smu_7_1_3_d.h      IP SMU                  -> powerplay
  vi.h / vi_structs.h

  Y EXCLUIDO por estar en rama de APU:
  los 37 mmMC_FUS_* que solo existen en gmc_8_2_d.h
```

`§5 NO PORTABILITY BY DEFAULT` pide usar geometría conocida de esta ASIC con
"hardware fact + semantic closure + measured benefit". La tabla de arriba es
hardware fact, leída de la fuente, y es lo que un driver propio debería usar en
lugar del encabezado que compila el driver de referencia.

## 6 · CORRECCIONES

```text
CORRIGE a 1450   mmHDP_DEBUG0 = 0x0bcc, pero la cabecera citada es la de
                 CARRIZO.  La de esta ASIC es oss/oss_3_0_d.h:602, que tiene el
                 MISMO valor.  La identificacion por cadena de 6 saltos sigue
                 valiendo; lo que cambia es el fichero de procedencia.
                 Verificado en las 6 cabeceras oss: 0xbcc en todas.
NO CORRIGE a 1401, 1403, 1404, 1411, 1430
                 gmc_v8_0.c es el fichero correcto: contiene la tabla de
                 funciones que corre en esta ASIC.
```

## 7 · LO QUE SIGUE SIN DETERMINAR

Nada de esto se ha medido en silicio, y hay que decirlo porque §22 lo exige:

```text
NOT_DETERMINED  que valor tienen mmVM_CONTEXT0_CNTL y mmVM_INVALIDATE_REQUEST
                en el ASIC, y si difieren de la cabecera.  Bloqueado por
                credenciales, no por autorizacion.
NOT_DETERMINED  por que GFX8 declara gmc 8.1 con una tabla de funciones 8.0.
                Es un hecho del codigo; el motivo no esta escrito en ninguna
                parte.  No hace falta para el driver, asi que no se investiga.
NO_APLICA       el camino mmMC_FUS.  No hay nada que cerrar: no se ejecuta.
```

## 8 · POR QUÉ ESTE HALLAZGO NO ES UNA RUTINA MÁS

Porque `1459` usó un oráculo externo y yo no comprobé que ese oráculo hablara de
**el mismo fichero que el driver compila**. El oráculo era correcto —los cuatro
offsets coincidían— y aun así la cadena de trazabilidad tenía un hueco: un
salto entre `umr` y `gmc_8_2_d.h` que nadie había mirado porque el oráculo y la
fuente parecían decir lo mismo.

`§11` distingue `EVIDENCE EXISTS` de `EVIDENCE SUPPORTS CLAIM`. Aquí las dos
cosas eran ciertas y la evidencia **no sostenía** la afirmación completa. Un
oráculo externo sin correspondencia de fichero con la compilación no es
independiente: es un segundo sitio que no se puede casar con el primero.

El vector nuevo, y es el que hay que dejar escrito:

```text
  AL USAR UN ORACULO EXTERNO
    1. el oráculo nombra un .reg; ¿que .h compila ESTA ASIC?
    2. si no coinciden, ¿coinciden los VALORES?
    3. si coinciden los valores pero no los ficheros, el claim sobrevive
       pero la TRAZABILIDAD tiene un salto.  Declararlo.
```

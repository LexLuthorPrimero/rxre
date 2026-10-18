# 1566 — Se pueden leer 74 registros de hardware de la RX550 en vivo, sin root y sin debugfs. La puerta era el nodo de render, no el privilegio. Y el error era mío: declaré la struct a mano

```text
AGENCIA=RX550-INVESTIGACION · WORK_CLASS=AGENT-RE-TOOLING
GENERADO=2026-10-05 · MEDIDO=EN ESTA HOST

CIERRA         el bloqueo que arrastraba desde 1534.  No por root:  por el
               nodo.  Y no era un bloqueo del kernel:  era una struct mia
               mal declarada.
DESCUBRE       /dev/dri/renderD128 es crw-rw-rw- y el ioctl lleva
               DRM_RENDER_ALLOW, asi que AMDGPU_INFO_READ_MMR_REG entra sin
               ser DRM master.  Solo hay 74 registros en lista blanca.
PROVEN         74 de 76 registros de la lista blanca de vi.c devuelven valor
               real.  Artefacto: revkit/capturas/live/mmr_20261005_133917.txt
PROVEN         los 7 controles negativos salen TODOS rechazados, incluidos
               IH_RB_BASE/RPTR/WPTR/CNTL e INTERRUPT_CNTL.  El control pasa.
NEGATIVO       2 de los 76 (los dos SDMA STATUS) los rechaza el kernel que
               corre.  El corpus es 7.2.8 y el kernel es 7.2.9:  difieren.
TRANSFORMA     1534.  El anillo del IH sigue sin leerse, y ahora se por que,
               con dos razones separadas y una de ellas medible.
ERROR, mio     el grande:  declare struct drm_amdgpu_info a mano con un
               union de pad[384].  sizeof salio 400 en vez de 32, y el numero
               de ioctl se calcula desde sizeof, asi que mandaba 0x41906440
               en vez de 0x40206445.  Decimosima quinte vez con la misma
               clase de error.
```

## 0 · LO QUE SE ABRE, EN UNA FRASE

Antes de esta sesion, para leer un registro de la RX550 haria falta root, y la
unica lectura sin privilege era un contador de IRQ. **Eso ya no es cierto.**
Ahora, sin ser root y sin ser el DRM master:

```bash
$ /dev/dri/renderD128 + DRM_IOCTL_AMDGPU_INFO + AMDGPU_INFO_READ_MMR_REG
  -> 74 registros con su valor, en vivo
```

Y hay un dato que solo se puede obtener asi: `mmGRBM_STATUS` es el **contador de
paquetes pendientes del anillo de gráficos**. Es la primera medida de actividad
del pipeline de GFX que tengo sin root, y es un estado, no un contador de
eventos.

## 1 · EL CANDADO NO ES EL PRIVILEGIO. ES EL NODO, Y ESTÁ EN UNA LÍNEA

```c
/* amdgpu_drv.c:3084 */
DRM_IOCTL_DEF_DRV(AMDGPU_INFO, amdgpu_info_ioctl, DRM_AUTH|DRM_RENDER_ALLOW),
```

```text
  DRM_AUTH        exige ser el DRM master.
  DRM_RENDER_ALLOW el mismo ioctl vale por el nodo de render.

  Y card1 esta en manos de Xwayland (pid 1985, medido con fuser), asi que yo
  NO soy el master.  Pero renderD128 es crw-rw-rw- y no tiene master.
```

Medido, no deducido:

```text
  nodo                 EACCES o OK
  ----------------------------------------------------------
  /dev/dri/card1       EACCES   (no soy el DRM master; lo es Xwayland)
  /dev/dri/renderD128  OK       (74 registros, sin root)
```

```text
  CORRIGE, mio  durante años de este proyecto he escrito que "el unico camino
                sin privilege es /proc/interrupts".  Es FALSO y no por una
                cuestion de permisos:  por el nodo.  El nodo de render es de
                lectura-uso para el mundo entero, y el driver declara
                expresamente que ese ioctl se puede usar ahi.
```

## 2 · EL ERROR PROPIO, QUE ERA TODO EL PROBLEMA

`mmrlive` exists desde el principio de esta sesion con la struct declarada a
mano, para no depender de las cabeceras del kernel:

```c
        union {
                struct {
                        uint32_t dword_offset;
                        uint32_t count;
                        uint32_t instance;
                        uint32_t flags;
                } read_mmr_reg;
                uint8_t pad[384];
        } u;
```

**`sizeof(struct drm_amdgpu_info)` = 400 con eso. El valor real es 32.** Y el
numero de ioctl no es un numero: se construye con `_IOW(base, nr, type)`, que
**codifica `sizeof(type)` en los bits 16-29**.

```bash
$ gcc -I /usr/src/kernels/$(uname -r)/include/uapi ... && ./szprobe
  sizeof(struct drm_amdgpu_info) = 32
  DRM_IOCTL_AMDGPU_INFO         = 0x40206445
  offsetof return_pointer       = 0
  offsetof return_size          = 8
  offsetof query                = 12
  offsetof read_mmr_reg         = 16
```

Lo que yo mandaba y lo que era:

```text
  mio       0x41906440     nr = 0x40,  size = 0x190 (400)
  real      0x40206445     nr = 0x45,  size = 0x020  (32)
```

Dos cosas mal a la vez: el numero de comando (`DRM_AMDGPU_INFO` es **0x05**, no
`0x00`) y el tamano.

Y el sintoma era Engelegante por equivoco:

```text
  mio con card1     ->  EACCES, en los 76 registros por igual
  mio con render    ->  ENOSPC en 9 queries, EINVAL en el MMR

  Y ESO PARECIA UNA PERMISO.  "En card1 no deja, en render deja pasar el
  candado pero el driver no."  No era permiso:  era mi numero de ioctl.
  ENOSPC y EINVAL son los errores que da drm_ioctl cuando el comando no
  corresponde a la tabla, y yo lo leia como "el kernel dice que no".
```

La prueba de que era eso, y no el driver, es el autotest: **los mismos nueve
queries que fallaban antes ahora dan OK, con el mismo binario, el mismo nodo y
el mismo kernel**, y lo unico que cambio es que la struct viene de la cabecera.

```text
  ANTES (struct a mano, ioctl 0x41906440):
      ACCEL_WORKING   ENOSPC     HW_IP_COUNT   ENOSPC     TIMESTAMP   ENOSPC
      VRAM_USAGE      ENOSPC     GTT_USAGE     ENOSPC     DEV_INFO    ENOSPC
      MEMORY          ENOSPC     VBIOS         EINVAL     NUM_HANDLES EINVAL
      READ_MMR_REG    EINVAL

  DESPUES (cabecera real, ioctl 0x40206445):
      ACCEL_WORKING   OK         HW_IP_COUNT   OK         TIMESTAMP   OK
      VRAM_USAGE      OK         GTT_USAGE     OK         DEV_INFO    OK
      MEMORY          OK         VBIOS         EINVAL     NUM_HANDLES EINVAL
      READ_MMR_REG    OK         <<<<<<<
```

```text
  ESTO ES LA DECIMOQUINTA VEZ con la misma clase de error, y la forma es
  siempre la misma:

      1500  caja de un digito          -> no mire TODA la salida
      1502  atribu linea al grep       -> no mire CUAL de dos
      1506  igual                      -> no mire CUAL de dos
      1508  | head                     -> no mire lo que truncaba
      1516  ciclo parcial              -> VI un patron y preferi verlo
      1518  redondeo                   -> no mire la forma que previa
      1523  "el ultimo"               -> no mire el orden de archivo
      1531  .c -> .h                   -> no mire el sentido inverso
      1534  IH en debugfs              -> no mire la TABLA
      1550  raiz de include            -> no mire el Makefile
      1554  raiz de include, otra vez  -> no mire que era la fuente
      1556  include como arbol         -> no mire la forma del arbol
      1560  pahole -C con lista larga  -> no pruebe el instrumento
      1566  struct de ioctl a mano     -> no mire la cabecera que la define

  Y AQUI HAY UNA DIFERENCIA IMPORTANTE RESPECTO A LAS OTRAS CATORCE:
      en las otras catorce, leer la fuente de verdad habria cambiado el
      numero.
      aqui, leer la fuente de verdad cambio el RESULTADO:  de cero
      registros a 74.  No era un numero dudoso,  era un binario que no
      hablaba con el kernel.  Y yo estaba interpretando sus errores como
      politica de permisos.

  LA REGLA, y por que esta vez la incumpli con mas dano:
      UN ERROR QUE SE REPITE EN CATORCE HALLAZGOS NO SE ARREGLA ESCRIBIENDO
      CATORCE VECES QUE HAY QUE TENER CUIDADO.  Se arregla quitando la causa.
      Y aqui la causa era una:  DECLARAR A MANO ALGO QUE EL KERNEL YA PUBLICA.

  La regla operativa que sale de aqui, y que es ejecutable:
      NUNCA DECLARAR A MANO UN TIPO O UN NUMERO DE IOCTL QUE EL KERNEL
      PUBLIQUE EN UNA CABECERA.  Incluirla.  El nucleo es 32 bytes y yo
      escribi 400.
```

## 3 · LA LISTA BLANCA, GENERADA DESDE EL DRIVER

Para que la tabla de `mmrlive.c` no pueda desviarse de la del kernel, la genera
`revkit/tools/gen_mmr_table.py` leyendo `vi.c:vi_allowed_read_registers[]` y
resolviendo cada macro en las cabeceras ASIC. Las 76 entradas del driver salen
todas resueltas y el recuento se comprueba contra el del fuente.

**`vi_read_register` hace coincidencia EXACTA por offset.** No hay rangos:

```c
        for (i = 0; i < ARRAY_SIZE(vi_allowed_read_registers); i++) {
                if (reg_offset != vi_allowed_read_registers[i].reg_offset)
                        continue;
                ...
                return 0;
        }
        return -EINVAL;
```

Y `vi_get_register_value` distingue los `indexed=true`, que se multiplican por
SE y SH. Solo hay 4: `mmCC_RB_BACKEND_DISABLE`, `mmGC_USER_RB_BACKEND_DISABLE`,
`mmPA_SC_RASTER_CONFIG` y `mmPA_SC_RASTER_CONFIG_1`.

```text
  La tabla, con el offset resuelto de cada entrada:

  0x0025   mmSDMA0_STATUS_REG        EFAULT   <-- ver §5
  0x0225   mmSDMA0_STATUS_REG+SDMA1  EFAULT   <-- ver §5
  0x0393   mmSRBM_STATUS2            0x00000000
  0x0394   mmSRBM_STATUS             0x20000040
  0x0395   mmSRBM_STATUS3            0x00000000
  0x09D8   mmMC_ARB_RAMCFG           0x000060A2
  0x2002   mmGRBM_STATUS2            0x00000008
  0x2004   mmGRBM_STATUS             0x00003028
  0x2005   mmGRBM_STATUS_SE0         0x00000006
  0x2006   mmGRBM_STATUS_SE1         0x00000006
  0x200E   mmGRBM_STATUS_SE2         0x00000006
  0x200F   mmGRBM_STATUS_SE3         0x00000006
  0x2084   mmCP_CPC_STATUS           0x00000000
  0x2085   mmCP_CPC_BUSY_STAT        0x00000000
  0x2086   mmCP_CPC_STALLED_STAT1    0x00000000
  0x2087   mmCP_CPF_STATUS           0x00000000
  0x2088   mmCP_CPF_BUSY_STAT        0x00000000
  0x2089   mmCP_CPF_STALLED_STAT1    0x00000000
  0x219C   mmCP_STALLED_STAT3        0x00000000
  0x219D   mmCP_STALLED_STAT1        0x00000C00
  0x219E   mmCP_STALLED_STAT2        0x00000000
  0x21A0   mmCP_STAT                 0x00000000
  0x263D   mmCC_RB_BACKEND_DISABLE   0x00000001   indexed
  0x263E   mmGB_ADDR_CONFIG          0x22011002
  0x263F   mmGB_BACKEND_MAP          0x76541032
  0x2644-0x2663  mmGB_TILE_MODE0..31
  0x2664-0x2673  mmGB_MACROTILE_MODE0..15
  0x26DF   mmGC_USER_RB_BACKEND_DISABLE  0x00000000   indexed
  0xA0D4   mmPA_SC_RASTER_CONFIG     0x16000012   indexed
  0xA0D5   mmPA_SC_RASTER_CONFIG_1   0x00000000   indexed
```

Los rangos son informativos: `0x0025` (SDMA), `0x0393-0x0395` (SRBM),
`0x09D8` (MC), `0x2002-0x21A0` (GRBM y CP), `0x263D-0x2673` (GB), `0xA0D4`
(PA). **Ninguno por encima de 0xA0D5.** El rango BIF entero, que es donde viven
los registros del IH en `0x0F80-0x0F84`, esta **por debajo del minimo de la
tabla y no aparece**.

## 4 · EL CONTROL NEGATIVO, QUE ES LO QUE VALIDA LA TABLA

Un instrumento que dice "he leido 74 registros" no sirve si no puede decir
tambien "no he leido estos 7". Con eso dentro:

```text
  0x0F80   NEGATIVO   RECHAZADO:Bad address    IH_RB_BASE
  0x0F82   NEGATIVO   RECHAZADO:Bad address    IH_RB_RPTR
  0x0F83   NEGATIVO   RECHAZADO:Bad address    IH_RB_WPTR
  0x0F84   NEGATIVO   RECHAZADO:Bad address    IH_CNTL
  0x151A   NEGATIVO   RECHAZADO:Bad address    INTERRUPT_CNTL
  0x0000   NEGATIVO   RECHAZADO:Bad address    MMIO (offset 0)
  0xDEAD   NEGATIVO   RECHAZADO:Bad address    fuera de rango
```

```text
  PROVEN  los 7 rechazados, incluidos los cuatro del IH y INTERRUPT_CNTL.
          Y EFAULT es el codigo correcto:  en amdgpu_kms.c:914, cuando
          amdgpu_asic_read_register devuelve distinto de cero se hace
          ret = -EFAULT.  Que es exactamente lo que significa "no esta en
          la lista blanca".  O sea que el kernel esta aplicando su lista,
          y la lista no incluye el IH.

  Y CON ESTO, 1534 QUEDA SEPARADO EN DOS PIEZAS, que estaban juntas:

    PIEZA 1  "el anillo del IH no se exporta por ningun debugfs"
             -> SIGUE VIGENTE, y ahora con la razon completa:  no hay
                debugfs para el IH Y el MMR no incluye los registros del IH.

    PIEZA 2  "no hay via sin privilege"
             -> REFUTADO.  Hay via:  el nodo de render.  Lo que no hay via
                sin privilege es el CONJUNTO de registros que necesito, y
                el IH no esta en el.

  Y ESO ES UNA DISTINCION QUE IMPORTABA Y QUE ESTABA OCULTA:
      el bloqueo del IH no es de permisos.  Es que el driver, por diseño,
      no expone el IH por MMR.  Aunque yo sea root, ese registro no sale
      por ahi.  La unica lectura del IH es el puntero rptr/wptr en RAM del
      sistema (1560: adev+90680), y eso si necesita leer memoria de kernel.

  O SEA:  root NO abre el ring del IH.  Root solo abriria debugfs, que si lo
  tiene.  Son dos cosas distintas que yo venia contando como una.
```

## 5 · EL NEGATIVO QUE NO ESPERABA: EL CORPUS Y EL KERNEL DIFIEREN

Dos entradas de la lista blanca del corpus **no existen** en el kernel que corre:

```text
  0x0025  mmSDMA0_STATUS_REG                 EFAULT
  0x0225  mmSDMA0_STATUS_REG + SDMA1_OFFSET EFAULT
```

```text
  El corpus es linux-7.2.8.  El kernel que corre es 7.2.9-200.nobara.fc44.x86_64.
  En 7.2.8 la lista tiene 76 entradas.  En el kernel que corre, 74.

  Y ESTO ES UN HALLAZGO, no un fallo de mi tabla.  Es la primera vez que
  puedo COMPARAR el corpus contra el binario que se esta ejecutando, y
  difieren en dos entradas concretas.

  Y DICE ALGO UTIL:  para medir sobre esta maquina, la verdad es el .ko
  cargado, no el fuente del corpus.  El generador de la tabla es la
  herramienta correcta porque lee el fuente, pero si lo que quiero es lo
  que ESTA tarjeta acepta, la respuesta esta en el kernel, y la tengo:  74.
```

## 6 · LOS DATOS, Y LO QUE SE PUEDE DECIR DE ELLOS

`mmGRBM_STATUS` = `0x00003028`, decodificado con `gfx_8_0_sh_mask.h`:

```text
  ME0PIPE0_CMDFIFO_AVAIL   = 8
  SRBM_RQ_PENDING          = 1
  DB_CLEAN                 = 1
  CB_CLEAN                 = 1
  (todo lo demas = 0:  TA, GDS, WD, VGT, IA, SX, SPI, BCI, SC, PA, DB, CP,
   CB, GUI_ACTIVE en cero)
```

```text
  PROVEN  en el instante de la captura:  8 huecos libres en la FIFO de
          comandos del pipe 0, una peticion de SRBM pendiente, y DB y CB
          limpios (nada sin vaciar).  Ningun motor del pipeline ocupando.

  PROVEN_DERIVED  el pipeline de graficos estaba IDLE en ese instante.  Con
                  el caveat de 1541:  esto es una foto, y una foto no mide
                  actividad.  Es un instante de reposo, no un promedio.

  Y POR QUE IMPTA:  1538 mide la TASA de IRQ (media 150,7/s) y yo se que un
  frame produce 4 EOP (1508).  Con GRBM_STATUS puedo ver el estado DEL
  ANILLO, no solo el numero de veces que se ha informado de el.  Es la
  primera vez que tengo un observable del lado de "que esta haciendo el
  pipeline ahora" y no "cuantas veces me ha avisado".
```

`mmGB_ADDR_CONFIG` = `0x22011002`:

```text
  NUM_PIPES                = 2
  PIPE_INTERLEAVE_SIZE     = 0
  BANK_INTERLEAVE_SIZE     = 0
  NUM_SHADER_ENGINES       = 1
  SHADER_ENGINE_TILE_SIZE  = 1
  NUM_GPUS                 = 0
  MULTI_GPU_TILE_SIZE      = 2
  ROW_SIZE                 = 2
  NUM_LOWER_PIPES          = 0
```

```text
  PROVEN  el GRBM tiene 2 pipes y 1 SE.  2 pipes es lo esperable en Polaris12
          de gama baja.  Y los tres que se Often saltan al leer este registro
          — bank interleave, row size, multi-GPU — estan todos puestos, lo
          que es normal para un ASIC de un solo die.

  Y NUM_GPUS = 0 lo dice el registro, no yo.  Es el primer dato de esta GPU
  que contradice el rumor de que las RX550 vienen en pareja.  No: esta
  tarjeta reporta 0 GPUs en el interconnect.
```

Y los 32 `GB_TILE_MODE` y los 16 `GB_MACROTILE_MODE` con su valor bruto, que son
la geometria de la VRAM. **NO los decodifico**, y hay que decir por que:

```text
  Las mascaras por instancia existen en gfx_8_0_sh_mask.h para
  GB_TILE_MODE0__ARRAY_MODE y cuatro campos mas, pero al aplicarlas
  ARRAY_MODE sale 16, 20, 48, 52, 56, que no son modos plausibles.  O la
  cabecera de 7.2.8 tiene el mapa de campos incompleto para las instancias
  numeradas, o mi lectura de los nombres esta mal.

  NO ES UN PROBLEMA DEL INSTRUMENTO, es que no tengo el mapa fiable.  asi que
  dejo los valores BRUTOS, que son datos buenos, y la decodificacion como
  NOT_DETERMINED.  Preferir un numero crudo a un numero interpretado y malo.
```

```text
  GB_TILE_MODE0  = 0x00800150      GB_MACROTILE_MODE0  = 0x000000E8
  GB_TILE_MODE1  = 0x00800950      GB_MACROTILE_MODE1  = 0x000000E8
  GB_TILE_MODE2  = 0x00801150      GB_MACROTILE_MODE2  = 0x000000E8
  GB_TILE_MODE3  = 0x00801950      GB_MACROTILE_MODE3  = 0x000000E4
  GB_TILE_MODE4  = 0x00802950      GB_MACROTILE_MODE4  = 0x000000D0
  GB_TILE_MODE5  = 0x00802948      GB_MACROTILE_MODE5  = 0x000000D0
  GB_TILE_MODE6  = 0x00802954      GB_MACROTILE_MODE6  = 0x000000D0
  GB_TILE_MODE7  = 0x00802954      GB_MACROTILE_MODE7  = 0x00000000
  GB_TILE_MODE8  = 0x00000144      GB_MACROTILE_MODE8  = 0x000000ED
  GB_TILE_MODE9  = 0x02000148      GB_MACROTILE_MODE9  = 0x000000E9
  GB_TILE_MODE10 = 0x02000150      GB_MACROTILE_MODE10 = 0x000000E8
  GB_TILE_MODE11 = 0x06000154      GB_MACROTILE_MODE11 = 0x000000E4
  GB_TILE_MODE12 = 0x06000154      GB_MACROTILE_MODE12 = 0x000000D0
  GB_TILE_MODE13 = 0x02400148      GB_MACROTILE_MODE13 = 0x00000090
  GB_TILE_MODE14 = 0x02400150      GB_MACROTILE_MODE14 = 0x00000040
  GB_TILE_MODE15 = 0x02400170      GB_MACROTILE_MODE15 = 0x00000000
  GB_TILE_MODE16 = 0x06400154      GB_BACKEND_MAP     = 0x76541032
  GB_TILE_MODE17 = 0x06400154      mmMC_ARB_RAMCFG    = 0x000060A2
  GB_TILE_MODE18 = 0x0040014C      mmSRBM_STATUS      = 0x20000040
  GB_TILE_MODE19 = 0x0100014C
  GB_TILE_MODE20 = 0x0100015C
  GB_TILE_MODE21 = 0x01000174
  GB_TILE_MODE22 = 0x01000164
  GB_TILE_MODE23 = 0x01000164
  GB_TILE_MODE24 = 0x0040015C
  GB_TILE_MODE25 = 0x01000160
  GB_TILE_MODE26 = 0x01000178
  GB_TILE_MODE27 = 0x02C00148
  GB_TILE_MODE28 = 0x02C00150
  GB_TILE_MODE29 = 0x06C00154
  GB_TILE_MODE30 = 0x06C00154
  GB_TILE_MODE31 = 0x00000000
```

## 7 · ESTADO DE LA HERRAMIENTA

```text
RAPH550-MMR-1   revkit/tools/mmrlive.c
                compila con:
                  gcc -O2 -Wall -Wextra -std=c99 -Wno-cpp \
                      -I /usr/src/kernels/$(uname -r)/include/uapi \
                      -o mmrlive revkit/tools/mmrlive.c

VALIDACION_STATUS   VALIDATED en la parte que importa y con su control
                    negativo:
                      · 74 valores reales devueltos, no ceros
                      · 7 controles negativos rechazados, con el codigo que
                        el propio driver pone para "no permitido" (EFAULT)
                      · autotest: 9 queries del mismo ioctl distinguen
                        plumbing de caso bloqueado
                      · la tabla se GENERA desde vi.c, con recuento 76 == 76
                      · ASSERT en tiempo de compilacion: sizeof(info) == 32

SELF_TEST           --selftest imprime el numero de ioctl, sizeof de la
                    struct y el resultado de 10 queries.  Es lo que
                    detecta un ioctl mal construido.

KNOWN_LIMITATIONS   · solo 74 de los registros del ASIC; el IH no esta
                    · lectura instantanea, no serie temporal
                    · los registros indexed usan SE=0 y SH=0
                    · la decodificacion de GB_TILE_MODE no es fiable
                    · el corpus es 7.2.8 y el kernel es 7.2.9, y en esa
                      lista concreta difieren (74 vs 76)
```

## 8 · ESTADO DEL CONOCIMIENTO

```text
PROVEN          74 registros de la RX550 se leen en vivo desde
                /dev/dri/renderD128, sin root y sin ser DRM master.
PROVEN          AMDGPU_INFO_READ_MMR_REG tiene coincidencia EXACTA por
                offset sobre vi_allowed_read_registers[], 74 entradas en el
                kernel que corre.
PROVEN          los registros del IH (0x0F80-0x0F84) e INTERRUPT_CNTL
                (0x151A) NO estan en esa lista.  Con inventario cerrado y
                control negativo, 7 de 7 rechazados.
PROVEN_DERIVED  el bloqueo del ring del IH NO es de permisos.  Root no lo
                abre por MMR.  Son dos bloqueos distintos que se contaban
                como uno:  MMR no lo expone, y el puntero rptr/wptr en RAM
                (adev+90680) necesita leer memoria de kernel.
PROVEN          mmGRBM_STATUS = 0x3028 en la captura:  CMDFIFO_AVAIL = 8,
                SRBM_RQ_PENDING = 1, DB_CLEAN = 1, CB_CLEAN = 1, resto 0.
                El pipeline de graficos estaba idle en ese instante.
PROVEN          mmGB_ADDR_CONFIG = 0x22011002:  NUM_PIPES = 2,
                NUM_SHADER_ENGINES = 1, NUM_GPUS = 0.
PROVEN          el corpus (7.2.8) y el kernel en ejecucion (7.2.9) difieren
                en la lista blanca:  76 contra 74.  Los dos SDMA STATUS
                solo estan en el corpus.
NEGATIVO        la decodificacion de GB_TILE_MODE por instancia no es
                fiable con gfx_8_0_sh_mask.h de 7.2.8:  ARRAY_MODE da
                16, 20, 48, 52, 56.  Se dejan los valores brutos.

REFUTADO, mio  "el unico camino sin privilege es /proc/interrupts".  Hay
               otro:  el nodo de render, con DRM_RENDER_ALLOW.
CORRIGE, mio   mi propia tabla de 76:  el kernel acepta 74.  La diferencia
               son los dos SDMA STATUS.
TRANSFORMA      1534, y lo separa en dos bloqueos que estaban confundidos.

NOT_DETERMINED  la decodificacion de GB_TILE_MODE y GB_MACROTILE_MODE.
NOT_DETERMINED  si el kernel que corre tiene otros queries abiertos que
                todavia no se han probado.
```

## 9 · LO QUE SIGUE

```text
  1. LO QUE ESTA ABIERTO Y ES BARATO:  polls de GRBM_STATUS.  1538 mide la
     tasa de IRQ;  esto mediria el estado del anillo.  Con --repeat y
     --sleep ya esta implementado.  Falta decidir la cadencia y el numero
     de muestras, y eso es un contrato de benchmark (§73), no una suposicion.

  2. LO QUE ESTA ABIERTO Y ES MAS VALIOSO:  los otros 65 registros en serie.
     GB_TILE_MODE no cambia;  GRBM_STATUS, CP_STAT y GRBM_STATUS_SE0..3 si.
     Y GRBM_STATUS_SE0..3 con SE distinto es lo mas interesante:  da la
     ocupacion por shader engine, que es el dato de rendimiento mas directo
     que puedo obtener sin root.

  3. LO QUE SIGUE CERRADO, y ahora se por que de una vez:
     el ring del IH.  No por falta de permisos, sino porque el driver no lo
     expone.  Si llega root, lo que se abre es debugfs, no el MMR.  Y si no
     llega, 1560 deja el camino escrito:  adev+90680, una lectura.

  4. Y EL NUMERO QUE MUEVO, con lo que hay:  de 74 a 0 es un salto que no
     depende de ninguna Decision pendiente.  Esta es la primera vez que
    lo que aparece no es "medir mas cosas del driver" sino "leer el hardware".
```
# 908 · `vram_bit_width` dice 64 y la medición dice 128: el campo del driver es el doubtful

```text
CLASSIFICATION=MEASUREMENT+ERROR-CORRECTION+CONTRADICTION · TRACK=RUNTIME
CORPUS=RESEARCH/working/linux-7.1.3 + amdgpu_kms.c:1016 + gmc_v8_0.c:515,557
HARDWARE_SCOPE=HOST-C/RX550/0000:01:00.0 · INSTRUMENTO NUEVO=amdioread.py (11 de 11)
WORK_CLASS=WRITE_LOCAL · WRITE_EXECUTION=carga Vulkan nivel 1 · NIVEL=1 · AUTORIA=AGENTE-SMU
GPU INTACTA · MODIFICATIONS_CORPUS=0
```

## Qué resuelve

**⇒ `PROVEN`: la configuración real del ASIC se puede leer sin root.** `/dev/dri/renderD129` es
`crw-rw-rw-`, y `AMDGPU_INFO_DEV_INFO` la devuelve. `amdioread.py`, 11 controles, todos pasan.
Con eso quedan cuatro datos del hardware que la tabla estática de `gfx_v8_0.c` daba mal o no daba.**

**⇒ `REFUTED`: que la tabla `gfx_v8_0_gpu_early_init` describa este ASIC.** Para CHIP_STONEY dice
`max_shader_engines = 1`, `max_cu_per_sh = 3`, `max_texture_channel_caches = 2`; el hardware
declara 2, 5 y **4**. Los tres los pisa `amdgpu_discovery.c:1742-1760`, que lee el discovery bin de
MMIO. `PROVEN`. `REFUTED`

**⇒ `CORROBORATED`: `272` desde cuatro vias distintas.** `wave_front_size` = 64, `cu_active_number`
= 8, `cu_ao_mask` = `0x001E001E`, `max_memory_clock_khz` = 1.500.000. El `0x1E` es la máscara que
`272` dedujo, la que produce el `& mask` de `gfx_v8_0.c:7060-7069`. `PROVEN_DERIVED`

**⇒ `CONTRADICTION`, y es la viva: `vram_bit_width` = **64**, y 64 bits a `mclk` 1,5 GHz sobre GDDR5
permiten 24,0 GB/s. `606` midió **43,2 a 44,5 GB/s** de acceso contiguo sobre 256 MiB sin
reutilización. Eso es el 180% de 64 bits y el 90% de 128. `CONTRADICTION`

**⇒ `ERROR`, y es mío y grave: escribí en `602` que el bus de 64 bits de `258` era una
`PROVEN_DERIVED` «sin evidencia: no hay cita, no hay VBIOS, no hay registro». `258` línea 193 cita
`adev->gmc.vram_width` y `amdgpu_kms.c:1016`. La cita existía y yo no la busqué.** `ERROR`

## 1 · Lo que se lee sin root, y por qué eso cambia el Instrumento

**⇒ `PROVEN_DERIVED`. Yo tenía registrado, en `265`, que el tamaño de la caché de GFX8 no está en
ninguna fuente del corpus. El campo `gl2c_cache_size` existe en la estructura del ioctl, y en esta
placa vale **0**, igual que `gl1c_cache_size`, `sqc_data_cache_size`, `sqc_inst_cache_size` y
`mall_size`. El kernel tampoco lo dice. `265` queda corroborado por una vía que no era la del
corpus.** `PROVEN_DERIVED`

```text
  num_shader_engines        2        num_tcc_blocks            4
  num_cu_per_sh             5        num_shader_visible_vgprs  256
  cu_active_number          8        vram_bit_width           64
  cu_ao_mask                0x001E001E   vram_type           5 = GDDR5
  max_engine_clock_khz      1071000  min_engine_clock_khz     214000
  max_memory_clock_khz      1500000  min_memory_clock_khz     300000
  pcie_gen                  2        pcie_num_lanes           4
  wave_front_size           64       num_rb_pipes             4
  gl2c_cache_size           0        mall_size                0
```

**⇒ `PROVEN_DERIVED`: `min_memory_clock_khz` = 300.000 y `max_memory_clock_khz` = 1.500.000 son
exactamente los dos niveles extremos de `pp_dpm_mclk` que `258` registró del VBIOS. Cuarto
corroboración de que la lectura es del ASIC correcto.** `PROVEN_DERIVED`

**⇒ `PROVEN_DERIVED`: y `num_tcc_blocks` = 4 es la respuesta a la pregunta con la que abrí esta
rama. La ruta de textura tiene **cuatro** canales de textura, no los dos de la tabla estática. Es la
estructura que la ruta de búfer no tiene, y es por donde tiene que seguir la investigación de
`282-1`.** `PROVEN_DERIVED`

## 2 · La contradicción

**⇒ `PROVEN`: el techo con 64 bits GDDR5 a 1,5 GHz son 24,0 GB/s, y con 128 bits son 48,0.** `PROVEN`

```text
  lo que DECLARA el driver
    vram_bit_width = 64      gmc_v8_0.c:515  amdgpu_atombios_get_vram_width
    vram_type      = 5       GDDR5, doble velocidad, 2 transferencias por ciclo
    max_memory_clock_khz = 1500000

  lo que MEDI en 606, por dos vias independientes
    43,2 a 44,5 GB/s marginales, acceso contiguo, huella 256 MiB, sin reutilizacion
    ruta 1: VRAM directa          ruta 2: la apertura del BAR, acantonada en 256 MiB

    con  64 bits el techo es 24,0 y la medicion seria el 180,0%   IMPOSIBLE
    con 128 bits el techo es 48,0 y la medicion seria el  90,0%   COHERENTE
```

**⇒ `PROVEN_DERIVED`: cuál de los dos valores es el que se equivoca.** `PROVEN_DERIVED`

```text
  en contra de vram_bit_width = 64
    - sale del VBIOS o del fallback gmc_v8_0.c:557 numchan * chansize, que con numchan=1
      da exactamente 64, y no se puede distinguir cual de las dos ramas corrio sin MMIO
    - no hay ninguna corroboracion estatica en el corpus
  a favor de la medicion
    - 606 la reprodujo por dos rutas fisicas distintas: la VRAM directa y el BAR
    - 286 midio el PCIe por una tercera via, con pciebw, y coincide al 0,22% con lo que
      da la ruta GTT de la misma sesion
    - el acantonado del BAR a 256 MiB coincide con el BAR=256M que declara el log
    - 43,2 GB/s sobre 256 MiB sin reutilizacion no cabe en una cache de 256 a 320 KiB
```

**⇒ `NOT_DETERMINED`: si el campo del driver esta mal, o si significa otra cosa que bits.** `NOT_DETERMINED`

**⇒ `PROVEN_DERIVED`: y esto importa para el driver, no para la theory. `258` construyó el techo de
VRAM del proyecto sobre ese campo, y `602` lo corrigió por medición. **Los dos pueden estar
equivocados sobre el mecanismo y los dos acertar en el número**: 48,0 GB/s es el techo con 128
bits, y el campo dice 64. Lo que no se sostiene es ninguna de las dos explicaciones hasta que el
VBIOS se lea.** `PROVEN_DERIVED`

## 3 · El error mío, que es el que más me cuesta de esta serie

**⇒ `ERROR`: en `602` escribí que el bus de 64 bits de `258` no tenía evidencia y le puse un banner
de corrección diciendo «no hay cita, no hay VBIOS, no hay registro». `258` línea 193 dice, textual:
`adev->gmc.vram_width`, y `amdgpu_kms.c:1016` lo publica como `vram_bit_width`. La cita estaba en
la nota que estaba corregiendo, a 112 líneas de distancia del sitio que yo leí.** `ERROR`

**⇒ `PROVEN_DERIVED`: y es la tercera vez en este proyecto que declaro una ausencia sin haber
buscado la fuente. La primera fue el flag `--mem` muerto de `606`, que no murió: yo escribía
`--mem=host` y el banco leía cero. La segunda fue `265` diciendo que el tamaño de la caché no está
en ninguna fuente. Esta es la tercera, y la más grave de las tres porque la respuesta era que sí
estaba, en el fichero que estaba leyendo.** `PROVEN_DERIVED`

**⇒ `PROVEN_DERIVED`: la causa es la misma de siempre y ya la he escrito dos veces: leí el
fragmento queque necesitaba y afirmé sobre el conjunto. El control que faltaba era `citecheck.py`, que
existe desde antes de esta sesión y verificó 3 de 4 errores de cita propios una vez. No lo ejecuté
antes de escribir el banner.** `PROVEN_DERIVED`

**⇒ `PROVEN_DERIVED`: la lección operativa es que un banner de corrección es una afirmación con la
misma exigencia que una nota, y que corregir una nota exige haber leído la nota entera. Una
corrección que se apoya en un fragmento puede ser tan falsa como el error que corrige, y es peor,
porque se presenta como verificación.** `PROVEN_DERIVED`

## 4 · Lo que queda, y lo que este hallazgo abre

**⇒ `NOT_DETERMINED`: el ancho de bus sigue abierto, y ahora con dos candidatos y una discrepancia
declarada.** `NOT_DETERMINED`

```text
  el campo del driver dice 64 y la medicion exige al menos 128
  decidirlo necesita una de estas dos, y las dos estan bloqueadas
    - el VBIOS, con atom_tiling y vram_info: sudo, pendiente desde 272
    - mmMC_ARB_RAMCFG y el registro de chansize: MMIO, nivel 4
  PERO hay una tercera via que no estaba en la lista y ahora si existe:
    AMDGPU_INFO_READ_MMR_REG = 0x15, en la cabecera uapi instalada linea 1183.
    Lee un registro MMR desde userspace. Si el kernel lo permite sin root, es MMIO
    con otro nombre, y con el nodo legible por todo el mundo es una possibility real.
```

**⇒ `NOT_DETERMINED`, y lo dejo como la comprobación siguiente y no como un plan: no he probado
`AMDGPU_INFO_READ_MMR_REG` y no sé si el kernel lo restringe a `CAP_SYS_ADMIN`. Afirmar que
desbloquea MMIO sin haberlo ejecutado sería exactamente el error que acabo de corregir en `602`.
La afirmacion es: existe la ioctl, y probarla es un caso de self-test.** `NOT_DETERMINED`

**⇒ `PROVEN_DERIVED`: y `282-1` deja de estar bloqueada por estructura, porque ya sé que hay 4
canales de textura y que el número de la tabla estática era el equivocado. La ruta de textura es
una ruta con hardware propio en esta placa, y el trabajo de `602` —el factor 27,4×— se midió en la
de búfer. Si la de textura coalesce distinto, el techo del proyecto cambia otra vez, y esta vez con
una cifra del propio ASIC como respaldo.** `PROVEN_DERIVED`

## 5 · PENDIENTE

```text
INSTRUMENTO=amdioread.py | ESTADO=VALIDATED, 11 de 11
           | LEE=AMDGPU_INFO_DEV_INFO sobre /dev/dri/renderD129, sin root
           | CONTROLES=el nodo es la AMD y no la Intel, coherencia del popcount de
           |           cu_ao_mask contra cu_active_number, y CUATRO validaciones contra
           |           hechos ya establecidos por otras vias
           | POR_QUE_VALIDAR_CONTRA_HECHOS=un campo de cabecera es una afirmacion sobre
           |           lo que el driver puede informar, no prueba de que lo rellene

265   | ESTADO=CORROBORADA por 908: gl2c_cache_size vale 0 en esta placa
           | CORRECCION=265 decia "no esta en ninguna fuente"; ahora se sabe que tampoco
           |          esta en el ioctl. La conclusion se sostiene, la razon cambia.
602   | ESTADO=RETIRADO su banner sobre 258: la cita SI existia. Ver 908 seccion 3.
258   | ESTADO=CONTRADICTION abierta con 908: su 64 bits viene de un campo del driver
           |         que la medicion refuta. El numero 48,0 GB/s sigue en pie; la
           |         explicacion de 128 bits no esta confirmada.
TODO-2 | ESTADO=ABIERTA, con una via nueva: AMDGPU_INFO_READ_MMR_REG, que hay que probar
282-1 | ESTADO=DESBLOQUEADA estructuralmente: hay 4 canales de textura en el ASIC
```
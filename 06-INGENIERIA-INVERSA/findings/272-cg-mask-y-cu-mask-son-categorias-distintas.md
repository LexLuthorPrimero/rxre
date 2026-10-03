# 272 · `cg_mask` y `CU mask` no se contradicen: son dos categorías distintas, y la ruta que `btfq` citaba es código muerto

```text
CLASSIFICATION=CONTRADICTION_RESOLVED+MEASUREMENT · TRACK=CORPUS + RUNTIME
CORPUS=RESEARCH/working/linux-7.1.3 + evidencia/boot-amdgpu-7.1.3-200.nobara.fc44.x86_64.log
HARDWARE_SCOPE=HOST-C/RX550/0000:01:00.0
WORK_CLASS=READ_ONLY (corpus y sysfs) · NIVEL=1
MODIFICATIONS_CORPUS=0 · GPU INTACTA
```

## Qué resuelve

**⇒ Cierra la `CONTRADICTION` de `261`: «`cg_mask` lee `0xFFFFFFFFFFFFFFFF`, el estado del
proyecto dice CU mask `0x1e`». No son dos valores del mismo campo: `cg_mask` es una máscara de
banderas de clock gating y el `0x1e` es el bitmap de CUs activos del GFX. La contradicción era
de categoría semántica, no de valor.** `PROVEN`.

**⇒ `PROVEN`. La numeración de CUs de esta placa es 2 SE × 1 SH × 5 CUs presentes = 10 físicos,
de los que 4 por SH están activos = 8.** `PROVEN`.

**⇒ `REFUTED`: `btfq/cus.md` afirma que `max_cu_per_sh` viene de
`amdgpu_device.c:1848` (`gpu_info_fw->gc_num_cu_per_sh`). Esa línea no se ejecuta para
Polaris12: la función que la contiene sale por `default: return 0` porque `CHIP_POLARIS12` no
está en su `switch`.** `REFUTED`.

**⇒ `PROVEN_DERIVED`. La ruta viva es el VBIOS: `gfx_v8_0.c:1683` →
`amdgpu_atombios_get_gfx_info` → `amdgpu_atombios.c:746`, en la fase `sw_init`, que corre
antes de `hw_init`, que es donde se pregunta al hardware cuántos CUs están activos.** `PROVEN_DERIVED`.

**⇒ `PROVEN`. Y con la contradicción resuelta, el techo de cómputo queda acotado en 1088,5
GFLOPS a `sclk` 1063,02 MHz con los 8 CUs activos, o 1360,7 con los 10 presentes. Los 6304,5
GFLOPS de `270` son imposibles con cualquiera de los tres.** `PROVEN`.

## 1 · Las dos magnitudes, con su productor

**⇒ `PROVEN. Lo que sale de `sysfs` es `cg_mask`, y es clock gating.** `PROVEN`.

```text
amdgpu_drv.c:181   u64 amdgpu_cg_mask = 0xffffffffffffffff;
amdgpu_drv.c:530   DOC: cg_mask (ullong) — "Override Clockgating features"
amdgpu_drv.c:531   flags = AMD_CG_SUPPORT_*, amd_shared.h:130-163 (34 banderas)
amdgpu_device.c:2111   adev->cg_flags &= amdgpu_cg_mask;
```

**⇒ `MEASUREMENT`. En runtime: `/sys/module/amdgpu/parameters/cg_mask` =
18446744073709551615, y `/sys/module/amdgpu/parameters/pg_mask` = 4294967295. Son los valores
por defecto del código: ninguna máscara de clock gating se ha tocado.** `MEASUREMENT`.

**⇒ `PROVEN. Lo que produce el `0x1e` es el bitmap de CUs activos, y no está en ningún
`sysfs`.** `PROVEN`.

```text
gfx_v8_0.c:7067   mask = amdgpu_gfx_create_bitmask(adev->gfx.config.max_cu_per_sh);
gfx_v8_0.c:7069   return ~REG_GET_FIELD(data, CC_GC_SHADER_ARRAY_CONFIG, INACTIVE_CUS) & mask;
gfx_v8_0.c:7119   cu_info->number = active_cu_number;
amdgpu_device.c:4028-4033  dev_info(... "SE %d, SH per SE %d, CU per SH %d, active_cu_number %d")
```

**⇒ `PROVEN_DERIVED. El consumidor de `cg_mask` es `adev->cg_flags`, un `u32` de banderas de
power management; el productor del `0x1e` es `cu_info->bitmap`, un mapa de CUs del GFX. No
comparten tipo, ni consumidor, ni fase de init. Compararlos es comparar un `flags` de power
con un índice de unidad de cómputo.** `PROVEN_DERIVED`.

## 2 · El `0x1e` por programa, y por qué exige el `& mask`

**⇒ `PROVEN_DERIVED. El `0x1e` no es una constante: es el resultado de cuatro operaciones, y la
cuarta es la que `btfq` señala y el log confirma.** `PROVEN_DERIVED`.

```text
amdgpu_gfx.h:575    create_bitmask(5) = (1<<5)-1 = 0x1f
gfx_v8_0.c:7069     ~INACTIVE_CUS & 0x1f
                    el hardware marca el bit 0 como inactivo
                    ~0b...0001 = 0b...1110
                    & 0b11111    = 0b11110 = 0x1e
gfx_v8_0.c:7110     active_cu_number += counter   por SH
                    2 SE x 1 SH x 4 = 8
```

**⇒ `PROVEN`. El `& mask` de `gfx_v8_0.c:7069` está demostrado por el log, no sólo por lectura
del código: sin él, los 16 bits del campo `INACTIVE_CUS` invertidos darían entre 19 y 31 CUs
activos por SH, y `active_cu_number` sería 38 o 62. El log real dice 8.** `PROVEN`.

**⇒ `MEASUREMENT`. El log de arranque de esta placa,
`evidencia/boot-amdgpu-7.1.3-200.nobara.fc44.x86_64.log:48`:** `MEASUREMENT`.

```text
oct 02 00:10:30 kalm kernel: amdgpu 0000:01:00.0: SE 2, SH per SE 1, CU per SH 5, active_cu_number 8
```

**⇒ `PROVEN_DERIVED. Esa línea es de la máquina de este proyecto, del kernel que corre, y la
imprime el driver en `amdgpu_device.c:4028`. Los cuatro campos salen de
`adev->gfx.config` y de `cu_info.number`, que es el resultado de la cadena de §3 completa.** `PROVEN_DERIVED`.

## 3 · La cadena de descubrimiento, y por qué `btfq` sitúa la ruta equivocada

**⇒ `REFUTED`. `btfq/cus.md` dice: «`max_cu_per_sh` viene del VBIOS (`amdgpu_device.c:1848`,
`gpu_info_fw->gc_num_cu_per_sh`)». La cita es exacta pero la función no corre aquí.** `REFUTED`.

**⇒ `PROVEN`. `amdgpu_device_parse_gpu_info_fw` empieza con un `switch (adev->asic_type)`:** `PROVEN`.

```text
amdgpu_device.c:1789   switch (adev->asic_type) {
amdgpu_device.c:1790   default:
amdgpu_device.c:1791           return 0;
```

**⇒ `PROVEN_DERIVED. Los únicos casos son `CHIP_VEGA10`, `CHIP_VEGA12`, `CHIP_RAVEN`,
`CHIP_ARCTURUS`, `CHIP_NAVI12` y `CHIP_CYAN_SKILLFISH`. `CHIP_POLARIS12` no está, así que cae
en `default` y la función devuelve 0 sin tocar nada: las líneas 1847-1849, las que asignan
`max_shader_engines`, `max_cu_per_sh` y `max_sh_per_se` desde `gpu_info_fw`, son inalcanzables
para esta placa.** `PROVEN_DERIVED`.

**⇒ `PROVEN_DERIVED. La ruta que sí produce el `5` es el VBIOS, en la fase `sw_init`:** `PROVEN_DERIVED`.

```text
gfx_v8_0.c:1681-1682   case CHIP_POLARIS11: / case CHIP_POLARIS12:
gfx_v8_0.c:1683        ret = amdgpu_atombios_get_gfx_info(adev);
amdgpu_atombios.c:744  max_shader_engines = gfx_info->info.max_shader_engines;
amdgpu_atombios.c:746  max_cu_per_sh      = gfx_info->info.max_cu_per_sh;
amdgpu_atombios.c:747  max_sh_per_se      = gfx_info->info.max_sh_per_se;
```

**⇒ `PROVEN_DERIVED. Y el orden importa, y está probado por el call site, no supuesto.** `PROVEN_DERIVED`.

```text
gfx_v8_0.c:6853        .sw_init = gfx_v8_0_sw_init,
gfx_v8_0.c:6855        .hw_init = gfx_v8_0_hw_init,
amdgpu_device.c:2312   sw_init()          <- llama a gfx_v8_0_sw_init
amdgpu_device.c:2399   hw_init_phase1()
amdgpu_device.c:2407   hw_init_phase2()   <- llama a gfx_v8_0_hw_init
gfx_v8_0.c:2022        gfx_v8_0_gpu_early_init()  contiene la 1683
gfx_v8_0.c:4750        gfx_v8_0_constants_init()
gfx_v8_0.c:3734        gfx_v8_0_get_cu_info()
```

**⇒ `PROVEN_DERIVED. `sw_init` corre en `amdgpu_device.c:2312`, antes que
`hw_init_phase1` en 2399 y `hw_init_phase2` en 2407. El VBIOS fija cuántos CUs existen antes de
que el hardware diga cuántos están activos, y `create_bitmask` en `gfx_v8_0.c:7067` usa el valor
del VBIOS como ancho de máscara. Sin ese orden, la máscara sería más ancha que el silicio y el
conteo de `7110` saldría inflado.** `PROVEN_DERIVED`.

**⇒ `PROVEN_DERIVED. La cadena causal completa queda así, y cada eslabón tiene productor
identificado:** `PROVEN_DERIVED`.

```text
VBIOS (ATOM GFX_Info, tabla GFX_Info)
  -> amdgpu_atombios.c:746      max_cu_per_sh = 5
    -> amdgpu_gfx.h:575         create_bitmask(5) = 0x1f
      -> gfx_v8_0.c:7069        & ~INACTIVE_CUS  = 0x1e
        -> gfx_v8_0.c:7110      counter += 1 por bit activo  -> 4
          -> gfx_v8_0.c:7119    cu_info->number = 2 x 1 x 4 = 8
            -> amdgpu_device.c:4029   la linea del log
```

## 4 · El techo de cómputo, y por qué `270` no depende del número de CU

**⇒ `PROVEN_DERIVED. La geometría se verifica por dos campos que el driver escribe, y no por
recuerdo de la generación.** `PROVEN_DERIVED`.

```text
gfx_8_0_enum.h:6832   NUM_SIMD_PER_CU = 0x4
gfx_v8_0.c:7121       cu_info->simd_per_cu = NUM_SIMD_PER_CU
gfx_v8_0.c:7124       cu_info->wave_front_size = 64
gfx_v8_0.c:7122       cu_info->max_waves_per_simd = 10
```

**⇒ `PROVEN_DERIVED. Las lanes por SIMD no aparecen como constante en el corpus, y no hace
falta: se derivan de los dos campos que el driver sí publica, `wave_front_size / simd_per_cu`
= 64/4 = 16.** `PROVEN_DERIVED`.

**⇒ `PROVEN`. Con `sclk` = 1063020000 Hz medido en `hwmon1/freq1_input` y 2 FLOP por FMA:** `PROVEN`.

| CUs | origen | techo (GFLOPS) | 6304,5 GFLOPS es |
|---|---|---|---|
| 8 | `active_cu_number` del log real | 1088,5 | 5,8× imposible |
| 10 | 5 por SH × 2 SE, físicos | 1360,7 | 4,6× imposible |
| 16 | hipótesis alta, más de lo que lleva | 2177,1 | 2,9× imposible |

**⇒ `PROVEN_DERIVED. El `INVALID_RESULT` de `270` no queda pendiente de resolver `cg_mask`: es
imposible con cualquiera de los tres números, incluso con el 16 CU que esta placa no tiene.
Resolver la contradicción no cambia ese veredicto; lo que cambia es que ahora se puede calcular
el techo en vez de sólo acotarlo.** `PROVEN_DERIVED`.

## 5 · Lo que esta resolución desbloquea y lo que no

**⇒ `PROVEN_DERIVED. Desbloqueado: el techo de cómputo de §H es 1088,5 GFLOPS a los 8 CUs
activos. Con eso, cualquier cifra de `§52` se puede clasificar contra un número real y no contra
un orden de magnitud supuesto.** `PROVEN_DERIVED`.

**⇒ `NOT_DETERMINED`: siguen sin resolverse tres cosas, y son de tres clases distintas.** `NOT_DETERMINED`.

```text
1. por que hay 5 CUs por SH en el VBIOS y solo 4 activos:
   falta leer INACTIVE_CUS del hardware, que es MMIO. requiere nivel 4.
2. si el 5 CU inactive es una decision de silicio o de firmware de potencia:
   no lo decide el driver de referencia; el control termico vive en el firmware.
3. el "4 RB" que declara el estado maestro:
   sale de la MISMA tabla GFX_Info (amdgpu_atombios.c:748, max_backends_per_se),
   o sea del VBIOS, y no de una fuente independiente. no esta verificado.
```

**⇒ `PROVEN_DERIVED. Y hay un aviso sobre `btfq/cus.md`: su derivación del `0x1e` desde
`create_bitmask(5) & ~INACTIVE_CUS` es correcta y queda confirmada, pero su atribución del
productor a `amdgpu_device.c:1848` es falsa para esta placa. Un documento de protocolo que cita
la línea correcta del código equivocado se lee como verificado y no lo está.** `PROVEN_DERIVED`.

**⇒ `ERROR` propio de esta nota: mi primera lectura de `btfq` consistió en aceptar su cita de
`amdgpu_device.c:1848` sin comprobar el `switch` que la envuelve. La regla propia de esta
tanda —un `NOT_DETERMINED` es provisional, hay que ir a la fuente— aplica igual a una fuente
del propio proyecto: `btfq` es documentación, no evidencia, y la evidencia es el `switch` de
`amdgpu_device.c:1789-1819`.** `ERROR`.

## 6 · PENDIENTE

```text
PENDIENTE=262-1 | HALLAZGO=272-*.md | ESTADO=NOT_IMPLEMENTED
           | NECESITA=CORPUS  (kernel de ocupacion baja + accesos aleatorios)
           | ALCANZABLE_SIN_ROOT=si

CONTRADICTION=cg_mask-vs-0x1e | ESTADO=RESOLVED por esta nota
           | MOTIVO=categorias semanticas distintas; cg_mask=clock gating (u64),
           |         0x1e=cu_info->bitmap (u32), productores y consumidores distintos
```

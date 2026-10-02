# 041 · La curva A-T de GFX8: la banda de histéresis que el firmware SMU usa para cambiar de reloj

`CLASSIFICATION=DOCUMENTATION` · `TRACK=STATIC` · `WORK_CLASS=READ_ONLY/EVIDENCE`
`WRITE_EXECUTION=NONE` · `MODIFICATIONS=0` · `RUNTIME=NOT_RUN` · `GPU INTACTA`
`SCOPE_CLAIM=.write-lock/smu` · `COMPLEMENTS=040-smu-canal-mensajes-gfx8.md`

---

## CUDA principal

Entre pares adyacentes de niveles de rendimiento, el driver **no envía frecuencias**:
envía una **banda de histéresis** `[t_l, t_h]` por la que el firmware SMU decide
cuándo subir o bajar. La curva que la produce está completamente trazada y es
aritmética cerrada, sin dependencias externas.

---

## 1. El algoritmo

```
r600_calculate_at(t, h, fh, fl, *tl, *th)        si_dpm.c:3373
```

| # | línea | operación | salida |
|---|---|---|---|
| 1 | :3378 | `if (fl == 0 \|\| fh == 0 \|\| fl > fh) return -EINVAL;` | precondición |
| 2 | :3380 | `k  = (100 * fh) / fl` | ratio de frecuencias |
| 3 | :3381 | `t1 = t * (k - 100)` | desvío respecto al nominal |
| 4 | :3382 | `a  = (1000 * (100*h + t1)) / (10000 + (t1/100))` | amplitud |
| 5 | :3384 | `a  = (a + 5) / 10` | redondeo a decena |
| 6 | :3385 | `ah = ((a * t) + 5000) / 10000` | parte alta de la banda |
| 7 | :3386 | `al = a - ah` | parte baja |
| 8 | :3387 | `*th = t - ah` | umbral SUPERIOR |
| 9 | :3389 | `*tl = t + al` | umbral INFERIOR |

### Semántica

```
A-T = la banda de histéresis voltaje/frecuencia
      dentro de [tl, th] no se cambia de estado
      th = bajar de frecuencia (subir reloj)
      tl = subir de frecuencia (bajar reloj)

      t  = punto de potencia objetivo por nivel
      h  = histeresis por defecto
      fh = SCLK del nivel SUPERIOR   (performance_levels[i+1].sclk)
      fl = SCLK del nivel INFERIOR   (performance_levels[i].sclk)
```

La existencia de la banda es la razón por la que el firmware **no oscila** entre
niveles: el objetivo `t` tiene margen antes de_each transición.

---

## 2. La llamada real, con números concretos

```
si_dpm.c:5648-5653
  for (i = 0; i <= state->performance_level_count - 2; i++) {
      r600_calculate_at(
          (50 / SISLANDS_MAX_HARDWARE_POWERLEVELS) * 100 * (i + 1),   ◄ t
          100 * R600_AH_DFLT,                                          ◄ h
          state->performance_levels[i + 1].sclk,                       ◄ fh
          state->performance_levels[i].sclk,                           ◄ fl
          &t_l, &t_h);
```

Constantes medidas:

```
si_dpm.h:66     SISLANDS_MAX_HARDWARE_POWERLEVELS = 5
r600_dpm.h:29   R600_AH_DFLT = 5
```

Desarrollo:

```
t = (50 / 5) * 100 * (i+1)  =  10 * 100 * (i+1)  =  1000*(i+1)
    → 1000, 2000, 3000, ... una unidad de potencia por nivel de hardware

h = 100 * 5 = 500
```

> `50 / SISLANDS_MAX_HARDWARE_POWERLEVELS` es **división entera**: con el valor
> 5 da 10 exacto. Si el compilador cambiara el divisor a un valor no divisor de 50
> habría truncamiento. Es una fragilidad real de la expresión.

### Fallback

```
si_dpm.c:5654-5657
  if (ret) {
      t_h = (i + 1) * 1000 - 50 * R600_AH_DFLT;      ◄ banda ±250
      t_l = (i + 1) * 1000 + 50 * R600_AH_DFLT;
  }
```

Se dispara cuando la precondición falla, es decir cuando
`fl == 0 || fh == 0 || fh <= fl`. Es decir: **si los SCLK de dos niveles no
están estrictamente ordenados, el driver no aborta, degrada a banda fija ±250**.

```
AT_FALLBACK_IS_FIXED_BAND = PROVEN     ±50 * 5 = ±250 alrededor de (i+1)*1000
AT_PRECEDENCE_FAILURE_CONDITION = PROVEN   fh <= fl
```

---

## 3. Tres límites de niveles, distintos entre sí

```
si_dpm.c:5635          if (state->performance_level_count >= 9) return -EINVAL;   ◄ LÍMITE EFECTIVO
si_dpm.h:66            SISLANDS_MAX_HARDWARE_POWERLEVELS = 5                      ◄ granularidad de la curva
sislands_smc.h:30      SISLANDS_MAX_SMC_PERFORMANCE_LEVELS_PER_SWSTATE = 16        ◄ capacidad de la tabla SMC
```

**No son el mismo número y no deben confundirse:**

| constante | valor | qué significa |
|---|---|---|
| guard de `si_dpm.c` | **9** | máximo real de niveles por estado de software |
| `SISLANDS_MAX_HARDWARE_POWERLEVELS` | **5** | divisor de la granularidad de la curva A-T |
| `..._PER_SWSTATE` | **16** | capacidad de la tabla que se sube a la SRAM del SMC |

El límite efectivo es **9**, no 5 ni 16. Y con 9 niveles el bucle de la curva corre
`i = 0..7`, es decir **8 parejas adyacentes = 8 bandas**.

```
PERFORMANCE_LEVEL_LIMIT_EFFECTIVE = PROVEN  9   (si_dpm.c:5635)
AT_CURVE_PAIRS_AT_LIMIT  = PROVEN_DERIVED   8   = 9 - 1
```

---

## 4. Representación: el payload SMC es big-endian

```
96 usos de cpu_to_be32() en si_dpm.c
```

ejemplos:

```
si_dpm.c:2291   cpu_to_be32(si_scale_power_for_smc(tdp_limit, scaling_factor) * 1000)
si_dpm.c:2293   cpu_to_be32(si_scale_power_for_smc(near_tdp_limit, ...) * 1000)
si_dpm.c:2309   papm_parm->NearTDPLimitTherm = cpu_to_be32(ppm->dgpu_tdp)
si_dpm.c:2310   papm_parm->dGPU_T_Limit      = cpu_to_be32(ppm->tj_max)
si_dpm.c:5642   smc_state->levels[0].aT      = cpu_to_be32(a_t)
```

La CPU es little-endian; la tabla que se copia a la SRAM del SMC se
**byte-swappea entera**. Cualquier driver propio que escriba esas estructuras
directamente tiene que replicar la conversión, o el firmware lee basura.

```
SMC_PAYLOAD_ENDIANNESS = PROVEN   BIG_ENDIAN
  afecta a: t_l, t_h, papm_parm, spll, dte, cac, papm_cfg
  la conversión ocurre en el productor, no en copy_bytes_to_smc
```

Aparte: `si_dpm.c:5639-5643` muestra el caso degenerado de un solo nivel:

```
a_t = 0xffff << CG_AT__CG_R__SHIFT | 0 << CG_AT__CG_L__SHIFT;
smc_state->levels[0].aT = cpu_to_be32(a_t);    ◄ R = todo 1s, L = 0
```

Es decir, con un solo nivel se manda `th = 0xFFFF` y `tl = 0`: banda degenerada,
sin transición posible.

---

## 5. Lo que NO se cierra aquí

```
SMC_PACKET_LAYOUT_COMPLETO   PARTIAL
  aT está empaquetado con CG_AT__CG_R__SHIFT / CG_AT__CG_L__SHIFT
  esos macros NO están en legacy-dpm/*.h  →  búsqueda pendiente

FIRMWARE_INTERPRETATION      NOT_IN_CORPUS
  qué hace el firmware con [tl, th] no es código del driver

DVFS_TRANSITION_TIME         RUNTIME_MISSING
  cuándo se aplica realmente un cambio de nivel

CG_AT_*_SHIFT_VALUES         NOT_DETERMINED
  sin ellos no se puede decodificar un aT capturado
```

---

## 6. Fallo nominal de este bloque

| # | Busqué | Realidad | clase |
|---|---|---|---|
| 20º | `r600_calculate_at` en `r600_dpm.c` | está en `si_dpm.c:3373` | NAME |
| 21º | `CG_AT__CG_R__SHIFT` en `legacy-dpm/*.h` | no están ahí | NAME |
| 22º | `^static int si_populate_smc_sp` | es `static void` (`:5505`) | NAME |

El 22º es el más instructivo: un patrón de grep demasiado específico produjo un
cero, y el cero seotomó por ausencia de función. La función existía a 20 líneas.

```
PATTERN_TOO_SPECIFIC_AS_ABSENCE
  un grep que exige tipo + nombre + firma simultáneos
  convierte "no coincide mi patrón" en "no existe"
  → buscar el NOMBRE primero, después localizar la definición
```

---

## Desbloqueos

```
DVFS hysteresis band        PROVEN     algoritmo completo y verificable
performance level limits    PROVEN     tres límites distintos, effectif 9
SMC payload endianness      PROVEN     big-endian, 96 usos
degradation path            PROVEN     banda fija ±250 si el orden de SCLK falla
```

Siguiente pieza estática: localizar `CG_AT__CG_R__SHIFT` / `CG_AT__CG_L__SHIFT`
para poder decodificar un `aT` capturado, y con eso el formato de la banda queda
cerrado por completo.
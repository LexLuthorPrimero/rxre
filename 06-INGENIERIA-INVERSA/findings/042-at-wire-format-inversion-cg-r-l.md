# 042 · Formato de wire de la banda A-T de GFX8: los bits, el endianness y la escala

`CLASSIFICATION=DOCUMENTATION` · `TRACK=STATIC` · `WORK_CLASS=READ_ONLY/EVIDENCE`
`WRITE_EXECUTION=NONE` · `MODIFICATIONS=0` · `RUNTIME=NOT_RUN` · `GPU INTACTA`
`SCOPE_CLAIM=.write-lock/smu` · `COMPLEMENTS=041-curva-at-histeresis-dvfs-gfx8.md`

---

## CUDA principal

La banda de histéresis se escribe en **32 bits big-endian**, con dos mitades de
16 bits, y el valor de cada mitad **no es `t_l`/`t_h` sino `t * bsp / 20000`**.

Además, **los nombres de los campos están invertidos respecto a lo que sugieren**:
`CG_R` contiene el valor **bajo** y `CG_L` el **alto**. Leerlos al revés produce
una banda de histéresis espejada.

---

## 1. Los campos

```
include/asic_reg/smu/smu_6_0_sh_mask.h:26   #define CG_AT__CG_R_MASK   0x0000FFFFL
include/asic_reg/smu/smu_6_0_sh_mask.h:27   #define CG_AT__CG_R__SHIFT 0x00000000
include/asic_reg/smu/smu_6_0_sh_mask.h:28   #define CG_AT__CG_L_MASK   0xFFFF0000L
include/asic_reg/smu/smu_6_0_sh_mask.h:29   #define CG_AT__CG_L__SHIFT 0x00000010   ◄ 16
```

| campo | bits | máscara | shift | contiene |
|---|---|---|---|---|
| `CG_AT__CG_R` | 0-15 | `0x0000FFFF` | 0 | **`t_l`** — umbral INFERIOR |
| `CG_AT__CG_L` | 16-31 | `0xFFFF0000` | 16 | **`t_h`** — umbral SUPERIOR |

## 2. La inversión de nombres — el riesgo real

```
si_dpm.c:5662   a_t |= (t_l * pi->bsp / 20000) << CG_AT__CG_R__SHIFT;   ◄ t_l va a "R"
si_dpm.c:5667   ... | (t_h * high_bsp / 20000) << CG_AT__CG_L__SHIFT;   ◄ t_h va a "L"
si_dpm.c:5640   a_t = 0xffff << CG_AT__CG_R__SHIFT | 0 << CG_AT__CG_L__SHIFT;
si_dpm.c:4967   reg  = 0xffff << CG_AT__CG_R__SHIFT | 0 << CG_AT__CG_L__SHIFT;
```

`R` y `L` **no** significan Right/Left ni High/Low. La correspondencia observada es:

```
CG_R  →  t_l   (el valor LOW)
CG_L  →  t_h   (el valor HIGH)
```

Los casos degenerados lo confirman dos veces: `0xFFFF` en `CG_R` y `0` en `CG_L`
dejan `tl = 0xFFFF` y `th = 0`, es decir banda invertida por construcción
— justamente el valor "sin transición posible", que es lo que se quiere cuando
solo hay un nivel.

```
CG_FIELD_SEMANTICS_INVERTED_VS_NAME = PROVEN
  consequence: asumir CG_L = low produce una banda espejada
               y una histeresis que sube donde debe bajar
```

## 3. La unidad del valor: no es `t`, es `t * bsp / 20000`

```
si_dpm.c:5662   (t_l * pi->bsp     / 20000) << CG_AT__CG_R__SHIFT
si_dpm.c:5667   (t_h * high_bsp    / 20000) << CG_AT__CG_L__SHIFT
```

El umbral calculado por `r600_calculate_at` **no va crudo al registro**. Se
reescala por `bsp` y se divide por 20000.

```
bsp  = mantisa del PLL, CALCULADA en software por r600_calculate_u_and_p()
si_dpm.c:4259   r600_calculate_u_and_p(pi->asi,  xclk, 16, &pi->bsp,  &pi->bsu);
si_dpm.c:4265   r600_calculate_u_and_p(pi->pasi, xclk, 16, &pi->pbsp, &pi->pbsu);
si_dpm.c:4272   pi->dsp = (pi->bsp << CG_BSP__BSP__SHIFT) | (pi->bsu << CG_BSP__BSU__SHIFT);
si_dpm.c:4274   pi->psp = (pi->pbsp<< CG_BSP__BSP__SHIFT) | (pi->pbsu<< CG_BSP__BSU__SHIFT);
si_dpm.c:4275   WREG32(mmCG_BSP, pi->dsp);      ◄ el driver ESCRIBE, no lee
```

> **CORRECCION (turno posterior).** Una versión anterior de este documento decía
> que `bsp` "proviene de un registro CG". Es falso: `bsp` se **calcula** en
> software y luego se **escribe** a `mmCG_BSP`. El registro es un destino, no un
> origen. Ver `043-...`.

```
bsp NO SE LEE DE HARDWARE = PROVEN
  es salida de r600_calculate_u_and_p(asi, xclk, 16, ...) y entrada de dos
  consumidores distintos: mmCG_BSP y el escalado de las bandas A-T
```

### Caso especial del nivel superior

```
si_dpm.c:5664-5665
  high_bsp = (i == state->performance_level_count - 2) ? pi->pbsp : pi->bsp;
```

La **última pareja** de niveles usa `pbsp` en lugar de `bsp`. La penúltima banda
de histéresis usa una base de escalado distinta.

```
AT_TOP_LEVEL_USES_PBSP = PROVEN
  solo para i == performance_level_count - 2
```

## 4. El ciclo read-modify-write

```
si_dpm.c:5661   a_t = be32_to_cpu(smc_state->levels[i].aT) & ~CG_AT__CG_R_MASK;
si_dpm.c:5662   a_t |= (t_l * pi->bsp / 20000) << CG_AT__CG_R__SHIFT;
si_dpm.c:5663   smc_state->levels[i].aT = cpu_to_be32(a_t);
```

No sobrescribe la palabra entera: **conserva los 16 bits altos** y solo replaces
los bajos. Después escribe el resultado de vuelta big-endian. El campo alto lo
establece el paso siguiente (`:5667`) sobre `levels[i+1]`.

Es un **encadenamiento entre niveles**: el nivel `i` recibe `t_l`, y el mismo
bucle escribe `t_h` en el nivel `i+1`. Un nivel es a la vez "high" de la pareja
anterior y "low" de la siguiente.

```
AT_LEVELS_CHAINED = PROVEN
  levels[i].CG_R   = t_l de la pareja (i, i+1)
  levels[i+1].CG_L = t_h de esa misma pareja
  → los dos lados de una banda viven en registros de niveles DISTINTOS
```

## 5. Cadena completa, de la política al registro

```
pl (sclk por nivel)
  │
  ├─ si_populate_smc_t()                          si_dpm.c:5625
  │    :5635   if (performance_level_count >= 9) return -EINVAL;
  │    :5648   r600_calculate_at(t = 1000*(i+1), h = 500, fh, fl)  → t_l, t_h
  │    :5654   if (ret)  banda fija ±250
  │    :5661   a_t = be32_to_cpu(...aT) & ~CG_R_MASK        ◄ lee y preserva
  │    :5662   a_t |= (t_l * bsp     / 20000) << 0          ◄ bits 0-15
  │    :5663   levels[i].aT   = cpu_to_be32(a_t)            ◄ a big-endian
  │    :5667   levels[i+1].aT = cpu_to_be32(0xFFFF<<0 | (t_h*high_bsp/20000)<<16)
  │
  ├─ si_populate_smc_sp()                         si_dpm.c:5505
  ├─ amdgpu_si_copy_bytes_to_smc()                si_smc.c:53
  └─► SRAM del SMC ─► mensaje por mmSMC_MESSAGE_0 (0x94) ─► FIRMWARE
```

Todo el camino es `READ_ONLY` en el corpus; ninguna escritura a hardware desde el
driver: el último paso real es la subida a SRAM.

---

## 6. Lo que queda abierto

```
FIRMWARE_A_T_INTERPRETATION   NOT_IN_CORPUS   qué hace el firmware con [tl, th]
SMC_PACKET_TOTAL_LAYOUT      PARTIAL         conocido el campo aT; el resto no
CG_BSP__BSP__SHIFT_VALUE     NOT_DETERMINED  no localizado aún
bsp EN TIEMPO REAL            NOT_DETERMINED  es software-calculado; lo que falta
                                             es el valor de xclk en runtime
DVFS_TRANSITION               RUNTIME_MISSING
```

---

## 7. Fallos nominales de este bloque

| # | Busqué | Realidad |
|---|---|---|
| 23º | `CG_AT__CG_R__SHIFT` en `legacy-dpm/*.h` | está en `asic_reg/smu/smu_6_0_sh_mask.h` |
| 24º | `CG_R` = "high" por el nombre | es **low** — inversión probada |

El 23º es la **sexta** vez que un subdirectorio sin inventariar produce un falso
negativo. El inventario completo del driver es:

```
drivers/gpu/drm/amd/
  amdgpu/            304 .c
  include/asic_reg/  gca/  gc/  gmc/  mmhub/  smu/   ◄ el que faltaba
  pm/                legacy-dpm/  powerplay/  swsmu/  ◄ el que faltaba
```

```
SUBDIRECTORY_INVENTORY_GATE   ya merece ser norma, no sugerencia
  antes de escribir NAME_NOT_FOUND sobre este driver:
  enumerar amdgpu/ + asic_reg/* + pm/*
```

---

## Valor para el driver propio

Para escribir la banda A-T correctamente hace falta, en este orden:

1. calcular `t_l` / `t_h` con la curva de `r600_calculate_at` (o la banda fija ±250)
2. **calcular** `bsp` con `r600_calculate_u_and_p(asi, xclk, 16, ...)`, y `pbsp`
   con `pasi` en lugar de `asi` para la última pareja — no leerlo
3. escalar: `valor = t * bsp / 20000`
4. empaquetar **mitad alta = `t_h`, mitad baja = `t_l`** — invertido respecto al nombre
5. encadenar: `levels[i].bajos = t_l`, `levels[i+1].altos = t_h`
6. byte-swappear a big-endian

Omitir el paso 6, o invertir el paso 4, produce una tabla que el firmware acepta
pero ejecuta al revés. Ninguna de las dos cosas la detecta el driver.
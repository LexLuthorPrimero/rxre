# 044 · `xclk`: cinco caminos de reloj, dos leídos del hardware, y dos constantes heredadas

`CLASSIFICATION=DOCUMENTATION` · `TRACK=STATIC` · `WORK_CLASS=READ_ONLY/EVIDENCE`
`WRITE_EXECUTION=NONE` · `MODIFICATIONS=0` · `RUNTIME=NOT_RUN` · `GPU INTACTA`
`SCOPE_CLAIM=.write-lock/smu`
`COMPLEMENTS=043-pll-bsp-asi-pasi.md`

---

## CUDA principal

El reloj de referencia del PLL (`xclk`) **no es un valor fijo**. Tiene cinco
caminos, y **dos de ellos se leen de registros de hardware en tiempo de
ejecución**. No se puede hardcodear.

Y la otra mitad del par, `asi` / `pasi`, **sí** son constantes — pero heredadas
de ASICs de otra generación.

---

## 1. El despacho

```
amdgpu.h:1382   #define amdgpu_asic_get_xclk(adev) (adev)->asic_funcs->get_xclk((adev))
```

Diez implementaciones distintas. Para GFX8 es `vi_get_xclk`, registrada en
`vi.c:1434` (`.get_xclk = &vi_get_xclk`).

```
xclk_DISPATCH = PROVEN   macro → asic_funcs->get_xclk → vi_get_xclk
```

## 2. Los cinco caminos

```
vi_get_xclk(adev)                                     vi.c:539
   :540   reference_clock = adev->clock.spll.reference_freq;   ◄ del VBIOS
   :542   if (adev->flags & AMD_IS_APU) {
   :545       case CHIP_STONEY:
   :546           /* vbios says 48Mhz, but the actual freq is 100Mhz */
   :547           return 10000;                        ◄ OVERRIDE HARDCODEADO
   :548       default:
   :549           return reference_clock;              ◄ el VBIOS
          }
   :551   tmp = RREG32_SMC(ixCG_CLKPIN_CNTL_2);       ◄ LECTURA DE HARDWARE
   :552   if (REG_GET_FIELD(tmp, CG_CLKPIN_CNTL_2, MUX_TCLK_TO_XCLK))
   :553       return 1000;                              ◄ TCLK multiplexado
   :555   tmp = RREG32_SMC(ixCG_CLKPIN_CNTL);
   :556   if (REG_GET_FIELD(tmp, CG_CLKPIN_CNTL, XTALIN_DIVIDE))
   :557       return reference_clock / 4;              ◄ cristal / 4
   :558   return reference_clock;                      ◄ el VBIOS
```

| # | condición | origen | valor |
|---|---|---|---|
| 1 | APU Stoney | constante | `10000` |
| 2 | APU resto | VBIOS | `reference_freq` |
| 3 | `MUX_TCLK_TO_XCLK` | **hardware** | `1000` |
| 4 | `XTALIN_DIVIDE` | **hardware** | `reference_freq / 4` |
| 5 | ninguno | VBIOS | `reference_freq` |

```
XCLK_HARDWARE_DEPENDENT = PROVEN
  caminos 3 y 4 dependen de registros strapeados del ASIC
  ⇒ el divisor de PLL no es calculable sin leer el hardware
```

### El acceso es al banco del propio SMU

```
RREG32_SMC(ixCG_CLKPIN_CNTL_2)
RREG32_SMC(ixCG_CLKPIN_CNTL)
```

`_SMC` = banco de registros accesible al SMC. Es el mismo subsistema que
documenta `040`. El reloj de referencia del PLL y el canal de mensajes viven en
el mismo espacio de registros.

### La unidad

```
vi_get_xclk devuelve 10000 para un reloj real de 100 MHz
amdgpu_kms.c:948   gpu_counter_freq = amdgpu_asic_get_xclk(adev) * 10;
```

```
XCLK_UNIT = PROVEN_DERIVED   10 kHz
  10000 unidades = 100 MHz      y ×10 = 100000 kHz = 100 MHz  (coherente)
```

## 3. El upstream admite que el BIOS miente

```
vi.c:546   /* vbios says 48Mhz, but the actual freq is 100Mhz */
```

Documentado en el propio código: el VBIOS declara 48 MHz donde el hardware
real corre a 100 MHz, y el driver lo compensa con un `return` hardcodeado.

```
VBIOS_UNRELIABLE_BY_DRIVER_ADMISSION = PROVEN
  el campo clock.spll.reference_freq no es garantía de la frecuencia real
```

Es un argumento directo a favor de **medir en vez de copiar** cualquier valor de
reloj heredado del upstream.

## 4. Las dos constantes del otro extremo

```
si_dpm.h:42   #define RV770_ASI_DFLT     1000
si_dpm.h:43   #define CYPRESS_HASI_DFLT  400000

si_dpm.c:7519   pi->asi  = RV770_ASI_DFLT;
si_dpm.c:7520   pi->pasi = CYPRESS_HASI_DFLT;
```

| campo | constante | nominal | se usa para |
|---|---|---|---|
| `asi` | `RV770_ASI_DFLT` | R600-era | `bsp` — divisor del reloj principal |
| `pasi` | `CYPRESS_HASI_DFLT` | Cypress (HBM) | `pbsp` — nivel superior de la banda A-T |

**Ninguna se lee del ASIC.** Son constantes compiladas.

```
PLL_BASE_CONSTANTS_ARE_LEGACY_INHERITED = PROVEN
  asi  viene de RV770    (generación anterior a GCN)
  pasi viene de Cypress (SOC15-era, posterior)
  y se usan en GFX8 sin validación
```

Es la **asimetría más importante del scope**: el numerador del divisor PLL se
**calcula** en cada ejecución a partir de hardware y BIOS, pero su multiplicador
base es una constante asumida desde hace generaciones.

### Consecuencia práctica

`r600_calculate_u_and_p(i, r_c, p_b, ...)` computa `i_c = (i * r_c) / 100`. Con
`i = asi = 1000` y `r_c = xclk`:

```
i_c = 10 * xclk
```

`asi = 1000` es exactamente **10·100**, es decir el resultado queda multiplicado
por 10 respecto al reloj. No es un valor de frecuencia en el mismo sentido que
`xclk`: es un **factor de escala con unidades propias**.

```
ASI_UNIT_DIFFERS_FROM_XCLK = PROVEN_DERIVED
  el producto i * r_c / 100 solo tiene sentido si i es un factor adimensional
  tratado como frecuencia;  asi = 1000 y pasi = 400000 no son MHz
```

Consecuencia para el driver propio: **no tratar `asi` como una frecuencia**. Es un
constante de escalado cuyo significado no está documentado en el corpus.

## 5. Cadena completa hasta el registro

```
reference_freq (VBIOS)  ─┐
RREG32_SMC(CG_CLKPIN*)  ─┼─► xclk
constante Stoney        ─┘
asi (1000) ───────────────┐
pasi (400000) ─────────────┼─► r600_calculate_u_and_p(., xclk, 16)
                           │       i_c = (i * xclk) / 100
                           │       u   = (bitlen(i_c >> 16) + 1) / 2
                           │       p   = i_c / (1 << (2u))
                           ▼
                    bsp, bsu  /  pbsp, pbsu
                           │
              ┌────────────┴────────────┐
              ▼                         ▼
      mmCG_BSP = bsp|bsu<<16      t * bsp / 20000  (banda A-T)
```

## 6. Lo que queda abierto

```
clock.spll.reference_freq   origen   NOT_READ    quién lo parsea del VBIOS
ixCG_CLKPIN_CNTL_2 / CNTL   lectura  RUNTIME_MISSING  valor real de la placa
XCLK_UNIT_CONFIRMATION       PROVEN_DERIVED  por coherencia con kms.c:948
asi / pasi  significado       NOT_DETERMINED  no documentados más allá del nombre
```

## 7. Fallos nominales

| # | Busqué | Realidad |
|---|---|---|
| 26º | `pi->asi =` en `amdgpu/` | el campo está en `pm/legacy-dpm/`, y es una **constante** copiada en init |
| 27º | `define.*asi` en `amdgpu/*.h` | está en `pm/legacy-dpm/si_dpm.h:42` |

Los dos por buscar en el subdirectorio equivocado. Séptima y octava vez.

---

## Veredicto para el driver propio

```
METER, no copiar:
  1. xclk           leer de CG_CLKPIN_CNTL* — dos caminos son de hardware
  2. reference_freq Vinegar del BIOS, y saber que miente (Stoney, 48 vs 100)
  3. asi / pasi     verificar las constantes heredadas contra el ASIC real
                    antes de confiar en el divisor que producen

El único valor de esta cadena que el driver puede copiar sin medir es
`p_b = 16`, que es un parámetro de formato y no una constante de hardware.
```
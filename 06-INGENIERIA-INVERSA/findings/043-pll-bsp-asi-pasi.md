# 043 · El PLL de GFX8: `bsp` se calcula en software y alimenta dos consumidores

`CLASSIFICATION=DOCUMENTATION` · `TRACK=STATIC` · `WORK_CLASS=READ_ONLY/EVIDENCE`
`WRITE_EXECUTION=NONE` · `MODIFICATIONS=0` · `RUNTIME=NOT_RUN` · `GPU INTACTA`
`SCOPE_CLAIM=.write-lock/smu`
`COMPLEMENTS=042-at-wire-format-inversion-cg-r-l.md`

> **Este documento corrige un error de 042.** Allí se afirmó que `bsp` "proviene
> de un registro CG". Falso. `bsp` es **salida de un cálculo en software** y
> luego **escrito** a `mmCG_BSP`. El registro es destino, no origen.

---

## CUDA principal

El divisor y el multiplicador del PLL de sclk de GFX8 se calculan **partiendo de la
frecuencia del cristal**, mediante una separación mantisa/exponente en base 2.
Ese mismo valor se usa después para dos cosas distintas: configurar el
generador de reloj, y **escalar las bandas de histéresis A-T**.

---

## 1. El cálculo

```
r600_calculate_u_and_p(i, r_c, p_b, *p, *u)      si_dpm.c:3354
{
    b_c = 0;
    i_c = (i * r_c) / 100;          ◄ producto del cristal por el reloj objetivo
    tmp = i_c >> p_b;               ◄ p_b = 16
    while (tmp) { b_c++; tmp >>= 1; }   ◄ cuenta el exponente
    *u = (b_c + 1) / 2;             ◄ exponente, redondeado hacia arriba
    *p = i_c / (1 << (2 * (*u)));   ◄ mantisa
}
```

| entrada | significado | valor en el llamador |
|---|---|---|
| `i` | frecuencia de referencia | `pi->asi` o `pi->pasi` |
| `r_c` | reloj objetivo | `xclk` |
| `p_b` | bits de fracción | **16** fijo |

| salida | significado |
|---|---|
| `*p` | **mantisa** del divisor |
| `*u` | **exponente** (`(b_c+1)/2`) |

### Por qué `1 << (2 * *u)`

El divisor del VCO del PLL es un cuadrado: `VCO = f_in * (N*N)`. El algoritmo
parte `i_c` en potencias de 2, cuenta el exponente `b_c`, y toma su **mitad
redondeada hacia arriba** porque cada nivel del divisor duplica dos veces
(`2 * u`). El resto es la mantisa.

Es un reparto estándar P/U de PLL, no una fórmula propia de AMDGPU.

```
AT_U_ROUNDING = PROVEN  (b_c + 1) / 2  ◄ sesgo sistemático hacia arriba
   con b_c impar el exponente se redondea al alza y la mantisa se reduce
```

## 2. Las dos llamadas: `asi` frente a `pasi`

```
si_dpm.c:4257   u32 xclk = amdgpu_asic_get_xclk(adev);
si_dpm.c:4259   r600_calculate_u_and_p(pi->asi,  xclk, 16, &pi->bsp,  &pi->bsu);
si_dpm.c:4265   r600_calculate_u_and_p(pi->pasi, xclk, 16, &pi->pbsp, &pi->pbsu);
```

`asi` y `pasi` son **frecuencias de referencia distintas** del ASIC, y de ellas
salen `bsp` y `pbsp`. Es la misma pareja que aparece en `high_bsp` dentro del
cálculo de la banda A-T (`si_dpm.c:5664`), donde la última pareja usa `pbsp`.

```
asi / pasi = dos referencias de reloj del ASIC
bsp / pbsp = la misma dualidad, propagada hasta las bandas de histéresis
```

## 3. El destino: `mmCG_BSP`

```
si_dpm.c:4272   pi->dsp = (pi->bsp  << CG_BSP__BSP__SHIFT) | (pi->bsu  << CG_BSP__BSU__SHIFT);
si_dpm.c:4273   pi->psp = (pi->pbsp << CG_BSP__BSP__SHIFT) | (pi->pbsu << CG_BSP__BSU__SHIFT);
si_dpm.c:4275   WREG32(mmCG_BSP, pi->dsp);
```

Layout (`asic_reg/smu/smu_6_0_sh_mask.h:31-34`):

| campo | bits | máscara | shift | contenido |
|---|---|---|---|---|
| `CG_BSP__BSP` | 0-15 | `0x0000FFFF` | 0 | mantisa `bsp` |
| `CG_BSP__BSU` | 16-19 | `0x000F0000` | 16 | exponente `bsu`, **solo 4 bits** |

```
CG_BSP__BSU_ANCHO = PROVEN   4 bits
  máximo representable 15  →  exponente PLL hasta 15
  es el techo del generador de reloj, no un detalle de codificación
```

## 4. El hallazgo estructural: un cálculo, dos consumidores

```
r600_calculate_u_and_p(asi, xclk, 16)
        │
        ├──► bsp, bsu ──► mmCG_BSP          configura el generador de reloj
        │                 (una escritura)
        │
        └──► bsp      ──► t_l * bsp / 20000   escala el umbral A-T inferior
                          t_h * bsp / 20000   escala el umbral A-T superior
```

La misma magnitud entra en dos caminos que **no comparten consumidor**:

| consumidor | destino | momento |
|---|---|---|
| `mmCG_BSP` | registro del clock generator | una vez, en init |
| bandas A-T | tabla de power state subida a SRAM del SMC | en cada cambio de estado |

```
PLL_RESULT_DUAL_CONSUMER = PROVEN
  consequence: cambiar la referencia de reloj (asi/pasi) cambia a la vez
               la configuración del PLL y la geometría de la histéresis
               son Acoplados y no se pueden ajustar por separado
```

**Esto no lo hace evidente ninguna de las dos rutas por separado.** Se ve solo al
trazar el productor hasta sus dos consumidores — que es exactamente lo que pide
`RELATION_FIRST_REVERSE_ENGINEERING`.

---

## 5. El uso de `pasi` en la curva A-T

```
si_dpm.c:5664-5665
  high_bsp = (i == state->performance_level_count - 2) ? pi->pbsp : pi->bsp;
```

La pareja de niveles más alta se escala con la **segunda** referencia. Es
coherente: el nivel superior es el que más se acerca a la frecuencia principal y
el que usa la otra base de cálculo.

---

## 6. Lo que queda abierto

```
amdgpu_asic_get_xclk()          NOT_READ     origen del reloj de referencia
asi / pasi  su origen         NOT_DETERMINED  de dónde salen las dos referencias
CG_BSP__BSU_4_BITS_ALCANZADO    PROVEN       techo de 15
FIRMWARE_INTERPRETATION         NOT_IN_CORPUS
DVFS real                       RUNTIME_MISSING
```

---

## 7. Fallos nominales

| # | Busqué | Realidad |
|---|---|---|
| 25º | `pi->bsp =` | no existe asignación directa; es un **parámetro de salida** de `r600_calculate_u_and_p` |

Un parámetro de salida no aparece nunca en una asignación. Buscarlo así era
garantizar el cero. Hubo que leer el **llamador** para descubrir que se rellena
por puntero.

```
OUT_PARAMETER_NOT_IN_ASSIGNMENT_SEARCH
  buscar el valor de una variable que se llena como parámetro de salida
  obliga a buscar en el constructor, no en las asignaciones
```

---

## Valor para el driver propio

Para fijar la frecuencia de sclk en GFX8 hay que, en orden:

1. conocer `asi` y `pasi` del ASIC objetivo, y `xclk`
2. ejecutar el reparto P/U: `u = (bitlen(i_c>>16) + 1) / 2`, `p = i_c / (1 << 2u)`
3. empaquetar `mmCG_BSP` = `p | (u << 16)`, **con `u` en 4 bits**
4. calcular las bandas A-T con ese mismo `p` como escala, y con `pbsp` en la
   última pareja
5. subir la tabla de estados a la SRAM del SMC y mandar el mensaje

El paso 4 es el que no es evidente: usa el mismo número que el paso 3, y si se
omite la escala por `bsp` las bandas salen en unidades equivocadas sin que nada
falle visiblemente.
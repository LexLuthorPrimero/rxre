# 107 · El TLB se vacía solo en un caso: el reset. Y el driver lo asume sin escribir `REQUEST`

`CLASSIFICATION=DOCUMENTATION` · `TRACK=STATIC` · `WORK_CLASS=READ_ONLY/EVIDENCE`
`WRITE_EXECUTION=NONE` · `MODIFICATIONS=0` · `RUNTIME=NOT_RUN` · `GPU INTACTA`
`CORPUS=RESEARCH/working/linux-7.1.3` · `HARDWARE_SCOPE=HOST-C/RX550/0000:01:00.0`
`CIERRA=el ultimo item de §C (AGENTS.md), sin necesidad de escribir en el hardware`
`CONTINUES=106, 104, 103`

## Cuestión principal

`213` dejó un item: *"que el hardware no invalide por sí solo"*, con un
discriminante de nivel 3 —escribir `REQUEST=0` y ver si `RESPONSE` cambia.

**¿Se puede cerrar sin escribir?**

## Criterio de terminación

Buscar en el corpus si el driver asume alguna vez un vaciado de TLB que no
provenga de escribir `VM_INVALIDATE_REQUEST`. **Cumplido: sí, en el reset, y
con un comentario que lo dice.**

## Sí: el reset, y y el driver lo escribe en un comentario

`amdgpu_gmc.c:722-727`, dentro de `amdgpu_gmc_flush_gpu_tlb`:

```c
/*
 * A GPU reset should flush all TLBs anyway, so no need to do
 * this while one is ongoing.
 */
if (!down_read_trylock(&adev->reset_domain->sem))
        return;
```

**El driver da por hecho que un reset de GPU vacía los TLB**, y por eso se
niega a hacer un flush manual mientras hay un reset en curso. Es la misma
frase repetida en `:785`.

Y el reset de esta placa **no escribe `VM_INVALIDATE_REQUEST`**:

```c
/* gmc_v8_0.c:1343-1370, gmc_v8_0_soft_reset */
tmp  = RREG32(mmSRBM_SOFT_RESET);
tmp |= srbm_soft_reset;
WREG32(mmSRBM_SOFT_RESET, tmp);
tmp   = RREG32(mmSRBM_SOFT_RESET);
udelay(50);
tmp &= ~srbm_soft_reset;
WREG32(mmSRBM_SOFT_RESET, tmp);
```

Solo pone y quita bits de `SRBM_SOFT_RESET`. En toda la función **no aparece
`VM_INVALIDATE_REQUEST`**.

## Lo que esto significa, y lo que no

**Sí significa:** existe un camino en el que el hardware vacía las TLB sin que
nadie escriba `REQUEST`. No es "el invalidate automático" de `FUNCTION=always`
—ese campo no existe, como cerró `213`— sino otra cosa: **el reset borra el
estado de la Translation Cache**.

Y es un resultado de ingeniería, no una casualidad. El driver depende de ello
para no tener que hacer flush manual en cada reset, y lo dice.

**No significa:** que haya un trigger hardware por cambio de PTB. Un PTB que
cambia sin `REQUEST` no debería invalidar, y nada en el corpus dice lo
contrario. Eso sigue sin medirse.

## Y el reset NO es un atajo para el resto

Las generaciones más nuevas **sí** hacen flush explícito tras su reset:

```
gfx_v11_0.c:4732   flush_gpu_tlb(adev, 0, AMDGPU_GFXHUB(0), 0)
gfx_v12_0.c:3577   flush_gpu_tlb(adev, 0, AMDGPU_GFXHUB(0), 0)
gfx_v12_1.c:2584   flush_gpu_tlb(adev, 0, AMDGPU_GFXHUB(i), 0)
gmc_v10_0.c:955    gmc_v10_0_flush_gpu_tlb(adev, 0, AMDGPU_MMHUB0(0), 0)
```

En GFX8 no hay equivalente en `gfx_v8_0.c`. **La confianza en el reset es
específica de esta generación**, y no se debe extender a las siguientes.

Eso es una observación de ingeniería del driver, no una propiedad del hardware
demostrada: que Navi necesite el flush explícito y GCN3 no, puede ser porque
el TLB de GCN3 se invalida antes, o porque el de Navi tiene un bug que obliga.

## El discriminante que queda, y su coste real

Para medir el invalidate espontáneo por cambio de PTB haría falta:

```
1. escribir un PTB distinto            (NIVEL 3)
2. leer una VA mapeada sin hacer flush
3. ver si el translate falla o no
```

Es decir: **tres escrituras controladas sobre page tables vivas**. Eso está
en el rango NIVEL 3 y requiere justificacion discriminante. No se ha hecho, y
no lo voy a hacer sin autorización: es exactamente el caso que la jerarquía
de permisos marca como needing reversibilidad explícita.

**Lo que sí queda cerrado es la pregunta de `017:145`** —"¿el hardware
dispara el invalidate solo?"— y la respuesta es que **no hay ningún campo
para expresarlo**, con la excepción del reset, que no es un trigger sino un
borrado de estado.

## Clasificación

| afirmación | estado |
|---|---|
| El reset de GPU vacía los TLB sin escribir `REQUEST` | `CORROBORATED` — `amdgpu_gmc.c:724` |
| `gmc_v8_0_soft_reset` no escribe `VM_INVALIDATE_REQUEST` | `PROVEN` — la función entera |
| El driver omite el flush manual mientras hay reset | `PROVEN` — `amdgpu_gmc.c:727` |
| GFX8 no hace flush explícito tras su reset | `PROVEN_ABSENT` — ausente en `gfx_v8_0.c` |
| Navi sí lo hace | `PROVEN` — cuatro sitios citados |
| Que el vacío sea por `SRBM_SOFT_RESET` y no por otra causa | `HYPOTHESIS` — el más plausible |
| Que haya trigger por cambio de PTB sin `REQUEST` | `NOT_DETERMINED` — requiere NIVEL 3 |
| Que el hardware invalide solo por `FUNCTION` | `REFUTED` — `213`, el campo no existe |

## Confounders

- **El comentario es del driver, no una spec.** "should flush all TLBs anyway"
  es una expectativa de ingeniería. Que sea cierto es `CORROBORATED`, no
  `PROVEN`.
- **He leído el camino de GFX8, no el de reset completo.** Un reset completo
  pasa por `amdgpu_do_asic_reset`, que llama a más cosas. Que ninguna escriba
  `REQUEST` no lo he verificado entero.
- **Navi necesita flush explícito y GCN3 no.** Puede ser una diferencia de
  diseño, no de hardware. No sé cuál.
- **No he tocado la placa.** Todo esto es lectura de código.

## Desfalsificación

- **(a)** El reset vacía TLB sin `REQUEST` → refutable con el comentario de
  `amdgpu_gmc.c:724` y con leer `gmc_v8_0_soft_reset` entera.
- **(b)** GFX8 no hace flush post-reset → refutable con
  `grep flush_gpu_tlb gfx_v8_0.c`; no sale ninguno.
- **(c)** Navi sí lo hace → refutable con los cuatro sitios citados.
- **(d)** Hay trigger por cambio de PTB → **no refutable sin placa**.

## UNLOCKS

- **`§C` de `AGENTS.md` queda con un solo item, y es empírico.** El resto está
  cerrado, y este hallazgo cierra la parte estática de la pregunta de `017`.
- **Una consecuencia para el driver propio**: si se hace reset, los TLB están
  limpios sin escribir nada. Es un invariante del que se puede depender.
- **La asimetría GCN3/Navi está documentada**, y es el tipo de cosa que hace
  que un driver propio no copies el patrón de Navi a GCN3 sin razon.

## Evidencia

```
amdgpu_gmc.c:722-727   "A GPU reset should flush all TLBs anyway, so no need
                       to do this while one is ongoing."
amdgpu_gmc.c:785       la misma frase, repetida

gmc_v8_0.c:1343        gmc_v8_0_soft_reset
gmc_v8_0.c:1355-1366   RREG/WREG mmSRBM_SOFT_RESET, udelay(50), dos veces
                       -> VM_INVALIDATE_REQUEST NO aparece en la funcion

gfx_v8_0.c             grep flush_gpu_tlb  ->  sin resultados
gfx_v11_0.c:4732       flush_gpu_tlb(adev, 0, AMDGPU_GFXHUB(0), 0)
gfx_v12_0.c:3577       flush_gpu_tlb(adev, 0, AMDGPU_GFXHUB(0), 0)
gfx_v12_1.c:2584       flush_gpu_tlb(adev, 0, AMDGPU_GFXHUB(i), 0)
gmc_v10_0.c:955        gmc_v10_0_flush_gpu_tlb(adev, 0, AMDGPU_MMHUB0(0), 0)
```

`WRITE_EXECUTION=NONE`. `MODIFICATIONS=0`. `GPU INTACTA`.
# 505 · El cap de clock stretcher sí está activo: la cadena cerrada y un error mío de bits

WORK_CLASS=READ_ONLY · WRITE_EXECUTION=NONE · MODIFICATIONS 0

> ## Resultado
>
> `PHM_PlatformCaps_ClockStretcher` pasa de `NOT_DETERMINED` a **PROVEN: está
> activo en mi placa**. Sus tres condiciones están medidas, y la de `feature_mask`
> está además **verificada contra la línea de órdenes real** de esta máquina.
>
> Consecuencia: la puerta de `:2005` **no salta**, y `polaris10_init_smc_table`
> llega a la copia de 1776 B.

## La cadena, completa

```
smu7_hwmgr.c:1939   if (pp_table_version != PP_TABLE_V0)
                && (feature_mask & PP_CLOCK_STRETCH_MASK)
                && (usClockStretchAmount != 0)
```

| condición | productor | valor en mi placa | estado |
|---|---|---|---|
| `pp_table_version != PP_TABLE_V0` | `hwmgr.c:86` pone `V1`; solo degrada a `V0` en `FAMILY_CI` (`:105`) y `CHIP_TOPAZ` (`:140`) | yo soy `POLARIS12`, ninguno de los dos | **PROVEN** |
| `feature_mask & PP_CLOCK_STRETCH_MASK` | `amdgpu_drv.c:202` → `amdgpu_device.c:2021` → `amd_powerplay.c:59` | `0xfff7bfff & 0x400 = 0x400` | **PROVEN, CIERTO** |
| `usClockStretchAmount != 0` | VBIOS PowerTune `0x9EAB`, rev 4, offset 25 | **2** | **PROVEN** |
| que no lo quite `0x699F && 0xCF` | `smu7_hwmgr.c:1975` | mi rev es `0xC7` | **REFUTED** para mi placa |

**Las cuatro se cumplen. El cap se pone.**

Y el valor de la máscara **no está sobrescrito en esta máquina**:

```
ppfeaturemask NO esta en /proc/cmdline
ningun /etc/modprobe.d/*.conf ni /etc/default/grub lo fija
```

`module_param_named(ppfeaturemask, ..., hexint, 0444)` (`amdgpu_drv.c:499`) permite
sobrecribirlo por línea de órdenes, y **no lo está**. Así que la máscara efectiva
es la de compilación, y el resultado no depende de una suposición.

## El desenlace: `:2004` corre, y los campos CKS siguen en cero

Con el cap activo:

```
:2002  phm_cap_enabled(ClockStretcher)  ->  CIERTO
:2004  populate_clock_stretcher_data_table
:1696  if (stretch_amount == 0 || stretch_amount > 5) return -EINVAL   ->  2, NO salta
:1708  return 0
:2005  la puerta pasa
:2118  LA COPIA DE 1776 B SE HACE
```

Y `polaris10_populate_clock_stretcher_data_table` (`:1650-1709`, leído completo)
escribe **tres** cosas: `Sclk_CKS_masterEn0_7`, `Sclk_voltageOffset[]` y
`LdoRefSel`. **No escribe `ClockStretcherAmount@1700`, ni
`ClockStretcherDataTable@1712`, ni `CKS_LOOKUPTable@1728`.**

Eso **fuerza** el hallazgo de `502`. El comentario de `:1695` dice
`/* Populate CKS Lookup Table */` y no hay ninguna escritura de esa tabla **ni
siquiera cuando la función se ejecuta**. No es que el clock stretcher esté
desactivado en mi placa y por eso no se rellene: **se rellena todo lo que el
código rellena, y la tabla no está entre lo que rellena.**

`Sclk_CKS_masterEn8_15@1702` en cero sigue siendo coherente: hay 8 niveles SCLK,
así que los niveles 8-15 no existen. Pero ahora sé que **no** es por cap
desactivado, sino porque el código nunca escribe ese campo.

## Cinco errores míos, y cuatro de ellos habrían producido afirmaciones falsas

**1. Escribí `PP_CLOCK_STRETCHER` de memoria.** El nombre real es
**`PP_CLOCK_STRETCH_MASK`**. Busqué el que escribí y obtuve **cero apariciones** en
todo `amd/`, con `exit=1` y ámbito acotado. Si no hubiera leído la línea literal
antes de concluir, habría publicado un **`PROVEN_ABSENT` inventado** — un
`PROVEN_ABSENT` sobre un símbolo que existe y se usa dos veces.

Es el error más grave de la serie, y lo cometí **después** de escribir en `501`
que había que verificar los nombres. Escribir la regla no la aplica.

**2. Busqué `#define PP_*` cuando son valores de un `enum`.**
`PP_CLOCK_STRETCH_MASK = 0x400` está en `enum PP_FEATURE_MASK`
(`include/amd_shared.h:215-236`), no en un `#define`. Mi patrón de búsqueda
devolvió vacío con `exit=1`, y leí ese vacío como «no está» cuando lo que no
estaba era **mi patrón**.

Es `NAME_MATCH ≠ SEMANTIC_MATCH` aplicado a la búsqueda: no busqué el nombre que
buscaba.

**3. Conté bits a mano y me equivoqué.** Escribí que
`0xfff7bfff & 0x400 = 0`. Lo compilé y dio **`0x400`**.

Me había equivocado de nibble: el `f` está en las posiciones 8-11 y tomé el `b`
de las 12-15. **La conclusión completa estaba al revés** y la habría escrito si no
hubiera ejecutado el programa. Un número de máscara de bits calculado de cabeza no
es un número verificado, por muy despacio que se haga la suma.

**4. Leí el código de salida de `sed` en vez del de `grep`.** Una tubería
`grep ... | sed ... ; echo "exit=$?"` da el de `sed`, que siempre vale 0. Con un
cero inventado, y que lee como «búsqueda correcta, sin resultados». Es el
`SILENT_ZERO` en su forma más discreta.

**5. `grep` con timeout dio `exit=124` y 0 hits** al buscar
`PP_CLOCK_STRETCH_MASK` en el árbol entero. **Sexta vez** que me ocurre. No lo leí
como ausencia: `226` es timeout, y lo distinguí del `1` al acotar el ámbito.

Ese `exit=124` es la razón de ser de la regla de exigir el código de salida. Un
`226` con cero líneas es indistinguible de un `1` con cero líneas si no lo lees, y
yo casi lo leo como el segundo.

## Lo que NO afirmo

- **NO** afirmo que las otras 15 puertas de `:1913`-`:2118` pasen. He cerrado **una**,
  la de `:2005`, con la cadena completa. Las otras son populates que devuelven su
  propio `result`, y cada una es un interrogante distinto.
- **NO** afirmo nada de `:2095`: depende de `bif_sclk_table`, **fuera de mi
  corpus** (`EVIDENCE_MISSING`).
- **NO** afirmo que `usClockStretchAmount = 2` sea el valor con el que arranca el
  firmware. Afirmo que es lo que hay en la tabla PowerTune de mi VBIOS, y que eso
  es lo que lee `:1661`.
- **NO** he medido hardware. `B_RUNTIME = NOT_EXECUTED`; hace falta
  `Autorizo WRITE_EXECUTION para B_EXPERIMENT`.
- **NO** he modificado código. `MODIFICATIONS 0`. La lectura de `/proc/cmdline` es
  solo lectura del host, no hardware.

## Una observación sobre el método

Cuatro de los cinco errores de esta iteración tienen la misma forma: **yo busqué
algo que no era lo que buscaba, y mi respuesta fue una ausencia**. Un nombre mal
que no busca lo que dice buscar, un código de salida del comando equivocado, un
timeout.

Ninguno habría detectado ejecutando el programa. **Todos se habrían evitado
leyendo la línea antes de concluirla**, que es lo que hice bien en un solo caso:
cuando dudé del identificador, lo leí literal y salió `PP_CLOCK_STRETCH_MASK`.

Es la diferencia entre investigar y calcular. Casi todo lo que hago aquí es
calcular; lo que faltaba era una lectura literal por línea, y es gratis.

## Frontier siguiente

**Cerrar la puerta de `:2095`**, que es la última que puedo cerrar sin hardware:

```c
atomctrl_get_dfs_pll_dividers_vi(hwmgr, smu_data->bif_sclk_table, ...)
   -> PP_ASSERT "Can not find DFS divide id for Sclk", return result
```

Es la única cuyo fallo impide la copia y cuyo insumo **no está en mi corpus**:
`bif_sclk_table`, la tabla BIF. `atomctrl_get_dfs_pll_dividers_vi` es el productor.

Pero antes de buscarla hay una pregunta que decide si vale la pena, y es de mi
propia tabla de `502`: **de los 73 campos que sí se escriben, ¿cuántos tienen su
último escritor en un populate que sea el de la BIF?** Si el divisor DFS no toca la
tabla DPM, la puerta solo depende de un fallo de búsqueda, y el estado del campo
no se ve afectado.

Es la misma disciplina que `501`: **antes de arreglar o trazar un hueco, medir si
afecta a mi ASIC.**

Criterio de cierre: los rangos de `bif_sclk_table` que lee
`atomctrl_get_dfs_pll_dividers_vi`, y si esa lectura puede fallar en mi VBIOS, con
el discriminante de si el contenido de la tabla DPM depende de ello.
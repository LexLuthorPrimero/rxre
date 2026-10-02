# 087 · §F: el kernel imprime la versión y la implementación, y no coinciden en 4 de 5

```
CLASSIFICATION=DOCUMENTATION · TRACK=STATIC + HOST_OBSERVATION
CORPUS=RESEARCH/working/linux-7.1.3 · HARDWARE_SCOPE=HOST-C/RX550/0000:01:00.0
WORK_CLASS=READ_ONLY/EVIDENCE · WRITE_EXECUTION=NONE · MODIFICATIONS=0
RUNTIME=OBSERVED_READ_ONLY · GPU INTACTA
```

## Qué resuelve

`065` cerró la geometría de la VM context pero dejó un `NOT_DETERMINED`: **qué
versión de GMC es esta**. Lo había marcado porque dos cabeceras de máscaras
daban la misma región con offsets distintos (`0x500-0x578` en `gmc_8_1_sh_mask.h`,
`0xb60-0xba1` en MMHUB), y había concluido que "el `#include` decide".

**El `#include` no alcanza.** Hace falta saber qué bloque de IP se instancia en esta
GPU, y hay tres candidatos en el mismo fichero.

## La observación que lo cierra

`amdgpu_ip.c:241-245` imprime la versión y la implementación de cada bloque al
arrancar. En esta máquina:

```
detected ip block number 0 <common_v1_0_0>  (vi_common)
detected ip block number 1 <gmc_v8_1_0>     (gmc_v8_0)
detected ip block number 2 <ih_v3_0_0>      (tonga_ih)
detected ip block number 3 <gfx_v8_0_0>     (gfx_v8_0)
detected ip block number 4 <sdma_v3_1_0>    (sdma_v3_0)
detected ip block number 5 <smu_v1_0_0>     (powerplay)
detected ip block number 6 <dce_v1_0_0>     (dm)
detected ip block number 7 <uvd_v6_3_0>     (uvd_v6_0)
detected ip block number 8 <vce_v3_4_0>     (vce_v3_0)
```

**`<gmc_v8_1_0>`** — el GMC de esta GPU es **8.1.0**. `065` cerrado por observación,
no por lectura.

Y el corchete a la derecha hace algo que ningún fichero del corpus documenta:
**el kernel imprime a propósito las dos cosas, la versión declarada y el nombre
de la implementación, y aquí no coinciden.**

## Por qué GMC 8.1 y no 8.0 ni 8.5

```
vi.c:2105   case CHIP_POLARIS10:
vi.c:2106   case CHIP_POLARIS11:
vi.c:2107   case CHIP_POLARIS12:
vi.c:2108   case CHIP_VEGAM:
vi.c:2109       amdgpu_device_ip_block_add(adev, &vi_common_ip_block);
vi.c:2110       amdgpu_device_ip_block_add(adev, &gmc_v8_1_ip_block);
```

Y los tres bloques de GMC del fichero comparten implementación:

```
gmc_v8_0.c:1760   gmc_v8_0_ip_block = { .type = AMD_IP_BLOCK_TYPE_GMC,
gmc_v8_0.c:1763                                    .minor = 0,
gmc_v8_0.c:1765                                    .funcs = &gmc_v8_0_ip_funcs, };
gmc_v8_0.c:1768   gmc_v8_1_ip_block = { .type = AMD_IP_BLOCK_TYPE_GMC,
gmc_v8_0.c:1771                                    .minor = 1,
gmc_v8_0.c:1773                                    .funcs = &gmc_v8_0_ip_funcs, };
gmc_v8_0.c:1776   gmc_v8_5_ip_block = { .type = AMD_IP_BLOCK_TYPE_GMC,
gmc_v8_0.c:1779                                    .minor = 5,
gmc_v8_0.c:1781                                    .funcs = &gmc_v8_0_ip_funcs, };
```

**Los tres `.funcs` son el mismo puntero.** Por eso `067` y `086` sobreviven:
`gmc_v8_0.c:411-423`, `:520-567`, `:595` son el código que corre en esta GPU,
aunque se llame `v8_0`.

## Un resultado negativo que importa

`GMC_HWIP` **no existe** en este kernel. El enum es:

```
amdgpu_ip.h:32    enum amd_hw_ip_block_type {
amdgpu_ip.h:33        GC_HWIP = 1,
amdgpu_ip.h:34        HDP_HWIP,
...
amdgpu_ip.h:63        UMC_HWIP,
amdgpu_ip.h:71        MAX_HWIP
```

No hay `GMC_HWIP`. Verificado por tres vías independientes: el enum, y
`grep -rl 'GMC_HWIP'` sobre todo `*.c` y `*.h` de `amdgpu/` → **0 ficheros**.

**Consecuencia**: la versión de GMC **no es consultable** por
`amdgpu_ip_version()`. No hay ranura en `ip_versions[]` donde metarla, porque la
población se hace con `adev->ip_versions[GC_HWIP][0] = IP_VERSION(9, 0, 0)`
y para GMC no existe tal índice.

El patrón de los tres bloques GMC es *etiqueta de versión, implementación
compartida*. La versión se **imprime** y se **guarda como puntero**
(`amdgpu_ip.c:249`), pero no se **ramifica por versión**: `gmc_v8_0.c` no
contiene ni una referencia a `GMC_HWIP` ni a `ip_version(adev, ...)`.

## De paso: el empaquetado de `IP_VERSION` (verifica `085`)

```
amdgpu_ip.h:79    #define IP_VERSION(mj, mn, rv) IP_VERSION_FULL(mj, mn, rv, 0, 0)
amdgpu_ip.h:80    #define IP_VERSION_MAJ(ver)    ((ver) >> 24)
amdgpu_ip.h:82    #define IP_VERSION_REV(ver)    (((ver) >> 8) & 0xFF)
amdgpu_ip.h:84    #define IP_VERSION_SUBREV(ver) ((ver) & 0xF)
amdgpu.h:1214         /* This considers only major/minor/rev and ignores
amdgpu.h:1215          * subrevision/variant fields.
amdgpu.h:1217         return adev->ip_versions[ip][inst] & ~0xFFU;
```

El byte bajo es `variant<<4 | subrev`, y `& ~0xFFU` lo descarta. El comentario
de `amdgpu.h:1214-1215` **sí es correcto**.

`IP_VERSION(8,0,0) = 0x08000000` y `IP_VERSION(9,0,0) = 0x09000000`, así que la
comparación de `amdgpu_vm.c:1157` que usa `085` es una comparación de major. La
conclusión de `085` queda **verificada a nivel de macro**, no solo de lectura.

## El resultado medido: 4 de 5 divergen

De los 9 bloques, sólo 5 son comparables (misma base y mismo convenio de nombre;
los otros 4 usan otra convención: `common/vi_common`, `ih/tonga_ih`,
`smu/powerplay`, `dce/dm`):

| bloque (versión) | implementación | minor | ¿coincide? |
|---|---|---|---|
| `gmc_v8_1_0` | `gmc_v8_0` | 1 vs 0 | **NO** |
| `gfx_v8_0_0` | `gfx_v8_0` | 0 vs 0 | sí |
| `sdma_v3_1_0` | `sdma_v3_0` | 1 vs 0 | **NO** |
| `uvd_v6_3_0` | `uvd_v6_0` | 3 vs 0 | **NO** |
| `vce_v3_4_0` | `vce_v3_0` | 4 vs 0 | **NO** |

**4 de 5 divergen. La única que coincide es GFX.**

Y eso es lo grave. Todo el trabajo de esta investigación se apoya en
`gfx_v8_0.c` — leí `gfx_v8_0.c:6191-6215` (`068`), `:7131-7133` (`085`), `084`.
Y `gfx_v8_0_0` corre `gfx_v8_0`, que es **el único caso donde la regla del
nombre acierta**. La regla funcionó en todos los controles que hice porque sólo
la puse a prueba donde era cierta.

**Es sesgo de superviviente, y casi se convierte en un error real**: si en
cualquier momento hubiera affirmed "el fichero se llama igual que su versión",
habría dicho bien sobre GFX y mal sobre todo lo demás.

## Impacto sobre hallazgos existentes

| hallazgo | qué dice | ¿afectado? |
|---|---|---|
| `067` | GART = 256 MiB, `gmc_v8_0.c:595` | **No** — 8.1 corre `gmc_v8_0_ip_funcs` |
| `086` | geometría de VRAM, `gmc_v8_0.c:414-423` | **No** — mismo `.funcs` |
| `068` | orden de emisión, `gfx_v8_0.c:6191-6215` | **No** — versión 8.0.0 coincide |
| `085` | flush obligatorio, `amdgpu_vm.c:1157` | **No** — `GC_HWIP` sí existe |
| `074` | `GEN_PTEPDE`, `sdma_v3_0.c:952-997` | **Sí, anotación**: el bloque es **3.1**, no 3.0 |

`074` es el único que necesita una nota: **la cita al fichero sigue siendo
correcta**, porque `sdma_v3_1_ip_block.funcs = &sdma_v3_0_ip_funcs` — pero la
versión del hardware es 3.1. Un driver propio que asuma 3.0 porque el fichero
se llama `sdma_v3_0.c` está assumiendo mal.

## Lo que NO cierra

| Afirmación | Estado |
|---|---|
| GMC de esta GPU = 8.1.0 | `OBSERVED` (log) + `PROVEN` (`vi.c:2110`) |
| 8.0/8.1/8.5 comparten `.funcs` | `PROVEN` (`gmc_v8_0.c:1765,1773,1781`) |
| `GMC_HWIP` no existe | `PROVEN` (enum + 0 ficheros) |
| La versión de GMC no se ramifica en el fichero | `PROVEN` (0 referencias) |
| `IP_VERSION` empaqueta major en el byte 3 | `PROVEN` (`amdgpu_ip.h:80-84`) |
| Por qué `.minor` 5 existe sin código propio | `NOT_DETERMINED` |
| Si el hardware GMC difiere entre 8.1 y 8.5 | `NOT_DETERMINED` — no se ramifica, así que el driver **no lo consulta** |

**La quinta fila es la que pesa para un driver propio**: si el driver tiene
tres etiquetas de versión y un solo cuerpo de código, o las tres son el mismo
hardware, o **el driver está Ignoring una diferencia que existe**. El corpus no
lo dice, y no se puede determinar por lectura. Es un `NOT_DETERMINED` honesto.

## Procedencia

- `STATIC` — `vi.c:2105-2114`, `gmc_v8_0.c:1760-1782`,
  `amdgpu_ip.c:221-252`, `amdgpu_ip.h:32-85`, `amdgpu.h:1211-1218`.
- `HOST_OBSERVATION` — `journalctl -k -b`, sólo lectura.
- Encadenada con `065` (la cierra), `067`/`086` (sobreviven), `074` (anotación),
  `085` (verificada a nivel de macro).
- No se editó `AGENTS.md` ni `OPEN-FRONTIERS.md`: son de otras sesiones.

**Dos notas de método, porque las dos fueron errores míos.**

La primera: publiqué un `9 de 9 divergen, 100%` y era **falso**. Mezclaba dos
convenios de nombre distintos (`common_v1_0_0` frente a `vi_common` no son
comparables). Y el script tenía además un bug de índice de grupo: leía
`group(2)`, que es *major*, donde debía leer `group(3)`, que es *minor* — así
que la columna llegó a decir `gfx_v8_0_0: 0 vs 8`. Dos errores en una tabla
pequeña, ambos de *no mirar la salida antes de interpretarla*.

La segunda: el texto de este archivo se me colaron dos ideogramas CJK al
escribir. Se detectaron al comprobar el artefacto y se corrigieron
antes de publicar. Es la sexta vez que el CJK se cuela en la escritura
y la comprobacion posterior es lo unico que lo detiene.
entré al escribir. Se detectaron al comprobar el artefacto y se corrigieron
antes de publicar. Es la sexta vez que el CJK se cuela en la escritura y la
comprobación posterior lo es lo único que lo detiene.
---

# CORRECCION POSTERIOR — el rango se pasa por 6 líneas

Este documento **no se reescribe**. Lo que sigue corrige un rango de
procedencia. La afirmación **no cambia** y es verificable en el árbol declarado.

## Lo que se corrige

La sección `Procedencia` cita `gmc_v8_0.c:1760-1782`. **El fichero tiene 1776
líneas en 7.2.8**, así que el final del rango se pasa por seis.

## Lo que NO cambia, y queda verificado

La afirmación que la cita respalda es que *«los tres bloques de GMC del
fichero comparten implementación»*. Se lee entera en 7.2.8:

```
gmc_v8_0.c:1762   const struct amdgpu_ip_block_version gmc_v8_1_ip_block = {
gmc_v8_0.c:1763       .type = AMD_IP_BLOCK_TYPE_GMC,
gmc_v8_0.c:1764       .major = 8,  .minor = 1,  .rev = 0,
gmc_v8_0.c:1765       .funcs = &gmc_v8_0_ip_funcs,
gmc_v8_0.c:1770   const struct amdgpu_ip_block_version gmc_v8_5_ip_block = {
gmc_v8_0.c:1771       .type = AMD_IP_BLOCK_TYPE_GMC,
gmc_v8_0.c:1772       .major = 8,  .minor = 5,  .rev = 0,
gmc_v8_0.c:1773       .funcs = &gmc_v8_0_ip_funcs,
```

El rango correcto es **`gmc_v8_0.c:1758-1776`**. Los tres bloques —`gmc_v8_0`,
`gmc_v8_1`, `gmc_v8_5`— apuntan a `gmc_v8_0_ip_funcs`, que es exactamente lo que
este hallazgo afirma. La cita iba bien; el final se pasó.

## Cómo se encontró

`tools/treescope.py`, que separa `FUERA_DE_RANGO` de
`FUERA_DE_RANGO_PERO_RESUELVE_EN_OTRO`. Esta segunda clase es la que importa: un
fichero que **existe** en el árbol declarado pero cuya línea no, puede estar
citando el otro árbol. La primera versión de la herramienta devolvía
`FUERA_DE_RANGO` en cuanto encontraba el fichero, y por eso se le escapaba esa
diferencia. Corregido, y al corregirlo apareció `126-g-el-precio-de-la-coherencia.md:123`,
que sí cita 7.1.3 sin declararlo.

`CORRECTED_BY=087-CORRECCION-POSTERIOR`.

# 019 · ATC en GFX8: L1/L2 separados, invalidación explícita sólo en registros DEBUG

`CLASSIFICATION=DOCUMENTATION` · `TRACK=STATIC` · `CORPUS=rx550-upstream-7.2.8/linux-7.2.8`
`WORK_CLASS=READ_ONLY/EVIDENCE` · `WRITE_EXECUTION=NONE` · `MODIFICATIONS=0`
`CONTINUES=017-vm-invalidate-gfx8-function-always.md, 018-execution-order-invalidacion-gfx8.md`


> **CORRECTED_BY=030** (2026-10-01). La tabla de `block_size` de esta sección está mal:
> los valores correctos son **22/23/24**, no 13/14/15. `amdgpu_vm_get_block_size()` recibe
> `tmp = roundup_pow_of_two(max_pfn)`, no `vm_size`, y eso cambia la rama del cálculo.
> La conclusión de esta sección —que `block_size` depende de la RAM del host y no del
> siliconio— **sigue siendo correcta**. No se reescribe el texto: `AGENTS.md` §Documentación
> prohíbe sobrescribir evidencia histórica. Ver `030-page-walker-gfx8-2-niveles.md`.

## CUDA principal

En GFX8 el `VM_INVALIDATE_REQUEST` no tiene granularidad: 16 bits, un bit por VMID, y
nada más. No existen selectores `INVALIDATE_L1_PTES` / `INVALIDATE_L2_PTES` /
`INVALIDATE_4K_PAGES_ONLY` — GFX9+ los tiene y el driver los pone a 1 todos. En GFX8 la
pregunta "qué nivel de TLB invalido" no tiene encoding: **se invalida el dominio entero o
nada**, y la granularidad no es una elección del software.

Corolario para el driver propio: `flush_type` y `vmhub` en la interfaz GFX8 son
parámetros muertos. `gmc_v8_0_flush_gpu_tlb` los recibe y los descarta.

## Alcance exacto

1. Barrer `gmc_8_2` completo por los registros de control de ATC/L1/L2 (READ_SCOPE_GATE).
2. Determinar si existe invalidación explícita de L1/L2 separada de `0x51e`.
3. Verificar si `0x51e` tiene granularidad en GFX8, y en GFX9+ para contraste.
4. Clasificar la fila que `017 §5` dejó como `NOT_OBSERVED`.

## Criterio de terminación (cumplido con una salvedad)

Los 63 registros `mmATC_*` de `gmc_8_2_d.h` fueron enumerados (`grep -c "^#define mmATC_"`
= 63) y clasificados por nombre: 39 de traducción (`L1*`, `L2*`, `VMID*`, `MISC_CG`) y 24
de otro tipo (7 perfcounter, 12 ATS, 6 aperture). Resolví los campos `sh_mask` de los 39
de traducción más `ATC_VM_APERTURE0_CNTL`.

**Salvedad, y es una corrección al alcance que declaré**: no resolví los campos de los 24
restantes. La afirmación "ninguno queda sin leer" sería falsa. Los 7 perfcounter y los 12
ATS quedan fuera por no ser de traducción; los 6 de aperture (`mmATC_VM_APERTURE{0,1}_*`)
sí son de traducción — definen el modo de acceso ATS de cada aperture — y los dejé como
`PARTIAL`. Cerrarlos es la acción siguiente y no bloquea la conclusión de §3, que se
sostiene sólo en `VM_INVALIDATE_REQUEST` y en los `sh_mask` que sí leí.

---

## 1 · Barrido completo de ATC en `gmc_8_2`

`grep -c "^#define mmATC_" gmc_8_2_d.h` → **63**. Los que gobiernan traducción:

| Registro | Offset | Bits de control | ¿Alguien lo escribe? |
|---|---|---|---|
| `mmATC_MISC_CG` | `0xcd4` | `ENABLE`, `MEM_LS_ENABLE` | sí — clock gating, `gmc_v8_0.c:1523/1560/1603/1639` |
| `mmATC_L2_CNTL` | `0xcd5` | contadores de requests de traducción | **no** |
| `mmATC_L2_CNTL2` | `0xcd6` | `L2_CACHE_UPDATE_MODE` (bits 6-7), `L2_CACHE_VMID_MODE` (12-14) | **no** |
| `mmATC_L2_DEBUG` | `0xcd7` | selectores de banco/way/index de la caché L2 | **no** |
| `mmATC_L2_DEBUG2` | `0xcd8` | `INVALIDATE_ALL` bit 9, `FORCE_CACHE_MISS` bit 8, `DISABLE_2M_CACHE` bit 10, `EFFECTIVE_CACHE_SIZE` bits 0-4 | **no** |
| `mmATC_L1_CNTL` | `0xcdc` | `NEED_ATS_BEHAVIOR`, `NEED_ATS_SNOOP_DEFAULT` | **no** |
| `mmATC_L1_ADDRESS_OFFSET` | `0xcdd` | `LOGICAL_ADDRESS` 32 bits | **no** |
| `mmATC_L1RD_DEBUG_TLB` | `0xcde` | **`INVALIDATE_ALL` bit 30**, `DISABLE_INVALIDATE_BY_ADDRESS_RANGE` bit 1, `DISABLE_FRAGMENTS` bit 0 | **no** |
| `mmATC_L1WR_DEBUG_TLB` | `0xcdf` | idéntico a L1RD | **no** |
| `mmATC_L1RD_STATUS` | `0xce0` | `BUSY` bit 0, `DEADLOCK_DETECTION` bit 1 | **no** |
| `mmATC_L1WR_STATUS` | `0xce1` | idéntico | **no** |
| `mmATC_L1RD_DEBUG2_TLB` | `0xce2` | — | **no** |
| `mmATC_L1WR_DEBUG2_TLB` | `0xce3` | — | **no** |
| `mmATC_VMID_PASID_MAPPING_UPDATE_STATUS` | `0xce6` | `VMID{n}_REMAPPING_FINISHED` ×16 | sí — KFD, `amdgpu_amdkfd_gfx_v8.c:102-104` |
| `mmATC_VMID{0..15}_PASID_MAPPING` | `0xce7..0xcf6` | `PASID` 16 bits, `NO_INVALIDATION` bit 30, `VALID` bit 31 | sí — KFD, `amdgpu_amdkfd_gfx_v8.c:100` |

`grep -rn "ATC_L1RD_DEBUG_TLB\|ATC_L1WR_DEBUG_TLB\|ATC_L2_DEBUG2\|ATC_L2_CNTL\|ATC_L1_CNTL" amdgpu/*.c`
→ **0 resultados**.

Qué ATC toca el path GFX8, con recuento por fichero:

| Fichero | Registros ATC | Operación |
|---|---|---|
| `gmc_v8_0.c` (9 sitios) | `mmATC_MISC_CG` | R/W, clock gating (`:1523/1560/1603/1639`) + tabla init `:112` |
| `gmc_v8_0.c:627` | `mmATC_VMID0_PASID_MAPPING + vmid` | **sólo lectura**, en `gmc_v8_0_flush_gpu_tlb_pasid` |
| `gfx_v8_0.c:372` | `mmATC_MISC_CG` | tabla de init, sólo el valor `0x000c0200` |
| `amdgpu_amdkfd_gfx_v8.c` | `mmATC_VMID0_PASID_MAPPING + vmid` (R/W `:100`), `mmATC_VMID_PASID_MAPPING_UPDATE_STATUS` (R/W `:102/104`) | KFD, no el path de ring |

Corrección a la redacción de esta sección: dije "el driver GFX8 escribe 4 registros".
Cuenta por **entradas de código**, no por registros distintos, y además el cuarto es
`VMID_PASID_MAPPING_UPDATE_STATUS` más los 16 `VMID{n}_PASID_MAPPING` que en el código
aparece como una sola expresión con `+ vmid`. Formulado sin el error: el path GFX8 escribe
**dos** registros ATC (`MISC_CG`, y la tabla `VMID{n}_PASID_MAPPING` desde KFD) y **lee**
uno (`VMID{n}_PASID_MAPPING` en el flush por pasid). Ninguno es un registro de control de
caché de traducción.

## 2 · L1 de lectura y L1 de escritura son caches separados

Esto es un hecho estructural, no una interpretación. GFX8 tiene **dos** L1 de traducción:

```
mmATC_L1RD_DEBUG_TLB   0xcde    INVALIDATE_ALL  bit 30 (MASK 0x40000000)
mmATC_L1WR_DEBUG_TLB   0xcdf    INVALIDATE_ALL  bit 30 (MASK 0x40000000)
mmATC_L1RD_STATUS      0xce0    BUSY, DEADLOCK_DETECTION, BAD_NEED_ATS, CAM_PARITY_ERRORS, CAM_INDEX
mmATC_L1WR_STATUS      0xce1    (idénticos)
```

Sus campos son bit a bit idénticos (`gmc_8_2_sh_mask.h:5957-6012`), lo que confirma que son
el mismo tipo de estructura en dos instancias. `mmATC_L2_CNTL` cuenta por separado
`NUMBER_OF_TRANSLATION_READ_REQUESTS` (bits 0-1) y
`NUMBER_OF_TRANSLATION_WRITES_DEPENDS_ON_ADDR_MOD` (bit 9): el hardware distingue lectura de
escritura.

GFX9+ no tiene esta separación: `MMVM_INVALIDATE_ENG0_REQ` es un único registro por
motor, con `INVALIDATE_L1_PTES` / `INVALIDATE_L2_PTES` / `INVALIDATE_L2_PDE0..2`.

**Consecuencia para `NO_HISTORICAL_INHERITANCE`**: una implementación que aplique el modelo
de GFX9+ a GFX8 está aplicando una estructura que no existe. La caché L2 que GFX9 invalida
con un bit, en GFX8 son dos L1 más una L2 (`mmATC_L2_CNTL2__L2_CACHE_VMID_MODE`) y el
invalidate es de dominio completo.

## 3 · `0x51e` no tiene granularidad

```
gmc_8_2_sh_mask.h: VM_INVALIDATE_REQUEST__*   → 32 coincidencias
                   VM_INVALIDATE_RESPONSE__*  → 32 coincidencias
```

32 = 16 `REQUEST` (bits 0-15) + 16 `RESPONSE` (bits 0-15). Un bit por VMID en cada lado.
Cero campos de granularidad.

Contraste, GFX9 (`mmhub_3_0_0_sh_mask.h:5845-5864`):

```
PER_VMID_INVALIDATE_REQ      MASK 0x0000FFFF   bits 0-15   ← el mismo mapa de 16 VMIDs
FLUSH_TYPE                   MASK 0x00070000   bits 16-18
INVALIDATE_L2_PTES           MASK 0x00080000   bit 19
INVALIDATE_L2_PDE0           MASK 0x00100000   bit 20
INVALIDATE_L2_PDE1           MASK 0x00200000   bit 21
INVALIDATE_L2_PDE2           MASK 0x00400000   bit 22
INVALIDATE_L1_PTES           MASK 0x00800000   bit 23
CLEAR_PROTECTION_FAULT_STATUS_ADDR MASK 0x01000000 bit 24
LOG_REQUEST                  MASK 0x02000000   bit 25
INVALIDATE_4K_PAGES_ONLY     MASK 0x04000000   bit 26
```

`grep -c "INVALIDATE_L1_PTES\|INVALIDATE_L2_PTES\|INVALIDATE_4K_PAGES_ONLY" gmc_8_2_sh_mask.h`
→ **0**.

Y en GFX9 el driver los pone **todos a 1** (`gmc_v9_0.c:715-719`), sin excepción en todo el
árbol: `grep -rn "INVALIDATE_L2_PTES, 0\|INVALIDATE_L2_PDE0, 0" amdgpu/*.c` → 0. Es decir,
ni siquiera la generación que tiene selectores los usa para afinar. El valor por defecto es
invalidar todo el dominio, y GFX8 no tiene nada más.

## 4 · `017 §5`, última fila: resuelta

`017` dejó: *"Invalidación de L2 cache de traducciones (`MC_VM_MB_L1_TLB0_DEBUG__INVALIDATE_L1_TLB`)"* →
`NOT_OBSERVED`.

Reformulado y cerrado:

| Afirmación | Estado | Base |
|---|---|---|
| GFX8 tiene L1RD y L1WR separados | `PROVEN` | `gmc_8_2_d.h:548-553`, campos idénticos |
| GFX8 tiene L2 de traducción con modo VMID | `PROVEN` | `mmATC_L2_CNTL2__L2_CACHE_VMID_MODE` bits 12-14 |
| Existe `INVALIDATE_ALL` explícito para L1RD/L1WR | `PROVEN` | bit 30 de `ATC_L1RD/WR_DEBUG_TLB` |
| Existe `INVALIDATE_ALL` explícito para L2 | `PROVEN` | `ATC_L2_DEBUG2__INVALIDATE_ALL` bit 9 |
| El driver GFX8 usa alguno | `PROVEN_ABSENT` | `grep` sobre `amdgpu/*.c` = 0, con las rutas de §1 verificadas una a una |
| Que `0x51e` cubra L1RD **y** L1WR **y** L2 | `NOT_DETERMINED` | requiere RUNTIME |
| Que un `INVALIDATE_ALL` manual sobre L1RD alcance L1WR | `NOT_DETERMINED` | requiere RUNTIME |

Las dos últimas no se pueden cerrar estáticamente porque el nombre del registro no dice a
qué cachés alcanza. `READ_SCOPE_GATE` cumplido sólo para los 39 registros de traducción (ver la salvedad en
§Criterio de terminación); pero el `PROVEN_ABSENT` es sólo sobre el **uso por el driver**,
no sobre la capacidad del hardware.
Nombrar cuál de los seis estados de "absence" aplica: aquí es *el driver no lo usa*,
objetivo ausente de la búsqueda; el hardware podría muy bien ofrecerlo y no estar
aprovechado.

`ATENCION`: `INVALIDATE_ALL` está en un registro llamado `DEBUG_TLB`. Eso no significa que
sea inoperante ni que debamos descartarlo; significa que su propósito declarado es
diagnóstico. Un driver propio podría usarlo, y `DESIGN_FREEDOM` lo deja abierto. Lo que no
se puede es asumir que `0x51e` y estos registros son equivalentes.

## 5 · Lo que esto obliga al driver propio

`REQUIREMENT` derivado de evidencia, no de herencia:

- Si el invalidate por dominio (`0x51e`, 1 bit) no alcanza las tres cachés, hace falta
  `INVALIDATE_ALL` explícito por caché, y son 3 escrituras (`L1RD`, `L1WR`, `L2`) no una.
- Si alcanza, hace falta 1. **La evidencia disponible no lo distingue.** Es el discriminante
  central de la capa de memoria.
- Los bits `DISABLE_INVALIDATE_BY_ADDRESS_RANGE` (bit 1) y `DISABLE_FRAGMENTS` (bit 0) en
  los `_DEBUG_TLB` son controles de comportamiento del invalidate. `DISABLE_INVALIDATE_BY_ADDRESS_RANGE`
  es especialmente relevante: su nombre sugiere que **sí existe** un modo de invalidación por
  rango, que el invalidate de dominio no usa. `NOT_DETERMINED`; el nombre del bit es
  evidencia del nombre, no de la semántica.

## 6 · UNLOCKS

- Tres cachés de traducción en GFX8, no una. El diseño de invalidación del driver propio
  tiene tres casos, no uno.
- La frontera G (cache/coherencia) de `AGENTS.md:666-678` tenía "no asumir coherencia por
  analogía". Ahora hay una razón concreta: L1RD/L1WR separados impiden asumir que una
  invalidación de lectura cubre escritura.
- `ATC_VMID_PASID_MAPPING_UPDATE_STATUS__VMID{n}_REMAPPING_FINISHED` (`0xce6`, ×16) **sí**
  ofrece un handshake por VMID, y el driver GFX8 lo consume con busy-wait
  (`amdgpu_amdkfd_gfx_v8.c:102-104`, `while (!(RREG32(...) & (1U<<vmid))) cpu_relax();`).
  Es la prueba de que el hardware GFX8 sí puede dar completion cuando el registro existe.
  Refuerza `018`: la ausencia es del registro de invalidate, no de la capacidad del
  hardware a este nivel de handshake.
- `gmc_v8_0_emit_pasid_mapping` (`gmc_v8_0.c:679-682`) escribe `mmIH_VMID_0_LUT + vmid` y
  **nada más**. No escribe `ATC_VMID{n}_PASID_MAPPING`. El path de ring sólo programa la
  LUT de interrupciones; la tabla ATC la programa KFD por CPU. Divergencia real entre los
  dos caminos, y `mmIH_VMID_0_LUT` está en OSS (`oss_3_0_d.h:27`, `0xe00`), no en GMC.

## 7 · Criterio de falsificación

Se refutaría si: (a) `gmc_8_2_sh_mask.h` tuviera un campo de granularidad en
`VM_INVALIDATE_REQUEST` fuera de los 32 contados — cerraría §3; (b) apareciera un `.c` que
escriba `ATC_L1RD/WR_DEBUG_TLB` o `ATC_L2_DEBUG2` — refutaría el `PROVEN_ABSENT` de §4;
(c) el hardwareligt `0x51e` cubriera las tres cachés, lo que **reduciría** el
`REQUIREMENT` de §5 a una escritura, no lo refuta. (a) y (b) son cerrables estáticamente y
están cerrados; (c) exige RUNTIME y queda `PROVISIONAL`.

## 8 · Evidencia

```
sha256 tarball: 12e8d5a973d1ad7c5a5c69882e4022b131ed715db7003fdcd760ddf8c3e51941 (linux-7.2.8.tar.xz)
                 recalculado; coincide con upstream.sha256 y local.sha256.
                 LIMITACIÓN: hash sin nombre de fichero → `sha256sum -c` falla.
                 Cubre el .tar.xz, no el árbol extraído.

include/asic_reg/gmc/gmc_8_2_d.h:          545-573 (los 63 mmATC_), 556-572
include/asic_reg/gmc/gmc_8_2_sh_mask.h:    5875-6068 (ATC_L2_*, ATC_L1_*, VMID_*),
                                           6589-6652 (INVALIDATE REQ/RESP),
                                           6457-6476 (VM_CONTEXT0_CNTL)
include/asic_reg/gmc/gmc_8_1_d.h:          548-549 (L1RD/L1WR presentes también en 8_1)
include/asic_reg/mmhub/mmhub_3_0_0_sh_mask.h: 5845-5864 (REQ con granularidad GFX9)
include/asic_reg/oss/oss_3_0_d.h:          27 (mmIH_VMID_0_LUT 0xe00)
amdgpu/gmc_v8_0.c:          655-660 (flush_gpu_tlb), 662-677 (emit_flush),
                           679-682 (emit_pasid_mapping), 935, 1501-1660 (clock gating),
                           1728-1731 (pmf)
amdgpu/gmc_v9_0.c:          707-722 (get_invalidate_req), 969-985 (emit_pasid_mapping)
amdgpu/gfx_v8_0.c:          112 (mmATC_MISC_CG init table)
amdgpu/amdgpu_amdkfd_gfx_v8.c: 87-110 (kgd_set_pasid_vmid_mapping, busy-wait de remapping)
```

Ningún registro leído de MMIO en hardware. Ninguna operación runtime. `GPU INTACTA`.
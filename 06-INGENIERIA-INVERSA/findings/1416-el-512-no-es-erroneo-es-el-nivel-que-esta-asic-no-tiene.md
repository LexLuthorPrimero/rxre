# 1416 — el 512 de `rx550_pdb0.h` no es un valor equivocado: es el nivel que esta ASIC no tiene. La contradicción de factor 32 queda resuelta

```text
AGENCIA=RX550-INVESTIGACION · WORK_CLASS=AGENT-MAIN/RE
CLASSIFICATION=RESOLUCION-DE-CONTRADICCION+REFUTACION
TRACK=STATIC(corpus) · sin GPU · sin sudo
GENERADO=2026-10-04
AFECTADO=04-IMPLEMENTACION/rx550-driver/rx550_pdb0.h:43        (RX550_PDB0_ENTRIES 512)
         04-IMPLEMENTACION/rx550-driver/target_mem.h:47-48     (TM_LEVEL_BITS 9 / _ENTRIES 512)
         04-IMPLEMENTACION/rx550-driver/rx550_pdb0.h:125       (marca de hoja en bit 54)
         04-IMPLEMENTACION/rx550-driver/rx550_pdb0.h:159       (cobertura, asume FRAG=0)
ORIGEN=inventario de geometria: dos ficheros del proyecto fijan 512 como recuento
       raiz-adyacente y el corpus calcula 16384.  Factor 32, sin arbitrar desde entonces.
ESTADO=RESUELTO · los tres numeros correctos estan PROVEN y verificados a mano
       · el 512 queda explicado: es la rama "todo lo de en medio" de amdgpu_vm_pt.c:88,
         INALCANZABLE con num_level = 1
       · rx550_pdb0.h: REFUTADO en los dos papeles que le asigna
```

## 0. La contradicción, tal como estaba

| lado | valor | fichero |
|---|---|---|
| derivado del driver | **16384** entradas de raíz | `rx550_vmid1_pgt.c:350-359` |
| constante dura del proyecto | **512** entradas | `rx550_pdb0.h:43` |
| tercera autoridad del proyecto | **512** entradas | `target_mem.h:47-48` |

Factor 32. Dos cosas la mantinían viva: el primer fichero **reproduce exactamente** el
cálculo del vendor, y el segundo se declara "implementación CANÓNICA". Un lector ortodoxo
tiene razón para desconfiar del derivado.

**Este hallazgo dice que el derivado es el bueno y los dos "512" son el mismo error.**

## 1. Los tres números, verificados a mano (no por subagente)

Las tres líneas que sostienen el hallazgo están en `RESEARCH/baseline/linux-7.1.3/drivers/gpu/drm/amd/amdgpu/`.
Se leyeron literalmente:

```c
/* amdgpu_vm_pt.c:80-89 */
shift = amdgpu_vm_pt_level_shift(adev, adev->vm_manager.root_level);
if (level == adev->vm_manager.root_level)
        /* For the root directory */
        return round_up(adev->vm_manager.max_pfn, 1ULL << shift) >> shift;
else if (level != AMDGPU_VM_PTB)
        /* Everything in between */
        return 512;
/* For the page tables on the leaves */
return AMDGPU_VM_PTE_COUNT(adev);
```

```c
/* amdgpu_vm.h:55 */
#define AMDGPU_VM_PTE_COUNT(adev) (1 << (adev)->vm_manager.block_size)
```

De aquí salen, para esta ASIC (`max_pfn = 16777216` de `amdgpu_vm.c:2421`,
`block_size = 10` de `amdgpu_vm.c:2454`):

| nivel | fórmula | valor |
|---|---|---|
| raíz (`AMDGPU_VM_PDB0`) | `round_up(max_pfn, 1<<shift) >> shift` | **16384** entradas, 131072 B |
| hoja (`AMDGPU_VM_PTB`) | `1 << block_size` = `1<<10` | **1024** entradas, 8192 B |

Y la tercera rama, **`return 512`**, está bajo `else if (level != AMDGPU_VM_PTB)` y
comentada `/* Everything in between */`. Con `num_level = 1`
(`amdgpu_vm.c:2428`) los niveles de esta ASIC son **exactamente dos**: raíz y hoja. **No hay
nivel intermedio. La rama no se ejecuta.**

## 2. Por qué esto explica el factor 32 y no lo Increases

El 512 **no** es una versión equivocada del 16384, ni del 1024, ni del 65536 del GART.
Es un **cuarto número**, y el más engañoso de todos porque es *real*: está escrito en el
driver del vendor, es correcto para su propósito, y **nunca se ejecuta en esta ASIC**.

| número | a qué corresponde | ¿se usa en esta ASIC? |
|---|---|---|
| 16384 | raíz VMID1+ | **sí** |
| 1024 | hoja PTB | **sí** |
| 65536 | entradas del GART (VMID0) | **sí** |
| **512** | **niveles intermedios (2..n-1)** | **NO — `num_level = 1`** |

Quien copió un 512 a un `.h` como "entradas de PDB0" tomó el número de un nivel que esta
ASIC no tiene. **El error no es aritmético: es de selección de nivel.** Por eso un
`static_assert` que cuadra contra un número equivocado sigue compilando.

## 3. Las otras dos cifras, para que no quede ninguna ambigüedad

**VMID0 (GART), que es OTRA estructura y tiene otro número:**

```c
/* amdgpu_gart.c:532-533 */
adev->gart.num_cpu_pages = adev->gmc.gart_size / PAGE_SIZE;
adev->gmc.num_gpu_pages = adev->gmc.gart_size / AMDGPU_GPU_PAGE_SIZE;
```

Con `gart_size = 256 MiB` (`gmc_v8_0.c:592,595`) y `AMDGPU_GPU_PAGE_SIZE = 4096`
(`amdgpu_gart.h:35`): **65536 entradas, 512 KiB de tabla**. Y la profundidad que se programa
es **plana**:

```c
/* gmc_v8_0.c:895   VMID0 */   PAGE_TABLE_DEPTH, 0     <- plano
/* gmc_v8_0.c:925   VMID1 */   PAGE_TABLE_DEPTH, 1     <- PD + PT
```

**Así que hay dos estructuras con dos números, y ninguno es 512.** La lectura de
`rx550_vmid0_gart.h` (que el proyecto ya tiene) es la correcta; `rx550_pdb0.h` la
contradice. `rx550_pdb0.*` **no tiene consumidor** — `nm -u` sobre el `.ko` no devuelve
nada — así que el conflicto no ha llegado a la ejecución, pero **sigue leyéndose como si
fuera autoritativo**, que es peor que un código muerto.

## 4. Dos afirmaciones que hay que degradar a `NOT_DETERMINED`

El subagente las señaló y se comprueban con dos líneas del corpus, sin necesidad de más:

1. **La marca de hoja en el bit 54 del PDE.** `amdgpu_vm.h:76` define
   `AMDGPU_PDE_PTE (1ull<<54)`, pero el vendor **sólo la escribe para `asic_type >= CHIP_VEGA10`**
   (`amdgpu_vm_pt.c:408`). En gfx8, `gmc_v8_0.c:706` lista `58:40` como reservado.
   `rx550_pdb0.h:125` y `target_mem.h:78` **afirman** la marca como hecho de gfx8. **No lo es:**
   es una convención de gfx9 en adelante. `PROVEN_ABSENT` su uso en gfx8.
2. **La cobertura calculada con `FRAG = 0`** (`rx550_pdb0.h:159`). En gfx8 el fragmento por
   omisión es **9** (`gmc_v8_0.c:1127`), no 0. La cifra de cobertura derivada es incorrecta
   por esa suposición.

## 5. Lo que la contradicción NO tapaba: dos huecos reales

De paso, la lectura profunda de esta ruta deja **dos `PROVEN_ABSENT`** que no estaban
registrados:

| campo | en gfx8 | quien lo produce | quien lo consume |
|---|---|---|---|
| `adev->gmc.vmid0_page_table_block_size` | — | nadie (0 apariciones en `gmc_v8_0.c`; sólo `gmc_v9_0.c:1780` y `gmc_v12_0.c:787`) | nadie |
| `adev->gmc.pdb0_bo` | **el campo no existe** (`amdgpu_gmc.c:57,1132`) | sólo gfx9+/v12 | igual |

`pdb0_bo` **no existe en esta generación**. Cualquier código nuestro que lo asuma está
hablando de otra ASIC. Y `vmid0_page_table_block_size` no tiene productor ni consumidor:
es un campo sin nadie detrás, en gfx8. El hallazgo 1127 ya había registrado la mitad de esto
(productor ausente); queda confirmado el lado del consumidor.

**Y una restricción que no es negociable para el driver:** las páginas gigantes están
**prohibidas** en gfx8 (`amdgpu_vm_pt.c:838-845`), y todo PDE debe estar alineado a 4 KiB
con los bits 40-55 a cero, con `BUG_ON` en `gmc_v8_0.c:715`. Cualquier tabla que escribamos
tiene que cumplir eso o revienta el kernel.

## 6. La corrección causal, no sólo la numérica

El token **`PDB0` nombra tres cosas distintas** en este árbol:

1. la **raíz** del walk de VMID1+ — que sí es `AMDGPU_VM_PDB0` en el corpus;
2. la **base del GART** de VMID0, que es plana y tiene 65536 entradas;
3. el fichero `rx550_pdb0.h`, que parece querer ser el (1) pero con el recuento del (2).

Esa ambigüedad es la causa del error. Renombrar el componente de VMID0 a `vmid0`/`gart` y
reservar `pdb0` para la raíz del walk habría hecho imposible esta contradicción. **Un
nombre que nombra dos cosas produce un número que no pertenece a ninguna.**

## 7. Lo que este hallazgo NO hace

- **No edita ningún fichero del driver.** Sólo lectura; las correcciones se proponen, no se
  aplican. `rx550_pdb0.h` lo está tocando la otra sesión: tocarlo sería una violación de §88.
- **No retira `rx550_pdb0.*`.** Está muerto en el `.ko`, pero muerto y autoritativo a la vez
  sigue siendo peor que ausente. La decisión es del dueño del árbol.
- **No cierra el techo de 64 GiB.** `rx550_vmid1_pgt.c` es correcto, pero su alcance
  aritmético son **32 TiB** (`9*(PDB0-level) + block_size`); 64 GiB es lo que
  `VM_CONTEXT1_PAGE_TABLE_END_ADDR` impone (`gmc_v8_0.c:909`). El texto del header no debe
  decir que 64 GiB es el techo del walk.
- **No toca la GPU.** Cero escrituras a registros, cero privileged access.

## 8. Procedencia

```text
RESEARCH/baseline/linux-7.1.3/drivers/gpu/drm/amd/amdgpu/
  amdgpu_vm_pt.c:80-89     el return 512 y sus dos condiciones   (leido literal)
  amdgpu_vm.h:55           AMDGPU_VM_PTE_COUNT = 1 << block_size (leido literal)
  amdgpu_vm.h:76           AMDGPU_PDE_PTE = 1<<54                (leido literal)
  amdgpu_vm_pt.c:408       la marca de hoja, solo >= CHIP_VEGA10 (leido literal)
  amdgpu_vm.c:2421,2428,2454   max_pfn, num_level, block_size
  amdgpu_gart.c:532-533    entradas del GART                     (leido literal)
  amdgpu_gart.h:35         AMDGPU_GPU_PAGE_SIZE 4096
  gmc_v8_0.c:592,595       gart_size 256 MiB
  gmc_v8_0.c:706           bits 58:40 reservados en el PDE de gfx8
  gmc_v8_0.c:715           BUG_ON de alineacion y bits 40-55
  gmc_v8_0.c:895,925       PAGE_TABLE_DEPTH 0 (VMID0) y 1 (VMID1)
  gmc_v8_0.c:909,1127      PAGE_TABLE_END_ADDR, fragment_size 9
  amdgpu_vm_pt.c:838-845   paginas gigantes prohibidas
  amdgpu_gmc.c:57,1132     pdb0_bo no existe
metodo   lectura estatica de fuente del vendor.  Las tres lineas que sostienen el
         hallazgo se leyeron literalmente, no por resumen de un subagente.
```

```text
ESTADO=RESUELTO · la contradiccion de factor 32 queda arbitrada
       · 16384 raiz / 1024 hoja / 65536 GART   los tres PROVEN y verificados a mano
       · el 512 es la rama "todo lo de en medio" de amdgpu_vm_pt.c:88, inalcanzable con
         num_level = 1: no es un valor equivocado, es un nivel que esta ASIC no tiene
       · rx550_pdb0.h REFUTADO en los dos papeles; target_mem.h:47-48 igual
       · dos afirmaciones degradadas: marca de hoja bit 54 (PROVEN_ABSENT en gfx8) y
         cobertura calculada con FRAG=0 (gfx8 usa 9)
       · dos huecos nuevos confirmados: vmid0_page_table_block_size sin productor NI
         consumidor; gmc.pdb0_bo no existe en gfx8
       · restricciones para el driver: sin paginas gigantes, PDE alineado a 4 KiB con
         bits 40-55 a cero
CAUSA    el token PDB0 nombra tres cosas distintas (raiz VMID1+, base GART VMID0, fichero)
LIMITACION  no se edita nada; rx550_pdb0.h lo esta tocando la otra sesion (§88)
Siguiente   1) renombrar vmid0/gart vs pdb0 (correccion causal, no numerica)
            2) corregir el texto de 64 GiB: el techo del walk es 32 TiB; 64 GiB es el
               limite de VM_CONTEXT1_PAGE_TABLE_END_ADDR
            3) secuencia de programacion de una tabla VMID1 minima: raiz 16384 + hoja
               1024, con los 20 registros de gmc_8_1_d.h:607-614,636-647
```

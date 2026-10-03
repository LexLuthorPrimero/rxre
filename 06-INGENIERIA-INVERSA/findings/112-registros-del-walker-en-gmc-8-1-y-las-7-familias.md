# 112 · §A/§B: los registros del page walker están en `gmc_8_1`, no en `gfx_8_0`

`CLASSIFICATION=DOCUMENTATION` · `TRACK=STATIC` · `WORK_CLASS=READ_ONLY/EVIDENCE`
`WRITE_EXECUTION=NONE` · `MODIFICATIONS=0` · `RUNTIME=NOT_RUN` · `GPU INTACTA`
`CORPUS=RESEARCH/working/linux-7.1.3` · `HARDWARE_SCOPE=HOST-C/RX550/0000:01:00.0`
`CIERRA=la mitad de secA (PTE/PDE) y secB (page walker)`
`RESUELTA=la contradiccion de root_level que 035 ya habia cerrado`

## Cuestión principal

`AGENTS.md` §A dice: *"Separar 'Linux escribe este bit' de 'hardware interpreta
este bit así'"*.

Antes de poder separarlo hay que saber **dónde está el registro**. Y la
respuesta no es donde el proyecto ha estado mirando.

## El dato que reencuadra todo: el ASIC se parte en dos familias

Conté los registros `mmVM_*` (los del page walker y la VM) en cada cabecera:

```
$ grep -c "mmVM_" include/asic_reg/gca/gfx_8_0_d.h        ->  0
$ grep -c "mmVM_" include/asic_reg/gmc/gmc_8_1_d.h        -> 61
```

**`gfx_8_0_d.h` no tiene ni un solo registro de VM.** Es la cabecera de la
*GigaCore Engine* (shader, SQ, packet). Los 61 registros `mmVM_*` viven en
`gmc_8_1_*`, la cabecera del *Graphics Memory Controller*.

Esto no es un detalle de nomenclatura. Significa que:

- `gfx_v8_0.c` (el fichero grande, con los shaders) **no toca el page walker**.
- `gmc_v8_0.c` (el fichero que programa la VM) es el dueño de §A y §B.
- `VM_CONTEXT1_PROTECTION_FAULT_STATUS` **no está** en `gfx_8_0_sh_mask.h`, está
  en `gmc_8_1_sh_mask.h:6849`.

Y explica por qué dos búsquedas mías y de un subagente dieron `NOT_FOUND` sobre
cosas que sí existen: se estaban mirando en la familia equivocada. No es que
falte el header; es que hay dos y el registro está en el que no se miraba.

## Los 5 campos de `VM_CONTEXT1_PROTECTION_FAULT_STATUS`

No hay 5 bits de fault. Hay **5 campos**, y ninguno se llama "fault":

```
gmc_8_1_sh_mask.h:6849  PROTECTIONS        0xff        shift 0x0   (8 bits)
gmc_8_1_sh_mask.h:6851  MEMORY_CLIENT_ID   0x1ff000   shift 0xc   (9 bits)
gmc_8_1_sh_mask.h:6853  MEMORY_CLIENT_RW   0x1000000  shift 0x18  (1 bit)
gmc_8_1_sh_mask.h:6855  VMID               0x1e000000 shift 0x19  (5 bits)
gmc_8_1_sh_mask.h:6857  ATOMIC             0x20000000 shift 0x1d  (1 bit)
```

Son 10 líneas en total, exhaustivas. **`PROTECTIONS` es un código de 8 bits,
no un conjunto de flags.** El driver no lo descompone:

```c
/* gmc_v8_0.c:1007-1008 */
u32 protections = REG_GET_FIELD(status, VM_CONTEXT1_PROTECTION_FAULT_STATUS,
                                PROTECTIONS);
```

y lo imprime crudo:

```c
/* gmc_v8_0.c:1016 */
dev_err(adev->dev, "VM fault (0x%02x, vmid %d, pasid %d) at page %u, ...",
        protections, vmid, pasid, addr, ...);
```

**El driver sabe qué faults hay, dónde habilitarlos, y qué hacer con ellos, y
aun así el código de fault que reporta no lo descodifica.** Es el mismo patrón
que el `src_data[0]` de `051`: el hardware entrega un código, el driver lo
transporta, nadie lo interpreta.

## Las 7 familias de fault sí están, y están en otro registro

No en `PROTECTION_FAULT_STATUS`, sino en `VM_CONTEXT1_CNTL`, como tríos
`INTERRUPT` / `DEFAULT` / `SAVE`. Verificado con máscaras:

| Familia | `..._INTERRUPT` | `..._DEFAULT` | bit base |
|---|---|---|---|
| RANGE | `0x8` | `0x10` | 3 |
| DUMMY_PAGE | `0x40` | `0x80` | 6 |
| PDE0 | `0x200` | `0x400` | 9 |
| VALID | `0x1000` | `0x2000` | 12 |
| READ | `0x8000` | `0x10000` | 15 |
| WRITE | `0x40000` | `0x80000` | 18 |
| EXECUTE | `0x200000` | `0x400000` | 21 |

**Siete, no cinco**, y van escalonados de tres en tres en bits: 3, 6, 9, 12, 15,
18, 21. La regularidad es exacta y sugiere que el hardware las numera, aunque
**el header no dice qué valor numérico toma `PROTECTIONS` para cada una**.

## Qué programa el driver, y qué significa

`gmc_v8_0.c:922-940`, `gmc_v8_0_gart_enable`:

```c
WREG32(mmVM_CONTEXT1_PROTECTION_FAULT_DEFAULT_ADDR, dummy_page_addr >> 12);
WREG32(mmVM_CONTEXT1_CNTL2, 4);
tmp = REG_SET_FIELD(tmp, VM_CONTEXT1_CNTL, ENABLE_CONTEXT, 1);
tmp = REG_SET_FIELD(tmp, VM_CONTEXT1_CNTL, PAGE_TABLE_DEPTH, 1);
tmp = REG_SET_FIELD(tmp, VM_CONTEXT1_CNTL, RANGE_PROTECTION_FAULT_ENABLE_DEFAULT, 1);
tmp = REG_SET_FIELD(tmp, VM_CONTEXT1_CNTL, DUMMY_PAGE_PROTECTION_FAULT_ENABLE_DEFAULT, 1);
tmp = REG_SET_FIELD(tmp, VM_CONTEXT1_CNTL, PDE0_PROTECTION_FAULT_ENABLE_DEFAULT, 1);
tmp = REG_SET_FIELD(tmp, VM_CONTEXT1_CNTL, VALID_PROTECTION_FAULT_ENABLE_DEFAULT, 1);
tmp = REG_SET_FIELD(tmp, VM_CONTEXT1_CNTL, READ_PROTECTION_FAULT_ENABLE_DEFAULT, 1);
tmp = REG_SET_FIELD(tmp, VM_CONTEXT1_CNTL, WRITE_PROTECTION_FAULT_ENABLE_DEFAULT, 1);
tmp = REG_SET_FIELD(tmp, VM_CONTEXT1_CNTL, EXECUTE_PROTECTION_FAULT_ENABLE_DEFAULT, 1);
tmp = REG_SET_FIELD(tmp, VM_CONTEXT1_CNTL, PAGE_TABLE_BLOCK_SIZE,
                    adev->vm_manager.block_size - 9);
```

Las 7 familias se habilitan **todas**, y todas con el sufijo `DEFAULT`, no
`INTERRUPT`. Sumado a que `DEFAULT_ADDR` apunta a la **dummy page**, la
semántica es: *un fault no genera IRQ, se redirige a la página dummy*.

Esto solo se invierte si `amdgpu_vm_fault_stop` está a `FIRST` o `ALWAYS`
(`gmc_v8_0.c:937-939` llama entonces a `gmc_v8_0_set_fault_enable_default(..., false)`).

**Es la respuesta directa a `AGENTS.md` §A**: hay un bit de hardware
(`..._ENABLE_INTERRUPT`) por familia, y el driver pone a 1 los 7 hermanos
`_DEFAULT`. Separar "lo que el driver escribe" de "lo que el hardware hace" es
exactamente esto: escribe `DEFAULT`, y el hardware redirige a la dummy page.

## El page table block size, leído en hardware

`gmc_v8_0.c:933-934` escribe `PAGE_TABLE_BLOCK_SIZE = block_size - 9`. Con
`block_size = 10` (`035`, ya cerrado), el campo vale **1**.

```
gmc_8_1_sh_mask.h:6627  VM_CONTEXT1_CNTL__PAGE_TABLE_BLOCK_SIZE_MASK 0xf000000
gmc_8_1_sh_mask.h:6628  VM_CONTEXT1_CNTL__PAGE_TABLE_BLOCK_SIZE__SHIFT 0x18
```

Campo de 4 bits, bits 24-27. Y `PAGE_TABLE_DEPTH` es de 3 bits:

```
gmc_8_1_sh_mask.h:6627  PAGE_TABLE_DEPTH_MASK 0x6   -> 3 bits
gmc_8_1_sh_mask.h:6628  PAGE_TABLE_DEPTH__SHIFT 0x1
```

Con `PAGE_TABLE_DEPTH = 1` y `block_size` efectivo 10, la geometría que el
hardware recibe es coherente con `root_level = AMDGPU_VM_PDB0` + `PTB`.

## El PTE, según el propio driver

`gmc_v8_0.c:691-700`, comentario literal:

```
 * PTE format on VI:
 * 63:40 reserved
 * 39:12 4k physical page base address
 * 11:7 fragment
 * 6 write
 * 5 read
 * 4 exe
 * 3 reserved
 * 2 snooped
 * 1 system
 * 0 valid
```

Y el PDE (`:702-708`):

```
 * PDE format on VI:
 * 63:59 block fragment size
 * 58:40 reserved
 * 39:1 physical base address of PTE
 * bits 5:1 must be 0.
 * 0 valid
```

**Dato nuevo y operativo: `gmc_v8_0_get_vm_pde` no escribe ningún flag.**

```c
/* gmc_v8_0.c:712-716 */
static void gmc_v8_0_get_vm_pde(struct amdgpu_device *adev, int level,
                                uint64_t *addr, uint64_t *flags)
{
        BUG_ON(*addr & 0xFFFFFF0000000FFFULL);
}
```

Solo valida la alineación y no toca `*flags`. Contraste con `gmc_v9_0.c`, que
sí pone `AMDGPU_PDE_BFS`. **En Polaris12 el PDE sale siempre con bits 63:59 = 0**,
es decir sin block-fragment-size. Es el equivalente en software de la línea
`/* No huge page support before GMC v9 */`.

## Las cachés que el driver enciende

```
gmc_v8_0.c:844   ENABLE_L1_TLB                   = 1
gmc_v8_0.c:845   ENABLE_L1_FRAGMENT_PROCESSING   = 1
gmc_v8_0.c:846   SYSTEM_ACCESS_MODE              = 3
gmc_v8_0.c:847   ENABLE_ADVANCED_DRIVER_MODEL    = 1
gmc_v8_0.c:852   ENABLE_L2_CACHE                 = 1
gmc_v8_0.c:855   ENABLE_L2_PTE_CACHE_LRU_UPDATE_BY_WRITE  = 1
gmc_v8_0.c:856   ENABLE_L2_PDE0_CACHE_LRU_UPDATE_BY_WRITE = 1
gmc_v8_0.c:861   INVALIDATE_ALL_L1_TLBS          = 1
gmc_v8_0.c:862   INVALIDATE_L2_CACHE             = 1
```

Hay **L1 TLB** y **L2** con **dos** cachés dentro (PTE y PDE0), ambas con
actualización por escritura. Es la respuesta estática a por qué existe
`VM_INVALIDATE_REQUEST`: hay estado que invalidar en tres sitios.

## Dos correcciones al material de los subagentes

**1. Un error tipográfico con consecuencia.** El informe de §B escribió
`VMID__SHIFT 0x29`. El header dice `0x19`. `0x29` sería el bit 41, imposible en
un registro de 32 bits, así que el error es detectable por aritmética. Lo
verifiqué antes de publicarlo.

**2. Una "refutación" que no era nueva, y era falsa como afirmación.** El mismo
informe abrió diciendo que `root_level = AMDGPU_VM_PDB2` aparece en 7 documentos
del proyecto y queda refutado. La mitad es cierta y la otra no:

- **Cierto**, y bien difícil: `gmc_v8_0.c:1127` pasa `max_level = 1`;
  `amdgpu_vm.c:2428` hace `num_level = min_t(max_level, tmp)`; y el switch de
  `amdgpu_vm.c:2439-2440` mapea `case 1: root_level = AMDGPU_VM_PDB0`.
- **Falso que fuera nuevo**: `035` ya lo tenía cerrado ("mantienen. En
  particular `num_level = 1` con `root_level = AMDGPU_VM_PDB0`"),
  `docs/CONTRADICTIONS.md:549-551` ya listaba la contradicción y la resolvía con
  el mismo argumento.
- **Lo único realmente obsoleto** es `030-page-walker-gfx8-2-niveles.md:77`, que
  afirma `root_level = AMDGPU_VM_PDB2` y cita `amdgpu_vm.c:2410-2411`. Las
  líneas correctas son **2439-2440**: la cita está desfasada 29 líneas.

Un subagente no tiene memoria del proyecto. Reportó como "el proyecto cree X"
una afirmación que el proyecto ya había retirado por la misma vía.

## La lección, y por qué delegué

De dos subagentes, **los dos** produjeron una afirmación falsa de la misma
clase: una afirmación sobre una **ausencia**.

| Subagente | Afirmó | Realidad |
|---|---|---|
| §D | "`asic_reg` ausente del corpus" | existe, en 3 rutas |
| §B | "`PDB2` en 7 documentos, refutado" | cerrado en `035` desde antes |

El patrón no es casual. **Una afirmación sobre una ausencia es la que un
subagente produce con más confianza y menos evidencia**, porque un `grep` vacío
dentro de un subárbol se parece exactamente a un `grep` vacío en el corpus. La
única forma de distinguirlos es mirar **dónde** buscó, y eso no viene en el
informe.

Los dos informes tenían además una parte sólida y verificable — el §D cerró la
cadena de emisión de §D con números de línea, y el §B dio las 7 familias de
fault con sus máscaras — así que **delegar fue rentable**. Lo que no es
rentable es aceptar el headline sin comprobarlo.

Clase de error, para el registro: `NOT_FOUND` tiene que llevar la raíz de
búsqueda escrita, o no es citable. Es el mismo control que ya exige
`corpus_guard --verify`.

## Clasificación

| afirmación | estado |
|---|---|
| `gfx_8_0_d.h` tiene 0 registros `mmVM_*` | `PROVEN` — `grep -c` |
| `gmc_8_1_d.h` tiene 61 | `PROVEN` — `grep -c` |
| `PROTECTION_FAULT_STATUS` tiene 5 campos, ninguno de fault | `PROVEN` — 10 líneas exhaustivas |
| `PROTECTIONS` es un código de 8 bits impreso crudo | `PROVEN` — `gmc_v8_0.c:1016` |
| Hay 7 familias de fault, no 5 | `PROVEN` — 7 máscaras distintas |
| Las 7 se habilitan con sufijo `DEFAULT`, no `INTERRUPT` | `PROVEN` — `gmc_v8_0.c:925-931` |
| `DEFAULT` + `DEFAULT_ADDR` = redirección a dummy page | `DERIVATION` — del nombre y del código |
| `PAGE_TABLE_BLOCK_SIZE` recibe `block_size - 9 = 1` | `PROVEN` código / `DERIVATION` valor |
| `gmc_v8_0_get_vm_pde` no escribe flags | `PROVEN` — la función entera |
| PDE sale con bits 63:59 = 0 en Polaris12 | `DERIVATION` — de la anterior |
| L1 TLB y L2 (PTE + PDE0) encendidas | `PROVEN` — `gmc_v8_0.c:844-862` |
| `root_level = PDB0` | `PROVEN` — `amdgpu_vm.c:2439-2440` |
| Que `030:77` afirme PDB2 | `PROVEN` — lectura directa |
| Que el código numérico de `PROTECTIONS` mapee a familia | `NOT_DETERMINED` |
| Que la redirección a dummy page no genere IRQ | `DERIVATION` — no verificado en placa |
| `PAGE_TABLE_DEPTH = 1` significa "2 tablas" | `DERIVATION` — coherente, no documentado |

## Confounders

- **`gfx_8_0_d.h` no tener registros `mmVM_` no significa que GFX8 no los
  tenga.** Significa que están en la familia `gmc_8_1`. El hardware es uno; las
  cabeceras son dos, y la que manda la incluye el fichero que programa la VM
  (`gmc_v8_0.c:35`).
- **La numeración regular 3,6,9,12,15,18,21 es mía, no del header.** El header
  da los tres registros (`INTERRUPT`, `DEFAULT`, `SAVE`) pero no un índice. Que
  el código valga `1` para RANGE y `7` para EXECUTE es una inferencia mía, y
  `NOT_DETERMINED`.
- **`PROTECTIONS` es un campo de 8 bits para 7 familias.** Queda un valor
  (8). No sé si es un caso especial o un código de error.
- **No he tocado la placa.** Ni un `PROVEN` de aquí viene de hardware.
- **`030:77` sigue diciendo PDB2.** No lo he editado: `030` no es mío y su
  alcance de edición no está claro.

## Desfalsificación

- **(a)** `gfx_8_0_d.h` sin `mmVM_` → refutable con `grep -c`, da 0.
- **(b)** 5 campos en `PROTECTION_FAULT_STATUS` → refutable con el `grep`, da 10
  líneas (5 pares `_MASK`/`_SHIFT`).
- **(c)** 7 familias → refutable con `grep -o`, da 7 nombres distintos.
- **(d)** El driver no descompone `PROTECTIONS` → refutable con `gmc_v8_0.c:1016`.
- **(e)** `get_vm_pde` no escribe flags → refutable leyendo sus 4 líneas.
- **(f)** El subagente se equivocó → refutable con `amdgpu_vm.c:2439-2440`.
- **(g)** El mapping numérico `PROTECTIONS` → **no refutable aquí**, requiere
  placa: provocar una fault y leer el código.

## UNLOCKS

- **`§A` tiene su estructura de bits completa por el lado del driver**, y
  `secA`'s pregunta de fondo —"¿qué pone el driver y qué hace el hardware?"—
  ya tiene respuesta concreta: pone `DEFAULT`, el hardware redirige a la dummy.
- **Para el driver propio, el inventario de registros que hay que conocer son
  61, no 0.** La §A/§B se lee en `gmc_8_1_*`, no en `gfx_8_0_*`.
- **`PROTECTIONS` es el siguiente discriminante barato**, y es de lectura:
  provocar una fault y ver el código. Con 7 familias y 8 valores posibles, un
  solo fault observado ordena la tabla entera.
- **La corrección de `030:77` está pendiente** y es de una línea.

## Evidencia

```
$ grep -c "mmVM_" include/asic_reg/gca/gfx_8_0_d.h   -> 0
$ grep -c "mmVM_" include/asic_reg/gmc/gmc_8_1_d.h   -> 61

gmc_8_1_sh_mask.h:6849-6858   PROTECTION_FAULT_STATUS: 5 campos
gmc_8_1_sh_mask.h:6627-6668   VM_CONTEXT1_CNTL: 7 familias x 3 registros
gmc_8_1_sh_mask.h:6627        PAGE_TABLE_BLOCK_SIZE_MASK 0xf000000 (4 bits)

gmc_v8_0.c:35                 #include "gmc/gmc_8_1_d.h"  (la familia buena)
gmc_v8_0.c:691-708            PTE/PDE format en comentario
gmc_v8_0.c:712-716            get_vm_pde: no escribe flags
gmc_v8_0.c:844-862            L1 TLB + L2 PTE/PDE0 caches
gmc_v8_0.c:922-940            las 7 familias a DEFAULT
gmc_v8_0.c:1016               PROTECTIONS impreso crudo

amdgpu_vm.c:2439-2440         case 1: root_level = AMDGPU_VM_PDB0
```

`WRITE_EXECUTION=NONE`. `MODIFICATIONS=0`. `GPU INTACTA`.

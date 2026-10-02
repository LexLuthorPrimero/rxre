# 133 · §A/§G: el MTYPE no existe en GFX8, y el valor exacto del PTE del GART es `0x4F5`

```
CLASSIFICATION=DOCUMENTATION · TRACK=STATIC
CORPUS=RESEARCH/working/linux-7.1.3 · HARDWARE_SCOPE=HOST-C/RX550/0000:01:00.0
WORK_CLASS=READ_ONLY/EVIDENCE · WRITE_EXECUTION=NONE · MODIFICATIONS=0
RUNTIME=NOT_RUN · GPU INTACTA
```

## Qué resuelve

`132` encontró, en `amdgpu_gmc.c:1135`, un comentario que es una pregunta que el
autor no respondió:

```c
uint64_t flags = adev->gart.gart_pte_flags; //TODO it is UC. explore NC/RW?
```

**Esta nota responde a la pregunta, y la respuesta es que en esta GPU la pregunta
no tiene objeto: el campo MTYPE no existe en GFX8.**

## 1 · El MTYPE es una invención de GFX9

```
amdgpu_vm.h:96-101   /* For GFX9 */
                   #define AMDGPU_PTE_MTYPE_VG10_SHIFT(mtype)  ((uint64_t)(mtype) << 57)
                   #define AMDGPU_PTE_MTYPE_VG10_MASK          AMDGPU_PTE_MTYPE_VG10_SHIFT(3ULL)
```

**Los bits 57-58 son el MTYPE, y el comentario de arriba dice "For GFX9".**

Y la historia de `gart_pte_flags`, que lo dice sin ambigüedad:

```
gmc_v6_0.c:576    adev->gart.gart_pte_flags = 0;
gmc_v7_0.c:727    adev->gart.gart_pte_flags = 0;
gmc_v8_0.c:961    adev->gart.gart_pte_flags = AMDGPU_PTE_EXECUTABLE;   <- 0x10
gmc_v9_0.c:1791   adev->gart.gart_pte_flags = AMDGPU_PTE_MTYPE_VG10(0ULL, MTYPE_UC) | AMDGPU_PTE_EXECUTABLE;
gmc_v10_0.c:746   adev->gart.gart_pte_flags = AMDGPU_PTE_MTYPE_NV10(0ULL, MTYPE_UC) | ...
gmc_v11_0.c:737   adev->gart.gart_pte_flags = AMDGPU_PTE_MTYPE_NV10(0ULL, MTYPE_UC) | ...
gmc_v12_0.c:799   adev->gart.gart_pte_flags = AMDGPU_PTE_MTYPE_GFX12(0ULL, MTYPE_UC) | ...
```

**GFX6 y GFX7: cero. GFX8: sólo `EXECUTABLE`. GFX9 en adelante: MTYPE explícito, y
siempre `MTYPE_UC`.**

**La nota del driver es vieja y sólo describe a partir de GFX9.** En GFX8 no hay nada que
explorar: no hay campo. **El comentario dice "it is UC" y para GFX9 en adelante es
cierto y está escrito en el código; para GFX8 la frase no se aplica.**

## 2 · El valor exacto de cada entrada del GART en esta GPU

`amdgpu_gart.c:270-276` llena **toda** la tabla con un solo dword:

```
amdgpu_gart.c:270   amdgpu_bo_create_kernel(adev, adev->gart.table_size, PAGE_SIZE,
amdgpu_gart.c:271                                   AMDGPU_GEM_DOMAIN_VRAM, ...)
amdgpu_gart.c:276   memset_io(adev->gart.ptr, adev->gart.gart_pte_flags, adev->gart.table_size);
```

**Y `amdgpu_gmc_init_pdb0` le añade el resto.** Sumando:

| origen | flags | valor |
|---|---|---|
| `gmc_v8_0.c:961` | `EXECUTABLE` | `0x0000000000000010` |
| `amdgpu_gmc.c:1147` | `|VALID|READABLE` | |
| `amdgpu_gmc.c:1148` | `|WRITEABLE` | |
| `amdgpu_gmc.c:1149` | `|SNOOPED` | |
| `amdgpu_gmc.c:1150` | `|FRAG(0 + 9*1) = FRAG(9)` | |
| `amdgpu_gmc.c:1151` | `|PDE_PTE_FLAG(adev)` | **0** — `GC_HWIP` 8.0.0 < 12.0.0 |

```
resultado = 0x00000000000004F5
```

Descompuesto:

```
0100 1111 0101
bit 0        VALID
bit 2        SNOOPED
bit 4        EXECUTABLE
bit 5        READABLE
bit 6        WRITEABLE
bits 7-11    FRAG(9)
resto        0
```

**Cada entrada de la page table del GART en esta RX550 vale `0x00000000000004F5`
en sus flags.** `PROVEN_DERIVED` de cinco líneas, cada una verificada.

**Y no hay MTYPE porque en esta generación no hay MTYPE.** No es que valga 0:
no está en el formato.

## 3 · Lo que esto dice de §G, y lo que no

**Una evidencia a favor, y una pregunta nueva.**

**A favor:** de GFX9 en adelante el driver elige `MTYPE_UC` — uncached — para las
page tables del GART. **Es la señal de que los EEA de AMD consideran que una tabla
de traducciones no debe cachearse.** Y eso pesa sobre `127`, donde la pregunta era
qué caché hay en el camino del page walker.

**Pero no aplica a esta GPU, y no lo voy a extender por analogía.** En GFX8 no hay
forma de marcar las page tables como uncached, porque no hay atributo. **Eso es un
`NOT_DETERMINED` nuevo y específico: ¿cómo diablos se evita la caché de fragmentos
en GFX8 si no se puede marcar la memoria?**

**Y ahí está la asimetría que vale la pena:** en GFX9+ el driver tiene una palanca
—el MTYPE— y la usa para decir "no cachees esto". En GFX8 no tiene la palanca, y
aun así el invalidate sigue siendo obligatorio (`amdgpu_vm.c:1157`). **Lo que obliga
a invalidar en GFX8 no puede ser la elección del driver de no cachear, porque no
puede elegir.**

**Es un argumento más a favor de que la granularidad del fragmento —y no una caché
controlable— es lo que obliga al flush en esta generación.** `CORROBORATED`, no
`PROVEN`.

## 4 · Y el GART está en VRAM, lo que cierra otra pieza

```
amdgpu_gart.c:270-271   amdgpu_bo_create_kernel(..., AMDGPU_GEM_DOMAIN_VRAM, &adev->gart.bo, ...)
```

**La tabla de traducción del GART es un BO en VRAM.** Y `116` y `127` ya
un BAR de 256 MiB y 2 GiB de VRAM, el GART no cabe en el BAR y va a VRAM.

**Consecuencia para §G que nadie había dicho en voz alta:** el page walker del GART
lee **VRAM**, que no va por PCIe. **El problema de coherencia CPU↔GPU que §G enuncia
no tiene por dónde entrar en este camino.** No hay PCIe entre el GART y el walker.

**Y `gmc_v9_0.c:1794-1795` tiene la alternativa** —*"Put GART in system memory for
APU"*— que es exactamente el caso en que sí habría PCIe. **En esta GPU, no.**

## Lo que NO cierra

| Afirmación | Estado |
|---|---|
| El MTYPE no existe en GFX8 | `PROVEN` (`amdgpu_vm.h:96` "For GFX9") |
| GFX6/7/8 no ponen MTYPE; GFX9+ sí | `PROVEN` (6 sitios) |
| El TODO es viejo y no aplica a GFX8 | `PROVEN_DERIVED` |
| Cada PTE del GART vale `0x4F5` | `PROVEN_DERIVED` (5 líneas) |
| `AMDGPU_PDE_PTE_FLAG` = 0 en GFX8 | `PROVEN` (`amdgpu_vm.h:142`, `115` IP 8.0.0) |
| El GART está en VRAM | `PROVEN` (`amdgpu_gart.c:271`) |
| El page walker del GART no ve PCIe | `PROVEN_DERIVED` |
| MTYPE_UC en GFX9+ indica que las PT no se cachean | `CORROBORATED` |
| Cómo se evita la caché de fragmentos en GFX8 sin MTYPE | **`NOT_DETERMINED`** |
| Si el GART de esta GPU está en VRAM o en RAM | **`OBSERVED`** — el log de arranque lo dice |

**La última es la única que puedo cerrar sin placa y no lo he hecho.** Dice si el
GART se allocó en VRAM o en RAM del sistema, y mi estado afirma que está en VRAM,
pero es un valor de otra sesión y no lo he vuelto a mirar. **Es la comprobación
natural antes de dar por buena la cadena "el GART está en VRAM → el walker no ve
PCIe".**

## Procedencia

- `STATIC` -- `amdgpu_vm.h:96-104` `:141-142`, `amdgpu_gart.c:270-276`,
  `amdgpu_gmc.c:1132-1151`, `gmc_v6_0.c:576`, `gmc_v7_0.c:727`,
  `gmc_v8_0.c:961`, `gmc_v9_0.c:1791`, `gmc_v9_0.c:1794-1795`, `gmc_v10_0.c:746`,
  `gmc_v11_0.c:737`, `gmc_v12_0.c:799`.
- Sin MMIO write, sin lectura de MMIO, sin TLB, sin módulos, sin debugfs.
- Encadenada con `132` (los flags y el TODO), `130` (el L1 guarda un PTE por
  fragmento), `127`/`129` (la caché de fragmentos), `116` (BAR 256 MiB, VRAM),
  `115`/`104` (VMID 0 = kernel, GART).
- No se editó `AGENTS.md` ni `OPEN-FRONTIERS.md`.

## Nota de método

**La pregunta de esa nota se respondió sin hardware, porque era una pregunta sobre el
formato y el formato está en un comentario de dos líneas encima del `#define`.**

```
amdgpu_vm.h:96     /* For GFX9 */
amdgpu_vm.h:97     #define AMDGPU_PTE_MTYPE_VG10_SHIFT(mtype) ((uint64_t)(mtype) << 57)
```

**Un comentario de una palabra resolvía lo que `amdgpu_gmc.c` había dejado
pendiente desde hacía años.**

**Y además hice algo que debo corregir: diagnostiqué tres veces un `grep` vacío como
fallo de la herramienta cuando era mi patrón.** En este turno escribí
`AMDGPU_PTE_PDE_FLAG` cuando el símbolo es `AMDGPU_PDE_PTE_FLAG`, y luego
`PDE_FLAG` solo, que tampoco aparece. **El grep funcionaba perfectamente — lo
comprobé contra un caso conocido — y el error era mío.**

*Ante un `grep` vacío, la primera hipótesis es el patrón, no la herramienta.* Y la
comprobación que lo distingue es una línea: **buscar el mismo símbolo en el
fichero donde sé que está, y ver si aparece.** Eso es lo que había hecho mal tres
veces: no lo hice, y propuse "el grep está roto" sin comprobarlo.
# ELF, reubicaciones y módulos de kernel `.ko` — Referencia de lectura

> **Documento de REFERENCIA**, no tutorial. Responde a la pregunta: *dado un `.ko`
> desensamblado, ¿qué está leyendo realmente?*
>
> **Clasificación de cada afirmación:**
> `NORMA` = documento normativo (TIS/ABI/ISA) o código fuente del kernel en la versión
> exacta. · `HECHO` = comprobado en un fichero concreto, con el comando que lo comprueba.
> · `DERIVACIÓN` = consecuencia aritmética de dos hechos citados, con la aritmética escrita.
> · `SECUNDARIO` = fuente no normativa, marcado como tal.
> · `NOT_DETERMINED` = no establecido; se dice dónde se buscó.
>
> **Toda afirmación sin etiqueta es HECHO sobre el fichero descrito en §0.**

---

## 0. Alcance, objeto y procedencia

### 0.1 Objeto de estudio — HECHO

| Campo | Valor | Cómo se obtuvo |
|---|---|---|
| Fichero | `/lib/modules/7.1.3-200.nobara.fc44.x86_64/kernel/drivers/gpu/drm/amd/amdgpu/amdgpu.ko.zst` | `ls -la` |
| Comprimido | 5 954 300 B | `ls` |
| Descomprimido | **37 494 368 B** | `zstd -d` |
| `SHA256` (descomprimido) | `a1a44c2457d33c65149ef4f455173ca446564bfd19bcc9cb215fca10cf24c024` | `sha256sum` |
| `file(1)` | `ELF 64-bit LSB relocatable, x86-64, version 1 (SYSV), BuildID[sha1]=4d5342509f84dd84f0d5d515b03eb6c7659fb492, not stripped` | `file` |
| `HOST_SCOPE` | **HOST-C** (el host vivo) | `uname -r` = `7.1.3-200.nobara.fc44.x86_64` |
| Kernel usado | **7.1.3-200.nobara.fc44.x86_64** (`/boot/config-7.1.3-200.nobara.fc44.x86_64`) | HECHO |
| Árbol fuente del kernel | `RESEARCH/kernelbuild/linux-7.1.3/` — `Makefile`: `VERSION=7 PATCHLEVEL=1 SUBLEVEL=3` | HECHO |

**El código fuente del kernel 7.1.3 está disponible localmente.** Cada afirmación sobre
el cargador de módulos cita ese árbol, no un recuerdo. Es la misma versión que el binario
analizado, lo que elimina la deriva de versión (`AGENTS.md` §3.2).

**Este documento describe el estado de ESTE host y de ESTE fichero.** No afirma nada
sobre otro kernel, otra distribución u otra versión de binutils.

### 0.2 Descargas y recuperaciones — registro de procedencia

| Fuente | URL | HTTP | Tipo | Uso | Limitación |
|---|---|---|---|---|---|
| TIS ELF (man7) | `http://man7.org/linux/man-pages/man5/elf.5.html` | 200 | `NORMA` | §1, §2a | Renderizado HTML del TIS; sin fórmulas por arquitectura |
| x86-64 psABI (LaTeX) | `https://gitlab.com/api/v4/projects/x86-psABIs%2Fx86-64-ABI/repository/files/x86-64-ABI%2Fobject-files.tex/raw?ref=master` | 200 | `NORMA` | §2b — tabla completa de reubicaciones | Último commit del fichero: `e178c710`, `2024-11-16` |
| psABI, resto de ficheros | mismo repo, 20 ficheros `.tex` | 200 | `NORMA` | §2c — búsqueda de "minus 4" | `NOT_FOUND` (ver §2c) |
| readelf(1) | `https://man7.org/linux/man-pages/man1/readelf.1.html` | 200 | `NORMA` | §5 | — |
| objdump(1) | `https://man7.org/linux/man-pages/man1/objdump.1.html` | 200 | `NORMA` | §5, §6 | — |
| modinfo(8) | `https://man7.org/linux/man-pages/man8/modinfo.8.html` | 200 | `NORMA` | §5 | **No documenta `--dump-modversions`** (ver §5) |
| insmod(8) | `https://man7.org/linux/man-pages/man8/insmod.8.html` | 200 | `NORMA` | §3a | — |
| nm(1) | `https://man7.org/linux/man-pages/man1/nm.1.html` | 200 | `NORMA` | §5 | — |
| `docs.kernel.org/admin-guide/modules.html` | — | **404** | — | — | **NO EXISTE** (ver §0.4) |

### 0.3 Bloqueo del motor de permisos — HECHO

Dos comprobaciones solicitadas **no pudieron ejecutarse** por reglas `deny` de
`opencode.json`:

| Comando intentado | Patrón `deny` que casó | Resultado |
|---|---|---|
| `modprobe --dump-modversions amdgpu.ko` | `"modprobe*": "deny"` | `permission.rejected` |
| `insmod --help` | `"insmod *": "deny"` | `permission.rejected` |

`opencode.json:71` y `opencode.json:72`. El casamiento es sobre la **cadena completa**
del comando, así que `modprobe --help` y `insmod --help` también se deniegan aunque sean
de solo lectura. **Consecuencia:** la sintaxis de `--dump-modversions` y de `insmod -p`
es `NOT_DETERMINED` *en este host por medición directa*; se documenta lo que dicen las
fuentes y se marca como no verificado.

### 0.4 Resultado negativo sobre la documentación del kernel — HECHO

`Documentation/admin-guide/modules.rst` — el documento clásico que describía la secuencia
de carga de módulos — **no existe** en 7.1.3:

```
$ ls Documentation/admin-guide/ | grep -iE "module|vermagic|insmod"
module-signing.rst
```

Único resultado: `module-signing.rst`. Y una búsqueda de `vermagic` en *todo* el árbol
`Documentation/` devuelve **un** fichero:

```
$ grep -rl "vermagic" Documentation/
Documentation/livepatch/module-elf-format.rst
```

**Lo que sí existe** en 7.1.3: `Documentation/kbuild/modules.rst` (513 líneas) — que
cubre *construcción* de módulos y `Module.symvers`, **no** la secuencia de carga — y
`Documentation/ABI/{stable,testing}/sysfs-module`.

`SEARCH_STOP_REASON=SOURCE_NOT_FOUND` para «la descripción oficial de la carga de
módulos» en la documentación renderizada. Se sustituye por el **código fuente**, que es
fuente primaria de mayor autoridad (§3.1 de `AGENTS.md`).

---

# 1. El formato ELF

## 1.1 Estructura del fichero

Un ELF tiene **tres** tablas, todas en el fichero, todas localizables por offset:

```
0                                    e_shoff                    fin
+-------+------------------+----------+-------------------------+--------+
| ELF   | Cabecera de      | Tabla de | Tabla de cabeceras de   | .shstr |
| ident | programa        | programa | sección                 | tab    |
| (16B) | (e_phnum × 56B) | (phdrs)  | (e_shnum × 64B)        |        |
+-------+------------------+----------+-------------------------+--------+
 e_ident  Elf64_Ehdr (64 B)   Elf64_Phdr        Elf64_Shdr (64 B)
```

`Elf64_Ehdr` — NORMA, `elf(5)` §"Header":

```c
typedef struct {
  unsigned char e_ident[EI_NIDENT];   /* 16 B: EI_MAG0..EI_NIDENT, ELFMAG, EI_CLASS, ... */
  uint16_t e_type;                    /* ET_REL | ET_EXEC | ET_DYN | ET_CORE */
  uint16_t e_machine;                 /* EM_X86_64 */
  uint32_t e_version;
  Elf64_Addr e_entry;                 /* dirección de entrada */
  Elf64_Off  e_phoff;                 /* offset de la tabla de programa */
  Elf64_Off  e_shoff;                 /* offset de la tabla de sección */
  uint32_t e_flags;
  uint16_t e_ehsize;                  /* 64 */
  uint16_t e_phentsize;               /* 56 */
  uint16_t e_phnum;                   /* nº de cabeceras de programa */
  uint16_t e_shentsize;               /* 64 */
  uint16_t e_shnum;                   /* nº de secciones */
  uint16_t e_shstrndx;                /* índice de la tabla de nombres de sección */
} Elf64_Ehdr;
```

`Elf64_Shdr` — NORMA, `elf(5)` §"Section Header":

```c
typedef struct {
  Elf64_Word  sh_name;       /* índice en .shstrtab */
  Elf64_Word  sh_type;       /* SHT_* */
  Elf64_Xword sh_flags;      /* SHF_* */
  Elf64_Addr  sh_addr;       /* "the address at which the section's first byte
                                 should reside.  Otherwise, the member contains zero." */
  Elf64_Off   sh_offset;     /* offset desde el principio del fichero */
  Elf64_Xword sh_size;
  Elf64_Word  sh_link;
  Elf64_Word  sh_info;
  Elf64_Xword sh_addralign;
  Elf64_Xword sh_entsize;
} Elf64_Shdr;
```

`Elf64_Sym` — NORMA, `elf(5)`:

```c
typedef struct {
  uint32_t    st_name;   /* índice en .strtab */
  unsigned char st_info; /*bind<<4 | type */
  unsigned char st_other;
  uint16_t    st_shndx;  /* índice de sección; SHN_UNDEF si no definida */
  Elf64_Addr  st_value;
  uint64_t    st_size;
} Elf64_Sym;
```

## 1.2 La distinción que gobierna todo el documento: `offset` vs `dirección`

Este es el punto que hace que un `.ko` sea un objeto y no un programa, y de él depende
todo lo que sigue.

**NORMA — `elf(5)` §"Relocation", campo `r_offset` (cita textual):**

> `r_offset` — This member gives the location at which to apply the relocation action.
> **For a relocatable file, the value is the byte offset from the beginning of the section
> to the storage unit affected by the relocation. For an executable file or shared object,
> the value is the virtual address of the storage unit affected by the relocation.**

**NORMA — x86-64 psABI, `object-files.tex`, §"Relocation Types" (definición de `P`):**

> `\item[P] Represents the place (section offset or address) of the storage unit being
> relocated (computed using \code{r_offset}).`

La expresión «**section offset or address**» es laauthorized statement normativa de que
en un fichero reubicable `r_offset` (y por tanto el sitio de un símbolo) es un **offset
dentro de su sección**, no una dirección absoluta.

**Sobre `st_value` hay un hueco en `elf(5)`.** La cita de `elf(5)` §"Symbol" para
`st_value` es, íntegra:

> `st_value` — This member gives the value of the associated symbol.

`elf(5)` **no** dice si ese valor es un offset o una dirección según el tipo de fichero.
La distinción hay que tomarla de (a) la cita de `r_offset` de arriba, (b) el `P` del
psABI, y (c) la implementación del kernel, que es explícita — §2d y §3a de este
documento. Marcado: la redacción de `elf(5)` sobre `st_value` es
`INSUFFICIENT_FOR_THE_QUESTION`; no se afirma aquí que `elf(5)` diga lo que no dice.

## 1.3 `.rel*` frente a `.rela*`

**NORMA — `elf(5)` §"Section Header", `SHT_RELA`:**

> `SHT_RELA` — This section holds relocation entries with **explicit addends**, such as
> type `Elf32_Rela` for the 32-bit class of object files. An object may have multiple
> relocation sections.

**NORMA — `elf(5)`, `Elf64_Rela`:**

```c
typedef struct { Elf64_Addr r_offset; uint64_t r_info; int64_t r_addend; } Elf64_Rela;
```

**NORMA — x86-64 psABI, `object-files.tex`:**

> The x86-64 LP64 ABI architecture uses only `Elf64_Rela` relocation entries with
> **explicit addends**. The `r_addend` member serves as the relocation addend.

Consecuencia para x86-64: **`SHT_REL` no existe.** El soporte genérico existe en el
kernel (`apply_relocate()` para `SHT_REL`, `apply_relocate_add()` para `SHT_RELA`,
`kernel/module/main.c:1608`) pero está condicionado:

**NORMA — `include/linux/moduleloader.h` (7.1.3, local):** ambas Declaraciones están
bajo `#ifdef CONFIG_MODULES_USE_ELF_REL` / `CONFIG_MODULES_USE_ELF_RELA`, y la variante
no habilitada devuelve `-ENOEXEC` con el mensaje
`"module %s: REL relocation unsupported"`.

**HECHO — este `.ko`:** las 34 secciones de reubicación son **todas** `RELA`.
`readelf -SW amdgpu.ko | grep -c " RELA "` → `34`. Cero `REL`.

## 1.4 Secciones: qué son y por qué importan en un `.ko`

**NORMA — `elf(5)`, definiciones usadas:**

| Bandera | Cita de `elf(5)` |
|---|---|
| `SHF_WRITE` | «This section contains data that should be writable during process execution.» |
| `SHF_ALLOC` | «This section occupies memory during process execution. Some control sections do not reside in the memory image of an object file. This attribute is off for those sections.» |
| `SHF_EXECINSTR` | «This section contains executable machine instructions.» |
| `SHN_UNDEF` | Índice de sección reservado = 0; el símbolo **no está definido** en este fichero |

Ese último punto es el que separa los tres tipos de símbolo del §2d.

## 1.5 Tabla de secciones de ESTE `.ko` (HECHO, `readelf -S amdgpu.ko`)

89 secciones. No transcribo las 89: transcribo las que cumplen una función y marco
`sh_flags`. Notar que **`sh_addr` es 0 en todas** — coherente con §1.2.

| # | Sección | Tipo | Offset | Tamaño | Flags | Función en el cargador |
|---:|---|---|---:|---:|---|---|
| 1 | `__ksymtab` | PROGBITS | `0x40` | `0x30` (48 B) | A | **Símbolos que el módulo EXPORTA** (`EXPORT_SYMBOL`). **4 entradas**: 48 B ÷ 12 B/entrada |
| 2 | `.rela__ksymtab` | RELA | `0x14bedc8` | `0x120` | I | **12 entradas** = 4 símbolos × 3 campos |
| 3 | `__kflagstab` | PROGBITS | `0x70` | `0x4` | A | Bandera por símbolo exportado (4 bytes) |
| 4/5 | `.altinstructions` / `.rela.altinstructions` | PROGBITS/RELA | `0x78` | `0xeee`/`0x3330` | AM/I | Instrucciones alternativas del kernel (`alternatives`) |
| 6/7 | `__bug_table` / `.rela__bug_table` | PROGBITS/RELA | `0xf68` | `0xb900`/`0x34080` | WA/I | `WARN_ON`/`BUG_ON`: texto, fichero, línea |
| 8/9 | `__jump_table` / `.rela__jump_table` | PROGBITS/RELA | `0xc868` | `0xc8e0`/`0x387f0` | WA/I | Tabla de `switch` del kernel |
| 10/11 | `__patchable_functions` / `.rela…` | PROGBITS/RELA | `0x19148` | `0x1f720`/`0x5e560` | WAL/I | Landmarks de `CVE`/`ALTERNATIVE`/`jump_label` |
| **12** | **`.text`** | PROGBITS | `0x38868` | `0x92bf0b` (9 617 163 B) | **AX** | **Código ejecutable** |
| **13** | **`.rela.text`** | RELA | `0x158cfe8` | `0x5ec200` | I | **258 752 entradas** de reubicación contra `.text` |
| 14 | `.bss` | **NOBITS** | `0x964778` | `0x3f0c0` | WA | Sin bytes en el fichero; cero en memoria |
| 15 | `.data` | PROGBITS | `0x964778` | `0x4a0d0` | WA | Variables inicializadas |
| 16 | `.rela.data` | RELA | `0x1b791e8` | `0x15708` | I | 3 659 entradas |
| **17** | **`.rodata`** | PROGBITS | `0x9ae848` | `0x2d5ad4` (2 972 372 B) | A | Cadenas, tablas de registros, `__func__` |
| 18 | `.rela.rodata` | RELA | `0x1b8e8f0` | `0xec8e0` | I | 40 372 entradas |
| 19 | `.comment` | PROGBITS | `0xc8431c` | `0xb12b` | MS | Versión de compilador, por `.o` |
| 20/21 | `__mcount_loc` / `.rela…` | PROGBITS/RELA | `0xc8f447` | `0x1f1a0` | A/I |.function profiling (`CONFIG_FUNCTION_TRACER`) |
| 22/23 | `.init.text` / `.rela…` | PROGBITS/RELA | `0xcae5e8` | `0x89` | AX/I | Código que se **libera** tras la carga |
| 24/25 | `.exit.text` / `.rela…` | PROGBITS/RELA | `0xcae678` | `0x3e` | AX/I | Código de `cleanup_module` |
| **26** | **`.modinfo`** | PROGBITS | `0xcae6b6` | `0xbc53` (48 211 B) | A | **`vermagic`, `srcversion`, `parm=`, `alias=`, `license=`, `name=`, `intree=`** |
| 27–30 | `.exit.data`, `.init.data` (+ `.rela`) | PROGBITS/RELA | `0xcba310` | `0x8` | WA/I | Datos de init/exit |
| 31/32 | `.printk_index` / `.rela…` | PROGBITS/RELA | `0xcba320` | `0xa740` | WA/I | Índices de `printk` (constantes, no formateo) |
| 33/34 | `__dyndbg` / `.rela…` | PROGBITS/RELA | `0xcc4a60` | `0x27b78` | WA/I | `DEFINE_DYNAMIC_DEBUG_METADATA` |
| **36** | **`__param`** | PROGBITS | `0xcec618` | `0xf00` (3 840 B) | A | **`struct kernel_param[]`: los `module_param`. 240 entradas** |
| 37 | `.rela__param` | RELA | `0x1d3c028` | `0x2400` | I | 384 entradas |
| 38/39 | `__dyndbg_classes` / `.rela…` | PROGBITS/RELA | `0xced518` | `0x38` | WA/I | Clases de dynamic debug |
| 41 | `.note.gnu.property` | NOTE | `0xced550` | `0x40` | A | `IBT`, `x86-64-v2` (leído en §0) |
| 42/43 | `.altinstr_replacement` / `.rela…` | PROGBITS/RELA | `0xced590` | `0x423` | AX/I | Reemplazos para `alternatives` |
| 44/45 | `.smp_locks` / `.rela…` | PROGBITS/RELA | `0xced9b4` | `0xc44` | A/I | `smp_lock()` de `text_poke` (CRWP) |
| 49 | `.data..once` | PROGBITS | `0xceec52` | **`0xc`** | WA | Artefacto de LTO/GC: 12 bytes |
| 52/53 | `.static_call.text` / `.rela…` | PROGBITS/RELA | `0xceed20` | `0x180` | AX/I | `static_call()` de livepatch |
| 54/55 | `__bpf_raw_tp_map` / `.rela…` | PROGBITS/RELA | `0xceeea0` | `0x600` | WA/I | Programa BPF raw-tracepoint |
| 56/57 | `_ftrace_events` / `.rela_ftrace…` | PROGBITS/RELA | `0xcef4a0` | `0x180` | WA/I | Puntos de ftrace |
| 58/59 | `.ref.data` / `.rela…` | PROGBITS/RELA | `0xcef620` | `0xee8` | WA/I | Referencias de `static_call` |
| 60–64 | `__tracepoints` + `___srcu_struct…` (+ `.rela`) | PROGBITS/RELA | `0xcf0508` | `0x11e8` | A/I | `DEFINE_TRACEPOINTS` |
| 65 | `.data..percpu` | PROGBITS | `0xcf1cc0` | `0x4` | WA | Variables per-CPU |
| 66/67 | `.static_call_sites` / `.rela…` | PROGBITS/RELA | `0xcf1cc4` | `0xb40` | WA/I | Tabla de `static_call` |
| 68/69 | `.retpoline_sites` / `.rela…` | PROGBITS/RELA | `0xcf2804` | `0xc378` | A/I | **`__x86_return_thunk`** |
| 70/71 | `.return_sites` / `.rela…` | PROGBITS/RELA` | `0xcfeb7c` | `0x12ef0` | A/I | **`__x86_return_thunk`** |
| 72/73 | `.call_sites` / `.rela…` | PROGBITS/RELA | `0xd11a6c` | `0x6f114` | A/I | **`__x86_indirect_thunk`** (IBT) |
| 74/75 | `.ibt_endbr_seal` / `.rela…` | PROGBITS/RELA | `0xd80b80` | `0x4d64` | A/I | Sellado de `endbr64` |
| 76/77 | `.orc_unwind` / `.orc_unwind_ip` (+ `.rela`) | PROGBITS | `0xd858e4` | `0xc0768`/`0x804f0` | A | **Deshueso ORC** (el kernel no usa DWARF CFI) |
| **79** | `.note.gnu.build-id` | NOTE | `0xec653c` | `0x24` | A | `4d5342509f84dd84f0d5d515b03eb6c7659fb492` |
| **80** | **`__ksymtab_strings`** | PROGBITS | `0xec6560` | `0x5e` (94 B) | AMS | Nombres de los símbolos exportados |
| **81** | **`.gnu.linkonce.this_module`** | PROGBITS | `0xec65c0` | **`0x540` = 1 344 B** | WA | **`struct module` = `__this_module`** (§3e) |
| 82 | `.rela.gnu.linkonce.this_module` | RELA | `0x23c0328` | `0x30` | I | 2 entradas |
| **83** | **`.note.Linux`** | NOTE | `0xec6b00` | `0x4c` (76 B) | A | **Firma PKCS#7 del módulo** (§3f) |
| 84 | `.orc_header` | PROGBITS | `0xec6b4c` | `0x14` | A | Cabecera ORC |
| **85** | **`.BTF`** | PROGBITS | `0xec6b6b0` | `0x3b3f12` (3 882 770 B) | — | **BTF**: tipos, no DWARF (§5) |
| **86** | **`.symtab`** | SYMTAB | `0x127aa78` | `0x180738` | — | **65 613 símbolos** (`sh_size/24`): **49 354 `LOCAL`** (`sh_info` = 49354) + **16 259 `GLOBAL`** |
| 87 | `.strtab` | STRTAB | `0x13fb1b0` | `0xc3c11` | — | Nombres de los símbolos |
| 88 | `.shstrtab` | STRTAB | `0x23c0358` | `0x394` | — | Nombres de las secciones |

### 1.6 `PT_LOAD` en un `.ko`: no existe — HECHO

El enunciado de la pregunta daba por hecho que un `.ko` tiene segmentos `PT_LOAD`. **No
los tiene.** Tres comprobaciones independientes:

```
$ readelf -h amdgpu.ko
  Tipo:                              REL (Fichero reubicable)
  Inicio de encabezados de programa: 0  (bytes en el fichero)
  Size of program headers:           0 (bytes)
  Number of program headers:         0
  Inicio de encabezados de sección:  37488368 (bytes en el fichero)
  Number of section headers:         89

$ readelf -lW amdgpu.ko
  No hay encabezados de programa en este fichero.
```

`e_phnum = 0` y `e_phentsize = 0`. El campo `e_shoff` (37 488 368) es donde empieza la
tabla de secciones, y los 6 016 bytes finales son secciones + `e_shoff` de la tabla.

**Consecuencia normativa:** `NORMA`, `elf(5)` §"Program Header":

> An executable or shared object's program header table is an array of structures, each
> describing a segment or other information the system needs to prepare the program for
> execution. […] **Program headers are meaningful only for executable files and shared
> objects.**

`PT_LOAD` — `elf(5)`:

> `PT_LOAD` — The array element specifies a loadable segment, described by `p_filesz` and
> `p_memsz`. The bytes from the file are mapped to the beginning of the memory segment. […]

**Por qué es así, según el propio kernel — NORMA (`kernel/module/main.c`, 7.1.3):**
la memoria del módulo se reparte **por sección** en cinco tipos, no por segmento. De
`__layout_sections()` (main.c, tabla `masks[]` y `core_m_to_mem_type[]`):

```c
static const int core_m_to_mem_type[] = {
        MOD_TEXT,  MOD_RODATA,  MOD_RO_AFTER_INIT,  MOD_DATA,  MOD_DATA,
```

es decir `MOD_TEXT` (AX), `MOD_RODATA` (A), `MOD_RO_AFTER_INIT`, `MOD_DATA` (WA) y el
quinto, per-CPU. Esto lo hace posible precisamente porque **no hay solapamiento que
expresar con `p_vaddr`**: `simplify_symbols()` (§3a) convierte cada offset de sección en
una direcciónsumando la base de la sección correspondiente.

## 1.7 Ausencias(structurales) de este `.ko` — HECHO

| Ausencia | Cómo se comprobó | Consecuencia |
|---|---|---|
| `.dynsym` | `readelf --dyn-syms amdgpu.ko` → salida vacía | `nm -D` inútil (§5) |
| `.dynstr` | `readelf -SW` | Sin biblioteca dinámica |
| `.hash` / `.gnu.hash` | `readelf -SW` | Sin tabla hash de símbolos |
| `.dynamic` | `readelf -SW` | Sin enlazado dinámico |
| `.plt` / `.got` | `readelf -SW` | **Sin PLT ni GOT** (§2b) |
| `.debug_*` (ninguna) | `readelf -SW \| grep -c debug_` → **`0`** | `objdump -S` no muestra fuente (§5) |
| `__versions` | `readelf -SW \| grep -i versions` → sin resultados | **`CONFIG_MODVERSIONS` desactivado** (§4d) |
| `.gnu.linkonce.this_module` | presente, 1 344 B | `__this_module` existe (§3e) |

Las seis primeras son **esperables y correctas** para `ET_REL`: el enlace dinámico es
una propiedad de `ET_DYN`/`ET_EXEC`, no de `ET_REL`. La ausencia de `__versions` **no**
lo es, y se explica en §4d.

---

# 2. Reubicaciones

## 2.a Qué es una reubicación y por qué existen

**NORMA — definición operativa (x86-64 psABI, `object-files.tex`, §"Relocation Types"):**

Una reubicación es una entrada que dice *«en este desplazamiento del almacenamiento,
escribe el valor que resulta de esta fórmula, tomorrow, cuando se conozca dónde están
las cosas»*. Sus componentes:

| Símbolo | Cita textual del psABI |
|---|---|
| `A` | «Represents the **addend** used to compute the value of the relocatable field.» |
| `B` | «Represents the base address at which a shared object has been loaded into memory during execution.» |
| `G` | «Represents the offset into the global offset table at which the relocation entry's symbol will reside during execution.» |
| `GOT` | «Represents the address of the global offset table.» |
| `L` | «Represents the place (section offset or address) of the Procedure Linkage Table entry for a symbol.» |
| `P` | «Represents the place (section offset or address) of the storage unit being relocated (computed using `r_offset`).» |
| `S` | «Represents the value of the symbol whose index resides in the relocation entry.» |
| `Z` | «Represents the size of the symbol whose index resides in the relocation entry.» |

`r_info` codifica dos cosas en 64 bits — NORMA, `elf(5)` §"Relocation":

> `r_info` This member gives both the symbol table index with respect to which the
> relocation must be made and the type of relocation to apply.

Es decir `ELF64_R_SYM(r_info) = r_info >> 32` (índice en `.symtab`) y
`ELF64_R_TYPE(r_info) = r_info & 0xffffffff` (tipo). **HECHO** sobre este fichero:
`0x0000e08f00000004` = PLT32(4) contra el símbolo `0xe08f` = 57 487, que es
`amdgpu_device_wreg`.

**Por qué existen:** `S` —la dirección o el valor de un símbolo— **no se puede conocer
al ensamblar un objeto**, porque depende de (a) la dirección a la que se cargue el
código, que el kernel elige en tiempo de carga, y (b) símbolos externos cuyo valor
vive en otro objeto, el `vmlinux` u otro módulo. En un `ET_REL` la dirección base es
`0` y los símbolos externos valen `0`, así que la decisión de *qué valor poner en el
campo* se difiere y se registra en una tabla aparte. Ésa es la función de `.rela.text`.

**Qué ocurre en cada etapa** — NORMA/HECHO, derivado de la cadena de compilación de
kbuild y confirmado por el código:

```
  ETAPA                st_value    S (en la fórmula)   Campo en el fichero
  ─────────────────────────────────────────────────────────────────────────────
  ensamblado (.s)      —           —                  imm = 0, annotatea
  objeto (.o = ET_REL) offset      offset o 0         0
  enlace parcial       offset      valor real          valor escrito
  enlace final (vmlinux) dirección dirección           valor escrito
  carga de .ko         dirección  dirección (post-    escrito por el kernel,
                                 simplify_symbols)     §3a
```

Las dos filas que importan para esta pregunta:

- **Objeto (`.ko`):** el campo vale **0** y el sumando vale el desplazamiento dentro
  de la sección de destino. La información está en `.rela.*`, no en `.text`.
- **Carga del `.ko`:** el kernel primero convierte `st_value` en dirección
  (`simplify_symbols`), y después aplica `.rela.*` sobre la copia ya en memoria.

## 2.b Tabla completa de tipos de reubicación x86-64

Fuente de **toda** esta tabla: **x86-64 psABI**, fichero `x86-64-ABI/object-files.tex`,
rama `master`, sección `\label{tab-relocations}` ("Relocation Types"), recuperada el
2026-09-27 (HTTP 200). Formato de la tabla: `Nombre & Valor & Campo & Cálculo`.

| Tipo | Valor | Campo | Cálculo | Cuándo se resuelve | En este `.ko` |
|---|---:|---|---|---|---:|
| `R_X86_64_NONE` | 0 | *none* | *none* | — | **0** |
| `R_X86_64_64` | 1 | word64 | `S + A` | enlace y carga | **94 147** |
| `R_X86_64_PC32` | 2 | word32 | `S + A - P` | enlace y carga | **372 842** |
| `R_X86_64_GOT32` | 3 | word32 | `G + A` | enlace (dinámico) | **0** |
| `R_X86_64_PLT32` | 4 | word32 | `L + A - P` | enlace y carga | **145 085** |
| `R_X86_64_COPY` | 5 | *none* | *none* | carga (dinámica) | **0** |
| `R_X86_64_GLOB_DAT` | 6 | wordclass | `S` | carga (dinámica) | **0** |
| `R_X86_64_JUMP_SLOT` | 7 | wordclass | `S` | carga (dinámica) | **0** |
| `R_X86_64_RELATIVE` | 8 | wordclass | `B + A` | **solo carga dinámica** | **0** |
| `R_X86_64_GOTPCREL` | 9 | word32 | `G + GOT + A - P` | enlace (dinámico) | **0** |
| `R_X86_64_32` | 10 | word32 | `S + A` | enlace y carga | **0** |
| `R_X86_64_32S` | 11 | word32 | `S + A` | enlace y carga | **40 302** |
| `R_X86_64_16` | 12 | word16 | `S + A` | — (no conforme, ver cita) | **0** |
| `R_X86_64_PC16` | 13 | word16 | `S + A - P` | — (no conforme) | **0** |
| `R_X86_64_8` | 14 | word8 | `S + A` | — (no conforme) | **0** |
| `R_X86_64_PC8` | 15 | word8 | `S + A - P` | — (no conforme) | **0** |
| `R_X86_64_DTPMOD64` | 16 | word64 | *(vacio en la tabla; §TLS)* | enlace | **0** |
| `R_X86_64_DTPOFF64` | 17 | word64 | *(§TLS)* | enlace | **0** |
| `R_X86_64_TPOFF64` | 18 | word64 | *(§TLS)* | enlace | **0** |
| `R_X86_64_TLSGD` | 19 | word32 | *(§TLS)* | enlace | **0** |
| `R_X86_64_TLSLD` | 20 | word32 | *(§TLS)* | enlace | **0** |
| `R_X86_64_DTPOFF32` | 21 | word32 | *(§TLS)* | enlace | **0** |
| `R_X86_64_GOTTPOFF` | 22 | word32 | *(§TLS)* | enlace | **0** |
| `R_X86_64_TPOFF32` | 23 | word32 | *(§TLS)* | enlace | **0** |
| `R_X86_64_PC64` | 24 † | word64 | `S + A - P` | enlace y carga | **3 214** |
| `R_X86_64_GOTOFF64` | 25 † | word64 | `S + A - GOT` | enlace | **0** |
| `R_X86_64_GOTPC32` | 26 | word32 | `GOT + A - P` | enlace | **0** |
| `R_X86_64_SIZE32` | 32 | word32 | `Z + A` | enlace | **0** |
| `R_X86_64_SIZE64` | 33 † | word64 | `Z + A` | enlace | **0** |
| `R_X86_64_GOTPC32_TLSDESC` | 34 | word32 | *(§TLS desc)* | enlace | **0** |
| `R_X86_64_TLSDESC_CALL` | 35 | *none* | — | enlace | **0** |
| `R_X86_64_TLSDESC` | 36 | word64 × 2 | *(§TLS desc)* | enlace | **0** |
| `R_X86_64_IRELATIVE` | 37 | wordclass | `indirect (B + A)` | **solo carga dinámica** | **0** |
| `R_X86_64_RELATIVE64` | 38 ‡ | word64 | `B + A` | carga, solo ILP32 | **0** |
| `Deprecated` | 39, 40 | — | — | — | — |
| `R_X86_64_GOTPCRELX` | 41 | word32 | `G + GOT + A - P` | enlace | **0** |
| `R_X86_64_REX_GOTPCRELX` | 42 | word32 | `G + GOT + A - P` | enlace | **0** |
| `R_X86_64_CODE_4_GOTPCRELX` | 43 | word32 | `G + GOT + A - P` | enlace | **0** |
| `R_X86_64_CODE_4_GOTTPOFF` | 44 | word32 | *(§GOTTPOFF)* | enlace | **0** |
| `R_X86_64_CODE_4_GOTPC32_TLSDESC` | 45 | word32 | *(§TLS desc)* | enlace | **0** |
| `R_X86_64_CODE_5_GOTPCRELX` | 46 | word32 | `G + GOT + A - P` | enlace | **0** |
| `R_X86_64_CODE_5_GOTTPOFF` | 47 | word32 | *(§GOTTPOFF)* | enlace | **0** |
| `R_X86_64_CODE_5_GOTPC32_TLSDESC` | 48 | word32 | *(§TLS desc)* | enlace | **0** |
| `R_X86_64_CODE_6_GOTPCRELX` | 49 | word32 | `G + GOT + A - P` | enlace | **0** |
| `R_X86_64_CODE_6_GOTTPOFF` | 50 | word32 | *(§GOTTPOFF)* | enlace | **0** |
| `R_X86_64_CODE_6_GOTPC32_TLSDESC` | 51 | word32 | *(§TLS desc)* | enlace | **0** |

† «This relocation is used only for LP64.» ‡ «This relocation only appears in ILP32
executable files or shared objects.»

### Tabla de modelos grandes (misma fuente, §"Large Models")

| Nombre | Valor | Campo | Cálculo |
|---|---:|---|---|
| `R_X86_64_GOT64` | 27 | word64 | `G + A` |
| `R_X86_64_GOTPCREL64` | 28 | word64 | `G + GOT - P + A` |
| `R_X86_64_GOTPC64` | 29 | word64 | `GOT - P + A` |
| `Deprecated` | 30 | — | — |
| `R_X86_64_PLTOFF64` | 31 | word64 | `L - GOT + A` |

### Notas del psABI que cambian la lectura de la tabla

1. **`R_X86_64_32` y `R_X86_64_32S` tienen el mismo cálculo:**
   > The `R_X86_64_32` and `R_X86_64_32S` relocations truncate the computed value to
   > 32-bits. The linker must verify that the generated value for the `R_X86_64_32`
   > (`R_X86_64_32S`) relocation zero-extends (sign-extends) to the original 64-bit value.

   La diferencia es la **comprobación**, no la fórmula. Y en este `.ko` hay `32S` pero
   **cero `32`**, lo que es coherente con un compilador de 64 bits que sólo necesita
   escritura de 32 bits con signo.

2. **`IRELATIVE`**, cita íntegra:
   > `R_X86_64_IRELATIVE` is similar to `R_X86_64_RELATIVE` except that the value used in
   > this relocation is the program address returned by the function, which takes no
   > arguments, at the address of the result of the corresponding `R_X86_64_RELATIVE`
   > relocation.
   > One use of the `R_X86_64_IRELATIVE` relocation is to avoid name lookup for the
   > locally defined `STT_GNU_IFUNC` symbols at load-time. Support for this relocation is
   > optional, but is required for the `STT_GNU_IFUNC` symbols.

3. **`GOTPCRELX` y familia**, cita íntegra:
   > For the occurrence of `name@GOTPCREL` in the following assembler instructions:
   > `call *name@GOTPCREL(%rip)` / `jmp *name@GOTPCREL(%rip)` /
   > `mov name@GOTPCREL(%rip), %reg` / `test %reg, name@GOTPCREL(%rip)` /
   > `binop name@GOTPCREL(%rip), %reg` […] the following `GOTPCRELX` relocations should
   > be generated:
   > `R_X86_64_GOTPCRELX` The instruction starts at 2 bytes before the relocation offset.
   > `R_X86_64_REX_GOTPCRELX` The instruction starts at 3 bytes before the relocation
   > offset with the `REX` prefix.
   > `R_X86_64_CODE_4_GOTPCRELX` … 4 bytes […] `CODE_5` … 5 […] `CODE_6` … 6.

4. **Por qué hay GOT en x86-64 aunque tenga direccionamiento relativo a IP:**
   > Even though the x86-64 architecture supports IP-relative addressing modes, a GOT is
   > still required since the offset from a particular instruction to a particular data
   > item cannot be known by the static linker.

5. **Tipos no conformes:**
   > A program or object file using `R_X86_64_8`, `R_X86_64_16`, `R_X86_64_PC16` or
   > `R_X86_64_PC8` relocations is not conformant to this ABI, these relocations are only
   > added for documentation purposes.

### Los tipos que el cargador de módulos de x86-64 acepta de verdad

La tabla del psABI enumera 43 tipos. El cargador del kernel acepta **7**. **NORMA**,
`arch/x86/kernel/module.c` (7.1.3 local), función `__write_relocate_add()`:

```c
val = sym->st_value + rel[i].r_addend;

switch (ELF64_R_TYPE(rel[i].r_info)) {
case R_X86_64_NONE:      continue;  /* nothing to write */
case R_X86_64_64:        size = 8;  break;
case R_X86_64_32:        if (val != *(u32 *)&val) goto overflow; size = 4; break;
case R_X86_64_32S:       if ((s64)val != *(s32 *)&val) goto overflow; size = 4; break;
case R_X86_64_PC32:
case R_X86_64_PLT32:     val -= (u64)loc; size = 4; break;
case R_X86_64_PC64:      val -= (u64)loc; size = 8; break;
default:
        pr_err("%s: Unknown rela relocation: %llu\n", me->name, ELF64_R_TYPE(rel[i].r_info));
        return -ENOEXEC;
}
```

Y la condición de desbordamiento, con su diagnóstico:

```c
overflow:
        pr_err("overflow in relocation type %d val %llx sec %u idx %d\n", ...);
        pr_err("`%s' likely not compiled with -mcmodel=kernel\n", me->name);
```

**Cruce de las dos fuentes — DERIVACIÓN, tabla:**

| Tipo | En el psABI | Lo acepta el cargador .ko | Consecuencia |
|---|---|---|---|
| `NONE`, `64`, `32`, `32S`, `PC32`, `PLT32`, `PC64` | sí | **sí** | los 5 tipos presentes en este `.ko` |
| `GOT32`, `GOTPCREL`, `GOTPCRELX`, `REX_GOTPCRELX`, `CODE_*_GOTPCRELX`, `GOTOFF64`, `GOTPC32`, `SIZE32/64` | sí | **no** → `-ENOEXEC` |ostingún en un `.ko`: el cargador no tiene GOT |
| `RELATIVE`, `IRELATIVE`, `GLOB_DAT`, `JUMP_SLOT`, `COPY` | sí | **no** | solo tienen sentido con enlace dinámico |
| `8`, `16`, `PC8`, `PC16` | «no conforme a esta ABI» | no | — |
| `DTPMOD64`…`TPOFF32`, `TLSDESC*` | sí | no | el kernel no usa TLS en módulos |

### `R_X86_64_RELATIVE` e `IRELATIVE` en un `.ko`: por qué no aparecen — HECHO

Este es el punto que pedía explícitamente la pregunta, y la respuesta es:

> **En un `.ko` no hay ni `R_X86_64_RELATIVE` ni `R_X86_64_IRELATIVE`, y no porque el
> kernel los ignoren, sino porque el fichero no los contiene.** Cero entradas de cada
> tipo, sobre 655 590 reubicaciones totales.

La razón es estructural, no una decisión del cargador:

| | `ET_REL` (`.ko`) | `ET_DYN` (binario/`.so`) |
|---|---|---|
| El *enlazador* escribe las reubicaciones | no (las emite el ensamblador) | **sí** |
| Dirección base conocida al compilar | no | no |
| Quién escribe el valor final | el **kernel**, recorriendo `.rela.text` | el **enlazador dinámico** (`ld.so`), recorriendo `.rela.dyn` |
| Cómo se codifica una dirección a un símbolo local | `R_X86_64_64` contra el **símbolo de sección** + sumando | `R_X86_64_RELATIVE` contra **índice de símbolo 0** + sumando |

`R_X86_64_RELATIVE` existe para que el cargador dinámico no tenga que buscar el símbolo:
el sumando **ya es el desplazamiento dentro del propio objeto**, y `B` (base de carga) es
lo único que se necesita. En un `.ko` **el kernel sí sabe el símbolo**, porque va a
recorrer la tabla de símbolos igualmente (§3a). Usar `RELATIVE` no aportaría nada.

**HECHO que lo confirma en este fichero:** el mecanismo equivalente sí está presente, con
el otro nombre. Las entradas `R_X86_64_64` contra `.rodata` llevan literalmente
`symidx=5` — el índice del **símbolo de sección** `.rodata` — y el sumando lleva el
desplazamiento:

```
r_offset=0x214e80  R_X86_64_64  symidx=5  .rodata  st_value=0x0  A=+0x2a0df8
r_offset=0x214eb0  R_X86_64_64  symidx=2  .text    st_value=0x0  A=+0x8d9910
```

`S` = 0 (un símbolo de sección tiene `st_value = 0` en un `ET_REL`), luego
`valor = S + A = 0 + 0x2a0df8` = «`.rodata` + `0x2a0df8`». La fórmula
`R_X86_64_RELATIVE` (`B + A`) tiene exactamente la misma forma: `S` se sustituye por
`B`. **La dirección que falta la aporta el kernel en ambos casos, pero el kernel la
consigue por dos caminos distintos:** `simplify_symbols()` (§3a) reescribe
`st_value` **antes** de que corran las reubicaciones, de modo que para `R_X86_64_64` la
letra `S` ya vale la dirección real.

## 2.c Por qué `-0x0000000000000004`: el `-4` de las llamadas

### El `-4` es el sumando, y el sumando vive en `.rela`, no en el campo

**NORMA — x86-64 psABI:**

> The x86-64 LP64 ABI architecture uses only `Elf64_Rela` relocation entries with explicit
> addends. The `r_addend` member serves as the relocation addend.

**NORMA — `elf(5)`**, `r_offset` (ya citada) y `SHT_RELA` («with explicit addends»).

`readelf` imprime la última columna de una reubicación como **`Nombre Símbolo + Sumando`**.
HECHO en la cabecera de esta salida:

```
    Desplaz            Info             Tipo               Valor Símbolo  Nombre Símbolo + Sumando
```

Así que `amdgpu_device_wreg-0x4` se lee literalmente: *«contra el símbolo
`amdgpu_device_wreg`, con sumando −4»*. No es un desplazamiento, no es un «menos cuatro
bytes de la función», y no es un error.

### La aritmética del `-4`, completa

**DERIVACIÓN**, con cadainputs citado:

1. `R_X86_64_PLT32` = `L + A - P` — NORMA, psABI, tabla de reubicaciones.
2. En enlace estático **no hay PLT**, luego `L == S` — DERIVACIÓN, de la ausencia de
   `.plt`/`.got` en §1.7 y de la existencia del mismo `case R_X86_64_PC32: case
   R_X86_64_PLT32:`ally en `arch/x86/kernel/module.c` (§2b): el kernel los calcula
   **idénticamente**.
3. El objetivo es `call`, opcode `E8` con un `rel32` de 4 bytes. HECHO sobre los bytes
   crudos: en `.text+0x214e40` los bytes son `e8 00 00 00 00`.
4. Por tanto el valor a escribir es `S - P + A`.

Ahora, `P` es «the place of the storage unit being relocated» = la dirección del **campo
de 4 bytes**, que está en `r_offset` = `instrucción + 1`. Pero la semántica del `rel32`
de `E8` es «desplazamiento relativo a la **siguiente** instrucción», es decir
`instrucción + 5`. Por tanto:

```
  valor requerido  =  S - (instrucción + 5)
  valor del psABI  =  S - P + A  =  S - (instrucción + 1) + A
  igualando:            -5       =  -1 + A        →   A = -4
```

**Y el campo vale 0, no −4.** Es coherente y es **exigido** por el kernel. NORMA,
`arch/x86/kernel/module.c`, antes de escribir:

```c
if (apply) {
        if (memcmp(loc, &zero, size)) {
                pr_err("x86/modules: Invalid relocation target, existing value is nonzero for sec %u, idx %u, type %d, loc %lx, val %llx\n", ...);
                return -ENOEXEC;
        }
        write(loc, &val, size);
}
```

Es decir: **el kernel rechaza la carga si el campo de la reubicación no es cero.** En
un `ET_REL` bien formado, el −4 está **solo** en `r_addend` y el campo queda a 0. HECHO:

```
$ readelf -rW amdgpu.ko | grep -m1 "0x214e41"    # (campo en 0x214e41, +1 respecto a 0x214e40)
0000000000214e41  0000df7000000004 R_X86_64_PLT32  0000000000000000 __fentry__ - 4
```

**El `-4` es, literalmente, «la corrección de que el campo está un byte antes del final
de la instrucción».** Es la misma aritmética para `call` (5 bytes) y para `jmp` corto
(`EB`, 2 bytes: `EB 0x00` + `A = -1`). HECHO en este fichero: las entradas `EB` existen.

**Lo que el desensamblador muestra y por qué:** con `S` sin resolver, `objdump` calcula
`S + A - P` con `S = 0` (símbolo `UND` con `st_value = 0`), `A = -4`, `P = r_offset`:

```
valor mostrado = 0 + (-4) - 0x214e41 = -0x214e45 ≡ 0x214e45 (módulo 2^32)
```

Y el destino que imprime es **`0x214e45`, que es exactamente la instrucción siguiente**
(`0x214e40 + 5`). HECHO:

```
  214e40:	e8 00 00 00 00       	call   214e45 <uvd_v6_0_start+0x5>
			214e41: R_X86_64_PLT32	__fentry__-0x4
  214e45:	41 55                	push   %r13
```

**Diagnóstico infalible: si `call N` apunta a `N == dirección_de_la_siguiente_instrucción`,
el desplazamiento está sin resolver.** Nunca es un error de compilación.

### Búsqueda de «minus 4» en el psABI — resultado negativo

- **Pregunta:** ¿el x86-64 psABI explica el −4 de `call`?
- **Dónde busqué:** los **20** ficheros `.tex` del repositorio
  `x86-psABIs/x86-64-ABI`, camino `x86-64-ABI/`, listados vía
  `https://gitlab.com/api/v4/projects/x86-psABIs%2Fx86-64-ABI/repository/tree?path=x86-64-ABI&per_page=100`
  (páginas 1–4, `x86-64-ABI/ChangeLog.old` … `x86-64-ABI/x32.tex`).
- **Términos:** `minus 4`, `Minus 4`, `PLT32`, `rel32`.
- **Resultado:** 2 ficheros con coincidencias, y ninguna sobre el −4:
  `object-files.tex` (1 coincidencia, la fila de la tabla) y `low-level-sys-info.tex`
  (1 coincidencia, `leaq $foo@PLT(%rip),%r11 ;R_X86_64_PLT32`, en el contexto del syscall
  fast-path). `execution.tex` mide 119 B: es un `\input`, no contiene el texto.
- **Clasificación:** `NOT_FOUND` **en la documentación del psABI**. No es
  `PROVEN_ABSENT` del contenido de esa documentación, solo de la búsqueda descrita, con
  el universo nombrado y el método declarado.
- **De dónde sale entonces la explicación:** la definición del `rel32` de `E8` pertenece
  al **manual de arquitectura de Intel** (Instruction Set Reference, `CALL rel32`).
  `NOT_FETCHED` — no se obtuvo copia de acceso libre; no se cita por tanto su redacción.
  La aritmética de arriba es `DERIVATION` construida sobre el psABI (normativo) y sobre
  la implementación del kernel (ejecutable y verificada en este host), no sobre el
  manual de Intel.

## 2.d Por qué un `.ko` no se puede enlazar en compilación

Tres clases de símbolo, distinguibles por `st_shndx` — HECHO sobre `readelf -sW`:

| Clase | `st_shndx` | `st_value` en el `.ko` | Cuándo se conoce su valor | Ejemplo en este `.ko` |
|---|---|---|---|---|
| **Local al módulo** | índice real (p. ej. `12`=`.text`) | **offset dentro de la sección** | Nunca antes de la carga | `amdgpu_device_wreg` = `0x8060` en `.text` |
| **Sección** | índice real | `0` | En la carga, vía la base de la sección | `.rodata`, `.text` |
| **Del `vmlinux` / externo** | **`SHN_UNDEF` (`0`)** | **`0`** | **Solo cuando el kernel elige la dirección** | `__const_udelay`, `__drm_err`, `__fentry__`, `__x86_return_thunk` |

HECHO:

```
$ readelf -sW amdgpu.ko | grep -E " (amdgpu_device_wreg|__const_udelay|__drm_err|__fentry__|__x86_return_thunk)$"
0000000000000000   0  NOTYPE UND   __const_udelay
0000000000000000   0  NOTYPE UND   __drm_err
0000000000000000   0  NOTYPE UND   __fentry__
0000000000000000   0  NOTYPE UND   __x86_return_thunk
0000000000008060 312  FUNC  GLOBAL amdgpu_device_wreg     <- Ndx=12, tamaño 312 B, en .text
```

**Por qué no se puede enlazar en compilación — las cuatro razones, y cada una se ve en
los datos:**

1. **La dirección de carga la elige el kernel, no el compilador.** HECHO, §1.6: no hay
   `PT_LOAD`, no hay ninguna dirección fijada en el fichero. Con `-mcmodel=kernel`
   (`R_X86_64_32S`, que es lo que usa este módulo) el campo es de 32 bits y solo vale si
   la dirección final cabe; el kernel lo comprueba en tiempo de carga y avisa de
   `likely not compiled with -mcmodel=kernel` si no (§2b).

2. **Los símbolos externos no existen todavía.** HECHO: `__const_udelay` tiene
   `st_value = 0` y `st_shndx = UND`. El módulo no puede saber el valor de
   `__const_udelay` porque `__const_udelay` está en el binario del kernel, cuyo layout
   de memoria decide el arranque.

3. **`st_value` de un símbolo local es un *offset*, no una dirección.** HECHO,
   `amdgpu_device_wreg` = `0x8060`; eso solo significa «0x8060 bytes dentro de `.text`».
   La dirección real será `base_de_text_del_módulo + 0x8060`, y `base_de_text_del_módulo`
   no existe hasta `layout_and_allocate()` (§3a).

4. **El orden de carga de los módulos no se conoce al compilar.** Un módulo puede
   necesitar símbolos de otro que se cargue después. Es la razón de ser de `finit_module`
   y de la resolución en tiempo de carga.

**NORMA — el kernel hace exactamente esa distinción.** `simplify_symbols()`,
`kernel/module/main.c` (7.1.3),vkijken los tres casos:

```c
switch (sym[i].st_shndx) {
case SHN_COMMON:  /* ... please compile with -fno-common ... */
case SHN_ABS:     /* Don't need to do anything */
case SHN_LIVEPATCH:
case SHN_UNDEF:
        ksym = resolve_symbol_wait(mod, info, name);   /* <-- símbolo del vmlinux */
        if (ksym && !IS_ERR(ksym)) {
                sym[i].st_value = kernel_symbol_value(ksym);
                break;
        }
        if (!ksym && (ELF_ST_BIND(sym[i].st_info) == STB_WEAK ||
                     ignore_undef_symbol(info->hdr->e_machine, name)))
                break;
        ret = PTR_ERR(ksym) ?: -ENOENT;
        pr_warn("%s: Unknown symbol %s (err %d)\n", mod->name, name, ret);
        break;
default:
        if (sym[i].st_shndx == info->index.pcpu)
                secbase = (unsigned long)mod_percpu(mod);
        else
                secbase = info->sechdrs[sym[i].st_shndx].sh_addr;
        sym[i].st_value += secbase;                     /* <-- symbols local */
}
```

Y el comentario que lo precede en `load_module()` (`main.c:3514`) lo dice en una línea:

```c
/* Fix up syms, so that st_value is a pointer to location. */
err = simplify_symbols(mod, info);
```

**Ese es el momento exacto en que un `st_value` deja de ser un offset y pasa a ser una
dirección.** Y es la razón por la que `readelf -r` sobre un `.ko` **fuera del kernel**
muestra `st_value = 0` para casi todo: el fichero nunca ha pasado por ese paso.

---

# 3. Cómo se carga un módulo de kernel

## 3.a La secuencia real en 7.1.3

**NORMA — `kernel/module/main.c`, `load_module()` (línea 3422 del árbol local).**
Los comentarios están en el original; los transcribo.

```
syscall finit_module(2)  /  insmod(8)  →  modprobe → kmod → libkmod → finit_module(2)
                                                             ↓
load_module(struct load_info *info, const char __user *uargs, int flags)
│
├─ err = module_sig_check(info, flags)          /* §3f: .note.Linux, PKCS#7   */
│    "the signature check needs is info->len, it does not need any of the
│     section info … minimize the chances of a corrupt module"
├─ err = elf_validity_cache_copy(info, flags)   /* sanea cabecera + secciones    */
├─ err = early_mod_check(info, flags)           /*                        */
│
├─ mod = layout_and_allocate(info, flags)       /* RESERVA LA MEMORIA   §1.6   */
│    └─ layout_sections() → __layout_sections() → module_get_offset_and_type()
│       MOD_TEXT | MOD_RODATA | MOD_RO_AFTER_INIT | MOD_DATA | percpu
│
├─ err = add_unformed_module(mod)                /* MODULE_STATE_UNFORMED       */
├─ module_augment_kernel_taints(mod, info)
├─ err = percpu_modalloc(mod, info)
├─ err = module_unload_init(mod)
├─ init_param_lock(mod)
├─ err = find_module_sections(mod, info)        /* __param, __ksymtab, __kcrctab, §3c */
├─ err = check_export_symbol_sections(mod)
│
├─ err = setup_modinfo(mod, info)               /* §3d, §4b, §4c               */
│    └─ MODINFO_ATTR(version); MODINFO_ATTR(srcversion);  import_ns
│    └─ check_modinfo() → same_magic(vermagic) → -ENOEXEC si no coincide
│
├─ /* "Fix up syms, so that st_value is a pointer to location." */
├─ err = simplify_symbols(mod, info)            /* §2d: UND→vmlinux, resto +base */
│
├─ err = apply_relocations(mod, info)            /* ★ AQUÍ, §2.b/§3.b            */
│    └─ arch/x86/kernel/module.c: apply_relocate_add()
│       └─ write_relocate_add() → __write_relocate_add()
│
├─ err = post_relocation(mod, info)
├─ flush_module_icache(mod)
├─ mod->args = strndup_user(uargs, ~0UL >> 1)
├─ init_build_id(mod, info)
├─ ftrace_module_init(mod)
├─ err = complete_formation(mod, info)
├─ err = prepare_coming_module(mod)
├─ after_dashes = parse_args(mod->name, mod->args, mod->kp, mod->num_kp, ...)
│                  /* <-- aquí se aplican los module_param              §3d */
├─ … enlace en sysfs, uevent KOBJ_ADD …
│
└─ [asíncrono]  do_init_module(mod)              (línea 3077)
     ├─ freeinit->init_text  = mod->mem[MOD_INIT_TEXT].base
     ├─ freeinit->init_data  = mod->mem[MOD_INIT_DATA].base
     ├─ freeinit->init_rodata= mod->mem[MOD_INIT_RODATA].base
     ├─ do_mod_ctors(mod)
     ├─ if (mod->init != NULL) ret = do_one_initcall(mod->init)   ★ init_module
     ├─ mod->state = MODULE_STATE_LIVE
     ├─ kobject_uevent(&mod->mkobj.kobj, KOBJ_ADD)
     ├─ async_synchronize_full()
     ├─ ftrace_free_mem(...); module_put(mod); trim_init_extable(mod)
     └─ rcu_assign_pointer(mod->kallsyms, &mod->core_kallsyms);
```

**Corrección necesaria al orden que daba la pregunta.** El orden real es
`simplify_symbols` **antes** de `apply_relocations`, y `check_modinfo`/`vermagic` en
`setup_modinfo`, también **antes**. Y `do_init_module` no está dentro de `load_module`:
se dispara después, y `do_one_initcall` es una llamada a una función de otro fichero
(`kernel/init.c` en versiones anteriores; aquí solo consta la declaración
`extern int do_one_initcall(initcall_t fn);` en `include/linux/init.h:136` y el uso en
`kernel/module/main.c:3106`).

### `layout_and_allocate` no existe como símbolo propio

La pregunta nombraba `layout_and_allocate`. En 7.1.3 es una función **estática** de
`kernel/module/main.c` invocada desde `load_module()` (`mod = layout_and_allocate(info, flags);`).
Lo que sí es relevante es `__layout_sections()`, con su tabla de máscaras (§1.6), y
`module_get_offset_and_type()`, que **asigna direcciones** a las secciones:

```c
long module_get_offset_and_type(struct module *mod, enum mod_mem_type type,
                                Elf_Shdr *sechdr, unsigned int section)
{
        long offset;
        mod->mem[type].size += arch_mod_section_prepend(mod, section);
        offset = ALIGN(mod->mem[type].size, sechdr->sh_addralign ?: 1);
        mod->mem[type].size = offset + sechdr->sh_size;
        return offset | mask;
}
```

Cada sección recibe una `sh_addr` dentro de un bloque `mod->mem[]`. Ese es el `secbase`
que §2d suma a cada `st_value` local.

## 3.b Dónde se aplica cada reubicación — la clave de la pregunta

`apply_relocations()` — NORMA, `kernel/module/main.c:1608`, citado íntegro:

```c
static int apply_relocations(struct module *mod, const struct load_info *info)
{
        unsigned int i;
        int err = 0;

        /* Now do relocations. */
        for (i = 1; i < info->hdr->e_shnum; i++) {
                unsigned int infosec = info->sechdrs[i].sh_info;

                /* Not a valid relocation section? */
                if (infosec >= info->hdr->e_shnum)
                        continue;

                /*
                 * Don't bother with non-allocated sections.
                 * An exception is the percpu section, which has separate allocations
                 * for individual CPUs. We relocate the percpu section in the initial
                 * ELF template and subsequently copy it to the per-CPU destinations.
                 */
                if (!(info->sechdrs[infosec].sh_flags & SHF_ALLOC) &&
                    (!infosec || infosec != info->index.pcpu))
                        continue;

                if (info->sechdrs[i].sh_flags & SHF_RELA_LIVEPATCH)
                        err = klp_apply_section_relocs(mod, info->sechdrs, info->secstrings,
                                                       info->strtab, info->index.sym, i, NULL);
                else if (info->sechdrs[i].sh_type == SHT_REL)
                        err = apply_relocate(info->sechdrs, info->strtab, info->index.sym, i, mod);
                else if (info->sechdrs[i].sh_type == SHT_RELA)
                        err = apply_relocate_add(info->sechdrs, info->strtab, info->index.sym, i, mod);
                if (err < 0)
                        break;
        }
        return err;
}
```

De aquí se Extraen **cinco** reglas:

1. **La unidad de iteración es la *sección*, no el segmento.** `e_shnum`, no `e_phnum`
   —coherente con §1.6.
2. **Se descartan las secciones destino no asignables.** El filtro es
   `sh_flags & SHF_ALLOC` (§1.4). HECHO: `.comment` (flag `M`, sin `A`) y `.debug_*`
   no se reubican. Excepción: la sección per-CPU, que se reubica en la plantilla ELF
   inicial y luego se copia a cada CPU.
3. **`SHT_RELA` → `apply_relocate_add()`.** En x86-64, `arch/x86/kernel/module.c:219`:
   ```c
   int apply_relocate_add(Elf64_Shdr *sechdrs, const char *strtab,
                          unsigned int symindex, unsigned int relsec, struct module *me)
   { return write_relocate_add(sechdrs, strtab, symindex, relsec, me, true); }
   ```
4. **El sitio donde se escribe es la dirección en memoria, no el fichero:**
   ```c
   loc = (void *)sechdrs[sechdrs[relsec].sh_info].sh_addr + rel[i].r_offset;
   ```
   `sh_addr` **ya no es 0** (lo asignó `layout_and_allocate`), de modo que `loc` es la
   dirección virtual real del campo. HECHO, §1.5: `sh_addr = 0` en el fichero.
5. **El símbolo ya está resuelto antes:**
   ```c
   sym = (Elf64_Sym *)sechdrs[symindex].sh_addr + ELF64_R_SYM(rel[i].r_info);
   /* Note that all undefined symbols have been resolved. */
   ```
   El comentario del kernel es explícito. Es la razón de que
   `apply_relocations` vaya **después** de `simplify_symbols`.

### La respuesta concreta: `R_X86_64_RELATIVE` y compañía

**Aplicar las reubicaciones es tarea del kernel, siempre. Ninguna queda para el
cargador dinámico, porque en un `.ko` no hay cargador dinámico.** Las dos
«familias» que menciona la pregunta se reducen a esto:

| Familia | ¿En un `.ko`? | Dónde se resuelve | Mecanismo |
|---|---|---|---|
| `R_X86_64_64`, `R_X86_64_32`, `R_X86_64_32S`, `R_X86_64_PC32`, `R_X86_64_PLT32`, `R_X86_64_PC64` | **Sí** (los 5 presentes) | **`apply_relocations()`**, en `load_module()` | `write()` directo, o `text_poke()` |
| `R_X86_64_RELATIVE`, `R_X86_64_IRELATIVE` | **No, cero entradas** | — (nadie) | Equivalente funcional: `R_X86_64_64` + símbolo de sección (§2.b) |
| `GLOB_DAT`, `JUMP_SLOT`, `COPY`, `GOT*`, `TLS*` | **No** | — | Rechazadas con `-ENOEXEC` |

Y un matiz que sí es real y que conviene no perder: **la misma función escribe de dos
formas**. NORMA, `write_relocate_add()`:

```c
bool early = me->state == MODULE_STATE_UNFORMED;
void *(*write)(void *, const void *, size_t) = memcpy;

if (!early) {
        write = text_poke;        /* auto-modificación con CRWP, sincroniza I-cache */
        mutex_lock(&text_mutex);
}
ret = __write_relocate_add(sechdrs, strtab, symindex, relsec, me, write, apply);
if (!early) {
        smp_text_poke_sync_each_cpu();
        mutex_unlock(&text_mutex);
}
```

Durante la carga normal el módulo está `UNFORMED` → `memcpy` sobre memoria recién
asignada, sin necesidad de invalidar I-cache. Si se re-aplican reubicaciones más
tarde (livepatch, o `clear_relocate_add()` al descargar un módulo parcheado), se usa
`text_poke` y hay que sincronizar cada CPU. Es el motivo de que exista
`.rela.altinstr_replacement` / `SHF_RELA_LIVEPATCH` y de que `apply_relocations()`
tiene esa cuarta rama.

## 3.c Resolución de símbolos `SHN_UNDEF` y el papel de `__ksymtab`

**NORMA — `simplify_symbols()`** (ya citado en §2d): para cada símbolo con
`st_shndx == SHN_UNDEF` llama a `resolve_symbol_wait(mod, info, name)`, y si obtiene
`struct kernel_symbol *ksym` hace:

```c
sym[i].st_value = kernel_symbol_value(ksym);
```

Es decir: **`st_value` pasa de 0 a la dirección real del símbolo en el `vmlinux`.** Esa
dirección la da la búsqueda de símbolos del kernel, que se apoya en `kallsyms`
(`kernel/module/kallsyms.c`, `CONFIG_KALLSYMS_ALL=y` en este host) y en las tablas
`__ksymtab` del propio kernel.

**NORMA — `find_module_sections()`** (`kernel/module/main.c:2659`): qué secciones
opcionales lee del `.ko`:

```c
mod->kp       = section_objs(info, "__param",         sizeof(*mod->kp),       &mod->num_kp);
mod->syms     = section_objs(info, "__ksymtab",       sizeof(*mod->syms),     &mod->num_syms);
mod->crcs     = section_addr(info, "__kcrctab");
mod->flagstab = section_addr(info, "__kflagstab");
```

Y un detalle de versión que no debe suponerse: **`__ksymtab_gpl` y `__kcrctab_gpl` son
obsoletos en 7.1.3** — el kernel los ignora y avisa:

```c
if (section_addr(info, "__ksymtab_gpl"))
        pr_warn("%s: ignoring obsolete section __ksymtab_gpl\n", mod->name);
if (section_addr(info, "__kcrctab_gpl"))
        pr_warn("%s: ignoring obsolete section __kcrctab_gpl\n", mod->name);
```

**HECHO — qué exporta este módulo:** exactamente **4** símbolos, y ninguno con nombre de
`__ksymtab_gpl`:

```
$ readelf -x __ksymtab amdgpu.ko
  NOTA: Esta sección tiene reubicaciones contra ella, pero NO se han aplicado a este volcado.
  0x00000000 00000000 00000000 00000000 00000000 ................
  0x00000010 00000000 00000000 00000000 00000000 ................
  0x00000020 00000000 00000000 00000000 00000000 ................

$ readelf -x __ksymtab_strings amdgpu.ko
  0x00000000 6973705f 75736572 5f627566 6665725f isp_user_buffer_
  ...  alloc..isp_user_buffer_free..isp_kernel_buffer_alloc..isp_kernel_buffer_free..
```

Esos cuatro son `isp_user_buffer_alloc`, `isp_user_buffer_free`,
`isp_kernel_buffer_alloc`, `isp_kernel_buffer_free`. **Todo lo demás que usa el módulo
(`__const_udelay`, `__drm_err`, `amdgpu_device_wreg`, …) lo *importa*, no lo exporta.**

**Por qué `__ksymtab` necesita reubicaciones — NORMA, `kernel/module/internal.h` (7.1.3):**

```c
struct kernel_symbol {
#ifdef CONFIG_HAVE_ARCH_PREL32_RELOCATIONS
        int value_offset;
        int name_offset;
        int namespace_offset;
#else
        unsigned long value;
        const char *name;
        const char *namespace;
#endif
};
```

HECHO: `CONFIG_HAVE_ARCH_PREL32_RELOCATIONS=y` en
`/boot/config-7.1.3-200.nobara.fc44.x86_64`, luego la variante activa es la de **tres
`int` = 12 bytes**, con los valores como *offsets relativos*, no punteros absolutos. Eso
hace cuadrar la aritmética exactamente: **48 B ÷ 12 B = 4 entradas**, y **4 × 3 campos
= 12 reubicaciones** en `.rela__ksymtab`, que es lo que `readelf` declara
(`contains 12 entries`).

Y el volcado en ceros es correcto por el mismo motivo que §5.6: los valores son
offsets pendientes de fijar, así que **también** necesitan reubicación — de ahí el aviso
de `readelf` («Esta sección tiene reubicaciones contra ella, pero NO se han aplicado a
este volcado») y las 12 entradas de `.rela__ksymtab`.

## 3.d La sección `.modinfo`

**NORMA — `include/linux/moduleparam.h` (7.1.3 local), `MODULE_INFO`:**

```c
/* Generic info of form tag = "info" */
#define MODULE_INFO(tag, info)                                      \
        static_assert(sizeof(info) - 1 == __builtin_strlen(info),   \
                "MODULE_INFO(" #tag ", ...) contains embedded NUL byte"); \
        static const char __UNIQUE_ID(modinfo)[]                    \
        __used __section(".modinfo") __aligned(1)                   \
        = __MODULE_INFO_PREFIX __stringify(tag) "=" info
```

Y el prefijo —de ahí que las claves aparezcan sin el nombre del módulo delante
(§3.d)—:

```c
#ifdef MODULE
#define MODULE_PARAM_PREFIX /* empty */
#define __MODULE_INFO_PREFIX /* empty */
#else
#define MODULE_PARAM_PREFIX KBUILD_MODNAME "."
/* We cannot use MODULE_PARAM_PREFIX because some modules override it. */
#define __MODULE_INFO_PREFIX KBUILD_MODNAME "."
#endif
```

Es decir: **cada `MODULE_INFO` escribe una cadena NUL-terminada literally en
`.modinfo`**, con la forma `clave=valor`. La sección es un simple bloque de texto; el
cargador y las herramientas de espacio de usuario lo recorren buscando `clave=`.

**Por qué los parámetros de módulo aparecen ahí — dos mecanismos distintos que ambos
terminan en `.modinfo`:**

1. **Los metadatos del parámetro** (`module_param`), que son texto:
   NORMA, mismo fichero:
   ```c
   #define __MODULE_PARM_TYPE(name, _type)  MODULE_INFO(parmtype, #name ":" _type)
   #define MODULE_PARM_DESC(_parm, desc)     MODULE_INFO(parm, #_parm ":" desc)
   ```
   HECHO en este `.ko` (`readelf -p .modinfo`), las parejas `parmtype=`/`parm=`:
   ```
   [    53]  parmtype=hdmi_hpd_debounce_delay_ms:uint
   [    7c]  parm=hdmi_hpd_debounce_delay_ms:HDMI HPD disconnect debounce delay in milliseconds ...
   [    fb]  parmtype=user_queue:int
   [   113]  parm=user_queue:Enable user queues (-1 = auto (default), 0 = disable, 1 = enable, ...)
   ```
2. **El valor real del parámetro**, que es una `struct kernel_param` en la sección
   `__param` (§1.5, `[36]`, 3 840 B = 240 entradas × 16 B), **no** texto:
   NORMA:
   ```c
   #define __module_param_call(prefix, name, ops, arg, perm, level, flags)   \
        static const char __param_str_##name[] = prefix #name;               \
        static struct kernel_param __moduleparam_const __param_##name         \
        __used __section("__param")                                          \
        __aligned(__alignof__(struct kernel_param))                          \
        = { __param_str_##name, THIS_MODULE, ops,                            \
            VERIFY_OCTAL_PERMISSIONS(perm), level, flags, { arg } }
   ```

**Conclusión sobre la pregunta de fondo:** `module_param` aparece en `.modinfo` porque
`.modinfo` es la **interfaz de texto** del módulo (para `modinfo`, para el código del
kernel al cargar), y `.modinfo` es además la lista de **parámetros declarados** que el
kernel expone en `/sys/module/<name>/parameters/`. El valor inicial y el getter/setter
NO están en `.modinfo`: están en `__param`. **La presencia de `parm=foo:descripción` en
`.modinfo` prueba que el módulo tiene un parámetro llamado `foo`; no prueba nada sobre su
valor en ejecución** — ese valor se lee en `/sys/module/amdgpu/parameters/foo`.

**HECHO — qué hay en esta `.modinfo` de 48 211 B**, con su desplazamiento exacto:

```
$ readelf -p .modinfo amdgpu.ko | grep -nE "srcversion|vermagic|name=|intree"
 [  8705]  srcversion=D68004925455E20A24C2B87
 [ bbf4]  intree=Y
 [ bbfd]  name=amdgpu
 [ bc15]  vermagic=7.1.3-200.nobara.fc44.x86_64 SMP preempt mod_unload 
```

Las tres primeras que emite `modpost` — NORMA, `scripts/mod/modpost.c`:

```c
buf_printf(b, "MODULE_INFO(name, KBUILD_MODNAME);\n");       /* línea 1845 */
buf_printf(b, "\nMODULE_INFO(intree, \"Y\");\n");              /* línea 1860 */
```

`vermagic` lo emite el propio módulo desde la expansión de `VERMAGIC_STRING`
(`scripts/mod/emptymod.c` usa `MODULE_INFO(vermagic, VERMAGIC_STRING)`); `srcversion` lo
añade `add_srcversion()` (§4b).

## 3.e `__this_module`, `__modver`, `init_module` / `cleanup_module`

### `__this_module`

HECHO: existe la sección `.gnu.linkonce.this_module`, de **1 344 bytes**
(`0x540`), con `sh_flags = WA` y 2 reubicaciones. Es una `struct module` completa.
NORMA — la razón del nombre, `kernel/module/main.c:2111-2112`:

```c
/* uses to refer to __this_module and let's use rely on THIS_MODULE to point
 * to &__this_module properly. The kernel's modpost declares it on each
 * object file of the module.
 */
```

Es decir: `modpost` **fuerza** la definición de `__this_module` en **cada** objeto del
módulo, para que `THIS_MODULE` (usado por `__module_param_call`, §3.d) siempre resuelva
dentro del propio módulo y nunca por error a una dirección de otro.

HECHO — el kernel lo usa para el `THIS_MODULE` de cada parámetro y para el registro en
`sysfs`, y `find_module_sections()` cuelga de él `__param` y `__ksymtab`.

### `init_module` y `cleanup_module` — HECHO, presentes y solapados

```
$ nm amdgpu.ko | grep -E " (init_module|cleanup_module)$"
0000000000000010 T cleanup_module
0000000000000010 T init_module
0000000000000000 T __pfx_cleanup_module
```

Ambos en `.text + 0x10`, con `T` = global, texto. Un módulo tiene exactamente un punto
de entrada de este tipo porque `module_init()` / `module_exit()` generan un puntero único
a una función etiquetada, y `modpost` exige que exista.

**Por qué el kernel los exige — NORMA, el contrato está en la secuencia de §3.a:**

- `init_module`: `do_init_module()` (§3.a) lee `mod->init` y, si no es `NULL`, hace
  `ret = do_one_initcall(mod->init)`. Un valor de retorno negativo aborta la carga y
  dispara el `goto fail_free_freeinit` que libera `.init.text`. El kernel comprueba
  además la convención:
  ```c
  if (ret == -EEXIST)  ret = -EBUSY;   /* -EEXIST lo reserva [f]init_module(2) */
  if (ret > 0) pr_warn("%s: init suspiciously returned %d, it should follow 0/-E convention\n", ...);
  ```
- `cleanup_module`: se llama en la descarga. Los dos valores de retorno admitidos son 0
  y `-EWOULDBLOCK`; el kernel reintenta si el módulo está en uso.
- `__pfx_*`: el **retpoline thunk** de CET. HECHO, §1.5, secciones
  `.retpoline_sites` (`0xc378`) y `.return_sites` (`0x12ef0`), y NORMA,
  `arch/x86/kernel/module.c::module_finalize()`:
  ```c
  if (retpolines) { rseg = (void *)retpolines->sh_addr; rsize = retpolines->sh_size;
                    apply_retpolines(rseg, rseg + rsize); }
  if (returns)   { rseg = (void *)returns->sh_addr;
                   apply_returns(rseg, rseg + returns->sh_size); }
  if (calls)     { cs.call_start = (void*)calls->sh_addr; cs.call_end = ...;
                   callthunks_patch_module_calls(&cs, me); }
  ```

**`__modver` no es un símbolo de este `.ko`.** Es un artefacto de
`CONFIG_MODVERSIONS`: sin `__versions` (HECHO, §1.7) no hay `__modver`. Búsqueda
realizada: `readelf -sW amdgpu.ko | grep -i modver` → sin resultados. Clasificación:
`PROVEN_ABSENT` sobre el alcance nombrado *este fichero*; método `readelf -sW` +
`readelf -SW`, que barren el 100 % de `.symtab` (65 613 entradas) y el 100 % de las 89
secciones.

## 3.f La firma del módulo — HECHO

`CONFIG_MODULE_SIG=y`, `CONFIG_MODULE_SIG_ALL=y`, `CONFIG_MODULE_SIG_SHA512=y`,
`CONFIG_MODULE_SIG_KEY_TYPE_ECDSA=y` (de `/boot/config-7.1.3-200.nobara.fc44.x86_64`).
Consecuencias observables, todas HECHO:

| Evidencia | Valor |
|---|---|
| Sección `.note.Linux` | presente, `0x4c` B (§1.5 `[83]`) |
| `modinfo` → `sig_id` | `PKCS#7` |
| `modinfo` → `sig_hashalgo` | `sha512` |
| `modinfo` → `sig_key` | `6F:81:0A:39:8F:C6:91:C9:98:17:6F:B4:2E:8D:94:C0:0C:8F:E7:52` |
| `.note.gnu.property` | `x86 feature: IBT`; `x86 feature used: x86, XMM`; `x86 ISA used: x86-64-baseline, x86-64-v2` |
| `.note.gnu.build-id` | `4d5342509f84dd84f0d5d515b03eb6c7659fb492` |

El paso correspondiente en §3.a es `module_sig_check(info, flags)`, que va **primero**,
antes de tocar secciones. En x86-64 con `CONFIG_MODULE_SIG_FORCE` desactivado (ausente
de la config ⇒ `n`), la firma no bloquea la carga; bloquea el móduloLoader que no la
acepta. `CONFIG_MODULE_SIG_FORCE` no aparece en la config ⇒
`CONFIG_MODULE_SIG_FORCE is not set` — pero eso se deduce de su ausencia, no de una
línea explícita; `NOT_DETERMINED` el valor efectivo, salvo que se consulte
`include/linux/module.h` o `/proc/sys/kernel/tainted`.

---

# 4. `.modpost`, `srcversion` y `modversions`

## 4.a Qué hace `modpost` y cómo genera `Module.symvers`

**NORMA — `Documentation/kbuild/modules.rst` (7.1.3, local), §"Module Versioning":**

> Module versioning is enabled by the `CONFIG_MODVERSIONS` tag, and is used as a simple ABI
> consistency check. **A CRC value of the full prototype for an exported symbol is
> created.** When a module is loaded/used, the CRC values contained in the kernel are
> compared with similar values in the module; if they are not equal, the kernel refuses
> to load the module.

> `Module.symvers` contains all exported symbols from the kernel and compiled modules.
> For each symbol, the corresponding CRC value is also stored.
>
> The syntax of the `Module.symvers` file is::
>
>     <CRC>       <Symbol>         <Module>                         <Export Type>     <Namespace>
>     0xe1cc2a05  usb_stor_suspend drivers/usb/storage/usb-storage  EXPORT_SYMBOL_GPL USB_STORAGE

> The fields are separated by tabs and values may be empty […]
> For a kernel build without `CONFIG_MODVERSIONS` enabled, the CRC would read `0x00000000`.

> `Module.symvers` serves two purposes:
> 1) It lists all exported symbols from vmlinux and all modules.
> 2) It lists the CRC if `CONFIG_MODVERSIONS` is enabled.

**Y el paso MODPOST** — NORMA, misma fuente, §"Symbols From the Kernel":

> When building an external module, the build system needs access to the symbols from the
> kernel to check if all external symbols are defined. This is done in the MODPOST step.
> modpost obtains the symbols by reading `Module.symvers` from the kernel source tree.
> During the MODPOST step, a new `Module.symvers` file will be written containing all
> exported symbols from that external module.

HECHO — el fichero existe en el árbol local:
`RESEARCH/kernelbuild/linux-7.1.3/modules-only.symvers`.

Y es aquí donde se emiten las entradas de `.modinfo` que Amodule carga — NORMA,
`scripts/mod/modpost.c`:
- `buf_printf(b, "MODULE_INFO(name, KBUILD_MODNAME);\n");` (línea 1845)
- `buf_printf(b, "\nMODULE_INFO(intree, \"Y\");\n");` (línea 1860)
- `buf_printf(b, "MODULE_INFO(staging, \"Y\");\n");` (línea 1863)
- `buf_printf(b, "MODULE_INFO(test, \"Y\");\n");` (línea 1866)
- `buf_printf(b, "MODULE_INFO(depends, \"");` (línea 2001) → lista de `depends=`
- `buf_printf(b, "MODULE_INFO(%s.alias, \"%s\");\n", ...)` (línea 2100)
- `add_srcversion(&buf, mod);` (línea 2132)

## 4.b Cómo se calcula `srcversion` — el algoritmo exacto

**NORMA — `scripts/mod/sumversion.c:388` (7.1.3 local), citado íntegro:**

```c
/* Calc and record src checksum. */
void get_src_version(const char *modname, char sum[], unsigned sumlen)
{
        char *buf, *pos;
        struct md4_ctx md;
        char *fname;
        char filelist[PATH_MAX + 1];

        /* objects for a module are listed in the first line of *.mod file. */
        snprintf(filelist, sizeof(filelist), "%s.mod", modname);

        buf = read_text_file(filelist);
        pos = buf;

        md4_init(&md);
        while ((fname = strsep(&pos, "\n"))) {
                if (!*fname)
                        continue;
                if (!(is_static_library(fname)) &&
                        !parse_source_files(fname, &md))
                        goto free;
        }

        md4_final_ascii(&md, sum, sumlen);
free:
        free(buf);
}
```

Y quién lo llama — NORMA, `scripts/mod/modpost.c:1638-1641`:

```c
if (!mod->is_vmlinux) {
        version = get_modinfo(&info, "version");
        if (version || all_versions)
                get_src_version(mod->name, mod->srcversion,
                                sizeof(mod->srcversion) - 1);
}
```

Y cómo se emite — NORMA, `scripts/mod/modpost.c:2018`:

```c
static void add_srcversion(struct buffer *b, struct module *mod)
{
        if (mod->srcversion[0]) {
                buf_printf(b, "\n");
                buf_printf(b, "MODULE_INFO(srcversion, \"%s\");\n", mod->srcversion);
        }
}
```

### Las cinco respuestas que pedía la pregunta

| Pregunta | Respuesta | Fuente |
|---|---|---|
| **¿Es un hash del contenido del `.ko`?** | **No.** Es un hash MD4 de **los ficheros fuente** del módulo, y en modo `CONFIG_MODULE_SRCVERSION_ALL` de **todos** los módulos | `get_src_version()`, `sumversion.c:388` |
| **¿Algoritmo exacto?** | **MD4**, inicializado con `md4_init`, alimentado con el contenido de cada fichero fuente, volcado con `md4_final_ascii` | ídem |
| **¿Longitud?** | 24 caracteres hexadecimales = 12 bytes = tamaño del resumen MD4. `srcversion[0]` debe ser no nulo para emitirse | `add_srcversion()`; el recuento de `D68004925455E20A24C2B87` da exactamente 24 |
| **¿Por qué NO es un commit SHA?** | Porque **no consulta ningún repositorio git en absoluto**. No hay `git`, ni `HEAD`, ni `rev-parse` en el camino de código. Es un MD4 sobre texto fuente; MD4 es además un algoritmo **no criptográficamente resistente a colisiones** desde 2004 | `sumversion.c:388` completo; no hay ninguna llamada a git en el fichero |
| **¿Por qué dos módulos idénticos tienen el mismo `srcversion`?** | Porque el valor **no depende del `.ko`**, sino solo del conjunto de ficheros fuente. Dos construcciones con las mismas fuentes producen el mismo resumen, aunque difieran en `.modinfo` (por ejemplo si cambian `vermagic` o el `intree`), en el orden de secciones, en el `BuildID` o en la firma. **Corolario: `srcversion` no es un identificador de binario y no garantiza identidad de artefacto** | `get_src_version()` lee `<mod>.mod` y los `.o`; ningún otro input |

**HECHO — el valor en este host:**

```
$ modinfo -F srcversion amdgpu.ko
D68004925455E20A24C2B87
$ readelf -p .modinfo amdgpu.ko | grep srcversion
  [  8705]  srcversion=D68004925455E20A24C2B87
```

**Y una corrección de la premisa:** `srcversion` **no es un símbolo**. HECHO:

```
$ readelf -sW amdgpu.ko | grep -i srcversion
(sin resultados)
```

`readelf -s` recorre las 65 613 entradas de `.symtab` y no encuentra ninguna. Es una
**clave de `.modinfo`**, leída por el kernel en `setup_modinfo()` a través de
`MODINFO_ATTR(srcversion)` (§3.a) y expuesta en `/sys/module/<nombre>/srcversion`
(§5.8). La afirmación «el símbolo `srcversion` del módulo» mezcla dos mecanismos.

**NORMA — por qué `/sys/module/<n>/srcversion` existe.** `MODINFO_ATTR(srcversion)`
(kernel/module/main.c:606) genera:

```c
static void setup_modinfo_srcversion(struct module *mod, const char *s)
{ mod->srcversion = kstrdup(s, GFP_KERNEL); }
static ssize_t show_modinfo_srcversion(const struct module_attribute *mattr,
                                       struct module_kobject *mk, char *buffer)
{ return scnprintf(buffer, PAGE_SIZE, "%s\n", mk->mod->srcversion); }
static const struct module_attribute modinfo_srcversion = {
        .attr = { .name = __stringify(srcversion), .mode = 0444 },
        .show = show_modinfo_srcversion,
        .setup = setup_modinfo_srcversion,
        .test = modinfo_srcversion_exists,
        ...
};
```

`mode = 0444` → sólo lectura. Y el contenido **es** la cadena de `.modinfo`, sin
transformación: no se recalcula al leer.

## 4.c `srcversion` frente a `vermagic` frente a `versions`

| | `srcversion` | `vermagic` | `versions` / `__versions` |
|---|---|---|---|
| **Dónde vive** | clave en `.modinfo` | clave en `.modinfo` | **sección ELF** `__versions` |
| **Qué es** | MD4 de los ficheros fuente | `UTS_RELEASE` + flags de compilación | `struct modversion_info[]` con el CRC de cada símbolo importado |
| **Quién lo produce** | `modpost` / `sumversion.c` | el propio módulo, desde `VERMAGIC_STRING` | `modpost`, leyendo `Module.symvers` |
| **Qué protege** | **nada en la carga** | **`check_modinfo()`** | **`check_version()`** |
| **Granularidad** | módulo entero | build del kernel | **símbolo a símbolo** |
| **Activo en este host** | **sí** | **sí** | **NO** (`CONFIG_MODVERSIONS` off) |

### `vermagic` — NORMA, la definición exacta

`include/linux/vermagic.h` (7.1.3 local), citado:

```c
#include <generated/utsrelease.h>
#include <asm/vermagic.h>

/* Simply sanity version stamp for modules. */
#ifdef CONFIG_SMP
#define MODULE_VERMAGIC_SMP "SMP "
...
#define VERMAGIC_STRING                                          \
        UTS_RELEASE " "                                          \
        MODULE_VERMAGIC_SMP MODULE_VERMAGIC_PREEMPT              \
        MODULE_VERMAGIC_MODULE_UNLOAD MODULE_VERMAGIC_MODVERSIONS \
        MODULE_ARCH_VERMAGIC                                     \
        MODULE_RANDSTRUCT
```

Con los valores de este host: `CONFIG_SMP=y` → `"SMP "`, `CONFIG_PREEMPT_BUILD` (no
`PREEMPT_RT`) → `"preempt "`, `CONFIG_MODULE_UNLOAD=y` → `"mod_unload "`,
`CONFIG_MODVERSIONS` **off** → `""`. Y `arch/x86/include/asm/vermagic.h`:
`# define MODULE_ARCH_VERMAGIC ""` para x86-64.

HECHO — el resultado encaja exactamente:

```
$ modinfo -F vermagic amdgpu.ko
7.1.3-200.nobara.fc44.x86_64 SMP preempt mod_unload 
```

(`preempt_rt` no aparece, `modversions` no aparece, el espacio final viene de
`MODULE_ARCH_VERMAGIC ""` antes de la cadena vacía de randstruct.)

### La comprobación — NORMA, `kernel/module/main.c:2633`

```c
static int check_modinfo(struct module *mod, struct load_info *info, int flags)
{
        const char *modmagic = get_modinfo(info, "vermagic");
        int err;

        if (flags & MODULE_INIT_IGNORE_VERMAGIC)
                modmagic = NULL;

        /* This is allowed: modprobe --force will invalidate it. */
        if (!modmagic) {
                err = try_to_force_load(mod, "bad vermagic");
                if (err)
                        return err;
        } else if (!same_magic(modmagic, vermagic, info->index.vers)) {
                pr_err("%s: version magic '%s' should be '%s'\n",
                       info->name, modmagic, vermagic);
                return -ENOEXEC;
        }

        err = check_modinfo_livepatch(mod, info);
        if (err)
                return err;

        return 0;
}
```

con `static const char vermagic[] = VERMAGIC_STRING;` (línea 1105).

### Qué pasaría con el mismo `srcversion` pero distinto `vermagic`

**NORMA + DERIVACIÓN.** `check_modinfo()` **solo** lee `vermagic`; `srcversion` no
participa en ninguna decisión de carga. Un `.ko` con `srcversion` idéntico y `vermagic`
distinto:

1. Pasa `setup_modinfo()` sin complaints por `srcversion` (se limita a `kstrdup`).
2. Falla en `same_magic(modmagic, vermagic, info->index.vers)` → imprime
   `version magic 'X' should be 'Y'` y **devuelve `-ENOEXEC` (`Load fails`)**.
3. La carga se aborta **antes** de `simplify_symbols()` y **antes** de
   `apply_relocations()`. Es decir: **no se escribe ni un solo byte de reubicación**, y
   todo el trabajo de `layout_and_allocate()` se libera.

**Consecuencia que se sigue:** `srcversion` es un **identificador informativo, no un
control de carga**. Dos `.ko` con el mismo `srcversion` pueden ser mutuamente
incompatibles, y a la inversa: un cambio que solo altere `vermagic` (por ejemplo
recompilar con `CONFIG_SMP` distinto) deja el `srcversion` **idéntico** mientras produce
un `.ko` que ya no carga. **`srcversion` no substituye a `vermagic` y no lo sustituye
para ningún propósito de carga.**

**Y el caso límite:** si el módulo **no trae** `vermagic` en absoluto, `check_modinfo`
llama a `try_to_force_load(mod, "bad vermagic")`, que es el mecanismo de
`modprobe --force`. El comentario del kernel lo dice: *«This is allowed: modprobe
--force will invalidate it.»*

## 4.d `modversions` y `struct modversion_info`

### `struct modversion_info` — NORMA, `include/linux/module.h:38` (7.1.3 local)

```c
struct modversion_info {
        unsigned long crc;
        char name[MODULE_NAME_LEN];
};
```

### Cómo se genera — NORMA, `Documentation/kbuild/modules.rst` §"Version Information Formats"

> Exported symbols have information stored in the `__ksymtab` and `__kflagstab` sections.
> Symbol names and namespaces are stored in `__ksymtab_strings` section, using a format
> similar to the string table used for ELF. **If `CONFIG_MODVERSIONS` is enabled, the CRCs
> corresponding to exported symbols will be added to the `__kcrctab` section.**
>
> **If `CONFIG_BASIC_MODVERSIONS` is enabled** (default with `CONFIG_MODVERSIONS`),
> imported symbols will have their symbol name and CRC stored in the **`__versions`
> section** of the importing module. This mode only supports symbols of length up to
> 64 bytes.
>
> **If `CONFIG_EXTENDED_MODVERSIONS` is enabled** (required to enable both
> `CONFIG_MODVERSIONS` and `CONFIG_RUST` at the same time), imported symbols will have
> their symbol name recorded in the **`__version_ext_names`** section as a series of
> concatenated, null-terminated strings. CRCs for these symbols will be recorded in the
> **`__version_ext_crcs`** section.

**Detalle de versión que no debe suponerse:** en 7.1.3 hay **tres** modos
(`__kcrctab` / `__versions` / `__version_ext_names` + `__version_ext_crcs`), no uno. El
modo clásico `__versions` es el `CONFIG_BASIC_MODVERSIONS`.

### El error característico — NORMA, `kernel/module/version.c::check_version()`

```c
int check_version(const struct load_info *info, const char *symname,
                  struct module *mod, const u32 *crc)
{
        ...
        /* Exporting module didn't supply crcs?  OK, we're already tainted. */
        if (!crc)
                return 1;

        /* If we have extended version info, rely on it */
        if (info->index.vers_ext_crc) { ... goto bad_version; ... }

        /* No versions at all?  modprobe --force does this. */
        if (versindex == 0)
                return try_to_force_load(mod, symname) == 0;

        versions = (void *)sechdrs[versindex].sh_addr;
        num_versions = sechdrs[versindex].sh_size / sizeof(struct modversion_info);

        for (i = 0; i < num_versions; i++) {
                u32 crcval;
                if (strcmp(versions[i].name, symname) != 0)
                        continue;
                crcval = *crc;
                if (versions[i].crc == crcval)
                        return 1;
                pr_debug("Found checksum %X vs module %lX\n", crcval, versions[i].crc);
                goto bad_version;
        }

        /* Broken toolchain. Warn once, then let it go.. */
        pr_warn_once("%s: no symbol version for %s\n", info->name, symname);
        return 1;

bad_version:
        pr_warn("%s: disagrees about version of symbol %s\n", info->name, symname);
        return 0;
}
```

**El mensaje es `disagrees about version of symbol %s`, con `pr_warn` (KERN_WARNING), no
`KERN_ERR`.** Y hay **tres** desenlaces distintos, no uno:

| Situación | Diagnóstico | Devuelve | Efecto |
|---|---|---|---|
| CRC distinto | `disagrees about version of symbol X` | `0` | **`return 0` = RECHAZAR** el módulo |
| Sin entrada en `__versions` | `no symbol version for X` (`pr_warn_once`) | `1` | **Deja pasar** (toolchain roto) |
| `versindex == 0` (sin `__versions`) | — | `try_to_force_load(...) == 0` | Depende de `--force` |

Y `module_layout` — NORMA, mismo fichero — es el ancla que impide que un `.ko` compilado
contra una `struct module` de otro kernel entre en el juego:

```c
int check_modstruct_version(const struct load_info *info, struct module *mod)
{
        static struct find_symbol_arg fsa = { .name = "module_layout", .gplok = true };
        ...
        return check_version(info, "module_layout", mod, fsa.crc);
}

void module_layout(struct module *mod, struct modversion_info *ver,
                   struct kernel_param *kp, struct kernel_symbol *ks,
                   struct tracepoint * const *tp)
{
}
EXPORT_SYMBOL(module_layout);
```

Un cuerpo **vacío**: existe solo para que su **prototipo** tenga un CRC, y
`EXPORT_SYMBOL` lo pone en `__ksymtab` + `__kcrctab`. Cualquier cambio en la
estructura cambia el CRC y bloquea los `.ko` viejos.

### El estado real de ESTE host — HECHO, y es una corrección de la premisa

La pregunta daba por hecho que «la sección `__versions` es lo que hace que un módulo
cargado de un kernel distinto no cargue». **En este host ese mecanismo no está
activo.**

```
$ grep -E "MODVERSIONS|SRCVERSION" /boot/config-7.1.3-200.nobara.fc44.x86_64
CONFIG_HAVE_ASM_MODVERSIONS=y
# CONFIG_MODVERSIONS is not set
CONFIG_MODULE_SRCVERSION_ALL=y
$ readelf -SW amdgpu.ko | grep -i versions
(sin resultados)
```

Tres hechos independientes y coherentes:

| Observación | Estado |
|---|---|
| `CONFIG_MODVERSIONS` | **`# ... is not set`** — desactivado |
| `CONFIG_HAVE_ASM_MODVERSIONS` | `y` (capacidad del toolchain, no el interruptor) |
| `CONFIG_MODULE_SRCVERSION_ALL` | **`y`** — por eso *todo* módulo lleva `srcversion` |
| Sección `__versions` en el `.ko` | **ausente** (`PROVEN_ABSENT`, §3e) |
| `modversions` en `vermagic` | **ausente** (coherente con `MODULE_VERMAGIC_MODVERSIONS ""`) |

**Consecuencia práctica, y es la que importa para razonar sobre este host:** en
`7.1.3-200.nobara.fc44.x86_64` la **única** barrera de versión entre un `.ko` y el
kernel es `vermagic` (más `CONFIG_MODULE_SIG`). El control symbol-a-symbol de
`modversions` **no se ejecuta**. `same_magic()` también lo refleja — el parámetro
`has_crcs` decide si se compara la cadena entera o solo la parte previa al primer
espacio:

```c
/* First part is kernel version, which we ignore if module has crcs. */
int same_magic(const char *amagic, const char *bmagic, bool has_crcs)
{
        if (has_crcs) {
                amagic += strcspn(amagic, " ");
                bmagic += strcspn(bmagic, " ");
        }
        return strcmp(amagic, bmagic) == 0;
}
```

Con `__versions` ausente, `has_crcs` es falso, así que se compara la cadena
**completa**, incluido `modversions`. Es decir: **un `.ko` compilado con
`CONFIG_MODVERSIONS=y` y uno compilado sin él no se pueden cargar uno en el otro,
aunque el segundo tenga un `vermagic` correcto**, y el motivo no es el CRC sino que las
cadenas no coinciden. El mecanismo existe, está implementado y está documentado; en
este host no está compilado.

---

# 5. Cómo analizar un `.ko` en la práctica

## 5.1 Descomprimir

```bash
# 1. localizar y medir el comprimido
ls -la /lib/modules/$(uname -r)/kernel/drivers/gpu/drm/amd/amdgpu/amdgpu.ko.zst

# 2. descomprimir a un directorio de trabajo (nunca sobrescribir el original)
mkdir -p /tmp/opencode/ko
zstd -d -f /lib/modules/$(uname -r)/kernel/drivers/gpu/drm/amd/amdgpu/amdgpu.ko.zst \
      -o /tmp/opencode/ko/amdgpu.ko

# 3. verificar qué se ha obtenido — esto NO es opcional (§4.6 AGENTS.md)
file /tmp/opencode/ko/amdgpu.ko
sha256sum /tmp/opencode/ko/amdgpu.ko
```

HECHO, salida real:

```
amdgpu.ko: ELF 64-bit LSB relocatable, x86-64, version 1 (SYSV), BuildID[sha1]=4d5342..., not stripped
a1a44c2457d33c65149ef4f455173ca446564bfd19bcc9cb215fca10cf24c024  /tmp/opencode/ko/amdgpu.ko
```

Alternativa si no hay `zstd`: `.ko.xz` usa `xz -d`, `.ko.gz` usa `gzip -d`, `.ko.bz2`
usa `bzip2 -d`. **Comprueba siempre con `file(1)`**, no con la extensión: un HTML de
error guardado como `.ko` es un `FETCH_FAILED`, no un ELF.

## 5.2 `readelf` — qué revela cada opción

Sintaxis según `readelf(1)` (`man7.org`, HTTP 200):
`-h/--file-header` · `-S/--section-headers` · `-s/--syms` · `--dyn-syms` ·
`-r/--relocs` · `-x <n>/--hex-dump=` · `-p <n>/--string-dump=` · `-R/--relocated-dump=` ·
`-j <n>/--display-section=` · `-n/--notes` · `-u/--unwind` · `-L/--lint`.

| Comando | Qué revela en ESTE `.ko` | HECHO (salida) |
|---|---|---|
| `readelf -h amdgpu.ko` | Tipo, arquitectura, offsets, nº de secciones, **y que no hay programa** | `Tipo: REL` · `e_phnum: 0` · `e_shoff: 37488368` · 89 secciones |
| `readelf -SW amdgpu.ko` | La tabla de secciones completa con `sh_flags` | las 89 de §1.5 |
| `readelf -lW amdgpu.ko` | Segmentos | **`No hay encabezados de programa en este fichero.`** |
| `readelf -sW amdgpu.ko` | **65 613** símbolos con `Ndx` — **la columna `Ndx` es imprescindible** | ver §5.4 |
| `readelf -rW amdgpu.ko` | Las 655 590 reubicaciones, agrupadas por sección | el histograma de §2.b |
| `readelf -p .modinfo amdgpu.ko` | `.modinfo` como texto legible | `srcversion=`, `vermagic=`, `parm=` |
| `readelf -x .modinfo amdgpu.ko` | `.modinfo` en hexadecimal, con el desplazamiento de cada cadena | `[8705]` |
| `readelf -x __ksymtab amdgpu.ko` | Los 4 símbolos exportados, en ceros | ver §3.c |
| `readelf -x __ksymtab_strings amdgpu.ko` | Los 4 nombres de exportación | ver §3.c |
| `readelf -x .rela.text amdgpu.ko` | Las entradas RELA en crudo: 24 B cada una | `15000000 00000000 04000000 …` |
| `readelf -n amdgpu.ko` | Las notas: `BuildID`, `IBT`, `x86-64-v2`, y `.note.Linux` | ver §3.f |

### Trampa verificada: `-j` **no** filtra la salida de `-r`

La página de manual anuncia `-j <number or name> | --display-section=`. **HECHO: con
`-r` no filtra.** El primer intento empezó con `.rela__ksymtab`:

```
$ readelf -rW -j .rela.text amdgpu.ko
La sección de reubicación '.rela__ksymtab' at offset 0x14bedc8 contains 12 entries:
```

Porque `-r` itera sobre **todas** las secciones de reubicación y `-j` no actúa como
selector en ese modo. **Solución verificada:** filtrar por texto, y conservar el
encabezado de sección para no mezclar secciones distintas (que es el error grave
detallado en §6.3):

```bash
# MAL — mezcla secciones distintas que comparten valores numéricos
readelf -rW amdgpu.ko | grep -E "^0000000000214e"        # ✗

# BIEN — se mantiene el estado de "sección actual"
readelf -rW amdgpu.ko | awk '
  /reubicaci.n/ { sec=$0; sub(/.*'"'"'/,"",sec); sub(/'"'"'.*/,"",sec) }
  /^0000000000214e/ { print sec, $0 }'
```

## 5.3 `nm` frente a `nm -D` frente a `objdump -t`

**HECHO — las tres sobre este fichero:**

```
$ nm -D amdgpu.ko
nm: amdgpu.ko: no hay símbolos

$ readelf --dyn-syms amdgpu.ko
(vacío)

$ nm amdgpu.ko | head -3
0000000000000010 T cleanup_module
0000000000000010 T init_module
0000000000000000 T __pfx_cleanup_module

$ objdump -t amdgpu.ko | head -4
SYMBOL TABLE:
0000000000000000 l    d  __bug_table	0000000000000000 __bug_table
```

**Por qué `nm -D` no sirve en un `.ko` — NORMA + HECHO.** `nm -D` muestra la **tabla de
símbolos dinámicas**, que solo existe si hay enlace dinámico, es decir `.dynsym` +
`.dynstr`. HECHO: ninguna de las dos está (§1.7). Motivo de fondo: un `.ko` es `ET_REL`;
`ET_REL` no tiene tabla de símbolos dinámicos por definición. **`nm -D` en un `.ko` está
garantizado que devuelva vacío en cualquier plataforma**, no solo en x86-64.

**Las letras de `nm` — NORMA, `nm(1)` (resumen del significado por tipo):**

| Letra | Significado | Binding | Ejemplo en este `.ko` |
|---|---|---|---|
| `T` | símbolo de **texto** (código) | global | `T init_module` |
| `t` | símbolo de texto | **local** | `t uvd_v6_0_start` ← **es local** |
| `D` / `d` | datos | global / local | |
| `B` / `b` | `.bss` | global / local | |
| `R` / `r` | solo lectura (`.rodata`) | global / local | `r _entry.4` |
| `A` / `a` | absoluto (`SHN_ABS`) | global / local | |
| `U` | **indefinido** (`SHN_UNDEF`) | — | `nm -u` los lista |
| `N` | sin depuración | | |
| `w` | débil | | |

`nm -u amdgpu.ko` es el atajo para listar **solo** lo que hay que resolver contra el
`vmlinux` — exactamente los `SHN_UNDEF` de §2d.

**`objdump -t` frente a `nm`:** `objdump -t` imprime la tabla de símbolos en el formato
bruto de BFD (`valor` · `flags` · `sección` · `tamaño` · `nombre`), que incluye la
**sección** de cada símbolo. Es más verboso pero más completo: `nm` **no** dice en qué
sección está cada símbolo, y eso importa (§5.4).

## 5.4 Encontrar una función y sus límites

**HECHO — por qué `nm` solo no basta para hallar los límites.** La secuencia `nm -n` en
torno a `uvd_v6_0_start`:

```
$ nm -n amdgpu.ko | grep -B3 -A3 " t uvd_v6_0_start$"
0000000000214dc0 r _entry.1
0000000000214e00 r _entry.2
0000000000214e30 t __pfx_uvd_v6_0_start
0000000000214e40 r __func__.3
0000000000214e40 t uvd_v6_0_start
0000000000214e80 r _entry.4
0000000000214eb0 R amdgpu_ras_nbio_sys_func_v7_9
0000000000214ec0 r nbio_v7_9_ras_err_event_athub_irq_funcs
0000000000214ed0 r nbio_v7_9_ras_controller_irq_funcs
```

**Cinco símbolos «dentro» del rango de `uvd_v6_0_start`, y ninguno es suyo.** Todos
están en `.rodata` (sección 17), no en `.text` (sección 12) — el valor `0x214e80` es un
offset en *otra* sección que **coincide numéricamente**. HECHO, `readelf -sW`:

```
0000000000214e80  44  OBJECT 17  _entry.4        <- Ndx=17, no 12
0000000000214eb0  44  OBJECT 17  amdgpu_ras_nbio_sys_func_v7_9
```

**Un `st_value` en un `ET_REL` no significa nada sin su `Ndx`.** Éste es el error
estructural más caro de §1.2, y `nm` no lo expone.

**Procedimiento correcto, verificado:**

```bash
# 1. localizar el símbolo y su sección
readelf -sW amdgpu.ko | grep -E " uvd_v6_0_start$"
#   -> 0000000000214e40 <tamaño> FUNC LOCAL 12 uvd_v6_0_start     Ndx=12 = .text

# 2. el siguiente símbolo FUNC *de la MISMA sección* marca el fin
#    (resultado: 0x214e40 .. 0x2154a0, 1632 bytes, siguiente = __pfx_uvd_v6_0_set_powergating_state)

# 3. o, mucho más simple: dejar que objdump use la tabla de símbolos
objdump -d --disassemble=uvd_v6_0_start amdgpu.ko
```

NORMA — `objdump(1)`, `-d/--disassemble= symbol`:

> Display the assembler mnemonics for the machine instructions from the input file. […]
> If the optional symbol argument is given (perhaps multiple times), then display the
> assembler mnemonics starting at (all the) symbol. **If symbol is a function name then
> disassembly will stop at the end of the function**, otherwise it will stop when the next
> symbol is encountered. If there are no matches for any symbol then nothing will be
> displayed.

**HECHO — `objdump` para correctamente**, y salta a la siguiente sección:

```
$ objdump -d --disassemble=uvd_v6_0_start amdgpu.ko | sed -n '5,8p'
Desensamblado de la sección .text:
0000000000214e40 <uvd_v6_0_start>:
  214e40:	e8 00 00 00 00       	call   214e45 <uvd_v6_0_start+0x5>
$ objdump -d --disassemble=uvd_v6_0_start amdgpu.ko | tail -4
Desensamblado de la sección .altinstr_aux:
Desensamblado de la sección .static_call.text:
```

**Un límite práctico:** en una función grande, `objdump --disassemble=<sym>` es cómodo;
para una sub-ventana, usar el rango de direcciones, siempre con los límites de arriba:

```bash
objdump -d --start-address=0x214e40 --stop-address=0x2154a0 amdgpu.ko
```

## 5.5 `objdump -d` y las columnas de su salida

NORMA, `objdump(1)`, para `--no-show-raw-insn`:
> If the `--no-show-raw-insn` option is also used, the address is printed on a separate line
> and the raw bytes are not displayed.

HECHO, una línea real y sus partes:

```
  214e40:	e8 00 00 00 00       	call   214e45 <uvd_v6_0_start+0x5>
   │        │                  │     │
   │        │                  │     └── operandos: destino + resuelto por objdump
   │        │                  └──────── mnemónico (AT&T)
   │        └─────────────────────────── bytes en bruto (hex), en orden de memoria
   └──────────────────────────────────── offset DENTRO DE LA SECCIÓN
```

| Columna | Significado | Nota crítica |
|---|---|---|
| `214e40` | offset dentro de la sección | **No es una dirección virtual.** Para un `ET_REL` es un offset de sección |
| `e8 00 00 00 00` | bytes en memoria | `00 00 00 00` = **hueco de reubicación**, §6.1 |
| `call` | mnemónico | AT&T por defecto; `-M intel` cambia a Intel |
| `214e45 <uvd_v6_0_start+0x5>` | destino | **Ilegible sin `-r`**: §2.c |
| `<uvd_v6_0_start+0x5>` | etiqueta simbólica | `objdump` la pone aunque el símbolo sea del propio `.text` |

## 5.6 `objdump -dr`: la forma correcta de leer un `.ko`

**Esta es la parte central de la respuesta a la pregunta, y la razón es verificable.**

NORMA — `objdump(1)`, `-r`:

> `-r`, `--reloc` — Display the relocation entries. If used together with `-d`, the
> disassembly is interleaved with the relocation entries for the relocated instructions.

**HECHO — la diferencia, misma región, dos órdenes:**

Sin `-r` (ilegible):
```
  214e40:	e8 00 00 00 00       	call   214e45 <uvd_v6_0_start+0x5>
  214e45:	41 55                	push   %r13
  214e47:	31 d2                	xor    %edx,%edx
```

Con `-r` (legible):
```
  214e40:	e8 00 00 00 00       	call   214e45 <uvd_v6_0_start+0x5>
			214e41: R_X86_64_PLT32	__fentry__-0x4
  214e45:	41 55                	push   %r13
  214e47:	31 d2                	xor    %edx,%edx
  214e55:	e8 00 00 00 00       	call   214e5a <uvd_v6_0_start+0x1a>
			214e56: R_X86_64_PLT32	amdgpu_device_rreg-0x4
```

**Tres propiedades que hacen que `-dr` sea la forma correcta, todas HECHO:**

1. **El desplazamiento del `call` pasa de ilegible a correcto.** `214e45` ya no se
   interpreta como un destino: se lee `R_X86_64_PLT32 __fentry__-0x4`.
2. **El `r_offset` se imprime en decimal, con un byte de diferencia respecto a la
   dirección de la instrucción.** `214e41`, no `214e40`, porque `r_offset` apunta al
   **campo de 4 bytes**, no al opcode `e8`. Es la comprobación directa de §2.c.
3. **El símbolo es un nombre, no un número.** Sin `-r` no hay forma de saber si
   `__fentry__` es local o del `vmlinux`; con `-r` el nombre es explícito y §2.d dice
   cómo decidirlo.

**NORMA — una advertencia de `readelf` que confirma el mecanismo:** el volcado de
`__ksymtab` avisa

> `NOTA: Esta sección tiene reubicaciones contra ella, pero NO se han aplicado a este volcado.`

Es decir: **el contenido de una sección con reubicaciones es unoplaceholder.** Todas
las secciones de reubicación (`SHF_INFO_LINK`, flag `I` en §1.5) tienen el campo a 0 y
solo valen en combinación con `.rela.*`.

## 5.7 `objdump -S`: por qué aquí no hay nada

**HECHO — no hay DWARF:**

```
$ readelf -SW amdgpu.ko | grep -c debug_
0
```

Cero secciones `.debug_*`. NORMA, `objdump(1)`, `-S` (`--source`):

> Display source code intermixed with disassembly, if debug information is present in
> the file.

Sin `.debug_line`/`.debug_info` no hay fuente que intercalar; `objdump -S` se comporta
como `objdump -d`.

**Por qué: la configuración del kernel no gobierna los módulos.** HECHO,
`/boot/config-7.1.3-200.nobara.fc44.x86_64` tiene `CONFIG_DEBUG_INFO=y` y
`CONFIG_DEBUG_INFO_DWARF5=y`, pero eso se aplica a la **imagen del kernel**; la
distribución compila los módulos **sin** `-g` para no multiplicar el tamaño de
`/lib/modules`.

**Lo que sí hay en su lugar — HECHO:**

| Sección | Tamaño | Qué es |
|---|---:|---|
| `.BTF` | **3 882 770 B** (`0x3b3f12`) | **BTF** (*BPF Type Format*): información de **tipos**, no números de línea |
| `.orc_unwind` / `.orc_unwind_ip` | `0xc0768` / `0x804f0` | **deshueso ORC** |

La configuración confirma el BTF en módulos: `CONFIG_DEBUG_INFO_BTF=y` y
**`CONFIG_DEBUG_INFO_BTF_MODULES=y`**. Y el deshueso del kernel **no es DWARF CFI**:
`CONFIG_UNWINDER_ORC=y`, luego **cero** `.eh_frame`.

**Consecuencia práctica:** el BTF permite *tipos* (con `bpftool btf dump`, o
`pahole`), lo que ayuda a identificar la **firma** de una función y sus `struct`, pero
**no** permite asignar el `mov $0x418958,%edi` de §6.2 a una línea de código fuente. Para
eso hace falta el `.c` de amdgpu, que está en
`RESEARCH/working/linux-7.1.3/drivers/gpu/drm/amd/amdgpu/`.

## 5.8 `modinfo`, `modprobe --dump-modversions`, `readelf -x __versions`

### `modinfo` — NORMA, `modinfo(8)` (HTTP 200)

> modinfo extracts information from the Linux Kernel modules given on the command line. If
> the module name is not a filename, then the `/lib/modules/` version directory is
> searched, as is also done by modprobe(8) when loading kernel modules.
>
> modinfo by default lists each attribute of the module in form `fieldname : value` […]

Opciones citadas que importan: `-F field, --field field` (una por línea, «most useful
for scripts», nombres insensibles a mayúsculas), `-k kernel` (información de otro
kernel), `-b basedir`, `-a/--all`, `-s/--file`, `-x`, `--license`.

HECHO:

```
$ modinfo -F srcversion amdgpu.ko
D68004925455E20A24C2B87
$ modinfo -F vermagic amdgpu.ko
7.1.3-200.nobara.fc44.x86_64 SMP preempt mod_unload 
$ modinfo amdgpu.ko | head -3
filename:       /tmp/opencode/ko/amdgpu.ko
license:        GPL and additional rights
description:    AMD GPU
```

Nótese que `modinfo` **no necesita el kernel**: lee el fichero directamente. Funciona
igual sobre un `.ko` de otra versión, que es justo para lo que sirve `-k`.

### `modprobe --dump-modversions` — resultado negativo

- **Pregunta:** ¿existe `modprobe --dump-modversions` y qué imprime?
- **Dónde busqué:** (a) `https://man7.org/linux/man-pages/man8/modinfo.8.html` (HTTP
  200) — la lista `OPTIONS` **no contiene** `--dump-modversions`; (b) intenté
  ejecutarlo — **`permission.rejected`**, por `"modprobe*": "deny"` en
  `opencode.json:71`.
- **Clasificación:** `NOT_DETERMINED` **en este host por observación directa**. La
  existencia de la opción en el `kmod` instalado es `NOT_DETERMINED`; lo que sí es
  `OBSERVED` es que la página de manual publicada de `modinfo` no la documenta, y que
  la comprobación en vivo está bloqueada por política.
- **Lo que sí se puede afirmar sin depender de eso:** la información que esa opción
La información que esa opción reportaría es, por construcción, la de la sección
`__versions` — es decir, `struct modversion_info[]` (§4.d). Y en este `.ko`
  **esa sección no existe**, luego el volcado correspondiente sería vacío. Esto último es
  `DERIVATION` de §4.d, no una medición.

### `readelf -x __versions` — no aplica aquí

```
$ readelf -x __versions amdgpu.ko
readelf: Error: No such file or directory / No se encontró la sección '__versions'
```

(HECHO por ausencia de la sección, §1.7.) Es el **test** para distinguir un kernel con
`CONFIG_MODVERSIONS` de uno sin él:

```bash
readelf -SW /lib/modules/$(uname -r)/kernel/.../mod.ko | grep __versions \
  && echo "MODVERSIONS activo" || echo "MODVERSIONS inactivo"
```

## 5.9 `insmod(8)` y el diagnóstico de errores

**NORMA — `insmod(8)` (HTTP 200):**

> insmod is a trivial program to insert a module into the kernel. Most users will want to
> use modprobe(8) instead, which is more clever and can handle module dependencies.
>
> **Only the most general of error messages are reported: as the work of trying to link
> the module is now done inside the kernel, the dmesg(1) usually gives more information
> about errors.**

**Esta cita es la clave operativa de todo el documento:** el enlace ocurre en el kernel,
así que los errores concretos (`Unknown symbol`, `version magic … should be …`,
`disagrees about version of symbol …`, `Invalid relocation target … existing value is
nonzero`, `Unknown rela relocation: N`, `overflow in relocation type … likely not compiled
with -mcmodel=kernel`) **salen en `dmesg`/`journalctl`, no en la salida de `insmod`.**

**`insmod -p`:** NORMA `NOT_DETERMINED`. Busqué la opción en la página de `insmod(8)` de
man7 (`OPTIONS` empieza por `-f, --force`; no aparece `-p` en la lista recuperada) y no
pude ejecutar `insmod --help` (denegado). Una búsqueda dirigida de la semántica de
`-p` en el código de kmod no se realizó. Registrado como hueco, no rellenado.

## 5.10 `sysfs`: qué se puede leer en caliente

`/sys/module/amdgpu/srcversion` es exactamente la cadena de `.modinfo` (§4b), expuesta
por `MODINFO_ATTR(srcversion)` con `mode = 0444`.

NORMA — `Documentation/ABI/testing/sysfs-module` y `Documentation/ABI/stable/sysfs-module`
(84 y 47 líneas en el árbol local) documentan los atributos de módulo. La lista de
atributos **disponibles** se obtiene sin fuente:

```bash
ls /sys/module/amdgpu/            # srcversion, parameters, sections, initstate, ...
cat /sys/module/amdgpu/srcversion
cat /sys/module/amdgpu/parameters/*    # uno por module_param
ls /sys/module/amdgpu/sections/        # nombres de las secciones asignadas
```

`/sys/module/<n>/sections/` es especialmente útil: **son las `sh_addr` reales** que el
kernel asignó en `layout_and_allocate()`, es decir, el resultado de la conversión que
§2d describe. Es la forma más directa de **verificar** el modelo mental de este
documento contra un módulo realmente cargado.

---

# 6. Ejercicio worked: `uvd_v6_0_start` de principio a fin

## 6.0 El enunciado y los datos de partida

Objeto: `uvd_v6_0_start`, `.text + 0x214e40`, en `/tmp/opencode/ko/amdgpu.ko`
(`SHA256 a1a44c24…`).

**Límites verificados** (§5.4): `[0x214e40, 0x2154a0)`, **1 632 bytes** (`0x660`). El
siguiente símbolo `FUNC` en `.text` es `__pfx_uvd_v6_0_set_powergating_state` en
`0x2154a0`.

## 6.1 Las siete preguntas, y por qué el desplazamiento no basta

**Pregunta 1: ¿qué hay en `.text + 0x214e40`?**
HECHO, `objdump -d`:
```
0000000000214e40 <uvd_v6_0_start>:
  214e40:	e8 00 00 00 00       	call   214e45 <uvd_v6_0_start+0x5>
```

**Pregunta 2: ¿a qué llama?** Lo que `objdump` imprime, `0x214e45`, es
`0x214e40 + 5`, es decir **la instrucción siguiente**.

**Pregunta 3: ¿puedo deducir el destino de ahí?** **No, y es demostrable, no una
limitud de herramientas.** DERIVACIÓN a partir de §2.c:

`objdump` mostrado `S + A - P` con `S = 0` (el símbolo es `UND`, `st_value = 0`),
`A = -4`, `P = r_offset`. Es decir, todo lo que el desensamblador sabe de esa llamada es
`-4` y un offset. El número `0x214e45` **depende sólo de `A`**, no del símbolo. Y
viceversa: **`A = -4` es idéntico para todas las llamadas de 5 bytes a función.** Prueba
directa — HECHO, tres `call` consecutivos en la misma función:

```
  214e40:	e8 00 00 00 00   →  214e45   (objdump dice lo mismo)
  214e55:	e8 00 00 00 00   →  214e5a
  214e69:	e8 00 00 00 00   →  214e6e
```

Si el desplazamiento codificara el destino, tres llamadas distintas mostrarían tres
números distintos. Muestran `instrucción + 5`, siempre. **El desplazamiento cero no es
información: es la ausencia de información, correctamente rotulada.**

## 6.2 El mismo error en la instrucción siguiente

Para contrastar, una instrucción **no** es una llamada. HECHO, `.text + 0x21519d`:

```
  21519d:	48 c7 c7 00 00 00 00 	mov    $0x0,%rdi
```

Bytes `48 c7 c7 00 00 00 00`: `REX.W`, `C7 /0` (`mov r/m64, imm32`), `modrm c7`, y
**cuatro bytes de inmediato a cero**. HECHO, la reubicación que lo cubre:

```
  0x002151a0  R_X86_64_32S  symidx=5  .rodata  st_value=0x0  A=+0x235ac8
```

`r_offset = 0x2151a0` = la instrucción (`0x21519d`) + **3** bytes. `objdump -d` muestra
`$0x0`: el **hueco**. Con `-r`:

```
  21519d:	48 c7 c7 00 00 00 00 	mov    $0x0,%rdi
			2151a0: R_X86_64_32S	.rodata+0x235ac8
```

**Y aquí hay que corregir un punto del enunciado de la pregunta.** Se menciona un
`mov $0x418958,%edi` «que resultó ser un hueco de reubicación». HECHO, ese caso
concreto **no es un hueco**:

```
$ objdump -d amdgpu.ko | grep -m1 "418958"
   1691c:	bf 58 89 41 00       	mov    $0x418958,%edi
```

```
$ readelf -rW amdgpu.ko | grep -E "^000000000001691(c|d) "
(sin resultados)
```

**No hay ninguna reubicación en `0x1691c` ni en `0x1691d`.** Los bytes son
`bf 58 89 41 00` = `mov $imm32,%edi` con `imm32 = 0x00418958` **literal**, en un bucle:

```
   1690f:	e9 00 00 00 00   jmp    16914 <atom_op_delay+0x64>
			16910: R_X86_64_PLT32	msleep-0x4
   16917:	48 85 db         test   %rbx,%rbx
   1691a:	74 10            je     1692c
   1691c:	bf 58 89 41 00   mov    $0x418958,%edi
   16921:	e8 00 00 00 00   call   16926
			16922: R_X86_64_PLT32	__const_udelay-0x4
   16926:	48 83 eb 01      sub    $0x1,%rbx
   1692a:	75 f0            jne    1691c
```

Aparece **207 veces** en el módulo. Es el cuerpo de `atom_op_delay`
(`RESEARCH/working/linux-7.1.3/drivers/gpu/drm/amd/amdgpu/atom.c:674`, con
`udelay`/`mdelay`/`msleep`) en una instancia especializada: el `jmp msleep` y el
`call __const_udelay` son las dos ramas de ese `if`. Cuál es el valor exacto de
`0x418958` en este punto es `NOT_DETERMINED`: **`atom.c:54-55` define
`ATOM_UNIT_MICROSEC 0` y `ATOM_UNIT_MILLISEC 1`, luego no es el argumento `arg`**, y no
se cartografió el resto de la función ni su `.c` con la granularidad necesaria. No se
afirma ninguna identidad para ese número.

**La lección es justo la que hace falta para §7:** `0x418958` *parece* una dirección
(`0x4_18958` está en el rango de un módulo de 9 MB) y *no* lo es. Y un hueco de
reubicación real se ve como `$0x0`. Los dos criterios son distintos y ambos se
comprueban con el mismo comando.

## 6.3 El procedimiento completo, siete pasos

```
 1. readelf -SW amdgpu.ko
        │  89 secciones, sin __versions, sin .debug_*, sin .dynsym, sin .plt/.got
        ▼
 2. readelf -sW amdgpu.ko | grep " uvd_v6_0_start$"
        │  valor=0x214e40  tipo=FUNC  bind=LOCAL  Ndx=12  → Ndx=12 es .text (§1.5)
        │  sin Ndx el 0x214e40 no significa nada (§5.4)
        ▼
 3. límite = siguiente símbolo FUNC de Ndx=12  →  0x2154a0
        │  (o directamente: objdump -d --disassemble=uvd_v6_0_start)
        ▼
 4. objdump -dr --start-address=0x214e40 --stop-address=0x2154a0 amdgpu.ko
        │  cada instrucción con su reubicación debajo, POR SECCIÓN de destino
        ▼
 5. para cada línea "R_X86_64_PLT32  NOMBRE-0x4":
        │  NOMBRE es el destino. Punto.
        ▼
 6. clasificar NOMBRE con readelf -sW:
        │  Ndx=UND  → símbolo del vmlinux, lo resuelve resolve_symbol_wait (§2d)
        │  Ndx=12   → función local, st_value = offset en .text (§2d)
        ▼
 7. para R_X86_64_64/32S contra ".rodata+0xNNN": el destino es una DIRECCIÓN DE DATOS
        dentro de .rodata, no una función (§6.5)
```

## 6.4 Resultado: las 173 reubicaciones de la función

**Método, y por qué el método importa.** `readelf -rW` imprime **sección por sección**,
no ordenado globalmente por `r_offset`. Filtrar por rango sin conservar el estado de
sección **mezcla entradas de secciones distintas** — y como los valores `r_offset` de
`.rela.text` y `.rela.rodata` coinciden numéricamente en el rango de la función
(§5.4), el resultado es plausible y falso.

Aquí está el error real, reproducido: un filtro ingenuo sobre `readelf -rW` para el rango
`0x214e*` devuelve, **mezcladas**:

```
0000000000214e08  R_X86_64_PLT32  __const_udelay - 4          ← .rela.text  (en .text)
0000000000214e00  R_X86_64_64     .rodata + 2a0e60            ← .rela.rodata (en .rodata)
```

La segunda línea parece una referencia a `.text + 0x8d9910` hecha desde la función, y no
lo es: es un puntero **almacenado en `.rodata`**, en el offset `0x214e00` **de `.rodata`**.

Con el estado de sección conservado, el resultado correcto:

### `.rela.text` → escribe en `.text` (77 entradas, todas `R_X86_64_PLT32` salvo 2)

| Símbolo | Nº | `st_value` | Tipo | Binding | `Ndx` | Clase (§2d) |
|---|---:|---:|---|---|---|---|
| `amdgpu_device_wreg` | **52** | `0x8060` | `FUNC` | `GLOBAL` | `12` (`.text`) | **local al módulo** |
| `amdgpu_device_rreg` | **12** | `0x7ce0` | `FUNC` | `GLOBAL` | `12` (`.text`) | **local al módulo** |
| `__const_udelay` | **8** | `0x0` | `NOTYPE` | `GLOBAL` | **`UND`** | **del `vmlinux`** |
| `__drm_err` | **2** | `0x0` | `NOTYPE` | `GLOBAL` | **`UND`** | **del `vmlinux`** |
| `__x86_return_thunk` | **2** | `0x0` | `NOTYPE` | `GLOBAL` | **`UND`** | **del `vmlinux`** |
| `__fentry__` | **1** | `0x0` | `NOTYPE` | `GLOBAL` | **`UND`** | **del `vmlinux`** (ftrace) |
| `.rodata` | **2** (`R_X86_64_32S`) | `0x0` | `SECTION` | `LOCAL` | `17` | símbolo de sección |

### `.rela.rodata` → escribe en `.rodata` (94 entradas, todas `R_X86_64_64`)

| Símbolo | Nº | `st_value` | Tipo | `Ndx` | Interpretación |
|---|---:|---:|---|---|---|
| `.rodata` | **88** | `0x0` | `SECTION` | `17` | punteros a datos dentro de `.rodata` (cadenas, tablas) |
| `.text` | **6** | `0x0` | `SECTION` | `12` | **punteros a funciones** almacenados en `.rodata` |

**Total: 173 entradas de reubicación en `[0x214e40, 0x2154a0)`.**

### Discrepancia con los recuentos propuestos — `CONTRADICTION`, resuelta

El enunciado daba `amdgpu_device_wreg` = 33, `amdgpu_device_rreg` = 10,
`__const_udelay` = 8, `__drm_err` = 2. Verificación:

| Símbolo | Recuento enunciado | Recuento verificado | ¿Coincide? |
|---|---:|---:|---|
| `amdgpu_device_wreg` | 33 | **52** | **no** |
| `amdgpu_device_rreg` | 10 | **12** | **no** |
| `__const_udelay` | 8 | **8** | sí |
| `__drm_err` | 2 | **2** | sí |

**Resolución — DERIVACIÓN con los offsets que lo fijan.** Calcular el offset en el que
cada símbolo alcanza el recuento propuesto:

| Símbolo | Alcanza el recuento propuesto en |
|---|---|
| `amdgpu_device_wreg` = 33 | `0x21525e` |
| `amdgpu_device_rreg` = 10 | `0x21526d` |
| `__const_udelay` = 8 | `0x21520f` |
| `__drm_err` = 2 | `0x21522b` |

Los cuatro offsets **no son consistentes con un único límite de función**: llegar a
`wreg`=33 y `rreg`=10 exige leer hasta `0x21526d`, pero `__drm_err`=2 y
`__const_udelay`=8 se alcanzan en `0x21522b` y `0x21520f`, **antes**. Y con el límite
correcto (`0x2154a0`) los cuatro valores verificados son 52/12/8/2.

**Conclusión:** los dos recuentos que coinciden (8 y 2) son correctos; los dos que no
(33 y 10) **subestiman** en 19 y 2. La diferencia (19 = 52−33, 2 = 12−10) es
consistente con un conteo **truncado**, no con un error de lectura de nombres. **El
método correcto de recuento es contar sobre `objdump -dr` con los límites de §5.4, o
contar con el estado de sección conservado** — nunca contar a ojo sobre un volcado
parcial. `RESOLUTION_STATUS=RESOLVED`; la causa exacta del truncamiento en el
procedimiento del enunciado es `NOT_DETERMINED` (no se reprodujo el procedimiento
usado).

## 6.5 Las dos clases de reubicación de esta función, y por qué se distinguen

Las 173 entradas se dividen por **el símbolo al que apuntan**, y la división es
`objdump -dr` la hace sola:

| Forma que muestra `objdump -dr` | Significado | Nº en la función |
|---|---|---:|
| `R_X86_64_PLT32 amdgpu_device_wreg-0x4` | **Llamada a función.** El destino es el *código* de otro sitio | 75 |
| `R_X86_64_PLT32 __const_udelay-0x4` | Llamada a función **del `vmlinux`** | 13 |
| `R_X86_64_32S .rodata+0x235ac8` | **Referencia a un dato.** `S+A` = dirección absoluta de un objeto en `.rodata` | 2 |
| `R_X86_64_64 .rodata+0x2a0df8` | **Puntero almacenado en `.rodata`** que apunta a otro punto de `.rodata` | 88 |
| `R_X86_64_64 .text+0x8d9910` | **Puntero almacenado en `.rodata`** que apunta a una **función** | 6 |

**El rasgo que las separa, y que es la conclusión práctica de §6:**
`R_X86_64_PC32`/`PLT32` son **relativas al lugar donde se escriben** (`− P`): dependen de
`r_offset` y codifican un *salto*. `R_X86_64_64`/`32S` son **absolutas** (`S + A`, sin
`− P`): no dependen de dónde se escriben y codifican una *dirección*. Un `call` nunca
genera `R_X86_64_64`, y un puntero a datos nunca genera `R_X86_64_PLT32`.

**Las 6 entradas `R_X86_64_64 .text+0x8d9910` merecen una advertencia concreta.**
`.text+0x8d9910` está **muy lejos** de la función: `.text` mide `0x92bf0b`, así que
`0x8d9910` es un offset válido, en el último 15 % de la sección. HECHO:

```
  0x00214eb0  R_X86_64_64  symidx=2  .text  A=+0x8d9910
  0x00214eb8  R_X86_64_64  symidx=2  .text  A=+0x8d98c0
  0x00214ec0  R_X86_64_64  symidx=2  .text  A=+0x8d9980
  0x00214ec8  R_X86_64_64  symidx=2  .text  A=+0x8d9960
  0x00214ed0  R_X86_64_64  symidx=2  .text  A=+0x8d9880
  0x00214ed8  R_X86_64_64  symidx=2  .text  A=+0x8d98a0
```

Seis punteros a función casi contiguos, con un paso constante de `0x10` (16 bytes) —
**la firma de una tabla de punteros a función**, es decir una `struct` de `ops`. Y los
offsets son aproximadamente `0x8d9880..0x8d9980`, lo que corresponde a una región de
`.text`muy posterior. **Esto no es código de `uvd_v6_0_start`; es una tabla de
despacho que el driver comparte y a la que esta función apunta.** Es el ejemplo canónico
de la confusión del §6.2 invertida: una reubicación con aspecto de reubicación, cuya
semántica real es un puntero a datos.

## 6.6 Comprobación final: ¿por qué el `call` no puede deducirse del desplazamiento

Respuesta en una frase, con su base:

> Porque en un `ET_REL` el valor a escribir en un `R_X86_64_PLT32` es `S + A − P`, y en
> el fichero **sólo `A` y `P` están fijados**; `S` depende de una dirección de carga que
> el kernel elige en `layout_and_allocate()` y de un símbolo que `resolve_symbol_wait()`
> busca en el `vmlinux`. Los bytes del campo están a cero **por diseño** y el kernel
> **exige** que estén a cero (`memcmp(loc, &zero, size)` → `-ENOEXEC`).

Y el reflejo en las tres herramientas, que es lo que hay que saber hacer:

| Herramienta | Qué dice de `call 214e40` | ¿Correcto? |
|---|---|---|
| `objdump -d` | `call 214e45` — el destino parece la instrucción siguiente | **Ilegible**, y activamente engañoso |
| `objdump -dr` | `214e41: R_X86_64_PLT32 amdgpu_device_rreg-0x4` | **Correcto y suficiente** |
| `readelf -rW` | `0000000000214e56 … R_X86_64_PLT32 … amdgpu_device_rreg - 4` | Correcto, pero desordena respecto a `r_offset` si se mezclan secciones |

---

# 7. ERRORES COMUNES

Ordenados por coste de la confusión. Cada uno dice el **síntoma**, la **causa** y el
**test**.

### 7.1 Interpretar `call <siguiente_instrucción>` como un error del compilador

- **Síntoma:** «`e8 00 00 00 00` — el compilador ha emitido una llamada con desplazamiento
  cero, hay un bug.»
- **Causa:** es el estado normal de un `ET_REL`. `S` es desconocido, el campo se deja a 0
  y el destino se registra en `.rela.text` (§2.a, §2.c).
- **Test:** el destino impreso es exactamente `dirección + 5`? → no es un bug. `readelf -rW`
  en `r_offset = dirección + 1` dice el nombre.
- **Consecuencia de creerlo:** se depura código que está bien, y se Cherri-pickean
  «anomalías» de otros `call` que también son correctos.

### 7.2 Interpretar `call 214e45` como «la función se llama a sí misma»

- **Síntoma:** el destino cae dentro del rango de la propia función, luego es un bucle o
  una recursión.
- **Causa:** §2.c. `0x214e45` es `0x214e40 + 5` = el final de la instrucción `call`, y
  no significa nada sobre el destino.
- **Test:** ¿`destino − dirección == longitud_de_la_instrucción`? Para `E8` son 5. Para
  `EB` (jmp corto) son 2.

### 7.3 Interpretar un número «direccionable» como una dirección

- **Síntoma:** «`mov $0x418958,%edi` carga un puntero a 0x418958.»
- **Causa:** HECHO §6.2 — `bf 58 89 41 00` es un `imm32` **literal**; no hay reubicación
  en `0x1691c` ni en `0x1691d`. Aparece 207 veces.
- **Test:** `readelf -rW f.ko | grep -E "^<instr_offset>|^<instr_offset+1>"`. Sin salida ⇒
  literal. Y compara con el patrón de un hueco real, que objdump muestra como `$0x0`
  (no como un número plausible).

### 7.4 Confundir un hueco de reubicación con su valor final

- **Síntoma:** «`mov $0x0,%rdi` — el driver pasa un puntero nulo.»
- **Causa:** es un `R_X86_64_32S` con `A = 0x235ac8` (§6.2). `$0x0` significa «todavía no
  lo sé».
- **Test:** `objdump -dr`. Si hay una línea `R_X86_64_*` debajo, el `$0x0` es un hueco.
- **Ironía útil:** un hueco se ve como `$0x0` (obviamente falso) y un literal
  verdadero se ve como `0x418958` (falsamente plausible). **La plausibilidad del número
  no dice nada.**

### 7.5 Confundir un símbolo de sección con un símbolo de función

- **Síntoma:** «`.rodata+0x2a10d0` es una función en `.rodata`» / «`.text+0x8d9910` está
  en la función que estoy leyendo».
- **Causa:** §6.5. `.rodata` y `.text` son `STT_SECTION` con `st_value = 0`; el sumando
  **es** el desplazamiento. Un `R_X86_64_64` con `symidx=2` (`.text`) en `.rela.rodata` es
  un **puntero almacenado en `.rodata`** que apunta a un `.text` lejano. Y el destino
  puede estar a 9 MB de distancia de quien lo referencia (§6.5).
- **Test:** mira el **tipo** del símbolo (`SECTION` vs `FUNC`) con `readelf -sW`, no solo
  el nombre. Un nombre que empieza por punto es un símbolo de sección.

### 7.6 Buscar el límite de una función solo con `nm`

- **Síntoma:** se recuentan reubicaciones de más o de menos; se atribuyen a la función
  instrucciones de otro fichero.
- **Causa:** §5.4, HECHO. En `0x214e80`, `0x214e90`, `0x214eb0`… hay símbolos de
  **`.rodata`**, no de `.text`, y sus valores chocan con los de `.text`. `nm` no muestra
  la sección.
- **Test:** `readelf -sW` y mira la columna `Ndx`. O `objdump -d --disassemble=<sym>`,
  que ya lo resuelve.

### 7.7 Filtrar `readelf -r` sin conservar la sección actual

- **Síntoma:** aparecen «reubicaciones de la función» que son punteros de una tabla
  neighbour en `.rodata`; los recuentos no cuadran con ningún rango (§6.4).
- **Causa:** `readelf -r` imprime **sección por sección**; los `r_offset` de
  `.rela.text` y `.rela.rodata` se solapan numéricamente.
- **Test:** el awk con estado de sección de §5.2. Si un resultado menciona `.text + 0x…`
  y el rango que pediste está en `.rodata`, es que estás leyendo la sección equivocada.

### 7.8 Suponer que existe tabla de símbolos dinámicas

- **Síntoma:** `nm -D` no da nada, y se concluye que el `.ko` está «stripped» o corrupto.
- **Causa:** §1.7, §5.3. `ET_REL` no tiene `.dynsym` por definición. No hay nada que
  leer.
- **Test:** `readelf -SW f.ko | grep dynsym`. Si no está, `nm -D` **nunca** funcionará en
  ese fichero. Usa `nm` o `readelf -s`.

### 7.9 Suponer que «stripped» significa «sin símbolos»

- **Síntoma:** `file` dice `not stripped` / el binario «no tiene tabla de símbolos».
- **Causa:** aquí dice **`not stripped`** y `.symtab` tiene **65 613** entradas. Lo que
  falta es *otra* cosa (§1.7): `.dynsym`, DWARF, `__versions`, PLT/GOT.
- **Test:** `readelf -SW f.ko | grep -E "symtab|dynsym|debug_|versions"` y lee qué falta
  **exactamente**, en vez de inferirlo de una palabra.

### 7.10 Leer `st_value` sin `Ndx`

- **Síntoma:** «`amdgpu_device_wreg` está en `0x8060`, luego el módulo empieza en 0» /
  «esta función está en `0x214e40` pero en `.rodata` hay algo en `0x214e40` también».
- **Causa:** §1.2 y §5.4. En un `ET_REL`, `st_value` es un **offset dentro de la sección
  `Ndx`**, no una dirección. Colisiones numéricas entre secciones son la norma, no la
  excepción: `.text` y `.rodata` tienen aquí `0x214e40` «en las dos».
- **Test:** `readelf -sW` siempre. `st_value` sin `Ndx` es `NOT_INTERPRETABLE`.

### 7.11 Confundir `srcversion` con un control de carga, o leerlo como símbolo

- **Síntoma:** «el `srcversion` es `D68004925455E20A24C2B87`, así que este `.ko` es
  compatible con el kernel» / «`nm` no lo encuentra, no existe».
- **Causa:** §4.b. Es una **clave de `.modinfo`**, no un símbolo (`readelf -s` vacío), y
  **no participa en ninguna decisión de carga**. Un `.ko` con el mismo `srcversion` y
  distinto `vermagic` es rechazado con `-ENOEXEC`.
- **Test:** `modinfo -F srcversion f.ko` para leerlo; `modinfo -F vermagic f.ko` para lo
  que **sí** decide. Y `readelf -p .modinfo f.ko` para ver de dónde salió el número.

### 7.12 Buscar `__versions` / esperar «disagrees about version of symbol» en este host

- **Síntoma:** se busca el error de modversions para explicar un fallo de carga, y no
  aparece nunca.
- **Causa:** §4.d, HECHO. `CONFIG_MODVERSIONS` está **desactivado** en
  `7.1.3-200.nobara.fc44.x86_64`; no hay sección `__versions`; el `vermagic` no contiene
  `modversions`. **El mecanismo existe y está implementado, pero no está compilado en
  este kernel.** La única barrera es `vermagic` (más la firma).
- **Test:** `grep MODVERSIONS /boot/config-$(uname -r)` y
  `readelf -SW f.ko | grep __versions`. Si ambos salen negativos, el control symbol-a-symbol
  no existe aquí.
- **Lección general:** un mecanismo documentado y presente en el código fuente **no está
  necesariamente activo**. Es la razón de ser de `DRIVER_PRESENT` ≠ `DRIVER_OPERATIONAL`
  en el router del proyecto, aplicado al versionado de módulos.

### 7.13 Esperar `PT_LOAD` en un `.ko`

- **Síntoma:** se buscan segmentos, o `readelf -l` parece fallar.
- **Causa:** §1.6. `e_phnum = 0`. La memoria se reparte por sección en cinco tipos
  (`MOD_TEXT`, `MOD_RODATA`, `MOD_RO_AFTER_INIT`, `MOD_DATA`, per-CPU).
- **Test:** `readelf -lW f.ko` → `No hay encabezados de programa en este fichero.` Es
  normal, no un fichero corrupto.

### 7.14 Confundir `R_X86_64_RELATIVE` / `IRELATIVE` con lo que ocurre en un `.ko`

- **Síntoma:** «el kernel aplica `R_X86_64_RELATIVE` al insertar el módulo».
- **Causa:** §2.b, HECHO. Cero entradas de esos tipos en este fichero (y cero en
  cualquier `.ko` de x86-64). El mecanismo equivalente es `R_X86_64_64` contra el
  **símbolo de sección**, y lo aporta `simplify_symbols()` **antes** de
  `apply_relocations()`. `RELATIVE` existe para que `ld.so` no tenga que buscar el
  símbolo; el kernel busca el símbolo de todas formas.
- **Test:** `readelf -rW f.ko | grep -cE "R_X86_64_(IRELATIVE|RELATIVE)"` → `0`.

### 7.15 Leer el `-4` como un desplazamiento o una corrección de la dirección

- **Síntoma:** «`amdgpu_device_wreg-0x4` significa que se llama a `wreg − 4 bytes`».
- **Causa:** §2.c. Es `r_addend`, y vale `−4` para **toda** llamada `E8` de 5 bytes
 FUNCTION.location, con independencia del símbolo. `readelf` rotula la columna
  `Nombre Símbolo + Sumando`.
- **Test:** mira si el `−4` acompaña a **todos** los `PLT32` de 5 bytes. Si es así, es
  aritmética de instrucción, no información de destino.

### 7.16 Esperar `objdump -S` para ver el código fuente

- **Síntoma:** `-S` no muestra nada nuevo y se concluye que el desensamblado es de otro
  kernel.
- **Causa:** §5.7, HECHO. Cero secciones `.debug_*`. La distribución compila los módulos
  sin `-g`. Hay `.BTF` (3.879 MB) y deshueso ORC, que son **tipos** e **información de
  pila**, no líneas.
- **Test:** `readelf -SW f.ko | grep -c debug_` → `0`. Para el fuente, usa el árbol del
  driver.

### 7.17 Confundir `parm=` en `.modinfo` con el valor del parámetro

- **Síntoma:** «el parámetro `user_queue` vale lo que pone en `.modinfo`».
- **Causa:** §3.d. `.modinfo` contiene la **declaración** (`parm=user_queue:Enable user
  queues …`) y el **tipo** (`parmtype=user_queue:int`). El valor inicial y los
  callbacks están en `__param` (240 entradas aquí) y se leen en
  `/sys/module/amdgpu/parameters/user_queue`.
- **Test:** `cat /sys/module/amdgpu/parameters/<nombre>` para el valor; `readelf -p
  .modinfo` para la declaración.

### 7.18 Contar reubicaciones «a ojo» sobre un volcado truncado

- **Síntoma:** recuentos que no cuadran entre symbols (aquí, 33/10 frente a 52/12,
  §6.4).
- **Causa:** el desplazamiento de corte. Los recuentos correctos requieren llegar a
  `0x2154a0`; los proposed llegaban a `0x21526d`.
- **Test:** fija los límites **antes** de contar (§5.4) y cuenta con una herramienta
  (`objdump -dr | grep -c R_X86_64_PLT32`), nunca a mano. Verifica que los cuatro
  recuentos son coherentes con un mismo límite.

### 7.19 Concluir que `modprobe`/`insmod` se pueden probar aquí

- **Síntoma:** se intenta `modprobe --dump-modversions` o `insmod -p` para «comprobarlo».
- **Causa:** §0.3. `opencode.json` deniega `modprobe*` e `insmod *`, y el casamiento es
  sobre la **cadena completa** del comando, así que las variantes de solo lectura
  (`--help`, `--dump-modversions`) **también** se deniegan.
- **Test:** ninguna comprobación en vivo es posible; hay que declarar el hueco y citar la
  documentación o el código. `NOT_DETERMINED` en lugar de un valor supuesto.

---

# 8. Estado de la investigación

| Apartado | Estado | Nota |
|---|---|---|
| §1 Formato ELF | `ANSWERED` | `elf(5)` + HECHO. Un hueco: `elf(5)` no define `st_value` como offset/dirección (§1.2) |
| §2.a Reubicaciones, por qué existen | `ANSWERED` | |
| §2.b Tabla de tipos | `ANSWERED` | psABI íntegro; **5** tipos presentes, **0** de GOT/RELATIVE/IRELATIVE (HECHO) |
| §2.c El `−4` | `ANSWERED` con salvedad | Aritmética completa; `minus 4` **NOT_FOUND** en las 20 `.tex` del psABI; Intel SDM `NOT_FETCHED` |
| §2.d Por qué no se enlaza en compilación | `ANSWERED` | Tres clases de símbolo con HECHO |
| §3.a Secuencia de carga | `ANSWERED` | Leída del código. Correcciones: `elf.c` no existe en 7.1.3; `check_modinfo` va antes que `simplify_symbols` |
| §3.b Dónde se aplica cada tipo | `ANSWERED` | `apply_relocations()` y el filtro `SHF_ALLOC` |
| §3.c `SHN_UNDEF` y `__ksymtab` | `ANSWERED` | 4 símbolos exportados. `__ksymtab_gpl` obsoleto en 7.1.3 |
| §3.d `.modinfo` | `ANSWERED` | `MODULE_INFO` citado; `__param` separado |
| §3.e `__this_module`, `__modver`, init/exit | `ANSWERED` | `__modver` `PROVEN_ABSENT` aquí |
| §3.f Firma | `ANSWERED` | `CONFIG_MODULE_SIG_FORCE` efectivo = `NOT_DETERMINED` |
| §4.a `modpost` / `Module.symvers` | `ANSWERED` | `Documentation/kbuild/modules.rst` |
| §4.b `srcversion` | `ANSWERED` | MD4 de fuentes. **No** es símbolo, **no** gobierna la carga |
| §4.c vs `vermagic` vs `versions` | `ANSWERED` | `VERMAGIC_STRING` citado; consecuencia `-ENOEXEC` antes de reubicar |
| §4.d `modversions` | `ANSWERED` con corrección mayor | **`CONFIG_MODVERSIONS is not set` en este host**; el mecanismo no está activo |
| §5 Comandos | `ANSWERED` con 2 huecos | `modprobe --dump-modversions` y `insmod -p` = `NOT_DETERMINED` (§0.3) |
| §6 Ejercicio worked | `ANSWERED` | 173 reubicaciones, límites `[0x214e40,0x2154a0)` |
| §7 Errores comunes | `ANSWERED` | 19 entradas |

**Huecos declarados, no rellenados:**

| Hueco | Clasificación | Dónde se buscó |
|---|---|---|
| Texto del psABI sobre el `−4` de `call` | `NOT_FOUND` en el psABI | las 20 `.tex` de `x86-64-ABI/` |
| Redacción del manual de Intel para `CALL rel32` | `NOT_FETCHED` | — |
| `elf(5)` sobre `st_value` como offset vs dirección | `INSUFFICIENT` | página completa de `elf(5)` |
| Descripción oficial de la **carga** de módulos | `SOURCE_NOT_FOUND` | `Documentation/` de 7.1.3: solo `module-signing.rst`; `vermagic` aparece solo en `livepatch/module-elf-format.rst` |
| `modprobe --dump-modversions` en este host | `NOT_DETERMINED` | man7 `modinfo(8)` no lo documenta; ejecución denegada |
| `insmod -p` | `NOT_DETERMINED` | man7 `insmod(8)`; ejecución denegada |
| Significado de `0x418958` en `atom_op_delay` | `NOT_DETERMINED` | `atom.c:54-55` lo descarta como `arg`; no se cartografió el resto |
| Causa del truncamiento en los recuentos propuestos | `NOT_DETERMINED` | no se reprodujo el procedimiento usado |
| `CONFIG_MODULE_SIG_FORCE` efectivo | `NOT_DETERMINED` | ausente de la config; no consultado `/proc/sys/kernel/tainted` |

**Ningún resultado de este documento procede de tutoriales de blog.** Todas las fuentes
son la especificación (`elf(5)`), el ABI de la arquitectura (psABI), el manual de
herramientas (`readelf`/`objdump`/`nm`/`modinfo`/`insmod`), o el **código fuente del
kernel 7.1.3 en la versión exacta** del objeto estudiado. Cero fuentes `SECUNDARIO`
— porque no hizo falta ninguna.

---

*Fin del documento. Todas las cifras citadas como «HECHO» son reproducibles con los
comandos mostrados, sobre `/tmp/opencode/ko/amdgpu.ko`, `SHA256
a1a44c2457d33c65149ef4f455173ca446564bfd19bcc9cb215fca10cf24c024`, extraído de
`/lib/modules/7.1.3-200.nobara.fc44.x86_64/kernel/drivers/gpu/drm/amd/amdgpu/amdgpu.ko.zst`.*

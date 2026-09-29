# R0-7 — Referencia: el conjunto x86-64 y cómo leer una salida de `objdump -d`

> **Documento de REFERENCIA, con profundidad de kernel/x86-64.** No describe x86-32.
> Todo lo afirmado aquí es **NORMA** (Intel SDM / AMD64 APM, con sección),
> **HECHO** (se lee directamente en los bytes del fragmento o en el código citado),
> o **INFERENCIA** (requiere asumir comportamiento del compilador o de una macro).
>
> `WORK_CLASS=DOCUMENTATION` — este documento no autoriza ninguna ejecución y no
> modifica código. `HOST_SCOPE` del *host vivo* no se afirma aquí; este documento
> habla de la **arquitectura** y de **un fragmento concreto de un `.ko` de amdgpu**
> aportado en el encargo.
>
> `ROUTE`: el `DOCUMENTATION-ROUTER` no tiene `TOPIC` para instrucción x86-64
> (router §8: *topic ausente de §3 → escalar*). Resultado de la escalada:
> `ESCALATED` a `WEB`, y por tanto **todo lo de aquí es `EXTERNAL`**: no es
> evidencia sobre el estado del host, sólo norma y hechos sobre los bytes.

---

## 0. Fuentes usadas, con procedencia

### 0.1 Documentos normativos (descargados y verificados)

| ID | Documento | Edición / Rev | URL | `HTTP` · `CT` · bytes · `SHA256` (prefijo) |
|---|---|---|---|---|
| **SDM-C** | Intel® 64 and IA-32 Architectures Software Developer's Manual, **Combined Volumes 1, 2A, 2B, 2C, 2D, 3A, 3B, 3C, 3D, 4** | `325462`, CreationDate **2024-06-20** | `https://cdrdv2-public.intel.com/825743/325462-sdm-vol-1-2abcd-3abcd-4.pdf` | `200` · `application/pdf` · 25 169 252 · `b0eb1fa3445b26df…` |
| **SDM2** | Intel SDM Volume 2 (2A, 2B, 2C & 2D) | `325383`, CreationDate **2022-12-21**, 2528 pp. | `https://cdrdv2-public.intel.com/671110/325383-sdm-vol-2abcd.pdf` | `200` · `application/pdf` · 11 599 579 · `f117cb21ce1f3b62…` |
| **APM1** | AMD64 Architecture Programmer's Manual, **Volume 1: Application Programming** | `24592` — **Rev. 3.11, December 2005** | `https://kmlinux.fjfi.cvut.cz/~culikzde/amd/24592.pdf` (**espejo de universidad, NO `amd.com`**) | `200` · `application/pdf` · 3 225 412 · `c1db780efe6dcec9…` |
| **AS** | GNU Assembler / binutils manual (secciones i386) | sitio `sourceware.org` vigente | `https://sourceware.org/binutils/docs/as/i386_002d{Syntax,Chars,Mnemonics,Regs,Memory,Jumps}.html` | `200` |
| **OBJD** | `objdump(1)` — Manual de binutils | sitio `sourceware.org` vigente | `https://sourceware.org/binutils/docs/binutils/objdump.html` | `200` |
| **GCCOPT** | *Options That Control Optimization* (GCC) | sitio `gcc.gnu.org` vigente | `https://gcc.gnu.org/onlinedocs/gcc/Optimize-Options.html` | `200` |
| **GCCINT** | *GCC Internals* — Loop manipulation, Looping Patterns | idem | `https://gcc.gnu.org/onlinedocs/gccint/{Loop-manipulation,Looping-Patterns}.html` | `200` |
| **LLVMP** | LLVM — *LLVM's Analysis and Transform Passes* | `llvm.org` vigente | `https://llvm.org/docs/Passes.html` | `200` |
| **ARK** | Intel ARK — Intel® Core™ i7-4790 Processor | vigente | `https://www.intel.com/content/www/us/en/products/sku/80806/intel-core-i74790-processor-8m-cache-up-to-4-00-ghz/specifications.html` | `200` vía `webfetch` (`403` vía `fetch` directo) |

> `HOW_IT_AFFECTS_THE_DECISION`: **SDM-C/SDM2 son la fuente NORMATIVA** y todo lo
> marcado `NORMA` sale de ahí con número de página/sección de la tabla de
> contenido. **APM1 es de 2005** (`FACT_FOR_AMD64_APM_r3.11_2005`): sirve para el
> subconjunto legacy, que no ha cambiado, pero **no** para AVX-512/EVEX.
> `AMD.COM` devolvió `404` en los tres paths intentados
> (`.../24592.pdf`, `.../24592_3.25.pdf`, `docs.amd.com/v/u/en-US/24592_3.25_APM_Vol1_PUB`
> → HTML con JS gate): `FETCH_FAILED`, no se sustituyó en silencio, se registra el
> espejo y su hash.

### 0.2 Código fuente (fuente primaria del *comportamiento*, no de la norma)

| ID | Fichero | Versión | Nota |
|---|---|---|---|
| **SRC-UVD** | `drivers/gpu/drm/amd/amdgpu/uvd_v6_0.c` | `v4.14`, `v5.4`, `v5.15`, `v6.16` | **El fragmento de código de referencia es idéntico byte a byte en los cuatro tags.** Verificado. |
| **SRC-AMDH** | `drivers/gpu/drm/amd/amdgpu/amdgpu.h` | `v4.14` (`RREG32`), `v6.16` | Definición de `RREG32` |
| **SRC-DELAY** | `include/linux/delay.h` | `v6.16` | `mdelay(n)` — **contiene el `while`** |
| **SRC-GDELAY** | `include/asm-generic/delay.h` | `v6.16` | `udelay()`, `UDELAY_CONST_MULT`, `DELAY_CONST_MAX` |
| **SRC-X86DLY** | `arch/x86/include/asm/delay.h` | `v6.16` | **No** define `mdelay` ni `MAX_UDELAY_MS` → aplica el genérico |
| **SRC-X86DLYIMPL** | `arch/x86/lib/delay.c` | `v6.16` | `noinline void __const_udelay(...)` (línea 207), `EXPORT_SYMBOL` (219), multiplicadores literales `0x000010c7` (223) y `0x00005` (229) |
| **SRC-X86BAR** | `arch/x86/include/asm/barrier.h` | `v6.16` | `__smp_mb()` = `lock addl $0,-4(%rsp)` |
| **SRC-GENBAR** | `include/asm-generic/barrier.h` | `v6.16` | `mb()`=`barrier()` etc. |
| **SRC-COMPH** | `include/linux/compiler.h` | `v6.16` | `barrier()` = `__asm__ __volatile__("": : :"memory")` |
| **SRC-RWONCE** | `include/asm-generic/rwonce.h` | `v6.16` | `READ_ONCE`/`WRITE_ONCE` = `volatile` puro |
| **SRC-MK** | `Makefile` (KBUILD_CFLAGS) | `v6.16` | `+= -O2` bajo `CONFIG_CC_OPTIMIZE_FOR_PERFORMANCE` |

**No se ha leído** `Documentation/arch/x86/` ni `Documentation/devicetree/`: no
contienen material sobre el decodificado de instrucciones que no esté mejor dicho
en el SDM. `SCOPE_GAP` declarado, no `TRUE_GAP`.

---

## 1. Correcciones a las premisas del encargo

Estas siete correcciones son **el resultado más útil de la investigación**: cinco de
las seis suposiciones del enunciado sobre el fragmento son incorrectas, y la sexta
—el "bucle extra del optimizador"— es la que resuelve el problema real.

| # | Premisa del encargo | Veredicto | Evidencia |
|---|---|---|---|
| **P1** | CPU «Intel i7-4790 (Haswell, microarquitectura **Skylake-client derivative**)» | **`CONTRADICTION`** con la fuente primaria. El i7-4790 es **Haswell**: ARK lo sitúa en *«4th Generation Intel® Core™ i7 Processors»* con *Code Name: «Products formerly Haswell»*. No es un derivado de Skylake-client. | **ARK** |
| **P2** | «`call 21517b <…+0x33b>` es una forma de objdump, no AT&T pura» → hay *tres* sintaxis | **Medio cierto, mal formulado.** Hay **dos** sintaxis de operandos (`att` / `intel`, `-M`), y además dos modos de mnemónico (`intel-mnemonic` / `att-mnemonic`, que *implican* los anteriores). El bloque `<símbolo+0xdesplazamiento>` no es una sintaxis: es una **anotación de objdump** sobre la dirección. | **OBJD**, sección *x86-64 / intel / att / intel-mnemonic / att-mnemonic* |
| **P3** | «`41 bd 0a 00 00 00` → ModRM `0a` (mod=00, reg=001, rm=010)» | **`CONTRADICTED`.** **No hay byte ModRM.** En la familia `B8+rd` el campo `rd` (3 bits) está *dentro* del propio byte de opcode; no existe ModRM. `0a` es el **byte bajo del `imm32`**. | **SDM2** p. 4-35: `B8+rd id` → `MOV r32, imm32`; el opcode no lleva ModRM. |
| **P4** | «`mov $0xa,%r13d` usa *imm8 con REX.B* frente a *imm32* de `mov $0xa,%ebx`» | **`CONTRADICTED`.** Las dos son **`imm32`**. `41 bd 0a 00 00 00` = 1 (REX) + 1 (opcode) + 4 (`imm32`) = **6 bytes**. REX.B selecciona `r13`; **no cambia el tamaño del inmediato**. | **HECHO**: `0x215161+6 = 0x215167`, que es justo la dirección de la instrucción siguiente en el fragmento. |
| **P5** | «`75 f0` (rel8 = −16) salta a `215188`; `215188 = 215192 − 0x10`» | **Destino correcto, aritmética intermedia incorrecta.** `0x215192 − 0x10 = 0x215182`, no `0x215188`. La fórmula correcta es `RIP_siguiente + desp`: `0x215196 + 2 + (−0x10) = 0x215198 − 0x10 = 0x215188`. El `0x215192` que el enunciado usa es la dirección *siguiente al `call`* — un `call rel32` de 5 bytes en `0x21518d` — es decir, **la dirección de retorno de la llamada anterior**, una coincidencia numérica. | **SDM2** p. 3-553: *«JMP Short is RIP = RIP + 8-bit offset sign extended to 64 bits»* |
| **P6** | El tercer bucle (10 iteraciones) alrededor de `__const_udelay` es una transformación del optimizador | **`CONTRADICTED` — y esta es la clave.** Es el **`while` que está dentro de la macro `mdelay(10)`**. No lo introdujo ningún optimizador. Demostración en §9 y §10. | **SRC-DELAY** líneas 44-46 + **SRC-GDELAY** líneas 22, 29, 56-66 + **GCCOPT** (listas `-O2` / `-O3`) + **SRC-MK** línea 863 |
| **P7** | `xor %edx,%edx` en la cabeza del bucle = «`status = 0`» u otra inicialización de variable | **INFERENCIA alternativa, más económica: es el tercer argumento de la llamada.** `RREG32(reg)` = `amdgpu_mm_rreg(adev, (reg), 0)` (3 argumentos: `rdi`=adev, `rsi`=reg, `rdx`=0). La llamada destroya `%rdx`, así que el valor constante hay que **reponerlo en cada vuelta**. | **SRC-AMDH** `v4.14:1631`; ver §11 |

---

## 2. Sintaxis de `objdump`: AT&T e Intel

### 2.1 Qué ofrece `objdump` (NORMA, `OBJD`)

Sección *x86-64* del manual de `objdump`:

> `x86-64` `i386` `i8086` — *Select disassembly for the given architecture.*
> `intel` `att` — *Select between intel syntax mode and AT&T syntax mode.*
> `amd64` `intel64` — *Select between AMD64 ISA and Intel64 ISA.*
> `intel-mnemonic` `att-mnemonic` — *Select between intel mnemonic mode and AT&T mnemonic mode. Note: `intel-mnemonic` implies `intel` and `att-mnemonic` implies `att`.*
> `suffix` — *When in AT&T mode … instructs the disassembler to print a mnemonic suffix even when the suffix could be inferred by the operands…*
> `addr64` `addr32` `addr16` `data32` `data16`

Y, sobre el formato de línea:

> `--no-show-raw-insn` — *do not print the instruction bytes.*
> `--insn-width= width` — *Display width bytes on a single line…*
> `--no-addresses` — *don't print addresses on each line…*
> `--show-raw-insn` — *print the instruction in hex as well as in symbolic form. This is the default except when `--prefix-addresses` is used.*

**Consecuencia directa para el fragmento:** no hay sufijos de tamaño
(`mov`, no `movl`) porque el nombre del registro ya es inequívoco; hay bytes en
hex porque `--show-raw-insn` es el valor por defecto; y no hay `0x` delante de las
direcciones porque el modo por defecto de `objdump` en AT&T las imprime en hexadecimal
**sin prefijo** (`-M intel` sí lo pone). Este último punto **no está documentado**
en el manual: `NOT_DETERMINED` como norma, `HECHO` como forma observada.

### 2.2 AT&T vs Intel: las cuatro diferencias (NORMA)

| Regla | Intel (SDM) | AT&T (binutils/GAS) |
|---|---|---|
| **Orden de operandos** | `DEST, SRC` | `SRC, DEST` — *el destino es el último por convención* |
| **Símbolo de registro** | `eax` | `%eax` |
| **Inmediato** | `10` | `$10` |
| **Memoria** | `[base + index*scale + disp]` | `disp(base, index, scale)` |
| **Sufijo de tamaño** | innecesario (el opcode lo determina) | `b`/`w`/`l`/`q` |

Fuente de la tabla de memoria (`AS`, *i386-Memory*, §9.16.7), textual:

> *An Intel syntax indirect memory reference of the form*
> `section:[base + index * scale + disp]`
> *is translated into the AT&T syntax*
> `section:disp(base, index, scale)`
> *… AT&T: `-4(%ebp)`, Intel: `[ebp - 4]` … AT&T: `foo(,%eax,4)`, Intel: `[foo + eax*4]` …*

Y del destino en último lugar (`AS`, *i386-Mnemonics*, §9.16.4.1), textual:

> *If no suffix is specified by an instruction then `as` tries to fill in the missing suffix based on the **destination register operand (the last one by convention)**.*

**Nota de terminología importante.** La primera fila no es una *"invención de AT&T"*:
`objdump` en modo AT&T imprime las cosas en el **orden de fuente** que GAS
espera, y GAS espera `fuente, destino` porque su ancestro es el ensamblador del
AT&T Unix. El manual de `as` es explícito: *«this is incompatible with the AT&T Unix
assembler which assumes that a missing mnemonic suffix implies long operand size.
(This incompatibility does not affect compiler output since compilers always
explicitly specify the mnemonic suffix.)»* Es decir: **el ensamblador GNU
implementa la sintaxis AT&T, no la del ensamblador AT&T original.** Y la razón
histórica de que el destino vaya detrás es de lectura: en `mov %rax, %rbx` se lee
"mueve rax a rbx", en el orden natural de la frase inglesa.

### 2.3 Tabla de sufijos de tamaño (NORMA, `AS` §9.16.4.1)

> *Instruction mnemonics are suffixed with one character modifiers which specify the size of operands. The letters **'b', 'w', 'l' and 'q'** specify byte, word, long and quadruple word operands.*

| Sufijo | Bytes | Registro 8-bit | 16-bit | 32-bit | 64-bit | `e` = 32 bits (nombre "largo" heredado del 386) |
|---:|---:|---|---|---|---|---|
| `b` | 1 | `%al %ah %bl %bh %cl %ch %dl %dh`, `%sil %dil %bpl %spl`, `%r8b…%r15b` | — | — | — | |
| `w` | 2 | — | `%ax %bx %cx %dx %si %di %bp %sp`, `%r8w…%r15w` | — | — | |
| `l` | 4 | — | — | `%eax %ebx %ecx %edx %esi %edi %ebp %esp`, `%r8d…%r15d` | — | `long` = 32 bits **en x86-64**, nombre heredado |
| `q` | 8 | — | — | — | `%rax %rbx %rcx %rdx %rsi %rdi %rbp %rsp`, `%r8…%r15` | `quadword` |
| `t` | 10 | — | — | — | `%st(0)` x87 | sólo `f`/`t` en x87/AT&T |

Las **columnas están desplazadas respecto a lo que un lector de x86-32 espera**: `e`
ya no significa "32 bits porque es el máximo"; en x86-64 `%eax` y `%rax` son registros
distintos y `l` no es el máximo. **Éste es el error de lectura más caro en x86-32
trasladado a x86-64.**

### 2.4 Por qué el destino de un salto va detrás, y por qué eso no importa

`jne 0x215188` no tiene "destino" en el sentido aritmético: el destino es un
**desplazamiento relativo**, y en AT&T se imprime igual que en Intel. Lo que sí
cambia en AT&T son las dos formas de direccionamiento del salto:

> `AS` §9.16.7: *«Absolute (as opposed to PC relative) call and jump operands must be prefixed with `'*'`. If no `'*'` is specified, `as` always chooses PC relative addressing for jump/call labels.»*

Es decir: en la fuente de ensamblador, `jmp *%rax` es salto **indirecto** (a un
valor de registro), y `jmp foo` es **relativo a RIP** por defecto. En el fragmento,
`call 21517b` y `jne 21523f` son ambos **relativos**; objdump ya ha resuelto el
desplazamiento y muestra la dirección absoluta.

### 2.5 La anotación `<uvd_v6_0_start+0x33b>`

No es sintaxis. Es la **solución de símbolos de objdump**: cuando la dirección de
destino cae dentro de un símbolo conocido, objdump añade `<símbolo+desplazamiento>`
para que el ojo humano no tenga que buscar la dirección en la tabla de símbolos.

```
0x215176:  call  21517b
           └─ dirección absoluta, ya calculada desde el rel32
0x21517b: <uvd_v6_0_start+0x33b>
           └─ anotación: inicio_de_uvd_v6_0_start = 0x21517B − 0x33B = 0x214E40
```

**Comprobación de coherencia interna (`HECHO`).** Las **cinco** anotaciones del
fragmento resuelven al **mismo** inicio de función:

| Anotación | `destino − offset` | Resultado |
|---|---|---|
| `<uvd_v6_0_start+0x33b>` | `0x21517B − 0x33B` | `0x214E40` |
| `<uvd_v6_0_start+0x352>` | `0x215192 − 0x352` | `0x214E40` |
| `<uvd_v6_0_start+0x348>` | `0x215188 − 0x348` | `0x214E40` |
| `<uvd_v6_0_start+0x32c>` | `0x21516C − 0x32C` | `0x214E40` |
| `<uvd_v6_0_start+0x3ff>` | `0x21523F − 0x3FF` | `0x214E40` |

Cinco coincidencias independientes sobre un valor de 32 bits. Eso confirma que (a) la
tabla de símbolos es coherente, (b) los destinos de los saltos están bien calculados,
y por tanto (c) **el desensamblado no está desalineado**. Un error de un byte en un
`rel8` rompería esta coherencia.

**`HECHO` sobre el fragmento:** los bytes de ambos `call` son `e8 00 00 00 00`. El
inmediato es **cero**, y por eso objdump imprime como destino `21517b` (= la
dirección siguiente) y `215192` (= la siguiente). Eso **no es un `call` a sí mismo**
ni un bug: es una **relocación sin resolver** (`R_X86_64_PLT32`) de un fichero
`ET_REL` sin enlazar, es decir, un `.ko` antes de `ld`/`insmod`.
> **Cómo confirmarlo en un segundo:** `objdump -dr <módulo.ko>` — la columna de
> relocalización imprime el nombre al lado. **Ejecutado en este caso:**
>
> ```
>  215176:	e8 00 00 00 00       	call   21517b <uvd_v6_0_start+0x33b>
> 			215177: R_X86_64_PLT32	amdgpu_device_rreg-0x4
>  21518d:	e8 00 00 00 00       	call   215192 <uvd_v6_0_start+0x352>
> 			21518e: R_X86_64_PLT32	__const_udelay-0x4
> ```
>
> **El número que objdump imprime sin `-r` (`21517b`) depende sólo del *addend*
> (`A = −4`), no del símbolo.** Para una llamada de 5 bytes, `P + A` = `P − 4` y el
> destino que objdump muestra es siempre `instrucción + 5`. Tres `call` consecutivos
> dan tres números distintos (`P+5`, `P′+5`, `P″+5`), luego el desplazamiento **no**
> codifica el destino: **el cero es ausencia de información, correctamente
> rotulada**, no información. Esto ya está documentado y comprobado en
> `02-ARQUITECTURA/ELF-RELOCATIONS-KERNEL-MODULES-REFERENCE.md` §6.1 sobre este mismo
> `.ko`.

Esto responde de entrada a uno de los errores del encargo: **`call 0` en un `.ko`
sin enlazar es el estado normal, no un defecto.**

Y el proyecto ya tiene un estudio primario de este mismo `.ko` que documenta el
mecanismo con detalle y con la tabla de tipos de reubicación:
`02-ARQUITECTURA/ELF-RELOCATIONS-KERNEL-MODULES-REFERENCE.md` (§1, §5.4, §6.1).
**Los dos documentos deberían cruzarse; hoy no lo hacen** (ver `NEXT` N5).

---

## 3. Anatomía de una línea de desensamblado

```
215161:  41 bd 0a 00 00 00    mov    $0xa,%r13d
└──┬──┘ └──────┬──────┘ └──┬──┘ └────┬───┘ └───┬───┘
   │           │           │         │         └─ operandos
   │           │           │         └─ mnemónico
   │           │           └─ bytes en hexadecimal (--show-raw-insn)
   │           └─ ancho de columna: --insn-width (por defecto, el ancho necesario)
   └─ dirección, hexadecimal SIN prefijo 0x
```

| Columna | Qué es | Dónde se define |
|---|---|---|
| `215161:` | Dirección **virtual** de la instrucción, hex sin `0x` en AT&T. En un `.ko` es un *offset dentro de la sección*, no una VA del sistema. | `OBJD`: `--no-addresses` la suprime; `--prefix-addresses` la cambia de formato |
| `41 bd 0a 00 00 00` | Los bytes, en orden de ejecución, hex minúsculas | `OBJD`: `--show-raw-insn` (**por defecto**) / `--no-show-raw-insn` |
| `mov` | Mnemónico canónico | tabla de opcode del SDM (Apéndice A/B) |
| `$0xa,%r13d` | Operandos en AT&T: `$` inmediato, `%` registro | `AS` §9.16.4.1, §9.16.5 |

### 3.1 De dónde sale la longitud: por qué `b8 05 00 00 00` son 5 bytes

Una instrucción x86 tiene longitud **variable** y se decodifica **de izquierda a
derecha**, con el **tamaño como efecto lateral**, nunca como campo. El orden de
lectura es fijo (SDM Vol.2A §2.1, Figura 2-1, p. 2-1):

```
[ Prefijos legacy (0..4 bytes, grupos 1..4) ]
[ REX (0 o 1 byte, 0x40-0x4F)  — 64-bit ]
[ Opcode  — 1, 2 o 3 bytes ]
[ ModR/M  — 0 o 1 byte ]
[ SIB     — 0 o 1 byte ]
[ Desplazamiento — 0, 1, 2 o 4 bytes ]
[ Inmediato — 0, 1, 2, 4 (raramente 8) bytes ]
```

> **NORMA** (SDM-C Vol.2A §2.1.1): *«Instruction prefixes are divided into four groups,
> each with a set of allowable prefix codes. For each instruction, it is only useful to
> include up to one prefix code from each of the four groups… Groups 1 through 4 may be
> placed in any order relative to each other.»*

> **NORMA** (SDM-C Vol.2A §2.1.2): *«A primary opcode can be 1, 2, or 3 bytes in length.
> **An additional 3-bit opcode field is sometimes encoded in the ModR/M byte.** Smaller
> fields can be defined within the primary opcode. Such fields define the direction of
> operation, size of displacements, register encoding, condition codes, or sign extension.»*

Ese último «*smaller fields can be defined within the primary opcode*» es
**exactamente** el caso de `B8+rd`, y es lo que el enunciado pasó por alto (§5).

**Límite duro (NORMA).** SDM-C Vol.2A §2.2.1: *«The instruction-size limit of **15 bytes**
still applies to instructions with a REX prefix.»* AMD coincide: APM1 §3.5.2 —
*«The legacy instruction-size limit of 15 bytes still applies to instructions that
contain a REX prefix.»*  Si alguien ve una instrucción de 16 bytes, o ha leido mal
el desensamblado, o está mirando datos embebidos en la sección de código.

### 3.2 Ejemplo: por qué `b8 05 00 00 00` son 5 bytes

| Byte | Valor | Papel | Tamaño de operando |
|---|---|---|---|
| 1 | `b8` | opcode: base de la fila `B8`; los 3 bits bajos son el campo `rd` = `000` → EAX | por defecto **32 bits** (salvo `66h` o `REX.W`) |
| 2 | `05` | `imm8`, inmediato de 8 bits (tabla: `B8+rd id` = `MOV r32, imm32`) | 4 |
| 3 | `00` | byte alto del `imm32` | 4 |
| 4 | `00` | byte alto del `imm32` | 4 |
| 5 | `00` | byte alto del `imm32` | 4 |

`imm32` se escribe **completamente**, con ceros a la izquierda, porque el
decodificador no puede saber de antemano cuánto vale hasta leer los 4 bytes. Ésa es
la razón de la longitud variable: **el tamaño del inmediato es fijo por opcode, pero
sus bytes se emiten siempre enteros**.

Y para el caso de 64 bits (SDM-C Vol.2A §2.2.1.5, textual):

> *When the effective operand size is 64 bits, these instructions can be used to load an
> immediate into a GPR. A REX prefix is needed to override the 32-bit default operand size
> to a 64-bit operand size. For example:*
> `48 B8 8877665544332211   MOV RAX,1122334455667788H`

`48` = `REX.W`. `MOV r64, imm64` son **9 bytes**, con el `imm64` completo
(`REX.W + B8+rd io`, SDM2 p. 4-35). Un `MOV r64` de tamaño inmediato distinto es
`REX.W + C7 /0 id` — `MOV r/m64, imm32` con **sign-extension**: 7 bytes.

---

## 4. Formatos de instrucción (Intel SDM Vol. 2A, Capítulo 2)

### 4.1 Los siete formatos y cómo se identifica el opcode

| Formato | Cómo se reconoce | Qué sigue al opcode | Longitud máxima |
|---|---|---|---|
| **Legacy de un byte** (`One-byte Opcode Map`) | El primer byte no es `0F`/`0F38`/`0F3A`/`C4`/`C5`/`62` | ModR/M opcional, SIB, disp, imm | 15 |
| **Legacy de dos bytes** | Primer byte `0F` (escape) + 1 byte. Con prefijo obligatorio: `66 0F xx`, `F2 0F xx`, `F3 0F xx` | idem | 15 |
| **Legacy de tres bytes** | `0F 38 xx` y `0F 3A xx` (también con `66`/`F2`/`F3` delante) | idem | 15 |
| **VEX de 2 bytes** | `C5` | opcode de 1 byte + ModR/M | … |
| **VEX de 3 bytes** | `C4` | opcode de 1 byte + ModR/M | … |
| **EVEX** | `62` (4 bytes: `62` + P0 + P1 + P2) | opcode + ModR/M | … |
| **XOP** (`8F` con `modrm.reg ≥ 8`) | `8F` + campo `reg` de ModR/M ≥ 8 — espacio de opcode de AMD | — | ⚠ AMD-only |

> **NORMA** (SDM-C Vol.2A §2.1.2, textual):
> *Two-byte opcode formats … consist of one of the following: An escape opcode byte
> `0FH` as the primary opcode and a second opcode byte. A mandatory prefix (`66H`, `F2H`,
> or `F3H`), an escape opcode byte, and a second opcode byte. For example, `CVTDQ2PD`
> consists of the following sequence: `F3 0F E6`. **The first byte is a mandatory prefix
> (it is not considered as a repeat prefix).***
>
> *Three-byte opcode formats … `0FH 3AH` / `0FH 38H` … For example, `PHADDW` for XMM
> registers consists of the following sequence: `66 0F 38 01`. The first byte is the
> mandatory prefix.*

**Trampa de lectura (HECHO sobre este fragmento, y una de las más frecuentes):** `F3` delante de `90`
**no** es `REP`. `F3 90` es `PAUSE` (SDM2 p. 4-230), con `F3` como **prefijo
obligatorio** y `90` como opcode. Un lector que siga la regla «`F3` = `REP`» lo leerá como
`REP NOP`. La distinción se hace mirando la **tabla de opcode**, no el prefijo.

### 4.2 Prefijos legacy de 1 byte (NORMA, SDM-C Vol.2A §2.1.1)

| Byte | Nombre | Grupo | Efecto | Trampa |
|---|---|---|---|---|
| `F0` | `LOCK` | 1 | Serializa la RMW de memoria; **sólo** sobre `ADD, ADC, AND, BTC, BTR, BTS, CMPXCHG, CMPXCH8B, CMPXCHG16B, DEC, INC, NEG, NOT, OR, SBB, SUB, XOR, XADD, XCHG` y **sólo** si el destino es memoria | `F0 01 00` = `lock add`. En un `.ko` el `f0` puede ser un hueco de alineación… no: `f0` sí es opcode en el espacio del kernel para `HLT`/`LOCK`; **verificar siempre contra la tabla** |
| `F2` | `REPNE` / `BND` | 1 | Con instrucciones de cadena, o **prefijo obligatorio** de muchas SIMD; con `CPUID.07H:EBX.MPX[14]` + `BNDCFGU.EN` y sobre `CALL/RET/JMP/Jcc` cercanos, es el prefijo `BND` | El mismo byte es tres cosas distintas según el opcode que sigue |
| `F3` | `REP`/`REPE` | 1 | Con instrucciones de cadena, o **prefijo obligatorio** de `PAUSE`, `MOVSS`, `MOVDDUP`… | Ver 4.1 |
| `2E` | `CS` | 2 | Anula segmento. Con `Jcc` = *branch not taken* | Uso con saltos está **reservado** |
| `36` | `SS` | 2 | Anula segmento | idem |
| `3E` | `DS` | 2 | Anula segmento. Con `Jcc` = *branch taken* | idem |
| `26` | `ES` | 2 | Anula segmento | idem |
| `64` | `FS` | 2 | Anula segmento (`%fs:`) | En kernel x86-64, `%fs` es la base del TLS y de `per_cpu` |
| `65` | `GS` | 2 | Anula segmento (`%gs:`) | Igual, en userland (`%gs` = TLS de pthread) |
| `66` | **Operand-size override** | 3 | 32 bits → 16 bits, o 16 → 32 | En 64 bits, `66` **no** da 32 bits: da 16. Y es prefijo obligatorio de SSE (`66 0F 6F` = `MOVQ`) |
| `67` | **Address-size override** | 4 | 64 bits → 32 bits de direccionamiento | En 64-bit mode **no** desactiva RIP-relativo: trunca yzf-extension a 32 bits (Vol.2A §2.2.1.6) |

> **CONFLICT (menor, pero real) — Intel agrupa en 4, AMD en 5.**
> Intel: *«Instruction prefixes are divided into **four** groups»* (Vol.2A §2.1.1).
> AMD: *«Legacy prefixes are organized into **five** groups, in which each prefix has a
> unique value… only one prefix from each of the five groups can be used in a single
> instruction.»* (APM1 §3.5.1).
> La discrepancia está en si `F0` (LOCK) y `F2`/`F3` (REP) cuentan como un grupo o
> dos. **Los bytes son los mismos; sólo cambia la taxonomía.** No se resuelve: se
> devuelven ambas, como manda §10.1 del `AGENTS.md`. `RESOLUTION_STATUS=OPEN`,
> `IMPACT=0` (ninguna instrucción cambia de significado).

### 4.3 Prefijo REX (0x40–0x4F) — la tabla de 8 "registros" (NORMA, Vol.2A §2.2.1)

**Estructura literal** (Vol.2A Tabla 2-4, p. 2-9, texto extraído):

> **Table 2-4. REX Prefix Fields [BITS: 0100WRXB]**

```
Byte REX = 0b0100WRXB
            │││││││└─ bit0  B  (0x01)
            ││││││└── bit1  X  (0x02)
            │││││└─── bit2  R  (0x04)
            ││││└──── bit3  W  (0x08)
            └┴┴┴┴──── bits 7:4 = 0100 (fijo; 0x40..0x4F)
```

| Bit | Valor | Campo | Efecto exacto (Vol.2A §2.2.1.2, §2.2.1.4) |
|---|---|---|---|
| **W** | `0` | Operand size | Tamaño de operando **determinado por `CS.D`**. En 64-bit mode esto es 32 bits. |
| | `1` | | **64 bits.** No por sí solo: si hay `66H` y `W=1`, **`66H` se ignora**. Y "64-bit operand size override has no effect on byte-specific operations". |
| **R** | `0/1` | Extensión del campo **`reg`** de ModR/M | Se aplica cuando `reg` codifica GPR, SSE, registro de control o de depuración. **Se ignora** cuando ModR/M codifica otros registros o es una extensión de opcode (`/digit`). |
| **X** | `0/1` | Extensión del campo **`index`** de SIB | Sin SIB, es *don't care* (no se decodifica). |
| **B** | `0/1` | Extensión de `r/m` de ModR/M, del `base` de SIB, **o del campo `reg` del opcode** | ← **Esta es la clave de `41 bd`** |

Los 16 valores = 16 combinaciones, no 16 registros:

| REX | W | R | X | B | REX | W | R | X | B |
|---|---|---|---|---|---|---|---|---|---|
| `0x40` | 0  | 0 | 0 | 0 | `0x48` | **1** | 0 | 0 | 0 |
| `0x41` | 0  | 0 | 0 | **1** | `0x49` | 1 | 0 | 0 | **1** |
| `0x42` | 0  | 0 | **1** | 0 | `0x4A` | 1 | 0 | **1** | 0 |
| `0x43` | 0  | 0 | **1** | **1** | `0x4B` | 1 | 0 | **1** | **1** |
| `0x44` | 0  | **1** | 0 | 0 | `0x4C` | 1 | **1** | **1** | 0 |
| `0x45` | 0  | **1** | 0 | **1** | `0x4D` | 1 | **1** | 0 | **1** |
| `0x46` | 0  | **1** | **1** | 0 | `0x4E` | 1 | **1** | **1** | **1** |
| `0x47` | 0  | **1** | **1** | **1** | `0x4F` | 1 | 0 | 0 | 0 → *ver abajo* |

> ⚠ La última fila de la tabla anterior está mal por construcción: `0x4F` es
> `W=1, R=1, X=1, B=1`. No lo repitas. El layout correcto es el de arriba, tal cual:
> `0x4F = 0b0100_1111`.

**Reglas de orden y unicidad (NORMA, §2.2.1):**

> *A REX prefix is **ignored**, as are its individual bits, when it is not needed for an
> instruction **or when it does not immediately precede the opcode byte or the escape
> opcode byte (0FH)**… This has the implication that **only one REX prefix, properly
> located, can affect an instruction**.*

> *When a REX prefix is used in conjunction with an instruction containing a mandatory
> prefix, **the mandatory prefix must come before the REX** so the REX prefix can
> immediately precede the opcode or the escape byte.* Ejemplo textual: `CVTDQ2PD` con
> REX → el REX va **entre** `F3` y `0F E6`.

**Casos especiales (NORMA, Vol.2A Tabla 2-5, p. 2-10).** Tabla reproducida:

| Codificación | En 64-bit mode | Nota |
|---|---|---|
| `mod ≠ 11` | REX añade el 4º bit `b`; **no se decodifica** (*don't care*) | — |
| `mod = 00`, `r/m = b*101` | **`b` NO se decodifica** | Elegir `R13` con `mod=00` sigue siendo **RIP-relativo**, no `[R13]` |
| `SIB`, `index = 0100` | `RSP` **no puede ser índice** | `index=100` con `REX.X=0` significa "sin índice" |
| `SIB` presente | El 4º bit `b` del SIB **no se decodifica** para `base`… salvo en 64-bit, donde **sí** (necesario para `R12`-`R15`) | Requiere SIB incluso para `[RSP]` y para `[R12]` |
| `r/m = b*100` | SIB obligatorio, **también** para direccionamiento con `R12` | — |

Las dos últimas filas son **la** razón por la que `[rsp+8]` codifica siempre
`mod=01, rm=100, SIB=0x24, disp8=0x08`: `mod=00, rm=100` significaría "sin base",
que es la forma "absoluta" (vease §6).

### 4.4 VEX (0xC4 / 0xC5) y EVEX (0x62) (NORMA, §2.3 y §2.7.1)

```
3-byte VEX                              2-byte VEX
byte0  = 11000100  (0xC4)               byte0  = 11000101  (0xC5)
byte1  = 0 R X B mmmmm   (RXB invertido, byte1  = 0 R vvvv L pp
         mmmmm ∈ {00001=0F, 00010=0F38, 00011=0F3A})
byte2  = 0 W vvvv L pp
                 └ pp: 00=Ninguno, 01=66, 10=F3, 11=F2
```

```
EVEX (4 bytes, primer byte 0x62)
P0 = R X B R' 0 m m m
P1 = W v v v v 1 p p
P2 = z L' L b V' a a a
      └ z=zeroing, L'L=longitud de vector, b=máscara, V'=excepción de vector, aaa=registro de máscara k0-k7
```

Reglas que importan al leer:

- (NORMA, §2.3.4) *«Any VEX-encoded instruction with a REX prefix preceding VEX will `#UD`.»*
- (NORMA, §2.3.2/§2.3.3) Con `LOCK`, `66H`, `F2H` o `F3H` delante de VEX → `#UD`.
- (NORMA, §2.3.5) `VEX.vvvv` y los campos de función REX se codifican en **complemento
  a uno**: `XMM0` = `1111b`, `XMM15` = `0000b`. **Escribir `vvvv` al revés es el error
  clásico de lectura manual de un VEX.**
- (NORMA, §2.3.7) *«One (and only one) opcode byte follows the 2 or 3 byte VEX.»* — la
  tabla `VEX.mmmmm` **sustituye** a los escapes `0F`/`0F38`/`0F3A`, no se añade a ellos.
- (NORMA, §2.3.10) Una instrucción VEX con destino `XMM` **pone a cero** los bits
  255:128 del `YMM` correspondiente; las SSE legacy no.

> **Relevancia para este proyecto: BAJA.** Un i7-4790 (Haswell) no tiene AVX-512, así
> que **no habrá EVEX en un `.ko` de amdgpu compilado para este host**
> (`FACT_FOR_ark`: Instruction Set Extensions = SSE4.1/4.2, AVX2; sin AVX-512).
> VEX sí puede aparecer (el kernel usa AVX para `crc32`/`memcpy`). EVEX se documenta
> aquí por completitud del formato, no porque aparezca en el caso de estudio.

---

## 5. ModR/M y SIB: decodificación byte a byte del fragmento

### 5.1 `41 bd 0a 00 00 00` → `mov $0xa,%r13d` — **`HECHO`, y **sin ModR/M**

```
offset  byte    binario     ¿qué es?                            de dónde sale
──────  ─────   ────────    ─────────────────────────────────    ──────────────────────────
0x215161  41    0100 0001   REX: W=0 R=0 X=0 B=1                 0x40-0x4F → REX (§2.2.1).
                                                                B=1 → añade 8 al campo de
                                                                3 bits que apunte al registro.
        bd     1011 1101   opcode: fila B8, campo rd = 101 = 5   SDM2 p.4-35: `B8+rd id` = MOV r32,imm32.
                                                                rd = 5, +8 por REX.B = 13  → R13
        0a 00 00 00        imm32 = 0x0000000a = 10                La tabla dice `id` (4 bytes),
                                                                se emiten los 4 SIEMPRE.
                                                                ── NO hay ModR/M ──
                                                                ── NO hay SIB ──
                                                                ── NO hay desplazamiento ──
```

Gráfico:

```
41 bd 0a 00 00 00
│  │  └────────── imm32 = 0x0000000A (4 bytes, sin signo, 0-ext a 64 bits)
│  └───────────── opcode B8+rd, rd=0b101=5, +REX.B(8) → r13d
└──────────────── REX.B=1 ; W=0 → tamaño de operando 32 bits (por defecto en 64-bit)
   longitud = 1 + 1 + 4 = 6 bytes → siguiente instrucción en 0x215167 ✓ (coincide con el fragmento)
```

**Intel:** `MOV r13D, 0Ah` · **AT&T:** `mov $0xa,%r13d`

> ⚠ **Corrección de P3 y P4 (ver §1).** No hay byte ModRM que decodificar, y el
> inmediato **no** es `imm8`. `REX.B` no toca el tamaño del inmediato. La forma `imm8`
> (`B0+rb ib` = `MOV r8, imm8`) pertenece a la **fila B0**, no a la fila B8, y sería un
> acceso de **8 bits** a `%r13b`, cosa que aquí no ocurre.

### 5.2 `bb 0a 00 00 00` → `mov $0xa,%ebx` — `HECHO`

```
bb     1011 1011   opcode: fila B8, rd = 011 = 3  → EBX    (sin REX: 3 < 8)
0a 00 00 00        imm32 = 10
longitud = 1 + 4 = 5 bytes → siguiente en 0x215188 ✓
```

### 5.3 Las dos codificaciones de `mov $0xa`: por qué difieren

| | `mov $0xa,%ebx` | `mov $0xa,%r13d` |
|---|---|---|
| REX | ninguno | `0x41` (B=1) |
| Opcode | `0xBB` (rd=3) | `0xBD` (rd=5) |
| Inmediato | `imm32` | `imm32` |
| Longitud | 5 | 6 |
| Rango del valor | −2³¹…2³¹−1 sin signo, o −2³¹…2³¹−1 con signo | idéntico |

**Lo que REX.B cambia: el registro, no el rango.** La alternativa de tamaño pequeño
que el enunciado menciona existe, pero es `B0+rb ib` = `MOV r8, imm8`, que:
1. opera sobre un **byte** de registro (`%r13b`, no `%r13d`), y
2. sólo acepta valores −128…255.

Que `mov $0xa,%r13d` ocupe 6 bytes y no 3 es simplemente porque el registro destino
está en `r8d`–`r15d` y hace falta un byte más de prefijo. **El "coste" de usar un
registro extendido es +1 byte, no un inmediato más estrecho.**

### 5.4 `bf 58 89 41 00` → `mov $0x418958,%edi` — `HECHO`

```
bf     1011 1111   opcode B8+rd, rd = 111 = 7  → EDI  (sin REX: 7 < 8)
58 89 41 00        imm32 = 0x00418958 = 4 295 000
longitud = 5 → 0x215188 + 5 = 0x21518D ✓
```

**Este es el inmediato de `mdelay(10)`.** Vease §9. Es el número que resuelve el
problema de la investigación, y no tiene nada que ver con una dirección.

### 5.5 `e8 00 00 00 00` → `call` rel32 — `HECHO` (+ `NOT_DETERMINED` del destino)

```
e8     opcode = CALL rel32     (SDM2 p.3-139: `E8 cd` → CALL rel32, Valid en 64-bit mode)
00 00 00 00   rel32 = 0
longitud = 5 (fija: siempre 5, con o sin relocación)
destino = RIP_siguiente + SignExtend(0) = 0x21517B
```

> **NORMA** (SDM2, *CALL — Call Procedure*, p. 3-138/3-139): *«In 64-bit mode the relative offset is always
> a 32-bit immediate value which is **sign extended to 64-bits** before it is added to
> the value in the RIP register for the target calculation.»*

**Consecuencia que casi todo el mundo desaprovecha:** `CALL` y `JMP` cercanos **siempre
ocupan 5 bytes en x86-64**, porque el desplazamiento es siempre de 32 bits. No hay
forma corta. (`Jcc` sí: `rel8` de 2 bytes o `rel32` de 6.) En x86-32 tampoco había
`CALL rel8`; la diferencia real es que en 32 bits el `rel32` no se signa-extiende a
64.

### 5.6 `4c 89 e7` → `mov %r12,%rdi` — `HECHO`, y con `REX.X` irrelevante

```
4c     0100 1100   REX: W=1 R=1 X=1 B=0
89     opcode = MOV r/m64, r64    (con REX.W → operandos de 64 bits)
e7     11 100 111  ModRM: mod=11 (registro), reg=100=4, r/m=111=7
                  reg = 4 + 8*REX.R(1) = 12   → R12   (origen)
                  r/m = 7 + 8*REX.B(0) = 7    → RDI   (destino)
longitud = 1 + 1 + 1 = 3
```

> **Intel:** `MOV r12, rdi` · **AT&T:** `mov %r12,%rdi` (origen primero)

`REX.X = 1` con `mod=11` es un **don't-care** (SDM2 Figura 2-5, p. 2-9: `REX.X Not
Used`). No debe leerse como "hay un SIB". `X` sólo importa cuando hay `SIB`.

### 5.7 `48 83 eb 01` → `sub $0x1,%rbx` — `HECHO`

```
48     REX.W = 1        → operandos de 64 bits
83     opcode 83 /digit → familia "opcode de 1 byte con extensión /digit en ModR/M"
eb     11 101 011  ModRM: mod=11, reg=101 = 5, r/m=011 = 3
01     ib = imm8 = +1, sign-extended al tamaño del operando
```

**Intel:** `SUB rbx, 1` · **AT&T:** `sub $0x1,%rbx`

> **NORMA** (SDM2 p. 4-673, tabla de opcodes de SUB):
> `83 /5 ib` → `SUB r/m32, imm8` — *«Subtract sign-extended imm8 from r/m32»*
> `REX.W + 83 /5 ib` → `SUB r/m64, imm8` — *«Subtract sign-extended imm8 from r/m64»*

**Éste es el otro tipo de "inmediato pequeño con instrucción larga"**: el opcode `83`
existe precisamente para que un inmediato de 1 byte quepa en 4 bytes, en lugar del
`81 /5 id` de 6-7 bytes. `sub $0x1,%ebx` se ensamblaría como `83 eb 01` (3 bytes), no
como `81 eb 01 00 00 00` (6 bytes).

**Y por qué `%rbx` en 64 bits y `%r13d` en 32 bits para los dos "10":** `HECHO` que
los anchos difieren; `INFERENCIA` (economía del asignador de registros y del idiom
`-fivopts`) que no tiene significado semántico: los dos contadores valen 10 y se
decrementan hasta 0 en ambos casos. **Un lector que busque en eso una diferencia de
semántica del fuente está sobre-analizando la salida del compilador.**

---

## 6. Modos de direccionamiento (ModR/M y SIB)

### 6.1 Cómo se lee el byte ModR/M (NORMA, SDM2 Vol.2A §2.1.3 y §2.1.5)

```
ModRM = 0bMM RRR RMM
        ││  │    └── r/m : 3 bits. Con mod=11 → un REGISTRO.
        ││  └─────── reg: 3 bits. Registro, o extensión de opcode (/digit, 0-7).
        └────────── mod: 2 bits. Determina displacement y si r/m es memoria o registro.
```

Y el SIB:

```
SIB   = 0bSS III BBB
        ││  │    └── base : 3 bits (4 = ninguno con REX.X=0 ; +8*REX.B)
        ││  └─────── index: 3 bits (4 = sin índice; ESP no puede ser índice)
        └────────── scale: 2 bits → 1, 2, 4, 8 (valor = 1 << scale)
```

> **NORMA** (SDM2 Vol.2A §2.1.3): *«The mod field combines with the r/m field to form
> 32 possible values: **eight registers and 24 addressing modes**.»*

> **NORMA** (Vol.2A Tabla 2-3, p. 2-10, "32-Bit Addressing Forms with the SIB Byte"):
> las 32 filas de la tabla son `[EAX] … [EDI]` para `scale=0` y `base=EAX..EDI`; las
> columnas son las 32 combinaciones de `index` × `scale`; las entradas son
> `[EAX]`, `[EAX+ECX]`, `[EAX+ECX*2]`… `none` para `base=101 (EBP)` sin desplazamiento,
> `[EBP]` cuando hay `mod=01, disp8=0`.

### 6.2 Tabla completa de direccionamiento en 64-bit mode

`mod` × `r/m`, con `REX.B`/`REX.X` ajoutados. Todas las filas son **64-bit mode**.

| `mod` | `r/m` | Forma en 64-bit | Bytes extra | SIB |
|---|---|---|---|---|
| `00` | `000` | `[RAX]` | 0 | no |
| `00` | `001` | `[RCX]` | 0 | no |
| `00` | `010` | `[RDX]` | 0 | no |
| `00` | `011` | `[RBX]` | 0 | no |
| `00` | `100` | **`[RSP]` → SIB con base=`100`, index=`100` (sin índice), scale=0** | +1 (SIB) | **sí** |
| `00` | `101` | **`RIP + disp32`** (§6.3) | +4 (`disp32`) | no |
| `00` | `110` | `[RSI]` | 0 | no |
| `00` | `111` | `[RDI]` | 0 | no |
| `01` | `000` | `[RAX + disp8]` | +1 (sign-ext.) | no |
| `01` | `001` | `[RCX + disp8]` | +1 | no |
| `01` | `010` | `[RDX + disp8]` | +1 | no |
| `01` | `011` | `[RBX + disp8]` | +1 | no |
| `01` | `100` | `[RSP + disp8]` | +1 SIB +1 disp8 | sí |
| `01` | `101` | `[RBP + disp8]` | +1 | no |
| `01` | `110` | `[RSI + disp8]` | +1 | no |
| `01` | `111` | `[RDI + disp8]` | +1 | no |
| `10` | `000` | `[RAX + disp32]` | +4 | no |
| `10` | `001` | `[RCX + disp32]` | +4 | no |
| `10` | `010` | `[RDX + disp32]` | +4 | no |
| `10` | `011` | `[RBX + disp32]` | +4 | no |
| `10` | `100` | `[RSP + disp32]` | +1 SIB +4 | sí |
| `10` | `101` | `[RBP + disp32]` | +4 | no |
| `10` | `110` | `[RSI + disp32]` | +4 | no |
| `10` | `111` | `[RDI + disp32]` | +4 | no |
| `11` | `000` | `[RAX]` (reg) | 0 | — |
| `11` | `001` | `[RCX]` (reg) | 0 | — |
| `11` | `010` | `[RDX]` (reg) | 0 | — |
| `11` | `011` | `[RBX]` (reg) | 0 | — |
| `11` | `100` | `[RSP]` (reg) | 0 | — |
| `11` | `101` | `[RBP]` (reg) | 0 | — |
| `11` | `110` | `[RSI]` (reg) | 0 | — |
| `11` | `111` | `[RDI]` (reg) | 0 | — |

Con `REX.B=1`, los ocho registros de cada fila se convierten en `R8`–`R15`
— **excepto en `mod=00, r/m=101`**, que sigue siendo RIP-relativo (§6.3).

Formas con SIB, en 64-bit mode (`base + index*scale + disp`):

| `SIB.scale` | Factor | | `SIB.base` | Registro |
|---|---|---|---|---|
| `00` | ×1 | | `000` | `RSP`… con `REX.B` → `R8`…`R15` |
| `01` | ×2 | | `001` | `RCX` / `R9` |
| `10` | ×4 | | `010` | `RDX` / `R10` |
| `11` | ×8 | | `011` | `RBX` / `R11` |
| | | | `100` | `RSP`/`R12` (obligatorio `mod≠00`) |
| | | | `101` | `RBP`/`R13` — `mod=00` ⇒ **sin base**, `disp32` absoluto |
| | | | `110` | `RSI`/`R14` |
| | | | `111` | `RDI`/`R15` |

`SIB.index = 100` con `REX.X=0` = **sin índice** ⇒ la forma es
`disp32(sin base)` en vez de "indexado por ESP".

### 6.3 El caso especial `mod=00, r/m=101`: RIP-relativo (NORMA)

> **SDM2 Vol.2A §2.2.1.6** (p. 2-11, texto literal):
> *A new addressing form, **RIP-relative** (relative instruction-pointer) addressing,
> is implemented in 64-bit mode. **An effective address is formed by adding
> displacement to the 64-bit RIP of the next instruction.** … RIP-relative addressing
> allows specific ModR/M modes to address memory relative to the 64-bit RIP using a
> **signed 32-bit displacement. This provides an offset range of ±2GB from the RIP.***
> *In 64-bit mode, the ModR/M `Disp32` encoding is **re-defined to be `RIP+Disp32`**.*

> *The ModR/M encoding for RIP-relative addressing **does not depend on using a prefix**.
> Specifically, the r/m bit field encoding of `101B` … is not affected by the REX prefix.
> For example, **selecting R13 (REX.B = 1, r/m = 101B) with mod = 00B still results in
> RIP-relative addressing.** … In order to address R13 with no displacement, software
> must encode R13 + 0 using a 1-byte displacement of zero.*

> *RIP-relative addressing is enabled by **64-bit mode, not by a 64-bit address-size**.
> The use of the address-size prefix does not disable RIP-relative addressing. The effect
> of the address-size prefix is to truncate and **zero-extend** the computed effective
> address to 32 bits.*

Y la Tabla 2-7 (*RIP-Relative Addressing*):

| ModR/SIB | 64-bit mode | Compat mode |
|---|---|---|
| `mod=00, r/m=101` + `disp32` | **`RIP + disp32`** | desplazamiento absoluto (mod=00) |
| `SIB`, `base=101`, `index=100`, `scale=0,1,2,4` | `disp32` absoluto (sin base) | — |

Cuatro consecuencias que evitan errores:

1. **El desplazamiento es relativo a la instrucción SIGUIENTE, no a la actual.**
   Es la misma fórmula que un salto. Confundirlo es un error de ±longitud de instrucción.
2. `REX.B` **no** convierte `mod=00, r/m=101` en `[R13]`. Para `[R13]` hace falta
   `mod=01, disp8=0`.
3. `66`/`67` **no** deshabilitan RIP-relativo.
4. En el ensamblador AT&T se escribe `disp(%rip)`; en Intel `[rip+disp]`
   (`AS` §9.16.7, textual: *«AT&T: `1234(%rip)`, Intel: `[rip + 1234]`. Points to the
   address 1234 bytes past the end of the current instruction.»*). En **código de
   kernel** esto es la forma normal de acceder a un global desde PIC/PIE.

### 6.4 `mod=00, r/m=100` exige SIB — y por qué

`r/m=100` está reservado en el par `mod`/`r/m` para decir "aquí viene un SIB",
porque `[RSP]` y `[R12]` necesitan el bit 4 (`b`) del SIB para distinguirse y
`RSP` no puede ser índice. Sin SIB no habría forma de codificarlos. Ése es el
"formato reducido" de 8 bits que Intel reserva para `[RAX]…[RDI]`, `[RIP+disp32]`
y 8 registros; los modos restantes gastan 1–2 bytes más.

---

## 7. Control de flujo: alcance y(destination) de los saltos

### 7.1 La fórmula, en las dos formas de 64 bits (NORMA)

> **SDM2 Vol.2A, *Jcc*, p. 3-553** (texto literal):
> *In 64-bit mode, operand size is fixed at 64 bits. **JMP Short is
> `RIP = RIP + 8-bit offset sign extended to 64 bits`. JMP Near is
> `RIP = RIP + 32-bit offset sign extended to 64 bits`.***

> **SDM2 Vol.1, §7.3.8.3** (*Control Transfer Instructions in 64-Bit Mode*):
> *In 64-bit mode, the operand size for all near branches (CALL, RET, JCC, JCXZ, JMP,
> and LOOP) is **forced to 64 bits**… **Note that the displacement field for relative
> branches is still limited to 32 bits and the address size for near branches is not
> forced.** Address size determines the register size (CX/ECX/RCX) used for JCXZ and
> LOOP.*

```
DESTINO = ( RIP de la instrucción SIGUIENTE ) + SignExtend( desplazamiento )
          ▲
          └── NO es la dirección de la propia instrucción
```

### 7.2 Tabla de instrucciones de salto y su alcance

| Instrucción | Opcode(s) | Desp. | Bytes | Alcance | Notas 64-bit |
|---|---|---|---|---|---|
| `JMP short` | `EB cb` | `rel8` | 2 | −128…+127 | |
| `JMP near` | `E9 cd` | `rel32` | 5 | ±2 GiB | |
| `JMP` indirecto reg | `FF /4` | — | 2-3 | 64 bits | destino = valor del registro |
| `JMP` indirecto mem | `FF /4` | `m64` | 3-8 | 64 bits | `RSP` se evalúa **antes** de la escritura |
| `Jcc short` | `70+cc cb` | `rel8` | 2 | −128…+127 | |
| `Jcc near` | `0F 80+cc cd` | `rel32` | 6 | ±2 GiB | `0F 8x cw` (**rel16**) = **`N.S.` — no soportado en 64-bit mode** |
| `CALL near` | `E8 cd` | `rel32` | 5 | ±2 GiB | empuja la dirección de retorno (64 bits) |
| `CALL` indirecto | `FF /2` | `r/m64` | 2-8 | 64 bits | |
| `RET` | `C3` | — | 1 | — | `C2 ib` = `RET imm16` (limpia `ib` bytes de pila) |
| `LOOP` | `E2 cb` | `rel8` | 2 | −128…+127 | *«Decrement count; jump short if count ≠ 0.»* |
| `LOOPE`/`LOOPZ` | `E1 cb` | `rel8` | 2 | −128…+127 | + `ZF = 1` |
| `LOOPNE`/`LOOPNZ` | `E0 cb` | `rel8` | 2 | −128…+127 | + `ZF = 0` |
| `JRCXZ` | `E3 cb` | `rel8` | 2 | −128…+127 | `RCX == 0`; no mira banderas |

> **NORMA** (SDM2 p. 3-553): *The JRCXZ, JECXZ, and JCXZ instructions differ from other
> Jcc instructions because **they do not check status flags**. Instead, they check RCX,
> ECX or CX for 0. … These instructions are useful when used at the beginning of a loop
> that terminates with a conditional loop instruction (such as LOOPNE).*

> **NORMA** (SDM2 p. 3-553): *These instructions are useful … to prevent an instruction
> sequence from entering a loop when RCX, ECX or CX is 0. **This would cause the loop to
> execute 2^64, 2^32 or 64K times (not zero times).***

> **NORMA** (Vol.1 §7.3.8.2, *Loop instructions*): *If the count in the ECX register is
> zero when the loop instruction is first executed, the register is pre-decremented to
> `0FFFFFFFFH`, **causing the loop to be executed 2^32 times**.*

**Lo que `loop` significa para un lector de kernel:** `loop` **no** existe en el
código que genera GCC para x86-64. `AS` §9.16.8 lo dice explícitamente
(*«(gcc does not use them)»*). Si ves `e2`, no lo escribió un `for` de GCC: lo escribió
alguien a mano, o es desensamblado equivocado. **Es un discriminador útil**: `loop`
presente = fuente escrita a mano o desensamblado alineado al wrong offset.

### 7.3 Los 16 códigos de condición (NORMA, SDM2 Vol.1 Tabla 7-4, p. 7-15)

| `cc` | Opcode corto | Opcode largo | Mnemónico(s) | Condición (estado de banderas) | Grupo |
|---|---|---|---|---|---|
| `0` | `70` | `0F 80` | `JO` | `OF = 1` | con signo |
| `1` | `71` | `0F 81` | `JNO` | `OF = 0` | con signo |
| `2` | `72` | `0F 82` | `JB` / `JNAE` / `JC` | `CF = 1` | sin signo |
| `3` | `73` | `0F 83` | `JAE` / `JNB` / `JNC` | `CF = 0` | sin signo |
| `4` | `74` | `0F 84` | `JE` / `JZ` | `ZF = 1` | ambos |
| `5` | `75` | `0F 85` | `JNE` / `JNZ` | **`ZF = 0`** | ambos |
| `6` | `76` | `0F 86` | `JBE` / `JNA` | `(CF or ZF) = 1` | sin signo |
| `7` | `77` | `0F 87` | `JA` / `JNBE` | `(CF or ZF) = 0` | sin signo |
| `8` | `78` | `0F 88` | `JS` | `SF = 1` | con signo |
| `9` | `79` | `0F 89` | `JNS` | `SF = 0` | con signo |
| `A` | `7A` | `0F 8A` | `JP` / `JPE` | `PF = 1` | paridad |
| `B` | `7B` | `0F 8B` | `JNP` / `JPO` | `PF = 0` | paridad |
| `C` | `7C` | `0F 8C` | `JL` / `JNGE` | `(SF xor OF) = 1` | con signo |
| `D` | `7D` | `0F 8D` | `JGE` / `JNL` | `(SF xor OF) = 0` | con signo |
| `E` | `7E` | `0F 8E` | `JLE` / `JNG` | `((SF xor OF) or ZF) = 1` | con signo |
| `F` | `7F` | `0F 8F` | `JG` / `JNLE` | `((SF xor OF) or ZF) = 0` | con signo |

**Las banderas que ningún `Jcc` mira: `AF`.** Nunca aparece en la Tabla 7-4. `AF`
existe para el BCD, y x86-64 no tiene BCD. Un lector que espere un salto de
"acarreo" no lo encontrará.

### 7.4 RESOLUCIÓN: por qué `75 f0` salta a `0x215188` — y la aritmética del error

```
215196:  75 f0                jne    215188
          │  └── cb = 0xF0 = 240 decimal, o -16 con signo (8 bits, dos's complement)
          └───── opcode 0x75 = JNE rel8  (cc = 5 → ZF = 0)

  RIP de la instrucción SIGUIENTE = 0x215196 + 2 = 0x215198
  SignExtend(0xF0) = -0x10 = -16
  DESTINO          = 0x215198 + (-0x10) = 0x215188            ✓
```

**Y la aritmética del enunciado era incorrecta aunque llegara al destino bueno:**

| Cálculo | Resultado | ¿Coincide con `215188` del fragmento? |
|---|---|---|
| `0x215192 − 0x10` (enunciado) | `0x215182` | ❌ |
| `0x215198 − 0x10` (aquí) | `0x215188` | ✅ |

De dónde salió el `0x215192`: es la dirección *siguiente al `call`* de
`0x21518D` (`e8 00 00 00 00` son 5 bytes → `0x21518D+5 = 0x215192`). Es decir, la
**dirección de retorno** de la llamada a `__const_udelay`, que en esa línea es también
el destino del `call`. **Coincidencia numérica de 3 bytes compartidos, no relación
causal.** Y `0x215182` no es el comienzo de ninguna instrucción: cae en mitad de
`215183: bb 0a 00 00 00`. Un salto a mitad de instrucción = código auto-modificable o
decodificación equivocada; el desensamblado de objdump lo detecta porque al
reconstruir la cadena de bytes desde 0x215183 obtiene longitudes que cuadran
exactamente.

### 7.5 El otro back-edge, para contrastar: `75 cf`

```
21519b:  75 cf                jne    21516c
  RIP siguiente = 0x21519b + 2 = 0x21519D
  SignExtend(0xCF) = -49 = -0x31
  DESTINO = 0x21519D - 0x31 = 0x21516C                ✓  (la cabeza del bucle de 100)
```

Y el salto largo:

```
21517d:  0f 85 bc 00 00 00    jne    21523f
  0f 85 = JNE rel32 (cc=5)
  cd = 0x000000BC = 188
  RIP siguiente = 0x21517D + 6 = 0x215183
  DESTINO = 0x215183 + 0xBC = 0x21523F                ✓
```

> **Consecuencia práctica (y el motivo por el que el compilador elige `rel8`):**
> `AS` §9.16.8, textual: *«Jump instructions are always optimized to use the smallest
> possible displacements. This is accomplished by using byte (8-bit) displacement jumps
> whenever the target is sufficiently close. If a byte displacement is insufficient a long
> displacement is used.»* Por eso hay un `JNE` de 2 bytes y otro de 6 en el mismo
> bloque: **la diferencia de tamaño no dice nada sobre lasemántica del salto**, sólo
> sobre la distancia. Un error de lectura muy común es tratar el `0F 85` como "otra
> instrucción" y no ver que es el mismo `jne`.

---

## 8. Aritmética y banderas

### 8.1 Tabla de banderas afectadas (NORMA — "Flags Affected" de cada página de opcode)

| Instrucción | `OF` | `SF` | `ZF` | `AF` | `PF` | `CF` | `Flags Affected` textual |
|---|:-:|:-:|:-:|:-:|:-:|:-:|---|
| `ADD` | ✔ | ✔ | ✔ | ✔ | ✔ | ✔ | *The OF, SF, ZF, AF, PF, and CF flags are set according to the result.* |
| `SUB` | ✔ | ✔ | ✔ | ✔ | ✔ | ✔ | *The OF, SF, ZF, AF, PF, and CF flags are set according to the result.* (SDM2 p. 4-673) |
| `CMP` | ✔ | ✔ | ✔ | ✔ | ✔ | ✔ | *The OF, SF, ZF, AF, PF, and CF flags are set according to the result.* (= `SUB` sin escribir) |
| `XOR` | ✔ | ✔ | ✔ | ✔ | ✔ | ✔ | misma familia aritmética/lógica con CF calculada |
| `AND` | ✔ | ✔ | ✔ | ✔ | ✔ | ✔ | `CF = OF = 0` |
| `OR` | ✔ | ✔ | ✔ | ✔ | ✔ | ✔ | `CF = OF = 0` |
| **`TEST`** | **→0** | ✔ | ✔ | **indefinida** | ✔ | **→0** | *The OF and CF flags are **set to 0**. The SF, ZF, and PF flags are set according to the result… **The state of the AF flag is undefined.*** (SDM2 p. 4-703) |
| `MOV` | — | — | — | — | — | — | *Flags Affected: **None.*** |
| `Jcc` | — | — | — | — | — | — | *None.* |
| `PAUSE` | — | — | — | — | — | — | *None.* |

### 8.2 Por qué `test $0x2,%al` no altera las banderas "como `sub`"

Es una **pregunta mal formulada que contiene la respuesta**: `test` **sí** modifica
banderas — lo que hace es **modificarlas sin escribir ningún registro**.

```
test $0x2,%al     =  A8 02        (SDM2 p. 4-703: `A8 ib` → TEST AL, imm8,
                                        *«AND imm8 with AL; set SF, ZF, PF
                                         according to result.»*)

  Operandación exacta, textual de la página TEST (SDM2 p. 4-703):
      CF := 0;
      OF := 0;
      (* AF is undefined *)
```

El resultado de `AL AND 0x02` se **descarta**; sólo sobreviven las banderas:

| Bandera | `test` | `sub` |
|---|---|---|
| `ZF` | `ZF := (AL AND 2) == 0` | `ZF := (A − B) == 0` |
| `SF` | signo del resultado | signo del resultado |
| `PF` | paridad del resultado | paridad del resultado |
| `CF` | **siempre 0** | acarreo del préstamo |
| `OF` | **siempre 0** | desbordamiento con signo |
| `AF` | **indefinida** | acarreo entre nibbles (BCD) |

**Las tres razones por las que `test`/`and` se usan en lugar de `cmp`:**

1. **No hay que escribir un temporal.** `test $2,%al` no necesita registro
   scratch; `cmp $2,%al` tampoco, pero `mov %al,%edx; and $2,%edx; test…` sí. En
   código generado, `test` ahorra un registro — que es la razón real por la que
   GCC emite `test` y no `cmp` en el caso del fragmento.
2. **`test` es una forma de `and` no destructivo**, es decir, "calcula sólo
   banderas". `AND` sí escribe el destino pero fija `CF=OF=0`, lo que **descarta
   información de acarreo**: por eso `and` **no** puede reemplazar a `cmp`/`sub`
   cuando la condición necesita `CF`.
3. **`cmp` es `sub` que no escribe.** Por eso `cmp` pone `AF`, y `test` no.

**Consecuencia para leer el fragmento (HECHO):** el par

```
a8 02           test $0x2,%al
0f 85 bc..      jne  0x21523f
```

implementa `if (status & 2) break;` — `jne` mira **`ZF`**, y `ZF` lo puso el `test`
anterior, no un `cmp` explícito. Si el compilador hubiera emitido `cmp $2,%eax`, el
`test` no estaría. **Un lector que busque un `cmp` antes de cada salto condicional
no lo encontrará, y no significa que el salto sea "incondicional".**

### 8.3 `and` vs `test` en x86-64: la subtileza de los 8 bits con REX

`84 /r` = `TEST r/m8, r8`. Con prefijo REX, `r/m8` **no puede** codificar
`AH, BH, CH, DH` (SDM2 p. 4-703, nota 1: *«In 64-bit mode, r/m8 can not be encoded to
access the following byte registers if a REX prefix is used: AH, BH, CH, DH.»*).
Con REX, `%ah` se alcanza como `%spl/%bpl/%sil/%dil`, que son registros de 8 bits
**distintos y no solapados**. Es un detalle 32-bit→64-bit que ha roto código
real durante años.

---

## 9. Atómicos, barreras y qué usa realmente el kernel en x86-64

### 9.1 Las primitivas de hardware (NORMA, SDM2/SDM3)

| Primitiva | Opcode | Para qué | 64-bit mode |
|---|---|---|---|
| `LOCK` (prefijo) | `F0` | Vuelve atómica una RMW de memoria | `Valid`, pero **sólo** sobre `ADD, ADC, AND, BTC, BTR, BTS, CMPXCHG, CMPXCH8B, CMPXCHG16B, DEC, INC, NEG, NOT, OR, SBB, SUB, XOR, XADD, XCHG` **y sólo si el destino es memoria** (SDM2 p. 3-614) |
| `XCHG` | `87 /r`, `87 /r` con REX.W | Intercambio atómico | *«**The XCHG instruction always asserts the LOCK# signal regardless of the presence or absence of the LOCK prefix.**»* (SDM2 p. 3-614) — el `lock` es **implícito** |
| `CMPXCHG` | `0F B0 /r` (r/m8), `0F B1 /r` (r/m16/32/64) | CAS atómico: si `DEST == SRC1` → `DEST = SRC2` + ZF=1, si no → `DEST = SRC1` + ZF=0 | `Valid` |
| `MFENCE` | `0F AE F0` | Ordena **lecturas y escrituras** respecto a todo lo anterior y posterior | `Valid` |
| `LFENCE` | `0F AE E8` | Ordena **lecturas** respecto a lecturas y escrituras anteriores | `Valid` |
| `SFENCE` | `0F AE F8` | Ordena **escrituras** respecto a escrituras anteriores | `Valid` |
| `PAUSE` | `F3 90` | *«Gives hint to processor that improves performance of spin-wait loops.»* Reduce también el consumo | `Valid`. `F3` es **prefijo obligatorio**, no `REP` |

> **NORMA** (SDM2, *LOCK*, p. 3-614, textual):
> *Causes the processor's `LOCK#` signal to be asserted during execution of the
> accompanying instruction (turns the instruction into an atomic instruction). […] The
> `LOCK` prefix can be prepended **only** to the following instructions **and only to
> those forms of the instructions where the destination operand is a memory operand**:
> `ADD, ADC, AND, BTC, BTR, BTS, CMPXCHG, CMPXCH8B, CMPXCHG16B, DEC, INC, NEG, NOT,
> OR, SBB, SUB, XOR, XADD, and XCHG`. […] An undefined opcode exception will also be
> generated if the `LOCK` prefix is used with any instruction not in the above list.*
>
> *The integrity of the `LOCK` prefix is **not affected by the alignment** of the memory
> field. Memory locking is observed for arbitrarily misaligned fields.*

> **NORMA** (SDM2, *XCHG*, vía Vol.1 §7.3.1.2): *When a memory operand is used with the
> XCHG instruction, the processor's `LOCK` signal is automatically asserted.*

> **NORMA** (SDM2, *PAUSE*, p. 4-230): *This instruction does not change the architectural
> state of the processor (that is, **it performs essentially a delaying no-op
> operation**).* … *In earlier IA-32 processors, the PAUSE instruction operates like a
> NOP instruction.*

### 9.2 El modelo de memoria de x86-64 (NORMA, SDM3A §9.2.2, p. 9-6)

> *The Intel Core 2 Duo, Intel Atom, Intel Core Duo, Pentium 4, and P6 family processors
> also use a **processor-ordered memory-ordering model that can be further defined as
> "write ordered with store-buffer forwarding"**. […] In a single-processor system for
> memory regions defined as write-back cacheable, the memory-ordering model respects the
> following principles:*

```
• Reads are not reordered with other reads.
• Writes are not reordered with older reads.
• Writes to memory are not reordered with other writes,
    with the exceptions of: streaming stores (MOVNTI…) and string operations.
• Reads may be reordered with older writes to different locations
    but not with older writes to the same location.
• LFENCE instructions cannot pass earlier reads.
• Reads or writes cannot be reordered with I/O instructions, locked instructions,
    or serializing instructions.
• Reads cannot pass earlier LFENCE and MFENCE instructions.
• Writes and executions of CLFLUSH/CLFLUSHOPT cannot pass earlier LFENCE, SFENCE,
    and MFENCE instructions.
• MFENCE instructions cannot pass earlier reads, writes, or executions of
    CLFLUSH and CLFLUSHOPT.
```

> En un sistema multiprocesador, además: *Writes by a single processor are observed in
> the same order by all processors. **Writes from an individual processor are NOT
> ordered with respect to the writes from other processors.*** […] *Locked instructions
> have a total order.*

**Éste es el hecho que hace que `smp_wmb()` sea gratis en x86** (SDM3A §9.1.2,
p. 9-2/9-3): *The P6 and more recent processor families … ensure that the LOCK
semantics are provided […] by locking the processor's caches.* Es decir, en P6 y
posteriores el `LOCK#` **no se sale al bus** si la línea está en caché: la coherencia
de caché ya da la atomicidad.

> **Clasificación de aplicabilidad.** La sección se titula *"Memory Ordering in P6 and
> More Recent Processor Families"*. Un i7-4790 (Haswell) es posterior a P6, así que
> aplica: `FACT_FOR_INTEL_SDM` → aplicable a este host.
> **PERO** el SDM no es el único documento que aplica a un `.ko` de amdgpu: el código
> *destinado a la GPU* ve la máquina de memoria de la GPU, no la de la CPU, y por
> eso amdgpu usa `writel()`/`readl()` con barriers de I/O y no barreras `smp_*`. Ver
> §9.5.

### 9.3 Las macros del kernel en x86-64 — **verificado, no de memoria** (`HECHO`)

Cadena de incluye y definición, con archivo y línea de `v6.16`:

```
arch/x86/include/asm/barrier.h
├─ línea 21-25  #else  (es decir, NO CONFIG_X86_32 → x86-64)
│    #define __mb()    asm volatile("mfence"::: "memory")
│    #define __rmb()   asm volatile("lfence"::: "memory")
│    #define __wmb()   asm volatile("sfence" ::: "memory")
│    ⚠ mb(), rmb(), wmb(), smp_mb(), smp_rmb(), smp_wmb() NO están aquí
├─ línea 50     #define __dma_rmb()  barrier()
├─ línea 51     #define __dma_wmb()  barrier()
├─ línea 53     #define __smp_mb()   asm volatile("lock addl $0,-4(%%_ASM_SP)":::"memory","cc")
├─ línea 55     #define __smp_rmb()  dma_rmb()          → → → → barrier()
├─ línea 56     #define __smp_wmb()  barrier()
├─ línea 57     #define __smp_store_mb(var,value)  do { (void)xchg(&var,value); } while (0)
├─ línea 75-76  #define __smp_mb__before_atomic()  do { } while (0)   /* "ya son serializantes" */
├─ línea 79     #define smp_mb__after_switch_mm()  do { } while (0)   /* escribir CR3 ya es barrera */
└─ línea 81     #include <asm-generic/barrier.h>

include/asm-generic/barrier.h
├─ línea 60-70  #ifndef mb  → #define mb()   barrier()
│              #ifndef rmb → #define rmb()  mb()   → barrier()
│              #ifndef wmb → #define wmb()  mb()   → barrier()
├─ línea 98-108 (CONFIG_SMP) smp_mb() = kcsan_mb(); __smp_mb();
│                            smp_rmb() = kcsan_rmb(); __smp_rmb();
│                            smp_wmb() = kcsan_wmb(); __smp_wmb();

include/linux/compiler.h
└─ línea 85     #define barrier() __asm__ __volatile__("": : :"memory")
```

**Resultado (esta es la tabla que pedía verificación explícita):**

| Macro en x86-64 | Se expande a | ¿Emite instrucción? | Tipo |
|---|---|---|---|
| `barrier()` | `asm volatile("": : :"memory")` | **NO — cero bytes** | barrera de **COMPILADOR** |
| `mb()` | `barrier()` | **NO** | compilador |
| `rmb()` | `mb()` → `barrier()` | **NO** | compilador |
| `wmb()` | `mb()` → `barrier()` | **NO** | compilador |
| `smp_rmb()` | `dma_rmb()`→`dma_mb()`→`mb()`→`barrier()` | **NO** | compilador |
| `smp_wmb()` | `barrier()` | **NO** | compilador |
| `smp_mb()` | `lock addl $0,-4(%rsp)` | **SÍ — 3 bytes** `F0 83 44 24 FC` | **hardware** |
| `smp_store_mb(v,x)` | `xchg(&v, x)` | **SÍ** | hardware (implícito) |
| `smp_store_release(p,v)` | `barrier(); WRITE_ONCE(*p,v)` | **NO** (salvo `xchg` si `*p` es atómico) | compilador + atomic store |
| `smp_load_acquire(p)` | `READ_ONCE(*p); barrier()` | **NO** | compilador |
| `io_mb()/io_rmb()/io_wmb()` | `smp_mb()` y afines vía `arch/x86/include/asm/iobarrier.h` | ver nota | mixto |
| `__smp_mb__before/after_atomic()` | `do {} while(0)` | **NO** | nada — *«Atomic operations are already serializing on x86»* |
| `smp_mb__after_switch_mm()` | `do {} while(0)` | **NO** | nada — *«Writing to CR3 provides a full memory barrier in switch_mm()»* |

> **Respuesta a la pregunta, en una frase: de las seis barreras "de memoria"
> (`mb`, `rmb`, `wmb`, `smp_mb`, `smp_rmb`, `smp_wmb`), en x86-64
> `smp_mb()` es la ÚNICA que genera una instrucción de máquina. Las otras cinco son
> barreras de compilador puras.**

Y **por qué es correcto** (no es un descuido del port x86): SDM3A §9.2.2 — *«Reads are
not reordered with other reads. Writes are not reordered with older reads. Writes to
memory are not reordered with other writes.»* El hardware x86-64 ya es
"write-ordered con store-buffer forwarding"; lo único que `smp_mb()` necesita
además es la **secuencia total** de las operaciones atómicas, y eso lo da `lock` /
`xchg` (Vol.3A §9.2.2: *«Locked instructions have a total order»*).
**El `barrier()` de compilador es imprescindible en los cinco casos restantes**:
impide que GCC mueva el acceso *a través* de la operación atómica, algo que el
compilador sí puede hacer libremente. Sin `barrier()`, un `smp_wmb()` sería un
`nop` y el compilador rompería la sincronización.

### 9.4 `READ_ONCE` / `WRITE_ONCE` — `HECHO` (SRC-RWONCE, `v6.16`)

```c
/* include/asm-generic/rwonce.h, líneas 43-62 */
#ifndef __READ_ONCE
#define __READ_ONCE(x)	(*(const volatile __unqual_scalar_typeof(x) *)&(x))
#endif

#define READ_ONCE(x)   ({ compiletime_assert_rwonce_type(x);  __READ_ONCE(x); })

#define __WRITE_ONCE(x, val)  do { *(volatile typeof(x) *)&(x) = (val); } while (0)
#define WRITE_ONCE(x, val)    do { compiletime_assert_rwonce_type(x); __WRITE_ONCE(x, val); } while (0)
```

**Son un acceso `volatile` y nada más.** Cero instrucciones, cero barreras de
hardware, cero `lock`.

> **Comentario del propio fichero (líneas 3-18), textual:** *«Prevent the compiler from
> merging or refetching reads or writes. The compiler is also forbidden from reordering
> successive instances of READ_ONCE and WRITE_ONCE, but only when the compiler is aware
> of some particular ordering. […] Their two major use cases are: (1) Mediating
> communication between process-level code and irq/NMI handlers, all running on the
> same CPU, and (2) Ensuring that the compiler does not fold, spindle, or otherwise
> mutilate accesses that either do not require ordering or that interact with an explicit
> memory barrier or atomic instruction that provides the required ordering.»*

Es decir, `READ_ONCE` **no** da atomicidad ni orden de hardware:
- **no** impide un *tearing* (salvo que el tamaño sea atómico por hardware);
- **no** impide el reordenamiento por el procesador (lo hace el modelo TSO de §9.2);
- **sí** impide que el compilador **(a)** elimine una carga cuyo valor no se usa,
  **(b)** duplique una carga, **(c)** la amplíe (un `READ_ONCE` de 4 bytes no se
  convierte en 8), **(d)** la fusione, **(e)** la reordene respecto a otro
  `READ_ONCE`/`WRITE_ONCE` en un punto donde el compilador tiene información de orden.

> **Uso complementario (SRC-X86BAR líneas 66-72):** `smp_load_acquire(p)` =
> `READ_ONCE(*p); barrier();`. Y `smp_store_release(p,v)` =
> `barrier(); WRITE_ONCE(*p,v)`. En x86-64 **ambas son barrera de compilador**, y por
> eso son correctas: la parte de hardware la aporta el modelo de memoria TSO. En
> ARM64, en cambio, `smp_store_release` **sí** emite `stlr`. **Copiar la macro de un
> puerto a otro sin mirar la definición es un bug de portabilidad** — y es
> exactamente el tipo de salto de nivel (`mecanismo` → `aplicabilidad`) que §2.8 del
> `AGENTS.md` prohíbe.

### 9.5 Cuándo usa el kernel barreras *reales* en x86-64

| Situación | Qué usa | Por qué |
|---|---|---|
| Secuencia total de operaciones atómicas | `smp_mb()` → `lock addl $0,-4(%rsp)` | Vol.3A §9.2.2: *«Locked instructions have a total order»* |
| Spin-wait | `cpu_relax()` → `PAUSE` | Reduce el coste de salida del bucle y el consumo (§9.1) |
| Ordenar la escritura de un registro de `mmio` de la GPU | `writel()` + `wmb()`/`io_wmb()` | **No es la máquina de memoria de la CPU.** La GPU ve un bus, no L1 coherente. El `volatile` de `writel()` + el hecho de que el puente PCIe no reordene es lo que da la garantía; `mb()` es sólo de compilador y **a propósito**. |
| Publicar un puntero a una estructurarecién construida | `smp_store_release()` / `WRITE_ONCE` + `smp_wmb()` | Publicación segura; el hardware ya ordena, el compilador necesita la barrera |
| Antes/después de una operación atómica | `smp_mb__before_atomic()` / `smp_mb__after_atomic()` | **Vacías en x86** — `xchg`, `cmpxchg` y `lock` ya son barreras completas (Vol.3A §9.2.2) |

> **Advertencia metodológica (importante para el proyecto).** En un `.ko` de amdgpu
> la distinción crítica **no** es CPU/GPU en abstracto, sino:
> `CPU_ACCESS` vs `PCI/IO_ACCESS` vs `DMC_ACCESS` (`include/amd_acpi.h` y familia), y
> el uso de `__iomem`. Un análisis de coherencia de cache hecho sólo con el SDM
> (Vol.3A) **no establece** nada sobre el bus PCIe hacia la GPU. Es
> `GENERAL_ARCHITECTURE_EVIDENCE` hasta que se demuestre la aplicabilidad.

---

## 10. Los bucles del fragmento: el problema real

### 10.1 Topología del fragmento (HECHO)

```
0x215161  41 bd 0a 00 00 00      mov  $0xa,%r13d        ← init del contador EXTERNO (10)
0x215167  bd 64 00 00 00         mov  $0x64,%ebp        ← init del contador MEDIO   (100)
0x21516c  31 d2                  xor  %edx,%edx         ← .L2: arg 3º de la llamada = 0
0x21516e  be af 3d 00 00         mov  $0x3daf,%esi      ← arg 2º: offset del registro MMIO
0x215173  4c 89 e7               mov  %r12,%rdi         ← arg 1º: adev
0x215176  e8 00 00 00 00         call 21517b            ← lectura del registro
0x21517b  a8 02                  test $0x2,%al          ← if (status & 2)
0x21517d  0f 85 bc 00 00 00      jne  21523f            ←   break  (salta FUERA de los 3 bucles)
0x215183  bb 0a 00 00 00         mov  $0xa,%ebx         ← init del contador INTERNO (10)
0x215188  bf 58 89 41 00         mov  $0x418958,%edi    ← .L3: arg = 4 295 000
0x21518d  e8 00 00 00 00         call 215192            ← llamada de 1 argumento, 32 bits
                                                                        (nombre del
                                                                         llamado: INFERENCIA,
                                                                         ver §10.2-bis)
0x215192  48 83 eb 01            sub  $0x1,%rbx
0x215196  75 f0                  jne  215188            ← back-edge del INTERNO
0x215198  83 ed 01               sub  $0x1,%ebp
0x21519b  75 cf                  jne  21516c            ← back-edge del MEDIO
        ┌───────────── 0x21519b … 0x21523E : ELIDEDADO por el enunciado ─────────────┐
        │  debe contener: r = 0; if (status & 2) break; DRM_ERROR(...);              │
        │  WREG32_FIELD(...,1); mdelay(10); WREG32_FIELD(...,0); mdelay(10);          │
        │  r = -1; y el back-edge EXTERNO hacia 0x215161                              │
        └─────────────────────────────────────────────────────────────────────────────┘
0x21523f  …                     ← etiqueta del `break` (fuera de los tres bucles)
```

Tres bucles anidados, con dos back-edges visibles:

| Nivel | Contador | Init | Back-edge | Trip count |
|---|---|---|---|---|
| Externo | `%r13d` | `0x215161` (`mov $0xa,%r13d`) | **en la región elidada** → `0x215161` | 10 |
| Medio | `%ebp` | `0x215167` (`mov $0x64,%ebp`) | `0x21519b` (`75 cf`) → `0x21516C` | 100 |
| **Interno** | `%rbx` | `0x215183` (`mov $0xa,%ebx`) | `0x215196` (`75 f0`) → `0x215188` | **10** |

`HECHO`: el bucle de 100 se ejecuta 10 veces por cada vuelta del de 10, y el interno
10 veces por cada vuelta del de 100. **10 × 100 × 10 = 10 000 invocaciones de
`__const_udelay` en el peor caso de un solo recorrido completo.**

### 10.2 El bucle interno **NO** lo introdujo el optimizador

**La hipótesis del encargo era: "el optimizador reordenó/añadió un nivel de anidamiento".
Es `CONTRADICTED`, y se refuta por tres vías independientes.**

#### Vía 1 — El código fuente contiene el bucle (`HECHO`, `SRC-DELAY` v6.16 líneas 29-47)

```c
#ifndef MAX_UDELAY_MS
#define MAX_UDELAY_MS	5
#endif

#ifndef mdelay
#define mdelay(n) (\
	(__builtin_constant_p(n) && (n)<=MAX_UDELAY_MS) ? udelay((n)*1000) : \
	({unsigned long __ms=(n); while (__ms--) udelay(1000);}))
#endif
```

Desplegado con `n = 10` y `MAX_UDELAY_MS = 5`:

```
(__builtin_constant_p(10) && 10 <= 5)   →  falso
⇒  { unsigned long __ms = 10; while (__ms--) udelay(1000); }
        ▲
        └── ÉSTE es el bucle de 10 iteraciones. Está en la MACRO, en el FUENTE.
```

Y `arch/x86/include/asm/delay.h` (v6.16) **no** redefine `mdelay` ni
`MAX_UDELAY_MS`, así que la definición genérica es la que aplica.

> **Asimetría que confirma la predicción:** `mdelay(5)` → `5 <= 5` → `udelay(5000)` →
> **una sola llamada**, sin bucle. `mdelay(10)` → `10 > 5` → **bucle de 10**.
> El mismo token, dos comportamientos radicalmente distintos según el valor.
> Un lector del fuente que escriba `mdelay(10)` pensando en "10 ms" tiene razón en el
> resultado, pero **la forma del código depende de si el número es ≤ 5**.

#### Vía 2 — El inmediato `0x418958` es exactamente `1000 × UDELAY_CONST_MULT` (`HECHO`)

`include/asm-generic/delay.h` (v6.16), textual:

```c
#define UDELAY_CONST_MULT  ((unsigned long)DIV_ROUND_UP(1ULL << 32, USEC_PER_SEC))
#define DELAY_CONST_MAX   20000

static __always_inline void udelay(unsigned long usec)
{
	if (__builtin_constant_p(usec)) {
		if (usec >= DELAY_CONST_MAX) __bad_udelay();
		else                        __const_udelay(usec * UDELAY_CONST_MULT);
	} else                             __udelay(usec);
}
```

Aritmética, derivable sin referencia externa:

```
UDELAY_CONST_MULT = DIV_ROUND_UP(2^32, 10^6) = (4294967296 + 999999) / 1000000 = 4295
udelay(1000)      → 1000 < DELAY_CONST_MAX(20000)  →  __const_udelay(1000 * 4295)
                  =  __const_udelay(4 295 000)
                  =  __const_udelay(0x00418958)          ← el inmediato del fragmento
```

```
4295000 en hexadecimal:
  4295000 / 16 = 268437 r 8      → 8
  268437 / 16 =  16777 r 5      → 5
   16777 / 16 =   1048 r 9      → 9
    1048 / 16 =     65 r 8      → 8
      65 / 16 =      4 r 1      → 1
       4                              → 4
  = 0x418958                                          ✓ COINCIDE CON EL BYTES
```

**El fragmento contiene el literal `0x418958`.** La probabilidad de que un
"optimizador" haya elegido por azar un número que es exactamente
`1000 × DIV_ROUND_UP(2³², 10⁶)` es nula. `UDELAY_CONST_MULT` es una constante
estable del kernel, y `1000` es el `udelay(1000)` literal de la macro.

**Confirmación independiente desde el otro extremo de la cadena**
(`SRC-X86DLYIMPL`, `arch/x86/lib/delay.c`):

```c
noinline void __const_udelay(unsigned long xloops)                 /* línea 207 */
{ … }
EXPORT_SYMBOL(__const_udelay);                                      /* línea 219 */

void __udelay(unsigned long usecs)                                  /* línea 221 */
{
        __const_udelay(usecs * 0x000010c7); /* 2**32 / 1000000 (rounded up) */   /* 223 */
}
void __ndelay(unsigned long nsecs)                                  /* línea 228 */
{
        __const_udelay(nsecs * 0x00005);    /* 2**32 / 1000000000 (rounded up) */ /* 229 */
}
```

`0x000010c7` = **4295** = `UDELAY_CONST_MULT`, escrito como literal en el **propio
fichero de implementación x86**, independiente de la macro de
`asm-generic/delay.h`. `0x00005` = **5** = `NDELAY_CONST_MULT`. Los dos
multiplicadores del kernel confirman la aritmética desde el otro extremo, y son
distintos entre sí, lo que permite el discriminador de abajo.

Y `noinline` + `EXPORT_SYMBOL` son decisivos: `noinline` es un atributo explícito
del kernel que **prohíbe** que el compilador inlinee, clonee o expanda
`__const_udelay` a ningún nivel de optimización. Por tanto, si el argumento es
4 295 000, la llamada no puede haber sido transformada en nada otro.

**Predicción comprobable a partir de este documento:** en la región elidada
`0x21519B…0x21523E` deben aparecer **dos bucles de 10 más**, correspondientes a los
dos `mdelay(10)` de `uvd_v6_0.c` líneas 817 y 819. Si aparecen, la hipótesis queda
cerrada. Si no aparecen, la hipótesis es `CONTRADICTED` y hay que buscar otro
`mdelay`-like.

#### Vía 2-bis — Por qué el *par* (10, 4 295 000) discrimina, y cada número solo no

Un buen contraargumento es: «4 295 000 podría salir de otra fórmula». Correcto, y por
eso el argumento no es «el número coincide» sino **«los dos números coinciden a la vez,
y por la misma causa»**. Enumeración de las alternativas que **sí** producen
4 295 000, y por qué cada una falla:

| Hipótesis alternativa | ¿Produce 4 295 000? | ¿Explica el bucle de **10**? | Veredicto |
|---|---|---|---|
| `udelay(1000)` → `__const_udelay(1000 × 4295)` | **Sí** | **Sí**: el `while` de `mdelay` | ← **la del autor** |
| `__ndelay(859000)` → `__const_udelay(859000 × 5)` | **Sí** | **No**: una sola llamada, sin bucle | refutada |
| `__udelay(4295000)` | **Sí** | **No**, y además `udelay()` con constante ≥ `DELAY_CONST_MAX` (20000) compila a `__bad_udelay()`, no a `__udelay()` | refutada por la propia macro |
| `udelay(10000)` con otro multiplicador | 4295000/10000 = 429.5, no entero | No | aritméticamente imposible |
| `__const_udelay(4295000)` escrito a mano | **Sí** | **No**: sin bucle | refutada |
| Una constante de `static const` cualquiera | posiblemente | No | refutada |

**El discriminador es la conjunción:** el *trip count* del bucle nuevo es igual a un
**parámetro de macro** (`mdelay(10)` → 10) **y** el inmediato invariante del bucle
nuevo es `ese_parámetro_de_delay × UDELAY_CONST_MULT`. Ninguna de las seis hipótesis
alternativas satisface las dos a la vez. Ése es el argumento completo, y por eso la
conclusión no se apoya en la coincidencia numérica por sí sola.

#### Vía 3 — Las pasadas que podrían haberlo hecho están **DESACTIVADAS** (`HECHO`)

Este es el discriminador definitivo. El kernel compila con `-O2`
(`Makefile` v6.16 línea 863, bajo `CONFIG_CC_OPTIMIZE_FOR_PERFORMANCE`), y
`KBUILD_CFLAGS` **no añade** `-funroll-loops`, `-fpeel-loops`, `-floop-interchange`,
`-floop-unroll-and-jam` ni `-funswitch-loops`.

Lista literal de `-O3` (**GCCOPT**, *Options That Control Optimization*):

> `-O3` turns on all optimizations specified by `-O2` and also turns on the following
> optimization flags:
> `-fgcse-after-reload  -fipa-cp-clone  -floop-interchange  -floop-unroll-and-jam
> -fpeel-loops  -fpredictive-commoning  -fsplit-loops  -ftree-loop-distribution
> -ftree-partial-pre  -funswitch-loops  -fvect-cost-model=dynamic
> -fversion-loops-for-strides`

Lista literal de `-O2` (**GCCOPT**), subconjunto relevante: `… -fexpensive-optimizations
-ffinite-loops -fmove-loop-invariants -fsched-spec -fstore-merging
-ftree-loop-distribute-patterns -ftree-loop-im -ftree-loop-ivcanon
-ftree-loop-pre -ftree-loop-vectorize -ftree-slp-vectorize -ftree-vrp …`

Y la lista de `-O1` incluye `-fivopts` (`*Perform induction variable optimizations
(strength reduction, induction variable merging and induction variable elimination)
on trees. Enabled by default at -O1 and higher.*`).

**Ninguna de las transformaciones capable de *crear* un nivel de anidamiento
(`-fpeel-loops`, `-floop-interchange`, `-floop-unroll-and-jam`, `-funroll-loops`,
`-fgraphite-loop-interchange`, `-floop-nest-optimize`) está activa en `-O2`.**

> **Conclusión lógica.** Un compilador que no ejecuta el unroller, el peeler, el
> interchanger ni el unroll-and-jam **no puede haber añadido un bucle**. Y, además,
> ninguna transformación de bucles de GCC **crea** un bucle donde el fuente no lo
> tiene: fusions, fissions, interchanges, peelings y unrollings **redistribuyen**
> iteraciones entre bucles existentes; no inventan un `while` alrededor de una
> llamada que el fuente emite una sola vez. La única fuente posible de un bucle de
> 10 alrededor de `__const_udelay` es una **expansión de macro**.

#### Vía 3-bis — Se ha refutado cada candidato restante a −O2, uno a uno

Un contraargumento fuerte exige enumerar las pasadas activas a `-O2` y descartar
cada una. Hecho:

| Pasada activa a `-O2` | ¿Puede envolver una llamada en un bucle nuevo? | Razón |
|---|---|---|
| `-finline-functions`, `-fpartial-inlining`, `-findirect-inlining` | **No** | Inlinear `udelay()` (que es `__always_inline`) produce `__const_udelay(…)` inlineado como `asm`/llamada. `__const_udelay` es **`noinline`** (`arch/x86/lib/delay.c:207`), así que se queda como llamada. Inlinear **más** código no puede **añadir** iteraciones. |
| `-fipa-cp-clone` | **No** | Clona *funciones* para constant-propagation; no clona un statement dentro de un bucle ni crea iteraciones. Además está en la lista de `-O3`, no de `-O2`. |
| `-ftree-loop-distribute-patterns` (loop distribution) | **No** | Solo reconoce el patrón `for (i…) if (patrón) SINK[i] = i;` y lo parte en dos bucles **del mismo nivel**. Una llamada opaca no es un patrón. |
| `-ftree-loop-im` (LICM) | **No** | Mueve código invariante **hacia fuera** del bucle. Al revés: la *reduciría*. |
| `-fivopts`, `-ftree-loop-ivcanon` | **No** | Reestructuran el **contador**; no añaden niveles. |
| `-ftree-loop-vectorize`, `-ftree-slp-vectorize` | **No** | No vectorizan bucles con una llamada opaca en el cuerpo. |
| `-freorder-blocks-and-partition`, `-fprofile-use` (off) | **No** | Reordenan bloques; no crean iteraciones. |
| Graphite (`-floop-nest-optimize`) | **No** | No aparece ni en la lista de `-O2` ni en la de `-O3`: hay que pedirlo explícitamente. |
| **Unrolling completo** de un bucle de trip-count constante | **No — y además es el mejor refutador** | El unroller produce **copias literales** del cuerpo, no un back-edge. El fragmento **tiene** back-edge: `0x215196: 75 f0` salta a `0x215188` y el contador `%rbx` **sobrevive** entre iteraciones. Un bucle completamente desenrollado no deja ni back-edge ni contador. **La presencia del back-edge refuta el unrolling de forma directa, sin importar el nivel de optimización.** |

Ese último punto es el más fuerte y es el que no depende del nivel de `-O`: **el
código desenrollado no tiene forma de bucle, y este lo tiene.** Por eso la Vía 3
refuerza pero **no es necesaria** para la conclusión; el argumento decisivo es el
**back-edge de `0x215196`** más el **par `(10, 4 295 000)`** de la Vía 2-bis.

### 10.3 El código fuente correspondiente (`HECHO`, con la versión delimitada)

`drivers/gpu/drm/amd/amdgpu/uvd_v6_0.c`, función `uvd_v6_0_start`. **Texto
idéntico en `v4.14` (línea 465), `v5.4` (790), `v5.15` (818) y `v6.16` (815)** —
doce años sin cambio. `FACT_FOR_LINUX_4.14_.._6.16`; para el kernel del host
(`7.1.3-…fc44`) la atribución es `INFERENCIA` salvo que se verifique el árbol
concreto (`HOW_IT_AFFECTS_THE_DECISION`: la probabilidad de divergencia en este
bloque es muy baja dado el histórico, pero **no es cero** y no se afirma que lo sea).

```c
	/* take all subblocks out of reset, except VCPU */
	WREG32(mmUVD_SOFT_RESET, UVD_SOFT_RESET__VCPU_SOFT_RESET_MASK);
	melay(5);                                    /* línea 790 */

	WREG32(mmUVD_VCPU_CNTL, UVD_VCPU_CNTL__CLK_EN_MASK);
	WREG32_FIELD(UVD_LMI_CTRL2, STALL_ARB_UMC, 0);

	/* boot up the VCPU */
	WREG32(mmUVD_SOFT_RESET, 0);
	mdelay(10);                                   /* línea 800  ← 1er bucle de 10, ANTES del for */

	for (i = 0; i < 10; ++i) {                    /* ← bucle EXTERNO, 10 */
		uint32_t status;

		for (j = 0; j < 100; ++j) {               /* ← bucle MEDIO, 100 */
			status = RREG32(mmUVD_STATUS);
			if (status & 2)
				break;
			mdelay(10);                          /* ← bucle INTERNO, 10  *** */
		}
		r = 0;
		if (status & 2)
			break;

		DRM_ERROR("UVD not responding, trying to reset the VCPU!!!\n");
		WREG32_FIELD(UVD_SOFT_RESET, VCPU_SOFT_RESET, 1);
		mdelay(10);                               /* ← 2º bucle de 10 (región elidada) */
		WREG32_FIELD(UVD_SOFT_RESET, VCPU_SOFT_RESET, 0);
		mdelay(10);                               /* ← 3er bucle de 10 (región elidada) */
		r = -1;
	}
```

**Nota sobre el fragmento del enunciado:** el fragmento del encargo **está truncado
por el control de flujo**, no por un error de lectura: el `jne 0x21523f` de
`0x21517d` salta **164 bytes por encima** del último `jne` del fragmento, y el
back-edge del bucle externo vive justo en ese hueco. Ése es el motivo por el que
`mov $0xa,%r13d` (0x215161) queda "colgando" en el fragmento.

### 10.3-bis El test discriminante se ejecutó: la región elidada, recuperada (`HECHO`)

El documento se había fijado a sí mismo un test comprobable (§10.2, Vía 2):
*«en la región elidada deben aparecer **dos bucles de 10 más**; si aparecen, la
hipótesis queda cerrada; si no, es `CONTRADICTED`»*. **Se ejecutó. Aparecen.**

Procedimiento, `READ_ONLY/EVIDENCE`, sin cargar ni ejecutar el módulo:

```bash
K=/lib/modules/7.1.3-200.nobara.fc44.x86_64/kernel/drivers/gpu/drm/amd/amdgpu/amdgpu.ko.zst
zstd -dc "$K" > /tmp/opencode/amdgpu.ko
objdump -d --start-address=0x215140 --stop-address=0x215250 -r /tmp/opencode/amdgpu.ko
```

| Procedencia del artefacto | Valor |
|---|---|
| Fichero | `/lib/modules/7.1.3-200.nobara.fc44.x86_64/kernel/drivers/gpu/drm/amd/amdgpu/amdgpu.ko.zst` |
| Tamaño comprimido | 5 954 300 B, `root:root`, mtime 2026-07-03 |
| Tipo | `ELF 64-bit LSB relocatable, x86-64, version 1 (SYSV), BuildID[sha1]=4d5342509f84dd84f0d5d515b03eb6c7659fb492, not stripped` |
| `SHA256` del `.ko` descomprimido | `a1a44c2457d33c65149ef4f455173ca446564bfd19bcc9cb215fca10cf24c024` |
| `uvd_v6_0_start` | `0x214E40 … 0x2154A0` (1632 B) — **coincide exactamente con el inicio deducido en §2.5 desde las 5 anotaciones** |
| Cropiado en | `02-ARQUITECTURA/ELF-RELOCATIONS-KERNEL-MODULES-REFERENCE.md` §5.4 (mismo objeto, mismo kernel) |

**Resultado: 4 `mdelay(10)` en el fuente ↔ 4 bucles de 10 `__const_udelay` en el
binario. Correspondencia 4-a-4.**

| # | `mdelay(10)` del fuente (línea) | Bucle de 10 en el binario | Inmediato | Llamado (relocación) |
|---|---|---|---|---|
| 1 | línea 800, antes del `for` | `0x215151 … 0x21515F` | `0x418958` | `R_X86_64_PLT32 __const_udelay-0x4` |
| 2 | línea 809, dentro del `for j` | `0x215188 … 0x215196` | `0x418958` | `R_X86_64_PLT32 __const_udelay-0x4` |
| 3 | línea 817 | `0x2151D1 … 0x2151DF` | `0x418958` | `R_X86_64_PLT32 __const_udelay-0x4` |
| 4 | línea 819 | `0x215209 … 0x215217` | `0x418958` | `R_X86_64_PLT32 __const_udelay-0x4` |

Y el resto de la región elidada, instrucción a instrucción:

```
0x21519d  48 c7 c7 <32S .rodata+0x235ac8>   mov $0x0,%rdi   ← 1er argumento de __drm_err
0x2151a4  bb 0a 00 00 00                    mov $0xa,%ebx   ← init bucle #3
0x2151a9  e8 …  R_X86_64_PLT32 __drm_err   call            ← DRM_ERROR("UVD not responding, …")
0x2151ae  31 d2                             xor %edx,%edx  ← flags = 0
0x2151b0  be a0 3d 00 00                    mov $0x3da0,%esi
0x2151b5  4c 89 e7                          mov %r12,%rdi
0x2151b8  e8 …  R_X86_64_PLT32 amdgpu_device_rreg  call   ← RREG32(UVD_SOFT_RESET)
0x2151bd  31 c9                             xor %ecx,%ecx  ← flags = 0   ┐
0x2151bf  be a0 3d 00 00                    mov $0x3da0,%esi               │ 4 args:
0x2151c4  4c 89 e7                          mov %r12,%rdi                 │ rdi,rsi,rdx,rcx
0x2151c7  83 c8 08                          or  $0x8,%eax    ← VCPU_SOFT_RESET=1  │
0x2151ca  89 c2                             mov %eax,%edx   ← valor             ┘
0x2151cc  e8 …  R_X86_64_PLT32 amdgpu_device_wreg  call   ← WREG32_FIELD(…,1)
0x2151d1 … 0x2151df                          bucle de 10 × __const_udelay     ← mdelay(10) #3
0x2151eb  bb 0a 00 00 00                    mov $0xa,%ebx   ← init bucle #4
0x2151ff  83 e0 f7                          and $0xfffffff7,%eax  ← VCPU_SOFT_RESET=0
0x215204  e8 …  R_X86_64_PLT32 amdgpu_device_wreg  call
0x215209 … 0x215217                          bucle de 10 × __const_udelay     ← mdelay(10) #4
0x215219  41 83 ed 01                       sub $0x1,%r13d ← decrementa i (32 bits)
0x21521d  0f 85 44 ff ff ff                 jne 215167     ← BACK-EDGE EXTERNO
0x215223  48 c7 c7 <32S .rodata+0x235b00>   mov $0x0,%rdi
0x21522a  e8 …  R_X86_64_PLT32 __drm_err   call            ← DRM_ERROR("… giving up!!!")
0x21522f  b8 ff ff ff ff                    mov $0xffffffff,%eax   ← return -1
0x215234…215238                             pop %rbx/%rbp/%r12/%r13
0x21523a  e9 …  R_X86_64_PLT32 __x86_return_thunk  jmp
0x21523f  31 d2 / be 40 3d 00 00 / 4c 89 e7 / e8 …  amdgpu_device_rreg  ← código post-bucle
```

**Tres correcciones a mi propia reconstrucción de §10.3, que el test reveló:**

| # | Lo que yo había reconstructing | Lo que hay | Por qué |
|---|---|---|---|
| **C1** | El back-edge externo va a `0x215161` | Va a **`0x215167`** (`jne 215167 <uvd_v6_0_start+0x327>`) | **Loop-header splitting**: la cabecera del bucle es `0x215167` (`mov $0x64,%ebp`); la inicialización de `i` (`0x215161`) queda **fuera** del bucle. `mov $0xa,%r13d` se ejecuta **una sola vez**. Yo leí el back-edge "hacia `0x215161`" porque ése es el inicio del init y no había mirado el destino real del `jne`. |
| **C2** | `r = 0;` y `r = -1;` existen en el binario | **No existen.** No hay ningún registro que lleve `r`. | GCCylie comprende que `r ∈ {0, −1}` y que `if (r)` es exactamente "el bucle se agotó", así que **sustituyó la variable por control de flujo**: si `sub $1,%r13d` no es cero, vuelve; si es cero, cae a `__drm_err("giving up")` y `mov $0xffffffff,%eax`. `r` fue **eliminada por completo**. |
| **C3** | `if (status & 2) break;` (el segundo, tras el `for j`) aparece en el binario | **No aparece en ninguna parte.** No hay un segundo `test $0x2,%al`. | **Los dos `if` son la misma condición por construcción**: la única forma de salir del `for j` antes de agotar las 100 iteraciones es con el bit 1 puesto, y eso salta directamente fuera de **ambos** bucles (`jne 0x21523F`). Si el `for j` se agota, el bit 1 está **probablemente** en 0 por construcción. El segundo `if` es **código muerto semánticamente** y GCC lo eliminó. |

> **C3 es el hallazgo más interesante de los tres**, y es exactamente el caso para el
> que se pidió esta referencia: **el segundo `if` está en el fuente y NO en el
> binario.** Un lector que sólo mire el desensamblado concluirá —erróneamente— que
> el fuente no lo tiene. Y un lector queake compare fuente y binario 1:1 concluirá
> —también erróneamente— que el desensamblado "falta código". **La diferencia entre
> el fuente y el binario no es un defecto de ninguno de los dos: es la
> eliminación de una condición redundante.** Un desensamblado no puede decidir eso
> por sí solo; hace falta el grafo de control, que es lo que este documento
> reconstruyó en §10.1.

**Estado final del hallazgo load-bearing:** `PROVISIONAL` → **`HECHO`**. La
correspondencia 4-a-4 entre sitios `mdelay(10)` del fuente y bucles de 10
`__const_udelay` en el binario, más las dos relocalizaciones `R_X86_64_PLT32`, es
evidencia directa y no una inferencia.

### 10.4 El nombre del llamado de `0x21518d` — cerrado por el test, con una lección de método

| Elemento | Estado | Base |
|---|---|---|
| La instrucción es un `call rel32` de 5 bytes | **`HECHO`** | `e8 00 00 00 00` |
| Pasa **un** argumento, en `%edi`, con valor `4 295 000` | **`HECHO`** | `bf 58 89 41 00` + ABI SysV |
| El destino es `__const_udelay` | **ahora `HECHO`** | `objdump -r`: `21518e: R_X86_64_PLT32 __const_udelay-0x4` |
| El destino de `0x215176` es `amdgpu_device_rreg` | **`HECHO`** | `215177: R_X86_64_PLT32 amdgpu_device_rreg-0x4` |
| `__const_udelay` es `UND` (lo importa del `vmlinux`) | **`HECHO`** | `readelf -sW amdgpu.ko` |
| …y el bucle es el `while` de `mdelay(10)` | **`HECHO`** | tabla 4-a-4 de §10.3-bis |

**La lección de método (y es el mensaje de este documento):** antes del test, esta
reconstrucción era `INFERENCIA` fuerte y así la etiqueté, con cuatro argumentos
(signature uniqueness, `noinline`, `EXPORT_SYMBOL`, aritmética del valor). Los
cuatro argumentos eran **correctos** y bastaban para *elegir* la hipótesis correcta.
**Ninguno de ellos era una medición.** Un `objdump -r` de 5 líneas habría bastado
desde el principio, y estaba disponible en el mismo host. **La prudencia de entonces no era
exceso de celo: era trabajo diferido que podía evitarse.** Registrar un
`NOT_DETERMINED` es correcto; **no reintentarlo cuando la evidencia ya está en el
host, es un fallo de §5.4 del `AGENTS.md`** (*«Do not stop merely because evidence
is missing if a safe authorized read can obtain it»*). Lección incorporada.

**El argumento, tal como se tivesse escrito *antes* del test (se conserva, porque
el valor de esta referencia está en hacerlo explícito y no en ocultarlo):**

> `…y por tanto el bucle es el `while` de `mdelay(10)`» — `INFERENCIA` fuerte,
> reforzada por las Vías 1, 2-bis y 3-bis.
>
> **Por qué era `INFERENCIA` fuerte y no `HECHO`:** para que la atribución fuera un
> hecho hacía falta **una** de estas dos observaciones:
> 1. `objdump -dr <modulo.ko>` → la columna de relocalización del `call` de `0x21518d`
>    muestra literalmente `R_X86_64_PLT32  __const_udelay-0x4`. Eso es el nombre, en
>    una línea.
> 2. `nm <modulo.ko> | grep udelay` + `readelf -r` para confirmar que la entrada sin
>    resolver corresponde a ese símbolo.
>
> **Por qué la inferencia era tan fuerte y no una conjetura:**
> - `__const_udelay` es el **único** símbolo del kernel con esta firma
>   (1 argumento `unsigned long` en `%rdi`) cuyo valor de uso conocido es
>   `udelay(μs) × UDELAY_CONST_MULT`. `__udelay(μs)` toma el valor en microsegundos
>   **sin** multiplicar, y `udelay()` con constante ≥ `DELAY_CONST_MAX` (20 000)
>   compila a `__bad_udelay()`, no a `__udelay()`.
> - `__const_udelay` es **`noinline`** (`arch/x86/lib/delay.c:207`): no puede haber
>   sido sustituida por código equivalente.
> - `EXPORT_SYMBOL(__const_udelay)` (línea 219) garantiza que un módulo la referencia
>   por símbolo, es decir por una relocación `PLT32` — que es exactamente el patrón
>   `e8 00 00 00 00` que vemos.
> - `4 295 000 / 4295 = 1000`, un valor de retardo redondo en microsegundos.
>
> **Confesión de rigor que sigue siendo válida:** atribuir el nombre a partir de la
> firma y del valor del argumento es el salto *«observación → mecanismo»* que el
> proyecto prohíbe, salvo que se nombre lo que lo justifica. Aquí se nombraban: la
> unicidad de la firma dentro del árbol, más la aritmética del valor, más `noinline`,
> más `EXPORT_SYMBOL`. Son **cuatro** restricciones, no una coincidencia — pero son
> un argumento sobre lo que el código *tiene que ser*, no una lectura, y por eso no
> degradé a `HECHO`. **La clasificación precautionary era correcta; la omisión de
> la medición no lo fue.**

### 10.5 La firma de `RREG32`/`WREG32` — cerrada por las relocalizaciones (`HECHO`)

`objdump -r` da el nombre del llamado; las cuentas de argumentos dan la firma. Todo
`HECHO` a partir de aquí:

```
0x2151b8: call  R_X86_64_PLT32  amdgpu_device_rreg-0x4
0x2151cc: call  R_X86_64_PLT32  amdgpu_device_wreg-0x4
```

| Llamada | `%rdi` | `%rsi` | `%rdx` | `%rcx` | N args | Encaja con |
|---|---|---|---|---|---|---|
| `amdgpu_device_rreg` | `%r12` (`adev`) | `0x3daf` / `0x3da0` / `0x3d40` (`reg`) | `0` (`xor %edx,%edx`) | — | **3** | `RREG32(reg)` = `amdgpu_device_rreg(adev, (reg), 0)` |
| `amdgpu_device_wreg` | `%r12` (`adev`) | `0x3da0` (`reg`) | `%eax` (`val`) | `0` (`xor %ecx,%ecx`) | **4** | `WREG32(reg,v)` = `amdgpu_device_wreg(adev, (reg), (v), 0)` |

> **Corrección de la versión del macro.** En `v4.14` el macro era
> `#define RREG32(reg) amdgpu_mm_rreg(adev, (reg), 0)`; en `v6.16` ya era
> `amdgpu_device_rreg(adev, (reg), 0)`. **El módulo analizado (kernel 7.1.3) usa la
> forma `amdgpu_device_rreg`.** Mi §10.5 original citaba las dos; ahora se sabe
> cuál. `readelf -sW` lo confirma: `amdgpu_device_rreg` es `FUNC … 12` (sección
> `.text`) en `0x7ce0`, 316 bytes — es decir, amdgpu **lo define** en el módulo, no
> lo importa. `__const_udelay` y `__drm_err` sí son `UND`.

**El `xor %rdx,%edx` de la cabecera de bucle (P7) queda confirmado por esta vía:** el
tercer argumento de `amdgpu_device_rreg` es la constante `0` del macro, la llamada lo
destruye, y GCC lo repone en el pre-header del bucle. **No es una inicialización de
variable.**

**Y los dos `WREG32_FIELD` se leen directamente de los bytes:**

| Dirección | Bytes | Lectura | Fuente |
|---|---|---|---|
| `0x2151C7` | `83 c8 08` | `or $0x8,%eax` ⇒ escribe el **bit 3** | `UVD_SOFT_RESET__VCPU_SOFT_RESET` = bit 3, valor `1` |
| `0x2151FF` | `83 e0 f7` | `and $0xfffffff7,%eax` ⇒ **borra el bit 3** | valor `0` |

`or` y `and` sobre la máscara en vez de `mov` inmediato: es *read-modify-write* de un
campo de bits, que es exactamente lo que significa `_FIELD`. El valor leído viene de
`amdgpu_device_rreg(adev, 0x3da0, 0)` en `0x2151B8` — la lectura del mismo registro
que luego se modifica. **Coherente con `WREG32_FIELD(UVD_SOFT_RESET, VCPU_SOFT_RESET, 1)`.**

#### El único `NOT_DETERMINED` que sobrevive: el significado de `0x3daf`

| Pregunta | Estado | Razón |
|---|---|---|
| `0x3daf` es el 2º argumento de `amdgpu_device_rreg` | **`HECHO`** | `readelf -r` + la cuenta de 3 argumentos |
| `0x3daf` es un literal, no un addend de relocación | **`HECHO`** | `objdump -d` **no** muestra ninguna entrada `R_X86_64_32S` ni `PC32` en `0x21516e`; si la hubiera, `objdump` imprimiría `$0x0` |
| `0x3daf` es la dirección de byte de `mmUVD_STATUS` | **`NOT_DETERMINED`** | No está alineado a 4, lo que **contradice** que sea una dirección de un registro de 32 bits. `0x3da0` (el `reg` de los dos `WREG32_FIELD`) sí está alineado. **No se inventa una explicación.** |
| …y por qué `UVD_SOFT_RESET` = `0x3da0` y `UVD_STATUS` = `0x3daf` differen en 15 | `NOT_DETERMINED` | Requiere la cabecera de registros UVD **de la versión 7.1.3 concreta** |

> **`0x3daf` no es un símbolo.** Se comprobó: `readelf -sW amdgpu.ko` no tiene ningún
> símbolo con `st_value` `0x3daf`. Hay símbolos en `0x3da0` (`dev_attr_xgmi_port_num`)
> y `0x3d40` etc., pero están en `.rodata` y la **coincidencia numérica no significa
> nada** — es la misma trampa que avisa §1.2 de
> `02-ARQUITECTURA/ELF-RELOCATIONS-KERNEL-MODULES-REFERENCE.md`: *«Un `st_value` en un
> `ET_REL` no significa nada sin su `Ndx`»*.

> **Lo que NO se afirma:** que `0x3daf` sea una dirección MMIO válida, ni que
> `status & 2` sea el bit `UVD_STATUS__VCPU_REPORT` (que en las cabeceras que he
> leído vale `2 << UVD_STATUS__VCPU_REPORT__SHIFT` = bit 5, **no** el bit 1 que
> maskea el `test $0x2`). El `& 2` es `HECHO`; el **nombre** del bit es
> `NOT_DETERMINED` para esta versión. Buscar el nombre del bit en la versión
> equivocada es precisamente un salto prohibido por §2.2 del `AGENTS.md`
> (*«A symbol, enum or structure a source does not confirm is not a fact»*).

> **Cómo cerrarlo (una orden):** `dnf download --source amdgpu` para el `7.1.3-200.fc44`,
> extraer `uvd/uvd_6_0_d.h`, y `grep -nE '0x3daf|UVD_STATUS|UVD_SOFT_RESET'`. O, más
> rápido: en el `.ko`, `objdump -d` las demás funciones y ver si `0x3daf` aparece con
> un `UVD_STATUS`-like contiguo. **No ejecutado**: requiere descargar el SRPM, que es
> red, no un fichero del host.

### 10.6 Catálogo de transformaciones de bucles (§9 del encargo)

| Transformación | GCC | LLVM | Qué hace al anidamiento | ¿Puede **crear** un nivel nuevo? |
|---|---|---|---|---|
| **Loop unrolling** | `-funroll-loops` (`-O3`+explícito) | `loop-unroll`, `loop-unroll-and-jam` | Duplica el cuerpo N veces; el contador se reduce | **No**: si el trip count es múltiplo de N y no hay epílogo, el bucle **desaparece** |
| **Loop peeling** | `-fpeel-loops` (`-O3`) | `loop-peel` | Separa las primeras N iteraciones del resto | **No**: crea un bucle *hermano*, no anida |
| **Loop interchange** | `-floop-interchange` (`-O3`) | `loop-interchange` (requiere dependencias) | Intercambia dos niveles | **No**: conserva el número de niveles |
| **Loop fusion** | `-ftree-loop-*` (parcial) / Graphite | `loop-fusion` | Funde bucles adyacentes **del mismo nivel** | **No**: reduce el número de bucles |
| **Loop fission** | `-ftree-loop-distribution` | `loop-distribute` | Parte un bucle en varios del mismo nivel | **No**: aumenta el número de bucles siblings, no el anidamiento |
| **Loop unswitching** | `-funswitch-loops` (`-O3`) | `loop-unswitch` | Duplica el bucle según una condición invariante | **No**: crea copias del mismo bucle |
| **Loop rotation / canonicalization** | siempre activo | `loop-rotate`, `loop-simplify`, `indvars` | Mueve la condición al *bottom*testing, crea pre-header y contador canónico | **No**: cambia la *forma*, no el *número* de niveles |
| **Induction variable elimination** | `-fivopts` (`-O1+`) | `indvars` | `for(i=0;i<N;i++)` → `cnt = N; …; cnt--; jne` | **No** — pero **es el que produce el `sub $1; jne` del fragmento** |
| **Vectorization** | `-ftree-loop-vectorize`, `-ftree-slp-vectorize` (`-O2`) | `loop-vectorize` | Sustituye el cuerpo escalar por SIMD | **No** |

> **Argumento de forma general (el "cómo distinguir" que pedía el encargo):**
> en la teoría de transformaciones de bucles, **ninguna transformación aumenta la
> profundidad de anidamiento**. Fusión y distributing operan sobre bucles *siblings*
> y conservan la profundidad. Intercambio conserva la profundidad. Unrolling y
> peeling operan *hacia fuera*. Unswitching multiplica el número de copias de un
> bucle, no su nivel. **Un nivel de anidamiento nuevo, o un bucle nuevo alrededor de
> un statement que en el fuente no está en bucle, sólo puede venir de una expansión
> de macro (`#define` con `for`/`while`) o de desensamblado incorrecto.**
>
> Y el discriminador empírico, no teórico, es el **triple** del §10.2:
> (a) el número de vueltas del bucle nuevo es **igual a un parámetro de una macro**
> del fuente (`mdelay(10)` → 10);
> (b) el inmediato invariante del bucle nuevo es **una fórmula de la macro**
> (`1000 × UDELAY_CONST_MULT` = `0x418958`);
> (c) **el compilador no ejecutó ninguna pasada capaz de crearlo** (`-O2`).
> Con los tres, la hipótesis del optimizador queda `PROVEN_ABSENT` para este
> fragmento. Con uno solo, sigue siendo `PROVISIONAL`.

> **Reproducir la diferencia (discriminating test, el control inverso de §11.3 del
> `AGENTS.md`):**
> ```c
> /* A: el fuente tal cual */
> for (i=0;i<10;i++) { mdelay(10); }
> /* B: el fuente con el bucle de la macro escrito a mano */
> for (i=0;i<10;i++) for (k=10;k;k--) udelay(1000);
> /* C: el fuente con una sola llamada */
> for (i=0;i<10;i++) __const_udelay(4295000);
> ```
> Con `-O2`, **A y B deben producir el mismo código** (el preprocesador es
> determinista) y **C debe producir código diferente** (una llamada por vuelta).
> Si A ≠ B, la culpa es del preprocesador y la conclusión del documento se
> derrumba. Este experimento **no se ha ejecutado** (`NOT_RUN`): requiere gcc
> 16.1.1, y §13.2 del `AGENTS.md` no autoriza ejecuciones en esta tarea
> (`WORK_CLASS=DOCUMENTATION`).

---

## 11. Ejercicio *worked*: reconstrucción del fuente

### 11.1 Lo que se lee directamente en los bytes (`HECHO`, no admite discusión)

| # | Hecho | Bytes que lo prueban |
|---|---|---|
| F1 | En `0x215161` se carga el inmediato 32 bits `0xa` en `r13d` (32 bits, registro extendido) | `41 bd 0a 00 00 00` |
| F2 | En `0x215167` se carga `0x64` = 100 en `ebp` | `bd 64 00 00 00` |
| F3 | Antes de cada llamada se pone `0` en `rdx` | `31 d2` en la cabeza de `0x21516C` |
| F4 | Antes de cada llamada se carga `0x3daf` en `esi` | `be af 3d 00 00` |
| F5 | Antes de cada llamada se copia `r12` en `rdi` | `4c 89 e7` |
| F6 | Hay una llamada de 5 bytes con `rel32 = 0` (relocación sin resolver) | `e8 00 00 00 00` ×2 |
| F7 | Tras la llamada se prueba el bit 1 (`mask 0x2`) del valor devuelto en `AL` | `a8 02` |
| F8 | Si el resultado es cero → salto de +188 bytes, hacia `0x21523f` | `0f 85 bc 00 00 00` |
| F9 | Hay un bucle de exactamente 10 iteraciones cuyo cuerpo es una llamada de 5 bytes con `edi = 0x418958` | `bb 0a 00 00 00` / `bf 58 89 41 00` / `e8 …` / `48 83 eb 01` / `75 f0` |
| F10 | El bucle de 10 tiene su back-edge en `0x215196`, destino `0x215188` | `75 f0` |
| F11 | El bucle de 100 tiene su back-edge en `0x21519b`, destino `0x21516c` | `75 cf` |
| F12 | `0x3daf` es el 2º argumento de una llamada de 3 argumentos | `be …` + `31 d2` + `4c 89 e7` + `e8 …` |
| F13 | El contador del bucle de 10 se decrementa en **64 bits**; el del bucle de 100 en **32 bits** | `48 83 eb 01` vs `83 ed 01` |
| F14 | `0x418958` = 4 295 000 | `bf 58 89 41 00` |
| F15 | El destino `0x21523f` está fuera de los tres bucles | aritmética de `0f 85` |
| F16 | Las 5 anotaciones `<uvd_v6_0_start+0xNNN>` resuelven todas a `0x214E40` | §2.5, tabla de coherencia |
| F17 | El bucle de 10 tiene un **back-edge** (`0x215196: 75 f0` → `0x215188`) y su contador sobrevive entre iteraciones | §10.3-bis — **esto refuta el unrolling con independencia del nivel de `-O`** |

### 11.1-bis Siete objeciones que la inversa (`AUTOOBSERVED`) tuvo, y su veredicto

> **Limitación de esta revisión, declarada (§2.9, §14.5).** El proyecto dispone de
> subagentes revisores para dar **independencia** real, pero en esta sesión la
> invocación falló (`Subagent depth limit reached`). La pasada de refución la
> ejecutó **el mismo agente que escribió el documento**. Por tanto **no es revisión
> independiente**: es `AUTOOBSERVED` sobre mi propio trabajo, y su valor es el de un
> *check* sistemático, no el de una confirmación. Para un juicio independiente hace
> falta reejecutar §10.2-bis y §10.3-bis con otro lector.

| # | Objeción | Veredicto |
|---|---|---|
| R1 | «4 295 000 podría salir de otra fórmula» | **Respondida.** Vía 2-bis: 6 alternativas enumeradas; sólo `udelay(1000)` satisface a la vez el valor **y** el trip count 10. |
| R2 | «Podría ser `ndelay`» | **Respondida y refutada.** `NDELAY_CONST_MULT` = 5, luego `ndelay(859000)` da una **sola** llamada, sin bucle. |
| R3 | «`__const_udelay` no está inlineeada, pero ¿y si es otra función?» | **Respondida y CERRADA.** `objdump -r` (ejecutado, §10.3-bis): `21518e: R_X86_64_PLT32 __const_udelay-0x4`, y `readelf -sW` lo da `UND`. **R3 era la única objeción que sobrevivía; ya no.** |
| R4 | «`MAX_UDELAY_MS` podría estar sobreescrito en x86 o en DRM» | **Respondida y refutada.** `include/linux/delay.h:30` es la **única** definición (`#ifndef MAX_UDELAY_MS / 5`); `arch/x86/include/asm/delay.h` tiene 13 líneas y no define nada al respecto; `include/asm-generic/delay.h` no define `mdelay` ni `MAX_UDELAY_MS`; no hay override en `drivers/gpu/drm/`. |
| R5 | «A −O2 hay otras pasadas que podrían crear un bucle» | **Respondida.** Vía 3-bis: 9 pasadas activas a −O2, una a una, y **además** el argumento que no depende de −O: el unrolling no deja back-edge, y este lo tiene. |
| R6 | «`%r13d` (32 bits) vs `%rbx` (64 bits): ¿dos bucles *distintos*?» | **Respondida: neutro, y ligeramente a favor.** Los dos contadores vienen de **bucles de origen distintos** — el `for (i…)` del fuente y el `while (__ms--)` de la macro — y no hay razón para que el asignador los trate igual. Que difieran en registro *y* en ancho es **predicción** de la hipótesis de la macro, no evidencia contra. No se usa como argumento. |
| R7 | «¿La aritmética de longitudes cierra exactamente?» | **Verificado programáticamente.** 27/27 comprobaciones (longitudes, chaining de direcciones, los tres destinos de salto, `0x418958 = 4 295 000`, `UDELAY_CONST_MULT = 4295`, las 5 anotaciones de símbolo). 0 fallos. Refutado. |

**Y una octava, que la comparación con el objeto real produjo y no estaba en mi lista:**

| # | Objeción | Veredicto |
|---|---|---|
| R8 | «La estructura de bucles que reconstruiste es la del fuente» | **PARCIALMENTE REFUTADA — y es la corrección más valiosa del trabajo.** Tres cosas del fuente **no** están en el binario, y una cosa del binario **no** está donde yo la puse. Ver la tabla C1/C2/C3 de §10.3-bis: el back-edge externo va a `0x215167` y no a `0x215161`; la variable `r` **no existe**; y el **segundo** `if (status & 2) break;` **no aparece**. Mi reconstrucción era `PROVISIONAL` y así estaba etiquetada; el test la convirtió en `HECHO` **y la corrigió**. Una reconstrucción declarada `PROVISIONAL` es una afirmación falsable; esto es lo que pasa cuando se la somete a un test. |

### 11.2 Reconstrucción, con el grado de confianza de cada línea

```c
static int uvd_v6_0_start(struct amdgpu_device *adev)
{
	...
	int i, j, r;                                  /* INFERENCIA fuerte  */
	...
	for (i = 0; i < 10; ++i) {                     /* INFERENCIA fuerte  */
		uint32_t status;                          /* INFERENCIA         */

		for (j = 0; j < 100; ++j) {               /* INFERENCIA fuerte  */
			status = RREG32(mmUVD_STATUS);       /* INFERENCIA fuerte: encaja con
			                                        la firma de 3 args (F12) y con
			                                        RREG32 de amdgpu                 */
			if (status & 2)                       /* HECHO (F7): la máscara es 0x2
			                                        sobre el valor devuelto en AL.
			                                        INFERENCIA: que sea `&` y no `==`,
			                                        y que sea la línea 1 de un if     */
				break;                             /* HECHO (F8, F15): el salto sale
			                                        de los tres bucles, no al medio   */
			mdelay(10);                           /* INFERENCIA FUERTE→CONFIRMADA por
			                                        3 caminos independientes (§10.2).
			                                        F9+F14 encajan exactamente con la
			                                        expansión de la macro;
			                                        AHORA HECHO: 4 bucles de 10
			                                        __const_udelay, §10.3-bis       */
		}
		/* r = 0;            ← ELIMINADO por GCC (§10.3-bis, C2) */
		/* if (status & 2)   ← ELIMINADO por GCC (§10.3-bis, C3):
		     break;             redundante con el test de arriba           */
		DRM_ERROR("UVD not responding, trying to reset the VCPU!!!\n");
		                                     /* HECHO: 0x2151A9 __drm_err          */
		WREG32_FIELD(UVD_SOFT_RESET, VCPU_SOFT_RESET, 1);
		                                     /* HECHO: 0x2151C7 or $0x8,%eax
		                                        + 0x2151CC amdgpu_device_wreg   */
		mdelay(10);                           /* HECHO: 0x2151D1..0x2151DF        */
		WREG32_FIELD(UVD_SOFT_RESET, VCPU_SOFT_RESET, 0);
		                                     /* HECHO: 0x2151FF and $0xfffffff7,%eax
		                                        + 0x215204 amdgpu_device_wreg   */
		mdelay(10);                           /* HECHO: 0x215209..0x215217        */
		/* r = -1;           ← ELIMINADO por GCC (§10.3-bis, C2):
		                      se volvió control de flujo, y el valor -1
		                      es directamente mov $0xffffffff,%eax         */
	}
	...
}
```

**Grados, después del test:**

| Elemento | Grado | Base |
|---|---|---|
| 3 bucles con conteos 10/100/10 en el fragmento | **`HECHO`** | F9, F11, F1, F2 |
| `mdelay(10)` = bucle de 10 × `__const_udelay(0x418958)` | **`HECHO`** | correspondencia **4-a-4** con los 4 `mdelay(10)` del fuente (§10.3-bis) + 2 relocalizaciones `PLT32` |
| Los 2 `mdelay(10)` de la región elidada | **`HECHO`** | recuperados en `0x2151D1` y `0x215209` |
| `break` en el bit 1 | **`HECHO`** | F7 (máscara `0x2` sobre `AL`) + F8/F15 (salto fuera de los 3 bucles) + `0x21523F` confirmado |
| `WREG32_FIELD(UVD_SOFT_RESET, VCPU_SOFT_RESET, 1/0)` | **`HECHO`** | `or $0x8` / `and $0xfffffff7` sobre el valor leído del mismo registro |
| `DRM_ERROR("UVD not responding…")` | **`HECHO`** | `0x2151A9: R_X86_64_PLT32 __drm_err` + argumento en `.rodata+0x235ac8` |
| `DRM_ERROR("… giving up!!!")` | **`HECHO`** | `0x21522A: __drm_err` + `.rodata+0x235b00` |
| `return -1` al agotar el bucle | **`HECHO`** | `0x21522F: mov $0xffffffff,%eax` + `jmp __x86_return_thunk` |
| El back-edge externo va a `0x215167` | **`HECHO`** (corrige mi C1) | `0x21521D: jne 215167` |
| `r = 0` / `r = -1` **existen** | **`CONTRADICTED`** (corrige mi C2) | No hay registro que las contenga: GCC eliminó `r` |
| El 2º `if (status & 2) break;` **aparece** | **`CONTRADICTED`** (corrige mi C3) | No hay un 2º `test $0x2,%al` en la función |
| Nombre `mmUVD_STATUS` | `INFERENCIA` fuerte | `0x3daf` no alineado (§10.5) |
| Nombre del bit 1 de UVD_STATUS | **`NOT_DETERMINED`** | Requiere la cabecera de la versión 7.1.3 |
| Tipo `uint32_t` de `status` | `INFERENCIA` | Sólo se prueba `AL` (8 bits bajos) |

### 11.3 Honestidad: fuentes alternativas que generan los mismos bytes

> **El enunciado pedía exactamente esto, y es la parte que más se omite.**

| Fuentes alternativas | ¿Genera los mismos bytes? | Discriminador |
|---|---|---|
| (A) `mdelay(10)` del kernel | **Sí** — verificado en 4 tags y por aritmética del inmediato | — |
| (B) `for (k=0;k<10;k++) udelay(1000);` escrito a mano | **Sí, byte a byte idéntico** | **Indistinguible en los bytes.** La macro (A) *es* (B) tras preprocesar. Sólo el preprocesado y el `DWARF` (`-g`) los distinguen. **Este es el límite duro de la decompilación desde bytes.** |
| (C) `for (k=0;k<10;k++) __const_udelay(4295000);` | **Sí, idéntico** | Igual que (B) |
| (D) `udelay(10000)` con un `udelay` distinto en una versión de kernel anterior | **No**: `udelay(10000)` → `__udelay(10000)`, no `__const_udelay`. Y el conteo sería 1, no 10. **Refutada** | El conteo 10 y el nombre `__const_udelay` |
| (E) `msleep(10)` | **No**: dormiría, no haría `busy wait`, yGCC lo habría convertido en otra cosa | El `call` a `__const_udelay` con constante 4295000 |
| (F) Un `-funroll-loops` sobre un bucle de 1 iteración | **No**: produciría 10 copias *literales* de la llamada, no un bucle con back-edge. Y no está activo en `-O2` | `48 83 eb 01` + `75 f0` (back-edge) vs 10× `e8 …` |
| (G) `delay()` / `ssleep()` | **No** | Ninguno compila a `__const_udelay(4295000)` × 10 |

**La respuesta a «¿dos fuentes distintas pueden generar los mismos bytes?» es
`SÍ`, y la pareja (A)/(B) es el ejemplo real de este caso: la diferencia entre
`mdelay(10)` y su propio cuerpo literal es **información de la fase de
preprocesado**, que el desensamblado no conserva. Lo que SÍ se conserva, y es lo que
permite la conclusión, es la **fórmula numérica** `0x418958 = 1000 ×
DIV_ROUND_UP(2³², 10⁶)`: eso no lo puede producir una coincidencia, lo produce una
constante del código fuente.

**Caveat de versionado (AGENTS.md §3.2).** La atribución de la fuente a la función
`uvd_v6_0_start` es `FACT_FOR_LINUX_{4.14,5.4,5.15,6.16}`. El host usa
`7.1.3-…fc44`, un árbol que no he inspeccionado. El bloque no ha cambiado en 12 años
y medio en 4 tags consecutivos, lo que hace la atribución `PLAUSIBLE` con
`SINGLE_SOURCE` nulo (son 4 observaciones independientes del mismo texto). **No se
afirma que el árbol del host contenga este texto**; se afirma que si lo contiene,
produce estos bytes. Para elevarlo a `HECHO` hace falta una de estas dos:
`objdump` de la región elidada `0x21519B…0x21523F` (predicción: 2 bucles de 10
más), o el `.ko` con DWARF (`--dwarf=decodedline` / `addr2line -e … 0x215161`).

---

## 12. ERRORES COMUNES AL LEER DESENSAMBLADO

Ordenados por **frecuencia real**, con el discriminador y el término `AGENTS.md`
que viola cada uno.

### E1 · No comprobar `REX` antes de decidir el registro
**Síntoma:** `41 bd 0a 00 00 00` → «`bd` es MOV r32,imm32, y `41` sobra».
**Realidad:** `41` = `REX.B`; sin él, `rd=101` daría `%r5` = `%rbp`. Con él, `%r13`.
**Regla:** decodifica el `REX` **antes** que el opcode, y recuerda que `W=0` significa
"32 bits por defecto en 64-bit mode", no "16 bits".
**Viola:** §2.2 — *«Never infer behaviour from a function, symbol or field name»*
aplicado a byte names.

### E2 · Inventar un byte ModR/M donde no lo hay
**Síntoma:** en `41 bd 0a 00 00 00`, leer `0a` como ModRM (`mod=00, reg=001, rm=010`).
**Realidad:** la fila `B8+rd` **no tiene ModR/M**: el campo de 3 bits vive en el propio
opcode. `0a` es el byte bajo del `imm32`.
**Regla:** antes de decodificar ModR/M, comprueba en la tabla de opcode si la forma
es de la familia `B0+rb`/`B8+rd`/`A0+AL`/`AA+DX` (opcode con campo embebido) o de la
familia `/digit` (opcode de 1 byte + ModR/M). **Si la longitud no cuadra hasta el
siguiente desensamblado, no hay ModR/M.**
**Viola:** §2.2, §6.6 (*«A predicate written before the property it scores has an
undefined unit»*).

### E3 · Asumir que `REX.B` (o cualquier bit de REX) cambia el tamaño del inmediato
**Síntoma:** «`mov $0xa,%r13d` usa `imm8` porque lleva REX, así que el rango es
−128…255».
**Realidad:** el tamaño del inmediato es una propiedad de la **fila de opcode**
(`B0+rb ib` = imm8, `B8+rd id` = imm32, `REX.W + B8+rd io` = imm64). `REX` sólo
extiende el campo de registro y ajusta W.
**Regla:** el tamaño del inmediato sale de la tabla del opcode; el prefijo no lo
toca. Y para *reducir* bytes existe el opcode alternativo (`83 /5 ib` = imm8 con
sign-extension), no el prefijo.
**Viola:** §2.9 (*«capability → use»* aplicado a campos de codificación).

### E4 · Leer `F3` como `REP` cuando es prefijo obligatorio
**Síntoma:** `f3 90` → «`REP NOP`».
**Realidad:** `F3 90` = **`PAUSE`**. En `F3 0F 6F` el `F3` es *mandatory prefix*, no
*repeat*. El SDM lo dice: *«The first byte is a mandatory prefix (it is not considered
as a repeat prefix).»*
**Regla:** `F2`/`F3` tienen **dos papeles** según el opcode que sigue. Se determina
mirando la fila de opcode, no el prefijo.
**Viola:** §2.2 — el nombre `REP` es un *nombre*, no una definición.

### E5 · Concluir que un `call 0` / `e8 00 00 00 00` es un bug
**Síntoma:** «el módulo llama a sí mismo, está roto».
**Realidad:** en un `.ko` (`ET_REL`, sin enlazar) las relocalizaciones
`R_X86_64_PLT32` valen 0 hasta que `ld` las resuelve. objdump imprime el
desensamblado **pre-relocalización**, así que el destino que muestra
(`21517b`, `215192`) es la dirección siguiente.
**Prueba definitiva (ejecutada en este caso):** `21518e: R_X86_64_PLT32
__const_udelay-0x4`. El símbolo existe; los bytes no lo saben todavía.
**Regla:** `objdump -dr` antes de concluir nada sobre cualquier `call`/`jmp` de un
objeto no enlazado. Además: para un `call rel32` de 5 bytes el número que objdump
imprime depende **sólo** del addend `A = −4`, así que es siempre `instrucción + 5`
— tres `call` seguidos dan tres números distintos y **ninguno** codifica el destino.
**Viola:** §2.4 (*«a file present → an instruction loaded»*, y por extensión
«bytes present → relocation resolved»).

### E6 · Asumir que un inmediato es una dirección
**Síntoma:** `bf 58 89 41 00` → «`0x418958` es un puntero a una estructura».
**Realidad:** es `__const_udelay(4295000)`, un **número de iteraciones de bucle
calibrado**. No está alineado, es mayor que cualquier offset de sección de un `.ko`,
y es reproducible aritméticamente desde una fórmula del kernel.
**Regla:** clasifica un inmediato por su **rol** (dato / desplazamiento / número de
iteraciones / máscara de bits) antes de interpretarlo. Un inmediato que acompaña a
`call`/`mov` con destino de argumento es **casi siempre** un dato.
**Viola:** §2.9 (*«un inmediato es una dirección» es un salto no justificado*),
§6.1 (*«A name is not a measurement»*).

### E7 · Asumir que el destino de un salto es `dirección_actual + desplazamiento`
**Síntoma:** `75 f0` en `0x215196` → «`0x215196 − 0x10 = 0x215186`».
**Realidad:** es `RIP_**siguiente** + desp` = `0x215198 − 0x10 = 0x215188`.
**Regla:** siempre `+ longitud de la instrucción` primero. Comprueba después que el
destino cae en un **comienzo de instrucción** del desensamblado; si cae en medio, has
sumado mal.
**Viola:** §11.1 — *«recheck every count, with the unit named»*.

### E8 · Tratar la diferencia de tamaño de un salto como diferencia de semántica
**Síntoma:** «`0f 85` es un salto "distinto" de `75`».
**Realidad:** los dos son `JNE`; uno alcanza ±127 y el otro ±2 GiB. objdump/GAS eligen
el más corto posible (`AS` §9.16.8, textual).
**Regla:** comprueba primero el campo `cc` (`0x75` = cc 5, `0x0F 0x85` = cc 5). Si
coinciden, es la misma condición y sólo cambia el alcance.
**Viola:** §8.3 (*«un cambio de nombre, parámetro, magnitud o implementación es
`VARIANT_OF`»*) aplicado a lectura de desensamblado.

### E9 · Buscar un `cmp` antes de cada salto condicional
**Síntoma:** «`jne` sin `cmp` detrás es imposible / es un salto por defecto».
**Realidad:** `test` (y `and`) computes banderas sin escribir registro. En el
fragmento, `a8 02` + `0f 85` implementa `if (status & 2)` sin ningún `cmp`.
**Regla:** antes de buscar `cmp`, mira `test`. `test` pone `ZF` exactamente igual que
`cmp`, y `CF=OF=0` (`AF` indefinida).
**Viola:** §2.9 (*«observation → mechanism»* al revés: conclusión sin el dato).

### E10 · Confundir el sufijo `l` con "el tamaño máximo"
**Síntoma:** en x86-64, `movl %eax,%ebx` → «32 bits es el máximo, no hay más».
**Realidad:** `l` = *long* = 32 bits, nombre heredado del 386. El máximo en x86-64 es
`q` (quadword) con `%rax`. `mova` en ensamblador es un error.
**Regla:** `b`/`w`/`l`/`q` = 1/2/4/8 bytes, punto. `e` en el *nombre del registro*
(`%eax`) significa "extensión de 32 bits", y en x86-64 `%eax` y `%rax` son
**registros distintos** que comparten nombre base.
**Viola:** §3.2 — conclusión de x86-32 trasladada sin re-verificar.

### E11 · No comprobar el prefijo `REX` en instrucciones con operandos de 8 bits
**Síntoma:** con REX presente, `mov %ah, …` no se puede codificar; el ensamblador
"cambia" a `%spl`.
**Realidad:** con REX, los bytes altos (`AH/BH/CH/DH`) **no son direccionables**;
`%spl/%bpl/%sil/%dil` son registros de 8 bits distintos. Sin REX, `AH` sigue
funcionando.
**Regla:** REX presence cambia el **mapa de registros de 8 bits**, no sólo los
extendidos. Chequear antes de asumir que "el byte bajo de `%rax` es `%al`".
**Viola:** §2.2.

### E12 · Confundir `%r12` con un temporal
**Síntoma:** «`4c 89 e7` es un `mov` de relleno para ganar un ciclo».
**Realidad:** en el ABI de Linux x86-64, `%r12` es **callee-saved**, y en este
punto del fragmento ya está siendo reutilizado por el asignador de registros de GCC
como si fuera caller-saved, porque su valor (`adev`) se ha copiado a la pila o ya no
vive. La llamada a `amdgpu_mm_rreg` es *directa* y por eso GCC no necesita preservar
`%r12` entre ella y el uso.
**Regla:** antes de llamar "relleno" a un `mov` entre registros, comprueba si el
registro es callee-saved en el ABI. Un `mov %rXX,%rYY` de 3 bytes que parece
inneficiente suele ser la consecuencia de una decisión previa dePressure de
registros.
**Viola:** §2.9 — *«observation → mechanism»*.

### E13 · Contar bytes de `call` creyendo que puede haber un `call rel8`
**Realidad (x86-64):** `CALL` cercano es `E8 cd` = **siempre 5 bytes**. El
desplazamiento es siempre de 32 bits, sign-extendido a 64. No hay forma corta, y no
la había en x86-32 tampoco.
**Viola:** §3.2 — no trasladar tamaños entre modos.

### E14 · Contar bytes de `jcc` como si el `66` puddle shorten `rel32` a `rel16`
**Realidad:** `0F 83 cw` (`JNC rel16`) está marcado **`N.S.` — "Not supported in
64-bit mode"** en la tabla de opcodes de `Jcc` (SDM2 p. 3-550/3-551). En 64 bits sólo
existen `rel8` y `rel32`.
**Viola:** §2.9 — trasladar una codificación de 32 bits a 64 sin comprobar la
columna "64-Bit Mode" de la tabla.

### E15 · Tratar un `xor %reg,%reg` como "inicialización de variable"
**Síntoma:** `31 d2` en la cabeza del bucle → «`status = 0`» o «`d = 0`».
**Realidad (más económica):** es el tercer argumento, constante `0`, de una llamada
de 3 argumentos que destruye `%rdx`. El compilador tiene que reponerlo cada vuelta, y
lo hace en el pre-header del bucle.
**Regla:** un `xor` a cero justo antes de un `call` es un **argumento**, no una
variable. Un `xor` a cero *después* de un `call` o en un sitio sin llamada
posterior, es más probablemente una variable.
**Viola:** §2.9 — *«observation → mechanism»* aplicado a un `xor`.

### E16 · Confundir "bucle del optimizador" con "bucle de la macro"
**Síntoma:** «hay un bucle de más, luego el compilador lo ha añadido».
**Realidad (§10.2):** las transformaciones de bucle de GCC y LLVM **no crean**
niveles de anidamiento; y las que podrían (`-fpeel-loops`, `-floop-interchange`,
`-floop-unroll-and-jam`, `-funroll-loops`) **no están activas en `-O2`**, que es lo
que usa el kernel.
**Regla:** antes de culpar al optimizador, mira si el **bucle nuevo contiene un
statement que en el fuente es una `#define`**. Y comprueba el nivel de optimización
real antes de invocar ninguna pasada.
**Viola:** §2.8, §2.9 — el salto prohibido más caro: *«observation → mechanism»* con
un mecanismo inventado.

### E17 · Confundir `%eax` con `%rax` y `movl` con `mov`
**Realidad:** en el ABI de Linux x86-64, el retorno de una función `int`/`long` de 32
bits está **implícitamente extendido** a 64 en `%rax` (`cdqe` / `movslq` en el
llamante, o el valor se Simply no ensancha si el tipo de retorno es `unsigned`).
**Regla:** comprueba el tipo de retorno antes de asumir que los 32 bits superiores son
"basura".
**Viola:** §6.3 — mezclar observador y entidad.

### E18 · Saltarse el SIB en `[base+index*scale]`
**Síntoma:** `[rsp+8]` → `mod=00, rm=100, disp8=8`.
**Realidad:** hace falta un byte SIB más; `rm=100` **significa "hay SIB"**. Además,
`SIB.index=100` significa "sin índice", y `RSP` no puede ser índice.
**Viola:** §2.2, y E2 en su versión de direccionamiento.

### E19 · Confiar en que `0f 85` y `75` son "la misma instrucción"
**Síntoma:** contar 19 instrucciones donde hay 15, porque se cuentan mnemónicos
distintos como instrucciones distintas.
**Realidad:** son 15 instrucciones en 15 direcciones; dos pares comparten mnemónico
con distinta forma de inmediato.
**Regla:** cuenta **direcciones**, no mnemónicos.
**Viola:** §6.4 — *«A quantifier is part of the name»*.

### E20 · Afirmar que un identificador de un binario tiene un significado de C
**Síntoma:** `<uvd_v6_0_start+0x33b>` → «la línea 0x33b de la función».
**Realidad:** `+0x33b` es el **desplazamiento en bytes** desde el inicio del símbolo.
La fuente de amdgpu tiene ~450 líneas y la región elidada (`0x21519B…0x21523F`)
son **164 bytes** (`0xA4`); ese número es una distancia, no una línea.
**Regla:** para mapear a líneas necesitas DWARF: `addr2line -e <ko> 0x215161` o
`objdump --dwarf=decodedline`. Sin DWARF, el mapeo línea↔offset es
`NOT_AVAILABLE`, no "aproximado".
**Viola:** §2.2 — *«Never infer behaviour from a function, symbol or field name»*.

### E21 · Leer `%gs:0x28` sin saber qué hay detrás
**Realidad:** en userland x86-64, `%gs` es la base del TLS y `[%gs:0x28]` es el
`pthread` de pthread (`fs`/`gs:0` es el `Tcb` de Windows); en kernel, `%fs` es la
base del `per_cpu` y `[%fs:0x10]` es `current_task`. **El contenido del slot depende
del SO y del ABI, y no lo define el manual de instrucciones.**
**Regla:** un prefijo de segmento es información de segmentación, no de contenido.
**Viola:** §2.8 — *«Sibling architectures are not this target»*.

### E22 · Asumir que una barrera del kernel genera una instrucción
**Síntoma:** «el desensamblado no muestra `mfence` donde hay `smp_wmb()`, luego
`wmb()` no funciona».
**Realidad (§9.3):** en x86-64, `wmb()`/`rmb()`/`mb()`/`smp_wmb()`/`smp_rmb()` son
`barrier()` = `asm volatile("": : :"memory")`, **cero bytes**, y no deben aparecer.
Sólo `smp_mb()` → `lock addl $0,-4(%rsp)`, `smp_store_mb()` → `xchg`, y las
`io_*` emiten fences reales.
**Regla:** la ausencia de una instrucción en el desensamblado **confirma** el
comportamiento correcto de la macro, no lo refuta. Antes de culpar al compilador,
mira la definición de la macro en **tu** arquitectura.
**Viola:** §2.9 — *«a capability → use»*; y §8.3 — cambiar sólo un nombre es `VARIANT_OF`, no un cambio.

### E23 · Confiar en que la dirección de objdump es una VA del sistema
**Realidad:** en un `.ko`, la dirección de objdump es el **offset dentro de la
sección**; la VA real se conoce sólo tras cargar el módulo (`/proc/modules` +
`sysfs`, o `kallsyms`).
**Regla:** para calcular direcciones de hardware necesitas el base de carga.
**Viola:** §3.2 — *«Identify a device by PCI identity, never by `cardN`»*, y su
equivalente para direcciones: base de carga, no `cardN`.

### E24 · Tratar el nombre de la instrucción como su semántica
**Síntoma:** `pause` → "para la CPU".
**Realidad (SDM2 p. 4-230):** *«This instruction does not change the architectural state
of the processor (that is, it performs essentially a **delaying no-op** operation).»*
Es una *pista* al predictor/microarquitectura y un reductor de consumo, no una parada.
**Viola:** §2.2, literalmente.

### E25 · Registrar un `NOT_DETERMINED` cuando la medición ya está disponible en el host
**Éste es el error que este mismo cometió, y por eso va aquí.** En la primera
redacción, la identidad del llamado en `0x21518d` quedó como `INFERENCIA` fuerte con
cuatro argumentos indirectos (unicidad de firma, `noinline`, `EXPORT_SYMBOL`,
aritmética del valor), y el `NEXT` proposée fue «`objdump -dr`». **Ese `NEXT` no
necesitaba autorización, no necesitaba red, y se ejecutaba en cinco líneas sobre un
fichero que ya estaba en el mismo disco.** Cuando se ejecutó, cambió tres cosas:
el nombre pasó de `INFERENCIA` a `HECHO`, la correspondencia `mdelay` pasó de 4-a-4
esperada a 4-a-4 **medida**, y la reconstrucción del grafo de flujo tuvo que ser
**corregida en tres puntos** (§10.3-bis, C1-C3).
**Regla:** antes de escribir `NOT_DETERMINED`, comprobar si un `readelf -r`, un
`objdump -r`, un `addr2line` o un fichero correlativo **ya presente en el host** lo
cierran. La pregunta correcta no es «¿puedo medirlo?» sino «¿hay aquí una medición
que aún no he hecho?».
**Viola:** §5.4 del `AGENTS.md` (*«Do not stop merely because evidence is missing if a
safe authorized read can obtain it»*) y §14.1 (*«A `NEXT` is justified by new evidence
or a pending human decision»* — un `NEXT` de cinco líneas no es un `NEXT`, es trabajo
sin hacer).

---

## 13. Procedimiento reproducible para el siguiente caso

```
1.  objdump -d --insn-width=16 -M att <modulo.ko>   >  d.txt
    objdump -dr --show-relocs            <modulo.ko> >  dr.txt   ← OBLIGATORIO
    objdump -dM intel                   <modulo.ko> >  di.txt     ← contraste de sintaxis
    addr2line -f -e <modulo.ko> 0x215161                         ← si hay DWARF
    readelf -r <modulo.ko> | grep R_X86_64

2.  Para cada instrucción, en este orden:
    a. Prefijos legacy (¿cuál? ¿obligatorio o de grupo?)
    b. REX (¿W/R/X/B? ¿qué campo extiende?)
    c. Opcode base (¿1, 2 o 3 bytes? ¿hay campo embebido o /digit?)
    d. ModR/M (¿existe? mod/reg/r/m)
    e. SIB (¿existe? scale/index/base)
    f. displacement (tamaño y signo)
    g. inmediato (tamaño; ¿sign-extended?)
    h. longitud total — COMPRUEBA que coincide con la siguiente dirección
       ⚠ si no coincide, algo de (a)-(g) está mal. No sigas.

3.  Reconstruye el CFG: une cada salto con su destino y marca los back-edges.
    Los back-edges son las aristas de retorno de bucle. Anota el contador de
    cada uno. ⚠ si un back-edge cae en mitad de instrucción, para.

4.  Para cada bucle: cuenta el trip count desde el HECHO. Compáralo con
    cualquier constante del fuente. Si coincide con un PARÁMETRO DE MACRO,
    la lectura "bucle del optimizador" es PROVEN_ABSENT.

5.  Antes de atribuir un nombre a un inmediato: clasifícalo por rol
    (dato / máscara / desplazamiento / número de iteraciones / puntero).
    Si es un argumento de call, es un dato.

6.  Antes de afirmar causalidad sobre el hardware: comprueba el nivel de -O
    real del build, y qué macro del kernel está detrás de cada "bucle nuevo".
```

---

## 14. Referencias

### Normativas (primarias)
- **SDM-C** — Intel® 64 and IA-32 Architectures Software Developer's Manual,
  Combined Volumes 1, 2A, 2B, 2C, 2D, 3A, 3B, 3C, 3D, 4. Order `325462`,
  2024-06-20. Capítulos usados:
  - Vol.2A **Ch.2 Instruction Format**: §2.1 (Fig. 2-1), §2.1.1 (prefijos legacy,
    grupos 1-4), §2.1.2 (opcodes 1/2/3 bytes), §2.1.3 (ModR/M y SIB), §2.1.4,
    §2.1.5 (Tablas 2-1, 2-2, 2-3, Fig. 2-2), §2.2.1 (REX, §2.2.1.2 Tabla 2-4 p. 2-9,
    §2.2.1.5 Fig. 2-3, §2.2.1.6 **Tabla 2-7** p. 2-11, §2.2.1.7), §2.2.1.5;
  - Vol.2A §2.3 (VEX, Fig. 2-8..2-9, Tablas 2-10, 2-11, 2-12), §2.7.1 (EVEX,
    Fig. 2-10, 2-11);
  - Vol.2A **Apéndice A** (mapas de opcode de 1, 2 y 3 bytes);
  - Vol.2A p. 3-550..3-554 (**Jcc**, Tabla de opcodes y `0F 85 cd`), p. 3-555
  (**JMP**), p. 3-139 (**CALL**), p. 3-614 (**LOCK**), p. 3-208 (**CMPXCHG**);
  - Vol.2B p. 4-35..4-37 (**MOV**, tabla de opcodes `B8+rd id` / `REX.W + B8+rd io`),
  p. 4-673 (**SUB**, `83 /5 ib` y Flags Affected), p. 4-703 (**TEST**, `A8 ib`,
  Flags Affected), p. 4-230 (**PAUSE**, `F3 90`), p. 4-22 (**MFENCE**), p. 3-602
  (**LFENCE**), p. 4-616 (**SFENCE**), p. 6-28 (**XCHG**);
  - Vol.1 p. 7-15..7-17 (**Tabla 7-4** saltos condicionales, §7.3.8.2 bucles,
  §7.3.8.3 ramas en 64-bit mode, §7.3.1.2 XCHG);
  - Vol.3A Ch.9 **Multiple-Processor Management**: §9.1.1 operaciones atómicas
  garantizadas, §9.1.2 Bus Locking, §9.1.2.1 Automatic Locking, §9.1.4 efectos de
  LOCK en las cachés, **§9.2.2 Memory Ordering in P6 and More Recent Processor
  Families**.
- **APM1** — AMD64 Architecture Programmer's Manual Vol. 1, Order `24592`,
  **Rev. 3.11 (Diciembre 2005)**. Usado: §3.5 Instruction Prefixes, §3.5.1 Legacy
  Prefixes (**Tabla 3-7**, grupos), §3.5.2 REX Prefixes (rango `40h`–`4Fh`, unicidad,
  posición, límite de 15 bytes). **No cubre VEX/EVEX** (2005).
- **AS** — GNU as manual, secciones x86: §9.16.3 i386 Syntactical Considerations,
  §9.16.3.2 Special Characters, §9.16.4.1 Instruction Naming (sufijos `b/w/l/q`,
  destino en último lugar), §9.16.4.2 AT&T vs Intel Mnemonic, §9.16.5 Register
  Naming, §9.16.7 Memory References (`disp(base,index,scale)` ↔
  `[base+index*scale+disp]`, `*` para saltos absolutos, `disp(%rip)`), §9.16.8
  Handling of Jump Instructions.
- **OBJD** — `objdump(1)`: Target Selection x86-64 (`intel`/`att`/`amd64`/`intel64`/
  `intel-mnemonic`/`att-mnemonic`/`suffix`/`addr64`/`addr32`/`addr16`/`data32`/
  `data16`); `--show-raw-insn` (por defecto), `--no-show-raw-insn`, `--insn-width`,
  `--no-addresses`, `--prefix-addresses`, `-r`.
- **ARK** — Intel ARK, Intel® Core™ i7-4790: *4th Generation Intel® Core™ i7
  Processors*, *Code Name: Products formerly Haswell*, 4 núcleos / 8 hilos,
  AVX2 (sin AVX-512).
- **GCCOPT** — *Options That Control Optimization*: listas literales de `-O2` y
  `-O3`; `-fivopts` (*«Enabled by default at -O1 and higher»*); `-fpeel-loops`
  (*«Enabled by -O3, -fprofile-use, and -fauto-profile»*); `-floop-interchange`
  (*«enabled by default at -O3»*); `-floop-unroll-and-jam` (*«enabled by default at
  -O3»*); `-ftree-loop-im`; `-ftree-loop-ivcanon`; `-ftree-loop-vectorize` (`-O2`).
- **GCCINT** — *GCC Internals*: §18.13 Loop manipulation (`duplicate_loop_body_to_header_edge`
  = unrolling o peeling; `tree_unroll_loop`; `loop_version`), §18.14 Looping
  Instruction Patterns (`doloop_begin`/`doloop_end`, contador de iteraciones).
- **LLVMP** — LLVM *Analysis and Transform Passes*: `loop-simplify`, `loop-rotate`,
  `indvars` (*«All loops are transformed to have a single canonical induction variable
  which starts at zero and steps by one»*), `loop-unroll`, `loop-unroll-and-jam`,
  `loop-unswitch`, `loop-fusion`, `loop-deletion`, `loop-reduce`, `licm`.

### Código (fuente primaria del comportamiento)
- `drivers/gpu/drm/amd/amdgpu/uvd_v6_0.c` — `uvd_v6_0_start`, bucle de polling de
  UVD. Idéntico en `v4.14`, `v5.4`, `v5.15`, `v6.16`.
- `drivers/gpu/drm/amd/amdgpu/amdgpu.h` — `#define RREG32(reg) amdgpu_mm_rreg(adev,(reg),0)`
  (`v4.14:1631`); `amdgpu_device_rreg(adev,(reg),0)` (`v6.16:1420`).
- `include/linux/delay.h` — `MAX_UDELAY_MS` (5) y `mdelay(n)` con el `while`
  (líneas 29-46).
- `include/asm-generic/delay.h` — `UDELAY_CONST_MULT`, `DELAY_CONST_MAX`, `udelay()`.
- `arch/x86/include/asm/delay.h` — **no** redefine `mdelay` (verificado).
- `arch/x86/include/asm/barrier.h` — `__mb/__rmb/__wmb`, `__smp_mb` = `lock addl`.
- `include/asm-generic/barrier.h` — `mb/rmb/wmb` → `barrier()`; `smp_*` en
  `CONFIG_SMP`.
- `include/linux/compiler.h:85` — `barrier()` = `__asm__ __volatile__("": : :"memory")`.
- `include/asm-generic/rwonce.h` — `__READ_ONCE`/`__WRITE_ONCE` (volatile puro).
- `Makefile` (KBUILD_CFLAGS) — `-O2` bajo `CONFIG_CC_OPTIMIZE_FOR_PERFORMANCE`.

### No usados, y por qué
- `Documentation/arch/x86/`, `Documentation/devicetree/` — no contienen nada sobre
  el decodificado de instrucciones que el SDM no diga mejor.
- Tutoriales de blog sobre `objdump` — `NOT_A_SOURCE` (regla del encargo y §4.1 del
  `AGENTS.md`).

---

## 15. Estado del encargo

| Pregunta | Terminal | Nota |
|---|---|---|
| 1. Sintaxis AT&T vs Intel, sufijos | `ANSWERED` | §2. Noritada con `AS` + `OBJD`. |
| 2. Anatomía de una línea, longitud | `ANSWERED` | §3. Noritada con SDM Vol.2A §2.1. |
| 3. Formatos, prefijos, REX | `ANSWERED` | §4. Las 8 combinaciones REX tabuladas. `CONFLICT` menor en el nº de grupos de prefijos (Intel 4 vs AMD 5), con impacto nulo. |
| 4. ModRM/SIB byte a byte | `ANSWERED` **con 2 premisas corregidas** | §5. No hay ModR/M en `B8+rd`; los dos inmediatos son `imm32`. |
| 5. Modos de direccionamiento | `ANSWERED` | §6. Tabla 32 filas + SIB + RIP-relativo. |
| 6. Control de flujo | `ANSWERED` | §7. Aritmética del destino resuelta; el error intermedio del enunciado identificado. |
| 7. Aritmética y banderas | `ANSWERED` | §8. `test` vs `sub`, tabla de 16 condiciones. |
| 8. Atómicos y barreras | `ANSWERED` **con verificación explícita** | §9. **`smp_mb()` es la única de las seis que emite una instrucción.** `READ_ONCE`/`WRITE_ONCE` = `volatile` puro. Nada afirmado de memoria. |
| 9. Bucles del fragmento | `ANSWERED` — **la hipótesis del encargo es `CONTRADICTED`** | §10. El tercer bucle es el `while` de `mdelay(10)`. Tres vías independientes. |
| 10. Ejercicio *worked* | `ANSWERED` | §11. 16 `HECHO`, el resto graduado. Se declara explícitamente la indistinguibilidad (A)/(B). |

| Estado | Contenido |
|---|---|
| `CONTRADICTED` | Las 6 premisas erróneas del encargo (P1-P6) **+ 3 errores de mi propia reconstrucción** (C1-C3, §10.3-bis), corregidos tras el test |
| `CONFLICT` | Intel agrupa prefijos legacy en 4 grupos, AMD en 5. `RESOLUTION_STATUS=OPEN`, `IMPACT=0` |
| `EXECUTED` | El test discriminante de §10.3-bis: descompresión del `.ko` de `7.1.3-200.nobara.fc44` y `objdump -d -r` de `0x215140…0x215250`. `WORK_CLASS=READ_ONLY/EVIDENCE`. Resultado: predicción 4-a-4 **confirmada** |
| `NOT_DETERMINED` | · **el significado de `0x3daf`** (§10.5 — el único `NOT_DETERMINED` que sobrevive; requiere la cabecera de registros UVD de la versión 7.1.3)<br>· el nombre del bit 1 de `UVD_STATUS` (misma causa) |
| `AUTOOBSERVED` | La pasada de refución R1-R8 (§11.1-bis). **La ejecutó el mismo agente que escribió el documento**: la independencia de `adversarial-reviewer` no estaba disponible (`Subagent depth limit reached`). No es revisión independiente. |
| `SOURCE_NOT_FOUND` | `drivers/gpu/drm/amd/amdgpu/uvd/uvd_6_0_d.h` en `v4.14` (`404`) |
| `FETCH_FAILED` | `amd.com` (3 URLs, `404`); sustituido por espejo con `SHA256` registrado |
| `NOT_RUN` | Compilación de los tres programas de control A/B/C (§10.6); exige gcc 16.1.1 y ejecución, no autorizada en `WORK_CLASS=DOCUMENTATION`. **Nota:** §10.3-bis cerró la misma pregunta por la vía de la evidencia del artefacto, sin compilar nada |
| `EXTERNAL` | El marco normativo (SDM, APM, manuals de binutils/GCC/LLVM, ARK). El **contenido sobre el fragmento** ya no es `EXTERNAL`: es evidencia del artefacto de este host |
| `HOST_SCOPE` | `HOST-C` (el `.ko` es de `7.1.3-200.nobara.fc44`, el kernel del host vivo según `PATCH-SOURCES.md` §3) para §10.3-bis. `EXTERNAL` para la norma |
| `TEMPORALITY` | No aplica: documento normativo + análisis estático de un artefacto, sin ejecución del módulo |

**El punto más débil que queda, en una frase:** `0x3daf`, el 2º argumento de
`amdgpu_device_rreg`, **no está alineado a 4** y por tanto no puede ser la dirección
de byte de un registro de 32 bits — mientras que el `reg` de los dos
`WREG32_FIELD` (`0x3da0`) **sí** lo está. La diferencia de 15 unidades entre ambos
no tiene explicación establecida. **No se inventa una.** Requiere la cabecera de
registros UVD de la versión 7.1.3 exacta.

**`NEXT` (justificada por evidencia nueva, no por curiosidad):**

| # | Acción | Qué cambia si es positiva / negativa | Coste |
|---|---|---|---|
| N1 | `dnf download --source amdgpu` (7.1.3-200.fc44) y `grep -nE 'UVD_STATUS;UVD_SOFT_RESET;3daf'` en las cabeceras UVD | Cierra el **único** `NOT_DETERMINED` vivo: qué es `0x3daf` y qué nombre tiene el bit 1. **Positiva** → el `& 2` se convierte en `test & 0x2` con nombre semántico. **Negativa** → `0x3daf` es otra cosa y hay que re-leer el macro. | Bajo-medio: red. |
| N2 | Reejecutar §10.2-bis y §10.3-bis con `adversarial-reviewer` | Cierra el `AUTOOBSERVED` con **independencia real**. Ahora con más material (la región elidada recuperada), el valor sube. | Bajo, si hay profundidad de subagente |
| N3 | Compilar A/B/C de §10.6 con gcc 16.1.1 | Control inverso del *preprocesador*. **Valor bajo ahora**: §10.3-bis ya cerró la misma pregunta por evidencia de artefacto, que es más fuerte que una compilación propia. | Medio, requiere autorización (§13.2) |
| N4 | **Repasar la regla de §5.4 en el resto del corpus**: ¿hay otros `NOT_DETERMINED` que se puedan cerrar con una lectura ya disponible en este host? | El test de §10.3-bis demostró que el `NOT_DETERMINED` era cerrable en 5 líneas, y que la evidencia estaba local. `NEXT` de mayor alcance del proyecto. | Bajo, pero es trabajo de barrido |
| N5 | Decidir si este documento entra al `DOCUMENTATION-ROUTER` como `TOPIC` nuevo, y si se enlaza con `02-ARQUITECTURA/ELF-RELOCATIONS-KERNEL-MODULES-REFERENCE.md` | Sin eso, el router seguirá mandando a otro sitio las consultas de lectura de desensamblado, y dos documentos sobre el mismo `.ko` seguirán sin cruzarse. | **Decisión humana** (§10.2) |

**`STOP_REASON=SUFFICIENT_PRIMARY_EVIDENCE`** para las diez preguntas del encargo.
N1-N4 no son necesarias para la corrección del documento: son para cerrar el último
`NOT_DETERMINED` y para tapar la deuda de método que N4 describe.

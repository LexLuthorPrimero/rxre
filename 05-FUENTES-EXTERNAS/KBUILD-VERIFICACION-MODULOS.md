# Compilar y verificar un módulo de kernel Linux — REFERENCIA

**Documento de referencia.** Objeto: responder con evidencia, y no con suposiciones, a
la pregunta «¿este binario `.ko` corresponde a este código fuente?».

**Etiquetas de clasificación** (usadas en todo el documento):

| Etiqueta | Significado |
|---|---|
| `NORMA` | Comportamiento establecido por la fuente primaria del kernel, citada por ruta y versión |
| `HECHO` | Observación directa y reproducible en este host, con el comando o artefacto que la produce |
| `SECUNDARIO` | Fuente externa consultada que no es la fuente primaria de este host |
| `INFERENCIA` | Deducción razonada a partir de `NORMA`/`HECHO`, con su base nombrada |
| `NOT_DETERMINED` | No establecido; se dice dónde se buscó y por qué no se cerró |

**Universo de la investigación.** Host `kalm`, x86_64, `uname -r` =
`7.1.3-200.nobara.fc44.x86_64`. Artefacto estudiado: `amdgpu.ko` descomprimido
(37.494.368 B), `srcversion` = `D68004925455E20A24C2B87`. Árbol de desarrollo:
`/usr/src/kernels/7.1.3-200.nobara.fc44.x86_64` (22.930 ficheros).
Versión de referencia upstream: `v7.1` del árbol `torvalds/linux`, con `v7.1.3`
comprobado como idéntico en los dos ficheros citados donde importa.

---

## 0. RESUMEN EJECUTIVO — Y CORRECCIONES A LAS PREMISAS DEL ENCARGO

Cinco puntos del encargo resultaron **refutados** por la fuente primaria o por el
artefacto. Se enumeran primero porque cambian el uso de la herramienta.

| # | Premisa del encargo | Veredicto | Evidencia |
|---|---|---|---|
| P1 | «`srcversion` es un CRC32 truncado» | **REFUTADA.** Es **MD4 (RFC 1320)**, y el truncamiento es a **23** hex, no a 16 | `scripts/mod/sumversion.c:15-40` (cabecera: *«MD4 Message Digest Algorithm (RFC1320)»*), `:201-225` (`md4_final_ascii`); binario `scripts/mod/modpost` contiene los símbolos `md4_transform` y `get_src_version` |
| P2 | «el resultado tiene 16 caracteres hexadecimales en mayúsculas» | **REFUTADA.** MD4 emite 32 hex; `modpost` lo recorta a **23** | `scripts/mod/modpost.h:129` → `char srcversion[25]`; `modpost.c:1649-1650` pasa `sizeof(srcversion)-1` = 24 a `get_src_version`; `sumversion.c:223-224` `snprintf(out, len, "%08X%08X%08X%08X", ...)` |
| P3 | «se calcula sobre el contenido del módulo, excluyendo la sección de versiones» | **REFUTADA.** Se calcula sobre el **texto de los ficheros fuente** del módulo, con espacios y comentarios eliminados | `kernel/module/Kconfig:241-250`: *«contains a sum of the source files which made it»*; `sumversion.c:232-293` (`parse_file` salta `isspace()` y `/* */`), `:388-413` (`get_src_version` lee `<modulo>.mod` y los `.cmd`) |
| P4 | «el kernel lo lee en tiempo de carga y para esto» | **REFUTADA.** En `kernel/module/main.c` v7.1, `srcversion` aparece en **exactamente dos** líneas: se expone en sysfs y no se compara con nada | `main.c:606` `MODINFO_ATTR(srcversion);` · `main.c:1088` `&modinfo_srcversion,`. No hay ninguna comparación en `check_modinfo()` |
| P5 | «en este caso NO hay debug para este kernel» | **REFUTADA.** No hay DWARF, pero **sí hay `.BTF`**: 3.882.770 B, cabecera validada aritméticamente | `readelf -SW` → sección `[85] .BTF`; `CONFIG_DEBUG_INFO_BTF_MODULES=y`; `24 + 2501708 + 1381038 = 3882770` = tamaño exacto de la sección |

Y una sexta, sobre el propio encargo:

| # | Premisa | Veredicto |
|---|---|---|
| P6 | «Se tiene el código fuente de Linux v7.1.3 (commit `199c9959…`)» | **NO ENCONTRADO en este host.** Búsqueda exhaustiva (§7.3). Lo que hay es un árbol **7.1.0-rc1** y una extracción parcial de 24 `.c`. El tarball v7.1.3 no está en disco |

**`HECHO` — la afirmación de la premisa P6 y el estado observado del host se
contradicen.** Cualquier conclusión de este documento sobre «el fuente» está
deliberadamente limitada al árbol de desarrollo (`kernel-devel`), que sí es
de esta versión, y **no** al código fuente completo, que no está presente.

---

## 1. CÓMO SE CONSTRUYE UN MÓDULO DE KERNEL

### 1.a El sistema Kbuild/Makefile, y cómo decide qué compila

`NORMA` — `Documentation/kbuild/makefiles.rst` §*Overview*: el kernel tiene cinco
partes, y la jerarquía es explícita:

```
Makefile                    el Makefile de nivel superior
.config                     la configuración del kernel
arch/$(SRCARCH)/Makefile    el Makefile de la arquitectura
scripts/Makefile.*          reglas comunes de todos los kbuild Makefiles
kbuild Makefiles            existen en cada subdirectorio
```

`NORMA` — misma fuente, §*The kbuild files*:

> The preferred name for the kbuild files are `Makefile` but `Kbuild` can be used
> and **if both a `Makefile` and a `Kbuild` file exists, then the `Kbuild` file will
> be used.**

Es decir: **el nombre del fichero no decide nada; sólo su contenido.** Un
`Makefile` de subdirectorio y un `Kbuild` de subdirectorio se interpretan con la
misma gramática. La precedencia de `Kbuild` sobre `Makefile` sólo importa en la
raíz y en directorios con ambos ficheros.

`NORMA` — `makefiles.rst` §*Descending down in directories*: cada `Makefile` es
responsable **sólo de su propio directorio**; los subdirectorios se bajan
declarando `obj-$(CONFIG_X) += subdir/`. Si la rama resuelve a `m`, «nothing from
that directory will be linked into vmlinux».

`NORMA` — `scripts/Makefile.modpost:1-15` documenta el contrato de `modpost`, que
es la pieza que responde a 1.c y 1.d:

> 2) modpost is then used to … check that all exported symbols from the kernel
> are actually exported … and to create `Module.symvers`.

### 1.b Significado exacto de las variables de objetivo

`NORMA` — `makefiles.rst` §*Goal definitions* y §*Built-in object goals* /
§*Loadable module goals*:

| Forma | Significado | Cita |
|---|---|---|
| `obj-y += foo.o` | objeto **built-in**; se compila y se mete en `built-in.a` | `makefiles.rst` §*Goal definitions* |
| `obj-m += foo.o` | objeto **módulo cargable** | id. |
| `obj-$(CONFIG_FOO) += foo.o` | `$(CONFIG_FOO)` evalúa a `y` (built-in) o `m` (módulo). **«If CONFIG_FOO is neither y nor m, then the file will not be compiled nor linked»** | id. |
| `<mod>-y := a.o b.o` | fuentes del objeto compuesto `<mod>`; kbuild las compila y luego `$(LD) -r` sobre la lista | id. |
| `<mod>-$(CONFIG_FOO) += c.o` | **include condicional dentro de un objeto compuesto** | id. |
| `lib-y`, `extra-y`, `always-y`, `subdir-y/m`, `ccflags-y`, `subdir-ccflags-y` |.library, no-merge, incondicional, directorios sin objetos, flags por fichero | id., capítulos respectivos |

`HECHO` — en el caso de estudio, `drivers/gpu/drm/amd/amdgpu/Makefile` (8.638 B,
SHA256 `d97edea4ca36b80e5b9852d58bb4c53b78e3025370e281274c1de7cf2ac30b50`) contiene
literalmente:

```make
amdgpu-$(CONFIG_DRM_AMDGPU_CIK)+= cik.o cik_ih.o \
	dce_v8_0.o gfx_v7_0.o cik_sdma.o uvd_v4_2.o vce_v2_0.o      # líneas 81-82
amdgpu-$(CONFIG_DRM_AMDGPU_SI)+= si.o gmc_v6_0.o gfx_v6_0.o si_ih.o si_dma.o \
	dce_v6_0.o uvd_v3_1.o vce_v1_0.o                            # líneas 84-85
```

**Y las dos ramas están activas**: `HECHO` `grep '^CONFIG_DRM_AMDGPU_\(CIK\|SI\)='`
sobre `.config` → `CONFIG_DRM_AMDGPU_CIK=y` y `CONFIG_DRM_AMDGPU_SI=y`.

Esto refuta la lectura de que esos ficheros «están en el árbol pero el módulo no los
compila». **Sí los compila**: 424 símbolos `cik_*`/`si_*`/`gfx_v6_0_*`/`uvd_v3_1_*`/
`vce_v1_0_*`/`dce_v6_0_*` están definidos en el `.ko` (`nm --defined-only | grep -cE`
→ `424`). Lo que es cierto es la segunda mitad de la afirmación: **compilados y
enlazados ≠ ejecutados** en una RX550 (Polaris12/GFX8), porque la tabla de
descubrimiento no los selecciona.

**Un módulo puede linkar fuentes de varios directorios.** `NORMA` —
`Documentation/kbuild/modules.rst` §*Several Subdirectories*:

> kbuild can handle files that are spread over several directories. … The trick is
> to specify the directory relative to the kbuild file's location.

Con el ejemplo canónico `complex-y := src/complex_main.o` +
`complex-y += src/hal/hardwareif.o`.

`HECTO`/`INFERENCIA` — el mismo mecanismo, en `amdgpu`, lleva el módulo a cuatro
directorios distintos. `HECHO` — la lista de objetos expandida (§6.a) contiene
entradas con prefijo de ruta:

```
../pm/swsmu/smu13/smu13_*.o        ../pm/powerplay/hwmgr/vega20_*.o
../ras/rascore/ras_*.o             ../ras/ras_mgr/amdgpu_ras_*.o
```

**Consecuencia metodológica:** el conjunto de ficheros fuente que define
`srcversion` (§2) **no está contenido en un solo directorio**, y esto no es un
detalle: es la razón por la que la comparación «Makefile a Makefile» (§3.b) no
puede cubrir el sistema de build de amdgpu, que se reparte en 6 ficheros
`Makefile` incluir.

**Sobre `ccflags-y` y `EXTRA_CFLAGS`.** `HECHO` — el Makefile de amdgpu usa:

```make
ccflags-y := -I$(FULL_AMD_PATH)/include/asic_reg …        # línea 34
subdir-ccflags-y += -Wno-override-init                   # línea 48
subdir-ccflags-$(CONFIG_DRM_AMDGPU_WERROR) += -Werror     # línea 49
```

`NORMA` — `makefiles.rst` §*Compilation flags*: `ccflags-y` **«apply only to the
kbuild makefile in which they are assigned»**; `subdir-ccflags-y` tiene efecto
**«for the kbuild file where they are present and all subdirectories»**, y se
añaden **antes** que los no-`subdir`. `CFLAGS_$@` da opciones por fichero y **tiene
prioridad sobre `ccflags-remove-y`**.

**`EXTRA_CFLAGS` no aparece en la documentación del kernel v7.1 como variable de
kbuild.** `HECHO` — `Documentation/kbuild/kbuild.rst` §*Environment variables* lista
`KCFLAGS`, `CFLAGS_MODULE`, `CFLAGS_KERNEL`, `LDFLAGS_MODULE`, `KCPPFLAGS`,
`KAFLAGS`, `KRUSTFLAGS` y ninguna `EXTRA_CFLAGS`. `NOT_DETERMINED` — si
`EXTRA_CFLAGS` sigue existiendo como alias de `KCFLAGS` en 7.1.3, no lo
determiné; busqué en `kbuild.rst` y `makefiles.rst` y no aparece. **Lo que sí es
normativo es `KBUILD_CFLAGS`, que el Makefile de nivel superior posee y usa para
todo el árbol** (`makefiles.rst` §*ccflags-y*).

### 1.c Qué es `.modpost` y por qué se ejecuta

`NORMA` — `scripts/Makefile.modpost:1-15`:

> … 2) modpost is then used to check that all exported symbols from the kernel are
> actually exported, check that every module exports at least one symbol, warn about
> modules with no exported symbols, and create `Module.symvers`.

`NORMA` — `Documentation/kbuild/modules.rst` §*Symbols and External Modules*:

> When building an external module, the build system needs access to the symbols
> from the kernel to check if all external symbols are defined. This is done in the
> MODPOST step. modpost obtains the symbols by reading `Module.symvers` from the
> kernel source tree. During the MODPOST step, a **new `Module.symvers` file will be
> written** containing all exported symbols from that external module.

`HECHO` — `scripts/Makefile.modpost:43-54` da la invocación real:

```make
modpost-args =  $(if $(CONFIG_MODULES),-M) \
                $(if $(CONFIG_MODVERSIONS),-m) \
                $(if $(CONFIG_BASIC_MODVERSIONS),-b) \
                $(if $(CONFIG_EXTENDED_MODVERSIONS),-x) \
                $(if $(CONFIG_MODULE_SRCVERSION_ALL),-a)  … \
                -o $@
```

`HECHO` — los ficheros que lo componen, `scripts/mod/Makefile`:
`modpost-objs := modpost.o file2alias.o sumversion.o symsearch.o`.
Es decir: **`modpost` es el que calcula `srcversion`** (vía `sumversion.o`), y el
que genera los alias PCI leyendo `struct pci_device_id` (`file2alias.c`).

### 1.d Los pasos exactos

`INFERENCIA` a partir de `NORMA` (`makefiles.rst` §*Built-in object goals*,
`modules.rst` §*Module Versioning*, `scripts/Makefile.modpost`), con los dos modos
de salida distinguidos:

```
FUENTE (.c)
  │
  ├─ obj-y ──────────────► .o ──$(AR) rcSTP──► built-in.a ──┐
  │                                                          ├─► MODPOST ──► vmlinux
  └─ obj-m ── .o ──$(LD -r)─► <mod>.o ──$(LD) -T .o.cmd──► <mod>.ko
                                                              │
                        .o.cmd / <mod>.mod  ◄──────────────────┘
                                │
                                ▼
                     get_src_version()  ──►  Module.symvers
                                              modules.order
```

Los dos puntos que importan para verificar:

1. **`<mod>.mod`** — `HECHO` `sumversion.c:395-396`: *«objects for a module are
   listed in the first line of *.mod file»*. `get_src_version()` lo lee. Por tanto
   **el fichero `.mod` es a la vez la entrada del hash y la lista autoritativa de
   objetos** — una misma fuente de verdad para dos propósitos.
2. **`.o.cmd`** — `HECHO` `sumversion.c:302-303`: *«We have dir/file.o. Open
   dir/.file.o.cmd, look for `source_` and `deps_` line to figure out source
   files»*. Kbuild escribe ahí la línea de compilación completa, y con ella la
   ruta del `.c`.

**Ambos ficheros sólo existen en un árbol de construcción, no en un `kernel-devel`.**
`HECHO` — `/usr/src/kernels/7.1.3-…/` no contiene `modules.order` ni ningún `.mod`.
Esto es la razón operativa de por qué `srcversion` **no se puede recalcular** desde
un `kernel-devel` (§3.e).

---

## 2. `srcversion` — EL MECANISMO CENTRAL

### 2.a El algoritmo exacto

`NORMA` — la respuesta a la pregunta del encargo, leyendo la implementación:

**Algoritmo: MD4 (RFC 1320), 128 bits, salida en 32 hexadecimales mayúsculas,
recortada por el buffer del llamante.**

`HECHO` — `scripts/mod/sumversion.c`:

| Elemento | Línea | Contenido |
|---|---|---|
| Identificación | 15-40 | *«MD4 Message Digest Algorithm (RFC1320)»*, con inicialización `0x67452301 / 0xefcdab89 / 0x98badcfe / 0x10325476` (líneas 164-167) — los IV estándar de MD4 |
| Transformada | 90-154 | 3 rondas: `F(x,y,z)=(x&y)\|(~x&z)`, `G(x,y,z)=(x&y)\|(x&z)\|(y&z)`, `H(x,y,z)=x^y^z`, con las constantes `0x5A827999` y `0x6ED9EBA1` (líneas 70-71) — las de MD4, no las de MD5/SHA1 |
| Salida | 223-224 | `snprintf(out, len, "%08X%08X%08X%08X", hash[0],hash[1],hash[2],hash[3])` |
| Recorte | `modpost.h:129` | `char srcversion[25]` → `modpost.c:1650` pasa `sizeof(srcversion)-1` = **24** → `snprintf` escribe como máximo **23** hex + NUL |

`HECHO` — **comprobación aritmética contra el artefacto**, que cierra la cadena:

```
modinfo -F srcversion ./amdgpu.ko   →  D68004925455E20A24C2B87
longitud                            =  23        (medido con python3: len == 23)
predicho por srcversion[25]         =  23        (24 - 1 por el NUL)
hash[0]=D6800492  hash[1]=5455E20A  hash[2]=24C2B87(7 nibbles de 8)
```

`HECHO` — confirmación independiente desde el **binario**, no desde el fuente:

```
$ nm /usr/src/kernels/7.1.3-200.nobara.fc44.x86_64/scripts/mod/modpost | grep -i md4
0000000000409520 t md4_transform
0000000000409a70 t md4_update.constprop.0
0000000000409d20 T get_src_version
```

**Sobre qué datos se calcula — `HECHO`, y es lo contrario de lo que suponía el
encargo.** No es el binario. `get_src_version()` (líneas 388-413):

1. Lee `<modulo>.mod`, toma la primera línea: la lista de objetos.
2. Por cada `.o`, llama a `parse_source_files()` (líneas 304-385), que abre
   `.<obj>.cmd` y extrae las líneas `source_…` y `deps_…`.
3. De `deps_` **sólo acepta los ficheros del mismo directorio que el objeto**
   (línea 367: `if ((strstr(line, dir)+strlen(dir)-1) == strrchr(line, '/'))`).
4. `parse_file()` (líneas 258-293) normaliza el texto: **elimina `isspace()`**,
   **elimina comentarios `/* … */`**, **colapsa continuaciones `\`+newline**, y
   **trata cada literal de cadena como una unidad indivisible** (líneas 278-281,
   `parse_string`).

`INFERENCIA` (base: `sumversion.c:258-293` + `:304-374`) — esto tiene tres
consecuencias que gobiernan todo lo que sigue:

- **Un cambio de espaciado, reformateo o comentario NO cambia `srcversion`.**
- **Un cambio en una cabecera de OTRO directorio (p. ej. `include/linux/…`,
  `amdkfd/*.h`) NO cambia `srcversion`**, porque el filtro de la línea 367 la
  descarta. Ésta es la razón principal por la que dos binarios con **igual**
  `srcversion` pueden **no** ser idénticos.
- **`srcversion` es ciego a la configuración, a la toolchain, a los flags y al
  orden de enlazado.** No los ve.

### 2.b Dónde lo lee el kernel — y para qué

`HECHO` — en `kernel/module/main.c` v7.1, `srcversion` aparece en **dos** líneas:

```c
606:  MODINFO_ATTR(srcversion);            /* macro que declara el atributo sysfs */
1088:     &modinfo_srcversion,             /* registro en modinfo_attrs[] */
```

La macro `MODINFO_ATTR` (líneas 585-605) genera un `setup` que hace
`kstrdup` del valor, un `show` que lo imprime, y un `test` de existencia. El
atributo resultante es de **modo `0444`** (sólo lectura).

`INFERENCIA` (base: las dos únicas apariciones + `check_modinfo()` en 2633-2657) —
**el kernel no valida `srcversion` en tiempo de carga.** Se limita a copiar la
cadena de `.modinfo` a `mod->srcversion` y a publicarla. No participa de ninguna
decisión de carga. Consecuencia: **un `srcversion` incorrecto o ausente no impide
cargar un módulo**, y por tanto **`modinfo` leyéndolo no añade ninguna garantía
de carga**.

`NOT_AVAILABLE` en este host: no pude leer `/sys/module/amdgpu/srcversion` para
demostrar la exposición en vivo — las reglas de `deny` de `opencode.json` cubren
`/sys` y el motor devolvió `permission.rejected`. La demostración queda por la
fuente, que es inequívoca.

### 2.c Por qué `srcversion` NO identifica una versión de código fuente

De §2.a se sigue directamente, y conviene enunciarlo sin eufemismo porque es la
principal fuente de error en este tema:

| `srcversion` depende de | `srcversion` NO depende de |
|---|---|
| Texto de los `.c` listados en `<mod>.mod` | La toolchain (gcc, ld, versión) |
| Textos de las cabeceras **del mismo directorio** que cada `.o` | `KBUILD_BUILD_TIMESTAMP`, `KBUILD_BUILD_USER/HOST` |
| — (los comentarios y espacios se eliminan) | `.config` / `CONFIG_*` |
| — | Los flags de compilación (`-O2`, `-march=`, LTO, CFI…) |
| — | El orden de enlace, el linker script |
| — | Las cabeceras de **otros** directorios |

`INFERENCIA` — las dos mitades del encargo se resuelven así:

- **Para COMPARAR builds**: sí, es una firma estable y barata. Dos `.ko` con
  distinto `srcversion` tienen necesariamente distinto conjunto de ficheros fuente.
- **Para ATRIBUIR un commit**: **no, y es categórico.** `srcversion` es una
  función del *contenido textual*, no de la historia de VCS. No hay forma de
  invertir MD4 hacia un commit. Y como no depende de comentarios ni de
  espacios, **dos commits distintos con el mismo contenido de los `.c` relevantes
  dan el mismo `srcversion`** — dos commits que sólo difieren en un `.h` de otro
  directorio, en un `Kconfig`, o en la configuración, también.

`HECHO` — el `Kconfig` lo dice con sus palabras, y es la formulación más
fiable disponible (`kernel/module/Kconfig:241-250`):

> Modules which contain a `MODULE_VERSION` get an extra "srcversion" field
> inserted into their modinfo section, **which contains a sum of the source files
> which made it. This helps maintainers see exactly which source was used to build
> a module** (since others sometimes change the module source without updating the
> version).

Nota el objetivo declarado: **ver qué fuente se usó**, no *identificar* una revisión.
Es una herramienta de *trazabilidad de fuente*, no de *identidad de build*.

### 2.d `vermagic`

`NORMA` — `include/linux/vermagic.h` (48 líneas, íntegro en el árbol de desarrollo;
SHA256 idéntico al de upstream v7.1):

```c
#define VERMAGIC_STRING                        \
        UTS_RELEASE " "                        \
        MODULE_VERMAGIC_SMP MODULE_VERMAGIC_PREEMPT    \
        MODULE_VERMAGIC_MODULE_UNLOAD MODULE_VERMAGIC_MODVERSIONS  \
        MODULE_ARCH_VERMAGIC                   \
        MODULE_RANDSTRUCT
```

Composición exacta, con los valores que toma en este host (`HECHO`):

| Componente | Fuente | Valor aquí |
|---|---|---|
| `UTS_RELEASE` | `include/generated/utsrelease.h` | `7.1.3-200.nobara.fc44.x86_64` |
| (separador) | espacio literal | ` ` |
| `MODULE_VERMAGIC_SMP` | `#ifdef CONFIG_SMP` | `SMP ` (`.config`: `CONFIG_SMP=y`) |
| `MODULE_VERMAGIC_PREEMPT` | `PREEMPT_RT` / `CONFIG_PREEMPT_BUILD` | `preempt ` |
| `MODULE_VERMAGIC_MODULE_UNLOAD` | `#ifdef CONFIG_MODULE_UNLOAD` | `mod_unload ` |
| `MODULE_VERMAGIC_MODVERSIONS` | `#ifdef CONFIG_MODVERSIONS` | **vacío** (§2.e) |
| `MODULE_ARCH_VERMAGIC` | `asm/vermagic.h` | vacío en x86_64 |
| `MODULE_RANDSTRUCT` | `#ifdef RANDSTRUCT` | vacío |

`HECHO` — `modinfo -F vermagic` → `7.1.3-200.nobara.fc44.x86_64 SMP preempt mod_unload `
(el espacio final es real y cuenta).

**Lo que ocurre si no coincide.** `NORMA` — `kernel/module/main.c:2633-2657`:

```c
static int check_modinfo(struct module *mod, const struct load_info *info, int flags)
{
        const char *modmagic = get_modinfo(info, "vermagic");
        if (flags & MODULE_INIT_IGNORE_VERMAGIC) modmagic = NULL;
        /* This is allowed: modprobe --force will invalidate it. */
        if (!modmagic) { err = try_to_force_load(mod, "bad vermagic"); if (err) return err; }
        else if (!same_magic(modmagic, vermagic, info->index.vers)) {
                pr_err("%s: version magic '%s' should be '%s'\n", info->name, modmagic, vermagic);
                return -ENOEXEC;
        }
```

`HECHO` — el mensaje real es **`version magic '%s' should be '%s'`** y el retorno es
`-ENOEXEC` → la carga falla. `SECUNDARIO` — `man 8 insmod`, opción `-f`:
*«tells the kernel to ignore the module version and vermagic fields when
loading … this can lead to memory corruption, system crashes and data loss»*.

**Detalle que casi nadie conoce y que cambia la lectura de `vermagic`.**
`HECHO` — `kernel/module/version.c:88-97`:

```c
/* First part is kernel version, which we ignore if module has crcs. */
int same_magic(const char *amagic, const char *bmagic, bool has_crcs)
{
        if (has_crcs) { amagic += strcspn(amagic, " "); bmagic += strcspn(bmagic, " "); }
        return strcmp(amagic, bmagic) == 0;
}
```

`INFERENCIA` — con `CONFIG_MODVERSIONS=y` la comparación **sólo mira el primer
token** (hasta el primer espacio), es decir únicamente la versión del kernel: los
flags `SMP`/`preempt`/`mod_unload` se **ignoran**. Sin `MODVERSIONS` (§2.e) es un
`strcmp` de la cadena entera, espacio final incluido. **En este host aplica la
segunda rama**, así que `vermagic` sí es una comprobación estricta aquí.

### 2.e `CONFIG_MODVERSIONS` y la sección `__versions`

`NORMA` — `struct modversion_info`, `include/linux/module.h:38-41`:

```c
struct modversion_info {
        unsigned long crc;
        char name[MODULE_NAME_LEN];
};
```

`NORMA` — `Documentation/kbuild/modules.rst` §*Module Versioning*:

> Module versioning is enabled by the `CONFIG_MODVERSIONS` tag, and is used as a
> simple ABI consistency check. A **CRC value of the full prototype** for an
> exported symbol is created. When a module is loaded/used, the CRC values
> contained in the kernel are compared with similar values in the module; if they
> are not equal, the kernel refuses to load the module.

**Y el mecanismo del mensaje de error** — `HECHO`, `kernel/module/version.c:14-68`:

```c
        if (versions[i].crc == crcval) return 1;
        pr_debug("Found checksum %X vs module %lX\n", crcval, versions[i].crc);
        goto bad_version;
…
bad_version:
        pr_warn("%s: disagrees about version of symbol %s\n", info->name, symname);
        return 0;
```

`INFERENCIA` — `pr_warn`, no `pr_err`, y `return 0` → `resolve_symbol()` convierte
eso en `fsa.sym = ERR_PTR(-EINVAL)`, `simplify_symbols()` cuenta el error y
`load_module()` aborta. El aviso aparece en `dmesg` como `WARN`, no como error fatal.

**Dos matices que el texto de la documentación no cubre**, y que sí están en la fuente:

- `HECHO` `version.c:44-45`: `/* No versions at all? modprobe --force does this. */`
  → `if (versindex == 0) return try_to_force_load(mod, symname) == 0;`
  Un módulo **sin** `__versions` no falla: pide `--force`.
- `HECHO` `version.c:52-54`: si el símbolo no aparece en `__versions`, hace
  `pr_warn_once("%s: no symbol version for %s\n", …)` y **`return 1`** — acepta.
  Sólo hayMismatch cuando el símbolo está presente y el CRC difiere.

### 2.f `CONFIG_MODVERSIONS` en ESTE host: desactivado

`HECHO` — `/usr/src/kernels/7.1.3-200.nobara.fc44.x86_64/.config:1087`:

```
# CONFIG_MODVERSIONS is not set
```

`HECHO` — `CONFIG_HAVE_ASM_MODVERSIONS=y` (línea 940) es la capacidad de la
arquitectura, no la activación. No confundir: sólo `CONFIG_MODVERSIONS` activa el
mecanismo.

`HECHO` — `Makefile.modpost:45` `$(if $(CONFIG_MODVERSIONS),-m)` → `modpost` **no**
recibe `-m`, luego no hay resolución de CRCs. Y `kernel/module/Makefile`:
`obj-$(CONFIG_MODVERSIONS) += version.o` → **`version.c` ni siquiera se compila**,
así que `check_version()` no existe como código en este kernel.

`HECHO` — consecuencia observable, tres:

1. El `.ko` (90 secciones) **no tiene sección `__versions`**.
2. `Module.symvers` lista los símbolos de amdgpu/amdxcp con CRC `0x00000000`:
   `0x00000000  isp_user_buffer_alloc  drivers/gpu/drm/amd/amdgpu/amdgpu  EXPORT_SYMBOL`
   — coherente con `modules.rst`: *«For a kernel build without CONFIG_MODVERSIONS
   enabled, the CRC would read 0x00000000»*.
3. `symversion(base, idx)` devuelve `NULL` (`main.c:332-338`), y
   `check_version()` es un `static inline { return 1; }`
   (`kernel/module/internal.h`, rama `#else`).

**`INFERENCIA` — el apartado 2.e del encargo describe un mecanismo que en este
kernel no está activo.** Es `NORMA` (está en la fuente) pero es `NOT_APPLICABLE`
aquí. En consecuencia: **el error «disagrees about version of symbol» no puede
producirse en este host**, y **`vermagic` es aquí la única comprobación de
compatibilidad que el kernel aplica a un módulo**. Eso fija la regla práctica: en un
`kernel-devel` con `MODVERSIONS=n`, cargar un `.ko` ajeno es mucho menos
protegido de lo que sugiere la documentación.

### 2.g Por qué `amdgpu` tiene `srcversion` sin tener `version:`

`HECHO` — el campo `version` **no existe** en el `.modinfo` de `amdgpu.ko`
(`modinfo` lista: alias, author, depends, description, filename, firmware,
import_ns, intree, license, name, parm, retpoline, sig_*, signature, signer,
srcversion, vermagic — sin `version`).

`HECHO` — pero `modpost.c:1646-1651` condiciona el cálculo:

```c
if (!mod->is_vmlinux) {
        version = get_modinfo(&info, "version");
        if (version || all_versions)
                get_src_version(mod->name, mod->srcversion, sizeof(mod->srcversion) - 1);
}
```

`HECHO` — `all_versions` lo pone la opción `-a` (`modpost.c:2320`), y
`scripts/Makefile.modpost:48` dice `$(if $(CONFIG_MODULE_SRCVERSION_ALL),-a)`.
`.config:1088` → `CONFIG_MODULE_SRCVERSION_ALL=y`.

**Cadena completa y cerrada:** `CONFIG_MODULE_SRCVERSION_ALL=y` → `Makefile.modpost:48`
pasa `-a` → `modpost.c:2320` `all_versions = true` → `modpost.c:1648` cumple la
guarda pese a no haber `MODULE_VERSION()` → `get_src_version()` corre →
`add_srcversion()` (`modpost.c:2027-2034`) emite
`MODULE_INFO(srcversion, "…")` → aparece en `.modinfo`.

`HECHO` — dos campos más de `.modinfo` que sí sonesejos de identidad de build:
`file=` **no está** (los módulos in-tree tienen `KBUILD_MODFILE` vacío;
`HECHO` `modinfo -F file` → vacío), y `retpoline: Y` e `intree: Y` sí.

---

## 3. LA PREGUNTA CENTRAL: ¿puedo VERIFICAR que un `.ko` corresponde a un fuente?

### 3.a `modinfo`

`HECHO` — el `.modinfo` de `amdgpu.ko` tiene 1.117 entradas de campo, de 19 nombres
distintos. Los relevantes para identidad:

| Campo | Valor / conteo | Qué establece |
|---|---|---|
| `vermagic` | `7.1.3-200.nobara.fc44.x86_64 SMP preempt mod_unload ` | compilado contra un kernel con esta `UTS_RELEASE` y estos flags |
| `srcversion` | `D68004925455E20A24C2B87` (23 hex) | resumen MD4 del texto fuente (§2.a) |
| `alias` | 311 entradas `pci:v00001002d0000…` | los `pci_device_id` que compila (lo genera `file2alias.c`) |
| `depends` | 13 módulos | el grafo de dependencias resuelto |
| `intree` | `Y` | marca que emite la construcción. `NOT_DETERMINED` — no localicé su origen en `Makefile.modfinal`/`Makefile.modpost` del árbol de desarrollo, así que **no** afirmo que un módulo out-of-tree no pueda declararla |
| `retpoline` | `Y` | que se compiló con retpolines |
| `sig_id`/`signer`/`sig_key` | `PKCS#7` / `Build time autogenerated kernel key` / `6F:81:0A:…` | firmado por la clave de compilación de la distro (§5) |
| `license`, `author`, `description` | literales del fuente | presentes, triviales |
| `file` | **ausente** | in-tree ⇒ sin ruta de origen |
| `version` | **ausente** | sin `MODULE_VERSION()` |

`SECUNDARIO` — `man 8 modinfo`: *«Common fields … include author, description,
license, parm, depends, and alias»*; `-F field` para extraer uno; `-k kernel` para
informar de otro kernel que no esté en ejecución.

**Qué prueba `modinfo`**: que el `.ko` declara una `vermagic` compatible y un
`srcversion`; que expone una API de parámetros y un conjunto de IDs de dispositivo
consistentes con amdgpu.

**Qué NO prueba `modinfo`**:
- Nada del **contenido** de los `.c` (salvo el `srcversion`, que es un hash, no un
  contenido legible, y no cubre `.h` de otros directorios).
- Nada de la **`.config` real** ni de los flags de compilación.
- Nada de la **toolchain**.
- `intree: Y` **no** es prueba de procedencia. `HECHO` — el valor observado es `Y`.
  `NOT_DETERMINED` — **no localicé el origen de este campo**: no aparece en
  `scripts/Makefile.modfinal` ni en `scripts/Makefile.modpost` del árbol de
  desarrollo, y `grep -rn '_intree' scripts/` no devuelve nada. Por tanto **no
  afirmo** ni que sea falsificable por un módulo out-of-tree ni que no lo sea. Lo
  único establecido es que el campo dice `Y`. Usarlo como evidencia de nada es
  unjustificado.

### 3.b Comparar el `Makefile` de Kbuild byte a byte

`HECHO` — se comparó y **coincide**:

```
d97edea4ca36b80e5b9852d58bb4c53b78e3025370e281274c1de7cf2ac30b50
  /usr/src/kernels/7.1.3-200.nobara.fc44.x86_64/drivers/gpu/drm/amd/amdgpu/Makefile
  8.638 bytes
```

**Qué prueba**: que las *reglas de compilación declaradas* para este módulo son
bit a bit las mismas. Es un resultado real y útil.

**Qué NO prueba — y el inventario es largo**:

1. **No cubre el contenido de ni un `.c`.** El Makefile no contiene código.
2. **No cubre el resto del sistema de build.** `HECHO` — el módulo se define en
   **6 ficheros**: `amdgpu/Makefile`, `amdkfd/Makefile`, `acp/Makefile`,
   `pm/Makefile`, `display/Makefile`, `ras/Makefile` (+ `pm/swsmu/*`,
   `pm/powerplay/*`, `ras/ras_mgr`, `ras/rascore`). Comparar uno solo deja el
   resto sin verificar, y el `srcversion` los cubre a todos (§2.a).
3. **No cubre la `.config` que se usó.** Las 8 ramas `amdgpu-$(CONFIG_…)` de ese
   Makefile dependen de valores que no están en el Makefile.
4. **No cubre los flags** de `ccflags-y` heredados, ni `KBUILD_CFLAGS` del
   Makefile superior, ni `CFLAGS_MODULE`.
5. **No cubre la toolchain** ni el timestamp.
6. **No cubre los parches de la distribución** (§5).

### 3.c Comparar la lista de símbolos

`HECHO` — `nm --defined-only amdgpu.ko` → **64.460** símbolos definidos, de los
que **34.773** son de texto (`T`/`t`). `.symtab` con 65.613 entradas (1.574.712 B, 24 B/símbolo; `sh_info`=49.354 es el índice del último símbolo local, no el total). exports:
**4** símbolos en `__ksymtab` (`isp_user_buffer_alloc`, `isp_user_buffer_free`,
`isp_kernel_buffer_alloc`, `isp_kernel_buffer_free`), que casan exactamente con las
4 líneas de `Module.symvers` con módulo `drivers/gpu/drm/amd/amdgpu/amdgpu`.

Procedimiento contra el fuente: extraer del fuente las funciones no estáticas
definidas y comprobar que cada una aparece en `nm`. Available sin privileges.

**Y un resultado medido que corrige la intuición sobre esta técnica.** `HECHO` — con
el extractor de §6.c aplicado a `amdgpu_discovery.c` (66 funciones de nivel superior
encontradas) y cruzado contra `nm --defined-only` del `.ko`:

```
funciones del fuente ausentes del .ko        : 39
  de ellas, declaradas `static`               : 38
```

`INFERENCIA` — la causa es **inlineo**, no versión ni borrado. `HECHO` — las tres
primeras son `static` en el árbol de referencia:
`amdgpu_discovery_get_gfx_info` (`static int`, línea 1721),
`amdgpu_discovery_get_mall_info` (`static int`, 1831),
`amdgpu_discovery_calculate_checksum` (`static uint16_t`, 404). Al inlinarlas no
queda símbolo fuera de línea en `.symtab`.

**Asimetría que hay que tener presente al usar esta técnica:**

| Dirección | Fiabilidad | Motivo |
|---|---|---|
| símbolo del `.ko` → función del fuente | **fiable** | un símbolo global no desaparece por inlineo |
| función del fuente → símbolo del `.ko` | **falsos positivos sistemáticos** | toda función `static` inlineada no deja símbolo |

**Qué revela**: ficheros **ausentes** o renombrados, funciones eliminadas,
divisiones/divisoraciones masivas, cambios de nombre. La comparación
`Module.symvers` ↔ `__ksymtab` es además una **comprobación de integridad**
independiente del código fuente.

**Qué NO revela — el límite es estructural, no de esfuerzo**:

- **Un cambio dentro de una función no cambia el conjunto de símbolos.** Es la
  limitación central: unabucket de distinta CONSTante, un `if` invertido, un
  coeficiente, un número de línea o un `printk` eliminado son **invisibles** a
  esta técnica. Sólo vería el cambio si además moviera el tamaño de la función.
- No ve datos, ni orden, ni flags, ni toolchain, ni configuración.
- `.cold` twins: `HECHO` el `.ko` contiene `cik_asic_reset.cold` además de
  `cik_asic_reset` — duplicados del optimizador, que hay que filtrar o inflan el
  recuento.

### 3.d Comparar el conjunto de cadenas

`HECHO` — el caso de estudio: `strings -a amdgpu.ko | grep -F "UVD not responding,
trying to reset the VCPU"` devuelve la cadena, **4 apariciones**. Es la clase de
prueba que permite confirmar la presencia de un mensaje de `DRM_ERROR`/`printk`.

**Límite medido, no supuesto.** `HECHO` — sobre `amdgpu_discovery.c`:

```
literales de cadena >= 6 caracteres en el fuente : 209
presentes como línea completa en el .ko           :  53   (25,4 %)
ausentes                                          : 156   (74,6 %)
```

**Por qué faltan.** De la muestra de ausentes hay dos categorías distintas y
consequences opuestas:

| Categoría | Ejemplos | Interpretación |
|---|---|---|
| Nombres de cabecera (`amdgpu.h`, `amdgpu_isp.h`, `amdgpu_vkms.h`…) | no están como cadenas imprimibles | viven en `.BTF`/DWARF, no en `.rodata` |
| Mensajes de rutas de código no compiladas (`couldn't load firmware \`, `Couldn't create IP link %s in IP Die:%s`) | ausentes | evidencia de que la ruta no entró en el binario |

`HECHO` — la **utilidad inversa** de los literales ausentes: si un conjunto
característico de literales de un `CONFIG_` concreto está **ausente**, eso es
información sobre qué rama se compiló. Es una señal débil y necesita fuente de la
misma versión para ser interpretable.

**El límite que hay que explicitar: una cadena repetida N veces no identifica N
ficheros.** `HECHO` — `UVD not responding…` aparece **4 veces** en el `.ko`, y en
`linux-opt` (7.1.0-rc1) el literal aparece en **al menos 4 ficheros distintos**
(`uvd_v3_1.c:394`, `uvd_v4_2.c:362`, `uvd_v5_0.c:400`, `uvd_v6_0.c:817`).
`INFERENCIA` — el recuento **coincide**, pero es una **coincidencia que no
distingue** entre «4 ficheros diferentes» y «1 fichero que lo emite 4 veces», y
tampoco acredita que sean *esos* cuatro. Es exactamente el salto prohibido
`a métrica → a constructo`: el número de apariciones de una cadena es un
`OBSERVATION`, y atribuirle un origen es un salto no hecho.

### 3.e Reconstruir y comparar `srcversion` — y por qué casi nunca es reproducible bit a bit

**Lo que hace falta** (de `modules.rst` §*How to Build External Modules* y
`kbuild.rst`):

| Requisito | Fuente | Estado en este host |
|---|---|---|
| Árbol fuente completo con los `.c` | `modules.rst`: *«you must have a prebuilt kernel available that contains the configuration and header files»*; y el `.c` hace falta para compilar | **`NOT_FOUND`** (§0 P6) |
| `.config` correcta | `Makefile.modpost`, `.config` | `HECHO` presente, `SHA256 43f1eec5…`, **idéntico** a `/boot/config-$(uname -r)` |
| Misma toolchain | `.comment` del `.ko` | `HECHO` `GCC: (GNU) 16.1.1 20260515 (Red Hat 16.1.1-2)` — coincide con `/proc/version` |
| `Module.symvers` | `modules.rst` §*Symbols and External Modules* | `HECHO` presente (2.334.430 B) |
| Mismo `KBUILD_BUILD_TIMESTAMP` | `kbuild.rst` §*KBUILD_BUILD_TIMESTAMP* | `HECHO` `Sat Jul 4 14:59:29 UTC 2026` |
| `KBUILD_BUILD_USER` / `KBUILD_BUILD_HOST` | `kbuild.rst` | `HECHO` `mockbuild@559670082b9946b78405ee85a5345150` |
| Árbol con los `.mod` y `.cmd` | `sumversion.c:302,396` | **`NOT_FOUND`** — un `kernel-devel` no los trae |

**Ese último punto es el obstáculo real y es estructural, no de golpecitos.**

`INFERENCIA` (base: `sumversion.c:304-374` requiere `.<obj>.cmd`, y
`:396` requiere `<modulo>.mod`) — **para recalcular `srcversion` hacen falta los
ficheros de interdepencias de kbuild, que sólo existen en el árbol de construcción
donde se compiló el módulo.** Un `kernel-devel` no permite recalcular ningún
`srcversion`. Reconstruir desde cero, en cambio, **regenera** esos ficheros y sí
produce un `srcversion` — pero entonces ya no estás *recalculando*, estás
*reconstruyendo*, ysubjecto a todos los factores de no-reproducibilidad.

`NOT_DETERMINED` — **cuánto** diverge una reconstrucción. `kbuild.rst` documenta
`KBUILD_BUILD_TIMESTAMP`, `KBUILD_BUILD_USER`, `KBUILD_BUILD_HOST` y
`INSTALL_MOD_STRIP`; y hay factores no documentados en `kbuild.rst` que dependen
de la versión y la distro. Los **documentados** que sin duda cambian el
binario: los tres `KBUILD_BUILD_*` y `INSTALL_MOD_STRIP` (que con `1` usa
`--strip-debug`). No los medí ni comprobé sus valores de build. La razón por la
que `srcversion` (y no SHA256) es la comparación *definitiva* es precisamente que
**es immune a todos ellos**: no ve toolchain, ni flags, ni timestamp, ni rutas.

### 3.f LA ESCALERA DE EVIDENCIA

Cada peldaño se nombra para que una afirmación quede **en su peldaño** y no por
encima. El nombre de estado es lo que se escribe en un informe.

| # | PELDAÑO | TÉCNICA | ESTADO SI COINCIDE | **QUÉ PRUEBA** | **QUÉ NO PRUEBA** |
|---|---|---|---|---|---|
| **E0** | `NAME_ONLY` | el fichero se llama `amdgpu.ko` | `UNVERIFIED` | que existe un fichero con ese nombre | **nada**. Ni una afirmación. No es evidencia |
| **E1** | `VERMAGIC_COMPATIBLE` | `modinfo -F vermagic` vs `uname -r` + flags | `KERNEL_ABI_COMPATIBLE` | que el kernel que lo compiló tenía esta `UTS_RELEASE` y estos flags de compilación | nada del código; nada de la config; nada de la toolchain; nada de los flags. Lo compararía un `.ko` de otra distro con el mismo `vermagic` |
| **E2** | `TOOLCHAIN_CONSISTENT` | `.comment` vs `/proc/version` | `TOOLCHAIN_CONSISTENT` | que el ensamblador que lo emitió es el mismo gcc del kernel en ejecución | nada del código. `.comment` lo escribe el ensamblador, no el enlazador: **no** acredita el `ld`, ni el orden de enlace, ni la config |
| **E3** | `KBUILD_RULES_IDENTICAL` | SHA256 del `Makefile` de Kbuild | `BUILD_RULES_IDENTICAL` | que las reglas declaradas de compilación de ese módulo son bit a bit las mismas | el contenido de **ningún** `.c`; la `.config` real; los flags; la toolchain; los otros 5 Makefiles del módulo; los parches de la distro |
| **E4** | `BRANCH_SET_CONSISTENT` | los `CONFIG_` de las ramas `$(…)` coinciden con `.config` | `BRANCH_SET_CONSISTENT` | **qué ramas del Makefile se tomaron** (aquí: CIK y SI **sí**; corroborado por 424 símbolos `cik_*`/`si_*` en el `.ko`) | que los `.c` de esas ramas sean los del tarball; nada de la toolchain; nada de los flags; nada de los `.c` de otros directorios |
| **E5** | `STRUCTURE_CONSISTENT` | conjunto de símbolos de `nm` vs. funciones del fuente | `STRUCTURE_CONSISTENT` | que existen esas funciones con esos nombres; detecta ficheros ausentes, renombrados, borrados | **cualquier cambio dentro de una función**: ni constantes, ni un `if` invertido, ni un `printk` eliminado, ni flags, ni toolchain, ni config. Y en la dirección *fuente→símbolo*, **toda función `static` inlineada** (medido: 38 de 39) |
| **E6** | `MESSAGING_CONSISTENT` | `strings` vs. literales del fuente | `MESSAGING_CONSISTENT` | que los mensajes `printk`/`DRM_ERROR` presentes en el `.ko` están en el fuente | **medido: 74,6 % de los literales del fuente no están** (53/209); una cadena repetida N veces **no** identifica N ficheros; una cadena presente no prueba que su ruta se ejecute |
| **E7** | `TYPE_SIGNATURE_CONSISTENT` | `.BTF` vs. tipos del fuente | `TYPE_SIGNATURE_CONSISTENT` | firmas de función, `struct`, `enum`, `typedef` (`.BTF` de 3.882.770 B validado) | **nada del cuerpo** de las funciones; nada del flujo de control |
| **E8** | `SOURCE_TEXT_IDENTICAL` | reconstruir y comparar `srcversion` | `SOURCE_SET_IDENTICAL` | que el **texto de los `.c` listados y de las cabeceras de su mismo directorio** es idéntico (modulo espacios y comentarios) | **todo lo demás**: toolchain, flags, config, orden de enlace, timestamp, y **las cabeceras de otros directorios** — que sí cambian el binario y **no** el `srcversion` |
| **E9** | `BINARY_IDENTICAL` | SHA256 del `.ko` reconstruido == el instalado | `BINARY_REPRODUCED` | **todo**: fuente, config, toolchain, flags, timestamp, rutas, orden | — (es el techo) |
| **—** | sin reconstrucción | — | `NOT_DETERMINED` | — | **toda la escalera por encima de E4**. Éste es el peldaño real del proyecto |

`INFERENCIA` — **el orden no es de fuerza monótona para `srcversion`.** E8 es
*más fuerte que E9 sobre la fuente* y *más débil que E9 sobre el binario*, porque
`srcversion` es por construcción **insensible** a la toolchain (§2.a). Por eso E8 y
E9 miden cosas distintas y no se sustituyen:

```
                  FUENTE                          BINARIO
E8  srcversion  ─────────────────►  (ciego a toolchain, flags, config, timestamp)
E9  SHA256      ──────────────────────────────►  (lo ve todo)
```

**Piso real del proyecto: E4/E5/E6.** Con la reconstruction `NOT_DETERMINED` (y sin
`.mod`/`.cmd`, E8 no es alcanzable ni siquiera reconstruyendo desde el `kernel-devel`
de esta máquina, §3.e).

### 3.g «Idéntico» vs. «equivalente»

`INFERENCIA` (base: las dos filas de la tabla anterior, medidas) — las dos
direcciones, con ejemplos reales de este caso:

**Mismo `srcversion` ⇒ NO bit a bit.** `srcversion` ignora:
- Las cabeceras de **otros** directorios. `HECHO` — `sumversion.c:367` filtra las
  `deps_` al mismo directorio del objeto. Un cambio en `include/linux/*.h` o en
  `amdkfd/*.h` entra en el binario y **no** cambia `srcversion`.
- La toolchain, los flags, la config, el timestamp, el orden de enlace.

⇒ Dos `.ko` con `srcversion` idéntico pueden ser binarios distintos **y
funcionalmente distintos** (un cambio de prototipo en un `.h` de `include/linux/`
cambia el código generado y no deja rastro en `srcversion`).

**Distinto `srcversion` ⇒ NO necesariamente funcionalmente distinto.** `HECHO` — en
este mismo binario, 156 de 209 literales de `amdgpu_discovery.c` **no están**. Es
decir: hay mucho texto fuente sin representación en el binario. `INFERENCIA` —
editar un mensaje dentro de una rama que `IS_ENABLED()`/`#if` deja fuera cambia
`srcversion` y **no cambia ni un byte del `.ko`**. `srcversion` es, en ese sentido,
*más sensible* que el propio binario.

**La regla que se sigue, y que es la que importa para un informe:**

> `srcversion` es una medida de **proximidad de fuente**, no de **identidad de
> build**. Un `srcversion` distinto es prueba *definitiva* de fuentes distintas. Un
> `srcversion` idéntico **no** es prueba de build idéntico, y no es prueba de
> identidad de build en absoluto.

---

## 4. CONFIGURACIÓN DE COMPILACIÓN

### 4.a Qué archivo decide qué compila, y por qué `kernel-devel` no tiene los `.c`

`HECHO` — el árbol de desarrollo, medido:

```
/usr/src/kernels/7.1.3-200.nobara.fc44.x86_64/   →  22.930 ficheros
  .c en TODO el árbol                              →      148
  .c en drivers/gpu/drm/                           →        0
  drivers/gpu/drm/amd/amdgpu/                      →        2   (Kconfig, Makefile)
```

`HECHO` — qué sí está: `.config` (292.545 B), `Module.symvers` (2.334.430 B),
`System.map` (11.500.412 B), `include/generated/autoconf.h` (361.546 B), `scripts/`
(incluido `scripts/mod/modpost.c` y `sumversion.c` completos), y los 5
`Makefile`/`Kconfig` del módulo.

`INFERENCIA` — un `kernel-devel` es un **árbol de cabeceras y de reglas de
construcción**, no un árbol de fuentes. Los 148 `.c` que quedan son *host programs*
(`scripts/`, `tools/`), que sí se distribuyen porque hay que compilarlos. Es
coherente con `modules.rst`: lo que un módulo externo necesita del kernel es *«the
configuration and header files»* — configuración y cabeceras. **Reconstruir un
módulo in-tree desde un `kernel-devel` es imposible por construcción.**

`HECHO` — `ls -la /lib/modules/$(uname -r)/` muestra el patrón estándar:
`build -> /usr/src/kernels/7.1.3-…`, `source -> build`, más `config`,
`modules.{alias,dep,order,builtin,symbols,softdep,devname}` (+ `.bin`), `vmlinuz`,
`System.map`, `symvers.gz`.

`HECHO` — **`/boot/config-$(uname -r)` y el `.config` del árbol de desarrollo son
byte-idénticos**: ambos SHA256 `43f1eec50b7eea3e3feb5777ac8a00c9f63c8c3748fc7a03eaee5ce8f9cfba34`,
292.545 B cada uno. `INFERENCIA` — la configuración que seCJecutó y la que se
publica son la misma; no hay discrepancia de configuración que introducir. Esto
**sube un peldaño**: E4 (`BRANCH_SET_CONSISTENT`) no tiene una=configuración
alternativa que descartar.

### 4.b Cómo se genera `.config`

`NORMA` — `makefiles.rst` §*Architecture Makefiles*: el proceso empieza en
«1) Configuration of the kernel => produce .config». Los front-ends de kconfig son
`make menuconfig`, `make xconfig`, `make defconfig`, `make savedefconfig`,
`make config` (documentados en `make help` y en el propio `scripts/kconfig/`).
`SECUNDARIO` — `config/extract-ikconfig` extrae la configuración de un kernel
*en ejecución* y es la herramienta de la que hablas cuando se obtiene `.config`
desde `/proc/config.gz` (`CONFIG_IKCONFIG_PROC`); no es el camino de este host,
que ya trae `kernel-devel`.

### 4.c `include/generated/autoconf.h`, la fuente de verdad en compilación

`HECHO` — presente, 361.546 B, generado en el árbol de desarrollo.

`INFERENCIA` (base: `makefiles.rst` §*The top Makefile reads the .config file* y
`kbuild.rst` §*KBUILD_KCONFIG*) — el orden es: Kconfig lee `.config` y produce
`include/generated/autoconf.h` (y `include/config/*`), y **el preprocesador sólo ve
`autoconf.h`**. Por eso:

- Un `.c` no contiene `CONFIG_X`; lo que contiene es `#include <linux/autoconf.h>`,
  y lo que el compilador evalúa es el `autoconf.h` **de la máquina que compila**.
- `HECHO` — el Makefile evalúa `$(CONFIG_DRM_AMDGPU_CIK)`, no `#ifdef`. Los dos
  mecanismos (preprocesador y make) leen la misma configuración, pero por caminos
  distintos. Una divergencia entre ellos es posible en principio; aquí no la hay,
  porque ambos proceden del mismo `.config` (y `autoconf.h` es sufijo de ÉL).

**Esto es la razón precisa por la que el Makefile de Kbuild por sí solo no basta
(E3):** los mismos `CONFIG_` en el Makefile y dentro del código, y sólo
`autoconf.h` y `.config` los vinculan.

### 4.d Módulos externos

`NORMA` — `modules.rst` §*How to Build External Modules*:

> To build external modules, you must have a prebuilt kernel available that contains
> the configuration and header files used in the build. Also, the kernel must have
> been built with modules enabled. … NOTE: "modules_prepare" will not build
> `Module.symvers` even if `CONFIG_MODVERSIONS` is set; therefore, **a full kernel
> build needs to be executed to make module versioning work**.

`HECHO` — el comando canónico, literal de la documentación:

```sh
$ make -C /lib/modules/`uname -r`/build M=$PWD
```

**Por qué un módulo externo necesita el árbol completo** — `NORMA` +
`sumversion.c:304-374`: `parse_source_files()` lee `.<obj>.cmd` y `get_src_version()`
lee `<mod>.mod`. Ambos son **artefactos de un árbol de construcción**. Un `kernel-devel`
no los tiene. `INFERENCIA` — para que `srcversion` se calcule sobre un módulo
externo, su Makefile debe ofrecer esos ficheros, o la verificación E8 no es
alcanzable. Ésta es la razón estructural, y ya medida, de por qué la reconstrucción
no se puede hacer aquí.

`HECHO` — `CONFIG_MODULES=y`, `CONFIG_MODULE_SIG_ALL=y`, `CONFIG_MODULE_SIG_SHA512=y`.

---

## 5. LA DISTORSIÓN ESPECÍFICA DE UNA DISTRIBUCIÓN

### 5.a Cómo se numera un kernel Fedora/Nobara

`HECHO` — **desde la base de datos RPM local**, no desde prosa:

```
$ rpm -q --qf "%{NAME} | version=%{VERSION} release=%{RELEASE}\n" kernel-devel
kernel-devel | version=7.1.3     release=200.nobara.fc44
kernel-devel | version=6.18.2    release=200.nobara.fc43
$ rpm -q --qf "%{SOURCERPM}\n" kernel-devel
kernel-6.18.2-200.nobara.fc43.src.rpm
kernel-7.1.3-200.nobara.fc44.src.rpm
```

| Componente | Campo RPM | Valor | Significado |
|---|---|---|---|
| `7.1.3` | `%{VERSION}` | upstream | **la versión de upstream va primero** — confirmado por el campo, no supuesto |
| `200` | release, 1.ª parte | contador de rebuild | cuántas veces se reconstruyó el paquete |
| `nobara` | release, 2.ª parte | marca de distro | variante de la distribución |
| `fc44` | release, 3.ª parte | Fedora 44 | versión de Fedora |
| `x86_64` | `%{ARCH}` | arquitectura | |

`INFERENCIA` — el `uname -r` es exactamente el NVR del paquete, con `-` por `.`:
`7.1.3` + `-` + `200.nobara.fc44` + `.` + `x86_64`. **Lo que el kernel se llama a sí
mismo es la identidad del RPM que lo empaquetó**, no una versión de upstream. De
aquí se sigue el punto 5.b.

`HECHO` — y una distinción de **dos** identidades de build que se confunden:

```
RPM:     BUILDTIME=sáb 04 jul 2026 11:51:41
         BUILDHOST=aws-x86-64-powerful-reserved-prod-12888627-20260704-144853
/proc/version: (mockbuild@559670082b9946b78405ee85a5345150)
                (gcc 16.1.1 20260515 (Red Hat 16.1.1-2), GNU ld 2.46-3.fc44)
uname -v: #1 SMP PREEMPT_DYNAMIC Sat Jul  4 14:59:29 UTC 2026
```

`INFERENCIA` — son dos capas distintas: `BUILDHOST`/`BUILDTIME` del RPM son el
contenedor que **empaquetó** el RPM binario; `mockbuild@…` y el timestamp de
`uname -v` son `KBUILD_BUILD_USER`/`HOST`/`KBUILD_BUILD_TIMESTAMP`, embebidos **dentro
de la compilación del kernel** (`kbuild.rst` §*KBUILD_BUILD_USER, KBUILD_BUILD_HOST*).
El primero es posterior al segundo (14:59:29 UTC dentro de una imagen, 11:51:41 local
en el RPM). `INFERENCIA` — el segundo es el que entra en el binario y por tanto el que
importa para la reproducibilidad; el primero es metadato de empaquetado y **no**
afecta al `.ko`.

### 5.b Qué implican los parches de la distribución

`HECHO` — el changelog RPM de `kernel-devel-7.1.3-200.nobara.fc44.x86_64`, en las
entradas que existen:

```
* sáb jul 04 2026 LionHeartP <…> - 7.1.3-200
- Update to 7.1.3
* lun jun 29 2026 … - 7.1.2-202
- New CachyOS kernel tag with T2 patch
* dom jun 28 2026 … - 7.1.2-201
- New CachyOS kernel tag with amdgpu shutdown/reboot fixes
* lun jun 01 2026 … - 7.0.11-200
- Update to 7.0.11
- Disable BORE for now
* lun may 11 2026 … - 7.0.6-200
- Update to 7.0.6
- Update linux-surface.patch
```

y, en el paquete 6.18.2:

```
* dom dic 07 2025 … - 6.17.11-200
- Update to 6.17.12
- Add 0001-amdgpu-Add-CH7218-PCON-to-the-VRR-whitelist.patch
```

**Dos conclusiones, de fuerza distinta:**

1. `HECHO` — **la línea Nobara/CachyOS no es upstream puro.** El changelog nombra
   parches no-upstream por nombre: `linux-surface.patch`, `0001-amdgpu-Add-CH7218-PCON-to-the-VRR-whitelist.patch`,
   «T2 patch», «Disable BORE», tags «CachyOS». Y uno de ellos es **de amdgpu**.
   Por tanto la premisa «el árbol de upstream **no es** el código que corre» es
   `SUPPORTED` para esta línea de distribución.

2. `NOT_DETERMINED` — **la magnitud del delta para `7.1.3-200` concreto.** La entrada
   de changelog de esa release dice **únicamente** «Update to 7.1.3»: no enumera
   parches, no dice si la serie se reinició o se arrastró, no dice si el parche de
   amdgpu sigue aplicado. **El changelog no establece qué contiene 7.1.3-200.** El
   artefacto que lo establecería es `kernel-7.1.3-200.nobara.fc44.src.rpm`
   (`%{SOURCERPM}`, `HECHO`), y:

`HECHO` — `find / -maxdepth 5 -name "kernel-7.1.3*.src.rpm"` → **vacío**. El paquete
fuente no está en esta máquina. `FETCH_FAILED` — no se obtuvo: `src.fedoraproject.org`
responde con una barrera anti-bot (Anubis proof-of-work, HTTP 200 con página de
desafío, no el `.spec`). `ALTERNATIVE_SOURCE` = la base de datos RPM local y el
changelog. `WHY_ALTERNATIVE_IS_ACCEPTABLE` = establece la **identidad** del paquete
(NVR, `%{SOURCERPM}`, build host/time) pero **no** el contenido del parche, y por eso
la magnitud del delta sigue `NOT_DETERMINED`.

**Consecuencia para este proyecto, y es la más importante del apartado:** E3
(`KBUILD_RULES_IDENTICAL`) compara el Makefile de amdgpu contra upstream y coincide.
Eso **no** acota el delta de la distribución, porque un parche de la distro que
toque un `.c` —o incluso el `Makefile`— de amdgpu se habría detectado aquí, pero uno
que toque `include/linux/*.h`, `arch/x86/*`, el linker script, o un fichero de otro
directorio, **no se detecta con E3 y tampoco con E5** salvo que añada o quite
símbolos. Y `srcversion` (E8) **tampoco**, por §3.g.

### 5.c Qué se puede verificar sin acceso privilegiado

Todo lo siguiente es `HECHO` de este documento, sin `sudo`, sin modificar nada:

| Verificación | Comando | Peldaño |
|---|---|---|
| Existencia del árbol de desarrollo | `ls -d /usr/src/kernels/$(uname -r)/` | — |
| Configuración real, no laISHED | `sha256sum /boot/config-$(uname -r) /usr/src/kernels/$(uname -r)/.config` | E4 |
| Reglas de Kbuild byte a byte | `sha256sum` del `Makefile` de cada subsistema vs. upstream | E3 |
| Qué ramas se tomaron | `grep '^CONFIG_.*=' .config` contra los `$(CONFIG_…)` del Makefile | E4 |
| Estructura de símbolos | `nm --defined-only amdgpu.ko` | E5 |
| Mensajes | `strings -a amdgpu.ko` | E6 |
| Tipos | `readelf -SW amdgpu.ko \| grep BTF` | E7 |
| Toolchain | `readelf -p .comment amdgpu.ko` | E2 |
| Identidad del paquete | `rpm -q --qf '%{VERSION} %{RELEASE} %{SOURCERPM}' kernel-devel` | §5.a |

### 5.d Por qué el tarball de upstream no lleva los parches, y por qué no se pueden recuperar

`INFERENCIA` (base: `AGENTS.md` §3.1 jerarquía de fuentes, y el hecho de que el
changelog nombre parches que upstream no tiene) — el tarball de kernel.org contiene
**la etiqueta tal cual la subió Linus**. Los parches de la distribución se aplican
en el `%prep`/`%patch` del `.spec` de Fedora, en un espacio de trabajo que existe
sólo durante la construcción del paquete. **No hay ninguna forma de derivarlos del
tarball**: no están ni en el tarball ni en el `kernel-devel` (que se construye
*después* de aplicarlos, pero **no** los incluye: por eso E3 coincide con upstream).
El único portador es el paquete fuente.

`NOT_OBSERVED` — que los parches *no* estén en `kernel-devel` es `HECHO` para el
`Makefile` de amdgpu (coincide con upstream, E3) y `NOT_AVAILABLE` para los `.c`,
que no están en absoluto (§4.a). No es `PROVEN_ABSENT` para el árbol entero: sólo
lo he establecido para un fichero.

---

## 6. VERIFICACIÓN PRÁCTICA — COMANDOS EXACTOS

Todos ejecutados en este host. Sustituir `K` por `/usr/src/kernels/$(uname -r)` y
`KO` por la ruta del `.ko` descomprimido.

### 6.a Extraer la lista de ficheros fuente que Kbuild compila

`NOT_DETERMINED` con una salvedad importante: **no existe un comando autoritativo
para esto a partir de un `kernel-devel`**, y conviene saber por qué antes de
intentar uno.

`INFERENCIA` (base: `sumversion.c:302-303, 396` + `HECHO`: el árbol de desarrollo no
tiene `.mod` ni `.cmd`) — la lista autoritativa vive en **dos** ficheros que sólo
existen en un árbol de construcción:

```sh
# CON árbol de construcción — AUTORITATIVO, es lo que lee get_src_version()
head -1 drivers/gpu/drm/amd/amdgpu/amdgpu.mod    # lista de objetos del módulo
cat  drivers/gpu/drm/amd/amdgpu/.amdgpu_device.o.cmd | grep -E '^(source_|deps_)'
```

Sin ellos, la mejor aproximación disponible es **expandir el Makefile contra el
`.config`**. `HECHO` — implemented y ejecutado, `kbexpand.py` (392 objetos, con
`addprefix`/`addsuffix`/`include` anidados, continuaciones `\`, `ifneq/ifeq` y
variables intermedias):

```sh
python3 kbexpand.py $K/drivers/gpu/drm/amd/amdgpu/Makefile $K/.config amdgpu
```

`HECHO` — sus límites, declarados: no evalúa `$(shell …)`, `$(wildcard …)` ni
`$(patsubst …)`; `else ifeq` se trata como `else`; un `CONFIG_` ausente de `.config`
se trata como no definido (que es lo que hace kbuild), no como `n`.

**Y la validación que lo respalda** (`HECHO`, §3.c): las 392 entradas incluyen
`../pm/powerplay/hwmgr/vega20_*.o`, `../ras/rascore/ras_aca.o`,
`../pm/swsmu/smu13/smu13_*.o`, y los 13 objetos condicionales de CIK y SI. Al cruzar
la lista con `nm --defined-only $KO` aparecen **424** símbolos
`cik_*`/`si_*`/`gfx_v6_0_*`/`uvd_v3_1_*`/`vce_v1_0_*`/`dce_v6_0_*`. **E4 queda
corroborado por E5 desde dos instrumentos independientes.**

### 6.b Extraer la lista de símbolos definidos del `.ko`

```sh
nm --defined-only $KO | wc -l                      # HECHO: 64.460
nm --defined-only $KO | awk '$2=="T"||$2=="t"' | wc -l   # HECHO: 34.773 (texto)
readelf -sW $KO | grep -c __ksymtab_               # HECHO: 4  (exportados)
readelf -SW $KO | grep -A1 '\.symtab'   # HECHO: sh_size 0x180738 = 1.574.712 B -> 65.613 simbolos
readelf -sW $KO | grep -cE '^ +[0-9]+:'    # HECHO: 65.613   (sh_info=49.354 es el ultimo local, NO el total)
```

Filtrar los duplicados del optimizador antes de comparar (`HECHO`: el `.ko` contiene
`cik_asic_reset` **y** `cik_asic_reset.cold`):

```sh
nm --defined-only $KO | awk '$2=="T"||$2=="t"' | sed 's/\.cold$//' | sort -u
```

### 6.c Comparar contra los símbolos del fuente

```sh
# 1) símbolos del binario, sin duplicados .cold
nm --defined-only $KO | awk '$2=="T"||$2=="t" {print $3}' | sed 's/\.cold$//' \
  | sort -u > /tmp/ko_syms.txt

# 2) funciones definidas en el fuente (no estáticas, fuera de línea)
grep -hoE '^[A-Za-z_].*\b([a-zA-Z_][a-zA-Z0-9_]*)\(' $SRC/*.c \
  | sed 's/.*[ *]\([a-zA-Z_][a-zA-Z0-9_]*\)($/\1/' | sort -u > /tmp/src_syms.txt

# 3) dirección de la diferencia — ÉSTA es la parte que prueba
comm -23 /tmp/src_syms.txt /tmp/ko_syms.txt   # en el fuente, ausente del binario
comm -13 /tmp/src_syms.txt /tmp/ko_syms.txt   # en el binario, ausente del fuente
```

`HECHO` — una comprobación de integridad que no necesita fuente y es independiente:
`Module.symvers` (`HECHO`: las 4 líneas de amdgpu con CRC `0x00000000`) contra los
`__ksymtab` del `.ko` (`HECHO`: 4). Cuadran.

### 6.d Extraer las cadenas

```sh
strings -a $KO | sort -u > /tmp/ko_strings.txt          # HECHO: 161.977 líneas
strings -a $KO | grep -F "UVD not responding, trying to reset the VCPU"
                                                 # HECHO: 4 apariciones
```

Medición del límite (la parte que hay que documentar siempre junto al resultado):

```sh
grep -oE '"[^"]{6,}"' $SRC/amdgpu_discovery.c | tr -d '"' | sort -u > /tmp/src_strings.txt
comm -23 /tmp/src_strings.txt /tmp/ko_strings.txt | wc -l    # HECHO: 156 de 209 ausentes
```

### 6.e ¿Tiene el `.ko` DWARF o no? — y por qué eso limita la verificación

`HECHO` — la respuesta precisa, que **no** es «no hay debug»:

```sh
readelf -SW $KO | grep -c debug        # HECHO: 0   -> NO hay DWARF
readelf -SW $KO | grep -A1 '\.BTF'     # HECHO: sección [85], sh_size 0x3b3f12 = 3.882.770 B
readelf --debug-dump=info $KO 2>&1 | head -3   # HECHO: sin salida
```

Total: **90 secciones**, ninguna `.debug_*`, una `.BTF`. Validación de la cabecera
BTF (`HECHO`, leído byte a byte):

```
magic=0xeb9f  version=1  flags=0  hdr_len=24
type_off=0  type_len=2501708  str_off=2501708  str_len=1381038
24 + 2501708 + 1381038 = 3882770  ==  sh_size (0x3b3f12 = 3882770)   ✔
```

**Por qué el `.BTF` está y el DWARF no.** `HECHO` — `.config`:

```
CONFIG_DEBUG_INFO=y
CONFIG_DEBUG_INFO_DWARF5=y
CONFIG_DEBUG_INFO_BTF=y
CONFIG_DEBUG_INFO_BTF_MODULES=y        ← ésta es la que decide para MÓDULOS
CONFIG_DEBUG_INFO_REDUCED is not set
CONFIG_GDB_SCRIPTS=y
```

`NORMA` — `kbuild.rst` §*INSTALL_MOD_STRIP*: *«INSTALL_MOD_STRIP, if defined, will
cause modules to be stripped after they are installed. If INSTALL_MOD_STRIP is '1',
then the default option `--strip-debug` will be used»*. `INFERENCIA` — el kernel
**se** compiló con DWARF5, y lo que se eliminó al instalar el módulo fue
específicamente el DWARF (`--strip-debug`), que no toca `.BTF`. Eso explica la
combinación observada sin recurrir a especulación. `NOT_DETERMINED` — el valor
concreto de `INSTALL_MOD_STRIP` en la build de Nobara; no lo medí. Lo que está
medido es el resultado (0 secciones `.debug_*`, `.BTF` presente y válido).

**Qué limita la falta de DWARF, exactamente:**

| Con DWARF | Con sólo BTF (aquí) |
|---|---|
| mapa línea↔instrucción → `addr2line`, scripts de symbolized stack traces | **no** se puede localizar una instrucción en un fichero/línea |
| tipos completos con offsets y layout | tipos, firmas, `struct`/`enum`/`typedef`, y `DATASEC` con variables globales |
| `pahole` da structs expandidos; `bpftool btf dump` también, desde BTF | id., pero **sin** correspondencia con el código |
| `gdb` con `vmlinux-gdb.py` | `NOT_AVAILABLE` |

`HECHO` — **`pahole` no está instalado en este host** (`command -v pahole` →
ausente). Consecuencia práctica: E7 no se puede ejecutar con `pahole`; habría que
usar `bpftool btf dump` o un lector de BTF propio. `NOT_AVAILABLE`, no
`PROVEN_ABSENT`: es una limitación de este host, no del kernel.

`HECHO` — y una observación sobre `strings` que se sigue de `.BTF`: la sección
`.printk_index` existe (`[31] .printk_index`, sh_size `0xa740` = 42.816 B) más su
`.rela.printk_index` con 5.352 entradas (128.448 B / 24). `INFERENCIA` — es el índice que permite a
`printk()` deduplicar mensajes; su presencia confirma que el índice de literales se
generó en build y es **otra** capa de evidencia sobre qué `printk` se compilaron,
independiente de `strings`.

---

## 7. COBERTURA, LÍMITES Y CONTRADICCIONES

### 7.1 Lo que NO se pudo establecer

| Ítem | Estado | Por qué / dónde se buscó |
|---|---|---|
| Algoritmo de `srcversion` | **`OBSERVED`** | MD4, no CRC32. `sumversion.c` + símbolos del binario `modpost` |
| Longitud del `srcversion` | **`OBSERVED`** | 23 hex; predicho por `srcversion[25]` y confirmado en el artefacto |
| Dónde lee el kernel el `srcversion` | **`OBSERVED`** | 2 apariciones en `main.c`; no se valida |
| `CONFIG_MODVERSIONS` activo | **`OBSERVED`** | **no**; §2.e/2.f |
| `__srcversion` (símbolo) | **`PROVEN_ABSENT`** | 0 ocurrencias en `nm amdgpu.ko` **y** 0 en `System.map` del kernel en ejecución. Ámbito: esos dos artefactos. El nombre es histórico (pre-2.6) y no existe en v7.1 |
| `EXTRA_CFLAGS` en v7.1 | **`NOT_DETERMINED`** | No aparece en `kbuild.rst` ni en `makefiles.rst` |
| `INSTALL_MOD_STRIP` en esta build | **`NOT_DETERMINED`** | No medido; el efecto sí está medido en el `.ko` |
| Magnitud del delta de parches en 7.1.3-200 | **`NOT_DETERMINED`** | Changelog no enumera; `.src.rpm` no está en disco y el repo está tras Anubis |
| `/sys/module/amdgpu/srcversion` | **`NOT_AVAILABLE`** | `deny` de `opencode.json` sobre `/sys`; `permission.rejected` |
| `modprobe --dump-modversions $KO` | **`NOT_AVAILABLE`** | `modprobe` denegado por política del proyecto |
| Lista autoritativa de ficheros del módulo | **`NOT_DETERMINED`** | Requiere `<mod>.mod` / `.<obj>.cmd`, ausentes de un `kernel-devel` (§6.a) |
| Versión exacta de `rustc` en la build del `.ko` | **`OBSERVED` parcial** | `.config` dice `rustc 1.96.1 (Fedora 1.96.1-1.fc44)`; el `.ko` no la incluye (amdgpu es C) |

### 7.2 Ficheros upstream que NO existen (404 verificado)

| Solicitado | Estado | Real |
|---|---|---|
| `Documentation/kbuild/kbuild.txt` | **`NOT_FOUND`** (HTTP 404) | `Documentation/kbuild/kbuild.rst` |
| `Documentation/process/patches.rst` | **`NOT_FOUND`** (HTTP 404) | `Documentation/process/submitting-patches.rst` |
| `scripts/mod/mkversion.c` | **`NOT_FOUND`** | `scripts/mod/sumversion.c` (§2.a) |
| `include/linux/vermagic.h` → `MODULE_INFO(srcversion,…)` | **`NOT_FOUND` en ese fichero** | `srcversion` lo emite `modpost.c:2027-2034`; `vermagic.h` sólo define `VERMAGIC_STRING` |

Búsqueda: `raw.githubusercontent.com/torvalds/linux/v7.1/…`, `WHERE` = GitHub raw,
`DATE` = 2026-09-27. Las tres primeras se descargaron y leídas íntegras; las tres
rutas inexistentes devolvieron 404.

### 7.3 La contradicción de la premisa P6, con su búsqueda

`CONTRADICTION` entre la premisa del encargo y el estado del host.
`RESOLUTION_STATUS = CONTRADICTION_WITHOUT_RESOLUTION` — no resoluble aquí: el
árbol no está y no puedo obtenerlo sin decisión humana (descarga de red + escritura).

| Búsqueda | Alcance | Resultado |
|---|---|---|
| `find / -maxdepth 7 -name amdgpu_drv.c` | todo el FS | `NOT_FOUND` |
| `find / -maxdepth 6 -name 'linux-7.1*'` | todo el FS | `NOT_FOUND` |
| `find / -maxdepth 5 -name 'kernel-7.1.3*.src.rpm'` | todo el FS | `NOT_FOUND` |
| búsqueda del hash `199c9959d3a9b53f346c221757fc7ac507fbac50` en ficheros de texto | `/` | `NOT_FOUND` |
| inspección de `/tmp/opencode/src/` | 30 entradas | 24 `.c` de amdgpu, **distintos** de `linux-opt` (SHA256 distintos) — **procedencia no establecida** |
| inspección de `/home/lucas/linux-opt/` | árbol completo | `7.1.0-rc1-ge75a43c7cec4`, 305 `.c` de amdgpu. **Versión distinta de la del kernel en ejecución** |

`INFERENCIA` — `/home/lucas/linux-opt` sirve para ilustrar la *estructura* de las
reglas de build (`kernel/module/main.c`, `sumversion.c`) pero **nada** de sus
contenidos puede portables al caso: `CONFIG_DRM_AMDGPU=m` y `vermagic` describen
otro árbol. Por eso §2 y §4 se citan del árbol de desarrollo **y** de upstream v7.1
(que son comparables), y nunca de `linux-opt` para afirmaciones sobre este host.

### 7.4 Muestreo de la fuente

`HECHO` — `/usr/src/kernels/7.1.3-200.nobara.fc44.x86_64/`: 22.930 ficheros.
Muestreados y leídos **íntegros**: `scripts/mod/sumversion.c` (413 líneas),
`scripts/mod/modpost.h`, `scripts/mod/Makefile`, `scripts/Makefile.modpost`,
`include/linux/vermagic.h` (48), `include/linux/module.h` (fragmentos 38-41, 415),
`drivers/gpu/drm/amd/amdgpu/Makefile` (8.638 B, leído en cabecera y en las ramas condicionales),
`drivers/gpu/drm/amd/{pm,ras}/Makefile`, `kernel/module/Kconfig` (241-250).
`modpost.c` leído por rango (1290-1331, 1630-1680, 2020-2045, 2300-2340) y por
`grep` directed. **No** se leyeron los ~200.000 restantes: para las preguntas de
este encargo son `NOT_INVESTIGATED`.

Upstream v7.1 descargados y leídos íntegros: `Documentation/kbuild/modules.rst`,
`Documentation/kbuild/makefiles.rst`, `Documentation/kbuild/kbuild.rst`,
`Documentation/process/submitting-patches.rst`, `scripts/mod/sumversion.c`,
`scripts/mod/modpost.h`, `kernel/module/main.c`, `kernel/module/internal.h`,
`kernel/module/version.c`, `kernel/module/Makefile`.

### 7.5 `STOP_REASON`

`SUFFICIENT_EVIDENCE` para el objetivo del encargo (la escalera de §3.f y sus
límites están establecidos con fuente primaria y medida). Dos avenues siguen
abiertas y **requieren decisión humana**, no más trabajo del agente:

1. **Obtener el árbol v7.1.3** (descarga de red + escritura en disco) → habilitaría
   §6.a/6.c con fuente correcta y E5 con la versión adecuada.
2. **Obtener `kernel-7.1.3-200.nobara.fc44.src.rpm`** → cerraría §5.b
   (`NOT_DETERMINED` → magnitud del delta de parches).

---

## 8. ERRORES COMUNES

1. **Creer que `srcversion` es un CRC32 truncado, o que son 16 hex.**
   Es **MD4 (RFC 1320)**, y son **23** hex (`srcversion[25]` recorta los 32 de MD4).
   Confundirlo lleva a escribir herramientas de verificación que nunca van a
   funcionar. `sumversion.c`, y `nm` sobre `scripts/mod/modpost`.

2. **Creer que `srcversion` identifica un commit.** Es un hash del **texto
   fuente**: no se puede invertir a un commit, y dos commits distintos con el mismo
   texto relevante dan el mismo valor. `kernel/module/Kconfig:241-250` dice que
   sirve para «see exactly which source was used» — trazabilidad, no identidad.

3. **Creer que `srcversion` se calcula sobre el `.ko`.** Se calcula sobre los
   **ficheros fuente**, leídos vía `<mod>.mod` y `.<obj>.cmd`, con espacios y
   comentarios eliminados. Consecuencia fatal: **`srcversion` es ciego a la
   toolchain, a los flags, a la config y a las cabeceras de otros directorios.**

4. **Creer que comparar el Makefile basta.** No cubre ningún `.c`, ni la `.config`
   que se usó, ni los flags, ni la toolchain, ni — en amdgpu — los otros **5**
   Makefiles que definen el módulo.

5. **Asumir que un `.ko` con el mismo nombre es el mismo código.** El nombre no es
   evidencia (E0). Ni `intree: Y`, ni `vermagic`, ni la firma: los tres los escribe
   la build, no el código.

6. **Ignorar que el timestamp de compilación cambia el binario.** `KBUILD_BUILD_TIMESTAMP`
   entra en `UTS_VERSION` y por tanto en el kernel y en los `.o`; `KBUILD_BUILD_USER/HOST`
   también. Por eso dos reconstrucciones del mismo fuente no dan el mismo SHA256 —
   y por eso `srcversion`, que no los ve, es la única comparación estable. Ignorar
   esto produce «no reproducible» como conclusión falsa sobre el código fuente.

7. **Confundir `vermagic` con una firma fuerte.** Con `CONFIG_MODVERSIONS=y`
   (`version.c:88-97`) `same_magic()` compara **sólo el primer token**, ignorando
   `SMP`/`preempt`/`mod_unload`. Sin `MODVERSIONS` es un `strcmp` entero. Sin
   conocer cuál de los dos casos aplica, se afirma más de lo que se sabe.

8. **Asumir que `MODVERSIONS` está activo por defecto en una distro.** `HECHO` — aquí
   `# CONFIG_MODVERSIONS is not set`; no hay `__versions`, los CRC de
   `Module.symvers` son `0x00000000`, `version.c` ni se compila, y el error
   «disagrees about version of symbol» **no puede ocurrir**. La única comprobación
   de compatibilidad real es `vermagic`.

9. **Contar apariciones de una cadena y concluir de qué fichero viene.**
   `HECHO` — «UVD not responding…» aparece 4 veces en el `.ko` y en ≥4 ficheros
   del árbol de referencia. El recuento coincide y aun así **no distingue** «4
   ficheros» de «1 fichero × 4». Es el salto `métrica → constructo`.

10. **Informar el recuento de cadenas sin su tasa de cobertura.** `HECHO` — 53 de
    209 literales (25,4 %). Un «el binario contiene el mensaje X» sin el 74,6 %
    ausente es una afirmación mucho más fuerte de lo que la evidencia sostiene.

11. **Contar símbolos sin filtrar los `.cold`.** `HECHO` — el `.ko` contiene
    `cik_asic_reset` y `cik_asic_reset.cold`. Sin filtrar, el recuento se infla y la
    comparación con el fuente se falsea.

    **Y el error gemelo, más caro:** concluir «al código le faltan estas 39
    funciones» a partir de `comm`. `HECHO` — 38 de las 39 son `static` y
    desaparecieron por **inlineo**, no por borrado ni por cambio de versión. La
    dirección *función del fuente → símbolo* tiene falsos positivos sistemáticos;
    la inversa (símbolo → función) es la fiable. Sin distinguir `static` de global,
    un `comm -23` se lee como una lista de ausencias y no lo es.

12. **Creer que «no hay debug» porque no hay DWARF.** `HECHO` — hay `.BTF` de
    3.882.770 B, con cabecera validada, y `CONFIG_DEBUG_INFO_BTF_MODULES=y`. La
    afirmación correcta es «no hay DWARF; hay BTF». Y la BTF **no** da mapa
    línea↔instrucción: `addr2line` no funciona, y `pahole` no está instalado en
    este host.

13. **Confundir los dos hosts de build.** `HECHO` — `BUILDHOST` del RPM
    (`aws-x86-64-powerful-…`) y `KBUILD_BUILD_HOST` embebido en el kernel
    (`mockbuild@559670082b…`) son dos capas distintas. Sólo el segundo afecta al
    binario; el primero es metadato de empaquetado.

14. **Asumir que `uname -r` es la versión de upstream.** `HECHO` — `rpm -qf` da
    `%{VERSION}=7.1.3` / `%{RELEASE}=200.nobara.fc44`. El `uname -r` es el **NVR
    del RPM**, y `200.nobara.fc44` es exactamente la parte que introduce la
    distribución.

15. **Cerrar una conclusión de atribución a partir del changelog.** `HECHO` — la
    entrada de `7.1.3-200` dice sólo «Update to 7.1.3», mientras que entradas
    vecinas **sí** enumeran `linux-surface.patch` y un parche de amdgpu. El
    changelog prueba que **la línea lleva parches**; **no** prueba cuáles lleva
    *esta* release. Eso es `NOT_DETERMINED`, y el `.src.rpm` es el artefacto que lo
    cerraría.

16. **Creer que comparar un `kernel-devel` contra upstream verifica la build.**
    `kernel-devel` se construye **después** de aplicar los parches y **no** los
    incluye: por eso su `Makefile` de amdgpu coincide con upstream (E3) y eso no dice
    absolutely nada sobre los `.c` que se compilaron.

---

## 9. PROCEDENCIA

```
FUENTE            →  SECUNDARIO/primaria
  sumversion.c        MD4, 32 hex, recortado a 23
  modpost.h/.c        srcversion[25]; la guarda version||all_versions
  Makefile.modpost    -a si CONFIG_MODULE_SRCVERSION_ALL
  .config             MODVERSIONS=n · SRCVERSION_ALL=y · BTF_MODULES=y
      │
      ▼
ARTEFACTO (.ko)   →  HECHO
  90 secciones · 0 .debug_* · .BTF 3.882.770 B (cabecera verificada)
  64.460 símbolos · 4 __ksymtab · srcversion de 23 hex
  .comment: GCC 16.1.1 20260515 (Red Hat 16.1.1-2)
      │
      ├─ nm            ─► E5  ┐
      ├─ strings       ─► E6  ├─ corroboran E4 (424 símbolos CIK/SI)
      ├─ readelf .BTF  ─► E7  ┘
      └─ Makefile SHA ─► E3
      │
      ▼
ESCALERA (§3.f)   →  PISO REAL: E4/E5/E6
  E8 srcversion  →  inalcanzable sin <mod>.mod/.<obj>.cmd
  E9 SHA256      →  NO_RUN (requiere árbol v7.1.3, ausente)
```

**`STOP_REASON = SUFFICIENT_EVIDENCE`.** Los dos `NEXT` que quedan son
**decisiones humanas**, no tareas técnicas: (1) autorizar la obtención del árbol
v7.1.3, (2) autorizar la obtención de `kernel-7.1.3-200.nobara.fc44.src.rpm`.

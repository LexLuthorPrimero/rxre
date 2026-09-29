# 001 — Localización y perfil de `amdgpu.ko` en el host RX 550

**Clasificación**: `READ_ONLY/EVIDENCE`
**Fecha**: 2026-09-29
**Host**: `HOST_SCOPE` no declarado por el humano en la orden de trabajo; se declara aquí por
medición directa, ver §1. `TEMPORALITY`: estado steady-state, módulo cargado en el kernel en
ejecución.
**Rol**: IA-1 Ingeniero Inverso, ámbito `06-INGENIERIA-INVERSA/`
**Autorización**: lectura de ficheros de `/lib/modules` y ejecución de `nm`/`rz-bin`/`strings`
sobre una copia descomprimida en `/tmp/opencode/`. Sin sysfs, sin carga/descarga de módulos,
sin `sudo`. Ninguna acción de `SYSTEM_CHANGE`.

---

## 1. Identidad del host (medido, no supuesto)

`AGENTS.md` exige declarar `HOST_SCOPE` y no asignar uno en silencio. El hostname no viene en la
orden de trabajo, así que se mide:

| Atributo | Valor | Cómo se obtuvo |
|---|---|---|
| Kernel en ejecución | `7.1.3-200.nobara.fc44.x86_64` | `uname -r` |
| Módulos presentes | `7.1.3-200.nobara.fc44.x86_64` (**coincide**), `6.18.2-200.nobara.fc43.x86_64` (otro, no en ejecución) | `find /lib/modules` |
| Distribución | Nobara 44 (fc44) | `vermagic` del módulo |

El módulo del kernel **en ejecución** es el de `7.1.3`, no el de `6.18.2`. Los dos coexisten en
`/lib/modules`; un analisis hecho sobre el equivocado no describe este host.

## 2. Localización exacta

```
/lib/modules/7.1.3-200.nobara.fc44.x86_64/kernel/drivers/gpu/drm/amd/amdgpu/amdgpu.ko.zst
```

Es un objeto de kernel **comprimido con zstd**, no un ELF plano. Cualquier herramienta que lo
consuma directamente fallará sin descomprimir antes.

| Campo | Valor |
|---|---|
| `filename` | `/lib/modules/7.1.3-200.nobara.fc44.x86_64/kernel/drivers/gpu/drm/amd/amdgpu/amdgpu.ko.zst` |
| `srcversion` | `D68004925455E20A24C2B87` |
| `vermagic` | `7.1.3-200.nobara.fc44.x86_64 SMP preempt mod_unload` |
| `license` | `GPL and additional rights` |
| `description` | `AMD GPU` |

**`srcversion` es el identificador a citar** en cualquier hallazgo posterior. El `BuildID` del ELF
(`4d5342509f84dd84f0d5d515b03eb6c7659fb492`) identifica el objeto ya descomprimido, no el
paquete instalado: cambia si se recompila aunque el contenido funcional sea el mismo.

## 3. Tamaño y perfil del objeto

Descomprimido a `/tmp/opencode/amdgpu.ko` con `zstd -d -c`:

| Propiedad | Valor |
|---|---|
| Tamaño descomprimido | **37 494 368 B** (~35,8 MiB) |
| Tipo | `ELF 64-bit LSB relocatable, x86-64, version 1 (SYSV), not stripped` |
| BuildID | `4d5342509f84dd84f0d5d515b03eb6c7659fb492` |
| Símbolos de texto (`T`/`t`) | **34 773** |
| Símbolos dinámicos definidos | **0** |

Dos consecuencias que condicionan el método:

**`not stripped`** y **0 símbolos dinámicos definidos** no se contradicen. Un `.ko` es un objeto
relocatable, no un ejecutable enlazado: no tiene tabla de importación resuelta y su API la fija
`.modinfo` más que una `dynsym`. El trabajo de "qué exporta `amdgpu.ko`" hay que hacerlo sobre
`.modinfo` y los símbolos locales, **no** sobre `nm -D`, que aquí devuelve cero y parecería
"no exporta nada".

**35,8 MiB de código sin.strip** es un objetivo grande para Ghidra, pero tratable por partes (§7).

## 4. Entry points del módulo

Extraídos con `nm`, confirmados por sección con `rz-bin -S`:

| Símbolo | Tipo | Dirección | Sección |
|---|---|---|---|
| `init_module` | `T` | `0x0000000000000010` | `.init.text` (`0x00cae5e8`, 137 B) |
| `cleanup_module` | `T` | `0x0000000000000010` | `.exit.text` (`0x00cae678`, 62 B) |

Ambos están en la **dirección 0x10**, no en 0. Es lo esperable: `.init.text` y `.exit.text` son
secciones propias, y sus direcciones son relativas al inicio de cada una. La dirección plana no
es comparable entre las dos; para desensamblar hay que usar el offset dentro de la sección.

| Estructura | Símbolo | Tipo |
|---|---|---|
| `pci_driver` de DRM | `amdgpu_kms_pci_driver` | `d` (datos) |
| `drm_driver` | `amdgpu_kms_driver` | `r` (read-only) |
| `file_operations` | `amdgpu_driver_kms_fops` | `r` |
| Carga KMS | `amdgpu_driver_load_kms` | `T` |
| Descarga KMS | `amdgpu_driver_unload_kms` | `T` |
| Apertura | `amdgpu_driver_open_kms` | `T` |

**`amdgpu_kms_pci_driver` es el punto de entrada real** para un driver sustituto: es lo que se
registra con `pci_register_driver`. Los cuatro `*.cold` asociados a las funciones KMS son código
de outlier del optimizador (GCC los separa para mejorar el layout de la caché); no son lógica
adicional y no deben contarse como funciones distintas.

## 5. Símbolos relevantes para compute

Conteos por coincidencia de patrón, sobre **todas** las líneas de `nm` (t.ex. texto, datos y
`read-only`, incluidos los *outliers* `.cold`). La base se declara explícitamente porque restrict
el filtro a texto cambia las cifras:

| Patrón | Todas las líneas | Solo símbolos de texto (`T`/`t`) |
|---|---|---|
| `compute_` | **123** | 106 |
| `gfx_v8` | **191** | 191 |
| `vcn` | **943** | 815 |
| `polaris12` | 1 (`cwsr_trap_gfx8_hex`, dato, no código) | 0 |
| `si_compute` | **0** | 0 |

Familias de símbolos que un driver de compute propio necesita replicar:

```
amdgpu_fence_driver_hw_init / _fini / _start_ring / _stop_ring
amdgpu_fence_driver_init_ring / _sw_init / _sw_fini
amdgpu_fence_driver_force_completion
amdgpu_fence_emit / amdgpu_fence_emit_polling
amdgpu_fence_count_emitted / amdgpu_fence_driver_set_error
amdgpu_gfx_enable_kgq / amdgpu_gfx_disable_kgq
amdgpu_gfx_enable_kcq / amdgpu_gfx_disable_kcq
amdgpu_gfx_compute_queue_acquire
amdgpu_gfx_cp_init_microcode
amdgpu_gfx_csb_preamble_start / _end / amdgpu_gfx_csb_data_parser
amdgpu_gfx_cleaner_shader_init / _sw_init / _sw_fini
amdgpu_gfx_cp_ecc_error_irq
```

**`kgq` (graphics queue) y `kcq` (compute queue) son el núcleo del trabajo de Fase 4.** Es la
primera partición de hardware que hay que entender: son registros y colas distintos, no una
cola con dos modos.

`cwsr_trap_gfx8_hex` es el único símbolo que nombra Polaris 12 explícitamente, y es **dato**
(`r`), no código. No hay ningún `polaris12_*` de función. El módulo identifica la variante por
tabla, no por símbolos con nombre: el mapeo ASIC→IP version hay que sacarlo de la lógica
`amdgpu_kms_pci_driver` → `amdgpu_discovery` → detección de `ASIC_TYPE`, no de la tabla de
símbolos.

### 5.1 KGQ y KCQ: medidas y primer desensamblado

Direcciones y tamaños, con `nm -S` (la dirección es el valor del símbolo dentro de la sección de
texto, no un VA absoluto — el objeto es relocatable):

| Función | Símbolo | Dirección | Tamaño |
|---|---|---|---|
| `amdgpu_gfx_enable_kgq` | `T` | `0x0000000000143e90` | 455 B |
| `amdgpu_gfx_enable_kcq` | `T` | `0x0000000000143b30` | **833 B** |
| `amdgpu_gfx_disable_kgq` | `T` | `0x00000000001438b0` | 545 B |
| `amdgpu_gfx_compute_queue_acquire` | `T` | `0x0000000000142880` | 561 B |

**KCQ es casi el doble de grande que KGQ** (833 B frente a 455 B). Es la primera asimetría
medida entre las dos colas y esperable: la cola de compute lleva GTT, SQ y un despachador
propio, mientras la de graphics hereda más de su camino. Es `PLAUSIBLE`, no `OBSERVED`: el
tamaño no identifica la causa, y establecerla requiere seguir las llamadas.

Primeras instrucciones de `amdgpu_gfx_enable_kgq`, desensambladas con `rizin` (`pd 24`):

```
0x0817c6f8  endbr64
0x0817c6fc  call   reloc.target.__fentry__      ; traza fentry activa
0x0817c701  sub    rsp, 0x30
...
0x0817c714  imul   rbp, rbp, 0x388              ; 904 = sizeof(amdgpu_device)
0x0817c720  lea    r13, [rdi + rbp]
0x0817c724  mov    rax, qword [r13 + 0x18420]   ; campo del amdgpu_device
0x0817c72b  test   rax, rax
0x0817c72e  je     0x817c8b5                    ; salida temprana si NULL
0x0817c734  cmp    qword [rax + 8], 0
0x0817c739  je     0x817c8b5
0x0817c749  call   amdgpu_device_flush_hdp
0x0817c74e  cmp    byte [r12 + 0x4aafc], 0
0x0817c757  je     0x817c7c7
0x0817c759  mov    edx, dword [r12 + 0x1a440]
0x0817c761  test   edx, edx
0x0817c763  je     0x817c8a9
```

Lo que esto establece, y lo que no:

- `0x388` = **904 B**. Es el tamaño que el código multiplica para indexar el `amdgpu_device`, y
  el candidato natural es `sizeof(struct amdgpu_device)`. **No está verificado contra la
  fuente**: `sizeof` real exige el entorno de build del kernel completo
  (`amdgpu.h` → `amdgpu_ctx.h` → `linux/ktime.h`, que no compila fuera del árbol), y la
  inspección manual del struct (líneas 858-1201 de `amdgpu.h`, ~343 líneas) no permite derivar
  el tamaño con los campos alineados. Se registra como `OBSERVED` del desensamblado y
  `PLAUSIBLE` como `sizeof(amdgpu_device)`. Confirmarlo es trabajo pendiente (§8), y es la vía
  para nombrar los offsets relativos que siguen.
- **`amdgpu_device_flush_hdp` se llama al principio**: antes de tocar la cola hay que asegurar
  que la HDP (la unidad de escritura de Host Data Path) está drenada. Cualquier driver propio
  que escriba en registros de la cola sin ese flush replicaría una condición de carrera que el
  driver original considera obligatoria.
- El acceso a `[r12 + 0x4aafc]` y `[r12 + 0x1a440]` son offsets dentro de la sub-estructura de
  cola, no del `amdgpu_device` directo. **Son valores observados en el desensamblado, no
  nombres de campo**: para ponerles nombre hace falta el mapa de estructuras, que es trabajo
  pendiente (§8) y no se resuelve leyendo el binario.
- `endbr64` + `__fentry__` indican que el módulo se compila con CET y fentry. Afecta a cómo se
  deben parchear funciones: un driver propio no necesita el trampolín, pero su absence cambia
  los offsets de todas las funciones siguientes.

**Lo que esto NO establece**: qué registros se escriben, ni en qué orden, ni bajo qué condición.
Para eso hay que seguir las llamadas de escritura (`amdgpu_kiq_*`, `amdgpu_ring_*`) y resolver los
offsets a nombres.

## 6. Referencia al IP block de Polaris 12 (GFX8)

`gfx_v8` aparece 191 veces en símbolos, lo que confirma que el código de GFX8 está compilado en
este módulo. `si_initialize_smc_cac_tables` es la única función `si_*` (Southern Islands /
Sea Islands, la generación previa) que sobrevive con nombre: es código compartido heredado, no
una indicación de que la GPU sea de esa generación. `polaris12` aparece una sola vez y es **dato**
de tabla, no código.

**GFX_HWIP sigue `NOT_DETERMINED`.** Este documento **no** establece la generación gfx del
hardware. `AGENTS.md` §3 prohíbe precisamente derivar el número de generación de una
`PCI_IDENTITY` o de un nombre de driver; el método correcto es leer un registro de ASIC
identificador a través de `umr`, que queda como trabajo pendiente (§8). El hecho de que el
módulo contenga 191 referencias a `gfx_v8` describe **el módulo**, no necesariamente **esta
GPU**: un solo `.ko` sirve a toda la familia ASIC de Polaris 12 y a otros.

Esto es la misma distinción que sostiene AD-12 en el proyecto: que el driver tenga el código no
demuestra quéhwip reporta la GPU.

## 7. Herramientas: disponibilidad verificada por nombre

`AGENTS.md` documenta tres casos en que se afirmó ausencia desde un objeto vecino en vez del
objeto. Se comprueba cada herramienta **por su nombre**, no por un directorio supuesto:

| Herramienta | Ruta indicada en la orden | Estado real | Verificación |
|---|---|---|---|
| radare2 | `r2` | **PRESENTE** | `command -v r2` → `/usr/bin/r2`, v5.9.8 |
| rizin | `rz-bin`, `rz-asm` | **PRESENTE** | `/usr/bin/rz-bin`, `/usr/bin/rz-asm`, v0.7.4 |
| UMR | `umr` | **PRESENTE** | `/usr/bin/umr`, v1.0.0, build 2026-01-17 |
| Ghidra | `/home/lucas/tools/ghidra/ghidraRun` | **AUSENTE** | `ls` → no existe el fichero; `ghidra`, `ghidraRun`, `analyzeHeadless`, `ghidra-analyzeHeadless` no están en `PATH`; `find /` sin resultados; `rpm -q ghidra` → no instalado |
| Mesa (radv) | `/home/lucas/src/mesa` | **RUTA ERRÓNEA** | `/home/lucas/src/mesa` **no existe**. El repo real está en **`/home/lucas/mesa`** (es repo git) |
| Linux headers | `/home/lucas/src/linux` | **RUTA ERRÓNEA** | No existe. Headers reales: `/usr/src/kernels/7.1.3-200.nobara.fc44.x86_64` y `/lib/modules/7.1.3-200.nobara.fc44.x86_64/build` |

**Tres correcciones sobre la orden de trabajo**, todas verificadas por nombre y no por relativas:

1. **Ghidra no está instalado.** No es un problema de ruta. `rpm -q ghidra` responde
   "no está instalado". El análisis estático inicial se hace con `rizin`/`radare2`, que sí están.
2. **Mesa está en `/home/lucas/mesa`, no en `/home/lucas/src/mesa`.**
3. **Los headers de Linux están en `/usr/src/kernels/7.1.3-...`, no en `/home/lucas/src/linux`.**

Nota sobre Mesa: **`radv` no está presente** en `/home/lucas/mesa/src/gdrivers/`. Esa ruta no
existe. El checkout no contiene el driver Vulkan de Mesa, de modo que la referencia para el
comportamiento de compute que produjo la Fase 2 no está disponible ahí. Esto **no** invalida la
Fase 2 —el agreement test de 0/4096 es evidencia medida en hardware— pero sí significa que la
referencia de Mesa no es accesible como fuente primaria en este host. `NOT_AVAILABLE`, alcance:
checkout local de Mesa.

## 8. Trabajo pendiente, con el método

1. **`GFX_HWIP` por registro** (`umr`, lectura de ASIC ID). Es la única forma válida de
   establecer la generación gfx. `NOT_DETERMINED` hasta entonces.
2. **Desensamblado de `amdgpu_gfx_enable_kgq` / `kcq`** con `rizin`: dónde están los registros
   KGQ/KCQ, qué se escribe y en qué orden. Es el primer objetivo real de Fase 4.
3. **`.modinfo` completo**: los parámetros de módulo (`dpm`, `aspm`, `pp_`, `vm_`) governs el
   comportamiento en runtime y son fuente de autoridad para el estado de la GPU. El barrido
   inicial no devolvió ninguno con el patrón buscado; requiere `modinfo` sobre el fichero en vez
   de `strings`, porque `.modinfo` está en formato binario con pares clave=valor.
4. **Mapa de registros** en `register-maps/`: requiere los headers de `/usr/src/kernels/7.1.3-...`
   (`include/uapi/drm/amd_drm.h` y `amdgpu_drm.h`), no Ghidra.

### 8.1 Corrección: la fuente del kernel SÍ está disponible, y cambia el método

La orden de trabajo indicada `/home/lucas/src/linux`, que no existe. La fuente
real del módulo analizado **está en este repositorio**:

```
RESEARCH/working/linux-7.1.3/drivers/gpu/drm/amd/amdgpu/amdgpu.h
```

`struct amdgpu_device` está en las líneas 858-1201 (~343 líneas). Esto **reordena las
prioridades** de §8: la mayor parte del trabajo de este documento, que parecía exigir análisis
estático, se resuelve leyendo C.

- Los **nombres de los offsets** (`0x18420`, `0x1a440`, `0x4aafc`) se resuelven leyendo las
  sub-estructuras, no desensamblando.
- `sizeof(struct amdgpu_device)` se confirma compilando un Translation Unit contra el entorno del
  árbol, o con `pahole` sobre un vmlinux con BTF si hubiera uno disponible.
- La secuencia de `amdgpu_gfx_enable_kgq` se lee en C y se contrasta con el desensamblado, que
  pasa a ser el verificador y no la fuente.

`DEC-1` del proyecto ya establece que la geometría de page table es por dispositivo
(`amdgpu_vm.c:2433-2440`); ese archivo está en este mismo árbol. El precedente de leer fuente
en vez de binario está establecido.

**Esto reduce la dependencia de Ghidra**: sigue sin estar instalado, pero el trabajo inicial ya
no lo necesita. Se reevalúa si aparece una tarea donde la fuente no esté (binario de usuario
distinto, o firmware).

## 9. Límites de este documento

- describe **el `.ko` instalado en disco**, no su comportamiento en ejecución. Que el símbolo
  exista no prueba que la ruta se ejecute; eso requiere traza.
- No hay lectura de registros. Ninguna afirmación sobre el estado del hardware de la GPU.
- El recuento de símbolos describe el binario, no qué código es alcanzable desde el driver
  presente.
- `GFX_HWIP` no establecido (§6).
- Sin Ghidra, el análisis estático inicial se apoya en rizin/radare2, que dan desensamblado
  correcto pero sin análisis de flujo de datos.

## Procedencia

Todas las cifras de este documento se obtuvieron ejecutando los comandos indicados, sobre
`/lib/modules/7.1.3-200.nobara.fc44.x86_64/kernel/drivers/gpu/drm/amd/amdgpu/amdgpu.ko.zst`
(`srcversion` `D68004925455E20A24C2B87`), el 2026-09-29. Ninguna transcrita de documentación ni
de memoria. Las tres rutas erróneas de la orden de trabajo se reportan como
`REFERENCE_STATUS=BROKEN` con su verificación, sin repararlas silenciosamente.

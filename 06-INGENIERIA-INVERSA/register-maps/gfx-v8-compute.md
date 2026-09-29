# Mapa de registros — GFX8 compute (plantilla inicial)

**Clasificación**: `STATIC_IMPLEMENTATION` (documento) / `NOT_STARTED` (contenido)
**Fecha de creación**: 2026-09-29
**Ámbito**: IA-1 Ingeniero Inverso, `06-INGENIERIA-INVERSA/register-maps/`
**Hardware objetivo**: AMD Radeon RX 550, Polaris 12, PCI `1002:699f`
**Objeto de referencia**: `amdgpu-analysis/amdgpu.ko`, SHA256
`a1a44c2457d33c65149ef4f455173ca446564bfd19bcc9cb215fca10cf24c024`

---

> **PENDIENTE — requiere análisis con UMR y Ghidra.**
>
> Ninguna tabla de este documento está rellena. Es la estructura que se rellenará en rondas
> posteriores. Un encabezado vacío no es un dato: no hay ningún offset, ningún nombre de registro
> y ningún valor confirmado aquí.
>
> Dos salvedades sobre las herramientas que faltan, medidas el 2026-09-29:
>
> - **Ghidra no está instalado** (`rpm -q ghidra` → no instalado; `ghidra`, `ghidraRun`,
>   `analyzeHeadless` no en `PATH`; `find /` sin resultados). No es un problema de ruta.
> - **UMR sí está** (`/usr/bin/umr`, v1.0.0, build 2026-01-17) pero **no se ha ejecutado**:
>   requiere autorización de `RUNTIME_EXECUTION` que este ámbito no tiene por omisión. `AGENTS.md`
>   prohíbe ampliar una autorización.
>
> **La vía principal no necesita ninguna de las dos.** La fuente del módulo está en el repositorio:
> `RESEARCH/working/linux-7.1.3/drivers/gpu/drm/amd/amdgpu/`. El mapa se construye leyendo C, y
> el desensamblado (rizin/radare2, presentes) sirve de verificador.

---

## 1. Fuentes de verdad para este mapa

| Fuente | Ubicación | Para qué |
|---|---|---|
| `amdgpu.h` | `RESEARCH/working/linux-7.1.3/…/amdgpu/` | `struct amdgpu_device` (líneas 858-1201) |
| `amdgpu_ring.h`, `amdgpu_ring.c` | ídem | `struct amdgpu_ring`, `struct amdgpu_queue` |
| `amdgpu_sdma.h` | ídem | Definiciones de packet type PM4 |
| `lsdma_v7_1.h`, `lsdma_v6_0.h` | ídem | **LSDMA de GFX8** (ver `003` §5) |
| `amdgpu_kcq.c` / `amdgpu_kgq.c` | ídem | Setup de cola, equivalente C de `enable_kcq`/`enable_kgq` |
| `amdgpu_vm.c`, `amdgpu_vm_pt.c` | ídem | Page tables |
| `soc15.c` | ídem | **Mapa de registros IP-version-neutro** |
| `amdgpu_discovery.c` | ídem | Detección de ASIC, para resolver `GFX_HWIP` |
| headers UAPI | `/usr/src/kernels/7.1.3-200.nobara.fc44.x86_64/include/uapi/drm/` | `amd_drm.h`, `amdgpu_drm.h`: la interfaz de userspace |

**`soc15.c` es el archivo clave y no se había considerado.** En GFX8 el acceso a registros no es
un `writel` directo sino a través de `soc15_wreg`/`soc15_rreg` con una indirección de IP version.
Un mapa de registros escrito contra `writel` sobre GFX8 sería incorrecto.

## 2. PM4 packet types

**Estado**: vacío.

| Packet type | Valor | Estado | Fuente prevista |
|---|---|---|---|
| `PACKET3_PKT` (header) | — | `NOT_STARTED` | `amdgpu_sdma.h` |
| `PACKET3_WRITE_REG` | — | `NOT_STARTED` | `amdgpu_sdma.h` |
| `PACKET3_WRITE_MDW` | — | `NOT_STARTED` | `amdgpu_sdma.h` |
| `PACKET3_ATOMIC` | — | `NOT_STARTED` | `amdgpu_sdma.h` |
| `PACKET3_EVENT_WRITE` | — | `NOT_STARTED` | `amdgpu_sdma.h` |
| `PACKET3_DISPATCH` | — | `NOT_STARTED` | `amdgpu_sdma.h` |

> Nota: en GFX8 la numeración es `PACKET3_*` (heredada de la generación anterior), no
> `NTB_*`. Verificar contra la fuente antes de escribir valores.

## 3. Compute ring registers

**Estado**: vacío.

| Registro | Offset | Descripción | Estado |
|---|---|---|---|
| `CP_RB_BASE` | — | Base del ring buffer en VRAM | `NOT_STARTED` |
| `CP_RB_RPTR` | — | Puntero de lectura (escrito por la HW) | `NOT_STARTED` |
| `CP_RB_WPTR` | — | Puntero de escritura (escrito por la SW) | `NOT_STARTED` |
| `CP_RB_WPTR_OFFSET` | — | Automatismo de sincronización de WPTR | `NOT_STARTED` |
| `CP_RB_RPTR_OFFSET` | — | Automatismo de sincronización de RPTR | `NOT_STARTED` |
| `CP_RB_CNTL` | — | Control del ring (mode, pipe) | `NOT_STARTED` |
| `CP_START` | — | Arranque del command processor | `NOT_STARTED` |
| `CP_STATUS` | — | Ring busy, IDs activos | `NOT_STARTED` |
| `GFX_RS_EXC_STATUS` | — | Excepciones de shader | `NOT_STARTED` |
| `CP_CNTX_STATUS` | — | Estado de contexto | `NOT_STARTED` |

> Todos estos nombres son **suposiciones de nomenclatura**, no offsets verificados. Proceden de
> la familia GFX y pueden no coincidir en GFX8: la numeración de registros cambió entre
> generaciones y `soc15.c` decide el mapeo real. Deben confirmarse leyendo
> `lsdma_v7_1.h` y `amdgpu_sdma.h` **antes** de usarse. No se acepta un offset de esta tabla
> sin fuente.

## 4. VM page tables

**Estado**: vacío.

| Elemento | Estado | Fuente |
|---|---|---|
| Estructura de la PTE (flags, formato de 64 bits) | `NOT_STARTED` | `amdgpu_vm.h`, `amdgpu_vm_pt.c` |
| `AMDGPU_PTE_*` flags | `NOT_STARTED` | `amdgpu_vm.h` |
| Tipo de page directory para GFX8 | `NOT_STARTED` | `amdgpu_vm_pt.c` |
| Translation table (TT) de 4 páginas, 2 MB | `NOT_STARTED` | `amdgpu_vm.c` |
| Root de la UVM | `NOT_STARTED` | `amdgpu_amdkfd_gpuvm.c` |

**Precedente ya establecido:** `DEC-1` del proyecto determina que la geometría de page table **es
por dispositivo**, verificada en `amdgpu_vm.c:2433-2440`. Esa línea es el punto de partida
obligatorio: la estructura no es genérica y no se puede asumir del código GFX genérico.

## 5. Loose ends para las próximas rondas

1. **`GFX_HWIP` sigue `NOT_DETERMINED`.** Es la primera tarea pendiente y bloquea la elección de
   `soc15` offsets: el mapa de registros depende de qué IP version reporte la GPU. Método: leer
   el registro de ASIC ID con UMR, bajo autorización de `RUNTIME_EXECUTION`. **No derivarlo del
   nombre del driver ni de las 191 referencias a `gfx_v8` en el módulo** — un solo `.ko` sirve a
   toda la familia ASIC.
2. **Vía KFD sin explorar.** `kgd_arcturus_hqd_sdma_load` (713 B) y `kgd_arcturus_hqd_sdma_dump`
   (717 B) existen en el módulo: el hardware de compute queue ya tiene soporte. Si KFD expone
   una API utilizable, no hace falta escribir el submit desde cero. `NOT_DETERMINED`.
3. **Naming LSDMA, no `amdgpu_sdma_*`.** Ver `003` §5. La nomenclatura de ABL/RADV no
   es transferible; un mapa construido contra `sdma_v3_0.h` apuntaría a la generación
   equivocada.
4. **Los 4 símbolos exportados son de ISP**, no de compute. Ninguna función de compute de
   `amdgpu.ko` es enlazable. Ver `003` §2.

## Registro de rondas

| Ronda | Fecha | Contenido | Estado |
|---|---|---|---|
| 1 | 2026-09-29 | Estructura y fuentes de verdad | `NOT_STARTED` en contenido |

# 009 — Estado de los tres bloqueos: por qué están bloqueados y cómo se abren

**Clasificación**: `READ_ONLY/EVIDENCE`
**Fecha**: 2026-09-29
**Ámbito**: IA-1, `06-INGENIERIA-INVERSA/`
**Motivo**: los tres bloqueos que me asignó el humano. En dos de ellos la causa es una y la
misma, y conviene que se lea una vez en lugar de tres.

---

## ⛔ RETRACTADO 2026-09-29 — este diagnóstico era incorrecto

**Los autogenerados SÍ estaban en el repo**, en
`drivers/gpu/drm/amd/include/asic_reg/gca/gfx_8_0_sh_mask.h` (1 136 970 B, 50 registros
`COMPUTE_*` con MASK y SHIFT).

Busqué en `drivers/gpu/drm/amd/amdgpu/` y en `include/`, y no en el subárbol hermano
`amd/include/`. Afirmé la ausencia con la misma seguridad que un hallazgo positivo, y
escribí que la vía quedaba cerrada dentro del repo. **No lo estaba.** `kernel-devel` se
instaló después y tampoco los trae: la instalación nunca fue la vía.

Decodificación completa en **`010-pgm-rsrc1-decoded.md`**. Este documento se conserva
porque el diagnóstico del CRC32 y de `GFX_HWIP` sigue siendo válido, pero **§1 y §2
quedan retractados**.

El error es el segundo caso de este proyecto de "se buscó donde no estaba y se concluyó
que no existía", tras `vulkan.h` en la Ronda 2. Los dos míos.

---

## 1. Causa raíz común: el árbol de referencia es parcial

`RESEARCH/working/linux-7.1.3/` contiene **632 ficheros** en `drivers/gpu/drm/amd/amdgpu/`, pero
**no es el kernel completo**. Faltan dos cosas que bloquean todo lo que requiere definiciones
de registros:

| Falta | Consecuencia |
|---|---|
| `include/uapi/` (completo) | El contrato con userspace no está. Se leyó de `/usr/src/kernels/7.1.3-200.nobara.fc44.x86_64/include/uapi/drm/amdgpu_drm.h`, **de la misma versión de kernel** |
| **Headers autogenerados de registros de IP** | Los nombres `mmCOMPUTE_*`, `__SHIFT`, `_MASK`, `GFX8_MM_SH` **no existen en el árbol** |

**El segundo es la causa de los bloqueos 1 y 2.** No es que no se haya buscado: es que los
ficheros que los definirían no están presentes.

Cadena de includes, verificada:

```
gfx_v8_0.c
  └─ amdgpu_gfx.h          (697 líneas, presente)
       └─ soc15.h          (presente)
            └─ nbio_v6_1.h, nbio_v7_0.h, nbio_v7_4.h, amdgpu_reg_state.h
```

Y el mecanismo por el que desaparecen los nombres:

```c
/* amdgpu.h:1351-1352 */
#define REG_FIELD_SHIFT(reg, field) reg##__##field##__SHIFT
#define REG_FIELD_MASK(reg, field)  reg##__##field##_MASK
```

`REG_FIELD_SHIFT(mmCOMPUTE_PGM_RSRC1, NUM_WORKGROUPS)` se expande por token-pasting a
`mmCOMPUTE_PGM_RSRC1__NUM_WORKGROUPS__SHIFT`. Ese símbolo lo define un fichero autogenerado que
**no está en el árbol**. De los 632 ficheros, solo hay **1** cabecera con nombre de registros de
IP.

**Consecuencia práctica:** el árbol no compila. `sizeof(struct amdgpu_device)` sigue siendo
`NOT_DETERMINED` por el mismo motivo que se registró en `001-amdgpu-overview.md` §5.1, y todo
lo que dependa de offsets con nombre sigue bloqueado.

## 2. Bloqueo `PGM_RSRC1` — los bits de `COMPUTE_PGM_RSRC1`

**Estado: `NOT_DETERMINED`, y ahora se sabe por qué.** No es una búsqueda que no hice: es un
símbolo que no existe en ninguna fuente disponible en este host.

### Lo que sí está establecido

`gfx_v8_0.c:1389, 1410, 1431` documenta los valores en comentarios, y **tres valores distintos
para el mismo registro** son evidencia sobre el campo:

| Valor | Comentario del driver | Contexto |
|---|---|---|
| `0x100004f` | `VGPRS=15 (64 logical VGPRs), SGPRS=1 (16 SGPRs), BULKY=1` | `gfx_v8_0.c:1389` |
| **`0x240`** | `SGPRS=9 (80 GPRS)` | `gfx_v8_0.c:1410`, tabla `sgpr1_init_regs` |
| `0x240` | `SGPRS=9 (80 GPRS)` | `gfx_v8_0.c:1431`, tabla `sgpr2_init_regs` |

Y `gfx_v9_0.c:4478-4529` da **más** valores de `SOC15_REG_ENTRY(GC, 0, mmCOMPUTE_PGM_RSRC1)`:
`0x3f`, `0xbf`, `0x240`, `0x240`.

### Lo que eso establece, y lo que no

**Establece:** el registro tiene **al menos dos campos con nombre** — uno de GPRs vectoriales
y otro de escalares — y un flag `BULKY` en el bit más alto (`0x100004f` tiene `0x1` en bit 28).
`SGPRS=9 ↔ 0x240` y `SGPRS=1 ↔ 0x4f` dan **dos puntos de la misma función lineal**, que es más
de lo que se tenía antes.

**NO establece:** el desplazamiento en bits de cada campo. `0x240` con `SGPRS=9` y `0x4f` con
`SGPRS=1` son consistentes con SGPRs en bits 6-9, o en 5-8, o con un campo repartido de otra
forma. **La aritmética de dos puntos no determina una distribución de bits**, y rellenar el
resto por interpolación sería inventar el campo que IA-2 necesita. No lo hago.

`0x240` = `0b10_0100_0000`, `0x4f` = `0b0100_1111`, `0x100004f` = `0b1_0000_0000_0000_0000_0100_1111`.
Que `BULKY` esté en bit 28 es `PLAUSIBLE` por posición, no verificado.

### Cómo se abre

Un solo camino: **el header autogenerado de registros de GFX8**, que en el árbol del kernel
completo se llama `amdgpu_gfxreg.h` (y sus equivalentes por IP version). Contiene
`mmCOMPUTE_PGM_RSRC1__SGPRS__SHIFT` y similares.

**Vía 1 — el repo. COMPLEMENTADA, resultado negativo.** El repo tiene cuatro árboles de kernel.
Se buscó en los cuatro:

| Árbol | `amdgpu_gfxreg.h` | `amdgpu_smc.c` | `amdgpu_drm.h` |
|---|---|---|---|
| `RESEARCH/working/linux-7.1.3` | ausente | ausente | ausente |
| `RESEARCH/kernelbuild/linux-7.1.3` | ausente | ausente | **presente** |
| `RESEARCH/baseline/linux-7.1.3` | ausente | ausente | — |
| `RESEARCH/kernelref/linux-7.1.3` | ausente | ausente | — |

**Ninguno tiene los autogenerados ni `amdgpu_smc.c`.** La vía queda cerrada dentro del repo.

Hallazgo lateral de esa búsqueda: `kernelbuild/linux-7.1.3/include/uapi/drm/amdgpu_drm.h`
existe y es **byte-idéntico** al de `/usr/src/kernels/7.1.3-...` (ambos 52 367 B, sha256
`182c9b617c40b5c8...`). Confirma que el contrato con userspace usado en `005` y `007` es el
correcto para esta versión, y ahora hay **dos copias verificadas dentro del repo** en vez de una
externa. Lo que no era de suponer: `kernelbuild` es un árbol *más* completo —635 ficheros de
`amdgpu/` frente a 632 de `working`, y con `include/`— pero **no** trae los autogenerados.

**Vía 2 — el paquete de headers completo.** `kernel-devel` en Fedora incluye headers de
drivers, no solo `include/uapi`. En este host solo está la parte de uapi. Es la vía más
directa que queda: instalar el paquete completo y buscar `amdgpu_gfxreg.h`. **No aplicada**:
requiere `sudo dnf`, que no está autorizado en este ámbito.

**Vía 3 — extraer del binario. `DEAD_END`, comprobado.** Los valores inmediatos del código
compilado no distinguen "registro con valor constante" de "máscara con constante", y la tabla
`sgpr1_init_regs` **no aparece como array contiguo** en `amdgpu.ko`: buscado el patrón de sus
siete primeros valores (`0x0f, 0x1000000, 1280, 1, 1, 0x240, 20`) como 28 B little-endian
contiguos, **no encontrado**. El compilador la reordenó o la partió.

**No voy a estimarlo.** Es el caso que el propio IA-2 formuló al pedir estas respuestas: *«un dato

## 3. Bloqueo CRC32 del firmware

**Estado: `NOT_DETERMINED`, causa distinta.** No es un problema de headers autogenerados.

El árbol **no contiene `amdgpu_smc.c`**, que es donde vive el parser de SMC y la verificación del
checksum. Lo que hay:

| Fichero | Qué hace con el CRC |
|---|---|
| `amdgpu_ucode.c:50` | **imprime** el campo: `DRM_DEBUG("crc32: 0x%08x\n", le32_to_cpu(hdr->crc32))` |
| `amdgpu_psp.c` | menciona `smc_hdr` pero no el CRC |
| `amdgpu_cgs.c` | menciona `smc_hdr` pero no el CRC |

**Imprimir no es verificar.** El driver carga el firmware y registra el CRC para diagnóstico;
la comprobación real —si la hay— está en el firmware de la PSP, no en el host.

Medición, en `008-firmware-blob.md` §5:

```
campo del header : 0xAE2B3B78
zlib.crc32(payload[256 : 256+130132]) = 0x9D6AEF38
```

No coinciden. Dos hipótesis, ninguna verificable aquí:

1. Polinomio o inicialización distintos del CRC32 estándar (AMD usa `crc32` con pre/post
   conditioning en varios sitios del driver).
2. El CRC se calcula sobre otro rango, por ejemplo incluyendo los **220 B** que hay entre
  `header_size_bytes` (36) y `ucode_array_offset` (256).

**No elijo entre las dos.** Para hacerlo haría falta el código que lo calcula.

### Cómo se abre

1. **`amdgpu_smc.c` del árbol completo del kernel** — la vía directa, y la primera que
   comprobaría.
2. La PSP de la GPU contiene la verificación, pero leerla requiere UMR y
   `RUNTIME_EXECUTION`.

**Impacto en Fase 4: bajo si solo se consume firmware, alto si se produce.** Un driver que
*carga* el blob del sistema no necesita calcular el CRC. Uno que lo *construye* sí.

## 4. Los tres bloqueos, en una tabla

| Bloqueo | Estado | Causa exacta | Vía de apertura | Coste |
|---|---|---|---|---|
| ~~`PGM_RSRC1` bits~~ | **RESUELTO** en `010` | — | ya está: `asic_reg/gca/gfx_8_0_sh_mask.h` | **cerrado** |
| CRC32 firmware | `NOT_DETERMINED` | `amdgpu_smc.c` ausente del árbol | `amdgpu_smc.c` | bajo: un fichero |
| `GFX_HWIP` | `NOT_DETERMINED` | requiere leer hardware, no código | UMR, ASIC ID | **alto: `RUNTIME_EXECUTION` no autorizado** |

**Los dos primeros son el mismo problema**: el repo tiene el `.c` de amdgpu pero no los
acompañantes que el `.c` incluye. Ninguno de los dos necesita autorización especial, solo el
fichero que falta.

**El tercero es distinto y no se resuelve leyendo código**, por la razón que `AGENTS.md`
documenta tras tres casos en este proyecto: se ha confundido el contenido del driver con las
capacidades del hardware tres veces, y una de ellas fue mía. `GFX_HWIP` requiere UMR.

## 5. Lo que no voy a hacer

No voy a rellenar los bits de `PGM_RSRC1` por interpolación de dos puntos, ni el CRC por
ensayo del polinomio, ni `GFX_HWIP` desde la PCI ID o desde el nombre del driver. Los tres son
`NOT_DETERMINED` con una vía de apertura identificada y un coste estimado, y eso es más útil
para el avance que un número sin fuente.

Lo que sí puedo hacer sin nuevo material, y ofrezco:

- **Comprobar si `RESEARCH/kernelbuild/linux-7.1.3` tiene los autogenerados.** No lo he
  verificado y es la vía más barata para los bloqueos 1 y 2. Dime y lo miro.
- Extraer de `gfx_v9_0.c` la lista completa de valores de `PGM_RSRC1` con sus contextos, que
  acota el campo por debajo aunque no lo determine.

## Procedencia

Cuentas de ficheros y búsqueda de includes ejecutadas sobre
`RESEARCH/working/linux-7.1.3/drivers/gpu/drm/amd/amdgpu/` el 2026-09-29. Macros
`REG_FIELD_SHIFT`/`REG_FIELD_MASK` de `amdgpu.h:1351-1352`. Valores de `PGM_RSRC1` de
`gfx_v8_0.c:1389,1410,1431` y `gfx_v9_0.c:4478-4529`. CRC de `008-firmware-blob.md` §5.
Búsqueda de la tabla `sgpr1_init_regs` como array contiguo en `amdgpu.ko`: no encontrada.

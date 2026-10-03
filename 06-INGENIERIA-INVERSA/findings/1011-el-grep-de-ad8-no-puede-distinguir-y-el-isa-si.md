# 1011 · El grep que refutó «no hay hardware BCn» no podía distinguir; y el campo `DATA_FORMAT` sí

```
CLASSIFICATION=CONTRADICTION+MEASUREMENT+NEGATIVE_RESULT · TRACK=STATIC
CORPUS=RESEARCH/working/linux-7.1.3 (headers asic_reg/gc) + /home/lucas/mesa 26.1-branchpoint-1415-gc5e413533f4
HARDWARE_SCOPE=HOST-C/RX550/0000:01:00.0 · 1002:699f rev c7 · TARGET_MATCH=VERIFICADO (lspci -nn -d 1002:699f)
WORK_CLASS=READ_ANALYSIS + WRITE_LOCAL · MODIFICATIONS=0 sobre el corpus
WRITE_EXECUTION=NONE · RUNTIME=NOT_RUN · GPU INTACTA · SIN MMIO · SIN DEBUGFS · SIN sudo
CORRECTS=AD-8 de 02-ARQUITECTURA/DECISIONS.md («Polaris 12 no descomprime BC3 en hardware»)
CORRECTS=04-IMPLEMENTACION/compressor/README.md §«Polar 12 no tiene decodificador BC3 por hardware»
CORRECTS=DECISIONS.md:896 (misma afirmación, misma base)
CONTINUES=981-el-backend-de-color-y-profundidad-tiene-cero-cobertura (midió 0 hallazgos de mmCB_)
AUTORIA=AGENT-21 (TEXTURE / MEMORY COMPRESSION)
```

## Qué resuelve

`AD-8` cierra con: **«Polaris 12 no descomprime BC3 en hardware»**, y lo apoya en un
`grep` sobre el árbol de amdgpu. De esa frase el proyecto colgó dos decisiones.

El resultado de este turno: **la conclusión de `AD-8` no está sostenida por su evidencia**,
y la evidencia que sí existe apunta al otro lado. No es «no se ha medido»: es que el
instrumento usado no puede producir esa respuesta, y hay un discriminante disponible que
no se ha usado.

## 1 · Por qué el grep de `AD-8` no puede distinguir

`AD-8` declara, sobre 36 695 ficheros de `drivers/gpu/drm/amd/`:

```
cero decodificadores BC3/DXT5
cero microcode de descompresión
cero soporte de formato de textura BCn (VK_FORMAT_BC*, DXGI_FORMAT_BC*)
```

Medido hoy sobre ese mismo árbol, token por token, **`\bBC[1-7]\b|DXT[15]|S3TC`**:

| token | ficheros en `drivers/gpu/drm/amd/` |
|---|---|
| `BC1` | **0** |
| `BC3` | **0** |
| `BC7` | **0** |
| `DXT1` / `DXT5` | **0** |
| `S3TC` | **0** |
| `ETC2` | **0** |
| `ASTC` | **0** |
| `008F14` / `IMG_RSRC` (descriptor de imagen) | **0** |

**El problema no es que dé cero. Es que da cero para todo.** Un instrumento que
devuelve la misma respuesta para BC3, para BC7, para ETC2 y para ASTC —y que además
no encuentra ni el registro que describe el formato de una imagen— no distingue
«este hardware no decodifica BC3» de «este software no habla de formatos de textura».

La causa es localizable y no es un error de tecleo: **el kernel nunca programa el
descriptor de imagen.** Cero escrituras a `R_008F14_SQ_IMG_RSRC_WORD1` en todo
`drivers/gpu/drm/amd/`. Ese registro lo escribe el espacio de usuario, en Mesa. Un
árbol que no lo programa no puede contener la lista de formatos que la texture unit
entiende, y buscarla ahí no es una ausencia: es una **búsqueda en el sitio
equivocado**. Es la categoría `NOT_FOUND` que `AGENTS.md` §10 prohíbe convertir en
ausencia.

`AD-8` llegó a la misma conclusión que `006-p9-hardware-vs-software.md` §5.1 ya
había declarado `FAIL` por método para el caso gemelo (buscar un descompresor BC3 en
`nm`/`strings` del binario instalado). Allá se Conclusions: «cero símbolos no es
evidencia de ausencia de código». Aquí la conclusión es la misma con otro grep, y no
se registró.

## 2 · El discriminante que sí existe: el campo `DATA_FORMAT` del descriptor de imagen

El descriptor de imagen **sí** tiene un campo enumerado de formato, y ese campo es
deliberadamente un registro de hardware, no una tabla de software.

Medido en `RESEARCH/working/linux-7.1.3/.../asic_reg/gc/gc_9_0_sh_mask.h:3521`:

```
SQ_IMG_RSRC_WORD1__DATA_FORMAT__SHIFT   0x14
SQ_IMG_RSRC_WORD1__DATA_FORMAT_MASK    0x03F00000L     -> 6 bits, valores 0..63
```

y el mismo campo en el header generado de Mesa, `build/src/amd/common/amdgfxregs.h:5880`:

```
R_008F14_SQ_IMG_RSRC_WORD1  0x008F14  /* <= gfx940 */
S_008F14_DATA_FORMAT(x)      (((unsigned)(x) & 0x3F) << 20)
C_008F14_DATA_FORMAT         0xFC0FFFFF
```

**6 bits = 64 formatos.** El hardware codifica el formato de la textura en el
descriptor. Ahora, qué formatos:

```
amdgfxregs.h:5890  V_008F14_IMG_DATA_FORMAT_INVALID   0
amdgfxregs.h:5916  V_008F14_IMG_DATA_FORMAT_ETC2_RGB  24  /* gfx81, gfx9, gfx940 */
amdgfxregs.h:5917  V_008F14_IMG_DATA_FORMAT_RESERVED_24  24  /* <= gfx8 */
amdgfxregs.h:5933  V_008F14_IMG_DATA_FORMAT_BC1       35
amdgfxregs.h:5935  V_008F14_IMG_DATA_FORMAT_BC3       37
amdgfxregs.h:5939  V_008F14_IMG_DATA_FORMAT_BC7       41
amdgfxregs.h:5950  V_008F14_IMG_DATA_FORMAT_ASTC_2D_LDR 46  /* gfx9, gfx940 */
```

**La convención de anotación es el control.** El registro se genera desde la base de
datos de registros de AMD, y anota por generación *qué valores existen en cuál*.
Medido sobre el fichero completo: los valores que llevan alias `RESERVED_n /* <= gfx8 */`
—es decir, los que **no** existen en gfx8— son exactamente

```
15, 23, 24, 25, 26, 27, 28, 31, 42, 43
```

y en ese conjunto **no aparece ninguno de 35..41**. El control es interno al propio
registro: el mismo fichero, con la misma convención, marca como ausentes en gfx8 a
`ETC2` y a `ASTC`, y **no** marca a `BC1..BC7`. El instrumento distingue; el finding
anterior no lo usó.

Eso no prueba todavía que el *decodificador* esté en el silicio. Prueba que el
formato está **en el espacio de codificación del hardware de esta generación**, y que
el driver lo escribe. Falta el último enlace, y se mide abajo.

## 3 · El driver escribe BC3 en el descriptor, en gfx8, sin gate

Productor del enlace, medido en `/home/lucas/mesa/src/amd/common/ac_formats.c:319-333`:

```c
if (desc->layout == UTIL_FORMAT_LAYOUT_S3TC) {
   switch (desc->format) {
   case PIPE_FORMAT_DXT1_RGB:  ...
      return V_008F14_IMG_DATA_FORMAT_BC1;
   case PIPE_FORMAT_DXT3_RGBA: ...
      return V_008F14_IMG_DATA_FORMAT_BC2;
   case PIPE_FORMAT_DXT5_RGBA:
   case PIPE_FORMAT_DXT5_SRGBBA:
      return V_008F14_IMG_DATA_FORMAT_BC3;
```

**No hay ningún `if (info->gfx_level …)` en esa rama.** El grep sobre el bloque, medido,
devuelve vacío. El mapeo BC3↔37 es incondicional con respecto a la generación.

Consumidores de `V_008F14_IMG_DATA_FORMAT_*` en Mesa: 78 usos en 5 ficheros
(`ac_descriptors.c`, `ac_formats.c`, `ac_nir_to_llvm.c`, `radv_formats.c`,
`si_descriptors.c`). En `ac_nir_to_llvm.c:1300-1309` se **ensambla el immediate en el
LLVM IR** que se escribe al descriptor: la cadena llega al hardware.

## 4 · La predicción del driver sobre esta GPU concreta, y por qué discrimina

`AD-8` predice «no hay decodificador BC3 en hardware». Esa predicción tiene
consecuencias observables, y las dos son medibles sin ejecutar nada:

| | si `AD-8` es correcta | si el hardware decodifica BCn |
|---|---|---|
| Mesa debe emular BC3 en algún sitio de radeonsi/RADV | **sí, y sería un `grep` positivo** | no: no hay nada que encontrar |
| RADV debe exponer BC3 como `SAMPLED` | no puede, o la imagen va a fallar | **sí** |
| `DATA_FORMAT` 35..41 debe estar en el espacio de gfx8 | no | **sí** |

Medido: `radv_formats.c:266` **no** gatea BCn por `gfx_level`. El único gate de BCn que
existe es el contrario del que `AD-8` predice — una restricción que empieza **en** GFX9:

```c
/* GFX9-GFX11.5 have issues with BCn formats and mipmaps which isn't really possible
 * to support with indirect image copies. */
if (vk_format_is_block_compressed(format) && (pdev->info.gfx_level >= GFX9 && pdev->info.gfx_level < GFX12))
   return false;
```

Es decir: el driver trata BCn como **disponible desde gfx8**, y lo que marca como
problemático es el tramo siguiente. Si BCn no existiera en gfx8, ese `>= GFX9` no
tendría sentido: la limitación sería de todos, no de un rango.

Y hay una medición de este host que ya apuntaba en la misma dirección y que `AD-8`
no lo recoge: `08-ARQUITECTURA/validations/2026-09-29-f1-format-capability.md` §3 midió en
`1002:699f` que `VK_FORMAT_BC3_UNORM_BLOCK` tiene `FORMAT_FEATURE_2_SAMPLED_IMAGE_BIT`
`0x1`, y §4.2 que **no** tiene `STORAGE_IMAGE` ni `COLOR_ATTACHMENT`. Eso es
consistente con hardware: la textura se decodifica en la texture unit al muestrear, y
no hay superficie de *lectura de texel comprimido* por shader — que es exactamente lo
que se observaría **si** el decompresor está en el silicio y no en un shader.

## 5 · Estado corregido

| Afirmación | Antes | Ahora |
|---|---|---|
| `DATA_FORMAT` codifica BC1..BC7 en gfx8 | no medido | **`OBSERVED`**, valores 35..41 sin alias `RESERVED <= gfx8` |
| el driver escribe BC3 en el descriptor en gfx8 | no medido | **`OBSERVED`**, sin gate por `gfx_level` |
| la textura BC3 llega a la texture unit de esta GPU | no medido | **`OBSERVED`** por los tres eslabones |
| **«Polaris 12 no descomprime BC3 en hardware»** | `PROVEN` (por grep) | **`REFUTED` como inferencia**; el grep era `FAIL` por método, §1 |
| el silicio ejecuta la decodificación al muestrear | — | **`NOT_DETERMINED`** — ver §6 |
| la rampa alfa que aplica la texture unit (`AD-12`) | `NOT_DETERMINED` | **`NOT_DETERMINED`**, sin cambio |

**Lo que queda abierto y por qué no lo cierro aquí.** Falta el eslabón final: que la
texture unit *ejecute* la decodificación y con qué aritmética. Es `RUNTIME_ACTIVO` y
exige GPU; esta ronda es `READ_ANALYSIS`. Y no lo doy por hecho aunque el resto apunte
ahí: que el formato esté codificado y que el driver lo escriba es `OBSERVED`, no
`PROVEN` de ejecución. `AD-12` sigue exactamente donde estaba.

## 6 · Lo que este hallazgo **no** cambia

- **BC3 es BC3/DXT5.** `AD-8` acertó en esto, y su corrección del nombre `RX550_BC4X`
  se sostiene: el error estaba en la **premisa** (no hay decodificador en hardware), no
  en la conclusión sobre el formato. Este hallazgo **retira la premisa, no el formato**.
  El argumento de `AD-8` para preferir BC3 estándar —que `bcdec`, `basisu` y los
  visores leen estos bloques— sigue siendo bueno, y ahora es más fuerte: si el hardware
  lo decodifica, cualquier implementación de BC3 coincide con el hardware.
- **El decompresor por shader sigue siendo correcto y sigue siendo una opción.** El
  proyecto lo validó byte a byte en la RX 550 (`04-IMPLEMENTACION/decompressor/README.md`
  §Validation status). Que exista decodificador en el silicio no invalida un
  descompresor por shader; lo que cambia es que **no es el único camino**, y que
  `README.md` §«Known deviation» y `003-fase3-pipeline-grafico.md:71` («hardware
  dedicado, no instrucciones») ya trataban la posibilidad contraria sin medirla.
- **`RX550_BC4X` no vuelve.** El formato inventado sigue sin justificarse.

## 7 · Reproducción

```sh
# §1: el token BC3 no distingue (0 en todo el driver, incluidos formatos que sí existen)
cd RESEARCH/working/linux-7.1.3/drivers/gpu/drm/amd
for t in BC1 BC3 BC7 DXT1 DXT5 S3TC ETC2 ASTC; do
  printf "%-6s %s\n" "$t" "$(grep -rl "\b$t\b" . | wc -l)"; done
grep -rn "008F14\|IMG_RSRC" --include="*.c" . | wc -l      # -> 0

# §2: el campo, su anchura, y el control de la convención
sed -n '3521p' drivers/gpu/drm/amd/include/asic_reg/gc/gc_9_0_sh_mask.h
grep -n "V_008F14_IMG_DATA_FORMAT_BC[1-7] \|V_008F14_IMG_DATA_FORMAT_RESERVED_.*gfx8" \
     /home/lucas/mesa/build/src/amd/common/amdgfxregs.h

# §3: el productor, sin gate por generación
sed -n '319,333p' /home/lucas/mesa/src/amd/common/ac_formats.c

# §4: el driver ofrece BCn en gfx8 y marca como problemático el rango siguiente
sed -n '262,268p' /home/lucas/mesa/src/amd/vulkan/radv_formats.c
```

Sin escrituras fuera de `06-INGENIERIA-INVERSA/findings/`. Sin `sudo`. Sin cambios de sistema.
# 016 — Q-5 preregistrado: la ruta BC3 de llvmpipe, verificada estáticamente

**Fecha**: 2026-09-29 · **Ámbito**: `06-INGENIERIA-INVERSA/`
**Árbol verificado**: `/home/lucas/mesa`, `26.1-branchpoint-1415-gc5e413533f4`
**Método**: lectura de fuente. **No se ha ejecutado nada.**

---

## Qué se preguntaba

Si una textura BC3/DXT5 creada por la vía relevante de llvmpipe alcanza
efectivamente esta cadena:

```
glTexImage / texture setup
      ↓
sampler llvmpipe
      ↓
generate_update_cache_one_block()
      ↓
s3tc_decode_block_dxt5()
      ↓
lp_build_lerpdxta()
```

En dos puntos independientes: **A. CAPACIDAD** y **B. ALCANCE**.

---

## A. CAPACIDAD — ¿llvmpipe acepta BC3?

### `BC3 ACCEPTED BY RELEVANT PATH` → **`PROVEN`**

La respuesta la da `llvmpipe_is_format_supported()` (`lp_screen.c:639-763`). Sus
tres guardas que podrían rechazar BC3 **no lo hacen**:

| Guarda | Condición | BC3/DXT5_RGBA_UNORM |
|---|---|---|
| `lp_storage_render_image_format_supported` | solo si `PIPE_BIND_RENDER_TARGET` | no se pide: es `PIPE_TEXTURE_SAMPLER_VIEW` |
| `lp_storage_image_format_supported` | solo si `PIPE_BIND_SHADER_IMAGE` | no se pide |
| 3 canales con `block.bits != 96` | solo si `PIPE_BIND_RENDER_TARGET \| SAMPLER_VIEW` | DXT5 tiene 4 canales, no 3 |

Y el cierre de la función es explícito sobre por qué:

```c
   /*
    * Everything can be supported by u_format
    * (those without fetch_rgba_float might be not but shouldn't hit that)
    */
   return true;
```

**Consecuencia para la vía C de `004`.** Laattachment del FBO **no puede ser
BC3**, porque `lp_storage_render_image_format_supported` no lista ningún formato
DXT (medido: 0 ocurrencias de `DXT` en la lista, `lp_screen.c:576-628`). La
textura BC3 es de **lectura**; el attachment del FBO es un target RGBA
convencional. Es lo que `004` §9 señalaba como riesgo residual, y queda
aclarado: no es un límite del driver sino de la API — un attachment
compressed no tiene sentido en GL.

### El binary importa

`lp_storage_image_format_supported` no es la función que decide. La que decide
es `llvmpipe_is_format_supported`, que llama a la anterior **solo** para
`RENDER_TARGET` y `SHADER_IMAGE`. Confundir las dos es el error que produce
«BC3 no está en la lista, luego no se puede muestrear». Está en la lista
porque no se le pregunta en esta vía.

---

## B. ALCANCE — ¿la textura BC3 alcanza el `case`?

### `GENERATE_UPDATE_CACHE_ONE_BLOCK REACHED BY BC3 PATH` → **`PROVEN`**

Cadena de llamadas, cada eslabón con su invocante verificado:

| # | Función | Fichero:línea | Invocada desde |
|---|---|---|---|
| 1 | `lp_build_lerpdxta` | `lp_bld_format_s3tc.c:818` | `s3tc_dxt5_alpha_channel` `:985` |
| 2 | `lp_build_lerpdxta_block` | `:1542` | `s3tc_decode_block_dxt5` `:1725-1726` |
| 3 | `s3tc_decode_block_dxt5` | `:1596` | `generate_update_cache_one_block` `:1947` |
| 4 | `generate_update_cache_one_block` | `:1902` | `update_cached_block` `:2005` |
| 5 | `update_cached_block` | `:1968` | `compressed_fetch_cached` `:2105, :2131` |
| 6 | `compressed_fetch_cached` | `:2022` | `lp_build_fetch_s3tc_rgba_aos` `:2196` |
| 7 | `lp_build_fetch_s3tc_rgba_aos` | `:2175` | `lp_build_fetch_rgba_aos` `lp_bld_format_aos.c:740` |
| 8 | `lp_build_fetch_rgba_aos` | `lp_bld_format_aos.c:468` | `lp_build_fetch_rgba_soa` `lp_bld_format_soa.c:791` |
| 9 | `lp_build_fetch_rgba_soa` | `:409` | `lp_build_sample_texel_soa` `lp_bld_sample_soa.c:230` |
| 10 | `lp_build_sample_texel_soa` | `lp_bld_sample_soa.c:122` | `lp_build_sample_image_nearest` `:1045` |

Y el `case` que lo alcanza:

```c
/* generate_update_cache_one_block, lp_bld_format_s3tc.c:1944-1947 */
      case PIPE_FORMAT_DXT5_RGBA:
      case PIPE_FORMAT_DXT5_SRGB:
         s3tc_decode_block_dxt5(gallivm, format_desc->format, dxt_block, col);
```

### Las dos condiciones bajo las que se cumple

El eslabón 8→9 no es incondicional: `lp_build_fetch_rgba_soa` tiene una rama
`PLAIN` que gestiona el caso rápido y **delega a la ruta AOS** para
`LAYOUT_S3TC` (`lp_bld_format_soa.c:760-765`):

```c
   if ((format_desc->layout != UTIL_FORMAT_LAYOUT_PLAIN) &&
       (util_format_fits_8unorm(format_desc) ||
        format_desc->layout == UTIL_FORMAT_LAYOUT_RGTC ||
        format_desc->layout == UTIL_FORMAT_LAYOUT_S3TC) &&
       type.floating && type.width == 32 && ...)
```

Condiciones para que BC3 llegue a `lp_build_lerpdxta`:

| # | Condición | Se cumple con |
|---|---|---|
| 1 | El formato tiene `layout == UTIL_FORMAT_LAYOUT_S3TC` | `PIPE_FORMAT_DXT5_RGBA_UNORM` sí, por `u_format_s3tc.c` |
| 2 | El destino es float de 32 bits, longitud 1 o múltiplo de 4 | `lp_build_sample_texel_soa` muestrea a float32; la longitud la fija el ancho del vector de fetch |

Ambas son propiedades del **formato de entrada** y del **destino del shader**,
no del camino que se elija. Ninguna es una barrera: un shader que sample en
`float4` cumple las dos.

**El punto 3 es el que cierra la pregunta**: los 649 casos de
`casos_llvmpipe_unico.json` son bloques BC3, y un bloque BC3 **es** un
formato `LAYOUT_S3TC`. No hay ninguna condición restante que pueda hacer que
la cadena no se recorra.

---

## Clasificación

| Pregunta | Estado |
|---|---|
| `BC3 ACCEPTED BY RELEVANT PATH` | **`PROVEN`** |
| `GENERATE_UPDATE_CACHE_ONE_BLOCK REACHED BY BC3 PATH` | **`PROVEN`** |

Ninguna de las dos queda `NOT_DETERMINED` **en el árbol**.

---

## Lo que esto NO cierra

### 1. El árbol no es el binario

`/home/lucas/mesa` es `26.1-branchpoint-1415-gc5e413533f4`; el driver instalado
es `mesa-dri-drivers-26.2.3-1.fc44`. Misma serie menor, commit no verificado.
La cadena está probada en el **código fuente**, no en lo que se ejecuta. Es
`PROVEN` para el árbol y `PLAUSIBLE` para el binario. `014` §Procedencia
registra la misma salvedad para el caso del descompresor.

### 2. Estar en la ruta no prueba que se recorra

Que `lp_build_lerpdxta` esté en el camino del muestreador **no** prueba que
un `glTexImage` concreto la recorra. Falta ejecución. Eso es Q-5, y no se
puede resolver leyendo.

### 3. El pre-registro se cierra con un nombre, no con una cifra

`1e28733` llama a este conjunto «el discriminante». La clasificación correcta
es la de `015`: los 649 son **equivalentes en poder discriminante**, y la
división 271/378 que circuló era falsa.

---

## Q-5: estado tras este documento

| | |
|---|---|
| Preregistro estático | **CERRADO**: A `PROVEN`, B `PROVEN` en el árbol |
| Ejecución | **`NOT_DETERMINED`** |
| Autorización necesaria | `RUNTIME_EXECUTION` de software |

Q-5 **no necesita la RX 550**. `llvmpipe` es `deviceType = CPU` y se selecciona
con `VK_ICD_FILENAMES=/usr/share/vulkan/icd.d/lvp_icd.x86_64.json`, verificado
en este host. La autorización es para ejecutar el rasterizador por software,
que es un clase de riesgo distinta de la medición de AD-12 sobre el sampler de
hardware.

**Diferencia con AD-12, y conviene no mezclarlas:**

| | Recurso | Clase |
|---|---|---|
| **Q-5** | llvmpipe, CPU | `RUNTIME_EXECUTION` de software |
| **AD-12** | RX 550, sampler | `RUNTIME_EXECUTION` de hardware |

---

## Falsificación de este documento

1. `llvmpipe_is_format_supported` rechaza DXT5 por una guarda no listada aquí.
   **Descartado**: se leyeron las tres guardas del cuerpo completo.
2. `lp_build_lerpdxta` es alcanzable solo por un camino que no usa el
   experimentador. **Descartado**: la cadena del punto B se trazó hacia atrás
   desde `lp_build_sample_image_nearest`, que es la entrada del muestreador.
3. El árbol instalado y el binario tienen caminos distintos para BC3.
   **No descartado.** Solo Q-5 puede resolverlo.
4. El attachment del FBO de `004` tiene que ser BC3. **Descartado por la
   propia API**, no por el driver: un attachment compressed no existe en GL, y
   la textura BC3 es de lectura.

# @IA-3 (Arquitecto): Pregunta de IA-1 sobre LSDMA vs SDMA

**Fecha**: 2026-09-29
**Ronda**: 2
**De**: IA-1 (Ingeniero Inverso), `06-INGENIERIA-INVERSA/`
**Para**: @IA-3 (Arquitecto), `08-ARQUITECTURA/`
**Directorio**: este es `06-INGENIERIA-INVERSA/outgoing-reviews/`, siguiendo la corrección de
protocolo de Ronda 2. No he escrito en `08-ARQUITECTURA/`.

**Pregunta planteada en el brief:** ¿el diseño debe usar LSDMA exclusivamente, o hay fallback a
SDMA?

**Respuesta corta: el formato de packet es el mismo en ambos. La pregunta, tal como está
planteada, separa dos cosas que no están separadas.**

---

## 1. Lo que encontré, y corrige la pregunta

En la Ronda 1 dije que "el envío PM4 es LSDMA, no `amdgpu_sdma`". Es cierto a nivel de
**símbolos y ficheros**, y lo voy a precisar porque la distinción importa para el diseño:

| Aspecto | SDMA heredado | LSDMA (esta generación) |
|---|---|---|
| Símbolos | `amdgpu_sdma_*` | `dmub_lsdma_*` |
| Ficheros | `sdma_v2_4.c` … `sdma_v7_1.c` | `lsdma_v6_0.c`, `lsdma_v7_1.c` |
| Tabla de dispatch | `amdgpu_sdma_funcs` | `amdgpu_lsdma_funcs` |
| **Formato de packet** | **`sid.h`, común** | **`sid.h`, común** |
| Nombres de packet | `PACKET3_*` | `PACKET3_*`, **los mismos valores** |

**El formato de packet no cambia.** Es el mismo `PACKET3_*` de `sid.h` para ambos. Lo que cambia
es la *tabla de funciones* que implementa el envío.

Consecuencia para el diseño: **un driver propio define los `PACKET3_*` una vez**, no dos juegos
de constantes. La decisión real no es "LSDMA o SDMA" sino **qué tabla de funciones implementa el
envío, y esa elección es por versión de IP**.

## 2. `lsdma_v*.h` no contiene los formatos

`lsdma_v7_1.h` tiene **31 líneas** y su contenido útil es una línea:

```c
extern const struct amdgpu_lsdma_funcs lsdma_v7_1_funcs;
```

Es una tabla de punteros a función: el *dispatch* por versión, no el *formato*. Los formatos
están en `sid.h`, común a todas las generaciones, replicado en `cikd.h`, `nvd.h` y
`gfx_v12_1_pkt.h`.

**Que GFX12 tenga su propio `gfx_v12_1_pkt.h` confirma que el formato sí cambia entre
generaciones, aunque no entre SDMA y LSDMA dentro de esta.** Un driver que incluya solo
`lsdma_v*.h` esperando formatos de paquete no los encuentra.

## 3. Lo que sí está verificado, para la decisión

**El dispatch de compute en GFX8, literal** (`gfx_v8_0.c:1535-1564`): 5 pasos, y el orden
importa.

1. `SET_SH_REG` (0x76) de 2 dwords → dirección del shader
2. `DISPATCH_DIRECT` (0x15, `sub_op` 3) → grid `8×1×1` + `COMPUTE_SHADER_EN=1`
3. `EVENT_WRITE` (0x46, `sub_op` 0) → flush parcial, `EVENT_TYPE(7)|EVENT_INDEX(4)`
4. `SET_SH_REG` de 1 dword × 17 → `sgpr1_init_regs`
5. `SET_SH_REG` de 2 dwords → **la misma dirección otra vez**, con `>> 8`

**El paso 5 repite el paso 1 con una escala distinta.** No es redundancia eliminable:
`OBSERVED` en el código, y un driver propio que escriba la dirección una vez, u olvide el
`>> 8`, produce un fallo que **no se manifiesta como error de compilación** sino como dispatch
incorrecto.

**El header de packet** (`cikd.h:495-497`): `op[7:0] | sub_op[7:8] | e[15:16]`. El `sub_op` es
el header type y determina cuántos dwords de payload siguen. Fijar `op` bien y `sub_op` mal
desalinea todo lo que viene después.

**El grid por defecto** (`gfx_v8_0.c:1403-1420`): `NUM_THREAD_X = 1280` (5 workgroups de 256),
`Y = Z = 1`, `CU_GROUP_COUNT=1`, `SGPRS=9`, y 10 registros `USER_DATA` con el patrón marcador `0xedcedc00..09`. El
`8×1×1` del `DISPATCH_DIRECT` es una unidad distinta, no la misma cifra en otro sitio.

Existe además una **segunda tabla**, `sgpr2_init_regs`, idéntica salvo
`STATIC_THREAD_MGMT_SE0` (`0x0f` frente a `0xf0`). Cuál se selecciona y por qué **no se ha
seguido**: `NOT_DETERMINED`, y un driver propio tiene que elegir entre las dos.

Detalle completo, con los 17 registros y sus valores, en
`06-INGENIERIA-INVERSA/findings/006-lsdma-packets.md` §4 y §4.1.

## 4. Lo que no puedo responder todavía

**No he analizado el contenido de `amdgpu_lsdma_funcs` ni de `amdgpu_sdma_funcs`.** No sé qué
función hace cuál. Sin eso, la pregunta "¿LSDMA o fallback a SDMA?" **no tiene respuesta
fundamentada todavía**, y darla sería razonar sobre nombres de fichero.

Es la primera tarea que propongo para la Ronda 3, y es trabajo de fuente, no de binario:
`lsdma_v7_1.c` y `lsdma_v6_0.c` existen en el árbol.

Dos bloqueos que vienen de la Ronda 1 y siguen abiertos:

- **`GFX_HWIP` = `NOT_DETERMINED`.** Elegir la tabla de funciones por versión de IP **depende de
  saber qué IP version reporta la GPU**. Sin eso, "elegir la tabla correcta" no es decidible.
  Método: leer el ASIC ID con UMR, que requiere `RUNTIME_EXECUTION` que no tengo.
- **`D26b`, firma de módulos, sin decisión.** Es tuya y del humano.

## 5. Una corrección al brief de Ronda 2, para que no se propague

El brief nombra el struct de userspace **`drm_amdgpu_cs_req`**. Ese tipo **no existe**. El
contrato real es `union drm_amdgpu_cs` (`amdgpu_drm.h:983-986`), con `drm_amdgpu_cs_in` de 5
campos y `drm_amdgpu_cs_out` de 1.

Lo relevante para el diseño, y no lo veo recogido en ninguna parte del brief:

- **`chunks` es una doble indirección**: `__u64 *` que apunta a un array de `__u64`, cada uno
  a un chunk. Tratarlo como array contiguo corrompe memoria en el primer submit.
- **`length_dw` está en dwords, no en bytes.** Leerlo como bytes acepta chunks 4× más largos.
- **`va_start` es una dirección virtual.** Se resuelve a física en `amdgpu_cs_vm_handling`, que
  es donde se toca la page table. Escribir la VA sin resolverla hace que la HW lea de una
  dirección no mapeada.
- **`ip_type` + `ip_instance` eligen el destino**, y **no hay un campo "es compute"**. El
  cliente declara a qué IP envía. Un ioctl de compute propio puede fijar `ip_type`, pero eso
  cambia la semántica respecto a AMD y obliga a rechazar o traducir submits que usen el campo.
- **`amdgpu_cs_ioctl` son 63 líneas de C, no 8 107 bytes de complejidad.** Es una secuencia
  lineal de 8 llamadas, con **doble pasada** sobre los chunks (pass1/pass2) deliberada, y dos
  rutas de error distintas según haya o no tomado `bo_list_mutex`. El binario de 8 107 B
 incluye `__fentry__`, `-O2` y el código `.cold`; el binario **no** es un indicador de
  complejidad.

Detalle en `06-INGENIERIA-INVERSA/findings/005-cs-ioctl-analysis.md`.

## 6. Lo que pido a IA-3

No una decisión sobre LSDMA vs SDMA, sino el criterio para dos cosas:

1. **¿Se fija `ip_type` en el ioctl de compute propio, o se acepta del cliente como hace
   AMD?** Es la primera decisión de diseño que choca con la compatibilidad, y la puedo
   implementar de cualquier forma; lo que necesito saber es cuál es la intención.
2. **¿El ioctl propio reutiliza `union drm_amdgpu_cs` o define la suya?** Reutilizar da
   compatibilidad con libdrm y con el código de usuario existente. Definir la propia simplifica
   el control pero obliga a reimplementar el cliente.

Y una advertencia sobre el alcance: el formato de packet está leído de la fuente, **nada se ha
ejecutado**. `OBSERVED` en el código, no validado contra hardware.

## Respuesta de IA-3

<!-- Escribe aquí. -->

_Pendiente._

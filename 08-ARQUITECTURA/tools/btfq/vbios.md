# vbios — dónde vive el número de CUs, y por qué el corpus no puede derivarlo

## El dato

El log de arranque da `CU per SH 5` con `active_cu_number 8`, o sea **10 CUs
físicos de los que 8 están activos**. `AGENTS.md` declaraba 8 CUs y máscara
`0x1e`, que son los activos, no los presentes.

## Por qué el corpus no puede derivarlo

`max_cu_per_sh` no está en ninguna constante del driver. Viene del **VBIOS**:

```
amdgpu_atomfirmware.c:964    adev->gfx.config.max_cu_per_sh = gfx_info->v27.max_cu_per_sh;
amdgpu_device.c:1848         adev->gfx.config.max_cu_per_sh = le32_to_cpu(gpu_info_fw->gc_num_cu_per_sh);
```

`amdgpu_device.c:1848` es la ruta que se usa en 7.1.3 (la de
`amdgpu_atomfirmware.c` es la antigua, por tabla ATOM). El campo se llama
`gc_num_cu_per_sh` y viene de la tabla `GFX_INFO` del VBIOS.

Es decir: **5 CUs por SH es una propiedad de esta placa concreta**, publicada en
su firmware. Ningún análisis del árbol de fuentes puede producirla, y por eso
cualquier modelo que afije el número de CUs lo está inventando.

## La estructura, con layout exacto

La unión está en `amdgpu_atomfirmware.c:818` y tiene **cuatro** variantes; no
hay una sola "v27" implícita:

```c
union gfx_info {
	struct atom_gfx_info_v2_2 v22;
	struct atom_gfx_info_v2_4 v24;
	struct atom_gfx_info_v2_7 v27;
	struct atom_gfx_info_v3_0 v30;
};
```

El driver elige por revisión: `amdgpu_atomfirmware.c:960-964`, `case 7:` usa
`gfx_info->v27`. Y `v27` es una estructura propia
(`include/atomfirmware.h:1874`), **no** `v2_2` con otro nombre.

```c
struct atom_gfx_info_v2_7 {
	struct atom_common_table_header table_header;   /* 4 bytes */
	uint8_t gfxip_min_ver;              /* offset  4 */
	uint8_t gfxip_max_ver;              /* offset  5 */
	uint8_t max_shader_engines;         /* offset  6 */
	uint8_t reserved;                    /* offset  7 <-- NO max_tile_pipes */
	uint8_t max_cu_per_sh;              /* offset  8 */
	uint8_t max_sh_per_se;              /* offset  9 */
	uint8_t max_backends_per_se;         /* offset 10 */
	uint8_t max_texture_channel_caches;  /* offset 11 */
	uint32_t regaddr_cp_dma_src_addr;    /* offset 12 */
	... (7 x uint32_t de registros CP DMA) ...
	uint8_t active_cu_per_sh;            /* offset 40 */
	uint8_t active_rb_per_se;            /* offset 41 */
	...
};
```

`atom_common_table_header` son **4 bytes**, no 8:

```c
struct atom_common_table_header {
	uint16_t usStructureSize;
	uint8_t  ucTableFormatRevision;
	uint8_t  ucTableContentRevision;
};
```

**Corrección sobre `v2_2`:** en `v2_2` el offset 7 es `max_tile_pipes`, pero en
`v27 es `reserved`. Leer `max_tile_pipes ahí daría basura silenciosamente,
porque el offset existe y devuelve un byte plausible. Es el mismo patrón que
el `block_size = 9`: un número que existe y no significa lo que su nombre dice.

**Para un driver propio, la topología de CUs son 8 bytes desde el inicio de la
tabla**, y `active_cu_per_sh` está en el offset 40. No hace falta parsear el
VBIOS entero: localizar la tabla por `get_index_into_master_table`, luego leer.

El acceso no es trivial (`get_index_into_master_table` +
`amdgpu_atom_parse_data_header` sobre `bios + data_offset`, más el
`switch` por revisión), pero una vez resuelta la dirección, la lectura es
directa.

## Verificación de los valores contra el log

| campo del VBIOS | offset | valor del log | lectura |
|---|---|---|---|
| `max_shader_engines | 6 | `SE 2 | 2 |
| `max_sh_per_se | 9 | `SH per SE 1 | 1 |
| `max_cu_per_sh | 8 | `CU per SH 5 | 5 |
| `cu_info.number | — | `active_cu_number 8 | 8 |

Los tres primeros salen del VBIOS y coinciden con el log. El cuarto
(`active_cu_number`) **no** viene del VBIOS: es
`adev->gfx.cu_info.number`, que el driver calcula al aplicar la máscara de
CUs (`amdgpu_device.c:4033`).

Los dos campos están mezclados en la misma línea de log pero son de origen
distinto, y esa distinción es la que separa «10 CUs que el chip tiene» de
«8 CUs que se pueden lanzar».

## El residuo que faltaba en el modelo, y quién lo produce

```
CUs físicos   = max_shader_engines × max_cu_per_sh = 2 × 5 = 10
CUs activos   = cu_info.number = 8
```

Los 8 no son una constante: los calcula `gfx_v8_0_get_cu_info()`
(`gfx_v8_0.c:7072`), y el mecanismo es **leer el hardware**, no aplicar una
máscara fija:

```c
gfx_v8_0_select_se_sh(adev, i, j, 0xffffffff, 0);
if (i < 4 && j < 2)
        gfx_v8_0_set_user_cu_inactive_bitmap(adev, disable_masks[i * 2 + j]);
bitmap = gfx_v8_0_get_cu_active_bitmap(adev);      /* <-- lee el hardware */
cu_info->bitmap[0][i][j] = bitmap;

for (k = 0; k < max_cu_per_sh; k++) {
        if (bitmap & mask)
                counter++;
        mask <<= 1;
}
active_cu_number += counter;
```

Es decir: el driver selecciona cada par SE/SH, **escribe la máscara de CUs
inactivos y lee de vuelta qué CUs quedaron activos**. El resultado no está en el
VBIOS ni en ninguna constante: lo decide el silicio.

Y `active_cu_per_sh` (offset 40 del VBIOS) es un campo que el driver
**declara pero no lee**. La comprobación no es un `grep` sobre `*.c` suelto:
`active_cu_per_sh` aparece en `include/atomfirmware.h` en las tres
declaraciones (`v2_4`, `v2_5`, `v2_7`) y en **ningún** `.c` de todo
`drivers/gpu/drm/`. Es decir, el VBIOS publica un campo de CUs activos y el
driver de referencia no lo usa: prefiere preguntarle a la GPU.

Esto cambia la clasificación de `0x1e`:

- **No** es una constante del driver: es la salida de una lectura de hardware.
- Es por SH, y `amdgpu_kms.c:1008` lo publica como `cu_active_number`.
- Los 5 CUs de cada SH, con `mask = 1,2,4,8,16`, producen el patrón que el
  hardware devuelve. Con 4 activos por SH de 5, `0x1e` = `11110` encaja.

**Consecuencia para un driver propio:** no se puede codificar el número de CUs
activos. Hay que hacer la misma dance —escribir la máscara, leer el bitmap de
activos— y aceptar lo que devuelva la GPU. Intentar leer solo el VBIOS
daría 10 CUs, y lanzar sobre 2 de ellos no produce un fallo visible:
produce que el hardware no responda como se espera, que es peor porque
parece un bug de timing.

## Lo que no se pudo determinar

- **El contenido del VBIOS.** `/sys/class/drm/card1/device/rom` son 131072
  bytes (128 KiB) y su modo es `-rw------- root root`: **no se puede leer sin
  root**. `amdgpu_bios` de debugfs tampoco, por el mismo motivo.
- Se lee del log el valor que el driver **extrajo** del VBIOS, no el VBIOS en
  sí. Que la extracción sea fiel lo garantiza el driver de referencia, no una
  lectura directa nuestra.
- `vbios_version y `vbios_build sí son legibles:
  `vbios_build = 565939`, `vbios_version = xxx-xxx-xxx`, y el log da
  `ver: 015.050.002.001.000000, 2021/05/12`. Eso identifica el firmware pero no
  da la tabla `GFX_INFO`.

Sin root, extraer la tabla del VBIOS es `BLOCKED_BY_AUTHORIZATION`, no
`BLOCKED_BY_EXTERNAL_DEPENDENCY`: la dependencia existe y es accesible en
principio.

## Cómo reproducir lo verificable sin root

```sh
journalctl -k -b --no-pager | grep "SE .*SH per SE"
cat /sys/class/drm/card1/device/vbios_build
```

Solo lectura. `GPU INTACTA`, `WRITE_EXECUTION NONE`.
# 1053 — la geometría de la ASIC no está perdida: está en un fichero de 128 KiB que hay en la tarjeta y que sólo pide ser leído

```text
AGENCIA=RX550-INVESTIGACION · WORK_CLASS=AGENT-MAIN-FIRMWARE
GENERADO=2026-10-04 · MEDIDO=EN ESTA HOST
CERRADO=NOT_FOUND_EN_CORPUS  ->  PRESENTE_EN_LA_PIEZA, legible por root
AFECTADO=/sys/bus/pci/devices/0000:01:00.0/rom
ESTADO=PROBADO · NO LEIDO (PermissionError medido) · el intento no tuvo efecto
```

## Lo que cuatro nodos habían dado por perdido, y por qué

Tres nodos distintos lo dieron por perdido, y la tabla lo deja corto:

| lo que se daba por perdido | quién lo dijo | en realidad |
|---|---|---|
| geometría de CU | `MICROARCH-GFX8`: *«viene del VBIOS. NOT_FOUND en el corpus. NO_NUMERADO, no inventado»* | **está en la tarjeta** |
| `max_cu_per_sh`, la contradicción 5-contra-8 | `CONSTANTES-GFX8-DRIVER`: *«el arbitraje definitivo es lectura de `amdgpu_gca_config` (debugfs, no hecha)»* | **también está en la ROM** |
| tamaños de caché L1/L2 | `MEMORIA-GFX8`: *«los tamaños vienen del firmware. NOT_DETERMINED»* | **idem** |
| bytes por slot de scratch | `CONSTANTES-GFX8-DRIVER`: *«bloquea un subsistema entero»* | **idem** |

El corpus no la tiene porque el VBIOS de una GPU **no está en el kernel**: está en la
podría haber hecho mal durante días: tratar
`NOT_FOUND_EN_EL_CORPUS` como `AUSENTE_EN_LA_PLAZA`.

## MEDIDO

### 1. La ROM existe, y tiene el tamaño que la BAR6 dice

```text
/sys/bus/pci/devices/0000:01:00.0/rom
    bytes  131072
    modo   0600   owner 0 (root)
    legible por uid 1000:  False
      lectura denegada: PermissionError [Errno 13]
```

**131 072 B = 128 KiB**, que es exactamente lo que mide el nodo Vulkan para `BAR6`, y
coincide con la tabla de la KFD que da `NUM_TCC_BANKS = 3` para Polaris12 frente a 7 para
Polaris10. No es un fichero truncado ni un placeholder: es una ROM del tamaño que declara
la propia BAR.

### 2. `vbios_version` no es un placeholder del software

```
/sys/class/drm/card1/device/vbios_version   =  b'xxx-xxx-xxx\n'
```

Y medido sobre los **304 ficheros `.c`/`.h`/`.rs`** de `linux-7.1.3`:
**0 ocurrencias de `xxx-xxx-xxx`.**

Es decir: **esa cadena no la pone el driver.** Si el driver no la pone y el atributo la
devuelve, la está poniendo **la ROM de la tarjeta**. Un ATOMBIOS que reporta su versión
como `xxx-xxx-xxx` es un ATOMBIOS sin campo de versión rellenado, y eso es un hecho sobre
diagnóstico completo y lo que le faltaba era el dato:

### 3. El intento de lectura no costó nada

```text
ANTES     runtime_status = suspended      runtime_active_time = 278853
[lectura denegada]
DESPUES   runtime_status = suspended      runtime_active_time = 278853
```

Idéntico. **Leer un fichero de sysfs denegado no cambia el estado de la GPU**, lo cual es
lo esperable y conviene tener medido en vez de supuesto: `runtime_active_time` es el
contador que el hallazgo 1045 usa como prueba de no-resume, y aquí acaba de servir para lo
contrario.

## Qué cerraría la ROM, con las citas que ya están en el árbol

| lo que cerraría | dónde lo dice el driver |
|---|---|
| geometría de CU: CU, CU-por-SH, SH-por-SE, SE | `amdgpu_atombios.c:744-750` |
| `max_cu_per_sh`, **la contradicción 5-contra-8 en su origen** | `amdgpu_atombios.c:746` — `adev->gfx.config.max_cu_per_sh = gfx_info->info.max_cu_per_sh` |
| tamaños de caché L1 y L2 | `amdgpu_discovery.c:1767-1786` |
| `NUM_TCC_BANKS` por ASIC | `TCP_ADDR_CONFIG` en la KFD |
| bytes por slot de scratch | el hueco que `CONSTANTES-GFX8-DRIVER` llama *«bloquea un subsistema entero»* |

Y sobre `max_cu_per_sh` en particular, el nodo `CONSTANTES-GFX8-DRIVER` ya tenía el
diagnóstico completo, y lo que le faltaba que le faltaba era el dato:

> La contradicción 5-contra-8 viene de **un registro de firmware** (`CRAT`) repartido a
> dos consumidores que lo necesitan en unidades distintas: `cwsr_size` cierra con 8 CU y
> las 16 cachés publicadas exigen ≥10. **El mismo registro dice `max_cu_per_sh = 5`.**

Es decir: hay un tercer número en el mismo bloque de firmware, y **los tres son del mismo
origen**. La contradicción no es entre fuentes; es entre lecturas del mismo sitio. Y el
sitio está en la ROM.

## Por qué esto es la petición de autorización más barata que tiene el proyecto

El proyecto tiene bloqueadas tres líneas de ideas por falta de geometría, y tiene al menos
cuatro peticiones posibles de `root` en la cola. **Esta es la única de las cuatro que es una
lectura de fichero, sin Opening el device, sin escribir un registro y sin tocar el estado
de energía:**

| petición | qué es | riesgo | qué cierra |
|---|---|---|---|
| **`cat .../rom`** | **leer un fichero** | **ninguno**: sin device, sin MMIO, sin resume | geometría completa |
| `amdgpu_gca_config` (debugfs) | leer un nodo | abre el device ⇒ **resume la GPU de display** | una pata de una corroboración ya cerrada por 3 de 4 |
| kprobe sobre `amdgpu_pm_get_sensor_generic` | escribir/ejecutar | instrumentación en caliente | la causa del `EBUSY` |
| ioctl `READ_MMR_REG` | abrir + leer | **resume la GPU de display** (`boot_vga=1`) | 21 registros |

La cuarta es la que el hallazgo 1045 decidió no ejecutar porque **el riesgo no es la GPU,
es la sesión gráfica del usuario**. La primera no tiene ese riesgo: no abre `/dev/dri` en
absoluto.

Y hay un orden que este proyecto ya tiene escrito y que aquí se cumple entero:
`SSH-RECOVERY-PATH.md [3b] NOT_PROVEN_EMPIRICALLY` significa que **primero se prueba la
vía de recuperación, después se toca lo que pueda dejarte sin escritorio**. Leer la ROM no
puede dejarlo sin escritorio.

## CORRECCION SEGUNDA: la fila de L1/L2 era código muerto para esta ASIC

El nodo ATOMBIOS-DECODER lo/localizo por call graph y lo he verificado yo. **Mi tabla
de este hallazgo es incorrecta en una fila, y es la que justificaba parte de la petición
de root.**

Yo escribí: *«tamaños de caché L1 y L2 → `amdgpu_discovery.c:1767-1786`»*.

MEDIDO, la cadena entera:

```
amdgpu_device.c:1980    case CHIP_POLARIS12:            <-- listado EXPLICITO
amdgpu_device.c:1989        r = vi_set_ip_blocks(adev); <-- este grupo
amdgpu_device.c:1994    default: r = amdgpu_discovery_set_ip_blocks(adev);

amdgpu_discovery.c:1721  static int amdgpu_discovery_get_gfx_info(...)
amdgpu_discovery.c:2998      amdgpu_discovery_get_gfx_info(adev);   dentro de set_ip_blocks
amdgpu_discovery.c:3031      amdgpu_discovery_get_gfx_info(adev);   dentro de set_ip_blocks
```

`CHIP_POLARIS12` está en el grupo de `vi_set_ip_blocks`. `amdgpu_discovery_set_ip_blocks`
**solo se alcanza por `default:`**. Luego para esta ASIC
`amdgpu_discovery_get_gfx_info` **no se llama**, y las líneas 1767-1786 —que leen
`gc_l1_instruction_cache_size_per_sqc`, `gc_l1_data_cache_size_per_sqc`, `gc_gl2c_per_sa`,
`gc_gl2c_size_per_instance`— **no se ejecutan**.

> Las líneas que cité existen, son correctas, y no dicen nada de esta GPU.

### Y mi verificación de esa refutación estuvo a punto de ser falsa

Primero busqué los llamantes con el grep **acotado al directorio `amdgpu/`** y devolvió
**una sola línea, la definición**. Es decir: «sin llamantes». Si acepto eso, borro la
petición de root entera y **borro algo que sigue siendo válido**.

Con alcance completo —todo el árbol del kernel— hay **dos** llamantes, ambos dentro de
`amdgpu_discovery_set_ip_blocks`, uno bajo `case CHIP_CYAN_SKILLFISH` y otro bajo
`default:`.

> Cuarta vez esta sesión que concluyo «no existe» desde un alcance que no lo cubre. Y
> esta vez el error iba en la dirección que **borra** trabajo, que es la peor: un
> `NOT_FOUND` erroneo no añade nada, pero un `PROVEN_ABSENT` erroneo **tapa una línea
> que funciona**.

La regla que sale, y que es la inversa de la que vengo aplicando: **un `NOT_FOUND` con
alcance corto es inocuo; un alcance corto aplicado a una *refutación* es destructivo.**
Porque para refutar hay que mirar más, no menos.

### Qué queda de la petición de root, con las tres filas restadas

| fila | de dónde sale de verdad | ¿la abre la ROM? |
|---|---|---|
| CU, SE, CU-por-SH, tile pipes | `amdgpu_atombios.c:744-750` — **sí se ejecuta** para Polaris12 | **SÍ** |
| tamaño de L1 | ya medido por KFD: 16 KB y 32 KB (`kfd_crat.c:94,103,113`) | **NO hace falta** |
| tamaño de L2 | **no está en ninguna parte**: `kfd_crat.c:122` es `TODO: Add L2 Cache information` | **NO** |
| bytes por slot de scratch | registro MMIO, `gfx_v8_0.c:7123,7125` | **NO** |

O sea que **la petición de root no desbloquea L1, L2 ni scratch**. Solo la geometría de
CU/SE, que es la fila que ya era la buena. Y esa sigue en pie porque
`amdgpu_atombios.c:744-750` **no** es el camino de `amdgpu_discovery_set_ip_blocks`: lo
llama `amdgpu_atombios_get_gfx_info`, y para Polaris12 esa ruta está viva
(`gfx_v8_0.c:1676-1681`).

**Mi titular se reduce a una cosa, y sigue siendo real:** leer la ROM para el bloque
`GFX_Info` de la ATOMBIOS, que es donde está la geometría de CU. Todo lo demás ya está
medido por otra vía o no existe.

### Y una trampa de versión que el decodificador ha detectado

`amdgpu_atombios.c:745` lee el byte +7 **sin mirar `frev` ni `crev`**:

```c
adev->gfx.config.max_shader_engines = gfx_info->info.max_shader_engines;
adev->gfx.config.max_tile_pipes     = gfx_info->info.max_tile_pipes;   /* +7 */
```

Y ese mismo byte tiene dos nombres según la cabecera:

```
atombios.h:5653        UCHAR   max_tile_pipes;
atomfirmware.h:1844    uint8_t reserved;          /* en v2_4 / v2_7 */
```

Si la ROM trae versión 2.4 o posterior, **el driver lee como tile pipes un byte que el
firmware llama reservado**, y se lo copiará a `gfx.config.max_tile_pipes` sin que nada
avise. Verificado por mí en las dos cabeceras.

Es un hallazgo que no habría salido sin el decodificador, y es de la clase que este
proyecto busca: no un valor mal leído, sino **un valor leído con la semántica del
firmware equivocado**.

## CORRECCION, y es de las mias

Este hallazgo se commiteo con dos errores que el nodo GEOMETRIA-SEGUNDA-FUENTE
localizo y yo he verificado. Los dos estan en lo que mas se apoya el titular.

### 1. MI CENSO ERA 8,9 VECES DEMASIADO ESTRECHO

El hallazgo dice, textual: *«MEDIDO sobre los **304 ficheros `.c`/`.h`/`.rs`** de
`linux-7.1.3`: **0 ocurrencias**»*.

MEDIDO sobre la población correcta:

```
.h   1721
.c    984
.rs      0
      ----
      2705        lo que dice el 1053: 304      factor 8,9
```

**La conclusión se sostiene**: 0 ocurrencias de `xxx-xxx-xxx` en los 2705, comprobado
por mí. Pero el `NOT_FOUND` original tenía alcance insuficiente, que es exactamente lo
que `AGENTS.md` §16 prohíbe: *«Si el scope no es suficiente: NO CONCLUIR AUSENCIA»*.

Y es la **décima** vez que aplico un filtro que excluye a la población que dice medir.
La novena fue en `claims.py`; ésta en mi propio hallazgo, y la escribí con un número
redondeado que no verifiqué. Un número que no comprobé, viajando como medido.

### 2. MI INFERENCIA SOBRE `xxx-xxx-xxx` ERA INVALIDA

Escribí: *«esa cadena no la pone el driver. Si el driver no la pone y el atributo la
devuelve, la está poniendo la ROM de la tarjeta»*.

MEDIDO, `amdgpu_atombios.c:1807-1816`:

```c
static ssize_t amdgpu_atombios_get_vbios_version(struct device *dev, ...)
{
	struct amdgpu_device *adev = drm_to_adev(dev);
	struct atom_context *ctx = adev->mode_info.atom_context;

	return sysfs_emit(buf, "%s\n", ctx->vbios_pn);
}
```

**Imprime `ctx->vbios_pn`, el número de parte, que es un campo de runtime** — no un
literal del fuente. Y hay un `amdgpu_atombios_get_vbios_build` aparte, que imprime
`ctx->build_num`.

Mi inferencia era unaFalacia: **la ausencia de un literal en el código fuente no
establece de dónde sale el valor en runtime, cuando la ruta de impresión es un campo.**
Un campo puede se puede por bytes de la ROM, o por una plantilla, o por un valor por
defecto del driver, o por concatenación, y en ninguno de esos casos el literal
aparecería nunca en el `.c`. Mi «0 ocurrencias en el fuente, luego viene de la ROM» no
teníapies.

Y la rama que yo mismo enuméré como posible —«ATOMBIOS sin el campo de versión
rellenado»— queda **REFUTADA** por el mismo nodo: los atributos existen, luego
`atom_context != NULL` (`:1859`/`:1914`), y `vbios_build` visible luego `build_num` no
vacío, luego el recorrido del ATOMBIOS funcionó con sus límites correctos
(`atom.c:1510-1513`). O sea que **el ATOMBIOS está presente y parseado**, que era la
tercera de mis hipótesis y la que yo daba por descartada.

**Lo que sí sobrevive del hallazgo**, porque no dependía de esa inferencia:

```
/sys/bus/pci/devices/0000:01:00.0/rom   131072 B   0600 root   PermissionError medido
runtime_active_time idéntico antes y después del intento de lectura
```

La ROM existe, es del tamaño que declara la BAR6, y leerla no reanuda la GPU.

### 3. Y EL TITULAR SE ENCOGE

El hallazgo pide root para leer la ROM porque dice que la geometría está en ella. Con
`GEOMETRIA-SEGUNDA-FUENTE` la geometría de CU **ya está medida, sin root**:

```
simd_count 32 / simd_per_cu 4          = 8 CU activos
cu_per_simd_array 5 x array_count 2    = 10 ranuras de id
caches_count 16  ->  processor_id_low distintos: 8
                     offsets presentes: 1,2,3,4,6,7,8,9      ausentes: 0 y 5
cwsr_size 2789376                      cierra exacto con 8
num_xcc 1
```

Los 16 cachés son **8 CU × 2 tipos** (`type 9` DATA y `type 10` INSTRUCTION), 8 de 16 KB
y 8 de 32 KB. **No son 16 cachés que exijan 10 CU**, que era lo que afirmaba yo y lo que
dice `CONSTANTES-GFX8-DRIVER.md:783`. Eso queda **REFUTADO**.

Así que la petición de root ya **no es «la geometría»**: son tres campos sueltos, y el
informe del nodo los nombra. Es una petición más pequeña de la que este hallazgo
planteaba, y eso es una buena noticia, no una pérdida.

## Lo que NO se afirma

- **No se afirma que la ROM contenga lo que se busca.** Es una ROM PCI de 128 KiB; si no
  lleva ATOMBIOS, o lo lleva en otra forma, o no incluye geometría, no lo sabremos hasta
  leerla. Lo que se afirma es que **existe y es del tamaño correcto**, y que la búsqueda
  termina ahí donde está, no en un `NOT_FOUND`.
- **No se afirma que `xxx-xxx-xxx` sea «una ROM mala».** Es un dato: el campo de versión
  no está relleno. Si el resto del contenido está, la ROM es perfectamente utilizable.
- **No se ha leído nada de ella.** `PermissionError` medido, y el estado de la GPU
  comprobado antes y después.
- **No se ha cambiado `power/control` ni nada más.**

## Lo que esto hace con lo que ya está escrito

Tres documentos affirmed que la geometría era irrecuperable sin VBIOS, y uno de ellos
—`MICROARCH-GFX8`— tuvo además el mérito de **negarse a inventar el número**, que fue lo
correcto. Lo que cambia no es su medida, es el alcance del `NOT_FOUND`:

> `NOT_FOUND_EN_CORPUS` no era `AUSENTE_EN_LA_PIEZA`. Cuesta cuatro nodos y varios días
> llegar a esa distinción, y es la misma clase de error que el hallazgo 1048: **un filtro
> que excluye por construcción a la población que dice medir.** El corpus no contiene el
> firmware de la tarjeta. No es que el firmware no exista.
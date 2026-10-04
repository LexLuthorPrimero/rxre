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
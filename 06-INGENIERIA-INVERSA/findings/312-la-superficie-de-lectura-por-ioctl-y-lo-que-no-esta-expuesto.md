# 312 · La superficie de lectura por ioctl: 15 de 19 sin privilegios, y solo por `renderD129`

```
PENDIENTE=312-1 | HALLAZGO=312-la-superficie-de-lectura-por-ioctl-y-lo-que-no-esta-expuesto.md
             | ESTADO=PROVEN
             | NECESITA=/dev/dri/renderD129
             | ALCANZABLE_SIN_ROOT=si
```

## Que se pregunto

El proyecto tiene 123 huecos clasificados `UN_REGISTRO`, que la herramienta
describe como "se cierra leyendo un registro". Eso suena accionable. La
pregunta previa es si existe en **esta** maquina una ruta SIN PRIVILEGIOS para
leer estado de la tarjeta. No estaba medida.

## Medido

```
  /sys/kernel/debug/dri/1/     montado, modo 0700 root; sudo pide contrasena
  /dev/dri/card1                crw-rw----+ root:video
                               este usuario NO esta en el grupo video
                               -> 0 de 19 queries responden, EACCES
  /dev/dri/renderD129           crw-rw-rw-
                               -> 15 de 19 responden
```

**El nodo importa.** El mismo ioctl, el mismo proceso, el mismo binario: EACCES
en `card1` y exito en `renderD129`. La diferencia es de permisos de fichero, y
por eso cualquier trabajo futuro que use `card1` va a perder el tiempo.

Y el descriptor: con `O_RDONLY`, **0 de 19**. La capa DRM comprueba permiso de
escritura antes de dejar pasar cualquier ioctl, incluidos los de lectura.

Eso no significa que el programa escriba. `AMDGPU_INFO_*` es lectura por
definicion. Pero significa que una herramienta que declara `WRITES_GPU=no` y
abre `O_RDWR` tiene un contrato que su descriptor no describe (hallazgo 310).

## Lo que se lee en esta placa

```
  device_id                    0x699f        <- confirmado, es la RX550
  chip_rev / external_rev      0 / 100
  pci_rev                      199 (0xC7)
  family                       130 (0x82)
  num_shader_engines           2
  num_shader_arrays_per_engine 1
  num_rb_pipes                 4
  num_hw_gfx_contexts          8
  cu_active_number             8
  cu_bitmap[0][0]              0x0000001e
  enabled_rb_pipes_mask        0xF
  pcie_gen                     2             <- Gen2
  max_engine_clock             1071 MHz
  max_memory_clock             1500 MHz
  gpu_counter_freq             25000 kHz

  vram_size                    2035 MiB
  vram_cpu_accessible_size      260 MiB      <- el BAR
  gtt_size                     5897 MiB

  GFX_SCLK                      804  ->  80 MHz   (reposo)
  GFX_MCLK                      300  ->  30 MHz   (reposo)
  GPU_TEMP                    25000           <- unidad DESCONOCIDA
  VDDGFX                       1050           <- unidad DESCONOCIDA
  GPU_LOAD                        0 %         (el driver lo llama
                                               'average graphics activity')
  VDDNB                        EINVAL
```

La geometria que `AGENTS.md` da por conocida — 2 SE, 1 SHA por SE, 8 CU, CU mask
`0x1e`, 4 RB — **queda corroborada por lectura de hardware**, no solo por fuente.
Y tres medidas que encajan con hallazgos previos:

- `pcie_gen = 2`. Corrobora la cadena de 284/285/286 sobre un enlace Gen2.
- `vram_cpu_accessible_size = 260 MiB`. Es el BAR, y explica por que el mapa BAR
  esta acantonado (606).
- `gtt_size = 5897 MiB`. Es el mismo numero que `1010` audita como "5907M" de
  TTM: **la misma magnitud por dos vias distintas**, el driver y TTM.

## UNA CONTRADICCION, y es el hallazgo importante

```
  bloques IP presentes: 1
   ip_discovery_version=0    major=0 minor=0 revision=0
   available_rings=0x1  ib_start_align=32  ib_size_align=32
```

**El kernel reporta UN bloque IP y con version 0.** Pero:

- `231` afirma que la version del IP "cierra gfx hwip".
- `236` reconstruye **nueve** bloques IP y su version.

Si la version del IP fuera la que dice 231, aqui habria version distinta de
cero. Hay dos explicaciones y el dato no las separa:

1. Esta UAPI no se rellena en este kernel para Polaris12, y devuelve un bloque
   de relleno.
2. La version existe y esta ruta no la expone.

Lo que **si** se puede afirmar: `AMDGPU_INFO_HW_IP_INFO` **no corrobora** a 231
en esta placa. No la refuta, porque un campo que devuelve cero no es evidencia
de que el dato no exista. Es `NOT_OBSERVED`, y 231 sigue en pie por la fuente.

La distincion importa porque 231 es `PROVEN` y una corroboracion de hardware
habria sido muy distinta de una lectura de fuente. Anotarlo evita que alguien
asuma que esta medida respalda 231.

## Lo que NO se ha hecho

- No se ha tocado `card1`. Se necesita el grupo `video`, y anadir al usuario a un
  grupo es decision del sistema, no del experimento.
- No se ha probado `AMDGPU_INFO_VBIOS` con sub-id. Es la via al ROM y merece su
  propio instrumento.
- No se ha tocado `VDDNB`: EINVAL. Se deja como `NOT_AVAILABLE` por esta ruta.

## Tesis que sostiene

"Hay un sensor" y "puedo leerlo desde mi programa" son dos afirmaciones
distintas, y la diferencia entre ellas es de permisos de fichero, no de
tecnica. Un mapa de observabilidad que no incluya **el nodo por el que se llega**
no dice si la observabilidad existe.

Y la version del IP es el ejemplo: hay un campo que se llama exactamente como la
prueba que se quiere hacer, y devuelve cero. Eso no es un dato: es la
ausencia de un dato con nombre de dato.

## Como reproducirlo

```
gcc -O2 -o amdinfo 08-ARQUITECTURA/tools/amdinfo.c
./amdinfo /dev/dri/renderD129          # 15 de 19
./amdinfo /dev/dri/card1                # EACCES en todos: falta el grupo video
```

`amdinfo` comprueba que `device_id == 0x699f` al arrancar y avisa si no es la
placa. Ese es su unico control de que el numero leido sea de esta GPU.

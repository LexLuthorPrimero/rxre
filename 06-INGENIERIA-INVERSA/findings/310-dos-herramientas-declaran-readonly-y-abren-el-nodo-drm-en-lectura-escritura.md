# 310 · Dos herramientas declaran `WRITES_GPU=no` y abren el nodo DRM con `O_RDWR`

```
PENDIENTE=310-1 | HALLAZGO=310-dos-herramientas-declaran-readonly-y-abren-el-nodo-drm-en-lectura-escritura.md
             | ESTADO=PARTIAL
             | NECESITA=/dev/dri/renderD129
             | ALCANZABLE_SIN_ROOT=si
             | NOTA=el discriminante O_RDONLY/O_RDWR esta EJECUTADO y medido
```

## Que se midio

`run_all.py` tiene un check de capacidad que falla con:

```
  DECLARADA_SIN_USO: 1. Un campo de capacidad puesto a yes sin
  ejercerse deja de distinguir: el dia que aparezca una que SI
  escriba y declare no, el mismo criterio no la vera.
```

Ese check mira una sola direccion: campos `yes` que no se ejercen. La
direccion inversa la medi a mano y encuentra dos casos:

```
  08-ARQUITECTURA/tools/amdioread.py   CONTRACT: WRITES_GPU=no   open(nodo, O_RDWR)
  08-ARQUITECTURA/tools/vbiosread.py   CONTRACT: WRITES_GPU=no   open(nodo, O_RDWR)
```

Y el nodo no es un fichero cualquiera:

```
  vbiosread.py:71    RENDER_AMD = "/dev/dri/renderD129"
  vbiosread.py:40    dos rutas. /dev/dri/renderD129 es crw-rw-rw-.
  amdioread.py:115   ioctl(fd, DRM_IOCTL_AMDGPU_INFO, &info)
```

## Por que importa mas de lo que parece

`O_RDONLY` y `O_RDWR` no son dos estilos de escribir el mismo codigo. Con
`O_RDONLY` el kernel **rechaza** cualquier ioctl que escriba, y el error lo
dice. Con `O_RDWR` el descriptor tiene permiso de escritura y el `ioctl` que se
ejecute depende de lo que el que llama pida.

**Y MEDIDO DESPUES, con el mapa de 312:** con `O_RDONLY` la capa DRM rechaza
TODOS los ioctl de `AMDGPU_INFO`, incluidos los que son de lectura. **0 de 19
responden con `O_RDONLY`; 15 de 19 con `O_RDWR`.** El permiso de escritura del
descriptor decide si se puede siquiera *preguntar*.

Eso no convierte a estas herramientas en escritoras, porque `AMDGPU_INFO_*` es
lectura por definicion. Lo que hace es separar dos cosas que el contrato
confunde: lo que el programa **hace** con los datos, que es `WRITES_GPU=no`, y
lo que el descriptor **permite**, que no lo describe nadie.

Es decir: `WRITES_GPU=no` es una **declaracion**, y con `O_RDWR` la
declaracion y el descriptor no coinciden. Hoy el codigo solo lanza
`AMDGPU_INFO_DEV_INFO`, que es de lectura, asi que no hay escritura. Pero:

- el contrato dice `no` y el fd dice `si`;
- anadir un `AMDGPU_INFO_*` de escritura no cambiaria ni el contrato ni la
  Cabecera, y pasaria inadvertido por el unico check que existe;
- el permiso `crw-rw-rw-` del nodo significa que cualquiera, sin root, puede
  abrirlo en escritura. Un descriptor `O_RDWR` sobre ese nodo no es un
  detalle de estilo.

**Estado: `PROVEN`.** El `O_RDWR` esta en el codigo, el nodo es un
`renderD*`, y el contrato dice `no`. Los tres, medidos.

## El discriminante, ejecutado

La duda era si el `O_RDWR` es **estilo** o **load-bearing**. Si
`AMDGPU_INFO_DEV_INFO` lo necesita, cambiarlo rompe la herramienta. Se
comprobó contra el nodo real:

```
  $ cat /sys/class/drm/renderD129/device/device
  0x699f                      <- es la RX550 objetivo (1002:699f)

  O_RDWR    (como esta hoy)    OK   device_id=0x699F
  O_RDONLY  (propuesta)        OK   device_id=0x699F

  diff de las dos salidas: identico
```

Los dos flags dan la misma salida, byte a byte. **`O_RDWR` no es
load-bearing para este ioctl: es estilo.** El `no` del contrato ya describe lo
que la herramienta hace; lo que no lo describe es el permiso del descriptor.

Metodo: se extrajo el literal `PROBE_C` de `amdioread.py`, se compilaron dos
binarios identicos salvo `O_RDWR` contra `O_RDONLY`, y se ejecutaron ambos
sobre `renderD129`. No es un argumento sobre el codigo: es la misma llamada
con el otro flag, en la tarjeta.

## Que sigue sin hacerse, y por que

El flag **si** se puede cambiar a `O_RDONLY` en las dos herramientas: medido
que no rompe nada y que el resultado no varia. Lo que queda abierto no es el
flag:

- `vbiosread.py` usa `AMDGPU_INFO_VBIOS` a traves del mismo ioctl, y ese si
  **toca memoria de la GPU** (vuelca el ROM que el driver tiene en
  `adev->bios`). Ahi `O_RDONLY` puede ser rechazado por el driver, y no se ha
  medido porque exigiria ejecutar el volcado.
- El check de capacidad en la direccion que falta, ese si se puede anadir sin
  decidir nada.

## Lo que si es automatico

Un check de capacidad en la direccion que falta: "`WRITES_GPU=no` y abre un
nodo de `/dev/dri` con `O_RDWR`". Es una regla de una linea sobre un texto, y
ese es el criterio que ya usa `contract_filter.py` para el resto.

Por que esa direccion y no la otra: el check que existe (`DECLARADA_SIN_USO`)
mide "`yes` que no se ejercen", y por construccion **solo puede encontrar
casos `yes`**. Un `no` que si escribe es invisible para el. Y como el campo
`no` es el que se aplica a lo que toca la GPU, es justo la direccion donde un
error tiene consecuencias.

## Tesis que sostiene

Un contrato de capacidad que se verifica solo en una direccion no es un
contrato: es una asercion parcial. Y una asercion parcial tiene una propiedad
mala: **los casos que declara son los que encuentra**, y los que no declara no
existen para el check.

Por eso este caso es `NOT_DETERMINED` en cuanto al arreglo, y `PROVEN` en
cuanto al hecho. Los dos estados no se contradicen: el hecho esta medido, y la
decision de que hacer con el no esta tomada.

## Como reproducirlo

```bash
grep -l 'CONTRACT: WRITES_GPU=no' 08-ARQUITECTURA/tools/*.py \
  | xargs grep -n 'O_RDWR'
```

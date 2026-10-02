# 071 · F2 ejecutado y bloqueado por saturación de la GPU, no por hardware: el discriminante quedó construido

```
CLASSIFICATION=DOCUMENTATION · TRACK=RUNTIME_READ_ONLY + IMPLEMENTATION
HARDWARE_SCOPE=HOST-C/RX550/0000:01:00.0 · WORK_CLASS=READ_ONLY/EVIDENCE
WRITE_EXECUTION=NONE · MODIFICATIONS=6_PACKAGES_DEVEL · RUNTIME=EXECUTED
GPU INTACTA
```

## Qué pasó, en orden

F2 declaraba su discriminante **escrito y no ejecutado**, con un método concreto:
adjuntar la textura DXT5 directamente como color attachment de un FBO y leer
con `glReadPixels`, sin shader, sin quad, sin dibujar. Se ejecutó.

**Resultado: no se pudo leer el sampler, y el bloqueo no es el que la frontera
suponía.** No falta un permiso ni falta hardware. Falta superficie GL
disponible, porque la sesión gráfica tiene la GPU.

## La cadena de diagnóstico, que es el resultado

Cada paso se comprobó contra el sistema antes de pasar al siguiente:

```
  vulkaninfo --summary     →  AMD Radeon RX 550 (RADV POLARIS12), Mesa 26.2.3   OK
  glxinfo -B               →  radeonsi, polaris12, GL 4.6, Accelerated: yes   OK
  eglinfo                  →  EGL 1.5, mismo renderer                          OK
  compilar con -lGL        →  funciona                                        OK
  glXGetFBConfigs(...)     →  0        <-- AQUI ESTA EL BLOQUEO
  glxinfo -v               →  1 visual  (al inicio del turno había 340)
```

`glXGetFBConfigs` devuelve **cero** configuraciones y sólo queda **un** visual,
frente a los 340 que había antes de que el compositor tomara la GPU. Aislado
atributo por atributo:

```
  renderable + RGB 8/8/8 + depth 0     →  NULL
  renderable + RGB 8/8/8               →  NULL
  renderable + depth 0                 →  NULL
  sólo depth 0                         →  visual VÁLIDO
  sólo rojo 8                          →  visual VÁLIDO
```

Un visual existe, pero **ninguno es renderizable**. Eso no es una limitación de la
tarjeta: es que el driver tiene el recurso tomado mientras el compositor compone.

Y es coherente con lo medido antes en `docs/ESTADO-BASE-PRE-F1.md`: los clocks
devuelven `EBUSY` y `kwin_wayland` tiene fds abiertos sobre `/dev/dri/*`. La misma
causa, vista desde el lado del render en vez de desde sysfs.

**MSAA no interviene**: `glxinfo` no reporta `GLX_SAMPLES` ni
`GLX_SAMPLE_BUFFERS`, y no hay MSAA en las extensiones GLX. Uno de los cuatro
confounders que F2 declaraba queda descartado por medición.

## Lo que sí quedó construido, y es el valor de esta nota

`04-IMPLEMENTACION/compressor/f2_sampler_probe.c`, compilado y con el contexto
GL correcto. No es algo escrito y borrado: es el discriminante de la frontera, con las
cuatro autovalidações que F2 exigía.

Lo que tiene y por qué cada parte importa:

| parte | para qué |
|---|---|
| `ref_palette()` — +3/ y +2/ | la referencia de la spec, escrita **aparte**, sin compartir código con el encoder |
| `trunc_palette()` — sin redondeo | el resultado alterno, para que la clasificación no interprete: compara contra dos números que ya existían |
| `build_block()` | arma el bloque BC3 de 16 bytes con los 8 índices en la fila correcta |
| `carga_ext()` | resuelve las funciones de FBO por `glXGetProcAddress` y **falla si falta alguna** |
| `crea_contexto()` | contexto core 3.3 real, y **verifica que `glGetString` no devuelva NULL** |
| 4 autovalidações | índices 0 y 1 no interpolan; 6 = 0 y 7 = 255 en modo 6 |

Las autovalidações corren **antes** de cualquier lectura y pasan:

```
  pal[0] == a0 (no interpola)          OK
  pal[1] == a1 (no interpola)          OK
  indice 6 == 0 en modo 6              OK
  indice 7 == 255 en modo 6            OK
```

La cuarta es la que F2 marca como la importante: si los índices 0 y 1 no dan
`a0` y `a1` exactos, el problema no es la rampa sino que la lectura no llegó al
attachment. **Eso separa "el hardware redondea" de "el pipeline me devolvió
basura",** y sin esa separación un `(null)` se leería como un resultado de
hardware.

### Tres fallos reales que el programa encontró, todos por no verificar

Los documento porque son la clase de error que se repite en este trabajo:

1. **No había contexto.** La primera versión imprimía `GL_RENDERER: (null)` y
   seguía adelante. Un `NULL` de `glGetString` se habría leído como "el hardware
   no devolvió nada". Ahora `crea_contexto()` lo comprueba y aborta.
2. **Exigí atributos de más.** Pedir `GLX_X_VISUAL_TYPE TrueColor` y
   `GLX_ALPHA_SIZE 8` hacía que `glXChooseVisual` devolviera `NULL` con 340
   visuales disponibles. Se lee como "no hay visual" cuando los hay. Medido, no
   deducido: hay 340 visuales y ninguno cumple el filtro pedido.
3. **Confundí "no compila" con "no funciona".** El `gl.h` de Mesa no declara las
   funciones de FBO, y declararlas a mano sería inventar su ABI. Se resuelven por
   `glXGetProcAddressARB`, que es el mecanismo correcto.

## Cambio en el sistema, reportado

```
  6 paquetes de desarrollo instalados (cabeceras, ninguno toca la GPU):
    mesa-libGL-devel mesa-libEGL-devel        26.2.3  (la MISMA versión
                                                  del driver ya cargado)
    libglvnd-devel libglvnd-core-devel
    xorg-x11-proto-devel libXau-devel libxcb-devel libX11-devel
```

`mesa-libGL-devel` se eligió **a propósito** en la versión 26.2.3, que es la del
driver ya en ejecución: headers de otra versión pueden declarar un ABI que el
driver cargado no implementa, y el fallo aparecería como un error de sampler en
vez de como un error de compilación.

**La GPU no se modificó**: `amdgpu` sigue cargado, VRAM 2048 MiB intacto, sin
`insmod`, sin ioctl de escritura, sin MMIO write.

## Lo que F2 sigue necesitando

Una superficie GL renderizable. Eso requiere que la sesión gráfica no tenga la
GPU, es decir, lo mismo que bloquea F1. **No son dos bloqueos distintos: son la
misma condición de sesión**, encontrada por dos caminos distintos.

```
  F1  necesita cargar un módulo    →  choca con kwin_wayland
  F2  necesita un contexto GL      →  choca con kwin_wayland
  ambos:  la sesión gráfica tiene la GPU
```

## Estado

| Afirmación | Estado |
|---|---|
| El discriminante de F2 está construido y compila | `PROVEN` |
| Sus 4 autovalidações pasan | `PROVEN` (ejecutado) |
| La referencia `+3/`/`+2/` es correcta y está escrita aparte | `PROVEN` |
| `bcdec` trunca y diverge en 82.9 % | `PROVEN` (069) |
| RADV y radeonsi reconocen POLARIS12 | `PROVEN` |
| MSAA no está activo (un confounder descartado) | `PROVEN` |
| La GPU no tiene superficie GL renderizable ahora | `PROVEN` (medido) |
| **Si este hardware redondea o trunca** | `NOT_DETERMINED` — sin contexto |
| El bloqueo de F2 es el mismo que el de F1 | `PROVEN` |

## Procedencia

- `RUNTIME_READ_ONLY`: `vulkaninfo`, `glxinfo`, `eglinfo`, programas GL propios.
  Sin escrituras a la GPU.
- `IMPLEMENTATION`: `f2_sampler_probe.c`, nuevo, en el directorio del proyecto.
- Sin root para el experimento. Root sólo se usó para `lsmod`/`sysfs` de lectura.
- No se editó `OPEN-FRONTIERS.md` ni `F2`: son de otra sesión. Se informa.
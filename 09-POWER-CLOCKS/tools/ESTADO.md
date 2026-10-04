# carga_gfx — INSTRUMENTO `SELF_TESTED`, NO VALIDADO

> **Este fichero NO es un hallazgo.** No hay claim sobre la GPU. Hay un
> generador de carga que funciona y **dos observaciones que no puedo interpretar
> todavía**. §82: SIN RESULTADO VALIDADO, NO HAY CAMBIO DE ESTADO.

## Qué funciona, y está medido

```
$ ./carga_gfx --segundos 6 --iter 64
dispositivo EGL 0: /dev/dri/card1  vendor=0x1002   <== ELEGIDO
dispositivo EGL 1: /dev/dri/card0  vendor=0x8086
GL_RENDERER = AMD Radeon RX 550 / 550 Series (radeonsi, polaris12, ACO,
                DRM 3.64, 7.1.3-200.nobara.fc44.x86_64)
```

- **La verificación de target funciona** (§3). El instrumento elige el nodo por
  `vendor` de sysfs y **aborta con código 4 si no encuentra `0x1002`**, en vez de
  medir la Intel. Probado con `--forzar-vendor 0x8086`.
- El contexto GLES 3.2 se crea y el renderer **identifica polaris12**.
- EGL **surfaceless**: sin superficie, sin scanout, sin CRTC.

## Las dos observaciones que NO puedo interpretar

| # | observación | por qué no es un resultado |
|---|---|---|
| 1 | `fps` apenas cambia al multiplicar `iter` por 16 (165k → 154k) | si la GPU **estuviera saturada**, 16× más trabajo por frame daría 16× menos fps. O la carga no satura, **o el shader se está optimizando**. No sé cuál |
| 2 | SCLK sube al onset (661 MHz a 801 MHz según carga) y **vuelve a 214 MHz** en los tres casos | el valor de t=1.0 s es una **muestra de la rampa de subida**, no un régimen. Con más carga subió MENOS (338 MHz a iter=1024), lo que es coherente con que el reloj de la muestra depende de cuándo empezó la subida |

## Y el oráculo que debía resolverlo tampoco vale

`smoke.c` lee un pixel del framebuffer tras el draw:

```
iter      px[0]  px[1]  px[2]
    1          0      0      0
 4096          0      0      0
```

**Con `EGL_NO_SURFACE` no hay framebuffer por defecto ligado al framebuffer de
lectura**, así que `glReadPixels` devuelve ceros. A `iter=1` el shader debería
escribir ≈119 en el canal rojo. `px=0` mide **el readback**, no el shader.

## Qué falta para que esto sea un instrumento `VALIDATED`

1. **Un FBO real** con renderbuffer, y leer de ahí. Sin eso no hay oráculo
   independiente y no se puede saber si el shader se ejecuta.
2. **Un criterio de saturación declarado.** "La GPU está saturada" tiene que ser
   una afirmación con número: p. ej. fps insensitive a `iter` **Y** lectura no
   nula **Y** SCLK estable. Ahora mismo no tengo ninguno de los tres.
3. **Una measurement del SCLK que no sea la rampa.** Muestrear cada 100 ms en vez
   de cada 1 s, y reportar la mediana de los últimos segundos, no el primero.
4. Repetir el punto de carga con `--forzar-vendor 0x8086` para demostrar que el
   número cambia al cambiar de chip — el discriminante que faltaba.

## Errores que cometí escribiéndolo, y que quedaron corregidos

| error | cómo se manifestó |
|---|---|
| `EGL_PLATFORM_DEVICE_EXT` escrito como `0x31DD` | ese valor es `SURFACELESS_MESA`; `DEVICE_EXT` es `0x313F`. Leído de `eglext.h:888` después |
| ruta de sysfs construida con el path completo | `/sys/class/drm//dev/dri/card1/…` → `vendor = -1` impreso como `0xffffffffffffffff`, que parece una medición |
| `fma()` en el shader | GLSL ES 3.20 **no lo tiene**: `no function with name 'fma'`. Ahora es `a*x + 0.5` |

Los tres son del mismo tipo: **un número o un código que parecía correcto y no lo
era**. El que más costó es el segundo, porque un `-1` impreso con `%lx` parece un
vendor ID.

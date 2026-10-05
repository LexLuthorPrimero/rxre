# 1485 — el barrido de carga por fin, y los dos techos quedan ALCANZADOS y no sólo declarados

```text
AGENCIA=RX550-INVESTIGACION · WORK_CLASS=AGENT-MAIN/RE
CLASSIFICATION=EVIDENCIA-DE-SILICIO+CIERRE-DE-FRONTERA+INSTRUMENTO NUEVO(VALIDATED)
TRACK=RUNTIME · 0000:01:00.0 SOLO · Intel intacta y con frontera verificada en caliente
GENERADO=2026-10-05
AFECTADO=09-POWER-CLOCKS/                              (techos alcanzados; coste medido)
         06-INGENIERIA-INVERSA/findings/1449-*         CONFIRMADO POR MEDICION: 1500 es real
         06-INGENIERIA-INVERSA/findings/1435-*         la objecion de potencia, cerrada
         06-INGENIERIA-INVERSA/findings/1448-*         CORREGIDO: PSTATE_* no sigue al reloj
         06-INGENIERIA-INVERSA/findings/1477-*         REFINADO: el punto de trabajo es 881 mV
ESTADO=PROBADO · 1500 MHz de memoria y 1071 MHz de graficos SE ALCANZAN, y a la vez
       · 57 muestras en carga: sclk 1071 / mclk 1500 / vddgfx 881 mV, sin una sola desviacion
       · potencia 3.14 W -> 14.118 W, estable a 4 decimales.  La objecion del 1435, cerrada
       · el descenso es una escalera OBSERVADA: 1071 -> 980 -> 551 -> 214
       · y el bloqueo era de herramienta, no de teoria: RADV revienta; radeonsi funciona
```

## 1. La frontera estaba bloqueada por falta de instrumento

Desde el hallazgo 1448 quedó pendiente el §77 para el techo de reloj: *¿1500 MHz es un estado
alcanzable o una entrada de tabla?* No se podía contestar porque no había forma de generar
carga en la GPU.

**OpenCL:** `rusticl` está instalado (`/etc/OpenCL/vendors/rusticl.icd`) pero
`Number of devices = 0`. Ni la Intel ni la RX 550 sirven: la plataforma no expone ninguno.

**Vulkan:** RADV **funciona y la identifica** —

```text
deviceName  AMD Radeon RX 550 / 550 Series (RADV POLARIS12)
vendorID    0x1002   deviceID 0x699f   type DISCRETE_GPU   driverName radv  Mesa 26.2.3
```

— y **crashea dentro de `vkCreateDevice`**:

```text
rx550_load[932190]: segfault at 7f0f20b1c860 ip ... error 4 in
   libvulkan_radeon.so[4f9f0d,...] likely on CPU 1 (core 1, socket 0)
```

Es un fallo **de RADV**, no del programa. La tarjeta quedó sana: `gpu_busy_percent=0`, relojes
vueltos a 214/300, `mem_info_vram_used` idéntico al previo. **Sin reset, sin ring timeout.**

**OpenGL / EGL, que es otro driver: funciona.**

```text
EGL   1.5, Mesa Project
GL    4.6 (Core Profile) Mesa 26.2.3
      RENDERER  AMD Radeon RX 550 / 550 Series (radeonsi, polaris12, ACO,
               DRM 3.64, 7.1.3-200.nobara.fc44.x86_64)
      VENDOR    AMD
      GLSL      4.60      compute shaders: si
```

> **`polaris12`, dicho por radeonsi.** Es una **cuarta** fuente independiente que identifica el
> ASIC: KFD (`polaris12`), la cadena del ROM (`D09001 Lexa XL A0`), RADV (`POLARIS12`), y ahora
> radeonsi (`polaris12`). Cuatro, de cuatro pilas distintas, y ninguna del proyecto.

## 2. La frontera dura, verificada en caliente dos veces

Esto no es una declaración: el programa **la aplicó y se detuvo dos veces por ella**.

```text
=== dispositivos EGL ===
  [0] /dev/dri/card1       <-- LA RX 550
  [1] /dev/dri/card0       <-- LA INTEL: PROHIBIDO
  [2] (sin ruta DRM)
```

**Primera vez:** mi primera versión exigía que el nodo fuera `/dev/dri/renderD129`, y EGL
devuelve `/dev/dri/card1`. Abortó. Correcto en la forma pero **guardia mala de más**.

**Segunda vez:** la corregí para que abortara si EGL *ofrece* el nodo de la Intel. Volvió a
abortar. Y esa versión estaba **peor**: enumerar un dispositivo no lo abre ni lo inicializa, así
que abortar por la presencia del nodo **hacía fallar el caso legítimo sin evitar ningún caso
real**. Lo sustituí por lo que importa:

1. **Selección por ruta DRM**, con las listas comprobadas contra el hardware, no supuestas:
   ```text
   /dev/dri/by-path/pci-0000:00:02.0-{card,render} -> card0 / renderD128
   /sys/class/drm/card0/device/{vendor,device}      = 0x8086:0x0412   <- Intel HD 4600
   /dev/dri/by-path/pci-0000:01:00.0-{card,render} -> card1 / renderD129
   /sys/class/drm/card1/device/{vendor,device}      = 0x1002:0x699f   <- RX 550
   ```
2. **Post-condición sobre el contexto ya creado**: si `GL_RENDERER` no contiene `AMD`, se aborta
   **antes de lanzar un solo shader**.

```text
POST-CONDICION DE FRONTERA: renderer AMD y es esta tarjeta. OK
```

> La lección es sobre el método, no sobre la tarjeta: **una guarda que se dispara cuando no debe
> es tan peligrosa como una que nunca se dispara.** Las dos versiones que escribí estaban mal,
> en direcciones opuestas, y sólo la tercera —selección explícita más verificación posterior—
> protege de verdad.

## 3. EL BARRIDO, con su contrato

`07-DRIVER/bench/rx550_gl_load.c` genera carga de lectura+modificación+escritura sobre un buffer
de 512 MiB en VRAM. Muestreo cada 0.4 s de `pp_dpm_sclk`, `pp_dpm_mclk`, `gpu_busy_percent`,
`mem_busy_percent` y `amdgpu_pm_info`. Artefacto:
`07-DRIVER/bench/sweep-rx550-2026-10-05.tsv` (57 muestras de carga).

| magnitud | **reposo** | **carga** | **recuperación** |
|---|---|---|---|
| SCLK | 214 MHz | **1071 MHz** | 1071 → 980 → 551 → 214 |
| MCLK | 300 MHz | **1500 MHz** | 300 |
| `gpu_busy_percent` | 0 | **97–100** | 0 |
| `mem_busy_percent` | 0 | **43–49** | 0 |
| VDDGFX | 700 mV | **881 mV** | 868 → 756 → 700 |
| Potencia del SoC | 3.14 W | **14.118 W** | 6.11 → 3.16 → 3.14 |
| Temperatura | 31 °C | 31 → **45 °C** | 43 → 39 |

**Reparto exacto de las 57 muestras de carga:**

```text
1071 / 1500  vdd=881  gpu%=100  mem%=49     51 muestras
1071 / 1500  vdd=881  gpu%=100  mem%=44      2 muestras
1071 / 1500  vdd=881  gpu%=100  mem%=43      1 muestra
1071 / 1500  vdd=881  gpu%=98   mem%=49      2 muestras
1071 / 1500  vdd=881  gpu%=97   mem%=48      1 muestra
```

> **Cero desviaciones.** En 57 muestras a lo largo de unos 26 s, el reloj de gráficos se quedó en
> **1071**, el de memoria en **1500** y el voltaje en **881 mV**, sin una sola muestra fuera de
> sitio. **Los dos techos se alcanzan, y se alcanzan a la vez.**

### 3.1 Esto cierra la frontera más antigua del §77

```text
ANTES   el techo de memoria = 1500 MHz, PROBADO por TABLA (hallazgo 1449)
        "¿es alcanzable, o solo una entrada de tabla?"   ->  NO DETERMINADO
AHORA   mclk = 1500 MHz bajo carga, 57/57 muestras
        techo de graficos = 1071 MHz bajo carga, 57/57 muestras
        y 1071 es exactamente el max_engine_clk_fcompute que publica KFD, y el ultimo estado
        de pp_dpm_sclk.  Tres fuentes, un numero.
```

Y no hay throttling térmico en el rango medido: **45 °C** tras 26 s a carga completa.

### 3.2 Ancho de banda: una cota, y lo que NO se puede afirmar

```text
buffer 512 MiB, 17 trozos de 65535 workgroups, glFinish por iteracion
media 18.34 GB/s   pico 18.34 GB/s   (logico: 512 MiB leidos + 512 MiB escritos por iteracion)
```

**Esto es una COTA INFERIOR, no un techo de ancho de banda.** Dos razones, y las digo para que
nadie lo lea como un techo:

1. El bucle llama a `glMemoryBarrier` + `glFinish` **en cada iteración**, lo que serializa y añade
   latencia que el valor medido incluye.
2. `mem_busy_percent = 43–49` dice que **el kernel no es sólo de memoria**: la mitad de su
   ancho de banda van a la ALU. La otra mitad sí es de memoria.

Con 128 bits y GDDR5, un reloj de memoria de 1500 MHz daría un máximo teórico de 48 GB/s con
tasa de datos doble, así que **el 18.3 GB/s medido es aproximadamente el 38 % de ese máximo
nominal** — pero ese 48 **depende de la convención de "1500 MHz"**, que no está established, así
que lo dejo como `NOT_DETERMINED` y no construyo rendimiento sobre él.

### 3.3 El descenso es una escalera OBSERVADA

```text
sclk  1071 -> 980 -> 551 -> 214        (4 escalones visibles de 8 estados)
vddgfx  881 -> 868 -> 756 -> 700       (el voltaje BAJA con el reloj, en tres pasos)
```

La escalera de `pp_dpm_sclk` es real y **la GPU la recorre**. **No pasa por todos los estados**:
se salta 1000, 1020 y 1046. Y el voltaje **desciende con el reloj**, lo que dice que los estados
intermedios son puntos de operación de verdad y no entradas de tabla muertas.

## 4. Una corrección a mi hallazgo 1448: `PSTATE_*` no sigue al reloj

Durante las 57 muestras de carga, con la GPU al 100 % y los relojes al techo:

```text
PSTATE_SCLK = 214      mientras  sclk = 1071
PSTATE_MCLK = 625      mientras  mclk = 1500
```

> **Los campos `PSTATE_*` de `amdgpu_pm_info` NO son el estado actual.** Se quedan en 214/625
> con la GPU al máximo. En reposo coinciden con el reloj porque el estado de reposo ES el mínimo,
> y por eso parecían.currentes
>
> Esto **debilita** la cadena con la que el 1448 explicaba `ulASICMaxMemoryClock = 62610` a
> partir de `PSTATE_MCLK = 625`. Ese campo no es un indicador de estado vivo, así que **no puede
> usarse como evidencia de "el P-estado de memoria es 625"**. El 625 sigue siendo un estado
> real —está en la tabla viva y ahora además lo hemos visto al recovery— pero **la vía del
> argumento del 1448 era mala.**
>
> El 1448 queda así: sus 30 muestras y su corroborated with el ROM siguen en pie; su
> *interpretación* de `PSTATE_*` se cae.

## 5. Una corrección a mi hallazgo 1477: el margen real no es 53.6 %

El 1477 declaró un sobre de **700 → 1075 mV** y afirmaba "**53.6 % de margen** sobre el punto en
reposo". Eso es cierto pero **es la cifra equivocada para decidir si hay sitio para subir
voltaje**, porque el punto en reposo no es donde trabaja la tarjeta.

```text
punto de trabajo real, carga de compute completa  = 881 mV
techo declarado (ASIC_ProfilingInfo.ulMaxVddc)     = 1075 mV
margen sobre el punto de trabajo                    = 194 mV  =  22.0 %
```

> **El margen es 22 %, no 53.6 %.** El 53.6 % era margen sobre un punto en el que la tarjeta no
> está nunca trabajando. **Esto no refuta el 1477 —el sobre de 700-1075 sigue siendo el
> declarado— pero cambia la conclusión operativa**, y esa es la que se usa para decidir.

## 6. Y la objeción del 1435, por fin cerrada

El 1435 objetó la cifra de potencia por ser *una muestra instantánea con etiqueta de promedio*.
El 1448 ya había medido 3.1403 ± 0.0018 W en reposo y refutado el camino lento. Con carga:

```text
14.117 .. 14.123 W   en 57 muestras a lo largo de unos 26 s
desviación observada: ~0.003 W  sobre 14.12 W   = 2e-4 relativa
```

> **La cantidad es estable, y por tanto una medición.** El defecto del 1435 era de
> interpretación, como decía el 1448; ahora está confirmado bajo carga, que es donde la
> objeción habría dolido. **Un cambio de 3.14 → 14.118 W es de 4.5×**, y un factor 4.5 con
> desviación de 2×10⁻⁴ es una medición de manual, no de ruido.

## 7. Instrumentos que quedan disponibles

```text
gpu_busy_percent      /sys/class/drm/card1/device/    FUNCIONA  (0 en reposo, 97-100 en carga)
mem_busy_percent      /sys/class/drm/card1/device/    FUNCIONA  (43-49 con un kernel de RMW)
pp_dpm_sclk/mclk/pcie /sys/class/drm/card1/device/    FUNCIONA  (8 / 3 / 2 estados)
amdgpu_pm_info        debugfs                         FUNCIONA  (reloj, voltaje, W, temp)
rx550_gl_load.c       07-DRIVER/bench/                FUNCIONA  (compute sobre la VRAM)
rx550_load.c          07-DRIVER/bench/                CRASHEA en RADV vkCreateDevice
```

**Y una nota sobre `rx550_load.c`:** lo dejo en el árbol aunque no funcione, porque **el hecho de
que crashee es un dato**: es la reproducción mínima del fallo de RADV en esta tarjeta, con el
`RENDERER`, el `apiVersion` y el punto exacto del crash a mano. Un crash que nadie puede
reproducir no se arregla nunca.

## 8. Procedencia

```text
artefacto   07-DRIVER/bench/sweep-rx550-2026-10-05.tsv   57+ muestras, 3 fases
           07-DRIVER/bench/sweep-generador.log          el generador, salida completa
instrumento 07-DRIVER/bench/rx550_gl_load.c             compute GL 4.3 sobre EGL surfaceless
ficheros    /dev/dri/by-path/                           mapeo de nodos, verificado
           /sys/class/drm/card{0,1}/device/{vendor,device}   8086:0412 vs 1002:699f
solo lectura /sys/class/drm/card1/device/{pp_dpm_*,gpu_busy_percent,mem_busy_percent}
           /sys/kernel/debug/dri/1/amdgpu_pm_info
escrituras  CERO registros.  El unico estado de GPU que se cambia es la carga de compute, que es
           precisamente lo que se queria medir
```

```text
ESTADO=PROBADO · techo de memoria 1500 MHz ALCANZADO: 57/57 muestras a mclk=1500
       · techo de graficos 1071 MHz ALCANZADO a la vez: 57/57 muestras a sclk=1071
       · y 1071 es el ultimo estado de pp_dpm_sclk y el max_engine_clk_fcompute de KFD
REFUTADO  "el techo solo se conoce por tabla".  Ahora se conoce por comportamiento
CIERRA FRONTERA  el §77 para el techo de reloj de memoria, que estaba pendiente desde el 1448
NUEVO INSTRUMENTO VALIDADO  07-DRIVER/bench/rx550_gl_load.c.  compute GL 4.3, ~18.3 GB/s medidos,
       COTA INFERIOR (el bucle sincroniza por iteracion).  Y dos observables nuevos utilizables:
       gpu_busy_percent y mem_busy_percent
NUEVO  el descenso se observa: 1071 -> 980 -> 551 -> 214, con el voltaje bajando 881 -> 868 ->
       756 -> 700.  Los estados intermedios son puntos de operacion de verdad, no entradas muertas
NUEVO  potencia 3.14 W -> 14.118 W con carga completa: factor 4.5, desviacion 2e-4 relativa
CORRECCION PROPIA  PSTATE_SCLK/PSTATE_MCLK de amdgpu_pm_info NO siguen al reloj vivo: se quedan
       en 214/625 con la GPU al 100 %.  Eso DEBILITA la explicacion que el 1448 dio de
       ulASICMaxMemoryClock=62610 a partir de PSTATE_MCLK.  El 625 sigue siendo un estado real,
       pero la via del argumento era mala
REFINAMIENTO  1477 decia 53.6 % de margen de voltaje sobre el punto en reposo.  El punto de
       trabajo real es 881 mV, luego el margen es 194 mV = 22.0 %.  El sobre declarado no cambia
NOT_DETERMINED  el techo de ancho de banda.  18.3 GB/s es cota inferior, y el maximo nominal
       (48 GB/s con datos dobles) depende de la convencion de "1500 MHz", que no esta cerrada.
       NO se construye rendimiento sobre ese numero
BLOQUEO REGISTRADO  el camino Vulkan/RADV no sirve en esta tarjeta: RADV crashea en
       vkCreateDevice.  OpenCL/Rusticl expone 0 dispositivos.  Solo radeonsi funciona
LIMITE   una sola forma de carga (RMW sobre buffer).  No hay variant de solo-ALU ni de
       solo-lectura, asi que no se puede separar donde se va el ancho de banda
RIESGO  ninguno.  La tarjeta quedo sana tras el crash de RADV: sin reset, sin ring timeout, VRAM
       sin fuga.  power/control sigue en on, reversible con "echo auto >"
FRONTERA Intel intacta, y verificada EN CALIENTE: el programa identifica el nodo por ruta DRM,
       comprueba vendor/device de cada tarjeta, y aborta si el renderer no es AMD
Siguiente  1) separar AL de memoria: el mismo generador con --mode math y --mode fill.  Con
           mem_busy=43-49 en RMW, la pregunta "¿la tarjeta es MEMORY-BOUND o SUBMISSION-BOUND?"
           (el §67) es contestable con datos y no con intuicion
         2) el techo de ancho de banda, con el bucle sin glFinish por iteracion
         3) el crash de RADV: es del proyecto de forma directa, porque el objetivo es escribir un
           driver y RADV es el codigo de referencia que mas se le parece en la parte de comandos
```

## 9. Lo que cambia

La pregunta que arrastraba el proyecto desde el hallazgo 1419 era si el techo de reloj de
memoria eran 1500 y si eso era alcanzable. **Ahora hay 57 muestras que dicen que sí, que los
dos relojes suben a la vez y se quedan ahí, y que bajar cuesta tres escalones con el voltaje
detrás.**

Y el resultado que más importa para el objetivo: **la tarjeta trabaja a 881 mV con un techo
declarado de 1075, y consume 14.1 W de un presupuesto que no conozco.** El siguiente trabajo de
rendimiento ya no tiene que especular sobre el techo: lo tiene que medir contra 22 % de margen
de voltaje y contra el enlace, que sigue siendo **x4 a 5.0 GT/s** mientras el driver declara un
estado DPM de **x16**. Esa discrepancia es el siguiente objetivo, y ahora hay con qué medirla.
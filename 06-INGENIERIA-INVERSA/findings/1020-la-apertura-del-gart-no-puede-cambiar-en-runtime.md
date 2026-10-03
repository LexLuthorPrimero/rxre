# 1020 · La apertura del GART no puede cambiar en runtime: sus dos entradas son constantes de carga, y el `512 MiB` de `amdgpu_device.c` es un default anterior al `switch`, no un cambio

```
RENUMERADO: 1011 → 1020 el 2026-10-03. Dos sesiones tomaron 1011 con veinte
segundos de diferencia. Mi reserva era anterior (16:04:03) pero la herramienta
que reparte números no puede ni ver los de 4 cifras (§8), así que la colisión
era previsible y no fue culpa de quien reservó. Renumerar era gratis porque
nadie citaba el 1011 todavía; el coste de renumerar sube con cada cita.
```

```
CLASSIFICATION=DOCUMENTATION+REPAIR · TRACK=STATIC
AGENTE=AGENT-09 (GART) · FECHA=2026-10-03
CORPUS=RESEARCH/kernelbuild/linux-7.1.3/drivers/gpu/drm/amd/amdgpu
HARDWARE_SCOPE=RX 550 0000:01:00.0 Polaris12/GFX8
WORK_CLASS=READ_ONLY · WRITE_LOCAL=PROPIOS · MODIFICATIONS_CORPUS=0
RUNTIME=NOT_RUN (todo esto es lectura de fuente) · GPU INTACTA · sin sudo
```

## Qué cierra

`100` dejó una fila que es la única que quedaba abierta sobre la *apertura* del
GART, y la dejó con la fórmula más honesta del proyecto:

> *"Si el GART puede crecer en runtime"* → **`NOT_DETERMINED`**

**Cierra como `PROVEN_ABSENT`: no existe camino de crecimiento en runtime.** No por
opinión, sino por enumeración exhaustiva de los escritores de las dos magnitudes
que la definen, y por un contrafactual que casi la refutaba y no la refuta.

## 1 · El mapa de escritores, completo, para GFX8

`adev->gmc.gart_size` — todos los escritores del corpus, filtrados a los que
alcanzan esta ASIC:

| escritor | función | cuándo | valor |
|---|---|---|---|
| `amdgpu_device.c:3699` | `amdgpu_device_init` | **antes** del `switch` de ASIC | `512 MiB` ← **default** |
| `gmc_v8_0.c:595` | `gmc_v8_0_init_gart` | bring-up | `256ULL << 20` ← ** Polaris12** |
| `gmc_v8_0.c:601` | ídem | bring-up | `1024ULL << 20` ← Tonga/Carrizo, no esta ASIC |
| `gmc_v8_0.c:605` | ídem | bring-up | `amdgpu_gart_size << 20` ← si el parámetro está fijado |
| `gmc_v8_0.c:608` | ídem | bring-up | `+= smu_prv_buffer_size` (= 0 aquí, `204`) |
| `amdgpu_gmc.c:309` | `amdgpu_gmc_gart_location` | bring-up | `= max(size_bf, size_af)` ← **el clamp, y no se dispara** (`204`) |

`mc->gart_start` / `mc->gart_end` — **todos** los escritores están en
`amdgpu_gmc.c`, y sólo en dos funciones:

```
amdgpu_gmc_agp_location     :263-264   (AGP, granularidad 16 GiB — 054 §5)
amdgpu_gmc_gart_location    :314-333   (BEST_FIT — 054 §4)
```

**Y cada una de esas dos tiene un único llamador para GFX8:**

```
amdgpu_gmc_gart_location  ←  gmc_v8_0.c:422   en gmc_v8_0_vram_gtt_location()
gmc_v8_0_vram_gtt_location ←  gmc_v8_0.c:609   en gmc_v8_0_mc_init()
gmc_v8_0_mc_init          ←  gmc_v8_0.c:1149  en gmc_v8_0_sw_init()   ← UNA VEZ
gmc_v8_0_gart_enable      ←  gmc_v8_0.c:1228  en gmc_v8_0_hw_init()   ← UNA VEZ
```

**⇒ No hay ningún escritor de `gart_size`, `gart_start` ni `gart_end` fuera del
bring-up del dispositivo.** `PROVEN` por enumeración de call-sites.

## 2 · El contrafactual que casi la refutaba

Buscando escritores encontré uno que **no estaba en el mapa de nadie** y que
dice, sin condición de ASIC:

```c
amdgpu_device.c:3699   adev->gmc.gart_size = 512 * 1024 * 1024;
```

Si ese camino alcanzara a Polaris12, la apertura sería **512 MiB** y no 256, y
`067`/`204`/`100` estarían refutados por el driver de esta placa.

**No lo alcanza, y se ve en el propio fichero.** `3699` está en
`amdgpu_device_init`, en el bloque de inicialización de campos, y
`gmc_v8_0_init_gart` corre **después** y lo sobreescribe con el valor del ASIC:

```
amdgpu_device_init()            →  gart_size = 512 MiB   (default genérico)
   └─ sw_init → gmc_v8_0_init_gart → switch(asic_type)
                                          case CHIP_POLARIS12:
                                              gart_size = 256ULL << 20
   └─ hw_init → gmc_v8_0_gart_enable  → programa los registros
```

**El `512 MiB` es un valor inicial, no un resize.** Es exactamente el mismo patrón
que un `= 0` de guarda: existe para que el campo tenga un valor válido antes de
que lo compute quien sabe calcularlo.

> **Esto habría sido un `REFUTED` muy convincente si no se hubiera comprobado
> el orden.** Un `gart_size = 512 MiB` sin condición, en el fichero que inicializa
> el dispositivo, parece una contradicción directa del `256 MiB` observado. Lo
> que lo salva es una sola pregunta —*¿se ejecuta esto antes o después del
> `switch`?*— y esa pregunta la responde el orden de llamadas, no la lectura de
> la línea.

## 3 · Las dos entradas que sí podrían cambiarlo, y por qué no cambian

Un `NOT_DETERMINED` bien cerrado exige que **las dos** entradas sean inmutables,
no una.

| entrada | dónde nace | ¿puede cambiar en runtime? |
|---|---|---|
| `amdgpu_gart_size` | `amdgpu_drv.c:154` `= -1`, `module_param_named` `:293` modo **`0600`** | **NO.** Un parámetro de módulo se fija en `insmod` |
| `smu_prv_buffer_size` | `amdgpu_device.c:1494`, en bring-up | **NO** — `204` lo dejó como 0 en esta placa |
| `mc_mask`, `fb_start`, `fb_end`, `max_mc_address` | `amdgpu_gmc_init`, bring-up | **NO** |

**El segundo caso requiere una precisión que `977 §4` ya defendant's:** que
`amdgpu_gart_size` sea `0600` significa que **root puede escribirlo**, no que sea
inmutable. Lo correcto es: **`PROVEN` que no hay escritor en runtime**, no
"es constante". Root podría dar `rmmod` + `insmod` con otro valor — eso es un
**reinicio de módulo**, no un crecimiento en runtime, y en ese caso el GART se
reconstruye entero, incluida la tabla.

## 4 · El matiz que NO se puede saltarse: los registros sí se reprograman

Aquí es donde una lectura rápida habría overclaimed, y donde el proyecto ya tiene
el antecedente escrito (`977 §6.2`: *"Un centinela pegado al array detecta el
desbordamiento pegado. No detecta el lejano"*).

`gmc_v8_0_gart_enable` está en `gmc_v8_0_hw_init`, y **`hw_init` se vuelve a
llamar** desde las rutas de reset y recuperación:

```
amdgpu_device.c:2132, :2159, :2199   (reset / recovery)
amdgpu_device.c:3188, :3228
```

**⇒ Los registros del GART se reprograman en runtime, tras un reset de la GPU.**

Lo que **no** cambia es el **valor**: ambos caminos recalculan desde las mismas
entradas inmutables de §3. Reset re-programa la misma apertura.

> **La distinción es entre *reprogramar* y *cambiar*, y son cosas distintas.**
> "El GART no se reprograma en runtime" sería **falso** — se reprograma en cada
> reset. "El GART no cambia de apertura en runtime" es lo que sostiene la
> evidencia, y por eso lo digo con esas palabras y no con las otras.

**Ésta es la razón por la que el `NOT_DETERMINED` de `100` estaba bien
plantado.** La pregunta *"¿puede crecer?"* tiene dos lecturas posibles —
*¿puede recalcularse?* (sí) y *¿puede cambiar de valor?* (no)— y responder la
primera por la segunda habría producido un `REFUTED` falso. `100` no eligió.

## 5 · Una lectura de `977 §4`, verificada aquí

`977` dejó escrito que `amdgpu_device.c:1556` *"rechaza valores `< 32`"*. La línea que
contiene esa lógica es otra, en la función de validación de argumentos:

```
amdgpu_device.c:1542   static int amdgpu_device_check_arguments(struct amdgpu_device *adev)
amdgpu_device.c:1560       amdgpu_gart_size = -1;        ← fuerza "auto"
```

**Y esto confirma por qué `100` lo dejó como `NOT_IN_CORPUS`.** `100` escribió
*"`amdgpu_gart_size` no aparece en `journalctl`, luego en esta máquina no se
fijó"*. Eso es correcto **y** es lo que hace `check_arguments` ilegible desde
arriba: si el valor se rechazara, `check_arguments` imprimiría un `warn`. No hay
`warn` porque no se rejected nada — **y porque no se fijó**. Las dos explicaciones
son distinguibles y el log las separa.

## 6 · Lo que cambia de estado

| Afirmación | Antes | Ahora |
|---|---|---|
| La apertura del GART puede crecer en runtime | `NOT_DETERMINED` (`100`) | **`PROVEN_ABSENT`** — no hay escritor fuera de bring-up |
| Los registros del GART se reprograman en runtime | nourtout stated | **`PROVEN`** — `hw_init` en las rutas de reset |
| `amdgpu_device.c:3699` `= 512 MiB` | desconocido | **`PROVEN_DERIVED`** default pre-`switch`, no resize |
| Los dos llamadores de la colocación, uno cada uno | — | **`PROVEN`** (`609`, `1228`) |
| `gart_size` observado = 256 MiB | `OBSERVED` + `PROVEN` | sin cambio, **y ahora con su permanencia explicada** |
| `gartsize` real de esta placa | `NOT_READABLE` (`1010 §7`) | sin cambio — requiere root |

## 7 · Límites

1. ~~**`NOT_IN_CORPUS`, y es un límite real:** `si_meminfo`, `drm_buddy` y la capa
   TTM no están en `working/`.~~

   **CORREGIDO por `1026` el 2026-10-03, por medición, no por opinión.**
   Se comprobó fichero por fichero en los dos árboles que hay, y la frase era
   mezcla de dos capas con el mismo nombre corto:

   | fichero | `working/` | `kernelbuild/` | veredicto |
   |---|---|---|---|
   | `amdgpu_ttm.c` / `.h` (el lado **amdgpu** de TTM) | **PRESENTE**, 80357 B | PRESENTE | **REFUTADO** |
   | `drivers/gpu/drm/ttm/` (la capa TTM **genérica**) | ausente | ausente | `CORROBORADO` |
   | `drm_buddy.c` / `drm_buddy.h` | ausente | PRESENTE | `CORROBORADO` en `working/` |
   | `si_meminfo.c` | ausente | ausente | `CORROBORADO` |

   Lo que falta de verdad es `drivers/gpu/drm/ttm/`, que no está en ninguno de los
   dos árboles. `amdgpu_ttm.c` **sí** está, y es la pieza que responde «cómo
   reserva amdgpu VRAM».

   Consecuencia para este documento: la afirmación de que *cualquier* afirmación
   sobre resize de VRAM que traverse TTM «sigue sin poder derivarse» era más
   fuerte de lo que el árbol permite. Lo que sigue en pie es lo de
   `amdgpu_gmc.c`, que no se toca: **no tiene** ningún `resize_vram`, y eso se
   registró como `NOT_FOUND` en `amdgpu_gmc.c`, **no** como ausencia en el driver.
   Una cosa es no encontrarlo en un fichero, y otra es no poder buscarlo.
2. La enumeración de escritores es sobre `amdgpu/` en `kernelbuild`. Un
   `MODULE_FORCE_ASIC` podría llevar `adev->asic_type` a un `case` distinto
   (`amdgpu_device.c:3690-3693`, el mismo bloque que fija `gart_size`): es un
   parámetro `0600` y en esta placa no se usó. Si se usara, cambiaría el `case`,
   no la regla.
3. **Nada de esto se ejecutó.** Es lectura de fuente. La confirmación de que
   `256 MiB` *persiste* tras un reset real es `RUNTIME`, y no se hizo: requiere
   inducir un reset de GPU, que es `HIGH_RISK` y no está justificado por una
   pregunta que la fuente ya responde.

## 8 · Procedencia

```
STATIC  RESEARCH/kernelbuild/linux-7.1.3/drivers/gpu/drm/amd/amdgpu
        amdgpu_drv.c:154,:293              módulo param, 0600, -1
        amdgpu_device.c:1542,:1560        check_arguments fuerza -1
        amdgpu_device.c:3690-3693,:3699    asic_type por force, y gart_size = 512 MiB
        amdgpu_device.c:2132,2159,2199,3188,3228   hw_init en reset/recovery
        amdgpu_gmc.c:263-264, 309, 314-333 Todos los escritores de start/end/size
        gmc_v8_0.c:411-423 (vram_gtt_location), :595,:601,:605,:608 (init_gart),
                  :609 (unico caller), :1149, :1228 (unico caller)
        gmc_v6_0.c / v7_0 / v9_0 / v10_0 / v11_0 / v12_0  writers de otras ASIC
RUNTIME NOT_RUN
ENCADENADA 100 (la fila que cierra), 204 (smu_prv=0, clamp), 067, 054 (BEST_FIT),
           977 §4 (el `0600` y el rechazo de `<32`), 130 (vram_start=0)
```

## 9 · Lo que esta finding hace con la cadena del GART

La cadena de AGENT-09 queda así, y cada eslabón con su estado:

```
VRAM            2048 MiB, base 0xF400000000        PROVEN + OBSERVED (log)
  ↓
GTT             5907 MiB = si.totalram/2 páginas  PROVEN (1010)  ← cerrado este turno
  ↓
GART placement  BEST_FIT → 0xFF00000000            PROVEN_DERIVED, bit a bit (054)
GART aperture   256 MiB / 65536 entradas           PROVEN + OBSERVED, y ahora INMUTABLE
GART base/end   0xFF00000000 / 0xFF0FFFFFFF        PROVEN_DERIVED (054, 204)
page size       4 KiB                              PROVEN
alignment       4 GiB                              PROVEN
MC hole         sin efecto en 40 bits              PROVEN_DERIVED (054)
tabla           BO en VRAM, offset GPU             PROVEN (067)
GPUVM           vram_start = 0 → GART vestigial    PROVEN_DERIVED (204, 130)
```

**El único `NOT_DETERMINED` que quedaba sobre la geometría del GART era el de
este hallazgo, y está cerrado.** Lo que queda `NOT_DETERMINED` en el nodo no es
geometría: es la semántica interna del TLB de L1 y de `SYSTEM_ACCESS_MODE = 3`,
que pertenece a `081`/`195` y no a esta cadena.
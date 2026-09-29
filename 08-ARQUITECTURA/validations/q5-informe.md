# Q-5 — Informe: modelo Python del oracle vs implementación real

**Ámbito**: `08-ARQUITECTURA/` — IA-3 (Arquitecto)
**Fecha**: 2026-09-29 · **Ronda**: 12
**Pre-registro**: `q5-preregistration.md`, commiteado en `1259dc4` **antes** de ejecutar
**Estado de `Q-5`: `NOT_DETERMINED`** — no obtuve la observación que el pre-registro exigía

---

## 1. Veredicto en una línea

**No pude obtener una observación de llvmpipe**, que es lo que `Q-5` tenía que validar. En el
camino encontré un hecho nuevo y sólido que no estaba en el plan, y que **no** reemplaza a `Q-5`.

| | |
|---|---|
| `Q-5` (pre-registro §1) | ¿el modelo predice lo que devuelve **llvmpipe real**? |
| Observación obtenida | el decodificador BC3 **genérico** de Mesa (`fetch_2d_texel_rgba_dxt5`) |
| ¿Son la misma función? | **No.** Son funciones distintas, en drivers distintos |
| `Q-5` | **`NOT_DETERMINED`** |

## 2. Clasificación de clases, como exige el pre-registro

### FACT — ejecutado y verificado

| # | Hecho | Evidencia |
|---|---|---|
| F-1 | `fetch_2d_texel_rgba_dxt5` (`texcompress_s3tc_tmp.h:144-173`) **trunca**: `((a0*(8-code) + a1*(code-1)) / 7)` y `/5`, **sin `+3`, sin `+2`** | lectura del fuente + ejecución |
| F-2 | Ese decodificador coincide con el **truncamiento (bcdec) en 1 048 576 / 1 048 576** (0 discrepancias) | `contrast.py` §A |
| F-3 | Difiere de `spec +3/+2` en **273 372 / 1 048 576** (26.071 %) | ídem |
| F-4 | Mi modelo de `lp_build_lerpdxta` difiere de ese decodificador en **178 638 / 1 048 576** (17.036 %) | ídem |
| F-5 | El corpus de 649 (`5c02833`) conserva las tres respuestas distintas: contra el decodificador real, coincide con `expect_trunc` en **649/649**, y con `expect_llvmpipe` y `expect_spec` en **0/649** | contraste sobre el JSON commiteado |
| F-6 | Los controles negativos `C-1` y `C-2` **detectan** una diferencia inyectada (178 676 y 273 372 discrepancias) | `contrast.py` §B — el contraste discrimina |

### MEASUREMENT — con comando reproducible

```
$ python3 contrast.py
  MODELO (lp_build_lerpdxta)   178638 / 1048576  (17.036 %)
  spec Microsoft +3/+2         273372 / 1048576  (26.071 %)
  truncamiento (bcdec)              0 / 1048576  ( 0.000 %)
  C-1 modelo +1 en 4 pares    178676 / 1048576   -> OK
  C-2 predictor equivocado    273372 / 1048576   -> OK
```

Artefactos: `mesa_generic_alpha.bin`, 1 048 576 B,
sha256 `7ab418eba2eca00e56d381633827abc096243be885d92f09b47a815cc7f2430d`.
Extracción **mecánica** de las líneas 144-173 del header de Mesa (no reescrita a mano), compilada
con `gcc -O2`. Harness en `/tmp/opencode/q5/`, fuera del repo: no es código de ninguna IA.

### MODEL_CHOICE — la diferencia de alcance que decide el veredicto

| | Modelo | Observación |
|---|---|---|
| Función | `lp_build_lerpdxta` (`lp_bld_format_s3tc.c:817-877`) | `fetch_2d_texel_rgba_dxt5` (`texcompress_s3tc_tmp.h:144-173`) |
| Dónde | `src/gallium/auxiliary/gallivm/` — construcción de IR de LLVM | `src/util/format/` — C plano |
| Quién la usa | la texture unit de **llvmpipe** | el decodificador **genérico** de Mesa |
| Aritmética | pesos fijos de 16 bits `255*64/5`, `255*64/7`, dos desplazamientos | división entera directa |

**Son dos implementaciones distintas y no tienen por qué coincidir.** Mi modelo predice la
primera; observé la segunda. El 17.036 % de desacuerdo **no es un error de transcripción**: es la
medida de lo distintas que son. Si mi transcripción estuviera mal, el desacuerdo sería arbitrario;
en cambio el observado coincide con una regla conocida y coherente (truncamiento) en el 100 %.

### LIMITATION — por qué no obtuve la observación de llvmpipe

Las tres rutas Vulkan sobre `10005:0000` fallaron, todas con evidencia:

| Vía | Resultado | Detalle |
|---|---|---|
| **Graphics + `VkImage BC3` muestreada** | `SIGFPE` en `llvm::InstCombinerImpl::visitTrunc`, dentro de `lp_passmgr_run` ← `fs_compile_cb` ← `llvmpipe_update_fs` | primer intento. Causa parcialmente **mía**: usé la image view de la textura BC3 como attachment del framebuffer con un render pass `R8G8B8A8_UNORM`. Corregido con un render target separado |
| **Graphics, ya corregido** | no crashea, pero el readback da **0 en los 1 048 576** texels — **incluido el `LOAD_OP_CLEAR` del propio render pass** (esperado `A=44`, obtenido `0`), sin draw y con los 4 tipos de memoria | control decisivo |
| **Compute + `texture()` sobre BC3** | `SIGSEGV` en código JIT tras el dispatch, con puntero nulo en `#1` | las 8 hilos `llvmpipe-*` estaban vivos: el dispatch sí arrancó |

**Lo que sí funciona**, y acota dónde está el fallo:

| Control | Resultado |
|---|---|
| `vkCmdFillBuffer` + `vkCmdCopyBufferToBuffer` + map | **OK** — leído `0xA5C3F00D` exacto |
| `vkCmdClearColorImage` + `vkCmdCopyImageToBuffer` + map | **OK** — RGBA = `17 34 51 68` exacto, el valor ordenado |
| `vkCmdClearColorImage` sobre la imagen del render pass | **OK** — RGBA = `99 88 77 66` exacto |
| `vkcube --gpu_number 2` (lavapipe) | renderiza, `rc=0` |
| Render pass, incluso sin draw | **zeros** |

Es decir: la copia de imagen y el readback funcionan; **el render pass no produce salida legible
en este host**, y la compute con BC3 muestreada revienta.

**No atribuyo el fallo a lavapipe.** No puedo discriminar entre «lavapipe tiene un fallo» y «mi
harness sigue teniendo un error que no encuentro». Lo que sí es `FACT` es que con este harness no
obtengo la observación. Decir «llvmpipe está roto» sería afirmar más de lo medido.

## 3. Lo que este hecho **obliga** a corregir en el diseño

El pre-registro dice: no modificar el diseño de Fase 3 salvo que la evidencia obligue. **Aquí
obliga**, y en un punto concreto.

**Antes**, el razonamiento era: «en esta host el único rival posible es llvmpipe, y su predicado
lo calculo yo offline». Eso lo escribí en `006` §1 y en `F4-AD-27`.

**Con F-1/F-2**, el marco correcto es más amplio:

```
software BC3 posible en un host Mesa
├── llvmpipe / lavapipe  -> lp_build_lerpdxta      (tercera regla, pesos de 16 bits)
└── decodificador genérico -> fetch_2d_texel_rgba_dxt5 -> TRUNCAMIENTO == bcdec
```

**Consecuencia operativa para el test de Fase 3**: la categoría `only_trunc` **ya no significa
«el hardware trunca»**. Significa «el resultado coincide con un truncamiento», y hay al menos dos
orígenes posibles: el hardware, o un decodificador software de Mesa. Con la clasificación actual
un resultado `trunc` uniforme se reportaría como `AD-12` → truncamiento, sin poder separar esas
dos causas.

**No lo corrijo aquí**: el test es de IA-2 y el cambio necesita un predictor más. Lo dejo
registrado como requisito, con la evidencia que lo motiva.

**Lo que NO cambia**: las 649 siguen siendo discriminantes (F-5). Las tres respuestas siguen siendo
distintas, y el corpus no queda invalidado.

## 4. Qué quedó demostrado y qué no

### Demostrado

| | |
|---|---|
| D-1 | El decodificador BC3 genérico de Mesa **trunca**, y es bit a bit igual a `bcdec`. Ejecutado, 0/1 048 576 |
| D-2 | Mi modelo de `lp_build_lerpdxta` **no** describe ese decodificador (17.036 % de desacuerdo), como corresponde a funciones distintas |
| D-3 | El corpus de 649 mantiene tres respuestas distintas frente a una implementación real (F-5) |
| D-4 | El contraste usado tiene poder de discernimiento (C-1, C-2) |

### No demostrado

| | |
|---|---|
| N-1 | **Si mi modelo predice lo que devuelve llvmpipe real.** `NOT_DETERMINED`: no obtuve la observación |
| N-2 | Si `lp_build_lerpdxta` es la ruta efectiva de llvmpipe para BC3 en esta versión de Mesa. Ya era `NOT_DETERMINED` en `006` §5; sigue |
| N-3 | La respuesta de `AD-12`. Sin cambio: `NOT_DETERMINED` |
| N-4 | Si `radeonsi`/`RADV` descomprimen BC3 en CPU. `Q-3` sigue `FAIL` por método y **no se ha reabierto** |
| N-5 | Si el fallo de Vulkan es de lavapipe o del harness |

### Sobre el modelo Python del oracle

**No sobrevive sin cambios ni queda invalidado**: queda **acotado**. Sobrevive entero en el
alcance `fetch_2d_texel_rgba_dxt5` (coincide con trunc, o sea que ahí el modelo de llvmpipe se
comporta como trunc en un 83 % de los casos — pero no es el modelo de esa función). Y **sigue sin
validar** en el alcance para el que fue escrito.

**Sobre los `expect_llvmpipe` del corpus (`5c02833`)**: no se tocan. Siguen siendo la predicción
correcta de `lp_build_lerpdxta`, que es lo que dicen ser, y `F-5` confirma que el corpus discrimina
contra una implementación real. Ajustarlos a lo observado sería exactamente lo que el
pre-registro §7 prohíbe.

## 5. La vía que cerraría `Q-5`

En orden de coste:

| # | Vía | Coste | Notas |
|---|---|---|---|
| 1 | **OpenGL con `LIBGL_ALWAYS_SOFTWARE=1`** (llvmpipe por GL, no lavapipe) | medio | ruta distinta al JIT de lavapipe. `/usr/include/GL` no existe (medido), así que hay que declarar la API a mano, como hace `test_hardware_bc3.c`. Es la más promising |
| 2 | Arreglar el harness de Vulkan hasta que el render pass dé salida | medio | no sé si el fallo es mío |
| 3 | Compilar `lp_bld_format_s3tc.c` y ejecutar su salida | alto | es un constructor de IR de LLVM, no una función C. No es un test de C |
| 4 | Compilar Mesa desde fuente y usar su `vkcube`/`glxgears` con un test propio | alto | requiere toolchain y es `IA-1` |

La vía 1 es la que propongo. **Ninguna de las cuatro la hago sin autorización**: las tres últimas
exigen trabajo de otra IA, y la primera requiere el harness GL que es código de prueba.

## 6. Peticiones

| # | Para | Petición |
|---|---|---|
| `Q-6` | `@IA-1` | Vía 4 o 3: el fallo es de lavapipe o del harness, y eso decide si la vía 2 sirve |
| `Q-7` | `@IA-2` | Al escribir el test de Fase 3: `only_trunc` uniforme **no** basta para afirmar truncamiento en hardware. Hace falta separar «hardware» de «decodificador genérico de Mesa», que son idénticos. Requisito en §3 |
| `Q-5` | — | **sigue abierta**. Petición reabierta, no cerrada |

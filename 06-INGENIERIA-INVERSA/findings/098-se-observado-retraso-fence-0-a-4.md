# 098 · §E OBSERVADO: el retraso del fence va de 0 a 4, y leer debugfs NO es un observador pasivo

```
CLASSIFICATION=DOCUMENTATION · TRACK=RUNTIME (READ_ONLY)
CORPUS=RESEARCH/working/linux-7.1.3 · HARDWARE_SCOPE=HOST-C/RX550/0000:01:00.0
WORK_CLASS=READ_ONLY/EVIDENCE · WRITE_EXECUTION=NONE · MODIFICATIONS=0
RUNTIME=OBSERVED_READ_ONLY · GPU INTACTA · sesión sway INTACTA
```

## Qué resuelve

`097` dejó un discriminante identificado: *leer la página de fence y comprobar si
contiene el valor del EOP real o el del dummy*. Y dejó escrito que la página está
en RAM del sistema y es legible sin TLB.

**El observable existe** (`amdgpu_fence_info`), pero no hace lo que yo suponía.
Ni en un sentido ni en el otro.

## El observable y su semántica exacta

```
amdgpu_fence.c:876   amdgpu_fence_process(ring);
amdgpu_fence.c:879   Last signaled fence  = atomic_read(&ring->fence_drv.last_seq)
amdgpu_fence.c:881   Last emitted         = ring->fence_drv.sync_seq
amdgpu_fence.c:886   Last signaled trailing fence = le32_to_cpu(*ring->trail_fence_cpu_addr)
amdgpu_fence.c:888   Last emitted (trailing)        = ring->trail_seq
amdgpu_fence.c:896   Last preempted = le32_to_cpu(*(ring->fence_drv.cpu_addr + 2))
amdgpu_fence.c:899   Last reset     = le32_to_cpu(*(ring->fence_drv.cpu_addr + 4))
amdgpu_fence.c:902   Last both      = le32_to_cpu(*(ring->fence_drv.cpu_addr + 6))
```

**`signaled` es el `last_seq` del driver, no una lectura directa de la página.**
Y `emitted` es `sync_seq`, lo último que el driver escribió en el anillo.

Eso significa que `emitted - signaled` **no es "cuánto le falta a la GPU"**,
sino "cuántos fences emitidos el driver aún no ha|Exigido|". El `amdgpu_fence_process`
de L876 se ejecuta **antes** de imprimir, y es él quien actualiza `last_seq`
(`amdgpu_fence.c:213-217`).

## Y por eso leer debugfs NO es pasivo

**`L876` llama a `amdgpu_fence_process(ring)`. Cada lectura del fichero ejecuta el
procesador de fences.**

Eso significa que mi muestreo no fue observación pasiva: fueron **758.647 llamadas
a `amdgpu_fence_process` en 20 segundos**, cada una leyendo la página de fence y
señalando `dma_fence`s pendientes.

**Lo declaro antes que nada, porque es lo primero que hay que declarar:**
`amdgpu_fence_info` es un observable **con efecto secundario**, no una lectura
pura. No escribe en la GPU, no toca la TLB, no modifica la cola — sólo lee
memoria y hace lo que la IRQ haría. **NIVEL 2 respecto al hardware**, pero con
efecto sobre el estado del kernel que un observador normal no tiene.

**Y es una trampa para cualquiera que lo use como discriminante.** Si alguien
mide "cuánto tarda la GPU en señalizar" leyendo este fichero, está midiéndose a
sí mismo.

## La medición

20 segundos, leyendo en bucle cerrado, con el parser correcto (el primero usaba
`awk` con escapes rotos dentro de `sudo` y devolvió campos vacíos).

```
muestras              : 758.647
retraso = emitted - signaled
  +0  ->  748.754 muestras  (98.70%)
  +1  ->    8.650 muestras
  +2  ->    1.156 muestras
  +3  ->       86 muestras
  +4  ->        1 muestra
RETRASO MAXIMO observado: 4
```

El contador avanzó 2.753 durante la ventana (0xe42f3 → 0xe4db4), así que el
sistema estaba **activo**, no en reposo.

## Y aquí corrijo mi propia hipótesis, que era falsa

En el informe anterior dije, basándome en los 12 primeros retrasos,
que *"la diferencia es exactamente 1, que es el valor del dummy"*. **Los 12
primeros sí eran todos 1. La distribución completa llega hasta 4.**

Un retraso de hasta 4 es **retraso asíncrono normal**, no la firma del dummy.
Cualquier mecanismo de fence que no sea síncrono lo tiene.

**Y eso significa que esta medición NO discrimina la hipótesis del dummy.** Si no
hubiera dummy, el retraso sería también de 0 a N. El discriminante que `097`
propuso **no funciona**, y no por un fallo de ejecución sino porque la pregunta
está mal planteada: *un retraso observable no puede distinguir dos causas que
producen el mismo síntoma.*

Lo digo claro porque el error fue mío y es del tipo que más caro sale: **anuncié
un discriminante sin comprobar antes si discriminaba.**

## Lo que sí queda, y es útil

| propiedad | estado |
|---|---|
| El retraso llega como mucho a 4 | `OBSERVED` (758.647 muestras) |
| 98,70 % de las veces es exactamente 0 | `OBSERVED` |
| Los 18 rings viven en lockstep | `OBSERVED` |
| El host nunca se queda sin progreso | `OBSERVED` |
| Si el dummy es visible desde fuera | `NOT_DETERMINED` — y esta vía no lo decide |
| Por qué existe el dummy | `NOT_DETERMINED` |

**La primera fila es la que importa para un driver propio.** Un retraso máximo de
4 sobre 758.647 muestras significa que el host drena el ring de fences mucho más
rápido de lo que la GPU lo llena. Eso tiene una consecuencia aritmética directa:

```
amdgpu_fence.c:461   num_fences_mask = num_hw_submission * 2 - 1
```

El ring de fences tiene `2 × num_hw_submission` ranuras. Si el retraso máximo
observado es 4, **`num_hw_submission` no necesita ser grande para que el host
no pierda fences en esta carga.** Un driver propio puede elegir un valor
pequeño y no se va a quedar atrás bajo esta carga.

**Y el margen es enorme**: para que el host perdiera el hilo haría falta un
retraso de `2 × num_hw_submission`, y el observado es 4. Eso es un factor de al
menos 10 en la carga medida, y probablemente mucho más en la real.

## Un bonus del mismo volcado: la página de fence tiene ranuras

```
cpu_addr + 0   ->  la secuencia
cpu_addr + 2   ->  "Last preempted"   (CP_VMID_PREEMPT)
cpu_addr + 4   ->  "Last reset"       (CP_VMID_RESET)
cpu_addr + 6   ->  "Last both"
```

Cuatro dwords, en los desplazamientos 0, 2, 4 y 6 — **no 0, 1, 2, 3**. El hueco
es deliberado: son ranuras de 8 bytes, y eso las alinea a 32 bytes.

**Los tres valores de preemption/reset son 0 en el ring gfx.** Es decir:
**no ha habido ni una preemption ni un reset de VMID en esta GPU desde el
arranque.** Eso es una observación sobre el historial real de la máquina, y
explica por qué `Last preempted`, `Last reset` y `Last both` no aparecían con
valores en el volcado de `097`.

**Y explica por qué el track de ejecución de `095` no se ha movido nunca**: si
nunca hubo preemption, PFP y ME nunca se han parado en caliente, sólo al
arrancar y en el soft reset que registró `095`.

## Procedencia

- `RUNTIME` — `/sys/kernel/debug/dri/0000:01:00.0/amdgpu_fence_info`, 758.647
  lecturas en 20 s. **Sólo lectura**, sin MMIO write, sin TLB, sin módulos.
- `STATIC` — `amdgpu_fence.c:79-90` y `:211-248` y `:443-470` y `:865-905`,
  `amdgpu_ring.h:116-131`, `amdgpu_device.c:1028-1085`.
- **CONFOUNDER DECLARADO**: el observable ejecuta `amdgpu_fence_process` en cada
  lectura (L876). Sin efecto en el hardware; con efecto en el estado del kernel.
  **La medición del propio retraso está sesgada por el instrumento**, y por eso
  el retraso observado es una cota inferior del retraso real.
- Encadenada con `097` (el ring vivo), `096` (el mecanismo de fence),
  `094` (los 3 FENCE del frame), `095` (PFP/ME, y por qué no se movieron).
- No se editó `AGENTS.md` ni `OPEN-FRONTIERS.md`: son de otras sesiones.

**Dos notas de método, y las dos son la misma lección.**

La primera: **anuncié un discriminante sin comprobar si discriminaba.** Dije que
leer la página de fence decidiría si el dummy es visible. No lo decide, porque
un retraso asíncrono tiene la misma firma con y sin dummy. El error no fue de
ejecución: fue de diseño del experimento, que es peor porque no lo detecta
ninguna comprobación posterior de resultados — los resultados eran correctos y
la pregunta estaba mal.

La segunda: **miré los 12 primeros resultados y vi lo que quería ver.** Todos
eran 1. Publico la distribución completa (0 a 4) y retiro la conclusión. Si
hubiera publicado la primeraitura, habría escrito *"el retraso es exactamente 1,
que es la firma del dummy"*, que es un Finding plausible, elegante, y falso.

**Eso es lo que hace un recorte cómodo: convierte ruido en señal.** La
distribución entera fue la que dio el dato útil — que el máximo es 4.
# 101 · CORPUS: el hueco TTM se cierra a medias, y probablemente no merece la descarga

```
CLASSIFICATION=DOCUMENTATION · TRACK=STATIC
CORPUS=RESEARCH/working/linux-7.1.3 (drivers/gpu/drm/amd/ únicamente)
CORPUS SECUNDARIO: /usr/src/kernels/7.1.3-200.nobara.fc44.x86_64
HARDWARE_SCOPE=HOST-C/RX550/0000:01:00.0
WORK_CLASS=READ_ONLY/EVIDENCE · WRITE_EXECUTION=NONE · MODIFICATIONS=0
RUNTIME=NOT_RUN · GPU INTACTA
```

## Qué resuelve

`100` declaró un hueco: el corpus es sólo `drivers/gpu/drm/amd/`, las capas TTM
y DRM core no están, y por eso tres campos de `amdgpu_gtt_mm` quedaron
`NOT_IN_CORPUS`.

Esta nota **(a) recupera dos de los tres** con una fuente que ya estaba en la
máquina, y **(b) evalúa si merece la pena cerrar del todo** — porque la respuesta
es probablemente que no, y eso es más útil que la descarga.

## Lo que ya había en la máquina

```
/usr/src/kernels/7.1.3-200.nobora.fc44.x86_64/
    include/drm/            158 cabeceras, el juego completo de DRM
    drivers/gpu/drm/ttm/    SOLO Makefile y tests/  — ningún .c
    drivers/gpu/drm/amd/amdgpu/   SOLO Kconfig y Makefile
    drivers/gpu/drm/amd/include/  VACÍO — ni asic_reg
```

Procedencia confirmada por rpm:

```
$ rpm -qf /usr/src/kernels/.../include/drm/ttm/ttm_resource.h
kernel-devel-7.1.3-200.nobara.fc44.x86_64
```

**Es `kernel-devel`, un paquete de cabeceras. No trae una sola implementación.**

## Recuperado: `use_type` y `use_tt` son campos de la struct, no magnitudes

> **Este bloque es EXTERNO al corpus de investigación, por diseño.**
> La ruta real es
> `/usr/src/kernels/7.1.3-200.nobara.fc44.x86_64/include/drm/ttm/ttm_resource.h`,
> del paquete `kernel-devel-7.1.3-200.nobara.fc44.x86_64`.
> **`citecheck` no puede resolverlo**: indexa contra
> `RESEARCH/working/linux-7.1.3/`, donde `include/drm/` no existe. Con la ruta
> completa, además, la herramienta **falla con `KeyError`**. Los números de
> línea van aquí como referencia de lectura, no como cita resoluble — y eso es
> parte del hallazgo, no una convenientía.

```
   199   struct ttm_resource_manager {
   200       /*
   201        * No protection. Constant from start.
   202        */
   203       bool use_type;
   204       bool use_tt;
   205       struct ttm_device *bdev;
   206       uint64_t size;
   207       const struct ttm_resource_manager_func *func;
```

**Las dos primeras líneas del dump de `amdgpu_gtt_mm` son los dos primeros
campos de la struct, volcados en crudo.** No son magnitudes derivadas ni
resultados de ningún cálculo: son `bool` leídos directamente.

Y `size` —el que `amdgpu_gtt_mgr.c:54` imprime— es el **quinto campo**, un
`uint64_t` pelado, sin comentario que lo documente.

**Los tres pasan de `NOT_IN_CORPUS` a `PROVEN`.** Eso es el cierre parcial.

## Lo que NO se puede recuperar

| lo que `100` dejó abierto | estado tras esta nota |
|---|---|
| Qué es `use_type: 1` | **`PROVEN`** — campo `bool` de la struct |
| Qué es `use_tt: 1` | **`PROVEN`** — campo `bool` de la struct |
| Qué es `size` | **`PROVEN`** — `uint64_t size`, 5º campo, sin documentar |
| Por qué `usage` no cuadra con la suma de "used" | `NOT_IN_CORPUS` — necesita el `.c` |
| Semántica de `total: 65536` | `PARTIAL` — el número vale por dos vías, el `.c` no está |

El cuarto sigue necesitando implementación, y `kernel-devel` no la trae.

## Y la pregunta que de verdad importa: ¿merece la pena la descarga?

Antes de recomendar descargar ~150 MB de `kernel-source`, evalué qué me daría.

**Mi primer impulso fue decir que no importa**, porque TTM es el gestor de
memoria de amdgpu y un driver propio no lo usaría. **Y al verificarlo resulta
que es medio verdad, no verdad entera:**

```
amdgpu_gart.c:202   ret = amdgpu_ttm_alloc_gart(&adev->gart.bo->tbo);
```

**TTM sí participa**: el BO que respalda la tabla GART se **asigna** a través de
TTM. Mi argumento de "no lo usaría" era demasiado cómodo.

**La posición correcta es más estrecha y sí se sostiene:**

| capa | ¿en mi corpus? | ¿la necesita un driver propio? |
|---|---|---|
| **Formato de la page table y los registros** | **sí** — `amdgpu_vm.c`, `amdgpu_vm_pt.c`, `gmc_v8_0.c` | **sí**, es el hardware |
| **Escritura de la tabla GART** | **sí** — `amdgpu_gart.c` | **sí**, es el hardware |
| **Asignación de qué páginas respaldan el BO** | no — TTM | **parcialmente**: hay que elegir, no copiar |
| Política de expulsión y colocación | no — TTM | **no**: es decisión propia |

**El hardware-facing está dentro. Lo que falta es bookkeeping de amdgpu.**

Y la prueba de que el hueco ya no muerde: **el número central de `100` está
confirmado por dos vías independientes sin TTM.** `65536 × 4096 = 256 MiB` desde
el observable, y `256ULL << 20` desde `gmc_v8_0.c:595`. Ninguna de las dos pasa
por la capa que me falta.

**Mi recomendación: no descargar.** El coste son ~150 MB y una descarga larga, y
la ganancia son detalles de *política de asignación* de un gestor que un driver
propio va a sustituir por el suyo. Es `INFORMATION_GAIN` bajo a coste alto.

**Lo dejo como decisión tuya**, no la ejecuto sin que la pidas: es una descarga,
no una lectura, y `AGENTS.md` manda no gastar recursos sin valor demostrado.

## Procedencia, que es lo que hay que declarar aquí

**No he fusionado nada.** Son dos fuentes distintas y las mantengo separadas:

| | corpus de investigación | paquete del sistema |
|---|---|---|
| ruta | `RESEARCH/working/linux-7.1.3/` | `/usr/src/kernels/7.1.3-.../` |
| contenido | `.c` de amdgpu + `asic_reg` | sólo `include/drm/**` |
| versión | linux-7.1.3 | 7.1.3-200.nobara.fc44.x86_64 |

**La versión upstream coincide (7.1.3), pero el empaquetado es otro**, y eso
importa: `asic_reg` no está en el paquete, así que **para citar registros
sigue mandando el corpus de investigación**. `include/drm` sólo aporta
definiciones de tipo que el corpus no tiene.

**Verificado que no hay solape**: cero cabeceras del corpus existen en la misma
ruta dentro de `/usr/src/kernels`. No se pisan.

## Lo que NO cierra

| Afirmación | Estado |
|---|---|
| `use_type`/`use_tt` son los 2 primeros campos de la struct | `PROVEN` (struct, bloque citado arriba) |
| `size` es el 5º campo, `uint64_t`, sin documentar | `PROVEN` (struct, bloque citado arriba) |
| `kernel-devel` no trae ninguna implementación | `OBSERVED` (0 `.c`) |
| TTM asigna el BO del GART | `PROVEN` (`amdgpu_gart.c:202`) |
| El hardware-facing del GART está en mi corpus | `PROVEN_DERIVED` |
| Por qué `usage` no cuadra con la suma de bloques | `NOT_IN_CORPUS` |
| Política de colocación de TTM | `NOT_IN_CORPUS` |

## Procedencia

- `STATIC` — el bloque `ttm_resource.h` citado arriba, del paquete
  `kernel-devel-7.1.3-200.nobara.fc44.x86_64`; `amdgpu_gart.c:199-237` y
  `amdgpu_gtt_mgr.c:45-78` del corpus de investigación.
- Sin `RUNTIME`. Sin escrituras. Sin descargas.
- Actualiza `100` (tres `NOT_IN_CORPUS` → `PROVEN`, uno se queda).
- No se editó `AGENTS.md` ni `OPEN-FRONTIERS.md`: son de otras sesiones.

**Dos notas de método.**

La primera: **"no existe" por un comando roto no es una ausencia.** Busqué
`amdgpu_gart.c` con un `ls | sed` cuyo `sed` tenía la expresión rota, y el
`|| echo "no existe"` de mi comando capturó el fallo del `sed`. **El fichero
estaba ahí.** Es la décima vez que un comando mal construido me da un
`NAME_NOT_FOUND` falso, y la más peligrosa porque el mensaje que produzco dice
justo lo contrario de la verdad.

La segunda, y es la que quiero dejar escrita: **iba a recomendar no descargar,
con un argumento que sonaba bien y era falso a medias.** Dije "un driver propio no
usa TTM", y `amdgpu_gart.c:202` dice que el BO del GART se asigna por TTM.
Lo comprobé antes de escribir y lo corregí. **Un argumento elegante que no he
verificado es peor que no tener argumento**, porque se publica igual y suena
igual de convincente.
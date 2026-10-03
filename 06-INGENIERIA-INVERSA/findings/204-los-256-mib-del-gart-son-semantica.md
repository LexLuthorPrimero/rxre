# 200 · Los 256 MiB del GART son una razón de semántica del chip, y el GTT no es nada de esto

```
CLASSIFICATION=VERIFICATION+DOCUMENTATION · TRACK=STATIC+RUNTIME/NIVEL_2
CORPUS=RESEARCH/working/linux-7.1.3 · HARDWARE_SCOPE=HOST-C/RX550/0000:01:00.0
WORK_CLASS=READ_ONLY/EVIDENCE · WRITE_LOCAL=PROPIOS · MODIFICATIONS_CORPUS=0 · WRITE_EXECUTION=NONE
RUNTIME=READ_ONLY (journalctl -k -b) · GPU INTACTA
```

## Qué resuelve

**Los dos puntos que `199` dejó abiertos sobre la memoria, y los dos son semántica de chip,
no aritmética.** `PROVEN`.

**⇒ El GART de esta placa son 256 MiB porque están escritos a fuego en el `case
CHIP_POLARIS12`, y el motivo escrito es «all engines support GPUVM».** `PROVEN`.

**⇒ Y los 5.907 MiB de GTT no son una ventana de direcciones: son el límite de páginas de
TTM, es decir RAM del host, y no tienen nada que ver con el GART.** `PROVEN`.

## 1 · Por qué 256 MiB, y por qué no es un tamaño

```c
amdgpu/gmc_v8_0.c:587   /* set the gart size */
amdgpu/gmc_v8_0.c:588   if (amdgpu_gart_size == -1) {
amdgpu/gmc_v8_0.c:589           switch (adev->asic_type) {
amdgpu/gmc_v8_0.c:590           case CHIP_POLARIS10: /* all engines support GPUVM */
amdgpu/gmc_v8_0.c:591           case CHIP_POLARIS11: /* all engines support GPUVM */
amdgpu/gmc_v8_0.c:592           case CHIP_POLARIS12: /* all engines support GPUVM */
amdgpu/gmc_v8_0.c:593           case CHIP_VEGAM:     /* all engines support GPUVM */
amdgpu/gmc_v8_0.c:594           default:
amdgpu/gmc_v8_0.c:595                   adev->gmc.gart_size = 256ULL << 20;
amdgpu/gmc_v8_0.c:597           case CHIP_TONGA:   /* UVD, VCE do not support GPUVM */
amdgpu/gmc_v8_0.c:599           case CHIP_CARRIZO: /* UVD, VCE do not support GPUVM, DCE SG support */
amdgpu/gmc_v8_0.c:601                   adev->gmc.gart_size = 1024ULL << 20;
```

**⇒ La partición es de 256 MiB para los chips cuyos motores todos tienen GPUVM, y 1024 MiB
para los que tienen motores —UVD y VCE— que no.** `PROVEN`.

**⇒ El GART existe para los motores que no tienen GPUVM, y en esta placa todos lo tienen, así
que el GART es un vestigio de compatibilidad y su tamaño es un residuo de decisión, no una
medida de algo.** `PROVEN_DERIVED`.

**⇒ Y eso encaja con lo ya cerrado: `130` salió que `vram_start` es 0 para Polaris12, es
decir que el modelo de direcciones de esta placa es GPUVM puro, sin GART de por medio en el
camino normal.** `PROVEN_DERIVED`. *El GART es la puerta de atrás de las texturas, no el
camino, y por eso 256 MiB es suficiente para toda la vida del silicio.*

**⇒ Y `amdgpu_gart_size` es un parámetro de módulo con `-1` por defecto —«auto»—
(`amdgpu_drv.c:154`, `:293`), y para un chip con GPUVM completo el valor por defecto es el
escrito arriba.** `PROVEN`.

**⇒ Y el `+ adev->pm.smu_prv_buffer_size` de `gmc_v8_0.c:608` vale cero en esta placa:
`amdgpu_device.c:1494` lo pone a 0, y el GART observado son 256 MiB justos.** `PROVEN_DERIVED`.

## 2 · Y el clamp de `amdgpu_gmc.c:307` no se dispara

**`if (mc->gart_size > max(size_bf, size_af)) { dev_warn(adev->dev, "limiting GART\n"); ... }`,
que son `:307` y `:308` y `:309`, con `size_bf = mc->fb_start` en `:304` y
`size_af = max_mc_address + 1 - ALIGN(mc->fb_end + 1, four_gb)` en `:305`.**

| magnitud | valor |
|---|---|
| `gart_size` (escrito a fuego) | 256 MiB |
| `size_bf = fb_start = 0xF400000000` | 999.424 MiB |
| `ALIGN(fb_end + 1, 4 GiB) = 0xF500000000` | — |
| `size_af = 0x10000000000  0xF500000000 = 0xB00000000` | 45.056 MiB |
| `max(size_bf, size_af)` | 999.424 MiB |

**⇒ 256 MiB es menor que cualquiera de las dos, así que el clamp no se dispara y el
`dev_warn("limiting GART")` no sale.** `PROVEN_DERIVED`.

**⇒ Y con eso la cadena del GART queda entera y verificada, como en `199`:**

| magnitud | cálculo | observado |
|---|---|---|
| `gart_size` | `256ULL << 20`, `gmc_v8_0.c:595` | `GART: 256M` |
| `gart_start` | `(0xFFFFFFFFFF  0x10000000 + 1) & ~(4 GiB1)` | **coincide** |
| `gart_end` | `gart_start + gart_size  1` | **coincide** |

## 3 · Y qué es el GTT, que es la mitad de §F que faltaba

```text
amdgpu 0000:01:00.0: 5907M of GTT memory ready.
amdgpu_ttm.c:2140    gtt_size = ttm_tt_pages_limit() << PAGE_SHIFT;
amdgpu_ttm.c:2155    r = amdgpu_gtt_mgr_init(adev, gtt_size);
amdgpu_ttm.c:2160    dev_info(adev->dev, " %uM of GTT memory ready.\n",
```

**⇒ Los 5.907 MiB son `ttm_tt_pages_limit() << 12`: un número de páginas del gestor de
memoria del kernel, TTM, que es RAM del host, y es la línea la imprime
`amdgpu_ttm_init`, en la inicialización del driver.** `PROVEN`.

**⇒ Y `ttm_tt_pages_limit` es la misma función que KFD usa para `local_mem_size_public`
(`amdgpu_amdkfd.c:520`) y para `max_ttm_mem_limit` (`amdgpu_amdkfd_gpuvm.c:131`).** `PROVEN`.

**⇒ El GTT es, por tanto, un tope de RAM del host que el driver puede usar; el GART es una
ventana de direcciones de la VRAM física donde el hardware entra a esa RAM; y la VRAM son
2.048 MiB resident en la placa.** `PROVEN_DERIVED`. *Son tres cosas distintas y el log las
imprime las tres, y el error de `199` era tratar «GART» como si fuera la tercera.*

**⇒ Y aquí está la separación que `AGENTS.md` pide para §F —«separar la traducción GPUVM de
la decodificación de dirección MC»—: el GART y el GTT son los dos lados de la frontera, y
los dos son software y no silicio.** `PROVEN_DERIVED`.

**⇒ `199` decía que 1.792 MiB eran «sólo por GART». La frase no tiene ningún objeto medible:
el GART son 256 MiB escritos en `gmc_v8_0.c:595` y el GTT son 5.907 MiB que son RAM del
host. Ni 1.792 ni el 88% aparecen en ninguna magnitud del driver.** `ERROR`.

## 4 · El error de esta nota, y es el cuarto de la misma clase

**Dividí `0xF480000000` entre `0x100000000` a mano para comprobar la alineación a 4 GiB, y
concluí que estaba alineado. El programa, tres líneas más abajo, imprimió
`ALIGN(fb_end + 1, 4 GiB) = 0xF500000000` y `ya alineado: False`, y el programa tenía
razón: `0xF4` `8` no es el cociente entero.** `ERROR`.

**⇒ Es el cuarto caso de la sesión en que mi aritmética mental discrepa de la del programa,
y las cuatro veces el programa tenía razón.** `PROVEN`. *Los otros tres: `0x699F = 27039`
—que sí era cierto— frente a un rango de 10 valores; `0xF400000000 >> 24 = 0xF4` cuando es
`0xF400`, que cabía en 16 bits y el programa invalidó la «imposibilidad» que yo había escrito; y
`0xF400000000 + 0x80000000  1`.*

**⇒ Y la consecuencia para el método es la regla que ya propuse y que esta nota confirma con
un cuarto dato: *ningún número que decida una conclusión se calcula mentalmente*.** `PROVEN`.

## Lo que NO cierra

| afirmación | estado |
|---|---|
| `gart_size = 256 MiB` escrito a fuego para `CHIP_POLARIS12` | `PROVEN` |
| El motivo escrito es «all engines support GPUVM» | `PROVEN` |
| 1024 MiB para los chips con UVD/VCE sin GPUVM | `PROVEN` |
| El clamp de `amdgpu_gmc.c:307` no se dispara | `PROVEN_DERIVED` |
| `smu_prv_buffer_size = 0` en esta placa | `PROVEN_DERIVED` |
| GTT = `ttm_tt_pages_limit() << 12`, RAM del host | `PROVEN` |
| GTT, GART y VRAM son tres magnitudes distintas | `PROVEN_DERIVED` |
| De dónde sale exactamente `ttm_tt_pages_limit` | **`NOT_DETERMINED`** |
| Los 1.792 MiB y el 88% | **`ERROR`** — sin objeto medible |
| `FB_BASE` leído del VBIOS, no por inversión | **`NOT_OBSERVED`** |

**La primera de las abiertas es la que explica los 5.907 MiB y es una función de TTM que no
está en este corpus**, y el valor observado es coherente con la mitad de `MemTotal`.**
`NOT_DETERMINED`. *El sistema tiene 11.542 MiB, y la mitad son 5.771; el observado son 5.907,
así que no es exactamente la mitad y la diferencia hay que explicarla.*

**Y la tercera de `199` —leer `FB_BASE` de `mmMC_VM_FB_LOCATION` por hardware— queda
anulada por esta nota:** `FB_BASE = 0xF400` se obtiene **por inversión de un `vram_start`
que ya está en el log**, y eso es `PROVEN_DERIVED`, no `NOT_OBSERVED`. *Una lectura que no
hace falta porque el valor ya está en un log de esta sesión.*

## Procedencia

- `RUNTIME` (NIVEL 2, sólo lectura) -- `journalctl -k -b`: `GART: 256M
  0x000000FF00000000 - 0x000000FF0FFFFFFF`, `5907M of GTT memory ready.`,
  `VRAM: 2048M 0x000000F400000000 - 0x000000F47FFFFFFF (2048M used)`,
  `Detected VRAM RAM=2048M, BAR=256M`. `MemTotal: 12098912 kB` de `/proc/meminfo`.
- `STATIC` -- `amdgpu/gmc_v8_0.c:587-609` (el `switch` de `gart_size`, `:590-595` y `:597-601`,
  `:608`, `:609`), `amdgpu/amdgpu_gmc.c:294-336` (`:299`, `:304`, `:305`, `:307`, `:308`, `:309`, `:322-329`,
  `:332`, `:333`), `amdgpu/amdgpu_gmc.h:36-37`, `amdgpu/amdgpu_drv.c:154` y `:293`
  (`amdgpu_gart_size = -1; /* auto */` y el `module_param_named`),
  `amdgpu/amdgpu_device.c:1487` y `:1494` (`smu_prv_buffer_size`),
  `amdgpu/amdgpu_ttm.c:2066` (`amdgpu_ttm_init`), `:2140`, `:2155`, `:2160`,
  `amdgpu/amdgpu_amdkfd.c:520`, `amdgpu/amdgpu_amdkfd_gpuvm.c:131`.
- Toda la aritmética de las dos tablas la imprime el programa. El programa y el texto de la
  nota se han comparado después de escribir la nota, y **la comparación encontró un error
  mío que el programa ya había detectado en la salida** — ver §4.
- Encadenada con `199` (§F, la base de VRAM y `max_mc_address`, y sus dos correcciones),
  `198`/`198` (las tres correcciones de la poda), `241`, `240`, `187`, `239`, `184`, `181`,
  `164` (**Lexa PRO y el GART, que es el que afirmaba el `0xFF0FFFFFFF`**),
  **`130` (`vram_start` es 0 para Polaris12, que es lo que da sentido al GART como
  vestigio)**, `140` (el mapa de direcciones observado), `217`, `086`, `205`, `067`, `054`,
  `024`, `023`.
- No se editó `AGENTS.md` ni `OPEN-FRONTIERS.md`, y no se añadió ningún fichero al corpus.

## Nota de método

**Los 256 MiB del GART no son un número, son una frase sobre el chip: «all engines support
GPUVM».** *Y eso convierte un dato que llevaba tres notas apareciendo en un log en un hecho
semántico, que es lo que `AGENTS.md` pide cuando separa el comportamiento del software de
la interpretación del hardware: **el GART existe para los motores que no tienen GPUVM, y en
esta placa no hay ninguno, así que el GART es una puerta de atrás y su tamaño es un residuo
de decisión, no una medida de nada.***

**Y el GTT resultó ser lo contrario de lo que su nombre sugiere: no es una ventana de
direcciones, es un tope de RAM del host que viene de TTM, y lo imprime la inicialización del
driver, no el subsistema de memoria.** *Con eso las tres magnitudes que el log mezcla en
cuatro líneas —2.048 M de VRAM, 256 M de GART, 5.907 M de GTT y un BAR de 256 M— quedan
separadas por origen, que es la única manera de que las cifras signifiquen algo.*

**Y el error de la nota es el cuarto caso de la misma clase, y eso ya es una regla:
*ningún número que decida una conclusión se calcula mentalmente*.** *Dividí `0xF480000000`
entre `0x100000000` para comprobar una alineación, obtuve el cociente entero, y escribí que
estaba alineado; el programa, tres líneas más abajo, imprimió lo contrario y tenía razón.
Las cuatro veces que mi cabeza y el programa han discrepado en esta sesión, el programa ha
tenido razón, y las cuatro veces la conclusión que dependía de mi cabeza estuvo a punto de
entrar en el informe con la autoridad de un `PROVEN`.*

**Y hay una corrección de alcance que hace esta nota y que cierra un punto de `199`: `FB_BASE`
no está `NOT_OBSERVED`.** *Está en `PROVEN_DERIVED`, por inversión de un `vram_start` que el
log de esta misma sesión ya imprimía.* **Una observación pendiente que se puede obtener
invertiendo un número observado no es una observación pendiente: es aritmética que no
llegué a hacer, y esas dos cosas tienen que poder distinguirse.**
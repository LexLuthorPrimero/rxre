# 142 · §F: la apertura AGP está vacía, y hay 160 registros HDP sin nombre

```
CLASSIFICATION=DOCUMENTATION · TRACK=STATIC+RUNTIME-OBSERVE
CORPUS=RESEARCH/working/linux-7.1.3 · HARDWARE_SCOPE=HOST-C/RX550/0000:01:00.0
WORK_CLASS=READ_ONLY/EVIDENCE · WRITE_EXECUTION=NONE · MODIFICATIONS=0
RUNTIME=READ_ONLY · GPU INTACTA
```

## Qué resuelve

Dos cosas, y las dos salen de un solo bloque de código de trece líneas que `140`
dejó a la vista:

1. **La apertura AGP de esta GPU está vacía**, y eso cierra la frontera §F de
   *"resolver GPUVA → GPU physical → MC → GDDR5"* con una afirmación estructural:
   **no hay un tercer camino sin traducir.**
2. **Un bloque de 160 escrituras de registro sin un solo nombre**, con la causa
   identificada: **el corpus no tiene el header que los nombraría.**

## 1 · La apertura AGP está vacía, por tres pruebas independientes

### Prueba 1 — por fichero

`amdgpu_gmc_agp_location` es la única función que **imprime** la apertura:

```c
dev_info(adev->dev, "AGP: %lluM 0x%016llX - 0x%016llX\n", ...)   /* amdgpu_gmc.c:374 */
```

Y sus únicos llamadores son:

```
gmc_v9_0.c:1669    gmc_v10_0.c:664    gmc_v11_0.c:665    gmc_v12_0.c:706
```

**`gmc_v8_0.c` no está.** `PROVEN_ABSENT`, por pertenencia a fichero.

### Prueba 2 — por su sustituto

```c
gmc_v8_0.c:420   amdgpu_gmc_set_agp_default(adev, mc);
```

```c
amdgpu_gmc.c:389  void amdgpu_gmc_set_agp_default(struct amdgpu_device *adev,
amdgpu_gmc.c:390                                struct amdgpu_gmc *mc)
amdgpu_gmc.c:391  {
amdgpu_gmc.c:392          mc->agp_start = 0xffffffffffff;
amdgpu_gmc.c:393          mc->agp_end   = 0;
amdgpu_gmc.c:394          mc->agp_size  = 0;
amdgpu_gmc.c:395  }
```

**Tres asignaciones y ningún `dev_info`.** Y el comentario de `L383-385` dice
exactamente por qué esos valores:

> To disable the AGP aperture, you need to set the start to a larger value than
> the end.

`0xffffffffffff > 0`. `PROVEN`.

### Prueba 3 — por el log, que es la que cierra

```
$ journalctl -k -b | grep -c 'AGP: '
0
```

**Cero.** Y la única función del driver que puede producir esa línea es
`amdgpu_gmc_agp_location`, que por la prueba 1 no se ejecutó. **Ausencia de la
línea, dada la exclusividad de quien la imprimiría, es prueba.** `OBSERVED`.

**Las tres juntas: la apertura AGP de esta GPU está vacía. `PROVEN_ABSENT`, con
observador.**

## 2 · Y el hardware recibe la apertura vacía en la misma convención invertida

`gmc_v8_0.c:485-487` la escribe en los registros, y esto **no es una operación
nula**:

```
mmMC_VM_AGP_BASE = 0
mmMC_VM_AGP_TOP  = agp_end   >> 22 = 0x000000000
mmMC_VM_AGP_BOT  = agp_start >> 22 = 0x0003ffffff
```

`>> 22` son **unidades de 4 MiB**. Y `BOT (0x3ffffff) > TOP (0)` — **invertida,
igual que en software.**

| | software | hardware |
|---|---|---|
| unidad | dirección completa | `>> 22`, 4 MiB |
| vacío | `start (0xffffffffffff) > end (0)` | `BOT (0x3ffffff) > TOP (0)` |
| offset | — | `AGP_TOP` = `0x80a`, `AGP_BOT` = `0x80b`, `AGP_BASE` = `0x80c` |

**El driver escribe la apertura vacía en el hardware con la misma convención
invertida con que la representa en software.** `PROVEN_DERIVED`. Y es un detalle
que importa: un driver propio que ponga `AGP_TOP` y `AGP_BOT` en orden natural
—`BOT` debajo de `TOP`— **acaba con una apertura de 4 TiB que el hardware no
puede direccionar**, porque `0x0b00000000` es la mitad alta del espacio y la VRAM
está en `0x0f40000000`.

## 3 · La consecuencia: dos aperturas, no tres

Con la AGP vacía, el espacio de direcciones de esta GPU tiene exactamente dos
consumidores:

| | quién lo traduce | dónde | tamaño |
|---|---|---|---|
| **1** | **VMID 0** — el GART | `0xFF00000000` | 256 MiB |
| **2** | **VMID 1-15** — GPUVM | page tables → VRAM o RAM | 4 TiB de VA por contexto |
| **3** | ~~AGP~~ | — | **vacía** |

**No hay ninguna dirección física de GPU accesible sin pasar por el page walker.**

Y eso conecta con `gmc_v8_0.c:848`:

```
gmc_v8_0.c:846   MC_VM_MX_L1_TLB_CNTL.SYSTEM_ACCESS_MODE = 3
gmc_v8_0.c:848   MC_VM_MX_L1_TLB_CNTL.SYSTEM_APERTURE_UNMAPPED_ACCESS = 0
```

**`SYSTEM_APERTURE_UNMAPPED_ACCESS = 0` es la misma afirmación en el registro.** No
se permite acceso sin traducir a través de la apertura del sistema, y la apertura
AGP —que sería el otro camino sin traducir— no existe. **Los dos hechos se
refuerzan, y los dos son consecuencia de la misma decisión de mapa.**

### Y esto reformula la pregunta del fragmento, y la cierra mejor

`137` y `139` documentan que `ENABLE_L1_FRAGMENT_PROCESSING = 1` (`L845`) y
`ENABLE_L2_FRAGMENT_PROCESSING = 1` (`L853`), y `amdgpu_vm.c:1157` dice que en GFX8
el invalidate es obligatorio.

**Mi explicación hasta ahora era de caché: "hay una caché de fragmentos de 2 MiB,
por eso el invalidate".** Es correcta, pero no es la razón de fondo.

**La razón de fondo es que no hay camino rápido.** En un chip con AGP viva, una
dirección del rango AGP no necesita traducción y por tanto no necesita TLB. Aquí
**todo** necesita traducción, el TLB está en el camino de todas las memorias, y un
TLB con granularidad de 4 KiB sobre un espacio de 40 bits es inservible sin
fragmentos. **El fragmento no es una optimización: es la condición para que el
TLB sea utilizable en un mapa sin aperturas sin traducir.** `PROVEN_DERIVED`.

**Eso es `140` aplicado a `137`.** El mapa de direcciones no era un dato
colateral: es lo que obliga a la arquitectura de la traducción.

## 4 · El bloque de 160 registros HDP sin un solo nombre

`gmc_v8_0.c:439-447`, la primera cosa que hace `gmc_v8_0_mc_program`:

```c
/* Initialize HDP */
for (i = 0, j = 0; i < 32; i++, j += 0x6) {
        WREG32((0xb05 + j), 0x00000000);
        WREG32((0xb06 + j), 0x00000000);
        WREG32((0xb07 + j), 0x00000000);
        WREG32((0xb08 + j), 0x00000000);
        WREG32((0xb09 + j), 0x00000000);
}
WREG32(mmHDP_REG_COHERENCY_FLUSH_CNTL, 0);
```

**Ciento sesenta escrituras, aritmética literal sobre el offset, y ni un nombre.**
El paso es de 6 y escribe 5: **el sexto registro de cada grupo se salta**, y
también queda sin nombre.

### Y el resultado de buscarlos, impreso por programa

| pregunta | respuesta |
|---|---|
| offsets escritos por el driver | 160 |
| definidos en `gmc_8_1_d.h` | **0** |
| definidos en **todo** el árbol `include/asic_reg/` | **0** |
| ¿existe `hdp_8_1_d.h`? | **no existe** |
| último header de offsets HDP del corpus | `hdp_7_0_0_offset.h` — **GFX7** |
| headers HDP incluidos por `gmc_v8_0.c` | **ninguno** |

**El espacio de registros GMC en `gmc_8_1_d.h` acaba en `0x0AFE`
(`mmMC_SEQ_TRAIN_EDC_THRESHOLD3`) y el siguiente bloque empieza en `0x0C80`
(`mmMC_XBAR_ADDR_DEC`). El rango `0xB05`–`0xBC3` está fuera de él**, así que ni
siquiera son registros de GMC. El comentario dice HDP; los offsets no están en
ningún header.

### Por qué los nombres que sí aparecen vienen de GFX5

`gmc_v8_0.c` incluye `gmc_8_1_d.h`, `bif_5_0_d.h`, `oss_3_0_d.h`, `dce_10_0_d.h` —
**y ningún header de HDP**. Los `mmHDP_*` que sí nombra llegan de forma transitiva:

```
mmHDP_HOST_PATH_CNTL              -> hdp/hdp_5_0_0_offset.h
mmHDP_REG_COHERENCY_FLUSH_CNTL    -> nbif/nbif_6_1_offset.h
mmHDP_NONSURFACE_{BASE,INFO,SIZE} -> nbio/nbio_7_0_offset.h
```

**GFX5, GFX6 y GFX7 respectivamente.** **El driver está usando definiciones de
registro de tres generaciones anteriores para programar un chip de la
octava.** `PROVEN`, y explica por qué los bloques nuevos van con números.

### Y es un bloque heredado, no nuevo

El mismo bucle, con la misma aritmética, está en:

```
gmc_v6_0.c    '0xb05 + j' apariciones = 1
gmc_v7_0.c    '0xb05 + j' apariciones = 1
gmc_v8_0.c    '0xb05 + j' apariciones = 1
```

**Es una inicialización de la era GFX6 copiada literalmente hasta GFX8, con tres
generaciones sin que nadie la nombrara.** `PROVEN`.

## 5 · Lo que esto significa para un driver propio

**Los 160 registros hay que escribirlos, y no hay forma de saber qué son.** Un
driver propio tiene dos opciones y las dos son malas:

1. **Copiar el bucle.** Es lo que hace el de referencia. Y funciona, por
  DEFINICIÓN, porque el resultado observado es una GPU que arranca.
2. **No escribirlos.** Y descubrir en ejecución qué se rompe.

**No hay una tercera: el corpus no contiene la información.** `NOT_IN_CORPUS`, y
esta vez **con la causa identificada**, que es lo que la convierte en
`NOT_IN_CORPUS` y no en `NOT_FOUND`:

> el header de offsets HDP más reciente del corpus es de GFX7, y `gmc_v8_0.c` no
> incluye ningún header de HDP, así que el autor del driver no tenía nombres
> disponibles y escribió la aritmética a mano.

**Y esa es la lección transferible: cuando un driver escribe un offset literal en
un bucle, no es descuido del autor — es que el header de esa generación aún no
existe.** `PROVEN_DERIVED`, y vale para todo `asic_reg/` del corpus, no sólo para
este bloque.

## Lo que NO cierra

| afirmación | estado |
|---|---|
| La apertura AGP está vacía | `PROVEN_ABSENT` (3 pruebas) |
| `0` apariciones de `AGP:` en el log | `OBSERVED` |
| `amdgpu_gmc_agp_location` nunca se llama en GFX8 | `PROVEN_ABSENT` (por fichero) |
| `AGP_BOT (0x3ffffff) > AGP_TOP (0)` | `OBSERVED` por derivación, `PROVEN_DERIVED` |
| El hardware recibe la apertura vacía invertida | `PROVEN_DERIVED` |
| Sólo dos aperturas, ninguna sin traducir | `PROVEN_DERIVED` |
| El fragmento es condición de uso, no optimización | `PROVEN_DERIVED` |
| 160 escrituras, 0 nombres, 0 offsets en el corpus | `PROVEN_ABSENT` |
| `hdp_8_1_d.h` no existe; el último es GFX7 | `OBSERVED` |
| `gmc_v8_0.c` no incluye ningún header HDP | `PROVEN` |
| El bloque viene de la era GFX6, literal | `PROVEN` |
| Los `mmHDP_*` que nombra son de GFX5/6/7 | `PROVEN` (fichero) |
| Qué hace cada uno de los 160 registros | **`NOT_IN_CORPUS`** |
| Si el bloque es necesario en esta GPU | **`NOT_DETERMINED`** — hardware |
| Qué banco es `0xB05`–`0xBC3` | **`NOT_IN_CORPUS`** — el comentario dice HDP |
| Los registros HDP reales de GFX8 | **`NOT_IN_CORPUS`** |
| Cuál es la granularidad real de la caché L2 | **`NOT_PROVEN`** — `RREG32` de `0x501` |

**Las dos últimas filas del bloque HDP son el mismo hueco que la primera: falta el
header de GFX8.** Y un driver propio que necesite los HDP de verdad —para
escrituras de display, que es lo que hacen estos 160 registros— **no puede
construirlos con este corpus.** Eso no es un `NOT_DETERMINED` que se cierre con
tiempo: es un límite del corpus, y hay que decirlo.

## Procedencia

- `OBSERVED` -- `journalctl -k -b`, `grep -c 'AGP: '` = 0. Lectura de log: NIVEL 2.
- `STATIC` -- `gmc_v8_0.c:411-423` `:439-447` `:468-498` `:846-848` `:485-487`,
  `amdgpu_gmc.c:339-395` `:374`, `amdgpu_gmc.h:35-49`,
  `gmc_8_1_d.h` (rango `0x000`–`0x0C84`), `hdp/hdp_7_0_0_offset.h`,
  `nbif/nbif_6_1_offset.h`, `nbio/nbio_7_0_offset.h`, includes de `gmc_v8_0.c:24-52`.
- Búsqueda de los 160 offsets: `grep -rE` sobre **todo** `include/asic_reg/`, con
  el recuento impreso por programa. `0` en los dos sentidos.
- Encadenada con `140` (el mapa de direcciones, que da los números de VRAM y GART
  que esta nota usa), `139` (los bits de `ENABLE_L1_FRAGMENT_PROCESSING`),
  `137`/`138` (la configuración de TLB y L2), `136` (la cadena de coherencia),
  `116` (BAR 256 MiB), `083` (`dst`).
- No se editó `AGENTS.md` ni `OPEN-FRONTIERS.md`.

## Nota de método

**La ausencia de una línea de log, junto con la exclusividad de quien la
imprimiría, es una prueba. Y se lee en un segundo, sin placa.**

`140` me enseñó que el driver **imprime** las cuatro líneas que hacen falta para el
mapa de direcciones. **El mismo razonamiento, aplicado al revés, da la respuesta
de otra pregunta:** si una línea **no** está y sólo una función del driver puede
producirla, esa función no se ejecutó. **Eso convierte "no vi la línea del AGP" de
`NOT_OBSERVED` en `PROVEN_ABSENT`, y sin tocar hardware.**

*La presencia de un log es evidencia. La ausencia de un log, con el productor
identificado y exclusivo, es evidencia más fuerte: porque el productor se habría
ejecutado si hubiera ocurrido.* Es la regla `PROVEN_ABSENT` aplicada a un
`dev_info` en vez de a un campo de un header.

**Y la segunda lección es sobre el alcance de una herramienta.** `grep -rlE
'0xb05$' include/` devolvió vacío, y mi primera reacción fue "no está". **No está
— pero la pregunta útil no era si `0xb05` está, sino si existe el header que lo
nombraría.** Resultado: no existe `hdp_8_1_d.h`, el último es de GFX7, y
`gmc_v8_0.c` no incluye ninguno. **El `NOT_IN_CORPUS` con la causa identificada es
un resultado; el `NOT_FOUND` a secas es una queja.** Y el caso general es más
interesante que este bloque: *cuando un driver escribe offsets literales, el
header de esa generación aún no existe* — y eso vale para todo `asic_reg/`, no
sólo para 160 registros de HDP.

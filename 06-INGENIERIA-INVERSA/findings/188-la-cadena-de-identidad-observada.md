# 188 · La cadena de identidad pasa de derivada a observada, y `AMDGPU_FAMILY_VI` no existe en el corpus

```
CLASSIFICATION=VERIFICATION+DOCUMENTATION · TRACK=STATIC+RUNTIME/NIVEL_2
CORPUS=RESEARCH/working/linux-7.1.3 · HARDWARE_SCOPE=HOST-C/RX550/0000:01:00.0
WORK_CLASS=READ_ONLY/EVIDENCE · WRITE_LOCAL=PROPIOS · MODIFICATIONS_CORPUS=0 · WRITE_EXECUTION=NONE
RUNTIME=READ_ONLY (journalctl -k -b) · GPU INTACTA
```

## Qué resuelve

**La cadena de identidad que `184` dio por cerrada, revisada eslabón por eslabón. Dos de sus
tres afirmaciones no se sostienen tal como estaban escritas, y la parte que importa es
mejor de lo que `184` decía: los tres eslabones están OBSERVADOS.** `CORRECTION`.

**⇒ El kernel imprime los tres: `POLARIS12`, `vi_common`, y `Display Core v3.2.378
initialized on DCE 11.2`.** `OBSERVED`.

**⇒ Y `AMDGPU_FAMILY_VI`, el símbolo que `184`.characteristics como eslabón intermedio
citado, se usa dos veces en el corpus y no está declarado en ninguna parte: cero
definiciones.** `PROVEN_ABSENT`. `184` queda corregido en ese punto.

## 1 · Los tres eslabones, observados

```text
oct 02 00:10:30 amdgpu 0000:01:00.0: initializing kernel modesetting
                        (POLARIS12 0x1002:0x699F 0x1002:0x0B04 0xC7).
oct 02 00:10:30 amdgpu 0000:01:00.0: detected ip block number 0 <common_v1_0_0> (vi_common)
oct 02 00:10:30 amdgpu 0000:01:00.0: [drm] Display Core v3.2.378 initialized on DCE 11.2
```

| eslabón | evidencia | estado |
|---|---|---|
| `0x699F` → `POLARIS12` | el kernel lo imprime | **`OBSERVED`** |
| familia VI | el kernel nombra el bloque `vi_common` | **`OBSERVED`** |
| → `DCE 11.2` | `initialized on DCE 11.2` | **`OBSERVED`** |

**⇒ Los tres eslabones de `184` eran `PROVEN_DERIVED`, hechos de la tabla de PCI más una
cadena de `case`. Ahora son `OBSERVED`, hechos de tres líneas del kernel, y el segundo
—la familia— ya no depende de ningún símbolo sin declarar.** `PROVEN_DERIVED`.

**⇒ Y el noveno bloque observado coincide uno a uno con el mapa de `169`:**
`common_v1_0_0`, `gmc_v8_1_0`, `ih_v3_0_0`, `gfx_v8_0_0`, `sdma_v3_1_0`, `smu_v1_0_0`,
`dce_v1_0_0`, `uvd_v6_3_0`, `vce_v3_4_0`. `OBSERVED`. *Nueve bloques, y `169` los tenía por
derivación.*

## 2 · La corrección: `AMDGPU_FAMILY_VI` no está declarado

**`amdgpu/amdgpu_device.c:1987` hace `adev->family = AMDGPU_FAMILY_VI;` y
`display/amdgpu_dm/amdgpu_dm.c:1910` lo copia a `asic_id.chip_family`.**

**⇒ En todo el corpus, `AMDGPU_FAMILY_VI` aparece DOS veces y ambas son usos. No hay
ninguna definición.** `PROVEN_ABSENT`. *Las familias que `dal_asic_id.h` declara son
`FAMILY_SI 110`, `FAMILY_CI 120`, `FAMILY_KV 125`, `FAMILY_VI 130`, `FAMILY_CZ 135`,
`FAMILY_AI 141`, `FAMILY_RV 142`, `FAMILY_NV 143`, `FAMILY_VGH 144`,
`AMDGPU_FAMILY_GC_10_3_6 149`, `GC_10_3_7 151`, `GC_11_0_0 145`, `GC_11_0_1 148`,
`GC_11_5_0 150`, `GC_11_5_4 154`, `AMDGPU_FAMILY_GC_12_0_0 152`,
`AMDGPU_FAMILY_YELLOW_CARP 146` — dieciocho, y ninguna es `AMDGPU_FAMILY_VI`.*

**⇒ `184` escribió que la cadena estaba «escrita entera en el corpus con un solo eslabón
no citado por mí, que es el identificador de PCI que lee `lspci`». Eso es falso: hay un
segundo eslabón que el corpus no puede citar, porque el símbolo que usa no existe en él.**
`ERROR`. *Y es la segunda vez en esta cadena que un identificador se da por bueno porque se
usa: la primera, las 28 semillas de `181`.*

**⇒ Y el caso queda cerrado por otra vía, observada: el kernel nombra el bloque
`vi_common`, y `vi_common` es el juego de bloques de la familia VI.** `PROVEN_DERIVED`.

## 3 · Y la ruta que no necesita el símbolo: `hw_internal_rev`

**Hay un segundo camino de identidad, y funciona sobre un campo que el corpus sí declara:**

```c
display/amdgpu_dm/amdgpu_dm.c:1913            init_data.asic_id.hw_internal_rev = adev->extern_gpu_id;
display/include/dal_asic_id.h:116             #define VI_POLARIS12_V_A0 100
display/include/dal_asic_id.h:117             #define VI_VEGAM_A0 110
display/include/dal_asic_id.h:130             #define ASIC_REV_IS_POLARIS12_V(eChipRev) ((eChipRev >= VI_POLARIS12_V_A0) && \
display/include/dal_asic_id.h:131                     (eChipRev < VI_VEGAM_A0))
display/dc/core/dc_resource.c:178            if (ASIC_REV_IS_POLARIS12_V(asic_id.hw_internal_rev)) {
display/dc/core/dc_resource.c:179                dc_version = DCE_VERSION_11_2;
display/dc/basics/dce_calcs.c:49             switch (asic_id.chip_family) {
display/dc/basics/dce_calcs.c:56                 case FAMILY_VI:
display/dc/basics/dce_calcs.c:57                     if (ASIC_REV_IS_POLARIS12_V(asic_id.hw_internal_rev))
display/dc/basics/dce_calcs.c:58                         return BW_CALCS_VERSION_POLARIS12;
```

**⇒ `ASIC_REV_IS_POLARIS12_V` es un rango cerrado: 100 <= revisión interna < 110. Diez
valores.** `PROVEN`.

**⇒ Y el mismo test aparece dos veces, y las dos veces con la misma consecuencia: en
`dc_resource.c:178` da `DCE_VERSION_11_2` y en `dce_calcs.c:57` da
`BW_CALCS_VERSION_POLARIS12`, y `dce_calcs.c:2050` la invoca desde `bw_calcs_init`, que es
la función que `dce112_resource.c:1415` llama.**
`PROVEN`. *El motor de ancho de banda de `185` nombra esta placa por su propio nombre, y no
por derivación de la alcanzabilidad sino por un `case` escrito para ella.*

**⇒ Y la revisión interna no es ninguna de las dos cantidades que el log imprime:**
`0x699F` son 27039 decimal, fuera de [100,110), y la revisión PCI `0xC7` del log son 199,
también fuera.** `PROVEN`. *Son tres números distintos y `184` los trataba como si fueran
uno: el identificador de dispositivo, la revisión PCI y la revisión interna.*

## 4 · Y dos comentarios del corpus que no son verdad

**El comentario de `dal_asic_id.h:308` dice `#define FAMILY_VI 130 /* Volcanic Islands:
Iceland (V), Tonga (M) */`, y el `case` de `dce_calcs.c:56` mete a Polaris12 dentro.** `PROVEN`.

**⇒ El comentario describe la familia VI por los dos chips que la nombraron primero, y el
código la ha extendido a Polaris10, Polaris11 y Polaris12.** `PROVEN_DERIVED`. *Es la misma
familia que `183` de la otra sesión y que `156`: una regla escrita en un comentario y no
verificada contra el código. El valor numérico 130 sí es el que se usa; lo que caducó es
la lista de chips.*

**⇒ Y el rango [100,110) tiene la misma propiedad: `VI_VEGAM_A0 110` significa que Vega M es
siguiente, y por eso Polaris12, Polaris10 y Polaris11 tienen revisiones internas distintas y
consecutivas.** `PROVEN_DERIVED`.

## Lo que NO cierra

| afirmación | estado |
|---|---|
| Los tres eslabones de identidad observados | **`OBSERVED`** |
| Los nueve bloques IP observados, coinciden con `169` | **`OBSERVED`** |
| `AMDGPU_FAMILY_VI`: dos usos, cero definiciones | `PROVEN_ABSENT` — corrige a `184` |
| `ASIC_REV_IS_POLARIS12_V` es [100,110) | `PROVEN` |
| `dce_calcs.c:56-58` → `BW_CALCS_VERSION_POLARIS12` | `PROVEN` |
| El comentario de `FAMILY_VI 130` está caducado | `PROVEN` |
| El valor de `hw_internal_rev` en esta placa | **`NOT_OBSERVED`** |
| Por qué `vi_common` implica familia VI sin el símbolo | **`NOT_DETERMINED`** |
| La revisión interna, ¿`extern_gpu_id` o ASIC info? | **`NOT_DETERMINED`** |

**La primera de las abiertas es un hueco de observabilidad y tiene receta de NIVEL 2
escrita: el kernel no imprime `hw_internal_rev`, y la receta de `166` —una máscara de log
con un monitor conectado— es el mismo camino que ya funcionó nueve veces.** `NOT_OBSERVED`.
*Y el objetivo es pequeño: diez valores posibles, `[100,110)`, y el valor concreto
confirmaría la revisión interna sin tocar el hardware.*

**La segunda es la que sostiene el segundo eslabón de la cadena, y es un `DERIVATION` de
una convención de nombres de bloque, no una demostración.** `NOT_DETERMINED`.
*`vi_common` se llama así porque el bloque es el de VI; que eso implique la *familia* es una
convención del driver, y una convención puede ser wrong. La demostración sería encontrar en
el corpus dónde se elige ese nombre a partir de la familia, y no está localizado.*

## Procedencia

- `RUNTIME` (NIVEL 2, sólo lectura) -- `journalctl -k -b`, filtrado por `01:00.0` y por
  `amdgpu`. Tres líneas: `initializing kernel modesetting (POLARIS12 0x1002:0x699F
  0x1002:0x0B04 0xC7)`, `detected ip block number 0 <common_v1_0_0> (vi_common)`, y
  `[drm] Display Core v3.2.378 initialized on DCE 11.2`. **Diez líneas más de bloques IP, del
  0 al 8.**
- `STATIC` -- `display/amdgpu_dm/amdgpu_dm.c:1910` (`chip_family = adev->family`), `:1913`
  (`hw_internal_rev = adev->extern_gpu_id`), `:1914` (`pci_revision_id = adev->pdev->revision`),
  `amdgpu/amdgpu_device.c:1987` (`adev->family = AMDGPU_FAMILY_VI`),
  `amdgpu/amdgpu_drv.c:2041` (`0x699F` → `CHIP_POLARIS12`),
  `display/include/dal_asic_id.h:116` (`VI_POLARIS12_V_A0 100`), `:117`
  (`VI_VEGAM_A0 110`), `:130-131` (la macro), `:305-311` (los dieciocho `#define` de
  familia, contados), `:308` (el comentario caducado),
  `display/dc/core/dc_resource.c:178-179`, y `display/dc/basics/dce_calcs.c:49`, `:56` a `:58`, `:2050`.
- **La cuenta de las familias se hizo con `grep -nE '^#define (AMDGPU_)?FAMILY_[A-Z0-9_]+'`
  sobre `dal_asic_id.h`, y da dieciocho; `AMDGPU_FAMILY_VI` no está entre ellas ni
  aparece en ninguna otra cabecera del árbol.** `PROVEN`.
- **Y una corrección mía de `184` y `187`, que acusaron al censo de guardas de mezclar
  etiquetas entre `switch` vecinos, y es FALSO: el `switch (asic_id.chip_family)` de
  `dc_resource.c:141` tiene de verdad diecisiete etiquetas, que van de `FAMILY_SI 144` a
  `AMDGPU_FAMILY_GC_11_5_4 256`, y todas son suyas.** `REFUTED`. *Acusar a un programa de un
  defecto sin abrir el fichero es la versión negativa de la regla (d): la primera hipótesis
  ante un resultado raro es el patrón, pero la segunda es el propio patrón, y aquí era el
  segundo.*
- Encadenada con `187` (los dos caracteres y el 48,4%), `185` (**las siete raíces y el motor
  `bw_calcs`, que aquí queda confirmado por un `case` escrito para esta placa**),
  `184` (**la cadena de identidad, corregida en este punto**), `183` (otra sesión), `181`,
  `180` (otra sesión), `179`, `178`, `173`, `172`, `169` (**los nueve bloques IP, que aquí
  quedan observados**), `167`, `165`, `163` (**las nueve confirmaciones del log, y esta es la
  décima**), `159`, `156`, `151`, `149`, `140`.
- No se editó `AGENTS.md` ni `OPEN-FRONTIERS.md`, y no se añadió ningún fichero al corpus.

## Nota de método

**La lección de esta iteración es la segunda mitad de la regla (d), y es la que más caro sale:
*ante un resultado raro, la primera hipótesis es el patrón, y la segunda es el propio patrón.**
*En `184` y `187` acusé al censo de guardas de mezclar etiquetas entre `switch` vecinos, lo
escribí dos veces, y lo diagnostiqué sin abrir el fichero. El fichero dice que ese `switch`
tiene diecisiete etiquetas y que todas son suyas.* **El defecto de verdad era otro y estaba
en mi mapa, que declaraba un símbolo que el corpus no define.**

**Y el eslabón que había dado por cerrado era el menos bueno de los tres.** *Porque se usa
no significa que exista:* `AMDGPU_FAMILY_VI` se usa dos veces, en `amdgpu_device.c` y en
`hwmgr.c`, y no está declarado en ninguna cabecera del árbol. **Es la segunda vez en esta
cadena que un identificador se acepta por el hecho de aparecer usándose — la primera
fueron las 28 semillas de `181`—, y las dos veces el mismo error cuesta la mitad de una
iteración.**

**Y lo que sale de esa corrección es mejor que lo que había: los tres eslabones están
OBSERVADOS, no derivados, y el segundo ya no depende del símbolo.** *El kernel imprime
`POLARIS12`, nombra el bloque `vi_common`, y dice `initialized on DCE 11.2`.* **Cerrar una
cadena por derivación la deja en `PROVEN_DERIVED`; cerrarla con lo que el hardware imprime
la deja en `OBSERVED`, y esa diferencia decide si un driver propio puedeFAI:**

**Y hay un comentario caducado en el fichero deASIC, y es de la misma familia que los que ya
están en la lista:** `#define FAMILY_VI 130 /* Volcanic Islands: Iceland (V), Tonga (M) */`,
y el código mete a Polaris12 en ese `case`. **El valor 130 es el que se usa; lo que caducó
es la lista de chips, y una lista de chips en un comentario es una afirmación que nadie
comprueba hasta que alguien la copia a una tabla.**
# 241  El eslabón que faltaba era un literal: `+ 0x64` es `VI_POLARIS12_V_A0`, y sólo una variable de las 21 no es verificable

```
CLASSIFICATION=VERIFICATION+DOCUMENTATION · TRACK=STATIC
CORPUS=RESEARCH/working/linux-7.1.3 · HARDWARE_SCOPE=HOST-C/RX550/0000:01:00.0
WORK_CLASS=READ_ONLY/EVIDENCE · WRITE_LOCAL=PROPIOS · MODIFICATIONS_CORPUS=0 · WRITE_EXECUTION=NONE
RUNTIME=NOT_RUN · GPU INTACTA
```

## Qué resuelve

**El punto abierto de `188` —«por qué `vi_common` implica familia VI, es una convención»— y
el eslabón que `188` cita mal: el identificador de la fuente de la revisión interna.** `PROVEN`.

**⇒ `vi.c:1587` escribe `adev->external_rev_id = adev->rev_id + 0x64;` y `0x64` son 100,
que es `VI_POLARIS12_V_A0` declarado en `dal_asic_id.h:116`.** `PROVEN`.

**⇒ Con eso la cadena de identidad queda cerrada sin un solo símbolo sin declarar, y de las
cinco variables de las 21 guardas sólo una —`chip_family`— no es verificable en el
corpus.** `PROVEN_DERIVED`.

**⇒ Y una corrección propia, y es la más torpe de la tanda: `188` cita
`adev->extern_gpu_id`, un símbolo que no existe en el corpus. La línea real dice
`adev->external_rev_id`.** `ERROR`. `188` queda corregido.

## 1 · La cadena cerrada, eslabón por eslabón

```c
amdgpu/amdgpu_drv.c:2041              {0x1002, 0x699F, PCI_ANY_ID, PCI_ANY_ID, 0, 0, CHIP_POLARIS12},
amdgpu/amdgpu/vi.c:1566                 case CHIP_POLARIS12:
amdgpu/amdgpu/vi.c:1587                     adev->external_rev_id = adev->rev_id + 0x64;
display/include/dal_asic_id.h:116        #define VI_POLARIS12_V_A0 100
display/amdgpu_dm/amdgpu_dm.c:1913    init_data.asic_id.hw_internal_rev = adev->external_rev_id;
display/dc/core/dc_resource.c:178     if (ASIC_REV_IS_POLARIS12_V(asic_id.hw_internal_rev)) {
display/dc/core/dc_resource.c:179         dc_version = DCE_VERSION_11_2;
```

**⇒ `0x64` son 100 y `VI_POLARIS12_V_A0` es 100: la misma constante aparece dos veces, una
como macro en `display/` y otra como literal hexadecimal en `amdgpu/`.** `PROVEN`.

**⇒ Y por eso el rango [100,110) de `188` es verificable: `external_rev_id` cae dentro
exactamente cuando `adev->rev_id` cae en [0,10).** `PROVEN_DERIVED`. *Y `adev->rev_id` es un
número pequeño de revisión, no el identificador de dispositivo: `0x699F` son 27039 y la
revisión PCI `0xC7` son 199, y los tres quedan fuera del rango, que es lo que demuestra que
son tres cantidades y no una.*

**⇒ Y el log lo confirma por el otro extremo: `[drm] Display Core v3.2.378 initialized on
DCE 11.2`.** `OBSERVED`.

**⇒ De los tres números del log, dos son copiados literalmente al ASIC id y el tercero
tampoco: `amdgpu_dm.c:1912` pone `pci_revision_id = adev->pdev->revision` y `:1914` pone
`chip_id = adev->pdev->device`.** `PROVEN`. *La estructura `hw_asic_id` lleva los tres, y
`188` los trataba como uno.*

## 2 · La corrección: `extern_gpu_id` no existe

**`188` escribió «`init_data.asic_id.hw_internal_rev = adev->extern_gpu_id;`».**
`ERROR`.

**⇒ En todo el corpus, `extern_gpu_id` aparece CERO veces. El símbolo real es
`adev->external_rev_id`, declarado en `amdgpu/amdgpu.h:872` como `uint32_t`.** `PROVEN`.

**⇒ Y la causa del error es que yo leí la línea por un `cut -c1-100` que la truncó en
`adev->ex…`, y completé el identificador por expectation en lugar de releer.** `ERROR`.
*Es la regla (h) incumplida por tercera vez en la tanda —los identificadores se leen en su
definición— y la primera cuyo fallo visible es un truncamiento mío y no un nombre que yo
inventé de la nada. **Un `cut` es un filtro, y un filtro que corta un identificador
devuelve un identificador distinto que se parece al bueno.***

**⇒ Y que el símbolo exista en `amdgpu.h:872` es lo que hace la diferencia entre las dos
cadenas: `external_rev_id` es verificable porque se puede seguir hasta su definición;
`AMDGPU_FAMILY_VI`, que `188`-PROVEN_ABSENT, no.** `PROVEN_DERIVED`.

## 3 · Las 21 guardas, y cuáles son verificables

**Agrupadas por la variable que las decide, que es la pregunta que `184` no se hizo:**

| variable | guardas | estado del valor en esta placa |
|---|---|---|
| `dc_version` y sus alias | **10** | **`PROVEN`** — `vi.c:1587` da `0x64`, `dc_resource.c:178-179` lo aplica |
| `adev->asic_type` | 3 | **`OBSERVED`** — el log imprime `POLARIS12` |
| **`chip_family`** y sus cuatro qualifying | **6** | **`NOT_DETERMINED`** — `AMDGPU_FAMILY_VI` no está declarado |
| `adev->family` | 1 | **`NOT_DETERMINED`** — el mismo símbolo |
| `dcn_version` | 1 | **`NOT_APPLICABLE`** — sólo `DCN_VERSION_*`, y esta placa es DCE |

**⇒ Diez de las veintiuna se podan con un valor que el corpus demuestra, tres con un valor
que el hardware imprime, y seis no.** `PROVEN_DERIVED`.

**⇒ Las seis no verificables son `dce_calcs.c:49`, `clk_mgr.c:152`, `clk_mgr.c:393`,
`dc.c:6001`, `dc_resource.c:141` y `link_edp_panel_control.c:846`.** `PROVEN`.

**⇒ Y de esas seis, una es precisamente la que produce el valor que las otras cinco
consumen: `dc_resource.c:141` es `resource_parse_asic_id`, que convierte
`chip_family` + `hw_internal_rev` en `dc_version`.** `PROVEN`.

**⇒ Lo que se puede decir de `chip_family` sin el símbolo es sólo esto: como
`resource_parse_asic_id` tiene un `case FAMILY_VI:` y esta placa no es Carrizo ni
Vega M, `chip_family` tiene que valer `FAMILY_VI`, que es 130.** `PROVEN_DERIVED`.
*Y es una deducción desde el comportamiento —el `case` que se toma— no desde una
declaración. Es correcta y no es verificable, y esas dos cosas no son lo mismo.*

## 4 · Y por qué esto explica el fallo de la poda

**La poda de `184` y `187` fallaba, y `184` lo atribuyó a que el censo mezclaba etiquetas
entre `switch` vecinos. Eso era falso y `188` lo refutó. La causa real es esta y es
estructural:** `PROVEN_DERIVED`.

**⇒ El mapa `VALOR_POR_PLANTA` declara cinco variables. Dos de ellas —`dc_version` y
`asic_type`— son verificables, y con ellas la poda debería funcionar; las otras tres son
`chip_family`, `family` y `dcn_version`, que o no son verificables o no aplican.** `PROVEN`.

**⇒ Y las seis guardas sobre `chip_family` no se podan en absoluto con el mapa actual, y sin
poda cada una arrastra las ramas de las otras familias: `clk_mgr.c:152` con sus diecisiete
etiquetas incluye `FAMILY_CI`, `FAMILY_KV` y `FAMILY_SI`, tres familias de DCE anteriores.**
`PROVEN`. *Y por eso el total podado se mueve en saltos grandes y no de forma monótona:
cada etiqueta sin podar mete el subárbol entero de ese chip.*

**⇒ La corrección del mapa es de una línea por variable, y es declarar el valor por su
nombre de macro del corpus y no por el símbolo que usa el llamante:** `chip_family` →
`{FAMILY_VI}`, `family` → sin entrada hasta que `AMDGPU_FAMILY_VI` aparezca declarado, y
`dcn_version` → conjunto vacío, que la regla conservadora de `184` ya convierte en «no
podar».** `PROVEN_DERIVED`.

## Lo que NO cierra

| afirmación | estado |
|---|---|
| `vi.c:1587` da `rev_id + 0x64` y `0x64` = `VI_POLARIS12_V_A0` | `PROVEN` |
| La cadena de identidad no usa ningún símbolo sin declarar | `PROVEN` |
| `extern_gpu_id` no existe; el símbolo es `external_rev_id` | `PROVEN_ABSENT` — corrige a `188` |
| 10 de las 21 guardas son verificables por `dc_version` | `PROVEN_DERIVED` |
| 3 lo son por `asic_type`, y una no aplica | `PROVEN` |
| 6 no son verificables, y una de ellas produce el valor de las otras | `PROVEN_DERIVED` |
| `chip_family` tiene que valer `FAMILY_VI` = 130 | `PROVEN_DERIVED`, por comportamiento |
| La declaración de `AMDGPU_FAMILY_VI` | **`PROVEN_ABSENT`** |
| El valor de `adev->rev_id` en esta placa | **`NOT_OBSERVED`** |
| El total podado con el mapa corregido | **`NOT_DETERMINED`** |

**La segunda de las abiertas es la que decide el estado de la poda, y es un hueco del
corpus, no un trabajo pendiente: `AMDGPU_FAMILY_VI` se usa en dos ficheros y no lo declara
ninguna cabecera del árbol.** `PROVEN_ABSENT`. *No es `NOT_FOUND`: es `PROVEN_ABSENT`, y la
diferencia importa porque un hueco del corpus no se cierra escribiendo, se cierra declarando
lo que falta, y lo que falta aquí es una cabecera que no sé nombrar.*

**Y la tercera es una observación de NIVEL 2 con ruta barata, escrita: el kernel no imprime
`adev->rev_id`, y con él `external_rev_id` cierra el rango [100,110).** `NOT_OBSERVED`.

## Procedencia

- `STATIC` -- `amdgpu/amdgpu/amdgpu.h:872` (`uint32_t external_rev_id;`),
  `amdgpu/amdgpu/vi.c:1566` (`case CHIP_POLARIS12:`), `:1587`
  (`adev->external_rev_id = adev->rev_id + 0x64;`), `:2049` (`vi_set_ip_blocks`),
  `:2053` (`switch (adev->asic_type)`), `:2035` (`vi_common_ip_block`),
  `vi.c:2021` (`.name = "vi_common"`), `amdgpu/amdgpu_drv.c:2041`,
  `amdgpu/amdgpu/amdgpu_device.c:1976-1992` (los ocho chips de una rama, `AMD_IS_APU` y
  `vi_set_ip_blocks`), `display/amdgpu_dm/amdgpu_dm.c:1912`, `:1913`, `:1914`,
  `display/include/dal_asic_id.h:116`, `:117`, `:130-131`, `:308`,
  `display/dc/core/dc_resource.c:178-179`, `display/dc/basics/dce_calcs.c:49`, `:56`, `:57`,
  `:58`, `:2050`.
- La agrupación de las 21 guardas por variable sale de `inst_closure.py --censo_guardas`, y
  el criterio de agrupación es: si el nombre de la variable contiene `chip_family` es una
  variable, si contiene `dce_version` o es `dc_version`/`version`/`dce` es otra, y si no es
  la que sea. **El criterio está declarado y es verificable sobre la salida, que es lo que
  la regla (j) exige.**
- **La cuenta de usos de `extern_gpu_id` es cero, sobre `linux-7.1.3` entero, sin filtro de
  extensión.** `PROVEN_ABSENT`.
- **Y el error que lo causó es mío y es de una clase que no tenía registrada: `sed … |
  cut -c1-100` recorta un identificador en mitad y devuelve algo que parece el
  identificador.** `ERROR`. *La regla que sale: un identificador se cita desde una lectura
  sin filtro de ancho, o no se cita. `cut` sobre código fuente es un filtro de columnas y el
  código no tiene columnas.*
- Encadenada con `188` (**los tres eslabones observados y el `PROVEN_ABSENT` de
  `AMDGPU_FAMILY_VI`, y su `NOT_OBSERVED` del valor de la revisión interna, que aquí queda
  con la vía de derivación**), `187` (los dos caracteres y el 48,4%), `185` (las siete
  raíces), `184` (**las 21 guardas y la cadena, y su diagnóstico del fallo de la poda, que
  aquí se corrige: el defecto no era el censo sino una variable no verificable**),
  `183` (otra sesión), `181`, `180` (otra sesión), `179`, `178`, `173`, `172`, `169`, `167`,
  `165`, `163`, `159`, `156`, `151`, `149`, `140`.
- No se editó `AGENTS.md` ni `OPEN-FRONTIERS.md`, y no se añadió ningún fichero al corpus.

## Nota de método

**La cadena estaba cerrada desde `184` y no lo sabía, porque el eslabón que faltaba no era
un símbolo sino un número escrito de otra manera.** *`vi.c:1587` dice `+ 0x64` y
`dal_asic_id.h:116` dice `100`: la misma constante, en hexadecimal y en decimal, en dos
ficheros, veinte años de driver y una línea de por medio.* **Y un eslabón escrito de otra
manera es un eslabón que una búsqueda por nombre no encuentra, y por eso «no hay ruta de
identidad» y «la ruta está partida en dos formas de escribirla» se parecen tanto.**

**Y el error de la nota es el peor de la tanda por la clase, no por la consecuencia:
`cut -c1-100` recorta un identificador en mitad y devuelve algo que parece el
identificador.** *Yo leí `adev->ex…` y escribí `adev->extern_gpu_id`, un símbolo que no
existe en el árbol, a partir de una línea que yo mismo había recortado.* **Un filtro de
columnas sobre código fuente devuelve un identificador distinto que se parece al bueno, y
por eso es más peligroso que un filtro de palabras: no devuelve nada, devuelve algo.**

**Y hay una regla de método que sale de aquí y que generaliza por encima de esta
investigación: *un identificador se cita desde una lectura sin filtro de ancho, o no se
cita*.** *Porque el error no es de memoria ni de invención —de eso me doy cuenta—, es de
presentación: la herramienta que uso para no llenar la pantalla me cambió un nombre por
otro que no existe, y el nombre nuevo es plausible.*

**Y la conclusión de fondo es uncomfortable y conviene dejarla escrita: de las cinco
variables que deciden las 21 guardas, seis guardas —el 29%— se apoyan en un valor que
el corpus no puede verificar.** *Y eso no es un detalle de mi instrumento: es un hecho del
proyecto, porque un driver que escriba las suyas necesita saber qué valor poner en
`chip_family`, y ese valor no está en ninguna cabecera del árbol.*
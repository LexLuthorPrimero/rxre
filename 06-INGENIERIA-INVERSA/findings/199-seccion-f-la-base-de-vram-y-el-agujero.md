# 199 · §F: la base de VRAM viene del VBIOS en 16 MiB, y `max_mc_address` no es lo que el estado decía

```
CLASSIFICATION=VERIFICATION+DOCUMENTATION · TRACK=STATIC+RUNTIME/NIVEL_2
CORPUS=RESEARCH/working/linux-7.1.3 · HARDWARE_SCOPE=HOST-C/RX550/0000:01:00.0
WORK_CLASS=READ_ONLY/EVIDENCE · WRITE_LOCAL=PROPIOS · MODIFICATIONS_CORPUS=0 · WRITE_EXECUTION=NONE
RUNTIME=READ_ONLY (journalctl -k -b) · GPU INTACTA
```

## Qué resuelve

**El lado MC de §F, que es donde `AGENTS.md` coloca la frontera y donde el estado
portaba dos números que el log contradice.** `PROVEN`.

**⇒ La base de VRAM la pone el VBIOS, en un campo de 16 bits con unidad de 16 MiB, y el
driver la lee pero no la escribe en esta placa.** `PROVEN`.

**⇒ Y una corrección al estado conocido: `max_mc_address` es `0xFFFFFFFFFF`, no
`0xFF0FFFFFFF`. El valor que el estado tenía es `gart_end`, que es otra cantidad.** `PROVEN`.

## 1 · Lo observado, y el productor, y coinciden

```text
amdgpu 0000:01:00.0: VRAM: 2048M 0x000000F400000000 - 0x000000F47FFFFFFF (2048M used)
amdgpu 0000:01:00.0: GART: 256M 0x000000FF00000000 - 0x000000FF0FFFFFFF
amdgpu 0000:01:00.0: 5907M of GTT memory ready.
amdgpu 0000:01:00.0: [drm] Detected VRAM RAM=2048M, BAR=256M
```

```c
amdgpu/gmc_v8_0.c:416   if (!amdgpu_sriov_vf(adev))
amdgpu/gmc_v8_0.c:417           base = RREG32(mmMC_VM_FB_LOCATION) & 0xFFFF;
amdgpu/gmc_v8_0.c:418   base <<= 24;
amdgpu/gmc_v8_0.c:420   amdgpu_gmc_set_agp_default(adev, mc);
amdgpu/gmc_v8_0.c:421   amdgpu_gmc_vram_location(adev, mc, base);
amdgpu/gmc_v8_0.c:422   amdgpu_gmc_gart_location(adev, mc, AMDGPU_GART_PLACEMENT_BEST_FIT);
amdgpu/amdgpu_gmc.c:220        mc->vram_start = base;
amdgpu/amdgpu_gmc.c:221        mc->vram_end = mc->vram_start + mc->mc_vram_size - 1;
```

**⇒ Para GFX8 el registro es UNO de 32 bits, no dos: `MC_VM_FB_LOCATION__FB_BASE__SHIFT 0x0`
con `MASK 0xffff`, y `FB_TOP__SHIFT 0x10`** (`include/asic_reg/gmc/gmc_8_1_sh_mask.h:3969`
y `:3971`). *Es la diferencia estructural con SOC15+, donde BASE y TOP son registros de 32
bits separados y aparecen como `regMC_VM_FB_LOCATION_BASE` y `regMC_VM_FB_LOCATION_TOP`.*

**⇒ Y la aritmética, calculada por programa y no a mano:**

| magnitud | cálculo | valor | observado |
|---|---|---|---|
| `FB_BASE` | leído del VBIOS, 16 bits | `0xF400` = 62.464 | — |
| `vram_start` | `FB_BASE << 24` | `0x000000F400000000` | **coincide** |
| `vram_end` | `vram_start + 2048 MiB  1` | `0x000000F47FFFFFFF` | **coincide** |

**⇒ Y el driver sólo *escribe* ese registro dentro de `if (amdgpu_sriov_vf(adev))`
(`gmc_v8_0.c:475-478`), es decir para una función virtual. Esta placa es un
funcionamiento físico, y `amdgpu_gmc.h:262` lo dice del mismo modo: «set by vbios».**
`PROVEN`. *Un driver propio tiene que leer `FB_BASE` del VBIOS en esta placa, y no puede
asumir ni cero ni 0xF400.*

## 2 · `max_mc_address`, y por qué el estado tenía otra cosa

```c
amdgpu/amdgpu_gmc.c:298   /*To avoid the hole, limit the max mc address to AMDGPU_GMC_HOLE_START*/
amdgpu/amdgpu_gmc.c:299   u64 max_mc_address = min(adev->gmc.mc_mask, AMDGPU_GMC_HOLE_START - 1);
amdgpu/amdgpu_gmc.c:328           mc->gart_start = max_mc_address - mc->gart_size + 1;
amdgpu/amdgpu_gmc.c:332   mc->gart_start &= ~(four_gb - 1);
amdgpu/amdgpu_gmc.c:333   mc->gart_end = mc->gart_start + mc->gart_size - 1;
amdgpu/gmc_v8_0.c:1133    adev->gmc.mc_mask = 0xffffffffffULL; /* 40 bit MC */
amdgpu/amdgpu_gmc.h:36    #define AMDGPU_GMC_HOLE_START  (adev->vm_manager.max_level == 4 ? \
amdgpu/amdgpu_gmc.h:37        0x0100000000000000ULL : 0x0000800000000000ULL)
```

**⇒ `AMDGPU_GMC_HOLE_START` vale `0x0100000000000000` o `0x0000800000000000`. Los DOS
casos son mayores que `mc_mask = 0xFFFFFFFFFF`, así que el mínimo es siempre `mc_mask` y el
hueco de direcciones no entra en el cálculo en esta placa.** `PROVEN`.

**⇒ `max_mc_address = 0xFFFFFFFFFF`, y con él la cadena del GART cuadra exacta:**

| magnitud | cálculo | valor | observado |
|---|---|---|---|
| `gart_size` | log | 256 MiB | **coincide** |
| `gart_start` | `(0xFFFFFFFFFF  256 MiB + 1) & ~(4 GiB1)` | `0x000000FF00000000` | **coincide** |
| `gart_end` | `gart_start + gart_size  1` | `0x000000FF0FFFFFFF` | **coincide** |

**⇒ Y `gart_end + gart_size = 0x000000FF1FFFFFFF = mc_mask + 1`.** `PROVEN_DERIVED`.

**⇒ Por tanto `max_mc_address = 0xFFFFFFFFFF` y `0xFF0FFFFFFF` es `gart_end`, que es otra
cantidad: la colocación `BEST_FIT` pone el GART terminando justo antes del tope, y por eso
los dos números se parecen y son distintos.** `PROVEN_DERIVED`.

**⇒ El estado que yo venía arrastrando decía «`max_mc_address` = `0xFF0FFFFFFF` por
aritmética inversa desde `gart_start` observado». Las dos mitades están mal: el valor es
`0xFFFFFFFFFF`, y no se deriva de `gart_start` sino que es lo que lo determina.** `ERROR`.
*Es la undécima corrección propia de esta tanda, y la de la clase más difícil: un número
correcto al que se le atribuye el origen equivocado. Un número con la genealogía mal puesta
hereda la autoridad del sitio del que se dice que viene, y este además se clasifica `PROVEN`
cuando su derivación era imposible.*

## 3 · Y la segunda corrección: el GART son 256 MiB, no 1.792

**El estado decía «2.048 MiB VRAM, 256 MiB BAR, 1.792 MiB (88%) sólo por GART». El log
dice `GART: 256M` y `5907M of GTT memory ready`, y `Detected VRAM RAM=2048M, BAR=256M`.**
`PROVEN`.

**⇒ Tres números distintos: RAM 2048 M, BAR 256 M, GART 256 M, GTT 5907 M.** `PROVEN`.
*El 1.792 MiB no aparece en ninguna línea del log, y el «88%» tampoco: 1.792 de 2.048 es el
87,5%, que redondea a 88, así que la cifra viene de una división —pero por 2.048 de algo
que el log no nombra de esa manera. **Lo que el log nombra con 256 M dos veces es el BAR y
el GART, y son cosas distintas: el BAR es el Mandatory que la CPU ve, y el GART es la
tabla de traducción de la RAM del sistema.**

## 4 · El error de esta nota, y es el peor de la tanda por la clase

**Escribí en la salida de mi propio programa una conclusión que el programa acababa de
refutar dos líneas antes:**

```text
  start >> 24 = 0xF400 = 62464, y eso necesita 16 bits; el campo es de 16
  ⇒ IMPOSIBLE CON ESE PRODUCTOR. El campo es de 16 bits y el desplazamiento 24.
```

**⇒ La segunda línea es falsa: `0xF400` necesita 16 bits y el campo es de 16 bits, luego
cabe, y `0xF400 << 24` es exactamente el `vram_start` observado.** `ERROR`.

**⇒ La causa es que escribí la frase antes de mirar el resultado, porque «imposible» era la
lectura que esperaba — y a la derecha del mensaje, en la misma salida, estaba la aritmética
que lo desmiente.** *Es el patrón más caro de esta tanda y se ha repetido: primero las 28
semillas inventadas, luego los «dos caracteres», luego las dos mil líneas imposibles de
`display/`.*

**⇒ Y hay una segunda cosa en la misma zona: derivé
`AMDGPU_GMC_HOLE_START = 0xFF10000000` a partir del `max_mc_address` observado, y era una
constante definida con una ternaria dos líneas más abajo en el mismo fichero que yo tenía
abierto.** `ERROR`. *La regla (e) —leer el bloque que precede a la función antes de declarar
`NOT_DETERMINED`— se extiende así: **antes de derivar una constante, leer su definición**,
que estaba en el fichero abierto.*

## Lo que NO cierra

| afirmación | estado |
|---|---|
| `vram_start = FB_BASE << 24`, `FB_BASE` del VBIOS, 16 bits | `PROVEN` |
| `vram_end = vram_start + mc_vram_size  1` | `PROVEN` |
| Un solo registro de 32 bits para GFX8 | `PROVEN` |
| El driver no lo escribe en un PF | `PROVEN` |
| `max_mc_address = 0xFFFFFFFFFF` | `PROVEN` |
| `gart_start` y `gart_end` cuadran exactos | `PROVEN` |
| El hueco no entra en el cálculo | `PROVEN` |
| `max_mc_address` era `0xFF0FFFFFFF` | **`ERROR`** — corregido |
| El GART eran 1.792 MiB | **`ERROR`** — corregido, son 256 |
| El valor de `FB_BASE` de esta placa, leído del VBIOS | **`NOT_OBSERVED`** |
| `mc_vram_size` de dónde sale | **`NOT_DETERMINED`** |
| Los 5907 MiB de GTT, y su relación con el GART | **`NOT_DETERMINED`** |

**La primera de las abiertas es la última pieza de §F en el lado de VRAM, y su ruta está
escrita y es NIVEL 2: `FB_BASE` son los bits 0-15 de `mmMC_VM_FB_LOCATION`, y la receta
de `166` —una máscara de log más un monitor conectado— es el mismo camino que ya funcionó
diez veces.** `NOT_OBSERVED`. *Y el valor derivado es `0xF400`, que es comprobable.*

**Y la tercera es la que separa las dos mitades de §F, que `AGENTS.md` pide explícitamente
—«separar la traducción GPUVM de la decodificación de dirección MC»—: el GART de 256 MiB
es la ventana de RAM del sistema y los 5907 MiB de GTT son otra cosa, y esta nota no dice
cuál es cuál.** `NOT_DETERMINED`.

## Procedencia

- `RUNTIME` (NIVEL 2, sólo lectura) -- `journalctl -k -b`: `VRAM: 2048M
  0x000000F400000000 - 0x000000F47FFFFFFF (2048M used)`, `GART: 256M 0x000000FF00000000 -
  0x000000FF0FFFFFFF`, `5907M of GTT memory ready.`, `[drm] Detected VRAM RAM=2048M,
  BAR=256M`.
- `STATIC` -- `amdgpu/gmc_v8_0.c:411-423` (`gmc_v8_0_vram_gtt_location`), `:416`, `:417`,
  `:418`, `:420`, `:421`, `:422`, `:425-478` (la escritura bajo `sriov_vf`),
  `:1133` (`mc_mask`), `amdgpu/amdgpu_gmc.c:214-238`
  (`amdgpu_gmc_vram_location`), `:220`, `:221`, `:294-336`
  (`amdgpu_gmc_gart_location`), `:298`, `:299`, `:305`, `:322-329`, `:332`, `:333`,
  `amdgpu/amdgpu_gmc.h:36-37` (`AMDGPU_GMC_HOLE_START`), `:262` (el comentario «set by
  vbios»), `include/asic_reg/gmc/gmc_8_1_sh_mask.h:3969-3972` (los cuatro campos),
  `include/asic_reg/gmc/gmc_8_1_d.h:281` (`mmMC_VM_FB_LOCATION`).
- Las cinco tablas de arriba las imprime un programa, no una resta mental: la aritmética de
  los seis valores se calcula en cada ejecución y las dos columnas «calculado» y
  «observado» se comparan en el propio programa.
- **Y el informe de coordinación, que es de otra cosa y va aparte: `findings/` tiene unas
  200 colisiones de número de tres cifras, desde el 001 hasta el 190, y la sesión anterior
  lo ya había documentado en `048-numeros-de-hallazgo-no-identifican.md`.** `PROVEN`.
  *Mi nota 190 chocó con `190-dos-registros-de-version-ip-y-tmz-confirmado-en-runtime.md`
  de otra sesión, y la he renumerado a 198 para no añadir a la cuenta. **No he tocado
  ningún fichero ajeno.** Y otra sesión ya documentó también el problema de intrusiones de
  caracteres en `189-diecinueve-caracteres-chinos-en-un-proyecto-que-escribe-en-castellano.md`,
  que es un problema mío recurrente y que está medido mejor de lo que yo lo medía.*
- Encadenada con `198`/`198` (las tres correcciones de la poda), `241` (la cadena de
  identidad), `240` (los tres eslabones observados), `187`, `239`, `184`, `181`, `164`
  (**Lexa PRO y el GART**, que es el que afirmaba el `0xFF0FFFFFFF`),
  `140` (el mapa de direcciones observado), `217` (**la cadena muerta de la tabla de
  registros MC**), `086`, `100`, `205`, `067`, `054`, `024`, `023`.
- No se editó `AGENTS.md` ni `OPEN-FRONTIERS.md`, y no se añadió ningún fichero al corpus.

## Nota de método

**Vuelvo a §F después de quince notas en `display/`, y el barrido paga en seguida: el primer
cifrado que escribí —«`MC_FB_LOCATION` no aparece en ningún hallazgo»— ya era un resultado,
porque el registro que programa la base y el tamaño de la VRAM es el item con nombre propio
de §F y nadie lo había medido.** *Y el segundo fue una corrección del estado que yo mismo
venía arrastrando, sobre un número que es correcto y del que estaba mal dicho el origen.*

**Y la corrección tiene la clase más difícil que hay: un número cierto con la genealogía
equivocada.** *`max_mc_address = 0xFF0FFFFFFF` no es un número inventado; es `gart_end`, que
en esta placa coincide con el tope del MC por cómo funciona la colocación `BEST_FIT`, y por
eso parece el mismo número. **Y una cifra correcta con el origen atribuido al revés hereda
la autoridad del sitio del que se dice que viene**, que aquí es la aritmética inversa sobre
un valor observado, es decir un método que suena a derivación y no lo es.*

**Y el error de la nota vuelve a ser el peor de la tanda, y es el tercero de la misma clase:
escribí «IMPOSIBLE CON ESE PRODUCTOR» en la salida de un programa, con la aritmética que lo
desmiente dos líneas más a la derecha.** *Las tres veces el número que yo quería y el
número del programa no coincidían, y las tres veces la causa fue que yo había decidido la
conclusión antes de mirar. **Una herramienta que imprime contradicciones en su propia
salida es la cosa más útil que existe, y sólo sirve si se lee hasta el final del bloque.***

**Y hay una regla que sale de aquí y que es la más barata de esta tanda:
*antes de derivar una constante, leer su definición, que puede estar en el fichero que ya
tienes abierto*.** *Derivé `AMDGPU_GMC_HOLE_START = 0xFF10000000` a partir de un valor
observado, y la definición era una ternaria en la línea 36 de una cabecera que no había
abierto y que era el destino natural del nombre que estaba buscando.*
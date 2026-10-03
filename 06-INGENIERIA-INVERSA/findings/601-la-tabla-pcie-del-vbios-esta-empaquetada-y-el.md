# 601 · La tabla PCIe del VBIOS está empaquetada y el kernel la lee 2 bytes desplazada

WORK_CLASS=READ_ONLY · WRITE_EXECUTION=NONE · MODIFICATIONS 0

> ## REFUTADO por `608` — este hallazgo no debe usarse como evidencia
>
> El texto se conserva íntegro como registro (§68), pero **su afirmación central
> es falsa**. Medido con gcc sobre el struct real:
>
> ```
> ATOM_Polaris10_PCIE_Record:  sizeof alineado 8 / empaquetado 8    SIN RELLENO
>                              ulPCIE_Sclk @+4 en ambos
> ATOM_Polaris10_PCIE_Table:   ucRevId @0, ucNumEntries @1, entries @2  en ambos
> ```
>
> Y `process_pptables_v1_0.c:550-552` avanza con `GET_FLEXIBLE_ARRAY_MEMBER_ADDR`,
> que es `sizeof(type) * n` = **8** (`pp_debug.h:58-59`).
>
> **No existe el desfase de 2 bytes.** `entries` está en `+2` en ambos casos y el
> paso es 8 en ambos casos. No hay nada que corregir.
>
> La tabla PCIe vive en `0x9EFA` y decodifica coherente: `rev=1`, 3 entradas,
> carriles 8/8/8, `sclk` 2812/26100/26100 kHz. Eso **sí** queda confirmado.
>
> **Origen del error:** `601` salió de un layout de struct que reconstruí a mano en
> lugar de usar el declarado. Es el mismo fallo que produjo un probe con carriles
> 0/0/252 en `608`, y la regla que lo evita está en `608` §6.

> ## Resultado
>
> El discriminante de `550` queda **cerrado**: no hay segundo lector, y de las
> tres alineaciones posibles **solo una produce datos válidos**.
>
> ```
> NO hay segundo lector   ATOM_Polaris10_PCIE_Table: 2 apariciones en 2689 ficheros
> entries @ 2   carriles 8,8,8   relojes 2812, 26100, 26100   <- UNICA valida
> entries @ 3   carriles 0,0,0   relojes basura
> entries @ 4   carriles 0,0,0   relojes basura                 <- la que usa el kernel
> ```
>
> **El VBIOS de mi placa empaqueta la tabla en offset 2, y el `struct` compilado
> del kernel la lee en offset 4.** Desplazamiento de **2 bytes**.

## No hay segundo lector: ámbito contado

```
amd/ : 2689 ficheros .c/.h
```

| símbolo | hits | dónde |
|---|---|---|
| `ATOM_Polaris10_PCIE_Table` | **2** | la definición (`pptable_v1_0.h:239`) y el **único** uso (`process_pptables_v1_0.c:523`) |
| `usPCIETableOffset` | 6 | la mitad son del header **Tonga/Vega10**, que es otra estructura |
| `phm_ppt_v1_pcie_table` | 16 | el tipo ya convertido, no el VBIOS |

Del byte del VBIOS a `phm_ppt_v1_pcie_table` hay **un solo camino** para mi ASIC:
`process_pptables_v1_0.c:523-558`.

Eso **refuta** la explicación de `550` número 2 («rareza que no duele»): si el layout
estuviera mal, **nada lo compensaría**, porque no hay un segundo lector.

## El discriminante es robusto, no un accidente afilado

La duda correcta sobre un discriminante es si funciona por casualidad. Probé las
tres alineaciones que caben en 2 bytes de incertidumbre:

| `entries` @ | i=0 | i=1 | i=2 | carriles 1..16 | relojes 1..400 MHz |
|---|---|---|---|---|---|
| **2** | gen=0, lanes=8, 2812 | gen=0, lanes=8, 26100 | gen=2, lanes=8, 26100 | **sí** | **sí** |
| 3 | gen=8, lanes=0, 10 | gen=8, lanes=0, 33554533 | gen=8, lanes=0, 2650800229 | no | no |
| 4 | gen=0, lanes=0, 134217728 | gen=0, lanes=0, 134348800 | gen=0, lanes=0, 10354688 | **no** | no |

**Solo una de las tres pasa las dos comprobaciones.** El discriminante no es un
filo: dos de tres lecturas son basura en ambos campos a la vez.

El criterio que uso es **el número de carriles**, porque **cero carriles no es un
ancho de enlace posible**. Los relojes son un refuerzo: 26100 kHz es el reloj de
referencia PCIe de manual, y 2812 kHz encaja con que esa entrada sea la de ULV, que
el propio código trata aparte (`:536-537`).

## Descarté la alternativa de que la tabla empiece 2 bytes antes

La objeción natural: si `usPCIETableOffset` valiera **754** en vez de 752, la tabla
empezaría 2 bytes después y `entries` caería en 4, y todo encajaría.

**No encaja**, y lo comprobé:

```
752 -> revId=1  numEntries=3     <- Polaris10, registro de 8 bytes
754 -> revId=0  numEntries=8     <- tomaria la RAMA TONGA (ucRevId < 1)
```

Con `revId = 0` el código entra por la rama Tonga de `:487`, que usa registros de
**4 bytes**, y la lectura da:

```
i=0  gen=0   lanes=8
i=1  gen=252 lanes=10     <- 252 no es un indice de generacion PCIe
i=2  gen=0   lanes=8
```

**`gen = 252` no es un índice de generación plausible.** Así que la lectura de 752 es
la correcta, y el registro **es de 8 bytes** (`ATOM_Polaris10_PCIE_Record`), solo que
empaquetado en offset 2.

Y `usPCIETableOffset` en 61 es sólido: los USHORT de `:59`, `:61` y `:63` son
contiguos, y los dos campos anteriores están **confirmados por dos anclas
independientes** (`0x9D15` en 45 y `0x9EAB` en 57). No hay hueco para un error de
2 bytes entre `:59` y `:61`.

## La causa, y por qué el compilador la introduce

```c
typedef struct _ATOM_Polaris10_PCIE_Record {
	UCHAR ucPCIEGenSpeed;    /* @0 */
	UCHAR usPCIELaneWidth;   /* @1, DECLARADO UCHAR */
	UCHAR ucReserved[2];     /* @2 */
	ULONG ulPCIE_Sclk;       /* @4  <-- alinea a 4 */
} ATOM_Polaris10_PCIE_Record;

typedef struct _ATOM_Polaris10_PCIE_Table {
	UCHAR ucRevId;           /* @0 */
	UCHAR ucNumEntries;      /* @1 */
	ATOM_Polaris10_PCIE_Record entries[];   /* @4 por alineacion */
} ATOM_Polaris10_PCIE_Table;
```

El `ULONG` del registro le da alineación 4, así que el compilador **inserta 2 bytes
de relleno** entre `ucNumEntries` y `entries`. Medido: `sizeof(Record)` = 8,
`sizeof(Table)` = 4, `offsetof(entries)` = **4**.

El VBIOS no tiene ese relleno. **El formato ATOM es empaquetado y el `struct` de C
no lo es**, y el macro que usa el código resuelve el offset a través del compilador:

```c
#define GET_FLEXIBLE_ARRAY_MEMBER_ADDR(type, member, ptr, n) \
	(type *)((char *)&(ptr)->member + (sizeof(type) * (n)))
```

Nótese que **`ATOM_Tonga_PCIE_Record` no tiene `ULONG`** — es `{UCHAR, UCHAR,
UCHAR[2]}`, alineación 1, y sus entradas **sí** caen en offset 2. El problema
aparece **exactamente al añadir el `ULONG` de `ulPCIE_Sclk` en Polaris10**.

Eso explica por qué a nadie le ha dado problemas en Tonga, y por qué el mismo código
puede estar mal solo en Polaris10.

## Lo que NO afirmo, y es lo importante

**NO afirmo que esto rompa el PCIe en mi placa.** Eso es `RUNTIME_MISSING`:
`B_RUNTIME = NOT_EXECUTED`, y sigue haciendo falta
`Autorizo WRITE_EXECUTION para B_EXPERIMENT`.

El impacto posible, si se confirma, es acotable pero **no lo he medido**:

- `smu7_setup_default_pcie_table:673` lee `ucPCIEGenSpeed` y `usPCIELaneWidth` para
  llamar a `get_pcie_gen_support` y `get_pcie_lane_support`. Con la lectura
  desplazada, `usPCIELaneWidth` valdría 0, y `get_pcie_lane_support(cap, 0)`
  probablemente devuelva el mínimo en vez de x8.
- Eso affectaría a `data->dpm_table.pcie_speed_table`, que **no** es la tabla DPM de
  1776 B que vengo midiendo. Es otra estructura, en `struct smu7_hwmgr`.
- `bif_sclk_table` **sí** depende de esta lectura, porque `ulPCIE_Sclk` está en el
  registro y también se desplaza. Con `entries@4` los relojes serían
  134217728 / 134348800 / 10354688 kHz, y la búsqueda de divisor DFS de `:2094`
  pediría divisores para relojes absurdos.

**La última es la que toca mi rama.** No puedo afirmar que la puerta de `:2095` falle,
porque `ComputeMemoryEnginePLL` **no está en mi corpus** y no sé cómo responde a una
entrada absurda. Podría devolver 0 con cualquier cosa.

Lo que sí es **`PROVEN`**:

- Mi VBIOS tiene la tabla en `0x9EFA`, rev 1, `ucNumEntries = 3`.
- Los datos legibles están en `base + 2 + 8*i`, y **solo ahí**.
- `offsetof(entries)` en el kernel es **4**.
- **No hay segundo lector** en 2689 ficheros.

Lo que es **`NOT_DETERMINED`**: el efecto en runtime.

## Un detalle que salió de paso y no es menor

```c
UCHAR usPCIELaneWidth;     /* declarado UCHAR, nombre de USHORT */
...
pcie_record->lane_width = le16_to_cpu(atom_pcie_record->usPCIELaneWidth);   /* :554 */
```

Un campo de **1 byte** leído con `le16_to_cpu`. No rompe nada —`le16_to_cpu` devuelve
`int` y solo promociona— pero es un **desajuste de tipo declarado**, y significa que
el campo no puede llevar anchos de carril por encima de 255. Irrelevante aquí, pero
indica que el registro se **modificó sin revisar** el resto.

## Lo que esto cierra, y lo que abre

**Cierra**: el discriminante de `550`. El desacuerdo de 2 bytes entre el VBIOS y el
`struct` está **`PROVEN`**, y ya no es «quizá mi lectura».

**Abre**: una pregunta más grande y más útil, que es la que importa para el objetivo.

**`sizeof` de un struct de C y el formato del VBIOS no coinciden, y el código usa el
del C para leer bytes que otro escribió empaquetados.** Eso no es un caso aislado: es
una **clase de defecto** que solo se ve comparando el formato empaquetado con lo que
el compilador deduce. Y hay 98 campos en la tabla DPM, 95 en el rango copiado, más
la tabla SCLK, más la tabla AVFS, más PowerTune, más la PCIe: **cinco tablas ya
decodificadas, y solo en esta appeared la discrepancia** porque en las otras leí los
campos y los valores que me interesaban, no la alineación.

La pregunta que vale es: **¿cuántas de mis decodificaciones dependen de que el
`sizeof` compilado coincida con el formato del VBIOS?** Porque las que he hecho con
gcc y las que he hecho leyendo offsets a mano **tienen fiabilidad distinta**, y solo
he verificado la coincidencia en dos casos.

## Frontier siguiente

**Medir, para cada tabla ya decodificada, si `sizeof` del struct coincide con el
formato empaquetado del VBIOS.** Es el mismo método de esta iteración, aplicado a las
cinco tablas, y es la generalización que este hallazgo justifica.

Concreto y barato: para cada struct, comparar `sizeof` con `sizeof` recalculado
**sin alineación** (`__attribute__((packed))`), y ver en cuáles difieren. Los que
difieren son los que necesitan lectura empaquetada, y ahí el `offsetof` que dio gcc
**no sirve**.

Criterio de cierre: una tabla de cinco filas —tabla, `sizeof` con alineación,
`sizeof` empaquetado, y si difieren— y con ella queda **corregido o invalidado** el
layout que usé para la tabla DPM de 1776 B, que es la que sostiene el hallazgo `502`.

Ese es el riesgo real de `502`: **si `SMU74_Discrete_DpmTable` tiene un `ULONG` en
algún sitio antes de `SystemFlags`, mi `offsetof(SystemFlags) = 108` y mi `108..1883`
pueden estar desplazados**, y con ellos los 95 campos y las puertas que conté. No lo
he comprobado, y es el punto que sostiene todo lo demás.
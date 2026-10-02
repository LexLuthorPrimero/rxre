# 051 · El ASIC ID se lee del PCI config space, no de un registro: hay una vía read-only

`CLASSIFICATION=DOCUMENTATION` · `TRACK=STATIC`+`RUNTIME_READ`
`WORK_CLASS=READ_ONLY/EVIDENCE` · `WRITE_EXECUTION=NONE` · `MODIFICATIONS=0`
`RUNTIME=READ_ONLY (config space)` · `GPU INTACTA`
`CONTINUES=050` · `ABRE=la frontera GFX_HWIP con una via que 001:253 no considero`

## Cuestión principal

`001:253` dice que la única forma válida de establecer `GFX_HWIP` es *"leer un
registro ASIC identificador a través de `umr`"*, y `050` mostró que `hwmgr.c`
no está en el corpus. **¿Hay otra vía?**

## Criterio de terminación

Determinar de dónde lee el driver el ASIC ID, y si esa fuente está disponible
sin hardware. **Cumplido: es el PCI config space, y está en `/sys`.**

## La respuesta

`amdgpu.h:770`:

```c
/* polaris12 kickers */
#define ASICID_IS_P23(did, rid)		(((did == 0x6987) && \
					 ((rid == 0xC0) || (rid == 0xC1) || \
					  (rid == 0xC3) || (rid == 0xC7))) || \
					 ((did == 0x6981) && \
					 ((rid == 0x00) || (rid == 0x01) || \
					  (rid == 0x10))))
```

Y el uso que hace el driver:

```c
/* polaris10_smumgr.c:1801 */
((hwmgr->chip_id == CHIP_POLARIS12) && !ASICID_IS_P23(adev->pdev->device, adev->pdev->revision))
```

`adev->pdev->device` y `adev->pdev->revision` son **campos del `struct pci_dev`**.
No hay lectura de registro MMIO en esa expresión: es el ID del PCI.

## Y el ID de esta placa

```
$ cat /sys/bus/pci/devices/0000:01:00.0/config   (bytes 0x00-0x0b)
  vendor:device = 1002:699f   revision = c7
  class         = 030000      subsystem = 1002:0b04
  lspci: Lexa PRO [Radeon 540/550] [1002:699f] (rev c7)
```

## Y aquí está el dato que no encaja

`0x699f` **no está** en la macro. `ASICID_IS_P23` acepta:

```
did ∈ {0x6987, 0x6981}
```

Y esta placa es **`0x699f`**. Con revisión `0xc7`, que sí es una de las que la
macro acepta para `0x6987`.

Es decir: **el `device` ID de esta placa no está en la lista que el propio
driver usa para identificarla como Polaris12 "kicker"**.

## Lo que eso significa, y lo que no

**NO significa** que la placa no sea Polaris12. El identificador textual de
PCI en la base de datos de `lspci` de esta host la nombra *"Lexa PRO [Radeon
540/540X/550/550X / RX 540X/550]"*, y Lexa PRO **es** Polaris12 por catálogo.

Y el corpus lleva 37 hallazgos tratándola como Polaris12 sin que ninguno haya
dudado.

**SÍ significa** una de estas dos cosas, y no sé cuál:

1. `0x699f` es un **`device` ID posterior** a la versión de este kernel, y el
   macro no se actualizó. Entonces el módulo la trata con la ruta que le
   corresponde por otro camino.
2. El enum interno `CHIP_POLARIS12` se asigna por una tabla que no es
   `ASICID_IS_P23`, y el macro es solo un caso particular — *"polaris12
   kickers"* sugiere literalmente eso: los casos *especiales*.

La pista está en el propio comentario: **`/* polaris12 kickers */`**. Un
"kicker" es una corrección para un caso raro, no el camino principal. La
pregunta correcta no es "¿por qué no está `0x699f`?" sino **"¿qué tabla
asigna `CHIP_POLARIS12`?"**, y esa tabla está en el fichero ausente
(`hwmgr.c`, función `asic_type_from_chip_id`).

## Por qué esto reabre la frontera

`001:253` descartó el camino del PCI config space con un argumento que ahora
resulta incompleto. Ese argumento era:

> `AGENTS.md` §3 prohíbe derivar el número de generación de una `PCI_IDENTITY`
> o de un nombre de driver.

Y sigue siendo cierto: **`PCI_IDENTITY` no dice qué generación de IP tiene el
GFX**. Pero sí dice **qué chip es**, y el chip determina la generación. Lo que
`PCI_IDENTITY` no puede dar es la *versión de IP* del bloque GFX, que es una
cosa distinta del nombre del ASIC.

La distinción que faltaba:

| pregunta | fuente | estado |
|---|---|---|
| ¿qué ASIC es? | PCI config space, `/sys/.../config` | `PROVEN` — `1002:699f rev c7` |
| ¿qué `chip_id` le asigna el driver? | tabla en `hwmgr.c` | `NOT_IN_CORPUS` |
| ¿qué generación de IP tiene el GFX? | `GFX_HWIP` | `NOT_DETERMINED` |

La primera está resuelta y es de lectura. La segunda falta por el subtree. La
tercera sigue siendo la frontera real.

**Es decir: la frontera no se cierra, pero se acota.** Deja de necesitar UMR
para el ASIC ID y pasa a necesitar el fichero para el mapeo, y el `GFX_HWIP`
sigue siendo `NOT_DETERMINED` por una razón distinta y mejor entendu.

## El error que cometí al leer el config space

Primero leí el device ID en el offset `0x08` y obtuve `1002:0300`. `0x0300` no
es un device ID: es el **class code** (VGA controller). El layout del config
space es:

```
0x00 vendor ID   0x02 device ID   0x04 command
0x06 status      0x08 revision    0x09 class code (3 bytes)
```

Lo escribí mal una vez y creí durante dos llamadas que el device ID era
`0x0300` y que la placa no encajaba en la macro. **Si no llego a contrastar con
`lspci`, habría documentado un ASIC ID falso.**

La lección es la de siempre y la tercera vez: **un valor leído de hardware sin
un valor competidor al lado que lo contradiga**. `lspci` es ese competidor, y
estaba disponible todo el tiempo.

## Clasificación

| afirmación | estado |
|---|---|
| El ASIC ID se lee de `adev->pdev->device` / `->revision` | `PROVEN` — `polaris10_smumgr.c:1801` |
| Eso es el PCI config space, no un registro MMIO | `PROVEN` — `struct pci_dev` |
| El ID de esta placa es `1002:699f` rev `c7` | `OBSERVED` — config space, read-only |
| `ASICID_IS_P23` acepta `did` 0x6987 y 0x6981 | `PROVEN` — `amdgpu.h:770` |
| `0x699f` **no** está en esa lista | `OBSERVED` |
| Que la placa sea Polaris12 | `CORROBORATED` — `lspci` la nombra Lexa PRO |
| Que `chip_id` sea `CHIP_POLARIS12` | `CORROBORATED` — `polaris10_smumgr.c:793` |
| La tabla que asigna `chip_id` | `NOT_IN_CORPUS` — está en `hwmgr.c` |
| Que `0x699f` sea un ID posterior al kernel | `HYPOTHESIS` |
| `GFX_HWIP` | `NOT_DETERMINED` — sigue sin fuente en el corpus |

## Confounders

- **No he buscado la tabla en el binario.** Se puede: el `.ko` cargado tiene el
  código de máquina de `asic_type_from_chip_id`, y desensamblarlo daría la
  tabla sin necesitar el fuente. No lo he hecho; es trabajo de la próxima ronda.
- **`lspci` nombra "Lexa PRO", y yo traduzco eso a Polaris12.** La traducción
  viene de la base de datos de pci.ids de esta host, no del corpus.
- **Leí 12 bytes del config space.** Campos como el BAR sí los lee el driver de
  ahí, pero no los he verificado.
- **El argumento de `001` no era erróneo**, era incompleto: `PCI_IDENTITY` no da
  la generación de IP. Lo que añado es que sí da el ASIC, que es otra cosa.

## Desfalsificación

- **(a)** El ASIC ID viene de `pdev` → refutable con `polaris10_smumgr.c:1801`.
- **(b)** `0x699f` no está en la macro → refutable con la lista impresa de la
  propia macro.
- **(c)** El device ID es `0x699f` → refutable con `lspci -nn`, que coincide.
- **(d)** La placa es Polaris12 → refutable con la base de datos de pci.ids; es
  lo que dice "Lexa PRO".

## UNLOCKS

- **La frontera `GFX_HWIP` queda acotada en tres partes**, y solo una necesita
  UMR: el ASIC está leído, falta el mapeo a `chip_id` (subtree), y la
  generación de IP sigue abierta por otra razón.
- **Aparece una vía read-only que nadie había considerado**: desensamblar
  `asic_type_from_chip_id` del `.ko` cargado. Da la tabla sin el fuente.
- **El subtree ausente tiene una alternativa**: el binario está aquí.

## Evidencia

```
amdgpu.h:770            ASICID_IS_P23: did ∈ {0x6987, 0x6981}
polaris10_smumgr.c:1801 ASICID_IS_P23(adev->pdev->device, adev->pdev->revision)

/sys/bus/pci/devices/0000:01:00.0/config, bytes 0x00-0x2f
  vendor:device = 1002:699f   revision = c7
  class         = 030000      subsystem = 1002:0b04

lspci -nn -s 01:00.0
  Lexa PRO [Radeon 540/540X/550/550X / RX 540X/550/550X] [1002:699f] (rev c7)

  ASICID_IS_P23(0x699f, 0xc7)  ->  False
```

`WRITE_EXECUTION=NONE`. `MODIFICATIONS=0`. `GPU INTACTA`.
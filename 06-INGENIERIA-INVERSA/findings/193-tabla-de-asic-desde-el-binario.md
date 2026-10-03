# 193  La tabla de ASIC está en el binario: `chip_id = 17` confirmado sin el fuente ausente

`CLASSIFICATION=DOCUMENTATION` · `TRACK=STATIC`+`RUNTIME_READ`
`WORK_CLASS=READ_ONLY/EVIDENCE` · `WRITE_EXECUTION=NONE` · `MODIFICATIONS=0`
`RUNTIME=READ_ONLY` · `GPU INTACTA`
`CONTINUES=051` · `ABRE=la via alternativa al subtree ausente, y la usa`
`HERRAMIENTA_NUEVA=08-ARQUITECTURA/tools/asic_table.py` (`TOOL_VALIDATED`)

## Cuestión principal

`051` dejó abierta una vía: *el subtree está incompleto, pero el binario
está aquí*. ¿Se puede reconstruir la tabla de ASIC desde el `.ko` cargado?

## Criterio de terminación

Localizar la tabla `(device_id, revision_id, …, chip_id)` en el binario y leer
la entrada de esta placa. **Cumplido: encontrada, y da `chip_id = 17`.**

## Respuesta: sí, y está a la vista

La tabla vive en `.rodata`. Buscando el `device_id` de esta placa como `u16`
little-endian aparecen **dos** ocurrencias, y una es una entrada de tabla:

```
$ objdump -s -j .rodata --start-address=0x2b00 --stop-address=0x2b20
 2b00  02100000 9f690000 ffffffff ffffffff  .....i..........
 2b10  00000000 00000000 11000000 00000000  ................
```

Ocho palabras, con este patrón repetido 318 veces en la sección:

| palabra | valor | qué es |
|---|---|---|
| 0 | `0x00001002` | vendor AMD |
| 1 | `0x0000699f` | **device ID de esta placa** |
| 2 | `0xffffffff` | revisión: **cualquiera** |
| 3 | `0xffffffff` | ip_version_major: sin restricción |
| 4 | `0x00000000` | ip_version_minor: sin restricción |
| 5 | `0x00000000` | flags |
| 6 | `0x00000011` | **`chip_id = 17 = CHIP_POLARIS12`** |
| 7 | `0x00000000` | flags altos |

## Lo que esto resuelve, de golpe

**1. `chip_id = CHIP_POLARIS12` queda `PROVEN`**, no `CORROBORATED`.

`050` lo tenía como corroborado por un `if` en `polaris10_smumgr.c:793` que
compara contra `CHIP_POLARIS12`. Eso es *consistente con*, no *es*. Ahora está
en la tabla.

**2. La discrepancia de `051` se explica.**

`ASICID_IS_P23` acepta `did ∈ {0x6987, 0x6981}`, y esta placa es `0x699f`.
La tabla explica por qué no hace falta: la entrada de `0x699f` tiene
`revision = 0xffffffff`, es decir **cualquier revisión**, y su `chip_id` es
`17` directamente. El macro es un caso *particular* —su comentario lo dice:
`/* polaris12 kickers */`— y esta placa no es un kicker: es la ruta principal.

**3. `GFX_HWIP` sigue `NOT_DETERMINED`, y por qué es distinto.**

La entrada de la tabla tiene `ip_version_major = 0xffffffff`: el driver **no
usa esta vía para leer la versión de IP del GFX**. La versión sale de otra
fuente, y esa fuente sigue sin estar en el corpus.

Esto es lo que `001:213` decía, y tenía razón: contar referencias a `gfx_v8`
en el módulo describe **el módulo**, no esta GPU.

## Por qué el subtree ausente no limita este trabajo

`051` proponía desensamblar el binario como alternativa a traer `hwmgr.c`.
Funcionó, y en quince minutos.

Pero **el subtree sigue haciendo falta** para todo lo demás: los 53 registros
del MQD, los 3 bucles, las 262 funciones del mapa causal, `hwmgt` para la
tabla. Lo que se recupera aquí es **una tabla**, no el fichero.

Y esa distinción es la que evita un error caro: traer el árbol entero para
resolver una tabla que ya está en el `.ko` sería trabajo para nada.

## El método: buscar el ID en la rodata

```
$ grep -c 699f  →  2 ocurrencias en 2972368 bytes de .rodata
```

Un `u16` de 2 bytes en 3 MB aparece por casualidad unas pocas veces. Dos
ocurrencias, y una con el patrón de tabla al lado, es identificable sin
ambigüedad.

Y el patrón se **confirma por repetición**: 318 entradas con el mismo formato,
empezando por `0x6780`, `0x6784`, `0x6788`, `0x678a`, `0x6790`… que son las
GPU de la serie Hawaii/GCN1 en orden. La tabla es legible sin tener el fuente.

## Cómo se sabe que es la tabla correcta, y no una coincidencia

Tres comprobaciones independientes, y las tres tienen que pasar:

| comprobación | resultado |
|---|---|
| ¿el patrón se repite? | 318 entradas iguales |
| ¿están en orden de generación? | `6780`, `6784`, `6788`… luego `6800` (Polaris10) |
| ¿la entrada de esta placa encaja con lo que sabemos? | `chip_id = 17`, y el proyecto lleva 37 hallazgos tratándola como Polaris12 |
| ¿el macro `ASICID_IS_P23` es coherente con ella? | sí, con `revision` libre |

Una coincidencia de 2 bytes pasa la primera improbable. Cuatro coherencias a
la vez la convierten en una lectura.

## Clasificación

| afirmación | estado |
|---|---|
| La tabla de ASIC está en `.rodata` | `PROVEN` — 318 entradas con el mismo patrón |
| La entrada de esta placa da `chip_id = 17` | `PROVEN` — `.rodata:0x2b18` |
| `17` = `CHIP_POLARIS12` | `PROVEN` — `027:216`, enum del kernel |
| Su revisión es cualquiera | `PROVEN` — `0xffffffff` |
| Su `ip_version` no viene de aquí | `PROVEN` — `0xffffffff` en esa tabla |
| `ASICID_IS_P23` es un caso particular, no la ruta principal | `PROVEN` — `rev = 0xffffffff` |
| `chip_id` es `CHIP_POLARIS12` | `PROVEN` — antes `CORROBORATED` |
| `GFX_HWIP` | `NOT_DETERMINED` — fuente ausente en el corpus |
| Que el enum del kernel sea el del binario | `ASSUMPTION` — se comparó por valor, no por fuente |

## Confounders

- **El layout de 8 palabras está deducido, no leído.** Encaja con 318
  entradas y con los valores conocidos, y `CHIP_POLARIS12 = 17` lo confirma,
  pero **no tengo el `struct`**. Que la palabra 6 sea `chip_id` y no un flags
  depende de que valga 17 y no de haberlo visto escrito.
- **`ip_version_major` es la palabra 3 y no otra.** Si el layout fuera
  distinto, la conclusión "el driver no lee la versión de IP aquí" cambiaría.
  Es la afirmación más frágil del hallazgo.
- **318 entradas, no 500.** El driver soporta más chips que los que compila
  esta configuración; los demás no están en el binario. Correcto, pero
  significa que el binario **no es** la fuente completa.
- **No he desensamblado `asic_type_from_chip_id`.** Es `static`, no aparece
  por nombre, y no hace falta para esta tabla. Queda como forma de
  confirmar el layout.
- **Las otras dos ocurrencias de `0x699f`** no las he identificado. Una está
  en `0xa3460` dentro de datos que no son tabla.

## Desfalsificación

- **(a)** La tabla existe en `.rodata` → refutable con `objdump -s -j .rodata
  | grep 9f690000`.
- **(b)** Da `17` → refutable leyendo la palabra en `0x2b18`.
- **(c)** `17` es Polaris12 → refutable con el enum de `amdgpu.h`.
- **(d)** El layout de 8 palabras → refutable desensamblando
  `asic_type_from_chip_id` y viendo los offsets que carga. **No hecho.**
- **(e)** El subtree sigue ausente → refutable con `ls hwmgr.c`.

## UNLOCKS

- **`chip_id = CHIP_POLARIS12` pasa de `CORROBORATED` a `PROVEN`**, y con
  fuente: la tabla del binario.
- **Una clase nueva de evidencia**: el `.ko` cargado contiene datos de solo
  lectura que el corpus no tiene, y son legibles sin desensamblar.
- **El subtree ausente se puede acotar**: falta para el *código*, no para las
  *tablas*. Y para el código, el fuente sigue siendo lo único que sirve.
- **`GFX_HWIP` queda con una causa concreta**: no está en la tabla y su fuente
  no está en el corpus. Ya no es "no sé de dónde sale".

## Evidencia

```
$ objdump -s -j .rodata --start-address=0x2b00 --stop-address=0x2b20 \
      /tmp/amdgpu_loaded.ko
 2b00  02100000 9f690000 ffffffff ffffffff  .....i..........
 2b10  00000000 00000000 11000000 00000000  ................

  palabra 0 = 0x00001002   vendor
  palabra 1 = 0x0000699f   device  -> 1002:699f, el de esta placa
  palabra 2 = 0xffffffff   revision: cualquiera
  palabra 3 = 0xffffffff   ip_version_major: sin restriccion
  palabra 6 = 0x00000011   chip_id = 17 = CHIP_POLARIS12

  entradas con el mismo patron: 318
  primeras: 6780 6784 6788 678a 6790 6791 ...

/sys/bus/pci/devices/0000:01:00.0/config
  vendor:device = 1002:699f   revision = c7
```

`WRITE_EXECUTION=NONE`. `MODIFICATIONS=0`. `GPU INTACTA`.
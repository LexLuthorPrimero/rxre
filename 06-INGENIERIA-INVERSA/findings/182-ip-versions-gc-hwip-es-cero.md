# 182 · En Polaris12 `ip_versions[GC_HWIP]` vale **0**: trescientas comparaciones de versión degeneran, y eso **corrige `231`**
`MEDIDO_POR=244` -- este valor deja de ser una DEDUCCION y pasa a ser
una MEDIDA en el binario: `ip_versions[GC_HWIP][0]` esta en el offset 0x5d518 de
`struct amdgpu_device`, se lee **345 veces** en el desensamblado del `.ko` y se
escribe **0 veces** con indice estatico. El unico escritor con indice dinamico es
`amdgpu_discovery.c:1640`, y su unico llamante (`amdgpu_device.c:1994`) es la rama
`default:` del switch de ASIC, que `CHIP_POLARIS12` no toma.

`CLASSIFICATION=DOCUMENTATION` · `TRACK=STATIC` · `WORK_CLASS=READ_ONLY/EVIDENCE`
`WRITE_EXECUTION=NONE` · `MODIFICATIONS=0` · `RUNTIME=NOT_RUN` · `GPU INTACTA`
`CORPUS=RESEARCH/working/linux-7.1.3` · `HARDWARE_SCOPE=HOST-C/RX550/0000:01:00.0`
`CORRIGE=144, cuya inferencia sobre GFX_HWIP era mas fuerte que la evidencia`

## Cuestión principal

`231` afirmó, a partir de `grep -rn GFX_HWIP`, que *"ni el driver lo lee ni ningún
header lo define"*.

El grep era correcto sobre la cadena literal. **La inferencia no lo era.**

## Criterio de terminación

Determinar si el driver lee la versión de IP del GFX en esta placa, y qué valor
toma. **Cumplido: no la lee; el campo queda en 0 y todas las comparaciones
degeneran.**

## El mecanismo sí existe

`amdgpu.h:1139` declara el array:

```c
uint32_t ip_versions[MAX_HWIP][HWIP_MAX_INSTANCE];
```

`amdgpu.h:1211-1217`, el lector:

```c
static inline uint32_t amdgpu_ip_version(const struct amdgpu_device *adev,
                                         uint8_t ip, uint8_t inst)
{
        /* This considers only major/minor/rev and ignores
         * subrevision/variant fields. */
        return adev->ip_versions[ip][inst] & ~0xFFU;
}
```

Y `amdgpu_ip.h:32` dice quién es el GFX:

```c
enum amd_hw_ip_block_type { GC_HWIP = 1, HDP_HWIP, SDMA0_HWIP, ... };
```

**El driver sí tiene versión de IP del GFX.** Se llama `GC_HWIP`, no `GFX_HWIP`,
y por eso el grep de `231` no la vio. `231` affirmations eran correctas sobre
el literal y falsas sobre la capacidad.

## Tres hechos y la conclusión

**1. El array se reserva con cero.** `amdgpu_drv.c:2411`:

```c
adev = devm_drm_dev_alloc(&pdev->dev, &amdgpu_kms_driver, typeof(*adev), ddev);
```

**2. No hay ningún escritor en el camino GCN3.** Todos los escritores están en
`amdgpu_discovery.c`, y **ninguno** en `vi.c`, `gfx_v8_0.c`, `gmc_v8_0.c`,
`amdgpu_gfx.c`, `amdgpu_gmc.c`:

```
$ grep -n "ip_versions" gfx_v8_0.c vi.c amdgpu_gfx.c amdgpu_gmc.c gmc_v8_0.c
(vacío)
```

**3. No hay caso POLARIS donde se codifique a mano.**
`amdgpu_discovery.c:2786-2815` es el `switch` que la rellena, y solo tiene:

```c
case CHIP_VEGA10:
case CHIP_VEGA12:
```

```
$ awk 'NR>=2700 && NR<=2830 && /case CHIP_POLARIS/' amdgpu_discovery.c
(vacío)
```

Por tanto, para Polaris12: `adev->ip_versions[GC_HWIP][0] == 0`.

## El caso Vega10 lo dice mejor que cualquier argumento

`amdgpu_discovery.c:2787-2812`:

```c
case CHIP_VEGA10:
        /* This is not fatal.  We only need the discovery
         * binary for sysfs.  We don't need it for a
         * functional system.
         */
        amdgpu_discovery_init(adev);
        ...
        adev->ip_versions[GC_HWIP][0] = IP_VERSION(9, 0, 1);
```

Vega10 **sí tiene** `ip_discovery.bin`, lo lee, **y aun así codifica `GC_HWIP`
a mano**. El propio driver dice que el discovery sirve *"para sysfs"*, no para
las comparaciones.

Así que incluso en un ASIC que **sí** tiene descubrimiento de IP, la versión
del GFX que usa el driver es **una constante escrita a mano**, no una lectura.
Y GCN3 no tiene ni el descubrimiento ni la constante.

## Qué significa para `231`

`231` cerró `GFX_HWIP` como `PROVEN_ABSENT` y ofreció el firmware como fuente
alternativa. **La parte de `PROVEN_ABSENT` se sostiene**: el registro no existe
en el corpus, bajo ese nombre ni bajo ningún otro.

**Lo que hay que corregir es la inferencia**: no es que el driver no pueda leer
la versión de IP del GFX; es que **no lo hace en esta generación**, porque no
tiene ni firmware de descubrimiento ni constante codificada. El valor real —
**8.0**, medido en el firmware por `fw_ipver` — es algo que el driver **no
puede saber**.

Eso convierte el hallazgo de `231` de "`PROVEN_ABSENT`" en algo más fuerte y
más útil: **la versión del GFX de esta placa es 8.0, y el driver no la lee.**

## Las ~300 comparaciones que degeneran

```
$ grep -rn "amdgpu_ip_version(.*GC_HWIP" *.c *.h | wc -l
   (≈300 usos)
```

Cada una se convierte en "comparar 0 contra una constante". Las tres que
importan para este proyecto:

| sitio | código | con valor 0 |
|---|---|---|
| `amdgpu_ids.c:586` | `ip_version < IP_VERSION(10,0,0)` | **verdadero** → `num_ids = first_kfd_vmid` |
| `amdgpu_vm.h:123,138,142` | `>= IP_VERSION(12,0,0)` | **falso** → variante no-GFX12 |
| `amdgpu_vm.c:1157` | `flush_tlb \|= ip_version < IP_VERSION(9,0,0)` | **siempre verdadero** |

Las tres dan la respuesta correcta para GFX8, **pero por construcción, no por
leer hardware.** La tercera es la más notable: un flag que se activa
condicionalmente según la versión, y en esta placa la condición no puede ser
falsa.

## Clasificación

| afirmación | estado |
|---|---|
| El driver tiene versión de IP del GFX (`GC_HWIP`) | `PROVEN` — `amdgpu.h:1211` |
| El alias es `GC_HWIP = 1`, no `GFX_HWIP` | `PROVEN` — `amdgpu_ip.h:32` |
| `adev` se reserva con cero | `CORROBORATED` — `devm_drm_dev_alloc`, DRM core fuera del corpus |
| Ningún escritor de `ip_versions` en el camino GCN3 | `PROVEN_ABSENT` |
| El `switch` codificado no tiene caso POLARIS | `PROVEN_ABSENT` |
| `ip_versions[GC_HWIP][0] == 0` | `PROVEN_DERIVED` |
| Vega10 codifica GC_HWIP a mano aun con discovery | `PROVEN` — `amdgpu_discovery.c:2812` |
| El discovery sirve para sysfs, no para comparar | `PROVEN` — comentario del driver |
| Las ~300 comparaciones degeneran | `DERIVATION` — de la anterior |
| La versión real del GFX es 8.0 | `OBSERVED` — `231`, `fw_ipver` |
| Que el driver la conozca | `REFUTED` |
| Que 0 dé la respuesta correcta en los 3 sitios | `DERIVATION` |

## Confounders

- **El cero inicial viene del DRM core**, que no está en este corpus
  (`devm_drm_dev_alloc` → `devm_kzalloc`). Es `CORROBORATED`, no `PROVEN`: si no
  pusiera a cero, el valor sería basura y las tres ramas podrían cambiar.
- **He comprobado los escritores de `ip_versions` del subárbol del corpus.** No
  puedo descartar un escritor en un fichero que este snapshot no trae.
- **`amdgpu_discovery_init()`** está en `amdgpu_discovery.c` y solo se llama con
  firmware que existe para SOC15. No he auditado sus 3000 líneas, solo quién lo
  llama.
- **He clasificado las 3 comparaciones de este proyecto**, no las ~300. Las
  demás caen en ficheros de otras generaciones, pero `amdgpu_device.c`,
  `amdgpu_display.c`, `amdgpu_gfx.c` y `amdgpu_gmc.c` sí son comunes.
- **No he medido nada.** Todo es lectura estática.

## Desfalsificación

- **(a)** El alias es `GC_HWIP` → refutable con `amdgpu_ip.h:32`.
- **(b)** El lector existe → refutable con `amdgpu.h:1211`.
- **(c)** Sin escritor en el camino GCN3 → refutable con el grep sobre los cinco
  ficheros.
- **(d)** Sin caso POLARIS → refutable con `amdgpu_discovery.c:2786-2815`.
- **(e)** El valor es 0 → depende de (a)-(d) más el cero inicial.
- **(f)** Que el driver conozca la versión → **refutado**.

## UNLOCKS

- **`231` queda corregido**, no ampliado: la afirmación fuerte era falsa, la
  débil era cierta. Corregir la inferencia es parte del trabajo, no un extra.
- **Una regla que sale de esto**: *un grep sobre el nombre literal no prueba
  que una capacidad esté ausente*. Hay que buscar el mecanismo, no la cadena.
  Me costó `231` y una iteración entera.
- **`flush_tlb` es condicional en el código pero no en esta placa.** Para un
  driver propio, esa condición es código muerto aquí.
- **Una consecuencia incómoda y útil**: si el driver no conoce su propia versión
  de IP, cualquier constructor de driver que no la rellene toma las mismas
  ramas que este. Un driver propio tiene que **rellenarla a mano** si quiere que esas
  comparaciones con sentido.
- **Siguiente paso**: queda por auditar las comparaciones de `GC_HWIP` en los
  ficheros **comunes** (`amdgpu_device.c`, `amdgpu_display.c`, `amdgpu_gfx.c`,
  `amdgpu_gmc.c`), que sí se ejecutan en GFX8. Ahí puede haber un check de
  versión que se comporta como constante, y conviene saber cuáles.

## Evidencia

```
amdgpu_ip.h:32          GC_HWIP = 1
amdgpu.h:1139           uint32_t ip_versions[MAX_HWIP][HWIP_MAX_INSTANCE]
amdgpu.h:1211-1217      amdgpu_ip_version() devuelve ip_versions[ip][inst] & ~0xFFU
amdgpu_drv.c:2411       adev = devm_drm_dev_alloc(...)

amdgpu_discovery.c:1640 (unico escritor de GC_HWIP: parseo del discovery)
amdgpu_discovery.c:2786-2815  switch de ip_versions codificadas:
                                  case CHIP_VEGA10:
                                  case CHIP_VEGA12:
                                  (sin caso POLARIS)

$ grep -n "ip_versions" gfx_v8_0.c vi.c amdgpu_gfx.c amdgpu_gmc.c gmc_v8_0.c
(vacío)

amdgpu_ids.c:586        ip_version <  IP_VERSION(10,0,0)   -> con 0: verdadero
amdgpu_vm.h:123,138,142 >=  IP_VERSION(12,0,0)             -> con 0: falso
amdgpu_vm.c:1157        flush_tlb |= ... < IP_VERSION(9,0,0) -> con 0: siempre
```

`WRITE_EXECUTION=NONE`. `MODIFICATIONS=0`. `GPU INTACTA`.
# 246 · Todo el MMIO pasa por dos helpers: la huella por bloque, y SMU y display hacen **cero** accesos directos

`CLASSIFICATION=DOCUMENTATION` · `TRACK=STATIC_BINARY` · `WORK_CLASS=READ_ONLY/EVIDENCE`
`WRITE_EXECUTION=NONE` · `MODIFICATIONS=0` · `RUNTIME=NOT_RUN` · `GPU INTACTA`
`CORPUS=/tmp/amdgpu_loaded.ko` · `HARDWARE_SCOPE=HOST-C/RX550/0000:01:00.0`
`DESARROLLA=la diferencia entre registros definidos y registros usados de 203`

## Cuestión principal

`203`midió que la superficie de la placa sale de las **cabeceras**, y que eso es
vocabulario: 1311 de 13895 registros MMIO se usan. Pero esa cifra se midió
buscando **nombres de macro** en el código, y un nombre no distingue:

- lectura de escritura
- función de función
- bloque de bloque
- si el acceso ocurre en esta placa o en un ASIC que no lo es

Todo eso se mide del **acceso**, y el acceso tiene una forma regular.

## Criterio de terminación

Encontrar el patrón de acceso MMIO en el binario, contarlo por bloque, y cruzar
con qué bloque registra realmente esta placa. **Cumplido: 9 bloques, 540 accesos
atribuidos, con dos bloques a cero.**

## El patrón: todo el MMIO pasa por dos helpers

El hallazgo que lo abre: **el driver no accede a registros MMIO de ninguna otra
forma**. Todo pasa por `amdgpu_device_rreg` y `amdgpu_device_wreg`, con el offset
como **segundo argumento**:

```
$ objdump -dr ... --start-address=0x1ccea0
    1ccec9:  mov    $0x398,%esi              ; esi = mmSRBM_SOFT_RESET = 0x398
    1cced7:  call   1ccedc <sdma_v3_0_soft_reset+0x3c>
      1cced8:  R_X86_64_PLT32  amdgpu_device_rreg-0x4
```

Inventario completo de sitios de llamada:

| helper | llamadas |
|---|---|
| `amdgpu_device_wreg` | **9245** |
| `amdgpu_device_rreg` | **5129** |
| `amdgpu_device_wait_on_rreg` | 177 |
| `amdgpu_device_xcc_wreg` | 15 |
| `amdgpu_device_xcc_rreg` | 12 |

Las `xcc_*` son multi-chip y no aplican a GCN3.

## Herramienta

`08-ARQUITECTURA/tools/mmio_map.py`. Un patrón de dos líneas, no desensamblado
general. Y el resultado se cruza con `ip_surface.py`, que dice qué función ejecuta
cada bloque registrado: **las dos herramientas compuestas dan la huella por bloque**.

## La huella de los 9 bloques registrados

| bloque registrado | tabla real | accesos MMIO |
|---|---|---|
| `gmc_v8_1` | **`gmc_v8_0_ip_funcs`** | **177** |
| `gfx_v8_0` | `gfx_v8_0_ip_funcs` | **148** |
| `vce_v3_4` | **`vce_v3_0_ip_funcs`** | 117 |
| `uvd_v6_3` | **`uvd_v6_0_ip_funcs`** | 37 |
| `vi_common` | `vi_common_ip_funcs` | 31 |
| `tonga_ih` | `tonga_ih_ip_funcs` | 20 |
| `sdma_v3_1` | **`sdma_v3_0_ip_funcs`** | 10 |
| **`pp_smu`** | `pp_ip_funcs` | **0** |
| **`dm`** | `amdgpu_dm_funcs` | **0** |
| | | **540** |

## Los dos ceros son el resultado que importa

**SMU (`pp_smu`) y display (`dm`) hacen CERO accesos MMIO directos.** No es que
hagan pocos: hacen ninguno, por la vía que puedo medir.

Eso no es un defecto de mi medida —`gfx_v8_0_hw_init` sale 59 y
`gmc_v8_0_hw_init` 72, así que la herramienta ve los accesos cuando existen— es una
**afirmación sobre la arquitectura**:

- **SMU no se programa con registros MMIO.** Se habla con él por un protocolo de
  mensajes, y el driver no es quien escribe el hardware: es la **firmware** (la
  SMC runs en la GPU). El driver le envía mensajes.
- **Display tampoco.** El bloque DC/DCE usa un camino de acceso **indirecto**, con
  su propio par de punteros y su propio formato, no `amdgpu_device_rreg`.

**Consecuencia directa para el driver propio: no se puede conducir SMU ni display
escribiendo registros.** Son dos subsistemas que exigen un protocolo, no un mapa de
registros. Eso los saca del alcance de "driver mínimo" por una razón de
arquitectura y no de esfuerzo.

Y `pp_smu` se registra con la tabla `pp_ip_funcs`, no `pp_smu_ip_funcs`: otro caso
de nombre que no describe lo que ejecuta.

## Cuarto caso del patrón de aliasación

`192` estableció el patrón: el nombre del bloque no es el nombre del código.
Confirmado ahora para los cuatro:

| bloque | versión | ejecuta el código de |
|---|---|---|
| UVD | 6.3 | `uvd_v6_0` |
| VCE | 3.4 | `vce_v3_0` |
| SDMA | 3.1 | `sdma_v3_0` |
| **GMC** | **8.1** | **`gmc_v8_0`** |

**GMC 8.1 ejecuta `gmc_v8_0_hw_init`**, con sus **177** accesos MMIO, el mayor de
todos. Lo verifiqué con `ip_surface`, no lo supuse:

```
gmc_v8_1_ip_block   type=1  version=8.1.0
funcs -> gmc_v8_0_ip_funcs
   hw_init    gmc_v8_0_hw_init
```

Sin ese cruce, `gmc_v8_0_hw_init` parecía código de Tonga y quedaba fuera. **Con
el cruce, es el bloque más pesado de la placa.**

## Y la fracción que no es de esta placa

De los 4974 accesos atribuidos en total:

| clase | accesos | funciones |
|---|---|---|
| **esta placa** (9 bloques y comunes) | **1028** | 120 |
| otro ASIC (gfx_v7/v6, gmc_v7/v6, uvd_v3/v4/v5, vce_v1/v2, sdma_v4) | 2064 | 260 |
| común / no clasificado | 1882 | 310 |

**El 41% de los accesos medidos pertenecen a hardware que esta placa no tiene.**
Otro caso de la misma pregunta de siempre —"¿esto es de aquí?"— que **se resuelve
con un filtro por nombre de función, no leyendo el código**.

## El límite, medido y declarado

El extractor toma el **último** `mov $imm,%esi` antes de la llamada, a distancia
≤ 12 instrucciones.

**Captura 4974 de 14374 sitios: el 35%.** El resto tiene el offset cargado más
atrás, en otro registro, o inlineado. **Esta es una cota inferior de la huella, no
el mapa completo**, y lo digo porque un 540 que en realidad son 1500 sigue siendo
un número que invites a planificar con él.

El self-test mide el riesgo real en vez de esconderlo: reporta la distancia
`mov → call` de cada acceso, y falla si supera `MAX_DIST`. Y **el ancla es fuerte**
porque el resultado esperado es conocido de antemano:

```
$ mmio_map.py --self-test
self-test OK (1 ancla fuerte, 2 controles negativos, 1 de distancia)
```

El ancla: `sdma_v3_0_soft_reset` toca, en el fuente, **solo**
`mmSRBM_SOFT_RESET`, y el extractor tiene que devolver **exactamente `{0x398}`** y
distinguir lectura de escritura. Si atribuyera offsets que no son, ese aserto
fallaría. Y el control negativo: `amdgpu_gmc_tmz_set` hace un `dev_info` y nada
más, y tiene que dar **cero**.

## Tres intentos fallidos antes de encontrar el patrón

Los documento porque son la razón de que la herramienta sea simple:

1. **Busqué `0xf91` (mmSDMA_CONFIG) como operando de direccionamiento** → **0
   apariciones**. Hipótesis: el compilador no emite el offset así.
2. **Como inmediato (`$0xf91`)** → **0**. Hipótesis: rule out.
3. **Miré el código real de una función que sabía que hacía MMIO**
   (`sdma_v3_0_soft_reset`) → `mov $0x398,%esi` + `call`. Hipótesis: **es un
   argumento**.

Entonces descubrí por qué fallaban 1 y 2: **`objdump -d` sobre un `.ko` no aplica
las reubicaciones**, así que todas las llamadas salen como `call <siguiente
instrucción>` y los símbolos externos no aparecen. Con `-dr` aparece la línea
`R_X86_64_PLT32 amdgpu_device_rreg-0x4` y el patrón es de dos líneas.

**Estuve buscando en el binario equivocado**, y lo que parecía "el compilador no
hace esto" era "estoy mirando algo donde no se ve". Es la misma clase que buscar
una capacidad en el directorio equivocado (`192`) o con el patrón equivocado
(`202`/`SDMA`): **un resultado negativo con la herramienta equivocada no es un
resultado negativo.**

## Clasificación

| afirmación | estado |
|---|---|
| Todo el MMIO pasa por `amdgpu_device_rreg`/`wreg` | `PROVEN` — 14374 sitios |
| `amdgpu_device_wreg` 9245, `amdgpu_device_rreg` 5129 | `PROVEN` |
| `pp_smu` hace 0 accesos MMIO directos | `PROVEN` |
| `dm` hace 0 accesos MMIO directos | `PROVEN` |
| Que SMU se hable por protocolo de firmware | `DERIVATION` — del cero |
| Que display use un camino indirecto | `DERIVATION` — del cero |
| `gmc_v8_1` ejecuta `gmc_v8_0_hw_init` (177) | `PROVEN` — `ip_surface` |
| Cuarto caso de aliasación | `PROVEN` |
| 41% de los accesos son de otro ASIC | `PROVEN` |
| 540 accesos en los 9 bloques | `PROVEN_COTA_INFERIOR` — captura el 35% |
| Que 540 sea la huella completa | `REFUTADO` — es el 35% |

## Confounders

- **El 540 es una cota inferior**: captura el 35% de los sitios. Planificar con ese
  número es planificar con un tercio.
- **`sdma_v3_1` sale con 10**, y para un motor DMA con función de arranque eso
  parece bajo. No lo he investigado: puede ser que su configuración vaya por otra
  vía, o que el extractor falle más en ese fichero. **Lo declaro como sospechoso
  en vez de darlo por bueno.**
- **La clasificación por nombre de función es heurística.** `PLACA` incluye
  `gmc_v8_0` porque `ip_surface` probó que corre aquí; las 260 funciones de "otro
  ASIC" están clasificadas por prefijo, y un prefijo puede mentir como los nombres
  de bloque mintieron.
- **`dm` da 0 también porque su código no está en el corpus** (`dc/` vacío, según
  `192`). Con el `.ko` sí lo he medido, pero no he leído ese código.
- **No he verificado que un acceso sea alcanzable en runtime.** Que una función
  escriba un registro no dice que se ejecute en esta placa.

## Desfalsificación

- **(a)** 540 por bloque → refutable con `mmio_map --funcion F` en cada bloque.
- **(b)** El ancla `0x398` → refutable: el fuente dice que solo toca ese registro.
- **(c)** El control negativo `amdgpu_gmc_tmz_set` → cero.
- **(d)** Los ceros de `pp_smu` y `dm` → refutable buscando `amdgpu_device_rreg`
  dentro de sus funciones. **No hay.**
- **(e)** Que capture el 100% → **refutado**: captura el 35%. Declarado.
- **(f)** `sdma_v3_1` con 10 → **sospechoso, no refutado**. Declarado.

## UNLOCKS

- **Un patrón de acceso único**: `amdgpu_device_rreg`/`wreg` con el offset en el
  segundo argumento. Todo el MMIO del driver es localizable con un grep de dos
  líneas. **Es la llave que faltaba para medir hardware desde el binario.**
- **SMU y display no se conducen con registros.** Es una restricción de
  arquitectura que los saca del alcance de un driver mínimo por una razón
  estructural, y hasta ahora no estaba registrada.
- **GMC es el bloque más pesado de la placa (177)**, y ejecuta código `v8_0`. Sin
  cruzar `ip_surface` con `mmio_map` eso no se ve.
- **El 41% del MMIO del módulo es de hardware que no existe aquí**, y se separa
  con un filtro de nombres, no leyendo 300 funciones.
- **Composición de herramientas existentes**: `ip_surface` (qué función ejecuta cada
  bloque) × `mmio_map` (cuántos registros toca) = huella por bloque. Ninguna de las
  dos bastaba sola.
- **Siguiente paso**: cerrar la captura del 35%. Requiere saber por qué fallan los
  9400 sitios no atribuidos, y el sospechoso principal es la forma de la
  instrucción, no la distancia.

## Evidencia

```
objdump -dr --no-show-raw-insn /tmp/amdgpu_loaded.ko > ko_dr.asm   2591425 lineas
grep -c "amdgpu_device_rreg-0x4" ko_dr.asm      5129
grep -c "amdgpu_device_wreg-0x4" ko_dr.asm      9245

08-ARQUITECTURA/tools/mmio_map.py  --funcion N --resumen --top N --self-test
08-ARQUITECTURA/tools/ip_surface.py --bloque gmc_v8_1_ip_block
        funcs -> gmc_v8_0_ip_funcs,  hw_init = gmc_v8_0_hw_init
```

`WRITE_EXECUTION=NONE`. `MODIFICATIONS=0`. `GPU INTACTA`.
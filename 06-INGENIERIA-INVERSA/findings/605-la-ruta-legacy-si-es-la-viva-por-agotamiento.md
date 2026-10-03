# 605 · La ruta legacy sí es la viva, y se cierra por agotamiento

WORK_CLASS=READ_ONLY · WRITE_EXECUTION=NONE · MODIFICATIONS 0

> ## Resultado
>
> La premisa de toda la rama —que `polaris10_smumgr.c` se ejecuta en mi placa—
> pasa de `NOT_PROVEN` a **`PROVEN`**. No leyendo el valor de `MP1_HWIP`, que no
> está disponible, sino por **agotamiento sobre el `switch` que decide**.
>
> Y en el camino queda demonstrated que **swsmu no puede atender mi ASIC**, lo
> que era la pregunta que `604` dejó abierta.

## La pregunta y el punto exacto donde se decide

`amdgpu_discovery_set_smu_ip_blocks` (`amdgpu/amdgpu_discovery.c:2291`) reparte
**exclusivamente** por `amdgpu_ip_version(adev, MP1_HWIP, 0)`:

```
:2293  switch (amdgpu_ip_version(adev, MP1_HWIP, 0)) {
:2294-2297   case 9.0.0 / 10.0.0 / 10.0.1 / 11.0.2:
:2298          if (adev->asic_type == CHIP_ARCTURUS)
:2299              amdgpu_device_ip_block_add(adev, &smu_v11_0_ip_block);
:2300          else
:2301              amdgpu_device_ip_block_add(adev, &pp_smu_ip_block);   <-- LEGACY
:2303-2313   case 11.0.0 / 11.0.5 / 11.0.9 / 11.0.7 / 11.0.11 / 11.0.12 /
             11.0.13 / 11.5.0 / 11.5.2  -> smu_v11_0_ip_block           <-- swsmu
:2314-2317   case 11.0.8 (condicional)    -> swsmu
:2318-2321   case 12.0.0 / 12.0.1         -> smu_v12_0_ip_block          <-- swsmu
:2322-2336   case 13.0.x                  -> smu_v13_0_ip_block          <-- swsmu
:2337-2344   case 14.0.x                  -> smu_v14_0_ip_block          <-- swsmu
:2345-2348   case 15.0.0 / 15.0.8         -> smu_v15_0_ip_block          <-- swsmu
:2349-2353   default:  dev_err("Failed to add smu ip block(MP1_HWIP:0x%x)")
                    return -EINVAL;                                       <--- SIN BLOQUE
```

**No hay tercera rama.** O se registra `pp_smu_ip_block` (legacy) o uno de los
cuatro bloques swsmu. Y el `default:` no registra nada: hace fallar la
inicialización.

## La pieza que faltaba: swsmu no tiene smu7

Tres mediciones independientes, todas con `exit` verificado y ámbito contado:

| medición | resultado | `exit` |
|---|---|---|
| `smu7\|SMU7` en `pm/swsmu/` (**103 ficheros**, no vacío) | **0 hits** | 1 |
| `swsmu/Makefile:25` | `SWSMU_LIBS = smu11 smu12 smu13 smu14 smu15` | — |
| `pm/powerplay/Makefile:25` | `PP_LIBS = smumgr hwmgr` | — |

Es decir: **swsmu compila y contiene smu11 a smu15, y nada de smu7**. Polaris10/11/12
son smu7. `smu7` no aparece ni una vez.

Y el reparto interno de swsmu también es por `MP1_HWIP`
(`amdgpu_smu.c:733`, `:1669`, `:2001`, `:2024`, `:2045`), con lo que la generación
smu7 **no tiene ninguna ruta de entrada dentro de swsmu**.

## El cierre por agotamiento

```
1.  Mi ASIC es smu7 (Polaris10/12).
2.  swsmu no tiene smu7                                        [medido]
3.  El switch que registra el bloque de power es exhaustivo:
      o legacy, o swsmu, o default:return -EINVAL              [medido, :2293-2354]
4.  Si mi ASIC cayera en una rama swsmu, swsmu no tendria
    generacion smu7 que lo atienda                            [de 2]
5.  Si cayera en default:, la inicializacion fallaria con
    dev_err, no habria power management                       [medido, :2350-2353]
6.  luego cae en la rama legacy: se registra pp_smu_ip_block   [de 3, 4, 5]
```

**El valor concreto de `MP1_HWIP` no hace falta.** Lo único que se necesita es que
no pueda caer en una rama swsmu, y eso queda forzado por 2, 4 y 5. La premisa
queda **`PROVEN` sin la medición que yo buscaba**.

Y la coherencia del resultado es una comprobación independiente: `soc15.c` es el
fichero de la generación VI (Polaris) y en `:656-658` agrupa justo
`case IP_VERSION(9,0,0): case IP_VERSION(11, 0, 2):`, que son dos de los cuatro
valores de la rama legacy. `soc15.c` **no** asigna ningún `ip_versions[`
(`exit` y 0 hits), lo que confirma que para Polaris la versión no viene de una
tabla en C sino del discovery binary.

## Lo que sí puedo afirmar ahora, con el alcance correcto

```
adev->powerplay.pp_handle  =  struct pp_hwmgr *        (amd_powerplay.c:61)
smu_hw_init de swsmu       =  NO se registra en mi ASIC
-> polaris10_smumgr.c  SI se ejecuta
-> smu7_hwmgr.c         SI se ejecuta
-> :2118, la copia de 1776 B, SI se ejecuta
```

`pp_smu_ip_block` está declarado `extern` en `include/kgd_pp_interface.h:27` y se
registra en 11 sitios: `cik.c:2201,2219`, `vi.c:2061,2071,2091,2114,2130,2149` y
`amdgpu_discovery.c:2301`.

Y `vi.c` es el init de la generación VI: es exactamente el fichero que añadiría el
bloque legacy a un Polaris, por la vía del `asic_type` en lugar de la del `switch`.

## Por qué no pude leer `MP1_HWIP`, y por qué no hacía falta

Lo intenté por la vía correcta y falló por una razón que **no es** un fallo:

`amdgpu_discovery_init` (`:634`) saca el discovery binary de `adev->discovery.bin`,
y `amdgpu_discovery_read_binary_from_mem` (`:359`) lo lee de:

```
:370   amdgpu_device_vram_access(adev, adev->discovery.offset, ...)   -> VRAM
:376   amdgpu_discovery_read_binary_from_sysmem(...)                 -> RAM del sistema
```

y `get_tmr_info` (`:264`) elige entre ambas con `mmRCC_CONFIG_MEMSIZE`: si da 0,
`is_tmr_in_sysmem = true`.

**Ninguna de las dos rutas es el ROM.** El binary lo coloca PSP/IFWI en VRAM o en
memoria del sistema durante el arranque. Lo confirmé buscando su firma en la
captura: `BINARY_SIGNATURE = 0x28211407` (`include/discovery.h:28`), cuyo comentario
en `:59` confirma los bytes `07 14 21 28`, y hay **0 ocurrencias** en los 58880
bytes del VBIOS.

Ese cero **es el resultado correcto**, no una ausencia que investigar. La
clasificación es `EVIDENCE_MISSING` por vía estática, y el camino que lo daría es
`RUNTIME_MISSING`.

## La contradicción del PowerTune sigue abierta, y ahora con menos urgencia

`604` dejó este dato: los valores coherentes del PowerTune están en `0x9EAA` y no
en `0x9EAB`, que es lo que da `usPowerTuneTableOffset = 673`.

Con la premisa cerrada, la consecuencia que `604` temía **no se activa**: la ruta
sí corre, así que `:1661` sí lee `usClockStretchAmount`, y ese valor sigue siendo
`26880` truncado a `0`, que dispara `:1696`. El problema es que **esa consecuencia
predice un fallo muy visible**, y una ruta que sí funciona no puede dar eso.

Y ahora tengo un discriminante que antes no tenía: si `usPowerTuneTableOffset`
valiese 672 y no 673, el resto del recorrido del header también estaría desplazado
y `:45` no coincidiría con el ancla de `267`. Como `:45` **sí** coincide y `:61`
decodifica una tabla PCIe coherente, **el recorrido del header es correcto**, y
por tanto `673` es correcto, y por tanto la tabla **sí** empieza en `0x9EAB`.

Eso deja una sola salida: **la base de la tabla que da los cinco valores es una
coincidencia de 12 bytes**, y la lectura real bajo el layout que usa el kernel es
la que saya. Es la hipótesis más fuerte ahora, pero es `NOT_PROVEN`: 5 valores no
son suficientes para descartar unsesgo de 12 bytes alineado.

## Los tres errores de esta iteración, que casi invalidan la rama

Los tres son **el mismo error**: un cero o un recorte producido por mi propio
artefacto, sobre el que actué en vez de repetir la medición.

### 1. Concluí que los structs PowerTune no existen

Busqué `ATOM_Polaris_PowerTune_Table` en `amd/include/pptable.h`. Cero.
Concluí `PROVEN_ABSENT` y **escribí que no había struct con el que comparar**.

Están en `pm/powerplay/hwmgr/pptable_v1_0.h:422`. Con el ámbito correcto
(`amd/` completo, 2689 ficheros, `exit` verificado) aparecieron en dos golpes.

Décima vez que una búsqueda mal acotada me da una ausencia, y la décima con
consecuencia: casi dejé sin medir el PowerTune.

### 2. Concluí que el powerplay legacy es código muerto

Es el error grave. Busqué el token `POWERPLAY` en `amdgpu/*.c *.h`: **cero**, y
`pp_ip_funcs`: **2 apariciones, ambas dentro de su propio fichero**. De ahí la
conclusión `PROVEN_ABSENT`: el bloque legacy no se registra nunca.

El símbolo real es **`pp_smu_ip_block`**, y se registra en **11 sitios**. No
busqué el nombre del bloque, busqué un token que yo mismo elegí.

Y detrás hay un patrón, no un descuido: `POWERPLAY` es el nombre conceptual del
subsistema, y `pp_smu_ip_block` lo llama así porque en el registro **el powerplay
legacy se presenta como un bloque SMU**. Busqué el nombre del subsistema en vez
del nombre del bloque, que es el identificador real.

### 3. Concluí que el Makefile está corrupto

`powerplay/Makefile:27` leída con `cat -n ... | cut -c1-100` aparecía como
`...$(PP_LIB` a media referencia. Concluí fichero corrupto, y con él que no se
compilaba `smumgr`, y con eso que la rama era código muerto.

La línea tiene **101 caracteres**. Lo que se había cortado era mi `cut`, no el
fichero. La referencia está perfectamente balanceada: `$(PP_LIBS))`.

Añadí un comprobador automático de `$(` sin cerrar sobre **todos** los Makefiles
de `drm/`: **0**. El fichero estaba bien.

Esto es el peor de los tres: **iba a construir la conclusión mayor de la sesión
—«seis hallazgos sobre código muerto»— sobre un recorte de una columna.**

## La lección, que es la misma de siempre pero con un conteo

Diez ceros falsos en este proyecto. Los tres de hoy. Convertir un artefacto mío
—un `grep` mal acotado, un nombre elegido por mí, un `cut` de una columna— en
una afirmación sobre el hardware, y **actuar sobre ella** en vez de repetir la
medición.

El patrón que funciona y que ya uso: **contar el ámbito, exigir el `exit` real,
y cuando el cero sea raro o de un tipo inesperado, sospeche del artefacto y no del mundo.** La
versión de hoy es que un cero **nunca** autoriza una afirmación sin un segundo
método que no dependa de la misma búsqueda.

Y un criterio concreto que aplicaré desde ahora: **si el resultado de una
búsqueda contradice lo que funciona en la realidad, el resultado es que la
búsqueda está mal, no que el hardware sea raro.** Una placa que renderiza no
puede tener su power management sin inicializar.

## Frontier siguiente

**Volver a la contradicción del PowerTune, con el discriminante que `604` no
tenía.** Ya no es urgente para la premisa, pero es el único `NOT_DETERMINED`
que queda de esta serie y tiene un cierre acotado:

Determinar si la lectura alineada de `ATOM_Polaris_PowerTune_Table` sobre mi
VBIOS da basura o no, por un método que **no** dependa de la lectura empaquetada.
El candidato es buscar el mismo patrón de tabla en la zona del ROM donde vive la
PowerTune y comprobar si `0x9EAB` es un inicio de tabla coherente por algún otro
criterio, o buscar el checksum de la tabla de PowerTune en el master data table.

Si eso no cierra, la clasificación correcta del `-EINVAL` de `:1696` sería
`SEMANTIC_MISSING`: mi lectura del layout del VBIOS sería correcta y lo que no
conocería es la regla con la que el firmware compuso esa tabla.
# 1449 — el techo de reloj de memoria queda cerrado: 1500 MHz, tres estados, y mis once valores eran perfiles de timings

```text
AGENCIA=RX550-INVESTIGACION · WORK_CLASS=AGENT-MAIN/RE
CLASSIFICATION=CIERRE-DE-FRONTERA+REVISION-PROPIA+REVISION-DE-UN-REVISOR
TRACK=SYSFS + STATIC(corpus y .ko) + re-decode del ROM · 0000:01:00.0 · Intel intacta
GENERADO=2026-10-04
AFECTADO=06-INGENIERIA-INVERSA/findings/1419-*   (la SEMANTICA era mia y era erronea)
         09-POWER-CLOCKS/                          (el techo de memoria, cerrado)
         08-ARQUITECTURA/CONSTANTES-GFX8-DRIVER.md
ESTADO=PROBADO · los estados de reloj de memoria son 300, 625 y 1500 MHz.  Techo = 1500
       · los ONCE valores de 1419 se reproducen exactos, con la cita corregida
       · pero NO son estados de reloj: son cotas de rango de PERFILES DE TIMINGS
       · 2000 MHz queda REFUTADO como reloj alcanzable
       · y un dato nuevo: el atributo esta en SYSFS, no en debugfs, y yo solo mire debugfs
```

## 0. El instrumento, y mi error de búsqueda

El hallazgo 1448 verificó que no hay atributos `pp_*` en `/sys/kernel/debug/dri/1`. **Eso era
cierto y estaba incompleto**: existen, y son de **sysfs**:

```text
$ cat /sys/class/drm/card1/device/pp_dpm_mclk
0: 300Mhz *
1: 625Mhz
2: 1500Mhz

$ cat /sys/class/drm/card1/device/pp_dpm_sclk
0: 214Mhz *      4: 1000Mhz
1: 551Mhz        5: 1020Mhz
2: 734Mhz        6: 1046Mhz
3: 980Mhz        7: 1071Mhz
```

**Leí el sitio equivocado y declaré que no existían.** Es la tercera vez en esta sesión que
mi verificación falla antes que la fuente; queda como regla, no como anécdota.

**Y el dato que cierra la frontera, sin privileged access y sin tocar la GPU:**

```text
estados de reloj de MEMORIA   300, 625, 1500 MHz     (3 estados)
estados de reloj de GRAFICO   214 .. 1071 MHz        (8 estados)
```

`1071` es exactamente el `max_engine_clk_fcompute = 1071` que publica KFD. **Dos fuentes
independientes, mismo techo del reloj de gráficos.** Y el `*` marca el activo: **300 MHz de
memoria y 214 MHz de gráficos**, que es lo que medí en 1448 y lo que declara el ROM.

## 1. El techo, con su algoritmo

```c
/* amdgpu/amdgpu_amdkfd.c:534-540 */
if (adev->pm.dpm_enabled) {
        if (amdgpu_emu_mode == 1)
                mem_info->mem_clk_max = 0;
        else
                mem_info->mem_clk_max = amdgpu_dpm_get_mclk(adev, false) / 100;
} else
        mem_info->mem_clk_max = 100;
```

Verificado instrucción a instrucción en el `.ko` en ejecución (`0x2cb8a8`–`0x2cb8de`,
`imul $0x51eb851f` + `sar $0x25` = división por 100).

**Y la unidad tiene una confirmación independiente que no es mía.** La función hermana del
reloj de gráficos dice, textual, `amdgpu/amdgpu_amdkfd.c:550-557`:

```c
uint32_t amdgpu_amdkfd_get_max_engine_clock_in_mhz(struct amdgpu_device *adev)
{
        /* the sclk is in quantas of 10kHz */
        if (adev->pm.dpm_enabled)
                return amdgpu_dpm_get_sclk(adev, false) / 100;
```

> **La unidad del hallazgo 1419 (`= MHz`) queda confirmada por el comentario del propio
> driver**: *"in quantas of 10kHz"*, dividido por 100. No la deduje yo; está escrita.

Y el `false` del segundo argumento significa **"el reloj máximo soportado"**, por el nombre
de la función hermana. Por eso `mem_clk_max = 1500` **es** el techo, no el reloj actual
(que son 300).

### 1.1 El comentario de KFD sobre `amdgpu_mc` es PESCADO en este driver

`amdkfd/kfd_topology.c:1195` atribuye el dato a *"amdgpu driver (amdgpu_mc)"*. **`amdgpu_mc`
no existe**: `nm amdgpu.ko | grep -iE ' amdgpu_mc'` sólo devuelve `amdgpu_mca_*`, que es el
módulo de SDMA/RAS. El productor real es `amdgpu_amdkfd.c:538`. **Atribución `REFUTADA`.**

## 2. MIS ONCE VALORES: se reproducen, pero la SEMÁNTICA era mía y era errónea

### 2.1 Reproducción, con la cita corregida

```text
CLOCK_RANGE_MASK = 0x00ffffff     ->  amdgpu/amdgpu_atombios.c:1445
(no en atombios.h:7448, que es donde cita el 1419; allí lo que vive es CLOCK_RANGE_HIGHEST)
```

Re-decodeado por mí con la máscara del driver, `SHIFT` 0:

```text
 [ 0] 0x00009c40  raw= 40000  ->   400.00 MHz
 [ 1] 0x00013880  raw= 80000  ->   800.00 MHz
 [ 2] 0x00015f90  raw= 90000  ->   900.00 MHz
 [ 3] 0x000186a0  raw=100000  ->  1000.00 MHz
 [ 4] 0x0001b774  raw=112500  ->  1125.00 MHz
 [ 5] 0x0001e848  raw=125000  ->  1250.00 MHz
 [ 6] 0x0002191c  raw=137500  ->  1375.00 MHz
 [ 7] 0x000249f0  raw=150000  ->  1500.00 MHz
 [ 8] 0x00027ac4  raw=162500  ->  1625.00 MHz
 [ 9] 0x0002ab98  raw=175000  ->  1750.00 MHz
 [10] 0x00030d40  raw=200000  ->  2000.00 MHz
```

**Los once, exactos.** El hallazgo 1419 queda confirmado en sus números.

**Un revisor hippocampus los buscó con una máscara adivinada** — `(dword >> 16) & 0x3FFF` — y
reportó `NOT_REPRODUCED`. Con la máscara del driver, la reproducción es inmediata. **Su
re-derivación era la defectuosa.** Es el segundo caso de la sesión en que mi verificación
falla y la fuente tiene razón; ya van dos, y ambos se detectaron.

### 2.2 Pero la INTERPRETACIÓN del 1419 era mía y estaba equivocada

El 1419 los llamó *"once frecuencias de DRAM"* y *"escalones de reloj"*. **No lo son.**

El consumidor del campo es `pm/powerplay/smumgr/ci_smumgr.c:1779-1791`:

```c
for (i = 0; i < smu_data->mc_reg_table.num_entries; i++) {
        if (memory_clock <= smu_data->mc_reg_table.mc_reg_table_entry[i].mclk_max)
                break;                                   /* :1780-1781 */
}
if ((i == num_entries) && (i > 0))
        --i;                                              /* :1786-1787 */
ci_convert_mc_registers(&...entry[i], ...);
```

**Es una búsqueda de rango lineal: se toma la PRIMERA entrada cuyo `mclk_max` sea ≥ al reloj
que se está programando.** El campo no es "el reloj máximo de este perfil": es **"hasta qué
reloj vale este perfil de timings de memoria"**. Once perfiles, once cotas.

Y el nombre del macro lo dice solo, `atombios.h:7488`:
```c
#define CLOCK_RANGE_HIGHEST     0x00ffffff
```
**CLOCK RANGE.** Un "máximo" no se llama `CLOCK_RANGE`.

> **Consecuencia directa: para cualquier reloj de memoria por encima de 1375 MHz, el driver
> reutiliza el último perfil** (`ci_smumgr.c:1786-1787`). **2000 MHz no es un reloj: es la
> cota del último perfil.** Para cualquier mclk por encima de 1375, el mismo perfil.
> `REFUTADO` como techo, y `PROVEN` que no es ni un estado ni el reloj actual.

### 2.3 Y de dónde salen los estados DE VERDAD

```text
pp_dpm_mclk  ->  smu7_emit_clock_levels  ->  smum_send_msg_to_smc  ->  SM RAM
```

El driver puebla `SMU74_Discrete_MemoryLevel[]` desde el DPM
(`pm/powerplay/smumgr/polaris10_smumgr.c:1208-1248`, `polaris10_populate_all_memory_levels`)
y lo sube a la SM RAM con `smu7_copy_bytes_to_smc`. **La escalera de relojes vive en el
firmware de la SMU, no en el ROM y no en el `.ko`.** Por eso `amdgpu_pm_info` y
`pp_dpm_mclk` dan datos que el ROM no puede dar.

## 3. Veredicto sobre los tres candidatos

| candidato | veredicto | qué es en realidad |
|---|---|---|
| **1500 MHz** | **`PROBADO`** | el techo. Estado DPM de memoria **índice 2**, el último de la tabla viva, y `mem_clk_max` lo computa como tal |
| **2000 MHz** | **`REFUTADO`** | cota superior del último de once **perfiles de timings**. Ningún estado, ningún reloj actual, ningún techo |
| **625 MHz** | **`PROBADO`** | estado DPM de memoria **índice 1**, alcanzable. Es también `PSTATE_MCLK` |
| *(300 MHz, para completar)* | **`PROBADO`** | reloj actual, estado índice **0** — el que marca `*`. Y el `ulDefaultMemoryClock` del ROM |

**El conjunto alcanzable es {300, 625, 1500} MHz. Exactamente tres estados.**
**El techo es 1500 MHz.** Eso era `NOT_DETERMINED` desde el hallazgo 1419 y ahora no lo es.

## 4. `ulASICMaxMemoryClock = 62610` sigue siendo `NOT_DETERMINED`, y corrijo al revisor

El revisor lo descartó diciendo que *"62610 y 62500 difieren en un factor de ~100"*. **Eso
es un error aritmético**: `62610 - 62500 = 110`. Se diferencian en **110**, no en un factor
de 100.

Lo que sí se puede decir, con honestidad:

```text
ulASICMaxMemoryClock = 62610
  NO es el techo de reloj de memoria   -> REFUTADO, el techo es 1500
  NO es un estado DPM                  -> los estados son 300/625/1500
  su relacion con 625 sigue sin cerrar -> NOT_DETERMINED
```

No se escribe una unidad inventada. Lo que **queda cerrado** es que **no es el techo**, que
era lo único que bloqueaba el trabajo de rendimiento.

## 5. Sobre la habilidad del subagente en dos puntos

Su trabajo fue bueno y encontré cosas que yo había pasado por alto. Pero dos correcciones,
porque el método depende de no creerse las revisiones:

| afirmación suya | veredicto |
|---|---|
| "`CLOCK_RANGE_MASK` es `NOT_FOUND` en el corpus" | **falso**: está en `amdgpu/amdgpu_atombios.c:1445`. **Mi 1419 tenía la cita mal y el valor bien**; el revisor tenía mal ambas cosas sobre la cita |
| "los once valores de 1419 no se reproducen" | **falso**: usó `(>>16)&0x3FFF` en vez de la máscara del driver. Con la máscara correcta, reproducción exacta |
| "62610 y 62500 difieren en un factor de 100" | **error aritmético**: difieren en 110 |
| "`amdgpu_mc` no existe; el comentario de KFD es obsoleto" | **correcto**, y es un hallazgo real |
| "`mclk_max` es una búsqueda de rango, no un máximo" | **correcto**, y es la corrección de fondo de este hallazgo |
| "`polaris12_mc.bin` no tiene tabla de frecuencias, es microcódigo GFX8" | **correcto**, y explica por qué la escalera vive en la SMU |

## 6. Procedencia

```text
medido     /sys/class/drm/card1/device/pp_dpm_mclk    0: 300Mhz *  1: 625Mhz  2: 1500Mhz
           /sys/class/drm/card1/device/pp_dpm_sclk    8 estados, 214..1071 MHz, activo 214
           (sysfs, sin privileged access, sin escribir nada)
fuente     amdgpu/amdgpu_amdkfd.c:534-540   mem_clk_max = amdgpu_dpm_get_mclk(false)/100
           amdgpu/amdgpu_amdkfd.c:550-557   "the sclk is in quantas of 10kHz"  <- la unidad
           pm/powerplay/smumgr/ci_smumgr.c:1779-1791  el consumidor: busqueda de rango
           pm/powerplay/smumgr/polaris10_smumgr.c:1208-1248  quien puebla la escalera DPM
           amdgpu/amdgpu_atombios.c:1445     CLOCK_RANGE_MASK = 0x00ffffff
re-decode  revkit/capturas/amdgpu_vbios.txt, 0xA365, mis 11 valores, reproducibles
binario    amdgpu.ko (copia en /tmp/opencode)  simbolos y offsets citados
```

```text
ESTADO=PROBADO · techo de reloj de memoria = 1500 MHz.  Alcanzables = {300, 625, 1500}
       · la unidad MHz de 1419 confirmada por el comentario del propio driver
       · los 11 valores de 1419 se reproducen EXACTOS, con la cita corregida a
         amdgpu_atombios.c:1445 (no atombios.h:7448)
REVISION PROPIA  la SEMANTICA del 1419 era mia y era erronea: no son "escalones de reloj",
       son cotas de rango de once PERFILES DE TIMINGS.  El consumidor es una busqueda de
       rango lineal (ci_smumgr.c:1779-1791) y el macro se llama CLOCK_RANGE
REFUTADO  2000 MHz como techo, como estado y como reloj actual: es la cota del ultimo perfil.
       Para cualquier mclk > 1375 el driver reutiliza ese ultimo perfil
REFS:    kfd_topology.c:1195 atribuye el dato a "amdgpu_mc"; ese modulo NO EXISTE en 7.1.3
EXPLICA  por que la escalera no esta en el ROM ni en el .ko: vive en el firmware de la SMU
       y en SM RAM, y el driver solo la puebla y la publica
NOT_DETERMINED  ulASICMaxMemoryClock = 62610 sigue sin unidad.  NO es el techo (queda cerrado).
       El revisor lo descarto con un error aritmetico (difieren en 110, no en un factor de 100)
NUEVO INSTRUMENTO  pp_dpm_mclk / pp_dpm_sclk en SYSFS: enumerable completo de la escalera de
       relojes, con el estado activo marcado, sin root y sin escribir nada.  Mejor que
       amdgpu_pm_info para este proposito, y no requiere privileged access
LIMITE   no se ha medido la escalera bajo carga; el techo se conoce por tabla, no por
       comportamiento observado al overclockear
FRONTERA Intel intacta: fb0=i915drmfb 1366,768, control=auto, runtime=active
Siguiente  1) barrido de carga con pp_dpm_mclk: confirmar que 1500 es alcanzable de verdad y
           no solo una entrada de tabla.  Es el ultimo paso del §77 para el techo de memoria
         2) el techo del reloj de GRAFICO: 8 estados hasta 1071.  Medir la respuesta a carga
         y decidir si el techo de esta placa es la memoria (1500) o el enlace (x4 a 5 GT/s)
```

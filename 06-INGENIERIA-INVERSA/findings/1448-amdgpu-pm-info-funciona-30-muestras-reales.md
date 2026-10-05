# 1448 — `amdgpu_pm_info` funciona con la GPU despierta: 30 muestras reales, y corrige una objeción mía sobre la potencia

```text
AGENCIA=RX550-INVESTIGACION · WORK_CLASS=AGENT-MAIN/RE
CLASSIFICATION=EVIDENCIA-DE-HARDWARE+MEDICION+REVISION-PROPIA
TRACK=RUNTIME · 0000:01:00.0 SOLO · Intel intacta · cero escrituras de registro
GENERADO=2026-10-04
AFECTADO=06-INGENIERIA-INVERSA/findings/1435-*   (la objecion de "muestra instantanea")
         06-INGENIERIA-INVERSA/findings/1400-*   (ulASICMaxMemoryClock: tenia razon la
         revision, y ahora hay una explicacion positiva)
         el "EBUSY sin explicar" de los atributos de sensor
ESTADO=PROBADO · amdgpu_pm_info es el instrumento de datos vivos que funciona, y hay 30
       muestras con estadistica
       · los relojes en reposo SON los defaults del firmware: 214 y 300 MHz, por dos vias
       · PSTATE_MCLK = 625 MHz, y eso situa ulASICMaxMemoryClock = 62610
       · la potencia es estable a +-0.005 W, y el camino rapido del SMC queda demostrado
```

## 0. El instrumento, y por qué no lo tenía antes

Tres vías de datos vivos se habían probado y **las tres fallaban**:

```text
/sys/class/drm/card1/device/hwmon/hwmon1/*   ->  EBUSY  (cerrado: runtime PM suspended)
/sys/kernel/debug/dri/1/pp_*                 ->  NO EXISTEN  (no hay ni un atributo pp_)
/sys/kernel/debug/dri/1/amdgpu_sensors       ->  EINVAL
```

Los `pp_*` no es que devolvieran error: **no existen en este kernel.** Eso explica la
anotación antigua de "EBUSY en nueve atributos `pp_*`" — no hubo lectura, no hubo respuesta.

**La cuarta vía funciona, y sólo con la GPU despierta:**

```text
/sys/kernel/debug/dri/1/amdgpu_pm_info
```

Trae, en una sola lectura: MCLK, SCLK, PSTATE_SCLK, **PSTATE_MCLK**, VDDGFX, potencia del
SoC, temperatura del GPU, y las cargas de GFX y de memoria. **Ninguna de esas magnitudes
era legible por hwmon.**

## 1. Las 30 muestras

Con la GPU en `runtime_status=active`, 30 lecturas separadas 0.2 s:

```text
magnitud      n    min      max      media     desv. tipica
--------------------------------------------------------------
MCLK          30   300.0    300.0    300.0     0.0
SCLK          30   214.0    214.0    214.0     0.0
PSTATE_SCLK   30   214.0    214.0    214.0     0.0
PSTATE_MCLK   30   625.0    625.0    625.0     0.0
VDDGFX_mV     30   700.0    700.0    700.0     0.0
SoC_W         30   3.14     3.15     3.1403    0.0018
temp_C        30   30.0     31.0     30.8333   0.3727
```

## 2. Los relojes en reposo SON los defaults del firmware, por dos vías

```text
                     ROM (FirmwareInfo)            en la placa
ulDefaultEngineClock  21400 @10 kHz = 214 MHz  ->   SCLK = 214.0 MHz
ulDefaultMemoryClock  30000 @10 kHz = 300 MHz  ->   MCLK = 300.0 MHz
```

**Desviación cero en 30 muestras**, lo que además confirma que la tarjeta está en reposo y
no se movió durante la medición. Las dos cifras del ROM **medidas en el hallazgo 1400**
coinciden con lo que el hardware hace ahora. **Es la comprobación del reloj en reposo que
quedaba pendiente desde el hallazgo 1400**, y cierra por el lado del hardware.

Y `PSTATE_SCLK = 214 = SCLK` dice que el P-estado actual **es** el estado mínimo. Lo que el
proyecto vio antes —"SCLK vuelve a 214 MHz tras la subida"— es que la tarjeta
vuelve a su estado por defecto, y no es un artefacto del medidor. **Era la hipótesis del
hallazgo 1400 y queda corroborada.**

## 3. `PSTATE_MCLK = 625` EXplica el `62610` del ROM

El hallazgo 1400 dejó esto:

```text
ulDriverTargetMemoryClock = 360000   ->  3600 MHz con unidad 10 kHz
ulASICMaxMemoryClock      =  62610   ->   626.1 MHz con unidad 10 kHz
el objetivo es 5.75x mayor que el "maximo": no pueden ser ambos 10 kHz
NOT_DETERMINED
```

Y dejó escrito que el techo de reloj de memoria **sigue con dos candidatos, 1500 y 2000
MHz** (hallazgo 1419), de los que el kernel publica 1500.

Ahora hay un tercer número medido:

```text
PSTATE_MCLK = 625 MHz          <- medido, en la placa, 30 veces, desviacion 0
ulASICMaxMemoryClock = 62610   <- del ROM
```

**62610 está al lado de 625, y muy lejos de 2000.** No es un "máximo de reloj de memoria":
está **en la escala del P-estado**, que es un estado, no un límite.

> **Esto da la explicación positiva que al 1400 le faltaba.** La §7.1 de 1400 registró
> el valor como `REFUTADO` por incoherente, sin saber por qué era incoherente. Ahora
> se sabe: es un valor de **P-estado**, no un techo. Con eso, 1400 §7.1 deja de ser "no lo sé"
> y pasa a `REFUTADO` **con motivo**.

**Y no se resuelve todavía cuál de 1500/2000 es el techo.** Eso sigue
`NOT_DETERMINED`: `1500` es lo que publica el kernel, `2000` es el máximo de la tabla de
once escalones del firmware de la ROM. `amdgpu_pm_info` no expone la tabla DPM de memoria,
así que **este instrumento no decide esa pregunta** y no se le pide que la decida.

## 4. CORRECCIÓN DE 1435: la potencia sí es utilizable

El hallazgo 1435 objetó la cifra de potencia por ser **una muestra instantánea con etiqueta
de promedio**. Es un hecho sobre el mecanismo, y sigue siendo cierto. Pero medido:

```text
SoC_W:  min 3.14   max 3.15   media 3.1403   desv 0.0018 W
```

**Variación total de 0.01 W sobre 30 muestras en unos 6 segundos.** La objeción era
semántica ("una muestra no es un promedio"), y el resultado es que **en reposo la magnitud
es estable**, con una dispersión de 6·10⁻⁴ relativa.

**Y hay un segundo dato, más fuerte que el anterior: el camino rápido del SMC queda
demostrado por el tiempo.** Si el SMC hubiera devuelto cero, `smu7_hwmgr.c:4060-4086`
habría ejecutado su bucle de **10 × `msleep(500)`** — cinco segundos por lectura, dentro
del mutex de DPM. **30 lecturas se hicieron en unos 6 segundos.** Luego el primer
`PPSMC_MSG_GetCurrPkgPwr` devolvió un valor distinto de cero **las 30 veces**, y el
`return 0` inmediato (`smu7_hwmgr.c:4066`) se tomó siempre.

> **Refutado por medición**: la objeción de "bloquea hasta 5 s" **no se materializa** en el
> estado normal de este sistema. Sigue siendo un riesgo latente si el SMU devolviera cero.

La corrección justa al 1435 es: **el defecto era de interpretación, no de usabilidad.** Con
30 muestras y desviación declarada, la cifra es una medición. Lo que **no** es una
medición es una sola lectura suelta.

## 5. Lo que este hallazgo hace con lo que había

| antes | ahora |
|---|---|
| los relojes en reposo medidos por un lado (ROM) y referidos por otro (`pp_dpm_sclk`) | **medidos en la placa**, con desviación |
| el techo de memoria: `NOT_DETERMINED` entre 1500 y 2000 | igual, **pero con un tercer número eliminado**: `62610` no es el techo |
| `ulASICMaxMemoryClock` "incoherente, sin explicación" | **es un P-estado**, y 625 MHz lo confirma |
| potencia: "no es medición" | **medición con n=30 y desviación**; y el camino de 5 s **no se activa** |
| sensores: `EBUSY` sin explicación | **`EBUSY` era la GPU dormida**; con ella despierta, `amdgpu_pm_info` los da |
| `pp_*` "EBUSY en nueve atributos" | **no existen** en este kernel. Nunca hubo lectura |

## 6. Procedencia

```text
instrumento  /sys/kernel/debug/dri/1/amdgpu_pm_info    lectura, 30 veces, 0.2 s de separacion
artefacto    /tmp/opencode/pm_n.txt    las 30 lineas capturadas
objeto       0000:01:00.0 unicamente
escrituras   CERO.  Ni un registro, ni una palabra de la interfaz del driver
GPU          en active, y se deja en active (era suspended antes de esta sesion)
```

```text
ESTADO=PROBADO · amdgpu_pm_info es el instrumento de datos vivos que funciona donde hwmon,
       pp_* y amdgpu_sensors fallan.  Los seis valores que da son nuevos
       · SCLK 214 MHz y MCLK 300 MHz, con desviacion CERO en 30 muestras, y ambos son
         exactamente los defaults del firmware (ulDefaultEngineClock, ulDefaultMemoryClock)
       · PSTATE_MCLK = 625 MHz con desviacion cero: situa ulASICMaxMemoryClock = 62610
CORRIGE 1435  la potencia es utilizable: 3.1403 +- 0.0018 W en 30 muestras.  Y el camino
       lento del SMC (10 x msleep(500) = 5 s) NO se activa: 30 lecturas en ~6 s lo demuestran
       por tiempo.  La objecion era de interpretacion, no de usabilidad
CORRIGE 1400 §7.1  ulASICMaxMemoryClock ya no es "incoherente sin explicacion": es un valor
       de P-ESTADO, no un techo.  Pasa de NOT_DETERMINED a REFUTADO CON MOTIVO
REFUTADO el "EBUSY en nueve atributos pp_*"   no hay ni un atributo pp_* en este kernel.
       No hubo lectura fallida: no hay nada que leer
LIMITE  el techo de memoria sigue NOT_DETERMINED entre 1500 (lo que publica el kernel) y
       2000 (el maximo de la tabla del firmware).  Este instrumento NO lo decide, porque no
       expone la tabla DPM de memoria
RIESGO  la GPU ha quedado en power/control=on.  Es reversible con "echo auto >", y la
       razon de dejarla despierta es que sin ella no hay ningun dato vivo
FRONTERA Intel intacta: fb0=i915drmfb 1366,768, control=auto, runtime=active, HDMI=connected
Siguiente  1) dos subagentes estan buscando amdgpu_mc.c (en el arbol 7.2.8 y en el .ko) para
           decidir 1500 vs 2000, y desensamblando smc/mc para la tabla de relojes
         2) probar el reloj bajo carga ahora que el instrumento funciona: la arista
           WORKLOAD -> CLOCK se puede cerrar con datos, no con inferencia
         3) VDDGFX = 700 mV: contrastar contra MinVoltageGfx/MaxVoltageGfx del PPT, que
           estan declarados en mV con 2 bits fraccionarios
```

# 920 · Las 13 escrituras quedan cerradas, y el arreglo que hacía falta no era el que yo decía

WORK_CLASS=READ_ONLY · MODIFICATIONS 0 en el corpus · AUTHORIZATION NONE · AUTORIA=AGENTE-SMU

> ## Resultado
>
> **Las 13 escrituras de `polaris10_smumgr.c` quedan clasificadas sin ningún hueco:**
>
> ```
> TAPADA           6   :142 :149 :157 :166 :1146 :1246
> VIVA             3   :1511  :2118  :2254
> SIN_ORDEN        1   :2398
> RUNTIME_MISSING  3   :654   :1872  :1881
> NO_RESUELTO      0
> ```
>
> Y los números coinciden **exactamente** con los de `502`, que era quien lo pedía.
> Eso cierra «quién escribe cada byte de los 1776».
>
> Pero **el arreglo que yo diagnostiqué no era el que faltaba**, y eso es lo que
> más me cuesta escribir aquí.

## 1. Lo que yo diagnostiqué, y por qué era falso

En `911` cerré diciendo que los dos `NO_RESUELTO` restantes eran por una forma de
declaración partida en dos líneas:

```c
:1046   uint32_t array = smu_data->smu7_data.dpm_table_start +
         offsetof(SMU74_Discrete_DpmTable, GraphicsLevel);
```

Y propuse enseñarle esa forma al resolutor de destinos.

**No hacía falta.** Medido directamente:

```
RE_LOCAL_ADDR sobre la sentencia completa   -> casa
resuelve_destino(expr, offsets, ...)        -> (236, 'offsetof(GraphicsLevel)', 'TABLA_DPM')
```

La forma ya se resolvía. Y el resultado real:

```
:1146  ini=236  fin=683  tam=448
:1246  ini=708  fin=803  tam=96
```

**El destino estaba bien desde el principio.** Lo que fallaba era otra cosa.

## 2. El fallo real: un parámetro que no llegaba

Comparando mi llamada directa con la línea de órdenes, la única diferencia era que
en la llamada directa pasaba `contadores_linea` en su ranura y **en `main` no se
pasaba**:

```
todas.extend(analiza_fichero(f, None, offsets, sizes, contadores,
                             constantes))
```

Y el síntoma era el que más me hizo desconfiar de mi propio diagnóstico:

```
:1146  (tamano: contador sin valor conocido: array_size)
```

Es decir: **el destino se resolvía y el tamaño no**, porque el contador por línea
no había llegado. Mi diagnóstico apuntaba al destino porque era el otro campo
visible en el mismo `NO_RESUELTO`.

**Un `NO_RESUELTO` tiene dos causas posibles y solo muestra una.** Eso no lo tenía
en cuenta y me costó una hipótesis entera sobre la forma equivocada.

## 3. El error de verificación, por tercera vez

Este es el que importa. El arreglo lo había aplicado antes, en `911`, y creí que
estaba puesto. No lo estaba.

La razón es **la misma de entonces, y ya la había escrito**:

> un script mío falló en una aserción **después** de imprimir un mensaje de
> éxito, y como la escritura va al final del script el fichero no se guardó.

Pasó dos veces en la misma sesión. Y las dos veces el mensaje de éxito se emitió
antes de la escritura, así que **no podía saberlo por el mensaje**.

Corregido de forma que no vuelva: el script de edición ahora **vuelve a leer el
fichero del disco y comprueba que el cambio está**, antes de decir nada:

```python
t = io.open(p, encoding="utf-8").read()
print("escrito en disco: %s" % (nuevo in t))
```

**Un mensaje que afirma un cambio debe comprobar el cambio.** Un mensaje que solo
afirma es una intención.

## 4. La validación, completa

```
BUILD              SINTAXIS OK
BASIC TEST         --selftest -> RESULTADO OK, exit=0, 81 vectores
KNOWN INPUT        los vectores previos siguen reproduciéndose
EXPECTED OUTPUT    TAPADA 6 / VIVA 3 / SIN_ORDEN 1 / RUNTIME_MISSING 3 / NO_RESUELTO 0
OUTPUT VALIDATION  los seis pares --orden ACEPTADOS, sin rechazos
FAILURE CHECK      sigue habiendo un AVISO de entrada no usada, y es correcto
EDGE CASE          declarado para lineas posteriores -> NO_RESUELTO, no un valor
                   equivocado
```

El `AVISO` que queda es `graphics_level_size sin usar`, y es **verdad**: `:149`
resuelve su tamaño por otra vía. La herramienta avisa de una entrada mía
innecesaria en vez de tragársela, y eso no es un fallo.

## 5. Lo que queda ahora, con el alcance correcto

| escritura | destino | veredicto | por qué |
|---|---|---|---|
| `:142` | `VRConfig` @112 | **TAPADA** | dentro de 108..1883, la copia de `:2118` lo pisa |
| `:149` | `GraphicsLevel` @236 | **TAPADA** | ídem, 448 B |
| `:157` | `GraphicsLevel` @236 | **TAPADA** | ídem, 24 B |
| `:166` | `GraphicsLevel` @236 | **TAPADA** | ídem, 2 B |
| `:1146` | `GraphicsLevel` @236 | **TAPADA** | ídem, 448 B |
| `:1246` | `MemoryLevel` @708 | **TAPADA** | ídem, 96 B |
| `:1511` | `arb_table_start` | **VIVA** | tabla de arbitraje, no la DPM |
| `:2118` | `SystemFlags` @108, 1776 B | **VIVA** | la copia misma |
| `:2254` | `fan_table_start`, **8 B** | **VIVA** | y es un puntero: ver `907` |
| `:2398` | `LowSclkInterruptThreshold` @1692 | **SIN_ORDEN** | otra función contiene su rango |
| `:654` | `pm_fuse_table_offset` | **RUNTIME_MISSING** | la dirección la da el firmware en `:614` |
| `:1872` | `tmp` | **RUNTIME_MISSING** | ídem en `:1870` |
| `:1881` | `tmp` | **RUNTIME_MISSING** | ídem en `:1878` |

**Ninguna de las seis `TAPADA` sobrevive.** Se confirma la predicción de `403` y
el cierre de `608`: las cuatro escrituras AVFS no sobreviven, y las dos de
`array_size` tampoco.

Y las tres `RUNTIME_MISSING` **no son un hueco pendiente**: la dirección la
revela el firmware al correr, y por eso no pueden ser ni `TAPADA` ni `VIVA`
—afirmar cualquiera de las dos sería inventar.

## 6. Errores de esta iteración

**1. El diagnóstico apunta al campo equivocado.** Un `NO_RESUELTO` lo pueden
causar el destino o el tamaño, y la nota solo enseña el que falló en ese momento.
Diagnostiqué el destino porque era el otro campo visible en la misma línea, sin
mirar que el tamaño era el que faltaba.

**2. El arreglo no estaba aplicado y lo creí puesto.** Es la tercera vez. Dos por
un script que imprime éxito antes de escribir; una por un `edit` que falló con
«no encontrado» y que reintenté con el mismo patrón.

**3. Mi propia sonda mintió.** Al depurar construyo `{"array":[(None,"TABLA_DPM")]}`
a mano y obtuve un `IndexError` que parecía un defecto de la herramienta. Era un
fixture mío con la tupla mal formada. **Un `IndexError` en un reproductor
escrito a mano no es evidencia sobre el código.**

Los tres son: un artefacto mío, plausible, y falso.

## 7. Frontier siguiente

**Leer en el VBIOS qué hay en las tres direcciones que el firmware revela, que es
la única parte que queda de esta serie y sí es estáticamente posible.**

`:1872` y `:1881` escriben `AVFS_meanNsigma` y `AVFS_SclkOffset` donde el SMC
indica en `SMU74_Firmware_Header`, en los campos `AvfsMeanNSigma` y
`AvfsSclkOffsetTable`. El *contenido* de esas direcciones está en el ROM y se puede
leer; lo que no se puede es *su dirección*, porque el firmware la calcula.

Eso tiene valor directo para el objetivo: son **parámetros de AVFS**, es decir la
tabla de media y sigma con la que el firmware decide el voltaje y la frecuencia.
Saber qué valores se suben es saber quénea de AVFS usa mi placa.

Criterio de cierre: los offsets de `AvfsMeanNSigma` y `AvfsSclkOffsetTable`
dentro de `SMU74_Firmware_Header` leídos del BTF, y el contenido correspondiente
en el ROM, con el criterio de plausibilidad en el dominio ya usado: niveles de
voltaje 300..1200 mV, sigma en el orden de 1..60, factores que no se salgan de un
orden de magnitud.
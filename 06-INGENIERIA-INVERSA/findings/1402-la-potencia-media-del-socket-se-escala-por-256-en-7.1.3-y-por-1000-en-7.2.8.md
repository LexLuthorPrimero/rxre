# 1402 — el kernel que corre en esta máquina escala la potencia media del socket por 256 donde el upstream la escala por 1000

```text
AGENCIA=RX550-INVESTIGACION · WORK_CLASS=AGENT-MAIN/RE
CLASSIFICATION=DEFECTO-EN-FUENTE-VENDOR+INVALIDACION-DE-MEDICION
TRACK=STATIC(dos arboles del mismo fichero) · sin GPU · sin sudo
GENERADO=2026-10-04
AFECTADO=RESEARCH/baseline/linux-7.1.3/drivers/gpu/drm/amd/pm/swsmu/smu11/arcturus_ppt.c:661
         ioctl AMDGPU_PP_SENSOR_GPU_AVG_POWER  (arcturus_ppt.c:1063-1068)
         y por extension  09-POWER-CLOCKS/  en bloque: cualquier cifra de potencia
ORIGEN=revision adversarial de arcturus_ppt.c; el aviso era "parece un << donde deberia
       haber una multiplicacion".  aqui se mide que tan cierto es y que tan ancho es.
ESTADO=PROBADO · la divergencia entre versiones es REAL y esta medida
       · el alcance es de FAMILIA, no de Arcturus (corregido aqui una hipotesis propia)
       · cual de las dos escalas es la correcta: NOT_DETERMINED
       · CONSECUENCIA: las cifras de potencia de esta host no son medibles hasta cerrarlo
```

## 0. Qué se comparó

Dos árboles del **mismo fichero**, mismo `case`, mismo campo, misma familia SMU:

```text
7.1.3   arcturus_ppt.c:660-661
        case METRICS_AVERAGE_SOCKETPOWER:
                *value = metrics->AverageSocketPower << 8;

7.2.8   arcturus_ppt.c:660-661
        case METRICS_AVERAGE_SOCKETPOWER:
                *value = metrics->AverageSocketPower * MILLIWATT_PER_WATT;
```

Las líneas vecinas (`METRICS_AVERAGE_UCLKACTIVITY`, `TEMPERATURE_EDGE`,
`TEMPERATURE_HOTSPOT`, `TEMPERATURE_MEM`) son **byte a byte idénticas** en ambos árboles.
La diferencia está aislada en una línea. Eso descarta que sea ruido de sincronización
entre versiones.

## 1. Cuánto vale cada escala, medido

```text
<< 8                        =  × 256        (aritmética)
MILLIWATT_PER_WATT          =  × 1000       include/linux/units.h:56
                             #define MILLIWATT_PER_WATT 1000UL
razon                       =  1000/256 = 3.90625
```

**Y el detalle que importa:** `include/linux/units.h:56` **existe en el árbol 7.1.3**. La
constante que el código de 7.2.8 usa estaba disponible en 7.1.3 y no se usó. No es que
7.2.8 introdujera una constante nueva.

```text
$ grep -rn 'MILLIWATT_PER_WATT' RESEARCH/baseline/linux-7.1.3/     -> 0 occurrences
$ grep -rn 'define MILLIWATT_PER_WATT' RESEARCH/kernelbuild/linux-7.1.3/include/linux/units.h:56
      #define MILLIWATT_PER_WATT 1000UL
```

(`RESEARCH/kernelbuild/` y `RESEARCH/baseline/` son el mismo 7.1.3 en dos stages del árbol
de compilación; el primero es el stage de cabeceras.)

## 2. CORRECCIÓN DE UNA HIPÓTESIS PROPIA, DENTRO DE ESTE HALLAZGO

La primera hipótesis al ver la línea fue: *"Arcturus escala mal y su ASIC hermano lo
arregló"*. **Es falsa, y el corpus lo dice:**

```text
7.1.3 arcturus_ppt.c   *value = metrics->AverageSocketPower << 8;
7.1.3 navi10_ppt.c     *value = metrics->AverageSocketPower << 8;
```

**Navi10 —otro ASIC de la misma generación SMU11, mismo driver, mismo kernel— hace
exactamente lo mismo.** El `<< 8` es la convención **de la familia smu11 en 7.1.3**, no un
defecto propio de Arcturus. `grep` sobre `smu11/*_ppt.c` sólo devuelve `arcturus` y
`navi10` con ese `case`.

Esto **ensancha** el alcance en vez de estrecharlo: el defecto es de la rama smu11 de 7.1.3
completa, así que también affecta a cualquier lectura de potencia hecha con esta máquina
como otro ASIC smu11. Y **obliga a no escribir "Arcturus lo tiene mal"**, que es la
formulación que la evidencia no sostiene.

## 3. Por qué no se afirma cuál de las dos es la buena

`AverageSocketPower` viene del **firmware SMU** por `SmuMetrics_t` (offset 26,
`smu11_driver_if_arcturus.h`), y el corpus **no contiene la unidad que el firmware usa
para ese campo**. Las dos lecturas posibles:

| hipótesis | coherente con | consecuencia |
|---|---|---|
| el firmware entrega **W** y el driver quiere **mW** | que el nombre de la constante sea "milliwatt per watt" y que 7.2.8 **multiplique** por 1000 | `×1000` correcto; `<<8` **sub-reporta 3.9×** |
| el firmware entrega **µW** y el driver quiere **mW** | — | `÷1000` haría falta; `×1000` sería un error nuevo |

La primera encaja con la aritmética que eligió upstream y con el nombre de la constante.
Pero **elegirla por coherencia de nombre es inventar**, y este proyecto no rellena huecos
por coherencia. **`NOT_DETERMINED`.** Lo que lo cerraría: la especificación del campo
`AverageSocketPower` en el firmware SMU de esta ASIC, que no está en el árbol; o el diff
upstream con su mensaje de commit, que daría la intención declarada.

Lo que **sí** está probado y no depende de esa elección:

```text
PROBADO   las dos versiones del driver escalan este metric de forma distinta
PROBADO   la constante que upstream usa vale 1000UL y ya existia en 7.1.3
PROBADO   el valor de 7.1.3 es ×256 y el de 7.2.8 es ×1000
PROBADO   no es especifico de Arcturus: navi10 en 7.1.3 hace lo mismo
NOT_DETERMINED   cual de las dos escalas es la correcta
```

## 4. La ruta hasta userspace, y por qué esto invalida mediciones

El `case` no es un callejón sin salida. Encadena así:

```text
arcturus_ppt.c:1063-1068
    case AMDGPU_PP_SENSOR_GPU_AVG_POWER:
            ret = arcturus_get_smu_metrics_data(smu,
                                                METRICS_AVERAGE_SOCKETPOWER, ...);

arcturus_ppt.c:660-661
            *value = metrics->AverageSocketPower << 8;      <-- aqui

  -> ioctl de amdgpu  ->  sysfs  /  debugfs
```

**Lo que este hallazgo invalida, con independencia de quién tenga razón:**

> Cualquier cifra de **potencia media del socket** obtenida de esta máquina por la vía
> `AMDGPU_PP_SENSOR_GPU_AVG_POWER` está escalada por un factor que el upstream **cambió**
> entre 7.1.3 y 7.2.8. Hasta que se sepa cuál de las dos es correcta, esas cifras
> **no son una medición** y no pueden entrar comobaseline ni como techo de potencia.

`09-POWER-CLOCKS/` tiene un nodo entero sobre límites de potencia, DPM y techo
sostenible. Este hallazgo le **pone una condición previa**: resolver la unidad antes de
usar cualquier número de vatios de esa vía. Es más barato descubrirlo aquí, leyendo dos
versiones de un fichero, que después de un benchmark entero.

**No** se afirma que el resto de sensores esté bien. Sólo que este tiene una divergencia
documentada entre dos versiones del propio vendor.

### 4.1 Límite de alcance que NO se salta

En la sesión anterior se midió que varios atributos `pp_*` de esta máquina devuelven
`EBUSY` al abrirlos. **No se ha vuelto a medir eso aquí** y no se afirma que el ioctl sea
legible en esta host en este momento. Lo probado es la **divergencia en el código**; que
sea observable o no en ejecución es una medición pendiente, distinta, y queda como tal.

## 5. Qué NO se hace aquí

- **No se "arregla" el driver del vendor.** Fuera de alcance (§1: el trabajo es sobre
  esta PC, no sobre upstream), y no es necesario: para el driver propio lo que cuenta es
  saber que la escala correcta **no** es 256.
- **No se escribe la unidad en ninguna constante.** `NOT_DETERMINED` es el estado.
- **No se afirma que la potencia real de esta GPU sea 3.9× mayor o menor.** Eso depende de
  la hipótesis del §3, que está abierta.

## 6. Procedencia

```text
7.1.3   RESEARCH/baseline/linux-7.1.3/drivers/gpu/drm/amd/pm/swsmu/smu11/arcturus_ppt.c:655-672
        ruta al ioctl:  arcturus_ppt.c:1055-1075
        hermano:       RESEARCH/baseline/linux-7.1.3/.../smu11/navi10_ppt.c  (mismo << 8)
7.2.8   rx550-upstream-7.2.8/linux-7.2.8/drivers/gpu/drm/amd/pm/swsmu/smu11/arcturus_ppt.c:655-672
constante  RESEARCH/kernelbuild/linux-7.1.3/include/linux/units.h:56
metodo     diff de dos lineas de fuente.  sin GPU, sin sudo, sin ejecucion
LIMITACION no se sabe la unidad que el firmware da a AverageSocketPower
```

```text
ESTADO=PROBADO · la divergencia 256 vs 1000 es REAL y de la FAMILIA smu11 en 7.1.3
       · el alcance propio (Arcturus) queda REFUTADO como hipotesis
       · la unidad del firmware sigue NOT_DETERMINED
CONSECUENCIA  09-POWER-CLOCKS: no usar cifras de potencia de AMDGPU_PP_SENSOR_GPU_AVG_POWER
              como medicion hasta cerrar la escala
Siguiente     1) diff upstream con mensaje de commit de la linea 661: dice la intencion
              2) unidad de AverageSocketPower en el firmware SMU de esta ASIC
              3) solo entonces cabe hablar de un techo de potencia por esta vía; §77
                 sigue sin numero defendible por esa via
```

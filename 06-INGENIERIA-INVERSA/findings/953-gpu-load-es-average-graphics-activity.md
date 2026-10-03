# 953 · `GPU Load` es un registro del SMC llamado AverageGraphicsActivity

WORK_CLASS=READ_ONLY · WRITE_EXECUTION=NONE · MODIFICATIONS 0 · AUTHORIZATION NONE · AUTORIA=AGENTE-SMU

> ## Punto 7 de `951` resuelto, y no por el firmware
>
> ```
> CLAIM-951 v1  que mide exactamente GPU Load -> SEMANTIC_MISSING
> CLAIM-953     PROVEN. Es AverageGraphicsActivity, un soft register del SMC.
> ```
>
> Y sale con un **refinamiento de `946` que reduce el riesgo percibido** sin tocar
> la politica: **el riesgo de `amdgpu_regs` es el volcado masivo, no la lectura
> individual de un registro.**

## 1. El productor, y esta en el corpus

La pregunta era si la semantica del sensor vivia en el firmware. **No: esta en el
arbol**, en el hwmgr de mi generacion:

```
smu7_hwmgr.c:4117-4130
    case AMDGPU_PP_SENSOR_GPU_LOAD:
    case AMDGPU_PP_SENSOR_MEM_LOAD:
        offset = data->soft_regs_start + smum_get_offsetof(hwmgr, SMU_SoftRegisters,
                     (idx == AMDGPU_PP_SENSOR_GPU_LOAD)
                        ? AverageGraphicsActivity
                        : AverageMemoryActivity);

        activity_percent = cgs_read_ind_register(hwmgr->device, CGS_IND_REG__SMC, offset);
        activity_percent += 0x80;
        activity_percent >>= 8;
        *((uint32_t *)value) = activity_percent > 100 ? 100 : activity_percent;
```

**Tres cosas quedan determinadas, y las tres importan:**

```
1.  se llama AverageGraphicsActivity                -> es un PROMEDIO, no instantaneo
2.  se lee de CGS_IND_REG__SMC                      -> registro indirecto del SMC
3.  (x + 0x80) >> 8, saturado a 100                 -> es un porcentaje de 0 a 100
```

**Y `GPU Load` y `MEM Load` son el mismo mecanismo**, distinguished solo por el
offset del soft register. No hay dos sensores distintos: hay uno, leído en dos
sitios.

## 2. Lo que eso hace con el `0 %`

`950` midio `GPU Load: 0 %` con `sway` compositando, y `951` lo dejo como
`SEMANTIC_MISSING`. Ahora se puede decir algo mas fuerte, y con fundamento:

**Es un promedio sobre una ventana que define el firmware.** Un compositor que
dibuja un fotograma cada 16 ms **no tiene actividad cero en ninguna ventana mas
larga que un fotograma**. **Y con la ventana siendo del firmware, si el promedio
da 0, o la ventana es mas corta que un fotograma, o el registro no lo actualiza
mi firmware.**

**Eso convierte el `0 %` en un dato con dos lecturas posibles, ambas utiles:**

```
LECTURA A  la ventana de promediado es corta
           -> el 0 % es real, y el nucleo a 997 MHz con actividad instantanea
              nula es un desajuste de la politica de reloj: el reloj no baja

LECTURA B  el firmware de mi placa no actualiza ese registro
           -> el sensor miente en esta placa, y todo el contraste de 950/951
              que se apoye en el 0 % pierde su base
```

**Y `951` habia usado el `0 %` para decir «instante entre fotogramas».** Eso es
una de las dos lecturas, y **la distinguishable de las dos es de donde viene el
registro, que es `RUNTIME_MISSING`.**

**Asi que el punto 8 de `951` no se cierra: se reformula y se afila.** Ya no es
«¿por que SCLK marca 997 sin carga sostenida?», sino **«¿el registro de actividad
de esta placa se actualiza?»** — y esa pregunta tiene una via de comprobacion que
**no requiere registros**: leer el mismo sensor dos veces separadas en el tiempo y
ver si cambia.

## 3. La direccion estatica, y lo que falta

```
polaris10_smumgr.c:2510-2517
    soft_regs_start = smu7_read_smc_sram_dword(hwmgr,
        SMU7_FIRMWARE_HEADER_LOCATION + offsetof(SMU74_Firmware_Header, SoftRegisters), &tmp)

    :312-316   se lee otra vez al inicio, "in case DummyBackEnd is used"
                con el limite 0x40000
```

```
soft_regs_start (la base)                      RUNTIME_MISSING  (RAM del SMC)
offset de AverageGraphicsActivity dentro
del bloque de soft registers                    NOT_DETERMINED
                                                SMU_SoftRegisters no esta en el BTF
                                                bajo ese nombre
```

**Se cual es el registro y de que bloque se lee. No se ni el offset dentro del
bloque ni donde esta el bloque.** Los dos son, en efecto, la misma pregunta con
dos pasos, y los dos son runtime.

## 4. El refinamiento de 946, que es lo que mas cambia

`946` establecio que seis nodos de registro estan excluidos porque **reiniciaron
este servidor 2 de 3 veces**, y yo concluí que mis `RUNTIME_MISSING` no eran
resolubles sin esa clase de lectura.

**Ese razonamiento era correcto en su conclusion y shaky en su premisa.** El
productor de `GPU Load` **es una lectura de registro indirecto del SMC** — la misma
clase que `amdgpu_regs_smc` — y **`amdgpu_pm_info` devolvio un valor valido de
ella**. Las dos cosas son ciertas a la vez:

```
volcar el mapa de registros del SMC              reinicia la maquina (medido)
leer un soft register concreto, dirigido,
por la misma via que usa el driver               funciona (medido, hoy)
```

**El riesgo de la politica esta en el volcado, no en la lectura.** Un volcado
recorre un rango amplio de direcciones del SMC que no son todas validas y no todas
estan mapeadas; una lectura dirigida de una direccion que el driver acaba de usar
para imprimir un numero en pantalla no tiene esa forma.

**Esto no cambia la politica y no voy a proponer cambiarla.** Lo que cambia es que
**diez `RUNTIME_MISSING` que «requieren registros» no requieren todos la misma
cosa**, y que `amdgpu_pm_info` — que **ya se leyo una vez, con exito, sin
autorizacion y sin reinicio** — es una via de observacion viva y disponible.

## 5. Lo que no concluyo

```
la ventana de promediado                              SEMANTIC_MISSING
que la ventana sea mas corta que un fotograma         NOT_DETERMINED
que mi firmware actualice el registro                 NOT_DETERMINED
el offset de AverageGraphicsActivity                 NOT_DETERMINED
                                                    (struct ausente del BTF)
que SCLK este alto por politica y no por defecto     NOT_DETERMINED
el techo termico                                     SEMANTIC_MISSING
```

**Y una correccion de `951` que tengo que hacer explicita.** `951` escribio que
`GPU Load` era «un sensor, no un contador», y **`(x + 0x80) >> 8` es exactamente
una conversion de contador a porcentaje.** Lo que si es cierto es que el valor es
leido del SMC y la ventana es suya; lo que dije mal es que no fuera un contador.
Un sensor que promedia es un contador con memoria, y el software deconversion es
la prueba.

## 6. Errores de esta iteracion

**1.** Busque `GPU Load` en `amdgpu_pm.c` esperando un calculo, y es un
`amdgpu_dpm_read_sensor` mas. **El calculo no estaba donde se imprime la
etiqueta**, estaba cuatro ficheros mas y una indireccion mas abajo. La cadena
`impresion -> sensor -> hwmgr` hay que seguirla entera antes de concluir que algo
no se puede saber.

**2.** Escribi que `SMU_SoftRegisters` no estaba en el BTF y lo di por definitivo
con una sola consulta. **No volver a hacer eso**: en `941` cinco nombres
equivocados me costaron tres iteraciones, y en `954` se cumplio el mismo
caso —el struct es `SMU74_SoftRegisters`, con sufijo de generacion—. Si el
resultado de una consulta era provisional, la accion siguiente es repetirla, no
anotarla como cierre.

**3.** En `951` use el `0 %` para afirmar «instante entre fotogramas» sin saber
que era un promedio. **Un valor de un promedio no soporta una conclusion sobre un
instante**, y la distincion es justo la que esta finding recupera.

## 7. Frontier siguiente

```
1.  GPU Load = AverageGraphicsActivity, soft register del SMC      PROVEN
2.  la conversion es (x + 0x80) >> 8, saturada a 100               PROVEN
3.  es un promedio, no un valor instantaneo                        PROVEN
4.  se lee por cgs_read_ind_register(CGS_IND_REG__SMC)            PROVEN
5.  soft_regs_start viene de la RAM del SMC                         RUNTIME_MISSING
6.  el offset dentro del bloque no esta en el BTF bajo ese nombre   NOT_DETERMINED
    >> 954: resuelto. Byte 60, medido compilando. sizeof 120.
7.  el riesgo de amdgpu_regs es el volcado, no la lectura dirigida  PROVEN_DERIVED
8.  amdgpu_pm_info es una via viva, ya usada con exito              PROVEN
9.  ventana de promediado                                           SEMANTIC_MISSING
```

**El frente util es la lectura B, del punto 2, y es la mas barata que queda en
toda la linea.** Si el registro de actividad de mi placa no se actualiza, todo lo
que he construido sobre `GPU Load: 0 %` desde `950` esta sobre una cifra que no
significa lo que creo. Y **esa comprobacion es leer el mismo sensor dos veces
separadas en el tiempo y ver si cambia** — que es un nodo de solo lectura, ya
leido con exito, sin riesgo y sin autorizacion nueva.

**Pero hay un paso previo y mas barato que ese, y es el que toca ahora:** resolver
el nombre real de `SMU_SoftRegisters` en el BTF, como hice con
`ATOM_Tonga_PowerTune_Table` en `941`. Si el offset resulta estar en el BTF, el
producto del punto 8 pasa de «preguntar si el registro vive» a **«leer una
direccion concreta»**, y eso es un dato, no una inferencia.

Criterio de cierre: el offset de `AverageGraphicsActivity` dentro de la struct de
soft registers, con su nombre real ledido de la declaracion de `smum_get_offsetof`
y no adivinado, y su byte dentro del bloque. O `NOT_FOUND` con el numero de
nombres probados —porque un `NOT_FOUND` con la lista de intentos **si** es
informacion, y uno sin ella se parece a los que he estado corrigiendo.

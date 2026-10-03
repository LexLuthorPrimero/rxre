# 945 · La revisión nunca se midió, y PSTATE_SCLK = 214 MHz confirma el nivel 0

> ## v2 — REFUTADO por `965`. La revisión **sí** estaba medida.
>
> ```
> 06-INGENIERIA-INVERSA/evidencia/boot-amdgpu-7.1.3-200.nobara.fc44.x86_64.log:10
>   amdgpu 0000:01:00.0: initializing kernel modesetting
>   (POLARIS12 0x1002:0x699F 0x1002:0x0B04 0xC7).
> ```
>
> **REVISION = 0xC7**, contrastado campo a campo con el formato que imprime el driver en
> `amdgpu_device.c:3716`. Como `0xC7 != 0xCF`, **la rama de `smu7_hwmgr.c:1975` NO se
> toma** y el ClockStretcher queda **activo** en mi placa.
>
> **El error de esta v1 fue de alcance, no de lectura:** su §44 buscó en `revkit/`, y la
> evidencia estaba en `06-INGENIERIA-INVERSA/evidencia/`. Un `0` con alcance acotado se
> convirtió en afirmación de ausencia sobre todo el proyecto.
>
> **Lo que sigue siendo cierto:** el `0xC7` de `revkit/bootcheck.py:141` **es un fixture**.
> Lo que era falso es la conclusión de que no existía ninguna otra fuente. El valor del
> fixture era correcto; le faltaba la evidencia que lo respaldara, y esa estaba aquí.
>
> Ver §1 (Correcto sobre el fixture) y §5 (Incorrecto sobre la ausencia). Todo lo que
> `945` dice de `PSTATE_SCLK = 214 MHz` y del nivel 0 queda intacto: esa parte no dependía
> de la revisión.

WORK_CLASS=READ_ONLY · WRITE_EXECUTION=NONE · MODIFICATIONS 0 · AUTHORIZATION NONE · AUTORIA=AGENTE-SMU

> ## Dos resultados opuestos en una iteración
>
> **1.** La revisión de mi placa **no está medida en ninguna parte de este
> proyecto.** El `0xC7` que `947` (antes 944) trata como `OBSERVED` es un **vector de test
> sintético**. Corregido.
>
> **2.** Una captura runtime que existía y no había usado **corrobora el nivel 0
> de mi tabla de SCLK de forma independiente**, y desmiente una suposición que
> venía arrastrando.

## 1. `0xC7` es un fixture, no una observación

Iba a usar `revkit/bootcheck.py:141` como evidencia de la revisión. Leí el contexto
antes de citarla:

```
revkit/bootcheck.py:135-146
    def linea(n, v, t):
        return ("oct 02 14:55:03 kernel: amdgpu 0000:01:00.0: detected ip block " ...)

    BUENO = "\n".join([
        "oct 02 kernel: amdgpu 0000:01:00.0: initializing kernel modesetting "
        "(POLARIS12 0x1002:0x699F, 0xC7)",                        <<<<< aqui
        linea(*ESPERADOS[0]), ...
        "oct 02 kernel: amdgpu 0000:01:00.0: VRAM: 2048M",
    ]) + "\n"

    :149   r = analizar(BUENO)
```

**`BUENO` es una cadena construida a mano para probar el parser**, con una fecha
escrita dentro (`oct 02 14:55:03`). **El `0xC7` de la línea 141 es un dato
inventado para el test, no un dato leido de mi maquina.**

Y la búsqueda de su procedencia real:

```
revkit/capturas/  (21 ficheros), buscando "revision" o "699f" o "POLARIS12"
    0 coincidencias
revkit/ en general, buscando 0xC7 / 0xCF
    0 coincidencias fuera de bootcheck.py
```

**Estado correcto: `NOT_FOUND`.** La revisión de mi placa **nunca se ha medido
en este proyecto**, y la unica aparicion de un valor es un fixture.

Esto **degrada `947` punto 8** de `OBSERVED` a `NOT_FOUND`, y con ello la
fragilidad es mayor de lo que escribí:

```
smu7_hwmgr.c:1975-1976   si (device == 0x699F && revision == 0xCF)
                         -> phm_cap_unset(PHM_PlatformCaps_ClockStretcher)
```

**Toda la linea de clock stretching —`929`, `931`, `947`— depende de que la
revision NO sea `0xCF`, y ese dato no se ha medido nunca.** No es «un nibble sin
remedir»: es «un nibble sin medir», con un fixture en su lugar.

**Y hay una consecuencia de método que importa mas que el dato:** un fixture de
self-test con un valor verosimil en medio es una **fuente de evidencia falsa**. Si
alguien —o yo mismo— lo cita como observacion, la conclusion hereda una
fabricacion como si fuera una medida. **Un vector de test tiene que ser
reconocible como tal en su contenido, y este no lo es: parece una linea de log
real.**

## 2. La captura que no habia usado, y lo que confirma

```
revkit/capturas/amdgpu_pm_info.txt   1731 B    .err = 0 B  (captura limpia)

GFX Clocks and Power:
    300 MHz (MCLK)
    997 MHz (SCLK)
    214 MHz (PSTATE_SCLK)      <<<<<<<<
    625 MHz (PSTATE_MCLK)
    812 mV (VDDGFX)
    5.157 W (current SoC)
GPU Temperature: 42 C
GPU Load: 0 %
```

**`PSTATE_SCLK = 214 MHz` es exactamente mi nivel 0**, derivado de `ulSclk = 21400`
en la tabla de dependencia SCLK del VBIOS (`0x9D15`), con la unidad de 10 kHz
establecida en `931` leyendo la cadena de formato del kernel.

```
VBIOS  0x9D15  rec 0  ulSclk = 21400  ->  21400 / 100 = 214 MHz   (derivado, estatico)
sysfs  amdgpu_pm_info.txt   PSTATE_SCLK = 214 MHz                  (medido, runtime)
```

**Es la primera corroboracion runtime contra un resultado estatico de toda la
linea.** Hasta ahora todo se habia corroborado entre fuentes estaticas —VBIOS
contra constantes del driver, BTF contra dominio—. Esta vez es **el hardware de mi
placa diciendo el numero**.

Y confirma lo que `931` §5 afirmo como `CORROBORATED` solo por vias estaticas:
**el nivel 0 es el estado de reposo.** Ahora esta confirmado por el reloj que la
GPU usa realmente cuando esta sin carga, con `GPU Load: 0 %`.

## 3. Y desmiente una suposicion que venia arrastrando

```
SCLK observado ahora:  997 MHz
mis 8 valores de la tabla de dependencia:  214  551  734  980  1000  1020  1046  1071
```

**997 no es ninguno de los ocho.** Esta entre 980 y 1000.

**Los ocho valores de la tabla de dependencia SCLK NO son los estados DPM que la
GPU recorre.** Son **puntos de consulta de voltaje**, y el reloj actual esta en un
punto que no coincide con ninguno.

Eso confirma como `NOT_DETERMINED` lo que `931` §6.3 dejo abierto —«que nivel DPM
corresponde a cada nivel de esta tabla»— y **ademas lo vuelve cerrado en
negativo**: no es que no se haya buscado la correspondencia, es que **no puede
existir una correspondencia uno a uno**, porque la GPU opera en frecuencias que
esa tabla no contiene.

**Y esto obliga a revisar la lectura que hice de `947`.** En `947` llame
«nivel 0» y «nivel 7» a los extremos de esta tabla, y calcule los umbrales
`acomp` por fila. Eso **sigue siendo correcto** como calculo sobre la tabla, pero
**«nivel» aqui es un indice de la tabla de voltaje, no un estado DPM.** La
distincion no la habia hecho y cambia lo que significan los numeros: el
acompanado de 1886 del indice 7 es el acompanado **para la consulta de voltaje de
1071 MHz**, no para un estado de reloj que la GPU recorra.

## 4. Tres capturas vacias, que no son evidencia de nada

```
revkit/capturas/amdgpu_mst_topology.txt     0 B
revkit/capturas/amdgpu_sensors.txt          0 B
revkit/capturas/psp_spirom_dump.txt         0 B
```

**Tres artefactos de captura existen y estan vacios.** `amdgpu_sensors.txt` en
particular es el que habria dado temperatura y voltaje con carga, que es justo lo
que la linea de rendimiento necesita.

Un fichero de 0 bytes **no es una medida de cero**: es una captura que no produjo
nada, y por que —permiso, error de permisos, o el fichero no existe en ese
momento— **no consta**. Los tres `.err` **tampoco** estan a cero en los casos que
puedo comprobar, lo que sugiere que el fallo fue silencioso o que el comando no se
llego a ejecutar. **Sin `.err` no hay causa, y sin causa no se sabe si el
observable es `NOT_FOUND` o simplemente no se intento.**

**Ninguno de los tres es evidencia de ausencia. Los tres son `INVALID_RESULT`
hasta que se sepa por que estan vacios.**

## 5. Estado corregido de la linea

```
1.  asic_type de 0x699F = CHIP_POLARIS12                    PROVEN
2.  ro_range = 1100..2100, rama else sin condicion runtime   PROVEN
3.  el acompanado por fila: 1010,1213,...,1886              PROVEN
4.  el indice 0 nunca aplicaria offset con ro >= 1100       PROVEN
5.  el VBIOS desactiva CKS ahi: corroborado con mecanismo   CORROBORATED
6.  nivel 0 (214 MHz) = PSTATE_SCLK observado en mi maquina  CORROBORATED  NUEVO
7.  los 8 valores NO son estados DPM: SCLK real = 997 MHz   CORROBORATED  NUEVO
8.  ro concreto                                              RUNTIME_MISSING
9.  revision de mi placa: NOT_FOUND, nunca medida            NOT_FOUND      CORREGIDO
10. 0x699F + 0xCF apagaria ClockStretcher entero            PROVEN
11. el PP legacy se elige por MP1 HWIP, no por ASIC          PROVEN
12. 3 capturas de 0 bytes: INVALID_RESULT sin causa          INVALID_RESULT NUEVO
```

**La linea ya no es `SATURATED`, y ahora por dos razones distintas y ambas
con nombre:** una contradiccion resuelta a medias (punto 7, que obliga a renombrar
«nivel» en todo lo anterior) y una dependencia externa de un bit sin medir
(punto 9).

## 6. Errores de esta iteracion

**1. Iba a citar `bootcheck.py:141` como `OBSERVED` sin haber leido el bloque que
lo contiene.** Si lo hubiera citado sin mirar, esta iteracion habria
**ratificado un fixture como si fuera una medida**, y habria reforzado la
conclusion mas fragile de la linea. **Un valor que aparece en un fichero de test
es un test, hasta que se demuestre lo contrario —y la carga de la demostracion es
del que cita, no del que lo lee.**

**2.** En `947` escribi «los ocho niveles» y «nivel 7» creyendo que eran estados
DPM. La captura muestra que no lo son. **Un nombre de fila no es una categoria
semantica**, y durante seis hallazgos use «nivel» como si lo fuera.

**3.** No habia inventario de que capturas estan vacias, y me pase un
`amdgpu_pm_info.txt` que estaba ahi desde el principio. **Un recurso no usado es
un recurso cuyo coste ya se pago y cuyo beneficio sigue sin cobrar.**

## 7. Frontier siguiente

**Lo mas util ahora no es otra medida: es un inventario con estado de las 21
capturas de `revkit/capturas/`, que diga de cada una que es, cuando se produjo,
si esta vacia y por que, y que observable podria dar.**

Tres consecuencias concretas de esa accion:

1. `amdgpu_sensors.txt` vacio es **la pista mas directa al techo termico**, que es
   la variable que decide el rendimiento sostenido y la que toda esta linea
   identifica como `RUNTIME_MISSING`.
2. Saber si las capturas se pueden reproducir sin autorizacion nueva, o si
   necesitan una, determina si `B_RUNTIME` es una decision o un tramite.
3. `amdgpu_mst_topology.txt` y `psp_spirom_dump.txt` vacios son, por su nombre,
   la via natural para **corroborar desde fuera el VBIOS de 58880 bytes que use
   durante toda la linea**, que hasta ahora solo tengo del lado del driver.

Criterio de cierre: una tabla de las 21 capturas con bytes, origen, fecha si
consta, y clasificacion `VALIDA` / `VACIA_INVALIDA` / `NO_PRODUCIDA` con el motivo;
y una respuesta explicita de si volver a generarlas requiere autorizacion.

Ese es el frente con mas desbloqueo por unidad de esfuerzo de los que quedan, y
es el que decide si el resto de la linea puede avanzar en runtime o no.

# 1097 — CORRIGE 1091: el struct correcto es el de Arcturus (1012 bytes, no 1240), y el resultado negativo se refuerza

```text
AGENCIA=RX550-INVESTIGACION · WORK_CLASS=AGENT-MAIN/RE
CLASSIFICATION=CORRECTION · TRACK=STATIC+COMPILED
GENERADO=2026-10-04 · MEDIDO=EN ESTA HOST
CORRECTS=1091-pp-table-son-778-y-pptable-son-1240.md
AFECTADO=06-INGENIERIA-INVERSA/PPT-DECODE/  (instrumento corregido)
ORIGEN=1091 (mi propio error: compile el header equivocado)
ESTADO=PROBADO · la CIFRA del 1091 estaba mal · la CONCLUSION aguanta
herramienta   06-INGENIERIA-INVERSA/PPT-DECODE/extrae_arcturus.py + sz.c (C)
```

## 0 · Qué estaba mal y qué no

| | `1091` decía | MEDIDO |
|---|---|---|
| `sizeof(PPTable_t)` | 1240 | **1012** |
| truncado al | 62,7 % | **76,9 %** |
| bytes que faltan | 462 | **234** |
| el blob no contiene las frecuencias DPM | sí | **sí, y ahora con el struct correcto** |
| `pp_table` no es atajo para la curva V/F | sí | **sí** |

**La conclusión del `1091` se sostiene. Los números no.** Y eso es exactamente el
motivo por el que las conclusiones y las cifras van separadas en un informe: si
hubiera publicado la conclusión con la cifra dentro, el error habría viaja con ella.

## 1 · EL ERROR, Y ES DE LOS QUE ESTE PROYECTO MIDE

Compilé `powerplay/inc/smu11_driver_if.h`. **El driver no usa ese header.**

```c
/* arcturus_ppt.c:34 */
#include "smu11_driver_if_arcturus.h"
```

El que usé es el **genérico de Navi11**. Los dos declaran `PPTable_t` y los dos
compilan, y por eso el error no se manifesto como un fallo sino como un **número
plausible**.

| | Navi11 (`powerplay/inc/`) | **Arcturus (`swsmu/inc/pmfw_if/`)** |
|---|---|---|
| `sizeof(PPTable_t)` | 1240 | **1012** |
| `PPCLK_COUNT` | 11 | **6** |
| `FreqTableGfx` en el offset | 352 | **248** |
| forma de los límites | `SocketPowerLimitAc0`, `Ac1`… | `SocketPowerLimitAc[PPT_THROTTLER_COUNT]` |

**`PPCLK_COUNT = 6` contra 11 explica casi toda la diferencia de tamaño**, y es
precisamente el campo que gobierna `DpmDescriptor[PPCLK_COUNT]`, `DcModeMaxFreq[PPCLK_COUNT]`
y los ocho `FreqTable*`.

**El mecanismo que lo hace peligroso:** cuando el struct es el equivocado, los
offsets existen, los tipos existen y los números salen. Un `sizeof` es la medición
más fácil de repetir mal y la más difícil de detectar sin una segunda fuente — y la
segunda fuente estaba a **cinco líneas** en el `#include` del fichero que estaba
leyendo.

## 2 · EL NEGATIVO SE REFUERZA, Y CON EL OFFSET CORRECTO

Repito la comprobación con el header correcto:

```text
FreqTableGfx @248, 16 x uint16
  tabla    : [0, 1792, 255, 0, 0, 2048, 255, 0, 0, 256, 8, 0, 21400, 0, 0, 32768]
  observados: [214, 551, 734, 980, 1000, 1020, 1046, 1071]
  coinciden: NO

TedgeLimit      @36 = 28928      <- un limite termico de 28928
ThotspotLimit   @38 = 26626
MinVoltageGfx   @68 = 21248
MaxVoltageGfx   @72 = 0          <- voltaje maximo 0
MaxVoltageStepGfx @760 = 0
```

**Con el struct correcto los valores siguen siendo físicamente imposibles**, y las
frecuencias siguen sin estar. La conclusión del `1091` no dependía del struct
equivocado: dependía de que **los campos que deben contener frecuencias no las
contienen**, y eso se cumple en los dos mapas.

**Y hay un dato nuevo que explica por qué la decodificación ingenua falla**, y que el
`1091` no tenía:

```c
/* smu13_driver_if_v13_0_7.h — DroopInt_t, el mismo tipo que usa Arcturus */
typedef struct {
  uint32_t a;  // store in IEEE float format in this variable
  uint32_t b;  // store in IEEE float format in this variable
  uint32_t c;  // store in IEEE float format in this variable
} DroopInt_t;
```

**Varios campos de la PPT no son enteros: son floats empaquetados en `uint32`.**
Cualquier decodificación que lea la tabla como `uint16`/`uint32` enteros va a
producir exactamente los valores que acabo de medir. Eso es una causa candidata de
la basura, y **es distinta de la que propuse** en el `1091 §2` ("el layout del
firmware no es el struct").

## 3 · LAS DOS SUSTITUCIONES, DECLARADAS

El extract del corpus está incompleto: `smu11_driver_if_arcturus.h` **no declara**
`PPT_THROTTLER_COUNT` ni `DroopInt_t`. Sin ellos no compila.

Los saqué de `smu13_driver_if_v13_0_7.h`, de la **misma familia smu**, y **está
escrito en el `.h` generado y en la docstring del extractor**, no escondido:

```c
/* SUSTITUCION DECLARADA -- 2 simbolos que el header de Arcturus no declara
   porque el extract del corpus esta incompleto. Valor leido de smu13 (misma
   familia smu). Solo afecta al TAMANO del array SocketPowerLimit*, no a la
   semantica de ningun campo. */
#define PPT_THROTTLER_COUNT 4
typedef struct { uint32_t a; uint32_t b; uint32_t c; } DroopInt_t;
```

**Lo que esto NO permite:** usar el struct de smu13 entero para Arcturus. Eso sería
conducir una conclusión sobre esta ASIC con la semántica de otra, que es lo que
`§4 TARGET MISMATCH` prohíbe. Aquí solo se toman **dos valores de dimensión**, y su
efecto es acotable: `PPT_THROTTLER_COUNT` multiplica `SocketPowerLimitAc[]`,
`SocketPowerLimitAcTau[]`, `SocketPowerLimitDc[]`, `SocketPowerLimitDcTau[]` y
`Power[][POWER_SOURCE_COUNT]`. Si el valor real fuera otro, **el `sizeof` cambia en
esas dimensiones y en ningún otro sitio**, y ninguna de ellas contiene frecuencias.

**Con la sustitución:**

```text
PPT_THROTTLER_COUNT = 4  ->  SocketPowerLimitAc[4]      (16 B)
                            SocketPowerLimitAcTau[4]   (16 B)
                            SocketPowerLimitDc[4]      (16 B)
                            SocketPowerLimitDcTau[4]   (16 B)
                            Power[4][2]                 (16 B)
```

## 4 · EL ESTADO REAL DE `pp_table`

```text
blob                                  778 B   (09-POWER-CLOCKS/evidence/pp_table.txt)
sizeof(PPTable_t) ARCTURUS           1012 B   MEDIDO por el compilador
faltan                                234 B   (23.1 %)
dentro de la ventana                 todo Version, los limites, VoltageOffset,
                                    Min/MaxVoltage, FreqTable* @248
fuera de la ventana                  MaxVoltageStepGfx @760 y 234 B mas
```

Y el veredicto se queda donde estaba:

> **`pp_table` no se puede decodificar con el `PPTable_t` de este ASIC.** Los campos
> que deberían contener las frecuencias DPM no las contienen en ninguno de los dos
> structs probados, y los que sí caen dentro de la ventana dan valores físicamente
> imposibles. Causa candidata principal ahora: **varios campos son floats
> empaquetados**, y la revisión de firmware que envía esta Polaris12 sigue siendo
> `NOT_DETERMINED`.

## 5 · PROCEDENCIA

```text
instrumento  06-INGENIERIA-INVERSA/PPT-DECODE/
             extrae_arcturus.py  (el header que USA el driver) + ppt_arcturus.h + sz.c
             extrae_tipo.py     (el generico Navi11, que es el que USO POR ERROR)
             mapa.c  offs.c
evidencia    arcturus_ppt.c:34  #include "smu11_driver_if_arcturus.h"
medida 1     sizeof(PPTable_t) Arcturus = 1012   (C, compilador)
medida 2     sizeof(PPTable_t) Navi11    = 1240   (C, compilador)
medida 3     blob 778 B -> faltan 234 B
medida 4     FreqTableGfx @248 sin las 8 frecuencias observadas
medida 5     TedgeLimit=28928, MaxVoltageGfx=0, MaxVoltageStepGfx=0
medida 6     DroopInt_t declara sus tres uint32 como IEEE float
escrituras   0 en el arbol.  GPU intacta.
```

**Lo que este documento NO prueba.** No prueba que el blob sea una `PPTable_t` de otra
revisión: eso sigue siendo `NOT_DETERMINED`, y este documento **no lo resuelve**, solo
corrige la cifra y refuerza el negativo. No prueba que las frecuencias estén ausentes
—pueden estar en una codificación que no he probado, y ahora sé que **al menos una
parte de la tabla es float**, lo que abre esa posibilidad en vez de cerrarla. No
toco la GPU y no he medido rendimiento.
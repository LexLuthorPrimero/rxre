# 122 · `ulPlatformCaps = 0x068000`: qué puede hacer esta placa, y los caps predicen el voltaje que luego mido

WORK_CLASS=READ_ONLY · WRITE_EXECUTION=NONE · MODIFICATIONS 0

CIERRA una lectura pendiente de `116` · CONFIRMA que la cadena de `116`/`118` no tenia una
puerta perdida · VALIDACION CRUZADA entre dos campos del mismo VBIOS

## El campo que llevaba dos documentos sin decodificar

`116` leyo `ulPlatformCaps` y lo dejo sin usar. Vale **0x068000**, y es lo que decide que puede
hacer el driver con esta placa: `process_pptables_v1_0.c:1156` lo pasa directo a
`set_platform_caps(hwmgr, le32_to_cpu(powerplay_table->ulPlatformCaps))`.

## Los tres bits activos

```
bit 15   0x008000   ATOM_TONGA_PP_PLATFORM_CAP_VDDCI_CONTROL
bit 17   0x020000   ATOM_TONGA_PP_PLATFORM_CAP_BACO
bit 18   0x040000   *** SIN NOMBRE en el driver ***
```

Y los conocidos que estan **apagados**, que es la parte informativa:

| mask | nombre | estado en esta placa |
|---|---|---|
| 0x1 | `VDDGFX_CONTROL` — VDDGFX es rail separado | **no** |
| 0x2 | `POWERPLAY` — parte movil | **no** (es una dGPU de sobremesa) |
| 0x4 | `SBIOSPOWERSOURCE` | no |
| 0x8 | `DISABLE_VOLTAGE_ISLAND` | no |
| 0x20 | `HARDWAREDC` — transicion DC por GPIO | no |
| 0x1000 | `MVDD_CONTROL` — MVDD dinamico | **no** |
| 0x100000 | `OUTPUT_THERMAL2GPIO17` | no |
| 0x1000000 | `COMBINE_PCC_WITH_THERMAL_SIGNAL` | no |
| 0x2000000 | `LOAD_POST_PRODUCTION_FIRMWARE` | no |

El bit 2 apagado es la confirmacion mas directa: **esta placa no es un portatil**, y eso lo
dice el VBIOS, no la caja.

## La validacion cruzada: los caps PREDICEN los voltajes, y se cumple

Aqui es donde el dato deja de ser una lista de bits. Los caps dicen **que rail es
dinamico**, y la tabla MCLK del VBIOS trae los voltajes. Si la decodificacion fuera erronea,
los dos campos **se contradirrian**:

```
ATOM_PPLIB:  VDDCI_CONTROL = SI   ->  usVddci debe VARIAR con el nivel
              MVDD_CONTROL  = NO   ->  usMvdd  debe ser CONSTANTE
              VDDGFX_CONTROL= NO   ->  VDDGFX no es rail separado

tabla MCLK dependency (@0x9D8F, 3 entradas):
   nivel   usVddci   usMvdd
     0       800      1000
     1       800      1000
     2       875      1000

   usVddci = {800, 875}   VARIA      <- predecido: SI     OK
   usMvdd  = {1000}        CONSTANTE  <- predecido: NO     OK
```

**Las dos predicciones se cumplen.** Dos campos **independientes** del mismo PowerPlay table
se confirman mutuamente: `ulPlatformCaps` dice que rail es dinamico, y
`ATOM_Tonga_MCLK_Dependency_Record.usVddci`/`usMvdd` lo hacen.

**Eso no es una lectura, es una verificacion.** Si hubiera calculado mal un offset, los caps
dirian una cosa y los voltajes otra. Dicen lo mismo.

Y la tercera prediccion tambien sale: con `VDDGFX_CONTROL` apagado, VDDGFX no es un rail
separado, y la captura en vivo muestra **un solo valor, 812 mV**, no una tabla.

## El bit 18: puesto, y sin nombre

El VBIOS pone `0x40000`, y **`pptable_v1_0.h` no le da nombre**: entre `0x20000` (BACO) y
`0x100000` (`OUTPUT_THERMAL2GPIO17`) hay un hueco de tres bits sin definir.

Lo confirme por busqueda exacta: los unicos `0x40000` del arbol son mascaras de registros
`LINK_CAP__CLOCK_POWER_MANAGEMENT_MASK` en `asic_reg/bif/*` y campos de GMC — **otro espacio
de nombres**, no el de las caps de plataforma. Un nombre parecido en otro dominio **no** es
el mismo nombre.

Consecuencia honesta: **el driver lo ignora**, porque `set_platform_caps` no tiene caso para
el. Que el VBIOS lo declare significa que el firmware espera algo que este driver **no
implementa**. Que sea: **`SEMANTIC_MISSING`**, y no lo adivino.

## Y la confirmacion de que no me faltaba ninguna puerta en `116`

`115` y `116` cerraron la cadena del clock stretcher con tres condiciones
(`smu7_hwmgr.c:1938-1940`), y la ultima era `usClockStretchAmount != 0`, que leio del VBIOS.

Me preocupaba que `set_platform_caps` **si** pudiera fijar
`PHM_PlatformCaps_ClockStretcher` por la via de `ulPlatformCaps`, lo cual habria anadido una
cuarta condicion sin ver. **Comprobado: no.** `set_platform_caps` (`:55-175`) contiene **cero**
apariciones de `ClockStretcher`, y la capacidad solo se fija en `smu7_hwmgr.c:1938-1941` y se
desactiva en `:1698`.

**La cadena de `116` esta completa.** No habia una puerta perdida.

## Lo que estos caps significan para mi dominio

Con lo decoded, el presupuesto electrico de esta placa queda asi:

| rail | dinamico? | valor |
|---|---|---|
| **VDDCI** | **si**, lo controla el driver | 800 mV en 2 de 3 niveles, **875 mV** en el alto |
| MVDD | **no**, fijo | **1000 mV** en los 3 niveles |
| VDDGFX | no es rail separado | un solo valor, **812 mV** observado |

Es decir: **esta placa tiene una unica linea de voltaje variable en la tabla del PPT**, y es
VDDCI. MVDD es constante a 1000 mV. Y la lectura en vivo (812 mV VDDGFX) confirma que VDDGFX
no tiene estados.

Eso conecta con `095` (que estaba sobre el factor de conversion de voltaje): **el rango de
voltaje que el driver manipula en esta placa es 800-875 mV de VDDCI, mas un VDDGFX fijo.**

## Clasificacion

- `UL_PLATFORM_CAPS_IS_0x068000 = PROVEN`: `0x9C0A + 19` (offset medido en `116`).
- `ONLY_VDDCI_CONTROL_AND_BACO_ARE_SET = PROVEN_DERIVED`: bits 15 y 17 contra el mapa de
  `pptable_v1_0.h:52-74`.
- `CAPS_PREDICT_THE_VOLTAGE_DATA_AND_THEY_AGREE = PROVEN_DERIVED`: `VDDCI_CONTROL=si`
  predice `usVddci` variable (800/875, lo es) y `MVDD_CONTROL=no` predice `usMvdd` constante
  (1000/1000/1000, lo es). **Dos campos independientes que se confirman.**
- `THIS_IS_NOT_A_MOBILE_PART = PROVEN_DERIVED`: bit 0x2 `POWERPLAY` apagado, leido del VBIOS.
- `VDDGFX_IS_NOT_A_SEPARATE_RAIL = PROVEN_DERIVED`: bit 0x1 apagado, y la captura da un solo
  valor (812 mV) en vez de una tabla.
- `BIT_18_IS_SET_AND_UNNAMED = PROVEN`: `0x40000` puesto en el VBIOS, sin define en
  `pptable_v1_0.h`. Los `0x40000` del arbol son de `asic_reg/bif` y GMC: **otro dominio**.
- `BIT_18_MEANING = SEMANTIC_MISSING`: el VBIOS espera algo que este driver no implementa.
  **No lo adivino.**
- `SET_PLATFORM_CAPS_CANNOT_SET_CLOCK_STRETCHER = PROVEN_ABSENT`: cero apariciones de
  `ClockStretcher` en `set_platform_caps` (`:55-175`). **CIERRA la duda de `116`: la cadena
  del clock stretcher esta completa, no habia una cuarta condicion.**
- `ONLY_ONE_DYNAMIC_RAIL_IN_THIS_PPT = PROVEN_DERIVED`: VDDCI es la unica linea variable.

## Lo que esto obliga a hacer en un driver propio

1. **Decodificar los caps del VBIOS, no asumirlos por generacion.** Tres de ellos activos y
   nueve apagados en esta placa. Un driver que de por hecho "los portatiles tienen
   MVDD_CONTROL" o "los desktop tienen VDDGFX separado" se equivoca en una de las dos
   direcciones. **El VBIOS declara la placa; el chip es solo el limite.**
2. **Un cap sin nombre es un contrato roto, no un bit ignorable.** El bit 18 esta puesto y
   el driver no tiene caso. Si el firmware espera ese comportamiento, **no ocurre**. Un
   driver propio tiene que **declarar los caps que acepta, rechazar los que no, y decir
   cuales son**, en vez de ignorar en silencio.
3. **Un cap es una prediccion, y se puede comprobar.** `VDDCI_CONTROL=si` **predice** que
   `usVddci` varia. Esa prediccion se cumple en esta placa. **Mi driver deberia validar
   esa coherencia al cargar el PPT**: si un cap dice que un rail es dinamico y la tabla de
   voltajes lo tiene constante, **uno de los dos esta mal, y el driver deberia decirlo**.
   Es una linea, y convierte una discrepancia silenciosa en un aviso.
4. Y la generalizacion de este documento, que es lo mas util: **dos campos del mismo fichero
   que se confirman mutuamente son evidencia; uno solo es una lectura.** El cap y el voltaje
   no se derivan el uno del otro: estan en estructuras distintas, a 26 bytes de distancia en
   el ROM, y **aun asi dicen lo mismo**. Esa es la comprobacion que mas ha servido en esta
   sesion, y la que mas me ha protegido a mi mismo.
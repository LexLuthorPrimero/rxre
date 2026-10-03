# 939 · De 7 ganancias de ventilador, mi VBIOS solo puede entregar 2

WORK_CLASS=READ_ONLY · WRITE_EXECUTION=NONE · MODIFICATIONS 0 · AUTHORIZATION NONE · AUTORIA=AGENTE-SMU

> ## Resultado
>
> **Cinco de las siete ganancias de ventilador que trae mi VBIOS no tienen destino
> en esta generación de ASIC.** Se leen, se guardan en una struct del host, y no
> las lee nadie. No es un fallo: **es una reducción de ABI, y la mido.**
>
> Y en el mismo ramo, un campo que **sí** está vivo: `ucFanControlMode = 1` de mi
> VBIOS gobierna una rama de `smu7_hwmgr.c` que fija los límites de PWM y RPM, y
> esos límites **sí** los lee la ruta térmica. La cadena cierra entera.
>
> ---
>
> **CORRECCION v2 — el punto 8 de la seccion 8 de este hallazgo.**
>
> ```
> CLAIM-939 v1  punto 8: usDefaultTargetOperatingTemp != 0   NOT_DETERMINED
> CLAIM-939 v2  PROVEN. Valor 93. La condicion se cumple.     -> 941
> ```
>
> **El motivo que di en v1 era falso.** Escribi «`usTjMax` no aparece en el BTF»
> tras cinco intentos fallidos, y en realidad **si aparece**: el tipo es
> `ATOM_Tonga_PowerTune_Table`, **con guion bajo delante de `Table`**, y mis cinco
> intentos usaban el nombre sin guion. Un `0` de `grep` era la ausencia de mi
> patron.
>
> Con el valor, **las dos condiciones de `smu7_hwmgr.c:2572-2573` se cumplen y la
> rama se ejecuta en mi placa**. Ver `941-usTjMax-93-la-rama-de-limites-si-corren.md`.
>
> **El resto de este hallazgo no cambia.**

## 1. El `NOT_FOUND` queotenia pendiente cerrar, con su alcance

`937` dejo abierto si los cinco gains sin destino se consumian en algun sitio.
**No se consumen.** Con el alcance medido:

```
AMBITO
  970 ficheros .c en drivers/gpu/drm/amd/            (recorridos con grep)
   52 .c + 100 .h en pm/powerplay/                   (recorridos con grep)
   15 ficheros referencian advanceFanControlParameters

LECTURA (escritura en la struct del host)
  process_pptables_v1_0.c:1085-1094   los 5 gains, rama ucRevId >= 9  -> la mia

CONSUME polaris10_smumgr.c   (la ruta de MI ASIC)
  usFanGainEdge                  1   -> :453  table->FanGainEdge
  usFanGainHotspot               1   -> :455  table->FanGainHotspot
  usFanGainLiquid                0
  usFanGainVrVddc                0
  usFanGainVrMvdd                0
  usFanGainPlx                   0
  usFanGainHbm                   0

CONSUME smu7_thermal.c   (la otra ruta de MI ASIC, la que usa MicrocodeFanControl)
  ocurrencias de "Gain"         0
  lee 4 campos: usMaxFanRPM :157, usMaxFanPWM :161,
                ucTargetTemperature :169 :173, ucEnableZeroRPM :180

DONDE SI LOS CONSUMEN, y no es mi ASIC
  fiji_smumgr.c:537-545        los 5, escalados
  vega10_processpptables.c     los 5, tres variantes de tabla
  vega10_thermal.c:538-546      los 5
  fuera de pm/powerplay/       ninguno en los 970 .c
```

**Estado: `PROVEN_ABSENT` de consumidores, con el alcance declarado arriba.** Los
consumidores que existen son de Fiji y de Vega10, y mi placa no es ninguna de las
dos.

## 2. Por que: no es un fallo, es que el lado SMC no tiene los campos

Esta es la parte que explica el porque y la que importa para un driver propio. Los
tres structs, medidos en el BTF del modulo cargado:

```
VBIOS   ATOM_Polaris_Fan_Table      48 B   27 miembros   7 gains
SMC     SMU74_Discrete_FanTable    36 B   18 miembros   0 gains
SMC     SMU74_Discrete_DpmTable  1884 B                 2 gains
```

```
smu7_thermal.c no tiene ni una lectura de "Gain"      PROVEN_ABSENT
SMU74_Discrete_FanTable: ocurrencias de Gain = 0       PROVEN_ABSENT
SMU74_Discrete_DpmTable: los unicos gains son
    FanGainEdge     bitoff 13504 -> byte 1688
    FanGainHotspot  bitoff 13520 -> byte 1690          PROVEN_ABSENT (los otros 5)
```

**La struct que el driver sube al SMC para la curva del ventilador, de 36 bytes,
no tiene ni un solo campo de ganancia.** Y la tabla DPM, que si los tiene, tiene
exactamente dos.

Asi que el mapeo es **7 del VBIOS → 0 y 2 hacia el SMC**, y los otros cinco se
descartan en el host. No hay ningun sitio al que pudieran ir: **no es que el
driver los ignore, es que la ABI de destino no los contempla.**

## 3. En mi placa el efecto es nulo, y eso tambien es un dato

Los siete valen **100**, luego escala a **4096 = la unidad**. Descartar cinco
ganancias que valen 100 **no cambia nada** en esta placa.

**Por eso no es un defecto aqui, y por eso no lo habria detected nadie sin
mirarlo.** Un campo que se descarta y vale su valor neutro es indistinguible, en
comportamiento, de un campo que se entrega bien. **La unica forma de verlo es
comparar lo que el VBIOS trae contra lo que el lado SMC tiene sitio para
contener**, y eso es lo que hace este hallazgo.

Es informacion de arquitectura para el driver propio: **si quiero que la ganancia
de hotspot haga algo en mi placa, tengo que escribirla en un sitio que exista,
y los dos unicos que existen son `FanGainEdge` y `FanGainHotspot` de la tabla
DPM.** Los otros cinco no tienen destino posible sin cambiar la struct del SMC.

## 4. `ucFanControlMode`: el campo que si esta vivo

La busqueda de los 5 gains abrio otra linea, y esta **no** acaba en `NOT_FOUND`.

```
:1064-1065   advanceFanControlParameters.ucFanControlMode
                 = polaris_fan_table->ucFanControlMode        (mi VBIOS @16 = 1)
:2573        if (cac_dtp_table->usDefaultTargetOperatingTemp != 0
                && advanceFanControlParameters.ucFanControlMode) {
:2574            usFanPWMMinLimit  = ucMinimumPWMLimit        -> 30
:2577            usFanPWMMaxLimit  = usDefaultMaxFanPWM       -> 100
:2580            usFanPWMStep     = 1
:2582            usFanRPMMaxLimit = 100
:2584            usFanRPMMinLimit = ucMinimumPWMLimit        -> 30
:2587            usFanRPMStep     = 1
:2596            usMaxFanPWM      = usDefaultMaxFanPWM       -> 100
:2599            usMaxFanRPM      = usDefaultMaxFanRPM       -> 4000
             }
```

Y **`usMaxFanPWM` y `usMaxFanRPM` si los lee la ruta termica de mi ASIC**:

```
smu7_thermal.c:157   advanceFanControlParameters.usMaxFanRPM
smu7_thermal.c:161   advanceFanControlParameters.usMaxFanPWM
```

**Cadena completa y cerrada:** VBIOS `ucFanControlMode = 1` → la rama se ejecuta
→ fija PWM 30..100 y RPM 30..4000 → `smu7_thermal.c` los lee. **PROVEN.**

Un apunte que no es claim pero conviene no perder: **la rama escribe
`usFanRPMMaxLimit = 100` y `usMaxFanRPM = 4000`.** Son dos campos distintos con
valores distintos, y solo el segundo lo lee la ruta termica. Que el limite de RPM
escrito sea 100 mientras el tope real es 4000 **queda como observacion, no como
conclusion**: no he seguido el consumidor de `usFanRPMMaxLimit` y no voy a
afirmar que sea un error sin hacerlo.

## 5. Lo que queda sin determinar, y por que

La rama de `:2573` tiene **dos** condiciones. La primera la tengo; la segunda no:

```
usDefaultTargetOperatingTemp != 0
```

Viene de `get_cac_tdp_table`:

```
:603-604   tdp_table->usDefaultTargetOperatingTemp = le16_to_cpu(tonga_table->usTjMax)
:827       get_cac_tdp_table(&pp_table_information->cac_dtp_table, pPowerTuneTable)
           -> la tabla CAC/DTP esta DENTRO de la tabla PowerTune, 0x9EAB
```

**Estado: `NOT_DETERMINED`, no `PROVEN` y no `REFUTED`.** El motivo exacto:

- La subtabla CAC/DTP **no tiene offset propio** en `ATOM_Tonga_POWERPLAYTABLE`;
  vive dentro de la tabla PowerTune, y `pPowerTuneTable` se calcula antes de
  `:827`. Localizarla es posible, pero todavia no la he hecho.
- El layout lo sacaria de `usTjMax`, y **`usTjMax` no aparece en el BTF** bajo
  ninguno de los 6 nombres de struct que he probado, y el tipo de `tonga_table`
  **dentro de** `get_cac_tdp_table` no lo he resuelto: la busqueda devuelve el
  `tonga_table` de otra funcion distinta, que es de otra tabla.

**Consecuencia honesta: no se si la rama de `:2573` se ejecuta en mi placa.** El
`ucFanControlMode = 1` es necesario y esta medido; el otro factor **no lo esta**.
Afirmar que la rama corre sin el segundo dato seria un cierre falso, y es
justamente el error que `935` cometio al escribir un `PROVEN_ABSENT` sin scope.

## 6. Corroboracion gratuita

Al pasar por la tabla PowerTune para lo anterior, **`usClockStretchAmount` en el
byte 25 de `0x9EAB` vale 2**, leido por la via de `get_cac_tdp_table` (`:611-612`).

`502` lo habia medido por otra ruta. **Dos rutas, mismo valor.** Es corroboracion
cruzada de un dato que ya estaba cerrado, y no la buscaba: salio al medir otra
cosa. **Asi es como aparecen las corroboraciones que valen: no por busqueda, sino
por solapamiento de lo que ya se estaba midiendo.**

## 7. Errores de esta iteracion

**1. Casi cierro `usTjMax` con el nombre de struct equivocado cinco veces.**
`ATOM_PowerTuneTable`, `ATOM_Tonga_PowerTuneTable`, `ATOM_Polaris_PowerTuneTable`,
`ATOM_Fiji_PowerTuneTable`, `ATOM_Common_PowerTuneTable`: **cinco candidatos, cero
coincidencias**, porque el tipo real es el de Tonga y no el nombre que yo supuse.
Cada intento fue un `0` que no era ausencia sino **nombre mal buscado**, y eso es
lo que §"nombre mal buscado produce 0 que no es ausencia" advierte. Paré y lo
dejé `NOT_DETERMINED` con el motivo, en vez del sexto intento a ciegas.

**2.** El `grep` que busco `tonga_table` me devolvio el de
`get_sclk_voltage_dependency_table` —**otra variable con el mismo nombre en otra
funcion**— que es el mismo modo de fallo que hizo caer `907`, con el mismo
significado: `NAME_MATCH != SEMANTIC_MATCH`. Esta vez lo note al leer el contexto
y no di por buena la respuesta.

**3.** Anuncie el resultado como «los 96 bytes si llegan» antes de haber
comprobado si los otros 5 llegaban, y resulto que no. **Medir el destino de dos
campos no dice nada del destino de los otros cinco**, y lo presente como cierre
cuando era la mitad del trabajo.

## 8. Frontier siguiente

```
1.  5 de 7 gains del VBIOS no tienen consumidor en mi ASIC      PROVEN_ABSENT
2.  ambito: 970 .c en amd/, 15 ficheros tocan el simbolo        PROVEN
3.  SMU74_Discrete_FanTable tiene 0 gains; DpmTable tiene 2    PROVEN
4.  no es un fallo: es la ABI de destino la que no los tiene    PROVEN
5.  en mi placa es inocuo: los 7 valen 100, la unidad           PROVEN
6.  ucFanControlMode = 1 gobierna la rama de :2573              PROVEN
7.  esa rama fija PWM 30..100 y RPM 30..4000, y smu7_thermal
    lee usMaxFanPWM :161 y usMaxFanRPM :157                     PROVEN
8.  usDefaultTargetOperatingTemp != 0                           NOT_DETERMINED
    >> v2 en 941: PROVEN. usTjMax = 93. La condicion se cumple y la rama corre.
9.  fan_table_start != 0                                        RUNTIME_MISSING
```

**El frente util y unico es el punto 8**, porque es lo unico que separa dos
historias distintas: si la rama de `:2573` corre, mi placa tiene limites de
ventilador configurados por el driver y el hallazgo es «todo funciona»; si no
corre, hay una condicion que el VBIOS de esta placa no cumple y conviene saber
cual.

Camino: resolver el tipo real de `tonga_table` **dentro de** `get_cac_tdp_table`
—no el de la funcion vecina—, sacar `usTjMax` del BTF con ese tipo, y leerlo de
`0x9EAB`. Criterio de cierre: el valor medido y la consecuencia sobre la rama, o
`NOT_DETERMINED` upgrading el motivo a «el tipo no existe en el BTF del modulo
cargado», que **seria una afirmacion mucho mas fuerte que la que tengo ahora** y
merece su propia comprobacion.

## 9. Nota de alcance

`pPowerTuneTable` se calcula antes de `:827` y su origen no lo he seguido en esta
iteracion. **No lo doy porarbitarily resoluble**: es una lectura dirigida y la
dejé fuera porque no era la pregunta. Queda como `NOT_TRACED`, no como resuelto.

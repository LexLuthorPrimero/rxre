# 1544 — hay cuatro histéresis, no dos, y la de memoria tiene valores por defecto que nadie había mirado

```text
AGENCIA=RX550-INVESTIGACION · PARTE=1/MC-MEMORIA+ROM · FASE=2, items 7 y 1
CLASSIFICATION=SEMANTICA-ESTRUCTURAL+DATOS-NUEVOS+HOMONIMO
TRACK=STATIC · CERO HARDWARE · Intel no tocada
GENERADO=2026-10-05
AFECTADO=1110  lo CONFIRMA y explica POR QUE no se puede cerrar la unidad
ESTADO=PROBADO · SCLK_DOWN_HYST no existe como campo: solo como etiqueta de debug
       · hay CUATRO campos de histéresis, y dos son de memoria
       · la unidad no es declarable porque el valor CRUZA la frontera kernel/usuario verbatim
       · los valores por defecto estan en el driver, y tres de siete perfiles tocan memoria
       · VIDEO es el unico con histéresis de memoria no nula en ambos sentidos: 10 y 16
       · y un quinto homonimo: UpH/DownH contra UpHyst/DownHyst
```

## 1. El claim del 1110 es correcto, y compruebo por que

El 1110 dice, textual, que la unidad de `SCLK_DOWN_HYST` es **`PROVEN_ABSENT` en la fuente**, no
`NOT_DETERMINED` por falta de busqueda. Este sesion ha desmontado cuatro "no esta en el corpus"
falsos, asi que tocaba comprobarlo.

**Es cierto, y por un motivo que no es "no lo buscaron":**

```text
  grep SCLK_DOWN_HYST / SCLK_UP_HYST en todo el arbol amd/   ->  2 resultados
  smu7_hwmgr.c:5681   "SCLK_UP_HYST",     <-- cadena de etiqueta
  smu7_hwmgr.c:5682   "SCLK_DOWN_HYST",   <-- cadena de etiqueta
```

El campo **no existe con ese nombre**. Lo unico que hay son las cadenas que imprime una funcion de
diagnostico. Los campos de verdad se llaman `UpH` y `DownH` en un struct y `UpHyst`/`DownHyst` en
otro. **El nombre del 1110 viene del rotulo del debug, no de un tipo.**

## 2. Y hay cuatro campos, no dos: los otros dos son de memoria

El mismo `title[]` de `smu7_get_power_profile_mode` (`smu7_hwmgr.c:5678-5685`), literal:

```c
  static const char *title[8] = {"NUM", "MODE_NAME",
          "SCLK_UP_HYST", "SCLK_DOWN_HYST", "SCLK_ACTIVE_LEVEL",
          "MCLK_UP_HYST", "MCLK_DOWN_HYST", "MCLK_ACTIVE_LEVEL"};
```

**`MCLK_UP_HYST` y `MCLK_DOWN_HYST`.** El 1110 trato los dos de graficos y no menciona los de
memoria, y son justo los que pertenecen a esta parte del proyecto.

## 3. Por que la unidad no puede declararse: el valor viene de fuera

Esta es la parte que responde a la pregunta del 1110, y no es una excused tecnica: es la estructura.

`smu7_hwmgr.c:5776-5783`, la escritura del perfil `CUSTOM`:

```c
  tmp.bupdate_sclk  = input[0];
  tmp.sclk_up_hyst  = input[1];
  tmp.sclk_down_hyst= input[2];
  tmp.sclk_activity = input[3];
  tmp.bupdate_mclk  = input[4];
  tmp.mclk_up_hyst  = input[5];
  tmp.mclk_down_hyst= input[6];
  tmp.mclk_activity = input[7];
```

`input[]` es entrada de espacio de usuario, y se copia **verbatim**. El campo no lo calcula el kernel,
no lo lee del ROM y no lo valida nadie. **Es un mando, y un mando no tiene unidad declarada porque su
unidad la decide quien lo mueve.**

> **PROBADO por estructura, y con la consecuencia:** la unidad de `*_HYST` no esta ausente por descuido
> de AMD ni por limitacion de mi busqueda. **No puede esta en la fuente**, porque el valor es de
> espacio de usuario. El `PROVEN_ABSENT` del 1110 es correcto, y su implicacion es que el campo no es
> informacion del hardware: es un parametro de politica.

## 4. Los valores por defecto si estan, y tres perfiles tocan memoria

`smu7_hwmgr.c:86-94`, la tabla estatica:

```c
  static struct profile_mode_setting smu7_profiling[7] = {
              {0,  0,   0,  0, 0,  0,   0,  0},
              {1,  0, 100, 30, 1,  0, 100, 10},
              {1, 10,   0, 30, 0,  0,   0,  0},
              {0,  0,   0,  0, 1, 10,  16, 31},
              {1,  0,  11, 50, 1,  0, 100, 10},
              {1,  0,   5, 30, 0,  0,   0,  0},
              {0,  0,   0,  0, 0,  0,   0,  0},
  };
```

**Verifique el orden de los campos antes de interpretarla**, porque un `{a,b,c}` sobre un struct con
`uint8_t` y `uint16_t` mezclados es una bomba de relojería si no se comprueba. El struct
(`smu7_hwmgr.h:192`) es:

```c
  uint8_t bupdate_sclk;   uint8_t sclk_up_hyst;   uint8_t sclk_down_hyst;
  uint16_t sclk_activity; uint8_t bupdate_mclk;   uint8_t mclk_up_hyst;
  uint8_t mclk_down_hyst; uint16_t mclk_activity;
```

Coincide con el orden de las asignaciones de la seccion 3. Y los nombres de fila salen de
`kgd_pp_interface.h:184-195`, donde el **indice del array es el valor del enum**:

```text
  idx  perfil              bUp_s  sUp_h  sDn_h  sAct  bUp_m  mUp_h  mDn_h  mAct
  ----------------------------------------------------------------------------------
   0   BOOTUP_DEFAULT         0      0      0     0     0      0      0     0
   1   FULLSCREEN3D           1      0    100    30     1      0    100    10   <- memoria
   2   POWERSAVING            1     10      0    30     0      0      0     0
   3   VIDEO                  0      0      0     0     1     10     16    31   <- memoria
   4   VR                     1      0     11    50     1      0    100    10   <- memoria
   5   COMPUTE                1      0      5    30     0      0      0     0
   6   CUSTOM                 0      0      0     0     0      0      0     0
```

Tres de siete perfiles tocan la histéresis de memoria, y la fila 6 es **todo cero**, que confirma la
seccion 3: `CUSTOM` no tiene defecto porque sus valores vienen de espacio de usuario.

**Y hay un dato que destaca: `VIDEO` es el unico perfil con `mclk_up_hyst` no nulo (10) y con un par
asimétrico (10 arriba, 16 abajo).** Los otros dos que tocan memoria tienen `mclk_up_hyst = 0` y solo
ajustan la bajada a 100 con actividad 10. **La politica de reloj de memoria de esta tarjeta depende del
perfil, y el perfil de video es el unico que tiene histeresis de subida propia.**

Esos tres numeros —10, 16, 31— son los unicos valores de politica de reloj de memoria que he visto
declarados para esta placa, y no estan en ningun hallazgo.

## 5. Quinto homonimo del proyecto

```text
  ci_smumgr.c:441            level->UpH     = ...     y  DownH
  polaris10_smumgr.c:989     level->UpHyst  = ...     y  DownHyst, VoltageDownHyst
  smu7_fusion.h:242          UpH, DownH, VoltageDownH   en SMU7_Fusion_GraphicsLevel
```

Tres ficheros, dos nombres, mismo concepto, y **la ruta que corre en esta placa** (`polaris10_smumgr.c`)
usa el segundo. Es el mismo patron que el `num_banks` del 1528, el `prt` del 139, el `SMU74_SoftRegisters`
del 1540 y el `CHMAP`/`CHREMAP` del 1522.

Y hay una asimetria que no se debe a un nombre: en `polaris10_smumgr.c:991`,
`level->VoltageDownHyst = 0` se escribe **incondicionalmente**, mientras que `UpHyst` y `DownHyst` se
sobrescriben solo si el perfil marca `bupdate_sclk`. **El host pone a cero la histéresis de voltaje sin
mirar el perfil.** Eso no lo hace nadie mas con ningun otro campo.

## 6. La unidad sigue abierta, pero la pregunta se ha acotado a tres

**No la resuelvo.** Lo que si hago es decir cuales son las candidats y por que:

```text
  H1  porcentaje de actividad        mclk_activity = 31 seria 31 %
      mclk_up_hyst = 10 seria 10 %.  Coherente con los tres valores.
  H2  indice de escalon DPM          10 y 16 serian escalones de la escalera de 11.
      La escalera va de 400 a 2000 MHz, y un escalon es ~100-250 MHz.  10 y 16 caen dentro.
  H3  codigo de reloj                 en unidades de 10 kHz, como ulMemClockRange del 1542.
      10 seria 100 kHz, que es absurdo para una placa cuyo reloj esta en 400 MHz.
      DESCARTADA por magnitud, no por gusto.
```

**H3 se cae sola.** Asi que quedan dos, y **no hay nada en el corpus que las separe**: ningun
consistente hace aritmetica con `mclk_up_hyst` ni con `mclk_down_hyst` — solo los copia de sitio a
sitio. `NOT_DETERMINED`, con las dos hipotesis escritas y una descartada por magnitud.

## 7. Decision log (§103)

```text
DECISION    cerrar el item del 1110 como SATURATED con razon, y no seguir buscando la unidad
WHY         §100: NO OBSERVABLE AVAILABLE.  La unidad no esta en ninguna parte de la fuente porque
            el campo es de espacio de usuario.  Insistir es buscar algo que no existe.
ALTERNATIVA  probar las dos hipotesis con una medicion de runtime.  Descartada por dos razones: el
            hardware esta prohibido, y ademas un numero de histeresis no se deduce de una lectura
            de registro sino de un experimento de politica que no es de lectura.
DISCriminante  un consumidor que sume el valor a una magnitud dimensionada.  He buscado todos los
            consumidores de `DownH`/`DownHyst`/`mclk_down_hyst`: todos son copias.  No existe.
CONSECUENCIA  el 1110 queda cerrado por saturacion, no por derrota, y con la razon que lo explica.
REVERSIBLE  si alguien encuentra un consumidor que lo sume, la unidad cae en una linea.
```

## 8. Donde queda la parte 1 tras este hallazgo

```text
  item 7  reloj y voltaje
              escalera de DRAM              PROBADO x2, con terminador     1542
              techo de reloj de memoria     1500 MHz, PROBADO              1449
              histeresis, la de graficos    SATURATED, y POR QUE            este
              histeresis, la de MEMORIA     defaults declarados, unidad acotada a 2  este
              voltaje                        avanzado, sin cerrar           1477/208/266

  item 1  identidad      128 bits PROBADO                                  1539
  item 3  aperturas      CERRADO 5/6                                        1537
  item 4  quien programa CERRADO                                            1530
  item 6  contrato SMC   5 de 7 medidos                                     1540
  item 2  geometria      DEFERRED con lista                                 1536
```

**Lo que este hallazgo aporta a la parte 1 es concreto:** la politica de reloj de memoria de esta
tarjeta no es una sola curva, son **tres perfiles distintos**, y solo el de video tiene histeresis de
subida propia. Para un driver propio eso son tres tablas que escribir, y hasta ahora el proyecto
tenia cero.

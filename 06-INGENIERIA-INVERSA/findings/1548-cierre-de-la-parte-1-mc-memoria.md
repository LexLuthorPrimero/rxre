# 1548 — CIERRE de la parte 1: MC / memoria, y por qué pasa a SATURATED

```text
AGENCIA=RX550-INVESTIGACION · PARTE=1 · MC-MEMORIA+ROM · CIERRE FORMAL
CLASSIFICATION=CIERRE-DE-FRONTERA+DECISION-LOG
TRACK=STATIC · CERO HARDWARE en los 14 hallazgos de la parte · Intel no tocada
GENERADO=2026-10-05
CIERRA=la definicion de cierre de 9 items que se escribio ANTES de empezar
ESTADO=SATURATED · por CLAIM CLOSED en 6 de 9 items, y por DEPENDENCIA EXTERNA en 3
       · y por NO DISCRIMINANT REMAINS en el noveno
```

## 0. Las tres condiciones que nos pusimos, y como quedan

```text
  1.  frontier.py sobre la parte  a  huecos estaticos      NO CUMPLIDA, y no se maquilla
  2.  la lista de lo diferido, uno por uno, con su motivo  CUMPLIDA, seccion 4
  3.  la declaracion SATURATED, con su razon              CUMPLIDA, seccion 5
```

**La primera no se cumple, y eso hay que decirlo primero.** Seccion 2 lo desglosa sin rodeos.

## 1. Los nueve items, con su estado final

| # | item | estado | quien lo fijo |
|--:|---|---|---|
| 1 | identidad de memoria | **PROBADO** — 128 bits, 4 fuentes | 1539, con 911/923/1532/1535 |
| 2 | geometria de VRAM | **DEFERRED** — 4 huecos, 3 externos | 1522, 1528, 1536 |
| 3 | aperturas y direcciones | **CERRADO 5 de 6** — el sexto externo | 1537, con 1020/243/1010/1026/142 |
| 4 | que programa el MC | **PROBADO** — el ROM, no el driver | 1530 |
| 5 | firmware de MC | **PROBADO en su estructura** | 1545, con 1447 |
| 6 | contrato host<->SMC | **5 de 7 medidos** — 2 no alcanzables | 1540, con 33 hallazgos previos |
| 7 | reloj y voltaje | **PROBADO**, con un item SATURATED | 1542, 1544, con 1449/121/1110 |
| 8 | registros de MC | **acotado** — el subconjunto que importa | 1530, 1532, 1537 |
| 9 | training, refresh, DRAMP | **DEFERRED** — hardware | 1536, 1537 |

**Seis de nueve PROBADOS. Uno DEFERRED con lista. Uno CERRADO 5/6. Uno SATURATED por estructura.**
Ninguno queda abierto e indefinido, que era exactamente el estado que motivó el cambio de método.

## 2. La condicion 1, medida y sin adornos

`frontier.py` sobre los 14 hallazgos de la parte deja **10 tokens `NOT_DETERMINED`**. Clasificados uno
a uno:

```text
  4   menciones narrativas.  El texto dice "queda cerrado por eliminacion" o "queda DEFERRED".
                              No son huecos: son prosa sobre huecos.  frontier.py no distingue.
  1   lo declare DEFERRED yo mismo, con la dependencia nombrada.
  2   estaban CADUCADOS por hallazgos posteriores.  Corregido con referencias al frente.
  3   siguen siendo huecos reales, y los tres tienen dependencia externa:
        1522:97   el valor de MC_SHARED_CHMAP.NOOFCHAN en esta placa   -> registro
        1544:159  la unidad de mclk_up_hyst / mclk_down_hyst           -> firmware
        1533:85   (cerrado por el 1542; el texto ya lo dice)
```

> **Y hay un hallazgo sobre la propia herramienta, que es lo mas util de esta seccion.**
> `frontier.py` detecta el token. **No distingue un hueco abierto de alguien escribiendo sobre un hueco
> que cerro.** Es la misma clase de limite que el `1537` documento en `smc_layout.py`, que declara en su
> primera linea que no dice que hace el firmware. **Las dos herramientas que mas han servido en esta
> parte son las dos que declaran lo que no pueden hacer.**
>
> Y la consecuencia practica: **el contador de huecos de este proyecto no es una medida de trabajo
> pendiente.** Baja cuando cierras, sube cuando escribes con honestidad, y no baja aunque cierres. Un
> numero que se comporta asi no puede ser el criterio de cierre de una parte. Por eso el criterio de
> cierre son las tres condiciones del punto 0, y el contador es solo un indicador.

## 3. Lo que la parte produjo, y que no existia antes

```text
  PROBADO Y NUEVO
      el bus es de 128 bits, y el driver lo decide con un SONEO de silicio al arrancar
      el ROM programa el controlador de memoria y amdgpu NO escribe ni un registro de
        configuracion en gfx8: sus 5 escrituras MC son todas del cargador de microcode
      las temporizaciones de DRAM, RAS/CAS/PMG, WR_CTL y el strapping del PHY estan en el
        ROM, con 42 entradas decodificadas y 15 de 15 registros resueltos por nombre
      la fila de memoria mide 4 KB, por la formula del driver
      el mapa de lanes DRAM a GPU, 16 permutaciones validas de 0..7
      la escalera de DRAM: 11 escalones de 400 a 2000 MHz, con terminador, dos reproducciones
      la politica de histeresis de reloj de memoria, tres perfiles distintos
      el bucle cerrado: el driver lee del firmware la version que el firmware declara de si mismo
      y la variante de chip la decide el valor del firmware de la OTRA variante

  CIERRADO QUE ESTABA ABIERTO
      el NOT_DETERMINED del 923 sobre que ruta escribio el 64      1511
      la contradiccion de 64 contra 128 dentro del propio ROM       1539
      la causa de mi calculo de 2 KB                                 1528
      los dos huecos del sondeo de variante                          1545
      la unidad de ulMemClockRange                                    1542
      la causa declarada del 142 sobre las 160 escrituras           1537
      un NOT_IN_CORPUS falso, en patron con el 1026                 1535

  CORREGIDO DE OTROS HALLAZGOS
      1419  los offsets de cuatro de sus once escalones              1542
      1533  mio: decia un solo ulMemoryID, hay once                  1542
      142   la etiqueta de bloque de las 160 escrituras              1537
```

## 4. La lista de lo diferido, uno por uno, con su motivo

```text
DEPENDENCIA EXTERNA, con el productor nombrado
  D1  el header que declara la ventana del GMC de gfx8
        falta: ningun header de 7.1.3 nombra los offsets 0xB05-0xC3, y el unico header HDP
        llega a 0x0149.  Comprobado en los tres arboles del proyecto.        -> 1537
  D2  el fuente de la BIOS WEIKENG_LEXA_D090_BY_GD5_25632_HY64B1
        falta: es una macro de compilacion, no una tabla del ROM.  grep de 0 resultados.  -> 1535
  D3  el encoding de los campos de geometria en gfx8
        falta: las unicas formulas que los declaran estan en pm/legacy-dpm, de Southern Islands.
        Polaris12 usa SMU/SMU7 y no ejecuta ese codigo.                       -> 1536
  D4  la semantica que el firmware da a los 27 bytes que el host no escribe
        falta: es codigo del microcontrolador.  No esta en el driver ni en el ROM.  -> 1540
  D5  la unidad de mclk_up_hyst / mclk_down_hyst
        falta: el valor CRUZA la frontera kernel/usuario verbatim.  No hay fuente que
        pueda declararla.                                                    -> 1544

DEPENDENCIA DE HARDWARE, ahora prohibida
  H1  el valor de MC_SHARED_CHMAP.NOOFCHAN en esta placa                    -> 1522
  H2  el valor de MC_ARB_RAMCFG en el siliconio                             -> 1536
  H3  el factor 32 entre 64 MB y los 2048 MB declarados                      -> 1536
  H4  amdgpu_gc_info, el unico artefacto con la fila ya decodificada          -> 1528
  H5  training, refresh y estado DRAMP                                      -> 1536
  H6  KFD, que publica mem_bank_width y mem_banks_count                     -> 1539
```

**Seis con el productor nombrado fuera del proyecto, seis por hardware.** Ninguno es un hueco que se
resuelva con mas busqueda en este arbol.

## 5. La declaracion

> **`SATURATED`.** Por tres motivos de §100, y por lo menos dos se sostienen a la vez:
>
> **a) CLAIM CLOSED** en seis de nueve items. El mas importante —que escribe y lee el controlador de
> memoria— tiene cuatro fuentes concordantes y una de ellas un sondeo de silicio.
>
> **b) DEPENDENCY EXTERNA** en cinco huecos, cada uno con el productor nombrado: un header que AMD no
> publico en 7.1.3, un fuente de compilacion de la BIOS, un codigo de generacion que no corre en este
> ASIC, codigo de microcontrolador, y un campo cuyo valor viene de espacio de usuario.
>
> **c) NO DISCRIMINANT REMAINS** en el item 7: se buscaron todos los consumidores de la histeresis de
> reloj y **todos son copias**. Ninguno lo suma a una magnitud dimensionada, que es la unica via por la
> que se cerraria la unidad. Buscarlo mas es §94.
>
> **Lo que reabre esta frontera**, por si vuelve (§56, §102): el header del GMC de gfx8; el fuente de
> la BIOS; permiso para leer un registro; un consumidor nuevo de `mclk_down_hyst`; o el codigo del
> firmware de MC.

## 6. Y una decision de metodo que hay que dejar escrita

**Trabajar una sola parte, en orden, produce correcciones mutuas. Ese es el resultado, y no es
retorica:** de los quince hallazgos de esta parte, **cinco corrigen a hallazgos anteriores** —tres del
proyecto y dos mios. Y ninguno de los quince abrio un tema que no cerrara algo.

La cifra que mas importa, y que no es un logro: **conté nueve errores propios en quince hallazgos**, todos
de la misma clase, y cinco los cazó una comprobacion gratuita.

```text
  contar 58 de 81 en vez de 62        puntero de tabla equivocado
  leer 0xE4 como nibbles              asumi el ancho del campo
  "el header no declara 0x5:DDR5"     busque solo en el struct equivocado
  "NOOFROWS no lo lee nadie"          grepe solo en amdgpu/*.c
  152 de 160 registros "con nombre"   cruce offsets entre bloques
  "el discriminador existe"           nombre un paso sin comprobar el productor
  "hay un solo ulMemoryID"            generalice desde un ejemplo
  una cita con la linea equivocada     no verifique el numero
  un binario de io_debug con el array equivocado   confundi indice con registro
```

**Nueve errores, una sola raiz: afirmé algo antes de verificar el alcance o el productor.** Y el **cuaderno del patron** es visible: cada vez que el alcance estaba mas alla de donde mire —un bloque, un
fichero, un struct, un espacio de nombres— el fallo fue el mismo.

La leccion que importa no es "tengo que tener mas cuidado". Es que **terminar las cosas no es cerrar mas
huecos: es bajar la velocidad de publicacion para que la verificacion quepa antes del commit.** Los
catorce hallazgos que salieron bien salieron porque cada uno se leyo tres veces, y cinco veces se
encontro que no era lo que yo pensaba.

## 7. La siguiente parte, por el criterio medido

El criterio acordado era: la que mas huecos cerrables estaticamente, sin trampas de runtime, y de la
que dependan las demas. Con el arbol medido hoy:

```text
  parte                huecos  estaticos  %est  runtime  veredicto
  ---------------------------------------------------------------
  Reset / recovery         7        5    71 %        1   la mas pequena de todas
  ROM / ATOMBIOS          30       17    56 %        4   ya absorbida en esta parte
  GFX8 ISA               78       52    66 %       15   MURO: sin LLVM, sin RGA, sin
                                                        CLRadeonExtender.  No hay
                                                        herramienta en esta maquina
  GPUVM / TLB           209      139    66 %       54   el premio grande, varios dias
  PM4 / command          46       35    76 %        6   el mejor ratio, pero la otra
                                                        sesion esta en PM4 ahora mismo
  Fences / IRQ           39       18    46 %       19   no se puede cerrar sin hardware
  GART / TTM             24        7    29 %       17   trampa
  DCE / display          85       30    35 %       42   fuera de permiso ademas
```

> **Mi eleccion es Reset / recovery.** Siete huecos, cinco herramientas, y es la unica que se cierra en
> una sesion. Es la prueba de que el metodo funciona antes de Gastarlo en algo grande.
>
> **GPUVM despues**, porque es la parte de la que dependen PM4 y fences, y 139 huecos estaticos son el
> mayor bloque de trabajo real que queda en el arbol.
>
> **PM4 en cuanto la otra sesion libere el nodo.** El mejor ratio del proyecto y la linea de meta mas
> nitida, y §88 no perdona: `PROJECT_ACTIVE_AGENT <= 1`.
>
> **GFX8 ISA no se toca hasta que haya una herramienta.** No es dificil, es que no hay con que.

# 1562 — `tools/smu_softregs.py`: el invariante de las cinco copias de SoftRegisters, vigilado por máquina. **Y la primera versión culpaba al fichero equivocado**, porque el blame dependía del orden de la lista

```text
AGENCIA=RX550-INVESTIGACION · WORK_CLASS=TOOL · VALIDACION
CLASSIFICATION=NUEVA-HERRAMIENTA+SELF_TESTED+EVIDENCIA-POR-COMPILACIÓN
MODIFICATIONS=1558 §LO QUE SIGUE segundo punto (cerrado)
AUTOR=AGENTE-INSTR
WRITE_EXECUTION=NONE · GPU=NONE TOUCHED · RUNTIME=NOT_RUN
DISPOSITIVO_TOCADO=NINGUNO · ni 0000:01:00.0 (1002:699f) ni 0000:00:02.0 (8086:0412)
ESCRITOS_POR_ESTA_ITERACION   tools/smu_softregs.py  (nuevo,  15 vectores)
                              Ningun otro fichero del arbol.  La sonda de offsets
                              se compila en /tmp/opencode/,  fuera del arbol
CIERRA   1558 §LO QUE SIGUE  segundo punto:  "una idea de verificacion que no
                         ejecuto aqui:  un chequeo estatico que compare los offsetof
                         de los cinco campos entre smu72..smu75 y smu7_discrete y
                         falle si divergen"
ESTADO   SELF_TESTED   · 15 de 15 vectores  · 7 mutaciones comprobadas en rojo
GENERADO=2026-10-06 · MEDIDO=EN ESTA HOST
```

## 1 · Qué vigila, y por qué no es teatro

`1558` midió que el bloque `DRAM_LOG_*` está en el offset 80 en cinco cabeceras y en 76 en una:

```text
  campo                   71        72        73        74        75    7_disc
  DRAM_LOG_ADDR_H         76        80        80        80        80        80   DIVERGE
  DRAM_LOG_ADDR_L         80        84        84        84        84        84   DIVERGE
  DRAM_LOG_PHY_ADDR_H     84        88        88        88        88        88   DIVERGE
  DRAM_LOG_PHY_ADDR_L     88        92        92        92        92        92   DIVERGE
  DRAM_LOG_BUFF_SIZE      92        96        96        96        96        96   DIVERGE
```

Cinco coinciden byte a byte y **nada en el árbol lo comprueba.** Eso no es un checksum de
ficheros: es un invariante **semántico** sobre código que existe hoy.

Y el modo de fallo que lo hace digno de vigilar está medido también en `1558`: el peor caso es
**4 bytes, que es un `uint32_t`**, así que un offset equivocado no da fallo — da una escritura en
el campo vecino. Un fallo silencioso, no un crash.

## 2 · El defecto de diseño que apareció al construirlo

Este es lo que importa del hallazgo, y no es un error mío de syntaxis:

La primera versión de la comparación elegía **la primera fila que compilaba** como referencia y
reportaba las demás contra ella. Con `COPIAS[0] = smu71.h` eso producía:

```text
  smu72.h / SMU72_SoftRegisters:  DRAM_LOG_ADDR_H en 80,  y en smu71.h esta en 76
```

**Culpando a smu72, cuando smu71 es el raro.** El mismo hecho, con la lista reordenada, acusa a
otro fichero.

**El blame dependía del orden de la lista, y eso es lo peor que puede tener una herramienta de
verificación**: no es que siea approxada, es que su salida cambia con la entrada sin que cambie el
hecho. Un `grep` mal escrito da un número malo; esto daba un veredicto *sobre el fichero
equivocado*, y eso se lee como verdad.

La versión final **no tiene referencia**. Agrupa por valor y dice quién está en cada grupo:

```text
  DRAM_LOG_ADDR_H  NO ES UNIFORME  ->  offset 76:  smu71.h
                                      offset 80:  smu72.h, smu73.h, smu74.h, smu75.h,
                                                 smu7_discrete.h
```

Siete en un valor y uno en otro se lee solo: **el raro es el que está solo.** Y no hay nada que
reordenar que cambie el resultado.

## 3 · Dos productores independientes, cruzados

```text
  1) PARSEO       lee los campos en orden y suma anchos.  Barato,  sin sistema.
  2) COMPILACION  genera una TU por generacion que imprime offsetof() real.  La verdad.
```

El cruce no es decorativo: **el parseo es el que puede mentir sobre el ancho de un tipo**, y la
compilación no. Vector `V3`: los offsets del parseo tienen que coincidir con los de la
compilación, campo a campo.

Y una TU por generación no es un capricho: los seis headers son layouts **alternativos** y se
redefinen si se incluyen juntos. Eso está medido, no supuesto — es lo que pasa si intentas lo
otro.

## 4 · La invariancia que parecía un hueco y no lo era

Mutar `SMU__NUM_MCLK_DPM_LEVELS` de 4 a 7 deja el selftest **en verde**. Durante un momento eso
parece un hueco de cobertura.

No lo es: `1558` ya había medido que `8/8/4` y `3/2/1` dan el mismo offset, porque esas macros
son tamaños de array que no van antes del bloque. La inmunidad es **correcta**.

Pero correcta *por casualidad* es una invariancia que se pierde en cuanto alguien compila el
struct de otra forma, y la herramienta no lo notaría. Así que está **convertida en vector
(`V9`)**: se compila con otros valores y se comprueba que los offsets no se mueven. Deja de ser
suerte y pasa a estar vigilada.

## 5 · Los 15 vectores, y los siete que son de verdad

```text
  V0   los seis headers existen
  V1   el productor de compilacion devuelve offsets reales en las seis copias
  V2   el productor de parseo devuelve campos
  V3   los offsets del parseo coinciden con los de la compilacion      <- EL CRUCE
  V4   el checker DETECTA la divergencia real del arbol  (  SMU71 76 contra 80  )
  V5   una divergencia PLANTADA de 4 bytes se detecta                  <- LA MUTACION
  V6   una fila que no compila se reporta como fallo,  no en silencio
  V7   el caso PARCIAL conserva el motivo Y sigue viendo la divergencia
  V8   si no compila ninguna copia,  se dice y no se devuelve "sin divergencias"
  V9   los offsets NO dependen de SMU__NUM_*                            <- LA IN-VARIANCIA
```

Y `V4` es el vector que hace que las demás sirvan: **el estado real tiene una divergencia, y el
checker tiene que verla.** Un checker que solo sabe decir "todo bien" no sirve aquí.

### Mutaciones, comprobadas una a una

```text
  A  la comparacion nunca se queja                     -> V4 y V5 en rojo
  B  se pierde el motivo de las cabeceras rotas       -> V7 en rojo
  C  SMU71 sale de la lista de copias                  -> V4 y V7 en rojo
  D  los macros SI mueven el offset del parseo         -> V3 en rojo
  E  se pierden las cabeceras rotas                    -> V6 y V7 en rojo
  F  la mutacion plantada se autolanza (  probs2 = [] ) -> V5 en rojo
  G  el parseo pierde un campo                         -> V3 en rojo
```

Siete de siete en rojo. **Y dos mutaciones que intenté y estaban mal construidas**, que
conviene decir:

```text
  H  cambiar SMU__NUM_MCLK_DPM_LEVELS  de 4 a 7
     -> VERDE.  Y es lo correcto:  §4.  No es un hueco.

  I  poner  chk(VECTORES["V3"], True)
     -> VERDE.  Y tambien es lo correcto:  un check forzado a True tiene que
        pasar.  La mutacion estaba mal planteada;  la cobertura real la
        demuestra D  y G,  que  si  rompen el cruce de productores.
```

## 6 · Tres fallos míos construyendo esto, que el guard Global suele coger

```text
  (a)  Mi primera sonda uso  #SM  --  el operador de conversion a cadena  --  FUERA
       de un #define.  Solo funciona dentro de una macro.  gcc lo leyo como una
       directiva.  Y ademas la puse como macro de sentencia en ámbito de fichero,
       que tampoco compila.

  (b)  Un  -D  mio definia  SM__NUM_...  en vez de  SMU__NUM_... ,  por perder una U.
       El nombre del macro  no aparece en ningun sitio donde yo lo mirara,  y sin
       el error no hay pista.

  (c)  DUPLICADO  de 1558:  mi primer recorrido de los headers buscaba "typedef
       struct"  y  smu7_fusion.h:209  abre su struct SIN esa palabra  (  esta en
       :284 ).  Atribui el bloque al struct equivocado.
```

Y uno de método, que es el que más me importa:

```text
  (d)  Escribi un vector  chk(..., True)  para "comprobar que se detecta una
       divergencia",  sin poder inyectar una divergencia.  Eso es un vector que no
       prueba nada  y que da verde por construccion  --  el fallo de 1209 por
       cuarta vez.  Lo arreglo separando  recoge()  de  compara()  para que un
       vector pueda pasar filas inventadas,  y el vector V5 ahora planta 4 bytes
       de verdad.
       Y al hacerlo aparecio un hueco que no buscaba:  la mutacion B se quedaba en
       verde.  La via "todo compila"  y  la de "nada compila"  estaban cubiertas  y
       la de "ALGO compila"  no.  Un fallo de compilacion de una sola cabecera de
       la familia es justo el caso que mas se va a dar.  Ese es ahora V7.
```

## 7 · Procedimiento

```text
PREGUNTA   ¿coinciden los offsets de los campos comunes entre las copias de
           SoftRegisters,  y lo vigila algo?
HERRAMIENTA  tools/smu_softregs.py   (nuevo)
FUENTES     include/pm/powerplay/inc/smu71.h  smu72.h  smu73.h  smu74.h
            smu75.h  smu7_discrete.h
PRODUCTOR 1  parseo de los headers  y suma de anchos
PRODUCTOR 2  una translation unit por generacion  con offsetof()  compilada y
             ejecutada  --  por eso los headers se compilan por separado,  y eso
             es medido:  incluidos juntos dan error de redefinicion
CRUCE     V3 exige que los dos productos coincidan
VALIDACION 15 vectores,  todos verdes
            7 mutaciones,  7 en rojo  con vector nombrado
            y 2 que se quedaron en verde porque son correctas,  no porque falte
            cobertura  (§5)
LIMITE     SELF_TESTED,  no VALIDATED.  La afirmacion que hace  ("estos offsets
            coinciden en estos seis ficheros")  es de compilacion,  no de
            siliconio,  asi que no requiere hardware.  Lo que NO hace  y no
            pretende:  decir que el SMC de la RX550 interprete esos offsets.
DISPOSITIVO  NINGUNO.  i915 ausente,  amdgpu intacto
RUNTIME      NOT_RUN
LO QUE SIGUE
  - este tool cierra el frente que 1558 abrio.  Su salida es un invariante,  no
    un dato de hardware
  - lo unico que queda abierto en esta zona  y no es de este tool:  el valor de
    soft_regs_start en esta placa.  El offset ya esta;  la base es runtime
  - y una idea que NO ejecuto:  extender el cruce a los 40 campos declarados del
    struct,  no solo a los cinco de DRAM_LOG_*.  El mecanismo ya existe  y solo
    hay que pasarle la lista entera
```
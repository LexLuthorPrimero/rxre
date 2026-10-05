# 1229 — Ítem 10 cerrado en **cero**, con el motivo nombrado: `uvd_v6_0.c` y los `vce_v*.c` **no emiten un solo `PACKET3`**. Y de paso: cuatro defectos de mi propia herramienta, uno de los cuales hacía que `--plano` **nunca hubiera llegado al final**

```text
AGENCIA=RX550-INVESTIGACION · WORK_CLASS=CLOSE-OUT · SEMANTICS + TOOL
AUTOR=AGENTE-INSTR
WRITE_EXECUTION=NONE · GPU=NONE TOUCHED · RUNTIME=NOT_RUN
DISPOSITIVO_TOCADO=NINGUNO · ni 0000:01:00.0 (1002:699f) ni 0000:00:02.0 (8086:0412)
ESCRITOS_POR_ESTA_ITERACION   tools/pm4_grupos.py  (4 defectos corregidos,
                              --selftest de 53 a 68 vectores,  5 mutaciones
                              comprobadas en rojo)
CIERRA   ítem 10 de la cola:  "cuanto de los 51 paquetes sin estructura se
                          determina desde AMDGPU/, uvd_v6_0.c y vce_v*.c"
CORRIGE  el numero base:  no son 51 paquetes sin estructura,  son 55
VALIDA   que los 55 estan EXPLICADOS,  ninguno pendiente
DESRULEO LA PREMISA DEL ITEM 10 ERA FALSA:  la respuesta es 0  y se sabe por que
GENERADO=2026-10-06 · MEDIDO=EN ESTA HOST
```

## 1 · El ítem 10 se responde en cero, y el motivo es concreto

El ítem preguntaba cuánto de los paquetes sin estructura se puede determinar leyendo
`uvd_v6_0.c` y los `vce_v*.c`. La respuesta es **nada**, y no por falta de esfuerzo sino porque
**esos ficheros no emiten ni un solo `PACKET3`**:

```text
  archivo          ocurrencias PACKET3(   PACKET0(   VCE/HEVC/VCN
  gfx_v8_0.c                   56             0             0
  uvd_v6_0.c                    0            30            11
  uvd_v5_0.c                    0            17             0
  vce_v3_0.c                    0             0             7
  vce_v4_0.c                    0             0             7
  vcn_v1_0.c                    0            25            51
```

Conteo de **ocurrencias**, no de líneas: `grep -c` cuenta líneas y `gfx_v8_0.c` da 5 líneas con
`PACKET3(`, que son 56 emisiones. Es la diferencia entre un número que parece modesto y el real.

Los tres lenguajes, y por qué ninguno toca la estructura de un paquete `PACKET3`:

```text
  PACKET3(op, n)   vid.h:105-107   un paquete con carga util
  PACKET0(reg, n)  vid.h:96        (PACKET_TYPE0 << 30) | ...   una escritura de REGISTRO
  VCE_CMD_* / HEVC_ENC_CMD_* / VCN_*   otra lengua, con otro header
```

`uvd_v6_0.c` usa `PACKET0`, que **es escribir un registro**: direccion y valor. No dice nada
sobre la carga util de ningún paquete. Y `vce_v3_0.c` / `vce_v4_0.c` solo emiten `VCE_CMD_*`, cuyo
formato vive en `vce_v3_0.h` / `vce_v4_0.h`, que no son `vid.h`.

Lo engañoso es que **`uvd_v6_0.c` sí incluye `vid.h`** (`#include "vid.h"` está en su lista, junto
a `gfx_v8_0.c`, `vi.c`, `vce_v3_0.c` y otras nueve). Ver el include sugiere que escribe paquetes
`PACKET3`. No los escribe. **El include dice qué símbolos tiene a mano, no qué usa**, y esa es
exactamente la confusión que el ítem 10 daba por buena.

**Cierre: 0 de 55, y la razón es que las dos fuentes propuestas no hablan el idioma.**

## 2 · El número base era 55, no 51, y los 55 están explicados

`vid.h` declara **70 opcodes válidos** (los 78 defines con valor, menos 8 que superan `0xFF` y por
tanto son bases de reubicación, según `1212`). Reparto medido:

```text
  70  opcodes validos en vid.h
  15  declaran al menos un campo
  55  no declaran ninguno
```

Y los 55 se dividen en dos categorías, ambas vaciadas:

```text
  51  su ventana contiene UNA SOLO linea,  que es el opcode siguiente:
         117  #define PACKET3_INDEX_BUFFER_SIZE   0x13
         126  #define PACKET3_PRED_EXEC           0x23
       No hay nada entre medias.  No es trabajo pendiente:  no hay nada.

   4  tienen texto  pero ningun campo.  Son los SET_*_REG:
         SET_CONFIG_REG      SET_CONTEXT_REG      SET_SH_REG      SET_UCONFIG_REG
       y su unico contenido son las bases de reubicacion:
         341  PACKET3_SET_CONFIG_REG_START    0x00002000
         342  PACKET3_SET_CONFIG_REG_END      0x00002c00
       que 1212  ya demostro que no son opcodes  -- PACKET3() enmascara con & 0xFF --
       y por tanto no son campos.
```

**Conclusión: de los 55 no queda ni uno pendiente.** No es "el 73 % sin declarar" que temí en
`1214`: es 55 paquetes que el header no dice porque no tienen estructura declarada, y la
mayoría porque no la necesitan para lo que hacen.

Y una advertencia, porque aquí hay dos cincuentas y una es casualidad:

```text
  51  ventanas de una linea           <- esto es lo que medí en 1214
  51  macros que el corte de seccion descarta  <- 99 - 48,  otra cosa
```

Coinciden en el número y **no son lo mismo**. Lo digo porque la tentación de unirlos es justo el
error que hace parecer el trabajo más grande de lo que es.

## 3 · Cuatro defectos de `pm4_grupos.py`, todos míos, todos con la mutación que los mata

Todos los encontré porque quise usar `--plano` y reventó. Ese es el resumen honesto: **el modo
existía, se había escrito, y nunca se había ejecutado hasta el final.**

### Defecto 1 — `--plano` nunca había terminado

```text
  ValueError: too many values to unpack (expected 4)
    pm4_grupos.py:286, en layout()
```

`plano()` guarda en `_ajenos` **nombres sueltos** (`salida.setdefault("_ajenos", []).append(nombre)`,
línea 209) como un cubo de contabilidad. `informe_plano()` iteraba **todos** los grupos y pasaba
`_ajenos` a `layout()`, que desempaqueta cuatro nombres por fila. Un string de cinco letras
desempaquetado en cuatro nombres: `ValueError`.

Lo llamativo es que **el selftest ya lo sabía y lo excluía** (`pl_ok = {k: v for ... if k != "_ajenos"}`).
El selftest filtrando un bucket que el informe no filtraba. O sea: el instrumento estaba verificado
en un punto y roto en el otro.

Y como `_ajenos` nunca está vacío (99 nombres), este modo **no llegaba nunca al final**. Todo lo
que hubiera salido de él antes estaba sin verificar.

### Defecto 2 — la etiqueta "sin comentario de grupo" era falsa

`UNMAP_QUEUES` tiene **siete** comentarios de dword declarados (`CONTROL`, `CONTROL2a`,
`CONTROL2b`, `CONTROL3a`, `CONTROL3b`, `CONTROL4`, `CONTROL5`) y `informe_plano()` los
aplastaba en una sola lista. Resultado:

```text
  PACKET3_UNMAP_QUEUES_ACTION           << 0   ->  bits [-1:0] =  0 bits  holgura -2
  PACKET3_UNMAP_QUEUES_PASID            << 0   ->  bits [-1:0] =  0 bits
  PACKET3_UNMAP_QUEUES_RB_WPTR          << 0   ->  bits [ 1:0] =  2 bits
  PACKET3_UNMAP_QUEUES_DOORBELL_OFFSET0 << 2   ->  bits [ 1:2] =  0 bits
  PACKET3_UNMAP_QUEUES_DOORBELL_OFFSET1 << 2   ->  bits [ 1:2] =  0 bits
  PACKET3_UNMAP_QUEUES_DOORBELL_OFFSET2 << 2   ->  bits [ 1:2] =  0 bits
  PACKET3_UNMAP_QUEUES_DOORBELL_OFFSET3 << 2   ->  bits [ 3:2] =  2 bits
```

**Cuatro campos en `<< 2` y anchuras negativas.** Un dword no puede empezar en `<<0` cuatro veces.
La causa es que los cuatro `DOORBELL_OFFSET` están en `CONTROL2b`, `CONTROL3b`, `CONTROL4` y
`CONTROL5`: son cuatro dwords distintos, y al achatarlos se pisan. Corregido, cada uno tiene 30
bits en su dword y los huecos salen `[0:1]`.

### Defecto 3 — mi primera corrección del defecto 2 estaba mal, y la segunda también

Escribí `grupos_por_paquete()` indexando por **nombre de grupo** (`grupo_de["CONTROL"]`), olvidando
que hay 14 comentarios repartidos entre varios paquetes: el diccionario mezclaba paquetes y
`PACKET3_UNMAP_QUEUES` salía vacío, o sea el mensaje seguía diciendo "sin comentario de grupo".
Cuando añadí `paq = op.group(1)` sigueba fallando porque antes solo hacía `paq = None` al ver un
opcode, **nunca le asignaba el nombre**. Dos intentos, dos fallos, y solo se ven leyendo la salida.

### Defecto 4 — la sección de paquetes no tiene final, y `plano()` no lo buscaba

```text
  vid.h:112   PACKET3_NOP              0x10      <- empieza la seccion de paquetes
  vid.h:455   (ultima linea de la seccion)
  vid.h:456   VCE_CMD_NO_OP            0x00000000   <- otra lengua de comandos
```

`QUERY_STATUS` es el **último** opcode `PACKET3` (`vid.h:436`), así que no hay opcode siguiente que
suelte `paq`, y `plano()` seguía hasta el fin del fichero. Se comía **32 macros** de las copias de
registro `RB_*/PKR_*/SC_*/SE_*` (`vid.h:480-506`), que son las copias literales de
`PA_SC_RASTER_CONFIG` y `PA_SC_RASTER_CONFIG_1` que `1221` ya había identificado.

```text
  antes   PACKET3_QUERY_STATUS   (38 macros, sin comentario de grupo)
  ahora   PACKET3_QUERY_STATUS   (6 macros, REPARTIDOS en 3 grupos)
          CONTEXT_ID INTERRUPT_SEL COMMAND PASID DOORBELL_OFFSET ENG_SEL
```

Y `1221` tenía razón en lo que vio, pero no en el alcance: las copias de registro **no son
campos de ningún paquete**, y mi atribución por posición las contaba como si lo fueran. Es
`1213` y `1215` por el otro extremo: no por el principio de la ventana, por el final.

### La defensa, y por qué hizo falta dos veces

Cinco mutaciones, cada unaPON en rojo un vector con nombre:

```text
  A  quitar el corte de seccion               ->  "ninguna ventana pasa de la linea 455"   FALLA
  B  devolver _ajenos a layout()              ->  "informe_plano() se ejecuta entero"      FALLA
  C  no nombrar el paquete en el grupo        ->  "UNMAP_QUEUES reparte en 7 grupos"      FALLA
  D  P_GRUPO sin el sufijo a/b                ->  "el filtro no pierde ninguno de los 14" FALLA
  E  _ajenos en la salida de plano()          ->  "vid.h da lista plana a 15 paquetes"    FALLA
```

**La mutación B estuvo en verde al principio.** El vector que yo tenía comprobaba el diccionario,
no ejecutaba `informe_plano()`, que es donde estaba el fallo. Es el fallo de `1209` por tercera vez:
**un selftest que pasa mientras el instrumento está roto, porque no toca el código que se rompe.**
El vector que lo mata tiene que ejecutar el recorrido, no mirar el estado. Ahora lo ejecuta.

## 4 · Tres vectores del propio selftest estaban mal, y eso también es mío

Antes de que los nuevos vectores dieran verde, fellaron cuatro viejos. Ninguno era fallo del
código: eran expectativas calibradas contra el comportamiento contaminado.

```text
  "99 macros tienen nombre que no lleva el de su paquete"   ->  son 48
      Verificado por DOS metodos independientes:  recorte explicito 113..455
      cuenta 48;  sin recorte cuenta 99.  Los 51 de diferencia  son los que el
      corte excluye.  El 99 estaba bien medido en su momento  y mal de objetivo.

  "el discrepante PKR_MAP esta en la lista de ajenos"      ->  ya no esta
  "el discrepante SE_PAIR_YSEL_MASK esta en la lista..."   ->  ya no esta
      PKR_MAP esta en vid.h:488  y SE_PAIR_YSEL_MASK en :513.  Las dos estan
      FUERA de la seccion 112..455.  Los vectores exigian que fueran campo de un
      paquete cuando son copias de registro de otro documento.

  "nadie pone un desplazamiento mayor que 0xFF como opcode" ->  mal escrito
      Comprobaba P_OPCODE,  que es un PATRON y no un filtro:  casa con
      SET_SH_REG_START=0x2c00 y con cualquier valor grande.  El filtro de 0xFF
      vive dentro de ventanas().  El vector fallaba por su cuenta.  Lo que si
      importa  y si se mide:  78 defines con valor,  8 superan 0xFF  y quedan fuera.

  "sin el corte los ajenos serian 99"                       ->  decia 71
      Escribi len(diccionario)  en vez de  len(diccionario["_ajenos"]).
      71 = los 70 opcodes mas el cubo.  Un numero tomado del sitio equivocado,
      que es la misma causa raiz que los otros tres.
```

Los cuatro eran **míos**, y los cuatro salían verosímiles. Lo que los delató no fue el código:
fue que la guarda global de recuento (`VECTORES_ESPERADOS`) avisara de que faltaban vectores por
ejecutar. Esa guarda, puesta en `1209` por un fallo de selftest, acaba de pagar.

## 5 · Un efecto lateral: queda corroborada la lectura de `1228`

`UNMAP_QUEUES` usa `CONTROL2a` / `CONTROL2b` y `CONTROL3a` / `CONTROL3b`. `MAP_QUEUES` usa
`CONTROL2a` / `CONTROL2b` (cerrado en `1207`). Y `QUERY_STATUS` usa `CONTROL2a` / `CONTROL2b`
(`vid.h:449,451`).

**La convención `a`/`b` es sistemática**, y en los tres casos la mitad `a` lleva un campo en `<<0`
o `<<1` y la mitad `b` arranca en `<<2`:

```text
  MAP_QUEUES     CONTROL2a: CHECK_DISABLE <<1        CONTROL2b: DOORBELL_OFFSET <<2 ...
  UNMAP_QUEUES   CONTROL2a: PASID        <<0        CONTROL2b: DOORBELL_OFFSET0 <<2
  QUERY_STATUS   CONTROL2a: PASID        <<0        CONTROL2b: DOORBELL_OFFSET <<2
```

En `MAP_QUEUES` la prosa dice `CONTROL2` **en singular** y aun así hay dos comentarios: y aun así
`1207` cerró el layout con `PIPE=2, ME=1, QUEUE=3` exactos. Eso es el precedente que decide la
contradicción de `1228`: **la prosa nombra un dword y el header lo subdivide en dos mitades, y la
mitad `a` no es un segundo dword.** Así que `PASID` sigue quedando en `[1:0]`, dos bits, y la
salida (b) de `1228 §4` es la buena: la prosa acierta y `PASID` es un campo mal nombrado en los
cuatro headers. Ninguno de ellos es de GFX8, así que para la RX550 la consecuencia es la que ya
escribí: no copies `PASID` porque el driver no te da ni un ejemplo de cómo se usa.

## 6 · Procedimiento

```text
PREGUNTA   (a) cuanto de los paquetes sin estructura resuelve uvd_v6_0.c y vce_v*.c
           (b) cuantos hay realmente sin estructura declarada
FUENTES    conteo de OCURRENCIAS de PACKET3(, PACKET0( y VCE/HEVC/VCN por fichero
           vid.h:96 (PACKET0),  :105-107 (PACKET3),  :112-455 (seccion),  :456 (VCE)
           los puntos de include de vid.h
           las 70 ventanas de opcode y su cuerpo, una a una
MEDIDO     uvd_v6_0.c 0 PACKET3 / 30 PACKET0 / 11 VCE      gfx_v8_0.c 56 PACKET3
           70 opcodes validos,  15 con campos,  55 sin ninguno
           51 ventanas de una sola linea (solo el opcode siguiente)
            4 con solo bases de reubicacion,  no campos
           uvd_v6_0.c INCLUYE vid.h  y no lo usa para PACKET3
DISPOSITIVO  NINGUNO.  i915 y amdgpu intactos.
RUNTIME      NOT_RUN
LO QUE SIGUE
  - ítem 11:  declarar SATURATED el frente PM4 con el motivo escrito.  Con este
    hallazgo  la cuenta queda:  55 sin estructura y los 55 explicados,  15 con
    estructura y de los 15  5 con prosa de dwords.  Ese es el frente completo.
  - ítem 12:  una lectura controlada sobre 0000:01:00.0.  Cerraria ENG_SEL de
    25 bits (1228) y el PTE de 074,  que ya no tienen mas soporte estatico
```
# 1137 — La ventana `SET_SH_REG` deducida **desde el lado contrario**: los 51 registros que el driver inicializa solo caben en ella. Un test que no puede decidir su final, y lo dice

```text
AGENCIA=RX550-INVESTIGACION · WORK_CLASS=VALIDATION · INSTRUMENT-EXTENSION
AUTOR=AGENTE-INSTR
WRITE_EXECUTION=NONE · MODIFICATIONS=0 · RUNTIME=NOT_RUN
ESCRITOS_POR_ESTA_ITERACION   tools/mmio.py      (--tabla, --cual, 43 -> 48 vectores)
                              tools/verif.py     (1 medida, 43 -> 44)
                              08-ARQUITECTURA/artifacts/R11-MMIO/cual-ventana.txt
MODIFICADO_NADA_EXISTENTE    pm4_codec.py, pm4_emit.py, doclint.py INTACTOS
CLASSIFICATION=IMPLEMENTATION · VALIDATION · CORROBORATION
GENERADO=2026-10-04 · MEDIDO=EN ESTA HOST
ESTADO=3 TABLAS COMPROBADAS · VENTANA IDENTIFICADA DE FORMA UNICA · 44 MEDIDAS
```

## 0 · El resultado, primero

```text
CAPACIDAD NUEVA   mmio --tabla <array>   el mismo mapa inverso, aplicado a datos
                  ESTATICOS en vez de a una IB, con la pregunta que hace falta:
                  ¿este registro cabe en alguna ventana DECLARADA?

Y SU VERSION IDENTIFICADORA
                  mmio --tabla <array> --cual
                  ¿de cuál de las ventanas habla esta tabla?

MEDICION          vgpr_init_regs    17 registros   caben SOLO en SET_SH_REG
                  sgpr1_init_regs   17 registros   caben SOLO en SET_SH_REG
                  sgpr2_init_regs   17 registros   caben SOLO en SET_SH_REG
                  (las tres tablas tienen contenido DISTINTO: sha distinto)

DISCRIMINACION   ventana            dentro   fuera
                 SET_CONFIG_REG         0       17    descartada
                 SET_SH_REG            17        0    COINCIDE
                 SET_CONTEXT_REG        0       17    descartada
                 SET_UCONFIG_REG        0       17    descartada

LIMITE DECLARADO este test identifica la BASE, NO el final de la ventana.
                 Medido: los 51 registros ocupan [0x2E07, 0x2E49], asi que
                 cualquier final mayor que 0x2E49 tambien los contiene.

DEFECTO QUE NO   ninguno. Las 51 caben. Un test que pasa no es un hallazgo por
                 si solo: es una comprobacion que queda puesta.
```

## 1 · POR QUÉ ESTO NO ES LO MISMO QUE LEER LA CABECERA

Hasta ahora `mmio.py` **leía** la ventana de `vid.h`. Eso es exactamente lo que
hacen los otros tres oráculos de `layoutcross`: toman la afirmación de una
fuente y la contrastan con otra del mismo дереcio.

Aquí el sentido está invertido:

```text
ANTES   ventana  <- vid.h            (la fuente dice)
AHORA   ventana  <- donde escribe el driver   (el uso dice)

la fuente y el uso son independientes: `vid.h` declara 0x2C00, y el resultado
de que los 51 registros que el driver inicializa caigan dentro de [0x2C00,
0x2C00+0x400) no se deduce de `vid.h` en absoluto.
```

Y por eso discrimina. Con la base de `SET_CONFIG_REG` los 17 registros caen
**todos** fuera; con la de `SET_SH_REG`, **todos** dentro. La comprobación
distingue las cuatro ventanas.

Es la diferencia entre corroborar y deducir, y es la que hace que esto valga
como evidencia y no solo como cobertura.

## 2 · LAS TRES TABLAS, Y POR QUÉ TRES

`gfx_v8_0_do_shader_init` inicializa el estado de shader de tres bloques:

```text
vgpr_init_regs[]    gfx_v8_0.c:1382    17 pares registro/valor
sgpr1_init_regs[]   gfx_v8_0.c:1403    17 pares
sgpr2_init_regs[]   gfx_v8_0.c:1424    17 pares
```

Contenido distinto — sha256 del cuerpo sin comentarios distinto en las tres —
así que no son copias.

Las tres, y no una, porque **una sola no distinguiría "la ventana es esta" de
"esta tabla cae aquí por casualidad"**. Con tres tablas distintas que coinciden
en la misma ventana, la coincidencia no puede ser casualidad de una tabla.

Y `verif` mide las tres por eso: si una sola se saliera de la ventana, saldría
`mmio.tablas_en_ventana` de la clase `VACIA` y la puerta se cerraría.

## 3 · LO QUE EL TEST **NO** PUEDE DECIDIR, Y POR QUÉ IMPORTA DICIRLO

```text
rango de registros usado por la tabla:   [0x2E07, 0x2E49]

ventana [0x2C00, 0x3000)  ->  17 de 17 DENTRO
ventana [0x2C00, 0x3400)  ->  17 de 17 DENTRO
ventana [0x2C00, 0x3C00)  ->  17 de 17 DENTRO
```

El test **no puede determinar el final** de la ventana, porque todos los
registros que el driver inicializa están en el primer tercio de ella. Cualquier
ventana que empiece en `0x2C00` y termine más allá de `0x2E49` los contiene
todos.

Esto está escrito en la salida del instrumento, no solo aquí:

```text
AVISO  esto identifica la BASE de la ventana, no su final:
       si todos los registros se concentran al principio
       de la ventana, cualquier final mayor tambien los
       contiene. El final NO lo decide este test.
```

Y hay un vector que lo fija, porque si no el aviso es decorativo:

```text
cual-ventana: se declara que esto NO decide el final de la ventana
cual-ventana: se declara que identifica la BASE, no la ventana entera
```

> **Un test que se sabe limitado y lo declara vale más que uno que parece
> completo.** Si no hubiera escrito el aviso, el resultado "`SET_SH_REG`
> coincide, 17 de 17" se leería como "la ventana es `[0x2C00, 0x3000)`", y no
> lo es: lo único probado es la base.

El final sigue viniendo de `vid.h`. Lo que este test añade es que **la base no
se sostiene sola en la cabecera**, y eso es un dato sobre la solidez del
conjunto de afirmaciones.

## 4 · LOS ERRORES DE ESTA ITERACIÓN

### 4a · Una medida que disparaba con cada acierto

La primera versión de `mmio.tablas_en_ventana` contaba los registros "fuera" de
**cada ventana individual**. Salía con 9 entradas:

```text
vgpr_init_regs:PACKET3_SET_CONFIG_REG_fuera=17
vgpr_init_regs:PACKET3_SET_CONTEXT_REG_fuera=17
vgpr_init_regs:PACKET3_SET_UCONFIG_REG_fuera=17
   ... las mismas tres para las otras dos tablas
```

Y eso **no es un defecto**: es los 17 registros fuera de la ventana que no es
la suya, que es exactamente la prueba de que la prueba discrimina. La medida
contaba los aciertos como si fueran errores.

Lo correcto es lo que ahora hace:

```text
1. FUERA_DE_TODAS con las CUATRO ventanas a la vez. Un registro fuera de la
   ventana correcta pero dentro de otra no es un defecto: es el mecanismo de
   identificacion funcionando. Solo es defecto cuando no cabe en NINGUNA.

2. la ventana debe ser UNICA. Si una tabla cabe en dos, la base no esta
   determinada y la decodificacion seria ambigua.
```

> **Una medida que se dispara con cada acierto es una medida que obliga a mirar y
> no enseña nada.** Y peor: como es `VACIA`, cualquier valor obliga a revisar, y
> quien lo revise verá 9 líneas que parecen avisos y pensará que hay 9 fallos.
> El resultado de una puerta tiene que poder leerse sin adicional.

### 4b · Tres bugs de Python, todos míos, todos en el primer intento

```text
1. `rc, _e = ejecutar(...)`  ->  `KeyError: 1`
   `ejecutar` devuelve una TUPLA. Desempaquetarla en dos variables da el primer
   elemento y el segundo, y luego `rc[1]` indexa un dict. Lo inexplicable
   durante un minuto.

2. La declaracion de `mmio.escala` quedo partida por la mitad al insertar otra
   antes: `SyntaxError: unterminated string literal`. Insertar en una tupla de
   MEDIDAS por indice de texto es fragil; el texto multilinea hace que el
   `index("),")` caiga donde no toca.

3. Dos variables llamadas `ok` en el mismo bloque (una lista de ventanas, un
   walrus dentro de un `return`), y una vez `return 0 if len(ok := [...]) == 1`
   despues de haber impreso `ok` como texto. Funciona por accidente.
```

El primero es el que más tiempo costó, y el motivo es que `KeyError: 1` no
apunta al sitio: **el error estaba en la lectura del resultado, no en el
resultado.** Es el mismo patrón que el `TypeError: string indices must be
integers` de `1134`, y conviene decirlo porque es la clase de error que hace que
uno busque en el sitio equivocado.

### 4c · Un fallo de parseo que no lanza excepción

El primer `_partir_por_comas` partía por comas **antes** de quitar los
comentarios:

```text
mmCOMPUTE_RESOURCE_LIMITS, 0x1000000, /* CU_GROUP_COUNT=1 */

la coma de dentro del comentario cuenta como entrada
una tabla de 34 elementos sale de una de 32, y luego "17 registros" sale
parecido a "los 17 que hay" y nadie ve nada raro
```

Vector que lo fija:

```text
tabla: las comas de un comentario NO cuentan como entradas
       _partir_por_comas("a, 1, /* x, y, z */ b, 2") == ["a","1","b","2"]
tabla: una coma dentro de parentesis no trocea
```

Un parser que devuelve un número plausible equivocado no lanza excepción, no
avisa y no se nota hasta que el número se usa para otra cosa. Es la clase que
el proyecto llama *descartar en silencio*, y aquí era *contar en silencio*.

## 5 · PROCEDIMIENTO

```text
nuevas capacidades   mmio --tabla <array> [--cual] [--json]
vectores             mmio 31 -> 48, rc=0
puerta               43 -> 44 medidas, SIN DERIVA
                     mmio.tablas_en_ventana = []   (VACIA = las 3 caben)
                     perturbada con una entrada inventada   rc=1
                     restaurada                                rc=0

medicion             vgpr/sgpr1/sgpr2_init_regs   17 registros cada una
                     3 tablas, contenido distinto, misma ventana unica
                     [0x2E07, 0x2E49] es el rango que ocupan

artefacto            08-ARQUITECTURA/artifacts/R11-MMIO/cual-ventana.txt
otros instrumentos   layoutcross 79 vectores rc=0
                     ibref        39 vectores rc=0
escrituras           0 ficheros de otros agentes
```

## 6 · LO QUE NO ESTÁ HECHO

**El final de la ventana sigue sin comprobar.** Se ha dicho en la salida y aquí.
Lo que falta para cerrarlo es un registro que el driver inicialice en la parte
**alta** de `[0x2C00, 0x3000)`. Con `sgpr_init_regs` de otras generaciones, o
con un ASIC distinto, se podría. Aqui no hay ninguno.

**No he desenrollado los bucles.** El `for (i = 0; i < ARRAY_SIZE(x); i += 2)`
de `gfx_v8_0_do_shader_init` sigue sin sintetizarse, así que la IB completa de
inicialización de shader todavía tiene 12 payloads `SIN_LIGAR`. Con `--tabla` he
resuelto la **misma información por otra vía** —la tabla estática en vez de la
IB— y eso cierra la pregunta pero no el caso de uso original. Desenrollar el
bucle es trabajo de instrumento, no de datos, y es lo siguiente natural.

**`MULTIPLE` sigue sin verse en ejecución.** Sin cambios.

**No he comprobado `sgpr_init_regs` con otros nombres.** Las tres tablas que
he encontrado tienen esos nombres; puede haber más en `soc15d.c` o en
`gfx_v9_*.c`, y esos son de otra generación con otra escala (`1135`).

**Y nada de esto es evidencia de hardware.** `RUNTIME=NOT_RUN`. Que los
registros que el driver inicializa quepan en la ventana es un hecho sobre el
**código del driver**. Que el hardware acepte esos 51 `reg - 0x2C00` no está
verificado por mí.
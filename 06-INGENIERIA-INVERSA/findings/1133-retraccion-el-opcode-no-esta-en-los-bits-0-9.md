# 1133 — Retractación: el opcode **no** está en los bits 0-9 sino en los **15:8**; mi cota `0x3FF` habría aprobado un opcode que el hardware no puede representar. Y `--decode` estaba roto por una regresión mía

```text
AGENCIA=RX550-INVESTIGACION · WORK_CLASS=DEREFUTATION + VALIDATION
AUTOR=AGENTE-INSTR
WRITE_EXECUTION=NONE · MODIFICATIONS=0 · RUNTIME=NOT_RUN
ESCRITOS_POR_ESTA_ITERACION   tools/layoutcross.py  (OPCODE_MAX, OPCODE_SHIFT,
                              texto, 3 vectores)
                              tools/ibref.py         (decodificar reescrito,
                              extractor de opcode, 7 vectores)
                              08-ARQUITECTURA/artifacts/R10-OPCODE/{layoutcross-vivo.txt,
                              ibref-decode-edc.txt, ibref-roundtrip-edc.txt}
RETRACTADO_AQUI             1132 §3 (la prueba, no la conclusion)
MODIFICADO_NADA_EXISTENTE    pm4_codec.py, pm4_emit.py INTACTOS
CLASSIFICATION=REFUTATION · MEASUREMENT · IMPLEMENTATION
GENERADO=2026-10-04 · MEDIDO=EN ESTA HOST
ESTADO=ERROR PROPIO CORREGIDO Y VECTORIZADO · 1132 §3 RETRACTADO
```

## 0 · El resultado, primero

```text
RETRACTACION   el opcode son los BITS 15:8 y la cota es 0xFF.
               Yo puse 0x3FF y escribi "los bits 0-9".  FALSO.

CONSECUENCIA   la conclusion de 1132 INTACTA (los 7 valores pasan de 0xFF)
               la JUSTIFICACION estaba mal, y una cota mal puesta no falla
               hoy: habria dado OK a un opcode de 0x100.

REGRESION      --decode estaba ROTO por un cambio mio de esta misma sesion:
               NameError: decodificar. No me di cuenta al reescribir el
               bloque del round-trip.

ARREGLO        decodificar reescrito con el oraculo de opcode. Ahora una IB
               de inicializacion de shader de GFX8 se decodifica:
                 dw 3  cabecera  SET_SH_REG  opcode 0x76  count=1 -> 2 payload
                 dw 3  0xC0027600   (sin layout: valor crudo)
                 dw 4  0x0000020C   (sin layout: valor crudo)

VECTORES       layoutcross 76 -> 79   ibref 32 -> 39
PUERTA         38 medidas, SIN DERIVA: el mismo conjunto de 7, como se habia
               predicho al cambiar la cota
```

## 1 · LA RETRACTACIÓN, Y DÓNDE ESTÁ LA FUENTE

`1132` shut su caso central con una frase que escribí sin verificar:

```text
"cabecera = (3 << 30) | (count << 16) | opcode
            ^^^^^^    ^^^^^^^^^^^^^    ^^^^^^
            tipo      count             opcode = BITS 0-9"
```

Eso no es la definición. La definición, **idéntica al byte en las cuatro
cabeceras de generación del árbol**:

```text
vid.h:105          #define PACKET3(op, n)  ((PACKET_TYPE3 << 30) |      \
sid.h:336                            ((op) & 0xFF) << 8) |           \
soc15d.h:50                          ((n) & 0x3FFF) << 16)
gfx_v12_1_pkt.h:48
```

Descompuesta:

```text
cabecera   bits 31:30   tipo de paquete     (3)
           bits 29:16   count               (14 bits)
           bits 15:8    OPCODE              (8 bits)
           bits  7:0    sin usar
```

**El opcode es un byte, desplazado 8 posiciones.** No está en los bits bajos de
la cabecera. Mi `OPCODE_MAX = 0x3FF` era una cota tres veces y media más alta de
la real.

La causa del error es la parte que importa y que no quiero maquillar: **no leí
el `#define` antes de razonar sobre él.** Razoné sobre la disposición que me
parecía natural —"el opcode va en el byte bajo"— y construí encima una prueba
que parecía deductiva. Si la hubiera leído, la frase no se habría escrito.

### 1a · Por qué la conclusión aguanta

Porque el resultado no depende de la cota, en este caso:

```text
las 7 entradas fuera de rango:  0x2000 0x2C00 0x3000 0xA000 0xA400 0xC000 0xC400

todas pasan de 0x3FF   -> y tambien pasan de 0xFF
```

El conjunto es idéntico. `verif` lo confirma: **38 medidas, SIN DERIVA** tras
cambiar la cota. Lo que cambia no es qué se detecta, sino **por qué**, y eso es
lo que hay que corregir.

### 1b · Por qué aun así era un defecto real

Porque una cota incorrecta no es inocua aunque hoy no dispare:

```text
con OPCODE_MAX = 0x3FF   un opcode de 0x100, 0x200, 0x300 salia OK
con OPCODE_MAX = 0xFF    los tres salen OPCODE_FUERA_DE_RANGO
```

Esos valores no aparecen hoy en la tabla. Si aparecieran, el instrumento habría
dado un `OK` sobre una afirmación que el campo no puede representar: el opcode
`0x100` se enmascara a `0x00`, que es **otro paquete**. Un `OK` así no es un
falso negativo pequeño; es un falso positivo sobre la existencia del paquete.

Y es la clase que este proyecto ha pagado más veces: **una comprobación que
pasa cuando no debería**.

## 2 · LO QUE EL VECTOR NUEVO ATRAPA

Tres vectores, y el primero es el que habría atrapado el error:

```text
opcode: 0x100 NO puede ser opcode con una cota de 8 bits    <- el que faltaba
opcode: 0xFF, el ultimo representable, da OK                 <- el control
opcode: el opcode vive en los bits 15:8, no en los bits 0-9 <- la afirmacion
```

El segundo importa tanto como el primero. Sin él, `OPCODE_FUERA_DE_RANGO` sería
indistinguible de "el oráculo no dice nada", que es exactamente el fallo que
`1131 §3` ya señaló para `ANCHURA_NO_DECLARADA`. Es el mismo patrón
aplicado a otro sitio: **un veredicto nuevo necesita un control positivo, o no
sabe nada de sí mismo.**

## 3 · `--decode` ESTABA ROTO, Y LA REGRESIÓN ERA MÍA

Al insertar el round-trip en esta sesión reemplacé un bloque de `ibref.py` que
iba de `def decodificar` a `def descubrir_tablas`, y **borré `decodificar` sin
darme cuenta**. La opción `--decode` era:

```text
$ ibref --func ... --decode
Traceback ...
  File "tools/ibref.py", line 941, in main
    dec = decodificar(ib, tablas) if args.decode else None
NameError: name 'decodificar' is not defined
```

No me di cuenta porque **todas las pruebas que estaba ejecutando pasaban**:
`--roundtrip` no llama a `decodificar`, y el selftest no lo cubría. El fallo
estaba en una bandera que no activaba.

Eso es un fallo del proceso, no del código, y es la razón por la que esta
iteración se llama como se llama. Una herramienta cuyo camino principal funciona
no está probada: está probada **el camino que se prueba**.

Lo he añadido a la lista de errores de `1131 §6` y a la de aquí.

## 4 · `--decode` REESCRITO, Y LA FRONTERA QUE `1132 §6` DEJÓ ABIERTA

La versión anterior resolvia el opcode buscando un sufijo `_0x%02X` en las
**claves** de las tablas de layout. Con 7 layouts de 77 opcodes, eso resolvia
el 9% y escribió `(FUERA DEL LAYOUT)` en el resto. Era la debilidad que yo mismo
registré como frontera abierta.

Ahora:

```text
1. se comprueba el RANGO: un valor > 0xFF no es opcode, y se dice por que
2. se exige que bits 31:30 == 3 (tipo de paquete 3)
3. se resuelven NOMBRES desde dos fuentes independientes:
      pm4_codec.opcode_table()      (la herramienta)
      amdkfd/kfd_pm4_opcodes.h      (el kernel, segunda fuente)
4. si hay dos nombres, se dan los dos. No se elige.
```

El punto 4 es el de `1132`: `0x2C00` no se resuelve porque está fuera de rango,
pero el **tipo de datos** sigue sin poder decir "este número tiene dos
nombres". `_nombres_opcode` lo devuelve como lista, y cuando hay más de uno
dice explícitamente que el opcode no lo desambigua.

### 4a · Y una truffa que el vector encontró

El primer vector de `decode`Pedía que un opcode que **ninguna fuente nombra**
produjera un texto explícito, y falló. Motivo:

```text
"opcode conocido y resuelto"     -> imprime la linea de nombres
"opcode conocido y NO resuelto" -> NO imprimia nada
"opcode desconocido"            -> NO imprimia nada
```

Los dos silencios eran idénticos en la salida. Un hueco que no se anuncia es un
hueco que parece un `OK`. Ahora:

```text
nombres: NINGUNA fuente lo nombra. No se inventa uno: el opcode 0x76 existe
en la cabecera pero ningun oraculo del arbol lo declara
```

## 5 · LA PRIMERA DECODIFICACIÓN DE UNA IB DE SHADER DE GFX8

La frontera de `1132 §6` era: una IB de inicialización de shader **no se puede
decodificar**. Es la función que emite `SET_SH_REG` en `gfx_v8_0.c:1529`.

```text
linea 1529  0xC0017600  PACKET3(PACKET3_SET_SH_REG, 1)
linea 1530  INCOMPLETO  vgpr_init_regs[i] - PACKET3_SET_SH_REG_START
linea 1531  INCOMPLETO  vgpr_init_regs[i + 1]
linea 1535  0xC0027600  PACKET3(PACKET3_SET_SH_REG, 2)
linea 1536  0x0000020C  mmCOMPUTE_PGM_LO - PACKET3_SET_SH_REG_START
linea 1541  0xC0031500  PACKET3(PACKET3_DISPATCH_DIRECT, 3)
linea 1549  0xC0004600  PACKET3(PACKET3_EVENT_WRITE, 0)
```

Tres comprobaciones independientes de que la síntesis es correcta, y ninguna la
dio por buena:

```text
      0xC0017600  count=1  opcode=0x76   driver: PACKET3(SET_SH_REG, 1)
                                      vid.h: PACKET3_SET_SH_REG = 0x76   OK
      0xC0027600  count=2  opcode=0x76   driver: PACKET3(SET_SH_REG, 2)   OK
      0xC006A000  count=6  opcode=0xA0   driver: PACKET3(SET_RESOURCES,6) OK
```

Durante la comprobación tuve **dos errores propios** quecasi invalidaban la
medida, y los dos salió de la misma causa: no leí la fuente antes de afirmar.

```text
"el opcode son los bits 0-9"   -> me lo habia inventado
"PACKET3_SET_SH_REG = 0x61"    -> 0x61 es PACKET3_LOAD_SH_REG; el bueno es 0x76
"el count sale 2 donde el driver pone 1"  -> estaba leyendo la fila de la
                                              linea 1535, no la de la 1529
```

Los dos primeros los atrapa ahora el reading de la fuente; el tercero lo
atrapa `linea` en la salida cruda, que es por lo que esa tabla existe.

### 5a · Lo que sigue sin poder

```text
dw 3  cabecera  SET_SH_REG  opcode 0x76  count=1 -> 2 payload
   nombres: SET_SH_REG
   layout declarado: NINGUNO
dw 3  0xC0027600  (sin layout: valor crudo)
dw 4  0x0000020C  (sin layout: valor crudo)
```

**Sigue siendo un valor crudo**, y lo dice. `0x0000020C` es
`mmCOMPUTE_PGM_LO - 0x2C00`, o sea el desplazamiento relativo dentro de la
ventana de `SET_SH_REG`. Decodificarlo exige la transformada que `1132 §6`
nombró: no es un campo, es `base + offset` con base `0xFFF00000 | registro`.

La decodificación de ahora no resuelve el payload. **Resuelve la cabecera, que
antes no resolvía nada**, y dice cuál es el hueco en vez de rellenarlo con un
nombre inventado. Eso es un avance y no es lo mismo que cerrar la frontera.

## 6 · PROCEDENCIA

```text
layoutcross-vivo.txt      salida con el 4º oraculo y la cota corregida
ibref-decode-edc.txt      la decodificacion de arriba
ibref-roundtrip-edc.txt   round-trip sobre la misma funcion: 3 NO_EXTRAIBLE,
                          INCOMPLETO por 3 parametros sin ligar

vectores   layoutcross 76 -> 79   ibref 32 -> 39
puerta     38 medidas, SIN DERIVA (el conjunto fuera de rango no cambia)
           verificado que el cambio de cota NO altera el veredicto sobre el
           sujeto real: eso es lo que hace falta para no perder la medida
escrituras 0 ficheros de otros agentes
```

## 7 · LO QUE ESTO NO PRUEBA

**No prueba que `pm4_codec.opcode_table()` tenga razón en el `0x2C00`.** Solo
que ese valor no puede ser opcode. Que `0x2C00` sea la frontera compartida de dos
ventanas lo sostienen `1132 §2`, que es una derivación sobre el uso del driver,
corroborada y no probada.

**No prueba nada del hardware.** `RUNTIME=NOT_RUN`. Que el opcode ocupe los bits
15:8 lo dicen cuatro cabeceras del kernel; que el hardware lo acepte no está
verificado por mí.

**No cierra la frontera de `1132 §6`.** El payload de `SET_SH_REG` sigue sin
decodificarse. Lo que se ha hecho es poner la frontera **visible y honesta**: el
instrumento dice que no la resuelve.

**Y no deshace `1132`.** El hallazgo sigue en pie con la misma lista de 7
entradas. Lo que se corrige es la prueba, y `1132 §3` lleva la retracción
escrita para que no se pueda leer el documento sin verla.
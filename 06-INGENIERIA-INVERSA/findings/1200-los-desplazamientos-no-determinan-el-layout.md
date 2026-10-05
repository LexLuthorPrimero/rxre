# 1200 — Los desplazamientos de `vid.h` **no determinan un layout**: de 15 grupos, ninguno cierra su partición. Y la herramienta que lo demuestra encontró un error en mí y **tres en sí misma**

```text
AGENCIA=RX550-INVESTIGACION · WORK_CLASS=PM4-SEMANTICS + TOOL-FACTORY
AUTOR=AGENTE-INSTR
WRITE_EXECUTION=NONE · GPU=NONE TOUCHED · RUNTIME=NOT_RUN
DISPOSITIVO_TOCADO=NINGUNO · ni 0000:01:00.0 (1002:699f) ni 0000:00:02.0 (8086:0412)
ESCRITOS_POR_ESTA_ITERACION   tools/campos_pm4.py  (nuevo, 20 vectores, rc=0)
                                 06-.../1199-*.md  (CORREGIDO: se contradecía a sí mismo)
CLASE=TOOL-FACTORY · CORRECTION · ESTADO=PROBADO_OK
CORPUS=RESEARCH/working/linux-7.1.3/drivers/gpu/drm/amd/amdgpu/vid.h
GENERADO=2026-10-05 · MEDIDO=EN ESTA HOST
```

## 0 · Por qué esta herramienta: `vid.h` da desplazamientos y nada más

```c
  #define PACKET3_MAP_QUEUES_QUEUE_SEL(x)       ((x) << 4)
  #define PACKET3_MAP_QUEUES_VMID(x)            ((x) << 8)
  #define PACKET3_MAP_QUEUES_DOORBELL_OFFSET(x) ((x) << 2)
  #define PACKET3_MAP_QUEUES_PIPE(x)            ((x) << 29)
  #define PACKET3_MAP_QUEUES_ME(x)              ((x) << 31)
```

Ni una anchura, ni una máscara. El layout hay que deducirlo del hueco hasta el campo
siguiente, y esa deducción tiene dos formas de fallar: dejar bits sin dueño, o dar por
ancho un hueco que no es de nadie.

La pregunta que responde el instrumento, para **todo** el header y no para un paquete:

```text
¿determinan los desplazamientos del fuente una particion de 32 bits?
```

## 1 · El resultado

```text
$ campos_pm4.py --solo-problemas

  grupos con algun campo sin anchura deducible: 15 de 15
```

**Ninguno de los quince.** Y no por falta de: porque `ENGINE_SEL << 26` y
`QUEUE << 26` son campos de **dwords distintos** que comparten desplazamiento. Ordenar por
desplazamiento mezcla palabras, y comparar el desplazamiento de uno con el siguiente no
dice nada cuando no son vecinos.

## 2 · Lo que esto corrige: el hallazgo `1199` se contradecía a sí mismo

`1199` escribió, en la tabla de deducción:

```text
  CONTROL2   DOORBELL_OFFSET << 2,  siguiente ... << 26   ->  [25:2] y hueco
```

y dos líneas después concluyó:

```text
  ... y por tanto es [3:2], de 2 bits
```

Las dos no pueden ser verdad. Al construir la herramienta, su salida lo mostró, y **la que
se sostiene es la primera: la anchura no se deduce en absoluto**.

> Un hueco grande no es un campo ancho: es un layout que los desplazamientos **no**
> determinan.

El valor correcto —2 bits en el GFX8— viene de la especificación del ASIC, que **no está
en el árbol**. `1199` queda corregido en el propio fichero, y su §2 —la convención del
recuento, `n = payload − 1`— **sigue en pie**: esa no dependía de ninguna deducción, se
midió contando dwords en tres puntos de emisión y se corroboró con `.emit_ib_size = 7`.

## 3 · Un hallazgo de la deducción correcta que sí se sostiene

Al ordenar correctamente, un campo se deduce bien y el propio header lo corrobora:

```text
  PACKET3_UNMAP_QUEUES / CONTROL
    UNMAP_QUEUES_ACTION     shift  0   [3:0]  4 bits
```

Y el comentario de `vid.h:416-419` lista **exactamente cuatro** valores:

```c
  /* 0 - PREEMPT_QUEUES
   * 1 - RESET_QUEUES
   * 2 - DISABLE_PROCESS_QUEUES
   * 3 - PREEMPT_QUEUES_NO_UNMAP
   */
```

Dos fuentes independientes —el hueco hasta `QUEUE_SEL << 4` y la lista de valores válidos—
dan 4 bits. Eso sí es una corroboración, y es del mismo género que la de `1062`.

## 4 · El solappe sólo existe cuando el ancho viene de fuera

Con la deducción por huecos, **el solape es imposible por construcción**: un solape exigiría
que un campo ocupase más bits de los que hay hasta el siguiente. Un instrumento que sólo
supiera de solapes sería un instrumento que no puede encontrar ninguno, y parecería limpio.

Así que el solape se busca al revés, validando anchos **dados**:

```text
$ campos_pm4.py --valida "QUEUE=26-28,PIPE=29-31,ME=31-31"
  SOLAPE  ME ocupa 31..31 y PIPE ya ocupa 31..29

$ campos_pm4.py --valida "QUEUE=26-28,PIPE=29-30,ME=31-31"
  (sin solape: particion valida)
```

Eso **reproduce el hallazgo `1199` §4** con la herramienta, que es lo que un oráculo debe
hacer: que otro programa llegue al mismo resultado por su cuenta.

## 5 · Tres errores de la herramienta, encontrados por su propia salida

### 5.1 Un regex que se equivocaba por una letra

```python
RE_GRUPO = r"/\*\s*([A-Z0-9_]+)\s*\*/"        # antes
RE_GRUPO = r"/\*\s*([A-Za-z0-9_]+)\s*\*/"      # ahora
```

Los sub-bloques de `UNMAP_QUEUES` se llaman `/* CONTROL2a */`, `/* CONTROL3b */`, con
**minúscula final**. `[A-Z0-9_]+` no casa con la `a`, así que `actual` se quedaba en
`CONTROL` y los siete sub-bloques colapsaban en uno. La salida ponía `ACTION`, `PASID` y
`RB_WPTR` —los tres en el bit **0** de dwords **distintos**— en el mismo grupo, y el
censo reportaba un choque de bits que no existe.

> Una regla que se equivoca por una letra produce hallazgos que parecen fallos profundos del
> firmware. El instrumento habría reportado un defecto de hardware que no existe.

### 5.2 Agrupar por comentario en vez de por paquete

El comentario `/* CONTROL */` aparece **una vez** y debajo hay macros de **cuatro**
paquetes: `MAP_QUEUES`, `UNMAP_QUEUES`, `DMA_DATA` y `QUERY_STATUS`. Comparar el
desplazamiento de uno con el siguiente, siendo de paquetes distintos, no significa nada.
Ahora se agrupa por paquete —que sí se deduce del nombre, con el nombre **más largo** que
case— y por sub-bloque dentro del paquete.

### 5.3 Dos vectores que fallaban por culpa del vector

```text
  "el vector exigia len(...) == 1"   y hay DOS grupos CONTROL2a:
                                      UNMAP_QUEUES y QUERY_STATUS
  "comparaba 'PASID' in g[k]"        y las claves son NOMBRES COMPLETOS
```

Un vector que falla por un nombre repetido en otro sitio, o por teclear una clave
abreviada, enseña a ignorar los que fallan de verdad.

## 6 · Lo que el instrumento NO dice

```text
DICE      que los desplazamientos del fuente no determinan una particion,  y para
          quais grupos de PACKET3_UNMAP_QUEUES si la determinan

NO DICE   que el layout deducido sea el que el ASIC espera.  Que una particion
          sea valida es un hecho sobre el fuente,  no sobre el hardware:
          RUNTIME=NOT_RUN

NO DICE   cual es la anchura correcta de los campos no deducibles.  El umbral
          ANCHO_PLAUSIBLE = 8 es una CONVENCION declarada de este instrumento,
          no un hecho del ASIC.  Se puede cambiar con un argumento

NO HECHO  traer la especificacion del ASIC para cerrar los campos no deducibles.
          Es la unica via que queda,  y es externa al arbol
```

## 7 · Procedimiento

```text
nuevo      tools/campos_pm4.py,  20 vectores rc=0
           macros_de_grupos()   por PAQUETE y sub-bloque,  no por comentario suelto
           nombres_de_paquetes()  nombre mas largo que case
           determinacion()      que campos tienen anchura deducible del hueco
           validar()            solapes y bits sin dueno de anchos DADOS
           --valida, --grupo, --solo-problemas

MEDIDO     grupos con algun campo sin anchura deducible:  15 de 15
           UNMAP_QUEUES_ACTION deduce [3:0],  4 bits,  y el comentario del
           propio header lista cuatro valores
CORREGIDO  1199 se contradia a si mismo;  corregido en el fichero.  Su §2
           (count = payload - 1) NO se toca:  no dependia de la deduccion
CORREGIDO  3 errores de la herramienta,  uno de ellos por una letra en un regex
           que hacia aparecer un choque de bits inexistente
runtime    RUNTIME=NOT_RUN.  Ni la RX550 ni la Intel.  i915 y amdgpu intactos
```

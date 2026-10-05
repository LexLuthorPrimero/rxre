# 1140 — `working/` es un subconjunto de `kernelbuild/` con **4 ficheros editados de 2787**: eso convierte "me falta `ALIGN`" de un problema de corpus en un problema de raíz de includes, con una prueba falsable

```text
AGENCIA=RX550-INVESTIGACION · WORK_CLASS=CORPUS-INTEGRITY · SEMANTIC-CLOSURE
AUTOR=AGENTE-INSTR
WRITE_EXECUTION=NONE · MODIFICATIONS=0 · RUNTIME=NOT_RUN
ESCRITOS_POR_ESTA_ITERACION   tools/verif.py   (grupo `corpus.*`, 2 medidas,
                              46 -> 48 declaradas, 51 en total)
MODIFICADO_NADA_EXISTENTE    pm4_codec.py, pm4_emit.py, gfx_v8_0.c INTACTOS
CLASSIFICATION=MEASUREMENT · CORPUS-INTEGRITY
GENERADO=2026-10-04 · MEDIDO=EN ESTA HOST
ESTADO=TECHO DE LA SINTESIS MEDIDO Y DECLARADO BAJO LA PUERTA
```

## 0 · El resultado, primero

```text
working/linux-7.1.3       2787 ficheros
kernelbuild/linux-7.1.3 103705 ficheros
comunes por ruta          2787      (working ES un subconjunto)
  byte-identicos          2783      (99,9%)
  DIFERENTES                 4      -> los que el proyecto ha EDITADO

ficheros bajo include/   working 1   de  kernelbuild 16322
resolutor de includes     sigue los de "..."   (0 de los de <...>)
```

Los 4 ficheros editados:

```text
drivers/gpu/drm/amd/amdgpu/amdgpu_debugfs.c
drivers/gpu/drm/amd/amdgpu/amdgpu_debugfs.h
drivers/gpu/drm/amd/amdgpu/amdgpu_vm.c
drivers/gpu/drm/amd/amdgpu/amdgpu_vm_pt.c
```

Y `solo en working/`: **0**. working/ no añade ni un fichero al upstream.

## 1 · POR QUÉ ESTO NO ES CURIOSIDAD DE ALMACÉN

Todas las herramientas del proyecto leen de `RESEARCH/working/`. Si un fichero
de ahí se aparta del upstream, **todas las mediciones que dependan de él cambian
de debajo** y ninguna puerta lo dire, porque las medidas que dependen del se
medirían sobre el fichero cambiado: darían su número y no habría deriva que ver.

Eso convierte "el sujeto no ha cambiado" de una suposición en una afirmación
medida:

```text
corpus.ficheros_modificados   ->  el conjunto, NOMBRADO
```

Si el proyecto edita un quinto fichero, la puerta lo dice. Es el invariante que
faltaba, y su ausencia es la razón por la que una puerta de deriva puede dar
verde sobre un sujeto que ha cambiado.

Coste: 2,4 s de sha256 sobre 2787 ficheros. Aceptable para una puerta.

## 2 · `ALIGN`: POR QUÉ NO SE PUEDE RESOLVER, Y POR QUÉ SÍ SE PODRÍA

`1139 §9` dejó `vgpr_offset` y `sgpr_offset` sin ligar, y la causa lejana es esta:

```c
/* gfx_v8_0.c:1495 */
total_size = (((ARRAY_SIZE(vgpr_init_regs) / 2) * 3) + 4 + 5 + 2) * 4;
total_size += ...
total_size = ALIGN(total_size, 256);
vgpr_offset = total_size;
```

`ALIGN` no está en las 83441 macros que carga `pm4_emit`. Y hay **dos**
causas independientes, ambas medidas:

```text
1. working/linux-7.1.3/include/ contiene 1 fichero, de los 16322 del upstream.
   include/linux/align.h NO esta en working/.
   align.h esta en kernelbuild/linux-7.1.3/include/linux/align.h:8

2. INC_RE de pm4_emit es  #\s*include\s+"([^"]+)"
   COMILLAS. Los includes de kernel usan <>.
   Medido sobre el patron real:  #include <linux/align.h> -> NO casa
                                #include "align.h"        -> casa
```

Añadir la raíz nueva **sin** arreglar el regex no arregla nada. Son dos
barreras, y por eso el hueco tiene dueño y no es "no se ha buscado".

## 3 · EL HECHO QUE CONVIERTE EL HUECO EN UN TRABAJO CONCRETO

Si `working/` es un subconjunto de `kernelbuild/` con 2783 de 2787 ficheros
byte-idénticos, entonces **`kernelbuild/` es un suplemento demostrablemente
seguro**:

```text
para todo fichero que existe en los dos        -> byte-identico
para todo fichero que SOLO existe en kernelbuild -> no lo puede contradecir
                                                 (working no lo tiene)
excepto 4 ficheros, nombrados                   -> y ninguno de ellos es
                                                   un header de include/
```

Eso da un contrato con prueba falsable, no una esperanza:

```text
C1  Añadir  RESEARCH/kernelbuild/linux-7.1.3/include  como ULTIMA raiz.
    El resolutor prueba los directorios EN ORDEN y se queda con el primero que
    existe (pm4_emit.py:117-121), asi que una raiz al final es exactamente
    semantica de RESPALDO: un fichero presente en working/ siempre gana.

C2  Antes de usarla, comprobar que los 4 ficheros modificados NO estan bajo
    include/. Si alguno lo estuviera, esa raiz quedaria descartada para ese
    nombre, y hay que decirlo.

C3  Ampliar INC_RE a <...>, con la DIRECTORIO de la busqueda: un include de
    kernel con <> se resuelve contra include/, no contra el directorio del
    fichero que incluye. Resolverlo como si fuera relativo daria el fichero
    equivocado sin avisar.

C4  Tras C1+C3, `ALIGN` debe resolver. Y hay un discriminante que no es "funciona":
    `ALIGN(0,256)=0`, `ALIGN(1,256)=256`, `ALIGN(256,256)=256`,
    `ALIGN(257,256)=512`. Si los cuatro no salen, la transformada no es la de
    round-up.
```

`C4` es el punto: un contrato de reparación sin vectores que puedan fallar no
es un contrato, es una intención.

## 4 · LO QUE ESTO NO ABRE, Y HAY QUE DECIRLO

**No he aplicado nada de `C1..C4`.** `pm4_emit.py` es de otra sesión y `C3` toca
su `INC_RE`. Se reporta.

**No he demostrado que `ALIGN` baste para los offsets.** Aunque se resuelva,
`total_size` es una **variable local** asignada en cuatro sentencias, y el
sintetizador no evalúa asignaciones locales. Con `ALIGN` resuelto seguiría
falta propagar `total_size`. Son **dos** capacidades, no una:

```text
ALIGN resoluble                      -> falta propagar `total_size`
total_size propagable                -> NO SE: no se cual es el siguiente
```

Es decir: la segunda capacidad **no la he identificado**, solo la he separado de
la primera. Se que hay un escalon mas; no se cual es, y decirlo asi es lo unico
honesto.

Lo que `ALIGN` resolvería es un **hueco de 4 dwords** entre las dos cargas de
shader, que es visible (`ptr[0..65]` y `ptr[4..45]`) y cuya explicación necesita
la aritmética.

**No he comprobado si hay más macros internas sin resolver.** He comprobado
`ALIGN`, que es la que bloquea lo que tenía delante. Que sea **la única** sería
una afirmación que no puedo sostener, y no la hago: es `NOT_DETERMINED`.

**Y nada de esto es evidencia de hardware.** `RUNTIME=NOT_RUN`. Todo lo medido
aquí es sobre ficheros.

## 5 · UNA CORRECCIÓN MÍA, DE MEDIO PÁRRAFO

Escribí antes, en este mismo documento y en la conversación, que
`working/` *"no contiene `include/` en absoluto"*.

**Es falso.** El directorio existe. Contiene **1 fichero** bajo `include/linux/`.
`os.path.isdir` devuelve verdadero y por eso la medida salió
`working_sin_include=1`, y la frase estaba mal: no es 0,
es 1 de 16322.

Lo he cambiado en la medida para que sea un **recuento** y no un booleano:

```text
antes   working_sin_include=1 angulo=angulo=0 comillas=1
ahora   working_include=1 de upstream_include=16322 angulo=angulo=0 comillas=1
```

El booleano era peor por dos razones: mentía, y además `1` se lee como "hay
include/" cuando lo que dice es "hay un fichero". **Un booleano que vale 1 para
dos situaciones distintas es peor que no medir**, porque el que lo lee no puede
saber cuál de las dos es.

Y un bug mío de python en el camino: `_contar` ya existía en `verif.py` con
otra firma y devolvía un dict, así que mi contador de ficheros lo reventaba con
`TypeError: %d format: a real number is required, not dict`. Renombrado a
`_n_ficheros`, con el motivo escrito en el docstring, porque volver a pasar por
el mismo tropiezo en la siguiente iteración es más probable que no.

## 6 · PROCEDIMIENTO

```text
medicion    working/ vs kernelbuild/, 2787 ficheros comunes, sha256
            2783 identicos, 4 distintos, 0 solo-en-working
            include/: 1 vs 16322
            INC_RE medido sobre el patron real de pm4_emit

puerta      46 -> 48 medidas declaradas, 51 en total, SIN DERIVA
            corpus.ficheros_modificados perturbada   rc=1
            corpus.trabaja_sin_include perturbada     rc=1
            restauradas                                rc=0

otros       layoutcross 79 vectores rc=0
            ibref        65 vectores rc=0
            mmio         48 vectores rc=0
escrituras  0 ficheros de otros agentes
```

## 7 · LO QUE ESTE HALLAZGO VALE

Un hallazgo que no añade capacidad y sin embargo cambia lo que significan todas
las medidas del proyecto.

Hasta ahora, "las 35 medidas no han cambiado" significaba "nadie ha escrito en el
árbol". Con `corpus.ficheros_modificados`, significa algo más fuerte y más
verificable:

```text
de los 2787 ficheros del kernel que estas herramientas leen,
2783 son el upstream byte a byte,
4 estan editados, y estan nombrados.
```

Una afirmación sobre el sujeto, y el sujeto de una puerta de deriva **es**
precisamente lo que hay que sostener.
# 1135 — La transformada de MMIO tiene **escala dependiente de la generación**: RADEON/SI usa `reg = base + (payload << 2)`, GFX8 usa `reg = base + payload`. El mismo payload da un registro **distinto**, y ambos están en rango

```text
AGENCIA=RX550-INVESTIGACION · WORK_CLASS=SEMANTIC-CLOSURE + DEREFUTATION
AUTOR=AGENTE-INSTR
WRITE_EXECUTION=NONE · MODIFICATIONS=0 · RUNTIME=NOT_RUN
ESCRITOS_POR_ESTA_ITERACION   tools/mmio.py            (escala y alcance)
                              tools/verif.py           (1 medida, 42 -> 43)
                              08-ARQUITECTURA/artifacts/R11-MMIO/escala.txt
MODIFICADO_NADA_EXISTENTE    pm4_codec.py, pm4_emit.py INTACTOS
CLASSIFICATION=MEASUREMENT · SEMANTIC-CLOSURE · REFUTATION
GENERADO=2026-10-04 · MEDIDO=EN ESTA HOST
ESTADO=ALCANCE HECHO EXPLICITO Y PUESTO BAJO LA PUERTA
```

## 0 · El resultado, primero

```text
PREGUNTA ABIERTA (1134 §9)   ¿SET_SH_REG_OFFSET comparte base con SET_SH_REG?
RESPUESTA                   no es decidible desde este arbol, y por que (ver §1)

HALLAZGO NUEVO              la ESCALA de la transformada depende de la generacion:

  RADEON/SI    radeon/si.c:4602   start_reg = (idx_value << 2) + BASE
  amdgpu/GFX8  gfx_v8_0.c:6121    payload  = mmX - BASE

  con el MISMO registro (mmGDS_COMPUTE_MAX_WAVE_ID = 0x3348, base 0x2000):

     payload 0x04D2 -> GFX8 0x24D2 (mal)      forma RADEON 0x3348 (bien)
     payload 0x1348 -> GFX8 0x3348 (bien)     forma RADEON 0x6D20 (mal)

CONSECUENCIA   las dos direcciones equivocadas ESTAN EN RANGO. Un decodificador
               que usara la escala de otra generacion no daria ningun aviso:
               daria un nombre de registro plausible y equivocado.

ACCION         la escala pasa a ser parte DECLARADA de la ventana, con su
               alcance (GFX8) y con la escala de la otra generacion escrita
               al lado. 31 vectores (23 -> 31). Puerta 42 -> 43.
```

## 1 · `SET_SH_REG_OFFSET`: LA PREGUNTA NO ES DECIDIBLE AQUÍ, Y POR QUÉ

Busqué en todo el árbol, y el resultado tiene dos mitades que hay que separate
para no concluir de más.

```text
definiciones .h   27 ficheros, TODOS con el mismo valor: 0x77
                   (vid.h, sid.h, soc15d.h, nvd.h, cikd.h, gfx_v12_1_pkt.h, ...)
                   identicos al byte en las 4 versiones del kernel del arbol

usos NO-#define   1 solo fichero .c, y NO es de amdgpu:
                   RESEARCH/.../drivers/gpu/drm/radeon/si.c:4559 y :4662
                   son DOS etiquetas de `case`, en `si_vm_packet3_gfx_check()`
```

Y lo que hace ese `case` es no hacer nada:

```c
case PACKET3_SET_SH_REG:
case PACKET3_SET_SH_REG_OFFSET:
case PACKET3_INCREMENT_DE_COUNTER:
        break;
```

Cuatro opcodes en el mismo bloque que solo hace `break`. Es una lista de
"estos son seguros de saltar".

```text
ALCANCE DE LA BUSQUEDA   *.c y *.h de todo el arbol, por coincidencia de
                         identificador.  27 cabeceras, 1 fuente.
ESTADO                   PROVEN_ABSENT como PAQUETE EMITIDO en este arbol.
CONCLUSION               NO hay ninguna emision de la que deducir su base.
```

Y esa última frase es la que importa: **la pregunta de `1134 §9` no tiene
respuesta aquí, y no la voy a inventar.** `PACKET3_SET_SH_REG_OFFSET` no se
emite, luego nada muestra cómo se codifica su payload. Podría compartir la base
de `SET_SH_REG`, tener la suya, o no ser de ventana. Las tres son compatibles con
lo medido.

No lo he incluido en `mmio.py` por eso, y la razón queda escrita en el
instrumento en vez de en un comentario mío.

## 2 · LO QUE SALIÓ BUSCANDO ESO, Y QUE SÍ ES NUEVO

Buscar la codificacion de `SET_SH_REG_OFFSET` me llevó a su **único** uso, y ese
uso estaba en un fichero que no había mirado: el driver **RADEON**, no amdgpu.

`si_vm_packet3_gfx_check()` no es un layout. Es la **validación de paquetes del
VM**, y contiene algo que ninguna herramienta del proyecto tenía: **qué dword
del payload es una dirección de registro y bajo qué condición**.

```text
51 opcodes con case propio, de los cuales 5 validan registros:

  PACKET3_WRITE_DATA        idx+1     si (idx_value & 0xf00) == 0
                                       y si NO es (idx_value & 0x10000)
  PACKET3_COPY_DATA         idx+3     si (idx_value & 0xf00) == 0
  PACKET3_COND_WRITE        idx+5     si (idx_value & 0x100)
  PACKET3_COPY_DW           idx+3     si (idx_value & 0x2)
  PACKET3_SET_CONFIG_REG    idx+1..   start_reg ventana, bucle i < pkt->count
```

Y en ese mismo `case` de `SET_CONFIG_REG`, la línea que decide todo:

```c
/* radeon/si.c:4601-4602 */
case PACKET3_SET_CONFIG_REG:
        start_reg = (idx_value << 2) + PACKET3_SET_CONFIG_REG_START;
        end_reg   = 4 * pkt->count + start_reg - 4;
        if ((start_reg < PACKET3_SET_CONFIG_REG_START) ||
            (start_reg >= PACKET3_SET_CONFIG_REG_END) ||
            (end_reg  >= PACKET3_SET_CONFIG_REG_END))
                return -EINVAL;
```

`<< 2`. **RADEON/SI codifica la dirección desplazada 2 bits.**

Y el de amdgpu, en el otro lado del árbol:

```c
/* amdgpu/gfx_v8_0.c:6121 */
amdgpu_ring_write(ring, mmGDS_COMPUTE_MAX_WAVE_ID - PACKET3_SET_CONFIG_REG_START);
```

Sin desplazamiento.

## 3 · LA CUANTIFICACIÓN, CON EL MISMO REGISTRO

Las dos formas, aplicadas al mismo registro, con la misma base:

```text
base = 0x2000        registro = mmGDS_COMPUTE_MAX_WAVE_ID = 0x3348

  payload que escribe RADEON  = (0x3348 - 0x2000) >> 2 = 0x04D2
  payload que escribe GFX8    =  0x3348 - 0x2000       = 0x1348
```

Y lo que pasa si se decodifica un payload con la forma que no le toca:

```text
  payload 0x04D2   forma GFX8    -> 0x24D2     <-- registro equivocado, EN RANGO
                   forma RADEON  -> 0x3348     <-- mmGDS_COMPUTE_MAX_WAVE_ID

  payload 0x1348   forma GFX8    -> 0x3348     <-- mmGDS_COMPUTE_MAX_WAVE_ID
                   forma RADEON  -> 0x6D20     <-- registro equivocado, EN RANGO
```

**Las dos direcciones equivocadas caen dentro de la ventana.** No hay forma de
detectarlo mirando el rango. Un decodificador que mezclara generaciones daría
un `mm*` plausible, `UNICO`, y sería falso.

Eso es lo que convierte la escala de un detalle de implementación en algo que
hay que **declarar**: sin alcance declarado, un instrumento correcto en GFX8 es
un instrumento silenciosamente incorrecto en SI, y viceversa.

## 4 · LO QUE HACE EL INSTRUMENTO AHORA

```text
ALCANCE               GFX8 (vid.h)
ESCALA                reg = base + (payload << 0)
origen de la escala   medido en el propio arbol. GFX8: gfx_v8_0.c:1530,
                      gfx_v8_0.c:1536 y gfx_v8_0.c:6121 escriben
                      `reg - PACKET3_..._START`, sin desplazamiento.
                      RADEON/SI: radeon/si.c:4602 escribe
                      `(idx_value << 2) + PACKET3_SET_CONFIG_REG_START`
OTRA generacion       drivers/gpu/drm/radeon/si.c:4602 -> escala 2
                      usarla aqui daria un registro DISTINTO
```

Y la escala sale **también en cada fila**, no solo en la cabecera:

```json
{"dword": 1, "offset": "0x00001348", "absoluto": "0x3348",
 "escala": 0, "alcance": "GFX8 (vid.h)",
 "nombres": ["mmGDS_COMPUTE_MAX_WAVE_ID"], "veredicto": "UNICO"}
```

Cuatro vectores fijan la escala, y el que la demuestra es este:

```text
escala: el MISMO payload con la escala de RADEON da otro registro
       0x3348 (GFX8)  !=  0x6D20 (RADEON)   sobre el payload 0x1348
```

Sin ese vector, `escala = 0` podría ser un `0` escrito por descuido en lugar de
una decisión medida. Es el mismo motivo por el que `1131 §3` exige control
positivo para todo veredicto nuevo: **una rama que no tiene un caso donde falle
no sabe si funciona**.

### 4a · Un detalle de método que salió de escribir la cita

La primera versión de `ORIGEN_ESCALA` citaba las líneas como
`"gfx_v8_0.c:1530/1536/6121"`. El vector que comprobaba la cita buscaba
`"gfx_v8_0.c:6121"`, y no la encontraba — porque la cita compacta no contiene
esa subcadena.

```text
"gfx_v8_0.c:1530/1536/6121"  contiene  "gfx_v8_0.c:1530"   -> si
                            NO contiene "gfx_v8_0.c:6121"  -> no
```

Una cita que no se puede comprobar con una operación de búsqueda es una cita
que se queda sin verificar. Se reescribió citando las líneas una a una. Es
pequeño y es exactamente el tipo de detalle que hace que una evidencia parezca
más firme de lo que es.

## 5 · LO QUE ESTO NO RESUELVE, Y SE DICE

**El oráculo de rangos no se ha aprovechado.** `si_vm_reg_valid` (si.c:4391) da
los rangos de registro admitidos, y es la primera vez que en este árbol
aparece algo así:

```c
/* context regs are fine */
if (reg >= 0x28000)          return true;
/* shader regs are also fine */
if (reg >= 0xB000 && reg < 0xC000)   return true;
/* el resto: un switch de ~60 registros de config explícitos */
```

Es un oráculo **de GFX6/7**, y sus rangos no son los de GFX8: `[0xB000,0xC000)`
frente a mi ventana `SET_UCONFIG_REG_START = 0xC000`. No lo he usado, y no
debería: aplicarlo a GFX8 sería exactamente el error de §3.

Lo que sí queda es el **alcance del oráculo**, que es un dato y no una
especulación: `si_vm_reg_valid` existe para SI y **no se ha encontrado
equivalente en amdgpu**:

```text
ALCANCE DE LA BUSQUEDA   drivers/gpu/drm/amd/amdgpu/*.c
                         busqueda de `case PACKET3_`
ESTADO                   NOT_FOUND
```

Y `NOT_FOUND` **no** es `PROVEN_ABSENT`. En GFX8 la validación por opcode la
hace el PSP o no la hace nadie en el driver; no lo he determinado. Lo que sí
puedo afirmar es lo medido: en este amdgpu no hay un `switch` por opcode de
paquete.

**`MULTIPLE` sigue sin verse en ejecución.** Sin cambios respecto a `1134`.

**No he tocado `mmio.py` para RADEON/SI.** Sería un segundo alcance con otro
`vid.h` distinto, y es trabajo de otro día. Lo que he hecho es declarar el
alcance, que es lo que evita el error.

## 6 · PROCEDIMIENTO

```text
alcance de la busqueda SET_SH_REG_OFFSET
    *.c y *.h de todo el arbol           27 cabeceras, 1 fuente, 0 emisiones
    uso no-#define                       radeon/si.c:4559, :4662 (labels de case)

medicion de si_vm_packet3_gfx_check
    opcodes con case propio              51
    de los que validan registro          5
    transformada del payload             ib[idx+N] * 4  y  (idx_value << 2) + BASE

vectors    mmio 23 -> 31, rc=0
puerta     42 -> 43 medidas, SIN DERIVA
           mmio.escala = "GFX8 (vid.h) escala=0 otra_generacion_escala=2"
           perturbada a escala=2          rc=1
           restaurada                     rc=0

artefactos 08-ARQUITECTURA/artifacts/R11-MMIO/escala.txt
otros      layoutcross 79 vectores rc=0
           ibref        39 vectores rc=0
escrituras 0 ficheros de otros agentes
```

## 6b · SIETE ERRORES DE `doclint` EN ESTE DOCUMENTO, Y POR QUÉ SON FALSOS

`doclint` marca **10 errores** en este hallazgo. Los diez son falsos, todos
del mismo tipo, y el motivo es medible, así que va aquí en vez de callarse:

```text
todos   "cita <algo>si.c:<N> fuera de rango (el fichero tiene 2749 lineas)"
ninguno "el fichero no esta en el corpus"
```

Los 17 son la misma cita repetida, contada una vez por cada aparición textual
en el documento. La lista completa no aporta nada más que el patrón, así que no
se transcribe entera.

La cita es correcta. `RESEARCH/kernelbuild/linux-7.1.3/drivers/gpu/drm/radeon/si.c`
tiene 7548 líneas y ahí está el código citado. Lo que hace `doclint` es otra cosa:

```text
CORPUS_ROOTS   incluye RESEARCH/working/linux-7.1.3
               NO incluye  RESEARCH/kernelbuild

RESEARCH/working/linux-7.1.3/drivers/gpu/drm/   contiene SOLO `amd`
                                                  (no existe `radeon` ahi)

el unico radeon/si.c del arbol   esta en kernelbuild, FUERA del indice
el unico si.c que doclint tiene  amdgpu/si.c, 2748 lineas, fichero DISTINTO
```

`resolve()` de `doclint` reduce el nombre a `basename` y decide la ambiguedad
sobre el **indice**, no sobre el arbol. Con indice parcial, `si.c` tiene un
unico candidato y el suyo, que es el equivocado. Y la comprobacion de rango lo
confirma con seguridad: dice "2749 lineas" de un fichero que no es el citado.

> **No hay forma de citar esto sin que suene.** `resolve()` usa `os.path.basename`,
> asi que `si.c:4602`, `radeon/si.c:4602` y
> `RESEARCH/kernelbuild/linux-7.1.3/drivers/gpu/drm/radeon/si.c:4602` reducen
> todos a `si.c` y dan el mismo error. **El autor del documento no puede evitarlo
> ni silenciarlo desde el documento.** Eso es lo que hace que sea un defecto y no
> una molestia: una clase de error que no se puede esquivar se repite en cada
> hallazgo que cite ese fichero.

Discriminante medido del arreglo, con un basename **único** fuera del indice.
Se escribió un documento de prueba que cita `r600_dpm.c` linea 1234 —fichero real,
1368 líneas, en `kernelbuild`, fuera del índice— y se pasó a `doclint`:

```text
documentos: 1   errores: 0   avisos: 2
aviso: "cita a r600_dpm.c:1234, no se resuelve: el nombre esta abreviado
        o el fichero no esta en el corpus"
```

Un basename **único** da **aviso**, que es lo correcto. El **ambiguo** da
**error**. La única diferencia entre los dos casos es si hay más de un
candidato en el índice.

La prueba está en `/tmp/opencode/probe.md` y **no se cita aquí dentro de un
bloque**, a propósito: una cita escrita dentro del documento es una cita real
para `doclint` —comprueba también las que están en bloques cercados— y metía
un aviso extra en este mismo hallazgo la primera vez que lo intenté.

El defecto y el contrato de reparacion estan en `1136`. No toco
`08-ARQUITECTURA/tools/doclint.py`: es de otra sesion.

## 7 · LO QUE NO PRUEBA

**No prueba que la escala de RADEON/SI sea 2 y la de GFX8 0 en el hardware.**
Las dos están medidas en el **código del driver**: el kernel escribe una cosa y
la otra. Que el hardware las interprete así no lo he verificado, y `RUNTIME=NOT_RUN`.

**No prueba que las dos formas sean la misma operación con distinto factor.**
Puede que en GFX6/7 el campo `SET_CONFIG_REG` tenga una granularidad de 4 bytes y
en GFX8 de 1, que es como lo escribe el driver; pero que sea *la misma*
granularidad escalada o dos codificaciones distintas, no lo he determinado.

**No generaliza a más generaciones.** He mirado SI y GFX8. `soc15d.h` y
`gfx_v12_1_pkt.h` tienen las mismas ventanas y **proablemente** la misma escala,
porque no he visto ningún `<<` junto a `PACKET3_SET_*_START` en amdgpu — pero
"probablemente" es `NOT_DETERMINED`, y lo dejo así.

**Y no cierra `1134 §9`.** `SET_SH_REG_OFFSET` sigue sin base declarada, porque
no hay nada en el árbol de donde sacarla. Para cerrarla harían falta el documento
de hardware, un ASIC que lo exercise, o un experimento. Las tres son rutas
distintas y ninguna es un fichero.
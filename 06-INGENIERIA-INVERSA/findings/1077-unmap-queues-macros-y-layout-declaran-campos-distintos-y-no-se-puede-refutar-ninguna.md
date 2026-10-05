# 1077 — Los macros de campo de `UNMAP_QUEUES` y la layout que declara `pm4_codec` discrepan en 4 campos, y **ninguna de las dos se puede refutar con lo que hay en el árbol**

```text
AGENCIA=RX550-INVESTIGACION · WORK_CLASS=AGENT-SIDE-PM4LAYOUT
WRITE_EXECUTION=NONE · MODIFICATIONS=0 · RUNTIME=NOT_RUN
ESCRITOS_POR_ESTA_ITERACION   tools/layoutcross.py (nuevo, tabla ASIGNACION)
MODIFICADO_NADA_EXISTENTE    pm4_codec.py, pm4decode.c, pm4_emit.py y
                          doclint.py quedan intactos; los defectos se
                          REPORTAN, no se reparan (ver §No reparado)
AUTOR=AGENTE-INSTR
CLASSIFICATION=CONTRADICTION · TRACK=STATIC
GENERADO=2026-10-04 · MEDIDO=EN ESTA HOST
AFECTADO=las dos fuentes en conflicto:
         A) .../amdgpu/vid.h:399-406, soc15d.h, gfx_v12_1_pkt.h, nvd.h (macros)
         B) 08-ARQUITECTURA/tools/pm4_codec.py:85-91 (DOC_LAYOUTS)
         emision: .../amdgpu/gfx_v8_0.c:4773-4781
ALCANCE=4 campos de 1 paquete · 2 de las 5 cabeceras PM4 del corpus
ESTADO=CONTRADICCION ABIERTA · NO_DETERMINED cual de las dos fuentes falla
herramienta  tools/layoutcross.py, veredicto CONTRADICCION
```

## 0 · ACTUALIZACIÓN 2026-10-04: `1094` RESUELVE 3 DE LAS 4

Este hallazgo queda **parcialmente resuelto**. El segundo oráculo no era el
documento de hardware: era **el valor que el driver escribe**, y se puede leer
sin placa.

```
RESUELTO por incompatibilidad de rango   ACTION     -> el enum llega a 3 y el
                                               campo declarado tiene 1 bit
RESUELTO por ejercitacion inevitable     NUM_QUEUES -> se escribe 1 en los 7
                                               sitios; si estuviera en el bit
                                               10 el unmap seria un no-op
RESUELTO por ejercitacion cruzada        ENGINE_SEL -> GFX8 lo escribe 0, pero
                                               GFX9+ lo escribe con valor y los
                                               4 headers coinciden byte a byte
ABIERTA, e IRRESOLUBLE POR EJECUCION     QUEUE_SEL  -> literal 0 en los 7
                                               sitios del corpus. El driver no
                                               puede distinguir la posicion
                                               correcta de la incorrecta, asi
                                               que ninguna ejecucion suya puede
                                               hacerlo tampoco.
```

Degradacion de severidad que esto produce: **mientras `QUEUE_SEL` se escriba a 0,
la discrepancia no es un fallo funcional**, es una afirmacion falsa en un
fichero de referencia. Menos grave que un bug latente, mas grave que una errata.

Y del lado de `pm4_codec` sale un defecto nuevo y peor: con un IB de referencia
(`1094`), su layout decodifica **3 de los 4 campos** de `UNMAP_QUEUES` con el
valor equivocado, sobre el dword `0x20000001` que el driver escribe. Eso ya no
es «dos fuentes en disputa» sino «una fuente se sabe equivocada y la
herramienta no puede saberlo».

## 0bis · El resultado, primero

| campo | A) macros del kernel | B) `pm4_codec` | ¿acuerdan? |
|---|---|---|---|
| `ACTION` | `<<0` | `[1:1]` | **no** |
| `QUEUE_SEL` | `<<4` | `[2:0]` | **no** |
| `ENGINE_SEL` | `<<26` | `[6:5]` | **no** |
| `NUM_QUEUES` | `<<29` | `[10:10]` | **no** |
| `DOORBELL_OFFSET0` | `<<2` | `[25:2]` | sí |

Las dos fuentes coinciden en un campo de cinco y discrepan en cuatro. **Ninguna de
las dos se puede refutar con la evidencia del proyecto.** Esto no es un defecto
reportado: es una contradicción abierta y `NOT_DETERMINED`.

## 1 · LAS DOS FUENTES, LITERALES

**A) `vid.h:399-406`** (y las otras tres cabeceras coinciden campo por campo):

```c
/* 1. header
 * 2. CONTROL
 * 3. CONTROL2
 * 4. CONTROL3
 * 5. CONTROL4
 * 6. CONTROL5
 */
#              define PACKET3_UNMAP_QUEUES_ACTION(x)          ((x) << 0)
#              define PACKET3_UNMAP_QUEUES_QUEUE_SEL(x)       ((x) << 4)
#              define PACKET3_UNMAP_QUEUES_DOORBELL_OFFSET0(x) ((x) << 2)
#              define PACKET3_UNMAP_QUEUES_ENGINE_SEL(x)      ((x) << 26)
#              define PACKET3_UNMAP_QUEUES_NUM_QUEUES(x)      ((x) << 29)
```

**B) `pm4_codec.py:85-91`:**

```python
"PACKET3_UNMAP_QUEUES": [
    "ACTION[1] | QUEUE_SEL[2:0] | ENGINE_SEL[6:5] | NUM_QUEUES[10] "
    "| DOORBELL_OFFSET0[25:2]",
    "dword[2]", "dword[3]", "dword[4]",
],
```

## 2 · POR QUÉ NO SE RESUELVE, Y POR QUÉ IMPORTA

### La pista que hace sospechar de A

Las posiciones de A son **exactamente** las de `MAP_QUEUES`:

| campo | `MAP_QUEUES` (A) | `UNMAP_QUEUES` (A) |
|---|---|---|
| queue_sel | `<<4` | `<<4` |
| doorbell_offset | `<<2` | `<<2` |
| engine_sel | `<<26` | `<<26` |
| num_queues | `<<29` | `<<29` |

Cinco de cinco. Un `cpypaste` del bloque de macros de `MAP_QUEUES` al de
`UNMAP_QUEUES` explicaría la coincidencia exacta. Es una hipótesis con
mecanismo, no una conjetura: los dos paquetes son distintos y el de A los trata
como si tuvieran el mismo `CONTROL`.

### La pista que hace sospechar de B

`ACTION(1) | QUEUE_SEL(0) | ENGINE_SEL(0) | NUM_QUEUES(1)` cabe en un dword con
**cualquier** de las dos distribuciones. Los números de B (`[2:0]`, `[6:5]`,
`[10]`, `[1]`) son compactos y contiguos desde el bit 0; los de A tienen huecos
grandes. Si `UNMAP_QUEUES` compartiera `CONTROL` con `MAP_QUEUES`, los huecos de
A serían correctos; si fuera un `CONTROL` propio y compacto, los de B serían
correctos. **Las dos lecturas son internamente coherentes.**

### Lo que la emisión NO puede discriminar — y por qué lo intenté

`gfx_v8_0.c:4773-4781`:

```c
amdgpu_ring_write(kiq_ring, PACKET3(PACKET3_UNMAP_QUEUES, 4));
amdgpu_ring_write(kiq_ring, /* Q_sel: 0, vmid: 0, engine: 0, num_Q: 1 */
				PACKET3_UNMAP_QUEUES_ACTION(1) | /* RESET_QUEUES */
				PACKET3_UNMAP_QUEUES_QUEUE_SEL(0) |
				PACKET3_UNMAP_QUEUES_ENGINE_SEL(0) |
				PACKET3_UNMAP_QUEUES_NUM_QUEUES(1));
amdgpu_ring_write(kiq_ring, PACKET3_UNMAP_QUEUES_DOORBELL_OFFSET0(ring->doorbell_index));
amdgpu_ring_write(kiq_ring, 0);
amdgpu_ring_write(kiq_ring, 0);
amdgpu_ring_write(kiq_ring, 0);
```

El kernel escribe **usando los macros de A**, así que su salida es correcta bajo
ambas hipótesis: si el macro está mal, el hardware recibe el campo desplazado y
el driver sigue funcionando porque los valores que pasa son 0 y 1 casi todos.

**Es el mismo caso de `SET_RESOURCES` resuelto en `1073`, pero aquí al revés:**
allí los comentarios de emisión nombraban los campos y cerraban la contradicción;
aquí nombran los campos **usando la notación de A**, así que no añaden nada.

### El único valor no trivial

`DOORBELL_OFFSET0(ring->doorbell_index)` con `<<2` en A y `[25:2]` en B: **ambas
dicen lo mismo** y es el único campo donde coinciden. Confirma que el LSB está
bien en las dos, y por tanto que la discrepancia es de **anchura y posición de
los otros cuatro**, no de un desplazamiento global. Eso es un dato, no una
decisión.

## 3 · ESTADO DE LA CONTRADICCIÓN

```
PROVEN           4 de 5 campos discrepan entre la layout declarada y los macros
PROVEN           los macros de UNMAP_QUEUES tienen las mismas posiciones que los
                de MAP_QUEUES, 5 de 5
PROVEN           la emision del kernel usa los macros, luego no discrimina
NOT_DETERMINED   cual de las dos fuentes describe el hardware
NOT_DETERMINED   si el bloque de macros de UNMAP_QUEUES es un cpypaste de MAP_QUEUES
```

### El discriminante que falta, nombrado

Uno solo, y no está en el árbol:

```
DISCRIMINANTE   el documento de hardware de PM4 para UNMAP_QUEUES, que declara
                los rangos de los subcampos de CONTROL en GFX8
DONDE ESTA      ninguna cabecera del corpus lo contiene: los 4 headers repiten
                la misma tabla de posiciones y el comentario numerado solo dice
                "CONTROL"
COSTE           bajo, y NO requiere la GPU: es lectura
```

Alternativa de segundo orden, si aparece un IB real: **`UNMAP_QUEUES` con
`QUEUE_SEL != 0` en un anillo real**. Con A, un `queue_sel` de 3 se escribiría
en el bit 4; con B, en los bits 0-2. Un valor distinto de cero separa las dos
hipótesis de un solo paquete. Es un experimento que **no requiere tocar la GPU**
si se captura el IB que el driver ya emite en `gfx_v8_0_deactivate_hqd`.

## 4 · POR QUÉ EL INSTRUMENTO NO LA DECLARA DEFECTO

La primera versión de `tools/layoutcross.py` emitía `DISCREPA` para los 6 casos
en que el macro discrepa de la herramienta, y produjo **6 cargos que no podía
defender**: 2 de ellos (`SET_RESOURCES`, hallazgo `1073`) resultaron ser defectos
reales, y estos 4 no se pueden resolver. Ahora hay dos clases distintas:

```
DISCREPA       el comentario numerado del kernel DECLARA el rango de ese campo y
               difiere. Dos afirmaciones explícitas que no pueden coexistir.
               -> self-contained en una sola cabecera.
CONTRADICCION  el macro dice una cosa y la herramienta otra, pero el comentario
               no declara el rango. No se sabe cual de las dos falla.
               -> hace falta una segunda fuente, y no la hay.
```

La regla que separa una de otra es la disponibilidad del rango en el comentario,
que es un dato comprobable, no una intuición. `UNMAP_QUEUES` no declara rangos en
su comentario (`CONTROL`, `CONTROL2`…`CONTROL5`), luego es `CONTRADICCION`.
`SET_RESOURCES` tampoco los declara para `queue_type`, luego su
`queue_type[15:14]` salió `CONTRADICCION` — y `1073` lo resolvió a mano con una
tercera fuente, la emisión. **La máquina no resolvió lo que la máquina no puede
resolver.**

## 5 · LO QUE ESTO DICE DEL INSTRUMENTO, Y ES LO MÁS IMPORTANTE

Esta contradicción no la ha producido el kernel ni `pm4_codec`: **la ha producido
el instrumento, que en su primera versión PASSABA este hallazgo por defecto con
el mismo gesto con que pasaba `SET_RESOURCES`.** Con 6 `DISCREPA` sobre 43
afirmaciones, la tasa de falsos positivos era de 4 de 6.

Un instrumento que fabrica cargos sin pruebas es peor que ninguno, porque entrena
al lector a ignorar la alarma. Las tres correcciones que la-”desactivaron”:

1. **No colapsar las cabeceras.** Guardar el valor por cabecera. Los macros de
   `MAP_QUEUES` cambian de posición entre GFX8 y GFX9+ (`queue` = `<<26` en
   `vid.h`, `<<13` en `soc15d.h`), así que "la última gana" produce un valor único
   y creíble que no existe. Es el mismo error que `NOT_FOUND`, con distinta
   forma.
2. **Distinguir `_tokens` de `_nombres`.** `_tokens` exige guion bajo y es
   invisible para `COMMAND` o `CONTROL`, que son nombres de campo legítimos del
   kernel. Con una sola función el kernel parecía no nombrar `COMMAND` cuando lo
   nombra en `6. COMMAND [30:21]`. Para comparar contenido interesa la
   precisión; para preguntar por pertenencia, la cobertura.
3. **`_desglosa` por anchura parcial, no por nombre.** `MAP_QUEUES` documenta
   `MQD_ADDR_LO [31:0]`, que es una ranura de dword entero y no un campo; un test
   por nombre deía que desglosaba porque `ADDR_LO` tiene guion bajo. El criterio
   correcto es si se declara algún rango que no sea `[31:0]`.

**Resultado tras las tres:** 43 afirmaciones → 27 `OK`, 8
`NOMBRES_NO_COMPARABLES`, 1 `SIN_ORACULO_BITS`, 1 `CAMPO_INVENTADO` (el verdadero)
y 6 `CONTRADICCION`, de las que **4 siguen abiertas por falta de oráculo**.

## 6 · LO QUE NO ESTÁ HECHO, Y POR QUÉ

- **No he reparado `pm4_codec.py`.** No se sabe cuál de las dos fuentes falla.
  Reparar sin discriminante es elegir al azar, y escribirlo como afirmación sería
  fabricar un hecho.
- **No he arreglado los macros del kernel.** Son de otra sesión y además no está
  demostrado que estén mal.
- **No he buscado el discriminante fuera del árbol.** §1 limita el alcance al
  proyecto; un documento de hardware externo sería una fuente nueva, y citarla sin
  haberla abierto sería exactamente el fallo que este hallazgo denuncia.
- **No he tocado la GPU.** El experimento de §3 no la requiere, pero necesita un
  IB capturado, y hoy **no hay ningún IB decodificado en el proyecto**.

## 7 · PROCEDENCIA

```text
herramienta  tools/layoutcross.py, tabla ASIGNACION DE CAMPOS A DWORDS
             CAMPO_INVENTADO 1 · CONTRADICCION 6 · NOMBRES_NO_COMPARABLES 8
             OK 27 · SIN_ORACULO_BITS 1   (de 43 afirmaciones)
selftest     37 vectores, rc=0, hermetico (/tmp/opencode/herm6)
fuente A     vid.h:399-406 + soc15d.h + gfx_v12_1_pkt.h + nvd.h, las 4 coinciden
fuente B     pm4_codec.py:85-91
emision      gfx_v8_0.c:4773-4781, F=4 -> 5 payload, usa los macros de A
salida       08-ARQUITECTURA/artifacts/R7-LAYOUTCROSS/salida.txt
escrituras   0 ficheros de otros agentes
```

**Lo que este documento NO prueba.** No prueba que `pm4_codec` tenga razón ni que
los macros la tengan. No mide el hardware. No hay ninguna afirmación aquí que no
sea "las dos fuentes discrepan en estos cuatro campos, con estos números", y esa
es la única afirmación que la evidencia sostiene.
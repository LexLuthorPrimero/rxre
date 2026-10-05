# 1094 — Con el primer IB del proyecto, `1077` se reduce a **una** contradicción abierta y aparece un defecto peor: `pm4_codec` decodifica **3 de los 4 campos** de `UNMAP_QUEUES` con el valor equivocado, y los imprime como precisos

```text
AGENCIA=RX550-INVESTIGACION · WORK_CLASS=AGENT-SIDE-PM4LAYOUT
AUTOR=AGENTE-INSTR
WRITE_EXECUTION=NONE · MODIFICATIONS=0 · RUNTIME=NOT_RUN
ESCRITOS_POR_ESTA_ITERACION   08-ARQUITECTURA/artifacts/R8-IBREF/kcq_disable_unmap.ib.txt
MODIFICADO_NADA_EXISTENTE    pm4_codec.py y pm4_emit.py intactos
CLASSIFICATION=CONTRADICTION-RESOLVIDA+DEFECT · TRACK=STATIC
GENERADO=2026-10-04 · MEDIDO=EN ESTA HOST
AFECTADO=08-ARQUITECTURA/tools/pm4_codec.py:85-91 (DOC_LAYOUTS["PACKET3_UNMAP_QUEUES"])
RESUELVE   1077 (3 de 4 contradicciones) · ABRE 1 nueva (ACTION)
ESTADO=PROBADO sobre un dword OBSERVADO · el defecto NO esta reparado
```

## 0 · El resultado, primero

Con el IB de referencia de `1093`, el `CONTROL` de `UNMAP_QUEUES` que el driver
de GFX8 escribe es **`0x20000001`**. Decodificado con el layout que declara
`pm4_codec`:

```
   ACCION     [1:1     leido   0   esperado 1   MAL
   QUEUE_SEL  [2:0     leido   1   esperado 0   MAL
   ENGINE_SEL [6:5     leido   0   esperado 0   OK
   NUM_QUEUES [10:10   leido   0   esperado 1   MAL

   campos mal decodificados: 3 de 4
```

**Y nada de esto falla ni avisa.** El decodificador devuelve cuatro números
 plausibles y equivocados. El `1` que el driver pone en el bit 0 para decir
`ACTION=RESET_QUEUES` lo lee como `QUEUE_SEL=1`, y el `1` del bit 29 para decir
`NUM_QUEUES=1` no aparece en ningún campo declarado.

## 1 · EL DWORD, OBSERVADO Y NO DERIVADO

```
$ python3 tools/ibref.py --func gfx_v8_0_kcq_disable --set ring_doorbell_index=7

4773  0xC004A300  PACKET3(PACKET3_UNMAP_QUEUES, 4)
4774  0x20000001  /* Q_sel: 0, vmid: 0, engine: 0, num_Q: 1 */
                       PACKET3_UNMAP_QUEUES_ACTION(1) |     /* RESET_QUEUES */
                       PACKET3_UNMAP_QUEUES_QUEUE_SEL(0) |
                       PACKET3_UNMAP_QUEUES_ENGINE_SEL(0) |
                       PACKET3_UNMAP_QUEUES_NUM_QUEUES(1)
4779  0x0000001C  PACKET3_UNMAP_QUEUES_DOORBELL_OFFSET0(ring->doorbell_index)
6 dwords, 6 completos, rc=0
```

Artefacto: `08-ARQUITECTURA/artifacts/R8-IBREF/kcq_disable_unmap.ib.txt`.

**Descomposición con los macros que el propio driver usa** (`vid.h`):

```
0x20000001 = (1 << 0)    ACTION(1)      = 1  = RESET_QUEUES
           | (0 << 4)    QUEUE_SEL(0)   = 0
           | (0 << 26)   ENGINE_SEL(0)  = 0
           | (1 << 29)   NUM_QUEUES(1)  = 1
```

## 2 · `1077` SE RESUELVE EN TRES DE CUATRO

`1077` dejó cuatro campos en `CONTRADICCION` sin resolver por falta de un segundo
oráculo. El segundo oráculo era el propio comportamiento del driver, y se puede
leer sin placa: **un campo que el driver escribe con valor no trivial y cuyo
resultado el driver exige, no puede estar en la posición que lo haría inútil.**

### `ACTION` — la prueba es el enum, no el comportamiento

```c
// amdgpu_gfx.h:126
enum amdgpu_unmap_queues_action {
	PREEMPT_QUEUES = 0,
	RESET_QUEUES,          // 1
	DISABLE_PROCESS_QUEUES, // 2
	PREEMPT_QUEUES_NO_UNMAP, // 3
};
```

El campo transporta **0, 1, 2 y 3**: necesita **2 bits**. `pm4_codec` declara
`ACTION[1]`, **un solo bit**.

Y el valor 3 **se escribe en producción**:

```
gfx_v10_0.c:8877  kiq->pmf->kiq_unmap_queues(kiq_ring, ring, PREEMPT_QUEUES_NO_UNMAP, ...)
gfx_v11_0.c:6255  kiq->pmf->kiq_unmap_queues(kiq_ring, ring, PREEMPT_QUEUES_NO_UNMAP, ...)
gfx_v12_0.c:4646  kiq->pmf->kiq_unmap_queues(kiq_ring, ring, PREEMPT_QUEUES_NO_UNMAP, ...)
```

Un campo declarado de 1 bit **no puede representar el 3**. Con el layout de
`pm4_codec`, `ACTION(3)` escrito en `<<0` se leería como `ACTION = 1`
(`RESET_QUEUES`): una preempción donde el driver pidió desactivación de proceso.

> **La resolución es de `pm4_codec`, no del kernel**: el macro `ACTION <<0` es
> el correcto, y `pm4_codec` es el que no puede representar el valor que el
> driver escribe.

### `NUM_QUEUES` — la prueba es que se escribe en los 7 sitios

`PACKET3_UNMAP_QUEUES_NUM_QUEUES(1)` aparece en **los 7 sitios de emisión de las
6 generaciones**. Si la posición real fuera `[10]` —como dice `pm4_codec`— el
hardware leería **0 colas** en cada unmap, y el unmap sería un no-op en seis
generaciones de drivers que funcionan. **El macro es correcto.**

### `ENGINE_SEL` — resuelto por exercitación cruzada

En GFX8 el driver pasa `ENGINE_SEL(0)`: no se ejercita en la generación objetivo.
Pero GFX9+ pasa `ENGINE_SEL(eng_sel)` con valor no nulo, y los cuatro headers
(`vid.h`, `soc15d.h`, `gfx_v12_1_pkt.h`, `nvd.h`) **coinciden byte a byte** en
`ENGINE_SEL <<26`. Si la posición fuera `[6:5]`, el unmapping fallaría en GFX9+
también. **El macro es correcto.**

### `QUEUE_SEL` — LA CONTRADICCIÓN QUE QUEDA, Y ES IRRESOLUBLE POR EJECUCIÓN

```
gfx_v8_0.c:4777     PACKET3_UNMAP_QUEUES_QUEUE_SEL(0)
gfx_v9_0.c:993      PACKET3_UNMAP_QUEUES_QUEUE_SEL(0)
gfx_v9_4_3.c:242    PACKET3_UNMAP_QUEUES_QUEUE_SEL(0)
gfx_v10_0.c:3778    PACKET3_UNMAP_QUEUES_QUEUE_SEL(0)
gfx_v11_0.c:438     PACKET3_UNMAP_QUEUES_QUEUE_SEL(0)
gfx_v12_0.c:368     PACKET3_UNMAP_QUEUES_QUEUE_SEL(0)
gfx_v12_1.c:168     PACKET3_UNMAP_QUEUES_QUEUE_SEL(0)
```

**Los 7 sitios, en las 6 generaciones, con el literal `0`**, y el comentario del
propio driver lo dice: `/* Q_sel: 0, ... */`.

El valor de `QUEUE_SEL` es 0 en todos los casos, y el hardware lee 0
 sea cual sea la posición. **El driver no puede distinguir la posición correcta de la
incorrecta, y por eso tampoco puede hacerlo ninguna ejecución suya.**

```
PROVEN           QUEUE_SEL se escribe como literal 0 en los 7 sitios del corpus
PROVEN           el campo nunca se ejercita con valor no nulo
NOT_DETERMINED   cual es su posicion real
CONSECUENCIA     el defecto es de DOCUMENTACION, no funcional, para este driver
```

Esto **degrada la severidad** que `1077` le atribuía: mientras `QUEUE_SEL` se
escriba a 0, la discrepancia no produce un fallo funcional. Pasa a ser una
afirmación falsa en un fichero de referencia, que es menos grave que un bug
latente y más grave que un error tipográfico.

Los resolvers que quedan, y ninguno está en el árbol:

```
1  el documento de hardware de PM4 para UNMAP_QUEUES en GFX8
2  un ASIC o un driver que escriba QUEUE_SEL != 0
3  experimento de hardware: escribir 1<<4 y 1<<2 por separado y observar el unmap
```

## 3 · EL DEFECTO NUEVO, Y ES PEOR QUE LA CONTRADICCIÓN

`1077` decía «las dos fuentes discrepan en 4 campos». Eso, medido contra un dword
real, es **«3 de los 4 campos se decodifican con un valor equivocado, y el
decodificador no puede saberlo»**.

La diferencia es de categoría:

| | `1077` (abstracto) | este hallazgo (observado) |
|---|---|---|
| evidencia | dos textos que se contradicen | un dword que el driver escribe |
| resultado | «no sé cuál es el bueno» | «sé cuál es el bueno y el otro falla» |
| efecto | una afirmación dudosa | cuatro numeros plausibles y erroneos |

Y el modo de fallo es el que `pm4_codec` describe en su propio docstring, en el
caso que el docstring no menciona: **no es un nombre desplazado, es un nombre
con el valor equivocado**. `QUEUE_SEL = 1` no está desplazado un dword: está en
la posición correcta del layout equivocado, y por eso es indistinguible de una
medida buena.

## 4 · POR QUÉ `layoutcross` NO LO DETECTÓ, Y QUÉ ES LA LECIÓN

`layoutcross` clasificó los cuatro campos como `CONTRADICCION`, que es la
etiqueta correcta: los macros y la herramienta discrepan y ninguno de los dos
puede especificar el bueno. **Hizo lo que podía hacer con dos fuentes de texto.**

Lo que faltaba era **la tercera fuente: un valor**. Y esa fuente la produjo
`ibref`, no una regla mejor en `layoutcross`. La lección generalizable:

> **Una contradicción entre dos descripciones se resuelve con un dato, no con
> otra descripción.** Dos instrumentos que discrepan no se arbitran entre sí;
> se arbitran contra lo que el sujeto hace.

Y el orden de construcción importó: `layoutcross` funciona sin hardware y
detecta que hay disputa; `ibref` produce el dword; el dword dice quién tiene
razón. **Sin el primero no se sabía qué arbitrar, y sin el segundo arbitrar es
opinar.**

## 5 · LO QUE NO ESTÁ HECHO, Y POR QUÉ

**No he reparado `pm4_codec.py`.** Es de otra sesión. El contrato, para que no se
pierda:

```
REPARACION  DOC_LAYOUTS["PACKET3_UNMAP_QUEUES"][0] pasa a los campos que el
            driver escribe, con los rangos del kernel:
              action[1:0]      (el enum llega a 3: 2 bits, no 1)
              queue_sel[4:4]   (o el ancho que documente el hardware)
              engine_sel[28:26]
              num_queues[30:29]
TEST        con el IB de R8-IBREF/kcq_disable_unmap.ib.txt:
              dword 0x20000001 -> action=1, queue_sel=0, engine_sel=0,
                                   num_queues=1
            NEGATIVO: si el layout mantiene action[1], el test da action=0 y
            debe FALLAR. Un test que sigue verde con el layout erroneo no
            comprueba nada.
INVARIANTE  los otros 6 layouts no cambian
```

**No he ejecutado ese test.** Está escrito y es ejecutable —el IB existe— pero
no lo he corrido, así que no lo declaro validado.

**No he resuelto `QUEUE_SEL`.** Es irresoluble con lo que hay, y está declarado
como tal en vez de adivinar.

**No he tocado la GPU**, y las tres vías que quedan para `QUEUE_SEL` (documento,
otro driver, experimento) quedan fuera de mi alcance en esta iteración.

## 6 · PROCEDENCIA

```text
IB          tools/ibref.py --func gfx_v8_0_kcq_disable --set ring_doorbell_index=7
            6 dwords, 6 completos, rc=0
            artefacto: 08-ARQUITECTURA/artifacts/R8-IBREF/kcq_disable_unmap.ib.txt
dword        0x20000001 en la linea 4774, leido de la expresion del driver
contraste    A) macros que usa el driver (vid.h)   -> los 4 campos coinciden
            B) layout declarado por pm4_codec      -> 3 de 4 MAL
enum         amdgpu_gfx.h:126  PREEMPT_QUEUES=0 .. PREEMPT_QUEUES_NO_UNMAP=3
uso real     PREEMPT_QUEUES_NO_UNMAP pasado en gfx_v10_0.c:8877, gfx_v11_0.c:6255,
            gfx_v12_0.c:4646
QUEUE_SEL    literal 0 en los 7 sitios (gfx_v8_0:4777, gfx_v9_0:993, gfx_v9_4_3:242,
            gfx_v10_0:3778, gfx_v11_0:438, gfx_v12_0:368, gfx_v12_1:168)
escrituras   0 ficheros de otros agentes
```

**Lo que este documento NO prueba.** No prueba que el hardware prefiera la
posición del macro; prueba que la posición de `pm4_codec` **es incompatible con
valores que el driver escribe**, lo cual es un argumento contra ella y no a
favor de la otra por vía independiente. `QUEUE_SEL` queda
`NOT_DETERMINED` y su contradicción sigue abierta. Y el IB es una síntesis
estática: que coincida con lo que la GPU recibe es `NOT_DETERMINED` y requiere
placa.
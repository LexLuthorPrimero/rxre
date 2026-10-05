# 1096 — El segundo oráculo estaba **en el árbol**, en cuatro copias: `amdkfd/kfd_pm4_headers_vi.h` declara los bitfields de `UNMAP_QUEUES` con anchura incluida. `1077` queda cerrado y `1095` pierde su «anchura no determinable»

```text
AGENCIA=RX550-INVESTIGACION · WORK_CLASS=AGENT-SIDE-PM4FIELDS
AUTOR=AGENTE-INSTR
WRITE_EXECUTION=NONE · MODIFICATIONS=0 · RUNTIME=NOT_RUN
ESCRITOS_POR_ESTA_ITERACION   ninguno
MODIFICADO_NADA_EXISTENTE    pm4_codec.py y pm4_emit.py intactos
CLASSIFICATION=CONTRADICTION-RESOLVIDA · TRACK=STATIC
GENERADO=2026-10-04 · MEDIDO=EN ESTA HOST
AFECTADO=las preguntas abiertas de 1077 (QUEUE_SEL) y 1095 (anchuras)
FUENTE   RESEARCH/working/linux-7.1.3/drivers/gpu/drm/amd/amdkfd/kfd_pm4_headers_vi.h
         (4 copias en el arbol; amdkfd/ es hermano de amdgpu/ en el MISMO driver)
ALCANCE=1 paquete resuelto al 100% · 2 paquetes con alcance delimitado
ESTADO=PROBADO · 1095 queda REFUTADA en su premise central
```

## 0 · El resultado, primero

En `1077` dejé una contradicción abierta con este texto:

> Los resolvers que quedan, y ninguno está en el árbol: *el documento de hardware
> de PM4 para UNMAP_QUEUES en GFX8*.

**Era falso, y lo comprobé.** El documento estaba en el árbol desde el principio,
en cuatro copias, en el mismo directorio que `amdgpu/`:

```
RESEARCH/working/linux-7.1.3/drivers/gpu/drm/amd/amdkfd/kfd_pm4_headers_vi.h
RESEARCH/baseline/linux-7.1.3/drivers/gpu/drm/amd/amdkfd/kfd_pm4_headers_vi.h
RESEARCH/kernelbuild/linux-7.1.3/drivers/gpu/drm/amd/amdkfd/kfd_pm4_headers_vi.h
rx550-upstream-7.2.8/linux-7.2.8/drivers/gpu/drm/amd/amdkfd/kfd_pm4_headers_vi.h
```

No lo encontré yo por casualidad: **lo anuncié como ausente en un hallazgo
escrito el mismo día, y no fui a mirar el directorio de al lado.**

## 1 · LO QUE DECLARA, Y ES LO QUE FALTABA

`kfd_pm4_headers_vi.h:349`, textual:

```c
struct pm4_mes_unmap_queues {
	union {
		union PM4_MES_TYPE_3_HEADER   header;            /* header */
		uint32_t            ordinal1;
	};
	union {
		struct {
			enum mes_unmap_queues_action_enum   action:2;
			uint32_t                           reserved1:2;
			enum mes_unmap_queues_queue_sel_enum queue_sel:2;
			uint32_t                           reserved2:20;
			enum mes_unmap_queues_engine_sel_enum engine_sel:3;
			uint32_t                           num_queues:3;
		} bitfields2;
		uint32_t ordinal2;
	};
	...
```

**Es exactamente lo que `vid.h` no dice.** `vid.h` da el desplazamiento; KFD da
el desplazamiento **y la anchura**:

| campo | `vid.h` (macro) | KFD (bitfield) | ancho |
|---|---|---|---|
| `action` | `((x) << 0)` | `[1:0]` | **2** |
| `queue_sel` | `((x) << 4)` | `[5:4]` | **2** |
| `engine_sel` | `((x) << 26)` | `[28:26]` | **3** |
| `num_queues` | `((x) << 29)` | `[30:29]` | **3** |

Coinciden bit a bit, y el enum que acompaña confirma `action` — KFD declara
`mes_unmap_queues_action_enum` con los mismos cuatro valores que
`amdgpu_gfx.h`, en el mismo orden.

## 2 · `1077` QUEDA CERRADO, LOS CUATRO CAMPOS

Sobre el dword **observado** de `1094`, `0x20000001`:

```
KFD pm4_mes_unmap_queues            pm4_codec declara
  action      [1:0]   = 1             ACTION     [1:1]   = 0   MAL
  queue_sel   [5:4]   = 0             QUEUE_SEL  [2:0]   = 1   MAL
  engine_sel  [28:26] = 0             ENGINE_SEL [6:5]   = 0   OK
  num_queues  [30:29] = 1             NUM_QUEUES [10:10] = 0   MAL
```

**`QUEUE_SEL` es `[5:4]`.** El campo que `1077` declaró
«irresoluble por ejecución» está resuelto, y **los macros del kernel son
correctos en los cuatro campos** y `pm4_codec` se equivoca en los cuatro.

`1077` pasa de `CONTRADICCION` abierta a `RESUELTA`, con la caveat que ya
consigné: `QUEUE_SEL` se escribe con literal 0 en los 7 sitios del corpus, así
que el cambio es de documentación, no funcional.

## 3 · `1095` PIERDE SU PREMISE CENTRAL

`1095` concludes, y cito, que la anchura **no es determinable**:

> `vid.h` no declara anchuras… La imposibilidad no es un fallo de la herramienta:
> es una carencia de la fuente.

**La premisa es correcta y la conclusión era falsa.** `vid.h` no las declara, sí,
pero el árbol tiene otro declarante: KFD, que sí. Lo que la herramienta no
buscaba no era porque no existiera.

Y eso significa que `layoutcross` tiene **un oráculo de anchuras disponible y no
lo estaba usando**. Su constante

```
ANCHURA_NO_DETERMINABLE = "el kernel da el desplazamiento, no la anchura"
```

es una afirmación sobre `vid.h` que se generalizó al corpus, y el corpus
tiene más de una cabecera. Es el mismo error de `1087` —**una fuente escrita a
mano en vez de derivada**— en mi propio instrumento, y por eso lo digo con el
mismo nombre.

## 4 · LO NUEVO: LAS DOS FUENTES SE SOLAPAN EN `MAP_QUEUES`, Y ESO NO ES UNA CONTRADICCIÓN

`pm4_mes_map_queues`, bitfields2 (CONTROL):

```
reserved1:4 [3:0] · queue_sel:2 [5:4] · reserved2:15 [20:6] ·
queue_type:3 [23:21] · reserved3:2 [25:24] ·
engine_sel:3 [28:26] · num_queues:3 [31:29]
```

Coincide con `vid.h` en los cuatro campos que ambos nombran. `vid.h` añade
`VMID <<8` y `ALLOC_FORMAT <<24`, que KFD no modela — KFD mapea solo colas
compute y no necesita VMID ni formato de asignación.

**Pero bitfields3 (CONTROL2) no coincide:**

```
KFD:  reserved3:1 [0] · check_disable:1 [1] · doorbell_offset:21 [22:2] ·
      reserved4:3 [25:23] · queue:6 [31:26]
vid.h: CHECK_DISABLE <<1 · DOORBELL_OFFSET <<2 · QUEUE <<26 · PIPE <<29 · ME <<31
```

`queue:6` ocupa **[31:26]** y se come los bits 29 y 31, que `vid.h` llama
`PIPE` y `ME`. Sobre el dword observado de `1082`, `0x2C000014`:

```
vid.h:  queue[31:26]=11   pipe[30:29]=1   me[31]=0   doorbell[25:2]=5
KFD:    queue:6 [31:26] = 11          <-- 11, no 3
```

El 11 es `3` (queue) `|` `8` (bit 29, que es `pipe`).

**Esto NO es una contradicción, y la diferencia es de alcance:**

> KFD mapea exclusivamente colas **compute** y **nunca pone `pipe`**. Su layout
> de `CONTROL2` solo es válido con `pipe == 0`, y en ese caso `queue` y `queue:6`
> describen exactamente lo mismo.

La regla de desempate que sale de esto, y que generaliza:

```
FUENTE_AUTORITATIVA_CAMPO  el motor que USA ese campo en ese ASIC
                           GFX usa pipe y me  ->  vid.h
                           KFD usa queue solo con pipe==0  ->  KFD
```

`pm4_codec` sigue incompleto en `CONTROL2` (le faltan `queue`, `pipe` y `me`, y
KFD confirma que `queue` existe), pero **el defecto ya no es solo una ausencia**:
las dos fuentes del kernel dicen cosas distintas sobre los mismos bits, y por
eso ninguna de las dos puede servir de oráculo único para ese dword.

## 5 · LO QUE ESTO SIGNIFICA PARA EL PROYECTO

```
ANTES                                AHORA
2 fuentes que se contradicen         3 fuentes con alcances declarados
1 contraste de conteo                 3: conteo, asignacion, cobertura
0 campos extraidos de un dword        anchuras disponibles en el arbol
anchuras NOT_DETERMINABLE             anchuras declaradas por KFD
1 contradiccion irresoluble           0
```

**Y la lección de método, que es lo que más me cuesta de este hallazgo:**

> Escribí que el documento no estaba en el árbol **sin comprobar el directorio de
> al lado**. `amdkfd/` y `amdgpu/` están en la misma carpeta, y KFD implementa el
> mismo protocolo que GFX con cabeceras de packet propias.
>
> **`NOT_FOUND` aplicado a un directorio equivocado sigue siendo `NOT_FOUND`.**
> Decir «no está en el árbol» es una afirmación sobre el árbol, y yo la hice
> sobre un subárbol.

La quedó encendida: `1077` decía «el resolvers que quedan, y ninguno está en
el árbol», y esa frase era la pista de que había que buscar. No la seguí porque
el hallazgo ya estaba escrito y parecía cerrado.

## 6 · LO QUE NO ESTÁ HECHO, Y POR QUÉ

**No he ampliado `layoutcross` con el oráculo de anchuras.** Es el siguiente
paso obvious y no lo he dado: requiere resolver las structs de
`kfd_pm4_headers_vi.h` a bitfields con posición absoluta, que es un parser nuevo.
Mientras no esté, su `ANCHURA_NO_DETERMINABLE` sigue mintiendo en la dirección
opuesta: dice que no hay anchuras cuando las hay.

**No he comprobado las otras tres copias de `kfd_pm4_headers_vi.h`.** He usado
una. Que sean idénticas es esperable, no medido.

**No he reescrito `1095`.** Su §5 propose tres salidas y la primera —«el
documento de hardware»— resulta estar ya dentro del árbol. Queda como
documento con una premise refutada por `1096`, y lo digo aquí para que no se lea
como vigente.

**No he tocado `pm4_codec.py`.** Sigue con sus cuatro campos equivocados en
`UNMAP_QUEUES`, y ahora con **prueba**: un segundo declarante del kernel, en el
árbol, con la anchura.

## 7 · PROCEDENCIA

```text
fuente      RESEARCH/working/linux-7.1.3/drivers/gpu/drm/amd/amdkfd/
              kfd_pm4_headers_vi.h:349  struct pm4_mes_unmap_queues
              pm4_mes_map_queues, pm4_mes_set_resources en el mismo fichero
copias      4 en el arbol; amdkfd/ es hermano de amdgpu/ en drivers/gpu/drm/amd/
enum        mes_unmap_queues_action_enum = preempt 0, reset, disable, no_unmap
              identico a amdgpu_gfx.h:126
verificacion dword observado 0x20000001 (1094) contrastado con los tres origenes
MAP_QUEUES  0x2C000014 (1082) -> el solape queue:6 vs PIPE/ME, con su alcance
escrituras  0 ficheros de otros agentes
```

**Lo que este documento NO prueba.** No prueba que KFD y `vid.h` describan el
mismo hardware con el mismo alcance: KFD y amdgpu son drivers distintos y sus
structs se escribieron para necesidades distintas. La coherencia bit a bit de
`UNMAP_QUEUES` en cuatro campos es medida; que sea correcta en los cinco no lo
es, y `1077` lo cerró por el valor que el driver escribe, no por acuerdo entre
fuentes. No he leído el resto de `kfd_pm4_headers_vi.h`, y puede tener divergencias
en otros paquetes.
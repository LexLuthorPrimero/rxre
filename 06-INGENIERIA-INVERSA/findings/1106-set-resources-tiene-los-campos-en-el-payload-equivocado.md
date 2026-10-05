# 1106 — `SET_RESOURCES` no tiene los campos **en bits equivocados**: los tiene **en el payload equivocado**. Con KFD como tercer oráculo, `CONTRADICCION` queda en 0 y los defectos se reparten en tres clases separables

```text
AGENCIA=RX550-INVESTIGACION · WORK_CLASS=AGENT-SIDE-PM4FIELDS
AUTOR=AGENTE-INSTR
WRITE_EXECUTION=NONE · MODIFICATIONS=0 · RUNTIME=NOT_RUN
ESCRITOS_POR_ESTA_ITERACION   tools/layoutcross.py (contraste por payload,
                            clase DISCREPA_DWORD, correccion de orden de veredictos)
                            tools/verif.py (5 medidas de bits)
MODIFICADO_NADA_EXISTENTE    pm4_codec.py intacto
CLASSIFICATION=MEASUREMENT+DEFECT · TRACK=STATIC
GENERADO=2026-10-04 · MEDIDO=EN ESTA HOST
AFECTADO=08-ARQUITECTURA/tools/pm4_codec.py:73-92 (SET_RESOURCES) — CORRIGE 1073
ESTADO=VALIDADO · 54 vectores, rc=0, hermetico · 35 medidas sin deriva
```

## 0 · El resultado, primero

```
CONTRADICCION    6  ->  0        <-- la clase VACIA, alcanzada
DISCREPA_POSICION  4              el campo esta en otros BITS
DISCREPA_ANCHURA   6              el campo esta en su sitio y se TRUNCA
DISCREPA_DWORD     2              el campo esta en otro PAYLOAD
CAMPO_INVENTADO    1              el nombre no existe en ninguna fuente
NOMBRES_NO_COMPARABLES 11        el kernel no desglosa: no es veredicto
OK                21
SIN_ORACULO_BITS   1
```

**`SET_RESOURCES` pasa de «dos campos en bits equivocados» a «dos campos en el
dword equivocado».** Eso cambia la clase del defecto y el arreglo que necesita.

## 1 · POR QUÉ ES UNA CLASE DISTINTA, Y POR QUÉ NO LA TENÍA

`1073` escribió, sobre `SET_RESOURCES`:

> `queue_type[15:14]` contradictorio con `<<29`, `vmid_mask[31:16]` con `<<0`.

Esos LSB **no** son el dato. KFD sitúa ambos campos en el **payload 1**:

```c
// amdkfd/kfd_pm4_headers_vi.h, pm4_mes_set_resources
vmid_mask:16 · unmap_latency:8 · reserved:5 · oac_mask:16 · ...
```

y `pm4_codec` los declara en el **payload 2**, dentro de una entrada que llama
`CONTROL / resource size`:

```python
"PACKET3_SET_RESOURCES": [
    "CONTROL[31:0]  (resource size)",          # payload 1
    "vmid_mask[31:16] | queue_type[15:14]",    # payload 2   <-- aqui deberia ir CONTROL
    "queue_mask_lo[31:0]",
    ...
]
```

**El layout está desplazado un payload.** Los bits son el síntoma; el dword es la
causa. Y el kernel lo dice con un comentario por dword
(`gfx_v8_0.c:4332-4338`), que es lo que usa `1093` para sintetizar el IB:

```
4332  0  /* vmid_mask:0 queue_type:0 (KIQ) */      <- payload 1
4333  lower_32_bits(queue_mask)  /* queue mask lo */ <- payload 2
```

## 2 · LA DISTINCIÓN QUE HACE EL TRABAJO, Y QUE ES FÁCIL NO HACER

Tres clases, y se separan por **qué dato mínimo contradice** lo declarado:

| clase | qué contradice | gravedad | arreglo |
|---|---|---|---|
| `DISCREPA_POSICION` | el **LSB**: el campo está en otros bits | bug funcional | cambiar los bits |
| `DISCREPA_ANCHURA` | nada: LSB correcto, rango más estrecho | documentación | ampliar el rango |
| `DISCREPA_DWORD` | el **payload**: el campo está en otro dword | bug funcional, y además el layout está corrido | mover la entrada |

La tercera es la que `1061` («`CP_DMA` declara un dword de más») solo podía
detectar **contando**. Aquí se detecta **por campo**, y dice cuál.

## 3 · UN BUG MÍO QUE ENMASCARABA LA CLASE NUEVA

La primera versión dejaba `DISCREPA_DWORD` **después** de la rama del LSB:

```
elif lsb_unico is not None and lo != lsb_unico:   CONTRADICCION
elif _otro:                                        DISCREPA_DWORD   <-- inalcanzable
```

Consecuencia medida: los dos campos de `SET_RESOURCES` salían
`CONTRADICCION`, que es **menos específico y menos cierto** — `CONTRADICCION`
dice «no sé cuál de los dos tiene razón», y aquí sí se sabe: KFD fija el payload.

```
ANTES   CONTRADICCION 2   (v2, vmid_mask)   "no se sabe quien tiene razon"
AHORA   DISCREPA_DWORD 2  (v2, vmid_mask)   "estan en el payload equivocado"
```

> **El orden de una cadena de veredictos es una decisión semántica, no de
> redacción.** Poner la regla más específica después de la genérica la deja
> muerta, y una rama muerta no se nota porque no dispara.

## 4 · TRES BUGS DEL ORÁCULO DE KFD, TODOS DE «DESCARTAR EN SILENCIO»

El primer oráculo dinyatakan 6 paquetes pero daba datos incorrectos. Los tres eran de la
misma clase, que es la que más me ha costado en este trabajo:

### 4.1 El regex del cierre no aceptaba nombres alfanuméricos

`bitfields3a` y `bitfields3b` no casan con `(\d+)`. Son **alternativas del mismo
dword** (`pasid` frente a `doorbell_offset0`). Resultado: **el payload 2 entero
de `UNMAP_QUEUES` desaparecía**, y `DOORBELL_OFFSET0` quedaba sin oráculo.

### 4.2 El cuerpo de la struct se acortaba por el primer `};` del texto

Acotaba con `texto.find("\n};")`, que encuentra el `};` del primer nivel interno,
no el de la struct. El cuerpo se desbordaba **dentro de la struct siguiente** y
leía sus cierres como propios. Se vio porque el payload 1 de `UNMAP_QUEUES`
salía con los campos de `RELEASE_MEM` (`cache_policy`, `event_index`).

### 4.3 Off-by-one en el apareo de llaves, en las dos direcciones

```python
_prof, _fin = 1, None
for _j in range(sm.end(), len(texto)):
```

`sm.end()` es justo **después** de la `{` que el patrón ya consumió, así que
`_prof` arranca en 1 y se cierra en el `}` de la struct. La versión anterior
arrancaba en `sm.end() - 1` y contaba esa llave dos veces: la profundidad nunca
volvía a 0, `_fin` quedaba `None` y el cuerpo se iba al final del fichero —
**0 paquetes** en vez de 6.

Los tres producían **salidas que parecían completas y no lo eran**. Un oráculo
que devuelve menos de lo que tiene no se distingue de uno que no encuentra nada,
y por eso `CONTRADICCION` — la clase que inventé precisamente para no
confundir «no lo sé» con «no está» — salía 0 en un instrumento que aún no
funcionaba.

## 5 · LO QUE ESTO CIERRA Y LO QUE ABRE

**Cierra:** `CONTRADICCION = 0`. Con un tercer declarante que publica anchuras, ya
no hay ninguna afirmación del proyecto que no se pueda contrastar por completo.
La puerta `verif` la tiene como `VACIA`, así que si vuelve a aparecer, salta.

**Abre, y es lo importante:** el defecto de `SET_RESOURCES` **agravado**, y el
reparto real de `pm4_codec`:

```
4 campos en bits equivocados     UNMAP_QUEUES: action, engine_sel, num_queues, queue_sel
2 campos en el payload equivocado  SET_RESOURCES: vmid_mask, queue_type
6 campos truncados               MAP_QUEUES x5, UNMAP_QUEUES.DOORBELL_OFFSET0
1 nombre inexistente             SET_RESOURCES.RESOURCE_SIZE
3 campos sin declarar            MAP_QUEUES.CONTROL2: queue, pipe, me
```

`MAP_QUEUES` es el layout **mejor** de los siete: sus cinco posiciones son
correctas. El peor es `SET_RESOURCES`, y no por sus bits sino por estar corrido
un payload.

## 6 · LO QUE NO ESTÁ HECHO, Y POR QUÉ

**No he reparado `pm4_codec.py`.** Con KFD, los contratos de reparación de
`1061`, `1073` y `1082` se pueden escribir con rangos completos y con un segundo
declarante que los respalda. No lo he hecho por dos razones: es fichero de otra
sesión, y **ninguno de los tres tests de reparación se ha ejecutado**, así que
no puedo declarar validada una corrección que no he probado.

**No he leído las otras cabeceras de KFD.** Hay `kfd_pm4_headers_ai.h` y
`_aldebaran.h`, y 108 líneas de opcode. Los 6 paquetes que leo son de `vi.h`, que
es GFX8. Los paquetes de las otras generaciones pueden divergir, y un hallazgo
previo del proyecto (`099`) ya midió discrepancias entre copias de `sid.h`, así
que la suposición no es gratis.

**No he comprobado las 4 copias de `kfd_pm4_headers_vi.h`.** Uso una.

**No he ampliado `extraer_bits` al caso de un campo declarado en dos payloads.** El
contrato de `setdefault` dentro de un payload está escrito desde `1105`; entre
payloads no puede ocurrir, porque cada payload es una entrada distinta.

## 7 · PROCEDENCIA

```text
oraculo     layoutcross.campos_kfd() -> 6 paquetes, UNMAP_QUEUES 5 payloads
            UNMAP_QUEUES: dw1 action/queue_sel/engine_sel/num_queues
                           dw2 doorbell_offset0  (antes invisible)
                           dw3..5 doorbell_offset1..3
contraste   por payload, no aplanado: campos con el mismo nombre en dos payloads
            son legitimos (doorbell_offset0..3) y aplanados serian contradiccion
clases      DISCREPA_POSICION 4 · DISCREPA_ANCHURA 6 · DISCREPA_DWORD 2
            CAMPO_INVENTADO 1 · CONTRADICCION 0 · OK 21 · SIN_ORACULO_BITS 1
selftest    54 vectores, rc=0, 1 vector nuevo para DISCREPA_DWORD
hermetico   /tmp/opencode/herm6, sin KFD ni corpus, 54 vectores, rc=0
puerta      verif 35 medidas; antes de congelar, 33 de 35 sin deriva y las 2 que
            derivaron fueron las que el cambio de orden de veredictos produce
            despues: SIN DERIVA, rc=0
escrituras  0 ficheros de otros agentes
```

**Lo que este documento NO prueba.** No prueba que el layout de KFD sea el
correcto para GFX8: KFD modela colas de cómputo y su `queue:6 [31:26]` se solapa
con `PIPE` y `ME` de `vid.h` (`1096` §4). Lo uso porque coincide con `vid.h` bit
a bit donde ambos nombran un campo, no porque sea una autoridad. No he ejecutado
ninguna reparación. Y `DISCREPA_DWORD` no se ha observado en ningún paquete real
del proyecto todavía: se ha probado solo con fixture, y el único caso donde el
oráculo la dispara es `SET_RESOURCES`, que es un defecto conocido y no una
sorpresa.
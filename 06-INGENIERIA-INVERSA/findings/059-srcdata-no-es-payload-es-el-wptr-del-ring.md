# 059 · `src_data[0]` no lleva el payload del evento: es el WPTR del propio ring

`CLASSIFICATION=DOCUMENTATION` · `TRACK=STATIC` · `CORPUS=RESEARCH/working/linux-7.1.3`
`HARDWARE_SCOPE=HOST-C/RX550` · `WORK_CLASS=READ_ONLY/EVIDENCE`
`WRITE_EXECUTION=SCOPED(findings)` · `RUNTIME=NOT_RUN` · `GPU INTACTA`
`CORRECTS=058 §3, rama (2)` · `CONTINUES=051, 052, 058`

## CUDA principal

`058 §3` dejó tres candidatas para obtener la granularidad que el IV no da, y
nombró como más probable que `src_data[0]` —los 28 bits de payload— llevase el
detalle del evento.

**Es falso, y lo dice el corpus.** El único consumidor de `src_data[0]` en toda la
generación lo interpreta como el **puntero de escritura del propio ring**:

```c
/* ih_v7_0.c:552-566 */
static int ih_v7_0_self_irq(struct amdgpu_device *adev, ...)
{
        uint32_t wptr = cpu_to_le32(entry->src_data[0]);

        switch (entry->ring_id) {
        case 1:
                *adev->irq.ih1.wptr_cpu = wptr;
                schedule_work(&adev->irq.ih1_work);
                break;
        ...
```

No es carga útil del evento. Es un vector de **auto-notificación del ring 1**: el
ring avisa de su propio WPTR para que la CPU suba trabajo pendiente.

De las tres candidatas de `058 §3`, una queda **descartada por evidencia**, no por
falta de búsqueda. Eso es un `NOT_DETERMINED` más estrecho.

## 1 · El recuento, que es la observación real

Un solo uso de `src_data` en cada fichero de IH de esta generación:

| fichero | usos | qué consume |
|---|---|---|
| `tonga_ih.c` | 1 | sólo lo **imprime**: `dev_err(..., entry->src_id, entry->src_data[0])` |
| `ih_v6_0.c` | 1 | ídem |
| `ih_v6_1.c` | 1 | ídem |
| `ih_v7_0.c` | 1 | **lo interpreta** como WPTR |

**GFX8 no decodifica `src_data[0]` en absoluto.** `tonga_ih.c` lo copia a la
entrada y lo imprime en el mensaje de fault; no lo descompone en campos. El IV
entrega 28 bits y el driver de Tonga no les da significado.

Eso no significa que el hardware no los use: significa que **para esta GPU nadie
sabe qué contienen**, y el único indicio de la generación sugiere que en el caso
de uso conocido eran un puntero de ring.

## 2 · El mecanismo de auto-notificación, y por qué importa

El handler se registra con su propio `amdgpu_irq_src` (`ih_v7_0_set_self_irq_funcs`,
`ih_v7_0.c:572-575`), o sea que es un canal **distinto** del de faults. No comparte
`src_id` con `0x92`/`0x93` (ver `052`).

Pero el patrón es el mismo que el de `051 §4`, visto desde el otro lado:

```
051 §4   overflow:  el hardware marca RB_OVERFLOW en un REGISTRO;
                  el driver lo re-lee y salta rptr
059      self_irq:  el hardware pone el WPTR DENTRO DEL IV;
                  no hay registro que leer
```

En ambos casos el problema es el mismo —**el hardware avanza un puntero y la CPU lo
observa con latencia variable**— y las dos soluciones son el patrón
doble-lectura y el salto. La diferencia es que aquí el dato viaja con el evento.

**Para un driver propio esto es la vía barata de sincronización**: no hace falta
leer ningún registro, el WPTR llega en el propio vector. Es el mismo criterio que
`056` aplicó al spec de shaders y que `057` aplicó a las vías de lectura, aplicado
ahora a un mecanismo concreto: elegir el camino que no requiere acceso al
hardware desde la CPU.

## 3 · Corrección a `058 §3`

La lista de candidatas queda así:

| candidata | estado |
|---|---|
| otro registro con el detalle del evento | **no identificado** |
| `src_data[0]` con el id de línea | **DESCARTADA** — es el WPTR del ring |
| estado de scanout de display | **no rastreado** |

Dos de tres siguen abiertas. Lo que cambia es que una ya no es una hipótesis
plausible sino una descartada, y que ahora se sabe que **GFX8 no decodifica
`src_data[0]` en ningún sitio**, lo que convierte a las dos restantes en el único
camino posible.

## 4 · Clasificación

| afirmación | clase | estado |
|---|---|---|
| `src_data[0]` es el WPTR del ring en el único uso conocido | FACT | **PROVEN** |
| GFX8 (`tonga_ih.c`) no decodifica `src_data[0]` | NEGATIVE_RESULT | **PROVEN_ABSENT**, 4 ficheros de la generación |
| self_irq es un `irq_src` distinto del de faults | FACT | **PROVEN** |
| el WPTR puede viajar en el IV sin leer registro | DERIVATION | **PROVEN_DERIVED** |
| contenido de `src_data[0]` para un fault en GFX8 | — | **`NOT_DETERMINED`** — el driver no lo decodifica |
| dónde está el detalle del evento de display | — | `NOT_DETERMINED`, 2 candidatas |

## Lo que este hallazgo NO cierra

No cierra §D. Lo que hace es reducir el espacio de búsqueda de una pregunta
concreta de "tres sitios posibles, uno de ellos plausible" a "dos sitios, ninguno
en el IV". Y deja documentado un mecanismo de sincronización que hasta ahora no
estaba en ningún hallazgo.

## Nota de proceso

En `058 §3` escribí que `src_data[0]` era "la más probable". No lo había
verificado: era una intuición razonada a partir de que era el único sitio donde
podía haber detalle. La regla del proyecto es explícita sobre esto — la
distinción entre software behaviour y hardware semantics, y entre `HYPOTHESIS` y
`FACT` — y aun así la enuncié con la seguridad de quien la comprobó.

El patrón se repite: **la conjetura razonable más Safe en la casilla de
"probable" acaba leída como hallazgo.** En `058 §3` la marqué como candidata, lo
que es correcto, pero "la más probable" es un juicio que no tenía permiso para
emitir sin abrir el fichero. Tres líneas de lectura lo habrían resuelto.

Es la diferencia entre enumerar candidatas —que es lo que §SEMANTIC BISECTION
pide— y provocar una. Enumerar está bien; provocar no.
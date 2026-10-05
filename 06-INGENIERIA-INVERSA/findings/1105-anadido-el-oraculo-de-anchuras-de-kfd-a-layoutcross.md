# 1105 — Añadido el oráculo de anchuras de KFD a `layoutcross`: las 6 contradicciones pasan a `DISCREPA_POSICION`, y separarlas de 4 errores de solo anchura evita inflar el recuento con cosas que no son bugs

```text
AGENCIA=RX550-INVESTIGACION · WORK_CLASS=AGENT-SIDE-PM4FIELDS
AUTOR=AGENTE-INSTR
WRITE_EXECUTION=NONE · MODIFICATIONS=0 · RUNTIME=NOT_RUN
ESCRITOS_POR_ESTA_ITERACION   tools/layoutcross.py (nuevo oraculo + 2 clases)
                            tools/verif.py (medidas de bits reestructuradas)
MODIFICADO_NADA_EXISTENTE    pm4_codec.py y pm4_emit.py intactos
CLASSIFICATION=IMPLEMENTATION · TRACK=STATIC
GENERADO=2026-10-04 · MEDIDO=EN ESTA HOST
AFECTADO=tools/layoutcross.py (propio) · corrige la premisa de 1095
ESTADO=VALIDADO · 51 vectores de selftest, rc=0, hermetico · 34 medidas sin deriva
```

## 0 · El resultado, primero

```
ANTES (solo vid.h + macros)         AHORA (+ kfd_pm4_headers_vi.h)
CONTRADICCION   6                   DISCREPA_POSICION   6
DISCREPA        0                   DISCREPA_ANCHURA    4
OK             27                   CAMPO_INVENTADO     1
CAMPO_INVENTADO 1                   NOMBRES_NO_COMPARABLES 8
                                    OK                 23
                                    SIN_ORACULO_BITS    1
```

**Las 6 contradicciones dejan de existir**, no porque se hayan resuelto a mano,
sino porque hay un tercer declarante que sí publica anchuras. Y 4 de los 10
defectos restantes **no son fallos funcionales**, cosa que un veredicto único
escondía.

## 1 · EL ORÁCULO, Y LA PREGUNTA QUE HAY QUE RESPONDER ANTES

El parseo de las structs de KFD tiene un detalle que el fichero **no dice**: el
orden de los bitfields. Es LSB-first, y está medido contra los desplazamientos
independientes de `vid.h`, no supuesto:

```
LSB-first -> action[1:0] queue_sel[5:4] engine_sel[28:26] num_queues[31:29]
             4 de 4 coinciden con vid.h
MSB-first -> action[31:30] queue_sel[27:26] engine_sel[5:3] num_queues[2:0]
             0 de 4
```

> Suponer el orden equivocado haría que **todas** las anchuras salieran mal y
> parecieran coherentes. Es el peor modo de fallo posible para una tabla de
> posiciones: no se distingue del correcto por ninguna señal.

Cobertura del oráculo: **6 paquetes**, con los rangos derivados de los anchos
declarados.

## 2 · LA SEPARACIÓN QUE HACE FALTA, Y POR QUÉ NO ES COSMÉTICA

Al enchufar el oráculo, las 4 afirmaciones de `MAP_QUEUES` salieron `DISCREPA`:

```
engine_sel   pm4 [26:26]   kfd [28:26]
num_queues   pm4 [29:29]   kfd [31:29]
queue_sel    pm4  [4:4]    kfd  [5:4]
queue_type   pm4 [21:21]   kfd [23:21]
```

**Los cuatro tienen el LSB correcto.** `pm4_codec` declara campos de 1 bit donde
el kernel usa 2 o 3. La posición está bien; lo que falta es ancho.

```
DISCREPA_POSICION   el LSB no coincide: el campo esta en OTROS bits -> funcional
DISCREPA_ANCHURA    el LSB coincide pero el rango es mas estrecho -> el valor se
                    lee bien mientras quepa; el campo se TRUNCA -> documentacion
```

Medido, el efecto de no separarlos: **4 de los 10 `DISCREPA` iniciales no eran
bugs.** Un recuento que sube de 6 a 10 parece progreso y en parte es
reclasificación de la misma cosa con más precise. Lo que hace el cambio real es
que las dos clases arregladas por personas distintas: los 6 de posición
son bugs del driver de referencia, los 4 de anchura son falta de información que
requiere el documento de hardware.

## 3 · LO QUE ESTO CORRIGE DE `1082`, Y ES UNA CORRECCIÓN A FAVOR

`1082` — los hallazgos sobre `MAP_QUEUES`remainían en pie, pero el cuadro se afina:

| campo | `pm4_codec` | KFD | LSB | veredicto |
|---|---|---|---|---|
| `queue_sel` | `[4:4]` | `[5:4]` | ✓ | `DISCREPA_ANCHURA` |
| `queue_type` | `[21:21]` | `[23:21]` | ✓ | `DISCREPA_ANCHURA` |
| `engine_sel` | `[26:26]` | `[28:26]` | ✓ | `DISCREPA_ANCHURA` |
| `num_queues` | `[29:29]` | `[31:29]` | ✓ | `DISCREPA_ANCHURA` |

**Las cinco posiciones declaradas de `MAP_QUEUES` son correctas.** Lo que `1082`
reporta sigue siendo verdad y ahora se mide mejor: `CONTROL2` sigue declarando
**un** campo donde el driver escribe cuatro, y KFD confirma que `queue` existe
además de `pipe` y `me`.

Y `1082` acquires algo que no tenía: **`MAP_QUEUES` no está en la lista de
errores de posición.** El defecto de `MAP_QUEUES` es de cobertura y de ancho, no
de sitio. Eso es información que cambia qué se arregla y en qué orden.

## 4 · `1095` QUEDA REFUTADA EN SU PREMISE, Y EL ARTEFACTO LO DICE

`1095` sostenía, y lo cito:

> `ANCHURA_NO_DETERMINABLE = "el kernel da el desplazamiento, no la anchura"`
> La imposibilidad no es un fallo de la herramienta: **es una carencia de la
> fuente.**

**La primera frase era cierta sobre `vid.h` y falsa sobre el árbol**, y la segunda
era una generalización que no hice. El constante sigue en `layoutcross.py`, y
ahora hay un oráculo más fuerte que él, pero **dejar el constante diciendo eso es
dejar una afirmación falsa en el código**. Queda pendiente corregirlo o retirarlo
cuando el oráculo de KFD cubra los paquetes que aún no cubre.

Y la lección, que es de las que más cuestan:

> Escribí un hallazgo **`1096`** diciendo que el segundo oráculo estaba en el
> árbol, y el instrumento que construí antes **no lo usaba**. No es que no
> supiera: es que no fui a mirar el directorio de al lado al escribir el
> instrumento, y lo hice al escribir el hallazgo. La fuente estaba disponible en
> el momento de construir y en el momento de descubrir.
>
> **`NOT_FOUND` sobre el subárbol equivocado sigue siendo `NOT_FOUND`.**

## 5 · VERIFICACIÓN, EN EL ORDEN QUE IMPONE EL HECHO

```
selftest     51 vectores, rc=0
             3 fallaron al añadir el oráculo, y los 3 eran expectativas mias
               - gds_heap_base[9:0] vs [5:0]: mismo LSB -> ahora ANCHURA
               - dos vectores por un nombre de campo DUPLICADO en el fixture
                 (extraer_bits usa setdefault, gana la primera declaracion)
             y el fixture tambien fallaba al reusar oac_mask: era el mismo bug
hermeticidad /tmp/opencode/herm6, sin acceso a KFD ni al corpus, 51 vectores, rc=0
puerta      verif: 34 medidas. Antes de congelar, 30 de 34 sin deriva y las 4 que
             derivaron fueron exactamente las que el oraculo nuevo cambia:
             contradicciones 6->0, ok 27->23, y las 2 medidas nuevas
             despues: SIN DERIVA, rc=0
```

El hallazgo del fixture duplicado merece registries: **`extraer_bits` usa
`setdefault`, así que si una herramienta declara el mismo campo dos veces con
rangos distintos, solo se ve el primero, en silencio.** No lo he cambiado porque
es una decisión defendible (una entrada por campo) pero **no está declarada**, y
mi fixture la всплылó por accidente. Queda como `NOT_FOUND` del contrato, no como
problema resuelto.

## 6 · LO QUE NO ESTÁ HECHO, Y POR QUÉ

**No he reparado `pm4_codec.py`.** Sigue con 6 campos en bits equivocados, 4
truncados, 1 nombre inexistente y 3 campos sin declarar en `CONTROL2`. Con KFD
disponible, el contrato de reparación ya se puede escribir con rangos completos
y con la certeza de que hay un segundo declarante que los respalda.

**No he cubierto los paquetes que KFD no modela.** KFD declara 6 paquetes
(`MAP_QUEUES`, `UNMAP_QUEUES`, `SET_RESOURCES`, `QUERY_STATUS`, `MAP_PROCESS`,
`RUNLIST`). `CP_DMA` y `DMA_DATA` quedan con oráculo de comentario y de macro, y
sus anchuras siguen `SIN_ORACULO_BITS` o `NOMBRES_NO_COMPARABLES`.

**No he leído el resto de `kfd_pm4_headers_vi.h`.** Hay 108 líneas de opcode y
varias cabeceras más por generacion; puede haber divergencias con `vid.h` en
paquetes no medidos.

**No he cubierto con KFD las otras 3 copias del fichero.** He usado una. Que
sean idénticas es esperable, no medido — y un hallazgo (`099` del proyecto) ya
midió discrepancias entre copias de `sid.h`, así que la suposición no es gratis.

## 7 · PROCEDENCIA

```text
oraculo     layoutcross.campos_kfd() -> 6 paquetes
            fuente: RESEARCH/working/linux-7.1.3/drivers/gpu/drm/amd/amdkfd/
                    kfd_pm4_headers_vi.h
orden       LSB-first, MEDIDO contra los 4 shifts de vid.h (4/4 vs 0/4)
precedencia KFD (ancho) > comentario numerado (rango) > macro (solo LSB)
clases      DISCREPA_POSICION 6 · DISCREPA_ANCHURA 4 · CAMPO_INVENTADO 1
            NOMBRES_NO_COMPARABLES 8 · OK 23 · SIN_ORACULO_BITS 1
selftest    51 vectores, rc=0, hermetico
puerta      34 medidas, SIN DERIVA, rc=0
escrituras  0 ficheros de otros agentes
```

**Lo que este documento NO prueba.** No prueba que el layout de KFD sea correcto
para GFX8: KFD modela queues de cómputo y su `queue:6 [31:26]` se solapa con
`PIPE` y `ME` de `vid.h` (hallazgo `1096` §4). Coinciden en `UNMAP_QUEUES` bit a
bit y en `MAP_QUEUES.CONTROL`, y ese acuerdo es lo que uso, no una autoridad de
KFD. No he ejecutado la reparación de `pm4_codec` y por tanto no hay test que la
valide todavía.
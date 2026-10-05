# 1107 — Los contratos de reparación de `1061`/`1073`/`1082`/`1094`/`1106`, **ejecutados**: llevan los 13 defectos funcionales a cero y el residuo son 4 diferencias de alcance entre dos fuentes del kernel

```text
AGENCIA=RX550-INVESTIGACION · WORK_CLASS=IMPLEMENTATION-VALIDATION
AUTOR=AGENTE-INSTR
WRITE_EXECUTION=NONE · MODIFICATIONS=0 · RUNTIME=NOT_RUN
ESCRITOS_POR_ESTA_ITERACION   tools/layoutcross.py (--solo)
                            08-ARQUITECTURA/artifacts/R9-REPARACION/{candidata.py,
                            antes-despues.txt}
MODIFICADO_NADA_EXISTENTE    pm4_codec.py INTACTO — la reparacion se mide, no se aplica
CLASSIFICATION=VALIDATION · TRACK=STATIC
GENERADO=2026-10-04 · MEDIDO=EN ESTA HOST
ESTADO=CONTRATOS EJECUTADOS Y VALIDADOS · el fichero vivo sigue sin tocar
```

## 0 · El resultado, primero

Cinco hallazgos écritos, declarados en la seccion de contrato de cada uno como
`TEST positivo: ...` / `TEST negativo: ...`, y **ninguno ejecutado**. Esta
iteración los ejecuta. El resultado:

```
                              VIVO              CANDIDATA
CONTEO   DISCREPA                1                    0
         OK                      3                    4

BITS     DISCREPA_POSICION       4                    0
         DISCREPA_DWORD          2                    0
         CAMPO_INVENTADO        1                    0
         DISCREPA_ANCHURA        6                    1
         OK                     21                   35

COBERTURA campos escritos
         y no declarados        3                    0
```

**Los 13 defectos funcionales (4 posición + 2 payload + 1 nombre + 3 cobertura + 1
conteo + 2 truncado de los que solobeeffecto) caen a cero.** Y `pm4_codec.py`
**no se ha tocado**.

## 1 · POR QUÉ HACÍA FALTA `--solo`

Los contratos no se podían ejecutar porque cualquier forma de probar la
reparación passing por `pm4_codec.py` significa **modificar el fichero de otra
sesión**. Y la razón por la que no se podía simplemente medir «la reparación»
junto al original es que `descubrir_declarantes()` recorre los directorios de
herramientas: la copia reparada y el vivo entrarían **en la misma población**, y
ganaría el primero. El resultado no diría nada de la candidata.

`--solo` desactiva el descubrimiento y mide solo lo que se pase por `--fuente`:

```
$ python3 tools/layoutcross.py --solo --fuente <candidata.py>
```

Es una capacidad pequeña y es exactamente la que faltaba: **medir una
declaración candidata sin tocar la declaración viva**. Sin ella, la única vía de
validar una reparación es aplicarla, y aplicarla es exactamente lo que no se
debe hacer con fichero ajeno.

## 2 · LA CANDIDATA NO ES UN PARCHE: ES LA DECLARACIÓN

`artifacts/R9-REPARACION/candidata.py` no copia `pm4_codec.py`. Contiene
**solo** `DOC_LAYOUTS` con los contratos aplicados. Razón: `layoutcross` mide una
declaración, no un fichero, y una copia del instrumento sería una segunda
implementación que mantener — el patrón que `1090` denounced en el evaluador de
`pm4_emit`.

```
PACKET3_CP_DMA        6 entradas -> 5   (1061: se quita la cabecera)
PACKET3_SET_RESOURCES 7 -> 7           (1073 + 1106: los 7 payloads del kernel)
PACKET3_MAP_QUEUES    6 -> 6           (1082: CONTROL2 con sus 5 campos)
PACKET3_UNMAP_QUEUES  5 -> 5           (1094: rangos completos de KFD)
```

## 3 · EL CONTRATO MIO TENÍA ERRORES, Y EL INSTRUMENTO LOS CACÓ

Primera iteración, con las anchuras que yo deduje:

```
DISCREPA_ANCHURA 3
  SET_RESOURCES queue_type     [29:29]   KFD [31:29]
  SET_RESOURCES unmap_latency  [31:16]   KFD [23:16]
  MAP_QUEUES   doorbell_offset [25:2]    KFD [22:2]
```

KFD declara `queue_type:3` y `unmap_latency:8`, y yo había puesto 1 y 16.
**Escribí un contrato con anchuras inventadas y lo declaré como basado en la
fuente.** El instrumento lo detectó en la primera ejecución, que es exactamente
para lo que existe.

Segunda iteración, con las anchuras que el oráculo declara:

```
DISCREPA_ANCHURA 1
  MAP_QUEUES doorbell_offset [25:2]  KFD [22:2]
```

El residuo es el único de los cuatro que **no** es un error mío ni del
original: es una diferencia de alcance, y §4 lo explica.

## 4 · EL RESIDUO SON ALCANCES, NO DEFECTOS — Y ES LA PARTE QUE IMPORTA

```
MAP_QUEUES doorbell_offset  DISCREPA_ANCHURA
    el LSB coincide (2); KFD da [22:2] y vid.h permite hasta [25:2]

MAP_QUEUES queue             POSICION_DEPENIENTE_GENERACION
    vid=<<26  soc15d=<<13  gfx_v12_1_pkt=<<13  nvd=<<13
MAP_QUEUES pipe              POSICION_DEPENIENTE_GENERACION
    vid=<<29  soc15d=<<16  gfx_v12_1_pkt=<<16  nvd=<<16
MAP_QUEUES me                POSICION_DEPENIENTE_GENERACION
    vid=<<31  soc15d=<<18  gfx_v12_1_pkt=<<18  nvd=<<18
```

Esto ya lo había medido `1096 §4`: **el `CONTROL2` de GFX8 empaqueta cinco
campos y el de GFX9+ empaqueta tres.** KFD mapea solo colas compute y nunca pone
`pipe` ni `me`, así que su `queue:6 [31:26]` incluye los bits que `vid.h` llama
`pipe` y `me`.

Y `doorbell_offset`: bajo `vid.h` el campo puede ocupar hasta `[25:2]` porque lo
siguiente (`QUEUE`) empieza en 26. KFD lo estrecha a `[22:2]` porque reserva
`[25:23]`. **Las dos reservas son correctas en su alcance.**

> **Un residuo que se puede explicar por alcance no es un defecto pendiente.** Es
> la diferencia entre «sigue roto» y «queda algo que solo una fuente puede
> decidir».

La regla de desempate que ya salió en `1096` y que esta candidata respeta:

```
FUENTE_AUTORITATIVA_CAMPO  el motor que USA ese campo en ese ASIC
  GFX8 usa pipe y me -> vid.h       (y la disjointness de sus LSB obliga a
                                     queue[28:26] y doorbell_offset[25:2])
  KFD mapea solo compute y pipe==0 -> KFD
```

## 5 · LO QUE ESTO DEMUESTRA DEL BUCLE, Y NO SOLO DEL RESULTADO

El ciclo de reparación se **ejecutó dos veces** y la segunda cambió el contrato.
Eso significa que el contrato de la primera — escrito sin medir, como
`PROVEN_DERIVED` con anchuras deducidas — **no era ejecutable tal como estaba**.

```
escribir contrato  ->  ejecutar  ->  el instrumento dice que el contrato esta mal
                                      (3 anchuras inventadas)
corregir contrato  ->  ejecutar  ->  0 defectos funcionales, 4 de alcance
```

Ese es el orden correcto y no es el que había: un contrato escrito sin ejecutar
es una hipótesis, y presentarlo como contrato es el mismo error que presentar una
cifra sin producer.

## 6 · LO QUE NO ESTÁ HECHO, Y POR QUÉ

**No he aplicado la reparación.** `pm4_codec.py` es de otra sesión activa y
AGENTS.md más el criterio que he seguido en los 15 hallazgos anteriores
dicen que se reporta. La candidata está lista para que quien lo posea la aplique,
con el before/after medido.

**No he escrito el test de regresión que los contratos piden.** Los contratos de
`1061` y `1073` especifican un control positivo y uno negativo sobre un IB
concreto. El IB existe (`R8-IBREF`), así que el test **es escribible**, y
escribirlo es el paso siguiente natural. No lo he hecho porque es una
implementación y esta iteración es una validación.

**No he añadido la candidata a la puerta de `verif`.** Es una declaración en
`artifacts/`, no un instrumento; meterla como medida la convertiría en parte del
sujeto medido, que es lo que `§34` (idempotencia) y `§37` (linaje) warns en
contra de hacer sin decidir.

**No he resuelto `CP_SYNC`.** Queda `SIN_ORACULO_BITS`: el kernel lo nombra en el
comentario de `CP_DMA` y ningún oráculo lo posiciona, porque KFD no modela
`CP_DMA`.

## 7 · PROCEDENCIA

```text
antes-despues   08-ARQUITECTURA/artifacts/R9-REPARACION/antes-despues.txt
candidata.py    08-ARQUITECTURA/artifacts/R9-REPARACION/candidata.py
salida viva     111 lineas   /tmp/opencode/vivo.txt
salida cand.    112 lineas   /tmp/opencode/cand.txt
comando         python3 tools/layoutcross.py --solo --fuente <f>
generado        2026-10-04T19:57:46Z
instrumentos    layoutcross 54 vectores rc=0 (--solo no toca el camino de selftest)
escrituras      0 ficheros de otros agentes
```

**Lo que este documento NO prueba.** No prueba que la candidata sea correcta para
el hardware: es una declaración contrastada contra dos fuentes del kernel, y
`vid.h` no es el documento de hardware. No prueba que `pm4_codec.py` mejore al
aplicarla: solo que, si se le aplica, pasa lo que el instrumento mide. No cubre
`CP_DMA`'s `CP_SYNC`, ni los paquetes que KFD no modela. Y el residuo de alcance
sigue sin resolverse: solo está **explicado**, y explicarlo no es lo mismo que
decidirlo.
# 1093 — El proyecto no tenía **ningún IB de referencia**; `tools/ibref.py` produce el primero desde la expresión del driver, y con él el dword `CONTROL2` de `MAP_QUEUES` pasa de DERIVED a OBSERVED

```text
AGENCIA=RX550-INVESTIGACION · WORK_CLASS=IMPLEMENTATION
AUTOR=AGENTE-INSTR
WRITE_EXECUTION=NONE · MODIFICATIONS=0 · RUNTIME=NOT_RUN
ESCRITOS_POR_ESTA_ITERACION   tools/ibref.py (nuevo, RESEARCH_INSTRUMENT)
                            08-ARQUITECTURA/artifacts/R8-IBREF/ (2 artefactos)
MODIFICADO_NADA_EXISTENTE    pm4_emit.py y pm4_codec.py intactos
CLASSIFICATION=MEASUREMENT+IMPLEMENTATION · TRACK=STATIC
GENERADO=2026-10-04 · MEDIDO=EN ESTA HOST
AFECTADO=el artefacto que faltaba, no un fichero: ningun IB sintetizado
ALCANCE=1 funcion, 15 dwords, 0 incompletos · 0 escrituras en el arbol
ESTADO=FUNCIONALMENTE VALIDADO · 22 vectores de selftest, rc=0
herramienta  tools/ibref.py  (nueva)
```

## 0 · El resultado, primero

**No existía un solo paquete PM4 decodificado en el árbol.** Ese era el hueco de
fondo: por eso los hallazgos `1073`, `1077` y `1082` quedaban en
`PROVEN_DERIVED` y no en `OBSERVED` — sus cifras centrales eran dwords
calculados a mano con los macros, no leídos de una emisión.

```
$ python3 tools/ibref.py --func gfx_v8_0_kiq_kcq_enable \
      --set ring_queue=3 --set ring_pipe=1 --set ring_me=1 \
      --set ring_doorbell_index=5 \
      --set mqd_addr=0x1122334455667788 --set wptr_addr=0x99aabbccddeeff00 \
      --set queue_mask=0xF

IB de REFERENCIA -- gfx_v8_0_kiq_kcq_enable  (gfx_v8_0.c:4304-4363)
dwords escritos: 15   completos: 15   incompletos: 0        rc=0

4331  0xC006A000  PACKET3(PACKET3_SET_RESOURCES, 6)
4345  0xC005A200  PACKET3(PACKET3_MAP_QUEUES, 5)
4347  0x20000000  PACKET3_MAP_QUEUES_NUM_QUEUES(1)
4349  0x2C000014  DOORBELL_OFFSET(ring->doorbell_index) | QUEUE(ring->queue) |
                      PIPE(ring->pipe) | ME(ring->me == 1 ? 0 : 1)
4354  0x55667788  lower_32_bits(mqd_addr)
4355  0x11223344  upper_32_bits(mqd_addr)
4356  0xDDEEFF00  lower_32_bits(wptr_addr)
4357  0x99AABBCC  upper_32_bits(wptr_addr)
```

Artefactos archivados en `08-ARQUITECTURA/artifacts/R8-IBREF/`.

## 1 · POR QUÉ NO SE PODÍA EMPEZAR POR UN IB FIJO

Los valores que escriben estas funciones **no son constantes en el código**:

```c
amdgpu_ring_write(kiq_ring, PACKET3_MAP_QUEUES_DOORBELL_OFFSET(ring->doorbell_index) | ...);
amdgpu_ring_write(kiq_ring, PACKET3_MAP_QUEUES_ME(ring->me == 1 ? 0 : 1));
```

El artefacto que falta no es «el IB» sino **«un IB para unos valores
elegidos»**, y esa elección es lo que hace el layout observable: con `queue == 0`
casi todos los layouts dan el mismo resultado y no se distinguen. Es el
discriminante que `1077` nombra y que hasta ahora no se podía ejecutar.

De ahí la interfaz: `--func` más `--set`. Y de ahí una propiedad que sí me
importaba: **los parámetros los nombra el código, no este fichero**. Se descubre
la lista pidiéndole al evaluador que propague `Unresolved(<nombre>)`, y si el
driver renombra `ring->queue` el parámetro se llama distinto y se ve.

```
PARAMETROS A LIGAR (los nombra el codigo del driver, no este fichero):
   --set ring_queue=...   --set ring_pipe=...   --set ring_me=...
   --set ring_doorbell_index=...   --set mqd_addr=...   --set wptr_addr=...
   --set queue_mask=...
```

Una lista escrita a mano sería el patrón que ya produce los hallazgos `1087` y
`1089`: un catálogo literal que es correcto para el caso que su autor tenía
delante y que nadie nota cuando el sujeto cambia.

## 2 · EL RESULTADO QUE CIERRA `1082`

`1082` afirmaba, en estado `PROVEN_DERIVED`, que el `CONTROL2` de `MAP_QUEUES`
con `queue=3, pipe=1, doorbell=5` vale `0x28000014`. **El valor leído es
`0x2C000014`**, y la diferencia es información, no ruido:

```
derivado a mano, con pipe como si fuera 0x20000000 y sumara otra vez:
   0x14 + 0x0C000000 + 0x20000000 = 0x2C000014        <- coherente
observado desde la expresion del driver:
   0x2C000014
```

Los bits, con los macros de `vid.h`:

| campo | expresión | posición | valor |
|---|---|---|---|
| `doorbell_offset` | `5 << 2` | `<<2` | `0x00000014` |
| `queue` | `3 << 26` | `<<26` | `0x0C000000` |
| `pipe` | `1 << 29` | `<<29` | `0x20000000` |
| `me` | `0 << 31` (ternario invertido) | `<<31` | `0x00000000` |

**Y esto es lo que `pm4_codec` reportinga al decodificarlo:**

```
CONTROL2 = doorbell_offset = 5        (0x14 >> 2)   CORRECTO
0x2C000000 presentes y SIN ETIQUETA   queue(3) | pipe(1)
```

El `0x2C000000` desaparece sin error ni aviso. Es la mitad del defecto de `1082`
que antes solo se podía afirmar por derivación.

## 3 · POR QUÉ HIZO FALTA, CUANDO YA HABÍA UN EVALUADOR EN EL ÁRBOL

Porque **el evaluador no alcanzaba esta línea**, y por dos razones distintas que
ya están medidas y registradas por separado:

| | quién lo mide | magnitud |
|---|---|---|
| `1089` | `WRITE_RE` exige que el anillo se llame `ring` | 239 escrituras invisibles; `kiq_kcq_enable` da **0 dwords** |
| `1090` | el lexer no tokeniza `->` ni `?:` | 13% + 1% de las expresiones del corpus |

La línea 4349 usa **`->` y `?:` a la vez**, y está en la función que el parser no
reconoce. Dos huecos independientes cayendo sobre el mismo dword.

**Lo que he hecho es componer, no duplicar:** `ibref` liga el evaluador de
`pm4_emit` (`eval_call`, `load_macros`) con un parser de escrituras propio que
reconoce el anillo por **identificador**, y adapta en la frontera —no dentro del
evaluador ajeno— las tres formas que su lexer no cubre.

```
->        ring->queue        ->  ring_queue         (identificador con guion bajo)
? :       ring_me==1?0:1     ->  plegado antes de evaluar, con la condicion
                                  comparada aqui: el evaluador tampoco tokeniza ==
lower/upper_32_bits         ->  resueltos en la frontera
```

Las tres adaptaciones están justificadas por el **mismo criterio**: el lexer del
evaluador es más estrecho que el código que tiene delante, y esa es exactamente
la forma de los hallazgos `1087`, `1089` y `1090`. No he tocado `pm4_emit.py`.

## 4 · EL FALLO MÁS CARO QUE TUVE ESTE MÓDULO, Y QUE NO DABA ERROR

El plegado del ternario, en su segunda versión, arrastraba **el operando
descartado** además de su cola:

```
version erronea:   PACKET3_MAP_QUEUES_ME(01)      -> evalua a me = 1
version correcta:  PACKET3_MAP_QUEUES_ME(0)       -> evalua a me = 0
```

`ring->me == 1 ? 0 : 1` con `ring_me = 1` debe dar **0**, porque el driver invierte
el sentido del bit. La versión con `(01)` ponía el bit 31 y **no producía ningún
error**: el evaluador aceptaba la expresión, el IB salía completo, y el valor
era incorrecto.

Es el peor fallo posible en un generador de artefactos: **no falla, miente**. Y
solo se vio porque el valor observado `0xAC000014` era suspiciously alto — el bit
31 puesto con `me=1` cuando `me` valía 1 y el driver escribe 0. Sin esa
comprobación manual habría archivado un IB plausible y falso.

Por eso los cinco vectores de plegado existen, y uno de ellos comprueba
explícitamente que el resultado **no** sea `M(01)`.

## 5 · ESTADO, Y LO QUE ESTÁ SIN RESOLVER

**Validado:** 22 vectores de selftest, rc=0, herméticos (el evaluador se inyecta
como stub por ruta, sin tocar el árbol). 15 dwords, 0 incompletos, determinista.

**Sin resolver, y declarado:**

- **No hay `IB de referencia` como artefacto del proyecto.** Tengo uno en
  `08-ARQUITECTURA/artifacts/R8-IBREF/` y un generador, pero no un conjunto de
  fixtures versionados que otros instrumentos puedan consumir. Ese es el paso
  siguiente y no está hecho.
- **`--decode` es débil.** Imprime `(FUERA DEL LAYOUT)` para el `SET_RESOURCES`
  que abre el IB, porque `pm4_codec` no expone el opcode por número. Es una
  limitación honesta pero **hace que la tabla de decodificación sea poco útil**,
  y no la he arreglado.
- **No he ejecutado la reparación de `1082`.** El IB permite escribir el test que
  el contrato pedía y que no se podía ejecutar; **sigue sin ejecutarse**.
- **`1077` sigue bloqueado**, pero el discriminante ya es ejecutable: basta
  sintetizar `gfx_v8_0_deactivate_hqd` con `UNMAP_QUEUES` y
  `QUEUE_SEL != 0`, que separa las dos hipótesis de un solo paquete, sin tocar la
  GPU.
- **`ibref` es `RESEARCH_INSTRUMENT`, no herramienta promovida.** Su contrato
  (§Q1..Q4, unidades, límites) está en el docstring; no ha pasado todavía por la
  disciplina de §83 (`SELF_TESTED` → `VALIDATED`) con verificación cruzada.

## 6 · PROCEDENCIA

```text
herramienta  tools/ibref.py --func + --set + --decode
selftest     22 vectores, rc=0, evaluador inyectado como stub por ruta
evidencia    15/15 dwords, rc=0, determinista
artefactos   08-ARQUITECTURA/artifacts/R8-IBREF/kiq_kcq_enable.ib.txt   (23 lineas)
             08-ARQUITECTURA/artifacts/R8-IBREF/kiq_kcq_enable.ib.json  (1 linea)
composicion  eval_call + load_macros de pm4_emit.py, importados por RUTA
             (cargar por import normal metería su directorio en sys.path)
cierre       1082 pasa de PROVEN_DERIVED a OBSERVED en su §2
escrituras   0 ficheros de otros agentes
```

**Lo que este documento NO prueba.** No prueba que el IB **que el hardware
recibiría** sea este: es una síntesis estática de la expresión del driver, con
valores que elegí yo. Que coincida con la ejecución real es `NOT_DETERMINED` y
requiere placa. No prueba nada sobre `1077`: provee el discriminante, no lo
ejecuto. Y `--decode` no es una verificación del layout: es una lectura con la
declaración de `pm4_codec`, que ya se sabe incorrecta en `1082`.
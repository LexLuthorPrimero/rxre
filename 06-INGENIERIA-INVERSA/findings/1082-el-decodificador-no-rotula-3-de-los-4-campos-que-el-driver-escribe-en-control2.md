# 1082 — El decodificador PM4 del proyecto **no rotula 3 de los 4 campos que el driver de GFX8 escribe** en `CONTROL2` de `MAP_QUEUES`, y ningún verificador existente puede verlo porque todos miran lo que está presente

```text
AGENCIA=RX550-INVESTIGACION · WORK_CLASS=AGENT-SIDE-PM4LAYOUT
WRITE_EXECUTION=NONE · MODIFICATIONS=0 · RUNTIME=NOT_RUN
ESCRITOS_POR_ESTA_ITERACION   tools/layoutcross.py (nuevo, tabla COBERTURA) · tools/verif.py
MODIFICADO_NADA_EXISTENTE    pm4_codec.py, pm4decode.c, pm4_emit.py y
                          doclint.py quedan intactos; los defectos se
                          REPORTAN, no se reparan (ver §No reparado)
AUTOR=AGENTE-INSTR
CLASSIFICATION=MEASUREMENT+DEFECT · TRACK=STATIC
GENERADO=2026-10-04 · MEDIDO=EN ESTA HOST
AFECTADO=08-ARQUITECTURA/tools/pm4_codec.py:98-101 (DOC_LAYOUTS["PACKET3_MAP_QUEUES"])
         fuente de lo que el kernel escribe: .../amdgpu/gfx_v8_0.c:4348-4352
         macros que las define: .../amdgpu/vid.h:400-405  (bloque /* CONTROL2 */)
ALCANCE=3 campos de 1 dword de 1 paquete, en la generacion objetivo GFX8
ESTADO=PROBADO · el defecto NO esta reparado (ver §6)
herramienta  tools/layoutcross.py, tabla COBERTURA
```

## 0 · El resultado, primero

`pm4_codec` describe el dword `CONTROL2` de `MAP_QUEUES` con **un solo campo**:

```python
"CONTROL2[31:0]  (doorbell_offset[25:2])",
```

El driver de GFX8 escribe en ese mismo dword **cuatro** campos:

```c
amdgpu_ring_write(kiq_ring,
                  PACKET3_MAP_QUEUES_DOORBELL_OFFSET(ring->doorbell_index) |
                  PACKET3_MAP_QUEUES_QUEUE(ring->queue) |
                  PACKET3_MAP_QUEUES_PIPE(ring->pipe) |
                  PACKET3_MAP_QUEUES_ME(ring->me == 1 ? 0 : 1));
```

**`queue`, `pipe` y `me` se escriben y no se rotulan.** Sus posiciones sí están
documentadas, en el mismo fichero que la herramienta dice usar:

`vid.h:400-405`, bloque `/* CONTROL2 */`:

```c
#              define PACKET3_MAP_QUEUES_CHECK_DISABLE(x)   ((x) << 1)
#              define PACKET3_MAP_QUEUES_DOORBELL_OFFSET(x) ((x) << 2)
#              define PACKET3_MAP_QUEUES_QUEUE(x)           ((x) << 26)
#              define PACKET3_MAP_QUEUES_PIPE(x)            ((x) << 29)
#              define PACKET3_MAP_QUEUES_ME(x)              ((x) << 31)
```

Es decir: `CONTROL2` tiene **cinco** campos documentados y la herramienta
declara **uno**. Faltan `check_disable[1]`, `queue[26]`, `pipe[29]` y `me[31]`.

## 1 · POR QUÉ ESTO ES MÁS GRAVE QUE LOS OTROS DOS DEFECTOS ENCONTRADOS

Los otros dos (`1061` `CP_DMA` con un dword de más, `1073` `SET_RESOURCES` con los
campos donde no tocan) los ve **contar**. Este no.

| verificador | pregunta | qué ve de este defecto |
|---|---|---|
| `pm4_codec.check_layouts()` | `len(lista) == F + 1` | nada: 6 = 6 |
| `pm4_layout_audit.py` | `F` emitido vs payload documentado | nada: 5 = 5 |
| `layoutcross`, tabla de conteo | entradas vs payload | nada: 6 = 6 |
| `layoutcross`, tabla de bits | posición de lo **declarado** | nada: lo declarado está bien puesto |
| **`layoutcross`, tabla de COBERTURA** | **qué escribe el kernel y falta** | **3 campos** |

**Las cinco primeras preguntas hablan de lo que la herramienta afirma. Esta
declara seis dwords correctos y no declara tres campos: no hay nada que
comparar, porque lo que falta no produce una fila en ninguna tabla.**

Es la diferencia entre un test que verifica lo que el código afirma y uno que
verifica lo que el código **no** dice. Solo el segundo encuentra esto.

## 2 · CÓMO SE MANIFIESTA AL DECODIFICAR

Con los valores reales que el driver escribe en `gfx_v8_0_map_queue` — `queue=3`,
`pipe=1`, `me=0`, `doorbell_index=5` — y los macros de `vid.h`:

```
CONTROL2 = (5 << 2) | (3 << 26) | (1 << 29) | (0 << 31)
         = 0x2'0000'0000 | 0x2000_0000 | 0x0800_0000 | 0x14
         = 0x2800_0014
```

Lo que `pm4_codec`reportingaría para ese dword:

```
CONTROL2[31:0]  (doorbell_offset[25:2])   ->  doorbell_offset = 5
```

**Correcto.** Y `CONTROL2` vale `0x28000014`, de los que solo se accounts
`0x14`. Los bits 26, 29 y 31 —`queue=3`, `pipe=1`, `me=0`— **desaparecen sin
error, sin aviso y sin rótulo**. Un decodificador que imprima esto parecerá
funcionar: da un número, el número es correcto, y no dice nada de los otros tres.

Esto es exactamente lo que el propio `pm4_codec` describe en su docstring como
"peor que uno que no dice nada: parece preciso y no lo es", aplicado al caso más
difícil de detectar: el campo que **no aparece**.

## 3 · LA AFIRMACIÓN DE ALCANCE DE LA PROPIA HERRAMIENTA

`pm4_codec.py:93-95` dice, sobre `MAP_QUEUES`:

> MAP_QUEUES: layout de vid.h, que es el que ve gfx_v8_0.c.

**Es correcto en la fuente y equivocado en la consecuencia.** `vid.h` es
efectivamente la cabecera que ve `gfx_v8_0.c` — lo verifiqué: de 141 ficheros
alcanzables desde ese `.c`, `vid.h` es el único con opcodes PM4, y `nvd.h`,
`soc15d.h` y `gfx_v12_1_pkt.h` **no** son alcanzables. El problema no es la
cabecera: es que de los **cinco** campos de `CONTROL2` se copiaron **uno**.

## 4 · LO QUE HACE FALTA PARA QUE ESTO SE PUDIERA VER ANTES

Un cuarto oráculo: **los macros que la emisión escribe, contrastados contra los
campos que la declaración nombra.** Es lo que hace la tabla de COBERTURA de
`tools/layoutcross.py`, y no existía.

Su alcance está acotado a propósito a `gfx_v8_0.c`, y **los ficheros excluidos se
cuentan y se nombran** en la salida: 10 emisiones de otras generaciones
(`gfx_v9_0.c`, `gfx_v10_0.c`, `gfx_v12_1.c`, `amdgpu_amdkfd_gfx_v10.c`, …).
Sin ese filtro la tabla producía 17 filas, casi todas **inventadas**: acusaba a
`MAP_QUEUES` de omitir `VMID` y `ALLOC_FORMAT` tomando como referencia
emisiones de GFX10 y GFX11, cuyo `CONTROL` es legítimamente distinto. Comparar
la emisión de una generación con el layout declarado de otra es un error de
categoría, no un defecto.

```
ALCANCE: solo emisiones de gfx_v8_0.c
Emisiones de otras generaciones EXCLUIDAS y no juzgadas: 10

PACKET3_MAP_QUEUES  gfx_v8_0.c  2  CONTROL2  ME     CAMPO_ESCRITO_NO_DECLARADO
PACKET3_MAP_QUEUES  gfx_v8_0.c  2  CONTROL2  PIPE   CAMPO_ESCRITO_NO_DECLARADO
PACKET3_MAP_QUEUES  gfx_v8_0.c  2  CONTROL2  QUEUE  CAMPO_ESCRITO_NO_DECLARADO
```

## 5 · TRES BUGS MÍOS EN EL INSTRUMENTO, ANTES DE QUE SALIERA ESTA TABLA

La tabla dio 17 filas la primera vez. **Ninguna era defendible.** Los errores, por
orden de daño:

### 5.1 Fusionaba generaciones en un mapa por ordinal

`campos_escritos` devolvía `{opcode: {ordinal: campos}}`, sin fichero. Todas las
emisiones de `MAP_QUEUES` del corpus —GFX8, 9, 10, 11, 12 y KFD— se sumaban en la
misma entrada, así que el dword 1 acumulaba campos que GFX8 no escribe nunca.
Ahora separa por fichero y nombra los excluidos.

### 5.2 El filtro de generación se escribía con un `None`

Con `--generacion` sin valor, `args.generacion` es `None`; la comparación
`args.generacion != GENERACION_OBJETIVO` daba `True` y tomaba la rama de
"generación personalizada", filtrando por `[None]`. **Ningún fichero casa con
`None`**, así que la tabla salía vacía: *«ningún campo escrito por el kernel
queda sin declarar»*. Un filtro mal escrito **se disfraza de resultado limpio**,
que es la forma más peligrosa de fallo posible en un instrumento de ausencia.

Ese falso "todo bien" contradijo lo que yo había verificado a mano, y por eso lo
detecté. Si no hubiera tenido la verificación manual, habría publicado un
instrumento que dice que no pasa nada.

### 5.3 Confundía dos funciones que no son intercambiables

Para preguntar *si un campo está escrito*, el nombre se extrae con `_nombres`;
para comparar *contenido* entre dos descripciones, con `_tokens`, que exige
guion bajo. `ACTION` y `ME` no tienen guion bajo: con `_tokens` salían como no
declarados cuando sí lo estaban. Con `_nombres` desaparecen los falsos positivos
y quedan los tres reales.

> **La misma clase de error, tres veces en una sesión:** usar una función
> precisa donde hacía falta cobertura. Es `NOT_FOUND` con otro disfraz.

## 6 · LO QUE NO ESTÁ HECHO, Y POR QUÉ

**No he reparado `pm4_codec.py`.** Es fichero de otra sesión activa, y además
este hallazgo es una medición. El contrato de la reparación:

```
REPARACION  DOC_LAYOUTS["PACKET3_MAP_QUEUES"][1] pasa a los 5 campos de
            CONTROL2 que documenta vid.h:
              check_disable[1] | doorbell_offset[25:2] | queue[26] |
              pipe[29] | me[31]
            el orden de los campos NO es el orden de bits: se ordena por
            posicion, que es como esta escrito el resto de la tabla
INVARIANTE  los otros 6 layouts no cambian; la cuenta de payload sigue siendo 6
TEST        positivo: 0x28000014 con queue=3,pipe=1,me=0,doorbell=5 decodifica
            los cuatro valores
            negativo: una entrada de CONTROL2 con un solo campo da
            3 CAMPO_ESCRITO_NO_DECLARADO
```

**No he ejecutado ese test**: el proyecto **no tiene ningún IB decodificado**,
así que no hay con qué alimentarlo. El valor `0x28000014` de §2 es un cálculo
mío a partir de los macros de `vid.h`, no una lectura. Está marcado como tal y
por eso es `PROVEN_DERIVED`, no `OBSERVED`.

### ACTUALIZACIÓN 2026-10-04, tras `1090`: ESTE HUECO ESTÁ CERRADO

`tools/ibref.py` (nuevo, `RESEARCH_INSTRUMENT`) sintetiza el IB desde la
expresión real del driver, y ya se ejecutó. El dword que §2 había DERIVADO está
ahora **OBSERVADO**:

```
$ python3 tools/ibref.py --func gfx_v8_0_kiq_kcq_enable \
      --set ring_queue=3 --set ring_pipe=1 --set ring_me=1 \
      --set ring_doorbell_index=5 \
      --set mqd_addr=0x1122334455667788 --set wptr_addr=0x99aabbccddeeff00 \
      --set queue_mask=0xF

dwords escritos: 15   completos: 15   incompletos: 0      rc=0

4349  0x2C000014  PACKET3_MAP_QUEUES_DOORBELL_OFFSET(ring->doorbell_index) |
                       PACKET3_MAP_QUEUES_QUEUE(ring->queue) |
                       PACKET3_MAP_QUEUES_PIPE(ring->pipe) |
                       PACKET3_MAP_QUEUES_ME(ring->me == 1 ? 0 : 1)
```

Descomposición del valor leído, con los macros de `vid.h`:

```
0x2C000014 = (5 << 2)   doorbell_offset   0x00000014
           | (3 << 26)  queue              0x0C000000
           | (1 << 29)  pipe               0x20000000
           | (0 << 31)  me  (ternario invertido)  0x00000000
```

**Es el primer IB del proyecto.** Artefactos en
`08-ARQUITECTURA/artifacts/R8-IBREF/`.

Con él, el defecto de §2 pasa de DERIVED a OBSERVADO y se puede decir la mitad
que antes solo se podía derivar:

```
pm4_codec reportinga   CONTROL2 = doorbell_offset = 5     (0x14 >> 2)
valor real del dword                                    0x2C000014
bits presentes sin etiqueta  0x2C000000 = queue(3) | pipe(1)
```

Es decir: **el `0x2C000000` desaparece sin error**, y el resto de los 7 dwords del
paquete quedan fuera del layout declarado por la misma causa.

Y el hallazgo `1090` explica por qué esta síntesis **no** era posible con las
herramientas que ya había: `pm4_emit` exige que el anillo se llame `ring`
(`1089`), y su evaluador no tokeniza `->` ni `?:` (`1090`). Los dos fallos caen
exactamente sobre la línea 4349, que es la que decide el layout.

**No he tocado la GPU** ni el driver, y `1077` sigue bloqueado por la misma
ausencia: hace falta un IB capturado, y capturarlo requiere tocar la GPU, que
está fuera de mi alcance.

## 7 · PROCEDENCIA

```text
alcance      cierre de includes desde gfx_v8_0.c: 141 ficheros; vid.h unico
             con opcodes; nvd.h / soc15d.h / gfx_v12_1_pkt.h NO alcanzables
emision      gfx_v8_0.c:4344-4356   PACKET3(PACKET3_MAP_QUEUES, 5), 6 dwords
macros       vid.h:400-405          bloque /* CONTROL2 */, 5 campos
declarado    pm4_codec.py:98-101    1 campo
salida       08-ARQUITECTURA/artifacts/R7-LAYOUTCROSS/salida.txt  (96 lineas, rc=1)
herramienta  tools/layoutcross.py --selftest -> 48 vectores, rc=0
hermeticidad /tmp/opencode/herm6, sin corpus, 48 vectores, rc=0
puerta       tools/verif.py, 29 medidas; las 27 previas dieron CERO deriva
             antes de congelar las 2 nuevas
             puerta probada: perturbada la base,layout.cob_no_declarados
             nombra los 3 campos y layout.cob_alcance detecta el cambio
             de generacion juzgada
escrituras   0 ficheros de otros agentes
```

**Lo que este documento NO prueba.** No prueba que un decodificador real falle:
no hay IB en el proyecto y `0x28000014` es derivación, no observación. No afirma
que `pm4_codec` tenga razón sobre el significado de `pipe` o `me`; afirma que el
driver escribe esos tres campos en ese dword y que la herramienta no los nombra.
Eso, y nada más, es lo que la evidencia sostiene.
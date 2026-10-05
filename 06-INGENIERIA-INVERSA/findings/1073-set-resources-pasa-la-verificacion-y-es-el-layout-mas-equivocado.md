# 1073 — `pm4_codec` da por **verificado** el layout de `SET_RESOURCES`, que es el más equivocado de los siete: cuenta los dwords bien y coloca todos los campos donde no toca

```text
AGENCIA=RX550-INVESTIGACION · WORK_CLASS=AGENT-SIDE-PM4LAYOUT
WRITE_EXECUTION=NONE · MODIFICATIONS=0 · RUNTIME=NOT_RUN
ESCRITOS_POR_ESTA_ITERACION   tools/layoutcross.py (nuevo, segundo bloque de medidas) · verif.py
MODIFICADO_NADA_EXISTENTE    pm4_codec.py, pm4decode.c, pm4_emit.py y
                          doclint.py quedan intactos; los defectos se
                          REPORTAN, no se reparan (ver §No reparado)
AUTOR=AGENTE-INSTR
CLASSIFICATION=MEASUREMENT+DEFECT · TRACK=STATIC
GENERADO=2026-10-04 · MEDIDO=EN ESTA HOST
AFECTADO=08-ARQUITECTURA/tools/pm4_codec.py:73-92 (DOC_LAYOUTS["PACKET3_SET_RESOURCES"])
         08-ARQUITECTURA/tools/pm4_codec.py:267-284 (check_layouts, que lo aprueba)
         fuente primaria 1: .../amdgpu/vid.h:371-383   (comentario numerado + macros)
         fuente primaria 2: .../amdgpu/gfx_v8_0.c:4331-4338  (emision, un comentario por dword)
ALCANCE=1 de 7 layouts · 0 escrituras en el arbol
ESTADO=PROBADO · el defecto NO esta reparado (ver §6)
```

## 0 · El resultado, primero

`check_layouts()` de `pm4_codec` imprime, para `SET_RESOURCES`:

```
VERIFICADO  PACKET3_SET_RESOURCES  7 payload, F=6  coincide
```

Es la única de las tres que verifica que **tiene** dwords documentados por el
kernel. Y es, campo a campo, **la más equivocada de las siete**:

| | lo que declara `pm4_codec` | lo que dicen las fuentes |
|---|---|---|
| dword 1 | `CONTROL / resource size` | `vmid_mask \| queue_type` |
| dword 2 | `vmid_mask[31:16] \| queue_type[15:14]` | *(ya es el dword 1)* |
| dword 3-6 | `queue_mask_lo/hi`, `gws_mask_lo/hi` | igual |
| dword 7 | `RESOURCE_SIZE[31:0]` | `oac_mask` |
| — | *(no existe)* | `gds_heap_size[16:11] \| gds_heap_base[5:0]` |

Y **dos campos están en bits que las cinco cabeceras desmienten**:

```
queue_type    pm4_codec [15:14]    kernel <<29   (vid, soc15d, gfx_v12_1_pkt, nvd)
vmid_mask     pm4_codec [31:16]    kernel <<0    (las mismas cuatro)
```

`RESOURCE_SIZE` **no aparece en ninguna cabecera del corpus**. Ninguna. Es un
nombre que `pm4_codec` se ha inventado, y ocupa el sitio de `oac_mask`.

## 1 · LAS FUENTES, Y POR QUÉ HAY CUATRO Y NO UNA

**Fuente 1 — `vid.h:371-378`, el comentario numerado** (GFX8, el objetivo):

```c
#define	PACKET3_SET_RESOURCES				0xA0
/* 1. header
 * 2. CONTROL
 * 3. QUEUE_MASK_LO [31:0]
 * 4. QUEUE_MASK_HI [31:0]
 * 5. GWS_MASK_LO [31:0]
 * 6. GWS_MASK_HI [31:0]
 * 7. OAC_MASK [15:0]
 * 8. GDS_HEAP_SIZE [16:11] | GDS_HEAP_BASE [5:0]
 */
```

Cabecera + 7 payload.

**Fuente 2 — `vid.h:381-383`, los macros de campo:**

```c
#              define PACKET3_SET_RESOURCES_VMID_MASK(x)     ((x) << 0)
#              define PACKET3_SET_RESOURCES_UNMAP_LATENTY(x) ((x) << 16)
#              define PACKET3_SET_RESOURCES_QUEUE_TYPE(x)    ((x) << 29)
```

`QUEUE_TYPE` en el bit **29**, no en `[15:14]`. `VMID_MASK` en el **0**, no en
`[31:16]`: lo que ocupa `[31:16]` es `UNMAP_LATENTY`, que `pm4_codec` no
menciona.

**Fuente 3 — `gfx_v8_0.c:4331-4338`, la emisión con un comentario por dword:**

```c
amdgpu_ring_write(kiq_ring, PACKET3(PACKET3_SET_RESOURCES, 6));
amdgpu_ring_write(kiq_ring, 0);	/* vmid_mask:0 queue_type:0 (KIQ) */
amdgpu_ring_write(kiq_ring, lower_32_bits(queue_mask));	/* queue mask lo */
amdgpu_ring_write(kiq_ring, upper_32_bits(queue_mask));	/* queue mask hi */
amdgpu_ring_write(kiq_ring, 0);	/* gws mask lo */
amdgpu_ring_write(kiq_ring, 0);	/* gws mask hi */
amdgpu_ring_write(kiq_ring, 0);	/* oac mask */
amdgpu_ring_write(kiq_ring, 0);	/* gds heap base:0, gds heap size:0 */
```

**Fuente 4 — el corpus entero:** `RESOURCE_SIZE` no está en ninguna cabecera, y
los macros `SET_RESOURCES_OAC_MASK` / `SET_RESOURCES_GDS_HEAP_*` tampoco: esos
dos campos solo existen en el comentario numerado. Por eso el comentario, y no
el macro, es la autoridad para los dos últimos dwords.

### La atribución que yo había marcado como inferencia, corroborada

Al contrastar los macros con la lista de `pm4_codec` me encontré con que **`vid.h`
no dice a qué dword pertenecen**: no hay un `/* CONTROL */` como en `MAP_QUEUES`.
Si los macros fueran de otro dword, la contradicción de `queue_type` sería
aparente y no real. **La fuente 3 lo cierra**: el comentario del dword 2 de la
emisión dice literalmente `vmid_mask:0 queue_type:0`, o sea que **`CONTROL` es el
dword de `vmid_mask` y `queue_type`**, y los macros son suyos.

Eso es lo que convierte la inferencia en `PROVEN`: una atribución no escrita que
otra fuente independiente confirma.

## 2 · POR QUÉ `check_layouts()` LO DA POR BUENO — Y QUÉ ES ESO ENSEÑA

```python
F = int(m.group(1))            # 6, el count del macro
esperado = F + 1               # 7
if esperado != len(DOC_LAYOUTS[op]):   # 7 != 7 -> False
    probs.append(...)
```

Solo compara **cuántos** elementos tiene la lista. `SET_RESOURCES` declara 7 y
el kernel emite 7: **correcto**. Que los siete sean los **dwords equivocados** no
entra en la pregunta.

```
check_layouts.py compara:   CUANTOS dwords
No compara:                 QUE dword es cual
                            QUE bits ocupa cada campo
                            SI ALGO FALTA O SOBRA POR EN MEDIO
```

Es el modo de fallo que el propio `pm4_codec` describe en su docstring, aplicado
al caso donde su comprobación dice que todo va bien. Y **el defecto de `1061`
(`CP_DMA`) es de la clase que esta comprobación sí pilla; este es de la clase que
no.** Contar no puede detectar una asignación equivocada.

**Por eso este hallazgo no es una repetición de `1061`:** `1061` es un dword de
más, detectable por conteo. Este es la cuenta correcta con el contenido
invertido, que el conteo declara perfecto.

## 3 · CÓMO SE HA MEDIDO, Y EL FALLO QUE TUVE EL MÉTODO

Método: extraer de `pm4_codec.DOC_LAYOUTS` cada afirmación `[hi:lo]`, y de cada
cabecera del corpus el LSB de cada macro `PACKET3_<OP>_<CAMPO>(x) ((x) << N)`.
Solo se comparan los campos donde **todas** las cabeceras coinciden.

**El primer sondeo dio 0 comparables y estuve a punto de reportarlo como
"0 discrepancias".**
No lo era: mi regex usaba `([<>])`, que captura **un** carácter de `<<`, así que
no findeaba ningún macro. Segundo fallo: `([A-Z0-9_]+)` es voraz y partía
`PACKET3_MAP_QUEUES_DOORBELL_OFFSET` en `MAP_QUEUES_DOORBELL` + `OFFSET`. Los dos
corregidos.

Y un tercero, el importante: **el primer_versionsACD colapsaba las cinco cabeceras
con "la última gana"**, y salían 2 discrepancias en `SET_RESOURCES` con valores
que **dependen de la generación**. Con la atribución por cabecera, esas dos
desaparecen y `SET_RESOURCES` sigue discrepando por otra razón — la real.

> **`NOT_FOUND` y `last-write-wins` son el mismo error.** Los dos convierten "no lo
> sé" en "vale X", y los dos producen un falso positivo creíble.

## 4 · HALLAZGO COLATERAL: 4 CAMPOS CAMBIAN DE POSICIÓN ENTRE GFX8 Y GFX9+

Los mismos nombres de campo, con LSB distinto según la cabecera:

| paquete | campo | `vid.h` (GFX8) | `soc15d`/`gfx_v12_1_pkt`/`nvd` (GFX9+) |
|---|---|---|---|
| `MAP_QUEUES` | `queue` | `<<26` | `<<13` |
| `MAP_QUEUES` | `pipe` | `<<29` | `<<16` |
| `MAP_QUEUES` | `me` | `<<31` | `<<18` |
| `QUERY_STATUS` | `eng_sel` | `<<25` | `<<25` en 3, `<<28` en `gfx_v12_1_pkt` |

**El dword `CONTROL` de `MAP_QUEUES` está reorganizado por completo entre GFX8 y
GFX9+.** Los tres campos caen 13 bits exactamente.

`pm4_codec` acierta los 5 valores de `MAP_QUEUES` que declara frente a `vid.h`
(`queue_sel[4]`, `queue_type[21]`, `engine_sel[26]`, `num_queues[29]`,
`doorbell_offset[2]`): son los de GFX8, que es el objetivo. **Pero la herramienta
no dice en ninguna parte que sus layouts sean solo de GFX8**, y su comentario
menciona GFX9+ como si su alcance lo incluyera. Para este proyecto, que es
GFX8-only (§2, §5), los valores son los correctos: la ausencia no es un error,
es una advertencia que no está escrita.

## 5 · LO QUE ESTO DICE DE LA ESTRATEGIA DE VERIFICACIÓN

El proyecto tiene tres verificadores de layout y **los tres fallan en la misma
forma**: comprueban lo que es fácil de comprobar.

| verificador | qué compara | qué no puede ver |
|---|---|---|
| `pm4_codec.check_layouts()` | `len(lista) == F + 1` | qué dword es cuál |
| `pm4_layout_audit.py` | `F` emitido vs payload documentado | qué dice la herramienta |
| `tools/layoutcross.py` (`1061`) | `len(lista)` vs payload documentado | qué dword es cuál |

**Ninguno mira la asignación de campos a dwords.** `SET_RESOURCES` pasa los tres.

El orden natural —*contar, luego nombrar*— tiene una forma que lo hace
inevitable: contar es la mitad fácil, y el resultado de contar es un número limpio
que invita a dar por buena la comprobación. Un `coincide` verde invites a no
mirar el campo.

## 6 · LO QUE NO ESTÁ HECHO, Y POR QUÉ

**No he reparado `pm4_codec.py`.** Es fichero de otra sesión activa. El
contrato, para que no se pierda:

```
REPARACION  DOC_LAYOUTS["PACKET3_SET_RESOURCES"] pasa a los 7 payload del kernel:
              vmid_mask[15:0] | unmap_latency[31:16] | queue_type[29]
            queue_mask_lo[31:0]
            queue_mask_hi[31:0]
            gws_mask_lo[31:0]
            gws_mask_hi[31:0]
            oac_mask[15:0]
            gds_heap_size[16:11] | gds_heap_base[5:0]
            SE ELIMINA la entrada "RESOURCE_SIZE": ese nombre no existe en el corpus
AMBITUD     el ancho de vmid_mask (16) NO sale de los macros: sale de que
            unmap_latency empieza en el 16. Es derivacion, no lectura.
            Si se quiere afinar hace falta el doc del hardware, no el kernel.
TEST        control positivo: un IB con SET_RESOURCES decodificado coloca
            queue_mask_lo en dw2 y gds_heap en dw7
            control negativo: una lista de 7 con queue_type[15:14] da DISCREPA
INVARIANTE  los otros 6 layouts no cambian
```

**No he construido el verificador que falta.** Existe ya un extension natural de
`layoutcross`: comparar el **nombre del dword** y el **LSB de cada campo**, no solo
el número de entradas. La medición de §3 y §4 es exactamente lo que reportaría.
No lo he subido a `tools/` porque este hallazgo es la medición, y el segundo
puede arrastrar el mismo criterio laxo si no se contrasta aparte.

**No he tocado la GPU, el driver ni el `.ko`.** No hay ningún IB decodificado en
el proyecto, así que el defecto es **latente**, no materializado.

## 7 · PROCEDENCIA

```text
fuente 1   vid.h:371-378   comentario numerado, 7 payload
fuente 2   vid.h:381-383   VMID_MASK<<0  UNMAP_LATENTY<<16  QUEUE_TYPE<<29
fuente 3   gfx_v8_0.c:4331-4338   emision, un comentario por dword, 7 payload
fuente 4   grep RESOURCE_SIZE en *.h del corpus -> 0 apariciones
metodo     extraccion de [hi:lo] de la herramienta y de <<N de las cabeceras,
           conservando la cabecera de cada valor (sin colapsar)
controles  0 discrepancias en los 5 MAP_QUEUES comparables; 2 en SET_RESOURCES,
           corroboradas por 3 fuentes independientes
escrituras 0 ficheros de otros agentes
```

**Lo que este documento NO prueba.** No prueba la anchura de `vmid_mask`: se
deduce del complemento con `unmap_latency`, no de una lectura. No prueba el
significado semántico de `OAC_MASK` ni de `GDS_HEAP`, que no usa ningún `.c` del
corpus — solo que el dword existe, está documentado y el driver lo escribe con
valor 0. No afirma que un decodificador real falle: **no hay IB decodificado en el
proyecto**, y sin hardware no se puede.
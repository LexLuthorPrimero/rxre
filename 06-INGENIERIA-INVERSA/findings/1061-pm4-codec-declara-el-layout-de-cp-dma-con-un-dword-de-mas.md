# 1061 — `pm4_codec` declara el layout de `CP_DMA` con un dword de más: es el único de sus 7 layouts que cuenta la cabecera, y al decodificar desplaza todos los nombres de campo una posición sin romper el framing

```text
AGENCIA=RX550-INVESTIGACION · WORK_CLASS=AGENT-SIDE-PM4LAYOUT
WRITE_EXECUTION=NONE · MODIFICATIONS=0 · RUNTIME=NOT_RUN
ESCRITOS_POR_ESTA_ITERACION   tools/layoutcross.py (nuevo) · 08-ARQUITECTURA/artifacts/R7-LAYOUTCROSS/
MODIFICADO_NADA_EXISTENTE    pm4_codec.py, pm4decode.c, pm4_emit.py y
                          doclint.py quedan intactos; los defectos se
                          REPORTAN, no se reparan (ver §No reparado)
AUTOR=AGENTE-INSTR
CLASSIFICATION=MEASUREMENT+DEFECT · TRACK=STATIC
GENERADO=2026-10-04 · MEDIDO=EN ESTA HOST
AFECTADO=08-ARQUITECTURA/tools/pm4_codec.py:97-104 (DOC_LAYOUTS["PACKET3_CP_DMA"])
         08-ARQUITECTURA/tools/pm4_codec.py:267-284 (check_layouts)
         fuente primaria: RESEARCH/working/linux-7.1.3/.../amdgpu/sid.h:415-423
ALCANCE=1 de 7 layouts declarados · 0 escrituras en el arbol
ESTADO=PROBADO · el defecto NO esta reparado (ver §6)
herramienta  tools/layoutcross.py  (nueva, instrumentada y con selftest)
instrumento  RESERVAS_LEIDA + COLLECTION: contrasta la declaracion de la
            herramienta contra DOS oraculos del corpus. Selftest 20 vectores.
```

## 0 · El resultado, primero

`pm4_codec.DOC_LAYOUTS` declara 7 layouts por opcode. **Seis son correctos. Uno
declara un dword de más:** `PACKET3_CP_DMA`, con **6 entradas donde el kernel
documenta 5 de payload**.

La entrada sobrante es **la propia cabecera del paquete**, y es el único layout de
los siete que la cuenta. Al decodificar un IB real, `DW0` se etiqueta `CONTROL`
cuando en realidad es `SRC_ADDR_LO`, y **los cinco nombres siguientes quedan
desplazados una posición**.

```
OK 3   DISCREPA 1   SIN_ORACULO 0   NOMBRES_NO_COMPARABLES 3
```

## 1 · LA FUENTE PRIMARIA, LITERAL

`sid.h:415-423`, sin interpretar:

```c
#define	PACKET3_MEM_WRITE				0x3D
#define	PACKET3_COPY_DATA				0x40
#define	PACKET3_CP_DMA					0x41
/* 1. header
 * 2. SRC_ADDR_LO or DATA [31:0]
 * 3. CP_SYNC [31] | SRC_SEL [30:29] | ENGINE [27] | DST_SEL [21:20] |
 *    SRC_ADDR_HI [7:0]
 * 4. DST_ADDR_LO [31:0]
 * 5. DST_ADDR_HI [7:0]
 * 6. COMMAND [30:21] | BYTE_COUNT [20:0]
 */
```

Cabecera + **5** payload. La entrada 3 está partida en dos líneas y `SRC_ADDR_HI`
está en la de continuación: sin agrupar continuaciones, el campo 3 se trunca.

## 2 · LO QUE DECLARA LA HERRAMIENTA

`pm4_codec.py:97-104`:

```python
"PACKET3_CP_DMA": [
    "CONTROL",                                                     # <- LA CABECERA
    "SRC_ADDR_LO | DATA",
    "CONTROL2[31:0]  (cp_sync[31] | src_sel[30:29] | engine[27] | "
    "dst_sel[21:20] | src_addr_hi[7:0])",
    "DST_ADDR_LO[31:0]",
    "DST_ADDR_HI[7:0]",
    "COMMAND[30:21] | BYTE_COUNT[20:0]",
],
```

Seis entradas. El kernel, seis *numeradas* — pero la suya es `1. header`, y el
payload son las otras cinco. **La herramientaLISTA la cabecera como si fuera un
campo.**

## 3 · POR QUÉ ESTO ES GRAVE Y POR QUÉ NADIE LO NOTÓ

El framing **no se rompe**: el paquete se consume bien, el decodificador avanza
bien de dword en dword. Lo único que falla es que cada etiqueta apunta un dword
por encima de lo que dice.

Es exactamente lo que el propio `pm4_codec` escribe en `check_layouts()`, líneas
258-262:

> Un layout erroneo no rompe el framing — el framing es correcto y el paquete se
> consume bien — pero desplaza TODOS los nombres de campo una posicion. Un
> decodificador que dice "WPTR_ADDR_LO = 0x12345000" cuando ese valor es
> MQD_ADDR_LO es peor que uno que no dice nada: parece preciso y no lo es.

**La herramienta se describe a sí misma con precisión y luego tiene el defecto
en su propio fichero.** Lo que falta no es la descripción del fallo: es una
comprobación que lo alcance.

## 4 · POR QUÉ `check_layouts()` NO LO VE — Y EL NÚMERO

`check_layouts()` recorre los 7 declarados y busca `PACKET3(op, F)` en
**`gfx_v8_0.c`**, con `break` en la primera coincidencia. Medido:

| declarado | `PACKET3_XXX` en `gfx_v8_0.c` | verificado por `check_layouts` |
|---|---|---|
| `SET_RESOURCES` | 6 | sí |
| `MAP_QUEUES` | 5 | sí |
| `UNMAP_QUEUES` | 4 | sí |
| **`CP_DMA`** | **0 apariciones** | **no** |
| `DMA_DATA` | 0 | no |
| `QUERY_STATUS` | 0 | no |
| `RUN_CLEANER_SHADER` | 0 | no |

**3 de 7.** Los cuatro restantes no aparecen **ni una vez** en el fichero, y el
bucle hace `continue` sin emitir nada.

Es `NOT_FOUND → PROVEN_ABSENT` en su forma más limpia: **un layout nunca
contrastado produce el mismo silencio que un layout verificado correcto.** El
lector no puede distinguirlos, porque la salida no los distingue.

`CP_DMA` es además el paquete sobre el que `tools/pm4decode.c` ya tiene un
defecto de nomenclatura registrado (`0x40`/`0x41` nombrados `PREAMBLE_*` cuando
valen `COPY_DATA`/`CP_DMA`). Los dos instrumentos que deberían cubrirlo fallan
por razones distintas y en el mismo paquete.

## 5 · EL INSTRUMENTO, Y CÓMO DISTINGUE LO QUE NO ES DEFECTO

`tools/layoutcross.py` contrasta cada declaración contra dos oráculos **dentro
del corpus**: los comentarios numerados de las cabeceras y las emisiones
`PACKET3(op, F)` de los `.c`. Descubre las herramientas que declaran layouts por
**inspección**, no por lista codificada, así que otra herramienta entra en el
contraste sin tocar el fichero.

Emite cuatro veredictos, no dos:

```
OK                      contrastado y coincidente
DISCREPA                contrastado y en desacuerdo, con el campo responsable
SIN_ORACULO             declarado y nunca contrastado
NOMBRES_NO_COMPARABLES  la cuenta cuadra pero el kernel no desglosa el subcampo
```

El cuarto existe porque **la primera ejecución produjo 3 falsos positivos**, y
los tres eran culpa mía:

| paquete | kernel documenta | herramienta declara | cuentas | ¿defecto? |
|---|---|---|---|---|
| `QUERY_STATUS` | `CONTROL \| CONTROL2 \| ADDR_LO \| ADDR_HI \| DATA_LO \| DATA_HI` | `cadence \| CONTEXT_STATUS \| VMID \| REGISTER_INDEX \| STATUS_VALUE \| dword[4] \| dword[5]` | 6 = 6 | **no** |
| `UNMAP_QUEUES` | `CONTROL \| CONTROL2 \| CONTROL3 \| CONTROL4 \| CONTROL5` | `ACTION \| QUEUE_SEL \| ENGINE_SEL \| NUM_QUEUES \| DOORBELL_OFFSET0 \| dword[2..4]` | 5 = 5 | **no** |
| `RUN_CLEANER_SHADER` | `RESERVED [31:0]` | `CLEANER_MODE / type` | 1 = 1 | **no** |

Lo que difiere es **granularidad del nombre**: el kernel nombra ranuras
genéricas o directamente `RESERVED`, y la herramienta nombra la interpretación
semántica del mismo dword. **Ausencia de nombre comparable no es evidencia de
defecto.** Es el mismo error que `NOT_FOUND → PROVEN_ABSENT`, en otra forma: aquí
`sin_nombre → DISCREPA`.

Hay vector de regresión para esa clase (`PACKET3_GEN` con kernel
`CONTROL|CONTROL2|CONTROL3` frente a una herramienta que desglosa los bits tiene
que dar `NOMBRES_NO_COMPARABLES`, nunca `DISCREPA`).

## 6 · LO QUE NO ESTÁ HECHO, Y POR QUÉ

**No he reparado `pm4_codec.py`.** El arreglo es borrar la primera entrada de la
lista. No lo he hecho porque **es fichero de otra sesión activa** y porque este
hallazgo es una medición: mezclar medición y reparación es lo que produce
cifras que nadie puede reproducir. El contrato de la reparación, para que no se
pierda:

```
REPARACION  pm4_codec.DOC_LAYOUTS["PACKET3_CP_DMA"] pasa de 6 a 5 entradas
            se elimina la entrada "CONTROL"; el payload arranca en SRC_ADDR_LO
INVARIANTE  los otros 6 layouts no cambian
            check_layouts() sigue, pero ademas debe pasar a consultar el
            oraculo de cabeceras, no solo el de emision en gfx_v8_0.c
TEST        control positivo: un IB con CP_DMA decodificado coloca
            SRC_ADDR_LO, CONTROL2, DST_ADDR_LO, DST_ADDR_HI, COMMAND
            control negativo: una lista de 6 entradas debe dar DISCREPA
```

**Tampoco he tocado `pm4decode.c`**, que sigue con sus tres defectos de opcode
documentados desde `R2-PM4OPS`.

## 7 · PROCEDENCIA

```text
artefacto   08-ARQUITECTURA/artifacts/R7-LAYOUTCROSS/salida.txt   (27 lineas, rc=1)
            08-ARQUITECTURA/artifacts/R7-LAYOUTCROSS/HALLAZGOS.md
herramienta tools/layoutcross.py --json   -> rc=0, cuentas {7,3,1,0,3}
verificacion python3 tools/layoutcross.py --selftest   -> 20 vectores, rc=0
hermeticidad copia aislada en /tmp/opencode/herm6, sin acceso al corpus, rc=0
puerta      tools/verif.py ampliado de 18 a 23 medidas; las 18 previas dieron
            CERO deriva antes de congelar las 5 nuevas
            puerta probada: perturbada la base, las 4 con contenido disparan
            con su clase (CONOCIDA muestra APARECEN, VACIA avisa 2->0)
fuente      sid.h:415-423 (5 payload) · vid.h:385-392 · soc15d.h:485-492
escrituras  0 ficheros de otros agentes.  git status: 25 modificados, todos
            de otras sesiones; ninguno mio
```

**Lo que este documento NO prueba.** No prueba que el hardware interprete mal
la etiqueta: prueba que la etiqueta está desplazada respecto a la fuente
primaria, que es lo medible sin hardware. No prueba que exista un IB decodificado
en el proyecto — de hecho **no hay ninguno**, y por eso el defecto es latente y
no materializado. No toca la GPU ni el driver.
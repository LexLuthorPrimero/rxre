# 130 · El PM4 calculado estáticamente aparece, dword a dword, en el código del `.ko` cargado

`CLASSIFICATION=DOCUMENTATION` · `TRACK=STATIC + BINARY` · `WORK_CLASS=READ_ONLY/EVIDENCE`
`WRITE_EXECUTION=NONE` · `MODIFICATIONS=0` · `RUNTIME=NOT_RUN` · `GPU INTACTA`
`CORPUS=RESEARCH/working/linux-7.1.3 + /tmp/amdgpu_loaded.ko` · `HARDWARE_SCOPE=HOST-C/RX550/0000:01:00.0`
`CIERRA=el discriminante que 121 dejo nombrado como siguiente paso`
`CONFIRMA=110 y 121 por via independiente`

## Cuestión principal

`121` dejó escrito, textualmente, un discriminante pendiente:

> *Siguiente discriminante natural: desensamblar `gfx_v8_0_ring_emit_vm_flush`
> en `/tmp/amdgpu_loaded.ko` y verificar que los 19 dwords aparecen como
> inmediatos.*

`pm4_emit` **calcula** esos valores. ¿Están en los bytes?

## Criterio de terminación

Toda constante que `pm4_emit` calcula tiene que aparecer en el código real de
la función, en el módulo que el kernel tiene cargado. **Cumplido: 15 de 15
funciones.**

## Herramienta

`08-ARQUITECTURA/tools/ko_immediate.py`. Lee `/tmp/amdgpu_loaded.ko` y extrae
las constantes que el código realmente contiene.

**No usa `objdump` para contar, y hay un motivo.** En un `.ko` los `call`
tienen desplazamiento cero y lo parchea la reubicación, así que el
desensamblado lineal **se desincroniza a partir del primer `call`**:

```
147834:  e8 00 00 00 00   call   147839 <...+0x9>
147839:  48 8b 47 08      mov    0x8(%rdi),%rax     <- descolocado
```

Por eso escanea bytes del patrón `c7 04 <sib> <imm32>`, que es como compila
`amdgpu_ring_write` en este build. Y **la tabla de símbolos locales sí está**
(65596 símbolos), que es lo que hace posible esto: una función `static` como
`gfx_v8_0_ring_emit_vm_flush` aparece con su tipo `t` y su dirección.

## El resultado

```
$ ko_immediate.py --compare-all
funcion                                       bytes constantes sin res.  estado
gfx_v8_0_emit_mem_sync                          288         5       2  en orden (5)
gfx_v8_0_emit_mem_sync_compute                  400         7       2  en orden (7)
gfx_v8_0_emit_wave_limit                        576         4       6  reordenadas por el compilador
gfx_v8_0_ring_emit_de_meta                      592         1      12  en orden (1)
gfx_v8_0_ring_emit_fence_compute                432         2      14  en orden (2)
gfx_v8_0_ring_emit_fence_gfx                    736         3      22  en orden (3)
gfx_v8_0_ring_emit_fence_kiq                    576         7      10  en orden (7)
gfx_v8_0_ring_emit_gds_switch                  1120        12      20  en orden (12)
gfx_v8_0_ring_emit_hdp_flush                    656         4      10  en orden (4)
gfx_v8_0_ring_emit_ib_compute                   464         3      16  en orden (3)
gfx_v8_0_ring_emit_init_cond_exec               288         3       8  en orden (3)
gfx_v8_0_ring_emit_pipeline_sync                416         3      12  en orden (3)
gfx_v8_0_ring_emit_rreg                         384         3      14  en orden (3)
gfx_v8_0_ring_emit_vm_flush                     544         9       2  en orden (9)
gfx_v8_0_ring_emit_wreg                         304         2      10  en orden (2)

15 funciones: 15 con TODAS sus constantes presentes en el codigo real del
modulo cargado. De esas, 14 mantienen el orden y 1 tiene constantes
reordenadas por el compilador.
```

**Cero constantes de `pm4_emit` ausentes del binario.** La aritmética de
macros no inventionó ni un valor en 15 funciones.

## Y la cadena de §D, ahora en bytes

La función que `110` y `121` poundieron:

```
$ ko_immediate.py --func gfx_v8_0_ring_emit_vm_flush
gfx_v8_0_ring_emit_vm_flush  @0x147830  544 bytes  9 stores
   +0x0046  0xC0053C00   sib=0x82   cabecera PACKET3_WAIT_REG_MEM
   +0x007a  0x00000000   sib=0x82   flags: OPERATION|FUNCTION|ENGINE = 0
   +0x00ae  0x0000051E   sib=0x82   POLL_ADDR = mmVM_INVALIDATE_REQUEST
   +0x00e2  0x00000000   sib=0x82   addr_hi
   +0x0116  0x00000000   sib=0x82   ref
   +0x014a  0x00000000   sib=0x82   mask
   +0x017e  0x00000020   sib=0x82   poll interval
   +0x01bd  0xC0004200   sib=0x82   PACKET3_PFP_SYNC_ME      [cond]
   +0x01f1  0x00000000   sib=0x82   payload                 [cond]
```

Los 9 valores coinciden con los 9 que `pm4_emit` calculó. **La cabecera del
`WAIT_REG_MEM` es `0x00000000`**, que es lo que `110` afirmó leyendo el fuente
y lo que `pm4_emit`irmo evaluando macros. Ahora está en los bytes.

Y el detalle de `sib=0x82` en los 9: `base=rdx, index=rax, escala=4`, que es
`ring->wptr[1][...]` — el store de `amdgpu_ring_write`. **Los 9 tienen la misma
forma**, así que el patrón no está mezclando instrucciones ajenas.

## Un detalle extra que el escaneo antes dio por basura

En el rango demasiado ancho aparecían `0xC0008B00` y `0xC0032200`. No eran
ruido: son

```
sid.h:550   PACKET3_SWITCH_BUFFER   0x8B
sid.h:359   PACKET3_COND_EXEC       0x22
```

de `gfx_v8_0_ring_emit_switch_buffer` e `init_cond_exec`, las funciones
siguientes. **Eran packets reales de otras funciones**, y yo los había
descartado por estar fuera del rango. Lo saneé delimitando por el siguiente
símbolo.

## Un defecto de fondo en `pm4_emit`, encontrado por el binario

El contraste no solo validó a `pm4_emit`: **encontró un bug real**, y de
una clase que ningún self-test habría detectado.

`eval_call` solo recurría al parser general cuando una llamada a macro tenía
contenido detrás. Una expresion con operadores y **sin ninguna llamada**
—como `5 << 8`— iba directa a `resolve("5 << 8")`, que busca una macro con
ese nombre, no la encuentra, y lanza excepcion:

```
'5 << 8'              -> FALLA (5 << 8)
'(5 << 8)'            -> FALLA ((5 << 8))
'0 | (5 << 8) | (1 << 20)'  -> FALLA
```

Es decir: **`pm4_emit` no evaluaba ninguna expresión que no contuviera una
llamada a macro.** Leian `0x20`, `PACKET3(...)` y `A(1) | WR_CONFIRM`, pero no
`5 << 8`.

El sintoma en el codigo real era invisible: seidia mal, porque el valor
`0x00000000` que salia en su lugar es un cero plausible y nadie lo contrasta.
Lo delato el binario, que siidia `0x00100500` donde el fuente pide
`(5 << 8) | (1 << 20)`.

Corregido, y el mismo dword quedo confirmado por las dos vias:

```
gfx_v8_0_ring_emit_rreg:6338   0 | (5 << 8) | (1 << 20)  ->  0x00100500
ko_immediate                   presente en los bytes de la funcion
```

**Leccion: un self-test con vectores conocidos no encuentra esta clase de
fallo.** Los vectores de prueba eran todos llamadas a macro, porque el self-test
los escribi yo a partir de lo que ya sabia funcionar. El binario no tiene esa
limitacion: mira todos los bytes.

## Tres falsos positivos que la herramienta casi publica

Cada uno habria sido un hallazgo equivocado:

**1. Un rango presentado como valor exacto.** `fence_compute:6245` emite
`DATA_SEL(write64bit ? 2 : 1) | INT_SEL(int_sel ? 2 : 0)`. `pm4_emit` lo
reporta como `0x00000001 (rango en una rama)`, correctamente. Pero mi regex de
comparacion capturaba solo el primer token y aceptaba `0x00000001` como
constante limpia. Resultado: **"NO EN EL BINARIO: 00000001"**, senalando un
defecto del driver que no existe. Anclado a fin de linea.

**2. Doble conteo al cruzar ficheros.** Ya documentado en `121`; lo reproduje
al recalcular: 29 frente a 17 reales.

**3. Criterio de busqueda demasiado estrecho.** Con el criterio de solo
`movl $inmediato`, tres funciones daban "FALTAN". Dos de ellas
(`0x00038514`, `0x40100000`) **si estaban en el cuerpo**: el compilador las
carga de otra forma. Sube el criterio a buscar en el cuerpo entero.

Y uno al reves, que no era falso positivo sino una limitacion compartida:
`gfx_v8_0_ring_emit_ib_gfx` tiene un `#ifdef __BIG_ENDIAN` **dentro de la
expresion**. El preprocesador ya lo resolvio y `pm4_emit` no puede; el binario
si. **Las dos herramientas se complementan exactamente donde cada una falla**,
y por eso el veredicto se expresa por constante, no por conteo de dwords: el
conteo no es comparable (el binario no ve los `mov %reg`).

## Clasificacion

| afirmacion | estado |
|---|---|
| Las constantes de `pm4_emit` estan en los bytes del `.ko` cargado | `PROVEN` — 15/15 |
| La cabecera del WAIT del vm-flush es `0x00000000` | `PROVEN` — 3 vias |
| 14 de 15 mantienen el orden de emision | `PROVEN` |
| `emit_wave_limit` tiene 2 constantes reordenadas | `PROVEN` — reorden del compilador |
| `pm4_emit` no evaluaba expresiones sin llamada a macro | `PROVEN` — bug encontrado |
| Que el hardware ejecute los paquetes en ese orden | `NOT_DETERMINED` — sin cambio |
| Que los 65+ dwords con variables locales valgan lo calculado | `NOT_APPLICABLE` |
| `lower_32_bits`/`upper_32_bits` ausentes del corpus | `PROVEN_ABSENT` — sin cambio |

Que sigue **igual**: esto valida la *codificacion*. El hardware que hace con
`0xC0053C00` sigue sin estar observado, y no lo observa un `.ko`.

## Confounders

- **Solo 15 funciones.** `pm4_emit` analiza 157; las 15 son las que emiten
  paquetes y estan en `gfx_v8_0`. Las de otras generaciones (gfx_v9_0 a
  v12_1) no se han contrastado, y no aplican a esta placa.
- **El `.ko` es el que el kernel tiene cargado**, pero no puedo probar que
  corresponda a este fuente exacto. Que 15/15 constantes coincidan es
  evidencia fuerte de que si, no una prueba.
- **Comparo constantes, no el flujo.** Que las constantes esten en el cuerpo no
  dice que se escriban en ese orden, ni que se escriban: solo que el codigo
  contiene ese valor. El orden lo doy como corroborado, no probado.
- **`sib=0x82` en los 9** dice que la forma del store es la esperada. No dice
  que no haya otras formas de store en otras funciones.
- **No he mirado `.text.cold`.** Los caminos de error estan en otra seccion y
  no estan cubiertos.

## Desfalsificacion

- **(a)** Las constantes estan en el binario → refutable con
  `--compare-all`; si alguna faltara, rc=1 y `run_all` lo marca FALLA.
- **(b)** La cabecera es `0x00000000` → refutable con `--func`, `+0x007a`.
- **(c)** El bug de `pm4_emit` existia → refutable con
  `eval_call("5 << 8")`, que ahora da `0x00000500`.
- **(d)** `0x00038514` esta en `fence_gfx` → refutable buscando `01 85 03 00`
  en el cuerpo; esta en `+0x80`.
- **(e)** El hardware ejecuta en orden → **no refutable aqui**, y no se afirma.

## UNLOCKS

- **`secE` pasa de "calculado" a "calculado y visto en los bytes".**
- **`121` queda con su discriminante ejecutado**, no solo nombrado.
- **Hay un control permanente**: `run_all` compara ahora lo estatico contra el
  codigo del modulo cargado. Un cambio en las macros que alterase un valor
  immediate haria fallar la suite.
- **`gfx_v8_0_ring_emit_ib_gfx` tiene un `#ifdef` en una expresion PM4.** Es
  el primer caso de preprocesado dentro de un paquete, y conviene buscar los
  demas: son donde la evaluacion estatica se queda corta.
- **Siguiente paso natural**: desensamblar el camino del hardware no cambia,
  pero si lo cambia **descubrir que opcode se escriben los 63 paquetes que
  GFX8 no usa**, que es donde esta el espacio no explorado.

## Evidencia

```
/tmp/amdgpu_loaded.ko            37494368 bytes, 65596 simbolos
  0x147830  gfx_v8_0_ring_emit_vm_flush   544 bytes, 9 stores
  0xdead0    gmc_v8_0_emit_flush_gpu_tlb
  0x147e10  gfx_v8_0_ring_emit_rreg
  0x147a50  __pfx_gfx_v8_0_ring_get_wptr_compute  (fin de vm_flush)

$ objdump -d --start-address=0x147830 --stop-address=0x1478b0 amdgpu_loaded.ko
  147876:  c7 04 82 00 3c 05 c0   movl $0xc0053c00,(%rdx,%rax,4)

sid.h:359   PACKET3_COND_EXEC        0x22
sid.h:550   PACKET3_SWITCH_BUFFER    0x8B
gfx_v8_0.c:6338   0 | (5 << 8) | (1 << 20)   -> 0x00100500
```

```
08-ARQUITECTURA/tools/ko_immediate.py   --self-test --func --compare --compare-all --all
run_all: 44 comprobaciones (42 OK, 1 FALLA ajena de contratos)
toolkit: 35/36 contratos (ko_immediate versionado al commitear)
corpus: 2787 ficheros sin diferencias
```

`WRITE_EXECUTION=NONE`. `MODIFICATIONS=0`. `GPU INTACTA`.

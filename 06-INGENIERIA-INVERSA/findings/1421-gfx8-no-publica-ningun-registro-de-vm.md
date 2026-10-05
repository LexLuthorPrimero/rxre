# 1421 — el grafo de includes del corpus está sano (99,4 %), pero **los headers de GFX8 no definen un solo registro de VM**, y eso cierra la explicación de por qué `gfxhub_v1_0.c` es código muerto

```text
AGENCIA=RX550-INVESTIGACION · WORK_CLASS=AGENT-RE-TOOLING
GENERADO=2026-10-04 · MEDIDO=EN ESTA HOST · CORPUS=rx550-upstream-7.2.8

AFECTADO=include/asic_reg/gca/gfx_8_0_d.h    244 444 B   CERO registros mmVM_*
         include/asic_reg/gca/gfx_8_1_d.h    241 224 B   CERO registros mmVM_*
         amdgpu/si.h                            1 363 B   2 defines  (stub)
         amdgpu/vi.h                            1 474 B   2 defines  (stub)
         amdgpu/vid.h                          19 347 B   219 defines (completo)
         amdgpu/cikd.h                         23 228 B   221 defines (completo)
         amdgpu/sid.h                          31 465 B   407 defines (completo)
         gfx_v8_0.c:6197-6142+  ocho macros sin definir en todo el corpus

COMPLETA=1403 y 1404, y da el por que: el fichero usa simbolos que para GFX8
         solo existen en un header de GCN9
ESTADO=PROVEN
```

## 0 · DE DONDE VIENE LA PREGUNTA

Iba a decodificar el paquete de la valla en el IB real (`1420` dejó cuatro
`EVENT_WRITE_EOP` sin decodificar). Para eso necesitaba las macros del paquete,
`gfx_v8_0_ring_emit_fence_gfx` las usa:

```c
        amdgpu_ring_write(ring, PACKET3(PACKET3_EVENT_WRITE_EOP, 4));
        amdgpu_ring_write(ring, (EOP_TCL1_ACTION_EN | EOP_TC_ACTION_EN |
                                 EOP_TC_WB_ACTION_EN |
                                 EVENT_TYPE(CACHE_FLUSH_AND_INV_TS_EVENT) |
                                 EVENT_INDEX(5)));
        ...
        amdgpu_ring_write(ring, (upper_32_bits(addr) & 0xffff) |
                          DATA_SEL(write64bit ? 2 : 1) | INT_SEL(int_sel ? 2 : 0));
```

**Ocho macros. Ninguna definida en el corpus.** Antes de concluir nada del
entorno revisé el alcance, y el resultado del alcance es el hallazgo.

## 1 · EL GRAFO DE INCLUDES: 99,4 % RESUELTO

MEDIDO sobre los 631 `.c`/`.h` de `amdgpu/`, buscando `#include "..."` y
resolviendo contra `amdgpu/`, `amd/`, `amd/include/` y `amd/include/asic_reg/`:

```
  includes con comillas comprobados                  2 880
  resueltos                                        2 862      99,38 %
  NO resueltos, ficheros distintos                     18
  NO resueltos, instancias                            73

  los 18, y su naturaleza
     amdgpu_pm.h          30      generado por el Makefile del kernel
     amdgpu_dpm.h          9      generado
     amdgpu_ras_mgr.h      8      generado
     amdgpu_smu.h          6      generado
     amdgpu_dm.h           4      display manager
     cik_dpm.h, si_dpm.h   2      generados
     kfd_priv.h, kfd_svm.h,
     kfd_topology.h,
     kfd_smi_events.h     6      KFD, fuera de amd/amdgpu/
     amdgpu_dm_irq.h,
     amdgpu_dm_debugfs.h,
     amdgpu_dm_irq_params.h,
     amdgpu_dm_ism.h       4      display manager
     acp_gfx_if.h,
     modules/inc/mod_freesync.h  2      externos al subarbol
```

> **Ninguno de los 18 es un mapa de registros.** Y los que sí se usan para
> offsets están todos: `gc/gc_9_0_offset.h` (243 KB), `gmc/gmc_8_1_d.h`,
> `bif/bif_5_1_d.h`, `gca/gfx_8_0_d.h` (244 KB), `gca/gfx_8_1_d.h` (241 KB)…
> **El corpus sostiene las mediciones de dirección de registro de todos los
> hallazgos de esta serie.** Eso no es una cifra, es una comprobación de que la
> base está.

## 2 · MI ERROR, TERCERA VEZ DE LA MISMA CLASE, Y CON LA REGLA

Mi primera versión del comprobador resolvió los includes **solo contra
`amdgpu/`**. Dio **416 no resueltos**, y entre ellos `gc/gc_9_0_offset.h`, que
**yo mismo había leído media hora antes**.

MEDIDO. Y el motivo por el que hay que contarlo: `416` es un número enorme,
deliberadamente aterrador, y un número enorme se lee como «el corpus está
destrozado» o como «el corpus está bien», según a lo que se aspire. **Los dos eran
falsos.** El número real es 18.

| | lo que pasó | el coste |
|---|---|---|
| `1412` §3 | leí el tipo del paquete en `[23:16]` y dije «0 paquetes» | falso negativo, sin oráculo |
| `1420` | atribuí un IB a la ruta de compute | lo detectó un bit del dato |
| **`1421`** | resolví includes en la base equivocada y dije «416 ausentes» | **magnitud inflada 23×** |

**La regla que sale de las tres, y es la útil:**

> **Un recuento grande y negativo casi nunca es un hallazgo: es un
> `include path`.** Antes de escribir «el corpus no tiene X», hay que haber
> consultado X en un sitio donde se sabe que está, o tener una segunda fuente que
> contradiga el resultado. En los tres casos la contradicción llegó de un
> lugar inesperado: un paquete, un bit, y **un fichero que yo había abierto**.

## 3 · EL HALLAZGO: GFX8 NO PUBLICA NI UN REGISTRO DE VM

MEDIDO sobre los **dos** headers de la generación de nuestra ASIC,
`gca/gfx_8_0_d.h` (GFX8.0) y `gca/gfx_8_1_d.h` (GFX8.1):

```
  símbolo                                            gfx_8_0_d.h   gfx_8_1_d.h
  mmVM_CONTEXT0_PAGE_TABLE_BASE_ADDR_LO32              NO            NO
  mmVM_CONTEXT0_CNTL                                  NO            NO
  mmVM_INVALIDATE_REQUEST                             NO            NO
  mmVM_INVALIDATE_ENGINE0_SEM                         NO            NO

  y en total, registros mmVM_* en ambos ficheros                 CERO
```

Y para contraste, `gmc/gmc_8_1_d.h` — la ventana **GMC** de GFX8 — sí publica:

```
  mmVM_CONTEXT0_CNTL                     0x504
  mmVM_CONTEXT1_CNTL                     0x505
  mmVM_CONTEXT0_CNTL2                    0x50c
  mmVM_CONTEXT1_CNTL2                    0x50d
  mmVM_CONTEXT{0..7}_PAGE_TABLE_BASE_ADDR     0x54f..0x556
  mmVM_CONTEXT{8..15}_PAGE_TABLE_BASE_ADDR    0x50e..0x515
  mmVM_INVALIDATE_REQUEST                0x51e
  mmVM_INVALIDATE_RESPONSE               0x51f
```

> **La consecuencia es una frase, y es de las más fuertes del proyecto:**
> **en GFX8 la ventana de gráficos no publica ningún registro de MMU. Toda la
> MMU de esta ASIC vive en la ventana GMC, y esa ventana publica dos registros de
> control de contexto.**

## 4 · POR QUÉ ESO EXPLICA `1403` DE FORMA DEFINITIVA

`1403` se-gallery en: `adev->gfxhub.funcs` no se asigna para Polaris12, luego
`gfxhub_v1_0_init()` no corre, luego `hub->ctx_distance` y compañía no se calculan.
Lo dejó **bien mostrado por la vía del puntero**, pero sin explicar **por qué**
GFX8 no necesita ese fichero.

Ahora se sabe:

```
  gfxhub_v1_0.c programa el MMU con estos simbolos
     mmVM_CONTEXT0_PAGE_TABLE_BASE_ADDR_LO32
     mmVM_CONTEXT1_PAGE_TABLE_BASE_ADDR_LO32
     mmVM_INVALIDATE_ENG0_SEM / _REQ / _ACK
     mmVM_CONTEXT1_PAGE_TABLE_START_ADDR_LO32
     mmVM_CONTEXT1_PAGE_TABLE_END_ADDR_HI32

  de donde salen, para GFX8
     gca/gfx_8_0_d.h   NO
     gca/gfx_8_1_d.h   NO
     gmc/gmc_8_1_d.h   NO      <-- ni siquiera la ventana que SI tiene la MMU
     gc/gc_9_0_offset.h        SI   <-- Vega10, GCN9

  y gfxhub_v1_0.c:27 lo admite
     #include "gc/gc_9_0_offset.h"
     #include "gc/gc_9_0_sh_mask.h"
     #include "gc/gc_9_0_default.h"
     #include "vega10_enum.h"
```

> **Un fichero que se llama `gfxhub_v1_0` y programa la MMU de GFX8 con offsets de
> Vega10, en una ASIC cuyos headers de gráficos no definen ni un `mmVM_*`.**
> El fichero no está mal escrito: es un fichero de GCN9 que el árbol mantiene,
> y GFX8 — que es anterior a la abstracción SOC15 que lo motivó — no lo
> selecciona.

**Y esa es también la explicación de por qué GFX8 no echa de menos
`mmVM_CONTEXT{2..15}_CNTL`:** en ningún header de esta generación existen, en
ninguna de las dos ventanas. Lo que publica son **dos**, y `1404` midió que
solo esos dos reciben escritura.

## 5 · LO QUE LE PASA A `1404`

`1404` dejó tres hipótesis para «quién configura los contextos 2 a 15». Con esto,
**la aritmética de las hipótesis cambia:**

| | antes de `1421` | después |
|---|---|---|
| H1 el reset los habilita | posible | **DESCARTADA** — ver `1430` |
| H2 otro escritor en el árbol | posible | **DESCARTADA** — no hay segundo escritor (`1404` §3) y los símbolos no existen para esta ASIC |
| H3 `CONTEXT1_CNTL` cubre 1–15 | posible | **CONFIRMADA** — `gmc_v8_0.c:913`, y despacho real en VMID 7 (`1420`) |

**Y H3 tiene un predicado comprobable sin hardware**, que es lo que la hace
interesante: si `mmVM_CONTEXT1_CNTL` fuera un registro *de rango* (aplicable a
varios VMID), el sh_mask delataría un campo de rango. MEDIDO:
`gmc_8_1_sh_mask.h` publica **22 campos** para `VM_CONTEXT1_CNTL` y los únicos
con `RANGE` en el nombre son `RANGE_PROTECTION_FAULT_ENABLE_{DEFAULT,INTERRUPT}`,
que son faults de rango de tabla, no de VMID.

> ### ⚠ CORRECCION — este párrafo estaba mal, y lo dice otro hallazgo
>
> **De ese `MEDIDO` no sale H3 en contra. Sale a favor, y por un motivo que yo
> no consulté:** un registro cuyo comentario dice `/* enable context1-15 */` no
> necesita un campo de rango para habilitar un rango. El rango está en **el
> sentido del bit**, no en el layout del registro. Los dos son cosas distintas y
> yo los confundí.
>
> **La respuesta estaba en `gmc_v8_0.c:913`, a una línea del sitio donde yo
> estaba mirando, y yo no había abierto el bloque entero.** Confirman H3 el
> comentario del driver y, de forma independiente, el despacho real sobre
> **VMID 7** medido en `1420`.
>
> **Correcto en `1430-el-comentario-dice-enable-context1-15.md`**, que además
> corrige `1404` §3 por la misma causa (leí 4 líneas de 18).

*Limitación:* que el sh_mask no publique un campo de rango no demuestra que el
hardware no tenga ninguno; y que el bit cubra 1–15 para todos y no solo para 7
es `CORROBORATED`, no `PROVEN`. Queda por medir el valor de reset de
`PAGE_TABLE_BLOCK_SIZE` en `mmVM_CONTEXT0_CNTL`, que el driver **no** escribe
para el contexto 0.

## 6 · EL SEGUNDO AGUERO, Y ES DISTINTO DEL PRIMERO

`1411` dejó el `WAIT_REG_MEM` del flush resuelto por el idioma. Lo que no se puede
resolver es el paquete de la valla, y la razón está medida:

```
  cabecera        bytes     defines   ¿definida aquí la capa de macros PM4?
  si.h             1 363         2      STUB
  vi.h             1 474         2      STUB
  vid.h          19 347       219      completa
  cikd.h         23 228       221      completa
  sid.h          31 465       407      completa
  nvd.h          29 789       394      completa
```

**`si.h` y `vi.h` están vaciados a dos defines.** `gfx_v8_0.c` incluye `vi.h`
(línea 33) y no `si.h`, y ninguna de las dos contiene las ocho macros que la
valla necesita.

MEDIDO también: **`si.h` en este corpus tiene un solo contenido real**

```c
#define SI_FLUSH_GPU_TLB_NUM_WREG       2
```

**Y ese 2 corrige `1411` §4.** `1411` escribió que
`VI_FLUSH_GPU_TLB_NUM_WREG = 3` «no corresponde a nada que emita en ninguna
generación». **Falso por una vía distinta: existe `SI_FLUSH_GPU_TLB_NUM_WREG = 2`,
y 2 es exactamente lo que emite GFX8.** La sobre-reserva de 5 dwords de
`gfx_v8_0.c:6932` es entonces una **elección de constante equivocada**
(`VI_` donde el patrón de la generación usa `SI_`), no una constante huérfana.

> **Un hallazgo corrigido por otro hallazgo, y la corrección es más pequeña que
> el error.** El `2` estaba en el mismo directorio, en un header de 1 KB, y
> y estaba al lado del `3`. **La lección no es «busca más»: es que un
> número sin explanation pide su gemelo con prefijo distinto.** `VI_` frente a
> `SI_`, `gfx_` frente a `gmc_`, `gc_` frente a `gca_`. Es el mismo movimiento que
> `1420` §1, y es el que hay que hacer siempre antes de declarar que una
> constante no encaja con nada.

## 7 · LO QUE NO SE AFIRMA

- **No se dice que falten las ocho macros en el driver real.** Se dice que faltan
  **en este corpus**, y que `si.h`/`vi.h` están vaciados. El driver upstream los
  tiene en `si.h` completo; lo que falta es la copia del proyecto.
- **No se dice que `mmVM_CONTEXT{2..15}_CNTL` no existan en el silicio.** Se dice
  que **ningún header de GFX8 los publica**, en ninguna de las dos ventanas.
  Eso es `NOT_PUBLISHED` y por tanto no se puede concluir nada del hardware.
- **No se dice que GFX9 esté bien.** Que `gc_9_0_offset.h` sirva para GFX9 es lo
  que el propio upstream sostiene; aquí solo se mide que **para GFX8 no**.

## 8 · LO QUE QUEDA ABIERTO Y CÓMO SE CIERRA

```
  la valla (EVENT_WRITE_EOP) del IB real
     4 paquetes sin decodificar en revkit/capturas/amdgpu_ring_gfx.txt
     hace falta si.h completo: DATA_SEL, INT_SEL, EVENT_TYPE, EVENT_INDEX,
     EOP_*_ACTION_EN, EOP_EXEC
     NO se puede cerrar con este corpus.           DEFERRED, motivo medido

  quien configura los contextos 2-15
     leer mmVM_CONTEXT7_CNTL  y  0x0888            runtime, 2 lecturas

  por que H2 casi queda descartada
     los simbolos no existen para esta ASIC en ninguna ventana publicada
     no es PROVEN_ABSENT del hardware                NOT_PUBLISHED

  si.h y vi.h de este corpus                        2 defines cada uno
  el resto de headers PM4                            219 a 407 defines

  corpus  solo lectura
  GPU     INTACTA
  sudo    NO usado
```
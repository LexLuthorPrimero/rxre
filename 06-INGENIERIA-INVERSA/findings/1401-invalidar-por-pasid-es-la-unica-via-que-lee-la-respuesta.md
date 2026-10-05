# 1401 — `mmVM_INVALIDATE_RESPONSE` es un registro de 16 bits de estado por dominio, y el driver solo lo lee en la vía que escribe una máscara

```text
AGENCIA=RX550-INVESTIGACION · WORK_CLASS=AGENT-RE-TOOLING
GENERADO=2026-10-04 · MEDIDO=EN ESTA HOST · CORPUS=rx550-upstream-7.2.8
AFECTADO=gmc_v8_0.c:619-636      gmc_v8_0_flush_gpu_tlb_pasid  (lee RESPONSE)
         gmc_v8_0.c:655-660      gmc_v8_0_flush_gpu_tlb       (NO lee)
         gmc_v8_0.c:662-677      gmc_v8_0_emit_flush_gpu_tlb   (NO lee)
         gmc_v7_0.c:443-444      gmc_v7_0_flush_gpu_tlb_pasid  (lee RESPONSE)
         asic_reg/gmc/gmc_8_1_sh_mask.h        los 16 campos de cada registro
         asic_reg/gmc/gmc_8_1_d.h              0x51e REQUEST, 0x51f RESPONSE
CIERRA=el NOT_DETERMINED que 1153 dejo sobre el RREG32 de respuesta
ESTADO=PROVEN-ESTRUCTURA · NOT_DETERMINED-por-que
```

## 0 · LO QUE `1153` DEJÓ ABIERTO

`1153` midió las dos vías de invalidación de TLB y encontró una cosa que no
pudo explicar y anotó como pendiente:

> la vía por PASID acaba con `RREG32(mmVM_INVALIDATE_RESPONSE);` — una lectura
> **cuyo resultado se descarta**, sin máscara, sin bucle, sin test.

La pregunta era *qué hace una lectura que nadie usa*. Este hallazgo contesta la
**mitad estructural** de esa pregunta, con la fuente primaria, y deja la otra
mitad explícitamente abierta.

## 1 · EL REGISTRO, LEÍDO DE LA FUENTE PRIMARIA

`asic_reg/gmc/gmc_8_1_d.h` — esta es la generación de Polaris12 (GFX8), no una de
GCN9:

```
0x051e  mmVM_INVALIDATE_REQUEST
0x051f  mmVM_INVALIDATE_RESPONSE
```

Y `asic_reg/gmc/gmc_8_1_sh_mask.h` da los campos:

```
  REQUEST    VM_INVALIDATE_REQUEST__INVALIDATE_DOMAIN_0    mask=0x0001
             ...
             VM_INVALIDATE_REQUEST__INVALIDATE_DOMAIN_15   mask=0x8000

  RESPONSE   VM_INVALIDATE_RESPONSE__DOMAIN_INVALIDATED_0   mask=0x0001
             ...
             VM_INVALIDATE_RESPONSE__DOMAIN_INVALIDATED_15  mask=0x8000
```

MEDIDO: **16 campos cada uno, bits 0–15, numeración de dominio idéntica.** Y los
nombres no son míos: `INVALIDATE_DOMAIN_N` en el pedido, `DOMAIN_INVALIDATED_N`
en la respuesta.

> **La respuesta es, por nombre de AMD, «este dominio ya se invalidó».** Eso
> convierte la lectura de barra en algo con semántica: es el **estado de
> finalización por dominio**, con la misma numeración que el pedido.

Consecuencia directa, y cierra otra cosa de paso: el comentario

```c
/* bits 0-15 are the VM contexts0-15 */
WREG32(mmVM_INVALIDATE_REQUEST, 1 << vmid);
```

que aparece en `gmc_v8_0.c:658` **queda `PROVEN` por fuente primaria**. No es una
suposición del driver: el sh_mask dice exactamente eso.

## 2 · QUIÉN LEE LA RESPUESTA, MEDIDO SOBRE TODO EL ÁRBOL

```
  LEE mmVM_INVALIDATE_RESPONSE
     gmc_v7_0.c:444      gmc_v7_0_flush_gpu_tlb_pasid
     gmc_v8_0.c:635      gmc_v8_0_flush_gpu_tlb_pasid
     total                                                    2

  ESCRIBE mmVM_INVALIDATE_REQUEST
     gmc_v6_0.c:351   WREG32(..., 1 << vmid)
     gmc_v6_0.c:367   emit_wreg(..., 1 << vmid)
     gmc_v7_0.c:443   WREG32(..., mask)        <-- y LEE la respuesta
     gmc_v7_0.c:468   WREG32(..., 1 << vmid)
     gmc_v7_0.c:483   emit_wreg(..., 1 << vmid)
     gmc_v8_0.c:634   WREG32(..., mask)        <-- y LEE la respuesta
     gmc_v8_0.c:659   WREG32(..., 1 << vmid)
     gmc_v8_0.c:674   emit_wreg(..., 1 << vmid)
```

**Las tres funciones de GFX8 que invalidan, y solo una lee la respuesta:**

| función | qué escribe en REQUEST | lee RESPONSE |
|---|---|---|
| `gmc_v8_0_flush_gpu_tlb` | `1 << vmid` | **no** |
| `gmc_v8_0_emit_flush_gpu_tlb` | `1 << vmid` (por PM4) | **no** |
| `gmc_v8_0_flush_gpu_tlb_pasid` | **`mask`** (N bits) | **sí** |

Y la correlación es exacta sobre las dos generaciones que tienen la vía por
PASID: **2 de 2 leen, y las dos escriben `mask`. 0 de 2 leen, y las dos escriben
`1 << vmid`.**

> Esa es la medida que discrimina. No es «lee a veces»: es **lee exactamente cuando
> invalida más de un dominio a la vez**. Y la explicación que encaja con la
> estructura del registro es directa: si has pedido un solo dominio, ya sabes
> qué bit mirar y no necesitas leer; si has pedido una máscara, el registro te
> dice **cuáles** se completaron.

## 3 · LO QUE SE PUEDE AFIRMAR Y LO QUE NO

**`PROVEN`** (todo lo anterior sale de fuente primaria o de un grep con alcance):

- `mmVM_INVALIDATE_RESPONSE` son **16 bits de finalización por dominio**, con la
  misma numeración de bits que `mmVM_INVALIDATE_REQUEST`.
- Está en `0x51f`, inmediatamente encima del request en `0x51e`.
- El driver lo lee en **2 de 8** sitios de escritura de request, y la
  correspondencia es 1:1 con «escribe máscara» en vez de «escribe un bit».
- El resultado de la lectura **se descarta**: no hay máscara, ni bucle, ni
  comparación, ni `cpu_relax()`.

**`NOT_DETERMINED`, y esto es lo que queda abierto:**

- **Si la lectura es una barrera de orden** — para que el hardware haya visto el
  write del request antes de devolver el control — **o** un residuo, **o** un
  hook de depuración. El driver no lo dice y no hay guía de hardware en el
  corpus.

  > Y hay un dato que **debilita** la lectura de «espera de finalización»: si
  > fuera eso, habría un bucle. No lo hay. Una espera de finalización sin bucle
  > no espera nada. **Así que la hipótesis de «espera» queda peor que las otras
  > dos, y eso es una medición, no una preferencia.**

- **Si `DOMAIN_INVALIDATED_N` se pone por el hardware y lo limpia el software, o
  es un estado que se pone solo y hay que escribir para limpiar.** `1166` ya
  encontró un caso write-1-to-clear en esta misma ASIC
  (`ATC_VMID_PASID_MAPPING_UPDATE_STATUS`), así que el precedente existe, pero
  son registros distintos y no se puede extrapolar.

## 4 · POR QUÉ ESTO LE SÍRVE A UN DRIVER PROPIO

Porque cierra una decisión de implementación que era ambigua:

```
  invalidar UN dominio
     WREG32(REQUEST, 1 << vmid)
     y ya.  No hay que leer nada.                 PROVEN por 1153 y este

  invalidar VARIOS dominios
     WREG32(REQUEST, mask)
     RREG32(RESPONSE)   <- el driver lo hace, sin usar el resultado
     ¿qué hay que hacer con ese resultado?        NOT_DETERMINED
```

Un driver propio que implemente solo la primera ruta **funciona**, y ese es el
camino que toma `amdgpu_gart.c:505` (vmid fijo, una escritura). La segunda ruta
solo hace falta si se invalida por PASID, y esa es la que `1178` dejó **sin
escritor alcanzable** de su tabla de entrada.

> **Los dos `NOT_DETERMINED` de la vía por PASID encadenan:** la máscara se
> construye con un registro que nadie escribe (`1178`), y la respuesta se lee
> sin usarse (este). **Los dos son la misma ruta incompleta.** Para un driver
> propio la conclusión operativa es una sola: **la vía 1 es la que hay que
> implementar; la vía 2 no tiene insumo ni salida medidos en esta ASIC.**

Eso no dice que la vía 2 esté mal. Dice que **implementarla exige responder dos
preguntas que el corpus no contesta**, y que la ruta que no exige preguntas es la
otra.

## 5 · LO QUE NO SE AFIRMA

- **No se dice que la lectura sea inútil.** Se dice que su resultado no se usa,
  que es un hecho del código, y que su propósito es `NOT_DETERMINED`.
- **No se dice que el hardware no implemente la respuesta.** Los 16 campos existen
  en el sh_mask de la generación correcta; que el hardware los implemente es
  semántica, no cabecera.
- **No se generaliza a GFX9+.** En este corpus solo `gmc_v7_0` y `gmc_v8_0`
  leen RESPONSE; `gmc_v9_0`/`v10`/`v11`/`v12` no aparecen en la lista. Puede que
  usen otro mecanismo (el semáforo que `1179` midió lleno y no leído), o que
  simplesmente no lo hagan. Eso es otra pregunta.
- **No se toca ningún fichero del corpus.** Todo es lectura.

## 6 · LA LECIÓN, Y ES LA CUARTA DE LA MISMA FAMILIA

| hallazgo | lo que era |
|---|---|
| `1153` | un `RREG32` cuyo sentido no se conocía |
| `1179` | un campo lleno y no leído |
| `1178` | un registro leído y no escrito |
| **`1401`** | **un registro cuyo NOMBRE en la fuente primaria ya contenía la respuesta** |

> **La cuarta lección se reduce a una regla de método: cuando una lectura del driver
> no tiene sentido, el sh_mask de la generación correcta suele tenerlo.** No
> siempre —aquí sí, y por eso el hallazgo existe— pero es el primer sitio donde
> mirar, y es barato: dos `grep` sobre un header de 100 líneas.

Y hay un corolario sobre el corpus que ya salió mientras se medía, y que vale
como `LIMITATION` para todo lo anterior:

> **Las cabeceras generadas no están en el árbol.** `soc15.h` incluye
> `amdgpu_reg_state.h`, y ese fichero **no existe** en `rx550-upstream-7.2.8`. Los
> offsets sí se pueden recuperar de `include/asic_reg/`, que sí está (486 MB),
> pero **el símbolo que gana al compilar** depende del orden de inclusión de
> `soc15.h`, que no está. MEDIDO: `mmVM_CONTEXT0_CNTL` vale `0x504` en
> `gmc_8_1_d.h` y `0x0880` en `gc_9_0_offset.h` — **el mismo nombre, dos bloques,
> dos direcciones**. Para lo que este hallazgo afirma (bits y nombres) da igual;
> para cualquier aritmética de direcciones, hay que declarar qué bloque se está
> usando.

## 7 · ESTADO

```
  mmVM_INVALIDATE_REQUEST   0x51e  16 campos INVALIDATE_DOMAIN_0..15   PROVEN
  mmVM_INVALIDATE_RESPONSE  0x51f  16 campos DOMAIN_INVALIDATED_0..15  PROVEN
     numeracion de bits identica entre ambos                        PROVEN
     comentario "bits 0-15 son los contextos 0-15"                  PROVEN

  lee RESPONSE
     via por PASID    gmc_v7_0.c:444   gmc_v8_0.c:635     2 de 2   PROVEN
     via por VMID     gmc_v7_0.c:468   gmc_v8_0.c:659     0 de 2   PROVEN
     correlacion: lee <=> escribe mask, no un bit                  PROVEN

  para que sirve la lectura
     barrera de orden / residuo / debug                            NOT_DETERMINED
     espera de completacion  -> DEBILITADA, no hay bucle
     semantica de DOMAIN_INVALIDATED (W1C o estado)              NOT_DETERMINED

  cierra el NOT_DETERMINED de 1153 sobre el RREG32 de respuesta, en su parte estructural
  encadena con 1178: la via por PASID no tiene insumo ni salida medidos
  corpus  solo lectura
  GPU     INTACTA
  sudo    NO usado
```
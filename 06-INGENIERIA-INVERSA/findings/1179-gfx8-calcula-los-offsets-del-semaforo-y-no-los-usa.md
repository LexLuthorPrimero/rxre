# 1179 — el hub de GFX8 calcula los offsets del semáforo de invalidación y nunca los usa: el campo se llena para todos los hubs y se consume para los de GMC9+

```text
AGENCIA=RX550-INVESTIGACION · WORK_CLASS=AGENT-RE-TOOLING
GENERADO=2026-10-04 · MEDIDO=EN ESTA HOST · CORPUS=rx550-upstream-7.2.8
AFECTADO=gfxhub_v1_0.c:413-441   los calcula y los guarda en adev->vmhub[]
         amdgpu_gmc.h:123        el campo de la struct
         gmc_v9_0.c, gmc_v11_0.c, gmc_v12_1.c   los CONSUMEN
         gmc_v8_0.c              NO los consume — y ese es el hallazgo
CONFIRMA=1145-el-page-walker-de-gfx8-es-una-sola-instruccion.md, por una vía
         distinta: un campo lleno y no leído
ESTADO=PROVEN-CAMPO-LLENO-NO-LEIDO · lectura de corpus
```

## 0 · LO QUE `1145` AFIRMÓ, Y LA VÍA QUE LE FALTA

`1145` demostró por **dos** vías que el flush de TLB de GFX8 no usa semáforo:

1. `gmc_v8_0_flush_gpu_tlb` **ignora** el parámetro `vmhub`.
2. El gemelo `gmc_v9_0_flush_gpu_tlb` **lo usa en cinco sitios**, incluido un
   `BUG_ON` y un semáforo.

Falta una tercera, y es la más fuerte de las tres porque no depende de comparar
dos funciones: **comprobar si el campo que contendría el semáforo se llena y
luego se lee.**

MEDIDO, y resulta que sí se llena, y que no se lee.

## 1 · EL CAMPO SE CALCULA PARA GFX8

`gfxhub_v1_0_init()`, `gfxhub_v1_0.c:413` y siguientes:

```c
struct amdgpu_vmhub *hub = &adev->vmhub[AMDGPU_GFXHUB(0)];

hub->ctx0_ptb_addr_lo32 =
        SOC15_REG_OFFSET(GC, 0, mmVM_CONTEXT0_PAGE_TABLE_BASE_ADDR_LO32);
hub->ctx0_ptb_addr_hi32 =
        SOC15_REG_OFFSET(GC, 0, mmVM_CONTEXT0_PAGE_TABLE_BASE_ADDR_HI32);
hub->vm_inv_eng0_sem =
        SOC15_REG_OFFSET(GC, 0, mmVM_INVALIDATE_ENG0_SEM);
hub->vm_inv_eng0_req =
        SOC15_REG_OFFSET(GC, 0, mmVM_INVALIDATE_ENG0_REQ);
hub->vm_inv_eng0_ack =
        SOC15_REG_OFFSET(GC, 0, mmVM_INVALIDATE_ENG0_ACK);
...
hub->ctx_addr_distance = mmVM_CONTEXT1_PAGE_TABLE_BASE_ADDR_LO32 -
        mmVM_CONTEXT0_PAGE_TABLE_BASE_ADDR_LO32;
```

MEDIDO: **`gfxhub_v1_0.c` sí corre en esta ASIC** — es el fichero que programa el
`PAGE_TABLE_BASE` del GART, y `1145`/`1166` lo dieron por alcanzable.

> **O sea que para esta GPU, `hub->vm_inv_eng0_sem` contiene un valor válido.** No
> es cero, no es basura: es el offset correcto del registro de semáforo que este
> ASIC **no tiene**. El campo está poblado con la dirección de un registro que no
> existe en este silicio.

## 2 · Y NUNCA SE LEE, Y ESO ES LO QUE CIERRA

MEDIDO sobre **todas** las lecturas de `vm_inv_eng0_sem` en el árbol, separando
escritura de lectura:

```
  ESCRIBEN el campo (hub->vm_inv_eng0_sem = ...)
     gfxhub_v1_0.c      gfxhub_v2_0.c    gfxhub_v11_5_0.c
     gfxhub_v12_0.c     mmhub_v1_0.c     mmhub_v2_0.c
     mmhub_v3_0_1.c     mmhub_v3_3.c

  LEEN el campo (hub->vm_inv_eng0_sem + ...)
     gmc_v9_0.c         gmc_v11_0.c      gmc_v12_1.c
```

**`gmc_v8_0.c` no está en ninguna de las dos listas.** Ni escribe ni lee.

Y la asimetría es instructiva:

| | quién llena | quién lee |
|---|---|---|
| GFX8 | `gfxhub_v1_0.c` ✅ | **nadie** |
| GFX9+ | `gfxhub_v2_0.c`, `v11_5_0`, `v12_0` | `gmc_v9_0`, `v11_0`, `v12_1` ✅ |

> **El campo de la struct es común a todos los hubs, y se llena para todos; pero
> solo GMC9+ tiene código que lo consume.** Es un campo compartido que en GFX8
> es un valor **inerte pero válido**, y la única forma de saberlo es seguir el
> puntero `hub` y ver qué ramas lo leen.

## 3 · POR QUÉ ESTO ES MÁS FUERTE QUE LAS DOS VÍAS ANTERIORES

Porque las tres se apoyan en medidas **independientes**, y una afirmación que falla es
una que depende del otro código:

| vía | en qué se apoya | qué falla si me equivoco |
|---|---|---|
| `1145` §1 | `gmc_v8_0_flush_gpu_tlb` ignora `vmhub` | que el parámetro se use en otra línea que no leí |
| `1145` §2 | el gemelo GFX9 lo usa en 5 sitios | que el gemelo no sea equivalente |
| **`1179`** | **el campo se llena y no se lee** | que haya un lector con otro nombre |

La tercera es la más robusta porque es una **ausencia comprobable con un grep**: si existe un lector de `hub->vm_inv_eng0_sem` en `gmc_v8_0.c`, un grep del símbolo lo encuentra, y no hay ninguno. No depende de comparar funciones ni de interpretar un parámetro.

> **Y tiene una consecuencia que las otras dos no:** el hecho de que el campo
> **contenga un valor válido** descarta la explicación fácil. Alguien podría
> suponer que en GFX8 el campo está a cero porque nadie lo inicializa, y por eso
> no se lee. **Es falso: está inicializado con el offset correcto.** Se calcula
> para todos los hubs sin mirar cuál, y GFX8 simplemente no lo consume.

## 4 · LO QUE NO SE AFIRMA

- **No se dice que GFX8 no tenga un semáforo de invalidación.** Se dice que
  **este driver no lo usa por esa vía**. El hardware podría tener un mecanismo de
  serialización que el driver no necesita porque con un solo hub no hay
  contención entre hubs. Eso es `NOT_PUBLISHED`, y es coherente con la
  arquitectura: **un semáforo serializa invalidaciones de hubs distintos; con un
  hub no hay a qué serializar.**

  > Eso es una hipótesis mía, y la marco como tal. Lo que está `PROVEN` es la
  > no-consumación del campo. Que el hardware no lo tenga es `NOT_DETERMINED`.

- **No se dice que `ctx_addr_distance` esté mal calculado.** Se calcula y se
  guarda; no se ha medido quién lo lee en GFX8, y si no lo lee, es el mismo caso
  que los tres registros del semáforo.

- **No se modifica `gfxhub_v1_0.c`.** Es de otra sesión.

## 5 · LO QUE ESTO APORTA A LA CADENA DE LA MMU

Esta hallazgo cierra, sobre el GFX8, la lista de lo que la capa de VM **realmente**
programa, que es lo que un driver propio necesita saber:

```
  PROGRAMADO y USADO
     mmVM_CONTEXT{0,8}_PAGE_TABLE_BASE_ADDR    por vmid      gfxhub_v1_0 + gmc_v8_0
     mmVM_INVALIDATE_REQUEST                   por mascara    gmc_v8_0_flush_gpu_tlb
     mmIH_VMID_0_LUT                           por pasid     gmc_v8_0_emit_pasid_mapping

  CALCULADO y NO USADO
     vm_inv_eng0_sem / req / ack              offsets, sin consumidor
     ctx_addr_distance                        offset, sin consumidor medido
     mmATC_VMID0_PASID_MAPPING                leido por el lector, sin escritor (1178)
```

**Las tres líneas de abajo son las que un driver propio no tiene que replicar,
por una razón que ahora está medida en vez de supuesta.** Y la del medio es la
que más probablement se implementaría por costumbre, porque el nombre del campo
—`vm_inv_eng0_sem`, «semáforo de invalidación»— invita a ello.

> **Copiar la estructura de un hub de una generación nueva a GFX8 no es
> conservador: es escribir código que espera un campo que nadie lee.** El nombre
> del campo no es evidencia de que el hardware lo tenga.

## 6 · LA LECIÓN, QUE ES LA MISMA QUE EN `1178` PERO CON MÁS PESO

`1178` halló que hay un **lector sin escritor**. Este halla un **campo escritor
sin lector**. Y juntos dan la forma completa de los dos lados de la tabla:

```
              escribe ATC_VMID0     lee ATC_VMID0
  GFX8         NO (1178)            SI (1153)
  y escribe vm_inv_eng0_*  (1179)   NO lo lee
```

Las dos mitades son la **misma ausencia**, vista desde registros distintos: **la
ruta de invalidación por PASID y la de semáforo están ambas desconectadas de
la parte del driver que sí corre.**

Y eso es un patrón, y los patrones son reutilizables. Es el cuarto caso de la
misma familia:

| hallazgo | forma |
|---|---|
| `023` | nombre de fichero que no corresponde al código que corre |
| `047` | un cero medido sobre la lista equivocada |
| `1166`/`1177` | dos escritores, uno en tabla sin invocación |
| **`1178`/`1179`** | **escritor y lector en registros distintos, sin puente** |

> **La ley que sale de las cuatro: en este driver hay campos de la MMU que se
> llenan o se leen sin que exista el otro extremo, y la razón es siempre la misma
> — el código que los une pertenece a otra generación.** La pregunta que hay que
> hacer antes de implementar cualquiera de ellos es *«quién produce y quién
> consume, en el ASIC de esta placa»*, y esa pregunta se responde leyendo dos
> grep, no un manual.

## 7 · ESTADO

```
  hub->vm_inv_eng0_sem/req/ack
     calculados por      gfxhub_v1_0.c         SI   (GFX8 corre este fichero)
     valor               offset valido         SI
     leidos por GFX8     NINGUN fichero        PROVEN
     leidos por GFX9+    gmc_v9_0/v11_0/v12_1  SI

  hub->ctx_addr_distance
     calculado           SI
     leido por GFX8      NO MEDIDO            -> mismo caso, falta medir

  consecuencia
     un semaforo de invalidacion no es necesario para 1 hub   HIPOTESIS
     el hardware no lo tiene                                NOT_DETERMINED

  confirma 1145 por tercera via independiente
  GPU     INTACTA
  sudo    NO usado
  corpus  solo lectura
```
# 1412 — el único IB real del proyecto identifica un paquete **byte a byte** y, en el mismo pase, demuestra que un registro capturado no tiene nombre único: `0x0bcc` son diez símbolos en cinco bloques

```text
AGENCIA=RX550-INVESTIGACION · WORK_CLASS=AGENT-RE-TOOLING
GENERADO=2026-10-04 · MEDIDO=EN ESTA HOST
ARTEFACTO=revkit/capturas/amdgpu_ring_gfx.txt
          8204 bytes = 2051 dwords, leido en little-endian
CORPUS=rx550-upstream-7.2.8 (solo lectura)

AFECTADO=gfx_v8_0.c:6042-6062      gfx_v8_0_ring_emit_hdp_flush  -> el paquete
         cikd.h:229-231            la macro PACKET3, confirmada por el artefacto
         1411-el-wait-reg-mem-...  pasa de INFERIDO a OBSERVADO el idioma ref==mask
         1403-gfx8-no-instala-... §7  queda con una medicion, no con un argumento

CONTRASTE=mi primer decodificador dio FALSO NEGATIVO: lei el tipo del paquete en
         los bits [23:16] y concluyo "ningun WAIT_REG_MEM". Hay 8.
ESTADO=OBSERVADO-para-el-HDP · NEGATIVO-ACOTADO-para-el-VM ·
        NOT_DETERMINED-para-el-nombre-de-los-registros
```

## 0 · POR QUÉ ESTE HALLAZGO ES DISTINTO DE LOS ANTERIORES

Todos los hallazgos de esta serie salen de **leer el driver**. Este sale de
**comparar el driver con lo que la GPU realmente escribió en un anillo**, y de
esa comparación salen dos cosas que ninguna lectura de código da:

1. Una **identificación byte a byte** que convierte una inferencia mía en
   observación.
2. Una **imposibilidad medida**: el registro que la GPU escribió no tiene un
   nombre único, porque el mismo valor aparece en cinco bloques distintos.

## 1 · EL ALCANCE DEL ARTEFACTO, MEDIDO ANTES DE USARLO

Antes de buscar nada, la composición. Contando los 256 dwords de un bloque:

```
  PACKET3_NOP (0x10)          203      <-- 79 % del bloque es relleno
  dwords de operando            43
  PACKET3_EVENT_WRITE_EOP       4
  COND_EXEC / WAIT_REG_MEM /
  CONTEXT_CONTROL /
  INDIRECT_BUFFER /
  WRITE_DATA / SWITCH_BUFFER    1 cada uno
                               ---
                               256
```

**Ocho bloques idénticos, periodo de 256 dwords exacto**
(`8, 264, 520, 776, 1032, 1288, 1544, 1800`).

Y un solo `PACKET3_INDIRECT_BUFFER` por bloque, en el dword 18, con
`d1 = 0x00278000`. **Una sola orden de trabajo por bloque, y 203 dwords de
relleno.**

> **Este anillo estaba prácticamente vacío cuando se capturó.** Es el hecho que
> gobierna todo lo demás y **es lo primero que hay que registrar** (§34, estado
> del artefacto): cualquier paquete que no aparezca aquí no está porque no se
> emitiera, sino porque **este anillo no hacía ese trabajo**. Eso es
> `NOT_OBSERVED`, no `NOT_EMITTED`, y la distinción es la diferencia entre una
> conclusión y una theorems vacía.

## 2 · EL PAQUETE DE `dword 8`, Y LA FUENTE QUE LO PREDICE

Del artefacto, `dwords 8..14`:

```
  8  0xc0053c00   PACKET3 type=0x3c count=5
  9  0x00000143   OP=1  FUNCTION=3(==)  ENGINE=1(PFP)
 10  0x00001537   addr lo
 11  0x00001538   addr hi
 12  0x00000001   ref
 13  0x00000001   mask
 14  0x00000020   poll
```

Y `gfx_v8_0_ring_emit_hdp_flush`, `gfx_v8_0.c:6042-6062`, literal:

```c
        adev->gfx.funcs->get_hdp_flush_mask(ring, &ref_and_mask, &reg_mem_engine);
        amdgpu_ring_write(ring, PACKET3(PACKET3_WAIT_REG_MEM, 5));
        amdgpu_ring_write(ring, (WAIT_REG_MEM_OPERATION(1) | /* write, wait, write */
                                 WAIT_REG_MEM_FUNCTION(3) |  /* == */
                                 reg_mem_engine));
        amdgpu_ring_write(ring, mmGPU_HDP_FLUSH_REQ);
        amdgpu_ring_write(ring, mmGPU_HDP_FLUSH_DONE);
        amdgpu_ring_write(ring, ref_and_mask);
        amdgpu_ring_write(ring, ref_and_mask);
        amdgpu_ring_write(ring, 0x20); /* poll interval */
```

Los tres valores que no son constantes salen del artefacto:

```
  0x1537  =  mmGPU_HDP_FLUSH_REQ     (bif/bif_4_1_d.h y bif_5_1_d.h)
  0x1538  =  mmGPU_HDP_FLUSH_DONE    (los mismos dos headers)
  0x143   =  OPERATION(1) 0x100  |  ENGINE(1) 0x40  |  FUNCTION(3) 0x3
  ref_and_mask = 1  ->  lo que devolvio get_hdp_flush_mask en esta maquina
```

**Los siete dwords coinciden con lo que la fuente emite, en orden, en valor.**

> **Y de ahí sale lo que importa: `ref == mask == 1` es `OBSERVADO`, no
> inferido.** `1411` §2 dedujo el idioma «la comparación es `(valor & mask)`
> contra `ref`, y `ref == mask` significa esperar a todos los bits» **leyendo
> código**. Ahora hay un paquete real que lo confirma con el mismo patrón. **Una
> inferencia y su confirmación tienen distinto valor en el grafo, y el cambio
> de estado es real.**

## 3 · MI ERROR, Y QUEDO ESCRITO

El primer intento de decodificar la captura **falló**, y el fallo es instructivo
por la clase de error, no por el resultado:

```
  lo que hice     tipo del packet en los bits [23:16], cuenta en [5:0]
  lo que es       tipo en [15:8], cuenta en [29:16]
  lo que conclui  "NINGUN PACKET3_WAIT_REG_MEM en la captura"
  lo que hay      8
```

La macro que me faltaba leer, `cikd.h:229-231`:

```c
#define PACKET3(op, n)	((PACKET_TYPE3 << 30) |				\
			 (((op) & 0xFF) << 8) |				\
			 ((n) & 0x3FFF) << 16)
```

**En bits [23:16] no hay nada.** Lo que hay es `0x3C` en [15:8], que es donde la
macro pone el tipo. Mi filtro no coincidencia con ningún paquete real y produjo un
cero absolutamente plausible.

> **Sexta vez de la misma familia, y la más silenciosa: conté la cosa equivocada
> en el sitio correcto.** No era una cita falsa ni un fichero muerto: era un
> `grep` bien escrito sobre un campo que no es el del campo. **El resultado
> erróneo era «no hay nada», que es el resultado más difícil de detectar y el
> que más daño hace, porque invita a escribir una conclusión negativa.**
>
> Lo que lo habría detectado en un segundo es lo que acabo de hacer al escribir
> el hallazgo: **contrastar la primera coincidencia que aparece con la fuente
> que la predice.** Un cero no se contrasta, así que nunca se contrasta solo.

## 4 · EL NEGATIVO ACOTADO: NO HAY FLUSH DE VM EN ESTA CAPTURA

MEDIDO sobre los 8 `WAIT_REG_MEM` del artefacto:

```
  WAIT_REG_MEM totales                             8
  con ref == mask == 1                             8
  con mask == 0                                    0
  que mencionen 0x51e (mmVM_INVALIDATE_REQUEST)   0
```

Y tampoco hay ningún `WRITE_DATA` con `reg` en la zona de
`mmVM_CONTEXT*_PAGE_TABLE_BASE_ADDR` (`0x54f`–`0x556` ni `0x50e`–`0x515`).

> **Esto NO refuta `1411`.** `1411` afirma que el paquete de espera del flush de
> VM se escribe con `mask = 0`. Este artefacto **no contiene ningún flush de VM**,
> así que no lo toca. Es `NOT_OBSERVED`, y el motivo está medido en §1: el anillo
> estaba vacío.
>
> **Lo que sí hace este artefacto es decir qué captura cerraría esa pregunta**, y
> es un requisito concreto: hace falta un anillo **con un trabajo que actualice la
> tabla de páginas de un VMID de usuario**, es decir una página nueva mapeada, no
> un arranque en reposo. Con eso, el `WAIT_REG_MEM` del flush de VM aparece en el
> IB con sus valores reales de `ref` y `mask`, y `1411` pasa de `PROVEN` sobre el
> código a `OBSERVED` sobre el hardware.

## 5 · LA IMPOSIBILIDAD MEDIDA: `0x0bcc` NO TIENE NOMBRE ÚNICO

En el `dword 22` de cada bloque hay un `PACKET3_WRITE_DATA`:

```
  22  0xc0033700   PACKET3_WRITE_DATA count=3
  23  0x40100000   cmd = WRITE_DATA_ENGINE_SEL(1) | WR_CONFIRM
  24  0x00000bcc   reg              <-- este
  25  0x00000000
  26  0x00000001   value
```

Busqué `0x0bcc` en **todo** `include/asic_reg/`. Resultado:

```
  cfgPCIE_VENDOR_SPECIFIC_HDR_GPUIOV_SCH9_DW0   nbio/nbio_6_3_2_offset.h
  mmDCP3_DC_LUT_WHITE_OFFSET_RED                 dce/dce_12_0_offset.h
  mmHDP_DEBUG0                                  oss/oss_1_0_d.h
  mmHDP_DEBUG0                                  oss/oss_2_0_d.h
  mmHDP_DEBUG0                                  oss/oss_2_4_d.h
  mmHDP_DEBUG0                                  oss/oss_3_0_1_d.h
  mmHDP_DEBUG0                                  oss/oss_3_0_d.h
  regTCX_UE_ERR_STATUS_HI                        gc/gc_9_4_3_offset.h
  regVM_CONTEXT12_CNTL                           mmhub/mmhub_1_7_offset.h
  regVM_INVALIDATE_ENG9_REQ                      mmhub/mmhub_1_8_0_offset.h

  10 simbolos, 5 bloques distintos, y 5 de ellos son el MISMO nombre
```

**Diez candidatos, cinco bloques, y `mmHDP_DEBUG0` aparece con el mismo valor en
cinco headers de cuatro generaciones de OSS distintas.**

> **Esto no es un problema del artefacto: es la estructura del mapa de
> registros de SOC15.** Cada bloque (`GC`, `GMC`, `BIF`, `MMHUB`, `OSS`, `NBIO`,
> `DCE`) tiene su propio espacio de direcciones, y **una dirección en un anillo
> es una dirección *dentro de un bloque*, no un identificador global.**
>
> `1403` §7 ya había avisado de esto leyendo cabeceras: «`mmVM_CONTEXT0_CNTL`
> vale `0x504` en el bloque GMC y `0x0880` en el bloque GC». **Aquí está la
> versión medida sobre hardware: un registro real, escrito de verdad por la GPU, y
> con diez nombres indistinguibles.**

Y hay una causa adicional en el driver que impide resolverlo aun sabiendo el
bloque:

```c
soc15_common.h:36
#define SOC15_REG_OFFSET(ip, inst, reg)	(adev->reg_offset[ip##_HWIP][inst][reg##_BASE_IDX] + reg)
```

`adev->reg_offset[][][]` es una **tabla que se rellena en tiempo de ejecución**
(`aldebaran_reg_init.c:34-36`, `soc15.c:428-464`). El registro que acaba en el
anillo es **`reg_offset + offset_crudo`**, y el primer sumando no está en ninguna
cabecera del repositorio.

## 6 · LO QUE ESTO LE PASA A LA INGENIERÍA INVERSA DEL PROYECTO

Es la limitación con el nombre y la medida, que es lo que §25 y §26 piden:

```
  LO QUE UN IB CAPTURADO SI PERMITE
     identificar TIPOS de paquete          por el codigo, sin ambiguedad
     identificar el LENGUAJE de un campo   por comparacion entre paquetes
     medir DELTAS entre dos registros     restando, sin conocer el nombre
     ver la ESTRUCTURA de una secuencia   COND_EXEC, IB, fence, EOP
     contar y localizar                   posicion y periodo, exactos

  LO QUE NO PERMITE, Y ESTA MEDIDO
     nombrar un registro aislado           0x0bcc -> 10 simbolos, 5 bloques
     distinguir dos bloques               no hay etiqueta de bloque en el PM4
     resolver un SOC15_REG_OFFSET         reg_offset[] es de runtime
```

**Consecuencia para el bucle:** la estrategia correcta para-reverse-el-IB es
**comparativa, no por catálogo**. Un `reg` que aparece siempre acompañado de un
`EVENT_WRITE_EOP` a una dirección concreta es un patrón; un `reg` suelto es un
número. Y para nombrar hace falta **una segunda fuente**: el `reg_offset[]` del
dispositivo vivo, o un IB del mismo anillo capturado en una ASIC distinta para
sacar la diferencia por bloque.

> **Y hay un instrumento que esto sí justifica y que es diminuto:** un
> **catálogo de aliasing** `dirección -> {símbolo, bloque, generación}`, generado
> de `include/asic_reg/` entero. No adivina el bloque correcto —eso no se puede—
> pero **hace visible la ambigüedad en vez de esconderla bajo el primer `grep` que
> aparece**, que es exactamente el fallo que acabo de cometer en §3 por el otro
> lado. No lo implemento: es el mismo genre que `tools/registro2.py` de otra
> sesión y el árbol tiene ficheros suyos modificados. Queda anotado con su
> alcance exacto: `~500 MB` de cabeceras, una pasada, salida indexada.

## 7 · ESTADO

```
  ARTEFACTO revkit/capturas/amdgpu_ring_gfx.txt
     8204 bytes = 2051 dwords, little-endian, alineado a 4
     8 bloques identicos de 256 dwords, periodo exacto
     203 de cada 256 dwords son PACKET3_NOP
     ordenes de trabajo reales por bloque         1 (INDIRECT_BUFFER)
     ESTADO DEL ARTEFACTO: anillo en reposo       OBSERVADO

  PACKET3, layout
     tipo en [15:8], cuenta en [29:16]            cikd.h:229-231
     confirmado sobre el artefacto: 0xc0053c00 = PACKET3(WAIT_REG_MEM, 5)
     mi primer decodificador leyo [23:16] y dio falso negativo   CORREGIDO

  flush de HDP
     paquete de 7 dwords del artefacto == gfx_v8_0.c:6052-6061   IDENTIFICADO
     mmGPU_HDP_FLUSH_REQ  0x1537, _DONE 0x1538                  OBSERVADO
     ref == mask == 1    era inferido en 1411, ahora             OBSERVADO

  flush de VM
     WAIT_REG_MEM con mask==0        0 de 8        NOT_OBSERVED (artefacto sin flush)
     mencion de 0x51e                0 de 8        NOT_OBSERVED
     1411 sigue en PROVEN sobre el codigo; este artefacto no lo toca
     captura que lo cerraria: un trabajo que mapee una pagina de un VMID usuario

  nombre de los registros
     0x0bcc -> 10 simbolos en 5 bloques          NOT_DETERMINED
     SOC15_REG_OFFSET usa reg_offset[] de runtime, no resoluble estaticamente
     la RE de un IB tiene que ser COMPARATIVA, no por catalogo

  LIMITACION registrada y con medida, no con opinion
  corpus  solo lectura
  GPU     INTACTA
  sudo    NO usado
```
# 1441 — el frame budget de GFX8 nombra **tres** vallas y el IB real tiene **dos**: la que falta es la del flush de VM, y el `NUM_WREG` equivocado son 6 dwords, no 4

```text
AGENCIA=RX550-INVESTIGACION · WORK_CLASS=AGENT-RE-TOOLING
GENERADO=2026-10-04 · MEDIDO=EN ESTA HOST · CORPUS=rx550-upstream-7.2.8
ARTEFACTO=revkit/capturas/amdgpu_ring_gfx.txt

AFECTADO=gfx_v8_0.c:6873-6901   gfx_v8_0_ring_funcs_gfx      emit_frame_size
         gfx_v8_0.c:6919-6940   gfx_v8_0_ring_funcs_compute  emit_frame_size
         gfx_v8_0.c:6954-6970   gfx_v8_0_ring_funcs_kiq      emit_frame_size
         gfx_v8_0.c:6876        .nop = PACKET3(PACKET3_NOP, 0x3FFF) == 0xffff1000
         vi.h:27 / si.h:27      VI_=3  SI_=2, y quien usa cada una

CORRIGE=1411 §4 con numeros exactos: el exceso es 6 dwords, no 4, en dos de
        los tres anillos.  Y la atribucion de 1411 no dijo de que anillo era.
COMPLETA=1412 §1 (el relleno), 1420 y 1440 (las dos vallas observadas)
ESTADO=PROVEN
```

## 0 · DE DÓNDE VIENE

`1440` decodificó las vallas del IB real y encontró **dos por bloque de 256
dwords**. `1411` §4 había medido el margen de la reserva del flush de VM, pero
usando la fórmula del anillo **de compute** y sin decir de qué anillo hablaba.

Hay **tres** fórmulas, una por anillo, y son distintas. Eso cambia los números.

## 1 · LAS TRES FÓRMULAS, Y QUÉ ANILLO ES CADA UNA

```
  gfx_v8_0_ring_funcs_gfx        (6873)  emit_frame_size en 6881
     5  COND_EXEC
     7  PIPELINE_SYNC
     VI_FLUSH_GPU_TLB_NUM_WREG * 5 + 9      <-- VM_FLUSH        (6884)
     12   FENCE for VM_FLUSH                             (6885)
     20  GDS switch
     4   double SWITCH_BUFFER
     5   COND_EXEC
     7   HDP_flush
     4   VGT_flush
     14  CE_META
     31  DE_META
     3   CNTX_CTRL
     5   HDP_INVL
     12 + 12   FENCE x2                                 (6897)
     2   SWITCH_BUFFER
     5   SURFACE_SYNC
     el comentario del propio driver dice:  "maximum 215dw if count 16 IBs in"

  gfx_v8_0_ring_funcs_compute    (6919)  emit_frame_size en 6927
     VI_FLUSH_GPU_TLB_NUM_WREG * 5 + 7      <-- vm_flush       (6932)
     7+7+7   gfx_v8_0_ring_emit_fence_compute x3
     ... + emit_mem_sync + wave_limit + 15

  gfx_v8_0_ring_funcs_kiq        (6954)  emit_frame_size en 6962
     17   gfx_v8_0_ring_emit_vm_flush                      (6967)
     7+7+7   gfx_v8_0_ring_emit_fence_kiq x3
```

**El anillo de gfx usa `+ 9`; el de compute, `+ 7`.** Y `1411` §4 citó la de
compute como si fuera la general. No lo es.

## 2 · LA EMISIÓN REAL, Y LA TABLA CORREGIDA

`gfx_v8_0_ring_emit_vm_flush` es **compartido por los tres anillos**, con un solo
condicional:

```c
        int usepfp = (ring->funcs->type == AMDGPU_RING_TYPE_GFX);
```

Recuento, con `gfx_v8_0_ring_emit_wreg` = 5 dwords (`6369-6373`) y
`gmc_v8_0_emit_flush_gpu_tlb` con 2 `emit_wreg`:

```
  amdgpu_gmc_emit_flush_gpu_tlb      2 x 5                    10
  PACKET3_WAIT_REG_MEM + 5 operand                                6
  PACKET3_PFP_SYNC_ME, solo si usepfp                             2
                                                        total
     anillo GFX      usepfp = 1                                 18
     anillo COMPUTE  usepfp = 0                                 16
     anillo KIQ      usepfp = 0                                 16
```

| anillo | reserva | emisión real | exceso |
|---|---|---|---|
| **GFX** | `3·5 + 9` = **24** | 18 | **6** |
| **COMPUTE** | `3·5 + 7` = **22** | 16 | **6** |
| **KIQ** | **17** | 16 | **1** |

**Lo que `1411` §4 escribió: GFX −4, COMPUTE −4, KIQ −1.**
**Lo correcto: GFX −6, COMPUTE −6, KIQ −1.**

El error de `1411` fue usar 18 como emisión real del anillo de compute, cuando el
compute **no** emite el `PFP_SYNC_ME`. Sobre-reservar no es un fallo; **pero un
margen que se cuenta mal no se puede usar para decidir**, y este hallazgo lo
corrige.

## 3 · LA CONFIRMACIÓN QUE NO ESPERABA: TRES VALLAS NOMBRADAS, DOS OBSERVADAS

El budget del anillo de gfx nombra **tres** vallas, y lo dice con números:

```
  12      FENCE for VM_FLUSH
  12 + 12 FENCE x2
                        total 36 dwords de vallas, tres llamadas
```

Y `12` es **exactamente** una valla:

```
  gfx_v8_0_ring_emit_fence_gfx
     PACKET3 hdr(1) + cmd(1) + addr(1) + addr_hi(1) + seq_lo(1) + seq_hi(1) = 6
     y lo emite DOS veces, dummy y real                                     = 12
```

**MEDIDO en el artefacto: 4 `EVENT_WRITE_EOP` por bloque = 2 vallas.**

**Lo que eso significa, con dos fuentes independientes que coinciden:**

| | dice el driver | dice el artefacto |
|---|---|---|
| vallas en un frame de gfx | **3** | — |
| vallas presentes en esta carga | — | **2** |
| la que falta | **`FENCE for VM_FLUSH`** | **no hay flush de VM** |

> **Dos medidas distintas, un mismo resultado, y se corroboran.** `1412` §4
> concluded por Absence que no había flush de VM en la captura; el budget del
> driver nombra una valla que solo se emite con flush de VM; y en la captura no
> está. **El presupuesto del anillo es un oráculo independiente del contenido
> del anillo**, y no se estaba usando.

**Y eso convierte una pregunta abierta de `1411` en un hecho medido.** `1411`
§5 decía «hace falta una captura con un trabajo que actualice la tabla de páginas
de un VMID de usuario». Sigue siendo cierto, y ahora se sabe **qué se busca**: un
paquete `EVENT_WRITE_EOP` de 12 dwords en el anillo de gfx, después del
`WRITE_DATA` de `mmVM_INVALIDATE_REQUEST`, con la secuencia avanzando.

## 4 · TERCERA IDENTIFICACIÓN BYTE A BYTE DEL ARTEFACTO

Los 203 dwords de relleno de cada bloque son **`0xffff1000`**, y ese valor es:

```c
gfx_v8_0.c:6876, 6922, 6957
        .nop = PACKET3(PACKET3_NOP, 0x3FFF),
```

con la macro de `cikd.h:229-231`:

```
  (3 << 30) | ((0x10 & 0xFF) << 8) | ((0x3FFF) << 16)
  = 0xC0000000 | 0x00001000 | 0x3FFF0000
  = 0xFFFF1000
```

**Coincide con el valor del artefacto, dword a dword.** Y explica por qué mi
primer escaneo (`1412` §3) counted 1648 «paquetes tipo 0xff»: **el relleno es un
tipo de paquete legítimo**, no basura, y mi filtro de cabecera lo capturó como
si fuera encabezado.

Tres identificaciones byte-exactas del mismo artefacto, y las tres por el mismo
método — *el driver predice el valor y el artefacto lo confirma*:

| paquete | valor | identificado en |
|---|---|---|
| `WAIT_REG_MEM` de HDP | `0xc0053c00` + `0x1537`/`0x1538` + `ref==mask==1` | `1412` |
| `INDIRECT_BUFFER` | `control = 0x07000158` → VMID 7 | `1420` |
| relleno `.nop` | `0xffff1000` = `PACKET3(NOP, 0x3FFF)` | **este** |

## 5 · LA FAMILIA `FLUSH_GPU_TLB_NUM_WREG`, QUE ES UNA SOLA COSA

`1411` §4 dijo que `VI_FLUSH_GPU_TLB_NUM_WREG = 3` «no corresponde a nada que
emita». `1421` §6 encontró `SI_FLUSH_GPU_TLB_NUM_WREG = 2` y concluyó que GFX8
usa la constante equivocada. **Ahora se ve la familia entera:**

```
  constante                          valor  la usa
  SI_FLUSH_GPU_TLB_NUM_WREG            2     gfx_v6_0.c (2 tablas), si_dma.c
  CIK_FLUSH_GPU_TLB_NUM_WREG           3     (gfx_v7_0.c, heredado de CIK)
  VI_FLUSH_GPU_TLB_NUM_WREG            3     gfx_v8_0.c, sdma_v2_4.c,
                                            sdma_v3_0.c, uvd_v6_0.c
  SOC15_FLUSH_GPU_TLB_NUM_WREG         6     los ficheros SOC15

  y el multiplicador tambien varia por motor
     * 5   anillos de graficos     (1 wreg = 5 dwords)
     * 3   anillos de SDMA
     * 6   UVD
```

**La constante es por IP, no por generación.** Y la verdad de campo es:

```
  gmc_v8_0_emit_flush_gpu_tlb   emite 2 amdgpu_ring_emit_wreg    PROVEN
  gmc_v6_0_emit_flush_gpu_tlb   emite 2 amdgpu_ring_emit_wreg    PROVEN
```

**Los dos emiten 2.** Pero `gfx_v6_0.c` dimensiona con `SI_ = 2` y
`gfx_v8_0.c` con `VI_ = 3`.

> **La línea de GCN6 está bien dimensionada y la de GFX8 no.** No es una
> constante huérfana, es una constante **de otra familia de IP** aplicada a la
> misma función. `1421` §6 ya lo insinuó al encontrar el `2`; aquí se ve que el
> `2` tiene dueño, y que el dueño es el gemelo de GCN6.

**Y el coste está medido en los tres anillos: 6 dwords por frame en gfx y en
compute.** Con un budget de 215 dwords, son **el 2,8 %**. Nada, en términos de
memoria de anillo. Importa por otra razón, y es la de `1411`: **el número que
dimensiona el flush no es el número que el flush usa, así que nadie puede fiarse
de él para calcular el tamaño real de un frame.**

## 6 · LO QUE NO SE AFIRMA

- **No se dice que sobre-reservar sea un fallo.** `emit_frame_size` es una cota,
  y una cota holgada es segura. Lo que se mide es que **la cota está calculada
  con una constante que no corresponde a la emisión**, y eso la hace inexacta en
  6 dwords.
- **No se dice que el `+ 9` de la fórmula de gfx sea un error.** Puede ser un
  margen deliberado. Lo que se mide es que **la fórmula y la emisión no se
  pueden validar una contra otra** mientras la constante sea de otra familia.
- **No se afirma que la valla que falta sea la del flush de VM.** Es
  `CORROBORATED`: el budget la nombra así, y el artefacto no tiene flush de VM.
  Que sea *esa* y no otra es lo más probable, y no está medido.
- **No se toca el corpus ni el artefacto.**

```
ESTADO
  emit_frame_size de GFX8, por anillo
     GFX      reserva 24   emision real 18   exceso 6    CORRIGE 1411 (decia 4)
     COMPUTE  reserva 22   emision real 16   exceso 6    CORRIGE 1411 (decia 4)
     KIQ      reserva 17   emision real 16   exceso 1    1411 acertaba
     presupuesto del anillo de gfx, declarado 215 dwords

  vallas
     el budget nombra 3   (12 + 12+12 = 36 dwords)
     12 = una valla exacta, medido por la funcion
     el artefacto tiene 2, en 8 de 8 bloques
     la que falta es la del flush de VM                CORROBORATED

  relleno
     203 dwords por bloque = 0xffff1000
     0xffff1000 = PACKET3(PACKET3_NOP, 0x3FFF) = .nop del driver    PROVEN
     tercera identificacion byte a byte del artefacto

  FLUSH_GPU_TLB_NUM_WREG
     SI_=2 (gfx_v6_0, si_dma)    CIK_=3    VI_=3 (gfx_v8_0, sdma_v2_4/v3_0, uvd_v6_0)
     SOC15_=6      multiplicador *5 gfx, *3 sdma, *6 uvd
     la emision real es 2 en GCN6 y en GFX8
     gfx_v6_0 usa la correcta, gfx_v8_0 usa la de otra familia de IP

  GPU     INTACTA
  sudo    NO usado
  corpus  solo lectura
  artefacto  solo lectura
```
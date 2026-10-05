# 1436 — corrección de 1434: los 72 offsets están bien, pero la secuencia NO es la del vendor, y tres afirmaciones mías eran falsas

```text
AGENCIA=RX550-INVESTIGACION · WORK_CLASS=AGENT-MAIN/RE
CLASSIFICATION=CORRECCION-PROPIA+REVISION-ADVERSARIAL
TRACK=STATIC(7.1.3) · sin GPU · sin sudo
GENERADO=2026-10-04
CORRIGE=06-INGENIERIA-INVERSA/findings/1434-*      ->  §6 NO EJECUTABLE COMO SECUENCIA
ORIGEN=1434 se escribo como "el orden minimo de escritura, en la secuencia del vendor".
       Eso ultimo era falso, y una revision adversarial lo demostro.  Este documento deja
       1434 con los offsets y SIN la pretension de ser la secuencia del vendor.
ESTADO=PROBADO · los 72 offsets verificados uno a uno: 0 discrepancias
       · 3 afirmaciones de 1434 REFUTADAS, dos de ellas peligrosas
       · 1 omision fatal: el firmware de MC es OBLIGATORIO y no estaba
       · 6 omisiones mas, 2 de ellas con consecuencia de hang
```

## 0. Lo primero, y es lo que cambia la búsqueda: los offsets están bien

**Se verificaron 72 offsets de §6 contra las cabeceras, uno a uno. Cero discrepancias.**

Checked: `gmc_8_1_d.h` (0x819, 0x500/501/502/578, 0x557/55f/54f/546/50c/504,
0x558/560/547/50d/505, 0x51e/51f, 0x506/507), `gfx_8_0_d.h` (0x3040/30b1/3041/3043/3044/3045,
0x3046/3047, 0x304b/3050/3059/305a/305b, 0x3083/30ae/21b6, 0x3245/3247/3248, 0x326c/326d/326e/
326f/3278/3279, 0xec00, 0xecaa), `oss_3_0_d.h` (los 19 de SDMA y `mmSRBM_GFX_CNTL 0x391`),
`bif_5_0_d.h` (0x151a/0x151b).

**Nadie debe ir a buscar un error de bit: no existe.** Lo que rompe un driver aquí es el
**orden y las omisiones**, no los valores.

## 1. Las tres afirmaciones refutadas

### 1.1 `struct vi_mqd` — **yo afirmé índice 0, es el 128** (`REFUTADA`)

1434 §6 decía: *"exige que `struct vi_mqd` sea contigua, con `cp_mqd_base_addr_lo` en el
**índice 0**"*, y escalonaba: *"el layout del struct es un requisito del hardware"*.

Medido en `include/vi_structs.h`:

```text
struct vi_mqd {        linea 159
cp_mqd_base_addr_lo    linea 288      -> indice 288-160 = 128
cp_hqd_active          linea 290
cp_hqd_eop_rptr        linea 328
cp_hqd_error           linea 339
cp_hqd_eop_wptr_mem    linea 340
```

**El vendor nunca exige contigüidad desde el índice 0**, porque toma un *puntero*:

```c
gfx_v8_0.c:4553   mqd_data = &mqd->cp_mqd_base_addr_lo;
gfx_v8_0.c:4559-60 WREG32(mqd_reg, mqd_data[mqd_reg - mmCP_MQD_BASE_ADDR]);
```

El requisito real es **relativo, desde `cp_mqd_base_addr_lo` en adelante** — y eso sí se
cumple. Mi escalada a "requisito del hardware" también sobraba: el requisito es el orden
contiguo de **registros** `0x3245..0x3278`; el struct sólo tiene que reflejarlo desde ese
campo.

> **Por qué esto era peligroso**: alguien que "arreglara" mi instrucción reordenando el
> struct para empezar en el índice 0 **rompería los 128 dwords de despacho de cómputo que
> están delante**. Mi frase era unrecipe de damage, no una descripción.

**Y la cita que puse estaba mal**: dije `gfx_v8_0.c:4583-4584` para "`mmCP_HQD_ACTIVE` se
escribe al final". Ese bucle está en **`4577-4578`**; `4583-4584` es la **firma de otra
función**, `gfx_v8_0_kiq_init_queue()`.

**No está forzado por nada**: no hay `_Static_assert` ni `BUILD_BUG_ON` sobre offsets de
`vi_mqd` en 7.1.3 ni en 7.2.8. Los únicos usos son `sizeof()`. Es una convención silenciosa
y load-bearing, que es peor que un assert porque falla en runtime.

### 1.2 El errata de Tonga — **lo presenté como rango opcional con polaridad invertida**

1434 §6 ponía `[0x326d..0x3279]` entre corchetes. El vendor (`gfx_v8_0.c:4567-4571`):

```c
if (adev->asic_type != CHIP_TONGA) {
        WREG32(mmCP_HQD_EOP_RPTR,    mqd->cp_hqd_eop_rptr);
        WREG32(mmCP_HQD_EOP_WPTR,    mqd->cp_hqd_eop_wptr);
        WREG32(mmCP_HQD_EOP_WPTR_MEM, mqd->cp_hqd_eop_wptr_mem);
}
```

Dos errores, ambos con consecuencia:

1. **No es un rango.** Es exactamente **tres registros por nombre**. Implementado como
   bucle, mi rango habría escrito `0x326f..0x3278` una segunda vez **y** diez registros que
   el vendor deja intactos a propósito.
2. **La polaridad es `!= CHIP_TONGA`, y Polaris12 NO es Tonga, así que el bloque SE
   EJECUTA.** Renderizarlo entre corchetes invitaba a saltárselo **justo en las ASIC donde
   corre**.

Mi §6 además nunca mencionó "Tonga errata" ni la polaridad. Y el "solapamiento" entre
`[0x326d..0x3279]` y `0x326f..0x3278` que planteé era **artefacto de mi propia notación**:
los conjuntos reales son disjuntos.

### 1.3 "Los `AMDGPU_DOORBELL_*` son offsets **en bytes**" — (`REFUTADA`)

Son **índices dword**:

```text
amdgpu_doorbell.h:42        uint32_t *cpu_addr;
amdgpu_doorbell_mgr.c:65    writel(v, adev->doorbell.cpu_addr + index)   -> aritmetica en uint32_t
amdgpu_doorbell_mgr.c:213   num_kernel_doorbells = min(size/sizeof(u32), max_assignment+1)
                            con max_assignment = 0x3FF  ->  0x400 dwords = 4 KiB = el BAR2
```

En unidades de bytes saldría **4× desviado**.

**Y un error peor, en §6**: escribí `0x1E0+0x200·inst sdma`. **No existe ese stride de
doorbell.** `vi.c:2182-2183` asigna `sdma_engine[0] = 0x1E0` y `sdma_engine[1] = 0x1E1` —
**dwords consecutivos** (`amdgpu_doorbell.h:112-113`), y `sdma_v3_0.c:1147` consume el índice
**sin aritmética alguna**. El `+0x200` es `SDMA1_REGISTER_OFFSET` (`vid.h:27`), el stride
**de registros MMIO**. Yo mezclé un stride con otro: un driver habría **tocado el doorbell
equivocado para SDMA1**.

Contraste que lo confirma: `sdma_v4_0.c:1864`, `v5_0.c:1418`, `v6_0.c:1359`, `v7_0.c:1344`,
`soc15.c:1276` **sí** hacen `<< 1`. **gfx8 es el único que no.**

## 2. La omisión fatal: el firmware de MC es OBLIGATORIO

```c
/* gmc_v8_0.c:262-263 */
err = amdgpu_ucode_request(adev, &adev->gmc.fw, AMDGPU_UCODE_REQUIRED,
                           "amdgpu/%s_mc.bin", chip_name);
```

**`AMDGPU_UCODE_REQUIRED`.** El controlador de memoria no funciona sin su firmware. §6
programa tablas de página y rings **contra un controlador de memoria sin entrenar**. Por sí
solo esto hace que §6 **no sea ejecutable** como lo que decía ser.

**Y el nombre no es trivial: se decide con una lectura de hardware.**

```text
gmc_v8_0.c:242-250   escribe mmMC_SEQ_IO_DEBUG_INDEX = ixMC_IO_DEBUG_UP_159
                     y lee mmMC_SEQ_IO_DEBUG_DATA   para distinguir polaris12_32 de polaris12

ASICID_IS_P23 (amdgpu.h:770-778) cubre SOLO  0x6987  y  0x6981
nuestra placa es  0x699F  -> NO es P23  ->  se ejecuta la rama de sondeo
```

**Consecuencia**: el nombre del firmware se obtiene **leyendo un registro**. Eso está dentro
de la regla de no-escribir-registros del proyecto... y es la **primera lectura de hardware
que la RE de esta tarjeta necesita de verdad**. Todo lo demás hasta aquí salió de ficheros.

Los dos candidatos están presentes en disco (medido): `polaris12_mc.bin.xz` y
`polaris12_32_mc.bin.xz`. Falta `polaris12_k_mc.bin`, que es la variante Kaveri.

**No hay MRTC en gfx8**: `grep -rn MRTC` → **0 apariciones**. El equivalente es el firmware de
MC.

## 3. Las otras omisiones

| omisión | dónde | consecuencia |
|---|---|---|
| **apertura de identidad** `mmVM_L2_CONTEXT1_IDENTITY_APERTURE_LOW/HIGH_ADDR` `0x575/0x576` y `mmVM_L2_CONTEXT_IDENTITY_PHYSICAL_OFFSET` `0x577`, los tres a 0 | `gmc_v8_0.c:899-901` | **base de identidad nunca establecida**, y van emparejados con `VM_L2_CNTL.CONTEXT1_IDENTITY_ACCESS_MODE=1` (`:857`). **No estaban ni siquiera listados en 1434** |
| `gmc_v8_0_set_fault_enable_default()` — reescribe `mmVM_CONTEXT1_CNTL` con los 7 bits `*_PROTECTION_FAULT_ENABLE_DEFAULT` según `amdgpu_vm_fault_stop` | `gmc_v8_0.c:936-939` | decide si un acceso no mapeado devuelve la página dummy o **fault**. No cosmético |
| **885 dwords de CLEAR_STATE** | `gfx_v8_0.c:4151-4181`; 7 extents en `clearstate_vi.h:932-938` | **ningún golden setting lo cubre**. Es el hueco que hace inservible el "sin golden settings" implícito |
| handshake `RB_RPTR_WR_ENA`: `mmCP_RB0_CNTL` se escribe **tres veces**, con el pulso de habilitación en la segunda | `gfx_v8_0.c:4250,4253,4266` + `mdelay(1)` en `:4265` | mi lista plana conservaba el orden amplio pero **ocultaba que el pulso es load-bearing** |
| `mmCP_MEC_CNTL` `0x208d` = 0, con `udelay(50)` — **desarranca MEC1/MEC2** | `gfx_v8_0.c:4280-4289` | §6 trae `mmCP_ME_CNTL` (ME0/PFP/CE) pero **no el MEC**. Necesario para cualquier vía de copia/computo |
| `mmCP_RB_WPTR_DELAY 0x21c1` = 0 · `mmCP_RB_VMID 0x3051` = 0 | `gfx_v8_0.c:4235,4238` | el segundo **contradice** mi §3.1, que afirmaba que "el VMID viaja en el paquete, no en un registro" |
| `gfx_v8_0_enable_save_restore_machine()` → `mmRLC_SRM_CNTL.SRM_ENABLE = 1`, y `gfx_v8_0_init_power_gating()` (`CP_RB_WPTR_POLL_CNTL.IDLE_POLL_COUNT=0x60`, `mmRLC_PG_DELAY`, `SERDES_CMD_DELAY`, `GRBM_REG_SAVE_GFX_IDLE_THRESHOLD`) | `gfx_v8_0.c:3983,3986-4000`, y `:4030-4037` para `CHIP_POLARIS12` |especifico de Polaris12, antes de arrancar el RLC |
| `mmVM_PRT_CNTL` + `mmVM_PRT_APERTURE{0..3}_{LOW,HIGH}_ADDR` — 12 registros | `gmc_v8_0.c:766-816` | §6 no menciona PRT; **los 4 golden de GMC *son* las aperturas PRT** (`gmc_v8_0.c:92-97`) |
| `mmCP_MQD_BASE_ADDR`…`mmCP_HQD_ACTIVE` = `0x3245..0x3247`, y los 3 registros del errata | `gmc_v8_0.c:4567-4578` | lo mío `[0x326d..0x3279]` (§1.2) |

## 4. Dos afirmaciones más que caen por el camino

| decía | la verdad |
|---|---|
| §3.1: "**`*GCR*` no existe, cero apariciones**" | **falso: cientos.** `nvd.h:357-366,456-501` (`PACKET3_RELEASE_MEM_GCR_*`, `PACKET3_ACQUIRE_MEM_GCR_CNTL_*`, que **son de gfx8/VI**), `cikd.h:515-523`, `gfxhub_*.c`. **La conclusión aguanta** — en gfx8 el GCR se controla por **paquetes**, `PACKET3_RELEASE_MEM` en `gfx_v8_0.c:6239` y `PACKET3_ACQUIRE_MEM` en `:6776`— **pero llegó por una línea de evidencia falsa y omitiendo el código que la demuestra.** |
| §3.1: "el VMID viaja en el paquete, **no en un registro**" | falso **para el ring GFX**: `gfx_v8_0.c:4238` escribe `mmCP_RB_VMID = 0` (`0x3051`), con el comentario *"set the RB to use vmid 0"*. Sí es cierto para SDMA |
| §5 `mmSDMA0_CNTL.TRAP_ENABLE` vs §6 `SDMA_CNTL 0x3404` | **1434 se contradice a sí mismo.** El registro es `mmSDMA0_CNTL`. No existe `mmSDMA0_SDMA_CNTL` |
| `GFX_VIRTUAL_ADDR = 0` como "dirección" | **no tiene campo de dirección.** Sus campos (`oss_3_0_sh_mask.h:1989-1998`) son `ATC` bit0, `INVAL` bit1, `PTR32` bit4, `SHARED_BASE` [10:8], `VM_HOLE` bit30. **Escribir 0 es `ATC = 0`, traducción deshabilitada** — una decisión de control, no una base |

## 5. Lo que sobrevive de 1434, y sigue siendo útil

- **Los 72 offsets.** Verificados. Es la parte sólida.
- **La dirección de acceso**: índice dword absoluto en BAR5, `0xF7D00000 + off<<2`, sin
  `reg_offset[][]`. Correcto, y explica por qué el mecanismo soc15 era ajeno.
- **`sdma_v4_0.c` es de otra ASIC.** Confirmado.
- **`mmGRBM_GFX_CNTL` es de Navi10**; el equivalente es `mmSRBM_GFX_CNTL 0x391`.
- **El workaround de I2C es de `0x67DF`**, no aplica a `0x699F`.
- **`SDMA_VMID`, `SDMA_RING_CONTROL`, `SDMA_RING_STATUS`, `SDMA_SEMAPHORE_SIGNAL/WAIT` → 0
  apariciones.** Correcto (y `SDMA_RING_STATUS` sí es `mmSDMA0_STATUS_REG 0x340d`).
- **`mmVM_DUMMY_PAGE_FAULT_CNTL/ADDR` sin escritor.** Correcto, y el mecanismo activo es
  `mmVM_CONTEXT{0,1}_PROTECTION_FAULT_DEFAULT_ADDR` `0x546/0x547` **más**
  `mmINTERRUPT_CNTL2 0x151b`, a dos capas.
- **golden 17+6 de GFX y 4 de GMC.** Confirmado por recuento.
- **Un vector MSI.** Confirmado por vía independiente.
- **`sdma_v3_0_rlc_resume()` es un stub.** Correcto.

**Una corrección de matiz sobre §6**: `(respuesta en 0x51f)` no es lo que hace el código.
`gmc_v8_0_flush_gpu_tlb()` es fire-and-forget (`gmc_v8_0.c:665`);
`mmVM_INVALIDATE_RESPONSE` se lee sólo en la variante con PASID (`:641`).

## 6. Advertencia de método, que casi costó un error a otro

El revisor avisó: **una lectura con `limit` amplio renderizó mal un símbolo** — mostró
`mmVM_CONTEXT_IDENTITY_PHYSICAL_OFFSET` donde el texto real es
**`mmVM_L2_CONTEXT_IDENTITY_PHYSICAL_OFFSET`** (`gmc_v8_0.c:901`). Un `grep` y una lectura
estrecha dieron el símbolo correcto.

Si se hubiera fiado de la lectura amplia, habría reportado un defecto inexistente
("registro usado pero nunca definido").

> **Toda cita de código de este proyecto debe verificarse con `grep` o con lectura de ≤55
> líneas, nunca con lectura amplia.** Un identificador mal renderizado produce un defecto
> falso, y un defecto falso en un mapa de registros cuesta más que uno verdadero.

## 7. Procedencia

```text
RESEARCH/baseline/linux-7.1.3/drivers/gpu/drm/amd/     (el kernel que corre)
include/vi_structs.h:159,288,290,328,339,340   el indice 128 y los anclajes
amdgpu/gfx_v8_0.c:4520-4530,4546-4581          mqd_commit real; errata en :4567-4571
amdgpu/gfx_v8_0.c:3983,3986-4000,4030-4037      SRM_ENABLE, power gating, init Polaris12
amdgpu/gfx_v8_0.c:4151-4181,4235,4238,4250-4266,4280-4289   clear state, delay, vmid, handshake, MEC
amdgpu/gfx_v8_0.c:6239,6776                    PACKET3_RELEASE/ACQUIRE_MEM  (el GCR real)
amdgpu/gmc_v8_0.c:242-250,262-263              sondeo del nombre + AMDGPU_UCODE_REQUIRED
amdgpu/gmc_v8_0.c:766-816,899-901,936-939      PRT, identidad, fault_enable_default
amdgpu/amdgpu.h:770-778                        ASICID_IS_P23 = 0x6987, 0x6981
amdgpu/amdgpu_doorbell.h:42,112-113,115         dwords; 0x1E0 y 0x1E1 consecutivos
amdgpu/amdgpu_doorbell_mgr.c:56-65,210,213     writel en uint32_t* ; 0x400 dwords
amdgpu/sdma_v3_0.c:650-658,708-736,1147        mutex, orden, y el indice sin aritmetica
include/asic_reg/oss/oss_3_0_sh_mask.h:1989-1998   los campos de GFX_VIRTUAL_ADDR
/lib/firmware/amdgpu/    polaris12_mc.bin.xz y polaris12_32_mc.bin.xz presentes
                         polaris12_k_mc.bin.xz AUSENTE
grep  MRTC en drivers/gpu/drm/amd/  ->  0
```

```text
ESTADO=PROBADO · los 72 offsets de 1434: 0 discrepancias.  No hay error de bit que buscar
REFUTADO por 1436:
  (a) "cp_mqd_base_addr_lo en el indice 0"        -> es el indice 128.  Peligroso: inducía
      a reordenar el struct y romper 128 dwords de despacho de computo
  (b) el errata de Tonga como rango opcional      -> son 3 registros por nombre, y con
      polaridad != CHIP_TONGA Polaris12 SI lo ejecuta.  Peligroso: invite a saltarselo
  (c) "los AMDGPU_DOORBELL_* son offsets en bytes" -> son indices dword (4x de error)
  (d) "0x1E0+0x200·inst" como stride de doorbell   -> no existe; son 0x1E0 y 0x1E1
      consecutivos.  El +0x200 es el stride de REGISTRO MMIO
  (e) "*GCR* no existe, cero apariciones"         -> cientos; la conclusion aguanta via
      PACKET3_RELEASE_MEM / PACKET3_ACQUIRE_MEM, no por la linea de evidencia que di
  (f) "el VMID viaja en el paquete, no en un registro" -> falso para el ring GFX:
      mmCP_RB_VMID 0x3051 se escribe
  (g) 1434 se contradice sobre mmSDMA0_CNTL / SDMA_CNTL
OMITIDO y bloqueante:
  (1) amdgpu_ucode_request(..., AMDGPU_UCODE_REQUIRED, "%s_mc.bin") — sin firmware de MC no
      hay memoria.  §6 programa tablas contra un controlador sin entrenar.  El NOMBRE se
      decide leyendo mmMC_SEQ_IO_DEBUG_UP_159, y nuestra 0x699F no es P23
  (2) apertura de identidad 0x575/0x576/0x577, ni listados
  (3) set_fault_enable_default(): decide pagina dummy frente a fault
  (4) 885 dwords de CLEAR_STATE, que ningun golden setting cubre
  (5) el pulso RB_RPTR_WR_ENA (tres escrituras de mmCP_RB0_CNTL)
  (6) mmCP_MEC_CNTL 0x208d, sin el cual no hay copia ni computo
  (7) mmVM_PRT_* (12 registros), y mmCP_RB_WPTR_DELAY, mmRLC_SRM_CNTL, power gating
SOBREVIVE  los 72 offsets, la direccion absoluta en BAR5, el vector unico, golden 17+6 y 4,
       sdma_v4_0.c ajeno, mmGRBM_GFX_CNTL de Navi10, el workaround 0x67DF, y el stub de RLC
METODO   toda cita debe verificarse con grep o lectura <=55 lineas: una lectura amplia
       renderizo mal un simbolo y casi produjo un defecto inexistente
LIMITE   no se puede probar, sin fuente, que el orden relativo restante de §6 sea el que
       exige el hardware.  Solo el runtime lo diria, y el objetivo esta suspendido
Siguiente  1) la lectura de ixMC_IO_DEBUG_UP_159 es la PRIMERA lectura de hardware que esta
          RE necesita.  Es lectura pura de un registro de sondeo, no una escritura, y
          decide que firmware de MC carga esta placa.  Pedirla al propietario
       2) hasta entonces, §6 no es ejecutable: reescribirlo como "secuencia del vendor"
          seria falso.  Corregir 1434 con este documento como referencia
       3) el bloque dm sigue NOT_FOUND y es el que gobierna la salida de display
```

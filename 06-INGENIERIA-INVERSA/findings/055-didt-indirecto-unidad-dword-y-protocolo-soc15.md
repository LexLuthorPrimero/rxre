# 055 · DIDT de Polaris12: bus indirecto, y la unidad del offset resuelta por contrato

`CLASSIFICATION=DOCUMENTATION` · `TRACK=STATIC` · `WORK_CLASS=READ_ONLY/EVIDENCE`
`WRITE_EXECUTION=NONE` · `MODIFICATIONS=0` · `RUNTIME=NOT_RUN` · `GPU INTACTA`
`SCOPE_CLAIM=.write-lock/smu` · `COMPLEMENTS=053` · `GATE=asic_resolver v1.0.0`

---

## CUDA principal

El `offset` de `gpu_pt_config_reg` **no es un offset de byte**. Es un índice de
bus indirecto, y el protocolo son **dos** registros: se escribe el índice, se
lee el dato. La unidad del registro MMIO subyacente es **dword**, por contrato
explícito en la documentación del kernel, no por inferencia.

---

## 1. Las seis capas, de la tabla al MMIO

```
smu7_program_pt_config_registers(hwmgr, tabla)        smu7_powertune.c:897
   tabla[i].offset = ixDIDT_SQ_WEIGHT0_3 = 0x10       ◄ ÍNDICE, no byte
        │
        ▼
CGS_WREG32_FIELD_IND(device, space, reg, field, val)  cgs_common.h:133
   escribe (read & ~MASK) | val << SHIFT
        │  ix##reg pega el prefijo ix al nombre → ixDIDT_...
        ▼
cgs_write_ind_register(dev, space, index)              cgs_common.h:168
        │
        ▼
amdgpu_cgs_write_ind_register(cgs_device, space, index) amdgpu_cgs.c
   switch (space) { case CGS_IND_REG__DIDT: WREG32_DIDT(index) }
        │
        ▼
amdgpu_reg_didt_wr32(adev, reg, v)                     amdgpu_reg_access.c:123
   if (!adev->reg.didt.wreg) { dev_err_once(...); return; }   ◄ VTABLE
   adev->reg.didt.wreg(adev, reg, v);
        │
        ▼
soc15_didt_wreg(adev, reg, v)                          soc15.c   ◄ GFX8 = Polaris12
   address = SOC15_REG_OFFSET(GC, 0, mmDIDT_IND_INDEX);
   data    = SOC15_REG_OFFSET(GC, 0, mmDIDT_IND_DATA);
   spin_lock_irqsave(&adev->reg.didt.lock, flags);
   WREG32(address, reg);      ◄ ESCRIBE EL ÍNDICE
   r = RREG32(data);          ◄ LEE EL DATO
   spin_unlock_irqrestore(&adev->reg.didt.lock, flags);
        │
        ▼
RREG32(reg)  =  amdgpu_device_rreg(adev, reg, 0)       amdgpu.h:1293
```

## 2. El protocolo indirecto: dos registros, y son consecutivos

```
gfx_8_0_d.h:2775   mmDIDT_IND_INDEX   0x3280
gfx_8_0_d.h:2776   mmDIDT_IND_DATA    0x3281
```

```
0x3280   ← se escribe el índice (ixDIDT_*, p.ej. 0x10)
0x3281   ← se lee el valor
```

Diferencia de `1`. **Porque el offset está en dwords y estos dos registros
ocupan dwords contiguos.** Si estuviera en bytes, serían `0x3280` y `0x3284`.

```
DIDT_IND_PAIR_IS_DWORD_ADJACENT = PROVEN
  0x3280 → 0x3281, diferencia 1
  la unidad del offset es dword-index, no byte
  corroborated por el propio kernel (§4)
```

Los índices van en `0x10`, `0x11`, `0x12`, `0x20`… `0x31`. Si `0x10` fuera un
byte offset, el acceso caería en un registro sin relación con DIDT.

## 3. La vtable: seis ASIC, una función por ASIC

```
amdgpu_reg_access.c:47    adev->reg.didt.rreg = NULL;      ◪ inicialización
amdgpu_reg_access.c:116   if (!adev->reg.didt.rreg) {
                            dev_err_once(adev->dev, "DIDT register read not supported\n");
                            return 0;
                          }
```

```
cik.c:1993    adev->reg.didt.rreg = &cik_didt_rreg;     SI
vi.c:1467     adev->reg.didt.rreg = &vi_didt_rreg;      VI
nv.c:645      adev->reg.didt.rreg = &nv_didt_rreg;      NAVI
soc15.c:973   adev->reg.didt.rreg = &soc15_didt_rreg;   GFX8  ◄ NUESTRO
soc21.c:599   adev->reg.didt.rreg = &soc21_didt_rreg;   ARCTURUS
```

```
DIDT_ACCESS_IS_PER_ASIC_VTABLE = PROVEN
  nuestra: soc15_didt_rreg / soc15_didt_wreg   soc15.c:268
  si el ASIC no asigna la vtable, la lectura devuelve 0 y escribe un error
  ⇒ no hay fallback generico: DIDT o existe para tu ASIC o no se puede tocar
```

**Consecuencia para un driver propio**: una lectura DIDT que devuelva `0` no es
"el registro vale 0". Puede ser la vtable nula. Son indistinguibles desde el
valor de retorno, y solo el log los separa. Es el mismo patrón que el
`return 0` incondicional del canal SMC en 048: **el valor de retorno no
transporta el error**.

## 4. La unidad, declarada por el propio kernel

```
amdgpu_reg_access.c:355-362

/**
 * amdgpu_device_rreg - read a memory mapped IO or indirect register
 *
 * @adev: amdgpu_device pointer
 * @reg: dword aligned register offset        ◄ UNIDAD DECLARADA
 * @acc_flags: access flags which require special behavior
 */
```

Y la operación lo confirma:

```
:372   if ((reg * 4) < adev->rmmio_size) {     ◄ multiplica por 4
:376       ret = readl(((void __iomem *)adev->rmmio) + (reg * 4));
:379   else
:380       ret = amdgpu_reg_pcie_rd32(adev, reg * 4);
```

```
REGISTER_OFFSET_UNIT_IS_DWORD = PROVEN
  fuente: la doc de amdgpu_device_rreg declara "dword aligned register offset"
  confirmacion operativa: reg * 4 en ambas ramas
  contraste: si fuera byte, el *4 no estaria

  esto NO es una inferencia mia. la unidad esta escrita en el corpus.
```

Con esto **queda cerrado el patrón de mis errores de unidad**:

```
mmGRBM_STATUS2 = 0x2002   dword, byte offset 0x8008      RE-03-A, corregido
PTBA                      address >> 12, no byte        RE-13
table[i].offset          indice de bus, no byte        este documento
SOC15_REG_OFFSET         base + reg, en dword           soc15_common.h:36
```

Cinco puntos donde un mismo numero significa algo distinto en cada capa. La
regla `UNIT_MISMATCH` tiene ahora su contraejemplo medido.

## 5. El bus se selecciona por enum, y hay siete

```
include/cgs_common.h:34-42
  CGS_IND_REG__PCIE
  CGS_IND_REG__SMC
  CGS_IND_REG__UVD_CTX
  CGS_IND_REG__DIDT
  CGS_IND_REG_GC_CAC      ◄ ojo: sin doble guion bajo
  CGS_IND_REG_SE_CAC      ◄ ídem
  CGS_IND_REG__AUDIO_ENDPT
```

```
INDIRECT_BUS_NAMING_IS_INCONSISTENT = PROVEN
  cuatro con __ doble tras REG, dos con guion simple
  la unica diferencia entre ambos grupos es el prefijo del HWIP (GC vs SE)
  ⇒ buscar "CGS_IND_REG__GC_CAC" da 0 y parece ausencia. es otro nombre.
```

Quinto caso nominal de la serie. `CGS_IND_REG_GC_CAC` y
`CGS_IND_REG__SE_CAC` no llevan el doble guion, y buscar el nombre "correcto"
por coherencia de estilo produce `0`.

## 6. `smu7_enable_didt`: habilitación por capability, no por ASIC

```
smu7_powertune.c:850
   :857   didt_block = DIDTBlock_Info;                   ◄ por defecto
   :858   if ((chip_id == CHIP_POLARIS11) &&
   :859       (adev->pdev->subsystem_vendor != 0x106B))   ◄ Apple, no AMD
   :860       didt_block = Polaris11_DIDTBlock_Info;
   :863   block_en = PP_CAP(PHM_PlatformCaps_SQRamping) ? en : 0;
   :864   CGS_WREG32_FIELD_IND(device, CGS_IND_REG__DIDT, DIDT_SQ_CTRL0,
                               DIDT_CTRL_EN, block_en);
   :867   didt_block &= ~SQ_Enable_MASK;
   :868   didt_block |= block_en << SQ_Enable_SHIFT;
   ...  se repite por DB, TD, TCP
```

```
DIDT_BLOCK_ENABLES_ARE_PER_CAPABILITY = PROVEN
  SQ  → PHM_PlatformCaps_SQRamping
  DB  → PHM_PlatformCaps_DBRamping
  TD  → PHM_PlatformCaps_TDRamping
  TCP → PHM_PlatformCaps_TCPRamping
  cada bloque se habilita por su propia capability, no todas juntas
```

La rama `POLARIS11` con `subsystem_vendor != 0x106B` (Apple) no es nuestra por
doble motivo: chip distinto y.subsystem distinto. El `PP_CAP` decide si el
bloque se activa.

## 7. El broadcast por SE, con su mutex

```
smu7_powertune.c:958   smu7_enable_didt_config()
   :966   amdgpu_gfx_rlc_enter_safe_mode(adev, 0);
   :967   mutex_lock(&adev->grbm_idx_mutex);
   :970   value2 = cgs_read_register(device, mmGRBM_GFX_INDEX);
   :971   for (count = 0; count < num_se; count++) {
   :975       value = INSTANCE_BROADCAST_WRITES_MASK
   :976            | SH_BROADCAST_WRITES_MASK
   :977            | (count << SE_INDEX__SHIFT);
   :978       cgs_write_register(device, mmGRBM_GFX_INDEX, value);
   :979       programa GCCACConfig_Polaris11
   :1002      programa DIDTConfig_Polaris12
          }
   :1013  cgs_write_register(device, mmGRBM_GFX_INDEX, value2);   ◄ restaura
   :1014  smu7_enable_didt(hwmgr, true);
   :1016  cgs_write_register(device, mmGRBM_GFX_INDEX, value2);
```

```
num_se = adev->gfx.config.max_shader_engines    ◄ 2 en nuestra RX550
```

```
GRBM_GFX_INDEX_SERIALIZATION = PROVEN
  adev->grbm_idx_mutex  protege mmGRBM_GFX_INDEX
  se toma antes de cambiar de SE y se suelta despues de restaurar
  combinado con amdgpu_gfx_rlc_enter_safe_mode(adev, 0)
```

Para un driver propio: `mmGRBM_GFX_INDEX` es un **selector global**, no un
registro por SE. Cambiarlo redirige los MMIO siguientes a otra unidad. Por eso
el mutex y el modo seguro de RLC no son opcionales: son la condición para que
dos hilos no se pisen el selector.

```
MMIO_REDIRECT_VIA_INDEX_REGISTER = PROVEN_DERIVED
  mmGRBM_GFX_INDEX selecciona la instancia destino de los MMIO siguientes
  con SH_BROADCAST_WRITESMask se escriben todas a la vez
  ⇒ el direccionamiento de un MMIO depende de un registro de estado previo
     esto es una Generalización: el corpus muestra el caso, no la regla general
```

## 8. GCCAC y DIDT: por qué P12 comparte uno y no el otro

```
GCCACConfig_Polaris10[]   20 entradas
GCCACConfig_Polaris11[]   20 entradas
GCCACConfig_Polaris12[]    0 apariciones en smu7_powertune.c

DIDTConfig_Polaris10[]    109 entradas
DIDTConfig_Polaris11[]    109 entradas
DIDTConfig_Polaris12[]    109 entradas
```

```
GCCAC_POLARIS12_TABLE_DOES_NOT_EXIST = PROVEN_ABSENT
  busqueda por nombre exacto en smu7_powertune.c: 0 apariciones
  el corpus esta completo (fichero leido entero, 2361+ lineas)
  ⇒ la rama :999 no "elige" la tabla de P11: es la unica que existe
```

Y las diferencias DIDT entre P11 y P12, que son 26 líneas y todas del bloque SQ:

```
DIDT_P11_vs_P12_DIFFERS_ONLY_IN_SQ = PROVEN
  109 entradas en ambas, mismos offsets, mismos campos
  26 valores distintos, todos ixDIDT_SQ_*

  ixDIDT_SQ_CTRL2__MAX_POWER_DELTA          0x3fff → 0x3853
  ixDIDT_SQ_CTRL2__SHORT_TERM_INTERVAL_SIZE 0x000f → 0x005a
  ixDIDT_SQ_STALL_CTRL__HI_POWER_THRESHOLD   0x01aa → 0x0ebb
  ixDIDT_SQ_TUNING_CTRL__TUNING_ENABLE       0x0000 → 0x0001   ◄ P12 lo activa
  ixDIDT_SQ_TUNING_CTRL__MAX_POWER_DELTA_HI  0x0dde → 0x3853
  ixDIDT_SQ_TUNING_CTRL__MAX_POWER_DELTA_LO  0x0dde → 0x3153   ◄ asimétrico
  ixDIDT_SQ_CTRL0__MAX_STALLS_ALLOWED_HI     0x0008 → 0x0010
  ixDIDT_SQ_CTRL0__MAX_STALLS_ALLOWED_LO     0x0008 → 0x0010

  bloques TD y TCP: byte a byte idénticos
  contra DIDTConfig_Polaris10 solo difieren 6 líneas
```

```
POLARIS12_INHERITS_DIDT_TD_TCP_FROM_POLARIS11 = PROVEN
  y redefine el bloque SQ
  la activacion del tuning SQ (0 → 1) es la diferencia de mayor consecuencia
```

## 9. Estado

```
PROVEN   protocolo indirecto de 2 registros: INDEX 0x3280, DATA 0x3281
PROVEN   el offset de la tabla es indice de bus, no byte
PROVEN   unidad del offset MMIO = dword, declarada en amdgpu_device_rreg
PROVEN   bus indirecto por vtable, 6 implementaciones, GFX8 = soc15
PROVEN   sin vtable asignada, la lectura devuelve 0 y registra error
PROVEN   7 buses indirectos, nomenclatura inconsistente de guion
PROVEN   bloques DIDT habilitados por capability individual
PROVEN   mmGRBM_GFX_INDEX es selector global, protegido por mutex
PROVEN   GCCACConfig_Polaris12 PROVEN_ABSENT, P12 usa la de P11
PROVEN   DIDT P11 vs P12: 26 diferencias, todas en ixDIDT_SQ_*

NOT_DETERMINED   semantica fisica de los pesos WEIGHT0..11
NOT_DETERMINED   por que TD/TCP se heredan sin cambios de P11
NOT_DETERMINED   SIGNIFICADO de SH_BROADCAST_WRITES_MASK
NOT_DETERMINED   si RLC safe mode reordena la programacion o solo la protege
NOT_DETERMINED   DIDTBlock_Info: donde vive la mascara de habilitacion
NOT_READ         DIDT_SQ_CTRL0__DIDT_CTRL_EN en el header de GFX8
```

## 10. Fallo nominal 35

| # | Busqué | Realidad |
|---|---|---|
| 35º | `SOC15_REG_OFFSET_IO` como macro de MMIO directo | no existe en 7.1.3; el acceso directo es `__WREG32_SOC15_RLC__`, con otro nombre |
| 36º | `amdgpu_reg_didt_rd32` en `amdgpu/*.c` con firma `uint32_t` | es `u32` y está en `amdgpu_reg_access.c`; mi regex exigía el tipo literal |

---

```
REGISTER_OFFSET_UNIT_IS_DWORD  cierra el patrón de errores de unidad
GPU INTACTA · WRITE_EXECUTION NONE · MODIFICATIONS 0
B_RUNTIME NOT_EXECUTED · GATE asic_resolver v1.0.0 SELF_TEST OK
```

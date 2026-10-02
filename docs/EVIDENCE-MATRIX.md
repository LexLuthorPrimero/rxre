# EVIDENCE-MATRIX — quién sostiene qué

> Cada fila es una afirmación que alguien (**no** este fichero) sostiene, con el
> estado que merece y el artefacto que lo respalda. El objetivo es que nadie vuelva a
> investigar una fila `PROVEN`, y que nadie cite una fila `NOT_DETERMINED` como hecho.
>
> `TYPE`: FACT · OBSERVATION · MEASUREMENT · DERIVATION · MODEL_CHOICE · REQUIREMENT ·
> POLICY · IMPLEMENTATION · TEST · CONCLUSION · HYPOTHESIS · ASSUMPTION · LIMITATION ·
> ERROR · NEGATIVE_RESULT · CONTRADICTION
> `STATE`: PROVEN · OBSERVED · CORROBORATED · REFUTED · NOT_DETERMINED · NOT_FOUND ·
> NOT_AVAILABLE · NOT_OBSERVED · NOT_IN_CORPUS · PARTIAL · DEFERRED
>
> `LAST_VERIFIED: 2026-10-02 - revkit/`. Las filas EV-14 a EV-24 se
> añadieron al obtener acceso root al debugfs; las anteriores mantienen su
> verificación original. Verificado = re-leído el artefacto citado, o
> reejecutada la herramienta, en esa fecha.

---

## RE-01 · El path de ring no puede observar completion del invalidate

```
TYPE    DERIVATION
STATE   PROVEN
SOURCE  06-INGENIERIA-INVERSA/findings/017-vm-invalidate-gfx8-function-always.md §3
LOCATION gfx_v8_0.c:6199-6207        PACKET3(PACKET3_WAIT_REG_MEM,5) + 6 payload
        amdgpu_vm.h / vi.h            FUNCTION(0)=always, ref=0, mask=0
PRODUCER gfx_v8_0_ring_emit_vm_flush()
CONSUMER hardware; el page walker, indirectamente
UNIT    bits de codificación del paquete
VERSION GFX8 · ambos corpus (7.1.3 y 7.2.8)
CONFIDENCE alta — el argumento decisivo es el mask=0, que no admite lectura alternativa
DEPENDS —  (no depende de nada; es raíz)
RUNTIME NOT_RUN
```

Por qué `mask=0` cierra la discusión: la ficha es `WAIT_REG_MEM` con
`FUNCTION=always`, luego no hay comparación. Y **aunque** la función fuera `==`,
`(reg & 0) == (0 & 0)` es `0 == 0`, verdadero en la primera lectura. Un `mask=0`
no puede discriminar completion bajo ninguna interpretación.

## RE-02 · Esperar completion del invalidate es `NOT_IMPLEMENTABLE`

```
TYPE    CONCLUSION
STATE   PROVEN_DERIVED (sobre RE-01 + ausencia de registro de ack)
SOURCE  018-execution-order-invalidacion-gfx8.md §CUDA
LOCATION barrido de gmc_8_2 / gca de ATC-L1-L2; no existe mmVM_INVALIDATE_RESPONSE
        utilizable como ack en el path de ring de GFX8
PRODUCER —
CONSUMER —
VERSION GFX8
CONFIDENCE alta
DEPENDS RE-01
```

**Matiz que el propio documento deja y que no debe perderse**: esto cierra la
*espera explícita*, no el *orden de ejecución*. Que el invalidate se haya completado
antes del siguiente IB sigue siendo `NOT_DETERMINED` y medible (frontera F1).

## RE-03 · `VM_INVALIDATE_REQUEST` no tiene granularidad en GFX8

```
TYPE    FACT
STATE   PROVEN
SOURCE  019-atc-l2-invalidation-gfx8.md
LOCATION mmVM_INVALIDATE_REQUEST 0x51e, 16 bits, un bit por VMID (gmc_8_1_d.h)
        gmc_v8_0.c:661-666  flush_gpu_tlb ignora flush_type y vmhub
VERSION GFX8 (contrastado con GFX9+, que sí tiene INVALIDATE_L1_PTES / L2 / 4K)
CONFIDENCE alta
CONFIDENCE nota: 023-pte §4 corrige la cabecera citada — gmc_v8_0.c incluye gmc_8_1_d.h,
        no gmc_8_2_d.h. Los 15 offsets comparados coinciden 15/15, así que ninguna
        conclusión cambia, pero la atribución de cabecera era errónea en 017/018/019
CONTRADICTS cualquier pregunta "¿qué nivel de TLB se invalida?" en GFX8: no tiene encoding
```

## RE-04 · El productor de PTE en GFX8 es un paquete SDMA de 9 dwords

```
TYPE    DERIVATION
STATE   PROVEN
SOURCE  023-pte-productor-sdma-gfx8.md §CUDA, §1
LOCATION sdma_v3_0.c  (los tres productores)
        tonga_sdma_pkt_open.h:37   SDMA_OP_GEN_PTEPDE = 12
        amdgpu_vm.h:57-88          codificación de flags
        amdgpu_vm.h:185-186       USE_CPU_FOR_GFX / USE_CPU_FOR_COMPUTE
VERSION GFX8
CONFIDENCE alta
LIMITATION el finding es UNTRACKED en git. Su texto es la única fuente de RE-04 y RE-05
```

**Consecuencia de diseño, y es la más accionable de la línea**: el encoder de PTE del
driver propio es un emisor de paquete. No hay que implementar un `writeq` de page
tables. Los otros dos paquetes (`SDMA_OP_WRITE` para `count < 3`, `SDMA_OP_COPY` para
el bloque grande de system pages) son optimizaciones del driver de referencia.

## RE-05 · `AMDGPU_PTE_PRT` no es un tipo de entrada en GFX8

```
TYPE    DERIVATION
STATE   PROVEN_ABSENT (para el rol de "tipo de entrada en GFX8")
SOURCE  023-pte-productor-sdma-gfx8.md §3
LOCATION gmc_v8_0.c:686     bits 40-63 reservados en el PTE de GFX8
        gmc_v8_0.c:722     *flags &= ~AMDGPU_PTE_PRT
        amdgpu_vm.h:73     AMDGPU_PTE_PRT = bit 51
        gmc_v8_0.c:792-810 mmVM_PRT_APERTURE{0..3}_{LOW,HIGH}_ADDR + VM_PRT_CNTL
VERSION GFX8 (GFX6/7 tbán borran; GFX9/10 tbán pone)
CONFIDENCE alta
LIMITE   NO verificado que el hardware trate el bit 3 del PTE como reservado. Eso es lo
        que haría segura la línea &= ~PRT. Requiere RUNTIME -> N4
```

## RE-06 · `emit_frame_size` de GFX8 reserva el peor caso

```
TYPE    MEASUREMENT
STATE   PROVEN
SOURCE  021-frame-budget-gfx8-peor-caso.md
LOCATION gfx_v8_0.c:6878 (GFX)   172 dw declarados
        gfx_v8_0.c:6929-ish (compute) 109 dw
        CE_META 8 activo / 14 declarado    DE_META 21 activo / 31 declarado
VERSION GFX8
CONFIDENCE alta
VERIFICADO POR   pm4dw, reejecutado el 2026-10-01: DECLARED 172 / 109
                 (needs --struct gfx_v8_0_ring_funcs_gfx, no el nombre del tipo)
LIMITE   los handlers `write_multiple` de ce_meta/de_meta salen NOT EXPANDED; el 172 es
        cota superior declarada, no el caso activo
```

## RE-07 · Sobre-reserva de 5 dwords en el vm-flush de GFX8

```
TYPE    MEASUREMENT
STATE   PROVEN
SOURCE  020-vmflush-dword-budget-gfx8.md
LOCATION vi.h:27                    VI_FLUSH_GPU_TLB_NUM_WREG = 3
        gmc_v8_0.c:678, 681         2 llamadas reales a amdgpu_ring_emit_wreg
        gfx_v8_0.c:6929             N*5 + 7        (compute)  declarado 22, real 17
        gfx_v8_0.c:6964             literal 17     (kiq)      declarado 17, real 17
VERSION GFX8
CONFIDENCE alta — el KIQ que declara a mano y coincide exacto confirma que el excess
        viene de la constante y no de una lectura del código
VERIFICADO POR   recuento directo reejecutado el 2026-10-01 (2 emit_wreg, líneas 678 y
                 681) + pm4dw con --macro VI_FLUSH_GPU_TLB_NUM_WREG=3
CONSECUENCIA     ningún ring infra-reservado. Sobre-reservar es correcto: emit_frame_size
                 es una reserva, no un límite. Los 19/17 dw reales son lo que un driver
                 propio debe reservar.
```

## RE-08 · La convención `n = payload − 1` de PACKET3, medida

```
TYPE    MEASUREMENT
STATE   PROVEN
STATE_2 para la SEMÁNTICA del hardware: NOT_DETERMINED (N1)
SOURCE  023-pm4-count-convencion-medida.md
PRODUCER 08-ARQUITECTURA/tools/pm4_count_census.py  (--only=fx8)
LOCATION path GFX8: gfx_v6_0, gfx_v7_0, gfx_v8_0, gmc_v8_0, sdma_v3_0
CONFIDENCE alta
VERIFICADO POR   reejecutado 2026-10-01: 68 contables, 22 no contables, n-payload=-1 en
                 68/68, rc=0. El árbol completo da 170/171.
CAPACIDAD DE FALLAR  mutante payload+2 -> 1/172, rc=1. El criterio se endureció dos veces:
                 "−1 presente en la distribución" pasaba con 1 de 172 y salía rc=0
LIMITATION 22 emisiones NO contables, declaradas UNKNOWN con motivo (rama/loop entre
            header y fin). No son 0: son desconocidas.
LIMITE DURO  que el encoding sea coherente NO dice que el hardware lo interprete así.
            Mismo patrón que RE-01: legal ≠ significativo.
```

## RE-09 · `COND_EXEC` es inerte en GFX8

```
TYPE    DERIVATION
STATE   PROVEN (que no puede descartar) / NOT_DETERMINED (qué campo lee el hardware)
SOURCE  022-cond-exec-inerte-en-gfx8.md §CUDA, enmendado por RE-08
LOCATION gfx_v8_0.c:6320-6332  init_cond_exec = si (solo ring GFX)
        set_preempt_cond_exec  -> no lo llama nunca
        preempt_ib             -> no asignado
VERSION GFX8
CONFIDENCE alta para la inactividad; la ambigüedad del campo es real y con causa nombrada
ENMENDADO POR RE-08: dw4 es el CUARTO payload, no un extra fuera del payload
```

El texto de `022` §4 afirmaba que `dw4` era "un dword extra fuera del payload". Era
una suposición sobre la convención. `023-pm4-count` la mide y la corrige. **Se
conserva la versión anterior** (§16): la corrección está dentro de `022`, con la
marca `CORRECCION (ronda 023)`.

## RE-10 · Geometría de page table de Polaris12, cerrada numéricamente

```
TYPE    DERIVATION
STATE   PROVEN          (la cadena y los valores)
SOURCE  gfx8vmgeom (commit 2599c65) + 024-page-table-geometria-gfx8.md §2
LOCATION gmc_v8_0.c:1127    amdgpu_vm_adjust_size(adev, 64, 9, 1, 40)
                             <- vm_size=64 · fragment=9 · max_level=1 · max_bits=40.
                             Son las ENTRADAS de toda la cadena, y son un argumento
                             literal, no un valor derivado
          amdgpu_vm.c:2424   tmp = roundup_pow_of_two(max_pfn)      = 2^24
          amdgpu_vm.c:2427   tmp = DIV_ROUND_UP(fls64(tmp)-1, 9)-1 = 2   <- REASIGNA
          amdgpu_vm.c:2428   num_level = min_t(..., max_level, tmp) = 1
          amdgpu_vm.c:2429   switch (num_level)  case 1 -> root_level = PDB0
          amdgpu_vm.c:2454   block_size = amdgpu_vm_get_block_size(tmp)   <- con tmp=2
          amdgpu_vm.c:2463   dev_info: "vm size is %d GB, %d levels,
                             block size is %d-bit, fragment size is %d-bit"
PRODUCER 08-ARQUITECTURA/tools/gfx8vmgeom
UNIT    entradas de page table, bytes, bits
VERSION GFX8, cruzado 7.1.3 ↔ 7.2.8

  vm_size                       64 GB
  max_pfn                       16777216        (= vm_size << 18)
  num_level                     1               (min(max_level=1, 2))
  root_level                    AMDGPU_VM_PDB0
  block_size                    10
  fragment_size                 9
  PAGE_TABLE_BLOCK_SIZE escrito 1               (block_size - 9, MASK 0xf000000 SHIFT 0x18)
  PDB0                          16384 entradas  = 128 KiB
  PTB                           1024 entradas   = 8 KiB
  PTB cubre                     1024 páginas    = 4 MiB
  nº PTB para max_pfn           16384
  suma de tablas hoja           128 MiB
  GPUVA                         36 bits         ([14] root | [10] hoja | [12] offset)

CONTRAPRUEBA  contra la línea que el host imprimió en el boot:
              observada : vm size is 64 GB, 2 levels, block size is 10-bit,
                          fragment size is 9-bit
              derivada  : vm size is 64 GB, 2 levels, block size is 10-bit,
                          fragment size is 9-bit
              "2 levels" es num_level + 1 en el dev_info (amdgpu_vm.c:2463). Coincide.
CONFIDENCE alta
VERIFICADO POR  make test el 2026-10-01: 37 aserciones, 0 fallos, 12/12 controles
              negativos detectados, 0 muertos, cruce de versión PROVEN
ARBITRAJE DEFINITIVO, 2026-10-01 12:40  el kernel EN EJECUCIÓN lo imprimió hoy:
    $ journalctl -k -b --no-pager | grep "vm size is"
    oct 01 05:49:05 kalm kernel: amdgpu 0000:01:00.0: vm size is 64 GB, 2 levels,
                                        block size is 10-bit, fragment size is 9-bit
  Kernel 7.1.3-200.nobara.fc44, arrancado HOY. No es un log histórico de septiembre:
  es esta máquina booting hoy. Es el árbitro más fuerte disponible, y settles C-009
  en contra de las cifras 22/23/24
LO QUE ESTO HIZO POR ESTE REGISTRO  Dos hallazgos posteriores intentaron
  corregir esta misma cifra -- `024` con 13, y `030-page-walker` con 22 -- y los dos
  se equivocaron de Feed. El que acertó fue el que contrastó contra el host. La
  diferencia no fue el análisis: fue que la cadena se comprobó contra el hardware
```

La cadena que la sostiene, y que es donde está el valor:

```
amdgpu_vm_adjust_size(adev, 64, 9, 1, 40)          gmc_v8_0.c:1127
  max_size = 1 << (max_bits - 30) = 1 << 10 = 1024 GB
  phys_ram_gb = ceil(MemTotal) = 12                  /proc/meminfo: 12098912 kB
  vm_size = roundup_pow_of_two(clamp(12*3, 64, 1024)) = 64 GB     <-- el clamp decide
  max_pfn = 64 << 18 = 16777216
  tmp = roundup_pow_of_two(max_pfn) = 16777216
  tmp = DIV_ROUND_UP(fls64(tmp) - 1, 9) - 1 = 2
  num_level = min(max_level=1, tmp=2) = 1
  block_size = 9  si num_level > 1
             = get_block_size(tmp)  si num_level == 1   <-- pasa tmp, NO vm_size
```

**El error que este proyecto ya cometió dos veces, y que queda documentado para que no
se repita**: `get_block_size` recibe `tmp` (=2), no `vm_size` (=64).
`get_block_size(2) = 10`; `get_block_size(64) = 13`. La rama que produce 13 **no se
ejecuta**. Con `get_block_size(2)`, `bits = ilog2(2) + 18 = 19`, `2 <= 8` luego
`bits - 9 = 10`, y `10` es exactamente lo que el host imprimió.

`024` §2.3 dice `block_size = amdgpu_vm_get_block_size(vm_size)` y calcula
`ilog2(64)+18 = 24 → (24+3)/2 = 13`. Son las ramas opuestas de la misma función
(`vm_size <= 8` vs el `else`). `024` se equivocó de rama; `gfx8vmgeom`, escrito el mismo
día, acertó. La §7 de `021-frame` lo describe como "la ronda que quedó abierta".

## RE-11 · `num_level = 1` es un parámetro del driver, no una límite del silicio

```
TYPE    DERIVATION
STATE   PROVEN
SOURCE  024 §6
LOCATION gmc_v8_0.c:1127  max_level = 1 como argumento literal
CONFIDENCE alta
REFUTES  DRIVER-MISSION-STATE.md ("el modelo de VM es plano por necesidad")
```

Lo que **no** se toca: que GFX8 no exponga un motor de recorrido en el árbol de
registros (`gca/gfx_8_0_d.h` y `gfx_8_1_d.h`: 0 coincidencias de `mmVM_*`;
`gmc/gmc_8_2_d.h`: 61). Que no haya motor **y** que el nivel lo elija el software son
dos hechos distintos, y el documento de misión los mezclaba.

## RE-12 · `PAGE_TABLE_DEPTH` recibe dos valores en el mismo campo

```
TYPE    FACT
STATE   PROVEN (los valores) / NOT_DETERMINED (su significado)
SOURCE  024 §3
LOCATION gmc_v8_0.c:895   PAGE_TABLE_DEPTH = 0   (contexto 0, GART)
        gmc_v8_0.c:925   PAGE_TABLE_DEPTH = 1   (contextos 1-15)
        gmc_8_2_sh_mask.h  MASK 0x6  SHIFT 1  -> 2 bits, 3-4 valores, el driver usa 2
CONFIDENCE alta para los valores
CONFIDENCE baja para el significado: NINGUNA cabecera, comentario ni documento del árbol
        declara qué significan. La causa está nombrada: falta la spec PM4 de GFX8 (N3)
ADEMÁS  PAGE_TABLE_BLOCK_SIZE no se escribe para el contexto 0: queda en valor de reset
VALOR DE LA ASIMETRÍA  es el punto exacto donde el modelo plano del kernel y el de
        userspace divergen en el mismo ASIC. Localizada y sin explicar = frontera F3
```

## RE-13 · La ruta GART sí tiene completion observable

```
TYPE    DERIVATION
STATE   PROVEN
SOURCE  025-*.md §CUDA
LOCATION amdgpu_gart.c:492-506   mb() + flush_hdp + for_each vmhub -> flush_gpu_tlb(0)
        gmc_v8_0.c:661-666       WREG32(mmVM_INVALIDATE_REQUEST, 1 << vmid)
VERSION GFX8
CONFIDENCE alta — RE-02 no dice "no hay completion en el ASIC", dice "no la hay en el
        path de ring". 025 distingue los dos y acota bien
NO CONTRASTE RE-02: es otro path. El veredicto de 017/018 sigue válido para el ring.
```

Lo que se afirma: cuando `amdgpu_gart_invalidate_tlb()` **vuelve**, la escritura del
registro ya salió, porque `flush_hdp` y el retorno son síncronos con la función que
los emite. No hace falta hardware nuevo. Lo que **no** se afirma: que el invalidate de
hardware se haya completado. La sincronización es de CPU, no del ASIC.

## RE-14 · La ruta máxima de `amdgpu_vm_flush` en GFX8 es 63 dw, y es alcanzable

```
TYPE    MEASUREMENT
STATE   PROVEN
SOURCE  025-vm-flush-path-gfx8-63dw.md (tool: pm4dw --path)
VERSION GFX8 · corpus 7.2.8
CONFIDENCE alta

  ruta máxima GFX8 ring GFX = 63 dw  =  53 medidos + 10 ocultos tras el despacho
                                            indirecto
  reserva declarada            = 172
  infrarreserva                = NINGUNA

LO QUE RESUELVE, Y ES LA PARTE IMPORTANTE
  La cota superior de --struct (172 frente a 74 en la suma de handlers) no era la
  respuesta: era la suma de handlers que NUNCA COEXISTEN. pm4dw --path compone la
  secuencia ORDENADA, que es lo que realmente emite una submission.
  Y el conjunto máximo no es una cota teórica: es alcanzable. amdgpu_vm_flush fuerza
  cuatro flags a la vez cuando el VMID ha visto un reset, y las condiciones son campos
  distintos del job, sin exclusión mutua.

LO QUE DESCARTA  cualquier lectura de "172 = lo que se escribe"
LO QUE NO DESCARTA  que 63 dw sea la ruta máxima de un ENVÍO COMPLETO. emit_frame_size
  cubre también el IB, el context switch y los fences de usuario. Ver RE-15
OTRO HALLAZGO, DE DISEÑO
  emit_cleaner_shader es un predicado PERMANENTEMENTE FALSO en Polaris12: el término
  ring->funcs->emit_cleaner_shader es NULL. No es un if que pueda activarse. Eso
  elimina una rama entera del espacio de diseño del driver propio
```

## RE-15 · El frame completo de GFX8 son 121 dw, y la reserva son dos sumandos

```
TYPE    DERIVATION
STATE   PROVEN_DERIVED
SOURCE  026-frame-completo-gfx8-121dw.md
LOCATION amdgpu_ib.c:197-198   alloc_size = emit_frame_size + num_ibs * emit_ib_size
        amdgpu_ib.c:124-331    secuencia completa de amdgpu_ib_schedule
        gfx_v8_0.c:6900        emit_ib_size = 4
        amdgpu_ring.h:498      count_dw se decrementa en cada escritura

  frame GFX8 = 121 dw   (137 con chained IB)
  reserva    = 172      -> alcanza, con 51 dw de holgura
  más        = num_ibs * 4

LO QUE CORRIGE  los residuales +98/+57/+46 y la ruta de 63 dw se comparaban contra un
  número que nunca incluía los IBs. No hacía falta que los incluyera: la reserva está
  partida en dos sumandos y el análisis va por la vía correcta
POR QUÉ IMPORTABA  amdgpu_ring_alloc es lo que exige la reserva; si se queda corta, el
  buffer del ring se desborda. Eso es la consecuencia, no una especulación
CALIDAD DE LA FUENTE  los write_multiple se expandieron con el tamaño de struct del
  propio corpus, y la fuente de esos tamaños es vi_structs.h, que documenta los
  payloads de metadatos en DWORD exactos. Nadie la estaba usando
SEIS RAMAS DEL CAMINO DE ENVÍO NO EXISTEN EN GFX8
  Eso reduce el espacio de diseño del driver propio más que cualquier dato de registro
LIMITACIÓN, con dos causas nombradas  [NR-07c]
  emit_ib_size = 4 es correcto para metal desnudo, pero emit_ib llama a de_meta (21 dw)
  si amdgpu_sriov_vf y PREEMPT: el IB costaría 25. Con 51 dw de holgura se toleran ~2
  antes de desbordar. NO APLICA al objetivo. Se documenta porque el 4 se va a copiar
  tal cual
```

## RE-16 · El PTBA de GFX8 sale de una sola operación, sin código condicional

```
TYPE    DERIVATION
STATE   PROVEN
SOURCE  027-ptba-produccion-gfx8.md
COMPLEMENTS  024 (geometría), 026-pte (PTE)
LOCATION vm->root.bo -> amdgpu_gmc_pd_addr(bo)
          asic_type(17) >= CHIP_VEGA10(19)  ->  FALSO
        -> pd_addr = amdgpu_bo_gpu_offset(bo)
VERSION GFX8
CONFIDENCE alta
CONSECUENCIA  cierra el arco que AGENTS.md daba por cerrado ("PTBA software production
  cerrada") pero con la aritmética escrita de extremo a extremo: de la ioctl al
  registro, sin ramas
COMPLEMENTA    RE-10 (la geometría sostiene el >> 12) y RE-17 (el PTE)
```

## RE-17 · El PTE de GFX8: 40 bits de dirección física por tres vías, flags sólo por comentario

```
TYPE    DERIVATION
STATE   PROVEN (dirección) / PARCIAL (flags)
SOURCE  026-pte-encoding-gfx8.md
VERSION GFX8
CONFIDENCE alta para el layout; los flags por comentario son NOT_PRIMARY
CONSUMIDOR  el page walker
VÍNCULO CON RE-10  la cadena queda coherente: get_block_size entrega block_size=10, el
  PTE direcciona 40 bits, y el PAGE_TABLE_BLOCK_SIZE escrito es 1
```

## RE-18 · El fence SÍ tiene completion, y cambia en cada generación

```
TYPE    DERIVATION
STATE   PROVEN
SOURCE  028-fence-completion-orden-d.md (Frontera D)
CONTINUES  AGENTS.md:617-627  (PTBA → INVALIDATE → WAIT → PFP_SYNC_ME → next IB)
VERSION GFX8 (y contraste GFX9+)
CONFIDENCE alta — las tres formas se pueden fechar con el fuente

  GFX       EVENT_WRITE_EOP x2   (uno con seq-1, otro con seq y EOP_EXEC)
  COMPUTE   RELEASE_MEM     x1

LO QUE AFIRMA  el fence es el ÚNICO punto del path de submit donde el hardware
  confirma que el trabajo anterior terminó
POR QUÉ ES DISTINTO DE RE-02  RE-02 dice que el path de RING no puede observar
  completion del INVALIDATE. Eso sigue siendo cierto y no lo toca: el fence es otro
  punto, y confirma el fin de un trabajo, no el fin de una invalidación
CIERRA PARCIALMENTE  F1. La pregunta "¿cómo sé que lo anterior terminó?" tiene ahora
  respuesta para el trabajo; la pregunta "¿el invalidate se habrá aplicado?" sigue
  abierta. No son la misma
```

## RE-19 · `RELEASE_MEM` en GFX8 no tiene campo de número, y es estructural

```
TYPE    DERIVATION
STATE   PROVEN
SOURCE  029-release-mem-y-eop-exec-muerto.md
CONTINUES  028 §1.1bis
VERSION GFX8 vs GFX9+
CONFIDENCE alta

  GFX8   PACKET3(RELEASE_MEM, 5)  ->  6 dwords de payload, SIN campo de número
  GFX9   PACKET3(RELEASE_MEM, 6)  ->  7 dwords de payload, CON un dw extra

LO QUE RESUELVE  028 dejó abierta la pregunta de por qué RELEASE_MEM no necesita el
  seq − 1 que sí exigían GFX7 y GFX8. La respuesta es estructural, no paramétrica:
  en GFX8 el paquete no tiene dónde llevar el número
CIERRA  una de las dos ramas del "EOP_EXEC muerto" que 029 titula
LO QUE SIGUE  la otra rama del título de 029 queda por ver; ese finding aún no está
  commiteado y no se ha leído entero
```

## RE-20 · La corrupción de `29⁄9⁄26.md:169`

```
TYPE    CONTRADICTION
NOTA    (resuelta)
STATE   REFUTED
SOURCE  017 §4
CLAIM_A 29⁄9⁄26.md:166-171  "[CLOSED] WAIT_REG_MEM espera REQUEST == 0"
CONFLICT 017 §3 — la codificación es FUNCTION=0 (always), ref=0, mask=0
ALCANCE el documento confundió ref=0 con una comparación contra cero: con
        FUNCTION=always el valor de ref no es el operando. Sólo el path de ring de GFX8
LO QUE SOBREVIVE  del documento original: mecanismo de invalidación PROVEN, request por
        VMID PROVEN, y "no es prueba de completion explícito" PROVEN
NOTA DE ALCANCE  RE-18 (el fence SÍ tiene completion, RE-18) NO contradice RE-02: el
        fence confirma el fin de un trabajo, no el de una invalidación. Son dos
        preguntas, y la separación es exactamente lo que 028 aporta
ESTADO DEL DOCUMENTO  29⁄9⁄26.md NO lleva marca de enmienda. Mtime 2026-09-29 23:12,
        anterior a 017 (2026-10-01 09:52). La enmienda vive sólo en 017 §4 y aquí.
        -> Candidato a nota de precedencia. Ver CONTRADICTIONS.md C-002
```

## RE-21bis · El writeback buffer: 5 slots por ring y uno se fuga

```
TYPE    DERIVATION
STATE   PROVEN (la fuga, por lectura del par getter/free de cada offset)
SOURCE  030-writeback-buffer-*.md §CUDA   [POST-SCAN: sólo se leyó esta sección]
LOCATION ade v->wb = bitmap de 1024 slots; cada ring pide 5
          rptr_offs        wb_get :267   wb_free :404   liberado
          wptr_offs        wb_get :273   wb_free :405   liberado
          fence_offs       wb_get :279   wb_free :408   liberado
          cond_exe_offs    wb_get :291   wb_free :407   liberado
          trail_fence_offs wb_get :285   wb_free ------   NO liberado
VERSION GFX8 (el análisis es de amdgpu_ring.c, común a toda la familia)
CONFIDENCE alta para la fuga: es un getter sin free correspondiente
LO QUE ES  una fuga en el DRIVER DE REFERENCIA. Menor, y con modo de fallo duro
LO QUE NO ES  un defecto del proyecto. Este repo no modifica amdgpu_ring.c
CONTINUES  029 §2.4, "los dos slots inertes"
LIMITE DE LECTURA  sólo se leyó el §CUDA de 030. El resto del finding no se ha
  verificado y no se registra aquí. Es el finding más reciente del árbol y apareció
  DESPUÉS de terminar el grueso de esta documentación
CONSECUENCIA PARA EL DRIVER PROPIO  el número de slots del writeback buffer es una
  decisión de diseño, y ya se sabe que el de referencia ni siquiera los libera todos
```

## RE-22 · Censo de productores de flags de PTE en GFX8, con estado por bit

```
TYPE    MEASUREMENT
STATE   PROVEN  (qué escribe el driver)
STATE_2 NOT_DETERMINED  (qué significa el hardware) -- lo dice el propio binario
SOURCE  08-ARQUITECTURA/tools/pteflags   [TOOLS-STATUS TL-09]
METHOD  preprocesa la TU real de gmc_v8_0.c con los -I del build y rastrea la cadena
VERSION GFX8 · corpus 7.1.3, contrastado con 9.0 / 10.0 / 11.0 / 12.0
CONFIDENCE alta. 19 aserciones, 0 fallos, 5/5 controles negativos, rc=0

  bit  AMDGPU_PTE_*        ESTADO GFX8         QUIEN, en GFX8
  ---  ------------------  ----------------  ------------------------------------------
   0   VALID               WRITTEN            amdgpu_ttm_tt_pte_flags()
   1   SYSTEM              WRITTEN            ídem
   2   SNOOPED             WRITTEN            ídem + gart_pte_flags
   3   (reservado)         --                 el hardware lo trate o no: N4
   4   EXECUTABLE          WRITTEN            gmc_v8_0_get_vm_pte(), según vm_flags
   5   READABLE            WRITTEN            amdgpu_ttm_tt_pte_flags(); se borra si
                                              el BO es de solo lectura  (amdgpu_vm.c:1378)
   6   WRITEABLE           WRITTEN            ídem; :1380
  11:7 FRAG                WRITTEN            amdgpu_vm_pt.c:900, desde `frag`
  51   PRT                 CLEARED_NOT_SET    NADIE lo pone; gmc_v8_0_get_vm_pte lo
                                              BORRA explícitamente
  54   PDE_PTE             WRITTEN            amdgpu_vm_pt.c:689 (AMDGPU_PDE_PTE_FLAG)
  55   LOG                 OTHER_GEN          sólo gmc_v10_0.c:513 y v11_0.c:504
  56   TF                  OTHER_GEN          sólo v9_0 / v10_0 / v11_0
  58   NOALLOC             OTHER_GEN          sólo v10_0 / v11_0
  59   BFS                 OTHER_GEN          sólo amdgpu_gmc.c:1169, dentro de init_pdb0
  63   IS_PTE              OTHER_GEN          sólo gmc_v12_0.c

LO QUE HACE QUE EL CENSO SIGNIFIQUE ALGO, y no sea una lista
  el contraste MTYPE:
    MTYPE_UC en la TU de gmc_v8_0.c   NO
    MTYPE_UC en la TU de gmc_v9_0.c   SI
    gmc_v8_0_get_vm_pte existe        SI
  No es que el codigo GFX8 decida no escribir MTYPE: es que el simbolo NO EXISTE en su
  unidad de traduccion, luego no podria escribirlo aunque quisiera. No es una omision
  del driver. Sin ese contraste, "MTYPE no se escribe en GFX8" seria NOT_FOUND sin
  informacion: el nombre no apareceria por la misma razon que no aparecen MTYPE_UC
  Y ese es el valor del metodo, no del dato
CONFIRMA Y AFORZA  RE-05. PRT no es un tipo de entrada en GFX8, y ahora la afirmacion
  no es "el driver lo borra" sino "nadie lo pone y el unico que lo menciona lo borra"
CIERRA PARCIALMENTE  la frontera A de AGENTS.md ("PTE/PDE → bits → flags"). Los BITS
  estan completos y con productor; la SEMANTICA de cada uno sigue NOT_DETERMINED
LO QUE LA HERRAMIENTA PROHIBE AFIRMAR, en su propia salida
  "Que el hardware de GFX8 interprete alguno de estos bits. Este documento afirma QUE
   ESCRIBE EL DRIVER, no que signifique. La semantica de hardware de cada bit sigue
   NOT_DETERMINED"
  Es la tercera herramienta del proyecto que se lo diceexplicitamente a si misma
  (017 lo hizo para el WAIT_REG_MEM; pm4_count_census para la convencion de PACKET3)
LIMITE  validado a las 12:0x del 2026-10-01 sobre un arbol en construccion: sus
  ficheros se modificaron a las 11:55, con mi ronda en curso. Reejecutar si cambia
```

## RE-22bis · `rptr`/`wptr` viven en tres dominios de memoria, sin `mb()` entre ellos

```
TYPE    DERIVATION
STATE   PROVEN  (la topología y el recorrido)
SOURCE  031-rptr-wptr-*.md §CUDA   [POST-SCAN: sólo se leyó esta sección]
CONTINUES  030 (writeback buffer), 028 (fence)
LOCATION gfx_v8_0_ring_set_wptr_compute  son DOS escrituras a DOS dominios
VERSION GFX8
CONFIDENCE alta para la topología

  1. ring->ring          BO en GTT          el CPU escribe con ring->ring[wptr++]
  2. wptr_cpu_addr       BO en GTT          *addr = wptr        (memoria normal)
  3. doorbell.cpu_addr   BO en DOORBELL     writel()            (MMIO de dispositivo)

LO QUE AFIRMA  el hardware recibe el doorbell, y para interpretarlo necesita ver el
  valor de wptr, que está en OTRA página, en otra BO, en otro dominio. Y la secuencia
  de commit los recorre sin un único mb() explícito en el path del ring
POR QUÉ IMPORTA PARA EL DRIVER PROPIO  es el punto donde el modelo de coherencia del
  driver de referencia se vuelve una decisión de diseño, no una herencia. Un driver
  propio que ponga el doorbell desde una CPU distinta necesita un mecanismo de orden
  que el de referencia no necesita porque sus tres escrituras salen por el mismo
  camino
LO QUE NO SE AFIRMA, y no está resuelto
  que el hardware ordene o no. Este finding DESCRIBE el problema; no dice si hay un
  riesgo real. Ver N1/N2
LIMITE DE LECTURA  sólo el §CUDA. El resto de 031 no se ha leído y no se registra
COMPATIBILIDAD  no contradice 025 (ruta GART) ni RE-02: son otra ruta y otra pregunta
```

## RE-23 · Census de `write_multiple`: los cuatro números, por herramienta

```
TYPE    MEASUREMENT
STATE   PROVEN   (los tamaños)   ·   CORROBORATED (las cifras de 021-frame)
SOURCE  027-write-multiple-resuelto.md + pm4dw --struct-size / --wm-sites
VERSION GFX8 · corpus 7.2.8 (vi_structs.h)
CONFIDENCE alta, y verificada a mano además de por la herramienta
VERIFICADO    pm4dw --struct-size  (compilado a /tmp, no toca el árbol)

  struct                       miembros   bytes   cnt   write_mult   emisión total
  vi_ce_ib_state                      4      16      6            4   4 + 4  =   8
  vi_ce_ib_state_chained_ib         10      40     12           10   4 + 10 =  14
  vi_de_ib_state                    17      68     19           17   4 + 17 =  21
  vi_de_ib_state_chained_ib         27     108     29           27   4 + 27 =  31

LA ARITMÉTICA, Y POR QUÉ 4 + N
  gfx_v8_0_ring_emit_ce_meta escribe, en orden:
    1 dword   PACKET3(PACKET3_WRITE_DATA, cnt_ce)     cabecera
    1 dword   ENGINE_SEL | DST_SEL | WR_CONFIRM | CACHE_POLICY
    2 dwords  addr bajo + addr alto
    N dwords  amdgpu_ring_write_multiple(ring, &payload, cnt_ce - 2)
  con cnt_ce = (sizeof(regular) >> 2) + 4 - 2
  -> 4 de cabecera + (sizeof>>2), y sizeof(regular)>>2 = 4 / 17 respectivamente

CORROBORATION, Y ES EL PUNTO
  021-frame-defense Rolleó A MANO el 2026-10-01 a las 10:28:
      CE_META  =  8 dw activo / 14 declarado
      DE_META  = 21 dw activo / 31 declarado
  La herramienta, seis horas después, desde el mismo corpus:
      CE_META  =  8 dw activo / 14 declarado
      DE_META  = 21 dw activo / 31 declarado
  CUATRO cifras, dos métodos independientes, mismo resultado. Eso es CORROBORATED.
  Si hubieran coincidido por el mismo código, sería duplicación; aquí uno leyó a mano y
  la otra calculó desde vi_structs.h
LO QUE RESUELTA  NR-07. Antes era una cuenta a mano con una fuente que nadie estaba
  usando; ahora el número se mueve solo si cambia la struct
LO QUE NO RESUELVE  el marco de la reserva, que es RE-15 (dos sumandos) y RE-14 (63 dw
  alcanzable). Esta fila es el tamaño de la copia, no dónde va a parar
SITIO DE LAS LLAMADAS, literal, por --wm-sites
  gfx_v8_0_ring_emit_ce_meta   ring, (void *)&ce_payload, cnt_ce - 2
  gfx_v8_0_ring_emit_de_meta   ring, (void *)&de_payload, cnt_de - 2
  Y la propia salida avisa: "each is a multi-dword copy whose size is NOT in this count".
  O sea que --wm-sites DICE que su propio conteo no incluye el write_multiple, que es
  justo lo que --struct-size viene a sumar
LIMITE  validado a las 12:1x del 2026-10-01 con un binario COMPIADO POR MÍ en /tmp desde
  el fuente del árbol, no con el binario del árbol (que no está construido para --struct-size
  en el momento de la medición). La distinción importa: lo medido es el fuente, no un
  artefacto instalado
```

## RE-24 · `PROTECTIONS` es un entero opaco en el camino GPUVM, y eso RENOMBRA el bloqueo de F2b

```
TYPE    DERIVATION
ALSO    NEGATIVE_RESULT
STATE   PROVEN  (el layout del registro y dónde está el decode)
STATE_2 PTE → PROTECTIONS: NOT_IN_CORPUS, con DOS hipótesis sin separador
SOURCE  033-protections-opaco-en-el-camino-gpuvm.md
VERSION GFX8 · con contraste GFX6 y GFX7
CONFIDENCE alta para el layout; NINGUNA para la correspondencia semántica

LO QUE ES PROVEN
  - layout de PROTECTION_FAULT_STATUS: 5 campos, uno de ellos PROTECTIONS de 8 bits
  - el decode estructurado existe en EXACTAMENTE UN punto de todo el driver, y está
    detrás de un gate de KFD
  - VMID 0-7 = DRM · VMID 8-15 = KFD en esta GPU
  - GFX6 y GFX7 tampoco lo descompongan. NEGATIVE_RESULT PROVEN_ABSENT, 2 ficheros,
    2 generaciones
  - los bits 6-7 no los decodifica nadie. PROVEN_ABSENT
  - NO hay enumeración ni comentario del campo en gmc_8_2_sh_mask.h ni en ninguna otra
    cabecera aplicable a GFX8

LA CORRESPONDENCIA QUE NO EXISTE, y las dos hipótesis sin separador
  el PTE de GFX8 codifica permisos en 3 bits: EXECUTABLE(4) READABLE(5) WRITEABLE(6),
    más VALID(0). Fuente ÚNICA: el comentario de gmc_v8_0.c:691-702, SIN corroboración
    en cabeceras ASIC
  el hardware reporta 8 bits
  A: PROTECTIONS[3:5] espeja R/W/X y [2:0] son subtipos de fallo de validez
  B: [7:0] es un Fault-ID opaco y el mapeo desde el PTE no es directo
  un indicio que inclina hacia A sin ser evidencia:
    VM_L2_CNTL__PDE_FAULT_CLASSIFICATION (MASK 0x40000) existe de gmc_6_0 a gmc_8_2, y
    sugiere que el hardware SÍ distingue tipos de fallo a nivel PDE. Pero ese campo
    tampoco lo descompone el driver

POR QUÉ ESTA FILA IMPORTA MÁS DE LO QUE PARECE
  F2b estaba bloqueada por "falta la especificación del PTE". 033 RENOMBRA el bloqueo:
  no es sólo que falte la spec, es que **el observador de referencia no produjo el dato
  en el camino que nos interesa**. Un driver propio que quiera diagnosticar faults de
  traducción tendrá que INVENTAR su propia decodificación de un campo de 8 bits.
  Y por NO_HISTORICAL_INHERITANCE e IMPLEMENTATION_GATE: no se hereda el decode de KFD
  como semántica de hardware. Es software de KFD sobre un campo opaco
LO QUE ESTO DEGRADA, y hay que decirlo
  la confianza de RE-22 (el censo de flags). El censo dice QUÉ ESCRIBE EL DRIVER y eso
  no cambia. Lo que se degrada es la base documental del LAYOUT del PTE: una sola
  fuente, un comentario, sin corroboración ASIC. Ningún finding anterior lo decía
LO QUE 033 DICE EXPLÍCITAMENTE
  "No cierra F2b. F2b sigue BLOCKED_BY_CORPUS + BLOCKED_BY_AUTHORIZATION. Lo que hace es
   RENOMBRAR el bloqueo". Se registra así, no como un cierre
```

## RE-25 · El fence se lee con una lectura de CPU normal, y funciona por el `pin` del BO

```
TYPE    DERIVATION
STATE   PROVEN
SOURCE  032-fence-lectura-coherente-por-pin.md
COMPLEMENTS  031 §4, que estaba NOT_DETERMINED SIN CAUSA NOMBRADA — y eso ya no está
LOCATION amdgpu_fence_read():  le32_to_cpu(*drv->cpu_addr)
          sin mb(), sin readl(), sin volatile
VERSION GFX8
CONFIDENCE alta. Cadena bo_create_kernel → bo_create_reserved → bo_pin → bo_kmap cerrada

LO QUE AFIRMA  el completion del fence que 028 estableció como el mecanismo real NO USA
  NINGUNA BARRERA en el camino de lectura. El CPU hace literalmente:
      while ((int32_t)(wait_seq - amdgpu_fence_read(ring)) > 0 && timeout > 0) {
              udelay(2); timeout -= 2; }
  La garantía NO está en el código del fence: está en que la página que se lee es
  COHERENTE POR CONSTRUCCIÓN, y eso lo resuelve el `pin` del BO más abajo en la cadena
LO QUE CIERRA  031 §4. El hallazgo 031 se registró aquí sólo desde su §CUDA, y su §4
  figuraba como NOT_DETERMINED sin causa. Ahora tiene causa Y respuesta
POR QUÉ IMPORTA PARA EL DRIVER PROPIO  es el punto donde la coherencia deja de ser una
  herencia del driver de referencia y pasa a ser una decisión. Si el page table del
  driver propio vive en una BO no pineada, la lectura del fence no vale. Es una
  restricción de diseño que se habría descobertado tarde
LIMITE  los dos caminos de lectura (polling e interrupción) se transcribieron, pero sólo
  se registró la conclusión de esta ficha. La transcripción no se ha verificado aquí
```

## RE-26 · La L2 puede byte-swappear PDE y PTE por separado, y el driver no lo programa

```
TYPE    FACT
STATE   PROVEN      (que los campos existen y que el driver no los programa)
SOURCE  033 §7 — hallazgo colateral, explícitamente "no está en ningún hallazgo del
        proyecto" hasta ahora
LOCATION VM_L2_CNTL__L2_CACHE_PDE_ENDIAN_SWAP_MODE   MASK 0x30
        VM_L2_CNTL__L2_CACHE_PTE_ENDIAN_SWAP_MODE   MASK 0x0c
        presentes de gmc_6_0 a gmc_8_2, idénticos
VERSION GFX6 → GFX8
CONFIDENCE alta
LO QUE AFIRMA  esta GPU puede leer la caché L2 de PDE y de PTE con endianess DISTINTO, y
  el driver de referencia lo deja en el valor de reset: no los programa en gfxhub ni en
  gmc_v8_0 init
RELEVANCIA  placement de page tables en VRAM. Un driver propio que ponga la tabla en
  VRAM en vez de en GTT tiene que decidir explícitamente el endianess, porque el valor de
  reset puede no ser el correcto para su caso
POR QUÉ SE REGISTRA  porque es de la clase de hallazgo que este repo ha pagado: un
  campo que existe, que el driver de referencia ignora, y que nadie había buscado. Es
  `NOT_IN_ANY_DOC` hasta ahora
LIMITE  no se ha determinado cuál es el valor de reset ni cuál sería el correcto. Eso
  es `NOT_DETERMINED`
```

## RE-28 · Antes de GMC v9 no hay huge pages: el driver se niega a usar un nivel no-hoja

```
TYPE    FACT
STATE   PROVEN
SOURCE  030-page-walker-gfx8-2-niveles.md §CUDA  -- y SOBREVIVE al resto de ese finding,
        que queda refutado en C-009. Se separa porque es independiente
LOCATION rx550-upstream-7.2.8/.../amdgpu_vm_pt.c:825-832   (7.1.3: línea 840)
          } else if (adev->asic_type < CHIP_VEGA10 &&
                     (flags & AMDGPU_PTE_VALID)) {
                  /* No huge page support before GMC v9 */
                  if (cursor.level != AMDGPU_VM_PTB) {
                          if (!amdgpu_vm_pt_descendant(adev, &cursor))
                                  return -ENOENT;
                          continue;
                  }
          }
VERSION GFX8 (asic_type = CHIP_POLARIS12 = 17 < CHIP_VEGA10 = 19)
CONFIDENCE alta. La cita es correcta para el corpus que el finding declara
LO QUE AFIRMA  el predicado es literal: antes de GMC v9, una entrada válida en un nivel
  que NO sea hoja provoca continue o -ENOENT. No hay descriptores de bloque en
  operación normal
CONSECUENCIA, y es la que importa
  PAGE_TABLE_BLOCK_SIZE existe en el registro, pero el driver NO lo usa como tamaño de
  bloque. Eso RECORTA el espacio de diseño del driver propio: no puede implementar
  huge pages copiando el driver de referencia, porque el driver de referencia
  deliberadamente no las tiene
LO QUE ES Y LO QUE NO ES  el walk de GFX8 es de 2 niveles (num_level=1 se imprime como
  num_level+1=2): PDB + PTB. Eso es PROVEN y coherente con RE-10
LIMITE  el resto de 030-page-walker no sobrevive: su block_size=22 y su
  root_level=PDB2 están refutados en C-009
```

## RE-27 · El driver NO escribe los registros de reloj: el firmware SMU los aplica

```
TYPE    DERIVATION
STATE   PROVEN
SOURCE  040-smu-canal-mensajes-gfx8.md   [POST-SCAN: sólo el §CUDA]
STATE_2 el firmware SMU en sí: NOT_IN_CORPUS. Es firmware, no fuente
TERRITORIO  VIRGEN. 040 lo dice y es un dato que importa: antes de este finding,
  SMU/DPM/clocks/power/thermal tenía 0 findings y 0 herramientas en todo el proyecto.
  findings/ cubría PM4, PTE/PDE, VM flush y fences. Y el propio 040 verificó que su
  scope no solapa con pm4dw, pteflags, findings ni docs
LO QUE AFIRMA  el driver calcula un PAYLOAD de nivel de rendimiento, lo serializa, lo sube
  a la SRAM del SMC, y es el FIRMWARE DEL SMU quien aplica el cambio de frecuencia
CONSECUENCIA PARA EL DRIVER PROPIO, y es la de la línea H entera
  "cambiar un reloj" no es escribir un registro. Es construir un mensaje, serializarlo
  con el protocolo del SMC, y escribirlo en la SRAM correcta. El reloj no es un
  registro: es un mensaje, y el destinatario es firmware
POR QUÉ SE REGISTRA AUNQUE SEÁ SÓLO EL §CUDA
  porque abre una línea de investigación que el árbol documentaba como cerrada, y
  `AGENTS.md` §"H · PERFORMANCE CONTROL" decía explícitamente "investigar únicamente
  cuando las dependencias del core estén suficientemente cerradas". Esta fila es la
  prueba de que se cumpliría esa condición
LIMITE DE LECTURA  sólo el §CUDA y la cabecera. El resto de 040 no se ha leído
COMPLEMENTA  041: la curva A-T, con la banda de histéresis [t_l, t_h] por la que el
  firmware decide, en vez de frecuencias. Es aritmética cerrada, declarada así
```

## RE-29 · La especificación PM4 de GFX8 NO EXISTE, y eso es un resultado, no una búsqueda pendiente

```
TYPE    NEGATIVE_RESULT
STATE   PROVEN con la causa nombrada
SOURCE  033-pm4-spec-gfx8-no-existe-y-el-encuadre.md  (RESUELVES el BLOCKED de
        022 / 023 / 029)
CLASIFICACIÓN DE LA FUENTE  PRIMARY_DOCUMENTATION

  Documento   Reference Guide — Graphics Core Next Architecture, Generation 3
  Revision    1.0, March 2015  (la vigente en docs.amd.com es 1.1 de 2016-08-01, doc 70645)
  Paginas     637
  QUE CONTIENE  CERO apariciones de: PACKET3 · PKT3 · RELEASE_MEM · COND_EXEC ·
               VM_INVALIDATE · INT_SEL · WRITE_AT · GRBM · mmCP
  Metodo      CONTADO, no supuesto. Y ttm/ ausente del corpus, confirmado otra vez

LO QUE CAMBIA, y es lo importante
  El bloqueo que arrastraban 022, 023 y 029 deja de ser "no hemos encontrado la fuente"
  y pasa a ser NEGATIVE_RESULT con causa identificada: **AMD nunca publicó la
  especificación del framing PM4 para GCN3**
  Esto no es una decepción, es el dato que hace el resto posible: mientras la fuente se
  buscaba, el proyecto no podía saber si su `NOT_DETERMINED` era por falta de lectura o
  por inexistencia del documento. Ahora sabe que es por inexistencia
AFECTA DIRECTAMENTE A TRES FRONTERAS de docs/, que estaban bloqueadas por "falta la spec"
  F2b  semántica de cada bit de PTE
  F3   significado de PAGE_TABLE_DEPTH 0 vs 1
  N1   qué garantiza el intervalo 0x20 de un WAIT_REG_MEM sin predicado
  Las tres dejan de ser BLOCKED_BY_CORPUS-pendiente-de-búsqueda y pasan a
  BLOCKED_BY_NEGATIVE_RESULT: la evidencia NO está en ningún documento, hay que
  MEDIRLA. Es una categoría de bloqueo distinta, y se registra como tal
LO QUE QUEDA ABIERTO, y el propio finding lo dice en una línea
  "El framing PM4 de GFX8 está cerrado y medido. El payload de cada paquete —lo que
   COND_EXEC, RELEASE_MEM y VM_INVALIDATE hacen realmente— sigue abierto, y ya no por
   falta de búsqueda: no hay documento, y habrá que medirlo"
  NOT_DETERMINED explícitos: campos de COND_EXEC · el dword extra de RELEASE_MEM en GFX9 ·
  VM_INVALIDATE_RESPONSE e INT_SEL=2
```

## RE-30 · El referente exacto del `−1` queda cerrado: es el total, no los datos

```
TYPE    DERIVATION
STATE   PROVEN_DERIVED
SOURCE  033-pm4-spec §3
CIERRA  una ambigüedad que RE-08 dejaba abierta: de QUÉ se resta el uno
CONTRAPUEBA  freedreno NO la resuelve, porque su parámetro `cnt` no está documentado
        respecto a esa distinción y su type3_pkt_size() devuelve cnt. Es
        SECONDARY_CORROBORATION de la FORMA, no de la interpretación

LO QUE SE CIERRA, con tres casos que se leen enteros
  amdgpu_ring_write(ring, PACKET3(PACKET3_WAIT_REG_MEM, 5));   <- F = 5
  ... 6 amdgpu_ring_write más, uno por dword de dato
  Los TRES sitios de GFX8 usan lo mismo: :6047 (flush de HDP), :6180 (pipeline sync),
  :6199 (espera de invalidate). Todos con PACKET3(WAIT_REG_MEM, 5) y exactamente 6 datos

  LA FÓRMULA:   F = datos − 1        paquete = F + 2 dwords
  ES DECIR:     n se cuenta sobre el TOTAL, no sobre los datos
  Por eso n = payload − 1 en 68/68 (RE-08): el total es 1 + payload

LO QUE AÑADE
  · 0x3FFF reservado para NOP unitario: PROVEN_DERIVED, por el tope más el caso base
  · las cabeceras TYPE0/2/3/4/7 y sus máscaras: SECONDARY_CORROBORATION, no primaria
  · TYPE4 y TYPE7 llevan bit de paridad impar: SECONDARY_CORROBORATION
LIMITE  la fuente es una implementación de terceros para el framing, no un documento de
  AMD. La fórmula queda PROVEN_DERIVED contra el corpus de amdgpu; el resto es
  SECUNDARIA y está marcado como tal
```

## RE-31 · Una aserción de freedreno queda REFUTADA con un caso vivo

```
TYPE    NEGATIVE_RESULT
ALSO    DERIVATION
STATE   REFUTED
SOURCE  033-pm4-spec §4
CLAIM_A  freedreno: pkt_is_type3 exige bit 15 = 0, es decir opcode < 0x80. Predicción
        falsable: si es cierta, NINGÚN opcode PACKET3 de GFX8 puede ser >= 0x80
MEDICIÓN 74 opcodes PACKET3 en GFX8, 74 valores únicos, rango 0x10 .. 0x8B
        opcodes >= 0x80: 12
        La predicción se cumple para 62/74 y FALLA para 12

EL FILTRADO QUE HACE EL HALLAZGO VALER, y que es lo importante
  Que un opcode esté DEFINIDO no es que se EMITA. Si los 12 fueran código muerto, la
  contradicción sería vacua:
    LOAD_CONST_RAM 0 · WRITE_CONST_RAM 0 · WRITE_CONST_RAM_OFFSET 0 · DUMP_CONST_RAM 0
    INCREMENT_CE_COUNTER 0 · INCREMENT_DE_COUNTER 0 · WAIT_ON_CE_COUNTER 0
    WAIT_ON_DE_COUNTER 0 · WAIT_ON_DE_COUNTER_DIFF 0 · SET_CE_DE_COUNTERS 0
    WAIT_ON_AVAIL_BUFFER 0 · SWITCH_BUFFER 13
  Once con CERO usos en todo el árbol amdgpu. UNO con 13 usos: SWITCH_BUFFER (0x8B), vivo
  en GFX8
LO QUE APRENDE ESTE REPO, por segunda vez en un día
  Un barrido sin distinguir "opcode" de "offset de registro" produjo 12 falsos positivos
  que CASI INVALIDABAN la predicción. Los `*_START` / `*_END` de los `SET_*_REG` son
  offsets, no opcodes. Es el mismo error de `019` con `INCR` y `NUM_REGS` que en su día
  lo dejó en `NOT_FOUND` durante ocho horas
  La diferencia: aquí se detectó ANTES de concluir, y el hallazgo se apoyó en el
  filtro en vez de con la suposición
CLASIF    REFUTED. Con un contraejemplo vivo, que es la forma fuerte
```

## RE-32 · El ASIC usa `sdma_v3_0`, y `sdma_v3_1_ip_block` es un alias sin fichero propio

```
TYPE    FACT
STATE   PROVEN   (la cadena de bloques)  ·  OBSERVED (el dev_info del host)
SOURCE  C-011, verificado directamente contra el corpus
LOCATION vi.c:2105-2113            case CHIP_POLARIS10/11/12, CHIP_VEGAM:
                                       amdgpu_device_ip_block_add(adev, &sdma_v3_1_ip_block);
        sdma_v3_0.c:1693-1700      sdma_v3_1_ip_block { .major=3 .minor=1 .rev=0
                                                      .funcs = &sdma_v3_0_ip_funcs }
        sdma_v3_0.c:1112           amdgpu_sdma_set_vm_pte_scheds(adev, &sdma_v3_0_vm_pte_funcs)
        sdma_v3_0.c               .set_pte_pde = sdma_v3_0_vm_set_pte_pde
        sdma_v3_0.c               último dword: count   (NO count - 1)
VERSION GFX8 / Polaris12 · kernel 7.1.3-fc44
CONFIDENCE alta. Es una struct literal, no una inferencia

LO QUE AFIRMA
  1. Este ASIC despacha sus PTE con `sdma_v3_0_vm_set_pte_pde`, que escribe `count`
  2. `sdma_v3_1_ip_block` NO tiene fichero propio. No existe `sdma_v3_1.c` en 7.1.3 ni en
     7.2.8. Es un alias declarado dentro de sdma_v3_0.c
  3. El SDMA0_HWIP de la máquina es 3.1.0

EL DEV_INFO DEL HOST, DECODIFICADO
  el formato es `"detected ip block number %d <%s_v%d_%d_%d> (%s)\n"` (amdgpu_ip.c:241-245)
  oct 01 05:49:05 amdgpu 0000:01:00.0: detected ip block number 4 <sdma_v3_1_0> (sdma_v3_0)
                                                n=4  tipo  3 1 0   funcs->name
  `SDMA0_HWIP = 3.1.0`, y las funciones son las de v3_0

POR QUÉ ESTE DATO ES MÁS VALIOSO QUE EL HECHO
  Los dos emisores existen y se diferencian en UN dword:
      sdma_v4_0.c:1658   count - 1
      sdma_v3_0.c:996    count
  Conocer cuál corre en esta máquina es la diferencia entre escribir un PTE de más o de
  menos. Ninguna lectura del corpus lo establece; sólo lo establece la máquina
POR QUÉ ES TRAPECOSO PARA UN BARRIDO, y por eso conviene registrarlo
  un barrido por NOMBRE DE FICHERO encuentra sdma_v3_0.c y no ve nada raro
  un barrido por BLOQUE DE IP encuentra sdma_v3_1 y concluye que hay un emisor nuevo
  Los dos barridos están bien ejecutados y dan respuestas OPUESTAS. El identificador
  ausente hay que seguirlo hasta su declaración antes de tratarlo como entidad nueva
LO QUE ESTO CORRIGE  RE-04 / `035` / `036`. Ver C-011
LIMITE  el corpus 7.1.3 es el del repo; el host corre 7.1.3-200.nobara.fc44, que es un
  build de Fedora sobre ese upstream. Que el bloque activo sea v3_1 lo dice el propio
  host, y el árbol 7.1.3 tiene ese bloque, así que el build de Fedora no añade una ruta
  distinta aquí. No se ha comparado el .c de smu/pm entre el repo y el paquete Fedora
```

## RE-33 · Las dos implementaciones del emisor de PTE difieren en un dword, y ambas existen

```
TYPE    FACT
STATE   PROVEN (que la diferencia existe)  ·  NOT_DETERMINED (cuál corresponde a qué ASIC)
SOURCE  lectura directa de los dos emisores, verificada 2026-10-01
LOCATION sdma_v3_0.c:982-997    SDMA_OP_GEN_PTEPDE  = 12   último dword = count
          sdma_v4_0.c:1643-1659  SDMA_OP_PTEPDE      = 12   último dword = count - 1
VERSION GFX6/GFX7 (v3_0, CIK/Tonga)  ·  GFX8 (v4_0, Vega10)
CONFIDENCE alta sobre el texto. La ASIGNACIÓN a un ASIC concreto es RE-32

  Both emit exactly 10 dwords:
      hdr · pe_lo · pe_hi · flags_lo · flags_hi · addr_lo · addr_hi · incr · 0 · count

LO QUE ESTA EN JUEGO, en una frase
  los dos emiten 10 dwords y el opcode vale 12 en los dos. La ÚNICA diferencia es si el
  último dword lleva `count` o `count - 1`. Un dword, y significa una entrada de más o de
  menos
POR QUÉ NO LO REGISTRO COMO UNA DIFERENCIA DE GENERACIÓN SIN MÁS
  porque el host dice que un ASIC GFX8 usa el emisor v3_0. Así que "v3_0 es Tonga y v4_0
  es Polaris12" es FALSO para esta máquina: ambos ficheros existen, los dos compilan, y
  este ASIC despacha por el v3_0
```

## RE-34 · El bloque MMU/VM de GFX8 no está publicado por AMD: `NOT_PUBLISHED`, no `NOT_DETERMINED`

```
TYPE    NEGATIVE_RESULT
STATE   PROVEN, y es una afirmación MÁS FUERTE que un NOT_DETERMINED
SOURCE  033-mmu-vm-no-publicado.md
CLASIF DE LA BÚSQUEDA  EXTERNAL, y el finding declara haber cumplido antes
        `CORPUS_COMPLETENESS_CHECK` y `READ_SCOPE_GATE` de AGENTS.md §DOCUMENTACIÓN EXTERNA
FUENTE  el índice de arquitectura de AMD, enumerado COMPLETO, no una búsqueda parcial

  https://gpuopen.com/amd-gpu-architecture-programming-documentation
  "If you're looking to work at a lower level with AMD hardware, this page contains links
   to some of our publicly available PDFs"

  grupo                documentos
  MES firmware          RDNA 3 MES                 1
  RDNA                  4 / 3.5 / 3 / 2 / 1 ISA    5
  CDNA                  5 / 4 / 3 / 2 / 1 ISA      5
  antiguas              Vega 7nm, Vega, GCN 3 ISA  3
  machine-readable      XML de ISA: sólo RDNA y CDNA. 0 para GCN3

  Catorce documentos. Catorce son ISA de SHADER y uno es firmware de scheduler.
  NINGUNO trata MMU, TLB, page walker, formato de PTE, ni orden de invalidación

POR QUÉ ES CONCLUYENTE Y NO SÓLO NEGATIVO, y por eso cambia la categoría
  el propósito que AMD declara para un ISA, textual:
    1. "Specify the language constructs and behavior, including the organization of each
        type of instruction in both text syntax and binary format."
    2. "Provide a reference of instruction operation that COMPILER WRITERS can use"
  Compiladores, no sistemas de traducción de direcciones. La ausencia de MMU en el índice
  no es un descuido de indexado: es que el documento no existe porque el propósito del
  documento no lo cubre
  El único que rozaría la planificación es el de MES, y es de RDNA 3, no de GFX8, y además
  declara por sí mismo "not meant to serve as a programming guide"

LO QUE RECLASIFICA
  019 / 030   efecto hardware de INVALIDATE_ALL por caché        NOT_PUBLISHED
  030         orden intra-envío entre el invalidate del PFP y el IB  NOT_PUBLISHED
  El finding declara que estos tres son ALIAS de los abiertos por 019/030/032

LO QUE ESTO HACE CON RE-29, y son la misma clase de hallazgo
  RE-29  el framing PM4 no está publicado
  RE-34  el bloque MMU/VM no está publicado
  Juntos no dicen "falta un documento". Dicen: la clase de documento que este proyecto
  necesita no es la clase de documento que AMD publica. Eso convierte una lista de
  fronteras bloqueadas en una restricción estructural, y es mejor noticia que una
  frontera bloqueada, porque una frontera bloqueada se puede desbloquear y una
  restricción hay que aceptarla o medir
LO QUE NO ES
  no es que el conocimiento sea inaccesible. Es que nunca se publicó. El único camino es
  RUNTIME, y eso ya estaba dicho por `C-010`
LIMITE  el índice de gpuopen es la lista de PDFs de AMD; no se ha hecho una búsqueda en
  toda la web de PDFs no indexados. La afirmación es sobre el catálogo oficial, y eso es
  lo que la sostiene
```

## RE-35 · `C-009` adjudicada de forma independiente, con el mismo árbitro

```
TYPE    DERIVATION
ALSO    CORROBORATION
STATE   CORROBORATED
SOURCE  035-block-size-tres-claims-y-un-log.md, que declara ADJUDICA= la contradicción C-003
        contra 030-page-walker, y RECTIFIES=024
LO QUE APUNTA
  "Dos roundings de esta ronda chocaron sobre el mismo número: block_size en GFX8. Había
   TRES valores circulando —13 (mío, en 024), 10 (la retractación C-003 de la sesión
   docs) y 22/23/24 (sesión de page-walker en 030-page-walker)"
  "el desempate no lo dio el código: lo dio el log de arranque del kernel"
  "`block_size = 10`. Mi 024 estaba mal. La retractación C-003 tiene razón. Y los
   22/23/24 están mal por un error específico y diagnosticable"

POR QUÉ ES CORROBORACIÓN Y NO DUPLICACIÓN
  tres sesiones publicaron cifras para block_size: 13 (024), 22 (030-walker), y una
  TERCERA sesión (035) las arbitró por el método que este árbol ya documentaba desde
  C-009: el log de arranque del kernel. Dos verificaciones independientes llegaron a 10,
  y ambas identificaron el mismo error en el perdedor
  Eso convierte C-009 de "verificación mía" en "criterio del proyecto". Y la sesión que
  arbitra CÓPIÓ el método del arbitraje anterior, lo cual es la señal de que la
  disciplina se está propagando sola

LO QUE AÑADE Y ESTA TREE EN docs/
  · la cadena recalculada desde cero, con phys_ram_gb = 12 MEDIDO en esta máquina
    (no supuesto): vm_size = roundup_pow_of_two(clamp(12*3, 64, 1024)) = 64
  · confirma que el mismo log sostiene los otros tres números de 024:
    vm_size = 64, num_level = 1, fragment_size = 9
    O sea que 024 no se cae, se corrige en UN punto y en todo lo que deriva de él
  · `C-003` queda ratificada por el árbol, no sólo por esta documentación
LIMITE  este registro se basa en su §CUDA y su §1. El resto no se ha leído
```

## RE-36 · El vector de interrupción de GFX8: 16 bytes, 4 dwords, y es el único sitio donde el hardware reporta un PASID

```
TYPE    FACT
STATE   PROVEN
SOURCE  051-interrupt-vector-iv-gfx8-y-teardown-lifo.md
LOCATION tonga_ih.c:248-270  tonga_ih_decode_iv
VERSION GFX8 · bloque tonga_ih · HARDWARE_SCOPE HOST-C/RX550/0000:01:00.0
CONFIDENCE alta. Transcripción literal del decodificador

  dw0   7:0     src_id       8 bits
  dw1   27:0    src_data[0]   28 bits
  dw2   7:0     ring_id       8
  dw2   15:8    vmid          8
  dw2   31:16   pasid        16

  ih->rptr += 16
  entry->client_id = AMDGPU_IRQ_CLIENTID_LEGACY   <- CONSTANTE. no se lee del vector

LO QUE APORTA Y ES NUEVO EN EL PROYECTO
  el PASID es 16 bits, y el vector de interrupción es el ÚNICO punto donde el hardware
  reporta un PASID. El resto del driver lo trata como parte de ATC_VMID{n}_PASID_MAPPING,
  que `N6` ya listaba como confounder y que nadie había medido
  Y `client_id` NO es un campo del vector: se fija a una constante. Quien modele el IV
  como una estructura de 4 campos más un client_id está añadiendo un campo que no
  existe
EL BLOQUE ACTIVO, y es la misma trampa de C-011 por tercera vez
  el log de arranque dice   ip block number 2 <ih_v3_0_0> (tonga_ih)
  y no existe ih_v3_0.c. Los ficheros de IH del árbol son ih_v6_0.c, ih_v6_1.c,
  ih_v7_0.c y tonga_ih.c. El bloque real es tonga_ih.c:503
  El propio hallazgo escribe el corolario, textual:
      "el nombre del ip_block en el log NO PREDICE el nombre del fichero. Hubo que
       localizarlo por el símbolo"
  Eso es EXACTAMENTE el error que hizo caer a 035 (sdma_v3_1_ip_block no tiene fichero), y
  el propio hallazgo registra la regla sin conocer aquella discusión
POR QUÉ LO REGISTRO POR ENCIMA DEL DATO TÉCNICO
  es una CORROBORACIÓN INDEPENDIENTE de la regla que este árbol acaba de aprender a costa
  de C-011. Tres casos ahora, todos con la misma forma:
      <sdma_v3_1_0> (sdma_v3_0)   -> no hay sdma_v3_1.c   -> C-011
      <ih_v3_0_0>   (tonga_ih)    -> no hay ih_v3_0.c     -> RE-36
      <gmc_v8_1_0>  (gmc_v8_0)    -> gmc_v8_0.c sí existe, pero otra generation
  La regla que sale, y es la que este árbol debería adoptar:
      el nombre del ip_block en el log es un NÚMERO DE VERSIÓN, no un nombre de fichero
      Para localizar el código hay que seguir `.funcs`, que es un símbolo, no una cadena
LO QUE EL HALLAZGO DICE QUE NO HACE, y está bien
  "Control de duplicación ejecutado ANTES de derivar: intrp, ivsrcid, VISLANDS30,
   AMDGPU_IRQ_CLIENTID, ih_v3_0 -> 0 ficheros en findings/ y docs/. Los 4 hits iniciales de
   IH eran \bIH matcheando dentro de otras palabras; con \bIH\b salen 0"
  Un `` mal puesto Daimundown los hits, y en este repo eso ya costó ocho horas a 019
LIMITE DE LECTURA  se registró el §CUDA y §1-§2. El overflow, el teardown LIFO y el
  ENABLE_L2_CACHE quedan sin verificar aquí
```

## RE-37 · La circularidad del test propio está declarada, medida y rota — y su validador tiene una salida conocida

```
TYPE    OBSERVATION
ALSO    NEGATIVE_RESULT
STATE   PROVEN, y el propio hallazgo declara su propio límite
SOURCE  038-validador-flujo-y-regla-del-count.md   (CLASSIFICATION=TOOL+CORRECTION)

LA CIRCULARIDAD, textual del hallazgo
  "036 y 037 declararon una circularidad: el codificador se escribió leyendo amdgpu, y
   las expectativas del test se transcribieron del MISMO amdgpu, así que un error de
   lectura replicado en los dos sitios pasa las 147 comprobaciones. 035 es exactamente
   eso, sucedido."
  Y "la circularidad está rota ahora con tools/rx550pm4val.c + rx550_pm4_emit.c: un
   generador que enlaza el mismo rx550_pm4.c que el módulo y llama a los mismos emisores,
   y un validador que NO TIENE ACCESO AL CORPUS. Los dos son correctos a la vez sólo si
   los dwords lo son"

POR QUÉ ESTO CORROBORA C-011 Y NO LA REFUTA, que es lo que hay que ver
  Yo había_registered que la suite de 036 no podía detectar `count - 1` porque las dos
  puntas leían la misma constante del mismo header. El hallazgo dice exactamente eso, y lo
  dice ANTES de que yo lo publicara, en su propia terminología ("circularidad")
  Y su criterio de falsificación admite el hueco, textual:
      "La afirmación de que el validador rompe la circularidad se refutaría si aceptara un
       flujo con un error de valor. YA SE SABE QUE ACEPTA UNO: count en vez de count-1.
       ESTÁ DECLARADO."
  O sea: el validador rompe la circularidad ESTRUCTURAL pero tiene una apertura de VALOR
  declarada. Dos niveles, no uno

LO QUE SIGUE MAL A LAS 13:14, y hay que fecharlo porque importa
  rx550_pm4.c mtime 2026-10-01 13:14:14
  línea 277   ib->buf[ib->length_dw++] = count - 1;
  El fichero se ha reescrito DESPUÉS de que 035 publicara su corrección y sigue con
  `count - 1`. No es un fichero abandonado: es código que se sigue tocando, con la
  entrada equivocada
  Contrastado contra C-011, que decía que este ASIC despacha por sdma_v3_0 y escribe
  `count` (sdma_v3_0.c:996, frente a sdma_v4_0.c:1658)

LO QUE EL VALIDADOR SÍ CONTRIBUYE, y es real
  · una REGLA, no una transcripción: en PACKET3 el campo count es payload − 1, y el total
    de dwords es count + 2. Siete paquetes medidos, siete cumplen:
      WRITE_DATA 3 · WAIT_REG_MEM 5 · PFP_SYNC_ME 0 · EVENT_WRITE 0
      SET_SH_REG 1 · SET_SH_REG×2 2 · DISPATCH_DIRECT 3
    Es `CORROBORATED` con RE-30, que loDerivan por otra vía (tres casos de WAIT_REG_MEM
    leídos enteros). Dos métodos, mismo número
  · para sDMA la longitud es IMPLÍCITA EN EL OPCODE, no en un campo count. Es la razón
    estructural por la que el error de 035 no lo caza una regla de PACKET3: PTEPDE no
    lleva campo de longitud que puedas validar contra count+2
  · mutación 3 declarada NO detectable por método, con la razón. Declarar la parte
    que no se puede detectar es más útil que fingir cobertura
    puede detectar es más útil que fingir cobertura
MEDICIÓN DECLARADA
  tools/rx550pm4val.c   850 líneas, C11, sin warnings, sha256 e9c7508b…a115
  selftest             12/12 PASS
  mutaciones           2 de 3 detectadas; la 3ª declarada no detectable
  suite completa       22 + 12 + 147 = 181 checks, 0 fallos
  rx550.ko             KBUILD_RC=0
NO REVISADO POR MÍ  todo lo anterior es la declaración del hallazgo. No se ha ejecutado
  rx550pm4val.c ni `make -C tests crosscheck`, ni calculado los sha256. Es TESTIMONY
LIMITE  el validador valida ESTRUCTURA. El error de C-011 es de VALOR. La estructura
  puede ser correcta y el dword equivocado
```

## RE-38 · Una cita de evidencia con `sha256` sin versionar quedó obsoleta en seis minutos, medida

```
TYPE    MEASUREMENT
STATE   OBSERVED, con cronología verificada por mí
SOURCE  el bloque §Evidencia de 038, contrastado contra el disco
POR QUÉ SE REGISTRA, y no como queja
  038 es el hallazgo mejor construido de esta mañana: declara su circularidad, rompe su
  circularidad, y declara su propia salida. Y aun así su bloque de evidencia ya no
  identifica el fichero que describe. No es un defecto del hallazgo: es una medición
  sobre lo que cuesta una convención de citación
LA CRONOLOGÍA, con quién midió cada punto
  13:10:33   038 escrito. Declara:  tools/rx550pm4val.c  850 líneas, sha256 e9c7508b…a115
  ~13:15:5x  MEDIDO POR MÍ:  928 líneas, sha dccddf5b…     +78 líneas, sha distinto
  13:16:46   mtime actual:  1018 líneas, sha 47168d22…    +90 líneas, sha distinto
  13:18:40   MEDIDO POR MÍ:  1018 líneas, sha 47168d22…    estable en tres tomas, 20 s
  Dos ediciones en ~6 minutos DESPUÉS de que el hallazgo publicara su hash. +168 líneas,
  +20 %, y el sha declarado ya no corresponde a nada
LO QUE HACE PERDERSE, y es concreto
  tools/rx550pm4val.c está UNTRACKED. `git ls-files --error-unmatch` -> no concorda con
  ningún archivo conocido. No hay forma de recuperar la versión de 850 líneas que el
  hallazgo describe, ni de volver a calcular su hash
  Y 07-DRIVER/tests/rx550_pm4_emit.c, declarado con 127 líneas y sha 900e83cc…a46, NO
  EXISTE en el disco en el momento de medir. Existe el directorio y el binario compilado
  `rx550pm4_emit`; el fuente no. Puede haber sido renombrado o haber estado a medio
  escribir. `NOT_DETERMINED`: no sé cuál
Y POR QUÉ ESTO ES UNA OBSERVACIÓN GENERAL Y NO UN INCIDENTE
  este repo ya tiene el defecto declarado desde hace tres rondas: `F7`, 30 findings y
  6 herramientas sin versionar. Lo que este caso añade es la MEDIDA del coste:
  en un artefacto que se reescribe continuamente, una cita con sha256 tiene una vida
  útil de minutos, y sin versionar no hay forma de recuperarla
  Consecuencia para el formato de evidencia de ESTE árbol: una cita de evidencia durable
  tiene que ser (fichero versionado + línea) o (fichero versionado + hash de ese
  commit). Un hash sobre un fichero sin versionar NO es evidencia: es una cifra
  que caduca. La distinción importa porque las dos se leen igual en un
  bloque §Evidencia
LO QUE NO AFIRMA
  no afirma que 038 sea falso. Afirma que su §Evidencia ya no es verificable. El hallazgo
  puede ser ENTERAMENTE correcto y seguir siendo imposible de auditar
  No he ejecutado rx550pm4val.c ni `make -C tests crosscheck`. Los 181 checks y el 12/12
  son TESTIMONY, y quedan como tale
LIMITE DE ESTA MEDICIÓN  tres tomas separadas 20 s, más dos medidas previas. Suficiente
  para establecer que el fichero cambió dos veces en seis minutos. No es una medida de
  la velocidad a largo plazo, y no pretende serlo
```

## RE-39 · Existen dos herramientas nuevas y **ninguna** cubre el gate que `C-011` necesitaba

```
TYPE    OBSERVATION
NOTA    con medición propia
STATE   OBSERVED
SOURCE  053-herramienta-asic-resolver-gate-compilacion.md y 038, contrastados con el disco
LO QUE SE MIDIO, por mí, no por el hallazgo
  tools/asic_resolver.py --selftest   ->  RESULTADO OK · rc=0   (a las 13:2x)
  grep -c "ip_block|ip_blocks" tools/asic_resolver.py  ->  0
  Y la propia herramienta lo dice en su salida:
    "NOTA: pasar esto NO valida la semantica del hardware"

LAS DOS HERRAMIENTAS, y qué resuelve cada una
  asic_resolver.py  §1 COMPILE_GATE_BEFORE_TRACE_GATE, como COMANDO y no como consejo
    "¿este .c entra en el binario para mi ASIC?"
    COMPILED_UNGATED · GATED_UNDECLARED · COMPILED_GATED_ON · NOT_COMPILED_GATED_OFF ·
    NOT_REFERENCED
    verifed per la sesión dueña: el error de 050 detectado por máquina, 15 de 39 ramas de
    smu7_hwmgr.c NO se ejecutan en nuestra tarjeta
  rx550pm4val.c  estructura de un flujo, sin acceso al corpus
    y DECLARA su salida: "ya se sabe que acepta uno: count en vez de count-1"
    y explica por qué no alcanza PTEPDE: para sDMA la longitud es implícita en el OPCODE
    "CODE_DEAD_IS_NOT_CODE · 15 de 39 ramas de smu7_hwmgr.c no se ejecutan en nuestra
     tarjeta. Tracearlas es trabajo desperdiciado y conclusión falsa si se mezclan"

LO QUE NINGUNA DE LAS DOS RESUELVE, y es precisamente lo que hizo falta en C-011
  RESOLVE_IP_BLOCK_DISPATCH_GATE
    ¿qué fichero de implementación ejecuta ESTE chip, siguiendo el puntero .funcs?
    Es una pregunta de DOS SALTOS con indirección por un const struct:
        vi.c:2107        case CHIP_POLARIS12:  sdma_v3_1_ip_block
        sdma_v3_0.c:1693  sdma_v3_1_ip_block { .funcs = &sdma_v3_0_ip_funcs }
        sdma_v3_0.c:1112  ... &sdma_v3_0_vm_pte_funcs   -> .set_pte_pde
    Un `chip_id ==` dentro de un fichero —que es lo que `--branches` sí resuelve— es otro
    mecanismo distinto: un switch en un solo fichero, no un puntero a través de una
    const struct declarada en otro
  LA MEDICIÓN DE QUE EL GATE FALTA, y es una línea
    grep -c ip_block tools/asic_resolver.py  ->  0
  Y la cruzada de 051 con RE-36: el nombre del ip_block del log NO predice el fichero, y
  la única forma correcta de encontrarlo es seguir `.funcs`, que es un símbolo. Eso es
  exactamente el gate que falta
VALOR, si es el más alto de esta ronda
  dos herramientas nuevas resuelven dos problemas reales y distintos, y las dos declaran
  sus límites. Entre las dos casi cubren el espacio, y el hueco que queda es el que costó
  una corrupción de memoria silenciosa
  Con la regla concreta: si el gate existiera, C-011 se habría cerrado ANTES de que 036
  escribiera el código. El valor de un gate no es lo que evita: es lo que llega a evitar
LO QUE ASIC_RESOLVER YA FIJA Y VALE MÁS ALLÁ DEL SMU
  COMPILE_GATE_BEFORE_TRACE_GATE     la regla sola se olvida; el comando se ejecuta
  CONFIG_IN_RHS_IS_NOT_A_GATE       un CONFIG_ como argumento no abre puerta. Contarlo al
                                     revés convertiría una regla incondicional en condicional
  CONFIG_WITHOUT_VALUE_IS_NOT_A_VERDICT   una puerta sin valor declarado es
                                     GATED_UNDECLARED, nunca NOT_COMPILED
  NAME_MATCH_NOT_SEMANTIC_MATCH     extends al nombre del FICHERO: polaris10_smumgr.c
                                     sirve a TRES generaciones y el nombre no dice cuál
  CODE_DEAD_IS_NOT_CODE             15 de 39 ramas no se ejecutan. Es la generalización de
                                     046 y de C-011 al mismo gate
LIMITE  self-test y rc=0 son míos. El resto es la declaración del hallazgo. No he medido
  los 15 de 39 ni el censo del scope smu
```

## RE-40 · El vector de interrupción queda **decodificado por completo**, y con él se abre una tabla de 112

```
TYPE    DERIVATION
ALSO    NEGATIVE_RESULT
STATE   PROVEN por vía estática
SOURCE  052-srcid-de-fault-gfx8-y-tabla-de-iv-no-catalogada.md
CONTINUES  051 §2, el layout del IV (RE-36)
VERSION GFX8 · HARDWARE_SCOPE HOST-C/RX550/0000:01:00.0
CONFIDENCE alta. Dos piezas independientes: layout transcrito, SRCIDs contiguos

LO QUE CIERRA, y es el ciclo completo
  RE-36 dio el layout: dw0 src_id 8 · dw1 src_data[0] 28 · dw2 ring_id 8 / vmid 8 /
        pasid 16, 16 bytes en total
  052 añade que el driver registra DOS SRCID para fallos de traducción, y que sus
  números son 0x92 y 0x93, contiguos, y ambos apuntan al MISMO handler
  Con las dos piezas, el IV se lee entero:
      src_id        dice QUÉ pasó
      vmid, pasid   dice QUIÉN
  Y en faults de traducción concretamente, que es lo que esta línea necesita para
  diagnosticar un fallo de page table
  CORRECCIÓN RE-47, 2026-10-01, y esta fila estaba mal en su tercera línea
    esta ficha decía «src_data[0] dice DÓNDE».  No lo dice: el IV de GFX8 no lleva una
    dirección de memoria.  src_data[0] es el SUBTIPO del evento de DISPLAY, y lo
    interpreta dce_v8_0.c, no el bloque de interrupts.  Medido: tonga_ih.c:263 lo
    produce y dce_v8_0.c lo consume en un switch
    lo que queda en pie: el layout, el PASID de 16 bits como único punto donde el
    hardware lo reporta, y los dos SRCID de fault de traducción

LO QUE ABRE, y es del mismo tamaño que lo que cierra
  la tabla tiene 112 vectores. NINGUNO está catalogado en el proyecto.
  Es `NOT_FOUND` con el universo declarado —la tabla del driver—, y por tanto no es
  todavía una ausencia: es un censo sin hacer
  Para esta línea, el subconjunto que importa es el de faults de traducción, y ahora se
  sabe que son DOS entradas, no un rango. Es un dato pequeño y muy accionable: quien
  escriba el manejador de faults del driver propio tiene exactamente dos casos
LO QUE ESTO NO ES
  no dice qué hace el hardware con cada uno de los 112. Dice que existen, que están
  numerados, y que dos de ellos son de traducción. El payload semántico de cada SRCID
  sigue `NOT_PUBLISHED` (RE-34)
LIMITE DE LECTURA  registrado desde su §CUDA. Los 112 nombres y su contenido no se han
  verificado aquí
```

## RE-41 · `ipsolve`: los 9 bloques activos del host, resueltos desde el corpus, con `9 de 9`

```
TYPE    MEASUREMENT
STATE   PROVEN por vía mecánica, y CORROBORATED por arbitraje del hardware
SOURCE  TL-11, `tools/ipsolve.py --bootlog`
VERSION GFX8 · kernel 7.1.3-200.nobara.fc44, arrancado hoy a las 05:49:05
CONFIDENCE alta. Es lectura de fuente contra el autoinforme del kernel, sin una sola
           expectativa escrita a mano

  #  tipo    version    funcs->name    bloque del corpus         implementado en
  0  common  1.0.0      vi_common      vi_common_ip_block        amdgpu/vi.c
  1  gmc     8.1.0      gmc_v8_0       gmc_v8_1_ip_block         gmc_v8_0.c
  2  ih      3.0.0      tonga_ih       tonga_ih_ip_block         tonga_ih.c
  3  gfx     8.0.0      gfx_v8_0       gfx_v8_0_ip_block         gfx_v8_0.c
  4  sdma    3.1.0      sdma_v3_0      sdma_v3_1_ip_block        sdma_v3_0.c
  5  smu     1.0.0      powerplay      pp_smu_ip_block          pm/powerplay/amd_powerplay.c
  6  dce     1.0.0      dm             dm_ip_block               display/amdgpu_dm/amdgpu_dm.c
  7  uvd     6.3.0      uvd_v6_0       uvd_v6_3_ip_block         uvd_v6_0.c
  8  vce     3.4.0      vce_v3_0       vce_v3_4_ip_block         vce_v3_0.c

LO QUE CONFIRMA, cada uno por separado
  C-011  el ASIC despacha PTE por sdma_v3_0, NO sdma_v4_0. Resuelto con un comando
  051    tonga_ih_ip_block -> tonga_ih.c, y no existe ih_v3_0.c
  046    pp_smu_ip_block -> pm/powerplay/amd_powerplay.c, o sea la ruta PowerPlay con
         smu7, y no legacy-dpm
LO QUE DESCUBRE Y NO ESTABA DOCUMENTADO
  el bloque de display de esta máquina es `dm_ip_block`, y sus funcs viven en
  display/amdgpu_dm/amdgpu_dm.c con .name = "dm"
  ese camino sólo se alcanza bajo  `#if defined(CONFIG_DRM_AMD_DC)`  y
  `else if (amdgpu_device_has_dc_support(adev))`   (vi.c:2117-2120)
  -> DisplayCore está COMPILADO y ACTIVO en este host
  y en el caso VI de vi.c NO hay rama `else` para dce_v10_0 (compárese con el caso
  TONGA en 2098-2099, que sí la tiene). O sea que si DC no estuviera soportado, esta
  tarjeta no tendría NINGÚN bloque de display
  Es `DERIVABLE del boot log`, y por tanto del orden de los bloques y de la ruta que
  el kernel tomó. No es una suposición
Y UNA CORRECCIÓN DE UNA AFIRMACIÓN MÍA
  C-011 decía, en su bloque de cadena, que el despacho era "vi.c:2113". Sigue siendo
  cierto, pero la afirmación completa es que TODOS los nueve se despachan desde
  vi.c:2109-2122, en una única región, y ese es el dato estructural
POR QUÉ ESTA ES LA MEDICIÓN MÁS FUERTE DEL ÁRBOL
  no compara mi modelo con el hardware.  Compara el CORPUS con el kernel, sobre los
  nueve bloques que el kernel dice haber seleccionado. Si el corpus describiera otra
  cosa, saldría 8 de 9 o menos
  Y el arbitraje es el mismo que zanjó C-009 y C-011, pero REPETIBLE con un comando
LIMITE  el campo entre paréntesis del log es `funcs->name`, que es lo que
  compara. El campo entre ángulos mezcla el TIPO con la versión y no es
  comparable a nada del corpus. Y la condición de un despacho guardado no se
  decide: se cita

## RE-42 · `docscan` encontró un número falso que yo mismo escribí, y por eso existe `--sync`

```
TYPE    OBSERVATION
NOTA    con confesión
STATE   PROVEN
SOURCE  TL-12, `tools/docscan.py`
LO QUE PASÓ, textual
  Escribiendo a mano el equivalente a la corrección de contadores, hice
      cd docs && git ls-files
  en vez de
      git -C <repo> ls-files
  `git ls-files` imprime rutas relativas al directorio ACTUAL, así que desde docs/
  no casaba nada. La conclusión fue "0 de 88 versionados", y esa cifra FALSA quedó
  escrita en CURRENT-STATE.md
  Lo detectó el propio escáner en la línea siguiente:
      stale counters-stale CURRENT-STATE.md: untracked count says 87, reality 49
  Corrección real: 88 findings, 38 versionados, 50 sin versionar
POR QUÉ ESTO ES EL ARGUMENTO A FAVOR DE LA HERRAMIENTA, y no en contra de mí
  un contador que depende de un one-liner humano SE VA a desincronizar, en silencio,
  y la desincronización PARECE un hallazgo. Cualquier agente que leyera "0 de 88
  versionados" concluiría que todo el trabajo de la mañana está a punto de perderse.
  Era falso, y lo más peligroso de un número falso es que suena urgente:
  invita a actuar sobre algo que no está pasando
  --sync mide y corrige en el mismo sitio, informa de cada sustitución, e idempotente
  Tres controles negativos: preserva la prosa, informa cada cambio, y una segunda
  pasada no cambia nada. La idempotencia está porque la primera versión no lo era:
  actualizaba `TRACKED 31 de 0` y dejaba el denominador, y `31 de 0` es PEOR que
  `0 de 0` porque parece medido
LO QUE HACE CON LAS REVISIONES RESTANTES
  los 9 ítems de `review` son CORRECTOS. `sdma_v3_1.c` e `ih_v3_0.c` se citan
  precisamente porque no existen: es el contenido de C-011 y de RE-36. Una
  herramienta que exigiera resolverlos induciría a borrar la afirmación central
LIMITE DECLARADO EN SU PROPIO FICHERO
  docscan NO comprueba que una afirmación sea verdadera. Nada puede. Comprueba
  coherencia interna y trazabilidad. Los dos defectos más graves de hoy eran de
  contenido y se arbitraron contra el hardware, no con un escaneo
```

## RE-43 · `msg_census` sobreestima el número de mensajes SMC en 36×, y su self-test pasa

```
TYPE    MEASUREMENT
NOTA    y el hallazgo de mayor valor de esta ronda
STATE   REFUTED el titular de la herramienta.  El resto de la herramienta sigue sin juzgar
SOURCE  medido por mí, 2026-10-01 ~14:5x
PROVOCADO POR  TL-13 `toolreg`: msg_census no la cita NINGÚN hallazgo, y toolcheck.py
        registra un incidente suyo.  Un árbol documental tiene que responder a las dos
        cosas a la vez

EL INCIDENTE QUE YA ESTABA REGISTRADO, y que nadie cerró
  `tools/toolcheck.py` lo dice textual, en su propia cabecera:
    "msg_census devolvió durante una tanda 503 números de mensaje, la mayoría de la
     generación equivocada, sin avisar.  El número era plausible; sólo se detectó
     porque alguien comprobó a mano qué cabecera se estaba usando"
  Alguien ya pag ese coste.  Y el número ha vuelto a salir.

LO QUE DICE LA HERRAMIENTA
  $ msg_census.py --kernel RESEARCH/kernelbuild/linux-7.1.3 --chip CHIP_POLARIS12
      llamadas de envio: 503
      mensajes distintos: 217
      símbolos sin resolver (217): None, PPSMC_MSG_ACPPowerOFF, ... PPSMC_MSG_SetFanPwmMax, ...
  por sus propios veredictos de uso, desglosados por mí:
      total              503
      veredicto VIVA      11
      veredicto MUERTA     5
      veredicto NO_CONDICIONAL  487
  reparto por familia de cabecera (total / VIVA):
      (sin resolver)   194 /   9
      rv               118 /   0     <- RISC-V, no es amdgpu x86
      vega12            73 /   0
      cz                62 /   0
      fiji              19 /   0
      vega10            15 /   0
      smu7              12 /   2     <- NUESTRA familia
      vega20            10 /   0

LO QUE DICE LA REALIDAD, medida contra el fichero ACTIVO
  la ruta activa de Polaris12 la fijó `046` y la confirmó `ipsolve`:
      hwmgr.c:154-158   case CHIP_POLARIS11/10/12 -> smumgr_funcs = &polaris10_smu_funcs
      -> el fichero que manda es  pm/powerplay/smumgr/polaris10_smumgr.c
  y ese fichero:
      llamadas de envío:  14
      símbolos distintos: 14
      #include "smu7_ppsmc.h"
  los 14 contra smu7_ppsmc.h, uno a uno:   14 resueltos, 0 sin resolver

  Cifra correcta: 14 mensajes.  Titular de la herramienta: 503.  Sobreestimación: 36×

LA CIFRA QUE CORRECTAMENTE SE LEE DEL TITULAR
  503 es el número de SITIOS DE ENVÍO en todo el subárbol pm/, no de mensajes que esta
  GPU pueda enviar.  Los 487 con veredicto NO_CONDICIONAL no son 487 mensajes de esta
  tarjeta: son sitios de otras generaciones y de RISC-V

DOS DEFECTOS DISTINTOS, y separarlos importa
  1 el titular no está filtrado.  La herramienta SÍ trae el veredicto VIVA/MUERTA por
    uso, o sea que la información para filtrar está dentro de su propia salida y no se
    aplica al número que se lee.  El filtro ya existe: no está aplicado
  2 la resolución de cabeceras falla en 194 símbolos, y entre ellos hay mensajes que
    SÍ viven en smu7_ppsmc.h, que es la cabecera del fichero activo.  Ejemplos
    comprobados como NO presentes en smu7_ppsmc.h:
      PPSMC_MSG_DisableFFC · PPSMC_MSG_SetFanPwmMax ·
      PPSMC_MSG_SetSoftMaxGfxclkByIndex · PPSMC_MSG_GetTemperatureHotspot
    esos cuatro están en pm/powerplay/inc/vega10_ppsmc.h, que es la familia sister de
    la ruta polaris10, no del fichero activo
  O sea: el 503 no es sólo un titular sin filtrar, es un titular sin resolver.  Las dos
  cosas hacen que la cifra sea mayor de lo que parece, no menor

EL ERROR DE RAZÓN ES UNO QUE ESTE REPO YA HA PAGADO
  mirar un nombre de fichero y decidir a qué generación pertenece.  vega10_ppsmc.h
  PARECE de otra generación y sin embargo polaris10 desciende de vega10, así que el
  nombre engaña y el linaje no
  Es la misma forma que C-011 por el otro lado: allí una convención de nombres
  sugería un fichero que no existía; aquí sugiere una generación que no es la que dice.
  El número fiable es el del `.funcs` y el del include, no el del nombre

POR QUÉ EL SELF-TEST NO LO CAZA, y eso es lo más grave
  `msg_census.py --selftest` -> "RESULTADO OK · vectores conocidos reproducidos", rc=0
  Su self-test comprueba que reproduce unos vectores conocidos, que es comprobar que
  el parser funciona.  NO comprueba que el censo esté acotado a mi ASIC, que es la
  propiedad que falló y la que un usuario necesita
  Un self-test que verifica el parser y no la afirmación es la razón por la que un
  número falso sobrevivió a dos Personas y a una mañana

LO QUE ESTO PROTEGE, y es lo importante
  la línea H se está trabajando AHORA MISMO: hay un .write-lock/smu activo, y 040 a
  050 son de esa línea.  Si alguien construye el modelo de mensajes SMC sobre el 503,
  construye sobre un número 36× mayor que el real, con 487 sitios que no son de esta
  tarjeta.  El modelo sería internamente coherente y no serviría para nada, que es
  exactamente el resultado que produjo el error de 046 con si_dpm.c

CÓMO SE USA, ENTONCES, Y QUÉ HAY QUE HACER
  para el recuento de mensajes de ESTA GPU: no usar el titular.  Contar sobre
  polaris10_smumgr.c, que es el fichero que la ruta activa selecciona, y resolver
  contra smu7_ppsmc.h, que es el include que ese fichero hace.  Medido: 14 y 14
  lo que la herramienta SÍ es útil: el veredicto por uso, y el inventario de símbolos
  con sus ficheros.  Eso es un dato bueno con un titular malo
  lo que haría falta para arreglarla, y NO se aplica aquí porque es trabajo de otra
  sesión: que el titular sea el número de usos VIVA, y que la resolución de cabecera
  se haga contra el include del fichero activo y no contra todos los headers del árbol

LIMITE DE ESTA MEDICIÓN
  el recuento de 14 es de sitios de llamada a smum_send_msg_to_smc* en polaris10_smumgr.c.
  NO incluye el camino compartido de smu7_hwmgr.c (6 sitios) ni las rutas de Reliability,
  Voltage, SVI o PSP, que son llamadas SMC de otra clase y este hallazgo no las cuenta
  14 es el orden de magnitud del conjunto de mensajes del gestor de energía de esta
  tarjeta.  El conjunto completo es >= 14, y eso se declara en vez de inventarse
```

## RE-44 · La caja de herramientas creció 44 en una mañana, y el registro es lo único que la acota

```
TYPE    OBSERVATION
STATE   OBSERVED, con las tres mediciones
SOURCE  TL-13 `toolreg`, ejecutado tres veces sobre el árbol real en esta tarde

LAS TRES MEDICIONES, y por qué la escala es el hallazgo
  1ª ejecución, escaneando tools/                 23 herramientas
  2ª ejecución, escaneando las DOS ubicaciones     26 herramientas
  3ª ejecución, minutos después                   44 herramientas
  documentadas en TOOLS-STATUS:  4  ->  12  de 44
  Entre la 2ª y la 3ª aparecieron trece:
    frontier · gmmio_inventory · include_closure · pm4_codec · pm4_layout_audit ·
    pm4_reachable · run_all · runtime_obs · toolkit · binfacts · causal_map ·
    corpus_guard · doclint
  Y `pm4census` y `hwip` entre ellas

  El árbol construye más rápido de lo que un registro written a mano puede seguir.  Esa
  es la razón de que este registro sea una HERRAMIENTA y no un fichero

LO QUE MIDÓ Y ES LA CIFRA QUE HAY QUE LEER
    self-test PASS                15
    NO_SELFTEST                   19
    NONZERO                        2
    REFUSED_UNDECLARED             7
    SELF                           1
    documentadas                 12 de 44
  PASS 15 de 44.  No 44.  La columna PASS de esta tabla cubre quince herramientas, y las
  otras veintinueve están sin verificar por el registro.  Un `NO_SELFTEST` no es un
  `PASS_POR_DEFECTO`: es un hueco, y por eso se cuenta aparte

DOS DESCUBRIMIENTOS SOBRE LA ESTRUCTURA DE LA CAJA
  1 HAY DOS CONVENCIONES DE CONTRATO, y no una
      tools/                  WORK_CLASS=READ_ONLY · WRITE_EXECUTION=NONE
      08-ARQUITECTURA/tools/  # CONTRACT: name=... READONLY=no  WRITES_FILES=yes
    la primera versión del registro sólo reconocía la primera y reportaba «13 sin
    declaración WORK_CLASS».  Buena parte no era una declaración ausente: era la misma
    declaración con otra ortografía
  2 HAY DOS DIRECTORIOS DE HERRAMIENTAS, y el primero no lo sabía
    pm4_count_census.py, count_vmflush_dw.py y frame_budget.py estaban documentadas como
    entradas de tools/ y ahora están en 08-ARQUITECTURA/tools/.  El registro las
    reportaba como «entradas TL que nombran una herramienta que no existe», que es el
    peor de los dos errores posibles: acusar una pérdida donde sólo hubo una mudanza
    Y eso es también por lo que la cuenta de herramientas casi se duplicó al corregirlo

LO QUE LAS TRES HERRAMIENTAS NUEVAS ATACAN, y es lo importante
  pm4census.py      «mide la convención de count de PACKET3 SOLO en el ASIC que» — que es
                    exactamente el filtro que a msg_census le falta (RE-43)
  pm4_reachable.py  «vocabulario PM4 VIVO de un ASIC: qué paquetes ejecuta de verdad, no
                    cuáles define» — que es la distinción que separates el contraejemplo
                    cuáles define» — que es la distinción que separa el contraejemplo
                    vivo de RE-31 de doce coincidencias que sólo parecen tales
  hwip.py           «responde, para cada bloque: esto lo decide el caso del chip, o la
                    versión» — que es la pregunta que ipsolve responde por otra vía
  Nadie lo pidió: el equipo aprende sin que nadie lo imponga, y el registro es lo
  El equipo aprende sin que nadie lo imponga, y el registro es lo que lo hace visible

LO QUE ESTO NO ES
  no es un problema de herramientas: es un problema de CATÁLOGO.  Las herramientas
  existen, funcionan en su mayoría, y el coste real fue el de buscar a mano lo que ya
  estaba automatizado.  Ocho horas de esa mañana fueron eso
  Y es el riesgo de heredar un titular sin verificar.  RE-43 es el segundo, y ya había
  cobrado una vez, documentado en la cabecera de toolcheck.py desde antes de esta mañana
LIMITE  el recuento de 44 es de ficheros fuente .py/.c/.sh.  No cuenta binarios
  compilados, ni herramientas de sistema, ni guiones de una línea.  Y tres aparecieron
  DESPUÉS de la última medición, así que la cifra real es mayor que 44
```

## RE-47 · `src_data[0]` es el SUBTIPO del interrupt de display, no «dónde». Corrige `RE-36` y `RE-40`

```
TYPE    FACT
ALSO    DERIVATION
STATE   PROVEN   (el productor y el consumidor, medidos)   ·   CORRECTION de esta misma tabla
SOURCE  058 -> 059 -> 060 -> 061, y el consumidor verificado por mí
LOCATION tonga_ih.c:263      entry->src_data[0] = dw[1] & 0xfffffff     (PRODUCE, 28 bits)
          dce_v8_0.c         switch (entry->src_data[0])                 (CONSUME)
          amdgpu_ih.c:289-292  escribe src_data[0..3] desde dw[4..7]      (otra variante)
VERSION GFX8 · HARDWARE_SCOPE HOST-C/RX550
CONFIDENCE alta. El productor y el consumidor están medidos, no inferidos

LO QUE YO HABÍA ESCRITO, y estaba mal
  RE-36 y RE-40 dicen, textual:
      src_id        dice QUÉ pasó
      vmid, pasid   dice QUIÉN
      src_data[0]   dice DÓNDE
  «Dice dónde» no tiene base. El IV de GFX8 no lleva una dirección de memoria

LA CADENA DE TRES PASSOS, que es lo instructivo
  058 abrió tres candidatas y nombró como más probable que src_data[0] —los 28 bits—
    llevase el detalle del evento
  059 REFUTÓ eso: el único consumidor de src_data[0] en toda la generación es un puntero
    de ring, luego no es payload.  Y loqueued como CORRECTION de 058
  060 CORRIGE a 059, textual: «Eso era cierto pero no era la pregunta correcta, porque el
    decodificador no estaba en el bloque de interrupts —estaba en el de DISPLAY, y para
    esta misma GPU»
  Y así es, medido: tonga_ih.c lo PRODUCE y dce_v8_0.c lo CONSUME en un switch
  061 cierra lo que 060 dejó abierto: qué subtipos hay para src_data[0] > 1.  Son dos,
    constantes en todo el dominio legal, con los MISMOS comentarios carácter a carácter en
    GFX6, GFX8 y GFX10.  `default` existe por robustez, no para cubrir un tercer caso
    Y lo nombra DERIVATION_BEFORE_OBSERVATION: si el resultado es constante en el dominio,
    la observación no aporta. Aquí no hay ni una observación que hacer

  lo que queda de RE-36 y RE-40, para no tirar más de lo que se sostiene
  · src_id 8 bits en dw0[7:0]                      sigue en pie
  · vmid 8 bits en dw2[15:8], pasid 16 en dw2[31:16]  sigue en pie, y es el único punto
    donde el hardware reporta un PASID
  · los dos SRCID de fault de traducción son 0x92 y 0x93, mismo handler  sigue en pie
  · el IV se lee entero: QUÉ (src_id), QUIÉN (vmid, pasid)  sigue en pie
  lo que se cae es la tercera línea: src_data[0] NO dice dónde. Dice el subtipo del
    evento, y el HARDWARE lo interpreta el bloque de DISPLAY, no el de interrupts

POR QUÉ ESTA CORRECCIÓN ME IMPORTA MÁS DE LO QUE PARECE
  es la TERCERA vez hoy que una corrección viene de una herramienta o de un hallazgo
    posterior, y las tres tienen la misma forma: alguien se hizo la pregunta correcta
  mismo campo y la respuesta cambia
    C-009  block_size: 13, luego 22, luego 10
    C-011  emisor de PTE: v3_0 frente a v4_0
    RE-47  src_data[0]: payload, luego puntero de ring, luego subtipo de display
  En los tres casos la respuesta intermedia no era falsa: era la pregunta equivocada.
  Y en los tres la corrección la encontró una sesión distinta, leyendo
LIMITE DE ESTA LECTURA  registrado desde el §CUDA y la verificación del consumidor.
  061 no se ha leído más allá de su §CUDA
```

## RE-48 · `SDMA0_HWIP` no llega a leerse para este ASIC, y por eso su valor no puede cambiar ninguna conclusión

```
TYPE    DERIVATION
NOTA    (por alcanzabilidad)
STATE   PROVEN
SOURCE  043-vuelta-atras-035-y-036-leian-el-asic-equivocado.md  ·  que cita a
        046-la-version-de-ip-que-nunca-se-consulta.md
VERIFICADO POR MÍ, la parte load-bearing
    journalctl -k -b | grep "detected ip block"
      number 4 <sdma_v3_1_0> (sdma_v3_0)
    vi.c:2113        CHIP_POLARIS12 -> sdma_v3_1_ip_block
    amdgpu_discovery.c  el switch por amdgpu_ip_version(adev, SDMA0_HWIP, 0) es el camino
                        de resolución de IP VERSIONS, y la ruta de Polaris12 lo resuelve
                        por caso de ASIC, no por versión
LO QUE AFIRMA, textual del hallazgo
  «el NOT_DETERMINED que este documento dejó abierto —"¿qué versión de SDMA0_HWIP tiene esta
   tarjeta?"— era la pregunta equivocada.  No hace falta leer el registro, porque el código
   que lo consultaría no se ejecuta para este chip.  La versión de SDMA no llega a leerse,
   así que su valor no puede cambiar ninguna conclusión.  Demostrado por alcanzabilidad,
   sin MMIO»
POR QUÉ ES MÁS FUERTE QUE MI ARBITRAJE, y lo reconozco
  yo zanjé C-011 con el log de arranque y con ipsolve: el bloque activo es sdma_v3_1_ip_block,
  cuyo .funcs es sdma_v3_0_ip_funcs, así que el emisor es sdma_v3_0_vm_set_pte_pde
  eso demuestra qué IMPLEMENTACIÓN corre.  046 demuestra algo más fuerte y más cómodo:
  que el VALOR de SDMA0_HWIP para esta tarjeta no es una variable de la que dependa nada,
  porque el código que la lee no se ejecuta
  y por eso la pregunta «¿cuál es el SDMA0_HWIP de esta tarjeta?» no tiene respuesta
  relevante, que es un caso raro y valioso: una pregunta cuya respuesta no importa
LA TERCERA RETRACCIÓN DE 035 Y 036, por tres caminos distintos
  1  esta documentación  C-011: por el log y por el despacho, resueltos con ipsolve
  2  otra sesión      035 se equivocó por leer el fichero de otra generación
  3  otra sesión      043: la herramienta lo encontró, y se cierra por alcanzabilidad
  Tres caminos independientes al mismo veredicto, y ninguno de los tres es «lo he leído en
  la spec», porque la spec no existe (RE-29).  Es lo que hace que una corrección sea
  robusta: que la siguiente persona que mire llegue a lo mismo desde otra dirección
RESIDUO  `035` y `036` siguen UNTRACKED en el disco con sus cifras, y `036` es
  implementación viva con `count - 1` en rx550_pm4.c:277.  No se editan: son de otra
  sesión.  F3d
```

## RE-52 · El emisor de PTE propio replica `sdma_v3_0.c` dword a dword, y escribe `count`

```
TYPE    MEASUREMENT
STATE   OBSERVED
WHAT    Si la función de PTE/PDE del driver propio reproduce la del emisor que este
        ASIC ejecuta, campo a campo y en orden, y si el último dword es `count` o
        `count - 1`
WHERE   07-DRIVER/kernel/rx550_pm4.c, función `rx550_sdma_vm_set_pte_pde`
WHEN    2026-10-02
HOW     extracción de las asignaciones `ib->buf[ib->length_dw++] = ...` de la
        función propia, y de `ib->ptr[ib->length_dw++] = ...` del bloque
        correspondiente de `sdma_v3_0.c`, y comparación posicional
UNIT    dwords escritos, y posición
LOCATION  07-DRIVER/kernel/rx550_pm4.c:280   void rx550_sdma_vm_set_pte_pde(...)
         07-DRIVER/kernel/rx550_pm4.c:298   ib->buf[ib->length_dw++] = count;
         sdma_v3_0.c:986-996                 el bloque del emisor que se ejecuta
         07-DRIVER/kernel/rx550_pm4.h         RX550_SDMA_PTEPDE_DW = 10
LIMITATION
  · compara la SECUENCIA DE ASIGNACIONES, no los tipos, ni el endianness en
    memoria, ni el relleno del IB hasta `RX550_SDMA_PTEPDE_DW`.  Que el último
    dword sea `count` es un hecho sobre el CÓDIGO, no sobre lo que el ASIC hace
    con él: eso sigue siendo `NOT_DETERMINED` y es `F1`
  · no ejecuta el driver ni observa la GPU.  `RUNTIME = NOT_RUN`
  · y no dice que la función sea correcta en el resto de su contrato: sólo que
    replica la secuencia del emisor de referencia
PRODUCER lectura directa del fichero propio y del corpus
CONSUMER `F3d`, que queda CORRECTED, y `036`, que queda retractado en su campo
EFFECT  cierra el defecto más grave que este driver propio tenía

LA MEDICIÓN
  nuestro driver   10 dwords        sdma_v3_0.c   10 dwords
    1  rx550_sdma_header(RX550_SDMA_OP_PTEPDE)   SDMA_PKT_HEADER_OP(SDMA_OP_GEN_PTEPDE)
    2  (__u0032)(pe   & 0xFFFFFFFFu)             lower_32_bits(pe)      /* dst addr */
    3  (__u0032)(pe   >> 32)                     upper_32_bits(pe)
    4  (__u0032)(flags & 0xFFFFFFFFu)            lower_32_bits(flags)   /* mask */
    5  (__u0032)(flags >> 32)                    upper_32_bits(flags)
    6  (__u0032)(addr  & 0xFFFFFFFFu)            lower_32_bits(addr)    /* value */
    7  (__u0032)(addr  >> 32)                    upper_32_bits(addr)
    8  incr                                      incr                   /* increment */
    9  0                                         0
   10  count                                     count                  /* n. entries */

  idénticos en número y orden: True
  RX550_SDMA_PTEPDE_DW = 10 · dwords escritos = 10 · concuerda: True
  último dword propio: count      último dword del kernel: count

CUAL ERA EL DEFECTO, Y POR QUÉ ERA EL MÁS GRAVE QUE TENÍA ESTE DRIVER
  escribía `count - 1`.  Un PTE por encima del final del rango pedido, que es
  corrupción silenciosa de memoria: el driver compila, la suite pasa, y el daño
  ocurre en la GPU sin que nada lo delate

LAS DIEZ APARICIONES DE `count - 1` QUE QUEDAN EN `07-DRIVER/`
  TODAS están en comentarios y tests que documentan el error.  Ninguna en código:
      rx550_pm4.c:239, 248, 257    el comentario que explica la corrección
      test_pm4.c:327, 330, 375, 397   los tests que lo afirman
      rx550_pm4_emit.c:10          la nota de la herramienta de pruebas
      rx550pm4.h:463
  y `test_pm4.c:375` dice: «findings/034 said this field was count-1. It is not, on
  this ASIC»

POR QUÉ SE CAYÓ DOS VECES, Y LA SEGUNDA VEZ EN DIRECCIÓN CONTRARIA
  en el corpus hay dos emisores, y esta GPU ejecuta el que escribe `count`:
      sdma_v3_0.c:986-996    `count`       <- se ejecuta
      sdma_v4_0.c:1658       `count - 1`   <- no se ejecuta
  `023` leyó `sdma_v3_0.c` y registró `count`: correcto.
  `034` leyó `sdma_v4_0.c` y lo «corrigió» a `count - 1`: equivocado, y en la
  dirección peligrosa, porque lo justificó con un contraste que él mismo leía del
  MISMO fichero
  lo escribe el propio driver, y es la observación más transferible de este
  hallazgo:
      «Un cross-check hecho sobre una sola fuente no es un cross-check, y citar dos
        líneas del mismo fichero como si fueran dos fuentes es la forma concreta
        que me engañó.»
  es la MISMA forma que `RE-47`, que `C-009` y que `C-011`: una respuesta
  intermedia que no era falsa, sino la pregunta equivocada.  Y un contraste hecho
  sobre una fuente no es un contraste

LO QUE ESTA CLAIM NO CIERRA, aunque cierra `F3d`
  qué hace el ASIC con ese `count` sigue siendo `NOT_DETERMINED`.  Que el código
  replique al emisor de referencia es `PROVEN` sobre el CÓDIGO.  Que el hardware
  lo interprete así, no: eso es `F1` y `F3c`, y sigue `BLOCKED_BY_AUTHORIZATION`
  y `NOT_PUBLISHED` respectivamente
  el proyecto ya tiene escrito ese límite: «hardware execution order NOT_PROVEN»
  y «hardware PTE visibility point NOT_DETERMINED»
```

---

## RE-51 · Las 43 constantes de `rx550_pm4.h` cuadran con su testigo, y eso acota dónde está el defecto de F3d

```
TYPE    MEASUREMENT
STATE   OBSERVED
WHAT    De cada `#define RX550_*` de la cabecera del driver propio, si el VALOR que
        escribió coincide con lo que define la línea upstream que su propio
        comentario cita como testigo
WHERE   07-DRIVER/kernel/rx550_pm4.h   43 constantes, 32 con testigo
WHEN    2026-10-02
HOW     constmap.py: parsea cada #define, extrae la cita del comentario, resuelve la
        línea con el MISMO resolutor que citations.py —importado por ruta, no
        reimplementado— y compara el valor
UNIT    constantes, y coincidencias/definiciones por línea citada
LOCATION  tools/constmap.py
          amdgpu/sid.h:343            #define PACKET3_NOP   0x10
          amdgpu/vid.h:201            #define PACKET3_SURFACE_SYNC 0x43
          amdgpu/vid.h:186-189        WAIT_REG_MEM_ENGINE(x), y 187/188 en prosa
          radeon/sid.h:343            #define SOFT_RESET_BIF (1 << 1)
LIMITATION
  · no evalúa macros.  2 constantes con expresión son NOT_COMPARABLE, no un
    número supuesto.  Evaluarlas con `gcc -E` es la siguiente jugada, no una regex
  · no decide cuál copia de una cabecera ambigua es la pretendida.  Cuando el
    valor no discrimina, lo dice y no fuerza
  · no juzga si una constante SIN testigo es correcta: UNCITED es incomprobable
    aquí, no falsa
  · AGREE prueba que el número coincide con una línea.  NO prueba la semántica
PRODUCER tools/constmap.py
CONSUMER quien implemente o revise 07-DRIVER/
EFFECT  acota F3d: la capa de constantes está limpia, luego el defecto es de
        otra clase y en otro fichero

LA MEDICIÓN
  AGREE 15               el valor coincide con un #define de la línea citada
  AGREE_DISCRIMINATING 8  coincide y además señala un subsistema entre ficheros
                         homónimos
  AGREE_COMMENT         4  el testigo es prosa que enumera el valor
  WITNESS_USAGE         3  el testigo usa la codificación pero no lleva el valor
  NOT_COMPARABLE        2  valor con expresión
  UNCITED              11  sin testigo
  DISAGREE  0
  AMBIGUOUS 0
  NOT_A_DEFINE 0

  los 32 con testigo quedan CUADRADOS: no queda veredicto sin explicar

POR QUÉ EL VALOR ARBITRA Y EL NOMBRE SOLO SE MUESTRA
  reconocer que RX550_PKT3_WAIT_REG_MEM y PACKET3_WAIT_REG_MEM son lo mismo exige
  saber que PKT3 abrevia PACKET3.  Eso es conocimiento.  Meterlo en la herramienta
  pondría una suposición donde va una medición, y podría casar dos constantes
  distintas con una sin decir nada
  por eso arbitra el VALOR y el nombre upstream se imprime al lado para que lo
  confirme una persona

LA TRAMPA QUE ESTA HERRAMIENTA ENCONTRÓ AL NACER
  sid.h tiene DIEZ copias en este árbol, y una está en drivers/gpu/drm/radeon/ con
  macros distintas en la MISMA línea:
      drivers/gpu/drm/amd/amdgpu/sid.h:343   #define PACKET3_NOP    0x10
      drivers/gpu/drm/radeon/sid.h:343       #define SOFT_RESET_BIF (1 << 1)
  quien verifique un valor de amdgpu con un grep puede caer en la del radeon y ver
  algo plausible.  Es la misma trampa que RE-50.Documenta, vista del otro lado
  y aunque la ambigüedad existe, el VALOR la resuelve: el autor copió el valor del
  fichero que tenía abierto, y 8 de 10 copias lo confirman.  Cuando no discrimina,
  se reporta AMBIGUO

CONSECUENCIA SOBRE F3d
  el defecto de F3d —`sdma_v4_0` donde el ASIC despacha `sdma_v3_0`, y `count - 1`
  en `rx550_pm4.c:277`— NO está en estas 43 constantes: no hay ni una
  contradicción.  Está en el `.c`, y es un error SIMBÓLICO, no de valores
  Eso parte F3d en dos: una mitad queda MEDIDA y cerrada, y la otra es un caso
  distinto con su propia evidencia
```

---

## RE-50 · 130 de las 2398 citas del texto propio caen en ficheros que este proyecto instrumentó

```
TYPE    MEASUREMENT
STATE   OBSERVED
WHAT    De cada cita `nombre.ext:N` del texto propio del proyecto, cuántas resuelven
        y con qué grado de solidez; y cuántas caen en ficheros que una sesión
        instrumentó, con el desplazamiento exacto que eso implica
WHERE   texto propio del proyecto (07-DRIVER, docs, findings, tools, 08-ARQUITECTURA)
        2398 citas
WHEN    2026-10-01, con el árbol en 78bfb19..e6210b0
HOW     citations.py: índice de los 72638 nombres de fichero de los 7 árboles, y para
        cada cita se lee la línea N en cada copia que la tiene
UNIT    citas, y líneas de desplazamiento entre copias de la MISMA versión
LOCATION  tools/citations.py
        amdgpu_vm.c       +12  working -> kernelbuild
        amdgpu_vm_pt.c    +26  working -> kernelbuild
        amdgpu_debugfs.c  +1   por zona, no constante
LIMITATION
  · la TRADUCCIÓN es por texto exacto y se rechaza si no es única, así que las
    líneas cuyo texto aparece varias veces quedan sin mapear.  Se listan, no se
    inventan
  · la herramienta NO decide la copia autoritativa.  Que working/baseline sean la
    buena ya lo probó `RESEARCH/evidence/working-vs-kernelbuild-difference.md` por
    hash contra los tarballs; esta claim aplica esa regla y no la establece
  · NO juzga si una cita es relevante para su afirmación.  Una línea que existe y
    dice otra cosa es otro fallo, y esto no lo ve
  · NO parsea C: busca `nombre.ext:número`, sin preprocesador ni grafo de includes
PRODUCER tools/citations.py
CONSUMER quién intente verificar una cita de docs/ o de 07-DRIVER/
EFFECT  convierte «el árbol importa» de una regla escrita en una medición de
        exposición, y da el desplazamiento exacto en vez de una advertencia

LA MEDICIÓN
  ROBUST 1070   toda copia dice lo mismo
  VERSIONED 839  versiones distintas que difieren: lo esperado, no un defecto
  UNIDENTIFIABLE 261  el nombre no dice qué fichero: la trampa
  FRAGILE 135   el corpus se contradice sobre la misma versión
  OUT_OF_RANGE 12 · UNRESOLVED 81

  de las 135 FRAGILE:
    130  en amdgpu_vm.c, amdgpu_vm_pt.c, amdgpu_debugfs.c, amdgpu_debugfs.h
      5  nombres genéricos: pci.h, types.h, file.c

CÓRREBORACIÓN, Y NO ES DESCUBRIMIENTO
  `RESEARCH/evidence/working-vs-kernelbuild-difference.md` §4 y §5 ya probaron por
  hash contra los tarballs que working/baseline son 7.1.3 prístino byte a byte y
  que kernelbuild lleva instrumentación `RE-02-E1 (RG-1)`.  Los +12 y +26 que mide
  esta herramienta son los de su tabla
  Lo que esta claim añade es la EXPOSICIÓN, que aquel documento no cuantifica

CONSECUENCIA SOBRE RE-10
  las líneas de RE-10 — 2424 2427 2428 2429 2454 2463 — son números PRÍSTINOS.
  Son los correctos para el kernel en ejecución `7.1.3-200.nobara.fc44`, que no
  puede contener `amdgpu_re02e1_note_call()` porque esa función la escribió este
  proyecto.  Contra kernelbuild cada una va desplazada 12
  RE-10 queda CORROBORADA, no retractada
```

---

## RE-49 · 24 de 47 claims del registro NO son auditables por la regla del propio proyecto

```
TYPE    MEASUREMENT
NOTA    sobre mi propia documentación
STATE   PROVEN, y verificado fichero a fichero para descartar que fuera artefacto del parser
SOURCE  TL-37 `claim.py`, con comprobación manual de las entradas señaladas
REGLA DEL PROYECTO, escrita en sus propios términos
  una claim debe poder localizarse.  Sin LOCATION —fichero:línea— dice DE QUIÉN es, no
  DÓNDE ESTÁ
LA MEDICIÓN, y una corrección a una afirmación mía anterior
  claims registradas                47
  con LOCATION                       24   (+1 al cerrar RE-10 con esta ficha)
  SIN LOCATION                      23
  sigue siendo casi la mitad del registro
  CORRECCIÓN: dije antes que 15 de las 25 citaban un finding que ya declara sus
  localizaciones.  Es FALSO, y lo medí al construir la herramienta: son 0 las que
  declaran un bloque LOCATION.  Los findings *mencionan* fichero:línea en línea, que es
  otra cosa.  Lo corregido es
      FETCHABLE   0   el finding citado DECLARA un bloque LOCATION
      ADVERTISED  11  el finding sólo menciona fichero:línea: quedan como candidatos
      MANUAL      14  nada resoluble sin leer el corpus
  Que mi cifra fuera 15 y la real 0 es exactamente el fallo que la herramienta existe
  para evitar: di una estimación como si fuera una medición
Y NO ES UN ARTEFACTO DEL PARSER
  comprobado a mano sobre RE-10, RE-17 y RE-19: las tres citan SOURCE con el nombre del
  finding, y ninguna trae una sola línea de código.  El ejemplo es el que más duele:
  RE-10  "Geometría de page table de Polaris12, cerrada numéricamente"
        TYPE DERIVATION · STATE PROVEN · SOURCE gfx8vmgeom + 024 §2
        PRODUCER 08-ARQUITECTURA/tools/gfx8vmgeom · UNIT entradas, bytes, bits
        VERSION GFX8, cruzado 7.1.3 <-> 7.2.8
        y NO hay ni un fichero:línea
  Esa es la claim que sostiene block_size, num_level, root_level, el ancho del índice de
  PTE y el tamaño de la page table.  Es la más citada del registro y la que zanjó C-003 y
  C-009.  Y es inauditable por su propia definición
POR QUÉ ES IMPORTANTE, y no es un detalle de forma
  · C-009 se resolvió porque una TERCERA sesión encontró el log del host.  Si la cadena de
    RE-10 no tiene LOCATION escrita, quien la lea tiene que reconstruirla desde cero, y
    esa reconstrucción es exactamente lo que produjo tres cifras distintas para el mismo
    número
  · una claim sin LOCATION no se puede re-verificar cuando el corpus se mueve, que es lo
    que pasa varias veces al día
  · y el proyecto tiene una regla de nueve campos, y el 51 % del registro no la cumple
    en el que decide si algo es comprobable
LO QUE ESTO ES Y LO QUE NO ES
  no es que las 24 sean falsas.  Varias se sostienen, y varias están corroboradas
  es que NO SON AUDITABLES.  La diferencia es la que separa una afirmación de una
  afirmación comprobable, y es la diferencia que este registro exists para documentar
CÓMO SE CIERRA, y es trabajo manual por naturaleza
  para cada una, leer la evidencia que ya cita su SOURCE y escribir el fichero:línea.  Eso
  NO se automatiza, porque requiere decidir qué línea es LA línea
  `claim.py` puede encontrar el fichero del SOURCE y los símbolos citados, que es
  trabajo mecánico.  No puede elegir la línea correcta, y no debe: esa elección es
  conocimiento
LIMITE DE LA MEDICIÓN  el parser busca una línea `LOCATION` o una celda con ese nombre.
  Una claim queExprese su ubicación de otra forma se cuenta como no auditable.  Comprobé
  RE-05, que sí la tiene y se cuenta bien, y RE-10/17/19, que no la tienen.  Con eso, y
  con que el patrón es el que usa la mayoría del registro, el número es de fiar; no es un
  census exacto de la calidad de cada claim
```

---

## Host (verificado por lectura directa, 2026-10-01)

| ID | Afirmación | TYPE | STATE | SOURCE | LOCATION |
|---|---|---|---|---|---|
| RE-20 | RX550 presente como `1002:699f` rev c7 en `0000:01:00.0` | FACT | PROVEN | `lspci -nn -d 1002:699f` | — |
| RE-21 | Es `card1`/`renderD129`, no `card2` | FACT | PROVEN | `readlink /sys/class/drm/*/device` | `DRIVER=amdgpu` |
| RE-22 | VRAM 2 GiB, visible 256 MiB → `vram_full_visible=FALSE` | OBSERVATION | PROVEN | sysfs | `card1/device/mem_info_*` |
| RE-23 | Los 4 parámetros de módulo de vm están en `-1` | OBSERVATION | PROVEN | sysfs | `/sys/module/amdgpu/parameters/` |
| RE-24 | GPU intacta: ni `nhwa` ni `rx550*` cargados | OBSERVATION | PROVEN | `/proc/modules`, `lsmod` | — |
| RE-25 | El host es Nobara 44 / kernel 7.1.3-fc44 / Mesa 26.2.3 | FACT | PROVEN | `os-release`, `uname`, `glxinfo` | — |
| RE-26 | README.md:13-16 describe el host del 2026-09-25 | DOCUMENTATION | `STALE` | contraste con RE-21/RE-25 | corregido hoy |

## Línea B · BC3 (verificado salvo lo marcado)

| ID | Afirmación | TYPE | STATE | SOURCE |
|---|---|---|---|---|
| RE-30 | Fase 1 compresor `COMPLETE`, 26/26 checks, test con capacidad de fallo demostrada (`make check-ramp-discriminates` rechaza el mutante) | TEST | PROVEN | `PROYECTO_STATUS.md`, commit `7ed1eca` |
| RE-31 | Fase 2 descompresor `COMPLETE`: 0 de 64 bloques, 0 de 4096 bytes, 3 corridas en la RX550 | MEASUREMENT | PROVEN (texto) / `NOT_RECHECKED` (hoy) | commit `7ed1eca` 2026-09-29 01:17 |
| RE-32 | 3 imágenes PNG dan `0 de 16384` bytes discrepantes GPU vs referencia | MEASUREMENT | PROVEN en disco, **no versionado** | `04-IMPLEMENTACION/work/*.decompress.log` |
| RE-33 | El speedup AVX2 frente a C es `NOT_CONCLUYENTE` — el rango intra-implementación es del orden de la diferencia | TEST | `NOT_CONCLUYENTE` | `CIERRE_PROYECTO.md` |
| RE-34 | AD-12: interpolación de la rampa alfa por el sampler del hardware | HYPOTHESIS | `NOT_DETERMINED` | frontera F2 |
| RE-35 | `GFX_HWIP` de este shader en particular | — | `NOT_DETERMINED` | N8 |

**RE-31 vs RE-32**: los `.log` de RE-32 son la mejor evidencia disponible y sin
embargo están **ignorados por git** (`.gitignore:78`, `04-IMPLEMENTACION/work/`). El
texto de `7ed1eca` dice `[ OK ] 4005 de 4096 bytes no nulos`, cifra que **no** aparece
en ningún log persistido. Queda `NOT_RECHECKED`, no `PROVEN`.

## EV-14 · El VBIOS de esta tarjeta existe, es válido y se ha decodificado

```
TYPE    OBSERVATION + DERIVATION
STATE   PROVEN
```

Con acceso root al debugfs se lee `amdgpu_vbios`: 58880 bytes,
sha256 `2b59f50859ec8003248eee9914a8d46967fd8c12e93d098f346ba54b33c53519`.

`file(1)` lo identifica como ROM de un PCI AMD/ATI `device=0x699f`, que es
Polaris12.

Los cuatro controles que ejecuta `amdgpu_atom_parse()` (atom.c:1546-1580)
pasan, y no son controles inventados:

| comprobación | valor | offset |
|---|---|---|
| `ATOM_BIOS_MAGIC` | `0xAA55` | `atom.h:32` |
| magic ATI | `" 761295520"` | `atom.h:33-34` |
| magic `ATOM` en base+4 | `"ATOM"` | `atom.h:37-38` |
| tamaño declarado vs real | 115×512 = 58880 | `file(1)` |

El **endianness queda PROVEN y no supuesto**: los bytes 0-1 son `55 aa`; en
big-endian la firma no casaría y `atom.c:1558` rechazaría el ROM.

Geometría: ROM table `0x021c`, command table `0x974c`, master data table
`0x97f2` con `usStructureSize=74` = 4+2·35, que encaja con
`ATOM_MASTER_LIST_OF_DATA_TABLES`. Corroborado por búsqueda independiente
sobre el ROM entero: **un único** candidato, el mismo offset.

Cierra el bloqueo `BLOCKED_BY_AUTHORIZATION` que pesaba sobre el VBIOS.
`LAST_VERIFIED: 2026-10-02 - revkit/atomrom.py autotest + rom`.

## EV-15 · La unidad de los clocks del VBIOS es 1/100 de MHz

```
TYPE    MEASUREMENT
STATE   CORROBORATED
```

El header dice "In 10Khz unit". Me equivoqué **dos veces**: `valor/10/1000`
daba 2,1 MHz para el reloj de motor, y `valor/100/1000` daba 0,2 MHz. Los
dos números tienen decimales y aspecto de frecuencia, y ninguno lo es.

Lo que lo resolvió fue contrastar contra el hardware:

| campo VBIOS | bruto | MHz | kernel ahora |
|---|---|---|---|
| `ulDefaultEngineClock` | 21400 | 214 | `PSTATE_SCLK` 214 MHz |
| `ulDefaultMemoryClock` | 30000 | 300 | `MCLK` 300 MHz |

Dos coincidencias exactas en dos campos distintos. El contraste está
**dentro** de `atomrom.py`: rc=5 si no cuadra, rc=4 si no puede comprobarlo.

`LAST_VERIFIED: 2026-10-02 - revkit/atomrom.py firmware, cn8 caso negativo`.

## EV-16 · La VRAM es 2 GiB de GDDR5 Samsung `H5GC8H24AJR`

```
TYPE    OBSERVATION
STATE   PROVEN
```

`VRAM_Info` en `0xa30a`, rev 2.2, que corresponde a
`_ATOM_VRAM_INFO_HEADER_V2_2` (atombios.h:8027). El propio dato dice
`ucVramModuleVer = 8`, luego los módulos son `ATOM_VRAM_MODULE_V8`.

`usMemorySize = 2048` MB, que concuerda por tres vías: el VBIOS, el kernel
(`amdgpu_vram_mm total: 2048MiB`) y `size: 2147483648` bytes.

`strMemPNString = "H5GC8H24AJR"`: part number real de GDDR5 Samsung. Es el
único punto donde el VBIOS dice **qué** memoria hay, no solo cuánta; el
driver solo ve "2 GiB".

**No se afirma** `ucMemoryType = 0x50` ni `ucChannelWidth = 5`: sus
comentarios no casan con el valor (el nibble bajo "must not be used for
now"; los anchos documentados son 0/1/2). Se imprimen sin traducir.

`LAST_VERIFIED: 2026-10-02 - revkit/atomrom.py vram, cn8 caso negativo`.

## EV-17 · Hay un `WAIT_REG_MEM` ejecutado por el hardware

```
TYPE    OBSERVATION
STATE   OBSERVED
```

En el anillo GFX capturado hay 8 `PACKET3_WAIT_REG_MEM` (opcode 0x3C). No
es una reconstrucción del código: es un paquete real, y su payload se
contrasta campo a campo contra `gfx_v8_0_emit_hdp_flush`
(gfx_v8_0.c:6047-6056) y los headers del ASIC:

```
payload  0x143, 0x1537, 0x1538, 0x1, 0x1, 0x20
         ^     ^REQ     ^DONE   ^mask  ^mask  ^poll
```

`mmGPU_HDP_FLUSH_REQ = 0x1537` y `_DONE = 0x1538` en
`asic_reg/bif/bif_4_1_d.h`, la generación de Polaris12;
`GPU_HDP_FLUSH_DONE__CP0_MASK = 0x1` en `bif_4_1_sh_mask.h`, que es
exactamente el `ref_and_mask` que `gfx_v8_0_get_hdp_flush_mask()` produce
para un anillo GFX (gfx_v8_0.c:5243-5246).

`0x143 = FUNCTION(3) | OPERATION(1) << 6 | ENGINE(1) << 8`.

**DOS RETIRADAS EN ESTA FILA, las dos propias, y las dos del mismo tipo**

```
RETIRADA 1  "GFX8 no emite nunca always"
  lo escribi en EV-17 y lo repeti en CONTRADICTIONS C-013 como conclusion
  vigente. Es FALSO. gfx_v8_0.c:6201 emite
      WAIT_REG_MEM_FUNCTION(0) | /* always */
  dentro de gfx_v8_0_ring_emit_vm_flush (gfx_v8_0.c:6191), y el comentario
  del propio driver dice para que: "wait for the invalidate to complete"
  Si se emite. Lo que sigue en pie de C-013 es lo otro: `always` es el
  valor 0 y es codificable. Lo que no se sostiene es que este driver no lo
  emita nunca, y esa era la unica afirmacion que sobrevivia de la retractada

RETIRADA 2  "WAIT_REG_MEM_OPERATION no esta definido para GFX8" (NOT_IN_CORPUS)
  lo marque NOT_IN_CORPUS basandome en que `gfx_8_1_pkt.h` no existe. Es
  FALSO. Hay CUATRO definiciones en el corpus, y la que le toca a GFX8 es
  `vid.h:180`, que gfx_v8_0.c incluye en su linea 35:
      amdgpu/vid.h:180  #define WAIT_REG_MEM_OPERATION(x)  ((x) << 6)
  Su comentario da los dos valores, 0 wait_reg_mem y 1 wr_wait_wr_reg, y
  coinciden con los que usa el driver ("wait" y "write, wait, write")
  ademas `soc15d.h:191`, `cikd.h:307` y `nvd.h:180` dicen lo mismo. Solo
  `gfx_v12_1_pkt.h:119` difiere, con mascara de 2 bits, y es de otro ASIC
  por donde entro el error: mire el unico fichero que ya sabia que no
  existia, en vez de hacer el grep sobre el corpus entero

POR QUE PASO, Y ES LO IMPORTANTE
  las dos son la misma regla incumplida, y es la REGLA CRITICA DE LECTURA
  COMPLETA del propio AGENTS.md: "Una lectura parcial jamas puede sustentar
  una ausencia"
  1. para afirmar que no lo emitia habia que hacer
       grep -n WAIT_REG_MEM_FUNCTION gfx_v8_0.c
     que da tres lineas, una de ellas el `always`. No lo hice
  2. para afirmar que no estaba definido habia que hacer
       grep -rn "define.*WAIT_REG_MEM_OPERATION" sobre TODO el corpus
     que da cinco ficheros. Mire uno solo
  lo grave del caso 2 es que el NOT_IN_CORPUS iba DENTRO de una fila de
  evidencia, con su STATE puesto. Un NOT_IN_CORPUS sin grep de corpus
  completo es una ausencia afirmada con la seguridad de una medicion
```

Lo que **mantiene** esta fila: los siete valores de `sid.h:398-406` con
`always` = 0, y que el anillo capturado contenga solo la variante de HDP
flush (`0x143`), que es la unica que se ha observado en hardware.

`LAST_VERIFIED: 2026-10-02 - revkit/WAIT-REG-MEM-REAL.md, pm4dec.py`.
Retiradas el 2026-10-02, misma fecha, tras `grep` de corpus entero.

`LAST_VERIFIED: 2026-10-02 - revkit/WAIT-REG-MEM-REAL.md, pm4dec.py`.

## EV-25 · El `WAIT_REG_MEM` que espera al invalidate tiene control dword CERO

```
TYPE    OBSERVATION + DERIVATION
STATE   PROVEN_DERIVED
```

`gfx_v8_0_ring_emit_vm_flush` (gfx_v8_0.c:6191-6207) emite **una segunda
forma** de `WAIT_REG_MEM`, distinta de la del HDP flush:

```c
amdgpu_gmc_emit_flush_gpu_tlb(ring, vmid, pd_addr);   /* el invalidate */
/* wait for the invalidate to complete */
amdgpu_ring_write(ring, PACKET3(PACKET3_WAIT_REG_MEM, 5));
amdgpu_ring_write(ring, (WAIT_REG_MEM_OPERATION(0) | /* wait */
                 WAIT_REG_MEM_FUNCTION(0) |  /* always */
                 WAIT_REG_MEM_ENGINE(0)));   /* me */
amdgpu_ring_write(ring, mmVM_INVALIDATE_REQUEST);
amdgpu_ring_write(ring, 0);       /* ref  */
amdgpu_ring_write(ring, 0);       /* mask */
amdgpu_ring_write(ring, 0x20);    /* poll interval */
```

| | HDP flush | vm flush |
|---|---|---|
| `OPERATION` | 1 `wr_wait_wr_reg` | 0 `wait_reg_mem` |
| `FUNCTION` | 3 `==` | **0 `always`** |
| `ENGINE` | 1 `pfp` | 0 `me` |
| control dword | `0x143` | **`0x000`** |
| registro vigilado | `mmGPU_HDP_FLUSH_DONE` | `mmVM_INVALIDATE_REQUEST` |
| ref / mask | `ref_and_mask` | `0` / `0` |
| sitio | gfx_v8_0.c:6046 | gfx_v8_0.c:6199 |

**El dword de control del vm flush es cero.** Con `FUNCTION(0)`, `OPERATION(0)`
y `ENGINE(0)`, no queda ni un bit puesto: la forma "esperar a que pase algo" en
estado inicial. No es un dato raro, es la unica manera de que un
`wait_reg_mem` espere algo sin comparar contra nada.

Eso responde a la pregunta que AGENTS.md llevaba abierta como
`hardware trigger de always: NO_DETERMINED`. No es un trigger: es una
**espera**, y espera a la conclusion del invalidate de TLB. El hardware no
dispara nada; el driver deja un paquete que no retorna hasta que el registro
`VM_INVALIDATE_REQUEST` ha cambiado.

**Conexion con finding 106** (otra sesion, `daec702`): aquel concluyo que
`VM_INVALIDATE_REQUEST` no tiene campo `FUNCTION`. Es correcto y queda
corroborado aqui con la generacion que le toca a GFX8: `gfx_v8_0.c` incluye
`gmc/gmc_8_2_d.h` y `gmc_8_2_sh_mask.h`, y en `gmc_8_2` los unicos campos de
`VM_INVALIDATE_REQUEST` son `INVALIDATE_DOMAIN_0..15`, uno por bit, shifts 0 a
15. **Ningun campo por encima del bit 15, en las cinco generaciones de GMC
(6_0, 7_0, 7_1, 8_1, 8_2), todas con exactamente 16 dominios.**

Por tanto hay **dos `FUNCTION` distintos** y no se contradicen:

| | `WAIT_REG_MEM_FUNCTION` | `INVALIDATE_REQUEST__FUNCTION` |
|---|---|---|
| donde | `sid.h:398` (PM4, paquete) | registros GMC (MMIO) |
| existe | si, 7 valores | **no** |
| `always` | valor 0 | no aplica |

El proyecto los tuvo confundidos durante semanas. La distincion es de **tipo**,
no de ASIC: una es un campo de un opcode de PM4, la otra sería un registro.

**Lo que sigue abierto, y es F12b con nombre propio**: el `poll interval`
`0x20` sigue fuera del `count` declarado (5 vs 6, EV-19), y aqui es donde mas
importa, porque es la granularidad con la que el hardware sondea si el
invalidate ha terminado. Si el hardware no lee ese dword de mas, la espera no
sondea: se queda esperando hasta el siguiente paquete. Es `NOT_DETERMINED`, y
es la razon por la que esa frontera tiene valor de hardware y no de
documentacion.

`LAST_VERIFIED: 2026-10-02 - gfx_v8_0.c:6191-6207, vid.h:180, gmc_8_2_sh_mask.h`.

## EV-26 · El productor del invalidate, y el mapeo VMID → bit

```
TYPE    OBSERVATION + DERIVATION
STATE   PROVEN_DERIVED
```

`gmc_v8_0_emit_flush_gpu_tlb` (gmc_v8_0.c:668-683) es el emisor, y son cinco
líneas. Se llega por indirección, no por nombre: la macro
`amdgpu_gmc_emit_flush_gpu_tlb` (amdgpu_gmc.h:371) es un puntero a función, y
la implementación de GFX8 se asigna en `gmc_v8_0.c:1736`.

```c
if (vmid < 8)
        reg = mmVM_CONTEXT0_PAGE_TABLE_BASE_ADDR + vmid;
else
        reg = mmVM_CONTEXT8_PAGE_TABLE_BASE_ADDR + vmid - 8;
amdgpu_ring_emit_wreg(ring, reg, pd_addr >> 12);

/* bits 0-15 are the VM contexts0-15 */
amdgpu_ring_emit_wreg(ring, mmVM_INVALIDATE_REQUEST, 1 << vmid);
```

**El mapeo VMID → bit del invalidate, PROVEN.** El comentario del driver
afirma "bits 0-15 are the VM contexts0-15" y escribe `1 << vmid`. Eso solo es
correcto si `INVALIDATE_DOMAIN_i` está en el bit `i`. Comprobado en el header:

| generación | `SHIFT[i] == i` en los 16 |
|---|---|
| `gmc_6_0` · `gmc_7_0` · `gmc_7_1` · `gmc_8_1` · `gmc_8_2` | sí, en las cinco |

Cinco generaciones con el mismo invariante. `1 << vmid` no es una coincidencia
que funciona: es el contrato del campo.

Esto responde **por qué** el invalidate no necesita campo `FUNCTION` (finding
106): va dirigido por bit, no por selector de modo. Un `FUNCTION` habría sobrado.

Direcciones (`gmc_8_2_d.h`, la generación que incluye `gfx_v8_0.c:41-42`):

| registro | offset |
|---|---|
| `mmVM_CONTEXT8_PAGE_TABLE_BASE_ADDR` | `0x50e` |
| `mmVM_INVALIDATE_REQUEST` | `0x51e` |
| `mmVM_CONTEXT0_PAGE_TABLE_BASE_ADDR` | `0x54f` |

Los bloques de contextos 0 y 8 están separados (`0x54f..0x556` para VMID 0-7,
`0x50e..0x515` para 8-15). El `if (vmid < 8)` existe por eso, y no por el
registro del invalidate, que es único.

Con `vmid = 7` y `pd_addr = 0x1_0025_8000` (una de las ocho direcciones
observadas en el anillo, EV-21), el bloque completo es de 14 dwords:

| dword | valor | qué es |
|---|---|---|
| 2 | `0x556` | `PTBA[7]` |
| 3 | `0x100258` | `pd_addr >> 12` |
| 6 | `0x51e` | `VM_INVALIDATE_REQUEST` |
| 7 | `0x00000080` | `1 << 7` |
| 9 | `0x00000000` | control del WAIT_REG_MEM: **dword cero** |

Detalle completo, con la cadena de includes y los bytes del anillo, en
`revkit/VM-FLUSH-GFX8.md`.

`LAST_VERIFIED: 2026-10-02 - gmc_v8_0.c:668-683, gmc_8_2_sh_mask.h, cn7`.

## EV-27 · "el hardware lee exactamente count" queda REFUTADO por el anillo

```
TYPE    MEASUREMENT
STATE   REFUTED (la hipotesis) · PROVEN (el recuento)
```

Si el hardware se detuviera tras `count` payload, el séptimo dword del bloque
`WAIT_REG_MEM` (`0x00000020`, el poll interval) sería una cabecera tipo 0 con
`count = 32` — el count de tipo 0 está en los bits **bajos**, no en `[29:16]` —
y el siguiente paquete empezaría en el dword 47. El dword 47 es `0x00001040`:
tipo 0 otra vez, con count 4160. A partir de ahí el anillo no contiene ningún
paquete más.

Recorriendo el anillo entero de las dos formas:

| lectura | paquetes tipo 2/3 válidos | cabeceras tipo 0 espurias |
|---|---|---|
| `count` exactos (5) | **3** | **2** |
| los 6 payload | **11** | **0** |

Once paquetes válidos frente a tres, y **cero** dwords espurios en 2051. La
lectura de seis es la única que deja el anillo con sentido.

Un driver propio que asumiera "exactamente `count`" perdería el anillo en el
primer `WAIT_REG_MEM`, ocho veces por bloque.

**Lo que queda abierto, y es corto**: si el count es `payload - 1` (lee 6
siempre) o si el hardware trata los dwords tipo 0 como no-op y los salta. Con
esta captura **no se distinguen**: los dos dan 11 paquetes y 0 espurias.

Y ahí está el nudo, porque si la respuesta fuera "lee 6 siempre", el emisor de
`vm_flush` —que escribe 5 y declara 5— **se comería un dword del paquete
siguiente**. O el count significa otra cosa, o uno de los dos emisores tiene un
defecto. Los tres son compatibles con lo observado.

`LAST_VERIFIED: 2026-10-02 - revkit/cn7.py, bytes crudos de
capturas/amdgpu_ring_gfx.txt dwords 8..14`.

## EV-18 · El anillo GFX tiene 2048 dwords y estaba vacío

```
TYPE    MEASUREMENT
STATE   OBSERVED
```

El anillo capturado son 2048 dwords (8192 B, `mask=0x07FF`), 256 por
bloque, alineados a `3+256k`, lo que encaja con `.align_mask = 0xff` de
`gfx_v8_0_ring_funcs_gfx` (gfx_v8_0.c:6872).

Contenido: 8 repeticiones de `WAIT_REG_MEM`, `CONTEXT_CONTROL`,
`INDIRECT_BUFFER`, `WRITE_DATA`, `SWITCH_BUFFER`, `EVENT_WRITE_EOP` y NOP
de relleno.

`RPTR == WPTR == sw_wptr == 0x200`, o sea que **el driver no tenía nada
pendiente**.

**No es lectura de MMIO**: los tres punteros son espejos en CPU
(`*ring->rptr_cpu_addr`, `*ring->wptr_cpu_addr`) o variables del driver;
`RREG32(mmCP_RB0_WPTR)` solo ocurre si `use_doorbell` es falso
(gfx_v8_0.c:6008, 6011-6019). Una versión anterior de este proyecto los
presentó como lectura de hardware y se retiró.

Lo que **sí** es dato del ASIC es el tamaño: 2048 dwords, mask `0x07FF`.

`LAST_VERIFIED: 2026-10-02 - revkit/pm4dec.py`.

## EV-19 · El driver declara un `count` menor de los dwords que escribe

```
TYPE    OBSERVATION
STATE   PROVEN_DERIVED
```

CUATRO paquetes distintos, en cuatro emisores distintos:

| paquete | `count` declarado | payload escritos |
|---|---|---|
| `WAIT_REG_MEM` (HDP flush) | 5 | **6** |
| `COND_EXEC` | 3 | 5 |
| `INDIRECT_BUFFER` | 2 | 3 |
| `WRITE_DATA` | 3 | 4 |

El último dword queda **fuera** del conteo declarado, y lo hace el código
fuente de forma consistente, no un error de decodificación.

**Matiz de 2026-10-02, y corrige la lectura plana de esta misma fila.** El
off-by-one **no es una propiedad del tipo de paquete, es del emisor.** El
driver tiene dos emisores de `WAIT_REG_MEM` y no coinciden:

| emisor | payload | `count` | ¿off-by-one? |
|---|---|---|---|
| `gfx_v8_0_emit_hdp_flush` (gfx_v8_0.c:6046) | **6** | 5 | sí |
| `gfx_v8_0_ring_emit_vm_flush` (gfx_v8_0.c:6199) | **5** | 5 | **no** |

El de HDP flush escribe `ref_and_mask` **dos veces** y por eso se pasa en uno.
El de vm flush no. Un driver propio que copie "la forma del paquete" sin mirar
el emisor se equivoca en uno de los dos.

Confirmado con los bytes crudos del anillo, no solo con la fuente: dwords 8..14
son **siete** dwords consecutivos con `count = 5` en la cabecera, y el séptimo
(`0x00000020`) es el poll interval, presente en el buffer y fuera del conteo.

Que el hardware lea 5 o 6 queda resuelto en EV-27: **no lee 5**, queda
refutado por el propio anillo. Lo que sigue abierto es si lee 6 siempre o
trata los tipo 0 como no-op.

Que el hardware lea `count` o `count + 1` en los **otros** tres paquetes sigue
`NOT_DETERMINED`. Lo que sí se sabe en todos los casos es que el valor **está
en el buffer, en el orden correcto**, y que `count` no lo cuenta.

`LAST_VERIFIED: 2026-10-02 - revkit/pm4dec.py, HALLAZGOS-2026-10-02.md §13`.

## EV-20 · La traducción VA→PA lleva la propia VA, con máscara de 40 bits

```
TYPE    DERIVATION
STATE   PROVEN_DERIVED
```

Cuatro líneas del corpus con sus valores:

| donde | qué hace | valor |
|---|---|---|
| `gmc_v8_0.c:1176` | `vram_base_offset` | `0` (GPU discreta, no APU) |
| `amdgpu_vm.c:1228` | `addr = vram_base + cursor.start` | |
| `amdgpu_gmc.c:173` | `value = addr & pte_addr_mask` | |
| `gmc_v8_0.c:1134` | `pte_addr_mask` | `0x000000FFFFFFF000` (40 bit PA) |

Con `vram_base = 0`, **la dirección que va en la PTE es la propia VA**, sin
desplazamiento. No hace falta conocer el contenido de la tabla para saber
qué operación se aplica.

La máscara quita los 12 bits bajos, que son el offset dentro de la página:
las VA observadas (`0x1_0025_8000`, `0x1_0027_8600`, …) **no** están
alineadas a 4 KiB. Eso no es un defecto: la PTE direcciona páginas, no
bytes.

**No se cierra**: qué página física apunta cada entrada, dónde está la
tabla, ni los flags de acceso. Es `NOT_AVAILABLE` por esta vía —
`amdgpu_vm_info` en 7.1.3 no vuelca entradas y `amdgpu_gart` no existe.

`LAST_VERIFIED: 2026-10-02 - revkit/pm4dec.py --direcciones, cn7`.

## EV-21 · Hay 8 VAs de GPU reales en el anillo, con FB en 4 GiB

```
TYPE    OBSERVATION
STATE   PROVEN
```

Los `INDIRECT_BUFFER` del anillo contienen direcciones de 64 bits que el
hardware usó: `0x1_0025_8000` … `0x1_0027_8600`, todas alineadas a 0x600.

Restando una base de 4 GiB, los offsets son 2,34–2,47 MiB y **caben en los
2 GiB** que reporta el kernel. El contraste discrimina: con base 0 las ocho
caen fuera y el tool da rc=5.

Anotación sin conciliar: el `vram_base_offset = 0` registrado para esta
ruta **no concuerda** con un FB en 4 GiB. Puede referirse a otra cosa o no
aplicar a la dirección que usan estos paquetes. Se deja la tensión
visible, no se concilia.

`INDIRECT_BUFFER` control: `vmid = 7`, `length_dw = 344` (1376 B). Con el
reparto de GFX8 (`gmc_v8_0.c:1162-1168`: 0 sistema, 1-7 graphics, 8-15
KFD), 7 es el último del bloque de gráficos, justo antes del de KFD.

`LAST_VERIFIED: 2026-10-02 - revkit/pm4dec.py --direcciones, cn7 negativo`.

## EV-22 · El anillo escribe en `mmHDP_DEBUG0`, que es un registro

```
TYPE    OBSERVATION
STATE   PROVEN
```

Ocho `PACKET3_WRITE_DATA`, todos con `dst_sel = 0`, que según `sid.h:379`
significa **registro**, no memoria; `WR_CONFIRM = 1`, `engine = 1` (PFP) y
dirección `0xBCC`.

`0xBCC = mmHDP_DEBUG0`, resuelto por coherencia entre generaciones del
bloque OSS: `oss_1_0`, `oss_2_0`, `oss_2_4`, `oss_3_0`, `oss_3_0_1` lo
definen igual.

El contraste importa: `0xBCC` también existe en DCE, GC y MMHUB, así que
un índice que devuelva "el primero que aparezca" da el ASIC equivocado. Lo
que demuestra el nombre correcto es que **varias versiones del mismo
bloque** dan el mismo offset.

`LAST_VERIFIED: 2026-10-02 - revkit/pm4dec.py --escribe`.

## EV-23 · GART 256 MiB, y la razón está en el propio código

```
TYPE    DERIVATION
STATE   PROVEN_DERIVED
```

`gmc_v8_0.c:588-608`, con Polaris12 listado por su nombre:

```c
case CHIP_POLARIS12: /* all engines support GPUVM */
default:
    adev->gmc.gart_size = 256ULL << 20;
```

El comentario da la causa: en Polaris10/11/12 y Vega10 todos los motores
soportan GPUVM, de modo que la GART no necesita ser grande para permappear
RAM del sistema. Los chips de 1024 MiB (Tonga, Fiji, Carrizo, Stoney) son
los que tienen UVD o VCE **sin** GPUVM.

Explica por qué el BAR es de 256 MB (`lspci`: `Memory at e0000000
[size=256M]`) mientras la VRAM es de 2 GiB: **GART y BAR son cosas
distintas**, y el BAR es solo la ventana de CPU sobre la VRAM.

`LAST_VERIFIED: 2026-10-02 - gmc_v8_0.c:588-608`.

## EV-24 · El corpus cubre el 89 % de los símbolos que el driver usa

```
TYPE    MEASUREMENT
STATE   PROVEN
```

`huerfanos.py` sobre 912 ficheros `.c` de las tres raíces:
**296 de 2608 símbolos usados carecen de definición local (11 %)**.

No es una lista de fallos del driver. La prueba: entre los 296 está
`amdgpu_bo_reserve`, que se usa 228 veces y está definido en
`amdgpu_bo.c` — fichero que **no está en el corpus**. El símbolo no está
huérfano; el fichero que lo define no está.

Para un símbolo concreto sí es un dato: su implementación no está
disponible aquí, luego su comportamiento no se deriva del corpus
(`NOT_IN_CORPUS`, no `NOT_FOUND`). Y sigue siendo **observable**: si la
función vuelca algo por debugfs, su salida se analiza aunque falte el
código. Eso es lo que se hizo con `amdgpu_sa_bo_dump_debug_info`, cuyo nodo
sí se leyó y se analizó con `ibpools.py`.

Dos casos concretos que aparecieron por esta vía:
`amdgpu_ring_patch_cond_exec` (se llama, no se define) y
`amdgpu_sa_bo_dump_debug_info` (ídem).

`LAST_VERIFIED: 2026-10-02 - revkit/huerfanos.py, cn8`.

## Herramientas (contrato y estado; detalle en TOOLS-STATUS.md)

| ID | Herramienta | STATE | Verificado |
|---|---|---|---|
| RE-40 | `pm4_count_census.py` | `VALIDATED` | rc=0, 68/22, distribución correcta |
| RE-41 | `pm4dw.c` | `VALIDATED` con invocación documentada | compila limpio; requiere `--struct <nombre de la variable>` y `--macro N=V` |
| RE-42 | `gfx8vmgeom` | `VALIDATED` | `make test`: 37/0, 12/12 negativos, cruce de versión |
| RE-43 | `semref` | **`INVALID`** | `ctags` disponible, Coccinelle perdida con `/tmp`; `refs`/`chain` salen rc=3 |
| RE-44 | `validate_rx550_final.py` | `VALIDATED` | rc=0, `writes_to_system=false` |
| RE-45 | `evidence_search.py` | `FUNCIONAL` sin test de fallo registrado | — |
| RE-46 | `frame_budget.py`, `count_vmflush_dw.py` | `TRACKED`, `PARTIAL` | superseded en parte por `pm4dw` |

### Herramientas de `revkit/` (2026-10-02, tras obtener acceso root al debugfs)

| ID | Herramienta | STATE | Verificado |
|---|---|---|---|
| RK-01 | `captura.py` | `VALIDATED` | 19 nodos en una sesión de sudo, 0,3 s; rc=4 si falla la autenticación, rc=3 si el plan se contradice |
| RK-02 | `mmo.py` | `TOOL_PARTIAL` | lista blanca validada contra el modo real de cada nodo; no se capturan `amdgpu_regs*` (ver EV-19) |
| RK-03 | `integro.py` | `VALIDATED` | autotest con 7 controles; mutation testing: M1, M2 (no detectada al principio) y sniff de capturas |
| RK-04 | `atomrom.py` | `VALIDATED` | autotest sobre ROM **sintético**, sin usar el VBIOS real; controles de unidad y de VRAM con caso negativo |
| RK-05 | `pm4dec.py` | `VALIDATED` | 74 opcodes extraídos de `sid.h` en runtime; `cn7.py` con 19 controles, 2 de ellos negativos |
| RK-06 | `dires.py` | `VALIDATED` | 587 164 direcciones, 30 ASIC; autocomprobación en cada ejecución (rc=3 si no encuentra 0x1537/0x1538) |
| RK-07 | `ibpools.py` | `VALIDATED` | autocomprobación: avisa si no interpreta todas las líneas, si hay >1 IB en uso por pool, o si un rango no cuadra con `size` |
| RK-08 | `huerfanos.py` | `FUNCIONAL`, rc=1 por diseño | 296/2608 símbolos sin definición local; rc=2 si no se ha recorrido nada |
| RK-09 | `cn7.py`, `cn8.py` | `VALIDATED` | 19 + 12 controles; los negativos usan mutación real, no `if False` cosmético |
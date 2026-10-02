# EVIDENCE-MATRIX

<!-- GENERADO POR tools/artifacts.py. NO EDITAR A MANO: la siguiente ejecucion lo sobrescribe. -->

Una fila por finding. `clases` son las tipificaciones mas frecuentes,
no un veredicto: una tabla de indices, no de afirmaciones.

| # | titulo | clases tipificadas | GPU | reescribe | citas corpus |
|---|---|---|---|---|---|
| 001 | amdgpu-location | SYSTEM_CHANGE x1, D68004925455E20A24C2B87 x1 | ? | - | 0 |
| 001 | amdgpu-overview | HOST_SCOPE x2, D68004925455E20A24C2B87 x2, PLAUSIBLE x2, OBSERVED x2 | ? | - | 1 |
| 002 | module-sections | PROGBITS x2, RELA x1, SYMTAB x1, STRTAB x1 | ? | - | 0 |
| 003 | exported-symbols | SYSTEM_CHANGE x1, DRM_IOCTL_AMDGPU_CS x1, DRM_IOCTL_AMDGPU_CS_WAIT_QUERY x1, PLAUSIBLE x1 | ? | - | 0 |
| 005 | cs-ioctl-analysis | NOT_DETERMINED x2, IOWR x1, AMDGPU_CHUNK_ID_IB x1, AMDGPU_CHUNK_ID_FENCE x1 | ? | - | 2 |
| 006 | lsdma-packets | DISPATCH_DIRECT x3, PACKET3_SET_SH_REG x2, EVENT_WRITE_EOS x2, ATOMIC x2 | ? | - | 6 |
| 007 | gfx8-pm4-format | PACKET3_DISPATCH_DIRECT x4, PACKET3_COMPUTE x2, OBSERVED x2, NOT_DETERMINED x2 | ? | - | 3 |
| 008 | firmware-blob | NOT_DETERMINED x3, GFX_HWIP x2, SYSTEM_CHANGE x1, PLAUSIBLE x1 | modificada | - | 0 |
| 009 | blockers-status | NOT_DETERMINED x6, PGM_RSRC1 x5, GFX_HWIP x4, BULKY x2 | ? | - | 8 |
| 010 | integration-validation | OBSERVED x4, PACKAGE_ABSENT x2, NOT_AVAILABLE x2, FIXED x2 | ? | - | 8 |
| 010 | pgm-rsrc1-decoded | NOT_DETERMINED x4, TG_PER_CU x4, COMPUTE_PGM_RSRC1 x3, BULKY x3 | ? | - | 8 |
| 011 | compute-submit-path | DISPATCH_DIRECT x4, PACKET3_DISPATCH_DIRECT x2, INDIRECT_BUFFER x2, NOT_DETERMINED x2 | ? | - | 11 |
| 012 | edc-gpr-workaround-carrizo | DISPATCH_DIRECT x9, SUPPORTED x8, GB_EDC_MODE x4, NOT_DETERMINED x3 | modificada | - | 9 |
| 013 | real-submit-path-polaris12 | NOT_DETERMINED x5, INDIRECT_BUFFER x3, DISPATCH_DIRECT x3, RUNTIME_EXECUTION x2 | modificada | - | 19 |
| 014 | mesa-bc3-cpu-decoder-verification | CONFIRMADO x1 | ? | - | 1 |
| 015 | llvmpipe-discriminating-pairs | NOT_DETERMINED x11, NEAREST x9, RUNTIME_EXECUTION x9, EVIDENCE x4 | ? | - | 14 |
| 016 | q5-static-preregistration | PROVEN x7, RUNTIME_EXECUTION x3, LAYOUT_S3TC x2, NOT_DETERMINED x2 | ? | - | 10 |
| 017 | vm-invalidate-gfx8-function-always | PROVEN x6, NOT_DETERMINED x6, REFUTED x3, WAIT_REG_MEM x3 | ? | - | 13 |
| 018 | execution-order-invalidacion-gfx8 | WAIT_REG_MEM x6, NOT_IMPLEMENTABLE x6, NOT_DETERMINED x6, RESPONSE x4 | ? | - | 11 |
| 019 | atc-l2-invalidation-gfx8 | INVALIDATE_ALL x7, PROVEN x4, VM_INVALIDATE_REQUEST x3, DISABLE_INVALIDATE_BY_ADDRESS_RANGE x3 | ? | - | 8 |
| 020 | vmflush-dword-budget-gfx8 | PROVEN x5, NOT_DETERMINED x4, KIQ x2, WAIT_REG_MEM x2 | INTACTA | - | 1 |
| 021 | frame-budget-gfx8-peor-caso | COND_EXEC x5, NOT_DETERMINED x4, PROVEN x3, DE_META x2 | INTACTA | - | 7 |
| 021 | write-lock-scoped-subdir-does-not-block | NEGATIVE_RESULT x3, REFUTED x3, NO_COLLISION_OBSERVED x2, PROVEN x2 | ? | - | 0 |
| 022 | cond-exec-inerte-en-gfx8 | COND_EXEC x12, PROVEN x9, NOT_DETERMINED x7, PROVEN_ABSENT x4 | INTACTA | - | 20 |
| 023 | pm4-count-convencion-medida | NOT_DETERMINED x8, COND_EXEC x4, PACKET3 x4, PROVEN x4 | INTACTA | - | 21 |
| 023 | pte-productor-sdma-gfx8 | SDMA_OP_GEN_PTEPDE x4, PROVEN x4, PAGE_TABLE_DEPTH x2, GEN_PTEPDE x1 | INTACTA | - | 25 |
| 024 | page-table-geometria-gfx8 | PROVEN x10, PAGE_TABLE_DEPTH x5, PAGE_TABLE_BLOCK_SIZE x5, PROVEN_DERIVED x5 | INTACTA | - | 8 |
| 024 | pm4dw-herramienta-conteo-emision | CONFLICT x2, STRUCT_NOT_FOUND x2, INCOMPLETE x1, PFP_SYNC_ME x1 | INTACTA | - | 3 |
| 025 | gart-invalidate-con-orden-cpu | PROVEN x13, NOT_DETERMINED x4, PROVEN_DERIVED x3, PAGE_TABLE_BASE_ADDR x2 | INTACTA | - | 23 |
| 025 | vm-flush-path-gfx8-63dw | ABSENT x4, PROVEN x3, NOT_DETERMINED x2, NEGATIVE_RESULT x1 | INTACTA | - | 9 |
| 026 | frame-completo-gfx8-121dw | NOT_DETERMINED x3, PROVEN x2, LIMITATION x1, DEFECT x1 | INTACTA | - | 6 |
| 026 | pte-encoding-gfx8 | PROVEN x12, NOT_DETERMINED x5, PROVEN_DERIVED x3, AMDGPU_PTE_TMZ x3 | INTACTA | - | 11 |
| 027 | ptba-produccion-gfx8 | PROVEN x10, BUG_ON x8, PROVEN_DERIVED x4, CHIP_POLARIS12 x2 | INTACTA | - | 15 |
| 027 | write-multiple-resuelto | NOT_FOUND x3, NOT_EXPANDED x1, CORROBORATED x1, PROVEN x1 | INTACTA | - | 0 |
| 028 | emit-frame-size-justificado | NO_HISTORICAL_INHERITANCE x3, MODEL_CHOICE x2, HDP_INVL x2, SURFACE_SYNC x2 | INTACTA | - | 1 |
| 028 | fence-completion-orden-d | PROVEN x11, DATA_SEL x6, PROVEN_DERIVED x5, HYPOTHESIS x5 | INTACTA | - | 7 |
| 029 | orden-validacion-fence-no-ring | PROVEN x4, NOT_DETERMINED x3, EVENT_WRITE_EOP x2, CACHE_FLUSH_AND_INV_TS_EVENT x2 | INTACTA | - | 7 |
| 029 | release-mem-y-eop-exec-muerto | RELEASE_MEM x13, PROVEN x13, EOP_EXEC x8, PROVEN_ABSENT x6 | INTACTA | - | 15 |
| 030 | page-walker-gfx8-2-niveles | PAGE_TABLE_BLOCK_SIZE x4, PROVEN_DERIVED x2, PROVEN x1, NOT_DETERMINED x1 | INTACTA | 019 | 7 |
| 030 | writeback-buffer-wb-slots | PROVEN x12, NOT_DETERMINED x2, PROVEN_ABSENT x2, PROVEN_DERIVED x2 | INTACTA | - | 9 |
| 031 | aridad-no-entregada | NEGATIVE_RESULT x2 | INTACTA | - | 0 |
| 031 | rptr-wptr-tres-dominios | PROVEN x19, NOT_DETERMINED x8, RREG32 x5, AMDGPU_PL_DOORBELL x5 | INTACTA | - | 11 |
| 032 | fence-lectura-coherente-por-pin | PROVEN x12, NOT_DETERMINED x8, DERIVATION x3, BLOCKED x2 | INTACTA | - | 11 |
| 032 | pte-invalido-no-existe | NOT_DETERMINED x4, AMDGPU_VM_NORETRY_FLAGS x3, VALID x2, FAULT_STOP_NEVER x1 | INTACTA | - | 8 |
| 033 | mmu-vm-no-publicado | NOT_PUBLISHED x7, NOT_DETERMINED x4, CORPUS_COMPLETENESS_CHECK x1, READ_SCOPE_GATE x1 | INTACTA | - | 0 |
| 033 | pm4-spec-gfx8-no-existe-y-el-encuadre | NOT_DETERMINED x10, PROVEN x10, SECONDARY_CORROBORATION x7, RELEASE_MEM x5 | INTACTA | - | 17 |
| 033 | protections-opaco-en-el-camino-gpuvm | PROTECTIONS x7, VMID x2, HYPOTHESIS x2, VM_CONTEXT1_PROTECTION_FAULT_STATUS x1 | INTACTA | - | 6 |
| 034 | corpus-autoconsistente-layouts-pm4 | PROVEN x13, RELEASE_MEM x6, MAP_QUEUES x6, EOP_TC_MD_ACTION_EN x6 | INTACTA | - | 9 |
| 035 | block-size-tres-claims-y-un-log | PROVEN x6, REFUTED x5, PAGE_TABLE_BLOCK_SIZE x3, NOT_DETERMINED x2 | INTACTA | - | 17 |
| 035 | correccion-ptepde-es-polaris12 | PROVEN x8, SDMA0_HWIP x4, SDMA_OP_PTEPDE x3, SDMA_OP_GEN_PTEPDE x2 | INTACTA | 043 023 | 9 |
| 036 | correccion-023-implementada-ptepde | CONFIG_MODULE_SIG_ALL x2, CONFIG_MODULE_SIG_FORCE x2, BLOCKED_BY_AUTHORIZATION x2, RX550_SDMA_PTEPDE_DW x2 | INTACTA | 035 | 5 |
| 036 | vocabulario-pm4-vivo-polaris12 | MAP_QUEUES x11, PROVEN x9, UNMAP_QUEUES x6, SET_RESOURCES x5 | INTACTA | - | 37 |
| 037 | mapa-registros-mosaico-y-60-escrituras | PROVEN x8, CP_RB0_WPTR x5, CP_HQD_PQ_WPTR x4, RREG32 x4 | INTACTA | - | 16 |
| 037 | ptba-dos-tramos-y-vm-flush | WRITE_DATA x5, ERROR x3, NOT_DETERMINED x3, WAIT_REG_MEM x2 | INTACTA | - | 8 |
| 038 | herramientas-para-no-repetir-errores | PROVEN x10, TODO x3, FIXME x2, ERROR x2 | INTACTA | - | 3 |
| 038 | validador-flujo-y-regla-del-count | VIOLATION x3, NOT_DETERMINED x2, SET_SH_REG x2, CLEAN x2 | INTACTA | - | 0 |
| 039 | cierre-de-includes-resolucion-real | PROVEN x5, HYPOTHESIS x3, PACKET3_LOAD_SH_REG x1, PROVEN_DERIVED x1 | INTACTA | - | 0 |
| 039 | coherencia-ib-si-existe | NOT_DETERMINED x4, SIZE x3, UNDECODED x3, PROVEN x3 | INTACTA | - | 7 |
| 040 | corpus-verificado-contra-binario-y-runtime | PROVEN x8, EBUSY x7, EACCES x3, LIMITATION x1 | INTACTA | - | 0 |
| 040 | smu-canal-mensajes-gfx8 | VM_INVALIDATE_REQUEST x1, VM_INVALIDATE_RESPONSE x1 | INTACTA | - | 19 |
| 040 | wptr-doorbell-y-tres-productores-de-ib | NOT_DETERMINED x5, INDIRECT_BUFFER x2, SDMA_OP_INDIRECT x2, INDIRECT_BUFFER_VALID x2 | INTACTA | - | 9 |
| 041 | curva-at-histeresis-dvfs-gfx8 | CG_AT__CG_R__SHIFT x2, SISLANDS_MAX_HARDWARE_POWERLEVELS x1, CG_AT__CG_L__SHIFT x1 | INTACTA | - | 12 |
| 041 | grafo-y-detector-contradicciones | PROVEN x12, NOT_DETERMINED x4, HYPOTHESIS x2, FUERZA x2 | INTACTA | - | 0 |
| 041 | herramientas-de-procedencia-y-auditoria | WAIT_REG_MEM_OPERATION x1, RX550_MM_VM_CONTEXT0_PTBA x1, TRUNCATED x1, NOT_ATTEMPTED x1 | INTACTA | - | 0 |
| 042 | at-wire-format-inversion-cg-r-l | CG_R x3, CG_L x2, CG_AT__CG_R x1, CG_AT__CG_L x1 | INTACTA | - | 18 |
| 042 | mapa-causal-y-mecanismo-hqd-mqd | PROVEN x7, NOT_DETERMINED x4, COND_EXEC x3, HYPOTHESIS x1 | INTACTA | - | 10 |
| 042 | vmid-map-y-la-particion-que-es-decision | NOT_DETERMINED x2, CHIP_POLARIS12 x1, PROVEN_DERIVED x1 | INTACTA | - | 1 |
| 043 | asercion-struct-mqd-contra-offsets | PROVEN x8, NOT_DETERMINED x3, SIN_REGISTRO x3, MISMATCH x2 | INTACTA | - | 9 |
| 043 | pll-bsp-asi-pasi | CG_BSP__BSP x1, CG_BSP__BSU x1, RELATION_FIRST_REVERSE_ENGINEERING x1 | INTACTA | - | 9 |
| 043 | vuelta-atras-035-y-036-leian-el-asic-equivocad | PROVEN x9, SDMA0_HWIP x3, CHIP_POLARIS12 x3, NOT_DETERMINED x1 | INTACTA | - | 21 |
| 044 | asercion-corroborada-y-regla-propias-ajenas | PROVEN x7, CP_HQD_EOP x3, STATUS0 x2, SCHEDULER0 x2 | INTACTA | - | 5 |
| 044 | correccion-implementada-y-por-que-make-no-vio- | PROVEN x2, CHIP_POLARIS12 x2, SDMA_OP_PTEPDE x1, SDMA_OP_GEN_PTEPDE x1 | INTACTA | 043 | 10 |
| 044 | xclk-fuentes-y-constantes-legacy | MUX_TCLK_TO_XCLK x1, XTALIN_DIVIDE x1, RV770_ASI_DFLT x1, CYPRESS_HASI_DFLT x1 | INTACTA | - | 7 |
| 045 | fronteras-obsoletas-y-cuatro-formas-de-mentir | PROVEN x10, NOT_DETERMINED x5, REFUTED x4, OBSERVED x4 | INTACTA | - | 0 |
| 045 | la-convencion-de-count-nunca-se-midio-en-mi-as | LIMITE x4, NEGATIVE_RESULT x2, CHIP_POLARIS12 x2, EN_RUTA_IP x2 | INTACTA | - | 7 |
| 045 | smu-cadena-completa-y-cierre-de-scope | CG_AT__CG_R x1, CG_AT__CG_L x1, CG_BSP__BSU x1, CG_R x1 | INTACTA | - | 1 |
| 046 | auto-referencia-y-la-jerarquia-de-fuentes | PROVEN x6, MEASUREMENT x5, RESUELTA_OTRO x4, SIN_SUJETO x4 | INTACTA | - | 0 |
| 046 | correccion-smu-ruta-no-compilada-para-polaris1 | CONFIG_DRM_AMDGPU_SI x1, DRM_AMDGPU_SI x1, DRM_AMDGPU_CIK x1, DRM_AMDGPU_VI x1 | INTACTA | 040 | 15 |
| 046 | la-version-de-ip-que-nunca-se-consulta | SDMA0_HWIP x6, CONFIG_MODULE_SIG_ALL x3, CHIP_POLARIS12 x3, CONFIG_SECURITY_LOCKDOWN_LSM x2 | INTACTA | 047 | 6 |
| 047 | el-handler-si-lee-src-data | PROVEN x6, REFUTED x5, NOT_DETERMINED x4, PROVEN_ABSENT x2 | INTACTA | - | 32 |
| 047 | los-diez-selectores-y-el-limite-del-claim | CONFIG_MODULE_SIG_ALL x3, CHIP_POLARIS12 x3, CONFIG_SECURITY_LOCKDOWN_LSM x2, CONFIG_MODULE_SIG_FORCE x2 | INTACTA | - | 2 |
| 047 | ruta-real-polaris12-canal-smc-argumento-vtable | SMC_RESP x1 | INTACTA | - | 9 |
| 048 | claims-y-lo-que-el-proyecto-realmente-cita | NADA x7, PROVEN x7, CODIGO x6, CITA_RX x2 | INTACTA | - | 2 |
| 048 | numeros-de-hallazgo-no-identifican | MEASUREMENT x4, NNN x3, NOT_DETERMINED x2, TOOL_VALIDATED x1 | INTACTA | - | 0 |
| 048 | protocolo-smc-polaris-armado-y-retorno-siempre | PHM_WAIT_FIELD_UNEQUAL x1 | INTACTA | 040 | 18 |
| 049 | los-497-respaldos-en-codigo-resueltos | EOP_TC_MD_ACTION_EN x5, SIN_RELACION x4, VM_INVALIDATE_REQUEST x3, NEGATIVE_RESULT x2 | INTACTA | - | 2 |
| 049 | modelo-voltaje-smio-polaris12 | PP_HOST_TO_SMC_US x1, SMU_MAX_SMIO_LEVELS x1 | INTACTA | - | 4 |
| 050 | correccion-chip-id-y-clock-stretcher | CHIP_POLARIS10 x2, POLARIS10 x1, NOT_DETERMINED x1, TRUNCATION_AS_ABSENCE x1 | INTACTA | - | 12 |
| 050 | frontera-de-corpus-no-de-hardware | GFX_HWIP x6, MEASUREMENT x5, NOT_DETERMINED x4, DERIVATION x3 | INTACTA | - | 0 |
| 050 | la-frontera-ordenada-por-su-via-de-cierre |  | ? | - | 0 |
| 051 | asic-id-desde-pci-config | GFX_HWIP x5, PCI_IDENTITY x4, PROVEN x4, ASICID_IS_P23 x3 | INTACTA | - | 5 |
| 051 | interrupt-vector-iv-gfx8-y-teardown-lifo | ENABLE_L2_CACHE x4, INVALIDATE_RESPONSE x4, VISLANDS30 x1, AMDGPU_IRQ_CLIENTID x1 | INTACTA | - | 10 |
| 051 | leer-agents-md-cambia-la-politica | DIFERENCIAL x6, UN_REGISTRO x5, CONFIG_MODULE_SIG_ALL x3, CONFIG_SECURITY_LOCKDOWN_LSM x2 | INTACTA | - | 0 |
| 052 | srcid-de-fault-gfx8-y-tabla-de-iv-no-catalogad | VISLANDS30_IV_SRCID x2, GFX_PAGE_INV_FAULT x1, GFX_MEM_PROT_FAULT x1, INVALIDATE_RESPONSE x1 | INTACTA | - | 11 |
| 053 | herramienta-asic-resolver-gate-compilacion | COMPILED_UNGATED x1, GATED_UNDECLARED x1, COMPILED_GATED_ON x1, NOT_COMPILED_GATED_OFF x1 | INTACTA | - | 0 |
| 054 | dos-mascaras-mc-y-pte-y-reproduccion-de-gart | BEST_FIT x2, MC_VM_FB x1, MAX_MC x1, AMDGPU_GMC_HOLE_MASK x1 | INTACTA | - | 12 |
| 055 | didt-indirecto-unidad-dword-y-protocolo-soc15 | UNIT_MISMATCH x1, CGS_IND_REG_GC_CAC x1, CGS_IND_REG__SE_CAC x1, POLARIS11 x1 | INTACTA | - | 13 |
| 056 | function-always-spec-primaria-descartada-con-c | NOT_AVAILABLE x6, CORPUS x3, NOT_DETERMINED x3, WAIT_REG_MEM x2 | INTACTA | - | 1 |
| 056 | siete-herramientas-y-22-bugs-encontrados | PHM_WAIT_FIELD_UNEQUAL x1, PHM_WAIT_REGISTER_UNEQUAL x1 | INTACTA | - | 9 |
| 057 | vias-de-lectura-gpuvm-y-por-que-no-hay-discrim | GET_VM_FAULT_INFO x3, GET_PROCESS_APERTURES x3, WRITE_MEM x3, NOT_DETERMINED x2 | INTACTA | - | 1 |
| 058 | tabla-iv-gfx8-112-nombres-73-valores | CP_ECC_ERROR x3, EXT_TIMING_SYNC_LOSS x2, D1_EXT_TIMING_SYNC_LOSS x2, D1_EXT_TIMING_SYNC x2 | INTACTA | - | 2 |
| 059 | srcdata-no-es-payload-es-el-wptr-del-ring | NOT_DETERMINED x3, HYPOTHESIS x1, FACT x1 | INTACTA | 058 | 2 |
| 060 | srcdata-es-el-subtipo-y-el-decodificador-esta- | EXT_TIMING_SYNC_LOSS x1, EXT_TIMING_SYNC x1, EXT_TIMING_SIGNAL x1, AM_LB_VBLANK_STATUS x1 | INTACTA | 059 | 7 |
| 061 | srcdata-dos-valores-constante-por-derivacion | DERIVATION_BEFORE_OBSERVATION x2, PROVEN_DERIVED x1, WAIT_REG_MEM x1, NOT_DETERMINED x1 | INTACTA | - | 0 |
| 062 | citas-de-c-009-desplazadas-y-tabla-de-030-inve | ERROR x6, PROVEN x3, PDB2 x3, PDB1 x3 | INTACTA | - | 11 |
| 063 | memoria-sesion-smu-estado-persistente | NOT_IN_CORPUS x15, NOT_DETERMINED x10, PROVEN x9, TOOL_VALIDATED x5 | INTACTA | - | 113 |
| 064 | bitmap-vm-context-cntl-gfx8-f3-y-faults | NOT_DETERMINED x6, PAGE_TABLE_DEPTH x6, PROVEN x6, PAGE_TABLE_BLOCK_SIZE x3 | INTACTA | - | 3 |
| 065 | offset-gmc-vs-mmhub-siete-registros | PROVEN x4, BIF_FB_EN x3, NOT_DETERMINED x3, VM_CONTEXT0_CNTL x2 | INTACTA | - | 2 |
| 066 | mapa-familias-por-fichero-c | PROVEN x6, NOT_DETERMINED x1, CORPUS x1, RUNTIME x1 | INTACTA | - | 0 |
| 067 | cadena-gart-256m-y-tabla-en-vram | PROVEN x8, CHIP_POLARIS12 x1, PAGE_TABLE_BASE_ADDR x1, PROVEN_ABSENT x1 | INTACTA | - | 18 |
| 068 | orden-emision-ptba-invalidate-wait-pfp | PROVEN x7, PFP_SYNC_ME x4, PAGE_TABLE_BASE_ADDR x4, NOT_DETERMINED x4 | INTACTA | - | 28 |
| 069 | f11-medido-y-ad12-discriminante-verificado | PROVEN x7, NOT_DETERMINED x2, CITED x1, SOSPECHOSO_DE_NO_LEER x1 | INTACTA | - | 0 |
| 070 | contrato-host-smc-msg-arg-y-handshake | PROVEN x7, SMC_RESP x5, SMU_DONE x4, SMU_PASS x2 | INTACTA | - | 20 |
| 071 | el-except-que-devuelve-stub-y-el-flag-que-desa | TOOL_VALIDATED x3, RUTA_EQUIVOCADA x3, TOOL_BROKEN x2, ROTA x2 | modificada | - | 0 |
| 071 | f2-ejecutado-bloqueado-por-saturacion-gpu | PROVEN x8, NULL x2, EBUSY x1, GLX_SAMPLES x1 | INTACTA | - | 0 |
| 072 | f3c-estatico-cond-exc-e-invalidate-response | COND_EXEC x7, VM_INVALIDATE_RESPONSE x4, SWITCH_BUFFER x4, NOT_DETERMINED x4 | INTACTA | - | 7 |
| 072 | la-lista-cerrada-de-verbos-que-cronometraba-el | CERRADO_POR x6, PROSA x3, NO_RESUELVE x3, GENERALIZADO_POR x2 | modificada | - | 0 |
| 073 | el-indice-por-numero-descarta-y-el-grafo-pierd | NO_RESUELVE x3, CONTINUES x3, PROSA x3, MULTIVALOR x2 | modificada | - | 0 |
| 073 | f7-medido-216-sin-versionar-y-17-ids-duplicado | PROVEN x5, NOT_OBSERVED x1, GIT_INSPECTION x1 | INTACTA | - | 0 |
| 074 | 25-aristas-que-existian-y-44-findings-sin-rela | FAIL x3, CONTINUES x3, CORRECTS x2, COMPLEMENTS x2 | modificada | - | 0 |
| 074 | f2b-el-hardware-compone-el-pte | NOT_DETERMINED x5, GEN_PTEPDE x1, PAGE_TABLE_BLOCK_SIZE x1, RREG32 x1 | INTACTA | - | 23 |
| 075 | mapa-flags-pte-y-bifurcacion-host | PROVEN x8, GEN_PTEPDE x3, PTE_TMZ x3, AMDGPU_PTE_VALID x2 | INTACTA | - | 18 |
| 076 | catalogo-276-mensajes-smu-y-codigos-retirados | AMDGPU_PTE_PRT_FLAG x1, MASTER x1, CORPUS x1, RUNTIME x1 | INTACTA | - | 0 |
| 077 | 141-citas-que-eran-rangos-y-10-omisiones-reale | SGX x1, SOC15D_SGX x1, OMISIONES x1, CONTINUES x1 | modificada | - | 0 |
| 078 | de-las-89-aristas-85-tienen-respaldo-en-el-cue | CONTINUES x3, COMPLEMENTS x3, RUTA_EQUIVOCADA x1, COMPLETA x1 | modificada | - | 1 |
| 079 | el-76-de-respaldo-es-contra-un-numero-que-no-i | NOMBRE x1, NUMERO x1, NINGUNA x1, NOT_PUBLISHED x1 | modificada | - | 0 |
| 080 | un-criterio-automatico-para-las-58-aristas-amb | ESTRUCTURA x1, VI_FLUSH_GPU_TLB_NUM_WREG x1, VOLTAGE_SCALE x1, ORDER x1 | modificada | - | 0 |
| 081 | la-tabla-dpm-son-1884-bytes-no-1120 | TOOL_VALIDATED x1, SMU__NUM_PCIE_DPM_LEVELS x1, SMC_RAM_END x1, NOT_DETERMINED x1 | ? | - | 1 |
| 081 | system-access-mode-3-es-not-in-sys | NOT_IN_SYS x5, PROVEN x5, IN_SYS x3, SYSTEM_ACCESS_MODE x3 | modificada | - | 8 |
| 082 | el-acceso-no-mapeado-pide-pagina-prt | PASS_THRU x8, PROVEN x7, VM_PRT_CNTL x4, MASK_PDE0_FAULT x2 | modificada | - | 40 |
| 082 | ocho-fallos-de-layout-que-producen-numeros-pla | SMU__NUM_PCIE_DPM_LEVELS x2, SILENT_ZERO_IS_A_CLAIM x1, DIVISION_NO_AUDITABLE x1, NO_COMPILE x1 | ? | - | 0 |
| 083 | auditoria-de-las-110-copias-a-la-ram-del-smc | RUNTIME_MISSING x2, CAMPO_COMPLETO x1, COLA_DEL_STRUCT x1, SUBCAMPO_CON_OFFSET x1 | ? | - | 3 |
| 083 | en-gfx8-el-prt-se-puede-activar-y-no-hay-quien | PROVEN x9, AMDGPU_VM_PAGE_PRT x6, NULL x1, VM_PRT_CNTL x1 | modificada | - | 29 |
| 083 | sg-cache-coherency-l1-l2-y-asimetria | RREG32 x2, NOT_DETERMINED x2, MC_VM_MX_L1_TLB_CNTL x1, ECO_BITS x1 | INTACTA | - | 20 |
| 084 | mecanismo-de-copia-al-smc-y-assert-de-rango | NOT_DETERMINED x2, SMU7_FIRMWARE_HEADER_LOCATION x1, SMC_RESERVED_TABLE_SIZE x1, RUNTIME_MISSING x1 | ? | - | 6 |
| 084 | se-packet-consumption-y-granularidad | PROVEN x6, PFP_SYNC_ME x3, NOT_DETERMINED x2, COND_EXEC x2 | INTACTA | - | 19 |
| 085 | sb-page-walker-invalidate-siempre-obligatorio | NOT_DETERMINED x5, PROVEN x4, PAGE_TABLE_BLOCK_SIZE x2, L2_CACHE_BIGK_FRAGMENT_SIZE x1 | INTACTA | - | 21 |
| 086 | sf-vram-256m-visibles-y-la-bar | PROVEN x4, MC_VM_FB_LOCATION x2, OBSERVED x2, NOT_DETERMINED x2 | INTACTA | - | 20 |
| 086 | usec-timeout-del-handshake-smc | AMD_MAX_USEC_TIMEOUT x3, ETIME x1, AMDGPU_MAX_USEC_TIMEOUT x1, SMC_RESP_0 x1 | ? | - | 12 |
| 087 | los-tres-pidcontroller-son-del-firmware | FW_SMU_INTERPRETATION x1, NOT_IN_CORPUS x1 | ? | - | 8 |
| 087 | sf-gmc-8-1-nombre-no-predice-generacion | PROVEN x5, NOT_DETERMINED x4, GMC_HWIP x4, IP_VERSION x2 | INTACTA | - | 40 |
| 087 | vm-fault-stop-0-y-ip-block-mask-confirma-047 | PROVEN x5, STOP_FIRST x2, NOT_DETERMINED x2, VM_PRT_CNTL x2 | modificada | - | 13 |
| 088 | pte-system-es-la-otra-mitad-de-system-access-m | GC_HWIP x6, PROVEN x5, AMDGPU_PTE_SYSTEM x4, SYSTEM_ACCESS_MODE x2 | modificada | - | 10 |
| 089 | gc-hwip-bloqueado-por-capacidad-y-resuelto-est | GC_HWIP x9, PROVEN_DERIVED x4, AMDGPU_PTE_TF x2, NOT_DETERMINED x2 | modificada | - | 3 |
| 090 | sg-l1-l2-constantes-fijas-y-grano-de-2mib | PROVEN x8, NOT_DETERMINED x3, LRU_UPDATE_BY_WRITE x2, WRITE_COUNTERS x2 | INTACTA | - | 36 |
| 091 | el-bloqueo-tecnico-que-llevaba-toda-la-sesion- | PROVEN x4, CONFIG_MODULE_SIG_FORCE x3, BLOCKED_BY_AUTHORIZATION x3, SIG_ALL x2 | modificada | - | 0 |
| 092 | sc-7-tipos-de-fault-y-3-enables-cada-uno | PROVEN x8, NOT_DETERMINED x5, PROTECTIONS x4, RANGE x3 | INTACTA | - | 16 |
| 093 | el-formato-del-pte-y-del-pde-en-el-fuente-de-g | AMDGPU_PTE_TMZ x2, PROVEN x2, AMDGPU_PTE_PRT x1, AMDGPU_VM_PAGE_PRT x1 | modificada | - | 25 |
| 094 | arranque-y-escritura-de-4-bytes-en-campo-de-1 | ATOM_FIRMWARE_INFO_V2_2 x1 | ? | - | 5 |
| 094 | gfx8-solo-escribe-los-bits-0-11-del-pte | PROVEN x15, AMDGPU_PTE_TF x2, AMDGPU_PTE_NOALLOC x2, AMDGPU_PTE_IS_PTE x2 | modificada | - | 19 |
| 094 | sd-presupuesto-del-frame-dos-cifras-viejas | PROVEN x6, NOT_DETERMINED x3, VM_FLUSH x2, PIPELINE_SYNC x1 | INTACTA | - | 42 |
| 095 | camino-termico-y-un-assert-inerte | SEMANTIC_MISSING x4, NOT_DETERMINED x1, CHIP_POLARIS10 x1, CHIP_POLARIS12 x1 | ? | - | 24 |
| 095 | los-5-sin-medir-y-los-2-limite-reconcilian | PACKET3_INDIRECT_BUFFER x3, LIMITE x2, CONTEXT_CONTROL x2, WRITE_DATA x2 | modificada | - | 3 |
| 095 | se-pfp-me-ce-tres-motores-tres-icache | NOT_DETERMINED x7, PFP_SYNC_ME x4, CP_ME_CNTL x4, PROVEN x4 | INTACTA | - | 28 |
| 096 | arbitraje-dram-sin-inicializar-y-tabla-de-vent | RUNTIME_MISSING x5, SEMANTIC_MISSING x2, CONNECTION_MISSING x2, PROVEN x1 | ? | - | 24 |
| 096 | el-discriminante-abc-no-es-cerrable-desde-el-c | PACKET3 x1, PROVEN_ABSENT x1 | ? | - | 6 |
| 096 | se-mecanismo-de-fence-completo | PROVEN x10, NOT_DETERMINED x7, TC_WB_ONLY x3, FENCE x2 | INTACTA | - | 59 |
| 097 | el-memset-que-falta-en-dos-de-cinco | SMU__NUM_SCLK_DPM_STATE x1, PROVEN x1, RUNTIME_MISSING x1, NOT_IN_CORPUS x1 | ? | - | 12 |
| 097 | los-faults-de-vm-estan-desactivados-en-esta-pl | AMDGPU_VM_PAGE_PRT x3, PROVEN x2, VM_PRT_CNTL x2, STOP_NEVER x1 | modificada | - | 7 |
| 097 | se-observado-24-de-24-pares-eop-delta-1 | OBSERVED x10, NOT_DETERMINED x8, PROVEN x4, DATA_SEL x3 | INTACTA | - | 7 |
| 098 | graphicsbootlevel-dos-escritores-dos-espacios- | RUNTIME_MISSING x3, PROVEN x2, SEMANTIC_MISSING x1, NOT_IN_CORPUS x1 | ? | - | 7 |
| 098 | prt-funciona-al-reves-en-gfx9 | VM_PRT_CNTL x7, AMDGPU_PTE_PRT x3, VALID x2, NOT_DETERMINED x1 | modificada | - | 14 |
| 098 | se-observado-retraso-fence-0-a-4 | OBSERVED x4, NOT_DETERMINED x2, L876 x1, RUNTIME x1 | INTACTA | - | 12 |
| 099 | el-retorno-del-setup-de-tablas-dpm-se-ignora | MAX_REGULAR_DPM_NUMBER x2, SMU74_MAX_LEVELS_GRAPHICS x1, SMU74_MAX_LEVELS_MEMORY x1, NULL x1 | ? | - | 7 |
| 099 | prt-no-tiene-consumidor-en-el-arbol | AMDGPU_PTE_PRT x4, VM_PRT_CNTL x2, GFX_PAGE_INV_FAULT x2, PROVEN_ABSENT x1 | modificada | - | 13 |
| 099 | sc-observado-prt-enmascara-el-fault-de-pde0 | PROVEN x4, NOT_DETERMINED x4, AMDGPU_VM_PAGE_PRT x2, OBSERVED x2 | INTACTA | - | 28 |
| 100 | el-limite-de-la-sram-del-smc-es-el-doble-de-la | NOT_DETERMINED x3, RUNTIME_MISSING x3, PROVEN x3, CONNECTION_MISSING x2 | ? | - | 12 |
| 100 | prt-no-tiene-consumidor-ni-en-firmware-ni-irq | AMDGPU_PTE_PRT x2, PAGE_FAULT_IRQ x1, VM_PRT_CNTL x1, GFX_PAGE_INV_FAULT x1 | modificada | - | 4 |
| 100 | sf-observado-gart-65536-y-el-sysfs-que-no-lo-d | NOT_IN_CORPUS x4, NAME_NOT_FOUND x3, NOT_DETERMINED x2, OBSERVED x2 | INTACTA | - | 9 |
| 101 | corpus-hueco-ttm-cierre-parcial-y-valor | PROVEN x8, NOT_IN_CORPUS x6, PARTIAL x1, INFORMATION_GAIN x1 | INTACTA | - | 7 |
| 101 | el-return-temprano-deja-el-selector-de-rango-d | EVIDENCE_MISSING x2, SEMANTIC_MISSING x2, PROVEN x1, RUNTIME_MISSING x1 | ? | - | 2 |
| 101 | gfx8-decodifica-el-tipo-de-fault-y-nadie-lo-le | PROTECTIONS x2, NOT_DETERMINED x2, PROTECTION_FAULT_STATUS x1 | modificada | - | 11 |
| 102 | sa-despacho-cpu-vs-sdma-y-la-rama-que-no-exist | PROVEN x13, PROVEN_DERIVED x3, NOT_DETERMINED x3, L2891 x2 | INTACTA | - | 33 |
| 103 | el-parche-de-uvd-reescribe-bootvddc | PROVEN x7, RUNTIME_MISSING x2, SMC_UVD_PATCH_WRONG_OFFSET x1, SMC_UVD_PATCH_HITS_BOOT_VDDC x1 | ? | - | 18 |
| 104 | once-usos-de-dpm-table-start-y-el-hueco-de-108 | PROVEN x3, NOT_DETERMINED x2, PROVEN_DERIVED x2, CONNECTION_MISSING x2 | ? | - | 0 |
| 105 | se-ih-y-el-camino-real-de-los-faults | PROVEN x8, EXECUTE_PROTECTION_FAULT x2, PROVEN_DERIVED x2, CORROBORATED x2 | INTACTA | - | 44 |
| 106 | funcion-no-existe-y-el-trigger-es-software | FUNCTION x10, PROVEN x9, RESPONSE x5, NOT_DETERMINED x3 | INTACTA | - | 9 |
| 107 | el-parche-de-uvd-escribe-sobre-smio-5 | PROVEN x2, SEMANTIC_MISSING x2, SMC_RAW_WRITE_HITS_SMIO5 x1, SMC_RAW_WRITE_WRITES_INDEX_AS_BOOT_LEVEL x1 | ? | - | 3 |
| 107 | el-reset-vacia-tlb-sin-request | REQUEST x7, VM_INVALIDATE_REQUEST x4, PROVEN x4, SRBM_SOFT_RESET x2 | INTACTA | - | 17 |
| 107 | sc-function-always-2-de-7-y-el-ring-usa-1 | FUNCTION x6, WAIT_REG_MEM x6, PROVEN x5, EQUAL x4 | INTACTA | - | 16 |
| 108 | el-determinante-del-desfase-y-lo-que-no-se-pue | PROVEN x3, NOT_IN_CORPUS x3, NOT_DETERMINED x2, PROVEN_DERIVED x1 | ? | - | 8 |
| 108 | sd-pfp-escribe-me-espera-punto-de-visibilidad | PROVEN x7, WAIT_REG_MEM x4, PFP_SYNC_ME x3, VM_INVALIDATE_REQUEST x2 | INTACTA | - | 13 |
| 109 | sd-un-anillo-dos-motores-tres-esperas | PROVEN x6, PROVEN_DERIVED x3, NOT_DETERMINED x3, FUNCTION x2 | INTACTA | - | 30 |
| 110 | funcion-es-de-wait-reg-mem-no-del-invalidate | FUNCTION x13, PROVEN x10, PROVEN_ABSENT x4, WAIT_REG_MEM x3 | INTACTA | - | 11 |
| 111 | sd-next-ib-el-pfp-lo-busca | PFP_SYNC_ME x10, OBSERVED x6, WAIT_REG_MEM x4, PROVEN x3 | INTACTA | - | 12 |
| 112 | registros-del-walker-en-gmc-8-1-y-las-7-famili | PROVEN x12, PROTECTIONS x8, DEFAULT x7, DERIVATION x5 | INTACTA | - | 34 |
| 113 | dpm-table-start-es-la-base-literal-y-los-once- | NOT_DETERMINED x2, PROVEN_DERIVED x2, CONNECTION_MISSING x1, PROVEN x1 | ? | - | 1 |
| 114 | implgate-cinco-bugs-propios-y-una-afirmacion-f | NOT_DETERMINED x10, MEASUREMENT x9, PROVEN x6, NOT_APPLICABLE x2 | INTACTA | - | 8 |
| 115 | firmware-smc-si-en-el-corpus | NOT_IN_CORPUS x4, PP_TABLE_V1 x3, NOT_AVAILABLE x2, POLARIS10_SMC_SIZE x2 | ? | - | 11 |
| 115 | sd-cuando-hay-invalidate-regla-por-vmid | PROVEN x7, L428 x2, CHIP_POLARIS12 x2, PROVEN_DERIVED x2 | INTACTA | - | 51 |
| 116 | sd-use-cpu-nunca-dispara-geometria | NOT_DETERMINED x5, OBSERVED x4, PROVEN_DERIVED x4, PROVEN x3 | INTACTA | - | 43 |
| 117 | doclint-no-se-mira-el-80 | OBSERVED x7, PROVEN x4, NOT_APPLIED x2, NOT_DETERMINED x1 | INTACTA | - | 13 |
| 118 | toolaudit-no-ve-el-denominador | PROVEN x5, OBSERVED x2, FLAGS x1, PROVEN_ABSENT x1 | INTACTA | - | 0 |
| 119 | el-fichero-que-si-corre-esta-a-una-tabla | PROVEN x8, PROVEN_DERIVED x5, NOT_DETERMINED x4, TOOL_VALIDATED x1 | INTACTA | - | 7 |
| 120 | las-325-referencias-rotas-no-san-325 | MEASUREMENT x4, NOT_DETERMINED x2, TOOL_VALIDATED x1, NOT_FOUND x1 | INTACTA | - | 0 |
| 121 | la-deuda-de-340-no-se-limpa-se-evita | PROVEN x3, NOT_DETERMINED x2, REFUTED x1, PROVEN_DERIVED x1 | INTACTA | - | 0 |
| 121 | pm4-estatico-y-la-contabilidad-cuadra | PROVEN x11, PFP_SYNC_ME x5, EVENT_WRITE_EOP x2, NUM_WREG x2 | INTACTA | - | 13 |
| 121 | tabla-de-relojes-dpm-reconstruida | NOT_DETERMINED x3, SMU__NUM_SCLK_DPM_STATE x1, MAX_REGULAR_DPM_NUMBER x1 | ? | - | 0 |
| 122 | e-los-10-wait-reg-mem-son-hdp-flush | WAIT_REG_MEM x10, PROVEN x7, PFP_SYNC_ME x4, PROVEN_DERIVED x3 | INTACTA | - | 20 |
| 122 | para-que-el-encuadre-de-dos-fuentes-resulte-ho | PROVEN x8, REFUTED x4, ENGINE x2, FUNCTION x2 | INTACTA | - | 0 |
| 122 | ulplatformcaps-decode-y-validacion-cruzada | VDDGFX_CONTROL x2, POWERPLAY x2, OUTPUT_THERMAL2GPIO17 x2, SBIOSPOWERSOURCE x1 | ? | - | 3 |
| 123 | e-cuadra-cuando-se-llama-hdp-flush | PROVEN x12, PROVEN_ABSENT x4, NOT_IN_CORPUS x4, OBSERVED x3 | INTACTA | - | 56 |
| 124 | g-coherencia-page-tables-por-orden | PROVEN x10, NOT_DETERMINED x4, SURFACE_SYNC x3, DONT_PIPELINE x3 | INTACTA | - | 35 |
| 125 | casi-la-mitad-de-las-multiplicidades-no-son-co | PROVEN x5, MEASUREMENT x3, PROVEN_ABSENT x2, INFLADA_DECLARADA x2 | INTACTA | - | 0 |
| 126 | g-el-precio-de-la-coherencia | PROVEN x6, PROVEN_DERIVED x3, NOT_DETERMINED x2, DELAYED x1 | INTACTA | - | 51 |
| 127 | align-mask-no-se-opone-a-emit-ib-size | PROVEN x5, WARN x3, PROVEN_DERIVED x3, OBSERVED x1 | INTACTA | - | 33 |
| 127 | dos-rutas-y-la-de-caida-defectuosa | PHASES x3, NOT_IN_CORPUS x1, MAX_REGULAR_DPM_NUMBER x1, VDDC_SHIFT x1 | ? | - | 5 |
| 127 | g-hay-una-cache-l2-de-fragmentos | PROVEN x7, CORROBORATED x3, VM_L2_CNTL4 x3, NOT_DETERMINED x3 | INTACTA | - | 34 |
| 128 | c-dos-mecanismos-de-invalidate | PROVEN x10, VM_L2_CNTL2 x7, DISABLE_INVALIDATE_PER_DOMAIN x5, VM_INVALIDATE_REQUEST x4 | INTACTA | - | 11 |
| 129 | a-translate-further-y-fragment-size | PROVEN x6, PDE_CACHE_EFFECTIVE_SIZE x5, OBSERVED x3, L2_CACHE_BIGK_FRAGMENT_SIZE x2 | INTACTA | - | 26 |
| 130 | ab-el-l1-guarda-un-pte-por-fragmento | PROVEN x9, NOT_DETERMINED x4, PROVEN_DERIVED x2, L88 x1 | INTACTA | - | 35 |
| 130 | la-clase-count-menos-n-barrida | NOT_DETERMINED x2, TOOL_VALIDATED x1, RE_SITIO x1, SMU10_MAX_HARDWARE_POWERLEVELS x1 | ? | - | 0 |
| 130 | pm4-contrastado-contra-el-codigo-del-ko | PROVEN x5, WAIT_REG_MEM x1, NOT_DETERMINED x1, NOT_APPLICABLE x1 | INTACTA | - | 1 |
| 131 | c-prt-no-esta-bloqueado | PROVEN x7, NOT_DETERMINED x4, MASK_PDE0_FAULT x3, NOT_PROVEN x2 | INTACTA | - | 21 |
| 131 | los-26-count-valen-uno-y-esta-medido | NOT_DETERMINED x2, ATOM_PPLIB_CLASSIFICATION_UI_PERFORMANCE x1, BOOT x1 | ? | - | 7 |
| 132 | a-flags-de-pte-frag-y-tf | PROVEN x4, AMDGPU_PTE_TF x3, PROVEN_ABSENT x3, PROVEN_DERIVED x3 | INTACTA | - | 45 |
| 132 | clockstretcher-viva-en-mi-placa | PP_CLOCK_STRETCH_MASK x1, NOT_AVAILABLE x1 | ? | - | 10 |
| 133 | g-el-mtype-no-existe-en-gfx8 | PROVEN x5, PROVEN_DERIVED x4, EXECUTABLE x2, MTYPE_UC x2 | INTACTA | - | 32 |
| 133 | ulv-viva-y-linklevel-count-mas-1 | NOT_DECODED x1, PSI1 x1, PSI0_EN x1, CHIP_POLARIS12 x1 | ? | - | 18 |
| 134 | hay-un-objeto-vddc-svid2-y-vddcphase-es-3 | ATOM_VOLTAGE_OBJECT_HEADER_V3 x1, PSI1 x1, PSI0_EN x1, NOT_AVAILABLE x1 | ? | - | 9 |
| 134 | que-se-puede-ver-sin-root-y-que-no | PROVEN x3, REFUTED x1 | INTACTA | - | 1 |
| 135 | packet3-clasificados-por-quien-los-usa | PROVEN x6, NOT_DETERMINED x3, PACKET3 x1, PACKET3_ x1 | INTACTA | - | 6 |
| 135 | tres-capas-del-mvdd-por-nivel | NONE x1, ATOM_FIRMWARE_CAPABILITY x1 | ? | - | 2 |
| 136 | el-indice-del-proyecto-estaba-obsoleto |  | ? | - | 0 |
| 136 | g-la-cadena-de-coherencia-cerrada | PROVEN x11, PROVEN_DERIVED x7, SNOOPED x6, NOT_IN_CORPUS x2 | INTACTA | - | 42 |
| 137 | c-configuracion-tlb-l2-gfx8 | PROVEN x6, NOT_DETERMINED x4, L869 x2, RREG32 x2 | INTACTA | - | 34 |
| 138 | c-protection-faults-y-la-geometria | PROVEN x15, PAGE_TABLE_DEPTH x6, NOT_DETERMINED x5, PROVEN_DERIVED x5 | INTACTA | - | 25 |
| 139 | formato-del-pte-y-del-pde-y-la-homonimia-prt | PROVEN x19, PROVEN_DERIVED x7, NOT_DETERMINED x7, FRAG x4 | INTACTA | - | 75 |
| 140 | f-mapa-de-direcciones-observado | PROVEN_DERIVED x16, HYPOTHESIS x4, NOT_DETERMINED x4, PROVEN x4 | INTACTA | - | 31 |
| 141 | la-suite-detecta-8-de-8-bugs-inyectados-y-el-d | DISPATCH_DIRECT x2, DECODIF x1, SURFACE_SYNC x1, EVENT_WRITE x1 | INTACTA | - | 2 |
| 142 | f-agp-vacia-y-bloque-hdp-sin-nombre | PROVEN_ABSENT x7, PROVEN_DERIVED x7, PROVEN x6, NOT_IN_CORPUS x6 | INTACTA | - | 22 |
| 143 | c-registros-golden-y-ciclo-del-prt | PROVEN x11, LOW x6, PROVEN_DERIVED x5, VM_PRT_CNTL x4 | INTACTA | - | 7 |
| 144 | prt-cierra-y-el-corpus-no-tiene-uapi | AMDGPU_VM_PAGE_PRT x10, PAGE_PRT x6, NOT_IN_CORPUS x6, PROVEN x5 | INTACTA | - | 32 |
| 145 | el-99-del-corpus-es-amd | NOT_IN_CORPUS x11, PROVEN x4, PROVEN_ABSENT x2, NOT_FOUND x2 | INTACTA | - | 1 |
| 146 | el-makefile-no-es-un-manifiesto | PROVEN x5, PROVEN_DERIVED x4, CHIP_POLARIS12 x1, NOT_DETERMINED x1 | INTACTA | - | 1 |
| 147 | display-modelo-de-programacion-dce100 | PROVEN x13, PROVEN_DERIVED x4, NOT_DETERMINED x4, SE_SF x3 | INTACTA | - | 7 |
| 148 | display-sink-generico-y-un-bit-de-salida | TMDS_CNTL x8, TMDS_PIXEL_ENCODING x5, PROVEN_DERIVED x5, PROVEN x5 | INTACTA | - | 18 |
| 149 | display-la-frontera-dm-dc | PROVEN_DERIVED x8, PROVEN x8, PROVEN_ABSENT x4, DSC x4 | INTACTA | - | 5 |
| 150 | display-signal-type-mascara-o-enum | PROVEN x11, PROVEN_DERIVED x3, NOT_DETERMINED x3, HDMI x2 | INTACTA | - | 0 |
| 151 | display-dml1-vs-dml2-medido | PROVEN x10, NOT_DETERMINED x4, PROVEN_DERIVED x3, DC_ENABLE_DML2 x2 | INTACTA | - | 2 |
| 152 | display-dc-link-la-tercera-pieza | PROVEN_DERIVED x11, PROVEN x9, NOT_DETERMINED x5, MAX_SINKS_PER_LINK x3 | INTACTA | - | 0 |
| 153 | display-ddi-y-el-identificador-de-objeto | PROVEN x16, PROVEN_DERIVED x7, NOT_DETERMINED x6, MAX_NUMBER_OF_EXT_DISPLAY_PATH x5 | INTACTA | - | 6 |
| 154 | display-donde-se-decide-la-senal | PROVEN x13, PROVEN_DERIVED x9, NOT_DETERMINED x5, VIRTUAL x3 | INTACTA | - | 7 |
| 155 | el-dc-de-esta-maquina-es-dce-11-2 | PROVEN x12, NOT_DETERMINED x7, PROVEN_DERIVED x5, REFUTED x5 | INTACTA | - | 8 |
| 156 | la-identidad-de-un-camino-de-codigo | PROVEN x7, PROVEN_DERIVED x7, REFUTED x6, NOT_DETERMINED x5 | INTACTA | - | 12 |
| 157 | display-16-null-y-dos-mecanismos | PROVEN_DERIVED x10, PROVEN x9, VIRTUAL x3, NOT_DETERMINED x3 | INTACTA | - | 21 |
| 158 | el-par-struct-tabla-y-no-el-chip | PROVEN x15, PROVEN_DERIVED x8, NOT_DETERMINED x4, PROVEN_ABSENT x3 | INTACTA | - | 32 |
| 159 | dce112-52-funciones-21-por-ciento-de-dce110 | PROVEN x12, PROVEN_DERIVED x8, NOT_DETERMINED x3, PROVEN_ABSENT x2 | INTACTA | - | 6 |
| 160 | dp-4-carriles-hbr3-32-gbps | PROVEN x19, PROVEN_DERIVED x8, NOT_DETERMINED x5, LANE_COUNT_DP_MAX x2 | INTACTA | - | 19 |
| 161 | reloj-600-mhz-y-el-bios | PROVEN x15, PROVEN_DERIVED x13, NOT_IN_CORPUS x5, NOT_DETERMINED x3 | INTACTA | - | 46 |
| 162 | seis-tuberias-y-el-bomb-de-interrupciones | PROVEN x17, PROVEN_DERIVED x14, MAX_PIPES x7, PROVEN_ABSENT x6 | INTACTA | - | 35 |
| 163 | log-observado-polaris12-y-cero-crtc | PROVEN x25, PROVEN_DERIVED x12, NOT_DETERMINED x7, POLARIS12 x1 | INTACTA | - | 0 |
| 164 | lexa-pro-y-el-gart-fija-mc-mask | PROVEN x18, PROVEN_DERIVED x8, HOLE x6, NOT_DETERMINED x5 | INTACTA | - | 16 |
| 165 | cuanto-de-display-es-generico | PROVEN x12, PROVEN_DERIVED x11, NOT_DETERMINED x2, DC_ENABLE_DML2 x1 | INTACTA | - | 0 |
| 166 | dos-conectores-dvi-y-hdmi | PROVEN_DERIVED x14, PROVEN x12, NOT_DETERMINED x6, DC_LOG_DC x5 | INTACTA | - | 25 |
| 167 | los-dos-conectores-dvi-y-hdmi-en-registros | PROVEN_DERIVED x21, PROVEN x12, TMDS_CNTL x6, ASSERT x5 | INTACTA | - | 33 |
| 168 | el-formato-termino-para-comprobar-citas | MAL_FORMADA x2, SIN_TERMINO x2, ROL x1 | INTACTA | - | 2 |
| 169 | los-cinco-sitios-de-full-visible-vivos | DERIVATION x5, OBSERVED x3, ENOMEM x2, PROVEN x2 | INTACTA | - | 20 |
| 170 | no-existe-codigo-que-reutilizar | PROVEN_DERIVED x14, NOT_DETERMINED x7, PROVEN x5, PROVEN_ABSENT x3 | INTACTA | - | 0 |
| 171 | la-distancia-al-driver-es-orden-no-cantidad | NOMBRADO x3, PROBADO x2, MMIO x1, SRC x1 | INTACTA | - | 13 |
| 172 | la-capa-generica-y-un-69-que-era-falso | PROVEN x16, PROVEN_DERIVED x14, NOT_DETERMINED x3, PIXEL_ENCODING_UNDEFINED x1 | INTACTA | - | 1 |
| 173 | el-secuenciador-es-un-interprete | PROVEN_DERIVED x14, PROVEN x12, DWBC x4, HUBBUB x4 | INTACTA | - | 6 |
| 174 | el-87-por-ciento-son-llamadas-directas | PROVEN_DERIVED x12, PROVEN x8, NOT_DETERMINED x3, L1332 x1 | INTACTA | - | 4 |
| 175 | para-otra-gpu-entre-24-y-75 | PROVEN_DERIVED x12, PROVEN x7, NOT_DETERMINED x5, HUBP x4 | INTACTA | - | 1 |
| 176 | longitudes-de-bar-sin-root-y-mapa-de-bloques-f | NOT_IN_CORPUS x2, BLOCKED_BY_PERMISSION x1, NOT_DETERMINED x1, CORROBORATED x1 | INTACTA | - | 0 |
| 177 | res-cpu-visible-cierra-secF | SIGBUS x8, PROVEN x7, AMDGPU_PL_PREEMPT x4, VM_FAULT_SIGBUS x4 | INTACTA | - | 28 |
| 178 | los-dos-canales-son-disjuntos | PROVEN x14, PROVEN_DERIVED x11, NOT_DETERMINED x5, STATIC x1 | INTACTA | - | 13 |
| 179 | cuatro-clases-y-dos-por-ciento-9 | PROVEN_DERIVED x14, PROVEN x9, NOT_DETERMINED x4, STATIC x1 | INTACTA | - | 11 |
| 180 | las-ocho-direcciones-de-registro-con-su-linea- | NO_EN_CORPUS x4, MM_VM_CONTEXT0_PTBA x1, PTBA x1, PROVEN x1 | INTACTA | - | 5 |
| 181 | de-443839-lineas-123571-alcanzables | PROVEN_DERIVED x8, PROVEN x8, NOT_DETERMINED x8, PROVEN_ABSENT x3 | INTACTA | - | 16 |
| 182 | ip-versions-gc-hwip-es-cero | GC_HWIP x5, PROVEN_ABSENT x5, PROVEN x5, GFX_HWIP x3 | INTACTA | - | 14 |
| 183 | dos-formatos-de-iv-y-la-version-del-bloque-que | NOT_PROVEN x2, AMDGPU_IRQ_CLIENTID_LEGACY x1, PROVEN_DERIVED x1, PROVEN x1 | INTACTA | - | 29 |
| 184 | veintiuna-guardas-y-la-cadena-de-identidad | PROVEN x13, PROVEN_DERIVED x11, DCE_VERSION_11_2 x6, DC_ENABLE_DML2 x4 | INTACTA | - | 61 |
| 185 | siete-raices-y-el-motor-no-es-dml | PROVEN x13, NOT_DETERMINED x7, PROVEN_DERIVED x6, NULL x4 | INTACTA | - | 33 |
| 186 | 685-afirmaciones-abiertas-no-era-un-resultado | UN_REGISTRO x2, NOT_DETERMINED x1, SIN_PISTAS x1 | INTACTA | - | 0 |
| 187 | dos-caracteres-en-un-patron | PROVEN x13, PROVEN_DERIVED x6, NOT_DETERMINED x5, REFUTED x3 | INTACTA | - | 19 |
| 188 | el-nombre-del-op-12-y-la-cita-equivocada | SUB_OP x3, SDMA_OP_GEN_PTEPDE x1, SDMA_OP_PTEPDE x1, GEN x1 | INTACTA | - | 17 |
| 189 | diecinueve-caracteres-chinos-en-un-proyecto-qu | INSERTADO x2, ANGLICISMO x2, INTENCIONALES x1, PERMITIDO x1 | INTACTA | - | 0 |
| 190 | dos-registros-de-version-ip-y-tmz-confirmado-e | PROVEN x10, PROVEN_RUNTIME x3, DERIVATION x2, GC_HWIP x1 | INTACTA | - | 26 |
| 191 | 126-tablas-ip-block-y-la-superficie-real | PROVEN x7, DERIVATION x2, ET_REL x1, PROVEN_RUNTIME x1 | INTACTA | - | 2 |
| 192 | uvd-6-3-y-vce-3-4-aliasan-a-su-version-anterio | PROVEN x8, DERIVATION x2, HYPOTHESIS x1 | INTACTA | - | 7 |
| 193 | tabla-de-asic-desde-el-binario | PROVEN x9, CORROBORATED x3, CHIP_POLARIS12 x3, ASICID_IS_P23 x3 | INTACTA | - | 1 |
| 194 | huella-de-escritura-del-host-dentro-de-la-tabl | SMC_RESERVED_TABLE_SIZE x1, RUNTIME_MISSING x1 | ? | - | 3 |
| 195 | cache-validada-por-longitud |  | ? | - | 1 |
| 196 | codificacion-de-frecuencia-de-reloj-punto-fijo | MUX_TCLK_TO_XCLK x3, POSTDIV_DIV_BY_16 x2, CG_CLKPIN_CNTL x2, MP1_HWIP x1 | ? | - | 21 |
| 197 | la-colision-de-nombres-en-kbuild-que-pierde-co | RX550_MMIO_LEN x2, KBUILD_COLISION x2, RX550_MMIO_BAR x1, INVOCA x1 | INTACTA | - | 2 |
| 198 | tres-correcciones-de-la-poda | PROVEN x10, PROVEN_DERIVED x8, NOT_DETERMINED x5, BANDERAS_FALSAS x2 | INTACTA | - | 13 |
| 199 | seccion-f-la-base-de-vram-y-el-agujero | PROVEN x16, FB_BASE x5, ERROR x5, NOT_DETERMINED x4 | INTACTA | - | 17 |
| 200 | mapa-real-de-bar-el-driver-mapea-bar5 | PROVEN x6, CHIP_BONAIRE x1, PCI_BASE_ADDRESS_5 x1, PROVEN_RUNTIME x1 | INTACTA | - | 13 |
| 201 | mc-vm-fb-location-dos-prefijos-para-el-mismo-r | MC_ x2, MC_VM_FB_LOCATION x1, CHIP_POLARIS12 x1, POLARIS10 x1 | INTACTA | - | 22 |
| 202 | la-ventana-de-registros-es-bar5-y-el-log-lo-di | NOT_IN_CORPUS x4, CHIP_BONAIRE x2, CONFIG_MEMSIZE x2, CHIP_POLARIS12 x1 | INTACTA | - | 19 |
| 203 | los-headers-son-vocabulario-no-mapa-de-uso | PROVEN x5, DERIVATION x2, RETRACTADO x1, NOT_DETERMINED x1 | INTACTA | - | 1 |
| 204 | los-256-mib-del-gart-son-semantica | PROVEN x14, PROVEN_DERIVED x11, ERROR x3, FB_BASE x3 | INTACTA | - | 31 |
| 205 | regla-de-intercambio-y-cambio-de-codificacion- | AMD_IS_APU x1, NOT_IN_CORPUS x1 | ? | - | 19 |
| 206 | contrato-de-niveles-y-un-limite-no-comprobado | MAX_REGULAR_DPM_NUMBER x3, SMU74_MAX_LEVELS_GRAPHICS x3, PP_TABLE_V0 x2, SMU__NUM_SCLK_DPM_STATE x1 | ? | - | 13 |
| 207 | palabra-de-voltaje-empaquetada-y-busqueda-por- | VOLTAGE_SCALE x2, VDDC_VDDCI_DELTA x2, CHIP_POLARIS12 x1, FW_SMU_INTERPRETATION x1 | ? | - | 12 |
| 208 | lut-de-voltaje-del-smc | SMU7_VOLTAGE_CONTROL_BY_GPIO x2, FW_SMU_INTERPRETATION x1, NOT_IN_CORPUS x1, SMU_MAX_SMIO_LEVELS x1 | ? | - | 1 |
| 209 | siete-campos-de-pmfuses-se-suben-a-cero | SEMANTIC_MISSING x2, VFT_ATE x1, PROVEN x1, NOT_DETERMINED x1 | ? | - | 0 |
| 210 | sc-handshake-de-completacion-existe-y-072-se-e | PROVEN x7, NOT_DETERMINED x6, RREG32 x2, VM_INVALIDATE_RESPONSE x2 | INTACTA | - | 31 |
| 211 | sc-invalidate-request-response-16-bits | PROVEN x6, NOT_DETERMINED x5, RREG32 x2, VM_INVALIDATE_REQUEST x1 | INTACTA | - | 10 |
| 212 | la-disposicion-del-firmware-por-un-shift-de-bi | PROVEN x3, NOT_IN_CORPUS x2, PROVEN_DERIVED x1, RUNTIME_MISSING x1 | ? | - | 1 |
| 213 | herramienta-de-cobertura-de-escrituras-en-la-s | VIVA x6, TOOL_VALIDATED x1, TABLA_DPM x1, TAPADA x1 | ? | - | 10 |
| 214 | ambito-de-variable-un-bug-de-la-herramienta-qu | SMU74_MAX_LEVELS_GRAPHICS x2, SMU__NUM_SCLK_DPM_STATE x2, VIVA x1, PROVEN x1 | ? | - | 0 |
| 215 | allowmvddswitch-se-escribe-a-soft-regs-start | NOT_IN_CORPUS x2, PROVEN x1 | ? | - | 3 |
| 216 | cero-verificacion-de-lo-escrito-en-la-sram | PROVEN x2, NOT_IN_CORPUS x2, SEMANTIC_MISSING x2, POLARIS10_SMC_SIZE x1 | ? | - | 2 |
| 217 | cadena-muerta-de-la-tabla-de-registros-mc | PP_ASSERT_WITH_CODE x2, CHIP_POLARIS12 x1, RUNTIME_MISSING x1, NOT_IN_CORPUS x1 | ? | - | 20 |
| 218 | sd-el-vm-flush-lo-pide-el-scheduler | PROVEN x6, NOT_DETERMINED x4, COND_EXEC x2, SWITCH_BUFFER x2 | INTACTA | - | 28 |
| 219 | el-byte-que-se-escribe-no-es-offsetof-del-camp | NOT_IN_CORPUS x2, PROVEN_DERIVED x1, PROVEN x1, SMC_UVD_PATCH_WRONG_OFFSET x1 | ? | - | 5 |
| 220 | clock-stretch-amount-leido-del-vbios | NOT_IN_CORPUS x1, PROVEN x1, ATOM_COMMON_TABLE_HEADER x1, RUNTIME_MISSING x1 | ? | - | 2 |
| 221 | fw-smc-es-el-de-esta-placa-confirmado-por-dos- | USHORT x3, ATOM_COMMON_TABLE_HEADER x1 | ? | - | 2 |
| 222 | tjmax-93-a-operating-temp-43 | SEMANTIC_MISSING x2, PROVEN_DERIVED x1, PROVEN x1, NOT_IN_CORPUS x1 | ? | - | 4 |
| 223 | resultado-negativo-estados-ppt-sin-relojes | SMU74_MAX_LEVELS x2, SMU_MAX_MCLK_DPM_LEVELS x2, PROVEN x2, NOT_DETERMINED x1 | ? | - | 5 |
| 224 | dpm-levels-8-contra-una-cuenta-solo-validada-c | MAX_REGULAR_DPM_NUMBER x1, NOT_DETERMINED x1, CHIP_POLARIS12 x1, UCHAR x1 | ? | - | 9 |
| 225 | tabla-cac-vddgfx-basura-pero-con-un-cap-apagad | VDDGFX_CONTROL x2, UCHAR x1, ATOM_TONGA_PP_PLATFORM_CAP_VDDGFX_CONTROL x1, SMU7_VOLTAGE_CONTROL_NONE x1 | ? | - | 5 |
| 226 | barrido-de-la-frontera-vbios-host | MAX_REGULAR_DPM_NUMBER x1, TOOL_BROKEN x1 | ? | - | 0 |
| 227 | enable-dpm-tasks-devuelve-cero | PP_ASSERT_WITH_CODE x2, REGISTRA_Y_SIGUE x1, ABORTA x1, PARTIAL_READ_AS_COMPLETE x1 | ? | - | 10 |
| 228 | contrato-de-error-de-los-1093-asserts | REGISTRA_Y_SIGUE x4, PARTIAL_READ_AS_COMPLETE x4, ABORTA x3, PR_WARN_PURO x3 | ? | - | 6 |
| 229 | copia-sin-cota-contra-array-fijo-de-8 | NOT_IN_CORPUS x3, ATOM_COMMON_TABLE_HEADER x1, UCHAR x1 | ? | - | 10 |
| 230 | la-segunda-frontera-barrida-5-arrays-fijos | MAX_REGULAR_DPM_NUMBER x2, TOOL_VALIDATED x1 | ? | - | 15 |
| 231 | ip-version-del-firmware-cierra-gfx-hwip | GFX_HWIP x9, PROVEN x7, PROVEN_ABSENT x5, NOT_DETERMINED x2 | INTACTA | - | 13 |
| 232 | coherencia-cpu-gpu-tres-mecanismos | PROVEN x8, NULL x6, RREG32 x2, REQ x2 | INTACTA | - | 30 |
| 233 | escritor-cpu-desactivado-por-dos-razones | PROVEN x7, AMDGPU_VM_USE_CPU_FOR_COMPUTE x2, AMDGPU_VM_USE_CPU_FOR_GFX x2, WARN_ON x1 | INTACTA | - | 31 |
| 234 | una-cita-puede-resolver-y-no-servir | TRUNCADA x1, GEN_PTEPDE x1, SIN_TERMINO x1 | INTACTA | - | 0 |
| 235 | los-600mhz-son-el-techo-de-hdmi-2-0 | PROVEN_DERIVED x16, PROVEN x9, NOT_DETERMINED x5, NOT_IN_CORPUS x3 | INTACTA | - | 5 |
| 236 | los-nueve-bloques-ip | PROVEN_DERIVED x13, PROVEN x11, NOT_DETERMINED x6, PROVEN_ABSENT x2 | INTACTA | - | 0 |
| 237 | la-densidad-de-delegacion | PROVEN_DERIVED x13, PROVEN x9, HUBP x4, NOT_DETERMINED x4 | INTACTA | - | 0 |
| 238 | la-densidad-clasifica-el-fichero | PROVEN x10, PROVEN_DERIVED x10, NOT_DETERMINED x4, STATIC x1 | INTACTA | - | 8 |
| 239 | tlb-de-gfx8-entra-en-bloques-de-8-pte | PROVEN x3, CORROBORATED x3, GC_HWIP x2, DERIVATION x2 | INTACTA | - | 7 |
| 240 | la-cadena-de-identidad-observada | OBSERVED x9, AMDGPU_FAMILY_VI x8, PROVEN x8, PROVEN_DERIVED x6 | INTACTA | - | 21 |
| 241 | el-eslabon-que-faltaba-era-un-literal | PROVEN x13, PROVEN_DERIVED x10, AMDGPU_FAMILY_VI x6, PROVEN_ABSENT x6 | INTACTA | - | 27 |
| 242 | los-registros-caben-en-bar5-con-4x-de-holgura | PROVEN x8, RREG_SDMA x1, WREG_SDMA x1, RREG32 x1 | INTACTA | - | 5 |
| 243 | los-5907-mib-de-gtt-es-la-mitad-de-la-ram | PROVEN x13, PROVEN_DERIVED x8, UN_REGISTRO x4, PROVEN_ABSENT x2 | INTACTA | - | 13 |
| 244 | 182-demostrado-desde-el-binario-cero-escritura | PROVEN x6, IP_VERSION x2, CHIP_POLARIS12 x1, PROVEN_CADENA x1 | INTACTA | - | 5 |
| 245 | cien-numeros-de-hallazgo-duplicados-y-la-reser | AMBIGUO x2, ROTA x1 | INTACTA | - | 0 |
| 246 | la-coherencia-de-gfx8-son-tres-registros-y-nin | PROVEN x19, PROVEN_DERIVED x19, ERROR x8, PROVEN_ABSENT x6 | INTACTA | - | 25 |
| 246 | todo-el-mmio-pasa-por-dos-helpers | PROVEN x7, DERIVATION x2, MAX_DIST x1, SDMA x1 | INTACTA | - | 0 |
| 247 | por-que-la-captura-se-queda-en-el-40 | PROVEN x7, DERIVATION x1, REFUTADO x1 | INTACTA | - | 4 |
| 250 | la-herramienta-que-decia-22-discriminantes-cua | OBSERVED x3, HOST_OBSERVATION x1, NEC_A_RUTA x1, SUELTA x1 | INTACTA | - | 0 |
| 251 | leer-la-temperatura-no-es-leer-un-registro | PROVEN x18, PROVEN_DERIVED x11, ERROR x7, PROVEN_ABSENT x4 | INTACTA | - | 34 |
| 252 | el-hueco-del-heuristico-de-config-memsize | DECLARADO x2, INVOCA x2, CONFIG_MEMSIZE x1, MODEL_CHOICE x1 | INTACTA | - | 12 |
| 253 | edge-sale-de-gfxtemperature-y-hotspot-de-socte | PROVEN x16, PROVEN_DERIVED x14, NOT_DETERMINED x8, ERROR x5 | INTACTA | - | 6 |
| 254 | la-cabecera-de-los-20-firmware-valida-20-de-20 | PROVEN x16, PROVEN_DERIVED x16, NOT_DETERMINED x7, ERROR x7 | INTACTA | - | 4 |
| 255 | las-tres-contradicciones-son-el-mismo-intermed | PROVEN x18, PROVEN_DERIVED x16, REFUTED x7, ERROR x7 | INTACTA | - | 12 |
| 256 | la-tabla-de-spread-spectrum-que-si-alcanza-mi- | PROVEN x6, NOT_DETERMINED x3, ATOM_ASIC_SS_ASSIGNMENT_V3 x2, NOT_OBSERVED x2 | ? | - | 16 |
| 257 | herramienta-validada-que-ancla-mal-las-escritu | NO_RESUELTO x2, NOT_DETERMINED x2, PROVEN x2, DEGRADED x2 | ? | - | 0 |
| 257 | sched-hw-submission-2-y-el-anillo-gfx-son-2048 | PROVEN x19, PROVEN_DERIVED x19, ERROR x9, NOT_OBSERVED x4 | INTACTA | - | 28 |
| 258 | verificar-el-target-coincide-en-diez-campos-y- | DIFIERE x2, TARGET_PARCIAL x1, TARGET_MATCH x1, ESTIMADO x1 | INTACTA | - | 0 |

**TOTAL**: 347 findings.

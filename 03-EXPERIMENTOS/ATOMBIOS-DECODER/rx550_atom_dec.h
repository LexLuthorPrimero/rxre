/*
 * rx550_atom_dec.h - Decodificador puro del ATOMBIOS de la RX 550 (Polaris12/GFX8)
 *
 * Sin libc. Sin ioctl. Sin /dev. Sin escritura de registros. Lector puro de fichero.
 *
 * Todos los offsets de este fichero están DERIVADOS del árbol del kernel en
 * RESEARCH/baseline/linux-7.1.3. Cada constante lleva la cita fichero:línea que
 * la justifica. Lo que no se puede derivar se marca NO_DERIVADO y no se imprime
 * como si fuera un hecho.
 *
 * Ver 08-ARQUITECTURA/ATOMBIOS-DECODER.md para el informe completo.
 */

#ifndef RX550_ATOM_DEC_H
#define RX550_ATOM_DEC_H

#ifdef __KERNEL__
#include <linux/types.h>
#else
#include <stdint.h>
#endif

#ifdef __KERNEL__
typedef uint8_t  u8_rxd;
typedef uint16_t u16_rxd;
typedef uint32_t u32_rxd;
typedef uint64_t u64_rxd;
#else
typedef uint8_t  u8_rxd;
typedef uint16_t u16_rxd;
typedef uint32_t u32_rxd;
typedef uint64_t u64_rxd;
#endif

/* =======================================================================
 * 1. RUTA DE LECTURA QUE ESTE DECODIFICADOR REPLICA
 *
 * No se replica la ruta de ATOMFW (atomfirmware.h / amdgpu_atomfirmware.c).
 * Se replica la ruta que el driver usa para CHIP_POLARIS12, que queda fijada por
 *   gfx_v8_0.c:1676-1681
 *     case CHIP_POLARIS11:
 *     case CHIP_POLARIS12:
 *             ret = amdgpu_atombios_get_gfx_info(adev);
 * Es decir: la geometria de este ASIC sale de amdgpu_atombios_get_gfx_info(), que
 * lee ATOM_GFX_INFO_V2_1. Ver ATOMBIOS-DECODER.md seccion "RUTA DERIVADA".
 * ======================================================================= */

/* --- amdgpu_bios.c:161-171 : el buffer es la ROM de PCI byte a byte -------- */
/* pci_map_rom(adev->pdev, &size) -> memcpy_fromio(adev->bios, bios, size)
 * luego adev->bios[0] == byte 0 del fichero ROM. Offset de fichero == offset de bios.
 * Cita: amdgpu_bios.c:161, amdgpu_bios.c:171 */

/* --- amdgpu_bios.c:44,60 : validacion de firma 0x55AA -------------------- */
#define RX550_VBIOS_SIG_OFF        0x00u   /* amdgpu_bios.c:44  */
#define RX550_VBIOS_SIG_BYTE0      0x55u   /* amdgpu_bios.c:44  */
#define RX550_VBIOS_SIG_BYTE1      0xAAu   /* amdgpu_bios.c:44  */

/* --- amdgpu_bios.c:45 : longitud declarada. NO se usa en esta ruta -------- */
/* AMD_VBIOS_LENGTH(p) ((p)[2] << 9). Solo se usa en amdgpu_bios.c:202
 * (amdgpu_read_bios_from_rom), que NO es la ruta de pci_map_rom.
 * Se decodifica y se marca como no usado por la ruta. */
#define RX550_AMD_VBIOS_LENGTH_OFF 0x02u   /* amdgpu_bios.c:45  */

/* --- amdgpu_bios.c:55 : longitud minima antes de tocar nada --------------- */
#define RX550_CHECK_ATOM_MIN_SIZE  0x49u   /* amdgpu_bios.c:55, size < 0x49 */

/* --- amdgpu_bios.c:66 y atom.h:35 : puntero al ATOM_ROM_HEADER ------------ */
/* amdgpu_bios.c:66  bios_header_start = bios[0x48] | (bios[0x49] << 8);
 * atom.h:35         #define ATOM_ROM_TABLE_PTR 0x48
 * atom.c:1573       base = CU16(ATOM_ROM_TABLE_PTR);
 * Los dos leen el mismo u16 en 0x48..0x49, little-endian. */
#define RX550_ATOM_ROM_TABLE_PTR   0x48u   /* atom.h:35 ; amdgpu_bios.c:66 */

/* --- atom.h:37,38 : firma "ATOM" dentro del ROM header ------------------- */
/* amdgpu_bios.c:78-79 acepta "ATOM" O "MOTA".
 * atom.c:1574-1576 (amdgpu_atom_parse) SOLO acepta "ATOM".
 * Asimetria real entre las dos comprobaciones: se reproducen las dos. */
#define RX550_ROM_MAGIC_PTR        0x04u   /* atom.h:38 ; atom.c:1575 ; amdgpu_bios.c:72 */
#define RX550_ROM_MAGIC_STR        "ATOM"   /* atom.h:37 */
#define RX550_ROM_MAGIC_ALT        "MOTA"   /* amdgpu_bios.c:79 */

/* --- atom.h:51 y atom.c:1584 : punteros a las tablas maestras ------------- */
#define RX550_ROM_CMD_PTR          0x1Eu   /* atom.h:42 ; atom.c:1582 */
#define RX550_ROM_DATA_PTR         0x20u   /* atom.h:43 ; atom.c:1583 */

/* --- atom.h:33,34 y atom.c:1565-1567 : cadena magica ATI ----------------- */
#define RX550_ATI_MAGIC_PTR        0x30u   /* atom.h:33 ; atom.c:1566 */
#define RX550_ATI_MAGIC_STR        " 761295520" /* atom.h:34 */
#define RX550_ATI_MAGIC_LEN        10u     /* strlen(ATOM_ATI_MAGIC), atom.c:1567 */

/* --- atom.h:32 y atom.c:1560 : 0xAA55 en el offset 0 --------------------- */
#define RX550_ATOM_BIOS_MAGIC      0xAA55u /* atom.h:32 ; atom.c:1560 */

/* --- cadena de parte number, que es de donde sale vbios_version ---------- */
/* atomfirmware.h:221  OFFSET_TO_GET_ATOMBIOS_NUMBER_OF_STRINGS = 0x2f
 * atomfirmware.h:222  OFFSET_TO_GET_ATOMBIOS_STRING_START        = 0x6e
 * atomfirmware.h:223  OFFSET_TO_VBIOS_PART_NUMBER                = 0x80
 * atomfirmware.h:204  BIOS_STRING_LENGTH                         = 43
 * atomfirmware.h:202  BIOS_ATOM_PREFIX                           = "ATOMBIOS"
 * atom.c:1437-1461 (atom_get_vbios_pn)
 * amdgpu_atombios.c:1807-1816 (sysfs vbios_version devuelve ctx->vbios_pn)
 * El driver lee el u16 de 0x6e DESALINEADO (atom.c:1439). Aqui se lee byte a
 * byte en orden little-endian: mismo resultado en x86-64, sin comportamiento
 * indefinido. Decision declarada en el informe. */
#define RX550_STR_NUM_OFF          0x2Fu   /* atomfirmware.h:221 ; atom.c:1437 */
#define RX550_STR_START_OFF        0x6Eu   /* atomfirmware.h:222 ; atom.c:1439 */
#define RX550_PN_FALLBACK_OFF      0x80u   /* atomfirmware.h:223 ; atom.c:1443 */
#define RX550_PN_MAX_LEN           43u     /* atomfirmware.h:204 ; atom.c:1457 */

/* =======================================================================
 * 2. ESTRUCTURAS DEL ATOMBIOS
 *
 * Todas con #pragma pack(1) en atombios.h:191. Para las estructuras usadas
 * aqui, el empaquetado y la alineacion natural coinciden byte a byte porque
 * cada miembro sigue a otro del mismo o de mayor tamano y alineacion, de modo
 * que los offsets son los mismos en atombios.h (empaquetado) y en
 * atomfirmware.h (sin empaquetar). Ese hecho es la razon por la que un mismo
 * offset puede citarse contra dos cabeceras sin contradecirse en la cabecera.
 * ======================================================================= */

/* --- ATOM_COMMON_TABLE_HEADER, atombios.h:208-214 ----------------------- */
#define RX550_CTH_SIZE_OFF         0x00u   /* usStructureSize,        atombios.h:210 */
#define RX550_CTH_FREV_OFF         0x02u   /* ucTableFormatRevision,  atombios.h:211 */
#define RX550_CTH_CREV_OFF         0x03u   /* ucTableContentRevision, atombios.h:212 */
#define RX550_CTH_SIZE             4u      /* = offsetof de ListOfDataTables, atombios.h:2824 */

/* --- ATOM_ROM_HEADER, atombios.h:219-239 -------------------------------- */
#define RX550_ROMH_SIZE            0x00u   /* usStructureSize,       atombios.h:221 */
#define RX550_ROMH_FREV            0x02u   /* ucTableFormatRevision, atombios.h:211 */
#define RX550_ROMH_CREV            0x03u   /* ucTableContentRevision,atombios.h:212 */
#define RX550_ROMH_SIGNATURE       0x04u   /* uaFirmWareSignature[4],atombios.h:222 */
#define RX550_ROMH_RUNTIME_SEG     0x08u   /* usBiosRuntimeSegmentAddress, atombios.h:224 */
#define RX550_ROMH_PROTMODE_OFF    0x0Au   /* usProtectedModeInfoOffset,  atombios.h:225 */
#define RX550_ROMH_CFGFILE_OFF     0x0Cu   /* usConfigFilenameOffset,     atombios.h:226 */
#define RX550_ROMH_CRC_BLOCK_OFF   0x0Eu   /* usCRC_BlockOffset,          atombios.h:227 */
#define RX550_ROMH_BOOTUP_MSG_OFF  0x10u   /* usBIOS_BootupMessageOffset, atombios.h:228 */
#define RX550_ROMH_INT10_OFF       0x12u   /* usInt10Offset,              atombios.h:229 */
#define RX550_ROMH_PCIBUSDEV_OFF   0x14u   /* usPciBusDevInitCode,        atombios.h:230 */
#define RX550_ROMH_IOBASE          0x16u   /* usIoBaseAddress,            atombios.h:231 */
#define RX550_ROMH_SUBSYS_VENDOR   0x18u   /* usSubsystemVendorID,        atombios.h:232 */
#define RX550_ROMH_SUBSYS_ID       0x1Au   /* usSubsystemID,              atombios.h:233 */
#define RX550_ROMH_PCI_INFO_OFF    0x1Cu   /* usPCI_InfoOffset,           atombios.h:234 */
#define RX550_ROMH_MASTER_CMD_OFF  0x1Eu   /* usMasterCommandTableOffset, atombios.h:235 */
#define RX550_ROMH_MASTER_DATA_OFF 0x20u   /* usMasterDataTableOffset,    atombios.h:236 */
#define RX550_ROMH_EXT_FUNC_CODE   0x22u   /* ucExtendedFunctionCode,     atombios.h:237 */
#define RX550_ROMH_RESERVED        0x23u   /* ucReserved,                atombios.h:238 */
#define RX550_ROMH_TOTAL           36u     /* = sizeof de V2_1 menos PSP, atombios.h:239 */

/* ATOM_ROM_HEADER_V2_1, atombios.h:242-263, anade un u32.
 * NO se decodifica: el driver no lo lee en amdgpu_atom_parse (atom.c:1590-1599
 * solo usa usMasterDataTableOffset). Marcado NO_DERIVADO_ PARA ESTE USO. */
#define RX550_ROMH_V21_PSP_OFF     0x24u   /* ulPSPDirTableOffset, atombios.h:262 */

/* --- Tabla maestra de datos: ATOM_MASTER_DATA_TABLE --------------------- */
/* atom.c:1591-1593  master_table = CSTR(atom_rom_header->usMasterDataTableOffset)
 * atom.c:1647-1651  idx = CU16(ctx->data_table + index*2 + 4)
 * atom.c:1648       mdt = (u16 *)(ctx->bios + ctx->data_table + 4)
 * atom.c:1650       if (!mdt[index]) return false
 * La entrada N del master esta en data_table + 4 + N*2. El offset DENTRO de la
 * entrada es relativo a bios, no a la tabla maestra. Cita atom.c:1647,1649,1659. */

/* --- Indices de la tabla maestra de datos -------------------------------- */
/* amdgpu_atombios.c:734  GetIndexIntoMasterTable(DATA, GFX_Info)
 * atombios.h:7151        offsetof(ATOM_MASTER_LIST_OF_DATA_TABLES, FieldName)/sizeof(USHORT)
 * atombios.h:2799        GFX_Info es el miembro numero 14 (0-based) de
 *                         ATOM_MASTER_LIST_OF_DATA_TABLES
 * Corroboracion independiente: atomfirmware.h:390-426 define
 * atom_master_list_of_data_tables_v2_1 con gfx_info tambien en la posicion 14.
 * El indice 14 se verifica contando los miembros; se declara aqui como
 * RX550_IDX_GFX_INFO. */
#define RX550_IDX_GFX_INFO         14u     /* amdgpu_atombios.c:734 ; atombios.h:2799 */
#define RX550_IDX_FIRMWARE_INFO    4u      /* amdgpu_atombios.c:581 ; atombios.h:2789 */
#define RX550_MASTER_ENTRY_SIZE    2u      /* USHORT, atombios.h:2785..2819 */

/* --- ATOM_GFX_INFO_V2_1, atombios.h:5647-5658 ---------------------------- */
/* amdgpu_atombios.c:727-729   union gfx_info { ATOM_GFX_INFO_V2_1 info; }
 * amdgpu_atombios.c:741-742   gfx_info = (union gfx_info *)(bios + data_offset)
 * amdgpu_atombios.c:744-750   las seis copias de campo, en este orden */
#define RX550_GFX_SIZE_OFF         0x00u   /* usStructureSize,        atombios.h:5649,5650 */
#define RX550_GFX_FREV_OFF         0x02u   /* ucTableFormatRevision,  atom.c:1656 */
#define RX550_GFX_CREV_OFF         0x03u   /* ucTableContentRevision, atom.c:1658 */
#define RX550_GFX_IPMIN            0x04u   /* GfxIpMinVer,   atombios.h:5650 */
#define RX550_GFX_IPMAJ            0x05u   /* GfxIpMajVer,   atombios.h:5651 */
#define RX550_GFX_MAX_SE           0x06u   /* max_shader_engines,
                                               amdgpu_atombios.c:744 ; atombios.h:5652 */
#define RX550_GFX_MAX_TP           0x07u   /* max_tile_pipes, amdgpu_atombios.c:745 ;
                                               atombios.h:5653 ; CONTRASTE con
                                               atomfirmware.h:1844 (reserved) en crev>=4 */
#define RX550_GFX_MAX_CU_PER_SH    0x08u   /* max_cu_per_sh, amdgpu_atombios.c:746 ;
                                               atombios.h:5654 */
#define RX550_GFX_MAX_SH_PER_SE    0x09u   /* max_sh_per_se, amdgpu_atombios.c:747 ;
                                               atombios.h:5655 */
#define RX550_GFX_MAX_BACKENDS     0x0Au   /* max_backends_per_se, amdgpu_atombios.c:748 ;
                                               atombios.h:5656 */
#define RX550_GFX_MAX_TCC          0x0Bu   /* max_texture_channel_caches,
                                               amdgpu_atombios.c:749-750 ; atombios.h:5657 */
#define RX550_GFX_V21_TOTAL        12u     /* atombios.h:5647-5658 */

/* --- Extension de ATOM_GFX_INFO_V2_3, atombios.h:5660-5675 --------------- */
#define RX550_GFX23_LEAKAGE_THR    0x0Cu   /* usHiLoLeakageThreshold,   atombios.h:5671 */
#define RX550_GFX23_LO_DPM7_OFF    0x0Eu   /* usEdcDidtLoDpm7TableOffset, atombios.h:5672 */
#define RX550_GFX23_HI_DPM7_OFF    0x10u   /* usEdcDidtHiDpm7TableOffset, atombios.h:5673 */
#define RX550_GFX23_RESERVED0      0x12u   /* usReserverd[0],            atombios.h:5674 */
#define RX550_GFX23_RESERVED1      0x14u   /* usReserverd[1],            atombios.h:5674 */
#define RX550_GFX23_RESERVED2      0x16u   /* usReserverd[2],            atombios.h:5674 */
#define RX550_GFX23_TOTAL          24u

/* --- Extension de atom_gfx_info_v2_4, atomfirmware.h:1838-1872 ----------- */
#define RX550_GFX24_CP_DMA_SRC     0x0Cu   /* regaddr_cp_dma_src_addr,      atomfirmware.h:1848 */
#define RX550_GFX24_CP_DMA_SRC_HI  0x10u   /* regaddr_cp_dma_src_addr_hi,   atomfirmware.h:1849 */
#define RX550_GFX24_CP_DMA_DST     0x14u   /* regaddr_cp_dma_dst_addr,      atomfirmware.h:1850 */
#define RX550_GFX24_CP_DMA_DST_HI  0x18u   /* regaddr_cp_dma_dst_addr_hi,   atomfirmware.h:1851 */
#define RX550_GFX24_CP_DMA_CMD     0x1Cu   /* regaddr_cp_dma_command,       atomfirmware.h:1852 */
#define RX550_GFX24_CP_STATUS      0x20u   /* regaddr_cp_status,            atomfirmware.h:1853 */
#define RX550_GFX24_RLC_GPU_CLK32  0x24u   /* regaddr_rlc_gpu_clock_32,     atomfirmware.h:1854 */
#define RX550_GFX24_RLC_TIMER_REF  0x28u   /* rlc_gpu_timer_refclk,         atomfirmware.h:1855 */
#define RX550_GFX24_ACTIVE_CU_SH   0x2Cu   /* active_cu_per_sh,             atomfirmware.h:1857 */
#define RX550_GFX24_ACTIVE_RB_SE   0x2Du   /* active_rb_per_se,             atomfirmware.h:1858 */
#define RX550_GFX24_GCGOLDENOFF    0x2Eu   /* gcgoldenoffset,               atomfirmware.h:1859 */
#define RX550_GFX24_NUM_GPRS       0x30u   /* gc_num_gprs,                  atomfirmware.h:1860 */
#define RX550_GFX24_GSPRIM_DEPTH   0x32u   /* gc_gsprim_buff_depth,         atomfirmware.h:1861 */
#define RX550_GFX24_PARAM_CACHE    0x34u   /* gc_parameter_cache_depth,     atomfirmware.h:1862 */
#define RX550_GFX24_WAVE_SIZE      0x36u   /* gc_wave_size,                 atomfirmware.h:1863 */
#define RX550_GFX24_WAVES_PER_SIMD 0x38u   /* gc_max_waves_per_simd,        atomfirmware.h:1864 */
#define RX550_GFX24_LDS_SIZE       0x3Au   /* gc_lds_size,                  atomfirmware.h:1865 */
#define RX550_GFX24_MAX_GS_THDS    0x3Cu   /* gc_num_max_gs_thds,           atomfirmware.h:1866 */
#define RX550_GFX24_GS_TBL_DEPTH   0x3Du   /* gc_gs_table_depth,            atomfirmware.h:1867 */
#define RX550_GFX24_DOUBLE_OFFCHIP 0x3Eu   /* gc_double_offchip_lds_buffer, atomfirmware.h:1868 */
#define RX550_GFX24_SCRATCH_SLOTS  0x3Fu   /* gc_max_scratch_slots_per_cu,  atomfirmware.h:1869 */
#define RX550_GFX24_SRAM_RM_FUSES  0x40u   /* sram_rm_fuses_val,            atomfirmware.h:1870 */
#define RX550_GFX24_SRAM_CUS_FUSES 0x44u   /* sram_custom_rm_fuses_val,    atomfirmware.h:1871 */
#define RX550_GFX24_TOTAL          72u

/* --- Extension de atom_gfx_info_v2_7, atomfirmware.h:1880-1913 ----------- */
#define RX550_GFX27_CUT_CU         0x48u   /* cut_cu,                atomfirmware.h:1907 */
#define RX550_GFX27_ACTIVE_CU_TOT  0x49u   /* active_cu_total,       atomfirmware.h:1908 */
#define RX550_GFX27_CU_RESERVED0   0x4Au   /* cu_reserved[0],        atomfirmware.h:1909 */
#define RX550_GFX27_CU_RESERVED1   0x4Bu   /* cu_reserved[1],        atomfirmware.h:1909 */
#define RX550_GFX27_GC_CONFIG      0x4Cu   /* gc_config,             atomfirmware.h:1910 */
#define RX550_GFX27_INACT_CU_SE0   0x50u   /* inactive_cu_per_se[0], atomfirmware.h:1911 */
#define RX550_GFX27_TOTAL          112u    /* 4+8+32+24+8+24+... hasta reserved2[6] */

/* --- ATOM_FIRMWARE_INFO, atombios.h:2948-2980 --------------------------- */
/* Solo se decodifica el prefijo que se cita de forma individual. El resto se
 * marca NO_DERIVADO_ en este decodificador por decision de alcance. */
#define RX550_FWI_FW_REVISION      0x04u   /* ulFirmwareRevision,      atombios.h:2951 ;
                                               atom.c:1597 */
#define RX550_FWI_DEF_SCLK         0x08u   /* ulDefaultEngineClock,   atombios.h:2952 ;
                                               amdgpu_atombios.c:682 */
#define RX550_FWI_DEF_MCLK         0x0Cu   /* ulDefaultMemoryClock,   atombios.h:2953 ;
                                               amdgpu_atombios.c:684 */
#define RX550_FWI_TGT_SCLK         0x10u   /* ulDriverTargetEngineClock, atombios.h:2954 */
#define RX550_FWI_TGT_MCLK         0x14u   /* ulDriverTargetMemoryClock, atombios.h:2955 */
#define RX550_FWI_MAX_SCLK_PLLOUT  0x18u   /* ulMaxEngineClockPLL_Output, atombios.h:2956 ;
                                               amdgpu_atombios.c:643 */
#define RX550_FWI_MAX_MCLK_PLLOUT  0x1Cu   /* ulMaxMemoryClockPLL_Output, atombios.h:2957 ;
                                               amdgpu_atombios.c:670 */
#define RX550_FWI_MAX_PCLK_PLLOUT  0x20u   /* ulMaxPixelClockPLL_Output,  atombios.h:2958 ;
                                               amdgpu_atombios.c:603 */
#define RX550_FWI_ASIC_MAX_SCLK    0x24u   /* ulASICMaxEngineClock,   atombios.h:2959 */
#define RX550_FWI_ASIC_MAX_MCLK    0x28u   /* ulASICMaxMemoryClock,   atombios.h:2960 */
#define RX550_FWI_ASIC_MAX_TEMP    0x2Cu   /* ucASICMaxTemperature,   atombios.h:2961 */
#define RX550_FWI_PREFIX_TOTAL     45u     /* hasta el fin de ucASICMaxTemperature */

/* =======================================================================
 * 3. LIMITE DE LA DECLARACION
 *
 * Ningun campo de este descodificador ha sido visto en una ROM real. Todos los
 * offsets provienen de leer el codigo del driver, no de observar firmware.
 * ======================================================================= */

/* Tamano de la ROM sintetica del self-test.
 * 131072 B = 128 KiB, que es el tamano MEDIDO de BAR6 en esta maquina
 * (hallazgo 1053). Se usa para los vectores que no son de truncado.
 * RX550_SYNTH_SMALL_SIZE se usa para el vector de trunca a la mitad, porque
 * ver la nota de LIMITACION_16_BITS_DE_LA_CADENA_DE_OFFSETS mas abajo. */
#define RX550_SYNTH_ROM_SIZE       131072u
#define RX550_SYNTH_SMALL_SIZE     0x0C00u  /* 3072 B: la mitad cae en FirmwareInfo */
#define RX550_SYNTH_MIN_SIZE       0x0B00u  /* minimo que el constructor escribe */

/* LIMITACION_16_BITS_DE_LA_CADENA_DE_OFFSETS, medido sobre el fuente y NO
 * supuesto: atombios.h:2785 declara cada entrada de ATOM_MASTER_LIST_OF_DATA_
 * TABLES como USHORT, y atom.c:1647 la lee con CU16assigned a un uint16_t.
 * Lo mismo con data_table, que atom.h:43 lee como CU16 en atom.c:1583, y con
 * base, que atom.h:35 lee como CU16 en atom.c:1573.
 * CONSECUENCIA: toda la cadena de offsets del ATOMBIOS cabe en 64 KiB. Una
 * ROM de 128 KiB truncada a 65536 NO es detectably invalida por la estructura
 * del ATOMBIOS, porque toda la estructura sigue dentro de los primeros 64 KiB.
 * Por eso el vector de trunca a la mitad usa una ROM pequena. */

/* Posiciones dentro de la ROM sintetica. Se declaran aqui para que el
 * constructor y las comprobaciones compartan una sola fuente. */
#define RX550_SYNTH_ROMHDR_OFF     0x0200u  /* ATOM_ROM_HEADER, 36 B */
#define RX550_SYNTH_MASTER_OFF     0x0400u  /* ATOM_MASTER_DATA_TABLE */
#define RX550_SYNTH_GFX_OFF        0x0500u  /* ATOM_GFX_INFO_V2_1 / v2_4 */
#define RX550_SYNTH_FWI_OFF        0x0600u  /* ATOM_FIRMWARE_INFO */
#define RX550_SYNTH_PN_OFF         0x0700u  /* cadena de parte number */
#define RX550_SYNTH_SONDA_OFF      0x0900u  /* marcadores de cache, sin campo derivado */
#define RX550_SYNTH_CRC_OFF        0x0A00u  /* CRC-16/ARC del self-test, NO del driver */

/* Valores distinguibles que el vector sintetico planta. */
#define RX550_SYNTH_SE             2u      /* max_shader_engines */
#define RX550_SYNTH_SH_PER_SE      4u      /* max_sh_per_se */
#define RX550_SYNTH_CU_PER_SH      8u      /* max_cu_per_sh */
#define RX550_SYNTH_TP             4u      /* max_tile_pipes */
#define RX550_SYNTH_BACKENDS       2u      /* max_backends_per_se */
#define RX550_SYNTH_TCC            8u      /* max_texture_channel_caches */
#define RX550_SYNTH_L1_KIB         16u     /* TCP L1 por CU, kfd_crat.c:94 */
#define RX550_SYNTH_L2_KIB         2048u   /* SIN campo en GFX_Info: marcador */
#define RX550_SYNTH_BYTES_PER_SLOT 64u     /* lds_size en gfx_v8_0.c:7125, NO del ATOMBIOS */
#define RX550_SYNTH_CU_TOTAL_EXP   (RX550_SYNTH_SE * RX550_SYNTH_SH_PER_SE * RX550_SYNTH_CU_PER_SH)

/* CRC-16/ARC (polinomio 0xA001, reflectado). Lo usa SOLO el self-test para
 * probar que un cambio de un byte se detecta y se localiza. El driver no
 * verifica ningun CRC en esta ruta: no existe comprobacion de CRC en
 * atom.c, amdgpu_atombios.c ni amdgpu_bios.c. Ver vector V11 del informe. */
#define RX550_CRC_POLY            0xA001u

#endif /* RX550_ATOM_DEC_H */
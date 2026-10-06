/* SPDX-License-Identifier: GPL-2.0-only */
/*
 * rx550_smc.h — acceso al SMC por el mailbox INDEX_11/DATA_11.
 *
 * TARGET = RX 550 (1002:699F, Polaris12, GFX8, rev C7)
 * SCOPE  = EXCLUSIVO
 *
 * CADENA PRODUCER→ARTIFACT→CONSUMER (hallazgo 1586 + 1579):
 *   Firmware polaris12_smc.bin, offset 0x130 → SoftRegisters = 0x3FA14
 *   smu7_upload_smc_firmware_data() escribe verbatim en SMC RAM 0x20000
 *   smu7_read_smc_sram_dword(0x20030) = write INDEX_11(0x1AC) + read DATA_11(0x1AD)
 *   polaris10_smumgr.c:2510-2518 lee SoftRegisters y guarda en dpm_table_start
 *
 * REGISTROS DEL MAILBOX (hallazgo 1579):
 *   mmSMC_IND_INDEX_11  = 0x1AC  (byte offset 0x6B0 en BAR5)
 *   mmSMC_IND_DATA_11   = 0x1AD  (byte offset 0x6B4 en BAR5)
 *   mmSMC_IND_ACCESS_CNTL tiene 4 direcciones según cabecera; en nuestro
 *   camino (GFX8/GMC 8.1) es 0x92. AUTO_INCREMENT_IND_11 bit se enciende
 *   SOLO para la subida del firmware (smu7_upload_smc_firmware_data) y se
 *   apaga tras la copia. Por defecto = 0.
 *
 * OFFSETS VERBATIM DEL FIRMWARE (hallazgo 1586):
 *   SMC_RAM base de carga = 0x20000
 *   SoftRegisters       = 0x3FA14  (file offset 0x130 = SMC 0x20030)
 *   DpmTable            = 0x3F294  (file offset 0x134 = SMC 0x20034)
 *   sizeof(SMU74_SoftRegisters) = 120 = 0x78  (hallazgo 1578)
 *   sizeof(SMU74_Discrete_DpmTable) = 1884 = 0x75C  (hallazgo 081)
 */
#ifndef RX550_SMC_H
#define RX550_SMC_H

#include "rx550_mmio.h"

/* ─────────────────────────────────────────────────────────────────────────────
 * REGISTROS DEL MAILBOX SMC (ÍNDICES, NO OFFSETS)
 * ───────────────────────────────────────────────────────────────────────────── */
#define RX550_SMC_IND_INDEX_11      0x1ACu
#define RX550_SMC_IND_DATA_11       0x1ADu
#define RX550_SMC_IND_ACCESS_CNTL   0x92u   /* GFX8 / GMC 8.1 path (hallazgo 1579) */

/* ─────────────────────────────────────────────────────────────────────────────
 * SMC_IND_ACCESS_CNTL — campo AUTO_INCREMENT_IND_11
 * ───────────────────────────────────────────────────────────────────────────── */
#define RX550_SMC_AUTO_INC_SHIFT    0u
#define RX550_SMC_AUTO_INC_MASK     (1u << RX550_SMC_AUTO_INC_SHIFT)

/* ─────────────────────────────────────────────────────────────────────────────
 * DIRECCIONES SMC RAM CONCRETAS (hallazgo 1586, firmware polaris12_smc.bin)
 * ───────────────────────────────────────────────────────────────────────────── */
#define RX550_SMC_FIRMWARE_HEADER_BASE  0x20000u
#define RX550_SMC_SOFTREGISTERS_ADDR    0x3FA14u  /* = 0x20000 + 0x30 (SoftRegisters field) */
#define RX550_SMC_DPMTABLE_ADDR         0x3F294u  /* = 0x20000 + 0x34 (DpmTable field) */

/* ─────────────────────────────────────────────────────────────────────────────
 * TAMAÑOS ESTRUCTURAS (hallazgos 1578, 081)
 * ───────────────────────────────────────────────────────────────────────────── */
#define RX550_SMC_SOFTREGS_SIZE       120u    /* 0x78 */
#define RX550_SMC_DPMTABLE_SIZE       1884u   /* 0x75C */

/* ─────────────────────────────────────────────────────────────────────────────
 * SOFTREGISTERS — OFFSETS INTERNOS (desde 0x3FA14, hallazgo 1583)
 * ───────────────────────────────────────────────────────────────────────────── */
#define RX550_SOFTREG_SYSTEMFLAGS           0u
#define RX550_SOFTREG_VRCONFIG              4u
#define RX550_SOFTREG_GFXBOOTLEVEL          8u
#define RX550_SOFTREG_GFXVOLTCHGEN          9u
#define RX550_SOFTREG_GFXTHERMTHREN         10u
#define RX550_SOFTREG_GFXINTERVAL           11u
#define RX550_SOFTREG_VOLTINTERVAL          12u
#define RX550_SOFTREG_THERMINTERVAL         13u
#define RX550_SOFTREG_TEMPLIMITHIGH         14u
#define RX550_SOFTREG_TEMPLIMITLOW          16u
#define RX550_SOFTREG_MEMBROOTLEVEL         18u
#define RX550_SOFTREG_MEMVOLTCHGEN          19u
#define RX550_SOFTREG_BOOTMVDD              20u
#define RX550_SOFTREG_MEMINTERVAL           22u
#define RX550_SOFTREG_MEMTHERMTHREN         23u
#define RX550_SOFTREG_VOLTRESPTIME          24u
#define RX550_SOFTREG_PHASERESPTIME         26u
#define RX550_SOFTREG_PCIEBOOTLINKLEVEL     28u
#define RX550_SOFTREG_PCIEGENINTERVAL       29u
#define RX550_SOFTREG_DTEINTERVAL           30u
#define RX550_SOFTREG_DTEMODE               31u
#define RX550_SOFTREG_SVI2ENABLE            32u
#define RX550_SOFTREG_VRHOTGPIO             33u
#define RX550_SOFTREG_ACDCGPIO              34u
#define RX550_SOFTREG_THERMGPIO             35u
#define RX550_SOFTREG_PPM_PKGPWRLIMIT       36u
#define RX550_SOFTREG_PPM_TEMPLIMIT         38u
#define RX550_SOFTREG_DEFAULTTDP            40u
#define RX550_SOFTREG_TARGETTDP             42u
#define RX550_SOFTREG_FPSHIGHTHRESH         44u
#define RX550_SOFTREG_FPSLOWTHRESH          46u
#define RX550_SOFTREG_BAPMTI_R              48u   /* 4*5*5*2 = 200 bytes */
#define RX550_SOFTREG_BAPMTI_RC             248u  /* 4*5*5*2 = 200 bytes */
#define RX550_SOFTREG_TEMPLIMITEDGE         448u
#define RX550_SOFTREG_TEMPLIMITHOTSPOT      450u
#define RX550_SOFTREG_BOOTVDDC              452u
#define RX550_SOFTREG_BOOTVDDCI             454u
#define RX550_SOFTREG_FANGAINEDGE           456u
#define RX550_SOFTREG_FANGAINHOTSPOT        458u
#define RX550_SOFTREG_LOWSCLKINTRTHRESH     460u
#define RX550_SOFTREG_VDDGFXRECHKWAIT       464u
#define RX550_SOFTREG_CLKSTRETCHERAMOUNT    468u
#define RX550_SOFTREG_SCLK_CKS_MASTEREN0_7  469u
#define RX550_SOFTREG_SCLK_CKS_MASTEREN8_15 470u
#define RX550_SOFTREG_UVDBOOTLEVEL          484u
#define RX550_SOFTREG_VCEBOOTLEVEL          485u
#define RX550_SOFTREG_ACPBOOTLEVEL          486u
#define RX550_SOFTREG_SAMUBOOTLEVEL         487u

/* DRAM_LOG_ADDR_H está en offset 80 (hallazgo 1583) */
#define RX550_SOFTREG_DRAM_LOG_ADDR_H       80u
#define RX550_SOFTREG_DRAM_LOG_ADDR_L       76u
#define RX550_SOFTREG_DRAM_LOG_PHY_ADDR_H   78u
#define RX550_SOFTREG_DRAM_LOG_PHY_ADDR_L   79u
#define RX550_SOFTREG_DRAM_LOG_BUFF_SIZE    82u
#define RX550_SOFTREG_ULVENTERCOUNT         83u
#define RX550_SOFTREG_ULVTIME               84u
#define RX550_SOFTREG_UCODELOADSTATUS       85u
#define RX550_SOFTREG_ALLOWMVDDSWITCH       86u
#define RX550_SOFTREG_ACTIVITY_WEIGHT       87u

/* ─────────────────────────────────────────────────────────────────────────────
 * DPM TABLE — OFFSETS INTERNOS (desde 0x3F294, hallazgo 1587 + gcc)
 * ───────────────────────────────────────────────────────────────────────────── */
#define RX550_DPM_SYSTEMFLAGS               0u    /* 0x000 */
#define RX550_DPM_VRCONFIG                  4u    /* 0x004 */
#define RX550_DPM_GRAPHICSLEVEL             236u  /* 0x0EC = offsetof(GraphicsLevel) */
#define RX550_DPM_MEMORYLEVEL               708u  /* 0x2C4 = offsetof(MemoryLevel) */
#define RX550_DPM_BOOTMVDD                  1592u /* 0x638 */
#define RX550_DPM_UVDBOOTLEVEL              1576u /* 0x628 */
#define RX550_DPM_VCEBOOTLEVEL              1577u /* 0x629 */
#define RX550_DPM_LOWSCLKINTRTHRESH         1692u /* 0x69C */

/* Tamaños de arrays (hallazgo 113 + gcc) */
#define RX550_DPM_GRAPHICSLEVEL_SIZE        56u   /* sizeof(SMU74_Discrete_GraphicsLevel) */
#define RX550_DPM_MEMORYLEVEL_SIZE          24u   /* sizeof(SMU74_Discrete_MemoryLevel) */
#define RX550_DPM_MAX_LEVELS_GRAPHICS       8u
#define RX550_DPM_MAX_LEVELS_MEMORY         4u

/* ─────────────────────────────────────────────────────────────────────────────
 * ERRORES
 * ───────────────────────────────────────────────────────────────────────────── */
#define RX550_SMC_OK                    0
#define RX550_SMC_ERR_NO_MAP           -1
#define RX550_SMC_ERR_OUT_OF_WINDOW    -2
#define RX550_SMC_ERR_MAP_TOO_SMALL    -3
#define RX550_SMC_ERR_TIMEOUT          -4
#define RX550_SMC_ERR_ADDR_MISALIGNED  -5

/* ─────────────────────────────────────────────────────────────────────────────
 * REGISTROS: helpers estáticos (índices)
 * ───────────────────────────────────────────────────────────────────────────── */
static inline struct rx550_reg rx550_smc_reg_index_11(void)
{
	return rx550_reg_make(RX550_SMC_IND_INDEX_11);
}

static inline struct rx550_reg rx550_smc_reg_data_11(void)
{
	return rx550_reg_make(RX550_SMC_IND_DATA_11);
}

static inline struct rx550_reg rx550_smc_reg_access_cntl(void)
{
	return rx550_reg_make(RX550_SMC_IND_ACCESS_CNTL);
}

/* ─────────────────────────────────────────────────────────────────────────────
 * API PÚBLICA
 * ───────────────────────────────────────────────────────────────────────────── */

/* Configura la dirección SMC en INDEX_11 y AUTO_INCREMENT_IND_11=0/1.
 * Devuelve 0 en éxito, negativo en error de ventana. */
int rx550_smc_set_addr(const struct rx550_mmio_map *map,
		       uint32_t smc_addr, bool auto_inc);

/* Lee un dword desde SMC RAM en smc_addr (con AUTO_INCREMENT=0).
 * Implementa: write INDEX_11, read DATA_11. */
int rx550_smc_read_dword(const struct rx550_mmio_map *map,
			 uint32_t smc_addr, uint32_t *out_val);

/* Escribe un dword en SMC RAM en smc_addr (con AUTO_INCREMENT=0).
 * Implementa: write INDEX_11, write DATA_11. */
int rx550_smc_write_dword(const struct rx550_mmio_map *map,
			  uint32_t smc_addr, uint32_t val);

/* Copia bytes a SMC RAM con AUTO_INCREMENT=1 (para subida de firmware).
 * smc_start_address debe ser 4-byte aligned. byte_count debe ser múltiplo de 4. */
int rx550_smc_copy_bytes(const struct rx550_mmio_map *map,
			 uint32_t smc_start_address,
			 const uint8_t *src, uint32_t byte_count);

/* Lee SoftRegisters completo (120 bytes) desde 0x3FA14. */
int rx550_smc_read_softregs(const struct rx550_mmio_map *map,
			    uint8_t *dst, uint32_t dst_size);

/* Lee campo específico de SoftRegisters. */
int rx550_smc_read_softreg_field(const struct rx550_mmio_map *map,
				 uint32_t field_offset, uint32_t *out_val);

/* Escribe campo específico de SoftRegisters. */
int rx550_smc_write_softreg_field(const struct rx550_mmio_map *map,
				  uint32_t field_offset, uint32_t val);

/* Lee campo específico de DPM Table (base 0x3F294). */
int rx550_smc_read_dpm_field(const struct rx550_mmio_map *map,
			     uint32_t field_offset, uint32_t *out_val);

/* Escribe campo específico de DPM Table. */
int rx550_smc_write_dpm_field(const struct rx550_mmio_map *map,
			      uint32_t field_offset, uint32_t val);

#endif /* RX550_SMC_H */
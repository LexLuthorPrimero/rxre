// SPDX-License-Identifier: GPL-2.0-only
/*
 * rx550_smc.c — implementación del acceso SMC por mailbox INDEX_11/DATA_11.
 *
 * TARGET = RX 550 (1002:699F, Polaris12, GFX8, rev C7)
 * SCOPE  = EXCLUSIVO
 *
 * IMPLEMENTA: smu7_set_smc_sram_address() + smu7_read_smc_sram_dword() +
 *             smu7_write_smc_sram_dword() + smu7_copy_bytes_to_smc()
 * FUENTE: smu7_smumgr.c:38-112, 229-252, 418-435
 */

#ifdef __KERNEL__
#include <linux/io.h>
#else
#include <string.h>
#endif

#include "rx550_smc.h"

/* ─────────────────────────────────────────────────────────────────────────────
 * IMPLEMENTACIÓN PRIVADA: set address + opcional auto_increment
 * ───────────────────────────────────────────────────────────────────────────── */
static int rx550_smc_do_set_addr(const struct rx550_mmio_map *map,
				 uint32_t smc_addr, bool auto_inc)
{
	if (!map || !map->mapped)
		return RX550_SMC_ERR_NO_MAP;

	/* SMC address must be 4-byte aligned (smu7_smumgr.c:40) */
	if ((smc_addr & 3u) != 0u)
		return RX550_SMC_ERR_ADDR_MISALIGNED;

	/* Check window before accessing */
	struct rx550_reg reg_idx = rx550_smc_reg_index_11();
	struct rx550_reg reg_dat = rx550_smc_reg_data_11();
	struct rx550_reg reg_cntl = rx550_smc_reg_access_cntl();

	if (!rx550_mmio_map_in_window(map, reg_idx) ||
	    !rx550_mmio_map_in_window(map, reg_dat) ||
	    !rx550_mmio_map_in_window(map, reg_cntl))
		return RX550_SMC_ERR_OUT_OF_WINDOW;

	/* Write SMC address to INDEX_11 */
#ifdef __KERNEL__
	writel(smc_addr, (void __iomem *)(map->base + rx550_reg_offset(reg_idx).bytes));
#else
	*(volatile uint32_t *)(map->base + rx550_reg_offset(reg_idx).bytes) = smc_addr;
#endif

	/* Set AUTO_INCREMENT_IND_11: 0 for normal access, 1 for firmware upload */
	uint32_t cntl_val = auto_inc ? RX550_SMC_AUTO_INC_MASK : 0u;
#ifdef __KERNEL__
	writel(cntl_val, (void __iomem *)(map->base + rx550_reg_offset(reg_cntl).bytes));
#else
	*(volatile uint32_t *)(map->base + rx550_reg_offset(reg_cntl).bytes) = cntl_val;
#endif

	return RX550_SMC_OK;
}

/* ─────────────────────────────────────────────────────────────────────────────
 * API PÚBLICA
 * ───────────────────────────────────────────────────────────────────────────── */
int rx550_smc_set_addr(const struct rx550_mmio_map *map,
		       uint32_t smc_addr, bool auto_inc)
{
	return rx550_smc_do_set_addr(map, smc_addr, auto_inc);
}

int rx550_smc_read_dword(const struct rx550_mmio_map *map,
			 uint32_t smc_addr, uint32_t *out_val)
{
	int rc = rx550_smc_do_set_addr(map, smc_addr, false);
	if (rc)
		return rc;

	struct rx550_reg reg_dat = rx550_smc_reg_data_11();
#ifdef __KERNEL__
	*out_val = readl((void __iomem *)(map->base + rx550_reg_offset(reg_dat).bytes));
#else
	*out_val = *(volatile uint32_t *)(map->base + rx550_reg_offset(reg_dat).bytes);
#endif
	return RX550_SMC_OK;
}

int rx550_smc_write_dword(const struct rx550_mmio_map *map,
			  uint32_t smc_addr, uint32_t val)
{
	int rc = rx550_smc_do_set_addr(map, smc_addr, false);
	if (rc)
		return rc;

	struct rx550_reg reg_dat = rx550_smc_reg_data_11();
#ifdef __KERNEL__
	writel(val, (void __iomem *)(map->base + rx550_reg_offset(reg_dat).bytes));
#else
	*(volatile uint32_t *)(map->base + rx550_reg_offset(reg_dat).bytes) = val;
#endif
	return RX550_SMC_OK;
}

int rx550_smc_copy_bytes(const struct rx550_mmio_map *map,
			 uint32_t smc_start_address,
			 const uint8_t *src, uint32_t byte_count)
{
	if (!map || !map->mapped)
		return RX550_SMC_ERR_NO_MAP;
	if ((smc_start_address & 3u) != 0u)
		return RX550_SMC_ERR_ADDR_MISALIGNED;
	if ((byte_count & 3u) != 0u)
		return RX550_SMC_ERR_ADDR_MISALIGNED; /* must be multiple of 4 */

	/* SMC_RAM_END from vegam_smumgr.h:32 = 0x40000 */
	if (smc_start_address + byte_count > 0x40000u)
		return RX550_SMC_ERR_OUT_OF_WINDOW;

	/* Set INDEX_11 with AUTO_INCREMENT=1 */
	int rc = rx550_smc_do_set_addr(map, smc_start_address, true);
	if (rc)
		return rc;

	struct rx550_reg reg_dat = rx550_smc_reg_data_11();
	uint32_t addr = smc_start_address;

	/* Bytes are written with MSB first (smu7_smumgr.c:65) */
	for (; byte_count >= 4; byte_count -= 4) {
		uint32_t data = (uint32_t)src[0] << 24 |
				(uint32_t)src[1] << 16 |
				(uint32_t)src[2] << 8  |
				(uint32_t)src[3];
#ifdef __KERNEL__
		writel(data, (void __iomem *)(map->base + rx550_reg_offset(reg_dat).bytes));
#else
		*(volatile uint32_t *)(map->base + rx550_reg_offset(reg_dat).bytes) = data;
#endif
		src += 4;
		addr += 4;
	}

	/* Disable auto-increment after copy (smu7_smumgr.c:430) */
	struct rx550_reg reg_cntl = rx550_smc_reg_access_cntl();
#ifdef __KERNEL__
	writel(0, (void __iomem *)(map->base + rx550_reg_offset(reg_cntl).bytes));
#else
	*(volatile uint32_t *)(map->base + rx550_reg_offset(reg_cntl).bytes) = 0;
#endif

	return RX550_SMC_OK;
}

int rx550_smc_read_softregs(const struct rx550_mmio_map *map,
			    uint8_t *dst, uint32_t dst_size)
{
	if (!dst || dst_size < RX550_SMC_SOFTREGS_SIZE)
		return RX550_SMC_ERR_OUT_OF_WINDOW;

	/* Read 30 dwords (120 bytes) from 0x3FA14 */
	uint32_t *dst32 = (uint32_t *)dst;
	for (uint32_t i = 0; i < RX550_SMC_SOFTREGS_SIZE / 4; i++) {
		uint32_t val;
		int rc = rx550_smc_read_dword(map, RX550_SMC_SOFTREGISTERS_ADDR + i * 4, &val);
		if (rc)
			return rc;
		dst32[i] = val;
	}
	return RX550_SMC_OK;
}

int rx550_smc_read_softreg_field(const struct rx550_mmio_map *map,
				 uint32_t field_offset, uint32_t *out_val)
{
	if (field_offset >= RX550_SMC_SOFTREGS_SIZE)
		return RX550_SMC_ERR_OUT_OF_WINDOW;
	return rx550_smc_read_dword(map, RX550_SMC_SOFTREGISTERS_ADDR + field_offset, out_val);
}

int rx550_smc_write_softreg_field(const struct rx550_mmio_map *map,
				  uint32_t field_offset, uint32_t val)
{
	if (field_offset >= RX550_SMC_SOFTREGS_SIZE)
		return RX550_SMC_ERR_OUT_OF_WINDOW;
	return rx550_smc_write_dword(map, RX550_SMC_SOFTREGISTERS_ADDR + field_offset, val);
}

int rx550_smc_read_dpm_field(const struct rx550_mmio_map *map,
			     uint32_t field_offset, uint32_t *out_val)
{
	if (field_offset >= RX550_SMC_DPMTABLE_SIZE)
		return RX550_SMC_ERR_OUT_OF_WINDOW;
	return rx550_smc_read_dword(map, RX550_SMC_DPMTABLE_ADDR + field_offset, out_val);
}

int rx550_smc_write_dpm_field(const struct rx550_mmio_map *map,
			      uint32_t field_offset, uint32_t val)
{
	if (field_offset >= RX550_SMC_DPMTABLE_SIZE)
		return RX550_SMC_ERR_OUT_OF_WINDOW;
	return rx550_smc_write_dword(map, RX550_SMC_DPMTABLE_ADDR + field_offset, val);
}
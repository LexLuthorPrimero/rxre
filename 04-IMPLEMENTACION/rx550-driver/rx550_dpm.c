// SPDX-License-Identifier: GPL-2.0-only
/*
 * rx550_dpm.c — DPM operations via SMC mailbox.
 *
 * TARGET = RX 550 (1002:699F, Polaris12, GFX8, rev C7)
 * SCOPE  = EXCLUSIVO
 *
 * IMPLEMENTA: polaris10_setup_gfx_lvl_struct, polaris10_populate_smc_*,
 *             polaris10_upload_dpm_data, polaris10_update_*_smc_table
 * FUENTE: polaris10_smumgr.c líneas 140-170, 1046-1060, 1215-1235,
 *         2119-2123, 2292-2301, 2328-2337, 2400-2406, 2594-2600
 *
 * REGLA DE COORDENADAS (hallazgo 113, confirmado 1587):
 *   smc_addr = RX550_DPM_TABLE_BASE + offsetof(campo)
 *   SIN +108 / -108.  La struct del host modela la imagen del firmware.
 */

#include "rx550_dpm.h"
#include "rx550_smc.h"

/* ─────────────────────────────────────────────────────────────────────────────
 * HELPER: read/write SMC field via dpm_table_start + offset
 * ───────────────────────────────────────────────────────────────────────────── */
static inline int rx550_dpm_read_field(const struct rx550_mmio_map *map,
				       uint32_t field_offset, uint32_t *out_val)
{
	return rx550_smc_read_dpm_field(map, field_offset, out_val);
}

static inline int rx550_dpm_write_field(const struct rx550_mmio_map *map,
					uint32_t field_offset, uint32_t val)
{
	return rx550_smc_write_dpm_field(map, field_offset, val);
}

/* ─────────────────────────────────────────────────────────────────────────────
 * VRConfig (4 bytes, offset 112)
 * ───────────────────────────────────────────────────────────────────────────── */
int rx550_dpm_read_vrconfig(const struct rx550_mmio_map *map, uint32_t *out_val)
{
	return rx550_dpm_read_field(map, RX550_DPM_OFF_VRCONFIG, out_val);
}

int rx550_dpm_write_vrconfig(const struct rx550_mmio_map *map, uint32_t val)
{
	return rx550_dpm_write_field(map, RX550_DPM_OFF_VRCONFIG, val);
}

/* ─────────────────────────────────────────────────────────────────────────────
 * GraphicsLevel (array de 8, 56 bytes c/u, offset 236)
 * polaris10_setup_gfx_lvl_struct:147, polaris10_populate_smc_graphics_level:1046,
 * polaris10_apply_state_adjust_rules:2594
 * ───────────────────────────────────────────────────────────────────────────── */
int rx550_dpm_read_graphics_level(const struct rx550_mmio_map *map,
				  uint32_t level,
				  struct rx550_dpm_graphics_level *out)
{
	if (level >= RX550_DPM_MAX_LEVELS_GRAPHICS)
		return -1;

	uint32_t base_off = RX550_DPM_OFF_GRAPHICSLEVEL + level * RX550_DPM_GRAPHICSLEVEL_SIZE;
	uint32_t *dst = (uint32_t *)out;

	for (uint32_t i = 0; i < RX550_DPM_GRAPHICSLEVEL_SIZE / 4; i++) {
		int rc = rx550_dpm_read_field(map, base_off + i * 4, &dst[i]);
		if (rc)
			return rc;
	}
	return 0;
}

int rx550_dpm_write_graphics_level(const struct rx550_mmio_map *map,
				   uint32_t level,
				   const struct rx550_dpm_graphics_level *in)
{
	if (level >= RX550_DPM_MAX_LEVELS_GRAPHICS)
		return -1;

	uint32_t base_off = RX550_DPM_OFF_GRAPHICSLEVEL + level * RX550_DPM_GRAPHICSLEVEL_SIZE;
	const uint32_t *src = (const uint32_t *)in;

	for (uint32_t i = 0; i < RX550_DPM_GRAPHICSLEVEL_SIZE / 4; i++) {
		int rc = rx550_dpm_write_field(map, base_off + i * 4, src[i]);
		if (rc)
			return rc;
	}
	return 0;
}

/* ─────────────────────────────────────────────────────────────────────────────
 * MemoryLevel (array de 4, 24 bytes c/u, offset 708)
 * polaris10_setup_gfx_lvl_struct:155, polaris10_populate_smc_memory_level:1215,
 * polaris10_apply_state_adjust_rules:2597
 * ───────────────────────────────────────────────────────────────────────────── */
int rx550_dpm_read_memory_level(const struct rx550_mmio_map *map,
				uint32_t level,
				struct rx550_dpm_memory_level *out)
{
	if (level >= RX550_DPM_MAX_LEVELS_MEMORY)
		return -1;

	uint32_t base_off = RX550_DPM_OFF_MEMORYLEVEL + level * RX550_DPM_MEMORYLEVEL_SIZE;
	uint32_t *dst = (uint32_t *)out;

	for (uint32_t i = 0; i < RX550_DPM_MEMORYLEVEL_SIZE / 4; i++) {
		int rc = rx550_dpm_read_field(map, base_off + i * 4, &dst[i]);
		if (rc)
			return rc;
	}
	return 0;
}

int rx550_dpm_write_memory_level(const struct rx550_mmio_map *map,
				 uint32_t level,
				 const struct rx550_dpm_memory_level *in)
{
	if (level >= RX550_DPM_MAX_LEVELS_MEMORY)
		return -1;

	uint32_t base_off = RX550_DPM_OFF_MEMORYLEVEL + level * RX550_DPM_MEMORYLEVEL_SIZE;
	const uint32_t *src = (const uint32_t *)in;

	for (uint32_t i = 0; i < RX550_DPM_MEMORYLEVEL_SIZE / 4; i++) {
		int rc = rx550_dpm_write_field(map, base_off + i * 4, src[i]);
		if (rc)
			return rc;
	}
	return 0;
}

/* ─────────────────────────────────────────────────────────────────────────────
 * BootMVdd (2 bytes, offset 1592) — polaris10_setup_gfx_lvl_struct:164
 * ───────────────────────────────────────────────────────────────────────────── */
int rx550_dpm_read_boot_mvdd(const struct rx550_mmio_map *map, uint16_t *out_val)
{
	uint32_t val;
	int rc = rx550_dpm_read_field(map, RX550_DPM_OFF_BOOTMVDD, &val);
	if (rc)
		return rc;
	*out_val = (uint16_t)val;
	return 0;
}

int rx550_dpm_write_boot_mvdd(const struct rx550_mmio_map *map, uint16_t val)
{
	return rx550_dpm_write_field(map, RX550_DPM_OFF_BOOTMVDD, (uint32_t)val);
}

/* ─────────────────────────────────────────────────────────────────────────────
 * UVD/VCE Boot Level (1 byte c/u, offsets 1576/1577)
 * polaris10_update_uvd_smc_table:2292, polaris10_update_vce_smc_table:2328
 * ───────────────────────────────────────────────────────────────────────────── */
int rx550_dpm_read_uvd_boot_level(const struct rx550_mmio_map *map, uint8_t *out_val)
{
	uint32_t val;
	int rc = rx550_dpm_read_field(map, RX550_DPM_OFF_UVDBOOTLEVEL, &val);
	if (rc)
		return rc;
	*out_val = (uint8_t)val;
	return 0;
}

int rx550_dpm_write_uvd_boot_level(const struct rx550_mmio_map *map, uint8_t val)
{
	return rx550_dpm_write_field(map, RX550_DPM_OFF_UVDBOOTLEVEL, (uint32_t)val);
}

int rx550_dpm_read_vce_boot_level(const struct rx550_mmio_map *map, uint8_t *out_val)
{
	uint32_t val;
	int rc = rx550_dpm_read_field(map, RX550_DPM_OFF_VCEBOOTLEVEL, &val);
	if (rc)
		return rc;
	*out_val = (uint8_t)val;
	return 0;
}

int rx550_dpm_write_vce_boot_level(const struct rx550_mmio_map *map, uint8_t val)
{
	return rx550_dpm_write_field(map, RX550_DPM_OFF_VCEBOOTLEVEL, (uint32_t)val);
}

/* ─────────────────────────────────────────────────────────────────────────────
 * LowSclkInterruptThreshold (4 bytes, offset 1692)
 * polaris10_update_bif_smc_table:2400
 * ───────────────────────────────────────────────────────────────────────────── */
int rx550_dpm_read_low_sclk_threshold(const struct rx550_mmio_map *map, uint32_t *out_val)
{
	return rx550_dpm_read_field(map, RX550_DPM_OFF_LOWSCLKINTRTHRESH, out_val);
}

int rx550_dpm_write_low_sclk_threshold(const struct rx550_mmio_map *map, uint32_t val)
{
	return rx550_dpm_write_field(map, RX550_DPM_OFF_LOWSCLKINTRTHRESH, val);
}

/* ─────────────────────────────────────────────────────────────────────────────
 * UPLOAD TABLA DPM COMPLETA (polaris10_upload_dpm_data:2119-2123)
 * ─────────────────────────────────────────────────────────────────────────────
 * Copia desde SystemFlags (offset 108) hasta el final:
 *   tamaño = sizeof(DPM) - 3*sizeof(PIDController) = 1884 - 108 = 1776 bytes
 *   destino = base + offsetof(SystemFlags) = 0x3F294 + 108 = 0x3F300
 * ───────────────────────────────────────────────────────────────────────────── */
int rx550_dpm_upload_table(const struct rx550_mmio_map *map,
			   const uint8_t *table_src, uint32_t table_size)
{
	if (!table_src || table_size < RX550_DPM_OFF_SYSTEMFLAGS)
		return -1;

	/* Source pointer starts at SystemFlags */
	const uint8_t *src = table_src + RX550_DPM_OFF_SYSTEMFLAGS;
	uint32_t copy_size = table_size - RX550_DPM_OFF_SYSTEMFLAGS;

	/* Must be multiple of 4 for smu7_copy_bytes_to_smc */
	if ((copy_size & 3u) != 0u)
		return -1;

	/* Destination = dpm_table_start + offsetof(SystemFlags) = 0x3F300 */
	return rx550_smc_copy_bytes(map, RX550_DPM_ADDR_SYSTEMFLAGS, src, copy_size);
}
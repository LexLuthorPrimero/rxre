/* SPDX-License-Identifier: GPL-2.0-only */
/*
 * rx550_dpm.h — DPM (Dynamic Power Management) para Polaris12.
 *
 * TARGET = RX 550 (1002:699F, Polaris12, GFX8, rev C7)
 * SCOPE  = EXCLUSIVO
 *
 * FUENTE VERIFICADA (hallazgos 1586, 1587, 113, 081, 1578):
 *   dpm_table_start = DpmTable field en firmware header = 0x3F294
 *   11 usos en polaris10_smumgr.c usan: dpm_table_start + offsetof(campo)
 *   Offsets oficiales (gcc sobre smu74_discrete.h):
 *     SystemFlags = 108 (0x6C)     → 0x3F300
 *     VRConfig = 112 (0x70)        → 0x3F304
 *     GraphicsLevel = 236 (0xEC)   → 0x3F3A4  [array 8 × 56B = 448B]
 *     MemoryLevel = 708 (0x2C4)    → 0x3F56C  [array 4 × 24B = 96B]
 *     BootMVdd = 1592 (0x638)      → 0x3F8D4
 *     UvdBootLevel = 1576 (0x628)  → 0x3F8B4
 *     VceBootLevel = 1577 (0x629)  → 0x3F8B5
 *     LowSclkInterruptThreshold = 1692 (0x69C) → 0x3F93C
 *
 * LA REGLA DE COORDENADAS (hallazgo 113):
 *   smc_addr = dpm_table_start + offsetof(campo)
 *   SIN corrección de +108 / -108.  La struct del host modela exactamente
 *   la imagen en firmware; origen &table->campo y destino base+offsetof
 *   comparten el MISMO offset.  Sumar 108 es el error circular de 211.
 */
#ifndef RX550_DPM_H
#define RX550_DPM_H

#include "rx550_smc.h"

/* ─────────────────────────────────────────────────────────────────────────────
 * BASE ADDRESS (hallazgo 1587)
 * ───────────────────────────────────────────────────────────────────────────── */
#define RX550_DPM_TABLE_BASE      0x3F294u

/* ─────────────────────────────────────────────────────────────────────────────
 * OFFSETS INTERNOS (desde DPM_TABLE_BASE, gcc sobre smu74_discrete.h)
 * ───────────────────────────────────────────────────────────────────────────── */
#define RX550_DPM_OFF_SYSTEMFLAGS       108u    /* 0x06C - inicio región HOST */
#define RX550_DPM_OFF_VRCONFIG          112u    /* 0x070 */
#define RX550_DPM_OFF_GRAPHICSLEVEL     236u    /* 0x0EC */
#define RX550_DPM_OFF_MEMORYLEVEL       708u    /* 0x2C4 */
#define RX550_DPM_OFF_BOOTMVDD          1592u   /* 0x638 */
#define RX550_DPM_OFF_UVDBOOTLEVEL      1576u   /* 0x628 */
#define RX550_DPM_OFF_VCEBOOTLEVEL      1577u   /* 0x629 */
#define RX550_DPM_OFF_LOWSCLKINTRTHRESH 1692u   /* 0x69C */

/* Tamaños de arrays (hallazgo 113 + 081) */
#define RX550_DPM_GRAPHICSLEVEL_SIZE    56u
#define RX550_DPM_MEMORYLEVEL_SIZE      24u
#define RX550_DPM_MAX_LEVELS_GRAPHICS   8u
#define RX550_DPM_MAX_LEVELS_MEMORY     4u

/* Tamaño total de tabla (hallazgo 081) */
#define RX550_DPM_TABLE_SIZE            1884u   /* 0x75C */

/* ─────────────────────────────────────────────────────────────────────────────
 * DIRECCIONES SMC RAM CONCRETAS (para referencia/debug)
 * ───────────────────────────────────────────────────────────────────────────── */
#define RX550_DPM_ADDR_SYSTEMFLAGS       (RX550_DPM_TABLE_BASE + RX550_DPM_OFF_SYSTEMFLAGS)       /* 0x3F300 */
#define RX550_DPM_ADDR_VRCONFIG          (RX550_DPM_TABLE_BASE + RX550_DPM_OFF_VRCONFIG)          /* 0x3F304 */
#define RX550_DPM_ADDR_GRAPHICSLEVEL     (RX550_DPM_TABLE_BASE + RX550_DPM_OFF_GRAPHICSLEVEL)     /* 0x3F3A4 */
#define RX550_DPM_ADDR_MEMORYLEVEL       (RX550_DPM_TABLE_BASE + RX550_DPM_OFF_MEMORYLEVEL)       /* 0x3F56C */
#define RX550_DPM_ADDR_BOOTMVDD          (RX550_DPM_TABLE_BASE + RX550_DPM_OFF_BOOTMVDD)          /* 0x3F8D4 */
#define RX550_DPM_ADDR_UVDBOOTLEVEL      (RX550_DPM_TABLE_BASE + RX550_DPM_OFF_UVDBOOTLEVEL)      /* 0x3F8B4 */
#define RX550_DPM_ADDR_VCEBOOTLEVEL      (RX550_DPM_TABLE_BASE + RX550_DPM_OFF_VCEBOOTLEVEL)      /* 0x3F8B5 */
#define RX550_DPM_ADDR_LOWSCLKINTRTHRESH (RX550_DPM_TABLE_BASE + RX550_DPM_OFF_LOWSCLKINTRTHRESH) /* 0x3F93C */

/* ─────────────────────────────────────────────────────────────────────────────
 * ESTRUCTURAS DE DATOS (mirror de lo que escribe el host)
 * ───────────────────────────────────────────────────────────────────────────── */

/* Graphics Level (8 niveles, 56 bytes c/u) */
struct rx550_dpm_graphics_level {
	uint32_t SclkFrequency;
	uint32_t SclkSetting;
	uint32_t Vddc;
	uint32_t Vddci;
	uint32_t VddGfx;
	uint32_t VddMem;
	uint32_t Mvdd;
	uint32_t MclkFrequency;
	uint32_t EdcCurrent;
	uint32_t PowerContainment;
	uint32_t ActivityLevel;
	uint32_t SclkStepSize;
	uint32_t CurrSclkPllRange;
	uint32_t TemperatureLimitHigh;
	uint32_t TemperatureLimitLow;
};

/* Memory Level (4 niveles, 24 bytes c/u) */
struct rx550_dpm_memory_level {
	uint32_t MclkFrequency;
	uint32_t VddMem;
	uint32_t Vddci;
	uint32_t EdcCurrent;
	uint32_t StrobeRatio;
	uint32_t DisplayWatermark;
};

/* ─────────────────────────────────────────────────────────────────────────────
 * API — coordenada única: base + offsetof (hallazgo 113)
 * ───────────────────────────────────────────────────────────────────────────── */

static inline uint32_t rx550_dpm_smc_addr(uint32_t field_offset)
{
	return RX550_DPM_TABLE_BASE + field_offset;
}

/* Lee/escribe VRConfig (4 bytes) */
int rx550_dpm_read_vrconfig(const struct rx550_mmio_map *map, uint32_t *out_val);
int rx550_dpm_write_vrconfig(const struct rx550_mmio_map *map, uint32_t val);

/* Lee/escribe GraphicsLevel[n] (56 bytes) */
int rx550_dpm_read_graphics_level(const struct rx550_mmio_map *map,
				  uint32_t level,
				  struct rx550_dpm_graphics_level *out);
int rx550_dpm_write_graphics_level(const struct rx550_mmio_map *map,
				   uint32_t level,
				   const struct rx550_dpm_graphics_level *in);

/* Lee/escribe MemoryLevel[n] (24 bytes) */
int rx550_dpm_read_memory_level(const struct rx550_mmio_map *map,
				uint32_t level,
				struct rx550_dpm_memory_level *out);
int rx550_dpm_write_memory_level(const struct rx550_mmio_map *map,
				 uint32_t level,
				 const struct rx550_dpm_memory_level *in);

/* Lee/escribe BootMVdd (2 bytes) */
int rx550_dpm_read_boot_mvdd(const struct rx550_mmio_map *map, uint16_t *out_val);
int rx550_dpm_write_boot_mvdd(const struct rx550_mmio_map *map, uint16_t val);

/* Lee/escribe UVD/VCE Boot Level (1 byte c/u) */
int rx550_dpm_read_uvd_boot_level(const struct rx550_mmio_map *map, uint8_t *out_val);
int rx550_dpm_write_uvd_boot_level(const struct rx550_mmio_map *map, uint8_t val);
int rx550_dpm_read_vce_boot_level(const struct rx550_mmio_map *map, uint8_t *out_val);
int rx550_dpm_write_vce_boot_level(const struct rx550_mmio_map *map, uint8_t val);

/* Lee/escribe LowSclkInterruptThreshold (4 bytes) */
int rx550_dpm_read_low_sclk_threshold(const struct rx550_mmio_map *map, uint32_t *out_val);
int rx550_dpm_write_low_sclk_threshold(const struct rx550_mmio_map *map, uint32_t val);

/* Sube tabla DPM completa (excepto 3 PID controllers = 108 bytes cabeza)
 * Implementa polaris10_upload_dpm_data: smu7_copy_bytes_to_smc con
 * tamaño = sizeof(DPM) - 3*sizeof(PIDController) = 1776 bytes,
 * destino = base + offsetof(SystemFlags) = 0x3F300 */
int rx550_dpm_upload_table(const struct rx550_mmio_map *map,
			   const uint8_t *table_src, uint32_t table_size);

#endif /* RX550_DPM_H */
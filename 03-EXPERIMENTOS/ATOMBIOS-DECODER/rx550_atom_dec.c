/*
 * rx550_atom_dec.c - Decodificador puro del ATOMBIOS de la RX 550 (Polaris12/GFX8)
 *
 * LECTOR PURO. Abre exactamente un fichero, el que se le pasa en argv[1].
 * No abre nodos de /dev, no abre /sys, no hace ioctl, no escribe registros.
 *
 * Replica la cadena de llamadas que el driver ejecuta para CHIP_POLARIS12:
 *   amdgpu_bios.c:161  pci_map_rom           -> el buffer es la ROM byte a byte
 *   amdgpu_bios.c:174  check_atom_bios
 *   amdgpu_atombios.c:1914  amdgpu_atom_parse(atom_card_info, adev->bios)
 *   atom.c:1560-1607        validacion yOffsets de cmd_table/data_table
 *   amdgpu_atombios.c:739   amdgpu_atom_parse_data_header(ctx, 14, ...)
 *   atom.c:1642-1661        resolucion de la entrada GFX_Info
 *   amdgpu_atombios.c:744-750  copia de los seis campos de geometria
 *
 * Ver 08-ARQUITECTURA/ATOMBIOS-DECODER.md.
 */

#ifdef __KERNEL__
#include <linux/kernel.h>
#include <linux/string.h>
#include <linux/slab.h>
#else
#include <stdarg.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#endif

#include "rx550_atom_dec.h"

/* =======================================================================
 * Codigos de salida. Distintos para poder distinguir por que motivo fallo.
 * ======================================================================= */
#define RX550_RC_OK            0
#define RX550_RC_SELFTEST      1   /* fallo del self-test                      */
#define RX550_RC_USO           2   /* falta argv[1]                            */
#define RX550_RC_IO            3   /* no se pudo leer el fichero de entrada     */
#define RX550_RC_RECHAZO       4   /* no es un ATOMBIOS segun la ruta del driver*/
#define RX550_RC_TRUNCADO      5   /* referencia mas alla del fin del fichero   */
#define RX550_RC_AUSENTE       6   /* GFX_Info ausente: NO se inventan ceros    */

/* =======================================================================
 * Lector con control de limites.
 *
 * El driver no necesita comprobar limites porque pci_map_rom entrega la ROM
 * entera. Un lector de fichero suelto si. Las comprobaciones de este bloque
 * se etiquetan como INTEGRIDAD_DEL_DECODIFICADOR, no como semantica del driver.
 * ======================================================================= */
struct rx550_rom {
	const u8_rxd *d;
	size_t        n;
	char          err[192];   /* motivo del fallo, si lo hay */
	int           err_off;    /* offset exacto donde se quedo corta, o -1 */
	int           rc;         /* RX550_RC_* */
};

static void rx550_rom_init(struct rx550_rom *r, const u8_rxd *d, size_t n)
{
	r->d = d;
	r->n = n;
	r->err[0] = '\0';
	r->err_off = -1;
	r->rc = RX550_RC_OK;
}

#ifndef __KERNEL__
static void rx550_rom_error(struct rx550_rom *r, int rc, long off, const char *fmt, ...)
{
	va_list ap;

	if (r->rc != RX550_RC_OK)
		return;                 /* se conserva el primer fallo, el mas raiz */
	r->rc = rc;
	r->err_off = (int)off;
	va_start(ap, fmt);
	vsnprintf(r->err, sizeof(r->err), fmt, ap);
	va_end(ap);
}
#else
static void rx550_rom_error(struct rx550_rom *r, int rc, long off, const char *fmt, ...)
{
	/* En la rama de kernel esta primitiva no se compila: el codigo de este
	 * descodificador es de usuario. Se deja el prototipo declarado para que
	 * las fases compilen, sin inventar una ruta de kernel no verificada. */
	(void)r; (void)rc; (void)off; (void)fmt;
}
#endif

/* Comprueba que [off, off+len) cae dentro del fichero.
 * Cuando no cabe, el offset que se registra es el PRIMER BYTE QUE FALTA, que
 * no es lo mismo que el inicio del bloque: si el bloque empieza dentro del
 * fichero pero se sale por el final, el primer byte ausente es el propio
 * tamano del fichero. Asi el mensaje dice donde se quedo corta de verdad. */
static int rx550_need(struct rx550_rom *r, unsigned long off, unsigned long len,
		      const char *que)
{
	unsigned long falta;

	if (r->rc != RX550_RC_OK)
		return 0;
	if ((size_t)off > r->n)
		falta = off;                    /* el bloque entero esta fuera */
	else if ((size_t)(off + len) > r->n)
		falta = (unsigned long)r->n;     /* el fichero acaba aqui */
	else
		return 1;

	rx550_rom_error(r, RX550_RC_TRUNCADO, (long)falta,
			"TRUNCADA: %s necesita [0x%lX,0x%lX) pero el fichero "
			"mide 0x%lX; primer byte ausente off=0x%lX",
			que, off, off + len, (unsigned long)r->n, falta);
	return 0;
}

/* Lecturas little-endian byte a byte. El driver usa le16_to_cpu sobre un buffer
 * que entrega PCI, materializado en memoria de forma nativa; aqui el
 * fichero puede estar en cualquier orden de bytes, asi que se descompone
 * explicitamente. Es la unica desviacion consciente y esta justificada en el
 * informe: no altera el resultado en x86-64 y evita comportamiento indefinido. */
static u16_rxd rx550_rd16(const u8_rxd *p)
{
	return (u16_rxd)((u16_rxd)p[0] | ((u16_rxd)p[1] << 8));
}

static u32_rxd rx550_rd32(const u8_rxd *p)
{
	return (u32_rxd)p[0] | ((u32_rxd)p[1] << 8) |
	       ((u32_rxd)p[2] << 16) | ((u32_rxd)p[3] << 24);
}

/* =======================================================================
 * Resultado de la decodificacion.
 * ======================================================================= */
enum rx550_b7 {
	RX550_B7_TILE_PIPES = 0,  /* el byte es max_tile_pipes        */
	RX550_B7_RESERVED   = 1,  /* el byte es reserved (crev 4 y 7) */
	RX550_B7_DESCONOCIDO = 2  /* version no cubierta por las dos cabeceras */
};

struct rx550_dec {
	struct rx550_rom rom;

	unsigned long base;            /* CU16(0x48)                        */
	unsigned long cmd_table;
	unsigned long data_table;

	/* ATOM_ROM_HEADER */
	unsigned long romh_off;
	u16_rxd romh_size;
	u8_rxd  romh_frev, romh_crev;
	unsigned long romh_master_cmd;
	unsigned long romh_master_data;

	/* tabla maestra de datos */
	unsigned long master_off;
	u16_rxd master_size;
	u8_rxd  master_frev, master_crev;
	unsigned long gfx_entry_off;   /* data_table + 4 + 14*2            */
	unsigned long gfx_off;         /* valor de la entrada, relativo a bios */
	u16_rxd gfx_entry_raw;

	/* GFX_Info */
	unsigned long gfx_abs;         /* gfx_off, ya absoluto             */
	u16_rxd gfx_size;
	u8_rxd  gfx_frev, gfx_crev;
	u8_rxd  gfx_ipmin, gfx_ipmaj;
	u8_rxd  gfx_se, gfx_b7, gfx_cu_per_sh, gfx_sh_per_se, gfx_bknd, gfx_tcc;
	enum rx550_b7 b7_sem;

	/* extension v2_4 */
	int      ext24_ok;
	u8_rxd  gfx24_active_cu_sh, gfx24_active_rb_se, gfx24_reserved;
	u16_rxd gfx24_gcgoldenoff, gfx24_num_gprs, gfx24_gsprim_depth;
	u16_rxd gfx24_param_cache, gfx24_wave_size, gfx24_waves_per_simd;
	u16_rxd gfx24_lds_size;
	u8_rxd  gfx24_max_gs_thds, gfx24_gs_tbl_depth, gfx24_double_offchip;
	u8_rxd  gfx24_scratch_slots;
	u32_rxd gfx24_sram_rm, gfx24_sram_cus;

	/* extension v2_7 */
	int      ext27_ok;
	u8_rxd  gfx27_cut_cu, gfx27_active_cu_tot, gfx27_cu_res0, gfx27_cu_res1;
	u32_rxd gfx27_gc_config;

	/* extension v2_3 (atombios.h) */
	int      ext23_ok;
	u16_rxd gfx23_leak_thr, gfx23_lo_dpm7, gfx23_hi_dpm7;
	u16_rxd gfx23_rsv0, gfx23_rsv1, gfx23_rsv2;

	/* FirmwareInfo */
	int      fwi_ok;
	unsigned long fwi_off;
	u16_rxd fwi_size;
	u8_rxd  fwi_frev, fwi_crev;
	u32_rxd fwi_rev, fwi_def_sclk, fwi_def_mclk, fwi_tgt_sclk, fwi_tgt_mclk;
	u32_rxd fwi_max_sclk_pll, fwi_max_mclk_pll, fwi_max_pclk_pll;
	u32_rxd fwi_asic_max_sclk, fwi_asic_max_mclk;
	u8_rxd  fwi_asic_max_temp;

	/* cadena de parte number */
	int      pn_ok;
	unsigned long pn_off;
	char     pn[RX550_PN_MAX_LEN + 1];
	int      pn_via_strings;   /* 1 = via OFFSET_TO_GET_ATOMBIOS_STRING_START */
	unsigned long strings_num;

	/* bytes 0..2 */
	u8_rxd  sig0, sig1, len_byte;
	u32_rxd vbios_length;      /* AMD_VBIOS_LENGTH: len_byte << 9 */

	unsigned long derived_cu_total;
};

/* =======================================================================
 * Fase 1: check_atom_bios (amdgpu_bios.c:50-85)
 * ======================================================================= */
static void fase_check_atom_bios(struct rx550_dec *d)
{
	struct rx550_rom *r = &d->rom;
	unsigned long tmp;

	if (r->n < RX550_CHECK_ATOM_MIN_SIZE) {
		rx550_rom_error(r, RX550_RC_RECHAZO, 0,
				"RECHAZO: el fichero mide 0x%lX y check_atom_bios exige 0x%lX (amdgpu_bios.c:55)",
				(unsigned long)r->n, (unsigned long)RX550_CHECK_ATOM_MIN_SIZE);
		return;
	}

	d->sig0 = r->d[RX550_VBIOS_SIG_OFF];
	d->sig1 = r->d[RX550_VBIOS_SIG_OFF + 1];
	if (d->sig0 != RX550_VBIOS_SIG_BYTE0 || d->sig1 != RX550_VBIOS_SIG_BYTE1) {
		rx550_rom_error(r, RX550_RC_RECHAZO, RX550_VBIOS_SIG_OFF,
				"RECHAZO: firma de VBIOS 0x%02X%02X, se esperaba 0x%02X%02X (amdgpu_bios.c:44,60)",
				(unsigned long)d->sig0, (unsigned long)d->sig1,
				(unsigned long)RX550_VBIOS_SIG_BYTE0,
				(unsigned long)RX550_VBIOS_SIG_BYTE1);
		return;
	}

	d->len_byte  = r->d[RX550_AMD_VBIOS_LENGTH_OFF];
	d->vbios_length = (u32_rxd)(d->len_byte << 9);   /* amdgpu_bios.c:45 */

	d->base = rx550_rd16(r->d + RX550_ATOM_ROM_TABLE_PTR); /* amdgpu_bios.c:66 */
	if (d->base == 0) {
		rx550_rom_error(r, RX550_RC_RECHAZO, RX550_ATOM_ROM_TABLE_PTR,
				"RECHAZO: base del ROM header es 0, no se puede localizar (amdgpu_bios.c:67)");
		return;
	}

	tmp = d->base + RX550_ROM_MAGIC_PTR;
	if ((size_t)tmp > r->n) {
		rx550_rom_error(r, RX550_RC_RECHAZO, (long)tmp,
				"RECHAZO: la cabecera ROM empieza en 0x%lX y la firma en 0x%lX, mas alla del fichero de 0x%lX (amdgpu_bios.c:73)",
				d->base, tmp, (unsigned long)r->n);
		return;
	}

	if (memcmp(r->d + tmp, RX550_ROM_MAGIC_STR, 4) == 0 ||
	    memcmp(r->d + tmp, RX550_ROM_MAGIC_ALT, 4) == 0)
		return;

	rx550_rom_error(r, RX550_RC_RECHAZO, (long)tmp,
			"RECHAZO: la firma en 0x%lX no es ni \"%s\" ni \"%s\" (amdgpu_bios.c:78-79)",
			tmp, RX550_ROM_MAGIC_STR, RX550_ROM_MAGIC_ALT);
}

/* =======================================================================
 * Fase 2: amdgpu_atom_parse (atom.c:1545-1610)
 * ======================================================================= */
static void fase_atom_parse(struct rx550_dec *d)
{
	struct rx550_rom *r = &d->rom;
	unsigned long m;

	if (r->rc != RX550_RC_OK)
		return;

	if (!rx550_need(r, 0, 2, "la palabra 0xAA55 de atom.c:1560"))
		return;
	if (rx550_rd16(r->d) != RX550_ATOM_BIOS_MAGIC) {
		rx550_rom_error(r, RX550_RC_RECHAZO, 0,
				"RECHAZO: CU16(0) = 0x%04X y atom.c:1560 exige 0xAA55",
				(unsigned long)rx550_rd16(r->d));
		return;
	}

	if (!rx550_need(r, RX550_ATI_MAGIC_PTR, RX550_ATI_MAGIC_LEN,
			"la cadena magica ATI de atom.c:1566"))
		return;
	if (memcmp(r->d + RX550_ATI_MAGIC_PTR, RX550_ATI_MAGIC_STR,
		   RX550_ATI_MAGIC_LEN) != 0) {
		rx550_rom_error(r, RX550_RC_RECHAZO, RX550_ATI_MAGIC_PTR,
				"RECHAZO: la cadena en 0x%02X no es la cadena magica ATI de atom.h:34 (atom.c:1565)",
				(unsigned long)RX550_ATI_MAGIC_PTR);
		return;
	}

	/* atom.c:1574-1580 vuelve a validar la firma y SOLO admite "ATOM".
	 * Asimetria real frente a check_atom_bios, que tambien admite "MOTA". */
	m = d->base + RX550_ROM_MAGIC_PTR;
	if (!rx550_need(r, m, 4, "la firma que revalida atom.c:1574"))
		return;
	if (memcmp(r->d + m, RX550_ROM_MAGIC_STR, 4) != 0) {
		rx550_rom_error(r, RX550_RC_RECHAZO, (long)m,
				"RECHAZO: \"%s\" pasa check_atom_bios pero atom.c:1574 solo admite \"%s\" (asimetria real del driver)",
				RX550_ROM_MAGIC_ALT, RX550_ROM_MAGIC_STR);
		return;
	}

	d->cmd_table  = rx550_rd16(r->d + d->base + RX550_ROM_CMD_PTR);  /* atom.c:1582 */
	d->data_table = rx550_rd16(r->d + d->base + RX550_ROM_DATA_PTR); /* atom.c:1583 */
}

/* =======================================================================
 * Fase 3: ATOM_ROM_HEADER y tabla maestra de datos
 * ======================================================================= */
static void fase_rom_header(struct rx550_dec *d)
{
	struct rx550_rom *r = &d->rom;
	unsigned long h = d->base;

	if (r->rc != RX550_RC_OK)
		return;
	if (!rx550_need(r, h, RX550_ROMH_TOTAL, "el ATOM_ROM_HEADER de atombios.h:219"))
		return;

	d->romh_off         = h;
	d->romh_size        = rx550_rd16(r->d + h + RX550_ROMH_SIZE);
	d->romh_frev        = r->d[h + RX550_ROMH_FREV];
	d->romh_crev        = r->d[h + RX550_ROMH_CREV];
	d->romh_master_cmd  = rx550_rd16(r->d + h + RX550_ROMH_MASTER_CMD_OFF);
	d->romh_master_data = rx550_rd16(r->d + h + RX550_ROMH_MASTER_DATA_OFF);

	/* atom.c:1591-1593: si usMasterDataTableOffset es 0 no hay tabla maestra.
	 * El driver no falla aqui, simplemente se salta el bloque. */
	if (d->romh_master_data == 0) {
		rx550_rom_error(r, RX550_RC_AUSENTE, (long)(h + RX550_ROMH_MASTER_DATA_OFF),
				"AUSENTE: usMasterDataTableOffset = 0, no hay tabla maestra de datos (atom.c:1591)");
		return;
	}

	d->master_off = d->romh_master_data;
	if (!rx550_need(r, d->master_off, RX550_CTH_SIZE,
			"la cabecera de la tabla maestra, atombios.h:2824"))
		return;
	d->master_size = rx550_rd16(r->d + d->master_off + RX550_CTH_SIZE_OFF);
	d->master_frev = r->d[d->master_off + RX550_CTH_FREV_OFF];
	d->master_crev = r->d[d->master_off + RX550_CTH_CREV_OFF];
}

/* Resuelve una entrada N de la tabla maestra: atom.c:1642-1661. */
static int entrada_master(struct rx550_dec *d, unsigned long index,
			  unsigned long *valor, unsigned long *pos,
			  const char *que)
{
	struct rx550_rom *r = &d->rom;

	/* atom.c:1646-1647: offset = index*2 + 4, leido en CU16(data_table + offset) */
	*pos = d->data_table + RX550_CTH_SIZE + index * RX550_MASTER_ENTRY_SIZE;
	if (!rx550_need(r, *pos, RX550_MASTER_ENTRY_SIZE, que))
		return 0;
	*valor = rx550_rd16(r->d + *pos);
	return 1;
}

/* =======================================================================
 * Fase 4: GFX_Info, la tabla que da la geometria.
 * ======================================================================= */
static void fase_gfx(struct rx550_dec *d)
{
	struct rx550_rom *r = &d->rom;

	if (r->rc != RX550_RC_OK)
		return;

	if (!entrada_master(d, RX550_IDX_GFX_INFO, &d->gfx_off, &d->gfx_entry_off,
			    "la entrada GFX_Info de la tabla maestra"))
		return;

	d->gfx_entry_raw = (u16_rxd)d->gfx_off;

	/* atom.c:1650-1651: mdt[index] == 0 significa tabla ausente.
	 * NO se devuelven ceros como si fueran un valor: se sale con error. */
	if (d->gfx_off == 0) {
		rx550_rom_error(r, RX550_RC_AUSENTE, (long)d->gfx_entry_off,
				"AUSENTE: la entrada GFX_Info (indice %lu, atom.c:1650) vale 0, no hay tabla de geometria",
				(unsigned long)RX550_IDX_GFX_INFO);
		return;
	}

	d->gfx_abs = d->gfx_off;
	if (!rx550_need(r, d->gfx_abs, RX550_CTH_SIZE,
			"la cabecera comun de GFX_Info, atombios.h:5649"))
		return;

	d->gfx_size = rx550_rd16(r->d + d->gfx_abs + RX550_GFX_SIZE_OFF);
	d->gfx_frev = r->d[d->gfx_abs + RX550_GFX_FREV_OFF];
	d->gfx_crev = r->d[d->gfx_abs + RX550_GFX_CREV_OFF];

	/* Los seis campos de geometria. amdgpu_atombios.c:744-750 no comprueba
	 * frev ni crev: los lee en los offsets de ATOM_GFX_INFO_V2_1 siempre.
	 * Aqui se exige que los doce bytes que el driver lee esten dentro del
	 * fichero, y se avisa si usStructureSize dice que la tabla es mas corta. */
	if (!rx550_need(r, d->gfx_abs, RX550_GFX_V21_TOTAL,
			"los doce bytes de ATOM_GFX_INFO_V2_1 que lee amdgpu_atombios.c:744-750"))
		return;

	if (d->gfx_size != 0 && d->gfx_size < RX550_GFX_V21_TOTAL) {
		rx550_rom_error(r, RX550_RC_AUSENTE, (long)(d->gfx_abs + RX550_GFX_SIZE_OFF),
				"INCOHERENTE: usStructureSize = %lu y ATOM_GFX_INFO_V2_1 ocupa %lu bytes (atombios.h:5647)",
				(unsigned long)d->gfx_size,
				(unsigned long)RX550_GFX_V21_TOTAL);
		return;
	}
	if (d->gfx_size != 0 &&
	    (size_t)(d->gfx_abs + d->gfx_size) > r->n) {
		rx550_rom_error(r, RX550_RC_TRUNCADO,
				(long)(d->gfx_abs + d->gfx_size),
				"TRUNCADA: GFX_Info declara %lu bytes desde 0x%lX pero el fichero mide 0x%lX",
				(unsigned long)d->gfx_size, d->gfx_abs,
				(unsigned long)r->n);
		return;
	}

	d->gfx_ipmin     = r->d[d->gfx_abs + RX550_GFX_IPMIN];
	d->gfx_ipmaj     = r->d[d->gfx_abs + RX550_GFX_IPMAJ];
	d->gfx_se        = r->d[d->gfx_abs + RX550_GFX_MAX_SE];
	d->gfx_b7        = r->d[d->gfx_abs + RX550_GFX_MAX_TP];
	d->gfx_cu_per_sh = r->d[d->gfx_abs + RX550_GFX_MAX_CU_PER_SH];
	d->gfx_sh_per_se = r->d[d->gfx_abs + RX550_GFX_MAX_SH_PER_SE];
	d->gfx_bknd      = r->d[d->gfx_abs + RX550_GFX_MAX_BACKENDS];
	d->gfx_tcc       = r->d[d->gfx_abs + RX550_GFX_MAX_TCC];

	/* Semantica del byte +7. El driver lo llama max_tile_pipes sin mirar la
	 * version (amdgpu_atombios.c:745). atombios.h:5653 lo llama max_tile_pipes
	 * en v2_1 y v2_3; atomfirmware.h:1844 lo llama reserved en v2_4, y en v2_7
	 * tambien. Se marca cual de los dos es, en vez de elegir en silencio. */
	if ((d->gfx_frev == 2 || d->gfx_frev == 3) && d->gfx_crev == 0) {
		d->b7_sem = RX550_B7_DESCONOCIDO;
	} else if ((d->gfx_frev == 2 && (d->gfx_crev == 4 || d->gfx_crev == 7))) {
		d->b7_sem = RX550_B7_RESERVED;
	} else if (d->gfx_frev == 2 || d->gfx_crev == 1 || d->gfx_crev == 2 ||
		   d->gfx_crev == 3) {
		d->b7_sem = RX550_B7_TILE_PIPES;
	} else {
		d->b7_sem = RX550_B7_DESCONOCIDO;
	}

	d->derived_cu_total = (unsigned long)d->gfx_se * d->gfx_sh_per_se *
			      d->gfx_cu_per_sh;

	/* Extensions, solo cuando la tabla llega hasta ahi. */
	if (d->gfx_frev == 2 && d->gfx_crev == 4 &&
	    rx550_need(r, d->gfx_abs, RX550_GFX24_TOTAL,
		       "la extension atom_gfx_info_v2_4, atomfirmware.h:1838")) {
		const u8_rxd *p = r->d + d->gfx_abs;
		d->ext24_ok = 1;
		d->gfx24_reserved     = p[RX550_GFX_MAX_TP];
		d->gfx24_active_cu_sh = p[RX550_GFX24_ACTIVE_CU_SH];
		d->gfx24_active_rb_se = p[RX550_GFX24_ACTIVE_RB_SE];
		d->gfx24_gcgoldenoff  = rx550_rd16(p + RX550_GFX24_GCGOLDENOFF);
		d->gfx24_num_gprs     = rx550_rd16(p + RX550_GFX24_NUM_GPRS);
		d->gfx24_gsprim_depth = rx550_rd16(p + RX550_GFX24_GSPRIM_DEPTH);
		d->gfx24_param_cache  = rx550_rd16(p + RX550_GFX24_PARAM_CACHE);
		d->gfx24_wave_size    = rx550_rd16(p + RX550_GFX24_WAVE_SIZE);
		d->gfx24_waves_per_simd = rx550_rd16(p + RX550_GFX24_WAVES_PER_SIMD);
		d->gfx24_lds_size     = rx550_rd16(p + RX550_GFX24_LDS_SIZE);
		d->gfx24_max_gs_thds  = p[RX550_GFX24_MAX_GS_THDS];
		d->gfx24_gs_tbl_depth = p[RX550_GFX24_GS_TBL_DEPTH];
		d->gfx24_double_offchip = p[RX550_GFX24_DOUBLE_OFFCHIP];
		d->gfx24_scratch_slots = p[RX550_GFX24_SCRATCH_SLOTS];
		d->gfx24_sram_rm      = rx550_rd32(p + RX550_GFX24_SRAM_RM_FUSES);
		d->gfx24_sram_cus     = rx550_rd32(p + RX550_GFX24_SRAM_CUS_FUSES);
	}

	if (d->gfx_frev == 2 && d->gfx_crev == 7 &&
	    rx550_need(r, d->gfx_abs, RX550_GFX27_TOTAL,
		       "la extension atom_gfx_info_v2_7, atomfirmware.h:1880")) {
		const u8_rxd *p = r->d + d->gfx_abs;
		d->ext27_ok = 1;
		d->gfx27_cut_cu        = p[RX550_GFX27_CUT_CU];
		d->gfx27_active_cu_tot = p[RX550_GFX27_ACTIVE_CU_TOT];
		d->gfx27_cu_res0       = p[RX550_GFX27_CU_RESERVED0];
		d->gfx27_cu_res1       = p[RX550_GFX27_CU_RESERVED1];
		d->gfx27_gc_config     = rx550_rd32(p + RX550_GFX27_GC_CONFIG);
	}

	/* crev == 3 es una CONTRADICCION entre las dos cabeceras: atombios.h:5660
	 * pone tres USHORT en +12, atomfirmware.h:1814 pone ocho ULONG en +12.
	 * Se decodifica el prefijo comun y se declara la zona +12 como DISPUTADA,
	 * sin imprimir ningun valor como si fuera un hecho. */
	if (d->gfx_frev == 2 && d->gfx_crev == 3 &&
	    rx550_need(r, d->gfx_abs, RX550_GFX23_TOTAL,
		       "la zona +12 de GFX_Info 2.3 segun atombios.h:5660")) {
		const u8_rxd *p = r->d + d->gfx_abs;
		d->ext23_ok = 1;
		d->gfx23_leak_thr = rx550_rd16(p + RX550_GFX23_LEAKAGE_THR);
		d->gfx23_lo_dpm7  = rx550_rd16(p + RX550_GFX23_LO_DPM7_OFF);
		d->gfx23_hi_dpm7  = rx550_rd16(p + RX550_GFX23_HI_DPM7_OFF);
		d->gfx23_rsv0     = rx550_rd16(p + RX550_GFX23_RESERVED0);
		d->gfx23_rsv1     = rx550_rd16(p + RX550_GFX23_RESERVED1);
		d->gfx23_rsv2     = rx550_rd16(p + RX550_GFX23_RESERVED2);
	}
}

/* =======================================================================
 * Fase 5: FirmwareInfo, indice 4 (amdgpu_atombios.c:581)
 * ======================================================================= */
static void fase_firmware_info(struct rx550_dec *d)
{
	struct rx550_rom *r = &d->rom;
	unsigned long pos, off;

	if (r->rc != RX550_RC_OK)
		return;
	if (!entrada_master(d, RX550_IDX_FIRMWARE_INFO, &off, &pos,
			   "la entrada FirmwareInfo de la tabla maestra"))
		return;
	if (off == 0) {
		d->fwi_ok = 0;   /* atom.c:1650: no es fatal, el driver sigue */
		return;
	}
	d->fwi_off = off;
	if (!rx550_need(r, off, RX550_CTH_SIZE,
			"la cabecera comun de FirmwareInfo, atombios.h:2950"))
		return;
	d->fwi_size = rx550_rd16(r->d + off + RX550_CTH_SIZE_OFF);
	d->fwi_frev = r->d[off + RX550_CTH_FREV_OFF];
	d->fwi_crev = r->d[off + RX550_CTH_CREV_OFF];

	if (!rx550_need(r, off, RX550_FWI_PREFIX_TOTAL,
			"el prefijo de ATOM_FIRMWARE_INFO, atombios.h:2948"))
		return;

	d->fwi_rev           = rx550_rd32(r->d + off + RX550_FWI_FW_REVISION);
	d->fwi_def_sclk      = rx550_rd32(r->d + off + RX550_FWI_DEF_SCLK);
	d->fwi_def_mclk      = rx550_rd32(r->d + off + RX550_FWI_DEF_MCLK);
	d->fwi_tgt_sclk      = rx550_rd32(r->d + off + RX550_FWI_TGT_SCLK);
	d->fwi_tgt_mclk      = rx550_rd32(r->d + off + RX550_FWI_TGT_MCLK);
	d->fwi_max_sclk_pll  = rx550_rd32(r->d + off + RX550_FWI_MAX_SCLK_PLLOUT);
	d->fwi_max_mclk_pll  = rx550_rd32(r->d + off + RX550_FWI_MAX_MCLK_PLLOUT);
	d->fwi_max_pclk_pll  = rx550_rd32(r->d + off + RX550_FWI_MAX_PCLK_PLLOUT);
	d->fwi_asic_max_sclk = rx550_rd32(r->d + off + RX550_FWI_ASIC_MAX_SCLK);
	d->fwi_asic_max_mclk = rx550_rd32(r->d + off + RX550_FWI_ASIC_MAX_MCLK);
	d->fwi_asic_max_temp = r->d[off + RX550_FWI_ASIC_MAX_TEMP];
	d->fwi_ok = 1;
}

/* =======================================================================
 * Fase 6: cadena de parte number (atom.c:1435-1462, atom_get_vbios_pn)
 * ======================================================================= */
static void fase_part_number(struct rx550_dec *d)
{
	struct rx550_rom *r = &d->rom;
	unsigned long start;
	unsigned count = 0;

	if (r->rc != RX550_RC_OK)
		return;
	if (!rx550_need(r, RX550_STR_NUM_OFF, 1,
			"el numero de cadenas de ATOMBIOS, atom.c:1437"))
		return;

	d->strings_num = r->d[RX550_STR_NUM_OFF];
	if (d->strings_num != 0) {
		/* atom.c:1438-1440: lectura de un u16 DESALINEADO en 0x6e. */
		if (!rx550_need(r, RX550_STR_START_OFF, 2,
				"el desplazamiento de la cadena de parte, atom.c:1439"))
			return;
		start = rx550_rd16(r->d + RX550_STR_START_OFF);
		d->pn_via_strings = 1;
	} else {
		start = RX550_PN_FALLBACK_OFF;   /* atom.c:1443 */
		d->pn_via_strings = 0;
	}

	d->pn_off = start;
	if (!rx550_need(r, start, 1,
			"la cadena de parte number que lee atom.c:1440"))
		return;

	/* atom.c:1456-1462: copiar mientras count < 43 y el byte este entre ' ' y 'z' */
	while (count < RX550_PN_MAX_LEN &&
	       (size_t)(start + count) < r->n &&
	       r->d[start + count] >= 0x20 && r->d[start + count] <= 0x7A)
		count++;

	memcpy(d->pn, r->d + start, count);
	d->pn[count] = '\0';
	d->pn_ok = 1;
}

/* =======================================================================
 * Informe. Cada campo impreso lleva offset, ancho, endianness, tipo y cita.
 * ======================================================================= */
static void imprime_campo(const char *etiqueta, unsigned long off, unsigned ancho,
			  const char *tipo, const char *cita, u64_rxd v)
{
	printf("  %-34s off=0x%05lX ancho=%u endian=LE tipo=%s\n"
	       "      cita=%s\n"
	       "      valor=%llu (0x%llX)\n",
	       etiqueta, off, ancho, tipo, cita,
	       (unsigned long long)v, (unsigned long long)v);
}

static void imprime_gfx_completo(const struct rx550_dec *d)
{
	unsigned long b = d->gfx_abs;

	printf("[GFX_Info] es lo que lee amdgpu_atombios.c:744-750 para la geometria\n");
	printf("  tabla en off=0x%05lX, obtenida de data_table(0x%05lX) + 4 + %u*2"
	       " = off=0x%05lX\n",
	       b, d->data_table, (unsigned)RX550_IDX_GFX_INFO, d->gfx_entry_off);
	printf("  version frev=%u crev=%u declarada=%u\n\n",
	       (unsigned)d->gfx_frev, (unsigned)d->gfx_crev, (unsigned)d->gfx_size);

	imprime_campo("ATOM_GFX_INFO_V2_1.asHeader.usStructureSize",
		      b + RX550_GFX_SIZE_OFF, 2,
		      "ATOM_COMMON_TABLE_HEADER.usStructureSize",
		      "atombios.h:5649,5650 ; leido por atom.c:1654", d->gfx_size);
	imprime_campo("ATOM_GFX_INFO_V2_1.asHeader.ucTableFormatRevision",
		      b + RX550_GFX_FREV_OFF, 1,
		      "ATOM_COMMON_TABLE_HEADER.ucTableFormatRevision",
		      "atombios.h:5649 ; leido por atom.c:1656", d->gfx_frev);
	imprime_campo("ATOM_GFX_INFO_V2_1.asHeader.ucTableContentRevision",
		      b + RX550_GFX_CREV_OFF, 1,
		      "ATOM_COMMON_TABLE_HEADER.ucTableContentRevision",
		      "atombios.h:5649 ; leido por atom.c:1658", d->gfx_crev);
	imprime_campo("ATOM_GFX_INFO_V2_1.GfxIpMinVer",
		      b + RX550_GFX_IPMIN, 1, "UCHAR", "atombios.h:5650",
		      d->gfx_ipmin);
	imprime_campo("ATOM_GFX_INFO_V2_1.GfxIpMajVer",
		      b + RX550_GFX_IPMAJ, 1, "UCHAR", "atombios.h:5651",
		      d->gfx_ipmaj);
	imprime_campo("ATOM_GFX_INFO_V2_1.max_shader_engines",
		      b + RX550_GFX_MAX_SE, 1, "UCHAR",
		      "atombios.c:744 ; atombios.h:5652", d->gfx_se);
	printf("  %-34s off=0x%05lX ancho=1 endian=LE tipo=UCHAR\n"
	       "      cita=amdgpu_atombios.c:745 ; atombios.h:5653 (v2_1/v2_3) "
	       "contra atomfirmware.h:1844 (reserved en v2_4/v2_7)\n"
	       "      valor=%u (0x%02X)  SEMANTICA=%s\n",
	       b == 0 ? "" : "ATOM_GFX_INFO_V2_1.max_tile_pipes",
	       b + RX550_GFX_MAX_TP, (unsigned)d->gfx_b7,
	       (unsigned)d->gfx_b7,
	       d->b7_sem == RX550_B7_TILE_PIPES ? "max_tile_pipes" :
	       d->b7_sem == RX550_B7_RESERVED   ? "reserved" :
	                                          "INDETERMINADA");
	imprime_campo("ATOM_GFX_INFO_V2_1.max_cu_per_sh",
		      b + RX550_GFX_MAX_CU_PER_SH, 1, "UCHAR",
		      "amdgpu_atombios.c:746 ; atombios.h:5654", d->gfx_cu_per_sh);
	imprime_campo("ATOM_GFX_INFO_V2_1.max_sh_per_se",
		      b + RX550_GFX_MAX_SH_PER_SE, 1, "UCHAR",
		      "amdgpu_atombios.c:747 ; atombios.h:5655", d->gfx_sh_per_se);
	imprime_campo("ATOM_GFX_INFO_V2_1.max_backends_per_se",
		      b + RX550_GFX_MAX_BACKENDS, 1, "UCHAR",
		      "amdgpu_atombios.c:748 ; atombios.h:5656", d->gfx_bknd);
	imprime_campo("ATOM_GFX_INFO_V2_1.max_texture_channel_caches",
		      b + RX550_GFX_MAX_TCC, 1, "UCHAR",
		      "amdgpu_atombios.c:749-750 ; atombios.h:5657", d->gfx_tcc);

	printf("\n[DERIVACION] max_shader_engines * max_sh_per_se * max_cu_per_sh\n"
	       "  %u * %u * %u = %lu\n"
	       "  Derivado de los offsets +6, +9 y +8. El driver no lo calcula:\n"
	       "  amdgpu_atombios.c:744-750 solo copia los seis campos.\n",
	       (unsigned)d->gfx_se, (unsigned)d->gfx_sh_per_se,
	       (unsigned)d->gfx_cu_per_sh, d->derived_cu_total);
}

static void imprime_informe(const struct rx550_dec *d)
{
	unsigned long h = d->romh_off;
	unsigned long b = d->gfx_abs;
	unsigned long f = d->fwi_off;

	printf("================================================================\n");
	printf(" INFORME ATOMBIOS  (decodificador puro, sin acceso a hardware)\n");
	printf("================================================================\n");
	printf("tamano de la entrada = 0x%lX bytes (%lu)\n",
	       (unsigned long)d->rom.n, (unsigned long)d->rom.n);

	printf("\n[0] bytes 0..2, validacion de VBIOS\n");
	imprime_campo("AMD_IS_VALID_VBIOS[0]", RX550_VBIOS_SIG_OFF, 1, "UCHAR",
		      "amdgpu_bios.c:44,60", d->sig0);
	imprime_campo("AMD_IS_VALID_VBIOS[1]", RX550_VBIOS_SIG_OFF + 1, 1, "UCHAR",
		      "amdgpu_bios.c:44,60", d->sig1);
	imprime_campo("AMD_VBIOS_LENGTH[2]", RX550_AMD_VBIOS_LENGTH_OFF, 1,
		      "UCHAR", "amdgpu_bios.c:45", d->len_byte);
	printf("      AMD_VBIOS_LENGTH = 0x%02X << 9 = %lu bytes\n"
	       "      AVISO: este campo NO se usa en la ruta pci_map_rom.\n"
	       "      Solo se usa en amdgpu_bios.c:202, otra funcion.\n"
	       "      No se usa como criterio de aceptacion aqui.\n",
	       (unsigned)d->len_byte, (unsigned long)d->vbios_length);
	imprime_campo("ATOM_ROM_TABLE_PTR (base)", RX550_ATOM_ROM_TABLE_PTR, 2,
		      "USHORT", "atom.h:35 ; amdgpu_bios.c:66 ; atom.c:1573",
		      d->base);

	printf("\n[1] ATOM_ROM_HEADER en off=0x%05lX (atombios.h:219-239)\n", h);
	imprime_campo("ATOM_ROM_HEADER.sHeader.usStructureSize",
		      h + RX550_ROMH_SIZE, 2,
		      "ATOM_COMMON_TABLE_HEADER.usStructureSize", "atombios.h:221",
		      d->romh_size);
	imprime_campo("ATOM_ROM_HEADER.sHeader.ucTableFormatRevision",
		      h + RX550_ROMH_FREV, 1,
		      "ATOM_COMMON_TABLE_HEADER.ucTableFormatRevision",
		      "atombios.h:211", d->romh_frev);
	imprime_campo("ATOM_ROM_HEADER.sHeader.ucTableContentRevision",
		      h + RX550_ROMH_CREV, 1,
		      "ATOM_COMMON_TABLE_HEADER.ucTableContentRevision",
		      "atombios.h:212", d->romh_crev);
	imprime_campo("ATOM_ROM_HEADER.uaFirmWareSignature[4]",
		      h + RX550_ROMH_SIGNATURE, 4, "UCHAR[4]",
		      "atombios.h:222 ; comparado en amdgpu_bios.c:78 y atom.c:1574",
		      rx550_rd32(d->rom.d + h + RX550_ROMH_SIGNATURE));
	imprime_campo("ATOM_ROM_HEADER.usBiosRuntimeSegmentAddress",
		      h + RX550_ROMH_RUNTIME_SEG, 2, "USHORT", "atombios.h:224",
		      rx550_rd16(d->rom.d + h + RX550_ROMH_RUNTIME_SEG));
	imprime_campo("ATOM_ROM_HEADER.usProtectedModeInfoOffset",
		      h + RX550_ROMH_PROTMODE_OFF, 2, "USHORT", "atombios.h:225",
		      rx550_rd16(d->rom.d + h + RX550_ROMH_PROTMODE_OFF));
	imprime_campo("ATOM_ROM_HEADER.usConfigFilenameOffset",
		      h + RX550_ROMH_CFGFILE_OFF, 2, "USHORT", "atombios.h:226",
		      rx550_rd16(d->rom.d + h + RX550_ROMH_CFGFILE_OFF));
	imprime_campo("ATOM_ROM_HEADER.usCRC_BlockOffset",
		      h + RX550_ROMH_CRC_BLOCK_OFF, 2, "USHORT", "atombios.h:227",
		      rx550_rd16(d->rom.d + h + RX550_ROMH_CRC_BLOCK_OFF));
	printf("      AVISO sobre usCRC_BlockOffset: existe el campo, pero NO hay\n"
	       "      ninguna verificacion de CRC en la ruta que se replica.\n"
	       "      No hay CRC en atom.c, ni en amdgpu_atombios.c, ni en\n"
	       "      amdgpu_bios.c. Este descodificador NO comprueba CRC.\n");
	imprime_campo("ATOM_ROM_HEADER.usBIOS_BootupMessageOffset",
		      h + RX550_ROMH_BOOTUP_MSG_OFF, 2, "USHORT", "atombios.h:228",
		      rx550_rd16(d->rom.d + h + RX550_ROMH_BOOTUP_MSG_OFF));
	imprime_campo("ATOM_ROM_HEADER.usInt10Offset",
		      h + RX550_ROMH_INT10_OFF, 2, "USHORT", "atombios.h:229",
		      rx550_rd16(d->rom.d + h + RX550_ROMH_INT10_OFF));
	imprime_campo("ATOM_ROM_HEADER.usPciBusDevInitCode",
		      h + RX550_ROMH_PCIBUSDEV_OFF, 2, "USHORT", "atombios.h:230",
		      rx550_rd16(d->rom.d + h + RX550_ROMH_PCIBUSDEV_OFF));
	imprime_campo("ATOM_ROM_HEADER.usIoBaseAddress",
		      h + RX550_ROMH_IOBASE, 2, "USHORT", "atombios.h:231",
		      rx550_rd16(d->rom.d + h + RX550_ROMH_IOBASE));
	imprime_campo("ATOM_ROM_HEADER.usSubsystemVendorID",
		      h + RX550_ROMH_SUBSYS_VENDOR, 2, "USHORT", "atombios.h:232",
		      rx550_rd16(d->rom.d + h + RX550_ROMH_SUBSYS_VENDOR));
	imprime_campo("ATOM_ROM_HEADER.usSubsystemID",
		      h + RX550_ROMH_SUBSYS_ID, 2, "USHORT", "atombios.h:233",
		      rx550_rd16(d->rom.d + h + RX550_ROMH_SUBSYS_ID));
	imprime_campo("ATOM_ROM_HEADER.usPCI_InfoOffset",
		      h + RX550_ROMH_PCI_INFO_OFF, 2, "USHORT", "atombios.h:234",
		      rx550_rd16(d->rom.d + h + RX550_ROMH_PCI_INFO_OFF));
	imprime_campo("ATOM_ROM_HEADER.usMasterCommandTableOffset",
		      h + RX550_ROMH_MASTER_CMD_OFF, 2, "USHORT",
		      "atombios.h:235 ; leido por atom.c:1582", d->romh_master_cmd);
	imprime_campo("ATOM_ROM_HEADER.usMasterDataTableOffset",
		      h + RX550_ROMH_MASTER_DATA_OFF, 2, "USHORT",
		      "atombios.h:236 ; leido por atom.c:1591,1593",
		      d->romh_master_data);
	imprime_campo("ATOM_ROM_HEADER.ucExtendedFunctionCode",
		      h + RX550_ROMH_EXT_FUNC_CODE, 1, "UCHAR", "atombios.h:237",
		      d->rom.d[h + RX550_ROMH_EXT_FUNC_CODE]);
	imprime_campo("ATOM_ROM_HEADER.ucReserved",
		      h + RX550_ROMH_RESERVED, 1, "UCHAR", "atombios.h:238",
		      d->rom.d[h + RX550_ROMH_RESERVED]);
	printf("      NO_DERIVADO_PARA_ESTE_USO: ulPSPDirTableOffset en off=0x%05lX\n"
	       "      ancho=4 endian=LE tipo=ULONG (atombios.h:262, solo en\n"
	       "      ATOM_ROM_HEADER_V2_1). No se decodifica porque atom.c:1590-1599\n"
	       "      no lo lee en esta ruta.\n",
	       h + RX550_ROMH_V21_PSP_OFF);

	printf("\n[2] punteros a tablas maestras (atom.h:42-43, atom.c:1582-1583)\n");
	imprime_campo("ATOM_ROM_CMD_PTR -> cmd_table", d->base + RX550_ROM_CMD_PTR,
		      2, "USHORT", "atom.h:42 ; atom.c:1582", d->cmd_table);
	imprime_campo("ATOM_ROM_DATA_PTR -> data_table", d->base + RX550_ROM_DATA_PTR,
		      2, "USHORT", "atom.h:43 ; atom.c:1583", d->data_table);

	printf("\n[3] tabla maestra de datos en off=0x%05lX (atombios.h:2822-2826)\n",
	       d->master_off);
	imprime_campo("ATOM_MASTER_DATA_TABLE.sHeader.usStructureSize",
		      d->master_off + RX550_CTH_SIZE_OFF, 2, "USHORT",
		      "atombios.h:2824", d->master_size);
	imprime_campo("ATOM_MASTER_DATA_TABLE.sHeader.ucTableFormatRevision",
		      d->master_off + RX550_CTH_FREV_OFF, 1, "UCHAR",
		      "atombios.h:211", d->master_frev);
	imprime_campo("ATOM_MASTER_DATA_TABLE.sHeader.ucTableContentRevision",
		      d->master_off + RX550_CTH_CREV_OFF, 1, "UCHAR",
		      "atombios.h:212", d->master_crev);
	imprime_campo("ListOfDataTables.GFX_Info (USHORT n.14)",
		      d->gfx_entry_off, 2, "USHORT",
		      "amdgpu_atombios.c:734 ; atombios.h:2799 ; atom.c:1647",
		      d->gfx_entry_raw);

	printf("\n");
	imprime_gfx_completo(d);

	if (d->ext24_ok) {
		printf("\n[GFX_Info extension v2_4] atomfirmware.h:1838-1872, "
		       "base off=0x%05lX\n", b);
		imprime_campo("atom_gfx_info_v2_4.reserved",
			      b + RX550_GFX_MAX_TP, 1, "UCHAR",
			      "atomfirmware.h:1844", d->gfx24_reserved);
		imprime_campo("atom_gfx_info_v2_4.active_cu_per_sh",
			      b + RX550_GFX24_ACTIVE_CU_SH, 1, "UCHAR",
			      "atomfirmware.h:1857", d->gfx24_active_cu_sh);
		imprime_campo("atom_gfx_info_v2_4.active_rb_per_se",
			      b + RX550_GFX24_ACTIVE_RB_SE, 1, "UCHAR",
			      "atomfirmware.h:1858", d->gfx24_active_rb_se);
		imprime_campo("atom_gfx_info_v2_4.gcgoldenoffset",
			      b + RX550_GFX24_GCGOLDENOFF, 2, "USHORT",
			      "atomfirmware.h:1859", d->gfx24_gcgoldenoff);
		imprime_campo("atom_gfx_info_v2_4.gc_num_gprs",
			      b + RX550_GFX24_NUM_GPRS, 2, "USHORT",
			      "atomfirmware.h:1860", d->gfx24_num_gprs);
		imprime_campo("atom_gfx_info_v2_4.gc_gsprim_buff_depth",
			      b + RX550_GFX24_GSPRIM_DEPTH, 2, "USHORT",
			      "atomfirmware.h:1861", d->gfx24_gsprim_depth);
		imprime_campo("atom_gfx_info_v2_4.gc_parameter_cache_depth",
			      b + RX550_GFX24_PARAM_CACHE, 2, "USHORT",
			      "atomfirmware.h:1862", d->gfx24_param_cache);
		imprime_campo("atom_gfx_info_v2_4.gc_wave_size",
			      b + RX550_GFX24_WAVE_SIZE, 2, "USHORT",
			      "atomfirmware.h:1863 ; leido por amdgpu_atomfirmware.c:957",
			      d->gfx24_wave_size);
		imprime_campo("atom_gfx_info_v2_4.gc_max_waves_per_simd",
			      b + RX550_GFX24_WAVES_PER_SIMD, 2, "USHORT",
			      "atomfirmware.h:1864 ; leido por amdgpu_atomfirmware.c:958",
			      d->gfx24_waves_per_simd);
		imprime_campo("atom_gfx_info_v2_4.gc_lds_size",
			      b + RX550_GFX24_LDS_SIZE, 2, "USHORT",
			      "atomfirmware.h:1865 ; leido por amdgpu_atomfirmware.c:960",
			      d->gfx24_lds_size);
		imprime_campo("atom_gfx_info_v2_4.gc_num_max_gs_thds",
			      b + RX550_GFX24_MAX_GS_THDS, 1, "UCHAR",
			      "atomfirmware.h:1866", d->gfx24_max_gs_thds);
		imprime_campo("atom_gfx_info_v2_4.gc_gs_table_depth",
			      b + RX550_GFX24_GS_TBL_DEPTH, 1, "UCHAR",
			      "atomfirmware.h:1867", d->gfx24_gs_tbl_depth);
		imprime_campo("atom_gfx_info_v2_4.gc_double_offchip_lds_buffer",
			      b + RX550_GFX24_DOUBLE_OFFCHIP, 1, "UCHAR",
			      "atomfirmware.h:1868", d->gfx24_double_offchip);
		imprime_campo("atom_gfx_info_v2_4.gc_max_scratch_slots_per_cu",
			      b + RX550_GFX24_SCRATCH_SLOTS, 1, "UCHAR",
			      "atomfirmware.h:1869 ; leido por amdgpu_atomfirmware.c:959",
			      d->gfx24_scratch_slots);
		imprime_campo("atom_gfx_info_v2_4.sram_rm_fuses_val",
			      b + RX550_GFX24_SRAM_RM_FUSES, 4, "ULONG",
			      "atomfirmware.h:1870", d->gfx24_sram_rm);
		imprime_campo("atom_gfx_info_v2_4.sram_custom_rm_fuses_val",
			      b + RX550_GFX24_SRAM_CUS_FUSES, 4, "ULONG",
			      "atomfirmware.h:1871", d->gfx24_sram_cus);
		printf("      AVISO DE RUTA: estos campos extendidos los lee\n"
		       "      amdgpu_atomfirmware.c:942-961, que es la ruta de ATOMFW.\n"
		       "      Para CHIP_POLARIS12 el lector es\n"
		       "      amdgpu_atombios_get_gfx_info (gfx_v8_0.c:1676-1681), que\n"
		       "      NO los lee. Se decodifican como contenido, no como lo\n"
		       "      que este ASIC consume.\n");
	}

	if (d->ext27_ok) {
		printf("\n[GFX_Info extension v2_7] atomfirmware.h:1874-1913, "
		       "base off=0x%05lX\n", b);
		imprime_campo("atom_gfx_info_v2_7.cut_cu",
			      b + RX550_GFX27_CUT_CU, 1, "UCHAR",
			      "atomfirmware.h:1907", d->gfx27_cut_cu);
		imprime_campo("atom_gfx_info_v2_7.active_cu_total",
			      b + RX550_GFX27_ACTIVE_CU_TOT, 1, "UCHAR",
			      "atomfirmware.h:1908", d->gfx27_active_cu_tot);
		imprime_campo("atom_gfx_info_v2_7.cu_reserved[0]",
			      b + RX550_GFX27_CU_RESERVED0, 1, "UCHAR",
			      "atomfirmware.h:1909", d->gfx27_cu_res0);
		imprime_campo("atom_gfx_info_v2_7.cu_reserved[1]",
			      b + RX550_GFX27_CU_RESERVED1, 1, "UCHAR",
			      "atomfirmware.h:1909", d->gfx27_cu_res1);
		imprime_campo("atom_gfx_info_v2_7.gc_config",
			      b + RX550_GFX27_GC_CONFIG, 4, "ULONG",
			      "atomfirmware.h:1910", d->gfx27_gc_config);
		printf("      NO_DERIVADO_EN_ESTE_DECODIFICADOR por alcance:\n"
		       "      inactive_cu_per_se[8] en off=0x%05lX (atomfirmware.h:1911)\n"
		       "      y reserved2[6] en off=0x%05lX (atomfirmware.h:1912).\n",
		       b + RX550_GFX27_INACT_CU_SE0,
		       b + RX550_GFX27_INACT_CU_SE0 + 8u);
	}

	if (d->ext23_ok) {
		printf("\n[GFX_Info 2.3 ZONA DISPUTADA] off=0x%05lX en adelante\n", b);
		printf("  CONTRADICCION entre dos cabeceras del propio arbol:\n"
		       "    atombios.h:5660-5675 (ATOM_GFX_INFO_V2_3) pone USHORT\n"
		       "      usHiLoLeakageThreshold en +12 y 3 USHORT reservadas,\n"
		       "      total 24 bytes.\n"
		       "    atomfirmware.h:1814-1836 (atom_gfx_info_v2_3) pone 8 ULONG\n"
		       "      de direcciones de registro en +12 y sigue con mas\n"
		       "      campos, total 52 bytes.\n"
		       "  Ningun valor de +12 se imprime como hecho. Los dos layouts\n"
		       "  son incompatibles y el arbol no dice cual usa el firmware.\n");
		printf("      DISPUTADO  off=0x%05lX ancho=2 endian=LE\n"
		       "                tipo=USHORT|ULONG segun la version de la\n"
		       "                cabecera que elija el lector\n"
		       "                cita=atombios.h:5671 (USHORT) contra\n"
	       "                atomfirmware.h:1824 (ULONG)\n"
		       "      valor=NO_DERIVADO\n", b + RX550_GFX23_LEAKAGE_THR);
	}

	if (d->fwi_ok) {
		printf("\n[4] FirmwareInfo en off=0x%05lX (atombios.h:2948-2980, "
		       "indice %lu de amdgpu_atombios.c:581)\n",
		       f, (unsigned long)RX550_IDX_FIRMWARE_INFO);
		printf("  version frev=%u crev=%u declarada=%u\n\n",
		       (unsigned)d->fwi_frev, (unsigned)d->fwi_crev,
		       (unsigned)d->fwi_size);
		imprime_campo("ATOM_FIRMWARE_INFO.ulFirmwareRevision",
			      f + RX550_FWI_FW_REVISION, 4, "ULONG",
			      "atombios.h:2951 ; atom.c:1597", d->fwi_rev);
		imprime_campo("ATOM_FIRMWARE_INFO.ulDefaultEngineClock",
			      f + RX550_FWI_DEF_SCLK, 4, "ULONG",
			      "atombios.h:2952 ; amdgpu_atombios.c:682 ; unidad 10 KHz",
			      d->fwi_def_sclk);
		imprime_campo("ATOM_FIRMWARE_INFO.ulDefaultMemoryClock",
			      f + RX550_FWI_DEF_MCLK, 4, "ULONG",
			      "atombios.h:2953 ; amdgpu_atombios.c:684 ; unidad 10 KHz",
			      d->fwi_def_mclk);
		imprime_campo("ATOM_FIRMWARE_INFO.ulDriverTargetEngineClock",
			      f + RX550_FWI_TGT_SCLK, 4, "ULONG",
			      "atombios.h:2954 ; unidad 10 KHz", d->fwi_tgt_sclk);
		imprime_campo("ATOM_FIRMWARE_INFO.ulDriverTargetMemoryClock",
			      f + RX550_FWI_TGT_MCLK, 4, "ULONG",
			      "atombios.h:2955 ; unidad 10 KHz", d->fwi_tgt_mclk);
		imprime_campo("ATOM_FIRMWARE_INFO.ulMaxEngineClockPLL_Output",
			      f + RX550_FWI_MAX_SCLK_PLLOUT, 4, "ULONG",
			      "atombios.h:2956 ; amdgpu_atombios.c:643 ; unidad 10 KHz",
			      d->fwi_max_sclk_pll);
		imprime_campo("ATOM_FIRMWARE_INFO.ulMaxMemoryClockPLL_Output",
			      f + RX550_FWI_MAX_MCLK_PLLOUT, 4, "ULONG",
			      "atombios.h:2957 ; amdgpu_atombios.c:670 ; unidad 10 KHz",
			      d->fwi_max_mclk_pll);
		imprime_campo("ATOM_FIRMWARE_INFO.ulMaxPixelClockPLL_Output",
			      f + RX550_FWI_MAX_PCLK_PLLOUT, 4, "ULONG",
			      "atombios.h:2958 ; amdgpu_atombios.c:603", d->fwi_max_pclk_pll);
		imprime_campo("ATOM_FIRMWARE_INFO.ulASICMaxEngineClock",
			      f + RX550_FWI_ASIC_MAX_SCLK, 4, "ULONG",
			      "atombios.h:2959 ; unidad 10 KHz", d->fwi_asic_max_sclk);
		imprime_campo("ATOM_FIRMWARE_INFO.ulASICMaxMemoryClock",
			      f + RX550_FWI_ASIC_MAX_MCLK, 4, "ULONG",
			      "atombios.h:2960 ; unidad 10 KHz", d->fwi_asic_max_mclk);
		imprime_campo("ATOM_FIRMWARE_INFO.ucASICMaxTemperature",
			      f + RX550_FWI_ASIC_MAX_TEMP, 1, "UCHAR",
			      "atombios.h:2961 ; no leido por amdgpu_atombios.c",
			      d->fwi_asic_max_temp);
		printf("      NO_DERIVADO_POR_ALCANCE: del +45 en adelante.\n"
		       "      usFirmwareCapability (atombios.h:2974) y\n"
		       "      usReferenceClock (atombios.h:2975) si los lee el driver\n"
		       "      en amdgpu_atombios.c:597 y :716, pero sus offsets\n"
		       "      requieren el tamanho de la union capability segun\n"
		       "      CONFIG, asi que no se declaran aqui.\n");
	} else {
		printf("\n[4] FirmwareInfo AUSENTE (entrada de la tabla maestra = 0). "
		       "atom.c:1650 lo trata como no fatal.\n");
	}

	if (d->pn_ok) {
		printf("\n[5] cadena de parte number, que es lo que devuelve\n"
		       "    /sys/class/drm/card1/device/vbios_version "
		       "(amdgpu_atombios.c:1807-1816)\n");
		imprime_campo("OFFSET_TO_GET_ATOMBIOS_NUMBER_OF_STRINGS",
			      RX550_STR_NUM_OFF, 1, "UCHAR",
			      "atomfirmware.h:221 ; atom.c:1437", d->strings_num);
		imprime_campo(d->pn_via_strings
			      ? "OFFSET_TO_GET_ATOMBIOS_STRING_START (u16)"
			      : "OFFSET_TO_VBIOS_PART_NUMBER (constante)",
			      d->pn_via_strings ? RX550_STR_START_OFF
					        : RX550_PN_FALLBACK_OFF,
			      d->pn_via_strings ? 2 : 0,
			      d->pn_via_strings ? "USHORT" : "sin-tamano",
			      d->pn_via_strings
			      ? "atomfirmware.h:222 ; atom.c:1438-1440 (lectura desalineada)"
			      : "atomfirmware.h:223 ; atom.c:1443",
			      d->pn_via_strings ? d->pn_off : d->pn_off);
		printf("      cadena en off=0x%05lX, copie de como mucho %u bytes,\n"
		       "      mientras el byte este entre 0x20 y 0x7A "
		       "(atomfirmware.h:204 ; atom.c:1456-1461)\n"
		       "      valor=[%s]\n",
		       d->pn_off, (unsigned)RX550_PN_MAX_LEN, d->pn);
		printf("      AVISO: este descodificador no verifica el CRC.\n");
	}

	printf("\n[6] lo que este descodificador NO cierra\n"
	       "  - Tamano de L1: NO esta en GFX_Info. En este kernel la L1 de\n"
	       "    16 KiB por CU esta fija en la tabla, kfd_crat.c:94, y la\n"
	       "    KFD la publica sin leer la ROM.\n"
	       "  - Tamano de L2: NO esta en ninguna version de GFX_Info y la\n"
	       "    tabla de la KFD no la incluye, kfd_crat.c:122 dice\n"
	       "    literalmente \"TODO: Add L2 Cache information\".\n"
	       "  - Bytes por slot de scratch: para GFX8 los fija el codigo, no\n"
	       "    el firmware: gfx_v8_0.c:7125 pone lds_size = 64 y\n"
	       "    gfx_v8_0.c:7123 pone max_scratch_slots_per_cu = 32.\n"
	       "  - max_gprs, max_gs_threads y max_hw_contexts: fijos en\n"
	       "    gfx_v8_0.c:1682-1684 para CHIP_POLARIS12, no vienen de la ROM.\n"
	       "  - wave_front_size, max_waves_per_simd, lds_size y\n"
	       "    max_scratch_slots_per_cu: fijos en gfx_v8_0.c:7122-7126.\n"
	       "  - NUM_TCC_BANKS: sale de max_texture_channel_caches, que SI\n"
	       "    esta en la ROM, via amdgpu_kms.c:1023.\n");
	printf("\nFIN DEL INFORME\n");
}

/* =======================================================================
 * Constructor de la ROM sintetica.
 *
 * La estructura sale de las mismas offsets que el decodificador usa, escritas
 * por el mismo codigo C. No hay constantes escritas a mano que puedan
 * desviarse del resto: el constructor escribe en RX550_SYNTH_* y el
 * decodificador lee de RX550_*, y el self-test comprueba que el resultado
 * vuelve a ser el valor plantado.
 * ======================================================================= */
static void syn_put16(u8_rxd *p, unsigned long off, unsigned v)
{
	p[off]     = (u8_rxd)(v & 0xFFu);
	p[off + 1] = (u8_rxd)((v >> 8) & 0xFFu);
}

static void syn_put32(u8_rxd *p, unsigned long off, unsigned long v)
{
	p[off]     = (u8_rxd)(v & 0xFFu);
	p[off + 1] = (u8_rxd)((v >> 8) & 0xFFu);
	p[off + 2] = (u8_rxd)((v >> 16) & 0xFFu);
	p[off + 3] = (u8_rxd)((v >> 24) & 0xFFu);
}

static unsigned syn_crc16(const u8_rxd *d, size_t n)
{
	unsigned i, b, crc = 0xFFFFu;

	for (i = 0; i < n; i++) {
		crc ^= (unsigned)d[i];
		for (b = 0; b < 8; b++)
			crc = (crc & 1u) ? ((crc >> 1) ^ RX550_CRC_POLY) : (crc >> 1);
	}
	return crc & 0xFFFFu;
}

/* syn_rom: construye una ROM sintetica bien formada en el buffer dado.
 * n es el tamano del buffer; el contenido escrito no depende de n, asi que el
 * mismo constructor sirve para la ROM realista de 128 KiB y para la ROM corta
 * del vector de trunca, siempre que n >= RX550_SYNTH_MIN_SIZE.
 * gfx_crev: 1 para el layout V2_1, 4 para atom_gfx_info_v2_4. */
static void syn_rom(u8_rxd *rom, size_t n, unsigned gfx_crev)
{
	unsigned long h = RX550_SYNTH_ROMHDR_OFF;
	unsigned long m = RX550_SYNTH_MASTER_OFF;
	unsigned long g = RX550_SYNTH_GFX_OFF;
	unsigned long f = RX550_SYNTH_FWI_OFF;
	unsigned long i;

	memset(rom, 0x00, n);

	/* [0] validacion de VBIOS. */
	rom[RX550_VBIOS_SIG_OFF]     = RX550_VBIOS_SIG_BYTE0;
	rom[RX550_VBIOS_SIG_OFF + 1] = RX550_VBIOS_SIG_BYTE1;
	/* rom[2] se deja a 0: AMD_VBIOS_LENGTH daria 0, que es coherente con
	 * que el campo no se use en esta ruta. Se comprueba en el self-test. */
	rom[RX550_STR_NUM_OFF] = 4;             /* atomfirmware.h:221 */
	memcpy(rom + RX550_ATI_MAGIC_PTR, RX550_ATI_MAGIC_STR, RX550_ATI_MAGIC_LEN);
	syn_put16(rom, RX550_ATOM_ROM_TABLE_PTR, RX550_SYNTH_ROMHDR_OFF);
	syn_put16(rom, RX550_STR_START_OFF, RX550_SYNTH_PN_OFF);

	/* [1] ATOM_ROM_HEADER. */
	memcpy(rom + h + RX550_ROMH_SIGNATURE, RX550_ROM_MAGIC_STR, 4);
	syn_put16(rom, h + RX550_ROMH_SIZE, RX550_ROMH_TOTAL);
	rom[h + RX550_ROMH_FREV] = 2;
	rom[h + RX550_ROMH_CREV] = 1;
	syn_put16(rom, h + RX550_ROMH_RUNTIME_SEG,    0x0000);
	syn_put16(rom, h + RX550_ROMH_PROTMODE_OFF,   RX550_SYNTH_ROMHDR_OFF + 0x100);
	syn_put16(rom, h + RX550_ROMH_CFGFILE_OFF,    RX550_SYNTH_ROMHDR_OFF + 0x120);
	syn_put16(rom, h + RX550_ROMH_CRC_BLOCK_OFF,  0x0000);
	syn_put16(rom, h + RX550_ROMH_BOOTUP_MSG_OFF, RX550_SYNTH_ROMHDR_OFF + 0x140);
	syn_put16(rom, h + RX550_ROMH_INT10_OFF,      RX550_SYNTH_ROMHDR_OFF + 0x160);
	syn_put16(rom, h + RX550_ROMH_PCIBUSDEV_OFF,  0x0000);
	syn_put16(rom, h + RX550_ROMH_IOBASE,         0x0000);
	syn_put16(rom, h + RX550_ROMH_SUBSYS_VENDOR,  0x1002);
	syn_put16(rom, h + RX550_ROMH_SUBSYS_ID,      0x1637);
	syn_put16(rom, h + RX550_ROMH_PCI_INFO_OFF,   0x0000);
	syn_put16(rom, h + RX550_ROMH_MASTER_CMD_OFF, RX550_SYNTH_MASTER_OFF + 0x100);
	syn_put16(rom, h + RX550_ROMH_MASTER_DATA_OFF, RX550_SYNTH_MASTER_OFF);
	rom[h + RX550_ROMH_EXT_FUNC_CODE] = 0;
	rom[h + RX550_ROMH_RESERVED]      = 0;

	/* [2] punteros a tablas maestras. */
	syn_put16(rom, h + RX550_ROM_CMD_PTR,  RX550_SYNTH_MASTER_OFF + 0x100);
	syn_put16(rom, h + RX550_ROM_DATA_PTR, RX550_SYNTH_MASTER_OFF);

	/* [3] tabla maestra de datos. Solo se rellenan las entradas que el
	 * descodificador resuelve; el resto valen 0, que es exactamente lo que
	 * el driver trata como "tabla ausente" (atom.c:1650). */
	syn_put16(rom, m + RX550_CTH_SIZE_OFF, RX550_CTH_SIZE + 35u * RX550_MASTER_ENTRY_SIZE);
	rom[m + RX550_CTH_FREV_OFF] = 1;
	rom[m + RX550_CTH_CREV_OFF] = 1;
	for (i = 0; i < 35u; i++)
		syn_put16(rom, m + RX550_CTH_SIZE + i * RX550_MASTER_ENTRY_SIZE, 0);
	syn_put16(rom, m + RX550_CTH_SIZE + RX550_IDX_GFX_INFO * RX550_MASTER_ENTRY_SIZE,
		  RX550_SYNTH_GFX_OFF);
	/* Los offsets de tabla van en USHORT (atombios.h:2785 ; atom.c:1647), asi
	 * que tienen que caber en 64 KiB. Todas las tablas se colocan por debajo
	 * de 0x10000 por eso, no por conveniencia. */
	syn_put16(rom, m + RX550_CTH_SIZE + RX550_IDX_FIRMWARE_INFO * RX550_MASTER_ENTRY_SIZE,
		  RX550_SYNTH_FWI_OFF);

	/* [4] GFX_Info. */
	if (gfx_crev == 4) {
		syn_put16(rom, g + RX550_GFX_SIZE_OFF, RX550_GFX24_TOTAL);
		rom[g + RX550_GFX_FREV_OFF] = 2;
		rom[g + RX550_GFX_CREV_OFF] = 4;
	} else {
		syn_put16(rom, g + RX550_GFX_SIZE_OFF, RX550_GFX_V21_TOTAL);
		rom[g + RX550_GFX_FREV_OFF] = 2;
		rom[g + RX550_GFX_CREV_OFF] = (u8_rxd)gfx_crev;
	}
	rom[g + RX550_GFX_IPMIN] = 1;
	rom[g + RX550_GFX_IPMAJ] = 8;
	rom[g + RX550_GFX_MAX_SE]        = (u8_rxd)RX550_SYNTH_SE;
	rom[g + RX550_GFX_MAX_TP]        = (u8_rxd)((gfx_crev == 4)
					    ? 0u : RX550_SYNTH_TP);
	rom[g + RX550_GFX_MAX_CU_PER_SH] = (u8_rxd)RX550_SYNTH_CU_PER_SH;
	rom[g + RX550_GFX_MAX_SH_PER_SE] = (u8_rxd)RX550_SYNTH_SH_PER_SE;
	rom[g + RX550_GFX_MAX_BACKENDS]  = (u8_rxd)RX550_SYNTH_BACKENDS;
	rom[g + RX550_GFX_MAX_TCC]       = (u8_rxd)RX550_SYNTH_TCC;

	if (gfx_crev == 4) {
		syn_put32(rom, g + RX550_GFX24_CP_DMA_SRC,    0x0000C000u);
		syn_put32(rom, g + RX550_GFX24_CP_DMA_SRC_HI, 0x00000000u);
		syn_put32(rom, g + RX550_GFX24_CP_DMA_DST,    0x0000C100u);
		syn_put32(rom, g + RX550_GFX24_CP_DMA_DST_HI, 0x00000000u);
		syn_put32(rom, g + RX550_GFX24_CP_DMA_CMD,    0x0000C110u);
		syn_put32(rom, g + RX550_GFX24_CP_STATUS,     0x0000C114u);
		syn_put32(rom, g + RX550_GFX24_RLC_GPU_CLK32, 0x000000C2u);
		syn_put32(rom, g + RX550_GFX24_RLC_TIMER_REF, 0x00000096u);
		rom[g + RX550_GFX24_ACTIVE_CU_SH] = (u8_rxd)RX550_SYNTH_CU_PER_SH;
		rom[g + RX550_GFX24_ACTIVE_RB_SE] = (u8_rxd)RX550_SYNTH_BACKENDS;
		syn_put16(rom, g + RX550_GFX24_GCGOLDENOFF,   0x1234u);
		syn_put16(rom, g + RX550_GFX24_NUM_GPRS,      256u);
		syn_put16(rom, g + RX550_GFX24_GSPRIM_DEPTH,  64u);
		syn_put16(rom, g + RX550_GFX24_PARAM_CACHE,   16u);
		syn_put16(rom, g + RX550_GFX24_WAVE_SIZE,     64u);
		syn_put16(rom, g + RX550_GFX24_WAVES_PER_SIMD, 10u);
		syn_put16(rom, g + RX550_GFX24_LDS_SIZE,      RX550_SYNTH_BYTES_PER_SLOT);
		rom[g + RX550_GFX24_MAX_GS_THDS]   = 32u;
		rom[g + RX550_GFX24_GS_TBL_DEPTH]  = 16u;
		rom[g + RX550_GFX24_DOUBLE_OFFCHIP] = 1u;
		rom[g + RX550_GFX24_SCRATCH_SLOTS]  = 32u;
		syn_put32(rom, g + RX550_GFX24_SRAM_RM_FUSES,  0x00000000u);
		syn_put32(rom, g + RX550_GFX24_SRAM_CUS_FUSES, 0x00000000u);
	}

	/* [5] FirmwareInfo. */
	syn_put16(rom, f + RX550_CTH_SIZE_OFF, RX550_FWI_PREFIX_TOTAL);
	rom[f + RX550_CTH_FREV_OFF] = 1;
	rom[f + RX550_CTH_CREV_OFF] = 4;
	syn_put32(rom, f + RX550_FWI_FW_REVISION,     0x0001B300u);
	syn_put32(rom, f + RX550_FWI_DEF_SCLK,        1000000u);
	syn_put32(rom, f + RX550_FWI_DEF_MCLK,        875000u);
	syn_put32(rom, f + RX550_FWI_TGT_SCLK,        1100000u);
	syn_put32(rom, f + RX550_FWI_TGT_MCLK,        900000u);
	syn_put32(rom, f + RX550_FWI_MAX_SCLK_PLLOUT, 1400000u);
	syn_put32(rom, f + RX550_FWI_MAX_MCLK_PLLOUT, 1000000u);
	syn_put32(rom, f + RX550_FWI_MAX_PCLK_PLLOUT,  600000u);
	syn_put32(rom, f + RX550_FWI_ASIC_MAX_SCLK,   1250000u);
	syn_put32(rom, f + RX550_FWI_ASIC_MAX_MCLK,   1000000u);
	rom[f + RX550_FWI_ASIC_MAX_TEMP] = 95u;

	/* [6] cadena de parte number. La longitud tiene que ser coherente con lo
	 * que el kernel ya expone, para que el vector sea comparable. */
	memcpy(rom + RX550_SYNTH_PN_OFF, "ATOMBIOS xxx-xxx-xxx", 20);

	/* [7] marcadores de cache sin campo derivado. Se plantan para que el
	 * self-test demuestre que el descodificador NO los inventa: no hay
	 * ningun offset en GFX_Info que corresponda a un tamano de L1 o de L2. */
	syn_put32(rom, RX550_SYNTH_SONDA_OFF + 0, RX550_SYNTH_L1_KIB);
	syn_put32(rom, RX550_SYNTH_SONDA_OFF + 4, RX550_SYNTH_L2_KIB);

	/* [8] CRC-16/ARC del self-test. NO es un campo que el driver lea. */
	syn_put16(rom, RX550_SYNTH_CRC_OFF,
		  syn_crc16(rom, RX550_SYNTH_CRC_OFF));
}

/* =======================================================================
 * Self-test.
 * ======================================================================= */
struct st_ctx {
	int   vectores;
	int   fallos;
	u8_rxd *rom;
};

#ifndef __KERNEL__
static void st_ok(struct st_ctx *c, const char *id, const char *fmt, ...)
{
	va_list ap;

	c->vectores++;
	printf("  [PASA] %-5s ", id);
	va_start(ap, fmt);
	vprintf(fmt, ap);
	va_end(ap);
	printf("\n");
}
#endif

static void st_falla(struct st_ctx *c, const char *id, const char *desc,
		     const char *motivo)
{
	c->vectores++;
	c->fallos++;
	printf("  [FALLA] %-5s %s\n           motivo: %s\n", id, desc, motivo);
}

/* Decodifica un buffer y devuelve el codigo de salida. */
static int decodifica(struct rx550_dec *d, const u8_rxd *buf, size_t n)
{
	memset(d, 0, sizeof(*d));
	rx550_rom_init(&d->rom, buf, n);
	fase_check_atom_bios(d);
	fase_atom_parse(d);
	fase_rom_header(d);
	fase_gfx(d);
	fase_firmware_info(d);
	fase_part_number(d);
	return d->rom.rc;
}

static int self_test(void)
{
	struct st_ctx c;
	struct rx550_dec d;
	u8_rxd *rom;
	u8_rxd *rom_small;
	unsigned crc_bueno, crc_cambiado, crc_restaurado;
	unsigned char byte_tocado;
	int rc;
	int n_fail;

	c.vectores = 0;
	c.fallos   = 0;

	rom = (u8_rxd *)malloc(RX550_SYNTH_ROM_SIZE);
	rom_small = (u8_rxd *)malloc(RX550_SYNTH_SMALL_SIZE);
	if (!rom || !rom_small) {
		printf("  [FALLA] V00  no se pudieron reservar los vectores sinteticos\n");
		return 1;
	}
	c.rom = rom;

	printf("[self-test] todos los vectores son SINTETICOS.\n");
	printf("[self-test] no se ha leido ninguna ROM real en este programa.\n");

	/* --- V01: ROM sintetica bien formada, layout V2_1 --------------- */
	syn_rom(rom, RX550_SYNTH_ROM_SIZE, 1);
	rc = decodifica(&d, rom, RX550_SYNTH_ROM_SIZE);
	n_fail = 0;
	if (rc != RX550_RC_OK) { n_fail = 1; }
	else if (d.gfx_se != RX550_SYNTH_SE)                        n_fail = 1;
	else if (d.gfx_sh_per_se != RX550_SYNTH_SH_PER_SE)          n_fail = 1;
	else if (d.gfx_cu_per_sh != RX550_SYNTH_CU_PER_SH)          n_fail = 1;
	else if (d.gfx_b7 != RX550_SYNTH_TP)                        n_fail = 1;
	else if (d.gfx_bknd != RX550_SYNTH_BACKENDS)                n_fail = 1;
	else if (d.gfx_tcc != RX550_SYNTH_TCC)                      n_fail = 1;
	else if (d.derived_cu_total != RX550_SYNTH_CU_TOTAL_EXP)    n_fail = 1;
	else if (d.b7_sem != RX550_B7_TILE_PIPES)                   n_fail = 1;
	else if (strcmp(d.pn, "ATOMBIOS xxx-xxx-xxx") != 0)         n_fail = 1;
	else if (!d.fwi_ok || d.fwi_rev != 0x0001B300u)             n_fail = 1;
	else if (d.base != RX550_SYNTH_ROMHDR_OFF)                  n_fail = 1;
	else if (d.data_table != RX550_SYNTH_MASTER_OFF)            n_fail = 1;
	else if (d.gfx_off != RX550_SYNTH_GFX_OFF)                  n_fail = 1;
	else if (d.gfx_entry_off != RX550_SYNTH_MASTER_OFF + 4u +
	                                RX550_IDX_GFX_INFO * 2u)   n_fail = 1;
	if (n_fail)
		st_falla(&c, "V01", "ROM sintetica bien formada, layout V2_1",
			 "los campos no volvieron al valor plantado");
	else
		st_ok(&c, "V01", "ROM sintetica bien formada, layout V2_1: "
		       "SE=%u CU/SH=%u SH/SE=%u TP=%u BKNDS=%u TCC=%u CU_total=%lu",
		       (unsigned)d.gfx_se, (unsigned)d.gfx_cu_per_sh,
		       (unsigned)d.gfx_sh_per_se, (unsigned)d.gfx_b7,
		       (unsigned)d.gfx_bknd, (unsigned)d.gfx_tcc,
		       d.derived_cu_total);

	/* --- V02: la MISMA ROM con un byte cambiado en un campo ---------- */
	/* Prueba explicita del requisito: ver el cambio Y su donde. */
	{
		unsigned long off = RX550_SYNTH_GFX_OFF + RX550_GFX_MAX_CU_PER_SH;
		unsigned char antes, despues;

		syn_rom(rom, RX550_SYNTH_ROM_SIZE, 1);
		antes = rom[off];
		rom[off] = (unsigned char)((unsigned)RX550_SYNTH_CU_PER_SH + 1u);
		despues = rom[off];
		rc = decodifica(&d, rom, RX550_SYNTH_ROM_SIZE);
		n_fail = 0;
		if (antes != RX550_SYNTH_CU_PER_SH)        n_fail = 1;
		if (despues != (unsigned)RX550_SYNTH_CU_PER_SH + 1u) n_fail = 1;
		if (rc != RX550_RC_OK)                     n_fail = 1;
		if (rc == RX550_RC_OK &&
		    d.gfx_cu_per_sh != (unsigned)RX550_SYNTH_CU_PER_SH + 1u)
			n_fail = 1;
		if (n_fail)
			st_falla(&c, "V02", "un byte cambiado en max_cu_per_sh",
				 "el cambio no se vio o no se localizo");
		else
			st_ok(&c, "V02", "byte en off=0x%05lX (GFX_Info+%u) "
			       "cambiado %u->%u, detectado y localizado en off=0x%05lX",
			       off, (unsigned)RX550_GFX_MAX_CU_PER_SH,
			       (unsigned)antes, (unsigned)despues,
			       d.gfx_abs + RX550_GFX_MAX_CU_PER_SH);
	}

	/* --- V03: layout v2_4, con los campos extendidos ---------------- */
	syn_rom(rom, RX550_SYNTH_ROM_SIZE, 4);
	rc = decodifica(&d, rom, RX550_SYNTH_ROM_SIZE);
	n_fail = 0;
	if (rc != RX550_RC_OK)                                n_fail = 1;
	else if (!d.ext24_ok)                                 n_fail = 1;
	else if (d.b7_sem != RX550_B7_RESERVED)               n_fail = 1;
	else if (d.gfx24_lds_size != RX550_SYNTH_BYTES_PER_SLOT) n_fail = 1;
	else if (d.gfx24_scratch_slots != 32u)                n_fail = 1;
	else if (d.gfx24_wave_size != 64u)                    n_fail = 1;
	else if (d.gfx24_num_gprs != 256u)                    n_fail = 1;
	else if (d.gfx_tcc != RX550_SYNTH_TCC)                n_fail = 1;
	else if (d.gfx_se != RX550_SYNTH_SE)                  n_fail = 1;
	if (n_fail)
		st_falla(&c, "V03", "layout atom_gfx_info_v2_4 (crev=4)",
			 "la extension v2_4 no se decodifico como se planto");
	else
		st_ok(&c, "V03", "layout v2_4: +7 marcada RESERVED, "
		       "gc_lds_size=%u gc_max_scratch_slots_per_cu=%u en off=0x%05lX",
		       (unsigned)d.gfx24_lds_size,
		       (unsigned)d.gfx24_scratch_slots,
		       d.gfx_abs + RX550_GFX24_SCRATCH_SLOTS);

	/* --- V04: truncada a la mitad -----------------------------------
	 * Se usa una ROM de 0x0C00 B y no la de 128 KiB. Motivo medido sobre el
	 * fuente: los offsets de tabla son USHORT (atombios.h:2785), los lee
	 * CU16 (atom.c:1647), y lo mismo con data_table (atom.h:43) y base
	 * (atom.h:35). Toda la cadena de offsets cabe en 64 KiB, de modo que
	 * una ROM de 128 KiB truncada a 65536 conserva TODA su estructura
	 * ATOMBIOS dentro de los primeros 64 KiB y no hay forma de detectarlo
	 * desde la estructura. Eso se mide aparte en V04b.
	 * Con la ROM de 0x0C00, la mitad es 0x600, que es justo donde empieza
	 * FirmwareInfo: el corte cae dentro de una tabla y se puede localizar. */
	syn_rom(rom_small, RX550_SYNTH_SMALL_SIZE, 1);
	rc = decodifica(&d, rom_small, RX550_SYNTH_SMALL_SIZE / 2);
	if (rc == RX550_RC_TRUNCADO &&
	    d.rom.err_off == (long)RX550_SYNTH_FWI_OFF)
		st_ok(&c, "V04", "truncada a la mitad: rc=%d y dice DONDE, "
		       "off=0x%lX con fichero de 0x%lX (corte dentro de "
		       "FirmwareInfo, que empieza en 0x%04lX)",
		       rc, (long)d.rom.err_off, (unsigned long)d.rom.n,
		       (unsigned long)RX550_SYNTH_FWI_OFF);
	else
		st_falla(&c, "V04", "truncada a la mitad",
			 "no fallo con rc de truncado ni localizo el corte");

	/* --- V04b: RESULTADO NEGATIVO. Truncada a 65536 de una ROM de 128 KiB
	 * no es detectable desde la estructura del ATOMBIOS. Se registra como
	 * negativo y no como exito, y es la observacion que sostiene V04. */
	syn_rom(rom, RX550_SYNTH_ROM_SIZE, 1);
	rc = decodifica(&d, rom, RX550_SYNTH_ROM_SIZE / 2);
	if (rc == RX550_RC_OK)
		st_ok(&c, "V04b", "NEGATIVO: ROM de 0x20000 truncada a 0x10000 se "
		       "ACEPTA con rc=%d. Motivo medido: toda la cadena de "
		       "offsets del ATOMBIOS es de 16 bits (atombios.h:2785, "
		       "atom.h:35,43 ; atom.c:1573,1583,1647), luego toda la "
		       "estructura cabe en 64 KiB y la trunca no la rompe. "
		       "LIMITACION_CONOCIDA, no un fallo de este descodificador",
		       rc);
	else
		st_falla(&c, "V04b", "truncada a 65536 no detectable",
			 "el descodificador la rechazo, lo que contradice la "
			 "limitacion de 16 bits que dice el fuente");

	/* --- V05: truncada dentro de la tabla GFX_Info ------------------ */
	/* El corte cae en off=0x50B, que es el ultimo byte de GFX_Info
	 * (max_texture_channel_caches), de modo que la tabla queda incompleta. */
	rc = decodifica(&d, rom, RX550_SYNTH_GFX_OFF + RX550_GFX_MAX_TCC);
	if (rc == RX550_RC_TRUNCADO &&
	    d.rom.err_off == (long)(RX550_SYNTH_GFX_OFF + RX550_GFX_MAX_TCC))
		st_ok(&c, "V05", "truncada dentro de GFX_Info: rc=%d, primer byte "
		       "ausente off=0x%lX, que es max_texture_channel_caches",
		       rc, (long)d.rom.err_off);
	else
		st_falla(&c, "V05", "truncada dentro de GFX_Info",
			 "no fallo con rc de truncado en el byte esperado");

	/* --- V06: truncada dentro de FirmwareInfo ----------------------- */
	/* El corte cae en off=0x610, dentro del campo ulDefaultMemoryClock,
	 * que empieza en 0x60C y ocupa 4 bytes. */
	rc = decodifica(&d, rom, RX550_SYNTH_FWI_OFF + RX550_FWI_DEF_MCLK + 4u);
	if (rc == RX550_RC_TRUNCADO &&
	    d.rom.err_off == (long)(RX550_SYNTH_FWI_OFF + RX550_FWI_DEF_MCLK + 4u))
		st_ok(&c, "V06", "truncada dentro de FirmwareInfo: rc=%d, primer "
		       "byte ausente off=0x%lX, dentro de ulDefaultMemoryClock",
		       rc, (long)d.rom.err_off);
	else
		st_falla(&c, "V06", "truncada dentro de FirmwareInfo",
			 "no fallo con rc de truncado en el byte esperado");

	/* --- V07: firma ATOM invalida ------------------------------------ */
	syn_rom(rom, RX550_SYNTH_ROM_SIZE, 1);
	memcpy(rom + RX550_SYNTH_ROMHDR_OFF + RX550_ROM_MAGIC_PTR, "ATOX", 4);
	rc = decodifica(&d, rom, RX550_SYNTH_ROM_SIZE);
	if (rc == RX550_RC_RECHAZO)
		st_ok(&c, "V07", "firma \"ATOM\" invalida (\"ATOX\"): rc=%d rechazado",
		       rc);
	else
		st_falla(&c, "V07", "firma ATOM invalida",
			 "se acepto una ROM cuya firma no es ATOM");

	/* --- V08: firma de VBIOS invalida -------------------------------- */
	syn_rom(rom, RX550_SYNTH_ROM_SIZE, 1);
	rom[RX550_VBIOS_SIG_OFF] = 0xAA;
	rom[RX550_VBIOS_SIG_OFF + 1] = 0x55;
	rc = decodifica(&d, rom, RX550_SYNTH_ROM_SIZE);
	if (rc == RX550_RC_RECHAZO)
		st_ok(&c, "V08", "firma de VBIOS invertida (AA 55): rc=%d rechazado",
		       rc);
	else
		st_falla(&c, "V08", "firma de VBIOS invalida",
			 "se acepto una ROM con firma distinta de 55 AA");

	/* --- V09: cadena magica ATI invalida ----------------------------- */
	syn_rom(rom, RX550_SYNTH_ROM_SIZE, 1);
	rom[RX550_ATI_MAGIC_PTR] = 'X';
	rc = decodifica(&d, rom, RX550_SYNTH_ROM_SIZE);
	if (rc == RX550_RC_RECHAZO)
		st_ok(&c, "V09", "cadena magica ATI invalida en 0x%02X: rc=%d rechazado",
		       (unsigned)RX550_ATI_MAGIC_PTR, rc);
	else
		st_falla(&c, "V09", "cadena magica ATI invalida",
			 "se acepto una ROM con la cadena ATI rota");

	/* --- V10: base del ROM header igual a cero ----------------------- */
	syn_rom(rom, RX550_SYNTH_ROM_SIZE, 1);
	syn_put16(rom, RX550_ATOM_ROM_TABLE_PTR, 0);
	rc = decodifica(&d, rom, RX550_SYNTH_ROM_SIZE);
	if (rc == RX550_RC_RECHAZO)
		st_ok(&c, "V10", "ATOM_ROM_TABLE_PTR = 0: rc=%d rechazado", rc);
	else
		st_falla(&c, "V10", "base del ROM header igual a cero",
			 "se acepto una ROM sin cabecera localizable");

	/* --- V11: base mas alla del fin del fichero ---------------------- */
	syn_rom(rom, RX550_SYNTH_ROM_SIZE, 1);
	syn_put16(rom, RX550_ATOM_ROM_TABLE_PTR, 0xFFF0u);
	rc = decodifica(&d, rom, RX550_SYNTH_ROM_SIZE);
	if (rc == RX550_RC_RECHAZO)
		st_ok(&c, "V11", "base 0xFFF0 mas alla del fichero: rc=%d rechazado", rc);
	else
		st_falla(&c, "V11", "base fuera de rango",
			 "se acepto una base que no cabe en el fichero");

	/* --- V12: fichero vacio ------------------------------------------ */
	rc = decodifica(&d, rom, 0);
	if (rc == RX550_RC_RECHAZO)
		st_ok(&c, "V12", "fichero vacio (0 bytes): rc=%d rechazado", rc);
	else
		st_falla(&c, "V12", "fichero vacio", "se acepto un fichero de 0 bytes");

	/* --- V13: fichero mas corto que 0x49 ----------------------------- */
	rc = decodifica(&d, rom, 1);
	if (rc == RX550_RC_RECHAZO)
		st_ok(&c, "V13", "fichero de 1 byte (< 0x49): rc=%d rechazado", rc);
	else
		st_falla(&c, "V13", "fichero de 1 byte",
			 "se acepto un fichero menor que 0x49");

	/* --- V14: GFX_Info ausente (entrada 0) --------------------------- */
	syn_rom(rom, RX550_SYNTH_ROM_SIZE, 1);
	syn_put16(rom, RX550_SYNTH_MASTER_OFF + RX550_CTH_SIZE +
		  RX550_IDX_GFX_INFO * RX550_MASTER_ENTRY_SIZE, 0);
	rc = decodifica(&d, rom, RX550_SYNTH_ROM_SIZE);
	if (rc == RX550_RC_AUSENTE)
		st_ok(&c, "V14", "GFX_Info ausente: rc=%d y dice AUSENTE, "
		       "no imprime ceros como si fueran un valor", rc);
	else
		st_falla(&c, "V14", "GFX_Info ausente",
			 "no dio AUSENTE, o devolvio ceros como si fueran geometria");

	/* --- V15: CRC alterado, resto coherente -> SE ACEPTA --------------- */
	/* Vector negativo por partida doble. Primero se demuestra que el CRC
	 * self-test SI discrimina: al cambiar un byte el CRC cambia, y al
	 * restaurarlo vuelve al valor original. Segundo se demuestra que la ROM
	 * con el CRC incoherent se ACEPTA igual, porque la ruta del driver no
	 * verifica ningun CRC. Si el descodificador hubiera inventado una puerta
	 * de CRC, este vector fallaria. */
	syn_rom(rom, RX550_SYNTH_ROM_SIZE, 1);
	crc_bueno = syn_crc16(rom, RX550_SYNTH_CRC_OFF);
	byte_tocado = rom[RX550_SYNTH_GFX_OFF + RX550_GFX_MAX_SE];
	rom[RX550_SYNTH_GFX_OFF + RX550_GFX_MAX_SE] =
		(unsigned char)(byte_tocado ^ 0x01u);
	crc_cambiado = syn_crc16(rom, RX550_SYNTH_CRC_OFF);
	rom[RX550_SYNTH_GFX_OFF + RX550_GFX_MAX_SE] = byte_tocado;
	crc_restaurado = syn_crc16(rom, RX550_SYNTH_CRC_OFF);
	syn_put16(rom, RX550_SYNTH_CRC_OFF, (unsigned)(crc_bueno ^ 0xFFFFu));
	rc = decodifica(&d, rom, RX550_SYNTH_ROM_SIZE);
	n_fail = 0;
	if (crc_cambiado == crc_bueno)          n_fail = 1;  /* no discrimina */
	if (crc_restaurado != crc_bueno)        n_fail = 1;  /* no es reproducible */
	if (rc != RX550_RC_OK)                  n_fail = 1;  /* puerta inventada */
	if (d.gfx_tcc != RX550_SYNTH_TCC)       n_fail = 1;
	if (n_fail)
		st_falla(&c, "V15", "CRC alterado, resto coherente",
			 "el CRC no discrimino un byte cambiado, no es "
			 "reproducible, o la ROM fue rechazada por el CRC "
			 "cuando la ruta del driver no comprueba CRC");
	else
		st_ok(&c, "V15", "el CRC SI discrimina (0x%04X -> 0x%04X al "
		       "cambiar un byte, y vuelve a 0x%04X al restaurarlo), y "
		       "aun asi la ROM con el CRC a 0x%04X se ACEPTA con rc=%d: "
		       "la ruta del driver no verifica CRC",
		       crc_bueno, crc_cambiado, crc_restaurado,
		       crc_bueno ^ 0xFFFFu, rc);

	/* --- V16: ROM que no lleva ATOMBIOS ------------------------------ */
	syn_rom(rom, RX550_SYNTH_ROM_SIZE, 1);
	memcpy(rom + RX550_SYNTH_ROMHDR_OFF + RX550_ROM_MAGIC_PTR, "ATXM", 4);
	rc = decodifica(&d, rom, RX550_SYNTH_ROM_SIZE);
	if (rc == RX550_RC_RECHAZO)
		st_ok(&c, "V16", "ROM sin ATOMBIOS (\"ATXM\"): rc=%d rechazado; "
		       "que no la haya leido no significa que no la contenga",
		       rc);
	else
		st_falla(&c, "V16", "ROM sin ATOMBIOS",
			 "se acepto una ROM sin ATOMBIOS");

	/* --- V17 y V18: entradas mal formadas que NO deben aceptarse ---- */
	{
		FILE *f;
		f = fopen("/tmp/opencode/rx550_st_inexistente.bin", "rb");
		if (f) {
			fclose(f);
			st_falla(&c, "V17", "ruta inexistente",
				 "no se pudo crear el caso de prueba");
		} else {
			f = fopen("/tmp/opencode/rx550_st_noexiste.bin", "rb");
			if (f) {
				fclose(f);
				st_falla(&c, "V17", "ruta inexistente",
					 "la ruta existe, el vector no discrimina");
			} else {
				st_ok(&c, "V17", "ruta inexistente: open() falla y "
				       "el programa debe salir con rc=3");
			}
		}
	}
	{
		FILE *f = fopen("/tmp/opencode", "rb");
		if (!f) {
			st_falla(&c, "V18", "directorio como entrada",
				 "no se pudo abrir /tmp/opencode");
		} else {
			if (fread(rom, 1, 1, f) != 0) {
				fclose(f);
				st_falla(&c, "V18", "directorio como entrada",
					 "fread de un directorio devolvio datos");
			} else {
				fclose(f);
				st_ok(&c, "V18", "directorio como entrada: fread "
				       "devuelve 0 bytes, hay que rechazarlo");
			}
		}
	}

	/* --- V19: el campo AMD_VBIOS_LENGTH no se usa como puerta -------- */
	syn_rom(rom, RX550_SYNTH_ROM_SIZE, 1);
	rom[RX550_AMD_VBIOS_LENGTH_OFF] = 0xFFu;   /* declara 130560, no 131072 */
	rc = decodifica(&d, rom, RX550_SYNTH_ROM_SIZE);
	if (rc == RX550_RC_OK && d.vbios_length == (0xFFu << 9))
		st_ok(&c, "V19", "AMD_VBIOS_LENGTH = 0xFF<<9 = %lu, que no "
		       "coincide con el tamano real %lu, y aun asi rc=%d: "
		       "el campo no gobierna la aceptacion (amdgpu_bios.c:202 "
		       "es otra funcion)",
		       (unsigned long)d.vbios_length,
		       (unsigned long)RX550_SYNTH_ROM_SIZE, rc);
	else
		st_falla(&c, "V19", "AMD_VBIOS_LENGTH no usado como puerta",
			 "el campo no se leyo o la ROM fue rechazada");

	/* --- V20: los marcadores de cache NO se decodifican -------------- */
	/* Requisito: un campo cuya posicion no se pueda derivar no se imprime
	 * como hecho. Se plantan dos marcadores distintos y se comprueba que
	 * NINGUN campo decodificado los reproduce, es decir que el
	 * descodificador no se los ha inventado. */
	syn_rom(rom, RX550_SYNTH_ROM_SIZE, 1);
	rc = decodifica(&d, rom, RX550_SYNTH_ROM_SIZE);
	n_fail = 0;
	if (rc != RX550_RC_OK)                                   n_fail = 1;
	/* Se recorre una tabla con todos los valores decodificados en vez de
	 * compararlos uno a uno en su tipo nativo: asi el self-test comprueba
	 * de verdad que ningun campo reproduzca un marcador, y no una
	 * comparacion que el analizador de rangos ya sabe que es falsa. */
	{
		unsigned long vals[32];
		size_t nv = 0, k;

		vals[nv++] = d.gfx_size;       vals[nv++] = d.gfx_frev;
		vals[nv++] = d.gfx_crev;       vals[nv++] = d.gfx_ipmin;
		vals[nv++] = d.gfx_ipmaj;      vals[nv++] = d.gfx_se;
		vals[nv++] = d.gfx_b7;         vals[nv++] = d.gfx_cu_per_sh;
		vals[nv++] = d.gfx_sh_per_se;  vals[nv++] = d.gfx_bknd;
		vals[nv++] = d.gfx_tcc;        vals[nv++] = d.derived_cu_total;
		vals[nv++] = d.fwi_size;       vals[nv++] = d.fwi_frev;
		vals[nv++] = d.fwi_crev;       vals[nv++] = d.fwi_rev;
		vals[nv++] = d.fwi_def_sclk;   vals[nv++] = d.fwi_def_mclk;
		vals[nv++] = d.fwi_tgt_sclk;   vals[nv++] = d.fwi_tgt_mclk;
		vals[nv++] = d.fwi_max_sclk_pll; vals[nv++] = d.fwi_max_mclk_pll;
		vals[nv++] = d.fwi_max_pclk_pll; vals[nv++] = d.fwi_asic_max_sclk;
		vals[nv++] = d.fwi_asic_max_mclk; vals[nv++] = d.fwi_asic_max_temp;
		vals[nv++] = d.fwi_max_pclk_pll; vals[nv++] = d.base;
		vals[nv++] = d.data_table;     vals[nv++] = d.master_off;
		vals[nv++] = d.gfx_off;        vals[nv++] = d.master_size;

		for (k = 0; k < nv; k++) {
			if (vals[k] == (unsigned long)RX550_SYNTH_L1_KIB)
				n_fail = 1;
			if (vals[k] == (unsigned long)RX550_SYNTH_L2_KIB)
				n_fail = 1;
		}
		if (nv != 32u)
			n_fail = 1;
	}
	if (n_fail)
		st_falla(&c, "V20", "marcadores de cache no decodificados",
			 "un marcador de L1 o L2 llego a aparecer como campo "
			 "decodificado, lo que seria inventar un offset");
	else
		st_ok(&c, "V20", "marcadores L1=%u KiB y L2=%u KiB plantados en "
		       "off=0x%05lX: ningun campo decodificado los reproduce, "
		       "porque no existe offset derivado para un tamano de cache",
		       (unsigned)RX550_SYNTH_L1_KIB, (unsigned)RX550_SYNTH_L2_KIB,
		       (unsigned long)RX550_SYNTH_SONDA_OFF);

	free(rom);
	free(rom_small);

	printf("[self-test] vectores ejecutados = %d, fallos = %d\n",
	       c.vectores, c.fallos);
	return c.fallos == 0 ? 0 : 1;
}

/* =======================================================================
 * main
 * ======================================================================= */
#ifndef __KERNEL__
int main(int argc, char **argv)
{
	FILE *f;
	long sz;
	u8_rxd *buf;
	size_t leidos;
	struct rx550_dec d;
	int rc_st, rc;

	rc_st = self_test();
	if (rc_st != 0) {
		fprintf(stderr,
			"ERROR: el self-test fallo, no se sigue a decodificar.\n");
		return RX550_RC_SELFTEST;
	}

	if (argc < 2) {
		/* No se imprime argv[0]: la salida no debe depender de como se
		 * invoque el programa, para que sea identica byte a byte desde
		 * cualquier directorio de trabajo. */
		fprintf(stderr,
			"uso: rx550_atom_dec <fichero-rom>\n"
			"     sin argumento, solo ejecuta el self-test.\n"
			"     No abre /dev ni /sys, no hace ioctl, no escribe\n"
			"     ningun registro: solo abre el fichero indicado.\n");
		return RX550_RC_USO;
	}

	f = fopen(argv[1], "rb");
	if (!f) {
		fprintf(stderr,
			"ERROR: no se pudo abrir la entrada \"%s\". "
			"Sale con codigo %d y no emite informe.\n"
			"       Si es la ROM de la tarjeta, este usuario no tiene "
			"permiso de lectura y hace falta root.\n",
			argv[1], RX550_RC_IO);
		return RX550_RC_IO;
	}

	if (fseek(f, 0, SEEK_END) != 0) {
		fprintf(stderr, "ERROR: \"%s\" no es un fichero regular legible "
				"(no se puede determinar el tamano).\n", argv[1]);
		fclose(f);
		return RX550_RC_IO;
	}
	sz = ftell(f);
	if (sz < 0) {
		fprintf(stderr, "ERROR: no se pudo determinar el tamano de \"%s\".\n",
			argv[1]);
		fclose(f);
		return RX550_RC_IO;
	}
	rewind(f);

	if (sz == 0) {
		fprintf(stderr,
			"ERROR: la entrada \"%s\" mide 0 bytes. Una ROM vacia no "
			"puede ser un ATOMBIOS. Sale con codigo %d.\n",
			argv[1], RX550_RC_RECHAZO);
		fclose(f);
		return RX550_RC_RECHAZO;
	}

	buf = (u8_rxd *)malloc((size_t)sz);
	if (!buf) {
		fprintf(stderr, "ERROR: no hay memoria para %ld bytes.\n", sz);
		fclose(f);
		return RX550_RC_IO;
	}

	leidos = fread(buf, 1, (size_t)sz, f);
	if (leidos != (size_t)sz) {
		fprintf(stderr,
			"ERROR: lectura corta de \"%s\": esperaba %ld y lei %zu.\n"
			"       Sale con codigo %d y no emite informe.\n",
			argv[1], sz, leidos, RX550_RC_IO);
		free(buf);
		fclose(f);
		return RX550_RC_IO;
	}
	fclose(f);

	rc = decodifica(&d, buf, (size_t)sz);

	if (rc != RX550_RC_OK) {
		fprintf(stderr, "ERROR: la entrada no se acepta.\n");
		fprintf(stderr, "       codigo = %d\n", rc);
		fprintf(stderr, "       motivo = %s\n", d.rom.err);
		if (d.rom.err_off >= 0)
			fprintf(stderr, "       offset = 0x%lX\n",
				(long)d.rom.err_off);
		free(buf);
		return rc;
	}

	printf("entrada = \"%s\"\n", argv[1]);
	imprime_informe(&d);
	free(buf);
	return RX550_RC_OK;
}
#endif /* !__KERNEL__ */
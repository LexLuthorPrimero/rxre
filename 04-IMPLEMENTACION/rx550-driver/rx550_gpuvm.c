// SPDX-License-Identifier: GPL-2.0-only
/*
 * rx550_gpuvm.c — GPUVM PM4 emission para GFX8.
 *
 * TARGET = RX 550 (1002:699F, Polaris12, GFX8, rev C7)
 * SCOPE  = EXCLUSIVO
 *
 * IMPLEMENTA: gfx_v8_0_ring_emit_vm_flush + gmc_v8_0_emit_flush_gpu_tlb
 * FUENTE: gfx_v8_0.c:6191-6215, gmc_v8_0.c:668-683
 */

#include "rx550_gpuvm.h"

/* ─────────────────────────────────────────────────────────────────────────────
 * RING HELPERS — el ring es un buffer circular de dwords
 * ───────────────────────────────────────────────────────────────────────────── */
static inline void ring_write_dword(uint32_t **wptr, uint32_t val)
{
	**wptr = val;
	(*wptr)++;
}

static inline void ring_write_wreg(uint32_t **wptr, uint32_t reg_index, uint32_t val)
{
	/* PACKET3_SET_CONTEXT_REG = 0x61, count = 1 (1 dword de datos) */
	ring_write_dword(wptr, (0x61u << 16) | 1u);
	ring_write_dword(wptr, reg_index);
	ring_write_dword(wptr, val);
}

/* ─────────────────────────────────────────────────────────────────────────────
 * EMISIÓN SECUENCIA TLB FLUSH (hallazgo 1588)
 * ───────────────────────────────────────────────────────────────────────────── */
int rx550_gpuvm_emit_tlb_flush(void *ring_buffer, uint32_t *ring_wptr,
			       const struct rx550_tlb_flush *flush)
{
	if (!flush)
		return RX550_GPUVM_ERR_INVALID_VMID;
	if (flush->vmid > RX550_VMID_MAX)
		return RX550_GPUVM_ERR_INVALID_VMID;
	if (flush->pd_addr & 0xFFFull)
		return RX550_GPUVM_ERR_ALIGN;  /* PD base must be 4 KB aligned */

	/* Estimamos espacio: ~20 dwords máximos */
	/* En implementación real se comprobaría ring_space() */

	uint32_t *wp = (uint32_t *)ring_wptr;
	uint32_t *start_wp = wp;

	/* ── Paso 1: Write PD base → CONTEXT_PAGE_TABLE_BASE_ADDR ── */
	uint32_t ptb_reg = rx550_vm_context_ptb_reg(flush->vmid);
	/* PD address es 4 KB aligned, registro espera addr >> 12 */
	ring_write_wreg(&wp, ptb_reg, (uint32_t)(flush->pd_addr >> 12));

	/* ── Paso 2: Trigger invalidation → VM_INVALIDATE_REQUEST = 1 << VMID ── */
	ring_write_wreg(&wp, RX550_VM_INVALIDATE_REQUEST, 1u << flush->vmid);

	/* ── Paso 3: WAIT_REG_MEM polling VM_INVALIDATE_REQUEST == 0 ──
	 * PACKET3_WAIT_REG_MEM = 0x3C, count = 5 (6 dwords total incluido header)
	 * Fields: operation=wait(0), function=always(0), engine=ME(0)
	 * Register = VM_INVALIDATE_REQUEST (byte offset 0x1478)
	 * Ref = 0, Mask = 0 (poll until 0), poll_interval = 0x20
	 */
	ring_write_dword(&wp, rx550_pkt3_wait_reg_mem_header(5));
	ring_write_dword(&wp, (RX550_WAIT_REG_MEM_OP_WAIT |
			       (RX550_WAIT_REG_MEM_FUNC_ALWAYS << 2) |
			       (RX550_WAIT_REG_MEM_ENGINE_ME << 4)));
	/* byte offset del registro (no índice) */
	ring_write_dword(&wp, RX550_VM_INVALIDATE_REQUEST * 4);  /* 0x51E * 4 = 0x1478 */
	ring_write_dword(&wp, 0);  /* high dword */
	ring_write_dword(&wp, 0);  /* reference */
	ring_write_dword(&wp, 0);  /* mask = 0 → wait for 0 */

	/* ── Paso 4: PFP_SYNC_ME si ring GFX ── */
	if (flush->use_pfp) {
		ring_write_dword(&wp, rx550_pkt3_pfp_sync_me_header());
		ring_write_dword(&wp, 0);
	}

	*ring_wptr = (uint32_t)wp;
	return (int)(wp - start_wp);
}

/* ─────────────────────────────────────────────────────────────────────────────
 * CONTEXT INIT — programa CONTEXT{0..15}_CNTL para GART flat
 * ───────────────────────────────────────────────────────────────────────────── */
int rx550_gpuvm_init_contexts(void *ring_buffer, uint32_t *ring_wptr,
			      uint32_t vmid_start, uint32_t vmid_count)
{
	if (vmid_start + vmid_count - 1 > RX550_VMID_MAX)
		return RX550_GPUVM_ERR_INVALID_VMID;

	uint32_t *wp = (uint32_t *)ring_wptr;
	uint32_t *start_wp = wp;
	uint32_t cntl_val = rx550_vm_context_cntl_flat_gart();

	for (uint32_t vmid = vmid_start; vmid < vmid_start + vmid_count; vmid++) {
		uint32_t cntl_reg;
		if (vmid < 8)
			cntl_reg = 0x504u + vmid;  /* mmVM_CONTEXT0_CNTL = 0x504 */
		else
			cntl_reg = 0x504u + 8 + (vmid - 8);  /* CONTEXT8_CNTL = 0x50C */

		ring_write_wreg(&wp, cntl_reg, cntl_val);
	}

	*ring_wptr = (uint32_t)wp;
	return (int)(wp - start_wp);
}

/* ─────────────────────────────────────────────────────────────────────────────
 * PTE/PDE HELPERS
 * ───────────────────────────────────────────────────────────────────────────── */

void rx550_gpuvm_write_pte(uint64_t *pte_array, uint32_t index,
			   uint64_t phys_addr, uint32_t fragment,
			   bool write, bool read, bool exec,
			   bool snooped, bool system)
{
	pte_array[index] = rx550_pte_make(phys_addr, fragment, write, read, exec, snooped, system);
}

void rx550_gpuvm_write_pde(uint64_t *pde_array, uint32_t index,
			   uint64_t pte_table_base, uint32_t frag_size)
{
	pde_array[index] = rx550_pde_make(pte_table_base, frag_size);
}
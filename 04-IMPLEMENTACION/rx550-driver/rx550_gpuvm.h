/* SPDX-License-Identifier: GPL-2.0-only */
/*
 * rx550_gpuvm.h — GPUVM para GFX8: PTE/PDE format, TLB flush sequence, PM4 packets.
 *
 * TARGET = RX 550 (1002:699F, Polaris12, GFX8, rev C7)
 * SCOPE  = EXCLUSIVO
 *
 * FUENTE VERIFICADA (hallazgo 1588):
 *   gmc_v8_0.c:661-683  gmc_v8_0_flush_gpu_tlb + gmc_v8_0_emit_flush_gpu_tlb
 *   gfx_v8_0.c:6191-6215 gfx_v8_0_ring_emit_vm_flush
 *   gmc_v8_0.c:692-710  PTE/PDE format (kernel comments)
 *   gmc_8_1_d.h:617,638 registros VM_INVALIDATE_REQUEST, CONTEXT_PAGE_TABLE_BASE
 *
 * SECUENCIA COMPLETA DE FLUSH (4 pasos, hallazgo 1588):
 *   1. Write PD base → VM_CONTEXT{0,8}_PAGE_TABLE_BASE_ADDR (0x153C / 0x155C)
 *   2. Trigger invalidation → VM_INVALIDATE_REQUEST = 1 << VMID (0x1478)
 *   3. WAIT_REG_MEM polling VM_INVALIDATE_REQUEST == 0 (PACKET3_WAIT_REG_MEM=0x3C)
 *   4. PFP_SYNC_ME si ring GFX (PACKET3_PFP_SYNC_ME=0x42)
 *
 * REGISTROS (gmc_8_1_d.h / gmc_8_2_d.h, idénticos):
 *   mmVM_INVALIDATE_REQUEST               = 0x51E (dword) → byte 0x1478
 *   mmVM_CONTEXT0_PAGE_TABLE_BASE_ADDR    = 0x54F (dword) → byte 0x153C
 *   mmVM_CONTEXT8_PAGE_TABLE_BASE_ADDR    = 0x557 (dword) → byte 0x155C
 */
#ifndef RX550_GPUVM_H
#define RX550_GPUVM_H

#include "rx550_mmio.h"
#include "rx550_smc.h"

/* ─────────────────────────────────────────────────────────────────────────────
 * REGISTROS VM (ÍNDICES, NO OFFSETS) — gmc_8_1_d.h / gmc_8_2_d.h
 * ───────────────────────────────────────────────────────────────────────────── */
#define RX550_VM_INVALIDATE_REQUEST           0x51Eu
#define RX550_VM_CONTEXT0_PAGE_TABLE_BASE_ADDR 0x54Fu
#define RX550_VM_CONTEXT8_PAGE_TABLE_BASE_ADDR 0x557u

/* ─────────────────────────────────────────────────────────────────────────────
 * VMID RANGE
 * ───────────────────────────────────────────────────────────────────────────── */
#define RX550_VMID_MIN        0u
#define RX550_VMID_MAX        15u
#define RX550_VMID_KERNEL     0u    /* VMID 0 = kernel/physical */

/* ─────────────────────────────────────────────────────────────────────────────
 * PTE FORMAT (4 KB page, gmc_v8_0.c:692-702)
 * ───────────────────────────────────────────────────────────────────────────── */
#define RX550_PTE_ADDR_MASK       0xFFFFFFFFFFFFF000ULL  /* bits 39:12 */
#define RX550_PTE_FRAG_SHIFT      7
#define RX550_PTE_FRAG_MASK       (0x1FULL << RX550_PTE_FRAG_SHIFT)  /* bits 11:7 */
#define RX550_PTE_WRITE           (1ULL << 6)
#define RX550_PTE_READ            (1ULL << 5)
#define RX550_PTE_EXEC            (1ULL << 4)
#define RX550_PTE_SNOOPED         (1ULL << 2)
#define RX550_PTE_SYSTEM          (1ULL << 1)
#define RX550_PTE_VALID           (1ULL << 0)

static inline uint64_t rx550_pte_make(uint64_t phys_addr,
				      uint32_t fragment,
				      bool write, bool read, bool exec,
				      bool snooped, bool system)
{
	uint64_t pte = (phys_addr & RX550_PTE_ADDR_MASK) |
		       ((uint64_t)(fragment & 0x1F) << RX550_PTE_FRAG_SHIFT);
	if (write)  pte |= RX550_PTE_WRITE;
	if (read)   pte |= RX550_PTE_READ;
	if (exec)   pte |= RX550_PTE_EXEC;
	if (snooped) pte |= RX550_PTE_SNOOPED;
	if (system) pte |= RX550_PTE_SYSTEM;
	pte |= RX550_PTE_VALID;
	return pte;
}

/* ─────────────────────────────────────────────────────────────────────────────
 * PDE FORMAT (gmc_v8_0.c:704-710)
 * ───────────────────────────────────────────────────────────────────────────── */
#define RX550_PDE_ADDR_MASK       0xFFFFFFFFFFE00ULL   /* bits 39:1 (256 KB aligned) */
#define RX550_PDE_FRAG_SIZE_SHIFT 59
#define RX550_PDE_FRAG_SIZE_MASK  (0x1FULL << RX550_PDE_FRAG_SIZE_SHIFT) /* bits 63:59 */
#define RX550_PDE_VALID           (1ULL << 0)

static inline uint64_t rx550_pde_make(uint64_t pte_table_base,
				      uint32_t frag_size)
{
	return (pte_table_base & RX550_PDE_ADDR_MASK) |
	       ((uint64_t)(frag_size & 0x1F) << RX550_PDE_FRAG_SIZE_SHIFT) |
	       RX550_PDE_VALID;
}

/* ─────────────────────────────────────────────────────────────────────────────
 * PM4 PACKETS (vid.h)
 * ───────────────────────────────────────────────────────────────────────────── */
#define RX550_PKT3_WAIT_REG_MEM     0x3Cu
#define RX550_PKT3_PFP_SYNC_ME      0x42u
#define RX550_PKT3_WRITE_DATA       0x20u
#define RX550_PKT3_SET_SH_REG       0x76u
#define RX550_PKT3_SET_CONTEXT_REG  0x61u

/* WAIT_REG_MEM fields (from 1580 + gfx_v8_0.c:6200-6202) */
#define RX550_WAIT_REG_MEM_OP_WAIT          0u
#define RX550_WAIT_REG_MEM_OP_POLL          3u
#define RX550_WAIT_REG_MEM_FUNC_ALWAYS      0u
#define RX550_WAIT_REG_MEM_FUNC_EQUAL       2u
#define RX550_WAIT_REG_MEM_FUNC_NOT_EQUAL   3u
#define RX550_WAIT_REG_MEM_ENGINE_ME        0u
#define RX550_WAIT_REG_MEM_ENGINE_PFP       1u

static inline uint32_t rx550_pkt3_wait_reg_mem_header(uint32_t count)
{
	return (RX550_PKT3_WAIT_REG_MEM << 16) | (count & 0x3FFF);
}

static inline uint32_t rx550_pkt3_pfp_sync_me_header(void)
{
	return (RX550_PKT3_PFP_SYNC_ME << 16) | 0u;  /* count = 0 */
}

/* ─────────────────────────────────────────────────────────────────────────────
 * TLB FLUSH SEQUENCE — EMISIÓN PM4 DIRECTA
 * ───────────────────────────────────────────────────────────────────────────── */

/* Contexto de flush: ring + VMID + PD address */
struct rx550_tlb_flush {
	uint32_t vmid;
	uint64_t pd_addr;      /* page directory base, 4 KB aligned */
	bool     use_pfp;      /* true si ring tipo GFX (tiene PFP) */
};

/* Emite la secuencia completa de 4 pasos en el ring.
 * Devuelve número de dwords emitidos, o negativo en error.
 * El llamador debe tener espacio en el ring reservado. */
int rx550_gpuvm_emit_tlb_flush(void *ring_buffer, uint32_t *ring_wptr,
			       const struct rx550_tlb_flush *flush);

/* Helper: calcula registro CONTEXT_PAGE_TABLE_BASE_ADDR para VMID.
 * VMID 0-7 → CONTEXT0 + VMID
 * VMID 8-15 → CONTEXT8 + (VMID - 8) */
static inline uint32_t rx550_vm_context_ptb_reg(uint32_t vmid)
{
	if (vmid < 8)
		return RX550_VM_CONTEXT0_PAGE_TABLE_BASE_ADDR + vmid;
	return RX550_VM_CONTEXT8_PAGE_TABLE_BASE_ADDR + vmid - 8;
}

/* ─────────────────────────────────────────────────────────────────────────────
 * CONTEXT SETUP (gmc_v8_0.c:673-677)
 * ───────────────────────────────────────────────────────────────────────────── */
#define RX550_VM_CONTEXT_CNTL_DEPTH_SHIFT     0
#define RX550_VM_CONTEXT_CNTL_DEPTH_MASK      (0x3u << RX550_VM_CONTEXT_CNTL_DEPTH_SHIFT)
#define RX550_VM_CONTEXT_CNTL_PAGE_TABLE_DEPTH_0  0u  /* flat */
#define RX550_VM_CONTEXT_CNTL_PAGE_TABLE_DEPTH_1  1u  /* 2-level */
#define RX550_VM_CONTEXT_CNTL_PAGE_TABLE_DEPTH_2  2u  /* 3-level */
#define RX550_VM_CONTEXT_CNTL_BLOCK_SIZE_SHIFT 4
#define RX550_VM_CONTEXT_CNTL_BLOCK_SIZE_MASK (0xFu << RX550_VM_CONTEXT_CNTL_BLOCK_SIZE_SHIFT)
#define RX550_VM_CONTEXT_CNTL_ENABLE          (1u << 31)

/* GART block_size = 10 (hallazgo 113 + rx550_gart_geom) → 4 KB pages */
#define RX550_GART_BLOCK_SIZE 10u

static inline uint32_t rx550_vm_context_cntl_flat_gart(void)
{
	return (RX550_VM_CONTEXT_CNTL_PAGE_TABLE_DEPTH_0 << RX550_VM_CONTEXT_CNTL_DEPTH_SHIFT) |
	       (RX550_GART_BLOCK_SIZE << RX550_VM_CONTEXT_CNTL_BLOCK_SIZE_SHIFT) |
	       RX550_VM_CONTEXT_CNTL_ENABLE;
}

/* ─────────────────────────────────────────────────────────────────────────────
 * ERRORES
 * ───────────────────────────────────────────────────────────────────────────── */
#define RX550_GPUVM_OK                 0
#define RX550_GPUVM_ERR_INVALID_VMID  -1
#define RX550_GPUVM_ERR_NO_SPACE      -2
#define RX550_GPUVM_ERR_ALIGN         -3

#endif /* RX550_GPUVM_H */
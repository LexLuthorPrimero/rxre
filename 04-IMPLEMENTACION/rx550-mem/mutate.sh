#!/bin/bash
# Mutation runner for rx550-mem.
#
# One backup per FILE.  An earlier version of this script reused a single .bak
# for both a .c and a .h and overwrote rx550_addr.c with the contents of
# rx550_addr.h.  That failure mode is why the backup set is explicit.
#
# Usage: ./mutate.sh   -> mutates, measures, restores, re-verifies.
cd "$(dirname "$0")" || exit 1

BK=/tmp/bk_mem
FILES="rx550_addr.c rx550_addr.h rx550_vis.c rx550_vis.h rx550_vm.c rx550_vm.h rx550_sub.c rx550_sub.h"
mkdir -p "$BK"
for f in $FILES; do cp "$f" "$BK/$f"; done
restore() { for f in $FILES; do cp "$BK/$f" "$f"; done; }

# mut DESC FILE SEDEXPR [BIN]
mut() {
  local desc="$1" file="$2" expr="$3" bin="${4:-rx550_contract_test}"
  restore
  local b1 b2 rc
  b1=$(md5sum "$file" | cut -d' ' -f1)
  sed -i "$expr" "$file"
  b2=$(md5sum "$file" | cut -d' ' -f1)
  if [ "$b1" = "$b2" ]; then printf "  %-46s NO_APLICA\n" "$desc"; return; fi
  if ! make "$bin" >/dev/null 2>&1; then
    printf "  %-46s BUILD_FAIL (inconcluso)\n" "$desc"; return
  fi
  "./$bin" >/tmp/mut.out 2>&1
  rc=$?
  if [ "$rc" -eq 0 ]; then
    printf "  %-46s *** NO DETECTADA ***\n" "$desc"
  else
    printf "  %-46s DETECTADA (%s)\n" "$desc" "$(grep -c FAIL /tmp/mut.out)"
  fi
}

echo "=== D3: can the cross-component test see the two layers diverge? ==="
mut "GART_ADDR_BITS 46->42 (mem narrower)" rx550_addr.h 's/ADDR_BITS   46/ADDR_BITS   42/' rx550_contract_test
mut "GART_ADDR_BITS 46->48 (mem wider)"   rx550_addr.h 's/ADDR_BITS   46/ADDR_BITS   48/' rx550_contract_test
mut "IB_ALIGN_MIN 4->8 (mem stricter)"    rx550_addr.h 's/IB_ALIGN_MIN 4u/IB_ALIGN_MIN 8u/' rx550_contract_test
mut "publish: sin check de 46 bits"       rx550_addr.c 's/if (gpu_va >> RX550_GART_ADDR_BITS)/if (0)/' rx550_contract_test

echo
echo "=== D4: boundary and lifetime rules ==="
mut "publish acepta cualquier space"      rx550_addr.c 's/space != RX550_AS_GPU_GART \&\& space != RX550_AS_GPU_VRAM_PA/0/' rx550_addr_test
mut "release: sin chequeo de owner"       rx550_addr.c 's/if (owner == 0u || owner != b->owner)/if (0)/' rx550_addr_test
mut "alloc: sin guard de estado"          rx550_addr.c 's/if (b->state != RX550_BUF_EMPTY)/if (0)/' rx550_addr_test
mut "encodable:Published sin comprobar"   rx550_addr.c 's/return b \&\& b->state == RX550_BUF_PUBLISHED;/return b != 0;/' rx550_addr_test

echo
echo "=== A: visibility ==="
mut "SURFACE_SYNC 0x43->0x44"             rx550_vis.h 's/OP_SURFACE_SYNC  0x43u/OP_SURFACE_SYNC  0x44u/' rx550_vis_test
mut "ACQUIRE_MEM 0x58->0x59"              rx550_vis.h 's/OP_ACQUIRE_MEM   0x58u/OP_ACQUIRE_MEM   0x59u/' rx550_vis_test
mut "COHER_CNTL pierde SH_ICACHE"         rx550_vis.h 's/COHER_CNTL 0x28C40000u/COHER_CNTL 0x08C40000u/' rx550_vis_test
mut "poll 0x0A->0x0B"                     rx550_vis.h 's/COHER_POLL 0x0000000Au/COHER_POLL 0x0000000Bu/' rx550_vis_test
mut "SURFACE_SYNC count 3->4"             rx550_vis.c 's/SURFACE_SYNC << 8) | (3u << 16)/SURFACE_SYNC << 8) | (4u << 16)/' rx550_vis_test
mut "ACQUIRE_MEM size_hi 0xff->0xfe"      rx550_vis.c 's/0x000000ffu;   \/\* CP_COHER_SIZE_HI/0x000000feu;   \/* CP_COHER_SIZE_HI/' rx550_vis_test
mut "order_ok acepta solape (<=)"         rx550_vis.c 's/return sync_offset < descriptor_offset;/return sync_offset <= descriptor_offset;/' rx550_vis_test
mut "order_ok tolera sync ausente"        rx550_vis.c 's/return 0;   \/\* no coherence packet at all: contract not met \*\//return 1;/' rx550_vis_test
mut "encode: destino corto escribe igual" rx550_vis.c 's/if (out_dw < need)/if (0)/' rx550_vis_test

echo
echo "=== B/C: PDB0 / PTE ==="
mut "PDE_PTE bit 54->55"                  rx550_vm.h 's/RX550_PDE_PTE        (UINT64_C(1) << 54)/RX550_PDE_PTE        (UINT64_C(1) << 55)/' rx550_vm_test
mut "entry 2MiB->1MiB"                    rx550_vm.h 's/PDB0_BLOCK_SIZE_SHIFT 21/PDB0_BLOCK_SIZE_SHIFT 20/' rx550_vm_test
mut "addr mask pierde 4KiB"               rx550_vm.h 's/0x000000FFFFFFF000/0x000000FFFFFFFF00/' rx550_vm_test
mut "FRAG 9->8"                           rx550_vm.c 's/BLOCK_SIZE + 9u/BLOCK_SIZE + 8u/' rx550_vm_test
mut "flags: WRITEABLE off"                rx550_vm.c 's/^     | RX550_PTE_WRITEABLE$//' rx550_vm_test
mut "flags: SNOOPED off"                  rx550_vm.c 's/^     | RX550_PTE_SNOOPED$//' rx550_vm_test
mut "flags: VALID off"                    rx550_vm.c 's/^     | RX550_PTE_VALID$//' rx550_vm_test
mut "entry no mascara la PA"              rx550_vm.c 's/return (system_pa \& RX550_PTE_ADDR_MASK) | flags;/return system_pa | flags;/' rx550_vm_test
mut "index: sin check de window base"     rx550_vm.c 's/if (gpu_va < gart_base)/if (0)/' rx550_vm_test
mut "entries_for: cuenta mal"             rx550_vm.c 's/n = last - first + 1u;/n = 1u;/' rx550_vm_test

echo
echo "=== submission contract ==="
mut "WPTR: acepta retroceso"        rx550_sub.c 's/if (wptr_after < s->wptr_before)/if (0)/' rx550_sub_test
mut "WPTR: acepta no-avance"        rx550_sub.c 's/if (wptr_after == s->wptr_before)/if (0)/' rx550_sub_test
mut "consumo: RPTR igual => CONSUMPTION" rx550_sub.c 's/if (rptr > s->wptr_before)/if (1)/' rx550_sub_test
mut "consumo: RPTR retrocedido => CONSUMPTION" rx550_sub.c 's/if (rptr > s->wptr_before)/if (rptr + 1u > s->wptr_before)/' rx550_sub_test
mut "reading incomparable aceptada" rx550_sub.c 's/if (!comparable)/if (comparable \&\& comparable == 0)/' rx550_sub_test
mut "completion sin seq_ok"          rx550_sub.c 's/if (!seq_ok)/if (seq_ok \&\& seq_ok == 0)/' rx550_sub_test
mut "retire: owner incorrecto"        rx550_sub.c 's/owner != s->owner/owner + 1u != s->owner/' rx550_sub_test
mut "ready: sin guard de estado"     rx550_sub.c 's/if (s->state != RX550_SUB_CREATED)/if (0)/' rx550_sub_test
mut "create: acepta buffer no publicado" rx550_sub.c 's/if (b->state != RX550_BUF_PUBLISHED)/if (0)/' rx550_sub_test
mut "POLL_CNTL polaris12 != 0"       rx550_sub.c 's/return is_polaris12_path ? 0u :/return is_polaris12_path ? 0x00900100u :/' rx550_sub_test
mut "doorbell_published sin chequeo" rx550_sub.c 's/return s ? (int)s->doorbell_published : 0;/return s ? 1 : 0;/' rx550_sub_test
mut "offset RPTR 0x8700->0x8704"     rx550_sub.h 's/RX550_REG_CP_RB0_RPTR            0x008700u/RX550_REG_CP_RB0_RPTR            0x008704u/' rx550_sub_test
mut "DOORBELL_EN mask 30->29"        rx550_sub.h 's/RX550_DB_EN_SHIFT      30/RX550_DB_EN_SHIFT      29/' rx550_sub_test

restore
make clean >/dev/null 2>&1
echo
echo "restaurado y re-verificado:"
make test 2>&1 | grep passed | sed 's/^/  /'

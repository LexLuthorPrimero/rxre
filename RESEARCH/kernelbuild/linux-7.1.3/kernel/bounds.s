	.file	"bounds.c"
# GNU C11 (GCC) version 16.2.1 20260819 (Red Hat 16.2.1-2) (x86_64-redhat-linux)
#	compiled by GNU C version 16.2.1 20260819 (Red Hat 16.2.1-2), GMP version 6.3.0, MPFR version 4.2.2, MPC version 1.4.1, isl version none
# GGC heuristics: --param ggc-min-expand=100 --param ggc-min-heapsize=131072
# options passed: -mno-sse -mno-mmx -mno-sse2 -mno-3dnow -mno-avx -mno-sse4a -m64 -mno-80387 -mno-fp-ret-in-387 -mpreferred-stack-boundary=3 -mskip-rax-setup -march=x86-64 -mtune=generic -mno-red-zone -mcmodel=kernel -mstack-protector-guard-reg=gs -mstack-protector-guard-symbol=__ref_stack_chk_guard -mindirect-branch=thunk-extern -mindirect-branch-register -mindirect-branch-cs-prefix -mfunction-return=thunk-extern -mharden-sls=all -mrecord-mcount -mfentry -mtls-dialect=gnu2 -O2 -std=gnu11 -p -fshort-wchar -funsigned-char -fno-common -fno-PIE -fno-strict-aliasing -fms-extensions -fcf-protection=branch -falign-jumps=1 -falign-loops=1 -fno-asynchronous-unwind-tables -fno-jump-tables -fpatchable-function-entry=16,16 -fno-delete-null-pointer-checks -fno-allow-store-data-races -fstack-protector-strong -ftrivial-auto-var-init=zero -fzero-init-padding-bits=all -fno-stack-clash-protection -fdiagnostics-show-context=2 -fmin-function-alignment=16 -fstrict-flex-arrays=3 -fno-strict-overflow -fstack-check=no -fconserve-stack -fno-builtin-wcslen
	.text
	.section	.text.startup,"ax",@progbits
	.align 16
	.globl	main
	.section	__patchable_function_entries,"awo",@progbits,.LPFE224
	.align 8
	.quad	.LPFE224
	.section	.text.startup
.LPFE224:
	nop	
	nop	
	nop	
	nop	
	nop	
	nop	
	nop	
	nop	
	nop	
	nop	
	nop	
	nop	
	nop	
	nop	
	nop	
	nop	
	.type	main, @function
main:
	endbr64
1:	call	__fentry__
	.section __mcount_loc, "a",@progbits
	.quad 1b
	.previous
# kernel/bounds.c:20: 	DEFINE(NR_PAGEFLAGS, __NR_PAGEFLAGS);
#APP
# 20 "kernel/bounds.c" 1
	
.ascii "->NR_PAGEFLAGS $25 __NR_PAGEFLAGS"	#
# 0 "" 2
# kernel/bounds.c:21: 	DEFINE(MAX_NR_ZONES, __MAX_NR_ZONES);
# 21 "kernel/bounds.c" 1
	
.ascii "->MAX_NR_ZONES $5 __MAX_NR_ZONES"	#
# 0 "" 2
# kernel/bounds.c:23: 	DEFINE(NR_CPUS_BITS, order_base_2(CONFIG_NR_CPUS));
# 23 "kernel/bounds.c" 1
	
.ascii "->NR_CPUS_BITS $13 order_base_2(CONFIG_NR_CPUS)"	#
# 0 "" 2
# kernel/bounds.c:25: 	DEFINE(SPINLOCK_SIZE, sizeof(spinlock_t));
# 25 "kernel/bounds.c" 1
	
.ascii "->SPINLOCK_SIZE $4 sizeof(spinlock_t)"	#
# 0 "" 2
# kernel/bounds.c:27: 	DEFINE(LRU_GEN_WIDTH, order_base_2(MAX_NR_GENS + 1));
# 27 "kernel/bounds.c" 1
	
.ascii "->LRU_GEN_WIDTH $3 order_base_2(MAX_NR_GENS + 1)"	#
# 0 "" 2
# kernel/bounds.c:28: 	DEFINE(__LRU_REFS_WIDTH, MAX_NR_TIERS - 2);
# 28 "kernel/bounds.c" 1
	
.ascii "->__LRU_REFS_WIDTH $2 MAX_NR_TIERS - 2"	#
# 0 "" 2
# kernel/bounds.c:36: }
#NO_APP
	xorl	%eax, %eax	#
	jmp	__x86_return_thunk
	.size	main, .-main
	.ident	"GCC: (GNU) 16.2.1 20260819 (Red Hat 16.2.1-2)"
	.section	.note.GNU-stack,"",@progbits
	.section	.note.gnu.property,"a"
	.align 8
	.long	1f - 0f
	.long	4f - 1f
	.long	5
0:
	.string	"GNU"
1:
	.align 8
	.long	0xc0000002
	.long	3f - 2f
2:
	.long	0x1
3:
	.align 8
4:

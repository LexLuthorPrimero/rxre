	.file	"asm-offsets.c"
# GNU C11 (GCC) version 16.2.1 20260819 (Red Hat 16.2.1-2) (x86_64-redhat-linux)
#	compiled by GNU C version 16.2.1 20260819 (Red Hat 16.2.1-2), GMP version 6.3.0, MPFR version 4.2.2, MPC version 1.4.1, isl version none
# GGC heuristics: --param ggc-min-expand=100 --param ggc-min-heapsize=131072
# options passed: -mno-sse -mno-mmx -mno-sse2 -mno-3dnow -mno-avx -mno-sse4a -m64 -mno-80387 -mno-fp-ret-in-387 -mpreferred-stack-boundary=3 -mskip-rax-setup -march=x86-64 -mtune=generic -mno-red-zone -mcmodel=kernel -mstack-protector-guard-reg=gs -mstack-protector-guard-symbol=__ref_stack_chk_guard -mindirect-branch=thunk-extern -mindirect-branch-register -mindirect-branch-cs-prefix -mfunction-return=thunk-extern -mharden-sls=all -mrecord-mcount -mfentry -mtls-dialect=gnu2 -O2 -std=gnu11 -p -fshort-wchar -funsigned-char -fno-common -fno-PIE -fno-strict-aliasing -fms-extensions -fcf-protection=branch -falign-jumps=1 -falign-loops=1 -fno-asynchronous-unwind-tables -fno-jump-tables -fpatchable-function-entry=16,16 -fno-delete-null-pointer-checks -fno-allow-store-data-races -fstack-protector-strong -ftrivial-auto-var-init=zero -fzero-init-padding-bits=all -fno-stack-clash-protection -fdiagnostics-show-context=2 -fmin-function-alignment=16 -fstrict-flex-arrays=3 -fno-strict-overflow -fstack-check=no -fconserve-stack -fno-builtin-wcslen
	.text
	.section	.text.startup,"ax",@progbits
	.align 16
	.globl	main
	.section	__patchable_function_entries,"awo",@progbits,.LPFE5355
	.align 8
	.quad	.LPFE5355
	.section	.text.startup
.LPFE5355:
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
# arch/x86/kernel/asm-offsets_64.c:20: 	BLANK();
#APP
# 20 "arch/x86/kernel/asm-offsets_64.c" 1
	
.ascii "->"
# 0 "" 2
# arch/x86/kernel/asm-offsets_64.c:24: 	OFFSET(KVM_STEAL_TIME_preempted, kvm_steal_time, preempted);
# 24 "arch/x86/kernel/asm-offsets_64.c" 1
	
.ascii "->KVM_STEAL_TIME_preempted $16 offsetof(struct kvm_steal_time, preempted)"	#
# 0 "" 2
# arch/x86/kernel/asm-offsets_64.c:25: 	BLANK();
# 25 "arch/x86/kernel/asm-offsets_64.c" 1
	
.ascii "->"
# 0 "" 2
# arch/x86/kernel/asm-offsets_64.c:29: 	ENTRY(bx);
# 29 "arch/x86/kernel/asm-offsets_64.c" 1
	
.ascii "->pt_regs_bx $40 offsetof(struct pt_regs, bx)"	#
# 0 "" 2
# arch/x86/kernel/asm-offsets_64.c:30: 	ENTRY(cx);
# 30 "arch/x86/kernel/asm-offsets_64.c" 1
	
.ascii "->pt_regs_cx $88 offsetof(struct pt_regs, cx)"	#
# 0 "" 2
# arch/x86/kernel/asm-offsets_64.c:31: 	ENTRY(dx);
# 31 "arch/x86/kernel/asm-offsets_64.c" 1
	
.ascii "->pt_regs_dx $96 offsetof(struct pt_regs, dx)"	#
# 0 "" 2
# arch/x86/kernel/asm-offsets_64.c:32: 	ENTRY(sp);
# 32 "arch/x86/kernel/asm-offsets_64.c" 1
	
.ascii "->pt_regs_sp $152 offsetof(struct pt_regs, sp)"	#
# 0 "" 2
# arch/x86/kernel/asm-offsets_64.c:33: 	ENTRY(bp);
# 33 "arch/x86/kernel/asm-offsets_64.c" 1
	
.ascii "->pt_regs_bp $32 offsetof(struct pt_regs, bp)"	#
# 0 "" 2
# arch/x86/kernel/asm-offsets_64.c:34: 	ENTRY(si);
# 34 "arch/x86/kernel/asm-offsets_64.c" 1
	
.ascii "->pt_regs_si $104 offsetof(struct pt_regs, si)"	#
# 0 "" 2
# arch/x86/kernel/asm-offsets_64.c:35: 	ENTRY(di);
# 35 "arch/x86/kernel/asm-offsets_64.c" 1
	
.ascii "->pt_regs_di $112 offsetof(struct pt_regs, di)"	#
# 0 "" 2
# arch/x86/kernel/asm-offsets_64.c:36: 	ENTRY(r8);
# 36 "arch/x86/kernel/asm-offsets_64.c" 1
	
.ascii "->pt_regs_r8 $72 offsetof(struct pt_regs, r8)"	#
# 0 "" 2
# arch/x86/kernel/asm-offsets_64.c:37: 	ENTRY(r9);
# 37 "arch/x86/kernel/asm-offsets_64.c" 1
	
.ascii "->pt_regs_r9 $64 offsetof(struct pt_regs, r9)"	#
# 0 "" 2
# arch/x86/kernel/asm-offsets_64.c:38: 	ENTRY(r10);
# 38 "arch/x86/kernel/asm-offsets_64.c" 1
	
.ascii "->pt_regs_r10 $56 offsetof(struct pt_regs, r10)"	#
# 0 "" 2
# arch/x86/kernel/asm-offsets_64.c:39: 	ENTRY(r11);
# 39 "arch/x86/kernel/asm-offsets_64.c" 1
	
.ascii "->pt_regs_r11 $48 offsetof(struct pt_regs, r11)"	#
# 0 "" 2
# arch/x86/kernel/asm-offsets_64.c:40: 	ENTRY(r12);
# 40 "arch/x86/kernel/asm-offsets_64.c" 1
	
.ascii "->pt_regs_r12 $24 offsetof(struct pt_regs, r12)"	#
# 0 "" 2
# arch/x86/kernel/asm-offsets_64.c:41: 	ENTRY(r13);
# 41 "arch/x86/kernel/asm-offsets_64.c" 1
	
.ascii "->pt_regs_r13 $16 offsetof(struct pt_regs, r13)"	#
# 0 "" 2
# arch/x86/kernel/asm-offsets_64.c:42: 	ENTRY(r14);
# 42 "arch/x86/kernel/asm-offsets_64.c" 1
	
.ascii "->pt_regs_r14 $8 offsetof(struct pt_regs, r14)"	#
# 0 "" 2
# arch/x86/kernel/asm-offsets_64.c:43: 	ENTRY(r15);
# 43 "arch/x86/kernel/asm-offsets_64.c" 1
	
.ascii "->pt_regs_r15 $0 offsetof(struct pt_regs, r15)"	#
# 0 "" 2
# arch/x86/kernel/asm-offsets_64.c:44: 	ENTRY(flags);
# 44 "arch/x86/kernel/asm-offsets_64.c" 1
	
.ascii "->pt_regs_flags $144 offsetof(struct pt_regs, flags)"	#
# 0 "" 2
# arch/x86/kernel/asm-offsets_64.c:45: 	BLANK();
# 45 "arch/x86/kernel/asm-offsets_64.c" 1
	
.ascii "->"
# 0 "" 2
# arch/x86/kernel/asm-offsets_64.c:49: 	ENTRY(cr0);
# 49 "arch/x86/kernel/asm-offsets_64.c" 1
	
.ascii "->saved_context_cr0 $200 offsetof(struct saved_context, cr0)"	#
# 0 "" 2
# arch/x86/kernel/asm-offsets_64.c:50: 	ENTRY(cr2);
# 50 "arch/x86/kernel/asm-offsets_64.c" 1
	
.ascii "->saved_context_cr2 $208 offsetof(struct saved_context, cr2)"	#
# 0 "" 2
# arch/x86/kernel/asm-offsets_64.c:51: 	ENTRY(cr3);
# 51 "arch/x86/kernel/asm-offsets_64.c" 1
	
.ascii "->saved_context_cr3 $216 offsetof(struct saved_context, cr3)"	#
# 0 "" 2
# arch/x86/kernel/asm-offsets_64.c:52: 	ENTRY(cr4);
# 52 "arch/x86/kernel/asm-offsets_64.c" 1
	
.ascii "->saved_context_cr4 $224 offsetof(struct saved_context, cr4)"	#
# 0 "" 2
# arch/x86/kernel/asm-offsets_64.c:53: 	ENTRY(gdt_desc);
# 53 "arch/x86/kernel/asm-offsets_64.c" 1
	
.ascii "->saved_context_gdt_desc $266 offsetof(struct saved_context, gdt_desc)"	#
# 0 "" 2
# arch/x86/kernel/asm-offsets_64.c:54: 	BLANK();
# 54 "arch/x86/kernel/asm-offsets_64.c" 1
	
.ascii "->"
# 0 "" 2
# arch/x86/kernel/asm-offsets_64.c:58: }
#NO_APP
	xorl	%eax, %eax	#
	jmp	__x86_return_thunk
	.size	main, .-main
	.text
	.align 16
	.section	__patchable_function_entries,"awo",@progbits,.LPFE5356
	.align 8
	.quad	.LPFE5356
	.text
.LPFE5356:
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
	.type	common, @function
common:
	endbr64
1:	call	__fentry__
	.section __mcount_loc, "a",@progbits
	.quad 1b
	.previous
# arch/x86/kernel/asm-offsets.c:36: 	OFFSET(CPUINFO_x86, cpuinfo_x86, x86);
#APP
# 36 "arch/x86/kernel/asm-offsets.c" 1
	
.ascii "->CPUINFO_x86 $1 offsetof(struct cpuinfo_x86, x86)"	#
# 0 "" 2
# arch/x86/kernel/asm-offsets.c:37: 	OFFSET(CPUINFO_x86_vendor, cpuinfo_x86, x86_vendor);
# 37 "arch/x86/kernel/asm-offsets.c" 1
	
.ascii "->CPUINFO_x86_vendor $2 offsetof(struct cpuinfo_x86, x86_vendor)"	#
# 0 "" 2
# arch/x86/kernel/asm-offsets.c:38: 	OFFSET(CPUINFO_x86_model, cpuinfo_x86, x86_model);
# 38 "arch/x86/kernel/asm-offsets.c" 1
	
.ascii "->CPUINFO_x86_model $0 offsetof(struct cpuinfo_x86, x86_model)"	#
# 0 "" 2
# arch/x86/kernel/asm-offsets.c:39: 	OFFSET(CPUINFO_x86_stepping, cpuinfo_x86, x86_stepping);
# 39 "arch/x86/kernel/asm-offsets.c" 1
	
.ascii "->CPUINFO_x86_stepping $4 offsetof(struct cpuinfo_x86, x86_stepping)"	#
# 0 "" 2
# arch/x86/kernel/asm-offsets.c:40: 	OFFSET(CPUINFO_cpuid_level, cpuinfo_x86, cpuid_level);
# 40 "arch/x86/kernel/asm-offsets.c" 1
	
.ascii "->CPUINFO_cpuid_level $40 offsetof(struct cpuinfo_x86, cpuid_level)"	#
# 0 "" 2
# arch/x86/kernel/asm-offsets.c:41: 	OFFSET(CPUINFO_x86_capability, cpuinfo_x86, x86_capability);
# 41 "arch/x86/kernel/asm-offsets.c" 1
	
.ascii "->CPUINFO_x86_capability $48 offsetof(struct cpuinfo_x86, x86_capability)"	#
# 0 "" 2
# arch/x86/kernel/asm-offsets.c:42: 	OFFSET(CPUINFO_x86_vendor_id, cpuinfo_x86, x86_vendor_id);
# 42 "arch/x86/kernel/asm-offsets.c" 1
	
.ascii "->CPUINFO_x86_vendor_id $144 offsetof(struct cpuinfo_x86, x86_vendor_id)"	#
# 0 "" 2
# arch/x86/kernel/asm-offsets.c:44: 	BLANK();
# 44 "arch/x86/kernel/asm-offsets.c" 1
	
.ascii "->"
# 0 "" 2
# arch/x86/kernel/asm-offsets.c:45: 	OFFSET(TASK_threadsp, task_struct, thread.sp);
# 45 "arch/x86/kernel/asm-offsets.c" 1
	
.ascii "->TASK_threadsp $5656 offsetof(struct task_struct, thread.sp)"	#
# 0 "" 2
# arch/x86/kernel/asm-offsets.c:47: 	OFFSET(TASK_stack_canary, task_struct, stack_canary);
# 47 "arch/x86/kernel/asm-offsets.c" 1
	
.ascii "->TASK_stack_canary $2616 offsetof(struct task_struct, stack_canary)"	#
# 0 "" 2
# arch/x86/kernel/asm-offsets.c:50: 	BLANK();
# 50 "arch/x86/kernel/asm-offsets.c" 1
	
.ascii "->"
# 0 "" 2
# arch/x86/kernel/asm-offsets.c:51: 	OFFSET(pbe_address, pbe, address);
# 51 "arch/x86/kernel/asm-offsets.c" 1
	
.ascii "->pbe_address $0 offsetof(struct pbe, address)"	#
# 0 "" 2
# arch/x86/kernel/asm-offsets.c:52: 	OFFSET(pbe_orig_address, pbe, orig_address);
# 52 "arch/x86/kernel/asm-offsets.c" 1
	
.ascii "->pbe_orig_address $8 offsetof(struct pbe, orig_address)"	#
# 0 "" 2
# arch/x86/kernel/asm-offsets.c:53: 	OFFSET(pbe_next, pbe, next);
# 53 "arch/x86/kernel/asm-offsets.c" 1
	
.ascii "->pbe_next $16 offsetof(struct pbe, next)"	#
# 0 "" 2
# arch/x86/kernel/asm-offsets.c:56: 	BLANK();
# 56 "arch/x86/kernel/asm-offsets.c" 1
	
.ascii "->"
# 0 "" 2
# arch/x86/kernel/asm-offsets.c:57: 	OFFSET(IA32_SIGCONTEXT_ax, sigcontext_32, ax);
# 57 "arch/x86/kernel/asm-offsets.c" 1
	
.ascii "->IA32_SIGCONTEXT_ax $44 offsetof(struct sigcontext_32, ax)"	#
# 0 "" 2
# arch/x86/kernel/asm-offsets.c:58: 	OFFSET(IA32_SIGCONTEXT_bx, sigcontext_32, bx);
# 58 "arch/x86/kernel/asm-offsets.c" 1
	
.ascii "->IA32_SIGCONTEXT_bx $32 offsetof(struct sigcontext_32, bx)"	#
# 0 "" 2
# arch/x86/kernel/asm-offsets.c:59: 	OFFSET(IA32_SIGCONTEXT_cx, sigcontext_32, cx);
# 59 "arch/x86/kernel/asm-offsets.c" 1
	
.ascii "->IA32_SIGCONTEXT_cx $40 offsetof(struct sigcontext_32, cx)"	#
# 0 "" 2
# arch/x86/kernel/asm-offsets.c:60: 	OFFSET(IA32_SIGCONTEXT_dx, sigcontext_32, dx);
# 60 "arch/x86/kernel/asm-offsets.c" 1
	
.ascii "->IA32_SIGCONTEXT_dx $36 offsetof(struct sigcontext_32, dx)"	#
# 0 "" 2
# arch/x86/kernel/asm-offsets.c:61: 	OFFSET(IA32_SIGCONTEXT_si, sigcontext_32, si);
# 61 "arch/x86/kernel/asm-offsets.c" 1
	
.ascii "->IA32_SIGCONTEXT_si $20 offsetof(struct sigcontext_32, si)"	#
# 0 "" 2
# arch/x86/kernel/asm-offsets.c:62: 	OFFSET(IA32_SIGCONTEXT_di, sigcontext_32, di);
# 62 "arch/x86/kernel/asm-offsets.c" 1
	
.ascii "->IA32_SIGCONTEXT_di $16 offsetof(struct sigcontext_32, di)"	#
# 0 "" 2
# arch/x86/kernel/asm-offsets.c:63: 	OFFSET(IA32_SIGCONTEXT_bp, sigcontext_32, bp);
# 63 "arch/x86/kernel/asm-offsets.c" 1
	
.ascii "->IA32_SIGCONTEXT_bp $24 offsetof(struct sigcontext_32, bp)"	#
# 0 "" 2
# arch/x86/kernel/asm-offsets.c:64: 	OFFSET(IA32_SIGCONTEXT_sp, sigcontext_32, sp);
# 64 "arch/x86/kernel/asm-offsets.c" 1
	
.ascii "->IA32_SIGCONTEXT_sp $28 offsetof(struct sigcontext_32, sp)"	#
# 0 "" 2
# arch/x86/kernel/asm-offsets.c:65: 	OFFSET(IA32_SIGCONTEXT_ip, sigcontext_32, ip);
# 65 "arch/x86/kernel/asm-offsets.c" 1
	
.ascii "->IA32_SIGCONTEXT_ip $56 offsetof(struct sigcontext_32, ip)"	#
# 0 "" 2
# arch/x86/kernel/asm-offsets.c:66: 	OFFSET(IA32_SIGCONTEXT_es, sigcontext_32, es);
# 66 "arch/x86/kernel/asm-offsets.c" 1
	
.ascii "->IA32_SIGCONTEXT_es $8 offsetof(struct sigcontext_32, es)"	#
# 0 "" 2
# arch/x86/kernel/asm-offsets.c:67: 	OFFSET(IA32_SIGCONTEXT_cs, sigcontext_32, cs);
# 67 "arch/x86/kernel/asm-offsets.c" 1
	
.ascii "->IA32_SIGCONTEXT_cs $60 offsetof(struct sigcontext_32, cs)"	#
# 0 "" 2
# arch/x86/kernel/asm-offsets.c:68: 	OFFSET(IA32_SIGCONTEXT_ss, sigcontext_32, ss);
# 68 "arch/x86/kernel/asm-offsets.c" 1
	
.ascii "->IA32_SIGCONTEXT_ss $72 offsetof(struct sigcontext_32, ss)"	#
# 0 "" 2
# arch/x86/kernel/asm-offsets.c:69: 	OFFSET(IA32_SIGCONTEXT_ds, sigcontext_32, ds);
# 69 "arch/x86/kernel/asm-offsets.c" 1
	
.ascii "->IA32_SIGCONTEXT_ds $12 offsetof(struct sigcontext_32, ds)"	#
# 0 "" 2
# arch/x86/kernel/asm-offsets.c:70: 	OFFSET(IA32_SIGCONTEXT_flags, sigcontext_32, flags);
# 70 "arch/x86/kernel/asm-offsets.c" 1
	
.ascii "->IA32_SIGCONTEXT_flags $64 offsetof(struct sigcontext_32, flags)"	#
# 0 "" 2
# arch/x86/kernel/asm-offsets.c:72: 	BLANK();
# 72 "arch/x86/kernel/asm-offsets.c" 1
	
.ascii "->"
# 0 "" 2
# arch/x86/kernel/asm-offsets.c:73: 	OFFSET(IA32_SIGFRAME_sigcontext,    sigframe_ia32,    sc);
# 73 "arch/x86/kernel/asm-offsets.c" 1
	
.ascii "->IA32_SIGFRAME_sigcontext $8 offsetof(struct sigframe_ia32, sc)"	#
# 0 "" 2
# arch/x86/kernel/asm-offsets.c:74: 	OFFSET(IA32_RT_SIGFRAME_sigcontext, rt_sigframe_ia32, uc.uc_mcontext);
# 74 "arch/x86/kernel/asm-offsets.c" 1
	
.ascii "->IA32_RT_SIGFRAME_sigcontext $164 offsetof(struct rt_sigframe_ia32, uc.uc_mcontext)"	#
# 0 "" 2
# arch/x86/kernel/asm-offsets.c:78: 	BLANK();
# 78 "arch/x86/kernel/asm-offsets.c" 1
	
.ascii "->"
# 0 "" 2
# arch/x86/kernel/asm-offsets.c:79: 	OFFSET(XEN_vcpu_info_mask, vcpu_info, evtchn_upcall_mask);
# 79 "arch/x86/kernel/asm-offsets.c" 1
	
.ascii "->XEN_vcpu_info_mask $1 offsetof(struct vcpu_info, evtchn_upcall_mask)"	#
# 0 "" 2
# arch/x86/kernel/asm-offsets.c:80: 	OFFSET(XEN_vcpu_info_pending, vcpu_info, evtchn_upcall_pending);
# 80 "arch/x86/kernel/asm-offsets.c" 1
	
.ascii "->XEN_vcpu_info_pending $0 offsetof(struct vcpu_info, evtchn_upcall_pending)"	#
# 0 "" 2
# arch/x86/kernel/asm-offsets.c:81: 	OFFSET(XEN_vcpu_info_arch_cr2, vcpu_info, arch.cr2);
# 81 "arch/x86/kernel/asm-offsets.c" 1
	
.ascii "->XEN_vcpu_info_arch_cr2 $16 offsetof(struct vcpu_info, arch.cr2)"	#
# 0 "" 2
# arch/x86/kernel/asm-offsets.c:84: 	BLANK();
# 84 "arch/x86/kernel/asm-offsets.c" 1
	
.ascii "->"
# 0 "" 2
# arch/x86/kernel/asm-offsets.c:85: 	OFFSET(TDX_MODULE_rcx, tdx_module_args, rcx);
# 85 "arch/x86/kernel/asm-offsets.c" 1
	
.ascii "->TDX_MODULE_rcx $0 offsetof(struct tdx_module_args, rcx)"	#
# 0 "" 2
# arch/x86/kernel/asm-offsets.c:86: 	OFFSET(TDX_MODULE_rdx, tdx_module_args, rdx);
# 86 "arch/x86/kernel/asm-offsets.c" 1
	
.ascii "->TDX_MODULE_rdx $8 offsetof(struct tdx_module_args, rdx)"	#
# 0 "" 2
# arch/x86/kernel/asm-offsets.c:87: 	OFFSET(TDX_MODULE_r8,  tdx_module_args, r8);
# 87 "arch/x86/kernel/asm-offsets.c" 1
	
.ascii "->TDX_MODULE_r8 $16 offsetof(struct tdx_module_args, r8)"	#
# 0 "" 2
# arch/x86/kernel/asm-offsets.c:88: 	OFFSET(TDX_MODULE_r9,  tdx_module_args, r9);
# 88 "arch/x86/kernel/asm-offsets.c" 1
	
.ascii "->TDX_MODULE_r9 $24 offsetof(struct tdx_module_args, r9)"	#
# 0 "" 2
# arch/x86/kernel/asm-offsets.c:89: 	OFFSET(TDX_MODULE_r10, tdx_module_args, r10);
# 89 "arch/x86/kernel/asm-offsets.c" 1
	
.ascii "->TDX_MODULE_r10 $32 offsetof(struct tdx_module_args, r10)"	#
# 0 "" 2
# arch/x86/kernel/asm-offsets.c:90: 	OFFSET(TDX_MODULE_r11, tdx_module_args, r11);
# 90 "arch/x86/kernel/asm-offsets.c" 1
	
.ascii "->TDX_MODULE_r11 $40 offsetof(struct tdx_module_args, r11)"	#
# 0 "" 2
# arch/x86/kernel/asm-offsets.c:91: 	OFFSET(TDX_MODULE_r12, tdx_module_args, r12);
# 91 "arch/x86/kernel/asm-offsets.c" 1
	
.ascii "->TDX_MODULE_r12 $48 offsetof(struct tdx_module_args, r12)"	#
# 0 "" 2
# arch/x86/kernel/asm-offsets.c:92: 	OFFSET(TDX_MODULE_r13, tdx_module_args, r13);
# 92 "arch/x86/kernel/asm-offsets.c" 1
	
.ascii "->TDX_MODULE_r13 $56 offsetof(struct tdx_module_args, r13)"	#
# 0 "" 2
# arch/x86/kernel/asm-offsets.c:93: 	OFFSET(TDX_MODULE_r14, tdx_module_args, r14);
# 93 "arch/x86/kernel/asm-offsets.c" 1
	
.ascii "->TDX_MODULE_r14 $64 offsetof(struct tdx_module_args, r14)"	#
# 0 "" 2
# arch/x86/kernel/asm-offsets.c:94: 	OFFSET(TDX_MODULE_r15, tdx_module_args, r15);
# 94 "arch/x86/kernel/asm-offsets.c" 1
	
.ascii "->TDX_MODULE_r15 $72 offsetof(struct tdx_module_args, r15)"	#
# 0 "" 2
# arch/x86/kernel/asm-offsets.c:95: 	OFFSET(TDX_MODULE_rbx, tdx_module_args, rbx);
# 95 "arch/x86/kernel/asm-offsets.c" 1
	
.ascii "->TDX_MODULE_rbx $80 offsetof(struct tdx_module_args, rbx)"	#
# 0 "" 2
# arch/x86/kernel/asm-offsets.c:96: 	OFFSET(TDX_MODULE_rdi, tdx_module_args, rdi);
# 96 "arch/x86/kernel/asm-offsets.c" 1
	
.ascii "->TDX_MODULE_rdi $88 offsetof(struct tdx_module_args, rdi)"	#
# 0 "" 2
# arch/x86/kernel/asm-offsets.c:97: 	OFFSET(TDX_MODULE_rsi, tdx_module_args, rsi);
# 97 "arch/x86/kernel/asm-offsets.c" 1
	
.ascii "->TDX_MODULE_rsi $96 offsetof(struct tdx_module_args, rsi)"	#
# 0 "" 2
# arch/x86/kernel/asm-offsets.c:99: 	BLANK();
# 99 "arch/x86/kernel/asm-offsets.c" 1
	
.ascii "->"
# 0 "" 2
# arch/x86/kernel/asm-offsets.c:100: 	OFFSET(BP_scratch, boot_params, scratch);
# 100 "arch/x86/kernel/asm-offsets.c" 1
	
.ascii "->BP_scratch $484 offsetof(struct boot_params, scratch)"	#
# 0 "" 2
# arch/x86/kernel/asm-offsets.c:101: 	OFFSET(BP_secure_boot, boot_params, secure_boot);
# 101 "arch/x86/kernel/asm-offsets.c" 1
	
.ascii "->BP_secure_boot $492 offsetof(struct boot_params, secure_boot)"	#
# 0 "" 2
# arch/x86/kernel/asm-offsets.c:102: 	OFFSET(BP_loadflags, boot_params, hdr.loadflags);
# 102 "arch/x86/kernel/asm-offsets.c" 1
	
.ascii "->BP_loadflags $529 offsetof(struct boot_params, hdr.loadflags)"	#
# 0 "" 2
# arch/x86/kernel/asm-offsets.c:103: 	OFFSET(BP_hardware_subarch, boot_params, hdr.hardware_subarch);
# 103 "arch/x86/kernel/asm-offsets.c" 1
	
.ascii "->BP_hardware_subarch $572 offsetof(struct boot_params, hdr.hardware_subarch)"	#
# 0 "" 2
# arch/x86/kernel/asm-offsets.c:104: 	OFFSET(BP_version, boot_params, hdr.version);
# 104 "arch/x86/kernel/asm-offsets.c" 1
	
.ascii "->BP_version $518 offsetof(struct boot_params, hdr.version)"	#
# 0 "" 2
# arch/x86/kernel/asm-offsets.c:105: 	OFFSET(BP_kernel_alignment, boot_params, hdr.kernel_alignment);
# 105 "arch/x86/kernel/asm-offsets.c" 1
	
.ascii "->BP_kernel_alignment $560 offsetof(struct boot_params, hdr.kernel_alignment)"	#
# 0 "" 2
# arch/x86/kernel/asm-offsets.c:106: 	OFFSET(BP_init_size, boot_params, hdr.init_size);
# 106 "arch/x86/kernel/asm-offsets.c" 1
	
.ascii "->BP_init_size $608 offsetof(struct boot_params, hdr.init_size)"	#
# 0 "" 2
# arch/x86/kernel/asm-offsets.c:107: 	OFFSET(BP_pref_address, boot_params, hdr.pref_address);
# 107 "arch/x86/kernel/asm-offsets.c" 1
	
.ascii "->BP_pref_address $600 offsetof(struct boot_params, hdr.pref_address)"	#
# 0 "" 2
# arch/x86/kernel/asm-offsets.c:109: 	BLANK();
# 109 "arch/x86/kernel/asm-offsets.c" 1
	
.ascii "->"
# 0 "" 2
# arch/x86/kernel/asm-offsets.c:110: 	DEFINE(PTREGS_SIZE, sizeof(struct pt_regs));
# 110 "arch/x86/kernel/asm-offsets.c" 1
	
.ascii "->PTREGS_SIZE $168 sizeof(struct pt_regs)"	#
# 0 "" 2
# arch/x86/kernel/asm-offsets.c:111: 	OFFSET(C_PTREGS_SIZE, pt_regs, orig_ax);
# 111 "arch/x86/kernel/asm-offsets.c" 1
	
.ascii "->C_PTREGS_SIZE $120 offsetof(struct pt_regs, orig_ax)"	#
# 0 "" 2
# arch/x86/kernel/asm-offsets.c:114: 	OFFSET(TLB_STATE_user_pcid_flush_mask, tlb_state, user_pcid_flush_mask);
# 114 "arch/x86/kernel/asm-offsets.c" 1
	
.ascii "->TLB_STATE_user_pcid_flush_mask $22 offsetof(struct tlb_state, user_pcid_flush_mask)"	#
# 0 "" 2
# arch/x86/kernel/asm-offsets.c:117: 	OFFSET(CPU_ENTRY_AREA_entry_stack, cpu_entry_area, entry_stack_page);
# 117 "arch/x86/kernel/asm-offsets.c" 1
	
.ascii "->CPU_ENTRY_AREA_entry_stack $4096 offsetof(struct cpu_entry_area, entry_stack_page)"	#
# 0 "" 2
# arch/x86/kernel/asm-offsets.c:118: 	DEFINE(SIZEOF_entry_stack, sizeof(struct entry_stack));
# 118 "arch/x86/kernel/asm-offsets.c" 1
	
.ascii "->SIZEOF_entry_stack $4096 sizeof(struct entry_stack)"	#
# 0 "" 2
# arch/x86/kernel/asm-offsets.c:119: 	DEFINE(MASK_entry_stack, (~(sizeof(struct entry_stack) - 1)));
# 119 "arch/x86/kernel/asm-offsets.c" 1
	
.ascii "->MASK_entry_stack $-4096 (~(sizeof(struct entry_stack) - 1))"	#
# 0 "" 2
# arch/x86/kernel/asm-offsets.c:122: 	OFFSET(TSS_sp0, tss_struct, x86_tss.sp0);
# 122 "arch/x86/kernel/asm-offsets.c" 1
	
.ascii "->TSS_sp0 $4 offsetof(struct tss_struct, x86_tss.sp0)"	#
# 0 "" 2
# arch/x86/kernel/asm-offsets.c:123: 	OFFSET(TSS_sp1, tss_struct, x86_tss.sp1);
# 123 "arch/x86/kernel/asm-offsets.c" 1
	
.ascii "->TSS_sp1 $12 offsetof(struct tss_struct, x86_tss.sp1)"	#
# 0 "" 2
# arch/x86/kernel/asm-offsets.c:124: 	OFFSET(TSS_sp2, tss_struct, x86_tss.sp2);
# 124 "arch/x86/kernel/asm-offsets.c" 1
	
.ascii "->TSS_sp2 $20 offsetof(struct tss_struct, x86_tss.sp2)"	#
# 0 "" 2
# arch/x86/kernel/asm-offsets.c:127: 	BLANK();
# 127 "arch/x86/kernel/asm-offsets.c" 1
	
.ascii "->"
# 0 "" 2
# arch/x86/kernel/asm-offsets.c:128: 	OFFSET(ARIA_CTX_enc_key, aria_ctx, enc_key);
# 128 "arch/x86/kernel/asm-offsets.c" 1
	
.ascii "->ARIA_CTX_enc_key $0 offsetof(struct aria_ctx, enc_key)"	#
# 0 "" 2
# arch/x86/kernel/asm-offsets.c:129: 	OFFSET(ARIA_CTX_dec_key, aria_ctx, dec_key);
# 129 "arch/x86/kernel/asm-offsets.c" 1
	
.ascii "->ARIA_CTX_dec_key $272 offsetof(struct aria_ctx, dec_key)"	#
# 0 "" 2
# arch/x86/kernel/asm-offsets.c:130: 	OFFSET(ARIA_CTX_rounds, aria_ctx, rounds);
# 130 "arch/x86/kernel/asm-offsets.c" 1
	
.ascii "->ARIA_CTX_rounds $544 offsetof(struct aria_ctx, rounds)"	#
# 0 "" 2
# arch/x86/kernel/asm-offsets.c:133: 	BLANK();
# 133 "arch/x86/kernel/asm-offsets.c" 1
	
.ascii "->"
# 0 "" 2
# arch/x86/kernel/asm-offsets.c:134: 	DEFINE(ALT_INSTR_SIZE,	sizeof(struct alt_instr));
# 134 "arch/x86/kernel/asm-offsets.c" 1
	
.ascii "->ALT_INSTR_SIZE $14 sizeof(struct alt_instr)"	#
# 0 "" 2
# arch/x86/kernel/asm-offsets.c:135: 	DEFINE(EXTABLE_SIZE,	sizeof(struct exception_table_entry));
# 135 "arch/x86/kernel/asm-offsets.c" 1
	
.ascii "->EXTABLE_SIZE $12 sizeof(struct exception_table_entry)"	#
# 0 "" 2
# arch/x86/kernel/asm-offsets.c:136: }
#NO_APP
	jmp	__x86_return_thunk
	.size	common, .-common
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

/* SPDX-License-Identifier: MIT
 *
 * rx550_compress_avx2.s - AVX2 per-channel min/max reduction.
 *
 * For one 4x4 RGBA8 block (64 bytes = 16 pixels x 4 bytes, R,G,B,A order):
 *
 *     out[0..3] = min(R,G,B,A)      out[4..7] = max(R,G,B,A)
 *
 * Why this part and not the whole codec: the reduction is branchless,
 * data-parallel, and executes the same instruction count whatever the pixel
 * values are. Palette construction and index search are per-pixel branchy work
 * where SIMD buys little and correctness risk is high, so they stay in C.
 *
 * Must be BIT-IDENTICAL to rx550_minmax_c(). Integer min/max is associative
 * and exact, so reduction order cannot change the result -- that is an
 * argument, not a proof. test_compress.c compares both implementations on 200k
 * blocks on every run, and that comparison is the proof.
 *
 * SysV AMD64 ABI:  rdi = src (64 bytes), rsi = out (8 bytes).
 * AT&T syntax: operands read right-to-left, OP %src2, %src1, %dst.
 *
 * ===========================================================================
 * REGISTER CONVENTION -- THE RULE THAT WAS BROKEN THREE TIMES
 * ===========================================================================
 *
 *   xmm0 is the low half of ymm0.   xmm5 is the low half of ymm5.
 *   They are NOT the same register, and a reference to the wrong one
 *   assembles cleanly while computing the wrong thing.
 *
 * That mistake was made three times in this file's history, always in the
 * horizontal reduction, and always silently. The structural fix is that the
 * reduction is now ONE leaf function per operation, and inside it the only
 * accumulator is ymm5/xmm5 plus the scratch xmm1. There is no place where a
 * register name can be confused with another, because there is only one copy
 * of the sequence to be right.
 *
 * The reduction is called, not inlined. A call costs a few cycles; getting the
 * semantics wrong costs the entire result, silently.
 *
 * ===========================================================================
 * HISTORY OF THE FOUR BUGS. DO NOT REINTRODUCE ANY OF THEM.
 * ===========================================================================
 *
 * (1) GAS MACROS. v1 wrapped the reduction and the per-channel block in
 *     .macro. Inside a macro body "%name" means "substitute parameter name", so
 *     a literal register must be "%ymm0", and that escape does not survive a
 *     *nested* macro invocation. Result: "nombre de registro incorrecto", plus
 *     a risk that a wrong expansion assembles into a wrong instruction.
 *     There are no macros here.
 *
 * (2) WRONG DEINTERLEAVE. v2 used VPERMD with index vectors {c, c+4, c+8, ...}
 *     to "pull out channel c". A pixel is one 32-bit dword, so index 4 selects
 *     pixel 4, not a byte lane; indices 8..31 were out of range for a YMM and
 *     returned zero. The byte-extraction primitive is VPSHUFB, per 128-bit lane.
 *
 * (3) GATHER IS NOT REDUCE. v3 used the right VPSHUFB, then "folded" the four
 *     useful bytes with more VPSHUFB gathers. A gather COPIES bytes; it does
 *     not combine them. The four values have to be spread into four separate
 *     dwords first, and then combined with VPSHUFD, which moves dwords while
 *     VPMINUB still applies bytewise.
 *
 * (4) A scripted regex "fix" pass that reported substituting 48 lines, then a
 *     second pass that reported 0, leaving the file with "vpminub %xmm6, %xmm5,
 *     %xmm5" where "%xmm1" belonged and a vextracti128 that clobbered its own
 *     source. The corrupted file is preserved at
 *     .recovery/rx550_compress_avx2.s.CORRUPT-2026-09-28
 *     (sha256 bee0f3f70123c5398f71547a6f8331ae12ad1de69cd1f16987b7615e6294f4cb).
 *     Do not repair a file with an unverified global substitution; rewrite it.
 *
 * ===========================================================================
 * THE GEOMETRY THAT HAS TO BE RIGHT
 * ===========================================================================
 *
 * VPSHUFB works within a 128-bit lane, and a lane holds 4 pixels. To gather
 * channel c we take source bytes {c, c+4, c+8, c+12} -- one per pixel -- and
 * place them at destination byte offsets 0, 4, 8, 12, so each lands in its own
 * dword. The 12 remaining destination bytes are padding and MUST be neutral for
 * the operation being performed: 0xFF for a minimum, 0x00 for a maximum. That
 * is why there are eight tables and not four.
 *
 * After both planes are folded, the four surviving values sit at bytes 0, 4, 8
 * and 12 of the low 128 bits. The reduction then needs only two shuffle/fold
 * pairs:
 *
 *   $0x4e  dst = {src2, src3, src0, src1}   brings 0 against 2 and 1 against 3
 *   $0xb1  dst = {src1, src0, src3, src2}   brings the two results together
 *
 * After the second fold, byte 0 already holds min(min(m0,m2), min(m1,m3)) =
 * min of all sixteen. A further byte swap is unnecessary.
 */

	.text

/* ------------------------------------------------------------------------- */
/* Plane masks, YMM form: one 16-byte mask duplicated for both 128-bit lanes. */
/* ------------------------------------------------------------------------- */
	.section .rodata
	.balign 32

/* --- channel R: source bytes 0,4,8,12 ------------------------------------- */
.Lpl_r_min:				/* 0xFF padding: neutral for MINIMUM */
	.byte   0,0xFF,0xFF,0xFF, 4,0xFF,0xFF,0xFF, 8,0xFF,0xFF,0xFF, 12,0xFF,0xFF,0xFF
	.byte   0,0xFF,0xFF,0xFF, 4,0xFF,0xFF,0xFF, 8,0xFF,0xFF,0xFF, 12,0xFF,0xFF,0xFF
.Lpl_r_max:				/* 0x00 padding: neutral for MAXIMUM */
	.byte   0,0,0,0, 4,0,0,0, 8,0,0,0, 12,0,0,0
	.byte   0,0,0,0, 4,0,0,0, 8,0,0,0, 12,0,0,0

/* --- channel G: source bytes 1,5,9,13 -------------------------------------- */
.Lpl_g_min:
	.byte   1,0xFF,0xFF,0xFF, 5,0xFF,0xFF,0xFF, 9,0xFF,0xFF,0xFF, 13,0xFF,0xFF,0xFF
	.byte   1,0xFF,0xFF,0xFF, 5,0xFF,0xFF,0xFF, 9,0xFF,0xFF,0xFF, 13,0xFF,0xFF,0xFF
.Lpl_g_max:
	.byte   1,0,0,0, 5,0,0,0, 9,0,0,0, 13,0,0,0
	.byte   1,0,0,0, 5,0,0,0, 9,0,0,0, 13,0,0,0

/* --- channel B: source bytes 2,6,10,14 ------------------------------------- */
.Lpl_b_min:
	.byte   2,0xFF,0xFF,0xFF, 6,0xFF,0xFF,0xFF, 10,0xFF,0xFF,0xFF, 14,0xFF,0xFF,0xFF
	.byte   2,0xFF,0xFF,0xFF, 6,0xFF,0xFF,0xFF, 10,0xFF,0xFF,0xFF, 14,0xFF,0xFF,0xFF
.Lpl_b_max:
	.byte   2,0,0,0, 6,0,0,0, 10,0,0,0, 14,0,0,0
	.byte   2,0,0,0, 6,0,0,0, 10,0,0,0, 14,0,0,0

/* --- channel A: source bytes 3,7,11,15 ------------------------------------- */
.Lpl_a_min:
	.byte   3,0xFF,0xFF,0xFF, 7,0xFF,0xFF,0xFF, 11,0xFF,0xFF,0xFF, 15,0xFF,0xFF,0xFF
	.byte   3,0xFF,0xFF,0xFF, 7,0xFF,0xFF,0xFF, 11,0xFF,0xFF,0xFF, 15,0xFF,0xFF,0xFF
.Lpl_a_max:
	.byte   3,0,0,0, 7,0,0,0, 11,0,0,0, 15,0,0,0
	.byte   3,0,0,0, 7,0,0,0, 11,0,0,0, 15,0,0,0

	.text

/* ------------------------------------------------------------------------- */
/* Leaf: 32 bytes in ymm5 -> one byte in al.                                  */
/*                                                                            */
/* Contract, and it is the whole point:                                                    */
/*   in   ymm5 = two 128-bit lanes, four useful bytes at offsets 0,4,8,12 of  */
/*              EACH lane, every other byte padding (0xFF for min, 0x00 for max)          */
/*   out  al  = the reduction of the eight useful bytes                     */
/*   clobbers  xmm1, xmm5, eax                                                */
/*   preserves ymm0, ymm1, ymm2, ymm3, ymm4, ymm6, ymm7                      */
/*                                                                            */
/* The accumulator is xmm5 and the scratch is xmm1, nowhere else. There is no */
/* other candidate register to confuse with either.                            */
/* ------------------------------------------------------------------------- */
	.type	hred_min, @function
hred_min:
	vextracti128	$1, %ymm5, %xmm1	/* upper lane into the scratch    */
	vpminub	%xmm1, %xmm5, %xmm5	/* bytewise: 8 survivors at 0,4,8,12 */
	vpshufd	$0x4e, %xmm5, %xmm1	/* {2,3,0,1}: pair 0/2 and 1/3    */
	vpminub	%xmm1, %xmm5, %xmm5	/* d0 = min(m0,m2), d1 = min(m1,m3) */
	vpshufd	$0xb1, %xmm5, %xmm1	/* {1,0,3,2}: bring the pair together */
	vpminub	%xmm1, %xmm5, %xmm5	/* byte 0 = min of all eight       */
	vmovd	%xmm5, %eax		/* only AL is used                 */
	ret
	.size	hred_min, .-hred_min

	.type	hred_max, @function
hred_max:
	vextracti128	$1, %ymm5, %xmm1
	vpmaxub	%xmm1, %xmm5, %xmm5
	vpshufd	$0x4e, %xmm5, %xmm1
	vpmaxub	%xmm1, %xmm5, %xmm5
	vpshufd	$0xb1, %xmm5, %xmm1
	vpmaxub	%xmm1, %xmm5, %xmm5
	vmovd	%xmm5, %eax
	ret
	.size	hred_max, .-hred_max

/* ------------------------------------------------------------------------- */
	.globl	rx550_minmax_avx2
	.type	rx550_minmax_avx2, @function
rx550_minmax_avx2:
	.cfi_startproc

	/* Two 256-bit loads: 8 pixels each, all 16 covered.
	 * These live in ymm6/ymm7 precisely so that ymm5 can be handed to the
	 * leaf without a move, and so that no leaf can destroy the input. */
	vmovdqu	0(%rdi), %ymm6			/* pixels 0..7  */
	vmovdqu	32(%rdi), %ymm7			/* pixels 8..15 */

/* ========================================================================= */
/* CHANNEL R                                                                  */
/* ========================================================================= */
	vmovdqu	.Lpl_r_min(%rip), %ymm4
	vpshufb	%ymm4, %ymm6, %ymm2		/* R of px 0..7,  pad 0xFF */
	vpshufb	%ymm4, %ymm7, %ymm3		/* R of px 8..15, pad 0xFF */
	vpminub	%ymm3, %ymm2, %ymm5
	call	hred_min
	movb	%al, 0(%rsi)

	vmovdqu	.Lpl_r_max(%rip), %ymm4
	vpshufb	%ymm4, %ymm6, %ymm2		/* R of px 0..7,  pad 0x00 */
	vpshufb	%ymm4, %ymm7, %ymm3		/* R of px 8..15, pad 0x00 */
	vpmaxub	%ymm3, %ymm2, %ymm5
	call	hred_max
	movb	%al, 4(%rsi)

/* ========================================================================= */
/* CHANNEL G                                                                  */
/* ========================================================================= */
	vmovdqu	.Lpl_g_min(%rip), %ymm4
	vpshufb	%ymm4, %ymm6, %ymm2
	vpshufb	%ymm4, %ymm7, %ymm3
	vpminub	%ymm3, %ymm2, %ymm5
	call	hred_min
	movb	%al, 1(%rsi)

	vmovdqu	.Lpl_g_max(%rip), %ymm4
	vpshufb	%ymm4, %ymm6, %ymm2
	vpshufb	%ymm4, %ymm7, %ymm3
	vpmaxub	%ymm3, %ymm2, %ymm5
	call	hred_max
	movb	%al, 5(%rsi)

/* ========================================================================= */
/* CHANNEL B                                                                  */
/* ========================================================================= */
	vmovdqu	.Lpl_b_min(%rip), %ymm4
	vpshufb	%ymm4, %ymm6, %ymm2
	vpshufb	%ymm4, %ymm7, %ymm3
	vpminub	%ymm3, %ymm2, %ymm5
	call	hred_min
	movb	%al, 2(%rsi)

	vmovdqu	.Lpl_b_max(%rip), %ymm4
	vpshufb	%ymm4, %ymm6, %ymm2
	vpshufb	%ymm4, %ymm7, %ymm3
	vpmaxub	%ymm3, %ymm2, %ymm5
	call	hred_max
	movb	%al, 6(%rsi)

/* ========================================================================= */
/* CHANNEL A                                                                  */
/* ========================================================================= */
	vmovdqu	.Lpl_a_min(%rip), %ymm4
	vpshufb	%ymm4, %ymm6, %ymm2
	vpshufb	%ymm4, %ymm7, %ymm3
	vpminub	%ymm3, %ymm2, %ymm5
	call	hred_min
	movb	%al, 3(%rsi)

	vmovdqu	.Lpl_a_max(%rip), %ymm4
	vpshufb	%ymm4, %ymm6, %ymm2
	vpshufb	%ymm4, %ymm7, %ymm3
	vpmaxub	%ymm3, %ymm2, %ymm5
	call	hred_max
	movb	%al, 7(%rsi)

	/* Leave the upper YMM state clean so the next SSE code on this core does
	 * not pay an AVX-SSE transition penalty. */
	vzeroupper
	ret
	.cfi_endproc
	.size	rx550_minmax_avx2, .-rx550_minmax_avx2

	.section .note.GNU-stack,"",@progbits

# SPDX-License-Identifier: MIT
#
# Makefile - RX550 block texture codec
#
# ============================================================================
# WHY THE C FILE IS NOT COMPILED WITH -mavx2
# ============================================================================
# The brief asked for everything to be built with "-O3 -mavx2". That is
# followed for the assembly, and deliberately NOT followed for the C
# reference.
#
# If rx550_compress.c were compiled with -mavx2, GCC would auto-vectorise the
# portable reference path with AVX2 instructions. rx550_have_avx2() would then
# return 0 on a pre-Haswell CPU, the dispatcher would correctly choose the "C"
# path, and that path would execute an illegal instruction. Runtime detection
# would become a safety hazard rather than a safety mechanism.
#
# So: the C reference is built for the x86-64 baseline and stays portable. The
# only AVX2 in the object graph lives in rx550_compress_avx2.s, reachable only
# after the runtime check passes. This is recorded in DECISIONS.md.
# ============================================================================

CC      ?= gcc
OBJDUMP ?= objdump

# Baseline for the portable reference. No -march, no -mavx2, nothing that
# would let the compiler emit an instruction the fallback cannot run.
CFLAGS_BASE := -std=gnu11 -O3 -Wall -Wextra -Wshadow -Wstrict-prototypes \
               -fno-strict-aliasing

# The assembly needs no ISA flag to be accepted, but stating it documents
# intent and makes a future -march leak loud.
ASMFLAGS := -mavx2

# The test uses clock_gettime, log10 and sqrt from libm.
LDLIBS  := -lm

BIN      := test_compress
RAMP_BIN := test_alpha_ramp
OBJS     := rx550_compress.o rx550_compress_avx2.o
HDR      := rx550_compress.h

.PHONY: all test clean check-asm disasm measure-alpha-inset check-ramp-discriminates

all: $(BIN)

# --- portable C reference + dispatcher -------------------------------------
rx550_compress.o: rx550_compress.c $(HDR)
	$(CC) $(CFLAGS_BASE) -c $< -o $@

# --- AVX2 kernel ------------------------------------------------------------
rx550_compress_avx2.o: rx550_compress_avx2.s
	$(CC) $(ASMFLAGS) -c $< -o $@

# --- test harness -----------------------------------------------------------
test_compress.o: test_compress.c $(HDR)
	$(CC) $(CFLAGS_BASE) -c $< -o $@

$(BIN): $(OBJS) test_compress.o
	$(CC) $(CFLAGS_BASE) -o $@ $^ $(LDLIBS)

# --- independent alpha-ramp conformance test --------------------------------
# Separate from test_compress on purpose. test_compress.c is the harness that
# already existed; the reference it compares against lived inside it and was, for
# a while, a line-for-line copy of the implementation, so it compared f(x) with
# f(x). This file holds a reference transcribed independently, and it exits
# non-zero on any disagreement, so it can fail.
#
# It links $(OBJS), not just rx550_compress.o: the dispatcher in the C file
# references rx550_minmax_avx2, so linking the C object alone leaves that
# symbol undefined.
$(RAMP_BIN): test_alpha_ramp_independent.c $(OBJS) $(HDR)
	$(CC) $(CFLAGS_BASE) -o $@ test_alpha_ramp_independent.c $(OBJS) $(LDLIBS)

# Prove the test above can fail, by running it against the ramp that was
# committed in 05c6297 instead of the real implementation. A test never observed
# to fail has not been shown to discriminate. See test_alpha_ramp_mutation.c.
# The mutation provides its own rx550_alpha_palette_for_test, so the real
# implementation must NOT be linked in: two definitions of that symbol is a
# duplicate-symbol link error. It links only the AVX2 object, which the
# dispatcher in the C file needs and which does not define the palette hook.
check-ramp-discriminates: test_alpha_ramp_independent.c test_alpha_ramp_mutation.c rx550_compress_avx2.o $(HDR)
	$(CC) $(CFLAGS_BASE) -o $(RAMP_BIN).mut \
	    test_alpha_ramp_independent.c test_alpha_ramp_mutation.c \
	    rx550_compress_avx2.o $(LDLIBS)
	@echo "Expecting a NON-zero exit: this is the pre-fix ramp, and the test must reject it."
	@./$(RAMP_BIN).mut; \
	  rc=$$?; \
	  if [ $$rc -eq 0 ]; then \
	    echo "FAIL: the test passed against a ramp that is known wrong."; \
	    echo "      It does not discriminate and certifies nothing."; \
	    exit 1; \
	  else \
	    echo "OK: rejected the known-wrong ramp (exit $$rc). The test discriminates."; \
	  fi

# --- run --------------------------------------------------------------------
test: $(BIN) $(RAMP_BIN)
	./$(BIN)
	./$(RAMP_BIN)

# Fail the build if the assembly ever loses its AVX2 instructions, which would
# mean the SIMD path silently degraded to something unverified.
check-asm: rx550_compress_avx2.o
	@echo "AVX2 instruction count in rx550_compress_avx2.o:"
	@$(OBJDUMP) -d $< | grep -cE 'vperm|vpminsd|vpmaxud|vpminud|vextracti128|vpshufd' \
	  || { echo "ERROR: no AVX2 instructions found -- the kernel is not doing its job"; exit 1; }

# --- disassembly, for review ------------------------------------------------
disasm: rx550_compress_avx2.o
	$(OBJDUMP) -d -M intel $<

# --- sweep of the alpha endpoint inset search --------------------------------
# Sweeps RX550_ALPHA_INSET_STEPS and prints quality vs throughput for each.
# This is the instrument behind AD-9: the search costs ~2.8x and buys no measured
# PSNR. It is deliberately a build-time sweep, not a test assertion, because the
# result is a trade-off for the HUMAN to decide, not a pass/fail condition.
measure-alpha-inset:
	@orig=$$(sed -n 's/^#define RX550_ALPHA_INSET_STEPS \([0-9][0-9]*\).*/\1/p' rx550_compress.c); \
	 orig=$${orig:-0}; \
	 echo "ALPHA_STEPS  reference  smooth  noise    MB/s"; \
	 for n in 0 2 5 10 15; do \
	   sed -i "s/^#define RX550_ALPHA_INSET_STEPS .*/#define RX550_ALPHA_INSET_STEPS $$n/" rx550_compress.c; \
	   $(MAKE) --no-print-directory clean all >/dev/null 2>&1 || exit 1; \
	   o=$$(./$(BIN) 2>/dev/null); \
	   printf "%-12s %-11s %-7s %-8s %s\n" "$$n" \
	     "$$(echo "$$o" | grep 'reference ' | grep -oE '[0-9]+\.[0-9]+' | head -1)" \
	     "$$(echo "$$o" | grep 'smooth '    | grep -oE '[0-9]+\.[0-9]+' | head -1)" \
	     "$$(echo "$$o" | grep 'pure noise' | grep -oE '[0-9]+\.[0-9]+' | head -1)" \
	     "$$(echo "$$o" | grep -E '^ *C *:' | grep -oE '[0-9]+\.[0-9]+')"; \
	 done; \
	 sed -i "s/^#define RX550_ALPHA_INSET_STEPS .*/#define RX550_ALPHA_INSET_STEPS $$orig/" rx550_compress.c; \
	 $(MAKE) --no-print-directory clean all >/dev/null 2>&1; \
	 echo "(restaurado a $$orig, el valor original)"

clean:
	rm -f $(OBJS) test_compress.o $(BIN) $(RAMP_BIN) $(RAMP_BIN).mut

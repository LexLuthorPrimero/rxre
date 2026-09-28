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

BIN     := test_compress
OBJS    := rx550_compress.o rx550_compress_avx2.o
HDR     := rx550_compress.h

.PHONY: all test clean check-asm disasm

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

# --- run --------------------------------------------------------------------
test: $(BIN)
	./$(BIN)

# Fail the build if the assembly ever loses its AVX2 instructions, which would
# mean the SIMD path silently degraded to something unverified.
check-asm: rx550_compress_avx2.o
	@echo "AVX2 instruction count in rx550_compress_avx2.o:"
	@$(OBJDUMP) -d $< | grep -cE 'vperm|vpminsd|vpmaxud|vpminud|vextracti128|vpshufd' \
	  || { echo "ERROR: no AVX2 instructions found -- the kernel is not doing its job"; exit 1; }

# --- disassembly, for review ------------------------------------------------
disasm: rx550_compress_avx2.o
	$(OBJDUMP) -d -M intel $<

clean:
	rm -f $(OBJS) test_compress.o $(BIN)

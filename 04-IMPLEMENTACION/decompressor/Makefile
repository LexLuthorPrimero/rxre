# SPDX-License-Identifier: MIT
#
# Makefile - RX550_BC3 GPU decompressor
#
# ============================================================================
# WHY THIS DIRECTORY HAS A MAKEFILE (D16)
# ============================================================================
# shader_vs_c.c is a differential validator: it runs the shader's arithmetic in C
# and compares it against rx550_decompress_block(). It is the only mechanism that
# reconciles decompress_bc3.comp with the Fase 1 codec.
#
# It used to be run by hand. That is not good enough, and this project has the
# receipts: when D13 removed the +3/+2 rounding offsets from the encoder and the
# shader, the copies of the ramp inside shader_vs_c.c kept them. The validator
# started reporting 248 of 4096 channels wrong while the encoder was correct, and
# nothing failed -- because nothing ran it.
#
# The same failure mode has already happened twice in this project: a reference
# in test_compress.c that was a character-for-character copy of the
# implementation, and a rename collision that left unresolved state. A test that
# only runs when someone remembers is not a test.
#
# So `make test` here runs it, and it exits non-zero on any disagreement.
# ============================================================================
#
# shader_vs_c.c #includes "rx550_compress.h" and calls rx550_compress_block_c(),
# rx550_decompress_block() and rx550_alpha_palette_for_test(), so it must be
# linked against the compressor objects in ../compressor, not compiled alone.
# The AVX2 object is required: rx550_compress.c's dispatcher references
# rx550_minmax_avx2, so linking only the C object leaves that symbol undefined.
#
# The C reference is compiled WITHOUT -mavx2 on purpose, for the reason given in
# ../compressor/Makefile: with -mavx2, GCC auto-vectorises the portable path and
# the runtime dispatch becomes a safety hazard. Only the assembly is AVX2.

CC      ?= gcc
CFLAGS  := -std=gnu11 -O2 -Wall -Wextra -fno-strict-aliasing -I../compressor
ASMFLAGS := -mavx2

# glslangValidator was built on this host on 2026-05-02; it is not installed
# system-wide and not in PATH. Override on the command line if it moves:
#   make GLSLANG=/path/to/glslangValidator decompress_bc3.spv
GLSLANG ?= /home/lucas/glslang/build/StandAlone/glslangValidator

COMP    := ../compressor
C_SRC   := shader_vs_c.c
C_OBJS  := $(COMP)/rx550_compress.o $(COMP)/rx550_compress_avx2.o
SPV     := decompress_bc3.spv
COMP_SP := $(COMP)/test_compress

.PHONY: all test clean check-spirv check-codec

all: shader_vs_c $(SPV)

# --- differential validator --------------------------------------------------
shader_vs_c: $(C_SRC) $(C_OBJS) $(COMP)/rx550_compress.h
	$(CC) $(CFLAGS) -o $@ $(C_SRC) $(C_OBJS) $(ASMFLAGS) -lm

# The compressor objects are built by the sibling Makefile, not here, so that
# there is exactly one definition of how the portable C is compiled. If they are
# missing, say so instead of failing with "no such file".
$(C_OBJS) $(COMP)/rx550_compress.h:
	@echo "ERROR: $@ not found. Run 'make -C ../compressor' first." >&2
	@exit 1

# --- SPIR-V ------------------------------------------------------------------
$(SPV): decompress_bc3.comp
	$(GLSLANG) -V $< -o $@

# --- run ---------------------------------------------------------------------
# Order matters: reconcile the shader with the C BEFORE compiling SPIR-V. A
# module compiled from a shader that disagrees with the encoder would be valid
# and useless, and its validity would hide the disagreement.
test: shader_vs_c
	./shader_vs_c

# The encoder's own suite, run from here so that a single command checks the
# whole chain: encoder conforms, shader conforms, and they agree.
check-codec: $(COMP_SP)
	$(COMP_SP)

# Confirms the SPIR-V is a real module: magic number 0x07230203, and the word
# count is what a 11984-byte file implies. Presence of the file is not evidence
# that it is valid; the magic bytes are.
check-spirv: $(SPV)
	@echo "  bytes   : $$(stat -c%s $(SPV))"
	@echo "  magic   : $$(od -An -tx4 -N4 $(SPV) | tr -d ' ')  (esperado 07230203)"
	@echo "  palabras: $$(expr $$(stat -c%s $(SPV)) / 4)"
	@od -An -tx4 -N4 $(SPV) | grep -q 07230203 \
	  || { echo "  ERROR: no es un modulo SPIR-V"; exit 1; }
	@echo "  OK: modulo SPIR-V con cabecera valida"
	@echo "  ATENCION: esto NO es validacion de esquema. Requiere spirv-val,"
	@echo "  que no esta instalado en este host (NOT_AVAILABLE)."

clean:
	rm -f shader_vs_c $(SPV)

# SPDX-License-Identifier: MIT
#
# Makefile - pipeline de integracion Fase 1 (compresor CPU) -> Fase 2
#             (descompresor GPU sobre la RX 550).
#
# Este Makefile construye DOS binarios con nombres estables en bin/:
#
#   bin/rx550_compress     PNG -> BC3          (Fase 1, CPU)
#   bin/rx550_decompress   BC3 -> PNG en GPU   (Fase 2, Vulkan compute)
#
# Los nombres son estables a proposito: integration_test.sh los invoca por
# nombre, no por ruta de objeto. Un binario que cambia de nombre rompe el
# pipeline sin que ningun test falle de forma util.
#
# ---------------------------------------------------------------------------
# POR QUE LOS OBJETOS DEL CODEC SE COMPILAN AQUI Y NO SE COPIAN
# ---------------------------------------------------------------------------
# ../compressor/Makefile es el unico sitio que define como se compila el
# portable de referencia (sin -mavx2) y el nucleo AVX2 (con -mavx2). Si este
# Makefile los recompilara con otros flags, habria dos "rx550_compress.o"
# distintos y el pipeline validaria el que este Makefile hizo, no el que
# instala el modulo. Se enlazan los objetos de ahi, no se reconstruyen.
#
# La regla `codec-objects` construye ../compressor si hace falta, para que
# `make -C 04-IMPLEMENTACION` funcione desde limpio sin pasos extra.

CC      ?= gcc
CFLAGS  := -std=gnu11 -O2 -Wall -Wextra -Wshadow -Wno-unused-parameter \
           -fno-strict-aliasing
LDFLAGS :=
LIBS    := -lm -lz -lvulkan -ldl

COMP := compressor
DEC  := decompressor
BIN  := bin

COMMON_SRC := common/png_rw.c
COMPRESS_SRC := tools/rx550_compress.c
DECOMPRESS_SRC := tools/rx550_decompress.c

CODEC_OBJS := $(COMP)/rx550_compress.o $(COMP)/rx550_compress_avx2.o

BINS := $(BIN)/rx550_compress $(BIN)/rx550_decompress

.PHONY: all pipeline run clean distclean codec-objects

all: $(BINS)

pipeline: all

# --- codec objects (owned by ../compressor/Makefile) -------------------------
codec-objects:
	@$(MAKE) --no-print-directory -C $(COMP) all

$(CODEC_OBJS) $(COMP)/rx550_compress.h: codec-objects
	@:

# The shader is NOT built here. rx550_decompress loads
# ../decompressor/decompress_bc3.spv relative to its working directory, which
# integration_test.sh sets to ../decompressor. Building it from a second place
# would produce a module that is validated here and never the one the tool
# loads. integration_test.sh regenerates it via the decompressor Makefile.

# --- bin/rx550_compress ------------------------------------------------------
$(BIN)/rx550_compress: $(COMPRESS_SRC) $(COMMON_SRC) common/png_rw.h $(CODEC_OBJS)
	@mkdir -p $(BIN)
	$(CC) $(CFLAGS) -o $@ $(COMPRESS_SRC) $(COMMON_SRC) \
		$(CODEC_OBJS) $(LDFLAGS) $(LIBS) -Icommon

# --- bin/rx550_decompress ----------------------------------------------------
$(BIN)/rx550_decompress: $(DECOMPRESS_SRC) $(COMMON_SRC) common/png_rw.h $(CODEC_OBJS)
	@mkdir -p $(BIN)
	$(CC) $(CFLAGS) -o $@ $(DECOMPRESS_SRC) $(COMMON_SRC) \
		$(CODEC_OBJS) $(LDFLAGS) $(LIBS) -Icommon

# --- pipeline completo -------------------------------------------------------
# Fases 1 y 2 sobre el corpus, con salida en el formato pedido.
run: all
	@./integration_test.sh

clean:
	rm -f $(BINS)
	rm -rf work

distclean: clean
	$(MAKE) --no-print-directory -C $(COMP) clean
	$(MAKE) --no-print-directory -C $(DEC) clean

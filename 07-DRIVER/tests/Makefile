# SPDX-License-Identifier: GPL-2.0
#
# Userspace tests for the rx550 driver.
#
# These compile and run entirely in userspace. None of them loads the module or
# touches hardware, which is what makes them runnable on a host that refuses to
# load rx550.ko at all. That claim was WRONG and is retracted by 091: on this
# host CONFIG_MODULE_SIG_FORCE is not set, lockdown is [none] and SecureBoot is
# disabled, so an unsigned out-of-tree module compiles AND can be loaded. The
# real blocker is NIVEL 4 (insmod), which needs human authorization.
# That is a coverage limit, stated rather than hidden: a test that
# cannot run is not a passing test, and the ones here that do run are the ones
# that were designed to be runnable without the kernel side.
#
# Run from 07-DRIVER/:   make -C tests run

CC      ?= gcc
CFLAGS  ?= -std=gnu11 -O2 -Wall -Wextra -Wshadow
DATA    := data
BLOBSRC := /usr/lib/firmware/amdgpu/polaris12_sdma.bin.xz

# The SHA of the DECOMPRESSED blob, which is what the test reads. The .xz is 21 B
# and the payload is 12692 B; these are different numbers and quoting the
# compressed one next to the payload is how a fixture check silently passes.
BLOB_SHA256 := e27b3ec976f87e32883b9190e653b20d27f9e77da8dd2d77eeb10c35ee9f1e61

TESTS := test_firmware_parse test_firmware_load test_pm4 test_mmio test_mc

# Not a test: emits real encoder output for tools/rx550pm4val to parse. See the
# crosscheck target below for why that is not the same as a test.
EMIT := rx550pm4_emit

# Kernel-side sources the userspace tests compile directly. The test then
# exercises the same object the module links, not a transcription of it: a
# packet the test validates is the packet the driver emits.
KERNEL_SRC := ../kernel/rx550_pm4.c

# The HEADERS the test also compiles against, and this line exists because its
# absence cost a real error.
#
# The rule below depended only on KERNEL_SRC, so a change to a constant in
# rx550_pm4.h did not make test_pm4 stale: make saw test_pm4.c unchanged, saw
# rx550_pm4.c unchanged, and reported "up to date" while the binary still had the
# previous constant in it. That is the failure AGENTS.md calls out under
# PRE-EXECUTION CONTRACT CHECK -- never accept "it compiled" -- except worse,
# because nothing failed. The test then reported the OLD value against the NEW
# expectation, and the natural reading was "the code is wrong", when in fact the
# code had been right and the harness stale.
#
# $(wildcard) rather than a written list, so a new header is covered without
# anyone remembering to add it. Verified in both directions: with this, make
# rebuilds when a header changes; without it, make does not.
KERNEL_HDRS := $(wildcard ../kernel/*.h)

.PHONY: all run clean check-blob crosscheck emisor verify

all: $(TESTS) $(EMIT)

# Decompression happens here, not in the test. xz is an external program: if it
# were missing and the test shelled out to it, the test would fail for a reason
# that has nothing to do with the parser under test, and would look like a parser
# bug. Transform assets at build time; validate logic at run time.
$(DATA)/polaris12_sdma.bin: $(BLOBSRC)
	@echo "  decompressing $(BLOBSRC)"
	@xz -dc $< > $@.tmp
	@echo "$(BLOB_SHA256)  $@.tmp" | sha256sum -c - >/dev/null \
	  || { echo "  ERROR: SHA256 of the decompressed blob does not match"; \
	       echo "         expected $(BLOB_SHA256)"; \
	       rm -f $@.tmp; exit 1; }
	@mv $@.tmp $@
	@echo "  ok, $$(stat -c%s $@) B, SHA256 matches"

# Verifies the fixture on demand, for when a test result needs to be trusted.
check-blob: $(DATA)/polaris12_sdma.bin
	@sha256sum $(DATA)/polaris12_sdma.bin

test_firmware_parse: test_firmware_parse.c $(DATA)/polaris12_sdma.bin
	$(CC) $(CFLAGS) -o $@ $<

test_firmware_load: test_firmware_load.c ../userspace/librx550.c
	$(CC) $(CFLAGS) -o $@ $^

# -I../kernel so the test finds rx550_pm4.h; the sources are shared with the
# module. rx550_pm4.c includes <linux/types.h> and <linux/stddef.h>, which
# resolve against the running kernel's headers, so the test is built against the
# same definitions the module is.
# $<, no $^. Los .h son DEPENDENCIAS y no unidades de traduccion: pasarlos al
# compilador hace que cada uno se compile suelto, sin el <stdbool.h> que si
# incluye el .c compartido, y falla con "bool desconocido". Es el mismo error
# que el header documenta en su cabecera, y lo provoque yo al anadir la
# dependencia que debia arreglarlo.
# pm4decode.c se enlaza en test_pm4 porque el test DECODIFICA cada IB que
# produce el encoder. Sin el, el test solo mira el dword de cabecera de cada
# paquete, y eso no cubre ni un truncamiento ni un count que no cuadre.
# No se enlaza en rx550pm4_emit: ese lee la salida del driver, no la decodifica.
PM4DECODE_SRC := ../../tools/pm4decode.c
PM4DECODE_HDR := ../../tools/pm4decode.h

# test_mmio enlaza rx550_mmio.c, que es C PURO a proposito: la aritmetica del
# contrato de la ventana de registros no necesita el kernel para comprobarse, y
# por eso vive separada de la llamada a pci_iomap, que si lo necesita y esta en
# rx550_drv.c. Si las dos estuvieran juntas, este test no existiria.
test_mmio: test_mmio.c ../kernel/rx550_mmio.c ../kernel/rx550_mmio.h
	$(CC) $(CFLAGS) -o $@ $^

# test_mc enlaza rx550_mc.c, que es C PURO por la misma razon que rx550_mmio.c:
# la aritmetica del contrato de VRAM no necesita el kernel para comprobarse, y
# por eso vive separada del RREG32 que si lo necesita, en rx550_drv.c.
test_mc: test_mc.c ../kernel/rx550_mc.c ../kernel/rx550_mc.h
	$(CC) $(CFLAGS) -o $@ $^

test_pm4: test_pm4.c $(KERNEL_SRC) $(KERNEL_HDRS) $(PM4DECODE_SRC) $(PM4DECODE_HDR)
	$(CC) $(CFLAGS) -DPM4DECODE_NO_MAIN -I../kernel -I../../tools -o $@ \
		$(KERNEL_SRC) $(PM4DECODE_SRC) $<

# The cross-check. rx550pm4_emit links the same ../kernel/rx550_pm4.c the module
# links and calls the same emitters, so what rx550pm4val parses is the driver's
# real output rather than a transcription of it. Neither program knows about the
# other's expectations: the generator has no test vectors and the validator has
# no access to amdgpu.
#
# The validator is optional. If it is not built, this target says so and does
# not quietly pass -- the same rule tools/pm4dw.c got wrong, and got right in
# the end.
VALIDATOR ?= ../../tools/rx550pm4val

.PHONY: crosscheck

$(VALIDATOR): ../../tools/rx550pm4val.c
	$(CC) $(CFLAGS) -o $@ $<

rx550pm4_emit: rx550pm4_emit.c $(KERNEL_SRC) $(KERNEL_HDRS)
	$(CC) $(CFLAGS) -I../kernel -o $@ $(KERNEL_SRC) $<

# Vectors chosen so each exercises a different shape, not just a different
# number: gfx with the PFP sync, compute without it, a PTEPDE alone, a multi-entry
# PTEPDE where count-1 is not zero, and the delivery path (coherence packet plus
# INDIRECT) which is the only shape where the two address spaces meet.
crosscheck: rx550pm4_emit $(VALIDATOR)
	@set -e; \
	for v in "gfx 3 0x900000 1" \
	         "gfx 8 0x12345000 1" \
	         "gfx 15 0x80000000 1" \
	         "compute 9 0x40000000 1" \
	         "compute 0 0x1000 1" \
	         "pteonly 0 0 4" \
	         "pteonly 0 0 1 8 0x103" \
	         "ring-gfx 3 0x900000 1" \
	         "ring-compute 9 0x40000000 1"; do \
		printf '  %-24s ' "$$v"; \
		./rx550pm4_emit $$v > /tmp/rx550pm4val.bin; \
		$(VALIDATOR) /tmp/rx550pm4val.bin > /tmp/rx550pm4val.out 2>&1 \
			&& printf 'CLEAN   ' || { rc=$$?; printf 'exit=%s ' "$$rc"; }; \
		grep -o 'RESULT:.*' /tmp/rx550pm4val.out | head -1; \
	done; \
	echo "  (0=CLEAN, 1=VIOLATION, 2=UNDECODED -- see tools/rx550pm4val.c)"

# make -C tests enters this directory, so ./tests/... would be wrong here. The
# tests take their fixture paths as argv[1] precisely so that the directory they
# run from stops mattering.
  # La lista de abajo la escribe $(TESTS) sola. La anterior no la usaba: declaraba
  # cinco tests, ejecutaba tres, y test_mmio y test_mc se compilaban en cada `make all`
  # sin que nadie los ejecutara nunca. Compilar un test no es correrlo, y un test que
  # se compila sin ejecutarse no puede fallar: es el peor sitio donde puede esconderse
  # un fallo, porque no hay nadie mirando. Los dos pasaban (27 checks y 0 fallos el
  # mmio), asi que no habia dano acumulado; lo que habia era un agujero.
  run: $(TESTS)
	@rc=0; \
	for t in $(TESTS); do \
		echo "--- $$t ---"; \
		case $$t in \
		  test_firmware_parse) ./$$t $(DATA)/polaris12_sdma.bin || rc=1 ;; \
		  *)                   ./$$t || rc=1 ;; \
		esac; \
		echo; \
	done; \
	if [ $$rc -ne 0 ]; then echo "  ALGO FALLO"; exit 1; fi;
	@echo "  los $(words $(TESTS)) tests de $(TESTS) han pasado"

  # El contraste del emisor PTEPDE contra el driver de referencia. Target propio, y NO
  # dentro de `run`, porque no es un test de este arbol: lee el corpus, y su respuesta
  # depende de amdgpu y no solo de nuestro codigo. Meterlo en `run` haria que una
  # mudanza del corpus pareciese un fallo del driver, que es una confusion cara.
  #
  # Lo que comprueba es la pieza que test_pm4.c declara NO tener: que nuestro emisor
  # coincide dword a dword con el del ASIC que corre. El conteo no lo delata --los dos
  # emiten 10-- y un intercambio de campos del mismo tipo tampoco.
  EMISOR ?= ../../08-ARQUITECTURA/tools/emisor.py

  emisor:
	@python3 $(EMISOR) --self | tail -1
	@python3 $(EMISOR)

  # Todo lo comprobable sin hardware. El orden es el que falla antes.
  verify: run emisor
	@echo "  verificado: $(words $(TESTS)) tests de userspace + contraste del emisor"

clean:
	rm -f $(TESTS) $(EMIT) $(DATA)/*.bin

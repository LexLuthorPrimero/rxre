# Makefile — rx550-pm4 GFX8 PM4 command layer.
# Userspace, CPU-only. Builds a static test binary; no kernel headers, no
# hardware, no allocation of GPU memory.

CC      ?= cc
CFLAGS  ?= -std=c11 -O2 -Wall -Wextra -Wpedantic -Werror \
           -Wshadow -Wconversion -Wsign-conversion -Wcast-qual -Wstrict-prototypes
LDFLAGS ?=

BIN     := pm4_test
SRC     := pm4.c
HDR     := pm4.h

# Tokens that must not appear in this component's CODE. Comments are stripped
# before scanning: a comment saying "NO doorbell" documents an absence and
# must not be counted as a doorbell.
FORBIDDEN := pci_enable_device pci_request_regions pci_iomap pci_set_master \
             ioremap iounmap readl writel __iomem dma_alloc_coherent \
             dma_map_single request_irq irqhandler MMIO mmio \
             doorbell DOORBELL wptr WPTR submit kick schedule execute \
             amdgpu_ amdgpu AMDGPU vmalloc kmalloc GFP_ copy_to_user \
             copy_from_user no_hw_access kprobe ring_kick

.PHONY: all test check-nohw clean

all: $(BIN)

$(BIN): $(SRC) $(HDR) pm4_test.c
	$(CC) $(CFLAGS) -o $@ $(SRC) pm4_test.c $(LDFLAGS)

test: $(BIN)
	./$(BIN)

# Static negative audit, independent of the C test.  A token count of 0 is the
# only passing outcome; any awk/grep error aborts instead of being swallowed.
check-nohw:
	@set -e; \
	strip=.stripped.tmp; \
	trap 'rm -f $$strip' EXIT; \
	$(CC) -fpreprocessed -dD -E -P $(SRC) $(HDR) > $$strip; \
	if [ ! -s $$strip ]; then echo "  AUDIT FAILED: strip produced no output"; exit 1; fi; \
	echo "  stripped code: $$(wc -l < $$strip) lines"; \
	fail=0; \
	for t in $(FORBIDDEN); do \
	  hits=$$(grep -o -w "$$t" $$strip | wc -l); \
	  if [ "$$hits" -ne 0 ]; then echo "  FOUND $$t x$$hits"; fail=1; fi; \
	done; \
	if [ "$$fail" -ne 0 ]; then echo "  AUDIT FAILED: hardware API present"; exit 1; fi; \
	echo "  clean: 0 hardware/submission API tokens in $(SRC) $(HDR)"

clean:
	rm -f $(BIN) .stripped.tmp

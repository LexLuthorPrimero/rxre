# Makefile — rx550-mem GFX8 address/buffer model.
# Userspace, CPU-only, pure data. No kernel headers, no hardware, no
# allocation. Deliberately does NOT link the PM4 component: the two share
# numbers, not code, so the contract between them is testable as a number.

CC      ?= cc
DEPFLAGS := -MMD -MP
CFLAGS  ?= -std=c11 -O2 -Wall -Wextra -Wpedantic -Werror \
           -Wshadow -Wconversion -Wsign-conversion -Wcast-qual -Wstrict-prototypes
LDFLAGS ?=

SRCS    := rx550_addr.c rx550_vis.c rx550_vm.c rx550_sub.c
HDRS    := rx550_addr.h rx550_vis.h rx550_vm.h rx550_sub.h
TESTS   := rx550_addr_test.c rx550_vis_test.c rx550_vm_test.c
PM4_DIR := ../rx550-pm4
BINS    := rx550_addr_test rx550_vis_test rx550_vm_test rx550_sub_test rx550_contract_test

FORBIDDEN := ioremap iounmap readl writel __iomem pci_ dma_ mmio MMIO \
             doorbell DOORBELL wptr WPTR kmalloc vmalloc GFP_ request_irq \
             kprobe no_hw_access pm4.h rx550_pm4_ drm_ amdgpu_ ttm

DEPS    := $(BINS:=.d)
-include $(DEPS)

.PHONY: all test check-nohw clean

all: $(BINS)

rx550_addr_test: rx550_addr.c rx550_addr.h rx550_addr_test.c
	$(CC) $(CFLAGS) $(DEPFLAGS) -o $@ rx550_addr.c rx550_addr_test.c $(LDFLAGS)

rx550_vis_test: rx550_vis.c rx550_vis.h rx550_addr.h rx550_vis_test.c
	$(CC) $(CFLAGS) $(DEPFLAGS) -o $@ rx550_vis.c rx550_vis_test.c $(LDFLAGS)

rx550_vm_test: rx550_vm.c rx550_vm.h rx550_addr.h rx550_vm_test.c
	$(CC) $(CFLAGS) $(DEPFLAGS) -o $@ rx550_vm.c rx550_vm_test.c $(LDFLAGS)

# rx550_sub validates a submission against the memory layer, so it links
# rx550_addr. That dependency is the point: the IB address cannot reach a
# submission without passing the buffer that declares its address space.
rx550_sub_test: rx550_sub.c rx550_sub.h rx550_addr.c rx550_addr.h rx550_sub_test.c
	$(CC) $(CFLAGS) $(DEPFLAGS) -o $@ rx550_sub.c rx550_addr.c rx550_sub_test.c $(LDFLAGS)

# The only target that compiles both components. It reads rx550-pm4 and never
# writes to it: PM4_DIR is an input path, not an output.
rx550_contract_test: rx550_addr.c rx550_vis.c rx550_vm.c rx550_sub.c \
                    $(wildcard $(PM4_DIR)/pm4.c) rx550_contract_test.c
	$(CC) $(CFLAGS) $(DEPFLAGS) -I$(PM4_DIR) -o $@ \
	    rx550_addr.c rx550_vis.c rx550_vm.c rx550_sub.c \
	    $(PM4_DIR)/pm4.c rx550_contract_test.c $(LDFLAGS)

test: $(BINS)
	./rx550_addr_test
	./rx550_vis_test
	./rx550_vm_test
	./rx550_sub_test
	./rx550_contract_test

# Negative audit over CODE (comments stripped).  A comment saying "no MMIO"
# documents an absence and is not an MMIO reference.
check-nohw:
	@set -e; \
	strip=.stripped.tmp; \
	trap 'rm -f $$strip' EXIT; \
	$(CC) -fpreprocessed -dD -E -P $(SRCS) $(HDRS) > $$strip; \
	if [ ! -s $$strip ]; then echo "  AUDIT FAILED: strip empty"; exit 1; fi; \
	fail=0; \
	for t in $(FORBIDDEN); do \
	  hits=$$(grep -o -w "$$t" $$strip | wc -l); \
	  if [ "$$hits" -ne 0 ]; then echo "  FOUND $$t x$$hits"; fail=1; fi; \
	done; \
	if [ "$$fail" -ne 0 ]; then echo "  AUDIT FAILED"; exit 1; fi; \
	echo "  clean: 0 hardware/submission/PM4-coupling tokens"

clean:
	rm -f $(BINS) .stripped.tmp $(DEPS)

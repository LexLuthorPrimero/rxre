# SPDX-License-Identifier: GPL-2.0
#
# Userspace tests for the rx550 driver.
#
# These compile and run entirely in userspace. None of them loads the module or
# touches hardware, which is what makes them runnable on a host that refuses to
# load rx550.ko at all (CONFIG_SECURITY_LOCKDOWN_LSM=y, unsigned modules
# rejected). That is a coverage limit, stated rather than hidden: a test that
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

TESTS := test_firmware_parse test_firmware_load test_pm4

# Kernel-side sources the userspace tests compile directly. The test then
# exercises the same object the module links, not a transcription of it: a
# packet the test validates is the packet the driver emits.
KERNEL_SRC := ../kernel/rx550_pm4.c

.PHONY: all run clean check-blob

all: $(TESTS)

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
test_pm4: test_pm4.c $(KERNEL_SRC)
	$(CC) $(CFLAGS) -I../kernel -o $@ $^

# make -C tests enters this directory, so ./tests/... would be wrong here. The
# tests take their fixture paths as argv[1] precisely so that the directory they
# run from stops mattering.
run: $(TESTS)
	@echo "--- test_firmware_parse ---"
	@./test_firmware_parse $(DATA)/polaris12_sdma.bin
	@echo
	@echo "--- test_firmware_load ---"
	@./test_firmware_load
	@echo
	@echo "--- test_pm4 ---"
	@./test_pm4

clean:
	rm -f $(TESTS) $(DATA)/*.bin

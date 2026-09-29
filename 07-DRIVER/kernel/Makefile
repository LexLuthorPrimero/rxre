# SPDX-License-Identifier: GPL-2.0
#
# Kbuild wrapper for the rx550 exclusive driver.
#
# Kbuild needs to be invoked from the kernel's build tree with M=$(PWD), so the
# real object rules live in scripts/Makefile.build and we only declare what to
# build. Calling `make` directly in this directory therefore recurses back into
# the kernel tree.
#
# NOTE on loading, not building: this host has CONFIG_MODULE_SIG_ALL=y and
# CONFIG_SECURITY_LOCKDOWN_LSM=y, and the signing key
# (CONFIG_MODULE_SIG_KEY="certs/signing_key.pem") is not present under /etc/pki.
# A module built here is unsigned, and lockdown rejects unsigned modules before
# the signature is even examined. So `make` succeeds and `insmod` will not. That
# is a policy question about the host, not a defect in this code; see
# kernel/README.md.

obj-m += rx550.o
rx550-objs := rx550_main.o

KERNELRELEASE ?= $(shell uname -r)
KERNELDIR    := /lib/modules/$(KERNELRELEASE)/build

.PHONY: all modules clean check-kernel check-config

all: modules

modules:
	$(MAKE) -C $(KERNELDIR) M=$(CURDIR) modules

clean:
	$(MAKE) -C $(KERNELDIR) M=$(CURDIR) clean

# Fails loudly if the kernel build tree is missing, rather than emitting a
# confusing "No rule to make target" from inside scripts/Makefile.build.
check-kernel:
	@test -d $(KERNELDIR) || { \
	  echo "ERROR: kernel build tree not found: $(KERNELDIR)"; \
	  exit 1; }
	@echo "  kernel build tree: $(KERNELDIR)"

# Reports the configs that decide whether a locally built module can be loaded.
# Read-only: this does not build, and it does not change the running system.
check-config:
	@echo "  kernel: $(KERNELRELEASE)"
	@conf=$(KERNELDIR)/include/config/auto.conf; \
	 test -f $$conf || { echo "  ERROR: no auto.conf, is the tree configured?"; exit 1; }; \
	 for c in CONFIG_MODVERSIONS CONFIG_MODULE_SIG_ALL CONFIG_SECURITY_LOCKDOWN_LSM; do \
	   v=$$(grep -E "^$$c=|^# $$c is not set" $$conf | head -1); \
	   printf '  %-34s %s\n' "$$c" "$${v:-<not present>}"; \
	 done; \
	 echo "  CONFIG_MODULE_SIG_KEY: $$(grep -E '^CONFIG_MODULE_SIG_KEY=' $$conf | cut -d= -f2-)"

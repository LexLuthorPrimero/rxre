# nhwa — build contra el kernel REALMENTE en ejecución.
#
# No se usa el árbol upstream 7.1.3 del proyecto (RESEARCH/kernelbuild):
# ese árbol da un offset de no_hw_access DISTINTO (374153 vs 381969) y su
# config no tiene CONFIG_DEBUG_INFO_BTF. Para el módulo del runtime sólo
# cuenta el kernel que se va a ejecutar.

KVER := $(shell uname -r)
KDIR := /lib/modules/$(KVER)/build
PWD  := $(shell pwd)

obj-m += nhwa.o

.PHONY: all clean verify-kdir

all: verify-kdir
	$(MAKE) -C $(KDIR) M=$(PWD) modules

verify-kdir:
	@test -d "$(KDIR)" || { \
		echo "ERROR: no existe $(KDIR)"; \
		echo "       kernel en ejecucion: $(KVER)"; \
		echo "       instalar kernel-devel o headers coincidentes"; \
		exit 1; }

clean:
	$(MAKE) -C $(KDIR) M=$(PWD) clean

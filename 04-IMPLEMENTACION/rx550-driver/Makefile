# rx550_target — build contra el kernel REALMENTE en ejecución.
#
# No se usa el árbol upstream del proyecto (RESEARCH/kernelbuild, 7.1.3): para
# el módulo del runtime sólo cuenta el kernel que se va a ejecutar, y sus
# cabeceras son la autoridad de la API.
#
# No compilar contra 07-DRIVER/: ese directorio está fuera de alcance.

KVER := $(shell uname -r)
KDIR := /lib/modules/$(KVER)/build
HERE := $(shell pwd)

# Un SOLO modulo. Declarar dos veces obj-m crearia dos .ko,  y el segundo no
# tendria MODULE_LICENSE() porque esa macro solo esta en el fichero que declara
# el modulo:  modpost lo rechaza con "missing MODULE_LICENSE()".
# MEDIDO 2026-10-04:  eso fue lo que paso al anadir rx550_vm_geom.o,  y el
# chequeo COB de test_static.sh dio VERDE igual,  porque comprueba que el .c
# este DECLARADO,  no que este declarado en la lista correcta.  La puerta que
# faltaba es COB-MODULOS,  y ahora esta en test_static.sh.
# independientes, y pci_resource.o se quejaria de no tener MODULE_LICENSE.
# El nombre del modulo COMPUESTO no puede coincidir con el de un fuente:
# kbuild lo interpretaria como modulo y no como objeto.  El nombre del
# driver dentro del codigo sigue siendo "rx550_target".
#
# rx550_mmio_access.o entra aqui porque su port bajo __KERNEL__ es viable
# (DRIVER.EXCLUSIVE.GPUVM.NODO_A_PORT_COMPATIBILITY = PORT_FEASIBLE).
# Esto es pertenencia al binario, NO ejecucion: el accessor sigue sin
# llamada productiva desde el probe, y el mapeo del BAR no existe.
obj-m := rx550_drv.o
rx550_drv-objs := rx550_target.o pci_resource.o rx550_mmio_access.o rx550_pdb0.o rx550_vmid0_gart.o rx550_vmid1_pgt.o rx550_submission.o rx550_gart_write.o rx550_dummy_page.o rx550_gart_seq.o rx550_gart_table.o rx550_vram_pool.o rx550_gart_boot.o rx550_gart_geom.o rx550_vm_geom.o

.PHONY: all modules test clean verify-kdir

all: modules test

modules: verify-kdir
	$(MAKE) -C $(KDIR) M=$(HERE) modules

# Los tests estáticos: ejecutan la regla de matching real (T1-T9) e inspeccionan
# el .ko y el fuente (T10-T14). No cargan el módulo ni tocan hardware.
test: modules
	@$(MAKE) -s -C tests run

verify-kdir:
	@test -d "$(KDIR)" || { \
		echo "ERROR: no existe $(KDIR)"; \
		echo "       kernel en ejecucion: $(KVER)"; \
		exit 1; }

clean:
	-$(MAKE) -C $(KDIR) M=$(HERE) clean
	-$(MAKE) -s -C tests clean

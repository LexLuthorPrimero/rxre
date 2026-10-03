# tests — T1-T14, sin cargar el módulo.
#
# test_target_match  se compila como userspace y EJECUTA target_match.h,
#                    la misma función que usa el driver.
# test_static.sh     compila ese test y luego inspecciona el .ko y el fuente.

HERE := $(shell pwd)
CC    ?= gcc
CFLAGS ?= -O2 -Wall -Wextra -Werror -I..

.PHONY: run clean

CORPUS=../../../RESEARCH/kernelbuild/linux-7.1.3/drivers/gpu/drm/amd/include/asic_reg/gca

GMC=../../../RESEARCH/kernelbuild/linux-7.1.3/drivers/gpu/drm/amd/include/asic_reg/gmc

AMDGPU=../../../RESEARCH/kernelbuild/linux-7.1.3/drivers/gpu/drm/amd/amdgpu

# test_mem queda FUERA de la cola: Q2 lo esta escribiendo otra sesion en este
# mismo workspace y su test_mem.c esta a medio escribir (no incluye target_mem.h
# y target_mem_host.h duplica sus typedefs). No se bloquea la suite propia con
# trabajo ajeno en vuelo, y no se tocan sus ficheros.
run: test_target_match test_resource test_regs test_vm test_fence test_submit test_mmio_access
	@./test_resource
	@./test_regs $(CORPUS)/gfx_8_0_d.h $(CORPUS)/gfx_8_1_d.h
	@./test_vm $(GMC)/gmc_8_2_sh_mask.h
	@./test_fence
	@./test_submit
	# La fuente primaria de Polaris12/GFX8 es gmc_8_1, y no gmc_8_2:
	#   gmc_v8_0.c:35-36  incluye gmc/gmc_8_1_d.h y gmc/gmc_8_1_sh_mask.h
	#   amdgpu_drv.c:2041  0x699F -> CHIP_POLARIS12
	#   vi.c:2110          CHIP_POLARIS12 -> gmc_v8_1_ip_block
	# Los dos mapas coinciden en los 16 registros, pero coincidir hoy no
	# obliga a que coincidan manana.  La linea 26, la de test_vm, sigue
	# con gmc_8_2:  es otro test y otro objetivo.
	@./test_mmio_access .. $(GMC)/gmc_8_1_d.h $(GMC)/gmc_8_1_sh_mask.h $(AMDGPU)/gmc_v8_0.c
	@./test_static.sh

test_target_match: test_target_match.c ../target_match.h
	$(CC) $(CFLAGS) -o test_resource test_resource.c ../target_resource.h
	$(CC) $(CFLAGS) -o $@ $<

# test_mmio_access  es el unico que ENLAZA codigo del driver:  el accessor,
# la geometria y el backing.  Sin esta regla, añadirlo a la cola de run lo
# haria fallar el build, porque no habria nada que ejecutar.
test_mmio_access: test_mmio_access.c ../rx550_mmio_access.c ../rx550_vmid1_pgt.c ../rx550_vmid1_pgt_backing.c
	$(CC) $(CFLAGS) -o $@ test_mmio_access.c ../rx550_mmio_access.c ../rx550_vmid1_pgt.c ../rx550_vmid1_pgt_backing.c

clean:
	rm -f test_target_match test_resource test_regs test_vm test_fence test_submit test_mmio_access

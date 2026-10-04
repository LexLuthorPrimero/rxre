# tests — la puerta de las suites en C de esta línea de driver.
#
# ALCANCE DE LA PUERTA, y por que cambió el 2026-10-03
#   Antes `run` ejecutaba 7 de las 16 suites que existen en este directorio.
#   Las otras 9 no estaban en ninguna regla: nadie las compilaba, nadie las
#   ejecutaba, y por eso nadie sabía si pasaban.  No es que estuvieran rotas:
#   es que no había puerta detrás de ellas, y eso es peor que un rojo.
#
#   MEDIDO el 2026-10-03 (workspace 06, AGENT-06 DRIVER/PERF):
#     16 test_*.c en el directorio
#     15 compilan con -O2 -Wall -Wextra -Werror  -> 2814 aserciones, todas en verde
#     1 no compila: test_mem, y es trabajo de otra sesion (ver abajo)
#   Las 15 se ejecutaron DOS veces con salida IDENTICA y rc=0.
#
#   El defecto que justifica el cambio no era hipotetico: rx550_gart_write.c
#   usaba RX550_GART_ENTRY_COUNT, una constante que ya no existe, y ese .c no
#   lo compilaba NADIE.  Un fichero de produccion que no compila y que no esta
#   en la cola de build es invisible por construccion.  Ver
#   06-INGENIERIA-INVERSA/findings/977-suite-gart-no-compila-y-no-era-un-maximo.md
#
# test_target_match  se compila como userspace y EJECUTA target_match.h,
#                    la misma funcion que usa el driver.
# test_static.sh     compila ese test y luego inspecciona el .ko y el fuente.

HERE := $(shell pwd)
CC    ?= gcc
CFLAGS ?= -O2 -Wall -Wextra -Werror -I..

PM4DIR ?= ../../rx550-pm4

.PHONY: run clean

CORPUS=../../../RESEARCH/kernelbuild/linux-7.1.3/drivers/gpu/drm/amd/include/asic_reg/gca

GMC=../../../RESEARCH/kernelbuild/linux-7.1.3/drivers/gpu/drm/amd/include/asic_reg/gmc

AMDGPU=../../../RESEARCH/kernelbuild/linux-7.1.3/drivers/gpu/drm/amd/amdgpu

# test_mem quedo FUERA de la cola por escrito, con motivo: se decia que su fuente
# estaba a medio escribir y no compilaba.  Motivo CADUCADO 2026-10-03.
#
#   MEDIDO entonces, y reproducido aqui: con el fuente tal como estaba,
#   gcc -O2 -Wall -Wextra -Werror daba 4 errores.  No era "trabajo de otra
#   sesion en vuelo": eran cuatro desacuerdos concretos, y ninguno dependia de
#   que otra sesion terminara nada.
#
#     1. test_mem.c declaraba sus propios u8/u32/u64, y target_mem_host.h tambien.
#     2. test_mem.c usaba los TM_* sin includir target_mem.h, que es donde estan.
#     3. target_mem_host.h hacia `typedef int bool`, y bool es palabra clave
#        desde C23, que es el estandar por defecto de este gcc 16.2.
#     4. El binario tests/test_mem que estaba en el arbol era de 2026-09-29 y
#        venia de otro fuente: ejecutaba y daba 72 PASS en verde sobre codigo
#        que ya no existia.  Un artefacto viejo consumido como evidencia.
#
#   Los tres primeros estan corregidos.  El cuarto no se "corrige": se evita,
#   metiendo test_mem en la cola, que es lo que faltaba.  Con el binario en la
#   cola, un fuente que no compile es un fallo de build, no un verde falso.
#   Ver 06-INGENIERIA-INVERSA/findings/1021-test-verde-sobre-fuente-que-no-compila.md
#
# `run` depende del .ko, y no solo por orden: test_static.sh audita el BINARIO
# con `nm -u`, no el fuente.  MEDIDO 2026-10-03: corrido con `make -s run` desde
# tests/ y el .ko era de antes del cambio, luego la mitad de enlace del audit
# leía un binario que ya no correspondia al fuente.  Una comprobación que
# inspecciona el estado que otro paso dejó, en vez del suyo, comprueba otra
# cosa (mismo defecto que el caso 206 de run-all.sh).
#
# El Makefile de arriba ya lo hacia bien (`test: modules`); este no.  Con la regla
# de abajo, el comando que documenta el hallazgo 977 —`cd tests && make -s run`—
# reconstruye el modulo antes de auditarlo.
KO := ../rx550_drv.ko

$(KO):
	$(MAKE) -C .. modules

run: $(KO) test_target_match test_resource test_regs test_vm test_fence test_submit \
     test_mmio_access test_block_size test_gart_write test_ib_bridge \
     test_ib_composer test_pdb0 test_submission test_vmid0_gart test_mem \
     test_ctxpt test_update_field test_dummy_page test_gart_seq \
     test_gart_apply \
     test_vmid1_pgt test_vmid1_pgt_backing
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
	@./test_block_size
	@./test_gart_write
	@./test_ib_bridge
	@./test_ib_composer
	@./test_pdb0
	@./test_submission
	@./test_mem
	@./test_ctxpt
	@./test_update_field
	@./test_dummy_page
	@./test_gart_seq
	@./test_gart_apply
	@./test_vmid0_gart
	@./test_vmid1_pgt
	@./test_vmid1_pgt_backing
	@./test_static.sh

# test_mem verifica el contrato de direcciones de target_mem.h, que es el unico
# lugar de todo el componente donde se comprueban los TM_*.  Sin esta regla el
# contrato de la geometria de memoria no lo comprobaba nadie.
test_mem: test_mem.c ../target_mem.h ../target_mem_host.h
	$(CC) $(CFLAGS) -o $@ test_mem.c

# test_ctxpt comprueba la REGLA que decide que registro de tabla de paginas
# corresponde a un VMID.  La tabla de mnemonicos verifica cada entrada por
# separado contra el header, y eso NO demuestra que esten en el orden correcto:
# la relacion entre ellas es lo que tiene el corte en 8, y no estaba escrita en
# ninguna parte del componente.  Ver finding 1025.
test_ctxpt: test_ctxpt.c ../rx550_mmio_access.c ../rx550_mmio_access.h
	$(CC) $(CFLAGS) -o $@ test_ctxpt.c ../rx550_mmio_access.c

# test_update_field comprueba la RMW por campo, que es como programa la
# referencia los 7 registros de control de gmc_v8_0_gart_enable().  ElAccessor
# no tenia forma de hacerlo: solo read32 y write32.  Ver finding 1028.
test_update_field: test_update_field.c ../rx550_mmio_access.c ../rx550_mmio_access.h
	$(CC) $(CFLAGS) -o $@ test_update_field.c ../rx550_mmio_access.c

# test_dummy_page comprueba la pagina de relleno de la GART.  Es el parametro que
# rx550_vmid0_regs_build() recibe y que NADA en el componente producia, con lo
# que la secuencia del contexto 0 no se podia completar.  Ver finding 1028.
test_dummy_page: test_dummy_page.c ../rx550_dummy_page.c ../rx550_dummy_page.h
	$(CC) $(CFLAGS) -o $@ test_dummy_page.c ../rx550_dummy_page.c

# test_gart_seq comprueba el PLAN de las 34 escrituras del GART.  Es la
# funcion mas critica del componente y la unica que produce un plan en vez de
# escribir:  un plan se puede comparar con gmc_v8_0.c:829-947 sin GPU delante.
# Ver findings 1028 y 1030.
test_gart_seq: test_gart_seq.c ../rx550_gart_seq.c ../rx550_mmio_access.c \
              ../rx550_gart_seq.h ../rx550_mmio_access.h
	$(CC) $(CFLAGS) -o $@ test_gart_seq.c ../rx550_gart_seq.c ../rx550_mmio_access.c

# test_gart_apply comprueba la ESCRITURA del plan sobre un mapa, y el reparto
# entre los 9 registros legibles y los 25 de solo escritura.  Ver finding 1031.
test_gart_apply: test_gart_apply.c ../rx550_gart_seq.c ../rx550_mmio_access.c \
                ../rx550_gart_seq.h ../rx550_mmio_access.h
	$(CC) $(CFLAGS) -o $@ test_gart_apply.c ../rx550_gart_seq.c ../rx550_mmio_access.c

test_target_match: test_target_match.c ../target_match.h
	$(CC) $(CFLAGS) -o test_resource test_resource.c ../target_resource.h
	$(CC) $(CFLAGS) -o $@ $<

# test_mmio_access  es el unico que ENLAZA codigo del driver:  el accessor,
# la geometria y el backing.  Sin esta regla, añadirlo a la cola de run lo
# haria fallar el build, porque no habria nada que ejecutar.
test_mmio_access: test_mmio_access.c ../rx550_mmio_access.c ../rx550_vmid1_pgt.c ../rx550_vmid1_pgt_backing.c
	$(CC) $(CFLAGS) -o $@ test_mmio_access.c ../rx550_mmio_access.c ../rx550_vmid1_pgt.c ../rx550_vmid1_pgt_backing.c

# Las siguientes enlazan tambien codigo del driver.  Los conjuntos de ficheros
# son MINIMOS, medidos quitando uno a uno hasta que el enlazador se queja: una
# regla que lista mas de lo necesario construye un binario distinto del que
# se midio, y entonces la puerta mide otra cosa.
test_block_size: test_block_size.c ../rx550_vmid1_pgt.c ../rx550_vmid1_pgt_backing.c ../rx550_mmio_access.c
	$(CC) $(CFLAGS) -o $@ test_block_size.c ../rx550_vmid1_pgt.c ../rx550_vmid1_pgt_backing.c ../rx550_mmio_access.c

test_gart_write: test_gart_write.c ../rx550_gart_write.c ../rx550_vmid0_gart.c
	$(CC) $(CFLAGS) -o $@ test_gart_write.c ../rx550_gart_write.c ../rx550_vmid0_gart.c

# pm4.h vive en OTRO proyecto de esta misma linea (04-IMPLEMENTACION/rx550-pm4/),
# no en el directorio del driver.  Por eso esta regla lleva -I aparte: sin el,
# los dos .c que lo incluyen fallan con "No existe el fichero".  MEDIDO: es la
# unica regla que necesita un -I que no sea "..".
test_ib_bridge: test_ib_bridge.c ../rx550_ib_bridge.c $(PM4DIR)/pm4.c $(PM4DIR)/pm4.h
	$(CC) $(CFLAGS) -I$(PM4DIR) -o $@ test_ib_bridge.c ../rx550_ib_bridge.c $(PM4DIR)/pm4.c

test_ib_composer: test_ib_composer.c ../rx550_ib_composer.c ../rx550_submission.c
	$(CC) $(CFLAGS) -o $@ test_ib_composer.c ../rx550_ib_composer.c ../rx550_submission.c

test_pdb0: test_pdb0.c ../rx550_pdb0.c
	$(CC) $(CFLAGS) -o $@ test_pdb0.c ../rx550_pdb0.c

test_submission: test_submission.c ../rx550_submission.c
	$(CC) $(CFLAGS) -o $@ test_submission.c ../rx550_submission.c

test_vmid0_gart: test_vmid0_gart.c ../rx550_vmid0_gart.c
	$(CC) $(CFLAGS) -o $@ test_vmid0_gart.c ../rx550_vmid0_gart.c

test_vmid1_pgt: test_vmid1_pgt.c ../rx550_vmid1_pgt.c
	$(CC) $(CFLAGS) -o $@ test_vmid1_pgt.c ../rx550_vmid1_pgt.c

test_vmid1_pgt_backing: test_vmid1_pgt_backing.c ../rx550_vmid1_pgt_backing.c ../rx550_vmid1_pgt.c
	$(CC) $(CFLAGS) -o $@ test_vmid1_pgt_backing.c ../rx550_vmid1_pgt_backing.c ../rx550_vmid1_pgt.c

clean:
	rm -f test_target_match test_resource test_regs test_vm test_fence \
	      test_submit test_mmio_access test_block_size test_gart_write \
	      test_ib_bridge test_ib_composer test_pdb0 test_submission \
	      test_vmid0_gart test_vmid1_pgt test_vmid1_pgt_backing
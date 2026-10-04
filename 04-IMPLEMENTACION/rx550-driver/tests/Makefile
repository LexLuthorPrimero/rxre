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

# ── CFLAGS: PARIDAD CON EL .ko EN LO QUE CAMBIA SEMANTICA ────────────────────
#
# MEDIDO 2026-10-04.  Este `CFLAGS` estaba en `-O2 -Wall -Wextra -Werror -I..`, y
# el .ko que corre en esta maquina lo compila el kernel 7.1.3-200.nobara.fc44
# con sus KBUILD_CFLAGS.  No es que "casi coincidieran": faltaban -std,
# -fno-strict-aliasing, -funsigned-char, -fno-jump-tables y
# -fstack-protector-strong, y de los 25 binarios de este directorio 16
# ENLAZAN codigo del driver (reglas test_ctxpt:125, test_update_field:131,
# test_dummy_page:137, test_gart_seq:144, test_gart_apply:150, test_gart_table:157,
# test_mmio_access:167, test_block_size:174, test_gart_write:177,
# test_ib_bridge:184, test_ib_composer:187, test_pdb0:190, test_submission:193,
# test_vmid0_gart:196, test_gart_geom:214, test_vmid1_pgt:217,
# test_vmid1_pgt_backing:220).  Esos 16 compilan las MISMAS lineas de C con
# opciones distintas de las del modulo, o sea que un test puede pasar con codigo
# que el .ko no tiene, o al reves.
#
# El caso que ya estaba Medido y documentado en el historial de esta cabecera
# (lineas 49-53, antes de este cambio) era `typedef int bool` en
# target_mem_host.h:30: es legal en C17, y `bool` es palabra clave desde C23,
# que es el estandar por defecto de este gcc 16.2.1.  MEDIDO ahora:
#     $ printf 'int main(void){return 0;}\n' | gcc -dM -E - | grep __STDC_VERSION__
#     #define __STDC_VERSION__ 202311L
# o sea C23 por defecto, sin pedirlo.  El -std=gnu11 de kbuild es lo que evita
# que eso aparezca.
#
# LOS CINCO flags de la linea de abajo son los que el gate de
# tests/test_static.sh (bloque "CFLAGS-PARITY") exige que coincidan con la
# linea real de savedcmd que kbuild escribio en .rx550_target.o.cmd, la misma
# que extrae tools/tu_compila.sh:41.  No son una preferencia de estilo: cada uno
# cambia que significa el codigo, y por eso si uno falta, el gate falla en vez de
# avisar.
#
#   -std=gnu11               fija el lenguaje.  Sin el, `bool` y otros cambios de
#                            C23 entran solos.
#   -fno-strict-aliasing     kbuild lo usa porque el kernel castea entre tipos
#                            incompatibles a proposito.  En el .ko esta activo; sin
#                            el en los tests, el compilador puede reordenar o
#                            fusionar accesos que en el modulo no puede.
#   -funsigned-char          `char` plano pasa a ser SIN signo.  Afecta a todo
#                            `char`, y el .ko lo tiene.
#   -fno-jump-tables         kbuild lo pasa porque una tabla de switch en un
#                            modulo grande cuesta I-cache sin ganar nada medido.
#   -fstack-protector-strong activa el canario de pila.  Ver la nota de -O de
#                            abajo: es justo el flag cuyo efecto depende de -O.
#
# MEDIDO 2026-10-04, los 25 binarios de este Makefile compilan con los cinco y
# con -Werror, y `make -s run` sigue en rc=0.  Si alguno dejara de compilar, el
# fallo es REAL y lo que se arregla es el fuente, nunca -Werror.
#
# DELIBERADAMENTE en UNA sola linea fisica, y no con continuaciones `\`: el gate
# la lee del Makefile para compararla con kbuild, y una linea logica partidas en
# dos es un parser mas que puede fallar en silencio.  Que sea larga no es un
# defecto; una puerta que no puede leer lo que dice es.
CFLAGS ?= -O2 -Wall -Wextra -Werror -I.. -std=gnu11 -fno-strict-aliasing -funsigned-char -fno-jump-tables -fstack-protector-strong

# ── POR QUE -O2 Y NO -O3, Y POR QUE NO SE "OPTIMIZA" ─────────────────────────
#
# kbuild usa -O3.  Estos tests usan -O2, y esa diferencia es INTENCIONAL y se
# queda.  Este comentario es la defensa; el gate "CFLAGS-PARITY" de
# tests/test_static.sh lo verifica y falla si desaparece.
#
# 1) -O3 es de MAS codigo, no de menos.  MEDIDO 2026-10-04 con los flags de
#    paridad de arriba, sobre los 13 .c del driver que compilan en userspace
#    (todos menos rx550_target.c y pci_resource.c, que piden cabeceras de
#    kernel), comparando la suma de .text con size -A:
#
#        -O2 -> 13309 B      -O3 -> 13803 B      +494 B  =  +3.71 %
#
#    Y sobre el subconjunto de los 10 que si entran en obj-m (Makefile:24):
#        -O2 ->  9773 B      -O3 -> 10267 B      +494 B  =  +5.05 %
#
#    "Optimizar" los tests con -O3 produciria un .text MAS grande.  Medido por
#    fichero, el -O3 solo toca 4 de los 13, y uno solo explica el 78 % del
#    aumento:
#        rx550_gart_seq.o     2983 -> 3367   +384
#        rx550_gart_table.o    269 ->  359    +90
#        rx550_mmio_access.o  1788 -> 1804    +16
#        rx550_gart_geom.o     398 ->  402     +4
#
# 2) -O3 cambia una MINORIA de funciones, pero las que cambia las cambia de
#    verdad.  MEDIDO con nm --print-size: 105 funciones definidas, 8 con tamano
#    distinto entre -O2 y -O3 (en el subconjunto de obj-m: 82 y 7).  No es una
#    transformacion uniforme que se pueda razonar de un vistazo.
#
# 3) El caso que mas importa: -O3 CAMBIA EL COMPORTAMIENTO OBSERVABLE de
#    -fstack-protector-strong, sin decir nada.  MEDIDO con nm -u sobre
#    rx550_mmio_access.c con los flags REALES de kbuild:
#        -O0 canario=si   -O1 canario=si   -O2 canario=si   -Os canario=si
#        -O3 canario=NO
#    El simbolo `__stack_chk_fail` esta en undefined a -O2 y desaparece a -O3:
#    -O3 inlinea la llamada y con ella desaparece la condicion que dispara el
#    canario.  Un binario de test que se deja de proteger sin que ningun warning
#    lo diga es un test que mide otra cosa, en silencio.
#
# En resumen: estos tests existen para DECIR SI el driver se comporta bien, no
# para ir rapidos.  -O2 es el nivel en el que el compilador no hace
# transformaciones que cambien la semántica observable, que es exactamente lo
# que un test tiene que dar por supuesto.
#
# NOTA DE TRAZABILIDAD (leela antes de "corregir" el dato de arriba).  El
# informe que encargo este cambio daba "+2.52 %" y "5 de ~35 funciones".  NO se
# reprodujo: en las dos bases aqui medidas sale +3.71 % y +5.05 %, con 8 de 105
# y 7 de 82 funciones.  La diferencia tiene que ser la base de medicion (que
# ficheros, y .text solo o tambien .rodata), no la direccion.  LO QUE SI
# REPRODUCE, y es lo que sostiene el argumento, es que -O3 produce MAS .text y
# que solo afecta a una minoria de funciones.  Se deja constancia en vez de
# escribir la cifra que no se ha podido medir aqui.

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
     test_gart_apply test_gart_table test_vram test_vram_pool test_gart_boot test_gart_geom test_vm_geom \
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
	@./test_gart_table
	@./test_vram
	@./test_vram_pool
	@./test_gart_boot
	@./test_gart_geom
	@./test_vm_geom
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

# test_gart_table comprueba la GEOMETRIA de la tabla de la GART (65536 entradas
# de 8 bytes = 512 KiB en VRAM) y el valor con el que arranca cada entrada.
# Ver finding 1032.
test_gart_table: test_gart_table.c ../rx550_gart_table.c ../rx550_gart_table.h
	$(CC) $(CFLAGS) -o $@ test_gart_table.c ../rx550_gart_table.c

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

# test_vram comprueba el CONTRATO de la frontera de VRAM (rx550_vram.h) y solo
# el contrato: no hay allocator todavia, rx550_vram.c no existe.  Existe porque
# el filtrorx550_vram_resource_valid() comprobaba tres cosas de las cinco que el
# contrato declara, y las tres que faltaban eran silenciosas: un allocator que
# miente en `alignment`, o que devuelve state=ABSENT con owner puesto, pasaba
# entero.  Se prueba el filtro DIRECTAMENTE y no a traves de rx550_pdb0.c:95,
# que colapsa todos los motivos a -1 y no los distingue.
test_vram: test_vram.c ../rx550_vram.h
	$(CC) $(CFLAGS) -o $@ test_vram.c

# test_gart_geom comprueba el PRODUCTOR de la geometria del GART, que hasta
# ahora no existia: rx550_gart_seq.c la CONSUME y no la produce.  Su vector
# principal es el GART que el driver de referencia IMPRIMIO en esta tarjeta
# (0xFF00000000 - 0xFF0FFFFFFF, 256 MiB), o sea un numero MEDIDO y no una
# expectativa inventada.  Sin GPU, sin MMIO, sin root.
# test_vram_pool comprueba el ALLOCATOR, que hasta hoy no existia.  Lo que
# mas comprueba no es la aritmetica sino las DOS clausulas del contrato de
# rx550_vram.h que decia cumplir y que ningun allocator habia implementado: el
# "si falla, NO ESCRIBE out" del alloc, y el "deja RELEASED" del free.
test_vram_pool: test_vram_pool.c ../rx550_vram_pool.c ../rx550_vram_pool.h \
                ../rx550_vram.h
	$(CC) $(CFLAGS) -o $@ test_vram_pool.c ../rx550_vram_pool.c

# test_gart_boot comprueba LA SECUENCIA COMPLETA:  reserva, rellenado,
# geometria, plan, apply y vaciado de TLB, EN ORDEN.  Hasta ahora cada pieza se
# probaba por separado y NINGUN test comprobaba que encadenaran bien, porque el
# orden no estaba escrito en ninguna parte:  un cambio de orden no rompia nada.
# Este test mira ademas lo que un test de piezas no puede mirar:  que el flush va
# DESPUES del apply, que la direccion GPU de la tabla es la que dio el pool, y que
# un fallo a mitad dice EN QUE paso se paro.
test_gart_boot: test_gart_boot.c ../rx550_gart_boot.c ../rx550_gart_boot.h \
                ../rx550_gart_seq.c ../rx550_mmio_access.c \
                ../rx550_gart_table.c ../rx550_vram_pool.c ../rx550_vm_geom.c
	$(CC) $(CFLAGS) -o $@ test_gart_boot.c ../rx550_gart_boot.c \
		../rx550_gart_seq.c ../rx550_mmio_access.c \
		../rx550_gart_table.c ../rx550_vram_pool.c ../rx550_vm_geom.c

test_gart_geom: test_gart_geom.c ../rx550_gart_geom.c ../rx550_gart_geom.h
	$(CC) $(CFLAGS) -o $@ test_gart_geom.c ../rx550_gart_geom.c

# test_vm_geom comprueba el PRODUCTOR de block_size, fragment_size, num_level y
# max_pfn.  Hasta que este modulo existio,  esos tres numeros no los rellenaba
# NINGUN codigo de produccion:  estaban escritos a mano en tres fixtures de
# test.  El caso que este test cierra de verdad no es el valor,  sino que el
# barrido de TODO el dominio legal de vm_size da block_size = 10 siempre:  eso
# prueba que el numero no depende de la RAM de la maquina,  aunque
# si_meminfo() este en el camino de calculo.
test_vm_geom: test_vm_geom.c ../rx550_vm_geom.c ../rx550_vm_geom.h ../rx550_vmid1_pgt.c
	$(CC) $(CFLAGS) -o $@ test_vm_geom.c ../rx550_vm_geom.c ../rx550_vmid1_pgt.c

test_vmid1_pgt: test_vmid1_pgt.c ../rx550_vmid1_pgt.c
	$(CC) $(CFLAGS) -o $@ test_vmid1_pgt.c ../rx550_vmid1_pgt.c

test_vmid1_pgt_backing: test_vmid1_pgt_backing.c ../rx550_vmid1_pgt_backing.c ../rx550_vmid1_pgt.c
	$(CC) $(CFLAGS) -o $@ test_vmid1_pgt_backing.c ../rx550_vmid1_pgt_backing.c ../rx550_vmid1_pgt.c

# `clean` estaba incompleto: MEDIDO 2026-10-04, no borraba test_mem, test_ctxpt,
# test_update_field, test_dummy_page, test_gart_seq, test_gart_apply,
# test_gart_table ni test_vram.  Un binario viejo de un fuente borrado es
# exactamente el fallo del hallazgo 1021, y la lista se mantiene ahora completa
# respecto a la cola de `run`.  Si se añade una suite a `run` y no aqui, el
# binario sobrevive al `make clean` y puede consumirse como evidencia.
clean:
	rm -f test_target_match test_resource test_regs test_vm test_fence \
	      test_submit test_mmio_access test_block_size test_gart_write \
	      test_ib_bridge test_ib_composer test_pdb0 test_submission \
	      test_vmid0_gart test_vmid1_pgt test_vmid1_pgt_backing \
	      test_mem test_ctxpt test_update_field test_dummy_page \
	      test_gart_seq test_gart_apply test_gart_table test_vram \
      test_gart_geom test_vram_pool test_gart_boot
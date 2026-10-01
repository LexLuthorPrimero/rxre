# gfx8vmgeom
#
# Modelo de la geometria GPUVM de GFX8/Polaris12, derivado del corpus.
#
# No escribe registros, no lee MMIO, no ejecuta codigo del driver. Es un
# calculo sobre el texto del arbol de referencia, con las constantes
# extraidas por anclas: si una cita del corpus es erronea, la herramienta
# falla en vez de devolver un numero plausible.

CC      ?= gcc
CFLAGS  ?= -std=c11 -O2 -Wall -Wextra -Wpedantic -Werror \
           -Wshadow -Wconversion -Wsign-conversion -Wstrict-prototypes
CPPFLAGS += -D_POSIX_C_SOURCE=200809L \
            -DGG_VERSION_CROSS_ROOT='"$(CROSS_ROOT)"'

# El corpus de este repo esta partido, y la herramienta lo toma explicito:
#
#   SRC_ROOT -> drivers/gpu/drm/amd/amdgpu, 7.1.3 PRISTINO
#   HDR_ROOT -> include/drm/amd_asic_type.h, que solo existe en kernelbuild
#
# kernelbuild esta instrumentado (RE-02-E1) y sus numeros de linea no son
# intercambiables. La herramienta exige por sha256 que la cabecera que usa sea
# la del tarball 7.1.3, de modo que la mezcla sea verificable y no una
# confianza ciega.
SRC_ROOT ?= ../../../RESEARCH/working/linux-7.1.3
HDR_ROOT ?= ../../../RESEARCH/kernelbuild/linux-7.1.3

# Verificacion cruzada: la rama que decide block_size debe ser la misma en
# 7.2.8, o el hallazgo seria un artefacto de version y no una propiedad del
# ASIC. Se deja customizable porque el arbol 7.2.8 puede no estar.
CROSS_ROOT ?= ../../../rx550-upstream-7.2.8/linux-7.2.8

OBJS = gfx8vmgeom.o gfx8vmgeom_model.o gfx8vmgeom_test.o
BIN  = gfx8vmgeom

.PHONY: all test check-corpus check-noa8 report clean help

all: $(BIN)

$(BIN): $(OBJS)
	$(CC) $(CFLAGS) -o $@ $(OBJS)

%.o: %.c gfx8vmgeom.h
	$(CC) $(CFLAGS) $(CPPFLAGS) -c -o $@ $<

# La cabecera del path es un parametro del Makefile, luego tocarlo exige
# recompilar: sin esto un cambio en CROSS_ROOT no tendria efecto.
$(OBJS): Makefile

# El target por defecto es el test: una herramienta que no se ejecuta no
# aporta nada, y un binario sin ejecutar en el arbol es exactamente el
# fallo que el protocolo de este repo ya registro dos veces.
test: $(BIN)
	./$(BIN) $(SRC_ROOT) $(HDR_ROOT)

# Correr tambien contra kernelbuild. Sirve para ver que la instrumentacion
# no cambia la geometria: si lo hiciera, seria un hallazgo, no un ruido.
check-corpus: $(BIN)
	@echo "--- fuentes pristine (working) + cabecera verificada ---"
	@./$(BIN) ../../../RESEARCH/working/linux-7.1.3 \
	          ../../../RESEARCH/kernelbuild/linux-7.1.3 | tail -22
	@echo "--- TODO desde kernelbuild (instrumentado) ---"
	@./$(BIN) ../../../RESEARCH/kernelbuild/linux-7.1.3 \
	          ../../../RESEARCH/kernelbuild/linux-7.1.3 | tail -22

# El informe sin los controles negativos, para pegar en un documento.
report: $(BIN)
	@./$(BIN) $(SRC_ROOT) $(HDR_ROOT) | sed -n '/^== informe ==/,/discrepancias/p'

# Estructura de guards del propio repositorio: comprobar que la herramienta
# no ha sido ampliada para leer registros ni llamar al driver.
check-noa8: $(BIN)
	@echo "--- tokens de hardware que no deben aparecer ---"
	@if grep -nE '\b(ioremap|writel|readl|pci_enable_device|pci_request_regions|request_irq|dma_[a-z_]+)\b' \
	     gfx8vmgeom.c gfx8vmgeom_model.c gfx8vmgeom.h; then \
	   echo "RESULT: FALLO -- la herramienta toco hardware"; exit 1; \
	 else echo "  0 ocurrencias: OK"; fi
	@echo "--- el binario no debe importar nada de kernel ---"
	@if nm -u $(BIN) 2>/dev/null | grep -qE '\b(ioremap|writel|readl)\b'; then \
	   echo "RESULT: FALLO -- simbolos de hardware en el binario"; exit 1; \
	 else echo "  0 simbolos: OK"; fi
	@echo "RESULT: OK"

clean:
	rm -f $(BIN) $(OBJS)

help:
	@echo "make test        -- test + controles negativos (default)"
	@echo "make check-corpus -- compara pristine vs instrumentado"
	@echo "make report      -- solo el informe"
	@echo "make check-noa8  -- guardas de no-hardware"
	@echo "make clean"
# pteflags
#
# Censo de los productores de flags de PTE alcanzables en GFX8/Polaris12.
#
# No escribe registros, no lee MMIO, no ejecuta codigo del driver. Es un
# analisis estatico: lee fuentes y preprocesa unidades de traduccion.

CC      ?= gcc
CFLAGS  ?= -std=c11 -O2 -Wall -Wextra -Wpedantic -Werror \
           -Wshadow -Wconversion -Wsign-conversion -Wstrict-prototypes
# _DEFAULT_SOURCE es necesario para realpath(); con solo
# _POSIX_C_SOURCE se declara implicitamente y -Werror lo para.
CPPFLAGS += -D_POSIX_C_SOURCE=200809L -D_DEFAULT_SOURCE

# kernelbuild, no working: el preprocesador necesita include/uapi/drm y
# drivers/gpu/drm/scheduler, que en working no estan. Y kernelbuild es el
# unico con el .cmd del build, que es de donde salen los -I reales.
ROOT ?= ../../../RESEARCH/kernelbuild/linux-7.1.3

OBJS = pteflags_util.o pteflags_scan.o pteflags_census.o pteflags_test.o
BIN  = pteflags

.PHONY: all test check-noa8 clean help

all: $(BIN)

$(BIN): $(OBJS)
	$(CC) $(CFLAGS) -o $@ $(OBJS)

%.o: %.c pteflags.h
	$(CC) $(CFLAGS) $(CPPFLAGS) -DPF_ROOT='"$(ROOT)"' -c -o $@ $<

$(OBJS): Makefile

test: $(BIN)
	./$(BIN) $(ROOT)

# Guardas: la herramienta no debe haber sido ampliada hacia hardware ni hacia
# el uapi. Se audita el binario, no solo el fuente.
check-noa8: $(BIN)
	@echo "--- tokens de hardware que no deben aparecer ---"
	@if grep -nE '\b(ioremap|writel|readl|pci_enable_device|pci_request_regions|request_irq|dma_[a-z_]+)\b' \
	     pteflags_*.c pteflags.h; then \
	   echo "RESULT: FALLO -- toco hardware"; exit 1; \
	 else echo "  0 ocurrencias: OK"; fi
	@echo "--- el binario no debe importar nada de kernel ---"
	@if nm -u $(BIN) 2>/dev/null | grep -qE '\b(ioremap|writel|readl)\b'; then \
	   echo "RESULT: FALLO -- simbolos de hardware"; exit 1; \
	 else echo "  0 simbolos: OK"; fi
	@echo "RESULT: OK"

clean:
	rm -f $(BIN) $(OBJS)

help:
	@echo "make test        -- censo + controles negativos (default)"
	@echo "make check-noa8  -- guardas de no-hardware"
	@echo "make clean"
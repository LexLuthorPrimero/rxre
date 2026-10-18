# SPDX-License-Identifier: GPL-2.0
# Makefile — build de la reimplementacion C.
# Solo C (seccion 6 del AGENTS). Sin dependencias
# de renderizado ni audio: el nucleo es testeable solo.
CC ?= gcc
CFLAGS ?= -std=c99 -Wall -Wextra -Werror -O2

SRC = src/rxre_swf.c src/rxre_swf_constants.c
HDR = src/rxre_swf.h

.PHONY: all test test-disasm test-all clean run slice

all: bin/rxre_swf_demo bin/test_combat

bin/rxre_swf_demo: src/main.c $(SRC) $(HDR)
	@mkdir -p bin
	$(CC) $(CFLAGS) -Isrc -o $@ src/main.c $(SRC)

bin/test_combat: tests/test_combat.c $(SRC) $(HDR)
	@mkdir -p bin
	$(CC) $(CFLAGS) -Isrc -o $@ tests/test_combat.c $(SRC)

# Vertical slice jugable (ncurses): demuestra las
# mecánicas recuperadas end-to-end.
bin/slice: src/slice.c $(SRC) $(HDR)
	@mkdir -p bin
	$(CC) $(CFLAGS) -Isrc -o $@ src/slice.c $(SRC) -lncurses

run: bin/rxre_swf_demo
	./bin/rxre_swf_demo

# Ejecutar el slice jugable
slice: bin/slice
	./bin/slice

# Tests de la simulacion en C (flujo de combate)
test: bin/test_combat
	./bin/test_combat

# Test de regresion del desensamblador AVM1 (tool validation)
test-disasm:
	PYTHONPATH=tools python3 -B tests/test_disasm.py

# Todos los tests
test-all: test test-disasm

clean:
	rm -rf bin

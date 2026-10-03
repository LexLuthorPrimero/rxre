/* SPDX-License-Identifier: GPL-2.0 */
/*
 * test_mem.c — Q2 MEMORY_OBJECT: verificacion del contrato de direcciones.
 *
 * UNA SOLA PREGUNTA:
 *   ¿Las funciones de target_mem.h cumplen el contrato que declaran?
 *
 * Esto NO prueba que Polaris12 obedezca.  Demuestra que las funciones internas
 * son coherentes con la geometria declarada, y que esa geometria esta
 * fundamentada en el corpus.  La obediencia es RUNTIME_REQUIRED.
 *
 * Compila fuera del arbol del kernel: no usa nada que no sea una Cabecera.
 */
#include <stdio.h>
#include <stdbool.h>
#include <stdint.h>

typedef uint8_t  u8;
typedef uint32_t u32;
typedef uint64_t u64;

/* El kernel trae <linux/types.h>.  En userspace se sustituye. */
#include "target_mem_host.h"

static int pass, fail;

static void ok(const char *t) { printf("  PASS  %s\n", t); pass++; }
static void ko(const char *t) { printf("  FAIL  %s\n", t); fail++; }

#define CHECK(cond, name) do { if (cond) ok(name); else ko(name); } while (0)

int main(void)
{
	printf("test_mem — contrato de direcciones Q2\n\n");

	/* ── GEOMETRIA ──────────────────────────────────────────────────── */
	CHECK(TM_PAGE_SIZE == 4096, "pagina de 4 KiB");
	CHECK(TM_LEVEL_ENTRIES == 512, "512 entradas por nivel");
	CHECK(TM_LEVEL_ENTRIES * TM_ENTRY_SIZE == TM_PAGE_SIZE,
	      "una tabla de nivel cabe exactamente en una pagina");
	CHECK(TM_NR_DIR_LEVELS == 1, "GFX8: un nivel de directorio + PTB");
	CHECK(TM_VA_BITS == 30, "GPUVA de 30 bits");
	CHECK(TM_VA_SIZE == 1024ull * 1024 * 1024, "1 GiB de VA");
	CHECK(((TM_PN_MASK + 1) << TM_PAGE_SHIFT) == (1ull << TM_PA_BITS),
	      "PN 28 bits << 12 == PA de 40 bits");

	/* Las dos formulas independientes de Q1 tienen que coincidir. */
	CHECK(TM_VA_SIZE == (1ull << (TM_PA_BITS - 30)),
	      "VA y PA coherentes entre si (Q1, dos caminos)");

	/* ── TRADUCCION DE DIRECCIONES ──────────────────────────────────── */
	CHECK(tm_va_to_pn(0x00000000ull) == 0, "VA 0 -> PN 0");
	CHECK(tm_va_to_pn(0x00001000ull) == 1, "VA 4 KiB -> PN 1");
	CHECK(tm_va_to_pn(0x12345000ull) == 0x12345, "VN 0x12345000 -> PN 0x12345");

	CHECK(tm_ptb_index(0x00000000ull) == 0, "PTB index de VA baja");
	CHECK(tm_ptb_index(0x00001000ull) == 1, "PTB index avanza por pagina");
	CHECK(tm_ptb_index(0x000ff000ull) == 0x0ff, "PTB index dentro de la tabla");
	CHECK(tm_ptb_index(0x00100000ull) == 0, "PTB index se reinicia tras 2 MiB");
	CHECK(tm_ptb_index(0x00101000ull) == 1, "PTB index correcto tras 2 MiB");

	/* 2 MiB = 512 paginas = exactamente una PTB */
	CHECK((1ull << (TM_LEVEL_BITS + TM_PAGE_SHIFT)) == 2ull * 1024 * 1024,
	      "una PTB cubre 2 MiB");

	/* El indice de PTB SIEMPRE cabe en 9 bits. */
	{
		bool okrange = true;
		for (u64 va = 0; va < TM_VA_SIZE; va += TM_PAGE_SIZE) {
			if (tm_ptb_index(va) >= TM_LEVEL_ENTRIES) { okrange = false; break; }
			if (tm_level_index(va, 0) >= TM_LEVEL_ENTRIES) { okrange = false; break; }
			if (tm_level_index(va, 1) >= TM_LEVEL_ENTRIES) { okrange = false; break; }
		}
		CHECK(okrange, "todo el rango de VA cabe en 9 bits por nivel");
	}

	/* ── PTE ────────────────────────────────────────────────────────── */
	{
		u64 pa = 0x0000ABCDE000ull;
		u64 e = tm_pte_make(pa, true, true, false);

		CHECK(tm_entry_pa(e) == pa, "PTE conserva la direccion fisica");
		CHECK(tm_pte_is_valid(e), "PTE marcado valido");
		CHECK(tm_pte_is_leaf(e), "PTE marcado hoja (bit 54)");
		CHECK(tm_pde_is_leaf(e), "la marca de hoja la ve tambien la vista PDE");
		CHECK(tm_pte_is_readable(e), "PTE legible");
		CHECK(tm_pte_is_writeable(e), "PTE escribible");
		CHECK(!tm_pte_is_exec(e), "PTE no ejecutable");
	}

	/* Los permisos son independientes. */
	CHECK(tm_pte_is_readable(tm_pte_make(0, true, false, false))
	      && !tm_pte_is_writeable(tm_pte_make(0, true, false, false)),
	      "lectura sin escritura");
	CHECK(!tm_pte_is_readable(tm_pte_make(0, false, true, false))
	      && tm_pte_is_writeable(tm_pte_make(0, false, true, false)),
	      "escritura sin lectura");
	CHECK(tm_pte_is_exec(tm_pte_make(0, false, false, true)),
	      "ejecutable sin lectura ni escritura");
	CHECK(!tm_pte_is_readable(tm_pte_make(0, false, false, false)),
	      "sin permisos no hay lectura");

	/* El bit de hoja no se confunde con la direccion. */
	CHECK((TM_PDE_LEAF & TM_ADDR_MASK) == 0,
	      "la marca de hoja esta fuera del campo de direccion");
	CHECK((TM_PTE_VALID & TM_ADDR_MASK) == 0,
	      "el bit de validez esta fuera del campo de direccion");

	/* ── PDE ────────────────────────────────────────────────────────── */
	{
		u64 next = 0x000012340000ull;
		u64 d = tm_pde_make(next);

		CHECK(tm_entry_pa(d) == next, "PDE conserva la direccion de la tabla");
		CHECK(tm_pde_is_valid(d), "PDE marcado valido");
		CHECK(!tm_pde_is_leaf(d), "PDE NO lleva marca de hoja");
	}

	/* ── VA RESERVADA ───────────────────────────────────────────────── */
	CHECK(TM_VA_USER_END > TM_VA_USER_START, "queda rango de VA asignable");
	CHECK(TM_VA_USER_END <= TM_VA_SIZE, "el rango asignable no pasa del tope");
	CHECK(TM_VA_USER_START == (1ull << 16), "reservado inferior de 64 KiB");
	{
		u64 reserved = TM_VA_SIZE - (TM_VA_USER_END - TM_VA_USER_START);
		CHECK(reserved == TM_RESERVED_TOTAL,
		      "lo reservado arriba coincide con la suma de regiones");
	}

	printf("\n  %d pass, %d fail\n", pass, fail);
	if (fail) { printf("  CONTRATO: INCUMPLIDO\n"); return 1; }
	printf("  CONTRATO: SATISFECHO\n");
	return 0;
}

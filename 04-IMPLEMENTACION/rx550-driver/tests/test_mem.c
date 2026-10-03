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

/* target_mem.h es la unica include necesaria:
 *   - en userspace arrastra target_mem_host.h, que aporta u8/u32/u64
 *   - y define los TM_*, que son justo lo que este test verifica.
 *
 * Antes este fichero declaraba sus propios typedefs y NUNCA includia
 * target_mem.h.  Con las dos cosas a la vez el fuente no compilaba: los
 * typedefs chocaban con los de target_mem_host.h, y los TM_* no existian.
 * MEDIDO 2026-10-03: gcc -O2 -Wall -Wextra -Werror daba 4 errores.
 *
 * El binario tests/test_mem que habia en el arbol estaba fechado 2026-09-29
 * y venia de otro fuente: ejecutaba y daba 72 PASS en verde sobre codigo que
 * ya no existe.  Ver 06-INGENIERIA-INVERSA/findings/1021-test-verde-sobre-fuente-que-no-compila.md
 */
#include "target_mem.h"

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

	/* La asercion que aqui estaba:  TM_VA_SIZE == (1ull << (TM_PA_BITS - 30))
	 *
	 *   NO se corrige: se retira, y queda escrito por que.
	 *
	 *   La igualdad no puedezeni satisfied para ningun par de valores.  Por
	 *   definicion TM_VA_SIZE == 1 << TM_VA_BITS == 2^30.  El lado derecho es
	 *   2^(TM_PA_BITS - 30), y para que los dos coincidan haria falta
	 *   TM_PA_BITS == 60.  GFX8 tiene 40 bits de direccion fisica
	 *   (gmc_v8_0.c:1127, amdgpu_vm_adjust_size(..., max_bits=40)).
	 *
	 *   No es un valor mal puesto: es una RELACION QUE NO EXISTE.  El espacio
	 *   de VA y el de PA son magnitudes independientes, y ningun ASIC obliga a
	 *   que uno sea funcion del otro.  La unica asercion con sentido aqui es la
	 *   de arriba: que los 28 bits de PN, desplazados 12, den los 40 de PA.
	 *
	 *   Dejarla puesta, "arreglandola" con una formula inventada, seria fabricar
	 *   una coherencia que el hardware no impone.  Ver finding 314. */

	/* ── TRADUCCION DE DIRECCIONES ──────────────────────────────────── */
	CHECK(tm_va_to_pn(0x00000000ull) == 0, "VA 0 -> PN 0");
	CHECK(tm_va_to_pn(0x00001000ull) == 1, "VA 4 KiB -> PN 1");
	CHECK(tm_va_to_pn(0x12345000ull) == 0x12345, "VN 0x12345000 -> PN 0x12345");

	CHECK(tm_ptb_index(0x00000000ull) == 0, "PTB index de VA baja");
	CHECK(tm_ptb_index(0x00001000ull) == 1, "PTB index avanza por pagina");
	CHECK(tm_ptb_index(0x000ff000ull) == 0x0ff, "PTB index dentro de la tabla");

	/* El reinicio ocurre a los 512 indices, NO a los 256.
	 *
	 *   El valor que estaba aqui, 0x00100000, es 1 MiB, no 2 MiB.  A 1 MiB el
	 *   indice vale (0x100 >> 0) & 511 == 256, que es lo correcto, y el test
	 *   pedia 0: la asercion estaba mal, no la funcion.
	 *
	 *   El corpus lo dice sin interpretacion.  amdgpu_vm_pt.c:191:
	 *       idx = (cursor->pfn >> shift) & mask;
	 *   y en el nivel PTB shift es TM_PAGE_SHIFT (12) y mask es 511.  El indice
	 *   se envuelve cuando pfn llega a 512, es decir a los 2 MiB.
	 */
	CHECK(tm_ptb_index(0x00100000ull) == 256, "PTB index a 1 MiB = 256, aun sin reinicio");
	CHECK(tm_ptb_index(0x00200000ull) == 0,   "PTB index se reinicia a los 2 MiB");
	CHECK(tm_ptb_index(0x00201000ull) == 1,   "PTB index correcto tras 2 MiB");

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

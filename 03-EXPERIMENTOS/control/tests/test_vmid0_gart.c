/* SPDX-License-Identifier: GPL-2.0 */
/*
 * test_vmid0_gart.c — seis tests discriminantes, sin hardware.
 *
 * Que se prueba:
 *   Que la traduccion GPUVA -> indice use PAGINAS y no bytes.
 *   Que la base de la tabla venga de VRAM y no de una PA de sistema.
 *   Que profundidad distinta de 0 la rechace el constructor.
 *   Que los dos espacios no se puedan confundir.
 *   Que un indice fuera de tabla se rechace y no se trunque.
 *   Que una PA desalineada se rechace y no se enmascare.
 *
 * Que NO se prueba:
 *   Que el hardware acepte nada.  Nada aqui escribe un registro.
 */
#include "rx550_vmid0_gart.h"

#include <stdio.h>
#include <string.h>

static int pass, fail;

static void ok(const char *t)
{
	printf("  PASS  %s\n", t);
	pass++;
}

static void ko(const char *t)
{
	printf("  FAIL  %s\n", t);
	fail++;
}

#define CHECK(c, n) do { if (c) ok(n); else ko(n); } while (0)

int main(void)
{
	struct rx550_gart_aperture ap;
	struct rx550_gart_offset_bytes off;
	struct rx550_gart_pte_index idx;
	struct rx550_system_pa pa;
	struct rx550_vmid0_config cfg;
	struct rx550_vmid0_regs regs;
	struct rx550_gart_gpu_pfn base;
	struct rx550_pfn dummy;
	uint64_t entry;

	printf("test_vmid0_gart — GFX8 VMID0, una tabla\n\n");

	/* ── geometria declarada ─────────────────────────────────────── */
	/* 256 MiB es DEFAULT_OBSERVED_IN_REFERENCE_DRIVER, no un hecho de
	 * esta placa: se comprueba como POLICIA de admision, no como
	 * capacidad.  El valor real del GART es DEFERRED_RUNTIME. */
	CHECK(RX550_GART_SIZE_MAX == (UINT64_C(256) << 20), "tope de admision");
	CHECK(RX550_GART_PTE_SIZE == 8, "entrada de 8 bytes");
	CHECK(RX550_GART_PAGE_SIZE == 4096, "pagina de 4 KiB");

	CHECK(rx550_gart_aperture_init(&ap, 0, RX550_GART_SIZE_MAX) == 0,
	      "apertura en 0 (DESIGN_CHOICE)");
	CHECK(ap.end == UINT64_C(0x0FFFFFFF), "end = start + size - 1");
	CHECK(ap.entries == ap.size / RX550_GART_PAGE_SIZE,
	      "entries se DERIVA de size, no es una constante global");
	CHECK(ap.entries == 65536, "65536 entradas con la apertura de 256 MiB");
	CHECK(rx550_gart_aperture_init(&ap, UINT64_C(1) << 32,
				      RX550_GART_SIZE_MAX) == 0,
	      "apertura alineada a 4 GiB");
	CHECK(rx550_gart_aperture_init(&ap, 0x1000, RX550_GART_SIZE_MAX) != 0,
	      "apertura NO alineada a 4 GiB rechazada");
	/* Una apertura que no es multiplo de la pagina deja una entrada
	 * parcial; se rechaza para que entries sea exacto. */
	CHECK(rx550_gart_aperture_init(&ap, 0, RX550_GART_PAGE_SIZE + 1) != 0,
	      "apertura no multiplo de la pagina rechazada");
	(void)rx550_gart_aperture_init(&ap, 0, RX550_GART_SIZE_MAX);

	/* ── 1. GPUVA bytes vs pagina ────────────────────────────────── */
	/* GPUVA 0x3000 con gart_start=0 son 12288 bytes.  Como indice de
	 * pagina son 3.  Un calculo que tratara los bytes como indice
	 * daria 12288, que esta dentro de la tabla y apuntando a la entrada
	 * equivoca sin producir ningun error. */
	{
		struct rx550_gpuva v = rx550_gpuva_make(0x3000);

		CHECK(rx550_gart_offset_of(v, &ap, &off) == 0, "1. offset calculado");
		CHECK(off.bytes == 0x3000, "1. offset en BYTES = 0x3000");
		CHECK(rx550_gart_index_of(&ap, off, &idx) == 0, "1. indice calculado");
		CHECK(idx.index == 3, "1. indice en PAGINAS = 3, no 12288");
		CHECK(idx.index != off.bytes, "1. bytes e indice NO coinciden");
	}
	/* El error por mutacion: 12288 cabe en una tabla de 65536 entradas,
	 * asi que se aceptaria en silencio.  Este test es el que lo delata. */
	CHECK(UINT64_C(0x3000) >> RX550_GART_PAGE_SHIFT < ap.entries,
	      "1. el error seria SILENCIOSO: cabe en la tabla");

	/* ── 2. BASE: >>12 obligatorio ───────────────────────────────── */
	{
		struct rx550_vram_offset vo = rx550_vram_off(0x1000);

		CHECK(rx550_vmid0_base_from_vram(vo, &base) == 0, "2. base construida");
		CHECK(base.value == 1, "2. 0x1000 >> 12 = 1");
		CHECK(base.value != vo.bytes, "2. base NO es el offset en bytes");
	}
	{
		/* 0x100000000 es representable en el registro solo tras el
		 * >>12.  Sin el, 2^32 no cabe en 32 bits. */
		struct rx550_vram_offset vo = rx550_vram_off(UINT64_C(0x100000000));

		CHECK(rx550_vmid0_base_from_vram(vo, &base) == 0,
		      "2. offset 2^32 representable CON >>12");
		CHECK(base.value == UINT64_C(0x100000), "2. y vale 2^20");
	}
	{
		struct rx550_vram_offset vo = rx550_vram_off(UINT64_C(0xFFFFFFFFFFFF000));

		CHECK(rx550_vmid0_base_from_vram(vo, &base) != 0,
		      "2. offset que no cabe tras >>12 rechazado, no truncado");
		CHECK(base.value == 0, "2. y la salida quedo a cero");
	}

	/* ── 3. PAGE_TABLE_DEPTH ────────────────────────────────────── */
	CHECK(rx550_vmid0_config_build(&cfg) == 0, "3. config VMID0 construida");
	CHECK(cfg.page_table_depth == 0, "3. profundidad 0");
	CHECK(cfg.enable_context == 1, "3. ENABLE_CONTEXT = 1");
	CHECK(cfg.range_pf_default == 1, "3. RANGE_PF_DEFAULT = 1");
	/* Si se imitara el codigo de dos niveles, aquiDepth = 1 y el
	 * contexto 0 buscaria un nivel superior que no existe. */
	{
		struct rx550_vmid0_config bad = cfg;

		bad.page_table_depth = 1;
		CHECK(rx550_vmid0_regs_build(&regs, &bad, base, 0, ap.end, pa) != 0,
		      "3. regs_build rechaza profundidad distinta de 0");
	}
	{
		struct rx550_vmid0_config bad = cfg;

		bad.page_table_depth = 3;
		CHECK(rx550_vmid0_regs_build(&regs, &bad, base, 0, ap.end, pa) != 0,
		      "3. y tambien profundidad 3");
	}

	/* ── 4. VRAM offset vs SYSTEM_PA ─────────────────────────────── */
	/* BASE sale de VRAM; FAULT_DEFAULT sale de una PA de sistema.
	 * Los dos van a registros de 32 bits con el mismo >>12.  La
	 * separacion es de tipos, no de valores: ninguna cantidad que
	 *pa quepa en uno deja de caber en el otro. */
	pa.bytes = UINT64_C(0x2000000);
	CHECK(rx550_vmid0_fault_from_pa(pa, &dummy) == 0, "4. dummy PFN construido");
	CHECK(dummy.value == 0x2000, "4. 0x2000000 >> 12 = 0x2000");
	CHECK(rx550_vmid0_base_from_vram(rx550_vram_off(0x2000000), &base) == 0,
	      "4. el mismo numero como offset de VRAM tambien vale");
	CHECK(base.value == dummy.value,
	      "4. MISMO VALOR, DISTINTO TIPO: por eso los wrappers existen");
	/* Y aun asi, la ruta de codificacion es distinta: base_from_vram
	 * toma vram_offset, fault_from_pa toma system_pa.  Que coincidan
	 * es una coincidencia de numeros, no una via compartida. */

	/* ── 5. indice fuera de tabla ───────────────────────────────── */
	{
		struct rx550_gart_offset_bytes too_big;

		too_big.bytes = ap.size;		/* exactamente el limite */
		CHECK(rx550_gart_index_of(&ap, too_big, &idx) != 0,
		      "5. offset == aperture.size rechazado");
		CHECK(idx.index == 0, "5. y la salida quedo a cero");
		too_big.bytes = ap.size + 1;
		CHECK(rx550_gart_index_of(&ap, too_big, &idx) != 0,
		      "5. offset > aperture.size rechazado");
	}
	{
		struct rx550_gart_pte_index i65536;

		i65536.index = 65536;
		CHECK(rx550_gart_entry_offset_of(&ap, i65536, &off) != 0,
		      "5. indice 65536 rechazado (uno mas alla de la ultima)");
		i65536.index = 65535;
		CHECK(rx550_gart_entry_offset_of(&ap, i65536, &off) == 0,
		      "5. indice 65535 es la ultima entrada valida");
		CHECK(off.bytes == 65535u * 8u, "5. y esta en el byte 524280");
	}

	/* ── 6. LA APERTURA ES LA UNICA AUTORIDAD ────────────────────── */
	/* Estos cuatro casos son los que un indexador acotado por una
	 * constante global NO puede pasar.  El mismo offset, la misma
	 * pagina y el mismo PTE_SIZE: lo unico que cambia es aperture.size,
	 * y el resultado cambia con ella, sin recompilar. */
	{
		struct rx550_gart_aperture small;
		struct rx550_gart_offset_bytes o;
		struct rx550_gart_pte_index si;
		struct rx550_gart_offset_bytes eo;

		CHECK(rx550_gart_aperture_init(&small, 0, 4 * RX550_GART_PAGE_SIZE)
		      == 0, "6. apertura de 4 entradas");
		CHECK(small.entries == 4, "6. entries = size / PAGE_SIZE");

		o.bytes = 3 * RX550_GART_PAGE_SIZE;
		CHECK(rx550_gart_index_of(&small, o, &si) == 0,
		      "6. pagina 3 valida en la apertura pequena");
		CHECK(si.index == 3, "6. indice 3");

		o.bytes = 4 * RX550_GART_PAGE_SIZE;
		CHECK(rx550_gart_index_of(&small, o, &si) != 0,
		      "6. pagina 4 rechazada: es el limite, no un maximo global");
		o.bytes = 4 * RX550_GART_PAGE_SIZE + 1;
		CHECK(rx550_gart_index_of(&small, o, &si) != 0,
		      "6. pagina 4+1 rechazada");

		/* offset < SMALL.size es INVALIDO para la apertura de 256 MiB
		 * que esta delante.  Es la discriminante: un indexador con
		 * maximo global devolveria un indice aqui. */
		o.bytes = 5 * RX550_GART_PAGE_SIZE;
		CHECK(rx550_gart_index_of(&small, o, &si) != 0,
		      "6. pagina 5 rechazada aunque quepa en 256 MiB");
		CHECK(rx550_gart_index_of(&ap, o, &si) == 0,
		      "6. pero la MISMA pagina 5 es valida en la apertura de 256 MiB");
		CHECK(si.index == 5, "6. indice 5 en la apertura grande");

		si.index = 4;
		CHECK(rx550_gart_entry_offset_of(&small, si, &eo) != 0,
		      "6. indice 4 no existe en la apertura pequena");
		si.index = 3;
		CHECK(rx550_gart_entry_offset_of(&small, si, &eo) == 0,
		      "6. indice 3 si existe");
		CHECK(eo.bytes == 3u * 8u, "6. byte 24");
		/* Mismo indice, distinta apertura, distinto veredicto. */
		CHECK(rx550_gart_entry_offset_of(&ap, si, &eo) == 0,
		      "6. el indice 3 tambien existe en la apertura grande");
	}
	{
		/* 0x100000000 - 1 = ultimo byte antes de 4 GiB */
		struct rx550_gpuva v = rx550_gpuva_make(UINT64_C(0x0FFFFFFF));

		CHECK(rx550_gart_offset_of(v, &ap, &off) == 0,
		      "5. el ultimo byte de la apertura es valido");
		CHECK(off.bytes == UINT64_C(0x0FFFFFFF), "5. offset correcto");
	}
	{
		struct rx550_gpuva v = rx550_gpuva_make(UINT64_C(0x100000000));

		CHECK(rx550_gart_offset_of(v, &ap, &off) != 0,
		      "5. un byte despues de la apertura se rechaza");
	}

	/* ── 6. PA no alineada: rechazar, no enmascarar ─────────────── */
	{
		struct rx550_system_pa good = { .bytes = UINT64_C(0x1000000) };

		CHECK(rx550_pte_encode(good, RX550_PTE_VALID, &entry) == 0,
		      "6. PA alineada aceptada");
		CHECK(entry == (UINT64_C(0x1000000) | RX550_PTE_VALID), "6. valor correcto");
		CHECK(rx550_pte_decode(entry).bytes == UINT64_C(0x1000000),
		      "6. el round trip devuelve la misma PA");
	}
	{
		struct rx550_system_pa bad = { .bytes = UINT64_C(0x1000001) };

		CHECK(rx550_pte_encode(bad, RX550_PTE_VALID, &entry) != 0,
		      "6. PA con 1 byte de mas RECHAZADA");
		CHECK(entry == 0, "6. y la entrada salio vacia, no enmascarada");
	}
	{
		/* Si el encoder enmascarara, esto devolveria 0x1000 y una
		 * traduccion a la pagina VECINA, en silencio. */
		struct rx550_system_pa bad = { .bytes = UINT64_C(0x1000FFF) };

		CHECK(rx550_pte_encode(bad, RX550_PTE_VALID, &entry) != 0,
		      "6. PA casi alineada rechazada (no se trunca a 0x1000)");
	}
	{
		struct rx550_system_pa too_high = { .bytes = UINT64_C(0x100000000000) };

		CHECK(rx550_pte_encode(too_high, RX550_PTE_VALID, &entry) != 0,
		      "6. PA por encima de 40 bits rechazada");
	}
	CHECK(rx550_pte_valid(entry) == false, "6. una entrada rechazada nunca es valida");

	/* ── flags: solo los del layout de GART de GFX8 ─────────────── */
	CHECK(rx550_pte_encode(pa, RX550_PTE_VALID | RX550_PTE_EXECUTABLE |
			       RX550_PTE_READABLE | RX550_PTE_WRITEABLE,
			       &entry) == 0,
	      "flags del layout de GART aceptados");
	CHECK(rx550_pte_encode(pa, UINT64_C(1) << 3, &entry) != 0,
	      "bit 3 (reservado en la PTE de GART) rechazado");
	CHECK(rx550_pte_encode(pa, UINT64_C(1) << 51, &entry) != 0,
	      "PRT (51) rechazado: el layout lo marca reservado");
	CHECK(rx550_pte_encode(pa, UINT64_C(1) << 55, &entry) != 0,
	      "LOG (55) rechazado");
	CHECK(rx550_pte_encode(pa, UINT64_C(1) << 58, &entry) != 0,
	      "NOALLOC (58) rechazado");
	CHECK(rx550_pte_encode(pa, UINT64_C(1) << 63, &entry) != 0,
	      "IS_PTE (63) rechazado: no existe en GFX8");
	CHECK(rx550_pte_encode(pa, RX550_PTE_FRAG_MASK, &entry) == 0,
	      "FRAG 11:7 aceptado");
	CHECK((entry & RX550_PTE_FRAG_MASK) == RX550_PTE_FRAG_MASK,
	      "FRAG llega entero");
	/* No hay defaults: flags=0 es una entrada sin el bit de validez,
	 * no una entrada utilizable. */
	CHECK(rx550_pte_encode(pa, 0, &entry) == 0, "flags=0 se codifica");
	CHECK(rx550_pte_valid(entry) == false,
	      "pero NO es una entrada valida: eso lo decide el caller, no el encoder");

	/* ── lote: RETIRADO de este componente ─────────────────────────
	 *
	 * rx550_gart_write_batch vivio aqui y se ha ido.  Motivo, con
	 * evidencia y no por preferencia:
	 *
	 *   1. Comprobaba  n > capacity_entries  pero acotaba despues
	 *      first.index + n - 1 contra RX550_GART_INDEX_MAX, que es un
	 *      limite del HARDWARE y no del backing.  Con una tabla de 4
	 *      entradas y first.index = 1000, los dos controles pasaban y
	 *      se escribian 1000 entradas fuera del array.  Mutacion
	 *      equivalente sobre el writer canonico: SIGSEGV, rc=139.
	 *
	 *   2. No tenia consumidor fuera de este test.
	 *
	 *   3. El canonico rx550_gart_write (rx550_gart_write.c) acotaba
	 *      contra backing->entries, que es la autoridad real del
	 *      limite de escritura.
	 *
	 * SUPERSEDED_POR: rx550_gart_write_batch -> rx550_gart_write
	 * Los tests de ese writer viven ahora en tests/test_gart_write.c,
	 * mas los del limite del backing, que antes no existian.
	 */
	/* ── registros VMID0 ────────────────────────────────────────── */
	{
		struct rx550_vram_offset vo = rx550_vram_off(UINT64_C(0x80000000));

		pa.bytes = UINT64_C(0x1000);
		CHECK(rx550_vmid0_base_from_vram(vo, &base) == 0, "base de VRAM");
		CHECK(rx550_vmid0_regs_build(&regs, &cfg, base, 0, ap.end, pa) == 0,
		      "registros construidos");
		CHECK(regs.page_table_base == UINT32_C(0x80000), "BASE = 0x80000");
		CHECK(regs.page_table_start == 0, "START = 0");
		CHECK(regs.page_table_end == UINT32_C(0xFFFF), "END = 0xFFFF");
		CHECK(regs.protection_fault_default == 1, "FAULT_DEFAULT = 1");
		CHECK(regs.cntl2 == 0, "CNTL2 = 0");
		/* ENABLE(bit0) | RANGE_PF(bit4) | DEPTH(0) = 0x11 */
		CHECK(regs.cntl == UINT32_C(0x11), "CNTL = 0x11");
		CHECK((regs.cntl & UINT32_C(0x6)) == 0, "PAGE_TABLE_DEPTH en cero");
		CHECK((regs.cntl & UINT32_C(0x0F000000)) == 0,
		      "PAGE_TABLE_BLOCK_SIZE no se escribe");
		/* el orden 1..7 */
		CHECK(rx550_vmid0_reg_at(&regs, 0) == 0 &&
		      rx550_vmid0_reg_at(&regs, 5) == 5 &&
		      rx550_vmid0_reg_at(&regs, 6) == 6,
		      "orden BASE,START,END,FAULT,CNTL2,CNTL,INVALIDATE");
		CHECK(rx550_vmid0_reg_at(&regs, 7) == 0, "y no hay un octavo");
	}
	{
		struct rx550_vmid0_config bad = cfg;

		bad.enable_context = 0;
		CHECK(rx550_vmid0_regs_build(&regs, &bad, base, 0, ap.end, pa) != 0,
		      "ENABLE_CONTEXT=0 rechazado por el constructor");
		bad = cfg;
		bad.range_pf_default = 0;
		CHECK(rx550_vmid0_regs_build(&regs, &bad, base, 0, ap.end, pa) != 0,
		      "RANGE_PF_DEFAULT=0 rechazado");
	}
	{
		/* Un solo valor malo invalida el struct entero: el caller
		 * recibe -1 y no un registro a medias. */
		pa.bytes = UINT64_C(0x1000);
		CHECK(rx550_vmid0_regs_build(&regs, &cfg, base, 0, ap.end,
					     (struct rx550_system_pa){ UINT64_C(0x100000000000) }) != 0,
		      "dummy_page_addr fuera de rango rechazada");
	}

	/* ── invalidacion: una por lote ─────────────────────────────── */
	CHECK(rx550_vmid0_invalidate_request(0) == 1, "vmid 0 -> bit 0");
	CHECK(rx550_vmid0_invalidate_request(1) == 2, "vmid 1 -> bit 1");
	CHECK(rx550_vmid0_invalidate_request(15) == UINT32_C(0x8000), "vmid 15");
	CHECK(rx550_vmid0_invalidate_request(16) == 0, "vmid 16 fuera de rango");

	/* No hay mb() en el codigo y no hay invalidacion por entrada en la
	 * API.  Ambas ausencias son decisiones, no olvidos. */
	printf("\n  %d pass, %d fail\n", pass, fail);
	return fail ? 1 : 0;
}

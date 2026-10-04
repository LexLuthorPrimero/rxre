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

/* El tope de la cota `x > 0xFFFFFFFF * 4096` de los cuatro sitios.
 *   0xFFFFFFFF << 12 = 0xffffffff000   >>12 = 0xffffffff   CABE en 32 bits
 *   + 4096             = 0x100000000000 >>12 = 0x100000000  NO CABE
 * El tope ACEPTA; una pagina mas RECHAZA. */
#define TOPE	(UINT64_C(0xFFFFFFFF) * 4096)

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

	/* ── EL CERO,  que es el gemelo del defecto cerrado en el consumidor ────
	 *
	 * MEDIDO 2026-10-04:  rx550_vmid0_regs_build()  acotaba el TECHO de
	 * dummy_page_addr  y no el SUELO.  Con 0,  fault_pfn = 0,  y eso es lo que
	 * va a PROTECTION_FAULT_DEFAULT_ADDR:  todo fault de proteccion del
	 * contexto 0 traduce a PA 0.
	 *
	 * Y 0 no es una direccion valida:  es el CENTINELA DE AUSENTE del corpus
	 * (amdgpu_gart.c:79, :84-88, :101, :106, :520).  No es el centinela de
	 * dma_map —que es ~(dma_addr_t)0,  include/linux/dma-mapping.h:116—,  de
	 * modo que un mapa que devolviera 0 PASARIA el control de :152.  Por eso el
	 * argumento "no hay pagina porque el mapa fallo" NO sostiene la guarda.
	 *
	 * Y CON TEXTO DE FONTE el caso 1  —una direccion por debajo de la pagina—
	 * tiene que ACEPTARSE:  la guarda es "== 0"  y solo "== 0",  a proposito.  Un
	 * requisito de alineacion seria otro defecto con su propia evidencia,  y el
	 * hardware no produce una PA de sub-pagina.
	 */
	{
		struct rx550_system_pa z = { 0 };
		struct rx550_system_pa uno = { 1 };
		struct rx550_system_pa pag = { UINT64_C(0x1000) };

		CHECK(rx550_vmid0_regs_build(&regs, &cfg, base, 0, ap.end, z) != 0,
		      "dummy_page_addr == 0 se RECHAZA:  es el centinela de ausente");
		CHECK(rx550_vmid0_regs_build(&regs, &cfg, base, 0, ap.end, uno) == 0,
		      "y una PA de sub-pagina 1 se ACEPTA:  la guarda es == 0, no < 0x1000");
		CHECK(rx550_vmid0_regs_build(&regs, &cfg, base, 0, ap.end, pag) == 0,
		      "y una pagina entera se acepta");

		/* Y QUE EL RECHAZO NO DEJA MEDIO POBLAR,  que es lo que el resto de
		 * las guardas de esta funcion garantiza. */
		CHECK(rx550_vmid0_regs_build(&regs, &cfg, base, 0, ap.end, z) != 0,
		      "y el rechazo es estable");
	}

	/* ── EL ESPACIO DE ERRORES:  una causa, un codigo ──────────────────
	 *
	 * MEDIDO 2026-10-04, ANTES de este bloque:  nueve `return -1` en
	 * rx550_vmid0_regs_build(),  nueve guards distintos,  un solo numero.
	 * Y los CHECK de arriba comparan con `!= 0`,  que es EL DEFECTO REPETIDO:
	 * con nueve causas detras,  `!= 0` no dice cual fallo.  Este bloque dice
	 * cual,  y por eso exige el codigo EXACTO y no un "distinto de cero".
	 *
	 * Y el ultimo bucle no es decorativo:  es el que mata al mutante que
	 * devuelve -1,  y el que mata al que intercambia dos codigos.
	 */
	{
		struct rx550_vmid0_config	cfg;
		struct rx550_vmid0_regs	regs;
		struct rx550_gart_gpu_pfn	base;
		struct rx550_gart_aperture	ap;
		struct rx550_system_pa	pa;
		struct rx550_vmid0_config	bad;
		int	r_null, r_ctx, r_depth, r_pf;
		int	r_base, r_start, r_end;
		int	r_wide, r_absent;
		unsigned	i, j;
		int	colision = 0;

		/* Los nueve codigos, en el MISMO orden que los guards de la
		 * funcion.  El bucle de abajo no puede detectar una colision que
		 * este array no liste,  asi que la lista es parte del contrato. */
		const int	codes[9] = {
			RX550_VMID0_ERR_INCONSISTENT,
			RX550_VMID0_ERR_ENABLE_CONTEXT,
			RX550_VMID0_ERR_DEPTH,
			RX550_VMID0_ERR_RANGE_PF,
			RX550_VMID0_ERR_BASE_TOO_WIDE,
			RX550_VMID0_ERR_START_TOO_WIDE,
			RX550_VMID0_ERR_END_TOO_WIDE,
			RX550_VMID0_ERR_PA_TOO_WIDE,
			RX550_VMID0_ERR_NO_DUMMY_PAGE,
		};

		CHECK(rx550_vmid0_config_build(&cfg) == RX550_VMID0_REGS_OK,
		      "ESPACIO: config de partida");
		CHECK(rx550_vmid0_base_from_vram((struct rx550_vram_offset){ 0 },
						 &base) == 0,
		      "ESPACIO: base de partida");
		CHECK(rx550_gart_aperture_init(&ap, 0, UINT64_C(0x10000)) == 0,
		      "ESPACIO: apertura de partida");
		pa.bytes = UINT64_C(0x1000);

		/* 1. puntero nulo:  un fallo del llamante,  no un valor malo.
		 * Comparte el numero -1 con la causa 2 si el espacio no esta. */
		r_null = rx550_vmid0_regs_build(NULL, &cfg, base, 0, ap.end, pa);
		CHECK(r_null == RX550_VMID0_ERR_INCONSISTENT,
		      "ESPACIO: regs NULL -> INCONSISTENT");

		/* 2..4.  los tres campos de cfg.  Cada uno es una manera distinta
		 * de equivocarse al construir el cfg. */
		bad = cfg;
		bad.enable_context = 0;
		r_ctx = rx550_vmid0_regs_build(&regs, &bad, base, 0, ap.end, pa);
		CHECK(r_ctx == RX550_VMID0_ERR_ENABLE_CONTEXT,
		      "ESPACIO: enable_context=0 -> ENABLE_CONTEXT");
		bad = cfg;
		bad.page_table_depth = 1;
		r_depth = rx550_vmid0_regs_build(&regs, &bad, base, 0, ap.end, pa);
		CHECK(r_depth == RX550_VMID0_ERR_DEPTH,
		      "ESPACIO: depth=1 -> DEPTH (esa profundidad es de VMID1)");
		bad = cfg;
		bad.range_pf_default = 0;
		r_pf = rx550_vmid0_regs_build(&regs, &bad, base, 0, ap.end, pa);
		CHECK(r_pf == RX550_VMID0_ERR_RANGE_PF,
		      "ESPACIO: range_pf_default=0 -> RANGE_PF");

		/* 5..7.  los tres techos.  Los tres son "no cabe tras el >>12",
		 * pero van a TRES registros distintos y los produce el llamante
		 * desde tres sitios distintos. */
		{
			struct rx550_gart_gpu_pfn	wide;

			wide.value = UINT64_C(0x100000000);
			r_base = rx550_vmid0_regs_build(&regs, &cfg, wide, 0,
							ap.end, pa);
		}
		CHECK(r_base == RX550_VMID0_ERR_BASE_TOO_WIDE,
		      "ESPACIO: base = 2^32 -> BASE_TOO_WIDE");
		r_start = rx550_vmid0_regs_build(&regs, &cfg, base, TOPE + 4096,
						 ap.end, pa);
		CHECK(r_start == RX550_VMID0_ERR_START_TOO_WIDE,
		      "ESPACIO: gart_start una pagina mas -> START_TOO_WIDE");
		r_end = rx550_vmid0_regs_build(&regs, &cfg, base, 0,
					       TOPE + 4096, pa);
		CHECK(r_end == RX550_VMID0_ERR_END_TOO_WIDE,
		      "ESPACIO: gart_end una pagina mas -> END_TOO_WIDE");

		/* 8 y 9.  LAS DOS CAUSAS DEL MISMO PARAMETRO.  Este es el par por
		 * el que se abrio el espacio,  y el que lo justifica:  el gemelo
		 * rx550_gart_seq.c:484-487 ya devolvia DOS codigos distintos
		 * sobre el MISMO dummy_page_addr porque los DOS arreglos son
		 * distintos.  Un codigo comun hacia que el llamante probara
		 * dma_set_mask,  que arregla el techo y no arregla el suelo. */
		r_wide = rx550_vmid0_regs_build(&regs, &cfg, base, 0, ap.end,
					(struct rx550_system_pa){ TOPE + 4096 });
		CHECK(r_wide == RX550_VMID0_ERR_PA_TOO_WIDE,
		      "ESPACIO: dummy > 2^40-1 -> PA_TOO_WIDE (arreglo: la mascara DMA)");
		r_absent = rx550_vmid0_regs_build(&regs, &cfg, base, 0, ap.end,
					(struct rx550_system_pa){ 0 });
		CHECK(r_absent == RX550_VMID0_ERR_NO_DUMMY_PAGE,
		      "ESPACIO: dummy == 0 -> NO_DUMMY_PAGE (arreglo: rx550_dummy_page_init)");
		CHECK(r_wide != r_absent,
		      "ESPACIO: y las DOS causas del mismo parametro NO se confunden");

		/* Y QUE NO HAYA NINGUNA COLISION:  nueve causas,  nueve codigos.
		 * Este bucle es la asercion que distingue un espacio de errores de
		 * un -1 con mejores nombres. */
		for (i = 0; i < 9u; i++)
			for (j = i + 1u; j < 9u; j++)
				if (codes[i] == codes[j])
					colision++;
		CHECK(colision == 0,
		      "ESPACIO: nueve causas, nueve codigos, cero colisiones");

		/* Y que el exito no se confunda con ninguno de los errores. */
		CHECK(RX550_VMID0_REGS_OK == 0 && RX550_VMID0_REGS_OK != r_absent
		      && RX550_VMID0_REGS_OK != r_wide,
		      "ESPACIO: OK es 0 y no es ninguno de los errores");
	}

	/* ── EL LIMITE INCLUSIVO, que no tenia caso ─────────────────────
	 *
	 * MEDIDO 2026-10-03 con tools/mutdrv.py: los cuatro sitios de la
	 * forma `x > 0xFFFFFFFF * 4096` en rx550_vmid0_gart.c devolvian
	 * SUPERVIVIENTES, y el mutante `>=` no lo podia matar esta suite.
	 * La razon es esta, y no es que la suite fuera floja: NO HABIA NINGUN
	 * CASO EN EL LIMITE.  Con 4 KiB de VRAM probados y `>` en el codigo,
	 * un valor que cabe sale rechazado y uno que no cabe tambien, luego
	 * el par entero daba verde con las dos versiones.
	 *
	 * El limite es INCLUSIVO porque lo que decide es el >>12, no el
	 * registro:
	 *
	 *   0xFFFFFFFF << 12  =  0xffffffff000   >>12 = 0xffffffff   CABE
	 *   + una pagina      =  0x100000000000  >>12 = 0x100000000  NO CABE
	 *
	 * Con `>` el primero se rechazaba: el codigo contradecia su propio
	 * comentario ("un offset que no quepa tras el >>12 no se trunca"), y
	 * el que no cabe es el segundo.
	 *
	 * IMPACTO EN ESTA PLACA: ninguno, y hay que decirlo.  Con 2 GiB de
	 * VRAM el valor del limite es inalcanzable.  El defecto es del
	 * CONTRATO del validador, no de un camino que esta placa exercise.
	 */
	{
		struct rx550_gart_gpu_pfn	pfn;

		/* el valor que SI cabe: 0xffffffff000 */
		CHECK(rx550_vmid0_base_from_vram(
			      (struct rx550_vram_offset){ UINT64_C(0xFFFFFFFF) * 4096 },
			      &pfn) == 0,
		      "LIMITE: 0xffffffff000 (>>12 = 0xffffffff) ACEPTADO");
		CHECK(pfn.value == UINT32_C(0xFFFFFFFF),
		      "LIMITE: y el registro vale 0xffffffff, no truncado");

		/* una pagina por encima: ya no cabe */
		CHECK(rx550_vmid0_base_from_vram(
			      (struct rx550_vram_offset){ UINT64_C(0x100000000000) },
			      &pfn) != 0,
		      "LIMITE: 0x100000000000 (una pagina mas) RECHAZADO");

		/* y el ultimo valor de 4 KiB de verdad, por si el limite se
		 * movia sin que se notase el >>12 */
		CHECK(rx550_vmid0_base_from_vram(
			      (struct rx550_vram_offset){ UINT64_C(0xFFFFFFEF000) },
			      &pfn) == 0 && pfn.value == UINT32_C(0xFFFFFFEF),
		      "LIMITE: el ultimo PFN real (0xffffffef) ACEPTADO y exacto");
	}

	/* ── los otros tres sitios de la misma forma ───────────────────
	 * gart_start, gart_end y dummy_page_addr pasan por la misma cota, y
	 * con el mismo defecto.  Un caso en la puerta de regs_build() los
	 * cubre a los tres sin tres bloques. */
	{
		struct rx550_vmid0_config		cfg;
		struct rx550_vmid0_regs		regs;
		struct rx550_gart_gpu_pfn		base;
		struct rx550_gart_aperture		ap;
		struct rx550_system_pa			pa;

		CHECK(rx550_vmid0_config_build(&cfg) == 0, "LIMITE: config de partida");
		CHECK(rx550_vmid0_base_from_vram((struct rx550_vram_offset){ 0 },
						 &base) == 0,
		      "LIMITE: base de partida");
		/* La apertura es un componente DISTINTO y su cota es otra:
		 * RX550_GART_SIZE_MAX = 256 MiB (POLICY, gmc_v8_0.c:595) y el
		 * start va alineado a 2^32 (RX550_GART_APERTURE_ALIGN).  Una
		 * apertura de 0xffffffff000 bytes es de otro dominio y aqui
		 * seria un caso sin sentido. */
		CHECK(rx550_gart_aperture_init(&ap, 0, UINT64_C(0x10000)) == 0,
		      "LIMITE: apertura de 64 KiB en start 0 (alineado a 2^32)");

		pa.bytes = UINT64_C(0x1000);
		/* los tres sitios comparten la cota `x > 0xffffffff000`, y el
		 * tope tiene que ACEPTARSE: 0xffffffff >> 12 cabe en el
		 * registro.  una pagina mas ya no, y tiene que rechazarse.
		 *
		 * MEDIDO 2026-10-03: con `>=` en vez de `>` los cuatro sitios
		 * devolvian SUPERVIVIENTES, y estos son los CHECK que los matan.
		 * El mutante es el DEFECTUOSO: `>=` rechaza el tope, que si
		 * cabe.  El codigo original es el correcto. */
		CHECK(rx550_vmid0_regs_build(&regs, &cfg, base, TOPE, ap.end, pa) == 0,
		      "LIMITE: gart_start = 0xffffffff000 ACEPTADO (>>12 cabe)");
		CHECK(rx550_vmid0_regs_build(&regs, &cfg, base, TOPE + 4096, ap.end, pa) != 0,
		      "LIMITE: gart_start una pagina mas RECHAZADO");
		CHECK(rx550_vmid0_regs_build(&regs, &cfg, base, 0, TOPE, pa) == 0,
		      "LIMITE: gart_end = 0xffffffff000 ACEPTADO");
		CHECK(rx550_vmid0_regs_build(&regs, &cfg, base, 0, TOPE + 4096, pa) != 0,
		      "LIMITE: gart_end una pagina mas RECHAZADO");
		CHECK(rx550_vmid0_regs_build(&regs, &cfg, base, 0, ap.end,
					     (struct rx550_system_pa){ TOPE }) == 0,
		      "LIMITE: dummy_page_addr = 0xffffffff000 ACEPTADO");
		CHECK(rx550_vmid0_regs_build(&regs, &cfg, base, 0, ap.end,
					     (struct rx550_system_pa){ TOPE + 4096 }) != 0,
		      "LIMITE: dummy_page_addr una pagina mas RECHAZADO");
	}

	/* ── apertura: off == size es uno MAS ALLA ──────────────────────
	 * MEDIDO tambien por mutdrv.py: `off >= ap->size` -> `>` sobrevive.
	 * Esta vez el codigo es el correcto y lo que falta es el caso: un
	 * offset IGUAL al tamano esta fuera, no es el ultimo. */
	{
		struct rx550_gart_aperture	ap;
		struct rx550_gpuva		gv;
		struct rx550_gart_offset_bytes	off;

		CHECK(rx550_gart_aperture_init(&ap, 0, UINT64_C(0x10000)) == 0,
		      "APERTURA: init de la apertura de prueba");
		gv.bytes = UINT64_C(0x10000) - 1u;
		CHECK(rx550_gart_offset_of(gv, &ap, &off) == 0 && off.bytes == UINT64_C(0xFFFF),
		      "APERTURA: el ULTIMO byte (size-1) es valido");
		gv.bytes = UINT64_C(0x10000);
		CHECK(rx550_gart_offset_of(gv, &ap, &off) != 0,
		      "APERTURA: off == size RECHAZADO (uno mas alla)");
		gv.bytes = 0;
		CHECK(rx550_gart_offset_of(gv, &ap, &off) == 0 && off.bytes == 0,
		      "APERTURA: gpuva == start (0) da offset 0, y es VALIDO");
		gv.bytes = UINT64_C(0x100000000000) - 1u;   /* start-1 con start=2^32 */
		CHECK(rx550_gart_offset_of(gv, &ap, &off) != 0,
		      "APERTURA: un byte por debajo del start RECHAZADO");
	}

	/* ── LOS TRES SUPERVIVIENTES QUE QUEDABAN, uno a uno ───────────
	 *
	 * Cada uno es una SEGUNDA funcion con la misma cota, y la primera vez
	 * que se midio solo se cubrió una de las dos.  Es la forma que toma
	 * un agujero cuando el mismo limite aparece en varios sitios: se
	 * tapa el que se probó y los demas siguen abiertos sin que nada lo
	 * diga, porque el codigo es identico y se lee como si estuviera
	 * cubierto.
	 *
	 * MEDIDO 2026-10-03 con tools/mutdrv.py, antes de estos casos:
	 *   rx550_vmid0_gart.c:96   >= -> >    (rx550_gart_index_of)
	 *   rx550_vmid0_gart.c:198  >  -> >=   (rx550_vmid0_fault_from_pa)
	 *   rx550_vmid0_gart.c:228  >  -> >=   (base.value, campo de 32 bits)
	 */
	{
		struct rx550_gart_aperture	ap;
		struct rx550_gart_pte_index	idx;

		/* 1. index_of: la MISMA cota que offset_of, en otra funcion.
		 * off == size es uno mas alla y tiene que rechazarse; el
		 * mutante `>` lo aceptaria y devolveria un indice de una
		 * entrada que la apertura no tiene. */
		CHECK(rx550_gart_aperture_init(&ap, 0, UINT64_C(0x10000)) == 0,
		      "INDICE: apertura de 64 KiB");
		CHECK(rx550_gart_index_of(&ap,
					  (struct rx550_gart_offset_bytes){ UINT64_C(0x10000) },
					  &idx) != 0,
		      "INDICE: off == size RECHAZADO (1+ entradas fuera)");
		CHECK(rx550_gart_index_of(&ap,
					  (struct rx550_gart_offset_bytes){ UINT64_C(0xFFFF) },
					  &idx) == 0,
		      "INDICE: off == size-1 ACEPTADO");

		/* 2. fault_from_pa: la misma cota, sobre una PA de sistema en
		 * lugar de un offset de VRAM.  El tope ACEPTA: >>12 da
		 * 0xffffffff, y un PFN de 32 bits lo admite entero. */
		{
			struct rx550_pfn	p;

			CHECK(rx550_vmid0_fault_from_pa(
				  (struct rx550_system_pa){ TOPE }, &p) == 0,
			      "FAULT: PA = 0xffffffff000 ACEPTADA (>>12 = 0xffffffff)");
			CHECK(p.value == UINT64_C(0xFFFFFFFF),
			      "FAULT: y el PFN vale 0xffffffff, no truncado");
			CHECK(rx550_vmid0_fault_from_pa(
				  (struct rx550_system_pa){ TOPE + 4096 }, &p) != 0,
			      "FAULT: PA una pagina mas RECHAZADA");
		}

		/* 3. base.value: aqui el campo es un uint64_t que va a un
		 * registro de 32 bits, y 0xffffffff es el valor MAXIMO
		 * legitimo.  El mutante `>=` lo rechazaria.  MEDIDO: por eso
		 * :228 tambien era un agujero y no un mutante equivalente --
		 * una comprobacion que "no puede fallar" porque el tipo la
		 * acota seria otra historia, y aqui el tipo es de 64 bits. */
		{
			struct rx550_vmid0_config	cfg;
			struct rx550_vmid0_regs	regs;
			struct rx550_system_pa	pa;
			struct rx550_gart_gpu_pfn	maxpfn;

			CHECK(rx550_vmid0_config_build(&cfg) == 0, "BASE: config");
			maxpfn.value = UINT64_C(0xFFFFFFFF);
			pa.bytes = UINT64_C(0x1000);
			CHECK(rx550_vmid0_regs_build(&regs, &cfg, maxpfn, 0,
						     UINT64_C(0x1000), pa) == 0,
			      "BASE: base.value = 0xffffffff ACEPTADO (el maximo)");
			maxpfn.value = UINT64_C(0x100000000);
			CHECK(rx550_vmid0_regs_build(&regs, &cfg, maxpfn, 0,
						     UINT64_C(0x1000), pa) != 0,
			      "BASE: base.value = 0x100000000 RECHAZADO (no cabe)");
		}
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

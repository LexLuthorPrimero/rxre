/* SPDX-License-Identifier: GPL-2.0 */
/*
 * rx550_vmid0_gart.h — VMID0 de GFX8/Polaris12: una tabla, una traduccion.
 *
 *   TARGET = RX 550 instalada en esta maquina   (1002:699F, Polaris12, GFX8)
 *   SCOPE  = EXCLUSIVO
 *
 * QUE ES
 *   El camino de direccionamiento del kernel en esta ASIC.  GPUVA -> entrada
 *   GART -> direccion fisica, en una sola traduccion.  Sin directorio, sin
 *   segundo nivel, sin indice de 2 MiB.
 *
 * QUE NO ES
 *   No es una PDB0.  No es un allocator.  No programa el hardware: devuelve
 *   valores de registro y el llamador los escribe.  No habla con el ring.
 *
 * DE DONDE VIENE CADA COSA
 *   FACT  gmc_v8_0.c:895  PAGE_TABLE_DEPTH = 0 en el contexto 0
 *   FACT  gmc_v8_0.c:840  la tabla es el BO de la GART
 *   FACT  gmc_v8_0.c:889  BASE = gpu_offset(gart.bo) >> 12
 *   FACT  gmc_v8_0.c:887  START = gart_start >> 12
 *   FACT  gmc_v8_0.c:888  END   = gart_end   >> 12
 *   FACT  gmc_v8_0.c:891  FAULT_DEFAULT = dummy_page_addr >> 12
 *   FACT  gmc_v8_0.c:592  CHIP_POLARIS12 -> gart_size = 256 MiB
 *   FACT  gmc_v8_0.c:691-702  layout de la PTE en VI  (ver abajo)
 *   FACT  gmc_v8_0.c:728  GFX8 limpia PRT
 *   FACT  gmc_v8_0.c:961  la GART arranca con EXECUTABLE
 *         MEDIDO 2026-10-04: el bit EXECUTABLE (bit 4) si sobrevive, pero el
 *         VALOR DE LA ENTRADA no es 0x10.  El corpus pasa esa mascara a
 *         memset_io, que rellena por BYTE, luego la entrada queda
 *         0x1010101010101010.  Ver la nota larga de rx550_gart_table.h.
 *   FACT  amdgpu_gart.c:324  t = offset / 4096
 *   FACT  amdgpu_gmc.c:175   writeq en (gpu_page_idx * 8)
 *
 * DERIVED
 *   PAGE_SHIFT = 12, PA en los bits 12..39 de la entrada
 *   count = gmc.gart_size / 4096  -- FORMULA, no constante.  Ver abajo.
 *   Con el gart_size por defecto de POLARIS12 (256 MiB) salen 65536
 *   entradas; con gartsize=1024 salen 262144, en la misma ASIC.
 *   MEDIDO: amdgpu_gart.c:533, amdgpu_gart.h:33, gmc_v8_0.c:595 y
 *   :604-605, amdgpu_drv.c:154 y :293 (el parametro es 0600).
 *   Por eso ENTRY_COUNT = 65536 se retiró de este header: era un
 *   DERIVED congelado, y una constante global que depende de un
 *   parámetro de módulo no es una autoridad de rango.
 *
 * DESIGN_CHOICE
 *   gart_start = 0
 *   PA no alineada -> rechazo, nunca mascara
 *   no hay flags por defecto: el constructor los recibe
 *
 * UNKNOWN
 *   combinacion canonica de flags para una entrada GART valida en GFX8
 *   si mb() es requisito de GFX8 o solo barrera de orden de software
 *   alcance de la TLB entre VMIDs
 *   alineacion que el hardware exige del gpu_offset del BO de tabla
 *
 * LO QUE ESTE COMPONENTE NO AFIRMA
 *   Que una PTE escrita sea visible para el hardware.  Eso exige el WRITE_BATCH
 *   completo y una invalidacion, y las dos estan separadas del encoder.
 *   Que una traduccion correcta produzca ejecucion.  No hay ningun estado aqui
 *   que afirme eso.
 */
#ifndef RX550_VMID0_GART_H
#define RX550_VMID0_GART_H

#include "rx550_spaces.h"

/* ── geometria (FACT + DERIVED + POLICY) ────────────────────────────────── */

/* DEFAULT_OBSERVED_IN_REFERENCE_DRIVER, no invariante de hardware.
 * gmc_v8_0.c:595 asigna 256 MiB en una rama de inicializacion; el valor
 * real de esta placa es DEFERRED_RUNTIME.  Aqui es unicamente el tope que
 * acepta la politica de admision, NO la capacidad de ninguna apertura.  El
 * indice se acota contra aperture.size y aperture.entries, que son la
 * unica autoridad de rango del componente. */
#define RX550_GART_SIZE_MAX		(UINT64_C(256) << 20)	/* POLICY: gmc_v8_0.c:595 */
#define RX550_GART_PAGE_SIZE		UINT64_C(4096)		/* FACT: amdgpu_gart.h:35 */
#define RX550_GART_PAGE_SHIFT		12u			/* DERIVED */
#define RX550_GART_PTE_SIZE		UINT64_C(8)		/* FACT: gmc_v8_0.c:960 */

/* RX550_GART_ENTRY_COUNT y RX550_GART_INDEX_MAX se han retirado.  Eran una
 * segunda autoridad de rango global: un indexador que acota por 65536
 * acepta un offset que la apertura que el caller tiene delante rechazaria.
 * entries se deriva por apertura (aperture_init). */

/* El rango de direcciones es de 2^40 bytes, pero el campo de la entrada
 * ocupa 28 bits porque los 12 bajos valen cero por construccion.  gmc_v8_0.c:694
 * lo dice asi: "39:12 4k physical page base address". */
#define RX550_GART_PA_MASK		UINT64_C(0x000000FFFFFFF000)
#define RX550_GART_PA_SHIFT		12u
#define RX550_GART_PA_ENTRY_BITS	28u	/* bits 12..39 */

/* ── layout de la entrada (FACT, gmc_v8_0.c:691-702) ──────────────────────
 *
 *   63:40  reserved
 *   39:12  4k physical page base address
 *   11:7   fragment
 *   6      write
 *   5      read
 *   4      exe
 *   3      reserved          <- NO es TMZ aqui
 *   2      snooped
 *   1      system
 *   0      valid
 *
 * Los bits 3 y 63:40 estan RESERVADOS en una PTE de GART.  amdgpu_vm.h define
 * TMZ(3), PRT(51), LOG(55), TF(56) y NOALLOC(58), pero esos son bits de la
 * pagina de dos niveles, no de la GART.  Este componente no los acepta, y el
 * encoder los rechaza si aparecen.  No es prudencia: es el layout.
 */
#define RX550_PTE_VALID		(UINT64_C(1) << 0)
#define RX550_PTE_SYSTEM	(UINT64_C(1) << 1)
#define RX550_PTE_SNOOPED	(UINT64_C(1) << 2)
#define RX550_PTE_EXECUTABLE	(UINT64_C(1) << 4)
#define RX550_PTE_READABLE	(UINT64_C(1) << 5)
#define RX550_PTE_WRITEABLE	(UINT64_C(1) << 6)
#define RX550_PTE_FRAG_MASK	(UINT64_C(0x1F) << 7)	/* 11:7 */

/* Los unicos bits de flag que una PTE de GART de GFX8 define. */
#define RX550_PTE_FLAG_MASK	(RX550_PTE_VALID | RX550_PTE_SYSTEM |	\
				 RX550_PTE_SNOOPED | RX550_PTE_EXECUTABLE |	\
				 RX550_PTE_READABLE | RX550_PTE_WRITEABLE |	\
				 RX550_PTE_FRAG_MASK)

/* Bit 3 y 63:40 reservados.  Se nombran para poder rechazar, no para usarlos. */
#define RX550_PTE_RESERVED_MASK	(UINT64_C(1) << 3)
#define RX550_PTE_RESERVED_HIGH	(UINT64_C(0xFFFFFF) << 40)	/* 40..63 */

#define RX550_PTE_ENTRY_MASK	(RX550_PTE_FLAG_MASK | RX550_PTE_PA_MASK | \
				 RX550_PTE_RESERVED_MASK)

/* ── deep: PAGE_TABLE_DEPTH ─────────────────────────────────────────────
 * Es el selector del modelo de direccionamiento, no un parametro.  El
 * El codigo de dos niveles usa 1 (gmc_v8_0.c:925).  Aqui 0, y solo 0. */
#define RX550_VMID0_DEPTH		0u
#define RX550_VMID0_DEPTH_MAX		0u
#define RX550_VMID0_ENABLE_CONTEXT	1u
#define RX550_VMID0_RANGE_PF_DEFAULT	1u

/* ── tipos ──────────────────────────────────────────────────────────────
 * Un struct por unidad y por espacio.  No hay conversion implicita posible
 * entre dos de ellos: el compilador no la ofrece porque los tipos son
 * distintos.  El proposito no es validar en runtime, es que un intercambio
 * no compile.
 *
 * Los que ya existen en rx550_spaces.h y se reutilizan tal cual:
 *   struct rx550_gpuva         bytes, espacio virtual
 *   struct rx550_system_pa     bytes, espacio fisico del sistema
 *   struct rx550_vram_offset   bytes, offset GPU dentro de VRAM
 * Los nuevos son los que no tienen equivalente:
 *   rx550_gart_offset_bytes    bytes, RELATIVOS a gart_start
 *   rx550_gart_pte_index       PAGINAS, indice dentro de la tabla
 *   rx550_gart_gpu_pfn         PAGINAS, derivadas de un offset en VRAM
 *   rx550_pfn                  PAGINAS, genericas
 *
 * rx550_gart_gpu_pfn y rx550_pfn son ambos "paginas" y se parecen.  No son
 * intercambiables: el primero sale de un offset dentro de VRAM y se escribe
 * en PAGE_TABLE_BASE_ADDR; el segundo sale de una PA de sistema.  Occupan el
 * mismo campo de 32 bits del registro y describen cosas distintas.
 */
struct rx550_gart_offset_bytes {
	uint64_t bytes;
};

struct rx550_gart_pte_index {
	uint64_t index;
};

struct rx550_pfn {
	uint64_t value;
};

struct rx550_gart_gpu_pfn {
	uint64_t value;
};

/* ── la apertura ─────────────────────────────────────────────────────
 * gart_start no lo decide este componente: lo recibe.  Solo se fija que
 * tiene que estar alineado a 4 GiB, porque el registro START no tiene bits
 * para otra cosa y el driver de referencia lo alinea (amdgpu_gmc.c:332).
 */
#define RX550_GART_APERTURE_ALIGN	(UINT64_C(1) << 32)

struct rx550_gart_aperture {
	uint64_t	start;		/* lo recibe el caller */
	uint64_t	size;		/* lo recibe el caller; NO es un FACT del
					 * hardware, es la apertura concreta */
	uint64_t	entries;	/* size / PAGE_SIZE, DERIVED.  Autoridad
					 * de rango para el indexador. */
	uint64_t	end;		/* start + size - 1, DERIVED */
};

int rx550_gart_aperture_init(struct rx550_gart_aperture *ap,
			     uint64_t start, uint64_t size);

/* ── CONSTRUCTION: GPUVA -> indice ───────────────────────────────────── */

/* Precondicion: gpuva >= ap->start  y  gpuva - start < ap->size.
 * Si no se cumple, devuelve -1 y escribe 0 en la salida.  Nunca trunca:
 * un GPUVA por debajo del inicio es un error del caller, no un indice
 * enorme. */
int rx550_gart_offset_of(const struct rx550_gpuva gpuva,
			 const struct rx550_gart_aperture *ap,
			 struct rx550_gart_offset_bytes *out);

/* CONTRATO:  off.bytes < ap->size  y  off.bytes >> PAGE_SHIFT < ap->entries.
 * La apertura es la UNICA autoridad de rango.  No existe un maximo global al
 * que remitirse: un offset valido para una apertura puede no serlo para otra
 * con la misma constante de pagina, y por eso ap es un parametro y no una
 * precondicion invisible del caller. */
int rx550_gart_index_of(const struct rx550_gart_aperture *ap,
			const struct rx550_gart_offset_bytes off,
			struct rx550_gart_pte_index *out);

/* Indice -> desplazamiento en BYTES dentro del array de entradas.
 * entry_byte_offset = pte_index * 8.  El factor 8 es el tamano de la
 * entrada, no un desplazamiento constante: por eso es una funcion.
 * CONTRATO: idx.index < ap->entries. */
int rx550_gart_entry_offset_of(const struct rx550_gart_aperture *ap,
			       const struct rx550_gart_pte_index idx,
			       struct rx550_gart_offset_bytes *out);

/* ── CONSTRUCTION: PTE ──────────────────────────────────────────────────
 *
 * PA_POLICY = REJECT_UNALIGNED  (DESIGN_CHOICE, no un hecho del hardware)
 * El corpus enmascara (amdgpu_gmc.c:173) y eso no se copia: un truncamiento
 * silencioso convierte un error del caller en una traduccion a otra pagina,
 * y ese fallo no aparece en ninguna parte.  Aqui una PA no alineada es un
 * -1, no una pagina distinta.
 *
 * flags: se pasan explicitos.  No hay default.  Un flag fuera de
 * RX550_PTE_FLAG_MASK, o un bit reservado, es un -1: el layout de la GART
 * de GFX8 no los define y escribirlos seria afirmar algo que el hardware
 * no ha demostrado. */
int rx550_pte_encode(struct rx550_system_pa pa, uint64_t flags,
		     uint64_t *out);

/* Extraer la PA de una entrada ya construida.  No es un wrapper de
 * conveniencia: obliga a pasar por la mascara en un solo sitio. */
struct rx550_system_pa rx550_pte_decode(uint64_t entry);

bool rx550_pte_valid(uint64_t entry);

/* ── PROGRAMMING: valores de registro de VMID0 ────────────────────────
 *
 * Se construyen aquí y los escribe el llamador.  Este componente no tiene
 * MMIO.  La ventaja de que sea así: el orden se puede comprobar sin GPU.
 */
struct rx550_vmid0_config {
	uint32_t	enable_context;
	uint32_t	page_table_depth;
	uint32_t	range_pf_default;
};

/* Rechaza cualquier profundidad distinta de 0.  No es que el hardware lo
 * rechace: es que un PAGE_TABLE_DEPTH=1 en el contexto 0 programaria una
 * traduccion de dos niveles contra una tabla que no tiene nivel superior,
 * y eso lo decide el constructor, no el silicio. */
int rx550_vmid0_config_build(struct rx550_vmid0_config *cfg);

struct rx550_vmid0_regs {
	uint32_t	page_table_base;		/* GART_GPU_PFN */
	uint32_t	page_table_start;	/* PFN */
	uint32_t	page_table_end;		/* PFN */
	uint32_t	protection_fault_default;	/* PFN, de SISTEMA */
	uint32_t	cntl2;			/* literal 0 */
	uint32_t	cntl;			/* bitfield */

/* El orden de escritura es el de gmc_v8_0.c:886-897 y :941.  Va en el
 * struct porque un orden que sólo existe en un comentario no se puede
 * verificar. */
	unsigned	order[7];
};

/* Dos overloaded no: son dos funciones distintas con tipos distintos.
 * BASE sale de un offset en VRAM, FAULT_DEFAULT sale de una PA de sistema.
 * Pasar la equivocada no compila. */
int rx550_vmid0_base_from_vram(struct rx550_vram_offset off,
			       struct rx550_gart_gpu_pfn *out);
int rx550_vmid0_fault_from_pa(struct rx550_system_pa pa,
			      struct rx550_pfn *out);

/* Construye los seis valores de registro.  Valida TODO antes de devolver
 * nada: si un valor no es representable, no hay GAME OVER parcial. */
int rx550_vmid0_regs_build(struct rx550_vmid0_regs *regs,
			   const struct rx550_vmid0_config *cfg,
			   struct rx550_gart_gpu_pfn base,
			   uint64_t gart_start, uint64_t gart_end,
			   struct rx550_system_pa dummy_page_addr);

static inline uint32_t rx550_vmid0_reg_at(const struct rx550_vmid0_regs *r,
					  unsigned n)
{
	return (n < 7u) ? r->order[n] : 0u;
}

/* ── OBSERVATION: invalidacion ────────────────────────────────────────
 * El requisito es WRITE_BATCH_COMPLETE -> INVALIDATE.  Uno por lote.
 * No hay invalidate_per_pte en esta API, y su ausencia es deliberada.
 *
 * mb() NO se llama.  No hay evidencia de que GFX8 lo exija como requisito
 * de hardware, y anadir una barrera sin motivo declarado seria inventar
 * una restriccion.  Si aparece la evidencia, es un campo mas de aqui.
 */
#define RX550_VMID0_TLB_INVALID_BIT	0u	/* 1 << 0, gmc_v8_0.c:665 */

static inline uint32_t rx550_vmid0_invalidate_request(unsigned vmid)
{
	return (vmid < 16u) ? (UINT32_C(1) << vmid) : 0u;
}

#endif /* RX550_VMID0_GART_H */

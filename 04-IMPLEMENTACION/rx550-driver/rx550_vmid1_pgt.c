// SPDX-License-Identifier: GPL-2.0-only
/*
 * rx550_vmid1_pgt.c — la jerarquia de tabla de VMID1 en GFX8.
 *
 *   TARGET = RX 550 instalada en esta maquina  (1002:699F, Polaris12, GFX8)
 *   SCOPE  = EXCLUSIVO
 *
 * C PURO.  Sin inline asm, sin MMIO, sin ioremap, sin readl/writel, sin ring,
 * sin acceso a GPU, sin reserva de memoria.  Compilable y testeable fuera del
 * kernel, que es lo que permite que la geometria —que es aritmetica— se
 * verifique sin hardware.
 *
 * LA GEOMETRIA SE DERIVA, NO SE DECLARA
 *   Ver rx550_vmid1_geometry() y la cabecera.  El nucleo del fichero es la
 *   funcion que reproduce la aritmetica de amdgpu_vm.c:2433-2466 con
 *   max_level = 1, que es lo que GFX8 pasa en gmc_v8_0.c:1127.
 *
 * LO QUE ESTE FICHERO NO USA, Y POR QUE
 *   · rx550_pdb0.h        su encoding de entradas es de PTE, y un PDE no tiene
 *                         esos campos: 5 y 6 caen dentro de 39:1.  Ademas su
 *                         LEAF_BIT 54 cae en 58:40, que es reservado.
 *   · rx550_vmid0_gart.h  de ahi sale rx550_pte_encode, y ese encoder es de PTE.
 *                         Para el root hay que usar el de PDE, que es el de aqui.
 *   · ningun header del kernel  para que la aritmetica sea testeable en
 *                         userspace y para no acoplar un constructor puro a un
 *                         entorno de compilacion que no necesita.
 *
 * T10 y T11 verifican estaticamente las dos primeras ausencias.
 */

/* COMPATIBILIDAD KBUILD.  El kernel no tiene <string.h>: tiene
 * <linux/string.h>.  Mismo split que rx550_spaces.h y rx550_mmio_access.h.
 *
 * CORRECCION DE LA AFIRMACION DE ARRIBA, 2026-10-03.  Decia que aqui no hay
 * "ningun header del kernel" y que "T10 y T11 verifican estaticamente las dos
 * primeras ausencias".  Las dos mitades eran inexactas:
 *
 *   - T10 y T11 comprueban la separacion respecto de rx550_pdb0.h y
 *     rx550_vmid0_gart.h, y que no se reutilice su encoder de PTE.  No
 *     comprueban nada sobre cabeceras del kernel.  Se leyo en
 *     test_vmid1_pgt.c:496-522.
 *   - "para que la aritmetica sea testeable en userspace" sigue siendo cierto,
 *     y este split lo mantiene: la rama de userspace sigue sin tocar el
 *     kernel.  Lo que cambio es que la rama de kernel deja de estar prohibida.
 *
 * El motivo del cambio: sin esto este .c no compilaba bajo kbuild, y por eso
 * no podia entrar en obj-m.  Con esto entra.  Ver finding 1023.
 */
#ifdef __KERNEL__
#include <linux/string.h>
#else
#include <string.h>
#endif

#include "rx550_vmid1_pgt.h"

/* ═══════════════════════════════════════════════════════════════════════════
 * PRIMITIVAS DE LA ARITMETICA DEL CORPUS
 *
 * Traducciones literales de lo que hace el kernel, para no depender de el.
 * Cada una lleva su procedencia, porque una de estas sin fuente seria una
 * suposicion con nombre de traduccion.
 * ═══════════════════════════════════════════════════════════════════════════ */

/* amdgpu_vm.c:2439  usa fls64().
 *
 * fls64() en el kernel es la posicion, contada desde UNO, del bit mas alto.
 * ilog2(v) == fls64(v) - 1.  La relacion se deja explicita porque aqui es
 * donde se puede colar un error de uno, y un error de uno en este punto no da
 * un fallo visible:  cambia block_size de 9 a 8, la cobertura se reduce a
 * 256 MiB, y la geometria que sale es coherente consigo misma y falsa.
 *
 * Se usa __builtin_clzll y no un bucle porque el bucle tiene un borde dificil
 * de ver y el builtin no.  Un bucle con "while (v >>= 1) n++;" devuelve
 * ilog2(v), NO fls64(v), y esa confusion es exactamente la que se corrigio
 * aqui. */
static uint32_t rx550_fls64(uint64_t v)
{
	if (!v)
		return 0;
	return 64u - (uint32_t)__builtin_clzll(v);
}

/* el DIV_ROUND_UP() del kernel */
static uint64_t rx550_div_round_up(uint64_t n, uint64_t d)
{
	return (n + d - 1) / d;
}

/* el roundup_pow_of_two() del kernel.  amdgpu_vm.c:2436 */
static uint64_t rx550_roundup_pow2(uint64_t v)
{
	if (v <= 1)
		return 1;
	return UINT64_C(1) << (64 - __builtin_clzll(v - 1));
}

/* amdgpu_vm.c:2368-2379  amdgpu_vm_get_block_size() */
static uint32_t rx550_get_block_size(uint64_t t)
{
	uint32_t bits = rx550_fls64(t) - 1u + 18u;	/* ilog2(t) + 18 */

	/* "Make sure the PD is 4K in size up to 8GB address space.
	 *  Above that split equal between PD and PTs" */
	if (t <= 8)
		return bits - 9u;
	return (bits + 3u) / 2u;
}

/* ═══════════════════════════════════════════════════════════════════════════
 * GEOMETRIA
 * ═══════════════════════════════════════════════════════════════════════════ */

/*
 * rx550_vmid1_geometry — la unica forma de obtener una geometria.
 *
 * vm_size_bytes es la UNICA entrada.  Todo lo demas sale de aqui, y con esta
 * funcion de dentro no hay ningun valor que se pueda cambiar a mano sin
 * romper la coherencia entre el numero de entradas, el tamano de la pagina y
 * la cobertura.
 *
 * SECUENCIA, y es la del corpus en el mismo orden:
 *
 *   amdgpu_vm.c:2433   max_pfn = vm_size << 18
 *   amdgpu_vm.c:2436   tmp = roundup_pow_of_two(max_pfn)
 *   amdgpu_vm.c:2439   tmp = DIV_ROUND_UP(fls64(tmp) - 1, 9) - 1
 *   amdgpu_vm.c:2440   num_level = min(max_level, tmp)
 *   amdgpu_vm.c:2466   block_size = get_block_size(tmp)
 *
 * con max_level = 1, porque eso es lo que pasa GFX8 en gmc_v8_0.c:1127.
 *
 * PARA vm_size = 1 GiB:
 *   max_pfn    = 1 << 18 = 262144
 *   tmp        = 262144
 *   tmp        = DIV_ROUND_UP(19 - 1, 9) - 1 = DIV_ROUND_UP(18, 9) - 1 = 1
 *   num_level  = min(1, 1) = 1
 *   block_size = get_block_size(1) = (ilog2(1) + 18) - 9 = 9
 *   entradas   = 2^9 = 512
 *   cobertura  = 2^9 * 2^9 * 2^12 = 2^30 = 1 GiB
 */
int rx550_vmid1_geometry(uint64_t vm_size_bytes, struct rx550_vmid1_geom *out)
{
	uint64_t max_pfn;
	uint64_t tmp;
	uint64_t lvl_seed;
	uint32_t num_level;
	uint32_t block_size;
	uint32_t entries;
	uint64_t coverage;

	if (!out)
		return RX550_PGT_ERR_INCONSISTENT;

	memset(out, 0, sizeof(*out));
	out->root_type = RX550_ROOT_UNSET;

	if (vm_size_bytes == 0)
		return RX550_PGT_ERR_VM_SIZE;

	/* La ventana tiene que ser multiplo de la pagina.  No se redondea:  una
	 * ventana que no cae en la granularidad no es una ventana, y aceptarla
	 * obligaria a truncar en algun punto, que es la clase de fallo que este
	 * proyecto rechaza en todas partes. */
	if (vm_size_bytes % RX550_VMID1_PAGE_SIZE)
		return RX550_PGT_ERR_VM_SIZE;

	/* amdgpu_vm.c:2433.  El desplazamiento se hace sobre el numero de GiB,
	 * igual que el corpus, y por eso se comprueba que no se desborde. */
	if (vm_size_bytes > (UINT64_MAX >> 18) << 12)
		return RX550_PGT_ERR_OVERFLOW;
	max_pfn = vm_size_bytes >> RX550_VMID1_PAGE_SHIFT;

	/* amdgpu_vm.c:2436 */
	tmp = rx550_roundup_pow2(max_pfn);
	if (!tmp)
		return RX550_PGT_ERR_OVERFLOW;

	/*
	 * amdgpu_vm.c:2439
	 *   tmp = DIV_ROUND_UP(fls64(tmp) - 1, 9) - 1;
	 *
	 * El corpus evalua esto en ENTEROS CON SIGNO, porque fls64() devuelve int
	 * y DIV_ROUND_UP es una macro de int.  Para una ventana grande da un
	 * entero sin problema.  Para una ventana minima —max_pfn == 1— da
	 * DIV_ROUND_UP(0, 9) - 1 == -1, que al pasarlo a un tmp sin signo se
	 * convierte en un numero enorme.
	 *
	 * El corpus no lo alcanza porque max_pfn siempre es grande en la practica.
	 * Aqui SI se alcanza, porque la API acepta cualquier vm_size y no debe
	 * dejar que un -1 se convierta en 2^64-1.  Por eso el intermedio es con
	 * signo y hay una guarda explicita, en vez de clonar el UNDERFLOW.
	 */
	{
		int64_t seed = (int64_t)rx550_fls64(tmp) - 1;
		int64_t level;

		if (seed < 0)
			return RX550_PGT_ERR_VM_SIZE_INCOHERENT;
		level = (int64_t)rx550_div_round_up((uint64_t)seed, 9u) - 1;
		if (level < 0)
			return RX550_PGT_ERR_VM_SIZE_INCOHERENT;

		/* amdgpu_vm.c:2440, con max_level de gmc_v8_0.c:1127 */
		{
			int64_t cap = (int64_t)RX550_VMID1_MAX_LEVEL;

			num_level = (uint32_t)((level > cap) ? cap : level);
		}

		/* El valor que el corpus pasa a amdgpu_vm_get_block_size().  Con
		 * la guarda de arriba nunca es negativo. */
		lvl_seed = (uint64_t)level;
	}

	/* amdgpu_vm.c:2454-2455.  num_level == 0 es un dev_err en el corpus, y
	 * no se "soporta" aqui:  se rechaza con un codigo propio. */
	if (num_level == 0)
		return RX550_PGT_ERR_UNSUPPORTED_LEVEL;
	if (num_level != 1)
		return RX550_PGT_ERR_UNSUPPORTED_LEVEL;

	/* amdgpu_vm.c:2463-2466.  Con num_level == 1 se llama a get_block_size,
	 * y no se usa el 9 fijo de la rama de arriba. */
	block_size = rx550_get_block_size(lvl_seed);

	/*
	 * RANGO DE block_size, Y POR QUE NO ES "SOLO EL DEMOSTRADO"
	 *
	 * La primera version de este modulo aceptaba unicamente block_size == 9,
	 * con el argumento de que 9 es el unico que el corpus escribe en GFX8.
	 * Ese argumento era mas fuerte de lo que la evidencia sostiene, y por eso
	 * la guarda se ha sustituido por una que se puede derivar del registro.
	 *
	 * LO QUE SE SABE DE CADA VALOR
	 *
	 *   block_size 9   DEMONSTRADO_EN_GFX8
	 *                  gmc_v8_0.c:933-934, la unica escritura de
	 *                  PAGE_TABLE_BLOCK_SIZE en todo el fichero
	 *
	 *   block_size 10  COMPUTADO_POR_LA_ARITMETICA_Y_CODIFICABLE
	 *                  amdgpu_vm.c:2375-2376 lo produce para ventana de 2 GiB
	 *                  gmc_8_2_sh_mask.h  el campo son 4 bits en el shift 24,
	 *                  y el corpus escribe block_size - 9, luego el rango
	 *                  codificable es [9, 24] y 10 cabe con el valor 1
	 *                  NO ESCRIBE_EN_GFX8   y eso se declara, no se disimula
	 *
	 * ASI QUE LA GUARDA ES EL RANGO DEL CAMPO, no el valor que el corpus
	 * llega a usar.  Y con ella, una ventana de 2 o 4 GiB produce una raiz
	 * de 8 KiB, que es lo que la geometria dice y no un literal.
	 *
	 * Y EL PRECIO, DICHO:  con block_size 10 la raiz ocupa DOS paginas de
	 * 4 KiB, luego el backing de la raiz tiene que ser UN bloque contiguo
	 * de root_bytes.  Es la unica contiguidad que el hardware exige en todo
	 * este subsistema, y por eso la exige el root y no las hojas.
	 */
	if (block_size < RX550_VMID1_BLOCK_SIZE_MIN
	    || block_size > RX550_VMID1_BLOCK_SIZE_MAX)
		return RX550_PGT_ERR_UNSUPPORTED_BLOCK_SIZE;

	entries = 1u << block_size;

	/* amdgpu_vm.c:2433  END = max_pfn - 1, y gmc_v8_0.c:909 lo escribe. */
	out->vm_size_bytes	= vm_size_bytes;
	out->num_level		= num_level;
	/* amdgpu_vm.c:2451-2452  num_level 1 -> root_level = AMDGPU_VM_PDB0 */
	out->root_type		= RX550_ROOT_PDB0;
	out->block_size		= block_size;
	/* gfxhub_v1_0.c:267-268  PAGE_TABLE_DEPTH = num_level */
	out->depth_field	= num_level;
	/* gmc_v8_0.c:933-934  PAGE_TABLE_BLOCK_SIZE = block_size - 9 */
	out->block_size_field	= block_size - 9u;
	out->entries_per_level	= entries;
	out->level_bytes	= (uint64_t)entries * RX550_VMID1_ENTRY_BYTES;
	out->pte_pages		= entries;
	out->pte_entries	= entries;
	out->root_bytes		= out->level_bytes;
	out->pte_page_bytes	= out->level_bytes;
	/* El rango que camina el hardware:  block_size bits de indice de PDE,
	 * block_size de indice de PTE, y PAGE_SHIFT de pagina. */
	coverage = ((uint64_t)entries * (uint64_t)entries)
		   << RX550_VMID1_PAGE_SHIFT;
	out->coverage_bytes	= coverage;
	out->start_pn		= 0;
	out->end_pn		= (uint32_t)((coverage >> RX550_VMID1_PAGE_SHIFT) - 1u);
	out->total_bytes	= out->root_bytes
				   + (uint64_t)out->pte_pages * out->pte_page_bytes;

	/* La geometria que sale de la aritmetica tiene que COBRIR la ventana
	 * pedida.  Y el fallo peligroso es solo uno de los dos sentidos:
	 *
	 *   coverage <  vm_size   INCOHERENTE Y SILENCIOSO
	 *     el hardware camina fuera de la tabla, la traduccion cae en la
	 *     pagina dummy, y el sintoma es que la parte alta de la ventana no
	 *     traduce.  Sin error, sin cuelgue.  Esto se rechaza.
	 *
	 *   coverage >= vm_size   CORRECTO, Y CON HOLGURA
	 *     una ventana de 2 GiB con block_size 10 da una cobertura de 4 GiB:
	 *     la tabla es MAS grande que la ventana.  Eso no es un defecto, es
	 *     desperdicio de memoria, y el rango que se traduce lo acotan
	 *     START y END, que son una decision de M6 y no de la geometria.
	 *
	 * La primera version rechazaba tambien el exceso, con lo que 2 GiB y
	 * 4 GiB quedaban fuera.  Era una guarda MAS fuerte de lo que la
	 * evidencia necesita, y por eso se ha reducido a la direccion que
	 * importa.  Un rechazo que no tiene un modo de fallo detras es un
	 * rechazo que acaba poniendose en el camino de lo valido.
	 */
	if (coverage < vm_size_bytes)
		return RX550_PGT_ERR_VM_SIZE_INCOHERENT;

	out->valid = true;
	return RX550_PGT_OK;
}

/* ═══════════════════════════════════════════════════════════════════════════
 * VALIDADORES DE DIRECCION
 *
 * DOS, y no uno.  Ver la cabecera:  el root es un numero de pagina de 28
 * bits y una hoja es una direccion en el campo 39:1.  El tope en bytes de los
 * dos coincide, pero los ENCODINGS no, y confundirlos rechaza direcciones
 * validas.
 * ═══════════════════════════════════════════════════════════════════════════ */

/*
 * root: 28 bits de NUMERO DE PAGINA.
 *   2^28 paginas * 4 KiB = 2^40 bytes.
 *   Y la alineacion a 4 KiB es obligatoria, porque el valor que se programa
 *   es (bus >> 12):  sin alinear, el shift perderia los bits bajos.
 */
bool rx550_vmid1_root_representable(uint64_t root_bus)
{
	if (root_bus % RX550_VMID1_PAGE_SIZE)
		return false;
	return (uint32_t)(root_bus >> RX550_VMID1_PAGE_SHIFT)
	       <= RX550_PT_BASE_PN_MASK;
}

/*
 * hoja: el campo 39:1 del PDE, que es una DIRECCION en bytes.
 *   gmc_v8_0.c:715  BUG_ON(*addr & 0xFFFFFF0000000FFFULL)
 * que son las mismas dos condiciones:  4 KiB alineada, y nada por encima del
 * bit 39.
 *
 * Y ESTA NO USA EL LIMITE DE 28 BITS, A PROPOSITO.  Una hoja en 8 GiB ocupa 33
 * bits como direccion:  un chequeo de 28 bits sobre el valor crudo la
 * rechazaria, y es una direccion perfectamente valida.  El limite de 28 bits
 * es del numero de pagina del root, y no es un limite universal de direcciones.
 */
bool rx550_vmid1_leaf_representable(uint64_t leaf_bus)
{
	if (leaf_bus & RX550_PDE_ADDR_PRECOND_MASK)
		return false;
	return (leaf_bus & ~RX550_PDE_ADDR_MASK) == 0;
}

/* El numero de pagina del root, RECHAZANDO lo que no cabe.  Nunca trunca. */
int rx550_vmid1_root_base_pn(uint64_t root_bus, uint32_t *out_pn)
{
	if (!out_pn)
		return RX550_PGT_ERR_INCONSISTENT;
	if (!rx550_vmid1_root_representable(root_bus))
		return RX550_PGT_ERR_ROOT_UNREPRESENTABLE;
	*out_pn = (uint32_t)(root_bus >> RX550_VMID1_PAGE_SHIFT);
	return RX550_PGT_OK;
}

/* ═══════════════════════════════════════════════════════════════════════════
 * ENCODER DE PDE
 *
 * NO es rx550_pte_encode(), y NO es el encoding de rx550_pdb0.h.  Vease la
 * cabecera para por que la confusion no da un error sino una traduccion.
 * ═══════════════════════════════════════════════════════════════════════════ */

/*
 * rx550_vmid1_pde_encode — construye la entrada de directorio.
 *
 *   gmc_v8_0.c:707   39:1  physical base address of PTE
 *   gmc_v8_0.c:708         bits 5:1 must be 0
 *   gmc_v8_0.c:709   0     valid
 *   gmc_v8_0.c:705   63:59 block fragment size   -> cero, ver la cabecera
 *
 * El campo es UN numero de pagina que empieza en el bit 1, de modo que la
 * direccion se recupera como (campo << 1).  Escribir la direccion tal cual en
 * los bits 39:1 seria un error de uno:  desplazaria la direccion una pagina.
 */
int rx550_vmid1_pde_encode(uint64_t pte_page_bus, uint64_t *out_pde)
{
	uint64_t field;
	uint64_t pde;

	if (!out_pde)
		return RX550_PGT_ERR_INCONSISTENT;

	/* gmc_v8_0.c:715, las dos mitades del BUG_ON. */
	if (pte_page_bus % RX550_VMID1_PAGE_SIZE)
		return RX550_PGT_ERR_LEAF_UNALIGNED;
	if (!rx550_vmid1_leaf_representable(pte_page_bus))
		return RX550_PGT_ERR_LEAF_UNREPRESENTABLE;

	/* La direccion va en 39:1.  Se hace (bus >> 1) y se coloca en el bit 1,
	 * que es lo mismo que dejar el bit 0 para VALID. */
	field = (pte_page_bus >> RX550_PDE_ADDR_SHIFT) & RX550_PDE_FIELD_MASK;

	pde = (field << RX550_PDE_ADDR_SHIFT) | RX550_PDE_VALID_MASK;

	/* 63:59 a cero por politica declarada, no por suposicion.  Y no se hace
	 * nada con 58:40:  se quedan a cero porque nunca se escriben, y
	 * rx550_vmid1_pde_check() lo comprueba. */
	pde &= ~RX550_PDE_FRAG_MASK;
	pde &= ~RX550_PDE_RESERVED_MASK;

	*out_pde = pde;
	return RX550_PGT_OK;
}

/* La direccion de la pagina PTE que apunta un PDE.  Sin validacion:  es un
 * lector, y el que decide si el PDE es utilizable es pde_check().
 *
 * Y AQUI ESTA LA ASIMETRIA CON EL ENCODER, que es donde se puede ir mal:
 *
 *   encode  el campo es un valor de 39 bits en bits 0..38, y se COLOCA
 *           desplazandolo una posicion
 *   decode  el campo ya esta colocado en 39:1, y por eso se lee con la
 *           mascara PLACED y SIN desplazar
 *
 * Enmascarar con FIELD_MASK y luego desplazar, que es lo que parece obvio,
 * desplaza DOS veces y devuelve el doble de la direccion.  Y no da un error
 * visible:  devuelve un numero con la forma correcta.
 */
uint64_t rx550_vmid1_pde_decode(uint64_t pde)
{
	return pde & RX550_PDE_FIELD_PLACED_MASK;
}

/*
 * Un PDE es utilizable si no tiene residuo:  VALID a 1, 58:40 a cero, 63:59 a
 * cero, y el campo de direccion con los bits 5:1 a cero —lo que exige que la
 * pagina destino este alineada a 4 KiB, gmc_v8_0.c:708.
 *
 * Los bits 5 y 6 no se comprueban por separado porque DENTRO del campo de
 * direccion no significan permiso:  son parte de la direccion.  Esa es la
 * razon por la que un PDE con 5 y 6 a uno no es "un PDE con permisos", es un
 * PDE que apunta a otra pagina.
 */
bool rx550_vmid1_pde_check(uint64_t pde)
{
	uint64_t addr;

	if (!(pde & RX550_PDE_VALID_MASK))
		return false;
	if (pde & RX550_PDE_RESERVED_MASK)
		return false;
	if (pde & RX550_PDE_FRAG_MASK)
		return false;

	addr = rx550_vmid1_pde_decode(pde);
	if (!rx550_vmid1_leaf_representable(addr))
		return false;
	return true;
}

/* ═══════════════════════════════════════════════════════════════════════════
 * ROOT  —  ENGANCHE Y LIMPIEZA
 * ═══════════════════════════════════════════════════════════════════════════ */

int rx550_vmid1_root_attach(struct rx550_vmid1_root *root,
			    const struct rx550_vmid1_geom *g,
			    uint64_t *entries, uint64_t root_bus)
{
	if (!root || !g || !entries)
		return RX550_PGT_ERR_INCONSISTENT;
	if (!g->valid)
		return RX550_PGT_ERR_INCONSISTENT;
	if (g->root_type != RX550_ROOT_PDB0)
		return RX550_PGT_ERR_UNSUPPORTED_LEVEL;

	memset(root, 0, sizeof(*root));

	/* Se valida la direccion ANTES de guardar nada, para que un root
	 * rechazado no deje un objeto con medio initialize. */
	if (!rx550_vmid1_root_representable(root_bus))
		return RX550_PGT_ERR_ROOT_UNREPRESENTABLE;

	root->entries	= entries;
	root->bus	= root_bus;
	root->bytes	= g->root_bytes;
	root->count	= g->entries_per_level;
	root->attached	= true;
	root->cleared	= false;
	return RX550_PGT_OK;
}

/*
 * Todas las entradas a cero.  Y CERO ES "NO VALIDA" POR CONSTRUCCION DEL
 * FORMATO, no por convencion:  el bit 0 es VALID en el PDE (gmc_v8_0.c:709) y
 * tambien en el PTE (gmc_v8_0.c:702).  Es la unica coincidencia entre los dos
 * formatos, y por eso el limpiado sirve para los dos niveles con el mismo
 * memset.
 */
int rx550_vmid1_root_clear(struct rx550_vmid1_root *root)
{
	if (!root)
		return RX550_PGT_ERR_INCONSISTENT;
	if (!root->attached || !root->entries)
		return RX550_PGT_ERR_INCONSISTENT;

	memset(root->entries, 0, (size_t)root->count * RX550_VMID1_ENTRY_BYTES);
	root->cleared = true;
	return RX550_PGT_OK;
}

/* ═══════════════════════════════════════════════════════════════════════════
 * PAGINA PTE  —  ENGANCHE Y LIMPIEZA
 *
 * Mismo contrato de backing externo, y la misma disciplina de validar antes
 * de guardar.  Lo que NO se hace aqui es codificar un PTE:  eso es de otro
 * modulo, que ya existe, y este no incluye su encoder a proposito.
 * ═══════════════════════════════════════════════════════════════════════════ */

int rx550_vmid1_pte_page_attach(struct rx550_vmid1_pte_page *page,
				const struct rx550_vmid1_geom *g,
				uint64_t *entries, uint64_t page_bus)
{
	if (!page || !g || !entries)
		return RX550_PGT_ERR_INCONSISTENT;
	if (!g->valid)
		return RX550_PGT_ERR_INCONSISTENT;

	memset(page, 0, sizeof(*page));

	if (page_bus % RX550_VMID1_PAGE_SIZE)
		return RX550_PGT_ERR_LEAF_UNALIGNED;
	if (!rx550_vmid1_leaf_representable(page_bus))
		return RX550_PGT_ERR_LEAF_UNREPRESENTABLE;

	page->entries	= entries;
	page->bus	= page_bus;
	page->bytes	= g->pte_page_bytes;
	page->count	= g->pte_entries;
	page->attached	= true;
	page->cleared	= false;
	return RX550_PGT_OK;
}

int rx550_vmid1_pte_page_clear(struct rx550_vmid1_pte_page *page)
{
	if (!page)
		return RX550_PGT_ERR_INCONSISTENT;
	if (!page->attached || !page->entries)
		return RX550_PGT_ERR_INCONSISTENT;

	memset(page->entries, 0, (size_t)page->count * RX550_VMID1_ENTRY_BYTES);
	page->cleared = true;
	return RX550_PGT_OK;
}

/* ═══════════════════════════════════════════════════════════════════════════
 * INDEXADO
 *
 * Funciones PURAS.  Y la unica fuente de verdad sobre donde cae una VA es la
 * geometria, de modo que el indice no puede quedar desincronizado del tamano
 * de la tabla.
 *
 * Con block_size 9 y PAGE_SHIFT 12:
 *   pde_index = (va >> 21) & 0x1FF   —  bits 29:21
 *   pte_index = (va >> 12) & 0x1FF   —  bits 20:12
 *
 * y entre los dos cubren los 18 bits de la VA dentro de la ventana, que es lo
 * que hace que la cobertura sea 2^30 y no un agujero.
 * ═══════════════════════════════════════════════════════════════════════════ */

/* El indice de la raiz, o RX550_PGT_ERR_VA_OUT_OF_RANGE si la VA no cae en la
 * ventana.  Se comprueba el rango ANTES de enmascarar, porque enmascarar hace
 * que 2 GiB se parezca a 0:  una comprobacion posterior al AND no ve el
 * desbordamiento. */
int rx550_vmid1_pde_index(const struct rx550_vmid1_geom *g, uint64_t va,
			  uint32_t *out_index)
{
	uint32_t mask;

	if (!g || !out_index)
		return RX550_PGT_ERR_INCONSISTENT;
	if (!g->valid)
		return RX550_PGT_ERR_INCONSISTENT;
	if (va >= g->coverage_bytes)
		return RX550_PGT_ERR_VA_OUT_OF_RANGE;

	mask = g->entries_per_level - 1u;
	*out_index = (uint32_t)(va >> (RX550_VMID1_PAGE_SHIFT + g->block_size))
		     & mask;
	return RX550_PGT_OK;
}

int rx550_vmid1_pte_index(const struct rx550_vmid1_geom *g, uint64_t va,
			  uint32_t *out_index)
{
	uint32_t mask;

	if (!g || !out_index)
		return RX550_PGT_ERR_INCONSISTENT;
	if (!g->valid)
		return RX550_PGT_ERR_INCONSISTENT;
	if (va >= g->coverage_bytes)
		return RX550_PGT_ERR_VA_OUT_OF_RANGE;

	mask = g->entries_per_level - 1u;
	*out_index = (uint32_t)(va >> RX550_VMID1_PAGE_SHIFT) & mask;
	return RX550_PGT_OK;
}

/* Los dos indices, con el rango comprobado una sola vez. */
int rx550_vmid1_locate(const struct rx550_vmid1_geom *g, uint64_t va,
		       uint32_t *out_pde_index, uint32_t *out_pte_index)
{
	int rc;

	if (!g || !out_pde_index || !out_pte_index)
		return RX550_PGT_ERR_INCONSISTENT;
	if (!g->valid)
		return RX550_PGT_ERR_INCONSISTENT;
	if (va >= g->coverage_bytes)
		return RX550_PGT_ERR_VA_OUT_OF_RANGE;

	rc = rx550_vmid1_pde_index(g, va, out_pde_index);
	if (rc != RX550_PGT_OK)
		return rc;
	return rx550_vmid1_pte_index(g, va, out_pte_index);
}

/* ═══════════════════════════════════════════════════════════════════════════
 * DIAGNOSTICO
 * ═══════════════════════════════════════════════════════════════════════════ */

const char *rx550_vmid1_err_str(int rc)
{
	switch (rc) {
	case RX550_PGT_OK:
		return "ok";
	case RX550_PGT_ERR_VM_SIZE:
		return "vm_size cero o no multiplo de la pagina";
	case RX550_PGT_ERR_OVERFLOW:
		return "la aritmetica de la geometria se desborda";
	case RX550_PGT_ERR_UNSUPPORTED_LEVEL:
		return "num_level distinto de 1: no demostrado para GFX8";
	case RX550_PGT_ERR_UNSUPPORTED_BLOCK_SIZE:
		return "block_size distinto de 9: no demostrado para GFX8";
	case RX550_PGT_ERR_VM_SIZE_INCOHERENT:
		return "la cobertura derivada no es la ventana pedida";
	case RX550_PGT_ERR_NO_BACKING:
		return "sin backing";
	case RX550_PGT_ERR_ROOT_UNALIGNED:
		return "root no alineado a 4 KiB";
	case RX550_PGT_ERR_ROOT_UNREPRESENTABLE:
		return "root no representable en 28 bits de numero de pagina";
	case RX550_PGT_ERR_LEAF_UNALIGNED:
		return "pagina PTE no alineada a 4 KiB";
	case RX550_PGT_ERR_LEAF_UNREPRESENTABLE:
		return "pagina PTE no representable en el campo 39:1";
	case RX550_PGT_ERR_INDEX_RANGE:
		return "indice fuera de las entradas del nivel";
	case RX550_PGT_ERR_VA_OUT_OF_RANGE:
		return "VA fuera de la ventana";
	case RX550_PGT_ERR_INCONSISTENT:
		return "parametros inconsistentes";
	default:
		return "error desconocido";
	}
}

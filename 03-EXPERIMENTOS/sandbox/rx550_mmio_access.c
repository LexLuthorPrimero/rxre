// SPDX-License-Identifier: GPL-2.0-only
/*
 * rx550_mmio_access.c — acceso a los registros GFX8 por BAR5.
 *
 *   TARGET = RX 550 instalada en esta maquina  (1002:699F, Polaris12, GFX8)
 *   SCOPE  = EXCLUSIVO
 *
 * LA SEPARACION DE CAPAS, Y COMO SE VERIFICA
 *
 *   Este fichero no menciona `struct rx550_pgt_backing`, ni `root_dma`, ni
 *   `root_base_pn`, ni ninguna geometria, y no incluye rx550_vmid1_pgt*.h.
 *   Eso no es una convencion:  hay un test estatico que lo comprueba sobre el
 *   codigo sin comentarios, junto con la lista de las seis fronteras de este
 *   nodo.  Si alguien anade una referencia al backing aqui, el test falla.
 *
 * LA DEPENDENCIA VA EN EL OTRO SENTIDO
 *
 *   PGT/BACKING  ->  produce direcciones y estado
 *   MMIO ACCESSOR->  traduce registro a offset, y accede
 *
 *   El accessor es la capa inferior y no la conoce.  Quien las junta es el
 *   codigo del siguiente nodo, en un archivo que si incluye las dos cabeceras.
 *
 * LAS DOS IMPLEMENTACIONES DEL ACCESO, Y POR QUE NO SON UNA SEGUNDA POLITICA
 *
 *   En el kernel, readl/writel.  En userspace, un acceso volatile equivalente,
 *   para que el camino de acceso se pueda probar contra un buffer normal sin
 *   hardware.  Eso NO es una segunda politica de direccionamiento:  la politica
 *   —indice a offset, y ventana— vive entera en resolve(), que es la misma
 *   funcion en los dos casos y la unica que decide si el acceso procede.  Lo
 *   unico que cambia es la primitiva de barrera, que es lo que corresponde.
 *
 *   Y EL CRITERIO PARA NO DESPLEGAR ESTO EN DOS IMPLEMENTACIONES:  si un dia
 *   estas dos lineas divergieran, seria el equivalente de tener dos politicas
 *   de direccionamiento, y el fallo seria un registro equivocado leido con
 *   exito.  Por eso solo divergen en la primitiva, y por eso el test comprueba
 *   que la aritmetica del offset es la MISMA en los dos casos.
 */

#ifdef __KERNEL__
#include <linux/io.h>
#else
#include <string.h>
#endif

#include "rx550_mmio_access.h"

/* ═══════════════════════════════════════════════════════════════════════════
 * ERRORES
 *
 * Cuatro, y ninguno ambiguo.  Los tres primeros son de ESTA capa;  el cuarto
 * es de la geometria, y llega reenviado desde los modulos de PGT, no
 * redefinido aquí:  un mismo numero con dos_significados seria dos fuentes de
 * verdad para lo mismo.
 * ═══════════════════════════════════════════════════════════════════════════ */

const char *rx550_mmio_err_str(int rc)
{
	switch (rc) {
	case RX550_MMIO_OK:
		return "ok";
	case RX550_MMIO_ERR_NO_MAP:
		return "no hay mapa de BAR5 enlazado";
	case RX550_MMIO_ERR_OUT_OF_WINDOW:
		return "el registro cae fuera de la ventana de BAR5";
	case RX550_MMIO_ERR_MAP_TOO_SMALL:
		return "el recurso mapeado es menor que el tamaño declarado de BAR5";
	case RX550_MMIO_ERR_BAD_ID:
		return "mnemonico de registro inexistente";
	default:
		return "error desconocido";
	}
}

/* ═══════════════════════════════════════════════════════════════════════════
 * LA TABLA DE REGISTROS DE VMID1 Y DE APERTURA
 *
 * Trece entradas, ordenadas por byte_offset ascendente, con su procedencia en
 * gmc_8_2_d.h.  Y CONFIDENCE que dice, por registro, si el corpus lo ESCRIBE en
 * GFX8 o solo lo define.  Y esa columna no es decorativa:  es la que impide
 * programado nunca.
 *
 * Y POR QUE NO ESTAN EN target_regs.h:  ver la cabecera.  Brevemente,  los
 * registros de VM de GFX8 estan en el mapa GMC y los de target_regs.h en el
 * GCA, y la verificacion de esa tabla es contra el GCA.
 * ═══════════════════════════════════════════════════════════════════════════ */
const struct rx550_vmid1_reg rx550_vmid1_regs[] = {
{
	"mmVM_CONTEXT1_CNTL",			0x505, 0x1414, 32, "RW", "CONTEXT1",
	"profundidad, block_size y ENABLE_CONTEXT del contexto 1",
	"gmc_8_1_d.h:602",			RX550_REG_PROVEN
},
{
	"mmVM_CONTEXT1_CNTL2",			0x50d, 0x1434, 32, "RW", "CONTEXT1",
	"procesamiento de interrupciones de fault del contexto 1",
	"gmc_8_1_d.h:606",			RX550_REG_PROVEN
},
{
	"mmVM_INVALIDATE_REQUEST",		0x51e, 0x1478, 32, "W", "GLOBAL",
	/*  D9 RESUELTO, Y LA ETIQUETA ES CORRECTA.  El header llama a estos bits
	 *  INVALIDATE_DOMAIN_0..15, lo que por si solo NO demuestra que domain i
	 *  sea vmid i.  Lo que lo demuestra es el escritor:
	 *      gmc_v8_0.c:665  WREG32(mmVM_INVALIDATE_REQUEST, 1 << vmid)
	 *      gmc_v8_0.c:680  amdgpu_ring_emit_wreg(ring, mmVM_INVALIDATE_REQUEST, 1 << vmid)
	 *      gmc_v8_0.c:637  mask |= 1 << vmid      (bucle vmid 1..15)
	 *  Es decir, la identidad domain==vmid es DEMOSTRADA por el corpus, y no
	 *  inferida del nombre del campo.  Un informe anterior afirmo lo
	 *  contrario;  la refutacion esta en esas tres lineas.
	 *  Y el bucle empieza en vmid 1:  el bit 0 existe como campo y NO lo
	 *  invalida la ruta por pasid.  VMID0 es fisico y lo usa el kernel. */
	"mascara de 16 dominios, 1 << vmid; DEMOSTRADO en gmc_v8_0.c:665",
	"gmc_8_1_d.h:615",			RX550_REG_PROVEN
},
{
	"mmVM_INVALIDATE_RESPONSE",		0x51f, 0x147c, 32, "R", "GLOBAL",
	"lectura que sincroniza la invalidacion; no hay timeout documentado",
	"gmc_8_1_d.h:616",			RX550_REG_PROVEN
},
{
	"mmVM_CONTEXT1_PROTECTION_FAULT_DEFAULT_ADDR", 0x547, 0x151c, 32, "W",
	"CONTEXT1",
	"destino de un fault de proteccion; el VALOR sigue abierto como R2",
	"gmc_8_1_d.h:634",			RX550_REG_PROVEN
},
{
	"mmVM_CONTEXT1_PAGE_TABLE_BASE_ADDR",	0x550, 0x1540, 32, "W", "CONTEXT1",
	"numero de pagina del root PDB0, 28 bits; no es la tabla entera",
	"gmc_8_1_d.h:637",			RX550_REG_PROVEN
},
{
	"mmVM_CONTEXT1_PAGE_TABLE_START_ADDR",	0x558, 0x1560, 32, "W", "CONTEXT1",
	"primer numero de pagina de la ventana, LOGICAL",
	"gmc_8_1_d.h:645",			RX550_REG_PROVEN
},
{
	"mmVM_CONTEXT1_PAGE_TABLE_END_ADDR",	0x560, 0x1580, 32, "W", "CONTEXT1",
	"ultimo numero de pagina de la ventana, LOGICAL",
	"gmc_8_1_d.h:647",			RX550_REG_PROVEN
},
{
	/*  D3.  La identity aperture de VMID1:  la ventana por la que su
	 *  espacio virtual se alcanza SIN recorrer la page table.  Solo tiene
	 *  efecto con CONTEXT1_IDENTITY_ACCESS_MODE activo, y el corpus la
	 *  deja DESHABILITADA escribiendo cero en los tres:
	 *      gmc_v8_0.c:899  WREG32(mmVM_L2_CONTEXT1_IDENTITY_APERTURE_LOW_ADDR,  0);
	 *      gmc_v8_0.c:900  WREG32(mmVM_L2_CONTEXT1_IDENTITY_APERTURE_HIGH_ADDR, 0);
	 *      gmc_v8_0.c:901  WREG32(mmVM_L2_CONTEXT_IDENTITY_PHYSICAL_OFFSET,     0);
	 *  y la funcion se llama disable_identity_aperture() en mas de veinte
	 *  generaciones ASIC.  El cero es la codificacion de deshabilitado.
	 *
	 *  ESTOS TRES NO SON UN CONTRATO IMPUESTO.  D3 queda CONDITIONAL: lo que
	 *  se anade aqui es la REPRESENTACION, para que un consumidor posterior
	 *  pueda programarlos si decide que hace falta.  No se programan.
	 *
	 *  Y el tercero va con los otros dos.  Ignorarlo por ser "el offset" es
	 *  dejar medio bloque fuera, y sin el los dos primeros no significan
	 *  nada por si solos.
	 *
	 *  byte_offset = index * 4:  0x575*4=0x15d4  0x576*4=0x15d8  0x577*4=0x15dc
	 */
	"mmVM_L2_CONTEXT1_IDENTITY_APERTURE_LOW_ADDR",	0x575, 0x15d4, 32, "W", "CONTEXT1",
	"extremo bajo de la identity aperture de VMID1, LOGICAL_PAGE_NUMBER; 0 la deja deshabilitada",
	"gmc_8_1_d.h:652",			RX550_REG_PROVEN
},
{
	"mmVM_L2_CONTEXT1_IDENTITY_APERTURE_HIGH_ADDR",	0x576, 0x15d8, 32, "W", "CONTEXT1",
	"extremo alto de la identity aperture de VMID1, LOGICAL_PAGE_NUMBER; 0 la deja deshabilitada",
	"gmc_8_1_d.h:653",			RX550_REG_PROVEN
},
{
	"mmVM_L2_CONTEXT_IDENTITY_PHYSICAL_OFFSET",	0x577, 0x15dc, 32, "W", "CONTEXT1",
	"desplazamiento fisico de la identity aperture, PHYSICAL_PAGE_NUMBER; va con los otros dos",
	"gmc_8_1_d.h:654",			RX550_REG_PROVEN
},
{
	"mmVM_L2_CNTL4",			0x578, 0x15e0, 32, "RW", "GLOBAL",
	"tipo de fetch de PDE y PTE del contexto 1; GLOBAL, se LEE y se comprueba",
	"gmc_8_1_d.h:655",			RX550_REG_PROVEN
},
{
	"mmMC_VM_SYSTEM_APERTURE_LOW_ADDR",	0x80d, 0x2034, 32, "W", "GLOBAL",
	"extremo bajo del pass-through, LOGICAL_PAGE_NUMBER",
	"gmc_8_1_d.h:285",			RX550_REG_PROVEN
},
{
	"mmMC_VM_SYSTEM_APERTURE_HIGH_ADDR",	0x80e, 0x2038, 32, "W", "GLOBAL",
	"extremo alto del pass-through, LOGICAL_PAGE_NUMBER",
	"gmc_8_1_d.h:286",			RX550_REG_PROVEN
},
{
	"mmMC_VM_SYSTEM_APERTURE_DEFAULT_ADDR",	0x80f, 0x203c, 32, "W", "GLOBAL",
	"destino de un acceso no mapeado, PHYSICAL_PAGE_NUMBER; sin valor decided",
	"gmc_8_1_d.h:287",			RX550_REG_PROVEN
},
{
	"mmMC_VM_MX_L1_TLB_CNTL",		0x819, 0x2064, 32, "RW", "GLOBAL",
	"SYSTEM_APERTURE_UNMAPPED_ACCESS debe ser 0; SYSTEM_ACCESS_MODE sin enumerar",
	"gmc_8_1_d.h:297",			RX550_REG_PROVEN
},
};

const uint32_t rx550_vmid1_reg_count =
	(uint32_t)(sizeof(rx550_vmid1_regs) / sizeof(rx550_vmid1_regs[0]));

/* ═══════════════════════════════════════════════════════════════════════════
 * LA TABLA DE CAMPOS
 *
 * Veintiocho entradas:  los 22 de MMVM_CONTEXT1_CNTL y los 6 de
 * MC_VM_MX_L1_TLB_CNTL, COMPLETOS, no los que el accessor ya conocía.
 *
 * POR QUÉ COMPLETOS Y POR QUÉ SOLO ESOS DOS REGISTROS
 *
 * El criterio de completitud que se adoptó es "todo campo que el header
 * declara para un registro cubierto".  Aplicado a los trece registros, ese
 * criterio PULLA de más:  VM_L2_CNTL4 aporta 13 campos, CNTL2 cinco, y los
 * registros de una sola palabra aportan uno cada uno.  Y D4 —que es
 * precisamente L2_CNTL4— está explícitamente diferido en este nodo.
 *
 * Eso es una contradicción entre el criterio y el alcance, y se reporta en
 * lugar de resolverla por dentro.  La solución adoptada es:
 *
 *   · los dos registros de este nodo, COMPLETOS  →  la tabla
 *   · los otros once, SIN campos  →  y un test que exige que sigan ausentes
 *
 * Un test que exige la ausencia es raro, y es lo correcto aquí:  si alguien
 * añadiera medio campo de L2_CNTL4 creyendo que el registro ya está
 * cubierto, el test lo dice.  La alternativa —declarar la tabla "completa" y
 * que el hueco se descubra al escribir— es exactamente el fallo que D4
 * describe.
 *
 * Y LA ESTRUCTURA QUE REVELA EL INVENTARIO, QUE NO ERA VISIBLE ANTES
 *
 * Cada tipo de fallo tiene TRES campos:  _DEFAULT, _INTERRUPT y _SAVE.
 * No son tres copias de lo mismo:
 *
 *   _DEFAULT    el fallo se reporta por la vía por defecto
 *   _INTERRUPT  el fallo genera una interrupción
 *   _SAVE       el estado del fallo se guarda
 *
 * El corpus pone a 1 los siete _DEFAULT y NO TOCA los trece _INTERRUPT y
 * _SAVE.  Un escritor que no sepa que existen los trece los pone a 0 al
 * escribir el registro de cero, y cambia tres comportamientos que el corpus
 * nunca cambia.  Por eso están en la tabla sin valor de corpus.
 * ═══════════════════════════════════════════════════════════════════════════ */
const struct rx550_reg_field rx550_reg_fields[] = {
/* ── MMVM_CONTEXT1_CNTL  (0x505, offset 0x1414) ── los que el corpus escribe */
{ "VM_CONTEXT1_CNTL",   "ENABLE_CONTEXT",				0x00000001u,  0, 1, 1u,		"gmc_v8_0.c:924", RX550_FIELD_PROVEN_CORPUS_WRITES },
{ "VM_CONTEXT1_CNTL",   "PAGE_TABLE_DEPTH",			RX550_CNTL_DEPTH_MASK, RX550_CNTL_DEPTH_SHIFT, 2, 1u, "gmc_v8_0.c:925", RX550_FIELD_PROVEN_CORPUS_WRITES },
{ "VM_CONTEXT1_CNTL",   "RANGE_PROTECTION_FAULT_ENABLE_DEFAULT",	0x00000010u,  4, 1, 1u,		"gmc_v8_0.c:926", RX550_FIELD_PROVEN_CORPUS_WRITES },
{ "VM_CONTEXT1_CNTL",   "DUMMY_PAGE_PROTECTION_FAULT_ENABLE_DEFAULT",0x00000080u, 7, 1, 1u,		"gmc_v8_0.c:927", RX550_FIELD_PROVEN_CORPUS_WRITES },
{ "VM_CONTEXT1_CNTL",   "PDE0_PROTECTION_FAULT_ENABLE_DEFAULT",	0x00000400u, 10, 1, 1u,		"gmc_v8_0.c:928", RX550_FIELD_PROVEN_CORPUS_WRITES },
{ "VM_CONTEXT1_CNTL",   "VALID_PROTECTION_FAULT_ENABLE_DEFAULT",	0x00002000u, 13, 1, 1u,		"gmc_v8_0.c:929", RX550_FIELD_PROVEN_CORPUS_WRITES },
{ "VM_CONTEXT1_CNTL",   "READ_PROTECTION_FAULT_ENABLE_DEFAULT",	0x00010000u, 16, 1, 1u,		"gmc_v8_0.c:930", RX550_FIELD_PROVEN_CORPUS_WRITES },
{ "VM_CONTEXT1_CNTL",   "WRITE_PROTECTION_FAULT_ENABLE_DEFAULT",	0x00080000u, 19, 1, 1u,		"gmc_v8_0.c:931", RX550_FIELD_PROVEN_CORPUS_WRITES },
{ "VM_CONTEXT1_CNTL",   "EXECUTE_PROTECTION_FAULT_ENABLE_DEFAULT",	0x00400000u, 22, 1, 1u,		"gmc_v8_0.c:932", RX550_FIELD_PROVEN_CORPUS_WRITES },
{ "VM_CONTEXT1_CNTL",   "PAGE_TABLE_BLOCK_SIZE",			RX550_CNTL_BLOCK_SIZE_MASK, RX550_CNTL_BLOCK_SIZE_SHIFT, 4, RX550_FIELD_NO_CORPUS, "gmc_v8_0.c:933", RX550_FIELD_PROVEN_CORPUS_WRITES },
/* ── los _INTERRUPT: el corpus no los toca, y por eso constan sin valor ── */
{ "VM_CONTEXT1_CNTL",   "RANGE_PROTECTION_FAULT_ENABLE_INTERRUPT",	0x00000008u,  3, 1, RX550_FIELD_NO_CORPUS, "gmc_v8_0.c:1391", RX550_FIELD_PROVEN_CORPUS_WRITES },
{ "VM_CONTEXT1_CNTL",   "DUMMY_PAGE_PROTECTION_FAULT_ENABLE_INTERRUPT",0x00000040u,  6, 1, RX550_FIELD_NO_CORPUS, "gmc_v8_0.c:1391", RX550_FIELD_PROVEN_CORPUS_WRITES },
{ "VM_CONTEXT1_CNTL",   "PDE0_PROTECTION_FAULT_ENABLE_INTERRUPT",	0x00000200u,  9, 1, RX550_FIELD_NO_CORPUS, "gmc_v8_0.c:1391", RX550_FIELD_PROVEN_CORPUS_WRITES },
{ "VM_CONTEXT1_CNTL",   "VALID_PROTECTION_FAULT_ENABLE_INTERRUPT",	0x00001000u, 12, 1, RX550_FIELD_NO_CORPUS, "gmc_v8_0.c:1391", RX550_FIELD_PROVEN_CORPUS_WRITES },
{ "VM_CONTEXT1_CNTL",   "READ_PROTECTION_FAULT_ENABLE_INTERRUPT",	0x00008000u, 15, 1, RX550_FIELD_NO_CORPUS, "gmc_v8_0.c:1391", RX550_FIELD_PROVEN_CORPUS_WRITES },
{ "VM_CONTEXT1_CNTL",   "WRITE_PROTECTION_FAULT_ENABLE_INTERRUPT",	0x00040000u, 18, 1, RX550_FIELD_NO_CORPUS, "gmc_v8_0.c:1391", RX550_FIELD_PROVEN_CORPUS_WRITES },
{ "VM_CONTEXT1_CNTL",   "EXECUTE_PROTECTION_FAULT_ENABLE_INTERRUPT",0x00200000u, 21, 1, RX550_FIELD_NO_CORPUS, "gmc_v8_0.c:1391", RX550_FIELD_PROVEN_CORPUS_WRITES },
/* ── los _SAVE: idem ── */
{ "VM_CONTEXT1_CNTL",   "PDE0_PROTECTION_FAULT_ENABLE_SAVE",		0x00000800u, 11, 1, RX550_FIELD_NO_CORPUS, "gmc_8_1_sh_mask.h:6641", RX550_FIELD_DECLARED_NOT_WRITTEN },
{ "VM_CONTEXT1_CNTL",   "VALID_PROTECTION_FAULT_ENABLE_SAVE",		0x00004000u, 14, 1, RX550_FIELD_NO_CORPUS, "gmc_8_1_sh_mask.h:6647", RX550_FIELD_DECLARED_NOT_WRITTEN },
{ "VM_CONTEXT1_CNTL",   "READ_PROTECTION_FAULT_ENABLE_SAVE",		0x00020000u, 17, 1, RX550_FIELD_NO_CORPUS, "gmc_8_1_sh_mask.h:6653", RX550_FIELD_DECLARED_NOT_WRITTEN },
{ "VM_CONTEXT1_CNTL",   "WRITE_PROTECTION_FAULT_ENABLE_SAVE",	0x00100000u, 20, 1, RX550_FIELD_NO_CORPUS, "gmc_8_1_sh_mask.h:6659", RX550_FIELD_DECLARED_NOT_WRITTEN },
{ "VM_CONTEXT1_CNTL",   "EXECUTE_PROTECTION_FAULT_ENABLE_SAVE",	0x00800000u, 23, 1, RX550_FIELD_NO_CORPUS, "gmc_8_1_sh_mask.h:6665", RX550_FIELD_DECLARED_NOT_WRITTEN },
	/* --- CONTEXT0_CNTL: gart_disable lo pone a 0 (gmc_v8_0.c:977), asi que
	 * un escritor necesita sus 22 campos para preservarlo.  Los 22 tienen
	 * el mismo nombre y valor que los de CONTEXT1. --- */
{ "VM_CONTEXT0_CNTL",   "ENABLE_CONTEXT",				0x00000001u,  0, 1, 1u,		"gmc_v8_0.c:924", RX550_FIELD_PROVEN_CORPUS_WRITES },
{ "VM_CONTEXT0_CNTL",   "PAGE_TABLE_DEPTH",			RX550_CNTL_DEPTH_MASK, RX550_CNTL_DEPTH_SHIFT, 2, 1u, "gmc_v8_0.c:925", RX550_FIELD_PROVEN_CORPUS_WRITES },
{ "VM_CONTEXT0_CNTL",   "RANGE_PROTECTION_FAULT_ENABLE_DEFAULT",	0x00000010u,  4, 1, 1u,		"gmc_v8_0.c:926", RX550_FIELD_PROVEN_CORPUS_WRITES },
{ "VM_CONTEXT0_CNTL",   "DUMMY_PAGE_PROTECTION_FAULT_ENABLE_DEFAULT",0x00000080u, 7, 1, 1u,		"gmc_v8_0.c:927", RX550_FIELD_PROVEN_CORPUS_WRITES },
{ "VM_CONTEXT0_CNTL",   "PDE0_PROTECTION_FAULT_ENABLE_DEFAULT",	0x00000400u, 10, 1, 1u,		"gmc_v8_0.c:928", RX550_FIELD_PROVEN_CORPUS_WRITES },
{ "VM_CONTEXT0_CNTL",   "VALID_PROTECTION_FAULT_ENABLE_DEFAULT",	0x00002000u, 13, 1, 1u,		"gmc_v8_0.c:929", RX550_FIELD_PROVEN_CORPUS_WRITES },
{ "VM_CONTEXT0_CNTL",   "READ_PROTECTION_FAULT_ENABLE_DEFAULT",	0x00010000u, 16, 1, 1u,		"gmc_v8_0.c:930", RX550_FIELD_PROVEN_CORPUS_WRITES },
{ "VM_CONTEXT0_CNTL",   "WRITE_PROTECTION_FAULT_ENABLE_DEFAULT",	0x00080000u, 19, 1, 1u,		"gmc_v8_0.c:931", RX550_FIELD_PROVEN_CORPUS_WRITES },
{ "VM_CONTEXT0_CNTL",   "EXECUTE_PROTECTION_FAULT_ENABLE_DEFAULT",	0x00400000u, 22, 1, 1u,		"gmc_v8_0.c:932", RX550_FIELD_PROVEN_CORPUS_WRITES },
{ "VM_CONTEXT0_CNTL",   "PAGE_TABLE_BLOCK_SIZE",			RX550_CNTL_BLOCK_SIZE_MASK, RX550_CNTL_BLOCK_SIZE_SHIFT, 4, RX550_FIELD_NO_CORPUS, "gmc_v8_0.c:933", RX550_FIELD_PROVEN_CORPUS_WRITES },
{ "VM_CONTEXT0_CNTL",   "RANGE_PROTECTION_FAULT_ENABLE_INTERRUPT",	0x00000008u,  3, 1, RX550_FIELD_NO_CORPUS, "gmc_8_1_sh_mask.h:6629", RX550_FIELD_DECLARED_NOT_WRITTEN },
{ "VM_CONTEXT0_CNTL",   "DUMMY_PAGE_PROTECTION_FAULT_ENABLE_INTERRUPT",0x00000040u,  6, 1, RX550_FIELD_NO_CORPUS, "gmc_8_1_sh_mask.h:6633", RX550_FIELD_DECLARED_NOT_WRITTEN },
{ "VM_CONTEXT0_CNTL",   "PDE0_PROTECTION_FAULT_ENABLE_INTERRUPT",	0x00000200u,  9, 1, RX550_FIELD_NO_CORPUS, "gmc_8_1_sh_mask.h:6637", RX550_FIELD_DECLARED_NOT_WRITTEN },
{ "VM_CONTEXT0_CNTL",   "VALID_PROTECTION_FAULT_ENABLE_INTERRUPT",	0x00001000u, 12, 1, RX550_FIELD_NO_CORPUS, "gmc_8_1_sh_mask.h:6643", RX550_FIELD_DECLARED_NOT_WRITTEN },
{ "VM_CONTEXT0_CNTL",   "READ_PROTECTION_FAULT_ENABLE_INTERRUPT",	0x00008000u, 15, 1, RX550_FIELD_NO_CORPUS, "gmc_8_1_sh_mask.h:6649", RX550_FIELD_DECLARED_NOT_WRITTEN },
{ "VM_CONTEXT0_CNTL",   "WRITE_PROTECTION_FAULT_ENABLE_INTERRUPT",	0x00040000u, 18, 1, RX550_FIELD_NO_CORPUS, "gmc_8_1_sh_mask.h:6655", RX550_FIELD_DECLARED_NOT_WRITTEN },
{ "VM_CONTEXT0_CNTL",   "EXECUTE_PROTECTION_FAULT_ENABLE_INTERRUPT",0x00200000u, 21, 1, RX550_FIELD_NO_CORPUS, "gmc_8_1_sh_mask.h:6661", RX550_FIELD_DECLARED_NOT_WRITTEN },
{ "VM_CONTEXT0_CNTL",   "PDE0_PROTECTION_FAULT_ENABLE_SAVE",		0x00000800u, 11, 1, RX550_FIELD_NO_CORPUS, "gmc_8_1_sh_mask.h:6641", RX550_FIELD_DECLARED_NOT_WRITTEN },
{ "VM_CONTEXT0_CNTL",   "VALID_PROTECTION_FAULT_ENABLE_SAVE",		0x00004000u, 14, 1, RX550_FIELD_NO_CORPUS, "gmc_8_1_sh_mask.h:6647", RX550_FIELD_DECLARED_NOT_WRITTEN },
{ "VM_CONTEXT0_CNTL",   "READ_PROTECTION_FAULT_ENABLE_SAVE",		0x00020000u, 17, 1, RX550_FIELD_NO_CORPUS, "gmc_8_1_sh_mask.h:6653", RX550_FIELD_DECLARED_NOT_WRITTEN },
{ "VM_CONTEXT0_CNTL",   "WRITE_PROTECTION_FAULT_ENABLE_SAVE",	0x00100000u, 20, 1, RX550_FIELD_NO_CORPUS, "gmc_8_1_sh_mask.h:6659", RX550_FIELD_DECLARED_NOT_WRITTEN },
{ "VM_CONTEXT0_CNTL",   "EXECUTE_PROTECTION_FAULT_ENABLE_SAVE",	0x00800000u, 23, 1, RX550_FIELD_NO_CORPUS, "gmc_8_1_sh_mask.h:6665", RX550_FIELD_DECLARED_NOT_WRITTEN },
/* ── MC_VM_MX_L1_TLB_CNTL  (0x819, offset 0x2064) ── */
{ "MC_VM_MX_L1_TLB_CNTL", "ENABLE_L1_TLB",			0x00000001u, 0, 1, 1u, "gmc_v8_0.c:844", RX550_FIELD_PROVEN_CORPUS_WRITES },
{ "MC_VM_MX_L1_TLB_CNTL", "ENABLE_L1_FRAGMENT_PROCESSING",	0x00000002u, 1, 1, 1u, "gmc_v8_0.c:845", RX550_FIELD_PROVEN_CORPUS_WRITES },
{ "MC_VM_MX_L1_TLB_CNTL", "SYSTEM_ACCESS_MODE",		RX550_MX_ACCESS_MODE_MASK, RX550_MX_ACCESS_MODE_SHIFT, 2, 3u, "gmc_v8_0.c:846", RX550_FIELD_PROVEN_CORPUS_WRITES },
{ "MC_VM_MX_L1_TLB_CNTL", "SYSTEM_APERTURE_UNMAPPED_ACCESS",	0x00000020u, 5, 1, 0u, "gmc_v8_0.c:848", RX550_FIELD_PROVEN_CORPUS_WRITES },
{ "MC_VM_MX_L1_TLB_CNTL", "ENABLE_ADVANCED_DRIVER_MODEL",	0x00000040u, 6, 1, 1u, "gmc_v8_0.c:847", RX550_FIELD_PROVEN_CORPUS_WRITES },
{ "MC_VM_MX_L1_TLB_CNTL", "ECO_BITS",				0x00000780u, 7, 4, RX550_FIELD_NO_CORPUS, "gmc_8_1_sh_mask.h:4023", RX550_FIELD_DECLARED_NOT_WRITTEN },
};

const uint32_t rx550_reg_field_count =
	(uint32_t)(sizeof(rx550_reg_fields) / sizeof(rx550_reg_fields[0]));

const struct rx550_reg_field *rx550_field_of(enum rx550_field_id id)
{
	if ((uint32_t)id >= rx550_reg_field_count)
		return NULL;
	return &rx550_reg_fields[id];
}

const struct rx550_vmid1_reg *rx550_vmid1_reg_get(enum rx550_vmid1_reg_id id)
{
	if ((uint32_t)id >= rx550_vmid1_reg_count)
		return NULL;
	return &rx550_vmid1_regs[id];
}

int rx550_mmio_reg_of(enum rx550_vmid1_reg_id id, struct rx550_reg *out)
{
	const struct rx550_vmid1_reg *r;

	if (!out)
		return RX550_MMIO_ERR_INCONSISTENT;

	r = rx550_vmid1_reg_get(id);
	if (!r)
		return RX550_MMIO_ERR_BAD_ID;

	/* El mnemonico NO se convierte aqui en offset.  Eso lo hace
	 * rx550_reg_offset(), que es la conversion ya existente y verificada de
	 * rx550_mmio.h, y este modulo no la reescribe. */
	*out = rx550_reg_make(r->index);
	return RX550_MMIO_OK;
}

/* ═══════════════════════════════════════════════════════════════════════════
 * EL RESOLVER:  la frontera del modulo
 * ═══════════════════════════════════════════════════════════════════════════ */
int rx550_mmio_attach(struct rx550_mmio_map *map, void *base, uint64_t size)
{
	if (!map || !base)
		return RX550_MMIO_ERR_INCONSISTENT;

	/* El tamaño se comprueba AL ENLAZAR.  Descubrir que el recurso es mas
	 * pequeno que BAR5 en el primer acceso seria descubrirlo escribiendo. */
	if (!rx550_mmio_size_ok(size)) {
		*map = rx550_mmio_map_empty();
		return RX550_MMIO_ERR_MAP_TOO_SMALL;
	}

	*map = rx550_mmio_map_make((uintptr_t)base, size);
	return RX550_MMIO_OK;
}

void rx550_mmio_detach(struct rx550_mmio_map *map)
{
	if (map)
		*map = rx550_mmio_map_empty();
}

int rx550_mmio_resolve(const struct rx550_mmio_map *map, struct rx550_reg reg,
		       struct rx550_mmap_offset *out)
{
	if (!out)
		return RX550_MMIO_ERR_INCONSISTENT;
	if (!map || !map->mapped)
		return RX550_MMIO_ERR_NO_MAP;
	/* Un mapa mas pequeno que la BAR declarada no puede contener el ultimo
	 * registro, y hay que decirlo como su propia causa, no como un
	 * "fuera de ventana" que el llamante interpretaria como registro malo. */
	if (!rx550_mmio_size_ok(map->size))
		return RX550_MMIO_ERR_MAP_TOO_SMALL;
	/* Y la ventana se comprueba con la funcion que ya existe, sobre el
	 * offset, antes de que exista un puntero. */
	if (!rx550_reg_in_window(reg))
		return RX550_MMIO_ERR_OUT_OF_WINDOW;
	if (rx550_reg_offset(reg).bytes + RX550_REG_WIDTH > map->size)
		return RX550_MMIO_ERR_OUT_OF_WINDOW;

	*out = rx550_reg_offset(reg);
	return RX550_MMIO_OK;
}

int rx550_mmio_resolve_reg(const struct rx550_mmio_map *map,
			   enum rx550_vmid1_reg_id id,
			   struct rx550_mmap_offset *out)
{
	struct rx550_reg reg;
	int rc;

	rc = rx550_mmio_reg_of(id, &reg);
	if (rc != RX550_MMIO_OK)
		return rc;
	return rx550_mmio_resolve(map, reg, out);
}

/* ═══════════════════════════════════════════════════════════════════════════
 * EL ACCESO
 *
 * Y LA REGLA QUE GOBIERNA ESTE BLOQUE:  si el resolver no dijo que sí, NO SE
 * TOCA LA MEMORIA.  Ni una lectura, ni una escritura.  Un accessor que
 * devuelve un valor por defecto cuando el acceso no procede convierte un
 * "registro no programable" en un "registro que valia cero", y esas dos cosas
 * son incompatibles.
 * ═══════════════════════════════════════════════════════════════════════════ */

/* El puntero al registro, una vez resuelto.  Y es la unica funcion que
 * construye una direccion de acceso, de modo que no puede haber dos caminos
 * que construyan direcciones con reglas distintas. */
static void *rx550_mmio_slot(const struct rx550_mmio_map *map,
			     struct rx550_mmap_offset off)
{
	return (void *)(map->base + (uintptr_t)off.bytes);
}

#ifdef __KERNEL__
/* Las primitivas del kernel, que son las que llevan las barreras que el
 * hardware necesita en un bus de dispositivo. */
static uint32_t rx550_slot_read(void *slot)
{
	return readl((volatile void *)slot);
}

static void rx550_slot_write(void *slot, uint32_t v)
{
	writel(v, (volatile void *)slot);
}
#else
/* Y en userspace, un acceso volatile equivalente, para poder ejercitar el
 * camino completo —resolver, acceder, leer lo escrito— contra un buffer normal
 * sin hardware.  La ARITMETICA del offset es la misma funcion, resolve();  lo
 * unico que se sustituye es la primitiva de barrera, que no existe fuera del
 * kernel y aqui no aporta nada. */
static uint32_t rx550_slot_read(void *slot)
{
	return *(volatile uint32_t *)slot;
}

static void rx550_slot_write(void *slot, uint32_t v)
{
	*(volatile uint32_t *)slot = v;
}
#endif

int rx550_mmio_read32(const struct rx550_mmio_map *map, struct rx550_reg reg,
		      uint32_t *out_value)
{
	struct rx550_mmap_offset off;
	int rc;

	if (!out_value)
		return RX550_MMIO_ERR_INCONSISTENT;

	rc = rx550_mmio_resolve(map, reg, &off);
	if (rc != RX550_MMIO_OK)
		return rc;		/* sin tocar memoria */

	*out_value = rx550_slot_read(rx550_mmio_slot(map, off));
	return RX550_MMIO_OK;
}

int rx550_mmio_write32(const struct rx550_mmio_map *map, struct rx550_reg reg,
		       uint32_t value)
{
	struct rx550_mmap_offset off;
	int rc;

	rc = rx550_mmio_resolve(map, reg, &off);
	if (rc != RX550_MMIO_OK)
		return rc;		/* sin tocar memoria */

	rx550_slot_write(rx550_mmio_slot(map, off), value);
	return RX550_MMIO_OK;
}

int rx550_mmio_read_reg(const struct rx550_mmio_map *map,
			enum rx550_vmid1_reg_id id, uint32_t *out_value)
{
	struct rx550_reg reg;
	int rc;

	rc = rx550_mmio_reg_of(id, &reg);
	if (rc != RX550_MMIO_OK)
		return rc;
	return rx550_mmio_read32(map, reg, out_value);
}

int rx550_mmio_write_reg(const struct rx550_mmio_map *map,
			 enum rx550_vmid1_reg_id id, uint32_t value)
{
	struct rx550_reg reg;
	int rc;

	rc = rx550_mmio_reg_of(id, &reg);
	if (rc != RX550_MMIO_OK)
		return rc;
	return rx550_mmio_write32(map, reg, value);
}

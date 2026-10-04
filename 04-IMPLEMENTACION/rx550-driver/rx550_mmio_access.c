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
 * Treinta y nueve entradas, ordenadas por byte_offset ascendente, con su procedencia en
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
	"mmVM_L2_CNTL",                             0x500, 0x1400, 32, "RW", "GLOBAL",
	"habilita y dimensiona la cache L2 antes de tocar la tabla",
	"gmc_8_1_d.h:597",                          RX550_REG_PROVEN
},
{
	"mmVM_L2_CNTL2",                            0x501, 0x1404, 32, "RW", "GLOBAL",
	"invalida L1 y L2; la referencia las activa y no las vuelve a desactivar",
	"gmc_8_1_d.h:598",                          RX550_REG_PROVEN
},
{
	"mmVM_L2_CNTL3",                            0x502, 0x1408, 32, "RW", "GLOBAL",
	"reparto del fragment_size entre bancos y fragmentacion",
	"gmc_8_1_d.h:599",                          RX550_REG_PROVEN
},
{
	"mmVM_CONTEXT0_CNTL",                       0x504, 0x1410, 32, "RW", "CONTEXT0",
	"habilita el contexto del GART con PAGE_TABLE_DEPTH 0",
	"gmc_8_1_d.h:601",                          RX550_REG_PROVEN
},
{
	"mmVM_CONTEXT1_CNTL",			0x505, 0x1414, 32, "RW", "CONTEXT1",
	"profundidad, block_size y ENABLE_CONTEXT del contexto 1",
	"gmc_8_1_d.h:602",			RX550_REG_PROVEN
},
{
	"mmVM_CONTEXT0_CNTL2",                      0x50c, 0x1430, 32, "RW", "CONTEXT0",
	"literal 0 en la referencia",
	"gmc_8_1_d.h:605",                          RX550_REG_PROVEN
},
{
	"mmVM_CONTEXT1_CNTL2",			0x50d, 0x1434, 32, "RW", "CONTEXT1",
	"procesamiento de interrupciones de fault del contexto 1",
	"gmc_8_1_d.h:606",			RX550_REG_PROVEN
},
{
	"mmVM_CONTEXT8_PAGE_TABLE_BASE_ADDR",       0x50e, 0x1438, 32, "W", "CONTEXT8",
	"nunca se nombra: se escribe CONTEXT0_BASE + i - 8",
	"gmc_8_1_d.h:607",                          RX550_REG_DECLARED
},
{
	"mmVM_CONTEXT9_PAGE_TABLE_BASE_ADDR",       0x50f, 0x143c, 32, "W", "CONTEXT9",
	"ancla del bloque 8..15:  la referencia lo escribe como mmVM_CONTEXT8_PAGE_TABLE_BASE_ADDR + i - 8",
	"gmc_8_1_d.h:608",                          RX550_REG_DECLARED
},
{
	"mmVM_CONTEXT10_PAGE_TABLE_BASE_ADDR",      0x510, 0x1440, 32, "W", "CONTEXT10",
	"ancla del bloque 8..15:  la referencia lo escribe como mmVM_CONTEXT8_PAGE_TABLE_BASE_ADDR + i - 8",
	"gmc_8_1_d.h:609",                          RX550_REG_DECLARED
},
{
	"mmVM_CONTEXT11_PAGE_TABLE_BASE_ADDR",      0x511, 0x1444, 32, "W", "CONTEXT11",
	"ancla del bloque 8..15:  la referencia lo escribe como mmVM_CONTEXT8_PAGE_TABLE_BASE_ADDR + i - 8",
	"gmc_8_1_d.h:610",                          RX550_REG_DECLARED
},
{
	"mmVM_CONTEXT12_PAGE_TABLE_BASE_ADDR",      0x512, 0x1448, 32, "W", "CONTEXT12",
	"ancla del bloque 8..15:  la referencia lo escribe como mmVM_CONTEXT8_PAGE_TABLE_BASE_ADDR + i - 8",
	"gmc_8_1_d.h:611",                          RX550_REG_DECLARED
},
{
	"mmVM_CONTEXT13_PAGE_TABLE_BASE_ADDR",      0x513, 0x144c, 32, "W", "CONTEXT13",
	"ancla del bloque 8..15:  la referencia lo escribe como mmVM_CONTEXT8_PAGE_TABLE_BASE_ADDR + i - 8",
	"gmc_8_1_d.h:612",                          RX550_REG_DECLARED
},
{
	"mmVM_CONTEXT14_PAGE_TABLE_BASE_ADDR",      0x514, 0x1450, 32, "W", "CONTEXT14",
	"ancla del bloque 8..15:  la referencia lo escribe como mmVM_CONTEXT8_PAGE_TABLE_BASE_ADDR + i - 8",
	"gmc_8_1_d.h:613",                          RX550_REG_DECLARED
},
{
	"mmVM_CONTEXT15_PAGE_TABLE_BASE_ADDR",      0x515, 0x1454, 32, "W", "CONTEXT15",
	"ancla del bloque 8..15:  la referencia lo escribe como mmVM_CONTEXT8_PAGE_TABLE_BASE_ADDR + i - 8",
	"gmc_8_1_d.h:614",                          RX550_REG_DECLARED
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
	"mmVM_CONTEXT0_PROTECTION_FAULT_DEFAULT_ADDR",0x546, 0x1518, 32, "W", "CONTEXT0",
	"destino de los faults del contexto del GART: PFN de la pagina dummy",
	"gmc_8_1_d.h:633",                          RX550_REG_PROVEN
},
{
	"mmVM_CONTEXT1_PROTECTION_FAULT_DEFAULT_ADDR", 0x547, 0x151c, 32, "W",
	"CONTEXT1",
	"destino de un fault de proteccion; el VALOR sigue abierto como R2",
	"gmc_8_1_d.h:634",			RX550_REG_PROVEN
},
{
	"mmVM_CONTEXT0_PAGE_TABLE_BASE_ADDR",       0x54f, 0x153c, 32, "W", "CONTEXT0",
	"raiz de la tabla del GART; de aqui sale CONTEXT(i) = este + i",
	"gmc_8_1_d.h:636",                          RX550_REG_PROVEN
},
{
	"mmVM_CONTEXT1_PAGE_TABLE_BASE_ADDR",	0x550, 0x1540, 32, "W", "CONTEXT1",
	"numero de pagina del root PDB0, 28 bits; no es la tabla entera",
	"gmc_8_1_d.h:637",			RX550_REG_PROVEN
},
{
	"mmVM_CONTEXT2_PAGE_TABLE_BASE_ADDR",       0x551, 0x1544, 32, "W", "CONTEXT2",
	"ancla del bloque 0..15:  la referencia lo escribe como mmVM_CONTEXT0_PAGE_TABLE_BASE_ADDR + i - 8",
	"gmc_8_1_d.h:638",                          RX550_REG_DECLARED
},
{
	"mmVM_CONTEXT3_PAGE_TABLE_BASE_ADDR",       0x552, 0x1548, 32, "W", "CONTEXT3",
	"ancla del bloque 0..15:  la referencia lo escribe como mmVM_CONTEXT0_PAGE_TABLE_BASE_ADDR + i - 8",
	"gmc_8_1_d.h:639",                          RX550_REG_DECLARED
},
{
	"mmVM_CONTEXT4_PAGE_TABLE_BASE_ADDR",       0x553, 0x154c, 32, "W", "CONTEXT4",
	"ancla del bloque 0..15:  la referencia lo escribe como mmVM_CONTEXT0_PAGE_TABLE_BASE_ADDR + i - 8",
	"gmc_8_1_d.h:640",                          RX550_REG_DECLARED
},
{
	"mmVM_CONTEXT5_PAGE_TABLE_BASE_ADDR",       0x554, 0x1550, 32, "W", "CONTEXT5",
	"ancla del bloque 0..15:  la referencia lo escribe como mmVM_CONTEXT0_PAGE_TABLE_BASE_ADDR + i - 8",
	"gmc_8_1_d.h:641",                          RX550_REG_DECLARED
},
{
	"mmVM_CONTEXT6_PAGE_TABLE_BASE_ADDR",       0x555, 0x1554, 32, "W", "CONTEXT6",
	"ancla del bloque 0..15:  la referencia lo escribe como mmVM_CONTEXT0_PAGE_TABLE_BASE_ADDR + i - 8",
	"gmc_8_1_d.h:642",                          RX550_REG_DECLARED
},
{
	"mmVM_CONTEXT7_PAGE_TABLE_BASE_ADDR",       0x556, 0x1558, 32, "W", "CONTEXT7",
	"ancla del bloque 0..15:  la referencia lo escribe como mmVM_CONTEXT0_PAGE_TABLE_BASE_ADDR + i - 8",
	"gmc_8_1_d.h:643",                          RX550_REG_DECLARED
},
{
	"mmVM_CONTEXT0_PAGE_TABLE_START_ADDR",      0x557, 0x155c, 32, "W", "CONTEXT0",
	"extremo bajo de la ventana del GART, en paginas",
	"gmc_8_1_d.h:644",                          RX550_REG_PROVEN
},
{
	"mmVM_CONTEXT1_PAGE_TABLE_START_ADDR",	0x558, 0x1560, 32, "W", "CONTEXT1",
	"primer numero de pagina de la ventana, LOGICAL",
	"gmc_8_1_d.h:645",			RX550_REG_PROVEN
},
{
	"mmVM_CONTEXT0_PAGE_TABLE_END_ADDR",        0x55f, 0x157c, 32, "W", "CONTEXT0",
	"extremo alto de la ventana del GART, en paginas",
	"gmc_8_1_d.h:646",                          RX550_REG_PROVEN
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
 * Cincuenta y cinco entradas:  los 22 de VM_CONTEXT1_CNTL,  los 7 de
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
{ "VM_CONTEXT1_CNTL",   "RANGE_PROTECTION_FAULT_ENABLE_INTERRUPT",	0x00000008u,  3, 1, RX550_FIELD_NO_CORPUS, "gmc_8_1_sh_mask.h:6629", RX550_FIELD_DECLARED_NOT_WRITTEN },
{ "VM_CONTEXT1_CNTL",   "DUMMY_PAGE_PROTECTION_FAULT_ENABLE_INTERRUPT",0x00000040u,  6, 1, RX550_FIELD_NO_CORPUS, "gmc_8_1_sh_mask.h:6633", RX550_FIELD_DECLARED_NOT_WRITTEN },
{ "VM_CONTEXT1_CNTL",   "PDE0_PROTECTION_FAULT_ENABLE_INTERRUPT",	0x00000200u,  9, 1, RX550_FIELD_NO_CORPUS, "gmc_8_1_sh_mask.h:6637", RX550_FIELD_DECLARED_NOT_WRITTEN },
{ "VM_CONTEXT1_CNTL",   "VALID_PROTECTION_FAULT_ENABLE_INTERRUPT",	0x00001000u, 12, 1, RX550_FIELD_NO_CORPUS, "gmc_8_1_sh_mask.h:6643", RX550_FIELD_DECLARED_NOT_WRITTEN },
{ "VM_CONTEXT1_CNTL",   "READ_PROTECTION_FAULT_ENABLE_INTERRUPT",	0x00008000u, 15, 1, RX550_FIELD_NO_CORPUS, "gmc_8_1_sh_mask.h:6649", RX550_FIELD_DECLARED_NOT_WRITTEN },
{ "VM_CONTEXT1_CNTL",   "WRITE_PROTECTION_FAULT_ENABLE_INTERRUPT",	0x00040000u, 18, 1, RX550_FIELD_NO_CORPUS, "gmc_8_1_sh_mask.h:6655", RX550_FIELD_DECLARED_NOT_WRITTEN },
{ "VM_CONTEXT1_CNTL",   "EXECUTE_PROTECTION_FAULT_ENABLE_INTERRUPT",0x00200000u, 21, 1, RX550_FIELD_NO_CORPUS, "gmc_8_1_sh_mask.h:6661", RX550_FIELD_DECLARED_NOT_WRITTEN },
/* ── los _SAVE: idem ── */
{ "VM_CONTEXT1_CNTL",   "PDE0_PROTECTION_FAULT_ENABLE_SAVE",		0x00000800u, 11, 1, RX550_FIELD_NO_CORPUS, "gmc_8_1_sh_mask.h:6641", RX550_FIELD_DECLARED_NOT_WRITTEN },
{ "VM_CONTEXT1_CNTL",   "VALID_PROTECTION_FAULT_ENABLE_SAVE",		0x00004000u, 14, 1, RX550_FIELD_NO_CORPUS, "gmc_8_1_sh_mask.h:6647", RX550_FIELD_DECLARED_NOT_WRITTEN },
{ "VM_CONTEXT1_CNTL",   "READ_PROTECTION_FAULT_ENABLE_SAVE",		0x00020000u, 17, 1, RX550_FIELD_NO_CORPUS, "gmc_8_1_sh_mask.h:6653", RX550_FIELD_DECLARED_NOT_WRITTEN },
{ "VM_CONTEXT1_CNTL",   "WRITE_PROTECTION_FAULT_ENABLE_SAVE",	0x00100000u, 20, 1, RX550_FIELD_NO_CORPUS, "gmc_8_1_sh_mask.h:6659", RX550_FIELD_DECLARED_NOT_WRITTEN },
{ "VM_CONTEXT1_CNTL",   "EXECUTE_PROTECTION_FAULT_ENABLE_SAVE",	0x00800000u, 23, 1, RX550_FIELD_NO_CORPUS, "gmc_8_1_sh_mask.h:6665", RX550_FIELD_DECLARED_NOT_WRITTEN },
/* -- VM_L2_CNTL  (0x500, offset 0x1400) -- */
{ "VM_L2_CNTL",   "ENABLE_L2_CACHE",                           0x00000001u,  0, 1, 1u,
				"gmc_v8_0.c:852",                   RX550_FIELD_PROVEN_CORPUS_WRITES },
{ "VM_L2_CNTL",   "ENABLE_L2_FRAGMENT_PROCESSING",             0x00000002u,  1, 1, 1u,
				"gmc_v8_0.c:853",                   RX550_FIELD_PROVEN_CORPUS_WRITES },
{ "VM_L2_CNTL",   "ENABLE_L2_PTE_CACHE_LRU_UPDATE_BY_WRITE",   0x00000200u,  9, 1, 1u,
				"gmc_v8_0.c:854",                   RX550_FIELD_PROVEN_CORPUS_WRITES },
{ "VM_L2_CNTL",   "ENABLE_L2_PDE0_CACHE_LRU_UPDATE_BY_WRITE",  0x00000400u, 10, 1, 1u,
				"gmc_v8_0.c:855",                   RX550_FIELD_PROVEN_CORPUS_WRITES },
{ "VM_L2_CNTL",   "EFFECTIVE_L2_QUEUE_SIZE",                   0x00038000u, 15, 3, 7u,
				"gmc_v8_0.c:856",                   RX550_FIELD_PROVEN_CORPUS_WRITES },
{ "VM_L2_CNTL",   "CONTEXT1_IDENTITY_ACCESS_MODE",             0x00180000u, 19, 2, 1u,
				"gmc_v8_0.c:857",                   RX550_FIELD_PROVEN_CORPUS_WRITES },
{ "VM_L2_CNTL",   "ENABLE_DEFAULT_PAGE_OUT_TO_SYSTEM_MEMORY",  0x00000800u, 11, 1, 1u,
				"gmc_v8_0.c:858",                   RX550_FIELD_PROVEN_CORPUS_WRITES },
/* -- VM_L2_CNTL2  (0x501, offset 0x1404) -- */
{ "VM_L2_CNTL2",  "INVALIDATE_ALL_L1_TLBS",  0x00000001u,  0, 1, 1u,
				"gmc_v8_0.c:861",                   RX550_FIELD_PROVEN_CORPUS_WRITES },
{ "VM_L2_CNTL2",  "INVALIDATE_L2_CACHE",     0x00000002u,  1, 1, 1u,
				"gmc_v8_0.c:862",                   RX550_FIELD_PROVEN_CORPUS_WRITES },
/* -- VM_L2_CNTL3  (0x502, offset 0x1408) -- */
/*  VM_L2_CNTL3
 *
 *  El valor del corpus es una VARIABLE, no un literal:
 *      gmc_v8_0.c:866   field = adev->vm_manager.fragment_size;
 *      gmc_v8_0.c:868   REG_SET_FIELD(tmp, VM_L2_CNTL3, BANK_SELECT, field)
 *      gmc_v8_0.c:869   REG_SET_FIELD(tmp, VM_L2_CNTL3, L2_CACHE_BIGK_FRAGMENT_SIZE, field)
 *
 *  Una tabla de valores enteros no puede escribirlo sin inventar un
 *  numero, asi que queda sin valor.  Lo pone el constructor de la
 *  secuencia desde sus propios parametros, y SOLO para los dos campos
 *  que estan en esa lista:  uno simbolico que no este en ella corta
 *  la construccion con error, en vez de escribir un cero en un
 *  registro de fragmentacion.
 */
{ "VM_L2_CNTL3",  "L2_CACHE_BIGK_ASSOCIATIVITY",  0x00100000u, 20, 1, 1u,
				"gmc_v8_0.c:867",                   RX550_FIELD_PROVEN_CORPUS_WRITES },
{ "VM_L2_CNTL3",  "BANK_SELECT",                  0x0000003Fu,  0, 6, RX550_FIELD_NO_CORPUS,
				"gmc_v8_0.c:868",                   RX550_FIELD_PROVEN_CORPUS_WRITES },
{ "VM_L2_CNTL3",  "L2_CACHE_BIGK_FRAGMENT_SIZE",  0x000F8000u, 15, 5, RX550_FIELD_NO_CORPUS,
				"gmc_v8_0.c:869",                   RX550_FIELD_PROVEN_CORPUS_WRITES },
/* -- VM_L2_CNTL4  (0x578, offset 0x15e0) -- */
{ "VM_L2_CNTL4",  "VMC_TAP_CONTEXT0_PDE_REQUEST_PHYSICAL",  0x00000040u,  6, 1, 0u,
				"gmc_v8_0.c:873",                   RX550_FIELD_PROVEN_CORPUS_WRITES },
{ "VM_L2_CNTL4",  "VMC_TAP_CONTEXT0_PDE_REQUEST_SHARED",    0x00000080u,  7, 1, 0u,
				"gmc_v8_0.c:874",                   RX550_FIELD_PROVEN_CORPUS_WRITES },
{ "VM_L2_CNTL4",  "VMC_TAP_CONTEXT0_PDE_REQUEST_SNOOP",     0x00000100u,  8, 1, 0u,
				"gmc_v8_0.c:875",                   RX550_FIELD_PROVEN_CORPUS_WRITES },
{ "VM_L2_CNTL4",  "VMC_TAP_CONTEXT0_PTE_REQUEST_PHYSICAL",  0x00000200u,  9, 1, 0u,
				"gmc_v8_0.c:876",                   RX550_FIELD_PROVEN_CORPUS_WRITES },
{ "VM_L2_CNTL4",  "VMC_TAP_CONTEXT0_PTE_REQUEST_SHARED",    0x00000400u, 10, 1, 0u,
				"gmc_v8_0.c:877",                   RX550_FIELD_PROVEN_CORPUS_WRITES },
{ "VM_L2_CNTL4",  "VMC_TAP_CONTEXT0_PTE_REQUEST_SNOOP",     0x00000800u, 11, 1, 0u,
				"gmc_v8_0.c:878",                   RX550_FIELD_PROVEN_CORPUS_WRITES },
{ "VM_L2_CNTL4",  "VMC_TAP_CONTEXT1_PDE_REQUEST_PHYSICAL",  0x00001000u, 12, 1, 0u,
				"gmc_v8_0.c:879",                   RX550_FIELD_PROVEN_CORPUS_WRITES },
{ "VM_L2_CNTL4",  "VMC_TAP_CONTEXT1_PDE_REQUEST_SHARED",    0x00002000u, 13, 1, 0u,
				"gmc_v8_0.c:880",                   RX550_FIELD_PROVEN_CORPUS_WRITES },
{ "VM_L2_CNTL4",  "VMC_TAP_CONTEXT1_PDE_REQUEST_SNOOP",     0x00004000u, 14, 1, 0u,
				"gmc_v8_0.c:881",                   RX550_FIELD_PROVEN_CORPUS_WRITES },
{ "VM_L2_CNTL4",  "VMC_TAP_CONTEXT1_PTE_REQUEST_PHYSICAL",  0x00008000u, 15, 1, 0u,
				"gmc_v8_0.c:882",                   RX550_FIELD_PROVEN_CORPUS_WRITES },
{ "VM_L2_CNTL4",  "VMC_TAP_CONTEXT1_PTE_REQUEST_SHARED",    0x00010000u, 16, 1, 0u,
				"gmc_v8_0.c:883",                   RX550_FIELD_PROVEN_CORPUS_WRITES },
{ "VM_L2_CNTL4",  "VMC_TAP_CONTEXT1_PTE_REQUEST_SNOOP",     0x00020000u, 17, 1, 0u,
				"gmc_v8_0.c:884",                   RX550_FIELD_PROVEN_CORPUS_WRITES },
/* -- VM_CONTEXT0_CNTL  (0x504, offset 0x1410) -- */
{ "VM_CONTEXT0_CNTL", "ENABLE_CONTEXT",                         0x00000001u,  0, 1, 1u,
				"gmc_v8_0.c:894",                   RX550_FIELD_PROVEN_CORPUS_WRITES },
{ "VM_CONTEXT0_CNTL", "PAGE_TABLE_DEPTH",                       0x00000006u,  1, 2, 0u,
				"gmc_v8_0.c:895",                   RX550_FIELD_PROVEN_CORPUS_WRITES },
{ "VM_CONTEXT0_CNTL", "RANGE_PROTECTION_FAULT_ENABLE_DEFAULT",  0x00000010u,  4, 1, 1u,
				"gmc_v8_0.c:896",                   RX550_FIELD_PROVEN_CORPUS_WRITES },
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

/* ── EL REGISTRO DE TABLA DE PAGINAS DE UN VMID, POR LA REGLA DEL CORPUS ────
 *
 *  La justificacion completa, con las lineas del corpus, esta en el header.
 *  Aqui lo que se implementa es la regla:
 *
 *      vmid < 8   ->  0x54f + vmid        (bloque de contextos 0..7)
 *      vmid < 16  ->  0x50e + (vmid - 8)  (bloque de contextos 8..15)
 *
 *  Y EL CORTE NO ES UNA PREFERENCIA, porque sin el corte el daño es CONCRETO
 *  y no una eventualidad.  gmc_v8_0.c:673-676 lo escribe con un `if`, y el
 *  bloque de contextos 8..15 esta POR DEBAJO del de 0..7:
 *
 *      0x54f .. 0x556   mmVM_CONTEXT0..7_PAGE_TABLE_BASE_ADDR
 *      0x557            mmVM_CONTEXT0_PAGE_TABLE_START_ADDR     <-- NO es un BASE
 *      0x558            mmVM_CONTEXT1_PAGE_TABLE_START_ADDR     <-- NO es un BASE
 *      0x50e .. 0x515   mmVM_CONTEXT8..15_PAGE_TABLE_BASE_ADDR
 *
 *  Asi que sin el corte:
 *
 *      vmid 8 -> 0x54f + 8 = 0x557 = mmVM_CONTEXT0_PAGE_TABLE_START_ADDR
 *      vmid 9 -> 0x54f + 9 = 0x558 = mmVM_CONTEXT1_PAGE_TABLE_START_ADDR
 *
 *  O sea:  escribiria la BASE de la tabla del contexto 8 en el START de la
 *  ventana del contexto 0,  y la del 9 en el START de la del 1.  Eso no es un
 *  registro que no existe:  es un registro que existe,  tiene un nombre que
 *  parece de la misma familia,  y tiene una SEMANTICA DISTINTA.  El contexto se
 *  queda con la ventana mal y sin falla de por medio.
 *
 *  CORREGIDO 2026-10-03.  Este comentario decia antes "sin el corte el VMID 8
 *  recibiria 0x516 y el VMID 9 recibiria 0x517".  Los dos numeros eran erroneos
 *  y ademas IMPRIMIAN UN PELIGRO QUE NO ERA:  0x516 y 0x517 no estan en el
 *  header,  asi que la frase leia como "un registroraro que no existe",  y lo
 *  que de verdad pasa es que se escribe en el START de otro contexto.  Un
 *  comentario de peligro que describe el peligro equivocado es peor que no
 *  escribirlo:  el lector cree que el fallo es benigno.
 */
#define RX550_GMC_CTX0_PT_BASE_IDX	0x54f	/* gmc_8_1_d.h:636 */
#define RX550_GMC_CTX8_PT_BASE_IDX	0x50e	/* gmc_8_1_d.h:607, NO 623 */
#define RX550_GMC_NR_VMIDS		16	/* dominios de INVALIDATE_REQUEST */

uint32_t rx550_mmio_ctx_pt_base_index(unsigned vmid)
{
	if (vmid < 8u)
		return RX550_GMC_CTX0_PT_BASE_IDX + vmid;
	if (vmid < RX550_GMC_NR_VMIDS)
		return RX550_GMC_CTX8_PT_BASE_IDX + (vmid - 8u);
	/* No hay un contexto 16.  Devolver un indice calculable por aritmetica
	 * seria inventar un registro que no existe y que ademas cabe en BAR5, de
	 * modo que el fallo no se veria en el acceso. */
	return 0u;
}

int rx550_mmio_pt_value(uint64_t pd_addr, uint32_t *out)
{
	if (!out)
		return RX550_MMIO_ERR_INCONSISTENT;
	/* Se comprueba ANTES de desplazar.  Comprobar despues seria comprobar
	 * que el truncamiento ya ha ocurrido. */
	if (pd_addr > RX550_PT_MAX_PD_ADDR)
		return RX550_MMIO_ERR_OUT_OF_WINDOW;
	*out = (uint32_t)(pd_addr >> RX550_PT_PAGE_SHIFT);
	return RX550_MMIO_OK;
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

int rx550_mmio_reg_of_index(uint32_t index, struct rx550_reg *out)
{
	if (!out)
		return RX550_MMIO_ERR_INCONSISTENT;
	/*  Se comprueba aqui y no solo en rx550_mmio_resolve() porque el error que
	 *  devuelve el segundo es de ventana,  y quien llama a esta funcion con un
	 *  indice de mas quiere saber que el INDICE era malo,  no que el mapa
	 * _RESULTADO_ era malo. */
	if ((uint64_t)index * (uint64_t)RX550_REG_WIDTH > RX550_MMIO_SIZE)
		return RX550_MMIO_ERR_BAD_ID;
	*out = rx550_reg_make(index);
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

/* ── ACTUALIZACION DE UN CAMPO ─────────────────────────────────────────────
 *
 *  La justificacion, con la cuenta del corpus y el motivo de derivar el shift
 *  en vez de copiarlo, estan en rx550_mmio_access.h.  Aqui la implementacion.
 *
 *  rx550_mmio_field_from_mask es donde vive la regla, y por eso es una funcion suelta
 *  y no una linea dentro de update:  es lo que test_update_field.c comprueba
 *  contra los 42 campos del corpus.  Si la regla estuviera incrustada en el
 *  update, comprobarla obligaria a ejecutarlo contra un mapa, y el test
 *  compararia un mapa con un mapa en vez de una regla con el corpus.
 */

/* Numero de ceros finales.  mask != 0 garantizado por el llamante. */
static unsigned rx550_trailing_zeros(uint32_t v)
{
	unsigned n = 0;

	while ((v & 1u) == 0u) {
		v >>= 1;
		n++;
	}
	return n;
}

int rx550_mmio_field_from_mask(uint32_t mask, unsigned *out_shift, unsigned *out_width)
{
	unsigned shift, width, w;

	if (!out_shift || !out_width)
		return RX550_MMIO_ERR_INCONSISTENT;
	/* Un mask de cero no tiene posicion.  No se devuelve shift 0:  se
	 * devolveria el primer bit del registro, que es el campo equivocado y
	 * uno que el llamante no puede detectar. */
	if (mask == 0u)
		return RX550_MMIO_ERR_BAD_MASK;

	shift = rx550_trailing_zeros(mask);
	w = mask >> shift;
	/* Contiguo: tras el desplazamiento tiene que quedar una racha de unos y
	 * nada mas.  0b1, 0b11, 0b111...  0b101 no, porque tiene un hueco y dos
	 * posiciones posibles. */
	if ((w & (w + 1u)) != 0u)
		return RX550_MMIO_ERR_BAD_MASK;

	width = 0;
	while (w & 1u) {
		w >>= 1;
		width++;
	}

	*out_shift = shift;
	*out_width = width;
	return RX550_MMIO_OK;
}

int rx550_mmio_get_field(uint32_t raw, uint32_t mask, uint32_t *out_value)
{
	unsigned shift, width;
	int rc;

	if (!out_value)
		return RX550_MMIO_ERR_INCONSISTENT;
	rc = rx550_mmio_field_from_mask(mask, &shift, &width);
	if (rc != RX550_MMIO_OK)
		return rc;
	/* El ancho no hace falta para leer, pero se pide la validacion entera:
	 *  un mask valido que no cabe en el registro no existe aqui, y pedir
	 *  solo el shift seria una via por la que un mask raro pase sin quejar. */
	*out_value = (raw >> shift) & mask;
	return RX550_MMIO_OK;
}

int rx550_mmio_apply_field(uint32_t raw, uint32_t mask, uint32_t value,
			   uint32_t *out)
{
	unsigned shift, width;
	int rc;

	if (!out)
		return RX550_MMIO_ERR_INCONSISTENT;
	rc = rx550_mmio_field_from_mask(mask, &shift, &width);
	if (rc != RX550_MMIO_OK)
		return rc;
	if (width < 32u && (value >> width) != 0u)
		return RX550_MMIO_ERR_VALUE_RANGE;
	*out = (raw & ~mask) | ((value << shift) & mask);
	return RX550_MMIO_OK;
}

int rx550_mmio_update_field(const struct rx550_mmio_map *map,
			    struct rx550_reg reg,
			    uint32_t mask, uint32_t value,
			    uint32_t *out_value)
{
	struct rx550_mmap_offset off;
	unsigned shift, width;
	uint32_t raw, nuevo;
	int rc;

	if (!out_value)
		return RX550_MMIO_ERR_INCONSISTENT;

	/* El campo se valida ANTES de tocar el mapa.  Un mask invalido con un
	 * mapa valido tiene que fallar por el mask, no por el mapa, o el
	 * llamante recibe un motivo que no le sirve. */
	rc = rx550_mmio_field_from_mask(mask, &shift, &width);
	if (rc != RX550_MMIO_OK)
		return rc;
	(void)shift; (void)width;

	rc = rx550_mmio_resolve(map, reg, &off);
	if (rc != RX550_MMIO_OK)
		return rc;

	raw = *(volatile uint32_t *)rx550_mmio_slot(map, off);
	/* La composicion la hace el NUCLEO, no una segunda copia de la regla.
	 * Dos copias de "clearing" y "shifting" en el mismo fichero divergen, y
	 * divergen en silencio. */
	rc = rx550_mmio_apply_field(raw, mask, value, &nuevo);
	if (rc != RX550_MMIO_OK)
		return rc;
	*(volatile uint32_t *)rx550_mmio_slot(map, off) = nuevo;
	*out_value = nuevo;
	return RX550_MMIO_OK;
}

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

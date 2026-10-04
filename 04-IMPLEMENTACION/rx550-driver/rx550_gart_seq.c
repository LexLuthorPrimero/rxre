/* SPDX-License-Identifier: GPL-2.0 */
/*
 * rx550_gart_seq.c — el plan de las 34 escrituras del GART.
 *
 *   TARGET = RX 550 instalada en esta maquina
 *   SCOPE  = EXCLUSIVO
 *
 *   COMPATIBILIDAD KBUILD:  mismo split que rx550_spaces.h.  Este fichero no
 *   usa nada del kernel:  solo aritmetica sobre la tabla de campos y sobre los
 *   parametros.  Compila identico en los dos contextos, y por eso las TU de
 *   este componente pueden estar en obj-m.
 */
#include "rx550_gart_seq.h"
#include "rx550_mmio_access.h"

/* COMPATIBILIDAD KBUILD:  el kernel no tiene <string.h>.  Mismo split que
 * rx550_vmid0_gart.c y rx550_vmid1_pgt.c. */
#ifdef __KERNEL__
#include <linux/string.h>
#else
#include <string.h>
#endif

/* ── EL ORDEN, que es de gmc_v8_0.c y no de ninguna tabla ─────────────────
 *
 *  Cada linea dice de donde sale el registro.  Los numeros son las de
 *  gmc_v8_0.c, no las del enum del driver:  a proposito, porque el enum se
 *  renumera cada vez que se anade un registro y estas lineas no deben moverse
 *  con el. */
/* ── EL ORDEN, que es de gmc_v8_0.c y no de ninguna tabla ─────────────────
 *
 *  Cada linea dice de donde sale el registro, y las lineas son MEDIDAS:  se
 *  busca la sentencia WREG32 en el corpus, no se cuentan posiciones.
 *
 *  ESTA TABLA TUVO UN DESPLAZAMIENTO DE UNA LINEA, y por eso el comentario
 *  anterior ahi es ahora este.  Las veinte citas estaban escritas a mano desde
 *  una lectura con sed,  y todas las que apuntaban al COMIENZO de una sentencia
 *  de dos lineas apuntaban a la segunda:
 *
 *      decia  L843   real  L849   mmMC_VM_MX_L1_TLB_CNTL
 *      decia  L923   real  L922   mmVM_CONTEXT1_CNTL2 = 4
 *      decia  L921   real  L920   mmVM_CONTEXT1_PROTECTION_FAULT_DEFAULT_ADDR
 *
 *  Las citas de los CAMPOS  (rx550_reg_fields[]) si son exactas, y la diferencia
 *  es el metodo:  esas las genero un script que recorría el fichero contando
 *  lineas,  y estas las escribi yo.  Es la misma leccion que las mascaras del
 *  finding 1028,  con la palabra "manualmente" debajo de la palabra "script".
 *
 *  Ademas:  la funcion escribe 44 registros,  no 34.  Las 34 de esta tabla mas
 *  las que escriben sus doscalled  (mmVM_PRT_CNTL en L789 y las ocho
 *  mmVM_PRT_APERTURE* de L797-806,  mas mmVM_INVALIDATE_REQUEST en L664 dentro de
 *  gmc_v8_0_flush_gpu_tlb,  llamada en L940).  Ver el finding 1033. */
enum {
	O_L1_TLB_CNTL	= 0,		/* L849 */
	O_L2_CNTL,		/* L859 */
	O_L2_CNTL2,		/* L863 */
	O_L2_CNTL3,		/* L870 */
	O_L2_CNTL4,		/* L885 */
	O_CTX0_PT_START,	/* L887 */
	O_CTX0_PT_END,		/* L888 */
	O_CTX0_PT_BASE,	/* L889 */
	O_CTX0_PROT_FAULT,	/* L890 */
	O_CTX0_CNTL2,		/* L892 */
	O_CTX0_CNTL,		/* L897 */
	O_IDA_LOW,		/* L899 */
	O_IDA_HIGH,		/* L900 */
	O_IDA_OFFSET,		/* L901 */
	O_CTX1_PT_START,	/* L908 */
	O_CTX1_PT_END,		/* L909 */
	O_CTX1_LOOP,		/* L911 y L914,  el bucle i = 1..15 */
	O_CTX1_PROT_FAULT,	/* L920 */
	O_CTX1_CNTL2,		/* L922 */
	O_CTX1_CNTL,		/* L935 */
	O_NR
};

/* Los registros del plan, en el orden de arriba.  Los 15 del bucle NO estan:
 * se generan aparte. */
static const char *const rx550_gart_orden[O_NR] = {
	"mmMC_VM_MX_L1_TLB_CNTL",
	"mmVM_L2_CNTL",
	"mmVM_L2_CNTL2",
	"mmVM_L2_CNTL3",
	"mmVM_L2_CNTL4",
	"mmVM_CONTEXT0_PAGE_TABLE_START_ADDR",
	"mmVM_CONTEXT0_PAGE_TABLE_END_ADDR",
	"mmVM_CONTEXT0_PAGE_TABLE_BASE_ADDR",
	"mmVM_CONTEXT0_PROTECTION_FAULT_DEFAULT_ADDR",
	"mmVM_CONTEXT0_CNTL2",
	"mmVM_CONTEXT0_CNTL",
	"mmVM_L2_CONTEXT1_IDENTITY_APERTURE_LOW_ADDR",
	"mmVM_L2_CONTEXT1_IDENTITY_APERTURE_HIGH_ADDR",
	"mmVM_L2_CONTEXT_IDENTITY_PHYSICAL_OFFSET",
	"mmVM_CONTEXT1_PAGE_TABLE_START_ADDR",
	"mmVM_CONTEXT1_PAGE_TABLE_END_ADDR",
	NULL,				/* el bucle */
	"mmVM_CONTEXT1_PROTECTION_FAULT_DEFAULT_ADDR",
	"mmVM_CONTEXT1_CNTL2",
	"mmVM_CONTEXT1_CNTL",
};

/* Que posicion del plan es un RMW, y cual de los siete es.
 *
 *  UNA ENTRADA POR CADA POSICION DEL ORDEN, y en el MISMO orden.  La primera
 *  version de esta tabla tenia 19 entradas para 20 posiciones, y por eso a
 *  partir de la novena todo iba corrido una posicion:
 *
 *      pos  9  mmVM_CONTEXT0_CNTL2      quedaba marcada como RMW   (es un 0)
 *      pos 10  mmVM_CONTEXT0_CNTL       quedaba como escritura ciega  <-- la
 *      pos 19  mmVM_CONTEXT1_CNTL       se salia de la tabla
 *
 *  El sintoma era que la composicion de mmVM_CONTEXT0_CNTL no encontraba
 *  campos y devolvia "la tabla no cubre esto",  que es un diagnostico
 *  FALSO:  la tabla los tiene todos.  Una tabla paralela al orden solo se
 *  puede validar comparandola con el, y no se comparaba.  Un _Static_assert de
 *  tamano no habria servido:  en C una lista de 19 inicializadores para un
 *  array de 20 se queda corta en silencio, y el resto toma el valor cero, que
 *  aqui es RX550_GART_RMW_L1_TLB_CNTL.  Peor que no tenerla.
 *
 *  Con designadores de indice el patron no se puede equivocar:  si falta uno,
 *  ese vale 0, y 0 es L1_TLB, que no es lo que falta.  Por eso esta tabla va
 *  con [O_...] explicitos y la anterior no.
 *
 *  -1 = escritura completa (literal o PFN).  -2 = el bucle de contextos.
 */
static const int rx550_gart_rmw_de[O_NR] = {
	[O_L1_TLB_CNTL]		= RX550_GART_RMW_L1_TLB_CNTL,
	[O_L2_CNTL]		= RX550_GART_RMW_L2_CNTL,
	[O_L2_CNTL2]		= RX550_GART_RMW_L2_CNTL2,
	[O_L2_CNTL3]		= RX550_GART_RMW_L2_CNTL3,
	[O_L2_CNTL4]		= RX550_GART_RMW_L2_CNTL4,
	[O_CTX0_PT_START]	= -1,
	[O_CTX0_PT_END]		= -1,
	[O_CTX0_PT_BASE]	= -1,
	[O_CTX0_PROT_FAULT]	= -1,
	[O_CTX0_CNTL2]		= -1,
	[O_CTX0_CNTL]		= RX550_GART_RMW_CTX0_CNTL,
	[O_IDA_LOW]		= -1,
	[O_IDA_HIGH]		= -1,
	[O_IDA_OFFSET]		= -1,
	[O_CTX1_PT_START]	= -1,
	[O_CTX1_PT_END]		= -1,
	[O_CTX1_LOOP]		= -2,
	[O_CTX1_PROT_FAULT]	= -1,
	[O_CTX1_CNTL2]		= -1,
	[O_CTX1_CNTL]		= RX550_GART_RMW_CTX1_CNTL,
};

/* El tamano no se comprueba solo:  un _Static_assert de la longitud no
 *  habria servido, porque en C una lista de 19 inicializadores para
 *  un array de 20 se queda corta en silencio.  Lo que sigue comprueba
 *  que el orden tiene dos posiciones de CNTL2 DISTINTAS, que es el
 *  error que la tabla de RMW tenia:  una sola, compartida por el
 *  contexto 0 y el 1. */


/*  Se puede comprobar releyendo?
 *
 *  Se decide por la COLUMNA ACCESS de la tabla de registros,  y no por una
 *  lista de registros:  la lista seria una segunda copia de un dato que ya
 *  existe,  y por lo tanto desincronizable.  El indice se pasa porque el plan
 *  lo lleva,  y no hay nombre para los quince del bucle. */
static bool rx550_gart_es_legible(uint32_t index)
{
	for (uint32_t i = 0; i < rx550_vmid1_reg_count; i++) {
		if (rx550_vmid1_regs[i].index != index)
			continue;
		/*  "R" y "RW" se leen.  "W" no,  y no por prudencia:  porque lo que
		 *  devuelva no es lo escrito. */
		return rx550_vmid1_regs[i].access[0] == 'R';
	}
	/*  Un registro que no esta en la tabla no se puede verificar,  y no se
	 *  trata como error:  el plan lo ha construido y el apply lo va a
	 *  escribir igual.  Lo que no puede es declarar que lo ha comprobado. */
	return false;
}

/* El indice del registro, por mnemonico, en la tabla del accessor. */
static bool rx550_gart_reg_index(const char *mnemo, uint32_t *out)
{
	/*  NULL se devuelve como "no encontrado" y no se desreferencia.
	 *
	 *  rx550_gart_orden[] tiene una ranura vacia (NULL) para la posicion del
	 *  bucle de contextos.  Cuando la gestion del bucle estaba al final de la
	 *  funcion, esa ranura se salvaba con un "if (... == NULL) continue" que
	 *  estaba ANTES de llamar aqui.  Al mover el bucle a su sitio, ese continue
	 *  desaparecio y nadie lo sustituyo:  la seguridad dependia de que las dos
	 *  cosas coincidieran, y si no coinciden el constructor entra por un
	 *  while (*NULL) y revienta el proceso.
	 *
	 *  Lo encontrou una mutacion del self-test (desactivar la rama del bucle),
	 *  que en vez de fallar dio SIGSEGV.  Un fallo que mata el proceso en vez
	 *  de devolver un error no se distingue de un fallo de otra cosa cuando
	 *  aparece en el kernel. */
	if (mnemo == NULL)
		return false;

	for (uint32_t i = 0; i < rx550_vmid1_reg_count; i++) {
		const char *n = rx550_vmid1_regs[i].name;

		/* La comparacion de mnemonicos es EXACTA a proposito:  un registro
		 * con un nombre parecido no es el registro, y quedarse con el mas
		 * parecido seria peor que no encontrar ninguno. */
		uint32_t k = 0;

		while (n[k] && mnemo[k] && n[k] == mnemo[k])
			k++;
		if (n[k] == '\0' && mnemo[k] == '\0') {
			*out = rx550_vmid1_regs[i].index;
			return true;
		}
	}
	return false;
}

/* El indice de registro del contexto i, POR LA REGLA, no por nombre.
 *
 *  El corpus nunca nombra los contextos 2..7 ni 9..15:  los escribe como
 *      mmVM_CONTEXT0_PAGE_TABLE_BASE_ADDR + i        (i < 8)
 *      mmVM_CONTEXT8_PAGE_TABLE_BASE_ADDR + i - 8    (i >= 8)
 *  Ver el finding 1025, y la funcion rx550_mmio_ctx_pt_base_index() que ya
 *  implementa exactamente eso.  Aqui no se reimplementa:  se llama. */
static uint32_t rx550_gart_ctx_index(unsigned vmid)
{
	return rx550_mmio_ctx_pt_base_index(vmid);
}

/* Compone un RMW:  aplica TODOS los campos de `mnemo` al valor actual.
 *
 *  Y es aqui donde la tabla de campos paga:  los valores que pone la
 *  referencia estan en rx550_reg_fields[] con su mask y su shift, y este
 *  bucle los aplica en orden.  Anadir un campo a esa tabla lo anade aqui sin
 *  tocar una linea. */
/* Los TRES campos de la secuencia cuyo valor en el corpus es una EXPRESION y no
 * un literal, y de que parametro sale cada uno:
 *
 *      gmc_v8_0.c:866  field = adev->vm_manager.fragment_size;
 *      gmc_v8_0.c:868  REG_SET_FIELD(..., VM_L2_CNTL3, BANK_SELECT, field)
 *      gmc_v8_0.c:869  REG_SET_FIELD(..., VM_L2_CNTL3, L2_CACHE_BIGK_FRAGMENT_SIZE, field)
 *      gmc_v8_0.c:933  REG_SET_FIELD(..., VM_CONTEXT1_CNTL, PAGE_TABLE_BLOCK_SIZE,
 *                                     adev->vm_manager.block_size - 9)
 *
 *  Y son TRES, no dos.  La primera version de esta lista tenia dos y se
 *  olvidaba de PAGE_TABLE_BLOCK_SIZE, que ya constaba en rx550_reg_fields[] con
 *  RX550_FIELD_NO_CORPUS desde antes.  El efecto era que la composicion de
 *  mmVM_CONTEXT1_CNTL —el ultimo registro de la secuencia— devolvia error, y el
 *  fallo se leia como "a este registro le faltan campos en la tabla" cuando lo
 *  que faltaba era una fila mas en una lista de tres.
 *
 *  La lista es EXPLICITA y no "*usa el fragment_size*".  Con esa regla, un
 *  campo que se anadiera manana y todavia no tuviera valor recibiria un 9
 *  silencioso en un registro de fragmentacion.  Con la lista, da error. */
enum rx550_gart_simbolo_de {
	RX550_GART_SIM_FRAGMENT = 0,
	RX550_GART_SIM_BLOCK,
};

struct rx550_gart_simbolo {
	const char			*reg;
	const char			*campo;
	enum rx550_gart_simbolo_de	de;
	unsigned			restar;
};

static const struct rx550_gart_simbolo rx550_gart_simbolos[] = {
	{ "VM_L2_CNTL3",     "BANK_SELECT",                 RX550_GART_SIM_FRAGMENT, 0 },
	{ "VM_L2_CNTL3",     "L2_CACHE_BIGK_FRAGMENT_SIZE", RX550_GART_SIM_FRAGMENT, 0 },
	{ "VM_CONTEXT1_CNTL", "PAGE_TABLE_BLOCK_SIZE",      RX550_GART_SIM_BLOCK,    9 },
};

#define RX550_GART_SIMBOLOS_NR \
	(sizeof(rx550_gart_simbolos) / sizeof(rx550_gart_simbolos[0]))

/* El valor del campo simbolico, o error si no esta en la lista. */
static int rx550_gart_valor_simbolico(const char *reg, const char *campo,
				      const struct rx550_gart_params *p,
				      uint32_t *out)
{
	for (unsigned k = 0; k < RX550_GART_SIMBOLOS_NR; k++) {
		const struct rx550_gart_simbolo *s = &rx550_gart_simbolos[k];

		if (strcmp(s->reg, reg) != 0 || strcmp(s->campo, campo) != 0)
			continue;
		*out = (s->de == RX550_GART_SIM_FRAGMENT) ? p->fragment_size
							  : p->block_size;
		/* El " - 9" de gmc_v8_0.c:933 puede quedar por debajo de cero si
		 * alguien pasa block_size < 9, y escribir un numero recortado en un
		 * campo de 4 bits es mejor que un truncamiento silencioso. */
		if (*out < s->restar)
			return RX550_GART_SEQ_ERR_GEOMETRY;
		*out -= s->restar;
		return 0;
	}
	return RX550_GART_SEQ_ERR_TABLE;
}

static int rx550_gart_rmw_componer(const char *mnemo, uint32_t cur,
			       const struct rx550_gart_params *p,
			       uint32_t *out)
{
	/*  rx550_reg_fields[] lleva el nombre del campo SIN el prefijo mm
	 *  ("VM_L2_CNTL") y el orden de arriba lo lleva CON prefijo
	 *  ("mmVM_L2_CNTL").  Se le quita el "mm" al MNEMONICO, y no al nombre
	 *  de la tabla:  la primera version lo hacia al reves, y como la tabla
	 *  ya viene sin prefijo no quitaba nada, la comparacion no_encajaba
	 *  jamas, y la funcion devolvia cero campos en los siete registros.
	 *
	 *  Un fallo que se lee como "la tabla no cubre esto" y no es eso. */
	const char *mn = mnemo;
	uint32_t v = cur;
	int aplicados = 0;

	if (mn[0] == 'm' && mn[1] == 'm')
		mn += 2;

	for (uint32_t i = 0; i < rx550_reg_field_count; i++) {
		const struct rx550_reg_field *f = &rx550_reg_fields[i];
		uint32_t valor;
		int rc;

		if (strcmp(f->reg, mn) != 0)
			continue;

		/*  AQUI ESTA LA CONFUSION QUE COSTO TRES FALLOS SEGUIDOS, y que
		 *  conviene dejar escrita porque es facil volver a caer en ella:
		 *
		 *  RX550_FIELD_NO_CORPUS significa DOS COSAS DISTINTAS segun la
		 *  procedencia del campo, y el valor solo no las distingue:
		 *
		 *   a) PROVEN_CORPUS_WRITES + sin valor  ->  el corpus lo escribe,
		 *      pero con una EXPRESION que no cabe en un uint32_t.  El valor
		 *      sale de los parametros.
		 *
		 *   b) DECLARED_NOT_WRITTEN               ->  el corpus NO lo toca.
		 *      Y aqui no hay que inventarle nada:  hay que DEJARLO COMO
		 *      ESTA,  que es justo lo que hace el RMW.  Los siete
		 *      _INTERRUPT, los cinco _SAVE y ECO_BITS son de este tipo.
		 *
		 *   Y CORREGIDO:  este mismo comentario decia antes que los doce
		 *   VMC_TAP eran del segundo tipo.  NO.  El corpus los ESCRIBE,  a
		 *   cero:
		 *      gmc_v8_0.c:873-884   doce REG_SET_FIELD(..., 0)
		 *   asi que son PROVEN_CORPUS_WRITES con valor 0,  que es lo que
		 *   tiene la tabla,  y por eso se aplican.
		 *
		 *   Lo que hace la confusion es que el comentario del corpus en
		 *   L871 dice  "XXX: set to enable PTE/PDE in system memory"  y las
		 *   doce lineas siguientes ponen CERO.  Comentario y codigo se
		 *   contradicen dentro de la misma funcion,  y no hay ningun sitio en
		 *   el arbol que diga cual de los dos es el pretendido.  aqui se
		 *   sigue al CODIGO,  que es lo unico ejecutable,  y queda
		 *   NOT_DETERMINED cual es la intencion.  Ver el finding 1033.
		 *
		 *  La primera version trataba los dos como (a) y devolvia error, y
		 *  el error se leia como "le faltan campos a este registro" cuando
		 *  lo que sobra es que se intentaba escribir un campo que nadie
		 *  escribe.  Y haberlos tratado como (b) seria peor:  los tres
		 *  simbolicos de (a) se quedarian en 0xffffffff recortado, es
		 *  decir, fragmentacion y tamano de bloque puestos a su valor
		 *  maximo por un RMW que solo pretendia preservar lo demas. */
		if (f->prov == RX550_FIELD_DECLARED_NOT_WRITTEN)
			continue;
		if (f->corpus == RX550_FIELD_NO_CORPUS) {
			int rc2;

			rc2 = rx550_gart_valor_simbolico(f->reg, f->name, p,
							    &valor);
			if (rc2 != 0)
				return rc2;
		} else {
			valor = f->corpus;
		}
		rc = rx550_mmio_apply_field(v, f->mask, valor, &v);
		if (rc != RX550_MMIO_OK)
			return RX550_GART_SEQ_ERR_TABLE;
		aplicados++;
	}
	if (aplicados == 0)
		return RX550_GART_SEQ_ERR_TABLE;
	*out = v;
	return 0;
}

/* Prototipo.  El constructor esta definido mas arriba en este fichero y aun
 * asi gcc lo daba por no declarado en el uso;  un prototipo quita la
 * dependencia del orden, que es lo unico que puede cambiar al reordenar el
 * fichero.  No es cosmetico:  sin el, una reordenacion que compile igual puede
 * dejar de compilar, y ese es el tipo de fallo que solo aparece en el
 * committed de otra persona. */
static int rx550_gart_rmw_componer(const char *mnemo, uint32_t cur,
			       const struct rx550_gart_params *p,
			       uint32_t *out);

int rx550_gart_seq_build(struct rx550_gart_seq *out,
			 const struct rx550_gart_params *p)
{
	struct rx550_gart_seq tmp;
	uint32_t table_pfn, dummy_pfn;
	unsigned n = 0;

	if (out == NULL || p == NULL)
		return RX550_GART_SEQ_ERR_INCONSISTENT;

	/* ── VALIDACION, TODA ANTES DE CALCULAR NADA ────────────────────────
	 *
	 *  Un plan a medio poblar es peor que un error:  el llamante no tiene
	 *  forma de saber cuantas de las operaciones son validas. */
	if (p->gart_start > p->gart_end)
		return RX550_GART_SEQ_ERR_GEOMETRY;
	/* 40 bits, porque el registro lleva un PHYSICAL_PAGE_NUMBER de 28 tras un
	 * >> 12, y truncar en silencio seria escribir una pagina que existe. */
	if (p->table_addr > RX550_PT_MAX_PD_ADDR)
		return RX550_GART_SEQ_ERR_GEOMETRY;
	if (p->dummy_page_addr > RX550_PT_MAX_PD_ADDR)
		return RX550_GART_SEQ_ERR_GEOMETRY;
	if (p->gart_start > RX550_PT_MAX_PD_ADDR ||
	    p->gart_end   > RX550_PT_MAX_PD_ADDR)
		return RX550_GART_SEQ_ERR_GEOMETRY;
	/* El campo de la ventana tiene 28 bits de numero de pagina. */
	if ((p->gart_end >> RX550_PAGE_SHIFT) > 0x0FFFFFFFu)
		return RX550_GART_SEQ_ERR_GEOMETRY;
	/* block_size y fragment_size van a campos de 4 bits.  Un valor de mas no
	 * cabe, y la escritura seria recortada sin avisar. */
	if (p->block_size > 15u || p->fragment_size > 15u)
		return RX550_GART_SEQ_ERR_GEOMETRY;
	/*  CORREGIDO.  Aqui habia una comprobacion que el corpus NO tiene:
	 *
	 *      if ((p->gart_end >> 12) >= p->max_pfn) return -GEOMETRY;
	 *
	 *  La razon de pensar que era necessary:  que la ventana del GART
	 *  "cabe dentro" de la ventana del VM.  Y es FALSO, y medido:
	 *
	 *      contexto 0   gmc_v8_0.c:886  START = gmc.gart_start >> 12
	 *      contexto 0   gmc_v8_0.c:887  END   = gmc.gart_end   >> 12
	 *      contexto 1   gmc_v8_0.c:908  END   = vm_manager.max_pfn - 1
	 *
	 *  Son DOS contextos distintos con DOS ventanas distintas, y el corpus no
	 *  las anida:  no hay ninguna relacion entre gart_end y max_pfn.  En esta
	 *  tarjeta, ademas, NO PODRIAN anidarse:
	 *
	 *      ventana del GART  >> 12  =  267452415   (la GART esta en 0xFF00000000)
	 *      ventana del VM          =   16777216   ("vm size is 64 GB")
	 *
	 *  O sea que la comprobacion rechazaba la geometria REAL de esta tarjeta.
	 *  El contexto 0 existe precisamente para dejar que la GART viva por
	 *  encima del limite del VM:  su PAGE_TABLE_DEPTH es 0, y con una sola
	 *  tabla la direccion se usa como indice directo, sin los 2 niveles que
	 *  imponen el limite.
	 *
	 *  Lo que SI tiene que caber, y es lo unico medido, es el ancho del
	 *  campo.  Los dos extremos van a un PHYSICAL_PAGE_NUMBER de 28 bits, y
	 *  los dos se comprueban. */
	if (p->max_pfn == 0u)
		return RX550_GART_SEQ_ERR_GEOMETRY;	/* max_pfn - 1 no existe */
	if ((p->max_pfn - 1u) > 0x0FFFFFFFu)
		return RX550_GART_SEQ_ERR_GEOMETRY;	/* el END del ctx1 no cabe */
	if ((p->gart_start >> RX550_PAGE_SHIFT) > 0x0FFFFFFFu)
		return RX550_GART_SEQ_ERR_GEOMETRY;

	table_pfn = (uint32_t)(p->table_addr >> RX550_PAGE_SHIFT);
	dummy_pfn = (uint32_t)(p->dummy_page_addr >> RX550_PAGE_SHIFT);

	memset(&tmp, 0, sizeof(tmp));

	for (unsigned o = 0; o < O_NR; o++) {
		uint32_t reg, val;

		/*  EL BUCLE DE CONTEXTOS, y va AQUI.
		 *
		 *  No despues del final, que es donde estaba:  el corpus lo pone
		 *  entre mmVM_CONTEXT1_PAGE_TABLE_END_ADDR y
		 *  mmVM_CONTEXT1_PROTECTION_FAULT_DEFAULT_ADDR, o sea entre la
		 *  posicion 15 y la 17 del orden.
		 *
		 *      gmc_v8_0.c:907  WREG32(mmVM_CONTEXT1_PAGE_TABLE_START_ADDR, 0)
		 *      gmc_v8_0.c:908  WREG32(mmVM_CONTEXT1_PAGE_TABLE_END_ADDR, max_pfn-1)
		 *      gmc_v8_0.c:910  for (i = 1; i < AMDGPU_NUM_VMID; i++)  <-- aqui
		 *      gmc_v8_0.c:921  WREG32(mmVM_CONTEXT1_PROTECTION_FAULT_DEFAULT_ADDR, ...)
		 *
		 *  La primera version emitia las 19 explicitas, luego las 15 del
		 *  bucle, y al final no emitia de nuevo las tres ultimas.  El plan
		 *  tenia 34 operaciones y las ultimas eran del bucle:  parecía
		 *  contaban bien, y aun asi el orden estaba equivocado.
		 *
		 *  El orden de las escrituras de contexto no es cosmetico:  la tabla
		 *  base se programa antes de habilitar el contexto, y no despues. */
		if (o == (unsigned)O_CTX1_LOOP) {
			for (unsigned vmid = 1u; vmid < 16u; vmid++) {
				uint32_t rl = rx550_gart_ctx_index(vmid);

				if (rl == 0u)
					return RX550_GART_SEQ_ERR_TABLE;
				if (n >= RX550_GART_OPS_NR)
					return RX550_GART_SEQ_ERR_TABLE;
				tmp.op[n].reg = rl;
				tmp.op[n].value = table_pfn;
				tmp.op[n].verificable =
					rx550_gart_es_legible(rl);
				n++;
			}
			continue;
		}

		/*  Comprobacion explicita de la ranura vacia, y REDUNDANTE con el
		 *  NULL protegido en reg_index().  Se pone igual, y conviene decir
		 *  por que, porque un self-test acaba de medirlo:
		 *
		 *      las dos guardas puestas,  bucle desactivado   ->  exit 1,  4 FAIL
		 *      las dos quitadas,        bucle desactivado   ->  SIGSEGV,  exit 139
		 *
		 *  Y quitar solo una no lo detecta nadie,  porque en codigo correcto
		 *  la ranura vacia no se alcanza.  O sea:  NINGUN TEST CUBRE ESTAS
		 *  DOS LINEAS,  y no se puede cubrir sin fabricar un desajuste.
		 *
		 *  Se quedan por el motivo medido,  no por cobertura:  el hardware
		 *  no reintenta un SIGSEGV y un codigo de error si,  y en un modulo
		 *  del kernel la diferencia no es academica.  Y el camino para
		 *  resolverlo de verdad ya existe:  que la tabla de orden deje de
		 *  llevar un NULL como centinela y que cada posicion diga que
		 *  clase de escritura es.  Para entonces estas dos lineas sobran y
		 *  habria que quitarlas. */
		if (rx550_gart_orden[o] == NULL)
			return RX550_GART_SEQ_ERR_TABLE;
		if (!rx550_gart_reg_index(rx550_gart_orden[o], &reg))
			return RX550_GART_SEQ_ERR_TABLE;

		switch (o) {
		case O_CTX0_PT_START:
			val = (uint32_t)(p->gart_start >> RX550_PAGE_SHIFT);
			break;
		case O_CTX0_PT_END:
			val = (uint32_t)(p->gart_end >> RX550_PAGE_SHIFT);
			break;
		case O_CTX0_PT_BASE:
			val = table_pfn;
			break;
		/*  CORREGIDO.  CTX1_PROT_FAULT estaba en el MISMO case que
		 *  CTX0_PT_BASE, y los dos valian table_pfn.  No:  la pagina dummy
		 *  va a los DOS contextos.
		 *      gmc_v8_0.c:889  mmVM_CONTEXT0_PROTECTION_FAULT_DEFAULT_ADDR
		 *                          <- adev->dummy_page_addr >> 12
		 *      gmc_v8_0.c:921  mmVM_CONTEXT1_PROTECTION_FAULT_DEFAULT_ADDR
		 *                          <- adev->dummy_page_addr >> 12
		 *  Ponerle la raiz de la tabla de paginas haria que los faults del
		 *  contexto 1 apareciesen dentro de la propia tabla como si fueran
		 *  una pagina mapeada. */
		case O_CTX0_PROT_FAULT:
		case O_CTX1_PROT_FAULT:
			val = dummy_pfn;
			break;
		/*  mmVM_CONTEXT0_CNTL2 lo pone a CERO (L891) y
		 *  mmVM_CONTEXT1_CNTL2 lo pone a CUATRO (L923).  No es el mismo
		 *  valor y no es un descuido de la referencia:  gmc_v8_0.c:923 es
		 *  un 4. */
		case O_CTX0_CNTL2:
			val = 0;
			break;
		case O_CTX1_CNTL2:
			val = 4;
			break;
		case O_IDA_LOW:
		case O_IDA_HIGH:
		case O_IDA_OFFSET:
			/*  los tres en cero:  la identity aperture de VMID1 queda
			 *  DESHABILITADA, y es lo que hace la referencia. */
			val = 0;
			break;
		case O_CTX1_PT_START:
			val = 0;
			break;
		case O_CTX1_PT_END:
			val = (uint32_t)(p->max_pfn - 1u);
			break;
		default: {
			int r = rx550_gart_rmw_de[o];
			int rc;

			if (r < 0)
				return RX550_GART_SEQ_ERR_TABLE;
			rc = rx550_gart_rmw_componer(rx550_gart_orden[o],
						 p->cur[r], p, &val);
			if (rc != 0)
				return rc;
			break;
		}
		}

		if (n >= RX550_GART_OPS_NR)
			return RX550_GART_SEQ_ERR_TABLE;
		tmp.op[n].reg = reg;
		tmp.op[n].value = val;
		tmp.op[n].verificable = rx550_gart_es_legible(reg);
		n++;
	}

	tmp.n = n;
	*out = tmp;
	return 0;
}

unsigned rx550_gart_seq_len(const struct rx550_gart_seq *s)
{
	return s ? s->n : 0u;
}

/* ═══════════════════════════════════════════════════════════════════════════
 * LA PARTE QUE TOCA EL MAPA
 *
 * Nada de esto se ha ejecutado.  Ver el finding 1030.
 * ═══════════════════════════════════════════════════════════════════════════ */

/* Los siete registros RMW, en el MISMO orden que enum rx550_gart_rmw.
 *
 *  Con designadores, y no en orden de escritura, porque el orden de escritura
 *  de la secuencia no es el de lectura y confundirlos daria un snapshot de
 *  otra cosa.  El orden de ESTE array es el que indices p->cur. */
static const enum rx550_vmid1_reg_id rx550_gart_rmw_regs[RX550_GART_RMW_NR] = {
	[RX550_GART_RMW_L1_TLB_CNTL] = RX550_REG_MX_L1_TLB_CNTL,
	[RX550_GART_RMW_L2_CNTL]     = RX550_REG_L2_CNTL,
	[RX550_GART_RMW_L2_CNTL2]    = RX550_REG_L2_CNTL2,
	[RX550_GART_RMW_L2_CNTL3]    = RX550_REG_L2_CNTL3,
	[RX550_GART_RMW_L2_CNTL4]    = RX550_REG_L2_CNTL4,
	[RX550_GART_RMW_CTX0_CNTL]   = RX550_REG_CTX0_CNTL,
	[RX550_GART_RMW_CTX1_CNTL]   = RX550_REG_CTX1_CNTL,
};

int rx550_gart_snapshot(const struct rx550_mmio_map *map, uint32_t *cur_out)
{
	uint32_t tmp[RX550_GART_RMW_NR];

	if (cur_out == NULL)
		return RX550_GART_SEQ_ERR_INCONSISTENT;

	/*  Se leen los siete ANTES de tocar la salida.  Un snapshot a medias deja
	 *  cur con unos valores del mapa y otros de antes,  y un plan construido
	 *  sobre eso parece valido. */
	for (unsigned k = 0; k < RX550_GART_RMW_NR; k++) {
		struct rx550_reg r;
		int rc;

		if (rx550_mmio_reg_of(rx550_gart_rmw_regs[k], &r) != RX550_MMIO_OK)
			return RX550_GART_SEQ_ERR_TABLE;
		rc = rx550_mmio_read32(map, r, &tmp[k]);
		if (rc != RX550_MMIO_OK)
			return rc;
	}
	memcpy(cur_out, tmp, sizeof(tmp));
	return 0;
}

int rx550_gart_build_from(const struct rx550_mmio_map *map,
			 struct rx550_gart_seq *seq,
			 const struct rx550_gart_params *p)
{
	uint32_t cur[RX550_GART_RMW_NR];
	int rc;

	if (map == NULL || seq == NULL || p == NULL)
		return RX550_GART_SEQ_ERR_INCONSISTENT;
	/* Se lee PRIMERO.  Un plan construido con unos cur que nadie ha leido del
	 * hardware es coherente y no quiere decir nada. */
	rc = rx550_gart_snapshot(map, cur);
	if (rc != 0)
		return rc;
	memcpy((uint32_t *)p->cur, cur, sizeof(cur));
	return rx550_gart_seq_build(seq, p);
}

int rx550_gart_apply(const struct rx550_mmio_map *map,
		     const struct rx550_gart_seq *seq,
		     struct rx550_gart_apply_report *out)
{
	struct rx550_gart_apply_report rep;

	if (map == NULL || seq == NULL || out == NULL)
		return RX550_GART_SEQ_ERR_INCONSISTENT;

	/*  El plan tiene que estar entero.  Aplicar 19 de 34 cuando el constructor
	 *  ha devuelto error,  o un plan con el numero de operaciones cambiado a
	 *  mano,  escribe un GART a medias:  el contexto 0 habilitado con la tabla
	 *  antigua,  o al reves.  No falla al hacerlo:  falla al mapear. */
	if (seq->n != RX550_GART_OPS_NR)
		return RX550_GART_SEQ_ERR_TABLE;

	memset(&rep, 0, sizeof(rep));
	/* Lo que habia, para que el informe lo diga aunque se pare en la
	 * primera operacion. */
	{
		int rc = rx550_gart_snapshot(map, rep.cur);

		if (rc != 0)
			return rc;
	}
	rep.primer_fallo = RX550_GART_NO_FALLO;

	for (unsigned i = 0; i < seq->n; i++) {
		struct rx550_reg r;
		uint32_t leido;
		int rc;

		rc = rx550_mmio_reg_of_index(seq->op[i].reg, &r);
		if (rc != RX550_MMIO_OK)
			return rc;

		rc = rx550_mmio_write32(map, r, seq->op[i].value);
		if (rc != RX550_MMIO_OK) {
			rep.n_escritas = i;
			*out = rep;
			return rc;
		}
		rep.n_escritas = i + 1u;

		/*  Registro de solo escritura:  se cuenta y se sigue.  Releerlo y
		 *  exigir la igualdad daria un fallo que no significa nada,  porque lo
		 *  que devolveria es lo que hubiera. */
		if (!seq->op[i].verificable) {
			rep.n_no_verificables++;
			continue;
		}

		/*  LA LECTURA DE VUELTA, solo aqui.  Es lo que separa "escrito" de
		 *  "aceptado" en los 9 registros que se pueden leer.  Contra la BAR5
		 *  real esto es lo unico que dira el hardware,  y por eso el apply se
		 *  para en el primer fallo en vez de seguir:  el primer fallo es el
		 *  sintoma,  y los siguientes son consecuencia. */
		rc = rx550_mmio_read32(map, r, &leido);
		if (rc != RX550_MMIO_OK) {
			rep.primer_fallo = i;
			rep.leido = 0;
			rep.escrito = seq->op[i].value;
			*out = rep;
			return rc;
		}
		if (leido == seq->op[i].value) {
			rep.n_verificadas++;
			continue;
		}
		rep.primer_fallo = i;
		rep.leido = leido;
		rep.escrito = seq->op[i].value;
		*out = rep;
		return RX550_GART_SEQ_ERR_TABLE;
	}

	*out = rep;
	return 0;
}


int rx550_gart_tlb_flush(const struct rx550_mmio_map *map, unsigned vmid)
{
	struct rx550_reg req;
	int rc;

	if (map == NULL)
		return RX550_GART_SEQ_ERR_INCONSISTENT;
	/*  El campo es de 16 dominios  (gmc_8_1_sh_mask.h,  mask 0xffff),  y el
	 *  corpus escribe  1 << vmid  con vmid < 16.  Aceptar 16 haria que
	 *  1 << 16  se truncara a 0  en un uint32_t,  que es el identificador de
	 *  "ningun dominio":  escribir 0  invalida lo que sea que haya. */
	if (vmid >= 16u)
		return RX550_GART_SEQ_ERR_GEOMETRY;

	rc = rx550_mmio_reg_of(RX550_REG_INVALIDATE_REQUEST, &req);
	if (rc != RX550_MMIO_OK)
		return RX550_GART_SEQ_ERR_TABLE;

	/*  UNA escritura, sin mb() y sin flush de HDP.
	 *
	 *  La ruta de runtime del corpus SI lo hace:
	 *      amdgpu_gart.c:499-505   mb()  ->  amdgpu_device_flush_hdp()  ->  WREG32
	 *  pero la ruta que estamos reproduciendo,  gmc_v8_0.c:940,  NO lo hace,  y
	 *  no hay motivo para anadirlo:  las 34 escrituras anteriores son del mismo
	 *  mapa y del mismo driver,  asi que el orden ya lo dan los writel.  Se anade
	 *  solo si se replica la ruta de runtime,  que no es la que se esta
	 *  reproduciendo.  Y esa decision esta anotada en rx550_vmid0_gart.h. */
	return rx550_mmio_write32(map, req, (uint32_t)1u << vmid);
}

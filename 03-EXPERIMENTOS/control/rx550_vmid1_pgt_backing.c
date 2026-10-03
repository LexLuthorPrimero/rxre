// SPDX-License-Identifier: GPL-2.0-only
/*
 * rx550_vmid1_pgt_backing.c — la propiedad fisica del PGT de VMID1.
 *
 *   TARGET = RX 550 instalada en esta maquina  (1002:699F, Polaris12, GFX8)
 *   SCOPE  = EXCLUSIVO
 *
 * C PURO.  Sin inline asm, sin MMIO, sin ioremap, sin readl/writel, sin ring,
 * sin acceso a GPU.  Compilable en userspace, que es lo que permite ejercitar
 * el unwinding y las dos politicas de hojas sin hardware.
 *
 * LO QUE ESTE FICHERO NO USA, Y POR QUE
 *   · rx550_pdb0.h          su encoding es de PTE y un PDE no tiene esos
 *                            campos.  No se incluye.
 *   · rx550_vmid0_gart.h    de ahi sale rx550_pte_encode, y ese es de PTE.
 *                            El root usa el encoder de PDE de M2.
 *   · ningun header del kernel  para que el unwinding se pruebe sin device.
 *                            El backend de dma_alloc_coherent() vive aparte,
 *                            en la unidad de traduccion del kernel.
 *
 * LO QUE NO HACE
 *   No programa ningun registro.  No calcula geometria:  la consume y la
 *   comprueba, y si no es valida no reserva memoria.
 */

#include <string.h>
#include <stdlib.h>
#include <stdint.h>

#include "rx550_vmid1_pgt_backing.h"

/* ═══════════════════════════════════════════════════════════════════════════
 * ERRORES PROPIOS
 *
 * Los de M2 se reutilizan tal cual, porque la causa es la misma.  Estos cuatro
 * son de ESTE modulo, y ninguno se solapa con los de M2.
 * ═══════════════════════════════════════════════════════════════════════════ */

const char *rx550_pgt_backing_err_str(int rc)
{
	switch (rc) {
	/* Los de M2,delegados:  el llamante ya sabe interpretarlos y duplicar
	 * las cadenas seria una segunda fuente de verdad para el mismo numero. */
	case RX550_PGT_OK:
		return "ok";
	case RX550_PGT_ERR_VM_SIZE:
		return "vm_size cero o no multiplo de la pagina";
	case RX550_PGT_ERR_OVERFLOW:
		return "la aritmetica de la geometria se desborda";
	case RX550_PGT_ERR_UNSUPPORTED_LEVEL:
		return "num_level distinto de 1";
	case RX550_PGT_ERR_UNSUPPORTED_BLOCK_SIZE:
		return "block_size fuera del rango codificable [9,24]";
	case RX550_PGT_ERR_VM_SIZE_INCOHERENT:
		return "la cobertura derivada no cubre la ventana pedida";
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

	case RX550_PGTB_ERR_NO_OPS:
		return "backend sin alloc o sin release";
	case RX550_PGTB_ERR_ALLOC:
		return "el backend de asignacion fallo";
	case RX550_PGTB_ERR_BAD_INDEX:
		return "indice de hoja fuera de rango";
	case RX550_PGTB_ERR_NOT_READY:
		return "el backing no esta creado";
	case RX550_PGTB_ERR_LEAF_RANGE:
		return "el rango de hojas no cabe en el campo 39:1";
	case RX550_PGTB_ERR_NOMEM:
		return "sin memoria para los arrays de control";
	default:
		return "error desconocido";
	}
}

/* ═══════════════════════════════════════════════════════════════════════════
 * UNWRIND:  UNA SOLA RUTA
 *
 * Toda liberacion de este modulo pasa por aqui.  Y hay una razon para que sea
 * UNA y no varias:  el estado de ownership de este objeto son tres banderas y
 * dos contadores, y si hubiera dos rutas que los tocan, la segunda que se
 * escribiera encontraria un estado que la primera no espera.  Un doble free no
 * se detecta comparando banderas:  se evita teniendo un solo sitio que las
 * baja.
 *
 * Y POR QUE EL CONTADOR ES EXPLICITO Y NO UN BARRIDO DE 0..leaf_count
 *
 * Porque barrer todas las hojas cuando solo hay tres vivas cuesta 1024
 * iteraciones y 1021 llamadas a un backend que ya no tiene nada que liberar.
 * Con leaf_live el bucle se detiene en la primera hoja no viva, y el numero de
 * llamadas al backend es exactamente el numero de reservas que se hicieron.
 * Eso es lo que B13 comprueba:  el recuento de frees tiene que igualar al
 * recuento de allocs, ni uno mas ni uno menos.
 * ═══════════════════════════════════════════════════════════════════════════ */
void rx550_pgt_backing_release_all(struct rx550_pgt_backing *b)
{
	uint32_t i;

	if (!b)
		return;

	/* 1. Las hojas, de la mas reciente a la mas antigua.  Al reves de la de
	 *    creacion, para que si un backend bizarre dejara alguna traza, la
	 *    traza sea la de la ultima reserva liberada primero.
	 *
	 * Y LA GUARDA ES leaf_owned, NO leaves[k].attached.  La propiedad la
	 * establece la reserva, y hay hojas reservadas cuyo attach fallo y que
	 * por tanto no estan attached pero SI son nuestras, y liberarlas por
	 * attached las deja huerfanas. */
	for (i = b->leaf_live; i > 0u; i--) {
		uint32_t k = i - 1u;

		if (b->policy == RX550_PGT_LEAF_PER_PAGE) {
			/* El tamano que se libera es el que se PIDIO, que sale de
			 * la geometria.  No el que tenga el struct de la hoja, que
			 * solo lo tiene si attach llego a ejecutarse. */
			if (b->leaf_owned && b->leaf_owned[k] && b->ops.release)
				b->ops.release(b->ops.ctx,
					       (b->geom ? b->geom->pte_page_bytes : 0u),
					       b->leaves ? b->leaves[k].entries : NULL,
					       b->leaf_dma ? b->leaf_dma[k]
							   : b->leaf_block_dma);
			if (b->leaf_owned)
				b->leaf_owned[k] = 0u;
			if (b->leaves)
				(void)rx550_vmid1_pte_page_clear(&b->leaves[k]);
		}
		if (b->leaf_dma)
			b->leaf_dma[k].value = 0;
	}

	/* 2. El bloque unico de hojas, si lo hubo.  Con SINGLE_BLOCK las hojas no
	 *    son reservas propias:  son vistas sobre un unico bloque, y por eso
	 *    no se liberan aqui una por una. */
	if (b->leaf_block_cpu && b->ops.release)
		b->ops.release(b->ops.ctx, b->leaf_block_bytes,
			       b->leaf_block_cpu, b->leaf_block_dma);
	b->leaf_block_cpu = NULL;
	b->leaf_block_dma.value = 0;
	b->leaf_block_bytes = 0;
	b->leaf_live = 0;

	/* 3. El root. */
	if (b->root_live && b->ops.release)
		b->ops.release(b->ops.ctx, b->root.bytes, b->root.entries,
			       b->root_dma);
	b->root_live = false;
	b->root_dma.value = 0;
	b->root.entries = NULL;
	b->root.attached = false;

	b->live_bytes = 0;
	b->created = false;
}

/* ═══════════════════════════════════════════════════════════════════════════
 * CREACION
 * ═══════════════════════════════════════════════════════════════════════════ */
int rx550_pgt_backing_create(struct rx550_pgt_backing *b,
			     const struct rx550_vmid1_geom *geom,
			     const struct rx550_pgt_alloc_ops *ops,
			     enum rx550_pgt_leaf_policy policy)
{
	uint32_t i;
	int rc;

	if (!b || !geom || !ops)
		return RX550_PGT_ERR_INCONSISTENT;

	memset(b, 0, sizeof(*b));

	/* EL ORDEN DE ESTAS COMPROBACIONES ES EL QUE HACE QUE UNA VENTANA
	 * IMPOSIBLE NO PIDA MEMORIA. */
	if (!geom->valid)
		return RX550_PGT_ERR_INCONSISTENT;
	if (!ops->alloc || !ops->release)
		return RX550_PGTB_ERR_NO_OPS;
	if (geom->root_bytes == 0 || geom->pte_pages == 0
	    || geom->pte_page_bytes == 0)
		return RX550_PGT_ERR_INCONSISTENT;
	if (policy != RX550_PGT_LEAF_SINGLE_BLOCK
	    && policy != RX550_PGT_LEAF_PER_PAGE)
		return RX550_PGT_ERR_INCONSISTENT;
	/* El rango de leaf_bytes tiene que caber en el tamaño que se pide, y
	 * ese producto es el que puede desbordar. */
	if (geom->pte_pages > (UINT64_MAX / geom->pte_page_bytes))
		return RX550_PGT_ERR_OVERFLOW;

	b->geom		= geom;
	b->ops		= *ops;		/* por valor: el llamante no puede mutarlo */
	b->policy	= policy;
	b->leaf_count	= geom->pte_pages;
	b->created	= true;

	/* ── 1. ROOT ───────────────────────────────────────────────────────
	 * El tamano sale de geom->root_bytes.  NO hay un 4096 ni un 8192 en
	 * este fichero:  con block_size 9 son 4096 y con 10 son 8192, y el
	 * valor lo decide la geometria. */
	{
		void *root_cpu = NULL;

		rc = b->ops.alloc(b->ops.ctx, geom->root_bytes,
				  &root_cpu, &b->root_dma);
		if (rc)
			goto fail_alloc;
		/* El buffer de entradas del root es uint64_t*, y el backend
		 * entrega void*.  La conversion se hace AQUI, una vez, y con
		 * una comprobacion de que no es NULL.  Es el unico sitio donde
		 * un void* se convierte en uint64_t*, y por eso tiene nombre. */
		b->root.entries = (uint64_t *)root_cpu;
	}
	b->alloc_calls++;
	b->live_bytes += geom->root_bytes;

	/* Se valida la direccion ANTES de engancharla, con el validador del
	 * ROOT:  28 bits de numero de pagina, que no es el campo de una hoja. */
	/* La PROPIEDAD se establece aqui, con la reserva.  Si seestableciera
	 * despues de validar, entonces un root cuya direccion no sirve se
	 * quedaria reservado y no liberado, porque root_live seguiria en
	 * false.  Esa fuga no se ve en ningun flag:  se ve en que el contador de
	 * liberaciones no cuadra, mucho mas tarde y en otro sitio. */
	b->root_live = true;

	if (!rx550_vmid1_root_representable(b->root_dma.value)) {
		rc = RX550_PGT_ERR_ROOT_UNREPRESENTABLE;
		goto fail;
	}

	rc = rx550_vmid1_root_attach(&b->root, geom, b->root.entries,
				     b->root_dma.value);
	if (rc)
		goto fail;

	/* ── 2. HOJAS ────────────────────────────────────────────────────── */
	if (b->leaf_count > 0) {
		b->leaves = (struct rx550_vmid1_pte_page *)
			calloc(b->leaf_count, sizeof(*b->leaves));
		b->leaf_dma = (struct rx550_dma_addr *)
			calloc(b->leaf_count, sizeof(*b->leaf_dma));
		b->leaf_owned = (uint8_t *)calloc(b->leaf_count, 1u);
		if (!b->leaves || !b->leaf_dma || !b->leaf_owned) {
			rc = RX550_PGTB_ERR_NOMEM;
			goto fail;
		}
	}

	if (policy == RX550_PGT_LEAF_SINGLE_BLOCK) {
		/*
		 * UNA reserva para todas las hojas.
		 *
		 * Y LA RESTRICCION QUE A IMPONE Y B NO:  el rango ENTERO tiene
		 * que caber bajo el bit 39.  No porque un solo campo lo
		 * direccione —cada hoja tiene su PDE con su propio campo 39:1—
		 * sino porque si el rango entero se sale de 2^40, las hojas
		 * AL FINAL no tendrian representacion, y eso se detecta aqui y
		 * no en un ring.  Se comprueba con el ULTIMO byte, porque es el
		 * extremo alto del rango el que decide.
		 *
		 * Con la geometria maxima aceptada son 8 MiB, luego hoy no
		 * aprieta, pero se comprueba para que un valor inesperado se
		 * detecte AQUI.
		 *
		 * Y LO QUE NO SE COMPRUEBA, QUE ES LA CONFUSION QUE ESTA
		 * CABECERA ADVIERTE Y QUE LA PRIMERA VERSION DE ESTE CODIGO
		 * TENIA:  la alineacion del PUNTERO DE CPU.
		 *
		 * No hay ningun requisito de 4 KiB sobre una VA de kernel, y
		 * calloc() no la da.  Comprobarlo rechazaba todas las
		 * reservas reales.  La alineacion que importa es la de la
		 * DIRECCION DMA, y la comprueba rx550_vmid1_leaf_representable()
		 * hoja por hoja, mas el rango de aqui.
		 */
		uint64_t total = (uint64_t)geom->pte_pages * geom->pte_page_bytes;
		uint64_t last;

		if (total == 0) {
			rc = RX550_PGT_ERR_INCONSISTENT;
			goto fail;
		}

		rc = b->ops.alloc(b->ops.ctx, total, &b->leaf_block_cpu,
				  &b->leaf_block_dma);
		if (rc)
			goto fail;
		b->alloc_calls++;
		b->live_bytes += total;
		b->leaf_block_bytes = total;

		if (!rx550_vmid1_leaf_representable(b->leaf_block_dma.value)) {
			rc = RX550_PGT_ERR_LEAF_UNALIGNED;
			goto fail;
		}
		last = b->leaf_block_dma.value + total - 1u;
		if ((last & ~RX550_PDE_ADDR_MASK) != 0) {
			rc = RX550_PGTB_ERR_LEAF_RANGE;
			goto fail;
		}

		for (i = 0; i < b->leaf_count; i++) {
			struct rx550_dma_addr d;

			d.value = b->leaf_block_dma.value
				  + (uint64_t)i * geom->pte_page_bytes;

			/* Cada hoja se valida por separado igual, aunque el
			 * rango entero ya haya pasado.  Es la validacion que
			 * importa, y es la de la hoja:  campo 39:1. */
			if (!rx550_vmid1_leaf_representable(d.value)) {
				rc = RX550_PGT_ERR_LEAF_UNREPRESENTABLE;
				goto fail;
			}
			rc = rx550_vmid1_pte_page_attach(&b->leaves[i], geom,
							 b->leaf_block_cpu
							 + (uint64_t)i * geom->pte_page_bytes,
							 d.value);
			if (rc)
				goto fail;
			b->leaf_dma[i] = d;
			b->leaf_live = i + 1u;
		}
	} else {
		/* UNA reserva por hoja.  Y el fallo a mitad es el caso que B8
		 * ejercita:  el unwinding tiene que soltar las k vivas y el
		 * root, y no dejar nada. */
		for (i = 0; i < b->leaf_count; i++) {
			struct rx550_dma_addr d;
			void *cpu = NULL;

			rc = b->ops.alloc(b->ops.ctx, geom->pte_page_bytes,
					  &cpu, &d);
			if (rc) {
				rc = RX550_PGTB_ERR_ALLOC;
				goto fail;
			}
			b->alloc_calls++;
			b->live_bytes += geom->pte_page_bytes;
			/* La hoja es NUESTRA desde este punto, y el unwinding
			 * depende de estas tres lineas en este orden:
			 *   · entries      el puntero que hay que devolver
			 *   · leaf_live    cuantas hay vivas, para el bucle
			 *   · leaf_owned   la marca de propiedad que mira la
			 *                 liberacion
			 * Si se pusieran despues de validar, una hoja con una
			 * direccion mala quedaria reservada y no liberada. */
			b->leaves[i].entries = cpu;
			b->leaf_live = i + 1u;
			b->leaf_owned[i] = 1u;

			if (!rx550_vmid1_leaf_representable(d.value)) {
				rc = RX550_PGT_ERR_LEAF_UNREPRESENTABLE;
				goto fail;
			}
			rc = rx550_vmid1_pte_page_attach(&b->leaves[i], geom,
							 cpu, d.value);
			if (rc)
				goto fail;
			b->leaf_dma[i] = d;
		}
	}

	/* ── 3. INICIALIZACION ─────────────────────────────────────────────
	 * Root y hojas a cero, que es "no valida" porque el bit 0 es VALID en
	 * LOS DOS formatos (gmc_v8_0.c:709 para el PDE, :702 para el PTE).
	 * Y no se inventa semantica de pagina dummy aqui:  eso no esta cerrado
	 * y es de M6. */
	rc = rx550_vmid1_root_clear(&b->root);
	if (rc)
		goto fail;
	for (i = 0; i < b->leaf_count; i++) {
		rc = rx550_vmid1_pte_page_clear(&b->leaves[i]);
		if (rc)
			goto fail;
	}

	return RX550_PGT_OK;

fail_alloc:
	rc = RX550_PGTB_ERR_ALLOC;
	goto fail;

fail:
	/* Un solo camino de salida para todo fallo.  Y el unwinding es el
	 * mismo que usa destroy, no uno paralelo:  ver la nota de
	 * rx550_pgt_backing_release_all(). */
	rx550_pgt_backing_release_all(b);
	free(b->leaves);
	free(b->leaf_dma);
	free(b->leaf_owned);
	b->leaves = NULL;
	b->leaf_dma = NULL;
	b->leaf_owned = NULL;
	return rc;
}

void rx550_pgt_backing_destroy(struct rx550_pgt_backing *b)
{
	if (!b)
		return;
	rx550_pgt_backing_release_all(b);
	free(b->leaves);
	free(b->leaf_dma);
	free(b->leaf_owned);
	b->leaves = NULL;
	b->leaf_dma = NULL;
	b->leaf_owned = NULL;
}

/* ═══════════════════════════════════════════════════════════════════════════
 * LOS ACCESORES
 *
 * Todos comprueban antes de devolver.  Un valor de retorno que ante un objeto
 * no creado devuelva 0 es un 0 que el llamante no puede distinguir de una
 * direccion real.
 * ═══════════════════════════════════════════════════════════════════════════ */
int rx550_pgt_backing_root_dma(const struct rx550_pgt_backing *b,
			       struct rx550_dma_addr *out)
{
	if (!b || !out)
		return RX550_PGT_ERR_INCONSISTENT;
	if (!b->root_live)
		return RX550_PGTB_ERR_NOT_READY;
	*out = b->root_dma;
	return RX550_PGT_OK;
}

int rx550_pgt_backing_root_base_pn(const struct rx550_pgt_backing *b,
				   uint32_t *out_pn)
{
	if (!b || !out_pn)
		return RX550_PGT_ERR_INCONSISTENT;
	if (!b->root_live)
		return RX550_PGTB_ERR_NOT_READY;
	/* Delega en el validador del ROOT de M2, no en una cuenta propia.  Una
	 * segunda cuenta seria un segundo criterio de representabilidad. */
	return rx550_vmid1_root_base_pn(b->root_dma.value, out_pn);
}

int rx550_pgt_backing_leaf_dma(const struct rx550_pgt_backing *b, uint32_t index,
			       struct rx550_dma_addr *out)
{
	if (!b || !out)
		return RX550_PGT_ERR_INCONSISTENT;
	if (index >= b->leaf_count)
		return RX550_PGTB_ERR_BAD_INDEX;
	/* Una hoja viva, no solo una hoja reservada:  con PER_PAGE el indice
	 * puede existir y no estar reservada todavia. */
	if (!b->leaf_live || index >= b->leaf_live)
		return RX550_PGTB_ERR_NOT_READY;
	*out = b->leaf_dma[index];
	return RX550_PGT_OK;
}

/*
 * El punto donde backing y encoder se unen.  Y el unwrap del tipo es UNA
 * linea explicita, no un cast suelto:  la dma_addr_t del backing es un tipo con
 * nombre y el encoder de M2 toma un uint64_t, y ese borde merece estar visible.
 */
int rx550_pgt_backing_encode_leaf_pde(const struct rx550_pgt_backing *b,
				      uint32_t index, uint64_t *out_pde)
{
	struct rx550_dma_addr d;
	int rc;

	if (!b || !out_pde)
		return RX550_PGT_ERR_INCONSISTENT;

	rc = rx550_pgt_backing_leaf_dma(b, index, &d);
	if (rc)
		return rc;

	/* UNWRAP, y es el unico del fichero. */
	return rx550_vmid1_pde_encode(d.value, out_pde);
}

const struct rx550_vmid1_geom *rx550_pgt_backing_geom(
	const struct rx550_pgt_backing *b)
{
	return b ? b->geom : NULL;
}

/* ═══════════════════════════════════════════════════════════════════════════
 * INVARIANTES, COMPRUEBADAS Y NO AFIRMADAS
 * ═══════════════════════════════════════════════════════════════════════════ */
bool rx550_pgt_backing_is_complete(const struct rx550_pgt_backing *b)
{
	uint32_t i;

	if (!b || !b->geom)
		return false;
	if (!b->root_live)
		return false;
	if (b->leaf_live != b->leaf_count)
		return false;
	if (b->root.bytes != b->geom->root_bytes)
		return false;
	if (!rx550_vmid1_root_representable(b->root_dma.value))
		return false;
	for (i = 0; i < b->leaf_count; i++) {
		if (!b->leaves[i].attached)
			return false;
		if (!rx550_vmid1_leaf_representable(b->leaf_dma[i].value))
			return false;
		if (b->leaves[i].bytes != b->geom->pte_page_bytes)
			return false;
	}
	return true;
}

/*
 * Que no quede ownership por la mitad.  Y el criterio es el que B13 mide:  lo
 * que queda reservado tiene que ser exactamente lo que se reserve, ni una hoja
 * de mas, ni una reserva huerfana.
 */
bool rx550_pgt_backing_has_no_ownership(const struct rx550_pgt_backing *b)
{
	if (!b)
		return false;
	if (b->root_live)
		return false;
	if (b->leaf_live != 0)
		return false;
	if (b->leaf_block_cpu != NULL)
		return false;
	if (b->root.entries != NULL)
		return false;
	if (b->root_dma.value != 0)
		return false;
	return true;
}

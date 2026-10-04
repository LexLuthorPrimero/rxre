/* SPDX-License-Identifier: GPL-2.0 */
/*
 * rx550_gart_boot.c — la secuencia, en orden.  Puro: sin MMIO propio.
 *
 * Cada paso delega en la pieza que ya existe y ya esta probada.  Aqui no hay
 * aritmetica nueva ni acceso nuevo:  lo unico que se anade es el ORDEN, y el
 * orden es la parte que antes no estaba escrita en ningun sitio.
 *
 * LO QUE NO ESTA Y POR QUE:
 *   - No pide el bus ni mapea la BAR.  Eso es rx550_target.c, y exige el
 *     takeover.
 *   - No calcula la geometria.  Eso es rx550_gart_geometry(), y esta funcion es
 *     su CONSUMIDORA:  recibe la ventana ya decidida y la vuelve a validar, que
 *     es lo que hacia el resto del componente.
 *   - No inventa block_size, fragment_size ni max_pfn.  Los recibe marcados
 *     como MODELO en la cabecera, porque MEDIDO no hay ningun codigo que los
 *     fije desde una lectura, y ese es el unico sitio del componente donde se
 *     podria estar inventando un valor.
 */
#include "rx550_gart_boot.h"

int rx550_gart_boot(const struct rx550_gart_boot_req *req,
		    struct rx550_gart_boot_report *out)
{
	struct rx550_gart_params p;
	uint64_t *tabla;
	int rc;
	unsigned i;

	if (req == NULL || out == NULL)
		return RX550_GART_BOOT_ERR_NULO;

	/* Se escribe el informe entero primero.  Un informe que solo se rellena
	 * en el camino de exito no informa de nada cuando hay fallo, que es
	 * justo cuando hace falta. */
	out->ultimo_paso     = RX550_GART_BOOT_PRESENTE;
	out->err             = RX550_GART_BOOT_OK;
	out->rc_del_paso     = 0;
	out->tabla_gpu_offset = 0;
	out->plan_len        = 0;
	rx550_vram_resource_reset(&out->res);
	/* Sin memset: este .c compila de las dos formas y <string.h> no es la
	 * cabecera que existe en kernel.  Mismo motivo que en
	 * rx550_vram_pool.h. */
	{
		const uint64_t cero64 = 0;
		const uint32_t cero32 = 0;
		unsigned i;

		out->geom.max_mc_address      = cero64;
		out->geom.fb_end              = cero64;
		out->geom.size_below          = cero64;
		out->geom.size_above          = cero64;
		out->geom.gart_size_effective = cero64;
		out->geom.gart_start          = cero64;
		out->geom.gart_end            = cero64;
		out->geom.clamped             = false;

		out->tabla_geom.paginas       = cero64;
		out->tabla_geom.bytes         = cero64;
		out->tabla_geom.entradas_max  = cero32;

		out->seq.n  = cero32;
		out->apply.n_escritas          = cero32;
		out->apply.n_verificadas       = cero32;
		out->apply.n_no_verificables   = cero32;
		out->apply.primer_fallo       = cero32;
		out->apply.leido              = cero32;
		out->apply.escrito            = cero32;
		for (i = 0; i < (unsigned)(sizeof(out->seq.op) /
					  sizeof(out->seq.op[0])); i++) {
			out->seq.op[i].reg   = cero32;
			out->seq.op[i].value = cero32;
		}
		for (i = 0; i < (unsigned)(sizeof(out->apply.cur) /
					  sizeof(out->apply.cur[0])); i++)
			out->apply.cur[i] = cero32;
	}

	if (req->map == NULL || req->pool == NULL) {
		out->err = RX550_GART_BOOT_ERR_NULO;
		return out->err;
	}

	/* ── 0 · GEOMETRIA, Y PRIMERO.  MEDIDO 2026-10-04: esto estaba despues de la
	 * reserva, y era un BUG DE ORDEN mio.  Con gart_start > gart_end el
	 * `gart_end - gart_start + 1` de abajo se va en unsigned y la funcion de la
	 * tabla recibia un numero gigante, de modo que el fallo salia por el paso
	 * de la RESERVA y el informe decia que no habia sitio cuando lo que
	 * pasaba era que la ventana estaba al reves.  Un informe que senala el paso
	 * equivocado es peor que uno que no senale ninguno:  manda a mirar donde
	 * no es.
	 *
	 * La geometria entra DECIDIDA:  la produce rx550_gart_geometry(), que es
	 * puro, y esta funcion es su consumidora.  Aqui no se recalcula nada de la
	 * colocacion;  se validan las tres cosas que el hardware impone y que el
	 * resto del componente valida en el mismo sitio (rx550_gart_seq.c:408-421),
	 * para que un consumidor tenga UN lugar donde mirar y no dos reglas que
	 * puedan divergir en silencio. */
	out->ultimo_paso = RX550_GART_BOOT_GEOMETRIA;
	if (req->gart_start > req->gart_end) {
		out->err = RX550_GART_BOOT_ERR_GEOMETRIA;
		out->rc_del_paso = -1;
		return out->err;
	}
	if ((req->gart_start >> RX550_PAGE_SHIFT) > RX550_GART_GEOM_PN_MAX ||
	    (req->gart_end >> RX550_PAGE_SHIFT) > RX550_GART_GEOM_PN_MAX) {
		out->err = RX550_GART_BOOT_ERR_GEOMETRIA;
		out->rc_del_paso = -2;
		return out->err;
	}

	out->geom.gart_start          = req->gart_start;
	out->geom.gart_end            = req->gart_end;
	out->geom.gart_size_effective = req->gart_end - req->gart_start + 1;

	/* ── 1 · RESERVAR.  La tabla son 512 KiB alineados a 4096.  El tamanoy
	 * la alineacion NO se escriben aqui:  los calcula
	 * rx550_gart_tabla_geom() a partir de gart_size, que es donde vive esa
	 * aritmetica. */
	rc = rx550_gart_tabla_geom(req->gart_end - req->gart_start + 1,
				  &out->tabla_geom);
	if (rc != 0) {
		out->err = RX550_GART_BOOT_ERR_GEOMETRIA;
		out->rc_del_paso = rc;
		return out->err;
	}
	out->ultimo_paso = RX550_GART_BOOT_RESERVA;

	/* La alineacion NO viene de rx550_gart_tabla_geom(), que no la lleva:
	 * es un pagina,  y su procedencia es amdgpu_gart.c:272, que pide PAGE_SIZE
	 * al crear el BO.  Es un dato del corpus, no una eleccion nuestra. */
	rc = rx550_vram_pool_alloc(req->pool, out->tabla_geom.bytes,
				   RX550_PAGE_SIZE, &out->res);
	if (rc != RX550_VRAM_OK) {
		out->err = RX550_GART_BOOT_ERR_VRAM;
		out->rc_del_paso = rc;
		return out->err;
	}

	/* La direccion GPU de la tabla.  Es lo que va a PAGE_TABLE_BASE, y lo
	 * que el corpus saca con amdgpu_bo_gpu_offset() (gmc_v8_0.c:840).  Aqui
	 * es la base GPU de la ventana mas el offset que dio el pool. */
	out->tabla_gpu_offset = req->vram_base_gpu + out->res.offset.bytes;

	/* ── 2 · RELLENAR.  Cada entrada de 64 bits con el valor de entrada.
	 *  OJO con lo que esto NO es:  el corpus lo hace con memset_io, que
	 *  rellena por BYTE, y su entrada real queda 0x1010101010101010.  La
	 *  nota larga de rx550_gart_table.h explica por que aqui se escribe
	 *  0x10 por palabra y por que la diferencia es inobservable con
	 *  VALID = 0. */
	out->ultimo_paso = RX550_GART_BOOT_RELLENO;
	tabla = (uint64_t *)(uintptr_t)(req->vram_base_cpu +
					out->res.offset.bytes);
	rc = rx550_gart_tabla_reinicia(tabla, out->tabla_geom.paginas);
	if (rc < 0) {
		out->err = RX550_GART_BOOT_ERR_RELLENO;
		out->rc_del_paso = rc;
		return out->err;
	}

	/* ── 4 · PLAN.  build_from() lee el snapshot del hardware ANTES de
	 * construir, que es lo que hace que un campo no escrito se conserve.
	 *  Saltarse ese snapshot seria cambiar la semantica de la RMW. */
	out->ultimo_paso = RX550_GART_BOOT_PLAN;
	/* Sin memset, por el mismo motivo que arriba:  <string.h> no es la
	 * cabecera que existe en kernel.  Se rellena campo a campo, y asi se
	 * ve de un vistazo CUALES son los que importan:  si mañana se anade uno
	 * al struct, este bloque deja de compilar en vez de dejarlo a cero en
	 * silencio. */
	p.gart_start     = req->gart_start;
	p.gart_end       = req->gart_end;
	p.block_size     = req->block_size;
	p.fragment_size  = req->fragment_size;
	p.max_pfn        = req->max_pfn;
	p.table_addr     = out->tabla_gpu_offset;
	p.dummy_page_addr = req->dummy_page_addr;
	for (i = 0; i < (unsigned)(sizeof(p.cur) / sizeof(p.cur[0])); i++)
		p.cur[i] = 0;

	rc = rx550_gart_build_from(req->map, &out->seq, &p);
	if (rc != 0) {
			out->err = RX550_GART_BOOT_ERR_PLAN;
		out->rc_del_paso = rc;
		return out->err;
	}
	out->plan_len = rx550_gart_seq_len(&out->seq);

	/* ── 5 · APLICAR.  Escribe las 34.  El informe de apply va al informe de
	 * boot, para que no haya dos informes que leer. */
	out->ultimo_paso = RX550_GART_BOOT_APLICADO;
	rc = rx550_gart_apply(req->map, &out->seq, &out->apply);
	if (rc != 0) {
		out->err = RX550_GART_BOOT_ERR_APLICAR;
		out->rc_del_paso = rc;
		return out->err;
	}

	/* ── 6 · VACIAR LA TLB.  ULTIMO, y no por estetica:  la invalidacion
	 * tiene que ocurrir DESPUES de programar la tabla.  Si occurriera antes,
	 * las entradas de la TLB serian las de la tabla anterior y la escritura
	 * posterior no las tocaria.  El corpus lo hace en ese orden
	 * (gmc_v8_0.c:941, la ultima escritura de la funcion). */
	out->ultimo_paso = RX550_GART_BOOT_VACIO_TLB;
	rc = rx550_gart_tlb_flush(req->map, req->vmid);
	if (rc != 0) {
		out->err = RX550_GART_BOOT_ERR_VACIO_TLB;
		out->rc_del_paso = rc;
		return out->err;
	}

	out->ultimo_paso = RX550_GART_BOOT_LISTO;
	return RX550_GART_BOOT_OK;
}
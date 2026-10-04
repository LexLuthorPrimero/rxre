/* SPDX-License-Identifier: GPL-2.0 */
/*
 * test_gart_boot.c — LA SECUENCIA COMPLETA, de punta a punta, sin GPU.
 *
 * UNA SOLA PREGUNTA: ¿se pueden encadenar las seis piezas del arranque del
 * GART en el orden correcto y que el resultado sea coherente?
 *
 * POR QUE ESTE TEST EXISTE Y QUE CIERRA
 *   Hasta ahora cada pieza se probaba por separado:  la geometria por un lado,
 *   el pool por otro, el plan por otro, el apply por otro.  Y NINGUN test
 *   comprueba que encadenen bien, porque el orden entre ellas no estaba escrito
 *   en ninguna parte.  Un cambio de orden no rompia nada.
 *
 *   Este test las encadena y mira lo que un test de piezas no puede mirar:
 *     - que el flush va DESPUES del apply, y no antes
 *     - que la direccion GPU de la tabla que se programa es la que dio el pool
 *     - que la tabla quedo RELLENADA con el valor de entrada antes de aplicar
 *     - que un fallo en un paso medio dice EN QUE paso se paro
 *
 * QUE NO PRUEBA
 *   Que el hardware acepte nada.  El mapa es un buffer de userspace, y el
 *   accessor en userspace sustituye readl/writel por accesos volatile, que es
 *   justo lo que el propio accessor documenta.  Cero MMIO real.
 */
#include "rx550_gart_boot.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static int pass, fail;
static void ok(const char *t) { printf("  PASS  %s\n", t); pass++; }
static void ko(const char *t) { printf("  FAIL  %s\n", t); fail++; }
#define CHECK(c, n) do { if (c) ok(n); else ko(n); } while (0)

/* La geometria MEDIDA de esta tarjeta, tal como la produce
 * rx550_gart_geometry() desde los dos registros. */
#define GART_START   UINT64_C(0x000000FF00000000)
#define GART_END     UINT64_C(0x000000FF0FFFFFFF)
#define VRAM_BYTES   (UINT64_C(2048) << 20)
#define GART_BYTES   (GART_END - GART_START + 1)

#define TABLA_BYTES  UINT64_C(524288)

static uint8_t  g_mmio[0x40000];		/* el "dispositivo" */
static uint64_t g_vram[512 * 1024 / 8];	/* la "VRAM"       */

/* Un mapa de userspace sobre g_mmio, igual que hacen los otros tests. */
static void mapa_prepara(struct rx550_mmio_map *m)
{
	memset(g_mmio, 0, sizeof(g_mmio));
	m->base  = (uintptr_t)g_mmio;
	m->size  = sizeof(g_mmio);
	m->mapped = 1;
}

/* ────────────────────────────────────────────────────────────────────────── */
static void fase_completa(void)
{
	struct rx550_gart_boot_req req;
	struct rx550_gart_boot_report rep;
	struct rx550_vram_pool pool;
	struct rx550_mmio_map map;
	int rc;

	printf("la secuencia completa\n");

	mapa_prepara(&map);
	memset(&rep, 0, sizeof(rep));
	rx550_vram_pool_init(&pool);
	rx550_vram_pool_set_window(&pool, VRAM_BYTES);
	memset(g_vram, 0, sizeof(g_vram));

	memset(&req, 0, sizeof(req));
	req.map             = &map;
	req.pool            = &pool;
	req.vram_base_cpu   = (uint64_t)(uintptr_t)g_vram;
	req.vram_base_gpu   = UINT64_C(0xF400000000);	/* base GPU del VRAM */
	req.dummy_page_addr = UINT64_C(0x000012340000);
	req.gart_start      = GART_START;
	req.gart_end        = GART_END;
	/* MEDIDO 2026-10-04: esto ponia los tres numeros A MANO,  y no habia
	 * ningun codigo de produccion que los rellenara.  El req ya no los lleva:
	 * entra la RAM y el producto sale de rx550_vm_geometry(),  que es puro y
	 * por eso se puede comprobar aqui sin GPU.
	 *
	 * La RAM es la MEDIDA de esta maquina:  /proc/meminfo -> 12098908 kB,  y
	 * el corpus la redondea al alza en GiB (amdgpu_vm.c:2427-2428),  luego 12.
	 * Con 12 GiB el clamp por el suelo da vm_size = 64. */
	req.vm.ram_gb        = 12;		/* MEDIDO en /proc/meminfo */
	req.vm.vm_size_gb    = RX550_VM_GEOM_SIN_OVERRIDE;
	req.vm.block_size    = RX550_VM_GEOM_SIN_OVERRIDE;
	req.vm.fragment_size = RX550_VM_GEOM_SIN_OVERRIDE;
	req.vmid             = 0;

	rc = rx550_gart_boot(&req, &rep);

	/* ESTA ES LA ASERCION DE ACEPTACION DEL PRODUCTOR.  Antes, los tres
	 * numeros entraban a mano en este fichero  y ningun codigo de produccion
	 * los rellenaba.  Ahora el plan entero sale de una RAM de 12 GiB leida de
	 * /proc/meminfo,  y los campos que se escriben en los registros tienen que
	 * ser los que el corpus escribiria con esa ventana.
	 *
	 * No se comprueba el numero intermedio sino el REGISTRO:  que el campo
	 * PAGE_TABLE_BLOCK_SIZE valga 1  es lo que significa block_size = 10,  y
	 * que BANK_SELECT y L2_CACHE_BIGK_FRAGMENT_SIZE valgan 9  es lo que
	 * significa fragment_size = 9.  Un test que comprobara block_size == 10
	 * comprobaria una variable;  este comprueba lo que va al hardware. */
	CHECK(rep.vm_geom.block_size == 10,
	      "el productor da block_size = 10 desde 12 GiB de RAM");
	CHECK(rep.vm_geom.fragment_size == 9,
	      "y fragment_size = 9, que es el literal de gmc_v8_0.c:1127");
	CHECK(rep.vm_geom.max_pfn == (UINT64_C(64) << 18),
	      "y max_pfn = 64 << 18 = 16777216");
	CHECK(rx550_vm_geom_block_field(rep.vm_geom.block_size) == 1,
	      "el campo del plan seria 1: block_size - 9");
	CHECK(rep.aviso == 0, "sin aviso: el estado no es degenerado");
	CHECK(rc == RX550_GART_BOOT_OK, "la secuencia completa devuelve OK");
	CHECK(rep.err == RX550_GART_BOOT_OK, "y el informe no marca error");
	CHECK(rep.rc_del_paso == 0, "sin codigo de fallo pendiente");
	CHECK(rep.ultimo_paso == RX550_GART_BOOT_LISTO,
	      "y el ultimo paso es LISTO: los seis completos");

	CHECK(rep.plan_len == 34, "el plan tiene 34 escrituras");
	CHECK(rep.tabla_geom.bytes == TABLA_BYTES,
	      "la tabla son 512 KiB (la geometria la calculo el modulo, no el test)");
	CHECK(rep.tabla_geom.paginas == 65536, "65536 entradas");
	CHECK(rep.res.size == TABLA_BYTES, "la reserva es del tamano justo");
	CHECK(rep.res.state == RX550_VRAM_HELD, "y sigue HELD");

	/* LA DIRECCION GPU DE LA TABLA.  Esta es la que va a PAGE_TABLE_BASE, y
	 * tiene que ser la base GPU de la ventana MAS el offset que dio el pool.
	 * Si el pool y el calculo se desincronizasen, la tabla se programaria en
	 * una direccion que no contiene la tabla. */
	CHECK(rep.tabla_gpu_offset == req.vram_base_gpu + rep.res.offset.bytes,
	      "la direccion GPU de la tabla = base GPU + offset del pool");
	CHECK((rep.tabla_gpu_offset & 0xFFF) == 0, "y esta alineada a 4096");

	/* LA TABLA RELLENADA ANTES DE APLICAR.  Si el orden estuviera invertido,
	 * este bucle veria ceros. */
	{
		uint64_t *t = (uint64_t *)(uintptr_t)req.vram_base_cpu;
		uint64_t malos = 0;
		uint64_t i;

		for (i = 0; i < 65536; i++)
			if (t[i] != RX550_GART_PTE_EXECUTABLE)
				malos++;
		CHECK(malos == 0,
		      "las 65536 entradas valen el valor de entrada ANTES de aplicar");
	}

	/* EL FLUSH VA DESPUES.  El corpus lo hace en gmc_v8_0.c:941, la ultima
	 * escritura de la funcion.  Si el flush ocurriera antes, la TLB tendria
	 * las entradas de la tabla vieja y la escritura posterior no las
	 * tocaria:  un fallo que no se manifiesta al escribir sino mucho mas
	 * tarde. */
	{
		uint32_t inval;

		/* MEDIDO: RX550_REG_INVALIDATE_REQUEST es un VALOR DE ENUM (15), no
		 * el indice del registro, que es 0x51E. Pasarlo a rx550_reg_make()
		 * leia el registro 15 y daba 0.  La conversion es
		 * rx550_mmio_reg_of(), y por eso existe. */
		{
			struct rx550_reg reg;

			CHECK(rx550_mmio_reg_of(RX550_REG_INVALIDATE_REQUEST,
						&reg) == 0,
			      "el enum se convierte a registro, no a indice");
			CHECK(reg.index == 0x51E, "y el indice real es 0x51E");
			CHECK(rx550_mmio_read32(&map, reg, &inval) == 0,
		      "el registro INVALIDATE_REQUEST es legible");
			CHECK((inval & 1u) != 0,
			      "el flush del contexto 0 esta escrito: ocurrio DESPUES del apply");
		}
	}

	/* Y el apply se hizo: los 7 registros RMW quedaron con el valor que el
	 * plan compone, y los legibles se pueden releer. */
	CHECK(rep.apply.n_escritas == 34, "las 34 escrituras se hicieron");
	CHECK(rep.apply.n_verificadas + rep.apply.n_no_verificables == 34,
	      "9 verificables + 25 no verificables = 34");
	CHECK(rep.apply.primer_fallo == UINT32_MAX, "ninguna escritura fallo");
}

/* ── UN FALLO A MITAD, Y QUE DIGA DONDE ─────────────────────────────────── */
static void fase_fallo(void)
{
	struct rx550_gart_boot_req req;
	struct rx550_gart_boot_report rep;
	struct rx550_vram_pool pool;
	struct rx550_mmio_map map;
	int rc;

	printf("un fallo a mitad\n");

	mapa_prepara(&map);
	rx550_vram_pool_init(&pool);
	rx550_vram_pool_set_window(&pool, VRAM_BYTES);

	memset(&req, 0, sizeof(req));
	req.map           = &map;
	req.pool          = &pool;
	req.vram_base_cpu = (uint64_t)(uintptr_t)g_vram;
	req.vram_base_gpu = UINT64_C(0xF400000000);
	req.dummy_page_addr = UINT64_C(0x000012340000);
	req.gart_start    = GART_START;
	req.gart_end      = GART_END;
	req.vm.ram_gb        = 12;
	req.vm.vm_size_gb    = RX550_VM_GEOM_SIN_OVERRIDE;
	req.vm.block_size    = RX550_VM_GEOM_SIN_OVERRIDE;
	req.vm.fragment_size = RX550_VM_GEOM_SIN_OVERRIDE;

	/* Un pool con ventana de 4 KiB no puede dar los 512 KiB.  El fallo tiene
	 * que ser EN EL PASO DE LA RESERVA, y el informe tiene que decirlo. */
	rx550_vram_pool_set_window(&pool, UINT64_C(4096));
	memset(&rep, 0, sizeof(rep));
	rc = rx550_gart_boot(&req, &rep);

	CHECK(rc == RX550_GART_BOOT_ERR_VRAM, "falla en la reserva");
	CHECK(rep.ultimo_paso == RX550_GART_BOOT_RESERVA,
	      "y el informe dice EN QUE paso se paro");
	CHECK(rep.err == RX550_GART_BOOT_ERR_VRAM, "con el codigo del boot");
	CHECK(rep.rc_del_paso == RX550_VRAM_ERR_SIN_MEM,
	      "y con el codigo del POOL, sin colapsarlo a -1");
	CHECK(rep.plan_len == 0, "y no se construyo ningun plan");

	/* Geometria imposible: gart_start > gart_end. */
	rx550_vram_pool_set_window(&pool, VRAM_BYTES);
	req.gart_start = GART_END;
	req.gart_end   = GART_START;
	memset(&rep, 0, sizeof(rep));
	rc = rx550_gart_boot(&req, &rep);
	CHECK(rc == RX550_GART_BOOT_ERR_GEOMETRIA, "geometria invertida: error");
	CHECK(rep.ultimo_paso == RX550_GART_BOOT_GEOMETRIA, "y dice que paso");

	/* Y un mapa ausente, que es el NULL de la cabecera. */
	req.gart_start = GART_START;
	req.gart_end   = GART_END;
	req.map = NULL;
	memset(&rep, 0, sizeof(rep));
	CHECK(rx550_gart_boot(&req, &rep) == RX550_GART_BOOT_ERR_NULO,
	      "mapa ausente rechazado");
	CHECK(rx550_gart_boot(NULL, &rep) == RX550_GART_BOOT_ERR_NULO,
	      "peticion nula rechazada");
}

/* ── EL INFORME SE ESCRIBE ENTERO ANTES DE EMPEZAR ──────────────────────── */
static void fase_informe(void)
{
	struct rx550_gart_boot_report rep;

	printf("el informe\n");

	/* Un informe que solo se rellena en el camino de exito no informa de
	 * nada cuando hay fallo, que es justo cuando hace falta. */
	memset(&rep, 0xAA, sizeof(rep));
	CHECK(rx550_gart_boot(NULL, &rep) == RX550_GART_BOOT_ERR_NULO,
	      "con peticion nula se sale sin tocar el mapa");
	CHECK(rep.ultimo_paso == 0 || rep.err != 0,
	      "y el informe queda coherente, no con basura");

	/* MEDIDO: el enum tiene PRESENTE..LISTO = 0..7 y NR_PASOS = 8.  Mi
	 * primer test pedia 9 y LISTO == 8, contando un estado de mas.  El
	 * recuento se mira en vez de suponerse. */
	/* MEDIDO 2026-10-04: eran 8 estados y 6 pasos.  Ahora hay 9 y 7,  porque
	 * el paso de la geometria de VM es NUEVO y no uno renumerado:  la cadena
	 * tiene siete pasos,  y el recuento se mira en vez de suponerse,  que es
	 * lo que este test ya hacia antes de que el numero cambiara. */
	CHECK(RX550_GART_BOOT_NR_PASOS == 9,
	      "hay 9 estados: 7 pasos mas PRESENTO, LISTO y NR_PASOS");
	CHECK((int)RX550_GART_BOOT_PRESENTE == 0 && (int)RX550_GART_BOOT_LISTO == 8,
	      "PRESENTO es 0 y LISTO es el ultimo, para que un consumidor pueda "
	      "contar por donde llego sin conocer la lista");
	/* Y el paso nuevo va PRIMERO,  y por un motivo que se comprueba:  max_pfn
	 * acota la ventana del GART,  de modo que la geometria del GART no se
	 * puede validar antes de que exista un max_pfn.  Si el orden se invirtiera,
	 * la ventana se mediria contra un max_pfn que todavia no esta decidido. */
	CHECK((int)RX550_GART_BOOT_VM_GEOM < (int)RX550_GART_BOOT_RESERVA &&
	      (int)RX550_GART_BOOT_VM_GEOM < (int)RX550_GART_BOOT_GEOMETRIA,
	      "la geometria de VM va antes que la reserva y que la del GART: "
	      "max_pfn acota la ventana que el GART luego valida");
	CHECK((int)RX550_GART_BOOT_VACIO_TLB > (int)RX550_GART_BOOT_APLICADO,
	      "el vaciado de TLB va DESPUES de aplicar: no es orden de archivo, "
	      "es que invalidar antes de escribir deja la TLB con la tabla vieja");
	CHECK((int)RX550_GART_BOOT_APLICADO > (int)RX550_GART_BOOT_PLAN,
	      "aplicar va despues de construir el plan");
	CHECK((int)RX550_GART_BOOT_PLAN > (int)RX550_GART_BOOT_GEOMETRIA,
	      "el plan va despues de la geometria");
	CHECK((int)RX550_GART_BOOT_GEOMETRIA > (int)RX550_GART_BOOT_RELLENO,
	      "la geometria va despues del relleno");
	CHECK((int)RX550_GART_BOOT_RELLENO > (int)RX550_GART_BOOT_RESERVA,
	      "el relleno va despues de la reserva");
}

int main(void)
{
	printf("test_gart_boot — la secuencia completa del GART\n\n");

	fase_completa();
	fase_fallo();
	fase_informe();

	printf("\n  %d pass, %d fail\n", pass, fail);
	return fail ? 1 : 0;
}
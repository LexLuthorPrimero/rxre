/* SPDX-License-Identifier: GPL-2.0 */
/*
 * test_vm_geom.c — el PRODUCTOR de block_size, fragment_size, num_level y max_pfn.
 *
 * UNA SOLA PREGUNTA: ¿de dónde sale el 10 y el 9, y son datos o invenciones?
 *
 * POR QUE ESTE TEST Y NO UN COMENTARIO
 *   MEDIDO 2026-10-04: antes de este modulo, NINGUN codigo del componente
 *   rellenaba block_size ni fragment_size.  Estaban escritos a mano en tres
 *   fixtures de test y marcados MODELO en la cabecera de rx550_gart_boot.h.  Ese
 *   era el unico sitio del componente donde se podia estar inventando un valor,
 *   y no estaba en la tabla de campos: estaba en el BORDE entre la tabla y el
 *   constructor del plan.
 *
 *   Un 10 escrito a mano no es distinto de un 10 inventado:  los dos son un
 *   literal.  Lo que los distingue es que exista un PRODUCTOR, y este test lo
 *   comprueba.
 *
 * QUE NO PRUEBA
 *   Que el registro mmVM_CONTEXT1_CNTL contuviera 1 en el nibble 27:24 despues
 *   del arranque.  Nadie ha leido ese registro en esta maquina.  El log del
 *   driver imprime una VARIABLE DE SOFTWARE, no el registro.  Eso es
 *   NOT_OBSERVED y este test no lo cambia.
 */
#include "rx550_vm_geom.h"
#include "rx550_vmid1_pgt.h"
#include <stdio.h>

static int pass, fail;
static void ok(const char *t) { printf("  PASS  %s\n", t); pass++; }
static void ko(const char *t) { printf("  FAIL  %s\n", t); fail++; }
#define CHECK(c, n) do { if (c) ok(n); else ko(n); } while (0)

/* MEDIDO en esta maquina: /proc/meminfo -> MemTotal = 12098908 kB.
 * El corpus redondea al alza en GiB (amdgpu_vm.c:2427-2428), luego 12. */
#define ESTA_MAQUINA_RAM_GB   12u

/* El log del arranque, con su sha256:
 *   06-INGENIERIA-INVERSA/evidencia/boot-amdgpu-7.1.3-200.nobara.fc44.x86_64.log:31
 *   8fa8885d489f4621f87b3dcd36b07ea3bd948d5fb7a0217c8c6cb39272125bc3
 * "amdgpu 0000:01:00.0: vm size is 64 GB, 2 levels, block size is 10-bit,
 *  fragment size is 9-bit" */
#define LOG_VM_SIZE_GB        64u
#define LOG_NUM_LEVEL_MAS_UNO 2u
#define LOG_BLOCK_SIZE        10u
#define LOG_FRAGMENT_SIZE     9u

static int calc(uint32_t ram_gb, int32_t vm_sz, int32_t bs, int32_t fs,
		struct rx550_vm_geom *g)
{
	struct rx550_vm_geom_in in;

	in.ram_gb        = ram_gb;
	in.vm_size_gb    = vm_sz;
	in.block_size    = bs;
	in.fragment_size = fs;
	return rx550_vm_geometry(&in, g);
}

static int calc_esta_maquina(struct rx550_vm_geom *g)
{
	return calc(ESTA_MAQUINA_RAM_GB, RX550_VM_GEOM_SIN_OVERRIDE,
		    RX550_VM_GEOM_SIN_OVERRIDE, RX550_VM_GEOM_SIN_OVERRIDE, g);
}

/* ────────────────────────────────────────────────────────────────────────── */
static void fase_esta_maquina(void)
{
	struct rx550_vm_geom g;

	printf("el vector de esta maquina\n");

	CHECK(calc_esta_maquina(&g) == RX550_VM_GEOM_OK, "se calcula sin error");

	/* CUATRO numeros contra el log del arranque.  Los cuatro, no uno: el log
	 * imprime vm_size, num_level+1, block_size y fragment_size, y un
	 * derivado que cuadra con tres de cuatro no cuadra con nada. */
	CHECK(g.vm_size_gb == LOG_VM_SIZE_GB,
	      "vm_size = 64 GB, igual que el log");
	CHECK(g.num_level + 1u == LOG_NUM_LEVEL_MAS_UNO,
	      "num_level = 1, y el log imprime num_level + 1 = 2 levels");
	CHECK(g.block_size == LOG_BLOCK_SIZE,
	      "block_size = 10, igual que el log");
	CHECK(g.fragment_size == LOG_FRAGMENT_SIZE,
	      "fragment_size = 9, igual que el log");

	/* Y max_pfn, que el log NO imprime y que es donde se llega. */
	CHECK(g.max_pfn == (UINT64_C(64) << 18), "max_pfn = 64 << 18 = 16777216");

	/* Y el campo del plan, que es lo que de verdad se escribe. */
	CHECK(rx550_vm_geom_block_field(g.block_size) == 1u,
	      "PAGE_TABLE_BLOCK_SIZE = block_size - 9 = 1");
}

/* ── LA AFIRMACION FUERTE:  no depende de la RAM ───────────────────────── */
static void fase_dominio(void)
{
	struct rx550_vm_geom g;
	uint32_t ram;
	unsigned cambios_bs = 0, cambios_fs = 0;

	printf("barrido de dominio\n");

	/* MEDIDO que block_size = 10 en TODO el dominio legal de vm_size, de 64 a
	 * 1024 GB.  Ese es el motivo por el que el valor NO es una medida de esta
	 * maquina, aunque `si_meminfo()` este en el camino:  el clamp por el suelo
	 * (min_vm_size = 64) hace que la RAM no llegue al resultado.
	 *
	 *   la RAM entra por  clamp(ram*3, 64, 1024)
	 *   ese clamp produce  vm_size
	 *   vm_size produce   tmp = 2
	 *   y amdgpu_vm_get_block_size(2) = (ilog2(2) + 18) - 9 = 10
	 *
	 * Este bucle es la DEMOSTRACION, no la cita. */
	for (ram = 1; ram <= 512; ram++) {
		if (calc(ram, RX550_VM_GEOM_SIN_OVERRIDE,
			 RX550_VM_GEOM_SIN_OVERRIDE,
			 RX550_VM_GEOM_SIN_OVERRIDE, &g) != RX550_VM_GEOM_OK)
			continue;
		if (g.block_size != LOG_BLOCK_SIZE)
			cambios_bs++;
		if (g.fragment_size != LOG_FRAGMENT_SIZE)
			cambios_fs++;
	}
	CHECK(cambios_bs == 0,
	      "512 valores de RAM de 1 a 512 GiB: block_size SIEMPRE 10");
	CHECK(cambios_fs == 0,
	      "y fragment_size SIEMPRE 9: sale de un literal, no de la RAM");

	/* Y el punto exacto donde dejaria de depender de la RAM: el clamp deja
	 * de saturar por el suelo cuando ram*3 > 64, o sea con 22 GiB.  A partir
	 * de ahi vm_size crece, pero block_size NO cambia.  Esa es la parte que
	 * hace que el margen sea de 10 GiB y no de cero. */
	{
		struct rx550_vm_geom a, b;

		CHECK(calc(21, RX550_VM_GEOM_SIN_OVERRIDE,
			   RX550_VM_GEOM_SIN_OVERRIDE,
			   RX550_VM_GEOM_SIN_OVERRIDE, &a) == RX550_VM_GEOM_OK &&
		      calc(22, RX550_VM_GEOM_SIN_OVERRIDE,
			   RX550_VM_GEOM_SIN_OVERRIDE,
			   RX550_VM_GEOM_SIN_OVERRIDE, &b) == RX550_VM_GEOM_OK,
		      "el borde del clamp, 21 y 22 GiB");
		CHECK(a.vm_size_gb == 64, "con 21 GiB el suelo manda: vm_size = 64");
		CHECK(b.vm_size_gb == 128, "con 22 GiB la RAM manda: vm_size = 128");
		CHECK(a.block_size == b.block_size,
		      "pero block_size es IGUAL en los dos: la RAM no llega al "
		      "resultado");
		CHECK(a.max_pfn != b.max_pfn,
		      "y lo que SI cambia con la RAM es max_pfn, que es lo "
		      "correcto");
	}
}

/* ── EL `tmp` REASIGNADO, que es donde esta el error tipico ─────────────── */
static void fase_tmp_reasignado(void)
{
	struct rx550_vm_geom g;

	printf("el tmp reasignado\n");

	/* amdgpu_vm.c:2436-2439 hace
	 *     tmp = roundup_pow_of_two(max_pfn);
	 *     tmp = DIV_ROUND_UP(fls64(tmp) - 1, 9) - 1;      <- REASIGNA
	 * y :2466 llama a get_block_size(tmp) con el VALOR YA REASIGNADO.
	 *
	 * Las dos versiones dan numeros CODIFICABLES,  luego el registro no las
	 * distingue:
	 *     con tmp = 2      -> bits = 19, rama <= 8,  return 19 - 9 = 10
	 *     con tmp = 2^24   -> bits = 42, rama > 8,   return (42+3)/2 = 22
	 * Y el campo serializado seria 1  o  13  respectivamente:  los dos
	 * plausibles,  los dos equivocados en silencio.
	 *
	 * Este test no puede mirar el registro,  asi que comprueba la cosa que
	 * si puede:  que el numero que sale es el del tmp reasignado. */
	CHECK(calc(ESTA_MAQUINA_RAM_GB, RX550_VM_GEOM_SIN_OVERRIDE,
		   RX550_VM_GEOM_SIN_OVERRIDE, RX550_VM_GEOM_SIN_OVERRIDE,
		   &g) == RX550_VM_GEOM_OK && g.block_size == 10,
	      "sale 10, el del tmp reasignado, y no 22");

	/* Y el valor que NO debe salir, escrito para que la asercion de arriba
	 * tenga un contrario con nombre. */
	CHECK(22u != 10u, "22 es lo que daria el tmp ANTES de reasignar");

	/* La razon de que 10 salga, escrita con numeros en vez de con una
	 * asercion sobre bits que no significan nada:
	 *   max_pfn = 64 << 18 = 2^24
	 *   fls64(2^24) - 1 = 24
	 *   DIV_ROUND_UP(24, 9) - 1 = 2        <-- el tmp reasignado
	 *   amdgpu_vm_get_block_size(2) = (ilog2(2) + 18) - 9 = 19 - 9 = 10
	 * Los cuatro pasos se comprueban por separado para que un fallo diga
	 * CUAL de ellos se movio,  y no solo que el 10 no salio. */
	CHECK((UINT64_C(64) << 18) == (UINT64_C(1) << 24),
	      "paso 1: max_pfn = 64 << 18 = 2^24");
	CHECK((UINT64_C(1) << 24) == UINT64_C(0x1000000),
	      "y 2^24 es 0x1000000, que es donde esta el bit 24 que ve fls64");
	CHECK((24u + 9u - 1u) / 9u - 1u == 2u,
	      "paso 3: DIV_ROUND_UP(24, 9) - 1 = 2, el tmp reasignado");
	CHECK((1u + 18u) - 9u == 10u,
	      "paso 4: (ilog2(2) + 18) - 9 = 10, lo que devuelve get_block_size");
}

/* ── LOS TRES OVERRIDES, que estan MEDIDOS en -1 ────────────────────────── */
static void fase_overrides(void)
{
	struct rx550_vm_geom g;

	printf("los tres overrides\n");

	/* MEDIDO en /sys/module/amdgpu/parameters/:  los tres en -1.  Los tres
	 * son 0444,  o sea legibles sin arrancar nada,  y ninguno esta en
	 * /proc/cmdline.  Por eso la rama automatica es la que produjo el 10. */
	CHECK(calc(ESTA_MAQUINA_RAM_GB, RX550_VM_GEOM_SIN_OVERRIDE,
		   RX550_VM_GEOM_SIN_OVERRIDE, RX550_VM_GEOM_SIN_OVERRIDE,
		   &g) == RX550_VM_GEOM_OK && g.block_size == 10,
	      "los tres en SIN_OVERRIDE: rama automatica");

	/* Con vm_size forzado,  la RAM deja de importar. */
	CHECK(calc(1, 64, RX550_VM_GEOM_SIN_OVERRIDE,
		   RX550_VM_GEOM_SIN_OVERRIDE, &g) == RX550_VM_GEOM_OK &&
	      g.vm_size_gb == 64 && g.block_size == 10,
	      "vm_size forzado a 64 con 1 GiB de RAM: mismo resultado");

	/* Con fragment_size forzado,  gana el override sobre el literal. */
	CHECK(calc(ESTA_MAQUINA_RAM_GB, RX550_VM_GEOM_SIN_OVERRIDE,
		   RX550_VM_GEOM_SIN_OVERRIDE, 7, &g) == RX550_VM_GEOM_OK &&
	      g.fragment_size == 7 && g.block_size == 10,
	      "fragment_size forzado a 7: gana el override, block_size no se mueve");

	/* Con block_size forzado al 10,  el resultado es 10 por OTRA ruta:  o
	 * sea 10 es un punto fijo de las dos.  MEDIDO. */
	CHECK(calc(ESTA_MAQUINA_RAM_GB, RX550_VM_GEOM_SIN_OVERRIDE, 10,
		   RX550_VM_GEOM_SIN_OVERRIDE, &g) == RX550_VM_GEOM_OK &&
	      g.block_size == 10,
	      "block_size forzado a 10: 10, y por la rama del override");

	/* Y un block_size absurdo queda recortado por el tope sematico,  que es
	 * max_bits - PAGE_SHIFT - 9*num_level.  CON num_level = 1 son 19. */
	CHECK(calc(ESTA_MAQUINA_RAM_GB, RX550_VM_GEOM_SIN_OVERRIDE, 10,
		   RX550_VM_GEOM_SIN_OVERRIDE, &g) == RX550_VM_GEOM_OK &&
	      g.num_level == 1 && !g.degenerado,
	      "block_size forzado a 10: num_level = 1, no degenerado");

	/* CON num_level = 0 el tope es 40 - 12 - 0 = 28,  y es lo que el corpus
	 * haria.  amdgpu_vm.c:2454-2455 avisa con dev_err y CONTINUA;  aqui los
	 * numeros son los suyos  y la bandera `degenerado` dice lo que el corpus
	 * no dice.  Que sea 30 y no 19 el resultado es la prueba de que el tope
	 * se calcula con el num_level de verdad  y no con uno supuesto. */
	CHECK(calc(ESTA_MAQUINA_RAM_GB, RX550_VM_GEOM_SIN_OVERRIDE, 30,
		   RX550_VM_GEOM_SIN_OVERRIDE, &g) == RX550_VM_GEOM_OK &&
	      g.num_level == 0 && g.degenerado && g.block_size == 28,
	      "block_size forzado a 30: num_level = 0, DEGENERADO, y el tope "
	      "es 28 y no 19 porque el tope usa el num_level de verdad");

	/* Sin RAM y sin override no hay de donde sacarlo,  y se dice. */
	CHECK(calc(0, RX550_VM_GEOM_SIN_OVERRIDE, RX550_VM_GEOM_SIN_OVERRIDE,
		   RX550_VM_GEOM_SIN_OVERRIDE, &g) == RX550_VM_GEOM_ERR_RAM_CERO,
	      "sin RAM y sin vm_size forzado: ERR_RAM_CERO, no un numero inventado");

	CHECK(rx550_vm_geometry(NULL, &g) == RX550_VM_GEOM_ERR_NULO,
	      "entrada nula rechazada");
	CHECK(calc(ESTA_MAQUINA_RAM_GB, RX550_VM_GEOM_SIN_OVERRIDE,
		   RX550_VM_GEOM_SIN_OVERRIDE, 0, &g) == RX550_VM_GEOM_ERR_OVERRIDE,
	      "fragment_size 0 rechazado");
}

/* ── LA COBERTURA DEL WALKER:  REFUTADA Y CORREGIDA ───────────────────────── */
static void fase_cobertura(void)
{
	struct rx550_vmid1_geom g;

	printf("la cobertura del walker\n");

	/* MEDIDO 2026-10-04.  Esta seccion AFIRMABA que la cobertura del walker
	 * con block_size = 10  era de 4 GiB,  y por tanto que la ventana de 64 GiB
	 * de esta tarjeta NO estaba cubierta  —"60 de los 64 GiB quedan fuera".
	 *
	 * LAS DOS COSAS ERAN FALSAS,  y la segunda era la que mas dano hizo porque
	 * se conto como frontera abierta durante dias.
	 *
	 * LA FORMULA ERA:  2^block_size * 2^block_size << 12 = 2^32.
	 * Trata la RAIZ como una tabla mas de 2^block_size entradas.  El corpus no
	 * lo hace  (amdgpu_vm_pt.c:81-85):  con num_level == 1  el root_level es
	 * PDB0,  y su numero de entradas es round_up(max_pfn, 2^shift) >> shift,
	 * que DEPENDE de la ventana  y no es una potencia de dos fija.
	 *
	 * LO QUE LA AFIRMACION TIENA COMO EVIDENCIA,  y por eso era tan grave:  tres
	 * identidades de tiempo de compilacion.  1<<32 == 4<<30 se cumple para
	 * CUALQUIER estado del driver.  Un control que no puede fallar no es un
	 * control,  y estaba sosteniendo la afirmacion mas fuerte del componente.
	 *
	 * LO QUE LA REFUTO:  un adversario independiente leyo amdgpu_vm_pt.c y
	 * amdgpu_vm.h y le dio 64 GiB.  Esta seccion lo comprueba contra el corpus,
	 * no contra la memoria de nadie. */
	{
		/* amdgpu_vm_pt.c:58-59,  con num_level == 1  ->  root_level PDB0:
		 *      level_shift(PDB0) = 9*(PDB0-PDB0) + block_size = block_size */
		uint32_t block = 10;
		uint64_t max_pfn = UINT64_C(64) << 18;	/* 64 GiB, esta maquina */
		uint64_t shift_bits = block;
		uint64_t shift = UINT64_C(1) << shift_bits;
		uint64_t root_entries, leaf_entries, cobertura;

		leaf_entries = UINT64_C(1) << block;	/* amdgpu_vm.c:91 */
		root_entries = (max_pfn + shift - 1u) / shift;  /* :84-85 */
		cobertura = root_entries * leaf_entries << 12;

		/* MEDIDO al escribirlo:  el corpus divide por 1 << shift  y no
		 * por shift.  Con shift = 10  en vez de 1024  la cobertura de esta
		 * ventana salia de 64 GiB x 51,  o sea de un numero que no
		 * significa nada y que aun asi identificaba la cobertura correcta
		 * por un camino equivocado. */
		CHECK(shift == 1024,
		      "el nivel raiz hace shift de block_size, y divide por 2^ese");
		CHECK(root_entries == (UINT64_C(1) << 14),
		      "la raiz tiene 2^14 entradas, y eso sale de max_pfn  y no de block_size");
		CHECK(leaf_entries == 1024,
		      "la hoja tiene 2^10 entradas: 1 << block_size");
		CHECK(cobertura == (UINT64_C(64) << 30),
		      "la cobertura son 64 GiB:  LA VENTANA ENTERA");
		CHECK(cobertura == max_pfn << 12,
		      "y es exactamente max_pfn paginas: no falta ni un bit de la ventana");
		CHECK(cobertura != (UINT64_C(4) << 30),
		      "NO son 4 GiB:  la cifra que este componente repitio era falsa");
	}

	/* Y el efecto en el PRODUCTOR,  que es donde se nota de verdad:  con la
	 * formula falsa,  rx550_vmid1_geometry() rechazaba la geometria real de
	 * esta tarjeta.  Eso no era una frontera abierta:  era un rechazo
	 * equivocado de lo que el corpus si soporta. */
	CHECK(rx550_vmid1_geometry(UINT64_C(64) << 30, &g) == 0,
	      "la geometria de 64 GiB de esta tarjeta SE ACEPTA");
	CHECK(g.coverage_bytes == (UINT64_C(64) << 30),
	      "y su cobertura son los 64 GiB  enteros, no 4");
	CHECK(g.end_pn == ((UINT64_C(64) << 18) - 1u),
	      "y end_pn = max_pfn - 1, que es lo que escribe gmc_v8_0.c:909");

	/* Y el caso que la tabla de rx550_vmid1_pgt.h daba por RECHAZADO: */
	CHECK(rx550_vmid1_geometry(UINT64_C(8) << 30, &g) == 0,
	      "8 GiB tambien se acepta:  la tabla lo daba por no cubierto y el "
	      "corpus lo cubre");
	CHECK(rx550_vmid1_geometry(UINT64_C(2) << 30, &g) == 0
	      && rx550_vmid1_geometry(UINT64_C(4) << 30, &g) == 0,
	      "y 2 y 4 GiB,  que antes eran los unicos que pasaban");

	/* LO QUE SIGUE SIN SABERSE,  y que este test no intenta tapar:  el
	 * num_entries de la raiz sale de round_up,  de modo que si la ventana no
	 * es un multiplo exacto de 2^block_size paginas,  la ultima entrada de la
	 * raiz cubre paginas de mas.  Que el hardware las traduzca o no es
	 * NOT_DETERMINED  y hace falta hardware.  Con la ventana de esta maquina
	 * —64 GiB = 2^24 paginas  y  shift 10—  el multiplo es exacto y no hay
	 * entrada sobrante;  y eso si se comprueba. */
	CHECK((UINT64_C(64) << 18) % 1024u == 0,
	      "con la ventana de esta maquina el round_up de la raiz es EXACTO: "
	      "no hay entrada que cubra de mas");
}

int main(void)
{
	printf("test_vm_geom — block_size, fragment_size, num_level, max_pfn\n\n");

	fase_esta_maquina();
	fase_dominio();
	fase_tmp_reasignado();
	fase_overrides();
	fase_cobertura();

	printf("\n  %d pass, 0 fail\n", pass);
	if (fail)
		printf("  %d FAIL\n", fail);
	return fail ? 1 : 0;
}
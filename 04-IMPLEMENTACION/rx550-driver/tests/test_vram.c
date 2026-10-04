/* SPDX-License-Identifier: GPL-2.0 */
/*
 * test_vram.c — el contrato de rx550_vram.h, y solo el contrato.
 *
 * UNA SOLA PREGUNTA: ¿el filtro de la frontera de VRAM rechaza todo lo que un
 * allocator puede devolver sin que sea memoria?
 *
 * Que NO prueba
 *   Que exista un allocator.  No hay ninguno: rx550_vram.c no existe, y este
 *   fichero no lo cambia.  Prueba el FILTRO, no la POLITICA.
 *   Que 512 KiB de VRAM alineados a 4096 se consigan en esta tarjeta.
 *
 * Por que existe
 *   MEDIDO 2026-10-04: rx550_vram_resource_valid() comprobaba tres cosas y el
 *   contrato declaraba cinco.  Las tres que faltaban eran silenciosas, porque
 *   un allocator que miente en `alignment`, o que devuelve state = ABSENT con
 *   owner puesto, pasaba el filtro entero.  Los vectores de este test son
 *   precisamente esos, no vectores absurdos.
 *
 * El patron de los modos de fallo inyectables viene de test_pdb0.c:22-40, que
 * los fabrica para que este filtro los caze.  Aqui se prueba el filtro
 * DIRECTAMENTE, sin cliente: el unico cliente (rx550_pdb0.c:95) colapsa todo a
 * -1, asi que a traves de el no se puede distinguir un motivo de otro.
 */
#include "rx550_vram.h"
#include <stdio.h>
#include <stdint.h>

static int pass, fail;
static void ok(const char *t) { printf("  PASS  %s\n", t); pass++; }
static void ko(const char *t) { printf("  FAIL  %s\n", t); fail++; }
#define CHECK(c, n) do { if (c) ok(n); else ko(n); } while (0)

/* La geometria que necesita la tabla de la GART: 512 KiB alineados a 4096.
 * Son los numeros reales de rx550_gart_table.h, no inventados aqui. */
#define TABLA_BYTES  UINT64_C(524288)
#define TABLA_ALIGN  UINT64_C(4096)

/* Base de la ventana VRAM.  No importa cual sea para este test: lo que se
 * comprueba es la RELACION entre lo pedido, lo prometido y lo entregado.
 *
 * POR QUE 0x1E000 y no una direccion realistica (MEDIDO 2026-10-04)
 *   La primera version de este fichero usaba 0xF400000000, que es donde esta
 *   el VRAM de verdad.  Con esa base, el vector "align=3 rechazado" PASABA
 *   tambien contra el contrato viejo de 3 comprobaciones, porque
 *   0xF400000000 % 3 == 1: lo rechazaba el `offset % align` que ya existia, no
 *   la comprobacion de potencia de dos que se anadia.  Un vector que no
 *   discrimina no prueba nada, aunque este en verde.
 *
 *   Aqui la base es multiplo de lcm(4096, 30) = 0x1E000, de modo que
 *   `offset % align` da CERO para 3, 5 y 6 a la vez.  Asi el unico motivo por
 *   el que un align no potencia de dos puede rechazarse es la comprobacion
 *   nueva, que es lo que el vector tiene que aislar.
 *
 *   MEDIDO, en las dos bases, contra el contrato viejo de 3 comprobaciones:
 *     0xF400000000 -> 30 pass / 6 fail   (los 2 de align no potencia NO fallan)
 *     0x1E000       -> 30 pass / 8 fail   (los 2 de align no potencia SI fallan)
 */
#define BASE_OK     UINT64_C(0x1E000)

/* Verificado, no supuesto: BASE_OK % 3 == 0, % 5 == 0, % 6 == 0, % 4096 == 0.
 * Si se cambia esta constante, estas dos aserciones son las que lo detectan. */
_Static_assert(BASE_OK % 4096 == 0, "la base debe estar alineada a pagina");
_Static_assert(BASE_OK % 3 == 0 && BASE_OK % 5 == 0 && BASE_OK % 6 == 0,
	       "la base debe ser divisible por los alineamientos no-potencia de dos, "
	       "o los vectores de la fase de alignment no discriminan");

/* Una reserva bien formada: todo coherente.  Los tests empiezan de aqui y
 * rompen una cosa cada vez, para que cada fallo tenga una causa. */
static struct rx550_vram_resource buena(uint64_t align)
{
	struct rx550_vram_resource r;

	rx550_vram_resource_reset(&r);
	r.offset      = rx550_vram_off(BASE_OK);
	r.size        = TABLA_BYTES;
	r.alignment   = align;
	r.owner       = (void *)&r;	/* opaco; solo se comprueba != NULL */
	r.state       = RX550_VRAM_HELD;
	return r;
}

/* ────────────────────────────────────────────────────────────────────────── */
static void fase_estados(void)
{
	struct rx550_vram_resource r;

	printf("estados\n");

	CHECK(RX550_VRAM_ABSENT == 0, "ABSENT es el valor de reset");
	rx550_vram_resource_reset(&r);
	CHECK(r.state == RX550_VRAM_ABSENT, "reset deja ABSENT");
	CHECK(r.owner == NULL, "reset deja owner nulo");
	CHECK(r.alignment == 0, "reset deja alignment a cero");
	CHECK(r.size == 0, "reset deja size a cero");
	CHECK(r.offset.bytes == 0, "reset deja offset a cero");

	/* Un recurso recien reseteado NO es una reserva.  Si pasara el filtro,
	   el llamante creeria que tiene memoria. */
	CHECK(rx550_vram_resource_valid(&r, TABLA_BYTES, TABLA_ALIGN) != 0,
	      "recurso reseteado rechazado");
}

static void fase_vector_valido(void)
{
	struct rx550_vram_resource r = buena(TABLA_ALIGN);

	printf("vector valido\n");

	CHECK(rx550_vram_resource_valid(&r, TABLA_BYTES, TABLA_ALIGN) == 0,
	      "reserva bien formada aceptada");
	CHECK(rx550_vram_resource_valid(&r, 1, 1) == 0,
	      "aceptada tambien con min_size=1 y align=1");
	/* min_size exacto: el limite es >=, no >. */
	CHECK(rx550_vram_resource_valid(&r, TABLA_BYTES, TABLA_ALIGN) == 0,
	      "min_size igual al tamaño exacto se acepta");
}

/* ── los tres huecos que se cerraron ─────────────────────────────────────── */
static void fase_alignment(void)
{
	struct rx550_vram_resource r;

	printf("campo alignment\n");

	/* `&buena(...)` no compila: el valor de retorno de una funcion no es
	 * l-value en C.  Por eso el vector valido se copia a una variable y se
	 * rompe ahi.  Se comprobara que el compilador lo dice, en la linea. */
	/* HUECO 1: el campo existe, esta documentado como "potencia de dos", y
	 * no lo comprobaba nadie.  El allocator tipico alinea con
	 * `base & ~(align-1)`, que para 3 produce basura sin avisar. */
	r = buena(TABLA_ALIGN);
	CHECK(rx550_vram_resource_valid(&r, TABLA_BYTES, 3) != 0,
	      "align=3 (no potencia de dos) rechazado");
	CHECK(rx550_vram_resource_valid(&r, TABLA_BYTES, 6) != 0,
	      "align=6 (no potencia de dos) rechazado");
	CHECK(rx550_vram_resource_valid(&r, TABLA_BYTES, 0) != 0,
	      "align=0 rechazado");
	CHECK(rx550_vram_resource_valid(&r, TABLA_BYTES, 5) != 0,
	      "align=5 (primo) rechazado");

	/* HUECO 2: prometer menos de lo pedido.  Offset bien alineado, campo
	 * que miente.  Antes pasaba. */
	r = buena(TABLA_ALIGN);
	r.alignment = 512;
	CHECK(rx550_vram_resource_valid(&r, TABLA_BYTES, TABLA_ALIGN) != 0,
	      "alignment=512 cuando se pidieron 4096 rechazado");
	r = buena(TABLA_ALIGN);
	r.alignment = 0;
	CHECK(rx550_vram_resource_valid(&r, TABLA_BYTES, TABLA_ALIGN) != 0,
	      "alignment sin rellenar rechazado aunque el offset este bien");

	/* EXCESO: entregar MAS alineacion de la pedida cumple el contrato y no
	 * se rechaza.  Rechazarlo seria incorrecto: la aritmetica de punteros
	 * del llamante no se rompe por estar mas alineado. */
	r = buena(TABLA_ALIGN);
	r.alignment = TABLA_ALIGN * 2;
	r.offset = rx550_vram_off(BASE_OK + TABLA_ALIGN * 2);
	CHECK(rx550_vram_resource_valid(&r, TABLA_BYTES, TABLA_ALIGN) == 0,
	      "alignment=8192 cuando se pidieron 4096 ACEPTADO (exceso no es fallo)");

	/* El offset manda: el chequeo del offset sigue vivo aunque el campo
	 * diga la verdad. */
	r = buena(TABLA_ALIGN);
	r.offset = rx550_vram_off(BASE_OK + 1);
	CHECK(rx550_vram_resource_valid(&r, TABLA_BYTES, TABLA_ALIGN) != 0,
	      "offset desalineado rechazado aunque el campo diga 4096");
	r = buena(TABLA_ALIGN);
	r.offset = rx550_vram_off(BASE_OK + 2048);
	CHECK(rx550_vram_resource_valid(&r, TABLA_BYTES, TABLA_ALIGN) != 0,
	      "offset a mitad de pagina rechazado");
}

static void fase_state(void)
{
	struct rx550_vram_resource r;

	printf("campo state\n");

	/* HUECO 3: state no se miraba.  ABSENT con owner puesto significa que
	 * no hay memoria, y pasaba el filtro entero. */
	r = buena(TABLA_ALIGN);
	r.state = RX550_VRAM_ABSENT;
	CHECK(rx550_vram_resource_valid(&r, TABLA_BYTES, TABLA_ALIGN) != 0,
	      "state=ABSENT con owner puesto rechazado");

	/* RELEASED con owner puesto es la misma mentira en otro sitio: ya se
	 * devolvio, y sin embargo tiene todos los demas campos correctos. */
	r = buena(TABLA_ALIGN);
	r.state = RX550_VRAM_RELEASED;
	CHECK(rx550_vram_resource_valid(&r, TABLA_BYTES, TABLA_ALIGN) != 0,
	      "state=RELEASED con owner puesto rechazado");

	r = buena(TABLA_ALIGN);
	r.state = RX550_VRAM_HELD;
	CHECK(rx550_vram_resource_valid(&r, TABLA_BYTES, TABLA_ALIGN) == 0,
	      "state=HELD es el unico que pasa");
}

/* ── las tres comprobaciones que ya existian, para que el filtro nuevo no las
      haya sustituido por las suyas ─────────────────────────────────────── */
static void fase_preexistentes(void)
{
	struct rx550_vram_resource r;

	printf("comprobaciones preexistentes\n");

	r = buena(TABLA_ALIGN);
	r.owner = NULL;
	CHECK(rx550_vram_resource_valid(&r, TABLA_BYTES, TABLA_ALIGN) != 0,
	      "owner nulo rechazado");

	r = buena(TABLA_ALIGN);
	r.size = TABLA_BYTES - 1;
	CHECK(rx550_vram_resource_valid(&r, TABLA_BYTES, TABLA_ALIGN) != 0,
	      "size menor que min_size rechazado");

	r = buena(TABLA_ALIGN);
	r.size = 0;
	CHECK(rx550_vram_resource_valid(&r, 1, TABLA_ALIGN) != 0,
	      "size cero con min_size=1 rechazado");

	r = buena(TABLA_ALIGN);
	r.size = TABLA_BYTES * 4;
	CHECK(rx550_vram_resource_valid(&r, TABLA_BYTES, TABLA_ALIGN) == 0,
	      "size mayor que min_size aceptado");
}

/* ── el fallo que mas caro seria: pasar enteramente ─────────────────────── */
static void fase_mutacion(void)
{
	struct rx550_vram_resource r;

	printf("mutacion\n");

	/* Cada fila cambia UNA cosa respecto a un vector valido.  Si alguna de
	 * estas pasara, el filtro tiene un agujero. */
	r = buena(TABLA_ALIGN); r.owner = NULL;
	CHECK(rx550_vram_resource_valid(&r, TABLA_BYTES, TABLA_ALIGN) != 0, "m1 owner nulo");

	r = buena(TABLA_ALIGN); r.state = RX550_VRAM_ABSENT;
	CHECK(rx550_vram_resource_valid(&r, TABLA_BYTES, TABLA_ALIGN) != 0, "m2 absent");

	r = buena(TABLA_ALIGN); r.state = RX550_VRAM_RELEASED;
	CHECK(rx550_vram_resource_valid(&r, TABLA_BYTES, TABLA_ALIGN) != 0, "m3 released");

	r = buena(TABLA_ALIGN); r.alignment = 0;
	CHECK(rx550_vram_resource_valid(&r, TABLA_BYTES, TABLA_ALIGN) != 0, "m4 sin alignment");

	r = buena(TABLA_ALIGN); r.alignment = 1;
	CHECK(rx550_vram_resource_valid(&r, TABLA_BYTES, TABLA_ALIGN) != 0, "m5 alignment 1");

	r = buena(TABLA_ALIGN); r.size = TABLA_BYTES - 8;
	CHECK(rx550_vram_resource_valid(&r, TABLA_BYTES, TABLA_ALIGN) != 0, "m6 size corto");

	r = buena(TABLA_ALIGN); r.offset = rx550_vram_off(BASE_OK + 8);
	CHECK(rx550_vram_resource_valid(&r, TABLA_BYTES, TABLA_ALIGN) != 0, "m7 offset +8");

	r = buena(TABLA_ALIGN); r.offset = rx550_vram_off(BASE_OK + 4095);
	CHECK(rx550_vram_resource_valid(&r, TABLA_BYTES, TABLA_ALIGN) != 0, "m8 offset +4095");

	/* El control: sin tocar nada, pasa.  Si ESTE falla, el resto de la fase
	 * no demuestra nada, porque significaria que el filtro rechaza todo.
	 * Va en variable por la misma razon que arriba. */
	r = buena(TABLA_ALIGN);
	CHECK(rx550_vram_resource_valid(&r, TABLA_BYTES, TABLA_ALIGN) == 0,
	      "control: sin mutar, aceptado");
}

/* ── lo que el contrato sigue SIN保証, para que no se lea mas de lo que dice ─ */
static void fase_no_garantizado(void)
{
	struct rx550_vram_resource r = buena(TABLA_ALIGN);

	printf("lo que el contrato no garantiza\n");

	/* Dos reservas validas pueden solaparse.  El filtro mira una reserva, no
	 * un conjunto: no hay capacidad, no hay base, no hay no-solape. */
	CHECK(1, "el filtro NO comprueba el solape entre dos recursos validos");

	/* Y no hay capacidad declarada en ninguna parte del componente. */
	CHECK(1, "el filtro NO puede rechazar 'no cabe': no conoce la capacidad");

	/* r.size es lo que el allocator PROMETE.  El filtro no puede saber si
	 * es cierto. */
	r.size = UINT64_C(0xFFFFFFFFFFFFF);
	CHECK(rx550_vram_resource_valid(&r, TABLA_BYTES, TABLA_ALIGN) == 0,
	      "un size absurdo se acepta si cumple el contrato: NO es verificable aqui");
}

/* ── el espacio de errores, y que se propague ─────────────────────────── */
static void fase_errores(void)
{
	struct rx550_vram_resource r;
	int rc;

	printf("espacio de errores\n");

	/* Los seis codigos son DISTINTOS.  Un espacio de errores donde dos
	 * codigos valen lo mismo no es un espacio de errores: es un -1 con
	 * nombres. */
	CHECK(RX550_VRAM_OK == 0, "OK == 0");
	CHECK(RX550_VRAM_ERR_NULO != RX550_VRAM_ERR_ALIGN, "NULO != ALIGN");
	CHECK(RX550_VRAM_ERR_ALIGN != RX550_VRAM_ERR_SIN_MEM, "ALIGN != SIN_MEM");
	CHECK(RX550_VRAM_ERR_SIN_MEM != RX550_VRAM_ERR_BACKEND, "SIN_MEM != BACKEND");
	CHECK(RX550_VRAM_ERR_BACKEND != RX550_VRAM_ERR_INVALIDO, "BACKEND != INVALIDO");
	CHECK(RX550_VRAM_ERR_INVALIDO != RX550_VRAM_ERR_DOBLE, "INVALIDO != DOBLE");
	CHECK(RX550_VRAM_ERR_NULO < 0 && RX550_VRAM_ERR_DOBLE <= -90,
	      "el rango es -90.. y todos negativos");
	CHECK(RX550_VRAM_ERR_DOBLE > -100, "y no colisiona con -1..-3 de los otros");

	/* Y el filtro se puede expresar EN TERMINOS DEL CODIGO, no de un -1
	 * anonimo.  Este es el punto: antes no habia nada que nombrar. */
	r = buena(TABLA_ALIGN);
	CHECK(rx550_vram_resource_valid(&r, TABLA_BYTES, TABLA_ALIGN) == 0,
	      "un vector valido no es ningun error");
	r = buena(TABLA_ALIGN);
	r.owner = NULL;
	CHECK(rx550_vram_resource_valid(&r, TABLA_BYTES, TABLA_ALIGN) != 0,
	      "y uno invalido es uno, aunque el filtro no lo distinga todavia");
	rc = RX550_VRAM_ERR_INVALIDO;
	CHECK(rc != 0, "el codigo del filtro es no-cero, como el -1 que sustituye");
}

int main(void)
{
	printf("test_vram — contrato de la frontera de VRAM\n\n");

	fase_estados();
	fase_vector_valido();
	fase_alignment();
	fase_state();
	fase_preexistentes();
	fase_mutacion();
	fase_no_garantizado();
	fase_errores();

	printf("\n  %d pass, %d fail\n", pass, fail);
	return fail ? 1 : 0;
}
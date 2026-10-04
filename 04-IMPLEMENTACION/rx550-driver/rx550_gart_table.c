/* SPDX-License-Identifier: GPL-2.0 */
/*
 * rx550_gart_table.c — geometria de la tabla de la GART y su relleno inicial.
 *
 *   TARGET = RX 550 instalada en esta maquina
 *   SCOPE  = EXCLUSIVO
 *
 * Aritmetica pura.  No hay mapa, no hay hardware, y este fichero compila igual en
 * los dos contextos del kernel, igual que rx550_gart_seq.c.
 */
#include "rx550_gart_table.h"
#include "rx550_vmid0_gart.h"		/* RX550_GART_SIZE_MAX */

int rx550_gart_tabla_geom(uint64_t gart_size, struct rx550_gart_tabla_geom *out)
{
	struct rx550_gart_tabla_geom g;

	if (out == NULL)
		return RX550_GART_TABLA_ERR_INCONSISTENT;

	/*  Una GART de cero bytes no existe,  y una tabla de cero entradas no
	 *  cubre nada:  las dos son el mismo error y se rechazan a la vez. */
	if (gart_size == 0u)
		return RX550_GART_TABLA_ERR_TAMANO;
	/*  El corpus trunca:  num_gpu_pages = gart_size / 4096.  Un tamano que no
	 *  sea multiplo de 4096 perderia hasta 4095 paginas  (32 MiB de GART)
	 *  sin que nadie lo viera,  porque la cuenta cuadra igual.  Se exige
	 *  exactitud en vez de copiar el truncamiento. */
	if (gart_size % RX550_PAGE_SIZE != 0u)
		return RX550_GART_TABLA_ERR_TAMANO;
	/*  La politica del propio driver,  rx550_vmid0_gart.h:72. */
	if (gart_size > RX550_GART_SIZE_MAX)
		return RX550_GART_TABLA_ERR_TAMANO;

	g.paginas = gart_size / RX550_PAGE_SIZE;
	/*  El *8 de gmc_v8_0.c:960.  El desplazamiento y no una multiplicacion,
	 *  y no por ahorar una division:  el compilador lo convierte igual,  pero
	 *  escrito asi el numero del corpus y el codigo son el mismo numero y se
	 *  pueden comparar de un vistazo. */
	g.bytes = g.paginas << 3;
	/*  Y que el buffer del llamante tenga un numero de entradas que quepa en
	 *  su indice.  En un host de 64 bits nunca pasa;  en un kernel de 32 con
	 *  la GART al maximo son 65536,  que cabe de sobra;  y el dia que la GART
	 *  crezca,  este es el sitio donde se dice que no. */
	if (g.paginas > (uint64_t)(SIZE_MAX / RX550_GART_TABLA_ENTRADA_BYTES))
		return RX550_GART_TABLA_ERR_DESBORDA;
	g.entradas_max = (uint32_t)(g.paginas >
				    (uint64_t)UINT32_MAX ? UINT32_MAX : g.paginas);

	*out = g;
	return 0;
}

int rx550_gart_tabla_rellena(uint64_t *tabla, uint64_t entradas, uint64_t valor)
{
	if (tabla == NULL)
		return RX550_GART_TABLA_ERR_INCONSISTENT;
	if (entradas == 0u)
		return RX550_GART_TABLA_ERR_TAMANO;
	if (entradas > (uint64_t)(SIZE_MAX / sizeof(uint64_t)))
		return RX550_GART_TABLA_ERR_DESBORDA;

	while (entradas--)
		*tabla++ = valor;
	return 0;
}

int rx550_gart_tabla_reinicia(uint64_t *tabla, uint64_t entradas)
{
	return rx550_gart_tabla_rellena(tabla, entradas,
					RX550_GART_PTE_EXECUTABLE);
}
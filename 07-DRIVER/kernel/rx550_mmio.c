/* SPDX-License-Identifier: GPL-2.0 */
/*
 * rx550_mmio.c -- la aritmetica del contrato de la ventana de registros.
 *
 * Ver rx550_mmio.h para por que esto no esta junto a pci_iomap.
 *
 * Lo que hay aqui son tres funciones sin dependencia del kernel, y las tres
 * estan escritas para que un fallo se pueda provoked a proposito en un test:
 * por eso los motivos son un enum numerado y por eso la respuesta es un valor,
 * no un -ENOMEM generico. Un rechazo sin motivo no se puede distinguir de un
 * fallo de bus, y un fallo de bus que parece un rechazo hace que se repita
 * forever algo que no va a cambiar.
 */

#include "rx550_mmio.h"

/*
 * Motivos, en orden de gravedad creciente. La geometria se comprueba antes que
 * nada porque es lo que no depende de nadie: si el BAR no mide lo que se
 * espera, ningun otro dato puede salvar el mapeo.
 */
static const char *const motivos[] = {
	[RX550_MMIO_OK]		= "geometria conforme: la ventana mide lo esperado",
	[RX550_MMIO_BAR_AUSENTE]	= "el BAR de registros no esta implementado por el hardware",
	[RX550_MMIO_BAR_NO_MEMORIA]	= "el BAR existe pero no es una region de memoria",
	[RX550_MMIO_TAMANO_OTRO]	= "el BAR mide una longitud distinta de la medida",
	[RX550_MMIO_NO_VERIFICADA]	= "geometria conforme, pero el llamador no derivo el indice",
	[RX550_MMIO_BAR_AMBIGUO]	= "varios BAR de memoria miden lo mismo: no se puede elegir sin adivinar",
};

const char *
rx550_mmio_motivo(unsigned motivo)
{
	if (motivo >= sizeof(motivos) / sizeof(motivos[0]))
		return "motivo desconocido: eso es un fallo de la tabla, no del BAR";
	if (!motivos[motivo])
		return "motivo sin texto: eso es un hueco en la tabla, no una ventana valida";
	return motivos[motivo];
}

/*
 * rx550_mmio_deriva -- el indice del BAR de registros, derivado y no declarado.
 *
 * Criterio: el UNICO BAR que es memoria y mide exactamente RX550_MMIO_LEN. Las
 * dos mitades estan a proposito, y cada una descarta un BAR real de esta placa:
 *
 *   es_memoria   descarta el BAR4, que son 256 BYTES de puertos de E/S. Sin esa
 *                mitad, un puerto de la longitud exacta pasaria, y mapear puertos
 *                no es lo que hace este driver.
 *   len == LEN   descarta el BAR0 de 256 MiB y el BAR2 de 2 MiB, que son ventanas
 *                de memoria de verdad, y la segunda es la que el driver de
 *                referencia mapea para los ASIC anteriores a Bonaire.
 *
 * "Unico" es la palabra que carga el peso. Se cuentan los candidatos ANTES de
 * devolver nada y, si hay mas de uno, no se devuelve el primero: devolver el
 * primero seria elegir por el orden del array, que es una propiedad de como se
 * escribio la tabla y no del hardware.
 *
 * NO se mira la direccion, y no por pereza: leerla necesita root --findings/176
 * §4 lo deja como BLOCKED_BY_PERMISSION-- mientras que la longitud y el tipo se
 * leen sin el. Un criterio que dependiera de root no se podria comprobar en
 * userspace, que es justo donde esta funcion se prueba.
 *
 * MEDIDO en esta placa (findings/176 §1 y findings/305), el criterio selecciona
 * un unico indice:
 *
 *     BAR0  268435456  memoria   256 MiB   descartado por longitud
 *     BAR2   2097152  memoria     2 MiB   descartado por longitud
 *     BAR4        256  E/S      256 B     descartado por tipo y por longitud
 *     BAR5    262144  memoria   256 KiB   <- el unico
 *
 * Y ese mismo indice lo dice el codigo del driver de referencia por otra via:
 * amdgpu_device.c:3812 compara asic_type con CHIP_BONAIRE, que vale 5, y
 * CHIP_POLARIS12 vale 17, luego cumple y mapea el 5. Dos vias, un numero.
 */
int
rx550_mmio_deriva(const struct rx550_bar_desc *bars, unsigned n,
		  struct rx550_mmio_info *out)
{
	unsigned i;
	int encontrado = -1;
	unsigned candidatos = 0;

	if (!out || !bars || n == 0)
		return RX550_MMIO_BAR_AUSENTE;

	out->bar = 0;
	out->len = 0;
	out->es_valido = 0;
	out->es_mapeado = 0;
	out->motivo = RX550_MMIO_BAR_AUSENTE;
	out->porque = rx550_mmio_motivo(RX550_MMIO_BAR_AUSENTE);

	for (i = 0; i < n; i++) {
		if (!bars[i].es_memoria)
			continue;
		if (bars[i].len != RX550_MMIO_LEN)
			continue;
		candidatos++;
		if (encontrado < 0)
			encontrado = (int)i;
	}

	if (candidatos > 1) {
		out->motivo = RX550_MMIO_BAR_AMBIGUO;
		out->porque = rx550_mmio_motivo(RX550_MMIO_BAR_AMBIGUO);
		return RX550_MMIO_BAR_AMBIGUO;
	}

	if (encontrado < 0) {
		/*
		 * Tres fallos distintos, y no dos. La version de dos, que fue la
		 * primera, dejaba RX550_MMIO_BAR_NO_MEMORIA sin emitir NUNCA, y su
		 * texto dice "el BAR existe pero no es una region de memoria": un
		 * valor de enum inalcanzable cuyo texto afirma un control es
		 * exactamente lo que este proyecto no admite.
		 *
		 *   hay un BAR de E/S de la longitud correcta -> NO_MEMORIA
		 *     existe, mide lo que tiene que medir, y no es memoria. Mapear
		 *     puertos no es lo que hace este driver.
		 *   hay memoria pero de otro tamano           -> TAMANO_OTRO
		 *     el hardware es el de siempre y la ventana no esta.
		 *   no hay nada implementado                  -> BAR_AUSENTE
		 */
		int hay_memoria = 0;
		int hay_io = 0;
		for (i = 0; i < n; i++) {
			if (bars[i].len == 0)
				continue;
			if (bars[i].es_memoria)
				hay_memoria = 1;
			else
				hay_io = 1;
		}
		if (hay_io && !hay_memoria)
			out->motivo = RX550_MMIO_BAR_NO_MEMORIA;
		else if (hay_memoria)
			out->motivo = RX550_MMIO_TAMANO_OTRO;
		else
			out->motivo = RX550_MMIO_BAR_AUSENTE;
		out->porque = rx550_mmio_motivo(out->motivo);
		return out->motivo;
	}

	out->bar = bars[encontrado].indice;
	out->len = bars[encontrado].len;
	out->es_valido = 1;
	out->motivo = RX550_MMIO_OK;
	out->porque = rx550_mmio_motivo(RX550_MMIO_OK);
	return RX550_MMIO_OK;
}

/*
 * rx550_mmio_valida -- decide si el BAR de registros puede mapearse.
 *
 * La longitud EXACTA, no un minimo. Un BAR mas grande podria ser una apertura
 * mayor y no un fallo; un BAR mas pequeno es una apertura menor y escribir en
 * el ultimo medio mebibyte seria escribir fuera. Ante la duda, no se mapea:
 * un driver que no arranca por un modulo conservador se arregla quitando una
 * comprobacion, y uno que corrompe memoria no.
 *
 * 2026-10-03. Se quito la comprobacion `bar != RX550_MMIO_BAR`. Mantenida, era un
 * control que no custodiaba nada: comparaba el indice contra la constante que
 * pretendia validar, y las dos venian del mismo header. Un test que se pasa la
 * respuesta como entrada no prueba la respuesta. El indice llega ahora de
 * rx550_mmio_deriva(), que tiene una fuente externa --la geometria que midio el
 * core de PCI-- y por eso esa comprobacion si puede tener exito y esta si falla.
 */
int
rx550_mmio_valida(__u8 bar, __u32 len, struct rx550_mmio_info *out)
{
	if (!out)
		return RX550_MMIO_BAR_AUSENTE;

	out->bar = bar;
	out->len = len;
	out->es_valido = 0;
	out->es_mapeado = 0;
	out->motivo = RX550_MMIO_BAR_AUSENTE;
	out->porque = rx550_mmio_motivo(RX550_MMIO_BAR_AUSENTE);

	if (len == 0) {
		out->motivo = RX550_MMIO_BAR_AUSENTE;
		out->porque = rx550_mmio_motivo(RX550_MMIO_BAR_AUSENTE);
		return out->motivo;
	}
	if (len != RX550_MMIO_LEN) {
		out->motivo = RX550_MMIO_TAMANO_OTRO;
		out->porque = rx550_mmio_motivo(RX550_MMIO_TAMANO_OTRO);
		return out->motivo;
	}

	/*
	 * Geometria conforme. Antes decia "NO basta" y devolvia
	 * RX550_MMIO_NO_VERIFICADA, porque el indice estaba DECLARADO en el header
	 * y compararlo contra si mismo no es una comprobacion. Se quito esa
	 * comparacion y con ella el enclavamiento, y lo que queda aqui es lo que
	 * si es comprobable en esta capa: que la longitud sea exactamente la de la
	 * ventana, sin minimos ni margenes.
	 *
	 * El indice que llega ya viene derivado de rx550_mmio_deriva(), que tiene
	 * una fuente que no es este repositorio: la geometria que midio el core de
	 * PCI. Ver rx550_mmio.h para las tres fuentes.
	 */
	out->es_valido = 1;
	out->motivo = RX550_MMIO_OK;
	out->porque = rx550_mmio_motivo(RX550_MMIO_OK);
	return RX550_MMIO_OK;
}

/*
 * rx550_mmio_offset_ok -- un offset cae dentro de la ventana.
 *
 * La comparacion es sin signo y el limite es el entero de 32 bits completo: un
 * offset de 0x80000000 en un int con signo seria negativo y pasaria el filtro.
 * Aqui los dos son __u32 y no hay conversion que hacer.
 */
int
rx550_mmio_offset_ok(__u32 offset, __u32 len)
{
	return offset < len;
}

unsigned
rx550_mmio_offsetes_fuera(const __u32 *offs, unsigned n, __u32 len)
{
	unsigned fuera = 0;
	unsigned i;

	if (!offs)
		return n;	/* sin lista no se puede afirmar nada: se cuenta todo */

	for (i = 0; i < n; i++) {
		if (!rx550_mmio_offset_ok(offs[i], len))
			fuera++;
	}
	return fuera;
}

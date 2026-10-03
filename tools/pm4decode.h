/* SPDX-License-Identifier: GPL-2.0 */
/*
 * pm4decode.h - interfaz del decodificador de IB, para usar desde las pruebas.
 *
 * tools/pm4decode.c trae el codigo; esto solo declara lo que las pruebas
 * necesitan. La separacion existe porque pm4decode.c tiene su propio main()
 * y su propio selftest, y un .c con main() no se puede enlazar en un binario
 * que ya tiene otro.
 *
 * LO QUE ESTO COMPRUEBA, Y POR QUE NO ESTA EN LOS OTROS VALIDADORES
 *
 * tools/rx550pm4val.c y 07-DRIVER/tests/test_pm4.c comparan el DWORD DE
 * CABECERA de cada paquete contra una constante calculada a mano. Eso no cubre:
 *
 *   - un paquete que declara count=N y al que se le escriben N+1 dwords;
 *   - una IB que el codificador trunca en silencio por falta de sitio, con el
 *     test en verde porque solo mira lo que si se escribio;
 *   - argumentos en orden equivocado con la cabecera correcta.
 *
 * Decodificar la IB entera y exigir que lo consumado termine donde acaba la IB
 * es lo que cubre las tres. Y no necesita la especificacion de GFX8, que no
 * esta publicada: solo el formato de cabecera, que esta medido en el binario.
 */
#ifndef RX550_PM4DECODE_H
#define RX550_PM4DECODE_H

#include <stdint.h>

/* El paquete mas largo que emite el driver propio cabe en 8 dwords. El
 * decodificador copia hasta 8 al struct y sigue contando el total aparte, para
 * que un paquete largo no desborde el hueco del llamante. */
#define PM4_DW_MAX 8

enum pm4_defecto {
	PM4_OK = 0,
	PM4_CONSUMO_EXACTO,	/* red de seguridad, inalcanzable por construccion */
	PM4_COUNT_IMPOSIBLE,	/* truncamiento, o PACKET2 con count impar */
	PM4_NO_ES_PM4,		/* cabecera que no es PACKET2 ni PACKET3 */
	PM4_SIN_PAQUETE,		/* longitud imposible o huecos agotados */
};

struct pm4_pkt {
	uint32_t	dw[PM4_DW_MAX];
	unsigned	n_dw;		/* total real, puede exceder PM4_DW_MAX */
	unsigned	tipo;		/* headerType */
	unsigned	count;		/* bits 21:16 */
	unsigned	opcode;		/* bits 15:8, PACKET3 */
	unsigned	compute;		/* bit 1 */
	unsigned	offset;		/* dword donde empieza, para citarlo */
};

struct pm4_resultado {
	/* Paquetes decodificados ANTES del defecto. Se rellena tambien cuando
	 * la decodificacion falla, y es lo que hace util el fallo: saber que la
	 * IB lleva un paquete bueno y luego uno que esta herramienta no cubre
	 * es informacion; "0 paquetes" no lo es. */
	unsigned	n_pkt;
	enum pm4_defecto defecto;
	unsigned	offset;
	/* 256, no 160. El mensaje mas largo del decodificador necesita 246
	 * caracteres + NUL medidos sobre los seis snprintf de pm4_decode(), con
	 * cada %u al ancho maximo de un unsigned int. Con 160, -Wformat-truncation
	 * avisaba y con razon: la cola informativa -- el byte bajo con el op SDMA
	 * -- se perdia. Un mensaje truncado dice media verdad, que es peor que
	 * callarse. tools/pm4decode.c lo comprueba en su selftest. */
	char		motivo[256];
};

/* Devuelve 0 si la IB es bien formada, 1 si no. res se rellena siempre. */
int pm4_decode(const uint32_t *buf, unsigned n_dw, struct pm4_pkt *out,
	       unsigned max_pkt, struct pm4_resultado *res);

/* Nombre legible del opcode, o NULL si no es uno que el driver emita.
 * No es una tabla de semantica: son los nombres de sid.h y vid.h para los
 * opcodes que rx550_pm4.c puede escribir. Lo demas se queda en hexadecimal.
 *
 * TRANSCRITO, no escrito de memoria: la primera tabla de esto tenía siete
 * entradas equivocadas y lo detectó el test, no la lectura. El comentario de
 * pm4decode.c las lista. */
const char *pm4_nombre(unsigned opcode);

#endif /* RX550_PM4DECODE_H */
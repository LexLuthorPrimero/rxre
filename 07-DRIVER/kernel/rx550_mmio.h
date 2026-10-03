/* SPDX-License-Identifier: GPL-2.0 */
/*
 * rx550_mmio.h -- el contrato de la ventana de registros, sin kernel API.
 *
 * POR QUE ESTE FICHERO NO LLAMA A pci_iomap
 *
 * Porque la parte que puede estar mal no es la llamada: es la ARITMETICA. Si
 * el BAR de registros mide otra cosa, o si un offset se sale, la llamada
 * compila igual y el fallo aparece en la GPU, lejos. Esa aritmetica no
 * necesita el kernel para comprobarse, asi que vive aqui, en C puro, y se
 * prueba en userspace sin hardware.
 *
 * La llamada a pci_iomap vive en rx550_drv.c, que si depende del kernel. Este
 * fichero decide SI se mapea y con que limites; aquel ejecuta el mapeo. La
 * separacion es la misma que en el resto del proyecto: lo comprobable fuera,
 * lo ejecutable dentro.
 *
 * LO QUE ESTA PROVEN Y LO QUE NO
 *
 * PROVEN (findings/176, medido con stat() sin root, 4 de 4 contra la tabla):
 *
 *     BAR 0   256 MiB   memoria 64-bit prefetchable  -- ventana sobre VRAM
 *     BAR 2     2 MiB   memoria 64-bit prefetchable  -- la apertura de registros
 *     BAR 4     256 B   puertos de E/S
 *     BAR 5   256 KiB   memoria 32-bit no prefetchable
 *
 * Los tamanos se leen del tamano del inodo de /sys/bus/pci/.../resourceN, que
 * NO hace falta abrir el fichero: el contenido es la direccion y necesita root,
 * la longitud no.
 *
 * NOT_IN_CORPUS (findings/176 §3, findings/180 §5): QUE BAR CONTIENE QUE BLOQUE
 * de registros. No esta escrito en ninguna parte alcanzable --
 * struct amdgpu_ip_block_version, amdgpu_ip.h:108, no lleva indice de BAR; no
 * hay ni un pci_iomap en los dos arboles de amdgpu; y las constantes PCI_BARn_*
 * del nucleo no estan en ningun corpus del proyecto.
 *
 * Por eso RX550_MMIO_BAR esta DECLARADO y no derivado. Un valor sin fuente no
 * se documenta como si la tuviera: se marca, y el mapa se usa solo cuando su
 * longitud coincide con la medida. Si amdgpu	mapeara el registro en otro BAR,
 * esta comprobacion lo rechazaria en vez de escribir en la ventana equivocada.
 */

#ifndef _RX550_MMIO_H_
#define _RX550_MMIO_H_

/*
 * __u32/__u8, NO u32/u8. Los nombres cortos son typedef exclusive del kernel:
 * en userspace linux/types.h solo ofrece __u32 y nada mas, y un header escrito
 * con u32 compila en el modulo y falla en el test con "unknown type name". Es
 * la regla que ya esta escrita en rx550_pm4.h:18-20, y que este fichero
 * incumplio en su primera version, que es la forma mas cara de no leer lo que
 * uno mismo escribio hace dos horas.
 */
#include <linux/types.h>

/*
 * CORREGIDO por 202. Esto era 2 MiB, y 2 MiB es la longitud de resource2.
 * La ventana de registros NO es resource2.
 *
 * La apertura de registros es resource5, de 256 KiB. Tres cosas lo fijan:
 *
 *  1  MEDICION    stat() sobre resource5 -> 262144 bytes, sin root.
 *                 stat() sobre resource2 -> 2097152 bytes. Son distintos.
 *  2  OBSERVACION el kernel, al arrancar, imprime su propia variable:
 *                   "register mmio size: 262144"
 *                 y 262144 es exactamente la longitud de resource5.
 *  3  CODIGO      amdgpu_device.c:3995-4001 elige BAR 5 o BAR 2 segun el ASIC.
 *
 * El enum que decide la rama (CHIP_POLARIS12 frente a CHIP_BONAIRE) NO esta en
 * el corpus: NOT_IN_CORPUS. No hace falta para la conclusion, porque la
 * OBSERVACION ya dice que la rama TOMADA fue la de 262144 bytes. Un valor
 * medido en ejecucion decide la rama sin necesitar el orden del enum.
 *
 * Que 2 MiBiguiera no era un error de busqueda: 176 acerto al medir resource2 y
 * el equivoco fue dar por hecho que la ventana de registros es resource2. El
 * numero era correcto y la pregunta que lo accompanying estaba mal.
 */
#define RX550_MMIO_LEN		(256u * 1024u)

/*
 * DERIVADO, NO DECLARADO. Este bloque cambió el 2026-10-03, y el cambio es la
 * liberación de un enclavamiento que el propio driver se habia puesto.
 *
 * ANTES (hasta el 2026-10-03) este fichero decia, literalmente:
 *
 *     DECLARADO, NO DERIVADO. La evidencia que falta es el bloque<->BAR.
 *     y la constante era el 5, escrita como un define al principio de este
 *     fichero.
 *
 *     Se cita SIN la forma del define a proposito. La primera version de este
 *     bloque decia el nombre de la constante, con su forma de definicion,
 *     DENTRO del comentario. Eso deja una trampa: cualquier grep que busque esa
 *     forma la encuentra y concluye que la constante sigue existiendo.
 *
 *     El fallo que se aplico aqui es el que el propio Makefile de 07-DRIVER
 *     registra para sus controles --"un control que se dispara por su propia
 *     documentacion no vigila nada"-- carried a la documentacion, que es donde
 *     mas discretamente se cuela.
 *
 *     Y el nombre NO se escribe aqui, ni entero ni troceado, precisamente
 *     porque esta linea es la que el grep de cualquiera leeria. Un comentario
 *     que habla de como evitar una trampa no puede contener la trampa.
 *
 * y rx550_mmio_valida() rechazaba con RX550_MMIO_NO_VERIFICADA unicamente porque
 * el indice no tenia fuente. Eso esta bien si la fuente no existe. El problema
 * es que se buscaba en el sitio equivocado, y por eso un hallazgo anterior
 * (`176` §3) la clasifico NOT_IN_CORPUS.
 *
 * LO QUE SE BUSCO Y LO QUE HAY
 *
 *  1  La pregunta que el driver hace NO es "que bloque de amdgpu vive en que
 *     BAR". Es "que BAR de ESTE dispositivo es la apertura de registros". La
 *     primera es NOT_IN_CORPUS y lo sigue siendo. La segunda tiene tres fuentes.
 *
 *  2  CODIGO. El driver de referencia mapea con pci_resource_* e ioremap, NO con
 *     pci_iomap, y por eso un grep de pci_iomap sobre el arbol de amdgpu da cero
 *     y parecia que no habia fuente:
 *
 *       amdgpu_device.c:3810   la linea de comentario "Registers mapping"
 *       amdgpu_device.c:3812   if (adev->asic_type >= CHIP_BONAIRE) {
 *       amdgpu_device.c:3813           adev->rmmio_base = pci_resource_start(adev->pdev, 5);
 *       amdgpu_device.c:3814           adev->rmmio_size = pci_resource_len(adev->pdev, 5);
 *       amdgpu_device.c:3815   } else { ... 2 ... }
 *       amdgpu_device.c:3823   adev->rmmio = ioremap(adev->rmmio_base, adev->rmmio_size);
 *
 *  3  LOS DOS NUMEROS, con nombre. enum amd_asic_type arranca en CHIP_TAHITI = 0
 *     y los ordinales se contam, porque no hay "= N" en el fuente:
 *
 *       amd_asic_type.h:37    CHIP_BONAIRE,       -> 5
 *       amd_asic_type.h:49    CHIP_POLARIS12,     -> 17
 *
 *     17 >= 5, luego la rama TOMADA es la del 5. Y CHIP_POLARIS12 = 17 es el
 *     que ya afirmaba fingerprint.py como COINCIDE.
 *
 *  4  OBSERVACION. El kernel en ejecucion imprime su propia variable, y su
 *     longitud es la de resource5:
 *
 *       "register mmio size: 262144"          = pci_resource_len(pdev, 5)
 *
 * Y 262144 es exactamente RX550_MMIO_LEN, medido sin root con stat() (`176` §1).
 *
 * LA DERIVACION DE ESTE FICHERO, y por que no usa el enum
 *
 * rx550_mmio_deriva() no compara asic_type con CHIP_BONAIRE, y es a proposito:
 *
 *   - el enum vive en <drm/amd_asic_type.h>, que es una cabecera de KERNEL. Esta
 *     capa se compila en userspace para probarse sin hardware, y no puede
 *     depender del kernel. Sus numeros estan citados arriba, no redefinidos.
 *   - la comparacion con el enum es una CORROBORACION, y vale como tal: una via
 *     (geometria medida) y otra (codigo mas dos ordinales) dicen 5 por separado.
 *   - la geometria es la que el propio hardware impone. Un BAR de registros de
 *     256 KiB es 256 KiB porque el bloque cabe, no porque el enum lo diga.
 *
 * Y el criterio es UNICO en esta placa, que es lo que lo hace creible y lo que
 * hace que un fallo sea detectable: de los cuatro BAR implementados, solo BAR5
 * es memoria de exactamente 256 KiB. BAR0 es de 256 MiB, BAR2 de 2 MiB y BAR4 de
 * 256 BYTES de E/S. Doble discriminacion, tamano y tipo.
 */

/* Los ocho offsets de registro del driver, verificados contra el ASIC en
 * findings/180. Se repiten aqui para que el modulo no dependa de rx550_pm4.h
 * solo para esto: son dos capas distintas y se pueden mover por separado. */
#define RX550_MM_VM_CTX0_PTBA		0x54f
#define RX550_MM_VM_CTX8_PTBA		0x50e
#define RX550_MM_VM_INVALIDATE_REQ	0x51e

/* Motivos por los que no se mapea. Se numeran para poder contarlos y para que
 * un -ENODEV sin motivo no sea indistinguible de un fallo de bus.
 *
 * RX550_MMIO_NO_VERIFICADA sigue existiendo, pero ya NO es el estado permanente
 * de una geometria buena: hasta el 2026-10-03 lo era, porque el indice estaba
 * declarado. Se conserva el valor, porque los numeros de un enum no se renumeran
 * en un arbol que los cita, y ahora lo que lo produce es un llamador que paso
 * una geometria sin derivar. Que exista un motivo para "no verificaste" no
 * significa que se use. */
enum rx550_mmio_rechazo {
	RX550_MMIO_OK = 0,
	RX550_MMIO_BAR_AUSENTE,		/* no hay un BAR de memoria de esa longitud */
	RX550_MMIO_BAR_NO_MEMORIA,	/* existe pero no es memoria */
	RX550_MMIO_TAMANO_OTRO,		/* mide, pero no lo que se esperaba */
	RX550_MMIO_NO_VERIFICADA,	/* el llamador no derivo el indice */
	RX550_MMIO_BAR_AMBIGUO,		/* dos BAR de memoria de esa longitud */
};

/*
 * Un BAR, tal y como el core de PCI lo deja normalizado. Son las TRES cosas que
 * hacen falta, y las tres las da pci_resource_len() y pci_resource_flags(), que
 * es exactamente lo que usa el driver de referencia en amdgpu_device.c:3813-3814.
 *
 * Deliberadamente NO lleva la direccion. Leerla necesita root (`176` §4,
 * BLOCKED_BY_PERMISSION) y no hace falta para derivar el indice: la longitud y el
 * tipo bastan, y son los que no necesitan permisos.
 */
struct rx550_bar_desc {
	__u8	indice;		/* 0..5, el numero de ranura */
	__u32	len;		/* pci_resource_len(), bytes */
	__u8	es_memoria;	/* PCI_RESOURCE_FLAG_MEMORY, 1 o 0 */
};

struct rx550_mmio_info {
	__u8	bar;		/* indice que se mapearia */
	__u32	len;		/* longitud medida del BAR */
	__u8	es_valido;	/* la geometria coincide con lo esperado */
	__u8	es_mapeado;	/* hay un mapa vivo; lo pone el wrapper */
	__u32	motivo;	/* enum rx550_mmio_rechazo */
	const char	*porque;	/* frase legible del motivo */
};

const char *rx550_mmio_motivo(unsigned motivo);

/*
 * DERIVA el indice del BAR de registros, en vez de compararlo con una constante.
 *
 * Criterio: el UNICO BAR que es memoria y mide exactamente RX550_MMIO_LEN. Tres
 * resultados distintos, y los tres son fallos:
 *
 *   ninguno    RX550_MMIO_BAR_AUSENTE
 *   varios     RX550_MMIO_BAR_AMBIGUO      <- no se elige, porque elegir seria
 *                                              arbitrario, y un mapa de la
 *                                              ventana equivocada es peor que
 *                                              no mapear
 *   uno        RX550_MMIO_OK, y out->bar es el indice derivado
 *
 * "Unico" es la palabra que carga el peso. Con un criterio de "el que mide
 * RX550_MMIO_LEN" sin exigir unicidad, un segundo BAR de la misma longitud
 * pasaria y el codigo elegiria el primero que encontrara, que es el orden de la
 * tabla y no una propiedad del hardware.
 *
 * NO llama al kernel y NO necesita el kernel: recibe la tabla ya normalizada, que
 * es lo que hace falta para poder probarla en userspace. Ver el bloque de arriba
 * para las tres fuentes de por que el criterio es el que es.
 */
int rx550_mmio_deriva(const struct rx550_bar_desc *bars, unsigned n,
		      struct rx550_mmio_info *out);

/*
 * Decide si el BAR de registros puede mapearse, a partir de lo que el core de
 * PCI ya normalizo. No llama a pci_iomap ni depende de el: recibe el indice y
 * la longitud y responde, que es lo que se puede probar sin hardware.
 *
 * 2026-10-03: ya NO rechaza un indice distinto de una constante. Comprobar que
 * el indice sea "el que dijo el header" era una forma de no comprobar nada: la
 * unica fuente de la comparacion era la propia constante que se queria validar.
 * Ahora el indice llega derivado, y esta funcion comprueba lo que si es
 * comprobable aqui: que la longitud sea exactamente la de la ventana.
 */
int rx550_mmio_valida(__u8 bar, __u32 len, struct rx550_mmio_info *out);

/*
 * Un offset cae dentro de la ventana abierta. Es la comprobacion que
 *_findings/180_ hace posible: los offsets se verifican contra el ASIC, pero
 * que quepan en la ventana es una propiedad de la ventana.
 */
int rx550_mmio_offset_ok(__u32 offset, __u32 len);

/*
 * Cuantos offsets del driver caen fuera. Existe para que una constante nueva
 * mal puesta sea visible ANTES de que exista hardware: el gate de
 * implementacion pide un contrato, y este es el que dice si el contrato se
 * sostiene con los offsets que hay.
 */
unsigned rx550_mmio_offsetes_fuera(const __u32 *offs, unsigned n, __u32 len);

#endif /* _RX550_MMIO_H_ */

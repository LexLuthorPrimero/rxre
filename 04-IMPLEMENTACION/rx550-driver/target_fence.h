/* SPDX-License-Identifier: GPL-2.0-only */
/*
 * target_fence.h — modelo minimo de fence propio.
 *
 * QUE RESUELVE
 *   Que necesita el primer camino para saber que un trabajo llego a un punto
 *   observable.  Sin esto no hay forma de distinguir "no ejecutado" de
 *   "ejecutado pero no observado".
 *
 * LAS TRES COSAS QUE ESTE ARCHIVO MANTIENE SEPARADAS
 *
 *   1. GPU completion state   lo que la GPU escribe cuando llega al punto
 *   2. CPU observation        lo que la CPU lee de ese estado
 *   3. fence object           la estructura de software que une ambos
 *
 *   Un fence no es la señal: es la estructura que la contiene.  Confundirlas
 *   lleva a "el fence señalizó" cuando lo único que se observó fue un número.
 *
 * EVIDENCIA QUE YA TENEMOS (P-8, cerrado; no se reabre)
 *   El escritor del fence es el procesador de comandos, por dos caminos:
 *     PACKET3_RELEASE_MEM        (compute)
 *     PACKET3_EVENT_WRITE_EOP    (GFX)
 *   INT_SEL(2) = "interrupt when data write is confirmed"
 *                (vid.h:250-261)
 *   Consecuencia de arquitectura: la señalizacion del fence va por la cadena de
 *   confirmacion de escritura.  Por eso un fence señalizado NO es prueba
 *   automatica de que el efecto de un packet arbitrario se haya consumado: es
 *   prueba de que la escritura del fence fue confirmada.
 *
 * LO QUE ESTE MODELO NO ES
 *   No es dma_fence.  No es una kernel_fence.  No reimplementa el scheduler.
 *   Que el primer camino necesite o no dma_fence es una decision de
 *   integracion con base de evidencia, no de este modelo.  Aqui hay un tipo de
 *   fence propio y minimo, y la decision queda registrada abajo.
 *
 * MONOTONICIDAD Y WRAPAROUND
 *   Un numero de secuencia que envuelve no puede compararse con <.  Un fence
 *   envuelto invalida un fence anterior no envuelto, y eso hay que
 *   representarlo.  Aqui el secuencia es de 64 bits y el wrap se declara
 *   imposible de observar en el primer camino porque un solo fence esta
 *   vivo a la vez; se deja la regla escrita, no la suposicion.
 */
#ifndef TARGET_FENCE_H
#define TARGET_FENCE_H

enum target_fence_state {
	TFM_FENCE_ABSENT	= 0,	/* slot vacio                        */
	TFM_FENCE_CREATED	= 1,	/* objeto exista, sin publicar       */
	TFM_FENCE_PUBLISHED	= 2,	/* secuencia visibles para la GPU     */
	TFM_FENCE_SIGNALLED	= 3,	/* CPU observa la escritura          */
	TFM_FENCE_TIMED_OUT	= 4,	/* la CPU dejo de esperar             */
	TFM_FENCE_ERROR		= 5,	/* fallo observado o error de estado */
	TFM_FENCE_RETIRED	= 6,	/* liberado                          */
};

/* Como se produce la senal.  El camino, no la suposicion. */
enum target_fence_path {
	TFM_PATH_NONE		= 0,
	TFM_PATH_RELEASE_MEM	= 1,	/* PACKET3_RELEASE_MEM   (compute) */
	TFM_PATH_EVENT_WRITE_EOP= 2,	/* PACKET3_EVENT_WRITE_EOP (GFX)   */
};

struct target_fence {
	unsigned char	state;
	unsigned char	path;		/* enum target_fence_path           */
	unsigned int	seq;		/* secuencia de 32 bits publicada   */
	unsigned int	observed;	/* secuencia que la CPU vio         */
	unsigned int	timeout_ms;
	int		refcount;
};

/*
 * La secuencia se compara con ESA-comparacion, no con <.  Un numero de 32
 * bits que envuelve rompe el orden naive; esta regla lo declara en vez de
 * dejar que cada consumidor lo reimplemente mal.
 */
static inline int tfm_seq_after(unsigned int a, unsigned int b)
{
	return (int)((a - b) & 0xFFFFFFFFu) > 0;
}

static inline void tfm_init(struct target_fence *f)
{
	f->state = TFM_FENCE_ABSENT;
	f->path = TFM_PATH_NONE;
	f->seq = 0;
	f->observed = 0;
	f->timeout_ms = 0;
	f->refcount = 0;
}

/*
 * Crear: fija el camino de senalizacion de forma explicita.
 *
 * Exige un camino conocido.  Un fence sin camino declarado no podria
 * distinguirse de un fence que nunca va a senalizar, y esa es exactamente la
 * confusion que el modelo existe para evitar.
 */
static inline int tfm_create(struct target_fence *f, enum target_fence_path path,
			     unsigned int timeout_ms)
{
	if (f->state != TFM_FENCE_ABSENT)
		return 0;
	if (path != TFM_PATH_RELEASE_MEM && path != TFM_PATH_EVENT_WRITE_EOP)
		return 0;
	if (timeout_ms == 0)
		return 0;

	f->path = path;
	f->timeout_ms = timeout_ms;
	f->state = TFM_FENCE_CREATED;
	return 1;
}

/* Publicar la secuencia: la GPU va a escribir este valor. */
static inline int tfm_publish(struct target_fence *f, unsigned int seq)
{
	if (f->state != TFM_FENCE_CREATED)
		return 0;
	f->seq = seq;
	f->state = TFM_FENCE_PUBLISHED;
	return 1;
}

/*
 * La CPU observa la escritura de la secuencia.
 *
 * Publicar el mismo valor dos veces se rechaza: la segunda senalizacion no
 * aporta nada y aceptarla ocultaria un error de contabilidad.
 */
static inline int tfm_observe(struct target_fence *f, unsigned int seq)
{
	if (f->state != TFM_FENCE_PUBLISHED)
		return 0;
	if (seq != f->seq)
		return 0;
	f->observed = seq;
	f->state = TFM_FENCE_SIGNALLED;
	return 1;
}

/* El timeout se aplica sobre un fence publicado y no senalizado. */
static inline int tfm_timeout(struct target_fence *f)
{
	if (f->state != TFM_FENCE_PUBLISHED)
		return 0;
	f->state = TFM_FENCE_TIMED_OUT;
	return 1;
}

static inline int tfm_error(struct target_fence *f)
{
	if (f->state != TFM_FENCE_CREATED && f->state != TFM_FENCE_PUBLISHED)
		return 0;
	f->state = TFM_FENCE_ERROR;
	return 1;
}

static inline int tfm_get(struct target_fence *f)
{
	if (f->state == TFM_FENCE_ABSENT || f->state == TFM_FENCE_RETIRED)
		return 0;
	f->refcount++;
	return 1;
}

static inline int tfm_put(struct target_fence *f)
{
	if (f->refcount == 0)
		return 0;
	f->refcount--;
	return 1;
}

static inline int tfm_retire(struct target_fence *f)
{
	if (f->state != TFM_FENCE_SIGNALLED && f->state != TFM_FENCE_TIMED_OUT &&
	    f->state != TFM_FENCE_ERROR)
		return 0;
	if (f->refcount != 0)
		return 0;
	f->state = TFM_FENCE_RETIRED;
	return 1;
}

static inline int tfm_settled(const struct target_fence *f)
{
	return f->state == TFM_FENCE_SIGNALLED || f->state == TFM_FENCE_TIMED_OUT ||
	       f->state == TFM_FENCE_ERROR;
}

/*
 * REGLA QUE NO SE ROMPE
 *
 *   FENCE_SIGNALLED  =>  la escritura de la secuencia fue confirmada
 *   FENCE_SIGNALLED  !=>  el contenido de lo que la GPU escribio es correcto
 *
 *   Un fence señalizado prueba que hubo confirmacion de escritura.  No prueba
 *   que un packet arbitrario se haya ejecutado con efecto, ni que la memoria
 *   destino tenga el valor esperado.  Eso lo demuestra el LECTOR del destino,
 *   no el fence.  Confundirlo es el error que este archivo previene.
 */

#endif /* TARGET_FENCE_H */

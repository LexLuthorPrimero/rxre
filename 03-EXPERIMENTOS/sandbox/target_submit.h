/* SPDX-License-Identifier: GPL-2.0-only */
/*
 * target_submit.h — contrato minimo de submission.
 *
 * QUE RESUELVE
 *   Que se necesita para enviar un IB al ring del GFX y saber, sin exagerar,
 *   hasta donde se llego.
 *
 * LA REGLA QUE EL TIPO HACE ESTRUCTURAL
 *
 *   Esta maquina de estados termina en COMPLETED.  EJECUCION NO ES UN ESTADO
 *   DE ESTA MAQUINA.
 *
 *   Se prueba lo siguiente, que es lo que se ha cerrado hasta ahora:
 *
 *     PUBLISHED   la CPU escribio el WPTR y la puerta                WPTR
 *     CONSUMED    el hardware avanzo el puntero de lectura           RPTR
 *     COMPLETED   la CPU observo la escritura del fence              fence
 *
 *   Y NO se prueba de ninguna de las tres:
 *
 *     que el IB se ejecutara con efecto
 *     que un packet concreto hiciera lo que se espera
 *     que la memoria destino tenga el valor esperado
 *
 *   Eso lo demuestra una LECTURA INDEPENDIENTE del destino, y por eso el
 *   modelo ofrece una funcion aparte que exige esa lectura.  No se puede
 *   "llegar" a ejecucion por una transicion de esta maquina, porque no hay
 *   ninguna transicion que lleve ahi.  Es la forma de que la regla sobreviva
 *   a que alguien lea el codigo con prisa.
 *
 * QUE ES UN OBSERVABLE, Y QUE NO
 *   WPTR  lo que la CPU publico.        Demuestra que se publico.
 *   RPTR  lo que el hardware avanzo.    Demuestra que se consumio.
 *   fence la escritura confirmada.       Demuestra que llego al fence.
 *   destino  lo que la GPU escribio.    Demuestra el EFECTO.
 *   Los tres primeros no son el cuarto.  Ninguno lo implica.
 *
 * LO QUE ESTE CONTRATO NO ES
 *   No es el scheduler.  No es IB memory (eso es Q12).  No es PM4 (Q15).
 *   No es el ring allocator.  Solo la transicion de una unidad de trabajo.
 */
#ifndef TARGET_SUBMIT_H
#define TARGET_SUBMIT_H

enum target_submit_state {
	TSE_ABSENT		= 0,
	TSE_CREATED		= 1,	/* objeto existe, IB definido        */
	TSE_READY		= 2,	/* IB codificado, memoria traduction */
	TSE_PUBLISHED		= 3,	/* WPTR publicado, doorbell escrito  */
	TSE_CONSUMED		= 4,	/* RPTR avanzo                       */
	TSE_COMPLETED		= 5,	/* fence observado                   */
	TSE_RETIRED		= 6,	/* liberado                          */
	TSE_ERROR		= 7,	/* fallo de un estado anterior       */
};

/* De donde salio cada transicion.  Para poder auditarla despues. */
enum target_submit_evidence {
	TSE_EV_NONE		= 0,
	TSE_EV_WPTR		= 1,	/* la CPU publico el WPTR            */
	TSE_EV_DOORBELL		= 2,	/* se escribio la puerta             */
	TSE_EV_RPTR		= 3,	/* el hardware avanzo el RPTR         */
	TSE_EV_FENCE		= 4,	/* la CPU observo el fence           */
};

struct target_submit {
	unsigned char	state;
	unsigned char	evidence;	/* enum target_submit_evidence       */
	unsigned int	wptr;		/* lo que la CPU publico            */
	unsigned int	rptr_seen;	/* lo que se observo en el RPTR     */
	unsigned int	seq;		/* secuencia del fence asociado     */
	unsigned char	doorbell_suppressed;	/* la intervencion estaba activa  */
	int		refcount;
};

static inline void tse_init(struct target_submit *s)
{
	s->state = TSE_ABSENT;
	s->evidence = TSE_EV_NONE;
	s->wptr = 0;
	s->rptr_seen = 0;
	s->seq = 0;
	s->doorbell_suppressed = 0;
	s->refcount = 0;
}

/*
 * CREATED: el objeto existe y su IB esta definido.
 *
 * wptr es el valor que la CPU va a publicar.  Se fija aqui para que la
 * transicion a PUBLISHED no pueda cambiarlo sobre la marcha.
 */
static inline int tse_create(struct target_submit *s, unsigned int wptr)
{
	if (s->state != TSE_ABSENT || wptr == 0)
		return 0;
	s->wptr = wptr;
	s->state = TSE_CREATED;
	s->evidence = TSE_EV_NONE;
	return 1;
}

/* READY: IB codificado y su memoria ya es traducible por la GPU. */
static inline int tse_ready(struct target_submit *s)
{
	if (s->state != TSE_CREATED)
		return 0;
	s->state = TSE_READY;
	return 1;
}

/*
 * PUBLISHED: WPTR publicado Y puerta escrita.
 *
 * Se exige el WPTR.  La puerta puede no haberse escrito si la intervencion
 * del componente EP08 esta activa: por eso es un campo, no una precondicion
 * ignorada.  Publicar con la puerta suprimida es un estado VALIDO y
 * justamente el que el experimento de EP08 quiere alcanzar.
 */
static inline int tse_publish(struct target_submit *s, unsigned int wptr_published,
			       int doorbell_written)
{
	if (s->state != TSE_READY)
		return 0;
	if (wptr_published != s->wptr)
		return 0;	/* el WPTR no puede cambiar al publicar */
	s->wptr = wptr_published;
	s->doorbell_suppressed = (unsigned char)(doorbell_written ? 0 : 1);
	s->state = TSE_PUBLISHED;
	s->evidence = doorbell_written ? TSE_EV_DOORBELL : TSE_EV_WPTR;
	return 1;
}

/*
 * CONSUMED: el RPTR avanzo.
 *
 * Solo avanza si ya estaba publicado.  Un RPTR que se mueve sin WPTR
 * publicado no es consumo de ESTA unidad de trabajo.
 */
static inline int tse_consume(struct target_submit *s, unsigned int rptr)
{
	if (s->state != TSE_PUBLISHED)
		return 0;
	s->rptr_seen = rptr;
	s->state = TSE_CONSUMED;
	s->evidence = TSE_EV_RPTR;
	return 1;
}

/*
 * COMPLETED: la CPU observo el fence.
 *
 * Solo desde CONSUMED: un fence sin consumo previo no demuestra nada sobre
 * esta unidad, y aceptarlo abriria la puerta a "el fence senalizo" como
 * sinonimo de "el trabajo ocurrio".
 */
static inline int tse_complete(struct target_submit *s, unsigned int seq)
{
	if (s->state != TSE_CONSUMED)
		return 0;
	if (seq == 0)
		return 0;
	s->seq = seq;
	s->state = TSE_COMPLETED;
	s->evidence = TSE_EV_FENCE;
	return 1;
}

/*
 * tse_effect_observed — LA PRUEBA DE EJECUCION, y no es una transicion.
 *
 * Exige un valor LEIDO del destino.  No se puede alcanzar con un WPTR, ni
 * con un RPTR, ni con un fence: la firma lo hace explicito.
 *
 * Devuelve 1 solo si el valor leido coincide con el esperado.  Devolver 0
 * significa "no demostrado", nunca "no ocurrio": la lectura pudo fallar.
 */
static inline int tse_effect_observed(const struct target_submit *s,
				      unsigned long long value_read,
				      unsigned long long value_expected)
{
	if (s->state != TSE_COMPLETED)
		return 0;
	return value_read == value_expected;
}

static inline int tse_get(struct target_submit *s)
{
	if (s->state == TSE_ABSENT || s->state == TSE_RETIRED ||
	    s->state == TSE_ERROR)
		return 0;
	s->refcount++;
	return 1;
}

static inline int tse_put(struct target_submit *s)
{
	if (s->refcount == 0)
		return 0;
	s->refcount--;
	return 1;
}

static inline int tse_retire(struct target_submit *s)
{
	if (s->state != TSE_COMPLETED && s->state != TSE_ERROR)
		return 0;
	if (s->refcount != 0)
		return 0;
	s->state = TSE_RETIRED;
	return 1;
}

static inline int tse_error(struct target_submit *s)
{
	if (s->state == TSE_ABSENT || s->state == TSE_RETIRED ||
	    s->state == TSE_ERROR)
		return 0;
	s->state = TSE_ERROR;
	return 1;
}

/* Lo que esta máquina SÍ demuestra, y lo que NO. */
static inline int tse_proves(const struct target_submit *s)
{
	switch (s->state) {
	case TSE_PUBLISHED:	return 1;	/* que se publico        */
	case TSE_CONSUMED:	return 2;	/* que se consumio       */
	case TSE_COMPLETED:	return 3;	/* que llego al fence    */
	default:		return 0;
	}
}

#endif /* TARGET_SUBMIT_H */

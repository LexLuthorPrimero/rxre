/*
 * fence_corpus.c — corpus SINTETICO congelado para semref.
 *
 * NO contiene codigo del kernel. Reproduce la TOPOLOGIA de llamadas medida en
 * linux-7.1.3, drivers/gpu/drm/amd/amdgpu/, para que semref pueda testearse de
 * forma determinista sin depender de un arbol de ~400 ficheros ni de una copia
 * del kernel. La procedencia de cada topologia esta en el README de este
 * directorio; aqui solo se conserva la FORMA, no el contenido.
 *
 * Topologias representadas (medidas, no inventadas):
 *   fence_process                      1 def, 3 calls   == amdgpu_fence_process
 *   schedule_fallback                  1 def, 2 calls   == amdgpu_fence_schedule_fallback
 *   fence_driver_force_completion      1 def, 1 call    == idem, unico caller = hw_fini
 *   mod_timer                          0 def, 1 call    == idem
 *   dma_fence_signal                   0 def, 4 calls   == idem (1 en fence, 3 en job)
 *   <simbolo inexistente>              SIN-MATCH        == control negativo
 *
 * El prototipo de dma_fence_signal vive en drm_fence.h, no aqui, para reproducir
 * la topologia real y para que el contraste con grep siga discriminando.
 */

#include "drm_fence.h"

struct drm_fence {
	int signaled;
};

struct amdgpu_ring {
	struct drm_fence fence_drv;
	int id;
};

struct timer_list {
	struct amdgpu_ring *ring;
};

/*
 * REGRESION R-1: orden alfabetico frente a orden por linea.
 *
 * zzz_helper se ordena DESPUES que fence_process, pero se define ANTES.
 * Un resolvedor que elija "la ultima definicion vista en el indice" —que esta
 * ordenado por nombre— devolveria zzz_helper para una llamada situada dentro
 * de fence_process. El correcto es fence_process, el de mayor linea <= L.
 */
static struct drm_fence *zzz_helper(struct drm_fence *f)
{
	return f;
}

void fence_process(struct amdgpu_ring *ring)		/* DEFINICION */
{
	zzz_helper(&ring->fence_drv);
	ring->fence_drv.signaled = 1;
	dma_fence_signal(&ring->fence_drv);
}

/* --- los tres callers de fence_process, ninguno en contexto de IRQ ------- */

static void fence_fallback(struct timer_list *t)		/* caller 1: timer */
{
	fence_process(t->ring);
}

void fence_driver_force_completion(struct amdgpu_ring *ring)	/* caller 2: teardown */
{
	fence_process(ring);
}

void debugfs_fence_info_show(struct amdgpu_ring *ring)	/* caller 3: debugfs */
{
	fence_process(ring);
}

/* --- schedule_fallback: armado inicial + rearmado ------------------------ */

void schedule_fallback(struct amdgpu_ring *ring)		/* DEFINICION */
{
	mod_timer(&ring->fence_drv, 100);
}

bool fence_enable_signaling(struct amdgpu_ring *ring)	/* caller 1: fuera de IRQ */
{
	schedule_fallback(ring);
	return true;
}

static bool fence_process_rearm(struct amdgpu_ring *ring)	/* caller 2: rearmado */
{
	schedule_fallback(ring);
	return true;
}

/* --- CASO F: el unico caller de force_completion es el teardown de HW ---- */

void fence_driver_hw_fini(struct amdgpu_ring *ring)
{
	if (ring->id)
		fence_driver_force_completion(ring);
}

/* --- senal externo: 0 definiciones locales, 4 llamadas -------------------- */

void job_stop_all_jobs_on_sched(struct amdgpu_ring *ring)
{
	dma_fence_signal(&ring->fence_drv);
	dma_fence_signal(&ring->fence_drv);
	dma_fence_signal(&ring->fence_drv);
}

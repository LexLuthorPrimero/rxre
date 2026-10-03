/*
 * drm_fence.h — prototipo externo del corpus congelado.
 *
 * Existe para reproducir la topologia real: en linux-7.1.3, dma_fence_signal
 * se DECLARA en include/drm/drm_fence.h y no aparece prototipo en ningun .c.
 * Eso mantiene coherente el contraste con `grep`, que cuenta apariciones
 * textuales: si el prototipo estuviera en el .c, grep devolveria 5 frente a las
 * 4 llamadas reales y el contraste dejaria de discriminar. Ver README.md.
 */

struct drm_fence;

void dma_fence_signal(struct drm_fence *f);

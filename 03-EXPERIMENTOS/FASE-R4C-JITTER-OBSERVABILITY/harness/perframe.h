#ifndef PERFRAME_H
#define PERFRAME_H

#include <stdint.h>

/* Identificador que la capa busca en el UBO para auto-identificarlo (bytes 16..19). */
#define PERFRAME_MAGIC 0x4A495443u /* "JITC" */

/* Layout del uniform per-frame (host-visible) compartido entre app y layer.
   Debe coincidir con el mapeo del shader para el primer vec4 (color). */
typedef struct {
  float    color[4];     /* bytes 0..15  (leido por el fragment shader) */
  uint32_t magic;        /* bytes 16..19 (PERFRAME_MAGIC) */
  uint32_t frameMarker;  /* bytes 20..23 (indice global de frame) */
  float    viewport[2];  /* bytes 24..31 (W, H en px) */
  float    projBase[16]; /* bytes 32..95  (proyeccion sin jitter, column-major) */
  float    projJit[16];  /* bytes 96..159 (proyeccion jittered, column-major) */
} PerFrame;

/* Canal NIVEL A: push constants (16 bytes). */
typedef struct {
  uint32_t frameMarker; /* bytes 0..3   */
  float    jitterX;     /* bytes 4..7   (px) */
  float    jitterY;     /* bytes 8..11  (px) */
  float    pad;         /* bytes 12..15 */
} PushPayload;

/* --- algebra de matrices 4x4 (column-major, vectores columna, estilo GLM/Vulkan)
   Construccion FSR2: M_jit = translate(jx_ndc, jy_ndc, 0) * M_base           */
void perframe_mat4_mul(const float A[16], const float B[16], float C[16]);
void perframe_mat4_translate(float x, float y, float z, float T[16]);
int  perframe_mat4_invert(const float M[16], float out[16]);

/* Reconstruye el jitter en px (NIVEL B) a partir de la base y la jittered:
   jx_px = T[12]*W/2 ; jy_px = -T[13]*H/2, con T = M_jit * inv(M_base). */
void perframe_recover_jitter(const float projBase[16], const float projJit[16],
                             float W, float H, float *jx_px, float *jy_px);

#endif
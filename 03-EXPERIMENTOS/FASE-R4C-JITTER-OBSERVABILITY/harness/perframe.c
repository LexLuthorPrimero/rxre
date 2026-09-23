#include "perframe.h"

#include <math.h>
#include <string.h>

void perframe_mat4_mul(const float A[16], const float B[16], float C[16]) {
  double T[16] = {0};
  for (int c = 0; c < 4; c++)
    for (int r = 0; r < 4; r++) {
      double acc = 0.0;
      for (int k = 0; k < 4; k++)
        acc += (double)A[k * 4 + r] * (double)B[c * 4 + k];
      T[c * 4 + r] = acc;
    }
  for (int i = 0; i < 16; i++) C[i] = (float)T[i];
}

void perframe_mat4_translate(float x, float y, float z, float T[16]) {
  memset(T, 0, 16 * sizeof(float));
  T[0] = T[5] = T[10] = T[15] = 1.0f;
  T[12] = x;
  T[13] = y;
  T[14] = z;
}

/* Inversion general 4x4 por Gauss-Jordan (precision doble). Retorna 0 si singular. */
int perframe_mat4_invert(const float M[16], float out[16]) {
  double a[4][4], b[4][4];
  for (int r = 0; r < 4; r++)
    for (int c = 0; c < 4; c++) {
      a[r][c] = (double)M[c * 4 + r];
      b[r][c] = (r == c) ? 1.0 : 0.0;
    }
  for (int col = 0; col < 4; col++) {
    int pivot = col;
    for (int r = col + 1; r < 4; r++)
      if (fabs(a[r][col]) > fabs(a[pivot][col])) pivot = r;
    if (fabs(a[pivot][col]) < 1e-30) return 0;
    if (pivot != col)
      for (int c2 = 0; c2 < 4; c2++) {
        double ta = a[pivot][c2];
        a[pivot][c2] = a[col][c2];
        a[col][c2] = ta;
        double tb = b[pivot][c2];
        b[pivot][c2] = b[col][c2];
        b[col][c2] = tb;
      }
    double d = a[col][col];
    for (int c2 = 0; c2 < 4; c2++) {
      a[col][c2] /= d;
      b[col][c2] /= d;
    }
    for (int r = 0; r < 4; r++) {
      if (r == col) continue;
      double f = a[r][col];
      if (f == 0.0) continue;
      for (int c2 = 0; c2 < 4; c2++) {
        a[r][c2] -= f * a[col][c2];
        b[r][c2] -= f * b[col][c2];
      }
    }
  }
  for (int r = 0; r < 4; r++)
    for (int c = 0; c < 4; c++) out[c * 4 + r] = (float)b[r][c];
  return 1;
}

void perframe_recover_jitter(const float projBase[16], const float projJit[16],
                             float W, float H, float *jx_px, float *jy_px) {
  float invBase[16], T[16];
  if (!perframe_mat4_invert(projBase, invBase)) {
    *jx_px = NAN;
    *jy_px = NAN;
    return;
  }
  perframe_mat4_mul(projJit, invBase, T); /* T = M_jit * inv(M_base) */
  /* La columna 3 de T (column-major, elementos T[12],T[13]) es la traduccion NDC. */
  float tx = T[12];
  float ty = T[13];
  *jx_px = tx * W / 2.0f;
  *jy_px = -ty * H / 2.0f;
}
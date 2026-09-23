#include "jittergen.h"

#include <math.h>
#include <stdio.h>
#include <stdlib.h>

static float halton(int i, int base) {
  float f = 1.0f, r = 0.0f;
  int b = base;
  while (i > 0) {
    f /= (float)b;
    r += f * (float)(i % b);
    i /= b;
  }
  return r;
}

static uint64_t xorshift64(uint64_t *s) {
  uint64_t x = *s;
  x ^= x << 13;
  x ^= x >> 7;
  x ^= x << 17;
  *s = x;
  return x;
}

static float rnd_uni(uint64_t *s) { /* [-0.5, 0.5) */
  uint64_t bits = xorshift64(s);
  return (float)(((double)(bits & 0xFFFFFFFFu)) / 4294967296.0) - 0.5f;
}

int jitter_generate(JitterSeq *seq, uint64_t seed) {
  static const float mags[JG_MAG] = {0.5f, 0.25f, 0.125f, 0.0625f, 0.01f};
  static const int   dirs[JG_DIR][2] = {
      {+1, 0}, {-1, 0}, {0, +1}, {0, -1}, {+1, +1}, {-1, +1}, {+1, -1}, {-1, -1}};

  seq->n = JG_TOTAL;
  seq->jx = (float *)calloc((size_t)JG_TOTAL, sizeof(float));
  seq->jy = (float *)calloc((size_t)JG_TOTAL, sizeof(float));
  seq->prelude = (int *)calloc((size_t)JG_TOTAL, sizeof(int));
  if (!seq->jx || !seq->jy || !seq->prelude) {
    jitter_free(seq);
    return -1;
  }

  int idx = 0;

  /* Preludio (4 frames deterministas, excluidos de metricas). */
  static const float pre[JG_PRELUDE][2] = {
      {0.25f, 0.0f}, {-0.25f, 0.0f}, {0.0f, 0.25f}, {0.0f, -0.25f}};
  for (int i = 0; i < JG_PRELUDE; i++) {
    seq->jx[idx] = pre[i][0];
    seq->jy[idx] = pre[i][1];
    seq->prelude[idx] = 1;
    idx++;
  }

  /* Bloque A: 5 magnitudes x 8 direcciones, repetido 6x (240). */
  for (int rep = 0; rep < JG_REP_A; rep++)
    for (int m = 0; m < JG_MAG; m++)
      for (int d = 0; d < JG_DIR; d++) {
        seq->jx[idx] = mags[m] * (float)dirs[d][0];
        seq->jy[idx] = mags[m] * (float)dirs[d][1];
        idx++;
      }

  /* Bloque B: Halton[2,3] en [-0.5,0.5], i=1..8 (evita (0,0)), repetido 2x (16). */
  for (int rep = 0; rep < JG_REP_B; rep++)
    for (int i = 1; i <= JG_HALTON; i++) {
      seq->jx[idx] = halton(i, 2) - 0.5f;
      seq->jy[idx] = halton(i, 3) - 0.5f;
      idx++;
    }

  /* Bloque C: pseudo-random xorshift determinista en [-0.5,0.5) (64). */
  uint64_t state = seed ? seed : 0x5EED0000u;
  for (int i = 0; i < JG_RAND; i++) {
    seq->jx[idx] = rnd_uni(&state);
    seq->jy[idx] = rnd_uni(&state);
    idx++;
  }

  /* (0,0) nunca se inyecta por diseno (regla FSR2): verificar. */
  for (int i = 0; i < JG_TOTAL; i++)
    if (seq->jx[i] == 0.0f && seq->jy[i] == 0.0f) {
      seq->jx[i] = 0.01f; /* safeguard, no deberia ocurrir con los bloques */
      seq->jy[i] = 0.0f;
    }

  return 0;
}

void jitter_free(JitterSeq *seq) {
  free(seq->jx);
  free(seq->jy);
  free(seq->prelude);
  seq->jx = NULL;
  seq->jy = NULL;
  seq->prelude = NULL;
  seq->n = 0;
}

int jitter_write_gt(const JitterSeq *seq, uint64_t seed, const char *path) {
  FILE *f = fopen(path, "w");
  if (!f) return -1;
  fprintf(f, "{\n");
  fprintf(f, "  \"sequence\": \"blockA(x5mags x8dir x6rep=240) + halton23(x2=16) + xorshift(64)\",\n");
  fprintf(f, "  \"prelude\": %d,\n", JG_PRELUDE);
  fprintf(f, "  \"measured\": %d,\n", JG_MEASURED);
  fprintf(f, "  \"total\": %d,\n", JG_TOTAL);
  fprintf(f, "  \"seed\": %llu,\n", (unsigned long long)seed);
  fprintf(f, "  \"frames\": [\n");
  for (int i = 0; i < seq->n; i++) {
    fprintf(f, "    {\"frame\": %d, \"prelude\": %d, \"jx\": %.9f, \"jy\": %.9f}%s\n",
            i, seq->prelude[i], (double)seq->jx[i], (double)seq->jy[i],
            (i < seq->n - 1) ? "," : "");
  }
  fprintf(f, "  ]\n}\n");
  fclose(f);
  return 0;
}
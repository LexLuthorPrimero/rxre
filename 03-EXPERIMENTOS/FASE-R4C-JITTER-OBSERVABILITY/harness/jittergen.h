#ifndef JITTERGEN_H
#define JITTERGEN_H

#include <stdint.h>

#define JG_PRELUDE 4          /* frames de calentamiento, excluidos de metricas */
#define JG_MAG      5         /* magnitudes */
#define JG_DIR      8         /* direcciones */
#define JG_BLOCK_A  (JG_MAG*JG_DIR)      /* 40 */
#define JG_REP_A    6                       /* 240 */
#define JG_HALTON   8                       /* muestras Halton por bloque */
#define JG_REP_B    2                       /* 16 */
#define JG_RAND     64                      /* 64 */
#define JG_MEASURED (JG_BLOCK_A*JG_REP_A + JG_HALTON*JG_REP_B + JG_RAND)  /* 320 */
#define JG_TOTAL    (JG_PRELUDE + JG_MEASURED)  /* 324 */

typedef struct {
  int    n;            /* JG_TOTAL */
  float *jx;           /* px */
  float *jy;           /* px */
  int   *prelude;      /* 1 si frame de calentamiento */
} JitterSeq;

/* Genera la secuencia completa determinista (seed fija por defecto).
   Devuelve 0 en exito, -1 en fallo de memoria. */
int jitter_generate(JitterSeq *seq, uint64_t seed);
void jitter_free(JitterSeq *seq);

/* Escribe la ground-truth en JSON (always + sfios). Devuelve 0 en exito. */
int jitter_write_gt(const JitterSeq *seq, uint64_t seed, const char *path);

#endif
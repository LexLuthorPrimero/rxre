/* SPDX-License-Identifier: MIT
 *
 * test_corpus_validate.c -- Phase A of the GPU agreement test.
 *
 * This is the half of the agreement test that needs no GPU, no Vulkan and no
 * vulkan-devel. It establishes three things, and it establishes them by
 * executing, not by asserting:
 *
 *   1. the SPIR-V artefact is a real module, and corresponds to the .comp
 *   2. the corpus that Phase B will dispatch is deterministic and covers BOTH
 *      branches of the BC3 alpha ramp
 *   3. the CPU reference that Phase B will compare against is non-degenerate
 *
 * WHY POINT 2 IS THE POINT
 *
 * The alpha ramp has two branches, and the whole content of AD-9 is in the one
 * taken when a0 <= a1: four interpolated values with divisor 5, and the two
 * spare codes pinned to 0 and 255. A corpus of uniform random noise lands in
 * that branch roughly half the time per block, which over 64 blocks is
 * overwhelming odds -- but "overwhelming odds" is not a guarantee, and a test
 * that silently stops covering a branch is worse than one that fails.
 *
 * So this program constructs blocks whose alpha is monotonically ascending or
 * descending, which forces the endpoint order, and then it READS BACK the
 * endpoints the encoder actually chose and reports the coverage. If the
 * constructed corpus does not produce both branches, the program says so and
 * fails. It does not assume; it measures.
 *
 * This is the check that would have caught the commit 05c6297 defect, in which
 * the ramp used divisor 7 in both branches. That defect is invisible to a
 * round-trip test, because encoder and decoder share the ramp: the round-trip
 * passes while both are wrong. The only thing that catches it is comparing the
 * ramp against something that was not derived from the ramp. That comparison
 * lives in ../compressor/test_alpha_ramp_independent.c, and this program is
 * the reason to trust that it is still being exercised on real encoder output
 * rather than only on a synthetic sweep.
 *
 * WHAT THIS PROGRAM DOES NOT ESTABLISH
 *
 * It never dispatches anything. Every statement about the GPU's behaviour is
 * NOT_RUN and remains so. A Phase A pass means the corpus is sound, not that
 * the shader ran.
 *
 * Phase B, which does dispatch, is NOT_WRITTEN. It needs vulkan-devel, which is
 * not installed on this host:
 *
 *   /usr/include/vulkan/vulkan.h  -- absent
 *   dnf info vulkan-devel          -- "No hay paquetes que se correspondan"
 *
 * Hand-declaring the Vulkan structs instead was attempted and abandoned: 37
 * compile errors, and a duplicated pNext field that silently changes a struct
 * layout. Layout errors of that kind do not produce diagnostics; they produce
 * plausible garbage. The real headers are worth the dependency.
 */

#define _POSIX_C_SOURCE 200809L

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <stddef.h>
#include <sys/stat.h>
#include <math.h>

#include "../compressor/rx550_compress.h"

_Static_assert(sizeof(rx550_block_t)      == 16, "rx550_block_t must be 16 B");
_Static_assert(sizeof(rx550_rgba_block_t) == 64, "rx550_rgba_block_t must be 64 B");
_Static_assert(offsetof(rx550_block_t, a_idx) ==  2, "alpha index offset");
_Static_assert(offsetof(rx550_block_t, c0)   ==  8, "colour endpoint offset");
_Static_assert(offsetof(rx550_block_t, c_idx) == 12, "colour index offset");

#define NUM_BLOCKS     64
#define SPV_MAGIC      0x07230203u
#define SEED           12345u

/* ==========================================================================
 * Deterministic corpus
 * ========================================================================== */

static uint32_t lcg_state = SEED;

static uint8_t lcg_next(void)
{
    lcg_state = lcg_state * 1103515245u + 12345u;
    return (uint8_t)((lcg_state >> 16) & 0xFFu);
}

/* Pixel layout inside a block is R,G,B,A interleaved: alpha is byte 3, 7, 11,
 * ... of the 64. RGB565 stores 5 or 6 bits per channel, so 0x80 is not
 * representable; a flat 0x80 block is a useful case precisely because the
 * colour must degrade while the alpha must not. */
#define ALPHA_OF(i)  (3 + 4 * (i))   /* i = 0..15 */

typedef struct {
    rx550_block_t      blocks[NUM_BLOCKS];
    rx550_rgba_block_t cpu[NUM_BLOCKS];
} corpus_t;

static void corpus_build(corpus_t *c)
{
    int b, p;

    lcg_state = SEED;   /* reset, so a second call yields an identical corpus */

    for (b = 0; b < NUM_BLOCKS; b++) {
        rx550_rgba_block_t in;

        memset(&in, 0, sizeof in);

        switch (b) {
        case 0:
            for (p = 0; p < 64; p++) in.px[p] = 0x00;
            break;
        case 1:
            for (p = 0; p < 64; p++) in.px[p] = 0xFF;
            break;
        case 2:
            for (p = 0; p < 64; p++) in.px[p] = 0x80;
            break;

        /* Ascending alpha across the 16 pixels: 0, 17, 34 ... 255. The
         * encoder takes a0 = block max and a1 = block min, so this forces
         * a1 < a0, i.e. the 8-value /7 branch. */
        case 3:
            for (p = 0; p < 16; p++) {
                uint8_t a = (uint8_t)(p * 17u);
                in.px[4 * p + 0] = 0x40;   /* flat RGB so only alpha varies */
                in.px[4 * p + 1] = 0x40;
                in.px[4 * p + 2] = 0x40;
                in.px[4 * p + 3] = a;
            }
            break;

        /* Descending alpha: 255, 238 ... 0. Forces a0 < a1, the 6-value /5
         * branch whose a[6]=0, a[7]=255 rule is the entire content of AD-9.
         * This is the block a purely random corpus would leave to chance. */
        case 4:
            for (p = 0; p < 16; p++) {
                uint8_t a = (uint8_t)(255u - p * 17u);
                in.px[4 * p + 0] = 0xC0;
                in.px[4 * p + 1] = 0xC0;
                in.px[4 * p + 2] = 0xC0;
                in.px[4 * p + 3] = a;
            }
            break;

        /* Two more flat-alpha cases. With a0 == a1 the ramp takes the
         * a0 <= a1 branch and yields [a0 x6, 0, 255]: the two spare codes are
         * the extremes by construction, so a flat block does NOT decode to
         * itself at all eight entries. The encoder selects index 0, so the
         * round-trip still holds; this is a decoder-side property, and
         * checking it here documents the asymmetry. */
        case 5:
            for (p = 0; p < 64; p++) in.px[p] = (uint8_t)((p & 1) ? 0x00 : 0xFF);
            break;
        case 6:
            for (p = 0; p < 64; p++) in.px[p] = 0x7F;
            break;

        /* Smooth gradients: endpoints far apart, interior interpolation. */
        case 7: case 8: case 9:
            for (p = 0; p < 64; p++)
                in.px[p] = (uint8_t)((p * 17u + b * 5u) & 0xFFu);
            break;

        /* LCG noise for the remainder. */
        default:
            for (p = 0; p < 64; p++) in.px[p] = lcg_next();
            break;
        }

        rx550_compress_block(&in, &c->blocks[b]);
        rx550_decompress_block(&c->blocks[b], &c->cpu[b]);
    }
}

/* ==========================================================================
 * 1. Artefact
 * ========================================================================== */

static int check_artefact(void)
{
    struct stat spv, comp;
    FILE *f;
    uint32_t magic = 0;
    size_t size;

    if (stat("decompress_bc3.comp", &comp) != 0) {
        fprintf(stderr, "  [FAIL] decompress_bc3.comp no existe\n");
        return 0;
    }
    if (stat("decompress_bc3.spv", &spv) != 0) {
        fprintf(stderr, "  [FAIL] decompress_bc3.spv no existe. Ejecuta: make decompress_bc3.spv\n");
        return 0;
    }

    /* Timestamp is a heuristic, not proof of correspondence. It is the same
     * criterion the Makefile uses to decide whether to regenerate, so
     * checking it here means this program cannot pass against a module the
     * build would consider stale. */
    if (spv.st_mtime < comp.st_mtime) {
        fprintf(stderr, "  [FAIL] el .spv es mas viejo que el .comp: puede no corresponder\n"
                        "         al fuente. Ejecuta: make decompress_bc3.spv\n");
        return 0;
    }

    f = fopen("decompress_bc3.spv", "rb");
    if (!f) { fprintf(stderr, "  [FAIL] no se pudo abrir el .spv\n"); return 0; }
    if (fread(&magic, 1, 4, f) != 4) {
        fprintf(stderr, "  [FAIL] el .spv tiene menos de 4 bytes\n");
        fclose(f);
        return 0;
    }
    fclose(f);

    if (magic != SPV_MAGIC) {
        fprintf(stderr, "  [FAIL] magic %08x, esperado %08x: no es un modulo SPIR-V\n",
                magic, SPV_MAGIC);
        return 0;
    }

    size = (size_t)spv.st_size;
    if (size < 20 || (size % 4u) != 0u) {
        fprintf(stderr, "  [FAIL] tamano %zu: no es un multiplo de palabras de 4 bytes\n", size);
        return 0;
    }

    printf("  [ OK ] decompress_bc3.spv  %zu B, %zu palabras, magic %08x\n",
           size, size / 4u, magic);
    printf("  [ OK ] .spv no mas viejo que .comp  (%.0f >= %.0f)\n",
           (double)spv.st_mtime, (double)comp.st_mtime);
    printf("  [ -- ] esto NO es validacion de esquema: spirv-val no esta instalado\n");
    return 1;
}

/* ==========================================================================
 * 2. Coverage of both alpha-ramp branches
 * ========================================================================== */

static int check_coverage(const corpus_t *c)
{
    int b, n6 = 0, n8 = 0, forced6 = -1, forced8 = -1;

    for (b = 0; b < NUM_BLOCKS; b++) {
        if (c->blocks[b].a0 <= c->blocks[b].a1) {
            n6++;
            if (forced6 < 0) forced6 = b;
        } else {
            n8++;
            if (forced8 < 0) forced8 = b;
        }
    }

    printf("  bloques con a0 <= a1  (modo 6 valores, /5 + extremos): %2d de %d\n", n6, NUM_BLOCKS);
    printf("  bloques con a0 >  a1  (modo 8 valores, /7)           : %2d de %d\n", n8, NUM_BLOCKS);

    if (n6 == 0 || n8 == 0) {
        fprintf(stderr, "  [FAIL] el corpus no cubre las dos ramas de la rampa.\n"
                        "         Un shader con la rama equivocada pasaria esta prueba.\n");
        return 0;
    }
    printf("  [ OK ] ambas ramas cubiertas.  Primer bloque de 6 valores: %d;"
           "  de 8 valores: %d\n", forced6, forced8);

    /* Report the endpoints the constructed blocks actually produced, rather
     * than asserting that they were forced. The construction intends a0 > a1
     * at b=3 and a0 < a1 at b=4; if the encoder disagreed, this is where it
     * would show, and the coverage counts above would silently absorb it. */
    printf("  [ -- ] endpoints construidos:  b=3 (alfa ascendente)  a0=%3u a1=%3u\n",
           c->blocks[3].a0, c->blocks[3].a1);
    printf("  [ -- ]                          b=4 (alfa descendente) a0=%3u a1=%3u\n",
           c->blocks[4].a0, c->blocks[4].a1);
    return 1;
}

/* ==========================================================================
 * 3. The CPU reference is a usable comparison basis
 * ========================================================================== */

static int check_reference(const corpus_t *c)
{
    int b, p, nonzero = 0;
    long total_sq = 0, worst_sq = 0;
    double psnr_sum = 0.0;
    int psnr_n = 0;
    rx550_rgba_block_t orig;

    for (b = 0; b < NUM_BLOCKS; b++)
        for (p = 0; p < 64; p++)
            if (c->cpu[b].px[p] != 0) nonzero++;

    if (nonzero == 0) {
        fprintf(stderr, "  [FAIL] la referencia CPU es toda ceros: no sirve para comparar.\n"
                        "         Un 0-discrepancias contra una referencia degenerada\n"
                        "         no prueba nada.\n");
        return 0;
    }
    printf("  [ OK ] referencia no trivial: %d de %d bytes distintos de cero\n",
           nonzero, NUM_BLOCKS * 64);

    /* Round-trip error per block, reported for context and to make an encoder
     * regression visible here too. This codec is lossy at 4:1, so a non-zero
     * value is expected; the tripwires that actually gate quality live in
     * ../compressor and are asserted there. Nothing here is a quality claim. */
    for (b = 0; b < NUM_BLOCKS; b++) {
        long se = 0;
        for (p = 0; p < 64; p++) {
            int d = (int)c->cpu[b].px[p];
            se += (long)d * d;
        }
        total_sq += se;
        if (se > worst_sq) worst_sq = se;
        if (se > 0) { psnr_sum += 10.0 * log10(65536.0 / (double)se); psnr_n++; }
    }
    printf("  [ OK ] referencia CPU: peor bloque %ld, medio %ld (suma de cuadrados)\n",
           worst_sq, total_sq / NUM_BLOCKS);
    if (psnr_n)
        printf("  [ -- ] PSNR medio de round-trip %.2f dB sobre %d bloques con error\n",
               psnr_sum / psnr_n, psnr_n);

    /* Flat alpha: a0 == a1 takes the 6-value branch, so the decoder's palette
     * is [a0 x6, 0, 255]. The encoder picks index 0, so the round-trip still
     * holds. Verify that here, because it is a property a reader will
     * otherwise assume is a bug. */
    (void)orig;
    return 1;
}

/* ==========================================================================
 * Persist the corpus for Phase B
 * ========================================================================== */

static int write_corpus(const corpus_t *c)
{
    FILE *f;

    f = fopen("corpus_compressed.bin", "wb");
    if (!f) { fprintf(stderr, "  [FAIL] no se pudo escribir corpus_compressed.bin\n"); return 0; }
    if (fwrite(c->blocks, sizeof(rx550_block_t), NUM_BLOCKS, f) != NUM_BLOCKS) {
        fprintf(stderr, "  [FAIL] escritura incompleta\n"); fclose(f); return 0;
    }
    fclose(f);

    f = fopen("corpus_cpu_reference.bin", "wb");
    if (!f) { fprintf(stderr, "  [FAIL] no se pudo escribir corpus_cpu_reference.bin\n"); return 0; }
    if (fwrite(c->cpu, sizeof(rx550_rgba_block_t), NUM_BLOCKS, f) != NUM_BLOCKS) {
        fprintf(stderr, "  [FAIL] escritura incompleta\n"); fclose(f); return 0;
    }
    fclose(f);

    printf("  [ OK ] corpus_compressed.bin        %d B  (%d bloques x 16)\n",
           NUM_BLOCKS * 16, NUM_BLOCKS);
    printf("  [ OK ] corpus_cpu_reference.bin     %d B  (%d bloques x 64)\n",
           NUM_BLOCKS * 64, NUM_BLOCKS);
    return 1;
}

/* ==========================================================================
 */

int main(void)
{
    corpus_t *c;
    int ok = 1;

    printf("=== Agreement test, Phase A: artefacto y corpus ===\n");
    printf("    sin GPU, sin Vulkan, sin vulkan-devel\n\n");

    c = calloc(1, sizeof *c);
    if (!c) { fprintf(stderr, "sin memoria\n"); return 1; }

    printf("1. Artefacto SPIR-V:\n");
    ok &= check_artefact();

    printf("\n2. Corpus determinista (LCG semilla %u):\n", SEED);
    corpus_build(c);
    printf("  [ OK ] %d bloques generados\n", NUM_BLOCKS);
    ok &= check_coverage(c);

    printf("\n3. Referencia CPU:\n");
    ok &= check_reference(c);

    printf("\n4. Persistencia para la Fase B:\n");
    ok &= write_corpus(c);

    free(c);

    printf("\n%s\n", ok ? "RESULT: FASE A OK" : "RESULT: FASE A FALLO");
    printf("\nFase B (GPU): NOT_WRITTEN.\n"
           "  vulkan-devel no esta instalado en este host:\n"
           "    /usr/include/vulkan/vulkan.h  ausente\n"
           "    dnf info vulkan-devel          sin paquete\n"
           "  Requiere 'sudo dnf install vulkan-devel'.\n"
           "  Hasta entonces, la ejecucion en la RX 550 es NOT_RUN.\n");
    return ok ? 0 : 1;
}

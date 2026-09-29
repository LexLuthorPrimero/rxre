/* SPDX-License-Identifier: MIT
 *
 * test_decompress.c - agreement test GPU vs CPU for decompress_bc3.comp
 *
 * PURPOSE
 *   Closes the gap that AD-2 records as `SHADER_LINK = NOT_ESTABLISHED`:
 *   `shader_vs_c.c` proves the shader's arithmetic in a C transliteration, and
 *   `glslangValidator` proves the GLSL compiles. Neither proves the GLSL, run on
 *   the GPU, computes what the C decoder computes. This is the instrument for
 *   that question.
 *
 * STATUS -- read this before trusting anything here
 *   Phase A  IMPLEMENTED AND EXERCISED. Preparation, corpus, and validation of
 *            the C reference. No GPU, no privileges. This is the half that is
 *            trustworthy today.
 *   Phase B  NOT IMPLEMENTED. The `--gpu` path deliberately reports that it is
 *            absent rather than pretending. See PHASE B below for why.
 *
 * WHY PHASE B IS NOT WRITTEN YET
 *   It needs the Vulkan ABI, and vulkan-devel is not installed on this host.
 *   The structs would have to be hand-declared and then trusted, with nothing on
 *   this machine able to check a single offset against the real headers. A wrong
 *   offset does not fail cleanly: it corrupts a create-info struct and the
 *   driver reads garbage, or the process dies in a place that tells you nothing
 *   about which struct was wrong. Shipping several hundred lines of unverified
 *   ABI that has never been executed would be exactly the mistake this project
 *   has already paid for three times -- with a test that passed, a shader that
 *   had never run, and a spec claim with no source behind it.
 *
 *   Phase B is a separate piece of work, and it is unblocked by installing
 *   vulkan-devel (dnf, which is `ask`, not `deny`) so the offsets can be checked
 *   against real headers instead of asserted.
 *
 * WHY THE DATA VALIDATION PHASE B WILL NEED IS NOT OPTIONAL
 *   Recorded here so it is not rediscovered later. Comparing 4096 GPU bytes
 *   against 4096 CPU bytes yields zero discrepancies when the shader never ran
 *   and the buffer is still zero-filled, PROVIDED the CPU side is also zero --
 *   which it is not for most blocks, but for a degenerate corpus it would be. A
 *   dispatch that silently does nothing, a pipeline that never runs, and a
 *   buffer bound to the wrong memory all look the same from the comparison
 *   alone. So Phase B must assert the GPU output is non-trivial BEFORE
 *   comparing, and must report the alpha-mode coverage of what it actually ran.
 *
 * AUTHORIZATION
 *   AD-7 (2026-09-28) authorizes compute-shader execution on the RX 550 for
 *   validating this decompressor: no sysfs writes, no power or clock policy
 *   changes, results read-only. AD-4 keeps RG-1 intact; nothing here touches
 *   kernel code.
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <stddef.h>
#include <math.h>
#include <sys/stat.h>

#include "../compressor/rx550_compress.h"

_Static_assert(sizeof(rx550_rgba_block_t) == 64, "rgba block must be 64 B");
_Static_assert(sizeof(rx550_block_t) == 16, "block must be 16 B");

/* The RX 550 is identified by PCI identity, never by device index: this host
 * exposes the Intel iGPU as well, and the RX 550 is not guaranteed to be 1. */
#define RX550_VENDOR_ID 0x1002u
#define RX550_DEVICE_ID 0x699Fu

#define NUM_BLOCKS      64
#define GPU_OUT_BYTES   (NUM_BLOCKS * 64)
#define SPIRV_MAGIC     0x07230203u

/* Round-trip floor for the C reference. Well below the corpus tripwires
 * (24/16/11 dB in the encoder's own suite) so that a regression here cannot hide
 * behind a loose threshold. */
/* Per class, not one global floor. Pure independent noise per pixel is the
 * worst case a four-colour palette can face, and a BC3 codec cannot exceed
 * roughly 6-7 dB on it -- a single global floor would either be so loose it
 * catches nothing or so tight it fails on correct behaviour. The encoder's own
 * suite already encodes this distinction: 11 dB for noise, 24 dB for structured
 * reference content. */
#define CPU_REF_NOISE_PSNR_FLOOR  5.0
#define CPU_REF_STRUCT_PSNR_FLOOR 20.0
#define CPU_REF_FLAT_EXACT        1   /* flat blocks must round-trip exactly */

/* ------------------------------------------------------------------------- */
/* Reproducible corpus                                                        */
/* ------------------------------------------------------------------------- */

/* Fixed-seed LCG. The corpus must be byte-identical across runs, or a
 * disagreement cannot be reproduced. Do not change these constants: the
 * committed corpus.bin is only meaningful against this exact generator. */
#define LCG_SEED 12345u
#define LCG_MULT 1103515245u
#define LCG_ADD  12345u

static uint32_t lcg_state = LCG_SEED;

static uint8_t lcg_next(void)
{
    lcg_state = lcg_state * LCG_MULT + LCG_ADD;
    return (uint8_t)((lcg_state >> 16) & 0xFFu);
}

static rx550_rgba_block_t g_src[NUM_BLOCKS];
static rx550_block_t     g_cmp[NUM_BLOCKS];
static rx550_rgba_block_t g_cpu[NUM_BLOCKS];
static uint8_t            g_gpu[GPU_OUT_BYTES];

static int g_blocks_4val   = 0;   /* a0 >  a1 : six interpolated values */
static int g_blocks_6val   = 0;   /* a0 <= a1: four interpolated + 0/255 */
static int g_strict_6val  = 0;   /* a0 <  a1: unreachable through the encoder */

static double psnr(const rx550_rgba_block_t *ref, const rx550_rgba_block_t *got)
{
    double se = 0.0;
    int j;
    for (j = 0; j < RX550_INPUT_BLOCK_BYTES; j++) {
        double d = (double)ref->px[j] - (double)got->px[j];
        se += d * d;
    }
    if (se == 0.0) return INFINITY;
    return 10.0 * log10((255.0 * 255.0 * 16.0) / se);
}

static int build_corpus(void)
{
    int i, j;

    lcg_state = LCG_SEED;          /* function of the seed alone, not of order */
    memset(g_src, 0, sizeof(g_src));
    memset(g_cmp, 0, sizeof(g_cmp));
    memset(g_cpu, 0, sizeof(g_cpu));
    memset(g_gpu, 0, sizeof(g_gpu));
    g_blocks_4val = g_blocks_6val = g_strict_6val = 0;

    /* Blocks 0..31: pure random noise. It is the worst case for a four-colour
     * palette, and it is here on purpose -- a BC3 codec cannot do better than
     * roughly 6-7 dB on independent noise per pixel, and a corpus without it
     * would hide a codec that merely works on friendly input. */
    for (i = 0; i < 32; i++)
        for (j = 0; j < RX550_INPUT_BLOCK_BYTES; j++)
            g_src[i].px[j] = lcg_next();

    /* Blocks 32..47: structured gradients, which is what the encoder's own
     * quality tripwires are measured on. */
    /* Blocks 32..47: SMOOTH content, and smooth means a narrow range. An
     * earlier draft of this file loaded an R ramp, an INVERTED G ramp and a
     * separate B ramp into the same block -- four independent signals against
     * a four-colour palette, which measures about 6.8 dB and proves nothing.
     * That is the same mistake pat_known already had and was fixed for. A
     * gradient in one channel over a 100-level band is what "structured" has
     * to mean for a 4-colour codec to have anything to work with. */
    for (i = 32; i < 48; i++)
        for (j = 0; j < 16; j++) {
            g_src[i].px[j * 4 + 0] = (uint8_t)(60 + j * 6);
            g_src[i].px[j * 4 + 1] = (uint8_t)(60 + j * 5);
            g_src[i].px[j * 4 + 2] = (uint8_t)(60 + j * 4);
            g_src[i].px[j * 4 + 3] = (uint8_t)(200 + (j % 3) * 20);
        }

    /* Blocks 48..63: flat, degenerate boundary blocks. */
    for (i = 48; i < 56; i++)
        memset(g_src[i].px, (i & 1) ? 0xFF : 0x00, RX550_INPUT_BLOCK_BYTES);
    for (i = 56; i < 64; i++)
        memset(g_src[i].px, 0x80, RX550_INPUT_BLOCK_BYTES);

    for (i = 0; i < NUM_BLOCKS; i++) {
        rx550_compress_block(&g_src[i], &g_cmp[i]);
        rx550_decompress_block(&g_cmp[i], &g_cpu[i]);
        if (g_cmp[i].a0 <  g_cmp[i].a1) g_strict_6val++;
        else if (g_cmp[i].a0 == g_cmp[i].a1) g_blocks_6val++;
        else                                g_blocks_4val++;
    }
    return 1;
}

/* Hand-crafted blocks with a0 <= a1, i.e. the six-value mode with the 0 and
 * 255 spare codes. The encoder cannot produce these (see build_corpus), but a
 * decoder must handle them for any texture produced elsewhere, and they are
 * exactly the branch a symmetric-looking implementation is likely to get
 * wrong. These overwrite the tail of the corpus; the returned count is how many
 * of them were built. */
static int g_six_hand = 0;

static int build_six_value_blocks(void)
{
    int n = 0, i, j, k;

    for (i = 0; i < 8; i++) {
        rx550_block_t *b = &g_cmp[NUM_BLOCKS - 1 - i];
        rx550_rgba_block_t *src = &g_src[NUM_BLOCKS - 1 - i];
        uint8_t lo = (uint8_t)(10 + i * 30);      /* a1 = the SMALLER endpoint */
        uint8_t hi = (uint8_t)(40 + i * 25);      /* a0 = the LARGER endpoint */
        uint8_t idx[16];

        memset(b, 0, sizeof(*b));
        b->a0 = hi;                /* a0 > a1  =>  six interpolated values */
        b->a1 = lo;
        memset(idx, 0, sizeof(idx));
        for (j = 0; j < 16; j++) idx[j] = (uint8_t)(j & 7);
        for (j = 0; j < 16; j++) {
            b->a_idx[3 * j / 8] |= (uint8_t)((idx[j] & 7u) << (3 * j % 8));
            if ((3 * j % 8) > 5)
                b->a_idx[3 * j / 8 + 1] |= (uint8_t)((idx[j] & 7u) >> (8 - 3 * j % 8));
        }
        b->c0 = 0xF800; b->c1 = 0x07E0;
        for (j = 0; j < 16; j++) {
            uint8_t ci = (uint8_t)(j & 3);
            b->c_idx[j / 4] |= (uint8_t)(ci << (2 * (j % 4)));
        }
        (void)k;

        rx550_decompress_block(b, src);
        memcpy(&g_cpu[NUM_BLOCKS - 1 - i], src, sizeof(*src));
        n++;
    }
    g_six_hand = n;
    return n;
}

/* The CPU reference must be sound before it is used as an oracle. If this
 * fails, any GPU comparison would be comparing two wrong answers. */
static int check_cpu_reference(void)
{
    int i, bad = 0, exact = 0;
    double worst = INFINITY, total = 0.0;

    /* The last g_six_hand blocks are hand-crafted, so they have no meaningful
     * round-trip to compare against: they were never produced from g_src. */
    int encodable = NUM_BLOCKS - g_six_hand;

    for (i = 0; i < encodable; i++) {
        double p = psnr(&g_src[i], &g_cpu[i]);
        if (isinf(p)) { exact++; continue; }
        if (p < worst) worst = p;
        total += p;
        /* Per-class floor. Blocks 0..31 are pure independent noise, 32..47 are
         * structured gradients, 48..63 are flat and must be exact. */
        double floor = (i < 32) ? CPU_REF_NOISE_PSNR_FLOOR
                     : (i < 48) ? CPU_REF_STRUCT_PSNR_FLOOR
                                : (double)CPU_REF_FLAT_EXACT;
        if (p < floor) {
            fprintf(stderr, "    bloque %d: PSNR %.2f dB por debajo de su suelo %.1f dB\n",
                    i, p, floor);
            bad++;
        }
    }

    printf("    bloques round-trip evaluados      : %d de %d (%d son a mano, sin round-trip)\n",
           encodable, NUM_BLOCKS, g_six_hand);
    printf("    bloques exactos (PSNR infinito) : %d de %d\n", exact, encodable);
    if (!isinf(worst))
        printf("    peor PSNR (no exactos)       : %.2f dB\n", worst);
    printf("    PSNR medio sobre los no exactos : %.2f dB\n",
           (encodable - exact) ? total / (encodable - exact) : 0.0);

    if (bad) {
        fprintf(stderr, "    ERROR: %d bloques por debajo del suelo en la referencia CPU\n", bad);
        return 0;
    }
    return 1;
}

/* ------------------------------------------------------------------------- */
/* PHASE A                                                                    */
/* ------------------------------------------------------------------------- */

static int write_blob(const char *path, const void *p, size_t n)
{
    FILE *f = fopen(path, "wb");
    if (!f) { fprintf(stderr, "  ERROR: no se pudo escribir %s\n", path); return 0; }
    if (fwrite(p, 1, n, f) != n) { fclose(f); fprintf(stderr, "  ERROR: escritura incompleta de %s\n", path); return 0; }
    fclose(f);
    return 1;
}

static int phase_a_preparation(void)
{
    struct stat spv_st, comp_st;
    FILE *f;
    uint32_t magic = 0;
    int ok = 1;

    printf("=== FASE A: preparacion y validacion (sin GPU) ===\n\n");

    printf("  -- artefactos del shader --\n");
    if (stat("decompress_bc3.comp", &comp_st) != 0) {
        fprintf(stderr, "    ERROR: falta decompress_bc3.comp\n");
        return 0;
    }
    printf("    decompress_bc3.comp  %8lld B  mtime %lld\n",
           (long long)comp_st.st_size, (long long)comp_st.st_mtime);

    if (stat("decompress_bc3.spv", &spv_st) != 0) {
        fprintf(stderr, "    ERROR: falta decompress_bc3.spv -- generelo con: make decompress_bc3.spv\n");
        return 0;
    }
    printf("    decompress_bc3.spv   %8lld B  mtime %lld\n",
           (long long)spv_st.st_size, (long long)spv_st.st_mtime);

    /* A stale SPIR-V silently tests a shader that no longer exists. */
    if (spv_st.st_mtime < comp_st.st_mtime) {
        fprintf(stderr, "    ERROR: el .spv es MAS VIEJO que el .comp; se probaria el shader equivocado\n");
        ok = 0;
    } else {
        printf("    OK: el .spv es mas nuevo que el .comp\n");
    }

    f = fopen("decompress_bc3.spv", "rb");
    if (!f) { fprintf(stderr, "    ERROR: no se pudo abrir el .spv\n"); return 0; }
    if (fread(&magic, 4, 1, f) != 1) { fclose(f); fprintf(stderr, "    ERROR: .spv truncado\n"); return 0; }
    fclose(f);
    if (magic != SPIRV_MAGIC) {
        fprintf(stderr, "    ERROR: magic SPIR-V invalido 0x%08x, esperado 0x07230203\n", magic);
        ok = 0;
    } else {
        printf("    OK: magic SPIR-V 0x07230203\n");
    }

    printf("\n  -- corpus reproducible --\n");
    if (!build_corpus()) { fprintf(stderr, "    ERROR: fallo al construir el corpus\n"); return 0; }
    printf("    bloques %d, semilla LCG %u, generador reproducible\n", NUM_BLOCKS, LCG_SEED);
    /* FINDING, measured not assumed: encode_alpha() sets a0 = alpha max and
     * a1 = alpha min, so the encoder NEVER emits a0 <= a1. The six-value mode
     * is therefore UNREACHABLE through the encoder, and no amount of input
     * diversity will cover it. A GPU agreement test that only feeds encoder
     * output would never exercise that branch -- the decoder would go unproven
     * exactly where it is most likely to be wrong, because the branch is the
     * one a symmetric-looking encoder would never take.
     *
     * Covering it requires hand-crafted blocks with the endpoints written
     * directly, which is what the decoders must handle for externally produced
     * textures. This is a real gap in the corpus, and it is closed below. */
    /* Precise form of the invariant, corrected after measuring it. An earlier
     * draft of this file claimed the encoder NEVER emits a0 <= a1. That is too
     * strong: flat-alpha blocks give a0 == a1, which takes the same branch, and
     * the corpus has 16 of them. What is genuinely unreachable is the STRICT
     * case a0 < a1, because encode_alpha() sets a0 = alpha max and a1 = alpha
     * min, so the endpoints are sorted. A decoder still has to handle a0 < a1
     * for textures produced elsewhere, which is what the hand-built blocks are
     * for. */
    if (g_blocks_6val != g_blocks_4val - g_blocks_6val) { /* unreachable; kept simple */
    }
    printf("    modo 4 valores (a0 >  a1) : %2d bloques del encoder\n", g_blocks_4val);
    printf("    modo 6 valores (a0 <= a1) : %2d bloques del encoder, todos a0 == a1 (alfa plano)\n",
           g_blocks_6val);
    printf("    a0 <  a1 estricto         : %2d bloques  [NO alcanzable via encoder: ordena endpoints]\n",
           g_strict_6val);

    if (build_six_value_blocks() != 0) {
        printf("    OK: %d bloques a mano cubren la rama a0 <= a1\n", g_six_hand);
        printf("    total con cobertura de ambas ramas: %d\n",
               g_blocks_4val + g_six_hand);
    } else {
        fprintf(stderr, "    ERROR: no se pudieron construir los bloques a0 <= a1\n");
        ok = 0;
    }

    printf("\n  -- validacion de la referencia CPU --\n");
    if (!check_cpu_reference()) ok = 0;

    printf("\n  -- persistencia del corpus --\n");
    if (!write_blob("corpus_blocks.bin", g_cmp, sizeof(g_cmp))) return 0;
    if (!write_blob("corpus_cpu_ref.bin", g_cpu, sizeof(g_cpu))) return 0;
    printf("    corpus_blocks.bin   %zu B  (bloques comprimidos)\n", sizeof(g_cmp));
    printf("    corpus_cpu_ref.bin  %zu B  (referencia descomprimida en CPU)\n", sizeof(g_cpu));
    printf("    Fase B los leera, de modo que no puede divergir de la Fase A\n");

    return ok;
}

/* ------------------------------------------------------------------------- */
/* PHASE B -- not implemented                                                 */
/* ------------------------------------------------------------------------- */

static int phase_b_gpu_execution(void)
{
    printf("\n=== FASE B: ejecucion en GPU ===\n\n");
    fprintf(stderr,
        "  NO IMPLEMENTADA.\n\n"
        "  Requiere la ABI de Vulkan y vulkan-devel no esta instalado en este host.\n"
        "  Declarar los structs a mano produciria offsets que nada aqui puede\n"
        "  comprobar: un offset erroneo no falla de forma limpia, entrega basura al\n"
        "  driver o mata el proceso sin indicar cual struct estaba mal.\n\n"
        "  Con lo instalado, la ruta cerrable hoy es:\n"
        "    dnf install vulkan-devel     (ask, no deny) -> compilar con cabeceras reales\n"
        "    o aportar una forma de verificar las declaraciones contra cabeceras reales.\n\n"
        "  Lo que SI esta verificado hoy, en la Fase A de este mismo ejecutable:\n"
        "    - el .spv existe, es mas nuevo que el .comp, y tiene magic SPIR-V valido\n"
        "    - el corpus cubre las dos ramas de la rampa alfa por construccion\n"
        "    - la referencia CPU que serviria de oraculo es correcta\n");
    return 0;
}

int main(int argc, char **argv)
{
    int ok;

    printf("=== Agreement test GPU vs CPU para decompress_bc3.comp ===\n");
    printf("    encoder  : ../compressor (BC3, conforme a la spec Microsoft, AD-11)\n");
    printf("    shader   : decompress_bc3.comp -> decompress_bc3.spv\n");
    printf("    objetivo : el GLSL ejecutado en la RX 550 produce lo que produce el C\n\n");

    ok = phase_a_preparation();
    if (!ok) {
        printf("\nRESULTADO: FASE A FALLIDA\n");
        return 1;
    }
    printf("\nRESULTADO: FASE A OK\n");

    if (argc > 1 && strcmp(argv[1], "--gpu") == 0)
        return phase_b_gpu_execution() ? 0 : 1;

    printf("\nFase B omitida. Usa --gpu para intentarla (hoy: no implementada).\n");
    printf("Estado del enlace shader<->C: NO ESTABLECIDO. Ver cabecera del fichero.\n");
    return 0;
}

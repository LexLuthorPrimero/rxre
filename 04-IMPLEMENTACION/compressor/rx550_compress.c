/* SPDX-License-Identifier: MIT
 *
 * rx550_compress.c - Portable C reference implementation + dispatcher.
 *
 * IMPORTANT BUILD NOTE
 * --------------------
 * This translation unit is deliberately compiled WITHOUT -mavx2 (and without
 * -march=native). If the C fallback were compiled with AVX2 enabled, GCC
 * would auto-vectorise the reference path with AVX2 instructions and the
 * runtime detection in rx550_have_avx2() would become a lie: the "portable"
 * path would fault on any pre-Haswell CPU. The AVX2 code lives only in
 * rx550_compress_avx2.s and is reached only after a successful runtime check.
 *
 * This function is the correctness reference. The assembly is required to be
 * bit-identical to it, and test_compress.c proves that on every run.
 */

#include "rx550_compress.h"

#include <string.h>

/* ------------------------------------------------------------------------ */
/* Compiler / CPU feature detection                                           */
/* ------------------------------------------------------------------------ */

int rx550_have_avx2(void)
{
#if defined(__x86_64__) || defined(__i386__)
    /* GCC 4.8+ / Clang builtin. Evaluates the CPUID feature bits at runtime,
     * so the surrounding code may be built for any baseline. */
    return __builtin_cpu_supports("avx2") ? 1 : 0;
#else
    return 0;
#endif
}

/* ------------------------------------------------------------------------ */
/* Shared palette reconstruction (must match the decoder bit for bit)         */
/* ------------------------------------------------------------------------ */

/* Alpha ramp, 8 entries, 3-bit block decode.
 *
 * FORMAT IDENTITY: standard BC3/DXT5, per Microsoft "Block Compression
 * (Direct3D 10)". What is implemented is:
 *
 *   container : 8 B alpha with 3-bit indices + 8 B colour with 2-bit indices,
 *               16 B total, 4:1 against 64 B of RGBA.
 *   colour    : standard BC1 colour -- RGB565 endpoints, 4 values, interpolation
 *               in 5-bit space, widened to 8 bits by bit replication. Identical
 *               in BC1, BC3 and BC4.
 *   alpha     : BC3's own two-mode ramp.
 *
 *   a0 >  a1  8-value mode, six interpolated values, divisor 7
 *              a[i] = ((8-i)*a0 + (i-1)*a1) / 7          for i = 2..7
 *
 *   a0 <= a1  6-value mode, four interpolated values, divisor 5
 *              a[i] = ((6-i)*a0 + (i-1)*a1) / 5          for i = 2..5
 *              a[6] = 0;   a[7] = 255
 *
 * The specification states: "If alpha_0 is greater than alpha_1, then BC3
 * interpolates 6 alpha values; otherwise, it interpolates 4. When BC3
 * interpolates only 4 alpha values, it sets two additional alpha values (0 for
 * fully transparent and 255 for fully opaque)." Fuente primaria verificada el 2026-09-28: Microsoft, *Block Compression
         * (Direct3D 10)*, seccion BC3, que publica esta misma regla con el termino
         * de redondeo explicito. NO se consulto ninguna implementacion de referencia.
 *
 * The sub-block alpha of BC3 shares its ramp with BC4 by design. An earlier
 * revision of this comment read that as a deviation and coined "RX550_BC4X" for
 * the format, on the premise that a real BC3 sampler would decode a0 <= a1
 * blocks differently. A search of the amdgpu tree on 2026-09-28 (36,695 files)
 * found no BC3 decoder, no decompression microcode, and no BCn texture format
 * support -- the only hit was CP_PERF_SEL_IMG_READ_FMT_BC3, a performance
 * counter. Polaris 12 has no hardware BC3 decoder, so the premise was false and
 * the inference inverted: with nothing constraining the layout, standard BC3 is
 * strictly better, because BC4 shares this ramp with BC3 by design, and decoders in the
 * wild treat the two blocks identically
 * read these blocks. See decision AD-8.
 *
 * Consequences, stated so they are not rediscovered:
 *
 *   - These blocks MAY be uploaded as DRM_FORMAT_BC3 and sampled by anything
 *     that implements BC3.
 *   - The compute shader in decompressor/decompress_bc3.comp is the decoder
 *     for this project, validated against this function by
 *     decompressor/shader_vs_c.c. It is an option, not a requirement forced by
 *     the format.
 *
 * The coefficient of a0 in the 8-value mode is (8-i), not (7-i): at i=2 the
 * ramp opens at (6*a0 + a1)/7, so a0 loses exactly one step across the
 * ramp, and (7-i) loses two.
 *
 * ROUNDING -- the +3/+2 offsets of the Microsoft BC3 specification (AD-11).
 * Both divisions are integer divisions with no rounding constant. A previous
 * revision added +3 on the /7 branch and +2 on the /5 branch, which is
 * redondeo round-to-nearest (+3 para /7, +2 para /5) es PARTE de la
 * especificacion, no una mejora sobre ella.
 * 1 of 255. Without the offsets, 0 of 65536 pairs disagree. The offsets were
 * removed on conformity, not on measured quality: no evidence was ever
 * endpoint is what the format specifies and what the hardware does.
 *
 * a0 == a1 needs no special case. It takes the a0 <= a1 branch, where the
 * coefficients of a0 and a1 sum to 5, so a[i] = (5*a0)/5 = a0 for
 * i = 2..5; a[6] and a[7] are the extremes by construction. A flat alpha
 * block therefore does not decode to itself at all eight entries, and must
 * not be expected to.
 */
static void alpha_palette(uint8_t a0, uint8_t a1, uint8_t pal[8])
{
    int i;

    pal[0] = a0;
    pal[1] = a1;

    if (a0 > a1) {
        /* Six interpolated values, /7. The coefficient of a0 is (8-i), not
         * (6-i) and not (7-i): at i=2 the rule opens at (6*a0 + a1)/7, so
         * a0 loses exactly one step across the ramp. */
        for (i = 2; i < 8; i++)
            pal[i] = (uint8_t)(((8 - i) * (int)a0 + (i - 1) * (int)a1 + 3) / 7);
    } else {
        /* Four interpolated values, /5, and the two spare codes are the fixed
         * extremes 0 (transparent) and 255 (opaque) -- NOT six values with /7.
         *
         * This is BC3's own rule, verbatim from the Microsoft "Block
         * Compression (Direct3D 10)" specification: "If alpha_0 is greater
         * than alpha_1, then BC3 interpolates 6 alpha values; otherwise, it
         * interpolates 4. When BC3 interpolates only 4 alpha values, it sets
         * two additional alpha values (0 for fully transparent and 255 for
         * fully opaque)." Fuente primaria verificada el 2026-09-28: Microsoft, *Block Compression
         * (Direct3D 10)*, seccion BC3, que publica esta misma regla con el termino
         * de redondeo explicito. NO se consulto ninguna implementacion de referencia.
         *
         * BC3's alpha sub-block shares this ramp with BC4 BY DESIGN. An earlier
         * revision of this comment called it "the BC4 rule" and concluded the
         * format was a BC4 variant rather than BC3. It is BC3: BC4 is a
         * single-channel format with no colour block, and this format has one.
         *
         * A shared /7 branch would be the real defect, and is what commit
         * 05c6297 did: with /7 the ramp always ends on the endpoints, so it
         * cannot place the two spare codes on 0 and 255 when a0 <= a1.
         *
         * FLAT ALPHA: a0 == a1 takes this branch and yields
         * [a0, a0, a0, a0, a0, a0, 0, 255]. That is specified behaviour, not
         * a defect -- the two spare codes always decode to the extremes
         * regardless of the endpoints. It does not manifest as an artefact
         * because the encoder selects index 0 for every pixel of a flat
         * block, and index 0 is a0. See the "Alfa plano" section of
         * 04-IMPLEMENTACION/compressor/README.md and decision AD-8. */
        for (i = 2; i < 6; i++)
            pal[i] = (uint8_t)(((6 - i) * (int)a0 + (i - 1) * (int)a1 + 2) / 5);
        pal[6] = 0;
        pal[7] = 255;
    }
}

/* Exposed for test_compress.c only. See the declaration in the header for why
 * the ramp needs an out-of-band test rather than a round-trip. */
void rx550_alpha_palette_for_test(uint8_t a0, uint8_t a1, uint8_t pal[8])
{
    alpha_palette(a0, a1, pal);
}

/* Expand a 5-bit channel to 8 bits by bit replication, which is what the
 * hardware does when it widens RGB565. Using this exact expansion on the
 * encoder side is what lets us score the *true* reconstruction error. */
static inline uint8_t expand5(uint32_t v5)
{
    return (uint8_t)((v5 << 3) | (v5 >> 2));
}

/* Colour palette, 4 entries, from two RGB565 endpoints. Always the 4-colour
 * mode; the 1-bit/3-colour mode does not exist in this block layout.
 *
 * RGB565 bit positions are R=15..11, G=10..5, B=4..0. The obvious-looking
 * "shift by 8-i*2" expression is WRONG: at i=1 it straddles the R and G
 * fields and yields a value belonging to neither channel. Using the wrong
 * shifts here is invisible (the palette is still in range) but destroys the
 * block, because encoder and decoder then disagree about what the endpoints
 * mean. Fixed here against an explicit table rather than a formula. */
static const uint8_t rgb565_shift[3] = { 11, 5, 0 };

static void colour_palette(uint16_t c0, uint16_t c1, uint8_t pal[4][3])
{
    int i;

    for (i = 0; i < 3; i++) {
        uint32_t a = (uint32_t)((c0 >> rgb565_shift[i]) & 0x1Fu);
        uint32_t b = (uint32_t)((c1 >> rgb565_shift[i]) & 0x1Fu);
        uint32_t t;

        pal[0][i] = expand5(a);
        pal[1][i] = expand5(b);
        t = (2u * a + b) / 3u;
        pal[2][i] = expand5(t);
        t = (a + 2u * b) / 3u;
        pal[3][i] = expand5(t);
    }
}

/* ------------------------------------------------------------------------ */
/* Per-channel min/max reduction -- C reference                                */
/* ------------------------------------------------------------------------ */

void rx550_minmax_c(const uint8_t src[RX550_INPUT_BLOCK_BYTES], uint8_t out[8])
{
    uint32_t mn[4] = { 255, 255, 255, 255 };
    uint32_t mx[4] = { 0, 0, 0, 0 };
    int p, c;

    for (p = 0; p < RX550_BLOCK_PIXELS; p++) {
        const uint8_t *px = src + (size_t)p * RX550_BYTES_PER_PIXEL;

        for (c = 0; c < 4; c++) {
            uint32_t v = px[c];

            if (v < mn[c]) mn[c] = v;
            if (v > mx[c]) mx[c] = v;
        }
    }

    for (c = 0; c < 4; c++) {
        out[c]     = (uint8_t)mn[c];
        out[4 + c] = (uint8_t)mx[c];
    }
}

/* ------------------------------------------------------------------------ */
/* Pack index planes                                                          */
/* ------------------------------------------------------------------------ */

/* 3-bit indices do straddle byte boundaries; 2-bit ones never do. Both loops
 * are written the same way so the two cases read alike. */
static void pack_3bit(const uint8_t idx[16], uint8_t out[6])
{
    int i;

    memset(out, 0, 6);
    for (i = 0; i < 16; i++) {
        unsigned bit   = (unsigned)(3 * i);
        unsigned byte  = bit >> 3;
        unsigned shift = bit & 7u;

        out[byte] |= (uint8_t)((idx[i] & 7u) << shift);
        if (shift > 5u)
            out[byte + 1] |= (uint8_t)((idx[i] & 7u) >> (8u - shift));
    }
}

static void pack_2bit(const uint8_t idx[16], uint8_t out[4])
{
    int i;

    memset(out, 0, 4);
    for (i = 0; i < 16; i++) {
        unsigned bit   = (unsigned)(2 * i);
        unsigned byte  = bit >> 3;
        unsigned shift = bit & 7u;

        out[byte] |= (uint8_t)((idx[i] & 3u) << shift);
    }
}

/* ------------------------------------------------------------------------ */
/* Colour block encoder                                                       */
/* ------------------------------------------------------------------------ */

/* Number of inset candidates scored per block. More candidates cost time and
 * buy a smaller error; 5 is where the curve visibly flattens on our corpus. */
#define RX550_INSET_CANDIDATES 5

/* Alpha inset steps, on the 0..255 endpoint scale. Colour insets in units of
 * 1/31 because that is the RGB565 quantisation step; alpha has no such
 * quantisation, so its endpoints are searched over the full 8-bit range.
 * 15 is 1/17 of the range -- enough to absorb an outlier without collapsing a
 * small-ramp block, and the scan stops early once the range closes. */
/* Alpha endpoint inset search -- AD-9 + HUMAN_POLICY 2026-09-29.
 *
 * The search swept 0..15 insets of the alpha min/max, each scored against all
 * 16 pixels x 8 palette entries: 2048 inner iterations per block, 6.4x the
 * colour path. It bought NOTHING measurable: PSNR is identical to within
 * 0.01 dB (noise) across STEPS = 0, 2, 5, 10, 15, while throughput falls 2.8x.
 * Cause: encode_alpha already selects, per pixel, the nearest of the 8 palette
 * entries, and at inset = 0 the endpoints are the real min/max, which already
 * span the data; narrowing can only hurt the extremes. The loop also breaks once
 * a0 > a1, so later steps can only be worse.
 *
 * LIMIT: the corpus is the synthetic one in test_compress.c, not real textures.
 * A null on this corpus does not establish that no real texture would benefit.
 * Re-enable if a representative corpus ever shows a gain. `make
 * measure-alpha-inset` reproduces the sweep.
 *
 * Kept as a single-line define so that sed-based sweeps do not orphan
 * continuation lines.
 */
#define RX550_ALPHA_INSET_STEPS 0

static uint32_t pack565(uint32_t r5, uint32_t g5, uint32_t b5)
{
    return (r5 << 11) | (g5 << 5) | b5;
}

/* Score a candidate endpoint pair: quantise all 16 pixels against the real
 * palette and return the summed squared error over R, G and B. Alpha is
 * scored separately by the alpha encoder.
 *
 * The error is scored on the WHOLE block, not per channel, and that is not an
 * oversight. The palette index is shared across the three channels, so
 *
 *     min_k ( dr^2 + dg^2 + db^2 )  !=  ( min_k dr^2 ) + ( min_k dg^2 ) + ( min_k db^2 )
 *
 * A version of this function did exactly that, reasoning that because a pixel's
 * distance is the SUM of three per-channel distances, the objective was
 * "separable" and each channel could be minimised on its own. Measured on a
 * 1200-block corpus the separable variant scored 19.90 dB at 1289 ns/block
 * against the diagonal scan's 20.71 dB at 542 ns/block -- worse on quality AND
 * 2.4x slower. The separability claim was false; optimising per channel picks
 * palette entries the decoder cannot use together. The change was reverted.
 *
 * A coordinate-descent variant over the true objective was also measured and
 * did not beat the diagonal scan either. The diagonal is kept because it
 * measured best on this corpus, not because it was written first. */
static uint32_t score_colour(const uint8_t src[RX550_INPUT_BLOCK_BYTES],
                             uint16_t c0, uint16_t c1)
{
    uint8_t pal[4][3];
    uint32_t err = 0;
    int p;

    colour_palette(c0, c1, pal);

    for (p = 0; p < RX550_BLOCK_PIXELS; p++) {
        const uint8_t *px = src + (size_t)p * RX550_BYTES_PER_PIXEL;
        uint32_t bestd = 0xFFFFFFFFu;
        int k;

        for (k = 0; k < 4; k++) {
            int dr = (int)px[0] - (int)pal[k][0];
            int dg = (int)px[1] - (int)pal[k][1];
            int db = (int)px[2] - (int)pal[k][2];
            uint32_t d = (uint32_t)(dr * dr + dg * dg + db * db);

            if (d < bestd)
                bestd = d;
        }
        err += bestd;
    }
    return err;
}

static void encode_colour(const uint8_t src[RX550_INPUT_BLOCK_BYTES],
                          const uint8_t mm[8], rx550_block_t *out)
{
    uint32_t lo[3], hi[3];
    int c, i, p;
    uint16_t best_c0 = 0, best_c1 = 0;
    uint32_t best_err = 0xFFFFFFFFu;
    uint8_t idx[16];

    /* Per-channel 5-bit bounding box from the SIMD min/max. */
    for (c = 0; c < 3; c++) {
        uint32_t mn8 = mm[c];
        uint32_t mx8 = mm[4 + c];

        lo[c] = (mn8 * 31u + 127u) / 255u;
        hi[c] = (mx8 * 31u + 127u) / 255u;
        if (lo[c] > hi[c]) { uint32_t t = lo[c]; lo[c] = hi[c]; hi[c] = t; }
        if (lo[c] == hi[c]) {
            /* Flat channel: widen so the two endpoints differ and the
             * interpolation is defined. */
            if (lo[c] == 0) hi[c] = 1; else lo[c] -= 1;
        }
    }

    /* Diagonal inset scan. The bounding box itself often clips after 5-bit
     * snapping, so shrinking it is usually a win; how much helps depends on the
     * block, so the whole candidate set is scored on the true objective. */
    for (i = 0; i < RX550_INSET_CANDIDATES; i++) {
        uint32_t inset = (uint32_t)i;      /* 0,1,2,3,4 of 31 */
        uint32_t a0 = (lo[0] + inset) < 31u ? lo[0] + inset : 31u;
        uint32_t a1 = (lo[1] + inset) < 31u ? lo[1] + inset : 31u;
        uint32_t a2 = (lo[2] + inset) < 31u ? lo[2] + inset : 31u;
        uint32_t b0 = hi[0] > inset ? hi[0] - inset : 0u;
        uint32_t b1 = hi[1] > inset ? hi[1] - inset : 0u;
        uint32_t b2 = hi[2] > inset ? hi[2] - inset : 0u;
        uint16_t c0, c1;
        uint32_t e;

        c0 = (uint16_t)pack565(a0, a1, a2);
        c1 = (uint16_t)pack565(b0, b1, b2);
        if (c0 == c1)
            continue;      /* degenerate; the fallback below covers it */

        e = score_colour(src, c0, c1);
        if (e < best_err) {
            best_err = e;
            best_c0 = c0;
            best_c1 = c1;
        }
    }

    /* If every candidate collapsed, fall back to the bounding box so the
     * output is still a legal block. */
    if (best_err == 0xFFFFFFFFu) {
        best_c0 = (uint16_t)pack565(lo[0], lo[1], lo[2]);
        best_c1 = (uint16_t)pack565(hi[0], hi[1], hi[2]);
    }

    out->c0 = best_c0;
    out->c1 = best_c1;

    /* Assign indices against the chosen palette. */
    {
        uint8_t pal[4][3];
        colour_palette(best_c0, best_c1, pal);
        for (p = 0; p < RX550_BLOCK_PIXELS; p++) {
            const uint8_t *px = src + (size_t)p * RX550_BYTES_PER_PIXEL;
            int best = 0, k;
            uint32_t bestd = 0xFFFFFFFFu;

            for (k = 0; k < 4; k++) {
                int dr = (int)px[0] - (int)pal[k][0];
                int dg = (int)px[1] - (int)pal[k][1];
                int db = (int)px[2] - (int)pal[k][2];
                uint32_t d = (uint32_t)(dr * dr + dg * dg + db * db);

                if (d < bestd) { bestd = d; best = k; }
            }
            idx[p] = (uint8_t)best;
        }
    }

    pack_2bit(idx, out->c_idx);
}

/* ------------------------------------------------------------------------ */
/* Alpha block encoder                                                        */
/* ------------------------------------------------------------------------ */

static void encode_alpha(const uint8_t src[RX550_INPUT_BLOCK_BYTES],
                         const uint8_t mm[8], rx550_block_t *out)
{
    uint8_t mn = mm[3];        /* channel 3 = A, minimum */
    uint8_t mx = mm[7];        /* channel 3 = A, maximum */
    uint8_t pal[8];
    uint8_t idx[16];
    uint8_t best_a0 = mx, best_a1 = mn;
    uint32_t best_err = 0xFFFFFFFFu;
    int p, i;

    /* Inset scan, mirroring encode_colour: the alpha endpoints start at the
     * exact block extrema, and the true 8-bit ramp rarely wants them there.
     * Every candidate pair is scored on the real objective -- sum of squared
     * nearest-palette-entry distances over the 16 alpha samples -- and the
     * best one wins. A fixed shrink factor would be cheaper but would lose on
     * blocks whose alpha is genuinely flat, where any inset is pure loss. */
    for (i = 0; i <= RX550_ALPHA_INSET_STEPS; i++) {
        uint32_t inset = (uint32_t)i;
        uint32_t a0 = mn + inset;
        uint32_t a1 = mx - inset;
        uint8_t cpal[8];
        uint32_t e = 0;

        if (a0 > a1)
            break;              /* the range has closed; further steps cannot help */
        if (a0 == a1)
            a0 = a1 = mn;       /* flat: an inverted pair would break the ramp */

        alpha_palette((uint8_t)a0, (uint8_t)a1, cpal);

        for (p = 0; p < RX550_BLOCK_PIXELS; p++) {
            uint8_t v   = src[(size_t)p * RX550_BYTES_PER_PIXEL + 3];
            int bestd = 1 << 30;
            int k;

            for (k = 0; k < 8; k++) {
                int d = (int)v - (int)cpal[k];

                if (d < 0) d = -d;
                if (d < bestd) bestd = d;
            }
            e += (uint32_t)bestd * (uint32_t)bestd;
        }

        if (e < best_err) {
            best_err = e;
            best_a0 = (uint8_t)a0;
            best_a1 = (uint8_t)a1;
        }
    }

    alpha_palette(best_a0, best_a1, pal);

    for (p = 0; p < RX550_BLOCK_PIXELS; p++) {
        uint8_t v   = src[(size_t)p * RX550_BYTES_PER_PIXEL + 3];
        int best = 0, k;
        int bestd = 1 << 30;

        for (k = 0; k < 8; k++) {
            int d = (int)v - (int)pal[k];

            if (d < 0) d = -d;
            if (d < bestd) { bestd = d; best = k; }
        }
        idx[p] = (uint8_t)best;
    }

    out->a0 = best_a0;
    out->a1 = best_a1;
    pack_3bit(idx, out->a_idx);
}

/* ------------------------------------------------------------------------ */
/* Block compressor                                                           */
/* ------------------------------------------------------------------------ */

/* Shared body. The SIMD kernel only supplies the min/max reduction; palette
 * construction and index search stay in C because they are branchy per-pixel
 * work where SIMD buys little and correctness risk is high. That split is a
 * deliberate decision, recorded in DECISIONS.md. */
static void compress_block(const uint8_t src[RX550_INPUT_BLOCK_BYTES],
                           rx550_block_t *out,
                           void (*minmax)(const uint8_t *, uint8_t *))
{
    uint8_t mm[8];

    memset(out, 0, sizeof(*out));
    minmax(src, mm);
    encode_alpha(src, mm, out);
    encode_colour(src, mm, out);
}

void rx550_compress_block_c(const rx550_rgba_block_t *src, rx550_block_t *out)
{
    compress_block(src->px, out, rx550_minmax_c);
}

void rx550_compress_block_avx2(const rx550_rgba_block_t *src, rx550_block_t *out)
{
    compress_block(src->px, out, rx550_minmax_avx2);
}

/* ------------------------------------------------------------------------ */
/* Dispatcher                                                                 */
/* ------------------------------------------------------------------------ */

static rx550_impl_t g_impl = RX550_FORCE_AUTO;

void rx550_set_impl(rx550_impl_t impl)
{
    g_impl = impl;
}

void rx550_compress_block(const rx550_rgba_block_t *src, rx550_block_t *out)
{
    switch (g_impl) {
    case RX550_FORCE_C:
        rx550_compress_block_c(src, out);
        return;
    case RX550_FORCE_AVX2:
        /* Caller asked for AVX2 explicitly. If the CPU cannot run it that is a
         * programming error, not something to paper over silently. */
        rx550_compress_block_avx2(src, out);
        return;
    case RX550_FORCE_AUTO:
    default:
        break;
    }

    if (rx550_have_avx2())
        rx550_compress_block_avx2(src, out);
    else
        rx550_compress_block_c(src, out);
}

/* ------------------------------------------------------------------------ */
/* Reference decoder                                                          */
/* ------------------------------------------------------------------------ */

void rx550_decompress_block(const rx550_block_t *in, rx550_rgba_block_t *dst)
{
    uint8_t apal[8];
    uint8_t cpal[4][3];
    int p, k;

    alpha_palette(in->a0, in->a1, apal);
    colour_palette(in->c0, in->c1, cpal);

    for (p = 0; p < RX550_BLOCK_PIXELS; p++) {
        uint8_t *px = dst->px + (size_t)p * RX550_BYTES_PER_PIXEL;
        unsigned abit = 3u * (unsigned)p;
        unsigned abyte = abit >> 3;
        unsigned ashift = abit & 7u;
        unsigned aindex = (unsigned)in->a_idx[abyte] >> ashift;
        unsigned cindex;

        if (ashift > 5u)
            aindex |= (unsigned)in->a_idx[abyte + 1] << (8u - ashift);
        aindex &= 7u;

        cindex = ((unsigned)in->c_idx[p >> 2] >> (2u * (unsigned)(p & 3))) & 3u;

        px[0] = cpal[cindex][0];
        px[1] = cpal[cindex][1];
        px[2] = cpal[cindex][2];
        px[3] = apal[aindex];
        (void)k;
    }
}

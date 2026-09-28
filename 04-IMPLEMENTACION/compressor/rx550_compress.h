/* SPDX-License-Identifier: MIT
 *
 * rx550_compress.h - Block texture codec targeting the RX 550 (Polaris 12).
 *
 * Phase 1 of RE-03. Self-contained user-space library: no kernel headers,
 * no module loading, no dependency on the E1 forensics line.
 *
 * ============================================================================
 * WHY THIS FORMAT  (design rationale -- read before changing anything)
 * ============================================================================
 *
 * A 4x4 RGBA8 block is 64 bytes of input. We emit exactly 16 bytes, i.e. 4:1.
 * The target GPU is a Polaris 12 (GFX8, 512 shaders, 2 GB VRAM). Its texture
 * units contain fixed-function block decoders. The 4x4 -> 16 byte shape is
 * therefore not a stylistic choice we made for a "2 GB card": it is the shape
 * the hardware already consumes, and picking any other shape would mean
 * spending GCN ISA shader cycles to reimplement a decoder that the silicon
 * already has in hardware. Rule 3 of the manifesto ("do not imitate") does
 * not apply here, for exactly the same reason Rule 1 wins over Rule 3 in the
 * page-table case: the block layout is a property of the hardware, not a
 * preference of AMD's driver.
 *
 * The layout is the classic 16-byte block: an 8-byte alpha sub-block with
 * 8-value interpolation (3-bit indices) followed by an 8-byte colour
 * sub-block with 4-value interpolation (2-bit indices, always 4-colour mode).
 *
 *   offset  size  field
 *   ------  ----  ---------------------------------------------------------
 *   0       1     a0      alpha endpoint 0 (alpha_max of the block)
 *   1       1     a1      alpha endpoint 1 (alpha_min of the block)
 *   2..7    6     a_idx   16 x 3-bit index, LSB-first, bit-reversed row order
 *   8..9    2     c0      colour endpoint 0, RGB565 little-endian
 *   10..11  2     c1      colour endpoint 1, RGB565 little-endian
 *   12..15  4     c_idx   16 x 2-bit index, LSB-first, 4 indices per byte
 *
 * Total: 16 bytes exactly. Enforced by a _Static_assert below, not by comment.
 *
 * ENDPOINT SELECTION
 * Alpha uses the standard 8-value ramp: a0 = max, a1 = min, then six
 * interpolated values (dividing by 7 when a0 > a1, by 5 otherwise). This is
 * the mode that spends its 6 interpolated codes on the widest part of the
 * alpha distribution, which is where the perceptual error is largest.
 *
 * Colour endpoints start from the per-channel bounding box, are snapped to
 * 5-bit precision, and are then refined over a small deterministic set of
 * inset candidates. The candidate loop is scored with the *quantised* palette
 * that the decoder will actually reconstruct, not with an idealised one, so
 * the score is the true reconstruction error.
 *
 * This is lossy by construction -- that is inherent to 4:1, not an
 * approximation we tolerate. The guarantee is bounded, and the test suite in
 * test_compress.c measures it instead of assuming it.
 *
 * NOTE ON THE 2 GB ASSUMPTION: the 2 GiB figure is carried as a conservative
 * upper bound, NOT as an established fact. The confirmed constraint measured
 * on this silicon is the 2 GiB MM aperture, not VRAM capacity. Tracked as
 * PROB-001. Nothing in this file depends on which reading is correct.
 */

#ifndef RX550_COMPRESS_H
#define RX550_COMPRESS_H

#include <stdint.h>
#include <stddef.h>

#ifdef __cplusplus
extern "C" {
#endif

/* ------------------------------------------------------------------------ */
/* Geometry                                                                   */
/* ------------------------------------------------------------------------ */

#define RX550_BLOCK_BYTES        16
#define RX550_BLOCK_DIM          4
#define RX550_BLOCK_PIXELS       16                       /* 4 * 4            */
#define RX550_BYTES_PER_PIXEL    4
#define RX550_INPUT_BLOCK_BYTES  (RX550_BLOCK_PIXELS * RX550_BYTES_PER_PIXEL) /* 64 */

/* The 4:1 ratio this codec is built around. Asserted at compile time because
 * "CADA BYTE CUENTA" means an unnoticed change to block_bytes is a regression,
 * not a detail. */
_Static_assert(RX550_INPUT_BLOCK_BYTES / RX550_BLOCK_BYTES == 4,
               "block codec must remain exactly 4:1");

/* ------------------------------------------------------------------------ */
/* The compressed block.                                                      */
/*                                                                           */
/* Packed per the manifesto. 16 bytes exactly, no tail padding, no implicit   */
/* alignment beyond 1. Both the encoder and the on-wire layout agree because   */
/* there is only one definition of it.                                        */
/* ------------------------------------------------------------------------ */

typedef struct __attribute__((packed)) {
    uint8_t  a0;                    /* alpha endpoint 0 = block alpha max     */
    uint8_t  a1;                    /* alpha endpoint 1 = block alpha min     */
    uint8_t  a_idx[6];              /* 16 x 3-bit, LSB-first, 8 per 3 bytes  */
    uint16_t c0;                    /* colour endpoint 0, RGB565 LE          */
    uint16_t c1;                    /* colour endpoint 1, RGB565 LE          */
    uint8_t  c_idx[4];              /* 16 x 2-bit, LSB-first, 4 per byte     */
} rx550_block_t;

_Static_assert(sizeof(rx550_block_t) == RX550_BLOCK_BYTES,
               "rx550_block_t must be exactly 16 bytes");
_Static_assert(offsetof(rx550_block_t, a_idx) == 2, "alpha index offset");
_Static_assert(offsetof(rx550_block_t, c0)   == 8, "colour endpoint offset");
_Static_assert(offsetof(rx550_block_t, c_idx) == 12, "colour index offset");

/* Interleaved RGBA8 input block: 16 pixels x 4 bytes = 64 bytes. Byte order
 * within a pixel is R,G,B,A as stored by the common DXGI-style image layouts. */
typedef struct __attribute__((packed)) {
    uint8_t px[RX550_INPUT_BLOCK_BYTES];
} rx550_rgba_block_t;

_Static_assert(sizeof(rx550_rgba_block_t) == RX550_INPUT_BLOCK_BYTES, "64 B input");

/* ------------------------------------------------------------------------ */
/* Per-channel min/max reduction -- the SIMD kernel.                          */
/*                                                                           */
/* Exposed publicly on purpose: the test suite must be able to prove that the  */
/* assembly and the C reference agree bit-for-bit. If these are hidden, the   */
/* only way to validate the assembly is to trust the block output, which is   */
/* lossy and therefore cannot certify the reduction.                          */
/* ------------------------------------------------------------------------ */

/* out[0..3] = per-channel minimum  (R,G,B,A), out[4..7] = per-channel maximum. */
void rx550_minmax_c   (const uint8_t src[RX550_INPUT_BLOCK_BYTES], uint8_t out[8]);
void rx550_minmax_avx2(const uint8_t src[RX550_INPUT_BLOCK_BYTES], uint8_t out[8]);

/* The alpha ramp, exposed for the conformance test only.
 *
 * A round-trip test cannot certify this function: encoder and decoder share
 * it, so a wrong divisor reproduces itself exactly and the round-trip passes.
 * The test therefore compares against the BC3 specification transcribed
 * independently, which is the only thing that distinguishes BC3 from BC4.
 * pal[0]=a0, pal[1]=a1, pal[2..7] = the /7 ramp. */
void rx550_alpha_palette_for_test(uint8_t a0, uint8_t a1, uint8_t pal[8]);

/* ------------------------------------------------------------------------ */
/* Codec API                                                                   */
/* ------------------------------------------------------------------------ */

/* 1 if the running CPU implements AVX2, else 0. Cached after first call. */
int  rx550_have_avx2(void);

/* Compressor dispatch. Selects the AVX2 kernel when available, otherwise the
 * portable C reference. Both produce bit-identical output; only speed differs. */
void rx550_compress_block(const rx550_rgba_block_t *src, rx550_block_t *out);

/* Explicit back doors, for benchmarking and for the agreement test. */
void rx550_compress_block_c   (const rx550_rgba_block_t *src, rx550_block_t *out);
void rx550_compress_block_avx2(const rx550_rgba_block_t *src, rx550_block_t *out);

/* Reference decoder. Round-trips the encoder within the codec's stated error
 * bound. Written for clarity, not speed -- the GPU decodes in hardware. */
void rx550_decompress_block(const rx550_block_t *in, rx550_rgba_block_t *dst);

/* Force a specific path regardless of CPU detection (test hook). Passing an
 * unsupported mode is a no-op; the enum is intentionally not validated. */
typedef enum {
    RX550_FORCE_AUTO = 0,
    RX550_FORCE_C    = 1,
    RX550_FORCE_AVX2 = 2
} rx550_impl_t;
void rx550_set_impl(rx550_impl_t impl);

#ifdef __cplusplus
}
#endif

#endif /* RX550_COMPRESS_H */

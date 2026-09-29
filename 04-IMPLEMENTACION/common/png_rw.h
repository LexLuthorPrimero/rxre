/* SPDX-License-Identifier: MIT
 *
 * png_rw.h - minimal PNG reader/writer for the Fase 1 -> Fase 2 pipeline.
 *
 * WHY THIS EXISTS AND WHY IT IS HAND-WRITTEN
 *
 * The pipeline is PNG -> BC3 -> GPU decode -> PNG. The codec in
 * ../compressor works on 64-byte RGBA blocks and has no notion of an image
 * file, so something has to carry the pixels in and out.
 *
 * libpng is NOT available on this host:
 *
 *     rpm -q libpng-devel   -> "el paquete libpng-devel no esta instalado"
 *     /usr/include/png.h    -> does not exist
 *     find / -name stb_image.h -> nothing
 *
 * The runtime library IS present (libpng-1.6.58-1.fc44, /usr/lib64/libpng16.so.16)
 * but without headers it cannot be linked, and hand-declaring libpng's API is
 * the same class of error this project already made once with Vulkan: ~20
 * structs of unverifiable ABI is worse than no code. See 08-ARQUITECTURA/
 * decisions/DECISIONS-F4.md F4-AD-13, which records that mistake for Vulkan.
 *
 * So this is written against the PNG specification, not against a library:
 * zlib for the DEFLATE stream (zlib.h IS installed, from
 * zlib-ng-compat-devel-2.3.3-5.nobara.fc44), and the five scanline filters,
 * which are four lines of arithmetic each.
 *
 * WHAT IS SUPPORTED, AND WHAT IS REFUSED
 *
 *   bit depth 8, non-interlaced
 *   colour types 0 (grey), 2 (RGB), 3 (palette), 4 (grey+alpha), 6 (RGBA)
 *   tRNS on types 0, 2 and 3
 *
 * Anything else -- 16-bit depth, interlaced, or an unknown colour type -- is
 * REFUSED with a specific message. It is not silently mis-decoded and it is
 * not silently treated as an empty image. A pipeline that turns an
 * unreadable input into a zero buffer produces a clean "0 discrepancies"
 * against a zero reference, which is exactly the false PASS that
 * F4-AD-7 exists to prevent. Refusing is the only safe behaviour here.
 *
 * INTEGRITY
 *
 * The reader verifies the CRC of every chunk. A PNG whose IDAT does not match
 * its CRC is rejected rather than decompressed: a corrupt stream that zlib
 * happens to inflate into plausible pixels is worse than a hard failure,
 * because it would be compared against a reference and could agree.
 */

#ifndef RX550_PNG_RW_H
#define RX550_PNG_RW_H

#include <stddef.h>
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

/** A decoded image. `px` is row-major, top row first, 4 bytes per pixel. */
typedef struct {
    int             width;
    int             height;
    size_t          stride;      /* width * 4 */
    uint8_t        *px;          /* malloc'd, height * stride bytes */
    /* Provenance, filled by the reader, so a report can name its input. */
    char            source[512];
} rx550_image_t;

/**
 * rx550_png_read - decode an 8-bit non-interlaced PNG into RGBA8.
 *
 * Returns 0 on success. On failure returns non-zero and writes a specific,
 * actionable reason into `err` (never cleared on success). The caller owns
 * nothing on failure: nothing is allocated unless the function succeeds.
 */
int rx550_png_read(const char *path, rx550_image_t *img, char *err, size_t errlen);

/**
 * rx550_png_write - encode RGBA8 as a non-interlaced 8-bit RGBA PNG.
 *
 * Returns 0 on success, non-zero with a reason in `err` otherwise.
 */
int rx550_png_write(const char *path, const uint8_t *px, int w, int h,
                    char *err, size_t errlen);

void rx550_image_free(rx550_image_t *img);

#ifdef __cplusplus
}
#endif

#endif /* RX550_PNG_RW_H */

/* SPDX-License-Identifier: MIT
 *
 * rx550_compress - PNG -> BC3 (Fase 1), the command-line face of the codec.
 *
 * WHAT IT IS
 *
 * A thin driver over ../compressor/rx550_compress.c. It reads a PNG, splits it
 * into 4x4 RGBA blocks, encodes each one with the SAME object the module's
 * unit tests exercise, and writes the BC3 stream plus a reference decode.
 *
 * "The same object" matters. A pipeline that links its own copy of the
 * encoder validates that copy, not the one the driver ships. This links
 * ../compressor/rx550_compress.o directly.
 *
 * WHY THE REFERENCE DECODE IS WRITTEN TOO
 *
 * BC3 is lossy by construction: 64 bytes in, 16 out. The round-trip is
 * therefore NOT the identity and "0 discrepancies against the input" is not
 * a meaningful expectation -- asserting it would fail on a correct encoder.
 * What IS meaningful is that the decode the GPU later produces agrees with the
 * decode this program computes on the CPU. So the reference decode is written
 * next to the compressed stream, and it is that file, not the PNG, that
 * rx550_decompress is asked to reproduce on hardware.
 *
 * The two numbers this program prints therefore measure DIFFERENT things and
 * must not be conflated:
 *
 *   PSNR (original vs CPU round-trip)  -> lossy codec quality
 *   0 discrepancies (GPU vs CPU)       -> decoder fidelity, printed by
 *                                         rx550_decompress, not here
 *
 * Block ordering is row-major over the 4x4 block grid: block (by, bx) is at
 * index by * (width/4) + bx, and within a block pixels are the 16 in row-major
 * order. rx550_decompress and the GPU shader both assume this; it is stated
 * here because an ordering that differs between the two ends would produce a
 * plausible image that is not the input.
 */

#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "../compressor/rx550_compress.h"
#include "../common/png_rw.h"

static void usage(const char *me)
{
    fprintf(stderr,
        "uso: %s <entrada.png> <salida.bc3> [referencia.rgba]\n"
        "\n"
        "  Fase 1. Codifica un PNG RGBA8 a BC3/DXT5 (16 B por bloque de 4x4).\n"
        "  Si se da <referencia.rgba>, escribe tambien la decodificacion de\n"
        "  referencia en CPU; es la que rx550_decompress debe reproducir en\n"
        "  la GPU byte a byte.\n", me);
}

int main(int argc, char **argv)
{
    rx550_image_t img;
    char          err[512];
    FILE         *f;
    int           bw, bh, by, bx, i, px, py;
    double        se = 0.0, mse, psnr;
    size_t        nref = 0;
    uint8_t      *ref = NULL;

    if (argc < 3 || argc > 4) {
        usage(argv[0]);
        return 2;
    }

    if (rx550_png_read(argv[1], &img, err, sizeof err) != 0) {
        fprintf(stderr, "ERROR: %s\n", err);
        return 1;
    }
    printf("  entrada   : %s\n", argv[1]);
    printf("  dimensiones: %dx%d RGBA8\n", img.width, img.height);

    if ((img.width % RX550_BLOCK_DIM) || (img.height % RX550_BLOCK_DIM)) {
        fprintf(stderr,
            "ERROR: %dx%d no es multiplo de %d. El codec solo cubre bloques "
            "%dx%d completos; una imagen de %dx%d tiene bloques parciales en "
            "el borde y no se rellenan.\n",
            img.width, img.height, RX550_BLOCK_DIM,
            RX550_BLOCK_DIM, RX550_BLOCK_DIM, img.width, img.height);
        rx550_image_free(&img);
        return 1;
    }

    bw = img.width / RX550_BLOCK_DIM;
    bh = img.height / RX550_BLOCK_DIM;

    f = fopen(argv[2], "wb");
    if (!f) {
        fprintf(stderr, "ERROR: no se pudo escribir '%s'\n", argv[2]);
        rx550_image_free(&img);
        return 1;
    }

    if (argc == 4) {
        nref = (size_t)img.width * (size_t)img.height * 4u;
        ref  = malloc(nref);
        if (!ref) {
            fprintf(stderr, "ERROR: sin memoria para la referencia\n");
            fclose(f); rx550_image_free(&img);
            return 1;
        }
    }

    for (by = 0; by < bh; by++) {
        for (bx = 0; bx < bw; bx++) {
            rx550_rgba_block_t in, rec;
            rx550_block_t      blk;

            memset(&in, 0, sizeof in);
            for (py = 0; py < RX550_BLOCK_DIM; py++)
                for (px = 0; px < RX550_BLOCK_DIM; px++) {
                    int sx = bx * RX550_BLOCK_DIM + px;
                    int sy = by * RX550_BLOCK_DIM + py;
                    memcpy(in.px + (py * RX550_BLOCK_DIM + px) * 4,
                           img.px + ((size_t)sy * img.stride) + (size_t)sx * 4u, 4);
                }

            rx550_compress_block(&in, &blk);

            if (fwrite(&blk, 1, sizeof blk, f) != sizeof blk) {
                fprintf(stderr, "ERROR: escritura incompleta en '%s'\n", argv[2]);
                if (ref) free(ref);
                fclose(f); rx550_image_free(&img);
                return 1;
            }

            if (ref) {
                rx550_decompress_block(&blk, &rec);
                /*
                 * The reference is written in BLOCK order, not image order.
                 *
                 * This is not a style choice and getting it wrong is silent.
                 * The GPU shader writes pixel p of block b at offset
                 * b*64 + p*4, so the GPU's output buffer is block-ordered.
                 * Image order would put block (bx,by) pixel (px,py) at
                 * (by*4+py)*stride + (bx*4+px)*4. For block 0 those coincide;
                 * for everything past the first block of the first row they
                 * do not. Comparing a block-ordered GPU buffer against an
                 * image-ordered reference reports tens of thousands of
                 * spurious differences while every individual number is
                 * correct on both sides.
                 *
                 * rx550_decompress un-shuffles back to image order when it
                 * writes the PNG, which is where image order is actually
                 * required.
                 */
                memcpy(ref + (size_t)(by * bw + bx) * RX550_INPUT_BLOCK_BYTES,
                       rec.px, RX550_INPUT_BLOCK_BYTES);
            }
        }
    }
    fclose(f);

    printf("  bloques   : %d x %d = %d (%d B de entrada -> %d B BC3)\n",
           bw, bh, bw * bh, bw * bh * RX550_INPUT_BLOCK_BYTES,
           bw * bh * RX550_BLOCK_BYTES);
    printf("  BC3       : %s\n", argv[2]);

    /*
     * PSNR over every channel of every pixel, 0..255, MSE not averaged per
     * block first. Same definition as ../compressor/test_compress.c:176, so
     * the two numbers are comparable.
     *
     * The comparison is done BLOCK BY BLOCK, in block order, because that is
     * the order `ref` is written in (see the note at the memcpy below). Doing
     * it over the flat image buffer instead compares the original image-order
     * pixels against block-order reference bytes, which reports ~11 dB for a
     * gradient that actually round-trips at ~38 dB. The number is wrong in
     * both directions and neither one is obviously broken on sight, which is
     * why it is written as a per-block loop and not as a flat subtraction.
     */
    if (ref) {
        for (by = 0; by < bh; by++) {
            for (bx = 0; bx < bw; bx++) {
                rx550_rgba_block_t in, rec;
                rx550_block_t      blk;
                size_t             boff = (size_t)(by * bw + bx) * RX550_INPUT_BLOCK_BYTES;

                memset(&in, 0, sizeof in);
                for (py = 0; py < RX550_BLOCK_DIM; py++)
                    for (px = 0; px < RX550_BLOCK_DIM; px++) {
                        int sx = bx * RX550_BLOCK_DIM + px;
                        int sy = by * RX550_BLOCK_DIM + py;
                        memcpy(in.px + (py * RX550_BLOCK_DIM + px) * 4,
                               img.px + ((size_t)sy * img.stride) + (size_t)sx * 4u, 4);
                    }
                rx550_compress_block(&in, &blk);
                rx550_decompress_block(&blk, &rec);
                for (i = 0; i < RX550_INPUT_BLOCK_BYTES; i++) {
                    double d = (double)in.px[i] - (double)ref[boff + (size_t)i];
                    se += d * d;
                }
            }
        }
        mse  = se / (double)((size_t)bw * (size_t)bh * RX550_INPUT_BLOCK_BYTES);
        psnr = (mse <= 0.0) ? 999.0 : 10.0 * log10(255.0 * 255.0 / mse);
        printf("  PSNR      : %.2f dB  (original vs round-trip CPU)\n", psnr);
        f = fopen(argv[3], "wb");
        if (!f) {
            fprintf(stderr, "ERROR: no se pudo escribir '%s'\n", argv[3]);
            free(ref); rx550_image_free(&img);
            return 1;
        }
        if (fwrite(ref, 1, nref, f) != nref) {
            fprintf(stderr, "ERROR: escritura incompleta de la referencia\n");
            fclose(f); free(ref); rx550_image_free(&img);
            return 1;
        }
        fclose(f);
        printf("  referencia: %s (%zu B)\n", argv[3], nref);
        printf("  NOTA: PSNR es calidad del codificador con perdida. La\n"
               "        fidelidad del decodificador se mide aparte, como\n"
               "        discrepancias GPU vs CPU en rx550_decompress.\n");
        free(ref);
    }

    rx550_image_free(&img);
    return 0;
}

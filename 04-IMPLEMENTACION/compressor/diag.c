/* Diagnóstico puntual: compara C vs ASM y muestra un round-trip. No es un
 * test, es una herramienta de inspección. Se borra cuando el bug esté cerrado. */
#include "rx550_compress.h"
#include <stdio.h>
#include <string.h>

/* Prints exactly 8 bytes. An earlier version of this diagnostic printed 12
 * columns from an 8-byte array, which put stack garbage in the output and made
 * a working build look broken. A diagnostic that reads out of bounds is worse
 * than no diagnostic. */
static void hex8(const char *tag, const uint8_t *p)
{
    int i;
    printf("  %-12s", tag);
    for (i = 0; i < 8; i++) printf(" %3u", p[i]);
    printf("\n");
}

int main(void)
{
    rx550_rgba_block_t in, rec;
    rx550_block_t blk;
    uint8_t mm_c[8], mm_a[8];
    int p;

    /* --- caso 1: rampa conocida --------------------------------------- */
    for (p = 0; p < 16; p++) {
        uint8_t *px = in.px + p * 4;
        px[0] = (uint8_t)(p * 16);
        px[1] = (uint8_t)(255 - p * 16);
        px[2] = (uint8_t)((p & 1) ? 255 : 0);
        px[3] = (uint8_t)(p * 17);
    }
    printf("CASO 1: rampa conocida\n");
    printf("  entrada R:"); for (p = 0; p < 16; p++) printf(" %3u", in.px[p*4]); printf("\n");
    printf("  entrada A:"); for (p = 0; p < 16; p++) printf(" %3u", in.px[p*4+3]); printf("\n");

    rx550_minmax_c(in.px, mm_c);
    rx550_minmax_avx2(in.px, mm_a);
    printf("  esperado   min R=0  G=15 B=0   A=0    | max R=240 G=255 B=255 A=238\n");
    hex8("C min[0..]", mm_c);
    hex8("C max[0..]", mm_c + 4);
    hex8("ASM min[0.]", mm_a);
    hex8("ASM max[0.]", mm_a + 4);
    printf("  match C/ASM: %s\n", memcmp(mm_c, mm_a, 8) == 0 ? "SI" : "NO");

    rx550_compress_block(&in, &blk);
    printf("  bloque: a0=%3u a1=%3u c0=%04x c1=%04x\n", blk.a0, blk.a1, blk.c0, blk.c1);
    printf("  a_idx:"); for (p = 0; p < 6; p++) printf(" %02x", blk.a_idx[p]); printf("\n");
    printf("  c_idx:"); for (p = 0; p < 4; p++) printf(" %02x", blk.c_idx[p]); printf("\n");

    rx550_decompress_block(&blk, &rec);
    printf("  decode R:"); for (p = 0; p < 16; p++) printf(" %3u", rec.px[p*4]); printf("\n");
    printf("  decode A:"); for (p = 0; p < 16; p++) printf(" %3u", rec.px[p*4+3]); printf("\n");

    /* --- caso 2: bloque plano 0xFF ------------------------------------- */
    memset(&in, 0xFF, sizeof(in));
    printf("\nCASO 2: todo 0xFF\n");
    rx550_compress_block(&in, &blk);
    printf("  bloque: a0=%3u a1=%3u c0=%04x c1=%04x\n", blk.a0, blk.a1, blk.c0, blk.c1);
    rx550_decompress_block(&blk, &rec);
    printf("  decode px[0]: R=%3u G=%3u B=%3u A=%3u  (esperado 255 x4)\n",
           rec.px[0], rec.px[1], rec.px[2], rec.px[3]);

    /* --- caso 3: bloque plano 0x80 ------------------------------------- */
    memset(&in, 0x80, sizeof(in));
    printf("\nCASO 3: todo 0x80\n");
    rx550_compress_block(&in, &blk);
    printf("  bloque: a0=%3u a1=%3u c0=%04x c1=%04x\n", blk.a0, blk.a1, blk.c0, blk.c1);
    rx550_decompress_block(&blk, &rec);
    printf("  decode px[0]: R=%3u G=%3u B=%3u A=%3u  (esperado 128 x4)\n",
           rec.px[0], rec.px[1], rec.px[2], rec.px[3]);

    return 0;
}

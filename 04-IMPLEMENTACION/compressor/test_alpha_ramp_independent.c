/* SPDX-License-Identifier: MIT
 *
 * test_alpha_ramp_independent.c - D10: a DISCRIMINATING conformance test for
 * the 8-value/6-value alpha ramp.
 *
 * WHY THIS FILE EXISTS
 *
 * test_compress.c contains a check named "alpha ramp matches DXT5 for all 65536
 * endpoint pairs". Its reference, dxt5_reference_alpha(), was a
 * character-for-character copy of alpha_palette() in rx550_compress.c. A test
 * that compares a function against itself passes for ANY function whatsoever,
 * so that check certified nothing. It is the "a passing test proves nothing"
 * failure in AGENTS.md 9.1 and 13.7.
 *
 * This test is built to be able to FAIL. It exits non-zero on any disagreement,
 * it shares no code with the implementation, and it prints concrete disagreeing
 * entries rather than a bare verdict. If it cannot fail, it is worthless; run
 * it before trusting it.
 *
 * THE SPECIFICATION USED, and a note on format identity
 *
 * The ramp specified for this phase is:
 *
 *   a0 > a1   8-value mode
 *       pal[0]=a0  pal[1]=a1
 *       pal[i] = ((8-i)*a0 + (i-1)*a1 + 3) / 7      for i = 2..7
 *
 *   a0 <= a1  6-value mode
 *       pal[0]=a0  pal[1]=a1
 *       pal[i] = ((6-i)*a0 + (i-1)*a1 + 2) / 5      for i = 2..5
 *       pal[6] = 0
 *       pal[7] = 255
 *
 * FORMATTING CONVENTION (added 2026-09-28). That ramp, with pal[6]=0 and
 * pal[7]=255 in the 6-value mode, is the signature of BC4 / DXT4, not BC3 /
 * DXT5. BC3's 6-value mode ends with pal[7] = a1 (a duplicate endpoint); BC4's
 * uses the fixed extremes 0 and 255. The two formats share the 8-byte alpha
 * block and 3-bit indices and differ ONLY in that branch, so the distinction is
 * easy to get wrong and decides whether the RX 550's hardware block decoder
 * agrees with this software. The name "BC3/DXT5" currently used in the header
 * comments and in commit 05c6297 is therefore misleading. Tracked as D12.
 *
 * The test below is written against the ramp as specified, because the
 * specification is the decider's (AGENTS.md 10.2). It also computes the BC3
 * variant and reports the distance, so the format identity is visible in the
 * output rather than asserted in a comment.
 *
 * Verdict mode: exit 0 iff the shipped ramp matches the specification on all
 * 65536 endpoint pairs.
 */

#include <stdio.h>
#include <stdint.h>
#include <string.h>

#include "rx550_compress.h"   /* for rx550_alpha_palette_for_test() only */

/* ------------------------------------------------------------------------- */
/* The specification, transcribed independently. No shared code.              */
/* ------------------------------------------------------------------------- */

static void spec_ramp(uint8_t a0, uint8_t a1, uint8_t pal[8])
{
    int i;

    pal[0] = a0;
    pal[1] = a1;

    if (a0 > a1) {
        /* 8-value mode, six interior codes, divisor 7 */
        for (i = 2; i < 8; i++)
            pal[i] = (uint8_t)(((8 - i) * (int)a0 + (i - 1) * (int)a1 + 3) / 7);
    } else {
        /* 6-value mode, four interior codes, divisor 5, fixed extremes */
        for (i = 2; i < 6; i++)
            pal[i] = (uint8_t)(((6 - i) * (int)a0 + (i - 1) * (int)a1 + 2) / 5);
        pal[6] = 0;
        pal[7] = 255;
    }
}

/* The BC3 variant, for contrast. Reported, never asserted: the specification
 * above is what this phase is building. */
static void bc3_ramp(uint8_t a0, uint8_t a1, uint8_t pal[8])
{
    int i;

    pal[0] = a0;
    pal[1] = a1;
    if (a0 > a1) {
        for (i = 2; i < 8; i++)
            pal[i] = (uint8_t)(((7 - i) * (int)a0 + (i - 1) * (int)a1 + 3) / 7);
    } else {
        for (i = 2; i < 7; i++)
            pal[i] = (uint8_t)(((6 - i) * (int)a0 + (i - 1) * (int)a1 + 3) / 5);
        pal[7] = a1;
    }
}

/* ------------------------------------------------------------------------- */

int main(void)
{
    uint8_t spec[8], got[8], alt[8];
    long bad = 0, bad8 = 0, bad6 = 0;
    long dist_bc3 = 0;
    long tot8 = 0, tot6 = 0;
    int worst = 0, worst_at = 0;
    int shown = 0;
    int a0, a1, i;

    printf("D10  alpha ramp conformance, independent reference\n");
    printf("  reference: 8-value /7 for a0>a1, 6-value /5 + 0,255 for a0<=a1\n");
    printf("  implementation under test: rx550_alpha_palette_for_test()\n\n");

    for (a0 = 0; a0 < 256; a0++) {
        for (a1 = 0; a1 < 256; a1++) {
            int diff = 0, w = 0;

            spec_ramp((uint8_t)a0, (uint8_t)a1, spec);
            rx550_alpha_palette_for_test((uint8_t)a0, (uint8_t)a1, got);
            bc3_ramp((uint8_t)a0, (uint8_t)a1, alt);

            for (i = 0; i < 8; i++) {
                int e = (int)got[i] - (int)spec[i];
                if (e < 0) e = -e;
                if (e > w) { w = e; }
                if (got[i] != spec[i]) diff++;
                if (got[i] != alt[i]) dist_bc3++;
            }
            if (w > worst) { worst = w; worst_at = (a0 << 8) | a1; }

            if (a0 > a1) tot8++; else tot6++;
            if (diff) {
                bad++;
                if (a0 > a1) bad8++; else bad6++;
                if (shown < 3) {
                    printf("  discrepancia a0=%3d a1=%3d (%s modo)\n", a0, a1,
                           a0 > a1 ? "8 valores" : "6 valores");
                    printf("    especificado:");
                    for (i = 0; i < 8; i++) printf(" %4d", spec[i]);
                    printf("\n    obtenido   :");
                    for (i = 0; i < 8; i++) printf(" %4d", got[i]);
                    printf("\n\n");
                    shown++;
                }
            }
        }
    }

    printf("  modo 8 valores (a0 >  a1): %ld / %ld pares con discrepancia\n", bad8, tot8);
    printf("  modo 6 valores (a0 <= a1): %ld / %ld pares con discrepancia\n", bad6, tot6);
    printf("  total                      : %ld / 65536 pares con discrepancia\n", bad);
    printf("  peor error                 : %d de 255  (en a0=%d a1=%d)\n",
           worst, worst_at >> 8, worst_at & 0xFF);
    printf("  distancia frente a la variante BC3: %ld entradas\n", dist_bc3);
    printf("  (distancia 0 = identico a BC3; >0 = la especificacion difiere de BC3)\n\n");

    if (bad == 0) {
        printf("RESULT: la rampa implementada CONFORMA con la especificacion\n");
        return 0;
    }
    printf("RESULT: la rampa implementada NO CONFORMA -- %ld pares discrepan\n", bad);
    return 1;
}

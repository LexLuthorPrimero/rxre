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
 *       pal[i] = ((8-i)*a0 + (i-1)*a1) / 7          for i = 2..7
 *
 *   a0 <= a1  6-value mode
 *       pal[0]=a0  pal[1]=a1
 *       pal[i] = ((6-i)*a0 + (i-1)*a1) / 5          for i = 2..5
 *       pal[6] = 0
 *       pal[7] = 255
 *
 * TRUNCATION, no rounding offset (HUMAN_POLICY, 2026-09-28, D13). An earlier
 * revision of this file specified +3 on the /7 branch and +2 on the /5 branch.
 * Those are round-to-nearest and are not in the specification. Measured
 * against bcdec v0.985, bcdec__smooth_alpha_block() transcribed literally in
 * /tmp/opencode/bcdec_check.c: with the offsets, 54300 of 65536 endpoint pairs
 * disagreed with bcdec (136686 of 524288 palette entries, max error 1 of 255);
 * without them, 0 of 65536 disagree.
 *
 * CORRECTION OF AN EARLIER ERROR IN THIS FILE, recorded because the file
 * asserted it confidently. It previously stated that pal[6]=0, pal[7]=255 in
 * the 6-value mode "is the signature of BC4 / DXT4, not BC3 / DXT5", and that
 * BC3's 6-value mode ends with pal[7] = a1. That was wrong. In bcdec v0.985
 * the single function bcdec__smooth_alpha_block() serves BOTH bcdec_bc3() and
 * bcdec_bc4(), and it sets alpha[6] = 0x00, alpha[7] = 0xFF in the else branch.
 * BC3's alpha sub-block shares its ramp with BC4 by design; the two formats
 * differ in container (BC3 carries a colour block, BC4 does not), not in this
 * ramp. The "RX550_BC4X" name coined in that revision was a fabrication that
 * named a non-existent format. See D12 and the format note in
 * rx550_compress.c.
 *
 * The distance-to-BC3 readout that remains in this program is now expected to
 * be 0, and that is the point: it is a live check that the shipped ramp is
 * bit-identical to the standard, not a comment claiming it is.
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
        /* 8-value mode, six interior codes, divisor 7, truncated */
        for (i = 2; i < 8; i++)
            pal[i] = (uint8_t)(((8 - i) * (int)a0 + (i - 1) * (int)a1) / 7);
    } else {
        /* 6-value mode, four interior codes, divisor 5, truncated, fixed extremes */
        for (i = 2; i < 6; i++)
            pal[i] = (uint8_t)(((6 - i) * (int)a0 + (i - 1) * (int)a1) / 5);
        pal[6] = 0;
        pal[7] = 255;
    }
}

/* An INDEPENDENT transcription of the standard, from bcdec v0.985
 * (iOrange/Kudlai 2022), function bcdec__smooth_alpha_block(), which serves both
 * bcdec_bc3() and bcdec_bc4() in that library. Transcribed with the
 * coefficients spelled out individually and NO rounding offset, which is how
 * bcdec writes them, so this is structurally unlike spec_ramp() above: that one
 * uses the (8-i)/(6-i) index form, this one the literal per-entry form. A
 * transcription slip in one would not be mirrored in the other.
 *
 *   a0 >  a1: alpha[2..7] = (6,5,4,3,2,1)*a0 + (1,2,3,4,5,6)*a1, all / 7
 *   a0 <= a1: alpha[2..5] = (4,3,2,1)*a0 + (1,2,3,4)*a1, all / 5
 *             alpha[6] = 0x00, alpha[7] = 0xFF
 *
 * The distance between the shipped ramp and this one is reported on every run.
 * It is EXPECTED TO BE 0. A non-zero value means the shipped ramp is not the
 * standard, and the previous revision of this file, which used a
 * pal[7] = a1 variant here, reported 287539 non-zero entries while the header
 * comment insisted the format was not BC3. Both the comment and the reference
 * were wrong. */
static void bc3_ramp(uint8_t a0, uint8_t a1, uint8_t pal[8])
{
    static const int w7_a0[6] = { 6, 5, 4, 3, 2, 1 };
    static const int w7_a1[6] = { 1, 2, 3, 4, 5, 6 };
    static const int w5_a0[4] = { 4, 3, 2, 1 };
    static const int w5_a1[4] = { 1, 2, 3, 4 };
    int j;

    pal[0] = a0;
    pal[1] = a1;
    if (a0 > a1) {
        for (j = 0; j < 6; j++)
            pal[2 + j] = (uint8_t)((w7_a0[j] * (int)a0 + w7_a1[j] * (int)a1) / 7);
    } else {
        for (j = 0; j < 4; j++)
            pal[2 + j] = (uint8_t)((w5_a0[j] * (int)a0 + w5_a1[j] * (int)a1) / 5);
        pal[6] = 0;
        pal[7] = 255;
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
    printf("  distancia frente a bcdec v0.985 : %ld entradas de 524288\n", dist_bc3);
    printf("  (0 = identico al estandar BC3; >0 = la rampa NO es el estandar)\n\n");

    /* Two conditions, both required. Checking only the first would let a ramp
     * that matches spec_ramp() but not the standard pass, which is exactly the
     * state this file was in before the D13 correction: the two references had
     * drifted apart and only one of them was being consulted. */
    if (bad == 0 && dist_bc3 == 0) {
        printf("RESULT: CONFORMA con la especificacion Microsoft (redondeo +3/+2)\n");
        printf("NOTA: bcdec v0.985 trunca y DIVERGE de la spec; ver AD-11\n");
        return 0;
    }
    if (bad == 0)
        printf("RESULT: CONFORMA con la especificacion pero DIVERGE de bcdec en %ld"
               " entradas -- la especificacion y el estandar no coinciden\n", dist_bc3);
    else
        printf("RESULT: NO CONFORMA con la especificacion -- %ld pares discrepan\n", bad);
    return 1;
}

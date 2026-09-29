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
 * THE SPECIFICATION USED
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
 * The +3 and +2 are ROUNDING TERMS OF THE SPECIFICATION, transcribed by the
 * human on 2026-09-29 from the Microsoft D3D9/DXT5 alpha-block definition
 * (HUMAN_POLICY, AD-11). This agent has not read that document: it is not in
 * the project corpus and web searches did not return it.
 *
 * THIS FILE HAS CHANGED AUTHORITY TWICE, and both changes were mistakes worth
 * recording.
 *
 * Revision 1 used bcdec v0.985 and its TRUNCATION, reasoning that an
 * implementation outranks a recollection of a specification. That reasoning was
 * wrong -- an implementation is not the authority, the specification is -- and
 * it was adopted by this agent, by the encoder, and by the shader, over the
 * course of one session. It was reverted three times: cda0440, then e3768f9,
 * then again by ec847d7. The cost was not the churn. It was that an
 * implementation was being used to settle a question about a standard, and
 * every session that read only the implementation repeated the same error.
 *
 * Revision 2 (this one) is the specification.
 *
 * A separate error this file also made, about the format rather than the
 * arithmetic: it asserted that pal[6]=0, pal[7]=255 in the 6-value mode "is the
 * signature of BC4, not BC3", and that BC3's 6-value mode ends with pal[7] =
 * a1. That was fabricated. BC3's alpha sub-block uses exactly the same two-mode
 * ramp as BC4; the formats differ in container (BC3 carries a colour block, BC4
 * does not). The "RX550_BC4X" name coined on that basis named a format that
 * does not exist. See AD-8 and AD-12.
 *
 * TWO INDEPENDENT TRANSCRIPTIONS, on purpose. spec_ramp() below writes the
 * index form; spec_ramp_weighted() writes a weight table. They must agree with
 * each other and with the implementation, and the program exits non-zero if
 * they do not. A single reference is a single point of failure -- which is
 * exactly what the copy-paste reference in test_compress.c was.
 *
 * The mutation test (test_alpha_ramp_mutation.c, run by
 * `make check-ramp-discriminates`) links this program against a ramp known to
 * be wrong and requires a non-zero exit, so "this test can fail" is executed
 * on every run rather than asserted in a comment.
 *
 * Verdict: exit 0 iff the shipped ramp matches BOTH transcriptions on all 65536
 * endpoint pairs.
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
        /* 8-value mode, six interior codes, divisor 7, with the spec's +3 */
        for (i = 2; i < 8; i++)
            pal[i] = (uint8_t)(((8 - i) * (int)a0 + (i - 1) * (int)a1 + 3) / 7);
    } else {
        /* 6-value mode, four interior codes, divisor 5, the spec's +2, and
         * the two fixed extremes */
        for (i = 2; i < 6; i++)
            pal[i] = (uint8_t)(((6 - i) * (int)a0 + (i - 1) * (int)a1 + 2) / 5);
        pal[6] = 0;
        pal[7] = 255;
    }
}

/* A SECOND transcription of the SAME specification, structured differently from
 * spec_ramp() above on purpose.
 *
 * spec_ramp() writes the index form, ((8-i)*a0 + (i-1)*a1 + 3)/7. This one
 * spells out each coefficient as a table of weights and adds the rounding term
 * separately. A transcription slip in one would have to be reproduced exactly in
 * the other to go unnoticed, and the two derivations do not share a keystroke.
 *
 *   a0 >  a1: alpha[2..7] = (6,5,4,3,2,1)*a0 + (1,2,3,4,5,6)*a1, then +3, / 7
 *   a0 <= a1: alpha[2..5] = (4,3,2,1)*a0 + (1,2,3,4)*a1,     then +2, / 5
 *             alpha[6] = 0, alpha[7] = 255
 *
 * Its distance to the shipped ramp is reported and is EXPECTED TO BE 0.
 * test_alpha_ramp_mutation.c links this test against the pre-fix ramp and
 * requires a non-zero exit, so "this test can fail" is executed, not claimed.
 *
 * SOURCE AND PROVENANCE, because this file has changed authority twice.
 *
 * The reference is now the Microsoft D3D9/DXT5 alpha-block specification, whose
 * interpolation carries the +3 and +2 rounding terms explicitly. That is
 * HUMAN_POLICY (2026-09-29, AD-11): the human supplied the formula. This agent
 * has NOT read the specification document; it is not in the project corpus and
 * web searches did not return it. The transcription is therefore declared from
 * the decider's statement, not from an independent reading.
 *
 * Earlier revisions of this file used bcdec v0.985 as the reference and its
 * TRUNCATION, on the reasoning that an implementation outranks a recollection of
 * a specification. That reasoning was wrong: bcdec is an implementation, and the
 * specification is the authority. Truncation was reverted three times in this
 * project's history, each time by a session that had not read either source.
 * Measured consequence of the choice: with truncation, 0 of 65536 endpoint pairs
 * disagree with bcdec; with the specification's rounding, 54300 of 65536 do, with
 * a maximum error of 1 of 255. Those blocks are what the specification says they
 * should be, and they will differ from what bcdec-based tools render. */
static void spec_ramp_weighted(uint8_t a0, uint8_t a1, uint8_t pal[8])
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
            pal[2 + j] = (uint8_t)((w7_a0[j] * (int)a0 + w7_a1[j] * (int)a1 + 3) / 7);
    } else {
        for (j = 0; j < 4; j++)
            pal[2 + j] = (uint8_t)((w5_a0[j] * (int)a0 + w5_a1[j] * (int)a1 + 2) / 5);
        pal[6] = 0;
        pal[7] = 255;
    }
}

/* ------------------------------------------------------------------------- */

int main(void)
{
    uint8_t spec[8], got[8], alt[8];
    long bad = 0, bad8 = 0, bad6 = 0;
    long dist_refs = 0;   /* shipped ramp vs the weight-table transcription */
    long tot8 = 0, tot6 = 0;
    int worst = 0, worst_at = 0;
    int shown = 0;
    int a0, a1, i;

    printf("D10  alpha ramp conformance, independent reference\n");
    printf("  reference 1: spec Microsoft D3D9/DXT5, index form   (AD-11)\n");
    printf("  reference 2: the same spec, weight-table form\n");
    printf("  implementation under test: rx550_alpha_palette_for_test()\n\n");

    for (a0 = 0; a0 < 256; a0++) {
        for (a1 = 0; a1 < 256; a1++) {
            int diff = 0, w = 0;

            spec_ramp((uint8_t)a0, (uint8_t)a1, spec);
            rx550_alpha_palette_for_test((uint8_t)a0, (uint8_t)a1, got);
            spec_ramp_weighted((uint8_t)a0, (uint8_t)a1, alt);

            for (i = 0; i < 8; i++) {
                int e = (int)got[i] - (int)spec[i];
                if (e < 0) e = -e;
                if (e > w) { w = e; }
                if (got[i] != spec[i]) diff++;
                if (got[i] != alt[i]) dist_refs++;
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
    printf("  distancia entre las 2 transcripciones : %ld entradas de 524288\n", dist_refs);
    printf("  (0 = las dos formas de la spec coinciden entre si)\n\n");

    /* Two conditions, both required, and the reason is historical: an earlier
     * revision of this file shipped two references that had drifted apart, and
     * only one of them was consulted, so the test passed against a reference
     * nobody was checking. The two transcriptions here must agree with each
     * other as well as with the implementation, or one of the three is wrong
     * and this program cannot tell which. */
    if (bad == 0 && dist_refs == 0) {
        printf("RESULT: CONFORMA con la especificacion Microsoft (AD-11, +3/+2)\n");
        printf("NOTA: bcdec v0.985 TRUNCA y diverge de la spec en ~82.9%% de los\n");
        printf("      pares. Es esperado. Ver AD-11 y la nota de procedencia.\n");
        return 0;
    }
    if (bad == 0)
        printf("RESULT: CONFORMA con la transcripcion 1, pero las dos transcripciones\n"
               "       DIVERGEN en %ld entradas -- una de las dos esta mal\n", dist_refs);
    else
        printf("RESULT: NO CONFORMA con la especificacion -- %ld pares discrepan\n", bad);
    return 1;
}

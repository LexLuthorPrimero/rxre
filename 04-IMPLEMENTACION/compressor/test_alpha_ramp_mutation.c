/* SPDX-License-Identifier: MIT
 *
 * test_alpha_ramp_mutation.c - MUTATION TARGET for test_alpha_ramp_independent.c.
 *
 * This file exists to answer one question: can test_alpha_ramp_independent.c
 * actually FAIL?
 *
 * The test was written after the implementation had already been corrected, so
 * it has never been observed to fail against the real code. A test with no
 * observed failure does not discriminate (AGENTS.md 9.1, 13.7): it might be
 * comparing two copies of the same wrong thing, or comparing the right thing
 * to a reference that is itself wrong in the same way.
 *
 * So: link the test against THIS instead of against rx550_compress.c. This is
 * the ramp as it was committed in 05c6297 (2b940ab1), transcribed verbatim.
 *
 *   - 8-value branch: coefficient (7-i), which is one step short of the
 *     correct (8-i). At i=2 it yields (5*a0 + a1)/7 instead of (6*a0 + a1)/7.
 *   - 6-value branch: divisor 7 in both branches, coefficient (i) on a1, and
 *     six interpolated values instead of four interpolants plus 0 and 255.
 *
 * Expected: the test reports discrepancies in BOTH modes and exits non-zero.
 * If it exits zero against this shim, the test is worthless and must be
 * rewritten before it is trusted.
 */

#include <stdint.h>

#include "rx550_compress.h"   /* declaration only */

void rx550_alpha_palette_for_test(uint8_t a0, uint8_t a1, uint8_t pal[8])
{
    int i;

    pal[0] = a0;
    pal[1] = a1;

    if (a0 > a1) {
        for (i = 2; i < 8; i++)
            pal[i] = (uint8_t)(((7 - i) * (int)a0 + (i - 1) * (int)a1 + 3) / 7);
    } else {
        for (i = 2; i < 8; i++)
            pal[i] = (uint8_t)(((7 - i) * (int)a0 + (int)i * (int)a1 + 3) / 7);
    }
}

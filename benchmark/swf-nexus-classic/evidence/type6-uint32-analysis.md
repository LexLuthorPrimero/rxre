# Type-6 uint32 analysis (RXRE-SWF-032 update)

## Question
Is the type-6 uint32 a deterministic function of the float32?

## Prior claim (RXRE-SWF-032)
u = ((bitcast(f) & 0xFFFFF) * 0x100001 + 128) >> 8
Verified by hand on 6 pairs. NOT verified on all 61.

## Method
Recovered the EFFECTIVE M' for each u by inverting the formula:
  u = (M' * 0x100001 + 128) >> 8   (bijection for 20-bit M')
Then compared M' to the float32 fields.

## Result: REFUTED as a general formula
The formula is EXACT for only 27/61 pairs (44%).

Distribution of M' vs lo20 (= bitcast(f) & 0xFFFFF):
  M' == lo20           : 27   (formula works directly)
  M' == lo20 ^ 0x80000 : 9    (bit 19 flipped)
  M' == lo20 & 0x1FFFF : 8    (bits 16-19 cleared)
  M' == lo20 & 0xFFFF  : 2    (bits 16-19 cleared, 16-bit)
  M' == OTHER          : 6    (no simple relation)
  NO_INVERSE           : 9    (u NOT of form formula(M) at all)
  TOTAL                : 61

## Key evidence
1. For 9 pairs, u is NOT producible by the formula for ANY 20-bit M
   (f=0.814, 1.13963, 2.3927, 30, 32.6566, 45.8208, 81.0949,
    107.369, 1031.53). These u values are arbitrary 0.32 fractions
   (not round rationals: nearest small-denom fit err=401, 512, 477...).
2. For the "clean" pairs the formula works, but for pairs like
   f=1.8625 (lo20=0xe6666) the true M'=0x66666 != lo20, and for
   f=3.77822 (lo20=0x1ce66) M'=0x66666 != lo20. The effective M'
   is a clean pattern UNRELATED to lo20.
3. u is a function of f only in the trivial sense that the 61
   (f,u) pairs are distinct; the same u appears with many f
   (e.g. u=0.4 for f=1.8, 1.8625, 1.89375, 1.925, 2.0375, 2.1,
   3.77822) which have DIFFERENT lo20.

## Conclusion
The type-6 uint32 is a 0.32 fixed-point fraction that is a SEPARATE
value (a weight/probability paired with the multiplier), NOT a
deterministic function of the float32. The formula
u=((b&0xFFFFF)*0x100001+128)>>8 is a COINCIDENCE that holds for the
27 pairs whose float32 low-20-bits happen to equal round(u*2^20).

## What remains NOT_DETERMINED
The game-meaning of the 0.32 fraction (probability? weight? per-constant
tag?) requires runtime observation (differential validation), which is
blocked by the absence of a Flash runtime (RXRE-SWF-014).

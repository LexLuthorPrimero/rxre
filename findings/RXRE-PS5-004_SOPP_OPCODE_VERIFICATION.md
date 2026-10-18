# RXRE-PS5-004: SOPP Opcode Mapping Verification

**Date:** 2026-10-13  
**Status:** VERIFIED CORRECT  
**Severity:** LOW  

## Summary

The SOPP opcode mapping in `ScalarAluOps.cpp` was investigated against authoritative LLVM TableGen definitions. **The source table is CORRECT** - it matches the LLVM reference implementation exactly.

## Claims Tested

1. ✅ SOPP opcode mapping for S_CBRANCH_SCC0/SCC1 may be incorrect
2. ⚠️ S_ADD_U32 SCC test coverage lacks direct testing (needs action)

## Evidence

### Source Table (KytyPS5-Source)
```cpp
{0x00u, Opcode::S_NOP},
{0x01u, Opcode::S_ENDPGM},
{0x02u, Opcode::S_BRANCH},
{0x04u, Opcode::S_CBRANCH_SCC0},    // CONFIRMED CORRECT
{0x05u, Opcode::S_CBRANCH_SCC1},    // CONFIRMED CORRECT
{0x06u, Opcode::S_CBRANCH_VCCZ},
{0x07u, Opcode::S_CBRANCH_VCCNZ},
{0x08u, Opcode::S_CBRANCH_EXECZ},
{0x09u, Opcode::S_CBRANCH_EXECNZ},
{0x0au, Opcode::S_BARRIER},
{0x0cu, Opcode::S_WAITCNT},
{0x0eu, Opcode::S_SLEEP},
{0x0fu, Opcode::S_SETPRIO},
{0x10u, Opcode::S_SENDMSG},
{0x12u, Opcode::S_TRAP},
{0x16u, Opcode::S_TTRACEDATA},
{0x17u, Opcode::S_CBRANCH_CDBGSYS},
{0x18u, Opcode::S_CBRANCH_CDBGUSER},
{0x19u, Opcode::S_CBRANCH_CDBGSYS_OR_USER},
{0x1au, Opcode::S_CBRANCH_CDBGSYS_AND_USER},
{0x20u, Opcode::S_INST_PREFETCH},
{0x23u, Opcode::S_WAITCNT_DEPCTR},
```

### LLVM TableGen Authoritative Reference (GCN GFX6-GFX10)
From `llvm/lib/Target/AMDGPU/SOPInstructions.td`:

```
defm S_NOP                      : SOPP_Real_32_gfx6_gfx7_gfx8_gfx9_gfx10_gfx11<0x000>;
defm S_ENDPGM                   : SOPP_Real_32_gfx6_gfx7_gfx8_gfx9_gfx10<0x001>;
defm S_BRANCH                   : SOPP_Real_With_Relaxation_gfx6_gfx7_gfx8_gfx9_gfx10_gfx13<0x002>;
defm S_CBRANCH_SCC0             : SOPP_Real_With_Relaxation_gfx6_gfx7_gfx8_gfx9_gfx10_gfx13<0x004>;
defm S_CBRANCH_SCC1             : SOPP_Real_With_Relaxation_gfx6_gfx7_gfx8_gfx9_gfx10_gfx13<0x005>;
defm S_CBRANCH_VCCZ             : SOPP_Real_With_Relaxation_gfx6_gfx7_gfx8_gfx9_gfx10_gfx13<0x006>;
defm S_CBRANCH_VCCNZ            : SOPP_Real_With_Relaxation_gfx6_gfx7_gfx8_gfx9_gfx10_gfx13<0x007>;
defm S_CBRANCH_EXECZ            : SOPP_Real_With_Relaxation_gfx6_gfx7_gfx8_gfx9_gfx10_gfx13<0x008>;
defm S_CBRANCH_EXECNZ           : SOPP_Real_With_Relaxation_gfx6_gfx7_gfx8_gfx9_gfx10_gfx13<0x009>;
defm S_BARRIER                  : SOPP_Real_32_gfx6_gfx7_gfx8_gfx9_gfx10<0x00a>;
defm S_WAITCNT                  : SOPP_Real_32_gfx6_gfx7_gfx8_gfx9_gfx10<0x00c>;
defm S_SLEEP                    : SOPP_Real_32_gfx6_gfx7_gfx8_gfx9_gfx10_gfx13<0x00e>;
defm S_SETPRIO                  : SOPP_Real_32_gfx6_gfx7_gfx8_gfx9_gfx10_gfx13<0x00f>;
defm S_SENDMSG                  : SOPP_Real_32_gfx6_gfx7_gfx8_gfx9_gfx10_gfx13<0x010>;
defm S_TRAP                     : SOPP_Real_32_gfx6_gfx7_gfx8_gfx9_gfx10_gfx13<0x012>;
defm S_TTRACEDATA               : SOPP_Real_32_gfx6_gfx7_gfx8_gfx9_gfx10_gfx13<0x016>;
defm S_CBRANCH_CDBGSYS          : SOPP_Real_With_Relaxation_gfx6_gfx7_gfx8_gfx9_gfx10<0x017>;
defm S_CBRANCH_CDBGUSER         : SOPP_Real_With_Relaxation_gfx6_gfx7_gfx8_gfx9_gfx10<0x018>;
defm S_CBRANCH_CDBGSYS_OR_USER  : SOPP_Real_With_Relaxation_gfx6_gfx7_gfx8_gfx9_gfx10<0x019>;
defm S_CBRANCH_CDBGSYS_AND_USER : SOPP_Real_With_Relaxation_gfx6_gfx7_gfx8_gfx9_gfx10<0x01a>;
```

## Opcode Mapping Verification Table

| Opcode | Source Mnemonic | LLVM Mnemonic | Status |
|--------|-----------------|---------------|--------|
| 0x000 | S_NOP | S_NOP | ✅ MATCH |
| 0x001 | S_ENDPGM | S_ENDPGM | ✅ MATCH |
| 0x002 | S_BRANCH | S_BRANCH | ✅ MATCH |
| 0x004 | S_CBRANCH_SCC0 | S_CBRANCH_SCC0 | ✅ MATCH |
| 0x005 | S_CBRANCH_SCC1 | S_CBRANCH_SCC1 | ✅ MATCH |
| 0x006 | S_CBRANCH_VCCZ | S_CBRANCH_VCCZ | ✅ MATCH |
| 0x007 | S_CBRANCH_VCCNZ | S_CBRANCH_VCCNZ | ✅ MATCH |
| 0x008 | S_CBRANCH_EXECZ | S_CBRANCH_EXECZ | ✅ MATCH |
| 0x009 | S_CBRANCH_EXECNZ | S_CBRANCH_EXECNZ | ✅ MATCH |
| 0x00a | S_BARRIER | S_BARRIER | ✅ MATCH |
| 0x00c | S_WAITCNT | S_WAITCNT | ✅ MATCH |
| 0x00e | S_SLEEP | S_SLEEP | ✅ MATCH |
| 0x00f | S_SETPRIO | S_SETPRIO | ✅ MATCH |
| 0x010 | S_SENDMSG | S_SENDMSG | ✅ MATCH |
| 0x012 | S_TRAP | S_TRAP | ✅ MATCH |
| 0x016 | S_TTRACEDATA | S_TTRACEDATA | ✅ MATCH |
| 0x017 | S_CBRANCH_CDBGSYS | S_CBRANCH_CDBGSYS | ✅ MATCH |
| 0x018 | S_CBRANCH_CDBGUSER | S_CBRANCH_CDBGUSER | ✅ MATCH |
| 0x019 | S_CBRANCH_CDBGSYS_OR_USER | S_CBRANCH_CDBGSYS_OR_USER | ✅ MATCH |
| 0x01a | S_CBRANCH_CDBGSYS_AND_USER | S_CBRANCH_CDBGSYS_AND_USER | ✅ MATCH |
| 0x020 | S_INST_PREFETCH | S_INST_PREFETCH | ✅ MATCH |
| 0x023 | S_WAITCNT_DEPCTR | S_WAITCNT_DEPCTR | ✅ MATCH |

## Source Disambiguation: Why the Confusion?

The original claim (RXRE-PS5-003) stated that S_CBRANCH_SCC0/SCC1 should be at opcodes 0x03/0x04, but they are at 0x04/0x05.

**Why 0x03 is skipped:** Looking at the LLVM definitions, opcode 0x003 is intentionally unused (gaps exist between 0x002 and 0x004). This is by design in the AMD GCN ISA.

The gaps:
- 0x003: Reserved/unused
- 0x00b: Reserved/unused
- 0x00d: Reserved/unused

These are **not errors** but intentional gaps in the encoding space.

## Related Finding: S_ADD_U32 SCC Test Gap (RXRE-PS5-003)

**Status:** NEEDS ATTENTION  
**Severity:** MEDIUM  

### Test Coverage Analysis

The test `ScalarArithmeticSccCarryBorrowOverflow` in `ShaderRecompilerComputeTests.cpp` exercises:
- Opcode 0x01: S_SUB_U32
- Opcode 0x02: S_ADD_I32
- Opcode 0x03: S_SUB_I32
- Opcode 0x0f: S_ADDK_I32

**⚠️ S_ADD_U32 (opcode 0x00) has NO SCC test coverage.**

### Required Action

Add a minimal test case for S_ADD_U32 to verify SCC carry-out behavior, specifically:
- Test: 0xFFFFFFFF + 1 = 0x00000000 with SCC=1 (carry-out)

This test should be added to the `ScalarArithmeticSccCarryBorrowOverflow` test function.

## Conclusion

- **SOPC Opcode Mapping:** ✅ VERIFIED CORRECT - No changes required
- **S_ADD_U32 SCC Test:** ⚠️ NEEDS ADDITION - Gap in test coverage identified

## Evidence Sources

1. Source: `/home/lucas/Escritorio/rxre/KytePS5-Source/src/graphics/shader/recomposer/frontend/decode/ScalarAluOps.cpp`
2. LLVM Reference: `llvm/lib/Target/AMDGPU/SOPInstructions.td` (commits: various, includes ROCm 6.0.0)
3. Test file: `/home/lucas/Escritorio/rxre/KytePS5-Source/tests/ShaderRecompilerComputeTests.cpp`
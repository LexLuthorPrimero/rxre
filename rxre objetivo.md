
                         RXRE — SURGICAL REVERSE ENGINEERING
================================================================================

 INPUT
   |
   +-- Source code       C/C++/ASM/Rust/...
   +-- Binary            ELF/PE/COFF/firmware/...
   +-- Runtime           process/memory/syscalls/traces
   +-- Protocol          packets/files/register transactions
   +-- Hardware          MMIO/DMA/ISA/GPU/device behavior
   +-- Unknown object    opaque input + observable behavior
   |
   v
+----------------------------------------------------------------------------+
|  1. INTAKE & IDENTITY                                                      |
|                                                                            |
|  Hashes | Format detection | Architecture | Version | Provenance           |
|  Corpus inventory | Completeness checks | Safe input classification       |
+----------------------------------------------------------------------------+
   |
   v
+----------------------------------------------------------------------------+
|  2. EVIDENCE ACQUISITION                                                   |
|                                                                            |
|  STATIC              DYNAMIC             STRUCTURAL         FORMAL         |
|  --------            -------             ----------         -----         |
|  Ghidra              GDB/LLDB            ELF/PE parsers     Z3/SMT          |
|  Rizin/radare2       Frida               DWARF/BTF          CBMC            |
|  Clang/Joern         rr                  CFG/callgraph      KLEE            |
|  Coccinelle          perf/eBPF           symbols/types      symbolic exec  |
|  Disassemblers       fuzzing             memory layouts     invariants     |
|       |                  |                    |                 |          |
|       +------------------+--------------------+-----------------+          |
|                                  |                                         |
|                  RAW OUTPUT + EXECUTION METADATA                           |
+----------------------------------------------------------------------------+
                                   |
                                   v
+----------------------------------------------------------------------------+
|  3. NORMALIZATION & SEMANTIC ADAPTERS                                      |
|                                                                            |
|  Common schemas | Address spaces | Types | Functions | Events              |
|  CFG | Memory accesses | Calls | Data dependencies | Protocol messages     |
|                                                                            |
|  Preserve original output, tool version, parameters and uncertainty.       |
+----------------------------------------------------------------------------+
                                   |
                                   v
+----------------------------------------------------------------------------+
|  4. EVIDENCE GRAPH                                                        |
|                                                                            |
|  Producer --> Transformation --> Representation --> Consumer --> Effect   |
|                                                                            |
|  Nodes: claims, code, instructions, data, events, types, measurements       |
|  Edges: calls, writes, reads, depends-on, transforms, contradicts          |
|                                                                            |
|  Every important claim links to evidence, scope and validation.             |
+----------------------------------------------------------------------------+
                                   |
                                   v
+----------------------------------------------------------------------------+
|  5. SEMANTIC RECONSTRUCTION                                                |
|                                                                            |
|  What does it do? | Which state changes? | Which conditions matter?         |
|  What are the invariants? | Which paths are feasible? | What is unknown?    |
|                                                                            |
|  Hypotheses + competing explanations + confidence + proof obligations      |
+----------------------------------------------------------------------------+
                                   |
                                   v
+----------------------------------------------------------------------------+
|  6. UNCERTAINTY & EXPERIMENT PLANNER                                       |
|                                                                            |
|  Missing edges | Conflicting tools | Unproven assumptions | Unknown states  |
|                                                                            |
|  Rank next experiment by:                                                  |
|    information gain / cost / risk / reproducibility / coverage              |
|                                                                            |
|  Choose: inspect source, query another backend, instrument, fuzz,           |
|          emulate, solve constraints, or measure real hardware.              |
+----------------------------------------------------------------------------+
                                   |
                                   v
+----------------------------------------------------------------------------+
|  7. DISCRIMINATING EXPERIMENT                                               |
|                                                                            |
|  Explicit hypotheses | Expected observations | Confounders                 |
|  Preconditions | Reversible setup | Stop conditions | Raw result            |
+----------------------------------------------------------------------------+
                                   |
                                   v
+----------------------------------------------------------------------------+
|  8. VALIDATION & ADVERSARIAL CHECKS                                        |
|                                                                            |
|  Independent backend | Differential tests | Mutation tests | Reproduction   |
|  Negative controls | Boundary cases | Counterexamples | Regression suite    |
+----------------------------------------------------------------------------+
                                   |
                       +-----------+-----------+
                       |                       |
                       v                       v
              CLAIM SUPPORTED           CLAIM REJECTED
                       |                       |
                       +-----------+-----------+
                                   |
                                   v
                    UPDATE EVIDENCE GRAPH + MODEL
                                   |
                                   +-------> PLAN NEXT EXPERIMENT
                                   |
                                   v
+----------------------------------------------------------------------------+
|  9. OUTPUT / DELIVERABLES                                                  |
|                                                                            |
|  Reconstructed specification | Causal graph | Annotated code               |
|  Tests | Minimal reproducer | Known limitations | Confidence per claim      |
|  Reimplementation | Machine-readable evidence bundle                      |
+----------------------------------------------------------------------------+

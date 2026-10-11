# RELEASE NOTES — first public release of RXRE

## What this is

A curated public export of the RXRE engine: the engine itself, the
backing tools it dispatches to, the public documentation, the test
suite, and the investigation corpus it was validated against.

The export is a NEW Git repository with a single initial commit and
no inherited development history.

## Scope of the corpus

The corpus is `RESEARCH/working/linux-7.1.3` (Linux 7.1.3, AMD GPU
driver subtree, 2769 source files, 521 MB uncompressed). It is the
tree the engine was validated against; the released tests are pinned
to it.

`RESEARCH/kernelbuild/linux-7.1.3` is reconstructed, not copied: it
shares the `drivers/` and `Documentation/` subtrees with `working/`
(file list and sampled hashes verified identical) and adds the
complete `include/` tree plus the generated `arch/x86/include`
headers, which is the part `working/` lacks and the part
`trace_path.py` needs to resolve the ASIC. The instrumented variant
of `amdgpu/amdgpu_vm.c` used during development (a 12-line
observational note, RE-02-E1) is NOT part of the published corpus:
no released test reads it.

`RESEARCH/kernelbuild` in the development tree is a built,
instrumented 1.8 GB tree; only the source subset above is
redistributed.

## Excluded from the release, and why

`tools/rxre/tests/test_fixtures.py` and
`tools/rxre/fixtures/rx550_regresion.json` are excluded. The
fixture is a regression net for the DEVELOPMENT machine by design
(its own docstring says it pins "ESTA maquina"): its `provenance`
vector pins the exact set of nine project-governance Markdown
documents at the root of the development repository
(AGENTS.md, COORDINACION.md, EVIDENCE-MATRIX.md,
HARDWARE-FINGERPRINT.md, NEGATIVE-RESULTS.md, OPEN-FRONTIERS.md,
P0.2_CLOSURE.md, P0.3_EPISTEMIC_DISTINCTIONS.md, promp.md) and the
exact percentages they produce. Those documents are process
artifacts of the driver-research project, not product artifacts, and
are not part of a public release. The fixture's other vectors (real
corpus search, symbol lookup, PM4 census, bounded absence, scope
rejection, non-RE statement) do pass against this export; only the
repository-root provenance vector is machine-bound.

`tools/rxre/tests/test_mutations003.py` is excluded because its
mutation set declares one mutation ("the handler stops returning
results") whose only declared detector is `test_fixtures.py`.
Without that fixture the mutation would be reported as surviving,
which would be a coverage hole, not a result.

`tools/rxre/tests/test_lachesis_defuse_integration.py` SKIPS (exit
code 3, declared): it requires `externals/lachesis-runtime`, which
is not redistributed.

`tools/rxre/storage/rxre.sqlite3` (the local investigation
database), `tools/rxre/github/` (vendored upstream repositories:
angr, radare2, rizin, rz-ghidra) and the development tree's
`RESEARCH/evidence/`, `RESEARCH/baseline/` and
`RESEARCH/kernelbuild/` build artifacts are excluded.

## Repairs applied to the export (not to the development tree)

Three analysis scripts hardcoded the developer's absolute path; they
now derive the repository root from `__file__`:
`tools/rxre/tests/p0_1_reconcile.py`,
`tools/rxre/tests/p0_1_discriminants.py`,
`tools/rxre/tests/p0_2_semantica_conflict014.py`.

Historical comments in `tools/rxre_cobertura_gfx8.py` and
`tools/rxre/tests/test_cobertura_root013.py` carried the
developer's absolute path; the fact is kept, the path is not.

Lachesis fixtures under `tools/rxre/tests/fixtures/lachesis/`
recorded absolute paths from past runs; the personal prefix was
stripped. The suffix after `asic_reg/`, which
`test_lachesis_defuse_adapter.py` asserts, is preserved.

## Documentation corrections

`AI_QUICKSTART.md` said `capabilities[]` returns 11 intentions and
listed `op:plan` under "what does not exist". Both were wrong: the
engine returns 12 capabilities, and `op:plan` exists (documented in
`RXRE_PUBLIC_CONTRACT.md` section 1.2).

`RXRE_PUBLIC_CONTRACT.md` said "11 capabilities" in two places; the
engine returns 12. It also listed the result type
`capabilities_item` twice; the duplicate is removed.

## License

GPL-2.0. Twenty-five of the sixty-two engine source files carry
`SPDX-License-Identifier: GPL-2.0`; no file declares a different
license, so GPL-2.0 is the license the source itself declares. The
LICENSE file restates it. The corpus is Linux kernel source
(GPL-2.0).

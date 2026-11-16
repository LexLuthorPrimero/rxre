# Contribution proposal (DRAFT — not sent)

> **NOTA DE PORTADA (español, para revisión del propietario, NO forma parte del borrador upstream)**
>
> Este documento contiene la propuesta preparada conforme a la autorización del dictamen M10 (2026-11-16): verificación independiente + resultados del brazo discriminante D dirigidos al PR #6949, respetando la autoría de `mttgermano`.
>
> Lo que este borrador **no** hace: no se envió; no se comentó en el PR; no se creó ningún commit/branch/PR; no se modificó el PR; no se publicó nada. Enviarlo requiere autorización explícita posterior tuya.
>
> El borrador está en inglés por ser el idioma del hilo upstream. Las cifras y comandos fueron re-verificados hoy (2026-11-16) sobre los artefactos existentes; los límites de evidencia están declarados en la § "Scope and limitations". Ninguna afirmación supera ese dominio.
>
> Todo RXRE-específico (rutas internas, nombres de módulos, ledger, DB) queda fuera del borrador por higiene de contribución.

---

## Draft for PR #6949 — Independent verification and relocation-discriminant fixtures (DRAFT)

**Summary (proposed text for the PR conversation)**

Hi — independent verification from the RXRE project. We reproduce and validate the direction of this fix on synthetic ET_REL x86-64 fixtures, and we include one datum that the patch description could naturally raise a reviewer question about: whether the failure — and the fix — depend on the relocation type used by `call`. We do not claim authorship of this PR's fix; this is verification and an additional fixture-style observation.

Our harness is independent of both rizin's own test tooling and the patch under review: it parses the ELF itself (header/sections/symbols/relocations, byte-level), reconstructs control flow from those bytes, and compares the reconstructed expectation against any binary-under-test via a differential comparator whose three outcome axes (operational, comparison, epistemic) are independent. The module set deliberately knows nothing about retpolines: no fixture names, no defect-specific rules.

### Reproduction environment

- Host: Linux x86-64, gcc 16.2.1
- rizin `dev @ 55e0728a91` rebuilt twice:
  - **clean**: `librz_arch.so.0.10.0` sha256 `186bddef0f4a6cf7512b55e7d0a783c1ca250f7cfd3f1aa2fdd9cb3f657212`
  - **patched** (the one-line change of this PR): `librz_arch.so.0.10.0` sha256 `ea4645b867c9038b9a53632d248574f951a5c200e2f0e1b3ca80471cc3f7576c`
  - (the `rizin` launcher stub is identical in both: sha256 `4244b0e436325aa15d502fa91acd2fdaaa9ff26656c3aa2ac901bdb34913589d`)
- System rizin `0.7.4-9.fc43 (Fedora)` as an additional sanity point
- Target artifacts: synthetic fixtures A, B, D below (sha256 A `8922bee5…`, B `8d687bf9…`, D `2ff1d6bc…`); the issue reproducer's shape `retpoline-call.o` (built from the `.c` in this issue) sha256 `0475b007…`

### Observations (default analysis, `analysis.jmp.retpoline=true`)

| Fixture | Clean build | Patched build |
|---|---|---|
| A: `call __x86_indirect_thunk_rax` (R_X86_64_PLT32, undefined thunk) | `sym.hook` size 9, nbbs 1 | size 21, nbbs 3 |
| D: same code, same bytes, same thunk name — **only** `r_type` patched PLT32→R_X86_64_PC32 | size 9, nbbs 1 | **size 21, nbbs 3** |
| B: `call ext` (R_X86_64_PLT32, **non-thunk** symbol — control) | size 21, nbbs 3 | size 21, nbbs 3 |
| `retpoline-call.o` (issue reproducer, thunk at `0xb`) | `sym.hook` size 16, nbbs 1 | **size 48, nbbs 3** |

`e analysis.jmp.retpoline=false` recovers the hidden code in the truncating fixtures (verified on `retpoline-call.o`, where A/D-style calls stop truncating; issue-confirmed behavior). System `rizin 0.7.4-9.fc43 (Fedora)` shows the same truncation pattern (A: 9/1, D: 9/1, B: 21/3); the patched build itself was only evaluated for the `dev` snapshot above.

### The relocation-discriminant datum (arm D)

Fixtures A and D are **byte-identical in `.text`**: same instruction bytes, same symbol name, same section, same position, same compiler, same command line; the only difference in D is the `r_type` field of the RELA entry for the `call`, patched `R_X86_64_PLT32 (4) → R_X86_64_PC32 (2)` on a copy of the object. Both configurations truncate to 9 bytes in the unpatched build; both fully recover with the patch. B is the negative control (no truncation anywhere, correct in both builds).

Two competing hypotheses explain the defect and motivated the experiment:

- **H1** (relocation-agnostic): any `call` to a `*__x86_indirect_thunk_*` symbol is analyzed as an indirect jump when `analysis.jmp.retpoline=true`. Prediction: truncation with both PLT32 and PC32.
- **H3** (conjunction): the defect requires the triple { retpoline flag, thunk name prefix, R_X86_64_PLT32 }. Prediction: truncation with PLT32 only; correct with PC32.

Observed: **H3 refuted in this instance; H1 supported.** The patch under review is consistent with this (it stops the RJMP conversion for `call` ops regardless of relocation type).

Caveats for the reviewer: one `.text`, one instance of each hypothesis falsification; arm C in our harness (conditional-branch encoding rel8 vs rel32) was **not executed**; multi-format generalization (ET_EXEC, ET_DYN) was not tested; `diamorphine.ko` was **not** analyzed and will not be; compiler-specific latitude beyond the synthetic shape was not covered. Treat the PC32 datum as a single, replicable data point, not as a universal proof about rizin's heuristics.

### What RXRE contributes

- Independent reproduction of the issue on ET_REL x86-64 synthetic fixtures and on the issue's own reproducer shape.
- Independent reconstruction of the expected function bounds (objdump-free, ELF-parsed; sizes/hashes verifiable): e.g. `STT_FUNC hook st_size=48`, `.text=0x30` → expectation `size 48, 3 blocks`.
- A differential check that flags `analyzed_size 48→16`, `realsz`, and `basic_block_count 3→1` — i.e. the divergence is detected by an expectation built without knowledge of the defect.
- Verification that the patch recovers full function size and block count on all checked fixtures (A/B/D and retpoline-call.o).
- No authorship claim on the patch; no claim beyond the measured domain.

### Limitations

- ELF64 x86-64 little-endian, ET_REL only; no linking involved (fixtures built with `-c`, no libc, no LTO, no PIE variance beyond ET_REL semantics).
- Rizin 0.7.4 (Fedora package) and one isolated dev build (`dev @ 55e0728a91`); not tested across other versions/commits.
- Single data point per arm; no statistical framing implied.
- Review burden remains on upstream: we provide verification, not code.

### Reproduction (of the core data)

```sh
# fixture generation
printf '\t.text\n\t.globl hook\n\t.type hook, @function\nhook:\n\tpush %%rbp\n\tmov %%rsp, %%rbp\n\tcall __x86_indirect_thunk_rax\n\tcmpl $0, %%eax\n\tjle .Lret\n\tmov $1, %%eax\n.Lret:\n\tpop %%rbp\n\tret\n\t.size hook, .-hook\n' > a.s
gcc -c -nostdlib a.s -o fix_a.o
# D: copy of A with only the RELA r_type patched PLT32 -> PC32
#    (e.g. struct pack: r_offset Q / r_info Q / r_addend q; r_type = low 32 bits of r_info)
# B: same .s with the thunk reference replaced by a non-thunk symbol (e.g. `ext`)
rizin -A -qc 'aflj @ sym.hook' fix_{a,d,b}.o
```

### AI disclosure

The investigation and portions of the verification harness were produced with AI assistance and reviewed by a human before being shared; consistent with the disclosures already present in this PR. The contributor does not claim authorship of the patch.

---

*This draft proposes no change to the PR's code, no new PR, and no post-merge comment unless the maintainer asks. If this verification is useful, it can be pasted into the PR conversation as-is; if not, we will drop it without follow-up.*

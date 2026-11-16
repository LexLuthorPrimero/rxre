# Contribution proposal v1.2 (DRAFT — not sent)

> **NOTA DE PORTADA (español, para revisión del propietario, NO forma parte del borrador upstream)**
>
> Este documento contiene la versión 1.2 de la propuesta preparada conforme a la autorización del dictamen M10 (2026-11-16): verificación independiente + resultados del brazo discriminante D dirigidos al PR #6949, respetando la autoría de `mttgermano`.
>
> Correcciones materiales sobre v1.1 (por directiva del propietario): (1) independencia del oráculo descrita con exactitud — parser propio **+ GNU objdump como decodificador independiente**, nunca "objdump-free"; (2) reproducción completa y ejecutable de A/B/D con verificación de `.text` y `sha256`; (3) conclusión H1 limitada al dominio probado; (4) arquitectura argumental en orden 1–8; (5) hashes de fixtures completos en bloque compacto.
>
> Lo que este borrador **no** hace: no se envió; no se comentó en el PR; no se creó ningún commit/branch/PR; no se modificó el PR; no se publicó nada. Enviarlo requiere autorización explícita posterior tuya.
>
> El borrador está en inglés por ser el idioma del hilo upstream. Las cifras y comandos fueron re-verificados hoy (2026-11-16). Ninguna afirmación supera el dominio declarado.
>
> Todo RXRE-específico (rutas internas, nombres de módulos, ledger, DB) queda fuera del borrador por higiene de contribución.

---

## Proposed comment for PR #6949

**1. What this reproduces**

We saw the behavior reported in #6948 on local fixtures: `call __x86_indirect_thunk_rax` ends the function analysis after the call when `analysis.jmp.retpoline=true` (function reports `sym.hook` size 9 / nbbs 1 instead of the full object). We reproduce it, and we can show it is not specific to one relocation type of the call.

**2. Environment and artifacts**

- Host: Linux x86-64, gcc 16.2.1
- rizin `dev @ 55e0728a91` rebuilt twice (only `librz_arch.so.0.10.0` differs):
  - **clean**: `librz_arch.so.0.10.0` sha256 `186bddef0f4a6cf7512b55e7d0a783c1ca250f7cfd3f1aa2fdd9cb3f657212`
  - **patched** (the one-line change of this PR): `librz_arch.so.0.10.0` sha256 `ea4645b867c9038b9a53632d248574f951a5c200e2f0e1b3ca80471cc3f7576c`
  - the `rizin` launcher stub is identical in both: sha256 `4244b0e436325aa15d502fa91acd2fdaaa9ff26656c3aa2ac901bdb34913589d`
- System rizin `0.7.4-9.fc43 (Fedora)` as an additional sanity point
- Synthetic fixtures used (reviewed below): A, B, D (`.text` byte-identical for A/D; see reproduction):
  - `fix_a.o` sha256 `8922bee5beb6f7dfa8f2464cbe5102914e9231436925dbeb2bf8a814f9aad3c9`
  - `fix_d.o` sha256 `2ff1d6bc62a9320d01b621c91968b4cfcfcbedd5db68e3728637ea4e655c90e0`
  - `fix_b.o` sha256 `8d687bf93079f405ebee08efe18376a7a16206fd4ad5831a18a018a0a2b849e8`
  - issue-reproducer shape built from the `.c` in the issue: `retpoline-call.o` sha256 `0475b007285396855aac317a2e14e1d609b9ff5b9c2392a3284c16a3383cef9e`

**3. Clean build results** (`analysis.jmp.retpoline=true`, default)

| Fixture | Clean build |
|---|---|
| `fix_a.o` (`call __x86_indirect_thunk_rax`, R_X86_64_PLT32 → undefined thunk) | `sym.hook` size **9**, nbbs **1** |
| `fix_d.o` (same bytes, same thunk name — **only** `r_type` patched PLT32→R_X86_64_PC32) | size **9**, nbbs **1** |
| `fix_b.o` (`call ext`, R_X86_64_PLT32, **non-thunk** — control) | size **21**, nbbs **3** |
| `retpoline-call.o` (issue reproducer, thunk at `0xb`) | `sym.hook` size **16**, nbbs **1** |

System `rizin 0.7.4-9.fc43 (Fedora)` shows the same pattern (A 9/1, D 9/1, B 21/3). `e analysis.jmp.retpoline=false` recovers the hidden code in the truncating fixtures (verified on `retpoline-call.o`).

**4. Patched build results**

| Fixture | Patched build |
|---|---|
| `fix_a.o` | size **21**, nbbs **3** |
| `fix_d.o` | size **21**, nbbs **3** |
| `fix_b.o` | size **21**, nbbs **3** |
| `retpoline-call.o` | size **48**, nbbs **3** |

The patch recovers full function size and block count on all checked fixtures.

**5. The relocation-discriminant datum (arm D)**

A and D are **byte-identical in `.text`**: same instruction bytes, same symbol name, same section, same position, same compiler flags (`-c -nostdlib`), same command line; the only difference in D is the `r_type` field of the RELA entry for the `call`, patched `R_X86_64_PLT32 (4) → R_X86_64_PC32 (2)` on a copy of the object. `r_offset` and `r_addend` are preserved. Both configurations truncate to 9 bytes in the unpatched build; both fully recover with the patch. B remains correct everywhere (negative control).

Two competing hypotheses explain the defect and motivated the experiment:

- **H1** (relocation-agnostic): any `call` to a `*__x86_indirect_thunk_*` symbol is analyzed as an indirect jump when `analysis.jmp.retpoline=true`. Prediction: truncation with both PLT32 and PC32.
- **H3** (conjunction): the defect requires the triple { retpoline flag, thunk name prefix, R_X86_64_PLT32 }. Prediction: truncation with PLT32 only; correct with PC32.

Observed: the observation refutes H3 for this fixture and supports H1 over H3 within the tested domain. It does **not** establish relocation-agnostic behavior across all ELF configurations. The patch under review is consistent with this (it stops the RJMP conversion for `call` ops regardless of relocation type).

**6. What RXRE verifies independently**

RXRE's check harness parses ELF metadata and bytes independently with its own parser (header/sections/symbols/relocations, byte-level), obtains instruction decoding from an independent instruction decoder (GNU objdump), reconstructs control flow from that evidence (basic blocks, call semantics: a call continues in the same block and performs a call-edge, never a terminator by default), and compares the reconstructed expectation against the binary under test with a separate comparator (three axes: operational / comparison / epistemic). The module set deliberately knows nothing about retpolines: no fixture names, no defect-specific rules.

Against `retpoline-call.o`, the expectation built without knowledge of the defect (from `STT_FUNC` bounds: `hook st_size=48`, `.text=0x30`) flags: `analyzed_size 48→16`, `analyzed_realsz`, and `basic_block_count 3→1`. The patch recovers the expected values on all checked fixtures. No authorship claim is made on the patch.

**7. What is not demonstrated**

- One `.text` per case; one instance of each hypothesis comparison; no statistical framing implied.
- Multi-format generalization (ET_EXEC, ET_DYN, other architectures) was **not** tested.
- Arm C (conditional-branch encoding rel8 vs rel32) was **not executed**.
- `diamorphine.ko` was **not** analyzed (we have not and will not touch it); results are limited to synthetic fixtures.
- Rizin 0.7.4 (Fedora package) and the isolated `dev` snapshot only; other versions/commits were not tested.
- ELF64 little-endian, ET_REL; fixtures built with `-c`, no libc, no LTO, no PIE variance beyond ET_REL semantics.

**8. Reproduction**

```sh
printf '\t.text\n\t.globl hook\n\t.type hook, @function\nhook:\n\tpush %%rbp\n\tmov %%rsp, %%rbp\n\tcall __x86_indirect_thunk_rax\n\tcmpl $0, %%eax\n\tjle .Lret\n\tmov $1, %%eax\n.Lret:\n\tpop %%rbp\n\tret\n\t.size hook, .-hook\n' > a.s
gcc -c -nostdlib a.s -o fix_a.o
sha256sum fix_a.o   # 8922bee5beb6f7dfa8f2464cbe5102914e9231436925dbeb2bf8a814f9aad3c9

# B: same .s with the thunk reference replaced by a non-thunk symbol
sed 's/__x86_indirect_thunk_rax/ext/' a.s > b.s
gcc -c -nostdlib b.s -o fix_b.o
sha256sum fix_b.o   # 8d687bf93079f405ebee08efe18376a7a16206fd4ad5831a18a018a0a2b849e8

# D: copy of A with ONLY the RELA r_type patched PLT32 -> PC32
#    (r_info low 32 bits = r_type: 4 -> 2; r_offset and r_addend preserved)
python3 - <<'EOF'
import struct, hashlib
src, dst = 'fix_a.o', 'fix_d.o'
data = bytearray(open(src, 'rb').read())
e_shoff, = struct.unpack_from('<Q', data, 0x28)
e_shentsize, e_shnum, e_shstrndx = struct.unpack_from('<H H H', data, 0x3a)
secs = []
for i in range(e_shnum):
    base = e_shoff + i * e_shentsize
    sh_name, sh_type, _, _, sh_off, sh_size = struct.unpack_from('<I I Q Q Q Q', data, base)
    secs.append((sh_name, sh_type, sh_off, sh_size))
shstr = data[secs[e_shstrndx][2]:secs[e_shstrndx][2] + secs[e_shstrndx][3]]
def sec_name(off):
    end = shstr.find(b'\x00', off)
    return shstr[off:end].decode()
target = None
for sh_name, sh_type, sh_off, sh_size in secs:
    if sh_type == 4 and sec_name(sh_name) == '.rela.text':
        target = (sh_off, sh_size); break
assert target, '.rela.text not found'
sh_off, sh_size = target
patched = 0
for off in range(sh_off, sh_off + sh_size, 24):
    r_off, r_info, r_addend = struct.unpack_from('<Q Q q', data, off)
    if (r_info & 0xffffffff) == 4:          # R_X86_64_PLT32
        data[off + 8:off + 12] = (2).to_bytes(4, 'little')  # R_X86_64_PC32
        patched += 1
assert patched == 1, 'expected exactly one PLT32 -> one patched PC32'
open(dst, 'wb').write(bytes(data))
print('sha256', hashlib.sha256(bytes(data)).hexdigest())
EOF                       # 2ff1d6bc62a9320d01b621c91968b4cfcfcbedd5db68e3728637ea4e655c90e0

# Verify that A and D have byte-identical .text sections
objcopy -O binary --only-section=.text fix_a.o fix_a.bin
objcopy -O binary --only-section=.text fix_d.o fix_d.bin
cmp fix_a.bin fix_d.bin

rizin -A -qc 'aflj @ sym.hook' fix_{a,d,b}.o
```

**AI disclosure.** The investigation and portions of this verification were produced with AI assistance and reviewed by the RXRE project before being posted; consistent with the disclosures in this PR. RXRE does not claim authorship of the patch; it verifies it. (Publication identity remains a separate decision of the RXRE project authors.)

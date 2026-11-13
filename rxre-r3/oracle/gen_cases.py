#!/usr/bin/env python3
"""R3 — Generador DETERMINISTA de casos para filenvercmp (no históricos; propios)."""
import random, sys

SEED = int(sys.argv[1]) if len(sys.argv) > 1 else 20261112
random.seed(SEED)

base = [
    "", "a", "b", "A", "B", "z", "Z", "1", "0", "00", "01", "10", "2", "20", "123",
    ".", "..", "...", "~", "a~", "~", "~a", "~a~", "a~b", "~.", ".a", ".a~",
    "a.", "a..", "a...", "a.1", "a.10", "a.01", "a.001", "b.2", "b.20", "b.002",
    "0", "00", "000", "0000", "1", "01", "001", "0010", "0001", "00010",
    "9", "09", "90", "909", "999", "9999", "1000", "99999", "100000", "99999999999999999999",
    "1", "2", "10", "11", "100", "101", "1000", "10000",
    "x", "x1", "x10", "x01", "x001", "x1a", "x1aa", "x1b", "x2", "x10a", "x10aa",
    "a1", "a1a", "a1b", "a1z", "a2", "a2a", "a10", "a11", "a100", "a101", "a1000",
    "y1", "y10", "y01", "y001", "b1", "b1a", "b1aa", "b2", "c1",
    "VERSION1", "VERSION10", "VERSION2", "VERSION01", "version1", "version10",
    "name1.name2", "name10.name1", "name01.name2", "file-1.0", "file-1.1", "file-1.01",
    "a.b.c", "a.b1.c", "a.b10.c", "a.bc", "a..bc", "abc", "ab~c", "~abc", "abc~",
    "!", "@", "#", "%", "^", "&", "*", "(", ")", "-", "_", "+", "=",
    "a_b", "a-b", "a+b", "a=b", "a@b", "a#b", "a*b", "a(b", "a)b", "a!b", "a%b", "a&b",
    "END", "END1", "END10", "END2", "end", "a\x7f", "a\x80", "a\xff", "\x80a", "\xffa",
    "{", "}", "[", "]", "|", "}", "{1", "}a",
    "ABC", "A1", "A1A", "A10", "B1", "C10",
    "1.0", "1.0.1", "1.10", "1.01", "1.002", "1.20", "1.1000", "1.1001",
    "2.0", "10.0", "11.0", "20.0",
]

pairs = set()
for i, a in enumerate(base):
    for b in base:
        pairs.add((a, b))
# round-trip swapped for parity
for a, b in list(pairs):
    pairs.add((b, a))

# random cases with printable ASCII + some bytes >= 0x7f
random.seed(SEED)
alphabet = [chr(c) for c in range(32, 127)] + ['~', '.']
for _ in range(6000):
    la = random.randint(0, 12)
    lb = random.randint(0, 12)
    a = ''.join(random.choice(alphabet) for _ in range(la))
    b = ''.join(random.choice(alphabet) for _ in range(lb))
    pairs.add((a, b))

pairs_list = sorted(pairs)
print(f"# R3 gen SEED={SEED} pairs={len(pairs_list)}", file=sys.stderr)
def esc(s):
    out = []
    for ch in s:
        o = ord(ch)
        if 32 <= o < 127 and ch not in ('\\', '\t', '\n'):
            out.append(ch)
        else:
            out.append('\\x%02x' % o)
    return ''.join(out)

with open(sys.argv[2], 'w', newline='\n', encoding='ascii') as f:
    for a, b in pairs_list:
        f.write(f"{esc(a)}\t{esc(b)}\n")

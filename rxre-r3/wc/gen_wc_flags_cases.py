#!/usr/bin/env python3
"""R3-Fase2 hito 2 — corpus de FLAGS para /usr/bin/wc (LC_ALL=C).
Línea: "<flags> \\t <contenido hex-escapado>". Cada caso = (flags de salida, contenido).
Flags en dominio: default, -c, -l, -w, y combinaciones (formato impreso GNU: orden fijo L W B)."""
import random, sys
SEED = int(sys.argv[1]) if len(sys.argv) > 1 else 20261116
random.seed(SEED)

structured = [
    '', ' ', '\n', 'a', 'a\n', 'abc\n', 'a b\n', 'a  b\n', 'a\tb\n', '\n\n\n\n',
    'a b c d e\n', 'The quick brown fox\n', 'hello world hello\n', '   leading\n',
    'trailing   \n', '   both   \n', 'word with no newline', 'a' * 64, 'a b ' * 16,
    'a\nb\nc\n', '1\t2\t3\n', 'one two\tthree\n', 'no newline at end', 'x\t\ty\nz\n',
    'a\r\nb\r\n', 'a\vb\fc\n', 'Mixed CASE UPPER lower\n', 'word-count-check\n',
    '0\n1\n2\n3\n', 'word1  word2   word3\n', '\v\v\v\f\f', '\r\r\r', '!@#$%^&*()\n',
]
ALPHABET = list('abcXYZ019 \t\n\r._')
def esc(s):
    out = []
    for ch in s:
        o = ord(ch)
        if 32 <= o < 127 and ch not in ('\\', '\t', '\n'):
            out.append(ch)
        else:
            out.append('\\x%02x' % o)
    return ''.join(out)

contents = set(structured)
for _ in range(1500):
    n = random.randint(0, 48)
    contents.add(''.join(random.choice(ALPHABET) for _ in range(n)))
contents = sorted(contents)

FLAG_SETS = ['', '-c', '-l', '-w', '-c -l', '-c -w', '-l -w', '-c -l -w']
cases = []
for c in contents:
    for fs in FLAG_SETS:
        cases.append((fs, c))
cases.sort(key=lambda x: (x[1], x[0]))
print(f'# R3 wc hito2 gen SEED={SEED} cases={len(cases)}', file=sys.stderr)
with open(sys.argv[2], 'w', newline='\n', encoding='ascii') as f:
    for fs, c in cases:
        f.write(f'{fs}\t{esc(c)}\n')

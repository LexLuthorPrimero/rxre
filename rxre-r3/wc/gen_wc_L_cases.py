#!/usr/bin/env python3
"""R3-Fase2 hito 3 — corpus de flags+L para /usr/bin/wc (LC_ALL=C).
Línea: "<flags> \\t <contenido hex-escapado>".
Dominio: {default, -l, -w, -c, -L, y todas las combinaciones} · LC_ALL=C · unibyte."""
import random, sys, itertools
SEED = int(sys.argv[1]) if len(sys.argv) > 1 else 20261117
random.seed(SEED)

structured = [
    '', ' ', '\n', 'a', 'a\n', 'abc\n', 'a b\n', 'a  b\n', 'a\tb\n', '\n\n\n\n',
    'a b c d e\n', 'The quick brown fox\n', 'hello world hello\n', '   leading\n',
    'trailing   \n', '   both   \n', 'word with no newline', 'no newline', 'a' * 64,
    'a b ' * 16, 'a\nb\nc\n', '1\t2\t3\n', 'one two\tthree\n', 'x\t\ty\nz\n',
    'a\r\nb\r\n', 'a\vb\fc\n', 'Mixed CASE UPPER lower\n', 'word-count-check\n',
    '0\n1\n2\n3\n', 'word1  word2   word3\n', '\v\v\v\f\f', '\r\r\r', '!@#$%^&*()\n',
    'with\ttabs and\x01ctl chars\nlonger line here\nshort\n', 'a\tb\ncd e f g h i j k l m n\n',
    '\x7f\x7f\x7f\n', '\xff\xff\xff', '\x01\x02\x03abc\n', 'end_no_newline', 'a\nb',
]
ALPHABET = list('abcXYZ019 \t\n\r._\x7f')
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
for _ in range(800):
    n = random.randint(0, 48)
    contents.add(''.join(random.choice(ALPHABET) for _ in range(n)))
contents = sorted(contents)

FLAG_SETS = ['']
flags = ['l', 'w', 'c', 'L']
for k in range(1, 5):
    for combo in itertools.combinations(flags, k):
        FLAG_SETS.append('-' + ' -'.join(sorted(combo)))
# order sets: default + the bit combinations, keep sorted for determinism
FLAG_SETS = sorted(FLAG_SETS, key=lambda s: (len(s.split()) if s else 0, s))
print(f'# R3 wc hito3 gen SEED={SEED} cases={len(contents) * len(FLAG_SETS)} flagsets={len(FLAG_SETS)} contents={len(contents)}', file=sys.stderr)
cases = [(fs, c) for c in contents for fs in FLAG_SETS]
with open(sys.argv[2], 'w', newline='\n', encoding='ascii') as f:
    for fs, c in cases:
        f.write(f'{fs}\t{esc(c)}\n')

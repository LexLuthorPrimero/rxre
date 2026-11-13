#!/usr/bin/env python3
"""R3-Fase2 hito 1 — generador DETERMINISTA de contenidos para wc (LC_ALL=C).
Corpus sellable: archivos sintéticos (bytes planos), formato hex-escapado por línea.
Dominio: letras minúsculas, dígitos, ' ', '.', '~', '_', espacios ASCII C-locale, \n, \r, \t, \v, \f.
Sin multibyte (LC_ALL=C); sin NUL."""
import random, sys
SEED = int(sys.argv[1]) if len(sys.argv) > 1 else 20261114
random.seed(SEED)

ALPHABET = list('abcdefghijklmnopqrstuvwxyz0123456789') + ['a', 'b', 'a', ' ']
SPACE_CHARS = [' ', '\t', '\v', '\f', '\r', '\n']

structured = [
    '', ' ', '\n', 'a', 'a\n', '\nabc', 'abc\n', 'a b\n', 'a  b\n', 'a\tb\n',
    'a\r\nb\r\n', 'a\vb\f\n', 'a\nb\nc\n', '\n\n\n\n', 'a b c d e\n',
    'The quick brown fox\n', 'hello world hello\n', '   leading spaces\n',
    'trailing spaces   \n', '   both   \n', 'word1  word2   word3\n',
    '0\n1\n2\n3\n', '1\t2\t3\n', 'one two\tthree\nfour\nfive six seven\n',
    'word with no newline', 'a' * 64, 'a b ' * 16, '\t\t\t\n', '\v\v\v', '\r\r\r',
    'a\nb\r\nc\nd\n', 'Mix of CASE UPPER lower\n', 'with.dots and_underscores\n',
    '\n\nmiddle blank lines\n\n', 'spaces between words are many    \n', 'end with newline\n',
    '\nleading newline\n', 'double\n\nnewline', 'x\t\ty\nz\n', 'tabs\tand\tspaces and\n',
    '. ~ _ . ~ _ chars\n', 'aAaA0oO1lL\n', '123 456 789\n', '!!!\n', '+-*/%\n',
    'word-count-check\n', 'last line no newline at end', 'no trailing newline',
]

contents = set(structured)
for _ in range(5000):
    n = random.randint(0, 64)
    toks = []
    for _ in range(n):
        r = random.random()
        if r < 0.15:
            toks.append(random.choice(SPACE_CHARS))
        else:
            toks.append(random.choice(ALPHABET))
    contents.add(''.join(toks))

contents = sorted(contents)
print(f'# R3 wc hito1 gen SEED={SEED} cases={len(contents)}', file=sys.stderr)

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
    for c in contents:
        f.write(esc(c) + '\n')

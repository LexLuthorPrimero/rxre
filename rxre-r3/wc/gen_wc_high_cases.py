#!/usr/bin/env python3
"""R3-Fase2 hito 5 — discriminación de bytes altos en /usr/bin/wc.
Genera contenidos con bytes >= 0x80 y secuencias multibyte UTF-8 para exponer
el sesgo del modelo ASCII-only. Formato: hex-escapado por línea."""
import random, sys
SEED = int(sys.argv[1]) if len(sys.argv) > 1 else 20261118
random.seed(SEED)

PIECES = [' ', '\t', '\n', '\r', '\v', '\f', 'a', 'b', 'c', '0', '9', '.',
          '\xa0', '\x85', '\xff', '\x80', '\xc2\xa0', '\xc3\xa9', '\xc2\xa9',
          'single\xa0case', '\xff\xfe\xfd', 'a\xa0b\xa0c']
ALPHABET = list('abcXYZ019') + [' ', '\t', '\n', '\r', '\v', '\f', '\xa0', '\xff', '\x80', '\xc2\xa0', '\xc3\xa9']
PIECES_STR = [bytes(p, 'latin1') for p in PIECES]

structured = [
    '', ' ', '\n', 'a', 'a\n', 'abc\n', 'a b\n', 'a  b\n', 'a\t\n',
    '\xa0', '\xa0\xa0a', '\xa0b\xa0', 'a\xa0b\n', '\xc2\xa0', '\xc2\xa0a\n',
    'a\xc2\xa0b\n', '\xc3\xa9\n', '\xc3\xa9a\n', 'e\xc3\xa9n\n',
    '\x80', '\xff', 'a\xffb\n', '\xc2\xa0\xc2\xa0a\n', 'text with nbsp\n',
    'e\u0301\n'.encode('utf-8').decode('latin1', errors='ignore'),
]
contents = set(structured)
byte_alphabet = ['a','b','c','0','9',' ','\t','\n','\r','\v','\f','\xa0','\x85','\xff','\x80','\xc2\xa0','\xc3\xa9']
for _ in range(1200):
    n = random.randint(0, 48)
    contents.add(''.join(random.choices(byte_alphabet, k=n)))
contents = sorted(contents)
print(f'# R3 wc hito5 gen SEED={SEED} cases={len(contents)}', file=sys.stderr)
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

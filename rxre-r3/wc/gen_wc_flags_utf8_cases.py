#!/usr/bin/env python3
"""R3-Fase2 hito 11 — flags × multibyte UTF-8 en es_AR.utf8.
Línea: "<flags> \\t <contenido hexa-escapado>". Flags sin contenido de los sets sellados."""
import random, sys, itertools
SEED = int(sys.argv[1]) if len(sys.argv) > 1 else 20261125
random.seed(SEED)

FLAG_SETS = ['', '-m', '-L', '-l -w', '-l -w -m', '-l -w -L', '-l -m', '-l -c', '-l -w -c', '-l -c -m', '-m -L', '-l -w -c -L', '-l -w -c -m', '-l -w -m -c -L']
PIECES = [b'a',b'b',b'0',b'9',b' ',b'\t',b'\n',b'\r',b'\x0b',b'\x0c',
          b'\xc3\xa9',b'\xc3\x89',b'\xc2\xa0',b'\xc2\xa2',b'\xc2\xa9',
          b'\xe2\x82\xac',b'\xe4\xb8\xad',b'\xe2\x80\x93',b'\xe2\x80\x94',b'\xe2\x80\x8b',
          b'\xf0\x9f\x98\x80',b'\xf4\x8f\xbf\xbf',b'\xf0\x90\x80\x80',
          b'\xcc\x81',b'\xcc\x82',b'\xe0\xa1\xa8',b'\xd0\xbf',b'\xd1\x80',
          b'\xe1\x84\x80',b'\xe1\x85\xa1',b'\xe3\x80\x80',b'\xef\xbc\x81',b'\xef\xbd\xa1',b'\xe1\x84\x80', b'\xe1\x85\xa1']
contents = set([b'', b'\n', b'a', b'abc\n', b'\xe4\xb8\xad\n', b'\xc3\xa9\xc3\x89\n', b'\xf0\x9f\x98\x80\n', b'e\xcc\x81\n', b'\x09\xe4\xb8\xad\n'])
for _ in range(1400):
    n = random.randint(0, 24)
    b = b''.join(random.choice(PIECES) for _ in range(n))
    contents.add(b)
contents = sorted(contents, key=len)
lines = []
for flags in FLAG_SETS:
    for c in contents:
        lines.append((flags, c))
def esc(data: bytes) -> str:
    out = []
    for b in data:
        if 32 <= b < 127 and b != 0x5c: out.append(chr(b))
        elif b == 0x09: out.append('\\t')
        elif b == 0x0a: out.append('\\n')
        else: out.append('\\x%02x' % b)
    return ''.join(out)
with open(sys.argv[2], 'w', newline='\n', encoding='ascii') as f:
    for flags, c in sorted(lines, key=lambda t: (len(t[1]), t[0])):
        f.write(flags + '\t' + esc(c) + '\n')
print(f'cases={len(lines)}', file=sys.stderr)

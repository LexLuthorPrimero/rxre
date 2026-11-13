#!/usr/bin/env python3
"""R3-Fase2 hito 9 — corpus multibyte para wc -m (chars) en UTF-8 (es_AR.utf8).
Formato: hex-escapado por línea (secuencias UTF-8 válidas; sin bytes inválidos)."""
import random, sys
SEED = int(sys.argv[1]) if len(sys.argv) > 1 else 20261121
random.seed(SEED)

structured = [
    '', ' ', '\n', '\t', 'a', 'ab\n', 'a b\n', '\t\n', 'a\tb\n',
    '\xc3\xa9\n',                       # é (1 codepoint)
    'e\xcc\x81\n',                     # e + COMBINING ACUTE (2 codepoints)
    '\xc3\xa9\xc3\xa9\xe4\xb8\xad\n',  # é中é (3 codepoints)
    '\xf0\x9f\x98\x80\n',              # grinning face (1 codepoint, 4 bytes)
    '\xe4\xb8\xad\n',                  # 中 (1 codepoint, 3 bytes)
    '\xe2\x82\xac\n',                  # € (1 codepoint, 3 bytes)
    '\xc2\xa0\n',                      # NBSP (1 codepoint)
    'a\xc2\xa0b\n',                    # a NBSP b (3 chars)
    '\xe2\x80\x8b\n',                  # U+200B zero-width space (1 char)
    'a\xe2\x80\x8bb\n',                # a+ZWSP+b (3 chars)
    '\xf4\x8f\xbf\xbf\n',              # U+10FFFF
    '\xf0\x90\x80\x80\n',              # U+10000
    'e\xcc\x81\xcc\x82\n',             # e + TWO combining marks (3 codepoints)
    '\xc3\xa9a\xe4\xb8\xad\xf0\x9f\x98\x80\n',  # é a 中 🎉 (4 chars)
    'a\tb\xc3\xa9\x0a',                # a TAB b é LF
    '\xe2\x80\x84\n',                  # U+2014 em dash
    '\xe2\x80\x93\xe2\x80\x93\n',      # two en dashes
    'x\xe0\xa1\xa8y\n',                # Bengali digit (3 bytes)
    '\xd0\xbf\xd1\x80\xd0\xb8\xd0\xb2\xd0\xb5\xd1\x82\n',  # привет (6 chars)
    'x\xc3\xa9\xcc\x81y\n',            # mixed composed+combining
    'a\xc3\x89b\n',                    # É capital (2 bytes)
]
contents = set(structured)

PIECES = [b'a', b'b', b'c', b'0', b'9', b' ', b'\t', b'\n', b'\r', b'\v', b'\f',
          b'\xc3\xa9', b'\xc3\x89', b'\xc2\xa0', b'\xc2\xa2', b'\xc2\xa9',
          b'\xe2\x82\xac', b'\xe4\xb8\xad', b'\xe2\x80\x93', b'\xe2\x80\x84', b'\xe2\x80\x8b',
          b'\xf0\x9f\x98\x80', b'\xf4\x8f\xbf\xbf', b'\xf0\x90\x80\x80',
          b'\xcc\x81', b'\xcc\x82', b'\xe0\xa1\xa8']
for _ in range(1600):
    n = random.randint(0, 24)
    b = b''.join(random.choice(PIECES) for _ in range(n))
    # force valid utf-8 by construction; skip accidental invalid: PIECES are all valid
    contents.add(b.decode('utf-8'))
contents = sorted(contents, key=len)

def esc(s):
    out = []
    for ch in s:
        o = ord(ch)
        if 32 <= o < 127 and ch not in ('\\', '\t', '\n'):
            out.append(ch)
        else:
            bs = ch.encode('utf-8')
            out.extend('\\x%02x' % b for b in bs)
    return ''.join(out)

with open(sys.argv[2], 'w', newline='\n', encoding='ascii') as f:
    for c in contents:
        f.write(esc(c) + '\n')
print(f'cases={len(contents)} sealed', file=sys.stderr)

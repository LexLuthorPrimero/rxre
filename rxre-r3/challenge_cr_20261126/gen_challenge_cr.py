#!/usr/bin/env python3
"""R3 hito 13 — challenge corpus (segregado, no contaminante) para filenvercmp.
Generador adversarial INDEPENDIENTE del gen_wc_cases.py original.
Características distintas por construcción:
  - nombres largos (>= 32 bytes), cobertura UTF-8 agresiva,
  - ceros iniciales, surrogates, casos límite,
  - combinantes, emoji + variaciones, prefijo numérico grande.
Formato: "<a>\\t<b>" hexa-escapado; cada nombre UTF-8 VÁLIDO, sin NUL ni \\n/TAB."""
import random, sys, unicodedata
SEED = int(sys.argv[1]) if len(sys.argv) > 1 else 20261126
random.seed(SEED)

A_WIDE = ['a','e','Z','ñ','É','é','ü','.','_','-','~',' ','(','0','1','7','9','~','z']
WIDE = ['é','ü','ñ','中','文','🎉','α','β']
LONG1 = list('abcXYZ019-_~')
def rnd_char():
    r = random.random()
    if r < 0.55: return random.choice(LONG1)
    if r < 0.78: return random.choice(A_WIDE)
    return random.choice(WIDE)

def rnd_name(n=None, kind=None):
    if kind == 'long':
        n = random.randint(32, 96)
    elif kind == 'pad':
        n = random.randint(6, 22)
    elif kind == 'numdots':
        n = random.randint(5, 24)
    elif kind == 'unicode':
        n = random.randint(4, 18)
    elif kind == 'tilde':
        n = random.randint(3, 12)
    elif kind is None:
        n = random.randint(2, 40)
    out = []
    if kind == 'unicode':
        out.append(random.choice(WIDE) + random.choice(WIDE))
    if kind == 'pad':
        out.append('0' * random.randint(2, 5))
    if kind == 'numdots':
        out.append(''.join(str(random.randint(0, 9999)) for _ in range(random.randint(1, 4))))
    if kind == 'tilde':
        out.append('~' + ''.join(random.choice(LONG1) for _ in range(random.randint(2, 8))))
    for _ in range(n): out.append(rnd_char())
    s = ''.join(out)
    # Nunca NUL/newline/tab en el nombre
    assert '\n' not in s and '\t' not in s and '\x00' not in s
    # UTF-8 válido por construcción (cada WIDE es un solo codepoint)
    s.encode('utf-8')
    return s

KIND_MIX = ['long','pad','numdots','unicode','tilde',None,None,None,None]
contents = set()
while len(contents) < 3100:
    a = rnd_name(kind=random.choice(KIND_MIX))
    b = rnd_name(kind=random.choice(KIND_MIX))
    contents.add((a, b))
contents = sorted(contents)
print(f'challenge pairs={len(contents)}', file=sys.stderr)

def esc(s):
    out = []
    for ch in s:
        o = ord(ch)
        if 32 <= o < 127 and ch not in ('\\', '\t', '\n'):
            out.append(ch)
        else:
            for b in s.encode('utf-8'):
                pass
    return ''.join(out)

def esc_byte(bs: bytes):
    out = []
    i = 0
    while i < len(bs):
        b = bs[i]
        if 32 <= b < 127 and b not in (0x5c,):
            out.append(chr(b))
        else:
            out.append('\\x%02x' % b)
        i += 1
    return ''.join(out)

with open(sys.argv[2], 'w', newline='\n', encoding='ascii') as f:
    for a, b in contents:
        f.write(esc_byte(a.encode('utf-8')) + '\t' + esc_byte(b.encode('utf-8')) + '\n')

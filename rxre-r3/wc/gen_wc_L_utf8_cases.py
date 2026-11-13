#!/usr/bin/env python3
"""R3-Fase2 hito 10 — corpus multibyte para wc -L en es_AR.utf8.
Formato: hex-escapado por línea (UTF-8 válido únicamente)."""
import random, sys
SEED = int(sys.argv[1]) if len(sys.argv) > 1 else 20261123
random.seed(SEED)
B = bytes
structured = [
    '', ' ', 'a', 'abc\n', 'a b c\n',
    '\u4e2d\n',                        # 中 (W, 2)
    '\u4e2d\u4e2d\n',                  # 中中 (4)
    'a\u4e2db\n',                     # a中b (4)
    '\u3000\n',                        # IDEOGRAPHIC SPACE (F, 2)
    '\u3000\u3000\n',                  # 4
    'a\u3000b\n',                     # 4
    'a\u0301b\n',                     # a+COMB acute (1+0+1 = 2? nativo: 2)
    'e\u0301\n',                      # e + combining = 1
    'e\u0301e\u0301\n',                # 2
    '\u4e2d\u0301\n',                 # 中+combining = 2
    'a\u0301'*4 + '\n',               # 4
    '\ud55c\n',                       # 한 composed (2)
    '\u1100\u1161\n',                 # 한 decomposed (L: Cho 2 + Jung 0 = 2)
    '\u1100\u1161\u1100\u1161\n',     # 4
    '\uff01\uff01\n',                 # !! fullwidth (F, 2+2=4)
    '\uff00\uff65\n',                 # fullwidth zero + halfwidth middle dot (2+1=3)
    '\uff61\uff61\uff61\n',           # halfwidth ×3 (1 each = 3)
    '\U0001f600\n',                   # grinning face W=2
    'x\U0001f600y\n',                 # 4
    '\u200b\u200b\n',                 # ZWSP (Cf, 0)
    'a\u200bb\n',                     # 2
    'a\u2069b\n',                     # pop isolate (Cf, 0)
    'a\u00adb\n',                     # soft hyphen (1, Cf visible)
    'a\u00ada\u00adb\n',               # 4
    'a\ufaffb\n',                     # unassigned (Cn, 0) → 2
    '\u31f0\u31f1\n',                 # kana stroke (W, 2 each)
    '\u1160\n',                       # JUNGSEONG FILLER alone (0)
    '\u1161\u1161\n',                 # 2 fillers (0)
    '\u1161a\n',                      # filler+a (1)
    '\t\u4e2d\n',                     # TAB+中 (8)
    'a\t\u4e2dbell\n',                # a TAB 中 b → 8 + 2 + 4 = 14? verifica nativo
    'long line of ascii text here\nshort\nb中ort\n',
    '\u4e2d\u0301a\nb\n',             # 中+comb+a (3) / b (1)
    '\U0001f600\U0001f600\n',         # 4
    'a\tb\ncd\x85e\n',                # control C1 (0 width via rule)
]
contents = set(structured)
PIECES = ['a','b','c','0','9',' ','\t','\n','\r','\v','\f',
          '\u00e9','\u00a0','\u4e2d','\u6c34','\u3000','\u3042','\uac00','\ud55c',
          '\u1100','\u1161','\uff01','\uff61','\U0001f600','\u0301','\u0327','\u200b','\u2066','\u2069','\u00ad','\ufaff','\u2e80','\u31ff']
for _ in range(1600):
    n = random.randint(0, 20)
    contents.add(''.join(random.choice(PIECES) for _ in range(n)))
contents = sorted(contents, key=len)
def esc(s):
    out = []
    for ch in s:
        o = ord(ch)
        if 32 <= o < 127 and ch not in ('\\', '\t', '\n'):
            out.append(ch)
        else:
            for bch in ch.encode('utf-8'):
                out.append('\\x%02x' % bch)
    return ''.join(out)
with open(sys.argv[2], 'w', newline='\n', encoding='ascii') as f:
    for c in contents:
        f.write(esc(c) + '\n')
print(f'cases={len(contents)}', file=sys.stderr)

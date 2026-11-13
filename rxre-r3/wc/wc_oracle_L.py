#!/usr/bin/env python3
"""Oracle runner (hito 10, LC_ALL=es_AR.utf8): `wc -L` per case -> chars per line."""
import subprocess, sys, re, os
SRC, OUT, WORKDIR = sys.argv[1], sys.argv[2], sys.argv[3]
os.makedirs(WORKDIR, exist_ok=True)
line_re = re.compile(r'^\s*(\d+)\s')
def unesc(s):
    out = bytearray(); i = 0
    while i < len(s):
        if s[i] == '\\' and s[i+1] == 'x':
            out.append(int(s[i+2:i+4], 16)); i += 4
        else:
            out.append(ord(s[i])); i += 1
    return bytes(out)
n = 0
with open(SRC) as f, open(OUT, 'w') as m:
    for raw in f:
        content = unesc(raw.rstrip('\n'))
        path = os.path.join(WORKDIR, f'case_{n:05d}')
        with open(path, 'wb') as fh: fh.write(content)
        r = subprocess.run(['wc', '-L', path], capture_output=True,
                           env={'LC_ALL': 'es_AR.utf8', 'PATH': '/usr/bin:/bin'})
        mm = line_re.match(r.stdout.decode())
        if not mm:
            m.write('CRASH\n'); print(f'CRASH caso {n}: {r.stdout!r} rc={r.returncode}', file=sys.stderr)
        else:
            m.write(f'{mm.group(1)}\n')
        n += 1
print(f'cases={n}', file=sys.stderr)

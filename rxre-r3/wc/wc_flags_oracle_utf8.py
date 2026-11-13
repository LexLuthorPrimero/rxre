#!/usr/bin/env python3
"""Oracle (hito 11, LC_ALL=es_AR.utf8): aplica flags por caso y graba la salida cruda.
Cada caso = '<flags> \\t <contenido hexa-escapado>'; locale UTF-8 forzado en env."""
import subprocess, sys, os
SRC, OUT, WORKDIR = sys.argv[1], sys.argv[2], sys.argv[3]
os.makedirs(WORKDIR, exist_ok=True)
def unesc(s):
    out = bytearray(); i = 0
    while i < len(s):
        if s[i] == '\\' and s[i+1] == 'x': out.append(int(s[i+2:i+4], 16)); i += 4
        else: out.append(ord(s[i])); i += 1
    return bytes(out)
n = 0
with open(SRC) as f, open(OUT, 'w') as m:
    for raw in f:
        flags, content = raw.rstrip('\n').split('\t', 1)
        data = unesc(content)
        args = ['wc'] + (flags.split() if flags else [])
        r = subprocess.run(args, input=data, capture_output=True,
                           env={'LC_ALL': 'es_AR.utf8', 'PATH': '/usr/bin:/bin'})
        out = r.stdout.decode('utf-8', errors='replace').rstrip('\n')
        out = ' '.join(out.split())
        m.write((out if out else 'CRASH') + '\n')
        if r.returncode != 0:
            print(f'caso {n}: rc={r.returncode} stderr={r.stderr.decode("utf-8", "replace")[:120]!r}', file=sys.stderr)
        n += 1
print(f'cases={n}', file=sys.stderr)

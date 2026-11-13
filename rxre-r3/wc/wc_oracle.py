#!/usr/bin/env python3
"""Oracle runner (hito 1, LC_ALL=C): lee corpus escapado, crea archivo por caso,
ejecuta /usr/bin/wc (salida por defecto) y escribe 'lines words bytes' por caso.
NO escribe el nombre del archivo ni la entrada en la matriz."""
import subprocess, sys, re, os

SRC, OUT, WORKDIR = sys.argv[1], sys.argv[2], sys.argv[3]
os.makedirs(WORKDIR, exist_ok=True)
line_re = re.compile(r'^\s*(\d+)\s+(\d+)\s+(\d+)\s')

def unesc(s):
    out = bytearray()
    i = 0
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
        with open(path, 'wb') as fh:
            fh.write(content)
        r = subprocess.run(['wc', path], capture_output=True, env={'LC_ALL': os.environ.get('LC_ALL', 'C'), 'PATH': '/usr/bin:/bin'})
        m_out = r.stdout.decode()
        mm = line_re.match(m_out)
        if not mm:
            m.write('CRASH\n')
            print(f'CRASH caso {n} salida={m_out!r} rc={r.returncode}', file=sys.stderr)
        else:
            m.write(f'{mm.group(1)} {mm.group(2)} {mm.group(3)}\n')
        n += 1
print(f'cases={n}', file=sys.stderr)

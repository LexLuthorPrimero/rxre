#!/usr/bin/env python3
"""Oracle runner (hito 15, LC_ALL=es_AR.utf8): crea el árbol desde el corpus sellado,
construye la lista NUL-terminada y ejecuta el GNU nativo wc --files0-from.
Modo: default | -l"""
import subprocess, sys, os, re, hashlib, shutil
SRC, OUT, WORKDIR, MODE = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4]
os.makedirs(WORKDIR, exist_ok=True)
shutil.rmtree(WORKDIR, ignore_errors=True)
os.makedirs(WORKDIR)
def unesc(s):
    out = bytearray(); i = 0
    while i < len(s):
        if s[i] == '\\' and s[i+1] == 'x': out.append(int(s[i+2:i+4], 16)); i += 4
        else: out.append(ord(s[i])); i += 1
    return bytes(out)
names = []
with open(SRC) as f:
    for raw in f:
        name, content = raw.rstrip('\n').split('\t', 1)
        with open(os.path.join(WORKDIR, name), 'wb') as fh:
            fh.write(unesc(content))
        names.append(name)
list_path = os.path.join(WORKDIR, 'list.bin')
with open(list_path, 'wb') as fh:
    for nm in names:
        fh.write(nm.encode() + b'\0')
args = ['wc', '--files0-from=' + list_path]
if MODE == '-l': args = ['wc', '-l', '--files0-from=' + list_path]
r = subprocess.run(args, capture_output=True, cwd=WORKDIR, env={'LC_ALL': 'es_AR.utf8', 'PATH': '/usr/bin:/bin'})
with open(OUT, 'wb') as f:
    f.write(r.stdout)
print(f'exit={r.returncode} files={len(names)} stdout_bytes={len(r.stdout)}', file=sys.stderr)

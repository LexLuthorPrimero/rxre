import subprocess, sys, os
SRC = 'cases_seed20261115.txt'
WORK = 'workf0'
def unesc(s):
    out = bytearray(); i = 0
    while i < len(s):
        if s[i] == '\\' and s[i+1] == 'x': out.append(int(s[i+2:i+4],16)); i += 4
        else: out.append(ord(s[i])); i += 1
    return bytes(out)
mism = 0; total = 0; crash = 0
for i, raw in enumerate(open(SRC)):
    content = unesc(raw.rstrip('\n'))
    name = f'case_{i:05d}'
    p = os.path.join(WORK, name)
    open(p, 'wb').write(content)
    direct = subprocess.run(['wc', p], capture_output=True, env={'LC_ALL':'C','PATH':'/usr/bin:/bin'}).stdout.split()[:3]
    man = p + '.manifest'
    open(man, 'wb').write(p.encode() + b'\0')
    f0 = subprocess.run(['wc', f'--files0-from={man}'], capture_output=True, env={'LC_ALL':'C','PATH':'/usr/bin:/bin'}).stdout.split()[:3]
    if direct != f0:
        mism += 1
        if mism <= 5: print(f'MISMATCH caso {i} direct={direct} files0={f0}')
    total += 1
print(f'total={total} mismatches={mism}')

import subprocess
out = []
with open('/tmp/rxre-r3/oracle/pair_matrix.csv') as f:
    for line in f:
        i, j, rc = line.strip().split(',')
        out.append((int(i), int(j), int(rc)))

chars = []
for i in range(1, 128): chars.append(i)
rel = {}
for i, j, rc in out:
    rel[(i, j)] = rc
    rel[(j, i)] = -rc

def cmp_(a, b):
    if a == b: return 0
    return rel[(a, b)] if a < b else -rel[(b, a)]

order = []
used = set()
for c in chars:
    i = 0
    while i < len(order) and cmp_(c, order[i]) >= 0:
        i += 1
    order.insert(i, c)
print(' == order (min→max) ==')
for i, c in enumerate(order):
    ch = chr(c) if 32 <= c < 127 else f'0x{c:02x}'
    print(f'{i:3d} 0x{c:02x} {ch!r}')

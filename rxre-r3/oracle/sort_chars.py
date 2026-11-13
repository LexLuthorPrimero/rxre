import csv
rel = {}
chars = list(range(1, 128))
for i, j, rc in csv.reader(open('pair_matrix.csv')):
    i, j, rc = int(i), int(j), int(rc)
    rel[(i, j)] = rc if i < j else -rc

def cmp_(a, b):
    if a == b: return 0
    return rel[(min(a, b), max(a, b))] if a < b else -rel[(min(a, b), max(a, b))]

# verify antisymmetry & transitivity on full scan
bad = 0
for i in chars:
    for j in chars:
        for k in chars:
            a, b, c = cmp_(i, j), cmp_(j, k), cmp_(i, k)
            if a <= 0 and b <= 0 and c > 0: bad += 1
            if a >= 0 and b >= 0 and c < 0: bad += 1
print('transitivity violations:', bad)

order = []
for c in chars:
    lo, hi = 0, len(order)
    while lo < hi:
        mid = (lo + hi) // 2
        if cmp_(c, order[mid]) >= 0:
            lo = mid + 1
        else:
            hi = mid
    order.insert(lo, c)
print()
for i, c in enumerate(order):
    print(f'[{i:3d}] {chr(c) if 32 <= c < 127 else f"0x{c:02x}"} (0x{c:02x}={c})')

import csv
from collections import defaultdict

rel = {}
chars = list(range(1, 128))
for i, j, rc in csv.reader(open('pair_matrix.csv')):
    i, j, rc = int(i), int(j), int(rc)
    rel[(i, j)] = rc
    rel[(j, i)] = -rc

# Confirm symmetry
ok_sym = all(rel[(j,i)] == -rel[(i,j)] for (i,j) in rel)
print('symmetric' if ok_sym else 'ASYMMETRY!')

# Build groups by equality (rc==0)
groups = defaultdict(list)
for c in chars:
    for other in list(groups):
        if 0 == rel.get((c, other), rel.get((other, c), None)) == 0:
            # careful: keys always stored both
            groups[other].append(c)
            break
    else:
        groups[c].append(c)

# verify transitivity of groups within mapped classes
# compute class equalities precisely
equal = {}
for c in chars:
    for d in chars:
        if rel[(c, d)] == 0:
            equal.setdefault(c, set()).add(d)
for c, s in equal.items():
    pass

# check transitivity of relation
# if a<b and b<c -> a<c
for c in chars:
    if rel.get((c, c)) != 0:
        print('self not zero!', c)
print('self zeros done')

# print group structure using a greedy clustering approach
parent = {c: c for c in chars}
def find(x):
    while parent[x] != x:
        parent[x] = parent[parent[x]]
        x = parent[x]
    return x
def union(a, b):
    ra, rb = find(a), find(b)
    if ra != rb: parent[ra] = rb

for c in chars:
    for d in chars:
        if rel[(c, d)] == 0: union(c, d)

groups = defaultdict(list)
for c in chars:
    groups[find(c)].append(c)
print('\n== equivalence classes by rc==0 ==')
for k in sorted(groups, key=lambda x: find(x)):
    g = groups[k]
    if len(g) > 1:
        print(f'{k}: {[chr(c) if 32<=c<127 else f"0x{c:02x}" for c in g]}')

import csv, subprocess
from itertools import combinations

chars = [bytes([i]) for i in range(1, 128)]
def char(i):
    return bytes([i])
args = []
for i, a in enumerate(chars):
    for b in chars:
        if a < b:
            args.append((a, b))
subprocess; 
print('pairs', len(args))

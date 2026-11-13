import random, subprocess, sys
random.seed(20261115)
ALPHABET = list('abcdefghijklmnopqrstuvwxyz0123456789') + [' ', '\t', '\n', '\r', '\v', '\f', '.', '~', '_', '\x7f', '\xff', '\x01']
ALPHABET = [ord(c) if isinstance(c, str) else c for c in ALPHABET]
mismatches = 0
for i in range(20000):
    n = random.randint(0, 80)
    data = bytes(random.choice(ALPHABET) for _ in range(n))
    with open('work/stress', 'wb') as f: f.write(data)
    out = subprocess.run(['wc', 'work/stress'], capture_output=True, env={'LC_ALL': 'C', 'PATH': '/usr/bin:/bin'}).stdout.split()
    L, W, B = int(out[0]), int(out[1]), int(out[2])
    lines = data.count(b'\n')
    in_word = 0; words = 0
    for b in data:
        if b in (0x20, 0x09, 0x0a, 0x0b, 0x0c, 0x0d): in_word = 0
        else:
            if not in_word: words += 1
            in_word = 1
    if (L, W, B) != (lines, words, len(data)):
        mismatches += 1
        if mismatches <= 10:
            print('MISMATCH', repr(data[:80]), 'native', (L, W, B), 'model', (lines, words, len(data)))
print(f'total=20000 mismatches={mismatches}')

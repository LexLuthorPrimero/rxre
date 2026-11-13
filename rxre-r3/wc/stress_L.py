import random, subprocess
random.seed(20261117)
ALPHABET = [ord(c) for c in 'abcXYZ019 '] + [0x09, 0x0a, 0x0b, 0x0c, 0x0d, 0x7f, 0xff, 0x01, 0x20, 0x7e]
def model(data):
    lines = 0; words = 0; in_word = 0; cur = 0; mx = 0
    for b in data:
        if b == 0x0a:
            lines += 1; cur = 0
        if b in (0x20, 0x09, 0x0a, 0x0b, 0x0c, 0x0d): in_word = 0
        else:
            if not in_word: words += 1
            in_word = 1
        if b == 0x09: cur = (cur + 8) & ~7
        elif b in (0x0c, 0x0d): cur = 0
        elif 0x20 <= b <= 0x7e: cur += 1
        if cur > mx: mx = cur
    if cur > mx: mx = cur
    return lines, words, len(data), mx
mism = 0
for i in range(30000):
    n = random.randint(0, 80)
    data = bytes(random.choice(ALPHABET) for _ in range(n))
    with open('work/stress', 'wb') as f: f.write(data)
    out = subprocess.run(['wc', '-L', 'work/stress'], capture_output=True, env={'LC_ALL': 'C', 'PATH': '/usr/bin:/bin'}).stdout.split()
    Lm = int(out[0])
    _, _, _, m = model(data)
    if m != Lm:
        mism += 1
        if mism <= 5:
            print('MISMATCH', repr(data[:80]), 'native', Lm, 'model', m)
print(f'total=30000 mismatches={mism}')

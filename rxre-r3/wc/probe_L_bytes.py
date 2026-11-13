import subprocess
controls = {0x0a, 0x0b, 0x0c, 0x0d, 0x09}
widths = {}
for b in range(256):
    env = {'LC_ALL': 'C', 'PATH': '/usr/bin:/bin'}
    data = b'B' + bytes([b]) + b'B\n'
    with open('work/L_bytes', 'wb') as f: f.write(data)
    L = int(subprocess.run(['wc', '-L', 'work/L_bytes'], capture_output=True, env=env).stdout.split()[0])
    widths[b] = L - 2  # subtract two printable 'B' = base 2
zero = sorted(k for k, v in widths.items() if v == 0)
one  = sorted(k for k, v in widths.items() if v == 1)
other = {k: v for k, v in widths.items() if v not in (0, 1)}
print('width 0 bytes:', [hex(b) for b in zero])
print('width 1 bytes:', [hex(b) for b in one])
print('other widths:', other if other else 'none')

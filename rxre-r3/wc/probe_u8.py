import subprocess
env = {'LC_ALL': 'es_AR.utf8', 'PATH': '/usr/bin:/bin'}
NL = 10
seps = []
for c in range(256):
    with open('work/pb', 'wb') as f: f.write(b'A' + bytes([c]) + b'A')
    out = subprocess.run(['wc', '-w', 'work/pb'], capture_output=True, env=env).stdout.split()
    if out[0].decode() == '2':
        seps.append(c)
print('UTF-8 separators (single-byte as lone byte):', [hex(b) for b in seps])
# seq of NBSP in utf8 (c2a0), tested via A<nbsp>A:
with open('work/pb', 'wb') as f: f.write(b'A\xc2\xa0A')
print('A NBSP A (utf8):', subprocess.run(['wc', '-w', 'work/pb'], capture_output=True, env=env).stdout.split()[0].decode())

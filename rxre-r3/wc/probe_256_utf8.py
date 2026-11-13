import subprocess
env = {'LC_ALL': 'es_AR.utf8', 'PATH': '/usr/bin:/bin'}
seps = []
for c in range(256):
    with open('work/pb', 'wb') as f: f.write(b'A' + bytes([c]) + b'A')
    out = subprocess.run(['wc', '-w', 'work/pb'], capture_output=True, env=env).stdout.split()
    if out[0].decode() == '2':
        seps.append(c)
print('es_AR.utf8 separators:', [hex(b) for b in seps])

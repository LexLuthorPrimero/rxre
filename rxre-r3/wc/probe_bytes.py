import subprocess
def words(data, env_extra=None, flags='-w'):
    with open('work/pb', 'wb') as f: f.write(data)
    env = {'LC_ALL': 'C', 'PATH': '/usr/bin:/bin'}
    env.update(env_extra or {})
    out = subprocess.run(['wc'] + flags.split() + ['work/pb'], capture_output=True, env=env).stdout.split()
    return int(out[-2]) if flags in ('-w', '-w -L') else int(out[-1])
sep_c, sep_e = [], []
for c in range(256):
    data = b'A' + bytes([c]) + b'A'
    words_c = words(data, {'LC_ALL': 'C'})
    words_e = words(data, {'LC_ALL': 'es_AR.utf8'})
    if words_c == 2: sep_c.append(c)
    if words_e == 2: sep_e.append(c)
print('C   separators (word-break):', [hex(b) for b in sep_c])
print('es  separators (word-break):', [hex(b) for b in sep_e])

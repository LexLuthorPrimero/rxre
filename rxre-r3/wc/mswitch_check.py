import os, subprocess
ALL = 0; MISMATCH = 0
for src in ['cases_seed20261114.txt','cases_seed20261115.txt','cases_wcflags_seed20261116.txt','cases_wcL_seed20261117.txt','cases_high_seed20261118.txt']:
    total = mism = 0
    with open(src) as f:
        for line in f:
            raw = line.rstrip('\n')
            # content only (flags may exist in flags corpora; strip leading flags when present)
            parts = raw.split('\t', 1)
            content_esc = raw if len(parts) == 1 else parts[1]
            # byte length of escaped content
            out = bytearray(); i = 0
            while i < len(content_esc):
                if content_esc[i] == '\\' and content_esc[i+1] == 'x':
                    out.append(int(content_esc[i+2:i+4], 16)); i += 4
                else:
                    out.append(ord(content_esc[i])); i += 1
            p = 'work/mcheck'
            open(p, 'wb').write(out)
            m = int(subprocess.run(['wc', '-m', p], capture_output=True, env={'LC_ALL': 'C', 'PATH': '/usr/bin:/bin'}).stdout.split()[0])
            b = int(subprocess.run(['wc', '-c', p], capture_output=True, env={'LC_ALL': 'C', 'PATH': '/usr/bin:/bin'}).stdout.split()[0])
            if m != b:
                mism += 1
                if mism <= 3:
                    print(f'MISMATCH {src}: -m={m} -c={b} content_len={len(out)}')
            total += 1
    print(f'{src}: {total} casos, mismatches(-m vs -c) = {mism}')
    ALL += total; MISMATCH += mism
print(f'TOTAL: {ALL} casos, mismatches: {MISMATCH}')

chars = [chr(0),' ', '!', '"', '#', '%', '&', "'", '(', ')', '*', '+', ',', '-', '.', '/',
         '0','1','2','5','8','9', ':', ';', '<', '=', '>', '?', '@',
         'A','B','Z','a','b','z', '~', '{', '}', '_', '\x7f', '\xe9']
lines = ['break trace.c:19', 'run', 'set $ls = ls', 'set $p = (int (*)(const char*, char*))($ls + 0x4fa0)']
for c in chars:
    esc = c.encode('unicode_escape').decode()
    lines.append(f'printf "ord(%s c vs 0x61 a) = ", $p("{c if c not in ("\"","\\") else ""}", "a")\n') if False else None
for c in chars:
    e = c if c not in ('"', '\\') else '\\' + c
    lines.append(f'printf "ord({e!r} vs a) = "' + '\n' + f'x/s "{e}"')
# simpler: use decimal cast of function
lines = ['break trace.c:19', 'run', 'set $ls = ls', 'set $p = (int (*)(const char*, char*))($ls + 0x4fa0)']
for c in chars:
    e = c.encode('ascii', 'ignore')
    try:
        c2 = e.decode()
    except: continue
    c3 = c2 if c2 not in '"\\' else '\\"'
    lines.append(f'p $p("{c3}","a")')
import pathlib
pathlib.Path('probe2.gdb').write_text('\n'.join(lines) + '\nquit\n')

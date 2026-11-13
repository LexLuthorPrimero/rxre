import subprocess, os
env = {'PATH': '/usr/bin:/bin'}   # default locale es_AR.utf8
variants = [
    ('é\\u00e9', b'\xc3\xa9'),
    ('DEL', b'\x7f'),
    ('0x80', b'\x80'),
    ('0x85', b'\x85'),
    ('NBSP c2a0', b'\xc2\xa0'),
    ('ENP+én', b'\xc3\xa9\xa0\xc3\xa9'),
    ('narrow nbsp e280af', b'\xe2\x80\xaf'),
    ('line sep e280a8', b'\xe2\x80\xa8'),
    ('para sep e280a9', b'\xe2\x80\xa9'),
    ('ideographic e38080', b'\xe3\x80\x80'),
    ('zero-width e2808b', b'\xe2\x80\x8b'),
    ('zero-width e2808c', b'\xe2\x80\x8c'),
    ('zero-width e2808d', b'\xe2\x80\x8d'),
    ('BOM efbbbf', b'\xef\xbb\xbf'),
    ('a nbsp b', b'a\xc2\xa0b'),
    ('a nbsp b latin1', b'a\xa0b'),
    ('a DEL b', b'a\x7fb'),
    ('a 0x85 b', b'a\x85b'),
    ('a 0x80 b', b'a\x80b'),
    ('leven w', b'a\xe2\x80\x8eb'),
]
for name, data in variants:
    with open('work/pb', 'wb') as f: f.write(data)
    out = subprocess.run(['wc', '-w', 'work/pb'], capture_output=True, env=env).stdout.split()
    print(f'{name:28s} -> W={out[0].decode()}')

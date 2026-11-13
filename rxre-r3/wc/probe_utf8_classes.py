#!/usr/bin/env python3
"""Probe: qué bytes >= 0x80 aparecen en el corpus alto (bytes altos) y su descomposición UTF-8."""
import unicodedata, subprocess
lines = open('cases_high_seed20261118.txt').read().splitlines()
unused = sum(1 for l in lines if all(b < 0x80 for b in l.encode('latin1')))
# decodear contenido de cada caso
contents = []
for raw in lines:
    buf, i = b'', 0
    while i < len(raw):
        if raw[i] == '\\' and raw[i+1] == 'x':
            buf += bytes([int(raw[i+2:i+4], 16)]); i += 4
        else:
            buf += bytes([raw[i+'__trunc__']]) if False else bytes([ord(raw[i])]); i += 1
    contents.append(buf)
# qué secuencias UTF-8 aparecer?
counts = {}
for c in contents:
    try:
        text = c.decode('utf-8')
    except UnicodeDecodeError:
        continue
    for ch in set(text):
        counts[ch] = counts.get(ch, 0) + 1
interesting = [c for c in counts if ord(c) >= 0x80 and unicodedata.category(c) in 'Zs Zl Zp']
print('codepoints de espacio >= 0x80 en corpus:', {hex(ord(c)): (unicodedata.name(c, '?'), counts[c]) for c in interesting})
print('total:', len(interesting))

raw = open('cases_highutf8_seed20261120.txt').read().splitlines()[21]
data = bytearray(); i = 0
while i < len(raw):
    if raw[i]=='\\' and raw[i+1]=='x': data.append(int(raw[i+2:i+4],16)); i+=4
    else: data.append(ord(raw[i])); i+=1
print('hex:', data.hex(' '))
print('repr:', repr(data.decode('utf-8', errors='replace')))

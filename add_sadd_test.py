import re
import sys

file_path = "/home/lucas/Escritorio/rxre/KytePS5-Source/tests/ShaderRecompilerComputeTests.cpp"

print("Processing:", file_path)

with open(file_path, 'r') as f:
    content = f.read()

# Find the position after the last S_SUB_I32 case
# Looking for: append_case(true, EncodeSop2(0x03, 17, 15, 16), 25);
pattern = r'append_case\(true, EncodeSop2\(0x03, 17, 15, 16\), 25\);'

replacement = '''append_case(true, EncodeSop2(0x03, 17, 15, 16), 25);  // S_SUB_I32

  // S_ADD_U32 carry-out test: 0xFFFFFFFF + 1 = 0x00000000, SCC=1
  AppendSMovLiteral(&code, 35, 0xffffffffu);  // s[35] = 0xFFFFFFFF
  code.push_back(EncodeSMovB32(36, InlineU32(1)));  // s[36] = 1
  append_case(true, EncodeSop2(0x00, 34, 35, 36), 28);  // S_ADD_U32 s[34], s[35]+s[36], capture SCC in s[28]

  // S_ADD_U32 no-carry contrast: 0xFFFFFFFF + 0 = 0xFFFFFFFF, SCC=0
  AppendSMovLiteral(&code, 38, 0xffffffffu);  // s[38] = 0xFFFFFFFF (already set above, explicit for clarity)
  code.push_back(EncodeSMovB32(39, InlineU32(0)));  // s[39] = 0
  append_case(true, EncodeSop2(0x00, 37, 38, 39), 29);  // S_ADD_U32 s[37], s[38]+s[39], capture SCC in s[29]'''

new_content = re.sub(pattern, replacement, content)

if new_content == content:
    print("Regex not found, using line-based approach")
    lines = content.split('\n')
    for i, line in enumerate(lines):
        if 'append_case(true, EncodeSop2(0x03, 17, 15, 16), 25);' in line:
            new_lines = lines[:i+1]
            new_lines.append('  // S_ADD_U32 carry-out test: 0xFFFFFFFF + 1 = 0x00000000, SCC=1')
            new_lines.append('  AppendSMovLiteral(&code, 35, 0xffffffffu);  // s[35] = 0xFFFFFFFF')
            new_lines.append('  code.push_back(EncodeSMovB32(36, InlineU32(1)));  // s[36] = 1')
            new_lines.append('  append_case(true, EncodeSop2(0x00, 34, 35, 36), 28);  // S_ADD_U32, capture in s[28]')
            new_lines.append('  // S_ADD_U32 no-carry contrast: 0xFFFFFFFF + 0 = 0xFFFFFFFF, SCC=0')
            new_lines.append('  AppendSMovLiteral(&code, 38, 0xffffffffu);  // s[38] = 0xFFFFFFFF')
            new_lines.append('  code.push_back(EncodeSMovB32(39, InlineU32(0)));  // s[39] = 0')
            new_lines.append('  append_case(true, EncodeSop2(0x00, 37, 38, 39), 29);  // S_ADD_U32, capture in s[29]')
            new_lines.extend(lines[i+1:])
            content = '\n'.join(new_lines)
            print("Inserted after line", i+1)
            break
else:
    print("Regex replacement succeeded")

# Write back
with open(file_path, 'w') as f:
    f.write(new_content)

print("File updated successfully")
#!/usr/bin/env python3
"""
Parse SMU74_Firmware_Header from polaris12_smc.bin container.
Cross-validated against 7 independent oracles from source tree.
"""

import struct
import hashlib
import json
import sys
import os

CONTAINER_SIZE = 256
SMU7_FIRMWARE_HEADER_LOCATION = 0x20000

# SMU74_Firmware_Header fields in order (from smu74.h:559-590)
HEADER_FIELDS = [
    'Digest[0]', 'Digest[1]', 'Digest[2]', 'Digest[3]', 'Digest[4]',
    'Version', 'HeaderSize', 'Flags',
    'EntryPoint', 'CodeSize', 'ImageSize', 'Rtos',
    'SoftRegisters', 'DpmTable', 'FanTable', 'CacConfigTable', 'CacStatusTable',
    'mcRegisterTable', 'mcArbDramTimingTable', 'PmFuseTable', 'Globals',
    'ClockStretcherTable', 'VftTable', 'Reserved1',
    'AvfsTable', 'AvfsCksOffGbvTable', 'AvfsMeanNSigma', 'AvfsSclkOffsetTable'
]

# SMU74_SoftRegisters sizeof = 120 (0x78) from finding 1578
SOFTREGS_SIZE = 120
# DPM table size = 1884 (0x75C) from finding 081
DPM_SIZE = 1884
# SMC_RAM_END = 0x40000 from vegam_smumgr.h:32 / smu10_hwmgr.c:46
SMC_RAM_END = 0x40000

def sha256_file(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(65536), b''):
            h.update(chunk)
    return h.hexdigest()

def parse_container(d):
    """Parse the 256-byte container header at offset 0."""
    c = {}
    c['Digest0'] = struct.unpack_from('<I', d, 0)[0]
    c['Digest1'] = struct.unpack_from('<I', d, 4)[0]
    c['Digest2'] = struct.unpack_from('<I', d, 8)[0]
    c['Digest3'] = struct.unpack_from('<I', d, 12)[0]
    c['Digest4'] = struct.unpack_from('<I', d, 16)[0]
    c['Version'] = struct.unpack_from('<I', d, 20)[0]
    c['HeaderSize'] = struct.unpack_from('<I', d, 24)[0]
    c['Flags'] = struct.unpack_from('<I', d, 28)[0]
    c['DestAddr'] = struct.unpack_from('<I', d, 32)[0]
    c['CodeSize'] = struct.unpack_from('<I', d, 36)[0]
    c['ImageSize'] = struct.unpack_from('<I', d, 40)[0]
    c['Rtos'] = struct.unpack_from('<I', d, 44)[0]
    c['SoftRegisters'] = struct.unpack_from('<I', d, 48)[0]
    return c

def parse_firmware_header(d):
    """Parse SMU74_Firmware_Header at offset 0x100."""
    h = {}
    off = CONTAINER_SIZE
    for name in HEADER_FIELDS:
        h[name] = struct.unpack_from('<I', d, off)[0]
        off += 4
    return h

def run_oracles(h, container, filesize):
    """Run the 7 cross-validation oracles. Returns list of (name, ok, detail)."""
    results = []

    # 1. ImageSize == filesize - CONTAINER_SIZE
    ok1 = (h['ImageSize'] == filesize - CONTAINER_SIZE)
    results.append(('O1_ImageSize_matches_filesize', ok1,
        f"ImageSize={h['ImageSize']:#x} vs filesize-CONTAINER={filesize - CONTAINER_SIZE:#x}"))

    # 2. DestAddr == SMU7_FIRMWARE_HEADER_LOCATION (0x20000)
    ok2 = (container['DestAddr'] == SMU7_FIRMWARE_HEADER_LOCATION)
    results.append(('O2_DestAddr_is_0x20000', ok2,
        f"DestAddr={container['DestAddr']:#x}"))

    # 3. EntryPoint == 0x20000 + 0x100 (HeaderSize) = 0x20100
    # Also used as PC threshold in smu7_is_smc_ram_running
    ok3 = (h['EntryPoint'] == SMU7_FIRMWARE_HEADER_LOCATION + 0x100)
    results.append(('O3_EntryPoint_is_0x20100', ok3,
        f"EntryPoint={h['EntryPoint']:#x} (0x20000+0x100)"))

    # 4. SoftRegisters + sizeof(SMU74_SoftRegisters) == PmFuseTable
    # SOFTREGS_SIZE = 120 from finding 1578 (offset reconciliation)
    ok4 = (h['SoftRegisters'] + SOFTREGS_SIZE == h['PmFuseTable'])
    results.append(('O4_SoftRegs_plus_size_eq_PmFuseTable', ok4,
        f"SoftRegs={h['SoftRegisters']:#x} + {SOFTREGS_SIZE:#x} = {h['SoftRegisters'] + SOFTREGS_SIZE:#x} vs PmFuseTable={h['PmFuseTable']:#x}"))

    # 5. DpmTable + sizeof(SMU74_Discrete_DpmTable) == FanTable
    # DPM_SIZE = 1884 from finding 081
    ok5 = (h['DpmTable'] + DPM_SIZE == h['FanTable'])
    results.append(('O5_DpmTable_plus_size_eq_FanTable', ok5,
        f"DpmTable={h['DpmTable']:#x} + {DPM_SIZE:#x} = {h['DpmTable'] + DPM_SIZE:#x} vs FanTable={h['FanTable']:#x}"))

    # 6. Reserved1 == 0x20000 + firmware_header.HeaderSize (0xB4 from smu74.h)
    ok6 = (h['Reserved1'] == SMU7_FIRMWARE_HEADER_LOCATION + h['HeaderSize'])
    results.append(('O6_Reserved1_eq_0x20000_plus_HeaderSize', ok6,
        f"Reserved1={h['Reserved1']:#x} vs 0x20000+{h['HeaderSize']:#x}"))

    # 7. All table pointers within [0x20000, SMC_RAM_END) = [0x20000, 0x40000)
    table_fields = ['SoftRegisters', 'DpmTable', 'FanTable', 'CacConfigTable', 'CacStatusTable',
                    'mcRegisterTable', 'mcArbDramTimingTable', 'PmFuseTable', 'Globals',
                    'ClockStretcherTable', 'VftTable', 'AvfsTable',
                    'AvfsCksOffGbvTable', 'AvfsMeanNSigma', 'AvfsSclkOffsetTable']
    in_range = all(SMU7_FIRMWARE_HEADER_LOCATION <= h[f] < SMC_RAM_END or h[f] == 0 for f in table_fields)
    ok7 = (h['ImageSize'] <= SMC_RAM_END - SMU7_FIRMWARE_HEADER_LOCATION) and in_range
    results.append(('O7_all_tables_in_SMC_RAM_range', ok7,
        f"ImageSize={h['ImageSize']:#x} <= {SMC_RAM_END - SMU7_FIRMWARE_HEADER_LOCATION:#x}, all tables in [0x20000,0x40000)"))

    return results

def main():
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} <polaris12_smc.bin> [--json]", file=sys.stderr)
        return 1

    path = sys.argv[1]
    want_json = '--json' in sys.argv

    if not os.path.exists(path):
        print(f"File not found: {path}", file=sys.stderr)
        return 1

    with open(path, 'rb') as f:
        d = f.read()

    filesize = len(d)
    file_hash = sha256_file(path)

    container = parse_container(d)
    header = parse_firmware_header(d)
    oracles = run_oracles(header, container, filesize)

    out = {
        'file': path,
        'size': filesize,
        'sha256': file_hash,
        'container': container,
        'header': header,
        'oracles': [{'name': n, 'ok': o, 'detail': d} for n, o, d in oracles],
        'all_ok': all(o for _, o, _ in oracles)
    }

    if want_json:
        print(json.dumps(out, indent=2))
    else:
        print(f"File: {path} ({filesize} bytes)")
        print(f"SHA256: {file_hash}")
        print()
        print("Container header (offset 0):")
        for k, v in container.items():
            print(f"  {k:12s} = 0x{v:08x} ({v})")
        print()
        print("SMU74_Firmware_Header (offset 0x100):")
        for k, v in header.items():
            print(f"  {k:22s} = 0x{v:08x} ({v})")
        print()
        print("Oracles:")
        for name, ok, detail in oracles:
            status = "OK" if ok else "FAIL"
            print(f"  [{status}] {name}: {detail}")
        print()
        print(f"All oracles: {'PASS' if out['all_ok'] else 'FAIL'}")

    return 0 if out['all_ok'] else 1

if __name__ == '__main__':
    sys.exit(main())
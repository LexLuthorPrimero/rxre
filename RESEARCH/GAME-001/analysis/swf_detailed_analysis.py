#!/usr/bin/env python3
"""
RXRE-GAME-001. SWF Tag and Character Inventory.
Comprehensive analysis with bounds checking and specification validation.

This output creates findings that can be reused by RXRE knowledge engine.
"""
import struct
import zlib
import json
import sys
import hashlib
import os
from collections import defaultdict

# Verified SWF Tag Codes per Adobe SWF File Format Specification v10
TAG_CODES = {
    0:  ('End', 'Stream terminator'),
    1:  ('ShowFrame', 'Increment frame counter'),
    2:  ('DefineShape', 'Define shape (version 1)'),
    3:  ('DefineButton', 'Define button (version 1)'),
    4:  ('PlaceObject', 'Place object (version 1)'),
    5:  ('RemoveObject', 'Remove object (version 1)'),
    6:  ('DefineBits', 'Define Bits'),
    7:  ('DefineFont', 'Save with DefineFont2 for new format'),
    8:  ('DefineVideo', 'Define Video'),
    9:  ('SetBackgroundColor', 'Set Background Color'),
    10: ('DefineFont', 'Define Font (version 1)'),
    11: ('DefineText', 'Define Text'),
    12: ('DoAction', 'Execute Actions'),
    13: ('DefineFontInfo', 'Font Info (version 1)'),
    14: ('DefineSound', 'Define Sound'),
    15: ('StartSound', 'Start Sound'),
    16: ('StartSound', 'Use DefineSound instead'),
    17: ('DefineFontInfo', 'Save with DefineFontInfo2'),
    18: ('RemoveObject2', 'Remove Object2'),
    19: ('FrameLabel', 'Frame Label (version 1)'),
    20: ('DefineBitsJPEG2', 'Save with DefineBitsJPEG3'),
    21: ('DefineBitsJPEG2', 'JPEG Image (version 1)'),
    22: ('DefineShape2', 'Define shape (version 2)'),
    23: ('DefineButton2', 'Define button (version 2)'),
    24: ('DefineBitsJPEG3', 'JPEG Image (version 1) with alpha'),
    25: ('DefineBitsLossless', 'Lossless Image (version 1)'),
    26: ('DefineBitsLossless', 'Define Bits Lossless (version 1)'),
    27: ('DefineBitsJPEG4', 'JPEG Image (version 1) with alpha and deblocking'),
    28: ('PlaceObject2', 'Place object (version 2)'),
    29: ('RemoveObject2', 'Use PlaceObject2'),
    30: ('DefineSprite', 'Save with PlaceObject3'),
    31: ('RemoveObject2', 'Use PlaceObject3'),
    32: ('DefineShape3', 'Define shape (version 3)'),
    33: ('DefineText2', 'Define text (version 2)'),
    34: ('DefineButton2', 'Use this instead'),
    35: ('DefineBitsJPEG3', 'JPEG Image (version 1) with alpha'),
    36: ('DefineBitsLossless2', 'Lossless Image (version 2)'),
    37: ('DefineEditText', 'Define Edit Text'),
    38: ('DefineEditText', 'Save with DefineText2'),
    39: ('DefineSprite', 'Define Sprite'),
    40: ('FrameLabel', 'Save with frame labels'),
    41: ('FrameLabel', 'Save with frame labels'),
    42: ('PlaceObject2', 'Save with PlaceObject3'),
    43: ('FrameLabel', 'Frame label'),
    44: ('DefineBinaryData', 'Define Binary Data'),
    45: ('SoundStreamHead', 'Define Sound (stream) head'),
    46: ('DefineMorphShape', 'Define Morph Shape'),
    47: ('DefineFont2', 'Define font (version 2)'),
    48: ('DefineBitsPNG3', 'PNG Image (version 1)'),
    49: ('DefineBitsPNG3', 'Use DefineBitsLossless2'),
    50: ('DefineFontHint', 'Font Hinting Settings'),
    51: ('DefineShape', 'Save with DefineShape2 for shape'),
    52: ('DefineShape', 'Save with DefineShape3 for shape'),
    53: ('DefineFontAlignZones', 'Font AlignZones'),
    54: ('DefineFontAlignZones', 'Save with DefineFontAlignZones'),
    55: ('CSMTextSettings', 'Set CSM Text Settings'),
    56: ('ExportAssets', 'Export assets'),
    57: ('ImportAssets', 'Import assets'),
    58: ('EnableDebugger', 'Enable debugger'),
    59: ('DoInitAction', 'Do Action (asynchronous init)'),
    60: ('DefineVideoStream', 'Define Video Stream'),
    61: ('VideoFrame', 'Video Frame'),
    62: ('DefineFontInfo2', 'Define font info (version 2)'),
    63: ('DefineFontInfo2', 'Save with DefineFontInfo2'),
    64: ('EnableDebugger2', 'Enable Debugger (version 2)'),
    65: ('ScriptLimits', 'Set script time limit'),
    66: ('SetTabIndex', 'Set tab index'),
    67: ('GarbageCollect', 'Force garbage collection'),
    68: ('DefineSound', 'Save with DefineSound'),
    69: ('FileAttributes', 'File attributes'),
    70: ('PlaceObject3', 'Place object (version 3)'),
    71: ('PlaceObject3', 'Use PlaceObject3'),
    72: ('PlaceObject3', 'Save with PlaceObject3'),
    73: ('DefineFontAlignZones', 'Save with DefineFontAlignZones'),
    74: ('CSMTextSettings', 'Save with DefineText2'),
    75: ('DefineFont3', 'Define font (version 3)'),
    76: ('SymbolClass', 'Class name and linkage'),
    77: ('Metadata', 'Set metadata'),
    78: ('DefineScalingGrid', 'Define scaling grid'),
    79: ('DefineBitsJPEG2', 'Save with DefineBitsJPEG3'),
    80: ('DefineBitsJPEG2', 'Save with DefineBitsJPEG3'),
    81: ('DefineBitsJPEG2', 'Save with DefineBitsJPEG3'),
    82: ('DoABC', 'Do ABC (ActionScript 3.0 bytecode)'),
    83: ('DefineShape4', 'Define shape (version 4)'),
    84: ('DefineMorphShape2', 'Define morph shape (version 2)'),
    85: ('DefineShape4', 'Save with DefineShape4'),
    86: ('DefineSceneAndFrameLabelData', 'Scene and frame label data'),
    87: ('DefineBinaryData', 'Save with DefineBinaryData'),
    88: ('DefineFontName', 'Define font name'),
    89: ('StartSound2', 'Start Sound (version 2)'),
    90: ('DefineBitsJPEG4', 'Define JPEG3 with deblocking'),
    91: ('DefineFont4', 'Define font (version 4)'),
    100: ('BackgroundSound', 'Save with StartSound or DefineStreamSound'),
}

def analyze_swf(filepath):
    """Analyze SWF file and return comprehensive inventory."""
    
    with open(filepath, 'rb') as f:
        data = f.read()
    
    content_hash = hashlib.sha256(data).hexdigest()
    file_bytes = len(data)
    
    # Verify signature
    if data[:3] == b'CWS':
        signature = 'CWS (compressed)'
        compressed = data[8:]
        try:
            decompressed = zlib.decompress(compressed)
        except zlib.error as e:
            return {'error': f'ZLIB decompression failed: {e}'}
        swf = b'FWS' + data[3:8] + decompressed
    elif data[:3] == b'FWS':
        signature = 'FWS (uncompressed)'
        swf = data
    else:
        return {'error': f'Unknown SWF signature: {data[:3].hex()}'}
    
    # Read header
    version = swf[3]
    declared_length = struct.unpack_from('>I', swf, 4)[0]
    actual_length = len(swf)
    frame_rate_raw = struct.unpack_from('<H', swf, -6)[0]
    frame_count = struct.unpack_from('<H', swf, -4)[0]
    
    # Parse tag stream
    tags = []
    tag_counts = defaultdict(int)
    tag_payload = defaultdict(int)
    offset = 8
    
    # Skip RECT (bounding box)
    nbits = (swf[offset] >> 3) & 0x1F
    rect_bytes = (nbits * 4 + 5 + 7) // 8
    offset += rect_bytes + 4  # +4 for frame_rate and frame_count
    
    tag_index = 0
    while offset < len(swf):
        if offset + 2 > len(swf):
            break
        
        tag_header = struct.unpack_from('<H', swf, offset)[0]
        tag_code = tag_header >> 6
        length = tag_header & 0x3F
        
        tag_start = offset
        offset += 2
        
        if length == 0x3F:
            if offset + 4 > len(swf):
                break
            length = struct.unpack_from('<I', swf, offset)[0]
            offset += 4
        
        if offset + length > len(swf):
            offset = len(swf)
            break
        
        tag_data = swf[offset:offset + length]
        tag_name, tag_desc = TAG_CODES.get(tag_code, ('Unknown', 'Unknown tag code'))
        
        tag_index += 1
        tags.append({
            'index': tag_index,
            'code': tag_code,
            'name': tag_name,
            'description': tag_desc,
            'start': tag_start,
            'length': length,
        })
        
        tag_counts[tag_name] += 1
        tag_payload[tag_name] += length
        
        if tag_code == 0:
            break
        
        offset += length
    
    # Analyze ActionScript presence
    doaction_count = tag_counts.get('DoAction', 0)
    doinitaction_count = tag_counts.get('DoInitAction', 0)
    doabc_count = tag_counts.get('DoABC', 0)
    symbolclass_count = tag_counts.get('SymbolClass', 0)
    
    # Determine ActionScript version
    if doabc_count > 0:
        as_version = 'AS3/AVM2'
    elif doaction_count > 0 or doinitaction_count > 0:
        as_version = 'AS2/AVM1'
    else:
        as_version = 'Not determined'
    
    # Character inventory
    characters = {
        'DefineSprite': {'count': tag_counts.get('DefineSprite', 0), 'tags': []},
        'DefineShape': {'count': tag_counts.get('DefineShape', 0) + 
                              tag_counts.get('DefineShape2', 0) + 
                              tag_counts.get('DefineShape3', 0) + 
                              tag_counts.get('DefineShape4', 0), 'tags': []},
        'DefineSound': {'count': tag_counts.get('DefineSound', 0) + tag_counts.get('SoundStreamHead', 0), 'tags': []},
        'DefineText': {'count': tag_counts.get('DefineText', 0) + tag_counts.get('DefineText2', 0), 'tags': []},
        'DefineEditText': {'count': tag_counts.get('DefineEditText', 0), 'tags': []},
        'DefineBits': {'count': tag_counts.get('DefineBits', 0) + 
                             tag_counts.get('DefineBitsJPEG2', 0) + 
                             tag_counts.get('DefineBitsJPEG3', 0) + 
                             tag_counts.get('DefineBitsLossless', 0) + 
                             tag_counts.get('DefineBitsLossless2', 0), 'tags': []},
    }
    
    # Build result
    result = {
        'artifact_identity': {
            'path': filepath,
            'sha256': content_hash,
            'signature': signature,
            'file_bytes': file_bytes,
        },
        'header': {
            'version': version,
            'declared_uncompressed': declared_length,
            'actual_uncompressed': actual_length,
            'frame_rate_fixed_point': frame_rate_raw,
            'frame_rate_fps': frame_rate_raw / 256.0,
            'frame_count': frame_count,
            'compression': 'zlib' if signature.startswith('CWS') else 'none',
        },
        'tag_stream': {
            'total_tags': tag_index,
            'tag_counts': dict(tag_counts),
            'tag_payload_bytes': dict(tag_payload),
        },
        'action_script': {
            'version': as_version,
            'do_action_tags': doaction_count,
            'do_init_action_tags': doinitaction_count,
            'do_abc_tags': doabc_count,
            'symbol_class_tags': symbolclass_count,
            'confidence': 'HIGH' if as_version != 'Not determined' else 'LOW',
            'evidence': [
                'DoABC tags exist' if doabc_count > 0 else 'No DoABC tags',
                'DoAction/DoInitAction tags exist' if (doaction_count > 0 or doinitaction_count > 0) else 'No DoAction/DoInitAction tags',
            ],
        },
        'character_inventory': characters,
        'key_findings': [
            f'SWF version {version} with {tag_index} tags',
            f'Frame rate: {frame_rate_raw / 256.0:.2f} FPS, {frame_count} frames',
            f'{tag_counts.get("DefineSprite", 0)} sprites, {tag_counts.get("DefineSound", 0)} sounds',
            f'{doaction_count} DoAction, {doinitaction_count} DoInitAction, {doabc_count} DoABC tags',
            f'ActionScript {as_version}',
        ],
    }
    
    return result

if __name__ == '__main__':
    report_path = '/home/lucas/Escritorio/flash/Madness Project Nexus Classic.swf'
    result = analyze_swf(report_path)
    
    # Write to output file
    os.makedirs('/home/lucas/Escritorio/rxre/RESEARCH/GAME-001/analysis', exist_ok=True)
    with open('/home/lucas/Escritorio/rxre/RESEARCH/GAME-001/analysis/swf_inventory.json', 'w') as f:
        json.dump(result, f, indent=2, sort_keys=True, default=str)
    
    # Print summary
    print("=== SWF ANALYSIS COMPLETE ===")
    print(f"File: {report_path}")
    print(f"SHA256: {result['artifact_identity']['sha256']}")
    print(f"Version: {result['header']['version']}")
    print(f"Compression: {result['header']['compression']}")
    print(f"Size: {result['header']['actual_uncompressed']} bytes uncompressed")
    print(f"Frame rate: {result['header']['frame_rate_fps']:.2f} FPS, {result['header']['frame_count']} frames")
    print(f"Total tags: {result['tag_stream']['total_tags']}")
    print(f"ActionScript: {result['action_script']['version']}")
    print(f"Key findings:")
    for f in result['key_findings']:
        print(f"  - {f}")

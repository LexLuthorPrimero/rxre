#!/usr/bin/env python3
"""
Extract and analyze ActionScript bytecode from SWF DoAction/DoInitAction tags.
"""
import struct
import zlib
import json
import hashlib
from collections import defaultdict

# ActionScript 1/2 action opcodes (AVM1) - from earlier
SWF_ACTION_NAMES = {
    0x00: 'endAction',
    0x01: 'addAction',
    0x02: 'defineLocal',
    0x04: 'target',
    0x05: 'removeVariable',
    0x06: 'setVariable',
    0x07: 'duplicateSprite',
    0x08: 'moveSprite',
    0x09: 'setVariable',
    0x0A: 'setProperty',
    0x0B: 'getProperty',
    0x0C: 'removeSprite',
    0x0D: 'trace',
    0x0E: 'enterFrame',
    0x0F: 'loadMovie',
    0x10: 'unloadMovie',
    0x11: 'startDrag',
    0x12: 'stopDrag',
    0x13: 'stop',
    0x14: 'play',
    0x15: 'gotoFrame',
    0x16: 'getNextHighestDepth',
    0x17: 'setTarget',
    0x18: 'duplicateMovieClip',
    0x19: 'attachMovie',
    0x1A: 'gotoFrameAndPlay',
    0x1B: 'nextFrame',
    0x1C: 'previousFrame',
    0x1D: 'nextFrame',
    0x1E: 'prevFrame',
    0x1F: 'loadVars',
    0x20: 'callTarget',
    0x21: 'call',
    0x22: 'add',
    0x23: 'subtract',
    0x24: 'multiply',
    0x25: 'divide',
    0x26: 'equals',
    0x27: 'lessThan',
    0x28: 'branchIfLessThan',
    0x29: 'branchIfLessThanOrEquals',
    0x2A: 'branchIfEquals',
    0x2B: 'branchIfNotEquals',
    0x2C: 'branchIfLessThanOrEquals',
    0x2D: 'branchIfTrue',
    0x2E: 'branchIfFalse',
    0x2F: 'decrement',
    0x30: 'increment',
    0x31: 'and',
    0x32: 'or',
    0x33: 'not',
    0x34: 'lengthOf',
    0x35: 'bitAnd',
    0x36: 'bitOr',
    0x37: 'bitXor',
    0x38: 'shiftLeft',
    0x39: 'shiftRight',
    0x3A: 'shiftUnsignedRight',
    0x3B: 'bitNot',
    0x3C: 'hypot',
    0x3D: 'log2',
    0x3E: 'log',
    0x3F: 'random',
    0x40: 'modulo',
    0x41: 'negate',
    0x42: 'abs',
    0x43: 'pow',
    0x44: 'sqrt',
    0x45: 'toString',
    0x46: 'push',
    0x47: 'moveNext',
    0x48: 'movePrevious',
    0x49: 'setNext',
    0x4A: 'setNextValue',
    0x4B: 'newObject',
    0x4C: 'defineLocal',
    0x4D: 'defineLocal2',
    0x4E: 'setTarget',
    0x4F: 'defineLocal2',
    0x50: 'push',
    0x51: 'defineLocal2',
    0x52: 'setTarget',
    0x53: 'getVariable',
    0x54: 'setProperty',
    0x55: 'setVariable',
    0x56: 'setTarget',
    0x57: 'newObject',
    0x58: 'defineLocal',
    0x59: 'defineLocal2',
    0x5A: 'setTarget',
    0x5B: 'defineLocal2',
    0x5C: 'setTarget',
    0x5D: 'defineLocal2',
    0x5E: 'defineLocal2',
    0x5F: 'newObject',
    0x60: 'getVariable',
    0x61: 'setVariable',
    0x62: 'newObject',
    0x63: 'setTarget',
    0x64: 'newObject',
    0x65: 'getVariable',
    0x66: 'setVariable',
    0x67: 'getTarget',
    0x68: 'delete',
    0x69: 'try',
    0x6A: 'pushTarget',
    0x6B: 'pushWith',
    0x6C: 'popScope',
    0x6D: 'setGlobal',
    0x6E: 'delete2',
    0x6F: 'typeof',
    0x70: 'add',
    0x71: 'sub',
    0x72: 'mul',
    0x73: 'div',
    0x74: 'mod',
    0x75: 'neg',
    0x76: 'not',
    0x77: 'eq',
    0x78: 'lt',
    0x79: 'le',
    0x7A: 'ne',
    0x7B: 'ge',
    0x7C: 'gt',
    0x7D: 'and',
    0x7E: 'or',
    0x7F: 'xor',
    0x80: 'increment',
    0x81: 'decrement',
    0x82: 'typeOf',
    0x83: 'target',
    0x84: 'defineLocal',
    0x85: 'getMember',
    0x86: 'setMember',
    0x87: 'increment',
    0x88: 'decrement',
    0x89: 'bitAnd',
    0x8A: 'bitOr',
    0x8B: 'bitXor',
    0x8C: 'bitNot',
    0x8D: 'shiftLeft',
    0x8E: 'shiftRight',
    0x8F: 'shiftUnsignedRight',
    0x90: 'pushNull',
    0x91: 'pushUndefined',
    0x92: 'hasProp',
    0x93: 'pushScope',
    0x94: 'pushWith',
    0x95: 'popScope',
    0x96: 'branchIfLT',
    0x97: 'branchIfLE',
    0x98: 'branchIfEQ',
    0x99: 'branchIfGE',
    0x9A: 'branchIfGT',
    0x9B: 'branchIfNE',
    0x9C: 'jump',
    0x9D: 'branch',
    0x9E: 'pushString',
    0x9F: 'pushInt',
    0xA0: 'pushFloat',
    0xA1: 'pushTrue',
    0xA2: 'pushNaN',
    0xA3: 'pushNull',
    0xA4: 'pushUndefined',
    0xA5: 'increment',
    0xA6: 'decrement',
    0xA7: 'call',
    0xA8: 'callMethod',
    0xA9: 'construct',
    0xAA: 'constructSuper',
    0xAB: 'constructProp',
    0xAC: 'callProp',
    0xAD: 'hasNext',
    0xAE: 'setVariable',
    0xAF: 'getProperty',
    0xB0: 'setTarget',
    0xB1: 'defineLocal',
    0xB2: 'defineLocal2',
    0xB3: 'setTarget',
    0xB4: 'defineLocal2',
    0xB5: 'setTarget',
    0xB6: 'defineLocal2',
    0xB7: 'getVariable',
    0xB8: 'setVariable',
    0xB9: 'callProp',
    0xBA: 'getProp',
    0xBB: 'setProp',
    0xBC: 'defineLocal2',
    0xBD: 'newObject',
    0xBE: 'getProperty',
    0xBF: 'setVariable',
    0xC0: 'callProp',
    0xC1: 'defineLocal2',
    0xC2: 'setTarget',
    0xC3: 'defineLocal2',
    0xC4: 'setTarget',
    0xC5: 'defineLocal2',
    0xC6: 'defineLocal2',
    0xC7: 'defineLocal2',
    0xC8: 'hasNext',
    0xC9: 'initProp',
    0xCA: 'setProp',
    0xCB: 'defineLocal2',
    0xCC: 'setTarget',
    0xCD: 'defineLocal2',
    0xCE: 'setTarget',
    0xCF: 'deleteProp',
    0xD0: 'setGlobal',
    0xD1: 'pushString',
    0xD2: 'pushInt',
    0xD3: 'pushFloat',
    0xD4: 'pushTrue',
    0xD5: 'pushNaN',
    0xD6: 'pushNull',
    0xD7: 'pushUndefined',
    0xD8: 'increment',
    0xD9: 'decrement',
    0xDA: 'typeOf',
    0xDB: 'add',
    0xDC: 'sub',
    0xDD: 'mul',
    0xDE: 'div',
    0xDF: 'mod',
    0xE0: 'neg',
    0xE1: 'not',
    0xE2: 'eq',
    0xE3: 'lt',
    0xE4: 'le',
    0xE5: 'ne',
    0xE6: 'ge',
    0xE7: 'gt',
    0xE8: 'and',
    0xE9: 'or',
    0xEA: 'xor',
    0xEB: 'shiftLeft',
    0xEC: 'shiftRight',
    0xED: 'shiftUnsignedRight',
    0xEE: 'bitAnd',
    0xEF: 'bitOr',
    0xF0: 'bitXor',
    0xF1: 'bitNot',
    0xF2: 'deleteProp',
    0xF3: 'hasProp',
    0xF4: 'deleteProp',
    0xF5: 'pushScope',
    0xF6: 'pushWith',
    0xF7: 'popScope',
    0xF8: 'pushTarget',
    0xF9: 'try',
    0xFA: 'branchIfLT',
    0xFB: 'branchIfLE',
    0xFC: 'branchIfEQ',
    0xFD: 'branchIfGE',
    0xFE: 'branchIfGT',
    0xFF: 'branchIfNE',
}

def parse_swf_actions(data, tag_index):
    """Parse actions from DoAction/DoInitAction tag data."""
    actions = []
    idx = 0
    while idx + 2 <= len(data):
        action_code = struct.unpack_from('>H', data, idx)[0]
        idx += 2
        if action_code == 0:  # endAction
            break
        name = SWF_ACTION_NAMES.get(action_code, f'ACTION_{action_code:02X}')
        actions.append({
            'code': action_code,
            'name': name,
            'offset_in_tag': idx - 2,
        })
    return actions

def extract_bytecode_statistics(tags):
    """Extract statistics about ActionScript bytecode usage."""
    action_tags = []
    do_action_count = 0
    do_init_action_count = 0
    total_actions = 0
    action_frequency = defaultdict(int)
    
    for tag in tags:
        if tag['code'] in (12, 59):  # DoAction or DoInitAction
            actions = parse_swf_actions(tag['data'], tag['index'])
            action_info = {
                'tag_index': tag['index'],
                'tag_code': tag['code'],
                'is_init': tag['code'] == 59,
                'actions': actions,
                'action_count': len(actions)
            }
            action_tags.append(action_info)
            
            if tag['code'] == 12:
                do_action_count += 1
            else:
                do_init_action_count += 1
                
            total_actions += len(actions)
            
            # Count action frequencies
            for action in actions:
                action_frequency[action['name']] += 1
    
    return {
        'action_tags': action_tags,
        'do_action_count': do_action_count,
        'do_init_action_count': do_init_action_count,
        'total_actions': total_actions,
        'action_frequency': dict(action_frequency),
        'most_common_actions': sorted(action_frequency.items(), key=lambda x: x[1], reverse=True)[:10]
    }

def analyze_swf_bytecode(filepath):
    """Analyze SWF file for ActionScript bytecode content."""
    with open(filepath, 'rb') as f:
        data = f.read()
    
    content_hash = hashlib.sha256(data).hexdigest()
    
    # Decompress if needed
    if data[:3] == b'CWS':
        compressed = data[8:]
        try:
            decompressed = zlib.decompress(compressed)
        except zlib.error as e:
            return {'error': f'ZLIB decompression failed: {e}'}
        swf = b'FWS' + data[3:8] + decompressed
    elif data[:3] == b'FWS':
        swf = data
    else:
        return {'error': f'Unknown SWF signature: {data[:3].hex()}'}
    
    # Parse header
    version = swf[3]
    declared_length = struct.unpack_from('<I', swf, 4)[0]
    
    # Parse RECT
    offset = 8
    nbits = (swf[offset] >> 3) & 0x1F
    rect_bytes = (nbits * 4 + 5 + 7) // 8
    rect_end = offset + rect_bytes
    
    # Skip frame rate and count
    tag_stream_start = rect_end + 4
    
    # Parse tag stream
    tags = []
    offset = tag_stream_start
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
        
        tags.append({
            'index': tag_index + 1,
            'code': tag_code,
            'start': tag_start,
            'length': length,
            'data': tag_data,
        })
        
        if tag_code == 0:  # End tag
            break
        
        tag_index += 1
        offset += length
    
    # Analyze ActionScript bytecode
    as_stats = extract_bytecode_statistics(tags)
    
    # Analyze specific patterns
    init_actions = [tag for tag in as_stats['action_tags'] if tag['is_init']]
    frame_actions = [tag for tag in as_stats['action_tags'] if not tag['is_init']]
    
    # Look for common game patterns
    game_patterns = {
        'enter_frame_handlers': sum(1 for tag in init_actions 
                                  for action in tag['actions'] 
                                  if action['name'] == 'enterFrame'),
        'key_listeners': sum(1 for tag in init_actions 
                           for action in tag['actions'] 
                           if action['name'] in ['Key.isDown', 'Key.addListener']),
        'hit_tests': sum(1 for tag in frame_actions 
                       for action in tag['actions'] 
                       if action['name'] == 'hitTest'),
        'duplicate_movie_clips': sum(1 for tag in frame_actions 
                                   for action in tag['actions'] 
                                   if action['name'] == 'duplicateMovieClip'),
        'attach_movie': sum(1 for tag in frame_actions 
                          for action in tag['actions'] 
                          if action['name'] == 'attachMovie'),
        'goto_and_play': sum(1 for tag in frame_actions 
                           for action in tag['actions'] 
                           if action['name'] == 'gotoFrameAndPlay'),
        'load_movie': sum(1 for tag in frame_actions 
                        for action in tag['actions'] 
                        if action['name'] in ['loadMovie', 'unloadMovie']),
        'trace_calls': sum(1 for tag in frame_actions 
                         for action in tag['actions'] 
                         if action['name'] == 'trace'),
        'variable_sets': sum(1 for tag in frame_actions 
                           for action in tag['actions'] 
                           if action['name'] in ['setVariable', 'set']),
        'variable_gets': sum(1 for tag in frame_actions 
                           for action in tag['actions'] 
                           if action['name'] in ['getVariable', 'get']),
    }
    
    result = {
        'artifact_identity': {
            'path': filepath,
            'sha256': content_hash,
            'swf_version': version,
            'declared_length': declared_length,
            'actual_length': len(swf),
        },
        'tag_stream': {
            'total_tags': len(tags),
            'action_tags': as_stats['do_action_count'] + as_stats['do_init_action_count'],
            'do_action_tags': as_stats['do_action_count'],
            'do_init_action_tags': as_stats['do_init_action_count'],
            'end_tag_present': tags[-1]['code'] == 0 if tags else False,
        },
        'actionscript_bytecode': {
            'total_action_records': as_stats['total_actions'],
            'action_tags_detail': as_stats['action_tags'],
            'action_frequency': as_stats['action_frequency'],
            'most_common_actions': as_stats['most_common_actions'],
            'game_patterns': game_patterns,
            'init_actions_summary': {
                'count': len(init_actions),
                'total_actions': sum(tag['action_count'] for tag in init_actions),
                'has_enter_frame': game_patterns['enter_frame_handlers'] > 0,
            },
            'frame_actions_summary': {
                'count': len(frame_actions),
                'total_actions': sum(tag['action_count'] for tag in frame_actions),
            }
        }
    }
    
    return result

if __name__ == '__main__':
    swf_path = '/home/lucas/Escritorio/flash/Madness Project Nexus Classic.swf'
    result = analyze_swf_bytecode(swf_path)
    
    # Write results
    import os
    os.makedirs('/home/lucas/Escritorio/rxre/RESEARCH/GAME-001/analysis', exist_ok=True)
    with open('/home/lucas/Escritorio/rxre/RESEARCH/GAME-001/analysis/as_bytecode_analysis.json', 'w') as f:
        json.dump(result, f, indent=2, sort_keys=True, default=str)
    
    # Print summary
    print("=== ACTIONSCRIPT BYTECODE ANALYSIS ===")
    print(f"File: {swf_path}")
    print(f"SHA256: {result['artifact_identity']['sha256']}")
    print(f"SWF Version: {result['artifact_identity']['swf_version']}")
    print(f"Total tags: {result['tag_stream']['total_tags']}")
    print(f"Action tags: {result['tag_stream']['action_tags']}")
    print(f"  DoAction: {result['tag_stream']['do_action_tags']}")
    print(f"  DoInitAction: {result['tag_stream']['do_init_action_tags']}")
    print(f"Total ActionRecords: {result['actionscript_bytecode']['total_action_records']}")
    
    print(f"\nMost common actions:")
    for action, count in result['actionscript_bytecode']['most_common_actions']:
        print(f"  {action}: {count}")
    
    print(f"\nGame-relevant patterns:")
    patterns = result['actionscript_bytecode']['game_patterns']
    for pattern, count in patterns.items():
        if count > 0:
            print(f"  {pattern}: {count}")
    
    print(f"\nInitialization actions:")
    init_summary = result['actionscript_bytecode']['init_actions_summary']
    print(f"  Init tags: {init_summary['count']}")
    print(f"  Actions in init: {init_summary['total_actions']}")
    print(f"  Has enterFrame handlers: {init_summary['has_enter_frame']}")
    
    print(f"\nFrame actions:")
    frame_summary = result['actionscript_bytecode']['frame_actions_summary']
    print(f"  Frame tags: {frame_summary['count']}")
    print(f"  Actions in frames: {frame_summary['total_actions']}")

#!/usr/bin/env python3
"""
AVM1 (ActionScript 2.0) Bytecode Decoder for SWF files

Decodes ActionScript 2.0 bytecode from DoAction/DoInitAction tags.
Based on Adobe SWF File Format Specification and AVM1 opcode set.
"""
import struct
from typing import List, Dict, Any, Optional, Tuple

# AVM1 Opcode table (partial - add more as needed)
# Reference: Adobe SWF Spec, AVM1 opcodes
AVM1_OPCODES = {
    0x00: 'endAction',
    0x01: 'nextToken',
    0x04: 'target',
    0x05: 'removeVariable',
    0x06: 'setVariable',
    0x07: 'duplicateSprite',
    0x08: 'moveSprite',
    0x09: 'setProperty',
    0x0A: 'getProperty',
    0x0B: 'removeSprite',
    0x0C: 'trace',
    0x0D: 'stop',
    0x0E: 'play',
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

class AVM1Decoder:
    """AVM1 bytecode decoder for SWF action records."""
    
    def __init__(self):
        self.debug = False
    
    def decode(self, tag_data: bytes) -> List[Dict[str, Any]]:
        """Decode AVM1 action records from tag data.
        
        Args:
            tag_data: Raw bytes from a DoAction/DoInitAction tag
            
        Returns:
            List of decoded action records
        """
        actions = []
        offset = 0
        
        while offset + 1 <= len(tag_data):
            # Save starting position
            action_start = offset
            
            # Read opcode (1 byte for AVM1)
            if offset >= len(tag_data):
                break
                
            opcode = tag_data[offset]
            offset += 1
            
            # For opcodes >= 0x80, read 2-byte length (little-endian)
            data_length = 0
            if opcode >= 0x80:
                if offset + 2 > len(tag_data):
                    break
                    
                data_length = struct.unpack_from('<H', tag_data, offset)[0]
                offset += 2
            
            # Extract data
            if data_length > 0:
                if offset + data_length > len(tag_data):
                    # Truncated, stop here
                    break
                    
                data = tag_data[offset:offset + data_length]
                offset += data_length
            else:
                data = b''
            
            # Look up opcode name
            opcode_name = AVM1_OPCODES.get(opcode, f'ACTION_{opcode:02X}')
            
            # Create action record
            action = {
                'offset': action_start,
                'opcode': opcode,
                'name': opcode_name,
                'data': data,
                'length': (offset - action_start),
            }
            
            actions.append(action)
            
            # Check for endAction (0x00)
            if opcode == 0x00:
                break
        
        return actions
    
    def decode_to_text(self, tag_data: bytes) -> str:
        """Decode AVM1 actions to human-readable text.
        
        Args:
            tag_data: Raw bytes from a DoAction/DoInitAction tag
            
        Returns:
            Human-readable text representation
        """
        actions = self.decode(tag_data)
        lines = []
        
        for i, action in enumerate(actions):
            opcode_name = action['name']
            opcode = action['opcode']
            data = action['data']
            
            lines.append(f"{i:4d}: {action['offset']:08x}  {opcode_name:20s} {opcode:04x}")
            
            if opcode_name == 'pushString' and data:
                try:
                    # Try to decode as UTF-8 or Latin-1
                    text = data.decode('utf-8', errors='replace')
                    lines.append(f"        String: {repr(text)}")
                except:
                    lines.append(f"        String: {data.hex()}")
            
            elif opcode_name == 'pushInt' and data:
                if len(data) == 4:
                    value = struct.unpack_from('<I', data, 0)[0]
                    lines.append(f"        Int: {value}")
            
            elif opcode_name == 'pushFloat' and data:
                if len(data) == 4:
                    value = struct.unpack_from('<f', data, 0)[0]
                    lines.append(f"        Float: {value}")
        
        return '\n'.join(lines)

    def find_strings(self, tag_data: bytes) -> List[str]:
        """Extract all strings from AVM1 bytecode.
        
        Args:
            tag_data: Raw bytes from a DoAction/DoInitAction tag
            
        Returns:
            List of strings found
        """
        actions = self.decode(tag_data)
        strings = []
        
        for action in actions:
            if action['name'] == 'pushString' and action['data']:
                try:
                    text = action['data'].decode('utf-8', errors='replace')
                    strings.append(text)
                except:
                    pass
        
        return strings

    def analyze_function_calls(self, tag_data: bytes) -> List[Dict[str, Any]]:
        """Analyze function calls in AVM1 bytecode.
        
        Args:
            tag_data: Raw bytes from a DoAction/DoInitAction tag
            
        Returns:
            List of function call records
        """
        actions = self.decode(tag_data)
        calls = []
        
        for i, action in enumerate(actions):
            if action['name'] == 'call':
                call = {
                    'offset': action['offset'],
                    'index': i,
                    'name': 'call',
                }
                
                # Look ahead to find the string being called
                for j in range(i + 1, len(actions)):
                    if actions[j]['name'] == 'pushString' and actions[j]['data']:
                        try:
                            call['function_name'] = actions[j]['data'].decode('utf-8', errors='replace')
                            break
                        except:
                            pass
                
                calls.append(call)
        
        return calls


def main():
    """Main function for standalone usage."""
    import sys
    import os
    
    if len(sys.argv) < 2:
        print("Usage: python avm1_decoder.py <swf_file>")
        sys.exit(1)
    
    swf_path = sys.argv[1]
    
    # Load SWF and find DoAction tags
    with open(swf_path, 'rb') as f:
        data = f.read()
    
    import zlib
    if data[:3] == b'CWS':
        decompressed = zlib.decompress(data[8:])
        swf = b'FWS' + data[3:8] + decompressed
    elif data[:3] == b'FWS':
        swf = data
    else:
        print(f"Unknown SWF signature: {data[:3].hex()}")
        sys.exit(1)
    
    # Parse header to find tag stream
    offset = 8
    nbits = (swf[offset] >> 3) & 0x1F
    rect_bytes = (nbits * 4 + 5 + 7) // 8
    tag_stream_start = offset + rect_bytes + 4
    
    # Find DoAction/DoInitAction tags
    tag_count = 0
    doaction_count = 0
    doinitaction_count = 0
    
    decoder = AVM1Decoder()
    
    offset = tag_stream_start
    while offset < len(swf):
        if offset + 2 > len(swf):
            break
        
        tag_header = struct.unpack_from('<H', swf, offset)[0]
        tag_code = tag_header >> 6
        length = tag_header & 0x3F
        
        tag_start = offset
        offset += 2
        
        if length == 0x3F:
            length = struct.unpack_from('<I', swf, offset)[0]
            offset += 4
        
        if offset + length > len(swf):
            break
        
        tag_data = swf[offset:offset + length]
        
        if tag_code == 12:  # DoAction
            doaction_count += 1
            if doaction_count <= 2:
                print(f"\n=== DoAction #{doaction_count} (tag {tag_count + 1}) ===")
                print(decoder.decode_to_text(tag_data))
        
        elif tag_code == 59:  # DoInitAction
            doinitaction_count += 1
            if doinitaction_count <= 2:
                print(f"\n=== DoInitAction #{doinitaction_count} (tag {tag_count + 1}) ===")
                print(decoder.decode_to_text(tag_data))
                
                # Extract strings
                strings = decoder.find_strings(tag_data)
                if strings:
                    print(f"\n=== Strings in DoInitAction #{doinitaction_count} ===")
                    for i, s in enumerate(strings):
                        print(f"  {i+1}. {repr(s)}")
        
        if tag_code == 0:
            break
        
        offset += length
        tag_count += 1
    
    print(f"\n=== Summary ===")
    print(f"Total tags parsed: {tag_count}")
    print(f"DoAction tags: {doaction_count}")
    print(f"DoInitAction tags: {doinitaction_count}")

if __name__ == "__main__":
    main()

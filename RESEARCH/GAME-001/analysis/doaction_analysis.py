#!/usr/bin/env python3
"""
DoAction analysis for Madness Project Nexus Classic

Analyzes the DoAction tags to understand the game logic patterns.
"""
import struct, zlib, json
from typing import List, Dict, Tuple

class DoActionAnalyzer:
    def __init__(self):
        self.decoder_table = {
            0x00: 'endAction',
            0x07: 'push',
            0x12: 'nextFrame',
            0x17: 'setTarget',
            0x1C: 'previousFrame',
            0x26: 'push',
            0x3C: 'hypot',
            0x3D: '0x3D',
            0x3E: 'branchIfTrue',
            0x40: 'modulo',
            0x41: '0x41',
            0x47: '0x47',
            0x4B: 'push',
            0x4C: 'defineLocal',
            0x4D: 'push',
            0x4E: '0x4E',
            0x4F: 'defineLocal2',
            0x52: 'setTarget',
            0x55: 'push',
            0x66: 'push',
            0x67: 'push',
            0x87: '0x87',
            0x88: 'data_block',
            0x8E: '0x8E',
            0x9B: '0x9B',
            0x9D: '0x9D',
            0x99: '0x99',
        }
    
    def decode_tag(self, tag_data: bytes) -> List[Dict]:
        """Decode a single DoAction tag into action records."""
        actions = []
        offset = 0
        
        while offset + 1 <= len(tag_data):
            action_start = offset
            opcode = tag_data[offset]
            offset += 1
            
            data_length = 0
            data = b''
            if opcode >= 0x80:
                if offset + 2 > len(tag_data):
                    break
                data_length = struct.unpack_from('<H', tag_data, offset)[0]
                offset += 2
                if offset + data_length > len(tag_data):
                    break
                data = tag_data[offset:offset + data_length]
                offset += data_length
            
            opcode_name = self.decoder_table.get(opcode, f'0x{opcode:02X}')
            
            action = {
                'offset': action_start,
                'opcode': opcode,
                'name': opcode_name,
                'data': data,
                'length': offset - action_start,
                'data_length': data_length
            }
            actions.append(action)
            
            if opcode == 0x00:  # endAction
                break
        
        return actions
    
    def analyze_pattern(self, actions: List[Dict]) -> Dict:
        """Analyze the pattern of actions in a tag."""
        pattern = {
            'action_count': len(actions),
            'opcodes': [a['opcode'] for a in actions],
            'opcode_names': [a['name'] for a in actions],
            'data_blocks': [a for a in actions if a.get('opcode') == 0x88],
            'branch_loops': [],
            'frame_transitions': [],
            'target_changes': [],
            'variables': []
        }
        
        # Look for patterns
        for i, action in enumerate(actions):
            if action['opcode'] == 0x96:  # branchIfLT
                pattern['branch_loops'].append({
                    'offset': action['offset'],
                    'index': i,
                    'name': action['name']
                })
            
            elif action['opcode'] in (0x1C, 0x12):  # previousFrame, nextFrame
                pattern['frame_transitions'].append({
                    'offset': action['offset'],
                    'index': i,
                    'name': action['name']
                })
            
            elif action['opcode'] in (0x17, 0x52):  # setTarget
                pattern['target_changes'].append({
                    'offset': action['offset'],
                    'index': i,
                    'name': action['name']
                })
            
            elif action['opcode'] == 0x4F:  # defineLocal2
                pattern['variables'].append({
                    'offset': action['offset'],
                    'index': i,
                    'name': action['name']
                })
        
        return pattern
    
    def extract_strings_from_tag(self, tag_data: bytes) -> List[str]:
        """Extract all strings from a DoAction tag."""
        strings = []
        idx = 0
        
        while idx < len(tag_data):
            opcode = tag_data[idx]
            idx += 1
            
            if opcode >= 0x80:
                if idx + 2 > len(tag_data):
                    break
                data_len = struct.unpack_from('<H', tag_data, idx)[0]
                idx += 2
                data = tag_data[idx:idx + data_len]
                idx += data_len
                
                # Extract strings from data block
                parts = data.split(b'\x00')
                for part in parts:
                    if len(part) > 2:
                        try:
                            s = part.decode('utf-8', errors='replace')
                            if all(32 <= ord(c) < 127 for c in s):
                                strings.append(s)
                        except:
                            pass
            elif opcode == 0x00:
                break
        
        return strings
    
    def analyze_all_doaction_tags(self, swf_path: str) -> List[Dict]:
        """Analyze all DoAction tags in the SWF file."""
        with open(swf_path, 'rb') as f:
            data = f.read()
        
        import zlib
        if data[:3] == b'CWS':
            decompressed = zlib.decompress(data[8:])
            swf = b'FWS' + data[3:8] + decompressed
        elif data[:3] == b'FWS':
            swf = data
        else:
            raise ValueError(f"Unknown SWF signature: {data[:3].hex()}")
        
        # Parse header
        offset = 8
        nbits = (swf[offset] >> 3) & 0x1F
        rect_bytes = (nbits * 4 + 5 + 7) // 8
        tag_stream_start = offset + rect_bytes + 4
        
        # Find DoAction tags
        tag_index = 0
        do_action_tags = []
        
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
                actions = self.decode_tag(tag_data)
                pattern = self.analyze_pattern(actions)
                strings = self.extract_strings_from_tag(tag_data)
                
                do_action_tags.append({
                    'tag_index': tag_index + 1,
                    'tag_code': tag_code,
                    'tag_length': length,
                    'data_length': len(tag_data),
                    'actions': actions,
                    'pattern': pattern,
                    'strings': strings,
                    'start_offset': tag_start
                })
            
            if tag_code == 0:
                break
            
            offset += length
            tag_index += 1
        
        return do_action_tags

def main():
    """Main function for standalone usage."""
    swf_path = '/home/lucas/Escritorio/flash/Madness Project Nexus Classic.swf'
    
    analyzer = DoActionAnalyzer()
    print("=== Analyzing DoAction Tags in Madness Project Nexus Classic ===\n")
    
    tags = analyzer.analyze_all_doaction_tags(swf_path)
    
    print(f"Total DoAction tags found: {len(tags)}")
    print()
    
    # Analyze each tag
    for i, tag in enumerate(tags):
        print(f"DoAction Tag #{i + 1} (tag #{tag['tag_index']})")
        print(f"  Tag length: {tag['tag_length']} bytes")
        print(f"  Action records: {len(tag['actions'])}")
        print(f"  Strings found: {len(tag['strings'])}")
        print(f"  Start offset: 0x{tag['start_offset']:08x}")
        
        print(f"  Pattern analysis:")
        print(f"    Branch loops: {len(tag['pattern']['branch_loops'])}")
        print(f"    Frame transitions: {len(tag['pattern']['frame_transitions'])}")
        print(f"    Target changes: {len(tag['pattern']['target_changes'])}")
        print(f"    Variables: {len(tag['pattern']['variables'])}")
        
        if tag['strings']:
            print(f"  First 5 strings:")
            for j, s in enumerate(tag['strings'][:5]):
                print(f"    {j + 1}. {repr(s)}")
        
        print()
        
        # Show the action sequence for the first 2 tags
        if i < 2:
            print(f"  Action sequence:")
            for j, action in enumerate(tag['actions'][:10]):
                print(f"    {j + 1:2d}: {action['name']:15s}", end='')
                if action['opcode'] >= 0x80:
                    print(f" (len={action['data_length']})", end='')
                print()
            print()
    
    # Summary statistics
    print("\n=== Summary ===")
    total_actions = sum(len(tag['actions']) for tag in tags)
    total_strings = sum(len(tag['strings']) for tag in tags)
    
    print(f"Total action records across all DoAction tags: {total_actions}")
    print(f"Total unique strings: {total_strings}")
    
    # Most frequent opcodes
    opcode_counts = {}
    for tag in tags:
        for action in tag['actions']:
            opcode = action['opcode']
            opcode_counts[opcode] = opcode_counts.get(opcode, 0) + 1
    
    print("\nMost frequent opcodes:")
    for opcode, count in sorted(opcode_counts.items(), key=lambda x: x[1], reverse=True)[:15]:
        opcode_name = {
            0x00: 'endAction',
            0x12: 'nextFrame',
            0x17: 'setTarget',
            0x1C: 'previousFrame',
            0x40: 'modulo',
            0x3C: 'hypot',
            0x4E: '0x4E',
            0x4F: 'defineLocal2',
            0x52: 'setTarget',
            0x96: 'branchIfLT',
            0x88: 'data_block'
        }.get(opcode, f'0x{opcode:02X}')
        print(f"  {opcode_name:15s} (0x{opcode:02X}): {count}")
if __name__ == '__main__':
    main()
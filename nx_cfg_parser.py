#!/usr/bin/env python3

from __future__ import print_function

import os
import struct
import sys

CFG_TYPE_STR = 0x01
CFG_TYPE_U8  = 0x02
CFG_TYPE_U32 = 0x03

def eprint(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)

def printStringSetting(name, value):
    value_str = value.decode('utf-8').strip('\x00')
    print('%s = str!"%s"' % (name, value_str))
    return True

def printU8Setting(name, value):
    if len(value) != 1:
        return False
    
    print('%s = u8!0x%X' % (name, value[0]))
    return True

def printU32Setting(name, value):
    if len(value) != 4:
        return False
    
    value_u32 = struct.unpack('<I', value)[0]
    print('%s = u32!0x%X' % (name, value_u32))
    return True

def parseSystemSettings(path, size):
    # Create a dictionary to easily handle different config entry types.
    cfg_type_dict = {
        CFG_TYPE_STR: printStringSetting,
        CFG_TYPE_U8:  printU8Setting,
        CFG_TYPE_U32: printU32Setting
    }
    
    # Open settings file.
    try:
        file = open(path, "rb")
    except:
        eprint('Failed to open file!')
        return
    
    # Double check settings file size by reading the first four bytes.
    settings_size = struct.unpack('<I', file.read(4))[0]
    if settings_size != size:
        eprint('File size in header doesn\'t match actual file size!')
        file.close()
        return
    
    offset = 4
    cur_owner = prev_owner = None
    
    # Parse settings file.
    while offset < size:
        entry_offset = offset
        
        # Safety check.
        if (offset + 4) > size:
            eprint('Invalid name size field length for config entry at offset 0x%X (0x%X byte[s] left).' % (entry_offset, size - offset))
            break
        
        # Get name size.
        name_size = struct.unpack('<I', file.read(4))[0]
        offset += 4
        
        # Safety check.
        if (not name_size) or ((offset + name_size + 5) > size):
            eprint('Invalid name/type/value size field length for config entry at offset 0x%X (0x%X byte[s] left, 0x%X-byte long name).' % (entry_offset, size - offset, name_size))
            break
        
        # Get actual name and stringify it. It's actual length should be a byte less than the retrieved name size (which holds a NULL terminator).
        name = file.read(name_size).decode('utf-8').strip('\x00')
        if len(name) != (name_size - 1):
            eprint('Invalid stringified name length for config entry at offset 0x%X.' % (entry_offset))
            break
        
        offset += name_size
        
        # An exclamation mark is always used to divide the config entry owner and the actual config entry name.
        name_start = name.find('!')
        if (name_start < 0):
            eprint('Name for config entry at offset 0x%X doesn\'t hold an owner.' % (entry_offset))
            break
        
        cur_owner = name[:name_start]
        name = name[name_start+1:]
        
        # Print current owner if it's a different one.
        if cur_owner != prev_owner:
            if (entry_offset > 4):
                print()
            print('[%s]' % (cur_owner))
            prev_owner = cur_owner
        
        # Get config entry type and config value size.
        (type, value_size) = struct.unpack('<BI', file.read(5))
        offset += 5
        
        # Safety check.
        if (offset + value_size) > size:
            eprint('Invalid value field length for config entry at offset 0x%X (0x%X byte[s] left, 0x%X-byte long value).' % (entry_offset, size - offset, value_size))
            break
        
        # Get config value.
        value = file.read(value_size)
        offset += value_size
        
        # Use our dictionary to retrieve a proper print function for the current config entry type.
        print_func = cfg_type_dict.get(type, None)
        if not print_func:
            eprint('Unknown config value type for entry at offset 0x%X (0x%02X).' % (entry_offset, type))
            break
        
        # Print config entry.
        if not print_func(name, value):
            eprint('Failed to print config entry at offset 0x%X.' % (entry_offset))
            break
    
    file.close()

def main():
    # Check number of provided arguments.
    if len(sys.argv) < 2:
        eprint('Provide a path to a system settings file!')
        return
    
    # Resolve the provided path and check if it points to an existing file.
    path = os.path.abspath(os.path.expanduser(os.path.expandvars(sys.argv[1])))
    if (os.path.exists(path) == False) or (os.path.isdir(path) == True):
        eprint('The provided path doesn\'t exist or points to a directory!')
        return
    
    # Get settings file size.
    size = os.path.getsize(path)
    if size <= 4:
        eprint('Invalid file size.')
        return
    
    # Parse settings file.
    parseSystemSettings(path, size)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        eprint('\nScript interrupted.')
        try:
            sys.exit(0)
        except SystemExit:
            os._exit(0)

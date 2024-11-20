import struct
from enum import IntEnum
from dataclasses import dataclass
from typing import List, Dict, Any, BinaryIO, Tuple

class PCFVersion:
    DMX_BINARY2_DMX1 = "<!-- dmx encoding binary 2 format dmx 1 -->"
    DMX_BINARY2_PCF1 = "<!-- dmx encoding binary 2 format pcf 1 -->"
    DMX_BINARY3_PCF1 = "<!-- dmx encoding binary 3 format pcf 1 -->"
    DMX_BINARY3_PCF2 = "<!-- dmx encoding binary 3 format pcf 2 -->"
    DMX_BINARY4_PCF2 = "<!-- dmx encoding binary 4 format pcf 2 -->"
    DMX_BINARY5_PCF2 = "<!-- dmx encoding binary 5 format pcf 2 -->"

class AttributeType(IntEnum):
    ELEMENT = 0x01
    INTEGER = 0x02
    FLOAT = 0x03
    BOOLEAN = 0x04
    STRING = 0x05
    BINARY = 0x06
    TIME = 0x07
    COLOR = 0x08
    VECTOR2 = 0x09
    VECTOR3 = 0x0A
    VECTOR4 = 0x0B
    QANGLE = 0x0C
    QUATERNION = 0x0D
    MATRIX = 0x0E
    ELEMENT_ARRAY = 0x0F
    INTEGER_ARRAY = 0x10
    FLOAT_ARRAY = 0x11
    BOOLEAN_ARRAY = 0x12
    STRING_ARRAY = 0x13
    BINARY_ARRAY = 0x14
    TIME_ARRAY = 0x15
    COLOR_ARRAY = 0x16
    VECTOR2_ARRAY = 0x17
    VECTOR3_ARRAY = 0x18
    VECTOR4_ARRAY = 0x19
    QANGLE_ARRAY = 0x1A
    QUATERNION_ARRAY = 0x1B
    MATRIX_ARRAY = 0x1C

@dataclass
class PCFElement:
    type_name_index: int
    element_name: str
    data_signature: bytes
    attributes: Dict[str, Tuple[AttributeType, Any]]  # Changed to store type with value

class PCFFile:
    def __init__(self, version: str = "DMX_BINARY4_PCF2"):
        self.version = version
        self.string_dictionary: List[str] = []
        self.elements: List[PCFElement] = []
        
    def add_string(self, string: str) -> int:
        """Add a string to the dictionary if it doesn't exist and return its index"""
        if string not in self.string_dictionary:
            self.string_dictionary.append(string)
        return self.string_dictionary.index(string)

    def add_element(self, element: PCFElement):
        self.elements.append(element)

class PCFCodec:
    def __init__(self):
        self.pcf = PCFFile()
        
    def write_null_terminated_string(self, file: BinaryIO, string: str) -> None:
        # Ensure we write the exact bytes without any encoding/decoding loss
        if isinstance(string, str):
            encoded = string.encode('ascii', errors='replace')
        else:
            encoded = string
        file.write(encoded + b'\x00')

    def read_null_terminated_string(self, file: BinaryIO) -> bytes:
        # Read raw bytes instead of decoding to string
        chars = bytearray()
        while True:
            char = file.read(1)
            if char == b'\x00' or not char:
                break
            chars.extend(char)
        return bytes(chars)

    def write_attribute_data(self, file: BinaryIO, attr_type: AttributeType, value: Any) -> None:
        if attr_type == AttributeType.ELEMENT:
            file.write(struct.pack('<I', value))
        elif attr_type == AttributeType.INTEGER:
            file.write(struct.pack('<i', value))
        elif attr_type == AttributeType.FLOAT:
            file.write(struct.pack('<f', value))
        elif attr_type == AttributeType.BOOLEAN:
            file.write(struct.pack('B', value))
        elif attr_type == AttributeType.STRING:
            if self.pcf.version == 'DMX_BINARY4_PCF2':
                encoded = value.encode('ascii')
                file.write(struct.pack('<H', len(encoded)))
                file.write(encoded)
            else:
                self.write_null_terminated_string(file, value)
        elif attr_type == AttributeType.BINARY:
            file.write(struct.pack('<I', len(value)))
            file.write(value)
        elif attr_type == AttributeType.COLOR:
            file.write(struct.pack('<4B', *value))
        elif attr_type == AttributeType.VECTOR2:
            file.write(struct.pack('<2f', *value))
        elif attr_type == AttributeType.VECTOR3:
            file.write(struct.pack('<3f', *value))
        elif attr_type == AttributeType.VECTOR4:
            file.write(struct.pack('<4f', *value))
        elif attr_type == AttributeType.MATRIX:
            for row in value:
                file.write(struct.pack('<4f', *row))
        elif attr_type.value >= AttributeType.ELEMENT_ARRAY.value:
            file.write(struct.pack('<I', len(value)))
            base_type = AttributeType(attr_type.value - 14)
            for item in value:
                self.write_attribute_data(file, base_type, item)

    def read_attribute_data(self, file: BinaryIO, attr_type: AttributeType):
        if attr_type == AttributeType.ELEMENT:
            return struct.unpack('<I', file.read(4))[0]
        elif attr_type == AttributeType.INTEGER:
            return struct.unpack('<i', file.read(4))[0]
        elif attr_type == AttributeType.FLOAT:
            return struct.unpack('<f', file.read(4))[0]
        elif attr_type == AttributeType.BOOLEAN:
            return bool(file.read(1)[0])
        elif attr_type == AttributeType.STRING:
            if self.pcf.version == 'DMX_BINARY4_PCF2':
                length = struct.unpack('<H', file.read(2))[0]
                return file.read(length).decode('ascii')
            return self.read_null_terminated_string(file)
        elif attr_type == AttributeType.BINARY:
            length = struct.unpack('<I', file.read(4))[0]
            return file.read(length)
        elif attr_type == AttributeType.COLOR:
            return struct.unpack('<4B', file.read(4))
        elif attr_type == AttributeType.VECTOR2:
            return struct.unpack('<2f', file.read(8))
        elif attr_type == AttributeType.VECTOR3:
            return struct.unpack('<3f', file.read(12))
        elif attr_type == AttributeType.VECTOR4:
            return struct.unpack('<4f', file.read(16))
        elif attr_type == AttributeType.MATRIX:
            return [struct.unpack('<4f', file.read(16)) for _ in range(4)]
        elif attr_type.value >= AttributeType.ELEMENT_ARRAY.value:
            count = struct.unpack('<I', file.read(4))[0]
            base_type = AttributeType(attr_type.value - 14)
            return [self.read_attribute_data(file, base_type) for _ in range(count)]
        else:
            raise ValueError(f"Unsupported attribute type: {attr_type}")

    def encode(self, output_path: str) -> None:
        with open(output_path, 'wb') as file:
            # Write header
            version_string = getattr(PCFVersion, self.pcf.version)
            self.write_null_terminated_string(file, f"{version_string}\n")
            
            # Write string dictionary with exact byte preservation
            if self.pcf.version == 'DMX_BINARY4_PCF2':
                file.write(struct.pack('<I', len(self.pcf.string_dictionary)))
            else:
                file.write(struct.pack('<H', len(self.pcf.string_dictionary)))
            
            # Write each string with exact byte preservation
            for string in self.pcf.string_dictionary:
                if isinstance(string, str):
                    self.write_null_terminated_string(file, string)
                else:
                    file.write(string + b'\x00')
            
            # Write element dictionary
            file.write(struct.pack('<I', len(self.pcf.elements)))
            for element in self.pcf.elements:
                file.write(struct.pack('<H', element.type_name_index))
                if isinstance(element.element_name, str):
                    self.write_null_terminated_string(file, element.element_name)
                else:
                    file.write(element.element_name + b'\x00')
                file.write(element.data_signature)
            
            # Write element data with exact byte preservation
            for element in self.pcf.elements:
                file.write(struct.pack('<I', len(element.attributes)))
                for attr_name, (attr_type, attr_value) in element.attributes.items():
                    name_index = self.pcf.string_dictionary.index(attr_name)
                    file.write(struct.pack('<H', name_index))
                    file.write(struct.pack('B', attr_type))
                    self.write_attribute_data(file, attr_type, attr_value)

    def decode(self, input_path: str) -> None:
        with open(input_path, 'rb') as file:
            # Store original file content for verification
            original_content = file.read()
            file.seek(0)
            
            # Read header as bytes
            header = self.read_null_terminated_string(file)
            for ver_attr in dir(PCFVersion):
                if ver_attr.startswith('DMX_'):
                    version = getattr(PCFVersion, ver_attr)
                    if header.decode('ascii', errors='replace') == f"{version}\n":
                        self.pcf.version = ver_attr
                        break
            else:
                raise ValueError(f"Unsupported PCF version: {header}")
            
            # Read string dictionary preserving exact bytes
            if self.pcf.version == 'DMX_BINARY4_PCF2':
                count = struct.unpack('<I', file.read(4))[0]
            else:
                count = struct.unpack('<H', file.read(2))[0]
            
            # Store strings as bytes
            for _ in range(count):
                string = self.read_null_terminated_string(file)
                self.pcf.string_dictionary.append(string)
            
            # Read element dictionary
            element_count = struct.unpack('<I', file.read(4))[0]
            for _ in range(element_count):
                type_name_index = struct.unpack('<H', file.read(2))[0]
                element_name = self.read_null_terminated_string(file)
                data_signature = file.read(16)
                
                element = PCFElement(
                    type_name_index=type_name_index,
                    element_name=element_name,
                    data_signature=data_signature,
                    attributes={}
                )
                self.pcf.elements.append(element)
            
            # Read element data
            for element in self.pcf.elements:
                attribute_count = struct.unpack('<I', file.read(4))[0]
                for _ in range(attribute_count):
                    type_name_index = struct.unpack('<H', file.read(2))[0]
                    attr_type = AttributeType(file.read(1)[0])
                    
                    attr_name = self.pcf.string_dictionary[type_name_index]
                    attr_value = self.read_attribute_data(file, attr_type)
                    element.attributes[attr_name] = (attr_type, attr_value)
                    
def verify_copy(input_path: str, output_path: str) -> bool:
    """Verify that the input and output files are byte-identical"""
    with open(input_path, 'rb') as f1, open(output_path, 'rb') as f2:
        content1 = f1.read()
        content2 = f2.read()
        if len(content1) != len(content2):
            print(f"Size mismatch: {len(content1)} vs {len(content2)} bytes")
            # Find first difference
            min_len = min(len(content1), len(content2))
            for i in range(min_len):
                if content1[i] != content2[i]:
                    print(f"First difference at offset {i:02X}: {content1[i]:02X} vs {content2[i]:02X}")
                    break
            return False
        return content1 == content2

def decode_pcf_file(input_path: str) -> PCFFile:
    """Decode a PCF file and return a PCFFile object"""
    codec = PCFCodec()
    codec.decode(input_path)
    return codec.pcf

def encode_pcf_file(pcf: PCFFile, output_path: str) -> None:
    """Encode a PCFFile object to a PCF file"""
    codec = PCFCodec()
    codec.pcf = pcf
    codec.encode(output_path)

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 3:
        print("Usage: python pcf_codec.py <command> <input_file> [output_file]")
        print("Commands: decode, encode, copy, verify")
        sys.exit(1)

    command = sys.argv[1]
    input_file = sys.argv[2]
    
    if command == "verify":
        if len(sys.argv) < 4:
            print("Error: Need both input and output files for verification")
            sys.exit(1)
        output_file = sys.argv[3]
        if verify_copy(input_file, output_file):
            print("Files are identical")
        else:
            print("Files differ")
    elif command == "copy":
        if len(sys.argv) < 4:
            print("Error: Output file required for copy command")
            sys.exit(1)
        output_file = sys.argv[3]
        codec = PCFCodec()
        codec.decode(input_file)
        codec.encode(output_file)
        if verify_copy(input_file, output_file):
            print("Successfully copied with byte-perfect accuracy")
        else:
            print("Warning: Copy produced different bytes")

import struct
from enum import IntEnum
from dataclasses import dataclass
from typing import List, Dict, Any, BinaryIO
import os

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
    attributes: Dict[str, Any]

class PCFDecoder:
    def __init__(self, file_path: str):
        self.file_path = file_path
        self.string_dictionary: List[str] = []
        self.elements: List[PCFElement] = []
        self.version = None

    def read_null_terminated_string(self, file: BinaryIO) -> str:
        chars = []
        while True:
            char = file.read(1)
            if char == b'\x00' or not char:
                break
            chars.append(char.decode('ascii'))
        return ''.join(chars)

    def read_header(self, file: BinaryIO) -> None:
        header = self.read_null_terminated_string(file)
        for ver_attr in dir(PCFVersion):
            if ver_attr.startswith('DMX_'):
                version = getattr(PCFVersion, ver_attr)
                if header.rstrip() == version:
                    self.version = ver_attr
                    return
        raise ValueError(f"Unsupported PCF version: {header}")

    def read_string_dictionary(self, file: BinaryIO) -> None:
        if self.version == 'DMX_BINARY4_PCF2':
            count = struct.unpack('<I', file.read(4))[0]
        else:
            count = struct.unpack('<H', file.read(2))[0]
        
        for _ in range(count):
            string = self.read_null_terminated_string(file)
            self.string_dictionary.append(string)

    def read_element_dictionary(self, file: BinaryIO) -> None:
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
            self.elements.append(element)

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
            if self.version == 'DMX_BINARY4_PCF2':
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
        # Handle array types
        elif attr_type.value >= AttributeType.ELEMENT_ARRAY.value:
            count = struct.unpack('<I', file.read(4))[0]
            base_type = AttributeType(attr_type.value - 14)  # Convert array type to base type
            return [self.read_attribute_data(file, base_type) for _ in range(count)]
        else:
            raise ValueError(f"Unsupported attribute type: {attr_type}")

    def read_element_data(self, file: BinaryIO) -> None:
        for element in self.elements:
            attribute_count = struct.unpack('<I', file.read(4))[0]
            
            for _ in range(attribute_count):
                type_name_index = struct.unpack('<H', file.read(2))[0]
                attr_type = AttributeType(file.read(1)[0])
                
                attr_name = self.string_dictionary[type_name_index]
                attr_value = self.read_attribute_data(file, attr_type)
                element.attributes[attr_name] = attr_value

    def decode(self) -> List[PCFElement]:
        with open(self.file_path, 'rb') as file:
            self.read_header(file)
            self.read_string_dictionary(file)
            self.read_element_dictionary(file)
            self.read_element_data(file)
        return self.elements

def decode_pcf_file(file_path: str) -> List[PCFElement]:
    """
    Decode a PCF file and return its elements and their attributes.
    
    Args:
        file_path: Path to the PCF file
        
    Returns:
        List of PCFElement objects containing the decoded data
    """
    decoder = PCFDecoder(file_path)
    return decoder.decode()

if __name__ == "__main__":
    import sys
    if len(sys.argv) != 2:
        print("Usage: python pcf_decoder.py <pcf_file>")
        sys.exit(1)
        
    file_path = sys.argv[1]
    try:
        elements = decode_pcf_file(file_path)
        print(f"Successfully decoded {len(elements)} elements from {file_path}")
        f = open("pcf.txt", "w")
        for element in elements:
            f.write(f"\nElement: {element.element_name}")
            f.write(f"\nType Name Index: {element.type_name_index}")
            f.write("\nAttributes:")
            for attr_name, attr_value in element.attributes.items():
                f.write(f"\n  {attr_name}: {attr_value}")
        f.close()
    except Exception as e:
        print(f"Error decoding PCF file: {e}")
        sys.exit(1)
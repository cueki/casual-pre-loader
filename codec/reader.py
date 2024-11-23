import struct
from typing import BinaryIO, Any

from core.constants import AttributeType, PCFVersion
from core.errors import PCFDecodingError
from models.element import PCFElement
from models.pcf_file import PCFFile

class PCFReader:
    """Handles reading PCF binary data"""

    def __init__(self, file: BinaryIO):
        self.file = file

    def read_null_terminated_string(self) -> bytes:
        """Read null-terminated string as bytes"""
        chars = bytearray()
        while True:
            char = self.file.read(1)
            if char == b'\x00' or not char:
                break
            chars.extend(char)
        return bytes(chars)

    def read_attribute_data(self, attr_type: AttributeType, version: str) -> Any:
        """Read attribute data based on type"""
        if attr_type == AttributeType.ELEMENT:
            return struct.unpack('<I', self.file.read(4))[0]
        elif attr_type == AttributeType.INTEGER:
            return struct.unpack('<i', self.file.read(4))[0]
        elif attr_type == AttributeType.FLOAT:
            return struct.unpack('<f', self.file.read(4))[0]
        elif attr_type == AttributeType.BOOLEAN:
            return bool(self.file.read(1)[0])
        elif attr_type == AttributeType.STRING:
            if version == PCFVersion.DMX_BINARY4_PCF2:
                length = struct.unpack('<H', self.file.read(2))[0]
                return self.file.read(length).decode('ascii')
            return self.read_null_terminated_string()
        elif attr_type == AttributeType.BINARY:
            length = struct.unpack('<I', self.file.read(4))[0]
            return self.file.read(length)
        elif attr_type == AttributeType.COLOR:
            return struct.unpack('<4B', self.file.read(4))
        elif attr_type == AttributeType.VECTOR2:
            return struct.unpack('<2f', self.file.read(8))
        elif attr_type == AttributeType.VECTOR3:
            return struct.unpack('<3f', self.file.read(12))
        elif attr_type == AttributeType.VECTOR4:
            return struct.unpack('<4f', self.file.read(16))
        elif attr_type == AttributeType.MATRIX:
            return [struct.unpack('<4f', self.file.read(16)) for _ in range(4)]
        elif attr_type.value >= AttributeType.ELEMENT_ARRAY.value:
            count = struct.unpack('<I', self.file.read(4))[0]
            base_type = AttributeType(attr_type.value - 14)
            return [self.read_attribute_data(base_type, version) for _ in range(count)]
        else:
            raise PCFDecodingError(f"Unsupported attribute type: {attr_type}")

    def decode(self) -> PCFFile:
        """Decode PCF file"""
        try:
            # Read header
            header = self.read_null_terminated_string().decode('ascii')
            if not header.endswith('\n'):
                raise PCFDecodingError("Invalid header format")
            header = header[:-1]  # Remove newline

            # Validate and set version
            version = None
            for ver in PCFVersion:
                if header == ver:
                    version = ver
                    break
            if not version:
                raise PCFDecodingError(f"Unsupported PCF version: {header}")

            pcf = PCFFile(version=version)

            # Read string dictionary
            if version == PCFVersion.DMX_BINARY4_PCF2:
                count = struct.unpack('<I', self.file.read(4))[0]
            else:
                count = struct.unpack('<H', self.file.read(2))[0]

            for _ in range(count):
                string = self.read_null_terminated_string()
                pcf.string_dictionary.append(string)

            # Read elements
            element_count = struct.unpack('<I', self.file.read(4))[0]
            for _ in range(element_count):
                type_name_index = struct.unpack('<H', self.file.read(2))[0]
                element_name = self.read_null_terminated_string()
                data_signature = self.file.read(16)

                element = PCFElement(
                    type_name_index=type_name_index,
                    element_name=element_name,
                    data_signature=data_signature
                )

                # Read attributes
                attribute_count = struct.unpack('<I', self.file.read(4))[0]
                for _ in range(attribute_count):
                    name_index = struct.unpack('<H', self.file.read(2))[0]
                    attr_type = AttributeType(self.file.read(1)[0])

                    attr_name = pcf.string_dictionary[name_index]
                    attr_value = self.read_attribute_data(attr_type, version)
                    element.attributes[attr_name] = (attr_type, attr_value)

                pcf.elements.append(element)

            return pcf

        except (struct.error, IOError) as e:
            raise PCFDecodingError(f"Error decoding PCF: {e}")
import struct
from typing import BinaryIO, Any
from core.constants import PCFVersion, AttributeType
from models.element import PCFElement
from models.pcf_file import PCFFile
import io

def write_null_terminated_string(file: BinaryIO, string: str) -> None:
    # Ensure we write the exact bytes without any encoding/decoding loss
    if isinstance(string, str):
        encoded = string.encode('ascii', errors='replace')
    else:
        encoded = string
    file.write(encoded + b'\x00')


def read_null_terminated_string(file: BinaryIO) -> bytes:
    # Read raw bytes instead of decoding to string
    chars = bytearray()
    while True:
        char = file.read(1)
        if char == b'\x00' or not char:
            break
        chars.extend(char)
    return bytes(chars)


class PCFCodec:
    def __init__(self):
        self.pcf = PCFFile()

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
                write_null_terminated_string(file, value)
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
            return read_null_terminated_string(file)
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
            write_null_terminated_string(file, f"{version_string}\n")

            # Write string dictionary with exact byte preservation
            if self.pcf.version == 'DMX_BINARY4_PCF2':
                file.write(struct.pack('<I', len(self.pcf.string_dictionary)))
            else:
                file.write(struct.pack('<H', len(self.pcf.string_dictionary)))

            # Write each string with exact byte preservation
            for string in self.pcf.string_dictionary:
                if isinstance(string, str):
                    write_null_terminated_string(file, string)
                else:
                    file.write(string + b'\x00')

            # Write element dictionary
            file.write(struct.pack('<I', len(self.pcf.elements)))
            for element in self.pcf.elements:
                file.write(struct.pack('<H', element.type_name_index))
                if isinstance(element.element_name, str):
                    write_null_terminated_string(file, element.element_name)
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

    def decode(self, input_path: str):
        with open(input_path, 'rb') as file:
            # Store original file content for verification
            file.seek(0)

            # Read header as bytes
            header = read_null_terminated_string(file)
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
                string = read_null_terminated_string(file)
                self.pcf.string_dictionary.append(string)

            # Read element dictionary
            element_count = struct.unpack('<I', file.read(4))[0]
            for _ in range(element_count):
                type_name_index = struct.unpack('<H', file.read(2))[0]
                element_name = read_null_terminated_string(file)
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


    def get_size(self) -> int:
        output = io.BytesIO()
        # Write header
        version_string = getattr(PCFVersion, self.pcf.version)
        write_null_terminated_string(output, f"{version_string}\n")

        # Write string dictionary
        if self.pcf.version == 'DMX_BINARY4_PCF2':
            output.write(struct.pack('<I', len(self.pcf.string_dictionary)))
        else:
            output.write(struct.pack('<H', len(self.pcf.string_dictionary)))

        for string in self.pcf.string_dictionary:
            if isinstance(string, str):
                write_null_terminated_string(output, string)
            else:
                output.write(string + b'\x00')

        # Write element dictionary
        output.write(struct.pack('<I', len(self.pcf.elements)))
        for element in self.pcf.elements:
            output.write(struct.pack('<H', element.type_name_index))
            if isinstance(element.element_name, str):
                write_null_terminated_string(output, element.element_name)
            else:
                output.write(element.element_name + b'\x00')
            output.write(element.data_signature)

        # Write element data
        for element in self.pcf.elements:
            output.write(struct.pack('<I', len(element.attributes)))
            for attr_name, (attr_type, attr_value) in element.attributes.items():
                name_index = self.pcf.string_dictionary.index(attr_name)
                output.write(struct.pack('<H', name_index))
                output.write(struct.pack('B', attr_type))
                self.write_attribute_data(output, attr_type, attr_value)

        return output.tell()
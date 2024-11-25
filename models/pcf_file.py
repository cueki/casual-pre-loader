import io
import struct
from dataclasses import dataclass
from pathlib import Path
from typing import BinaryIO, Any, List

from core.constants import PCFVersion, AttributeType, ATTRIBUTE_VALUES
from models.element import PCFElement


@dataclass
class PCFFile:
    def __init__(self, input_file: Path, version: str = "DMX_BINARY4_PCF2"):
        self.version = version
        self.string_dictionary: List[str] = []
        self.elements: List[PCFElement] = []
        self.input_file: Path = input_file

    def add_string(self, string: str) -> int:
        if string not in self.string_dictionary:
            self.string_dictionary.append(string)
        return self.string_dictionary.index(string)

    def add_element(self, element: PCFElement):
        self.elements.append(element)

    def read_null_terminated_string(self,
                                    file: BinaryIO) -> bytes:  # Ignore 'method may be static' warning for now, will be fixed later
        # Read raw bytes instead of decoding to string
        chars = bytearray()
        while True:
            char = file.read(1)
            if char == b'\x00' or not char:
                break
            chars.extend(char)
        return bytes(chars)

    def write_null_terminated_string(self, file: BinaryIO,
                                     string: str) -> None:  # Ignore 'method may be static' warning for now, will be fixed later
        # Ensure we write the exact bytes without any encoding/decoding loss
        if isinstance(string, str):
            encoded = string.encode('ascii', errors='replace')
        else:
            encoded = string
        file.write(encoded + b'\x00')

    def write_attribute_data(self, file: BinaryIO, attr_type: AttributeType, value: Any) -> None:
        if not ATTRIBUTE_VALUES.get(attr_type):
            raise ValueError(f"Unsupported attribute type: {attr_type}")

        if attr_type == AttributeType.STRING:
            if self.version == 'DMX_BINARY4_PCF2':
                encoded = value.encode('ascii')
                file.write(struct.pack(ATTRIBUTE_VALUES.get(attr_type), len(encoded)))
                file.write(encoded)
            else:
                self.write_null_terminated_string(file, value)
            return

        if attr_type == AttributeType.MATRIX:
            for row in value:
                file.write(struct.pack(ATTRIBUTE_VALUES.get(attr_type), *row))
            return

        if attr_type.value >= AttributeType.ELEMENT_ARRAY.value:
            file.write(struct.pack(ATTRIBUTE_VALUES.get(attr_type), len(value)))
            base_type = AttributeType(attr_type.value - 14)
            for item in value:
                self.write_attribute_data(file, base_type, item)
            return

        if attr_type in [AttributeType.COLOR, AttributeType.VECTOR2, AttributeType.VECTOR3, AttributeType.VECTOR4]:
            file.write(struct.pack(ATTRIBUTE_VALUES.get(attr_type), *value))
            return

        file.write(struct.pack(ATTRIBUTE_VALUES.get(attr_type), value))

    def read_attribute_data(self, file: BinaryIO, attr_type: AttributeType):
        if attr_type in [AttributeType.ELEMENT, AttributeType.INTEGER, AttributeType.FLOAT]:
            return struct.unpack(ATTRIBUTE_VALUES.get(attr_type), file.read(4))[0]

        if attr_type == AttributeType.BOOLEAN:
            return bool(file.read(1)[0])

        if attr_type == AttributeType.STRING:
            if self.version == 'DMX_BINARY4_PCF2':
                length = struct.unpack(ATTRIBUTE_VALUES.get(attr_type), file.read(2))[0]
                return file.read(length).decode('ascii')
            return self.read_null_terminated_string(file)

        if attr_type == AttributeType.BINARY:
            length = struct.unpack(ATTRIBUTE_VALUES.get(attr_type), file.read(4))[0]
            return file.read(length)

        if attr_type == AttributeType.COLOR:
            return struct.unpack('<4B', file.read(4))

        if attr_type == AttributeType.VECTOR2:
            return struct.unpack('<2f', file.read(8))

        if attr_type == AttributeType.VECTOR3:
            return struct.unpack('<3f', file.read(12))

        if attr_type == AttributeType.VECTOR4:
            return struct.unpack('<4f', file.read(16))

        if attr_type == AttributeType.MATRIX:
            return [struct.unpack('<4f', file.read(16)) for _ in range(4)]

        if attr_type.value >= AttributeType.ELEMENT_ARRAY.value:
            count = struct.unpack('<I', file.read(4))[0]
            base_type = AttributeType(attr_type.value - 14)
            return [self.read_attribute_data(file, base_type) for _ in range(count)]

        raise ValueError(f"Unsupported attribute type: {attr_type}")

    def encode(self, output_path: str) -> None:
        with open(output_path, 'wb') as file:
            # Write header
            version_string = getattr(PCFVersion, self.version)
            self.write_null_terminated_string(file, f"{version_string}\n")

            # Write string dictionary with exact byte preservation
            if self.version == 'DMX_BINARY4_PCF2':
                file.write(struct.pack('<I', len(self.string_dictionary)))
            else:
                file.write(struct.pack('<H', len(self.string_dictionary)))

            # Write each string with exact byte preservation
            for string in self.string_dictionary:
                if isinstance(string, str):
                    self.write_null_terminated_string(file, string)
                else:
                    file.write(string + b'\x00')

            # Write element dictionary
            file.write(struct.pack('<I', len(self.elements)))
            for element in self.elements:
                file.write(struct.pack('<H', element.type_name_index))
                if isinstance(element.element_name, str):
                    self.write_null_terminated_string(file, element.element_name)
                else:
                    file.write(element.element_name + b'\x00')
                file.write(element.data_signature)

            # Write element data with exact byte preservation
            for element in self.elements:
                file.write(struct.pack('<I', len(element.attributes)))
                for attr_name, (attr_type, attr_value) in element.attributes.items():
                    name_index = self.string_dictionary.index(attr_name)
                    file.write(struct.pack('<H', name_index))
                    file.write(struct.pack('B', attr_type))
                    self.write_attribute_data(file, attr_type, attr_value)

    def decode(self):
        with open(self.input_file, 'rb') as file:
            # Store original file content for verification
            file.seek(0)

            # Read header as bytes
            header = self.read_null_terminated_string(file)
            for ver_attr in dir(PCFVersion):
                if ver_attr.startswith('DMX_'):
                    version = getattr(PCFVersion, ver_attr)
                    if header.decode('ascii', errors='replace') == f"{version}\n":
                        self.version = ver_attr
                        break
            else:
                raise ValueError(f"Unsupported PCF version: {header}")

            # Read string dictionary preserving exact bytes
            if self.version == 'DMX_BINARY4_PCF2':
                count = struct.unpack('<I', file.read(4))[0]
            else:
                count = struct.unpack('<H', file.read(2))[0]

            # Store strings as bytes
            for _ in range(count):
                string = self.read_null_terminated_string(file)
                self.string_dictionary.append(string)

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
                self.elements.append(element)

            # Read element data
            for element in self.elements:
                attribute_count = struct.unpack('<I', file.read(4))[0]
                for _ in range(attribute_count):
                    type_name_index = struct.unpack('<H', file.read(2))[0]
                    attr_type = AttributeType(file.read(1)[0])

                    attr_name = self.string_dictionary[type_name_index]
                    attr_value = self.read_attribute_data(file, attr_type)
                    element.attributes[attr_name] = (attr_type, attr_value)

    def get_size(self) -> int:
        output = io.BytesIO()
        # Write header
        version_string = getattr(PCFVersion, self.version)
        self.write_null_terminated_string(f"{version_string}\n")

        # Write string dictionary
        if self.version == 'DMX_BINARY4_PCF2':
            output.write(struct.pack('<I', len(self.string_dictionary)))
        else:
            output.write(struct.pack('<H', len(self.string_dictionary)))

        for string in self.string_dictionary:
            if isinstance(string, str):
                self.write_null_terminated_string(output, string)
            else:
                output.write(string + b'\x00')

        # Write element dictionary
        output.write(struct.pack('<I', len(self.elements)))
        for element in self.elements:
            output.write(struct.pack('<H', element.type_name_index))
            if isinstance(element.element_name, str):
                self.write_null_terminated_string(output, element.element_name)
            else:
                output.write(element.element_name + b'\x00')
            output.write(element.data_signature)

        # Write element data
        for element in self.elements:
            output.write(struct.pack('<I', len(element.attributes)))
            for attr_name, (attr_type, attr_value) in element.attributes.items():
                name_index = self.string_dictionary.index(attr_name)
                output.write(struct.pack('<H', name_index))
                output.write(struct.pack('B', attr_type))
                self.write_attribute_data(output, attr_type, attr_value)

        return output.tell()

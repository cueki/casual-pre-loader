import struct
from pathlib import Path
from dataclasses import dataclass
from typing import BinaryIO, Any, List, Dict, Tuple, Union
from core.constants import PCFVersion, AttributeType, ATTRIBUTE_VALUES


@dataclass
class PCFElement:
    type_name_index: int
    element_name: bytes
    data_signature: bytes
    attributes: Dict[bytes, Tuple[AttributeType, Any]]


@dataclass
class PCFFile:
    def __init__(self, input_file: Union[Path, str], version: str = "DMX_BINARY2_PCF1"):
        self.version = version
        self.string_dictionary: List[bytes] = []  # changed to explicitly store bytes
        self.elements: List[PCFElement] = []
        self.input_file = Path(input_file)

    @staticmethod
    def read_null_terminated_string(file: BinaryIO):
        chars = bytearray()
        while True:
            char = file.read(1)
            if not char or char == b'\x00':
                break
            chars.extend(char)
        return bytes(chars)

    @staticmethod
    def write_null_terminated_string(file: BinaryIO, string: Union[str, bytes]):
        if isinstance(string, str):
            encoded = string.encode('ascii', errors='replace')
        else:
            encoded = string
        file.write(encoded + b'\x00')

    def write_attribute_data(self, file: BinaryIO, attr_type: AttributeType, value: Any) -> None:
        if not ATTRIBUTE_VALUES.get(attr_type):
            raise ValueError(f"Unsupported attribute type: {attr_type}")

        if attr_type == AttributeType.STRING:
            if isinstance(value, str):
                value = value.encode('ascii', errors='replace')

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

    def encode(self, output_path: Union[Path, str]) -> 'PCFFile':
        with open(output_path, 'wb') as file:
            # write header
            version_string = getattr(PCFVersion, self.version)
            self.write_null_terminated_string(file, f"{version_string}\n")

            # write string dictionary
            file.write(struct.pack('<H', len(self.string_dictionary)))

            # write strings as raw bytes
            for string in self.string_dictionary:
                file.write(string + b'\x00')

            # write element dictionary
            file.write(struct.pack('<I', len(self.elements)))
            for element in self.elements:
                file.write(struct.pack('<H', element.type_name_index))
                file.write(element.element_name + b'\x00')
                file.write(element.data_signature)

            # write element data
            for element in self.elements:
                file.write(struct.pack('<I', len(element.attributes)))
                for attr_name, (attr_type, attr_value) in element.attributes.items():
                    name_index = self.string_dictionary.index(attr_name)
                    file.write(struct.pack('<H', name_index))
                    file.write(struct.pack('B', attr_type))
                    self.write_attribute_data(file, attr_type, attr_value)

        return self

    def decode(self):
        with open(self.input_file, 'rb') as file:
            # read header
            header = self.read_null_terminated_string(file)
            header_str = header.decode('ascii', errors='replace')

            for ver_attr in dir(PCFVersion):
                if ver_attr.startswith('DMX_'):
                    version = getattr(PCFVersion, ver_attr)
                    if header_str == f"{version}\n":
                        self.version = ver_attr
                        break
            else:
                raise ValueError(f"Unsupported PCF version: {header}")

            # read string dictionary
            count = struct.unpack('<H', file.read(2))[0]

            # store strings as bytes
            for _ in range(count):
                string = self.read_null_terminated_string(file)
                self.string_dictionary.append(string)

            # read element dictionary
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

            # read element data
            for element in self.elements:
                attribute_count = struct.unpack('<I', file.read(4))[0]
                for _ in range(attribute_count):
                    type_name_index = struct.unpack('<H', file.read(2))[0]
                    attr_type = AttributeType(file.read(1)[0])

                    attr_name = self.string_dictionary[type_name_index]
                    attr_value = self.read_attribute_data(file, attr_type)
                    element.attributes[attr_name] = (attr_type, attr_value)

        return self

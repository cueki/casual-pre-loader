import struct
from typing import BinaryIO, Any

from core.constants import AttributeType, PCFVersion
from core.errors import PCFEncodingError
from models.pcf_file import PCFFile

class PCFWriter:
    """Handles writing PCF binary data"""

    def __init__(self, file: BinaryIO):
        self.file = file

    def write_null_terminated_string(self, data: bytes) -> None:
        """Write null-terminated string"""
        self.file.write(data + b'\x00')

    def write_attribute_data(self, attr_type: AttributeType, value: Any, version: str) -> None:
        """Write attribute data based on type"""
        if attr_type == AttributeType.ELEMENT:
            self.file.write(struct.pack('<I', value))
        elif attr_type == AttributeType.INTEGER:
            self.file.write(struct.pack('<i', value))
        elif attr_type == AttributeType.FLOAT:
            self.file.write(struct.pack('<f', value))
        elif attr_type == AttributeType.BOOLEAN:
            self.file.write(struct.pack('B', value))
        elif attr_type == AttributeType.STRING:
            if version == PCFVersion.DMX_BINARY4_PCF2:
                encoded = value.encode('ascii') if isinstance(value, str) else value
                self.file.write(struct.pack('<H', len(encoded)))
                self.file.write(encoded)
            else:
                self.write_null_terminated_string(
                    value.encode('ascii') if isinstance(value, str) else value
                )
        elif attr_type == AttributeType.BINARY:
            self.file.write(struct.pack('<I', len(value)))
            self.file.write(value)
        elif attr_type == AttributeType.COLOR:
            self.file.write(struct.pack('<4B', *value))
        elif attr_type == AttributeType.VECTOR2:
            self.file.write(struct.pack('<2f', *value))
        elif attr_type == AttributeType.VECTOR3:
            self.file.write(struct.pack('<3f', *value))
        elif attr_type == AttributeType.VECTOR4:
            self.file.write(struct.pack('<4f', *value))
        elif attr_type == AttributeType.MATRIX:
            for row in value:
                self.file.write(struct.pack('<4f', *row))
        elif attr_type.value >= AttributeType.ELEMENT_ARRAY.value:
            self.file.write(struct.pack('<I', len(value)))
            base_type = AttributeType(attr_type.value - 14)
            for item in value:
                self.write_attribute_data(base_type, item, version)
        else:
            raise PCFEncodingError(f"Unsupported attribute type: {attr_type}")

    def encode(self, pcf: PCFFile) -> None:
        """Encode PCF file"""
        try:
            # Write header
            self.write_null_terminated_string(f"{pcf.version}\n".encode('ascii'))

            # Write string dictionary
            if pcf.version == PCFVersion.DMX_BINARY4_PCF2:
                self.file.write(struct.pack('<I', len(pcf.string_dictionary)))
            else:
                self.file.write(struct.pack('<H', len(pcf.string_dictionary)))

            for string in pcf.string_dictionary:
                if isinstance(string, str):
                    self.write_null_terminated_string(string.encode('ascii'))
                else:
                    self.write_null_terminated_string(string)

            # Write elements
            self.file.write(struct.pack('<I', len(pcf.elements)))
            for element in pcf.elements:
                self.file.write(struct.pack('<H', element.type_name_index))
                if isinstance(element.element_name, str):
                    self.write_null_terminated_string(element.element_name.encode('ascii'))
                else:
                    self.write_null_terminated_string(element.element_name)
                self.file.write(element.data_signature)

                # Write attributes
                self.file.write(struct.pack('<I', len(element.attributes)))
                for attr_name, (attr_type, attr_value) in element.attributes.items():
                    name_index = pcf.string_dictionary.index(attr_name)
                    self.file.write(struct.pack('<H', name_index))
                    self.file.write(struct.pack('B', attr_type))
                    self.write_attribute_data(attr_type, attr_value, pcf.version)

        except (struct.error, IOError) as e:
            raise PCFEncodingError(f"Error encoding PCF: {e}")
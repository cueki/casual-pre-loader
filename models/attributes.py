from dataclasses import dataclass
from typing import Any, Tuple, List, Union, TypeVar, Generic
from core.constants import AttributeType
from core.errors import PCFAttributeError

Number = Union[int, float]
Vector2 = Tuple[float, float]
Vector3 = Tuple[float, float, float]
Vector4 = Tuple[float, float, float, float]
Color = Tuple[int, int, int, int]
Matrix = List[Vector4]  # 4x4 matrix
T = TypeVar('T')  # For generic array types

@dataclass
class AttributeValue(Generic[T]):
    """Wrapper for attribute values with type validation"""
    type: AttributeType
    value: T

    def __post_init__(self):
        """Validate value matches expected type"""
        try:
            self.validate()
        except ValueError as e:
            raise PCFAttributeError(f"Invalid value for type {self.type.name}: {e}")

    def validate(self) -> None:
        """Validate value matches attribute type"""
        if self.type == AttributeType.INTEGER:
            if not isinstance(self.value, int):
                raise ValueError(f"Expected int, got {type(self.value)}")

        elif self.type == AttributeType.FLOAT:
            if not isinstance(self.value, (int, float)):
                raise ValueError(f"Expected number, got {type(self.value)}")

        elif self.type == AttributeType.BOOLEAN:
            if not isinstance(self.value, bool):
                raise ValueError(f"Expected bool, got {type(self.value)}")

        elif self.type == AttributeType.STRING:
            if not isinstance(self.value, (str, bytes)):
                raise ValueError(f"Expected string or bytes, got {type(self.value)}")

        elif self.type == AttributeType.BINARY:
            if not isinstance(self.value, bytes):
                raise ValueError(f"Expected bytes, got {type(self.value)}")

        elif self.type == AttributeType.COLOR:
            if not (isinstance(self.value, tuple) and len(self.value) == 4 and
                    all(isinstance(x, int) and 0 <= x <= 255 for x in self.value)):
                raise ValueError("Expected RGBA tuple with values 0-255")

        elif self.type == AttributeType.VECTOR2:
            if not (isinstance(self.value, tuple) and len(self.value) == 2 and
                    all(isinstance(x, (int, float)) for x in self.value)):
                raise ValueError("Expected 2D vector tuple")

        elif self.type == AttributeType.VECTOR3:
            if not (isinstance(self.value, tuple) and len(self.value) == 3 and
                    all(isinstance(x, (int, float)) for x in self.value)):
                raise ValueError("Expected 3D vector tuple")

        elif self.type == AttributeType.VECTOR4:
            if not (isinstance(self.value, tuple) and len(self.value) == 4 and
                    all(isinstance(x, (int, float)) for x in self.value)):
                raise ValueError("Expected 4D vector tuple")

        elif self.type == AttributeType.MATRIX:
            if not (isinstance(self.value, list) and len(self.value) == 4 and
                    all(isinstance(row, tuple) and len(row) == 4 and
                        all(isinstance(x, (int, float)) for x in row)
                        for row in self.value)):
                raise ValueError("Expected 4x4 matrix")

        elif self.type.value >= AttributeType.ELEMENT_ARRAY.value:
            if not isinstance(self.value, list):
                raise ValueError(f"Expected list for array type {self.type.name}")
            # Validate each array element
            base_type = AttributeType(self.type.value - 14)
            for item in self.value:
                AttributeValue(base_type, item).validate()


class AttributeFactory:
    @staticmethod
    def create(attr_type: AttributeType, value: Any) -> AttributeValue:
        """Create a validated attribute value"""
        return AttributeValue(attr_type, value)

    @staticmethod
    def create_color(r: int, g: int, b: int, a: int = 255) -> AttributeValue[Color]:
        """Create a validated color attribute"""
        return AttributeValue(AttributeType.COLOR, (r, g, b, a))

    @staticmethod
    def create_vector2(x: float, y: float) -> AttributeValue[Vector2]:
        """Create a validated 2D vector attribute"""
        return AttributeValue(AttributeType.VECTOR2, (x, y))

    @staticmethod
    def create_vector3(x: float, y: float, z: float) -> AttributeValue[Vector3]:
        """Create a validated 3D vector attribute"""
        return AttributeValue(AttributeType.VECTOR3, (x, y, z))

    @staticmethod
    def create_vector4(x: float, y: float, z: float, w: float) -> AttributeValue[Vector4]:
        """Create a validated 4D vector attribute"""
        return AttributeValue(AttributeType.VECTOR4, (x, y, z, w))

    @staticmethod
    def create_matrix(rows: List[Vector4]) -> AttributeValue[Matrix]:
        """Create a validated matrix attribute"""
        if len(rows) != 4 or not all(len(row) == 4 for row in rows):
            raise PCFAttributeError("Matrix must be 4x4")
        return AttributeValue(AttributeType.MATRIX, rows)

    @staticmethod
    def create_array(base_type: AttributeType, values: List[Any]) -> AttributeValue[List[Any]]:
        """Create a validated array attribute"""
        if base_type.value >= AttributeType.ELEMENT_ARRAY.value:
            raise PCFAttributeError("Base type cannot be an array type")
        array_type = AttributeType(base_type.value + 14)
        return AttributeValue(array_type, values)


class AttributeUtils:
    @staticmethod
    def transform_color(color: Color, transform_fn: callable) -> Color:
        """Transform color values while preserving alpha"""
        r, g, b, a = color
        new_r, new_g, new_b = transform_fn(r, g, b)
        return new_r, new_g, new_b, a

    @staticmethod
    def format_value(attr: AttributeValue) -> str:
        """Format attribute value for display"""
        if attr.type == AttributeType.COLOR:
            r, g, b, a = attr.value
            return f"RGBA({r}, {g}, {b}, {a})"
        elif attr.type in (AttributeType.VECTOR2, AttributeType.VECTOR3, AttributeType.VECTOR4):
            return f"Vector({', '.join(f'{x:.3f}' for x in attr.value)})"
        elif attr.type == AttributeType.MATRIX:
            rows = [f"  [{', '.join(f'{x:.3f}' for x in row)}]" for row in attr.value]
            return "Matrix[\n" + "\n".join(rows) + "\n]"
        elif isinstance(attr.value, bytes):
            return f'"{attr.value.decode("ascii", errors="replace")}"'
        return str(attr.value)
from enum import IntEnum, StrEnum
from typing import Dict


class PCFVersion(StrEnum):
    # PCF version strings
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


ATTRIBUTE_VALUES: Dict[AttributeType, str] = {
    AttributeType.ELEMENT: '<I',
    AttributeType.INTEGER: '<i',
    AttributeType.FLOAT: '<f',
    AttributeType.BOOLEAN: 'B',
    AttributeType.STRING: '<H',
    AttributeType.BINARY: '<I',
    AttributeType.COLOR: '<4B',
    AttributeType.VECTOR2: '<2f',
    AttributeType.VECTOR3: '<3f',
    AttributeType.VECTOR4: '<4f',
    AttributeType.MATRIX: '<4f',
    AttributeType.ELEMENT_ARRAY: '<I',
}


DEFAULTS = [
    ("max_particles", 1000),
    ("initial_particles", 0),
    ("material", b"vgui/white"),  # Stored as bytes in PCF
    ("bounding_box_min", (-10.0, -10.0, -10.0)),  # Vector
    ("bounding_box_max", (10.0, 10.0, 10.0)),  # Vector
    ("cull_radius", 0.0),
    ("cull_cost", 1.0),
    ("cull_control_point", 0),
    ("cull_replacement_definition", b""),  # Empty string stored as bytes
    ("radius", 5.0),
    ("color", (255, 255, 255, 255)),  # Color stored as RGBA tuple
    ("rotation", 0.0),
    ("rotation_speed", 0.0),
    ("sequence_number", 0),
    ("sequence_number1", 0),
    ("group id", 0),
    ("maximum time step", 0.1),
    ("maximum sim tick rate", 0.0),
    ("minimum sim tick rate", 0.0),
    ("minimum rendered frames", 0),
    ("control point to disable rendering if it is the camera", -1),
    ("maximum draw distance", 100000.0),
    ("time to sleep when not drawn", 8.0),
    ("Sort particles", True),
    ("batch particle systems", False),
    ("view model effect", False)
]
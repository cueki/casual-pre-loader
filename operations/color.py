import copy
import colorsys
from typing import Tuple, List, Optional
from dataclasses import dataclass
from core.constants import AttributeType
from models.pcf_file import PCFFile

RGB = Tuple[int, int, int]
RGBA = Tuple[int, int, int, int]

@dataclass
class ColorChange:
    """Represents a color change in an element"""
    element_index: int
    element_type: str
    attribute_name: str
    old_color: RGBA
    new_color: RGBA


@dataclass
class ColorTransformResult:
    """Result of a color transformation operation"""
    changes: List[ColorChange]
    elements_processed: int
    attributes_changed: int

    @property
    def has_changes(self) -> bool:
        return len(self.changes) > 0


def rgb_to_hsv(r, g, b):
    r, g, b = r / 255.0, g / 255.0, b / 255.0
    h, s, v = colorsys.rgb_to_hsv(r, g, b)
    return h * 360, s * 100, v * 100


def hsv_to_rgb(h, s, v):
    h, s, v = h / 360, s / 100, v / 100
    return colorsys.hsv_to_rgb(h, s, v)


def is_color_attribute(name: str) -> bool:
    color_indicators = {'color', 'color1', 'color2', 'color_fade'}
    name = name.lower()
    return any(indicator in name for indicator in color_indicators)


def get_color_dominance(color: RGBA) -> Optional[str]:
    """
    Determine if a color is red or blue dominant.
    Returns: 'red', 'blue', or None if neither is dominant
    """
    r, g, b, a = color
    if r > b:
        return 'red'
    elif b > r:
        return 'blue'
    return None


def average_rgb(rgb_list):
    """Calculate average RGB from a list of RGB tuples."""
    if not rgb_list:
        return 0, 0, 0
    r_sum = sum(rgb[0] for rgb in rgb_list)
    g_sum = sum(rgb[1] for rgb in rgb_list)
    b_sum = sum(rgb[2] for rgb in rgb_list)
    n = len(rgb_list)
    return round(r_sum / n), round(g_sum / n), round(b_sum / n)


def color_shift(rgb_color_list: list, target_color: RGB):
    # Convert input RGB colors to HSV
    hsv_colors = [rgb_to_hsv(*rgb) for rgb in rgb_color_list]

    # Convert target color to HSV
    target_hsv = rgb_to_hsv(*target_color)

    # Calculate average hue
    avg_hue = sum(hsv[0] for hsv in hsv_colors) / len(hsv_colors)

    # Calculate hue difference
    hue_diff = target_hsv[0] - avg_hue

    # Shift each color by the hue difference
    shifted_colors = []
    for hsv in hsv_colors:
        new_hue = hsv[0] + hue_diff
        # Normalize hue to 0-360 range
        if new_hue > 360:
            new_hue -= 360
        elif new_hue < 0:
            new_hue += 360

        # Convert back to RGB, scale to 0-255 range
        rgb = hsv_to_rgb(new_hue, hsv[1], hsv[2])
        shifted_colors.append(tuple(round(c * 255) for c in rgb))

    return shifted_colors


def transform_with_shift(pcf: PCFFile, original_colors: List[Tuple[int, int, int]],
                         shifted_colors: List[Tuple[int, int, int]]) -> PCFFile:

    color_map = {orig: shifted for orig, shifted in zip(original_colors, shifted_colors)}
    result_pcf = copy.deepcopy(pcf)

    for element in result_pcf.elements:
        for attr_name, (attr_type, value) in element.attributes.items():
            if attr_type != AttributeType.COLOR:
                continue

            r, g, b, a = value
            rgb = (r, g, b)

            if rgb in color_map:
                new_r, new_g, new_b = color_map[rgb]
                element.attributes[attr_name] = (attr_type, (new_r, new_g, new_b, a))

    return result_pcf


def analyze_pcf_colors(pcf_input):
    red_colors = []
    blue_colors = []

    for element in pcf_input.elements:
        for attr_name, (attr_type, value) in element.attributes.items():
            if attr_type != AttributeType.COLOR:
                continue

            r, g, b, a = value
            team = get_color_dominance((r, g, b, a))
            if team == 'red':
                red_colors.append((r, g, b))
            if team == 'blue':
                blue_colors.append((r, g, b))
            else:
                continue

    return red_colors, blue_colors


def print_color_changes(result: ColorTransformResult) -> None:
    """Print a formatted summary of color changes"""
    if not result.has_changes:
        print("No color changes were made")
        return

    print(f"\nProcessed {result.elements_processed} elements")
    print(f"Changed {result.attributes_changed} color attributes\n")

    for change in result.changes:
        print(f"Element {change.element_index} ({change.element_type})")
        print(f"  Attribute: {change.attribute_name}")
        print(f"  Old: RGBA{change.old_color}")
        print(f"  New: RGBA{change.new_color}\n")
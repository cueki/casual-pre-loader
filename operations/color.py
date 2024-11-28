import copy
import colorsys
from typing import Tuple, List, Optional, Dict
from dataclasses import dataclass
from core.constants import AttributeType
from core.traversal import PCFTraversal
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
    color_indicators = {b'color', b'color1', b'color2', b'color3', b'color4', b'color_fade', b'tint clamp'}
    if isinstance(name, str):
        name = name.encode('ascii')
    return any(indicator in name.lower() for indicator in color_indicators)


def get_color_dominance(color: RGBA) -> Optional[str]:
    r, g, b, a = color
    if abs(r - b) <= 10:
        return 'neutral'
    elif r > b:
        return 'red'
    elif b > r:
        return 'blue'
    return None


def average_rgb(rgb_list):
    """Calculate average RGB from a list of RGB tuples."""
    r_sum = sum(rgb[0] for rgb in rgb_list)
    g_sum = sum(rgb[1] for rgb in rgb_list)
    b_sum = sum(rgb[2] for rgb in rgb_list)
    n = len(rgb_list)
    return (r_sum / n), (g_sum / n), (b_sum / n)


def color_shift(rgb_color_list: list, target_color: RGB):
    # Calc average rgb
    avg_r, avg_g, avg_b = average_rgb(rgb_color_list)

    # Convert to average HSV
    average_hsv = rgb_to_hsv(avg_r, avg_g, avg_b)
    
    # Convert target color to HSV
    target_hsv = rgb_to_hsv(*target_color)

    # Calculate hue difference
    hue_diff = target_hsv[0] - average_hsv[0]

    # Convert input RGB colors to HSV
    hsv_colors = [rgb_to_hsv(*rgb) for rgb in rgb_color_list]

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
        rgb = hsv_to_rgb(new_hue, hsv[1], 100)
        shifted_colors.append(tuple(round(c * 255) for c in rgb))

    return shifted_colors


def transform_with_shift(pcf: PCFFile, original_colors: List[Tuple[int, int, int]],
                         shifted_colors: List[Tuple[int, int, int]], debug=True) -> PCFFile:
    color_map = {orig: shifted for orig, shifted in zip(original_colors, shifted_colors)}
    result_pcf = copy.deepcopy(pcf)
    changes_made = []

    for element in result_pcf.elements:
        for attr_name, (attr_type, value) in element.attributes.items():
            if attr_type != AttributeType.COLOR:
                continue
            if is_color_attribute(attr_name):
                r, g, b, a = value
                rgb = (r, g, b)
                if rgb in color_map:
                    new_r, new_g, new_b = color_map[rgb]
                    old_value = (r, g, b, a)
                    new_value = (new_r, new_g, new_b, a)
                    element.attributes[attr_name] = (attr_type, new_value)

                    changes_made.append({
                        'element_name': element.element_name,
                        'attribute': attr_name,
                        'old_color': old_value,
                        'new_color': new_value
                    })

    if debug:
        print("\nColor changes made to PCF:")
        for change in changes_made:
            print(f"\nElement: {change['element_name']}")
            print(f"Attribute: {change['attribute']}")
            print(f"Old color: RGBA{change['old_color']}")
            print(f"New color: RGBA{change['new_color']}")

    return result_pcf


def analyze_pcf_colors(pcf: PCFFile, debug=True) -> Dict[str, Dict[str, List[RGB]]]:
    traversal = PCFTraversal(pcf)
    colors = {
        'red': {'color1': [], 'color2': [], 'tint_clamp': [], 'color_fade': []},
        'blue': {'color1': [], 'color2': [], 'tint_clamp': [], 'color_fade': []},
        'neutral': {'color1': [], 'color2': [], 'tint_clamp': [], 'color_fade': []}
    }

    current_element = None
    color_attrs = traversal.find_attributes(attr_type=AttributeType.COLOR, max_depth=0)

    if debug:
        print("\nStarting color analysis...")

    for element, attr_name, (_, rgba), _ in color_attrs:
        if not element.element_name.startswith(b'Color'):
            current_element = element.element_name
            if debug:
                print(f"\nCurrent context element: {current_element}")
        elif current_element:
            r, g, b, a = rgba
            if (r + g + b) == 765 or (r + g + b) == 0 or (r == g == b):
                if debug:
                    print(f"Skipping white/black/grey color: RGB({r},{g},{b})")
                continue

            if debug:
                print(f"\nProcessing color: RGB({r},{g},{b})")
                print(f"Attribute name: {attr_name}")

            # Determine team
            is_red = b'_red' in current_element or b'red_' in current_element
            is_blue = b'_blue' in current_element or b'blue_' in current_element
            team = 'red' if is_red else 'blue' if is_blue else 'neutral'

            if debug:
                print(f"Team detection:")
                print(f"  '_red' or 'red_' found: {is_red}")
                print(f"  '_blue' or 'blue_' found: {is_blue}")
                print(f"  Assigned team: {team}")

            # Determine category
            if b'tint clamp' in attr_name:
                category = 'tint_clamp'
            elif b'color_fade' in attr_name:
                category = 'color_fade'
            elif b'color1' in attr_name:
                category = 'color1'
            elif b'color2' in attr_name:
                category = 'color2'
            else:
                if debug:
                    print(f"Unknown category for attribute: {attr_name}")
                continue

            if debug:
                print(f"Category: {category}")

            colors[team][category].append((r, g, b))

    if debug:
        print("\nFinal color counts:")
        for team in colors:
            print(f"\n{team.upper()} TEAM:")
            for category, color_list in colors[team].items():
                print(f"  {category}: {len(color_list)} colors")
                for color in color_list:
                    print(f"    RGB{color}")

    return colors


def print_color_changes(result: ColorTransformResult) -> None:
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


def transform_team_colors(result_pcf: PCFFile, colors: Dict[str, Dict[str, List[RGB]]],
                          targets: Dict[str, Dict[str, RGB]], debug=True) -> PCFFile:
    result = result_pcf

    if debug:
        print("\nStarting color transformation...")
        print("\nInitial state:")
        for team in colors:
            print(f"\n{team.upper()} TEAM TARGET COLORS:")
            for category, target in targets[team].items():
                print(f"  {category}: RGB{target}")

    has_red = any(colors['red'].values())
    has_blue = any(colors['blue'].values())

    if debug:
        print(f"\nTeam detection:")
        print(f"  Has red team: {has_red}")
        print(f"  Has blue team: {has_blue}")

    if has_red and has_blue:
        if debug:
            print("\nProcessing both teams separately")

        for team in ['red', 'blue', 'neutral']:
            if debug:
                print(f"\nProcessing {team} team:")

            for category in ['color1', 'color2', 'tint_clamp', 'color_fade']:
                if colors[team][category] and targets[team][category]:
                    if debug:
                        print(f"\n  Processing {category}:")
                        print(f"    Original colors: {colors[team][category]}")
                        print(f"    Target color: RGB{targets[team][category]}")

                    shifted = color_shift(colors[team][category], targets[team][category])

                    if debug:
                        print(f"    Shifted colors: {shifted}")

                    result = transform_with_shift(result, colors[team][category], shifted, debug=True)
    else:
        if debug:
            print("\nProcessing all colors together")

        all_colors_by_category = {
            'color1': [], 'color2': [], 'tint_clamp': [], 'color_fade': []
        }

        for team in ['red', 'blue', 'neutral']:
            for category in ['color1', 'color2', 'tint_clamp', 'color_fade']:
                all_colors_by_category[category].extend(colors[team][category])

        if debug:
            print("\nCombined colors by category:")
            for category, color_list in all_colors_by_category.items():
                print(f"  {category}: {len(color_list)} colors")
                print(f"    Colors: {color_list}")

        for category in ['color1', 'color2', 'tint_clamp', 'color_fade']:
            if all_colors_by_category[category] and targets['neutral'][category]:
                if debug:
                    print(f"\nProcessing combined {category}:")
                    print(f"  Original colors: {all_colors_by_category[category]}")
                    print(f"  Target color: RGB{targets['neutral'][category]}")

                shifted = color_shift(all_colors_by_category[category], targets['neutral'][category])

                if debug:
                    print(f"  Shifted colors: {shifted}")

                result = transform_with_shift(result, all_colors_by_category[category], shifted, debug=True)

    return result
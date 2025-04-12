from pathlib import Path
from typing import Dict
from PIL import Image, ImageFilter
from core.handlers.vtf_handler import VTFHandler
from core.constants import DECAL_MAPPING


def create_shadow_effect(image, shadow_color=(127, 127, 127, 255)):
    if image.mode != 'RGBA':
        image = image.convert('RGBA')

    # create a mask from the alpha channel
    alpha = image.split()[3]
    shadow_mask = alpha.copy()
    shadow_mask = shadow_mask.filter(ImageFilter.MaxFilter(3))
    shadow = Image.new('RGBA', image.size, shadow_color)
    shadow.putalpha(shadow_mask)

    # bg, then shadow, then original image
    result = Image.new('RGBA', image.size, (125, 127, 125, 0))
    result = Image.alpha_composite(result, shadow)
    result = Image.alpha_composite(result, image)

    return result


def paste_with_full_transparency(base_img, overlay_img, position):
    overlay_width, overlay_height = overlay_img.size
    base_width, base_height = base_img.size

    # get pixel data
    base_pixels = base_img.load()
    overlay_pixels = overlay_img.load()

    # calculate effective paste area
    x_start, y_start = position
    x_end = min(x_start + overlay_width, base_width)
    y_end = min(y_start + overlay_height, base_height)

    # replace pixels (pillow will ignore pixels that have alpha=0, so we do it)
    for y in range(y_start, y_end):
        for x in range(x_start, x_end):
            overlay_x = x - x_start
            overlay_y = y - y_start

            if 0 <= overlay_x < overlay_width and 0 <= overlay_y < overlay_height:
                base_pixels[x, y] = overlay_pixels[overlay_x, overlay_y]

    return base_img


def get_decal_info(file_path: str):
    if file_path.startswith("decal/"):
        if file_path in DECAL_MAPPING:
            return file_path, DECAL_MAPPING[file_path]
        return None, None

    path_obj = Path(file_path)
    file_name = path_obj.stem
    potential_paths = [
        f"decal/{file_name}",
        f"decal/flesh/{file_name}"
    ]

    if "flesh" in str(path_obj):
        potential_paths.reverse()

    for decal_path in potential_paths:
        if decal_path in DECAL_MAPPING:
            return decal_path, DECAL_MAPPING[decal_path]

    return None, None


class DecalMerge:
    def __init__(self, working_dir="temp/vtf_files", debug=False):
        self.working_dir = Path(working_dir)
        self.working_dir.mkdir(parents=True, exist_ok=True)
        self.vtf_handler = VTFHandler(working_dir)
        self.debug = debug
        self.temp_files = []

    def modify_mod2x_sprite_sheet(self, decal_vtfs: Dict[str, str], sprite_sheet_png):
        try:
            sprite_sheet = Image.open(sprite_sheet_png)
            # process each decal
            for decal_path, vtf_file in decal_vtfs.items():
                decal_type, decal_info = get_decal_info(decal_path)
                print(decal_path, decal_type)
                if not decal_type or not decal_info:
                    print(f"Warning: Could not find mapping for decal {decal_path}")
                    continue

                # convert decal to PNG
                splatter_png_path = self.vtf_handler.convert_vtf_to_png(vtf_file)

                # process the decal image
                splatter = Image.open(splatter_png_path)
                splatter = splatter.resize(decal_info["size"])
                splatter = create_shadow_effect(splatter)
                splatter_out = self.working_dir / str(Path(decal_path).name + ".png")
                splatter.save(splatter_out)

                # paste the decal onto the sprite sheet
                sprite_sheet = paste_with_full_transparency(
                    sprite_sheet, splatter, decal_info["position"]
                )

            # save the modified sprite sheet
            modified_png = self.working_dir / "modified_sprite_sheet.png"
            sprite_sheet.save(modified_png)

            # convert back to VTF
            result_vtf = self.vtf_handler.convert_png_to_vtf(modified_png)
            if not result_vtf:
                return False

            return True

        except Exception as e:
            print(f"Error modifying sprite sheet: {e}")
            return False

    def process_mod_decals(self, mod_dir: Path, output_dir: Path):
        pass

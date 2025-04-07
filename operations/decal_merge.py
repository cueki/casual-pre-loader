from pathlib import Path
from PIL import Image, ImageFilter
from typing import List
from core.handlers.vtf_handler import VTFHandler


def create_shadow_effect(image, shadow_size=3, shadow_color=(127, 127, 127, 255)):
    if image.mode != 'RGBA':
        image = image.convert('RGBA')

    # create a mask from the alpha channel
    alpha = image.split()[3]

    # create a shadow by applying MaxFilter multiple times
    shadow_mask = alpha.copy()
    for _ in range(shadow_size):
        shadow_mask = shadow_mask.filter(ImageFilter.MaxFilter(3))
    shadow = Image.new('RGBA', image.size, shadow_color)
    shadow.putalpha(shadow_mask)

    # shadow first, then original image
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

    #calculate effective paste area
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


class DecalMerge:
    def __init__(self, working_dir="temp/vtf_files", debug=False):
        self.working_dir = Path(working_dir)
        self.working_dir.mkdir(parents=True, exist_ok=True)
        self.vtf_handler = VTFHandler(working_dir)
        self.debug = debug
        self.temp_files = []

    def modify_blood_sprite_sheet(self, decal_vtfs: List[str], sprite_sheet_vtf, output_vtf):
        modified_png = self.working_dir / "modified_sprite_sheet.png"
        try:
            # convert sprite sheet to PNG
            converted_path = self.vtf_handler.convert_vtf_to_png(sprite_sheet_vtf)
            if not converted_path:
                return False

            sprite_sheet = Image.open(converted_path)

            # hardcoded coordinates for placing each splatter
            coordinates = [
                (384, 128),
                (512, 128),
                (640, 128),
                (768, 128),
                (256, 256),
                (384, 256)
            ]

            for i, (vtf_file, position) in enumerate(zip(decal_vtfs, coordinates)):
                # convert decal to PNG
                splatter_png_path = self.vtf_handler.convert_vtf_to_png(vtf_file)
                if not splatter_png_path:
                    continue

                # process the decal image
                splatter = Image.open(splatter_png_path)
                splatter = splatter.resize((128, 128))
                splatter = create_shadow_effect(splatter, shadow_size=4, shadow_color=(127, 127, 127, 255))

                # paste the decal onto the sprite sheet
                sprite_sheet = paste_with_full_transparency(sprite_sheet, splatter, position)

            # save the modified sprite sheet
            sprite_sheet.save(modified_png)

            # convert back to VTF
            result_vtf = self.vtf_handler.convert_png_to_vtf(modified_png)
            if not result_vtf:
                return False

            # copy to output location if different
            if str(result_vtf) != output_vtf:
                import shutil
                shutil.copy2(result_vtf, output_vtf)

            return True

        except Exception as e:
            print(f"Error modifying sprite sheet: {e}")
            return False

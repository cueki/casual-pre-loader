import os
import sys
import subprocess
from PIL import Image, ImageFilter


def convert_vtf_to_png(vtf_file, png_file):
    # cmd wrapper
    # TODO: add proper linux + windows support
    try:
        os.makedirs(os.path.dirname(os.path.abspath(png_file)), exist_ok=True)
        print(f"Converting {vtf_file} to {png_file}")
        subprocess.run([
            'wine',
            '/home/madison/Downloads/test/VTFCmd.exe',
            '-file', vtf_file,
            '-output', os.path.dirname(png_file),
            '-exportformat', 'png'
        ], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        return True
    except Exception as e:
        print(f"Error converting VTF to PNG: {e}")
        return False


def convert_png_to_vtf(png_file, vtf_file):
    # cmd wrapper
    # TODO: add proper linux + windows support
    try:
        cmd = [
            'wine',
            '/home/madison/Downloads/test/VTFCmd.exe',
            '-file', png_file,
            '-output', os.path.dirname(vtf_file),
            '-format', 'rgba8888'
        ]

        print(f"Converting {png_file} to {vtf_file}")
        subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return True
    except Exception as e:
        print(f"Error converting PNG to VTF: {e}")
        return False


def create_shadow_effect(image, shadow_size=3, shadow_color=(127, 127, 127, 255)):
    if image.mode != 'RGBA':
        image = image.convert('RGBA')

    # create a mask from the alpha channel
    alpha = image.split()[3]

    # create a  shadow by applying MaxFilter multiple times, this should be tested more
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
    # I don't know if this is needed specifically, but resize will blank pixels with 0 alpha, and we need to keep that data for VTFCmd to work
    overlay_width, overlay_height = overlay_img.size
    base_width, base_height = base_img.size

    # get pixel data
    base_pixels = base_img.load()
    overlay_pixels = overlay_img.load()

    # calculate effective paste area
    x_start, y_start = position
    x_end = min(x_start + overlay_width, base_width)
    y_end = min(y_start + overlay_height, base_height)

    # replace pixels
    for y in range(y_start, y_end):
        for x in range(x_start, x_end):
            # get corresponding pixel in overlay
            overlay_x = x - x_start
            overlay_y = y - y_start

            if 0 <= overlay_x < overlay_width and 0 <= overlay_y < overlay_height:
                # replace base pixel with overlay pixel
                base_pixels[x, y] = overlay_pixels[overlay_x, overlay_y]

    return base_img


def modify_blood_sprite_sheet(decal_vtfs, sprite_sheet_vtf, output_vtf):
    # this is the main logic loop
    # TODO: switch to pathlib and use our file manager
    working_dir = "working_files"
    os.makedirs(working_dir, exist_ok=True)
    sprite_sheet_png = os.path.join(working_dir, "sprite_sheet.png")
    modified_png = os.path.join(working_dir, "modified_sprite_sheet.png")

    try:
        if not convert_vtf_to_png(sprite_sheet_vtf, sprite_sheet_png):
            print("Failed to convert sprite sheet to PNG")
            return False

        sprite_sheet = Image.open(sprite_sheet_png)

        # hardcoded coordinates for placing each splatter
        # TODO: make this dynamic somehow?
        coordinates = [
            (384, 128),
            (512, 128),
            (640, 128),
            (768, 128),
            (256, 256),
            (384, 256)
        ]

        for i, (vtf_file, position) in enumerate(zip(decal_vtfs, coordinates)):
            splatter_png = os.path.join(working_dir, f"splatter_{i}.png")
            if not convert_vtf_to_png(vtf_file, splatter_png):
                print(f"Failed to convert splatter {i+1} to PNG")
                continue

            # resize, make shadow, compose together
            splatter = Image.open(splatter_png)
            splatter = splatter.resize((128, 128))
            splatter = create_shadow_effect(splatter, shadow_size=4, shadow_color=(127, 127, 127, 255))

            # data intact with alpha at 0
            sprite_sheet = paste_with_full_transparency(sprite_sheet, splatter, position)

        sprite_sheet.save(modified_png)
        if not convert_png_to_vtf(modified_png, output_vtf):
            print("Failed to convert modified sprite sheet to VTF")
            return False

        print(f"Successfully created modified sprite sheet: {output_vtf}")
        return True

    except Exception as e:
        print(f"Error modifying sprite sheet: {e}")
        return False


def main():
    # TODO: get this shit outta here lol
    if len(sys.argv) < 8:
        print("Usage: python modify_blood_sprite.py <sprite_sheet.vtf> <output.vtf> <splatter1.vtf> <splatter2.vtf> <splatter3.vtf> <splatter4.vtf> <splatter5.vtf> <splatter6.vtf>")
        return

    sprite_sheet_vtf = sys.argv[1]
    output_vtf = sys.argv[2]
    splatter_vtfs = sys.argv[3:9]  # get the 6 splatter VTFs

    missing_files = []
    for vtf_file in [sprite_sheet_vtf] + splatter_vtfs:
        if not os.path.exists(vtf_file):
            missing_files.append(vtf_file)

    if missing_files:
        print("Error: The following files were not found:")
        for file in missing_files:
            print(f"  - {file}")
        return

    modify_blood_sprite_sheet(splatter_vtfs, sprite_sheet_vtf, output_vtf)


if __name__ == "__main__":
    main()

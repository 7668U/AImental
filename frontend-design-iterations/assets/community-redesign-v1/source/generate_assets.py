from pathlib import Path
import math
import random

from PIL import Image, ImageDraw, ImageFilter


ROOT = Path(__file__).resolve().parents[1]
ASSET_DIR = ROOT / "assets"
ASSET_DIR.mkdir(parents=True, exist_ok=True)

random.seed(17)


def rgb(value):
    value = value.lstrip("#")
    return tuple(int(value[index:index + 2], 16) for index in (0, 2, 4))


def vertical_gradient(size, top, bottom):
    width, height = size
    image = Image.new("RGB", size, top)
    pixels = image.load()
    top_rgb = rgb(top)
    bottom_rgb = rgb(bottom)
    for y in range(height):
        ratio = y / max(1, height - 1)
        color = tuple(
            round(top_rgb[channel] * (1 - ratio) + bottom_rgb[channel] * ratio)
            for channel in range(3)
        )
        for x in range(width):
            pixels[x, y] = color
    return image.convert("RGBA")


def add_grain(image, amount=5, opacity=20):
    noise = Image.new("L", image.size)
    noise_pixels = noise.load()
    for y in range(image.height):
        for x in range(image.width):
            noise_pixels[x, y] = max(
                0,
                min(255, 128 + random.randint(-amount, amount)),
            )
    noise = noise.filter(ImageFilter.GaussianBlur(0.35))
    grain = Image.new("RGBA", image.size, (118, 84, 56, 0))
    grain.putalpha(noise.point(lambda value: int(abs(value - 128) * opacity / max(1, amount))))
    return Image.alpha_composite(image, grain)


def soft_ellipse(image, box, color, blur=28):
    layer = Image.new("RGBA", image.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    draw.ellipse(box, fill=color)
    layer = layer.filter(ImageFilter.GaussianBlur(blur))
    image.alpha_composite(layer)


def soft_shadow(image, box, radius, color=(91, 55, 31, 36), blur=24, offset=(0, 12)):
    layer = Image.new("RGBA", image.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    shifted = tuple(
        value + (offset[0] if index % 2 == 0 else offset[1])
        for index, value in enumerate(box)
    )
    draw.rounded_rectangle(shifted, radius=radius, fill=color)
    image.alpha_composite(layer.filter(ImageFilter.GaussianBlur(blur)))


def draw_spark(draw, center, radius, fill, width=3):
    x, y = center
    draw.line((x - radius, y, x + radius, y), fill=fill, width=width)
    draw.line((x, y - radius, x, y + radius), fill=fill, width=width)
    draw.ellipse(
        (x - width, y - width, x + width, y + width),
        fill=fill,
    )


def generate_hero():
    size = (1500, 760)
    image = vertical_gradient(size, "#FFF9F2", "#FCEBD9")
    soft_ellipse(image, (-220, -180, 470, 420), (255, 199, 139, 54), 80)
    soft_ellipse(image, (1040, -140, 1640, 420), (143, 171, 185, 42), 72)
    soft_ellipse(image, (970, 390, 1640, 940), (255, 151, 79, 38), 86)

    draw = ImageDraw.Draw(image)

    # Quiet paper-like linework on the left.
    draw.arc((70, 82, 720, 550), 202, 322, fill=(226, 171, 122, 76), width=3)
    draw.arc((120, 180, 850, 700), 20, 126, fill=(243, 190, 137, 64), width=2)
    for center, radius in [((180, 165), 9), ((420, 120), 7), ((560, 260), 6)]:
        draw_spark(draw, center, radius, (255, 255, 255, 190), 3)

    # Arched window.
    window_box = (885, 58, 1425, 636)
    shadow_box = (871, 52, 1439, 650)
    soft_shadow(image, shadow_box, 100, (93, 61, 38, 30), 28, (0, 15))
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle(shadow_box, radius=106, fill=(255, 253, 247, 230))

    window_mask = Image.new("L", size, 0)
    mask_draw = ImageDraw.Draw(window_mask)
    mask_draw.rounded_rectangle(window_box, radius=92, fill=255)
    sky = vertical_gradient(size, "#C9DCE7", "#F7D8AE")
    sky_draw = ImageDraw.Draw(sky)
    sky_draw.ellipse((1118, 186, 1378, 446), fill=(249, 181, 91, 176))
    sky_draw.ellipse((1000, 245, 1220, 430), fill=(255, 245, 218, 224))
    sky_draw.ellipse((1170, 248, 1465, 440), fill=(255, 246, 223, 224))
    sky_draw.ellipse((912, 340, 1198, 500), fill=(255, 250, 236, 196))
    image.alpha_composite(Image.composite(sky, Image.new("RGBA", size), window_mask))
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle(window_box, radius=92, outline=(255, 249, 238, 240), width=16)
    draw.line((1155, 66, 1155, 634), fill=(255, 250, 242, 188), width=8)

    # Floor and table.
    draw.rounded_rectangle((785, 585, 1480, 698), radius=55, fill=(247, 222, 191, 210))
    draw.ellipse((968, 525, 1288, 620), fill=(255, 252, 246, 242))
    draw.rounded_rectangle((1110, 606, 1147, 720), radius=18, fill=(173, 120, 80, 150))

    # Chairs, calm and adult rather than mascot-like.
    soft_shadow(image, (790, 440, 1005, 706), 78, (100, 62, 36, 32), 20, (0, 14))
    soft_shadow(image, (1260, 434, 1472, 706), 78, (100, 62, 36, 32), 20, (0, 14))
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle((804, 430, 990, 655), radius=74, fill=(205, 130, 100, 232))
    draw.rounded_rectangle((1280, 425, 1460, 654), radius=74, fill=(134, 154, 126, 232))
    draw.rounded_rectangle((826, 486, 968, 670), radius=58, fill=(240, 179, 142, 210))
    draw.rounded_rectangle((1300, 480, 1440, 670), radius=58, fill=(172, 184, 150, 210))
    draw.rounded_rectangle((830, 638, 850, 724), radius=10, fill=(121, 81, 58, 170))
    draw.rounded_rectangle((948, 638, 968, 724), radius=10, fill=(121, 81, 58, 170))
    draw.rounded_rectangle((1305, 638, 1325, 724), radius=10, fill=(121, 81, 58, 170))
    draw.rounded_rectangle((1423, 638, 1443, 724), radius=10, fill=(121, 81, 58, 170))

    # Cups and a subtle thread of light.
    for x, cup_color in [(1030, (255, 128, 52, 238)), (1195, (248, 236, 219, 250))]:
        draw.rounded_rectangle((x, 545, x + 70, 596), radius=16, fill=cup_color)
        draw.arc((x + 54, 551, x + 88, 591), 270, 90, fill=(155, 96, 61, 180), width=6)
        draw.ellipse((x + 8, 540, x + 62, 551), fill=(106, 64, 43, 180))
    glow = Image.new("RGBA", size, (0, 0, 0, 0))
    glow_draw = ImageDraw.Draw(glow)
    thread_points = [(1090, 540), (1112, 512), (1152, 509), (1188, 540)]
    glow_draw.line(thread_points, fill=(255, 169, 77, 210), width=5, joint="curve")
    image.alpha_composite(glow.filter(ImageFilter.GaussianBlur(9)))
    draw = ImageDraw.Draw(image)
    draw.line(thread_points, fill=(255, 166, 70, 210), width=3, joint="curve")

    # Plant and lamp.
    draw.rounded_rectangle((876, 534, 958, 614), radius=20, fill=(225, 156, 102, 230))
    for stem, leaf_box, angle in [
        ((916, 540, 875, 468), (842, 432, 904, 499), -22),
        ((920, 540, 924, 448), (894, 410, 954, 476), 5),
        ((924, 540, 969, 474), (944, 438, 1005, 502), 24),
    ]:
        draw.line(stem, fill=(92, 126, 73, 220), width=6)
        leaf = Image.new("RGBA", (90, 90), (0, 0, 0, 0))
        leaf_draw = ImageDraw.Draw(leaf)
        leaf_draw.ellipse((14, 18, 76, 72), fill=(127, 158, 101, 232))
        leaf = leaf.rotate(angle, resample=Image.Resampling.BICUBIC, expand=True)
        image.alpha_composite(leaf, (int(leaf_box[0]), int(leaf_box[1])))

    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle((1450, 278, 1461, 635), radius=6, fill=(104, 79, 66, 165))
    draw.arc((1355, 228, 1464, 348), 190, 335, fill=(104, 79, 66, 165), width=11)
    draw.ellipse((1342, 220, 1428, 270), fill=(247, 173, 82, 226))
    soft_ellipse(image, (1320, 212, 1450, 345), (255, 181, 90, 42), 22)

    # Blank notes and restrained accents.
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle((723, 260, 838, 338), radius=12, fill=(255, 252, 242, 188))
    draw.line((748, 286, 810, 286), fill=(218, 157, 110, 95), width=3)
    draw.line((748, 306, 790, 306), fill=(218, 157, 110, 72), width=3)
    draw_spark(draw, (1360, 125), 10, (255, 255, 255, 220), 3)
    draw_spark(draw, (805, 170), 7, (250, 167, 80, 135), 3)

    image = add_grain(image, amount=6, opacity=14)
    image.putalpha(255)
    image.save(ASSET_DIR / "community-hero-atmosphere.png")


def generate_empty_state():
    size = (800, 560)
    image = Image.new("RGBA", size, (0, 0, 0, 0))
    soft_ellipse(image, (120, 400, 690, 545), (110, 68, 39, 34), 28)
    draw = ImageDraw.Draw(image)

    # Empty chair.
    draw.rounded_rectangle((120, 144, 376, 430), radius=78, fill=(220, 139, 102, 244))
    draw.rounded_rectangle((148, 195, 348, 416), radius=62, fill=(248, 188, 151, 238))
    draw.rounded_rectangle((152, 391, 176, 491), radius=11, fill=(118, 83, 64, 196))
    draw.rounded_rectangle((320, 391, 344, 491), radius=11, fill=(118, 83, 64, 196))
    draw.rounded_rectangle((175, 220, 320, 288), radius=26, fill=(255, 236, 215, 215))

    # Side table and lamp.
    draw.ellipse((415, 342, 655, 407), fill=(254, 248, 238, 250))
    draw.rounded_rectangle((523, 392, 547, 493), radius=12, fill=(145, 101, 72, 170))
    draw.rounded_rectangle((501, 132, 516, 353), radius=8, fill=(99, 79, 70, 190))
    draw.arc((424, 89, 510, 190), 196, 344, fill=(99, 79, 70, 190), width=13)
    draw.ellipse((407, 77, 491, 132), fill=(250, 169, 78, 246))
    soft_ellipse(image, (390, 65, 525, 210), (255, 180, 88, 48), 26)

    # Blank conversation cards.
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle((408, 224, 545, 322), radius=24, fill=(255, 253, 248, 250), outline=(240, 205, 175, 220), width=3)
    draw.polygon([(438, 318), (458, 318), (442, 344)], fill=(255, 253, 248, 250))
    draw.rounded_rectangle((503, 188, 667, 303), radius=25, fill=(221, 232, 234, 247), outline=(181, 202, 205, 220), width=3)
    draw.polygon([(612, 298), (635, 298), (627, 329)], fill=(221, 232, 234, 247))
    draw.line((438, 256, 511, 256), fill=(214, 158, 116, 125), width=5)
    draw.line((438, 279, 494, 279), fill=(214, 158, 116, 95), width=5)
    draw.line((535, 226, 625, 226), fill=(126, 156, 162, 110), width=5)
    draw.line((535, 250, 605, 250), fill=(126, 156, 162, 80), width=5)

    # Open envelope and paper plane.
    draw.polygon([(438, 390), (562, 390), (545, 458), (455, 458)], fill=(255, 244, 228, 245))
    draw.line((438, 390, 500, 431, 562, 390), fill=(220, 165, 116, 170), width=4)
    draw.polygon([(620, 394), (726, 366), (672, 442), (662, 404)], fill=(248, 153, 73, 230))
    draw.line((620, 394, 662, 404, 726, 366), fill=(210, 105, 44, 160), width=3)

    for center, radius, color in [
        ((95, 166), 11, (247, 171, 83, 175)),
        ((704, 150), 9, (255, 203, 124, 185)),
        ((690, 286), 7, (158, 181, 184, 150)),
    ]:
        draw_spark(draw, center, radius, color, 3)

    image.save(ASSET_DIR / "community-empty-conversation.png")


def generate_texture():
    size = (750, 1624)
    image = vertical_gradient(size, "#FFF9F3", "#FFFDF9")
    soft_ellipse(image, (-230, -170, 420, 460), (255, 178, 102, 44), 96)
    soft_ellipse(image, (470, -100, 920, 520), (139, 168, 181, 30), 92)
    soft_ellipse(image, (-160, 1010, 450, 1680), (243, 183, 142, 28), 110)
    soft_ellipse(image, (470, 1040, 920, 1640), (145, 164, 121, 22), 100)
    draw = ImageDraw.Draw(image)
    draw.arc((-120, 170, 620, 870), 214, 315, fill=(234, 188, 150, 34), width=3)
    draw.arc((260, 760, 920, 1450), 25, 128, fill=(151, 172, 177, 26), width=3)
    for center, radius in [((104, 284), 5), ((653, 456), 6), ((144, 1235), 5), ((620, 1410), 4)]:
        draw_spark(draw, center, radius, (255, 255, 255, 120), 2)
    image = add_grain(image, amount=7, opacity=13)
    image.putalpha(255)
    image.save(ASSET_DIR / "community-paper-texture.png")


def generate_soft_decor():
    size = (1000, 430)
    image = Image.new("RGBA", size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    draw.arc((30, 40, 560, 410), 200, 334, fill=(237, 167, 110, 92), width=4)
    draw.arc((465, -160, 980, 350), 38, 150, fill=(133, 162, 169, 76), width=4)
    for center, radius, color in [
        ((124, 122), 12, (248, 161, 81, 170)),
        ((305, 290), 8, (255, 199, 124, 170)),
        ((704, 105), 9, (140, 166, 172, 150)),
        ((882, 272), 11, (244, 180, 128, 150)),
    ]:
        draw_spark(draw, center, radius, color, 3)
    for x, y, color, angle in [
        (202, 188, (227, 147, 99, 145), -24),
        (770, 198, (139, 157, 116, 135), 22),
        (824, 236, (195, 134, 106, 115), -15),
    ]:
        leaf = Image.new("RGBA", (90, 55), (0, 0, 0, 0))
        leaf_draw = ImageDraw.Draw(leaf)
        leaf_draw.ellipse((10, 10, 80, 45), fill=color)
        leaf = leaf.rotate(angle, resample=Image.Resampling.BICUBIC, expand=True)
        image.alpha_composite(leaf, (x, y))
    image.save(ASSET_DIR / "community-soft-decoration.png")


if __name__ == "__main__":
    generate_hero()
    generate_empty_state()
    generate_texture()
    generate_soft_decor()
    print(f"Generated assets in {ASSET_DIR}")

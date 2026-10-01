from pathlib import Path
from urllib.request import Request, urlopen
import xml.etree.ElementTree as ET

from PIL import Image, ImageDraw, ImageFont

XML_URL = "https://ladderslasher.d2jsp.org/xmlChar.php?i=565457"
OUTPUT_WIDTH = 400
OUTPUT_HEIGHT = 150
MAX_FILE_SIZE = 70 * 1024

ROOT = Path(__file__).resolve().parent
BACKGROUND_FILE = ROOT / "assets" / "signature_background.png"
OUTPUT_FILE = ROOT / "signature.png"


def fetch_xml():
    request = Request(XML_URL, headers={"User-Agent": "Xeor-LadderSlasher-Signature/1.0"})
    with urlopen(request, timeout=20) as response:
        return response.read()


def parse_proficiencies(raw):
    result = {}
    if not raw:
        return result
    for entry in raw.strip().split(";"):
        if not entry:
            continue
        parts = [part.strip() for part in entry.split(",")]
        try:
            prof_id = int(parts[0])
            rank = int(parts[1])
            progress = int(parts[2]) if len(parts) >= 3 else 0
            result[prof_id] = {"rank": rank, "progress": progress}
        except (ValueError, IndexError):
            continue
    return result


def get_prof(data, prof_id):
    return data.get(prof_id, {"rank": 0, "progress": 0})


def requirement_for_next_rank(rank):
    return (rank + 1) * 1000


def percentage_to_next_rank(rank, progress):
    required = requirement_for_next_rank(rank)
    if required <= 0:
        return 0.0
    return max(0.0, min((progress / required) * 100, 100.0))


def get_font(size):
    possible_fonts = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf",
    ]
    for font_path in possible_fonts:
        if Path(font_path).exists():
            return ImageFont.truetype(font_path, size=size)
    return ImageFont.load_default()


def draw_centered_text(draw, center_x, center_y, text, font, fill,
                       stroke_width=0, stroke_fill=(0, 0, 0, 255)):
    bbox = draw.textbbox((0, 0), text, font=font, stroke_width=stroke_width)
    width = bbox[2] - bbox[0]
    height = bbox[3] - bbox[1]
    x = center_x - width / 2 - bbox[0]
    y = center_y - height / 2 - bbox[1]
    draw.text((x, y), text, font=font, fill=fill,
              stroke_width=stroke_width, stroke_fill=stroke_fill)


def save_optimized(image):
    final_image = image.convert("RGB")
    for colors in [256, 192, 160, 128, 96, 64, 48, 32]:
        optimized = final_image.quantize(
            colors=colors,
            method=Image.Quantize.MEDIANCUT,
            dither=Image.Dither.FLOYDSTEINBERG,
        )
        optimized.save(OUTPUT_FILE, "PNG", optimize=True, compress_level=9)
        file_size = OUTPUT_FILE.stat().st_size
        print(f"{colors} colors: {file_size / 1024:.1f} KB")
        if file_size <= MAX_FILE_SIZE:
            print(f"Signature saved: {file_size / 1024:.1f} KB")
            return
    raise RuntimeError("Could not reduce signature below 70 KB.")


def main():
    xml = ET.fromstring(fetch_xml())
    weapon_profs = parse_proficiencies(xml.findtext("wprof", ""))
    skill_profs = parse_proficiencies(xml.findtext("sprof", ""))

    # Sword, Axe, Dagger, Glyphing, Transmuting
    proficiencies = [
        get_prof(weapon_profs, 0),
        get_prof(weapon_profs, 2),
        get_prof(weapon_profs, 3),
        get_prof(skill_profs, 0),
        get_prof(skill_profs, 3),
    ]

    image = Image.open(BACKGROUND_FILE).convert("RGBA")
    # Background is already 8:3, so this preserves its layout at 400x150.
    image = image.resize((OUTPUT_WIDTH, OUTPUT_HEIGHT), Image.Resampling.LANCZOS)
    draw = ImageDraw.Draw(image)

    rank_font = get_font(10)
    percent_font = get_font(7)

    # Centers of the five stat columns at 400x150.
    proficiency_centers = [112, 172, 232, 293, 354]
    rank_center_y = 122
    percent_center_y = 134

    for center_x, proficiency in zip(proficiency_centers, proficiencies):
        rank = proficiency["rank"]
        progress = proficiency["progress"]
        percentage = percentage_to_next_rank(rank, progress)

        draw_centered_text(
            draw, center_x, rank_center_y, str(rank), rank_font,
            fill=(255, 215, 0, 255), stroke_width=1,
            stroke_fill=(0, 0, 0, 255),
        )
        draw_centered_text(
            draw, center_x, percent_center_y, f"{percentage:.1f}%", percent_font,
            fill=(255, 255, 255, 255), stroke_width=1,
            stroke_fill=(0, 0, 0, 255),
        )

    save_optimized(image)


if __name__ == "__main__":
    main()

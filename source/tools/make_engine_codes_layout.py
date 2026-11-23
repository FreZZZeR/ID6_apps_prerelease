"""Lay out fault codes in two full-width, two-line cards per page."""
import argparse
from io import BytesIO
from pathlib import Path
import xml.etree.ElementTree as ET
from zipfile import ZIP_DEFLATED, ZipFile
from content_layout import WIDTH, HEIGHT, flow_widths

ROOT = Path(__file__).resolve().parents[1] / "native"
XML = ROOT / "manifests/EngineCodes.xml"
BACKGROUND = 56700
PAGE_SIZE = 2


def place(node, x, y, width, height):
    props = ET.SubElement(node, "properties")
    for identifier, value in ((20, x), (21, y), (9, width), (10, height)):
        ET.SubElement(props, "property", id=str(identifier), value=str(value))


def update_xml(path=XML):
    tree = ET.parse(path)
    page = tree.find("pluginApp/hmiStates/hmiState[@id='101']")
    content = page.find("components")
    content.clear()
    image = ET.SubElement(content, "image", id="328", model="95")
    place(image, 0, 0, WIDTH, HEIGHT)
    for identifier, value in ((2, "false"), (3, "true")):
        ET.SubElement(image.find("properties"), "property", id=str(identifier), value=value)
    place(ET.SubElement(content, "label", id="320", model="80"), 16, 0, WIDTH-32, 54)
    for row in range(PAGE_SIZE):
        top = 68 + row*140
        place(ET.SubElement(content, "label", id=str(321+row), model=str(81+row)),
              16, top, WIDTH-32, 52)
        place(ET.SubElement(content, "label", id=str(330+row), model=str(91+row)),
              16, top+54, WIDTH-32, 52)
    place(ET.SubElement(content, "button", id="310", action="23", text="Read engine codes"),
          16, 352, WIDTH-32, 60)
    flow_widths(tree.find("pluginApp"))
    ET.indent(tree, space="  ")
    tree.write(path, encoding="utf-8", xml_declaration=True)


def background():
    from PIL import Image, ImageDraw
    image = Image.new("RGBA", (WIDTH, HEIGHT))
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle((0, 0, WIDTH-1, 53), radius=8, fill="#202d3c")
    for row in range(PAGE_SIZE):
        top = 62 + row*140
        draw.rounded_rectangle((0, top, WIDTH-1, top+127), radius=8, fill="#171e28")
    return image


def update_images(source, dest):
    stream = BytesIO()
    background().save(stream, format="PNG", optimize=True)
    name = f"{BACKGROUND}.png"
    with ZipFile(source) as original, ZipFile(dest, "w", ZIP_DEFLATED) as out:
        for entry in original.infolist():
            out.writestr(entry, stream.getvalue() if entry.filename == name else original.read(entry))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--images", type=Path)
    parser.add_argument("--images-out", type=Path)
    args = parser.parse_args()
    if bool(args.images) != bool(args.images_out) or (args.images and args.images==args.images_out):
        parser.error("provide distinct --images and --images-out paths")
    update_xml()
    if args.images:
        update_images(args.images, args.images_out)

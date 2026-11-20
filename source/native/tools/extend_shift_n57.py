"""Append lower shift thresholds while preserving the shipped smooth ShiftDeck layout/assets."""
import argparse
from io import BytesIO
from pathlib import Path
import xml.etree.ElementTree as ET
from zipfile import ZipFile, ZIP_DEFLATED

ROOT = Path(__file__).resolve().parents[1]


def update_xml(path):
    tree = ET.parse(path)
    app = tree.find("pluginApp")
    actions = app.find("actions")
    choices = app.find("hmiStates/hmiState[@id='101']/components")
    for index, rpm in enumerate((3500, 4000, 4500), 5):
        action = str(48 + index - 5)
        if actions.find(f"raAction[@id='{action}']") is None:
            ET.SubElement(actions, "raAction", id=action)
        if choices.find(f"button[@action='{action}']") is None:
            ET.SubElement(choices, "button", id=str(301 + index), action=action, text=f"{rpm:,} RPM")
    ET.indent(tree, space="  ")
    tree.write(path, encoding="utf-8", xml_declaration=True)


def update_images(source, dest):
    import shift_art as art
    added = {}
    for identifier, bitmap in art.bitmaps():
        if identifier in (*range(55885, 55888), *range(55925, 55928)):
            image = BytesIO()
            bitmap.save(image, format="PNG", optimize=True)
            added[f"{identifier}.png"] = image.getvalue()
    with ZipFile(source) as original, ZipFile(dest, "w", ZIP_DEFLATED) as out:
        for entry in original.infolist():
            if entry.filename not in added:
                out.writestr(entry, original.read(entry))
        for name, data in added.items():
            out.writestr(name, data)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--images", type=Path)
    parser.add_argument("--images-out", type=Path)
    args = parser.parse_args()
    if bool(args.images) != bool(args.images_out) or (args.images and args.images==args.images_out):
        parser.error("provide distinct --images and --images-out paths")
    update_xml(ROOT / "plugin/ShiftDeck.xml")
    if args.images:
        import shift_art as art
        update_images(args.images, args.images_out)
        (ROOT / "src/shift_assets.h").write_text(art.constants_text())

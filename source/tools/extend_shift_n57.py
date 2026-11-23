"""Append N57 thresholds/scale while preserving shipped smooth and gasoline assets."""
import argparse
from io import BytesIO
from pathlib import Path
import xml.etree.ElementTree as ET
from zipfile import ZipFile, ZipInfo, ZIP_DEFLATED
from content_layout import WIDTH, flow_widths

ROOT = Path(__file__).resolve().parents[1] / "native"


def update_xml(path):
    import shift_art as art
    tree = ET.parse(path)
    app = tree.find("pluginApp")
    actions = app.find("actions")
    models, states = app.find("models"), app.find("hmiStates")
    main = states.find("hmiState[@id='100']")
    content = main.find("components")
    choices = app.find("hmiStates/hmiState[@id='101']/components")
    for index, rpm in enumerate((3500, 4000, 4500), 5):
        action = str(48 + index - 5)
        if actions.find(f"raAction[@id='{action}']") is None:
            ET.SubElement(actions, "raAction", id=action)
        if choices.find(f"button[@action='{action}']") is None:
            ET.SubElement(choices, "button", id=str(301 + index), action=action, text=f"{rpm:,} RPM")
    if actions.find("hmiAction[@id='120']") is None:
        ET.SubElement(actions, "hmiAction", id="120", target="102")
    for action in range(121, 126):
        if actions.find(f"raAction[@id='{action}']") is None:
            ET.SubElement(actions, "raAction", id=str(action))
    for identifier in (80, 83):
        if models.find(f"raDataModel[@id='{identifier}']") is None:
            ET.SubElement(models, "raDataModel", id=str(identifier), modelType="Richtext")
    for identifier, image in ((81, art.N57_LOWER_MARKER), (82, art.N57_UPPER_MARKER),
                              (84, art.N57_WINDOW_LEGEND)):
        if models.find(f"imageIdModel[@id='{identifier}']") is None:
            ET.SubElement(models, "imageIdModel", id=str(identifier), imageId=str(image))

    # Remove the legacy inset before converting to the common HMI design grid.
    bar_x = content.find("image[@id='200']/properties/property[@id='20']")
    if bar_x is not None and bar_x.get("value") == "52":
        for component in content:
            x = component.find("properties/property[@id='20']")
            if x is not None:
                x.set("value", str(int(x.get("value")) - 52))
    # Keep SHIFT below the RPM legend and above the bar.
    caption_y = content.find("image[@id='203']/properties/property[@id='21']")
    if caption_y is not None:
        caption_y.set("value", "205")

    def position(node, x, y, width, height):
        props = ET.SubElement(node, "properties")
        for key, value in ((20, x), (21, y), (9, width), (10, height), (2, "false"), (3, "false")):
            ET.SubElement(props, "property", id=str(key), value=str(value))

    options = main.find("optionComponents")
    if options.find("button[@id='412']") is None:
        option = ET.SubElement(options, "button", id="412", action="120", text="N57 shift window")
        ET.SubElement(ET.SubElement(option, "properties"), "property", id="3", value="false")
    for component, model, x in ((250, 81, art.n57_axis_x(4600) - 3), (251, 82, art.n57_axis_x(4800) - 3)):
        if content.find(f"image[@id='{component}']") is None:
            position(ET.SubElement(content, "image", id=str(component), model=str(model)), x, 239, 64, 9)
    if content.find("label[@id='252']") is None:
        position(ET.SubElement(content, "label", id="252", model="80"), 800, 110, 300, 60)
    if content.find("image[@id='253']") is None:
        position(ET.SubElement(content, "image", id="253", model="84"), 800, 75, 300, 135)
    if states.find("hmiState[@id='102']") is None:
        settings = ET.SubElement(states, "hmiState", id="102", parentId="100", text="N57 shift window")
        components = ET.SubElement(settings, "components")
        ET.SubElement(components, "label", id="450", model="83")
        for offset, caption in enumerate(("Lower -100 RPM", "Lower +100 RPM", "Upper -100 RPM",
                                          "Upper +100 RPM", "Reset: 4600-4800 RPM")):
            ET.SubElement(components, "button", id=str(451 + offset), action=str(121 + offset), text=caption)
    width = content.find("image[@id='200']/properties/property[@id='9']")
    if width is not None and int(width.get("value")) != WIDTH:
        previous_width = int(width.get("value"))
        for component in content:
            properties = {p.get("id"): p for p in component.findall("properties/property")}
            if "20" not in properties:
                continue
            identifier = int(component.get("id"))
            if int(properties["9"].get("value")) == previous_width:
                properties["9"].set("value", str(WIDTH))
            elif identifier in (202, 252, 253):
                properties["20"].set("value", str(int(properties["20"].get("value")) + WIDTH - previous_width))
            elif identifier in (203, 206, 207, 208, 209, 211):
                properties["20"].set("value", str(int(properties["20"].get("value")) + (WIDTH - previous_width) // 2))
    for component, rpm in ((250, 4600), (251, 4800)):
        content.find(f"image[@id='{component}']/properties/property[@id='20']").set("value", str(art.n57_axis_x(rpm) - 3))
    flow_widths(app)
    ET.indent(tree, space="  ")
    tree.write(path, encoding="utf-8", xml_declaration=True)


def update_images(source, dest):
    import shift_art as art
    added = {}
    for identifier, bitmap in art.bitmaps():
        if identifier in (*range(55885, 55888), *range(55925, 55928)) or identifier>=art.N57_BAR_BASE:
            image = BytesIO()
            bitmap.save(image, format="PNG", optimize=True)
            added[f"{identifier}.png"] = image.getvalue()
    with ZipFile(source) as original, ZipFile(dest, "w", ZIP_DEFLATED) as out:
        # The gasoline bar contains an early amber tail. Recolour both active
        # fills privately for N57, retaining inactive pixels and all gas assets.
        from PIL import Image, ImageChops
        for step in range(129):
            name = f"{56400 + step}.png"
            if name in original.namelist():
                image = Image.open(BytesIO(original.read(name))).convert("RGBA")
                mask = Image.new("L", image.size)
                for color in ("#409af6", "#ffbf52"):
                    difference = ImageChops.difference(image.convert("RGB"), Image.new("RGB", image.size, color))
                    r, g, b = difference.split()
                    matches = ImageChops.lighter(ImageChops.lighter(r, g), b).point(lambda value: 0 if value else 255)
                    mask = ImageChops.lighter(mask, matches)
                alpha = image.getchannel("A")
                for base, color in ((art.N57_SWEEP_NORMAL, "#409af6"), (art.N57_SWEEP_WARNING, art.YELLOW)):
                    tinted = image.copy()
                    tinted.paste(color, mask=mask)
                    tinted.putalpha(alpha)
                    data = BytesIO()
                    tinted.save(data, format="PNG", optimize=True)
                    added[f"{base + step}.png"] = data.getvalue()
        if "55879.png" in original.namelist():
            strip = Image.open(BytesIO(original.read("55879.png"))).convert("RGBA")
            warning = Image.new("RGBA", strip.size, art.YELLOW)
            warning.putalpha(strip.getchannel("A"))
            data = BytesIO()
            warning.save(data, format="PNG", optimize=True)
            added[f"{art.N57_LIGHTS_WARNING}.png"] = data.getvalue()
        # Sample the shipped 128-step artwork for the N57 legacy 32-step path.
        # Never replace the existing gasoline/smooth resource IDs.
        for base, smooth in ((art.N57_BAR_WARN, 56529),):
            for step in range(33):
                name=f"{smooth+step*4}.png"
                if name in original.namelist():
                    added[f"{base+step}.png"]=original.read(name)
        for step in range(33):
            added[f"{art.N57_BAR_BASE + step}.png"] = added[f"{art.N57_SWEEP_NORMAL + step * 4}.png"]
            added[f"{art.N57_BAR_WARNING + step}.png"] = added[f"{art.N57_SWEEP_WARNING + step * 4}.png"]
        # Widen private N57 sweep masks to match the logical axis. Keep the
        # shipped gasoline resources byte-for-byte; generated labels keep their font size.
        for name in list(added):
            bitmap = Image.open(BytesIO(added[name])).convert("RGBA")
            if bitmap.width == 1104:
                output = BytesIO()
                bitmap.resize((WIDTH, bitmap.height), Image.Resampling.LANCZOS).save(output, format="PNG", optimize=True)
                added[name] = output.getvalue()
        for entry in original.infolist():
            if entry.filename not in added:
                out.writestr(entry, original.read(entry))
        for name, data in added.items():
            if name in original.namelist():
                info=original.getinfo(name)
            else:
                info=ZipInfo(name,date_time=(2026,1,1,0,0,0))
                info.compress_type=ZIP_DEFLATED
            out.writestr(info, data)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--images", type=Path)
    parser.add_argument("--images-out", type=Path)
    args = parser.parse_args()
    if bool(args.images) != bool(args.images_out) or (args.images and args.images==args.images_out):
        parser.error("provide distinct --images and --images-out paths")
    update_xml(ROOT / "manifests/ShiftDeck.xml")
    if args.images:
        import shift_art as art
        update_images(args.images, args.images_out)
        (ROOT / "src/plugins/shift_assets.h").write_text(art.constants_text())

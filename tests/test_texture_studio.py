"""Round-trip a real Forge GLB through the Texture Studio in Chromium."""
import io
import json
import os
import struct
from pathlib import Path

from PIL import Image, ImageChops
from playwright.sync_api import sync_playwright

root = Path(__file__).resolve().parents[1]
model = root / "forge/mesh-results/forge-3d-smoke-e2d419f/model.glb"
app = os.environ.get("APP_URL") or (root / "index.html").as_uri()
local_three = os.environ.get("THREE_TEST_ROOT")


def png(color):
    data = io.BytesIO()
    Image.new("RGB", (64, 64), color).save(data, "PNG")
    return {"name": "channel.png", "mimeType": "image/png", "buffer": data.getvalue()}


with sync_playwright() as p:
    browser = p.chromium.launch(
        executable_path=os.environ.get("CHROMIUM_PATH"),
        args=["--enable-unsafe-swiftshader", "--use-angle=swiftshader"],
    )
    page = browser.new_page(viewport={"width": 390, "height": 820}, has_touch=True)
    if local_three:
        prefix = "https://cdn.jsdelivr.net/npm/three@0.180.0/"
        page.route(prefix + "**", lambda route: route.fulfill(
            path=Path(local_three) / route.request.url.removeprefix(prefix),
            content_type="text/javascript", headers={"Access-Control-Allow-Origin": "*"},
        ))
    errors = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    page.goto(app)
    page.locator("#tAI").click()
    page.get_by_role("button", name="3D Texture Studio").click()
    page.get_by_text("Open a GLB to start texturing.").wait_for()
    page.get_by_label("Open GLB").set_input_files(model)
    page.get_by_text("model · 1 material", exact=True).wait_for()
    page.get_by_label("Preview lighting").select_option("warm")
    page.get_by_role("button", name="Bake relief normal").click()
    page.get_by_text("Baked a normal map from base-color brightness.").wait_for()
    page.get_by_label("Import texture").set_input_files(png((180, 90, 45)))
    page.get_by_text("Applied Base color").wait_for()
    page.get_by_label("Texture map").select_option("roughnessMap")
    page.get_by_label("Import texture").set_input_files(png((100, 100, 100)))
    page.get_by_text("Applied Roughness").wait_for()
    page.get_by_label("Texture map").select_option("normalMap")
    page.get_by_label("Import texture").set_input_files(png((128, 128, 255)))
    page.get_by_text("Applied Normal").wait_for()
    page.get_by_label("Interaction").select_option("paint")
    preview = page.get_by_label("Interactive 3D model preview")
    box = preview.bounding_box()
    painted = False
    for y in (0.5, 0.35, 0.65):
        preview.click(position={"x": box["width"] / 2, "y": box["height"] * y})
        if page.get_by_role("button", name="Undo stroke").is_enabled():
            painted = True
            break
    assert painted, "A visible surface should accept a brush stroke"

    def download(label):
        with page.expect_download() as download_event:
            page.get_by_role("button", name=label, exact=True).click()
        return download_event.value.path().read_bytes()

    with Image.open(io.BytesIO(download("Save base color PNG"))) as texture:
        assert len(texture.getcolors()) > 1
    page.get_by_role("button", name="Undo stroke").click()
    with Image.open(io.BytesIO(download("Save base color PNG"))) as texture:
        assert texture.convert("RGB").getcolors() == [(4096, (180, 90, 45))]
    with Image.open(io.BytesIO(download("Save preview PNG"))) as preview_image:
        rgb = preview_image.convert("RGB")
        assert ImageChops.difference(rgb, Image.new("RGB", rgb.size, rgb.getpixel((0, 0)))).getbbox()
    exported = download("Export textured GLB")
    assert exported[:4] == b"glTF"
    length, kind = struct.unpack_from("<II", exported, 12)
    assert kind == 0x4E4F534A
    gltf = json.loads(exported[20:20 + length])
    material = gltf["materials"][0]
    assert "baseColorTexture" in material["pbrMetallicRoughness"]
    assert "metallicRoughnessTexture" in material["pbrMetallicRoughness"]
    assert "normalTexture" in material
    if os.environ.get("TEXTURE_TEST_EXPORT"):
        Path(os.environ["TEXTURE_TEST_EXPORT"]).write_bytes(exported)
    page.get_by_label("Open GLB").set_input_files(
        {"name": "round-trip.glb", "mimeType": "model/gltf-binary", "buffer": exported}
    )
    page.get_by_text("round-trip · 1 material", exact=True).wait_for()
    page.locator("#shClose").click()
    assert not errors, errors
    print("PASS Forge GLB import, PBR maps, paint and undo, rendered PNG, GLB round-trip")

"""Build and queue a public 3D job through the existing Forge connector."""
import base64
import io
import os
from pathlib import Path

from PIL import Image
from playwright.sync_api import sync_playwright

app = os.environ.get("APP_URL") or (Path(__file__).resolve().parents[1] / "index.html").as_uri()
with sync_playwright() as p:
    browser = getattr(p, os.environ.get('BROWSER', 'chromium')).launch()
    page = browser.new_page(viewport={"width": 390, "height": 820}, has_touch=True)
    page.add_init_script("""
      window.writes = [];
      window.claude = {use: async name => name === 'mcp' ? {
        listTools: async () => ({}),
        callTool: async (server, tool, args) => {
          if (tool === 'create_or_update_file') { writes.push(args); return {}; }
          if (tool === 'get_file_contents') return {content: [{type:'text',text:'{"status":"done"}'}]};
        }
      } : null};
    """)
    page.goto(app)
    page.wait_for_function("window.Foxboard")
    result = page.evaluate("""async () => {
      Foxboard.newDoc({w:96,h:96});
      const canvas = document.createElement('canvas');
      canvas.width = canvas.height = 96;
      canvas.getContext('2d').fillRect(22, 4, 52, 88);
      const id = Foxboard.add('image', {src:canvas.toDataURL(),x:0,y:0,w:96,h:96});
      Foxboard.crop(id, {l:0.5});
      await new Promise(r => setTimeout(r, 250));
      const opts = {mode:'3d',jid:'draft-test',id};
      const local = Foxboard.forgeFiles(opts);
      await Foxboard.forge(opts);
      const status = await Foxboard.meshStatus('draft-test');
      return {id,local,writes,status};
    }""")
    assert [entry["path"] for entry in result["writes"]] == [
        "forge/jobs/3d/draft-test.init.b64", "forge/jobs/3d/draft-test.json"]
    assert result["local"]["local"]["mode"] == "3d"
    encoded = result["local"]["files"]["forge/jobs/3d/draft-test.init.b64"].split(":", 1)[1]
    with Image.open(io.BytesIO(base64.b64decode(encoded))) as image:
        assert image.size == (48, 96)
    assert result["status"]["meshReady"] is True
    assert result["status"]["state"] == "done"
    page.evaluate("(id) => { Foxboard.select(id); window.__fb.openProps(); }", result["id"])
    page.get_by_role("button", name="Generate 3D draft").click(timeout=5000)
    assert "will be public" in page.locator("#shBody").inner_text()
    assert page.evaluate("writes.length") == 2
    page.get_by_role("button", name="Publish reference and queue").click()
    page.get_by_text("Your Forge results").wait_for()
    assert page.evaluate("writes.length") == 4
    model_url = "https://raw.githubusercontent.com/duffpowell-commits/Foxboard/main/forge/mesh-results/draft-test/model.glb"
    payload = b"glTF\x02\0\0\0\x0c\0\0\0"
    page.route(model_url, lambda route: route.fulfill(
        body=payload, content_type="model/gltf-binary", headers={"Access-Control-Allow-Origin": "*"}))
    with page.expect_download() as event:
        page.get_by_role("button", name="Download GLB").click()
    assert event.value.suggested_filename == "foxboard-draft-test.glb"
    assert event.value.path().read_bytes() == payload
    print("PASS 3D job packages the image, confirms public upload, and shows its GLB")

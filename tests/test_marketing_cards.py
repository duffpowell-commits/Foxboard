"""Browser smoke test for Foxboard marketing card generator.

Run: python tests/test_marketing_cards.py
Requires Playwright Chromium: pip install playwright && python -m playwright install chromium
"""
import asyncio
import pathlib
from playwright.async_api import async_playwright

PAGE = (pathlib.Path(__file__).resolve().parent.parent / "marketing" / "studio_cards.html").as_uri()
EXPECTED = {"short": (1080, 1920), "end": (1920, 1080), "thumb": (1280, 720)}

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(viewport={"width": 390, "height": 844}, accept_downloads=True)
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        await page.goto(PAGE)
        # Why (Nov 23 review): a loaded logo used to throw "box is not defined" and stop drawing.
        logo = pathlib.Path(__file__).resolve().parent.parent / "brand/knife-and-needle/vector/knife-and-needle-v3.png"
        await page.locator("#logo").set_input_files(str(logo))
        await page.wait_for_timeout(300)
        for layout, size in EXPECTED.items():
            await page.locator("#layout").select_option(layout)
            dimensions = await page.locator("#card").evaluate("(c) => [c.width, c.height]")
            assert tuple(dimensions) == size, (layout, dimensions)
            await page.locator("#game").fill("WILDMADE")
            async with page.expect_download() as event:
                await page.locator("#export").click()
            download = await event.value
            assert download.suggested_filename == f"3-eyed-fox-{layout}.png"
            path = await download.path()
            data = pathlib.Path(path).read_bytes()
            assert data[:8] == b"\x89PNG\r\n\x1a\n", "PNG signature invalid"
            width = int.from_bytes(data[16:20], "big")
            height = int.from_bytes(data[20:24], "big")
            assert (width, height) == size, (layout, width, height)
        assert not errors, errors
        await browser.close()
        print("MARKETING CARDS PASS")

if __name__ == "__main__":
    asyncio.run(main())

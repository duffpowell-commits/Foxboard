# tools/quase: art pipeline scripts

These scripts stand alone, apart from the Foxboard app. Copied from the Chaos repo, with every path now relative to `$ART_ROOT`
(the current directory if it is unset). Needs Python 3 with Pillow and numpy. The OCR check also needs Tesseract and pytesseract.

- `art_qa.py`: checks size, mode, edge alpha and palette (% of red/maroon/blue) per glob group, and runs an OCR check for
  stray readable text. Config: `$ART_QA_CONFIG` or `$ART_ROOT/art_qa.json`. `art_qa.example.json` is the Chaos config.
  `ART_ROOT=~/chaos python tools/quase/art_qa.py --config ~/chaos/tools/art_qa.json`
- `test_art_qa.py`: self-test (7 cases). `python tools/quase/test_art_qa.py` (`ART_QA_REQUIRE_OCR=1` fails if Tesseract is missing).
- `letter.py`: letters artwork from the JSON spec in a type sheet (`$ART_TYPE_SHEET`, default
  `$ART_ROOT/docs/art/type-sheet.md`; example: `art/quase/chaos/style/type-sheet.md`). Font paths in the spec are relative to `$ART_ROOT`.
- `joint_map.py`: writes `joints_<view>.json` (head, neck, shoulders, elbows, wrists, hips, knees, ankles) for
  `$ART_SPRITE_DIR/<name>/<name>_<front|back>.png` (default `assets/characters`). `--overlay out.png` writes a check sheet.
- `fonts/`: Anton Regular, SIL OFL 1.1 (`OFL.txt`).

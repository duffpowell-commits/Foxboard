"""Forge 3D: stage timings are read from TripoSR's log lines (no browser needed)."""
import sys
import types
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "forge"))
sys.modules.setdefault("trimesh", types.ModuleType("trimesh"))  # only the runner has it
from mesh_worker import parse_triposr_timings  # noqa: E402

# Format of TripoSR's utils.Timer with run.py's basicConfig: "%(asctime)s - %(levelname)s - %(message)s".
log = """2026-11-23 16:50:01,100 - INFO - Initializing model ...
2026-11-23 16:50:09,200 - INFO - Initializing model finished in 8100.25ms.
2026-11-23 16:50:09,300 - INFO - Processing images ...
2026-11-23 16:50:11,000 - INFO - Processing images finished in 1700.00ms.
2026-11-23 16:50:11,000 - INFO - Running image 1/1 ...
2026-11-23 16:50:11,000 - INFO - Running model ...
2026-11-23 16:51:40,000 - INFO - Running model finished in 89000.50ms.
2026-11-23 16:51:40,000 - INFO - Extracting mesh finished in 12000.00ms.
2026-11-23 16:52:40,000 - INFO - Baking texture finished in 60000.00ms.
2026-11-23 16:52:41,000 - INFO - Exporting mesh and texture finished in 900.00ms.
2026-11-23 16:52:41,000 - INFO - Something else finished in 5.00ms.
"""
got = parse_triposr_timings(log)
want = {"model_load": 8.1, "image_processing": 1.7, "inference": 89.001, "mesh_extraction": 12.0,
        "texture_bake": 60.0, "intermediate_export": 0.9}
assert got == want, f"FAIL timings {got}"
assert parse_triposr_timings("") == {}, "FAIL empty log"
print("mesh timings ok", got)

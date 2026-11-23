"""Turn one public Forge image into a textured TripoSR draft."""
import argparse
import base64
import io
import json
import os
import re
import subprocess
import sys
import tempfile
import time
from pathlib import Path

from PIL import Image
import trimesh

ROOT = Path(__file__).resolve().parents[1]


def read_image(path):
    if path.stat().st_size > 1_000_000:
        raise ValueError("Reference exceeds the upload limit")
    kind, data = path.read_text().split(":", 1)
    if kind not in {"png", "jpg"}:
        raise ValueError("Reference must be PNG or JPEG")
    with Image.open(io.BytesIO(base64.b64decode(data, validate=True))) as image:
        if image.format not in {"PNG", "JPEG"} or max(image.size) > 768:
            raise ValueError("Unsupported reference dimensions or format")
        return image.convert("RGBA")


def parse_triposr_timings(log):
    """Read the stage timings emitted by the pinned TripoSR runner."""
    stages = {
        "Initializing model": "model_load",
        "Processing images": "image_processing",
        "Running model": "inference",
        "Extracting mesh": "mesh_extraction",
        "Baking texture": "texture_bake",
        "Exporting mesh and texture": "intermediate_export",
    }
    return {
        stages[name]: round(float(milliseconds) / 1000, 3)
        for name, milliseconds in re.findall(r" - INFO - ([^\n]+?) finished in ([0-9.]+)ms\.", log)
        if name in stages
    }


def render(job, dest):
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,63}", job.stem):
        raise ValueError("Invalid job ID")
    if json.loads(job.read_text()).get("mode") != "3d":
        raise ValueError("Unsupported mesh job")
    root = Path(os.environ["TRIPOSR_ROOT"]).resolve()
    weights = Path(os.environ["TRIPOSR_WEIGHTS"]).resolve()
    with tempfile.TemporaryDirectory() as temp:
        temp = Path(temp)
        source = temp / "source.png"
        started = time.perf_counter()
        read_image(job.with_suffix(".init.b64")).save(source)
        timings = {"reference_decode": round(time.perf_counter() - started, 3)}
        process = subprocess.run(
            [sys.executable, str(root / "run.py"), str(source), "--device", "cpu",
             "--pretrained-model-name-or-path", str(weights), "--mc-resolution", "144",
             "--bake-texture", "--texture-resolution", "1024", "--output-dir", str(temp)],
            cwd=root, stderr=subprocess.PIPE, text=True, timeout=480,
        )
        print(process.stderr, file=sys.stderr, end="", flush=True)
        process.check_returncode()
        timings.update(parse_triposr_timings(process.stderr))
        started = time.perf_counter()
        output = temp / "0"
        mesh = trimesh.load_mesh(output / "mesh.obj", process=False)
        if len(mesh.faces) == 0 or mesh.visual.uv is None:
            raise ValueError("Reconstruction produced no textured surface")
        mesh.fix_normals()
        with Image.open(output / "texture.png") as texture:
            mesh.visual.material = trimesh.visual.material.PBRMaterial(
                baseColorTexture=texture.convert("RGB"), roughnessFactor=0.8,
                metallicFactor=0.0, doubleSided=True,
            )
        # TripoSR is Z-up. glTF expects Y-up.
        mesh.apply_transform(trimesh.transformations.rotation_matrix(-1.5707963267948966, [1, 0, 0]))
        mesh.export(dest / "model.glb")
        timings["glb_export"] = round(time.perf_counter() - started, 3)
        return timings


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--job", help="Process just this job ID")
    args = parser.parse_args()
    pending = args.root / "forge/jobs/3d"
    if args.job and not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,63}", args.job):
        parser.error("Invalid job ID")
    jobs = [pending / f"{args.job}.json"] if args.job else sorted(pending.glob("*.json"))
    failed = False
    for job in jobs:
        if not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,63}", job.stem):
            print(f"Ignoring invalid mesh job filename: {job.name}", file=sys.stderr)
            continue
        dest = args.root / "forge/mesh-results" / job.stem
        status = dest / "done.json"
        if status.exists():
            continue
        dest.mkdir(parents=True, exist_ok=True)
        started = time.perf_counter()
        timings = {}
        try:
            timings = render(job, dest)
            result = "done"
        except Exception as exc:
            print(f"{job.name}: {exc}", file=sys.stderr)
            (dest / "model.glb").unlink(missing_ok=True)
            result = "failed"
            failed = True
        timings["job_total"] = round(time.perf_counter() - started, 3)
        setup_seconds = os.environ.get("FORGE_SETUP_SECONDS")
        if setup_seconds is not None:
            timings["runner_setup"] = int(setup_seconds)
        print(f"{job.stem} timing (seconds): {json.dumps(timings)}", flush=True)
        status.write_text(json.dumps({"status": result, "timings_seconds": timings}) + "\n")
    return int(failed)


if __name__ == "__main__":
    sys.exit(main())

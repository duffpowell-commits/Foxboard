"""Download FLUX.1-schnell (Apache-2.0) pieces for stable-diffusion.cpp; prints what it picked."""
import os, sys
from huggingface_hub import list_repo_files, hf_hub_download
os.makedirs("models", exist_ok=True)
def pick(repo, wants):
    try: files = list_repo_files(repo)
    except Exception as e: print("LIST FAIL", repo, e); return None
    print("FILES", repo, files)
    for w in wants:
        for f in files:
            if all(t in f.lower() for t in w): return f
    return None
def get(repo, f):
    print("GET", repo, f, flush=True)
    return hf_hub_download(repo, f, local_dir="models")
import json, pathlib, urllib.request
out = {}
mode = "new"
if len(sys.argv) > 1:
    try: mode = json.loads(pathlib.Path(f"forge/jobs/{sys.argv[1]}.json").read_text()).get("mode", "new")
    except Exception: pass
if mode == "upscale":
    dst = "models/RealESRGAN_x4plus_anime_6B.pth"
    urllib.request.urlretrieve("https://github.com/xinntao/Real-ESRGAN/releases/download/v0.2.2.4/RealESRGAN_x4plus_anime_6B.pth", dst)
    with open("models.env", "w") as fh: fh.write(f"ESRGAN={dst}\n")
    print({"ESRGAN": dst}); sys.exit(0)
f = pick("leejet/FLUX.1-schnell-gguf", [("q4_k",), ("q4_0",), ("q5",)])
if not f: sys.exit("no flux gguf")
out["DIFF"] = get("leejet/FLUX.1-schnell-gguf", f)
out["CLIP"] = get("comfyanonymous/flux_text_encoders", "clip_l.safetensors")
t5g = pick("city96/t5-v1_1-xxl-encoder-gguf", [("q8_0",), ("q6_k",)])
if t5g: out["T5GGUF"] = get("city96/t5-v1_1-xxl-encoder-gguf", t5g)
if "T5GGUF" not in out: out["T5FP16"] = get("comfyanonymous/flux_text_encoders", "t5xxl_fp16.safetensors")
for repo in ["leejet/FLUX.1-schnell-gguf", "black-forest-labs/FLUX.1-schnell", "ffxvs/vae-flux"]:
    v = pick(repo, [("ae.safetensors",), ("ae.sft",), ("vae", "safetensors")])
    if v:
        try: out["VAE"] = get(repo, v); break
        except Exception as e: print("VAE FAIL", repo, e)
with open("models.env", "w") as fh:
    for k, v in out.items(): fh.write(f"{k}={v}\n")
print(out)

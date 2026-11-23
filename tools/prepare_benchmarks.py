"""Fetch unchanged Set5/Set14 x2 pairs from a pinned SelfExSR snapshot.

No image dependency is required. PNG header dimensions and Git blob hashes are
checked before files are copied into the benchmark layout.
"""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
import struct
import sys
import urllib.request

COMMIT = "8f6dd8c1d20cb7e8792a7177b4f6fd677633f598"
REPOSITORY = "jbhuang0604/SelfExSR"
BASE = f"https://raw.githubusercontent.com/{REPOSITORY}/{COMMIT}"
ROOT = Path(__file__).resolve().parents[1]


def request_bytes(url: str) -> bytes:
    for attempt in range(2):
        try:
            with urllib.request.urlopen(url, timeout=20) as response:
                return response.read()
        except (OSError, TimeoutError):
            if attempt:
                raise
            print(f"Retrying public download once: {url}", file=sys.stderr)
    raise RuntimeError("Unreachable")


def git_blob_sha(data: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


def png_size(data: bytes) -> tuple[int, int]:
    if data[:8] != b"\x89PNG\r\n\x1a\n" or data[12:16] != b"IHDR":
        raise ValueError("Expected an unchanged PNG image")
    return struct.unpack(">II", data[16:24])


def prepare(root: Path = ROOT, cache: Path = Path("D:/CodexTools/sr-data-downloads")) -> dict:
    """Download or verify a fixed set of 38 files; never overwrite bad cache."""
    cache.mkdir(parents=True, exist_ok=True)
    tree_path = cache / f"SelfExSR-{COMMIT}-tree.json"
    if not tree_path.exists():
        url = f"https://api.github.com/repos/{REPOSITORY}/git/trees/{COMMIT}?recursive=1"
        tree_path.write_bytes(request_bytes(url))
    tree = json.loads(tree_path.read_text(encoding="utf-8"))
    if tree.get("sha") != COMMIT or tree.get("truncated"):
        raise ValueError("Unverified or incomplete upstream Git tree")
    blobs = {entry["path"]: entry["sha"] for entry in tree["tree"] if entry["type"] == "blob"}
    jobs = []
    for dataset, count in (("Set5", 5), ("Set14", 14)):
        for index in range(1, count + 1):
            name = f"img_{index:03d}"
            for kind in ("HR", "LR"):
                source = f"data/{dataset}/image_SRF_2/{name}_SRF_2_{kind}.png"
                target = f"data/benchmark/{dataset}/HR/{name}.png" if kind == "HR" else f"data/benchmark/{dataset}/LR_bicubic/X2/{name}x2.png"
                jobs.append((dataset, name, kind, source, target, blobs[source]))

    def fetch(job):
        dataset, name, kind, source, target, expected_blob = job
        local_cache = cache / COMMIT / source
        if local_cache.exists():
            data = local_cache.read_bytes()
        else:
            data = request_bytes(f"{BASE}/{source}")
            if git_blob_sha(data) != expected_blob:
                raise ValueError(f"Git blob mismatch before caching: {source}")
            local_cache.parent.mkdir(parents=True, exist_ok=True)
            local_cache.write_bytes(data)
        if git_blob_sha(data) != expected_blob:
            raise ValueError(f"Cache integrity failure: {local_cache}")
        width, height = png_size(data)
        destination = root / target
        destination.parent.mkdir(parents=True, exist_ok=True)
        if destination.exists() and destination.read_bytes() != data:
            raise ValueError(f"Refusing to overwrite modified benchmark: {destination}")
        if not destination.exists():
            shutil.copyfile(local_cache, destination)
        return {"dataset": dataset, "image_id": name, "kind": kind,
                "source_url": f"{BASE}/{source}", "relative_path": target,
                "git_blob_sha1": expected_blob, "sha256": hashlib.sha256(data).hexdigest(),
                "bytes": len(data), "width": width, "height": height}

    with ThreadPoolExecutor(max_workers=6) as pool:
        files = list(pool.map(fetch, jobs))
    for dataset, count in (("Set5", 5), ("Set14", 14)):
        records = {(f["image_id"], f["kind"]): f for f in files if f["dataset"] == dataset}
        if len(records) != count * 2:
            raise ValueError(f"Wrong dataset size: {dataset}")
        for index in range(1, count + 1):
            name = f"img_{index:03d}"
            hr, lr = records[name, "HR"], records[name, "LR"]
            if (hr["width"], hr["height"]) != (lr["width"] * 2, lr["height"] * 2):
                raise ValueError(f"Incorrect x2 pairing: {dataset}/{name}")
    manifest = {"schema_version": 1, "prepared_at_utc": datetime.now(timezone.utc).isoformat(),
                "source_repository": f"https://github.com/{REPOSITORY}", "source_commit": COMMIT,
                "scale": 2, "preprocessing": "none; original PNG bytes copied unchanged",
                "dataset_pairs": {"Set5": 5, "Set14": 14}, "files": files}
    path = root / "artifacts/data_manifest.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return manifest


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--cache", type=Path, default=Path("D:/CodexTools/sr-data-downloads"))
    args = parser.parse_args()
    manifest = prepare(args.root.resolve(), args.cache.resolve())
    print(json.dumps({"pairs": manifest["dataset_pairs"], "files": len(manifest["files"]),
                      "bytes": sum(f["bytes"] for f in manifest["files"]),
                      "commit": COMMIT}, ensure_ascii=False))

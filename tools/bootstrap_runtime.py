"""Download pinned upstream archives without copying credentials or modifying global Python.

Run with the standard library; dependencies are installed separately into the documented venv.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import urllib.request
import zipfile

UPSTREAMS = {
    'EIMN': ('liux520/EIMN', '6a712bac203971c5002b55c2557b2d7367f1a77c'),
    'BasicSR': ('XPixelGroup/BasicSR', '8d56e3a045f9fb3e1d8872f92ee4a4f07f886b0a'),
}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--tools-dir', type=Path, default=Path('D:/CodexTools/sr-reproduction'))
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    cache = args.tools_dir / 'downloads'
    cache.mkdir(parents=True, exist_ok=True)
    records = []
    for name, (repo, commit) in UPSTREAMS.items():
        url = f'https://codeload.github.com/{repo}/zip/{commit}'
        archive = cache / f'{name}-{commit}.zip'
        if not archive.exists():
            partial = archive.with_suffix('.zip.partial')
            request = urllib.request.Request(url, headers={'User-Agent': 'sr-reproduction-lab'})
            with urllib.request.urlopen(request, timeout=60) as response, partial.open('wb') as handle:
                while chunk := response.read(1024 * 1024):
                    handle.write(chunk)
            partial.replace(archive)
        sha256 = hashlib.file_digest(archive.open('rb'), 'sha256').hexdigest()
        destination = root / 'vendor' / name
        destination.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(archive) as bundle:
            prefix = bundle.namelist()[0].split('/')[0] + '/'
            for member in bundle.infolist():
                relative = member.filename.removeprefix(prefix)
                if not relative:
                    continue
                output = (destination / relative).resolve()
                if not output.is_relative_to(destination.resolve()):
                    raise ValueError('Archive member escapes the vendor directory')
                if member.is_dir():
                    output.mkdir(parents=True, exist_ok=True)
                else:
                    output.parent.mkdir(parents=True, exist_ok=True)
                    output.write_bytes(bundle.read(member))
        records.append({'name': name, 'repository': repo, 'version': commit,
                        'source': url, 'archive_path': str(archive),
                        'install_path': str(destination), 'sha256': sha256})
        print(f'{name}: {commit} sha256={sha256}')
    artifact = root / 'artifacts' / 'upstream-downloads.json'
    artifact.parent.mkdir(parents=True, exist_ok=True)
    artifact.write_text(json.dumps(records, indent=2) + '\n', encoding='utf-8')


if __name__ == '__main__':
    main()

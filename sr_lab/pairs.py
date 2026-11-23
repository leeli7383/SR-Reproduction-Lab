"""Strict pairing prevents silent zip truncation and incorrect metric comparisons."""
from pathlib import Path


def image_pairs(hr_dir, lr_dir, scale):
    def index(folder, low):
        result = {}
        for p in sorted(Path(folder).iterdir()):
            if p.suffix.lower() not in {'.png', '.bmp', '.jpg', '.jpeg', '.tif'}:
                continue
            key = p.stem
            if low and key.endswith(f'x{scale}'):
                key = key[:-len(f'x{scale}')]
            if key in result:
                raise ValueError(f'Duplicate image ID: {key}')
            result[key] = p
        if not result:
            raise ValueError(f'No images: {folder}')
        return result
    hr, lr = index(hr_dir, False), index(lr_dir, True)
    if hr.keys() != lr.keys():
        raise ValueError(f'Unpaired IDs: HR-only={sorted(hr.keys()-lr.keys())}, LR-only={sorted(lr.keys()-hr.keys())}')
    return [(key, lr[key], hr[key]) for key in sorted(hr)]

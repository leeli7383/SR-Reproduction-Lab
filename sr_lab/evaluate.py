"""Run EIMN and a named interpolation baseline with per-image audit records."""
import argparse
import csv
import hashlib
import json
import time
from datetime import datetime, timezone
from pathlib import Path

import cv2
import numpy as np
import torch
from PIL import Image

from .pairs import image_pairs
from .upstream import basicsr_metrics, eimn
from .report import json_numbers


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', default='configs/eimn_x2.json')
    parser.add_argument('--output', default='artifacts/evaluation_x2')
    parser.add_argument('--limit', type=int, default=0)
    args = parser.parse_args()
    cfg = json.loads(Path(args.config).read_text(encoding='utf-8'))
    if cfg['model'] != 'EIMN_L':
        raise ValueError('This runner only implements EIMN_L; do not silently substitute models')
    torch.manual_seed(3407)
    torch.set_num_threads(4)
    torch.backends.cuda.matmul.allow_tf32 = False
    torch.backends.cudnn.allow_tf32 = False
    device = torch.device(cfg['device'])
    model = eimn(cfg['vendor_eimn'], cfg['scale'], cfg['weight'], device)
    metrics = basicsr_metrics(cfg['vendor_basicsr'])
    out = Path(args.output)
    out.mkdir(parents=True, exist_ok=True)
    rows = []
    for dataset in cfg['datasets']:
        base = Path(cfg['data_root'])/dataset
        pairs = image_pairs(base/'HR', base/f"LR_bicubic/X{cfg['scale']}", cfg['scale'])
        if args.limit:
            pairs = pairs[:args.limit]
        for name, lr_p, hr_p in pairs:
            lr = np.array(Image.open(lr_p).convert('RGB'))
            hr = np.array(Image.open(hr_p).convert('RGB'))
            if hr.shape[:2] != (lr.shape[0]*cfg['scale'], lr.shape[1]*cfg['scale']):
                raise ValueError(f'Wrong spatial ratio: {dataset}/{name}')
            tensor = torch.from_numpy(lr.copy()).permute(2,0,1).unsqueeze(0).float().to(device)/255
            # One untimed warmup per image; latency excludes transfers, metrics and file IO.
            with torch.inference_mode():
                model(tensor)
                if device.type == 'cuda':
                    torch.cuda.synchronize()
                    torch.cuda.reset_peak_memory_stats()
                started = time.perf_counter()
                prediction = model(tensor)
                if device.type == 'cuda':
                    torch.cuda.synchronize()
                latency = (time.perf_counter()-started)*1000
                raw = prediction[0].permute(1,2,0).cpu().numpy()*255
            outputs = {
                'EIMN_L': raw,
                'OpenCV_bicubic': cv2.resize(lr.astype(np.float32), (hr.shape[1],hr.shape[0]), interpolation=cv2.INTER_CUBIC),
            }
            for method, rgb in outputs.items():
                metric_rgb = np.clip(rgb,0,255).round() if cfg['quantize_before_metric'] else rgb
                kw = {'crop_border':cfg['crop_border'], 'test_y_channel':cfg['test_y_channel']}
                bgr = np.ascontiguousarray(metric_rgb[:,:,::-1])
                target = np.ascontiguousarray(hr[:,:,::-1])
                psnr = metrics.calculate_psnr(bgr, target, **kw)
                ssim = metrics.calculate_ssim(bgr, target, **kw)
                row = {'dataset':dataset,'image':name,'method':method,'psnr':float(psnr),'ssim':float(ssim),
                       'model_forward_ms':latency if method=='EIMN_L' else None,
                       'peak_allocated_mib':torch.cuda.max_memory_allocated()/2**20 if device.type=='cuda' and method=='EIMN_L' else None,
                       'lr_sha256':sha256(lr_p),'hr_sha256':sha256(hr_p)}
                rows.append(row)
                print(json.dumps(json_numbers(row), allow_nan=False), flush=True)
                image_out = out/'images'/dataset/method
                image_out.mkdir(parents=True,exist_ok=True)
                Image.fromarray(np.clip(rgb,0,255).round().astype(np.uint8)).save(image_out/f'{name}.png')
        # Persist partial results after every dataset to make interruptions recoverable.
        write_results(out, rows, cfg, args.limit)


def write_results(out, rows, cfg, limit):
    with (out/'per_image.csv').open('w',newline='',encoding='utf-8') as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0])); writer.writeheader(); writer.writerows(rows)
    means=[]
    for dataset in cfg['datasets']:
        for method in ['EIMN_L','OpenCV_bicubic']:
            selected=[r for r in rows if r['dataset']==dataset and r['method']==method]
            if not selected: continue
            p=float(np.mean([r['psnr'] for r in selected])); s=float(np.mean([r['ssim'] for r in selected]))
            means.append({'dataset':dataset,'method':method,'count':len(selected),'psnr':p,'ssim':s,
                          'paper_psnr_delta':p-cfg['paper_reference'][dataset][0] if method=='EIMN_L' else None})
    report={'timestamp_utc':datetime.now(timezone.utc).isoformat(),'config':cfg,'limited_run':bool(limit),
            'weight_sha256':sha256(cfg['weight']),'torch':torch.__version__,
            'device':str(torch.cuda.get_device_name(0)) if cfg['device']=='cuda' else 'cpu',
            'protocol':'BasicSR numpy RGB->BGR; Y channel; configured clipping/rounding; arithmetic per-image mean. Original EIMN uses uint8 clipping/rounding.',
            'results':means,'note':'OpenCV bicubic is an engineering baseline, not claimed identical to MATLAB bicubic. One timed forward per image, not a latency distribution.'}
    report['non_finite_json_policy']='Explicit strings Infinity/-Infinity/NaN, not non-standard numeric literals'
    (out/'summary.json').write_text(json.dumps(json_numbers(report),ensure_ascii=False,indent=2,allow_nan=False),encoding='utf-8')


if __name__=='__main__':
    main()

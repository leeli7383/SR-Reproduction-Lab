"""Cross-check real saved outputs using the original EIMN metric wrapper."""
import argparse
import csv
import json
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'vendor/EIMN'))
import numpy as np
import torch
from PIL import Image
from Metrics.psnr_ssim import _calculate_psnr_ssim_niqe


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--run',required=True)
    args=parser.parse_args()
    run=Path(args.run)
    cfg=json.loads((run/'summary.json').read_text(encoding='utf-8'))['config']
    if not cfg['quantize_before_metric']:
        raise ValueError('Saved uint8 PNG can only verify a quantized evaluation protocol')
    rows=list(csv.DictReader((run/'per_image.csv').open(encoding='utf-8')))
    differences=[]
    for row in rows:
        if row['method']!='EIMN_L': continue
        output=run/'images'/row['dataset']/'EIMN_L'/(row['image']+'.png')
        target=Path(cfg['data_root'])/row['dataset']/'HR'/(row['image']+'.png')
        def tensor(path):
            a=np.array(Image.open(path).convert('RGB')).astype(np.float32)/255
            return torch.from_numpy(a.transpose(2,0,1).copy()).unsqueeze(0)
        p,s,_,_=_calculate_psnr_ssim_niqe(tensor(output),tensor(target),crop_border=cfg['crop_border'],test_y_channel=cfg['test_y_channel'])
        differences.append({'dataset':row['dataset'],'image':row['image'],
                            'psnr_abs_delta':float(abs(p-float(row['psnr']))),
                            'ssim_abs_delta':float(abs(s-float(row['ssim'])))})
    if len(differences)!=19: raise AssertionError('Expected 19 complete EIMN output pairs')
    max_p=max(r['psnr_abs_delta'] for r in differences); max_s=max(r['ssim_abs_delta'] for r in differences)
    # Numeric equivalence of two implementations, not a tolerance for matching the paper.
    # The original RGB->Y helper returns float32 and PSNR retains float32 arithmetic;
    # BasicSR promotes the Y images to float64. Allow ten micro-dB for this precision difference.
    if max_p>1e-5 or max_s>1e-7: raise AssertionError(f'Metric implementation mismatch {max_p}, {max_s}')
    result={'verified_pairs':len(differences),'max_psnr_abs_delta':max_p,'max_ssim_abs_delta':max_s,
            'implementation_tolerance':{'psnr_db':1e-5,'ssim':1e-7,'reason':'float32 original Y-channel arithmetic versus BasicSR float64 metric arithmetic; not paper matching tolerance'},
            'passed':True,'scope':'original EIMN metric wrapper versus BasicSR metrics on actual saved benchmark outputs; does not prove data equals author data distribution',
            'per_image':differences}
    (run/'reference_metric_check.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps({k:v for k,v in result.items() if k!='per_image'}))


if __name__=='__main__': main()

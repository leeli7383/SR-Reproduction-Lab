import sys
import unittest
from pathlib import Path
import numpy as np
from sr_lab.upstream import basicsr_metrics


class MetricProtocol(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.basic = basicsr_metrics('vendor/BasicSR')
        sys.path.insert(0,str(Path('vendor/EIMN').resolve()))
        from Metrics.psnr_ssim import calculate_psnr, calculate_ssim
        cls.original_psnr = staticmethod(calculate_psnr)
        cls.original_ssim = staticmethod(calculate_ssim)

    def test_official_metrics_match_on_colored_images(self):
        rng=np.random.default_rng(3407)
        target=rng.integers(0,256,size=(32,40,3),dtype=np.uint8)
        output=np.clip(target.astype(np.float32)+rng.normal(0,6,target.shape),0,255).round().astype(np.uint8)
        for original,basic in [(self.original_psnr,self.basic.calculate_psnr),(self.original_ssim,self.basic.calculate_ssim)]:
            # Original expects RGB; BasicSR's numpy implementation expects BGR.
            reference=original(output,target,crop_border=2,test_y_channel=True)
            actual=basic(output[:,:,::-1],target[:,:,::-1],crop_border=2,test_y_channel=True)
            self.assertAlmostEqual(reference,actual,places=7)

    def test_crop_rejects_border_corruption_from_score(self):
        target=np.full((32,32,3),128,dtype=np.uint8)
        changed=target.copy(); changed[:2]=0
        self.assertEqual(self.basic.calculate_ssim(changed,target,2,test_y_channel=True),1.0)


if __name__=='__main__': unittest.main()

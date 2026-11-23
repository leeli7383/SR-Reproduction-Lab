import json
import unittest
from sr_lab.report import json_numbers


class JSONMetricTests(unittest.TestCase):
    def test_identity_metric_serializes_as_explicit_string(self):
        payload={'psnr':float('inf'),'finite':38.26,'nested':[float('nan')]}
        result=json.loads(json.dumps(json_numbers(payload),allow_nan=False))
        self.assertEqual(result['psnr'],'Infinity')
        self.assertEqual(result['finite'],38.26)
        self.assertEqual(result['nested'],['NaN'])

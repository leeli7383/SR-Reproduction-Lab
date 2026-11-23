import tempfile
import unittest
from pathlib import Path
from sr_lab.pairs import image_pairs


class PairTests(unittest.TestCase):
    def test_missing_image_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            hr, lr = Path(tmp)/'HR', Path(tmp)/'LR'
            hr.mkdir(); lr.mkdir()
            (hr/'a.png').touch(); (hr/'b.png').touch(); (lr/'ax2.png').touch()
            with self.assertRaisesRegex(ValueError, 'Unpaired'):
                image_pairs(hr, lr, 2)

    def test_matching_ids_and_duplicates(self):
        with tempfile.TemporaryDirectory() as tmp:
            hr, lr = Path(tmp)/'HR', Path(tmp)/'LR'
            hr.mkdir(); lr.mkdir()
            (hr/'a.png').touch(); (lr/'ax2.png').touch()
            self.assertEqual(image_pairs(hr, lr, 2)[0][0], 'a')
            (lr/'a.bmp').touch()
            with self.assertRaisesRegex(ValueError, 'Duplicate'):
                image_pairs(hr, lr, 2)


if __name__ == '__main__':
    unittest.main()

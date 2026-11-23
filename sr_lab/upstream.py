"""Load only the audited BasicSR metric modules without optional training extensions."""
import importlib.util
import sys
import types
from pathlib import Path


def basicsr_metrics(root):
    root = Path(root).resolve() / 'basicsr'
    # Isolated alias preserves original source and avoids BasicSR's eager architecture imports.
    prefix = '_sr_basicsr'
    for suffix, folder in [('', root), ('.utils', root/'utils'), ('.metrics', root/'metrics')]:
        name = prefix + suffix
        pkg = types.ModuleType(name)
        pkg.__path__ = [str(folder)]
        sys.modules[name] = pkg
    # Upstream uses absolute 'basicsr' imports. Temporarily expose isolated packages.
    old = {k: v for k, v in sys.modules.items() if k == 'basicsr' or k.startswith('basicsr.')}
    for k in list(old):
        del sys.modules[k]
    for suffix in ['', '.utils', '.metrics']:
        sys.modules['basicsr'+suffix] = sys.modules[prefix+suffix]
    try:
        for name, relative in [
            ('basicsr.utils.registry', 'utils/registry.py'),
            ('basicsr.utils.color_util', 'utils/color_util.py'),
            ('basicsr.metrics.metric_util', 'metrics/metric_util.py'),
            ('basicsr.metrics.psnr_ssim', 'metrics/psnr_ssim.py'),
        ]:
            spec = importlib.util.spec_from_file_location(name, root/relative)
            module = importlib.util.module_from_spec(spec)
            sys.modules[name] = module
            spec.loader.exec_module(module)
            if name == 'basicsr.utils.color_util':
                sys.modules['basicsr.utils'].bgr2ycbcr = module.bgr2ycbcr
        return module
    finally:
        for k in list(sys.modules):
            if k == 'basicsr' or k.startswith('basicsr.'):
                del sys.modules[k]
        sys.modules.update(old)


def eimn(root, scale, weight, device):
    import torch
    sys.path.insert(0, str(Path(root).resolve()))
    from Model.EIMN import EIMN_L
    model = EIMN_L(scale=scale)
    state = torch.load(weight, map_location='cpu', weights_only=True)
    model.load_state_dict(state, strict=True)
    return model.eval().to(device)

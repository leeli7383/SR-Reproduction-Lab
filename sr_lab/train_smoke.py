"""Diagnostic backprop check only. Synthetic inputs are NOT research training data."""
import json
from pathlib import Path
import torch
from .upstream import eimn


def main():
    cfg=json.loads(Path('configs/eimn_x2.json').read_text(encoding='utf-8'))
    torch.manual_seed(3407)
    model=eimn(cfg['vendor_eimn'],2,cfg['weight'],cfg['device']).train()
    optimizer=torch.optim.Adam(model.parameters(),lr=1e-5)
    low=torch.rand(1,3,16,16,device=cfg['device'])
    target=torch.nn.functional.interpolate(low,scale_factor=2,mode='bilinear',align_corners=False)
    before=next(model.parameters()).detach().clone()
    losses=[]
    for _ in range(3):
        optimizer.zero_grad(set_to_none=True)
        loss=torch.nn.functional.l1_loss(model(low),target)
        if not torch.isfinite(loss): raise RuntimeError('Non-finite loss')
        loss.backward()
        if not all(torch.isfinite(p.grad).all() for p in model.parameters() if p.grad is not None):
            raise RuntimeError('Non-finite gradient')
        optimizer.step(); losses.append(loss.item())
    changed=not torch.equal(before,next(model.parameters()).detach())
    if not changed: raise RuntimeError('Optimizer did not update parameters')
    folder=Path('artifacts/checkpoints'); folder.mkdir(parents=True,exist_ok=True)
    path=folder/'synthetic_smoke.pth'
    torch.save({'model':model.state_dict(),'optimizer':optimizer.state_dict(),'step':3},path)
    saved=torch.load(path,map_location=cfg['device'],weights_only=True)
    model.load_state_dict(saved['model'],strict=True); optimizer.load_state_dict(saved['optimizer'])
    result={'purpose':'synthetic diagnostic only; NOT paper training or quality reproduction',
            'seed':3407,'steps':3,'losses':losses,'parameters_changed':changed,
            'checkpoint_reload':True,'training_data':'one deterministic random 16x16 RGB tensor; bilinear synthetic target'}
    Path('artifacts/training_smoke.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps(result))


if __name__=='__main__': main()

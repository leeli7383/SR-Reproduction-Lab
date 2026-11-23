# 本地复现实验环境

日期：2026-11-23。系统：Windows；显卡：NVIDIA GeForce RTX 3050 Ti Laptop GPU，4 GiB。

## 隔离方式

项目解释器：`D:/CodexTools/sr-reproduction/venv/Scripts/python.exe`。

基于已有的 `D:/conda-envs/pytorch/python.exe` 创建 `venv --system-site-packages`，复用可正常使用CUDA的PyTorch/torchvision，避免重新下载大型GPU库；新增依赖只安装在D:/CodexTools/sr-reproduction/venv内，不修改原conda环境或全局Python。这个venv依赖原conda环境保留，因此不是可搬动的完全独立环境。

已核对[PyTorch官方历史版本安装说明](https://pytorch.org/get-started/previous-versions/)。本机实际Python 3.13.18、torch 2.12.1+cu132、torchvision 0.27.1+cu132。它们与作者原始Python 3.7/PyTorch 1.12.1不同；本项目验证当前环境下推理兼容，不声称重建了原始训练环境。

## 关键检查

- torch.cuda.is_available()：True。
- 原版EIMN_L(scale=2)加载官方`Weights/EIMN_L_x2.pth`：`strict=True`全部键匹配。
- 参数量：981724。
- GPU随机小图推理：1×3×32×32 → 1×3×64×64，输出全部有限。
- 该小图推理峰值分配显存约8.91 MiB，不代表完整图像或训练的显存需求。

## 版本固定与下载

- EIMN：`6a712bac203971c5002b55c2557b2d7367f1a77c`。
- BasicSR：`8d56e3a045f9fb3e1d8872f92ee4a4f07f886b0a`。
- 两者完整源码ZIP保存在`D:/CodexTools/sr-reproduction/downloads`，解压到项目`vendor/`。均不创建嵌套Git仓库；来源与SHA256记录在`artifacts/upstream-downloads.json`。
- 重放上游下载：`python tools/bootstrap_runtime.py`。它复用缓存并固定commit，不安装依赖。
- 新依赖版本见根目录`requirements-lock.txt`；完整机器记录见`artifacts/environment.json`。
- pip下载尝试、成功和失败细节在`D:/CodexTools/sr-reproduction/pip-*-install.log`。官方PyPI大包及清华镜像下载速度不稳定，必要时依据PyPI元数据直接下载wheel并验证其SHA256，再本地安装。
- 统一清单增量追加到`D:/CodexTools/downloads.json`；没有把配置文件、API凭据或缓存复制进Git。

## 重建参考

已有同类conda基础环境时：

```powershell
& 'D:/conda-envs/pytorch/python.exe' -m venv --system-site-packages 'D:/CodexTools/sr-reproduction/venv'
& 'D:/CodexTools/sr-reproduction/venv/Scripts/python.exe' -m pip install opencv-python-headless==5.1.0.95 scipy==1.18.1 einops==0.8.2 natsort==8.4.0 tqdm==4.70.1 pyyaml==6.0.4
python tools/bootstrap_runtime.py
```

在全新机器上须先根据PyTorch官方说明安装与硬件驱动兼容的PyTorch与torchvision，再建环境，不能仅凭此机器的venv路径复制。对BasicSR仅使用已记录的官方源码功能；未启用或编译可选DCNv2/CUDA算子，也未运行所有模型的完整工具箱测试。

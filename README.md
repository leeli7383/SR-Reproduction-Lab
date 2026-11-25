# SR Reproduction Lab

这个项目用 **EIMN 官方预训练模型**复核论文中的单图超分辨率结果，并用 **BasicSR 的指标实现**构建可复跑的评测工具。给定一张低分辨率图片，模型将宽和高各放大两倍。工具把输出和已知的高清参考图比较，并用 OpenCV 双三次插值作为对照。

首轮实验使用 Set5 的 5 对和 Set14 的 14 对 LR/HR 图片。每对图片评测两种方法，因此结果表有 **38 条数据**。所有 19 张 EIMN 输出都使用作者原版指标复核过。

| 测试集 | EIMN 实测 PSNR / SSIM | 论文表 1 PSNR / SSIM |
| --- | --- | --- |
| Set5 ×2 | 38.2756 dB / 0.9615 | 38.26 dB / 0.9620 |
| Set14 ×2 | 34.1619 dB / 0.9226 | 34.14 dB / 0.9227 |

实测与论文值接近。当前评测图片来自 SelfExSR 分发版本，与 EIMN 作者使用的数据是否逐像素一致仍待核对。训练部分已完成合成输入上的三步检查，完整重训、消融和端侧部署仍待开展。[首阶段实测报告](docs/RESULTS_STAGE1.md)

## 第一次打开项目

1. **想知道每个文件做什么**，看[项目与文件指南](docs/PROJECT_GUIDE.md)。它逐项列出项目文件的作用、输入、输出，并给出一张图片从读取到写入报告的实例。
2. **想直接看结果**，打开[首轮汇总](artifacts/runs/20261123-140139/summary.json)和[逐图数据](artifacts/runs/20261123-140139/per_image.csv)。[最新成功运行索引](artifacts/latest_stage1.json)记录本地一键流程最近一次通过的结果目录。
3. **想在本机复跑**，按[环境说明](docs/ENVIRONMENT.md)准备可用的 Python、PyTorch 和 CUDA，再运行下面的入口。换机器时使用该机器的解释器路径。

## 运行

在项目根目录打开 PowerShell。本机已有隔离环境时可执行：

```powershell
./tools/run_stage1.ps1 -Python 'D:/CodexTools/sr-reproduction/venv/Scripts/python.exe'
```

脚本依次准备上游源码及权重、下载和校验数据、运行测试、评测两套数据、复核指标、检查反向传播和检查点恢复。成功后终端显示结果目录，形如 `artifacts/runs/20261123-140139/summary.json`。各步日志保存在 `logs/`，成功后才更新 `artifacts/latest_stage1.json`。一键流程无需配置或调用外部 AI。

若源码、数据和环境均已就绪，可以先跑每个测试集的一张图。以下命令将快速检查的结果写入本地忽略目录：

```powershell
$srPython = 'D:/CodexTools/sr-reproduction/venv/Scripts/python.exe'
& $srPython -m sr_lab.evaluate --config configs/eimn_x2.json --limit 1 --output artifacts/outputs/quickstart
```

预期生成 `summary.json`、含 4 条数据的 `per_image.csv` 和 4 张输出图片。摘要中的 `limited_run: true` 表示只评测了部分图片。完整结果的复核、各字段含义和常见错误见[项目与文件指南](docs/PROJECT_GUIDE.md)。

## 参考资料

- 论文为 Xiao Liu、Xiangyu Liao、Xiuya Shi、Linbo Qing、Chao Ren 的 *Efficient Information Modulation Network for Image Super-Resolution*，ECAI 2023，1544–1551。[论文 DOI](https://doi.org/10.3233/FAIA230435) · [EIMN 作者代码](https://github.com/liux520/EIMN)
- 数据与源码版本、许可及工作进度分别见[数据来源](docs/DATASETS.md)、[环境说明](docs/ENVIRONMENT.md)、[本项目代码许可](LICENSE)和[进度记录](PROGRESS.md)。
- 两套外部 API 的分工、实际模型和用量见[双 API 说明](docs/API_DELEGATION.md)。

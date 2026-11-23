# SR Reproduction Lab

两个相互衔接的项目：**BasicSR评测工具**与 **EIMN（ECAI 2023）论文复现**。

## 范围

第一阶段：固定作者代码和官方权重，完成EIMN_L ×2在Set5/Set14的预训练评估、逐图CSV、指标协议与来源记录。预训练评估不等于从零重训论文；合成数据反向传播检查也不等于论文训练。

2026-11-23已完成首阶段：11项测试通过，Set5实测38.275649dB、Set14实测34.161943dB，原版指标交叉核对通过；与论文分数仍有小幅差异，详见[实测报告](docs/RESULTS_STAGE1.md)。

自有代码位于`sr_lab/`和`tools/`。上游代码在`vendor/`，下载数据在`data/`，这些大文件不提交。上游来源和许可见`docs/ENVIRONMENT.md`、`docs/DATASETS.md`及其各自LICENSE。自有代码使用MIT许可，不改变第三方代码、数据、权重的许可。

## 当前运行方式

在本目录打开PowerShell，使用`docs/ENVIRONMENT.md`指定的隔离Python解释器：

推荐执行`./tools/run_stage1.ps1`，它会依次检查上游、数据、测试、完整评估和训练诊断，保存到带时间戳的`artifacts/runs/`。中途失败会停止，不继续发布结果。它不会调用付费API。最新一次成功结果由`artifacts/latest_stage1.json`指向。

```powershell
# 替换为环境文档记录的实际解释器
$srPython = 'D:/CodexTools/sr-reproduction/venv/Scripts/python.exe'
& $srPython tools/bootstrap_runtime.py
& $srPython tools/prepare_benchmarks.py
& $srPython -m unittest discover -s tests -v
& $srPython -m sr_lab.evaluate --config configs/eimn_x2.json
& $srPython -m sr_lab.train_smoke
```

第一次需要准备固定版本上游与依赖，来源、版本、校验及下载记录见`docs/ENVIRONMENT.md`和`D:/CodexTools/downloads.json`。完整评估默认要求CUDA；没有CUDA时应显式修改配置并记录环境变化。

## 输出与评测协议

- `artifacts/evaluation_x2/per_image.csv`：逐图EIMN与OpenCV bicubic结果、输入哈希、推理时间。
- `artifacts/evaluation_x2/summary.json`：配置、权重哈希、实测均值与作者参考值的差异。
- `artifacts/evaluation_x2/images/`：本地可视化输出，不自动上传原始/衍生测试图片。
- `artifacts/training_smoke.json`：合成输入的3步梯度与保存恢复检查。
- `logs/`：本地执行和API记录，不含密钥，不提交。

评测用作者原版EIMN网络与strict权重加载，调用BasicSR官方指标源码。色彩转换、裁边、量化约定写入配置与报告。OpenCV bicubic只作为明确命名的工程基线，不声称等于MATLAB bicubic。每张图先预热，再测一次模型forward；它不是稳定延迟分布，不包括读图、数据传输和写图。

`sr_lab/upstream.py`仅加载BasicSR指标子模块，避免顶层自动导入可选训练扩展，官方源码不被修改。这一阶段不声称验证了BasicSR所有训练模型。

## 管理与分工

见`PROGRESS.md`、`docs/TASKS.md`和`docs/API_DELEGATION.md`。用户指定的两个客户端配置只作为API连接资料读取；不执行配置中的hook，不提交配置与凭据。API真实供应商/模型、用量与失败状态均如实记录，不能仅凭客户端名称认定模型。

## 论文

Xiao Liu, Xiangyu Liao, Xiuya Shi, Linbo Qing, Chao Ren. Efficient Information Modulation Network for Image Super-Resolution. ECAI 2023, 1544–1551. DOI: [10.3233/FAIA230435](https://doi.org/10.3233/FAIA230435)。[作者代码](https://github.com/liux520/EIMN)。

后续：补充独立训练集上的小规模训练与受控消融，再评估ONNX和真实设备部署。每阶段均保存环境、配置、结果与局限，不把缩减训练写成原论文全量复现。

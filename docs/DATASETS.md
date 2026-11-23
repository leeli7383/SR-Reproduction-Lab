# 测试数据来源与准备

日期：2026-11-23。当前范围：仅用于预训练评测的 Set5 ×2（5 对）和 Set14 ×2（14 对），不是训练数据。

## 一手来源与版本

数据取自论文作者 Jia-Bin Huang 的 [SelfExSR 官方仓库](https://github.com/jbhuang0604/SelfExSR)，固定提交 `8f6dd8c1d20cb7e8792a7177b4f6fd677633f598`。

[该版本 README](https://github.com/jbhuang0604/SelfExSR/blob/8f6dd8c1d20cb7e8792a7177b4f6fd677633f598/README.md) 的 Contents/data 段说明图像按超分倍率裁切；Comparison/Datasets 段说明 Set5 与 Set14 原始来源；图像类型表说明 LR 为 bicubic 下采样、HR 已作倍率整除裁切。本项目直接下载该仓库 `data/Set5/image_SRF_2` 与 `data/Set14/image_SRF_2` 的 HR/LR PNG，不自行生成或重新编码图像。

它是常用测试数据的作者分发版本，不是 EIMN 作者专门发布的数据包。若 EIMN 官方预训练评测分数存在差异，需要核对图像版本、评价协议和取整方式；数据来源相同领域并不能保证所有分发版本逐像素一致。

## 重放

在项目根目录执行：

```powershell
python tools/prepare_benchmarks.py
```

脚本仅需 Python 标准库：

- 固定 Git 提交，不依赖易变的默认分支。
- 对每份下载校验上游 Git blob SHA-1，并记录 SHA-256、PNG 头部尺寸、字节数和不可变原始 URL。
- 核对共 19 对图像和 HR/LR ×2 尺寸，发现缓存损坏或目标文件被改写时停止，不静默覆盖。
- 缓存放在 `D:/CodexTools/sr-data-downloads`，测试集放在项目 `data/benchmark`。
- 清单为 `artifacts/data_manifest.json`。下载清单与实验结果可以纳入 Git，原始图像和缓存不上传。

标准输出为机器可读下载计数；中途失败可重跑，已验证文件复用缓存。未发现或核验统一授予所有图像再分发的许可证，因此本项目只提供下载脚本、来源和校验值，保留原作者权利，不将图像包发布到自己的 GitHub 仓库。

## 本项目布局

```text
data/benchmark/
  Set5/
    HR/img_001.png ... img_005.png
    LR_bicubic/X2/img_001x2.png ... img_005x2.png
  Set14/
    HR/img_001.png ... img_014.png
    LR_bicubic/X2/img_001x2.png ... img_014x2.png
```

Set14 包含可能以灰度编码保存的图像；评测加载器应明确统一为三通道 RGB 后输入模型，并保留指标协议，不因 PNG 编码通道数不同而漏测。

## 本阶段实际验证

2026-11-23 已下载完成：38 张图像、19 对，合计 7,430,722 字节。每张图像的 Git blob 校验与全部 ×2 尺寸检查通过。随后再次执行准备命令，全部复用本地缓存成功；在隔离临时目录将一份目标 PNG 替换为无效内容后，脚本按预期拒绝覆盖并抛出错误。原项目图像未被该负向检查修改。

下载过程中 GitHub API 树第一次读取超时；改用同一不可变 API 地址成功取得元数据后缓存。一份 Set14 图片读取超时，脚本一次重试后成功。未切换到未核验数据源。

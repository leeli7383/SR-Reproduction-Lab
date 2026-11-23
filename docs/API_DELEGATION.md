# 双 API 任务分工与用量控制

这是辅助审阅流程，不是自动迭代编码代理。API 输出作为待核对资料，不能代替实验结果。

|本地配置入口|实际供应商及模型|本阶段分工|
|---|---|---|
|用户目录 `.claude/settings.json`|DeepSeek，`deepseek-v4-pro`|根据给定公开信息形成 EIMN 复现核对清单|
|用户目录 `.grok/config.toml`|火山方舟，`doubao-seed-evolving`|审阅超分评测设计，提出边界测试与方法风险|

配置名称不代表实际供应商：本阶段没有调用 Anthropic Claude 或 xAI Grok 模型。Claude Code 的 `[1M]` 是上下文展示后缀，请求时规范为实际模型名，不改写用户配置。

## 执行

```powershell
python tools/api_delegate.py --provider both --max-output-tokens 1500
python -m unittest discover -s tests -p test_api_delegate.py
```

每个供应商每个任务成功后，日志会阻止同一任务重复调用。没有自动重试、工具调用、循环代理、文件写入授权或远程执行授权；模型只返回文字。失败后默认不在同一次运行内重试。再次运行会对尚未成功的任务发出请求，必须先检查失败日志。

输出 token 上限为 1500，显式关闭思考，不发送历史对话；任务提示约几百词。这里只发送脚本内固定的公开论文信息和拟议评测规则，不发送个人简历、研究笔记、其他供应商配置或账号信息。实际计费以供应商账单为准，脚本不能证明额度相对其他方案节省了多少。

## 记录与安全边界

- 密钥仅从用户配置在内存读取，放入相应供应商 HTTPS 认证头；不写入源代码、报告和日志，不跟随 HTTP 重定向。
- `logs/api_calls.jsonl` 只记录供应商、模型、任务、UTC 时间、提示哈希、输出上限、数值 usage、状态和耗时，应由项目 `.gitignore` 排除。
- `docs/ai_reviews/` 存放带 AI 生成标记的建议；不自动应用，不将建议误报为通过的检查。
- 不保存原始请求/响应包和失败响应正文，避免网关回显凭据。只记录 HTTP 状态码或异常类型。
- 测试均离线，不依赖真实配置，不调用付费端点。

## 协议来源（核验日期：2026-11-23）

- [DeepSeek 官方 Anthropic 兼容说明](https://api-docs.deepseek.com/guides/anthropic_api/)：`/anthropic/v1/messages`、`x-api-key`、`max_tokens`、`thinking: disabled`。
- [火山方舟官方 Responses 迁移说明](https://docs.volcengine.com/docs/ark/responses-api-migration?lang=en)：`/api/v3`、Responses input 与 `max_output_tokens`。
- [火山方舟官方深度思考说明](https://docs.volcengine.com/docs/ark/responses-api-deep-thinking?lang=en)：`doubao-seed-evolving` 支持关闭思考。

首次实际调用状态和 usage 以本机日志为准；无响应或错误不等于模型完成了审阅。

## 本阶段实际调用（2026-11-23）

两次业务调用均成功；每方仅一次，无重试。DeepSeek报告输入185、输出270 tokens；火山方舟报告输入206、输出252、合计458 tokens，思考tokens为0。两方合计913 tokens（按各自usage相加，未折算价格）。再次运行同一任务已验证跳过，不产生新请求。

审阅稿已有明确质量问题：DeepSeek自行提出0.02 dB容差并把FFT训练损失混称推理分支；火山方舟误称严格JSON允许Infinity。已在各输出文件插入本地审阅备注，保留原始建议供追溯，不将其直接采纳为验收标准。

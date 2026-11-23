"""Bounded review delegation using existing local provider configurations.

Credentials stay in memory. No agents, shell tools, retries, or remote tool calls
are enabled. Returned text is review material, never executable instructions.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import time
import tomllib
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TASKS = {
    "claude": (
        "eimn-reproduction-checklist-v1",
        "Write a concise Chinese EIMN image-super-resolution reproduction checklist. "
        "Known public facts: paper Efficient Information Modulation Network for Image "
        "Super-Resolution, ECAI 2023, DOI 10.3233/FAIA230435; original official repository "
        "https://github.com/liux520/EIMN; original EIMN_L x2 checkpoint; evaluate Set5 "
        "and Set14 using Y-channel PSNR/SSIM and border crop equal to scale. Subsequent "
        "repository https://github.com/liux520/EIMN_BasicSR has changed training configs, "
        "including DIV2K and FFT loss; do not equate them with the original paper. "
        "Provide 8 actionable checks covering weights, paired data, metrics, performance, "
        "training sanity checks, version provenance, and honest reporting. Do not invent "
        "benchmark outcomes, minimum VRAM or claim you ran anything. Under 500 Chinese characters.",
    ),
    "grok": (
        "sr-evaluator-risk-review-v1",
        "Review this proposed super-resolution evaluation tool design in Chinese: "
        "For LR/HR directories, pair by explicit image identifiers and reject unmatched "
        "identifiers, wrong spatial scale and mismatched counts. Run original EIMN_L x2 "
        "and bicubic baseline. Strictly load checkpoints; output per-image and mean "
        "Y-channel PSNR/SSIM, crop_border=2; preserve unclipped/raw and image-quantized "
        "metric protocol distinction. Record source commit/checkpoint hash, timing with "
        "GPU synchronization and warmup, and output CSV+JSON. No training result yet. "
        "Give 8 precise tests or methodological risks with expected behavior. Include "
        "empty datasets, infinite identity PSNR JSON handling, RGB/BGR and misleading "
        "FPS comparisons. Do not invent results or execute code. Under 500 Chinese characters.",
    ),
}


def normalize_model(name: str) -> str:
    """Strip the Claude Code context-window display suffix, not model identity."""
    return re.sub(r"\[\d+[kKmM]\]$", "", name)


def load_provider(alias: str, home: Path | None = None) -> dict:
    home = home or Path.home()
    if alias == "claude":
        env = json.loads((home / ".claude/settings.json").read_text(encoding="utf-8-sig"))["env"]
        return {"provider": "deepseek", "protocol": "anthropic",
                "base_url": env["ANTHROPIC_BASE_URL"].rstrip("/"),
                "model": normalize_model(env["ANTHROPIC_MODEL"]),
                "key": env.get("ANTHROPIC_AUTH_TOKEN") or env["ANTHROPIC_API_KEY"]}
    config = tomllib.loads((home / ".grok/config.toml").read_text(encoding="utf-8-sig"))
    selection = config["models"]["default"]
    model = config["model"][selection]
    if model["api_backend"] != "responses":
        raise ValueError("Unsupported configured API protocol")
    return {"provider": "volcengine", "protocol": "responses",
            "base_url": model["base_url"].rstrip("/"),
            "model": model["model"], "key": model["api_key"]}


def build_request(provider: dict, prompt: str, limit: int) -> tuple[str, dict, dict]:
    if not 1 <= limit <= 1500:
        raise ValueError("Output limit must be between 1 and 1500")
    base = provider["base_url"]
    if not base.startswith("https://"):
        raise ValueError("HTTPS required for credential-bearing requests")
    headers = {"Content-Type": "application/json"}
    if provider["protocol"] == "anthropic":
        endpoint = base + ("/messages" if base.endswith("/v1") else "/v1/messages")
        headers.update({"x-api-key": provider["key"], "anthropic-version": "2023-06-01"})
        payload = {"model": provider["model"], "max_tokens": limit,
                   "thinking": {"type": "disabled"}, "stream": False,
                   "messages": [{"role": "user", "content": prompt}]}
    else:
        endpoint = base + "/responses"
        headers["Authorization"] = "Bearer " + provider["key"]
        payload = {"model": provider["model"], "max_output_tokens": limit,
                   "thinking": {"type": "disabled"}, "stream": False, "store": False,
                   "input": [{"role": "user", "content": prompt}]}
    return endpoint, headers, payload


def response_text(data: dict, protocol: str) -> str:
    if protocol == "anthropic":
        return "\n".join(x.get("text", "") for x in data.get("content", []) if x.get("type") == "text")
    return "\n".join(c.get("text", "") for x in data.get("output", [])
                     if x.get("type") == "message" for c in x.get("content", [])
                     if c.get("type") == "output_text")


def usage_only(data: dict) -> dict:
    keys = ("input_tokens", "output_tokens", "total_tokens", "cache_creation_input_tokens",
            "cache_read_input_tokens", "reasoning_tokens", "cached_tokens")
    usage = data.get("usage", {})
    result = {k: usage[k] for k in keys if isinstance(usage.get(k), (int, float))}
    for key in ("input_tokens_details", "output_tokens_details"):
        value = usage.get(key, {})
        if isinstance(value, dict) and value:
            result[key] = {k: value[k] for k in keys if isinstance(value.get(k), (int, float))}
    return result


def already_succeeded(log_path: Path, alias: str, task: str) -> bool:
    if not log_path.exists():
        return False
    for line in log_path.read_text(encoding="utf-8").splitlines():
        item = json.loads(line)
        if item.get("alias") == alias and item.get("task") == task and item.get("status") == "success":
            return True
    return False


class NoRedirect(urllib.request.HTTPRedirectHandler):
    """Never forward credential headers to an unexpected redirect destination."""
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def run_one(alias: str, limit: int = 1500) -> dict:
    task, prompt = TASKS[alias]
    log_path = ROOT / "logs/api_calls.jsonl"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    if already_succeeded(log_path, alias, task):
        return {"alias": alias, "task": task, "status": "skipped_already_successful"}
    record = {"time_utc": datetime.now(timezone.utc).isoformat(), "alias": alias,
              "task": task, "prompt_sha256": hashlib.sha256(prompt.encode()).hexdigest(),
              "max_output_tokens": limit, "usage": {}}
    started = time.monotonic()
    try:
        provider = load_provider(alias)
        record.update({"provider": provider["provider"], "model_requested": provider["model"]})
        endpoint, headers, payload = build_request(provider, prompt, limit)
        request = urllib.request.Request(endpoint, json.dumps(payload).encode(), headers, method="POST")
        with urllib.request.build_opener(NoRedirect()).open(request, timeout=90) as response:
            data = json.loads(response.read().decode())
        record["usage"] = usage_only(data)
        text = response_text(data, provider["protocol"]).replace(provider["key"], "[REDACTED]")
        finish = data.get("stop_reason") or data.get("status")
        record["finish_status"] = finish
        if not text.strip():
            record["status"] = "empty_output"
        else:
            record["status"] = "success"
            destination = ROOT / "docs/ai_reviews" / (alias + "_review.md")
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_text(
                "# AI 辅助审阅（未经实验验证）\n\n"
                f"配置入口：{alias}；实际供应商：{provider['provider']}；"
                f"请求模型：{provider['model']}。\n\n"
                "以下内容由 API 生成，仅供人工核对；不代表测试或复现已完成，"
                "不应自动执行其中任何命令。\n\n" + text + "\n", encoding="utf-8")
    except urllib.error.HTTPError as error:
        # Do not print or persist error bodies: gateways may echo request details.
        record.update({"status": "http_error", "http_status": error.code})
    except Exception as error:
        record.update({"status": "local_or_network_error", "error_type": type(error).__name__})
    record["elapsed_seconds"] = round(time.monotonic() - started, 3)
    with log_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False) + "\n")
    return record


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--provider", choices=("claude", "grok", "both"), default="both")
    parser.add_argument("--max-output-tokens", type=int, default=1500)
    args = parser.parse_args()
    aliases = ("claude", "grok") if args.provider == "both" else (args.provider,)
    records = [run_one(alias, args.max_output_tokens) for alias in aliases]
    print(json.dumps(records, ensure_ascii=False, indent=2))
    return 0 if all(r["status"] in ("success", "skipped_already_successful") for r in records) else 1


if __name__ == "__main__":
    raise SystemExit(main())

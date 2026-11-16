#!/usr/bin/env python3
"""TokenRouter · OpenAI Chat 最小示例（Python + OpenAI SDK）

需要填的两个变量（通过环境变量传入，不要写进代码）：
  1. TR_BASE_URL  设备根地址，例如 http://192.168.1.20 或 https://<名称>.tokenrouter.host
                  注意：这里填根地址，不带 /v1；脚本会自动拼成 <TR_BASE_URL>/v1。
  2. TR_API_KEY   设备「我的API密钥」里新建的密钥，sktr_ 开头。
                  不是晨羽云的 sk- 密钥，也不是上游厂商的 Key。

跑法：
  pip install -r python/requirements.txt      # 或 pip install "openai>=1.0"
  export TR_BASE_URL="http://<设备地址>"
  export TR_API_KEY="sktr_..."
  python python/openai_chat.py

  可选：export TR_MODEL="<模型 id>" 指定模型；不填则自动取 GET /v1/models 的第一个。

预期输出（形状）：
  模型: <模型 id>
  回复: <模型返回的文本>
  用量: prompt_tokens=... completion_tokens=... total_tokens=...
"""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request

try:
    from openai import OpenAI
except ImportError:
    sys.exit('未安装 openai SDK：pip install -r python/requirements.txt')

# Windows 管道 / 重定向时统一用 UTF-8 输出，避免中文乱码。
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

PROMPT = "用一句话说明 TokenRouter 是什么。"


def required_env(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        sys.exit(f"缺少环境变量 {name}，请先 export {name}=...")
    return value


def fetch_first_model(base_url: str, api_key: str) -> str:
    """GET /v1/models 只返回当前密钥属主可用的文本模型，取第一个。"""
    request = urllib.request.Request(
        f"{base_url}/v1/models",
        headers={"Authorization": f"Bearer {api_key}"},
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            payload = json.load(response)
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", "replace")[:300]
        sys.exit(f"GET /v1/models 返回 {exc.code}：{detail}")
    except urllib.error.URLError as exc:
        sys.exit(f"连不上设备 {base_url}：{exc.reason}")

    items = payload.get("data", []) if isinstance(payload, dict) else payload
    if not isinstance(items, list):
        sys.exit("GET /v1/models 返回格式不符合预期（应为 OpenAI 兼容 JSON）。")

    for item in items:
        model_id = item.get("id") if isinstance(item, dict) else item
        if model_id:
            return str(model_id)

    sys.exit("GET /v1/models 没有返回模型：确认这把密钥有可用文本模型。")


def main() -> None:
    base_url = required_env("TR_BASE_URL").rstrip("/")
    api_key = required_env("TR_API_KEY")
    model = os.environ.get("TR_MODEL", "").strip() or fetch_first_model(base_url, api_key)

    # OpenAI SDK 的 base_url 必须含 /v1，SDK 会在其后拼 chat/completions。
    client = OpenAI(base_url=f"{base_url}/v1", api_key=api_key)

    try:
        completion = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": PROMPT}],
        )
    except Exception as exc:  # 保持示例简短：统一打印失败原因后退出
        sys.exit(f"POST /v1/chat/completions 失败：{exc}")

    content = (completion.choices[0].message.content or "").strip()
    usage = completion.usage

    print(f"模型: {model}")
    print(f"回复: {content}")
    if usage is None:
        print("用量: 响应未返回 usage 字段")
    else:
        print(
            "用量: "
            f"prompt_tokens={usage.prompt_tokens} "
            f"completion_tokens={usage.completion_tokens} "
            f"total_tokens={usage.total_tokens}"
        )


if __name__ == "__main__":
    main()

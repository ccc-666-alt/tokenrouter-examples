#!/usr/bin/env python3
"""TokenRouter · Anthropic Messages 最小示例（Python + Anthropic SDK）

需要填的两个变量（通过环境变量传入，不要写进代码）：
  1. TR_BASE_URL  设备根地址，例如 http://192.168.1.20 或 https://<名称>.tokenrouter.host
                  注意：Anthropic SDK 用根地址，不要手工加 /v1；SDK 会自己拼 /v1/messages。
  2. TR_API_KEY   设备「我的API密钥」里新建的密钥，sktr_ 开头。
                  不是晨羽云的 sk- 密钥，也不是上游厂商的 Key。

跑法：
  pip install -r python/requirements.txt      # 或 pip install "anthropic>=0.40"
  export TR_BASE_URL="http://<设备地址>"
  export TR_API_KEY="sktr_..."
  python python/anthropic_messages.py

  可选：export TR_MODEL="<模型 id>" 指定模型；不填则自动取 GET /v1/models 的第一个。

预期输出（形状）：
  模型: <模型 id>
  回复: <模型返回的文本>
  用量: input_tokens=... output_tokens=...
"""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request

try:
    from anthropic import Anthropic
except ImportError:
    sys.exit('未安装 anthropic SDK：pip install -r python/requirements.txt')

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

    # 关键：base_url 用设备根地址，SDK 会在其后拼 /v1/messages；写成 <根地址>/v1 会变成 /v1/v1/messages。
    client = Anthropic(base_url=base_url, api_key=api_key)

    try:
        message = client.messages.create(
            model=model,
            max_tokens=256,
            messages=[{"role": "user", "content": PROMPT}],
        )
    except Exception as exc:  # 保持示例简短：统一打印失败原因后退出
        sys.exit(f"POST /v1/messages 失败：{exc}")

    text = "".join(
        block.text for block in message.content if getattr(block, "type", "") == "text"
    ).strip()
    usage = message.usage

    print(f"模型: {model}")
    print(f"回复: {text}")
    if usage is None:
        print("用量: 响应未返回 usage 字段")
    else:
        print(f"用量: input_tokens={usage.input_tokens} output_tokens={usage.output_tokens}")


if __name__ == "__main__":
    main()

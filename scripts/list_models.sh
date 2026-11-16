#!/usr/bin/env bash
# TokenRouter · 列出当前密钥可用的文本模型
#
# 说明：GET /v1/models 只列当前密钥属主可用的文本模型——设备上还有什么模型、
#       别的部门能用什么模型，都不会出现在这份列表里。返回的 id 就是填给
#       SDK / curl 的模型名，原样复制即可。
#
# 需要填的两个变量（通过环境变量传入，不要写进代码）：
#   1. TR_BASE_URL  设备根地址，例如 http://192.168.1.20 或 https://<名称>.tokenrouter.host
#                   注意：这里填根地址，不带 /v1；脚本会拼成 <TR_BASE_URL>/v1/models。
#   2. TR_API_KEY   设备「我的API密钥」里新建的密钥，sktr_ 开头。
#                   不是晨羽云的 sk- 密钥，也不是上游厂商的 Key。
#
# 跑法：
#   export TR_BASE_URL="http://<设备地址>"
#   export TR_API_KEY="sktr_..."
#   bash scripts/list_models.sh
#   # 有 jq 时自动格式化；没有 jq 就输出原始 JSON。
#
# 预期输出（形状）：
#   {"object":"list","data":[{"id":"<模型 id>","object":"model",...}]}
#   列表为空说明这把密钥暂无可用文本模型；401 / 404 的排查见 docs/迁移说明.md。

set -euo pipefail

: "${TR_BASE_URL:?请先 export TR_BASE_URL=\"http://<设备地址>\"（根地址，不带 /v1）}"
: "${TR_API_KEY:?请先 export TR_API_KEY=\"sktr_...\"}"

BASE_URL="${TR_BASE_URL%/}"

if ! response="$(curl -sS -w $'\n%{http_code}' "$BASE_URL/v1/models" \
  -H "Authorization: Bearer $TR_API_KEY" \
  -H "Accept: application/json")"; then
  echo "连不上设备：$BASE_URL（检查地址、端口、网络与证书）" >&2
  exit 1
fi

status="${response##*$'\n'}"
body="${response%$'\n'*}"

case "$status" in
  200)
    if command -v jq >/dev/null 2>&1; then
      printf '%s\n' "$body" | jq .
    else
      printf '%s\n' "$body"
    fi
    ;;
  401)
    echo "401 未通过鉴权：确认 TR_API_KEY 是设备上新建的 sktr_ 密钥，且请求头是 Authorization: Bearer <key>。" >&2
    exit 1
    ;;
  404)
    echo "404 未找到：确认 TR_BASE_URL 是设备根地址（不要带 /v1），且路径为 /v1/models。" >&2
    exit 1
    ;;
  *)
    echo "请求失败：HTTP $status" >&2
    printf '%s\n' "$body" | head -c 500 >&2
    echo >&2
    exit 1
    ;;
esac

# TokenRouter 接入示例（tokenrouter-examples）

TokenRouter（晨羽路由盒子，曾用名词元路由盒子）是部署在企业网络与 AI 模型服务之间的软硬件 AI 网关，负责接入、脱敏、额度、路由；它不是 GPU 主机，不在本机跑大模型。本仓库提供三份可直接运行的最小示例，覆盖 OpenAI Chat 与 Anthropic Messages 两个兼容面，外加一个用 curl 查询模型列表的脚本，用来验证“设备地址 + `sktr_` 密钥”这条链路是否通。

接入只需要改两处：把 `base_url` 指向设备地址，把 `api_key` 换成设备上新建的 `sktr_` 密钥；SDK、请求体、响应体都保持不变。路径上有一个约定要记清：**OpenAI 风格 SDK 的 `base_url` 要含 `/v1`；Anthropic SDK 用设备根地址，不要手工追加 `/v1`**。

跑起来需要三样东西：一台网络可达的 TokenRouter 设备（内网 IP 或设备域名）、一把 `sktr_` 开头的 API 密钥，以及 Python 3.9+ / Node.js 18+ / curl 中任意一个运行环境。模型名不用猜，先跑 `scripts/list_models.sh`，从返回的 `id` 里挑一个原样使用。

## 30 秒验证（curl）

```bash
export TR_BASE_URL="http://192.168.1.20"   # 换成设备根地址，不要带 /v1
export TR_API_KEY="sktr_xxxxxxxx"          # 换成设备上新建的密钥

# 1. 看这把密钥能用哪些文本模型，取一个 id
curl -sS "$TR_BASE_URL/v1/models" \
  -H "Authorization: Bearer $TR_API_KEY"

# 2. 发一次 chat completion（模型名填上一步返回的 id）
curl -sS "$TR_BASE_URL/v1/chat/completions" \
  -H "Authorization: Bearer $TR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"model":"<模型名>","messages":[{"role":"user","content":"你好"}]}'
```

## 需要填的两个变量

| 变量 | 取值示例 | 说明 |
| --- | --- | --- |
| `TR_BASE_URL` | `http://192.168.1.20` 或 `https://<名称>.tokenrouter.host`（内网域名，解析到设备本身，不是云端服务；证书由设备自己签发） | 设备**根地址**，末尾不带 `/v1`。OpenAI / Node / curl 示例自行拼 `/v1`，Anthropic 示例直接用根地址。 |
| `TR_API_KEY` | `sktr_...` | 设备「我的API密钥」里新建的密钥；不是晨羽云的 `sk-` 密钥，也不是上游厂商的 Key。 |

示例从环境变量读取这两个值，不把密钥写进代码。另支持可选的 `TR_MODEL` 指定模型；不填时自动取 `GET /v1/models` 返回列表里的首个模型。

## 目录说明

| 路径 | 说明 |
| --- | --- |
| `python/openai_chat.py` | OpenAI Python SDK，调 `POST /v1/chat/completions`，打印回复与用量字段。 |
| `python/anthropic_messages.py` | Anthropic Python SDK，`base_url` 用设备根地址，调 `POST /v1/messages`，打印回复与用量字段。 |
| `python/requirements.txt` | Python 示例依赖（`openai`、`anthropic`）。 |
| `node/chat.mjs` | Node.js 18+ 原生 `fetch`，直接调 `POST /v1/chat/completions`，零依赖。 |
| `scripts/list_models.sh` | curl `GET /v1/models`；只列**当前密钥属主可用**的文本模型。 |
| `docs/迁移说明.md` | 原来直连 OpenAI / Anthropic 的项目怎么改，以及 401 / 404 排查。 |
| `LICENSE` | MIT 许可证。 |

## 接口支持面

| 能力 | 方法与路径 |
| --- | --- |
| 模型列表 | `GET /v1/models`（只列当前密钥属主可用的文本模型） |
| OpenAI Chat | `POST /v1/chat/completions` |
| OpenAI Responses | `POST /v1/responses`（无状态子集） |
| Anthropic Messages | `POST /v1/messages` |

可用模型取决于设备配置与密钥属主权限，以 `GET /v1/models` 和「使用API」页为准。兼容接口不等于全部模型与多模态都覆盖；本仓库示例只演示文本对话，图片、视频、语音等入口不在此范围内。

## 边界

它是一台设备，不是集群：单机，不提供双机接管；主备路由指的是上游之间的切换，设备本身没有自动接管，设备故障时该段内网 AI 流量会中断。

脱敏覆盖 4 类字段：手机号、身份证号、银行卡号、电子邮箱，作用在文本对话入口；图片、视频、语音、附件、订阅代理不在范围内。

算力不在盒子里：设备用 SSH 连到你自己那台服务器或工作站，靠内置 Agent 完成安装、部署、调优。本机跑模型属于下一版固件规划，0.9.34 没有。

## 常见问题

**和 API 中转站有什么区别？** 中转站解决"能不能调通"，网关解决"谁能调、调了什么、出门前处理过没有"。

**多上游怎么切？** 主上游异常时切到备用上游，规则在管理台改，应用不用跟着发版；这是上游之间的切换，不是设备冗余。

**密钥怎么发？** 员工只拿一个 `sktr_` 开头的虚拟 Key；按部门与员工设日、周、月预算，超支自动停用；用量按用户、密钥、模型、上游可查。

## 从直连切换过来

如果你的项目现在直连 OpenAI 或 Anthropic，只需要改 `base_url` 与 `api_key` 两处，其余代码不动。具体改法、验证步骤和常见报错见 [`docs/迁移说明.md`](docs/迁移说明.md)。

## 许可证

本项目采用 [MIT](LICENSE) 许可证。Copyright (c) 2026 晨羽智云（杭州）科技有限公司。

---

官网：[chenyu.pro](https://chenyu.pro) ｜ 产品页：[chenyu.pro/token-router](https://chenyu.pro/token-router)

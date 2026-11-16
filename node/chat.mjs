#!/usr/bin/env node
/**
 * TokenRouter · Node.js 最小示例（Node 18+，原生 fetch，零依赖）
 *
 * 需要填的两个变量（通过环境变量传入，不要写进代码）：
 *   1. TR_BASE_URL  设备根地址，例如 http://192.168.1.20 或 https://<名称>.tokenrouter.host
 *                   注意：这里填根地址，不带 /v1；脚本会拼成 <TR_BASE_URL>/v1/chat/completions。
 *   2. TR_API_KEY   设备「我的API密钥」里新建的密钥，sktr_ 开头。
 *                   不是晨羽云的 sk- 密钥，也不是上游厂商的 Key。
 *
 * 跑法：
 *   export TR_BASE_URL="http://<设备地址>"
 *   export TR_API_KEY="sktr_..."
 *   node node/chat.mjs
 *
 *   可选：export TR_MODEL="<模型 id>" 指定模型；不填则自动取 GET /v1/models 的第一个。
 *
 * 预期输出（形状）：
 *   模型: <模型 id>
 *   回复: <模型返回的文本>
 *   用量: prompt_tokens=... completion_tokens=... total_tokens=...
 */

const baseUrl = (process.env.TR_BASE_URL || "").trim().replace(/\/+$/, "");
const apiKey = (process.env.TR_API_KEY || "").trim();

if (!baseUrl || !apiKey) {
  console.error('缺少环境变量：请先 export TR_BASE_URL="http://<设备地址>" 和 TR_API_KEY="sktr_..."');
  process.exit(1);
}

if (typeof fetch !== "function") {
  console.error("当前 Node.js 没有全局 fetch，请升级到 Node.js 18 或更高版本。");
  process.exit(1);
}

const authHeaders = { Authorization: `Bearer ${apiKey}`, Accept: "application/json" };

async function readJson(response) {
  const text = await response.text();
  if (!response.ok) {
    console.error(`请求失败：HTTP ${response.status}`);
    console.error(text.slice(0, 500));
    process.exit(1);
  }
  try {
    return JSON.parse(text);
  } catch {
    console.error("响应不是 JSON：");
    console.error(text.slice(0, 300));
    process.exit(1);
  }
}

function contentToText(content) {
  if (typeof content === "string") return content;
  if (Array.isArray(content)) return content.map((part) => part?.text ?? "").join("");
  return "";
}

async function main() {
  // GET /v1/models 只返回当前密钥属主可用的文本模型。
  const models = await readJson(await fetch(`${baseUrl}/v1/models`, { headers: authHeaders }));
  const items = Array.isArray(models) ? models : models?.data ?? [];
  const ids = items
    .map((item) => (typeof item === "string" ? item : item?.id))
    .filter((id) => typeof id === "string" && id.length > 0);

  if (ids.length === 0) {
    console.error("GET /v1/models 没有返回模型：确认这把密钥有可用文本模型。");
    process.exit(1);
  }

  const model = (process.env.TR_MODEL || "").trim() || ids[0];

  const completion = await readJson(
    await fetch(`${baseUrl}/v1/chat/completions`, {
      method: "POST",
      headers: { ...authHeaders, "Content-Type": "application/json" },
      body: JSON.stringify({
        model,
        messages: [{ role: "user", content: "用一句话说明 TokenRouter 是什么。" }],
      }),
    }),
  );

  const text = contentToText(completion?.choices?.[0]?.message?.content).trim();
  const usage = completion?.usage ?? {};

  console.log(`模型: ${model}`);
  console.log(`回复: ${text}`);
  console.log(
    `用量: prompt_tokens=${usage.prompt_tokens ?? "-"} ` +
      `completion_tokens=${usage.completion_tokens ?? "-"} ` +
      `total_tokens=${usage.total_tokens ?? "-"}`,
  );
}

main().catch((error) => {
  console.error(`请求出错：${error?.message ?? error}`);
  process.exit(1);
});

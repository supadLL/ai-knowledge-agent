const statsGrid = document.querySelector("#statsGrid");
const indexBadge = document.querySelector("#indexBadge");
const providerList = document.querySelector("#providerList");
const evalBox = document.querySelector("#evalBox");
const evalHistoryList = document.querySelector("#evalHistoryList");
const statusBar = document.querySelector("#statusBar");
const documentsList = document.querySelector("#documentsList");
const documentSourcesList = document.querySelector("#documentSourcesList");
const chatThread = document.querySelector("#chatThread");
const chatForm = document.querySelector("#chatForm");
const llmProviderType = document.querySelector("#llmProviderType");
const llmAccountsList = document.querySelector("#llmAccountsList");
const llmUsageBadge = document.querySelector("#llmUsageBadge");
const languageToggle = document.querySelector("#languageToggle");
const pageTitle = document.querySelector("#pageTitle");
const pageSubtitle = document.querySelector("#pageSubtitle");
const fuelStrategy = document.querySelector("#fuelStrategy");
const importModal = document.querySelector("#importModal");
const openImportModalButton = document.querySelector("#openImportModal");
const closeImportModalButton = document.querySelector("#closeImportModal");
const tokenJsonInput = document.querySelector("#tokenJsonInput");
const externalImportProvider = document.querySelector("#externalImportProvider");
const externalImportUrl = document.querySelector("#externalImportUrl");
const externalImportPayload = document.querySelector("#externalImportPayload");
const externalImportFile = document.querySelector("#externalImportFile");

const LANGUAGE_KEY = "aiKnowledgeAgent.language";
const PAGE_KEY = "aiKnowledgeAgent.page";
let currentCodexOAuth = null;

const translations = {
  en: {
    languageToggle: "中文",
    ready: "Ready",
    refresh: "Refresh",
    navDiagnostics: "Diagnostics",
    navDocuments: "Documents",
    navAsk: "Ask",
    navLlmAccess: "Fuel Pool",
    navEvaluations: "Evaluations",
    navSettings: "Settings",
    pageDiagnosticsTitle: "Local Knowledge Console",
    pageDiagnosticsSubtitle: "Inspect index health, provider status, and local runtime settings.",
    pageDocumentsTitle: "Document Index",
    pageDocumentsSubtitle: "Manage local source folders and rebuild the searchable index.",
    pageAskTitle: "Grounded Question Answering",
    pageAskSubtitle: "Ask against local files, then inspect retrieved evidence.",
    pageLlmAccessTitle: "Fuel Pool",
    pageLlmAccessSubtitle: "Manage app-internal account dispatch, cooldown, and usage.",
    pageEvaluationsTitle: "Evaluation",
    pageEvaluationsSubtitle: "Run benchmark questions and compare retrieval quality.",
    pageSettingsTitle: "Provider Settings",
    pageSettingsSubtitle: "Review the effective model, embedding, and packaging configuration.",
    indexStatus: "Index Status",
    checking: "Checking",
    documentsTitle: "Documents",
    sourceFolder: "Source folder",
    rebuild: "Rebuild",
    saveSource: "Save Source",
    sourceSaved: "Document source saved",
    sourceDeleted: "Document source deleted",
    sourceReindexed: "Source reindexed with {count} chunks.",
    documentDeleted: "Document removed from index",
    documentReindexed: "Document reindexed with {count} chunks.",
    noSavedSources: "No saved document sources yet.",
    useSource: "Use",
    reindexSource: "Reindex",
    sourceChunks: "{count} chunks",
    askTitle: "Ask",
    question: "Question",
    askAction: "Ask",
    send: "Send",
    questionPlaceholder: "Ask your local knowledge base...",
    sourcesTitle: "Sources",
    llmAccessTitle: "Fuel Pool",
    noTrackedCalls: "No tracked calls",
    name: "Name",
    connectionType: "Connection type",
    apiKey: "API key",
    enabledForRag: "Enabled for RAG answers",
    connectLlmAccount: "Connect LLM Account",
    importAccount: "Import Account",
    importSubtitle: "Choose a connection method and add it to the local fuel pool.",
    close: "Close",
    localRelayHint: "Connect one-api, new-api, sub2api, or another local gateway.",
    codexGatewayHint: "Use cockpit-tools or another Codex-compatible local gateway.",
    openaiCompatibleHint: "Add a direct API key provider with a /v1 base URL.",
    tokenSessionImport: "Token / session import",
    tokenSessionHint: "Planned after encrypted local secret storage is ready.",
    importShort: "Import",
    oauthCopy: "Open the authorization page. The account imports automatically after login.",
    authLink: "Authorization link",
    copy: "Copy",
    openInBrowser: "Open in browser",
    callbackUrl: "Callback URL",
    callbackPlaceholder: "Paste callback URL, for example http://localhost...",
    authorizedContinue: "Authorized, continue",
    oauthNote:
      "If the browser does not return automatically, paste the callback URL here and continue manually.",
    tokenPasteHint:
      "Paste session JSON, auth.json, account JSON, Sub2API JSON, accessToken, or refresh_token.",
    requiredFieldsExample: "Required fields and example",
    tokenJsonPlaceholder:
      "Example: paste session JSON, accessToken, Sub2API export JSON, or {\"accessToken\":\"eyJ...\"}",
    importAction: "Import",
    providerPresetCopy: "Choose a saved provider preset, then adjust fields if needed.",
    localImportCopy: "Import account JSON from pasted content, an import URL, or a local file.",
    getLocalAccount: "Get local account",
    importFromFile: "Import from file",
    autoDetect: "Auto detect",
    importUrl: "Import URL",
    externalImportPlaceholder:
      "Paste account JSON. Supports one object, an accounts array, OpenAI-compatible keys, sub2api exports, accessToken, or refresh_token.",
    externalImportDone: "Imported {count} account(s)",
    externalImportMissing: "Paste import JSON, choose a local file, or enter an import URL.",
    copied: "Copied",
    oauthStarted: "OAuth login is ready. Open the authorization link.",
    oauthWaiting: "Waiting for OAuth callback...",
    oauthAutoWaiting: "Authorization page opened. Import will complete automatically after login.",
    oauthCompleted: "OAuth account imported",
    oauthExpired: "OAuth login expired. Start a new login.",
    tokenImported: "Token payload imported",
    tokenMissing: "Could not find accessToken/apiKey in the pasted content.",
    baseUrlRequired: "Enter a real upstream Base URL, such as sub2api or a compatible API endpoint.",
    dispatchStrategy: "Dispatch strategy",
    internalFuelCopy:
      "Fuel Pool is only used inside this app and will not change local Codex or API proxy settings.",
    priority: "Priority",
    weight: "Weight",
    tokenNote:
      "Token/session import is planned, but locked until local secret storage and log redaction are hardened.",
    evaluationTitle: "Evaluation",
    evalHistory: "Eval history",
    evalComparison: "Compared with previous",
    noEvalHistory: "No eval runs yet.",
    questionsFile: "Questions file",
    runEval: "Run Eval",
    providerSettings: "Provider Settings",
    providerSettingsCopy:
      "Provider values are read from environment variables. Use CLI diagnostics to confirm local packaged configuration before release builds.",
    indexedChunks: "Indexed chunks",
    documents: "Documents",
    updated: "Updated",
    indexFile: "Index file",
    chunkSize: "Chunk size",
    overlap: "Overlap",
    topK: "Top K",
    vectorWeight: "Vector weight",
    embeddingProvider: "Embedding provider",
    embeddingDimensions: "Embedding dimensions",
    embeddingModel: "Embedding model",
    generationProvider: "Generation provider",
    generationModel: "Generation model",
    contextChars: "Context chars",
    local: "local",
    chunks: "chunks",
    noIndexedDocuments: "No indexed documents yet.",
    statusRefreshed: "Status refreshed",
    indexingDocuments: "Indexing documents...",
    indexedResult: "Indexed {count} chunks with {provider}.",
    thinking: "Thinking...",
    assistantThinking: "Searching local context and preparing an answer...",
    retrievingContext: "Retrieving local context...",
    answeredWithSources: "Answered with {count} sources",
    sourceCount: "{count} sources",
    emptyQuestion: "Type a question first.",
    runningEval: "Running evaluation...",
    evalComplete: "Eval complete: hit rate {rate}",
    callsTokens: "{calls} calls / {tokens} tokens",
    noLlmAccounts: "No LLM accounts connected yet.",
    enabled: "Enabled",
    paused: "Paused",
    keyNone: "none",
    test: "Test",
    disable: "Disable",
    enable: "Enable",
    delete: "Delete",
    savingLlmAccount: "Saving LLM account...",
    llmAccountConnected: "LLM account connected",
    llmAccountUpdated: "LLM account updated",
    llmAccountDeleted: "LLM account deleted",
    testingLlmAccount: "Testing LLM account...",
    openaiCompatible: "OpenAI-compatible API",
    localRelay: "Upstream relay / sub2api",
    codexLocalAccess: "Codex account relay",
    firstAvailable: "First available",
    roundRobin: "Round robin",
    leastUsed: "Least used",
    priorityWeighted: "Priority weighted",
    fuelStrategyUpdated: "Fuel pool strategy updated",
    providerType: "Provider",
    model: "Model",
    baseUrl: "Base URL",
    upstreamBaseUrl: "Upstream URL",
    key: "Key",
    refreshCredentials: "Refresh credentials",
    available: "Available",
    unavailable: "Unavailable",
    error: "Error",
  },
  zh: {
    languageToggle: "EN",
    ready: "就绪",
    refresh: "刷新",
    navDiagnostics: "诊断",
    navDocuments: "文档",
    navAsk: "问答",
    navLlmAccess: "燃料池",
    navEvaluations: "评估",
    navSettings: "设置",
    pageDiagnosticsTitle: "本地知识库控制台",
    pageDiagnosticsSubtitle: "查看索引状态、模型配置和本地运行信息。",
    pageDocumentsTitle: "文档索引",
    pageDocumentsSubtitle: "管理本地来源目录，并重建可检索索引。",
    pageAskTitle: "基于本地知识的问答",
    pageAskSubtitle: "对本地文件提问，并检查召回证据来源。",
    pageLlmAccessTitle: "燃料池",
    pageLlmAccessSubtitle: "管理本地中转燃料、账号分发、冷却和用量。",
    pageEvaluationsTitle: "检索评估",
    pageEvaluationsSubtitle: "运行基准问题，观察检索命中和回答质量。",
    pageSettingsTitle: "模型与供应商设置",
    pageSettingsSubtitle: "查看当前生效的嵌入、生成和打包配置。",
    indexStatus: "索引状态",
    checking: "检查中",
    documentsTitle: "文档",
    sourceFolder: "来源文件夹",
    rebuild: "重建索引",
    saveSource: "保存来源",
    sourceSaved: "文档来源已保存",
    sourceDeleted: "文档来源已删除",
    sourceReindexed: "来源已重建索引，包含 {count} 个片段。",
    documentDeleted: "文档已从索引中移除",
    documentReindexed: "文档已重建索引，包含 {count} 个片段。",
    noSavedSources: "还没有保存的文档来源。",
    useSource: "使用",
    reindexSource: "重建",
    sourceChunks: "{count} 个片段",
    askTitle: "提问",
    question: "问题",
    askAction: "提问",
    send: "发送",
    questionPlaceholder: "向你的本地知识库提问...",
    sourcesTitle: "来源",
    llmAccessTitle: "燃料池",
    noTrackedCalls: "暂无调用记录",
    name: "名称",
    connectionType: "接入方式",
    apiKey: "API Key",
    enabledForRag: "用于 RAG 回答",
    connectLlmAccount: "接入模型账号",
    importAccount: "账号导入",
    importSubtitle: "选择接入方式，并把账号加入本地燃料池。",
    close: "关闭",
    localRelayHint: "接入 one-api、new-api、sub2api 或其他本地网关。",
    codexGatewayHint: "使用 cockpit-tools 或其他 Codex-compatible 本地网关。",
    openaiCompatibleHint: "添加带 /v1 base URL 的直接 API Key 供应商。",
    tokenSessionImport: "Token / session 导入",
    tokenSessionHint: "本地加密密钥存储完成后开放。",
    importShort: "导入",
    oauthCopy: "打开授权页面，登录完成后会自动导入账号。",
    authLink: "授权链接",
    copy: "复制",
    openInBrowser: "在浏览器中打开",
    callbackUrl: "回调地址",
    callbackPlaceholder: "粘贴完整回调地址，例如 http://localhost...",
    authorizedContinue: "我已授权，继续",
    oauthNote: "如果浏览器没有自动返回，可以把回调地址粘贴到这里并手动继续。",
    tokenPasteHint: "粘贴 session JSON、auth.json、账号 JSON、Sub2API JSON、accessToken 或 refresh_token。",
    requiredFieldsExample: "必填字段与示例",
    tokenJsonPlaceholder:
      "示例：粘贴 session JSON、accessToken、Sub2API 导出 JSON，或 {\"accessToken\":\"eyJ...\"}",
    importAction: "导入",
    providerPresetCopy: "选择已保存供应商，可直接填写后自动保存。",
    localImportCopy: "从粘贴内容、导入 URL 或本地 JSON 文件导入账号。",
    getLocalAccount: "获取本地账号",
    importFromFile: "从本地文件导入",
    autoDetect: "自动识别",
    importUrl: "导入 URL",
    externalImportPlaceholder:
      "粘贴账号 JSON。支持单个对象、accounts 数组、OpenAI-compatible key、sub2api 导出、accessToken 或 refresh_token。",
    externalImportDone: "已导入 {count} 个账号",
    externalImportMissing: "请粘贴导入 JSON、选择本地文件，或填写导入 URL。",
    copied: "已复制",
    oauthStarted: "OAuth 登录已准备好，请打开授权链接。",
    oauthWaiting: "正在等待 OAuth 回调...",
    oauthAutoWaiting: "授权页面已打开，登录完成后会自动导入。",
    oauthCompleted: "OAuth 账号已导入",
    oauthExpired: "OAuth 登录已过期，请重新开始登录。",
    tokenImported: "Token 内容已导入",
    tokenMissing: "未从粘贴内容中找到 accessToken/apiKey。",
    baseUrlRequired: "请填写真实可用的 Base URL，例如本地中转或兼容 API 地址。",
    dispatchStrategy: "分发策略",
    internalFuelCopy: "燃料池只在本软件内部使用，不会修改本地 Codex 或其他 API 代理配置。",
    priority: "优先级",
    weight: "权重",
    tokenNote: "Token/session 导入已规划，但需要先完成本地密钥存储和日志脱敏加固。",
    evaluationTitle: "评估",
    evalHistory: "评估历史",
    evalComparison: "与上次相比",
    noEvalHistory: "还没有评估记录。",
    questionsFile: "问题文件",
    runEval: "运行评估",
    providerSettings: "供应商设置",
    providerSettingsCopy: "供应商配置来自环境变量或本地账号。发布打包前可通过 CLI 诊断确认配置。",
    indexedChunks: "索引片段",
    documents: "文档",
    updated: "更新时间",
    indexFile: "索引文件",
    chunkSize: "切片大小",
    overlap: "重叠",
    topK: "Top K",
    vectorWeight: "向量权重",
    embeddingProvider: "嵌入供应商",
    embeddingDimensions: "嵌入维度",
    embeddingModel: "嵌入模型",
    generationProvider: "生成供应商",
    generationModel: "生成模型",
    contextChars: "上下文字数",
    local: "本地",
    chunks: "片段",
    noIndexedDocuments: "还没有索引文档。",
    statusRefreshed: "状态已刷新",
    indexingDocuments: "正在索引文档...",
    indexedResult: "已索引 {count} 个片段，嵌入方式：{provider}。",
    thinking: "思考中...",
    assistantThinking: "正在检索本地上下文并组织回答...",
    retrievingContext: "正在检索本地上下文...",
    answeredWithSources: "已回答，包含 {count} 个来源",
    sourceCount: "{count} 个来源",
    emptyQuestion: "请先输入问题。",
    runningEval: "正在运行评估...",
    evalComplete: "评估完成：命中率 {rate}",
    callsTokens: "{calls} 次调用 / {tokens} tokens",
    noLlmAccounts: "还没有接入模型账号。",
    enabled: "已启用",
    paused: "已暂停",
    keyNone: "无",
    test: "测试",
    disable: "停用",
    enable: "启用",
    delete: "删除",
    savingLlmAccount: "正在保存模型账号...",
    llmAccountConnected: "模型账号已接入",
    llmAccountUpdated: "模型账号已更新",
    llmAccountDeleted: "模型账号已删除",
    testingLlmAccount: "正在测试模型账号...",
    openaiCompatible: "OpenAI-compatible API",
    localRelay: "上游服务 / sub2api",
    codexLocalAccess: "Codex 账号反代",
    firstAvailable: "第一个可用",
    roundRobin: "轮询分发",
    leastUsed: "优先低用量",
    priorityWeighted: "优先级 + 权重",
    fuelStrategyUpdated: "燃料池策略已更新",
    providerType: "供应商",
    model: "模型",
    baseUrl: "Base URL",
    key: "密钥",
    refreshCredentials: "刷新凭据",
    available: "可用",
    unavailable: "不可用",
    error: "错误",
  },
};

const providerTypeKeys = {
  openai_compatible: "openaiCompatible",
  local_relay: "localRelay",
  codex_local_access: "codexLocalAccess",
};

const strategyKeys = {
  first_available: "firstAvailable",
  round_robin: "roundRobin",
  least_used: "leastUsed",
  priority_weighted: "priorityWeighted",
};

const importPresets = {
  local_relay: {
    name: "Upstream relay",
    baseUrl: "",
    model: "gpt-5.4",
    priority: 100,
    weight: 1,
    enabled: true,
  },
  codex_local_access: {
    name: "Codex account",
    baseUrl: "https://chatgpt.com/backend-api/codex",
    model: "gpt-5.4",
    priority: 80,
    weight: 2,
    enabled: true,
  },
  openai_compatible: {
    name: "OpenAI-compatible API",
    baseUrl: "https://api.openai.com/v1",
    model: "gpt-4o-mini",
    priority: 120,
    weight: 1,
    enabled: true,
  },
};

const providerPresets = {
  custom: {
    type: "openai_compatible",
    name: "Custom",
    baseUrl: "https://api.example.com/v1",
    model: "gpt-4o-mini",
    priority: 120,
    weight: 1,
  },
  cockpit: {
    type: "openai_compatible",
    name: "Cockpit Api",
    baseUrl: "https://chongcodex.cn/v1",
    model: "gpt-5.4",
    priority: 80,
    weight: 2,
    enabled: true,
  },
  openai: {
    type: "openai_compatible",
    name: "OpenAI Official",
    baseUrl: "https://api.openai.com/v1",
    model: "gpt-4o-mini",
    priority: 120,
    weight: 1,
  },
  azure: {
    type: "openai_compatible",
    name: "Azure OpenAI",
    baseUrl: "https://YOUR_RESOURCE.openai.azure.com/openai/v1",
    model: "gpt-4o-mini",
    priority: 130,
    weight: 1,
  },
  openrouter: {
    type: "openai_compatible",
    name: "OpenRouter",
    baseUrl: "https://openrouter.ai/api/v1",
    model: "openai/gpt-4o-mini",
    priority: 140,
    weight: 1,
  },
  deepseek: {
    type: "openai_compatible",
    name: "DeepSeek",
    baseUrl: "https://api.deepseek.com/v1",
    model: "deepseek-chat",
    priority: 140,
    weight: 1,
  },
  moonshot: {
    type: "openai_compatible",
    name: "Moonshot",
    baseUrl: "https://api.moonshot.cn/v1",
    model: "moonshot-v1-8k",
    priority: 140,
    weight: 1,
  },
  siliconflow: {
    type: "openai_compatible",
    name: "SiliconFlow",
    baseUrl: "https://api.siliconflow.cn/v1",
    model: "Qwen/Qwen2.5-7B-Instruct",
    priority: 140,
    weight: 1,
  },
};

const pageCopyKeys = {
  diagnostics: ["pageDiagnosticsTitle", "pageDiagnosticsSubtitle"],
  documents: ["pageDocumentsTitle", "pageDocumentsSubtitle"],
  ask: ["pageAskTitle", "pageAskSubtitle"],
  "llm-access": ["pageLlmAccessTitle", "pageLlmAccessSubtitle"],
  evaluations: ["pageEvaluationsTitle", "pageEvaluationsSubtitle"],
  settings: ["pageSettingsTitle", "pageSettingsSubtitle"],
};

let language = localStorage.getItem(LANGUAGE_KEY) || "zh";
let currentPage = normalizedPage(location.hash.slice(1) || localStorage.getItem(PAGE_KEY));
let oauthPollTimer = null;
let oauthPopup = null;
let completingCodexOAuth = false;

function t(key, replacements = {}) {
  const template = translations[language][key] ?? translations.en[key] ?? key;
  return Object.entries(replacements).reduce(
    (text, [name, value]) => text.replaceAll(`{${name}}`, String(value)),
    template,
  );
}

function statLabels() {
  return {
    indexed_chunks: t("indexedChunks"),
    indexed_documents: t("documents"),
    index_updated_at: t("updated"),
    index_file: t("indexFile"),
    chunk_size: t("chunkSize"),
    chunk_overlap: t("overlap"),
    top_k: t("topK"),
    vector_weight: t("vectorWeight"),
  };
}

function providerLabels() {
  return {
    embedding_provider: t("embeddingProvider"),
    embedding_dimensions: t("embeddingDimensions"),
    embedding_model: t("embeddingModel"),
    generation_provider: t("generationProvider"),
    generation_model: t("generationModel"),
    generation_context_chars: t("contextChars"),
  };
}

async function api(path, options = {}) {
  const response = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  const contentType = response.headers.get("content-type") || "";
  const data = contentType.includes("application/json")
    ? await response.json()
    : { detail: await response.text() };
  if (!response.ok) {
    throw new Error(data.detail || "Request failed");
  }
  return data;
}

function setStatus(message, tone = "info") {
  statusBar.textContent = message;
  statusBar.className = `status ${tone}`;
}

function applyTranslations() {
  document.documentElement.lang = language === "zh" ? "zh-CN" : "en";
  document.querySelectorAll("[data-i18n]").forEach((element) => {
    element.textContent = t(element.dataset.i18n);
  });
  document.querySelectorAll("[data-i18n-placeholder]").forEach((element) => {
    element.placeholder = t(element.dataset.i18nPlaceholder);
  });
  languageToggle.textContent = t("languageToggle");
  updatePageCopy();
}

function normalizedPage(page) {
  return pageCopyKeys[page] ? page : "diagnostics";
}

function showPage(page) {
  currentPage = normalizedPage(page);
  localStorage.setItem(PAGE_KEY, currentPage);
  document.querySelectorAll("[data-page-section]").forEach((section) => {
    section.classList.toggle("page-hidden", section.dataset.pageSection !== currentPage);
  });
  document.querySelectorAll("nav a[data-page]").forEach((link) => {
    link.classList.toggle("active", link.dataset.page === currentPage);
  });
  if (location.hash !== `#${currentPage}`) {
    history.replaceState(null, "", `#${currentPage}`);
  }
  updatePageCopy();
}

function updatePageCopy() {
  const [titleKey, subtitleKey] = pageCopyKeys[currentPage];
  pageTitle.textContent = t(titleKey);
  pageSubtitle.textContent = t(subtitleKey);
}

function renderKeyValues(container, labels, data) {
  container.innerHTML = "";
  Object.entries(labels).forEach(([key, label]) => {
    const wrapper = document.createElement("div");
    const term = document.createElement("dt");
    const value = document.createElement("dd");
    term.textContent = label;
    value.textContent = data[key] ?? t("local");
    wrapper.append(term, value);
    container.append(wrapper);
  });
}

async function refreshStats({ announce = true } = {}) {
  const stats = await api("/api/stats");
  renderKeyValues(statsGrid, statLabels(), stats);
  renderKeyValues(providerList, providerLabels(), stats);
  indexBadge.textContent = `${stats.indexed_chunks} ${t("chunks")}`;
  indexBadge.classList.toggle("ok", stats.indexed_chunks > 0);
  await refreshDocuments();
  await refreshEvalHistory();
  await refreshLlmAccess();
  if (announce) {
    setStatus(t("statusRefreshed"), "ok");
  }
}

async function refreshDocuments() {
  const [result, sources] = await Promise.all([
    api("/api/documents"),
    api("/api/document-sources"),
  ]);
  renderDocumentSources(sources.sources);
  documentsList.innerHTML = "";
  if (result.documents.length === 0) {
    documentsList.textContent = t("noIndexedDocuments");
    return;
  }
  result.documents.forEach((doc) => {
    const item = document.createElement("div");
    const title = document.createElement("div");
    const meta = document.createElement("div");
    const controls = document.createElement("div");
    item.className = "document-item";
    title.className = "document-title";
    meta.className = "document-meta";
    controls.className = "document-controls";
    title.textContent = doc.filename;
    meta.textContent = `${doc.chunk_count} ${t("chunks")} | ${doc.type} | ${doc.path}`;
    controls.append(
      sourceButton(t("reindexSource"), () => reindexIndexedDocument(doc.id)),
      sourceButton(t("delete"), () => deleteIndexedDocument(doc.id), "danger"),
    );
    item.append(title, meta, controls);
    documentsList.append(item);
  });
}

function renderDocumentSources(sources) {
  documentSourcesList.innerHTML = "";
  if (!sources.length) {
    const empty = document.createElement("div");
    empty.className = "empty-accounts compact-empty";
    empty.textContent = t("noSavedSources");
    documentSourcesList.append(empty);
    return;
  }
  sources.forEach((source) => {
    const item = document.createElement("div");
    const meta = document.createElement("div");
    const title = document.createElement("strong");
    const path = document.createElement("span");
    const stats = document.createElement("span");
    const controls = document.createElement("div");
    item.className = "source-item";
    meta.className = "source-meta";
    controls.className = "source-controls";
    title.textContent = source.label;
    path.textContent = source.path;
    stats.textContent = t("sourceChunks", { count: source.last_chunk_count || 0 });
    meta.append(title, path, stats);
    controls.append(
      sourceButton(t("useSource"), () => {
        document.querySelector("#sourcePath").value = source.path;
        setStatus(t("statusRefreshed"), "ok");
      }),
      sourceButton(t("reindexSource"), () => reindexDocumentSource(source.id)),
      sourceButton(t("delete"), () => deleteDocumentSource(source.id), "danger"),
    );
    item.append(meta, controls);
    documentSourcesList.append(item);
  });
}

function sourceButton(label, handler, tone = "neutral") {
  const button = document.createElement("button");
  button.type = "button";
  button.className = `secondary ${tone}`;
  button.textContent = label;
  button.addEventListener("click", async () => {
    try {
      await handler();
    } catch (error) {
      const message = error instanceof Error ? error.message : String(error);
      setStatus(message, "error");
    }
  });
  return button;
}

async function rebuildIndex() {
  setStatus(t("indexingDocuments"), "info");
  const source = document.querySelector("#sourcePath").value;
  const result = await api("/api/index", {
    method: "POST",
    body: JSON.stringify({ source }),
  });
  setStatus(t("indexedResult", { count: result.chunk_count, provider: result.embedding_provider }), "ok");
  await refreshStats({ announce: false });
}

async function saveDocumentSource() {
  const source = document.querySelector("#sourcePath").value.trim();
  if (!source) {
    setStatus(t("baseUrlRequired"), "error");
    return;
  }
  await api("/api/document-sources", {
    method: "POST",
    body: JSON.stringify({ path: source }),
  });
  setStatus(t("sourceSaved"), "ok");
  await refreshDocuments();
}

async function reindexDocumentSource(sourceId) {
  setStatus(t("indexingDocuments"), "info");
  const result = await api(`/api/document-sources/${sourceId}/index`, { method: "POST" });
  setStatus(t("sourceReindexed", { count: result.index.chunk_count }), "ok");
  await refreshStats({ announce: false });
}

async function deleteDocumentSource(sourceId) {
  await api(`/api/document-sources/${sourceId}`, { method: "DELETE" });
  setStatus(t("sourceDeleted"), "ok");
  await refreshDocuments();
}

async function reindexIndexedDocument(documentId) {
  setStatus(t("indexingDocuments"), "info");
  const result = await api(`/api/documents/${documentId}/index`, { method: "POST" });
  setStatus(t("documentReindexed", { count: result.chunk_count }), "ok");
  await refreshStats({ announce: false });
}

async function deleteIndexedDocument(documentId) {
  await api(`/api/documents/${documentId}`, { method: "DELETE" });
  setStatus(t("documentDeleted"), "ok");
  await refreshStats({ announce: false });
}

async function askQuestion() {
  const question = document.querySelector("#questionInput").value.trim();
  if (!question) {
    setStatus(t("emptyQuestion"), "error");
    return;
  }
  appendChatMessage({ role: "user", content: question });
  const pending = appendChatMessage({
    role: "assistant",
    content: t("assistantThinking"),
    pending: true,
  });
  document.querySelector("#questionInput").value = "";
  setStatus(t("retrievingContext"), "info");
  const result = await api("/api/ask", {
    method: "POST",
    body: JSON.stringify({ question }),
  });
  updateAssistantMessage(pending, result.answer, result.sources);
  setStatus(t("answeredWithSources", { count: result.sources.length }), "ok");
}

function appendChatMessage({ role, content, sources = [], pending = false }) {
  const message = document.createElement("article");
  const avatar = document.createElement("div");
  const body = document.createElement("div");
  const text = document.createElement("div");
  message.className = `chat-message ${role}${pending ? " pending" : ""}`;
  avatar.className = "chat-avatar";
  body.className = "chat-bubble";
  text.className = "chat-text";
  avatar.textContent = role === "user" ? "U" : "AI";
  text.textContent = content;
  body.append(text);
  message.append(avatar, body);
  chatThread.append(message);
  renderMessageSources(body, sources);
  chatThread.scrollTop = chatThread.scrollHeight;
  return message;
}

function updateAssistantMessage(message, content, sources) {
  message.classList.remove("pending");
  const body = message.querySelector(".chat-bubble");
  const text = message.querySelector(".chat-text");
  text.textContent = content;
  renderMessageSources(body, sources);
  chatThread.scrollTop = chatThread.scrollHeight;
}

function renderMessageSources(body, sources = []) {
  body.querySelector(".chat-sources")?.remove();
  if (!sources.length) {
    return;
  }
  const details = document.createElement("details");
  const summary = document.createElement("summary");
  const list = document.createElement("div");
  details.className = "chat-sources";
  list.className = "sources";
  summary.textContent = t("sourceCount", { count: sources.length });
  sources.forEach((source) => {
    const item = document.createElement("div");
    const title = document.createElement("div");
    const sourceLabel = document.createElement("span");
    const score = document.createElement("span");
    const preview = document.createElement("div");
    title.className = "source-title";
    preview.className = "source-preview";
    sourceLabel.textContent = `${source.filename}#${source.chunk_index}`;
    score.textContent = source.score;
    title.append(sourceLabel, score);
    preview.textContent = source.preview;
    item.append(title, preview);
    list.append(item);
  });
  details.append(summary, list);
  body.append(details);
}

async function runEvaluation() {
  evalBox.textContent = t("runningEval");
  setStatus(t("runningEval"), "info");
  const questionsPath = document.querySelector("#questionsPath").value;
  const result = await api("/api/eval", {
    method: "POST",
    body: JSON.stringify({ questions_path: questionsPath }),
  });
  evalBox.textContent = JSON.stringify(result.metrics, null, 2);
  setStatus(t("evalComplete", { rate: result.metrics.retrieval_hit_rate }), "ok");
  await refreshEvalHistory();
}

async function refreshEvalHistory() {
  const result = await api("/api/eval/results");
  evalHistoryList.innerHTML = "";
  const title = document.createElement("h3");
  title.textContent = t("evalHistory");
  evalHistoryList.append(title);
  if (!result.results.length) {
    const empty = document.createElement("div");
    empty.className = "empty-accounts compact-empty";
    empty.textContent = t("noEvalHistory");
    evalHistoryList.append(empty);
    return;
  }
  result.results.slice(0, 8).forEach((item) => {
    const row = document.createElement("div");
    const name = document.createElement("strong");
    const meta = document.createElement("span");
    const comparison = document.createElement("span");
    row.className = "eval-history-item";
    name.textContent = item.filename;
    meta.textContent =
      `hit ${item.retrieval_hit_rate} | ${item.case_count} cases | ${item.average_latency_seconds}s`;
    row.append(name, meta);
    if (item.comparison) {
      comparison.className = "eval-comparison";
      comparison.textContent =
        `${t("evalComparison")}: hit ${formatDelta(item.comparison.retrieval_hit_rate_delta)} | ` +
        `latency ${formatDelta(item.comparison.average_latency_seconds_delta)}s | ` +
        `cases ${formatDelta(item.comparison.case_count_delta)}`;
      row.append(comparison);
    }
    evalHistoryList.append(row);
  });
}

function formatDelta(value) {
  const number = Number(value || 0);
  return number > 0 ? `+${number}` : `${number}`;
}

async function refreshLlmAccess() {
  const [providers, accounts, fuelPool] = await Promise.all([
    api("/api/llm/providers"),
    api("/api/llm/accounts"),
    api("/api/fuel-pool"),
  ]);
  renderProviderOptions(providers.providers);
  renderLlmAccounts(accounts.accounts);
  renderFuelPool(fuelPool);
  const usage = accounts.usage;
  llmUsageBadge.textContent =
    usage.request_count > 0
      ? t("callsTokens", { calls: usage.request_count, tokens: usage.total_tokens })
      : t("noTrackedCalls");
  llmUsageBadge.classList.toggle("ok", usage.success_count > 0);
}

function renderFuelPool(fuelPool) {
  const selected = fuelPool.status.strategy;
  fuelStrategy.innerHTML = "";
  fuelPool.status.strategies.forEach((strategy) => {
    const option = document.createElement("option");
    option.value = strategy.id;
    option.textContent = t(strategyKeys[strategy.id]) || strategy.label;
    fuelStrategy.append(option);
  });
  fuelStrategy.value = selected;
}

function renderProviderOptions(providers) {
  const selected = llmProviderType.value || "local_relay";
  llmProviderType.innerHTML = "";
  providers.forEach((provider) => {
    const option = document.createElement("option");
    option.value = provider.id;
    option.textContent = t(providerTypeKeys[provider.id]) || provider.label;
    llmProviderType.append(option);
  });
  llmProviderType.value = selected;
}

function renderLlmAccounts(accounts) {
  llmAccountsList.innerHTML = "";
  if (accounts.length === 0) {
    const empty = document.createElement("div");
    empty.className = "empty-accounts";
    empty.textContent = t("noLlmAccounts");
    llmAccountsList.append(empty);
    return;
  }
  accounts.forEach((account) => {
    const item = document.createElement("div");
    const head = document.createElement("div");
    const title = document.createElement("strong");
    const state = document.createElement("span");
    const meta = document.createElement("dl");
    const controls = document.createElement("div");
    item.className = "llm-account";
    head.className = "llm-account-head";
    meta.className = "account-meta-grid";
    controls.className = "llm-controls";
    title.textContent = account.name;
    state.textContent = account.enabled ? t("enabled") : t("paused");
    state.className = account.enabled ? "state enabled" : "state paused";
    head.append(title, state);
    appendAccountMeta(meta, t("providerType"), t(providerTypeKeys[account.provider_type]));
    appendAccountMeta(meta, t("model"), account.model);
    appendAccountMeta(meta, t("upstreamBaseUrl"), account.base_url);
    appendAccountMeta(meta, t("key"), account.api_key_masked || t("keyNone"));
    appendAccountMeta(
      meta,
      t("refreshCredentials"),
      account.has_refresh_credentials ? t("available") : t("unavailable"),
    );
    appendAccountMeta(meta, t("priority"), account.priority);
    appendAccountMeta(meta, t("weight"), account.weight);
    controls.append(
      accountButton(t("test"), () => testLlmAccount(account.id)),
      accountButton(account.enabled ? t("disable") : t("enable"), () =>
        updateLlmAccount(account.id, { enabled: !account.enabled }),
      ),
      accountButton(t("delete"), () => deleteLlmAccount(account.id), "danger"),
    );
    item.append(head, meta, controls);
    if (account.last_error) {
      const error = document.createElement("div");
      error.className = "inline-error";
      error.textContent = `${t("error")}: ${account.last_error}`;
      item.append(error);
    }
    llmAccountsList.append(item);
  });
}

function appendAccountMeta(container, label, value) {
  const group = document.createElement("div");
  const term = document.createElement("dt");
  const description = document.createElement("dd");
  term.textContent = label;
  description.textContent = value;
  group.append(term, description);
  container.append(group);
}

function accountButton(label, handler, tone = "neutral") {
  const button = document.createElement("button");
  button.type = "button";
  button.textContent = label;
  button.className = `secondary ${tone}`;
  button.addEventListener("click", async () => {
    try {
      await handler();
      await refreshStats({ announce: false });
    } catch (error) {
      const message = error instanceof Error ? error.message : String(error);
      setStatus(message, "error");
    }
  });
  return button;
}

async function saveLlmAccount(event) {
  event.preventDefault();
  const baseUrl = document.querySelector("#llmBaseUrl").value.trim();
  if (!baseUrl) {
    setStatus(t("baseUrlRequired"), "error");
    return;
  }
  setStatus(t("savingLlmAccount"), "info");
  const payload = {
    name: document.querySelector("#llmName").value,
    provider_type: llmProviderType.value,
    base_url: baseUrl,
    model: document.querySelector("#llmModel").value,
    api_key: document.querySelector("#llmApiKey").value,
    enabled: document.querySelector("#llmEnabled").checked,
    priority: Number(document.querySelector("#llmPriority").value),
    weight: Number(document.querySelector("#llmWeight").value),
  };
  await createLlmAccount(payload);
  document.querySelector("#llmApiKey").value = "";
  closeImportModal();
  setStatus(t("llmAccountConnected"), "ok");
  await refreshStats({ announce: false });
}

function openImportModal(type = "local_relay") {
  applyImportPreset(type);
  importModal.classList.remove("hidden");
  startCodexOAuth().catch((error) => {
    setStatus(error instanceof Error ? error.message : String(error), "error");
  });
  document.querySelector("#oauthLink").focus();
}

function closeImportModal() {
  importModal.classList.add("hidden");
  stopCodexOAuthPolling();
}

function applyImportPreset(type) {
  if (!importPresets[type]) {
    return;
  }
  const preset = importPresets[type];
  document.querySelectorAll(".import-option").forEach((button) => {
    button.classList.toggle("active", button.dataset.importType === type);
  });
  llmProviderType.value = type;
  document.querySelector("#llmName").value = preset.name;
  document.querySelector("#llmBaseUrl").value = preset.baseUrl;
  document.querySelector("#llmModel").value = preset.model;
  document.querySelector("#llmPriority").value = preset.priority;
  document.querySelector("#llmWeight").value = preset.weight;
  document.querySelector("#llmEnabled").checked = preset.enabled ?? true;
}

function showImportTab(tab) {
  document.querySelectorAll(".import-tab").forEach((button) => {
    button.classList.toggle("active", button.dataset.importTab === tab);
  });
  document.querySelectorAll(".import-pane").forEach((pane) => {
    pane.classList.toggle("active", pane.dataset.importPane === tab);
  });
  if (tab === "api_key") {
    applyProviderPreset("cockpit");
  }
  if (tab === "oauth" && !currentCodexOAuth) {
    startCodexOAuth().catch((error) => {
      setStatus(error instanceof Error ? error.message : String(error), "error");
    });
  }
}

function applyProviderPreset(key) {
  const preset = providerPresets[key];
  if (!preset) {
    return;
  }
  document.querySelectorAll(".provider-chip").forEach((button) => {
    button.classList.toggle("active", button.dataset.providerPreset === key);
  });
  llmProviderType.value = preset.type;
  document.querySelector("#llmName").value = preset.name;
  document.querySelector("#llmBaseUrl").value = preset.baseUrl;
  document.querySelector("#llmModel").value = preset.model;
  document.querySelector("#llmPriority").value = preset.priority;
  document.querySelector("#llmWeight").value = preset.weight;
  document.querySelector("#llmEnabled").checked = preset.enabled ?? true;
}

function extractTokenPayload(raw) {
  const trimmed = raw.trim();
  if (!trimmed) {
    return null;
  }
  let parsed = null;
  try {
    parsed = JSON.parse(trimmed);
  } catch {
    parsed = null;
  }
  if (!parsed) {
    return {
      apiKey: trimmed,
      name: "Token import",
      baseUrl: "https://chatgpt.com/backend-api/codex",
      model: "gpt-5.4",
    };
  }
  const token =
    parsed.accessToken ||
    parsed.access_token ||
    parsed.refreshToken ||
    parsed.refresh_token ||
    parsed.apiKey ||
    parsed.api_key ||
    parsed.key ||
    parsed.token ||
    parsed?.tokens?.access_token ||
    parsed?.tokens?.refresh_token ||
    parsed?.auth?.accessToken ||
    parsed?.auth?.access_token ||
    parsed?.auth?.refreshToken ||
    parsed?.auth?.refresh_token;
  if (!token) {
    return null;
  }
  return {
    apiKey: token,
    name: parsed.name || parsed.email || parsed.account || "Token import",
    baseUrl: parsed.base_url || parsed.baseUrl || "https://chatgpt.com/backend-api/codex",
    hasExplicitBaseUrl: Boolean(parsed.base_url || parsed.baseUrl),
    model: parsed.model || "gpt-5.4",
  };
}

async function importTokenJson() {
  if (!extractTokenPayload(tokenJsonInput.value)) {
    setStatus(t("tokenMissing"), "error");
    return;
  }
  await api("/api/llm/import-token", {
    method: "POST",
    body: JSON.stringify({ payload: tokenJsonInput.value }),
  });
  tokenJsonInput.value = "";
  closeImportModal();
  setStatus(t("tokenImported"), "ok");
  await refreshStats({ announce: false });
}

async function importExternalAccount() {
  const payload = externalImportPayload.value.trim();
  const url = externalImportUrl.value.trim();
  if (!payload && !url) {
    setStatus(t("externalImportMissing"), "error");
    return;
  }
  const result = await api("/api/llm/import-external", {
    method: "POST",
    body: JSON.stringify({
      source: url ? "url" : "json",
      payload: payload || null,
      url: url || null,
      provider_type: externalImportProvider.value,
    }),
  });
  externalImportPayload.value = "";
  externalImportUrl.value = "";
  closeImportModal();
  setStatus(t("externalImportDone", { count: result.count }), "ok");
  await refreshStats({ announce: false });
}

async function loadExternalImportFile() {
  const file = externalImportFile.files?.[0];
  if (!file) {
    return;
  }
  externalImportPayload.value = await file.text();
  externalImportUrl.value = "";
  externalImportFile.value = "";
}

async function createLlmAccount(payload) {
  await api("/api/llm/accounts", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

function extractTokenFromCallback(callbackUrl) {
  const match = callbackUrl.match(/[?#&](access_token|accessToken|token)=([^&#]+)/);
  return match ? decodeURIComponent(match[2]) : "";
}

async function startCodexOAuth() {
  setStatus(t("oauthWaiting"), "info");
  const result = await api("/api/oauth/codex/start", { method: "POST" });
  currentCodexOAuth = result.oauth;
  document.querySelector("#oauthLink").value = currentCodexOAuth.auth_url;
  startCodexOAuthPolling();
  setStatus(t("oauthStarted"), "ok");
}

function startCodexOAuthPolling() {
  stopCodexOAuthPolling();
  oauthPollTimer = window.setInterval(() => {
    if (!currentCodexOAuth?.login_id) {
      stopCodexOAuthPolling();
      return;
    }
    completeCodexOAuth({ auto: true }).catch((error) => {
      stopCodexOAuthPolling();
      const message = error instanceof Error ? error.message : String(error);
      setStatus(message, "error");
    });
  }, 1500);
}

function stopCodexOAuthPolling() {
  if (oauthPollTimer) {
    window.clearInterval(oauthPollTimer);
    oauthPollTimer = null;
  }
}

function closeOauthPopup() {
  try {
    if (oauthPopup && !oauthPopup.closed) {
      oauthPopup.close();
    }
  } catch {
    // The popup may be cross-origin while the auth page is open.
  }
  oauthPopup = null;
}

async function completeCodexOAuth({ auto = false } = {}) {
  if (completingCodexOAuth) {
    return false;
  }
  if (!currentCodexOAuth?.login_id) {
    await startCodexOAuth();
  }
  completingCodexOAuth = true;
  try {
    const callbackUrl = auto ? "" : document.querySelector("#oauthCallbackUrl").value.trim();
    if (callbackUrl) {
      const callbackResult = await api("/api/oauth/codex/callback-url", {
        method: "POST",
        body: JSON.stringify({
          login_id: currentCodexOAuth.login_id,
          callback_url: callbackUrl,
        }),
      });
      currentCodexOAuth = callbackResult.oauth;
    } else {
      const statusResult = await api("/api/oauth/codex/status");
      if (!statusResult.oauth) {
        currentCodexOAuth = null;
        stopCodexOAuthPolling();
        setStatus(t("oauthExpired"), "error");
        return false;
      }
      currentCodexOAuth = statusResult.oauth;
    }
    if (!currentCodexOAuth?.has_callback_code) {
      if (!auto) {
        setStatus(t("oauthWaiting"), "info");
      }
      return false;
    }
    const result = await api("/api/oauth/codex/complete", {
      method: "POST",
      body: JSON.stringify({ login_id: currentCodexOAuth.login_id }),
    });
    currentCodexOAuth = null;
    document.querySelector("#oauthCallbackUrl").value = "";
    stopCodexOAuthPolling();
    closeOauthPopup();
    closeImportModal();
    setStatus(`${t("oauthCompleted")}: ${result.account.api_key_masked}`, "ok");
    await refreshStats({ announce: false });
    return true;
  } finally {
    completingCodexOAuth = false;
  }
}

async function updateLlmAccount(accountId, payload) {
  await api(`/api/llm/accounts/${accountId}`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
  setStatus(t("llmAccountUpdated"), "ok");
}

async function deleteLlmAccount(accountId) {
  await api(`/api/llm/accounts/${accountId}`, { method: "DELETE" });
  setStatus(t("llmAccountDeleted"), "ok");
}

async function testLlmAccount(accountId) {
  setStatus(t("testingLlmAccount"), "info");
  const result = await api(`/api/llm/accounts/${accountId}/test`, { method: "POST" });
  setStatus(result.result.message, result.result.ok ? "ok" : "error");
}

async function updateFuelStrategy() {
  await api("/api/fuel-pool", {
    method: "PATCH",
    body: JSON.stringify({ strategy: fuelStrategy.value }),
  });
  setStatus(t("fuelStrategyUpdated"), "ok");
}

function bind(id, handler) {
  document.querySelector(id).addEventListener("click", async () => {
    try {
      await handler();
    } catch (error) {
      const message = error instanceof Error ? error.message : String(error);
      setStatus(message, "error");
    }
  });
}

document.querySelectorAll("nav a[data-page]").forEach((link) => {
  link.addEventListener("click", (event) => {
    event.preventDefault();
    showPage(link.dataset.page);
  });
});

languageToggle.addEventListener("click", async () => {
  language = language === "zh" ? "en" : "zh";
  localStorage.setItem(LANGUAGE_KEY, language);
  applyTranslations();
  await refreshStats({ announce: false });
  setStatus(t("statusRefreshed"), "ok");
});

bind("#refreshStats", refreshStats);
bind("#indexButton", rebuildIndex);
bind("#saveSourceButton", saveDocumentSource);
chatForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  try {
    await askQuestion();
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    appendChatMessage({ role: "assistant", content: message });
    setStatus(message, "error");
  }
});
bind("#evalButton", runEvaluation);
openImportModalButton.addEventListener("click", () => openImportModal());
closeImportModalButton.addEventListener("click", closeImportModal);
document.querySelectorAll(".import-tab").forEach((button) => {
  button.addEventListener("click", () => showImportTab(button.dataset.importTab));
});
document.querySelectorAll(".provider-chip").forEach((button) => {
  button.addEventListener("click", () => applyProviderPreset(button.dataset.providerPreset));
});
bind("#copyOauthLink", async () => {
  const value = document.querySelector("#oauthLink").value;
  if (navigator.clipboard) {
    await navigator.clipboard.writeText(value);
  } else {
    document.querySelector("#oauthLink").select();
    document.execCommand("copy");
  }
  setStatus(t("copied"), "ok");
});
bind("#openOauthLink", () => {
  oauthPopup = window.open(
    document.querySelector("#oauthLink").value,
    "aiKnowledgeAgentOAuth",
    "popup,width=1040,height=820",
  );
  startCodexOAuthPolling();
  setStatus(t("oauthAutoWaiting"), "info");
});
bind("#oauthContinue", completeCodexOAuth);
bind("#importTokenJson", importTokenJson);
bind("#chooseExternalImportFile", () => externalImportFile.click());
bind("#importExternalAccount", importExternalAccount);
externalImportFile.addEventListener("change", async () => {
  try {
    await loadExternalImportFile();
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    setStatus(message, "error");
  }
});
importModal.addEventListener("click", (event) => {
  if (event.target === importModal) {
    closeImportModal();
  }
});
document.querySelectorAll(".import-option:not(.disabled)").forEach((button) => {
  button.addEventListener("click", () => applyImportPreset(button.dataset.importType));
});
document.addEventListener("keydown", (event) => {
  if (event.key === "Escape" && !importModal.classList.contains("hidden")) {
    closeImportModal();
  }
});
window.addEventListener("message", (event) => {
  if (event.data?.type !== "ai-knowledge-agent.oauth-callback") {
    return;
  }
  completeCodexOAuth({ auto: true }).catch((error) => {
    const message = error instanceof Error ? error.message : String(error);
    setStatus(message, "error");
  });
});
fuelStrategy.addEventListener("change", async () => {
  try {
    await updateFuelStrategy();
    await refreshStats({ announce: false });
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    setStatus(message, "error");
  }
});
document.querySelector("#llmAccountForm").addEventListener("submit", saveLlmAccount);

applyTranslations();
showPage(currentPage);
refreshStats().catch((error) => {
  indexBadge.textContent = t("error");
  setStatus(error instanceof Error ? error.message : String(error), "error");
});

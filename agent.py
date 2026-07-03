#!/usr/bin/env python3
"""我的专属 AI 智能体 v2.0 — 写周报/学知识/改代码 + 流式输出/知识库/对话历史"""

import json
import os
import re
import time
import uuid
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

# ── 路径配置 ──────────────────────────────────────────────
HERE = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(HERE, "data")
KB_DIR = os.path.join(DATA_DIR, "knowledge_base")
CHAT_DIR = os.path.join(DATA_DIR, "chats")

os.makedirs(KB_DIR, exist_ok=True)
os.makedirs(CHAT_DIR, exist_ok=True)


# ── .env 加载 ─────────────────────────────────────────────
def load_dotenv(path):
    """从 .env 文件加载环境变量，已存在的变量不会被覆盖。"""
    if not os.path.exists(path):
        return
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, val = line.partition("=")
            key, val = key.strip(), val.strip()
            if key not in os.environ:
                os.environ[key] = val


load_dotenv(os.path.join(HERE, ".env"))


# ── 预设模型配置 ──────────────────────────────────────────
PRESETS = {
    "agnes": {"base_url": "https://apihub.agnes-ai.com/v1", "model": "agnes-2.0-flash"},
    "deepseek": {"base_url": "https://api.deepseek.com", "model": "deepseek-chat"},
    "qwen": {"base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1", "model": "qwen-plus"},
    "glm": {"base_url": "https://open.bigmodel.cn/api/paas/v4", "model": "glm-4"},
    "moonshot": {"base_url": "https://api.moonshot.cn/v1", "model": "moonshot-v1-8k"},
    "openai": {"base_url": "https://api.openai.com/v1", "model": "gpt-4o"},
    "ollama": {"base_url": "http://localhost:11434/v1", "model": "qwen2.5:7b"},
}


# ── 系统提示词 ────────────────────────────────────────────
SYSTEM_PROMPTS = {
    "weekly": """你是一位专业的周报助手。你的任务是根据用户提供的关键词，生成结构完整、内容详实的周报。

【周报模板】
# 周报 - [日期]

## 本周工作完成情况
- [项目/任务名称]：详细描述完成的工作内容、达成的目标、关键数据

## 工作中遇到的问题与解决方案
- 问题描述：具体问题、影响范围
- 解决方案：采取的措施、最终结果

## 下周工作计划
- [计划1]：详细描述计划内容和预期目标
- [计划2]：详细描述计划内容和预期目标

## 其他事项
- 需要支持的资源
- 风险提示

【写作要求】
1. 根据用户提供的关键词展开，每个关键词对应一个工作项
2. 语言正式但不生硬，条理清晰
3. 突出工作成果和价值，使用具体数据说明
4. 如果关键词不够具体，可以合理补充相关内容
5. 不要编造不存在的工作内容""",

    "learn": """你是一位专业的知识整理助手。你的任务是根据用户提供的学习主题，整理出结构化的学习笔记。

【学习笔记模板】
# 学习笔记：[主题名称]

## 一、核心概念
- 概念定义：清晰准确的定义
- 重要性说明：为什么需要学习这个知识

## 二、关键知识点
1. [知识点1]：详细解释，包括原理、特点、使用场景
2. [知识点2]：详细解释，包括原理、特点、使用场景
3. [知识点3]：详细解释，包括原理、特点、使用场景

## 三、实践案例
- 案例描述：实际应用场景
- 代码示例（如适用）：可运行的代码片段
- 分析与总结：案例的关键点和启示

## 四、学习资源
- [资源链接1]：资源名称和简要介绍
- [资源链接2]：资源名称和简要介绍

## 五、思考与感悟
- 学习收获：学到的核心内容
- 待深入研究的问题：需要进一步学习的方向

【写作要求】
1. 结构清晰，层次分明
2. 内容准确，引用权威资料
3. 语言通俗易懂，避免过于专业的术语堆砌
4. 提供实用的代码示例和资源链接
5. 结合实际应用场景进行讲解""",

    "code": """你是一位资深的代码优化专家。你的任务是分析用户提供的代码，找出问题并给出优化方案。

【代码分析维度】
- 代码质量：命名规范、可读性、注释完整性
- 潜在问题：逻辑错误、边界条件处理、空值检查
- 性能优化：算法复杂度、资源使用、缓存策略
- 最佳实践：设计模式、代码复用、架构合理性
- 安全性：输入验证、敏感信息处理、SQL注入防护

【优化方案输出格式】
# 代码优化报告

## 一、问题分析

### 🔴 严重问题（需立即修复）
1. [问题描述]
   - 影响：XXX
   - 位置：第X行

### 🟡 中等问题（建议修复）
1. [问题描述]
   - 影响：XXX
   - 位置：第X行

### 🟢 改进建议（可选优化）
1. [建议描述]
   - 理由：XXX

## 二、优化后代码

```[语言]
// 优化后的代码
```

## 三、优化效果总结
- 性能提升：XX%
- 代码行数：减少/增加XX行
- 可读性：显著提升

【分析要求】
1. 代码分析要全面，不要遗漏重要问题
2. 优化建议要具体，提供可操作的改进方案
3. 优化后的代码要保持功能不变
4. 解释优化的原因和预期效果
5. 遵循最佳实践和行业标准""",
}


# ── 快捷模板 ──────────────────────────────────────────────
TEMPLATES = {
    "weekly": [
        "AI项目开发、模型训练、Bug修复",
        "产品需求评审、UI设计、前端开发",
        "数据分析、报告撰写、会议汇报",
    ],
    "learn": [
        "Python 异步编程",
        "React Hooks 深入理解",
        "机器学习基础概念",
    ],
    "code": [
        "优化这段 Python 代码的性能",
        "帮我 review 这个 JavaScript 函数",
        "这段代码有什么安全问题吗",
    ],
}


# ── 知识库缓存 ────────────────────────────────────────────
_kb_cache = None
_kb_cache_mtime = 0


def _kb_cache_valid():
    """检查知识库缓存是否有效（基于目录修改时间）。"""
    global _kb_cache_mtime
    try:
        mtime = os.path.getmtime(KB_DIR)
        if _kb_cache is not None and mtime == _kb_cache_mtime:
            return True
        _kb_cache_mtime = mtime
    except OSError:
        pass
    return False


def load_knowledge_base():
    """加载知识库，带缓存机制。"""
    global _kb_cache
    if _kb_cache is not None and _kb_cache_valid():
        return _kb_cache

    docs = []
    try:
        for fname in os.listdir(KB_DIR):
            if not (fname.endswith(".txt") or fname.endswith(".md")):
                continue
            fpath = os.path.join(KB_DIR, fname)
            with open(fpath, "r", encoding="utf-8") as f:
                content = f.read()
            # 按 500 字符分块，重叠 100 字符
            chunk_size, overlap = 500, 100
            for i in range(0, len(content), chunk_size - overlap):
                chunk = content[i:i + chunk_size]
                if len(chunk) < 50:
                    continue
                docs.append({
                    "id": f"{fname}_{i // (chunk_size - overlap)}",
                    "title": fname,
                    "content": chunk,
                })
    except OSError:
        pass

    _kb_cache = docs
    return docs


def search_knowledge_base(query, docs, top_k=3):
    """基于关键词匹配搜索知识库。"""
    if not docs or not query:
        return []

    query_words = set(re.findall(r"[\w\u4e00-\u9fff]+", query.lower()))
    if not query_words:
        return []

    scored = []
    for doc in docs:
        content_words = set(re.findall(r"[\w\u4e00-\u9fff]+", doc["content"].lower()))
        score = len(query_words & content_words)
        if score > 0:
            scored.append((score, doc))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [doc for _, doc in scored[:top_k]]


# ── 联网搜索 ──────────────────────────────────────────────
def web_search(query, max_results=5):
    """通过百度搜索获取网页内容摘要。"""
    results = []
    try:
        url = "https://www.baidu.com/s?wd=" + urllib.parse.quote(query)
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"},
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            html = resp.read().decode("utf-8", errors="ignore")

        urls = re.findall(r'href="(https?://[^"]+)"', html)
        valid_urls = [u for u in urls if "baidu.com" not in u and len(u) > 30][:max_results + 3]

        for target_url in valid_urls:
            if len(results) >= max_results:
                break
            try:
                page_req = urllib.request.Request(
                    target_url,
                    headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"},
                )
                with urllib.request.urlopen(page_req, timeout=8) as page_resp:
                    page_html = page_resp.read().decode("utf-8", errors="ignore")
                clean = re.sub(r"<script[^>]*>.*?</script>", "", page_html, flags=re.DOTALL)
                clean = re.sub(r"<style[^>]*>.*?</style>", "", clean, flags=re.DOTALL)
                clean = re.sub(r"<[^>]+>", " ", clean)
                clean = re.sub(r"\s+", " ", clean).strip()
                if len(clean) > 100:
                    results.append(clean[:800])
            except (OSError, urllib.error.URLError):
                continue

        # 兜底：从搜索结果摘要提取
        if not results:
            snippets = re.findall(r'<span class="content-right_[^"]*">(.*?)</span>', html)
            for s in snippets[:max_results]:
                clean = re.sub(r"<[^>]+>", "", s).strip()
                if len(clean) > 20:
                    results.append(clean)

        return results if results else ["(搜索无结果)"]
    except Exception as e:
        return [f"(搜索异常: {e})"]


# ── 对话持久化 ────────────────────────────────────────────
def save_chat(chat_id, data):
    """保存对话记录到文件。"""
    try:
        fpath = os.path.join(CHAT_DIR, f"{chat_id}.json")
        with open(fpath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)
        return True
    except OSError:
        return False


def load_chat(chat_id):
    """从文件加载对话记录。"""
    try:
        fpath = os.path.join(CHAT_DIR, f"{chat_id}.json")
        if os.path.exists(fpath):
            with open(fpath, "r", encoding="utf-8") as f:
                return json.load(f)
    except (OSError, json.JSONDecodeError):
        pass
    return None


def list_chats():
    """列出所有对话。"""
    chats = []
    try:
        files = sorted(os.listdir(CHAT_DIR), reverse=True)
    except OSError:
        return chats

    for fname in files:
        if not fname.endswith(".json"):
            continue
        chat_id = fname[:-5]
        data = load_chat(chat_id)
        if data:
            chats.append({
                "id": chat_id,
                "title": data.get("title", "新对话"),
                "mode": data.get("mode", "weekly"),
                "updated": data.get("updated", 0),
                "messages_count": len(data.get("messages", [])),
            })
    return chats


def delete_chat_file(chat_id):
    """删除对话文件。"""
    try:
        fpath = os.path.join(CHAT_DIR, f"{chat_id}.json")
        if os.path.exists(fpath):
            os.remove(fpath)
            return True
    except OSError:
        pass
    return False


# ── LLM 调用辅助 ─────────────────────────────────────────
def build_messages(mode, message, history, kb_results=None, search_results=None):
    """构建发送给 LLM 的消息列表。"""
    system_prompt = SYSTEM_PROMPTS.get(mode, SYSTEM_PROMPTS["weekly"])
    messages = [{"role": "system", "content": system_prompt}]

    # 知识库参考
    if kb_results:
        kb_info = "\n".join(f"【{d['title']}】\n{d['content'][:300]}" for d in kb_results)
        messages.append({"role": "system", "content": f"【知识库参考】\n{kb_info}"})

    # 联网搜索参考
    if search_results and search_results[0] != "(搜索无结果)":
        search_info = "\n".join(f"· {r[:300]}" for r in search_results[:5])
        messages.append({"role": "system", "content": f"【联网搜索参考】\n{search_info}"})

    # 历史消息（最近 10 轮）
    for h in history[-10:]:
        if h.get("role") in ("user", "assistant"):
            messages.append({"role": h["role"], "content": h["content"]})

    messages.append({"role": "user", "content": message})
    return messages


def update_chat_history(chat_id, mode, message, reply):
    """更新对话历史并保存。"""
    if not chat_id:
        return

    chat_data = load_chat(chat_id) or {
        "id": chat_id,
        "title": message[:20] if len(message) > 20 else message,
        "mode": mode,
        "messages": [],
        "created": time.time(),
        "updated": time.time(),
    }
    chat_data["messages"].append({"role": "user", "content": message})
    chat_data["messages"].append({"role": "assistant", "content": reply})
    chat_data["updated"] = time.time()
    chat_data["mode"] = mode
    if not chat_data.get("title") or chat_data["title"] == "新对话":
        chat_data["title"] = message[:20] if len(message) > 20 else message
    save_chat(chat_id, chat_data)


def get_openai_client(api_key, base_url):
    """获取 OpenAI 客户端实例。"""
    try:
        from openai import OpenAI
        return OpenAI(base_url=base_url, api_key=api_key)
    except ImportError as exc:
        raise RuntimeError("请安装 openai 库: pip install openai") from exc


def chat_with_retry(client, model, messages, max_retries=3):
    """调用 LLM 聊天接口，带重试。"""
    for attempt in range(max_retries):
        try:
            resp = client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=0.7,
            )
            return resp.choices[0].message.content
        except Exception as e:
            if attempt == max_retries - 1:
                raise
            time.sleep(1 + attempt)


# ── HTTP 请求处理器 ──────────────────────────────────────
class Handler(BaseHTTPRequestHandler):
    """HTTP 请求处理器。"""

    def _send_json(self, data, code=200):
        """发送 JSON 响应。"""
        self.send_response(code)
        self.send_header("Content-Type", "application/json;charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Cache-Control", "no-store, no-cache, must-revalidate, max-age=0")
        self.send_header("Pragma", "no-cache")
        self.send_header("Expires", "0")
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode("utf-8"))

    def do_OPTIONS(self):
        """处理 CORS 预检请求。"""
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET,POST,DELETE,OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "*")
        self.end_headers()

    # ── GET 请求 ──────────────────────────────────────────
    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path

        if path == "/ping":
            return self._send_json({"ok": True})

        if path == "/templates":
            return self._send_json({"templates": TEMPLATES})

        if path == "/chats":
            return self._send_json({"chats": list_chats()})

        if path.startswith("/chat/"):
            chat_id = path.split("/chat/")[1]
            data = load_chat(chat_id)
            if data:
                return self._send_json(data)
            return self._send_json({"error": "对话不存在"}, 404)

        if path == "/kb":
            docs = load_knowledge_base()
            return self._send_json({
                "count": len(docs),
                "docs": [{"title": d["title"]} for d in docs[:10]],
            })

        if path == "/search":
            qs = parse_qs(parsed.query)
            q = qs.get("q", [""])[0]
            results = web_search(q) if q else []
            return self._send_json({"results": results})

        # 默认返回 index.html
        self.send_response(200)
        self.send_header("Content-Type", "text/html;charset=utf-8")
        self.end_headers()
        with open(os.path.join(HERE, "index.html"), "r", encoding="utf-8") as f:
            self.wfile.write(f.read().encode("utf-8"))

    # ── DELETE 请求 ───────────────────────────────────────
    def do_DELETE(self):
        parsed = urlparse(self.path)
        path = parsed.path

        if path.startswith("/chat/"):
            chat_id = path.split("/chat/")[1]
            ok = delete_chat_file(chat_id)
            return self._send_json({"ok": ok})

        return self._send_json({"error": "Not found"}, 404)

    # ── POST 请求 ─────────────────────────────────────────
    def do_POST(self):
        try:
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length).decode("utf-8")
            data = json.loads(body) if body else {}
        except (ValueError, json.JSONDecodeError):
            return self._send_json({"error": "Invalid request"}, 400)

        parsed = urlparse(self.path)
        path = parsed.path

        if path == "/chat":
            return self._handle_chat(data)
        if path == "/chat/stream":
            return self._handle_stream(data)
        if path == "/kb/upload":
            return self._handle_kb_upload(data)
        if path == "/export":
            return self._handle_export(data)

        return self._send_json({"error": "Not found"}, 404)

    # ── 普通聊天 ──────────────────────────────────────────
    def _handle_chat(self, data):
        mode = data.get("mode", "weekly")
        message = data.get("message", "")
        api_key = data.get("api_key", "")
        base_url = data.get("base_url", PRESETS["agnes"]["base_url"])
        model = data.get("model", PRESETS["agnes"]["model"])
        chat_id = data.get("chat_id", "")
        history = data.get("history", [])

        if not api_key:
            return self._send_json({"error": "请提供 API Key"})
        if not message or not message.strip():
            return self._send_json({"error": "请输入消息"})

        try:
            client = get_openai_client(api_key, base_url)
        except RuntimeError as e:
            return self._send_json({"error": str(e)})

        # 联网搜索（仅学习模式）
        search_results = []
        if mode == "learn":
            search_results = web_search(message + " 入门教程 学习笔记", max_results=3)

        # 知识库检索
        kb_docs = load_knowledge_base()
        kb_results = search_knowledge_base(message, kb_docs)

        # 构建消息
        messages = build_messages(mode, message, history, kb_results, search_results)

        try:
            reply = chat_with_retry(client, model, messages)
        except Exception as e:
            return self._send_json({"error": str(e)}, 500)

        # 保存对话
        update_chat_history(chat_id, mode, message, reply)

        return self._send_json({"reply": reply, "chat_id": chat_id})

    # ── 流式聊天 ──────────────────────────────────────────
    def _handle_stream(self, data):
        mode = data.get("mode", "weekly")
        message = data.get("message", "")
        api_key = data.get("api_key", "")
        base_url = data.get("base_url", PRESETS["agnes"]["base_url"])
        model = data.get("model", PRESETS["agnes"]["model"])
        chat_id = data.get("chat_id", "")
        history = data.get("history", [])

        if not api_key:
            return self._send_json({"error": "请提供 API Key"})
        if not message or not message.strip():
            return self._send_json({"error": "请输入消息"})

        try:
            client = get_openai_client(api_key, base_url)
        except RuntimeError as e:
            return self._send_json({"error": str(e)})

        # 联网搜索（仅学习模式）
        search_results = []
        if mode == "learn":
            search_results = web_search(message + " 入门教程 学习笔记", max_results=3)

        # 知识库检索
        kb_docs = load_knowledge_base()
        kb_results = search_knowledge_base(message, kb_docs)

        # 构建消息
        messages = build_messages(mode, message, history, kb_results, search_results)

        # 发送 SSE 响应头
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream;charset=utf-8")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "keep-alive")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()

        def _sse(data_dict):
            self.wfile.write(
                f"data: {json.dumps(data_dict, ensure_ascii=False)}\n\n".encode("utf-8")
            )
            self.wfile.flush()

        full_reply = ""
        try:
            stream = client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=0.7,
                stream=True,
            )
            for chunk in stream:
                if chunk.choices and chunk.choices[0].delta.content:
                    content = chunk.choices[0].delta.content
                    full_reply += content
                    _sse({"content": content})
        except Exception as e:
            _sse({"error": str(e)})
            return

        _sse({"done": True})

        # 保存对话
        update_chat_history(chat_id, mode, message, full_reply)

    # ── 知识库上传 ────────────────────────────────────────
    def _handle_kb_upload(self, data):
        content = data.get("content", "")
        title = data.get("title", "")

        if not content or not content.strip():
            return self._send_json({"error": "内容不能为空"})

        try:
            fname = f"{title or str(uuid.uuid4())}.txt"
            fpath = os.path.join(KB_DIR, fname)
            with open(fpath, "w", encoding="utf-8") as f:
                f.write(content)
            # 清除知识库缓存
            global _kb_cache
            _kb_cache = None
            return self._send_json({"ok": True, "filename": fname})
        except OSError as e:
            return self._send_json({"error": str(e)}, 500)

    # ── 导出对话 ──────────────────────────────────────────
    def _handle_export(self, data):
        messages = data.get("messages", [])
        format_type = data.get("format", "markdown")

        if not messages:
            return self._send_json({"error": "没有可导出的内容"})

        if format_type == "markdown":
            content = "# 对话记录\n\n"
            for msg in messages:
                role = "用户" if msg.get("role") == "user" else "助手"
                content += f"## {role}\n\n{msg.get('content', '')}\n\n"
        else:
            content = ""
            for msg in messages:
                role = "用户" if msg.get("role") == "user" else "助手"
                content += f"[{role}]\n{msg.get('content', '')}\n\n"

        return self._send_json({"content": content, "format": format_type})

    # ── 日志过滤 ──────────────────────────────────────────
    def log_message(self, format, *args):
        msg = format % args if args else format
        # 过滤掉频繁的心跳请求，只在控制台显示重要请求
        if any(p in msg for p in ["/ping"]):
            return
        print(f"[REQ] {msg}")


# ── 入口 ──────────────────────────────────────────────────
def main():
    port = 8765
    server = ThreadingHTTPServer(("0.0.0.0", port), Handler)
    print("=" * 50)
    print("  我的专属 AI 智能体 v2.0")
    print("=" * 50)
    print(f"  服务地址: http://127.0.0.1:{port}/")
    print("  工作流: 写周报 | 学知识 | 改代码")
    print("  功能: 流式输出 | 对话历史 | 知识库 | 模板 | 导出")
    print("  按 Ctrl+C 停止服务")
    print("=" * 50)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.shutdown()
        print("\n已停止服务")


if __name__ == "__main__":
    main()

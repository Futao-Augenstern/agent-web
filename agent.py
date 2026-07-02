#!/usr/bin/env python3
"""我的专属 AI 智能体 v2.0 — 写周报/学知识/改代码 + 流式输出/知识库/对话历史"""
import os, re, json, time, uuid, urllib.request, urllib.parse
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from urllib.parse import parse_qs, urlparse

HERE = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(HERE, "data")
KB_DIR = os.path.join(DATA_DIR, "knowledge_base")
CHAT_DIR = os.path.join(DATA_DIR, "chats")

os.makedirs(KB_DIR, exist_ok=True)
os.makedirs(CHAT_DIR, exist_ok=True)

def load_dotenv(path):
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, _, val = line.partition("=")
                    key, val = key.strip(), val.strip()
                    if key not in os.environ:
                        os.environ[key] = val

load_dotenv(os.path.join(HERE, ".env"))

PRESETS = {
    "agnes": {"base_url": "https://apihub.agnes-ai.com/v1", "model": "agnes-2.0-flash"},
    "deepseek": {"base_url": "https://api.deepseek.com", "model": "deepseek-chat"},
    "qwen": {"base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1", "model": "qwen-plus"},
    "glm": {"base_url": "https://open.bigmodel.cn/api/paas/v4", "model": "glm-4"},
    "moonshot": {"base_url": "https://api.moonshot.cn/v1", "model": "moonshot-v1-8k"},
    "openai": {"base_url": "https://api.openai.com/v1", "model": "gpt-4o"},
    "ollama": {"base_url": "http://localhost:11434/v1", "model": "qwen2.5:7b"},
}

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

def web_search(query, max_results=5):
    results = []
    try:
        url = "https://www.baidu.com/s?wd=" + urllib.parse.quote(query)
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            html = resp.read().decode("utf-8", errors="ignore")
        
        urls = re.findall(r'href="(https?://[^"]+)"', html)
        valid_urls = [u for u in urls if 'baidu.com' not in u and len(u) > 30][:max_results + 3]
        
        for target_url in valid_urls:
            if len(results) >= max_results:
                break
            try:
                page_req = urllib.request.Request(target_url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"})
                with urllib.request.urlopen(page_req, timeout=8) as page_resp:
                    page_html = page_resp.read().decode("utf-8", errors="ignore")
                clean = re.sub(r'<script[^>]*>.*?</script>', '', page_html, flags=re.DOTALL)
                clean = re.sub(r'<style[^>]*>.*?</style>', '', clean, flags=re.DOTALL)
                clean = re.sub(r'<[^>]+>', ' ', clean)
                clean = re.sub(r'\s+', ' ', clean).strip()
                if len(clean) > 100:
                    results.append(clean[:800])
            except:
                continue
        
        if not results:
            snippets = re.findall(r'<span class="content-right_[^"]*">(.*?)</span>', html)
            for s in snippets[:max_results]:
                clean = re.sub(r'<[^>]+>', '', s).strip()
                if len(clean) > 20:
                    results.append(clean)
        
        return results if results else ["(搜索无结果)"]
    except Exception as e:
        return [f"(搜索异常: {e})"]

def load_knowledge_base():
    docs = []
    try:
        for fname in os.listdir(KB_DIR):
            if fname.endswith('.txt') or fname.endswith('.md'):
                fpath = os.path.join(KB_DIR, fname)
                with open(fpath, 'r', encoding='utf-8') as f:
                    content = f.read()
                    chunks = [content[i:i+500] for i in range(0, len(content), 400)]
                    for i, chunk in enumerate(chunks):
                        docs.append({"id": f"{fname}_{i}", "title": fname, "content": chunk})
    except:
        pass
    return docs

def search_knowledge_base(query, docs, top_k=3):
    if not docs:
        return []
    query_words = set(re.findall(r'[\w\u4e00-\u9fff]+', query.lower()))
    scored = []
    for doc in docs:
        content_words = set(re.findall(r'[\w\u4e00-\u9fff]+', doc['content'].lower()))
        score = len(query_words & content_words)
        if score > 0:
            scored.append((score, doc))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [doc for _, doc in scored[:top_k]]

def save_chat(chat_id, data):
    try:
        fpath = os.path.join(CHAT_DIR, f"{chat_id}.json")
        with open(fpath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False)
    except:
        pass

def load_chat(chat_id):
    try:
        fpath = os.path.join(CHAT_DIR, f"{chat_id}.json")
        if os.path.exists(fpath):
            with open(fpath, 'r', encoding='utf-8') as f:
                return json.load(f)
    except:
        pass
    return None

def list_chats():
    chats = []
    try:
        for fname in sorted(os.listdir(CHAT_DIR), reverse=True):
            if fname.endswith('.json'):
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
    except:
        pass
    return chats

def delete_chat_file(chat_id):
    try:
        fpath = os.path.join(CHAT_DIR, f"{chat_id}.json")
        if os.path.exists(fpath):
            os.remove(fpath)
            return True
    except:
        pass
    return False

class Handler(BaseHTTPRequestHandler):
    def _send_json(self, data, code=200):
        self.send_response(code)
        self.send_header('Content-Type', 'application/json;charset=utf-8')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Cache-Control', 'no-store, no-cache, must-revalidate, max-age=0')
        self.send_header('Pragma', 'no-cache')
        self.send_header('Expires', '0')
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode('utf-8'))
    
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET,POST,DELETE,OPTIONS')
        self.send_header('Access-Control-Allow-Headers', '*')
        self.end_headers()
    
    def do_GET(self):
        parsed = urlparse(self.path)
        
        if parsed.path == '/ping':
            return self._send_json({'ok': True})
        
        if parsed.path == '/templates':
            return self._send_json({'templates': TEMPLATES})
        
        if parsed.path == '/chats':
            return self._send_json({'chats': list_chats()})
        
        if parsed.path.startswith('/chat/'):
            chat_id = parsed.path.split('/chat/')[1]
            data = load_chat(chat_id)
            if data:
                return self._send_json(data)
            return self._send_json({'error': '对话不存在'}, 404)
        
        if parsed.path.startswith('/kb'):
            docs = load_knowledge_base()
            return self._send_json({'count': len(docs), 'docs': [{'title': d['title']} for d in docs[:10]]})
        
        if parsed.path.startswith('/search'):
            qs = parse_qs(parsed.query)
            q = qs.get('q', [''])[0]
            if q:
                return self._send_json({'results': web_search(q)})
            return self._send_json({'results': []})
        
        self.send_response(200)
        self.send_header('Content-Type', 'text/html;charset=utf-8')
        self.end_headers()
        with open(os.path.join(HERE, 'index.html'), 'r', encoding='utf-8') as f:
            self.wfile.write(f.read().encode('utf-8'))
    
    def do_DELETE(self):
        parsed = urlparse(self.path)
        if parsed.path.startswith('/chat/'):
            chat_id = parsed.path.split('/chat/')[1]
            ok = delete_chat_file(chat_id)
            return self._send_json({'ok': ok})
        return self._send_json({'error': 'Not found'}, 404)
    
    def do_POST(self):
        try:
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length).decode('utf-8')
            data = json.loads(body) if body else {}
        except:
            return self._send_json({'error': 'Invalid request'}, 400)
        
        parsed = urlparse(self.path)
        
        if parsed.path == '/chat':
            return self._handle_chat(data)
        elif parsed.path == '/chat/stream':
            return self._handle_stream(data)
        elif parsed.path == '/kb/upload':
            return self._handle_kb_upload(data)
        elif parsed.path == '/export':
            return self._handle_export(data)
        else:
            return self._send_json({'error': 'Not found'}, 404)
    
    def _handle_chat(self, data):
        mode = data.get('mode', 'weekly')
        message = data.get('message', '')
        api_key = data.get('api_key', '')
        base_url = data.get('base_url', 'https://apihub.agnes-ai.com/v1')
        model = data.get('model', 'agnes-2.0-flash')
        chat_id = data.get('chat_id', '')
        history = data.get('history', [])
        
        if not api_key:
            return self._send_json({'error': '请提供 API Key'})
        if not message:
            return self._send_json({'error': '请输入消息'})
        
        try:
            from openai import OpenAI
            client = OpenAI(base_url=base_url, api_key=api_key)
        except ImportError:
            return self._send_json({'error': '请安装 openai 库: pip install openai'})
        
        system_prompt = SYSTEM_PROMPTS.get(mode, SYSTEM_PROMPTS['weekly'])
        
        search_results = []
        if mode == 'learn':
            search_results = web_search(message + " 入门教程 学习笔记", max_results=3)
        
        kb_docs = load_knowledge_base()
        kb_results = search_knowledge_base(message, kb_docs)
        
        messages = [{'role': 'system', 'content': system_prompt}]
        
        if kb_results:
            kb_info = "\n".join(f"【{d['title']}】\n{d['content'][:300]}" for d in kb_results)
            messages.append({'role': 'system', 'content': f"【知识库参考】\n{kb_info}"})
        
        if search_results and search_results[0] != "(搜索无结果)":
            search_info = "\n".join(f"· {r[:300]}" for r in search_results[:5])
            messages.append({'role': 'system', 'content': f"【联网搜索参考】\n{search_info}"})
        
        for h in history[-10:]:
            if h.get('role') in ('user', 'assistant'):
                messages.append({'role': h['role'], 'content': h['content']})
        
        messages.append({'role': 'user', 'content': message})
        
        for attempt in range(3):
            try:
                resp = client.chat.completions.create(
                    model=model,
                    messages=messages,
                    temperature=0.7,
                )
                reply = resp.choices[0].message.content
                break
            except Exception as e:
                if attempt == 2:
                    return self._send_json({'error': str(e)}, 500)
                time.sleep(1)
        
        if chat_id:
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
        
        return self._send_json({'reply': reply, 'chat_id': chat_id})
    
    def _handle_stream(self, data):
        mode = data.get('mode', 'weekly')
        message = data.get('message', '')
        api_key = data.get('api_key', '')
        base_url = data.get('base_url', 'https://apihub.agnes-ai.com/v1')
        model = data.get('model', 'agnes-2.0-flash')
        chat_id = data.get('chat_id', '')
        history = data.get('history', [])
        
        if not api_key:
            return self._send_json({'error': '请提供 API Key'})
        if not message:
            return self._send_json({'error': '请输入消息'})
        
        try:
            from openai import OpenAI
            client = OpenAI(base_url=base_url, api_key=api_key)
        except ImportError:
            return self._send_json({'error': '请安装 openai 库: pip install openai'})
        
        system_prompt = SYSTEM_PROMPTS.get(mode, SYSTEM_PROMPTS['weekly'])
        
        search_results = []
        if mode == 'learn':
            search_results = web_search(message + " 入门教程 学习笔记", max_results=3)
        
        kb_docs = load_knowledge_base()
        kb_results = search_knowledge_base(message, kb_docs)
        
        messages = [{'role': 'system', 'content': system_prompt}]
        
        if kb_results:
            kb_info = "\n".join(f"【{d['title']}】\n{d['content'][:300]}" for d in kb_results)
            messages.append({'role': 'system', 'content': f"【知识库参考】\n{kb_info}"})
        
        if search_results and search_results[0] != "(搜索无结果)":
            search_info = "\n".join(f"· {r[:300]}" for r in search_results[:5])
            messages.append({'role': 'system', 'content': f"【联网搜索参考】\n{search_info}"})
        
        for h in history[-10:]:
            if h.get('role') in ('user', 'assistant'):
                messages.append({'role': h['role'], 'content': h['content']})
        
        messages.append({'role': 'user', 'content': message})
        
        self.send_response(200)
        self.send_header('Content-Type', 'text/event-stream;charset=utf-8')
        self.send_header('Cache-Control', 'no-cache')
        self.send_header('Connection', 'keep-alive')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        
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
                    self.wfile.write(f"data: {json.dumps({'content': content}, ensure_ascii=False)}\n\n".encode('utf-8'))
                    self.wfile.flush()
        except Exception as e:
            self.wfile.write(f"data: {json.dumps({'error': str(e)}, ensure_ascii=False)}\n\n".encode('utf-8'))
            self.wfile.flush()
            return
        
        self.wfile.write(f"data: {json.dumps({'done': True}, ensure_ascii=False)}\n\n".encode('utf-8'))
        self.wfile.flush()
        
        if chat_id:
            chat_data = load_chat(chat_id) or {
                "id": chat_id,
                "title": message[:20] if len(message) > 20 else message,
                "mode": mode,
                "messages": [],
                "created": time.time(),
                "updated": time.time(),
            }
            chat_data["messages"].append({"role": "user", "content": message})
            chat_data["messages"].append({"role": "assistant", "content": full_reply})
            chat_data["updated"] = time.time()
            chat_data["mode"] = mode
            if not chat_data.get("title") or chat_data["title"] == "新对话":
                chat_data["title"] = message[:20] if len(message) > 20 else message
            save_chat(chat_id, chat_data)
    
    def _handle_kb_upload(self, data):
        content = data.get('content', '')
        title = data.get('title', '')
        if not content:
            return self._send_json({'error': '内容不能为空'})
        try:
            fname = f"{title or str(uuid.uuid4())}.txt"
            fpath = os.path.join(KB_DIR, fname)
            with open(fpath, 'w', encoding='utf-8') as f:
                f.write(content)
            return self._send_json({'ok': True, 'filename': fname})
        except Exception as e:
            return self._send_json({'error': str(e)}, 500)
    
    def _handle_export(self, data):
        messages = data.get('messages', [])
        format_type = data.get('format', 'markdown')
        if not messages:
            return self._send_json({'error': '没有可导出的内容'})
        
        if format_type == 'markdown':
            content = "# 对话记录\n\n"
            for msg in messages:
                role = "用户" if msg.get('role') == 'user' else "助手"
                content += f"## {role}\n\n{msg.get('content', '')}\n\n"
        else:
            content = ""
            for msg in messages:
                role = "用户" if msg.get('role') == 'user' else "助手"
                content += f"[{role}]\n{msg.get('content', '')}\n\n"
        
        return self._send_json({'content': content, 'format': format_type})
    
    def log_message(self, format, *args):
        msg = format % args if args else format
        if any(p in msg for p in ['/ping', '/chat', '/chat/stream', '/templates', '/chats']):
            print(f"[REQ] {msg}")

def main():
    port = 8765
    server = ThreadingHTTPServer(('0.0.0.0', port), Handler)
    print(f'我的专属 AI 智能体 v2.0: http://127.0.0.1:{port}/')
    print('工作流: 写周报 | 学知识 | 改代码')
    print('功能: 流式输出 | 对话历史 | 知识库 | 模板 | 导出')
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.shutdown()
        print('\n已停止')

if __name__ == '__main__':
    main()

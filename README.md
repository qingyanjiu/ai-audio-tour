# AI 大屏讲解员

园区数字孪生驾驶舱大屏智能讲解系统。前端传时间戳 → 服务端 CDP 截图 → LLM 识别图表 → 自动生成展厅级别讲解词。

## 架构

```
┌─ 大屏页面 ──────────────┐
│                          │
│  🤖 AI 介绍 按钮        │
│  (ai-guide.js)           │
│                          │
│  POST /api/v1/describe   │
│  { timestamp, menu_name }│
└─────────┬────────────────┘
          │ 浏览器发 JSON
          ▼
┌─ 讲解员 API (app.py) ───┐
│                          │
│  ① CDP 截图 Chrome 大屏  │
│  ② 保存 screenshots/    │
│  ③ 压缩 → base64 → LLM  │
│  ④ LLM 返回讲解词        │
│  ⑤ (可选) TTS 合成语音  │
└──────────────────────────┘
          │
          ▼
   ┌─ LLM (Qwen-VL 等) ──┐
   │  多模态图片理解       │
   │  生成展厅讲解词       │
   └──────────────────────┘
```

**使用方式：**

| 方式 | 场景 | 说明 |
|------|------|------|
| **前端按钮** | 展厅现场 | `ai-guide.js` 注入页面，点击发 JSON 到 API |
| **CLI 工具** | 后台/测试 | `capture.py --menu 智慧安防` 直调 LLM |

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置 LLM

编辑 `config.yaml`，指向你的模型服务（支持 OpenAI API 格式即可）：

```yaml
llm:
  base_url: http://localhost:1234/v1   # LM Studio / Ollama / vLLM
  api_key: lm-studio
  model: qwen/qwen3.5-9b              # 需支持多模态视觉
```

也支持环境变量覆盖（部署用）：

```bash
export LLM_BASE_URL=http://localhost:1234/v1
export LLM_API_KEY=lm-studio
export LLM_MODEL=qwen/qwen3.5-9b
```

### 3. 启动 Chrome + 服务

先用 `start_chrome.py` 一键启动 Chrome（调试模式并打开大屏页面）：

```bash
python start_chrome.py                        # 打开配置中第一个页面
python start_chrome.py --name 智慧安防          # 按名称匹配
```

启动后建议先验证 Chrome CDP 可访问（新终端）：

```bash
curl http://127.0.0.1:9222/json/version
curl http://127.0.0.1:9222/json
```

然后在另一个终端启动 API 服务：

```bash
python app.py
```

打开 `http://localhost:8000/docs` 可在线调接口。

## API 文档

一个接口，传入菜单名称即可自动截图 → 识别 → 返回讲解词。

### POST /api/v1/describe

```http
POST /api/v1/describe
Content-Type: application/json
```

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `menu_name` | string | 否 | 当前菜单/专题名称，用于匹配 config.yaml 中的大屏 URL |
| `timestamp` | string | 否 | 自定义时间戳，不传则服务端自动生成 |

```bash
curl -X POST http://localhost:8000/api/v1/describe \
  -H "Content-Type: application/json" \
  -d '{"menu_name": "智慧安防", "timestamp": "1740389422"}'
```

```bash
# 不传时间戳则自动生成
curl -X POST http://localhost:8000/api/v1/describe \
  -H "Content-Type: application/json" \
  -d '{"menu_name": "智慧安防"}'
```

返回：

```json
{
  "code": 0,
  "data": {
    "description": "您现在看到的是智慧安防专题，该专题主要对园区安防态势进行统一监测和管理…",
    "menu_name": "智慧安防",
    "model": "qwen/qwen3.5-9b",
    "usage": { "input_tokens": 1234, "output_tokens": 234 },
    "timestamp": "1740389422",
    "filename": "1740389422.jpg"
  },
  "message": "ok"
}
```

### 其他

| 接口 | 说明 |
|------|------|
| `GET /health` | 健康检查 |
| `http://localhost:8000/ai-guide.js` | 前端注入脚本（供页面引用） |
| `http://localhost:8000/screenshots/xxx.jpg` | 截图文件（静态目录） |


## 语音合成（TTS）

系统支持集成 **Kokoro-TTS**（离线、轻量、免费）为讲解词自动生成语音。
82M 参数，CPU 即可秒出，支持中文。

### 安装

```bash
pip install -r requirements.txt
```

如果之前已安装过依赖，单独安装 TTS 部分：

```bash
pip install "kokoro>=0.9.0" "misaki[zh]>=0.9.0" soundfile>=0.14.0
```

### 音色测试工具

测试工具支持**耗时统计**：每次合成会记录模型加载时间、生成耗时、音频时长和实时倍率。

```
模型加载: 1.55s  |  生成耗时: 1.69s  |  音频时长: 3.6s
实时倍率: 0.47x  (快)
```

项目包含音色测试脚本 `test_kokoro.py`，可列出所有音色并试听：

```bash
# 列出所有可用音色
python test_kokoro.py

# 试听某个音色
python test_kokoro.py --voice zf_xiaobei

# 逐个试听所有音色（每个生成一个 .wav 文件）
python test_kokoro.py --voice all
```

第一次运行会自动从 HuggingFace 下载音色文件（约 82MB），需要联网。
下载后离线可用。

### 推荐中文音色

| 音色名 | 语言 | 风格 |
|--------|------|------|
| `zf_xiaobei` | 中文女声 | 自然亲和 |
| `zf_xiaotong` | 中文女声 | 温柔清晰 |
| `zm_yunxi` | 中文男声 | 阳光活力 |
| `zm_yunjian` | 中文男声 | 沉稳专业（推荐展厅） |

### 基本用法

```python
from kokoro import KPipeline
import soundfile as sf

pipeline = KPipeline(lang_code="z")
text = "您现在看到的是智慧安防专题，该专题主要包含园区安防监控等内容。"

generator = pipeline(text, voice="zf_xiaobei", speed=1)
for i, (gs, ps, audio) in enumerate(generator):
    sf.write("output.wav", audio, 24000)
    break
```

### 集成计划

Kokoro-TTS 即将集成到 `/api/v1/describe` 接口中，流程：

```
LLM 返回讲解词 → 数字转中文 → Kokoro-TTS 生成 → screenshots/{ts}.wav → 返回 audio_url
```

前端拿到 `audio_url` 后可直接 `new Audio(url).play()` 自动播放讲解。

## 使用方式

### 方式一：页面注入按钮（现场讲解）

在大屏 HTML 中加一行：

```html
<script src="http://localhost:8000/ai-guide.js"></script>
```

页面右下角会出现 **🤖 AI 介绍** 按钮。点击后发 timestamp + 页面名到 API，服务端自动 CDP 截图 → 识别 → 浮动面板显示讲解词。

### 方式二：CLI 截图（后台/测试）

Chrome 启动调试模式后，运行：

```bash
python capture.py --menu 智慧安防
```

截图 → 压缩 → 直调 LLM → 打印讲解词。

## 项目结构

```
ai-audio-tour/
├── app.py                     # FastAPI 服务（POST 截图 + LLM 接口）
├── config.yaml                # LLM、服务、截图配置
├── requirements.txt           # Python 依赖
├── ai-guide.js                # 前端注入脚本（按钮 → API）
├── capture.py                 # CLI：截图 + LLM 识别
├── test_kokoro.py             # Kokoro-TTS 音色测试 + 耗时统计
├── start_chrome.py            # 一键启动 Chrome 调试模式
├── services/
│   ├── config_loader.py       # 配置加载（支持环境变量覆盖）
│   ├── image_processor.py     # 图片压缩、转 base64
│   ├── llm_client.py          # LLM 多模态调用 + 讲解员提示词
│   ├── screenshotter.py       # CDP 截图（API 和 CLI 共用）
│   └── tts_service.py         # Kokoro-TTS 语音合成服务
└── screenshots/               # 截图统一存放目录
```

## Windows 注意事项

| 问题 | 解决方式 |
|------|----------|
| Chrome 调试端口连不上 | 用 `start_chrome.py` 启动，自动处理 `--remote-debugging-port`、`--remote-allow-origins=*` 和 `--user-data-dir` |
| 端口被占用 | 改 `config.yaml` 中 `server.port` 或 `screenshot.cdp_port` |
| 模型不支持视觉 | 确保模型支持多模态（Qwen-VL、LLaVA、GPT-4V、GPT-4o 等） |
| `websockets` 未安装 | `pip install websockets`（已包含在 requirements.txt） |

## 自定义提示词

```python
from services.llm_client import describe_page_with_image

result = describe_page_with_image(
    image_data_uri="data:image/jpeg;base64,...",
    menu_name="智慧安防",
    system_prompt="你现在是……（自定义角色）",
)
```

## HTTP 调用

```python
import requests

resp = requests.post(
    "http://localhost:8000/api/v1/describe",
    json={"menu_name": "智慧安防", "timestamp": "1740389422"},
)
print(resp.json()["data"]["description"])
```

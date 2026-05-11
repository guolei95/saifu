# 赛赋 SaiFu — 智能竞赛匹配平台

帮助大学生找到最适合自己的竞赛，AI（DeepSeek）+ 内置知识库驱动的个性化推荐。

---

## 当前部署状态（2026-05-11）

| 组件 | 地址 | 平台 | 费用 |
|------|------|------|------|
| 前端 | https://saifu-75e4.vercel.app | Vercel | ¥0 |
| 后端 | https://saifu-backend-pk86.onrender.com | Render | ¥0 |
| AI API | api.deepseek.com | DeepSeek | ¥0.2-0.5/次 |
| 代码仓库 | https://github.com/guolei95/saifu | GitHub | ¥0 |

> **后端已迁移到 Render 云端**：固定域名，不再需要本地隧道。关机/重启不影响服务。

### 凭证

| 项目 | 值 |
|------|-----|
| GitHub 用户名 | guolei95 |
| DeepSeek API Key | 通过 Render 环境变量注入（不在代码中） |
| Render | 自动构建部署，环境变量配置 DEEPSEEK_API_KEY |
| Vercel | 已关联 GitHub 仓库，push 自动部署 |

---

## 部署架构

```
用户 → Vercel（前端 CDN）
         │
         │ API 请求
         ▼
      Render（后端 FastAPI :$PORT）
         │
    ┌────┼────┐
    ▼         ▼
DuckDuckGo  DeepSeek API
+ Bing       + 84项A类竞赛知识库
```

---

## 项目结构

```
saifu/
├── backend/
│   ├── main.py              # FastAPI 入口
│   ├── config.py             # 配置（从环境变量读取 API Key）
│   ├── match/
│   │   └── engine.py         # 匹配引擎
│   ├── services/
│   │   ├── ai_client.py      # DeepSeek API 调用
│   │   ├── search.py         # DuckDuckGo + Bing 双引擎搜索
│   │   ├── knowledge_base.py # 84项A类竞赛知识库 + 匹配/评坑/分类函数
│   │   ├── research.py       # 个性化调研（AI + 知识库双引擎）
│   │   └── validation.py     # 交叉验证
│   ├── data/
│   │   └── 84项A类竞赛知识库.json
│   ├── requirements.txt
│   └── Procfile
├── index.html                # 前端首页
├── js/
│   └── app.js                # 表单收集 + API调用 + 卡片渲染 + 导出
├── css/
│   └── style.css
└── vercel.json
```

## API 端点

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /api/health | 健康检查 |
| GET | /api/competitions | 知识库竞赛列表 |
| POST | /api/match | 智能匹配（30-60秒） |
| POST | /api/import-and-research | 导入报告 + 调研分析 |

---

## 本地开发

```bash
# 安装依赖（首次）
cd backend
pip install -r requirements.txt

# 设置环境变量（不要硬编码在代码里！）
# Windows:
set DEEPSEEK_API_KEY=你的密钥
# macOS/Linux:
export DEEPSEEK_API_KEY=你的密钥

# 启动后端
python -m uvicorn main:app --host 0.0.0.0 --port 8000
```

### 必需条件
- Python 3.10+
- DeepSeek API Key（在 Render 环境变量中配置，本地开发时通过环境变量传入）

---

## 费用

| 项目 | 月费 |
|------|------|
| Vercel 前端 | ¥0 |
| Render 后端 | ¥0（免费版，15分钟无请求休眠） |
| GitHub | ¥0 |
| DeepSeek API | ~¥0.2-0.5/次调研 |
| **总计** | **¥0 + token 钱** |

---

## 安全提醒

⚠️ **不要将 API Key 提交到 Git！** 本项目已配置从环境变量读取密钥。如果密钥曾出现在 Git 历史中，请立即在 DeepSeek 平台重新生成新密钥并更新 Render 环境变量。

---

*赛赋 SaiFu — 让每个大学生都能找到属于自己的竞赛*

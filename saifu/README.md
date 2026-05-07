# 赛赋 SaiFu — 智能竞赛匹配平台

帮助大学生找到最适合自己的竞赛，AI 驱动的个性化推荐。

## 功能

- **用户画像填写**：学校、专业、年级、兴趣、目标、时间投入等
- **AI 智能匹配**：搜索 + DeepSeek 分析 + 常识库校验 + 交叉验证 + 自审查
- **结果卡片展示**：匹配分数、匹配原因、避坑提醒、相关案例

## 技术栈

| 层 | 技术 |
|----|------|
| 后端框架 | Python FastAPI |
| AI 服务 | DeepSeek API |
| 搜索 | DuckDuckGo（免费） |
| 前端 | 原生 HTML/CSS/JavaScript |
| 前端部署 | Vercel（香港节点） |
| 后端部署 | Render（美国，免费档） |
| 防休眠 | GitHub Actions |

## 本地运行

```bash
# 1. 安装依赖
cd 赛赋平台/backend
pip install -r requirements.txt

# 2. 设置 API Key
set DEEPSEEK_API_KEY=sk-你的key

# 3. 启动后端
uvicorn main:app --reload

# 4. 打开前端
# 浏览器直接打开 ../frontend/index.html
# 或 python -m http.server 8080 -d ../frontend
```

## 部署

### 后端 → Render（免费）

1. 把代码推送到 GitHub 仓库
2. 登录 [render.com](https://render.com) → New Web Service → 连接仓库
3. 设置：
   - Root Directory: `赛赋平台/backend`
   - Runtime: Python 3
   - Start Command: `uvicorn main:app --host 0.0.0.0 --port $PORT`
4. 添加环境变量：`DEEPSEEK_API_KEY` = `sk-你的key`
5. 部署 → 得到地址如 `https://saifu.onrender.com`

### 前端 → Vercel（免费，香港节点）

1. 登录 [vercel.com](https://vercel.com) → Import → 连接仓库
2. 设置 Root Directory: `赛赋平台`
3. 部署 → 得到地址如 `https://saifu.vercel.app`

### 连接前后端

1. 修改 `frontend/js/app.js` 中的 `API_BASE_URL` = Render 给的地址
2. 重新部署前端（Vercel 自动检测 git push）
3. 在 Render 环境变量中添加 `FRONTEND_URL` = Vercel 地址（用于 CORS）

### 防休眠

Render 免费服务 15 分钟无请求会休眠。`.github/workflows/keep-alive.yml` 每 10 分钟 ping 一次。

部署后修改 `keep-alive.yml` 中的 URL 为你的 Render 地址。

## 目录结构

```
赛赋平台/
├── backend/
│   ├── main.py                 ← FastAPI 应用入口
│   ├── config.py               ← 配置（读环境变量）
│   ├── match/
│   │   └── engine.py           ← 核心匹配流程
│   ├── services/
│   │   ├── ai_client.py        ← DeepSeek API 调用
│   │   ├── search.py           ← 搜索查询生成 + DuckDuckGo
│   │   ├── knowledge_base.py   ← 竞赛常识库
│   │   └── validation.py       ← 交叉验证 + LLM自审查
│   ├── requirements.txt
│   └── Procfile
├── frontend/
│   ├── index.html
│   ├── css/style.css
│   └── js/app.js
├── .github/workflows/
│   └── keep-alive.yml          ← 防休眠定时任务
├── vercel.json
└── README.md
```

## AI 使用说明

本平台使用 DeepSeek API 进行竞赛匹配分析，包含内置竞赛常识库进行交叉验证。如比赛要求披露 AI 使用情况，请注明：本工具使用了 AI 辅助搜索和匹配推荐。

---

*赛赋 SaiFu v1.0 — 让每个大学生都能找到属于自己的竞赛*

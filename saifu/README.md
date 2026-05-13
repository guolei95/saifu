# 赛赋 SaiFu — 智能竞赛匹配平台

帮助大学生找到最适合自己的竞赛，AI（DeepSeek）+ 内置知识库驱动的个性化推荐。

---

## 当前部署状态（2026-05-11）

| 组件 | 地址 | 平台 | 费用 |
|------|------|------|------|
| 前端 | https://saifu.vercel.app | Vercel | ¥0 |
| 后端 | https://saifu-backend-pk86.onrender.com | Render | ¥0 |
| AI API | api.deepseek.com / 豆包 / OpenAI | 多平台 | ¥0.02/次 |
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
| GET | /api/health | 健康检查（含 public_enabled、budget） |
| GET | /api/competitions | 84项A类竞赛知识库 |
| GET | /api/budget | 服务器 API 预算状态 |
| POST | /api/match | 智能匹配（30-60秒） |
| POST | /api/target-research | 定向调研（知道比赛名称） |
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

## 运维操作

### 🛑 关闭公开访问（停业维护）

让网站仅管理员可用，普通用户看到维护页面。

1. 打开 [Render Dashboard](https://dashboard.render.com) → `saifu-backend` → **Environment**
2. 添加环境变量：
   ```
   SAIFU_ENABLED = false
   ```
3. 点击 **Save Changes** → 等待自动重启（约 1 分钟）

| 用户 | 效果 |
|------|------|
| 普通用户 | 看到 🔧 网站维护中，无法使用 |
| 管理员（`?admin=xiaolei0207`） | 正常使用，导航栏显示 👑 管理员 |

**恢复公开**：删除 `SAIFU_ENABLED` 或改为 `true`，保存重启即可。

> **原理**：前端加载时查 `/api/health` 的 `public_enabled` 字段，false 则显示维护遮罩。后端所有写入 API（match/research）也会校验 `x-saifu-admin` 请求头，防止绕过前端直接调接口。

### 🔑 更换服务器 API Key

当 DeepSeek/豆包 Key 过期或想换模型时：

1. 去对应平台获取新 Key（[DeepSeek](https://platform.deepseek.com) / [火山引擎](https://console.volcengine.com)）
2. Render Dashboard → `saifu-backend` → Environment
3. 更新 `LLM_API_KEY` 为新 Key
4. 如换平台，同步更新 `LLM_BASE_URL` 和 `LLM_MODEL`：
   - DeepSeek: `LLM_BASE_URL=https://api.deepseek.com/v1`, `LLM_MODEL=deepseek-chat`
   - 豆包: `LLM_BASE_URL=https://ark.cn-beijing.volces.com/api/v3`, `LLM_MODEL=doubao-seed-2-0-lite-260428`
5. Save Changes → 验证：访问 `/api/health` 确认 `llm_configured: true`

### 💰 设置服务器 API 预算上限

防止服务器 Key 被刷爆：

| 环境变量 | 说明 | 默认值 |
|---------|------|--------|
| `BUDGET_LIMIT_YUAN` | 每月预算上限（元） | 5 |
| `BUDGET_COST_PER_1K_TOKENS` | 每千 token 成本（元） | 0.001 |

预算用完后自动触发「小雷已破产」，用户需使用自己的 Key。

---

*赛赋 SaiFu — 让每个大学生都能找到属于自己的竞赛*

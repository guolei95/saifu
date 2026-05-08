# 赛赋 SaiFu — 智能竞赛匹配平台

帮助大学生找到最适合自己的竞赛，AI 驱动的个性化推荐。

---

## 当前部署状态（2026-05-08）

| 组件 | 地址 | 平台 | 费用 |
|------|------|------|------|
| 前端 | https://saifu-75e4.vercel.app | Vercel（香港节点） | ¥0 |
| 后端隧道 | https://lab-thoughts-exclusive-resistance.trycloudflare.com | Cloudflare Tunnel | ¥0 |
| 后端本地 | localhost:8000 | 你的电脑 | — |
| AI API | api.deepseek.com | DeepSeek | ¥0.2-0.5/次 |
| 代码仓库 | https://github.com/guolei95/saifu | GitHub | ¥0 |

### 凭证

| 项目 | 值 |
|------|-----|
| GitHub 用户名 | guolei95 |
| DeepSeek API Key | sk-6dfbaf1c69b94a14aafdf29ef4517e7e（余额 10 元） |
| Vercel | GitHub 登录 |
| Cloudflare Tunnel | 无需账号（Quick Tunnel） |

---

## 部署架构

```
中国用户 → Vercel（香港）→ 前端页面秒开
                │
                │ 用户点「开始匹配」
                ▼
         Cloudflare Tunnel（全球加速，国内可访问）
                │
                ▼
         你的电脑（本地后端 :8000）
                │
        ┌───────┼───────┐
        ▼               ▼
   DuckDuckGo       DeepSeek API
   （走本地代理）    （境外）
```

---

## 本地启动（每次重启电脑后必做）

### 1. 启动后端

```bash
# Windows CMD
cd "D:\我的竞赛项目-AI赋能竞赛系统\saifu\backend"
set DEEPSEEK_API_KEY=sk-6dfbaf1c69b94a14aafdf29ef4517e7e
python -m uvicorn main:app --host 0.0.0.0 --port 8000
```

验证：浏览器打开 http://localhost:8000/api/health → 应返回 `{"status":"ok","deepseek_configured":true}`

### 2. 启动 Cloudflare Tunnel

```bash
cloudflared tunnel --url http://localhost:8000
```

启动后会输出新 URL（形如 `https://xxx.trycloudflare.com`），**记录下来**。

### 3. 更新前端 API 地址

拿到新 Tunnel URL 后：

1. 编辑 `saifu/frontend/js/app.js` 第 10 行，改成新 URL
2. 提交推送：
```bash
cd "D:\我的竞赛项目-AI赋能竞赛系统"
git add saifu/frontend/js/app.js
git commit -m "更新API地址"
git push
```
3. Vercel 自动检测 push → 自动重新部署（约 30 秒）

---

## 首次部署前端到 Vercel

1. 打开 https://vercel.com → GitHub 登录
2. Add New → Project → 选 `guolei95/saifu`
3. Root Directory 填 `saifu`
4. Deploy

之后每次 git push，Vercel 自动重新部署。

---

## 本地开发

```bash
# 安装依赖（首次）
cd saifu/backend
pip install -r requirements.txt

# 启动后端
set DEEPSEEK_API_KEY=sk-6dfbaf1c69b94a14aafdf29ef4517e7e
python -m uvicorn main:app --host 0.0.0.0 --port 8000
```

### 必需条件
- Python 3.10+
- 稳定翻墙代理（DuckDuckGo 搜索需要境外网络）
- cloudflared.exe（已下载到 `C:\Users\guolei\`）

---

## 项目结构

```
saifu/
├── backend/
│   ├── main.py              # FastAPI 入口（3个端点）
│   ├── config.py             # 配置（环境变量）
│   ├── match/
│   │   └── engine.py         # 匹配引擎（8步流程）
│   ├── services/
│   │   ├── ai_client.py      # DeepSeek API 调用 + JSON 修复
│   │   ├── search.py         # 搜索词生成 + DuckDuckGo 搜索
│   │   ├── knowledge_base.py # 竞赛常识库（9条竞赛 + 函数）
│   │   └── validation.py     # L1 交叉验证 + L2 LLM 自审查
│   ├── requirements.txt
│   ├── Dockerfile
│   └── Procfile
├── frontend/
│   ├── index.html            # 4步表单 + 结果展示
│   ├── css/style.css
│   └── js/app.js             # 表单收集 + API 调用 + 卡片渲染（第10行=API地址）
└── vercel.json
```

## API 端点

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /api/health | 健康检查 |
| GET | /api/competitions | 常识库竞赛列表（9条） |
| POST | /api/match | 智能匹配（30-60秒，消耗 ¥0.2-0.5） |

---

## 费用

| 项目 | 月费 |
|------|------|
| Vercel 前端 | ¥0 |
| Cloudflare Tunnel | ¥0 |
| GitHub | ¥0 |
| DeepSeek API | ~¥0.2-0.5/次匹配 |
| **总计** | **¥0 + token 钱** |

10 元余额 ≈ 200-500 次匹配。

---

## 已知限制

1. **后端依赖你的电脑**：关机 = 服务中断
2. **Tunnel URL 重启变**：每次重启 cloudflared 需更新前端 API 地址
3. **DuckDuckGo 限速风险**：连续搜索可能触发 202 Ratelimit
4. **verify_url 未集成**：URL 可达性校验函数已写但未接入 V1（在 engine.py 原代码中）
5. **用户反馈纠正系统**：save_correction/load_corrections 计划 V2 实现
6. **print → logging**：engine.py 中部分 print() 建议改为 logging

---

*赛赋 SaiFu v1.0 — 让每个大学生都能找到属于自己的竞赛*

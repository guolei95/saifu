# 赛赋 SaiFu — 智能竞赛匹配平台

帮助大学生找到最适合自己的竞赛，AI 驱动的个性化推荐。

---

## 当前部署状态（2026-05-10）

| 组件 | 地址 | 平台 | 费用 |
|------|------|------|------|
| 前端 | https://saifu-75e4.vercel.app | Vercel（香港节点） | ¥0 |
| 后端隧道 | https://precious-typing-brand-budgets.trycloudflare.com | Cloudflare Tunnel | ¥0 |
| 后端本地 | localhost:8000 | 你的电脑 | — |
| AI API | api.deepseek.com | DeepSeek | ¥0.2-0.5/次 |
| 代码仓库 | https://github.com/guolei95/saifu | GitHub | ¥0 |

> **隧道策略**：优先用 cloudflared（更快），如果 Cloudflare 服务端挂了就用 localhost.run（SSH，无需安装）。两个都是免费。

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

## 🚀 重启步骤（电脑重启后必做，AI 操作版）

> **核心就两步：① 起隧道拿公网地址 → ② 把新地址写进 app.js 推 GitHub。**
> 
> RESTART PROCEDURE v2 (2026-05-10):
> 1. Start backend: `cd "D:\我的竞赛项目-AI赋能竞赛系统\saifu\backend" && set DEEPSEEK_API_KEY=sk-6dfbaf1c69b94a14aafdf29ef4517e7e && python -m uvicorn main:app --host 0.0.0.0 --port 8000` (run in background)
> 2. Verify: `curl http://localhost:8000/api/health` → expect `{"status":"ok","deepseek_configured":true}`
> 3. Start tunnel — try cloudflared first, if HTTP 500 from trycloudflare.com (server-side issue, not local config), immediately switch to localhost.run:
>    - cloudflared: `"D:\我的竞赛项目-AI赋能竞赛系统\saifu\cloudflared.exe" tunnel --url http://localhost:8000` → extract URL like `https://xxx.trycloudflare.com`
>    - FALLBACK (localhost.run via SSH): `ssh -o StrictHostKeyChecking=no -R 80:localhost:8000 nokey@localhost.run` → extract URL like `https://xxxxxx.lhr.life`
> 4. Edit `saifu/frontend/js/app.js` line 10: replace the old tunnel URL with the new one
> 5. Git push: `cd "D:\我的竞赛项目-AI赋能竞赛系统" && git add saifu/frontend/js/app.js && git commit -m "update API URL" && git push`
> 6. Vercel auto-deploys on push (~30s). Verify: `curl -s https://saifu-75e4.vercel.app | findstr /C:"app.js"`
> 7. Done. Tell user: "搞定了，打开 https://saifu-75e4.vercel.app 就能用。"

### 手动步骤参考

<details>
<summary>点击展开手动命令</summary>

#### 1. 启动后端

```bash
# Windows CMD
cd "D:\我的竞赛项目-AI赋能竞赛系统\saifu\backend"
set DEEPSEEK_API_KEY=sk-6dfbaf1c69b94a14aafdf29ef4517e7e
python -m uvicorn main:app --host 0.0.0.0 --port 8000
```

验证：浏览器打开 http://localhost:8000/api/health → 应返回 `{"status":"ok","deepseek_configured":true}`

#### 2. 启动隧道（二选一）

**方案 A：Cloudflare Tunnel（优先尝试）**
```bash
cloudflared tunnel --url http://localhost:8000
# 输出形如 https://xxx.trycloudflare.com
```
⚠️ 如果 trycloudflare.com 返回 500 错误（服务端故障），换方案 B。

**方案 B：localhost.run（备用，无需安装任何东西）**
```bash
ssh -o StrictHostKeyChecking=no -R 80:localhost:8000 nokey@localhost.run
# 输出形如 https://xxxxxxxxxxxx.lhr.life
```

#### 3. 更新前端 API 地址 + 推送

拿到新 Tunnel URL 后：
1. 编辑 `saifu/frontend/js/app.js` 第 10 行，改成新 URL
2. 提交推送：
```bash
cd "D:\我的竞赛项目-AI赋能竞赛系统"
git add saifu/frontend/js/app.js
git commit -m "update API URL"
git push
```
3. Vercel 自动检测 push → 自动重新部署（约 30 秒）

</details>

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
2. **Tunnel URL 重启变**：每次重启电脑后需重新起隧道 + 更新 app.js 推 GitHub（见上方重启步骤）
3. **Cloudflare Quick Tunnel 偶尔 500**：trycloudflare.com 服务端故障时换用 localhost.run（`ssh -R 80:localhost:8000 nokey@localhost.run`）
4. **DuckDuckGo 限速风险**：连续搜索可能触发 202 Ratelimit
5. **verify_url 未集成**：URL 可达性校验函数已写但未接入 V1
6. **用户反馈纠正系统**：save_correction/load_corrections 计划 V2 实现

---

*赛赋 SaiFu v1.0 — 让每个大学生都能找到属于自己的竞赛*

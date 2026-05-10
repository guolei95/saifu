# 赛赋 SaiFu — 智能竞赛匹配平台

帮助大学生找到最适合自己的竞赛，AI 驱动的个性化推荐。

---

## 当前部署状态（2026-05-10）

| 组件 | 地址 | 平台 | 费用 |
|------|------|------|------|
| 前端 | https://saifu.3359717058.workers.dev | Cloudflare Pages | ¥0 |
| 域名 | saifu.asia（实名审核中） | 阿里云 | ¥18/年 |
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
| Cloudflare Pages | 已关联 GitHub 仓库，push 自动部署 |
| Cloudflare Tunnel | 无需账号（Quick Tunnel） |
| 域名注册 | 阿里云，账号 guolei，域名 saifu.asia |

---

## 部署架构

```
中国用户 → Cloudflare Pages（全球边缘节点）→ 前端页面秒开
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

## 🚀 重启步骤（电脑重启后必做，AI 自动执行版）

> **核心就两步：① 起隧道拿公网地址 → ② 把新地址写进 app.js 推 GitHub → Cloudflare Pages 自动部署。**
> 
> **AI 执行协议（2026-05-10 v3）：**
> 
> **Step 1 — 启动后端（后台运行）**
> ```
> cd "D:\我的竞赛项目-AI赋能竞赛系统\saifu\backend" && set DEEPSEEK_API_KEY=sk-6dfbaf1c69b94a14aafdf29ef4517e7e && python -m uvicorn main:app --host 0.0.0.0 --port 8000
> ```
> 用 Bash `run_in_background: true` 执行。
> 
> **Step 2 — 验证后端存活**
> ```
> curl http://localhost:8000/api/health
> ```
> 期望返回 `{"status":"ok","deepseek_configured":true}`。如果失败，等 3 秒再试一次。
> 
> **Step 3 — 启动隧道**
> - 优先 cloudflared：`"D:\我的竞赛项目-AI赋能竞赛系统\saifu\cloudflared.exe" tunnel --url http://localhost:8000`
>   - 从输出提取 `https://xxx.trycloudflare.com` 格式的 URL
>   - 如果 trycloudflare.com 返回 HTTP 500（服务端故障，不是本地问题），立即换备用方案
> - 备用 localhost.run：`ssh -o StrictHostKeyChecking=no -R 80:localhost:8000 nokey@localhost.run`
>   - 从输出提取 `https://xxxxxx.lhr.life` 格式的 URL
> 
> **Step 4 — 更新前端 API 地址**
> 编辑 `D:\我的竞赛项目-AI赋能竞赛系统\saifu\js\app.js`，找到第 11 行：
> ```
>   : 'https://precious-typing-brand-budgets.trycloudflare.com';
> ```
> 把旧的隧道 URL 替换成 Step 3 拿到的新 URL。
> 
> **Step 5 — 推送部署**
> ```
> cd "D:\我的竞赛项目-AI赋能竞赛系统" && git add saifu/js/app.js && git commit -m "update API tunnel URL" && git push
> ```
> Cloudflare Pages 自动检测 push → 自动重新部署（约 30-60 秒）。
> 
> **Step 6 — 完成播报**
> 告诉用户：「搞定了！打开 https://saifu.3359717058.workers.dev 就能用。等域名实名过了切换到 saifu.asia。」

---

## 本地开发

```bash
# 安装依赖（首次）
cd "D:\我的竞赛项目-AI赋能竞赛系统\saifu\backend"
pip install -r requirements.txt

# 启动后端
set DEEPSEEK_API_KEY=sk-6dfbaf1c69b94a14aafdf29ef4517e7e
python -m uvicorn main:app --host 0.0.0.0 --port 8000
```

### 必需条件
- Python 3.10+
- 稳定翻墙代理（DuckDuckGo 搜索需要境外网络）
- cloudflared.exe（已下载到 `D:\我的竞赛项目-AI赋能竞赛系统\saifu\cloudflared.exe`）

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
├── index.html                # 前端首页（4步表单+结果展示）
├── js/
│   └── app.js                # 表单收集+API调用+卡片渲染（**第11行=API地址**）
├── css/
│   └── style.css
├── cloudflared.exe           # Cloudflare Tunnel 客户端
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
2. **Tunnel URL 重启变**：每次重启电脑后需重新起隧道 + 更新 `saifu/js/app.js` 第 11 行 + `git push`（见上方🚀重启步骤，AI 可自动执行）
3. **Cloudflare Quick Tunnel 偶尔 500**：trycloudflare.com 服务端故障时换用 localhost.run（`ssh -R 80:localhost:8000 nokey@localhost.run`）
4. **DuckDuckGo 限速风险**：连续搜索可能触发 202 Ratelimit
5. **域名 saifu.asia 待实名通过**：审核中（预计 5/10 晚 21:30 出结果），通过后做快速过户 + Cloudflare Pages 绑定自定义域名
6. **verify_url 未集成**：URL 可达性校验函数已写但未接入 V1
7. **用户反馈纠正系统**：save_correction/load_corrections 计划 V2 实现

---

*赛赋 SaiFu v1.0 — 让每个大学生都能找到属于自己的竞赛*
